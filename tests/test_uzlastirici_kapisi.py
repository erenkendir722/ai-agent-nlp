"""Uzlaştırmadan sonraki ALAN MAKULLÜĞÜ kapısı.

NEDEN BU TESTLER VAR — 16 Ağustos'ta bulunan sızıntı:
    Makullük sınırı, aralık-ucu denetimi ve veto ifadeleri `KuralTanimi`
    üzerindeydi, yani yalnız kural katmanına uygulanıyordu. Uzlaştırıcı ise
    kural susunca LLM değerini doğrudan geçiriyordu:

        if kural is None and llm is not None:
            return llm

    Sonuç: kural katmanına yazılan her eleme, hatayı ÖNLEMEK yerine
    KAYNAĞINI DEĞİŞTİRİYORDU. Ölçülmüş örnek — altın sette `finansman_
    tutari_max` için `sistem=66066.24 yontem=llm`, ham ifade "66.066,24 TL",
    kaynağı bir "Geri Ödenecek Toplam Tutar" satırı.

    Buradaki testler kapının hangi katmandan gelirse gelsin çalıştığını
    ve konumsuz değerleri yanlışlıkla elemediğini kanıtlar.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.extraction.uzlastirici import uzlastir
from src.schema import Alan, HamKayit, Kaynak

CEKIM = datetime(2026, 8, 16, 12, 0)

HESAP_MAKINESI = (
    "Konut finansmanı başvurunuzu hemen yapın. % Oranı kendim gireceğim. "
    "Aylık Taksit Tutarı 11.349,76 TL Geri Ödenecek Toplam Tutar 261.044,84 TL "
    "Yıllık Maliyet Oranı % 84,93 Ücretler Toplamı 750,00"
)


def _kayit(metin: str) -> HamKayit:
    return HamKayit(
        banka_kodu="0299",
        banka_adi="Test Katılım Bankası A.Ş.",
        url="https://ornek.test/kampanya",
        cekim_tarihi=CEKIM,
        http_durum=200,
        govde_metin=metin,
    )


def _llm_alani(deger: float, ham: str, metin: str) -> Alan:
    """Metinde gerçekten geçen, konumu doğrulanmış bir LLM değeri."""
    bas = metin.index(ham)
    return Alan(
        deger=deger,
        ham_ifade=ham,
        kaynak=Kaynak(
            url="https://ornek.test/kampanya",
            cekim_tarihi=CEKIM,
            alinti=ham,
            karakter_baslangic=bas,
            karakter_bitis=bas + len(ham),
        ),
        guven=0.75,
        yontem="llm",
    )


def test_kural_susunca_llm_degeri_filtresiz_gecmez() -> None:
    """Sızıntının ta kendisi: kural eledi, LLM aynı sayıyı içeri sokuyordu."""
    kayit = _kayit(HESAP_MAKINESI)
    llm = {"finansman_tutari_max": _llm_alani(261044.84, "261.044,84 TL", HESAP_MAKINESI)}

    kampanya, rapor = uzlastir({}, llm, kayit=kayit)

    assert kampanya.finansman_tutari_max.var_mi is False
    assert rapor.elenen_alan_sayisi == 1


def test_dilim_tablosundan_gelen_llm_degeri_elenir() -> None:
    """Aralık-ucu denetimi de artık LLM yolunda çalışıyor."""
    metin = (
        "Nihai fatura bedeli 1.200.001 TL – 2.000.000 TL aralığında olan taşıt "
        "finansmanlarında en fazla 12 ay vade uygulanır."
    )
    kayit = _kayit(metin)
    llm = {"finansman_tutari_max": _llm_alani(2_000_000.0, "2.000.000 TL", metin)}

    kampanya, _ = uzlastir({}, llm, kayit=kayit)

    assert kampanya.finansman_tutari_max.var_mi is False


def test_makul_deger_gecer() -> None:
    """Kapı yalnız hatalıyı elemeli — asıl risk doğruyu elemek."""
    metin = "Kurumsal müşterilerimize 150.000.000 TL'ye varan proje finansmanı sağlanır."
    kayit = _kayit(metin)
    llm = {"finansman_tutari_max": _llm_alani(150_000_000.0, "150.000.000 TL", metin)}

    kampanya, rapor = uzlastir({}, llm, kayit=kayit)

    assert kampanya.finansman_tutari_max.deger == pytest.approx(150_000_000.0)
    assert rapor.elenen_alan_sayisi == 0


def test_konumsuz_deger_elenmez() -> None:
    """Enum ve cümleden türeyen alanlar konum taşımaz; kapı onlara uygulanmaz.

    `karakter_baslangic == karakter_bitis` LLM katmanının kanıtsız kaynak
    biçimidir; oradan pencere çıkarmak metnin başını denetlemek olurdu.
    """
    kayit = _kayit(HESAP_MAKINESI)
    konumsuz = Alan(
        deger=500_000.0,
        ham_ifade="500.000 TL",
        kaynak=Kaynak(
            url="https://ornek.test/kampanya",
            cekim_tarihi=CEKIM,
            alinti="",
            karakter_baslangic=0,
            karakter_bitis=0,
        ),
        guven=0.6,
        yontem="llm",
    )

    kampanya, rapor = uzlastir({}, {"finansman_tutari_max": konumsuz}, kayit=kayit)

    assert kampanya.finansman_tutari_max.var_mi is True
    assert rapor.elenen_alan_sayisi == 0


def test_kaynaksiz_alan_kapiyi_dusurmez() -> None:
    """`kaynak=None` (masrafsiz_mi'nin LLM biçimi) çökmeye yol açmamalı."""
    kayit = _kayit(HESAP_MAKINESI)
    kaynaksiz = Alan(
        deger=True, ham_ifade="masraf yok", kaynak=None, guven=0.65, yontem="llm"
    )

    kampanya, _ = uzlastir({}, {"masrafsiz_mi": kaynaksiz}, kayit=kayit)

    assert kampanya.masrafsiz_mi.deger is True
