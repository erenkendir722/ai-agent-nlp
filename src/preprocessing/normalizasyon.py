"""Türkçe metin normalizasyonu (şartname 5.6).

Bu modül %30'luk "eksik veya farklı yazılmış bilgiler karşısında doğru sonuç"
kriterinin kalbidir. Buradaki her fonksiyon saf ve test edilebilirdir: girdi bir
metin parçası, çıktı normalize değer. Metin İÇİNDE arama yapmak bu modülün işi
değil — o iş `src/extraction/kural.py`'nin.

Türkçe'ye özgü tuzaklar ve nasıl çözüldükleri dosya içinde işaretlidir.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

from src.schema import ALAN_BOYUTLARI, TEK_BIRIMLI_ALANLAR, Birim

# ---------------------------------------------------------------------------
# TUZAK 1 — İ/I/ı/i sorunu
# ---------------------------------------------------------------------------
# Python'un str.lower() metodu Türkçe için YANLIŞTIR:
#     "İSTANBUL".lower() -> "i̇stanbul"   (i + U+0307 birleşik nokta kalır)
#     "IRAK".lower()     -> "irak"        (olması gereken: "ırak")
# Bu sessiz hata, eşleştirme ve sınıflandırmada saatlerce sürecek hata avına yol
# açar. Önce Türkçe'ye özgü harfleri elle eşleriz, sonra genel lower() uygularız.

_KUCULTME = str.maketrans({"I": "ı", "İ": "i", "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç"})
_BUYULTME = str.maketrans({"ı": "I", "i": "İ", "ş": "Ş", "ğ": "Ğ", "ü": "Ü", "ö": "Ö", "ç": "Ç"})
_BIRLESIK_NOKTA = "̇"  # COMBINING DOT ABOVE


def tr_kucult(metin: str) -> str:
    """Türkçe'ye doğru küçük harfe çevirme.

    >>> tr_kucult("İSTANBUL")
    'istanbul'
    >>> tr_kucult("IRAK")
    'ırak'
    >>> tr_kucult("KÂR PAYI")
    'kâr payı'
    """
    return metin.translate(_KUCULTME).lower().replace(_BIRLESIK_NOKTA, "")


def tr_buyult(metin: str) -> str:
    """Türkçe'ye doğru büyük harfe çevirme.

    >>> tr_buyult("istanbul")
    'İSTANBUL'
    """
    return metin.translate(_BUYULTME).upper()


# ---------------------------------------------------------------------------
# TUZAK 2 — şapkalı harfler ve kesme işareti
# ---------------------------------------------------------------------------
# "kâr" ve "kar" metinlerde iki türlü de geçiyor; aramada birleştirilmeli.
# "TL'ye", "Bankası'nın", "2026'da" tokenizasyonu bozar.

_SAPKALI = str.maketrans({"â": "a", "î": "i", "û": "u", "Â": "A", "Î": "İ", "Û": "U"})
_KESME_ISARETLERI = "'’ʼ´`"


def sapkasiz(metin: str) -> str:
    """Şapkalı harfleri düzleştirir: kâr -> kar. Yalnız ARAMA için kullanın.

    Kullanıcıya gösterilen metinde şapkayı koruyun; bu yalnız eşleştirme anahtarı.
    """
    return metin.translate(_SAPKALI)


def arama_anahtari(metin: str) -> str:
    """Eşleştirme için kanonik biçim: küçük harf, şapkasız, tek boşluk, kesmesiz.

    >>> arama_anahtari("KÂR PAYI  ORANI")
    'kar payi orani'
    """
    s = tr_kucult(metin)
    s = sapkasiz(s)
    for k in _KESME_ISARETLERI:
        s = s.replace(k, "")
    # Türkçe'ye özgü harfleri ASCII'ye indir (yalnız anahtar üretiminde)
    s = s.translate(str.maketrans({"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c"}))
    return re.sub(r"\s+", " ", s).strip()


def kesmeden_ayir(metin: str) -> str:
    """Kesme işaretini BOŞLUĞA çevirir — özel adı kendi ekinden ayırmak için.

    `arama_anahtari` kesmeyi SİLER ve tokenizasyon için doğrusu odur:
    «TL'ye» tek bir belirteçtir. Ama ÖZEL AD eşleştirmesinde tersi gerekir —
    kesme, Türkçe'de özel adı ekinden ayıran işaretin ta kendisidir:

        «Albaraka'dan»  -> arama_anahtari -> «albarakadan»   ← eşleşmez
                        -> kesmeden_ayir  -> «albaraka dan»  ← «albaraka» eşleşir

    27 Ağustos'ta ölçüldü: `chatbot._bankalari_bul` sözcük kümesini kurarken
    `anahtar.replace("'", " ")` yazıyordu, yani niyet buydu — ama `anahtar`
    zaten `arama_anahtari`'ndan geçmiş ve kesme silinmişti. Satır ÖLÜYDÜ ve
    «Albaraka'dan 1.000.000 TL konut finansmanı» sorusu HİÇBİR bankaya
    eşleşmiyordu.

    Ekin serbest bırakılması (`terim_gecer` gibi baş bağlama) bu iş için
    yanlış olurdu: «emlakçı» o zaman Türkiye Emlak'a eşleşirdi ve bu, yakınlık
    eşiğinin ölçerek dışarıda bıraktığı bir eşleşme (bkz. `YAKINLIK_ESIGI`).
    Kesme bir tahmin değil, kullanıcının kendi koyduğu sınırdır.

    ÇIKARIM YOLU BU FONKSİYONU ÇAĞIRMAZ; yalnız eşleştirme kullanır.

    >>> kesmeden_ayir("Albaraka'dan")
    'Albaraka dan'
    """
    for isaret in _KESME_ISARETLERI:
        metin = metin.replace(isaret, " ")
    return metin


def bosluk_duzelt(metin: str) -> str:
    """Görünmez karakterleri temizler, boşlukları teke indirir, satırları korur."""
    metin = metin.replace(" ", " ").replace("​", "")
    metin = unicodedata.normalize("NFC", metin)
    metin = re.sub(r"[ \t]+", " ", metin)
    metin = re.sub(r"\n{3,}", "\n\n", metin)
    return metin.strip()


# ---------------------------------------------------------------------------
# TUZAK 3 — binlik / ondalık ayracı
# ---------------------------------------------------------------------------
# Türkçe'de "1.500,50" = bin beş yüz elli kuruş. Standart float() bunu 1.5 okur.
# Ayrı bir ayrıştırıcı şart.

_SAYI_DESENI = re.compile(r"[-+]?\d[\d.,\s]*\d|\d")


def sayi_ayristir(parca: str) -> float | None:
    """Türkçe biçimli sayıyı float'a çevirir.

    Karar kuralı:
      - Hem '.' hem ',' varsa  -> '.' binlik, ',' ondalık   ("1.500,50" -> 1500.5)
      - Yalnız ',' varsa       -> ',' ondalık                ("2,05"     -> 2.05)
      - Yalnız '.' varsa       -> son grup tam 3 haneliyse binlik, değilse ondalık
                                  ("50.000" -> 50000 · "2.05" -> 2.05)

    Son kural bir sezgidir ve Türkçe metinlerde doğru çalışır: kimse ondalık
    kısmı üç haneli yazmaz ("2.050" oran değil, iki bin elli demektir).

    >>> sayi_ayristir("1.500,50")
    1500.5
    >>> sayi_ayristir("50.000")
    50000.0
    >>> sayi_ayristir("2.05")
    2.05
    >>> sayi_ayristir("% 2 , 05")
    2.05
    """
    if not parca:
        return None
    eslesme = _SAYI_DESENI.search(parca)
    if not eslesme:
        return None

    ham = eslesme.group(0)
    ham = re.sub(r"\s+", "", ham)  # "2 , 05" -> "2,05" (bozma varyantı)
    ham = ham.rstrip(".,")
    if not ham:
        return None

    isaret = -1.0 if ham.startswith("-") else 1.0
    ham = ham.lstrip("+-")

    if "." in ham and "," in ham:
        govde = ham.replace(".", "").replace(",", ".")
    elif "," in ham:
        govde = ham.replace(",", ".")
    elif "." in ham:
        son_grup = ham.rsplit(".", 1)[1]
        govde = ham.replace(".", "") if len(son_grup) == 3 else ham
    else:
        govde = ham

    try:
        return isaret * float(govde)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Oran (kâr payı, indirim)
# ---------------------------------------------------------------------------

_YUZDE_SOZCUGU = re.compile(r"y[üu]zde", re.IGNORECASE)


_BINDE = re.compile(r"\bbinde\s+([\d.,]+|\w+)", re.IGNORECASE)
"""«binde 5», «binde beş» — bindelik oran. Yüzdeye çevrilir: binde 5 = %0,5."""

_YAZIYLA_SAYI = {
    "bir": 1.0, "iki": 2.0, "uc": 3.0, "dort": 4.0, "bes": 5.0,
    "alti": 6.0, "yedi": 7.0, "sekiz": 8.0, "dokuz": 9.0, "on": 10.0,
}
"""Bindelik oranlarda sayı yazıyla da yazılıyor («binde beş»); derlemde 9 kayıt."""


def oran_ayristir(parca: str) -> float | None:
    """Yüzde ifadesini sayıya çevirir. Tüm yazım varyantlarını kabul eder.

    >>> oran_ayristir("%2,05")
    2.05
    >>> oran_ayristir("% 2.05")
    2.05
    >>> oran_ayristir("2.05 %")
    2.05
    >>> oran_ayristir("yüzde 2,05")
    2.05
    >>> oran_ayristir("aylık %1,89'dan başlayan")
    1.89

    BİNDE — Türk bankacılığının tahsis ücretinde standart yazımı. Yüzde
    işareti hiç geçmez, oran bindelik olarak verilir:

    >>> oran_ayristir("binde 5")
    0.5
    >>> oran_ayristir("binde 5'i oranındadır")
    0.5
    >>> oran_ayristir("binde beş")
    0.5
    >>> oran_ayristir("vergiler hariç finansman tutarının binde 5'i")
    0.5
    """
    if not parca:
        return None

    # 25 Ağustos ölçümü: "binde" derlemde 62 kayıtta geçiyor (22'si "binde 5")
    # ve hiçbiri okunamıyordu. `tahsis_ucreti` bu yüzden altın sette dolu olan
    # hücreleri boş bırakıyordu; altın set haklıydı, ayrıştırıcı sağırdı.
    # Yüzdeden ÖNCE bakılır: "binde 5" ifadesinde yüzde işareti yoktur.
    if (bindelik := _BINDE.search(parca)) is not None:
        ham = bindelik.group(1)
        deger = _YAZIYLA_SAYI.get(arama_anahtari(ham)) if not ham[0].isdigit() else sayi_ayristir(ham)
        if deger is not None and 0.0 <= deger <= 1000.0:
            return deger / 10.0
        return None

    temiz = _YUZDE_SOZCUGU.sub("%", parca)
    if "%" not in temiz and "٪" not in temiz:
        return None

    deger = sayi_ayristir(temiz.replace("%", " "))
    if deger is None:
        return None

    # Akıl sağlığı kontrolü: kâr payı/indirim oranı 0-100 aralığındadır.
    # "50.000" gibi bir sayı yanlışlıkla oran olarak okunduysa reddet.
    if not 0.0 <= deger <= 100.0:
        return None
    return deger


# ---------------------------------------------------------------------------
# Para tutarı
# ---------------------------------------------------------------------------

_CARPAN_SOZLERI = {"milyar": 1_000_000_000, "milyon": 1_000_000, "bin": 1_000}
"""Çarpan sözcüğü -> değeri. Tek kaynak: hem serbest tarama hem birim
bağlama aynı sözlükten okur."""

_CARPANLAR = tuple(
    (re.compile(rf"\b{soz}\b", re.IGNORECASE), carpan)
    for soz, carpan in _CARPAN_SOZLERI.items()
)
# Dikkat: "50.000TL" yazımı gerçek metinlerde sık geçer. `\bTL\b` bunu KAÇIRIR,
# çünkü rakam ile 'T' arasında sözcük sınırı yoktur. Bu yüzden başta sözcük
# sınırı yerine "önünde harf olmasın" koşulu kullanıyoruz — böylece "50.000TL"
# eşleşir ama "HTL", "ATL" gibi kısaltmalar eşleşmez.
_HARF_ONCESI_YOK = r"(?<![A-Za-zÇĞİÖŞÜçğıöşü])"
_PARA_BIRIMI = re.compile(
    rf"(₺|{_HARF_ONCESI_YOK}TL\b|{_HARF_ONCESI_YOK}TRY\b"
    rf"|\bT[üu]rk\s+Liras[ıi]\b|\blira\b)",
    re.IGNORECASE,
)


_TUTAR_DESENI = re.compile(
    rf"(?:(\d[\d.,\s]*\d|\d)\s*)?({'|'.join(_CARPAN_SOZLERI)})?\s*"
    rf"(?:₺|{_HARF_ONCESI_YOK}TL\b|{_HARF_ONCESI_YOK}TRY\b"
    rf"|T[üu]rk\s+Liras[ıi]\b|lira\b)",
    re.IGNORECASE,
)
"""Sayıyı PARA BİRİMİNE BAĞLAYAN desen — birim zorunluyken kullanılır.

