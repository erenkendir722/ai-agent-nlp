"""Keşif sözleşmesi (G-19) — «elimizde olmayan yeni kampanya var mı?».

TARAYICI AÇILMAZ: `kaziyici_sinifi` ve `surucu_olustur` yamanır, sahte
kazıyıcı sabit bir URL listesi döndürür. Sınanan şey banka sitesi değil
diff'in kararı — neyi YENİ sayıyor, neyi KALDIRILMIŞ sayıyor, hangi tabana
karşı bakıyor.

Gerçek ağda ayrıca ölçüldü (27 Ağu): Hayat Finans 9 sn / 13 adres / 1 gerçek
yeni kampanya · Albaraka 81 sn / 48 adres. Ayrıntı
`docs/kararlar/019-yeni-kampanya-kesfi.md`.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.izleme.kesif import (
    envanter_oku,
    kampanya_urli_mi,
    kesif_kos,
    kesif_taban_oku,
    kesif_taban_yaz,
    url_normalize,
)
from src.schema import Banka

BANKA_KODU = "0203"


def _banka(**degisiklik: Any) -> Banka:
    ayar: dict[str, Any] = {
        "kod": BANKA_KODU,
        "ad": "Deneme Katılım Bankası A.Ş.",
        "kisa_ad": "Deneme",
        "site": "https://deneme.com.tr",
        "durum": "faal",
        "kod_dogrulandi": True,
        "seed_urls": ["https://deneme.com.tr/kampanyalar"],
        "url_desenleri": ["/kampanya"],
        "robots_kontrol": True,
    }
    ayar.update(degisiklik)
    return Banka(**ayar)


def _envanter_yaz(dizin: Path, urller: list[str], kod: str = BANKA_KODU) -> None:
    banka_dizin = dizin / kod
    banka_dizin.mkdir(parents=True, exist_ok=True)
    for i, url in enumerate(urller):
        (banka_dizin / f"{kod}-{i:04d}.json").write_text(
            json.dumps(
                {
                    "banka_kodu": kod,
                    "banka_adi": "Deneme Katılım Bankası A.Ş.",
                    "url": url,
                    "cekim_tarihi": datetime(2026, 8, 26).isoformat(),
                    "http_durum": 200,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )


def _kos(tmp_path: Path, bulunan: list[str], *, envanter: list[str] | None = None,
         taban_adi: str = "kesif.json", **kwargs):
    """Sahte kazıyıcı ile keşif koşar; gerçek tarayıcı AÇILMAZ."""
    ham = tmp_path / "raw"
    if envanter is not None:
        _envanter_yaz(ham, envanter)
    ham.mkdir(parents=True, exist_ok=True)

    class SahteKaziyici:
        def __init__(self, banka, surucu, bekleme, **_: object) -> None:
            self.banka = banka

        def kampanya_urlleri(self) -> list[str]:
            return list(bulunan)

    with (
        patch("src.collector.tarayici.surucu_olustur",
              return_value=(MagicMock(), MagicMock())),
        patch("src.collector.kaziyicilar.kaziyici_sinifi", return_value=SahteKaziyici),
    ):
        return kesif_kos(
            [_banka()], dizin=ham, taban_yolu=tmp_path / taban_adi, **kwargs
        )


# ---------------------------------------------------------------------------
# URL normalizasyonu
# ---------------------------------------------------------------------------


class TestUrlNormalize:
    def test_fragment_atilir(self) -> None:
        assert url_normalize("https://a.com/k#bolum") == url_normalize("https://a.com/k")

    def test_son_slash_tekillestirilir(self) -> None:
        assert url_normalize("https://a.com/k/") == url_normalize("https://a.com/k")

    def test_sema_ve_www_tekillestirilir(self) -> None:
        assert url_normalize("http://www.a.com/k") == url_normalize("https://a.com/k")

    def test_izleme_parametresi_atilir(self) -> None:
        assert url_normalize("https://a.com/k?utm_source=mail") == url_normalize(
            "https://a.com/k"
        )
        assert url_normalize("https://a.com/k?gclid=123&fbclid=9") == url_normalize(
            "https://a.com/k"
        )

    def test_anlamli_parametre_KORUNUR(self) -> None:
        """`?slug=` ve `?page=` sayfayı belirliyor — atılırsa farklı sayfalar birleşir."""
        assert "slug=bireysel" in url_normalize("https://a.com/k?slug=bireysel")
        assert url_normalize("https://a.com/k?slug=a") != url_normalize(
            "https://a.com/k?slug=b"
        )

    def test_parametre_sirasi_onemsiz(self) -> None:
        assert url_normalize("https://a.com/k?b=2&a=1") == url_normalize(
            "https://a.com/k?a=1&b=2"
        )

    def test_yol_buyuk_kucuk_harfi_KORUNUR(self) -> None:
        """Sunucu ayırt edebilir; birleştirmek veri kaybıdır."""
        assert url_normalize("https://a.com/Kampanya") != url_normalize(
            "https://a.com/kampanya"
        )

    def test_bos_girdi_kirilmaz(self) -> None:
        assert url_normalize("") == ""
        assert url_normalize("   ") == ""


class TestKampanyaUrliMi:
    @pytest.mark.parametrize(
        "url",
        [
            "https://a.com/tr/kampanyalar",
            "https://a.com/tr/kampanyalar/",
            "https://a.com/tr/kampanya",
            "https://a.com/tr/kampanyalar?page=3",
            "https://a.com/tr/kampanyalar?slug=gecmis-kampanyalar",
            "https://a.com/tr/gecmis-kampanyalar/x",
            # Gerçek örnek: albaraka.com.tr/tr/kampanyalar?slug=bireysel —
            # yolun sonu liste adı olduğu için parametre ne olursa olsun liste.
            "https://a.com/tr/kampanyalar?slug=bireysel",
        ],
    )
    def test_liste_ve_arsiv_elenir(self, url: str) -> None:
        assert kampanya_urli_mi(url) is False

    @pytest.mark.parametrize(
        "url",
        [
            "https://a.com/tr/kampanyalar/detay/yaz-kampanyasi",
            "https://a.com/kampanyalar/biz-kart-ile-okula-donus",
            "https://a.com/tr/kampanyalar/detay/x?slug=bireysel",
        ],
    )
    def test_detay_sayfasi_elenmez(self, url: str) -> None:
        assert kampanya_urli_mi(url) is True

    def test_bos_girdi_kirilmaz(self) -> None:
        assert kampanya_urli_mi("") is False


# ---------------------------------------------------------------------------
# Envanter ve taban
# ---------------------------------------------------------------------------


class TestEnvanterVeTaban:
    def test_envanter_banka_koduna_gore_okunur(self, tmp_path: Path) -> None:
        _envanter_yaz(tmp_path, ["https://a.com/k/1", "https://a.com/k/2"])
        envanter = envanter_oku(tmp_path)
        assert set(envanter) == {BANKA_KODU}
        assert len(envanter[BANKA_KODU]) == 2

    def test_envanter_normalize_edilir(self, tmp_path: Path) -> None:
        """Aynı sayfa iki biçimde kayıtlıysa tek URL sayılmalı."""
        _envanter_yaz(tmp_path, ["https://www.a.com/k/1", "https://a.com/k/1/"])
        assert len(envanter_oku(tmp_path)[BANKA_KODU]) == 1

    def test_olmayan_dizin_kirilmaz(self, tmp_path: Path) -> None:
        assert envanter_oku(tmp_path / "yok") == {}

    def test_taban_yazilip_okunur(self, tmp_path: Path) -> None:
        yol = tmp_path / "kesif.json"
        kesif_taban_yaz({BANKA_KODU: {"https://a.com/k/1"}}, yol)
        assert kesif_taban_oku(yol) == {BANKA_KODU: {"https://a.com/k/1"}}

    def test_taban_yazma_atomik(self, tmp_path: Path) -> None:
        kesif_taban_yaz({}, tmp_path / "kesif.json")
        assert not list(tmp_path.glob("*.tmp"))

    def test_bozuk_taban_kosuyu_dusurmez(self, tmp_path: Path) -> None:
        yol = tmp_path / "kesif.json"
        yol.write_text("{bozuk", encoding="utf-8")
        assert kesif_taban_oku(yol) == {}


# ---------------------------------------------------------------------------
# Diff — asıl iş
# ---------------------------------------------------------------------------


class TestYeniKampanya:
    def test_envanterde_olmayan_adres_YENI_sayilir(self, tmp_path: Path) -> None:
        """Asıl hedef: listede olup elimizde olmayanı bulmak."""
        ozet = _kos(
            tmp_path,
            bulunan=["https://a.com/k/1", "https://a.com/k/2", "https://a.com/k/YENI"],
            envanter=["https://a.com/k/1", "https://a.com/k/2"],
        )
        (sonuc,) = ozet.sonuclar
        assert sonuc.yeni == ["https://a.com/k/YENI"]
        assert ozet.toplam_yeni == 1
        assert sonuc.bulunan == 3

    def test_hepsi_envanterdeyse_yeni_yok(self, tmp_path: Path) -> None:
        ozet = _kos(
            tmp_path,
            bulunan=["https://a.com/k/1"],
            envanter=["https://a.com/k/1"],
        )
        assert ozet.toplam_yeni == 0

    def test_yeni_normalize_edilerek_karsilastirilir(self, tmp_path: Path) -> None:
        """Aynı sayfa farklı yazımla gelirse YENİ sanılmamalı."""
        ozet = _kos(
            tmp_path,
            bulunan=["https://www.a.com/k/1/?utm_source=mail"],
            envanter=["https://a.com/k/1"],
        )
        assert ozet.toplam_yeni == 0

    def test_kirli_envanter_YENIyi_sismez(self, tmp_path: Path) -> None:
        """Envanterdeki ürün/liste sayfaları YENİ kümesini etkilemez."""
        ozet = _kos(
            tmp_path,
            bulunan=["https://a.com/k/YENI"],
            envanter=[
                "https://a.com/tr/kampanyalar",
                "https://a.com/tr/bireysel/finansmanlar",
                "https://a.com/tr/bireysel/finansmanlar/bayide-finansman",
            ],
        )
        assert ozet.toplam_yeni == 1


class TestKaldirilmis:
    def test_ilk_kosu_kaldirilmis_iddia_etmez(self, tmp_path: Path) -> None:
        """Taban yokken karşılaştıracak önceki keşif de yok."""
        ozet = _kos(tmp_path, bulunan=["https://a.com/k/1"], envanter=[])
        (sonuc,) = ozet.sonuclar
        assert sonuc.ilk_kesif is True
        assert sonuc.kaldirilmis == []
        assert ozet.taban_kuruldu_mu is True

    def test_ikinci_kosuda_dusen_adres_yakalanir(self, tmp_path: Path) -> None:
        _kos(tmp_path, bulunan=["https://a.com/k/1", "https://a.com/k/2"], envanter=[])
        ozet = _kos(tmp_path, bulunan=["https://a.com/k/1"])
        (sonuc,) = ozet.sonuclar
        assert sonuc.ilk_kesif is False
        assert sonuc.kaldirilmis == ["https://a.com/k/2"]

    def test_kaldirilmis_ENVANTERE_karsi_bakilmaz(self, tmp_path: Path) -> None:
        """ÖLÇÜLEN tuzak: envanterde ürün sayfaları var, keşif onları döndürmez.

        Envantere karşı diff alınsaydı Albaraka'da her koşuda 88 sahte
        «kaldırıldı» çıkardı (27 Ağu ölçümü).
        """
        ozet = _kos(
            tmp_path,
            bulunan=["https://a.com/k/1"],
            envanter=[
                "https://a.com/k/1",
                "https://a.com/tr/bireysel/finansmanlar/bayide-finansman",
                "https://a.com/tr/bireysel/finansmanlar/arsa-finansmani",
            ],
        )
        (sonuc,) = ozet.sonuclar
        assert sonuc.kaldirilmis == []  # ilk keşif — ve envanterden türetilmiyor
        # Bilgi sayacı bunları görüyor ama «kaldırıldı» demiyor:
        assert sonuc.envanterde_gorunmeyen == 2

    def test_bilgi_sayaci_liste_sayfalarini_saymaz(self, tmp_path: Path) -> None:
        ozet = _kos(
            tmp_path,
            bulunan=["https://a.com/k/1"],
            envanter=["https://a.com/k/1", "https://a.com/tr/kampanyalar"],
        )
        assert ozet.sonuclar[0].envanterde_gorunmeyen == 0


# ---------------------------------------------------------------------------
# Akış, olaylar, dayanıklılık
# ---------------------------------------------------------------------------


class TestAkis:
    def test_olaylar_sirayla_gelir(self, tmp_path: Path) -> None:
        olaylar: list = []
        _kos(tmp_path, bulunan=["https://a.com/k/1"], envanter=[],
             ilerleme=olaylar.append)
        assert [o.asama for o in olaylar] == ["banka_basladi", "banka_bitti"]
        assert olaylar[-1].bulunan == 1

    def test_ilerleme_verilmezse_kosar(self, tmp_path: Path) -> None:
        assert _kos(tmp_path, bulunan=["https://a.com/k/1"], envanter=[]).toplam_bulunan == 1

    def test_taban_diske_yazilir(self, tmp_path: Path) -> None:
        _kos(tmp_path, bulunan=["https://a.com/k/1"], envanter=[])
        assert kesif_taban_oku(tmp_path / "kesif.json") == {
            BANKA_KODU: {"https://a.com/k/1"}
        }

    def test_iptal_kesfi_atlar(self, tmp_path: Path) -> None:
        ozet = _kos(tmp_path, bulunan=["https://a.com/k/1"], envanter=[],
                    iptal=lambda: True)
        assert ozet.sonuclar == []
        assert ozet.iptal_edildi is True

    def test_kazıyıcı_hatasi_kosuyu_dusurmez(self, tmp_path: Path) -> None:
        """Bir banka bozulunca diğerleri etkilenmemeli — hata YUTULMAZ, raporlanır."""
        ham = tmp_path / "raw"
        ham.mkdir(parents=True, exist_ok=True)

        class PatlayanKaziyici:
            def __init__(self, *a: object, **k: object) -> None:
                pass

            def kampanya_urlleri(self) -> list[str]:
                raise RuntimeError("liste yüklenemedi")

        with (
            patch("src.collector.tarayici.surucu_olustur",
                  return_value=(MagicMock(), MagicMock())),
            patch("src.collector.kaziyicilar.kaziyici_sinifi",
                  return_value=PatlayanKaziyici),
        ):
            ozet = kesif_kos([_banka()], dizin=ham, taban_yolu=tmp_path / "k.json")
        (sonuc,) = ozet.sonuclar
        assert "liste yüklenemedi" in sonuc.hata
        assert ozet.hatali_banka == 1
        assert ozet.toplam_yeni == 0

    def test_kaziyicisi_olmayan_banka_raporlanir(self, tmp_path: Path) -> None:
        ham = tmp_path / "raw"
        ham.mkdir(parents=True, exist_ok=True)
        with (
            patch("src.collector.tarayici.surucu_olustur",
                  return_value=(MagicMock(), MagicMock())),
            patch("src.collector.kaziyicilar.kaziyici_sinifi", return_value=None),
        ):
            ozet = kesif_kos([_banka()], dizin=ham, taban_yolu=tmp_path / "k.json")
        assert "kazıyıcısı yok" in ozet.sonuclar[0].hata

    def test_surucu_her_halukarda_kapatilir(self, tmp_path: Path) -> None:
        """Yarıda kalan Chrome süreci makinede asılı kalmamalı."""
        ham = tmp_path / "raw"
        ham.mkdir(parents=True, exist_ok=True)
        surucu = MagicMock()
        with (
            patch("src.collector.tarayici.surucu_olustur",
                  return_value=(surucu, MagicMock())),
            patch("src.collector.kaziyicilar.kaziyici_sinifi", return_value=None),
        ):
            kesif_kos([_banka()], dizin=ham, taban_yolu=tmp_path / "k.json")
        surucu.quit.assert_called_once()

    def test_faal_olmayan_banka_kesfedilmez(self, tmp_path: Path) -> None:
        ham = tmp_path / "raw"
        ham.mkdir(parents=True, exist_ok=True)
        with patch("src.collector.tarayici.surucu_olustur") as sahte:
            ozet = kesif_kos(
                [_banka(durum="faaliyete_gecmedi", seed_urls=[])],
                dizin=ham, taban_yolu=tmp_path / "k.json",
            )
        assert ozet.sonuclar == []
        sahte.assert_not_called()  # tarayıcı hiç açılmadı


class TestOzet:
    def test_toplamlar_hesaplanir(self, tmp_path: Path) -> None:
        ozet = _kos(
            tmp_path,
            bulunan=["https://a.com/k/1", "https://a.com/k/2"],
            envanter=["https://a.com/k/1"],
        )
        assert ozet.toplam_bulunan == 2
        assert ozet.toplam_yeni == 1
        assert ozet.sure >= 0  # Windows zamanlayıcısı 0,0 dönebilir

    def test_bos_kosu_kirilmaz(self, tmp_path: Path) -> None:
        ozet = _kos(tmp_path, bulunan=[], envanter=[])
        assert ozet.toplam_bulunan == 0
        assert ozet.toplam_yeni == 0
