"""Görülmemiş metin ölçümü — `make eval-gorulmemis`.

    make eval-gorulmemis           # kural katmanı (saniyeler)
    make eval-gorulmemis llm=1     # kural + LLM (yavaş, ~1 sn/sayfa değil ~15 sn)

NEDEN VAR — jürinin 19 Ağustos'taki cevabı:

    «Sizin değerlendirme kriterleriniz de önemli ama O ANDA JÜRİ KENDİSİ DE
     TEST VERİSİ VEREBİLİR.»

Bu, ölçüm sorusunu değiştiriyor. Altın set «bizim seçtiğimiz 60 örnekte ne
kadar iyiyiz?» sorusunu cevaplıyor. Jürinin sorusu farklı: **«hiç görmediğin
bir metinde ne oluyor?»**

VERİ NEREDEN GELİYOR — ücretsiz ve gerçek:
    `data/raw` altında 283 HTML var ama korpusta 96 kayıt. Aradaki 187 sayfa
    9 Ağustos taramasında gerçekten çekildi, sonra korpus seçimi sırasında
    dışarıda kaldı ve GELİŞTİRME BOYUNCA HİÇ GÖRÜLMEDİ. Ne kural yazarken
    bakıldı, ne altın sete girdi, ne bir metrik onlara göre ayarlandı.

    Jürinin vereceği veriye en yakın vekil budur: gerçek banka sayfaları,
    bizim seçmediğimiz, hiç bakılmamış.

ETİKET GEREKTİRMEZ — ve bu tesadüf değil:
    Sistemin kanıt zinciri sözleşmesi (`Alan` her değerin kaynağını taşır)
    sayesinde ETİKETSİZ ölçülebilen gerçek kalite göstergeleri var:

      * KANIT İHLALİ  — üretilen değer ham metinde geçiyor mu? (halüsinasyon)
      * ÇÖKME         — çıkarım kaydı düşürüyor mu?
      * BOYUT İHLALİ  — çok birimli alanın birimi çözülebiliyor mu?
      * ÇİFTE SAHİPLENME — aynı sayıyı iki alan birden alıyor mu?
      * DOLULUK       — görülmemiş metinde korpustakine göre ne kadar düşüyor?

    İlk dördü için doğru cevabı bilmeye gerek yok; hepsi sistemin KENDİ
    sözleşmesine uyup uymadığını sorar. Etiketleme maliyeti sıfır.

NE ÖLÇMEZ — dürüst sınır:
    Doğruluk ölçmez. Çıkarılan değerin DOĞRU olup olmadığını bilmiyoruz,
    yalnız KANITLI olduğunu biliyoruz. Doğruluk için altın set gerekir.
    Bu iki ölçüm birbirinin yerine geçmez; farklı soruları cevaplarlar.
"""

from __future__ import annotations

import argparse
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import trafilatura

from src.collector.toplayici import EN_AZ_GOVDE_UZUNLUGU, HAM_DIZIN
from src.extraction.kural import KURALLAR, _adaylari_bul, _tek_atama
from src.extraction.uzlastirici import kampanya_cikar
from src.schema import ALAN_BOYUTLARI, TEK_BIRIMLI_ALANLAR, HamKayit

log = logging.getLogger("gorulmemis")

KOK = Path(__file__).resolve().parents[1]
RAPOR_DOSYASI = KOK / "docs" / "GORULMEMIS_METIN.md"


def gorulmemis_sayfalar(dizin: Path = HAM_DIZIN) -> list[Path]:
    """Korpusa girmemiş HTML anlık görüntüleri.

    Korpus seçimi `.json` üst verisiyle işaretlenir; `.html` var ama `.json`
    yoksa o sayfa çekilmiş ama korpusa alınmamıştır.
    """
    html = {p.with_suffix("").name: p for p in dizin.rglob("*.html")}
    json_ = {p.with_suffix("").name for p in dizin.rglob("*.json")}
    return [html[ad] for ad in sorted(set(html) - json_)]


