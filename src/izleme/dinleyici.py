"""Dinleyici — kampanya sayfası son çekimden beri değişmiş mi?

İKİ KADEMELİ, ucuzdan pahalıya:

  1. HTTP DOĞRULAYICI — elimizde `ETag` / `Last-Modified` varsa koşullu GET
     yapılır. Sunucu `304` derse sayfa gövdesi hiç indirilmez; en ucuz cevap.
  2. İÇERİK ÖZETİ — doğrulayıcı yoksa sayfa çekilir, `trafilatura` ile gövde
     ayıklanır, boşluk normalize edilip sha256 alınır ve ÖNCEKİ YOKLAMANIN
     özetiyle karşılaştırılır.

NEDEN İKİ KADEME — ölçüldü (27 Ağustos, dokuz bankanın her birinden bir
kampanya URL'i):

    ETag ya da Last-Modified veren      2 / 9   (Kuveyt Türk, Türkiye Finans)
    hiçbir doğrulayıcı vermeyen         7 / 9
    koşullu GET'e 304 dönen             2 / 2   ← veren iki banka da doğru davrandı

Yani tek başına `ETag` yoklaması bankaların yedisini hiç kapsamıyor; içerik
özeti şart. Tersi de doğru: doğrulayıcı veren ikisinde sayfayı indirmemek
bedava kazanç.

DİKKAT — TABAN ÇİZGİSİ KENDİ YOLUNDAN KURULUR — bu dosyanın en kritik kararı.
    Özet, `data/raw`'daki `govde_metin` ile KARŞILAŞTIRILMAZ. O gövdeyi
    Selenium üretti, buradaki çekim ise tarayıcısız (`httpx`). Ölçüldü: iki
    yol dokuz bankanın yedisinde birebir aynı gövdeyi veriyor, ama ikisinde
    vermiyor — Vakıf Katılım'da `httpx` fazladan menü başlığı görüyor, Dünya
    Katılım'da `trafilatura` tablo satırlarını `| ` önekiyle basıyor. İkisi de
    İÇERİK DEĞİŞİKLİĞİ DEĞİL, render yolu farkı. Selenium tabanına karşı
    karşılaştırılsaydı bu iki banka her koşuda «değişti» derdi.

    Bu yüzden ilk yoklama `ilk_kayit` döner: taban çizgisi kurulur, değişiklik
    İDDİA EDİLMEZ. Karşılaştırma ikinci yoklamadan itibaren, elmayla elma.

Nezaket aynen geçerli: robots.txt kapısı, alan adı başına tek sıra, istek
arası en az `ISTEK_ARASI_SANIYE`. Denetim de bir ziyarettir.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import httpx
import trafilatura

from src.collector.toplayici import (
    HAM_DIZIN,
    KULLANICI_AJANI,
    NezaketSirasi,
    RobotsBekcisi,
)

log = logging.getLogger(__name__)

KOK = Path(__file__).resolve().parents[2]
IZLEME_DIZIN = KOK / "data" / "izleme"
TABAN_DOSYASI = IZLEME_DIZIN / "tazelik.json"
"""Taban çizgisi. `data/raw` ve `data/katilim.db`'ye ASLA yazılmaz — ölçümlerin
üzerinde koştuğu veri teslim için donmuş durumda (G-17 uyarısı)."""

ZAMAN_ASIMI = 20.0

Sonuc = Literal["degismedi", "degisti", "ilk_kayit", "erisilemedi", "robots_reddi"]
Yontem = Literal["http_dogrulayici", "icerik_ozeti", ""]


@dataclass(frozen=True)
class IzlemeHedefi:
    """Denetlenecek tek adres. Ham kayıttan yalnız kimlik alanları alınır."""

    banka_kodu: str
    banka_adi: str
    url: str


@dataclass(frozen=True)
class TazelikOlayi:
    """Yoklama sırasında dışarı bildirilen tek olay.

    `Ilerleme` ve `CikarimIlerlemesi` ile aynı desen: çekirdek ekrana hiçbir
    şey yazmaz, olayı geri çağrıya verir.
    """

    banka_kodu: str = ""
    banka_adi: str = ""
    url: str = ""
    sonuc: Sonuc = "degismedi"
    yontem: Yontem = ""
    sira: int = 0
    toplam: int = 0
    mesaj: str = ""


@dataclass
class TazelikKaydi:
    """Bir URL'in taban çizgisi — `tazelik.json` içinde duran satır."""

    url: str
    banka_kodu: str = ""
    ozet: str = ""
    etag: str = ""
    son_degisiklik: str = ""
    yoklama_zamani: str = ""
    degisiklik_zamani: str = ""
    """En son DEĞİŞİKLİK görülen an. Yoklama zamanından ayrı: «üç gündür
    denetleniyor, iki gün önce değişmiş» ancak ikisi ayrı tutulursa söylenebilir."""


