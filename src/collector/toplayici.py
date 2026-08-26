"""Toplama katmanının çekirdeği (Katman 0) — kayıt defteri, nezaket, diske yazma.

Bu dosya kampanya sayfalarını KENDİ ÇEKMEZ. Çekme işi banka başına yazılmış
Selenium kazıyıcılarındadır (`src/collector/kaziyicilar/`); burada onların
ortak altyapısı durur:

    bankalari_yukle / faal_bankalar   ← data/banks.yaml kayıt defteri
    RobotsBekcisi                     ← robots.txt kapısı + crawl-delay
    NezaketSirasi                     ← alan adı başına tek sıra, hız sınırı
    kaydi_yaz / ham_kayitlari_oku     ← data/raw disk biçimi
    topla                             ← `make crawl` giriş noktası

TARİHÇE — neden banka başına kod var (26 Ağu 2026):
    v0'da tek jenerik httpx toplayıcı vardı: sitemap + seed URL'den 2 seviye
    derinlik. Katılım bankalarının kampanya listeleri JavaScript ile render
    edilip «daha fazla yükle» butonuyla sayfalandığı için o yol kartların
    çoğunu hiç göremiyordu. `data/raw` altındaki kayıtları fiilen üreten şey
    Selenium kazıyıcılarıydı; kod ise hâlâ jenerik toplayıcıyı gösteriyordu.
    Jüriye anlatılan mimari ile veriyi üreten mimari ayrı olduğu için jenerik
    yol kaldırıldı, kazıyıcılar depoya alındı. Ayrıntı: docs/VERI_METODOLOJISI.md

Toplama disiplini (docs/kanit/VERI_TOPLAMA_ETIGI.md ile aynı, jüri okuyacak):
  - robots.txt kontrolü zorunlu, crawl-delay uygulanır
  - İstek arası en az 2 saniye, eşzamanlı istek yok
  - Tanımlı User-Agent, iletişim adresiyle
  - Yalnız kamuya açık sayfalar; giriş gerektiren hiçbir alan yok
  - Kişisel veri toplanmaz (KVKK)
"""

from __future__ import annotations

import json
import logging
import time
import urllib.robotparser
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin, urlparse

import httpx
import yaml

from src.schema import Banka, HamKayit

if TYPE_CHECKING:  # yalnız tip denetimi için — selenium'u içeri çekmez
    from src.collector.temel_kaziyici import IlerlemeGeriCagrisi

log = logging.getLogger(__name__)

KOK = Path(__file__).resolve().parents[2]
BANKS_YAML = KOK / "data" / "banks.yaml"
HAM_DIZIN = KOK / "data" / "raw"
DEMO_HAM_DIZIN = KOK / "data" / "demo_raw"
"""Arayüzdeki «Canlı Boru Hattı» sayfasının yazdığı alan.

Üretim verisinden AYRI tutuluyor: demo koşusu banka başına birkaç sayfa
çeker ve o kırpılmış çıktı `data/raw`'un üstüne yazarsa, ambar sessizce
eksik hâle gelir. Türetilmiş ve atılabilir — `.gitignore`'da.
"""

KULLANICI_AJANI = "TEKNOFEST-2026-SVARTAL-Bot (+kendireren722@gmail.com)"
ISTEK_ARASI_SANIYE = 2.0
ROBOTS_ZAMAN_ASIMI = 10.0  # robots.txt çekimi; sayfa zaman aşımı tarayici.py'de
EN_AZ_GOVDE_UZUNLUGU = 200  # bundan kısa metinler kampanya sayfası değildir


# ---------------------------------------------------------------------------
# Kayıt defteri
# ---------------------------------------------------------------------------


def bankalari_yukle(yol: Path = BANKS_YAML) -> list[Banka]:
    """banks.yaml'i doğrulanmış Banka nesnelerine çevirir."""
    ham = yaml.safe_load(yol.read_text(encoding="utf-8")) or []
    return [Banka.model_validate(kayit) for kayit in ham]


def faal_bankalar(bankalar: list[Banka] | None = None) -> list[Banka]:
    """Yalnız kampanya beklenen bankalar. Diğerleri kayıt defterinde kalır."""
    return [b for b in (bankalar or bankalari_yukle()) if b.kampanya_beklenir_mi]


# ---------------------------------------------------------------------------
# Nezaket katmanı
# ---------------------------------------------------------------------------


