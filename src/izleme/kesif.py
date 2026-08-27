"""Keşif — bankanın güncel listesinde ELİMİZDE OLMAYAN kampanya var mı?

Tazelik dinleyicisi (`dinleyici.py`) «elimizdeki bayatladı mı» sorusunu
cevaplar ve bu soruyu YAPISAL OLARAK göremez: yalnız bildiği URL'leri yoklar,
envanterde olmayan bir kampanyanın adresi hiç ziyaret edilmez.

Burada yapılan: bankanın kampanya LİSTESİ yeniden keşfedilir
(`kampanya_urlleri()`), dönen URL kümesi karşılaştırılır. **Detay sayfası
ÇEKİLMEZ** — tam toplamanın pahalı kısmı odur. Ölçüldü (27 Ağu): Hayat Finans
keşfi 9 sn, Albaraka 81 sn; tam toplama ise onlarca dakika.

DİFF'İN İKİ YÖNÜ AYRI TABANA KARŞI ÇALIŞIR — bu dosyanın en kritik kararı,
ölçümle verildi:

    YENİ         = keşif − `data/raw` envanteri          → GÜVENİLİR
    KALDIRILMIŞ  = önceki keşif − bu keşif               → GÜVENİLİR
    envanterde olup listede yok                          → yalnız BİLGİ

Neden kaldırılmış yönü envantere karşı çalışmıyor: `data/raw` yalnız kampanya
detay sayfalarından ibaret değil. Ölçüldü — Albaraka'nın 136 kaydının 88'i
`/bireysel/finansmanlar/...` gibi ÜRÜN sayfaları ve `kampanya_urlleri()`
onları tasarımı gereği hiç döndürmüyor. Envantere karşı diff alınsaydı her
koşuda 88 sahte «kaldırıldı» üretirdi.

YENİ yönü aynı kirlilikten etkilenmez: envanterde fazladan URL bulunması
YENİ kümesini yalnız KÜÇÜLTÜR, şişirmez. Bu yüzden asıl hedef güvenle
raporlanabiliyor.

Bu, `docs/kararlar/018-*` dersinin aynısı: karşılaştırma, karşılaştırılanı
ÜRETEN yola karşı yapılır.

Keşif de bir ziyarettir: robots kapısı ve nezaket kuralı `TemelKaziyici`
üzerinden aynen işler. `data/raw` ve `data/katilim.db` DEĞİŞTİRİLMEZ; yazılan
tek yer `data/izleme/kesif.json`.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.collector.toplayici import HAM_DIZIN, Banka, bankalari_yukle, faal_bankalar
from src.izleme.dinleyici import IZLEME_DIZIN

log = logging.getLogger(__name__)

KESIF_DOSYASI = IZLEME_DIZIN / "kesif.json"
"""Keşif taban çizgisi — banka başına son koşunun URL kümesi.

`.gitignore`'da: türetilmiş ve makineye özgü. `data/raw` ile
`data/katilim.db`'ye ASLA yazılmaz (G-17 kuralı burada da geçerli).
"""

IZLEME_PARAMETRELERI = frozenset(
    {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "utm_id", "gclid", "fbclid", "msclkid", "mc_cid", "mc_eid",
        "yclid", "igshid", "_ga", "ref", "referrer",
    }
)
"""Atılan izleme parametreleri — BEYAZ LİSTE değil, KARA liste.

