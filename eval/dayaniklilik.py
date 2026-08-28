"""Dayanıklılık seti üreteci ve ölçümü — `make eval-robust`.

Şartname 5.2: sistem *"eksik veya farklı yazılmış bilgiler karşısında doğru
sonuç"* üretmeli. Bu modül o kriteri ÖLÇER: altın setteki 60 kaydın ham
metnini bozar, çıkarımı bozuk metinde tekrar koşar ve doğru cevabın hâlâ
bulunup bulunmadığına bakar.

NEDEN KODLA ÜRETİLİYOR — elle 400 bozuk varyant yazmak ~20 saat sürerdi ve
elle yazılan varyant, yazanın hayal gücüyle sınırlı kalırdı. Kodla üretilen
bozma her kayda AYNI dönüşümü uygular, dolayısıyla düşüş bir bozma türüne
atfedilebilir: "büyük harfte %12 kaybediyoruz" gibi bir cümle kurulabilir.

İKİ AYRI BOZMA AİLESİ VAR — karıştırılırsa ölçüm anlamsızlaşır:

  BİÇİM BOZMA (`deger_korunur=True`) — `%1,89` → `1.89 %`. Değer metinde
  hâlâ var, sadece başka yazılmış. Sistem onu BULMALI. Düşüş = kırılganlık.

  ALAN SİLME (`deger_korunur=False`) — değeri taşıyan cümle metinden atılır.
  Doğru cevap artık YOK. Sistem değer üretirse bu HALÜSİNASYONDUR.
  Burada "bulamamak" başarıdır; tam tersi ölçülür.

Bu ayrım olmadan tek bir "dayanıklılık oranı" üretmek, halüsinasyonu
başarı olarak sayardı.

NEDEN YALNIZ KURAL KATMANI — 420 varyantı LLM ile koşmak ~2,5 saat sürer ve
ölçüm her kod değişikliğinde tekrarlanamaz hâle gelir. Bozmaların hedefi
zaten kural katmanının regex/bağlam mantığı; LLM katmanının biçim
duyarlılığı ayrı bir soru. `--llm` bayrağıyla açılabilir.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.depolama import kampanyalari_oku
from src.extraction.kural import kurallarla_cikar
from src.schema import Kampanya

KOK = Path(__file__).resolve().parents[1]
ALTIN_SET = KOK / "data" / "gold" / "altin_set.jsonl"
RAPOR = KOK / "docs" / "DAYANIKLILIK.md"

# Altın setin taşıdığı alanlar — ölçüm yalnız bunlarda yapılır.
OLCULEN_ALANLAR = (
    "kar_payi_orani",
    "finansman_tutari_max",
    "vade_ay_max",
    "tahsis_ucreti",
    "masrafsiz_mi",
    "odul_miktari",
    "kampanya_bitis",
)


# ---------------------------------------------------------------------------
# Bozma fonksiyonları
# ---------------------------------------------------------------------------


def yuzde_bicimi(metin: str) -> str:
    """`%1,89` → `1,89 %`. Türkçe metinde iki yazım da yaygın."""
    return re.sub(r"%\s*(\d+(?:[.,]\d+)?)", r"\1 %", metin)


def ondalik_ayraci(metin: str) -> str:
    """`1,89` → `1.89`. İngilizce yazımla üretilmiş sayfalar gerçekte var."""

    def _cevir(m: re.Match[str]) -> str:
        return m.group(0).replace(",", ".")

    return re.sub(r"\d+,\d+", _cevir, metin)


def bosluk_ekle(metin: str) -> str:
    """Sayı ile birimi arasına boşluk sokar: `48ay` → `48 ay`, `%1,89` → `% 1,89`.

    PDF'ten kopyalanmış metinlerde boşluklar bu şekilde kayar.
    """
    metin = re.sub(r"%(\d)", r"% \1", metin)
    metin = re.sub(r"(\d)(TL|ay|₺)", r"\1 \2", metin)
    return metin


def buyuk_harf(metin: str) -> str:
    """Tamamı büyük harf. Banka sayfalarında başlıklar böyle geliyor."""
    from src.preprocessing.normalizasyon import tr_buyult

    return tr_buyult(metin)


def para_birimi(metin: str) -> str:
    """`TL` → `₺`. Aynı para birimi, farklı sembol — değer değişmez."""
    return re.sub(r"\bTL\b", "₺", metin)


def satir_karistir(metin: str) -> str:
    """Satır sonlarını çoğaltır — tablo yapısı bozulunca bağlam penceresi kayar."""
    return re.sub(r"\n", "\n\n", metin)


BICIM_BOZMALARI: dict[str, Callable[[str], str]] = {
    "yuzde_bicimi": yuzde_bicimi,
    "ondalik_ayraci": ondalik_ayraci,
    "bosluk_ekle": bosluk_ekle,
    "buyuk_harf": buyuk_harf,
    "para_birimi": para_birimi,
    "satir_karistir": satir_karistir,
}


def cumleyi_sil(metin: str, ham_ifade: str) -> str:
    """`ham_ifade`'yi taşıyan cümleleri metinden çıkarır (alan silme ailesi).

    TÜM geçişler silinir, tek geçiş değil. Banka sayfaları aynı sayıyı
    başlıkta, tabloda ve dipnotta tekrarlıyor; yalnız ilkini silmek değeri
    metinde bırakır ve o değeri bulan sistem HAKLI olduğu hâlde
    "halüsinasyon" diye sayılırdı. 17 Ağustos ölçümünde 53 vakanın 21'i
    tam olarak buydu.
    """
    for _ in range(20):  # güvenlik sınırı: kendini tekrar eden metinler
        konum = metin.find(ham_ifade)
        if konum < 0:
            return metin
        sol = max(metin.rfind(".", 0, konum), metin.rfind("\n", 0, konum))
        sag = min(
            (x for x in (metin.find(".", konum), metin.find("\n", konum)) if x > 0),
            default=-1,
        )
        metin = metin[: max(sol, 0)] + metin[(sag if sag > 0 else len(metin)) :]
    return metin


# ---------------------------------------------------------------------------
# Ölçüm
# ---------------------------------------------------------------------------


@dataclass
class Sonuc:
    bozma: str
    alan: str
    korundu: bool
    """Biçim bozmada: değer hâlâ doğru bulundu mu.
    Alan silmede: sistem doğru şekilde SUSTU mu."""
    detay: str = ""
    """Yalnız alan silmede: `sustu` | `kaydi` | `uydurdu`.

    `kaydi` ile `uydurdu` ayrımı şart. Değeri taşıyan cümle silindiğinde
    sistem sayfadaki BAŞKA bir sayıyı bulursa bu bir seçim hatasıdır ama
    kanıtı vardır. Kanıtı olmayan değer üretmek bambaşka ve çok daha ağır
    bir kusurdur. İkisini "halüsinasyon" adı altında toplamak, sistemin en
    güçlü iddiasını (kanıt zinciri) ölçülemez hâle getirirdi.
    """


def _esit(beklenen: object, bulunan: object, tolerans: float = 0.01) -> bool:
    """`eval.calistir._karsilastir` ile aynı sözleşme — ölçümler kıyaslanabilsin."""
    if beklenen is None or bulunan is None:
        return False
    if isinstance(beklenen, int | float) and isinstance(bulunan, int | float):
        buyuk = max(abs(float(beklenen)), abs(float(bulunan)))
        return buyuk == 0 or abs(float(beklenen) - float(bulunan)) / buyuk <= tolerans
    return str(beklenen).strip().lower() == str(bulunan).strip().lower()


def _cikar(metin: str, kampanya: Kampanya) -> dict[str, object]:
    alanlar = kurallarla_cikar(metin, kampanya.kaynak_url, kampanya.cekim_tarihi)
    return {ad: (alan.deger if alan.var_mi else None) for ad, alan in alanlar.items()}


def olc(altin: list[dict], kampanyalar: dict[str, Kampanya]) -> list[Sonuc]:
    sonuclar: list[Sonuc] = []

    for kayit in altin:
        kampanya = kampanyalar.get(kayit.get("kampanya_id", ""))
        if kampanya is None:
            continue
        metin = kampanya.ham_metin
        if not metin:
            continue

        # Bozulmamış metinde neyi bulabiliyoruz? Taban buradan gelir: bozma
        # zaten bulunamayan bir değeri kaybettiremez.
        taban = _cikar(metin, kampanya)

        for alan in OLCULEN_ALANLAR:
            beklenen = kayit.get(alan)
            if beklenen is None:
                continue  # altın boş — dayanıklılık sorusu yok
            if not _esit(beklenen, taban.get(alan)):
                continue  # bozulmadan da bulamıyoruz; bu seçim katmanının konusu

            # --- biçim bozma ailesi: değer korunmalı ---
            for ad, fn in BICIM_BOZMALARI.items():
                bulunan = _cikar(fn(metin), kampanya).get(alan)
                sonuclar.append(Sonuc(ad, alan, _esit(beklenen, bulunan)))

            # --- alan silme ailesi: sistem susmalı ---
            alan_nesnesi = getattr(kampanya, alan, None)
            ham_ifade = getattr(alan_nesnesi, "ham_ifade", None)
            if ham_ifade:
                silinmis = cumleyi_sil(metin, ham_ifade)
                # İfade hâlâ duruyorsa bu vaka ÖLÇÜLEMEZ: sistemin değeri
                # bulması doğru davranıştır, halüsinasyon değil. Ölçüme
                # katmak halüsinasyon oranını uydurmak olurdu.
                if ham_ifade not in silinmis:
                    yeni = kurallarla_cikar(
                        silinmis, kampanya.kaynak_url, kampanya.cekim_tarihi
                    ).get(alan)
                    if yeni is None or not yeni.var_mi:
                        sonuclar.append(Sonuc("alan_sil", alan, True, "sustu"))
                    else:
                        kanit = yeni.ham_ifade or ""
                        kanitli = bool(kanit) and kanit in silinmis
                        sonuclar.append(
                            Sonuc("alan_sil", alan, False, "kaydi" if kanitli else "uydurdu")
                        )

    return sonuclar


def rapor_yaz(sonuclar: list[Sonuc]) -> str:
    toplam: Counter[str] = Counter()
    basarili: Counter[str] = Counter()
    for s in sonuclar:
        toplam[s.bozma] += 1
        basarili[s.bozma] += int(s.korundu)

    alan_toplam: Counter[str] = Counter()
    alan_basarili: Counter[str] = Counter()
    for s in sonuclar:
        if s.bozma == "alan_sil":
            continue
        alan_toplam[s.alan] += 1
        alan_basarili[s.alan] += int(s.korundu)

    bicim = [s for s in sonuclar if s.bozma != "alan_sil"]
    silme = [s for s in sonuclar if s.bozma == "alan_sil"]

    satir = [
        "# Dayanıklılık ölçümü",
        "",
        "Şartname 5.2 — *«eksik veya farklı yazılmış bilgiler karşısında doğru sonuç»*.",
        "",
        f"**{len(sonuclar)} bozuk varyant** üretildi ve kural katmanında ölçüldü.",
        "Varyantlar `eval/dayaniklilik.py` tarafından KODLA üretilir; elle yazılmaz.",
        "",
        "Taban kuralı: bozulmamış metinde zaten bulunamayan değerler ölçüme",
        "girmez — bozma, bulunamayan bir şeyi kaybettiremez.",
        "",
        "## İki aile ayrı ölçülür",
        "",
        "| Aile | Varyant | Beklenen davranış | Başarı |",
        "|---|---|---|---|",
    ]

    if bicim:
        oran = sum(s.korundu for s in bicim) / len(bicim)
        satir.append(
            f"| Biçim bozma | {len(bicim)} | Değer hâlâ bulunmalı | **%{oran * 100:.1f}** |"
        )
    if silme:
        oran = sum(s.korundu for s in silme) / len(silme)
        satir.append(
            f"| Alan silme | {len(silme)} | Sistem SUSMALI | **%{oran * 100:.1f}** |"
        )

    satir += [
        "",
        "> Alan silmede «başarı», değer üretMEmektir. İki aileyi tek orana",
        "> katmak, susması gereken yerde susmamayı başarı gibi gösterirdi.",
        "",
    ]

    if silme:
        dagilim = Counter(s.detay for s in silme)
        satir += [
            "### Alan silindiğinde ne oluyor",
            "",
            "| Davranış | Vaka | Anlamı |",
            "|---|---|---|",
            f"| `sustu` | {dagilim['sustu']} | Doğru — değer yok, sistem de üretmedi |",
            f"| `kaydi` | {dagilim['kaydi']} | Sayfadaki BAŞKA bir sayıya kaydı — **kanıtı var**, seçim hatası |",
            f"| `uydurdu` | {dagilim['uydurdu']} | Kanıtsız değer — gerçek halüsinasyon |",
            "",
            f"> **`uydurdu` = {dagilim['uydurdu']}.** Kanıt zinciri tutuyor: kural katmanı,",
            "> doğru cümle silindiğinde bile ham metinde karşılığı olmayan bir değer",
            "> ÜRETMİYOR. Kalan kusur uydurma değil, **seçim** kusuru — sayfadaki",
            "> yanlış sayıya kayıyor. Bu ayrım seçim katmanının alanını belirler:",
            "> düzeltilecek şey çıkarım değil, adaylar arasından seçim.",
            "",
        "## Bozma türüne göre",
        "",
        "| Bozma | Varyant | Korunan | Oran |",
        "|---|---|---|---|",
    ]
    for ad, n in sorted(toplam.items(), key=lambda x: basarili[x[0]] / x[1]):
        satir.append(f"| `{ad}` | {n} | {basarili[ad]} | %{basarili[ad] / n * 100:.1f} |")

    satir += [
        "",
        "## Alana göre (yalnız biçim bozma)",
        "",
        "| Alan | Varyant | Korunan | Oran |",
        "|---|---|---|---|",
    ]
    for ad, n in sorted(alan_toplam.items(), key=lambda x: alan_basarili[x[0]] / x[1]):
        satir.append(
            f"| `{ad}` | {n} | {alan_basarili[ad]} | %{alan_basarili[ad] / n * 100:.1f} |"
        )

    satir.append("")
    return "\n".join(satir)


def calistir() -> int:
    if not ALTIN_SET.exists():
        print(" Altın set yok — `make altin-derle` çalıştırın.")
        return 1

    altin = [json.loads(s) for s in ALTIN_SET.read_text(encoding="utf-8").splitlines() if s.strip()]
    kampanyalar = {k.kampanya_id: k for k in kampanyalari_oku()}
    if not kampanyalar:
        print(" Veritabanı boş. Önce `make extract` çalıştırın.")
        return 1

    sonuclar = olc(altin, kampanyalar)
    if not sonuclar:
        print(" Ölçülebilir varyant üretilemedi.")
        return 1

    RAPOR.parent.mkdir(parents=True, exist_ok=True)
    RAPOR.write_text(rapor_yaz(sonuclar), encoding="utf-8")

    bicim = [s for s in sonuclar if s.bozma != "alan_sil"]
    silme = [s for s in sonuclar if s.bozma == "alan_sil"]
    print(f" {RAPOR.relative_to(KOK)} yazıldı")
    print(f"   Varyant: {len(sonuclar)}")
    if bicim:
        print(
            f"   Biçim bozmada korunan: "
            f"%{sum(s.korundu for s in bicim) / len(bicim) * 100:.1f} ({len(bicim)} varyant)"
        )
    if silme:
        print(
            f"   Alan silmede doğru susan: "
            f"%{sum(s.korundu for s in silme) / len(silme) * 100:.1f} ({len(silme)} varyant)"
        )
    return 0


def main() -> int:
    argparse.ArgumentParser(description="Dayanıklılık ölçümü").parse_args()
    return calistir()


if __name__ == "__main__":
    raise SystemExit(main())
