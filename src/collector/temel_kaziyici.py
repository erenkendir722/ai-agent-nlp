"""Kazıyıcı taban sınıfı — banka başına DEĞİŞEN tek şey URL keşfidir.

Tasarım: her bankanın kampanya listesi farklı biçimde sayfalanıyor (kimi
«daha fazla yükle» butonu, kimi sekme, kimi düz liste). Bu farklılık alt
sınıfların `kampanya_urlleri()` gövdesinde toplanır. Bulunan URL'lerin
gezilmesi, nezaket, robots kapısı, gövde ayıklama ve `HamKayit` üretimi
burada TEK yerdedir — dokuz kazıyıcıda dokuz kez yazılmaz.

Toplama disiplini (docs/kanit/VERI_TOPLAMA_ETIGI.md ile aynı, jüri okuyacak):
  - Her kampanya URL'i çekilmeden önce robots.txt'e sorulur
  - Alan adı başına tek sıra, istek arası en az `ISTEK_ARASI_SANIYE`
  - Tanımlı User-Agent, iletişim adresiyle
  - Yalnız kamuya açık sayfalar; giriş gerektiren hiçbir alan yok
  - Kişisel veri toplanmaz (KVKK)

HTTP DURUM KODU HAKKINDA: Selenium yanıtın durum kodunu vermez. Sayfa
gövdesi yüklendiyse `http_durum=200` yazılır ve bu «sayfa yüklendi»
demektir, «sunucu 200 döndü» demek DEĞİLDİR. Kayıtta uydurma değer
taşımamak için başka bir kod da uydurulmaz; yüklenemeyen sayfa hiç
kaydedilmez.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Literal

import trafilatura
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.collector.toplayici import (
    EN_AZ_GOVDE_UZUNLUGU,
    NezaketSirasi,
    RobotsBekcisi,
)
from src.schema import Banka, HamKayit

log = logging.getLogger(__name__)

SAYFA_YERLESME_SANIYE = 2.0
"""Gövde belirdikten sonra JS'in kalanını yazması için beklenen süre."""

AZAMI_YUKLE_TIKLAMASI = 100
"""«Daha fazla yükle» için sert üst sınır.

Buton görünür kalıp yeni kart getirmediğinde döngü sonsuza gider. Ölçülen
en kalabalık liste 217 kayıt; 100 tıklama fazlasıyla yeter, sonsuz döngüden
ise ucuz kurtarır.
"""

AZAMI_ARTIS_BEKLEMESI = 10.0
"""Tıklamanın kartları getirmesi için beklenecek AZAMİ süre (sn).

Azami, sabit değil: artış gelir gelmez beklenmeden devam edilir. Yalnız
liste gerçekten bittiğinde bu sürenin tamamı harcanır.
"""

ARTIS_YOKLAMA_ARALIGI = 0.5
"""Kart sayısı iki yoklama arasında bu kadar beklenir (sn)."""

ARTIS_SONRASI_DINLENME = 1.5
"""Parti indikten sonra bir sonraki tıklamaya kadar beklenen süre (sn).

Artışı yoklayarak beklemek döngüyü hızlandırdı; art arda çok hızlı tıklamak
sitenin isteklerinden birini düşürmesine zemin hazırlıyor. Hem nezaket hem
kayıp oranı için tempo kasten yavaşlatılır.
"""

CEREZ_KATMANI_SECICILER = (
    "cookie",
    "cerez",
    "consent",
    "kvkk",
    "onetrust",
)
"""Çerez onay katmanını tanıtan sınıf/kimlik parçaları.

DAR TUTULUR. Buraya «modal», «popup», «overlay» gibi genel sözcükler
EKLENMEZ: onlar içerik taşıyan bileşenlerin de adıdır ve eklenirse gerçek
kampanya metni sessizce silinir. Ölçüt «gizli mi» de değil — bkz.
`TemelKaziyici.cerez_katmanini_kaldir` gövdesindeki ölçüm.
"""

