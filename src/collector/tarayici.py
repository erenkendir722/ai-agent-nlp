"""Selenium sürücüsü — kazıyıcıların tarayıcı katmanı.

Neden tarayıcı: katılım bankalarının kampanya listeleri JavaScript ile
render ediliyor ve «daha fazla yükle» butonuyla sayfalanıyor. Ham HTML'i
httpx ile çekmek kartların çoğunu hiç görmez; kartlar DOM'a ancak script
koştuktan ve butona tıklandıktan sonra giriyor. `data/raw` altındaki
kayıtlar bu tarayıcı yoluyla toplandı (kayıt kimlikleri, URL'ler ve çekim
tarihleri kazıyıcı çıktısıyla birebir eşleşiyor).

User-Agent TEK yerden gelir: `src.collector.toplayici.KULLANICI_AJANI`.
Ağa giden dize ile `docs/kanit/VERI_TOPLAMA_ETIGI.md`'de beyan edilen dize
aynı olmalı — ikisi ayrı yerde tanımlanırsa beyan er geç yalan olur.
"""

from __future__ import annotations

import logging
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait

from src.collector.toplayici import KULLANICI_AJANI

log = logging.getLogger(__name__)

SAYFA_ZAMAN_ASIMI = 180
"""Sayfa yükleme üst sınırı (sn). Banka siteleri ağırdır; 180 ölçülmüş değer."""

BEKLEME_SANIYE = 15
"""`WebDriverWait` üst sınırı — öge belirene kadar beklenecek azami süre."""


def _secenekler(gorunmez: bool) -> Options:
    secenekler = Options()
    # 'eager': DOMContentLoaded yeter, tüm resim/analitik istekleri beklenmez.
    # Kampanya kartları DOM'da olur; tam 'load' beklemek kayıt başına ~10 sn ekler.
    secenekler.page_load_strategy = "eager"
    secenekler.add_argument("--start-maximized")
    secenekler.add_argument("--disable-notifications")
    secenekler.add_argument("--disable-popup-blocking")
    secenekler.add_argument(f"user-agent={KULLANICI_AJANI}")
    if gorunmez:
        secenekler.add_argument("--headless=new")
        secenekler.add_argument("--window-size=1920,1080")
    return secenekler


def _servis() -> Service | None:
    """chromedriver'ı bul.

    Öncelik `webdriver_manager` — `data/raw`'ı üreten koşularda kullanılan yol
    budur. Kurulu değilse Selenium Manager (Selenium 4.6+ gömülü) devreye
    girer. İkisi de yoksa hata FIRLATILIR; sessizce sürücüsüz devam edilmez.
    """
    try:
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        log.info("webdriver_manager yok — Selenium Manager kullanılıyor")
        return None
    return Service(ChromeDriverManager().install())


def surucu_olustur(
    *,
    gorunmez: bool | None = None,
    bekleme_saniye: int = BEKLEME_SANIYE,
) -> tuple[webdriver.Chrome, WebDriverWait]:
    """Chrome sürücüsü ve ortak `WebDriverWait` üretir.

    `gorunmez` verilmezse `KAZIYICI_GORUNMEZ` ortam değişkenine bakılır.
    Görünür tarayıcı varsayılandır: toplama sırasında ne olduğunu görmek,
    site yapısı değiştiğinde tanıyı dakikalar mertebesinde kısaltıyor.
    """
    if gorunmez is None:
        gorunmez = os.getenv("KAZIYICI_GORUNMEZ", "").strip().lower() in {"1", "true", "evet"}

    servis = _servis()
    secenekler = _secenekler(gorunmez)
    surucu = (
        webdriver.Chrome(service=servis, options=secenekler)
        if servis is not None
        else webdriver.Chrome(options=secenekler)
    )
    surucu.set_page_load_timeout(SAYFA_ZAMAN_ASIMI)
    return surucu, WebDriverWait(surucu, bekleme_saniye)
