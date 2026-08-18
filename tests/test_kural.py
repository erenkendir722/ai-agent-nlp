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

from src.extraction.kural import GUVEN_BANDI, Aday, _sec, kurallarla_cikar

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
        """Üst sınır bilinçli olarak YOK — yüz milyonlu limitler gerçektir.

        Bu testin ÖNCEKİ metni şuydu:

            "Hesapta 1.000 TL alt limit ve 150.000.000 TL üst limit
             bulunmaktadır. Finansman limiti."

        16 Ağustos'ta altın set o cümlenin geldiği kaydı `null` etiketledi ve
        haklıydı: metin Ziraat Katılım'ın GÜNLÜK HESAP sayfasından geliyor,
        150.000.000 TL kâr payı işletilecek bakiyenin üst sınırı. Test,
        `EN_AZ_FINANSMAN_TUTARI` docstring'indeki "kurumsal finansmanda yüz
        milyonlu limitler gerçektir" iddiasını doğru bir örnekle değil, bir
        mevduat bandıyla sınıyordu.

        İddia hâlâ geçerli — o yüzden test duruyor, yalnız örneği gerçek bir
        kurumsal finansman cümlesiyle değişti. Bandın kendisi artık
        `test_hesap_bandi_finansman_limiti_sayilmaz` ile REDDEDİLİYOR.
        """
        assert cikar(
            "Kurumsal müşterilerimize 150.000.000 TL'ye varan proje finansmanı sağlanmaktadır."
        ).get("finansman_tutari_max") == pytest.approx(150_000_000.0)

    @pytest.mark.parametrize(
        "metin",
        [
            # Mevduat bandı — sayı bir aralığın UCU, finansman limiti değil.
            "Hesapta 1.000 TL alt limit ve 150.000.000 TL üst limit bulunmaktadır. Finansman limiti.",
            # Dilim tablosu: tutar vadeyi belirliyor, finansmanı değil.
            "Fatura bedeli 1.200.001 TL – 2.000.000 TL aralığında olan taşıt "
            "finansmanlarında en fazla 12 ay vade uygulanır.",
            # Kredi-değer tablosu: finansman bir YÜZDE, mutlak sayı konut değeri.
            "Azami kredi tutarı: Değer <= 5.000.000 TL | Değer x 22,5% finansman.",
            # Hesaplama aracının çıktısı.
            "Aylık Taksit Tutarı 11.349,76 TL Geri Ödenecek Toplam Tutar "
            "261.044,84 TL finansman tutarı",
            # Örnek ödeme tablosunun tabanı.
            "100.000 TL. baz alınarak oluşturulan Arsa Finansmanı örnek ödeme tablosu.",
        ],
    )
    def test_hesap_bandi_finansman_limiti_sayilmaz(self, metin: str) -> None:
        """16 Ağustos ölçümünün kapattığı 11 yanlış pozitifin biçimleri.

        Hepsinde "finansman" ya da "limit" sözcüğü sayının YANINDA; bağlam
        kontrolü hiçbirini elemiyor. Büyüklük sınırı da elemiyor — 2 milyon TL
        makul bir taşıt finansmanıdır. Ayıran şey sayının YAZILIŞ BİÇİMİ:
        aralığın ucu, tablo hücresi ya da hesap makinesi çıktısı.
        """
        assert "finansman_tutari_max" not in cikar(metin)


