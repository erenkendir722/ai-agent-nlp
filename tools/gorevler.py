#!/usr/bin/env python3
"""Görev panosu okuyucu — "benim görevim ne?" sorusunun makine cevabı.

    python tools/gorevler.py                # herkesin durumu
    python tools/gorevler.py Esra           # yalnız Esra
    python tools/gorevler.py --dogrula      # panoyu denetle (bozuk bağımlılık, döngü)

NEDEN GEREKLİ:
    `GOREVLER.md` insan için yazıldı ve bağımlılıklar `⛔ Önce bitmeli:` satırıyla
    belirtiliyor. Ama 74 görevlik bir listede "benim sıradaki işim hangisi ve
    başlayabilir miyim?" sorusunu gözle cevaplamak zor. Bu araç grafiği çözer:

      - ✅ ŞU AN BAŞLAYABİLİRSİN  → tüm ön koşulları bitmiş, açık görevler
      - ⛔ ŞU AN YAPAMAZSIN       → hangi görev, kimde, neden bekliyor

    Böylece kimse boşta beklemiyor: bir iş bloke ise, aynı kişinin bloke olmayan
    bir sonraki işine geçiyor. Düşük kapasitede bloke olmak en pahalı şeydir.

Tek doğruluk kaynağı `GOREVLER.md` dosyasıdır; burada ayrı bir liste tutulmaz.
Pano düzenlendiğinde bu araç kendiliğinden güncel kalır.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
PANO = KOK / "GOREVLER.md"

_ASIL_SAHIPLER = {"E": "Eren", "S": "Samet", "G": "Görkem", "ES": "Esra", "H": "Herkes"}

# DEVREDİLEN GÖREVLER
#
# 18 Ağustos 2026: Samet çalışamaz durumda; `S-*` görevlerinin tamamı Eren'e
# devredildi. Görev KODLARI değiştirilmedi — `S-02`, `S-13` gibi kodlar
# `⛔ Önce bitmeli:` satırlarında, commit mesajlarında ve `docs/` içinde
# geçiyor; yeniden adlandırmak o referansların hepsini kırardı.
#
# Devir geri alınacaksa bu sözlükten ilgili satırı silmek yeterlidir.
DEVIR = {"S": "Eren"}

SAHIPLER = {onek: DEVIR.get(onek, ad) for onek, ad in _ASIL_SAHIPLER.items()}

# TEK GÖREV DEVRİ — ön ek değil, görev bazında.
#
# `DEVIR` bütün bir ön eki taşır (`S-*` → Eren). Bazen tek bir görevi taşımak
# gerekir: 24 Ağustos'ta Esra'nın 15 açık işi ve teslime 3 günü vardı, üstelik
# ES-17 tek başına üç görevi tıkıyordu. Video ve slayt onda kalmalıydı; ekran
# gerektirmeyen ES-15 (model çıktı örnekleri — veritabanından üretiliyor)
# Görkem'e verildi, çünkü 8 açık işle en az yüklü kişi oydu.
#
# Kod DEĞİŞTİRİLMEZ: `ES-15` referansları `⛔ Önce bitmeli:` satırlarında ve
# `docs/` içinde geçiyor. Yalnız sahibi değişir.
GOREV_DEVRI = {"ES-15": "Görkem"}


def sahip_bul(kod: str) -> str:
    """Görevin sahibi — önce tek görev devri, sonra ön ek devri."""
    if (devralan := GOREV_DEVRI.get(kod)) is not None:
        return devralan
    return SAHIPLER[kod.split("-")[0]]

# Büyük `[X]` de kabul edilir: 16 Ağustos'ta elle atılan üç `[X]` üç görevi
# panodan tamamen düşürdü ve onlara bağlı beş görev "tanımsız referans" verdi.
_GOREV = re.compile(r"^- \[([ xX])\] \*\*((?:ES|E|S|G|H)-\d{2})\*\*\s*(.*)$")
_ONCE = re.compile(r"^\s+⛔ \*\*Önce bitmeli:\*\*\s*(.+)$")
_KOD = re.compile(r"(ES|E|S|G|H)-\d{2}")
_TARIH = re.compile(r"📅\s*\*{0,2}([^·*\n]+?)\*{0,2}\s*$")


@dataclass
class Gorev:
    kod: str
    sahip: str
    baslik: str
    bitti: bool
    kritik: bool = False
    son_tarih: str = ""
    once: list[str] = field(default_factory=list)
    satir_no: int = 0


def panoyu_oku(yol: Path = PANO) -> dict[str, Gorev]:
    """GOREVLER.md'yi ayrıştırır. Kod bloklarındaki örnekler atlanır."""
    gorevler: dict[str, Gorev] = {}
    son: Gorev | None = None
    kod_blogu = False

    for no, satir in enumerate(yol.read_text(encoding="utf-8").split("\n"), 1):
        if satir.lstrip().startswith("```"):
            kod_blogu = not kod_blogu
            continue
        if kod_blogu:
            continue

        if (m := _GOREV.match(satir)) is not None:
            durum, kod, kalan = m.groups()
            temiz = re.sub(r"[*`🔴]", "", kalan).strip()
            baslik = temiz.split("·")[0].strip()
            tarih_m = _TARIH.search(kalan)
            son = Gorev(
                kod=kod,
                sahip=sahip_bul(kod),
                baslik=baslik or temiz,
                bitti=(durum.lower() == "x"),
                kritik="🔴" in kalan,
                son_tarih=tarih_m.group(1).strip() if tarih_m else "",
                satir_no=no,
            )
            # Aynı kod iki kez tanımlanmışsa ilkini koru, denetim yakalasın
            gorevler.setdefault(kod, son)
            continue

        if son is not None and (m := _ONCE.match(satir)) is not None:
            son.once = _kodlari_ayikla(m.group(1))

    return gorevler


