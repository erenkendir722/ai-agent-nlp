"""Altın set araçları — örneklem çıkar, etiketleri derle, seti denetle (H-01).

Altın set İNSAN işidir. Bu araç etiket üretmez; yalnız etiketlemenin etrafındaki
mekanik işi yapar:

    python tools/altin_set.py ornekle    # katmanlı örneklem -> kişi başı CSV
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
import json
import random
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.depolama import kampanyalari_oku  # noqa: E402
from src.preprocessing.normalizasyon import sayi_ayristir, tarih_ayristir  # noqa: E402
from src.schema import (  # noqa: E402
    ALAN_ADLARI,
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

CSV_UST_BILGI = ("kampanya_id", "banka_adi", "kaynak_url", "metin")
BOOL_ALANLAR = ("masrafsiz_mi",)
TARIH_ALANLAR = ("kampanya_bitis",)
METIN_KIRPMA = 15_000
"""Excel hücre sınırı 32.767 karakter. 96 kaydın yalnız 2'si bu eşiğin üstünde;
tam metin her hâlükârda `data/gold/metinler/` altına da yazılır."""

EMIN_DEGIL = "?"
"""Hücreye '?' yazan kişi o alanı atlamış olur — alan JSONL'e hiç girmez ve
metriğe katılmaz. Tahmin edilmiş etiket, eksik etiketten daha zararlıdır."""

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


def _csv_yaz(yol: Path, kampanyalar: list[Kampanya]) -> None:
    # utf-8-sig: Excel, BOM'suz UTF-8'i Türkçe karakterlerde bozuk gösteriyor
    with yol.open("w", encoding="utf-8-sig", newline="") as dosya:
        yazici = csv.writer(dosya)
        yazici.writerow([*CSV_UST_BILGI, *ALAN_ADLARI])
        for kampanya in kampanyalar:
            yazici.writerow(
                [
                    kampanya.kampanya_id,
                    kampanya.banka_adi,
                    kampanya.kaynak_url,
                    _kirp(kampanya.ham_metin),
                    *([""] * len(ALAN_ADLARI)),
                ]
            )


def calisma_sayfalari_yaz(
    secilen: list[Kampanya], kisiler: tuple[str, ...]
) -> tuple[list[Kampanya], dict[str, int]]:
    """Örneklemi uyum bloğu + kişisel paylara ayırır ve CSV'leri yazar.

    (uyum_blogu, kisi -> kişisel örnek sayısı) döner.
    """
    GOLD.mkdir(parents=True, exist_ok=True)
    METINLER.mkdir(parents=True, exist_ok=True)

    uyum_blogu = secilen[:UYUM_ADET]
    kisisel = secilen[UYUM_ADET:]

    paylar: dict[str, list[Kampanya]] = {kisi: [] for kisi in kisiler}
    for sira, kampanya in enumerate(kisisel):
        paylar[kisiler[sira % len(kisiler)]].append(kampanya)

    sayilar: dict[str, int] = {}
    for kisi, pay in paylar.items():
        _csv_yaz(GOLD / f"etiketleme_{kisi.lower()}.csv", pay)
        _csv_yaz(GOLD / f"etiketleme_uyum_{kisi.lower()}.csv", uyum_blogu)
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
    return uyum_blogu, sayilar


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
    kisiler: tuple[str, ...],
) -> dict[str, list[tuple[int, str, dict[str, Any], bool]]]:
    return {
        kisi: [s for s in _csv_oku(yol) if s[3]]
        for kisi in kisiler
        if (yol := GOLD / f"etiketleme_uyum_{kisi.lower()}.csv").exists()
    }


def uyum_hesapla(kisiler: tuple[str, ...] = KISILER) -> dict[str, Any]:
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
    dosyalar = uyum_dosyalari(kisiler)
    bos = {
        "kisi_sayisi": len(dosyalar),
        "ornek_sayisi": 0,
        "karsilastirilan": 0,
        "uyum": None,
        "ham_uyum": None,
        "alan_bazli": {},
        "ayrisma": [],
    }
    if len(dosyalar) < 2:
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
        if isinstance(oran, int | float) and not 0 < oran < 15:
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
    dolu = doldurulmus_sayfalar()
    if dolu and not zorla:
        print("❌ Yeniden örnekleme iptal edildi — doldurulmuş sayfaların üstüne yazardı:\n")
        for satir in dolu:
            print(f"   {satir}")
        print(
            "\n   Etiketlenmiş sayfalar saatlerce emek demektir; sessizce silinemez.\n"
            "   Gerçekten baştan başlamak istiyorsan: "
            "`python tools/altin_set.py ornekle --zorla`\n"
            "   Önce mevcut etiketleri `make altin-derle` ile kaydetmiş ol."
        )
        return 1

    kampanyalar = _kampanyalari_al()
    if adet > len(kampanyalar):
        print(f"⚠️  Sadece {len(kampanyalar)} kampanya var, örneklem buna düşürüldü.")
        adet = len(kampanyalar)

    secilen = katmanli_ornekle(kampanyalar, adet)
    uyum_blogu, sayilar = calisma_sayfalari_yaz(secilen, KISILER)

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
    print(f"   Örneklem kaydı: {ORNEK_KAYDI.relative_to(KOK)}")
    print("\n   Tür dağılımı:")
    for tur, sayi in Counter(_tur(k) for k in secilen).most_common():
        print(f"     {tur}: {sayi}")
    print("\n📖 Etiketlemeden önce docs/ETIKETLEME_KILAVUZU.md okunmalı.")
    print("   Sıra: uyum bloğu → `make altin-uyum` → tartış → kişisel pay")
    return 0


def komut_uyum() -> int:
    sonuc = uyum_hesapla()
    if sonuc["uyum"] is None:
        if sonuc["kisi_sayisi"] < 2:
            print("❌ Uyum dosyası bulunamadı. Önce `make altin-ornekle` çalıştırın.")
        else:
            print(f"❌ {sonuc['kisi_sayisi']} uyum dosyası var ama hiçbirinde etiket yok.")
            print("   Uyum oranı için en az iki kişinin aynı 10 örneği etiketlemesi gerekiyor.")
            print("   Dosyalar: data/gold/etiketleme_uyum_<ad>.csv")
        return 1

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

    print(f"\n✅ {ALTIN_SET.relative_to(KOK)} yazıldı — {len(kayitlar)} örnek\n")
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
        print(f"❌ {ALTIN_SET.relative_to(KOK)} yok. Önce `make altin-derle`.")
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Altın set araçları (H-01)")
    alt = ap.add_subparsers(dest="komut", required=True)

    p_ornekle = alt.add_parser("ornekle", help="katmanlı örneklem + kişi başı CSV")
    p_ornekle.add_argument("--adet", type=int, default=60, help="örnek sayısı (varsayılan 60)")
    p_ornekle.add_argument(
        "--zorla", action="store_true", help="doldurulmuş sayfaların üstüne yaz"
    )

    alt.add_parser("uyum", help="etiketleyiciler arası uyum oranı (H-02)")
    alt.add_parser("derle", help="CSV'leri altin_set.jsonl'e derle")
    alt.add_parser("dogrula", help="mevcut altın seti denetle")

    args = ap.parse_args()
    if args.komut == "ornekle":
        return komut_ornekle(args.adet, args.zorla)
    if args.komut == "uyum":
        return komut_uyum()
    if args.komut == "derle":
        return komut_derle()
    return komut_dogrula()


if __name__ == "__main__":
    raise SystemExit(main())
