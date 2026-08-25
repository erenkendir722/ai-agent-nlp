"""Gömme + kosinüs benzerliği RAG katmanı (S-09, ADR 014).

Bu testler AĞ İSTEMEZ: gömme çağrısı sahte bir işlevle değiştiriliyor.
Ölçülen şey EVREN'in kalitesi değil, bizim indeks ve arama mantığımız —
yineleme ayıklama, kampanya süzgeci, hata yolları, boyut sözleşmesi.
"""

from __future__ import annotations

import numpy as np
import pytest

from src import vektor_db
from src.depolama import KampanyaKaydi


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------


def _kayit(kampanya_id: str, ham_metin: str, banka: str = "Test Katılım") -> KampanyaKaydi:
    return KampanyaKaydi(
        kampanya_id=kampanya_id,
        banka_kodu="test",
        banka_adi=banka,
        kaynak_url="https://ornek.test/kampanya",
        cekim_tarihi=None,
        ham_metin=ham_metin,
    )


def _sahte_gomme(metin: str) -> list[float]:
    """Metne göre belirlenimci sahte vektör.

    Gerçek anlam taşımaz ama AYNI metin AYNI vektörü verir — yineleme ve
    süzgeç mantığını sınamak için gereken tek özellik bu.
    """
    tohum = abs(hash(" ".join(metin.lower().split()))) % (2**32)
    uretec = np.random.default_rng(tohum)
    return uretec.standard_normal(vektor_db.BOYUT).astype(np.float32).tolist()


@pytest.fixture
def sahte_evren(monkeypatch, tmp_path):
    """Gömme ucunu sahteler ve indeksi geçici dizine yazar."""
    monkeypatch.setattr(
        vektor_db, "gom_toplu", lambda metinler: [_sahte_gomme(m) for m in metinler]
    )
    monkeypatch.setattr(vektor_db, "INDEKS_DOSYASI", tmp_path / "indeks.npz")
    monkeypatch.setattr(vektor_db, "_indeks", None)
    yield
    vektor_db._indeks = None


# ---------------------------------------------------------------------------
# Paragraflara ayırma
# ---------------------------------------------------------------------------


def test_kisa_satirlar_indekse_girmez():
    """40 karakterin altındaki satırlar bağlam taşımıyor — başlık, tarih, boşluk."""
    kayit = _kayit(
        "k1",
        "Başlık\n"
        + "Bu satır kırk karakterden uzun olduğu için indekse girmelidir.\n"
        + "kısa\n",
    )
    paragraflar = vektor_db.paragraflara_ayir(kayit)
    assert len(paragraflar) == 1
    assert paragraflar[0].startswith("Bu satır kırk")


def test_ham_metni_bos_kayit_cokmez():
    assert vektor_db.paragraflara_ayir(_kayit("k1", "")) == []


# ---------------------------------------------------------------------------
# İndeks kurma ve yükleme
# ---------------------------------------------------------------------------


def test_indeks_kurulur_ve_sayilir(sahte_evren):
    kayitlar = [
        _kayit("k1", "Konut finansmanı için gerekli belgeler listesi burada yer alır."),
        _kayit("k2", "Emekli müşterilerimize özel promosyon kampanyası koşulları."),
    ]
    assert vektor_db.indeks_kur(kayitlar, ilerleme=False) == 2

    durum = vektor_db.indeks_durumu()
    assert durum["var"] is True
    assert durum["paragraf"] == 2
    assert durum["boyut"] == vektor_db.BOYUT
    assert durum["kampanya"] == 2


def test_indeks_yokken_acik_hata(sahte_evren):
    """Sessizce boş dönmek "veri setinde yok" demektir — yanlış cevap üretir."""
    with pytest.raises(vektor_db.IndeksYok, match="make vektor"):
        vektor_db.vektor_ara("herhangi bir soru")


def test_bos_korpus_indekslenemez(sahte_evren):
    with pytest.raises(ValueError, match="make extract"):
        vektor_db.indeks_kur([_kayit("k1", "kısa")], ilerleme=False)


# ---------------------------------------------------------------------------
# Arama
# ---------------------------------------------------------------------------