class TestKampanyaBitisAraligi:
    """Bitiş tarihi çoğu zaman çıplak bir ARALIK olarak yazılıyor.

    16 Ağustos ölçümü: duyarlılık 0,571 → 0,929 (kaçırılan 6 → 1).
    """

    def test_baglam_sozcugu_olmadan_aralik_sonu_kabul_edilir(self) -> None:
        """Kaçırmaların çoğu buydu: menü metninin ardına düşmüş çıplak aralık.

        Yakınında "son", "bitiş", "geçerli" gibi hiçbir sözcük yok; kanıt
        yapısal — iki tarih tire ile bağlanmış.
        """
        assert str(
            cikar(
                "SİZE ÖZEL ÇÖZÜMLER ÜRÜN VE HİZMETLERİMİZ "
                "13 Mart 2026 - 31 Aralık 2026 Vakıf Katılım müşterileri..."
            ).get("kampanya_bitis")
        ) == "2026-12-31"

    def test_aralik_basi_bitis_sayilmaz(self) -> None:
        """Yalnız SONA bakılır; başlangıç tarihi bitiş değildir."""
        alanlar = cikar("Kampanya Dönemi: 2 Temmuz 2026 - 31 Aralık 2026")
        assert str(alanlar.get("kampanya_bitis")) == "2026-12-31"

    def test_kampanya_donemi_sozcugu_taninir(self) -> None:
        assert str(
            cikar("📢 Kampanya Dönemi: 16 Haziran - 31 Ağustos 2026 Koşullar...")
            .get("kampanya_bitis")
        ) == "2026-08-31"

    def test_tek_basina_tarih_hala_baglam_ister(self) -> None:
        """Yapısal istisna, bağlam kuralını TÜMDEN kaldırmamalı.

        Aralık yoksa ve sözcük yoksa tarih kabul edilmez — aksi hâlde
        sayfadaki telif yılı ya da mevzuat tarihi bitiş sanılırdı.
        """
        assert "kampanya_bitis" not in cikar(
            "Bu düzenleme 14 Aralık 2021 tarihli yönetmeliğe dayanmaktadır."
        )


class TestKarPayiSifirVeYabanciOranlar:
    """Yüzde her yerde geçer; hangisi KÂR PAYI?

    16 Ağustos ölçümü: F1 0,545 → 0,842 (YP 6 → 1).
    """

    def test_sifir_kar_payi_cikarilir(self) -> None:
        """«Vade farksız» kampanyada oran gerçekten sıfırdır.

        `gecerli_aralik` alt sınırı (0,10) sıfırı eliyordu; altın setin dolu
        hücrelerinin %30'u sıfır etiketli olduğu için alan yapısal olarak
        erişilemezdi.
        """
        assert cikar(
            "Vade farksız kampanyamızda aylık kâr payı oranı 0% olarak uygulanır."
        ).get("kar_payi_orani") == pytest.approx(0.0)

    def test_sifir_disindaki_kucuk_oran_hala_elenir(self) -> None:
        """Muafiyet YALNIZ tam sıfıra; alt sınırın asıl işi duruyor.

        "Giden Fon Transferi | USD | 25 | % 0.05" bir havale komisyonudur.
        """
        assert "kar_payi_orani" not in cikar(
            "Giden Fon Transferi komisyon oranı % 0,05 olarak uygulanır."
        )

    def test_guven_bandi_tablo_hucresini_kapsar(self) -> None:
        """Tablo hücresi güven çarpanı yediği için bandın dışında kalıyordu.

        Güvenler Albaraka kaydından ÖLÇÜLMÜŞ gerçek değerlerdir: aynı kâr
        oranı tablosunun iki hücresi farklı yoldan puanlanıyor —
        0% tablo yolundan (0,93 × 0,78), 3,95% mesafe yolundan.
        0,05'lik bantta 0% eleniyor ve `en_dusuk` 3,95'i seçiyordu.

        Doğrudan `_sec` üzerinde sınanıyor: uçtan uca metinle sınamak
        tablo kolon hizasına bağımlı olurdu ve bandı değil ayrıştırmayı
        ölçerdi.
        """
        tablo_hucresi = Aday(0.0, "0%", 3407, 3409, 0.7254)
        duz_metin = Aday(3.95, "3,95%", 3466, 3471, 0.8516)

        assert _sec([tablo_hucresi, duz_metin], "en_dusuk").deger == 0.0
        assert duz_metin.guven - tablo_hucresi.guven < GUVEN_BANDI

    @pytest.mark.parametrize(
        "metin",
        [
            # Vergi oranı — "oranlarda" bağlam sözcüğü sayının yanında.
            "Hesaba yatan hasılattan belirtilen oranlarda (%4 ve %2) gelir "
            "vergisi kesilmesini sağlayan cari hesap türüdür.",
            # Mülkiyet payı, oran değil.
            "Finansman kullanan kişinin üzerinde %1 oranında dahi konut "
            "hissesi bulunuyorsa banka tarafından BSMV uygulanabilir.",
            # Mevduat getirisi, finansman kâr payı değil.
            "Günlük hesap oranına ek +%2'ye varan getiri oranından yararlanın.",
            # Tazminat oranı.
            "Erken ödeme tazminatı oranı, kalan vadesi 36 ayı aşmayan "
            "finansmanlarda erken ödenen tutarın %1'i kadardır.",
        ],
    )
    def test_kar_payi_olmayan_yuzdeler_elenir(self, metin: str) -> None:
        assert "kar_payi_orani" not in cikar(metin)


