"""Karşılaştırma motoru — beş kriter ve kenar durumları (E-05).

Şartname 5.7 beş sıralama kriteri istiyor. Motor bunları uyguluyordu ama
**kendi test dosyası yoktu**: `toplam_maliyet` dolaylı olarak
`tests/test_muhakeme.py` üzerinden, birim tuzağı `tests/test_boyut_sozlesmesi.py`
üzerinden sınanıyordu; `sirala`, `avantaj_skorla` ve `uyarilar` ise hiç.

Buradaki testlerin işi iddiaları koda bağlamak:

    «beş kriterin her biri çalışıyor»          -> TestBesKriter
    «veri yok, en iyi sonuç gibi görünmez»     -> TestEksikVeriSonaGider
    «ağırlıklar kullanıcının, formül şeffaf»   -> TestAgirliklar
    «karşılaştırılamayanı karşılaştırmıyoruz»  -> TestUyarilar

Sunumdaki cümleler de bunlara dayanıyor; test kırılırsa slayt da yanlıştır.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.comparison.karsilastirma import (
    VADE_IZGARASI,
    Agirliklar,
    Kriter,
    Senaryo,
    avantaj_skorla,
    sirala,
    toplam_maliyet,
    vade_duyarliligi,
    vade_tavsiyesi,
    uyarilar,
)
from src.depolama import KampanyaKaydi
from src.schema import Birim


def _kayit(kimlik: str, **alanlar: object) -> KampanyaKaydi:
    varsayilan: dict[str, object] = {
        "kampanya_id": kimlik,
        "banka_kodu": "0299",
        "banka_adi": f"{kimlik} Katılım Bankası A.Ş.",
        "kaynak_url": f"https://ornek.test/{kimlik}",
        "cekim_tarihi": datetime(2026, 8, 26),
        "tam_kayit": {},
        "ham_metin": "",
        "ortalama_guven": 0.8,
        "doluluk_orani": 0.5,
        # Kâr payı sıralaması yalnız FİNANSMAN kampanyalarını kıyaslar
        # (`karsilastirma.OLCUT_KAPSAMI`); bu testler sıralama mekaniğini
        # ölçüyor, ürün sınıfını değil.
        "kampanya_turu": "ihtiyac_finansmani",
    }
    return KampanyaKaydi(**{**varsayilan, **alanlar})  # type: ignore[arg-type]


def _sira(kayitlar: list[KampanyaKaydi], kriter: Kriter, **kw) -> list[str]:
    return [k.kampanya_id for k in sirala(kayitlar, kriter, **kw)]


class TestBesKriter:
    """Şartname 5.7'nin beş kriteri — her biri ayrı ayrı."""

    def test_en_dusuk_kar_payi(self) -> None:
        kayitlar = [
            _kayit("ucuz", kar_payi_orani=1.87),
            _kayit("pahali", kar_payi_orani=2.45),
            _kayit("orta", kar_payi_orani=1.99),
        ]
        assert _sira(kayitlar, Kriter.EN_DUSUK_KAR_PAYI) == ["ucuz", "orta", "pahali"]

    def test_en_yuksek_odul(self) -> None:
        kayitlar = [
            _kayit("az", odul_miktari=500.0),
            _kayit("cok", odul_miktari=5000.0),
        ]
        assert _sira(kayitlar, Kriter.EN_YUKSEK_ODUL) == ["cok", "az"]

    def test_en_uzun_vade(self) -> None:
        kayitlar = [_kayit("kisa", vade_ay_max=12), _kayit("uzun", vade_ay_max=120)]
        assert _sira(kayitlar, Kriter.EN_UZUN_VADE) == ["uzun", "kisa"]

    def test_en_dusuk_masraf(self) -> None:
        kayitlar = [
            _kayit("masrafli", tahsis_ucreti=20000.0, tahsis_ucreti_birim=Birim.TL),
            _kayit("masrafsiz", tahsis_ucreti=0.0, tahsis_ucreti_birim=Birim.TL),
        ]
        assert _sira(kayitlar, Kriter.EN_DUSUK_MASRAF) == ["masrafsiz", "masrafli"]

    def test_en_avantajli_dordunun_bilesimi(self) -> None:
        """Beşinci kriter, dördünün ağırlıklı bileşimidir."""
        iyi = _kayit(
            "iyi",
            kar_payi_orani=1.80,
            tahsis_ucreti=0.0,
            tahsis_ucreti_birim=Birim.TL,
            vade_ay_max=120,
            odul_miktari=5000.0,
        )
        kotu = _kayit(
            "kotu",
            kar_payi_orani=2.90,
            tahsis_ucreti=25000.0,
            tahsis_ucreti_birim=Birim.TL,
            vade_ay_max=12,
            odul_miktari=100.0,
        )
        assert _sira([kotu, iyi], Kriter.EN_AVANTAJLI) == ["iyi", "kotu"]


