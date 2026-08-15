"""Kural katmanı testleri — çekirdeği şartnamenin KENDİ örneğidir.

Şartname madde 11'de jüri, üç bankanın kampanya metnini ve bu metinlerden
çıkarılmasını beklediği tabloyu birlikte veriyor. Bu, elimizdeki tek RESMÎ
doğru cevap anahtarıdır: altın setten bağımsızdır, tartışmaya kapalıdır ve
demo sırasında jürinin deneyeceği ilk şey büyük olasılıkla budur.

Bu yüzden o tablo burada test olarak sabitlenmiştir. 14 Ağustos'ta koşulduğunda
12 iddiadan 4'ü başarısızdı (bkz. sınıf içi notlar); düzeltmelerin geri
gelmemesinin güvencesi bu dosyadır.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.extraction.kural import kurallarla_cikar

CEKIM = datetime(2026, 8, 14, 12, 0)

# --- Şartname madde 11, Örnek Temsili Senaryo-1 metinleri (BİREBİR) ---------

A_BANKASI = (
    "Yeni ev sahibi olmak isteyen müşterilerimize özel %1,89 kâr payı oranı ile "
    "120 aya kadar konut finansmanı fırsatı sunulmaktadır. Kampanya kapsamında "
    "50.000 TL'ye kadar dosya masrafı alınmamaktadır. Kampanya 31 Aralık 2026 "
    "tarihine kadar geçerlidir."
)

B_BANKASI = (
    "Konut finansmanında avantajlı ödeme seçenekleri. %1,95 kâr payı oranı ile "
    "120 ay vadeye kadar finansman imkanı sunulmaktadır. Kampanya kapsamında "
    "ekspertiz ücreti banka tarafından karşılanmaktadır."
)

C_BANKASI = (
    "Yeni konut alımlarına özel %1,87 kâr payı oranı ile 96 ay vadeli konut "
    "finansmanı fırsatı. Kampanya kapsamında 5.000 TL değerinde alışveriş çeki "
    "verilmektedir."
)


def cikar(metin: str) -> dict[str, object]:
    """Alan adı -> değer sözlüğü. Bulunmayan alan sözlükte YOKTUR."""
    return {
        ad: alan.deger
        for ad, alan in kurallarla_cikar(metin, "https://test.local", CEKIM).items()
    }


class TestSartnameMadde11:
    """Jürinin yayımladığı tablo. Her iddia şartname sayfa 12'den gelir."""

    @pytest.mark.parametrize(
        ("metin", "beklenen_oran", "beklenen_vade"),
        [(A_BANKASI, 1.89, 120), (B_BANKASI, 1.95, 120), (C_BANKASI, 1.87, 96)],
    )
    def test_oran_ve_vade(self, metin: str, beklenen_oran: float, beklenen_vade: int) -> None:
        alanlar = cikar(metin)
        assert alanlar.get("kar_payi_orani") == pytest.approx(beklenen_oran)
        assert alanlar.get("vade_ay_max") == beklenen_vade

    def test_a_bankasi_masrafi_ucret_sanmaz(self) -> None:
        """«50.000 TL'ye kadar dosya masrafı ALINMAMAKTADIR» -> ücret YOK.

        Regresyon: -mAktAdır kipi olumsuzlama listesinde olmadığı için bu
        cümleden 50.000 TL'lik bir tahsis ücreti çıkarılıyordu. Aynı kayıtta
        `masrafsiz_mi=True` de bulunduğu için kayıt kendi içinde çelişiyordu.
        """
        alanlar = cikar(A_BANKASI)
        assert "tahsis_ucreti" not in alanlar
        assert alanlar.get("masrafsiz_mi") is True

    def test_b_bankasi_bankanin_karsiladigi_ucret_masrafsizdir(self) -> None:
        """«Ekspertiz ücreti banka tarafından karşılanmaktadır» -> masrafsız.

        Yüklem OLUMLU ama masraf müşteriye yansımıyor; şartname tablosu bunu
        «Ekspertiz ücretsiz» olarak gösteriyor.
        """
        assert cikar(B_BANKASI).get("masrafsiz_mi") is True

    def test_c_bankasi_hediye_ceki_finansman_tutari_degildir(self) -> None:
        """«5.000 TL değerinde alışveriş çeki» ödüldür, finansman limiti değil.

        Regresyon: aynı cümlede "konut finansmanı" geçtiği için 5.000 TL
        `finansman_tutari_max` alanına düşüyordu.
        """
        alanlar = cikar(C_BANKASI)
        assert "finansman_tutari_max" not in alanlar
        assert alanlar.get("odul_miktari") == pytest.approx(5000.0)

    def test_c_bankasinda_masraf_beyani_yoktur(self) -> None:
        """Metin masraftan hiç söz etmiyor; «Belirtilmemiş» doğru cevaptır.

        Şartname tablosu bu hücreyi «Masraf belirtilmemiş» olarak dolduruyor.
        Uydurulmuş bir `masrafsiz_mi=True`, olmayan bir avantaj vaat ederdi.
        """
        assert "masrafsiz_mi" not in cikar(C_BANKASI)

    def test_a_bankasi_kampanya_bitisi(self) -> None:
        assert str(cikar(A_BANKASI).get("kampanya_bitis")) == "2026-12-31"


