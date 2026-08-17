"""Arayüz yardımcıları — grafik ve tablo etiketleri.

Banka kısa adları `data/banks.yaml`'daki `kisa_ad` alanından okunur. Burada
ikinci bir sözlük TUTULMAZ: elle yazılan kopya 16 Ağustos'ta kayıt defteriyle
yedi bankada ayrışmıştı ("Türkiye Emlak Katılım Bankası A.Ş." kayıt defterinde
"Emlak Katılım", kopyada hiç eşleşmiyordu). Kayıt defteri tek doğruluk kaynağı.
"""

from __future__ import annotations

from functools import lru_cache

from src.collector.toplayici import bankalari_yukle

# Kayıt defterinde olmayan bir banka için başlığı kısaltırken atılan ekler.
_EKLER = (
    " Katılım Bankası A.Ş.",
    " Bankası A.Ş.",
    " Katılım A.Ş.",
    " A.Ş.",
    " Anonim Şirketi",
)

_AZAMI_UZUNLUK = 15


@lru_cache(maxsize=1)
def _kisa_adlar() -> dict[str, str]:
    """banks.yaml'daki tam ad -> kısa ad eşlemesi (bir kez okunur)."""
    return {b.ad: b.kisa_ad for b in bankalari_yukle()}


def format_bank_name(bank_name: str | None) -> str:
    """Banka adını grafiklerde göstermek için standartlaştırır."""
    if not bank_name:
        return "Belirtilmemiş"

    temiz_girdi = bank_name.strip()

    kisa = _kisa_adlar().get(temiz_girdi)
    if kisa:
        return kisa

    # Kayıt defterinde yoksa (yeni banka, serbest metinden gelen ad) ekleri at.
    kisaltilmis = temiz_girdi
    for ek in _EKLER:
        kisaltilmis = kisaltilmis.replace(ek, "")
    kisaltilmis = kisaltilmis.strip()

    if len(kisaltilmis) > _AZAMI_UZUNLUK:
        return kisaltilmis[:_AZAMI_UZUNLUK] + "..."

    return kisaltilmis