class RobotsBekcisi:
    """Alan adı başına robots.txt kuralları ve crawl-delay yönetimi."""

    def __init__(self, kullanici_ajani: str = KULLANICI_AJANI) -> None:
        self.kullanici_ajani = kullanici_ajani
        self._ayristiricilar: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def _ayristirici(self, url: str) -> urllib.robotparser.RobotFileParser | None:
        parcalar = urlparse(url)
        alan = f"{parcalar.scheme}://{parcalar.netloc}"
        if alan in self._ayristiricilar:
            return self._ayristiricilar[alan]

        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(urljoin(alan, "/robots.txt"))
        try:
            with httpx.Client(timeout=ROBOTS_ZAMAN_ASIMI, follow_redirects=True) as istemci:
                yanit = istemci.get(
                    urljoin(alan, "/robots.txt"),
                    headers={"User-Agent": self.kullanici_ajani},
                )
            if yanit.status_code == 200:
                rp.parse(yanit.text.splitlines())
            else:
                # robots.txt yoksa erişim serbesttir (RFC 9309)
                rp.allow_all = True
        except httpx.HTTPError as hata:
            log.warning("robots.txt okunamadı (%s): %s — temkinli davranılıyor", alan, hata)
            rp = None

        self._ayristiricilar[alan] = rp
        return rp

    def izinli_mi(self, url: str) -> bool:
        rp = self._ayristirici(url)
        if rp is None:
            return False  # okuyamadıysak çekmiyoruz; temkinli taraf
        return rp.can_fetch(self.kullanici_ajani, url)

    def bekleme_suresi(self, url: str) -> float:
        """robots.txt crawl-delay değeri ile kendi alt sınırımızın büyüğü."""
        rp = self._ayristirici(url)
        gecikme = None
        if rp is not None:
            try:
                gecikme = rp.crawl_delay(self.kullanici_ajani)
            except AttributeError:
                gecikme = None
        return max(float(gecikme or 0.0), ISTEK_ARASI_SANIYE)


class NezaketSirasi:
    """Alan adı başına tek sıra: iki istek arasına asgari süreyi koyar.

    Eşzamanlı istek YOKTUR — sıra tek iş parçacığında ilerler. `docs/kanit/
    VERI_TOPLAMA_ETIGI.md` bunu «alan adı başına tek sıra» diye beyan eder;
    beyanı uygulayan kod burasıdır.
    """

    def __init__(self, bekci: RobotsBekcisi | None = None) -> None:
        self.bekci = bekci or RobotsBekcisi()
        self._son_istek: dict[str, float] = {}

    def bekle(self, url: str) -> None:
        alan = urlparse(url).netloc
        gecikme = self.bekci.bekleme_suresi(url)
        gecen = time.monotonic() - self._son_istek.get(alan, 0.0)
        if gecen < gecikme:
            time.sleep(gecikme - gecen)
        self._son_istek[alan] = time.monotonic()


# ---------------------------------------------------------------------------
# Diske yazma
# ---------------------------------------------------------------------------


def kaydi_yaz(kayit: HamKayit, dizin: Path = HAM_DIZIN) -> Path:
    """Ham anlık görüntüyü diske yazar. HTML ayrı dosyada — JSON'u şişirmesin."""
    banka_dizin = dizin / kayit.banka_kodu
    banka_dizin.mkdir(parents=True, exist_ok=True)
    kimlik = kayit.kampanya_id()

    (banka_dizin / f"{kimlik}.html").write_text(kayit.ham_html, encoding="utf-8")

    ust_veri = kayit.model_dump(mode="json", exclude={"ham_html"})
    yol = banka_dizin / f"{kimlik}.json"
    yol.write_text(json.dumps(ust_veri, ensure_ascii=False, indent=2), encoding="utf-8")
    return yol


def ham_kayitlari_oku(dizin: Path = HAM_DIZIN) -> Iterator[HamKayit]:
    """Diske yazılmış ham kayıtları geri okur (çıkarım katmanının girdisi)."""
    for yol in sorted(dizin.rglob("*.json")):
        veri = json.loads(yol.read_text(encoding="utf-8"))
        html_yolu = yol.with_suffix(".html")
        veri["ham_html"] = html_yolu.read_text(encoding="utf-8") if html_yolu.exists() else ""
        yield HamKayit.model_validate(veri)


# ---------------------------------------------------------------------------
# Toplama akışı
# ---------------------------------------------------------------------------


