"""Uçtan uca boru hattı CLI'ı.

    python -m src.boru_hatti crawl            # toplama
    python -m src.boru_hatti extract          # çıkarım + veritabanına yazma
    python -m src.boru_hatti extract --yalniz-kural   # ablasyon koşusu
    python -m src.boru_hatti seed             # tohum veriyi işle (LLM/ağ gerekmez)
    python -m src.boru_hatti durum            # veritabanı özeti

Makefile bu komutları sarar. Jürinin gördüğü şey `make crawl && make extract`
olacak; ara katman ne kadar sade olursa "uçtan uca çalışıyor" iddiası o kadar
inandırıcı.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from src.collector.toplayici import (
    DEMO_HAM_DIZIN,
    HAM_DIZIN,
    bankalari_yukle,
    ham_kayitlari_oku,
    topla,
)
from src.depolama import (
    VERITABANI_URL,
    cikarim_kosusu_yaz,
    istatistikler,
    kaydet,
    semayi_kur,
)
from src.extraction.uzlastirici import UzlastirmaRaporu, kampanya_cikar
from src.schema import HamKayit

log = logging.getLogger("boru_hatti")

KOK = Path(__file__).resolve().parents[1]
TOHUM_DOSYASI = KOK / "data" / "seed" / "seed.jsonl"

ARA_KAYIT_ARALIGI = 10
"""Kaç kayıtta bir veritabanına yazılacağı. Uzun koşularda iş kaybını önler."""


def _varsayilan_isci() -> int:
    """Eş zamanlı çıkarım işçisi sayısı.

    YERELDE 1 OLMAK ZORUNDA. Ollama tek makinede koşuyor; ikinci bir istek
    modeli belleğe ikinci kez yüklemeye çalışır ve 8 GB'lık makinede bellek
    takasına girer — `CLAUDE.md`'deki "extract koşarken Streamlit'i kapat"
    uyarısının sebebi de budur. Paralellik orada hız değil, çökme getirir.

    EVREN'DE İŞ BİZİM MAKİNEMİZDE DEĞİL. 8×H200 üzerinde vLLM sürekli
    yığınlama yapıyor; eş zamanlı istek zaten beklediği çalışma biçimi.
    Ölçüm (24 gerçek kayıt, `llm-large`):

        seri      2,2 sn/kayıt  ->  590 kayıt ~25 dk
        16 işçi   0,44 sn/kayıt ->  590 kayıt ~4,5 dk

    16 seçildi çünkü ölçümde 4 ve 8 işçi arasında anlamlı fark yoktu
    (servis ortak kullanımda, kuyruk gürültüsü baskın). Gerekirse
    `CIKARIM_ISCI` ile değiştirilebilir.
    """
    varsayilan = 1 if os.getenv("LLM_SAGLAYICI", "evren").lower() == "ollama" else 16
    return max(1, int(os.getenv("CIKARIM_ISCI", str(varsayilan))))


def _gunlugu_kur(ayrintili: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if ayrintili else logging.INFO,
        format="%(levelname)-7s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Komutlar
# ---------------------------------------------------------------------------


def _crawl_ilerlemesi(olay: object) -> None:
    """Toplama olaylarını terminale tek satır hâlinde basar.

    Toplama dakikalarca sürüyor; ilerleme görünmezse koşan mı takılan mı
    belli olmuyor. Aynı geri çağrı arayüzde aşama göstergesini besleyecek.
    """
    asama = getattr(olay, "asama", "")
    if asama == "sayfa":
        log.info("  %s %d/%d %s", olay.banka_adi, olay.sira, olay.toplam, olay.url)  # type: ignore[attr-defined]
    elif asama in {"atlandi", "hata"}:
        log.info("  %s ATLANDI (%s) %s", olay.banka_adi, olay.mesaj, olay.url)  # type: ignore[attr-defined]


def komut_crawl(args: argparse.Namespace) -> int:
    bankalar = bankalari_yukle()
    if args.banka:
        bankalar = [b for b in bankalar if b.kod in args.banka or b.kisa_ad in args.banka]
        if not bankalar:
            log.error("Eşleşen banka yok: %s", args.banka)
            return 1
    topla(bankalar, gorunmez=args.gorunmez or None, ilerleme=_crawl_ilerlemesi)
    return 0


def _tohum_kayitlari() -> list[HamKayit]:
    """seed.jsonl -> HamKayit listesi.

    Tohum veri, toplayıcı hazır olmadan çıkarım geliştirmeyi mümkün kılar.
    Beklenen satır biçimi: {"banka_adi", "banka_kodu", "url", "metin"}
    """
    if not TOHUM_DOSYASI.exists():
        log.warning("Tohum dosyası yok: %s", TOHUM_DOSYASI)
        return []

    kayitlar: list[HamKayit] = []
    for satir_no, satir in enumerate(TOHUM_DOSYASI.read_text(encoding="utf-8").splitlines(), 1):
        satir = satir.strip()
        if not satir or satir.startswith("//"):
            continue
        try:
            veri = json.loads(satir)
        except json.JSONDecodeError as hata:
            log.error("seed.jsonl satır %d bozuk: %s", satir_no, hata)
            continue
        kayitlar.append(
            HamKayit(
                banka_kodu=veri.get("banka_kodu", "TOHUM"),
                banka_adi=veri.get("banka_adi", "Bilinmiyor"),
                url=veri.get("url", f"seed://{satir_no}"),
                cekim_tarihi=datetime.fromisoformat(
                    veri["cekim_tarihi"]) if veri.get("cekim_tarihi") else datetime.now(),
                http_durum=200,
                baslik=veri.get("baslik"),
                govde_metin=veri.get("metin", ""),
            )
        )
    return kayitlar


def ablasyon_veritabani(yapilandirma: str) -> str:
    """Ablasyon koşusunun kendi veritabanı — üretim verisine DOKUNMAZ.

    NEDEN AYRI: `make extract-kural` üretim veritabanının üstüne yazıyordu.
    Ablasyon ölçmek için koşulan «yalnız kural» yapılandırması, demoyu
    besleyen kayıtları katman eksik hâlleriyle değiştiriyordu; sonrasında
    `make extract` koşulmazsa arayüz sessizce bozuk veri gösteriyordu.
    Ölçüm koşusu, ölçtüğü sistemi bozmamalıdır.
    """
    dizin = KOK / "data" / "ablasyon"
    dizin.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{dizin / f'{yapilandirma}.db'}"


# ---------------------------------------------------------------------------
# Çıkarım çekirdeği — CLI ve arayüz aynı kod yolunu kullanır
# ---------------------------------------------------------------------------
#
# NEDEN AYRILDI: çıkarım mantığı `_cikar_ve_kaydet(kayitlar, args)` içindeydi
# ve girdi olarak `argparse.Namespace` istiyordu; ilerlemesi de yalnız
# `log.info`'ya gidiyordu. Arayüzden ne çağrılabiliyor ne de izlenebiliyordu.
# Aşağıdaki üç veri sınıfı + `cikarim_kos` o gövdenin AYNISIDIR; `_cikar_ve_
# kaydet` artık yalnız `args`'ı çevirip özeti basan ince bir sarmalayıcı.


@dataclass(frozen=True)
class CikarimAyarlari:
    """Bir çıkarım koşusunun yapılandırması — `args`'ın yerine geçen tip."""

    yalniz_kural: bool = False
    yalniz_llm: bool = False
    elestirmen_yok: bool = False
    yuklem_yok: bool = False
    model: str | None = None

    @property
    def yapilandirma(self) -> str:
        """Ablasyon tablosundaki kol adı — veritabanı seçimi buna bakar."""
        if self.yalniz_kural:
            return "kural"
        if self.yalniz_llm:
            return "llm"
        return "hibrit"

    @classmethod
    def argstan(cls, args: argparse.Namespace) -> CikarimAyarlari:
        return cls(
            yalniz_kural=bool(args.yalniz_kural),
            yalniz_llm=bool(args.yalniz_llm),
            elestirmen_yok=bool(args.elestirmen_yok),
            yuklem_yok=bool(args.yuklem_yok),
            model=args.model,
        )


