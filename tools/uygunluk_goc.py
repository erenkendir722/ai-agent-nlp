"""Uygunluk göçü — mevcut kayıtlara `uygunluk` koşullarını yazar.

    python tools/uygunluk_goc.py --deneme    # ne değişecek, YAZMADAN göster
    python tools/uygunluk_goc.py             # uygula

NEDEN GÖÇ, NEDEN YENİDEN ÇIKARIM DEĞİL:
    Uygunluk koşulları LLM'siz türetilir (`src/ajanlar/uygunluk.py`): çoğu
    zaten çıkarılmış alanların yeniden yorumlanması, kalanı metin kalıbı.
    1024 kaydı EVREN'den yeniden geçirmek ~8 dakika sürer ve — ölçüldüğü gibi
    EVREN bayt düzeyinde deterministik değildir — başka alanların
    değerlerini oynatır. O zaman `docs/SONUCLAR.md`'deki makro-F1, uygunlukla
    hiç ilgisi olmayan sebeplerle değişirdi.

    Göç yalnız `uygunluk` alanını doldurur; kalan her değer BİREBİR korunur.
    Aynı ilke `tools/birim_goc.py`'de de uygulandı.

NEDEN AYRI BİR ÇÖZÜMLEYİCİ YAZILMADI:
    Göç, çıkarımın kullandığı `UygunlukAjani`'nin TA KENDİSİNİ çağırır. İkinci
    bir uygulama, göç edilmiş kayıtla yeni çıkarılan kaydın sessizce ayrışması
    demekti.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ajanlar.uygunluk import UygunlukAjani  # noqa: E402
from src.depolama import VERITABANI_URL, kampanyalari_oku, kaydet  # noqa: E402


def _tarih_tipini_onar(kampanya) -> None:
    """JSON gidiş-dönüşünde kaybolan `date` tipini geri kurar.

    `Alan.deger` bilinçli olarak `Any` (alan başına farklı tip taşır), bu
    yüzden pydantic `tam_kayit` JSON'undan okurken tarihi ÇÖZMEZ —
    "2026-08-31" string olarak kalır ve SQLite `Date` sütunu onu reddeder.
    `tools/birim_goc.py` aynı tuzağa aynı yerde düşmüştü; not orada da var.
    """
    alan = kampanya.kampanya_bitis
    if isinstance(alan.deger, str):
        try:
            alan.deger = date.fromisoformat(alan.deger)
        except ValueError:  # biçimsiz tarih: değere DOKUNMA, göç onu onarmaz
            pass


def calistir(deneme: bool, url: str = VERITABANI_URL) -> int:
    ajan = UygunlukAjani()
    kampanyalar = list(kampanyalari_oku(url))
    if not kampanyalar:
        print(" Veritabanı boş. Önce `make extract` çalıştırın.")
        return 1

    sayac: Counter[str] = Counter()
    kisit_var = 0
    onceden_dolu = 0

    for kampanya in kampanyalar:
        if kampanya.uygunluk is not None:
            onceden_dolu += 1
        _tarih_tipini_onar(kampanya)
        kosul = ajan.cikar(kampanya)
        kampanya.uygunluk = kosul
        if kosul.kisit_var_mi():
            kisit_var += 1
        for ad, deger in (
            ("musteri_tipi", kosul.musteri_tipi),
            ("segment_detayi", kosul.segment_detayi),
            ("min_tutar", kosul.min_tutar),
            ("max_tutar", kosul.max_tutar),
            ("min_vade_ay", kosul.min_vade_ay),
            ("max_vade_ay", kosul.max_vade_ay),
            ("zorunlu_urun", kosul.zorunlu_urun),
        ):
            if deger not in (None, [], ()):
                sayac[ad] += 1

    toplam = len(kampanyalar)
    print(f"Kayıt: {toplam} · önceden uygunluğu olan: {onceden_dolu}")
    print(f"Kısıt bulunan kayıt: {kisit_var} (%{kisit_var / toplam * 100:.1f})")
    print("Alan bazlı doluluk:")
    for ad, n in sorted(sayac.items(), key=lambda x: -x[1]):
        print(f"   {ad:16} {n:5d}  %{n / toplam * 100:.1f}")

    if deneme:
        print("\n(deneme modu — hiçbir şey yazılmadı)")
        return 0

    kaydet(kampanyalar, url)
    print(f"\n {toplam} kayıt güncellendi — `uygunluk` yazıldı.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Uygunluk göçü")
    ap.add_argument("--deneme", action="store_true", help="yazmadan göster")
    return calistir(ap.parse_args().deneme)


if __name__ == "__main__":
    raise SystemExit(main())