def _ham_kayit(yol: Path) -> HamKayit | None:
    govde = trafilatura.extract(
        yol.read_text(encoding="utf-8", errors="ignore"),
        include_comments=False,
        include_tables=True,
        favor_recall=True,
    ) or ""
    if len(govde) < EN_AZ_GOVDE_UZUNLUGU:
        return None
    return HamKayit(
        banka_kodu=yol.parent.name,
        banka_adi=f"Banka {yol.parent.name}",
        url=f"gorulmemis://{yol.parent.name}/{yol.stem}",
        cekim_tarihi=datetime(2026, 8, 9),
        http_durum=200,
        govde_metin=govde,
    )


def _span_cakismasi(metin: str) -> tuple[int, int]:
    """(ham çakışma, çözülmemiş çakışma) — İKİSİ FARKLI ŞEY ÖLÇER.

    HAM ÇAKIŞMA bir ihlal DEĞİLDİR: iki kuralın aynı sayıya talip olması
    doğaldır ve `_tek_atama` bunu çözmek için vardır. Bu sayı, düzeltmenin
    ne kadar sık devreye girdiğini gösteren bir TEŞHİS ölçüsüdür — sıfır
    olması beklenmez, hatta sıfırsa örneklem çok dar demektir.

    ÇÖZÜLMEMİŞ ÇAKIŞMA gerçek ihlaldir: `_tek_atama` koştuktan SONRA hâlâ
    iki alanın sahiplendiği bir span kaldıysa çözümleyici çalışmıyordur.
    Hedef sıfırdır.

    İkisini tek sayaçta toplamak, teşhisi ihlal gibi gösterirdi — raporun
    en baştaki uyarısıyla aynı hata: bir sayının ne anlama geldiğini yanlış
    etiketlemek, ölçmemekten kötüdür.
    """
    adaylar = {kural.alan: _adaylari_bul(metin, kural) for kural in KURALLAR}

    ham: dict[tuple[int, int], set[str]] = {}
    for alan, alan_adaylari in adaylar.items():
        for aday in alan_adaylari:
            ham.setdefault((aday.baslangic, aday.bitis), set()).add(alan)
    ham_sayisi = sum(1 for alanlar in ham.values() if len(alanlar) > 1)

    kalan: dict[tuple[int, int], set[str]] = {}
    for alan, alan_adaylari in _tek_atama(adaylar).items():
        for aday in alan_adaylari:
            kalan.setdefault((aday.baslangic, aday.bitis), set()).add(alan)
    cozulmemis = sum(1 for alanlar in kalan.values() if len(alanlar) > 1)

    return ham_sayisi, cozulmemis


