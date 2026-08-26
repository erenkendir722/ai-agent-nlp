"""Veri seti dışa aktarımı — yayınlanabilir sürüm + veri kartı (G-11).

    python tools/veri_seti_disa_aktar.py          # data/exports/ altına yaz
    python tools/veri_seti_disa_aktar.py --deneme # ne yazılacağını göster

NEDEN TAM SAYFA METNİ KOYULMUYOR:
    Kampanya sayfalarının metni bankalara aittir. Yapısal alanları, kaynak
    URL'sini ve **her değerin dayandığı kısa alıntıyı** yayımlamak veri setini
    doğrulanabilir kılar; sayfanın tamamını kopyalamak telif riskidir ve
    ölçüm için hiçbir şey eklemez. Alıntı sınırı `ALINTI_SINIRI`.

NEDEN İKİ BİÇİM:
    `.csv` insan içindir (Excel'de açılır, jüri hemen bakar), `.jsonl` makine
    içindir — kanıt zinciri (alıntı + güven + yöntem) düz tabloya sığmaz.
    İkisi de AYNI koşudan üretilir, ayrışamazlar.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.depolama import VERITABANI_URL, kampanyalari_oku  # noqa: E402
from src.schema import ALAN_ADLARI, SEMA_SURUMU  # noqa: E402

KOK = Path(__file__).resolve().parents[1]
DIZIN = KOK / "data" / "exports"
CSV_YOL = DIZIN / "svartal_kampanyalar.csv"
JSONL_YOL = DIZIN / "svartal_kampanyalar.jsonl"
KART_YOL = DIZIN / "DATASET_CARD.md"

ALINTI_SINIRI = 300
"""Bir alıntı en fazla kaç karakter taşır. Kanıt için yeter, kopya için yetmez."""


def _duz_satir(kampanya) -> dict[str, object]:
    satir: dict[str, object] = {
        "kampanya_id": kampanya.kampanya_id,
        "banka_adi": kampanya.banka_adi,
        "banka_kodu": kampanya.banka_kodu,
        "kaynak_url": kampanya.kaynak_url,
        "cekim_tarihi": kampanya.cekim_tarihi.isoformat(),
        "sema_surumu": kampanya.sema_surumu,
    }
    for ad in ALAN_ADLARI:
        alan = getattr(kampanya, ad)
        deger = alan.deger
        satir[ad] = getattr(deger, "value", deger)
        satir[f"{ad}__yontem"] = alan.yontem
        satir[f"{ad}__guven"] = round(alan.guven, 3)
    return satir


def _zengin_satir(kampanya) -> dict[str, object]:
    kayit: dict[str, object] = {
        "kampanya_id": kampanya.kampanya_id,
        "banka_adi": kampanya.banka_adi,
        "kaynak_url": kampanya.kaynak_url,
        "cekim_tarihi": kampanya.cekim_tarihi.isoformat(),
        "sema_surumu": kampanya.sema_surumu,
        "alanlar": {},
    }
    for ad in ALAN_ADLARI:
        alan = getattr(kampanya, ad)
        if not alan.var_mi:
            continue
        deger = alan.deger
        kayit["alanlar"][ad] = {  # type: ignore[index]
            "deger": getattr(deger, "value", deger),
            "birim": alan.birim.value if alan.birim else None,
            "ham_ifade": alan.ham_ifade,
            "yontem": alan.yontem,
            "guven": round(alan.guven, 3),
            "alinti": (alan.kaynak.alinti[:ALINTI_SINIRI] if alan.kaynak else None),
        }
    if kampanya.uygunluk is not None:
        kayit["uygunluk"] = kampanya.uygunluk.model_dump(mode="json", exclude={"kaynak"})
    return kayit


def _veri_karti(kampanyalar, bankalar: Counter, turler: Counter, dolu: int, toplam: int) -> str:
    tarih = datetime.now().strftime("%d.%m.%Y")
    banka_satirlari = "\n".join(
        f"| {ad} | {n} |" for ad, n in sorted(bankalar.items(), key=lambda x: -x[1])
    )
    tur_satirlari = "\n".join(
        f"| `{ad}` | {n} |" for ad, n in sorted(turler.items(), key=lambda x: -x[1])
    )
    return f"""# Veri Kartı — SVARTAL Katılım Bankacılığı Kampanya Veri Seti

_Otomatik üretildi: {tarih} · `make veri-seti`_

Türkiye'de faaliyet gösteren **katılım bankalarının** herkese açık kampanya
sayfalarından toplanmış, yapısal alanlara çıkarılmış kampanya kayıtları.
TEKNOFEST 2026 Yapay Zekâ Dil Ajanları Yarışması 2. Senaryo için üretildi.

## Özet

| | |
|---|---|
| Kayıt sayısı | **{len(kampanyalar)}** |
| Banka sayısı | **{len(bankalar)}** |
| Şema sürümü | `{SEMA_SURUMU}` |
| Alan sayısı (kayıt başına) | 16 yapısal alan + uygunluk koşulları |
| Dolu hücre | {dolu} / {toplam} |
| Dil | Türkçe |
| Lisans | Apache-2.0 (kod ve derleme) · kaynak metinler ilgili bankalara aittir |