NEDEN VAR (27 Ağustos, jüri soru havuzu 9. madde):
    Eski kod «metinde TL geçiyor mu?» diye sorup sonra metnin İLK sayısını
    alıyordu. İkisi arasında hiçbir bağ yoktu:

        «120 ay vadeli 1.000.000 TL konut finansmanı»
          -> TL var  ✓        -> ilk sayı 120  -> tutar 120 TL

    Profil ekranı bunu «mevcut_musteri · 120 TL · 120 ay» diye çözüyor ve
    357 kampanyayı uygun buluyordu; sorulan 1.000.000 TL hiç görülmedi.
    Aynı hata çarpanda da vardı: «bin» sözcüğü metnin HERHANGİ bir yerinde
    geçtiğinde tabana uygulanıyordu.

    `_AY_DESENI` vadeyi ilk günden birimine bağlıyordu; tutar bağlanmamıştı.
"""


def para_ayristir(parca: str, birim_zorunlu: bool = True) -> float | None:
    """TL tutarını float'a çevirir. Çarpan sözcüklerini uygular.

    `birim_zorunlu` iken sayı BİRİME BAĞLI olmalıdır: metnin başka bir yerinde
    duran sayı (vade, taksit sayısı, tarih) tutar sayılmaz.

    >>> para_ayristir("500 TL")
    500.0
    >>> para_ayristir("50.000 TL")
    50000.0
    >>> para_ayristir("500₺")
    500.0
    >>> para_ayristir("1,5 milyon TL")
    1500000.0
    >>> para_ayristir("500 bin Türk Lirası")
    500000.0
    >>> para_ayristir("120 ay vadeli 1.000.000 TL konut finansmanı")
    1000000.0
    >>> para_ayristir("36 ay, bin TL'lik harcama")
    1000.0
    """
    if not parca:
        return None

    if birim_zorunlu:
        for eslesme in _TUTAR_DESENI.finditer(parca):
            sayi, carpan_sozu = eslesme.group(1), eslesme.group(2)
            if sayi is None and carpan_sozu is None:
                continue  # çıplak «TL» — bağlanacak bir değer yok
            # «bin TL» sayısızdır ve BİN TL demektir; taban 1 alınır.
            taban = sayi_ayristir(sayi) if sayi is not None else 1.0
            if taban is None:
                continue
            if carpan_sozu is not None:
                taban *= _CARPAN_SOZLERI[carpan_sozu.lower()]
            return taban
        return None

    # Birim aranmıyorsa bağlanacak bir çıpa da yok: ilk sayı + metindeki çarpan.
    taban = sayi_ayristir(parca)
    if taban is None:
        return None
    for desen, carpan in _CARPANLAR:
        if desen.search(parca):
            return taban * carpan
    return taban


# ---------------------------------------------------------------------------
# Vade / taksit
# ---------------------------------------------------------------------------

# Türkçe eklerine dikkat: "120 ay", "120 aya kadar", "36 aylık", "24 ayda".
# Basit \bay\b sınırı bunların hepsini kaçırır. Ek listesi kapalı tutulur ki
# "ayrıca" gibi sözcükler yanlışlıkla eşleşmesin.
_TR_EKLER = r"(?:a|e|ı|i|da|de|ta|te|dan|den|tan|ten|lık|lik|luk|lük|lı|li|ya|ye|nın|nin)?"
_AY_DESENI = re.compile(rf"(\d+)\s*(?:ay|taksit){_TR_EKLER}\b", re.IGNORECASE)
_YIL_DESENI = re.compile(rf"(\d+)\s*(?:y[ıi]l|sene){_TR_EKLER}\b", re.IGNORECASE)


def vade_ayristir(parca: str) -> int | None:
    """Vadeyi AY cinsine çevirir. Yıl geçiyorsa 12 ile çarpar.

    Birden fazla süre geçiyorsa en büyüğünü alır: "12-120 ay" -> 120,
    çünkü şemadaki alan `vade_ay_max`.

    >>> vade_ayristir("120 ay")
    120
    >>> vade_ayristir("120 aya kadar")
    120
    >>> vade_ayristir("10 yıl")
    120
    >>> vade_ayristir("120 taksit")
    120
    >>> vade_ayristir("36 aya varan vade seçeneği")
    36
    """
    if not parca:
        return None
    adaylar: list[int] = [int(s) for s in _AY_DESENI.findall(parca)]
    adaylar += [int(s) * 12 for s in _YIL_DESENI.findall(parca)]
    if not adaylar:
        return None
    en_buyuk = max(adaylar)
    # Akıl sağlığı: 600 aydan (50 yıl) uzun vade yok, muhtemelen tutar okunmuş.
    return en_buyuk if 0 < en_buyuk <= 600 else None


# ---------------------------------------------------------------------------
# Tarih
# ---------------------------------------------------------------------------

_AYLAR = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "mayis": 5,
    "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8, "eylül": 9, "eylul": 9,
    "ekim": 10, "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12,
}
_AY_ADLARI = "|".join(_AYLAR)

_TARIH_METIN = re.compile(rf"(\d{{1,2}})\s+({_AY_ADLARI})\s+(\d{{4}})", re.IGNORECASE)
_TARIH_NOKTALI = re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b")
_YIL_SONU = re.compile(r"\b(\d{4})\s*(?:y[ıi]l\s*sonu|sonuna\s+kadar)", re.IGNORECASE)
_AY_SONU = re.compile(rf"\b({_AY_ADLARI})\s+(\d{{4}})\s*(?:sonu|ay\s*sonu)", re.IGNORECASE)

_AY_GUN_SAYISI = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _ayin_son_gunu(yil: int, ay: int) -> int:
    if ay == 2 and (yil % 4 == 0 and (yil % 100 != 0 or yil % 400 == 0)):
        return 29
    return _AY_GUN_SAYISI[ay - 1]


def tarih_ayristir(parca: str) -> date | None:
    """Türkçe tarih ifadelerini `date` nesnesine çevirir.

    Belirsiz ifadeler ("yıl sonuna kadar") kampanya bitişi bağlamında SON güne
    yorumlanır — kampanya o tarihe kadar geçerli demektir.

    >>> tarih_ayristir("31 Aralık 2026")
    datetime.date(2026, 12, 31)
    >>> tarih_ayristir("31.12.2026")
    datetime.date(2026, 12, 31)
    >>> tarih_ayristir("2026 yıl sonuna kadar")
    datetime.date(2026, 12, 31)
    >>> tarih_ayristir("Eylül 2026 sonu")
    datetime.date(2026, 9, 30)
    """
    if not parca:
        return None
    kucuk = tr_kucult(parca)

    if (m := _TARIH_METIN.search(kucuk)) is not None:
        gun, ay_adi, yil = int(m.group(1)), m.group(2), int(m.group(3))
        return _guvenli_tarih(yil, _AYLAR[ay_adi], gun)

    if (m := _TARIH_NOKTALI.search(kucuk)) is not None:
        gun, ay, yil = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return _guvenli_tarih(yil, ay, gun)

    if (m := _AY_SONU.search(kucuk)) is not None:
        ay, yil = _AYLAR[m.group(1)], int(m.group(2))
        return _guvenli_tarih(yil, ay, _ayin_son_gunu(yil, ay))

    if (m := _YIL_SONU.search(kucuk)) is not None:
        return _guvenli_tarih(int(m.group(1)), 12, 31)

    return None


def _guvenli_tarih(yil: int, ay: int, gun: int) -> date | None:
    if not (1 <= ay <= 12 and 1 <= gun <= 31 and 2000 <= yil <= 2100):
        return None
    try:
        return date(yil, ay, gun)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Masrafsızlık (bool alan)
# ---------------------------------------------------------------------------

MASRAF_SOZCUKLERI = ("masraf", "ucret", "komisyon", "tahsis", "dosya parasi")
"""Bir cümlenin masraftan bahsedip bahsetmediği. Bunlardan biri yoksa cümle
masrafsızlık beyanı DEĞİLDİR — 14 Ağustos'ta LLM, masraf sözcüğü hiç geçmeyen
bir metinden `masrafsiz_mi=True` uydurdu (şartname madde 11, C Bankası)."""

FINANSMAN_MASRAFI = (
    "dosya masraf", "finansman masraf", "kredi masraf",
    "tahsis", "dosya parasi", "ekspertiz", "ipotek tesis",
)
"""`masrafsiz_mi` ALANININ konusu: finansmanın maliyeti.