class TestEksikVeriSonaGider:
    """«Veri yok» en iyi sonuç gibi görünmemeli — motorun temel dürüstlük kuralı."""

    @pytest.mark.parametrize(
        ("kriter", "alan", "deger"),
        [
            (Kriter.EN_DUSUK_KAR_PAYI, "kar_payi_orani", 1.87),
            (Kriter.EN_YUKSEK_ODUL, "odul_miktari", 5000.0),
            (Kriter.EN_UZUN_VADE, "vade_ay_max", 120),
        ],
    )
    def test_degeri_olmayan_kayit_sona_gider(self, kriter, alan, deger) -> None:
        kayitlar = [_kayit("bos"), _kayit("dolu", **{alan: deger})]
        assert _sira(kayitlar, kriter)[-1] == "bos"

    def test_sifir_kar_payi_eksik_sayilmaz(self) -> None:
        """«Vade farksız» bir beyandır: 0,0 boş değildir (ADR 012)."""
        kayitlar = [_kayit("sifir", kar_payi_orani=0.0), _kayit("bos"), _kayit("bir", kar_payi_orani=1.0)]
        assert _sira(kayitlar, Kriter.EN_DUSUK_KAR_PAYI) == ["sifir", "bir", "bos"]

    def test_bos_liste_ve_tek_kayit_kirilmaz(self) -> None:
        assert sirala([], Kriter.EN_AVANTAJLI) == []
        tek = [_kayit("tek", kar_payi_orani=1.5)]
        assert _sira(tek, Kriter.EN_AVANTAJLI) == ["tek"]


class TestAgirliklar:
    """«En avantajlı» bir tercih bileşimidir; tercihi kullanıcı verir."""

    def test_agirlik_degisince_siralama_degisir(self) -> None:
        oranci = _kayit(
            "oranci", kar_payi_orani=1.80, odul_miktari=100.0,
            tahsis_ucreti=0.0, tahsis_ucreti_birim=Birim.TL, vade_ay_max=36,
        )
        odulcu = _kayit(
            "odulcu", kar_payi_orani=2.60, odul_miktari=9000.0,
            tahsis_ucreti=0.0, tahsis_ucreti_birim=Birim.TL, vade_ay_max=36,
        )
        kayitlar = [oranci, odulcu]

        kar_agir = Agirliklar(kar_payi=0.90, masraf=0.04, vade=0.03, odul=0.03)
        odul_agir = Agirliklar(kar_payi=0.03, masraf=0.04, vade=0.03, odul=0.90)

        assert _sira(kayitlar, Kriter.EN_AVANTAJLI, agirliklar=kar_agir)[0] == "oranci"
        assert _sira(kayitlar, Kriter.EN_AVANTAJLI, agirliklar=odul_agir)[0] == "odulcu"

    def test_agirliklar_normalize_edilir(self) -> None:
        toplam = Agirliklar(kar_payi=4, masraf=2, vade=2, odul=2).normalize().toplam()
        assert toplam == pytest.approx(1.0)

    def test_skor_detayi_aciklanabilir(self) -> None:
        """Gizli skor yok: her skorun dökümü döner."""
        kayitlar = [
            _kayit("a", kar_payi_orani=1.8, vade_ay_max=60),
            _kayit("b", kar_payi_orani=2.4, vade_ay_max=24),
        ]
        detaylar = avantaj_skorla(kayitlar)
        assert len(detaylar) == 2
        assert all(hasattr(d, "kampanya_id") for d in detaylar)


