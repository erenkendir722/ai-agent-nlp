"""Dünya Katılım (0214) — tek URL, iki JS sekmesi (bireysel / kurumsal).

Sekme değiştirmek URL'i DEĞİŞTİRMİYOR: `#personal` ve `#corporate` ögelerine
tıklandığında liste yerinde yeniden çiziliyor. Bu yüzden iki sekme ayrı
başlangıç URL'i olarak yazılamaz; tek sayfa açılır, sekmeler sırayla
tıklanır ve her sekmenin listesi ayrı ayrı sonuna kadar yüklenir.

«Daha fazla» düğmesi son sayfadan sonra da DOM'da kalıyor, o yüzden taban
sınıfın görünürlük süzgeci burada kullanılmıyor: ölçüt kart sayısıdır —
art arda üç turda artmıyorsa liste bitmiştir.
"""

from __future__ import annotations

import logging
import time
from typing import ClassVar

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By

from src.collector.temel_kaziyici import AZAMI_YUKLE_TIKLAMASI, TemelKaziyici

log = logging.getLogger(__name__)

KART_BAGLANTISI = (
    "//*[contains(@class, 'page-campaigns-content-list')]//a[contains(@class, 'link')]"
)
DAHA_FAZLA = "//a[@id='moreCampaigns']"
SEKMELER = ("personal", "corporate")


class DunyaKatilimKaziyici(TemelKaziyici):
    BANKA_KODU: ClassVar[str] = "0214"

    def kampanya_urlleri(self) -> list[str]:
        self.sayfayi_ac(self.liste_urlleri[0])
        time.sleep(5)
        self.acilir_pencereleri_kapat()

        urller: list[str] = []
        for sekme_id in SEKMELER:
            if not self._sekmeye_gec(sekme_id):
                continue
            self._listeyi_sonuna_kadar_yukle()
            urller += self.xpath_baglantilari(KART_BAGLANTISI)
        return urller

    def _sekmeye_gec(self, sekme_id: str) -> bool:
        try:
            sekme = self.surucu.find_element(By.ID, sekme_id)
            self.surucu.execute_script("arguments[0].scrollIntoView({block: 'center'});", sekme)
            time.sleep(1)
            self.surucu.execute_script("arguments[0].click();", sekme)
        except WebDriverException as hata:
            log.warning("Dünya Katılım '%s' sekmesi açılamadı: %s", sekme_id, hata)
            return False
        time.sleep(3)
        return True

    def _listeyi_sonuna_kadar_yukle(self) -> None:
        bos_tur = 0
        for _ in range(AZAMI_YUKLE_TIKLAMASI):
            if bos_tur >= 3:
                return
            self._kaydir_sona()
            time.sleep(2)

            try:
                onceki = len(self.surucu.find_elements(By.XPATH, KART_BAGLANTISI))
                dugmeler = self.surucu.find_elements(By.XPATH, DAHA_FAZLA)
            except WebDriverException as hata:
                log.debug("Dünya Katılım listesi okunamadı: %s", hata)
                return

            if not dugmeler:
                return
            if not self._tikla(dugmeler[0]):
                return
            time.sleep(3)

            try:
                sonraki = len(self.surucu.find_elements(By.XPATH, KART_BAGLANTISI))
            except WebDriverException as hata:
                log.debug("kart sayılamadı: %s", hata)
                return
            bos_tur = bos_tur + 1 if sonraki == onceki else 0