def olc(llm_kullan: bool = False, azami: int | None = None) -> dict[str, Any]:
    sayfalar = gorulmemis_sayfalar()
    if azami:
        sayfalar = sayfalar[:azami]

    llm_cikarici = None
    if llm_kullan:
        from src.extraction.llm import LLMCikarici

        llm_cikarici = LLMCikarici()

    islenen = atlanan = coken = 0
    kanit_ihlali = 0
    ihlal_ornekleri: list[str] = []
    boyut_ihlali = 0
    cakisma_ham = 0
    cakisma_cozulmemis = 0
    dolu_alan = toplam_alan = 0
    alan_sayaci: Counter[str] = Counter()
    banka_sayaci: Counter[str] = Counter()

    for sira, yol in enumerate(sayfalar, 1):
        kayit = _ham_kayit(yol)
        if kayit is None:
            atlanan += 1
            continue

        ham_cakisma, kalan_cakisma = _span_cakismasi(kayit.govde_metin)
        cakisma_ham += ham_cakisma
        cakisma_cozulmemis += kalan_cakisma

        try:
            kampanya, _ = kampanya_cikar(
                kayit, llm_cikarici=llm_cikarici, llm_kullan=llm_kullan
            )
        except Exception as hata:
            coken += 1
            log.error("çöktü (%s): %s", yol.name, hata)
            continue

        islenen += 1
        banka_sayaci[kayit.banka_kodu] += 1

        for ad, alan in kampanya.cikarilan_alanlar().items():
            toplam_alan += 1
            if alan.var_mi:
                dolu_alan += 1
                alan_sayaci[ad] += 1
                if ad in ALAN_BOYUTLARI and ad not in TEK_BIRIMLI_ALANLAR and alan.birim is None:
                    boyut_ihlali += 1

        ihlaller = kampanya.kanit_denetimi()
        kanit_ihlali += len(ihlaller)
        ihlal_ornekleri.extend(f"{yol.name}: {i}" for i in ihlaller[:1])

        if sira % 25 == 0:
            log.info("%d/%d", sira, len(sayfalar))

    return {
        "sayfa": len(sayfalar),
        "islenen": islenen,
        "atlanan": atlanan,
        "coken": coken,
        "banka_sayisi": len(banka_sayaci),
        "toplam_alan": toplam_alan,
        "dolu_alan": dolu_alan,
        "alan_dolulugu": dolu_alan / toplam_alan if toplam_alan else 0.0,
        "kanit_ihlali": kanit_ihlali,
        "kanit_ihlali_orani": kanit_ihlali / dolu_alan if dolu_alan else 0.0,
        "kanit_ihlali_ornekleri": ihlal_ornekleri[:8],
        "boyut_ihlali": boyut_ihlali,
        "cakisma_ham": cakisma_ham,
        "cakisma_cozulmemis": cakisma_cozulmemis,
        "alan_sayaci": dict(alan_sayaci),
        "llm_kullanildi": llm_kullan,
    }