@dataclass
class TazelikOzeti:
    """Yoklamanın ölçülmüş sonucu."""

    denetlenen: int = 0
    degismedi: int = 0
    degisti: int = 0
    ilk_kayit: int = 0
    erisilemedi: int = 0
    robots_reddi: int = 0
    dogrulayici_ile: int = 0
    """Kaç URL sayfa gövdesi indirilmeden (304 ile) cevaplandı."""

    sure: float = 0.0
    degisenler: list[TazelikOlayi] = field(default_factory=list)
    taban_dosyasi: str = ""
    iptal_edildi: bool = False

    @property
    def taban_kuruldu_mu(self) -> bool:
        """İlk koşu mu — bu koşuda değişiklik iddiası anlamlı değildir."""
        return self.ilk_kayit > 0 and self.degisti == 0


def icerik_ozeti(metin: str) -> str:
    """Gövde metninin sha256'sı. BÜTÜN boşluklar atılarak.

    Boşluk daraltmak yetmedi — ölçüldü (27 Ağustos, Albaraka
    `konut-ve-tasit-finansmani-kampanyasi`). Sunucu aynı sayfayı iki ayrı
    biçimde veriyor ve fark TEK BİR BOŞLUK:

        çekim 1,2,3,4,6,8 →  "%3,19 'danbaşlayan kâr oranı"   (682 karakter)
        çekim 5,7         →  "%3,19 'dan başlayan kâr oranı"  (683 karakter)

    `" ".join(metin.split())` boşluk DİZİLERİNİ daraltır ama eksik boşluğu
    ekleyemez; iki varyant farklı özet üretiyor ve sayfa dakikada bir
    «değişti» diyordu. Yanlış alarm, kaçırılan değişiklikten daha pahalıdır:
    her koşuda bağıran bir uyarı okunmaz hâle gelir ve gerçek değişiklik de
    onunla birlikte gözden kaçar.

    Boşluğu tamamen atmak bunu çözer, çünkü DEĞİŞİKLİK TESPİTİNDE boşluk
    içerik değildir. Gerçek bir kampanya değişikliği rakam ya da kelime
    değiştirir (`%1,89` → `%2,49`, `120 ay` → `60 ay`); bunların hiçbiri
    boşluk atılınca kaybolmaz.
    """
    return hashlib.sha256("".join(metin.split()).encode("utf-8")).hexdigest()


