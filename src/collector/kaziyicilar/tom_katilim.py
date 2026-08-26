"""T.O.M. Katılım (0213) — «hadi kazan» listesi, süresi geçenler elenir.

İKİ AYRI ALAN ADI: kurumsal site `tombank.com.tr`, kampanyalar ise
`tombankhadi.com` altında. `data/banks.yaml`'daki `site` alanı kurumsal
adresi gösterir; kazınan adres budur ve robots.txt kontrolü de gerçek
adrese sorulur (`RobotsBekcisi` alan adını URL'den türetir).

SÜRESİ GEÇEN KAMPANYALAR: liste, biten kampanyaları da kart olarak
gösteriyor. Başlığında «süresi geçmiş» geçenler burada elenir. Sitedeki
yazım tutarsız (`GEÇMŞİ` gibi harf devrikleri var) ve Python'un `upper()`
metodu Türkçe 'i' harfini 'I' yapıyor; bu yüzden tek bir kalıp yerine
gözlenmiş varyantların tamamı denetlenir.
"""

from __future__ import annotations

import time
from typing import ClassVar

from src.collector.temel_kaziyici import TemelKaziyici

KART = "//*[contains(@class, 'campaign-item')]"
DAHA_FAZLA = "//button[contains(@class, 'show-more')]"

TOPLA_JS = """
let results = [];
let items = document.querySelectorAll('.campaign-item');
for (let item of items) {
    let a = item.querySelector('a.btn');
    if (!a) continue;
    if (a.offsetParent === null) continue;

    let title = item.querySelector('h4') ? item.querySelector('h4').innerText : '';
    results.push({title: title, href: a.href});
}
return results;
"""

SURESI_GECTI_KALIPLARI = (
    "GEÇMİŞ",
    "GECMIS",
    "GEÇMIŞ",
    "SÜRESİ",
    "SURESI",
    "SÜRESI",
    "GEÇMŞİ",
    "GEÇMŞI",
)


class TomKatilimKaziyici(TemelKaziyici):
    BANKA_KODU: ClassVar[str] = "0213"

    def kampanya_urlleri(self) -> list[str]:
        self.sayfayi_ac(self.liste_urlleri[0])
        time.sleep(5)
        self.acilir_pencereleri_kapat()

        self.hepsini_yukle(KART, DAHA_FAZLA)

        kartlar = self.surucu.execute_script(TOPLA_JS) or []
        urller: list[str] = []
        for kart in kartlar:
            baslik = (kart.get("title") or "").upper()
            href = kart.get("href") or ""
            if any(kalip in baslik for kalip in SURESI_GECTI_KALIPLARI):
                continue
            if href:
                urller.append(str(href))
        return urller