def topla(
    bankalar: list[Banka] | None = None,
    *,
    gorunmez: bool | None = None,
    ilerleme: IlerlemeGeriCagrisi | None = None,
    dizin: Path = HAM_DIZIN,
    azami_sayfa: int | None = None,
    iptal: Callable[[], bool] | None = None,
) -> int:
    """`make crawl` giriş noktası. Diske yazılan sayfa sayısını döner.

    Tek tarayıcı oturumu tüm bankalar için kullanılır: her banka için ayrı
    Chrome açmak makinede ~4 sn/banka bedel ve gereksiz bellek demek.

    `ilerleme` verilirse toplama olayları oraya akar (arayüzün aşama
    göstergesi bunun üzerine kurulacak). Verilmezse yalnız günlüğe yazılır.

    `azami_sayfa` BANKA BAŞINA yazılan sayfa tavanıdır — arayüzdeki demo
    kipinin tek fren mekanizması. NEZAKETİ DEĞİL ADEDİ kısar: istek arası
    süre ve robots kapısı demo kipinde de aynen işler (`NezaketSirasi`).
    Tavan yalnız çekilen sayfa sayısını sınırlar, URL keşfini değil —
    liste yine tam yüklenir, çünkü `tara()` üreteci sayfa sayısını ancak
    listeyi gördükten sonra bilir.

    `iptal` her banka öncesinde ve her sayfadan sonra yoklanır. `True`
    dönerse döngüden ÇIKILIR; iş parçacığı öldürülmez, `finally` sürücüyü
    her hâlükârda kapatır. Yarıda kesilen bir Chrome süreci makinede asılı
    kalırdı — işbirlikçi durdurmanın sebebi bu.

    İkisi de `None` iken kod yolu bugünküyle birebir aynıdır; `make crawl`
    bu eklemelerden etkilenmez.

    selenium yalnız BURADA içeri alınır: `bankalari_yukle` gibi hafif
    yardımcıları çağıran arayüz ve testler tarayıcı bağımlılığı olmadan
    çalışabilsin diye.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    from src.collector.kaziyicilar import kaziyici_sinifi
    from src.collector.tarayici import surucu_olustur

    hedefler = faal_bankalar(bankalar)
    if not hedefler:
        log.warning("Kampanya beklenen banka yok — toplama yapılmadı.")
        return 0

    bekci = RobotsBekcisi()
    sira = NezaketSirasi(bekci)
    toplam = 0

    def _iptal_edildi() -> bool:
        return iptal is not None and iptal()

    log.info("Tarayıcı başlatılıyor...")
    surucu, bekleme = surucu_olustur(gorunmez=gorunmez)
    try:
        for banka in hedefler:
            if _iptal_edildi():
                log.info("Toplama iptal edildi — kalan bankalara girilmiyor.")
                break

            sinif = kaziyici_sinifi(banka.kod)
            if sinif is None:
                log.warning(
                    "%-22s kazıyıcısı yok (kod %s) — atlanıyor", banka.kisa_ad, banka.kod
                )
                continue

            kaziyici = sinif(
                banka, surucu, bekleme, bekci=bekci, sira=sira, ilerleme=ilerleme
            )
            sayac = 0
            # Üreteç ELDE tutuluyor: tavana varıp `break` ettiğimizde
            # `close()` çağrılabilsin diye. Çöp toplayıcıya bırakılırsa
            # kazıyıcı yarım kalmış hâlde belirsiz bir zamanda kapanır.
            uretec = kaziyici.tara()
            try:
                for kayit in uretec:
                    kaydi_yaz(kayit, dizin)
                    sayac += 1
                    if azami_sayfa is not None and sayac >= azami_sayfa:
                        log.info(
                            "%-22s sayfa tavanı (%d) doldu — bu banka kesiliyor",
                            banka.kisa_ad, azami_sayfa,
                        )
                        break
                    if _iptal_edildi():
                        log.info("%-22s iptal edildi", banka.kisa_ad)
                        break
            finally:
                uretec.close()
            log.info("%-22s %3d sayfa", banka.kisa_ad, sayac)
            toplam += sayac
    finally:
        log.info("Tarayıcı kapatılıyor...")
        surucu.quit()

    log.info("TOPLAM: %d sayfa, %d banka", toplam, len(hedefler))
    return toplam


def __getattr__(ad: str) -> Any:
    """Kaldırılan jenerik toplayıcıyı sessizce `None` yapmamak için.

    `Toplayici` sınıfı 26 Ağu 2026'da kaldırıldı. Eski bir içe aktarma
    kalırsa `AttributeError` yerine ne olduğunu anlatan bir hata verilsin.
    """
    if ad == "Toplayici":
        raise AttributeError(
            "Jenerik httpx toplayıcısı (`Toplayici`) kaldırıldı — kampanya "
            "sayfaları JS ile render edildiği için kartların çoğunu göremiyordu. "
            "Yerine banka başına Selenium kazıyıcıları geçti: "
            "`src.collector.kaziyicilar`. Toplama için `topla()` kullanın."
        )
    raise AttributeError(f"module {__name__!r} has no attribute {ad!r}")


if __name__ == "__main__":
    topla()