def _kodlari_ayikla(metin: str) -> list[str]:
    return [m.group(0) for m in re.finditer(r"(?:ES|E|S|G|H)-\d{2}", metin)]


# ---------------------------------------------------------------------------
# Grafik çözümü
# ---------------------------------------------------------------------------


def engelleyenler(gorev: Gorev, gorevler: dict[str, Gorev]) -> list[Gorev]:
    """Bu görevi ŞU AN engelleyen, henüz bitmemiş ön koşullar."""
    return [
        gorevler[k]
        for k in gorev.once
        if k in gorevler and not gorevler[k].bitti
    ]


def bekleyenler(kod: str, gorevler: dict[str, Gorev]) -> list[Gorev]:
    """Bu görev bitmezse hangi görevler başlayamaz (doğrudan bağımlılar)."""
    return [g for g in gorevler.values() if kod in g.once and not g.bitti]


def dongu_bul(gorevler: dict[str, Gorev]) -> list[list[str]]:
    """Bağımlılık döngüsü — varsa hiçbir görev başlayamaz, panoyu kilitler."""
    dongular: list[list[str]] = []
    GRI, SIYAH = 1, 2
    renk: dict[str, int] = {}

    def gez(kod: str, yol: list[str]) -> None:
        renk[kod] = GRI
        for onceki in gorevler.get(kod, Gorev(kod, "?", "", False)).once:
            if onceki not in gorevler:
                continue
            if renk.get(onceki) == GRI:
                dongular.append(yol[yol.index(onceki):] + [onceki])
            elif renk.get(onceki) is None:
                gez(onceki, yol + [onceki])
        renk[kod] = SIYAH

    for kod in gorevler:
        if renk.get(kod) is None:
            gez(kod, [kod])
    return dongular


# ---------------------------------------------------------------------------
# Denetim
# ---------------------------------------------------------------------------


def dogrula(gorevler: dict[str, Gorev]) -> list[str]:
    sorunlar: list[str] = []

    for gorev in gorevler.values():
        for k in gorev.once:
            if k not in gorevler:
                sorunlar.append(
                    f"{gorev.kod} (satır {gorev.satir_no}) tanımsız bir göreve "
                    f"bağlı: {k}"
                )
            elif k == gorev.kod:
                sorunlar.append(f"{gorev.kod} kendine bağlı")

        # Bitmiş ama ön koşulu bitmemiş görev — tik erken atılmış olabilir
        if gorev.bitti:
            acik = [k for k in gorev.once if k in gorevler and not gorevler[k].bitti]
            if acik:
                sorunlar.append(
                    f"{gorev.kod} bitmiş işaretli ama ön koşulu açık: {', '.join(acik)}"
                )

    for dongu in dongu_bul(gorevler):
        sorunlar.append(f"DÖNGÜ: {' → '.join(dongu)}")

    return sorunlar


# ---------------------------------------------------------------------------
# Görüntüleme
# ---------------------------------------------------------------------------


def _satir(gorev: Gorev, ek: str = "") -> str:
    isaret = "🔴" if gorev.kritik else "  "
    tarih = f"📅 {gorev.son_tarih}" if gorev.son_tarih else ""
    return f"  {isaret} {gorev.kod:<6} {gorev.baslik[:52]:<52} {tarih}{ek}"


