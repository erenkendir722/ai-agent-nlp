"""Veri kalitesi denetiminin eşiklerini koruyan testler (G-07).

NEDEN BU TESTLER VAR:
    Rapor, jürinin "bankalar sitelerini değiştirirse ne olur?" sorusunun
    cevabı. Cevabın işe yaraması iki şeye bağlı: eşiklerin gerçekten
    kırılması ve YANLIŞ ALARM üretmemesi.

    İkincisi birincisi kadar önemli. Kâr payı = 0 olan kayıtlar "vade
    farksız" kampanyalardır ve gerçektir; bunlara hata denirse rapor
    her koşuda kırmızı yanar, kimse bakmaz ve gerçek kırılma gözden
    kaçar. O yüzden sıfır kâr payı `bilgi` seviyesinde tutulur ve
    aşağıdaki test bunu sözleşme hâline getirir.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from tools.veri_kalitesi import (
    AYLIK_KAR_PAYI_TAVANI,
    DIGER_ESIK_ORANI,
    aykiri_degerler,
    banka_kapsami,
    celiskiler,
    eksiklik,
    rapor_yaz,
)


class SahteKayit:
    """`KampanyaKaydi` yerine geçer — denetim düz sütunlarla çalışır."""

    def __init__(self, **alanlar: object) -> None:
        varsayilan: dict[str, object] = {
            "banka_kodu": "0203",
            "banka_adi": "Albaraka Türk Katılım Bankası A.Ş.",
            "kaynak_url": "https://ornek.test/kampanya",
            "kampanya_turu": "kart",
            "hedef_kitle": None,
            "kar_payi_orani": None,
            "finansman_tutari_max": None,
            "vade_ay_max": None,
            "taksit_sayisi": None,
            "tahsis_ucreti": None,
            "odul_miktari": None,
            "indirim_orani": None,
            "alisveris_puani": None,
            "masrafsiz_mi": None,
            "kampanya_bitis": None,
            "doluluk_orani": 0.3,
        }
        varsayilan.update(alanlar)
        for ad, deger in varsayilan.items():
            setattr(self, ad, deger)


def bulgu_bul(bulgular: list, parca: str):
    for b in bulgular:
        if parca.lower() in b.ad.lower():
            return b
    raise AssertionError(f"{parca!r} içeren kontrol yok: {[b.ad for b in bulgular]}")


class TestAykiriDegerler:
    def test_aylik_tavani_asan_kar_payi_yakalanir(self) -> None:
        kayitlar = [SahteKayit(kar_payi_orani=AYLIK_KAR_PAYI_TAVANI + 5)]
        assert bulgu_bul(aykiri_degerler(kayitlar), "Kâr payı oranı > ").asildi

    def test_makul_kar_payi_uyari_uretmez(self) -> None:
        kayitlar = [SahteKayit(kar_payi_orani=2.05)]
        assert not bulgu_bul(aykiri_degerler(kayitlar), "Kâr payı oranı > ").asildi

    def test_sifir_kar_payi_hata_sayilmaz(self) -> None:
        """Vade farksız kampanyalar gerçek — yanlış alarm üretilmemeli."""
        bulgu = bulgu_bul(aykiri_degerler([SahteKayit(kar_payi_orani=0)]), "= 0")
        assert bulgu.sayi == 1
        assert bulgu.seviye == "bilgi"
        assert not bulgu.asildi

    def test_gecmis_bitis_tarihi_yakalanir(self) -> None:
        kayitlar = [SahteKayit(kampanya_bitis=date.today() - timedelta(days=1))]
        assert bulgu_bul(aykiri_degerler(kayitlar), "bitişi geçmişte").asildi

    def test_gelecekteki_bitis_tarihi_temiz(self) -> None:
        kayitlar = [SahteKayit(kampanya_bitis=date.today() + timedelta(days=30))]
        assert not bulgu_bul(aykiri_degerler(kayitlar), "bitişi geçmişte").asildi

    @pytest.mark.parametrize(
        ("alan", "deger", "parca"),
        [
            ("finansman_tutari_max", 1_000.0, "Finansman tutarı <"),
            ("finansman_tutari_max", 50_000_000.0, "Finansman tutarı >"),
            ("vade_ay_max", 480, "Vade >"),
            ("taksit_sayisi", 99, "Taksit sayısı >"),
            ("indirim_orani", 150.0, "İndirim oranı >"),
        ],
    )
    def test_aralik_disi_degerler(self, alan: str, deger: object, parca: str) -> None:
        assert bulgu_bul(aykiri_degerler([SahteKayit(**{alan: deger})]), parca).asildi


class TestCeliskiler:
    def test_masrafsiz_ama_tahsis_ucreti_var(self) -> None:
        kayitlar = [SahteKayit(masrafsiz_mi=True, tahsis_ucreti=500.0)]
        assert bulgu_bul(celiskiler(kayitlar), "Masrafsız").asildi

    def test_masrafsiz_ve_ucretsiz_tutarli(self) -> None:
        kayitlar = [SahteKayit(masrafsiz_mi=True, tahsis_ucreti=0.0)]
        assert not bulgu_bul(celiskiler(kayitlar), "Masrafsız").asildi

    def test_ayni_bankada_genis_oran_araligi_yakalanir(self) -> None:
        kayitlar = [
            SahteKayit(kar_payi_orani=0.5),
            SahteKayit(kar_payi_orani=AYLIK_KAR_PAYI_TAVANI + 6),
        ]
        assert bulgu_bul(celiskiler(kayitlar), "Banka içi").asildi

    def test_mukerrer_url_yakalanir(self) -> None:
        kayitlar = [SahteKayit(kaynak_url="https://a.test/x") for _ in range(2)]
        assert bulgu_bul(celiskiler(kayitlar), "birden çok kayıt").asildi


class TestEksiklik:
    def test_bos_kayit_yakalanir(self) -> None:
        bulgular, _ = eksiklik([SahteKayit(doluluk_orani=0.0)])
        assert bulgu_bul(bulgular, "Hiçbir alanı").asildi

    def test_diger_orani_esigi_asinca_kirilir(self) -> None:
        n = 100
        kayitlar = [SahteKayit(kampanya_turu="diger") for _ in range(n)]
        bulgular, _ = eksiklik(kayitlar)
        assert bulgu_bul(bulgular, "`diger`").asildi

    def test_diger_orani_esigin_altinda_temiz(self) -> None:
        kayitlar = [SahteKayit(kampanya_turu="diger") for _ in range(10)]
        kayitlar += [SahteKayit(kampanya_turu="kart") for _ in range(90)]
        bulgular, _ = eksiklik(kayitlar)
        bulgu = bulgu_bul(bulgular, "`diger`")
        assert bulgu.sayi == 10
        assert not bulgu.asildi

    def test_bos_alan_tablosu_orani_dogru(self) -> None:
        kayitlar = [SahteKayit(kar_payi_orani=None) for _ in range(4)]
        kayitlar.append(SahteKayit(kar_payi_orani=2.0))
        _, tablo = eksiklik(kayitlar)
        oranlar = {alan: oran for alan, _, oran in tablo}
        assert oranlar["kar_payi_orani"] == pytest.approx(80.0)


class TestRapor:
    def test_bayat_veritabani_uyari_basar(self) -> None:
        durum = {"bayat": True, "sebep": "kod değişti", "kosu": None}
        metin = rapor_yaz([SahteKayit()], durum)
        assert "**BAYAT" in metin
        assert "make extract && make veri-kalitesi" in metin

    def test_guncel_veritabani_bayat_demez(self) -> None:
        durum = {
            "bayat": False,
            "sebep": "",
            "kosu": {
                "zaman": __import__("datetime").datetime(2026, 8, 23, 14, 57),
                "yapilandirma": "hibrit",
                "kayit_sayisi": 590,
            },
        }
        metin = rapor_yaz([SahteKayit()], durum)
        assert "BAYAT" not in metin
        assert "**Güncel.**" in metin

    def test_banka_kapsami_dengesizligi_raporlar(self) -> None:
        kayitlar = [SahteKayit(banka_kodu="0203") for _ in range(10)]
        kayitlar += [SahteKayit(banka_kodu="0212", banka_adi="Hayat Finans")]
        satirlar = {kod: n for kod, _, n, _, _ in banka_kapsami(kayitlar)}
        assert satirlar == {"0203": 10, "0212": 1}


def test_diger_esigi_makul_araliktadir() -> None:
    """Eşik sessizce gevşetilirse rapor kırılmayı görmez."""
    assert 0.0 < DIGER_ESIK_ORANI <= 0.5