class TestUyarilar:
    """Karşılaştırılamayanı karşılaştırmamak — finansal titizlik."""

    def test_farkli_vade_uyarisi_verilir(self) -> None:
        kayitlar = [_kayit("kisa", vade_ay_max=12), _kayit("uzun", vade_ay_max=120)]
        assert any("vade" in m.lower() for m in uyarilar(kayitlar))

    def test_tek_kayitta_uyari_yok(self) -> None:
        assert uyarilar([_kayit("tek", vade_ay_max=12)]) == []

    def test_karisik_birim_uyarisi(self) -> None:
        """%0,50 ile 500 TL aynı sütunda: sessizce sıralamak yanlış olurdu."""
        kayitlar = [
            _kayit("oranli", tahsis_ucreti=0.5, tahsis_ucreti_birim=Birim.YUZDE),
            _kayit("tutarli", tahsis_ucreti=500.0, tahsis_ucreti_birim=Birim.TL),
        ]
        assert uyarilar(kayitlar), "karışık birimde uyarı bekleniyordu"


class TestUyariBicimi:
    """Uyarı METNİNİN sözleşmesi — 26 Ağustos'ta ölçülen okunabilirlik kusuru.

    Dört uyarı 1.060 karakter ediyordu; 300 karakteri «Katılım Bankası A.Ş.»
    ifadesini dokuz kez tekrar etmekti, 206 karakteri on dokuz vade değerini
    tek tek dökmekti. Ekranı doldurup asıl cevabı aşağı itiyordu.
    """

    def test_uyari_metin_gibi_davranir(self) -> None:
        """`/compare` ucu ve `Cevap.uyarilar` `list[str]` bekliyor — sözleşme testi.

        `Uyari` bir `str` alt sınıfıdır; ayrı bir tip döndürmek API'yi, chatbot
        cevabını ve metin birleştirmeyi birden kırardı.
        """
        mesajlar = uyarilar([_kayit("a", vade_ay_max=12), _kayit("b", vade_ay_max=120)])
        assert mesajlar
        for mesaj in mesajlar:
            assert isinstance(mesaj, str)
            assert mesaj.strip(), "boş uyarı metni"

    def test_birim_karisimi_engelleyici_isaretlenir(self) -> None:
        """Kriteri SIRALAMADAN DÜŞÜREN uyarı, bağlam notundan ayrılmalı.

        Ayrım olmadan dört uyarı aynı görsel ağırlıkta çiziliyor ve kullanıcı
        hangisinin kararını değiştirdiğini seçemiyordu.
        """
        kayitlar = [
            _kayit("oranli", tahsis_ucreti=0.5, tahsis_ucreti_birim=Birim.YUZDE, vade_ay_max=12),
            _kayit("tutarli", tahsis_ucreti=500.0, tahsis_ucreti_birim=Birim.TL, vade_ay_max=120),
        ]
        mesajlar = uyarilar(kayitlar)

        engelleyiciler = [m for m in mesajlar if m.engelleyici]
        notlar = [m for m in mesajlar if not m.engelleyici]

        assert len(engelleyiciler) == 1, "birim karışımı tek engelleyici uyarı olmalı"
        assert "sıralamaya katılmadı" in engelleyiciler[0].baslik
        assert notlar, "vade farkı bağlam notu olarak kalmalı"

    def test_uzun_vade_listesi_araliga_iner(self) -> None:
        """On dokuz değeri tek tek yazmak kullanıcıya bir şey söylemiyor."""
        kayitlar = [_kayit(f"k{v}", vade_ay_max=v) for v in (2, 6, 12, 24, 36, 60, 120)]
        vade_uyarisi = next(m for m in uyarilar(kayitlar) if "Vade" in m.baslik)

        assert "2–120 ay arasında 7 farklı değer" in vade_uyarisi.detay
        assert "2, 6, 12" not in vade_uyarisi.detay, "uzun liste hâlâ dökülüyor"

    def test_kisa_vade_listesi_dokulur(self) -> None:
        """Az sayıda değerde asıl bilgi değerlerin KENDİSİ; aralığa indirmek kayıptır."""
        kayitlar = [_kayit("a", vade_ay_max=12), _kayit("b", vade_ay_max=36)]
        vade_uyarisi = next(m for m in uyarilar(kayitlar) if "Vade" in m.baslik)

        assert "12, 36 ay" in vade_uyarisi.detay

    def test_tum_bankalarda_eksikse_ad_sayilmaz(self) -> None:
        """Dokuz bankanın hepsi listedeyse «hiçbirinde» demek doğrudur.

        Eski metin dokuz tam unvanı sıralıyordu: 382 karakterin ~300'ü tekrar.
        """
        kayitlar = [
            _kayit("a", banka_adi="A Katılım Bankası A.Ş.", vade_ay_max=12),
            _kayit("b", banka_adi="B Katılım Bankası A.Ş.", vade_ay_max=36),
        ]
        oran_uyarisi = next(m for m in uyarilar(kayitlar) if "Kâr payı" in m.baslik)

        assert "Hiçbirinin finansman kampanyasında belirtilmemiş" in oran_uyarisi.detay
        assert "Katılım Bankası A.Ş." not in oran_uyarisi.detay

    def test_bir_iki_banka_eksikse_adlari_yazilir(self) -> None:
        """Az sayıda bankada eksikse HANGİSİ olduğu bilgi taşır."""
        kayitlar = [
            _kayit("a", banka_adi="A Bankası", kar_payi_orani=1.5, vade_ay_max=12),
            _kayit("b", banka_adi="B Bankası", vade_ay_max=36),
        ]
        oran_uyarisi = next(m for m in uyarilar(kayitlar) if "Kâr payı" in m.baslik)

        assert "B Bankası" in oran_uyarisi.detay
        assert "Hiçbir" not in oran_uyarisi.detay

    def test_uyari_toplam_uzunlugu_makul(self) -> None:
        """Ekranı kapatan metin duvarı geri gelmesin — üst sınır sözleşmesi."""
        kayitlar = [
            _kayit(f"k{i}", vade_ay_max=v, kampanya_turu=t, banka_adi=f"{ad} Bankası")
            for i, (v, t, ad) in enumerate(
                [(2, "konut_finansmani", "A"), (12, "tasit_finansmani", "B"),
                 (36, "ihtiyac_finansmani", "C"), (60, "kart", "D"),
                 (120, "yatirim_urunu", "E")]
            )
        ]
        toplam = sum(len(m) for m in uyarilar(kayitlar))
        assert toplam < 600, f"uyarı metni yine şişti: {toplam} karakter"