`MASRAF_SOZCUKLERI` çıplak "ucret"i de içeriyor ve o fazla geniş: banka
sayfalarında "kart aidatı yok", "FAST ile ücretsiz transfer", "hesap işletim
ücreti alınmaz" cümleleri boldur. Bunlar doğru cümlelerdir ama BAŞKA bir
ürünün ücretinden söz ederler; finansmanın masrafsız olduğunu söylemezler.

15 Ağustos altın set ölçümü: `masrafsiz_mi` 15 uyuşmazlığın üçü tam olarak
buydu — "Kolay ve Hızlı para transferi FAST'ta ücretsiz" cümlesinden
`masrafsiz_mi=True`, "hisse senedi alım-satım komisyonu" cümlesinden `False`
üretiliyordu. Kılavuz insana bu ayrımı açıkça yaptırıyor
(docs/ETIKETLEME_KILAVUZU.md, "kart ücreti yok" tablosu); sistem de aynı
ayrımı yapmalı."""

FINANSMAN_DISI_UCRET = (
    "kart aidat", "aidat", "kart ucreti", "kart yillik",
    "havale", "eft", "fast", "para transfer", "transfer ucret",
    "hesap isletim", "uyelik", "hisse senedi", "alim-satim", "alim satim",
    "ekstre", "sigorta primi",
    # Tüketici mevzuatı kalıbı — BAŞVURUNUN ücretsiz sonuçlandırılmasını
    # anlatır, finansmanın masrafsızlığını değil. Banka sayfalarının
    # altbilgisinde neredeyse standart olarak geçiyor ve 16 Ağustos
    # ölçümünde tek başına 3 yanlış pozitif üretti:
    #   "Talebiniz en kısa sürede ve en geç otuz (30) gün içinde ücretsiz
    #    olarak sonuçlandırılmaktadır."
    "talebiniz", "sonuclandirilmakta", "basvurunuz",
    # "temel bankacılık işlemlerinden de ücretsiz yararlanın" — hesap/kart
    # hizmetleri paketi, finansman masrafı değil.
    "temel bankacilik",
    # 25 Ağustos ölçümü (altın set 98 kayıt): `masrafsiz_mi` 16 yanlış pozitif
    # üretti ve hepsi aynı biçimdeydi — sayfada finansmanla ilgisi olmayan bir
    # ücretsizlik geçiyordu. Kanıt cümleleriyle birlikte:
    #   "Katılım SMS'i ücretsiz olup..."          -> sms
    #   "Ücretsiz Lounge Hizmeti"                  -> lounge
    #   "ATM'lerden ücretsiz olarak para çekme"    -> para cekme
    #   "hediye altın ... ücretsiz gönderilir"     -> kargo/gonderil
    #   "- Masrafsız Banka ve Kredi Kartı"         -> kart
    "sms", "lounge", "para cekme", "kargo", "gonderil",
    "kredi karti", "banka karti", "kart dunyasi",
)
"""Ücretin finansmana DEĞİL başka bir hizmete ait olduğunu gösteren imler."""

FINANSMAN_URUNU = (
    "finansman", "ihtiyac", "konut", "tasit", "arac", "dosya", "tahsis", "ekspertiz",
)
"""Cümlenin finansman ürününden söz ettiğini gösteren imler.

