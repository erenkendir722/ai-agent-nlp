"""Banka bazlı kapsam raporu — dengesizliği ölçer ve YAZAR.

    python tools/kapsam_raporu.py     # docs/KAPSAM_RAPORU.md üret

NEDEN VAR:
    Karşılaştırma motoru "en avantajlı ürün" derken elindeki kayıtlara bakar.
    Bir bankadan 217, diğerinden 16 kampanya varsa sonuç sessizce YANLI olur —
    az temsil edilen bankanın iyi teklifi kümede yoktur, motor onu bulamaz.
    Şartname 15.1 sistemin "adil ve yanlılıktan arındırılmış" olmasını istiyor;
    dengesizliği ölçüp yazmak, fark etmemekten dürüsttür.

    Rapor bir SUÇLAMA değil sınırdır: bankaların yayımladığı sayfa sayısı
    gerçekten farklı. Ölçtüğümüz şey bizim kapsamımız, onların kampanya sayısı
    değil.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.depolama import VERITABANI_URL, kampanyalari_oku  # noqa: E402
from src.schema import ALAN_ADLARI  # noqa: E402

KOK = Path(__file__).resolve().parents[1]
RAPOR = KOK / "docs" / "KAPSAM_RAPORU.md"


def calistir(url: str = VERITABANI_URL) -> int:
    kampanyalar = list(kampanyalari_oku(url))
    if not kampanyalar:
        print(" Veritabanı boş.")
        return 1

    banka_sayisi: Counter[str] = Counter()
    banka_dolu: defaultdict[str, int] = defaultdict(int)
    banka_tur: defaultdict[str, Counter] = defaultdict(Counter)
    tur_toplam: Counter[str] = Counter()

    for k in kampanyalar:
        banka_sayisi[k.banka_adi] += 1
        banka_dolu[k.banka_adi] += sum(1 for a in k.cikarilan_alanlar().values() if a.var_mi)
        tur = getattr(k.kampanya_turu.deger, "value", k.kampanya_turu.deger) or "belirtilmemis"
        banka_tur[k.banka_adi][tur] += 1
        tur_toplam[tur] += 1

    toplam = len(kampanyalar)
    en_cok = max(banka_sayisi.values())
    en_az = min(banka_sayisi.values())

    satirlar = [
        "# Banka Bazlı Kapsam Raporu",
        "",
        f"_Otomatik üretildi: {datetime.now():%d.%m.%Y %H:%M} · `make kapsam`_",
        "",
        "Bu dosya elle düzenlenmez. Karşılaştırma sonuçlarını okurken **önce buraya**",
        "bakın: kapsam dengesizliği, motorun tarafsızlığından bağımsız bir yanlılık",
        "kaynağıdır (şartname 15.1).",
        "",
        "## Kapsam",
        "",
        f"- Toplam kampanya: **{toplam}**",
        f"- Banka: **{len(banka_sayisi)}** (BDDK listesindeki **faal** katılım bankalarının tamamı)",
        f"- En geniş kapsam / en dar kapsam oranı: **{en_cok / en_az:.1f}×**",
        "",
        "| Banka | Kampanya | Pay | Dolu alan / kayıt |",
        "|---|---|---|---|",
    ]
    for ad, n in banka_sayisi.most_common():
        satirlar.append(
            f"| {ad} | {n} | %{n / toplam * 100:.1f} | {banka_dolu[ad] / n:.1f} / {len(ALAN_ADLARI)} |"
        )

    satirlar += [
        "",
        "## Kampanya türü dağılımı",
        "",
        "| Tür | Kayıt | Pay |",
        "|---|---|---|",
    ]
    for tur, n in tur_toplam.most_common():
        satirlar.append(f"| `{tur}` | {n} | %{n / toplam * 100:.1f} |")

    # `diger` KUTUSU — «neden bu kadar çok?» sorusunun ölçülmüş cevabı.
    diger_kayitlar = [
        k for k in kampanyalar
        if (getattr(k.kampanya_turu.deger, "value", k.kampanya_turu.deger) or "") == "diger"
    ]
    if diger_kayitlar:
        anahtarlar = {
            "indirim / iade": ("indirim", "iade", "cashback"),
            "taksit / vade farksız": ("taksit", "vade farksız"),
            "sigorta": ("sigorta", "kasko", "poliçe"),
            "döviz / altın / yatırım": ("döviz", "altın", "yatırım", "fon"),
            "ücretsiz işlem / ATM": ("ücretsiz", "atm", "havale", "eft"),
            "promosyon / hediye": ("promosyon", "hediye", "çekiliş"),
        }
        dagilim = []
        for etiket, kelimeler in anahtarlar.items():
            n = sum(
                1 for k in diger_kayitlar
                if any(kelime in (k.ham_metin or "").lower() for kelime in kelimeler)
            )
            dagilim.append((etiket, n))
        satirlar += [
            "",
            "## `diger` neden bu kadar çok?",
            "",
            f"Kayıtların **{len(diger_kayitlar)}'i** (%{len(diger_kayitlar) / toplam * 100:.1f}) "
            "`diger` türünde. Bu bir sınıflandırma başarısızlığı DEĞİL, bilinçli bir karardır:",
            "şartname 5.4'teki sekiz tür finansman ve kart odaklıdır; bankaların yayımladığı",
            "kampanyaların önemli bir bölümü o sekizin dışına düşer. **Zorlama sınıflandırma",
            "yapmaktansa «diğer» demek daha dürüsttür** (ADR 002).",
            "",
            "`diger` kayıtlarında geçen konular (ham metin taraması, bir kayıt birden çok",
            "başlıkta sayılabilir):",
            "",
            "| Konu | `diger` kaydı |",
            "|---|---|",
        ]
        for etiket, n in sorted(dagilim, key=lambda x: -x[1]):
            satirlar.append(f"| {etiket} | {n} |")
        satirlar += [
            "",
            "> Altın sette `kampanya_turu` alanının F1 skoru **0,80** — yani tür çıkarımı",
            "> ölçülen bir başarıyla çalışıyor; `diger` oranı korpusun kendi özelliğidir.",
        ]

    satirlar += [
        "",
        "## Bu dengesizlik neyi etkiler",
        "",
        f"En geniş kapsamlı bankada en dar kapsamlının **{en_cok / en_az:.1f} katı** kayıt var.",
        "Sonuçları okurken üç kural:",
        "",
        "1. **«En avantajlı» ifadesi, TOPLADIĞIMIZ kümede en avantajlı demektir.**",
        "   Az temsil edilen bir bankanın daha iyi teklifi kümede olmayabilir.",
        "2. **Banka karşılaştırması kayıt sayısına değil, kayıt İÇERİĞİNE dayanmalı.**",
        "   Arayüzdeki sıralama tekil ürünleri karşılaştırır, banka ortalaması almaz —",
        "   dengesizlik bu yüzden sıralamayı doğrudan bozmaz.",
        "3. **Tür dağılımı da dengesizdir.** Kart kampanyalarında kâr payı oranı",
        "   bulunmaz; alan doluluğunu bankalar arası kıyaslarken tür karışımına bakın.",
        "",
        "## Neden bazı bankalarda daha az kayıt var",
        "",
        "- Bazı bankalar kampanya sayfalarını **JavaScript ile parça parça** yüklüyor",
        "  («daha fazla göster» düğmesi). Toplayıcı ilk grubu alır; kalanı elle eklenir.",
        "  Ayrıntı ve banka bazlı notlar: `data/banks.yaml`.",
        "- İki banka (Adil Katılım, İktisat Katılım) **BDDK kaydı var ama faaliyete",
        "  geçmemiş** durumda; kampanya sayfaları yok. Listede tutulur, sayılmaz.",
        "",
    ]

    RAPOR.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    print(f" {RAPOR.relative_to(KOK)} yazıldı ({len(banka_sayisi)} banka, {toplam} kayıt)")
    print(f"   Dengesizlik oranı: {en_cok / en_az:.1f}×")
    return 0


if __name__ == "__main__":
    raise SystemExit(calistir())
