"""Türkiye Finans (0206) — kampanya URL'leri ELLE tutulur.

Diğer sekiz bankada kampanya listesi gezilerek keşfediliyor. Türkiye
Finans'ta liste sayfası SharePoint `.aspx` altında ve kart bağlantıları
gezilebilir bir listede durmuyor; bu yüzden `data/banks.yaml` içindeki
`seed_urls` bu banka için LİSTE değil DETAY sayfalarını taşır. Şartname 5.1
manuel toplama tekniklerine izin veriyor, yöntem uygun — ama bedeli açık
yazılmalı:

    YENİ TÜRKİYE FİNANS KAMPANYASI ÇIKARSA `data/banks.yaml` İÇİNDEKİ
    `seed_urls` LİSTESİNE ELLE EKLENMELİ. Otomatik keşif yok; liste
    eskirse kayıt eksik kalır ve sistem bunu haber vermez.

Kazıyıcının kendisi bu yüzden neredeyse boş: gezilecek liste sayfası
olmadığı için tarayıcıyla keşif adımı da yok.
"""

from __future__ import annotations

from typing import ClassVar

from src.collector.temel_kaziyici import TemelKaziyici


class TurkiyeFinansKaziyici(TemelKaziyici):
    BANKA_KODU: ClassVar[str] = "0206"

    def kampanya_urlleri(self) -> list[str]:
        return list(self.liste_urlleri)
