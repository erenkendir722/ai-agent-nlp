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
    "nedir", "ne demek", "ne demektir", "ne anlama gel",
    "aciklar misin", "aciklayabilir misin",
    "farki ne", "farki nedir", "arasindaki fark",
)
"""«… nedir?» — bir TANIM isteniyor, bir kampanya değil.

YALNIZ SORU BİÇİMLERİ. «tanımı», «tanımla» ipucu olarak denendi ve
BIRAKILDI: alt dize olarak «özel TANIMLAnmış kampanyalar nelerdir?»
içinde bulunuyor ve o soruyu — bir kampanya listesi sorusunu — sözlük
tanımına düşürüyordu (27 Ağustos, jüri havuzu 21. madde). «Tanımı nedir?»
zaten «nedir» ile yakalanıyor; ikinci ipucu kazanç getirmeden yanlış
pozitif üretiyordu."""


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


# ---------------------------------------------------------------------------
# Ölçüt eşlemesi — sözlük ŞEMAYA bağlıyor, biz de ondan okuyoruz
# ---------------------------------------------------------------------------

VETO_ISARETLERI = ("degil", "karistirilmaz", "veto", "sizmasin", "aranmaz")
"""Sözlüğün «Sistemdeki karşılığı» sütununda BEYAN EDİLMİŞ olumsuzlamalar.

Sütun her zaman bir kimlik kurmuyor; bazen tam tersini söylüyor:

    | **Riba** | … | Kavramsal — `kar_payi_orani` faiz DEĞİLDİR |
    | **Kâr payı dağıtım oranı** | … | `kar_payi_orani` ile KARIŞTIRILMAZ |
    | **Erken ödeme tazminatı** | … | `kar_payi_orani` VETOSU |

Alan adını körü körüne okuyan bir eşleme, sözlüğün AYIRDIĞI iki kavramı
birleştirirdi — üstelik sözlüğün §10'u bu ikisini «karışanlar» tablosunda
ayrıca uyarıyor. İşaretler dosyanın kendi diliyle yazılmış; yeni bir veto
eklenirse aynı sözcüklerle yazılacaktır."""

HESAPLANAN_ISARETI = "hesaplan"
"""«tek alan değil, **hesaplanır**» — ölçüt bir sütun değil, bir FORMÜLDÜR.

`Finansman Maliyeti` böyle: `toplam_maliyet()` anapara ve vade ister. Bu
ölçüt sorulduğunda bir sütun sıralanamaz; eksik girdi SORULUR."""

_KOD_ADI = re.compile(r"`([^`]+)`")


def _ilk_beyan(karsilik: str) -> str:
    """Karşılık sütununun İLK cümleciği — kimliği o kurar.

    Sütun sık sık noktalı virgülle ayrılmış birden çok beyan taşıyor ve
    ikisi farklı şeyler söylüyor:

        | **Nakit iade** | … | `odul_miktari`; `kar_payi_orani` VETOSU |

    Burada terim `odul_miktari`DİR ve ayrıca «kâr payı değildir» diye
    uyarılır. Sütunun tamamında veto sözcüğü aramak, geçerli kimliği de
    silerdi — ilk okuyuşta «nakit iade» ve «mil» tam bu yüzden ödül
    ölçütünden düşmüştü.
    """
    return karsilik.split(";", 1)[0]


def _alan_adi(karsilik: str) -> str | None:
    """İlk beyandaki şema alanı adı. Yoksa None.

    KÜÇÜK HARF ŞARTI: şema alanları `snake_case`, veto sabitleri
    `BUYUK_HARF` (`MEVDUAT_URUNU`, `HESAP_ARACI_CIKTISI`). İkisi aynı sütunda
    duruyor; ayrım yazım biçiminden okunur, ayrı bir liste tutulmaz.
    """
    for kod in _KOD_ADI.findall(_ilk_beyan(karsilik)):
        ad = kod.split("=")[0].strip().split("(")[0].strip()
        if ad.isidentifier() and ad.islower():
            return ad
    return None


def _veto_mu(karsilik: str) -> bool:
    anahtar = arama_anahtari(_ilk_beyan(karsilik))
    return any(isaret in anahtar for isaret in VETO_ISARETLERI)


@lru_cache(maxsize=1)
def alan_eslemesi() -> dict[str, str]:
    """Terim anahtarı -> şema alanı. YALNIZ kimlik kuranlar.

    NEDEN SÖZLÜKTEN: ölçüt ipuçları chatbot'ta elle yazılıydı ve sabit
    sırayla ilk eşleşen kazanıyordu. «48 ay vadeli taşıt finansmanında en
    düşük TOPLAM MALİYET» sorusunda «vade» baskın çıkıp cevabı
    «Vade en düşük olan banka: 3 ay» yapıyordu.

    Sözlük bu eşlemeyi zaten tutuyor ve dört kişi ona karşı çalışıyor;
    ikinci bir liste tutmak, iki listenin zamanla ayrışmasını garanti eder.
    Yan kazanç: «nakit iade» ve «mil» gibi konuşma dilindeki karşılıklar
    sözlükte var, elle yazılan listede yoktu.
    """
    return {
        ad: alan
        for terim in terimler()
        if not _veto_mu(terim.karsilik) and (alan := _alan_adi(terim.karsilik))
        for ad in terim.adlar
    }


@lru_cache(maxsize=1)
def karistirilan_olcutler() -> dict[str, Terim]:
    """Sözlüğün AYRI TUTMAYI beyan ettiği terimler: anahtar -> terim.

    «Katılma hesaplarında en yüksek kâr paylaşım oranı?» sorusunda doğru
    davranış, `kar_payi_orani` sütununu sıralamak değil, sözlüğün yazdığı
    ayrımı söylemektir.
    """
    return {
        ad: terim
        for terim in terimler()
        if _veto_mu(terim.karsilik) and _alan_adi(terim.karsilik)
        for ad in terim.adlar
    }


@lru_cache(maxsize=1)
def hesaplanan_olcutler() -> dict[str, Terim]:
    """Sütun değil FORMÜL olan ölçütler: anahtar -> terim."""
    return {
        ad: terim
        for terim in terimler()
        if HESAPLANAN_ISARETI in arama_anahtari(terim.karsilik)
        for ad in terim.adlar
    }


__all__ = [
    "SOZLUK_YOLU",
    "alan_eslemesi",
    "hesaplanan_olcutler",
    "karistirilan_olcutler",
    "TANIM_IPUCLARI",
    "Terim",
    "tanim_sorusu_mu",
    "terim_bul",
    "terimler",
]
