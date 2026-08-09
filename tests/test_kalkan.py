"""Sayısal doğrulama kalkanı ve kanıt zinciri testleri.

Bu testler sistemin en özgün iddiasını korur: "sistem uydurma kâr payı oranı
söyleyemez". Bu bir istem mühendisliği vaadi değil, kodla uygulanmış bir
kısıttır — ve kısıt ancak testi varsa kısıttır.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.depolama import KampanyaKaydi
from src.extraction.kural import kurallarla_cikar
from src.rag.chatbot import Niyet, niyet_belirle, sayisal_dogrulama
from src.schema import Alan, Kampanya, Kaynak

ORNEK_METIN = (
    "Konut Finansmanı kampanyası. Aylık kâr payı oranı %1,89'dan başlayan "
    "oranlarla, 120 aya kadar vade imkânı. 5.000.000 TL'ye kadar finansman. "
    "Dosya masrafı alınmaz. Kampanya 31 Aralık 2026 tarihine kadar geçerlidir."
)


def _kayit(**alanlar) -> KampanyaKaydi:
    varsayilan = {
        "kampanya_id": "TEST-1",
        "banka_kodu": "0205",
        "banka_adi": "Test Katılım Bankası A.Ş.",
        "kaynak_url": "https://ornek.test/kampanya",
        "cekim_tarihi": datetime(2026, 8, 9, 12, 0),
        "tam_kayit": {},
        "ham_metin": ORNEK_METIN,
    }
    return KampanyaKaydi(**{**varsayilan, **alanlar})


class TestSayisalDogrulama:
    def test_kayitta_olan_sayi_gecer(self) -> None:
        kayit = _kayit(kar_payi_orani=1.89, vade_ay_max=120)
        gecti, reddedilen = sayisal_dogrulama(
            "Kâr payı oranı aylık %1.89, vade 120 ay.", [kayit]
        )
        assert gecti, f"Doğru sayılar reddedildi: {reddedilen}"

    def test_uydurulmus_sayi_reddedilir(self) -> None:
        """Kalkanın var oluş sebebi: kayıtta olmayan oran cevaba giremez."""
        kayit = _kayit(kar_payi_orani=1.89, vade_ay_max=120)
        gecti, reddedilen = sayisal_dogrulama(
            "Kâr payı oranı aylık %2.45'tir.", [kayit]
        )
        assert not gecti
        assert "2.45" in reddedilen

    def test_bos_kayitla_her_sayi_reddedilir(self) -> None:
        gecti, reddedilen = sayisal_dogrulama("Oran %3,10 ve vade 96 aydır.", [])
        assert not gecti
        assert reddedilen

    def test_sayisiz_cevap_gecer(self) -> None:
        gecti, _ = sayisal_dogrulama("Bu bilgi veri setinde bulunmuyor.", [])
        assert gecti

    def test_tek_haneli_sayilar_gurultu_uretmez(self) -> None:
        """Madde numarası gibi tek haneler halüsinasyon sayılmamalı."""
        gecti, _ = sayisal_dogrulama("1. madde geçerlidir.", [])
        assert gecti

    def test_sistem_aciklamasi_veri_iddiasi_sayilmaz(self) -> None:
        """Regresyon: 9 Ağustos 2026.

        Karşılaştırma cevabının sonundaki açıklama, skor ağırlıklarını
        (%40, %25, %20, %15) ve hesaplanan skoru (0,625) içeriyor. Kalkan
        bunları veri iddiası sanıp GEÇERLİ bir cevabı engelliyordu.

        Çözüm kalkanı gevşetmek değil — asıl iş onun sıkı kalması. Doğru
        çözüm, denetlenecek metni doğru seçmek: `Cevap.dogrulanacak_metin`.
        """
        from src.rag.chatbot import Cevap, Niyet

        kayit = _kayit(kar_payi_orani=1.89, vade_ay_max=120)
        veri = "Vade açısından A Bankası daha avantajlıdır, çünkü 120 ay vade sunmaktadır."
        aciklama = "Ağırlıklar: kâr payı %40, masraf %25, vade %20, ödül %15. Skor 0.625."

        cevap = Cevap(
            metin=veri + "\n" + aciklama,
            dogrulanacak_metin=veri,
            niyet=Niyet.KARSILASTIRMA,
            kullanilan_kayitlar=[kayit],
        )

        gecti, reddedilen = sayisal_dogrulama(cevap.denetlenecek(), cevap.kullanilan_kayitlar)
        assert gecti, f"Geçerli cevap engellendi: {reddedilen}"

        # Karşı kontrol: tüm metin denetlenseydi kalkan (haklı olarak) takılırdı.
        gecti_hepsi, _ = sayisal_dogrulama(cevap.metin, cevap.kullanilan_kayitlar)
        assert not gecti_hepsi, "Kalkan gevşemiş olmamalı — açıklama sayıları veride yok"

    def test_kalkan_hala_uydurma_orani_yakaliyor(self) -> None:
        """Yukarıdaki düzeltme kalkanı işlevsiz bırakmamalı."""
        from src.rag.chatbot import Cevap, Niyet

        kayit = _kayit(kar_payi_orani=1.89)
        cevap = Cevap(
            metin="Kâr payı oranı %7,77'dir.",
            dogrulanacak_metin="Kâr payı oranı %7,77'dir.",
            niyet=Niyet.TEKIL_SORGU,
            kullanilan_kayitlar=[kayit],
        )
        gecti, reddedilen = sayisal_dogrulama(cevap.denetlenecek(), cevap.kullanilan_kayitlar)
        assert not gecti
        assert "7,77" in reddedilen


class TestNiyetYonlendirici:
    @pytest.mark.parametrize(
        ("soru", "beklenen"),
        [
            # Şartname madde 11, Senaryo 1
            ("A Bankası'nın konut finansmanı oranı ne?", Niyet.TEKIL_SORGU),
            # Şartname madde 11, Senaryo 2
            ("A Bankası mı daha avantajlı, C Bankası mı?", Niyet.KARSILASTIRMA),
            # Türkçe ünlü uyumu: mi / mı / mu / mü
            ("Kuveyt Türk mü daha avantajlı?", Niyet.KARSILASTIRMA),
            ("En düşük kâr payı hangi bankada?", Niyet.KARSILASTIRMA),
            ("Kampanya koşulları neler?", Niyet.KOSUL_SORGUSU),
            ("Hava durumu nasıl?", Niyet.KAPSAM_DISI),
            ("Hesabıma gir ve para gönder", Niyet.KAPSAM_DISI),
        ],
    )
    def test_yonlendirme(self, soru: str, beklenen: Niyet) -> None:
        assert niyet_belirle(soru) == beklenen


class TestKanitZinciri:
    def test_kural_katmani_kaynak_bagliyor(self) -> None:
        alanlar = kurallarla_cikar(ORNEK_METIN, "https://ornek.test", datetime.now())
        assert alanlar, "Kural katmanı örnek metinden hiçbir alan çıkaramadı"
        for ad, alan in alanlar.items():
            assert alan.kaynak is not None, f"{ad} kaynaksız üretildi"
            assert alan.kaynak.alinti in ORNEK_METIN, f"{ad} alıntısı metinde yok"
            assert alan.yontem == "kural"

    def test_beklenen_degerler_bulunuyor(self) -> None:
        alanlar = kurallarla_cikar(ORNEK_METIN, "https://ornek.test", datetime.now())
        assert alanlar["kar_payi_orani"].deger == pytest.approx(1.89)
        assert alanlar["vade_ay_max"].deger == 120
        assert alanlar["masrafsiz_mi"].deger is True

    def test_tutar_tahsis_ucreti_ile_karistirilmaz(self) -> None:
        """Regresyon: 9 Ağustos 2026.

        "5.000.000 TL'ye kadar finansman. Dosya masrafı alınmaz." cümlelerinde
        çıkarım motoru 5 milyon TL'yi TAHSİS ÜCRETİ olarak etiketliyordu ve
        finansman tutarını tamamen kaçırıyordu. Sebep: dışlayıcı sözcük kontrolü
        mesafeye duyarsızdı ve cümle sınırı gözetilmiyordu.
        """
        alanlar = kurallarla_cikar(ORNEK_METIN, "https://ornek.test", datetime.now())

        assert alanlar["finansman_tutari_max"].deger == pytest.approx(5_000_000.0)
        assert "tahsis_ucreti" not in alanlar, (
            "Masrafsız olduğu açıkça yazan bir kampanyaya tahsis ücreti atandı: "
            f"{alanlar.get('tahsis_ucreti')}"
        )

    def test_olumsuzlanmis_masraftan_tutar_cikarilmaz(self) -> None:
        """"ücret alınmaz" diyen cümledeki sayı, o ücretin tutarı değildir."""
        metin = "Kampanya kapsamında 250.000 TL finansman sağlanır. Tahsis ücreti alınmaz."
        alanlar = kurallarla_cikar(metin, "https://ornek.test", datetime.now())
        assert alanlar.get("tahsis_ucreti") is None

    def test_gercek_tahsis_ucreti_yakalanir(self) -> None:
        """Karşı kontrol: gerçek bir tahsis ücreti hâlâ çıkarılabilmeli.

        Önceki iki test yalnız 'reddet' davranışını ölçüyor; bu test kuralın
        aşırı kısıtlanıp işlevsiz kalmadığını doğrular.
        """
        metin = "Konut finansmanında 7.500 TL tahsis ücreti alınmaktadır."
        alanlar = kurallarla_cikar(metin, "https://ornek.test", datetime.now())
        assert alanlar["tahsis_ucreti"].deger == pytest.approx(7500.0)

    def test_degersiz_alan_belirtilmemis_isaretlenir(self) -> None:
        """Şartname madde 11 'Belirtilmemiş' ifadesini birebir kullanıyor."""
        alan = Alan.yok()
        assert alan.goster() == "Belirtilmemiş"
        assert alan.yontem == "belirtilmemis"
        assert not alan.var_mi

    def test_kanitsiz_deger_uretilemez(self) -> None:
        """Şema düzeyinde kısıt: değer varsa yöntem beyan edilmek zorunda."""
        with pytest.raises(ValueError, match="belirtilmemis"):
            Alan(deger=2.05, yontem="belirtilmemis")

    def test_kanit_denetimi_uydurmayi_yakalar(self) -> None:
        kampanya = Kampanya(
            banka_adi="Test",
            banka_kodu="0205",
            kampanya_id="X",
            kaynak_url="https://ornek.test",
            cekim_tarihi=datetime.now(),
            ham_metin=ORNEK_METIN,
            kar_payi_orani=Alan(
                deger=9.99,
                ham_ifade="%9,99",  # metinde YOK
                kaynak=Kaynak(
                    url="https://ornek.test",
                    cekim_tarihi=datetime.now(),
                    alinti=ORNEK_METIN[:50],
                    karakter_baslangic=0,
                    karakter_bitis=50,
                ),
                guven=0.9,
                yontem="llm",
            ),
        )
        ihlaller = kampanya.kanit_denetimi()
        assert any("kar_payi_orani" in i for i in ihlaller)

    def test_siniflandirma_etiketi_halusinasyon_sayilmaz(self) -> None:
        """kampanya_turu bir enum etiketidir, metinde geçmesi beklenmez."""
        from src.schema import KampanyaTuru

        kampanya = Kampanya(
            banka_adi="Test",
            banka_kodu="0205",
            kampanya_id="X",
            kaynak_url="https://ornek.test",
            cekim_tarihi=datetime.now(),
            ham_metin=ORNEK_METIN,
            kampanya_turu=Alan(
                deger=KampanyaTuru.KONUT_FINANSMANI,
                ham_ifade="konut_finansmani",
                guven=0.8,
                yontem="llm",
            ),
        )
        assert kampanya.kanit_denetimi() == []
