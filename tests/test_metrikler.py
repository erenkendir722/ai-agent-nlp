"""Değerlendirme metrikleri — F1, makro-F1 ve «hep boş» tabanı (S-12).

NEDEN BU TESTLER VAR:
    Altın setin çoğu hücresi boş. Doğruluk metriği «iki taraf da boş»
    hücreleri doğru saydığı için, hiçbir şey çıkarmayan bir sistem bile
    yüksek doğruluk alır. Buradaki testler F1'in bu tuzağa DÜŞMEDİĞİNİ
    kanıtlar: doğru negatif sayılmaz, aşırı çıkarım cezalandırılır.

    Metrik kodunun kendisi yanlışsa, ölçtüğü her şey yanlıştır. Sunumda
    jüriye söylenecek sayı buradan çıkıyor.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from eval.calistir import _f1, altin_set_metrikleri
from src.schema import Alan, Kampanya


def _kampanya(kimlik: str, **ek) -> Kampanya:
    return Kampanya(
        banka_adi="Test Katılım Bankası A.Ş.",
        banka_kodu="0299",
        kampanya_id=kimlik,
        kaynak_url="https://ornek.test/kampanya",
        cekim_tarihi=datetime(2026, 8, 16, 12, 0),
        ham_metin="kampanya metni",
        **ek,
    )


def _alan(deger: float) -> Alan:
    return Alan(deger=deger, ham_ifade=str(deger), guven=0.9, yontem="kural")


@pytest.fixture
def altin_yaz(tmp_path, monkeypatch):
    """Altın set dosyasını geçici bir yola yazar ve modüle bağlar."""
    import json

    from eval import calistir as modul

    def yaz(kayitlar: list[dict]) -> None:
        yol = tmp_path / "altin_set.jsonl"
        yol.write_text(
            "\n".join(json.dumps(k, ensure_ascii=False) for k in kayitlar),
            encoding="utf-8",
        )
        monkeypatch.setattr(modul, "ALTIN_SET", yol)

    return yaz


# ---------------------------------------------------------------------------
# _f1 — sayaçtan orana
# ---------------------------------------------------------------------------


def test_hic_pozitif_hucre_yoksa_olculmedi_doner():
    """Sıfır DEĞİL None: ölçülmemişi başarısız göstermek ölçmemekten kötüdür."""
    assert _f1(0, 0, 0) == {"kesinlik": None, "duyarlilik": None, "f1": None}


def test_kusursuz_cikarim_f1_biri_verir():
    assert _f1(5, 0, 0) == {"kesinlik": 1.0, "duyarlilik": 1.0, "f1": 1.0}


def test_yalniz_yanlis_pozitif_f1_sifirlar():
    olcum = _f1(0, 4, 0)
    assert olcum["kesinlik"] == 0.0
    assert olcum["f1"] == 0.0


def test_kesinlik_ve_duyarlilik_ayri_hesaplanir():
    olcum = _f1(3, 1, 1)
    assert olcum["kesinlik"] == pytest.approx(0.75)
    assert olcum["duyarlilik"] == pytest.approx(0.75)
    assert olcum["f1"] == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# Doğru negatif F1'e girmez — metriğin bütün amacı
# ---------------------------------------------------------------------------


def test_iki_taraf_da_bos_hucre_f1e_girmez(altin_yaz):
    """«Altın boş, sistem de boş» doğruluğu artırır ama F1'i ETKİLEMEZ."""
    altin_yaz([{"kampanya_id": "0299-a", "kar_payi_orani": None}])
    olcum = altin_set_metrikleri([_kampanya("0299-a")])

    assert olcum["alan_bazli"]["kar_payi_orani"] == 1.0  # doğruluk: tam
    assert olcum["sayimlar"]["kar_payi_orani"] == {"dp": 0, "yp": 0, "yn": 0}
    assert olcum["alan_f1"]["kar_payi_orani"]["f1"] is None  # F1: ölçülmedi


def test_hicbir_sey_cikarmayan_sistem_yuksek_dogruluk_dusuk_f1_alir(altin_yaz):
    """Metriğin şişkinliğini gösteren asıl test.

    Dokuz boş, bir dolu hücre. Hiçbir şey çıkarmayan sistem 0,900 doğruluk
    alır — ama tek bir doğru değer üretmediği için F1'i sıfırdır.
    """
    kayitlar = [{"kampanya_id": f"0299-{i}", "odul_miktari": None} for i in range(9)]
    kayitlar.append({"kampanya_id": "0299-9", "odul_miktari": 2000.0})
    altin_yaz(kayitlar)

    bos_sistem = [_kampanya(f"0299-{i}") for i in range(10)]
    olcum = altin_set_metrikleri(bos_sistem)

    assert olcum["alan_bazli"]["odul_miktari"] == pytest.approx(0.9)
    assert olcum["hep_bos_tabani"]["odul_miktari"] == pytest.approx(0.9)
    assert olcum["alan_f1"]["odul_miktari"]["f1"] == 0.0