class TestOdulMiktariSecimi:
    """Ödül KİŞİ BAŞINA düşen tutardır — toplam havuz ya da eşik değil.

    16 Ağustos ölçümü: `odul_miktari` 5 yanlış pozitif üretiyordu, F1 0,400.
    """

    def test_toplam_odul_kisi_basi_odul_yerine_gecmez(self) -> None:
        """`en_yuksek` seçimi toplamı alıp kişi başı ödülü eziyordu.

        BİLİNEN AÇIK — doğru cevap 2.000 TL, sistem "Belirtilmemiş" diyor.
        Veto aynı cümledeki doğru adayı da eliyor. Yanlış bir 10.000'den
        iyidir (uydurulmuş ödül vaadi yok) ama tam değildir.

        "kisi basi"yi bağlam sözcüğü yapmak denendi ve ÖLÇÜLDÜ: alan F1'ini
        0,667'den 0,333'e düşürdü, başka yerlerde yeni yanlış pozitif açtı.
        Doğrusu seçim katmanında çözmek — S-14'e bırakıldı.
        """
        odul = cikar(
            "Davet eden kişi, kişi başı maksimum 2.000 TL, toplamda 5 kişi "
            "için maksimum 10.000 TL nakit ödül kazanabilir."
        ).get("odul_miktari")
        assert odul != pytest.approx(10_000.0)

    def test_toplamda_gecen_gercek_odul_elenmez(self) -> None:
        """17 Ağu (S-14) — vetonun yan hasarı kapatıldı.

        Veto "toplamda" sözcüğüne bakıyordu ve şu cümlede 300 TL'yi eliyordu:
        *"kazanılabilecek maksimum nakit ödül tutarı TOPLAMDA 300 TL'dir"*.
        Burada 300 TL gerçek ödül tutarıdır — kişi sayısına bölünmüş bir
        havuz değil. Toplamı işaret eden asıl imleç `kisi icin`.

        Ölçüm (yalnız kural, altın set): F1 0,400 → 0,667, yeni yanlış
        pozitif yok. Vetoyu tamamen kaldırmak (F1 0,571) reddedildi: o,
        sessizliği yanlış bir 10.000 ile takas ediyordu.
        """
        odul = cikar(
            "Her iki karttan yapılacak dijital üyelik ödemeleri kapsamınca "
            "kazanılabilecek maksimum nakit ödül tutarı toplamda 300 TL’dir."
        ).get("odul_miktari")
        assert odul == pytest.approx(300.0)

    @pytest.mark.parametrize(
        "metin",
        [
            # Mevduat ürünü eşiği — ödül değil.
            "Zümrüt Katılma Hesabı 3 milyon TL ve üzerinde birikimi olan "
            "müşterilerimiz için sunulmuştur. Kazanç sağlar.",
            # ATM çekim limiti — "kadar olan" aralık ucu.
            "Tek seferde 500 TL'ye kadar olan tüm para çekme işlemlerini "
            "komisyon ödemeden yapın, nakit ödül kazanın.",
            # Harcama örneği: ödül 10 TL, 1.000 TL harcamanın kendisi değil.
            "Örneğin 1.000 TL banka kartı harcamanızda 10 TL nakit ödül kazanırsınız.",
        ],
    )
    def test_odul_olmayan_tutarlar_elenir(self, metin: str) -> None:
        assert cikar(metin).get("odul_miktari") != pytest.approx(3_000_000.0)
        assert cikar(metin).get("odul_miktari") not in (500.0, 1000.0)


