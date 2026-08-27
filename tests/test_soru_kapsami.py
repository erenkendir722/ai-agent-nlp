"""Soru kapsamı ve terim eşleştirmesi — AĞ İSTEMEZ.

27 Ağustos'ta 182 soruluk uçtan uca tarama üç kusur çıkardı; üçü de aynı
kökten geliyordu: **bir terimin soruda geçip geçmediği alt dize aramasıyla
karara bağlanıyordu.**

    soru  : «Python'da liste nasıl ters çevrilir?»
    cevap : üç kampanya kaynağıyla konut kampanyası dökümü
    sebep : `_URUN_ANAHTARLARI`'ndaki «ev» sözcüğü «ters çEVrilir» içinde

Kapsam dışı olması gereken soru kapsam içi sayılıyordu — hem de kaynak
göstererek, yani doğrulanmış görünerek.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.depolama import KampanyaKaydi
from src.rag.chatbot import (
    _ALAN_SOZCUKLERI,
    _URUN_ANAHTARLARI,
    Niyet,
    _urun_filtrele,
    alan_disi_soru,
    sor,
    terim_gecer,
)
from src.schema import SEGMENT_ORNEKLERI, KampanyaTuru


def _kayit(kimlik: str, **alanlar: object) -> KampanyaKaydi:
    varsayilan: dict[str, object] = {
        "kampanya_id": kimlik,
        "banka_kodu": "0299",
        "banka_adi": "Test Katılım Bankası A.Ş.",
        "kaynak_url": f"https://ornek.test/{kimlik}",
        "cekim_tarihi": datetime(2026, 8, 27),
        "tam_kayit": "{}",
        "ham_metin": "ornek",
        "ortalama_guven": 0.8,
        "doluluk_orani": 0.5,
    }
    return KampanyaKaydi(**{**varsayilan, **alanlar})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Terim eşleştirmesi: baş bağlanır, son serbest
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("anahtar", "terim"),
    [
        # Türkçe eklemeli: sonu serbest bırakmak ZORUNLU
        ("bankasinin kar payi", "banka"),
        ("vadesi kac ay", "vade"),
        ("kartlarinizla", "kart"),
        ("kampanyasinda", "kampanya"),
        ("ogrencilere ozel", "ogrenci"),
        # tam sözcük
        ("ev kredisi", "ev"),
    ],
)
def test_ek_almis_sozcuk_eslesir(anahtar: str, terim: str) -> None:
    assert terim_gecer(anahtar, terim)


@pytest.mark.parametrize(
    ("anahtar", "terim"),
    [
        # KUSURUN TA KENDİSİ
        ("pythonda liste nasil ters cevrilir", "ev"),
        # sözcüğün İÇİNE gömülü geçişler
        ("devam ediyor", "ev"),
        ("evrak teslimi", "ev"),
        ("guvence bedeli", "ev"),
        ("makarna tarifi", "kart"),
        ("davetiye", "vade"),
    ],
)
def test_sozcuk_icine_gomulu_terim_eslesmez(anahtar: str, terim: str) -> None:
    assert not terim_gecer(anahtar, terim)


@pytest.mark.parametrize(
    "soru",
    [
        "python'da liste nasil ters cevrilir",
        "bugun hava nasil",
        "bana bir siir yaz",
        "bitcoin fiyati ne kadar",
        "2 + 2 kac eder",
        "en iyi futbolcu kim",
    ],
)
def test_alan_disi_soru_iceri_sizmaz(soru: str) -> None:
    assert alan_disi_soru(soru, [_kayit("a")])


@pytest.mark.parametrize(
    "soru",
    [
        "kar payi orani kac",
        "vade kac ay",
        "hangi bankada masraf yok",
        "konut finansmani var mi",
        "ogrencilere ozel ne var",
        "emeklilere ozel kampanya var mi",
        "kobi icin ne var",
    ],
)
def test_alan_ici_soru_disari_atilmaz(soru: str) -> None:
    assert not alan_disi_soru(soru, [_kayit("a")])


def test_segment_sozcukleri_semadan_gelir() -> None:
    """İki yerde iki liste tutulmaz: «emekli» vardı, «öğrenci» yoktu.

    `HedefKitle.SEGMENT` altındaki kesimler şemada duruyor; chatbot'un alan
    sözlüğü oradan besleniyor. Yeni bir kesim eklendiğinde ikisi birden
    genişler.
    """
    from src.preprocessing.normalizasyon import arama_anahtari

    for ornek in SEGMENT_ORNEKLERI:
        assert arama_anahtari(ornek) in _ALAN_SOZCUKLERI, ornek


# ---------------------------------------------------------------------------
# Ürün süzgeci: her anahtarın veride bir karşılığı olmalı
# ---------------------------------------------------------------------------


def test_her_urun_anahtarinin_karsiligi_var() -> None:
    """Karşılığı olmayan etiket, süzgeci sessizce boşaltır.

    Ölçülen kusur: «kart» sözcüğü `kredi_karti` etiketine bakıyordu, oysa
    `KampanyaTuru` değeri `kart` ve hiçbir URL'de `kredi_karti` geçmiyor.
    Süzgeç 264 kaydın tamamını eliyor, «hangi bankaların kart kampanyası
    var?» sorusu «karşılaştırma için en az iki bankanın kaydı gerekiyor»
    cevabını alıyordu.
    """
    kayitlar = [
        _kayit(f"t{i}", kampanya_turu=tur.value, kaynak_url=f"https://ornek.test/{tur.value}")
        for i, tur in enumerate(KampanyaTuru)
    ]
    # Katılma hesabı ve altın bir kampanya TÜRÜ değil; URL diliminde geçerler.
    kayitlar += [
        _kayit("kh", kaynak_url="https://ornek.test/katilma-hesabi"),
        _kayit("al", kaynak_url="https://ornek.test/altin-hesabi"),
    ]

    for sozcuk in _URUN_ANAHTARLARI:
        assert _urun_filtrele(f"{sozcuk} hakkinda bilgi", kayitlar), (
            f"{sozcuk!r} süzgeci hiçbir kayda uymuyor — etiketin veride karşılığı yok"
        )


# ---------------------------------------------------------------------------
# Veri setinin kendisi soruluyorsa kapsam döner (27 Ağustos)
# ---------------------------------------------------------------------------
#
#     soru  : «Kaç kampanya var?»
#     cevap : rastgele tek bir Kuveyt Türk kampanyasının alan dökümü
#
# Jürinin ilk soracağı şeylerden biri; cevabı korpusta hazır duruyordu.


@pytest.fixture
def korpus() -> list[KampanyaKaydi]:
    return [
        _kayit("a1", banka_adi="A Katılım Bankası A.Ş."),
        _kayit("a2", banka_adi="A Katılım Bankası A.Ş."),
        _kayit("b1", banka_adi="B Katılım Bankası A.Ş."),
    ]


@pytest.mark.parametrize(
    "soru",
    [
        "kac kampanya var",
        "veri setinde kac kayit var",
        "kac tane kampanya topladiniz",
        "kac banka var",
        "veriler ne zaman toplandi",
        "hangi bankalari topluyorsunuz",
    ],
)
def test_korpus_sorusu_kapsam_dondurur(korpus, soru: str) -> None:
    cevap = sor(soru, korpus)
    assert cevap.niyet is Niyet.KORPUS_SORGUSU
    assert "3" in cevap.metin and "2" in cevap.metin, "sayım yapılmamış"
    assert cevap.dogrulama_gecti, "korpus sayıları kalkandan geçmeli"


@pytest.mark.parametrize(
    "soru",
    [
        # «kaç» tek başına korpus sorusu yapmaz — nesnesiyle yan yana olmalı
        "bu kampanyada kac taksit var",
        "A Katilim kar payi orani kac",
        "vade seceneği en fazla kac ay",
        # kapsam dışı soru «kaç» içeriyor diye içeri sızmamalı
        "kac tane futbolcu var",
    ],
)
def test_korpus_deseni_yanlis_tetiklenmez(korpus, soru: str) -> None:
    assert sor(soru, korpus).niyet is not Niyet.KORPUS_SORGUSU


def test_korpus_cevabi_tarihi_noktasiz_yazar(korpus) -> None:
    """«26.08.2026» kalkanda tek sayı (26082026) olarak okunur ve bloklanır."""
    cevap = sor("veriler ne zaman toplandi", korpus)
    assert "Ağustos" in cevap.metin
    assert cevap.dogrulama_gecti


# ---------------------------------------------------------------------------
# Evet/hayır: veride olmayan iddia REDDEDİLİR (27 Ağustos)
# ---------------------------------------------------------------------------
#
#     soru  : «Kuveyt Türk 500 ay vade veriyor mu?»
#     cevap : «Kuveyt Türk … — Azami vade: 48 ay …»   ← soru yanıtlanmıyor
#
# Uydurma yoktu ama açık bir ret de yoktu; jüri halüsinasyon yemi attığında
# görmek istediği şey budur.


@pytest.fixture
def tek_banka() -> list[KampanyaKaydi]:
    return [
        _kayit("k1", banka_adi="K Katılım Bankası A.Ş.", vade_ay_max=48,
               kar_payi_orani=2.87, kampanya_turu="ihtiyac_finansmani"),
        _kayit("k2", banka_adi="K Katılım Bankası A.Ş.", vade_ay_max=120,
               kar_payi_orani=1.99, kampanya_turu="konut_finansmani"),
    ]


@pytest.mark.parametrize(
    ("soru", "beklenen"),
    [
        ("K Katilim 500 ay vade veriyor mu", "120 ay"),
        ("K Katilim yuzde 99 kar payi mi aliyor", "%2,87"),
    ],
)
def test_tavani_asan_iddia_reddedilir(tek_banka, soru: str, beklenen: str) -> None:
    cevap = sor(soru, tek_banka)
    assert cevap.metin.startswith("**Hayır.**"), cevap.metin[:80]
    assert beklenen in cevap.metin, "gerçek tavan gösterilmemiş"
    assert cevap.kaynaklar, "ret de kanıtla verilir"


def test_reddedilen_sayi_cevaba_yazilmaz(tek_banka) -> None:
    """Uydurma sayıyı tekrar etmek onu meşru gösterir; kalkan da reddederdi."""
    cevap = sor("K Katilim 500 ay vade veriyor mu", tek_banka)
    assert "500" not in cevap.metin
    assert cevap.dogrulama_gecti


@pytest.mark.parametrize(
    "soru",
    [
        # tavanın ALTINDA — reddedilemez, olağan cevap dönmeli
        "K Katilim 48 ay vade veriyor mu",
        # sayı yok
        "K Katilim konut finansmani veriyor mu",
        # ölçüt yok
        "K Katilim 500 var mi",
    ],
)
def test_emin_olunmayan_iddia_reddedilmez(tek_banka, soru: str) -> None:
    """Emin olunmayan yerde susulur — «Hayır» yalnız tavan aşıldığında."""
    assert not sor(soru, tek_banka).metin.startswith("**Hayır.**")


# ---------------------------------------------------------------------------
# Tekil cevap: sorulan alanı taşıyan kayıt, yoksa «Belirtilmemiş» (27 Ağustos)
# ---------------------------------------------------------------------------
#
# Jüri havuzu 1. madde: «Kuveyt Türk'ün konut finansmanı kâr payı oranı ve
# maksimum vade süresi nedir?» Kayıt «en dolu» olana göre seçiliyordu —
# doluluk sorudan bağımsız bir ölçü. Seçilen kaydın oranı boştu ve satır hiç
# yazılmıyordu; kullanıcı sorduğu şeyin cevabını göremiyordu.


def _banka(kimlik: str, **alanlar: object) -> KampanyaKaydi:
    return _kayit(kimlik, banka_adi="K Katılım Bankası A.Ş.", **alanlar)


def test_sorulan_alani_tasiyan_kayit_secilir() -> None:
    """En dolu kayıt değil, SORULANI taşıyan kayıt."""
    kayitlar = [
        # daha dolu ama oranı yok
        _banka("dolu", vade_ay_max=120, finansman_tutari_max=5_000_000.0,
               odul_miktari=1_000.0, doluluk_orani=0.9),
        _banka("oranli", kar_payi_orani=1.89, vade_ay_max=60, doluluk_orani=0.4),
    ]
    cevap = sor("K Katılım kâr payı oranı kaç", kayitlar)
    assert "1,89" in cevap.metin, cevap.metin


def test_iki_olcut_sorulunca_ikisini_tasiyan_secilir() -> None:
    """«Kâr payı oranı VE maksimum vade» — biri yeterli sayılmamalı."""
    kayitlar = [
        _banka("yalniz_vade", vade_ay_max=120, doluluk_orani=0.9),
        _banka("ikisi", kar_payi_orani=1.89, vade_ay_max=60, doluluk_orani=0.3),
    ]
    cevap = sor("K Katılım kâr payı oranı ve maksimum vade süresi nedir", kayitlar)
    assert "1,89" in cevap.metin and "60 ay" in cevap.metin, cevap.metin


def test_sorulan_alan_hicbir_kayitta_yoksa_belirtilmemis_yazilir() -> None:
    """Sessizce atlamak, soruyu anlamamış görünmektir.

    Jüri havuzu 26. madde: «açıkça yazmıyorsa sistem tahminde bulunuyor mu
    yoksa Belirtilmemiş mi diyor?» — cevabın ekranda görünmesi gerekiyor.
    """
    kayitlar = [_banka("oransiz", vade_ay_max=120, doluluk_orani=0.9)]
    cevap = sor("K Katılım kâr payı oranı kaç", kayitlar)

    assert "Kâr payı oranı: **Belirtilmemiş**" in cevap.metin
    assert cevap.dogrulama_gecti


# ---------------------------------------------------------------------------
# Tekil cevap: taşıyanlar arasında SIRA — sorulan ölçütün avantajlı ucu
# ---------------------------------------------------------------------------
#
# 27 Ağustos'ta ölçüldü:
#
#     soru  : «Albaraka … 120 ay vade»
#     cevap : «Albaraka Türk — Diğer: … Azami vade: 6 ay»
#
# «Sorulan alanı taşıyan kayıt öncelikli» kuralı vardı ama TAŞIYANLAR
# ARASINDA sıra yoktu; karar dolulukla veriliyordu ve doluluk sorudan
# bağımsız bir ölçü. Vadeyi soran kullanıcıya bankanın EN KISA vadesi
# gösterilebiliyordu.


def test_tekil_cevap_sorulan_olcutun_avantajli_ucunu_secer() -> None:
    """Yön `ALAN_YONLERI`'nden gelir — karşılaştırma motoruyla AYNI kaynak."""
    kayitlar = [
        _banka("kisa", vade_ay_max=6, kar_payi_orani=1.0,
               finansman_tutari_max=150_000.0, doluluk_orani=0.9),
        _banka("uzun", vade_ay_max=120, doluluk_orani=0.2),
    ]
    assert "120 ay" in sor("K Katılım vade", kayitlar).metin


