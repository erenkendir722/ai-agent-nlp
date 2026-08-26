"""Çıkarım koşusunun kod parmak izini YENİ tanıma göre taşır (ADR 017).

NEDEN GEREKLİ
-------------
`CIKARIM_KAYNAKLARI` daraltıldı: `src/ajanlar` klasörünün tamamı yerine yalnız
çıkarım zamanı koşan ajanlar listede. Tanım değişince `kod_parmak_izi()` başka
bir değer üretiyor; veritabanındaki koşu kaydı ise ESKİ tanımla damgalanmış.
İkisi tutmayınca `cikarim_durumu()` "BAYAT" der — oysa çıkarılan tek bir değer
bile değişmemiştir.

NEDEN UYDURMA DEĞİL
-------------------
Damga körlemesine yazılmaz. Araç önce şunu ISPATLAR: dar kümedeki dosyalar,
veritabanının çıkarıldığı commit'ten bu yana **bayt bayt aynı**. Aynıysa yeni
tanımın o koşudaki değeri, bugün hesaplanan değerle özdeştir — yeniden çıkarım
yapmadan bilinebilir. Aynı değilse araç YAZMAZ ve yeniden çıkarım ister.

Bu, `Alan(deger=..., yontem="belirtilmemis")` yasağının aynı refleksi:
kanıtlanmamış bir değer kaydedilmez.

KULLANIM
--------
    python tools/parmak_izi_goc.py              # yalnız gösterir (kuru koşu)
    python tools/parmak_izi_goc.py --uygula     # damgayı yazar
    python tools/parmak_izi_goc.py --referans <commit>
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from src.depolama import (  # noqa: E402
    CIKARIM_KAYNAKLARI,
    CikarimKosusu,
    VERITABANI_URL,
    cikarim_durumu,
    kod_parmak_izi,
    oturum,
)


def _git(*argv: str) -> str:
    sonuc = subprocess.run(
        ["git", *argv], cwd=KOK, capture_output=True, text=True, check=False
    )
    if sonuc.returncode != 0:
        raise RuntimeError(f"git {' '.join(argv)} başarısız: {sonuc.stderr.strip()}")
    return sonuc.stdout.strip()


def _veritabani_commiti() -> str:
    """Veritabanına en son dokunan commit — çıkarımın kaydedildiği yer."""
    cikti = _git("log", "-1", "--format=%H", "--", "data/katilim.db")
    if not cikti:
        raise RuntimeError(
            "data/katilim.db için commit bulunamadı; --referans ile elle verin."
        )
    return cikti


def _degisen_dosyalar(referans: str) -> list[str]:
    """Dar kümede referanstan bu yana değişen dosyalar (commit'li + çalışma ağacı)."""
    kaynaklar = list(CIKARIM_KAYNAKLARI)
    commitli = _git("diff", "--name-only", referans, "HEAD", "--", *kaynaklar)
    calisma = _git("diff", "--name-only", "HEAD", "--", *kaynaklar)
    return sorted({*commitli.splitlines(), *calisma.splitlines()} - {""})


def main() -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--uygula", action="store_true", help="damgayı yaz")
    ayristirici.add_argument("--referans", help="çıkarımın yapıldığı commit")
    ayristirici.add_argument("--url", default=VERITABANI_URL)
    args = ayristirici.parse_args()

    durum = cikarim_durumu(args.url)
    if durum.get("kosu") is None:
        print(" Veritabanında çıkarım koşusu kaydı yok. Önce `make extract`.")
        return 1

    kosu = durum["kosu"]
    yeni_iz = kod_parmak_izi()
    eski_iz = kosu.get("kod_parmak_izi")

    referans = args.referans or _veritabani_commiti()
    print(f"  çıkarım koşusu   : {kosu['zaman']:%d.%m.%Y %H:%M} · {kosu['yapilandirma']}")
    print(f"  referans commit  : {referans[:12]}")
    print(f"  depolanan damga  : {eski_iz}")
    print(f"  yeni tanımla     : {yeni_iz}")
    print(f"  dar küme         : {len(CIKARIM_KAYNAKLARI)} girdi")

    if eski_iz == yeni_iz:
        print("\n Damga zaten güncel — yapılacak bir şey yok.")
        return 0

    degisenler = _degisen_dosyalar(referans)
    if degisenler:
        print("\n GÖÇ REDDEDİLDİ — çıkarım kaynakları o koşudan beri değişmiş:")
        for dosya in degisenler:
            print(f"     {dosya}")
        print("\n   Bu gerçek bir bayatlıktır. Çözüm: `make extract`.")
        return 1

    print("\n İSPAT: dar kümedeki hiçbir dosya referans commit'ten beri değişmemiş.")
    print("   Yeni tanımın o koşudaki değeri = bugün hesaplanan değer.")

    if not args.uygula:
        print("\n(kuru koşu — yazmak için `--uygula`)")
        return 0

    with oturum(args.url) as oturum_:
        kayit = (
            oturum_.query(CikarimKosusu).order_by(CikarimKosusu.id.desc()).first()
        )
        kayit.kod_parmak_izi = yeni_iz
        oturum_.commit()

    sonra = cikarim_durumu(args.url)
    print(f"\n Damga taşındı: {eski_iz} → {yeni_iz}")
    print(f"   bayat: {sonra['bayat']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
