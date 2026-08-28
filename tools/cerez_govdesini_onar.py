"""Gövdesi ÇEREZ AYDINLATMA METNİ olan ham kayıtları saklı HTML'den onarır.

NEDEN VAR — ölçülen kusur ve NÜKSÜ:
Dünya Katılım'ın 38 kaydında `govde_metin`, kampanya metni değil 6971
karakterlik KVKK çerez aydınlatma metniydi. Sayfa doğruydu (`<title>`
kampanyanın adını veriyor) ve gerçek içerik de HTML'de duruyordu; kusur
trafilatura'nın ana içerik seçimindeydi — gizli duran onay modalı gerçek
içerikten uzun olduğu için «ana içerik» seçiliyordu.

Zararsız değil. Çıkarım bu metinden alan üretti ve ürettiği şey uydurma:

    vade_ay_max     33 kayıt   ← çerez saklama süresinden türemiş
    kar_payi_orani   7 kayıt
    indirim_orani    2 · kampanya_bitis 2 · odul_miktari 1

Yani korpusta, KVKK metninden türetilmiş bir «vade» verisi duruyordu —
kaynak alıntısıyla, yani güvenilir görünerek. Ziraat'in liste sayfalarıyla
aynı hata biçimi (bkz. `tools/liste_sayfalarini_ele.py`).

BU İKİNCİ DEFA. 27 Ağustos'ta `e86ac41` aynı kusuru giderdi
(«45 kaydın 44'ünde gövde aynı 7058 karakterlik sayfa iskeletiydi») ama
düzeltme VERİYE uygulandı, SEBEBE değil. 28 Ağustos'ta `2207ec4` ile
yeniden toplandığında kusur geri geldi — üstelik commit mesajı chatbot
cevaplarıyla ilgiliydi, veri değişikliği fark edilmeden içine bindi.

Sebep bu oturumda kapatıldı: `TemelKaziyici.cerez_katmanini_kaldir` çerez
katmanını gövde ayıklanmadan ÖNCE DOM'dan siliyor, yani bundan sonraki her
toplama temiz gövde üretir. Bu araç GEÇMİŞİ onarır; nöbetçisi
`tests/test_veri_kalitesi_cerez.py`.

NEDEN AĞA ÇIKMIYOR:
Her bozuk kaydın ham HTML'i `data/raw/<banka>/<kimlik>.html` altında zaten
duruyor. Sayfayı yeniden çekmek gereksiz site trafiği olurdu ve daha kötüsü,
bugünkü sayfa dünküyle aynı olmayabilir — şartname 5.1'in izlenebilirlik
kanıtı çekildiği ANDAKİ arşivdir. Onarım o arşivden yapılır.

SÖZCÜK DAĞARCIĞI TEK KAYNAKTAN: `temel_kaziyici.CEREZ_KATMANI_SECICILER`.
İkinci bir liste tutulsaydı, tarayıcı tarafındaki kapı ile buradaki onarım
sessizce ayrışırdı.

GÜVENLİK: Varsayılan koşu YAZMAZ, ne değişeceğini gösterir. Yazmak için
`--uygula` gerekir (`make cerez-govdesini-onar uygula=1`).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import trafilatura
from lxml import html as lxml_html

KOK = Path(__file__).resolve().parent.parent
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from src.collector.temel_kaziyici import CEREZ_KATMANI_SECICILER  # noqa: E402
from src.collector.toplayici import EN_AZ_GOVDE_UZUNLUGU, HAM_DIZIN  # noqa: E402

CEREZ_IZLERI = (
    "AYDINLATMA METNİ",
    "ÇEREZ KULLANIMINA",
    "COOKIE POLICY",
)
"""Gövdenin BAŞINDA geçtiğinde «bu kayıt çerez metni» diyen ifadeler.

Yalnız ilk `BAS_PENCERESI` karakterde aranır: bir kampanya sayfası da
altında çerez politikasına bağlantı taşıyabilir; onu bozuk saymak yanlış
olur. Bozuk kayıtta metin sayfanın TAMAMIDIR, yani en baştan başlar.
"""

BAS_PENCERESI = 300


def cerez_metni_mi(govde: str) -> bool:
    """Gövde bir çerez aydınlatma metni mi?"""
    bas = govde.upper()[:BAS_PENCERESI]
    return any(iz in bas for iz in CEREZ_IZLERI)


def cerez_katmanini_ayikla(ham_html: str) -> tuple[str, int]:
    """Çerez onay katmanını HTML'den siler. (temiz html, atılan öge sayısı).

    Tarayıcıdaki `CEREZ_KATMANI_JS` ile aynı ölçüt — orada `querySelectorAll`,
    burada lxml. İkisi de `CEREZ_KATMANI_SECICILER`'i okur.
    """
    agac = lxml_html.fromstring(ham_html)
    atilan = 0
    for oge in list(agac.xpath("//*[@class or @id]")):
        imza = f"{oge.get('class') or ''} {oge.get('id') or ''}".lower()
        if any(parca in imza for parca in CEREZ_KATMANI_SECICILER):
            ust = oge.getparent()
            if ust is not None:
                ust.remove(oge)
                atilan += 1
    return lxml_html.tostring(agac, encoding="unicode"), atilan


def govdeyi_uret(ham_html: str) -> str:
    """Temizlenmiş HTML'den gövde ayıklar — `_sayfayi_cek` ile aynı ayarlar."""
    temiz, _ = cerez_katmanini_ayikla(ham_html)
    return (
        trafilatura.extract(
            temiz,
            include_comments=False,
            include_tables=True,
            favor_recall=True,
        )
        or ""
    )


