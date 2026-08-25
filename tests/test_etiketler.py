"""Gösterim etiketleri — tek doğruluk kaynağı ve Türkçe doğruluğu.

NEDEN VAR (25 Ağustos):
    Kullanıcıya gösterilen alan ve tür adları üç ayrı yerde, üç ayrı kez,
    elle "güzelleştiriliyordu":

        alan_adi.replace("_", " ").title().replace("Ucreti", "Ücreti")
        t.replace("_", " ").title().replace("Ihtiyac", "İhtiyaç")

    Sebep, Python'un `str.title()` metodunun Türkçe için yanlış olması.
    Yamalarla düzeltilmeye çalışıldı ama ölçüldüğünde dokuz kampanya türünün
    DOKUZU da hâlâ yanlış çıkıyordu — yamalananlar dahil:

        "ihtiyac_finansmani" -> "İhtiyaç Finansmani"   (sondaki ı düşmüş)
        "yeni_musteri"       -> "Yeni Musteri"          (hiç yamalanmamış)
        "diger"              -> "Diger"                 (hiç yamalanmamış)

    Yama listesinin ikinci sorunu: yeni bir alan ya da tür eklendiğinde
    sessizce eksik kalır. Kimse fark etmez, jüri ekranda görür.

Bu testler iki şeyi birden korur: etiketlerin DOĞRU olduğunu ve tek yerden
geldiğini.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.schema import (
    ALAN_ETIKETLERI,
    KAMPANYA_TURU_ETIKETLERI,
    KampanyaTuru,
    alan_etiketi,
    tur_etiketi,
)

KOK = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Kapsama — hiçbir tür ya da alan etiketsiz kalmaz
# ---------------------------------------------------------------------------


def test_her_kampanya_turunun_etiketi_var():
    """Yeni bir tür eklendiğinde bu test kırılır — sessiz eksik kalmaz."""
    eksik = [t.value for t in KampanyaTuru if t not in KAMPANYA_TURU_ETIKETLERI]
    assert not eksik, f"Etiketi olmayan kampanya türü: {eksik}"


def test_sayisal_alanlarin_hepsinin_etiketi_var():
    from src.schema import SAYISAL_ALANLAR

    eksik = [a for a in SAYISAL_ALANLAR if a not in ALAN_ETIKETLERI]
    assert not eksik, f"Etiketi olmayan sayısal alan: {eksik}"


# ---------------------------------------------------------------------------
# Türkçe doğruluğu — `.title()`'ın bozduğu tam olarak buydu
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ham", "beklenen"),
    [
        ("ihtiyac_finansmani", "İhtiyaç Finansmanı Kampanyası"),
        ("tasit_finansmani", "Taşıt Finansmanı Kampanyası"),
        ("yeni_musteri", "Yeni Müşteri Kampanyası"),
        ("alisveris_puani", "Alışveriş Puanı Kampanyası"),
        ("yatirim_urunu", "Yatırım Ürünü Kampanyası"),
        ("diger", "Diğer"),
    ],
)
def test_tur_etiketi_turkce_dogru(ham, beklenen):
    assert tur_etiketi(ham) == beklenen


def test_etiketler_title_ile_uretilemez():
    """İddianın kendisi: bu dönüşüm türetilemez, sözlük şart.

    En az bir tür `.title()` yaklaşımından FARKLI olmalı — aksi hâlde sözlüğü
    savunmanın bir gerekçesi kalmazdı.
    """
    farkli = [
        t.value
        for t in KampanyaTuru
        if KAMPANYA_TURU_ETIKETLERI[t] != t.value.replace("_", " ").title()
    ]
    assert farkli, "Hiçbir etiket `.title()`'dan farklı değilse sözlük gereksizdir"


def test_bilinmeyen_tur_uydurulmaz():
    """Bilinmeyen değer ham hâliyle döner — uydurmak yerine göstermek."""
    assert tur_etiketi("olmayan_tur") == "olmayan_tur"
    assert tur_etiketi(None) == ""
    assert tur_etiketi("") == ""


def test_bilinmeyen_alan_uydurulmaz():
    assert alan_etiketi("olmayan_alan") == "olmayan_alan"


# ---------------------------------------------------------------------------
# Tek doğruluk kaynağı — elle güzelleştirme geri gelmesin
# ---------------------------------------------------------------------------


_TARANAN = (
    "src/comparison/karsilastirma.py",
    "src/rag/chatbot.py",
    "src/ajanlar/muhakeme.py",
)

_TITLE_DESENI = re.compile(r"\.replace\(\s*[\"']_[\"']\s*,\s*[\"'] [\"']\s*\)\s*\.title\(\)")


@pytest.mark.parametrize("yol", _TARANAN)
def test_elle_guzellestirme_geri_gelmesin(yol):
    """`x.replace("_", " ").title()` deseni yasak.

    Türkçe'de yanlış sonuç verir ve her kopyası ayrı ayrı bayatlar. Etiket
    gerekiyorsa `schema.alan_etiketi` / `schema.tur_etiketi` kullanılır.
    """
    metin = (KOK / yol).read_text(encoding="utf-8")
    bulgular = _TITLE_DESENI.findall(metin)
    assert not bulgular, (
        f"{yol} içinde elle etiket güzelleştirme var ({len(bulgular)} yer). "
        f"`schema.alan_etiketi` / `schema.tur_etiketi` kullanın — "
        f"`.title()` Türkçe'de sessizce bozar."
    )


def test_alan_etiketleri_tek_yerde_tanimli():
    """Etiket dizeleri şema dışında ikinci kez tanımlanmasın.

    İki kopya kaçınılmaz olarak ayrışır; 25 Ağustos'ta ayrıştı.
    """
    for yol in _TARANAN:
        metin = (KOK / yol).read_text(encoding="utf-8")
        assert "_ALAN_ETIKETLERI = {" not in metin, (
            f"{yol} kendi etiket sözlüğünü tutuyor — `schema.ALAN_ETIKETLERI` var."
        )
