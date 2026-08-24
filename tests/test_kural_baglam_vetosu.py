"""Yanlış alana sızan sayıları eleyen vetoları koruyan testler.

NEDEN BU TESTLER VAR — 23 Ağustos'ta 590 kayıtta ölçülen hata:
    Kural katmanı sayıyı buluyor ama çevresindeki cümlenin ne dediğine
    bakmıyordu. Kanıt alıntıları hatayı açık ediyordu:

        "%10 oranında indirim kazanımı"        -> kar_payi_orani = %10
        "%10 oranında mil kazanırsınız"        -> kar_payi_orani = %10
        "%7,5 yerine %15 iade"                 -> kar_payi_orani = %7,5
        "komisyon ödemeden 10.000 TL çekebilir"-> tahsis_ucreti = 10.000
        "1.3.2021 Tarihinden Önce"             -> kampanya_bitis = 2021-03-01
        "10 Mart 2007 ... Resmî Gazete"        -> kampanya_bitis = 2007-03-10

    Hepsinde değer metinde GERÇEKTEN geçiyordu, yani eleştirmen ajanı
    halüsinasyon saymıyordu; kalkan varlığı doğrular, anlamı değil.

    Dışlayıcı sözcük de yetmiyordu: mesafeye duyarlı olduğu için bağlam
    sözcüğü ("oran", "komisyon", "kadar") sayıya daha yakın kaldığında
    karşılaştırmayı kazanıyordu. Çözüm veto: varlık ölçüttür.

    Vetolar sessizce kaldırılırsa hata sessizce geri gelir — ölçüm
    sayıları oynar ama hiçbir test düşmez. Buradaki testler onu engeller.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from src.extraction.kural import kurallarla_cikar

CEKIM = datetime(2026, 8, 23, 12, 0)
URL = "https://ornek.test/kampanyalar/detay/deneme"


def cikar(metin: str, alan: str):
    return kurallarla_cikar(metin, URL, CEKIM).get(alan)


class TestKarPayiKirlenmesi:
    @pytest.mark.parametrize(
        "metin",
        [
            "Kampanya kapsamında kırtasiye harcamaları için %10 oranında "
            "indirim kazanımı sağlayacaklardır.",
            "Kampanya süresi boyunca tüm gönderilerinizden %10 oranında mil "
            "kazanırsınız.",
            "Gold Statü ile %10 oranına varan özel indirimler sizi bekliyor.",
            "Tüm restoranlarda %7,5 yerine %15 iade, tüm marketlerde %5 iade.",
        ],
    )
    def test_baska_bir_yuzde_kar_payi_sayilmaz(self, metin: str) -> None:
        assert cikar(metin, "kar_payi_orani") is None

    def test_gercek_kar_payi_hala_cikarilir(self) -> None:
        """Veto meşru değeri elemez — asıl risk buydu."""
        alan = cikar("Aylık kâr payı oranı %2,05'ten başlıyor.", "kar_payi_orani")
        assert alan is not None
        assert alan.deger == pytest.approx(2.05)

    def test_vade_farksiz_sifir_orani_korunur(self) -> None:
        alan = cikar("Vade farksız kampanya: kâr payı oranı %0.", "kar_payi_orani")
        assert alan is not None
        assert alan.deger == 0


class TestTahsisUcretiKirlenmesi:
    def test_komisyonsuz_cekim_limiti_ucret_sayilmaz(self) -> None:
        metin = (
            "Anlaşmalı İş Bankası, Yapı Kredi ve PTT ATM'sinden komisyon "
            "ödemeden 10.000 TL'ye kadar para çekebilirsiniz."
        )
        assert cikar(metin, "tahsis_ucreti") is None

    def test_gercek_tahsis_ucreti_hala_cikarilir(self) -> None:
        alan = cikar("60 ay vadede 500 TL tahsis ücreti alınır.", "tahsis_ucreti")
        assert alan is not None
        assert alan.deger == pytest.approx(500.0)


class TestBitisTarihiYonu:
    def test_tarihinden_once_bitis_sayilmaz(self) -> None:
        metin = (
            "Nakdi Finansman Erken Kapama-Kalan Vadesi 24 Aya Kadar "
            "(1.3.2021 Tarihinden Önce Kullandırılan Finansmanlarda)"
        )
        assert cikar(metin, "kampanya_bitis") is None

    def test_tarihi_sonrasinda_bitis_sayilmaz(self) -> None:
        metin = (
            "Kuveyt Türk Mobil'den müşterimiz olanlar 16 Haziran 2025 tarihi "
            "sonrasında kampanyaya katılabilir."
        )
        assert cikar(metin, "kampanya_bitis") is None

    def test_mevzuat_tarihi_bitis_sayilmaz(self) -> None:
        metin = (
            "Ürün gruplarında uygulanacak taksit adetleri 10 Mart 2007 "
            "tarihinde 26458 numaralı Resmî Gazete'de yayımlanmıştır."
        )
        assert cikar(metin, "kampanya_bitis") is None

    def test_gercek_bitis_tarihi_hala_cikarilir(self) -> None:
        alan = cikar("Kampanya 31 Aralık 2026 tarihine kadar geçerlidir.", "kampanya_bitis")
        assert alan is not None
        assert alan.deger == date(2026, 12, 31)


def test_veto_yedek_yolu_da_kapatir() -> None:
    """Tarih aralığı yapısı vetoyu atlamamalı.

    `_adaylari_bul` bağlam skoru None dönünce "aralık sonu" yapısına bakıp
    adayı yine kabul ediyordu; veto yalnız bir yolu kapatıyordu. Aşağıdaki
    metinde "Kapama-Kalan" tiresi yapıyı aralık sonu gibi gösteriyor.
    """
    metin = "Erken Kapama-Kalan Vadesi 24 Aya Kadar (1.3.2021 Tarihinden Önce)"
    assert cikar(metin, "kampanya_bitis") is None
