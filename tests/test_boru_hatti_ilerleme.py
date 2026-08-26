"""`cikarim_kos` sözleşmesi — olay akışı, ölçülen sayaçlar, iptal, hata dayanımı.

Hepsi `yalniz_kural=True` ile koşuyor: LLM katmanı kapalı olduğu için AĞ
GEREKMEZ ve sayılar koşudan koşuya oynamaz. (CLAUDE.md: EVREN bayt düzeyinde
deterministik değil; ilerleme sözleşmesini oynayan bir sayıya bağlamak testi
kırılgan yapardı.)

Veritabanı her testte `tmp_path` altında ayrı bir sqlite dosyası — üretim
veritabanına ve ablasyon dizinine dokunulmaz.
"""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path

import pytest

from src.boru_hatti import CikarimAyarlari, CikarimOzeti, cikarim_kos, demo_veritabani
from src.depolama import VERITABANI_URL
from src.extraction.uzlastirici import kampanya_cikar
from src.schema import HamKayit

METIN = (
    "Konut finansmanı kampanyamız kapsamında %1,89 kâr payı oranıyla 120 aya varan "
    "vade seçenekleri sunuyoruz. 500.000 TL'ye kadar kullanabileceğiniz bu "
    "finansmanda tahsis ücreti alınmamaktadır. Kampanya 31.12.2026 tarihine "
    "kadar geçerlidir."
)


def _kayit(sira: int) -> HamKayit:
    return HamKayit(
        banka_kodu="0203",
        banka_adi="Deneme Katılım Bankası A.Ş.",
        url=f"https://deneme.com.tr/kampanya/{sira}",
        cekim_tarihi=datetime(2026, 8, 26, 12, 0, 0),
        http_durum=200,
        baslik=f"Kampanya {sira}",
        ham_html="<html></html>",
        govde_metin=METIN,
    )


def _url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'deneme.db'}"


KURAL = CikarimAyarlari(yalniz_kural=True)


@pytest.fixture
def tek_isci(monkeypatch: pytest.MonkeyPatch) -> None:
    """Öbek sınırı deterministik olsun diye tek işçi.

    16 işçide `havuz.map` tüm işleri aynı anda gönderir; «kaçıncı kayıtta
    iptal edildi» sorusunun tekrarlanabilir bir cevabı olmaz.
    """
    monkeypatch.setenv("CIKARIM_ISCI", "1")


# ---------------------------------------------------------------------------
# Olay akışı
# ---------------------------------------------------------------------------


class TestOlayAkisi:
    def test_olaylar_sirayla_gelir(self, tmp_path: Path) -> None:
        olaylar: list = []
        cikarim_kos(
            [_kayit(i) for i in range(3)], KURAL, url=_url(tmp_path),
            ilerleme=olaylar.append,
        )
        asamalar = [o.asama for o in olaylar]
        assert asamalar[0] == "basladi"
        assert asamalar[-1] == "bitti"
        assert asamalar.count("kayit") == 3
        assert "ara_kayit" in asamalar

    def test_kayit_olayi_olculen_degerleri_tasir(self, tmp_path: Path) -> None:
        """Doluluk, güven ve süre ÖLÇÜLEN değerlerdir — animasyon bunlardan beslenir."""
        olaylar: list = []
        cikarim_kos([_kayit(0)], KURAL, url=_url(tmp_path), ilerleme=olaylar.append)
        (kayit_olayi,) = [o for o in olaylar if o.asama == "kayit"]

        beklenen, _ = kampanya_cikar(_kayit(0), llm_kullan=False)
        assert kayit_olayi.doluluk == pytest.approx(beklenen.doluluk_orani())
        assert kayit_olayi.guven == pytest.approx(beklenen.ortalama_guven())
        assert kayit_olayi.sure > 0
        assert kayit_olayi.sira == 1
        assert kayit_olayi.toplam == 1
        assert kayit_olayi.url == _kayit(0).url

    def test_ilerleme_verilmezse_kosu_calisir(self, tmp_path: Path) -> None:
        """CLI yolu geri çağrı vermiyor — `None` kontrolü atlanırsa orası kırılırdı."""
        ozet = cikarim_kos([_kayit(0)], KURAL, url=_url(tmp_path))
        assert ozet.kayit_sayisi == 1

    def test_bos_kayit_listesi_kirilmaz(self, tmp_path: Path) -> None:
        ozet = cikarim_kos([], KURAL, url=_url(tmp_path))
        assert ozet.kayit_sayisi == 0
        assert ozet.saniye_basina_kayit == 0.0


