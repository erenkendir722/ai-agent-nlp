"""`CIKARIM_KAYNAKLARI` sözleşmesi — bayatlık bayrağının doğruluğu (ADR 017).

Parmak izi iki yönde de yanılabilir ve iki yanılma da pahalıdır:

* **Dar kalırsa** — çıkarımı değiştiren bir dosya listede yoksa, veritabanı
  eskirken "taze" görünür ve jüriye bayat sayı gösterilir.
* **Geniş kalırsa** — çıkarıma etkisiz bir dosya listedeyse, veritabanı
  güncelken "BAYAT" denir; `make eval` jüriye giden `docs/SONUCLAR.md`'nin
  başına «bu sayıları sunuma kopyalamayın» yazar ve ekip teslim arifesinde
  gereksiz bir yeniden çıkarıma itilir.

26 Ağustos'ta ikincisi oldu: `src/ajanlar` klasörünün tamamı listedeydi, oysa
`muhakeme.py` ve `orkestrator.py` yalnız SORGU zamanında koşuyor.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.depolama import CIKARIM_KAYNAKLARI, kod_parmak_izi

KOK = Path(__file__).resolve().parents[1]

# Çıkarım hattında koşan ajanlar — `boru_hatti.py`'nin kat ettiği yol.
CIKARIM_ZAMANI_AJANLARI = ("elestirmen.py", "yuklem.py", "uygunluk.py")

# Yalnız kullanıcı soru sorduğunda koşanlar. Çıkarılan değerlere dokunmazlar.
SORGU_ZAMANI_AJANLARI = ("muhakeme.py", "orkestrator.py")


def _kapsanan_dosyalar() -> set[str]:
    """Parmak izinin fiilen özetlediği `.py` dosyaları (göreli yol)."""
    dosyalar: set[str] = set()
    for gosterge in CIKARIM_KAYNAKLARI:
        hedef = KOK / gosterge
        if hedef.is_dir():
            dosyalar |= {p.relative_to(KOK).as_posix() for p in hedef.rglob("*.py")}
        elif hedef.is_file():
            dosyalar.add(hedef.relative_to(KOK).as_posix())
    return dosyalar


@pytest.mark.parametrize("ajan", CIKARIM_ZAMANI_AJANLARI)
def test_cikarim_zamani_ajanlari_kapsamda(ajan: str):
    """Bunlar değerleri DEĞİŞTİRİR — listeden düşerlerse bayatlık körleşir."""
    assert f"src/ajanlar/{ajan}" in _kapsanan_dosyalar(), (
        f"{ajan} çıkarım hattında koşuyor ama parmak izi kapsamında değil. "
        "Değişikliği veritabanını eskitir ve kimse fark etmez."
    )


@pytest.mark.parametrize("ajan", SORGU_ZAMANI_AJANLARI)
def test_sorgu_zamani_ajanlari_kapsam_disi(ajan: str):
    """Bunlar çıkarım çıktısına dokunmaz — listede olurlarsa YANLIŞ ALARM üretir.

    Ölçüldü (26 Ağu): `orkestrator.py`'de chatbot cevap biçimi düzeltildi,
    parmak izi kaydı, `cikarim_durumu()` "BAYAT" dedi. Çıkarılan tek bir değer
    değişmemişti. Bkz. ADR 017.
    """
    assert f"src/ajanlar/{ajan}" not in _kapsanan_dosyalar(), (
        f"{ajan} yalnız sorgu zamanında koşuyor; parmak izine girerse "
        "chatbot'a yapılan her düzeltme veritabanını sahte bayat gösterir."
    )


def test_sema_ve_cikarim_katmani_kapsamda():
    """Şema sözleşmesi ve çıkarım katmanı her zaman kapsamda olmalı."""
    kapsanan = _kapsanan_dosyalar()
    assert "src/schema.py" in kapsanan
    assert "src/preprocessing/normalizasyon.py" in kapsanan
    assert any(d.startswith("src/extraction/") for d in kapsanan)
    for zorunlu in ("kural.py", "llm.py", "uzlastirici.py"):
        assert f"src/extraction/{zorunlu}" in kapsanan


def test_toplayici_ve_arayuz_kapsam_disi():
    """Ham metni değiştirmezler; listeye girerlerse yine yanlış alarm olur."""
    kapsanan = _kapsanan_dosyalar()
    assert not any(d.startswith("src/collector/") for d in kapsanan)
    assert not any(d.startswith("app/") for d in kapsanan)
    assert not any(d.startswith("eval/") for d in kapsanan)


def test_parmak_izi_kararli():
    """Aynı ağaç aynı izi verir — yoksa her koşuda sahte bayatlık çıkar."""
    assert kod_parmak_izi() == kod_parmak_izi()
    assert len(kod_parmak_izi()) == 16


def test_listedeki_her_girdi_var():
    """Silinmiş bir yol sessizce kapsam dışı kalır — iz zayıflar, kimse görmez."""
    for gosterge in CIKARIM_KAYNAKLARI:
        assert (KOK / gosterge).exists(), f"{gosterge} yok — liste güncellenmemiş"