class TestMasrafsizlikKapsami:
    """`masrafsiz_mi` FİNANSMANIN masrafını anlatır, her ücreti değil.

    16 Ağustos ölçümü: 7 yanlış pozitif, F1 0,250 → düzeltmeden sonra 0,714.
    """

    def test_kapsam_beyani_masrafsizlik_degildir(self) -> None:
        """«ücretini içermemektedir» = ücret VAR, toplama dahil değil."""
        assert cikar(
            "Ödenecek toplam tutar finansman tahsis ücretini içermemektedir."
        ).get("masrafsiz_mi") is False

    def test_tuketici_mevzuati_kalibi_masrafsizlik_degildir(self) -> None:
        """Banka sayfalarının altbilgisinde standart; tek başına 3 hata verdi."""
        assert "masrafsiz_mi" not in cikar(
            "Talebiniz en kısa sürede ve en geç otuz (30) gün içinde "
            "ücretsiz olarak sonuçlandırılmaktadır."
        )

    def test_temel_bankacilik_masrafsizligi_finansmani_baglamaz(self) -> None:
        assert "masrafsiz_mi" not in cikar(
            "Türkiye Finans'ın temel bankacılık işlemlerinden de ücretsiz yararlanın."
        )

    def test_gercek_masrafsizlik_beyani_korunur(self) -> None:
        """Daraltma doğru cevapları elememeli — asıl risk bu."""
        assert cikar(
            "50.000 TL'ye kadar dosya masrafı alınmamaktadır."
        ).get("masrafsiz_mi") is True


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


# ---------------------------------------------------------------------------
# Kampanya türü düzeltmeleri (18 Ağu — altın setin yakaladığı iki hata biçimi)
# ---------------------------------------------------------------------------


def test_genel_finansman_url_alt_turuyle_ozellestirilir() -> None:
    """LLM «finansman» dediğinde URL alt türü söylüyorsa o kullanılır.

    Altın sette 6 vaka: .../konut-finansmani.aspx için LLM genel «finansman»
    diyordu, altın set «konut_finansmani». Ürün türü URL'de birebir yazıyor.
    """
    from src.extraction.kural import kampanya_turunu_duzelt

    for url, beklenen in [
        ("https://x.com/tr/konut-finansmani.aspx", "konut_finansmani"),
        ("https://x.com/tr/tasit-finansmani", "tasit_finansmani"),
        ("https://x.com/tr/arac-finansmani", "tasit_finansmani"),
        ("https://x.com/tr/ihtiyac-finansmani", "ihtiyac_finansmani"),
    ]:
        tur, sebep = kampanya_turunu_duzelt("finansman", url, "kampanya metni")
        assert tur == beklenen, url
        assert sebep is not None


def test_url_isareti_yoksa_genel_finansman_korunur() -> None:
    """Zorlama özelleştirme yapılmaz — sinyal yoksa cevap değişmez."""
    from src.extraction.kural import kampanya_turunu_duzelt

    tur, sebep = kampanya_turunu_duzelt("finansman", "https://x.com/kampanyalar", "metin")
    assert tur == "finansman"
    assert sebep is None


def test_kanitsiz_alisveris_puani_dusurulur() -> None:
    """Metinde puan/mil/chip yoksa «alisveris_puani» etiketi verilmez.

    Altın sette 9 vaka: sistem indirim ve kart kampanyalarına «alışveriş
    puanı» diyordu; dokuzunun metninde «puan» kelimesi bile geçmiyordu.
    """
    from src.extraction.kural import kampanya_turunu_duzelt

    tur, sebep = kampanya_turunu_duzelt(
        "alisveris_puani", "https://x.com/arzumda-15-indirim", "%15 indirim fırsatı"
    )
    assert tur == "diger"
    assert sebep is not None


def test_puan_kaniti_varsa_alisveris_puani_korunur() -> None:
    from src.extraction.kural import kampanya_turunu_duzelt

    tur, sebep = kampanya_turunu_duzelt(
        "alisveris_puani", "https://x.com/kampanya", "Alışverişlerinizde 1.000 puan kazanın"
    )
    assert tur == "alisveris_puani"
    assert sebep is None


