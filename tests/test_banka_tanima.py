"""Banka adının TANINMASI — iki kapı asla çelişmez. AĞ İSTEMEZ.

NEDEN VAR — 27 Ağustos'ta ölçülen kusur:
    Soruda banka adı geçiyor mu sorusunu İKİ yer birbirinden habersiz
    cevaplıyordu. `alan_disi_soru` eşleştirmeyi `_bankalari_bul`'dan elle
    kopyalamıştı ve kopya geride kaldı:

        soru : «albarakatürk»
          _bankalari_bul -> 126 kayıt   (banka tanındı)
          alan_disi_soru -> True        (kapsam dışı ilan edildi)

    Kullanıcı karşılaştırmayı aldıktan hemen sonra banka adını yazınca
    «bu soru sistemin kapsamı dışında» cevabını alıyordu — sistemin
    hakkında 126 kaydı olan bir banka için.

BU TESTLER AD EZBERLEMEZ. Denenecek yazımlar korpustaki adlardan TÜRETİLİR
(`_yazim_varyantlari`); depoya yeni bir banka girdiğinde küme kendiliğinden
genişler ve aynı kusur o banka için de yakalanır.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.depolama import KampanyaKaydi
from src.preprocessing.normalizasyon import arama_anahtari
from src.rag.chatbot import (
    sifat_fiil_mi,
    Niyet,
    _bankalari_bul,
    _bilinen_bankalar,
    alan_disi_soru,
    sor,
    yabanci_banka_soruluyor,
)

# Korpusun banka adları — kazıyıcıların ürettiği gerçek biçimler.
BANKA_ADLARI = (
    "Albaraka Türk Katılım Bankası A.Ş.",
    "Dünya Katılım Bankası A.Ş.",
    "Hayat Finans Katılım Bankası A.Ş.",
    "Kuveyt Türk Katılım Bankası A.Ş.",
    "T.O.M. Katılım Bankası A.Ş.",
    "Türkiye Emlak Katılım Bankası A.Ş.",
    "Türkiye Finans Katılım Bankası A.Ş.",
    "Vakıf Katılım Bankası A.Ş.",
    "Ziraat Katılım Bankası A.Ş.",
)


def _kayit(kimlik: str, banka: str) -> KampanyaKaydi:
    return KampanyaKaydi(
        kampanya_id=kimlik,
        banka_kodu=kimlik.split("-")[0],
        banka_adi=banka,
        kaynak_url=f"https://ornek.test/{kimlik}",
        cekim_tarihi=datetime(2026, 8, 27, 12, 0),
        kampanya_turu="ihtiyac_finansmani",
        kar_payi_orani=2.5,
        tam_kayit="{}",
        ham_metin="ornek kampanya metni",
    )


@pytest.fixture
def korpus() -> list[KampanyaKaydi]:
    return [_kayit(f"{i:04d}-x", ad) for i, ad in enumerate(BANKA_ADLARI)]


def _yazim_varyantlari(banka_adi: str, tekil_ilk: bool) -> list[str]:
    """Bir kullanıcının o bankayı yazabileceği makul biçimler — ADDAN türetilir.

    Elle yazılmış takma ad listesi YOK: liste ezberlenirse test yalnız
    ezberlenen adları korur, yeni banka geldiğinde sessizce kör kalır.
    """
    parcalar = arama_anahtari(banka_adi).split()
    cekirdek = " ".join(parcalar[:2])
    varyantlar = [
        banka_adi,                          # tam ad
        cekirdek,                           # «kuveyt turk»
        cekirdek.replace(" ", ""),          # «kuveytturk»   — bitişik
        cekirdek.replace(".", ""),          # «t.o.m.» -> «tom katilim»
        cekirdek.replace(".", "").replace(" ", ""),
    ]
    if tekil_ilk:
        varyantlar.append(parcalar[0].replace(".", ""))  # «albaraka», «tom»
    return varyantlar


def _tekil_ilk_sozcuk(banka_adi: str) -> bool:
    """İlk sözcük tek bir bankaya mı ait? «türkiye» ikisine ait, ona güvenilmez."""
    ilk = arama_anahtari(banka_adi).split()[0].replace(".", "")
    sahipler = {
        ad for ad in BANKA_ADLARI
        if arama_anahtari(ad).split()[0].replace(".", "") == ilk
    }
    return len(sahipler) == 1


def _tum_varyantlar() -> list[tuple[str, str]]:
    return [
        (banka, yazim)
        for banka in BANKA_ADLARI
        for yazim in _yazim_varyantlari(banka, _tekil_ilk_sozcuk(banka))
    ]


@pytest.mark.parametrize(("banka", "yazim"), _tum_varyantlar())
def test_her_yazim_dogru_bankayi_bulur(korpus, banka: str, yazim: str) -> None:
    bulunan = {k.banka_adi for k in _bankalari_bul(yazim, korpus)}
    assert bulunan == {banka}, f"{yazim!r} -> {sorted(bulunan)}"


@pytest.mark.parametrize(("banka", "yazim"), _tum_varyantlar())
def test_taninan_banka_kapsam_disi_sayilmaz(korpus, banka: str, yazim: str) -> None:
    """KUSURUN TA KENDİSİ: iki kapı aynı soruya farklı cevap veriyordu."""
    assert not alan_disi_soru(yazim, korpus), (
        f"{yazim!r} bankayı buluyor ama kapsam dışı ilan ediliyor"
    )


def test_iki_kapi_hicbir_soruda_celismez(korpus) -> None:
    """Değişmez kural: banka bulunuyorsa soru kapsam dışı OLAMAZ.

    Tek tek yazımları denemek kusuru yakalar; bu test kuralı söyler. İleride
    biri eşleştirmeyi yine kopyalarsa burada patlar.
    """
    sorular = [yazim for _, yazim in _tum_varyantlar()] + [
        "kuveyttürk ve albarakatürk hangisi avantajlı",
        "tom bank kampanyaları neler",  # korpus metninde geçen marka yazımı
        "ziraatkatılım vade",
    ]
    for soru in sorular:
        if _bankalari_bul(soru, korpus):
            assert not alan_disi_soru(soru, korpus), f"çelişki: {soru!r}"


@pytest.mark.parametrize(
    "soru",
    [
        "bugün hava nasıl",
        "bana bir şiir yaz",
        "bitcoin fiyatı ne kadar",
        "en iyi futbolcu kim",
        "istanbul'da trafik var mı",
    ],
)
def test_alan_disi_sorular_hala_eleniyor(korpus, soru: str) -> None:
    """Kapı gevşetilmedi: banka adı geçmeyen soru hâlâ kapsam dışı.

    Kapsam kapısını `_bankalari_bul`'a bağlamak, kapıyı açmak değildi.
    """
    assert not _bankalari_bul(soru, korpus)
    assert alan_disi_soru(soru, korpus)


def test_bilinen_bankalar_listesi_korpustan_turer(korpus) -> None:
    assert set(_bilinen_bankalar(korpus)) == set(BANKA_ADLARI)


# ---------------------------------------------------------------------------
# Korpusta OLMAYAN banka — kaynaşmış morfem (27 Ağustos)
# ---------------------------------------------------------------------------
#
# `yabanci_banka_soruluyor` tam bu hata için yazılmıştı ama yalnız AYRI
# yazılan «… Bankası» sözcüğünü görüyordu. Uçtan uca taramada ölçüldü:
#
#     soru  : «Akbank ne kadar vade veriyor?»
#     cevap : «Kuveyt Türk Katılım Bankası A.Ş. — Alışveriş Puanı Kampanyası…»
#
# Kalkan bunu yakalayamaz: sayı gerçekten yapısal veride var, yalnızca YANLIŞ
# bankanın. «Garanti Bankası» ile «Akbank» arasındaki tek fark bir boşluktu.


@pytest.mark.parametrize(
    "soru",
    [
        "Akbank ne kadar vade veriyor",
        "Akbank'tan ne kadar finansman alabilirim",
        "Denizbank kâr payı oranı kaç",
        "Halkbank kampanyaları neler",
        # Vakıfbank ile Vakıf Katılım AYRI kurumlar; adın benzerliği
        # birinin verisini diğerine yazdırmamalı.
        "vakıfbank kampanyaları",
        # Ayrı yazılan biçim — eskiden de yakalanıyordu, kırılmamalı.
        "Garanti Bankası'nın kâr payı oranı kaç",
    ],
)
def test_korpusta_olmayan_banka_baskasinin_verisiyle_cevaplanmaz(
    korpus, soru: str
) -> None:
    assert yabanci_banka_soruluyor(soru, korpus), f"{soru!r} yabancı sayılmadı"

    cevap = sor(soru, korpus)
    assert cevap.niyet is Niyet.KAPSAM_DISI
    assert not cevap.kaynaklar
    # Kapsadığımız bankaların adı cevapta GEÇER (kullanıcıya listelenir);
    # geçmemesi gereken şey onların VERİSİDİR — kaynakça boş, sayı yok.
    assert "katılım bankası değil" in cevap.metin
    assert not any(ch.isdigit() for ch in cevap.metin), (
        f"{soru!r} cevabında sayısal veri sunulmuş"
    )


@pytest.mark.parametrize(("banka", "yazim"), _tum_varyantlar())
def test_kendi_bankamiz_yabanci_sayilmaz(korpus, banka: str, yazim: str) -> None:
    """Morfem kuralı kendi bankalarımızı vurmamalı — «tom bank» korpusta var."""
    assert not yabanci_banka_soruluyor(yazim, korpus)


@pytest.mark.parametrize(
    "soru",
    [
        "hangi banka daha avantajlı",
        "her bankada masraf alınıyor mu",
        "katılım bankacılığı nedir",
        "en yüksek ödülü hangi banka veriyor",
        "tüm bankaların vadelerini karşılaştır",
    ],
)
def test_tur_adlandiran_soru_yabanci_sayilmaz(korpus, soru: str) -> None:
    """«banka», «bankacılık» bir KURUMU değil türü adlandırır.

    Bu ayrım yapılmazsa korpusun tamamına sorulan meşru sorular kapsam dışına
    düşer — «En yüksek ödülü hangi banka veriyor?» bir zamanlar düşüyordu.
    """
    assert not yabanci_banka_soruluyor(soru, korpus)


# ---------------------------------------------------------------------------
# Adın ORTASINDAN tutan yazımlar (27 Ağustos, jüri havuzu 5. madde)
# ---------------------------------------------------------------------------
#
#     soru  : «Emlak Katılım'ın konut finansmanı kâr payı oranı nedir?»
#     cevap : «Türkiye Finans Katılım Bankası A.Ş. — Konut Finansmanı …»
#
# Korpustaki ad «Türkiye Emlak Katılım Bankası A.Ş.»; çekirdek «turkiye emlak»,
# ilk sözcük «turkiye» ve o İKİ bankaya ait. Kullanıcının söylediği «emlak»
# hiçbir kapıdan geçmiyor, yedek devreye girip BAŞKA bankanın verisini
# sunuyordu — `yabanci_banka_soruluyor`'un önlemeye çalıştığı hatanın aynısı.


@pytest.mark.parametrize(
    "yazim",
    ["Emlak Katılım", "emlak katılım", "emlakkatılım", "emlak katılımın oranı"],
)
def test_adin_ortasindan_tutan_yazim_eslesir(korpus, yazim: str) -> None:
    bulunan = {k.banka_adi for k in _bankalari_bul(yazim, korpus)}
    assert bulunan == {"Türkiye Emlak Katılım Bankası A.Ş."}, sorted(bulunan)


def test_tur_adlandiran_sozcuk_banka_sayilmaz(korpus) -> None:
    """«katılım», «bankası», «finans» bir kurumu değil türü adlandırır.

    Benzersizlik kapısı bugünkü korpusta zaten eliyor; küme tek bankaya
    süzüldüğünde eleme kalmadığı için ayrıca yazılı bir kapı var.
    """
    tek_banka = [k for k in korpus if k.banka_adi.startswith("Vakıf")]
    assert tek_banka, "test kurgusu bozuk"
    for soru in ("hangi banka daha avantajlı", "katılım bankacılığı nedir"):
        assert _bankalari_bul(soru, tek_banka) == [], soru


# ---------------------------------------------------------------------------
# KESME EKİ — «Albaraka'dan», «Kuveyt Türk'ün» (27 Ağustos)
# ---------------------------------------------------------------------------
#
# `arama_anahtari` kesmeyi SİLER ve tokenizasyon için doğrusu odur («TL'ye»
# tek belirteçtir). Ama özel ad eşleştirmesinde kesme, adı kendi ekinden
# ayıran işaretin ta kendisidir. `_bankalari_bul` bunu biliyordu ve
# `anahtar.replace("'", " ")` yazıyordu — ama `anahtar` zaten kesmesizdi,
# yani satır ÖLÜYDÜ:
#
#     «Albaraka'dan 1.000.000 TL konut finansmanı»  -> HİÇBİR banka eşleşmedi
#
# Profil kolu adlandırılan bankayı yok sayıp dokuz bankayı sıralıyordu.


def _ekli_yazimlar(banka_adi: str, tekil_ilk: bool) -> list[str]:
    """Bankanın kesme ekli biçimleri — ADDAN türetilir, ezberlenmez."""
    parcalar = arama_anahtari(banka_adi).split()
    govdeler = [" ".join(parcalar[:2])]
    if tekil_ilk:
        govdeler.append(parcalar[0].replace(".", ""))
    return [f"{govde}'{ek}" for govde in govdeler for ek in ("dan", "nin", "un", "a")]


@pytest.mark.parametrize(
    ("banka", "yazim"),
    [
        (banka, yazim)
        for banka in BANKA_ADLARI
        for yazim in _ekli_yazimlar(banka, _tekil_ilk_sozcuk(banka))
    ],
)
def test_kesme_ekli_yazim_dogru_bankayi_bulur(korpus, banka: str, yazim: str) -> None:
    bulunan = {k.banka_adi for k in _bankalari_bul(f"{yazim} kâr payı oranı ne", korpus)}
    assert bulunan == {banka}, f"{yazim!r} -> {bulunan}"


def test_kesme_ayrimi_ek_serbestligi_getirmez(korpus) -> None:
    """Kesme bir SINIRDIR, baş bağlama değil.

    Eki serbest bırakmak (`terim_gecer` gibi) daha kolay olurdu ama
    «emlakçı»yı Türkiye Emlak'a bağlardı — `YAKINLIK_ESIGI` bu eşleşmeyi
    ölçerek dışarıda bırakmıştı (0,833). Kesme kullanıcının kendi koyduğu
    sınırdır; ek serbestliği bizim tahminimiz olurdu.
    """
    assert _bankalari_bul("emlakçı kredisi var mı", korpus) == []
    assert _bankalari_bul("ziraatçilik hakkında", korpus) == []


# ---------------------------------------------------------------------------
# SIFAT-FİİL — «olan banka» bir kurumu ADLANDIRMAZ (27 Ağustos)
# ---------------------------------------------------------------------------
#
#     soru  : «Kâr payı oranı en düşük OLAN BANKA aynı zamanda en uzun vadeyi
#              de veriyor mu?»
#     cevap : «Sorduğunuz banka bir katılım bankası değil…» + dokuz banka
#
# Soruda hiçbir banka adlandırılmamıştı. `_BELIRTEC_SOZCUKLERI` sabit bir
# liste olduğu için «olan» orada yoktu; listeye eklemek aynı hatayı «sunan»,
# «veren», «sağlayan» için tekrar ederdi.


@pytest.mark.parametrize(
    "soru",
    [
        "kâr payı oranı en düşük olan banka en uzun vadeyi de veriyor mu",
        "masrafsız finansman sunan banka hangisi",
        "en uzun vadeyi veren bankanın oranı ne",
        "kampanya düzenleyen bankalar hangileri",
        "en çok ödül sağlayan bankada vade kaç ay",
        "bu oranı uyguladığı bankada masraf var mı",
    ],
)
def test_sifat_fiil_nitelemesi_yabanci_banka_sayilmaz(korpus, soru: str) -> None:
    assert not yabanci_banka_soruluyor(soru, korpus), soru


@pytest.mark.parametrize(
    ("sozcuk", "beklenen"),
    [
        ("olan", True), ("sunan", True), ("veren", True),
        ("verdigi", True), ("sundugu", True), ("verecek", True),
        ("en", False),      # iki harf — sıfat-fiil değil, belirteç
        ("garanti", False), ("ziraat", False), ("kuveyt", False),
    ],
)
def test_sifat_fiil_kurali(sozcuk: str, beklenen: bool) -> None:
    """Kural EK arar, sözcük listesi değil — `MUHATAP_EKLERI` ile aynı refleks."""
    assert sifat_fiil_mi(sozcuk) is beklenen


def test_yabanci_banka_hala_yakalaniyor(korpus) -> None:
    """Muafiyet kapıyı açmadı: adlandırılan yabancı banka hâlâ reddedilir."""
    for soru in ("Garanti Bankası'nın konut kredisi faizi kaç",
                 "Akbank ne kadar vade veriyor",
                 "Denizbank kampanyaları neler"):
        assert yabanci_banka_soruluyor(soru, korpus), soru
