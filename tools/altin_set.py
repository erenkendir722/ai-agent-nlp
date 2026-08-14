"""Altın set araçları — örneklem çıkar, etiketleri derle, seti denetle (H-01).

Altın set İNSAN işidir. Bu araç etiket üretmez; yalnız etiketlemenin etrafındaki
mekanik işi yapar:

    python tools/altin_set.py ornekle    # katmanlı örneklem -> kişi başı CSV
    python tools/altin_set.py denetle    # KENDİ dosyanı pushlamadan önce kontrol
    python tools/altin_set.py derle      # doldurulmuş CSV'ler -> altin_set.jsonl
    python tools/altin_set.py dogrula    # üretilen seti denetle

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
    METINSEL_ALANLAR,
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
KALIBRASYON_ONEK = "kalibrasyon_"
KALIBRASYON_KAYDI = GOLD / "kalibrasyon_listesi.json"
"""Kalibrasyon bloğu — uyum oranını ölçmek için AYRI bir örnek kümesi.

Neden ayrı: uyum bloğunun ilk turu kirlendi (tamamlanmış bir dosya depoya
girip kopyalandı). O 10 örneğin etiketleri altın set için hâlâ geçerli —
sahibinin kendi işi — ama uyum ölçümü için kullanılamaz, çünkü iki kişi de
aynı cevapları görmüş durumda; tekrar ölçmek uyumu değil hafızayı ölçer.

Kalibrasyon bloğu, 60'lık altın set örnekleminin DIŞINDAN çekilir. Böylece
altın sete dokunulmaz ve kimsenin görmediği örnekler üzerinde gerçek bir
uyum oranı elde edilir."""

UYUM_ADET = 10
"""Örneklemin ilk 10'unu DÖRDÜ BİRDEN etiketler (H-02).

İki işi birden görür: etiketleyiciler arası uyum oranını ölçer (sunumda
«etiketleme uzlaşmamız %X» cümlesi buradan çıkar) ve bu 10 örnek çoğunluk
oyuyla uzlaştırılıp altın sete girer. Kalan örnekler tek etiketleyicilidir —
dört kişinin her örneği ayrı ayrı etiketlemesi 4 kat maliyet demekti."""


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


def _kirp(metin: str) -> str:
    if len(metin) <= METIN_KIRPMA:
        return metin
    return (
        metin[:METIN_KIRPMA]
        + f"\n\n[... {len(metin) - METIN_KIRPMA} karakter kırpıldı —"
        " tam metin: data/gold/metinler/<kampanya_id>.txt ...]"
    )


def csv_basliklari() -> list[str]:
    return [*CSV_UST_BILGI, *ALAN_ADLARI, *CSV_SON_BILGI]


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
                    *([""] * len(ALAN_ADLARI)),
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


def _csv_oku(yol: Path) -> list[tuple[int, str, dict[str, Any], bool]]:
    """(satir_no, kampanya_id, {alan: deger}, dokunuldu_mu)."""
    cikti: list[tuple[int, str, dict[str, Any], bool]] = []
    with yol.open(encoding="utf-8-sig", newline="") as dosya:
        for satir_no, satir in enumerate(csv.DictReader(dosya), start=2):
            kimlik = (satir.get("kampanya_id") or "").strip()
            dokunuldu = bool((satir.get(DOKUNMA_ALANI) or "").strip())
            etiketler: dict[str, Any] = {}
            for alan in ALAN_ADLARI:
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


def aktif_uyum_kaynagi(kisiler: tuple[str, ...] = KISILER) -> tuple[str, str]:
    """Uyum hangi blok üzerinden ölçülecek?

    Kalibrasyon bloğunda etiket varsa o kullanılır — ilk uyum bloğu kirlendiği
    için oradan çıkan oran geçerli değil.
    """
    if any(s for s in uyum_dosyalari(kisiler, KALIBRASYON_ONEK).values()):
        return KALIBRASYON_ONEK, "kalibrasyon bloğu"
    return UYUM_ONEK, "uyum bloğu"


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


KOPYA_ESIGI = 0.90
KOPYA_ASGARI_ORNEK = 5


def kopya_suphesi(kisiler: tuple[str, ...] = KISILER, onek: str = UYUM_ONEK) -> list[str]:
    """İki etiketleyicinin serbest metin alanları fazla mı benziyor?

    Uyum oranı ancak etiketleme BAĞIMSIZ yapıldıysa anlam taşır. Serbest metin
    alanları bunun turnusol kâğıdıdır: iki kişi bir kampanyayı kendi cümleleriyle
    özetlediğinde sonuç asla harfi harfine aynı olmaz. %90'ın üstünde birebir
    eşleşme, uyumun değil kopyanın işaretidir.

    12 Ağustos'ta tam olarak bu yaşandı: tamamlanmış bir uyum dosyası diğerleri
    etiketlemeden önce depoya pushlandı ve cevap anahtarı herkesin eline geçti.
    Ölçülen %98, gerçekte iki dosyanın aynı olmasıydı.
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
                diger = tablolar[sag].get(kimlik, {})
                for alan in METINSEL_ALANLAR:
                    a, b = alanlar.get(alan), diger.get(alan)
                    if isinstance(a, str) and isinstance(b, str) and a.strip() and b.strip():
                        toplam += 1
                        ayni += a.strip() == b.strip()
            if toplam >= KOPYA_ASGARI_ORNEK and ayni / toplam >= KOPYA_ESIGI:
                uyarilar.append(
                    f"{sol} ↔ {sag}: {ayni}/{toplam} serbest metin alanı BİREBİR aynı "
                    f"(%{ayni / toplam * 100:.0f}) — bağımsız etiketlemede beklenmez"
                )
    return uyarilar


