"""Tetikleyici + dinleyici sözleşmesi.

AĞ KULLANILMAZ: `httpx.MockTransport` ile sahte sunucu kurulur. Sınanan şey
banka sitesi değil dinleyicinin kararı — neyi «değişti» sayıyor, neyi
saymıyor, tabanı ne zaman kuruyor, nezaketi atlıyor mu.

Gerçek bankalarda ölçüm ayrıca yapıldı (27 Ağu, 18 URL / 9 banka):
ilk koşu 18 `ilk_kayit` + 0 değişiklik iddiası, ikinci koşu 18 `degismedi`
+ 0 yanlış alarm. Ayrıntı `docs/kararlar/018-tetikleyici-dinleyici.md`.
"""

from __future__ import annotations

from datetime import datetime, time
from pathlib import Path

import httpx
import pytest

from src.izleme import IzlemeHedefi, Tetikleyici, tazelik_denetle
from src.izleme.dinleyici import icerik_ozeti, taban_oku, taban_yaz
from src.izleme.tetikleyici import KAMPANYA_SAATLERI

GOVDE_A = "<html><body><p>" + ("Kâr payı oranı %1,89 ve 120 ay vade. " * 20) + "</p></body></html>"
GOVDE_B = "<html><body><p>" + ("Kâr payı oranı %2,49 ve 60 ay vade. " * 20) + "</p></body></html>"

HEDEF = IzlemeHedefi(banka_kodu="0203", banka_adi="Albaraka", url="https://banka.test/k/1")


class SahteBekci:
    """robots kapısı — testte ağa çıkmadan karar verir."""

    def __init__(self, izinli: bool = True) -> None:
        self.izinli = izinli

    def izinli_mi(self, url: str) -> bool:
        return self.izinli

    def bekleme_suresi(self, url: str) -> float:
        return 0.0


class SahteSira:
    """Nezaket sırası — testte beklemez ama BEKLENDİĞİNİ kaydeder."""

    def __init__(self) -> None:
        self.beklenen: list[str] = []

    def bekle(self, url: str) -> None:
        self.beklenen.append(url)


def _tasiyici(govde: str = GOVDE_A, *, durum: int = 200, basliklar: dict | None = None):
    def _yanit(istek: httpx.Request) -> httpx.Response:
        return httpx.Response(durum, text=govde, headers=basliklar or {})

    return httpx.MockTransport(_yanit)


