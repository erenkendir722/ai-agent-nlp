"""Değerlendirme koşum takımı — `make eval` (şartname %30'luk kriter).

    make eval             # tüm metrikler -> docs/SONUCLAR.md
    make eval-ablation    # kural / LLM / hibrit karşılaştırması

TASARIM İLKESİ — sonuçlar OTOMATİK markdown tabloya yazılır.
Sunum günü elle rakam kopyalamak hata kaynağıdır; jüriye yanlış sayı söylemek
metriğin kendisinden daha pahalıya patlar.

İki metrik sınıfı vardır:

  ALTIN SET GEREKTİRMEYENLER — bugün çalışır:
    halüsinasyon oranı, şema geçerliliği, alan doluluğu, yöntem dağılımı,
    güven dağılımı, çelişki sayısı

  ALTIN SET GEREKTİRENLER — altın set 15 Ağustos'ta geldi, aktif:
    alan bazlı doğruluk, kesinlik/duyarlılık/F1, makro-F1
    (dayanıklılık düşüşü S-07'nin bozuk varyant üreticisini bekliyor)

Altın set yoksa ikinci grup "beklemede" olarak raporlanır; koşu ÇÖKMEZ.

DOĞRULUK TEK BAŞINA OKUNMAZ — altın setin çoğu hücresi boştur, dolayısıyla
«iki taraf da boş» hücreler doğruluğu şişirir. Rapordaki *hep boş* sütunu
hiçbir şey çıkarmayan bir sistemin alacağı doğruluğu gösterir; doğruluk onun
altındaysa sistem o alanda zarar veriyordur. Karşılaştırılabilir tek sayı
makro-F1'dir (bkz. `altin_set_metrikleri`).
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from src.depolama import cikarim_durumu, kampanyalari_oku
from src.schema import ALAN_ADLARI, METINSEL_ALANLAR, SAYISAL_ALANLAR, Kampanya

KOK = Path(__file__).resolve().parents[1]
ALTIN_SET = KOK / "data" / "gold" / "altin_set.jsonl"
SONUC_DOSYASI = KOK / "docs" / "SONUCLAR.md"


# ---------------------------------------------------------------------------
# Altın set gerektirmeyen metrikler
# ---------------------------------------------------------------------------


def temel_metrikler(kampanyalar: list[Kampanya]) -> dict[str, Any]:
    if not kampanyalar:
        return {"kampanya_sayisi": 0}

    toplam_alan = 0
    dolu_alan = 0
    yontem_sayaci: Counter[str] = Counter()
    guvenler: list[float] = []
    ihlal_sayisi = 0
    ihlal_ornekleri: list[str] = []

    for kampanya in kampanyalar:
        for _, alan in kampanya.cikarilan_alanlar().items():
            toplam_alan += 1
            if alan.var_mi:
                dolu_alan += 1
                yontem_sayaci[alan.yontem] += 1
                guvenler.append(alan.guven)

        ihlaller = kampanya.kanit_denetimi()
        ihlal_sayisi += len(ihlaller)
        ihlal_ornekleri.extend(ihlaller[:2])

    return {
        "kampanya_sayisi": len(kampanyalar),
        "banka_sayisi": len({k.banka_kodu for k in kampanyalar}),
        "toplam_alan": toplam_alan,
        "dolu_alan": dolu_alan,
        "alan_dolulugu": dolu_alan / toplam_alan if toplam_alan else 0.0,
        # Şema geçerliliği: kayıtlar Kampanya olarak doğrulanarak okundu,
        # dolayısıyla ayrıştırma hatası kategorisi yapısal olarak mümkün değil.
        "sema_gecerliligi": 1.0,
        "halusinasyon_sayisi": ihlal_sayisi,
        "halusinasyon_orani": ihlal_sayisi / dolu_alan if dolu_alan else 0.0,
        "halusinasyon_ornekleri": ihlal_ornekleri[:10],
        "yontem_dagilimi": dict(yontem_sayaci),
        "ortalama_guven": sum(guvenler) / len(guvenler) if guvenler else 0.0,
    }


def alan_bazli_doluluk(kampanyalar: list[Kampanya]) -> dict[str, float]:
    """Hangi alanlar sık boş kalıyor? Kural/istem iyileştirmesinin yol haritası."""
    sayac: Counter[str] = Counter()
    for kampanya in kampanyalar:
        for ad, alan in kampanya.cikarilan_alanlar().items():
            if alan.var_mi:
                sayac[ad] += 1
    n = len(kampanyalar) or 1
    return {ad: sayac.get(ad, 0) / n for ad in ALAN_ADLARI}


# ---------------------------------------------------------------------------
# Altın set gerektiren metrikler
# ---------------------------------------------------------------------------


def altin_seti_yukle() -> list[dict[str, Any]]:
    if not ALTIN_SET.exists():
        return []
    return [
        json.loads(satir)
        for satir in ALTIN_SET.read_text(encoding="utf-8").splitlines()
        if satir.strip() and not satir.startswith("//")
    ]


def _degerler_esit(beklenen: Any, bulunan: Any, tolerans: float = 0.01) -> bool:
    if beklenen is None and bulunan is None:
        return True
    if beklenen is None or bulunan is None:
        return False
    if isinstance(beklenen, int | float) and isinstance(bulunan, int | float):
        buyuk = max(abs(float(beklenen)), abs(float(bulunan)))
        return buyuk == 0 or abs(float(beklenen) - float(bulunan)) / buyuk <= tolerans
    return str(beklenen).strip().lower() == str(bulunan).strip().lower()


def _f1(dogru_pozitif: int, yanlis_pozitif: int, yanlis_negatif: int) -> dict[str, float | None]:
    """Bir alanın kesinlik / duyarlılık / F1 üçlüsü.

    Hiç pozitif hücre yoksa (altın da sistem de o alanda hiç değer üretmemiş)
    üçü de None döner — sıfır DEĞİL. Gerekçe `ortalama()` ile aynı: ölçülmemişi
    başarısız göstermek, ölçmemekten kötüdür.
    """
    if dogru_pozitif + yanlis_pozitif + yanlis_negatif == 0:
        return {"kesinlik": None, "duyarlilik": None, "f1": None}
    kesinlik = (
        dogru_pozitif / (dogru_pozitif + yanlis_pozitif)
        if dogru_pozitif + yanlis_pozitif
        else 0.0
    )
    duyarlilik = (
        dogru_pozitif / (dogru_pozitif + yanlis_negatif)
        if dogru_pozitif + yanlis_negatif
        else 0.0
    )
    toplam = kesinlik + duyarlilik
    return {
        "kesinlik": kesinlik,
        "duyarlilik": duyarlilik,
        "f1": 2 * kesinlik * duyarlilik / toplam if toplam else 0.0,
    }


def altin_set_metrikleri(kampanyalar: list[Kampanya]) -> dict[str, Any] | None:
    """Altın sete karşı alan bazlı doğruluk, F1 ve makro-F1. Set yoksa None.

    NEDEN F1 DE ÖLÇÜLÜYOR — doğruluk tek başına yanıltıyor:
        Altın setin çoğu hücresi boş (`kar_payi_orani` 60 örnekte yalnız 10
        kez dolu). Doğruluk «iki taraf da boş» hücreleri DOĞRU sayar, yani
        hiçbir şey çıkarmayan bir sistem `odul_miktari`'nda 0,950 doğruluk
        alır. Gerçek başarı, değer ÜRETİLMESİ gereken hücrelerde ölçülür.

        F1 doğru negatifi hiç saymaz: yalnız bir taraf değer ürettiğinde
        sayaç işler. Bu yüzden aşırı çıkarım (boş olması gereken yere değer
        yazmak) doğruluğu az, F1'i çok düşürür — istediğimiz tam olarak bu.

    Yuva doldurma (slot filling) sözleşmesi:
        DP — altın dolu, sistem dolu, değerler eşit
        YP — sistem değer üretti ama isabet etmedi (altın boş ya da farklı)
        YN — altın dolu ama sistem ıskaladı (boş bıraktı ya da yanlış yazdı)

        Yanlış değer hem YP hem YN sayılır: hem uydurulmuş bir değerdir hem de
        doğru cevap kaçırılmıştır. Tek sayaca yazmak ikisinden birini gizlerdi.
    """
    altin = altin_seti_yukle()
    if not altin:
        return None

    kimlik_kampanya = {k.kampanya_id: k for k in kampanyalar}
    dogru: Counter[str] = Counter()
    toplam: Counter[str] = Counter()
    dp: Counter[str] = Counter()
    yp: Counter[str] = Counter()
    yn: Counter[str] = Counter()
    altin_bos: Counter[str] = Counter()

    for kayit in altin:
        kampanya = kimlik_kampanya.get(kayit.get("kampanya_id", ""))
        if kampanya is None:
            continue
        for alan_adi in ALAN_ADLARI:
            if alan_adi not in kayit:
                continue
            toplam[alan_adi] += 1
            beklenen = kayit[alan_adi]
            bulunan = getattr(kampanya, alan_adi).deger
            isabet = _degerler_esit(beklenen, bulunan)
            if isabet:
                dogru[alan_adi] += 1
            if beklenen is None:
                altin_bos[alan_adi] += 1
            if isabet and beklenen is not None:
                dp[alan_adi] += 1
            else:
                if bulunan is not None:
                    yp[alan_adi] += 1
                if beklenen is not None:
                    yn[alan_adi] += 1

    def ortalama(alanlar: tuple[str, ...]) -> float | None:
        """Karşılaştırılacak hücre yoksa None — sıfır DEĞİL.

        Altın set yalnız sekiz çekirdek alanı taşıyor (bkz. ADR 008), yani
        `METINSEL_ALANLAR` için hiç hücre yok. Sıfır döndürmek raporda
        «0,000 ❌» yazdırırdı: sistem o alanlarda başarısız oldu demek olur,
        oysa gerçek şu ki o alanlar hiç ölçülmedi. Ölçülmemişi başarısız
        göstermek, ölçmemekten daha kötüdür.
        """
        d = sum(dogru[a] for a in alanlar)
        t = sum(toplam[a] for a in alanlar)
        return d / t if t else None

    alan_f1 = {a: _f1(dp[a], yp[a], yn[a]) for a in ALAN_ADLARI}
    olculen = [d["f1"] for d in alan_f1.values() if d["f1"] is not None]

    return {
        "eslesen_ornek": sum(1 for k in altin if k.get("kampanya_id") in kimlik_kampanya),
        "altin_set_boyutu": len(altin),
        "sayisal_dogruluk": ortalama(SAYISAL_ALANLAR),
        "metinsel_dogruluk": ortalama(METINSEL_ALANLAR),
        "alan_bazli": {a: (dogru[a] / toplam[a] if toplam[a] else None) for a in ALAN_ADLARI},
        # Makro-F1 alanları EŞİT ağırlıklar: nadir ama kritik bir alan (örn.
        # tahsis_ucreti) sık alanların içinde erimesin. Mikro ortalama alsaydık
        # tablo, en çok hücresi olan alanın performansını gösterirdi.
        "makro_f1": sum(olculen) / len(olculen) if olculen else None,
        "alan_f1": alan_f1,
        "sayimlar": {a: {"dp": dp[a], "yp": yp[a], "yn": yn[a]} for a in ALAN_ADLARI},
        # «Hep boş bırak» tabanı: hiçbir şey çıkarmayan sistemin doğruluğu.
        # Doğruluk sütununun yanına konunca metriğin şişkinliği görünür olur.
        "hep_bos_tabani": {
            a: (altin_bos[a] / toplam[a] if toplam[a] else None) for a in ALAN_ADLARI
        },
    }


# ---------------------------------------------------------------------------
# Raporlama
# ---------------------------------------------------------------------------

HEDEFLER = {
    "sayisal_dogruluk": 0.90,
    "metinsel_dogruluk": 0.78,
    "sema_gecerliligi": 1.00,
    "halusinasyon_orani": 0.03,
    # F1 hedefi şemadan geliyor (`METINSEL_ALANLAR` açıklaması: «alan bazlı F1
    # ile ölçülür, hedef ≥0,78»). Makro-F1 aynı çıtayı tüm alanlara uygular.
    "makro_f1": 0.78,
}


def _oran(deger: float | None) -> str:
    return "ölçülmedi" if deger is None else f"{deger:.3f}"


def _durum(ad: str, deger: float | None) -> str:
    if deger is None:
        return "—"  # ölçülmedi; başarısız değil
    hedef = HEDEFLER.get(ad)
    if hedef is None:
        return "—"
    if ad == "halusinasyon_orani":
        return "✅" if deger <= hedef else "❌"
    return "✅" if deger >= hedef else "❌"


def _kokenlik_notu(durum: dict[str, Any]) -> list[str]:
    """Raporun EN BAŞINA giden bayatlık uyarısı.

    Başa konuyor çünkü aşağıdaki her sayı bu uyarıya bağlı: kod değiştiyse
    tablolar eski çıkarımı anlatır. Sonuna konsa, sayıyı kopyalayan kişi
    uyarıyı görmeden kopyalamış olurdu.
    """
    kosu = durum.get("kosu")
    if not durum.get("bayat"):
        return [
            f"> ✅ **Güncel.** Çıkarım {kosu['zaman']:%d.%m.%Y %H:%M}'de "
            f"`{kosu['yapilandirma']}` yapılandırmasıyla koştu "
            f"({kosu['kayit_sayisi']} kayıt) ve o tarihten beri çıkarım kodu değişmedi.",
            "",
        ]
    satirlar = [
        "> 🔴 **BAYAT — bu sayıları sunuma kopyalamayın.**",
        f"> {durum.get('sebep', '')}",
    ]
    if kosu:
        satirlar.append(
            f"> Kayıtlı koşu: `{kosu['yapilandirma']}` yapılandırması, "
            f"{kosu['kayit_sayisi']} kayıt."
        )
    satirlar += ["> Düzeltmek için: `make extract && make eval`.", ""]
    return satirlar


def rapor_yaz(
    temel: dict[str, Any],
    altin: dict[str, Any] | None,
    doluluk: dict[str, float],
    kokenlik: dict[str, Any] | None = None,
) -> str:
    s: list[str] = [
        "# Değerlendirme Sonuçları",
        "",
        f"_Otomatik üretildi: {datetime.now():%d.%m.%Y %H:%M} · `make eval`_",
        "",
        "> Bu dosya elle düzenlenmez. Sunumdaki her sayı buradan kopyalanır.",
        "",
    ]
    if kokenlik is not None:
        s += _kokenlik_notu(kokenlik)
    s += [
        "## Veri kapsamı",
        "",
        f"- İşlenen kampanya: **{temel.get('kampanya_sayisi', 0)}**",
        f"- Banka sayısı: **{temel.get('banka_sayisi', 0)}**",
        f"- Toplam alan: {temel.get('toplam_alan', 0)} · Dolu: {temel.get('dolu_alan', 0)}",
        "",
        "## Altın set gerektirmeyen metrikler",
        "",
        "| Metrik | Değer | Hedef | Durum |",
        "|---|---|---|---|",
    ]

    s.append(
        f"| Şema geçerliliği | {temel.get('sema_gecerliligi', 0):.2f} | 1,00 | "
        f"{_durum('sema_gecerliligi', temel.get('sema_gecerliligi', 0))} |"
    )
    hal = temel.get("halusinasyon_orani", 0.0)
    s.append(
        f"| **Halüsinasyon oranı** | %{hal * 100:.2f} | ≤ %3 | {_durum('halusinasyon_orani', hal)} |"
    )
    s.append(f"| Alan doluluğu | %{temel.get('alan_dolulugu', 0) * 100:.1f} | — | — |")
    s.append(f"| Ortalama güven | {temel.get('ortalama_guven', 0):.3f} | — | — |")
    s.append("")

    s += ["## Yöntem dağılımı (ablasyonun temeli)", "", "| Yöntem | Alan sayısı |", "|---|---|"]
    for yontem, sayi in sorted(temel.get("yontem_dagilimi", {}).items(), key=lambda x: -x[1]):
        s.append(f"| `{yontem}` | {sayi} |")
    s.append("")

    if temel.get("halusinasyon_ornekleri"):
        s += ["## Halüsinasyon örnekleri (hata analizi)", ""]
        s += [f"- `{ornek}`" for ornek in temel["halusinasyon_ornekleri"]]
        s.append("")

    s += ["## Alan bazlı doluluk", "", "| Alan | Doluluk |", "|---|---|"]
    for ad, oran in sorted(doluluk.items(), key=lambda x: -x[1]):
        s.append(f"| `{ad}` | %{oran * 100:.0f} |")
    s.append("")

    s += ["## Altın set metrikleri", ""]
    if altin is None:
        s += [
            "> ⏳ **Beklemede.** `data/gold/altin_set.jsonl` henüz yok.",
            "> Altın set olmadan alan bazlı doğruluk, F1 ve makro-F1 hesaplanamaz.",
            "> Bunlar şartnamenin %30'luk «Model Başarısı» kriterinin temelidir.",
            "> **Son tarih: 16 Ağustos 2026.**",
            "",
        ]
    else:
        s += [
            f"- Altın set boyutu: **{altin['altin_set_boyutu']}** örnek "
            f"(eşleşen: {altin['eslesen_ornek']})",
            "",
            "| Metrik | Değer | Hedef | Durum |",
            "|---|---|---|---|",
            f"| Sayısal alan doğruluğu | {_oran(altin['sayisal_dogruluk'])} | ≥ 0,90 | "
            f"{_durum('sayisal_dogruluk', altin['sayisal_dogruluk'])} |",
            f"| Metinsel alan doğruluğu | {_oran(altin['metinsel_dogruluk'])} | ≥ 0,78 | "
            f"{_durum('metinsel_dogruluk', altin['metinsel_dogruluk'])} |",
            f"| **Makro-F1** | {_oran(altin['makro_f1'])} | ≥ 0,78 | "
            f"{_durum('makro_f1', altin['makro_f1'])} |",
            "",
            "> Metinsel alanlar altın sette etiketlenmiyor (ADR 008): yalnız LLM "
            "katmanından geliyorlar ve birebir string karşılaştırmasıyla ölçülemezler.",
            "",
            "### Alan bazlı doğruluk ve F1",
            "",
            "> **Doğruluk sütununu tek başına okumayın.** Altın setin çoğu hücresi "
            "boş, dolayısıyla «iki taraf da boş» hücreler doğruluğu şişiriyor. "
            "*Hep boş* sütunu, hiçbir şey çıkarmayan bir sistemin alacağı "
            "doğruluktur: doğruluk o sütunun altındaysa, sistem o alanda "
            "hiçbir şey yapmamaktan daha kötüdür. F1 doğru negatifi saymaz, "
            "bu yüzden gerçek başarıyı gösterir.",
            "",
            "| Alan | Doğruluk | Hep boş | Kesinlik | Duyarlılık | **F1** | DP/YP/YN |",
            "|---|---|---|---|---|---|---|",
        ]
        for ad, deger in altin["alan_bazli"].items():
            olcum = altin["alan_f1"][ad]
            sayim = altin["sayimlar"][ad]
            taban = altin["hep_bos_tabani"][ad]
            # Tabanın altına düşen alan, aşırı çıkarım yapıyor demektir.
            isaret = (
                " ⚠️"
                if deger is not None and taban is not None and deger < taban
                else ""
            )
            s.append(
                f"| `{ad}` | {'—' if deger is None else f'{deger:.3f}'}{isaret} "
                f"| {'—' if taban is None else f'{taban:.3f}'} "
                f"| {_oran(olcum['kesinlik'])} | {_oran(olcum['duyarlilik'])} "
                f"| **{_oran(olcum['f1'])}** "
                f"| {sayim['dp']}/{sayim['yp']}/{sayim['yn']} |"
            )
        s.append("")
        s += [
            "> ⚠️ = doğruluk «hep boş» tabanının altında. Bu alanlarda sistem "
            "boş olması gereken hücrelere değer yazıyor (yanlış pozitif); "
            "önce kesinliği düzeltmek gerekir.",
            "",
            "> **DP/YP/YN** — doğru pozitif / yanlış pozitif / yanlış negatif. "
            "Yanlış değer hem YP hem YN sayılır: uydurulmuş bir değerdir ve "
            "aynı anda doğru cevap kaçırılmıştır.",
            "",
        ]

    return "\n".join(s)


def calistir(ablasyon: bool = False) -> int:
    kampanyalar = list(kampanyalari_oku())
    if not kampanyalar:
        print("❌ Veritabanı boş. Önce `make crawl && make extract` çalıştırın.")
        return 1

    temel = temel_metrikler(kampanyalar)
    altin = altin_set_metrikleri(kampanyalar)
    doluluk = alan_bazli_doluluk(kampanyalar)
    kokenlik = cikarim_durumu()

    icerik = rapor_yaz(temel, altin, doluluk, kokenlik)
    if ablasyon:
        icerik += _ablasyon_notu()

    SONUC_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    SONUC_DOSYASI.write_text(icerik, encoding="utf-8")

    print(f"✅ {SONUC_DOSYASI.relative_to(KOK)} yazıldı")
    if kokenlik["bayat"]:
        print(f"   🔴 BAYAT — {kokenlik['sebep']}")
        print("      Sunuma sayı kopyalamadan önce: make extract && make eval")
    print(f"   Kampanya: {temel['kampanya_sayisi']} · Banka: {temel['banka_sayisi']}")
    print(f"   Halüsinasyon oranı: %{temel['halusinasyon_orani'] * 100:.2f} (hedef ≤ %3)")
    print(f"   Alan doluluğu: %{temel['alan_dolulugu'] * 100:.1f}")
    if altin is None:
        print("   ⏳ Altın set yok — doğruluk metrikleri beklemede (son tarih 16 Ağustos)")
    else:
        print(
            f"   Sayısal doğruluk: {_oran(altin['sayisal_dogruluk'])} (hedef ≥ 0,90) · "
            f"Makro-F1: {_oran(altin['makro_f1'])} (hedef ≥ 0,78)"
        )
        zayif = [
            ad
            for ad, deger in altin["alan_bazli"].items()
            if deger is not None
            and altin["hep_bos_tabani"][ad] is not None
            and deger < altin["hep_bos_tabani"][ad]
        ]
        if zayif:
            print(f"   ⚠️  «Hep boş» tabanının altındaki alanlar: {', '.join(zayif)}")
    return 0


def _ablasyon_notu() -> str:
    return (
        "\n## Ablasyon tablosu\n\n"
        "Üç yapılandırma **aynı kod yolundan** koşulur; yalnız katman bayrakları değişir.\n"
        "Ayrı kod yolu yazmak ölçümü karşılaştırılamaz hâle getirirdi.\n\n"
        "```bash\n"
        "make extract-kural && make eval   # yalnız kural\n"
        "make extract-llm   && make eval   # yalnız LLM\n"
        "make extract       && make eval   # hibrit\n"
        "```\n\n"
        "| Yapılandırma | Kâr payı | Vade | Makro-F1 | Halüsinasyon |\n"
        "|---|---|---|---|---|\n"
        "| Yalnız kural (regex) | ? | ? | — | %0 |\n"
        "| Yalnız LLM (şema kısıtlı) | ? | ? | ? | ? |\n"
        "| **Hibrit (bizim)** | ? | ? | ? | ? |\n\n"
        "_Tablo altın set hazır olduğunda (16 Ağustos sonrası) doldurulacak._\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Değerlendirme koşum takımı")
    ap.add_argument("--ablasyon", action="store_true", help="ablasyon bölümünü ekle")
    return calistir(ap.parse_args().ablasyon)


if __name__ == "__main__":
    raise SystemExit(main())