class TestOrtakTaban:
    """Farklı birimler ancak bir senaryoda kıyaslanabilir."""

    def test_senaryo_ile_yuzde_ve_tl_ayni_tabana_iner(self) -> None:
        # 100.000 TL'lik finansmanda %0,50 = 500 TL. Senaryosuz kıyas yanlıştır.
        kayitlar = [
            _kayit("oranli", tahsis_ucreti=0.5, tahsis_ucreti_birim=Birim.YUZDE),
            _kayit("tutarli", tahsis_ucreti=500.0, tahsis_ucreti_birim=Birim.TL),
        ]
        senaryo = Senaryo(anapara=100_000, vade_ay=36)
        sirali = sirala(kayitlar, Kriter.EN_DUSUK_MASRAF, senaryo=senaryo)
        assert {k.kampanya_id for k in sirali} == {"oranli", "tutarli"}


class TestMansetOranTuzagi:
    """Sunumdaki sayı burada sabitlenir — slayt ile motor ayrışamaz."""

    def test_dusuk_oran_masrafla_pahali_olabilir(self) -> None:
        ucuz_gorunen = toplam_maliyet(800_000, 1.87, 120, tahsis_ucreti=20_000)
        gercekten_ucuz = toplam_maliyet(800_000, 1.89, 120, tahsis_ucreti=0)
        assert ucuz_gorunen["toplam_geri_odeme"] > gercekten_ucuz["toplam_geri_odeme"]
        fark = ucuz_gorunen["toplam_geri_odeme"] - gercekten_ucuz["toplam_geri_odeme"]
        assert 3_000 < fark < 6_000, f"slayttaki ~4.204 TL farkı değişti: {fark:.0f}"


