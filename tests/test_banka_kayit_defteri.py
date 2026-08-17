"""`data/banks.yaml` sözleşme testleri — şartname 5.1 kayıt defteri.

G-01'de on bankanın `kod_dogrulandi` bayrağı `true`'ya çekildi ve Adil Katılım'a
yeni bir EFT kodu (0215) atandı. O ana kadar kayıt defterini denetleyen hiçbir
test yoktu: yer tutucu bir kod (`DOGRULA-ADIL`) "doğrulandı" işaretlenebilir,
iki banka aynı kodu taşıyabilirdi. Kimlik çakışması kampanyaları yanlış bankaya
yazar ve bu, çıkarım metriklerinde değil yalnız sunumda görünür.
"""

from __future__ import annotations

import re

import pytest

from src.collector.toplayici import bankalari_yukle
from src.schema import BankaDurumu

EFT_KODU = re.compile(r"^\d{4}$")


@pytest.fixture(scope="module")
def bankalar():
    return bankalari_yukle()


def test_kodlar_benzersiz(bankalar) -> None:
    """Aynı kodu taşıyan iki banka kampanyaları birbirine karıştırır."""
    kodlar = [b.kod for b in bankalar]
    tekrar = {k for k in kodlar if kodlar.count(k) > 1}
    assert not tekrar, f"Yinelenen banka kodu: {sorted(tekrar)}"


def test_dogrulanmis_kod_gercek_eft_kodudur(bankalar) -> None:
    """`kod_dogrulandi: true` demek dört haneli gerçek EFT kodu demek.

    Yer tutucu (`DOGRULA-*`) taşıyan bir kayıt doğrulanmış sayılamaz.
    """
    hatali = [
        f"{b.ad} -> {b.kod}"
        for b in bankalar
        if b.kod_dogrulandi and not EFT_KODU.match(b.kod)
    ]
    assert not hatali, f"Doğrulandı işaretli ama kod EFT biçiminde değil: {hatali}"


def test_faal_bankanin_kodu_dogrulanmis(bankalar) -> None:
    """Kampanya beklenen bankanın kimliği kesin olmalı."""
    eksik = [
        b.ad
        for b in bankalar
        if b.durum == BankaDurumu.FAAL and not b.kod_dogrulandi
    ]
    assert not eksik, f"Faal ama kodu doğrulanmamış banka: {eksik}"


def test_faal_bankalar_bddk_kanitiyla_ayni_sayida(bankalar) -> None:
    """`docs/kanit/bddk-liste.png` 12 Ağu 2026'da 10 faal katılım bankası gösteriyor.

    Sayı değişirse kanıt görüntüsü de yenilenmeli — yoksa şartname 5.1 kanıtı
    kayıt defteriyle çelişir.
    """
    faal = [b for b in bankalar if b.durum == BankaDurumu.FAAL]
    assert len(faal) == 10, (
        f"Faal banka sayısı {len(faal)}, kanıt görüntüsü 10 diyor. "
        "docs/kanit/bddk-liste.png yenilenmeli."
    )