CEREZ_KATMANI_JS = """
var parcalar = %s;
var secici = parcalar.map(function (p) {
    return "[class*='" + p + "'],[id*='" + p + "']";
}).join(",");
var atilan = 0;
document.querySelectorAll(secici).forEach(function (oge) {
    if (oge.parentNode) { oge.parentNode.removeChild(oge); atilan++; }
});
return atilan;
""" % list(CEREZ_KATMANI_SECICILER)


Asama = Literal["url_kesfi", "sayfa", "atlandi", "hata", "bitti"]


@dataclass(frozen=True)
class Ilerleme:
    """Kazıma sırasında dışarı bildirilen tek olay.

    Toplama aşamaları arayüzde gösterilecek; bu yüzden ilerleme `print` ile
    değil geri çağrıyla akar. Aynı kazıyıcı hem CLI'dan hem Streamlit'ten
    sürülebilsin diye kazıyıcı ekrana hiçbir şey yazmaz.
    """

    banka_kodu: str
    banka_adi: str
    asama: Asama
    sira: int = 0
    toplam: int = 0
    url: str = ""
    mesaj: str = ""


IlerlemeGeriCagrisi = Callable[[Ilerleme], None]


class TemelKaziyici:
    """Tek bankanın kampanya sayfalarını gezip `HamKayit` üretir."""

    BANKA_KODU: ClassVar[str] = ""
    """`data/banks.yaml` içindeki EFT kodu. Kayıt defteriyle bağı bu kurar."""

    def __init__(
        self,
        banka: Banka,
        surucu: WebDriver,
        bekleme: WebDriverWait,
        *,
        bekci: RobotsBekcisi | None = None,
        sira: NezaketSirasi | None = None,
        ilerleme: IlerlemeGeriCagrisi | None = None,
    ) -> None:
        if banka.kod != self.BANKA_KODU:
            raise ValueError(
                f"{type(self).__name__} banka kodu {self.BANKA_KODU} bekliyor, "
                f"{banka.kod} verildi — kayıt defteri ile kazıyıcı eşleşmiyor."
            )
        self.banka = banka
        self.surucu = surucu
        self.bekleme = bekleme
        self.bekci = bekci or RobotsBekcisi()
        self.sira = sira or NezaketSirasi(self.bekci)
        self._ilerleme = ilerleme

    # -- Dışarıya bildirim ------------------------------------------------

    def _bildir(self, asama: Asama, **ayrinti: Any) -> None:
        if self._ilerleme is None:
            return
        self._ilerleme(
            Ilerleme(
                banka_kodu=self.banka.kod,
                banka_adi=self.banka.kisa_ad,
                asama=asama,
                **ayrinti,
            )
        )

    # -- Başlangıç adresleri ---------------------------------------------

    @property
    def liste_urlleri(self) -> tuple[str, ...]:
        """Kazımanın başladığı adresler — `data/banks.yaml` · `seed_urls`.

        URL'ler kazıyıcıda DEĞİL kayıt defterinde durur. İki gerekçe:
        `tools/robots_kanit.py` robots kanıtını `seed_urls` üzerinden üretiyor,
        yani liste burada tutulmazsa kanıt fiilen çekilen adresleri denetlemez;
        ayrıca banka sitesi adres değiştirdiğinde düzeltme Python dosyasına
        değil YAML'a düşer.

        Boş liste hata sayılır: sessizce sıfır kayıt üretip «kampanya yok»
        görüntüsü vermek, kırıldığını söylemeyen en pahalı hata biçimidir.
        """
        if not self.banka.seed_urls:
            raise ValueError(
                f"{self.banka.kisa_ad} ({self.banka.kod}) için `seed_urls` boş — "
                "data/banks.yaml doldurulmalı."
            )
        return tuple(self.banka.seed_urls)

    # -- Alt sınıfın dolduracağı tek yer ---------------------------------

    def kampanya_urlleri(self) -> list[str]:
        """Kampanya DETAY sayfalarının URL'leri. Alt sınıf uygular."""
        raise NotImplementedError

    # -- Ortak tarayıcı yardımcıları -------------------------------------

    def acilir_pencereleri_kapat(self) -> None:
        """Çerez onayı ve benzeri örtüleri kapatır.

        Bulunamaması hata değildir: her sitede çerez katmanı yok, olan da her
        zaman aynı sınıf adını kullanmıyor. Burada yutulan istisna VERİ hatası
        değil, İSTEĞE BAĞLI bir arayüz etkileşiminin başarısızlığıdır — kayıt
        üretimini etkilemez, o yüzden `debug` seviyesinde geçilir.
        """
        adaylar = [
            "//*[contains(@class, 'accept-cookie')]",
            "//*[contains(@class, 'cookie-accept')]",
            "//*[contains(@class, 'cookie')]//a[contains(text(), 'Kabul') or contains(text(), 'KABUL')]",
            "//*[contains(@class, 'cookie')]//button[contains(text(), 'Kabul') or contains(text(), 'KABUL')]",
            "//*[contains(@id, 'onetrust-accept')]",
        ]
        for xpath in adaylar:
            try:
                dugmeler = self.surucu.find_elements(By.XPATH, xpath)
            except WebDriverException as hata:
                log.debug("çerez düğmesi aranamadı (%s): %s", xpath, hata)
                continue
            for dugme in dugmeler:
                try:
                    if not dugme.is_displayed():
                        continue
                    self.surucu.execute_script("arguments[0].click();", dugme)
                except WebDriverException as hata:
                    log.debug("çerez düğmesine tıklanamadı: %s", hata)
                    continue
                time.sleep(1)
                return

    def cerez_katmanini_kaldir(self) -> int:
        """Çerez onay katmanını DOM'dan siler. Atılan öge sayısını döner.

        NEDEN GEREKLİ — 28 Ağustos'ta ölçüldü, Dünya Katılım:
        Dört finansman sayfası gövde olarak **6971 karakterlik ÇEREZ
        AYDINLATMA METNİ** üretiyordu. Sayfa doğruydu (`<title>` «İşletme
        Finansmanı | Dünya Katılım»), ürün metni de DOM'da duruyordu; kusur
        trafilatura'nın ana içerik seçimindeydi — gizli duran onay modalı
        gerçek içerikten uzun olduğu için «ana içerik» seçiliyordu.

        Zararsız değildi: kayıt KVKK çerez metnini taşıyıp finansman sayılır,
        çıkarım o metinden alan üretir ve ortaya kaynak alıntılı, güvenilir
        görünen uydurma bir finansman ürünü çıkardı. Ziraat'in liste
        sayfalarıyla aynı hata biçimi (bkz. `tools/liste_sayfalarini_ele.py`).

        NEDEN «GÖRÜNMEYEN HER ÖGEYİ AT» DEĞİL — o da denendi, ölçüldü, geri
        alındı. `offsetParent === null` olan her ögeyi atmak bozuk sayfayı
        düzeltiyor ama SAĞLAM sayfaları kırpıyordu:

            Dünya · araç finansmanı      3461 -> 2379   (sağlam sayfa küçüldü)
            Vakıf · konut finansmanı     6312 -> 5204   «murabaha» DÜŞTÜ

        Vakıf'ta düşen şey tam da `mask-area-open-btn` arkasındaki SSS metni,
        yani korunması gereken içerik. Ölçüt görünürlük olamaz: kapalı akordeon
        da görünmez, ama içeriktir.

        Dar seçici ile ölçüm (aynı dört sayfa):

            Dünya · işletme finansmanı   6971 -> 569    çerez metni gitti
            Dünya · enerya karz-ı hasen  6971 -> 1524   çerez metni gitti
            Dünya · araç finansmanı      3461 -> 3461   DEĞİŞMEDİ
            Vakıf · konut finansmanı     6312 -> 6001   maskeli içerik DURUYOR

        Sözcük dağarcığı `acilir_pencereleri_kapat` ile aynı ailedendir;
        ikisi ayrı işler yapar: o TIKLAR (örtüyü kapatır), bu SİLER (kapatılsa
        da DOM'da kalan onay metnini ana içerik yarışından çıkarır). Kabul
        tıklaması modalı DOM'dan kaldırmıyor — ölçüldü, tıklamadan sonra da
        6971 geliyordu.
        """
        try:
            atilan = self.surucu.execute_script(CEREZ_KATMANI_JS)
        except WebDriverException as hata:
            # Veri hatası değil: sayfa çerez katmanı taşımıyor olabilir ya da
            # JS çalıştırılamamıştır. Gövde ayıklaması yine de yapılır.
            log.debug("çerez katmanı kaldırılamadı: %s", hata)
            return 0
        return int(atilan or 0)

    def sayfayi_ac(self, url: str) -> None:
        """Liste sayfasını nezaket ve robots kapısından geçirerek açar."""
        if self.banka.robots_kontrol and not self.bekci.izinli_mi(url):
            raise PermissionError(f"robots.txt liste sayfasını reddetti: {url}")
        self.sira.bekle(url)
        self.surucu.get(url)

    def _kaydir_sona(self) -> None:
        try:
            self.surucu.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        except WebDriverException as hata:
            log.debug("sayfa kaydırılamadı: %s", hata)

    def _tikla(self, oge: Any) -> bool:
        """Önce gerçek tıklama, olmazsa JS tıklaması. Başarıyı döner."""
        try:
            oge.click()
            return True
        except WebDriverException:
            pass
        try:
            self.surucu.execute_script("arguments[0].click();", oge)
            return True
        except WebDriverException as hata:
            log.debug("düğmeye tıklanamadı: %s", hata)
            return False

    def _artisi_bekle(
        self, oge_xpath: str, onceki: int, azami_saniye: float
    ) -> int | None:
        """Tıklamadan sonra kart sayısı ARTANA DEK bekler; artınca hemen döner.

        Dönen değer yeni kart sayısıdır; sayım yapılamazsa `None`.

        SABİT SÜRE BEKLEMEK YETMİYOR — ölçüldü (Albaraka, 26 Ağustos). Eski kod
        tıkladıktan sonra 2 saniye bekleyip kartları BİR KEZ sayıyordu. Parti o
        pencerede gelmezse tur «artış olmadı» sayılıyor, döngü bir sonraki tura
        geçip YENİDEN tıklıyordu. Sitenin iç sayfa sayacı ilerlediği için
        atlanan partinin dokuz kartı bir daha hiç gelmiyordu:

            tur 1: 9 -> 9      ← tıklama gitti, kartlar 2 sn'de yetişmedi
            tur 2: 9 -> 18
            ...
            tur 5: 36 -> 39    ← son parti 9 yerine 3
            düğme kayboldu     → 48 yerine 39 kampanya, HATA VERMEDEN

        Altı koşumda ikisi eksik döndü (39 ve 27). Bu yüzden ölçüt SÜRE değil
        ARTIŞ: bir sonraki tıklama, öncekinin kartları gelmeden yapılmaz.
        """
        biti = time.monotonic() + azami_saniye
        while True:
            try:
                sayi = len(self.surucu.find_elements(By.XPATH, oge_xpath))
            except WebDriverException as hata:
                log.debug("liste sayılamadı: %s", hata)
                return None
            if sayi > onceki or time.monotonic() >= biti:
                return sayi
            time.sleep(ARTIS_YOKLAMA_ARALIGI)

    def hepsini_yukle(
        self,
        oge_xpath: str,
        dugme_xpath: str,
        *,
        bekleme_saniye: float = AZAMI_ARTIS_BEKLEMESI,
        azami_bos_tur: int = 3,
    ) -> bool:
        """«Daha fazla yükle» düğmesine kart sayısı artmayı bırakana dek basar.

        Düğmenin kaybolmasını beklemek yetmiyor: bazı sitelerde düğme son
        sayfadan sonra da görünür kalıyor. Bu yüzden asıl ölçüt KART SAYISI —
        art arda `azami_bos_tur` turda artmıyorsa liste bitmiştir.

        `bekleme_saniye` bir tıklamanın kartlarının beklenebileceği AZAMİ
        süredir, sabit gecikme değil: artış gelir gelmez devam edilir
        (`_artisi_bekle`, orada neden böyle olduğu yazılı).

        DÖNEN DEĞER liste temiz yüklendiğinde `True`'dur. Bir tıklama yutulup
        o partinin kartları hiç gelmediyse `False` döner — bkz.
        `listeyi_tamamla`. Kayıp şöyle ayırt edilir: SONU boş turlarla biten
        liste normaldir (site tükendi), ama ARASINDA boş tur olup sonra
        yeniden artan liste bir parti kaybetmiştir.
        """
        bos_tur = 0
        kayip_aday = False
        parti_kaybedildi = False
        for _ in range(AZAMI_YUKLE_TIKLAMASI):
            if bos_tur >= azami_bos_tur:
                return not parti_kaybedildi
            self._kaydir_sona()
            time.sleep(2)

            try:
                onceki = len(self.surucu.find_elements(By.XPATH, oge_xpath))
                dugmeler = [
                    d
                    for d in self.surucu.find_elements(By.XPATH, dugme_xpath)
                    if d.is_displayed()
                ]
            except WebDriverException as hata:
                log.debug("liste/düğme sayılamadı: %s", hata)
                return not parti_kaybedildi

            if not dugmeler:
                return not parti_kaybedildi
            if not self._tikla(dugmeler[0]):
                return not parti_kaybedildi

            sonraki = self._artisi_bekle(oge_xpath, onceki, bekleme_saniye)
            if sonraki is None:
                return not parti_kaybedildi

            if sonraki > onceki:
                time.sleep(ARTIS_SONRASI_DINLENME)
                if kayip_aday:
                    # Boş turdan SONRA yeniden arttı: o tıklama yutulmuş, ama
                    # sitenin sayfa sayacı ilerlemiş. Bir parti eksik kalacak.
                    parti_kaybedildi = True
                    kayip_aday = False
                bos_tur = 0
            else:
                kayip_aday = True
                bos_tur += 1
        else:
            log.warning(
                "%s: «daha fazla yükle» %d tıklamada bitmedi, kesiliyor",
                self.banka.kisa_ad,
                AZAMI_YUKLE_TIKLAMASI,
            )
        return not parti_kaybedildi

    def _oturumu_tazele(self) -> None:
        """Yeniden denemeden önce tarayıcı oturumunu temizler.

        Kayıp aynı oturumda üst üste tekrarlanabiliyor: ölçümde bir koşumun üç
        denemesi de 39'da bitti. Çerez ve önbellek denemeler arasında taşındığı
        için sayfa aynı duruma düşüyor olabilir; bu yüzden oturum sıfırlanır.
        Temizlik başarısız olursa deneme yine de yapılır — bu iyileştirmedir,
        veri üretiminin koşulu değildir.
        """
        try:
            self.surucu.delete_all_cookies()
        except WebDriverException as hata:
            log.debug("çerezler silinemedi: %s", hata)
        try:
            self.surucu.execute_cdp_cmd("Network.clearBrowserCache", {})  # type: ignore[attr-defined]
        except Exception as hata:  # noqa: BLE001 - CDP yalnız Chrome'da var
            log.debug("önbellek temizlenemedi: %s", hata)
        try:
            self.surucu.get("about:blank")
        except WebDriverException as hata:
            log.debug("boş sayfaya gidilemedi: %s", hata)

    def listeyi_tamamla(
        self,
        hazirla: Callable[[], None],
        oge_xpath: str,
        dugme_xpath: str,
        *,
        azami_deneme: int = 3,
        **yukleme: Any,
    ) -> None:
        """Listeyi eksiksiz yükler; parti kaybı olursa baştan dener.

        Kaybı yerinde ONARMAK mümkün değil: yutulan tıklama sitenin iç sayfa
        sayacını ilerletiyor, o partinin kartları aynı oturumda bir daha
        gelmiyor (ölçüldü — Albaraka, 26 Ağustos; 48 kampanyalık liste 39'da
        bitiyordu). Tek çare listeyi baştan yüklemek, o yüzden `hazirla`
        sayfayı yeniden açan çağrılabilir olmalı.

        Denemeler tükenirse SESSİZ KALINMAZ: uyarı basılır ve ilerleme akışına
        düşer. Eksik liste, hiçbir şey söylemediği için «o bankada az kampanya
        var» gibi görünür — bu projenin en pahalı bulduğu hata biçimi.
        """
        for deneme in range(1, azami_deneme + 1):
            if deneme > 1:
                self._oturumu_tazele()
            hazirla()
            if self.hepsini_yukle(oge_xpath, dugme_xpath, **yukleme):
                return
            log.warning(
                "%s: liste yüklenirken bir parti kayboldu (deneme %d/%d), baştan alınıyor",
                self.banka.kisa_ad,
                deneme,
                azami_deneme,
            )
        mesaj = f"{azami_deneme} denemede de eksik yüklendi — liste eksik olabilir"
        log.warning("%s: %s", self.banka.kisa_ad, mesaj)
        self._bildir("hata", mesaj=mesaj)

    def baglantilari_topla(self, js: str) -> list[str]:
        """Sayfadaki GÖRÜNÜR bağlantıları JS ile toplar.

        JS tarafında `offsetParent === null` denetimi gizli ögeyi eler: kapalı
        sekmedeki kartlar DOM'da durur ama o listeye ait değildir.
        """
        sonuc = self.surucu.execute_script(js) or []
        return [str(u) for u in sonuc if u]

    def xpath_baglantilari(self, xpath: str) -> list[str]:
        """XPath ile eşleşen `<a>` ögelerinin `href` değerleri."""
        return [
            href
            for oge in self.surucu.find_elements(By.XPATH, xpath)
            if (href := oge.get_attribute("href"))
        ]

    # -- Ana akış ---------------------------------------------------------

    def urun_urlleri(self) -> list[str]:
        """Finansman ÜRÜN sayfaları — `banka.urun_bolumleri` altındaki bağlantılar.

        BANKA BAŞINA KOD YOK, bilerek: dokuz kazıyıcının dokuzunda da kural
        aynı — bölüm kökünün altındaki bağlantıları topla. Değişen tek şey
        kökün kendisi ve o `banks.yaml`'da (bkz. `Banka.urun_bolumleri`).
        Kampanya listelerinde durum farklıydı — orada her banka kendi kart
        bileşenini kullanıyor ve seçici paylaşılamıyor; ürün bölümleri düz
        gezinme menüleri olduğu için tek bir kural yetiyor.

        SÜZGEÇ KÖKÜN KENDİSİDİR: yalnız kökle BAŞLAYAN adresler alınır, yani
        menüdeki «iletişim», «hakkımızda» bağlantıları kendiliğinden düşer.
        Kökün kendisi de listeye girer (bölüm sayfası çoğu bankada ürünü de
        anlatıyor); yinelenenleri `benzersiz` atar.

        Bölüm tanımlanmamışsa boş döner ve davranış eskisiyle birebir aynıdır.
        """
        if not self.banka.urun_bolumleri:
            return []
        bulunan: list[str] = []
        for kok in self.banka.urun_bolumleri:
            try:
                self.sayfayi_ac(kok)
            except Exception as hata:
                # Bölüm açılamazsa KAMPANYA tarafı düşmez: ürün keşfi ek bir
                # kademedir, tek bir bölümün erişilemez olması dokuz bankalık
                # koşuyu iptal ettirmemeli. Hata YUTULMAZ, uyarı olarak yazılır.
                #
                # `except Exception` DAR YAZILAMAZ, ölçüldü: burada
                # `WebDriverException` bekleniyordu ama gelen
                # `urllib3.exceptions.ReadTimeoutError` oldu — chromedriver'ın
                # HTTP istemcisi, Selenium'un kendi zaman aşımından önce
                # kırılıyordu (bkz. `tarayici.SAYFA_ZAMAN_ASIMI`). Tip listesi
                # tutmak, bu katmandan çıkabilecek her kütüphanenin istisna
                # ağacını bilmeyi gerektirirdi; burada önemli olan hatanın
                # TİPİ değil, ürün keşfinin İSTEĞE BAĞLI bir kademe olması.
                log.warning("%s: ürün bölümü açılamadı (%s): %s",
                            self.banka.kisa_ad, kok, hata)
                continue
            time.sleep(3)
            self.acilir_pencereleri_kapat()
            bulunan.append(kok)
            bulunan += [
                u for u in self.xpath_baglantilari("//a[@href]")
                if u.split("#")[0].split("?")[0].startswith(kok)
            ]
        return benzersiz(bulunan)

    def tara(self) -> Iterator[HamKayit]:
        """Kampanya ve ÜRÜN sayfalarını gezip ham kayıt üretir."""
        self._bildir("url_kesfi", mesaj=f"{self.banka.kisa_ad}: kampanya listesi taranıyor")
        urller = benzersiz(self.kampanya_urlleri() + self.urun_urlleri())
        toplam = len(urller)
        log.info("%-22s %3d kampanya bağlantısı bulundu", self.banka.kisa_ad, toplam)
        self._bildir("url_kesfi", toplam=toplam, mesaj=f"{toplam} kampanya bağlantısı")

        uretilen = 0
        for sira, url in enumerate(urller, 1):
            kayit = self._sayfayi_cek(url, sira, toplam)
            if kayit is not None:
                uretilen += 1
                yield kayit

        self._bildir(
            "bitti",
            sira=uretilen,
            toplam=toplam,
            mesaj=f"{self.banka.kisa_ad}: {uretilen}/{toplam} kayıt",
        )

    def sayfa_kaydi(self, url: str) -> HamKayit | None:
        """Tek sayfayı kayda çevirir — liste keşfi olmadan.

        `tara()` kampanya listesini gezip bulduğu her adresi çeker. Elde
        ZATEN adres varsa (bkz. `data/seed/finansman_urlleri.txt`) o keşif
        adımının karşılığı yok; çekilecek tek şey sayfanın kendisi.

        Ayrı bir yol DEĞİL: robots kapısı, nezaket sırası, gövde eşiği ve
        `HamKayit` üretimi `_sayfayi_cek`'te tektir ve burası onu çağırır.
        İkinci bir çekme yolu yazılsaydı, iki yol arasındaki her ayrışma
        sessizce farklı disiplinde kayıt üretirdi.

        `sira`/`toplam` ilerleme bildiriminin sayaçları; tek sayfada 1/1.
        """
        return self._sayfayi_cek(url, 1, 1)

    def _sayfayi_cek(self, url: str, sira: int, toplam: int) -> HamKayit | None:
        if self.banka.robots_kontrol and not self.bekci.izinli_mi(url):
            log.info("robots.txt reddetti, atlanıyor: %s", url)
            self._bildir(
                "atlandi", sira=sira, toplam=toplam, url=url, mesaj="robots.txt reddetti"
            )
            return None

        self.sira.bekle(url)
        try:
            self.surucu.get(url)
            self.bekleme.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except WebDriverException as hata:
            log.warning("Sayfa yüklenemedi %s: %s", url, type(hata).__name__)
            self._bildir("hata", sira=sira, toplam=toplam, url=url, mesaj=type(hata).__name__)
            return None

        time.sleep(SAYFA_YERLESME_SANIYE)
        self.cerez_katmanini_kaldir()
        ham_html = self.surucu.page_source
        govde = (
            trafilatura.extract(
                ham_html,
                include_comments=False,
                include_tables=True,
                favor_recall=True,
            )
            or ""
        )

        if len(govde) < EN_AZ_GOVDE_UZUNLUGU:
            log.info("Gövde %d karakter, eleniyor: %s", len(govde), url)
            self._bildir(
                "atlandi",
                sira=sira,
                toplam=toplam,
                url=url,
                mesaj=f"gövde {len(govde)} karakter",
            )
            return None

        baslik = self.surucu.title or None
        self._bildir("sayfa", sira=sira, toplam=toplam, url=url, mesaj=baslik or "")
        return HamKayit(
            banka_kodu=self.banka.kod,
            banka_adi=self.banka.ad,
            url=url,
            cekim_tarihi=datetime.now(),
            http_durum=200,  # bkz. modül başlığı: «sayfa yüklendi» demektir
            baslik=baslik,
            ham_html=ham_html,
            govde_metin=govde,
        )


def benzersiz(urller: list[str]) -> list[str]:
    """Sırayı bozmadan yineleyenleri atar.

    `set()` kullanılmıyor: sıra korunmazsa iki koşunun günlükleri
    karşılaştırılamaz hâle geliyor.
    """
    gorulen: set[str] = set()
    sonuc: list[str] = []
    for url in urller:
        temiz = url.split("#")[0].strip()
        if temiz and temiz not in gorulen:
            gorulen.add(temiz)
            sonuc.append(temiz)
    return sonuc