@dataclass(frozen=True)
class CikarimIlerlemesi:
    """Çıkarım sırasında dışarı bildirilen tek olay.

    `src.collector.temel_kaziyici.Ilerleme` ile aynı desen: çekirdek ekrana
    hiçbir şey yazmaz, olayı geri çağrıya verir. Böylece aynı kod hem
    terminalden hem Streamlit'ten sürülebilir.
    """

    asama: Literal["basladi", "kayit", "hata", "ara_kayit", "bitti"]
    sira: int = 0
    toplam: int = 0
    banka_adi: str = ""
    url: str = ""
    doluluk: float = 0.0
    guven: float = 0.0
    sure: float = 0.0
    mesaj: str = ""

    kural: int = 0
    llm: int = 0
    hibrit: int = 0
    """O ANA KADAR birikmiş katman alan sayıları — koşan toplam, kayıt başına değil.

    `UzlastirmaRaporu` bu üç sayacı zaten kayıt başına üretiyordu; koşu
    sonuna kadar bekletmek için bir sebep yoktu. Arayüzdeki katman hattı
    bunlardan besleniyor, yani çubuklar koşu sürerken de ölçülmüş değerle
    doluyor — ara değer uydurulmuyor, var olan ölçüm erken veriliyor.
    """


CikarimGeriCagrisi = Callable[[CikarimIlerlemesi], None]


@dataclass
class CikarimOzeti:
    """Koşu bitiminde ölçülmüş sayılar. Terminal özeti de arayüz de bunu basar."""

    yapilandirma: str = "hibrit"
    veritabani_url: str = ""
    kayit_sayisi: int = 0
    hatali_kayit: int = 0
    kural_alan_sayisi: int = 0
    llm_alan_sayisi: int = 0
    hibrit_alan_sayisi: int = 0
    yuklem_duzeltme_sayisi: int = 0
    yuklem_reddi_sayisi: int = 0
    elenen_alan_sayisi: int = 0
    celiskiler: list = field(default_factory=list)
    kanit_denetimi_hatasi: int = 0
    sure: float = 0.0
    ortalama_doluluk: float = 0.0
    ortalama_guven: float = 0.0
    banka_dagilimi: dict[str, int] = field(default_factory=dict)
    kampanyalar: list = field(default_factory=list)
    iptal_edildi: bool = False

    @property
    def saniye_basina_kayit(self) -> float:
        """Ölçülen hız. Kayıt yoksa 0 — uydurma bölme yapılmaz."""
        return self.sure / self.kayit_sayisi if self.kayit_sayisi else 0.0


def demo_veritabani() -> str:
    """Arayüzdeki «Canlı Boru Hattı» sayfasının yazdığı veritabanı.

    `ablasyon_veritabani` ile aynı gerekçe: demo koşusu birkaç kayıtlık
    kırpılmış bir çıkarımdır; üretim ambarının üstüne yazarsa Genel Bakış
    sessizce eksik veri gösterir. Türetilmiş ve atılabilir.
    """
    dizin = KOK / "data" / "demo"
    dizin.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{dizin / 'demo.db'}"


