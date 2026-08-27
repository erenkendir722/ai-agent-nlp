"""İçeriği indekslenemeyen liste sayfalarını veritabanından siler.

NEDEN GEREKLİ — 27 Ağustos'ta ölçüldü:
734 kaydın 8'i kampanya değil, **kategori listeleme sayfası**. URL'ler bunu
zaten söylüyor:

    /kampanyalar/market-ve-gida   /kampanyalar/e-ticaret   /kart-kampanyalari

Gövdeleri baştan sona tek bir satırın tekrarı:

    "Market ve Gıda\\nSon Gün 07.09.2026\\nSon Gün 07.09.2026\\nSon Gün 07.08.2026…"

En uzun paragrafları 18-21 karakter. Biri 3.970 karakter ve 209 paragraf
taşıyor — yani UZUNLUK bir ölçüt değil, paragrafın kendisi ölçüt.

ZARARSIZ DEĞİLLER. Çıkarım bu sayfalardan da alan üretiyor ve ürettiği şey
uydurma: `market-ve-gida` sayfasında **dokuz ayrı tarih** var ve
`kampanya_bitis` onlardan biri seçilmiş (2026-09-07). Yani korpusta, var
olmayan bir kampanyanın keyfî bir bitiş tarihi duruyor — kaynak alıntısıyla
birlikte, yani güvenilir görünerek. `kampanya_avantaji` ve
`kampanya_kosullari` de aynı kabuktan türetiliyor.

ÖLÇÜT NEDEN `vektor_db.paragraflara_ayir` — ikinci bir eşik yazılmadı:
RAG katmanı bu sekiz kaydı ZATEN dışarıda bırakıyor (indekste 726 kampanya
var, veritabanında 734). Kullandığı kural tek satır: `ASGARI_PARAGRAF`
uzunluğunda tek bir paragraf bile yoksa indekslenecek bir şey yok. Aynı
soruya iki farklı yerde iki farklı cevap vermemek için ölçüt oradan okunur —
eşik değişirse ikisi birlikte değişir.

Cümlenin kendisi de savunulabilir: *bir sayfadan tek bir paragraf bile
indekslenemiyorsa o sayfa bir kampanya metni değildir.*

NEDEN AYRI BİR ADIM, ÇIKARIMIN İÇİNDE DEĞİL:
`yinelenenleri_ele.py` ve `suresi_gecenleri_ele.py` ile aynı gerekçe. Karar
geri alınabilir kalsın diye: `make extract` yeniden koşulduğunda kayıtlar
geri gelir. Çıkarımın içine gömülseydi, eşiğin bir gün yanlış olduğu
anlaşıldığında elde veri kalmazdı.

`data/raw` DEĞİŞMEZ. O adresler gerçekten gezildi; ham arşiv şartname 5.1'in
izlenebilirlik kanıtıdır. Düşen tek şey o sayfanın bir KAMPANYA sayılması.

ALTIN SET MUAFİYETİ:
Etiketli kayıt asla silinmez — silinirse `make eval` ölçüm zemini kayar.
Bu koşuda ısırıyor: sekiz adayın biri (`0209-7201b97fc48c`,
`/kart-kampanyalari`) Esra tarafından etiketlenmiş. Muafiyet onu tutuyor ve
tutmalı; ölçüm zemini, sayım temizliğinden pahalıdır. Kaydın kendisi bir
bulgu olarak duruyor: etiketleme kılavuzu liste sayfalarını dışlamıyordu.

GÜVENLİK: Varsayılan koşu SİLMEZ, ne silineceğini gösterir. Silmek için
`--uygula` gerekir (`make liste-sayfalarini-ele uygula=1`).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from sqlalchemy import delete, select  # noqa: E402

from src.depolama import VERITABANI_URL, KampanyaKaydi, oturum  # noqa: E402
from src.vektor_db import paragraflara_ayir  # noqa: E402

ALTIN_SET = KOK / "data" / "gold" / "altin_set.jsonl"


def altin_set_kimlikleri(yol: Path | None = None) -> set[str]:
    """Etiketli kampanyaların kimlikleri — bunlar silinmez.

    Varsayılan `ALTIN_SET` imzada DEĞİL burada çözülür: varsayılan argüman
    tanım anında bağlanır ve sabiti sonradan değiştirmek (test, farklı depo
    kökü) etkisiz kalırdı.
    """
    yol = yol or ALTIN_SET
    if not yol.exists():
        return set()
    kimlikler = set()
    for satir in yol.read_text(encoding="utf-8").splitlines():
        if satir.strip():
            kimlikler.add(json.loads(satir)["kampanya_id"])
    return kimlikler


def indekslenemeyenler(url: str = VERITABANI_URL) -> list[dict]:
    """Tek bir paragrafı bile indekslenemeyen kayıtlar.

    Ölçüt `vektor_db.paragraflara_ayir` — ikinci bir eşik tutulmaz.
    """
    with oturum(url) as oturum_:
        return [
            {
                "kampanya_id": k.kampanya_id,
                "banka_kodu": k.banka_kodu,
                "banka_adi": k.banka_adi,
                "kaynak_url": k.kaynak_url,
                "uzunluk": len(k.ham_metin or ""),
                "doluluk_orani": k.doluluk_orani,
            }
            for k in oturum_.scalars(select(KampanyaKaydi))
            if not paragraflara_ayir(k)
        ]


def ele(url: str = VERITABANI_URL, uygula: bool = False) -> tuple[list[dict], list[dict]]:
    """(silinecekler, altın set muafiyetiyle korunanlar) döner."""
    korunacak = altin_set_kimlikleri()
    adaylar = indekslenemeyenler(url)

    silinecek = [k for k in adaylar if k["kampanya_id"] not in korunacak]
    korunan = [k for k in adaylar if k["kampanya_id"] in korunacak]

    if uygula and silinecek:
        with oturum(url) as oturum_:
            oturum_.execute(
                delete(KampanyaKaydi).where(
                    KampanyaKaydi.kampanya_id.in_([k["kampanya_id"] for k in silinecek])
                )
            )
            oturum_.commit()
    return silinecek, korunan


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="İçeriği indekslenemeyen liste sayfalarını ele"
    )
    ap.add_argument(
        "--uygula", action="store_true", help="gerçekten sil (varsayılan: yalnız göster)"
    )
    args = ap.parse_args(argv[1:])

    silinecek, korunan = ele(uygula=args.uygula)

    if not silinecek and not korunan:
        print("İndekslenemeyen kayıt yok.")
        return 0

    baslik = "SİLİNDİ" if args.uygula else "Silinecek (kuru çalıştırma)"
    print(f"{baslik}: {len(silinecek)} kayıt")
    print()
    for kayit in sorted(silinecek, key=lambda k: (k["banka_kodu"], k["kaynak_url"])):
        print(f"  {kayit['kampanya_id']}  {kayit['uzunluk']:>5} krk  "
              f"doluluk {kayit['doluluk_orani']:.2f}")
        print(f"      ...{kayit['kaynak_url'][-62:]}")

    if korunan:
        print()
        print(f"ALTIN SET MUAFİYETİ — {len(korunan)} kayıt korundu (ölçüm zemini kaymasın):")
        for kayit in korunan:
            print(f"  {kayit['kampanya_id']}  ...{kayit['kaynak_url'][-62:]}")

    if not args.uygula:
        print()
        print("Silmek için: make liste-sayfalarini-ele uygula=1")
    else:
        print()
        print("`data/raw` DEĞİŞMEDİ. `make extract` bu kayıtları geri getirir.")
        print("Sırada: make vektor  (indeksin korpus izi değişti)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