Ters yönde («tanımadığımı at») çalışılsaydı `?slug=bireysel` ve `?page=3` gibi
SAYFAYI BELİRLEYEN parametreler de silinir, farklı sayfalar tek URL'e
indirgenirdi. Bilinmeyen parametre korunur.
"""

Asama = Literal["banka_basladi", "banka_bitti", "hata"]


@dataclass(frozen=True)
class KesifOlayi:
    """Keşif sırasında dışarı bildirilen tek olay.

    `Ilerleme` / `CikarimIlerlemesi` / `TazelikOlayi` ile aynı desen: çekirdek
    ekrana hiçbir şey yazmaz, olayı geri çağrıya verir.
    """

    banka_kodu: str = ""
    banka_adi: str = ""
    asama: Asama = "banka_basladi"
    bulunan: int = 0
    yeni: int = 0
    kaldirilmis: int = 0
    sira: int = 0
    toplam: int = 0
    sure: float = 0.0
    mesaj: str = ""


@dataclass
class KesifSonucu:
    """Tek bankanın keşif sonucu."""

    banka_kodu: str
    banka_adi: str
    bulunan: int = 0
    yeni: list[str] = field(default_factory=list)
    kaldirilmis: list[str] = field(default_factory=list)
    envanterde_gorunmeyen: int = 0
    """Envanterde olup listede çıkmayan adres sayısı — YALNIZ BİLGİ.

    Ürün ve liste sayfalarıyla dolu olduğu ölçüldü; «kaldırıldı» anlamına
    GELMEZ. Arayüzde bu uyarıyla birlikte gösterilir.
    """

    ilk_kesif: bool = False
    """Bu banka ilk kez keşfedildi — `kaldirilmis` iddiası anlamlı değil."""

    sure: float = 0.0
    hata: str = ""


@dataclass
class KesifOzeti:
    """Koşunun ölçülmüş sonucu."""

    sonuclar: list[KesifSonucu] = field(default_factory=list)
    sure: float = 0.0
    iptal_edildi: bool = False
    taban_dosyasi: str = ""

    @property
    def toplam_bulunan(self) -> int:
        return sum(s.bulunan for s in self.sonuclar)

    @property
    def toplam_yeni(self) -> int:
        return sum(len(s.yeni) for s in self.sonuclar)

    @property
    def toplam_kaldirilmis(self) -> int:
        return sum(len(s.kaldirilmis) for s in self.sonuclar)

    @property
    def hatali_banka(self) -> int:
        return sum(1 for s in self.sonuclar if s.hata)

    @property
    def taban_kuruldu_mu(self) -> bool:
        """İlk koşu mu — kaldırılmış iddiası bu koşuda anlamlı değil."""
        return bool(self.sonuclar) and all(s.ilk_kesif for s in self.sonuclar)


# ---------------------------------------------------------------------------
# URL normalizasyonu
# ---------------------------------------------------------------------------


def url_normalize(url: str) -> str:
    """Karşılaştırılabilir biçime indirger.

    İki URL'in aynı sayfayı gösterip göstermediğine karar veren yer burası;
    fazla agresif olursa farklı kampanyalar birleşir, fazla gevşek olursa
    aynı kampanya iki kez sayılır ve «yeni» sanılır.
    """
    if not url or not url.strip():
        return ""
    parca = urlsplit(url.strip())
    şema = "https" if parca.scheme in ("", "http", "https") else parca.scheme
    konak = parca.netloc.lower()
    if konak.startswith("www."):
        konak = konak[4:]
    yol = parca.path.rstrip("/") or "/"
    # Sorgu: izleme parametreleri atılır, kalan SIRALANIR (sıra anlam taşımaz).
    kalan = [
        (a, d) for a, d in parse_qsl(parca.query, keep_blank_values=True)
        if a.lower() not in IZLEME_PARAMETRELERI
    ]
    return urlunsplit((şema, konak, yol, urlencode(sorted(kalan)), ""))


def kampanya_urli_mi(url: str) -> bool:
    """Kampanya DETAY sayfası gibi mi görünüyor?

    Liste sayfalarını, sayfalama adreslerini ve arşivi eler. Yalnız
    «envanterde olup listede yok» BİLGİ sayacını anlamlı kılmak için var;
    YENİ hesabında kullanılmaz (orada eleme yanlışlıkla gerçek bir yeni
    kampanyayı gizleyebilirdi).
    """
    if not url:
        return False
    parca = urlsplit(url_normalize(url))
    yol = parca.path.lower()
    sorgu = dict(parse_qsl(parca.query))

    if any(a.lower() == "page" for a in sorgu):
        return False
    if "gecmis" in yol or "gecmis" in parca.query.lower():
        return False
    # Yolun son parçası liste adının kendisiyse detay değildir.
    son = yol.rstrip("/").rsplit("/", 1)[-1]
    return son not in {"", "kampanya", "kampanyalar", "kampanyalarimiz", "tumu"}


# ---------------------------------------------------------------------------
# Envanter ve taban çizgisi
# ---------------------------------------------------------------------------


def envanter_oku(dizin: Path = HAM_DIZIN) -> dict[str, set[str]]:
    """`data/raw`'daki URL'leri banka koduna göre normalize ederek okur.

    HTML gövdesi OKUNMAZ — yalnız JSON üst verisi. 1.024 kaydın HTML'ini
    belleğe almak yüzlerce megabayt ve tamamen boşuna.
    """
    envanter: dict[str, set[str]] = {}
    if not dizin.is_dir():
        return envanter
    for yol in sorted(dizin.rglob("*.json")):
        try:
            veri = json.loads(yol.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as hata:
            log.warning("Ham kayıt okunamadı (%s): %s", yol, hata)
            continue
        url = url_normalize(veri.get("url", ""))
        if url:
            envanter.setdefault(veri.get("banka_kodu", ""), set()).add(url)
    return envanter


def kesif_taban_oku(yol: Path = KESIF_DOSYASI) -> dict[str, set[str]]:
    """Önceki keşif koşusunun banka başına URL kümesi."""
    if not yol.is_file():
        return {}
    try:
        ham = json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as hata:
        # SESSİZ YUTMA DEĞİL: bozuk taban «her şey kaldırıldı» görüntüsü verir.
        log.warning("Keşif tabanı okunamadı (%s): %s — sıfırdan kurulacak", yol, hata)
        return {}
    return {
        kod: {url_normalize(u) for u in kayit.get("urller", [])}
        for kod, kayit in ham.get("bankalar", {}).items()
        if isinstance(kayit, dict)
    }


def kesif_taban_yaz(
    taban: dict[str, set[str]], yol: Path = KESIF_DOSYASI, *, zaman: str = ""
) -> None:
    """Taban çizgisini atomik yazar (önce geçici dosya, sonra taşıma)."""
    yol.parent.mkdir(parents=True, exist_ok=True)
    veri = {
        "surum": 1,
        "yazma_zamani": zaman or datetime.now().isoformat(timespec="seconds"),
        "bankalar": {
            kod: {"urller": sorted(urller), "adet": len(urller)}
            for kod, urller in taban.items()
        },
    }
    gecici = yol.with_suffix(".json.tmp")
    gecici.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
    gecici.replace(yol)


# ---------------------------------------------------------------------------
# Keşif akışı
# ---------------------------------------------------------------------------


def kesif_kos(
    bankalar: list[Banka] | None = None,
    *,
    gorunmez: bool | None = True,
    dizin: Path = HAM_DIZIN,
    taban_yolu: Path = KESIF_DOSYASI,
    ilerleme: Callable[[KesifOlayi], None] | None = None,
    iptal: Callable[[], bool] | None = None,
) -> KesifOzeti:
    """Banka listelerini keşfeder, envanterle karşılaştırır, özeti döner.

    YALNIZ `kampanya_urlleri()` çağrılır — `tara()` DEĞİL. Hiçbir detay
    sayfası açılmaz, hiçbir kayıt yazılmaz. `data/raw` ve `data/katilim.db`
    bu işlevden etkilenmez.

    selenium yalnız BURADA içeri alınır (`topla()` ile aynı gerekçe): hafif
    yardımcıları çağıran arayüz ve testler tarayıcı bağımlılığı olmadan
    çalışabilsin diye.
    """
    from src.collector.kaziyicilar import kaziyici_sinifi
    from src.collector.tarayici import surucu_olustur
    from src.collector.temel_kaziyici import benzersiz
    from src.collector.toplayici import NezaketSirasi, RobotsBekcisi

    baslangic = time.monotonic()
    hedefler = faal_bankalar(bankalar if bankalar is not None else bankalari_yukle())
    ozet = KesifOzeti(taban_dosyasi=str(taban_yolu))
    if not hedefler:
        log.warning("Kampanya beklenen banka yok — keşif yapılmadı.")
        return ozet

    envanter = envanter_oku(dizin)
    taban = kesif_taban_oku(taban_yolu)
    yeni_taban = dict(taban)

    def _bildir(**ayrinti: Any) -> None:
        if ilerleme is not None:
            ilerleme(KesifOlayi(**ayrinti))

    bekci = RobotsBekcisi()
    sira = NezaketSirasi(bekci)
    surucu, bekleme = surucu_olustur(gorunmez=gorunmez)
    try:
        for sayac, banka in enumerate(hedefler, 1):
            if iptal is not None and iptal():
                ozet.iptal_edildi = True
                break

            ortak = {
                "banka_kodu": banka.kod,
                "banka_adi": banka.kisa_ad,
                "sira": sayac,
                "toplam": len(hedefler),
            }
            sinif = kaziyici_sinifi(banka.kod)
            if sinif is None:
                mesaj = f"kazıyıcısı yok (kod {banka.kod})"
                log.warning("%-22s %s — atlanıyor", banka.kisa_ad, mesaj)
                ozet.sonuclar.append(
                    KesifSonucu(banka.kod, banka.kisa_ad, hata=mesaj)
                )
                _bildir(**ortak, asama="hata", mesaj=mesaj)
                continue

            _bildir(**ortak, asama="banka_basladi", mesaj="liste keşfediliyor")
            t0 = time.monotonic()
            kaziyici = sinif(banka, surucu, bekleme, bekci=bekci, sira=sira)
            try:
                bulunan = {
                    n for u in benzersiz(kaziyici.kampanya_urlleri())
                    if (n := url_normalize(u))
                }
            except Exception as hata:  # noqa: BLE001 — bir banka diğerlerini düşürmez
                mesaj = f"{type(hata).__name__}: {hata}"
                log.error("%-22s keşif hatası: %s", banka.kisa_ad, mesaj)
                ozet.sonuclar.append(
                    KesifSonucu(
                        banka.kod, banka.kisa_ad, sure=time.monotonic() - t0, hata=mesaj
                    )
                )
                _bildir(**ortak, asama="hata", mesaj=mesaj, sure=time.monotonic() - t0)
                continue

            envanter_kumesi = envanter.get(banka.kod, set())
            onceki_kesif = taban.get(banka.kod)

            # YENİ — envantere karşı. Kirli envanter bu kümeyi yalnız küçültür.
            yeni = sorted(bulunan - envanter_kumesi)
            # KALDIRILMIŞ — ÖNCEKİ KEŞFE karşı, elmayla elma. İlk koşuda iddia yok.
            kaldirilmis = sorted(onceki_kesif - bulunan) if onceki_kesif else []
            # BİLGİ — envanterde olup listede çıkmayan; ürün/liste sayfalarıyla dolu.
            gorunmeyen = sum(
                1 for u in envanter_kumesi - bulunan if kampanya_urli_mi(u)
            )

            sonuc = KesifSonucu(
                banka_kodu=banka.kod,
                banka_adi=banka.kisa_ad,
                bulunan=len(bulunan),
                yeni=yeni,
                kaldirilmis=kaldirilmis,
                envanterde_gorunmeyen=gorunmeyen,
                ilk_kesif=onceki_kesif is None,
                sure=time.monotonic() - t0,
            )
            ozet.sonuclar.append(sonuc)
            yeni_taban[banka.kod] = bulunan
            log.info(
                "%-22s bulunan=%3d yeni=%3d kaldirilmis=%3d (%.0f sn)",
                banka.kisa_ad, len(bulunan), len(yeni), len(kaldirilmis), sonuc.sure,
            )
            _bildir(
                **ortak, asama="banka_bitti", bulunan=len(bulunan), yeni=len(yeni),
                kaldirilmis=len(kaldirilmis), sure=sonuc.sure,
                mesaj=f"{len(bulunan)} adres · {len(yeni)} yeni",
            )
    finally:
        surucu.quit()

    # Kesilen koşuda da yazılır: keşfedilen bankalar boşa gitmesin.
    kesif_taban_yaz(yeni_taban, taban_yolu)
    ozet.sure = time.monotonic() - baslangic
    return ozet


__all__ = [
    "IZLEME_PARAMETRELERI",
    "KESIF_DOSYASI",
    "KesifOlayi",
    "KesifOzeti",
    "KesifSonucu",
    "envanter_oku",
    "kampanya_urli_mi",
    "kesif_kos",
    "kesif_taban_oku",
    "kesif_taban_yaz",
    "url_normalize",
]