def hedefleri_oku(dizin: Path = HAM_DIZIN) -> list[IzlemeHedefi]:
    """Ham kayıtlardan denetlenecek adresleri okur.

    `ham_kayitlari_oku` KULLANILMIYOR: o, kayıt başına `.html` dosyasını da
    okur. Burada gövdeye ihtiyaç yok — 1.024 kaydın HTML'ini belleğe almak
    yüzlerce megabayt, üstelik tamamen boşuna.
    """
    hedefler: list[IzlemeHedefi] = []
    gorulen: set[str] = set()
    for yol in sorted(dizin.rglob("*.json")):
        try:
            veri = json.loads(yol.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as hata:
            log.warning("Ham kayıt okunamadı (%s): %s", yol, hata)
            continue
        url = veri.get("url", "")
        if not url or url in gorulen:
            continue
        gorulen.add(url)
        hedefler.append(
            IzlemeHedefi(
                banka_kodu=veri.get("banka_kodu", ""),
                banka_adi=veri.get("banka_adi", ""),
                url=url,
            )
        )
    return hedefler


def taban_oku(yol: Path = TABAN_DOSYASI) -> dict[str, TazelikKaydi]:
    """Taban çizgisini okur. Dosya yoksa boş sözlük — ilk koşu demektir."""
    if not yol.is_file():
        return {}
    try:
        ham = json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as hata:
        # SESSİZ YUTMA DEĞİL: bozuk taban, «her şey değişmiş» görüntüsü verir.
        # Uyarı basılır ve taban sıfırdan kurulur.
        log.warning("Taban çizgisi okunamadı (%s): %s — sıfırdan kurulacak", yol, hata)
        return {}
    return {
        url: TazelikKaydi(**kayit)
        for url, kayit in ham.get("kayitlar", {}).items()
        if isinstance(kayit, dict)
    }


def taban_yaz(taban: dict[str, TazelikKaydi], yol: Path = TABAN_DOSYASI) -> None:
    """Taban çizgisini diske yazar (önce geçici dosya, sonra taşıma).

    Yarıda kesilen yazma bozuk JSON bırakır ve bir sonraki koşu tabanı
    okuyamayıp her sayfayı «ilk kayıt» sayardı.
    """
    yol.parent.mkdir(parents=True, exist_ok=True)
    veri = {
        "surum": 1,
        "yazma_zamani": datetime.now().isoformat(timespec="seconds"),
        "kayitlar": {url: asdict(kayit) for url, kayit in taban.items()},
    }
    gecici = yol.with_suffix(".json.tmp")
    gecici.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
    gecici.replace(yol)


def _govdeyi_ayikla(html: str) -> str:
    return (
        trafilatura.extract(
            html, include_comments=False, include_tables=True, favor_recall=True
        )
        or ""
    )


def tazelik_denetle(
    hedefler: list[IzlemeHedefi],
    *,
    taban_yolu: Path = TABAN_DOSYASI,
    ilerleme: Callable[[TazelikOlayi], None] | None = None,
    iptal: Callable[[], bool] | None = None,
    bekci: RobotsBekcisi | None = None,
    sira: NezaketSirasi | None = None,
    transport: httpx.BaseTransport | None = None,
) -> TazelikOzeti:
    """Adresleri yoklar, taban çizgisini günceller, ölçülmüş özeti döner.

    Sayfa İNDİRİLİR ama HİÇBİR ŞEY YENİDEN ÇEKİLMEZ: `data/raw` ve
    `data/katilim.db` bu işlevden etkilenmez. Tek yazılan yer `taban_yolu`.

    `iptal` her hedef öncesinde yoklanır; kesilen koşuda o ana kadarki taban
    yine de yazılır — yapılan ziyaretler boşa gitmesin.

    `transport` yalnız TEST içindir (`httpx.MockTransport`): dinleyicinin
    sözleşmesi ağ olmadan sınanabilsin diye. Üretimde `None` kalır.
    """
    baslangic = time.monotonic()
    bekci = bekci or RobotsBekcisi()
    sira = sira or NezaketSirasi(bekci)
    taban = taban_oku(taban_yolu)
    ozet = TazelikOzeti(taban_dosyasi=str(taban_yolu))
    simdi = datetime.now().isoformat(timespec="seconds")

    def _bildir(**ayrinti: Any) -> None:
        if ilerleme is not None:
            ilerleme(TazelikOlayi(**ayrinti))

    toplam = len(hedefler)
    with httpx.Client(
        timeout=ZAMAN_ASIMI,
        follow_redirects=True,
        headers={"User-Agent": KULLANICI_AJANI},
        transport=transport,
    ) as istemci:
        for sayac, hedef in enumerate(hedefler, 1):
            if iptal is not None and iptal():
                ozet.iptal_edildi = True
                break

            ortak = {
                "banka_kodu": hedef.banka_kodu,
                "banka_adi": hedef.banka_adi,
                "url": hedef.url,
                "sira": sayac,
                "toplam": toplam,
            }

            if not bekci.izinli_mi(hedef.url):
                ozet.robots_reddi += 1
                _bildir(**ortak, sonuc="robots_reddi", mesaj="robots.txt reddetti")
                continue

            onceki = taban.get(hedef.url)
            sira.bekle(hedef.url)

            # 1. KADEME — koşullu GET. Elimizde doğrulayıcı varsa sunucuya
            # «değiştiyse gönder» denir; değişmediyse gövde hiç inmez.
            sartlar: dict[str, str] = {}
            if onceki is not None:
                if onceki.etag:
                    sartlar["If-None-Match"] = onceki.etag
                if onceki.son_degisiklik:
                    sartlar["If-Modified-Since"] = onceki.son_degisiklik

            try:
                yanit = istemci.get(hedef.url, headers=sartlar or None)
            except httpx.HTTPError as hata:
                ozet.erisilemedi += 1
                _bildir(
                    **ortak, sonuc="erisilemedi", mesaj=f"{type(hata).__name__}"
                )
                continue

            ozet.denetlenen += 1
            etag = yanit.headers.get("etag", "")
            son_degisiklik = yanit.headers.get("last-modified", "")

            if yanit.status_code == 304 and onceki is not None:
                ozet.degismedi += 1
                ozet.dogrulayici_ile += 1
                taban[hedef.url] = TazelikKaydi(
                    url=hedef.url,
                    banka_kodu=hedef.banka_kodu,
                    ozet=onceki.ozet,
                    etag=etag or onceki.etag,
                    son_degisiklik=son_degisiklik or onceki.son_degisiklik,
                    yoklama_zamani=simdi,
                    degisiklik_zamani=onceki.degisiklik_zamani,
                )
                _bildir(
                    **ortak, sonuc="degismedi", yontem="http_dogrulayici",
                    mesaj="304 — sunucu değişmedi dedi",
                )
                continue

            if yanit.status_code >= 400:
                ozet.erisilemedi += 1
                _bildir(**ortak, sonuc="erisilemedi", mesaj=f"HTTP {yanit.status_code}")
                continue

            # 2. KADEME — içerik özeti.
            yeni_ozet = icerik_ozeti(_govdeyi_ayikla(yanit.text))

            if onceki is None or not onceki.ozet:
                # TABAN ÇİZGİSİ KURULUYOR — değişiklik iddia edilmez.
                ozet.ilk_kayit += 1
                sonuc: Sonuc = "ilk_kayit"
                degisiklik_zamani = ""
                mesaj = "taban çizgisi kuruldu"
            elif onceki.ozet == yeni_ozet:
                ozet.degismedi += 1
                sonuc = "degismedi"
                degisiklik_zamani = onceki.degisiklik_zamani
                mesaj = "içerik özeti aynı"
            else:
                ozet.degisti += 1
                sonuc = "degisti"
                degisiklik_zamani = simdi
                mesaj = f"özet değişti ({onceki.ozet[:8]} → {yeni_ozet[:8]})"

            taban[hedef.url] = TazelikKaydi(
                url=hedef.url,
                banka_kodu=hedef.banka_kodu,
                ozet=yeni_ozet,
                etag=etag,
                son_degisiklik=son_degisiklik,
                yoklama_zamani=simdi,
                degisiklik_zamani=degisiklik_zamani,
            )
            olay_ayrinti = dict(
                **ortak, sonuc=sonuc, yontem="icerik_ozeti", mesaj=mesaj
            )
            if sonuc == "degisti":
                ozet.degisenler.append(TazelikOlayi(**olay_ayrinti))
            _bildir(**olay_ayrinti)

    # Kesilen koşuda da yazılır: yapılan ziyaretler boşa gitmesin, bir
    # sonraki koşu onları yeniden yoklamak zorunda kalmasın.
    taban_yaz(taban, taban_yolu)
    ozet.sure = time.monotonic() - baslangic
    return ozet


__all__ = [
    "TABAN_DOSYASI",
    "IzlemeHedefi",
    "TazelikKaydi",
    "TazelikOlayi",
    "TazelikOzeti",
    "hedefleri_oku",
    "icerik_ozeti",
    "taban_oku",
    "taban_yaz",
    "tazelik_denetle",
]
