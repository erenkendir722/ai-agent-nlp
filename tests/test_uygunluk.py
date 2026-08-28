"""Uygunluk ajanının testleri — kısıtlar metinden nasıl çıkıyor.

Bu ajanın en pahalı hata sınıfı YANLIŞ POZİTİFTİR: uydurulmuş bir kısıt
muhakemede müşteriyi eler ve gerekçesini ekrana yazar, yani hata jürinin
gözünün önünde olur. Testlerin çoğu bu yüzden "bulmamalı" testidir.
"""

from __future__ import annotations

from datetime import datetime

from src.ajanlar.uygunluk import UygunlukAjani
from src.schema import Alan, Birim, HedefKitle, Kampanya


def _kampanya(metin: str, **alanlar) -> Kampanya:
    varsayilan = {ad: Alan.yok() for ad in ("hedef_kitle", "finansman_tutari_max", "vade_ay_max")}
    varsayilan.update(alanlar)
    return Kampanya(
        banka_adi="Test Bankası",
        banka_kodu="0299",
        kampanya_id="0299-test",
        kaynak_url="https://test.bank/kampanya",
        cekim_tarihi=datetime(2026, 8, 26),
        ham_metin=metin,
        **varsayilan,
    )


class TestAlandanTuretme:
    def test_azami_tutar_ve_vade_alandan_gelir(self):
        kampanya = _kampanya(
            "Konut finansmanı kampanyası.",
            finansman_tutari_max=Alan(
                deger=800000.0, ham_ifade="800.000 TL", guven=0.9, yontem="kural", birim=Birim.TL
            ),
            vade_ay_max=Alan(
                deger=120, ham_ifade="120 ay", guven=0.9, yontem="kural", birim=Birim.AY
            ),
        )
        kosul = UygunlukAjani().cikar(kampanya)
        assert kosul.max_tutar == 800000.0
        assert kosul.max_vade_ay == 120
        assert kosul.kisit_var_mi()

    def test_hedef_kitle_musteri_tipine_donusur(self):
        kampanya = _kampanya(
            "Yeni müşterilere özel.",
            hedef_kitle=Alan(
                deger=HedefKitle.YENI_MUSTERI, ham_ifade="yeni müşteri", guven=0.8, yontem="llm"
            ),
        )
        assert UygunlukAjani().cikar(kampanya).musteri_tipi == [HedefKitle.YENI_MUSTERI]


class TestMetindenCikarma:
    def test_asgari_finansman_tutari_bulunur(self):
        kampanya = _kampanya(
            "Pratik Finansman Kart ile asgari 250 TL finansman kullanılabilmektedir."
        )
        assert UygunlukAjani().cikar(kampanya).min_tutar == 250.0

    def test_zorunlu_urun_yukumluluk_ifadesiyle_bulunur(self):
        kampanya = _kampanya(
            "Kampanyadan faydalanabilmek için ödemenin kredi kartı ile "
            "gerçekleştirilmesi gerekmektedir."
        )
        assert UygunlukAjani().cikar(kampanya).zorunlu_urun == ["kredi kartı"]

    def test_segment_adi_musteri_tipini_segmente_cekiyor(self):
        kampanya = _kampanya("Emekli müşterilerimize özel promosyon fırsatı.")
        kosul = UygunlukAjani().cikar(kampanya)
        assert kosul.segment_detayi == ["emekli"]
        assert kosul.musteri_tipi == [HedefKitle.SEGMENT]


class TestYanlisPozitifKapilari:
    """Bulmaması gerekenler — ajanın asıl sınavı."""

    def test_urun_adi_tek_basina_zorunluluk_saymaz(self):
        # Kredi kartı kampanyasının metninde "kredi kartı" geçer; bu, kampanyaya
        # girmek için kredi kartı sahibi OLMAK gerektiği anlamına gelmez.
        kampanya = _kampanya("Yeni kredi kartı başvurularında 500 TL hediye puan!")
        assert UygunlukAjani().cikar(kampanya).zorunlu_urun == []

    def test_harcama_esigi_finansman_alt_siniri_sayilmaz(self):
        kampanya = _kampanya("1.500 TL ve üzeri alışverişlerde 50 TL Worldpuan kazanın.")
        assert UygunlukAjani().cikar(kampanya).min_tutar is None

    def test_ucret_tarifesi_kisit_uretmez(self):
        kampanya = _kampanya("399.000 TL üstü | 797,68 TL | BSMV hariçtir.")
        kosul = UygunlukAjani().cikar(kampanya)
        assert kosul.min_tutar is None

    def test_kisitsiz_metin_herkese_acik_demek(self):
        kosul = UygunlukAjani().cikar(_kampanya("Bankamızın yeni şubesi hizmete girdi."))
        assert kosul.kisit_var_mi() is False
        assert kosul is not None  # `None` "hiç bakılmadı" demek olurdu


class TestTutarlilik:
    def test_ters_aralikta_zayif_kanit_dusurulur(self):
        # Metinden gelen asgari (100.000 TL) alandan gelen azamiyi (50.000 TL)
        # aşıyor. Şema ters aralıkta ValueError fırlatıyor; ajan patlamamalı.
        kampanya = _kampanya(
            "Kampanyada asgari 100.000 TL finansman kullanılabilir.",
            finansman_tutari_max=Alan(
                deger=50000.0, ham_ifade="50.000 TL", guven=0.9, yontem="kural", birim=Birim.TL
            ),
        )
        kosul = UygunlukAjani().cikar(kampanya)
        assert kosul.max_tutar == 50000.0
        assert kosul.min_tutar is None

    def test_kisit_bulunca_kaynak_tasinir(self):
        kampanya = _kampanya(
            "Kampanyadan faydalanmak için maaş hesabı bankamızda bulunan müşteri olmak gerekir."
        )
        kosul = UygunlukAjani().cikar(kampanya)
        assert kosul.kaynak is not None
        assert kosul.kaynak.url == "https://test.bank/kampanya"
        assert "maaş" in kosul.kaynak.alinti.lower()

    def test_iz_defteri_gerekce_yaziyor(self):
        _, iz = UygunlukAjani().cikar_izli(_kampanya("Emekli müşterilere özel."))
        assert iz.llm_kullanildi is False
        assert iz.karar_gerekcesi


class TestBoruHattiBaglantisi:
    def test_cikarim_uygunlugu_dolduruyor(self):
        """`kampanya_cikar` uygunluk ajanını koşmalı — asıl kapı burasıdır."""
        from src.extraction.uzlastirici import kampanya_cikar
        from src.schema import HamKayit

        kayit = HamKayit(
            banka_kodu="0299",
            banka_adi="Test Bankası",
            url="https://test.bank/kampanya",
            cekim_tarihi=datetime(2026, 8, 26),
            http_durum=200,
            govde_metin=(
                "Emekli müşterilerimize özel 120 aya kadar konut finansmanı. "
                "Kampanyaya katılmak için maaş hesabınızın bankamızda bulunması gerekmektedir."
            ),
        )
        kampanya, _ = kampanya_cikar(kayit, kural_kullan=True, llm_kullan=False)
        assert kampanya.uygunluk is not None
        assert kampanya.uygunluk.kisit_var_mi()
