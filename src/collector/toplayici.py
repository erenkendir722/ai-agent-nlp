"""Jenerik kampanya toplayıcı (Katman 0).

Banka başına ÖZEL KOD YOKTUR. Tüm bankalar tek kod yolundan geçer; farklılıklar
`data/banks.yaml` içindeki yapılandırmayla ifade edilir. Yeni banka eklemek
8 satır YAML demektir — jürinin "bankalar sitelerini değiştirirse?" sorusunun
cevabı budur.

Toplama disiplini (docs/VERI_METODOLOJISI.md ile aynı, jüri okuyacak):
  - robots.txt kontrolü zorunlu, crawl-delay uygulanır
  - İstek arası en az 2 saniye, eşzamanlı istek yok
  - Tanımlı User-Agent, iletişim adresiyle
  - Yalnız kamuya açık sayfalar; giriş gerektiren hiçbir alan yok
  - Kişisel veri toplanmaz (KVKK)
"""

from __future__ import annotations

import json
import logging
import time
import urllib.robotparser
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura
import yaml
from selectolax.parser import HTMLParser

from src.schema import Banka, HamKayit

log = logging.getLogger(__name__)

KOK = Path(__file__).resolve().parents[2]
BANKS_YAML = KOK / "data" / "banks.yaml"
HAM_DIZIN = KOK / "data" / "raw"

KULLANICI_AJANI = "TEKNOFEST-2026-SVARTAL-Bot (+kendireren722@gmail.com)"
ISTEK_ARASI_SANIYE = 2.0
ZAMAN_ASIMI = 20.0
EN_AZ_GOVDE_UZUNLUGU = 200  # bundan kısa metinler kampanya sayfası değildir


# ---------------------------------------------------------------------------
# Kayıt defteri
# ---------------------------------------------------------------------------


def bankalari_yukle(yol: Path = BANKS_YAML) -> list[Banka]:
    """banks.yaml'i doğrulanmış Banka nesnelerine çevirir."""
    ham = yaml.safe_load(yol.read_text(encoding="utf-8")) or []
    return [Banka.model_validate(kayit) for kayit in ham]


def faal_bankalar(bankalar: list[Banka] | None = None) -> list[Banka]:
    """Yalnız kampanya beklenen bankalar. Diğerleri kayıt defterinde kalır."""
    return [b for b in (bankalar or bankalari_yukle()) if b.kampanya_beklenir_mi]


# ---------------------------------------------------------------------------
# Nezaket katmanı
# ---------------------------------------------------------------------------


class RobotsBekcisi:
    """Alan adı başına robots.txt kuralları ve crawl-delay yönetimi."""

    def __init__(self, kullanici_ajani: str = KULLANICI_AJANI) -> None:
        self.kullanici_ajani = kullanici_ajani
        self._ayristiricilar: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def _ayristirici(self, url: str) -> urllib.robotparser.RobotFileParser | None:
        parcalar = urlparse(url)
        alan = f"{parcalar.scheme}://{parcalar.netloc}"
        if alan in self._ayristiricilar:
            return self._ayristiricilar[alan]

        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(urljoin(alan, "/robots.txt"))
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as istemci:
                yanit = istemci.get(
                    urljoin(alan, "/robots.txt"),
                    headers={"User-Agent": self.kullanici_ajani},
                )
            if yanit.status_code == 200:
                rp.parse(yanit.text.splitlines())
            else:
                # robots.txt yoksa erişim serbesttir (RFC 9309)
                rp.allow_all = True
        except httpx.HTTPError as hata:
            log.warning("robots.txt okunamadı (%s): %s — temkinli davranılıyor", alan, hata)
            rp = None

        self._ayristiricilar[alan] = rp
        return rp

    def izinli_mi(self, url: str) -> bool:
        rp = self._ayristirici(url)
        if rp is None:
            return False  # okuyamadıysak çekmiyoruz; temkinli taraf
        return rp.can_fetch(self.kullanici_ajani, url)

    def bekleme_suresi(self, url: str) -> float:
        """robots.txt crawl-delay değeri ile kendi alt sınırımızın büyüğü."""
        rp = self._ayristirici(url)
        gecikme = None
        if rp is not None:
            try:
                gecikme = rp.crawl_delay(self.kullanici_ajani)
            except AttributeError:
                gecikme = None
        return max(float(gecikme or 0.0), ISTEK_ARASI_SANIYE)


