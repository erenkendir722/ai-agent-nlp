"""Görev panosu tutarlılık testleri.

`GOREVLER.md` elle düzenlenen bir dosya ve bağımlılıklar görev kodlarıyla
yazılıyor. Birisi görev numarasını değiştirdiğinde ya da yeni bir bağımlılık
eklerken yanlış kod yazdığında, pano sessizce bozulur: kimse fark etmez,
"şu an başlayabilirsin" listesi yanlış görev gösterir.

Bu testler panoyu `make test` kapsamına alır. Sprint 0'da numaralandırma bir kez
değişti ve iki çapraz referans bayatladı — bu testler o hatayı yakalar.
"""

from __future__ import annotations

import pytest

from tools.gorevler import PANO, dogrula, dongu_bul, engelleyenler, panoyu_oku


@pytest.fixture(scope="module")
def gorevler():
    if not PANO.exists():
        pytest.skip("GOREVLER.md yok")
    return panoyu_oku()


def test_pano_ayristirilabiliyor(gorevler) -> None:
    assert len(gorevler) > 50, f"Beklenenden az görev ayrıştırıldı: {len(gorevler)}"


def test_bagimliliklar_var_olan_gorevlere_isaret_ediyor(gorevler) -> None:
    """Bayat referans yakalayıcı: silinmiş/yeniden numaralanmış koda bağlanma."""
    bilinmeyen = [
        f"{g.kod} -> {k}"
        for g in gorevler.values()
        for k in g.once
        if k not in gorevler
    ]
    assert not bilinmeyen, f"Tanımsız göreve bağımlılık: {bilinmeyen}"


def test_bagimlilik_dongusu_yok(gorevler) -> None:
    """Döngü olursa o zincirdeki hiçbir görev başlayamaz — pano kilitlenir."""
    dongular = dongu_bul(gorevler)
    assert not dongular, f"Bağımlılık döngüsü: {dongular}"


def test_her_gorevin_sahibi_var(gorevler) -> None:
    gecerli = {"Eren", "Samet", "Görkem", "Esra", "Herkes"}
    hatali = [g.kod for g in gorevler.values() if g.sahip not in gecerli]
    assert not hatali, f"Sahibi tanınmayan görev: {hatali}"


def test_herkesin_baslayabilecegi_en_az_bir_is_var(gorevler) -> None:
    """Kimse boşta kalmamalı.

    Bir kişinin TÜM açık görevleri bloke ise, o kişi bekliyor demektir ve
    bu bir planlama hatasıdır — düşük kapasitede en pahalı durum budur.
    """
    for ad in ("Eren", "Samet", "Görkem", "Esra"):
        benim = [
            g for g in gorevler.values()
            if g.sahip in (ad, "Herkes") and not g.bitti
        ]
        hazir = [g for g in benim if not engelleyenler(g, gorevler)]
        assert hazir, f"{ad} için başlanabilir hiçbir görev yok — herkes bloke"


def test_pano_denetimi_temiz(gorevler) -> None:
    sorunlar = dogrula(gorevler)
    assert not sorunlar, "Pano tutarsız:\n" + "\n".join(f"  - {s}" for s in sorunlar)
