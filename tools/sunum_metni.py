"""Sunum slaytlarının okunabilir metin dökümü — `docs/sunum/sunum_icerik.txt`.

NEDEN VAR — 27 Ağustos'ta ölçülen durum:
    Depo kökünde elle üretilmiş bir `sunum_icerik.txt` duruyordu. İki kusuru
    vardı ve ikisi de elle üretilmiş olmasından geliyordu:

    1. KODLAMASI BOZUKTU. PDF'ten metin çıkarılırken yanlış kod sayfasıyla
       okunmuş, sonra öyle kaydedilmişti: «Katılım» yerine «Kat─▒l─▒m».
       Onarılamıyor — 870 karakter (ğ, ş, ç) kaydedilmeden önce kaybolmuş.

    2. RAKAMLARI BAYATTI. «1.024 işlenmiş kampanya» ve «755 geçen test»
       yazıyordu; o sırada gerçek değerler 931 ve 1.025'ti.

    Kaynak (`sunum.html`) depoda ve güncel — `tests/test_sunum_sayilari.py`
    onu `data/ablasyon.json` ile `docs/SONUCLAR.md`'ye bağlıyor. Dökümü elle
    tutmak, güncel bir kaynağın yanına bayat bir kopya koymak demekti.

    Bu araç dökümü KAYNAKTAN üretir. Slayt değişince tek komutla tazelenir;
    ikinci bir doğruluk kaynağı oluşmaz.

KULLANIM:
    make sunum-metni
"""

from __future__ import annotations

import sys
from pathlib import Path

from selectolax.parser import HTMLParser, Node

KOK = Path(__file__).resolve().parent.parent
KAYNAK = KOK / "docs" / "sunum" / "sunum.html"
CIKTI = KOK / "docs" / "sunum" / "sunum_icerik.txt"

# Metni olmayan, yalnız düzen taşıyan etiketler.
ATLANACAK = {"script", "style", "svg", "path", "br", "hr"}


def _metin_satirlari(dugum: Node) -> list[str]:
    """Belge sırasında, YAPRAK düğümlerden birer satır üretir.

    Neden yaprak: üst düğümün `text()`i tüm alt metni tek satırda birleştirir
    ve «1.024 işlenmiş kampanya 9 katılım bankası» gibi okunmaz bir dizi
    çıkar. Slaytta ayrı duran şey dökümde de ayrı satır olmalı.
    """
    satirlar: list[str] = []

    def gez(n: Node) -> None:
        if n.tag in ATLANACAK:
            return
        cocuklar = [c for c in n.iter(include_text=False)]
        if not cocuklar:
            metin = " ".join((n.text(deep=True) or "").split())
            if metin:
                satirlar.append(metin)
            return
        # Çocuk etiketleri var; aralarındaki düz metinler de kaybolmasın.
        for parca in n.iter(include_text=True):
            if parca.tag == "-text":
                duz = " ".join((parca.text(deep=False) or "").split())
                if duz:
                    satirlar.append(duz)
            else:
                gez(parca)

    gez(dugum)
    return satirlar


def dokum_uret(kaynak: Path = KAYNAK) -> str:
    agac = HTMLParser(kaynak.read_text(encoding="utf-8"))
    sayfalar = agac.css("section")
    if not sayfalar:
        raise ValueError(f"{kaynak} içinde <section> yok — slayt yapısı değişmiş olabilir.")

    parcalar = [f"Toplam sayfa: {len(sayfalar)}"]
    for sira, sayfa in enumerate(sayfalar, 1):
        parcalar.append(f"=== SAYFA {sira} ===")
        satirlar = _metin_satirlari(sayfa)
        if not satirlar:
            parcalar.append("(bu sayfada metin yok)")
        parcalar.extend(satirlar)
        parcalar.append("")
    return "\n".join(parcalar).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    if not KAYNAK.is_file():
        print(f"HATA: {KAYNAK.relative_to(KOK)} yok.")
        return 1

    metin = dokum_uret()
    CIKTI.write_text(metin, encoding="utf-8")

    sayfa_sayisi = metin.count("=== SAYFA ")
    print(f"{CIKTI.relative_to(KOK)} yazıldı")
    print(f"   {sayfa_sayisi} sayfa · {len(metin.splitlines())} satır · {len(metin)} karakter")
    return 0


if __name__ == "__main__":
    sys.exit(main())