class TestVadeDuyarliligi:
    """Karar desteği: «aynı kampanyada vadeyi kısaltsam ne kazanırım?»

    Mentör geri bildirimi (26 Ağu): tekil teklif yerine vade/tutar karşılaştırması
    sunmak jüriye daha çok şey anlatır. Hesap `toplam_maliyet` üstünde koşan bir
    ızgaradır — yeni matematik yok, dolayısıyla burada sınanan şey aritmetik
    değil **sözleşme**: neyin döndüğü, neyin elenmediği, neyin iddia edilmediği.
    """

    def test_kisa_vade_toplamda_her_zaman_daha_ucuz(self) -> None:
        secenekler = vade_duyarliligi(800_000, 2.05, referans_vade=120)
        uygunlar = [s for s in secenekler if s.uygun_mu]
        toplamlar = [s.toplam_geri_odeme for s in uygunlar]
        assert toplamlar == sorted(toplamlar), "vade uzadıkça toplam maliyet artmalı"

    def test_taksit_vade_uzadikca_duser(self) -> None:
        secenekler = vade_duyarliligi(800_000, 2.05, referans_vade=120)
        taksitler = [s.aylik_taksit for s in secenekler if s.uygun_mu]
        assert taksitler == sorted(taksitler, reverse=True)

    def test_referans_vade_farki_sifir(self) -> None:
        secenekler = vade_duyarliligi(800_000, 2.05, referans_vade=120)
        referans = next(s for s in secenekler if s.vade_ay == 120)
        assert referans.toplam_farki == 0.0
        assert referans.taksit_farki == 0.0
        assert referans.referans_mi

    def test_izgarada_olmayan_referans_vade_tabloya_eklenir(self) -> None:
        """Kullanıcının girdiği vade tabloda görünmezse kıyas dayanaksız kalır."""
        assert 96 not in VADE_IZGARASI
        secenekler = vade_duyarliligi(500_000, 1.9, referans_vade=96)
        assert 96 in [s.vade_ay for s in secenekler]

    def test_azami_vade_asan_adim_ELENMEZ_sebebiyle_doner(self) -> None:
        """Sessizce elemek «neden 180 ay yok?» sorusunu cevapsız bırakır."""
        secenekler = vade_duyarliligi(
            800_000, 2.05, referans_vade=120, vade_ay_max=120
        )
        asan = next(s for s in secenekler if s.vade_ay == 180)
        assert not asan.uygun_mu
        assert asan.engel is not None and "120" in asan.engel
        assert asan.toplam_geri_odeme is None, "uygun olmayan vade için sayı üretilmez"

    def test_tahsis_ucreti_toplama_giriyor(self) -> None:
        ucretsiz = vade_duyarliligi(500_000, 2.0, referans_vade=60)
        ucretli = vade_duyarliligi(500_000, 2.0, referans_vade=60, tahsis_ucreti=10_000)
        a = next(s for s in ucretsiz if s.vade_ay == 60).toplam_geri_odeme
        b = next(s for s in ucretli if s.vade_ay == 60).toplam_geri_odeme
        assert b == pytest.approx(a + 10_000)

    def test_sifir_kar_payi_patlamaz(self) -> None:
        """ADR 012 — sıfır kâr payı beyanı geçerli bir değerdir, hata değil."""
        secenekler = vade_duyarliligi(300_000, 0.0, referans_vade=36)
        uygunlar = [s for s in secenekler if s.uygun_mu]
        assert all(s.toplam_kar_payi == pytest.approx(0.0) for s in uygunlar)

    def test_referans_vade_pozitif_olmali(self) -> None:
        with pytest.raises(ValueError):
            vade_duyarliligi(100_000, 2.0, referans_vade=0)


