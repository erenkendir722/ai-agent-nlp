"""Ablasyon tablosunun SAVUNMA KATMANI (S-13 · ADR 011).

Tablo sunumun en güçlü slaydı ve sayıları elle kopyalanmıyor.

TARİHÇE — bu testler bir kere yön değiştirdi:
    İlk sürümde tabloyu `make eval` yazıyordu: her koşu, veritabanının koşu
    kaydından hangi yapılandırmayı ölçtüğünü okuyup KENDİ SATIRINI ekliyordu.
    Bu mekanizma, satırların farklı zamanlarda ve farklı kodlarla birikmesine
    izin veriyordu — 18 Ağustos'ta tablo iki ayrı kod parmak izi taşır hâle
    geldi ve karşılaştırma geçersizleşti.

    Artık tabloyu YALNIZ `eval/ablasyon.py` yazar (tek süreç, tek parmak izi,
    atomik yazım — bkz. ADR 011 ve `tests/test_ablasyon_butunlugu.py`).

Buradaki testler yazıcıyı değil, **okuyucunun savunma katmanını** korur:
`_ablasyon_notu`, bozuk bir tabloyla karşılaşırsa SUSMAMALI. Koşucu garanti
veriyor diye bu uyarıları kaldırmak, garantinin bozulduğu günü sessiz kılardı.
"""

from __future__ import annotations

import json

import pytest

from eval import calistir as ec


@pytest.fixture
def ablasyon_dosyasi(tmp_path, monkeypatch):
    """Gerçek `data/ablasyon.json`'a dokunma — koşu sonuçları kıymetli."""
    yol = tmp_path / "ablasyon.json"
    monkeypatch.setattr(ec, "ABLASYON_DOSYASI", yol)
    return yol


def _satir(
    *,
    parmak_izi: str = "abc123",
    kampanya_sayisi: int = 96,
    makro_f1: float = 0.628,
) -> dict:
    """`eval/ablasyon.py`'nin yazdığı satır biçimi."""
    return {
        "zaman": "2026-08-19T14:30:00",
        "kod_parmak_izi": parmak_izi,
        "kampanya_sayisi": kampanya_sayisi,
        "alan_dolulugu": 0.073,
        "halusinasyon_orani": 0.0,
        "makro_f1": makro_f1,
        "sayisal_dogruluk": 0.930,
        "alan_f1": {"kar_payi_orani": 0.842, "vade_ay_max": 0.791},
    }


def _tablo_yaz(yol, **satirlar) -> None:
    yol.write_text(json.dumps(satirlar, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Tek yazıcı ilkesi
# ---------------------------------------------------------------------------


def test_eval_ablasyon_tablosunu_yazmaz() -> None:
    """`make eval` artık tabloya DOKUNMAZ — satır birikmesi böyle önlendi.

    Bu, 18 Ağustos'ta iki farklı kod parmak izinin aynı tabloda buluşmasının
    kök nedeniydi: her eval kendi satırını ekliyor, satırlar zamanla ayrışıyordu.
    """
    assert not hasattr(ec, "ablasyon_kaydet"), (
        "artımlı yazıcı geri gelmiş — tablo yalnız eval/ablasyon.py tarafından "
        "yazılmalı (ADR 011)"
    )


# ---------------------------------------------------------------------------
# Savunma katmanı — bozuk tabloya susma
# ---------------------------------------------------------------------------


def test_eksik_yapilandirma_soru_isaretiyle_gosterilir(ablasyon_dosyasi) -> None:
    _tablo_yaz(ablasyon_dosyasi, kural=_satir())
    metin = ec._ablasyon_notu()
    assert "?" in metin
    assert "Henüz koşulmayan" in metin


def test_farkli_kodla_kosulan_satirlar_karsilastirilamaz_isaretlenir(
    ablasyon_dosyasi,
) -> None:
    """REGRESYON — 18 Ağustos'un tam senaryosu."""
    _tablo_yaz(
        ablasyon_dosyasi,
        kural=_satir(parmak_izi="f797dd3f69630cfc"),
        llm=_satir(parmak_izi="f797dd3f69630cfc"),
        hibrit=_satir(parmak_izi="f835ccc2f7e8d116"),
        hibrit_elestirmensiz=_satir(parmak_izi="f797dd3f69630cfc"),
        tam=_satir(parmak_izi="f797dd3f69630cfc"),
    )
    metin = ec._ablasyon_notu()
    assert "KARŞILAŞTIRILAMAZ" in metin
    assert "f797dd3f69630cfc" in metin and "f835ccc2f7e8d116" in metin


def test_farkli_korpus_buyuklugu_karsilastirilamaz_isaretlenir(
    ablasyon_dosyasi,
) -> None:
    _tablo_yaz(
        ablasyon_dosyasi,
        kural=_satir(kampanya_sayisi=96),
        llm=_satir(kampanya_sayisi=96),
        hibrit=_satir(kampanya_sayisi=300),
        hibrit_elestirmensiz=_satir(kampanya_sayisi=96),
        tam=_satir(kampanya_sayisi=96),
    )
    metin = ec._ablasyon_notu()
    assert "KARŞILAŞTIRILAMAZ" in metin
    assert "96" in metin and "300" in metin


def test_tam_ve_tutarli_tablo_uyari_vermez(ablasyon_dosyasi) -> None:
    """Koşucunun ürettiği tablo temiz olmalı — uyarı çıkıyorsa arıza var."""
    _tablo_yaz(
        ablasyon_dosyasi,
        kural=_satir(makro_f1=0.628),
        llm=_satir(makro_f1=0.176),
        hibrit=_satir(makro_f1=0.778),
        hibrit_elestirmensiz=_satir(makro_f1=0.760),
        tam=_satir(makro_f1=0.828),
    )
    metin = ec._ablasyon_notu()
    assert "KARŞILAŞTIRILAMAZ" not in metin
    assert "Henüz koşulmayan" not in metin
    assert "0.778" in metin


def test_bozuk_json_cokme_uretmez(ablasyon_dosyasi) -> None:
    ablasyon_dosyasi.write_text("{bozuk", encoding="utf-8")
    metin = ec._ablasyon_notu()
    assert "Henüz koşulmayan" in metin


def test_tablo_yoksa_beklemede_gosterilir(ablasyon_dosyasi) -> None:
    metin = ec._ablasyon_notu()
    assert "Henüz koşulmayan" in metin
    for ad, _ in ec.ABLASYON_SIRASI:
        assert ad in metin or ad.capitalize() in metin or "Hibrit" in metin
