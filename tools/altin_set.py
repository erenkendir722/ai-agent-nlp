"""Altın set araçları — örneklem çıkar, etiketleri derle, seti denetle (H-01).

Altın set İNSAN işidir. Bu araç etiket üretmez; yalnız etiketlemenin etrafındaki
mekanik işi yapar:

    python tools/altin_set.py ornekle    # katmanlı örneklem -> kişi başı CSV + okuma kâğıdı
    python tools/altin_set.py denetle    # KENDİ dosyanı pushlamadan önce kontrol
    python tools/altin_set.py uyum       # etiketleyiciler arası uyum oranı
    python tools/altin_set.py derle      # doldurulmuş CSV'ler -> altin_set.jsonl

NEDEN ETİKETİ ARAÇ ÜRETMİYOR:
    Altın set, sistemi ölçmek için vardır. Sistemin kendi çıktısıyla doldurulursa
    `make eval` sistemi kendisiyle karşılaştırır ve doğruluk yapay olarak
    yükselir. Bu yüzden CSV'de model tahmini GÖSTERİLMEZ — etiketleyen kişi
    metni okur ve kendi kararını yazar (körleme).

NEDEN KİŞİ BAŞI AYRI DOSYA:
    Dört kişi aynı CSV'yi düzenlerse her push çakışır. Ayrı dosyada kimse
    kimsenin satırını ezmez, `derle` hepsini birleştirir.

NEDEN `ham_metin` CSV'ye GÖMÜLÜ:
    Etiket, sistemin GÖRDÜĞÜ metne karşı verilmeli. Canlı sayfaya bakıp
    etiketlemek, çıkarım hatasıyla sayfanın sonradan değişmesini birbirine
    karıştırır — o zaman ölçtüğümüz şey çıkarım doğruluğu olmaz.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.depolama import kampanyalari_oku  # noqa: E402
from src.preprocessing.normalizasyon import (  # noqa: E402
    arama_anahtari,
    sayi_ayristir,
    tarih_ayristir,
)
from src.schema import (  # noqa: E402
    ALAN_ADLARI,
    AYLIK_KAR_PAYI_UST_SINIRI,
    SAYISAL_ALANLAR,
    HedefKitle,
    Kampanya,
    KampanyaTuru,
)

KOK = Path(__file__).resolve().parents[1]
GOLD = KOK / "data" / "gold"
METINLER = GOLD / "metinler"
ALTIN_SET = GOLD / "altin_set.jsonl"
ORNEK_KAYDI = GOLD / "ornek_listesi.json"

KISILER = ("Eren", "Samet", "Görkem", "Esra")
TOHUM = 20260812
"""Sabit tohum — örneklem yeniden üretilebilir olmalı. Jüri 'bu 60 örneği nasıl
seçtiniz?' diye sorduğunda cevap 'rastgele' değil, 'şu tohumla katmanlı' olmalı."""

CSV_UST_BILGI = ("kampanya_id", "banka_adi", "kaynak_url")
CSV_SON_BILGI = ("metin",)
"""`metin` bilerek EN SONA konur.

İlk sürümde 4. sütundaydı ve etiket sütunlarını sağa itiyordu: 2.500 karakterlik
bir hücrenin ötesine kaydırınca hangi sütunda olduğunu takip etmek imkânsız
hâle geliyor ve değerler komşu sütunlara düşüyor. 12 Ağustos'ta tam olarak bu
oldu — bir etiketleme turunun 15 alanı yanlış sütuna yazıldı. Etiket sütunları
artık kimlik sütunlarının hemen yanında, dar ve yan yana."""
BOOL_ALANLAR = ("masrafsiz_mi",)
TARIH_ALANLAR = ("kampanya_bitis",)
METIN_KIRPMA = 15_000
"""Excel hücre sınırı 32.767 karakter. 96 kaydın yalnız 2'si bu eşiğin üstünde;
tam metin her hâlükârda `data/gold/metinler/` altına da yazılır."""

def _kisa_yol(yol: Path) -> str:
    """Depo köküne göre yol; kök dışındaysa (testlerde geçici dizin) tam yol."""
    try:
        return str(yol.relative_to(KOK))
    except ValueError:
        return str(yol)


EMIN_DEGIL = "?"
"""Hücreye '?' yazan kişi o alanı atlamış olur — alan JSONL'e hiç girmez ve
metriğe katılmaz. Tahmin edilmiş etiket, eksik etiketten daha zararlıdır."""

UYUM_ONEK = "etiketleme_uyum_"

EK_ONEK = "etiketleme_ek_"
"""Genişletme turunun çalışma sayfaları — ilk turdan AYRI dosyalar.

Aynı dosyalara yazmak, 15 Ağustos'ta doldurulmuş 60 kaydı ezme riski taşır.
Ayrı dosya, `derle`nin ikisini birden okumasıyla birleşir; etiketleyen ise
yalnız yeni satırları görür, eskileri tekrar gözden geçirmek zorunda kalmaz."""

EK_UYUM_ONEK = EK_ONEK + "uyum_"
"""Genişletme turunun ortak bloğu — `derle` bunu da okumak ZORUNDA.

25 Ağustos'ta ölçüldü: bu ön ek `derle` yolunda yoktu ve genişletme turunun
5 ortak kaydı altın sete hiç girmiyordu (93 kayıt derlendi, 98 değil). Kaybolan
kayıtlar setin en güvenilirleriydi — dördü birden etiketleyip çoğunlukla
uzlaştığı kayıtlar. Kişisel paylar zaten okunuyordu, açık yalnız ortak bloktaydı.

Ölçüm ön eki (`uyum_hesapla`) bilerek AYRI bırakıldı: «etiketleme uzlaşmamız
%X» cümlesi tek bir turun oranıdır, iki turu harmanlamak o sayıyı bozar."""

UYUM_ADET = 5
"""Örneklemin ilk 5'ini DÖRDÜ BİRDEN etiketler (H-02).

İki işi birden görür: etiketleyiciler arası uyum oranını ölçer (sunumda
«etiketleme uzlaşmamız %X» cümlesi buradan çıkar) ve bu 5 örnek çoğunluk
oyuyla uzlaştırılıp altın sete girer. Kalan örnekler tek etiketleyicilidir —
dört kişinin her örneği ayrı ayrı etiketlemesi 4 kat maliyet demekti.

Neden 10 değil 5: ortak blok dört kişinin de aynı satırları etiketlemesi
demek, yani tek satır dört kat emek. 5 satır × 8 alan, kişi başı ~8 dakikaya
mal olup uyum oranını hesaplamaya yetecek kadar hücre üretir."""

CEKIRDEK_ALANLAR: tuple[str, ...] = (
    "kampanya_turu",
    "kar_payi_orani",
    "vade_ay_max",
    "finansman_tutari_max",
    "tahsis_ucreti",
    "masrafsiz_mi",
    "odul_miktari",
    "kampanya_bitis",
)
"""CSV'de etiketlenen sekiz alan — şemanın 16 alanının tamamı DEĞİL.

Kalan sekiz alan bilinçli olarak dışarıda:

  * `urun_turu` (%0 doluluk), `alisveris_puani` ve `masraf_bilgisi` (%1),
    `hedef_kitle` (%4) ölçümde neredeyse hiç örnek üretmiyor.
  * Serbest metin alanları (`kampanya_avantaji`, `kampanya_kosullari`, …)
    yalnız LLM katmanından geliyor ve `eval` bunları BİREBİR string
    karşılaştırmasıyla ölçüyor. Elle yazılmış bir cümlenin modelin cümlesiyle
    harfi harfine tutması pratikte imkânsız — yani en yorucu alanlar, aynı
    zamanda skoru garanti sıfır olan alanlar.

Sekiz alanı çok örnekte etiketlemek, on altı alanı az örnekte etiketlemekten
hem ucuz hem istatistiksel olarak daha sağlamdır. Gerekçenin tamamı:
docs/kararlar/008-altin-set-kapsami.md"""


# ---------------------------------------------------------------------------
# Örnekleme
# ---------------------------------------------------------------------------


def _tur(kampanya: Kampanya) -> str:
    deger = kampanya.kampanya_turu.deger
    return getattr(deger, "value", deger) or "siniflandirilmamis"


def katmanli_ornekle(kampanyalar: list[Kampanya], adet: int, tohum: int = TOHUM) -> list[Kampanya]:
    """Türe ve bankaya göre dengeli örneklem.

    Nadir türler önce gelir: 3 taşıt finansmanı kampanyası varsa üçü de sete
    girsin, 37 'diğer' arasından ise bir avuç yeter. Tür içinde, o ana kadar en
    az örnek vermiş bankadan seçilir; böylece 8 bankanın yükü eşitlenir.

    Türler MODEL TAHMİNİDİR (bugün %38'i 'diger'). Bu bir kusur değil, bilinçli
    tercih: doğru katmanlama için zaten altın sete ihtiyaç var. Elimizdeki tek
    sinyalle dengeliyoruz ve bunu kılavuzda açıkça yazıyoruz.
    """
    rastgele = random.Random(tohum)

    havuz: dict[str, list[Kampanya]] = defaultdict(list)
    for kampanya in kampanyalar:
        havuz[_tur(kampanya)].append(kampanya)
    for liste in havuz.values():
        rastgele.shuffle(liste)

    turler = sorted(havuz, key=lambda t: (len(havuz[t]), t))
    banka_sayaci: Counter[str] = Counter()
    secilen: list[Kampanya] = []

    while len(secilen) < adet and any(havuz.values()):
        tur_bulundu = False
        for tur in turler:
            if len(secilen) >= adet or not havuz[tur]:
                continue
            tur_bulundu = True
            aday = min(havuz[tur], key=lambda k: banka_sayaci[k.banka_kodu])
            havuz[tur].remove(aday)
            banka_sayaci[aday.banka_kodu] += 1
            secilen.append(aday)
        if not tur_bulundu:
            break

    return secilen


