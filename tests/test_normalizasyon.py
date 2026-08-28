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
        [
            "finansman masrafı alınmaz",
            "masrafsız ihtiyaç finansmanı",
            "Dosya masrafı yok!",
            "TAHSİS ÜCRETİ ALINMAZ",
        ],
    )
    def test_masrafsiz(self, girdi: str) -> None:
        assert masrafsiz_mi(girdi) is True

    @pytest.mark.parametrize(
        "girdi",
        ["masraf alınmaz", "masrafsız", "Masraf yok, kazanç var", "İşlemlerin Masrafsız!"],
    )
    def test_finansman_baglami_yoksa_none(self, girdi: str) -> None:
        """«Masrafsız» NEYİN masrafsız olduğunu söylemez.

        25 Ağustos ölçümü (altın set 98 kayıt): bu alan 16 yanlış pozitif
        üretti ve hepsi finansman dışı bir ücretsizlikti — SMS, Lounge, ATM'den
        para çekme, kart aidatı. Alan yalnız finansmanın tahsis/dosya masrafını
        taşır (`docs/ETIKETLEME_KILAVUZU.md`), dolayısıyla finansman bağlamı
        olmayan beyan bu alana YAZILMAZ. Bu testler önce `True` bekliyordu;
        ölçüm o sözleşmenin yanlış olduğunu gösterdi.
        """
        assert masrafsiz_mi(girdi) is None

    def test_masrafli(self) -> None:
        assert masrafsiz_mi("Dosya masrafı alınır.") is False

    @pytest.mark.parametrize(
        "girdi",
        [
            "Tahsis ücreti, finansman tutarının %0,5'i kadardır.",
            "Finansman tahsis ücreti %0,5 oranında tahsil edilecektir.",
        ],
    )
    def test_ucretin_varligi_beyan_edilmisse_false(self, girdi: str) -> None:
        """Ücretin VARLIĞINI bildiren yüklemler de bir beyandır.

        Sistem bu kalıpları tanımadığı için 9 kayıtta hiçbir şey üretmiyordu;
        etiketçiler aynı kayıtlara doğru şekilde «hayır» yazmıştı.
        """
        assert masrafsiz_mi(girdi) is False

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


# ---------------------------------------------------------------------------
# Kural katmanı — makullük aralığı (14 Ağustos)
# ---------------------------------------------------------------------------
#
# Ölçüm: `kar_payi_orani` dolu 27 kaydın 13'ü (%48) makul aralık dışındaydı ve
# hepsi kural katmanından geliyordu. Tipik kaynak, bir hesaplama aracının
# çıktısı:
#
#     Yıllık Maliyet Oranı
#     % 82,44
#     Ücretler Toplamı
#
# Bağlam kontrolü burada KURTARMIYOR: "oran" sözcüğü sayıya "maliyet"ten daha
# yakın olduğu için dışlayıcı sözcük tetiklenmiyor. Aylık kâr payının %82
# olamayacağını bilen tek şey alan bilgisidir.

from datetime import datetime  # noqa: E402

from src.extraction.kural import kurallarla_cikar  # noqa: E402
from src.schema import AYLIK_KAR_PAYI_UST_SINIRI  # noqa: E402

_HESAPLAMA_ARACI = (
    "Konut finansmanı seçenekleri sunuyoruz.\n%\nOranı kendim gireceğim.\n"
    "Aylık Taksit Tutarı\n9.169,06 TL\nGeri Ödenecek Toplam Tutar\n210.888,82 TL\n"
    "Yıllık Maliyet Oranı\n% 82,44\nÜcretler Toplamı\n28.076,27\n"
)


def _oran(metin: str):
    alanlar = kurallarla_cikar(metin, "https://ornek.test", datetime(2026, 8, 14))
    alan = alanlar.get("kar_payi_orani")
    return float(alan.deger) if alan and alan.var_mi else None


