"""Türkçe normalizasyon testleri.

Buradaki her vaka, şartname 5.6'daki "farklı yazılmış bilgiler" kriterinin
bir örneğidir. Yeni bir yazım varyantı gördüğünüzde ÖNCE buraya bir satır
ekleyin, sonra düzeltin — dayanıklılık metriğimiz bu setin genişliğine bağlı.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.preprocessing.normalizasyon import (
    arama_anahtari,
    masrafsiz_mi,
    oran_ayristir,
    para_ayristir,
    sayi_ayristir,
    tarih_ayristir,
    tr_buyult,
    tr_kucult,
    vade_ayristir,
)


class TestTurkceHarfler:
    """Python'un .lower() metodu Türkçe için yanlıştır — bu testler onu korur."""

    @pytest.mark.parametrize(
        ("girdi", "beklenen"),
        [
            ("İSTANBUL", "istanbul"),
            ("IRAK", "ırak"),
            ("KÂR PAYI", "kâr payı"),
            ("ŞUBE", "şube"),
            ("ÇEK", "çek"),
            ("ĞĞ", "ğğ"),
            ("İş Bankası", "iş bankası"),
        ],
    )
    def test_kucultme(self, girdi: str, beklenen: str) -> None:
        assert tr_kucult(girdi) == beklenen

    def test_birlesik_nokta_kalmiyor(self) -> None:
        """Python'un hatası: "İ".lower() -> "i" + U+0307."""
        assert "̇" not in tr_kucult("İSTANBUL")
        assert tr_kucult("İ") == "i"

    @pytest.mark.parametrize(
        ("girdi", "beklenen"), [("istanbul", "İSTANBUL"), ("ırak", "IRAK")]
    )
    def test_buyultme(self, girdi: str, beklenen: str) -> None:
        assert tr_buyult(girdi) == beklenen

    def test_arama_anahtari_sapkayi_ve_kesmeyi_temizler(self) -> None:
        assert arama_anahtari("Kâr Payı'nın") == "kar payinin"
        assert arama_anahtari("KÂR  PAYI   ORANI") == "kar payi orani"


class TestSayiAyristirma:
    """Türkçe binlik/ondalık ayracı: 1.500,50 = bin beş yüz."""

    @pytest.mark.parametrize(
        ("girdi", "beklenen"),
        [
            ("1.500,50", 1500.50),
            ("50.000", 50000.0),
            ("2,05", 2.05),
            ("2.05", 2.05),  # tek nokta + 2 hane -> ondalık
            ("1.500.000", 1500000.0),
            ("120", 120.0),
            ("% 2 , 05", 2.05),  # bozulmuş boşluklu varyant
        ],
    )
    def test_sayi(self, girdi: str, beklenen: float) -> None:
        assert sayi_ayristir(girdi) == pytest.approx(beklenen)

    def test_bos_ve_gecersiz(self) -> None:
        assert sayi_ayristir("") is None
        assert sayi_ayristir("kâr payı") is None


class TestOran:
    @pytest.mark.parametrize(
        "girdi", ["%2,05", "% 2.05", "2.05 %", "yüzde 2,05", "Yüzde 2,05 oranı"]
    )
    def test_tum_varyantlar_ayni_degeri_verir(self, girdi: str) -> None:
        assert oran_ayristir(girdi) == pytest.approx(2.05)

    def test_yuzde_isareti_yoksa_oran_degildir(self) -> None:
        assert oran_ayristir("2,05") is None

    def test_akil_sagligi_siniri(self) -> None:
        """50.000 bir oran değildir — reddedilmeli."""
        assert oran_ayristir("%50.000") is None


class TestPara:
    @pytest.mark.parametrize(
        ("girdi", "beklenen"),
        [
            ("500 TL", 500.0),
            ("500₺", 500.0),
            ("500 Türk Lirası", 500.0),
            ("50.000 TL", 50000.0),
            ("1,5 milyon TL", 1_500_000.0),
            ("500 bin TL", 500_000.0),
            ("2 milyar TL", 2_000_000_000.0),
        ],
    )
    def test_para(self, girdi: str, beklenen: float) -> None:
        assert para_ayristir(girdi) == pytest.approx(beklenen)

    def test_birim_yoksa_reddeder(self) -> None:
        assert para_ayristir("50.000") is None
        assert para_ayristir("50.000", birim_zorunlu=False) == 50000.0


