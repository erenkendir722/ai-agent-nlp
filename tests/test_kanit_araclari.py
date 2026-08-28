"""Veri toplama etiği kanıt araçlarının testleri.

Bu araçların çıktısı jüriye kanıt olarak gösteriliyor. Yanlış bir kanıt,
eksik kanıttan kötüdür: "robots.txt bizi reddetti" ile "robots.txt'i
okuyamadık, o yüzden çekmedik" aynı şey değildir ve bunları karıştıran bir
günlük, sitenin bize yasak koyduğu izlenimini verir.

Testler ağa ÇIKMAZ; kanıt üretimi ağ gerektirir ama kanıtın DOĞRU YAZILMASI
gerektirmez.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx

from tools import kvkk_taramasi, robots_kanit

# Sağlama toplamı tutan sentetik numara — gerçek bir kişiye ait değil,
# algoritmanın ürettiği ilk geçerli değerdir.
GECERLI_TCKN = "10000000146"


def _alan(ad: str = "Test Banka", *, hata: str | None = None, izinli: bool = True) -> dict:
    return {
        "ad": ad,
        "alan": "https://www.test.com",
        "robots": {
            "adres": "https://www.test.com/robots.txt",
            "durum": None if hata else 200,
            "hata": hata,
            "uzunluk": 0 if hata else 42,
            "sha256": None if hata else "a" * 64,
            "dosya": None if hata else "docs/kanit/robots/www.test.com.txt",
            "gonderilen_basliklar": {"user-agent": robots_kanit.KULLANICI_AJANI},
            "beyan_edilen_gecikme": None,
            "sitemapler": [],
        },
        "kararlar": [
            {"url": "https://www.test.com/kampanyalar", "izinli": izinli, "uygulanan_bekleme_sn": 2.0}
        ],
    }


def _veri(alanlar: list[dict]) -> dict:
    return {
        "uretildi": "2026-08-24T22:00:00+03:00",
        "kullanici_ajani": robots_kanit.KULLANICI_AJANI,
        "asgari_istek_araligi_sn": 2.0,
        "uretici": "tools/robots_kanit.py",
        "alanlar": alanlar,
    }


class TestRobotsGunlugu:
    def test_disallow_ile_okunamama_ayri_yazilir(self) -> None:
        """Jüriye gösterilen metinde iki sebep karışmamalı."""
        reddeden = robots_kanit.gunluk_uret(_veri([_alan("Reddeden", izinli=False)]))
        okunamayan = robots_kanit.gunluk_uret(
            _veri([_alan("Okunamayan", hata="ConnectError: zincir", izinli=False)])
        )

        assert "Disallow" in reddeden
        assert "okunamadı" not in reddeden.split("## Alan adı ayrıntıları")[1]
        assert "okunamadı" in okunamayan
        assert "Disallow" not in okunamayan.split("## Alan adı ayrıntıları")[1]

    def test_kullanilan_user_agent_gunluge_yazilir(self) -> None:
        metin = robots_kanit.gunluk_uret(_veri([_alan()]))
        assert robots_kanit.KULLANICI_AJANI in metin
        assert "tarayıcı taklidi yapılmaz" in metin

    def test_sitesiz_banka_sessizce_atlanmaz(self) -> None:
        veri = _veri(
            [{"ad": "Kuruluş Bankası", "alan": None, "atlandi": "site yok", "robots": None, "kararlar": []}]
        )
        assert "site yok" in robots_kanit.gunluk_uret(veri)

    def test_izinli_ve_cekilmeyen_sayilari_toplanir(self) -> None:
        metin = robots_kanit.gunluk_uret(
            _veri([_alan("A", izinli=True), _alan("B", izinli=False)])
        )
        assert "**Toplam:** 1 URL izinli, 1 URL çekilmiyor." in metin


class TestRobotsArsivi:
    @patch("httpx.Client.get")
    def test_html_404_govdesi_robots_diye_arsivlenmez(
        self, sahte_get: MagicMock, tmp_path: Path
    ) -> None:
        """404 sayfası robots.txt değildir; arşive girerse kanıt kirlenir."""
        istek = httpx.Request("GET", "https://www.test.com/robots.txt")
        sahte_get.return_value = httpx.Response(
            404, text="<html>bulunamadı</html>", headers={"content-type": "text/html"}, request=istek
        )
        with patch.object(robots_kanit, "ROBOTS_DIZIN", tmp_path):
            sonuc = robots_kanit.robots_getir("https://www.test.com")

        assert sonuc["durum"] == 404
        assert sonuc["dosya"] is None
        assert list(tmp_path.glob("*.txt")) == []

    @patch("httpx.Client.get")
    def test_arsivlenen_dosyanin_ozeti_diskteki_baytlarla_eslesir(
        self, sahte_get: MagicMock, tmp_path: Path
    ) -> None:
        """Günlükteki sha256 ile dosyanın özeti tutmazsa kanıt doğrulanamaz."""
        import hashlib

        govde = "User-agent: *\nDisallow: /gizli\nCrawl-delay: 5\nSitemap: https://www.test.com/s.xml\n"
        istek = httpx.Request("GET", "https://www.test.com/robots.txt")
        sahte_get.return_value = httpx.Response(
            200, text=govde, headers={"content-type": "text/plain"}, request=istek
        )
        with patch.object(robots_kanit, "ROBOTS_DIZIN", tmp_path):
            sonuc = robots_kanit.robots_getir("https://www.test.com")

        yazilan = (tmp_path / "www.test.com.txt").read_bytes()
        assert hashlib.sha256(yazilan).hexdigest() == sonuc["sha256"]
        assert sonuc["beyan_edilen_gecikme"] == 5.0
        assert sonuc["sitemapler"] == ["https://www.test.com/s.xml"]

    @patch("httpx.Client.get", side_effect=httpx.ConnectError("zincir doğrulanamadı"))
    def test_ag_hatasi_gizlenmez_yazilir(self, _sahte_get: MagicMock) -> None:
        sonuc = robots_kanit.robots_getir("https://www.bddk.example")
        assert sonuc["hata"].startswith("ConnectError")
        assert sonuc["dosya"] is None


class TestTcknSaglamasi:
    def test_ornek_form_degeri_kisisel_veri_sayilmaz(self) -> None:
        assert not kvkk_taramasi.tckn_gecerli_mi("11111111111")
        assert not kvkk_taramasi.tckn_gecerli_mi("12345678901")

    def test_saglama_toplami_tutan_numara_yakalanir(self) -> None:
        assert kvkk_taramasi.tckn_gecerli_mi(GECERLI_TCKN)

    def test_sifirla_baslayan_ve_kisa_degerler_elenir(self) -> None:
        assert not kvkk_taramasi.tckn_gecerli_mi("01000000146")
        assert not kvkk_taramasi.tckn_gecerli_mi("1000000014")


class TestKvkkTaramasi:
    def _korpus(self, tmp_path: Path, metin: str) -> Path:
        dizin = tmp_path / "0203"
        dizin.mkdir(parents=True)
        (dizin / "0203-aaa.json").write_text(
            json.dumps(
                {"banka_kodu": "0203", "url": "https://x/y", "baslik": "Kampanya", "govde_metin": metin},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return tmp_path

    def test_gercek_kisi_numarasi_supheli_olarak_raporlanir(self, tmp_path: Path) -> None:
        veri = kvkk_taramasi.tara(self._korpus(tmp_path, f"Başvuru no {GECERLI_TCKN} ile"))
        assert len(veri["supheliler"]) == 1
        rapor = kvkk_taramasi.rapor_uret(veri)
        assert "şüpheli bulgu var" in rapor
        assert GECERLI_TCKN not in rapor  # tam değer rapora yazılmaz

    def test_kurumsal_iletisim_bilgisi_maskelenir(self, tmp_path: Path) -> None:
        veri = kvkk_taramasi.tara(
            self._korpus(tmp_path, "Bilgi: destek@banka.com.tr — IBAN TR04 0021 1000 0005 1027 4001 18")
        )
        rapor = kvkk_taramasi.rapor_uret(veri)
        assert not veri["supheliler"]
        assert "destek@banka.com.tr" not in rapor
        assert "…@banka.com.tr" in rapor
        assert "…0118" in rapor

    def test_temiz_korpus_temiz_raporlanir(self, tmp_path: Path) -> None:
        veri = kvkk_taramasi.tara(self._korpus(tmp_path, "Aylık %2,05 kâr payı ile konut finansmanı."))
        assert veri["kayit_sayisi"] == 1
        assert not veri["supheliler"]
        assert "Kimliği belirli gerçek kişiye ait veri bulunmadı" in kvkk_taramasi.rapor_uret(veri)