def test_yillik_maliyet_orani_kar_payi_sanilmaz():
    """Bu tek hata 13 kaydı birden bozuyordu."""
    assert _oran(_HESAPLAMA_ARACI) is None


def test_gercek_kar_payi_orani_hala_yakalanir():
    """Karşı kontrol: sınır doğru olanı elemiyor. Bir kısıtı sıkarken yalnız
    'reddediyor mu' diye bakmak yetmez (Sprint 0 raporu 5.3)."""
    assert _oran("Konut finansmanında aylık kâr payı oranı %1,89'dan başlıyor.") == 1.89


def test_yuzde_seksen_indirim_kar_payina_dusmez():
    assert _oran("Kampanya kapsamında %80 indirim uygulanır. Kâr payı oranı avantajlı.") is None


def test_sinir_degerleri():
    """Üst sınır dışlayıcıdır: %15 aylık oran değildir, %14,9 olabilir."""
    assert _oran(f"Aylık kâr payı oranı %{AYLIK_KAR_PAYI_UST_SINIRI:g} olarak uygulanır.") is None
    assert _oran("Aylık kâr payı oranı %14,9 olarak uygulanır.") == 14.9


def test_sifir_oran_gecerlidir():
    """'0%' GEÇERLİ bir aylık kâr payıdır — «vade farksız» kampanyanın ta kendisi.

    Bu test 16 Ağustos'ta TERSİNE ÇEVRİLDİ. Önceki hâli sıfırın üretilmemesini
    şart koşuyor ve gerekçesi şuydu: "müşterinin anaparayı birebir ödemesi
    demek olurdu". Katılım bankacılığında bu tam olarak gerçekleşen şeydir;
    vade farksız/0 kâr paylı kampanyalar yaygındır ve anapara birebir ödenir.

    Altın set kılavuzu bunu zaten söylüyordu (`tools/altin_set.py`:
    "SIFIR GEÇERLİDİR ve boş hücreden farklıdır") ve 60 örneğin 3'ü sıfır
    etiketli. Çıkarım katmanı ise `gecerli_aralik` alt sınırı (0,10) yüzünden
    sıfırı hiçbir koşulda üretemiyordu: etiketleyene "sıfır yaz" denen değer
    çıkarıcı için erişilemezdi. Alanın dolu hücrelerinin %30'u buydu.

    Eski testin ikincil kaygısı — "hesaplanırsa maliyet listesinin tepesine
    çıkar" — yerinde ama aşağı akışta zaten karşılanmış:
    `toplam_maliyet()` `i == 0` durumunda `anapara / vade_ay` kullanıyor,
    bölme hatası yok ve sonuç doğru. Sıfır oranlı kampanya listenin tepesine
    çıkmalıdır; gerçekten en ucuzudur.
    """
    assert _oran("Kâr payı oranı 0% olarak görünmektedir.") == 0.0


def test_vade_ustu_sinir():
    """360 ay üstü vade katılım finansmanında yok; '2026 ay' gibi bir çıkarım
    tarih kalıntısıdır."""
    alanlar = kurallarla_cikar(
        "Vade seçenekleri 2026 ay olarak listelenmiştir.",
        "https://ornek.test", datetime(2026, 8, 14),
    )
    alan = alanlar.get("vade_ay_max")
    assert alan is None or not alan.var_mi


