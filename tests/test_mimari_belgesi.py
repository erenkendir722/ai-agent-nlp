"""`docs/MIMARI.md` ajan tablosu ile kodun ayrışmasını engelleyen sözleşme.

26 Ağustos'ta mentör geri bildirimi üzerine mimari şema hazırlanırken belgenin
koddan ayrılmış olduğu görüldü: metin *«beş ajan var ve DÖRDÜ dil modeli
kullanmaz»* diyor, hemen altındaki tablo ise **beş ajanın beşine birden** «LLM ✗»
koymuştu. Oysa `YuklemAjani.llm_kullanir = True`.

Bu, jüriye gösterilecek belgede en pahalı hata türü: sistemin kendi hakkında
söylediği şey kodun yaptığından farklı. Mimari şemanın ikna ediciliği tam da
bu tür sessiz kaymalara dayanmadığını gösterebilmekten gelir.

Test, tabloyu ve mermaid şemasını kodun `llm_kullanir` bayrağına bağlar.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

MIMARI = Path(__file__).resolve().parents[1] / "docs" / "MIMARI.md"

# Belgedeki dosya adı -> ajan sınıfının yaşadığı modül
AJAN_MODULLERI = {
    "uygunluk.py": "src.ajanlar.uygunluk",
    "elestirmen.py": "src.ajanlar.elestirmen",
    "yuklem.py": "src.ajanlar.yuklem",
    "muhakeme.py": "src.ajanlar.muhakeme",
    "orkestrator.py": "src.ajanlar.orkestrator",
}

# Tablo satırı:  | **Ad** | `dosya.py` | açıklama | ✓ |
TABLO_SATIRI = re.compile(
    r"^\|\s*\*\*(?P<ad>[^*]+)\*\*\s*\|\s*`(?P<dosya>\w+\.py)`\s*\|[^|]*\|\s*(?P<llm>[✓✗])\s*\|",
    re.MULTILINE,
)


def _belge() -> str:
    return MIMARI.read_text(encoding="utf-8")


def _koddaki_bayrak(modul_adi: str) -> bool:
    """Modüldeki ajan sınıfını bulur ve `llm_kullanir` bayrağını döndürür."""
    modul = importlib.import_module(modul_adi)
    adaylar = [
        nesne
        for nesne in vars(modul).values()
        if isinstance(nesne, type)
        and getattr(nesne, "__module__", None) == modul_adi
        and hasattr(nesne, "llm_kullanir")
        and hasattr(nesne, "ad")
    ]
    assert len(adaylar) == 1, f"{modul_adi}: tek ajan sınıfı bekleniyordu, {adaylar}"
    return bool(adaylar[0].llm_kullanir)


def test_tabloda_bes_ajan_var():
    satirlar = {m.group("dosya") for m in TABLO_SATIRI.finditer(_belge())}
    assert satirlar >= set(AJAN_MODULLERI), (
        f"MIMARI.md ajan tablosunda eksik dosya: {set(AJAN_MODULLERI) - satirlar}"
    )


@pytest.mark.parametrize("dosya,modul", sorted(AJAN_MODULLERI.items()))
def test_tablodaki_llm_isareti_kodla_ayni(dosya: str, modul: str):
    """`| ... | ✓ |` işareti sınıfın `llm_kullanir` bayrağıyla birebir olmalı."""
    belgede = {
        m.group("dosya"): m.group("llm") == "✓" for m in TABLO_SATIRI.finditer(_belge())
    }
    assert dosya in belgede, f"{dosya} MIMARI.md ajan tablosunda yok"
    assert belgede[dosya] == _koddaki_bayrak(modul), (
        f"{dosya}: MIMARI.md tablosu 'LLM {'✓' if belgede[dosya] else '✗'}' diyor, "
        f"kod tersini söylüyor. Belgeyi düzelt ya da ADR yaz."
    )


def test_metindeki_dordu_llmsiz_iddiasi_dogru():
    """«Beş ajan var ve dördü dil modeli kullanmaz» cümlesi sayılabilir olmalı."""
    llmsiz = sum(1 for m in AJAN_MODULLERI.values() if not _koddaki_bayrak(m))
    assert llmsiz == 4, f"kodda LLM'siz ajan sayısı {llmsiz}, belge 4 diyor"
    assert "dördü dil modeli kullanmaz" in _belge()


def test_orkestrasyon_semasi_var():
    """Mentör geri bildirimi (26 Ağu): jüriye gösterilecek hiyerarşi şeması."""
    belge = _belge()
    assert belge.count("```mermaid") >= 2, "orkestrasyon şeması eksik"
    assert "ORKESTRATÖR" in belge
    assert "ÇIKARIM ZAMANI" in belge and "SORGU ZAMANI" in belge


def test_semadaki_llm_etiketleri_kodla_tutuyor():
    """Şema düğümlerindeki `LLM ✓/✗` etiketi de koda bağlı."""
    belge = _belge()
    for etiket, modul in [
        ("ELEŞTİRMEN", "src.ajanlar.elestirmen"),
        ("YÜKLEM", "src.ajanlar.yuklem"),
        ("UYGUNLUK", "src.ajanlar.uygunluk"),
        ("MUHAKEME", "src.ajanlar.muhakeme"),
        ("ORKESTRATÖR", "src.ajanlar.orkestrator"),
    ]:
        blok = re.search(rf"{etiket}(.*?)\"\]", belge, re.DOTALL)
        assert blok, f"şemada {etiket} düğümü bulunamadı"
        beklenen = "LLM ✓" if _koddaki_bayrak(modul) else "LLM ✗"
        assert beklenen in blok.group(1), (
            f"şemadaki {etiket} düğümü '{beklenen}' demiyor"
        )


def test_katman_sifir_selenium_diyor():
    """Toplama yolu httpx değil Selenium — 26 Ağustos düzeltmesi."""
    belge = _belge()
    assert "trafilatura" not in belge or "Jenerik Toplayıcı<br/>httpx" not in belge
    assert "Selenium" in belge
