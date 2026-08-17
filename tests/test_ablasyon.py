"""Ablasyon tablosunun kendi kendini doldurmasını koruyan testler (S-13).

Tablo sunumun en güçlü slaydı ve sayıları ELLE kopyalanmıyor: her `make eval`
veritabanının koşu kaydından hangi yapılandırmayı ölçtüğünü okuyup kendi
satırını yazıyor. Buradaki testler o mekanizmanın üç sessiz hata biçimini
kapatır: yanlış satıra yazmak, önceki koşuları ezmek ve farklı kodla koşulmuş
satırları karşılaştırılabilir göstermek.
"""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from eval import calistir as ec


@pytest.fixture
def ablasyon_dosyasi(tmp_path, monkeypatch):
    """Gerçek `data/ablasyon.json`'a dokunma — koşu sonuçları kıymetli."""
    yol = tmp_path / "ablasyon.json"
    monkeypatch.setattr(ec, "ABLASYON_DOSYASI", yol)
    return yol


def _temel(kampanya_sayisi: int = 96, halusinasyon: float = 0.0) -> dict:
    return {
        "kampanya_sayisi": kampanya_sayisi,
        "alan_dolulugu": 0.073,
        "halusinasyon_orani": halusinasyon,
    }


def _altin(makro_f1: float = 0.628) -> dict:
    return {
        "makro_f1": makro_f1,
        "sayisal_dogruluk": 0.930,
        "alan_f1": {"kar_payi_orani": {"f1": 0.842}, "vade_ay_max": {"f1": 0.791}},
    }


def _kokenlik(yapilandirma: str, parmak_izi: str = "abc123") -> dict:
    return {
        "kosu": {
            "zaman": datetime(2026, 8, 17, 14, 30),
            "yapilandirma": yapilandirma,
            "kayit_sayisi": 96,
            "kod_parmak_izi": parmak_izi,
        },
        "bayat": False,
        "sebep": "",
    }


def test_kosu_kendi_satirina_yazilir(ablasyon_dosyasi) -> None:
    ec.ablasyon_kaydet(_temel(), _altin(), _kokenlik("kural"))

    kayit = json.loads(ablasyon_dosyasi.read_text(encoding="utf-8"))
    assert set(kayit) == {"kural"}
    assert kayit["kural"]["makro_f1"] == 0.628
    assert kayit["kural"]["alan_f1"]["kar_payi_orani"] == 0.842


def test_ikinci_kosu_oncekini_ezmez(ablasyon_dosyasi) -> None:
    """Üç koşu sırayla yapılır; ikincisi birincisinin satırını silmemeli."""
    ec.ablasyon_kaydet(_temel(), _altin(0.628), _kokenlik("kural"))
    ec.ablasyon_kaydet(_temel(), _altin(0.755), _kokenlik("llm"))

    kayit = json.loads(ablasyon_dosyasi.read_text(encoding="utf-8"))
    assert set(kayit) == {"kural", "llm"}
    assert kayit["kural"]["makro_f1"] == 0.628
    assert kayit["llm"]["makro_f1"] == 0.755


def test_kosu_kaydi_yoksa_yazilmaz(ablasyon_dosyasi) -> None:
    """Hangi yapılandırma olduğu bilinmiyorsa tahmin ETME — sessiz yanlış satır
    üretmek, satırı boş bırakmaktan kötüdür."""
    ec.ablasyon_kaydet(_temel(), _altin(), {"kosu": None, "bayat": True, "sebep": "yok"})

    assert not ablasyon_dosyasi.exists()


def test_eksik_yapilandirma_soru_isaretiyle_gosterilir(ablasyon_dosyasi) -> None:
    ec.ablasyon_kaydet(_temel(), _altin(), _kokenlik("kural"))

    not_ = ec._ablasyon_notu()
    assert "Henüz koşulmayan yapılandırma" in not_
    assert "Yalnız LLM (şema kısıtlı)" in not_
    assert "**Hibrit (bizim)**" in not_


def test_farkli_kodla_kosulan_satirlar_karsilastirilamaz_isaretlenir(
    ablasyon_dosyasi,
) -> None:
    """Üç satır aynı koddan gelmiyorsa tablo yanıltıcıdır; rapor bunu söylemeli."""
    ec.ablasyon_kaydet(_temel(), _altin(), _kokenlik("kural", "eski111"))
    ec.ablasyon_kaydet(_temel(), _altin(), _kokenlik("llm", "yeni222"))
    ec.ablasyon_kaydet(_temel(), _altin(), _kokenlik("hibrit", "yeni222"))

    not_ = ec._ablasyon_notu()
    assert "KARŞILAŞTIRILAMAZ" in not_
    assert "eski111" in not_


def test_farkli_korpus_buyuklugu_karsilastirilamaz_isaretlenir(
    ablasyon_dosyasi,
) -> None:
    """96 kayıtta koşan satırla 300 kayıtta koşan satır yan yana konmaz."""
    ec.ablasyon_kaydet(_temel(96), _altin(), _kokenlik("kural"))
    ec.ablasyon_kaydet(_temel(96), _altin(), _kokenlik("llm"))
    ec.ablasyon_kaydet(_temel(300), _altin(), _kokenlik("hibrit"))

    not_ = ec._ablasyon_notu()
    assert "KARŞILAŞTIRILAMAZ" in not_
    assert "96" in not_ and "300" in not_


def test_tam_tablo_uyari_vermez(ablasyon_dosyasi) -> None:
    for yapilandirma in ("kural", "llm", "hibrit"):
        ec.ablasyon_kaydet(_temel(), _altin(), _kokenlik(yapilandirma))

    not_ = ec._ablasyon_notu()
    assert "Henüz koşulmayan" not in not_
    assert "KARŞILAŞTIRILAMAZ" not in not_
    assert "0.842" in not_  # kâr payı F1 tabloya gerçekten girmiş
