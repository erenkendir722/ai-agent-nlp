"""Kampanya KONUSU — kullanıcı kampanyayı kimliğiyle değil, konusuyla anar.

    soru  : «TOM Katılım'ın AKARYAKIT kampanyasında ne kadar iade var?»
    cevap : «… — Hadi Kredi Kartı: Ödül miktarı: 250 TL»
    kaynak: …/a101lerde-meyve-sebze-alisverislerinde-10-nakit-iade

28 Ağustos'ta ölçüldü. Soruda dört şey vardı — banka, konu, ölçüt, nicelik —
ve sistem yalnız bankayı gördü. `_bankalari_bul` 123 TOM kaydını getirdi,
`sorulan_urun` «akaryakıt» diye bir ürün sınıfı tanımadığı için küme hiç
daralmadı, kararı `doluluk_orani` verdi: soruyla ilgisiz bir ölçü. Cevaptaki
her sayı doğruydu — YANLIŞ KAMPANYANIN sayılarıydı. Kalkan bunu göremez;
o «bu sayı kayıtta var mı?» diye sorar, «bu kayıt, sorulan şey mi?» diye
sormaz — `yabanci_banka_soruluyor`'un banka için kapattığı boşluğun
kampanya için açık kalanı.

BU MODÜL BİR SÖZLÜK TUTMAZ. «akaryakıt», «restoran», «market» diye bir
liste yazmak, korpus her tazelendiğinde geride kalacak bir liste yazmaktı.
Konu dağarcığı kampanyaların KENDİ ADLARINDAN doğar ve ayırt edicilik
korpusun kendisinden ölçülür.

ÜÇ KARAR, ÜÇÜ DE ÖLÇÜLDÜ:

1. KAMPANYANIN ADI ADRESİNİN SON DİLİMİDİR (`konu_metni`).
   Aday üç metin vardı. `ham_metin` elenir: bir sayfa başka kampanyalardan
   da söz eder — TOM'un 123 kaydının 10'unda «akaryakıt» gövdede geçiyor,
   oysa gerçekten akaryakıt kampanyası olan 3'ü. `kampanya_avantaji` de
   elenir: LLM'in özetidir ve pazarlama düzyazısı taşır; aynı ölçümde
   «güncel» 4 kayda, «belirli» 24, «olarak» 13, «sunan» 4 kayda eşleşiyordu
   — hepsi soru dili. Adres diliminde üçü de SIFIR. Geriye kampanyanın
   bankaca verilmiş adı kalır; kimlik iddiası için doğru olan da odur.
   Yol ÖNEKİ değil son dilimi alınır: önek site gezinmesidir
   («/kendim-icin/kart-kampanyalari/») ve «için» tek başına 232 kayda
   eşleşiyordu.

2. AYIRT EDİCİLİK KORPUSTAN ÖLÇÜLÜR (`KONU_TAVANI`).
   Bir sözcük kampanya adlarının büyük bölümünde geçiyorsa bir kampanyayı
   ADLANDIRMAZ, hepsini niteler. Ölçülen sınır (979 kayıt):

       varan 114 · fırsatı 103 · özel 77 · harcama 72 · toplam 37 · iade 37
       ————————————————— %3 = 29 kayıt —————————————————
       harcamalarınıza 29 · ticari 28 · troy 25 · mobil 25 · worldpuan 20
       akaryakıt 16 · sağlık 15 · a101 14 · market 12 · restoran 12 · pegasus 4

   Sınırın üstü pazarlama kalıbı, altı konu adı. Eşik bir tercih değil,
   bu ayrımın ölçülen yeri.

3. SÜZGEÇ BİRLEŞİMDİR, KESİŞİM DEĞİL (`konu_suz`).
   «Yalnız belirli sektörlerdeki (ör. akaryakıt, market, beyaz eşya)
   harcamalara…» sorusunda en çok sözcüğü tutan kayda daralmak 444 kaydı
   2'ye indiriyordu; kullanıcı üç konuyu SAYIYOR, hepsini birden taşıyan
   tek kampanyayı sormuyor. Konu sözcüklerinden BİRİNİ taşıyan kayıt
   kümede kalır; kaçını taşıdığı SIRAYI belirler (`konu_sirasi`).

Kapı, `_urun_filtrele` ve `_segment_filtrele` ile aynı refleksle çalışır:
eşleşen kayıt yoksa küme daralmaz — konu adlandırılmamış ya da korpusta
karşılığı yok demektir, ikisinde de eski davranış doğrudur.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Iterable
from typing import Protocol

from src.preprocessing.normalizasyon import arama_anahtari

ORTAK_KOK_UZUNLUGU = 5
"""İki sözcüğün aynı kökten sayılması için gereken ortak ön ek uzunluğu.