class TestCanliSayaclar:
    """Katman çubukları koşu SÜRERKEN dolmalı — bitişi beklememeli."""

    def test_kayit_olayi_kosan_katman_toplamlarini_tasir(self, tmp_path: Path) -> None:
        olaylar: list = []
        cikarim_kos(
            [_kayit(i) for i in range(3)], KURAL, url=_url(tmp_path),
            ilerleme=olaylar.append,
        )
        kayitlar = [o for o in olaylar if o.asama == "kayit"]
        assert len(kayitlar) == 3
        # KOŞAN TOPLAM: azalmamalı ve sonuncusu özetle birebir tutmalı.
        kurallar = [o.kural for o in kayitlar]
        assert kurallar == sorted(kurallar)
        assert kurallar[0] > 0  # ilk kayıtta bile ölçülmüş bir değer var

    def test_son_kayit_olayi_ozetle_tutar(self, tmp_path: Path) -> None:
        olaylar: list = []
        ozet = cikarim_kos(
            [_kayit(i) for i in range(4)], KURAL, url=_url(tmp_path),
            ilerleme=olaylar.append,
        )
        son = [o for o in olaylar if o.asama == "kayit"][-1]
        assert son.kural == ozet.kural_alan_sayisi
        assert son.llm == ozet.llm_alan_sayisi
        assert son.hibrit == ozet.hibrit_alan_sayisi

    def test_olaylar_kayit_bitince_gonderilir(self, tmp_path: Path) -> None:
        """Olay, öbek tamamlanmadan gelmeli — arayüz koşu boyunca donuk kalmasın.

        Ölçüm: `havuz.map` sonuçları girdi sırasında verdiği için tüketici
        döngüsünden gönderilen olaylar öbek sonunda tek seferde düşüyordu.
        Burada ilk olayın SON kaydın çıkarımı bitmeden geldiği sınanır.
        """
        yavas_bitti = threading.Event()
        ilk_olay = threading.Event()
        import src.boru_hatti as modul

        gercek = modul.kampanya_cikar

        def _son_kayit_yavas(kayit, **kwargs):
            if kayit.url.endswith("/4"):
                # İlk olay gelene dek son kaydı bekletiyoruz: olay gelmezse
                # test zaman aşımına düşmesin diye üst sınır var.
                ilk_olay.wait(timeout=10)
                yavas_bitti.set()
            return gercek(kayit, **kwargs)

        monkeypatch_hedef = modul
        eski = monkeypatch_hedef.kampanya_cikar
        monkeypatch_hedef.kampanya_cikar = _son_kayit_yavas
        try:
            def _ilerleme(olay) -> None:
                if olay.asama == "kayit" and not ilk_olay.is_set():
                    # İlk «kayit» olayı geldiğinde yavaş kayıt HENÜZ bitmemiş
                    # olmalı: olay akışı öbek sonunu beklemiyor demektir.
                    assert not yavas_bitti.is_set()
                    ilk_olay.set()

            ozet = cikarim_kos(
                [_kayit(i) for i in range(5)], KURAL, url=_url(tmp_path),
                ilerleme=_ilerleme,
            )
        finally:
            monkeypatch_hedef.kampanya_cikar = eski

        assert ilk_olay.is_set(), "hiç canlı olay gelmedi"
        assert ozet.kayit_sayisi == 5


# ---------------------------------------------------------------------------
# Özet sayaçları
# ---------------------------------------------------------------------------


class TestOzet:
    def test_sayaclar_raporlarla_tutar(self, tmp_path: Path) -> None:
        kayitlar = [_kayit(i) for i in range(3)]
        ozet = cikarim_kos(kayitlar, KURAL, url=_url(tmp_path))

        beklenen_kural = sum(
            kampanya_cikar(k, llm_kullan=False)[1].kural_alan_sayisi for k in kayitlar
        )
        assert ozet.kayit_sayisi == 3
        assert ozet.kural_alan_sayisi == beklenen_kural
        assert ozet.llm_alan_sayisi == 0  # LLM katmanı kapalı
        assert ozet.hibrit_alan_sayisi == 0

    def test_yapilandirma_ve_hiz_olculur(self, tmp_path: Path) -> None:
        ozet = cikarim_kos([_kayit(i) for i in range(2)], KURAL, url=_url(tmp_path))
        assert ozet.yapilandirma == "kural"
        assert ozet.sure > 0
        assert ozet.saniye_basina_kayit == pytest.approx(ozet.sure / 2)

    def test_banka_dagilimi_sayilir(self, tmp_path: Path) -> None:
        ozet = cikarim_kos([_kayit(i) for i in range(4)], KURAL, url=_url(tmp_path))
        assert ozet.banka_dagilimi == {"Deneme Katılım Bankası A.Ş.": 4}

    def test_kanit_denetimi_kampanyalardan_hesaplanir(self, tmp_path: Path) -> None:
        kayitlar = [_kayit(i) for i in range(2)]
        ozet = cikarim_kos(kayitlar, KURAL, url=_url(tmp_path))
        assert ozet.kanit_denetimi_hatasi == sum(
            len(k.kanit_denetimi()) for k in ozet.kampanyalar
        )

    def test_veritabanina_gercekten_yazilir(self, tmp_path: Path) -> None:
        from src.depolama import tum_kayitlar

        url = _url(tmp_path)
        cikarim_kos([_kayit(i) for i in range(3)], KURAL, url=url)
        assert len(tum_kayitlar(url)) == 3