class TestTutarBirimeBagli:
    """Sayı PARA BİRİMİNE bağlı olmalı — 27 Ağustos, jüri havuzu 9. madde.

    Eski kod «metinde TL geçiyor mu?» diye sorup metnin İLK sayısını alıyordu;
    ikisi arasında hiçbir bağ yoktu:

        «120 ay vadeli 1.000.000 TL konut finansmanı»  ->  120 TL

    Profil ekranı bunu «mevcut_musteri · 120 TL · 120 ay» diye çözüyor ve
    357 kampanyayı uygun buluyordu; sorulan 1.000.000 TL hiç görülmedi.
    """

    @pytest.mark.parametrize(
        ("metin", "beklenen"),
        [
            ("120 ay vadeli 1.000.000 TL konut finansmanı", 1_000_000.0),
            ("36 ay vade, 250.000 TL tutar", 250_000.0),
            ("12 taksitte 5.000 TL harcama", 5_000.0),
            # çarpan sözcüğü de sayıya BİTİŞİK olmalı
            ("1,5 milyon TL", 1_500_000.0),
            ("36 ay, bin TL'lik harcama", 1_000.0),
            # eski kod buradaki «bin»i 36'ya uygulayıp 36.000 üretiyordu
            ("36 ay vadeli 250.000 TL, bin TL hediye", 250_000.0),
        ],
    )
    def test_birime_bagli_sayi_secilir(self, metin: str, beklenen: float) -> None:
        assert para_ayristir(metin) == pytest.approx(beklenen)

    def test_birimsiz_sayi_tutar_sayilmaz(self) -> None:
        assert para_ayristir("120 ay vadeli konut finansmanı") is None

    def test_ciplak_birim_deger_uretmez(self) -> None:
        """«TL cinsinden» bir tutar beyan etmez."""
        assert para_ayristir("TL cinsinden ödeme") is None

    def test_birim_zorunlu_degilken_ilk_sayi_alinir(self) -> None:
        """Çıpa yoksa bağlanacak bir şey de yok — eski davranış korunur."""
        assert para_ayristir("50.000", birim_zorunlu=False) == 50_000.0


class TestBuyukHarfliCarpanSozcugu:
    """`para_ayristir` çarpan sözcüğünü `tr_kucult` ile çözmeli, `.lower()` ile DEĞİL.

    Bu dosyanın 22. satırındaki TUZAK 1 tam olarak burada ısırdı ve sessiz bir
    yanlış değil, bir ÇÖKME üretti:

        desen `re.IGNORECASE` ile "MİLYON"u yakalıyor
        "MİLYON".lower() -> 'mi̇lyon'  (i + U+0307 birleşik nokta)
        _CARPAN_SOZLERI['mi̇lyon']     -> KeyError

    Kural katmanı komple çöküyordu: `make kural-olc` altın sette hiç
    koşamıyordu ve korpusta bu yazımı taşıyan iki ham kayıt var.
    """

    @pytest.mark.parametrize(
        ("girdi", "beklenen"),
        [
            ("1,5 MİLYON TL", 1_500_000.0),
            ("1,5 milyon TL", 1_500_000.0),
            ("2 MİLYAR TL", 2_000_000_000.0),
            ("500 BİN TL", 500_000.0),
            ("500 bin TL", 500_000.0),
        ],
    )
    def test_carpan_buyuk_harfle_de_cozulur(self, girdi: str, beklenen: float) -> None:
        assert para_ayristir(girdi) == pytest.approx(beklenen)


class TestVasitaHali:
    """«6 taksitLE», «36 ayLA» — ek listesinde vasıta hâli yoktu.

    Boşluk `taksit_sayisi` diriltilince görünür oldu: aday deseni ifadeyi
    yakalıyor, `vade_ayristir` onu tanımıyor ve aday sessizce düşüyordu.
    Desen ile ayrıştırıcının aynı ek listesini (`TR_EKLER`) okuması bu yüzden
    bir tercih değil, bir zorunluluk.
    """

    @pytest.mark.parametrize(
        ("girdi", "beklenen"),
        [
            ("6 taksitle", 6),
            ("12 taksitle ödeme", 12),
            ("36 ayla", 36),
            ("3 yılla", 36),
            ("36 aylık", 36),  # eski ekler bozulmadı
            ("24 ayda", 24),
        ],
    )
    def test_vasita_hali_okunur(self, girdi: str, beklenen: int) -> None:
        assert vade_ayristir(girdi) == beklenen

    def test_kapali_ek_listesi_hala_kapali(self) -> None:
        """Ek eklemek «ayrıca» gibi sözcükleri serbest bırakmamalı."""
        assert vade_ayristir("50000 ayrıca geçerlidir") is None