def cikarim_kos(
    kayitlar: list[HamKayit],
    ayarlar: CikarimAyarlari,
    *,
    url: str | None = None,
    ilerleme: CikarimGeriCagrisi | None = None,
    iptal: Callable[[], bool] | None = None,
) -> CikarimOzeti:
    """Ham kayıtları çıkarır, veritabanına yazar, ölçülmüş özeti döner.

    `iptal` her öbek ve her kayıt öncesinde yoklanır. İş parçacığı
    öldürülmez: kalan kayıtlar atlanır, açık öbek biter, ara kayıt yazılır.
    Yarıda kesilen koşu da bir koşudur — `cikarim_kosusu_yaz` yine çağrılır,
    aksi hâlde `make eval` yeni yazılan kayıtları «bayat» sayardı.
    """
    baslangic = time.monotonic()
    yapilandirma = ayarlar.yapilandirma
    if url is None:
        url = VERITABANI_URL if yapilandirma == "hibrit" else ablasyon_veritabani(yapilandirma)
    if url != VERITABANI_URL:
        log.info("Ablasyon koşusu — ayrı veritabanı: %s", url)

    def _bildir(asama: str, **ayrinti: Any) -> None:
        if ilerleme is not None:
            ilerleme(CikarimIlerlemesi(asama=asama, **ayrinti))  # type: ignore[arg-type]

    def _iptal_edildi() -> bool:
        return iptal is not None and iptal()

    semayi_kur(url)
    llm_cikarici = None
    if not ayarlar.yalniz_kural:
        from src.ajanlar.elestirmen import ElestirmenAjani
        from src.extraction.llm import LLMCikarici

        elestirmen = ElestirmenAjani(etkin=not ayarlar.elestirmen_yok)
        llm_cikarici = LLMCikarici(model=ayarlar.model, elestirmen=elestirmen)
        log.info("LLM katmanı: %s / %s", llm_cikarici.saglayici.ad, llm_cikarici.model)
        if ayarlar.elestirmen_yok:
            log.warning(
                "DİKKAT: ELEŞTİRMEN AJANI KAPALI — çıkarılan değerler ham metinde "
                "doğrulanmayacak. Bu yalnız ablasyon ölçümü içindir; üretim "
                "koşusu değildir."
            )

    # YÜKLEM AJANI — kural-tek sayısal değerlerin yüklemini denetler.
    # Ölçüm (60 kayıtlık altın set, 3 tekrar): `vade_ay_max` 0,791→0,810,
    # `tahsis_ucreti` 0,833→0,909. Ayrıntı: `src/ajanlar/yuklem.py`.
    yuklem_ajani = None
    if not ayarlar.yalniz_kural and not ayarlar.yuklem_yok:
        from src.ajanlar.yuklem import YuklemAjani

        yuklem_ajani = YuklemAjani()
        log.info("Yüklem ajanı etkin (kapatmak için --yuklem-yok)")

    toplam_rapor = UzlastirmaRaporu()
    kampanyalar: list = []
    bekleyen: list = []
    hatali = 0

    isci = _varsayilan_isci()
    obek_boyu = max(ARA_KAYIT_ARALIGI, isci)
    if isci > 1:
        log.info("Eş zamanlı çıkarım: %d işçi, %d kayıtlık öbekler", isci, obek_boyu)

    _bildir(
        "basladi",
        toplam=len(kayitlar),
        mesaj=f"{yapilandirma} · {isci} işçi · {len(kayitlar)} kayıt",
    )

    # CANLI SAYAÇLAR — ilerleme olayları İŞÇİ PARÇACIĞINDAN, kayıt biter bitmez
    # gönderilir. Eskiden tüketici döngüsünden gönderiliyordu ve `havuz.map`
    # sonuçları GİRDİ SIRASINDA verdiği için 16 işçiyle koşan bir öbeğin bütün
    # olayları öbek sonunda tek seferde düşüyordu: arayüz koşu boyunca donuk
    # durup en sonda birden doluyordu. Ölçüldü — 3 kayıtlık koşuda üç olay da
    # 3,7 saniyenin sonunda geldi.
    #
    # Günlük satırı ve veritabanı yazma sırası DEĞİŞMEDİ: onlar hâlâ tüketici
    # döngüsünde, girdi sırasında. Paralelden çıkan tek şey ekranın beslendiği
    # olay akışı; `ilerleme` geri çağrısının bu yüzden iş parçacığı güvenli
    # olması gerekir (arayüzde `queue.Queue.put`).
    canli_kilit = threading.Lock()
    canli = {"biten": 0, "denenen": 0, "kural": 0, "llm": 0, "hibrit": 0}

    def _canli_kayit(kayit: HamKayit, kampanya, rapor) -> None:
        with canli_kilit:
            canli["biten"] += 1
            canli["denenen"] += 1
            canli["kural"] += rapor.kural_alan_sayisi
            canli["llm"] += rapor.llm_alan_sayisi
            canli["hibrit"] += rapor.hibrit_alan_sayisi
            anlik = dict(canli)
        # SÜRE YENİDEN ÖLÇÜLMEZ: `kampanya_cikar` zaten `trace_log` içine
        # yazıyor. İkinci bir ölçüm ikinci bir gerçeklik olurdu.
        _bildir(
            "kayit",
            sira=anlik["biten"],
            toplam=len(kayitlar),
            banka_adi=kampanya.banka_adi,
            url=kayit.url,
            doluluk=kampanya.doluluk_orani(),
            guven=kampanya.ortalama_guven(),
            sure=float(getattr(rapor, "trace_log", {}).get("toplam_sure", 0.0)),
            kural=anlik["kural"],
            llm=anlik["llm"],
            hibrit=anlik["hibrit"],
        )

    def _canli_hata(kayit: HamKayit, hata: Exception) -> None:
        with canli_kilit:
            canli["denenen"] += 1
            sira = canli["denenen"]
        _bildir(
            "hata",
            sira=sira,
            toplam=len(kayitlar),
            banka_adi=kayit.banka_adi,
            url=kayit.url,
            mesaj=f"{type(hata).__name__}: {hata}",
        )

    def _guvenli_cikar(kayit: HamKayit):
        """Tek kaydı çıkarır; hatayı YUTMAZ, çağırana geri verir.

        Bir kaydın düşmesi 590 kayıtlık koşuyu düşürmemeli — seri sürümdeki
        `continue` davranışının paraleldeki karşılığı budur. Ama hata
        kaybolmaz: istisna nesnesi döndürülür, sayılır ve arayüze bildirilir.
        """
        if _iptal_edildi():
            return None
        try:
            sonuc = kampanya_cikar(
                kayit,
                llm_cikarici=llm_cikarici,
                kural_kullan=not ayarlar.yalniz_llm,
                llm_kullan=not ayarlar.yalniz_kural,
                yuklem=yuklem_ajani,
            )
        except Exception as hata:
            log.error("Çıkarım hatası (%s): %s", kayit.url, hata)
            _canli_hata(kayit, hata)
            return hata
        _canli_kayit(kayit, *sonuc)
        return sonuc

    # ÖBEKLİ PARALELLİK — iki kısıtı aynı anda karşılar:
    #   1. `havuz.map` sonuçları GİRDİ SIRASINDA verir, bitiş sırasında değil.
    #      Günlük satırları ve veritabanı yazma sırası koşudan koşuya oynamaz.
    #      (Arayüzü besleyen olaylar bu sıraya BAĞLI DEĞİL — onlar işçiden,
    #      bitiş sırasında gidiyor; bkz. `_canli_kayit`.)
    #   2. Ara kayıt öbek sonunda yapılır; çökmede en fazla bir öbek kaybedilir.
    #
    # `isci = 1` olduğunda bu, eski seri döngüyle aynı davranışı üretir —
    # bilerek: ablasyon satırlarının aynı kod yolundan çıkması gerekiyor.
    sira = 0
    iptal_edildi = False
    with ThreadPoolExecutor(max_workers=isci) as havuz:
        for obek_bas in range(0, len(kayitlar), obek_boyu):
            if _iptal_edildi():
                iptal_edildi = True
                break
            obek = kayitlar[obek_bas : obek_bas + obek_boyu]

            for kayit, sonuc in zip(obek, havuz.map(_guvenli_cikar, obek)):
                sira += 1
                if isinstance(sonuc, Exception):
                    hatali += 1  # olay `_canli_hata`'dan zaten gitti
                    continue
                if sonuc is None:
                    continue
                kampanya, rapor = sonuc

                kampanyalar.append(kampanya)
                bekleyen.append(kampanya)
                toplam_rapor.kural_alan_sayisi += rapor.kural_alan_sayisi
                toplam_rapor.llm_alan_sayisi += rapor.llm_alan_sayisi
                toplam_rapor.hibrit_alan_sayisi += rapor.hibrit_alan_sayisi
                # Bu iki satır UNUTULMUŞTU: sayaçlar kayıt başına doğru
                # işliyordu ama toplama eklenmediği için özet hep 0 gösterdi
                # ve yüklem ajanı hiç çalışmıyor sanıldı.
                toplam_rapor.yuklem_duzeltme_sayisi += rapor.yuklem_duzeltme_sayisi
                toplam_rapor.yuklem_reddi_sayisi += rapor.yuklem_reddi_sayisi
                toplam_rapor.elenen_alan_sayisi += rapor.elenen_alan_sayisi
                toplam_rapor.celiskiler.extend(rapor.celiskiler)

                log.info(
                    "[%3d/%3d] %-16s doluluk=%.0f%% guven=%.2f  %s",
                    sira, len(kayitlar), kampanya.banka_adi[:16],
                    kampanya.doluluk_orani() * 100, kampanya.ortalama_guven(),
                    kayit.url[-52:],
                )

            # ARA KAYIT: koşunun sonunda tek seferde yazmak, ortada oluşacak bir
            # çökmede tüm işi çöpe atar. Kimlikler deterministik ve yazma upsert
            # olduğu için ara kayıt güvenlidir — koşu tekrarlanabilir.
            if bekleyen:
                kaydet(bekleyen, url)
                log.info("   ↳ %d kayıt veritabanına yazıldı (ara kayıt)", len(bekleyen))
                _bildir(
                    "ara_kayit",
                    sira=len(kampanyalar),
                    toplam=len(kayitlar),
                    mesaj=f"{len(bekleyen)} kayıt veritabanına yazıldı",
                )
                bekleyen.clear()

    # Koşuyu kaydet: `make eval` bayat sayı raporlamasın diye. Ara kayıttan
    # SONRA, tek sefer — koşunun tamamlandığı an budur.
    cikarim_kosusu_yaz(yapilandirma, len(kampanyalar), url)

    banka_dagilimi: dict[str, int] = {}
    for kampanya in kampanyalar:
        banka_dagilimi[kampanya.banka_adi] = banka_dagilimi.get(kampanya.banka_adi, 0) + 1

    ozet = CikarimOzeti(
        yapilandirma=yapilandirma,
        veritabani_url=url,
        kayit_sayisi=len(kampanyalar),
        hatali_kayit=hatali,
        kural_alan_sayisi=toplam_rapor.kural_alan_sayisi,
        llm_alan_sayisi=toplam_rapor.llm_alan_sayisi,
        hibrit_alan_sayisi=toplam_rapor.hibrit_alan_sayisi,
        yuklem_duzeltme_sayisi=toplam_rapor.yuklem_duzeltme_sayisi,
        yuklem_reddi_sayisi=toplam_rapor.yuklem_reddi_sayisi,
        elenen_alan_sayisi=toplam_rapor.elenen_alan_sayisi,
        celiskiler=list(toplam_rapor.celiskiler),
        kanit_denetimi_hatasi=sum(len(k.kanit_denetimi()) for k in kampanyalar),
        sure=time.monotonic() - baslangic,
        ortalama_doluluk=(
            sum(k.doluluk_orani() for k in kampanyalar) / len(kampanyalar)
            if kampanyalar
            else 0.0
        ),
        ortalama_guven=(
            sum(k.ortalama_guven() for k in kampanyalar) / len(kampanyalar)
            if kampanyalar
            else 0.0
        ),
        banka_dagilimi=banka_dagilimi,
        kampanyalar=kampanyalar,
        iptal_edildi=iptal_edildi or _iptal_edildi(),
    )
    _bildir(
        "bitti",
        sira=ozet.kayit_sayisi,
        toplam=len(kayitlar),
        sure=ozet.sure,
        mesaj="iptal edildi" if ozet.iptal_edildi else "tamamlandı",
    )
    return ozet


