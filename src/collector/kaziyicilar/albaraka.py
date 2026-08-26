"""Albaraka Türk (0203) — «daha fazla kampanya» butonu, tek liste sayfası."""

from __future__ import annotations

import logging
import time
from typing import ClassVar

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By

from src.collector.temel_kaziyici import TemelKaziyici

log = logging.getLogger(__name__)

KART_BAGLANTISI = "//*[contains(@class, 'kampanyalar-card')]//h2//a"
DAHA_FAZLA = "//a[contains(@class, 'btn-outline-kampanyalar-primary')]"

TOPLA_JS = """
let links = [];
let items = document.querySelectorAll('.kampanyalar-card h2 a');
for (let a of items) {
    if (a.offsetParent !== null) {
        links.push(a.href);
    }
}
return links;
"""


class AlbarakaKaziyici(TemelKaziyici):
    BANKA_KODU: ClassVar[str] = "0203"

    def acilir_pencereleri_kapat(self) -> None:
        """Albaraka'nın çerez katmanı taban listedeki desenlere uymuyor.

        Örtü, sınıf adında 'cookie' geçen bir kapsayıcı; içindeki onay ögesi
        ne `<button>` ne de bilinen bir sınıf taşıyor. Bu yüzden daha geniş
        bir desen kullanılıyor ve GÖRÜNEN tüm adaylara tıklanıyor.
        """
        xpath = (
            "//*[contains(@class, 'cookie') or contains(translate(text(), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'kabul')]"
        )
        try:
            adaylar = self.surucu.find_elements(By.XPATH, xpath)
        except WebDriverException as hata:
            log.debug("çerez katmanı aranamadı: %s", hata)
            return
        for oge in adaylar:
            try:
                if oge.is_displayed():
                    self.surucu.execute_script("arguments[0].click();", oge)
            except WebDriverException as hata:
                log.debug("çerez ögesine tıklanamadı: %s", hata)

    def kampanya_urlleri(self) -> list[str]:
        self.sayfayi_ac(self.liste_urlleri[0])
        time.sleep(5)
        self.acilir_pencereleri_kapat()
        time.sleep(1)

        self.hepsini_yukle(KART_BAGLANTISI, DAHA_FAZLA, bekleme_saniye=2.0)
        return self.baglantilari_topla(TOPLA_JS)
