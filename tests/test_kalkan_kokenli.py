"""Köken tipli sayısal doğrulama kalkanı (bulgu 1.2).

Bu testler tek bir iddiayı korur: **kalkan gevşemedi, sertleşti.**

18 Ağustos ölçümünde kalkan iki hatayı birden yapıyordu:

  * MEŞRU CEVABI ENGELLİYORDU — koşul sorularında bankanın kendi metninden
    alınan paragraf, yapısal alana karşı denetleniyordu. Metindeki sayı
    yapısal alanda bulunamayınca cevap bloklanıyordu. 10 doğal soruda 2 blok.
  * KÖR NOKTASI VARDI — `dogrulanacak_metin` ikili bir muafiyetti; skor ve
    ağırlık bölümüne yazılan hiçbir sayı denetlenmiyordu.

Çözüm kalkanı gevşetmek değil, ona parçanın KÖKENİNİ bildirmekti. Aşağıdaki
testler bunun her iki yönünü de sabitler: yanlış blok gitti, yeni garantiler
geldi, eski sertlik yerinde.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from src.depolama import KampanyaKaydi
from src.rag.chatbot import (
    Cevap,
    CevapParcasi,
    Koken,
    Niyet,
    kalkandan_gecir,
    sor,
)

HAM_METIN = (
    "Hayat Finans Katılım Bankası dijital başvuru kampanyası.\n"
    "Başvurunuz en geç 17 iş günü içinde sonuçlandırılır ve onay sonrası "
    "tutar hesabınıza aktarılır.\n"
    "Kampanya kapsamında aylık kâr payı oranı %1,89'dan başlamaktadır.\n"
)


def _kayit(**alanlar: object) -> KampanyaKaydi:
    varsayilan = {
        "kampanya_id": "0212-test",
        "banka_kodu": "0212",
        "banka_adi": "Hayat Finans Katılım Bankası A.Ş.",
        "kaynak_url": "https://ornek.test/kampanya",
        "cekim_tarihi": datetime(2026, 8, 9, 12, 0),
        "tam_kayit": {},
        "ham_metin": HAM_METIN,
        # Veritabanı varsayılanları (`mapped_column(default=...)`) yalnız
        # INSERT sırasında uygulanır; bellekte kurulan kayıtta None kalır.
        # Fikstür, okunmuş bir kaydı taklit etmeli.
        "ortalama_guven": 0.0,
        "doluluk_orani": 0.0,
    }
    return KampanyaKaydi(**{**varsayilan, **alanlar})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 1) Giderilen hata — alıntıdaki kaynak sayısı meşrudur
# ---------------------------------------------------------------------------


class TestAlintiYanlisBlokGitti:
    def test_kaynak_metnindeki_sayi_bloklanmaz(self) -> None:
        """REGRESYON — "17 iş günü" yapısal alanda YOK ama metinde VAR.

        Eski kalkan bunu "doğrulanamayan sayı" sayıp cevabı engelliyordu:
        `sor("Hayat Finans başvuru nasıl yapılır?")` -> reddedilen ['17'].
        """
        kayit = _kayit(kar_payi_orani=1.89)
        alinti = "Başvurunuz en geç 17 iş günü içinde sonuçlandırılır"
        cevap = Cevap(
            parcalar=[
                CevapParcasi(
                    f"**{kayit.banka_adi}:** {alinti}",
                    Koken.ALINTI,
                    kayit_id=kayit.kampanya_id,
                    alinti=alinti,
                )
            ],
            niyet=Niyet.KOSUL_SORGUSU,
            kullanilan_kayitlar=[kayit],
        )
        gecti, reddedilen = kalkandan_gecir(cevap, [kayit])
        assert gecti, f"Bankanın kendi metnindeki sayı engellendi: {reddedilen}"

    def test_alinti_disina_eklenen_sayi_bloklanir(self) -> None:
        """Alıntı köken bir serbest geçiş kartı DEĞİL.

        Alıntının dışına eklenmiş, ne kaynakta ne yapısal alanda karşılığı
        olan bir sayı hâlâ reddedilir.
        """
        kayit = _kayit(kar_payi_orani=1.89)
        alinti = "Başvurunuz en geç 17 iş günü içinde sonuçlandırılır"
        cevap = Cevap(
            parcalar=[
                CevapParcasi(
                    f"**{kayit.banka_adi}:** {alinti} (toplam 9.999 TL masrafla)",
                    Koken.ALINTI,
                    kayit_id=kayit.kampanya_id,
                    alinti=alinti,
                )
            ],
            kullanilan_kayitlar=[kayit],
        )
        gecti, reddedilen = kalkandan_gecir(cevap, [kayit])
        assert not gecti
        assert "9.999" in reddedilen


# ---------------------------------------------------------------------------
# 2) YENİ garanti — alıntı bütünlüğü (eski kalkanda hiç yoktu)
# ---------------------------------------------------------------------------


class TestAlintiButunlugu:
    def test_kaynakta_olmayan_alinti_bloklanir(self) -> None:
        """Uydurulmuş bir "alıntı" cevaba giremez.

        Eski kalkanda böyle bir denetim YOKTU: alıntı diye sunulan bir cümle
        hiçbir yerde kaynağıyla karşılaştırılmıyordu.
        """
        kayit = _kayit()
        uydurma = "Kampanya tüm müşterilerimize sınırsız avantaj sunmaktadır"
        assert uydurma not in HAM_METIN
        cevap = Cevap(
            parcalar=[
                CevapParcasi(
                    uydurma, Koken.ALINTI, kayit_id=kayit.kampanya_id, alinti=uydurma
                )
            ],
            kullanilan_kayitlar=[kayit],
        )
        gecti, reddedilen = kalkandan_gecir(cevap, [kayit])
        assert not gecti
        assert any("kaynak metinde yok" in r for r in reddedilen)

    def test_baskasinin_kaydina_baglanan_alinti_bloklanir(self) -> None:
        """Alıntı, GÖSTERİLDİĞİ kaydın metninden gelmek zorundadır."""
        kaynak = _kayit()
        yabanci = _kayit(kampanya_id="0203-baska", ham_metin="Bambaşka bir metin.")
        alinti = "Başvurunuz en geç 17 iş günü içinde sonuçlandırılır"
        cevap = Cevap(
            parcalar=[
                CevapParcasi(
                    alinti, Koken.ALINTI, kayit_id=yabanci.kampanya_id, alinti=alinti
                )
            ],
            kullanilan_kayitlar=[kaynak, yabanci],
        )
        gecti, _ = kalkandan_gecir(cevap, [kaynak, yabanci])
        assert not gecti


# ---------------------------------------------------------------------------
# 3) Kapatılan kör nokta — SISTEM parçası yeniden hesaplanır
# ---------------------------------------------------------------------------


class TestSistemHesabiDogrulanir:
    def test_dogru_hesap_gecer(self) -> None:
        cevap = Cevap(
            parcalar=[
                CevapParcasi(
                    "Ağırlıklar: kâr payı %40, masraf %25, vade %20, ödül %15. "
                    "Skor 0.625.",
                    Koken.SISTEM,
                    hesap={
                        "kar_payi": 40.0, "masraf": 25.0, "vade": 20.0,
                        "odul": 15.0, "skor": 0.625,
                    },
                )
            ],
        )
        gecti, reddedilen = kalkandan_gecir(cevap, [])
        assert gecti, f"Yeniden üretilebilir hesap engellendi: {reddedilen}"

    def test_elle_yazilmis_skor_bloklanir(self) -> None:
        """KÖR NOKTANIN KAPANDIĞININ KANITI.

        Eski kalkanda bu metin `dogrulanacak_metin` sayesinde HİÇ
        denetlenmiyordu; açıklama bölümüne istenen skor yazılabilirdi.
        """
        cevap = Cevap(
            parcalar=[
                CevapParcasi(
                    "Ağırlıklar: kâr payı %40, masraf %25, vade %20, ödül %15. "
                    "Skor 0.999.",  # <- hesap 0,625 üretti, metne 0,999 yazıldı
                    Koken.SISTEM,
                    hesap={
                        "kar_payi": 40.0, "masraf": 25.0, "vade": 20.0,
                        "odul": 15.0, "skor": 0.625,
                    },
                )
            ],
        )
        gecti, reddedilen = kalkandan_gecir(cevap, [])
        assert not gecti, "Hesaptan üretilemeyen skor geçti — kör nokta duruyor"
        assert "0.999" in reddedilen


# ---------------------------------------------------------------------------
# 4) Eski sertlik yerinde — YAPISAL köken değişmedi
# ---------------------------------------------------------------------------


class TestYapisalSertligiKorundu:
    def test_uydurma_oran_hala_bloklanir(self) -> None:
        """Kalkanın var oluş sebebi. Bu test kırılırsa düzeltme kalkanı bozmuş demektir."""
        kayit = _kayit(kar_payi_orani=1.89)
        cevap = Cevap(
            parcalar=[CevapParcasi("Kâr payı oranı aylık %7,77'dir.", Koken.YAPISAL)],
            kullanilan_kayitlar=[kayit],
        )
        gecti, reddedilen = kalkandan_gecir(cevap, [kayit])
        assert not gecti
        assert "7,77" in reddedilen

    def test_yapisal_koken_ham_metne_bakmaz(self) -> None:
        """YAPISAL parça, ham metinde geçse bile yapısal alanda yoksa reddedilir.

        Köken ayrımının anlamı budur: veri İDDİASI, alıntıdan farklı bir
        ölçüte tabidir. "17" ham metinde var ama bir veri iddiası olarak
        sunulamaz.
        """
        kayit = _kayit(kar_payi_orani=1.89)
        assert "17" in HAM_METIN
        cevap = Cevap(
            parcalar=[CevapParcasi("Azami vade 17 aydır.", Koken.YAPISAL)],
            kullanilan_kayitlar=[kayit],
        )
        gecti, reddedilen = kalkandan_gecir(cevap, [kayit])
        assert not gecti
        assert "17" in reddedilen

    def test_kayittaki_sayi_gecer(self) -> None:
        kayit = _kayit(kar_payi_orani=1.89, vade_ay_max=120)
        cevap = Cevap(
            parcalar=[CevapParcasi("Kâr payı %1,89, vade 120 ay.", Koken.YAPISAL)],
            kullanilan_kayitlar=[kayit],
        )
        gecti, reddedilen = kalkandan_gecir(cevap, [kayit])
        assert gecti, f"Doğru sayılar reddedildi: {reddedilen}"


# ---------------------------------------------------------------------------
# 5) Köken sözleşmesi yapıcıda denetlenir — `Alan._kanit_zinciri` refleksi
# ---------------------------------------------------------------------------


class TestKokenSozlesmesi:
    def test_alinti_kayit_id_zorunlu(self) -> None:
        with pytest.raises(ValueError, match="kayit_id"):
            CevapParcasi("bir alıntı", Koken.ALINTI, alinti="bir alıntı")

    def test_alinti_ham_alinti_zorunlu(self) -> None:
        with pytest.raises(ValueError, match="ham alıntıyı"):
            CevapParcasi("bir alıntı", Koken.ALINTI, kayit_id="0212-test")

    def test_sistem_hesap_zorunlu(self) -> None:
        with pytest.raises(ValueError, match="hesap"):
            CevapParcasi("Skor 0.625.", Koken.SISTEM)

    def test_duz_parca_sayi_iceremez(self) -> None:
        """DUZ, "denetlenmeyen metin" demek. Sayı taşıyorsa kaçış deliği olurdu."""
        with pytest.raises(ValueError, match="sayı içeremez"):
            CevapParcasi("Kâr payı oranı %2,05'tir.", Koken.DUZ)

    def test_duz_parca_sayisiz_metni_kabul_eder(self) -> None:
        parca = CevapParcasi("Veri setinde bulunan ilgili bilgiler:", Koken.DUZ)
        assert parca.koken is Koken.DUZ


# ---------------------------------------------------------------------------
# 6) SINIF TESTİ — üreticiler kökensiz/miras parça bırakamaz
# ---------------------------------------------------------------------------


SORULAR = [
    "Kuveyt Türk kampanya koşulları nelerdir?",
    "Hayat Finans başvuru nasıl yapılır?",
    "Dünya Katılım kart kampanyası kapsamı nedir?",
    "Vakıf Katılım ile Ziraat Katılım hangisi daha avantajlı?",
    "Türkiye Finans taşıt kampanyasında vade kaç ay?",
    "Konut finansmanı için başvuru şartları nelerdir?",
    "Emeklilere özel kampanya var mı?",
    "En düşük kâr payı oranını hangi banka veriyor?",
    "Hava durumu nasıl?",
    "Bulunmayan Banka A.Ş. oranı ne kadar?",
]


def _demo_kayitlari() -> list[KampanyaKaydi]:
    return [
        _kayit(kar_payi_orani=1.89, vade_ay_max=120, kampanya_bitis=date(2026, 12, 31)),
        _kayit(
            kampanya_id="0203-test",
            banka_kodu="0203",
            banka_adi="Albaraka Türk Katılım Bankası A.Ş.",
            ham_metin=(
                "Albaraka Türk konut finansmanı başvuru şartları.\n"
                "Kampanya kapsamında 48 aya kadar vade sunulmaktadır.\n"
            ),
            vade_ay_max=48,
            odul_miktari=2000.0,
        ),
    ]


class TestUreticiKapsamasi:
    @pytest.mark.parametrize("soru", SORULAR)
    def test_hicbir_uretici_denetimsiz_parca_uretmez(self, soru: str) -> None:
        """Miras yolun (`Koken.DENETIMSIZ`) chatbot üreticilerinde borcu SIFIR.

        Yeni bir cevap üreticisi `metin=` ile yazılırsa bu test kırılır ve
        muafiyet sessizce geri gelemez.
        """
        cevap = sor(soru, _demo_kayitlari())
        assert cevap.denetimsiz_parca_sayisi() == 0, (
            f"{soru!r} miras yoldan {cevap.denetimsiz_parca_sayisi()} parça üretti"
        )

    @pytest.mark.parametrize("soru", SORULAR)
    def test_her_parcanin_kokeni_atanmis(self, soru: str) -> None:
        cevap = sor(soru, _demo_kayitlari())
        assert cevap.parcalar, f"{soru!r} hiç parça üretmedi"
        assert all(isinstance(p.koken, Koken) for p in cevap.parcalar)

    @pytest.mark.parametrize("soru", SORULAR)
    def test_mesru_sorular_bloklanmaz(self, soru: str) -> None:
        """YANLIŞ BLOK ORANI HEDEFİ: %0.

        18 Ağustos ölçümü %20'ydi (10 soruda 2 blok). Bu test o oranı
        sıfırda sabitler; bir üretici köken ataması bozarsa geri gelir.
        """
        cevap = sor(soru, _demo_kayitlari())
        assert cevap.dogrulama_gecti, (
            f"{soru!r} engellendi, reddedilen: {cevap.reddedilen_sayilar}"
        )


# ---------------------------------------------------------------------------
# 7) Miras yol anlamı korur ve GÖRÜNÜR kalır
# ---------------------------------------------------------------------------


class TestMirasYol:
    def test_metin_kwargi_yapisal_parcaya_donusur(self) -> None:
        cevap = Cevap(metin="Kâr payı %2,05'tir.", niyet=Niyet.TEKIL_SORGU)
        assert [p.koken for p in cevap.parcalar] == [Koken.YAPISAL]
        assert cevap.metin == "Kâr payı %2,05'tir."

    def test_dogrulanacak_metin_muafiyeti_sayilir(self) -> None:
        """Miras muafiyet yok olmadı; GÖRÜNÜR ve SAYILABİLİR hâle geldi."""
        veri = "Vade 120 aydır."
        cevap = Cevap(metin=veri + "\nSkor 0.625.", dogrulanacak_metin=veri)
        assert [p.koken for p in cevap.parcalar] == [Koken.YAPISAL, Koken.DENETIMSIZ]
        assert cevap.denetimsiz_parca_sayisi() == 1

    def test_parcalar_ve_metin_birlikte_verilemez(self) -> None:
        with pytest.raises(ValueError, match="birlikte verilemez"):
            Cevap(parcalar=[CevapParcasi("x", Koken.DUZ)], metin="y")
