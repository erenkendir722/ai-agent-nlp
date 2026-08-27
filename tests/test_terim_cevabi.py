"""Tanım soruları ve yazım hatası toleransı — AĞ İSTEMEZ.

27 Ağustos'ta ölçülen iki kusur:

    soru  : «Kâr payı nedir?»
    cevap : «Kuveyt Türk … — Alışveriş Puanı Kampanyası: aylık %1,99 …»

    soru  : «albraka kâr payı oranı»
    cevap : dokuz bankanın tamamı üzerinden karşılaştırma

Birincisinde tanım kendi depomuzda, `docs/TERIM_SOZLUGU.md`'de yazılıydı ve
sözlüğün çıkarım isteminden başka tüketicisi yoktu. İkincisinde eşleştirme
birebir metin karşılaştırmasıydı.

EZBER YOK: ne terim listesi ne yazım hatası listesi yazıldı. Tanımlar sözlük
dosyasından okunuyor, yazım hatası mesafe hesabıyla çözülüyor — ikisi de
veriden türüyor ve yeni terim/banka eklendiğinde kendiliğinden genişliyor.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.depolama import KampanyaKaydi
from src.rag.chatbot import YAKINLIK_ESIGI, Niyet, _bankalari_bul, sor
from src.terim_sozlugu import tanim_sorusu_mu, terim_bul, terimler

BANKALAR = (
    "Albaraka Türk Katılım Bankası A.Ş.",
    "Kuveyt Türk Katılım Bankası A.Ş.",
    "T.O.M. Katılım Bankası A.Ş.",
    "Türkiye Emlak Katılım Bankası A.Ş.",
    "Türkiye Finans Katılım Bankası A.Ş.",
    "Ziraat Katılım Bankası A.Ş.",
)


def _kayit(kimlik: str, banka: str) -> KampanyaKaydi:
    return KampanyaKaydi(
        kampanya_id=kimlik,
        banka_kodu=kimlik.split("-")[0],
        banka_adi=banka,
        kaynak_url=f"https://ornek.test/{kimlik}",
        cekim_tarihi=datetime(2026, 8, 27),
        kampanya_turu="ihtiyac_finansmani",
        kar_payi_orani=2.5,
        vade_ay_max=36,
        tam_kayit="{}",
        ham_metin="ornek",
        ortalama_guven=0.8,
        doluluk_orani=0.5,
    )


@pytest.fixture
def korpus() -> list[KampanyaKaydi]:
    return [_kayit(f"{i:04d}-x", ad) for i, ad in enumerate(BANKALAR)]


# ---------------------------------------------------------------------------
# Sözlük ayrıştırma
# ---------------------------------------------------------------------------


def test_sozluk_okunuyor() -> None:
    """G-09 en az 60 terim istiyor; ayrıştırıcı hepsini görmeli."""
    assert len(terimler()) >= 60


def test_sartnamenin_bes_kavrami_da_okunuyor() -> None:
    """§1'deki beş kavram TABLO DEĞİL, `### Başlık` + düzyazı biçiminde.

    Ayrıştırıcı önce yalnız tabloları okuyordu ve tam da en çok sorulacak beş
    kavramı kaçırıyordu — «Kâr payı nedir?» bulunamıyordu.
    """
    for soru in (
        "kâr payı oranı nedir",
        "finansman maliyeti nedir",
        "katılım fonu nedir",
        "masrafsız finansman nedir",
        "avantajlı finansman nedir",
    ):
        assert terim_bul(soru) is not None, soru


@pytest.mark.parametrize(
    ("soru", "beklenen"),
    [
        # kullanıcı KISA söyler, sözlükteki ad tam biçimdir
        ("kâr payı nedir", "Kâr Payı Oranı"),
        ("vade nedir", "Vade"),
        # en uzun tam geçiş kazanır: iki kavram karıştırılmamalı
        (
            "kâr payı dağıtım oranı nedir",
            "Kâr payı dağıtım oranı / katılım oranı / kâr paylaşım oranı",
        ),
        # eğik çizgi EŞ ANLAMLI yazımları ayırır
        ("dosya parası nedir", "Dosya masrafı / dosya parası"),
        # ön ekte en KISA kazanır — genel olan istenir
        ("vade farksız ne demek", "Vade farksız"),
    ],
)
def test_terim_dogru_eslesir(soru: str, beklenen: str) -> None:
    terim = terim_bul(soru)
    assert terim is not None and terim.ad == beklenen


# ---------------------------------------------------------------------------
# Tanım cevabı
# ---------------------------------------------------------------------------


def test_tanim_sorusu_sozlukten_cevaplanir(korpus) -> None:
    cevap = sor("kâr payı nedir?", korpus)

    assert cevap.niyet is Niyet.TANIM_SORGUSU
    assert "faiz yerine" in cevap.metin
    assert "kar_payi_orani" in cevap.metin, "sistemdeki karşılığı yazılmamış"
    assert cevap.dogrulama_gecti, f"kalkan reddetti: {cevap.reddedilen_sayilar}"


def test_tanim_cevabi_kaynagini_soyler(korpus) -> None:
    """Tanım bir kampanya kaydından gelmiyor; nereden geldiği yazılmalı."""
    assert "TERIM_SOZLUGU" in sor("murabaha nedir", korpus).metin


@pytest.mark.parametrize(
    "soru",
    [
        # KUSUR: «nedir» geçiyor ama bir DEĞER isteniyor
        "Kuveyt Türk'ün konut finansmanı kâr payı oranı nedir",
        "Ziraat Katılım'ın vadesi nedir",
        "en düşük kâr payı hangi bankada",
        "kâr payı oranı kaç",
    ],
)
def test_deger_sorusu_tanima_dusmez(korpus, soru: str) -> None:
    """Jüri havuzunun 1. ve 5. maddesi bu kalıpta ve SAYI istiyor.

    Tanım yolu bunları da yutunca chatbot bankanın oranı yerine sözlük
    tanımını dönüyordu.
    """
    assert sor(soru, korpus).niyet is not Niyet.TANIM_SORGUSU


def test_tanim_ipucu_yoksa_tanim_donmez(korpus) -> None:
    assert not tanim_sorusu_mu("kâr payı oranı 2,5 mi")


# ---------------------------------------------------------------------------
# Yazım hatası — mesafe hesabı, ezber değil
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("yanlis", "beklenen"),
    [
        ("albraka kâr payı oranı", "Albaraka Türk Katılım Bankası A.Ş."),
        ("albarka türk", "Albaraka Türk Katılım Bankası A.Ş."),
        ("kuvet turk vade", "Kuveyt Türk Katılım Bankası A.Ş."),
        ("zirat katılım ödül", "Ziraat Katılım Bankası A.Ş."),
        ("türkiyefinnas", "Türkiye Finans Katılım Bankası A.Ş."),
    ],
)
def test_yazim_hatasi_duzeltilir(korpus, yanlis: str, beklenen: str) -> None:
    bulunan = {k.banka_adi for k in _bankalari_bul(yanlis, korpus)}
    assert bulunan == {beklenen}, sorted(bulunan)


@pytest.mark.parametrize(
    "soru",
    [
        # «tumkatilim» ~ «tomkatilim» = 0,90 — eşiğin ÜSTÜNDE ama bu soru
        # korpusun tamamına soruluyor, düzeltilecek bir yazım hatası yok.
        "tüm katılım bankaları",
        "her bankada masraf var mı",
        "hangi banka daha avantajlı",
        "katılım bankacılığı nedir",
        # alan dışı soru yakınlıkla içeri sızmamalı
        "bugün hava nasıl",
        "python listesi nasıl ters çevrilir",
    ],
)
def test_yakinlik_yanlis_eslesme_uretmez(korpus, soru: str) -> None:
    assert _bankalari_bul(soru, korpus) == []


def test_kesin_eslesme_yakinlikla_ezilmez(korpus) -> None:
    """Yakınlık YALNIZ hiçbir kesin eşleşme yokken devreye girer."""
    bulunan = {k.banka_adi for k in _bankalari_bul("kuveyt türk mü albaraka mı", korpus)}
    assert bulunan == {
        "Kuveyt Türk Katılım Bankası A.Ş.",
        "Albaraka Türk Katılım Bankası A.Ş.",
    }


def test_yakinlik_esigi_olculmus_araliktadir() -> None:
    """Eşik gerçek yazım hatasıyla meşru sözcüğü ayırmak zorunda.

        albraka ~ albaraka    0,933   ← düzeltilmeli
        emlakci ~ emlak       0,833   ← DÜZELTİLMEMELİ
    """
    from difflib import SequenceMatcher

    assert SequenceMatcher(None, "albraka", "albaraka").ratio() > YAKINLIK_ESIGI
    assert SequenceMatcher(None, "emlakci", "emlak").ratio() < YAKINLIK_ESIGI
