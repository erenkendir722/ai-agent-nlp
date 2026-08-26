"""Emlak Katılım (0211) — iki liste sayfası, sayfalama YOK.

«Daha fazla yükle» düğmesi bulunmuyor; tüm kampanyalar tek listede geliyor.
Bu yüzden kart bağlantıları doğrudan toplanır.
"""

from __future__ import annotations

import time
from typing import ClassVar

from src.collector.temel_kaziyici import TemelKaziyici

TOPLA_JS = """
let links = [];
let items = document.querySelectorAll('a.campaign-card__button');
for (let a of items) {
    if (a.offsetParent !== null) {
        links.push(a.href);
    }
}
return links;
"""


class EmlakKatilimKaziyici(TemelKaziyici):
    BANKA_KODU: ClassVar[str] = "0211"

    def kampanya_urlleri(self) -> list[str]:
        urller: list[str] = []
        for liste_url in self.liste_urlleri:
            self.sayfayi_ac(liste_url)
            time.sleep(3)
            urller += self.baglantilari_topla(TOPLA_JS)
        return urller
