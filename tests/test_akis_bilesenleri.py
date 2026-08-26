"""«Canlı Boru Hattı» çizim bileşenleri — saf HTML üreticilerinin sözleşmesi.

Bu bileşenler `unsafe_allow_html=True` ile basılıyor ve içlerine banka sayfa
başlığı, URL ve hata mesajı gibi UZAK SİTEDEN gelen metin giriyor. Buradaki
testlerin en kritik olanı kaçırma (escape) testleridir: kaçırma atlanırsa
banka sayfasındaki bir `<script>` arayüzde koşar.

Saf işlev oldukları için tarayıcı, Streamlit ya da ağ gerekmez.
"""

from __future__ import annotations

import pytest

from app.akis import (
    YESIL,
    BankaDurumu,
    GunlukSatiri,
    KayitOzeti,
    akis_css,
    banka_izgarasi,
    ilerleme_cubugu,
    katman_hatti,
    kayit_seridi,
    olay_gunlugu,
)

ZARARLI = "<script>alert('x')</script>"


# ---------------------------------------------------------------------------
# Kaçırma — bu bölüm gevşetilemez
# ---------------------------------------------------------------------------


class TestKacirma:
    def test_banka_adi_kacirilir(self) -> None:
        html = banka_izgarasi([BankaDurumu(ad=ZARARLI, asama="taraniyor")])
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_banka_mesaji_kacirilir(self) -> None:
        """Mesaj `title` özniteliğine giriyor — tırnak kaçmazsa öznitelikten çıkar."""
        html = banka_izgarasi([BankaDurumu(ad="Test", asama="hata", mesaj=ZARARLI)])
        assert "<script>" not in html

    def test_gunluk_metni_kacirilir(self) -> None:
        html = olay_gunlugu([GunlukSatiri(tur="sayfa", metin=ZARARLI, etiket=ZARARLI)])
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_kayit_url_kacirilir(self) -> None:
        html = kayit_seridi(
            [KayitOzeti(banka=ZARARLI, doluluk=0.5, guven=0.5, sure=1.0, url=ZARARLI)]
        )
        assert "<script>" not in html

    def test_katman_basliklari_sabittir_ve_sayilar_tam_sayiya_zorlanir(self) -> None:
        html = katman_hatti({"kural": 3, "llm": 1, "hibrit": 7})
        assert "<script>" not in html
        assert "KURAL" in html and "UZLAŞTIRICI" in html


# ---------------------------------------------------------------------------
# Durum sınıfları
# ---------------------------------------------------------------------------


class TestBankaIzgarasi:
    def test_bos_liste_kirilmaz(self) -> None:
        assert banka_izgarasi([]) == '<div class="kl-izgara"></div>'

    def test_aktif_taranan_banka_nabiz_alir(self) -> None:
        html = banka_izgarasi(
            [BankaDurumu(ad="Albaraka", asama="taraniyor", aktif=True)]
        )
        assert "kl-nabizli" in html
        assert YESIL in html

    def test_aktif_olmayan_taranan_banka_nabiz_almaz(self) -> None:
        """Nabız YALNIZ üzerinde işlem yapılan kartta — aşama tek başına yetmez."""
        html = banka_izgarasi(
            [BankaDurumu(ad="Albaraka", asama="taraniyor", aktif=False)]
        )
        assert "kl-nabizli" not in html

    def test_tek_kart_nabiz_atar(self) -> None:
        html = banka_izgarasi(
            [
                BankaDurumu(ad="Albaraka", asama="taraniyor", aktif=False),
                BankaDurumu(ad="Kuveyt", asama="taraniyor", aktif=True),
                BankaDurumu(ad="Vakıf", asama="bekliyor"),
            ]
        )
        assert html.count("kl-nabizli") == 1

    def test_bekleyen_banka_nabiz_almaz(self) -> None:
        assert "kl-nabizli" not in banka_izgarasi([BankaDurumu(ad="Albaraka")])

    def test_biten_banka_sayfa_sayisini_gosterir(self) -> None:
        html = banka_izgarasi(
            [BankaDurumu(ad="Kuveyt Türk", asama="bitti", sayfa=12, toplam=14)]
        )
        assert "12/14 sayfa" in html
        assert "kl-nabizli" not in html

    def test_bilinmeyen_asama_bekliyor_gibi_cizilir(self) -> None:
        """Yeni bir aşama eklenirse sayfa KIRILMAZ, kart nötr çizilir."""
        html = banka_izgarasi([BankaDurumu(ad="X", asama="uydurma")])  # type: ignore[arg-type]
        assert "kl-kart" in html