def bozuk_kayitlar(dizin: Path = HAM_DIZIN) -> list[Path]:
    """Gövdesi çerez metni olan JSON kayıtları."""
    bulunan: list[Path] = []
    for yol in sorted(dizin.rglob("*.json")):
        try:
            veri = json.loads(yol.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if cerez_metni_mi(veri.get("govde_metin") or ""):
            bulunan.append(yol)
    return bulunan


def onar(
    yollar: list[Path], *, uygula: bool = False
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Onarılabilenleri döndürür. (onarilan, onarilamayan)

    ONARILMIŞ SAYILMANIN KOŞULU DAR: yeni gövde hem eşiği geçmeli hem de
    artık çerez metni OLMAMALI. İkisinden biri tutmazsa kayda DOKUNULMAZ —
    bozuk bir gövdeyi başka bir bozuk gövdeyle değiştirmek onarım değildir.
    """
    onarilan: list[dict[str, object]] = []
    onarilamayan: list[dict[str, object]] = []
    for yol in yollar:
        veri = json.loads(yol.read_text(encoding="utf-8"))
        kimlik = yol.stem
        html_yolu = yol.with_suffix(".html")
        if not html_yolu.exists():
            onarilamayan.append(
                {"kimlik": kimlik, "url": veri.get("url", ""), "sebep": "HTML arşivi yok"}
            )
            continue
        yeni = govdeyi_uret(html_yolu.read_text(encoding="utf-8", errors="replace"))
        if len(yeni) < EN_AZ_GOVDE_UZUNLUGU:
            onarilamayan.append(
                {
                    "kimlik": kimlik,
                    "url": veri.get("url", ""),
                    "sebep": f"yeni gövde {len(yeni)} karakter, eşik {EN_AZ_GOVDE_UZUNLUGU}",
                }
            )
            continue
        if cerez_metni_mi(yeni):
            onarilamayan.append(
                {
                    "kimlik": kimlik,
                    "url": veri.get("url", ""),
                    "sebep": "temizlikten sonra da çerez metni",
                }
            )
            continue
        onarilan.append(
            {
                "kimlik": kimlik,
                "url": veri.get("url", ""),
                "eski": len(veri.get("govde_metin") or ""),
                "yeni": len(yeni),
            }
        )
        if uygula:
            veri["govde_metin"] = yeni
            yol.write_text(
                json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    return onarilan, onarilamayan


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Gövdesi çerez metni olan ham kayıtları saklı HTML'den onar"
    )
    ap.add_argument(
        "--uygula", action="store_true", help="gerçekten yaz (varsayılan: yalnız göster)"
    )
    args = ap.parse_args(argv[1:])

    yollar = bozuk_kayitlar()
    if not yollar:
        print("Gövdesi çerez metni olan kayıt yok.")
        return 0

    onarilan, onarilamayan = onar(yollar, uygula=args.uygula)

    baslik = "ONARILDI" if args.uygula else "Onarılacak (kuru çalıştırma)"
    print(f"{baslik}: {len(onarilan)} / {len(yollar)} kayıt")
    print()
    for kayit in onarilan:
        print(
            f"  {kayit['kimlik']}  {kayit['eski']:>5} -> {kayit['yeni']:>5} krk"
            f"  ...{str(kayit['url'])[-46:]}"
        )
    if onarilamayan:
        print()
        print(f"ONARILAMADI: {len(onarilamayan)} — kayda DOKUNULMADI")
        for kayit in onarilamayan:
            print(f"  {kayit['kimlik']}  {kayit['sebep']}")
            print(f"      ...{str(kayit['url'])[-58:]}")

    print()
    if not args.uygula:
        print("Yazmak için: make cerez-govdesini-onar uygula=1")
        print("  (Windows: .venv/Scripts/python.exe -m tools.cerez_govdesini_onar --uygula)")
        return 0

    kimlikler = " ".join(str(k["kimlik"]) for k in onarilan)
    print("Sırada — YALNIZ onarılan kimlikler için çıkarım:")
    print(f"  python -m src.boru_hatti extract --kimlik {kimlikler}")
    print()
    print("Ardından (korpus izi değişti): python -m src.boru_hatti vektor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