def _cikar_ve_kaydet(
    kayitlar: list[HamKayit],
    args: argparse.Namespace,
    url: str | None = None,
) -> int:
    """CLI sarmalayıcısı — `cikarim_kos`'u çağırır, özeti terminale basar.

    Terminal çıktısı ve dönüş kodu refactor öncesiyle aynıdır; ayrılan tek
    şey mantık, biçim değil.
    """
    if not kayitlar:
        log.error("İşlenecek kayıt yok. Önce `make crawl` veya seed.jsonl doldurun.")
        return 1

    ozet = cikarim_kos(kayitlar, CikarimAyarlari.argstan(args), url=url)

    print("\n" + "=" * 64)
    print(f"  Yapılandırma         : {ozet.yapilandirma}")
    print(f"  İşlenen kayıt        : {ozet.kayit_sayisi}")
    # DÜŞEN KAYIT SAYISI BASILIR — bu satır YOKTU ve 175 kayıt kaybettirdi.
    #
    # `hatali_kayit` hesaplanıyor, `CikarimOzeti`'nde duruyor ve arayüz onu
    # uyarı olarak gösteriyordu; TERMİNAL yolu hiç göstermiyordu. Takımın
    # fiilen kullandığı yol terminal olduğu için koşu «İşlenen kayıt: 726»
    # deyip 0 dönüyor, düşen 172 kayıt yalnız günlük satırlarında kalıyordu.
    #
    # Ölçüldü (27 Ağustos): data/raw'da 901 ham kayıt var, veritabanında 726.
    # Düşen 175'in tamamı http=200 ve gövdeli — 144'ünün gövdesi 1000+
    # karakter. Kural katmanı 175'inde de sorunsuz koşuyor, yani kayıp LLM
    # çağrısının geçici hatalarından; kalıcı bir veri kusuru değil. Bu satır
    # olmadan «726» korpusun tamamı sanıldı ve dokümana o sayı yazıldı.
    #
    # `girdi_kaydi` ile birlikte basılır: asıl bilgi mutlak sayı değil,
    # girdi ile çıktı arasındaki FARK. Dönüş kodu bilerek 0 kalıyor —
    # `make extract` zincirini kırmak, ara kayıtla yazılmış kayıtları da
    # kullanılamaz hâle getirirdi; kusur sessizlikti, koşunun kendisi değil.
    if ozet.hatali_kayit:
        print(
            f"  DİKKAT  Düşen kayıt  : {ozet.hatali_kayit} "
            f"(girdi {len(kayitlar)} → yazılan {ozet.kayit_sayisi})"
        )
        print("          Yeniden koşmak için: make extract kimlik=\"<düşen kimlikler>\"")
    print(f"  Yalnız kuraldan gelen: {ozet.kural_alan_sayisi} alan")
    print(f"  Yalnız LLM'den gelen : {ozet.llm_alan_sayisi} alan")
    print(f"  Hibrit (iki katman)  : {ozet.hibrit_alan_sayisi} alan")
    print(f"  Yüklem düzeltmesi    : {ozet.yuklem_duzeltme_sayisi} alan")
    print(f"  Yüklem reddi         : {ozet.yuklem_reddi_sayisi} alan")
    print(f"  Çelişki              : {len(ozet.celiskiler)}")
    for celiski in ozet.celiskiler[:8]:
        print(f"     - {celiski}")
    print("=" * 64)

    if ozet.kanit_denetimi_hatasi:
        print(
            f"  DİKKAT  Kanıt denetimi: {ozet.kanit_denetimi_hatasi} alan "
            "ham metinde doğrulanamadı"
        )
    else:
        print("  Kanıt denetimi: tüm değerler ham metinde doğrulandı")
    return 0

