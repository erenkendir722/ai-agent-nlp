"""Kampanya konusu eşleşmesi — AĞ İSTEMEZ (ADR 026).

28 Ağustos'ta ölçülen kusur:

    soru  : «TOM Katılım'ın AKARYAKIT kampanyasında ne kadar iade var?»
    cevap : «… Hadi Kredi Kartı: Ödül miktarı: 250 TL»
    kaynak: …/a101lerde-meyve-sebze-alisverislerinde-10-nakit-iade

Doğru kayıt aynı bankada duruyordu (`odul_miktari = 500`, adresinde
«akaryakit» yazan kampanya). Banka tanınıyor, ürün sınıfı tanınıyor, segment
tanınıyor — kampanyanın KONUSU hiçbir yerde okunmuyordu. Kalkan bunu
göremez: cevaptaki sayı gerçekten kayıtta var, yalnızca YANLIŞ kaydın.

Buradaki sınamalar üç şeyi birden tutuyor: eşleştirme kuralını (`ayni_kok`),
neyin konu sözcüğü sayıldığını (`konu_sozcukleri`) ve kayıt seçiminin
konudan önce başka hiçbir ölçüte düşmediğini.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from src.depolama import KampanyaKaydi
from src.rag.chatbot import (
    cekimli_fiil_mi,
    konu_sozcukleri,
    niteleyen_fiil_mi,
    sor,
)
from src.rag.konu import (
    KONU_TAVANI,
    ayni_kok,
    konu_agirliklari,
    konu_metni,
    konu_suz,
    konu_tavani,
)


def _kayit(dilim: str, **alanlar: object) -> KampanyaKaydi:
    """Adres dilimi kampanyanın ADIDIR — kayıtlar da öyle kurulur."""
    varsayilan: dict[str, object] = {
        "kampanya_id": dilim,
        "banka_kodu": "0299",
        "banka_adi": "K Katılım Bankası A.Ş.",
        "kaynak_url": f"https://ornek.test/kampanyalar/{dilim}",
        "cekim_tarihi": datetime(2026, 8, 28),
        "tam_kayit": "{}",
        "ham_metin": "ornek",
        "ortalama_guven": 0.8,
        "doluluk_orani": 0.5,
    }
    return KampanyaKaydi(**{**varsayilan, **alanlar})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Kök eşleşmesi: Türkçe iki yönlü ek alır
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("bir", "iki"),
    [
        ("akaryakit", "akaryakit"),
        ("akaryakitta", "akaryakit"),        # ek SORUDA
        ("harcamasina", "harcamalarinda"),   # ek İKİ TARAFTA da farklı
        ("kart", "kartlar"),                 # kısa sözcük tam ön ek
        ("marketten", "market"),
    ],
)
def test_ayni_kokten_sayilir(bir: str, iki: str) -> None:
    assert ayni_kok(bir, iki)


@pytest.mark.parametrize(
    ("bir", "iki"),
    [
        ("market", "marka"),   # ortak «mar» — üç harf kök değildir
        ("kar", "kart"),       # kâr payı ile kart aynı konu değil
        ("var", "varan"),      # ölçülen kusur: «var mı?» 114 kampanyaya eşleşiyordu
        ("iade", "iadxx"),
    ],
)
def test_ayri_koktur(bir: str, iki: str) -> None:
    assert not ayni_kok(bir, iki)


# ---------------------------------------------------------------------------
# Konu metni: kampanyanın ADI, sayfanın gövdesi değil
# ---------------------------------------------------------------------------


def test_konu_metni_adresin_son_dilimidir() -> None:
    """Yol öneki site gezinmesidir; «kendim için» bir konu adlandırmaz."""
    kayit = _kayit(
        "akaryakit-harcamalarina-500-tl-iade",
        kaynak_url=(
            "https://ornek.test/kendim-icin/kart-kampanyalari/"
            "akaryakit-harcamalarina-500-tl-iade?IsArchived=true"
        ),
    )
    metin = konu_metni(kayit)
    assert "akaryakit" in metin
    assert "icin" not in metin, "yol öneki konuya karışıyor"


def test_konu_metni_sayfa_govdesini_okumaz() -> None:
    """Bir kampanya sayfası BAŞKA kampanyalardan da söz eder.

    Ölçüldü: TOM'un 123 kaydının 10'unda «akaryakıt» gövdede geçiyor,
    gerçekten akaryakıt kampanyası olan 3'ü.
    """
    kayit = _kayit("meyve-sebze-alisverisi", ham_metin="Akaryakıt kampanyamız da var!")
    assert "akaryakit" not in konu_metni(kayit)


# ---------------------------------------------------------------------------
# ÖLÇÜLEN KUSURUN KENDİSİ
# ---------------------------------------------------------------------------


def test_konusu_sorulan_kampanya_secilir() -> None:
    """Doğru sayı, YANLIŞ kampanyadan verilmez.

    «Yanlış kayıt» daha dolu ve daha yüksek ödüllü; iki eski hakem de
    (doluluk, ölçütün avantajlı ucu) onu seçiyordu.
    """
    kayitlar = [
        _kayit("a101lerde-meyve-sebze-alisverislerinde-10-nakit-iade",
               odul_miktari=250.0, indirim_orani=30.0, vade_ay_max=12,
               kar_payi_orani=0.0, kampanya_turu="kart", doluluk_orani=0.9),
        _kayit("hadi-black-kredi-karti-ile-akaryakit-harcamalarina-500-tl-iade",
               odul_miktari=500.0, kampanya_turu="kart", doluluk_orani=0.2),
    ]
    cevap = sor("K Katılım'ın akaryakıt kampanyasında ne kadar iade var?", kayitlar)

    assert "500" in cevap.metin, cevap.metin
    assert "akaryakit" in cevap.kaynaklar[0].url
    assert cevap.dogrulama_gecti


def test_konu_olcutun_avantajli_ucundan_once_gelir() -> None:
    """«iade» ölçüt olarak çözülür (`odul_miktari`) ve en yükseğe bakar.

    Kullanıcı bir üstünlük sormadı, BİR KAMPANYAYI sordu: konu bir tercih
    değil kimlik kısıtıdır. Bu sıra bozulursa cevap, bankanın en yüksek
    ödülünü akaryakıt kampanyası diye sunar.
    """
    kayitlar = [
        _kayit("restoran-harcamalarinda-10000-tlye-varan-iade", odul_miktari=10_000.0),
        _kayit("akaryakit-harcamalarina-500-tl-iade", odul_miktari=500.0),
    ]
    cevap = sor("K Katılım akaryakıt kampanyasında ne kadar iade var", kayitlar)
    assert "500" in cevap.metin, cevap.metin


def test_konusu_gecmeyen_kayit_kumeden_duser() -> None:
    kayitlar = [
        _kayit("akaryakit-kampanyasi", odul_miktari=500.0),
        _kayit("market-kampanyasi", odul_miktari=250.0),
        _kayit("restoran-kampanyasi", odul_miktari=100.0),
    ]
    agirlik = konu_agirliklari(["akaryakit"], kayitlar)
    assert [k.kampanya_id for k in konu_suz(agirlik, kayitlar)] == ["akaryakit-kampanyasi"]


# ---------------------------------------------------------------------------
# Kapının sınırları
# ---------------------------------------------------------------------------


def test_korpusta_olmayan_konu_kumeyi_bosaltmaz() -> None:
    """Konu adlandırılmış ama karşılığı yoksa eski davranış doğrudur.

    `_segment_filtrele` ile aynı sözleşme: boş liste «daraltma yok» demek.
    """
    kayitlar = [_kayit("akaryakit-kampanyasi"), _kayit("market-kampanyasi")]
    assert konu_suz(konu_agirliklari(["kripto"], kayitlar), kayitlar) == []


def test_her_kampanyada_gecen_sozcuk_konu_sayilmaz() -> None:
    """«varan», «fırsatı», «özel» kampanyayı değil kampanyacılığı adlandırır."""
    kayitlar = [_kayit(f"varan-firsat-{i}") for i in range(40)]
    kayitlar.append(_kayit("akaryakit-firsati"))
    assert konu_agirliklari(["varan"], kayitlar) == {}
    assert konu_agirliklari(["akaryakit"], kayitlar)


def test_tavan_kucuk_kumelerde_sifira_inmez() -> None:
    """Kesir üç kayıtlık bir kümede 0,09'dur; taban 1 kayıt olmalı."""
    assert konu_tavani(3) == 1
    assert konu_tavani(979) == int(979 * KONU_TAVANI)