class TestOlumsuzlamaKipleri:
    """Bankaların resmî yazım kipi -mAktAdır'dır; kalıp listesi yetmez."""

    @pytest.mark.parametrize(
        "cumle",
        [
            "Dosya masrafı alınmamaktadır.",
            "Tahsis ücreti tahsil edilmemektedir.",
            "Komisyon uygulanmamaktadır.",
            "Dosya masrafı alınmaz.",
            "Masraf yansıtılmamaktadır.",
        ],
    )
    def test_olumsuz_masraf_cumlesinden_ucret_cikmaz(self, cumle: str) -> None:
        metin = f"Konut finansmanı kampanyası. 25.000 TL'ye kadar {cumle}"
        assert "tahsis_ucreti" not in cikar(metin)

    def test_olumlu_masraf_cumlesinden_ucret_cikar(self) -> None:
        """Olumsuzlamayı geniş tutmak, gerçek ücreti kaçırmamalı."""
        metin = "Finansman kullandırımında 750 TL tahsis ücreti alınır."
        assert cikar(metin).get("tahsis_ucreti") == pytest.approx(750.0)


class TestVadeBaglami:
    def test_kisa_metinde_vade_sozcugu_olmadan_yakalanir(self) -> None:
        """"120 aya kadar" kendi başına bir vade ifadesidir.

        Uzun sayfalarda "vade" sözcüğü pencerede zaten geçtiği için bu eksik
        görünmüyordu; kısa metinlerde (şartname örneği, `/extract` uç noktasına
        yapıştırılan metin) görünüyor.
        """
        assert cikar("36 aya kadar finansman imkânı.").get("vade_ay_max") == 36

    def test_en_yuksek_vade_secilir(self) -> None:
        """Kademeli tabloda `vade_ay_max` azami olanı almalı.

        Gerçek kayıt (Albaraka ihtiyaç finansmanı) bu biçimde yazılmış ve
        düzeltmeden önce 36 yerine 24 çıkarılıyordu.
        """
        metin = (
            "125.000 TL'ye kadar olan finansmanlarda 36 aya kadar, "
            "125.000 – 250.000 TL ye kadar olan finansmanlarda 24 aya kadar, "
            "250.000 TL ve üzerindeki finansmanlar ise 12 aya kadar vade "
            "seçeneklerinden faydalanabilirsiniz."
        )
        assert cikar(metin).get("vade_ay_max") == 36


