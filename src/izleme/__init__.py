"""Tetikleyici ve dinleyici katmanı (G-17) — «veri hâlâ güncel mi?».

İki parça, bilerek ayrı:

    tetikleyici.py   NE ZAMAN denetleneceğinin takvimi — TANIMLI AMA KURULU DEĞİL
    dinleyici.py     Kampanya sayfası değişmiş mi — asıl iş burada

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
from src.izleme.tetikleyici import KAMPANYA_SAATLERI, Tetikleyici

__all__ = [
    "KAMPANYA_SAATLERI",
    "IzlemeHedefi",
    "TazelikKaydi",
    "TazelikOlayi",
    "TazelikOzeti",
    "Tetikleyici",
    "hedefleri_oku",
    "icerik_ozeti",
    "taban_oku",
    "taban_yaz",
    "tazelik_denetle",
]