def test_konu_suzgeci_birlesimdir() -> None:
    """Kullanıcı üç konu SAYIYORSA üçünü birden taşıyan kampanyayı sormaz.

    Kesişim kuralı 444 kaydı 2'ye indiriyordu (28 Ağustos ölçümü); doğrusu
    konulardan birini taşıyan her kaydın kümede kalması.
    """
    kayitlar = [
        _kayit("akaryakit-ve-beyaz-esya-kampanyasi"),  # İKİ konu birden
        _kayit("market-kampanyasi"),                   # yalnız biri
        _kayit("konut-finansmani"),                    # hiçbiri
    ]
    agirlik = konu_agirliklari(["akaryakit", "market", "beyaz"], kayitlar)
    kalanlar = {k.kampanya_id for k in konu_suz(agirlik, kayitlar)}

    assert kalanlar == {"akaryakit-ve-beyaz-esya-kampanyasi", "market-kampanyasi"}
    # Çok eşleşen kayıt daha AĞIRDIR — ama tek eşleşeni kümeden atmaz.
    assert agirlik["akaryakit-ve-beyaz-esya-kampanyasi"] > agirlik["market-kampanyasi"]


def test_suresi_dolmus_kampanya_ayni_konudaki_guncelin_onune_gecmez() -> None:
    """Ölçüldü: Ziraat'in üç market kampanyasından ikisi arşivde ve seçilen
    o ikisinden biriydi — aynı tutarı yazan güncel kayıt kümedeydi."""
    dun = date.today() - timedelta(days=1)
    kayitlar = [
        _kayit("market-alisverislerinize-1500-tl-arsiv",
               odul_miktari=1_500.0, kampanya_bitis=dun, doluluk_orani=0.9),
        _kayit("market-alisverislerinize-1500-tl",
               odul_miktari=1_500.0, doluluk_orani=0.2),
    ]
    cevap = sor("K Katılım market kampanyasında ne kadar ödül var", kayitlar)
    assert "arsiv" not in cevap.kaynaklar[0].url, cevap.metin