class TestMakullukAraligi:
    def test_makul_olmayan_oran_kar_payi_sayilmaz(self) -> None:
        """"Yıllık Maliyet Oranı % 82,44" aylık kâr payı DEĞİLDİR."""
        assert "kar_payi_orani" not in cikar("Yıllık Maliyet Oranı\n% 82,44")

    def test_makul_oran_kabul_edilir(self) -> None:
        assert cikar("Aylık kâr payı oranı %2,05").get("kar_payi_orani") == pytest.approx(2.05)

    def test_ucret_tarifesi_orani_kar_payi_sayilmaz(self) -> None:
        """Havale komisyonu (% 0,05) aylık kâr payı DEĞİLDİR.

        Gerçek kayıt: Albaraka ürün-hizmet ücretleri tablosu. Binde beşlik bu
        oran "en düşük kâr payı" sıralamasının tepesine oturup tüm
        karşılaştırmayı bozuyordu.
        """
        metin = "Giden Fon Transferi | USD | 25 | % 0.05 | 5000 | kâr payı oranı"
        assert "kar_payi_orani" not in cikar(metin)


class TestFinansmanTutariMakulluk:
    """Her TL tutarı bir finansman limiti değildir."""

    @pytest.mark.parametrize(
        "metin",
        [
            "Miles&Smiles kredi kartınız ile 1.000 TL ve üzeri harcamanıza finansman avantajı.",
            "Kazanılacak nakit ödül günlük maksimum 100 TL olup finansman limitine sayılmaz.",
            "2.500 TL'ye kadar kullanılan yedek hesap limitine kâr payı işletilmez.",
        ],
    )
    def test_kucuk_tutarlar_finansman_limiti_sayilmaz(self, metin: str) -> None:
        """Bunların hepsinde "finansman"/"limit" sözcüğü YAKINDA geçiyor.

        Bağlam kontrolü kurtarmıyor; ayıran tek şey büyüklük. Ölçüm: dolu 31
        kaydın 10'u bu türdendi.
        """
        assert "finansman_tutari_max" not in cikar(metin)

    def test_gercek_finansman_limiti_kabul_edilir(self) -> None:
        assert cikar(
            "5.000.000 TL'ye kadar konut finansmanı imkânı."
        ).get("finansman_tutari_max") == pytest.approx(5_000_000.0)

    def test_kurumsal_buyuk_limit_elenmez(self) -> None:
        """Üst sınır bilinçli olarak YOK — yüz milyonlu limitler gerçektir."""
        assert cikar(
            "Hesapta 1.000 TL alt limit ve 150.000.000 TL üst limit bulunmaktadır. Finansman limiti."
        ).get("finansman_tutari_max") == pytest.approx(150_000_000.0)


class TestKismiJsonKurtarma:
    """LLM çıktısı yarıda kesildiğinde tamamlanmış alanlar kaybolmamalı.

    Eskiden `json.loads` hatası tüm kayıt için `{}` döndürüyordu: 15 alanın
    14'ü doğru üretilmiş olsa bile hepsi birden düşüyor, kayıt yine de
    yazıldığı için hata hiçbir yerde görünmüyordu.
    """

    def test_kesilmis_ciktidan_alanlar_kurtarilir(self) -> None:
        from src.extraction.llm import _kismi_json_kurtar

        kesik = (
            '{"kampanya_turu": "konut_finansmani", "hedef_kitle": null, '
            '"masrafsiz_mi": true, "kampanya_avantaji": "Avantaj'
        )
        kurtarilan = _kismi_json_kurtar(kesik)
        assert kurtarilan["kampanya_turu"] == "konut_finansmani"
        assert kurtarilan["masrafsiz_mi"] is True
        assert "kampanya_avantaji" not in kurtarilan  # yarım alan ALINMAZ

    def test_gecerli_json_bozulmaz(self) -> None:
        from src.extraction.llm import _kismi_json_kurtar

        assert _kismi_json_kurtar('{"a": 1}') == {"a": 1}

    def test_kapanis_parantezi_eksik(self) -> None:
        from src.extraction.llm import _kismi_json_kurtar

        assert _kismi_json_kurtar('{"a": 1, "b": 2') == {"a": 1, "b": 2}

    def test_kurtarilamayan_bos_doner(self) -> None:
        from src.extraction.llm import _kismi_json_kurtar

        assert _kismi_json_kurtar("merhaba dünya") == {}
        assert _kismi_json_kurtar("") == {}
        assert _kismi_json_kurtar("[1, 2, 3") == {}