def uyum_uzlasisi(kisiler: tuple[str, ...] = KISILER) -> tuple[list[dict[str, Any]], list[str]]:
    """Uyum bloğunu çoğunluk oyuyla tek kayda indirger.

    Çoğunluk yoksa (2-2 bölünme gibi) o alan YAZILMAZ. Bölünmüş bir alanı
    rastgele bir tarafa yazmak, cevap anahtarına yazı-tura sokmak olurdu.
    """
    dosyalar = uyum_dosyalari(kisiler)
    if not dosyalar:
        return [], []

    tablo: dict[str, dict[str, list[Any]]] = defaultdict(lambda: defaultdict(list))
    for satirlar in dosyalar.values():
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
        yol = GOLD / f"etiketleme_{kisi.lower()}.csv"
        if not yol.exists():
            uyarilar.append(f"{yol.name} yok — {kisi} henüz başlamamış olabilir")
            continue

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
        if isinstance(oran, int | float) and not 0 < oran < AYLIK_KAR_PAYI_UST_SINIRI:
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
    print(f"\n   Kişi başı toplam yük: ~{toplam_kisi} örnek")
    print(f"   Tam metinler: data/gold/metinler/ ({len(secilen)} dosya)")
    print(f"   Örneklem kaydı: {_kisa_yol(ORNEK_KAYDI)}")
    print("\n   Tür dağılımı:")
    for tur, sayi in Counter(_tur(k) for k in secilen).most_common():
        print(f"     {tur}: {sayi}")
    print("\n📖 Etiketlemeden önce docs/ETIKETLEME_KILAVUZU.md okunmalı.")
    print("   Sıra: uyum bloğu → `make altin-uyum` → tartış → kişisel pay")
    return 0


def altin_set_orneklemi() -> set[str]:
    """60'lık altın set örnekleminin kimlikleri (uyum bloğu + kişisel paylar)."""
    if not ORNEK_KAYDI.exists():
        return set()
    kayit = json.loads(ORNEK_KAYDI.read_text(encoding="utf-8"))
    kimlikler = set(kayit.get("uyum_blogu", []))
    for pay in kayit.get("atama", {}).values():
        kimlikler.update(pay)
    return kimlikler