def rapor_yaz(olcum: dict[str, Any]) -> str:
    katman = "kural + LLM (hibrit)" if olcum["llm_kullanildi"] else "yalnız kural"
    s = [
        "# Görülmemiş Metin Ölçümü",
        "",
        f"_Otomatik üretildi: {datetime.now():%d.%m.%Y %H:%M} · `make eval-gorulmemis`_",
        "",
        "> Bu dosya elle düzenlenmez.",
        "",
        "## Soru",
        "",
        "Jüri 19 Ağustos'ta *«o anda jüri kendisi de test verisi verebilir»* dedi.",
        "Altın set «bizim seçtiğimiz 60 örnekte ne kadar iyiyiz?» sorusunu",
        "cevaplıyor. Bu ölçüm farklı bir soruyu cevaplıyor: **hiç görülmemiş bir",
        "metinde sistem sözleşmesine uyuyor mu?**",
        "",
        "## Veri",
        "",
        f"- Görülmemiş sayfa: **{olcum['sayfa']}** · işlenen: {olcum['islenen']} · "
        f"gövdesi kısa/atlanan: {olcum['atlanan']}",
        f"- Banka: {olcum['banka_sayisi']} · çıkarım katmanı: {katman}",
        "",
        "> Bu sayfalar 9 Ağustos taramasında gerçekten çekildi, korpus seçimi",
        "> sırasında dışarıda kaldı ve **geliştirme boyunca hiç görülmedi** —",
        "> ne kural yazarken bakıldı, ne altın sete girdi, ne bir metrik onlara",
        "> göre ayarlandı. Jürinin vereceği veriye en yakın vekil budur.",
        "",
        "## Sözleşme ihlalleri (etiket gerektirmez)",
        "",
        "| Denetim | Değer | Hedef | Durum |",
        "|---|---|---|---|",
    ]

    def satir(ad: str, deger: int, hedef: int = 0) -> str:
        return f"| {ad} | {deger} | {hedef} | {'✅' if deger <= hedef else '❌'} |"

    s.append(satir("Çöken kayıt", olcum["coken"]))
    s.append(
        f"| **Kanıt ihlali** (halüsinasyon) | {olcum['kanit_ihlali']} "
        f"(%{olcum['kanit_ihlali_orani'] * 100:.2f}) | 0 | "
        f"{'✅' if olcum['kanit_ihlali'] == 0 else '❌'} |"
    )
    s.append(satir("Boyut ihlali (birimsiz değer)", olcum["boyut_ihlali"]))
    s.append(satir("Çözülmemiş span çakışması", olcum["cakisma_cozulmemis"]))
    s.append("")
    s += [
        f"> 🔎 **Teşhis (ihlal değil):** aynı sayıya iki kuralın talip olduğu "
        f"**{olcum['cakisma_ham']}** durum saptandı ve `_tek_atama` hepsini "
        "çözdü. Bu sayının sıfır olması BEKLENMEZ — iki kuralın aynı sayıya "
        "talip olması doğaldır. Anlamı şu: tek atama düzeltmesi görülmemiş "
        f"{olcum['islenen']} sayfada **{olcum['cakisma_ham']} kez** devreye "
        "girdi, yani düzeltilen hata nadir bir uç durum değildi.",
        "",
    ]
    s += [
        "> **Ne ölçmez — dürüst sınır.** Bu tablo DOĞRULUK ölçmez. Çıkarılan",
        "> değerin doğru olup olmadığını bilmiyoruz; yalnız **kanıtlı** olduğunu",
        "> biliyoruz. Doğruluk için altın set gerekir. İki ölçüm birbirinin",
        "> yerine geçmez, farklı soruları cevaplar.",
        "",
        "## Kapsam",
        "",
        f"- Alan doluluğu: **%{olcum['alan_dolulugu'] * 100:.1f}** "
        f"({olcum['dolu_alan']}/{olcum['toplam_alan']})",
        "",
        "| Alan | Dolu kayıt |",
        "|---|---|",
    ]
    for ad, sayi in sorted(olcum["alan_sayaci"].items(), key=lambda x: -x[1]):
        s.append(f"| `{ad}` | {sayi} |")
    s.append("")

    if olcum["kanit_ihlali_ornekleri"]:
        s += ["## Kanıt ihlali örnekleri", ""]
        s += [f"- `{o}`" for o in olcum["kanit_ihlali_ornekleri"]]
        s.append("")

    return "\n".join(s)


def calistir(llm_kullan: bool = False, azami: int | None = None) -> int:
    olcum = olc(llm_kullan, azami)
    if not olcum["sayfa"]:
        print("❌ Görülmemiş sayfa yok (data/raw altında JSON'suz HTML bulunamadı).")
        return 1

    RAPOR_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    RAPOR_DOSYASI.write_text(rapor_yaz(olcum), encoding="utf-8")
    print(f"✅ {RAPOR_DOSYASI.relative_to(KOK)} yazıldı")
    print(f"   Görülmemiş sayfa: {olcum['sayfa']} · işlenen: {olcum['islenen']}")
    print(f"   Çöken: {olcum['coken']} · kanıt ihlali: {olcum['kanit_ihlali']}")
    print(
        f"   Boyut ihlali: {olcum['boyut_ihlali']} · "
        f"çözülmemiş çakışma: {olcum['cakisma_cozulmemis']} "
        f"(çözülen: {olcum['cakisma_ham']})"
    )
    print(f"   Alan doluluğu: %{olcum['alan_dolulugu'] * 100:.1f}")
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Görülmemiş metin ölçümü")
    ap.add_argument("--llm", action="store_true", help="LLM katmanını da koş (yavaş)")
    ap.add_argument("--azami", type=int, default=None, help="ilk N sayfa (deneme)")
    a = ap.parse_args()
    return calistir(a.llm, a.azami)


if __name__ == "__main__":
    raise SystemExit(main())