def test_kanitsiz_alisveris_puani_url_kart_diyorsa_karta_iner() -> None:
    from src.extraction.kural import kampanya_turunu_duzelt

    tur, _ = kampanya_turunu_duzelt(
        "alisveris_puani", "https://x.com/biz-kart-dijital-uyelikler", "üyelik kampanyası"
    )
    assert tur == "kart"


# ---------------------------------------------------------------------------
# Dilim tablosu ayrıştırıcı (18 Ağu — finansman_tutari_max F1 0,400 -> 0,714)
# ---------------------------------------------------------------------------


def test_tasit_dilim_tablosundan_deger_carpi_oran() -> None:
    """Kılavuzun insana söylediği hesabın kodda karşılığı.

    `docs/ETIKETLEME_KILAVUZU.md`: «Kademeli tabloda her satır için değer ×
    oran hesapla, en büyüğünü yaz.» max(400k×.70, 800k×.50, 1.2M×.30) = 400k.
    """
    from src.extraction.kural import dilim_tablosundan_azami_finansman

    metin = """Aracın Nihai Fatura Tutarı /Kasko Değeri | Taşıt Değerine Oranı | Vade
0-400.000 TL | %70 | 48
400.001 - 800.000 TL | %50 | 36
800.001 - 1.200.000 TL | %30 | 24"""
    tutar, sebep = dilim_tablosundan_azami_finansman(metin)
    assert tutar == 400_000.0, sebep


def test_ayni_tablo_hucreleri_ayrik_bicimde_de_okunur() -> None:
    """`|` ile bölünce tutar ve oran ayrı hücreye düşen biçim.

    18 Ağu'da bu biçim kaçırılmıştı: `|` ile bölmek oran sütununu yok edip
    tabloyu «oransız» gösteriyordu.
    """
    from src.extraction.kural import dilim_tablosundan_azami_finansman

    metin = "kasko değeri\n| 0 TL – 400.000 TL 70% 48 | 400.001 TL – 800.000 TL 50% 36 |"
    tutar, _ = dilim_tablosundan_azami_finansman(metin)
    assert tutar == 400_000.0


def test_ust_dilim_sinirsizsa_azami_uretilmez() -> None:
    """«250.000 ve üzeri» varsa azami tutar BİLİNMEZ — uydurmak yerine boş."""
    from src.extraction.kural import dilim_tablosundan_azami_finansman

    metin = """kasko değerine oranı
125.000 TL'ye kadar olan finansmanlarda 36 ay
125.000 - 250.000 TL arası 24 ay
250.000 TL ve üzeri 12 ay"""
    tutar, sebep = dilim_tablosundan_azami_finansman(metin)
    assert tutar is None
    assert "sınırsız" in sebep


def test_mevduat_oran_tablosu_finansman_sanilmaz() -> None:
    """EN ÖNEMLİ KORUMA — mevduat tablosu finansman tablosuyla aynı yapıda.

    18 Ağu'da bağlam kapısı yokken ayrıştırıcı günlük hesap kâr payı
    tablosundan 55.500.000 TL «finansman» üretti. Yapı ayırt etmiyor;
    ayıran şey başlıktaki «taşıt değerine oranı» / «kasko» ifadesi.
    """
    from src.extraction.kural import dilim_tablosundan_azami_finansman

    metin = """Günlük Katılma Hesabı kâr payı oranları
0 - 50.000 TL | %30 | 32
50.001 - 500.000 TL | %35 | 32
500.001 TL ve üzeri | %37 | 32"""
    tutar, sebep = dilim_tablosundan_azami_finansman(metin)
    assert tutar is None, f"mevduat tablosundan finansman üretildi: {tutar}"
    assert "işaret" in sebep


def test_makul_olmayan_kucuk_sonuc_elenir() -> None:
    """1.000 × %1 = 10 TL — hesap doğru ama girdi tablo değil."""
    from src.extraction.kural import dilim_tablosundan_azami_finansman

    metin = "kasko\n1.000 TL %1 12\n2.000 TL %1 6"
    tutar, sebep = dilim_tablosundan_azami_finansman(metin)
    assert tutar is None
    assert "makul" in sebep