# ---------------------------------------------------------------------------
# Hangi sözcük KONU sayılır
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "soru",
    [
        "K Katılım'ın kâr payı oranı kaç",       # ölçüt sözlükten çözülür
        "K Katılım konut finansmanı var mı",     # ürün sınıfı süzgeci çözer
        "en düşük vadeyi hangi banka veriyor",   # banka ve yön dağarcığı
        "emeklilere özel kampanya var mı",       # segment süzgeci çözer
        "Başvuru nasıl yapılıyor?",              # çekimli fiil
        "kâr payı en düşük olan banka hangisi",  # niteleyen fiil (ADR 024)
    ],
)
def test_baska_ayristiricinin_cozdugu_sozcuk_konu_sayilmaz(soru: str) -> None:
    assert konu_sozcukleri(soru, [_kayit("ornek-kampanya")]) == []


@pytest.mark.parametrize(
    ("soru", "beklenen"),
    [
        ("K Katılım'ın akaryakıt kampanyası", "akaryakit"),
        ("K Katılım restoran harcamalarında ne veriyor", "restoran"),
        ("A101 kampanyası var mı", "a101"),
        ("mağazadan alışverişte ne kazanırım", "magazadan"),
    ],
)
def test_konu_adi_ayakta_kalir(soru: str, beklenen: str) -> None:
    """Ad sınıfı AÇIKTIR; dilbilgisi kapıları onu yutmamalı.

    «restoran» ve «mağazadan» sonuna «-an/-en» aldığı için sıfat-fiil
    kuralına takılıyordu — o kural korpusun konu dağarcığından 43 sözcük
    yutuyordu (bkz. `AZAMI_FIIL_GOVDESI`).
    """
    assert beklenen in konu_sozcukleri(soru, [_kayit("ornek-kampanya")])


@pytest.mark.parametrize("sozcuk", ["olan", "veren", "sunan", "alan"])
def test_niteleyen_fiil_taninir(sozcuk: str) -> None:
    assert niteleyen_fiil_mi(sozcuk)


@pytest.mark.parametrize("sozcuk", ["restoran", "mobilden", "worldpuan", "magazadan"])
def test_ad_niteleyen_fiil_sayilmaz(sozcuk: str) -> None:
    assert not niteleyen_fiil_mi(sozcuk)


@pytest.mark.parametrize("sozcuk", ["yapiliyor", "veriyorsunuz", "geldiginde", "sundugu"])
def test_cekimli_fiil_taninir(sozcuk: str) -> None:
    assert cekimli_fiil_mi(sozcuk)


def test_yorgun_fiil_sayilmaz() -> None:
    """Ek sözcüğün BAŞINDA aranmaz."""
    assert not cekimli_fiil_mi("yorgun")


# ---------------------------------------------------------------------------
# Sözlükten gelen ölçüt: «iade» ödül alanıdır
# ---------------------------------------------------------------------------


def test_iade_odul_olcutune_baglanir() -> None:
    """Yazım SÖZLÜĞE eklenir, koda değil (`docs/TERIM_SOZLUGU.md`).

    Sözlükte yalnız «nakit iade» yazılıydı; kullanıcı «iade» diyor ve soru
    hiçbir ölçüt taşımıyor sayılıyordu.
    """
    from src.rag.chatbot import _sorulan_olcut

    assert _sorulan_olcut("ne kadar iade var") == "odul_miktari"