def test_ayni_metin_iki_kez_donmez(sahte_evren):
    """Korpusta aynı sözleşme cümlesi birçok kampanyada geçiyor; tekrar,
    üç sonuçluk yerin ikisini harcıyordu (ölçüldü, 25 Ağu)."""
    ortak = "Kampanya diğer kampanyalarla birleştirilemez ve değiştirilebilir."
    kayitlar = [
        _kayit("k1", ortak),
        _kayit("k2", ortak),
        _kayit("k3", "Emekli müşterilerimize özel promosyon kampanyası koşulları."),
    ]
    vektor_db.indeks_kur(kayitlar, ilerleme=False)

    sonuclar = vektor_db.vektor_ara(ortak, limit=3)
    metinler = [s["metin"] for s in sonuclar]
    assert len(metinler) == len(set(metinler))


def test_madde_isareti_yinelemeyi_gizleyemez(sahte_evren):
    """«- Cümle» ile «Cümle» aynı içeriktir; imza bunu eşitlemeli."""
    cumle = "Kampanya koşulları önceden haber verilmeksizin değiştirilebilir."
    vektor_db.indeks_kur(
        [_kayit("k1", f"- {cumle}"), _kayit("k2", cumle)], ilerleme=False
    )
    assert len(vektor_db.vektor_ara(cumle, limit=3)) == 1


def test_kampanya_suzgeci_disaridakini_getirmez(sahte_evren):
    kayitlar = [
        _kayit("k1", "Konut finansmanı için gerekli belgeler listesi burada yer alır."),
        _kayit("k2", "Emekli müşterilerimize özel promosyon kampanyası koşulları."),
    ]
    vektor_db.indeks_kur(kayitlar, ilerleme=False)

    sonuclar = vektor_db.vektor_ara("herhangi bir soru", limit=3, kampanya_idleri=["k2"])
    assert {s["kampanya_id"] for s in sonuclar} == {"k2"}


def test_eslesmeyen_suzgec_bos_doner(sahte_evren):
    vektor_db.indeks_kur(
        [_kayit("k1", "Konut finansmanı için gerekli belgeler listesi burada.")],
        ilerleme=False,
    )
    assert vektor_db.vektor_ara("soru", kampanya_idleri=["olmayan"]) == []


def test_sonuclar_benzerlige_gore_sirali(sahte_evren):
    kayitlar = [
        _kayit("k1", "Konut finansmanı için gerekli belgeler listesi burada yer alır."),
        _kayit("k2", "Emekli müşterilerimize özel promosyon kampanyası koşulları."),
        _kayit("k3", "Taşıt finansmanı vade seçenekleri ve başvuru adımları burada."),
    ]
    vektor_db.indeks_kur(kayitlar, ilerleme=False)
    skorlar = [s["benzerlik"] for s in vektor_db.vektor_ara("soru", limit=3)]
    assert skorlar == sorted(skorlar, reverse=True)


# ---------------------------------------------------------------------------
# Boyut sözleşmesi — sessiz model değişimine karşı
# ---------------------------------------------------------------------------


def test_yanlis_boyut_sessizce_gecmez():
    """Jenerik `embed` ucu 2560 boyut veriyor; sessizce kabul edilirse
    indeks bozulur ve arama anlamsız sonuç üretir (25 Ağu, ölçüldü)."""
    with pytest.raises(ValueError, match="Gömme boyutu"):
        vektor_db._boyut_denetle([[0.0] * 2560])


def test_dogru_boyut_gecer():
    vektor_db._boyut_denetle([[0.0] * vektor_db.BOYUT])


def test_birimlestirme_norm_bire_getirir():
    dizey = vektor_db._birimlestir(np.array([[3.0, 4.0], [1.0, 0.0]], dtype=np.float32))
    assert np.allclose(np.linalg.norm(dizey, axis=1), 1.0)


def test_sifir_vektor_bolme_hatasi_vermez():
    dizey = vektor_db._birimlestir(np.zeros((1, 4), dtype=np.float32))
    assert not np.isnan(dizey).any()
