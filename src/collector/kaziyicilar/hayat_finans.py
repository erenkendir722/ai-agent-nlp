"""Hayat Finans (0212) — iki liste sayfası, sayfalama YOK.

Site Chakra UI ile kurulu ve sınıf adları üretilmiş (`hf-s2k4sf` gibi), yani
yapı değiştiğinde sessizce kayabilir. Bu yüzden JS iki kademeli: önce üretilmiş
kapsayıcı denenir, bulunamazsa jenerik `a.chakra-link` üzerinden gidilir.
İkisinde de `kampanyalar/` süzgeci var — menü ve altbilgi bağlantıları girmesin.
"""

from __future__ import annotations

import time
from typing import ClassVar

from src.collector.temel_kaziyici import TemelKaziyici

TOPLA_JS = """
let links = [];
let container = document.querySelector('.hf-s2k4sf');
if (container) {
    let items = container.querySelectorAll('a');
    for (let a of items) {
        if (a.offsetParent !== null && a.href && a.href.includes('kampanyalar/')) {
            links.push(a.href);
        }
    }
} else {
    let items = document.querySelectorAll('a.chakra-link');
    for (let a of items) {
        if (a.offsetParent !== null && a.href && a.href.includes('kampanyalar/')) {
            links.push(a.href);
        }
    }
}
return links;
"""


class HayatFinansKaziyici(TemelKaziyici):
    BANKA_KODU: ClassVar[str] = "0212"

    def kampanya_urlleri(self) -> list[str]:
        urller: list[str] = []
        for liste_url in self.liste_urlleri:
            self.sayfayi_ac(liste_url)
            time.sleep(3)
            urller += self.baglantilari_topla(TOPLA_JS)
        return urller
