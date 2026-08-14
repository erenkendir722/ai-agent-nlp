"""Eleştirmen ajanının testleri — halüsinasyon savunmasının regresyon kalkanı.

Bu ajan `extraction/llm.py` içinden çıkarıldı (14 Ağustos, ajan mimarisi).
Taşıma sırasında bir kontrolün düşmesi halüsinasyon oranını sessizce yükseltir
ve bunu ancak `make eval` koşulduğunda fark ederdik. Buradaki testler o
davranışı taşımadan bağımsız olarak sabitler.

Ollama GEREKTİRMEZ: eleştirmen deterministik koddur, LLM kullanmaz. Testinin
modelsiz koşabiliyor olması da zaten iddianın bir parçası.
"""

from __future__ import annotations

import pytest

from src.ajanlar.elestirmen import ElestirmenAjani
from src.schema import KANIT_ZORUNLU_ALANLAR

METIN = (
    "Konut Finansmanı Kampanyası. Aylık kâr payı oranı %1,89'dan başlayan "
    "avantajlı finansman. 120 aya varan vade ve 5.000.000 TL'ye kadar "
    "finansman imkânı. Tahsis ücreti 500 TL'dir. Kampanya 30.09.2026 "
    "tarihinde sona erecektir."
)


@pytest.fixture
def elestirmen() -> ElestirmenAjani:
    return ElestirmenAjani()


# ---------------------------------------------------------------------------
# Kabul
# ---------------------------------------------------------------------------


def test_metinde_birebir_gecen_deger_kabul_edilir(elestirmen):
    kabul, konum = elestirmen.dogrula("kar_payi_orani", "%1,89", METIN)
    assert kabul is True
    assert konum is not None
    assert METIN[konum[0] : konum[1]] == "%1,89"


def test_bicim_farki_halusinasyon_sayilmaz(elestirmen):
    """Modelin '%1,89' yerine '% 1,89' yazması biçim farkıdır, uydurma değil.
    Ama sayının kendisi metinde geçmek zorunda."""
    kabul, _ = elestirmen.dogrula("kar_payi_orani", "% 1,89", METIN)
    assert kabul is True


@pytest.mark.parametrize(
    ("alan", "ifade"),
    [
        ("vade_ay_max", "120"),
        ("finansman_tutari_max", "5.000.000 TL"),
        ("tahsis_ucreti", "500 TL"),
        ("kampanya_bitis", "30.09.2026"),
    ],
)
def test_gercek_degerler_kabul_edilir(elestirmen, alan, ifade):
    """Karşı kontrol: kalkanın sıkı olması, doğru olanı reddetmesi demek değil.
    Yalnız 'reddediyor mu' diye bakmak yetmez (bkz. SPRINT0_RAPORU 5.3)."""
    kabul, _ = elestirmen.dogrula(alan, ifade, METIN)
    assert kabul is True


# ---------------------------------------------------------------------------
# Ret — sistemin en özgün davranışı
# ---------------------------------------------------------------------------


def test_uydurma_oran_reddedilir(elestirmen):
    kabul, konum = elestirmen.dogrula("kar_payi_orani", "%2,45", METIN)
    assert kabul is False
    assert konum is None
    assert any("2,45" in r for r in elestirmen.reddedilen)


def test_uydurma_tutar_reddedilir(elestirmen):
    assert elestirmen.dogrula("finansman_tutari_max", "9.999.999 TL", METIN)[0] is False


def test_ret_kaydi_hata_analizi_icin_tutulur(elestirmen):
    elestirmen.dogrula("kar_payi_orani", "%2,45", METIN)
    elestirmen.dogrula("odul_miktari", "750 TL", METIN)
    assert len(elestirmen.reddedilen) == 2


# ---------------------------------------------------------------------------
# Kanıt zorunlu OLMAYAN alanlar
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("alan", ["kampanya_turu", "hedef_kitle", "kampanya_avantaji"])
def test_siniflandirma_ve_ozet_alanlari_metinde_aranmaz(elestirmen, alan):
    """Enum etiketi metinde geçmez ('konut_finansmani'), özet ise modelin
    yeniden ifade etmesi meşrudur. Bunları reddetmek kendi metriğimizi
    hatalı biçimde kötü gösterirdi (bkz. SPRINT0_RAPORU 5.4)."""
    assert alan not in KANIT_ZORUNLU_ALANLAR
    kabul, _ = elestirmen.dogrula(alan, "konut_finansmani", METIN)
    assert kabul is True