def komut_extract(args: argparse.Namespace) -> int:
    """Ham kayıtlardan çıkarım yapar; `--banka`/`--kimlik` ile daraltılabilir.

    NEDEN SÜZGEÇ VAR: ham veri düzeltildiğinde 900+ kaydın hepsini yeniden
    çıkarmak hem gereksiz hem zararlı — EVREN bayt düzeyinde deterministik
    değil, dokunulmayan kayıtların değerleri de oynardı (bkz. CLAUDE.md,
    «SAPMA SAYISAL ALANLARA DA VURUYOR»). Süzgeç dokunulanı yalıtır.

    İKİ KADEME, ÇÜNKÜ İKİSİNİN DE KARŞILIĞI ÇIKTI:
        `--banka 0214`  bir bankanın gövde ayıklaması toptan düzeldi (27 Ağu)
        `--kimlik 0203-2a8c276994f9 ...`  aynı bankanın YALNIZ birkaç kaydı
            düzeldi (27 Ağu, Albaraka'da 4 kayıt). Burada `--banka 0203`
            demek, dokunulmamış 122 kaydı da sapmaya açmak olurdu.

    İkisi birlikte verilirse KESİŞİM alınır. `kaydet` upsert olduğu için
    süzülen koşu diğer satırlara dokunmaz; süzgeç yalnız İŞLENECEK kayıt
    kümesini daraltır.
    """
    kayitlar = list(ham_kayitlari_oku())
    secim: list[str] = []

    if args.banka:
        istenen = set(args.banka)
        kayitlar = [k for k in kayitlar if k.banka_kodu in istenen]
        secim.append(f"banka={', '.join(sorted(istenen))}")

    if args.kimlik:
        istenen_kimlik = set(args.kimlik)
        kayitlar = [k for k in kayitlar if k.kampanya_id() in istenen_kimlik]
        secim.append(f"kimlik={len(istenen_kimlik)} adet")
        # SESSİZ EKSİK YASAK: yazım hatası olan bir kimlik süzgeci sessizce
        # daraltır, koşu «başarılı» görünür ve düzeltilen kayıt hiç çıkarılmaz.
        bulunmayan = istenen_kimlik - {k.kampanya_id() for k in kayitlar}
        if bulunmayan:
            log.error("Ham kayıtta bulunamayan kimlik: %s", ", ".join(sorted(bulunmayan)))
            return 1

    if secim:
        log.info("Süzgeç: %s — %d kayıt işlenecek", " · ".join(secim), len(kayitlar))
        if not kayitlar:
            log.error("Süzgece uyan ham kayıt yok: %s", " · ".join(secim))
            return 1

    return _cikar_ve_kaydet(kayitlar, args)


