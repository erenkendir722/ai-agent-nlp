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

    def hepsini_yukle(
        self,
        oge_xpath: str,
        dugme_xpath: str,
        *,
        bekleme_saniye: float = 3.0,
        azami_bos_tur: int = 3,
    ) -> None:
        """«Daha fazla yükle» düğmesine kart sayısı artmayı bırakana dek basar.

        Düğmenin kaybolmasını beklemek yetmiyor: bazı sitelerde düğme son
        sayfadan sonra da görünür kalıyor. Bu yüzden asıl ölçüt KART SAYISI —
        art arda `azami_bos_tur` turda artmıyorsa liste bitmiştir.
        """
        bos_tur = 0
        for _ in range(AZAMI_YUKLE_TIKLAMASI):
            if bos_tur >= azami_bos_tur:
                return
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
                return

            if not dugmeler:
                return
            if not self._tikla(dugmeler[0]):
                return

            time.sleep(bekleme_saniye)
            try:
                sonraki = len(self.surucu.find_elements(By.XPATH, oge_xpath))
            except WebDriverException as hata:
                log.debug("liste sayılamadı: %s", hata)
                return
            bos_tur = bos_tur + 1 if sonraki <= onceki else 0
        else:
            log.warning(
                "%s: «daha fazla yükle» %d tıklamada bitmedi, kesiliyor",
                self.banka.kisa_ad,
                AZAMI_YUKLE_TIKLAMASI,
            )

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

    def tara(self) -> Iterator[HamKayit]:
        """Kampanya URL'lerini gezip ham kayıt üretir."""
        self._bildir("url_kesfi", mesaj=f"{self.banka.kisa_ad}: kampanya listesi taranıyor")
        urller = benzersiz(self.kampanya_urlleri())
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