class TestVade:
    @pytest.mark.parametrize(
        ("girdi", "beklenen"),
        [
            ("120 ay", 120),
            ("120 aya kadar", 120),
            ("10 yıl", 120),
            ("120 taksit", 120),
            ("36 aya varan vade seçeneği", 36),
            ("48 aylık ödeme planı", 48),
            ("24 ayda ödeme", 24),
            ("12-120 ay arası", 120),  # en büyüğü alınır (alan adı _max)
        ],
    )
    def test_vade(self, girdi: str, beklenen: int) -> None:
        assert vade_ayristir(girdi) == beklenen

    def test_ayrica_kelimesi_yanlis_eslesmiyor(self) -> None:
        """'ayrıca' sözcüğü 'ay' ekiyle karışmamalı."""
        assert vade_ayristir("50000 ayrıca geçerlidir") is None

    def test_makul_olmayan_vade_reddedilir(self) -> None:
        assert vade_ayristir("50000 ay") is None


class TestTarih:
    @pytest.mark.parametrize(
        ("girdi", "beklenen"),
        [
            ("31 Aralık 2026", date(2026, 12, 31)),
            ("31.12.2026", date(2026, 12, 31)),
            ("31/12/2026", date(2026, 12, 31)),
            ("2026 yıl sonuna kadar", date(2026, 12, 31)),
            ("Eylül 2026 sonu", date(2026, 9, 30)),
            ("1 Ocak 2027", date(2027, 1, 1)),
        ],
    )
    def test_tarih(self, girdi: str, beklenen: date) -> None:
        assert tarih_ayristir(girdi) == beklenen

    def test_gecersiz_tarih(self) -> None:
        assert tarih_ayristir("32 Aralık 2026") is None
        assert tarih_ayristir("kampanya devam ediyor") is None

    def test_subat_artik_yil(self) -> None:
        assert tarih_ayristir("Şubat 2028 sonu") == date(2028, 2, 29)
        assert tarih_ayristir("Şubat 2026 sonu") == date(2026, 2, 28)


class TestMasrafsizlik:
    @pytest.mark.parametrize(
        "girdi",
        ["masraf alınmaz", "masrafsız", "Dosya masrafı yok!", "TAHSİS ÜCRETİ ALINMAZ"],
    )
    def test_masrafsiz(self, girdi: str) -> None:
        assert masrafsiz_mi(girdi) is True

    def test_masrafli(self) -> None:
        assert masrafsiz_mi("Dosya masrafı alınır.") is False

    def test_belirsiz_none_doner(self) -> None:
        """None ile False farklıdır: None = bilgi yok, False = masraf var."""
        assert masrafsiz_mi("Konut finansmanı kampanyası") is None


class TestDayaniklilikBozmalari:
    """Şartname: 'eksik veya farklı yazılmış bilgiler karşısında doğru sonuç'."""

    @pytest.mark.parametrize(
        "varyant",
        ["%1,89", "% 1,89", "1,89 %", "yüzde 1,89", "%1.89", "% 1 , 89", "%1,89'dan"],
    )
    def test_oran_bozmalari(self, varyant: str) -> None:
        assert oran_ayristir(varyant) == pytest.approx(1.89)

    @pytest.mark.parametrize(
        "varyant", ["50.000 TL", "50.000TL", "50.000 ₺", "50000 TL", "50 bin TL"]
    )
    def test_tutar_bozmalari(self, varyant: str) -> None:
        assert para_ayristir(varyant) == pytest.approx(50000.0)

    def test_tamami_buyuk_harf(self) -> None:
        assert oran_ayristir("AYLIK %2,05 KÂR PAYI") == pytest.approx(2.05)
        assert vade_ayristir("120 AY VADE") == 120
