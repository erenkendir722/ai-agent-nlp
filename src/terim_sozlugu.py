"""Terim sözlüğünü OKUNABİLİR veri hâline getirir (şartname 5.5).

`docs/TERIM_SOZLUGU.md` iki işi görüyordu: insan başvuru belgesi ve çıkarım
isteminin kaynağı (`extraction.llm.terimleri_yukle` istem bloğunu okur).
Üçüncü bir tüketicisi olmalıydı ve yoktu — CHATBOT.

27 Ağustos'ta ölçüldü:

    soru  : «Kâr payı nedir?»
    cevap : «Kuveyt Türk … — Alışveriş Puanı Kampanyası: aylık %1,99 …»

Kullanıcı bir TANIM sordu, rastgele bir kampanyanın alan dökümünü aldı.
Oysa tanım, kendi depomuzda 85 satırlık bir tabloda yazılı duruyordu.

Şartname 5.5'in istediği terminoloji hâkimiyeti tam olarak budur ve jüri
havuzunun 16. maddesi bunu doğrudan sınıyor: «En düşük faizli ihtiyaç kredisi
veren katılım bankası hangisi?» sorusunda beklenen davranış, önce «katılım
bankacılığında faiz yerine kâr payı, kredi yerine finansman kullanılır»
düzeltmesini yapmaktır.

BİÇİM BİR SÖZLEŞMEDİR. Tablo başlığı `tests/test_terim_sozlugu.py` tarafından
zaten korunuyor; bu modül aynı başlığa tutunur, ayrı bir ayrıştırma kuralı
icat etmez.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from src.preprocessing.normalizasyon import arama_anahtari

SOZLUK_YOLU = Path(__file__).resolve().parents[1] / "docs" / "TERIM_SOZLUGU.md"

TABLO_BASLIGI = "| Terim | Tanım | Sistemdeki karşılığı | İstem |"
"""Terim tablolarının değişmez başlığı — ayrıştırıcının tutunduğu yer.

Sözlükte başka tablolar da var («İfade | Sistem ne yapar», «Karışan | …»);
onlar terim tablosu DEĞİLDİR. Ayrım bu başlıkla yapılır — testteki ayrımın
aynısı, çünkü iki yerde iki kural zamanla ayrışır.
"""

_KALIN = re.compile(r"\*\*(.+?)\*\*")
_KOD = re.compile(r"`([^`]*)`")


@dataclass(frozen=True)
class Terim:
    """Sözlüğün bir satırı."""

    ad: str
    """Gösterilecek ad — sözlükteki yazımıyla, şapkalar yerinde."""

    adlar: tuple[str, ...]
    """Eşleştirme anahtarları. «Finansman tutarı / limiti» İKİ addır."""

    tanim: str
    karsilik: str
    """Sistemdeki karşılığı — alan adı, sabit ya da veto. Boşsa «—»."""


def _hucreler(satir: str) -> list[str]:
    return [h.strip() for h in satir.strip().strip("|").split("|")]


def _adlari_ayir(hucre: str) -> tuple[str, tuple[str, ...]]:
    """«**Finansman tutarı / limiti**» -> ad + iki eşleştirme anahtarı.

    Eğik çizgi sözlükte EŞ ANLAMLI yazımları ayırıyor («dosya masrafı / dosya
    parası»). Tek ad sayılırsa kullanıcının söylediği ikinci biçim hiç
    bulunmaz.
    """
    kalinlar = _KALIN.findall(hucre)
    ham = " ".join(kalinlar) if kalinlar else hucre
    ad = ham.strip()
    parcalar = [p.strip() for p in ad.split("/") if p.strip()]
    anahtarlar = tuple(dict.fromkeys(arama_anahtari(p) for p in parcalar))
    return ad, anahtarlar


RESMI_BOLUM = "## 1. Şartnamedeki beş resmî kavram"
"""Şartname 5.5'in beş kavramı TABLO DEĞİL, `### Başlık` + düzyazı biçiminde.

Ayrıştırıcı önce yalnız tabloları okuyordu ve tam da en çok sorulacak beş
kavramı kaçırıyordu:

    «Kâr payı nedir?» -> bulunamadı

Projenin merkez kavramı kendi sözlüğünde tanımsız görünüyordu; oysa tanımı
şartnameden birebir alınmış hâlde bu bölümde duruyor. İkinci bir biçim
uydurulmadı — dosyada zaten olan biçim okundu."""

_SEMA_SATIRI = "- **Şemadaki karşılığı:**"


def _resmi_kavramlar(metin: str) -> list[Terim]:
    """§1'deki `### Başlık` bloklarını terim satırına çevirir."""
    try:
        govde = metin.split(RESMI_BOLUM, 1)[1].split("\n## ", 1)[0]
    except IndexError:
        return []

    bulunan: list[Terim] = []
    baslik: str | None = None
    tanim: list[str] = []
    karsilik = ""

    def _kapat() -> None:
        if baslik and tanim:
            ad, adlar = _adlari_ayir(baslik)
            bulunan.append(
                Terim(ad=ad, adlar=adlar, tanim=" ".join(tanim).strip(),
                      karsilik=_KOD.sub(r"`\1`", karsilik).strip(" —")))

    for satir in govde.splitlines():
        duz = satir.strip()
        if duz.startswith("### "):
            _kapat()
            baslik, tanim, karsilik = duz[4:].strip(), [], ""
        elif duz.startswith(_SEMA_SATIRI):
            karsilik = duz[len(_SEMA_SATIRI):].strip()
        elif duz.startswith("-") or duz.startswith("#"):
            continue
        elif duz and baslik and not karsilik:
            tanim.append(duz)
    _kapat()
    return bulunan