## Dosyalar

| Dosya | Kim için | İçerik |
|---|---|---|
| `svartal_kampanyalar.csv` | insan | Düz tablo: her alan + hangi katmandan geldiği + güven skoru |
| `svartal_kampanyalar.jsonl` | makine | Kanıt zinciri: değer + birim + ham ifade + **kaynak alıntısı** |

## Banka dağılımı

| Banka | Kayıt |
|---|---|
{banka_satirlari}

## Kampanya türü dağılımı

| Tür | Kayıt |
|---|---|
{tur_satirlari}

## Nasıl toplandı

- Yalnız **herkese açık** kampanya sayfaları; giriş gerektiren hiçbir sayfa yok.
- Her alan adresi için `robots.txt` çekilmeden önce kontrol edildi ve karar
  günlüğe yazıldı: [`docs/kanit/ROBOTS_KONTROL_GUNLUGU.md`](../../docs/kanit/ROBOTS_KONTROL_GUNLUGU.md).
  *(robots.txt: bir sitenin, otomatik programlara hangi sayfaları çekmelerinin
  uygun olduğunu bildirdiği metin dosyası.)*
- Kişisel veri taraması yapıldı, kimliği belirli gerçek kişiye ait veri
  bulunmadı: [`docs/kanit/KVKK_TARAMASI.md`](../../docs/kanit/KVKK_TARAMASI.md).
- Yöntem: [`docs/VERI_METODOLOJISI.md`](../../docs/VERI_METODOLOJISI.md).

## Bilinen sınırlar

- **Anlık görüntüdür.** Kampanyalar süreli; `cekim_tarihi` her kayıtta durur.
- **Alan doluluğu türe göre değişir.** Kart kampanyalarında kâr payı oranı
  yoktur; boş hücre eksik veri değil, o kampanyada olmayan bilgidir.
- **Dengesiz dağılım.** Bankaların sayfa sayısı farklı; karşılaştırma yaparken
  kapsam raporuna bakın: [`docs/KAPSAM_RAPORU.md`](../../docs/KAPSAM_RAPORU.md).
- **Değerler modelden gelebilir.** Her hücre `__yontem` sütununda hangi
  katmandan geldiğini (`kural` / `llm` / `hibrit`) beyan eder; `guven`
  sütunu 0–1 arasıdır. Ölçüm sonuçları: [`docs/SONUCLAR.md`](../../docs/SONUCLAR.md).

## Atıf

> Takım SVARTAL (2026). *SVARTAL Katılım Bankacılığı Kampanya Veri Seti.*
> TEKNOFEST 2026 Yapay Zekâ Dil Ajanları Yarışması.
> https://github.com/erenkendir722/ai-agent-nlp
"""


def calistir(deneme: bool, url: str = VERITABANI_URL) -> int:
    kampanyalar = list(kampanyalari_oku(url))
    if not kampanyalar:
        print(" Veritabanı boş. Önce `make extract` çalıştırın.")
        return 1

    bankalar: Counter[str] = Counter(k.banka_adi for k in kampanyalar)
    turler: Counter[str] = Counter(
        (getattr(k.kampanya_turu.deger, "value", k.kampanya_turu.deger) or "belirtilmemis")
        for k in kampanyalar
    )
    dolu = sum(1 for k in kampanyalar for a in k.cikarilan_alanlar().values() if a.var_mi)
    toplam = len(kampanyalar) * len(ALAN_ADLARI)

    print(f"Kayıt: {len(kampanyalar)} · banka: {len(bankalar)} · dolu hücre: {dolu}/{toplam}")
    if deneme:
        print("(deneme modu — dosya yazılmadı)")
        return 0

    DIZIN.mkdir(parents=True, exist_ok=True)

    satirlar = [_duz_satir(k) for k in kampanyalar]
    with CSV_YOL.open("w", encoding="utf-8-sig", newline="") as dosya:
        yazici = csv.DictWriter(dosya, fieldnames=list(satirlar[0].keys()), delimiter=";")
        yazici.writeheader()
        yazici.writerows(satirlar)

    with JSONL_YOL.open("w", encoding="utf-8") as dosya:
        for kampanya in kampanyalar:
            dosya.write(json.dumps(_zengin_satir(kampanya), ensure_ascii=False) + "\n")

    KART_YOL.write_text(_veri_karti(kampanyalar, bankalar, turler, dolu, toplam), encoding="utf-8")

    for yol in (CSV_YOL, JSONL_YOL, KART_YOL):
        print(f" {yol.relative_to(KOK)} ({yol.stat().st_size / 1024:.0f} KB)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Veri seti dışa aktarımı (G-11)")
    ap.add_argument("--deneme", action="store_true", help="yazmadan göster")
    return calistir(ap.parse_args().deneme)


if __name__ == "__main__":
    raise SystemExit(main())