def komut_seed(args: argparse.Namespace) -> int:
    return _cikar_ve_kaydet(_tohum_kayitlari(), args)


def komut_durum(_: argparse.Namespace) -> int:
    ozet = istatistikler()
    print("\n=== VERİTABANI DURUMU ===")
    for anahtar, deger in ozet.items():
        if anahtar == "tur_dagilimi":
            print(f"  {anahtar}:")
            for tur, sayi in deger.items():  # type: ignore[union-attr]
                print(f"      {tur:28} {sayi}")
        elif isinstance(deger, float):
            print(f"  {anahtar:22}: {deger:.3f}")
        else:
            print(f"  {anahtar:22}: {deger}")

    from src.depolama import tum_kayitlar
    from src.vektor_db import indeks_durumu


    # Kayıtlar BİLEREK geçiliyor: `indeks_durumu` korpus verilmezse
    # bayatlığı denetlemez ve «denetlenmedi» der. `make durum`un tek işi
    # durumu söylemek olduğuna göre, denetlenmemiş bir cevap burada
    # işe yaramaz.
    durum = indeks_durumu(tum_kayitlar())
    print("\n=== RAG VEKTÖR İNDEKSİ ===")
    if not durum["var"]:
        print(f"  kurulmamış — `make vektor` ile kurulur ({durum['yol']})")
    else:
        print(f"  {'paragraf':22}: {durum['paragraf']}")
        print(f"  {'kampanya':22}: {durum['kampanya']}")
        print(f"  {'boyut':22}: {durum['boyut']}")
        print(f"  {'model':22}: {durum['model']}")
        print(f"  {'korpus izi':22}: {durum['korpus_izi']}")
        if durum["bayat"]:
            print(f"  BAYAT — {durum['sebep']}")
        elif durum["bayat"] is False:
            print("  güncel — indeks veritabanındaki korpusla aynı")

    # HAM ENVANTER ↔ KORPUS FARKI (27 Ağustos).
    #
    # İndeks bayatlığı için kurulan refleksin aynısı, bir kademe yukarıda:
    # `data/raw`da duran ama korpusa girmemiş kayıt kaç tane? Bu satır
    # olmadan 175 kayıtlık bir kayıp iki gün görünmedi — düşen kayıtlar
    # çıkarım koşusunda sayılıyordu ama koşu bitince o sayı hiçbir yerde
    # durmuyordu, `make durum` da yalnız veritabanına bakıyordu.
    #
    # SAYIM ÜCRETSİZ DEĞİL ama ucuz: yalnız `.json` adlarından kimlik
    # üretilir, gövdeler okunmaz (`ham_kayitlari_oku` HTML'i de yükler).
    from src.collector.toplayici import HAM_DIZIN

    ham_kimlikler = {yol.stem for yol in HAM_DIZIN.rglob("*.json")}
    if ham_kimlikler:
        korpus_kimlikleri = {k.kampanya_id for k in tum_kayitlar()}
        eksik = ham_kimlikler - korpus_kimlikleri
        print("\n=== HAM ENVANTER ↔ KORPUS ===")
        print(f"  {'ham kayıt (data/raw)':22}: {len(ham_kimlikler)}")
        print(f"  {'korpusta':22}: {len(ham_kimlikler) - len(eksik)}")
        if eksik:
            # FARKIN İKİ SEBEBİ VAR — 28 Ağustos'ta ölçüldü.
            #
            # Burada eskiden tek satır yazıyordu: «EKSİK — N ham kayıt
            # çıkarılmamış; `make extract` ile tamamlanır». O gün fark 98'di
            # ve tamamı BİLEREK ayıklanmıştı (95 kopya + 7 liste sayfası,
            # `make yinelenenleri-ele` · `make liste-sayfalarini-ele`).
            # Mesajın söylediğini yapan biri 95 kopyayı sessizce geri
            # getirirdi — ve sayım yeniden şişerdi. Ayıklama `data/raw`a
            # dokunmadığı için bu fark KALICIDIR, kusur değildir.
            print(
                f"  FARK — {len(eksik)} ham kayıt korpusta değil. İki sebebi olabilir:"
            )
            print(
                "    · bilerek ayıklanmış (kopya ya da liste sayfası) — bu fark BEKLENEN;"
                "\n      `make yinelenenleri-ele` / `make liste-sayfalarini-ele` kuru koşusu gösterir"
            )
            print(
                "    · çıkarımda düşmüş — `make extract` tamamlar, AMA ayıklananları da"
                "\n      geri getirir; sonrasında ayıklama adımları yeniden koşulmalı"
            )
        else:
            print("  tam — her ham kayıt korpusta")
    return 0


