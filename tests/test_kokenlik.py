"""Çıkarım kökeni ve bayatlık tespiti.

NEDEN BU TESTLER VAR — 15 Ağustos'ta yaşanan hata:
    Veritabanı 17:49'da yazıldı, çıkarım düzeltmeleri 18:05'te commit edildi.
    `docs/SONUCLAR.md` güncel göründü ama düzeltmeleri içermeyen sayıları
    taşıyordu. Hatayı yakalayan şey, dosya tarihlerine elle bakmak oldu.

    Buradaki testler o denetimi otomatikleştirir: kod değiştiyse rapor
    bayat olduğunu KENDİSİ söylemeli. Sunuma yanlış rakam gitmesini
    engelleyen son savunma hattı budur.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.depolama import (
    CIKARIM_KAYNAKLARI,
    cikarim_durumu,
    cikarim_kosusu_yaz,
    kod_parmak_izi,
    son_cikarim_kosusu,
)


@pytest.fixture
def gecici_vt(tmp_path) -> str:
    """Boş, izole bir veritabanı URL'i."""
    return f"sqlite:///{tmp_path / 'test.db'}"


# ---------------------------------------------------------------------------
# Kod parmak izi
# ---------------------------------------------------------------------------


def test_parmak_izi_ayni_kodda_ayni():
    assert kod_parmak_izi() == kod_parmak_izi()


def test_parmak_izi_kaynak_degisince_degisir(tmp_path):
    """Çıkarım kodu değiştiğinde iz DEĞİŞMELİ — tespitin tamamı buna dayanıyor."""
    (tmp_path / "src" / "extraction").mkdir(parents=True)
    (tmp_path / "src" / "schema.py").write_text("a = 1", encoding="utf-8")
    (tmp_path / "src" / "extraction" / "kural.py").write_text("b = 1", encoding="utf-8")

    onceki = kod_parmak_izi(tmp_path)
    (tmp_path / "src" / "extraction" / "kural.py").write_text("b = 2", encoding="utf-8")

    assert kod_parmak_izi(tmp_path) != onceki


def test_parmak_izi_ilgisiz_dosyadan_etkilenmez(tmp_path):
    """Arayüz ya da toplayıcı değişikliği çıkarılan değerleri değiştirmez."""
    (tmp_path / "src" / "extraction").mkdir(parents=True)
    (tmp_path / "src" / "schema.py").write_text("a = 1", encoding="utf-8")
    (tmp_path / "app").mkdir()

    onceki = kod_parmak_izi(tmp_path)
    (tmp_path / "app" / "Genel_Bakis.py").write_text("import streamlit", encoding="utf-8")

    assert kod_parmak_izi(tmp_path) == onceki


def test_parmak_izi_izlenen_kaynaklari_kapsar():
    """Liste daralırsa bayatlık tespiti sessizce körleşir — sözleşme testi."""
    assert "src/schema.py" in CIKARIM_KAYNAKLARI
    assert "src/extraction" in CIKARIM_KAYNAKLARI
    assert "src/preprocessing/normalizasyon.py" in CIKARIM_KAYNAKLARI


# ---------------------------------------------------------------------------
# Koşu kaydı
# ---------------------------------------------------------------------------


def test_kosu_kaydedilmemisse_none(gecici_vt):
    assert son_cikarim_kosusu(gecici_vt) is None


def test_kosu_yazilir_ve_okunur(gecici_vt):
    cikarim_kosusu_yaz("hibrit", 96, url=gecici_vt)
    kosu = son_cikarim_kosusu(gecici_vt)

    assert kosu["yapilandirma"] == "hibrit"
    assert kosu["kayit_sayisi"] == 96
    assert kosu["kod_parmak_izi"] == kod_parmak_izi()
    assert isinstance(kosu["zaman"], datetime)


def test_en_son_kosu_doner(gecici_vt):
    """Ablasyon üç koşu yazar; rapor SONUNCUSUNU anlatmalı."""
    cikarim_kosusu_yaz("kural", 96, url=gecici_vt)
    cikarim_kosusu_yaz("llm", 96, url=gecici_vt)
    cikarim_kosusu_yaz("hibrit", 96, url=gecici_vt)

    assert son_cikarim_kosusu(gecici_vt)["yapilandirma"] == "hibrit"


# ---------------------------------------------------------------------------
# Bayatlık kararı
# ---------------------------------------------------------------------------


def test_kayit_yoksa_bayat_sayilir(gecici_vt):
    """Bilmemek, güncel varsaymak için gerekçe değildir."""
    durum = cikarim_durumu(gecici_vt)

    assert durum["bayat"] is True
    assert durum["kosu"] is None
    assert "kaydı yok" in durum["sebep"]


def test_guncel_kodla_kosulmussa_bayat_degil(gecici_vt):
    cikarim_kosusu_yaz("hibrit", 96, url=gecici_vt)
    durum = cikarim_durumu(gecici_vt)

    assert durum["bayat"] is False
    assert durum["sebep"] == ""


def test_kod_degisince_bayat_olur(gecici_vt, monkeypatch):
    """15 Ağustos senaryosunun ta kendisi: koşudan sonra kod değişiyor."""
    cikarim_kosusu_yaz("hibrit", 96, url=gecici_vt)

    from src import depolama

    monkeypatch.setattr(depolama, "kod_parmak_izi", lambda *a, **k: "baskabirizdir")
    durum = cikarim_durumu(gecici_vt)

    assert durum["bayat"] is True
    assert "değişti" in durum["sebep"]
    assert durum["kosu"]["yapilandirma"] == "hibrit"


# ---------------------------------------------------------------------------
# Motor önbelleği — url parametresi gerçekten çalışmalı
# ---------------------------------------------------------------------------


def test_farkli_url_farkli_veritabani(tmp_path):
    """Tek global motor olsaydı ikinci URL yok sayılır, testler üretim
    veritabanına yazardı."""
    bir = f"sqlite:///{tmp_path / 'bir.db'}"
    iki = f"sqlite:///{tmp_path / 'iki.db'}"

    cikarim_kosusu_yaz("kural", 10, url=bir)

    assert son_cikarim_kosusu(bir)["yapilandirma"] == "kural"
    assert son_cikarim_kosusu(iki) is None
