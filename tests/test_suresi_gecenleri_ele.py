"""Süresi geçmiş kampanyaların elenmesini koruyan testler.

NEDEN BU TESTLER VAR:
    Bu araç VERİ SİLİYOR. İki hatası da sessizdir ve pahalıdır:

    1. Fazla siler — altın setteki bir kaydı götürürse `make eval` 60 yerine
       59 kayıt üzerinden ölçmeye başlar. Hiçbir test düşmez, metrikler
       oynar ve önceki ölçümlerle karşılaştırma sessizce geçersizleşir.
       O 60 kaydı dört kişi elle etiketledi; yeniden üretmek ucuz değil.
    2. İstemeden siler — kuru çalıştırma yazma yaparsa, "ne silinecek"
       diye bakan kişi silmiş olur.

    Aşağıdaki testler ikisini de sözleşme hâline getirir.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from src.depolama import KampanyaKaydi, oturum, semayi_kur
from tools.suresi_gecenleri_ele import altin_set_kimlikleri, ele, suresi_gecenler

BUGUN = date(2026, 8, 23)


def kayit(kimlik: str, bitis: date | None) -> KampanyaKaydi:
    return KampanyaKaydi(
        kampanya_id=kimlik,
        banka_kodu="0203",
        banka_adi="Albaraka Türk Katılım Bankası A.Ş.",
        kaynak_url=f"https://ornek.test/{kimlik}",
        cekim_tarihi=datetime(2026, 8, 20, 12, 0),
        kampanya_bitis=bitis,
        tam_kayit={"kampanya_id": kimlik},
    )


@pytest.fixture
def veritabani(tmp_path: Path) -> str:
    """Dört kayıtlı geçici veritabanı: 2 süresi geçmiş, 1 geçerli, 1 tarihsiz."""
    url = f"sqlite:///{tmp_path / 'deneme.db'}"
    semayi_kur(url)
    with oturum(url) as oturum_:
        oturum_.add_all(
            [
                kayit("gecmis-1", BUGUN - timedelta(days=60)),
                kayit("gecmis-2", BUGUN - timedelta(days=1)),
                kayit("gecerli", BUGUN + timedelta(days=30)),
                kayit("tarihsiz", None),
            ]
        )
        oturum_.commit()
    return url


def kalanlar(url: str) -> set[str]:
    with oturum(url) as oturum_:
        return {k.kampanya_id for k in oturum_.query(KampanyaKaydi).all()}


class TestSecim:
    def test_yalniz_gecmis_tarihliler_secilir(self, veritabani: str) -> None:
        secilen = {k["kampanya_id"] for k in suresi_gecenler(veritabani, BUGUN)}
        assert secilen == {"gecmis-1", "gecmis-2"}

    def test_tarihsiz_kayit_secilmez(self, veritabani: str) -> None:
        """Bitiş tarihi bilinmiyorsa süresi geçmiş sayılamaz."""
        secilen = {k["kampanya_id"] for k in suresi_gecenler(veritabani, BUGUN)}
        assert "tarihsiz" not in secilen

    def test_bugun_biten_kampanya_secilmez(self, tmp_path: Path) -> None:
        url = f"sqlite:///{tmp_path / 'bugun.db'}"
        semayi_kur(url)
        with oturum(url) as oturum_:
            oturum_.add(kayit("bugun-biten", BUGUN))
            oturum_.commit()
        assert suresi_gecenler(url, BUGUN) == []


class TestKuruCalistirma:
    def test_varsayilan_kosu_SILMEZ(self, veritabani: str) -> None:
        silinecek, _ = ele(veritabani, BUGUN, uygula=False)
        assert len(silinecek) == 2
        assert kalanlar(veritabani) == {"gecmis-1", "gecmis-2", "gecerli", "tarihsiz"}

    def test_uygula_ile_silinir(self, veritabani: str) -> None:
        silinecek, _ = ele(veritabani, BUGUN, uygula=True)
        assert len(silinecek) == 2
        assert kalanlar(veritabani) == {"gecerli", "tarihsiz"}


class TestAltinSetMuafiyeti:
    def test_altin_setteki_kayit_silinmez(
        self, veritabani: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        altin = tmp_path / "altin_set.jsonl"
        altin.write_text(
            json.dumps({"kampanya_id": "gecmis-1", "kampanya_turu": "kart"}) + "\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("tools.suresi_gecenleri_ele.ALTIN_SET", altin)

        silinecek, muaf = ele(veritabani, BUGUN, uygula=True)

        assert {k["kampanya_id"] for k in muaf} == {"gecmis-1"}
        assert {k["kampanya_id"] for k in silinecek} == {"gecmis-2"}
        assert "gecmis-1" in kalanlar(veritabani)

    def test_altin_set_dosyasi_yoksa_bos_kume(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "tools.suresi_gecenleri_ele.ALTIN_SET", tmp_path / "yok.jsonl"
        )
        assert altin_set_kimlikleri(tmp_path / "yok.jsonl") == set()

    def test_gercek_altin_set_okunabiliyor(self) -> None:
        """Depodaki altın set biçimi değişirse muafiyet sessizce çöker."""
        kimlikler = altin_set_kimlikleri()
        assert len(kimlikler) > 0
        assert all(isinstance(k, str) and k for k in kimlikler)