# ---------------------------------------------------------------------------
# İptal
# ---------------------------------------------------------------------------


class TestIptal:
    def test_bastan_iptal_hicbir_kayit_islemez(self, tmp_path: Path) -> None:
        ozet = cikarim_kos(
            [_kayit(i) for i in range(5)], KURAL, url=_url(tmp_path),
            iptal=lambda: True,
        )
        assert ozet.kayit_sayisi == 0
        assert ozet.iptal_edildi is True

    def test_obek_sinirinda_iptal_erken_durdurur(
        self, tmp_path: Path, tek_isci: None
    ) -> None:
        """İlk ara kayıttan sonra iptal: ikinci öbeğe hiç girilmez.

        Öbek boyu `max(ARA_KAYIT_ARALIGI, isci)` = 10; 25 kayıt üç öbeğe
        bölünür. İptal `ara_kayit` olayında kalkar, yani birinci öbek
        bittikten sonra — sonuç tam 10 kayıt olmalı.
        """
        bayrak = {"dur": False}

        def _ilerleme(olay) -> None:
            if olay.asama == "ara_kayit":
                bayrak["dur"] = True

        ozet = cikarim_kos(
            [_kayit(i) for i in range(25)], KURAL, url=_url(tmp_path),
            ilerleme=_ilerleme, iptal=lambda: bayrak["dur"],
        )
        assert ozet.kayit_sayisi == 10
        assert ozet.iptal_edildi is True

    def test_iptal_verilmezse_tamami_islenir(self, tmp_path: Path) -> None:
        ozet = cikarim_kos([_kayit(i) for i in range(3)], KURAL, url=_url(tmp_path))
        assert ozet.kayit_sayisi == 3
        assert ozet.iptal_edildi is False


# ---------------------------------------------------------------------------
# Hata dayanımı
# ---------------------------------------------------------------------------


class TestHataDayanimi:
    def test_tek_kaydin_hatasi_kosuyu_dusurmez(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bir kaydın düşmesi 590 kayıtlık koşuyu düşürmemeli."""
        import src.boru_hatti as modul

        gercek = modul.kampanya_cikar

        def _bazen_patla(kayit, **kwargs):
            if kayit.url.endswith("/1"):
                raise ValueError("uydurma çıkarım hatası")
            return gercek(kayit, **kwargs)

        monkeypatch.setattr(modul, "kampanya_cikar", _bazen_patla)

        olaylar: list = []
        ozet = cikarim_kos(
            [_kayit(i) for i in range(3)], KURAL, url=_url(tmp_path),
            ilerleme=olaylar.append,
        )
        assert ozet.kayit_sayisi == 2
        assert ozet.hatali_kayit == 1

    def test_hata_sessizce_yutulmaz_olaya_dusar(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sessiz yutma yasak: düşen kayıt arayüze bildirilmeli."""
        import src.boru_hatti as modul

        monkeypatch.setattr(
            modul, "kampanya_cikar",
            lambda kayit, **kwargs: (_ for _ in ()).throw(ValueError("patladı")),
        )
        olaylar: list = []
        ozet = cikarim_kos(
            [_kayit(0)], KURAL, url=_url(tmp_path), ilerleme=olaylar.append
        )
        hatalar = [o for o in olaylar if o.asama == "hata"]
        assert len(hatalar) == 1
        assert "patladı" in hatalar[0].mesaj
        assert ozet.kayit_sayisi == 0


# ---------------------------------------------------------------------------
# Yazma hedefi — demo alanı üretim verisine dokunmaz
# ---------------------------------------------------------------------------


class TestYazmaHedefi:
    def test_demo_veritabani_uretimden_ayridir(self) -> None:
        demo = demo_veritabani()
        assert demo != VERITABANI_URL
        assert "demo.db" in demo

    def test_ayarlar_yapilandirma_adini_uretir(self) -> None:
        assert CikarimAyarlari().yapilandirma == "hibrit"
        assert CikarimAyarlari(yalniz_kural=True).yapilandirma == "kural"
        assert CikarimAyarlari(yalniz_llm=True).yapilandirma == "llm"

    def test_ozet_varsayilanlari_bolme_hatasi_uretmez(self) -> None:
        assert CikarimOzeti().saniye_basina_kayit == 0.0
