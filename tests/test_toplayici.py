from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.collector.toplayici import (
    ISTEK_ARASI_SANIYE,
    RobotsBekcisi,
    Toplayici,
    bankalari_yukle,
    faal_bankalar,
    ham_kayitlari_oku,
    kaydi_yaz,
)
from src.schema import Banka, HamKayit

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
    def test_crawl_delay_alt_sinir_uygulanir(self, mock_get: MagicMock, mock_delay: MagicMock) -> None:
        mock_get.return_value = MagicMock(status_code=200, text="")
        mock_delay.return_value = 0.5  # Çok düşük
        bekci = RobotsBekcisi("TestBot")
        assert bekci.bekleme_suresi("https://example.com/") == ISTEK_ARASI_SANIYE


class TestToplayici:
    @pytest.fixture
    def test_banka(self) -> Banka:
        return Banka(
            kod="0203",
            ad="Test",
            kisa_ad="Test",
            site="https://test.com",
            durum="faal",
            kod_dogrulandi=True,
            seed_urls=["https://test.com/kampanyalar"],
            url_desenleri=["/kampanya"],
            robots_kontrol=False,
        )

    @patch("src.collector.toplayici.RobotsBekcisi.izinli_mi", return_value=True)
    @patch("src.collector.toplayici.RobotsBekcisi.bekleme_suresi", return_value=0.0)
    @patch("time.sleep")
    @patch("httpx.Client.get")
    def test_banka_tara_seed_url_den_kayit_uretir(
        self, mock_get: MagicMock, mock_sleep: MagicMock, mock_bekleme: MagicMock, mock_izin: MagicMock, test_banka: Banka
    ) -> None:
        html = f"<html><head><title>Test Kampanya</title></head><body><p>{'Uzun bir kampanya metni denemesi. ' * 50}</p></body></html>"
        mock_get.return_value = MagicMock(status_code=200, text=html, headers={"content-type": "text/html"})
        
        with Toplayici() as t:
            kayitlar = list(t.banka_tara(test_banka))
            
        assert len(kayitlar) == 1
        assert kayitlar[0].baslik == "Test Kampanya"
        assert "Uzun bir kampanya metni" in kayitlar[0].govde_metin

    @patch("httpx.Client.get")
    def test_kisa_govde_eleniyor(self, mock_get: MagicMock, test_banka: Banka) -> None:
        html = "<html><body><p>kısa metin</p></body></html>"
        mock_get.return_value = MagicMock(status_code=200, text=html, headers={"content-type": "text/html"})
        with Toplayici() as t:
            kayitlar = list(t.banka_tara(test_banka))
        assert len(kayitlar) == 0

    @patch("httpx.Client.get")
    def test_url_deseni_filtresi_calisiyor(self, mock_get: MagicMock, test_banka: Banka) -> None:
        html = f"<html><body><p>{'Uzun bir kampanya metni denemesi. ' * 50}</p><a href='/kampanya/1'>K1</a><a href='/diger/2'>D2</a></body></html>"
        # 1 seed, 2 alt sayfa = 3 istek simülasyonu
        mock_get.return_value = MagicMock(status_code=200, text=html, headers={"content-type": "text/html"})
        test_banka.robots_kontrol = False
        
        with Toplayici(derinlik=1) as t:
            # wait bypass
            t._nezaketle_bekle = lambda x: None  # type: ignore
            kayitlar = list(t.banka_tara(test_banka))
            
        urls = [k.url for k in kayitlar]
        assert "https://test.com/kampanyalar" in urls
        assert "https://test.com/kampanya/1" in urls
        assert "https://test.com/diger/2" not in urls


class TestKayitYazOku:
    def test_kaydi_yaz_json_ve_html_olusturur(self, tmp_path: Path) -> None:
        from datetime import datetime
        k = HamKayit(
            banka_kodu="0203", banka_adi="Test", url="https://test.com",
            cekim_tarihi=datetime.now(), http_durum=200, baslik="Test", 
            ham_html="<html></html>", govde_metin="test"
        )
        yol = kaydi_yaz(k, dizin=tmp_path)
        assert yol.exists()
        assert yol.suffix == ".json"
        assert yol.with_suffix(".html").exists()

    def test_ham_kayitlari_oku_geri_yukler(self, tmp_path: Path) -> None:
        from datetime import datetime
        k = HamKayit(
            banka_kodu="0203", banka_adi="Test", url="https://test.com",
            cekim_tarihi=datetime.now(), http_durum=200, baslik="Test", 
            ham_html="<html></html>", govde_metin="test"
        )
        kaydi_yaz(k, dizin=tmp_path)
        
        kayitlar = list(ham_kayitlari_oku(dizin=tmp_path))
        assert len(kayitlar) == 1
        assert kayitlar[0].banka_kodu == "0203"
        assert kayitlar[0].ham_html == "<html></html>"