Türkçe SONDAN eklemeli: kök her zaman öndedir, ek arkada birikir. Bu yüzden
kök yaklaşıklaması ortak ön ektir — ve iki yönlü olmak zorunda, çünkü ek
soruda da olabilir kampanya adında da:

    harcamasına ~ harcamalarında   ortak «harcama» (7)   ← aynı kök
    akaryakıtta ~ akaryakıt        ortak «akaryakit» (9) ← aynı kök
    market      ~ marka            ortak «mar» (3)       ← DEĞİL

`terim_gecer` tek yönlüdür (soruda arar, sonunu serbest bırakır) ve bu iş
için yetmez: kampanya adı «harcamasına» yazarken kullanıcı «harcamalarında»
yazıyor; hiçbiri diğerinin ön eki değil.
"""

ASGARI_KONU_UZUNLUGU = 4
"""Konu sözcüğü en az dört harf. `ASGARI_SIFAT_FIIL_UZUNLUGU` ile aynı sebep.

Üç harfli sözcük ortak kök kuralını sulandırıyor: «var» ~ «varan» ortak üç
harf ve kural onları aynı kökten sayardı — «… veriyor mu?» sorusundaki
«var», adında «varan» geçen 114 kampanyaya eşleşirdi. Konu adları
(«a101», «troy», «kasko») dört harften kısa olmuyor.
"""

KONU_TAVANI = 0.03
"""Bir konu sözcüğü korpusun en fazla yüzde kaçında geçebilir — ölçüldü (§2).