def komut_tazelik(args: argparse.Namespace) -> int:
    """Veri tazeliği denetimi (G-17) — kampanya sayfaları değişmiş mi?

    `Tetikleyici.cron_satiri()`'nin çağırdığı hedef budur. Ürünleşince cron
    bu komutu koşar; bugün elle ya da arayüzden çağrılır.

    HİÇBİR ŞEY YENİDEN ÇEKİLMEZ: `data/raw` ve `data/katilim.db`'ye
    dokunulmaz, yalnız `data/izleme/tazelik.json` yazılır.
    """
    from src.izleme import Tetikleyici, hedefleri_oku, tazelik_denetle

    dizin = DEMO_HAM_DIZIN if args.demo else HAM_DIZIN
    hedefler = hedefleri_oku(dizin)
    if args.adet:
        hedefler = hedefler[: args.adet]
    if not hedefler:
        log.error("Denetlenecek adres yok: %s", dizin)
        return 1

    log.info("%d adres yoklanıyor (%s)", len(hedefler), dizin)
    ozet = tazelik_denetle(hedefler, ilerleme=_tazelik_ilerlemesi)

    tetikleyici = Tetikleyici()
    print()
    print("=" * 64)
    print(f"  Denetlenen adres     : {ozet.denetlenen}")
    print(f"  Değişmedi            : {ozet.degismedi}")
    print(f"  DEĞİŞTİ              : {ozet.degisti}")
    print(f"  Taban çizgisi kuruldu: {ozet.ilk_kayit}")
    print(f"  Erişilemedi          : {ozet.erisilemedi}")
    print(f"  robots.txt reddetti  : {ozet.robots_reddi}")
    print(f"  Gövde inmeden (304)  : {ozet.dogrulayici_ile}")
    print(f"  Süre                 : {ozet.sure:.0f} sn")
    for olay in ozet.degisenler[:10]:
        print(f"     - {olay.banka_adi[:18]:18} {olay.url}")
    print("=" * 64)
    if ozet.taban_kuruldu_mu:
        print("  BİLGİ: İlk koşu — taban çizgisi kuruldu, değişiklik iddia edilmedi.")
    elif ozet.degisti:
        print("  DİKKAT: Değişen sayfalar var — tazelemek için `make crawl`.")
    else:
        print("  Kayıtlı kampanya verisi güncel.")
    print(f"  Zamanlayıcı kurulu mu: {'evet' if tetikleyici.kurulu else 'HAYIR (tasarım)'}")
    print(f"  Ürünleşince cron      : {tetikleyici.cron_satiri()}")
    return 0


def komut_kesif(args: argparse.Namespace) -> int:
    """Yeni kampanya keşfi (G-19) — listede olup elimizde olmayan var mı?

    YALNIZ liste keşfi koşar; detay sayfası çekilmez, hiçbir kayıt yazılmaz.
    `data/raw` ve `data/katilim.db` bu komuttan etkilenmez.
    """
    from src.izleme import kesif_kos

    bankalar = bankalari_yukle()
    if args.banka:
        bankalar = [b for b in bankalar if b.kod in args.banka or b.kisa_ad in args.banka]
        if not bankalar:
            log.error("Eşleşen banka yok: %s", args.banka)
            return 1

    ozet = kesif_kos(
        bankalar,
        gorunmez=not args.gorunur,
        ilerleme=_kesif_ilerlemesi,
    )

    print()
    print("=" * 64)
    print(f"  Keşfedilen banka     : {len(ozet.sonuclar)}")
    print(f"  Listede bulunan adres: {ozet.toplam_bulunan}")
    print(f"  YENİ (elimizde yok)  : {ozet.toplam_yeni}")
    print(f"  Kaldırılmış          : {ozet.toplam_kaldirilmis}")
    print(f"  Hatalı banka         : {ozet.hatali_banka}")
    print(f"  Süre                 : {ozet.sure:.0f} sn")
    print("-" * 64)
    for sonuc in ozet.sonuclar:
        if sonuc.hata:
            print(f"  {sonuc.banka_adi[:18]:18} HATA: {sonuc.hata[:38]}")
            continue
        print(
            f"  {sonuc.banka_adi[:18]:18} bulunan={sonuc.bulunan:3} "
            f"yeni={len(sonuc.yeni):3} kaldirilmis={len(sonuc.kaldirilmis):3} "
            f"({sonuc.sure:.0f} sn)"
        )
        for url in sonuc.yeni[:5]:
            print(f"      + {url}")
        if len(sonuc.yeni) > 5:
            print(f"      ... +{len(sonuc.yeni) - 5} tane daha")
    print("=" * 64)
    if ozet.taban_kuruldu_mu:
        print("  BİLGİ: İlk keşif — kaldırılmış iddiası bu koşuda anlamlı değil.")
    if ozet.toplam_yeni:
        print("  DİKKAT: Yeni kampanya bulundu — toplamak için `make crawl`.")
    else:
        print("  Listede elimizde olmayan kampanya yok.")
    return 0


