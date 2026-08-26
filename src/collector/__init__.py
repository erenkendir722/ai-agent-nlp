"""Toplama katmanı (Katman 0).

    toplayici.py        kayıt defteri · robots · nezaket · diske yazma · topla()
    tarayici.py         Selenium sürücüsü
    temel_kaziyici.py   kazıyıcı taban sınıfı (URL gezme, gövde ayıklama)
    kaziyicilar/        banka başına URL keşfi (9 banka)

Burada YALNIZ selenium gerektirmeyen yüzey dışa açılır: arayüz ve testler
`bankalari_yukle()` için tarayıcı kurmak zorunda kalmasın. Kazıyıcılar
`src.collector.kaziyicilar`'dan, sürücü `src.collector.tarayici`'dan alınır.
"""

from src.collector.toplayici import (
    BANKS_YAML,
    EN_AZ_GOVDE_UZUNLUGU,
    HAM_DIZIN,
    ISTEK_ARASI_SANIYE,
    KULLANICI_AJANI,
    NezaketSirasi,
    RobotsBekcisi,
    bankalari_yukle,
    faal_bankalar,
    ham_kayitlari_oku,
    kaydi_yaz,
    topla,
)

__all__ = [
    "BANKS_YAML",
    "EN_AZ_GOVDE_UZUNLUGU",
    "HAM_DIZIN",
    "ISTEK_ARASI_SANIYE",
    "KULLANICI_AJANI",
    "NezaketSirasi",
    "RobotsBekcisi",
    "bankalari_yukle",
    "faal_bankalar",
    "ham_kayitlari_oku",
    "kaydi_yaz",
    "topla",
]
