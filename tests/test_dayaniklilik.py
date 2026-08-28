"""Dayanıklılık ölçüm aracının kendi testleri.

Ölçüm aracı sessizce bozulursa, ürettiği "%100 dayanıklı" raporu sistemin
gerçek durumunu değil aracın kırıldığını gösterir — ve bu, ölçmemekten
kötüdür. Buradaki testler aracın üç sessiz kırılma biçimini kapatır:
bozmanın metni hiç değiştirmemesi, silmenin eksik yapılması ve
"kaydı" ile "uydurdu" ayrımının kaybolması.
"""

from __future__ import annotations

import pytest

from eval.dayaniklilik import (
    BICIM_BOZMALARI,
    bosluk_ekle,
    buyuk_harf,
    cumleyi_sil,
    ondalik_ayraci,
    para_birimi,
    yuzde_bicimi,
)

ORNEK = (
    "Konut finansmanında %1,89 kâr payı oranı geçerlidir.\n"
    "Vade 48 ay olarak uygulanır.\n"
    "Tahsis ücreti 1.500 TL tutarındadır.\n"
)


@pytest.mark.parametrize("ad,fn", sorted(BICIM_BOZMALARI.items()))
def test_bozma_metni_gercekten_degistirir(ad: str, fn) -> None:
    """Hiçbir şey değiştirmeyen bir bozma, ölçümü sahte %100'e taşır."""
    assert fn(ORNEK) != ORNEK, f"{ad} metni değiştirmedi — ölçüm anlamsızlaşır"


def test_yuzde_bicimi_degeri_korur() -> None:
    """Biçim bozmanın sözleşmesi: yazım değişir, DEĞER durur."""
    assert "1,89" in yuzde_bicimi(ORNEK)
    assert "%1,89" not in yuzde_bicimi(ORNEK)


def test_ondalik_ayraci_degeri_korur() -> None:
    assert "1.89" in ondalik_ayraci(ORNEK)


def test_para_birimi_degeri_korur() -> None:
    bozuk = para_birimi(ORNEK)
    assert "1.500" in bozuk and "₺" in bozuk and "TL" not in bozuk


def test_bosluk_ekle_degeri_korur() -> None:
    assert "1,89" in bosluk_ekle(ORNEK)


def test_buyuk_harf_degeri_korur() -> None:
    assert "1,89" in buyuk_harf(ORNEK)


def test_cumleyi_sil_tum_gecisleri_siler() -> None:
    """Tek geçiş silmek, değeri metinde bırakıp sistemi haksız yere suçlardı.

    17 Ağustos ölçümünde 53 vakanın 21'i tam olarak buydu: banka sayfaları
    aynı sayıyı başlıkta, tabloda ve dipnotta tekrarlıyor.
    """
    tekrarli = (
        "Kâr payı oranı %1,89 olarak uygulanır.\n"
        "Detay tabloda: %1,89 kâr payı.\n"
        "Dipnot — %1,89 oranı 2026 için geçerlidir.\n"
    )
    assert "%1,89" not in cumleyi_sil(tekrarli, "%1,89")


def test_cumleyi_sil_bulunmayan_ifadede_metni_bozmaz() -> None:
    assert cumleyi_sil(ORNEK, "%9,99") == ORNEK


def test_cumleyi_sil_sonsuz_donguye_girmez() -> None:
    """Güvenlik sınırı: kendini tekrar eden metin aracı kilitlememeli."""
    assert cumleyi_sil("abc " * 500, "abc") is not None