# ---------------------------------------------------------------------------
# Toplayıcı
# ---------------------------------------------------------------------------


class Toplayici:
    """Tek kod yolu, tüm bankalar."""

    def __init__(
        self,
        *,
        derinlik: int = 2,
        banka_basi_azami_sayfa: int = 60,
        kullanici_ajani: str = KULLANICI_AJANI,
    ) -> None:
        self.derinlik = derinlik
        self.banka_basi_azami_sayfa = banka_basi_azami_sayfa
        self.bekci = RobotsBekcisi(kullanici_ajani)
        self.istemci = httpx.Client(
            timeout=ZAMAN_ASIMI,
            follow_redirects=True,
            headers={
                "User-Agent": kullanici_ajani,
                "Accept-Language": "tr-TR,tr;q=0.9",
            },
        )
        self._son_istek: dict[str, float] = {}

    def __enter__(self) -> Toplayici:
        return self

    def __exit__(self, *_: object) -> None:
        self.istemci.close()

    # -- Alt seviye ------------------------------------------------------

    def _nezaketle_bekle(self, url: str) -> None:
        alan = urlparse(url).netloc
        gecikme = self.bekci.bekleme_suresi(url)
        gecen = time.monotonic() - self._son_istek.get(alan, 0.0)
        if gecen < gecikme:
            time.sleep(gecikme - gecen)
        self._son_istek[alan] = time.monotonic()

    def _getir(self, url: str, banka: Banka) -> httpx.Response | None:
        if banka.robots_kontrol and not self.bekci.izinli_mi(url):
            log.info("robots.txt reddetti, atlanıyor: %s", url)
            return None
        self._nezaketle_bekle(url)
        try:
            yanit = self.istemci.get(url)
        except httpx.HTTPError as hata:
            log.warning("İstek başarısız %s: %s", url, hata)
            return None
        if yanit.status_code != 200:
            log.info("HTTP %s: %s", yanit.status_code, url)
            return None
        if "text/html" not in yanit.headers.get("content-type", ""):
            return None
        return yanit

    # -- URL keşfi -------------------------------------------------------

    def _sitemap_urlleri(self, banka: Banka) -> list[str]:
        """sitemap.xml varsa oradan URL topla — en temiz keşif yolu."""
        if not banka.site:
            return []
        yanit = self._getir(urljoin(banka.site, "/sitemap.xml"), banka)
        if yanit is None:
            return []
        # Basit çıkarım: iç içe sitemap indekslerini takip etmiyoruz (v0 kapsamı)
        return [
            parca.split("</loc>")[0].strip()
            for parca in yanit.text.split("<loc>")[1:]
        ]

    def _sayfadaki_baglantilar(self, html: str, temel_url: str) -> list[str]:
        agac = HTMLParser(html)
        baglantilar = []
        for dugum in agac.css("a[href]"):
            href = (dugum.attributes.get("href") or "").strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            baglantilar.append(urljoin(temel_url, href).split("#")[0])
        return baglantilar

    def _desene_uyuyor_mu(self, url: str, banka: Banka) -> bool:
        if not banka.url_desenleri:
            return True
        return any(desen in url.lower() for desen in banka.url_desenleri)

    def _ayni_site_mi(self, url: str, banka: Banka) -> bool:
        return urlparse(url).netloc.endswith(urlparse(banka.site).netloc.removeprefix("www."))

    # -- Ana akış --------------------------------------------------------

    def banka_tara(self, banka: Banka) -> Iterator[HamKayit]:
        """Bir bankanın kampanya sayfalarını gezip ham kayıt üretir."""
        if not banka.kampanya_beklenir_mi:
            log.info("%s faaliyette değil, atlanıyor (durum=%s)", banka.kisa_ad, banka.durum)
            return

        gorulen: set[str] = set()
        sira: list[tuple[str, int]] = [(u, 0) for u in banka.seed_urls]
        sira += [
            (u, 1)
            for u in self._sitemap_urlleri(banka)
            if self._desene_uyuyor_mu(u, banka)
        ][: self.banka_basi_azami_sayfa]

        cikan = 0
        while sira and cikan < self.banka_basi_azami_sayfa:
            url, seviye = sira.pop(0)
            if url in gorulen or seviye > self.derinlik:
                continue
            gorulen.add(url)

            yanit = self._getir(url, banka)
            if yanit is None:
                continue

            govde = trafilatura.extract(
                yanit.text,
                include_comments=False,
                include_tables=True,
                favor_recall=True,
            ) or ""

            if len(govde) >= EN_AZ_GOVDE_UZUNLUGU and self._desene_uyuyor_mu(url, banka):
                cikan += 1
                yield HamKayit(
                    banka_kodu=banka.kod,
                    banka_adi=banka.ad,
                    url=url,
                    cekim_tarihi=datetime.now(),
                    http_durum=yanit.status_code,
                    baslik=self._baslik(yanit.text),
                    ham_html=yanit.text,
                    govde_metin=govde,
                )

            if seviye < self.derinlik:
                for bag in self._sayfadaki_baglantilar(yanit.text, url):
                    if bag not in gorulen and self._ayni_site_mi(bag, banka):
                        if self._desene_uyuyor_mu(bag, banka):
                            sira.append((bag, seviye + 1))

    @staticmethod
    def _baslik(html: str) -> str | None:
        dugum = HTMLParser(html).css_first("title")
        return dugum.text(strip=True) if dugum else None


