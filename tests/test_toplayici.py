"""Toplama altyapısı testleri — kayıt defteri, robots kapısı, disk biçimi.

Kazıyıcıların kendisi `tests/test_kaziyicilar.py` içinde sınanır. Buradaki
testler tarayıcı gerektirmez: `bankalari_yukle` ve `kaydi_yaz` gibi
yardımcıları arayüz ve değerlendirme kodu da çağırıyor.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.collector.toplayici import (
    ISTEK_ARASI_SANIYE,
    NezaketSirasi,
    RobotsBekcisi,
    bankalari_yukle,
    faal_bankalar,
    ham_kayitlari_oku,
    kaydi_yaz,
)
from src.schema import HamKayit

# -- Fake Data --

MOCK_BANKS_YAML = """
- kod: "0203"
  ad: "Test Banka 1"
  kisa_ad: "Test1"
  site: "https://www.test1.com"
  durum: "faal"
  kod_dogrulandi: true
  seed_urls: ["https://www.test1.com/kampanya"]
  url_desenleri: ["/kampanya"]
  robots_kontrol: true

- kod: "0215"
  ad: "Test Banka 2"
  kisa_ad: "Test2"
  site: "https://www.test2.com"
  durum: "faaliyete_gecmedi"
  kod_dogrulandi: true
  seed_urls: []
  url_desenleri: []
  robots_kontrol: true
"""


@pytest.fixture
def mock_banks_file(tmp_path: Path) -> Path:
    p = tmp_path / "banks.yaml"
    p.write_text(MOCK_BANKS_YAML, encoding="utf-8")
    return p


class TestBankalariYukle:
    def test_yaml_dosyasindan_banka_listesi_yuklenir(self, mock_banks_file: Path) -> None:
        bankalar = bankalari_yukle(mock_banks_file)
        assert len(bankalar) == 2
        assert bankalar[0].kisa_ad == "Test1"

    def test_faal_bankalar_sadece_kampanya_beklenenleri_doner(self, mock_banks_file: Path) -> None:
        bankalar = bankalari_yukle(mock_banks_file)
        faal = faal_bankalar(bankalar)
        assert len(faal) == 1
        assert faal[0].kisa_ad == "Test1"


class TestRobotsBekcisi:
    @patch("urllib.robotparser.RobotFileParser.can_fetch")
    @patch("httpx.Client.get")
    def test_izinli_url_geciriliyor(
        self, mock_get: MagicMock, mock_can_fetch: MagicMock
    ) -> None:
        mock_get.return_value = MagicMock(status_code=200, text="User-agent: *\\nAllow: /")
        mock_can_fetch.return_value = True

        bekci = RobotsBekcisi("TestBot")
        assert bekci.izinli_mi("https://example.com/kampanya") is True

    @patch("httpx.Client.get")
    def test_robots_okunamazsa_temkinli_red(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = httpx.HTTPError("Network Error")
        bekci = RobotsBekcisi("TestBot")
        assert bekci.izinli_mi("https://example.com/kampanya") is False

    @patch("urllib.robotparser.RobotFileParser.crawl_delay")
    @patch("httpx.Client.get")
    def test_crawl_delay_uygulanir(self, mock_get: MagicMock, mock_delay: MagicMock) -> None:
        mock_get.return_value = MagicMock(status_code=200, text="")
        mock_delay.return_value = 5.0
        bekci = RobotsBekcisi("TestBot")
        assert bekci.bekleme_suresi("https://example.com/") == 5.0

    @patch("urllib.robotparser.RobotFileParser.crawl_delay")
    @patch("httpx.Client.get")
    def test_crawl_delay_alt_sinir_uygulanir(
        self, mock_get: MagicMock, mock_delay: MagicMock
    ) -> None:
        mock_get.return_value = MagicMock(status_code=200, text="")
        mock_delay.return_value = 0.5  # Çok düşük
        bekci = RobotsBekcisi("TestBot")
        assert bekci.bekleme_suresi("https://example.com/") == ISTEK_ARASI_SANIYE


class TestNezaketSirasi:
    """Alan adı başına tek sıra — `docs/kanit/VERI_TOPLAMA_ETIGI.md` beyanı."""

    def test_ayni_alana_ard_arda_istekte_beklenir(self) -> None:
        bekci = MagicMock(spec=RobotsBekcisi)
        bekci.bekleme_suresi.return_value = 2.0
        sira = NezaketSirasi(bekci)

        with patch("time.sleep") as uyu:
            sira.bekle("https://a.com/1")
            sira.bekle("https://a.com/2")

        assert uyu.call_count == 1
        assert uyu.call_args[0][0] == pytest.approx(2.0, abs=0.1)

    def test_farkli_alanlar_birbirini_bekletmez(self) -> None:
        bekci = MagicMock(spec=RobotsBekcisi)
        bekci.bekleme_suresi.return_value = 2.0
        sira = NezaketSirasi(bekci)

        with patch("time.sleep") as uyu:
            sira.bekle("https://a.com/1")
            sira.bekle("https://b.com/1")

        assert uyu.call_count == 0

    def test_bekleme_suresi_robotstan_gelir(self) -> None:
        """Süre uydurulmuyor: robots.txt ne diyorsa o (alt sınırla birlikte)."""
        bekci = MagicMock(spec=RobotsBekcisi)
        bekci.bekleme_suresi.return_value = 7.0
        sira = NezaketSirasi(bekci)

        with patch("time.sleep") as uyu:
            sira.bekle("https://a.com/1")
            sira.bekle("https://a.com/2")

        assert uyu.call_args[0][0] == pytest.approx(7.0, abs=0.1)


class TestKayitYazOku:
    def _kayit(self) -> HamKayit:
        return HamKayit(
            banka_kodu="0203",
            banka_adi="Test",
            url="https://test.com",
            cekim_tarihi=datetime.now(),
            http_durum=200,
            baslik="Test",
            ham_html="<html></html>",
            govde_metin="test",
        )

    def test_kaydi_yaz_json_ve_html_olusturur(self, tmp_path: Path) -> None:
        yol = kaydi_yaz(self._kayit(), dizin=tmp_path)
        assert yol.exists()
        assert yol.suffix == ".json"
        assert yol.with_suffix(".html").exists()

    def test_ham_html_json_icinde_tekrarlanmaz(self, tmp_path: Path) -> None:
        """HTML ayrı dosyada: JSON'u şişirirse `data/raw` okunamaz hâle gelir."""
        yol = kaydi_yaz(self._kayit(), dizin=tmp_path)
        assert "ham_html" not in yol.read_text(encoding="utf-8")

    def test_ham_kayitlari_oku_geri_yukler(self, tmp_path: Path) -> None:
        kaydi_yaz(self._kayit(), dizin=tmp_path)

        kayitlar = list(ham_kayitlari_oku(dizin=tmp_path))
        assert len(kayitlar) == 1
        assert kayitlar[0].banka_kodu == "0203"
        assert kayitlar[0].ham_html == "<html></html>"


def test_kaldirilan_jenerik_toplayici_anlatan_hata_verir() -> None:
    """Eski `Toplayici` içe aktarması sessiz `AttributeError` ile bitmesin."""
    import src.collector.toplayici as modul

    with pytest.raises(AttributeError, match="kaldırıldı"):
        _ = modul.Toplayici