# ---------------------------------------------------------------------------
# Hedefli örnekleme — zayıf alanları derinleştirir (24 Ağustos)
# ---------------------------------------------------------------------------
#
# NEDEN GEREKLİ:
#     `katmanli_ornekle` TÜRE ve BANKAYA göre dengeler. Bu, sınıflandırma
#     alanı için doğru; ama sayısal alanların doluluğu türle ilgisiz. 60
#     kayıtlık ilk sette sonuç şu oldu:
#
#         kampanya_turu 60 · vade_ay_max 20 · kampanya_bitis 14
#         kar_payi_orani 10 · masrafsiz_mi 7 · tahsis_ucreti 5
#         finansman_tutari_max 5 · odul_miktari 3
#
#     Makro-F1 bu sekiz alanın DÜZ ortalaması. `odul_miktari` N=3 demek, tek
#     bir kaydın düzelmesinin F1'i 33 puan oynatması demek — yani makro-F1'in
#     sekizde biri neredeyse tamamen gürültü. Rastgele kayıt eklemek bunu
#     düzeltmez: nadir alan nadir kalır.
#
# SEÇİM SİSTEMİN ÇIKTISINA BAKMAZ — bu kural pazarlık konusu değil:
#     Kayıtları "sistemin `tahsis_ucreti` bulduğu kayıtlar" diye seçseydik,
#     altın set sistemin zaten başardığı örneklerle dolar ve ölçüm kendi
#     kendini onaylardı. Seçim yalnız HAM METİNDE bir yüzey işareti arar
#     ("tahsis ücreti" ifadesi geçiyor mu?). İşaretin geçmesi alanın DOLU
#     olduğunu garanti etmez — o kararı etiketleyen insan verir.
#
# ÖLÇÜMÜN ANLAMI DEĞİŞİR, BU YAZILMALIDIR:
#     Hedefli örneklemle F1, "rastgele bir kampanyada" değil, "o alanın
#     konuşulduğu kampanyalarda" ölçülür. F1 zaten doğru negatifi saymadığı
#     için bu daha bilgilendirici; ama farklı bir soruya cevap verdiği
#     `docs/SONUCLAR.md`'de açıkça söylenir.

ZAYIF_ALAN_ISARETLERI: dict[str, str] = {
    "kar_payi_orani": r"k[âa]r pay[ıi]\s*oran|%\s*\d+[,.]\d+.{0,30}k[âa]r pay",
    "finansman_tutari_max": r"'?ye kadar finansman|varan finansman|finansman tutar[ıi]",
    "vade_ay_max": r"\d+\s*ay(a|ı)? (kadar|varan|vade)",
    "tahsis_ucreti": r"tahsis [üu]creti|dosya masraf",
    "odul_miktari": r"hediye|[öo]d[üu]l|kazan[ıi]n?\b.{0,20}TL",
    "masrafsiz_mi": r"masrafs[ıi]z|[üu]cret al[ıi]nma|masraf al[ıi]nma",
    "kampanya_bitis": (
        r"\d{1,2}[./ ](Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos"
        r"|Eylül|Ekim|Kasım|Aralık)[./ ]\d{4}"
    ),
}
"""Alanın metinde KONUŞULDUĞUNA dair yüzey işaretleri.

Kasten gevşek: amaç alanı çıkarmak değil, etiketlemeye DEĞER adayı bulmak.
Yanlış pozitif ucuzdur (etiketleyen "boş" der, kayıt yine de sete girer);
yanlış negatif pahalıdır (aday hiç görülmez)."""


def hedefli_ornekle(
    kampanyalar: list[Kampanya],
    gerekli: dict[str, int],
    *,
    tohum: int = TOHUM,
) -> list[Kampanya]:
    """Zayıf alanları kapatacak en küçük kayıt kümesini seçer.

    Açgözlü küme kaplama: her adımda hâlâ AÇIK olan en çok alanı taşıyan
    kayıt alınır. Eşitlikte o ana kadar en az örnek vermiş banka kazanır —
    aksi hâlde tek bir bankanın sayfa düzeni seti ele geçirir (ilk denemede
    34 kaydın 21'i tek bankadan gelmişti).

    `gerekli`: alan -> daha kaç dolu örnek isteniyor.
    """
    desenler = {
        alan: re.compile(desen, re.IGNORECASE)
        for alan, desen in ZAYIF_ALAN_ISARETLERI.items()
        if gerekli.get(alan, 0) > 0
    }
    rastgele = random.Random(tohum)
    havuz = list(kampanyalar)
    rastgele.shuffle(havuz)  # eşit adaylar arasında koşudan koşuya kararlı sıra

    kapsam = {
        k.kampanya_id: {a for a, d in desenler.items() if d.search(k.ham_metin or "")}
        for k in havuz
    }
    kalan = dict(gerekli)
    banka_sayaci: Counter[str] = Counter()
    secilen: list[Kampanya] = []

    while any(v > 0 for v in kalan.values()):
        en_iyi = None
        en_iyi_puan = (0, 0)
        for k in havuz:
            if k in secilen:
                continue
            fayda = sum(1 for a in kapsam[k.kampanya_id] if kalan.get(a, 0) > 0)
            if fayda == 0:
                continue
            # Çok alan kapatan kazanır; eşitlikte az temsil edilen banka.
            puan = (fayda, -banka_sayaci[k.banka_kodu])
            if puan > en_iyi_puan:
                en_iyi, en_iyi_puan = k, puan
        if en_iyi is None:
            break  # korpusta bu alanları taşıyan başka kayıt yok
        secilen.append(en_iyi)
        banka_sayaci[en_iyi.banka_kodu] += 1
        for a in kapsam[en_iyi.kampanya_id]:
            if kalan.get(a, 0) > 0:
                kalan[a] -= 1

    return secilen


def alan_doluluk_raporu(altin: list[dict[str, object]]) -> dict[str, int]:
    """Altın sette her alanın kaç kez DOLU olduğu (F1'deki N)."""
    return {alan: sum(1 for r in altin if r.get(alan) is not None) for alan in CEKIRDEK_ALANLAR}


def _kirp(metin: str) -> str:
    if len(metin) <= METIN_KIRPMA:
        return metin
    return (
        metin[:METIN_KIRPMA]
        + f"\n\n[... {len(metin) - METIN_KIRPMA} karakter kırpıldı —"
        " tam metin: data/gold/metinler/<kampanya_id>.txt ...]"
    )


def csv_basliklari() -> list[str]:
    return [*CSV_UST_BILGI, *CEKIRDEK_ALANLAR, *CSV_SON_BILGI]


def _csv_yaz(yol: Path, kampanyalar: list[Kampanya]) -> None:
    # utf-8-sig: Excel, BOM'suz UTF-8'i Türkçe karakterlerde bozuk gösteriyor
    with yol.open("w", encoding="utf-8-sig", newline="") as dosya:
        yazici = csv.writer(dosya)
        yazici.writerow(csv_basliklari())
        for kampanya in kampanyalar:
            yazici.writerow(
                [
                    kampanya.kampanya_id,
                    kampanya.banka_adi,
                    kampanya.kaynak_url,
                    *([""] * len(CEKIRDEK_ALANLAR)),
                    _kirp(kampanya.ham_metin),
                ]
            )


def _etiketli_mi(yol: Path) -> bool:
    return yol.exists() and any(dokunuldu for _, _, _, dokunuldu in _csv_oku(yol))


