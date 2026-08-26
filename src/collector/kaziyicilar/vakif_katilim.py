"""Vakıf Katılım (0210) — iki liste sayfası, «daha fazla yükle» butonu.

Buradaki döngü tabandaki `hepsini_yukle`'yi KULLANMAZ, bilerek: Vakıf
Katılım'da kart kapsayıcısı sayfalama sırasında yeniden yazılıyor, yani
önceki sayfanın kartları DOM'dan düşebiliyor. Bağlantılar bu yüzden sonda
tek seferde değil, HER TURDA toplanıp biriktirilir. Sonda toplamak, ilk
sayfaların kampanyalarını kaybetmek demek.
"""

from __future__ import annotations

import logging
import time
from typing import ClassVar

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By

from src.collector.temel_kaziyici import AZAMI_YUKLE_TIKLAMASI, TemelKaziyici, benzersiz

log = logging.getLogger(__name__)

KART_BAGLANTISI = "//*[@id='campaign-pagination-page']//a[contains(@class, 'card')]"
DAHA_FAZLA = "//*[@id='load-more-btn']"


class VakifKatilimKaziyici(TemelKaziyici):
    BANKA_KODU: ClassVar[str] = "0210"

    def kampanya_urlleri(self) -> list[str]:
        urller: list[str] = []
        for liste_url in self.liste_urlleri:
            self.sayfayi_ac(liste_url)
            time.sleep(5)
            self.acilir_pencereleri_kapat()
            urller += self._listeyi_gez()
        return benzersiz(urller)

    def _listeyi_gez(self) -> list[str]:
        bulunan: list[str] = []
        bos_tur = 0
        for _ in range(AZAMI_YUKLE_TIKLAMASI):
            if bos_tur >= 3:
                break
            self._kaydir_sona()
            time.sleep(2)

            try:
                onceki = len(self.surucu.find_elements(By.XPATH, KART_BAGLANTISI))
                bulunan += self.xpath_baglantilari(KART_BAGLANTISI)
                dugmeler = [
                    d
                    for d in self.surucu.find_elements(By.XPATH, DAHA_FAZLA)
                    if d.is_displayed()
                ]
            except WebDriverException as hata:
                log.debug("Vakıf Katılım listesi okunamadı: %s", hata)
                break

            if not dugmeler:
                break

            dugme = dugmeler[0]
            try:
                self.surucu.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", dugme
                )
            except WebDriverException as hata:
                log.debug("düğme görünüre getirilemedi: %s", hata)
            time.sleep(1)

            if not self._tikla(dugme):
                break
            time.sleep(3)

            try:
                sonraki = len(self.surucu.find_elements(By.XPATH, KART_BAGLANTISI))
            except WebDriverException as hata:
                log.debug("kart sayılamadı: %s", hata)
                break
            bos_tur = bos_tur + 1 if sonraki <= onceki else 0

        return bulunan