def test_asiri_cikarim_dogrulugu_az_f1i_cok_dusurur(altin_yaz):
    """Boş olması gereken hücrelere değer yazmak yanlış pozitiftir."""
    kayitlar = [{"kampanya_id": f"0299-{i}", "odul_miktari": None} for i in range(9)]
    kayitlar.append({"kampanya_id": "0299-9", "odul_miktari": 2000.0})
    altin_yaz(kayitlar)

    # Sistem her kayda değer yazıyor; yalnız sonuncusu doğru.
    asiri = [_kampanya(f"0299-{i}", odul_miktari=_alan(2000.0)) for i in range(10)]
    olcum = altin_set_metrikleri(asiri)

    assert olcum["alan_bazli"]["odul_miktari"] == pytest.approx(0.1)
    assert olcum["sayimlar"]["odul_miktari"] == {"dp": 1, "yp": 9, "yn": 0}
    assert olcum["alan_f1"]["odul_miktari"]["kesinlik"] == pytest.approx(0.1)
    assert olcum["alan_f1"]["odul_miktari"]["duyarlilik"] == 1.0


# ---------------------------------------------------------------------------
# Yanlış değer: hem YP hem YN
# ---------------------------------------------------------------------------


def test_yanlis_deger_hem_yanlis_pozitif_hem_yanlis_negatif_sayilir(altin_yaz):
    """Uydurulmuş bir değerdir VE doğru cevap kaçırılmıştır — ikisi de sayılır."""
    altin_yaz([{"kampanya_id": "0299-a", "vade_ay_max": 36.0}])
    olcum = altin_set_metrikleri([_kampanya("0299-a", vade_ay_max=_alan(48.0))])

    assert olcum["sayimlar"]["vade_ay_max"] == {"dp": 0, "yp": 1, "yn": 1}
    assert olcum["alan_f1"]["vade_ay_max"]["f1"] == 0.0


def test_iskalanan_deger_yalniz_yanlis_negatif_sayilir(altin_yaz):
    """Boş bırakmak halüsinasyon değildir: YP artmaz, yalnız YN artar."""
    altin_yaz([{"kampanya_id": "0299-a", "vade_ay_max": 36.0}])
    olcum = altin_set_metrikleri([_kampanya("0299-a")])

    assert olcum["sayimlar"]["vade_ay_max"] == {"dp": 0, "yp": 0, "yn": 1}
    assert olcum["alan_f1"]["vade_ay_max"]["kesinlik"] == 0.0


# ---------------------------------------------------------------------------
# Makro-F1
# ---------------------------------------------------------------------------


def test_makro_f1_olculmeyen_alanlari_disarida_birakir(altin_yaz):
    """Etiketlenmemiş alanlar ortalamayı sıfıra çekmemeli."""
    altin_yaz([{"kampanya_id": "0299-a", "vade_ay_max": 36.0}])
    olcum = altin_set_metrikleri([_kampanya("0299-a", vade_ay_max=_alan(36.0))])

    # Yalnız vade_ay_max'ın sinyali var; makro-F1 onun F1'ine eşit olmalı.
    assert olcum["alan_f1"]["vade_ay_max"]["f1"] == 1.0
    assert olcum["makro_f1"] == 1.0


def test_makro_f1_alanlari_esit_agirliklar(altin_yaz):
    """Nadir alan, sık alanın içinde erimemeli (mikro değil makro ortalama)."""
    kayitlar = [
        {"kampanya_id": f"0299-{i}", "vade_ay_max": 36.0, "odul_miktari": None}
        for i in range(9)
    ]
    kayitlar.append({"kampanya_id": "0299-9", "vade_ay_max": 36.0, "odul_miktari": 500.0})
    altin_yaz(kayitlar)

    # vade_ay_max kusursuz (10 hücre), odul_miktari tamamen yanlış (1 hücre).
    sistem = [_kampanya(f"0299-{i}", vade_ay_max=_alan(36.0)) for i in range(10)]
    olcum = altin_set_metrikleri(sistem)

    assert olcum["alan_f1"]["vade_ay_max"]["f1"] == 1.0
    assert olcum["alan_f1"]["odul_miktari"]["f1"] == 0.0
    # Mikro ortalama ~0,95 verirdi; makro iki alanı eşitler.
    assert olcum["makro_f1"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Kenar durumlar
# ---------------------------------------------------------------------------


def test_altin_set_yoksa_none_doner(tmp_path, monkeypatch):
    from eval import calistir as modul

    monkeypatch.setattr(modul, "ALTIN_SET", tmp_path / "yok.jsonl")
    assert altin_set_metrikleri([_kampanya("0299-a")]) is None


def test_eslesmeyen_kampanya_sayaclara_girmez(altin_yaz):
    """Altın sette olup veritabanında olmayan kayıt metriği bozmamalı."""
    altin_yaz([{"kampanya_id": "0299-yok", "vade_ay_max": 36.0}])
    olcum = altin_set_metrikleri([_kampanya("0299-baska")])

    assert olcum["eslesen_ornek"] == 0
    assert olcum["sayimlar"]["vade_ay_max"] == {"dp": 0, "yp": 0, "yn": 0}
    assert olcum["makro_f1"] is None