def calisma_sayfalari_yaz(
    secilen: list[Kampanya], kisiler: tuple[str, ...], zorla: bool = False
) -> tuple[list[Kampanya], dict[str, int], list[str]]:
    """Örneklemi uyum bloğu + kişisel paylara ayırır ve CSV'leri yazar.

    Etiket içeren sayfalar KORUNUR (`zorla` verilmedikçe) — biri çalışırken
    başkasının yeniden örnekleme yapması, saatlerce emeği silmemeli. Örneklem
    sabit tohumlu olduğu için korunan sayfa yeni örneklemle tutarlı kalır.

    (uyum_blogu, kisi -> kişisel örnek sayısı, korunan dosyalar) döner.
    """
    GOLD.mkdir(parents=True, exist_ok=True)
    METINLER.mkdir(parents=True, exist_ok=True)

    uyum_blogu = secilen[:UYUM_ADET]
    kisisel = secilen[UYUM_ADET:]

    paylar: dict[str, list[Kampanya]] = {kisi: [] for kisi in kisiler}
    for sira, kampanya in enumerate(kisisel):
        paylar[kisiler[sira % len(kisiler)]].append(kampanya)

    sayilar: dict[str, int] = {}
    korunan: list[str] = []
    for kisi, pay in paylar.items():
        for yol, icerik in (
            (GOLD / f"etiketleme_{kisi.lower()}.csv", pay),
            (GOLD / f"etiketleme_uyum_{kisi.lower()}.csv", uyum_blogu),
        ):
            if not zorla and _etiketli_mi(yol):
                korunan.append(yol.name)
                continue
            _csv_yaz(yol, icerik)
        sayilar[kisi] = len(pay)

    for kampanya in secilen:
        (METINLER / f"{kampanya.kampanya_id}.txt").write_text(
            kampanya.ham_metin, encoding="utf-8"
        )

    ORNEK_KAYDI.write_text(
        json.dumps(
            {
                "olusturma": datetime.now().isoformat(timespec="seconds"),
                "tohum": TOHUM,
                "adet": len(secilen),
                "uyum_blogu": [k.kampanya_id for k in uyum_blogu],
                "dagilim_tur": dict(Counter(_tur(k) for k in secilen)),
                "dagilim_banka": dict(Counter(k.banka_adi for k in secilen)),
                "atama": {kisi: [k.kampanya_id for k in pay] for kisi, pay in paylar.items()},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return uyum_blogu, sayilar, korunan


# ---------------------------------------------------------------------------
# Derleme — CSV -> JSONL
# ---------------------------------------------------------------------------


def _hucre_cozumle(alan: str, ham: str) -> tuple[bool, Any]:
    """(alan_yazilsin_mi, deger) döndürür.

    Üç durum ayrılır:
      ''  -> alan metinde YOK          -> JSONL'de null (metriğe girer)
      '?' -> etiketleyen emin değil    -> alan hiç yazılmaz (metriğe girmez)
      ... -> etiket                    -> türüne göre ayrıştırılır
    """
    deger = ham.strip()
    if deger == EMIN_DEGIL:
        return False, None
    if not deger:
        return True, None

    if alan in BOOL_ALANLAR:
        return True, deger.lower() in {"evet", "true", "1", "var", "e"}

    if alan in TARIH_ALANLAR:
        try:
            return True, date.fromisoformat(deger).isoformat()
        except ValueError:
            cozulen = tarih_ayristir(deger)
            return True, cozulen.isoformat() if cozulen else deger

    if alan in SAYISAL_ALANLAR:
        sayi = sayi_ayristir(deger)
        return True, sayi if sayi is not None else deger

    return True, deger


DOKUNMA_ALANI = "kampanya_turu"
"""Satırın etiketlenip etiketlenmediğini bu sütun belirler.

Boş hücre 'bu alan metinde yok' demek olduğu için, hiç açılmamış bir CSV ile
'her alanı tek tek boş bıraktım' diyen bir CSV ayırt edilemez — ilki sessizce
baştan sona null dolu bir cevap anahtarı üretirdi. Kılavuz `kampanya_turu` için
her zaman bir değer istiyor (hiçbiri uymuyorsa `diger`), dolayısıyla bu sütun
'bu satıra bakıldı' işareti olarak güvenilirdir."""


def _etiket_sutunlari(okuyucu: csv.DictReader) -> list[str]:
    """CSV'de GERÇEKTEN bulunan etiket sütunları.

    `ALAN_ADLARI` üzerinde körlemesine dönmek olmaz: eksik bir sütun
    `satir.get(alan) or ""` ile boş stringe düşer ve `_hucre_cozumle` bunu
    'metinde YOK' (null) diye yazar. Yani CSV'de hiç sorulmamış bir alan,
    cevap anahtarına «bu bilgi sayfada yoktu» iddiası olarak girerdi —
    sistem doğru değeri bulduğunda haksız yere hata sayılırdı.

    Sorulmayan alan metriğin dışında kalmalı; bu fonksiyon o sınırı çizer.
    """
    basliklar = set(okuyucu.fieldnames or ())
    return [alan for alan in ALAN_ADLARI if alan in basliklar]


def _csv_oku(yol: Path) -> list[tuple[int, str, dict[str, Any], bool]]:
    """(satir_no, kampanya_id, {alan: deger}, dokunuldu_mu)."""
    cikti: list[tuple[int, str, dict[str, Any], bool]] = []
    with yol.open(encoding="utf-8-sig", newline="") as dosya:
        okuyucu = csv.DictReader(dosya)
        sutunlar = _etiket_sutunlari(okuyucu)
        for satir_no, satir in enumerate(okuyucu, start=2):
            kimlik = (satir.get("kampanya_id") or "").strip()
            dokunuldu = bool((satir.get(DOKUNMA_ALANI) or "").strip())
            etiketler: dict[str, Any] = {}
            for alan in sutunlar:
                yazilsin, deger = _hucre_cozumle(alan, satir.get(alan) or "")
                if yazilsin:
                    etiketler[alan] = deger
            cikti.append((satir_no, kimlik, etiketler, dokunuldu))
    return cikti


def _anahtar(deger: Any) -> str:
    """Oylama için hashlenebilir anahtar (None, bool, float, str hepsi olabilir)."""
    return json.dumps(deger, ensure_ascii=False, sort_keys=True)


def uyum_dosyalari(
    kisiler: tuple[str, ...], onek: str = UYUM_ONEK
) -> dict[str, list[tuple[int, str, dict[str, Any], bool]]]:
    return {
        kisi: [s for s in _csv_oku(yol) if s[3]]
        for kisi in kisiler
        if (yol := GOLD / f"{onek}{kisi.lower()}.csv").exists()
    }


def uyum_hesapla(kisiler: tuple[str, ...] = KISILER, onek: str = UYUM_ONEK) -> dict[str, Any]:
    """Etiketleyiciler arası uyum — ikili eşleşme oranı (H-02'nin çıktısı).

    İKİ ORAN HESAPLANIR, çünkü tek oran yanıltıcıdır:

      `ham_uyum`  — bütün alan çiftleri. Alanların ~%74'ü zaten boş olduğu için
                    bu oran «ikimiz de burada bir şey yok dedik» mutabakatıyla
                    şişer; %95'ler görürsünüz ve hiçbir şey öğrenmezsiniz.
      `uyum`      — en az bir kişinin DEĞER yazdığı alan çiftleri. Gerçek
                    anlaşmazlık burada görünür. Eşik (%85) buna uygulanır ve
                    sunumda söylenecek sayı budur.

    '?' yazan kişi o alanda oylamaya hiç girmez.
    """
    dosyalar = uyum_dosyalari(kisiler, onek)
    etiketleyenler = sorted(k for k, s in dosyalar.items() if s)
    bekleyenler = sorted(k for k in kisiler if k not in etiketleyenler)
    bos = {
        "kisi_sayisi": len(dosyalar),
        "etiketleyenler": etiketleyenler,
        "bekleyenler": bekleyenler,
        "ornek_sayisi": 0,
        "karsilastirilan": 0,
        "uyum": None,
        "ham_uyum": None,
        "alan_bazli": {},
        "ayrisma": [],
    }
    if len(etiketleyenler) < 2:
        return bos

    # kampanya_id -> alan -> {kisi: deger}
    tablo: dict[str, dict[str, dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))
    for kisi, satirlar in dosyalar.items():
        for _, kimlik, etiketler, _dokunuldu in satirlar:
            if not kimlik:
                continue
            for alan, deger in etiketler.items():
                tablo[kimlik][alan][kisi] = deger

    esit = toplam = 0
    esit_dolu = toplam_dolu = 0
    alan_esit: Counter[str] = Counter()
    alan_toplam: Counter[str] = Counter()
    ayrisma: list[str] = []

    for kimlik, alanlar in tablo.items():
        for alan, cevaplar in alanlar.items():
            kisi_listesi = sorted(cevaplar)
            if len(kisi_listesi) < 2:
                continue
            for i in range(len(kisi_listesi)):
                for j in range(i + 1, len(kisi_listesi)):
                    sol, sag = cevaplar[kisi_listesi[i]], cevaplar[kisi_listesi[j]]
                    ayni = _anahtar(sol) == _anahtar(sag)
                    toplam += 1
                    esit += ayni
                    if sol is not None or sag is not None:
                        toplam_dolu += 1
                        esit_dolu += ayni
                        alan_toplam[alan] += 1
                        alan_esit[alan] += ayni
            if len({_anahtar(d) for d in cevaplar.values()}) > 1:
                ozet = " · ".join(f"{k}={cevaplar[k]!r}" for k in kisi_listesi)
                ayrisma.append(f"{kimlik} → {alan}: {ozet}")

    if not tablo:
        return bos

    return {
        "kisi_sayisi": len(dosyalar),
        "etiketleyenler": etiketleyenler,
        "bekleyenler": bekleyenler,
        "ornek_sayisi": len(tablo),
        "karsilastirilan": toplam_dolu,
        "karsilastirilan_ham": toplam,
        "uyum": esit_dolu / toplam_dolu if toplam_dolu else None,
        "ham_uyum": esit / toplam if toplam else None,
        "alan_bazli": {
            a: alan_esit[a] / alan_toplam[a] for a in sorted(alan_toplam) if alan_toplam[a]
        },
        "ayrisma": ayrisma,
    }


KOPYA_ESIGI = 1.00
KOPYA_ASGARI_HUCRE = 10


def kopya_suphesi(kisiler: tuple[str, ...] = KISILER, onek: str = UYUM_ONEK) -> list[str]:
    """İki etiketleyicinin ortak bloğu kusursuz mu örtüşüyor?

    Uyum oranı ancak etiketleme BAĞIMSIZ yapıldıysa anlam taşır. Tamamlanmış bir
    dosya diğerleri etiketlemeden depoya girerse, ya da iki dosyayı aynı kişi
    (veya aynı dil modeli) doldurursa, ölçülen şey uyum değil kopyadır.

    Eskiden bu kontrol serbest metin alanlarına bakıyordu: iki insan bir
    kampanyayı kendi cümleleriyle özetlediğinde sonuç asla harfi harfine aynı
    olmaz, dolayısıyla turnusol kâğıdı iyiydi. Serbest metin alanları CSV'den
    çıkınca kontrol sessizce ölecekti; sekiz çekirdek alana yeniden hedeflendi.

    Yapısal alanlarda birebir eşleşme MEŞRUDUR — doğru etiketleyen iki kişi
    aynı sayıyı yazar. O yüzden eşik %90 değil %100: bağımsız iki insan 5 satır
    × 8 alanda bir yerde mutlaka ayrışır (tarih biçimi, bir aralığın ucu, bir
    türün sınırı). Kusursuz örtüşme, uyumun değil ortak kaynağın işaretidir.

    Boş-boş mutabakatı sayılmaz: yalnız en az birinin DEĞER yazdığı hücreler
    karşılaştırılır. Alanların çoğu zaten boş olduğu için, aksi hâlde her dosya
    çifti %95 örtüşür ve kontrol hiçbir şey söylemez.
    """
    dosyalar = uyum_dosyalari(kisiler, onek)
    tablolar = {
        kisi: {kimlik: etiketler for _, kimlik, etiketler, _d in satirlar}
        for kisi, satirlar in dosyalar.items()
        if satirlar
    }

    uyarilar: list[str] = []
    adlar = sorted(tablolar)
    for i in range(len(adlar)):
        for j in range(i + 1, len(adlar)):
            sol, sag = adlar[i], adlar[j]
            ayni = toplam = 0
            for kimlik, alanlar in tablolar[sol].items():
                diger = tablolar[sag].get(kimlik)
                if diger is None:
                    continue
                for alan in CEKIRDEK_ALANLAR:
                    if alan not in alanlar or alan not in diger:
                        continue  # biri '?' demiş — oylamaya girmez
                    a, b = alanlar[alan], diger[alan]
                    if a is None and b is None:
                        continue  # ortak 'burada bir şey yok' — bilgi taşımaz
                    toplam += 1
                    ayni += _anahtar(a) == _anahtar(b)
            if toplam >= KOPYA_ASGARI_HUCRE and ayni / toplam >= KOPYA_ESIGI:
                uyarilar.append(
                    f"{sol} ↔ {sag}: dolu {toplam} hücrenin {ayni}'si BİREBİR aynı "
                    f"(%{ayni / toplam * 100:.0f}) — bağımsız etiketlemede beklenmez"
                )
    return uyarilar


def uyum_uzlasisi(kisiler: tuple[str, ...] = KISILER) -> tuple[list[dict[str, Any]], list[str]]:
    """Uyum bloğunu çoğunluk oyuyla tek kayda indirger.

    Çoğunluk yoksa (2-2 bölünme gibi) o alan YAZILMAZ. Bölünmüş bir alanı
    rastgele bir tarafa yazmak, cevap anahtarına yazı-tura sokmak olurdu.

    HER TURUN ortak bloğu okunur (bkz. `EK_UYUM_ONEK`); kayıtlar kampanya
    kimliğiyle ayrıldığı için turlar birbirine karışmaz.
    """
    dosyalar: list[list[tuple[int, str, dict[str, Any], bool]]] = []
    for onek in (UYUM_ONEK, EK_UYUM_ONEK):
        dosyalar.extend(uyum_dosyalari(kisiler, onek).values())
    if not dosyalar:
        return [], []

    tablo: dict[str, dict[str, list[Any]]] = defaultdict(lambda: defaultdict(list))
    for satirlar in dosyalar:
        for _, kimlik, etiketler, _dokunuldu in satirlar:
            if not kimlik:
                continue
            for alan, deger in etiketler.items():
                tablo[kimlik][alan].append(deger)

    kayitlar: list[dict[str, Any]] = []
    notlar: list[str] = []
    for kimlik, alanlar in tablo.items():
        kayit: dict[str, Any] = {"kampanya_id": kimlik, "etiketleyen": "uzlasi"}
        for alan, degerler in alanlar.items():
            sayac = Counter(_anahtar(d) for d in degerler)
            en_cok, adet = sayac.most_common(1)[0]
            if adet * 2 > len(degerler):
                kayit[alan] = json.loads(en_cok)
            else:
                notlar.append(f"{kimlik}/{alan}: çoğunluk yok, alan sete girmedi")
        if len(kayit) > 2:
            kayitlar.append(kayit)
    return kayitlar, notlar


def derle(kisiler: tuple[str, ...] = KISILER) -> tuple[list[dict[str, Any]], list[str]]:
    """Kişisel CSV'ler + uzlaştırılmış uyum bloğu -> tek liste."""
    kayitlar: list[dict[str, Any]] = []
    uyarilar: list[str] = []
    gorulen: set[str] = set()

    uzlasi, notlar = uyum_uzlasisi(kisiler)
    uyarilar.extend(notlar)
    for kayit in uzlasi:
        gorulen.add(kayit["kampanya_id"])
        kayitlar.append(kayit)

    for kisi in kisiler:
        # İlk tur + genişletme turu birlikte okunur. Genişletme dosyası yoksa
        # sessiz geçilir: her takım her turu yapmak zorunda değil.
        yollar = [GOLD / f"etiketleme_{kisi.lower()}.csv"]
        if (ek := GOLD / f"{EK_ONEK}{kisi.lower()}.csv").exists():
            yollar.append(ek)

        if not yollar[0].exists():
            uyarilar.append(f"{yollar[0].name} yok — {kisi} henüz başlamamış olabilir")
            if len(yollar) == 1:
                continue
            yollar = yollar[1:]

        for yol in yollar:
            for satir_no, kimlik, etiketler, dokunuldu in _csv_oku(yol):
                if not kimlik:
                    uyarilar.append(f"{yol.name}:{satir_no} kampanya_id boş — atlandı")
                    continue
                if not dokunuldu or not etiketler:
                    uyarilar.append(
                        f"{yol.name}:{satir_no} ({kimlik}) etiketlenmemiş "
                        f"({DOKUNMA_ALANI} boş) — atlandı"
                    )
                    continue
                if kimlik in gorulen:
                    uyarilar.append(f"{kimlik} birden fazla yerde etiketli — ilki korundu")
                    continue

                gorulen.add(kimlik)
                kayitlar.append({"kampanya_id": kimlik, "etiketleyen": kisi, **etiketler})

    return kayitlar, uyarilar


def jsonl_yaz(kayitlar: list[dict[str, Any]]) -> None:
    GOLD.mkdir(parents=True, exist_ok=True)
    ALTIN_SET.write_text(
        "\n".join(json.dumps(k, ensure_ascii=False) for k in kayitlar) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Denetim
# ---------------------------------------------------------------------------

GECERLI_TURLER = {t.value for t in KampanyaTuru}
GECERLI_KITLELER = {h.value for h in HedefKitle}


def denetle(kayitlar: list[dict[str, Any]], kampanyalar: list[Kampanya]) -> list[str]:
    """Etiketleme hatalarını yakalar — yanlış altın set, ölçümü sessizce bozar."""
    hatalar: list[str] = []
    bilinen = {k.kampanya_id for k in kampanyalar}

    for kayit in kayitlar:
        kimlik = kayit["kampanya_id"]
        if kimlik not in bilinen:
            hatalar.append(f"{kimlik}: veritabanında böyle bir kampanya yok")

        tur = kayit.get("kampanya_turu")
        if tur and tur not in GECERLI_TURLER:
            hatalar.append(f"{kimlik}: kampanya_turu '{tur}' geçersiz")

        kitle = kayit.get("hedef_kitle")
        if kitle and kitle not in GECERLI_KITLELER:
            hatalar.append(f"{kimlik}: hedef_kitle '{kitle}' geçersiz")

        for alan in SAYISAL_ALANLAR:
            deger = kayit.get(alan)
            if deger is not None and not isinstance(deger, int | float):
                hatalar.append(f"{kimlik}: {alan} sayıya çevrilemedi -> {deger!r}")

        oran = kayit.get("kar_payi_orani")
        # SIFIR GEÇERLİDİR — "vade farksız" kampanyada kâr payı gerçekten
        # sıfırdır, bilinmiyor değil. `dosya_denetle` bunu zaten kabul ediyordu;
        # burası `0 < oran` diyordu ve etiketleyen `make altin-denetle`den ✅
        # alıp `make altin-derle`de hata yiyordu.
        if isinstance(oran, int | float) and not 0 <= oran < AYLIK_KAR_PAYI_UST_SINIRI:
            hatalar.append(f"{kimlik}: kar_payi_orani %{oran} — aylık oran için şüpheli")

        vade = kayit.get("vade_ay_max")
        if isinstance(vade, int | float) and not 0 < vade <= 360:
            hatalar.append(f"{kimlik}: vade_ay_max {vade} ay — şüpheli")

    return hatalar


_AY_ADLARI_TR = (
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
)


def _sayi_varyantlari(deger: float) -> list[str]:
    """Bir sayının Türkçe metinde geçebileceği yazımları."""
    if float(deger).is_integer():
        tam = int(deger)
        binlikli = f"{tam:,}".replace(",", ".")
        return [str(tam), binlikli, binlikli.replace(".", " ")]
    ondalikli = f"{deger:.10f}".rstrip("0").rstrip(".")
    return [ondalikli.replace(".", ","), ondalikli]


def _tarih_varyantlari(iso: str) -> list[str]:
    try:
        gun = date.fromisoformat(iso)
    except ValueError:
        return [iso]
    return [
        iso,
        f"{gun.day:02d}.{gun.month:02d}.{gun.year}",
        f"{gun.day}.{gun.month}.{gun.year}",
        f"{gun.day:02d}/{gun.month:02d}/{gun.year}",
        f"{gun.day} {_AY_ADLARI_TR[gun.month - 1]} {gun.year}",
    ]


def kanit_uyarilari(kayitlar: list[dict[str, Any]], kampanyalar: list[Kampanya]) -> list[str]:
    """Etiketlenen sayı/tarih ham metinde geçiyor mu?

    Şemanın kanıt zinciri ilkesini cevap anahtarına da uygular: bir oran ya da
    tutar metinde YAZIYOR olmalı. Geçmiyorsa üç ihtimal var — etiketleyen yanlış
    okudu, kafasından çıkardı ya da metinde alışılmadık bir biçimde yazılmış.
    Üçü de bakılmayı hak eder.

    Bunlar HATA değil UYARI'dır: "%2,05'ten başlayan" gibi ifadeler ya da
    "yarım milyon TL" gibi yazımlar meşru olduğu hâlde eşleşmeyebilir. Derlemeyi
    durdurmaz, göz gezdirilecek listeyi verir.
    """
    metinler = {k.kampanya_id: k.ham_metin for k in kampanyalar}
    uyarilar: list[str] = []

    for kayit in kayitlar:
        metin = metinler.get(kayit["kampanya_id"])
        if not metin:
            continue

        for alan in SAYISAL_ALANLAR:
            deger = kayit.get(alan)
            if not isinstance(deger, int | float) or isinstance(deger, bool):
                continue
            if not any(v in metin for v in _sayi_varyantlari(deger)):
                uyarilar.append(f"{kayit['kampanya_id']}: {alan}={deger} ham metinde geçmiyor")

        bitis = kayit.get("kampanya_bitis")
        if isinstance(bitis, str) and bitis:
            if not any(v in metin for v in _tarih_varyantlari(bitis)):
                uyarilar.append(f"{kayit['kampanya_id']}: kampanya_bitis={bitis} metinde geçmiyor")

    return uyarilar


def kapsam_raporu(kayitlar: list[dict[str, Any]], kampanyalar: list[Kampanya]) -> str:
    kimlik_banka = {k.kampanya_id: k.banka_adi for k in kampanyalar}
    banka = Counter(kimlik_banka.get(k["kampanya_id"], "?") for k in kayitlar)
    tur = Counter(k.get("kampanya_turu") or "belirtilmemis" for k in kayitlar)
    kisi = Counter(k.get("etiketleyen", "?") for k in kayitlar)

    satir = [f"  Örnek: {len(kayitlar)}", "", "  Kişi başına:"]
    satir += [f"    {a}: {n}" for a, n in kisi.most_common()]
    satir += ["", "  Banka başına:"]
    satir += [f"    {a}: {n}" for a, n in banka.most_common()]
    satir += ["", "  Tür başına:"]
    satir += [f"    {a}: {n}" for a, n in tur.most_common()]
    return "\n".join(satir)


# ---------------------------------------------------------------------------
# Komutlar
# ---------------------------------------------------------------------------


def _kampanyalari_al() -> list[Kampanya]:
    kampanyalar = list(kampanyalari_oku())
    if not kampanyalar:
        print("❌ Veritabanı boş. Önce `make crawl && make extract` çalıştırın.")
        raise SystemExit(1)
    return kampanyalar


def doldurulmus_sayfalar(kisiler: tuple[str, ...] = KISILER) -> list[str]:
    """İçinde etiket bulunan çalışma sayfaları — üzerine yazmadan önce sorulur."""
    dolu: list[str] = []
    for kisi in kisiler:
        for kalip in (f"etiketleme_{kisi.lower()}.csv", f"etiketleme_uyum_{kisi.lower()}.csv"):
            yol = GOLD / kalip
            if not yol.exists():
                continue
            etiketli = sum(1 for _, _, _, dokunuldu in _csv_oku(yol) if dokunuldu)
            if etiketli:
                dolu.append(f"{kalip} ({etiketli} satır)")
    return dolu


def komut_genislet(hedef_n: int = 20, uygula: bool = False) -> int:
    """Zayıf alanları kapatacak EK örneklem çıkarır (mevcut seti bozmadan).

    `ornekle`den farkı: baştan set kurmaz, VAR OLAN setin eksiğini tamamlar.
    Zaten etiketlenmiş kayıtlar havuzdan çıkarılır; seçim yalnız ham metindeki
    yüzey işaretlerine bakar (bkz. `ZAYIF_ALAN_ISARETLERI`).
    """
    from eval.calistir import altin_seti_yukle

    altin = altin_seti_yukle()
    if not altin:
        print("❌ Altın set bulunamadı. Önce `make altin-ornekle` + `make altin-derle`.")
        return 1

    mevcut = alan_doluluk_raporu(altin)
    gerekli = {a: max(0, hedef_n - n) for a, n in mevcut.items() if a in ZAYIF_ALAN_ISARETLERI}

    print(f"Altın set: {len(altin)} kayıt · hedef N={hedef_n}\n")
    print(f"{'alan':24}{'mevcut N':>9}{'gereken':>9}")
    print("-" * 42)
    for alan in ZAYIF_ALAN_ISARETLERI:
        print(f"{alan:24}{mevcut.get(alan, 0):9}{gerekli.get(alan, 0):9}")

    if not any(gerekli.values()):
        print("\n✅ Tüm alanlar hedefte. Genişletmeye gerek yok.")
        return 0

    etiketli = {r.get("kampanya_id") for r in altin}
    havuz = [k for k in _kampanyalari_al() if k.kampanya_id not in etiketli]
    secilen = hedefli_ornekle(havuz, gerekli)

    print(f"\n✅ {len(secilen)} EK kayıt seçildi (etiketsiz havuz: {len(havuz)})\n")

    # Seçim sonrası hangi alanlar hâlâ açık? Korpus sınırı burada görünür.
    desenler = {a: re.compile(d, re.I) for a, d in ZAYIF_ALAN_ISARETLERI.items()}
    print(f"{'alan':24}{'hedef N':>9}{'ulaşılabilir':>13}{'durum':>10}")
    print("-" * 58)
    for alan, gerek in gerekli.items():
        if not gerek:
            continue
        kapanan = sum(1 for k in secilen if desenler[alan].search(k.ham_metin or ""))
        varilan = mevcut.get(alan, 0) + kapanan
        durum = "✅" if varilan >= hedef_n else "🔴 KORPUS YETMİYOR"
        print(f"{alan:24}{hedef_n:9}{varilan:13}{durum:>10}")

    banka = Counter(k.banka_adi[:20] for k in secilen)
    print(f"\nBanka dağılımı: {dict(banka)}")
    if not uygula:
        print(
            "\nBu bir PLANDIR, dosya yazılmadı."
            "\nÇalışma sayfalarını üretmek için:  make altin-genislet uygula=1"
        )
        return 0

    # Çalışan kişiler: ilk turda dördü vardı. Genişletme turunda kimin
    # etiketleyeceği takım kararıdır; varsayılan olarak ilk turdaki
    # dosyalardan hangileri DOLU ise onlar sürdürür.
    GOLD.mkdir(parents=True, exist_ok=True)
    METINLER.mkdir(parents=True, exist_ok=True)

    uyum = secilen[:UYUM_ADET]
    kisisel = secilen[UYUM_ADET:]
    paylar: dict[str, list[Kampanya]] = {k: [] for k in KISILER}
    for sira, kampanya in enumerate(kisisel):
        paylar[KISILER[sira % len(KISILER)]].append(kampanya)

    yazilan: list[str] = []
    for kisi in KISILER:
        for yol, kume in (
            (GOLD / f"{EK_ONEK}{kisi.lower()}.csv", paylar[kisi]),
            (GOLD / f"{EK_ONEK}uyum_{kisi.lower()}.csv", uyum),
        ):
            if yol.exists() and _etiketli_mi(yol):
                print(f"🛡️  {yol.name} etiket içeriyor — DOKUNULMADI")
                continue
            _csv_yaz(yol, kume)
            yazilan.append(f"{yol.name} ({len(kume)} satır)")

    for kampanya in secilen:
        (METINLER / f"{kampanya.kampanya_id}.txt").write_text(
            kampanya.ham_metin or "", encoding="utf-8"
        )

    print("\n✅ Genişletme çalışma sayfaları yazıldı:")
    for satir in yazilan:
        print(f"     data/gold/{satir}")
    print(
        f"\n  1️⃣  UYUM BLOĞU — ilk {len(uyum)} kayıt, herkes etiketler"
        f"\n  2️⃣  KİŞİSEL PAY — kişi başı ~{len(kisisel) // max(1, len(KISILER))} kayıt"
        "\n\n  Bitince:  make altin-denetle ad=<adın>  →  make altin-derle  →  make eval"
        "\n\n  ⚠️  İlk turun dosyaları (etiketleme_<ad>.csv) DEĞİŞMEDİ."
        " `derle` ikisini birden okur."
    )
    return 0


def komut_ornekle(adet: int, zorla: bool = False) -> int:
    kampanyalar = _kampanyalari_al()
    if adet > len(kampanyalar):
        print(f"⚠️  Sadece {len(kampanyalar)} kampanya var, örneklem buna düşürüldü.")
        adet = len(kampanyalar)

    if zorla and (dolu := doldurulmus_sayfalar()):
        print("⚠️  --zorla verildi, aşağıdaki etiketler SİLİNİYOR:")
        for satir in dolu:
            print(f"     {satir}")

    secilen = katmanli_ornekle(kampanyalar, adet)
    uyum_blogu, sayilar, korunan = calisma_sayfalari_yaz(secilen, KISILER, zorla)
    okuma_kagitlari_yaz(KISILER)

    if korunan:
        print("🛡️  Etiket içerdiği için KORUNAN sayfalar (yeniden yazılmadı):")
        for ad in korunan:
            print(f"     {ad}")
        print()

    print(f"✅ {len(secilen)} örnek seçildi (tohum {TOHUM}, katmanlı)\n")
    print(f"  1️⃣  UYUM BLOĞU — {len(uyum_blogu)} örnek, DÖRDÜ DE etiketler (H-02)")
    for kisi in KISILER:
        print(f"       data/gold/etiketleme_uyum_{kisi.lower()}.csv")
    print("\n  2️⃣  KİŞİSEL PAY — tek etiketleyici (H-01)")
    for kisi, sayi in sayilar.items():
        print(f"       data/gold/etiketleme_{kisi.lower()}.csv → {kisi}: {sayi} örnek")

    toplam_kisi = len(uyum_blogu) + max(sayilar.values(), default=0)
    print(f"\n   Kişi başı toplam yük: ~{toplam_kisi} satır × {len(CEKIRDEK_ALANLAR)} alan")
    print("   Okuma kâğıdı: data/gold/okuma_<ad>.md  (ilgili cümleler alan alan hazır)")
    print(f"   Tam metinler: data/gold/metinler/ ({len(secilen)} dosya)")
    print(f"   Örneklem kaydı: {_kisa_yol(ORNEK_KAYDI)}")
    print("\n   Tür dağılımı:")
    for tur, sayi in Counter(_tur(k) for k in secilen).most_common():
        print(f"     {tur}: {sayi}")
    print("\n📖 Etiketlemeden önce docs/ETIKETLEME_KILAVUZU.md okunmalı (tek sayfa).")
    print("   Sıra: uyum bloğu → `make altin-uyum` → tartış → kişisel pay")
    return 0


def komut_uyum() -> int:
    onek = UYUM_ONEK
    print(f"\n  Kaynak: uyum bloğu ({onek}<ad>.csv)")
    sonuc = uyum_hesapla(KISILER, onek)
    if sonuc["uyum"] is None:
        etiketleyen = sonuc.get("etiketleyenler") or []
        bekleyen = sonuc.get("bekleyenler") or []
        if not sonuc["kisi_sayisi"]:
            print("❌ Uyum dosyası bulunamadı. Önce `make altin-ornekle` çalıştırın.")
        elif not etiketleyen:
            print("❌ Uyum dosyalarının hiçbiri doldurulmamış.")
            print("   Dosyalar: data/gold/etiketleme_uyum_<ad>.csv")
        else:
            print(f"⏳ Uyum oranı için en az iki kişi gerekiyor — şu an {len(etiketleyen)} kişi.")
            print(f"   ✅ Bitirenler : {', '.join(etiketleyen)}")
            print(f"   ⌛ Bekleyenler: {', '.join(bekleyen)}")
        return 1

    kopya = kopya_suphesi(KISILER, onek)
    if kopya:
        print("\n🚨 KOPYA ŞÜPHESİ — uyum oranı bu haliyle GEÇERSİZ\n")
        for satir in kopya:
            print(f"   {satir}")
        print(
            "\n   Uyum ancak bağımsız etiketlemede anlam taşır. Tamamlanmış bir\n"
            "   dosya depoya girdiyse sonrakiler cevabı görmüş olur.\n"
            "   Çözüm: yeni bir uyum bloğu çekin; dosyalar HERKES bitirmeden\n"
            "   pushlanmasın (doğrudan kaptana gönderilip tek seferde işlensin).\n"
        )

    oran = sonuc["uyum"]
    print(f"\n  Etiketleyici sayısı: {sonuc['kisi_sayisi']} · Örnek: {sonuc['ornek_sayisi']}")
    print(f"  Karşılaştırılan alan çifti: {sonuc['karsilastirilan']} (dolu)")
    print(f"\n  📊 UYUM ORANI: %{oran * 100:.1f}   (hedef ≥ %85)")
    print(f"     ham oran (boş alanlar dahil): %{sonuc['ham_uyum'] * 100:.1f}")
    print("     Sunumda DOLU alan oranı söylenir — ham oran, ortak 'burada bir")
    print("     şey yok' mutabakatıyla şiştiği için tek başına bilgi vermez.\n")

    zayif = [(a, o) for a, o in sonuc["alan_bazli"].items() if o < 0.85]
    if zayif:
        print("  En çok ayrıştığınız alanlar:")
        for alan, o in sorted(zayif, key=lambda x: x[1]):
            print(f"    {alan}: %{o * 100:.0f}")
    if sonuc["ayrisma"]:
        print(f"\n  Ayrışan {len(sonuc['ayrisma'])} karar (ilk 15):")
        for satir in sonuc["ayrisma"][:15]:
            print(f"    {satir}")

    if kopya:
        print("\n❌ Bu oran SUNUMDA KULLANILAMAZ — yukarıdaki kopya şüphesi giderilmeden")
        print("   «etiketleme uzlaşmamız %X» cümlesi kurulmamalı.")
        return 1

    if oran >= 0.85:
        print("\n✅ Uyum yeterli. Kişisel paylara dağılabilirsiniz.")
        print(f"   Sunum cümlesi: «etiketleme uzlaşmamız %{oran * 100:.0f}»")
        return 0
    print("\n⚠️  Uyum %85'in altında. Dağılmadan önce ayrışan alanları konuşun ve")
    print("   kararı docs/ETIKETLEME_KILAVUZU.md «Kararlar defteri» tablosuna yazın.")
    return 0


def komut_derle() -> int:
    kampanyalar = _kampanyalari_al()
    kayitlar, uyarilar = derle()

    for uyari in uyarilar:
        print(f"⚠️  {uyari}")

    if not kayitlar:
        print("\n❌ Hiç etiket bulunamadı. CSV'ler boş — önce etiketleyin.")
        return 1

    hatalar = denetle(kayitlar, kampanyalar)
    kanit = kanit_uyarilari(kayitlar, kampanyalar)
    jsonl_yaz(kayitlar)

    print(f"\n✅ {_kisa_yol(ALTIN_SET)} yazıldı — {len(kayitlar)} örnek\n")
    print(kapsam_raporu(kayitlar, kampanyalar))

    if kanit:
        print(f"\n🔎 {len(kanit)} değer ham metinde bulunamadı — gözden geçirin:")
        for satir in kanit[:15]:
            print(f"   {satir}")
        print("   (Uyarıdır, hata değil: 'yarım milyon TL' gibi yazımlar meşrudur.)")

    if hatalar:
        print(f"\n❌ {len(hatalar)} denetim hatası:")
        for hata in hatalar[:20]:
            print(f"   {hata}")
        print("\n   Düzeltip tekrar `make altin-derle` çalıştırın.")
        return 1

    print("\n   Sonraki adım: `make eval`")
    return 0


_TUR_ESANLAMLI: dict[str, str] = {
    # docs/ETIKETLEME_KILAVUZU.md «kampanya_turu seçenekleri» karar sırasında
    # AÇIKÇA yazanlar
    "arac": "tasit_finansmani", "araba": "tasit_finansmani", "otomobil": "tasit_finansmani",
    "kredi karti": "kart", "kart aidati": "kart", "taksit": "kart",
    "puan": "alisveris_puani", "mil": "alisveris_puani", "chip para": "alisveris_puani",
    "katilma": "yatirim_urunu", "katilma hesabi": "yatirim_urunu",
    "altin": "yatirim_urunu", "fon": "yatirim_urunu", "sukuk": "yatirim_urunu",
    "ev": "konut_finansmani", "mortgage": "konut_finansmani",
    # Uyum bloğunda diğer ÜÇ etiketleyicinin hemfikir olduğu karşılıklar
    "davet": "yeni_musteri",   # "arkadaşını davet et" — üçü de yeni_musteri dedi
    "isyeri": "finansman",     # ürün türü belirsiz finansman — üçü de finansman dedi
}
"""Etiketleyenin doğal yazımı -> enum. Kaynağı iki tanedir ve ikisi de bizim
görüşümüz değildir: kılavuzun kendi karar listesi, ya da uyum bloğunda diğer üç
kişinin aynı satırda vardığı ortak karar. Bu sözlüğe 'bize mantıklı geldi' diye
madde eklenmez — altın set, tahminlerimizin değil metnin cevap anahtarıdır."""

_KITLE_ESANLAMLI: dict[str, str] = {
    "genel": "tum_musteriler", "herkes": "tum_musteriler", "tumu": "tum_musteriler",
    "mevcut": "mevcut_musteri", "maas": "maas_musterisi",
    # schema.py: SEGMENT = öğrenci, emekli, KOBİ, kadın girişimci vb.
    "emekli": "segment", "ogrenci": "segment", "kobi": "segment",
}

_DOGRU_SOZCUKLER = frozenset({"evet", "true", "1", "var", "e"})
_YANLIS_SOZCUKLER = frozenset({"hayir", "hayır", "false", "0", "yok", "h", "hayır."})


def _yakin_oneri(deger: str, gecerliler: set[str]) -> str:
    """Yanlış yazılmış bir enum için en olası geçerli karşılığı önerir.

    İki tasarım kararı:

    1. Önce `arama_anahtari` ile Türkçe harfler ASCII'ye indirilir. Enum
       değerleri şapkasızdır (`tasit_finansmani`); etiketleyen ise doğal olarak
       "taşıt" yazar. Normalizasyon olmadan 'ş' ≠ 's' yüzünden alt dize eşleşmesi
       kaçar ve difflib harf örtüşmesine bakıp "taşıt → kart" gibi saçma bir
       öneri üretir.
    2. difflib eşiği bilinçli olarak YÜKSEK. Yanlış öneri, önerisizlikten
       kötüdür: son tarihe yetişmeye çalışan bir etiketleyici öneriyi sorgusuz
       kabul eder. Emin olamadığımızda geçerli değerlerin tamamını basıp kararı
       insana bırakıyoruz.
    """
    anahtar = arama_anahtari(deger)

    esanlamli = _TUR_ESANLAMLI if gecerliler == GECERLI_TURLER else _KITLE_ESANLAMLI
    if anahtar in esanlamli:
        return esanlamli[anahtar]

    for gecerli in sorted(gecerliler):
        if gecerli.startswith(anahtar) or anahtar in gecerli:
            return gecerli
    yakin = difflib.get_close_matches(anahtar, sorted(gecerliler), n=1, cutoff=0.75)
    if yakin:
        return yakin[0]
    return "geçerliler: " + ", ".join(sorted(gecerliler))


def dosya_denetle(yol: Path) -> tuple[list[str], int, int]:
    """Tek bir etiketleme CSV'sini satır satır denetler.

    `_csv_oku` yerine HAM hücreleri okur. `_hucre_cozumle` bilinçli olarak
    bağışlayıcıdır — çözemediği tarihi ve sayıyı sessizce metin olarak geçirir,
    çünkü derleme sırasında tek bir hücre yüzünden koşuyu düşürmek istemeyiz.
    Ama etiketleyene geri bildirim verirken o bağışlayıcılık tam tersine
    dönmeli: çözülemeyen her hücre burada görünür.

    Dönen: (hatalar, etiketlenen_satir, toplam_satir)
    """
    hatalar: list[str] = []
    toplam = etiketlenen = 0

    with yol.open(encoding="utf-8-sig", newline="") as dosya:
        okuyucu = csv.DictReader(dosya)
        sutunlar = _etiket_sutunlari(okuyucu)
        for satir_no, satir in enumerate(okuyucu, start=2):
            toplam += 1
            yer = f"satır {satir_no}"

            # `kampanya_turu` satırın 'bakıldı' işareti (bkz. DOKUNMA_ALANI).
            # Boşsa satırın TAMAMI derlemede atlanır — en pahalı sessiz hata bu.
            tur_ham = (satir.get(DOKUNMA_ALANI) or "").strip()
            if not tur_ham:
                hatalar.append(
                    f"{yer}  {DOKUNMA_ALANI} BOŞ → bu satırın tamamı altın sete "
                    f"girmez. Hiçbir tür uymuyorsa 'diger' yaz."
                )
                continue
            etiketlenen += 1

            for alan in sutunlar:
                ham = (satir.get(alan) or "").strip()
                if not ham or ham == EMIN_DEGIL:
                    continue  # boş = 'metinde yok', '?' = metrik dışı; ikisi de geçerli

                if alan == "kampanya_turu" and ham not in GECERLI_TURLER:
                    hatalar.append(
                        f"{yer}  kampanya_turu={ham!r} geçersiz → {_yakin_oneri(ham, GECERLI_TURLER)}"
                    )
                elif alan == "hedef_kitle" and ham not in GECERLI_KITLELER:
                    hatalar.append(
                        f"{yer}  hedef_kitle={ham!r} geçersiz → {_yakin_oneri(ham, GECERLI_KITLELER)}"
                    )
                elif alan in TARIH_ALANLAR:
                    try:
                        date.fromisoformat(ham)
                    except ValueError:
                        if tarih_ayristir(ham) is None:
                            hatalar.append(
                                f"{yer}  {alan}={ham!r} tarihe çevrilemedi → YYYY-AA-GG yaz (2026-09-30)"
                            )
                elif alan in BOOL_ALANLAR:
                    if ham.lower() not in _DOGRU_SOZCUKLER | _YANLIS_SOZCUKLER:
                        hatalar.append(
                            f"{yer}  {alan}={ham!r} anlaşılmadı → 'evet' veya 'hayır' yaz"
                        )
                elif alan in SAYISAL_ALANLAR:
                    sayi = sayi_ayristir(ham)
                    if sayi is None:
                        hatalar.append(f"{yer}  {alan}={ham!r} sayıya çevrilemedi")
                    elif alan == "kar_payi_orani" and not 0 <= sayi < AYLIK_KAR_PAYI_UST_SINIRI:
                        # SIFIR GEÇERLİDİR ve boş hücreden farklıdır: "vade farksız"
                        # kampanyada kâr payı gerçekten sıfırdır, bilinmiyor değil.
                        # 15 Ağustos'ta bu ayrım yokken gerçek bir etiket
                        # ("Pratik Finansman Kart", vade farksız) şüpheli sayılıyordu.
                        hatalar.append(
                            f"{yer}  kar_payi_orani=%{sayi} — AYLIK oran bekleniyor, şüpheli"
                        )
                    elif alan == "vade_ay_max" and not 0 < sayi <= 360:
                        hatalar.append(f"{yer}  vade_ay_max={sayi} ay — şüpheli")

    return hatalar, etiketlenen, toplam


def atlanma_uyarilari(yol: Path, kampanyalar: list[Kampanya]) -> list[str]:
    """Boş bırakılan hücrelerde sistem bir DEĞER bulmuş mu?

    NEDEN GEREKLİ — sözleşmede kapatılamayan tek delik buydu:
        Boş hücre "bu alan metinde yok" demektir ve metriğe böyle girer. Doğru
        bir tasarım, ama bir maliyeti var: hiç bakılmadan boş bırakılan hücre
        ile bakılıp "yok" denen hücre BİREBİR aynı görünür. `kampanya_turu`
        satır düzeyinde "bakıldı" işareti verir, hücre düzeyinde karşılığı yok.

        15 Ağustos ölçümü: çekirdek alanların yalnız %20-43'ü doluydu ve 10
        ortak kayıtta karşılaştırılabilir sadece 16-20 hücre kalıyordu. Uyum
        oranı bu yüzden hesaplanamıyordu — anlaşmazlıktan değil, seyreklikten.

    NEDEN HATA DEĞİL, UYARI:
        Sistemin değer bulduğu yerde insanın "yok" demesi MEŞRU olabilir ve
        tam da metriğin yakalaması gereken şeydir (sistem yanlış pozitifi).
        Bu yüzden push'u engellemez; etiketleyeni "bunu bilerek mi boş
        bıraktın?" diye bir kez durdurur. Kararı insan verir, araç sormakla
        yetinir.
    """
    kimlik_kampanya = {k.kampanya_id: k for k in kampanyalar}
    uyarilar: list[str] = []

    with yol.open(encoding="utf-8-sig", newline="") as dosya:
        for satir_no, satir in enumerate(csv.DictReader(dosya), start=2):
            if not (satir.get(DOKUNMA_ALANI) or "").strip():
                continue  # satıra hiç bakılmamış; zaten hata olarak raporlanıyor
            kampanya = kimlik_kampanya.get((satir.get("kampanya_id") or "").strip())
            if kampanya is None:
                continue

            bos_ama_dolu = [
                alan
                for alan in CEKIRDEK_ALANLAR
                if not (satir.get(alan) or "").strip()
                and getattr(kampanya, alan, None) is not None
                and getattr(kampanya, alan).var_mi
            ]
            if bos_ama_dolu:
                uyarilar.append(
                    f"satır {satir_no}  boş bıraktın ama sistem değer buldu: "
                    f"{', '.join(bos_ama_dolu)}"
                )
    return uyarilar


def _cekirdek_ilerleme(yol: Path) -> tuple[int, int]:
    """Çekirdek sekiz alanda kaç hücre dolduruldu / doldurulmalı."""
    dolu = gereken = 0
    with yol.open(encoding="utf-8-sig", newline="") as dosya:
        for satir in csv.DictReader(dosya):
            for alan in CEKIRDEK_ALANLAR:
                gereken += 1
                if (satir.get(alan) or "").strip():
                    dolu += 1
    return dolu, gereken


OKUMA_ONEK = "okuma_"
_ALAN_IPUCLARI: dict[str, tuple[str, ...]] = {
    "kampanya_turu": ("finansman", "kampanya", "kart", "hesap"),
    "kar_payi_orani": ("kâr payı", "kar payı", "kâr oranı", "oran"),
    "vade_ay_max": ("vade", "taksit", "aya kadar", "ay vade"),
    "finansman_tutari_max": ("finansman", "limit", "tutar"),
    "tahsis_ucreti": ("tahsis", "dosya masraf", "komisyon", "ücret"),
    "masrafsiz_mi": ("masraf", "ücret", "komisyon", "tahsis"),
    "odul_miktari": ("ödül", "hediye", "kazan", "iade", "puan"),
    "kampanya_bitis": ("geçerlidir", "geçerli", "son başvuru", "tarihine"),
}

_SAYI_GEREKTIREN = frozenset(SAYISAL_ALANLAR) | {"kampanya_bitis"}
"""Bu alanlarda RAKAM içermeyen cümle gösterilmez.

İlk sürüm "kadar" ve "tl" gibi her yerde geçen ipuçları kullanıyordu ve
`kampanya_bitis` altına finansman cümleleri düşüyordu. Sayısal bir alanın
kanıtı sayı içermek zorundadır; bu tek kısıt isabeti belirgin biçimde
artırıyor."""

_RAKAM = re.compile(r"\d")
"""Alan başına metinde aranacak ipuçları — okuma yardımı içindir, ÇIKARIM DEĞİL.

Bilinçli olarak `kural.py`'deki `baglam_sozcukleri`nden ayrı tutuldu: orası
neyin kabul edileceğine karar verir, burası insanın nereye bakacağını söyler.
İkisini birleştirmek, etiketleyeni kuralın gördüğü yere hapsederdi — kuralın
kaçırdığı değer de tam olarak orada bulunur."""


def _ilgili_cumleler(metin: str, alan: str, azami: int = 3) -> list[str]:
    """Bir alanla ilgili olabilecek cümleleri metinden seçer."""
    ipuclari = _ALAN_IPUCLARI.get(alan, ())
    sayi_sart = alan in _SAYI_GEREKTIREN
    bulunan: list[str] = []
    for parca in re.split(r"(?<=[.!?\n])\s+", metin):
        temiz = " ".join(parca.split())
        if not (30 <= len(temiz) <= 260):
            continue
        if sayi_sart and not _RAKAM.search(temiz):
            continue
        kucuk = temiz.lower()
        if any(ipucu in kucuk for ipucu in ipuclari) and temiz not in bulunan:
            bulunan.append(temiz)
        if len(bulunan) >= azami:
            break
    return bulunan


def okuma_kagidi(yollar: list[Path]) -> str:
    """Etiketlemeyi kolaylaştıran okuma kâğıdı — her satır için ilgili cümleler.

    NEDEN VAR:
        Etiketlemenin pahalı kısmı karar vermek değil, ARAMAK: 2.500 karakterlik
        bir banka sayfasında vadenin nerede geçtiğini bulmak. Bu kâğıt sekiz
        alanın her biri için aday cümleleri önden çıkarır; etiketleyen CSV'nin
        yanında açar ve doğrudan karara geçer.

    NEDEN SİSTEMİN ÇIKTISI GÖSTERİLMEZ:
        Kâğıt yalnız BANKA METNİNİ gösterir. Sistemin kendi çıkarımını buraya
        koymak cevap anahtarını sistemin kopyasına çevirirdi — doğruluk %100
        çıkar ve hiçbir şey ölçmemiş oluruz. Etiketleyenin dayanağı yalnızca
        banka metnidir.

    NEDEN ALINTI, TAM METİN DEĞİL:
        Alıntılar YOL GÖSTERİCİDİR, kanıt değil. İpucu listesi kaçırabilir; bir
        alanın altı boşsa bu "metinde yok" demek değil, "aday bulunamadı"
        demektir. Karar her zaman metnin tamamına aittir —
        `data/gold/metinler/<kampanya_id>.txt`.
    """
    satirlar = [
        "# Okuma kâğıdı",
        "",
        "Bu sayfa **karar vermez, arama yapar.** Her satır için sekiz alanın aday "
        "cümlelerini önden çıkarır; sen okuyup CSV'ye yazarsın.",
        "",
        "- Boş hücre **\"metinde yok\"** demektir ve cevap anahtarına öyle girer.",
        "- Bakmadan geçiyorsan **`?`** yaz — o hücre metrikten çıkar.",
        "- Bir alanın altında alıntı yoksa **metinde yok demek değildir**; "
        "ipucu bulunamadı demektir. Şüphedeysen tam metne bak.",
        "",
        "Kurallar: `docs/ETIKETLEME_KILAVUZU.md`",
        "",
        "---",
        "",
    ]

    for yol in yollar:
        satirlar += [f"# {yol.name}", ""]
        with yol.open(encoding="utf-8-sig", newline="") as dosya:
            for satir_no, satir in enumerate(csv.DictReader(dosya), start=2):
                metin = satir.get("metin") or ""
                kimlik = (satir.get("kampanya_id") or "").strip()
                satirlar += [
                    f"## satır {satir_no} — {satir.get('banka_adi', '')}",
                    f"<{satir.get('kaynak_url', '')}>",
                    f"Tam metin: `data/gold/metinler/{kimlik}.txt`",
                    "",
                ]
                for alan in CEKIRDEK_ALANLAR:
                    satirlar.append(f"**{alan}**")
                    cumleler = _ilgili_cumleler(metin, alan)
                    satirlar += [f"> {c}" for c in cumleler] or [
                        "> _(aday cümle bulunamadı — tam metne bak)_"
                    ]
                    satirlar.append("")
                satirlar += ["---", ""]

    return "\n".join(satirlar)


def okuma_kagitlari_yaz(kisiler: tuple[str, ...] = KISILER) -> list[Path]:
    """Kişi başına tek okuma kâğıdı: uyum bloğu + kişisel pay bir arada.

    `ornekle` içinden otomatik çağrılır. Ayrı bir komut olarak dursaydı kimse
    çalıştırmazdı; etiketlemeyi ucuzlatan asıl şeyin ayrı bir adım olmaması
    gerekiyor.
    """
    uretilen: list[Path] = []
    for kisi in kisiler:
        yollar = [
            yol
            for onek in (UYUM_ONEK, "etiketleme_")
            if (yol := GOLD / f"{onek}{kisi.lower()}.csv").exists()
        ]
        if not yollar:
            continue
        hedef = GOLD / f"{OKUMA_ONEK}{kisi.lower()}.md"
        hedef.write_text(okuma_kagidi(yollar), encoding="utf-8")
        uretilen.append(hedef)
    return uretilen


def komut_denetle(ad: str | None) -> int:
    """Kişi CSV'sini pushlamadan önce denetler — H-01'in kalite kapısı."""
    kisiler = (ad,) if ad else KISILER
    onekler = ("etiketleme_", UYUM_ONEK)

    # Atlanma uyarısı sistemin çıkarımıyla karşılaştırma gerektiriyor; veritabanı
    # yoksa denetimin geri kalanı yine de çalışmalı (kılavuz koşusu, CI vb.).
    try:
        kampanyalar = _kampanyalari_al()
    except Exception:  # noqa: BLE001 — veritabanı yoksa uyarıdan vazgeçilir
        kampanyalar = []

    bulunan = 0
    toplam_hata = 0
    for kisi in kisiler:
        for onek in onekler:
            yol = GOLD / f"{onek}{kisi.lower()}.csv"
            if not yol.exists():
                continue
            bulunan += 1
            hatalar, etiketlenen, toplam = dosya_denetle(yol)
            dolu, gereken = _cekirdek_ilerleme(yol)

            yuzde = f" (%{dolu / gereken * 100:.0f})" if gereken else ""
            print(f"\n📄 {_kisa_yol(yol)}")
            print(
                f"   Etiketlenen satır: {etiketlenen}/{toplam}   ·   "
                f"Çekirdek 8 alan: {dolu}/{gereken} hücre{yuzde}"
            )
            if hatalar:
                toplam_hata += len(hatalar)
                for hata in hatalar[:25]:
                    print(f"   ❌ {hata}")
                if len(hatalar) > 25:
                    print(f"   … {len(hatalar) - 25} hata daha")
            else:
                print("   ✅ Sözleşme ihlali yok")

            if kampanyalar:
                atlananlar = atlanma_uyarilari(yol, kampanyalar)
                for uyari in atlananlar[:10]:
                    print(f"   ⚠  {uyari}")
                if len(atlananlar) > 10:
                    print(f"   … {len(atlananlar) - 10} satır daha")
                if atlananlar:
                    print(
                        "   ⚠  Boş hücre 'metinde YOK' demektir ve cevap anahtarına "
                        "öyle girer.\n      Bakmadan bıraktıysan '?' yaz — o hücre "
                        "metrik dışı kalır."
                    )

    if not bulunan:
        hedef = ad or "hiç kimse"
        print(f"❌ {hedef} için etiketleme dosyası bulunamadı. Önce `make altin-ornekle`.")
        return 1

    if toplam_hata:
        print(f"\n❌ Toplam {toplam_hata} ihlal — DÜZELTMEDEN PUSHLAMA.")
        print("   Kılavuz: docs/ETIKETLEME_KILAVUZU.md")
        return 1

    print("\n✅ Dosyalar sözleşmeye uygun. Pushlayabilirsin.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Altın set araçları (H-01)")
    alt = ap.add_subparsers(dest="komut", required=True)

    p_ornekle = alt.add_parser("ornekle", help="katmanlı örneklem + kişi başı CSV")
    p_ornekle.add_argument("--adet", type=int, default=60, help="örnek sayısı (varsayılan 60)")
    p_ornekle.add_argument(
        "--zorla", action="store_true", help="doldurulmuş sayfaların üstüne yaz"
    )

    p_gen = alt.add_parser("genislet", help="zayıf alanlar için EK örneklem (mevcut seti bozmaz)")
    p_gen.add_argument("--hedef-n", type=int, default=20, help="alan başına hedef dolu örnek")
    p_gen.add_argument("--uygula", action="store_true", help="planı uygula, CSV yaz")
    p_gen.set_defaults(islev="genislet")

    p_den = alt.add_parser("denetle", help="kendi CSV'ni pushlamadan önce kontrol et")
    p_den.add_argument("--ad", default=None, help="yalnız bu kişinin dosyaları")

    alt.add_parser("uyum", help="etiketleyiciler arası uyum oranı (H-02)")
    alt.add_parser("derle", help="CSV'leri altin_set.jsonl'e derle + denetle")

    args = ap.parse_args()
    if args.komut == "ornekle":
        return komut_ornekle(args.adet, args.zorla)
    if args.komut == "genislet":
        return komut_genislet(args.hedef_n, args.uygula)
    if args.komut == "denetle":
        return komut_denetle(args.ad)
    if args.komut == "uyum":
        return komut_uyum()
    return komut_derle()


if __name__ == "__main__":
    raise SystemExit(main())