class TestVadeTavsiyesi:
    """En kritik dürüstlük kuralı: kapasite bilinmeden «en iyi vade» iddia edilmez."""

    def test_tavansiz_tavsiye_kazanan_secmez(self) -> None:
        """Tavan yoksa en kısa vade değil, BİR ADIM kısa vade söylenir.

        Toplam maliyet vade kısaldıkça tekdüze azaldığı için «en avantajlı vade»
        her zaman ızgaranın en kısa adımıdır — 800.000 TL için aylık 75.880 TL
        taksit demek. Doğru ama tavsiye değil; o yüzden karar tabloya bırakılır.
        """
        secenekler = vade_duyarliligi(800_000, 2.05, referans_vade=120, vade_ay_max=120)
        cumle = vade_tavsiyesi(secenekler, 120)
        assert cumle is not None
        assert "84 ay" in cumle
        assert "12 ay" not in cumle

    def test_taksit_tavani_verilince_en_kisa_uygun_vade_onerilir(self) -> None:
        """Mentörün örneği: 800 bin TL / 120 ay yerine 60 ay ne kazandırır?"""
        secenekler = vade_duyarliligi(
            800_000, 2.05, referans_vade=120, tahsis_ucreti=5_000, vade_ay_max=120
        )
        cumle = vade_tavsiyesi(secenekler, 120, azami_taksit=25_000)
        assert cumle is not None and "60 ay" in cumle

    def test_tavana_hicbir_kisa_vade_sigmazsa_durust_cevap(self) -> None:
        secenekler = vade_duyarliligi(800_000, 2.05, referans_vade=120, vade_ay_max=120)
        cumle = vade_tavsiyesi(secenekler, 120, azami_taksit=15_000)
        assert cumle is not None
        assert "sığmıyor" in cumle

    def test_en_kisa_vadede_tavsiye_yok(self) -> None:
        """Referans zaten ızgaranın en kısası ise kıyaslanacak bir şey yoktur."""
        secenekler = vade_duyarliligi(200_000, 2.0, referans_vade=12)
        assert vade_tavsiyesi(secenekler, 12) is None

    def test_referans_banka_limitini_asiyorsa_tavsiye_yok(self) -> None:
        secenekler = vade_duyarliligi(800_000, 2.05, referans_vade=120, vade_ay_max=60)
        assert vade_tavsiyesi(secenekler, 120) is None


