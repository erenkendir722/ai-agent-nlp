"""Tetikleyici ve dinleyici katmanı — «veri hâlâ güncel mi?».

İki parça, bilerek ayrı:

    tetikleyici.py   NE ZAMAN denetleneceğinin takvimi — TANIMLI AMA KURULU DEĞİL
    dinleyici.py     ELİMİZDEKİ kampanya sayfası değişmiş mi
    kesif.py         ELİMİZDE OLMAYAN yeni kampanya çıkmış mı

İki soru farklıdır ve dinleyici ikincisini yapısal olarak göremez: yalnız
bildiği URL'leri yoklar, envanterde olmayanın adresi hiç ziyaret edilmez.

Bu katman **değişikliği TESPİT eder, veriyi TAZELEMEZ.** Değişmiş bulduğu
sayfayı kendiliğinden yeniden çekmez; «şu kampanyalar değişmiş» der ve
tazelemeyi operatöre bırakır. Sebebi ölçüm disiplini: `data/raw` ve
`data/katilim.db` yayımlanan sayıların üzerinde koştuğu veridir, kendiliğinden
değişirse `make eval` çıktısı ile `docs/SONUCLAR.md` sessizce ayrışır.

Katmanın yazdığı tek yer `data/izleme/`'dir.
"""

from src.izleme.dinleyici import (
    IzlemeHedefi,
    TazelikKaydi,
    TazelikOlayi,
    TazelikOzeti,
    hedefleri_oku,
    icerik_ozeti,
    taban_oku,
    taban_yaz,
    tazelik_denetle,
)
from src.izleme.kesif import (
    KESIF_DOSYASI,
    KesifOlayi,
    KesifOzeti,
    KesifSonucu,
    envanter_oku,
    kampanya_urli_mi,
    kesif_kos,
    kesif_taban_oku,
    kesif_taban_yaz,
    url_normalize,
)
from src.izleme.tetikleyici import KAMPANYA_SAATLERI, Tetikleyici

__all__ = [
    "KAMPANYA_SAATLERI",
    "KESIF_DOSYASI",
    "KesifOlayi",
    "KesifOzeti",
    "KesifSonucu",
    "IzlemeHedefi",
    "TazelikKaydi",
    "TazelikOlayi",
    "TazelikOzeti",
    "Tetikleyici",
    "envanter_oku",
    "hedefleri_oku",
    "icerik_ozeti",
    "kampanya_urli_mi",
    "kesif_kos",
    "kesif_taban_oku",
    "kesif_taban_yaz",
    "taban_oku",
    "taban_yaz",
    "tazelik_denetle",
    "url_normalize",
]
