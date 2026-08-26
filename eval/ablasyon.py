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
from concurrent.futures import ThreadPoolExecutor
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
    # LLM koşularından ÖNCE ortaya çıkar.
    #
    # İKİ SORU, BEŞ SATIR (A-09, 26 Ağu):
    #   Soru 1 — hangi ÇIKARIM KATMANI ne katıyor?   kural / llm / hibrit
    #   Soru 2 — hangi AJAN ne katıyor?              hibrit_elestirmensiz / tam
    #
    # Eski üç satır AYNEN korundu; yeni iki satır onların üstüne biniyor.
    # `hibrit` tarihsel satırdır (eleştirmen açık, yüklem kapalı); `tam`
    # üretimde koşan yapılandırmadır (`make extract`) — ikisi arasındaki fark
    # yüklem ajanının, `hibrit` ile `hibrit_elestirmensiz` arasındaki fark
    # eleştirmen ajanının katkısıdır.
    ("kural", {"kural_kullan": True, "llm_kullan": False, "elestirmen": True, "yuklem": False}),
    ("llm", {"kural_kullan": False, "llm_kullan": True, "elestirmen": True, "yuklem": False}),
    ("hibrit", {"kural_kullan": True, "llm_kullan": True, "elestirmen": True, "yuklem": False}),
    (
        "hibrit_elestirmensiz",
        {"kural_kullan": True, "llm_kullan": True, "elestirmen": False, "yuklem": False},
    ),
    ("tam", {"kural_kullan": True, "llm_kullan": True, "elestirmen": True, "yuklem": True}),
)

# `kampanya_cikar` yalnız bu ikisini bayrak olarak alır; kalan ikisi ajan kurar.
KATMAN_BAYRAKLARI = ("kural_kullan", "llm_kullan")

ASGARI_BASARI_ORANI = 0.90
"""Bir kolun ölçülebilmesi için gereken en düşük çıkarım başarısı.

Tek tük düşen kayıt normaldir (ortak servis, nadir zaman aşımı) ve ortak korpus
onları zaten eler. Ama kayıtların onda birinden fazlası düştüyse ortada bir
arıza vardır — ağ, anahtar ya da servis. O hâlde ölçüm YAPILMAZ; yarım korpustan
çıkan sayı, sayı olmadığını söylemez."""


def _veritabanini_sil(url: str) -> None:
    """Kolun eski veritabanını siler. Yoksa sessizce geçer."""
    if url.startswith("sqlite:///"):
        yol = Path(url.removeprefix("sqlite:///"))
        yol.unlink(missing_ok=True)


def _varsayilan_isci() -> int:
    """Eş zamanlı çıkarım işçisi — üretim boru hattıyla AYNI kaynak.

    Ablasyon 5 yapılandırma × korpus koşuyor; seri koşumda 1024 kayıt tek kolda
    ~40 dakika sürer ve tablo teslim gününe yetişmez. `src.boru_hatti` zaten
    ölçülmüş bir varsayılan taşıyor (EVREN'de 16, Ollama'da 1) — ikinci bir
    sayı tanımlamak, iki yerin zamanla ayrışmasını garanti ederdi.
    """
    from src.boru_hatti import _varsayilan_isci as boru_hatti_iscisi

    return boru_hatti_iscisi()


def _yapilandirmayi_kos(
    ad: str, bayraklar: dict[str, bool], kayitlar: list[HamKayit], isci: int
) -> list[Any]:
    """Tek yapılandırmayı kendi veritabanına koşar. Üretim verisine dokunmaz.

    ÖNCEKİ KOŞU SİLİNİR — ölçülmüş sessiz bayatlık (26 Ağustos, akşam koşusu):
        Koşu sırasında makinenin ağı düştü. LLM'li üç kolun **1024 kaydının
        tamamı** hata verdi, `kaydet([])` hiçbir şey yazmadı ve fonksiyon
        veritabanını okuyup ÖNCEKİ KOŞUNUN kayıtlarını döndürdü. Sonuç:
        `data/ablasyon.json` eski sayılarla, ama YENİ kod parmak iziyle
        yazıldı — yani tablo, ölçmediği bir kodun ölçümü gibi göründü.

        Bu, projenin en pahalı hata sınıfının (sessiz başarısızlık) ablasyona
        sızmış hâliydi: her kontrol yeşil, tablo tam, sayılar yanlış.

    İki savunma eklendi:
      1. Kolun veritabanı koşudan ÖNCE silinir — eski satır hayatta kalamaz.
      2. Kayıtların %90'ı çıkarılamadıysa koşu PATLAR (aşağıda). Kırpılmış bir
         korpusta ölçüm yapmak, ölçmemekten kötüdür.
    """
    url = ablasyon_veritabani(ad)
    _veritabanini_sil(url)
    semayi_kur(url)

    katman = {k: bayraklar[k] for k in KATMAN_BAYRAKLARI}

    llm_cikarici = None
    if bayraklar["llm_kullan"]:
        from src.ajanlar.elestirmen import ElestirmenAjani
        from src.extraction.llm import LLMCikarici

        llm_cikarici = LLMCikarici(elestirmen=ElestirmenAjani(etkin=bayraklar["elestirmen"]))

    yuklem_ajani = None
    if bayraklar["yuklem"]:
        from src.ajanlar.yuklem import YuklemAjani

        yuklem_ajani = YuklemAjani()

    def _guvenli_cikar(kayit: HamKayit):
        try:
            kampanya, _ = kampanya_cikar(
                kayit, llm_cikarici=llm_cikarici, yuklem=yuklem_ajani, **katman
            )
            return kampanya
        except Exception as hata:  # tek kayıt tüm koşuyu düşürmesin
            log.error("[%s] çıkarım hatası (%s): %s", ad, kayit.url, hata)
            return None

    # `havuz.map` sonuçları GİRDİ sırasında verir; işçi sayısı değişse de
    # veritabanına yazma sırası değişmez. `isci = 1` seri döngüyle aynıdır.
    kampanyalar = []
    with ThreadPoolExecutor(max_workers=isci) as havuz:
        for sira, kampanya in enumerate(havuz.map(_guvenli_cikar, kayitlar), 1):
            if kampanya is not None:
                kampanyalar.append(kampanya)
            if sira % 50 == 0:
                log.info("[%s] %d/%d", ad, sira, len(kayitlar))

    basari_orani = len(kampanyalar) / len(kayitlar) if kayitlar else 0.0
    if basari_orani < ASGARI_BASARI_ORANI:
        raise RuntimeError(
            f"[{ad}] {len(kayitlar)} kayıttan yalnız {len(kampanyalar)}'i çıkarıldı "
            f"(%{basari_orani * 100:.1f}). Kırpılmış korpusta ölçüm yapılmaz — "
            "sağlayıcıya erişimi doğrulayın: make saglayici-dogrula"
        )
    if len(kampanyalar) < len(kayitlar):
        log.warning(
            "[%s] %d kayıt düştü (hata); ortak korpus bunları eleyecek",
            ad, len(kayitlar) - len(kampanyalar),
        )

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


