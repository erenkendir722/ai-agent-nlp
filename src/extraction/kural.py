"""Kural katmanı — regex tabanlı, yüksek kesinlikli çıkarım (Katman 2a).

Bu katman AZ ama KESİN çalışır. Bir sayıyı yalnız uygun bağlam sözcüğünün
yakınında bulursa kabul eder; şüphedeyse hiç değer üretmez. Boşluğu LLM katmanı
doldurur, uzlaştırıcı ikisini birleştirir.

Neden hibrit? Sayısal alanlarda regex'in kesinliği, metinsel alanlarda LLM'in
esnekliği gerekiyor. Ablasyon tablosu bu kararın ölçülmüş gerekçesidir.

Tasarım notu: banka başına özel kural YOKTUR. Tüm kurallar `KURALLAR` listesinde
veri olarak durur; yeni bir alan eklemek bir satır eklemektir.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from src.preprocessing.normalizasyon import (
    masrafsiz_mi,
    olumsuzlanmis_mi,
    oran_ayristir,
    para_ayristir,
    tarih_ayristir,
    vade_ayristir,
)
from src.schema import (
    AYLIK_KAR_PAYI_ALT_SINIRI,
    AYLIK_KAR_PAYI_UST_SINIRI,
    EN_AZ_FINANSMAN_TUTARI,
    Alan,
    Kaynak,
)

# ---------------------------------------------------------------------------
# Değer desenleri — "metinde şuna benzeyen bir şey var mı?"
# ---------------------------------------------------------------------------

D_ORAN = re.compile(r"(?:%|y[üu]zde)\s*\d[\d.,\s]*|\d[\d.,]*\s*%", re.IGNORECASE)
D_PARA = re.compile(
    r"\d[\d.,]*\s*(?:milyar|milyon|bin)?\s*(?:₺|TL\b|TRY\b|T[üu]rk\s+Liras[ıi])",
    re.IGNORECASE,
)
D_VADE = re.compile(
    r"\d+\s*(?:ay|taksit|y[ıi]l|sene)"
    r"(?:a|e|ı|i|da|de|ta|te|dan|den|tan|ten|lık|lik|luk|lük|lı|li|ya|ye)?\b",
    re.IGNORECASE,
)
D_TARIH = re.compile(
    r"\d{1,2}[./]\d{1,2}[./]\d{4}"
    r"|\d{1,2}\s+(?:Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|Haziran|Temmuz|"
    r"Ağustos|Agustos|Eylül|Eylul|Ekim|Kasım|Kasim|Aralık|Aralik)\s+\d{4}"
    r"|\d{4}\s*(?:y[ıi]l\s*sonu|sonuna\s+kadar)",
    re.IGNORECASE,
)
D_SAYI = re.compile(r"\b\d+\b")

Secim = Literal["en_yuksek", "en_dusuk", "ilk", "en_yakin"]


@dataclass(frozen=True)
class KuralTanimi:
    """Tek bir alan için çıkarım kuralı.

    `baglam_sozcukleri` olmadan hiçbir değer kabul edilmez. "50.000 TL" metnin
    herhangi bir yerinde geçebilir; onu `finansman_tutari_max` yapan şey,
    yakınında "finansman limiti" yazmasıdır. Halüsinasyon önlemenin kural
    katmanındaki karşılığı budur.
    """

    alan: str
    deger_deseni: re.Pattern[str]
    ayristirici: Callable[[str], Any]
    baglam_sozcukleri: tuple[str, ...]
    secim: Secim = "en_yakin"
    baglam_penceresi: int = 140
    taban_guven: float = 0.90
    dislayici_sozcukler: tuple[str, ...] = field(default=())
    ayni_cumle: bool = False
    """True ise bağlam sözcüğü değerle AYNI CÜMLEDE olmak zorunda."""
    olumsuzlama_reddet: bool = False
    """True ise "alınmaz / yok / ücretsiz" içeren bağlamdan sayı çıkarılmaz."""
    gecerli_aralik: tuple[float, float] | None = None
    """(alt, üst) — değer bu ARALIĞIN DIŞINDAYSA aday hiç üretilmez (dışlayıcı sınırlar).

    Bağlam kontrolü "bu sayı doğru şeyin yanında mı?" diye sorar; bu alan
    "bu sayı bu alan için MÜMKÜN mü?" diye sorar. İkisi farklı hatalar yakalar.

    14 Ağustos ölçümü: `kar_payi_orani` dolu 27 kaydın 13'ü (%48) makul aralık
    dışındaydı ve hepsi kural katmanından geliyordu. Örnek — bir hesaplama
    aracının çıktısı:

        Yıllık Maliyet Oranı
        % 82,44

    Burada bağlam kontrolü kuralı KURTARMAZ: "oran" sözcüğü sayıya
    "maliyet"ten daha yakın, dolayısıyla dışlayıcı sözcük tetiklenmez.
    Aylık kâr payının %82 olamayacağını bilen tek şey alan bilgisidir."""


KURALLAR: tuple[KuralTanimi, ...] = (
    KuralTanimi(
        alan="kar_payi_orani",
        deger_deseni=D_ORAN,
        ayristirici=oran_ayristir,
        # Çıplak "oran" bilinçli olarak KALIYOR. 14 Ağustos'ta önce o suçlandı
        # ("Yıllık Maliyet Oranı" onunla eşleşiyor) ve çıkarıldı; 96 kayıt
        # üzerinde ölçülünce zararlı olduğu görüldü:
        #
        #   yapılandırma        dolu  çöp  temiz
        #   özgün                 27   13     14
        #   yalnız aralık         15    0     15   ← seçilen
        #   yalnız sözcük         11    3      8
        #   aralık + sözcük        9    0      9
        #
        # Aralık sınırı çöpü tek başına sıfırlıyor; sözcük kısıtı üstüne hiçbir
        # şey katmadan 6 DOĞRU değeri eliyor. Bağlam sözcüğünü daraltmak
        # sezgisel olarak doğru görünüyordu, ölçüm aksini söyledi.
        baglam_sozcukleri=("kar payi", "kar orani", "kar payi orani", "oran", "aylik kar"),
        dislayici_sozcukler=("indirim", "iade", "nakit iade", "kdv"),
        secim="en_dusuk",  # "%1,89'dan başlayan" — vitrin oranı en düşüğüdür
        taban_guven=0.93,
        # Aylık kâr payı tek haneli yüzdelerde seyreder; %15 üstü aylık oran
        # değildir (bkz. schema.AYLIK_KAR_PAYI_UST_SINIRI). Sınır ayrıca
        # SEÇİMİ de düzeltiyor: makul olmayan adaylar elenince `en_dusuk`
        # seçimi gerçek orana ulaşabiliyor — temiz sayısı 14'ten 15'e çıkıyor.
        gecerli_aralik=(AYLIK_KAR_PAYI_ALT_SINIRI, AYLIK_KAR_PAYI_UST_SINIRI),
    ),
    KuralTanimi(
        alan="finansman_tutari_max",
        deger_deseni=D_PARA,
        ayristirici=lambda s: para_ayristir(s, birim_zorunlu=True),
        baglam_sozcukleri=(
            "finansman", "limit", "tutar", "kredi", "destek", "kadar finansman",
        ),
        # "degerinde" ve "... ceki" bir HEDİYENİN değerini işaret eder, finansman
        # limitini değil. Şartname madde 11, C Bankası: "5.000 TL değerinde
        # alışveriş çeki verilmektedir" cümlesindeki 5.000 TL, aynı cümlede
        # "konut finansmanı" geçtiği için finansman tutarı sanılıyordu.
        # Tam sözcük yerine "ceki" kullanmak zorunlu: "cek" parçası "gercek",
        # "cekim", "cekilis" gibi sözcüklerin içinde geçer ve yanlış eleme yapar.
        dislayici_sozcukler=(
            "odul", "hediye", "iade", "masraf", "ucret", "puan",
            "degerinde", "alisveris ceki", "hediye ceki", "market ceki",
        ),
        secim="en_yuksek",
        taban_guven=0.88,
        # Üst sınır YOK: kurumsal finansmanda yüz milyonlu limitler gerçektir.
        gecerli_aralik=(EN_AZ_FINANSMAN_TUTARI, float("inf")),
    ),
    KuralTanimi(
        alan="vade_ay_max",
        deger_deseni=D_VADE,
        ayristirici=vade_ayristir,
        # "aya kadar" / "aya varan" bilinçli olarak burada: bu kalıpların
        # KENDİSİ vade ifadesidir, ayrıca "vade" sözcüğü aramaya gerek yok.
        # Uzun sayfalarda "vade" zaten pencerede geçtiği için bu fark
        # görünmüyordu; ŞARTNAME MADDE 11'in kısa örnek metninde görünüyor:
        #     "%1,89 kâr payı oranı ile 120 aya kadar konut finansmanı"
        # Burada hiçbir bağlam sözcüğü yok ve vade kaçırılıyordu. Jürinin
        # kendi örneği ve `/extract` uç noktasına yapıştırılan kısa metinler
        # tam olarak bu biçimde geliyor.
        baglam_sozcukleri=(
            "vade", "geri odeme", "odeme plani", "taksit",
            "aya kadar", "ay kadar", "aya varan", "ay varan",
        ),
        secim="en_yuksek",
        taban_guven=0.92,
        gecerli_aralik=(0.0, 361.0),  # 30 yıl üstü vade katılım finansmanında yok
    ),
    KuralTanimi(
        alan="taksit_sayisi",
        deger_deseni=re.compile(r"\d+\s*taksit\w*", re.IGNORECASE),
        ayristirici=vade_ayristir,
        baglam_sozcukleri=("taksit", "pesin fiyatina"),
        secim="en_yuksek",
        taban_guven=0.90,
        gecerli_aralik=(0.0, 361.0),
    ),
    KuralTanimi(
        alan="tahsis_ucreti",
        deger_deseni=re.compile(
            rf"(?:{D_PARA.pattern})|(?:{D_ORAN.pattern})", re.IGNORECASE
        ),
        ayristirici=lambda s: para_ayristir(s, birim_zorunlu=True) or oran_ayristir(s),
        baglam_sozcukleri=("tahsis ucreti", "tahsis", "dosya masrafi", "komisyon"),
        # "5.000.000 TL'ye kadar finansman. Dosya masrafı alınmaz." cümlesinde
        # her iki kural da aynı sayıya talip olur. Mesafe kuralı sayesinde
        # "finansman" daha yakın olduğu için tahsis ücreti reddedilir.
        dislayici_sozcukler=("finansman", "limit", "odul", "hediye", "iade"),
        secim="en_yakin",
        taban_guven=0.85,
        ayni_cumle=True,
        olumsuzlama_reddet=True,
    ),
    KuralTanimi(
        alan="odul_miktari",
        deger_deseni=D_PARA,
        ayristirici=lambda s: para_ayristir(s, birim_zorunlu=True),
        baglam_sozcukleri=(
            "odul", "hediye", "kazan", "nakit iade", "bonus", "cashback", "para puan",
            "alisveris ceki", "hediye ceki", "market ceki", "degerinde",
        ),
        dislayici_sozcukler=("finansman", "limit", "masraf"),
        secim="en_yuksek",
        taban_guven=0.86,
    ),
    KuralTanimi(
        alan="indirim_orani",
        deger_deseni=D_ORAN,
        ayristirici=oran_ayristir,
        baglam_sozcukleri=("indirim", "iade orani", "avantaj orani"),
        dislayici_sozcukler=("kar payi",),
        secim="en_yuksek",
        taban_guven=0.88,
        gecerli_aralik=(0.0, 100.1),  # yüzde; %100'den fazla indirim olmaz
    ),
    KuralTanimi(
        alan="alisveris_puani",
        deger_deseni=D_PARA,
        ayristirici=lambda s: para_ayristir(s, birim_zorunlu=True),
        baglam_sozcukleri=("puan", "alisveris puani", "para puan", "chip para"),
        secim="en_yuksek",
        taban_guven=0.84,
    ),
    KuralTanimi(
        alan="kampanya_bitis",
        deger_deseni=D_TARIH,
        ayristirici=tarih_ayristir,
        baglam_sozcukleri=(
            "son", "bitis", "gecerli", "kadar", "kampanya suresi", "son basvuru",
        ),
        secim="en_yakin",
        taban_guven=0.90,
    ),
)


# ---------------------------------------------------------------------------
# Aday bulma
# ---------------------------------------------------------------------------


@dataclass
class Aday:
    deger: Any
    ham_ifade: str
    baslangic: int
    bitis: int
    guven: float


_CUMLE_SONU = re.compile(r"[.!?\n]")


def _cumle_araligi(metin: str, baslangic: int, bitis: int, azami: int = 300) -> tuple[int, int]:
    """Eşleşmeyi içeren cümleyi bulur — kullanıcıya gösterilecek alıntı budur."""
    sol = max(0, baslangic - azami)
    sag = min(len(metin), bitis + azami)

    onceki = list(_CUMLE_SONU.finditer(metin, sol, baslangic))
    alinti_bas = onceki[-1].end() if onceki else sol

    sonraki = _CUMLE_SONU.search(metin, bitis, sag)
    alinti_bit = sonraki.end() if sonraki else sag

    return alinti_bas, alinti_bit


_KONUM_KORUYAN_ESLEME = str.maketrans(
    {"I": "ı", "İ": "i", "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç",
     "â": "a", "î": "i", "û": "u", "Â": "a", "Î": "i", "Û": "u",
     "ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c"}
)


def _konum_koruyan_anahtar(metin: str) -> str:
    """`arama_anahtari` ile aynı eşlemeyi yapar ama UZUNLUĞU DEĞİŞTİRMEZ.

    Bu ayrım şart: `arama_anahtari` kesme işaretlerini siler ve boşlukları
    teke indirir, dolayısıyla üretilen dizgideki konumlar özgün metindeki
    konumlarla hizalanmaz. Mesafe hesabı yapan kod, hizalanmayan indeksle
    çalışırsa sessizce yanlış uzaklık üretir.
    """
    return metin.translate(_KONUM_KORUYAN_ESLEME).lower()


def _en_yakin_uzaklik(pencere: str, sozcukler: tuple[str, ...], hedef: int) -> int | None:
    """Verilen sözcüklerden hedefe en yakın OLANIN uzaklığı. Yoksa None.

    Her sözcüğün YALNIZ ilk geçtiği yere değil, tüm geçişlerine bakar —
    "Konut Finansmanı" başlıkta da geçiyorsa, sayının yanındaki "finansman"
    kaçırılmamalı.
    """
    en_yakin: int | None = None
    for sozcuk in sozcukler:
        basla = 0
        while (konum := pencere.find(sozcuk, basla)) != -1:
            uzaklik = abs(konum - hedef)
            en_yakin = uzaklik if en_yakin is None else min(en_yakin, uzaklik)
            basla = konum + 1
    return en_yakin


def _olumsuz_cumle_mi(cumle: str) -> bool:
    """"Dosya masrafı alınmaz" -> bu cümleden sayısal ücret çıkarılamaz.

    Olumsuzlanmış bir masraf beyanının yakınındaki sayı, o masrafın tutarı
    DEĞİLDİR. Bu ayrımı yapmamak, "masrafsız" diyen bir kampanyaya 5.000.000
    TL'lik tahsis ücreti atamakla sonuçlanır.

    Olumsuzlama tanıma normalizasyon katmanından gelir; burada ikinci bir
    sözcük listesi TUTULMAZ. Eskiden tutuluyordu ve listede -mAktAdır kipi
    yoktu: "50.000 TL'ye kadar dosya masrafı alınmamaktadır" cümlesinden
    50.000 TL'lik tahsis ücreti çıkarılıyordu.
    """
    return olumsuzlanmis_mi(cumle)


def _baglam_skoru(metin: str, kural: KuralTanimi, baslangic: int, bitis: int) -> float | None:
    """Bağlam sözcüğü yakınlığına göre güven çarpanı. Sözcük yoksa None (=reddet).

    DIŞLAMA MESAFEYE DUYARLIDIR. Naif yaklaşım — "pencerede dışlayıcı sözcük
    varsa reddet" — gerçek metinlerde yanlış çalışır:

        "5.000.000 TL'ye kadar finansman. Dosya masrafı alınmaz."

    Burada "masraf" sözcüğü penceredeydi, bu yüzden `finansman_tutari_max`
    reddedildi; aynı sayı `tahsis_ucreti` kuralına takılıp 5 milyon TL'lik bir
    "tahsis ücreti" üretti. Jüri önünde görülecek türden bir hata.

    Doğrusu: dışlayıcı sözcük, ancak KAPSAYICI sözcükten DAHA YAKINSA reddeder.
    "finansman" sayının hemen yanındaysa, 40 karakter ötedeki "masraf" o sayının
    ne olduğunu değiştirmez.
    """
    if kural.ayni_cumle:
        # Değer ile bağlam sözcüğü AYNI CÜMLEDE olmalı. Ücret gibi alanlarda
        # cümle sınırı anlam sınırıdır: bir cümlede tutar, ondan sonraki
        # cümlede masraf beyanı geçiyorsa bunlar farklı şeylerdir.
        # `azami` cümle sınırının ARANDIĞI yarıçaptır, pencerenin kendisi değil;
        # 0 verilirse pencere sayının kendisine çöker ve kural her şeyi reddeder.
        sol, sag = _cumle_araligi(metin, baslangic, bitis, azami=kural.baglam_penceresi)
    else:
        sol = max(0, baslangic - kural.baglam_penceresi)
        sag = min(len(metin), bitis + kural.baglam_penceresi)

    ham_pencere = metin[sol:sag]
    pencere = _konum_koruyan_anahtar(ham_pencere)
    hedef = baslangic - sol

    kapsayici = _en_yakin_uzaklik(pencere, kural.baglam_sozcukleri, hedef)
    if kapsayici is None:
        return None

    dislayici = _en_yakin_uzaklik(pencere, kural.dislayici_sozcukler, hedef)
    if dislayici is not None and dislayici < kapsayici:
        return None

    if kural.olumsuzlama_reddet and _olumsuz_cumle_mi(ham_pencere):
        return None

    yakinlik = max(0.0, 1.0 - kapsayici / (2 * kural.baglam_penceresi))
    return kural.taban_guven * (0.80 + 0.20 * yakinlik)


def _adaylari_bul(metin: str, kural: KuralTanimi) -> list[Aday]:
    adaylar: list[Aday] = []
    for eslesme in kural.deger_deseni.finditer(metin):
        ham = eslesme.group(0).strip()
        try:
            deger = kural.ayristirici(ham)
        except (ValueError, TypeError):
            continue
        if deger is None:
            continue

        if kural.gecerli_aralik is not None and isinstance(deger, int | float):
            alt, ust = kural.gecerli_aralik
            if not alt < float(deger) < ust:
                continue

        guven = _baglam_skoru(metin, kural, eslesme.start(), eslesme.end())
        if guven is None:
            continue

        adaylar.append(Aday(deger, ham, eslesme.start(), eslesme.end(), guven))
    return adaylar


def _sec(adaylar: list[Aday], secim: Secim) -> Aday | None:
    if not adaylar:
        return None
    if secim == "ilk":
        return adaylar[0]
    if secim == "en_yakin":
        return max(adaylar, key=lambda a: a.guven)
    # Sayısal seçimlerde önce en güvenilir grubu al, sonra değere göre seç
    en_yuksek_guven = max(a.guven for a in adaylar)
    guvenli = [a for a in adaylar if a.guven >= en_yuksek_guven - 0.05]
    sirali = sorted(guvenli, key=lambda a: (a.deger, a.guven))
    return sirali[-1] if secim == "en_yuksek" else sirali[0]


# ---------------------------------------------------------------------------
# Dış yüz
# ---------------------------------------------------------------------------


def kurallarla_cikar(metin: str, url: str, cekim_tarihi: datetime) -> dict[str, Alan]:
    """Metinden kural katmanının bulabildiği tüm alanları çıkarır.

    Dönen sözlükte YALNIZCA bulunan alanlar vardır. Bulunamayanlar burada yer
    almaz; uzlaştırıcı onları LLM'den ya da `Alan.yok()`'tan doldurur.
    """
    sonuc: dict[str, Alan] = {}

    for kural in KURALLAR:
        secilen = _sec(_adaylari_bul(metin, kural), kural.secim)
        if secilen is None:
            continue
        alinti_bas, alinti_bit = _cumle_araligi(metin, secilen.baslangic, secilen.bitis)
        sonuc[kural.alan] = Alan(
            deger=secilen.deger,
            ham_ifade=secilen.ham_ifade,
            kaynak=Kaynak(
                url=url,
                cekim_tarihi=cekim_tarihi,
                alinti=metin[alinti_bas:alinti_bit].strip(),
                karakter_baslangic=alinti_bas,
                karakter_bitis=alinti_bit,
            ),
            guven=round(min(secilen.guven, 1.0), 3),
            yontem="kural",
        )

    if (masrafsiz := _masrafsizlik(metin, url, cekim_tarihi)) is not None:
        sonuc["masrafsiz_mi"] = masrafsiz

    return sonuc


_MASRAF_CUMLE = re.compile(r"[^.!?\n]*(?:masraf|tahsis|komisyon|ücret)[^.!?\n]*[.!?\n]?", re.IGNORECASE)


def _masrafsizlik(metin: str, url: str, cekim_tarihi: datetime) -> Alan | None:
    """Masrafsızlık beyanı — cümle düzeyinde aranır, kanıt cümlesi saklanır."""
    for eslesme in _MASRAF_CUMLE.finditer(metin):
        cumle = eslesme.group(0)
        karar = masrafsiz_mi(cumle)
        if karar is None:
            continue
        return Alan(
            deger=karar,
            ham_ifade=cumle.strip()[:120],
            kaynak=Kaynak(
                url=url,
                cekim_tarihi=cekim_tarihi,
                alinti=cumle.strip(),
                karakter_baslangic=eslesme.start(),
                karakter_bitis=eslesme.end(),
            ),
            guven=0.91,
            yontem="kural",
        )
    return None


__all__ = ["KURALLAR", "KuralTanimi", "kurallarla_cikar"]
