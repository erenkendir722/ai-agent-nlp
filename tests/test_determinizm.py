"""Çıkarımın deterministik olduğunu koruyan testler.

NEDEN BU TESTLER VAR — 20 Ağustos'ta ölçülen hata:
    `temperature=0,1` ile aynı kod, aynı girdi ve aynı model iki koşu
    arasında 6/96 kayıtta farklı sınıflandırma üretti. Dördü altın sette,
    üçü doğrudan yanlışa döndü; tek başına bedeli −0,006 makro-F1 oldu —
    hedefe olan farktan büyük.

    Sıcaklık sessizce geri yükseltilirse hata da sessizce geri gelir:
    testler geçmeye devam eder, ölçüm sayıları oynamaya başlar ve
    ablasyon tablosunun üç satırı karşılaştırılamaz hâle gelir.

    Buradaki testler o ayarı sözleşme hâline getirir.

⚠️  24 AĞUSTOS 2026 — KAPSAM DARALDI, İDDİA DEĞİŞTİ.
    Çıkarım EVREN'e taşındı. EVREN, `temperature=0` ve sabit tohuma rağmen
    BAYT DÜZEYİNDE DETERMİNİSTİK DEĞİL — ölçüldü: aynı girdi 5 kez
    gönderildiğinde 5 kayıttan 3'ü farklı çıktı verdi. Sebep örnekleme
    değil; ortak vLLM sunucusunda sürekli yığınlama, yığın bileşimine göre
    kayan nokta indirgeme sırasını değiştirir. Tohum bunu düzeltemez.

    Ama sapma ölçtüğümüz yerde DEĞİL: 8 kayıt × 4 koşuda oynayan alanların
    tamamı serbest metindi (`kampanya_kosullari` 4, `kampanya_avantaji` 1).
    Sayısal ve enum alanlarda sıfır sapma görüldü.

    Bu yüzden testler artık "çıktı aynı olacak" demiyor — bunu SÖYLEYEMEYİZ.
    Söyledikleri şu: **determinizmi isteyen parametreleri doğru gönderiyoruz.**
    Gönderilmediği an sapma serbest metinden sayısal alanlara taşar.

    Bayt düzeyinde tekrarlanabilirlik gerektiğinde: `LLM_SAGLAYICI=ollama`.
    `docs/SONUCLAR.md` sayıları zaten işlenmiş veritabanından üretilir
    (`data/katilim.db`, depoda), modelin o anki çıktısından değil.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from src.extraction.llm import SABIT_TOHUM, SICAKLIK, LLMCikarici
from src.extraction.saglayici import AZAMI_URETIM, EvrenSaglayici, OllamaSaglayici


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
# Yerel sağlayıcı (Ollama) — hava boşluğu demosunun ve yedek yolun sağlayıcısı
# ---------------------------------------------------------------------------


class SahteOllamaIstemcisi:
    """`ollama.Client` yerine geçer; çağrının seçeneklerini yakalar."""

    def __init__(self) -> None:
        self.cagrilar: list[dict[str, Any]] = []

    def chat(self, **kwargs: Any) -> dict[str, Any]:
        self.cagrilar.append(kwargs)
        return {"message": {"content": "{}"}}


@pytest.fixture
def ollama_cikarici() -> tuple[LLMCikarici, SahteOllamaIstemcisi]:
    saglayici = OllamaSaglayici.__new__(OllamaSaglayici)
    saglayici.model = "qwen3.5:4b-q4_K_M"
    istemci = SahteOllamaIstemcisi()
    saglayici.istemci = istemci  # type: ignore[attr-defined]
    return LLMCikarici(saglayici=saglayici), istemci


def test_ollama_cagrisina_sicaklik_ve_tohum_geciyor(ollama_cikarici):
    """Sabitleri tanımlayıp çağrıya geçirmemek sessiz bir gerilemedir."""
    cikarici, istemci = ollama_cikarici
    cikarici.ham_cikar("Kâr payı oranı %2,05")

    secenekler = istemci.cagrilar[0]["options"]
    assert secenekler["temperature"] == 0.0
    assert secenekler["seed"] == SABIT_TOHUM
    assert secenekler["num_predict"] == AZAMI_URETIM


def test_ollama_ayni_girdi_ayni_secenekleri_uretiyor(ollama_cikarici):
    """İki çağrı arasında örnekleme ayarları oynamamalı."""
    cikarici, istemci = ollama_cikarici
    cikarici.ham_cikar("Kâr payı oranı %2,05")
    cikarici.ham_cikar("Kâr payı oranı %2,05")

    ilk, ikinci = istemci.cagrilar
    assert ilk["options"] == ikinci["options"]
    assert ilk["messages"] == ikinci["messages"]


def test_ollama_dusunme_kapali_kaliyor(ollama_cikarici):
    """`think=False` kaldırılırsa üretim bütçesi akıl yürütmeye gider ve
    çıktı boş döner — determinizmden önce çıkarımın kendisi bozulur."""
    cikarici, istemci = ollama_cikarici
    cikarici.ham_cikar("Kâr payı oranı %2,05")

    assert istemci.cagrilar[0]["think"] is False


# ---------------------------------------------------------------------------
# EVREN sağlayıcısı — üç ayar da SESSİZ bozar, üçü de sözleşme
# ---------------------------------------------------------------------------


class SahteHttpxIstemcisi:
    """`httpx.Client` yerine geçer; gönderilen gövdeyi yakalar."""

    def __init__(self) -> None:
        self.govdeler: list[dict[str, Any]] = []

    def post(self, yol: str, json: dict[str, Any]) -> Any:  # noqa: A002
        self.govdeler.append(json)

        class Yanit:
            @staticmethod
            def raise_for_status() -> None: ...

            @staticmethod
            def json() -> dict[str, Any]:
                return {
                    "choices": [
                        {"finish_reason": "stop", "message": {"content": "{}"}}
                    ]
                }

        return Yanit()


@pytest.fixture
def evren_cikarici() -> tuple[LLMCikarici, SahteHttpxIstemcisi]:
    saglayici = EvrenSaglayici.__new__(EvrenSaglayici)
    saglayici.model = "llm-large"
    saglayici.temel_url = "https://evren-llmapi.ssyz.org.tr/v1"
    istemci = SahteHttpxIstemcisi()
    saglayici.istemci = istemci  # type: ignore[attr-defined]
    return LLMCikarici(saglayici=saglayici), istemci


def test_evren_cagrisina_sicaklik_ve_tohum_geciyor(evren_cikarici):
    cikarici, istemci = evren_cikarici
    cikarici.ham_cikar("Kâr payı oranı %2,05")

    govde = istemci.govdeler[0]
    assert govde["temperature"] == 0.0
    assert govde["seed"] == SABIT_TOHUM


def test_evren_dusunme_kapali_ve_UST_SEVIYEDE(evren_cikarici):
    """`chat_template_kwargs` `extra_body` içine konursa SESSİZCE düşer.

    ÖLÇÜLDÜ — ağ geçidi `extra_body`'yi açmıyor:
        extra_body içinde: finish=length, tok=1500, içerik="" (boş!)
        üst seviyede:      finish=stop,   tok=111,  içerik=geçerli JSON

    Yani hata almazsınız; çıkarım sessizce boş döner ve doluluk oranı düşer.
    """
    cikarici, istemci = evren_cikarici
    cikarici.ham_cikar("Kâr payı oranı %2,05")

    govde = istemci.govdeler[0]
    assert "extra_body" not in govde, "chat_template_kwargs extra_body'ye taşınmış — sessizce düşer"
    assert govde["chat_template_kwargs"]["enable_thinking"] is False


def test_evren_sema_kisiti_json_schema_ile_gonderiliyor(evren_cikarici):
    """`guided_json` DEĞİL — ağ geçidi onu yok sayıyor.

    ÖLÇÜLDÜ: şemaya modelin asla kendiliğinden seçmeyeceği bir enum
    (`ZZZ_YESIL`) konup istendi.
        guided_json                 -> düz metin döndü, şema uygulanmadı
        response_format.json_schema -> {"kampanya_turu": "ZZZ_YESIL"} ✅

    `guided_json`'a dönülürse çıktı geçerli JSON olmaya devam eder ama
    ŞEMANIN JSON'ı olmaz — "şema geçerliliği 1,00" iddiası sessizce çöker.
    """
    cikarici, istemci = evren_cikarici
    cikarici.ham_cikar("Kâr payı oranı %2,05")

    govde = istemci.govdeler[0]
    assert "guided_json" not in govde, "guided_json ağ geçidince yok sayılıyor"
    bicim = govde["response_format"]
    assert bicim["type"] == "json_schema"
    assert bicim["json_schema"]["strict"] is True
    assert "properties" in bicim["json_schema"]["schema"]


def test_evren_ayni_girdi_ayni_govdeyi_uretiyor(evren_cikarici):
    """İstek gövdesi koşudan koşuya oynamamalı.

    Bu, çıktının aynı olacağını GARANTİ ETMEZ (modül başlığındaki ölçüme
    bakın). Yalnız sapmanın bizim tarafımızdan gelmediğini garanti eder.
    """
    cikarici, istemci = evren_cikarici
    cikarici.ham_cikar("Kâr payı oranı %2,05")
    cikarici.ham_cikar("Kâr payı oranı %2,05")

    ilk, ikinci = istemci.govdeler
    assert json.dumps(ilk, sort_keys=True) == json.dumps(ikinci, sort_keys=True)
