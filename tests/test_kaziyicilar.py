"""Kazıyıcı testleri — kayıt defteri bağı, robots kapısı, kayıt üretimi.

Gerçek tarayıcı AÇILMAZ. Selenium sürücüsü yerine `SahteSurucu` geçilir;
sınanan şey site HTML'i değil, kazıyıcının sözleşmesi: hangi URL'i çekiyor,
neyi eliyor, ürettiği `HamKayit` şemaya uyuyor mu.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.collector.kaziyicilar import KAZIYICILAR, kaziyici_sinifi
from src.collector.kaziyicilar.tom_katilim import SURESI_GECTI_KALIPLARI
from src.collector.temel_kaziyici import Ilerleme, TemelKaziyici, benzersiz
from src.collector.toplayici import EN_AZ_GOVDE_UZUNLUGU, bankalari_yukle, faal_bankalar
from src.schema import Banka

UZUN_METIN = "Kampanya kapsamında kâr payı oranı avantajlıdır. " * 20
UZUN_SAYFA = f"<html><head><title>Kampanya</title></head><body><p>{UZUN_METIN}</p></body></html>"
KISA_SAYFA = "<html><head><title>Kısa</title></head><body><p>üç kelime</p></body></html>"


# ---------------------------------------------------------------------------
# Sahte tarayıcı
# ---------------------------------------------------------------------------


class SahteSurucu:
    """Selenium `WebDriver` yerine geçen en küçük yüzey."""

    def __init__(self, sayfalar: dict[str, str] | None = None) -> None:
        self.sayfalar = sayfalar or {}
        self.gezilen: list[str] = []
        self.page_source = "<html><body></body></html>"
        self.title = "Kampanya"

    def get(self, url: str) -> None:
        self.gezilen.append(url)
        self.page_source = self.sayfalar.get(url, UZUN_SAYFA)

    def find_elements(self, *_: Any) -> list[Any]:
        return []

    def find_element(self, *_: Any) -> Any:
        raise AssertionError("bu testte öge aranmamalı")

    def execute_script(self, *_: Any) -> Any:
        return []

    def quit(self) -> None:
        pass


def sahte_bekleme() -> MagicMock:
    bekleme = MagicMock()
    bekleme.until.return_value = True
    return bekleme


class DenemeKaziyici(TemelKaziyici):
    BANKA_KODU = "0203"

    def __init__(self, *args: Any, urller: list[str] | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._urller = urller or []

    def kampanya_urlleri(self) -> list[str]:
        return self._urller


def deneme_bankasi(**degisiklik: Any) -> Banka:
    ayar: dict[str, Any] = {
        "kod": "0203",
        "ad": "Deneme Katılım Bankası A.Ş.",
        "kisa_ad": "Deneme",
        "site": "https://deneme.com.tr",
        "durum": "faal",
        "kod_dogrulandi": True,
        "seed_urls": ["https://deneme.com.tr/kampanyalar"],
        "robots_kontrol": True,
    }
    ayar.update(degisiklik)
    return Banka.model_validate(ayar)


def kaziyici_kur(
    *,
    urller: list[str],
    izinli: bool = True,
    banka: Banka | None = None,
    ilerleme: Any = None,
    sayfalar: dict[str, str] | None = None,
) -> tuple[DenemeKaziyici, SahteSurucu]:
    surucu = SahteSurucu(sayfalar)
    bekci = MagicMock()
    bekci.izinli_mi.return_value = izinli
    bekci.bekleme_suresi.return_value = 0.0
    sira = MagicMock()
    kaziyici = DenemeKaziyici(
        banka or deneme_bankasi(),
        surucu,  # type: ignore[arg-type]
        sahte_bekleme(),
        bekci=bekci,
        sira=sira,
        ilerleme=ilerleme,
        urller=urller,
    )
    return kaziyici, surucu


# ---------------------------------------------------------------------------
# Kayıt defteri ile kazıyıcıların bağı
# ---------------------------------------------------------------------------


class TestKayitDefteriBagi:
    """`data/banks.yaml` ile `src/collector/kaziyicilar/` birbirini tutmalı.

    Bu iki taraf ayrışırsa hata sessizdir: toplama koşar, bir bankanın
    kampanyaları hiç gelmez ve kimse fark etmez.
    """

    def test_her_faal_bankanin_kaziyicisi_var(self) -> None:
        eksik = [b.kisa_ad for b in faal_bankalar() if kaziyici_sinifi(b.kod) is None]
        assert not eksik, f"Faal ama kazıyıcısı olmayan banka: {eksik}"

    def test_her_kaziyici_kayit_defterinde_karsilik_buluyor(self) -> None:
        kodlar = {b.kod for b in bankalari_yukle()}
        fazla = [kod for kod in KAZIYICILAR if kod not in kodlar]
        assert not fazla, f"Kayıt defterinde olmayan kazıyıcı: {fazla}"

    def test_faal_bankanin_seed_urlleri_dolu(self) -> None:
        """Boş `seed_urls` = sessizce sıfır kayıt. Kazıyıcı adresini buradan okur."""
        bos = [b.kisa_ad for b in faal_bankalar() if not b.seed_urls]
        assert not bos, f"Faal ama seed_urls boş: {bos}"

    def test_kaziyici_sinif_kodu_ile_banka_kodu_ayni(self) -> None:
        for kod, sinif in KAZIYICILAR.items():
            assert sinif.BANKA_KODU == kod


class TestBankaKoduDogrulamasi:
    def test_yanlis_bankayla_kurulan_kaziyici_patlar(self) -> None:
        with pytest.raises(ValueError, match="banka kodu"):
            DenemeKaziyici(
                deneme_bankasi(kod="0999"),
                SahteSurucu(),  # type: ignore[arg-type]
                sahte_bekleme(),
            )

    def test_seed_urlleri_bos_bankada_liste_urlleri_patlar(self) -> None:
        kaziyici, _ = kaziyici_kur(urller=[], banka=deneme_bankasi(seed_urls=[]))
        with pytest.raises(ValueError, match="seed_urls"):
            _ = kaziyici.liste_urlleri


# ---------------------------------------------------------------------------
# Kayıt üretimi
# ---------------------------------------------------------------------------


@patch("time.sleep")
class TestTara:
    def test_kampanya_sayfasindan_ham_kayit_uretilir(self, _uyu: MagicMock) -> None:
        kaziyici, surucu = kaziyici_kur(urller=["https://deneme.com.tr/k/1"])
        kayitlar = list(kaziyici.tara())

        assert len(kayitlar) == 1
        kayit = kayitlar[0]
        assert kayit.banka_kodu == "0203"
        assert kayit.banka_adi == "Deneme Katılım Bankası A.Ş."
        assert kayit.url == "https://deneme.com.tr/k/1"
        assert "kâr payı oranı" in kayit.govde_metin
        assert kayit.ham_html
        assert surucu.gezilen == ["https://deneme.com.tr/k/1"]

    def test_robots_reddettigi_url_hic_cekilmez(self, _uyu: MagicMock) -> None:
        kaziyici, surucu = kaziyici_kur(urller=["https://deneme.com.tr/k/1"], izinli=False)
        kayitlar = list(kaziyici.tara())

        assert kayitlar == []
        assert surucu.gezilen == [], "robots reddettiği hâlde sayfa çekilmiş"

    def test_robots_kontrolu_kapali_bankada_kapi_atlanir(self, _uyu: MagicMock) -> None:
        kaziyici, surucu = kaziyici_kur(
            urller=["https://deneme.com.tr/k/1"],
            izinli=False,
            banka=deneme_bankasi(robots_kontrol=False),
        )
        assert len(list(kaziyici.tara())) == 1
        assert surucu.gezilen == ["https://deneme.com.tr/k/1"]

    def test_kisa_govde_elenir(self, _uyu: MagicMock) -> None:
        kaziyici, _ = kaziyici_kur(
            urller=["https://deneme.com.tr/k/kisa"],
            sayfalar={"https://deneme.com.tr/k/kisa": KISA_SAYFA},
        )
        assert list(kaziyici.tara()) == []

    def test_uzun_govde_esigi_semadan_gelir(self, _uyu: MagicMock) -> None:
        kaziyici, _ = kaziyici_kur(urller=["https://deneme.com.tr/k/1"])
        (kayit,) = list(kaziyici.tara())
        assert len(kayit.govde_metin) >= EN_AZ_GOVDE_UZUNLUGU

    def test_yinelenen_url_bir_kez_cekilir(self, _uyu: MagicMock) -> None:
        kaziyici, surucu = kaziyici_kur(
            urller=[
                "https://deneme.com.tr/k/1",
                "https://deneme.com.tr/k/1#detay",
                "https://deneme.com.tr/k/1",
            ]
        )
        assert len(list(kaziyici.tara())) == 1
        assert len(surucu.gezilen) == 1

    def test_sayfa_yuklenemezse_kayit_uretilmez(self, _uyu: MagicMock) -> None:
        from selenium.common.exceptions import TimeoutException

        kaziyici, surucu = kaziyici_kur(
            urller=["https://deneme.com.tr/k/1", "https://deneme.com.tr/k/2"]
        )
        cagri = {"n": 0}
        gercek_get = surucu.get

        def patlayan_get(url: str) -> None:
            cagri["n"] += 1
            if cagri["n"] == 1:
                raise TimeoutException("zaman aşımı")
            gercek_get(url)

        surucu.get = patlayan_get  # type: ignore[method-assign]
        kayitlar = list(kaziyici.tara())

        assert len(kayitlar) == 1, "hatalı sayfa diğerlerini de düşürmemeli"
        assert kayitlar[0].url == "https://deneme.com.tr/k/2"

    def test_ilerleme_olaylari_bildirilir(self, _uyu: MagicMock) -> None:
        """Arayüzün aşama göstergesi bu olay akışına bağlanacak."""
        olaylar: list[Ilerleme] = []
        kaziyici, _ = kaziyici_kur(
            urller=["https://deneme.com.tr/k/1", "https://deneme.com.tr/k/kisa"],
            sayfalar={"https://deneme.com.tr/k/kisa": KISA_SAYFA},
            ilerleme=olaylar.append,
        )
        list(kaziyici.tara())

        asamalar = [o.asama for o in olaylar]
        assert "url_kesfi" in asamalar
        assert "sayfa" in asamalar
        assert "atlandi" in asamalar
        assert asamalar[-1] == "bitti"

        son = olaylar[-1]
        assert son.sira == 1 and son.toplam == 2
        assert son.banka_kodu == "0203"


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------


@patch("time.sleep")
class TestTopla:
    """`make crawl` akışı: sürücü aç → banka başına kazı → diske yaz → kapat."""

    def _kos(self, tmp_path: Any, banka: Banka, urller: list[str]) -> tuple[int, SahteSurucu]:
        from src.collector.toplayici import topla

        surucu = SahteSurucu()

        class Sabit(DenemeKaziyici):
            def __init__(self, *a: Any, **k: Any) -> None:
                super().__init__(*a, urller=urller, **k)

        with (
            patch(
                "src.collector.tarayici.surucu_olustur",
                return_value=(surucu, sahte_bekleme()),
            ),
            patch("src.collector.kaziyicilar.kaziyici_sinifi", return_value=Sabit),
            patch("src.collector.toplayici.RobotsBekcisi.izinli_mi", return_value=True),
            patch("src.collector.toplayici.NezaketSirasi.bekle"),
        ):
            sayi = topla([banka], dizin=tmp_path)
        return sayi, surucu

    def test_kayitlar_diske_yazilir(self, _uyu: MagicMock, tmp_path: Any) -> None:
        sayi, _ = self._kos(
            tmp_path,
            deneme_bankasi(),
            ["https://deneme.com.tr/k/1", "https://deneme.com.tr/k/2"],
        )
        assert sayi == 2
        assert len(list((tmp_path / "0203").glob("*.json"))) == 2
        assert len(list((tmp_path / "0203").glob("*.html"))) == 2

    def test_faaliyete_gecmemis_banka_taranmaz(self, _uyu: MagicMock, tmp_path: Any) -> None:
        """Kayıt defterinde durur ama sitesinde kampanya beklenmez."""
        sayi, surucu = self._kos(
            tmp_path,
            deneme_bankasi(durum="faaliyete_gecmedi"),
            ["https://deneme.com.tr/k/1"],
        )
        assert sayi == 0
        assert surucu.gezilen == []

    def test_kaziyicisi_olmayan_banka_atlanir(self, _uyu: MagicMock, tmp_path: Any) -> None:
        from src.collector.toplayici import topla

        surucu = SahteSurucu()
        with (
            patch(
                "src.collector.tarayici.surucu_olustur",
                return_value=(surucu, sahte_bekleme()),
            ),
            patch("src.collector.kaziyicilar.kaziyici_sinifi", return_value=None),
        ):
            assert topla([deneme_bankasi()], dizin=tmp_path) == 0

    def test_hata_halinde_de_tarayici_kapatilir(self, _uyu: MagicMock, tmp_path: Any) -> None:
        """Kapanmayan Chrome süreci makinede bellek yiyerek kalır."""
        from src.collector.toplayici import topla

        surucu = SahteSurucu()
        kapandi = {"evet": False}
        surucu.quit = lambda: kapandi.__setitem__("evet", True)  # type: ignore[method-assign]

        class Patlayan(DenemeKaziyici):
            def kampanya_urlleri(self) -> list[str]:
                raise RuntimeError("site çöktü")

        with (
            patch(
                "src.collector.tarayici.surucu_olustur",
                return_value=(surucu, sahte_bekleme()),
            ),
            patch("src.collector.kaziyicilar.kaziyici_sinifi", return_value=Patlayan),
            pytest.raises(RuntimeError, match="site çöktü"),
        ):
            topla([deneme_bankasi()], dizin=tmp_path)

        assert kapandi["evet"], "hata sonrası tarayıcı açık kalmış"


class TestBenzersiz:
    def test_sira_korunur(self) -> None:
        assert benzersiz(["/c", "/a", "/b", "/a"]) == ["/c", "/a", "/b"]

    def test_capa_atilir(self) -> None:
        assert benzersiz(["https://x/k#ust", "https://x/k"]) == ["https://x/k"]

    def test_bos_deger_elenir(self) -> None:
        assert benzersiz(["", "  ", "https://x/k"]) == ["https://x/k"]


class TestTomSuresiGecenSuzgeci:
    """Sitede yazım tutarsız; süzgeç gözlenmiş varyantların tamamını tanımalı."""

    @pytest.mark.parametrize(
        "baslik",
        ["SÜRESİ GEÇMİŞ KAMPANYA", "Süresi Geçmiş", "GEÇMŞİ KAMPANYALAR"],
    )
    def test_suresi_gecen_baslik_taninir(self, baslik: str) -> None:
        assert any(kalip in baslik.upper() for kalip in SURESI_GECTI_KALIPLARI)

    def test_gecerli_kampanya_elenmez(self) -> None:
        baslik = "AKARYAKIT KAMPANYASI"
        assert not any(kalip in baslik.upper() for kalip in SURESI_GECTI_KALIPLARI)


# ---------------------------------------------------------------------------
# «Daha fazla yükle» — geç gelen kartlar
# ---------------------------------------------------------------------------


class SahteDugme:
    """Tıklanabilir «daha fazla yükle» düğmesi."""

    def __init__(self, liste: SahteListeSurucu) -> None:
        self._liste = liste

    def is_displayed(self) -> bool:
        return True

    def click(self) -> None:
        self._liste.tikla()


class SahteListeSurucu:
    """Sayfalanan liste: her tıklama bir parti ekler, kartlar GEÇ gelir.

    Gerçek Albaraka davranışı: tıklama sitenin iç sayfa sayacını hemen
    ilerletir ama kartlar DOM'a birkaç yoklama sonra girer. Kartların
    gelmesini beklemeden ikinci kez tıklanırsa o parti kaybolur — burada
    `kayip_parti` ile sayılır.
    """

    def __init__(
        self,
        *,
        kart_xpath: str,
        dugme_xpath: str,
        ilk: int = 9,
        parti: int = 9,
        toplam_parti: int = 5,
        gecikme_yoklama: int = 4,
        dugme_sonda_kalir: bool = False,
        yutulan_tiklama: int | None = None,
    ) -> None:
        self.kart_xpath = kart_xpath
        self.dugme_xpath = dugme_xpath
        self.parti = parti
        self.kalan_parti = toplam_parti
        self.gecikme_yoklama = gecikme_yoklama
        self.dugme_sonda_kalir = dugme_sonda_kalir
        self.yutulan_tiklama = yutulan_tiklama

        self.gorunen = ilk
        self.tiklama = 0
        self.kayip_parti = 0
        self.temizleme = 0
        self.gidilen: list[str] = []
        self._bekleyen: int | None = None  # kaç yoklama sonra inecek

    # -- site davranışı ---------------------------------------------------

    def tikla(self) -> None:
        self.tiklama += 1
        if self._bekleyen is not None:
            # önceki parti daha inmeden tekrar tıklandı: sayfa sayacı ilerledi,
            # o parti bir daha GELMEZ. Eski kodun kaybettiği kartlar bunlar.
            self.kayip_parti += 1
            self._bekleyen = None
            return
        if self.kalan_parti <= 0:
            return
        self.kalan_parti -= 1
        if self.tiklama == self.yutulan_tiklama:
            # Tıklama yutuldu: sayfa sayacı ilerledi ama kartlar HİÇ gelmeyecek.
            # Albaraka'da ölçülen davranış bu (26 Ağustos).
            self.kayip_parti += 1
            return
        self._bekleyen = self.gecikme_yoklama

    def _yokla(self) -> None:
        if self._bekleyen is None:
            return
        if self._bekleyen <= 0:
            self.gorunen += self.parti
            self._bekleyen = None
        else:
            self._bekleyen -= 1

    # -- WebDriver yüzeyi -------------------------------------------------

    def find_elements(self, _by: Any, xpath: str) -> list[Any]:
        if xpath == self.kart_xpath:
            self._yokla()
            return [object()] * self.gorunen
        if xpath == self.dugme_xpath:
            if self.kalan_parti > 0 or self.dugme_sonda_kalir:
                return [SahteDugme(self)]
            return []
        return []

    def execute_script(self, *_: Any) -> Any:
        return None

    def delete_all_cookies(self) -> None:
        self.temizleme += 1

    def get(self, url: str) -> None:
        self.gidilen.append(url)

    def quit(self) -> None:
        pass


KART_X = "//div[@class='kart']//a"
DUGME_X = "//a[@class='daha-fazla']"


def yukleyici_kur(**ayar: Any) -> tuple[DenemeKaziyici, SahteListeSurucu]:
    surucu = SahteListeSurucu(kart_xpath=KART_X, dugme_xpath=DUGME_X, **ayar)
    kaziyici = DenemeKaziyici(
        deneme_bankasi(),
        surucu,  # type: ignore[arg-type]
        sahte_bekleme(),
        bekci=MagicMock(),
        sira=MagicMock(),
        urller=[],
    )
    return kaziyici, surucu


@patch("src.collector.temel_kaziyici.time.sleep", MagicMock())
class TestHepsiniYukle:
    """Sabit bekleme yerine ARTIŞ beklendiğinin sınaması."""

    def test_gec_gelen_kartlar_kaybolmaz(self) -> None:
        kaziyici, surucu = yukleyici_kur(gecikme_yoklama=6)
        kaziyici.hepsini_yukle(KART_X, DUGME_X)
        assert surucu.gorunen == 9 + 9 * 5
        assert surucu.kayip_parti == 0

    def test_parti_inmeden_yeniden_tiklanmaz(self) -> None:
        """Asıl kusur buydu: parti inmeden ikinci tıklama sayfayı atlatıyordu."""
        kaziyici, surucu = yukleyici_kur(gecikme_yoklama=8)
        kaziyici.hepsini_yukle(KART_X, DUGME_X)
        assert surucu.tiklama == 5

    def test_kartlar_hemen_gelse_de_hepsi_toplanir(self) -> None:
        kaziyici, surucu = yukleyici_kur(gecikme_yoklama=0)
        kaziyici.hepsini_yukle(KART_X, DUGME_X)
        assert surucu.gorunen == 9 + 9 * 5

    def test_dugme_yoksa_hic_tiklanmaz(self) -> None:
        kaziyici, surucu = yukleyici_kur(toplam_parti=0)
        kaziyici.hepsini_yukle(KART_X, DUGME_X)
        assert surucu.tiklama == 0
        assert surucu.gorunen == 9

    def test_dugme_sonda_kalirsa_bos_turlarla_biter(self) -> None:
        """Düğme kaybolmayan sitelerde durduran şey kart sayısının artmaması."""
        kaziyici, surucu = yukleyici_kur(
            toplam_parti=2, dugme_sonda_kalir=True, gecikme_yoklama=0
        )
        kaziyici.hepsini_yukle(KART_X, DUGME_X, bekleme_saniye=0.01, azami_bos_tur=3)
        assert surucu.gorunen == 9 + 9 * 2
        assert surucu.tiklama == 5  # 2 verimli + 3 boş tur

    def test_artis_gelmezse_azami_surede_vazgecilir(self) -> None:
        kaziyici, surucu = yukleyici_kur(toplam_parti=1, gecikme_yoklama=10**6)
        kaziyici.hepsini_yukle(KART_X, DUGME_X, bekleme_saniye=0.01)
        assert surucu.gorunen == 9


@patch("src.collector.temel_kaziyici.time.sleep", MagicMock())
class TestPartiKaybiSaptamasi:
    """Yutulan tıklama saptanıyor mu — eksik liste sessizce kabul edilmemeli."""

    def test_temiz_yukleme_true_doner(self) -> None:
        kaziyici, _ = yukleyici_kur(gecikme_yoklama=2)
        assert kaziyici.hepsini_yukle(KART_X, DUGME_X, bekleme_saniye=0.05) is True

    def test_yutulan_tiklama_false_doner(self) -> None:
        kaziyici, surucu = yukleyici_kur(gecikme_yoklama=0, yutulan_tiklama=1)
        temiz = kaziyici.hepsini_yukle(KART_X, DUGME_X, bekleme_saniye=0.05)
        assert temiz is False
        assert surucu.gorunen == 9 + 9 * 4  # bir parti eksik

    def test_sondaki_bos_turlar_kayip_sayilmaz(self) -> None:
        """Site tükendiğinde son turlar boş geçer; bu kayıp DEĞİLDİR."""
        kaziyici, _ = yukleyici_kur(
            toplam_parti=2, dugme_sonda_kalir=True, gecikme_yoklama=0
        )
        assert (
            kaziyici.hepsini_yukle(KART_X, DUGME_X, bekleme_saniye=0.05, azami_bos_tur=3)
            is True
        )


@patch("src.collector.temel_kaziyici.time.sleep", MagicMock())
class TestListeyiTamamla:
    """Parti kaybında liste baştan yükleniyor mu, tükenince susuluyor mu?"""

    def test_kayipta_bastan_denenir(self) -> None:
        durum: dict[str, Any] = {}

        def hazirla() -> None:
            # ilk denemede tıklama yutulur, ikincisinde temiz
            sayi = durum.get("sayi", 0) + 1
            durum["sayi"] = sayi
            durum.setdefault("ilk", None)
            durum["surucu"] = SahteListeSurucu(
                kart_xpath=KART_X,
                dugme_xpath=DUGME_X,
                gecikme_yoklama=0,
                yutulan_tiklama=1 if sayi == 1 else None,
            )
            if durum["ilk"] is None:
                durum["ilk"] = durum["surucu"]
            kaziyici.surucu = durum["surucu"]

        kaziyici, _ = yukleyici_kur()
        kaziyici.listeyi_tamamla(hazirla, KART_X, DUGME_X, bekleme_saniye=0.05)
        ilk_surucu = durum["ilk"]

        assert durum["sayi"] == 2, "kayıptan sonra liste baştan alınmalı"
        assert durum["surucu"].gorunen == 9 + 9 * 5
        assert ilk_surucu.temizleme == 1, "yeniden denemeden önce oturum tazelenmeli"

    def test_temizse_tek_denemede_biter(self) -> None:
        cagri = {"sayi": 0}

        def hazirla() -> None:
            cagri["sayi"] += 1

        kaziyici, _ = yukleyici_kur(gecikme_yoklama=0)
        kaziyici.listeyi_tamamla(hazirla, KART_X, DUGME_X, bekleme_saniye=0.05)
        assert cagri["sayi"] == 1

    def test_denemeler_tukenince_sessiz_kalinmaz(self) -> None:
        olaylar: list[Ilerleme] = []

        def hazirla() -> None:
            kaziyici.surucu = SahteListeSurucu(  # type: ignore[assignment]
                kart_xpath=KART_X,
                dugme_xpath=DUGME_X,
                gecikme_yoklama=0,
                yutulan_tiklama=1,
            )

        kaziyici, _ = yukleyici_kur()
        kaziyici._ilerleme = olaylar.append
        kaziyici.listeyi_tamamla(
            hazirla, KART_X, DUGME_X, azami_deneme=2, bekleme_saniye=0.05
        )

        assert [o.asama for o in olaylar] == ["hata"]
        assert "eksik" in olaylar[0].mesaj
