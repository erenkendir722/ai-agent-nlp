"""Süresi geçmiş kampanyaları veritabanından siler.

NEDEN AYRI BİR ADIM, ÇIKARIMIN İÇİNDE DEĞİL:
Bitiş tarihi ancak çıkarımdan SONRA bilinir; çıkarım sırasında elemek için
tarihi iki kez çıkarmak gerekirdi. Ayrı adım olması ayrıca kararı geri
alınabilir kılıyor: `make extract` yeniden koşulduğunda kayıtlar geri gelir.

ALTIN SET MUAFİYETİ:
`data/gold/altin_set.jsonl` içindeki kampanyalar silinmez. O 60 kaydı dört
kişi elle etiketledi ve `make eval` metriklerinin taban çizgisi onlar. Süresi
geçmiş bir kaydı silmek, ölçümü 60 yerine 59 kayıt üzerinden yapmaya başlar
ve önceki metriklerle karşılaştırma sessizce bozulur. Veride bir tane bayat
kampanya kalması, ölçüm zeminini kaydırmaktan iyidir.

GÜVENLİK: Varsayılan koşu SİLMEZ, ne silineceğini gösterir. Silmek için
`--uygula` gerekir (`make suresi-gecenleri-ele uygula=1`).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from sqlalchemy import delete, select  # noqa: E402

from src.depolama import VERITABANI_URL, KampanyaKaydi, oturum  # noqa: E402

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


def suresi_gecenler(url: str = VERITABANI_URL, bugun: date | None = None) -> list[dict]:
    """Bitiş tarihi geçmiş kayıtlar — altın set muafiyeti UYGULANMADAN."""
    bugun = bugun or date.today()
    with oturum(url) as oturum_:
        sorgu = select(KampanyaKaydi).where(
            KampanyaKaydi.kampanya_bitis.is_not(None),
            KampanyaKaydi.kampanya_bitis < bugun,
        )
        return [
            {
                "kampanya_id": k.kampanya_id,
                "banka_kodu": k.banka_kodu,
                "kampanya_bitis": k.kampanya_bitis,
                "kaynak_url": k.kaynak_url,
            }
            for k in oturum_.scalars(sorgu)
        ]


def ele(
    url: str = VERITABANI_URL,
    bugun: date | None = None,
    uygula: bool = False,
) -> tuple[list[dict], list[dict]]:
    """(silinecekler, muaf_tutulanlar) döner. `uygula` False ise yazma yapmaz."""
    korunacak = altin_set_kimlikleri()
    tumu = suresi_gecenler(url, bugun)
    muaf = [k for k in tumu if k["kampanya_id"] in korunacak]
    silinecek = [k for k in tumu if k["kampanya_id"] not in korunacak]

    if uygula and silinecek:
        with oturum(url) as oturum_:
            oturum_.execute(
                delete(KampanyaKaydi).where(
                    KampanyaKaydi.kampanya_id.in_([k["kampanya_id"] for k in silinecek])
                )
            )
            oturum_.commit()
    return silinecek, muaf


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Süresi geçmiş kampanyaları ele")
    ap.add_argument(
        "--uygula",
        action="store_true",
        help="gerçekten sil (varsayılan: yalnız göster)",
    )
    args = ap.parse_args(argv[1:])

    silinecek, muaf = ele(uygula=args.uygula)

    if muaf:
        print(f"Altın sette olduğu için KORUNAN {len(muaf)} kayıt:")
        for k in muaf:
            print(f"  {k['banka_kodu']}  {k['kampanya_bitis']}  ...{k['kaynak_url'][-52:]}")
        print()

    if not silinecek:
        print("Silinecek kayıt yok.")
        return 0

    baslik = "SİLİNDİ" if args.uygula else "Silinecek (kuru çalıştırma)"
    print(f"{baslik}: {len(silinecek)} kayıt")
    for k in sorted(silinecek, key=lambda x: x["kampanya_bitis"]):
        print(f"  {k['banka_kodu']}  {k['kampanya_bitis']}  ...{k['kaynak_url'][-52:]}")

    if not args.uygula:
        print()
        print("Silmek için: make suresi-gecenleri-ele uygula=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