def _kesif_ilerlemesi(olay: object) -> None:
    """Keşif olaylarını terminale tek satır hâlinde basar."""
    if getattr(olay, "asama", "") == "banka_basladi":
        log.info("  %s: liste keşfediliyor...", getattr(olay, "banka_adi", ""))


def _tazelik_ilerlemesi(olay: object) -> None:
    """Tazelik olaylarını terminale tek satır hâlinde basar."""
    sonuc = getattr(olay, "sonuc", "")
    if sonuc in {"degisti", "erisilemedi"}:
        log.info("  %-12s %s", sonuc.upper(), getattr(olay, "url", ""))
    else:
        log.debug("  %-12s %s", sonuc, getattr(olay, "url", ""))


def komut_vektor(_: argparse.Namespace) -> int:
    """RAG vektör indeksini kurar (S-09, ADR 014).

    Harici vektör veritabanı yok: paragraflar EVREN `bge-m3-embed` ile
    gömülüp yerel bir `.npz` dosyasına yazılır, arama numpy ile yapılır.
    """
    from src.depolama import tum_kayitlar
    from src.vektor_db import GOMME_SAGLAYICI, INDEKS_DOSYASI, aktif_gomme_modeli, indeks_kur

    kayitlar = tum_kayitlar()
    if not kayitlar:
        print("Veritabanı boş — önce `make extract` koşun.")
        return 1

    print(
        f"{len(kayitlar)} kayıt, gömme: {GOMME_SAGLAYICI} / {aktif_gomme_modeli()}"
    )
    adet = indeks_kur(kayitlar)
    print(f"{adet} paragraf indekslendi → {INDEKS_DOSYASI}")
    return 0


# ---------------------------------------------------------------------------


def ayristirici_kur() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="boru_hatti", description="Katılım bankacılığı metin madenciliği boru hattı"
    )
    ap.add_argument("-v", "--ayrintili", action="store_true", help="ayrıntılı günlük")
    altlar = ap.add_subparsers(dest="komut", required=True)

    p_crawl = altlar.add_parser("crawl", help="banka sitelerinden kampanya topla")
    p_crawl.add_argument("--banka", nargs="*", default=[], help="yalnız bu banka kodları")
    p_crawl.add_argument(
        "--gorunmez",
        action="store_true",
        help="tarayıcıyı görünmez (headless) koştur — sunucuda/CI'da gerekir",
    )
    p_crawl.set_defaults(islev=komut_crawl)

    for ad, islev, yardim in (
        ("extract", komut_extract, "toplanmış ham kayıtlardan çıkarım yap"),
        ("seed", komut_seed, "tohum veriden çıkarım yap (ağ gerekmez)"),
    ):
        p = altlar.add_parser(ad, help=yardim)
        p.add_argument("--model", default=None, help="model adı (EVREN: llm-large/llm-fast, yerel: Ollama etiketi)")
        p.add_argument("--yalniz-kural", action="store_true", help="ablasyon: LLM kapalı")
        p.add_argument("--yalniz-llm", action="store_true", help="ablasyon: kural kapalı")
        p.add_argument(
            "--elestirmen-yok",
            action="store_true",
            help="ablasyon: kanıt doğrulaması kapalı (üretimde KULLANMA)",
        )
        p.add_argument(
            "--yuklem-yok",
            action="store_true",
            help="ablasyon: yüklem denetimi kapalı",
        )
        if ad == "extract":
            # Yalnız `extract`e: `seed` tohum dosyasından okur, orada ham
            # kayıt süzmenin karşılığı yok.
            p.add_argument(
                "--banka",
                nargs="*",
                default=[],
                help="yalnız bu banka kodlarını çıkar (örn. --banka 0214)",
            )
            p.add_argument(
                "--kimlik",
                nargs="*",
                default=[],
                help="yalnız bu kampanya kimliklerini çıkar (örn. --kimlik 0203-2a8c276994f9)",
            )
        p.set_defaults(islev=islev)

    p_durum = altlar.add_parser("durum", help="veritabanı özeti")
    p_durum.set_defaults(islev=komut_durum)

    p_vektor = altlar.add_parser("vektor", help="RAG vektör indeksini kur (gömme + kosinüs)")
    p_vektor.set_defaults(islev=komut_vektor)

    p_tazelik = altlar.add_parser(
        "tazelik", help="kampanya sayfaları değişmiş mi (G-17 dinleyicisi)"
    )
    p_tazelik.add_argument(
        "--adet", type=int, default=0, help="yalnız ilk N adres (0 = hepsi)"
    )
    p_tazelik.add_argument(
        "--demo", action="store_true", help="data/demo_raw adreslerini yokla"
    )
    p_tazelik.set_defaults(islev=komut_tazelik)

    p_kesif = altlar.add_parser(
        "kesif", help="listede olup elimizde olmayan kampanya var mı (G-19)"
    )
    p_kesif.add_argument("--banka", nargs="*", default=[], help="yalnız bu banka kodları")
    p_kesif.add_argument(
        "--gorunur", action="store_true", help="tarayıcıyı görünür koştur (hata ayıklama)"
    )
    p_kesif.set_defaults(islev=komut_kesif)

    return ap


def main(argv: list[str] | None = None) -> int:
    args = ayristirici_kur().parse_args(argv)
    _gunlugu_kur(args.ayrintili)

    # Model varsayılanı artık sağlayıcının işi (`saglayici_kur`): EVREN'de
    # `llm-large`, yerelde `OLLAMA_MODEL`. `--model` verilmezse None kalır
    # ve sağlayıcı kendi varsayılanını seçer.
    return int(args.islev(args))


if __name__ == "__main__":
    sys.exit(main())