class TestOlayGunlugu:
    def test_bos_liste_bilgilendirici_satir_doner(self) -> None:
        assert "henüz olay yok" in olay_gunlugu([])

    def test_yeni_olay_ustte(self) -> None:
        html = olay_gunlugu(
            [GunlukSatiri(tur="bilgi", metin="ilk"), GunlukSatiri(tur="bilgi", metin="son")]
        )
        assert html.index("son") < html.index("ilk")

    def test_azami_satir_uygulanir(self) -> None:
        olaylar = [GunlukSatiri(tur="bilgi", metin=f"olay-{i}") for i in range(40)]
        html = olay_gunlugu(olaylar, azami=5)
        assert html.count("kl-gunluk-satir") == 5
        assert "olay-39" in html and "olay-0" not in html

    def test_kapali_gunluk_yalniz_son_olayi_gosterir(self) -> None:
        olaylar = [GunlukSatiri(tur="bilgi", metin=f"olay-{i}") for i in range(40)]
        html = olay_gunlugu(olaylar, acik=False)
        assert html.count("kl-gunluk-satir") == 1
        assert "olay-39" in html
        assert "olay-38" not in html

    def test_kapali_gunluk_kaydirilmaz(self) -> None:
        """Kapalı kutu tek satır: kaydırma çubuğu görünmemeli."""
        html = olay_gunlugu([GunlukSatiri(tur="bilgi", metin="tek")], acik=False)
        assert "kl-gunluk-kapali" in html

    def test_acik_gunluk_kaydirilabilir_kutu_kullanir(self) -> None:
        html = olay_gunlugu([GunlukSatiri(tur="bilgi", metin="tek")], acik=True)
        assert "kl-gunluk-kapali" not in html

    def test_bos_gunluk_iki_kipte_de_kirilmaz(self) -> None:
        assert "henüz olay yok" in olay_gunlugu([], acik=False)
        assert "henüz olay yok" in olay_gunlugu([], acik=True)


class TestIlerlemeCubugu:
    def test_bilinmeyen_toplam_uydurma_ilerleme_uretmez(self) -> None:
        """Toplam bilinmiyorken çubuk DOLMAZ — sayfanın tek yasağı bu."""
        html = ilerleme_cubugu(7, 0)
        assert "width:0.0%" in html
        assert "7 / ?" in html

    def test_olculen_oran_yazilir(self) -> None:
        assert "width:25.0%" in ilerleme_cubugu(5, 20)

    def test_tasan_deger_kirpilir(self) -> None:
        """Sayaç toplamı aşarsa çubuk %100'de durur, taşmaz."""
        assert "width:100.0%" in ilerleme_cubugu(30, 20)

    def test_bitmis_kosuda_animasyon_durur(self) -> None:
        assert "kl-durgun" in ilerleme_cubugu(20, 20, akiyor=False)


class TestKatmanHatti:
    def test_sifir_sayacta_bolme_hatasi_yok(self) -> None:
        html = katman_hatti({"kural": 0, "llm": 0, "hibrit": 0})
        assert "width:0.0%" in html

    def test_eksik_anahtar_sifir_sayilir(self) -> None:
        assert "0" in katman_hatti({"kural": 5})

    def test_en_buyuk_sayac_tam_genislik_alir(self) -> None:
        html = katman_hatti({"kural": 2, "llm": 4, "hibrit": 8})
        assert "width:100.0%" in html


class TestKayitSeridi:
    def test_bos_liste_kirilmaz(self) -> None:
        assert "henüz kayıt işlenmedi" in kayit_seridi([])

    def test_olculen_degerler_yuvarlanmadan_gosterilir(self) -> None:
        html = kayit_seridi([KayitOzeti(banka="Albaraka", doluluk=0.5, guven=0.42, sure=1.234)])
        assert "1.23 sn" in html
        assert "güven 0.42" in html

    def test_cubuklar_imlecle_aciklanir(self) -> None:
        """Renk tek başına anlatmıyor: iki çubuğun ne olduğu sorulmuştu."""
        html = kayit_seridi([KayitOzeti(banka="Albaraka", doluluk=0.25, guven=0.74, sure=1.2)])
        assert "title=\"doluluk:" in html
        assert "title=\"güven:" in html

    def test_azami_kayit_uygulanir(self) -> None:
        kayitlar = [
            KayitOzeti(banka=f"B{i}", doluluk=0.1, guven=0.1, sure=0.1) for i in range(20)
        ]
        # `kl-kart-ad`/`kl-kart-alt` de eşleşmesin diye tam sınıf adı sayılıyor.
        assert kayit_seridi(kayitlar, azami=3).count('class="kl-kart"') == 3


@pytest.mark.parametrize(
    "keyframe", ["kl-nabiz", "kl-kayan", "kl-belir", "kl-supurme"]
)
def test_css_gerekli_keyframeleri_tasir(keyframe: str) -> None:
    assert f"@keyframes {keyframe}" in akis_css()


def test_css_disa_baglanmaz() -> None:
    """Hava boşluğu kısıtı: CDN, dış font, dış JS yok."""
    css = akis_css()
    for yasak in ("http://", "https://", "@import", "url("):
        assert yasak not in css