class TestOlcutKapsami:
    """Ürün sınıfı ortak tabanın ikinci yarısı (ADR 020).

    27 Ağustos'ta 931 kayıtta ölçüldü: `kar_payi_orani` dolu 119 kaydın 110'u
    kart / alışveriş / «diğer» kampanyalarından geliyor ve neredeyse hepsi
    sıfır. Bir kart taksit promosyonunun sıfırı ile bir ihtiyaç finansmanının
    aylık %2,87'si aynı min-maks ölçeğine sokulunca her karşılaştırma aynı
    cümleyle bitiyordu: «Kâr payı oranı açısından iki banka EŞİT: aylık %0».
    """

    def test_kart_kampanyasinin_sifiri_orani_kiyaslamaz(self) -> None:
        kayitlar = [
            _kayit("kart", kar_payi_orani=0.0, kampanya_turu="kart"),
            _kayit("finansman", kar_payi_orani=2.87, kampanya_turu="ihtiyac_finansmani"),
        ]
        # Kart kaydı «en ucuz» diye başa geçmez; değeri yokmuş gibi sona gider.
        assert _sira(kayitlar, Kriter.EN_DUSUK_KAR_PAYI) == ["finansman", "kart"]

    def test_finansman_kampanyasinin_sifiri_gecerlidir(self) -> None:
        """ADR 012 korunuyor: «vade farksız» finansmanda 0,0 gerçek bir beyandır.

        Kapı ürün sınıfına bakar, değerin kendisine değil. Togg %0 ve Albaraka
        «vade farksız destek» kampanyaları gerçek sıfır kâr paylı FİNANSMAN
        teklifleridir ve sıralamayı kazanmaları doğrudur.
        """
        kayitlar = [
            _kayit("sifirli", kar_payi_orani=0.0, kampanya_turu="tasit_finansmani"),
            _kayit("oranli", kar_payi_orani=2.87, kampanya_turu="ihtiyac_finansmani"),
        ]
        assert _sira(kayitlar, Kriter.EN_DUSUK_KAR_PAYI) == ["sifirli", "oranli"]

    def test_yatirim_urunu_kar_payi_kiyaslamaz(self) -> None:
        """Katılma hesabı GETİRİSİ finansman maliyeti değildir.

        Türkiye Finans Günlük Hesap sayfasından gelen %11 bir yıllık getiri
        hücresiydi; «en yüksek kâr payı» sıralamasında o çıkıyordu.
        """
        kayitlar = [
            _kayit("mevduat", kar_payi_orani=11.0, kampanya_turu="yatirim_urunu"),
            _kayit("finansman", kar_payi_orani=4.82, kampanya_turu="ihtiyac_finansmani"),
        ]
        assert _sira(kayitlar, Kriter.EN_DUSUK_KAR_PAYI) == ["finansman", "mevduat"]

    def test_turu_belirsiz_kayit_kapsam_disidir(self) -> None:
        """«diğer» sınıflandırılamadı demektir; finansman saymak varsayım olurdu."""
        kayitlar = [
            _kayit("belirsiz", kar_payi_orani=0.0, kampanya_turu="diger"),
            _kayit("finansman", kar_payi_orani=3.5, kampanya_turu="konut_finansmani"),
        ]
        assert _sira(kayitlar, Kriter.EN_DUSUK_KAR_PAYI) == ["finansman", "belirsiz"]

    @pytest.mark.parametrize(
        ("kriter", "alan", "deger"),
        [
            (Kriter.EN_UZUN_VADE, "vade_ay_max", 120),
            (Kriter.EN_YUKSEK_ODUL, "odul_miktari", 5000.0),
        ],
    )
    def test_kapisiz_olcutler_her_turde_siralanir(self, kriter, alan, deger) -> None:
        """Vade ve ödül ürün sınıfından bağımsız okunur — kapı yalnız kâr payında."""
        kayitlar = [
            _kayit("kart", kampanya_turu="kart", **{alan: deger}),
            _kayit("finansman", kampanya_turu="ihtiyac_finansmani", **{alan: deger / 2}),
        ]
        assert _sira(kayitlar, kriter)[0] == "kart"

    def test_kapsam_disi_kayit_silinmez(self) -> None:
        """Sıralamadan düşmek listeden düşmek değildir — kanıt yerinde durur."""
        kayitlar = [
            _kayit("kart", kar_payi_orani=0.0, kampanya_turu="kart"),
            _kayit("finansman", kar_payi_orani=2.87, kampanya_turu="ihtiyac_finansmani"),
        ]
        assert len(sirala(kayitlar, Kriter.EN_DUSUK_KAR_PAYI)) == 2

    def test_kapsam_disi_kalinca_uyari_cikar(self) -> None:
        """Sessiz daraltma yok: kullanıcı neden kıyaslanmadığını görmeli."""
        kayitlar = [
            _kayit("a", banka_adi="A Bankası", kar_payi_orani=0.0, kampanya_turu="kart"),
            _kayit("b", banka_adi="B Bankası", kar_payi_orani=0.0, kampanya_turu="alisveris_puani"),
        ]
        oran_uyarisi = next(m for m in uyarilar(kayitlar) if "Kâr payı" in m.baslik)
        assert "finansman kampanyasında belirtilmemiş" in oran_uyarisi.detay
        assert "vade farksız" in oran_uyarisi.detay
