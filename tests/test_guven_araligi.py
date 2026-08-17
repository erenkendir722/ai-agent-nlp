"""Makro-F1 güven aralığının sözleşme testleri.

Aralık, sunumda söylenecek sayının yanına gidiyor. Sessizce bozulursa
(her koşuda oynayan, noktayı içermeyen ya da ters sıralı bir aralık)
jüriye yanlış bir belirsizlik beyan edilir — bu, aralık hiç vermemekten
kötüdür.
"""

from __future__ import annotations

import pytest

from eval.calistir import altin_set_metrikleri, altin_seti_yukle, makro_f1_guven_araligi
from src.depolama import kampanyalari_oku


@pytest.fixture(scope="module")
def kampanyalar():
    return list(kampanyalari_oku())


@pytest.fixture(scope="module")
def altin():
    return altin_seti_yukle()


def test_aralik_ayni_tohumda_ayni_sonucu_verir(kampanyalar, altin) -> None:
    """Rapor her koşuda oynarsa hangi sayının doğru olduğu bilinemez."""
    if not kampanyalar or not altin:
        pytest.skip("veritabanı veya altın set yok")
    a = makro_f1_guven_araligi(kampanyalar, altin, tekrar=50)
    b = makro_f1_guven_araligi(kampanyalar, altin, tekrar=50)
    assert a == b


def test_aralik_siralidir(kampanyalar, altin) -> None:
    if not kampanyalar or not altin:
        pytest.skip("veritabanı veya altın set yok")
    alt, ust = makro_f1_guven_araligi(kampanyalar, altin, tekrar=50)
    assert alt <= ust


def test_aralik_nokta_tahmini_icerir(kampanyalar, altin) -> None:
    """Raporlanan makro-F1 kendi aralığının dışında kalamaz."""
    if not kampanyalar or not altin:
        pytest.skip("veritabanı veya altın set yok")
    alt, ust = makro_f1_guven_araligi(kampanyalar, altin, tekrar=200)
    nokta = altin_set_metrikleri(kampanyalar, altin)["makro_f1"]
    assert alt <= nokta <= ust


def test_aralik_0_1_araliginda(kampanyalar, altin) -> None:
    if not kampanyalar or not altin:
        pytest.skip("veritabanı veya altın set yok")
    alt, ust = makro_f1_guven_araligi(kampanyalar, altin, tekrar=50)
    assert 0.0 <= alt <= 1.0 and 0.0 <= ust <= 1.0


def test_altin_set_yoksa_aralik_yok(kampanyalar) -> None:
    """Ölçülemeyen şey için aralık uydurulmaz."""
    assert makro_f1_guven_araligi(kampanyalar, []) is None


def test_disaridan_verilen_altin_set_kullanilir(kampanyalar, altin) -> None:
    """Önyükleme, yeniden örneklenmiş seti ölçüm yoluna geçirebilmeli —
    yoksa aralık raporlanan sayıdan başka bir şeyi ölçer."""
    if not kampanyalar or len(altin) < 2:
        pytest.skip("veritabanı veya altın set yok")
    tam = altin_set_metrikleri(kampanyalar, altin)
    tek = altin_set_metrikleri(kampanyalar, altin[:1])
    assert tam["altin_set_boyutu"] == len(altin)
    assert tek["altin_set_boyutu"] == 1