# ---------------------------------------------------------------------------
# Ablasyon — "ajan var, eleştirmen yok" satırının dayanağı
# ---------------------------------------------------------------------------


def test_ablasyonda_uydurma_deger_gecer():
    """Eleştirmen kapatılınca uydurma değer sisteme girer. Ablasyon
    tablosundaki halüsinasyon farkı tam olarak bu davranıştan doğuyor."""
    kapali = ElestirmenAjani(etkin=False)
    assert kapali.dogrula("kar_payi_orani", "%2,45", METIN)[0] is True
    assert kapali.reddedilen == []


def test_ablasyon_izi_durumu_acikca_soyler():
    kapali = ElestirmenAjani(etkin=False)
    _, iz = kapali.calistir({"metin": METIN, "alanlar": {"kar_payi_orani": "%2,45"}})
    assert "ABLASYON" in iz.karar_gerekcesi


# ---------------------------------------------------------------------------
# İz kaydı — jüriye gösterilen kanıt
# ---------------------------------------------------------------------------


def test_iz_llm_kullanilmadigini_bildirir(elestirmen):
    """Sistemin en kırılgan iddiası 'doğrulamayı LLM'e sormuyoruz'. İz bunu
    ekranda ispatlıyor."""
    _, iz = elestirmen.calistir({"metin": METIN, "alanlar": {"kar_payi_orani": "%1,89"}})
    assert iz.llm_kullanildi is False
    assert elestirmen.llm_kullanir is False
    assert "kod" in iz.satir()


def test_toplu_calistirma_yalniz_dogrulananlari_dondurur(elestirmen):
    kabul, iz = elestirmen.calistir(
        {
            "metin": METIN,
            "alanlar": {"kar_payi_orani": "%1,89", "odul_miktari": "750 TL"},
        }
    )
    assert set(kabul) == {"kar_payi_orani"}
    assert "1 alan reddedildi" in iz.karar_gerekcesi


# ---------------------------------------------------------------------------
# Alıntı
# ---------------------------------------------------------------------------


def test_alinti_degeri_baglamiyla_birlikte_verir(elestirmen):
    """Jüri 'bu sayı nereden geldi?' diye sorduğunda cevap ekranda olmalı."""
    _, konum = elestirmen.dogrula("kar_payi_orani", "%1,89", METIN)
    alinti = elestirmen.alinti(METIN, *konum)
    assert "%1,89" in alinti
    assert "kâr payı" in alinti  # yalnız sayı değil, geçtiği cümle
    assert alinti in METIN


# ---------------------------------------------------------------------------
# Boşluk toleransı — gevşetmenin karşı kontrolü
# ---------------------------------------------------------------------------
#
# 14 Ağustos'ta konum_bul'a "boşluktan bağımsız arama" eklendi (şartname 5.6:
# '%2,05' / '% 2.05' aynı değerdir). Bir kısıtı gevşetirken yalnız "artık
# kabul ediyor mu" diye bakmak yetmez; "hâlâ reddediyor mu" da sorulmalı —
# aksi halde kalkanda sessiz bir delik açılır.


@pytest.mark.parametrize("ifade", ["% 1,89", "%1, 89", " %1,89 "])
def test_bosluk_varyantlari_kabul_edilir(elestirmen, ifade):
    assert elestirmen.dogrula("kar_payi_orani", ifade, METIN)[0] is True


@pytest.mark.parametrize("ifade", ["% 2,45", "%2, 45", "1,98", "%18,9"])
def test_bosluk_toleransi_uydurmaya_kapi_acmaz(elestirmen, ifade):
    """Boşluk atılıyor ama RAKAMLAR birebir eşleşmek zorunda. Metinde
    '%1,89' varken '%18,9' veya '1,98' kabul edilirse kalkan delinmiş olur."""
    assert elestirmen.dogrula("kar_payi_orani", ifade, METIN)[0] is False


def test_bosluksuz_eslesmede_konum_kesin(elestirmen):
    """Alıntı ham metinden kesiliyor; konum yaklaşık olursa kullanıcıya
    yanlış kanıt gösterilir."""
    _, konum = elestirmen.dogrula("kar_payi_orani", "% 1,89", METIN)
    assert METIN[konum[0] : konum[1]] == "%1,89"


def test_bosluklu_tutar_dogru_yerde_bulunur(elestirmen):
    metin = "Toplam 5.000.000 TL finansman sağlanır."
    _, konum = elestirmen.dogrula("finansman_tutari_max", "5.000.000TL", metin)
    assert metin[konum[0] : konum[1]] == "5.000.000 TL"