def _kos(tmp_path: Path, tasiyici, *, hedefler=None, bekci=None, sira=None, **kwargs):
    return tazelik_denetle(
        hedefler if hedefler is not None else [HEDEF],
        taban_yolu=tmp_path / "tazelik.json",
        bekci=bekci or SahteBekci(),
        sira=sira or SahteSira(),
        transport=tasiyici,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Taban çizgisi
# ---------------------------------------------------------------------------


class TestTabanCizgisi:
    def test_ilk_kosu_degisiklik_iddia_etmez(self, tmp_path: Path) -> None:
        """İlk yoklama taban kurar. «Değişti» demek için karşılaştıracak şey yok."""
        ozet = _kos(tmp_path, _tasiyici())
        assert ozet.ilk_kayit == 1
        assert ozet.degisti == 0
        assert ozet.degismedi == 0
        assert ozet.taban_kuruldu_mu is True

    def test_ikinci_kosu_ayni_icerikte_degismedi_der(self, tmp_path: Path) -> None:
        _kos(tmp_path, _tasiyici())
        ozet = _kos(tmp_path, _tasiyici())
        assert ozet.degismedi == 1
        assert ozet.degisti == 0
        assert ozet.ilk_kayit == 0

    def test_icerik_degisince_yakalanir(self, tmp_path: Path) -> None:
        """Asıl iş bu: gerçek değişiklik görülmeli."""
        _kos(tmp_path, _tasiyici(GOVDE_A))
        ozet = _kos(tmp_path, _tasiyici(GOVDE_B))
        assert ozet.degisti == 1
        assert ozet.degismedi == 0
        assert len(ozet.degisenler) == 1
        assert ozet.degisenler[0].url == HEDEF.url

    def test_degisiklik_zamani_ayri_tutulur(self, tmp_path: Path) -> None:
        """«Ne zaman denetlendi» ile «ne zaman değişti» aynı şey değil."""
        yol = tmp_path / "tazelik.json"
        _kos(tmp_path, _tasiyici(GOVDE_A))
        _kos(tmp_path, _tasiyici(GOVDE_B))
        kayit = taban_oku(yol)[HEDEF.url]
        assert kayit.degisiklik_zamani  # değişiklik görüldü
        _kos(tmp_path, _tasiyici(GOVDE_B))
        sonraki = taban_oku(yol)[HEDEF.url]
        assert sonraki.yoklama_zamani  # yine denetlendi
        assert sonraki.degisiklik_zamani == kayit.degisiklik_zamani  # ama değişmedi

    def test_taban_diske_yazilir(self, tmp_path: Path) -> None:
        _kos(tmp_path, _tasiyici())
        assert (tmp_path / "tazelik.json").is_file()
        assert HEDEF.url in taban_oku(tmp_path / "tazelik.json")

    def test_bozuk_taban_kosuyu_dusurmez(self, tmp_path: Path) -> None:
        """Bozuk JSON «her şey değişmiş» demek yerine tabanı sıfırdan kurar."""
        yol = tmp_path / "tazelik.json"
        yol.write_text("{bozuk json", encoding="utf-8")
        ozet = _kos(tmp_path, _tasiyici())
        assert ozet.ilk_kayit == 1
        assert ozet.degisti == 0


# ---------------------------------------------------------------------------
# HTTP doğrulayıcı kademesi
# ---------------------------------------------------------------------------


class TestDogrulayici:
    def test_304_govde_indirmeden_degismedi_der(self, tmp_path: Path) -> None:
        _kos(tmp_path, _tasiyici(GOVDE_A, basliklar={"ETag": '"abc"'}))
        ozet = _kos(tmp_path, _tasiyici("", durum=304, basliklar={"ETag": '"abc"'}))
        assert ozet.degismedi == 1
        assert ozet.dogrulayici_ile == 1

    def test_304_ozeti_bozmaz(self, tmp_path: Path) -> None:
        """Gövde inmediği için özet ESKİSİ korunmalı — boş özet yazılırsa bir
        sonraki koşu sayfayı «ilk kayıt» sanardı."""
        yol = tmp_path / "tazelik.json"
        _kos(tmp_path, _tasiyici(GOVDE_A, basliklar={"ETag": '"abc"'}))
        beklenen = taban_oku(yol)[HEDEF.url].ozet
        _kos(tmp_path, _tasiyici("", durum=304, basliklar={"ETag": '"abc"'}))
        assert taban_oku(yol)[HEDEF.url].ozet == beklenen

    def test_dogrulayici_yoksa_icerik_ozetine_dusulur(self, tmp_path: Path) -> None:
        """9 bankanın 7'sinde doğrulayıcı yok — bu yol asıl yoldur."""
        _kos(tmp_path, _tasiyici(GOVDE_A))
        olaylar: list = []
        _kos(tmp_path, _tasiyici(GOVDE_A), ilerleme=olaylar.append)
        assert olaylar[0].yontem == "icerik_ozeti"

    def test_ilk_kosuda_kosullu_baslik_gonderilmez(self, tmp_path: Path) -> None:
        gorulen: list = []

        def _yanit(istek: httpx.Request) -> httpx.Response:
            gorulen.append(dict(istek.headers))
            return httpx.Response(200, text=GOVDE_A)

        _kos(tmp_path, httpx.MockTransport(_yanit))
        assert "if-none-match" not in gorulen[0]
        assert "if-modified-since" not in gorulen[0]


# ---------------------------------------------------------------------------
# Nezaket ve kenar durumlar
# ---------------------------------------------------------------------------


class TestNezaketVeKenarDurumlar:
    def test_robots_reddi_cekmeyi_engeller(self, tmp_path: Path) -> None:
        """Denetim de bir ziyarettir — robots kapısı burada da işler."""
        cagrildi: list = []

        def _yanit(istek: httpx.Request) -> httpx.Response:
            cagrildi.append(istek.url)
            return httpx.Response(200, text=GOVDE_A)

        ozet = _kos(tmp_path, httpx.MockTransport(_yanit), bekci=SahteBekci(izinli=False))
        assert ozet.robots_reddi == 1
        assert ozet.denetlenen == 0
        assert cagrildi == []  # hiç istek gitmedi

    def test_nezaket_sirasi_her_url_icin_beklenir(self, tmp_path: Path) -> None:
        sira = SahteSira()
        _kos(tmp_path, _tasiyici(), sira=sira)
        assert sira.beklenen == [HEDEF.url]

    def test_ag_hatasi_kosuyu_dusurmez(self, tmp_path: Path) -> None:
        def _yanit(istek: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("ag yok")

        ozet = _kos(tmp_path, httpx.MockTransport(_yanit))
        assert ozet.erisilemedi == 1
        assert ozet.degisti == 0

    def test_sunucu_hatasi_degisiklik_sayilmaz(self, tmp_path: Path) -> None:
        """500 dönen sayfa «değişti» DEĞİLDİR — yanlış alarm üretirdi."""
        _kos(tmp_path, _tasiyici(GOVDE_A))
        ozet = _kos(tmp_path, _tasiyici("hata", durum=500))
        assert ozet.erisilemedi == 1
        assert ozet.degisti == 0

    def test_iptal_kalan_hedefleri_atlar(self, tmp_path: Path) -> None:
        hedefler = [
            IzlemeHedefi(banka_kodu="0203", banka_adi="A", url=f"https://banka.test/k/{i}")
            for i in range(5)
        ]
        ozet = _kos(tmp_path, _tasiyici(), hedefler=hedefler, iptal=lambda: True)
        assert ozet.denetlenen == 0
        assert ozet.iptal_edildi is True

    def test_iptal_edilse_de_taban_yazilir(self, tmp_path: Path) -> None:
        """Yapılan ziyaretler boşa gitmesin — nezaket bedeli ödendi."""
        hedefler = [
            IzlemeHedefi(banka_kodu="0203", banka_adi="A", url=f"https://banka.test/k/{i}")
            for i in range(4)
        ]
        sayac = {"n": 0}

        def _iptal() -> bool:
            sayac["n"] += 1
            return sayac["n"] > 2

        ozet = _kos(tmp_path, _tasiyici(), hedefler=hedefler, iptal=_iptal)
        assert ozet.denetlenen == 2
        assert len(taban_oku(tmp_path / "tazelik.json")) == 2

    def test_bos_hedef_listesi_kirilmaz(self, tmp_path: Path) -> None:
        ozet = _kos(tmp_path, _tasiyici(), hedefler=[])
        assert ozet.denetlenen == 0

    def test_ilerleme_verilmezse_kosar(self, tmp_path: Path) -> None:
        assert _kos(tmp_path, _tasiyici()).ilk_kayit == 1

    def test_uretim_verisine_dokunulmaz(self, tmp_path: Path) -> None:
        """Dinleyici yalnız taban dosyasına yazar."""
        _kos(tmp_path, _tasiyici())
        assert {y.name for y in tmp_path.iterdir()} == {"tazelik.json"}


# ---------------------------------------------------------------------------
# İçerik özeti
# ---------------------------------------------------------------------------


class TestIcerikOzeti:
    def test_bosluk_farki_ozeti_degistirmez(self) -> None:
        """Satır sonu / girinti farkı «değişti» saydırmamalı."""
        assert icerik_ozeti("bir  iki\nüç") == icerik_ozeti("bir iki üç")
        assert icerik_ozeti(" bir iki üç ") == icerik_ozeti("bir\tiki\nüç")

    def test_eksik_bosluk_ozeti_degistirmez(self) -> None:
        """ÖLÇÜLEN vaka: Albaraka aynı sayfayı iki biçimde veriyor, fark tek boşluk.

        `%3,19 'danbaşlayan` ↔ `%3,19 'dan başlayan`. Boşluk DİZİSİNİ daraltmak
        bunu çözmez — eksik boşluk eklenemez. Bu yüzden özet bütün boşlukları atar.
        """
        assert icerik_ozeti("%3,19 'danbaşlayan kâr oranı") == icerik_ozeti(
            "%3,19 'dan başlayan kâr oranı"
        )

    def test_gercek_degisiklik_bosluktan_bagimsiz_yakalanir(self) -> None:
        """Boşluk atmak gerçek değişikliği KÖRLEŞTİRMEMELİ."""
        assert icerik_ozeti("%1,89 kâr payı 120 ay") != icerik_ozeti(
            "%2,49 kâr payı 120 ay"
        )
        assert icerik_ozeti("%1,89 kâr payı 120 ay") != icerik_ozeti(
            "%1,89 kâr payı 60 ay"
        )

    def test_gercek_fark_ozeti_degistirir(self) -> None:
        assert icerik_ozeti("%1,89 kâr payı") != icerik_ozeti("%2,49 kâr payı")

    def test_bos_metin_kirilmaz(self) -> None:
        assert len(icerik_ozeti("")) == 64


def test_taban_yazma_atomik(tmp_path: Path) -> None:
    """Geçici dosya bırakılmamalı — bir sonraki koşu onu taban sanmasın."""
    yol = tmp_path / "tazelik.json"
    taban_yaz({}, yol)
    assert yol.is_file()
    assert not list(tmp_path.glob("*.tmp"))


# ---------------------------------------------------------------------------
# Tetikleyici — tanımlı ama kurulu DEĞİL
# ---------------------------------------------------------------------------


class TestTetikleyici:
    def test_varsayilan_olarak_kurulu_degildir(self) -> None:
        """Bu test bilerek var: `kurulu=True` bir karardır, kaza olamaz.

        Kurulu bir zamanlayıcı donmuş ölçüm verisine yazabilir; gerekçe
        `src/izleme/tetikleyici.py` başlığında.
        """
        assert Tetikleyici().kurulu is False

    def test_saatler_mentor_geri_bildiriminden(self) -> None:
        assert KAMPANYA_SAATLERI == (time(8, 0), time(17, 0), time(0, 0))

    @pytest.mark.parametrize(
        ("simdi", "beklenen"),
        [
            ("2026-08-27T07:30", "2026-08-27T08:00"),
            ("2026-08-27T08:00", "2026-08-27T17:00"),  # tam anında BİR SONRAKİ
            ("2026-08-27T12:00", "2026-08-27T17:00"),
            ("2026-08-27T18:00", "2026-08-28T00:00"),
            ("2026-08-27T23:59", "2026-08-28T00:00"),
        ],
    )
    def test_sonraki_calisma(self, simdi: str, beklenen: str) -> None:
        t = Tetikleyici()
        assert t.sonraki_calisma(datetime.fromisoformat(simdi)) == datetime.fromisoformat(
            beklenen
        )

    def test_onceki_calisma_gun_devrini_gecer(self) -> None:
        t = Tetikleyici()
        assert t.onceki_calisma(datetime(2026, 8, 27, 7, 30)) == datetime(2026, 8, 27, 0, 0)

    def test_hic_kosulmamis_veri_gecikmis_sayilir(self) -> None:
        assert Tetikleyici().gecikmis_mi(None, datetime(2026, 8, 27, 12, 0)) is True

    def test_gecikme_tespiti(self) -> None:
        t = Tetikleyici()
        simdi = datetime(2026, 8, 27, 12, 0)
        assert t.gecikmis_mi(datetime(2026, 8, 27, 7, 0), simdi) is True  # 08:00 kaçtı
        assert t.gecikmis_mi(datetime(2026, 8, 27, 9, 0), simdi) is False  # 08:00 sonrası

    def test_cron_satiri_uretilir(self) -> None:
        """Ürünleşince kurulacak satır elde — kurulum kararı operatörün."""
        assert Tetikleyici().cron_satiri() == "0 0,8,17 * * * make tazelik"

    def test_bos_takvim_reddedilir(self) -> None:
        """Boş takvim, hiç koşmayan bir işi «zamanlandı» gibi gösterirdi."""
        with pytest.raises(ValueError, match="en az bir saat"):
            Tetikleyici(saatler=())