@lru_cache(maxsize=1)
def terimler(yol: Path | None = None) -> tuple[Terim, ...]:
    """Sözlükteki bütün terim satırları. Dosya yoksa PATLAR.

    Sessizce boş liste dönmek, chatbot'un terminoloji yeteneğini hiç
    olmamış gibi göstermek olurdu — `terimleri_yukle` ile aynı refleks.
    """
    hedef = yol or SOZLUK_YOLU
    if not hedef.exists():
        raise FileNotFoundError(
            f"Terim sözlüğü bulunamadı: {hedef}. Chatbot'un tanım cevapları "
            "bu dosyadan besleniyor."
        )

    metin = hedef.read_text(encoding="utf-8")
    bulunan: list[Terim] = _resmi_kavramlar(metin)
    tabloda = False
    for satir in metin.splitlines():
        duz = satir.strip()
        if duz.startswith(TABLO_BASLIGI):
            tabloda = True
            continue
        if not duz.startswith("|"):
            tabloda = False
            continue
        if not tabloda or set(duz) <= set("|-: "):
            continue

        hucre = _hucreler(duz)
        if len(hucre) < 3:
            continue
        ad, adlar = _adlari_ayir(hucre[0])
        if not adlar:
            continue
        bulunan.append(
            Terim(
                ad=ad,
                adlar=adlar,
                tanim=hucre[1].strip(),
                karsilik=_KOD.sub(r"`\1`", hucre[2]).strip(),
            )
        )
    return tuple(bulunan)


TANIM_IPUCLARI = (
    "nedir", "ne demek", "ne anlama gel", "tanimi", "tanimla", "aciklar misin",
    "aciklayabilir misin", "ne demektir", "farki ne", "farki nedir",
    "arasindaki fark", "ne anlama geliyor",
)
"""«… nedir?» — bir TANIM isteniyor, bir kampanya değil."""


def tanim_sorusu_mu(soru: str) -> bool:
    return any(ipucu in arama_anahtari(soru) for ipucu in TANIM_IPUCLARI)


def _ozne(soru: str) -> str:
    """Sorunun tanım ipuçlarından arındırılmış gövdesi: «kâr payı nedir» -> «kar payi»."""
    anahtar = arama_anahtari(soru).replace("?", " ")
    for ipucu in TANIM_IPUCLARI:
        anahtar = anahtar.replace(ipucu, " ")
    for dolgu in (" bir ", " bu ", " ne ", " nasil "):
        anahtar = anahtar.replace(dolgu, " ")
    return " ".join(anahtar.split())


def terim_bul(soru: str) -> Terim | None:
    """Soruda geçen terimi bulur.

    İKİ AŞAMA — ölçülmüş sebeple:

    1. TAM GEÇİŞ, en uzun kazanır. Uzunluk kuralı şart: «kâr payı dağıtım
       oranı» sorulduğunda «kâr payı» da eşleşir ve kısa olanı seçmek iki
       kavramı karıştırmak demektir — sözlüğün §10'u bu ikisini «karışanlar»
       tablosunda ayrı ayrı uyarıyor.

    2. ÖN EK, en KISA kazanır. Sözlükteki ad tam biçimdir («Kâr Payı Oranı»),
       kullanıcı kısa söyler («kâr payı nedir?»). Tam geçiş aranınca terim hiç
       bulunmuyordu. Burada en kısası seçilir çünkü kısa olan daha GENEL
       olandır: «vade» sorulduğunda «Vade farksız» değil «Vade» istenir.
    """
    anahtar = arama_anahtari(soru)
    en_iyi: tuple[int, Terim] | None = None
    for terim in terimler():
        for ad in terim.adlar:
            if ad and ad in anahtar and (en_iyi is None or len(ad) > en_iyi[0]):
                en_iyi = (len(ad), terim)
    if en_iyi is not None:
        return en_iyi[1]

    ozne = _ozne(soru)
    if not ozne:
        return None

    # «Kâr payı ile faiz arasındaki fark ne?» — özne İKİ kavram taşıyor.
    # Her parça ayrı denenir; ilk bulunan cevaplar, çünkü sözlükteki tanım
    # zaten ayrımı yazıyor («faiz yerine kullanılan…»).
    adaylar = [ozne]
    for ayirac in (" ile ", " ve ", " veya "):
        adaylar.extend(p.strip() for p in ozne.split(ayirac) if p.strip())

    en_kisa: tuple[int, Terim] | None = None
    for parca in adaylar:
        for terim in terimler():
            for ad in terim.adlar:
                if ad.startswith(f"{parca} ") and (
                    en_kisa is None or len(ad) < en_kisa[0]
                ):
                    en_kisa = (len(ad), terim)
        if en_kisa is not None:
            return en_kisa[1]
    return None


__all__ = [
    "SOZLUK_YOLU",
    "TANIM_IPUCLARI",
    "Terim",
    "tanim_sorusu_mu",
    "terim_bul",
    "terimler",
]