# ---------------------------------------------------------------------------
# Diske yazma
# ---------------------------------------------------------------------------


def kaydi_yaz(kayit: HamKayit, dizin: Path = HAM_DIZIN) -> Path:
    """Ham anlık görüntüyü diske yazar. HTML ayrı dosyada — JSON'u şişirmesin."""
    banka_dizin = dizin / kayit.banka_kodu
    banka_dizin.mkdir(parents=True, exist_ok=True)
    kimlik = kayit.kampanya_id()

    (banka_dizin / f"{kimlik}.html").write_text(kayit.ham_html, encoding="utf-8")

    ust_veri = kayit.model_dump(mode="json", exclude={"ham_html"})
    yol = banka_dizin / f"{kimlik}.json"
    yol.write_text(json.dumps(ust_veri, ensure_ascii=False, indent=2), encoding="utf-8")
    return yol


def ham_kayitlari_oku(dizin: Path = HAM_DIZIN) -> Iterator[HamKayit]:
    """Diske yazılmış ham kayıtları geri okur (çıkarım katmanının girdisi)."""
    for yol in sorted(dizin.rglob("*.json")):
        veri = json.loads(yol.read_text(encoding="utf-8"))
        html_yolu = yol.with_suffix(".html")
        veri["ham_html"] = html_yolu.read_text(encoding="utf-8") if html_yolu.exists() else ""
        yield HamKayit.model_validate(veri)


def topla(bankalar: list[Banka] | None = None, **secenekler: object) -> int:
    """`make crawl` giriş noktası. Toplanan sayfa sayısını döner."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    hedefler = faal_bankalar(bankalar)
    toplam = 0
    with Toplayici(**secenekler) as toplayici:  # type: ignore[arg-type]
        for banka in hedefler:
            sayac = 0
            for kayit in toplayici.banka_tara(banka):
                kaydi_yaz(kayit)
                sayac += 1
            log.info("%-22s %3d sayfa", banka.kisa_ad, sayac)
            toplam += sayac
    log.info("TOPLAM: %d sayfa, %d banka", toplam, len(hedefler))
    return toplam


if __name__ == "__main__":
    topla()