def test_tekil_cevap_kullanicinin_belirttigi_yonu_dinler() -> None:
    """Kullanıcı ucu söylediyse avantajlı uç değil, SÖYLENEN uç geçerlidir."""
    kayitlar = [
        _banka("kisa", vade_ay_max=6, doluluk_orani=0.2),
        _banka("uzun", vade_ay_max=120, doluluk_orani=0.9),
    ]
    assert "6 ay" in sor("K Katılım en kısa vade", kayitlar).metin


def test_tekil_cevap_kapsam_disi_kaydi_one_almaz() -> None:
    """ADR 020 kapısı sıralamada da geçerli — kart promosyonunun %0'ı.

    Karşılaştırmanın dışladığı kaydı tekil cevabın vitrine koyması,
    kullanıcının aynı soruya iki farklı yerde iki farklı cevap alması
    demekti.
    """
    kayitlar = [
        _banka("kart", kampanya_turu="kart", kar_payi_orani=0.0, doluluk_orani=0.9),
        _banka("finansman", kampanya_turu="konut_finansmani",
               kar_payi_orani=2.87, doluluk_orani=0.2),
    ]
    assert "2,87" in sor("K Katılım kâr payı oranı", kayitlar).metin


def test_yon_beyan_edilmemis_alanda_siralama_yapilmaz() -> None:
    """Yön uydurulmaz: beyan yoksa karar eski ölçüte, dolulukla, kalır."""
    from src.comparison.karsilastirma import ALAN_YONLERI
    from src.rag.chatbot import _odak_sirasi

    kayit = _banka("x", vade_ay_max=60)
    assert "taksit_sayisi" not in ALAN_YONLERI
    assert _odak_sirasi(kayit, "taksit_sayisi", None) == float("-inf")  # alan boş
    assert _odak_sirasi(kayit, None, None) == float("-inf")  # ölçüt sorulmadı
