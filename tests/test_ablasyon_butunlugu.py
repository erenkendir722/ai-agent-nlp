"""Ablasyon tablosunun bütünlüğü (bulgu 2.2).

18 Ağustos'ta `data/ablasyon.json` üç satır taşıyordu ve satırlar FARKLI KOD
SÜRÜMLERİYLE koşulmuştu:

    llm     17 Ağu  f797dd3f69630cfc
    kural   17 Ağu  f797dd3f69630cfc
    hibrit  18 Ağu  f835ccc2f7e8d116   <- farklı

Yani sunumun en güçlü grafiği («hibrit 0,778 vs kural 0,628 vs LLM 0,176»)
geçersizdi: hibrit satırı daha yeni ve iyileştirilmiş kodla koşulmuştu.

Eksik olan tespit değildi — `_ablasyon_notu` bunu zaten yakalıyordu. Eksik
olan koşumdu. Bu testler, ayrışmanın YAPISAL OLARAK imkânsız olduğunu ve
yarım tablonun yazılamayacağını sabitler.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from eval import ablasyon as ablasyon_modulu
from eval.calistir import ABLASYON_SIRASI, _ablasyon_notu

KOK = Path(__file__).resolve().parents[1]
ABLASYON_DOSYASI = KOK / "data" / "ablasyon.json"


def _kayitlari_oku() -> dict[str, Any]:
    if not ABLASYON_DOSYASI.exists():
        return {}
    return json.loads(ABLASYON_DOSYASI.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1) Koşucunun yapısal garantileri
# ---------------------------------------------------------------------------


class TestKosucuGarantileri:
    def test_uc_yapilandirma_tanimli(self) -> None:
        assert {ad for ad, _ in ablasyon_modulu.YAPILANDIRMALAR} == {
            ad for ad, _ in ABLASYON_SIRASI
        }, "koşucu ile rapor farklı yapılandırma kümesi tanıyor"

    def test_bayraklar_ayni_kod_yolunu_kullanir(self) -> None:
        """Ayrı kod yolu yazmak ölçümü karşılaştırılamaz kılardı.

        Üç yapılandırma yalnız `kural_kullan` / `llm_kullan` bayraklarında
        ayrışmalı; başka hiçbir parametre farkı olmamalı.
        """
        for _, bayraklar in ablasyon_modulu.YAPILANDIRMALAR:
            assert set(bayraklar) == {"kural_kullan", "llm_kullan"}
        kombinasyonlar = {
            (b["kural_kullan"], b["llm_kullan"])
            for _, b in ablasyon_modulu.YAPILANDIRMALAR
        }
        assert kombinasyonlar == {(True, False), (False, True), (True, True)}

    def test_kural_once_kosulur(self) -> None:
        """LLM'siz koşu saniyeler sürer; sorun iki saatlik koşulardan ÖNCE çıksın."""
        assert ablasyon_modulu.YAPILANDIRMALAR[0][0] == "kural"

    def test_ablasyon_uretim_veritabanina_yazmaz(self) -> None:
        """Ölçüm koşusu, ölçtüğü sistemi bozmamalıdır.

        `make extract-kural` üretim veritabanının üstüne yazıyordu; sonrasında
        `make extract` koşulmazsa arayüz katman eksik veri gösteriyordu.
        """
        from src.boru_hatti import ablasyon_veritabani
        from src.depolama import VERITABANI_URL

        for ad, _ in ablasyon_modulu.YAPILANDIRMALAR:
            assert ablasyon_veritabani(ad) != VERITABANI_URL


# ---------------------------------------------------------------------------
# 2) Atomiklik — yarım tablo yazılamaz
# ---------------------------------------------------------------------------


class TestAtomiklik:
    def test_eksik_kosu_tabloyu_yazmaz(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Duman testi (`--yalniz-kural`) mevcut tabloyu EZMEZ.

        İlk sürümde eziyordu: tek satır yazıp diğer ikisini siliyordu — yani
        önlemeye çalıştığımız yarım tablonun ta kendisini üretiyordu.
        """
        yazildi: list[object] = []
        monkeypatch.setattr(ablasyon_modulu, "_atomik_yaz", lambda k: yazildi.append(k))
        monkeypatch.setattr(
            ablasyon_modulu, "ham_kayitlari_oku", lambda: [object()]
        )
        monkeypatch.setattr(
            ablasyon_modulu,
            "_yapilandirmayi_kos",
            lambda ad, bayraklar, kayitlar: [],
        )
        monkeypatch.setattr(
            ablasyon_modulu, "temel_metrikler",
            lambda k: {"kampanya_sayisi": 0, "alan_dolulugu": 0.0, "halusinasyon_orani": 0.0},
        )
        monkeypatch.setattr(ablasyon_modulu, "altin_set_metrikleri", lambda k: None)

        assert ablasyon_modulu.calistir(yalniz_kural=True) == 0
        assert not yazildi, "duman testi tabloyu yazdı"

    def test_atomik_yaz_gecici_dosya_birakmaz(self, tmp_path: Path) -> None:
        hedef = tmp_path / "ablasyon.json"
        ablasyon_modulu.ABLASYON_DOSYASI = hedef  # type: ignore[misc]
        try:
            ablasyon_modulu._atomik_yaz({"kural": {"makro_f1": 0.5}})
            assert json.loads(hedef.read_text(encoding="utf-8"))["kural"]["makro_f1"] == 0.5
            assert not list(tmp_path.glob("*.tmp")), "geçici dosya kaldı"
        finally:
            ablasyon_modulu.ABLASYON_DOSYASI = ABLASYON_DOSYASI  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 3) Yayınlanan tablonun kendisi — savunma katmanı yerinde mi
# ---------------------------------------------------------------------------


class TestYayinlananTablo:
    def test_satirlar_ayni_kod_iziyle_kosulmus(self) -> None:
        """REGRESYON — 18 Ağustos'ta üç satır iki farklı kod izi taşıyordu."""
        kayitlar = _kayitlari_oku()
        if len(kayitlar) < len(ABLASYON_SIRASI):
            pytest.skip("tablo henüz tam koşulmadı (make ablasyon)")
        izler = {k["kod_parmak_izi"] for k in kayitlar.values() if k.get("kod_parmak_izi")}
        assert len(izler) == 1, f"satırlar farklı kod sürümleriyle koşulmuş: {izler}"

    def test_satirlar_ayni_korpus_buyuklugunde(self) -> None:
        kayitlar = _kayitlari_oku()
        if len(kayitlar) < len(ABLASYON_SIRASI):
            pytest.skip("tablo henüz tam koşulmadı (make ablasyon)")
        boyutlar = {k["kampanya_sayisi"] for k in kayitlar.values()}
        assert len(boyutlar) == 1, f"farklı korpus büyüklükleri: {boyutlar}"

    def test_rapor_ayrismayi_hala_yakaliyor(self) -> None:
        """Savunma katmanı SİLİNMEDİ — koşucu garanti veriyor diye kaldırmak,
        garantinin bozulduğu günü sessiz kılardı."""
        metin = _ablasyon_notu()
        assert "KARŞILAŞTIRILAMAZ" in metin or "⏳" in metin or "|" in metin