Üstünde kalan sözcük kampanyayı adlandırmaz, kampanyacılığı anlatır
(«varan», «fırsatı», «özel», «harcama»). Oran mutlak sayı değil, korpusla
birlikte büyüsün diye kesir: yeni kampanyalar eklendiğinde «özel»in payı
değişmez, sayısı değişir.
"""


class KonuluKayit(Protocol):
    """`konu_metni`'nin ihtiyacı — `KampanyaKaydi` de `Kampanya` da karşılar.

    İki tip de aynı üç alanı taşıyor ama farklı biçimde (`Kampanya.urun_turu`
    bir `Alan`, `KampanyaKaydi.urun_turu` düz sütun). Protokol düz olanı
    tanımlar; `Kampanya` için çağıran `.deger`'i çözer.
    """

    kampanya_id: str
    kaynak_url: str


_AYIRAC = re.compile(r"[^0-9a-z]+")
"""Konu metnini sözcüklere ayırır. `arama_anahtari` çıktısı ASCII'ye
indirgenmiş olduğu için harf sınıfı bu kadar dar tutulabiliyor."""


def ayni_kok(bir: str, iki: str) -> bool:
    """İki sözcük aynı kökten mi? Gerekçe `ORTAK_KOK_UZUNLUGU`'nda.

    >>> ayni_kok("akaryakitta", "akaryakit")
    True
    >>> ayni_kok("harcamasina", "harcamalarinda")
    True
    >>> ayni_kok("market", "marka")
    False
    """
    ortak = 0
    for bir_harf, iki_harf in zip(bir, iki, strict=False):
        if bir_harf != iki_harf:
            break
        ortak += 1
    if ortak >= ORTAK_KOK_UZUNLUGU:
        return True
    # Kısa sözcük diğerinin TAMAMEN ön eki olmalı: «kart» ~ «kartlar» evet,
    # «kar» ~ «kart» hayır — üç harf kök saymaya yetmiyor (bkz. ASGARI).
    return ortak >= ASGARI_KONU_UZUNLUGU and ortak in (len(bir), len(iki))


def _adres_dilimi(url: str) -> str:
    """Adresin SON yol dilimi — kampanyanın bankaca verilmiş adı.

    >>> _adres_dilimi("https://x.test/kampanyalar/akaryakit-harcamalarina-500-tl-iade")
    'akaryakit harcamalarina 500 tl iade'
    """
    govde = url.split("://", 1)[-1].split("?", 1)[0].rstrip("/")
    dilimler = govde.split("/")[1:]
    return re.sub(r"[-_.]", " ", dilimler[-1]) if dilimler else ""


def konu_metni(kayit: object) -> str:
    """Kaydın KONU metni: adres dilimi + ürün türü. Gerekçe modül başlığında.

    `urun_turu` iki tipte iki biçimde duruyor (`Alan` ya da düz sütun);
    ikisi de çözülür, çünkü profil kolu `Kampanya` ile çalışıyor.
    """
    urun = getattr(kayit, "urun_turu", None)
    urun_adi = getattr(urun, "deger", urun) or ""
    return arama_anahtari(f"{_adres_dilimi(getattr(kayit, 'kaynak_url', ''))} {urun_adi}")


def sozcuklere_ayir(metin: str) -> list[str]:
    """Konu sözcükleri — kısa ve yalnız rakamdan ibaret olanlar atılır.

    Sorunun ve kampanya adının TEK ayırıcısı burasıdır: iki taraf farklı
    ayrıştırılırsa eşleşme sessizce kayar.

    «500», «2026» bir konu adlandırmaz; «a101» adlandırır — ölçüt «rakam
    içermemek» değil, «yalnız rakamdan ibaret olmamak».
    """
    return [
        s
        for s in _AYIRAC.split(metin)
        if len(s) >= ASGARI_KONU_UZUNLUGU and not s.isdigit()
    ]


def gosterim_bicimi(sozcuk: str, ham_metin: str) -> str:
    """Normalize edilmiş sözcüğün METİNDEKİ yazımı — şapkalar yerinde.

    Eşleştirme ASCII'ye indirgenmiş anahtarla yapılır, ekrana yazılan ad ham
    biçimiyle kalmalı: `segment_dagarcigi` aynı ayrımı yapıyor ve gerekçesi
    orada yazılı — anahtarı göstermek «çiftçi»yi «ciftci» diye yazdırıyordu.

    >>> gosterim_bicimi("akaryakit", "TOM'un akaryakıt kampanyası")
    'akaryakıt'
    """
    for ham in re.split(r"[^0-9A-Za-zÇĞİÖŞÜçğıöşü]+", ham_metin):
        if ham and arama_anahtari(ham) == sozcuk:
            return ham
    return sozcuk


def kayit_sozcukleri(kayit: object) -> frozenset[str]:
    """Kaydın konu sözcükleri."""
    return frozenset(sozcuklere_ayir(konu_metni(kayit)))


def konu_dagarcigi(korpus: Iterable[object]) -> dict[str, set[str]]:
    """Konu sözcüğü -> o sözcüğü adında taşıyan kampanya kimlikleri."""
    dagarcik: dict[str, set[str]] = defaultdict(set)
    for kayit in korpus:
        kimlik = getattr(kayit, "kampanya_id", "")
        for sozcuk in kayit_sozcukleri(kayit):
            dagarcik[sozcuk].add(kimlik)
    return dagarcik


def konu_tavani(korpus_buyuklugu: int) -> int:
    """Bir konu sözcüğünün eşleşebileceği azami kampanya sayısı.

    En az 1: küçük kümelerde (sınama korpusları) kesir sıfırın altına inip
    her sözcüğü eleyecekti.
    """
    return max(1, int(korpus_buyuklugu * KONU_TAVANI))


def eslesen_kampanyalar(sozcuk: str, dagarcik: dict[str, set[str]]) -> set[str]:
    """Sözcükle AYNI KÖKTEN bir ad taşıyan kampanyalar.

    Tek kaynak: hem ağırlık hesabı hem `eval/soru_taramasi.py` buradan
    sorar. İki yerde iki ölçü, taramanın chatbot'un GÖRMEDİĞİ bir sözcükle
    soru üretmesi demekti — bulunan kusur chatbot'un değil taramanın
    kendi tutarsızlığı olurdu.
    """
    eslesen: set[str] = set()
    for aday, kimlikler in dagarcik.items():
        if ayni_kok(sozcuk, aday):
            eslesen |= kimlikler
    return eslesen


def _konu_eslesmeleri(
    sozcukler: Iterable[str], korpus: list[object]
) -> list[tuple[str, set[str]]]:
    """GEÇERLİ konu sözcükleri ve eşleştikleri kampanyalar.

    Geçerli olmak iki şart: korpusta karşılığı olacak ve `KONU_TAVANI`'nı
    aşmayacak. Ağırlık hesabı da sohbet bağlamı da buradan okur — bağlam,
    çözülmemiş bir sözcüğü sonraki tura devretmemeli (`SohbetBaglami`
    ÇÖZÜLMÜŞ yuvaları taşır, kullanıcının yazdığı ham metni değil).
    """
    dagarcik = konu_dagarcigi(korpus)
    tavan = konu_tavani(len(korpus))
    eslesmeler: list[tuple[str, set[str]]] = []
    for sozcuk in sozcukler:
        eslesen = eslesen_kampanyalar(sozcuk, dagarcik)
        if eslesen and len(eslesen) <= tavan:
            eslesmeler.append((sozcuk, eslesen))
    return eslesmeler


def gecerli_konu_sozcukleri(
    sozcukler: Iterable[str], korpus: list[object]
) -> tuple[str, ...]:
    """Korpusta gerçekten bir kampanyayı adlandıran sözcükler."""
    if not korpus:
        return ()
    return tuple(sozcuk for sozcuk, _ in _konu_eslesmeleri(sozcukler, korpus))


def konu_agirliklari(
    sozcukler: Iterable[str], korpus: list[object]
) -> dict[str, float]:
    """Kampanya kimliği -> konu alakası. Ağırlık NADİRLİKTEN gelir.

    Bir konu sözcüğünün ağırlığı `ln(N / eşleşen)`: az kampanyada geçen
    sözcük çok şey söyler, çoğunda geçen az. Böylece soru birden çok sözcük
    taşıdığında hangisinin baskın olduğu elle sıralanmaz — «kentsel» (2
    kayıt) «dönüşüm»den (7 kayıt) kendiliğinden ağır basar.

    `KONU_TAVANI`'nı aşan sözcük hiç sayılmaz (bkz. sabitin gerekçesi).
    """
    if not korpus:
        return {}
    agirlik: dict[str, float] = defaultdict(float)
    for _, eslesen in _konu_eslesmeleri(sozcukler, korpus):
        puan = math.log(len(korpus) / len(eslesen))
        for kimlik in eslesen:
            agirlik[kimlik] += puan
    return dict(agirlik)


def konu_sirasi(kayit: object, agirliklar: dict[str, float]) -> float:
    """Kaydın konu alakası — sıralama anahtarı olarak kullanılır."""
    return agirliklar.get(getattr(kayit, "kampanya_id", ""), 0.0)


def konu_suz(agirliklar: dict[str, float], adaylar: list) -> list:
    """Konusu SORULANA uyan kayıtlar; hiçbiri uymuyorsa boş liste.

    Boş dönmek «daraltma yok» demektir ve çağıran `or` ile eski kümeye
    döner — `_segment_filtrele` ile aynı sözleşme. Kesişim değil birleşim
    olduğu gerekçesi modül başlığında (§3).
    """
    if not agirliklar:
        return []
    return [k for k in adaylar if konu_sirasi(k, agirliklar) > 0.0]


__all__ = [
    "ASGARI_KONU_UZUNLUGU",
    "KONU_TAVANI",
    "ORTAK_KOK_UZUNLUGU",
    "ayni_kok",
    "eslesen_kampanyalar",
    "gecerli_konu_sozcukleri",
    "gosterim_bicimi",
    "kayit_sozcukleri",
    "konu_agirliklari",
    "konu_dagarcigi",
    "konu_metni",
    "konu_sirasi",
    "konu_suz",
    "konu_tavani",
    "sozcuklere_ayir",
]