`masrafsiz_mi` sıfat yolunun kapısı. «Masrafsız» tek başına neyin masrafsız
olduğunu söylemez: 25 Ağustos ölçümünde "Bankan Mobilse İşlemlerin Masrafsız!",
"Masraf yok, kazanç var" ve "VKart dünyasında masraf yok!" cümleleri
`masrafsiz_mi=True` üretiyordu. Üçü de doğru cümle, üçü de finansman hakkında
DEĞİL. Kılavuzun insana dayattığı ayrımın (finansmanın tahsis/dosya masrafı)
kural karşılığı budur."""

_KAPSAM_DISI = re.compile(
    r"\bicermemekte(?:dir)?\b|\bicermez\b|\bdahil degil|\bharic(?:tir)?\b"
)
"""«Ödenecek toplam tutar finansman tahsis ücretini İÇERMEMEKTEDİR.»

Olumsuz yüklem ama masrafsızlık DEĞİL — tam tersi. Cümle ücretin var
olduğunu, yalnız gösterilen toplama dahil edilmediğini söylüyor. Ek tanıyan
`_OLUMSUZ_YUKLEM` bunu "alınmamaktadır" ile aynı kefeye koyup True üretiyordu;
altın set False diyor ve haklı. Kapsam beyanı ile ücret beyanı ayrı şeylerdir."""

# TUZAK 6 — Türkçe olumsuzlama EK ile yapılır, sözcükle değil.
#
# Önceki sürüm kalıp listesi tutuyordu ("masraf alinmaz", "masraf yok", ...).
# Bankaların resmî sitelerinde baskın olan kip ise -mAktAdır'dır:
#
#     "Kampanya kapsamında 50.000 TL'ye kadar dosya masrafı ALINMAMAKTADIR."
#
# Bu kalıp listede yoktu; cümle "masraf bilgisi yok" sayıldı ve daha kötüsü,
# olumsuzlama görülmediği için 50.000 TL bir TAHSİS ÜCRETİ olarak çıkarıldı.
# Şartnamenin kendi örnek metni (madde 11, A Bankası) tam bu cümledir.
#
# Çözüm kalıp eklemek değil, EKİ tanımaktır: -mAz, -mIyor, -mAmAktA(dır).
# Kalıp listesi her yeni çekimde tekrar kırılırdı.
_OLUMSUZ_YUKLEM = re.compile(
    r"\w*m(?:az|ez)\b"  # alınmaz, ödenmez, uygulanmaz
    r"|\w*m[iu]yor\b"  # alınmıyor, olmuyor  (ı->i, u ünlü uyumu)
    r"|\w*m[ae]m(?:akta|ekte)(?:dir)?\b"  # alınmamaktadır, tahsil edilmemektedir
    r"|\byok(?:tur)?\b"
    r"|\bbulunmamaktadir\b"
    r"|\bsifir\b"
)

_MASRAFSIZ_SIFAT = re.compile(r"\b(?:masraf|ucret|komisyon)(?:siz|suz)\b")
"""masrafsız / ücretsiz / komisyonsuz — yüklem gerektirmeyen sıfat biçimi."""

_MASRAFSIZ_KALIPLAR = ("sifir masraf", "0 masraf", "hicbir masraf")

_BANKA_KARSILIYOR = "banka tarafindan karsilan"
"""«Ekspertiz ücreti banka tarafından karşılanmaktadır» — yüklem OLUMLU ama
masraf müşteriye yansımıyor. Şartname madde 11, B Bankası bunu «Ekspertiz
ücretsiz» olarak tablolar."""

_UCRET_MIKTARI = re.compile(
    r"%\s*\d|\d\s*%|\bbinde\s+\d|\byuzde\s+\d|\d[\d.,]*\s*(?:tl|₺)\b"
)
"""Ücretin miktarını bildiren ifade — oran, binde ya da tutar."""

_MASRAFLI_YUKLEM = re.compile(
    r"\balin(?:ir|maktadir|mistir)\b"
    r"|\btahsil edil(?:ir|mektedir)\b"
    r"|\buygulan(?:ir|maktadir)\b"
    r"|\byansitil(?:ir|maktadir)\b"
    # 25 Ağustos: 9 ıskalama tek kalıptaydı — "Tahsis ücreti, finansman
    # tutarının %0,5'i KADARDIR". Ücretin varlığını bildiriyor ama yüklem
    # listesinde yoktu, alan `None` kalıyordu (etiketçiler doğru şekilde
    # `hayır` yazmıştı).
    r"|\bkadardir\b"
    r"|\boranindadir\b"
    r"|\btahsil edilecektir\b"
    r"|\balinacaktir\b"
)


def olumsuzlanmis_mi(parca: str) -> bool:
    """Cümlede olumsuz bir yüklem var mı? (kural katmanı da bunu kullanır)

    Tek kaynak olması bilinçli: kural katmanı kendi olumsuzlama listesini
    tutsaydı iki liste zamanla ayrışır, biri düzeltilirken diğeri unutulurdu.

    >>> olumsuzlanmis_mi("Dosya masrafı alınmamaktadır.")
    True
    >>> olumsuzlanmis_mi("Dosya masrafı alınır.")
    False
    """
    return bool(_OLUMSUZ_YUKLEM.search(arama_anahtari(parca)))


def masrafsiz_mi(parca: str) -> bool | None:
    """Masrafsızlık beyanını bool'a çevirir. Belirsizse None döner.

    None ile False farkı önemlidir: None = "metinde bilgi yok" (Belirtilmemiş),
    False = "metin masraf alındığını söylüyor".

    >>> masrafsiz_mi("Dosya masrafı yok!")
    True
    >>> masrafsiz_mi("masrafsız konut finansmanı")
    True
    >>> masrafsiz_mi("Dosya masrafı alınır.")
    False
    >>> masrafsiz_mi("Konut finansmanı kampanyası") is None
    True
    >>> masrafsiz_mi("50.000 TL'ye kadar dosya masrafı alınmamaktadır.")
    True
    >>> masrafsiz_mi("Ekspertiz ücreti banka tarafından karşılanmaktadır.")
    True
    >>> masrafsiz_mi("Sağlam Kart'ta yıllık kart ücreti yok!") is None
    True
    >>> masrafsiz_mi("FAST ile para transferi ücretsiz.") is None
    True
    >>> masrafsiz_mi("Hisse senedi alım-satım işlemlerinde komisyon alınır.") is None
    True

    Kapsam beyanı masrafsızlık değildir — ücret VARDIR, yalnız gösterilen
    toplama dahil edilmemiştir:

    >>> masrafsiz_mi("Ödenecek toplam tutar finansman tahsis ücretini içermemektedir.")
    False

    Tüketici mevzuatı kalıbı BAŞVURUNUN ücretsizliğini anlatır:

    >>> masrafsiz_mi("Talebiniz 30 gün içinde ücretsiz sonuçlandırılmaktadır.") is None
    True
    """
    if not parca:
        return None
    anahtar = arama_anahtari(parca)

    # Cümle BAŞKA bir hizmetin ücretinden söz ediyorsa, finansmanın masrafı
    # hakkında hiçbir şey söylemiyor demektir — meğer ki finansman masrafını
    # da ayrıca anıyor olsun ("kart aidatı ve dosya masrafı alınmaz").
    #
    # `komisyon` bilerek `FINANSMAN_MASRAFI` DIŞINDA: hem finansman komisyonunu
    # hem hisse senedi alım-satım komisyonunu anlatabiliyor, dolayısıyla tek
    # başına "bu cümle finansman masrafından söz ediyor" demeye yetmez.
    if any(im in anahtar for im in FINANSMAN_DISI_UCRET) and not any(
        sozcuk in anahtar for sozcuk in FINANSMAN_MASRAFI
    ):
        return None

    # Sıfat biçimi ("masrafsız") yüklem aramaya gerek bırakmaz, ama NEYİN
    # masrafsız olduğunu söylemez — finansman bağlamı ayrıca aranır.
    if _MASRAFSIZ_SIFAT.search(anahtar) or any(k in anahtar for k in _MASRAFSIZ_KALIPLAR):
        if any(im in anahtar for im in FINANSMAN_URUNU):
            return True
        return None

    # Buradan sonrası bir MASRAF cümlesi olmayı şart koşar. Bu kapı olmadan
    # "kampanya sona ermemektedir" gibi alakasız bir olumsuzlama masrafsızlık
    # sanılırdı.
    if not any(sozcuk in anahtar for sozcuk in MASRAF_SOZCUKLERI):
        return None

    # Cümle masraftan söz ediyor ama HANGİ ürünün masrafı? Finansman bağlamı
    # yoksa beyan bu alana yazılamaz — "Masraf yok, kazanç var" bir kart
    # kampanyası sloganıdır, finansman masrafsızlığı değil.
    if not any(im in anahtar for im in FINANSMAN_URUNU):
        return None

    if _BANKA_KARSILIYOR in anahtar:
        return True
    # Kapsam beyanı olumsuzlamadan ÖNCE bakılır: "ücreti içermemektedir"
    # olumsuz bir yüklemdir ama ücretin YOK olduğunu değil, gösterilen
    # toplama DAHİL OLMADIĞINI söyler — yani ücret vardır.
    if _KAPSAM_DISI.search(anahtar):
        return False
    if _OLUMSUZ_YUKLEM.search(anahtar):
        return True
    if _MASRAFLI_YUKLEM.search(anahtar):
        return False

    # ÜCRETİN MİKTARINI bildirmek, ücretin VARLIĞINI bildirmektir.
    # "Finansman tahsis ücreti finansman tutarının %0,5'dir" cümlesinde
    # yüklem ne olumsuz ne de "alınır" ailesinden; sadece bir orandır.
    # 25 Ağustos ölçümünde bu kalıp 6 kayıtta alanı boş bırakıyordu.
    # Olumsuzlama kapısı YUKARIDA olduğu için "dosya masrafı alınmaz"
    # buraya hiç düşmez.
    if _UCRET_MIKTARI.search(anahtar):
        return False
    return None


# ---------------------------------------------------------------------------
# Birim çözümleme (şema sözleşmesi: `schema.ALAN_BOYUTLARI`)
# ---------------------------------------------------------------------------


def birim_belirle(ham_ifade: str | None, alan_adi: str) -> Birim | None:
    """Bir değerin BOYUTUNU çözer. Tek çözümleyici — çıkarım da göç de bunu çağırır.

    İki aşamalı, çünkü sorunun iki hâli var:

    1. TEK BİRİMLİ ALAN — cevabı sözleşme veriyor. `kar_payi_orani` her zaman
       yüzdedir; metne bakmaya gerek yok, bakmak gereksiz risk olurdu.

    2. ÇOK BİRİMLİ ALAN — cevabı yalnız ham ifade veriyor. `tahsis_ucreti`
       hem «500 TL» hem «%0,50» olabilir ve bunları ayıran tek şey yazılıştır.
       Bilgi tam burada kayboluyordu:

           ayristirici=lambda s: para_ayristir(s, ...) or oran_ayristir(s)

       O `or`, hangisinin tuttuğunu çağırana söylemiyordu.

    TEK FONKSİYON OLMASI ÖNEMLİ: aynı çözümleme hem yeni çıkarımda hem eski
    kayıtların göçünde kullanılır. İki ayrı uygulama, iki ayrı gerçeklik
    üretir ve göç edilmiş kayıtla yeni kayıt sessizce ayrışırdı.

    >>> birim_belirle("%1,89", "kar_payi_orani").value
    'yuzde'
    >>> birim_belirle("120 aya kadar", "vade_ay_max").value
    'ay'
    >>> birim_belirle("0,50%", "tahsis_ucreti").value
    'yuzde'
    >>> birim_belirle("500 TL", "tahsis_ucreti").value
    'tl'
    >>> birim_belirle("binde 5", "tahsis_ucreti").value
    'yuzde'
    >>> birim_belirle("belirsiz", "tahsis_ucreti") is None
    True
    """
    ima_edilen = TEK_BIRIMLI_ALANLAR.get(alan_adi)
    if ima_edilen is not None:
        return ima_edilen

    izinli = ALAN_BOYUTLARI.get(alan_adi)
    if not izinli or not ham_ifade:
        return None

    # Yüzde işareti TL'den önce sınanır: «%0,50 TL» gibi karma yazımda
    # belirleyici olan oran işaretidir (maliyet tablolarında görülüyor).
    #
    # «binde» de bir ORAN yazımıdır ve işaretsizdir. `oran_ayristir` onu zaten
    # yüzdeye çeviriyor (binde 5 -> 0,5), ama birim çözümü yalnız «%» ve
    # «yüzde» arıyordu: değer doğru üretilip BİRİMSİZ kalıyor, çok birimli
    # `tahsis_ucreti` boyut kapısında düşüyordu. 26 Ağustos'ta ölçüldü —
    # dört kayıtta doğru cevap («finansman tutarının binde 5'i») böyle
    # kayboluyordu.
    if Birim.YUZDE in izinli and (
        "%" in ham_ifade or _YUZDE_SOZCUGU.search(ham_ifade) or _BINDE.search(ham_ifade)
    ):
        return Birim.YUZDE
    if Birim.TL in izinli and _PARA_BIRIMI.search(ham_ifade):
        return Birim.TL
    return None


__all__ = [
    "MASRAF_SOZCUKLERI",
    "arama_anahtari",
    "birim_belirle",
    "bosluk_duzelt",
    "kesmeden_ayir",
    "masrafsiz_mi",
    "olumsuzlanmis_mi",
    "oran_ayristir",
    "para_ayristir",
    "sapkasiz",
    "sayi_ayristir",
    "tarih_ayristir",
    "tr_buyult",
    "tr_kucult",
    "vade_ayristir",
]