def _altin_korpusa_indir(ham: list[HamKayit]) -> list[HamKayit]:
    """Korpusu altın sette etiketli kayıtlarla sınırlar.

    Makro-F1 zaten YALNIZ altın sette karşılığı olan kayıtlardan hesaplanır;
    kalan kayıtlar tabloya doluluk ve halüsinasyon oranı katar. Zaman darsa
    (5 yapılandırma × 1024 kayıt) bu bayrak koşuyu ~10 katı kısaltır — ama
    o zaman doluluk sütunu «altın set korpusunun doluluğu» demektir, tüm
    korpusun değil. Varsayılan bilerek tam korpustur.
    """
    from eval.calistir import altin_seti_yukle

    kimlikler = {kayit["kampanya_id"] for kayit in altin_seti_yukle()}
    return [h for h in ham if h.kampanya_id() in kimlikler]


def calistir(yalniz_kural: bool = False, altin_korpus: bool = False) -> int:
    ham = list(ham_kayitlari_oku())
    if not ham:
        print("❌ Ham kayıt yok. Önce `make crawl` çalıştırın.")
        return 1

    if altin_korpus:
        ham = _altin_korpusa_indir(ham)
        if not ham:
            print("❌ Altın sette eşleşen ham kayıt yok.")
            return 1

    izi = kod_parmak_izi()
    isci = _varsayilan_isci()
    hedefler = YAPILANDIRMALAR[:1] if yalniz_kural else YAPILANDIRMALAR
    print(
        f"Ablasyon: {len(hedefler)} yapılandırma × {len(ham)} kayıt "
        f"· {isci} işçi · kod izi {izi}"
        + (" · ALTIN KORPUS" if altin_korpus else "")
    )

    # ÖNCE HEPSİNİ KOŞ, SONRA ÖLÇ — ortak korpus garantisi için.
    kollar: dict[str, list[Any]] = {}
    for ad, bayraklar in hedefler:
        print(f"\n--- {ad} ---")
        kollar[ad] = _yapilandirmayi_kos(ad, bayraklar, ham, isci)
        print(f"    çıkarılan kayıt: {len(kollar[ad])}")

    # ORTAK KORPUS — ölçülmüş sorun (26 Ağustos):
    #     EVREN ortak bir servistir; nadiren tek bir istek zaman aşımına uğrar
    #     (1024 kayıtlık koşuda 2 kayıt). Kol başına DÜŞEN kayıt farklı olunca
    #     satırlar farklı korpusu ölçer ve tablo karşılaştırılamaz hâle gelir —
    #     eski davranış tabloyu hiç yazmamaktı, yani 25 dakikalık koşu çöpe
    #     giderdi.
    #
    #     Doğru çözüm hatayı yok saymak değil, KESİŞİMİ ölçmek: her kolda
    #     başarıyla çıkarılmış kayıtların ortak kümesi. Böylece satırlar
    #     tanım gereği aynı korpustan gelir; düşen kayıt sayısı da yazılır,
    #     gizlenmez.
    ortak = set.intersection(*({k.kampanya_id for k in kol} for kol in kollar.values()))
    dusen = {ad: len(kol) - len(ortak) for ad, kol in kollar.items()}
    if any(dusen.values()):
        print(
            f"\n⚠️  Ortak korpus: {len(ortak)} kayıt "
            f"(kol başına düşen: {', '.join(f'{a}={n}' for a, n in dusen.items() if n)})"
        )

    sonuclar: dict[str, Any] = {}
    for ad in kollar:
        kampanyalar = [k for k in kollar[ad] if k.kampanya_id in ortak]
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
            f"    {ad:22} kayıt={temel['kampanya_sayisi']} "
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
    ap.add_argument(
        "--altin-korpus",
        action="store_true",
        help="yalnız altın sette etiketli kayıtlar (hızlı; doluluk sütunu o korpusa ait)",
    )
    args = ap.parse_args()
    return calistir(args.yalniz_kural, args.altin_korpus)


if __name__ == "__main__":
    raise SystemExit(main())
