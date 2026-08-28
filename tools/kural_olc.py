"""Kural katmanının altın set üzerindeki hızlı, DETERMİNİSTİK ölçümü.

NEDEN VAR — tam ölçüm bu iş için kullanılamaz:
    `make extract && make eval` yaklaşık 18 dakika sürüyor ve üstüne ±0,01
    gürültü taşıyor (EVREN ortak bir vLLM sunucusu; `temperature=0` bayt
    düzeyinde determinizm getirmiyor, bkz. ADR 013).
    Kural katmanındaki bir veto ya da desen değişikliğinin etkisi çoğu zaman
    o gürültü bandının içinde kalır — yani tam ölçümle ANLAŞILAMAZ.

    Bu araçta LLM yok, ağ yok, rastgelelik yok: aynı girdi her zaman aynı
    sayıyı verir. İki ölçüm arasındaki fark GERÇEK bir farktır.

 BURADAKİ MAKRO-F1 HİBRİT SKORLA KARŞILAŞTIRILAMAZ.
    `kampanya_turu`nun kural katmanında karşılığı yok, hep 0 çıkar; başka
    alanlar da LLM'siz doğal olarak zayıftır. Anlamlı olan tek şey AYNI
    ARAÇLA alınmış iki ölçümün farkıdır. Sunuma giren sayı `make eval`den
    çıkar, buradan değil.

Ölçülen yol kural katmanı + uzlaştırıcı kapılarıdır (LLM sözlüğü boş):
makullük ve veto denetimleri uzlaştırıcıda yaşıyor, onları atlayan bir
ölçüm tam da değiştirmek istediğimiz şeyi görmezdi.

    make kural-olc
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from src.depolama import kampanyalari_oku  # noqa: E402
from src.extraction.kural import kurallarla_cikar  # noqa: E402
from src.extraction.uzlastirici import uzlastir  # noqa: E402
from src.schema import HamKayit  # noqa: E402

GOLD = KOK / "data" / "gold"
ALTIN_SET = GOLD / "altin_set.jsonl"
METINLER = GOLD / "metinler"

ALANLAR = (
    "kampanya_turu",
    "kar_payi_orani",
    "vade_ay_max",
    "finansman_tutari_max",
    "tahsis_ucreti",
    "masrafsiz_mi",
    "odul_miktari",
    "kampanya_bitis",
)

CEKIM = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
"""Sabit çekim tarihi — `datetime.now()` kullanmak aracı tarihe bağımlı,
yani deterministik OLMAYAN hale getirirdi. Bağıl tarih çözen kurallar
(«kampanya 3 ay geçerli») aynı günü görmezse iki koşu farklı çıkar."""


def _esit(beklenen: object, bulunan: object, tolerans: float = 0.01) -> bool:
    """`eval/calistir.py::_degerler_esit` ile aynı sözleşme — %1 göreli tolerans."""
    if beklenen is None and bulunan is None:
        return True
    if beklenen is None or bulunan is None:
        return False
    if isinstance(beklenen, int | float) and isinstance(bulunan, int | float):
        buyuk = max(abs(float(beklenen)), abs(float(bulunan)))
        return buyuk == 0 or abs(float(beklenen) - float(bulunan)) / buyuk <= tolerans
    return str(beklenen).strip().lower() == str(bulunan).strip().lower()


def olc() -> dict[str, object]:
    altin = [
        json.loads(s)
        for s in ALTIN_SET.read_text(encoding="utf-8").splitlines()
        if s.strip() and not s.startswith("//")
    ]
    kim = {k.kampanya_id: k for k in kampanyalari_oku()}

    dp: Counter[str] = Counter()
    yp: Counter[str] = Counter()
    yn: Counter[str] = Counter()
    atlanan = 0

    for kayit in altin:
        kimlik = kayit["kampanya_id"]
        kampanya = kim.get(kimlik)
        metin_yolu = METINLER / f"{kimlik}.txt"
        if kampanya is None or not metin_yolu.exists():
            atlanan += 1
            continue

        metin = metin_yolu.read_text(encoding="utf-8")
        ham = HamKayit(
            banka_kodu=kimlik.split("-")[0],
            banka_adi=kampanya.banka_adi,
            url=kampanya.kaynak_url,
            cekim_tarihi=CEKIM,
            http_durum=200,
            govde_metin=metin,
        )
        kural_alanlari = kurallarla_cikar(metin, kampanya.kaynak_url, CEKIM)
        cikan, _ = uzlastir(kural_alanlari, {}, kayit=ham)

        for alan in ALANLAR:
            if alan not in kayit:
                continue
            beklenen = kayit[alan]
            bulunan = getattr(cikan, alan).deger
            if _esit(beklenen, bulunan):
                if beklenen is not None:
                    dp[alan] += 1
                continue
            if bulunan is not None:
                yp[alan] += 1
            if beklenen is not None:
                yn[alan] += 1

    return {"dp": dp, "yp": yp, "yn": yn, "atlanan": atlanan, "kayit": len(altin)}


def _f1(d: int, p: int, n: int) -> float | None:
    if d + p + n == 0:
        return None
    kesinlik = d / (d + p) if d + p else 0.0
    duyarlilik = d / (d + n) if d + n else 0.0
    return 2 * kesinlik * duyarlilik / (kesinlik + duyarlilik) if kesinlik + duyarlilik else 0.0


def rapor(sonuc: dict[str, object]) -> str:
    dp, yp, yn = sonuc["dp"], sonuc["yp"], sonuc["yn"]  # type: ignore[assignment]
    satirlar = [
        f"Kural katmanı ölçümü — {sonuc['kayit']} altın kayıt "
        f"(atlanan: {sonuc['atlanan']})  ·  LLM YOK, deterministik",
        "",
        f"{'alan':24}{'DP':>5}{'YP':>5}{'YN':>5}{'F1':>9}",
    ]
    f1ler: list[float] = []
    for alan in ALANLAR:
        d, p, n = dp[alan], yp[alan], yn[alan]  # type: ignore[index]
        f1 = _f1(d, p, n)
        if f1 is not None:
            f1ler.append(f1)
        satirlar.append(
            f"{alan:24}{d:>5}{p:>5}{n:>5}{('—' if f1 is None else f'{f1:.4f}'):>9}"
        )
    makro = sum(f1ler) / len(f1ler) if f1ler else 0.0
    satirlar += [
        "",
        f"{'MAKRO-F1 (kural katmanı)':24}{'':>15}{makro:>9.4f}",
        "",
        " Bu sayı `make eval`in hibrit makro-F1'iyle KARŞILAŞTIRILAMAZ.",
        "    Anlamlı olan: aynı araçla alınmış iki ölçümün FARKI.",
    ]
    return "\n".join(satirlar)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not ALTIN_SET.exists():
        print(" data/gold/altin_set.jsonl yok — önce `make altin-derle`")
        return 1
    print(rapor(olc()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