class TestTabloKolonAyrimi:
    """Tabloda anlamı uzaklık değil KOLON belirler.

    Banka oran tabloları düz metne serilince `Kâr Payı Oranı` ve
    `Tahsis Ücreti` kolonları yan yana düşüyor; karakter penceresine bakan
    bağlam kontrolü ikisini ayırt edemiyordu. 15 Ağustos altın set ölçümünde
    `kar_payi_orani`'nin 12 uyuşmazlığından 5'i tam olarak buydu — sistem
    tahsis ücretini (%0,50) kâr payı sanıyordu.
    """

    TABLO = (
        "Sigortalı İhtiyaç Finansmanı Kâr Payı Oranları ve Maliyet Tablosu "
        "Vade | Kâr Payı Oranı | Tahsis Ücreti | Aylık Toplam Maliyet | "
        "Yıllık Toplam Maliyet | "
        "3 | 4,20% | 0,50% | 5,77% | 96,05% | "
        "12 | 4,15% | 0,50% | 5,50% | 90,09% | "
        "36 | 3,80% | 0,50% | 4,98% | 79,27% |"
    )

    def test_tahsis_kolonu_kar_payi_sayilmaz(self) -> None:
        assert cikar(self.TABLO).get("kar_payi_orani") != pytest.approx(0.50)

    def test_kar_payi_kolonundan_en_dusuk_alinir(self) -> None:
        """Kılavuz: kademeli tabloda müşteri lehine uç yazılır."""
        assert cikar(self.TABLO).get("kar_payi_orani") == pytest.approx(3.80)

    def test_maliyet_kolonlari_kar_payi_sayilmaz(self) -> None:
        """`Aylık/Yıllık Toplam Maliyet` de oran kolonudur ama kâr payı değildir."""
        deger = cikar(self.TABLO).get("kar_payi_orani")
        for maliyet in (5.77, 4.98):
            assert deger != pytest.approx(maliyet)

    def test_tablo_disi_metin_eski_yoldan_cikarilir(self) -> None:
        """Kolon mantığı yalnız tabloda devreye girer; düz cümle bozulmamalı."""
        assert cikar(A_BANKASI)["kar_payi_orani"] == pytest.approx(1.89)


class TestFinansmanDisiUcret:
    """`masrafsiz_mi` finansmanın masrafını anlatır, her ücreti değil.

    Kılavuzdaki "kart ücreti yok" tablosunun koddaki karşılığı. Altın sette
    üç kayıt bu yüzden yanlış çıkıyordu.
    """

    def test_kart_aidati_masrafsizlik_sayilmaz(self) -> None:
        metin = "Sağlam Kart ile yıllık kart ücreti olmadan harcama yapın."
        assert "masrafsiz_mi" not in cikar(metin)

    def test_transfer_ucreti_masrafsizlik_sayilmaz(self) -> None:
        metin = "Kolay ve Hızlı para transferi FAST ile ücretsiz."
        assert "masrafsiz_mi" not in cikar(metin)

    def test_hisse_komisyonu_masrafli_sayilmaz(self) -> None:
        metin = "Hisse senedi alım-satım işlemlerinde standart komisyon uygulanır."
        assert "masrafsiz_mi" not in cikar(metin)

    def test_finansman_masrafi_hala_yakalanir(self) -> None:
        """Daraltma gerçek beyanı elememeli."""
        metin = "Konut finansmanında dosya masrafı alınmaz."
        assert cikar(metin)["masrafsiz_mi"] is True

    def test_kart_ve_dosya_masrafi_birlikte_gecerse_yakalanir(self) -> None:
        metin = "Kart aidatı ve dosya masrafı alınmaz."
        assert cikar(metin)["masrafsiz_mi"] is True
