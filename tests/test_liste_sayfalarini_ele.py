"""İndekslenemeyen liste sayfalarının elenmesini koruyan testler.

NEDEN BU TESTLER VAR:
    Bu araç VERİ SİLİYOR ve `test_suresi_gecenleri_ele.py` ile aynı iki
    sessiz hataya açık: fazla silmek (altın seti götürüp ölçüm zeminini
    kaydırmak) ve istemeden silmek (kuru çalıştırmanın yazması).

    Bir üçüncüsü buraya özgü: **ölçütün ikinci bir kopyası**. Araç, RAG
    katmanının zaten uyguladığı kuralı kullanır (`paragraflara_ayir`).
    Burada ayrı bir uzunluk eşiği yazılsaydı, eşik bir gün değiştiğinde
    indeks ile veritabanı sessizce ayrışırdı: indekste olmayan ama
    veritabanında duran kayıtlar geri gelirdi.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from src.depolama import KampanyaKaydi, oturum, semayi_kur
from src.vektor_db import ASGARI_PARAGRAF
from tools.liste_sayfalarini_ele import altin_set_kimlikleri, ele, indekslenemeyenler

# Gerçek liste sayfalarının biçimi: uzun ama tek satırı bile indekslenemez.
LISTE_SAYFASI = "Market ve Gıda\n" + "Son Gün 07.09.2026\n" * 40
KAMPANYA_SAYFASI = (
    "Ziraat Katılım kredi kartınızla market alışverişlerinizde "
    "vade farksız 6 taksit fırsatından yararlanabilirsiniz.\n"
)


def kayit(kimlik: str, metin: str) -> KampanyaKaydi:
    return KampanyaKaydi(
        kampanya_id=kimlik,
        banka_kodu="0209",
        banka_adi="Ziraat Katılım Bankası A.Ş.",
        kaynak_url=f"https://ornek.test/{kimlik}",
        cekim_tarihi=datetime(2026, 8, 20, 12, 0),
        ham_metin=metin,
        tam_kayit={"kampanya_id": kimlik},
    )


@pytest.fixture
def veritabani(tmp_path: Path) -> str:
    """Üç kayıt: 2 liste sayfası, 1 gerçek kampanya."""
    url = f"sqlite:///{tmp_path / 'deneme.db'}"
    semayi_kur(url)
    with oturum(url) as oturum_:
        oturum_.add_all(
            [
                kayit("liste-1", LISTE_SAYFASI),
                kayit("liste-2", "E-Ticaret\n" + "Son Gün 31.08.2026\n" * 20),
                kayit("gercek", KAMPANYA_SAYFASI),
            ]
        )
        oturum_.commit()
    return url


def kalanlar(url: str) -> set[str]:
    with oturum(url) as oturum_:
        return {k.kampanya_id for k in oturum_.query(KampanyaKaydi).all()}


class TestSecim:
    def test_yalniz_indekslenemeyenler_secilir(self, veritabani: str) -> None:
        secilen = {k["kampanya_id"] for k in indekslenemeyenler(veritabani)}
        assert secilen == {"liste-1", "liste-2"}

    def test_uzunluk_olcut_degil(self, veritabani: str) -> None:
        """Sahadaki en büyük liste sayfası 3.970 karakter — uzunluk aldatır."""
        uzunluklar = {k["kampanya_id"]: k["uzunluk"] for k in indekslenemeyenler(veritabani)}
        assert uzunluklar["liste-1"] > len(KAMPANYA_SAYFASI), (
            "liste sayfası gerçek kampanyadan uzun; seçim yine de doğru olmalı"
        )

    def test_olcut_rag_katmanindan_okunur(self, tmp_path: Path) -> None:
        """Eşiğin tek kaynağı `vektor_db.ASGARI_PARAGRAF` — ikinci kopya yok."""
        url = f"sqlite:///{tmp_path / 'esik.db'}"
        semayi_kur(url)
        with oturum(url) as oturum_:
            oturum_.add_all(
                [
                    kayit("tam-esikte", "x" * ASGARI_PARAGRAF),
                    kayit("esigin-altinda", "x" * (ASGARI_PARAGRAF - 1)),
                ]
            )
            oturum_.commit()
        secilen = {k["kampanya_id"] for k in indekslenemeyenler(url)}
        assert secilen == {"esigin-altinda"}


class TestAltinSetMuafiyeti:
    def test_etiketli_kayit_silinmez(self, veritabani: str, tmp_path: Path) -> None:
        """Sahada ısırdı: sekiz adayın biri altın sette."""
        altin = tmp_path / "altin.jsonl"
        altin.write_text(json.dumps({"kampanya_id": "liste-1"}) + "\n", encoding="utf-8")

        import tools.liste_sayfalarini_ele as arac

        eski = arac.ALTIN_SET
        arac.ALTIN_SET = altin
        try:
            silinecek, korunan = ele(veritabani, uygula=True)
        finally:
            arac.ALTIN_SET = eski

        assert {k["kampanya_id"] for k in silinecek} == {"liste-2"}
        assert {k["kampanya_id"] for k in korunan} == {"liste-1"}
        assert kalanlar(veritabani) == {"liste-1", "gercek"}

    def test_altin_set_yoksa_bos_kume(self, tmp_path: Path) -> None:
        assert altin_set_kimlikleri(tmp_path / "yok.jsonl") == set()


class TestKuruCalistirma:
    def test_uygula_olmadan_hicbir_sey_silinmez(self, veritabani: str) -> None:
        """«Ne silinecek» diye bakan kişi silmiş olmamalı."""
        silinecek, _ = ele(veritabani, uygula=False)
        assert {k["kampanya_id"] for k in silinecek} == {"liste-1", "liste-2"}
        assert kalanlar(veritabani) == {"liste-1", "liste-2", "gercek"}

    def test_uygula_ile_silinir(self, veritabani: str) -> None:
        ele(veritabani, uygula=True)
        assert kalanlar(veritabani) == {"gercek"}
