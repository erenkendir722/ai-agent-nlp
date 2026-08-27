"""Aynı içeriği taşıyan yinelenen kayıtları veritabanından siler.

NEDEN GEREKLİ — 27 Ağustos'ta ölçüldü:
920 kaydın yalnız 734'ü farklı metin taşıyor. 186 kayıt, başka bir kaydın
birebir kopyası. İki ayrı kaynağı var:

    TOM Katılım · 48 kampanya iki yoldan birden gezilmiş
        /kampanyalar/X  ve  /cok-kazananlar-kulubu-kampanya/X
    Türkiye Finans · 86 sözleşme PDF'i, hepsi görüntüleyici kabuğunu vermiş
        "Enter the password to open this PDF file: File name: - ..."

İkisi de aynı hatanın iki yüzü: kimlik URL'den türetiliyor
(`Kampanya.kimlik_uret`), dolayısıyla aynı içerik farklı adreste farklı kayıt
oluyor. Kimlik sözleşmesi doğru — kaynak izlenebilirliği URL'e bağlı — ama
sayım o yüzden şişiyor: jüriye «920 kampanya» denirken elde 734 farklı metin
var.

NEDEN AYRI BİR ADIM, ÇIKARIMIN İÇİNDE DEĞİL:
`suresi_gecenleri_ele.py` ile aynı gerekçe. Yinelenme ancak bütün korpus
elde olunca görülür; çıkarım kayıt kayıt koşuyor ve o sırada «bunun kopyası
başka yerde var mı» sorusunu cevaplayamaz. Ayrı adım kararı geri alınabilir
de kılıyor: `make extract` yeniden koşulduğunda kayıtlar geri gelir.

`data/raw` DEĞİŞMEZ. Silinen adresler gerçekten gezildi; ham arşiv şartname
5.1'in izlenebilirlik kanıtıdır ve kopya diye silinmesi kazımanın kendisini
yanlış gösterirdi. Düşen tek şey o kaydın ayrı bir kampanya sayılması.

ALTIN SET MUAFİYETİ:
Etiketli kayıt asla silinmez — silinirse `make eval` ölçüm zemini kayar.
Bir çiftin bir ucu altın settteyse KORUNAN o uçtur, kopyası düşer.

GÜVENLİK: Varsayılan koşu SİLMEZ, ne silineceğini gösterir. Silmek için
`--uygula` gerekir (`make yinelenenleri-ele uygula=1`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from sqlalchemy import delete, select  # noqa: E402

from src.depolama import VERITABANI_URL, KampanyaKaydi, oturum  # noqa: E402

ALTIN_SET = KOK / "data" / "gold" / "altin_set.jsonl"


def icerik_izi(metin: str | None) -> str:
    """Metnin boşluktan arındırılmış özeti.

    BÜTÜN BOŞLUKLAR ATILIR — `src/izleme/dinleyici.py` ile aynı gerekçe:
    Albaraka aynı sayfayı tek boşluk farkıyla iki biçimde veriyor. Boşluğa
    duyarlı bir özet o iki kaydı «farklı içerik» sayar ve yinelenme gizlenir.
    """
    return hashlib.sha256(re.sub(r"\s+", "", metin or "").encode()).hexdigest()


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


def _tutulma_onceligi(kayit: dict, korunacak: set[str]) -> tuple:
    """Bir kopya öbeğinde hangi kaydın kalacağını belirleyen sıralama anahtarı.

    Küçük olan kazanır. Sıra ve gerekçesi:

    1. **Altın sette olan.** Ölçüm zemini kaymasın (bkz. modül başlığı).
    2. **URL'inde 'kampanya' geçen.** TOM'da aynı sayfa hem
       `/kampanyalar/X` hem `/cok-kazananlar-kulubu-kampanya/X` altında.
       Kampanya listesindeki adres kanonik olandır; kulüp yolu bir vitrin.
    3. **Kısa URL.** Aynı içeriğe giden iki yoldan kısa olanı üst dizin
       demektir; sorgu parametresi ve derin yol eklentileri düşer.
    4. **Kimlik alfabetik.** Yalnız belirlenircilik için — yukarıdakiler
       berabere kalırsa seçim makineye değil sıraya bırakılır, aynı
       veritabanı her koşuda aynı kaydı tutar.
    """
    url = kayit["kaynak_url"]
    return (
        kayit["kampanya_id"] not in korunacak,
        "kampanya" not in url.lower(),
        len(url),
        kayit["kampanya_id"],
    )


def yinelenen_obekleri(url: str = VERITABANI_URL) -> list[list[dict]]:
    """Aynı içeriği taşıyan kayıt öbekleri (yalnız 2+ üyeli olanlar)."""
    with oturum(url) as oturum_:
        kayitlar = [
            {
                "kampanya_id": k.kampanya_id,
                "banka_kodu": k.banka_kodu,
                "banka_adi": k.banka_adi,
                "kaynak_url": k.kaynak_url,
                "iz": icerik_izi(k.ham_metin),
                "uzunluk": len(k.ham_metin or ""),
            }
            for k in oturum_.scalars(select(KampanyaKaydi))
        ]

    obekler: dict[str, list[dict]] = defaultdict(list)
    for kayit in kayitlar:
        obekler[kayit["iz"]].append(kayit)
    return [o for o in obekler.values() if len(o) > 1]


def ele(url: str = VERITABANI_URL, uygula: bool = False) -> tuple[list[dict], list[dict]]:
    """(silinecekler, tutulanlar) döner. `uygula` False ise yazma yapmaz."""
    korunacak = altin_set_kimlikleri()
    silinecek: list[dict] = []
    tutulan: list[dict] = []

    for obek in yinelenen_obekleri(url):
        sirali = sorted(obek, key=lambda k: _tutulma_onceligi(k, korunacak))
        tutulacak = sirali[0]
        tutulacak["kopya_sayisi"] = len(obek) - 1
        tutulan.append(tutulacak)
        for kayit in sirali[1:]:
            # ALTIN SET İKİ UÇTA BİRDEN OLABİLİR: aynı içerik iki adreste
            # etiketlenmişse ikisi de korunur. Nadir ama sessizce silmek
            # ölçümü bozardı; sayım şişkinliği ölçüm zemininden ucuzdur.
            if kayit["kampanya_id"] in korunacak:
                tutulan.append({**kayit, "kopya_sayisi": 0})
                continue
            kayit["tutulan"] = tutulacak["kampanya_id"]
            silinecek.append(kayit)

    if uygula and silinecek:
        with oturum(url) as oturum_:
            oturum_.execute(
                delete(KampanyaKaydi).where(
                    KampanyaKaydi.kampanya_id.in_([k["kampanya_id"] for k in silinecek])
                )
            )
            oturum_.commit()
    return silinecek, tutulan


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Yinelenen (aynı içerikli) kayıtları ele")
    ap.add_argument(
        "--uygula",
        action="store_true",
        help="gerçekten sil (varsayılan: yalnız göster)",
    )
    ap.add_argument(
        "--ayrinti",
        action="store_true",
        help="silinecek her kaydı tek tek listele",
    )
    args = ap.parse_args(argv[1:])

    silinecek, tutulan = ele(uygula=args.uygula)

    if not silinecek:
        print("Yinelenen kayıt yok.")
        return 0

    bankalar: dict[str, list[dict]] = defaultdict(list)
    for kayit in silinecek:
        bankalar[kayit["banka_adi"]].append(kayit)

    baslik = "SİLİNDİ" if args.uygula else "Silinecek (kuru çalıştırma)"
    print(f"{baslik}: {len(silinecek)} kayıt · {len(tutulan)} öbekten birer tane tutuldu")
    print()
    print(f"  {'banka':24}{'silinen':>9}")
    print("  " + "-" * 33)
    for ad in sorted(bankalar, key=lambda a: -len(bankalar[a])):
        print(f"  {ad[:22]:24}{len(bankalar[ad]):9}")

    if args.ayrinti:
        print()
        for kayit in sorted(silinecek, key=lambda k: (k["banka_kodu"], k["kaynak_url"])):
            print(f"  {kayit['kampanya_id']}  ...{kayit['kaynak_url'][-64:]}")
            print(f"      -> tutulan: {kayit['tutulan']}")

    if not args.uygula:
        print()
        print("Silmek için: make yinelenenleri-ele uygula=1")
        print("Tek tek görmek için: --ayrinti")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
