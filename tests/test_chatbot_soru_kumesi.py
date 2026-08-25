"""Chatbot test kümesinin bütünlüğü (S-10) — AĞ İSTEMEZ.

Kümenin kendisini koşmak ağ ister (`make chatbot-test`); burada yalnız
kümenin SÖZLEŞMESİ denetleniyor. Amaç, bozuk bir soru dosyasının ölçümü
sessizce anlamsızlaştırmasını engellemek.
"""

from __future__ import annotations

import pytest
import yaml

from eval.chatbot_testi import DOGRULUK_HEDEFI, KAYNAK_HEDEFI, SORU_DOSYASI, sorulari_yukle
from src.rag.chatbot import Niyet

GECERLI_NIYETLER = {n.value for n in Niyet}


@pytest.fixture(scope="module")
def sorular():
    return sorulari_yukle()


def test_en_az_otuz_soru(sorular):
    """Görev tanımı 30 soru istiyor."""
    assert len(sorular) >= 30


def test_sorular_benzersiz(sorular):
    metinler = [s["soru"] for s in sorular]
    assert len(metinler) == len(set(metinler))


def test_niyetler_gecerli(sorular):
    for s in sorular:
        niyet = s.get("niyet")
        kabul = [niyet] if isinstance(niyet, str) else niyet
        assert kabul, f"niyet eksik: {s['soru']!r}"
        for n in kabul:
            assert n in GECERLI_NIYETLER, f"bilinmeyen niyet {n!r}: {s['soru']!r}"


def test_yinelenen_anahtar_yok():
    """YAML'da aynı anahtar iki kez yazılırsa ikincisi birincisini SESSİZCE ezer.

    25 Ağustos'ta tam olarak bu oldu: bir kayıtta iki `not:` vardı ve ilk
    açıklama kayboldu. Ölçüm bozulmaz ama gerekçe kaybolur.
    """

    class YinelemeyeDuyarli(yaml.SafeLoader):
        pass

    def _esle(yukleyici, dugum, deep=False):
        gorulen = set()
        for anahtar_dugum, _ in dugum.value:
            anahtar = yukleyici.construct_object(anahtar_dugum, deep=deep)
            assert anahtar not in gorulen, f"YAML'da yinelenen anahtar: {anahtar!r}"
            gorulen.add(anahtar)
        return yaml.SafeLoader.construct_mapping(yukleyici, dugum, deep)

    YinelemeyeDuyarli.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _esle
    )
    yaml.load(SORU_DOSYASI.read_text(encoding="utf-8"), Loader=YinelemeyeDuyarli)


def test_sartname_senaryolari_kumede(sorular):
    """Şartnamenin iki örnek senaryosu kümede olmak ZORUNDA.

    Jüri demosunda ilk sorulacaklar bunlar; kümeden düşerlerse ölçüm
    onları korumaz.
    """
    senaryolar = {s.get("sartname_senaryosu") for s in sorular}
    assert 1 in senaryolar, "Şartname Senaryo 1 (tek banka sorgusu) kümede yok"
    assert 2 in senaryolar, "Şartname Senaryo 2 (iki banka karşılaştırma) kümede yok"


def test_kapsam_disi_sorular_var(sorular):
    """Sistem «bilmiyorum» diyebilmeli — ölçülmeyen yetenek yoktur."""
    kapsam_disi = [s for s in sorular if s.get("niyet") == "kapsam_disi"]
    assert len(kapsam_disi) >= 3


def test_kapsam_disi_sorularda_kaynak_beklenmiyor(sorular):
    """Kapsam dışı bir cevap kaynakça gösteriyorsa, veri iddiası üretmiş demektir."""
    for s in sorular:
        if s.get("niyet") == "kapsam_disi":
            assert s.get("kaynak") is False, (
                f"{s['soru']!r}: kapsam dışı soruda kaynak beklenmemeli"
            )


def test_hedefler_gorev_tanimiyla_uyumlu():
    """GOREVLER.md S-10: doğruluk ≥ 0,88 · kaynak gösterme oranı 1,00."""
    assert DOGRULUK_HEDEFI == 0.88
    assert KAYNAK_HEDEFI == 1.00
