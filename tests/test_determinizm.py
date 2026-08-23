"""Çıkarımın deterministik olduğunu koruyan testler (S-20).

NEDEN BU TESTLER VAR — 20 Ağustos'ta ölçülen hata:
    `temperature=0,1` ile aynı kod, aynı girdi ve aynı model iki koşu
    arasında 6/96 kayıtta farklı sınıflandırma üretti. Dördü altın sette,
    üçü doğrudan yanlışa döndü; tek başına bedeli −0,006 makro-F1 oldu —
    hedefe olan farktan büyük.

    Sıcaklık sessizce geri yükseltilirse hata da sessizce geri gelir:
    testler geçmeye devam eder, ölçüm sayıları oynamaya başlar ve
    ablasyon tablosunun üç satırı karşılaştırılamaz hâle gelir. Aradaki
    farkın ne kadarı yapılandırmadan, ne kadarı gürültüden geldiği
    ayırt edilemez.

    Buradaki testler o ayarı sözleşme hâline getirir.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.extraction.llm import SABIT_TOHUM, SICAKLIK, LLMCikarici


class SahteIstemci:
    """`ollama.Client` yerine geçer; çağrının seçeneklerini yakalar."""

    def __init__(self) -> None:
        self.cagrilar: list[dict[str, Any]] = []

    def chat(self, **kwargs: Any) -> dict[str, Any]:
        self.cagrilar.append(kwargs)
        return {"message": {"content": "{}"}}


@pytest.fixture
def cikarici_ve_istemci() -> tuple[LLMCikarici, SahteIstemci]:
    cikarici = LLMCikarici()
    istemci = SahteIstemci()
    cikarici.istemci = istemci  # type: ignore[assignment]
    return cikarici, istemci


# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------


def test_sicaklik_sifir():
    """Sıfır sıcaklık üretimi açgözlü yapar — determinizmin asıl kaynağı."""
    assert SICAKLIK == 0.0


def test_tohum_sabit_ve_tamsayi():
    """Değeri anlamlı değil, SABİT olması anlamlı."""
    assert isinstance(SABIT_TOHUM, int)


# ---------------------------------------------------------------------------
# Çağrıya gerçekten geçiyor mu
# ---------------------------------------------------------------------------


def test_cagriya_sicaklik_ve_tohum_geciyor(cikarici_ve_istemci):
    """Sabitleri tanımlayıp çağrıya geçirmemek sessiz bir gerilemedir."""
    cikarici, istemci = cikarici_ve_istemci
    cikarici.ham_cikar("Kâr payı oranı %2,05")

    secenekler = istemci.cagrilar[0]["options"]
    assert secenekler["temperature"] == 0.0
    assert secenekler["seed"] == SABIT_TOHUM


def test_ayni_girdi_ayni_secenekleri_uretiyor(cikarici_ve_istemci):
    """İki çağrı arasında örnekleme ayarları oynamamalı."""
    cikarici, istemci = cikarici_ve_istemci
    cikarici.ham_cikar("Kâr payı oranı %2,05")
    cikarici.ham_cikar("Kâr payı oranı %2,05")

    ilk, ikinci = istemci.cagrilar
    assert ilk["options"] == ikinci["options"]
    assert ilk["messages"] == ikinci["messages"]


def test_dusunme_kapali_kaliyor(cikarici_ve_istemci):
    """`think=False` kaldırılırsa üretim bütçesi akıl yürütmeye gider ve
    çıktı boş döner — determinizmden önce çıkarımın kendisi bozulur."""
    cikarici, istemci = cikarici_ve_istemci
    cikarici.ham_cikar("Kâr payı oranı %2,05")

    assert istemci.cagrilar[0]["think"] is False
