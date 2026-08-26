"""Banka başına kazıyıcı kayıt defteri.

Anahtar `data/banks.yaml` içindeki EFT kodudur. Kayıt defterinde faal olup
burada karşılığı olmayan bankayı `topla()` uyararak atlar — sessizce eksik
veri üretmez.

Yeni banka eklemek:
  1. `data/banks.yaml`'a satırını yaz (kod, ad, site, durum: faal)
  2. Bu dizine `<banka>.py` ekle: `TemelKaziyici` türet, `BANKA_KODU` ver,
     `kampanya_urlleri()` yaz
  3. Aşağıdaki eşlemeye bir satır ekle

Bu modül selenium'u içeri çeker; `bankalari_yukle` gibi hafif yardımcıları
kullanan arayüz/test kodu buraya DEĞİL `src.collector.toplayici`'ya bakmalı.
"""

from __future__ import annotations

from src.collector.kaziyicilar.albaraka import AlbarakaKaziyici
from src.collector.kaziyicilar.dunya_katilim import DunyaKatilimKaziyici
from src.collector.kaziyicilar.emlak_katilim import EmlakKatilimKaziyici
from src.collector.kaziyicilar.hayat_finans import HayatFinansKaziyici
from src.collector.kaziyicilar.kuveyt_turk import KuveytTurkKaziyici
from src.collector.kaziyicilar.tom_katilim import TomKatilimKaziyici
from src.collector.kaziyicilar.turkiye_finans import TurkiyeFinansKaziyici
from src.collector.kaziyicilar.vakif_katilim import VakifKatilimKaziyici
from src.collector.kaziyicilar.ziraat_katilim import ZiraatKatilimKaziyici
from src.collector.temel_kaziyici import TemelKaziyici

KAZIYICILAR: dict[str, type[TemelKaziyici]] = {
    sinif.BANKA_KODU: sinif
    for sinif in (
        AlbarakaKaziyici,
        KuveytTurkKaziyici,
        TurkiyeFinansKaziyici,
        ZiraatKatilimKaziyici,
        VakifKatilimKaziyici,
        EmlakKatilimKaziyici,
        HayatFinansKaziyici,
        TomKatilimKaziyici,
        DunyaKatilimKaziyici,
    )
}


def kaziyici_sinifi(banka_kodu: str) -> type[TemelKaziyici] | None:
    """Banka kodundan kazıyıcı sınıfı. Yoksa `None`."""
    return KAZIYICILAR.get(banka_kodu)


__all__ = [
    "KAZIYICILAR",
    "AlbarakaKaziyici",
    "DunyaKatilimKaziyici",
    "EmlakKatilimKaziyici",
    "HayatFinansKaziyici",
    "KuveytTurkKaziyici",
    "TemelKaziyici",
    "TomKatilimKaziyici",
    "TurkiyeFinansKaziyici",
    "VakifKatilimKaziyici",
    "ZiraatKatilimKaziyici",
    "kaziyici_sinifi",
]
