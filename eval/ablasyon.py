"""Atomik ablasyon koşucusu — `make ablasyon` (bulgu 2.2).

    make ablasyon              # üç yapılandırma + üç ölçüm + tablo, TEK komut
    make ablasyon hizli=1      # yalnız kural katmanı (LLM'siz duman testi)

NEDEN VAR — ölçülmüş hata (18 Ağustos):
    `data/ablasyon.json` üç satır taşıyordu ve satırlar FARKLI KOD SÜRÜMLERİYLE
    koşulmuştu:

        llm     17 Ağu  f797dd3f69630cfc
        kural   17 Ağu  f797dd3f69630cfc
        hibrit  18 Ağu  f835ccc2f7e8d116   <- farklı

    Yani «hibrit 0,778 vs kural 0,628 vs LLM 0,176» karşılaştırması geçersizdi:
    hibrit satırı daha yeni ve iyileştirilmiş kodla koşulmuştu. Sunumun en
    güçlü grafiği, ölçtüğü şeyi ölçmüyordu.

    Eksik olan TESPİT değildi — `eval.calistir._ablasyon_notu` bu durumu zaten
    yakalıyor ve «🔴 Satırlar KARŞILAŞTIRILAMAZ» basıyordu. Eksik olan KOŞUMDU:
    üç yapılandırma üç ayrı elle komutla, farklı zamanlarda çalıştırılıyordu.
    İnsan hatasını uyarıyla değil, YAPIYLA engellemek gerekir.

İKİ YAPISAL GARANTİ:

    1. TEK SÜREÇ, TEK PARMAK İZİ — üç koşu arasında kod değişemez, çünkü
       aralarında insan yok. Satırların ayrışması imkânsız hâle gelir.

    2. ATOMİK YAZIM — tablo ancak ÜÇÜ DE bittikten sonra tek seferde yazılır.
       Koşu yarıda kalırsa `data/ablasyon.json` DEĞİŞMEZ; yarım tablo diye bir
       durum kalmaz. (15 Ağustos'ta yarım kalan bir çıkarım koşusu iyi
       kayıtların üstüne yazmıştı; aynı hata sınıfı.)

`eval.calistir._ablasyon_notu` içindeki parmak izi ve korpus uyarıları
KALDIRILMADI — savunma katmanı olarak duruyor. Artık tetiklenmemeleri gerekir;
tetiklenirlerse gerçek bir arıza var demektir.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from eval.calistir import ABLASYON_DOSYASI, altin_set_metrikleri, temel_metrikler
from src.boru_hatti import ablasyon_veritabani
from src.collector.toplayici import ham_kayitlari_oku
from src.depolama import kampanyalari_oku, kaydet, kod_parmak_izi, semayi_kur
from src.extraction.uzlastirici import kampanya_cikar
from src.schema import HamKayit

log = logging.getLogger("ablasyon")

KOK = Path(__file__).resolve().parents[1]

YAPILANDIRMALAR: tuple[tuple[str, dict[str, bool]], ...] = (
    # Kural önce: LLM gerektirmediği için saniyeler sürer ve bir sorun varsa
    # iki saatlik LLM koşularından ÖNCE ortaya çıkar.
    ("kural", {"kural_kullan": True, "llm_kullan": False}),
    ("llm", {"kural_kullan": False, "llm_kullan": True}),
    ("hibrit", {"kural_kullan": True, "llm_kullan": True}),
)


def _yapilandirmayi_kos(
    ad: str, bayraklar: dict[str, bool], kayitlar: list[HamKayit]
) -> list[Any]:
    """Tek yapılandırmayı kendi veritabanına koşar. Üretim verisine dokunmaz."""
    url = ablasyon_veritabani(ad)
    semayi_kur(url)

    llm_cikarici = None
    if bayraklar["llm_kullan"]:
        from src.extraction.llm import LLMCikarici

        llm_cikarici = LLMCikarici()

    kampanyalar = []
    for sira, kayit in enumerate(kayitlar, 1):
        try:
            kampanya, _ = kampanya_cikar(kayit, llm_cikarici=llm_cikarici, **bayraklar)
        except Exception as hata:  # tek kayıt tüm koşuyu düşürmesin
            log.error("[%s] çıkarım hatası (%s): %s", ad, kayit.url, hata)
            continue
        kampanyalar.append(kampanya)
        if sira % 10 == 0:
            log.info("[%s] %d/%d", ad, sira, len(kayitlar))

    kaydet(kampanyalar, url)
    return list(kampanyalari_oku(url))


def _atomik_yaz(kayitlar: dict[str, Any]) -> None:
    """Geçici dosyaya yaz, sonra yerine koy. Yarım tablo bırakmaz."""
    ABLASYON_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=ABLASYON_DOSYASI.parent, delete=False, suffix=".tmp"
    ) as gecici:
        json.dump(kayitlar, gecici, indent=2, ensure_ascii=False)
        gecici_yol = gecici.name
    os.replace(gecici_yol, ABLASYON_DOSYASI)  # POSIX'te atomik


def calistir(yalniz_kural: bool = False) -> int:
    ham = list(ham_kayitlari_oku())
    if not ham:
        print("❌ Ham kayıt yok. Önce `make crawl` çalıştırın.")
        return 1

    izi = kod_parmak_izi()
    hedefler = YAPILANDIRMALAR[:1] if yalniz_kural else YAPILANDIRMALAR
    print(f"Ablasyon: {len(hedefler)} yapılandırma × {len(ham)} kayıt · kod izi {izi}")

    sonuclar: dict[str, Any] = {}
    for ad, bayraklar in hedefler:
        print(f"\n--- {ad} ---")
        kampanyalar = _yapilandirmayi_kos(ad, bayraklar, ham)
        temel = temel_metrikler(kampanyalar)
        altin = altin_set_metrikleri(kampanyalar)
        sonuclar[ad] = {
            "zaman": datetime.now().isoformat(),
            "kod_parmak_izi": izi,
            "kampanya_sayisi": temel["kampanya_sayisi"],
            "alan_dolulugu": temel["alan_dolulugu"],
            "halusinasyon_orani": temel["halusinasyon_orani"],
            "makro_f1": altin["makro_f1"] if altin else None,
            "sayisal_dogruluk": altin["sayisal_dogruluk"] if altin else None,
            "alan_f1": {a: d["f1"] for a, d in altin["alan_f1"].items()} if altin else {},
        }
        print(
            f"    kayıt={temel['kampanya_sayisi']} "
            f"doluluk=%{temel['alan_dolulugu'] * 100:.1f} "
            f"makro-F1={sonuclar[ad]['makro_f1']}"
        )

    # KARŞILAŞTIRILABİLİRLİK DENETİMİ — tek süreçte koştukları için tutmalı.
    # Tutmuyorsa varsayımlarımızdan biri yanlış demektir; sessizce yazmaktansa
    # patlamak doğrudur.
    izler = {s["kod_parmak_izi"] for s in sonuclar.values()}
    boyutlar = {s["kampanya_sayisi"] for s in sonuclar.values()}
    if len(izler) > 1 or len(boyutlar) > 1:
        print(f"🔴 Satırlar karşılaştırılamaz (iz={izler}, boyut={boyutlar}). Yazılmadı.")
        return 1

    # EKSİK KOŞU YAZMAZ. `--yalniz-kural` bir duman testidir; sonucu yazmak
    # tabloyu tek satıra indirip diğer ikisini SİLERDİ — önlemeye çalıştığımız
    # «yarım tablo» durumunun ta kendisi. Kural, kendi hızlı moduna da uygulanır.
    if len(sonuclar) < len(YAPILANDIRMALAR):
        eksik = [ad for ad, _ in YAPILANDIRMALAR if ad not in sonuclar]
        print(
            f"\n⏭️  Duman testi — tablo YAZILMADI (eksik: {', '.join(eksik)}). "
            "Eksik koşu yazmak, önlemeye çalıştığımız yarım tablonun kendisidir."
        )
        return 0

    _atomik_yaz(sonuclar)
    print(f"\n✅ {ABLASYON_DOSYASI.relative_to(KOK)} yazıldı ({len(sonuclar)} satır, tek kod izi).")
    print("   Tabloyu üretmek için: make eval-ablation")
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Atomik ablasyon koşucusu")
    ap.add_argument("--yalniz-kural", action="store_true", help="LLM'siz duman testi")
    return calistir(ap.parse_args().yalniz_kural)


if __name__ == "__main__":
    raise SystemExit(main())
