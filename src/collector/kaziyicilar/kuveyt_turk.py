"""Kuveyt Türk (0205) — iki liste sayfası, «daha fazla yükle» butonu."""

from __future__ import annotations

import time
from typing import ClassVar

from src.collector.temel_kaziyici import TemelKaziyici

KART_BAGLANTISI = (
    "//*[contains(@class, 'campaign-item-list')]//a[contains(@class, 'no-content-style')]"
)
DAHA_FAZLA = "//a[contains(@class, 'load-more-btn')]"

TOPLA_JS = """
let links = [];
let items = document.querySelectorAll('.campaign-item-list a.no-content-style');
for (let a of items) {
    if (a.offsetParent !== null) {
        links.push(a.href);
    }
}
return links;
"""


class KuveytTurkKaziyici(TemelKaziyici):
    BANKA_KODU: ClassVar[str] = "0205"

    def kampanya_urlleri(self) -> list[str]:
        urller: list[str] = []
        for liste_url in self.liste_urlleri:
            self.sayfayi_ac(liste_url)
            time.sleep(5)
            self.hepsini_yukle(KART_BAGLANTISI, DAHA_FAZLA)
            urller += self.baglantilari_topla(TOPLA_JS)
        return urller