def kisi_raporu(ad: str, gorevler: dict[str, Gorev]) -> None:
    ad_kucuk = ad.casefold().replace("ı", "i")
    benim = [
        g for g in gorevler.values()
        if g.sahip.casefold().replace("ı", "i") == ad_kucuk or g.sahip == "Herkes"
    ]
    if not benim:
        print(f"'{ad}' diye biri yok. Geçerli adlar: {', '.join(sorted(set(SAHIPLER.values())))}")
        return

    acik = [g for g in benim if not g.bitti]
    hazir = [g for g in acik if not engelleyenler(g, gorevler)]
    bloke = [g for g in acik if engelleyenler(g, gorevler)]
    bitmis = [g for g in benim if g.bitti]
    kendi = len([g for g in acik if g.sahip != "Herkes"])
    ortak = len(acik) - kendi

    print(f"\n{'=' * 78}")
    print(f"  {ad.upper()} — {len(acik)} açık görev ({kendi} kendi + {ortak} ortak)")
    if bitmis:
        print(f"  Tiklenmiş: {len(bitmis)}")
    print(f"{'=' * 78}")

    if hazir:
        print(f"\n✅ ŞU AN BAŞLAYABİLİRSİN ({len(hazir)})")
        print(f"   Sıradaki işin: **{hazir[0].kod}**\n")
        for g in hazir:
            print(_satir(g))

    if bloke:
        print(f"\n⛔ ŞU AN YAPAMAZSIN ({len(bloke)}) — önce başkasının işi bitmeli\n")
        for g in bloke:
            engeller = engelleyenler(g, gorevler)
            print(_satir(g))
            for e in engeller:
                print(f"        └─ bekliyor: {e.kod} ({e.sahip}) — {e.baslik[:44]}")

    if not acik:
        print("\n🎉 Bütün görevlerin bitmiş.")

    kritik_acik = [g for g in hazir if g.kritik]
    if kritik_acik:
        print(f"\n🔴 Kritik ve şu an yapılabilir: {', '.join(g.kod for g in kritik_acik)}")


def genel_rapor(gorevler: dict[str, Gorev]) -> None:
    print(f"\n{'=' * 78}")
    print("  GÖREV PANOSU ÖZETİ")
    print(f"{'=' * 78}\n")
    print(f"  {'Kişi':<10}{'Açık':>6}{'Hazır':>7}{'Bloke':>7}{'Tikli':>7}   Sıradaki")
    print(f"  {'-' * 72}")

    for ad in ("Eren", "Görkem", "Esra", "Herkes"):
        benim = [g for g in gorevler.values() if g.sahip == ad]
        acik = [g for g in benim if not g.bitti]
        hazir = [g for g in acik if not engelleyenler(g, gorevler)]
        bloke = [g for g in acik if engelleyenler(g, gorevler)]
        bitmis = [g for g in benim if g.bitti]
        sirada = hazir[0].kod if hazir else "—"
        print(f"  {ad:<10}{len(acik):>6}{len(hazir):>7}{len(bloke):>7}{len(bitmis):>7}   {sirada}")

    print("\n  (Sprint 0'da biten kodsuz işler bu sayıma girmez — panonun")
    print("   «✅ bitenler» bölümlerinde duruyorlar.)")

    # En çok işi tıkayan görevler — bunlar öncelik sırasının gerçek tepesi
    darbogazlar = sorted(
        ((len(bekleyenler(k, g_)), k) for k, g_ in [(k, gorevler) for k in gorevler]),
        reverse=True,
    )[:5]
    print("\n  🚧 EN ÇOK İŞİ TIKAYAN GÖREVLER")
    for sayi, kod in darbogazlar:
        if sayi == 0 or gorevler[kod].bitti:
            continue
        g = gorevler[kod]
        bekleyen_kodlar = ", ".join(b.kod for b in bekleyenler(kod, gorevler))
        print(f"     {kod} ({g.sahip}) → {sayi} görevi tıkıyor: {bekleyen_kodlar}")

    print("\n  Kendi listen için:  python tools/gorevler.py <adın>")


def main(argv: list[str]) -> int:
    # Windows konsolu cp1254; panodaki ✅/⛔ işaretleri orada UnicodeEncodeError
    # fırlatıyordu — `make gorev-dogrula` doğrulamayı bitirip son satırda
    # çöküyordu. Yalnız CLI yolunda; testler modülü içe aktarırken dokunulmaz.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not PANO.exists():
        print(f"Pano bulunamadı: {PANO}")
        return 1

    gorevler = panoyu_oku()
    sorunlar = dogrula(gorevler)

    if "--dogrula" in argv:
        if sorunlar:
            print("❌ Panoda sorun var:")
            for s in sorunlar:
                print(f"   - {s}")
            return 1
        print(f"✅ Pano tutarlı — {len(gorevler)} görev, bağımlılıklar geçerli, döngü yok")
        return 0

    if sorunlar:
        print("\n⚠️  PANO UYARILARI")
        for s in sorunlar:
            print(f"   - {s}")

    adlar = [a for a in argv[1:] if not a.startswith("-")]
    if adlar:
        for ad in adlar:
            kisi_raporu(ad, gorevler)
    else:
        genel_rapor(gorevler)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