def komut_kalibrasyon(adet: int, zorla: bool = False) -> int:
    """Uyum ölçümü için, altın set örnekleminin DIŞINDAN taze blok."""
    kampanyalar = _kampanyalari_al()
    kullanilmis = altin_set_orneklemi()
    disarida = [k for k in kampanyalar if k.kampanya_id not in kullanilmis]

    if len(disarida) < adet:
        print(f"❌ Örneklem dışında yalnız {len(disarida)} kampanya var, {adet} istendi.")
        return 1

    dolu = [
        f"{KALIBRASYON_ONEK}{k.lower()}.csv"
        for k in KISILER
        if _etiketli_mi(GOLD / f"{KALIBRASYON_ONEK}{k.lower()}.csv")
    ]
    if dolu and not zorla:
        print("❌ Doldurulmuş kalibrasyon dosyaları var, üstlerine yazılmadı:")
        for ad in dolu:
            print(f"   {ad}")
        print("   Sıfırlamak için: python tools/altin_set.py kalibrasyon --zorla")
        return 1

    # Tohum farklı: aynı tohum, aynı sıralamayla örtüşen blok üretirdi.
    blok = katmanli_ornekle(disarida, adet, tohum=TOHUM + 1)
    GOLD.mkdir(parents=True, exist_ok=True)
    METINLER.mkdir(parents=True, exist_ok=True)

    for kisi in KISILER:
        _csv_yaz(GOLD / f"{KALIBRASYON_ONEK}{kisi.lower()}.csv", blok)
    for kampanya in blok:
        (METINLER / f"{kampanya.kampanya_id}.txt").write_text(
            kampanya.ham_metin, encoding="utf-8"
        )

    KALIBRASYON_KAYDI.write_text(
        json.dumps(
            {
                "olusturma": datetime.now().isoformat(timespec="seconds"),
                "tohum": TOHUM + 1,
                "amac": "etiketleyiciler arası uyum ölçümü (H-02)",
                "not": "Altın set örnekleminin dışından seçildi; altın sete girmez.",
                "kampanyalar": [k.kampanya_id for k in blok],
                "dagilim_tur": dict(Counter(_tur(k) for k in blok)),
                "dagilim_banka": dict(Counter(k.banka_adi for k in blok)),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"✅ Kalibrasyon bloğu: {len(blok)} örnek (altın set örnekleminin dışından)\n")
    for kisi in KISILER:
        print(f"   data/gold/{KALIBRASYON_ONEK}{kisi.lower()}.csv")
    print("\n   Tür dağılımı:")
    for tur, sayi in Counter(_tur(k) for k in blok).most_common():
        print(f"     {tur}: {sayi}")
    print(
        "\n🔒 MÜHÜRLÜ ÇALIŞIN — dolu dosyayı PUSHLAMAYIN.\n"
        "   Herkes kendi dosyasını doldurup doğrudan kaptana gönderir;\n"
        "   kaptan dördünü birden koyar, sonra `make altin-uyum` çalışır.\n"
        "   Aksi hâlde depoyu çeken kişi cevapları görür ve oran anlamsızlaşır."
    )
    return 0


def komut_uyum() -> int:
    onek, aciklama = aktif_uyum_kaynagi()
    print(f"\n  Kaynak: {aciklama} ({onek}<ad>.csv)")
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
    print("   kararı docs/ETIKETLEME_KILAVUZU.md bölüm 6'ya yazın.")
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


def komut_dogrula() -> int:
    if not ALTIN_SET.exists():
        print(f"❌ {_kisa_yol(ALTIN_SET)} yok. Önce `make altin-derle`.")
        return 1

    kayitlar = [
        json.loads(s) for s in ALTIN_SET.read_text(encoding="utf-8").splitlines() if s.strip()
    ]
    kampanyalar = _kampanyalari_al()
    hatalar = denetle(kayitlar, kampanyalar)
    kanit = kanit_uyarilari(kayitlar, kampanyalar)

    print(kapsam_raporu(kayitlar, kampanyalar))
    if kanit:
        print(f"\n🔎 {len(kanit)} değer ham metinde bulunamadı — gözden geçirin:")
        for satir in kanit:
            print(f"   {satir}")
    if hatalar:
        print(f"\n❌ {len(hatalar)} hata:")
        for hata in hatalar:
            print(f"   {hata}")
        return 1
    print("\n✅ Altın set tutarlı." + ("  (yukarıdaki kanıt uyarılarına bakın)" if kanit else ""))
    return 0


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
"""Metriği taşıyan sekiz alan — etiketleme önceliği bunlardır.

Kalan alanlar bilinçli olarak ikinci sırada: `urun_turu` (%0 doluluk),
`alisveris_puani` ve `masraf_bilgisi` (%1), `hedef_kitle` (%4) ölçümde neredeyse
hiç örnek üretmiyor; serbest metin alanları ise etiketleyiciler arası uyumun en
düşük olduğu yer. Sekiz alanı çok örnekte etiketlemek, on altı alanı az örnekte
etiketlemekten hem ucuz hem istatistiksel olarak daha sağlamdır."""

_TUR_ESANLAMLI: dict[str, str] = {
    # docs/ETIKETLEME_KILAVUZU.md §4.1 karar sırasında AÇIKÇA yazanlar
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
        for satir_no, satir in enumerate(csv.DictReader(dosya), start=2):
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

            for alan in ALAN_ADLARI:
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
                    elif alan == "kar_payi_orani" and not 0 < sayi < AYLIK_KAR_PAYI_UST_SINIRI:
                        hatalar.append(
                            f"{yer}  kar_payi_orani=%{sayi} — AYLIK oran bekleniyor, şüpheli"
                        )
                    elif alan == "vade_ay_max" and not 0 < sayi <= 360:
                        hatalar.append(f"{yer}  vade_ay_max={sayi} ay — şüpheli")

    return hatalar, etiketlenen, toplam


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


def komut_denetle(ad: str | None) -> int:
    """Kişi CSV'sini pushlamadan önce denetler — H-01'in kalite kapısı."""
    kisiler = (ad,) if ad else KISILER
    onekler = ("etiketleme_", UYUM_ONEK, KALIBRASYON_ONEK)

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

    p_kal = alt.add_parser("kalibrasyon", help="uyum ölçümü için taze blok (H-02)")
    p_kal.add_argument("--adet", type=int, default=10, help="örnek sayısı (varsayılan 10)")
    p_kal.add_argument("--zorla", action="store_true", help="dolu kalibrasyon dosyalarını sıfırla")

    p_den = alt.add_parser("denetle", help="kendi CSV'ni pushlamadan önce kontrol et")
    p_den.add_argument("--ad", default=None, help="yalnız bu kişinin dosyaları")

    alt.add_parser("uyum", help="etiketleyiciler arası uyum oranı (H-02)")
    alt.add_parser("derle", help="CSV'leri altin_set.jsonl'e derle")
    alt.add_parser("dogrula", help="mevcut altın seti denetle")

    args = ap.parse_args()
    if args.komut == "ornekle":
        return komut_ornekle(args.adet, args.zorla)
    if args.komut == "kalibrasyon":
        return komut_kalibrasyon(args.adet, args.zorla)
    if args.komut == "denetle":
        return komut_denetle(args.ad)
    if args.komut == "uyum":
        return komut_uyum()
    if args.komut == "derle":
        return komut_derle()
    return komut_dogrula()


if __name__ == "__main__":
    raise SystemExit(main())
