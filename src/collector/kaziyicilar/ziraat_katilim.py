"""Ziraat Katılım (0209) — tek liste sayfası, sekmeli kart ızgarası.

Sayfada birden çok sekme var ve kapalı sekmelerin kartları da DOM'da duruyor.
JS tarafındaki `offsetParent !== null` denetimi o gizli kartları eler: açık
sekmede gerçekten görünen kampanyalar alınır.
"""

from __future__ import annotations

import time
from typing import ClassVar

from src.collector.temel_kaziyici import TemelKaziyici

TOPLA_JS = """
let links = [];
let wrappers = document.querySelectorAll('.bankkart-kampanyalar-wrapper');
for (let wrapper of wrappers) {
    let atags = wrapper.querySelectorAll('a.details-link');
    for (let a of atags) {
        if (a.offsetParent !== null) {
            links.push(a.href);
        }
    }
}
return links;
"""


class ZiraatKatilimKaziyici(TemelKaziyici):
    BANKA_KODU: ClassVar[str] = "0209"

    def kampanya_urlleri(self) -> list[str]:
        self.sayfayi_ac(self.liste_urlleri[0])
        time.sleep(5)
        self.acilir_pencereleri_kapat()
        return self.baglantilari_topla(TOPLA_JS)
