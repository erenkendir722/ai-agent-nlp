"""Yinelenen kayıtların elenmesini koruyan testler.

NEDEN BU TESTLER VAR:
    `test_suresi_gecenleri_ele.py` ile aynı gerekçe — bu araç da VERİ SİLİYOR
    ve hataları sessiz. Buraya özgü üç risk daha var:

    1. **Yanlış ucu tutar.** Bir çiftin iki ucu da kalıcıdır ama biri
       kanoniktir: TOM'da aynı kampanya `/kampanyalar/X` ve
       `/cok-kazananlar-kulubu-kampanya/X` altında duruyor. Vitrin adresini
       tutup liste adresini silmek, kaynağı bir dahaki gezmede kaybettirir.
    2. **Boşluğa takılır.** Albaraka aynı sayfayı tek boşluk farkıyla iki
       biçimde veriyor (bkz. ADR 018). Boşluğa duyarlı bir özet o çifti
       görmez ve yinelenme sessizce kalır.
    3. **Altın setin İKİ ucunu birden götürür.** Aynı içerik iki adreste
       etiketlendiyse ikisi de korunmalı; biri silinirse `make eval` ölçüm
       zemini kayar ve hiçbir test düşmez.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from src.depolama import KampanyaKaydi, oturum, semayi_kur
from tools.yinelenenleri_ele import (
    altin_set_kimlikleri,
    ele,
    icerik_izi,
    yinelenen_obekleri,
)


def kayit(kimlik: str, url: str, metin: str) -> KampanyaKaydi:
    return KampanyaKaydi(
        kampanya_id=kimlik,
        banka_kodu="0213",
        banka_adi="T.O.M. Katılım Bankası A.Ş.",
        kaynak_url=url,
        cekim_tarihi=datetime(2026, 8, 20, 12, 0),
        ham_metin=metin,
        tam_kayit={"kampanya_id": kimlik},
    )


@pytest.fixture
def veritabani(tmp_path: Path) -> str:
    """Beş kayıt: bir kopya çifti, bir üçlü öbek, bir tekil."""
    url = f"sqlite:///{tmp_path / 'deneme.db'}"
    semayi_kur(url)
    with oturum(url) as oturum_:
        oturum_.add_all(
            [
                kayit("cift-liste", "https://t.test/kampanyalar/x", "Aynı kampanya metni"),
                kayit("cift-vitrin", "https://t.test/kulup-kampanya/x", "Aynı kampanya metni"),
                kayit("kabuk-1", "https://t.test/a.pdf", "PDF kabuğu"),
                kayit("kabuk-2", "https://t.test/b.pdf", "PDF kabuğu"),
                kayit("kabuk-3", "https://t.test/c.pdf", "PDF kabuğu"),
                kayit("tekil", "https://t.test/kampanyalar/y", "Kendine özgü metin"),
            ]
        )
        oturum_.commit()
    return url


def kalanlar(url: str) -> set[str]:
    with oturum(url) as oturum_:
        return {k.kampanya_id for k in oturum_.query(KampanyaKaydi).all()}


class TestIcerikIzi:
    def test_bosluk_farki_ayni_iz_verir(self) -> None:
        """Albaraka aynı sayfayı iki boşluk biçiminde veriyor (ADR 018)."""
        assert icerik_izi("Kampanya  metni\n\n") == icerik_izi("Kampanya metni")

    def test_farkli_icerik_farkli_iz_verir(self) -> None:
        assert icerik_izi("Kampanya metni") != icerik_izi("Başka metin")

    def test_bos_metin_patlamaz(self) -> None:
        assert icerik_izi(None) == icerik_izi("")


class TestSecim:
    def test_yalniz_cok_uyeli_obekler_secilir(self, veritabani: str) -> None:
        obekler = yinelenen_obekleri(veritabani)
        assert sorted(len(o) for o in obekler) == [2, 3]

    def test_tekil_kayit_obege_girmez(self, veritabani: str) -> None:
        kimlikler = {k["kampanya_id"] for o in yinelenen_obekleri(veritabani) for k in o}
        assert "tekil" not in kimlikler


class TestTutmaKurali:
    def test_kanonik_kampanya_adresi_tutulur(self, veritabani: str) -> None:
        """URL'inde 'kampanya' geçen uç kalır — vitrin adresi değil."""
        silinecek, _ = ele(veritabani, uygula=False)
        assert {k["kampanya_id"] for k in silinecek} >= {"cift-vitrin"}
        assert "cift-liste" not in {k["kampanya_id"] for k in silinecek}

    def test_her_obekten_tam_bir_kayit_kalir(self, veritabani: str) -> None:
        ele(veritabani, uygula=True)
        assert kalanlar(veritabani) == {"cift-liste", "kabuk-1", "tekil"}

    def test_secim_belirlenircidir(self, veritabani: str) -> None:
        """Aynı veritabanı her koşuda aynı kaydı tutmalı."""
        birinci = {k["kampanya_id"] for k in ele(veritabani, uygula=False)[0]}
        ikinci = {k["kampanya_id"] for k in ele(veritabani, uygula=False)[0]}
        assert birinci == ikinci


class TestKuruCalistirma:
    def test_varsayilan_kosu_SILMEZ(self, veritabani: str) -> None:
        silinecek, _ = ele(veritabani, uygula=False)
        assert len(silinecek) == 3
        assert len(kalanlar(veritabani)) == 6

    def test_uygula_ile_silinir(self, veritabani: str) -> None:
        silinecek, _ = ele(veritabani, uygula=True)
        assert len(silinecek) == 3
        assert len(kalanlar(veritabani)) == 3


class TestAltinSetMuafiyeti:
    def _altin_yaz(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *kimlikler: str) -> None:
        yol = tmp_path / "altin_set.jsonl"
        yol.write_text(
            "\n".join(json.dumps({"kampanya_id": k}) for k in kimlikler) + "\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("tools.yinelenenleri_ele.ALTIN_SET", yol)

    def test_altin_setteki_uc_tutulur(
        self, veritabani: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Etiketli olan vitrin adresi bile olsa o kalır, kanonik olan düşer."""
        self._altin_yaz(tmp_path, monkeypatch, "cift-vitrin")
        silinecek, _ = ele(veritabani, uygula=True)

        assert "cift-vitrin" not in {k["kampanya_id"] for k in silinecek}
        assert "cift-vitrin" in kalanlar(veritabani)

    def test_iki_ucu_da_etiketliyse_ikisi_de_kalir(
        self, veritabani: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ölçüm zemini, sayım şişkinliğinden pahalıdır."""
        self._altin_yaz(tmp_path, monkeypatch, "cift-liste", "cift-vitrin")
        ele(veritabani, uygula=True)

        assert {"cift-liste", "cift-vitrin"} <= kalanlar(veritabani)

    def test_altin_set_yoksa_bos_kume(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("tools.yinelenenleri_ele.ALTIN_SET", tmp_path / "yok.jsonl")
        assert altin_set_kimlikleri() == set()
