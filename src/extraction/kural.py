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

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from src.preprocessing.normalizasyon import (
    arama_anahtari,
    masrafsiz_mi,
    olumsuzlanmis_mi,
    oran_ayristir,
    birim_belirle,
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

log = logging.getLogger(__name__)

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
AYLAR = (
    "Ocak", "Şubat", "Subat", "Mart", "Nisan", "Mayıs", "Mayis", "Haziran",
    "Temmuz", "Ağustos", "Agustos", "Eylül", "Eylul", "Ekim", "Kasım", "Kasim",
    "Aralık", "Aralik",
)
"""Türkçe ay adları — şapkalı ve şapkasız biçimleriyle TEK kaynak.

Tarihe bakan her desen bundan türetilir (`D_TARIH`, tarih aralığı
denetimleri). Ayrı ayrı yazılsalardı yeni bir biçim eklemek birkaç regex'i
birden düzeltmeyi gerektirirdi ve biri unutulduğunda hata sessiz olurdu:
desen eşleşmez, alan boş kalır, kimse fark etmez."""

_AY = "|".join(AYLAR)
_GUN_AY = rf"\d{{1,2}}\s+(?:{_AY})"
"""«13 Mart» — yılsız da eşleşir; aralığın başında yıl çoğu zaman yazılmıyor
("16 Haziran - 31 Ağustos 2026")."""

_SAYISAL_TARIH = r"\d{1,2}[./]\d{1,2}[./]\d{4}"

D_TARIH = re.compile(
    rf"{_SAYISAL_TARIH}"
    rf"|{_GUN_AY}\s+\d{{4}}"
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
    veto_ifadeleri: tuple[str, ...] = field(default=())
    """Pencerede GEÇMESİ yeten ifadeler — mesafe karşılaştırması yapılmaz.

    `dislayici_sozcukler` "hangisi daha yakın?" diye sorar ve bazı hatalarda
    yapısal olarak kaybeder:

        "Geri Ödenecek Toplam Tutar 261.044,84 TL"

    Burada dışlayıcı olarak "geri odenecek" eklense bile bağlam sözcüğü
    "tutar" sayıya DAHA YAKINDIR (hemen solunda), dolayısıyla mesafe kuralı
    değeri kabul eder. Oysa bu ifade pencerede geçiyorsa sayı ne olursa olsun
    finansman limiti değildir. Böyle ifadeler için yakınlık değil VARLIK
    ölçüttür."""
    tarih_araligi_sonu_kabul: bool = False
    """True ise «X - Y» aralığının SONU, bağlam sözcüğü olmasa da kabul edilir.

    Bağlam sözcüğü kuralının tek istisnası ve gerekçesi ölçülmüş: kampanya
    bitiş tarihlerinin çoğu, yakınında hiçbir anahtar sözcük olmayan çıplak
    bir aralık olarak yazılıyor. Bkz. `_tarih_araligi_sonu_mu`."""
    aralik_ucu_reddet: bool = False
    """True ise bir ARALIĞIN UCU olarak yazılmış sayı aday sayılmaz.

    Dilim tabloları ("400.000-800.000 TL arasında %50'si") bağlam kontrolünü
    de büyüklük sınırını da geçer; onları ayıran tek şey yazılış biçimidir.
    Bkz. `_aralik_ucu_mu`."""
    sifir_gecerli: bool = False
    """True ise TAM SIFIR, `gecerli_aralik` alt sınırından muaftır.

    "Vade farksız" / "0 kâr payı" kampanyalarında oran gerçekten sıfırdır ve
    bu, boş hücreden FARKLI bir bilgidir — altın set kılavuzu bunu açıkça
    söylüyor (`tools/altin_set.py`: "SIFIR GEÇERLİDİR").

    Kural katmanı ise üretemiyordu: `gecerli_aralik` denetimi `alt < deger`
    biçiminde ve `AYLIK_KAR_PAYI_ALT_SINIRI` 0,10. Yani etiketleyene "sıfır
    yaz" denen değeri çıkarıcı hiçbir koşulda bulamıyordu. 16 Ağustos
    ölçümünde `kar_payi_orani`'nın 10 dolu hücresinin 3'ü sıfırdı — alanın
    %30'u yapısal olarak erişilemezdi.

    Muafiyet YALNIZ tam sıfıra: alt sınırın asıl işi "%0,05 havale
    komisyonu" gibi küçük ama sıfır olmayan oranları elemek ve o iş duruyor."""
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


# ---------------------------------------------------------------------------
# Veto kategorileri — "bu sayı kampanyanın koşulu değil"
# ---------------------------------------------------------------------------
#
# Bunlar ALAN'a değil, sayının geldiği BAĞLAM TÜRÜNE bakar. Bir hesap
# makinesi widget'ı hem tutar hem oran üretir; ikisi de kampanya koşulu
# değildir. Kategoriyi tek alana bağlamak, aynı hatayı bir alanda eleyip
# diğerinde geçirmek demektir — 16 Ağustos'ta tam olarak bu oldu:
#
#     Kâr Oranı | %1.00 |
#     Toplam Geri Ödenen | 66.066,24 TL |
#
# Tutar için veto yazılmıştı, oran serbestti; üstelik %1,00 makullük
# aralığının içinde olduğu için sınır da yakalamıyordu.

HESAP_ARACI_CIKTISI = (
    "geri oden",
    "aylik taksit tutari",
    "yillik maliyet oran",
    "toplam geri",
    "ucretler toplami",
)
"""Sayfadaki taksit hesaplama aracının ÜRETTİĞİ değerler.

Kampanyanın koşulu değil, kullanıcının girdiği örneğin sonucudur. Gövde
hâlinde yazılıyor çünkü bankalar aynı şeyi farklı çekimlerle söylüyor:
"Geri Ödenecek Toplam Tutar" (Albaraka) / "Toplam Geri Ödenen"
(Türkiye Finans). Ek'e bağlı yazılan veto ikincisini kaçırıyordu."""

ORNEK_TABLO = ("baz alinarak", "ornek odeme")
"""«100.000 TL baz alınarak oluşturulan örnek ödeme tablosu».

Tablodaki her sayı temsilîdir; taban tutar da, satırlardaki oranlar da."""

MEVDUAT_URUNU = (
    "hesap bakiyesi",
    "gunluk hesap",
    "katilma hesabi",
    "katilim fonu",
    "getiri oran",
    "hos geldin",
)
"""Mevduat/katılma hesabı ürünleri — finansman kampanyası değil.

Aynı sayfada hem hesap hem finansman anlatılabiliyor; hesabın alt/üst
bakiye limitleri ve getiri oranları finansman koşulu sanılıyordu."""

VERGI_VE_MEVZUAT = ("gelir vergisi", "vergi istisna", "bsmv", "kkdf")
"""Yasal kesinti oranları — bankanın sunduğu koşul değil.

NOT: Buradaki her ifade derlemde EN AZ İKİ kayıtta geçmelidir. Tek kayıtta
geçen bir veto, örüntü değil o kaydın ezberidir; ölçümü şişirir ve
görülmemiş metinde işe yaramaz. `tools/` altındaki tarama bunu denetler."""

SAYISAL_ALAN_VETOLARI = (
    HESAP_ARACI_CIKTISI + ORNEK_TABLO + MEVDUAT_URUNU + VERGI_VE_MEVZUAT
)
"""Her sayısal alana uygulanan ortak taban.

Alan bazlı ekler bunun ÜSTÜNE gelir; taban ortak olduğu için yeni bir
bağlam türü keşfedildiğinde tek yere yazmak bütün alanları korur."""


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
        # Yüzde her yerde var; ortak taban KÂR PAYI olmayan yüzdeleri eler.
        # Hepsinde "oran" bağlam sözcüğü yakında geçtiği için mesafe kuralı
        # elemiyor — varlık ölçüt olmalı.
        veto_ifadeleri=SAYISAL_ALAN_VETOLARI
        + (
            # "Erken ödeme tazminatı oranı ... % 1'i" — tazminat, kâr payı değil.
            "erken odeme tazminati",
            # 23 Ağustos, 590 kayıt: kâr payı %5 üstüne çıkan 10 kaydın
            # HEPSİNDE yüzde başka bir şeye bağlıydı:
            #   "%10 oranında indirim kazanımı sağlayacaklardır"
            #   "%10 oranında mil kazanırsınız"
            #   "%10 oranına varan özel indirimler"
            # Bunlar DIŞLAYICI sözcükle elenemiyor: "oran" sayının hemen
            # yanında ("oranında") olduğu için mesafe karşılaştırmasını hep
            # kazanıyor. Yukarıdaki not zaten bunu söylüyor — varlık ölçüt
            # olmalı, o yüzden veto.
            "oraninda indirim",
            "oraninda mil",
            "oranina varan ozel indirim",
            "indirim kazanimi",
            # "iade" ÖLÇÜLDÜ (23 Ağustos, 590 kayıt): veto olarak 10 kaydı
            # eliyor ve onunun da HEPSİ nakit iade kampanyası — tek bir meşru
            # kâr payı kaybı yok. Dolu kâr payı 43'ten 33'e, %5 üstü 3'ten 1'e
            # iniyor. Dışlayıcı sözcük olarak zaten vardı ama yetmiyordu:
            # "%7,5 yerine %15 iade" gibi cümlelerde bağlam sözcüğü sayıya
            # daha yakın kalıp mesafe karşılaştırmasını kazanıyordu.
            "iade",
        ),
        # NOT: "konut hissesi" / "hisseli" de denendi (mülkiyet payı yüzdesi)
        # ama ÖLÇÜMDE hiçbir şey katmadı — o kaydı ortak tabandaki "bsmv"
        # zaten yakalıyor. Derlemde tek kayıtta geçen ifadeler eklenmedi.
        secim="en_dusuk",  # "%1,89'dan başlayan" — vitrin oranı en düşüğüdür
        taban_guven=0.93,
        # "Vade farksız" kampanyada oran gerçekten sıfırdır; alt sınır onu
        # eliyordu. Bkz. `KuralTanimi.sifir_gecerli`.
        sifir_gecerli=True,
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
        # Ortak taban yeterli: hesap makinesi çıktısı, örnek tablo ve mevduat
        # limitleri bu alanın yanlış pozitiflerinin tamamını oluşturuyordu.
        # Dışlayıcı SÖZCÜK olarak eklemek işe yaramıyordu: bağlam sözcüğü
        # "tutar" ifadelerin kendi içinde geçiyor ve sayıya daha yakın kalıp
        # mesafe kuralını her seferinde kazanıyordu.
        veto_ifadeleri=SAYISAL_ALAN_VETOLARI,
        secim="en_yuksek",
        taban_guven=0.88,
        # Üst sınır YOK: kurumsal finansmanda yüz milyonlu limitler gerçektir.
        gecerli_aralik=(EN_AZ_FINANSMAN_TUTARI, float("inf")),
        # Üst sınırın yerine geçen kısıt. 16 Ağustos ölçümünde 15 yanlış
        # pozitifin 8'i dilim tablosundandı; büyüklük değil YAZILIŞ ayırıyor.
        aralik_ucu_reddet=True,
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
        # Ölçüldü (16 Ağu): ortak taban bu alanda F1'i 0,756 → 0,791 yapıyor.
        # Örnek ödeme tablolarındaki vade sütunu ("48 | 4,50% | ...") ve
        # hesap makinesi çıktısındaki vade artık aday olmuyor.
        veto_ifadeleri=SAYISAL_ALAN_VETOLARI,
        secim="en_yuksek",
        taban_guven=0.92,
        gecerli_aralik=(0.0, 361.0),  # 30 yıl üstü vade katılım finansmanında yok
    ),
    KuralTanimi(
        alan="taksit_sayisi",
        deger_deseni=re.compile(r"\d+\s*taksit\w*", re.IGNORECASE),
        ayristirici=vade_ayristir,
        baglam_sozcukleri=("taksit", "pesin fiyatina"),
        veto_ifadeleri=SAYISAL_ALAN_VETOLARI,
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
        # 23 Ağustos ölçümü: masrafsız işaretli 3 kayıtta tahsis ücreti de
        # doluydu — üçünde de alan alakasız bir tutarı toplamıştı:
        #   "5.000.000 TL ve üzerinde işlem hacmi"   -> hacim eşiği
        #   "10.000 TL'ye kadar para çekebilir"      -> ATM limiti
        #   "Blokesiz %0.99 Komisyon"                -> POS komisyon oranı
        # Son ikisi "komisyon" bağlam sözcüğüyle geldiği için sözcüğü
        # kaldırmak çözüm değil (gerçek tahsis ücretlerini de elerdi);
        # ayırt edici olan hacim/ATM/POS bağlamıdır.
        dislayici_sozcukler=(
            "finansman", "limit", "odul", "hediye", "iade",
            "islem hacmi", "para cek", "atm", "bloke",
        ),
        # Ortak taban burada ÖLÇÜMDE nötr (0,909 sabit) ama yine de bağlı:
        # hesap makinesi çıktısı bir tahsis ücreti satırı da üretebilir ve
        # aynı bağlam türünü bir alanda eleyip diğerinde geçirmek, bugün
        # düzeltilen tutarsızlığın ta kendisiydi. Nötr olması zarar değil;
        # kapsam dışı bırakmak ise bilinen bir hataya açık kapı bırakmaktır.
        veto_ifadeleri=SAYISAL_ALAN_VETOLARI
        + (
            # "PTT ATM'sinden komisyon ÖDEMEDEN 10.000 TL'ye kadar para
            # çekebilir" — olumsuzlama cümlesi; buradaki tutar ücret değil,
            # çekim limitidir. Dışlayıcı ("atm") mesafede kaybediyordu çünkü
            # "komisyon" bağlam sözcüğü sayıya daha yakın. Ölçüldü: yalnız bu
            # kaydı eliyor, yan hasar yok (10 -> 9).
            "komisyon odemeden",
            "para cekebilir",
        ),
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
        veto_ifadeleri=SAYISAL_ALAN_VETOLARI
        + (
            # "kişi başı maksimum 2.000 TL, TOPLAMDA 5 kişi için maksimum
            # 10.000 TL" — ödül kişi başına düşendir; `en_yuksek` toplamı
            # alıyordu. Veto aynı cümledeki DOĞRU adayı (2.000) da eliyor,
            # sonuç "Belirtilmemiş" — yanlış bir 10.000'den iyi ama tam değil.
            #
            # YÖNLÜ NİTELİK DENENDİ VE ÖLÇÜLDÜ (16 Ağu). Sayının yalnız soluna
            # bakıp "toplamda"yı "kişi başı"ndan ayıran bir mekanizma yazıldı;
            # izole cümlede 2.000'i doğru seçti ama altın sette alan F1'ini
            # 0,667'den 0,333'e DÜŞÜRDÜ. İki sebep:
            #   1) Belgede ikinci bir cümle daha var — "davet eden kişinin
            #      maksimum 10.000 TL ödül kazanabilmesi için" — solunda
            #      "toplamda" yok, eleme tutmuyor, `en_yuksek` yine onu seçiyor.
            #   2) Eleme, hayatta kalan aday kümesini değiştirdiği için başka
            #      kayıtlarda seçimi kaydırıp iki yeni hata açtı.
            # Ders: bu bir ELEME değil SIRALAMA sorunu. Aday eleyerek
            # çözülmüyor; `secim="en_yuksek"` ödül alanı için yanlış ölçüt.
            # Doğru çözüm seçim katmanında — S-14'e bırakıldı.
            #
            # 17 Ağu (S-14) — VETO DARALTILDI: "toplamda" → "kisi icin".
            # "toplamda" jenerik bir sözcük ve yan hasar veriyordu: Hayat
            # Finans'ın *"kazanılabilecek maksimum nakit ödül tutarı TOPLAMDA
            # 300 TL'dir"* cümlesinde 300 TL gerçek ödül tutarı olduğu hâlde
            # eleniyordu. Toplamı işaret eden asıl imleç "toplamda" değil,
            # kişi sayısına bölünmüş ifade: *"5 KİŞİ İÇİN maksimum 10.000 TL"*.
            # Ölçüm (yalnız kural, altın set): F1 0,400 → 0,667, DP 1→2 ve
            # YENİ YANLIŞ POZİTİF YOK. Vetoyu tamamen kaldırmak da denendi
            # (F1 0,571) ama o, 2.000'i bulamadığı yerde 10.000 ÜRETİYOR —
            # sessiz kalmayı yanlış sayıyla takas ediyor. Bu depoda yanlış
            # değer, eksik değerden pahalıdır; o yüzden daraltma seçildi.
            # ⚠️ N=3: bu alanın F1'i üç hücreye dayanıyor, tek başına
            # alıntılanmamalı (bkz. docs/HATA_ANALIZI.md).
            "kisi icin",
            # "ÖRNEĞİN 1.000 TL banka kartı harcamanızda 10 TL nakit ödül" —
            # burada veto DOĞRU araç: cümledeki sayıların hiçbiri ödül tutarı
            # değil, ikisi de örneğin parçası.
            "ornegin",
            # "Zümrüt Katılma Hesabı 3 milyon TL ve üzerinde BİRİKİMİ OLAN" —
            # ürünün kendisi ortak tabandaki `MEVDUAT_URUNU` ile eleniyor;
            # bu ek, hesap adı geçmeyen birikim eşiği ifadeleri için.
            "birikimi olan",
        ),
        secim="en_yuksek",
        taban_guven=0.86,
        # Ödül tutarı bir aralığın ucu olarak yazılmaz. "500 TL'ye kadar olan
        # tüm para çekme işlemleri" bir ATM limitidir, ödül değil.
        aralik_ucu_reddet=True,
    ),
    KuralTanimi(
        alan="indirim_orani",
        deger_deseni=D_ORAN,
        ayristirici=oran_ayristir,
        baglam_sozcukleri=("indirim", "iade orani", "avantaj orani"),
        dislayici_sozcukler=("kar payi",),
        veto_ifadeleri=SAYISAL_ALAN_VETOLARI,
        secim="en_yuksek",
        taban_guven=0.88,
        gecerli_aralik=(0.0, 100.1),  # yüzde; %100'den fazla indirim olmaz
    ),
    KuralTanimi(
        alan="alisveris_puani",
        deger_deseni=D_PARA,
        ayristirici=lambda s: para_ayristir(s, birim_zorunlu=True),
        baglam_sozcukleri=("puan", "alisveris puani", "para puan", "chip para"),
        veto_ifadeleri=SAYISAL_ALAN_VETOLARI,
        secim="en_yuksek",
        taban_guven=0.84,
    ),
    KuralTanimi(
        alan="kampanya_bitis",
        deger_deseni=D_TARIH,
        ayristirici=tarih_ayristir,
        baglam_sozcukleri=(
            "son", "bitis", "gecerli", "kadar", "kampanya suresi", "son basvuru",
            # "Kampanya Dönemi: 2 Temmuz - 31 Aralık 2026" — ölçümde kaçırılan
            # 6 tarihin 2'si yalnız bu sözcüğün eksikliğinden düşüyordu.
            "kampanya donemi", "donem", "kampanya tarihleri",
        ),
        # 23 Ağustos ölçümü: geçmiş tarihli 19 kayıttan 3'ü kampanya bitişi
        # DEĞİLDİ; tarih doğru okunmuş ama yönü yanlış yorumlanmıştı:
        #   "10 Mart 2007 tarihinde 26458 numaralı Resmî Gazete" -> mevzuat
        #   "1.3.2021 Tarihinden ÖNCE kullandırılan"             -> tarife sınırı
        #   "16 Haziran 2025 tarihi SONRASINDA"                  -> başlangıç
        # Üçü de "tarih" çevresinde geçtiği için bağlam sözcüğü tutuyordu.
        # Bitiş tarihi "kadar geçerli" der; "önce/sonrasında" başka bir sınırdır.
        dislayici_sozcukler=(
            "resmi gazete", "tarihinden once", "sonrasinda", "yururlu",
        ),
        # Dışlayıcı mesafeye duyarlı olduğu için iki kayıtta yetmedi:
        #   "24 Aya Kadar (1.3.2021 Tarihinden Önce Kullandırılan"
        #   "16 Haziran 2025 tarihi sonrasında müşterimiz olanlar"
        # İkisinde de bağlam sözcüğü ("kadar", "tarih") sayıya daha yakındı.
        # Bitiş tarihi "kadar geçerlidir" der; "önce/sonrasında" başka bir
        # sınırı işaretler ve o sınır kampanyanın bitişi değildir.
        veto_ifadeleri=("tarihinden once", "tarihi sonrasinda"),
        secim="en_yakin",
        taban_guven=0.90,
        # Kalan 4 kaçırma bağlam sözcüğü OLMAYAN çıplak aralıklardı.
        tarih_araligi_sonu_kabul=True,
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
    mesafe: int = 10**6
    """Bu span ile kuralın EN YAKIN bağlam sözcüğü arasındaki uzaklık.

    `guven`'den AYRI tutulur çünkü ikisi farklı soruları cevaplar:

        guven  = "bu alan genelde ne kadar güvenilir" (taban) × yakınlık
        mesafe = "bu SPAN bu alana ne kadar ait" (yalnız kanıt)

    Sahiplik çözümünde (bkz. `_tek_atama`) yalnız `mesafe` kullanılır.
    Güven kullanılamaz: taban güveni yüksek bir alan, bağlam sözcüğü çok
    uzakta olsa bile düşük tabanlı bir alanı yener. Ölçülen örnek —
    «…kâr payı oranı %2,45'ten başlıyor. … Tahsis ücreti %0,75.»

        %0,75 için  kar_payi_orani guven=0,8828  (taban 0,93, sözcük uzak)
        %0,75 için  tahsis_ucreti  guven=0,8415  (taban 0,85, sözcük bitişik)

    Güvene bakan bir sahiplik kuralı span'ı YANLIŞ alana verirdi. Önsel,
    bu span hakkında bir kanıt değildir."""


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
    # BÜYÜK harfler DOĞRUDAN ASCII karşılığına iner — iki adımda değil.
    #
    # `str.translate` metni TEK GEÇİŞTE çevirir: bir karakterin yerine
    # konan şey tabloya tekrar sokulmaz. Önceki sürüm "Ö"yü "ö"ye, ayrı bir
    # satırda da "ö"yü "o"ya eşliyordu; ilk kural uygulandığı için sonuç
    # "ö"de kalıyor, ASCII'ye hiç inmiyordu. Ardından gelen `.lower()` de
    # zaten küçük olan harfi değiştirmiyordu.
    #
    # Sonuç sessiz bir körlüktü: bağlam, dışlayıcı ve veto sözcükleri
    # `arama_anahtari` ile (ASCII'ye inmiş) yazılıyor, metin ise BÜYÜK
    # harfliyse inmemiş hâlde kalıyordu. Banka sayfaları büyük harfli
    # başlıkla dolu ("KULLANDIRILABİLECEK AZAMİ KREDİ TUTARI", "ÖDÜL"),
    # yani eşleşmesi gereken sözcükler eşleşmiyordu.
    #
    # Hepsi 1:1 — uzunluk korunuyor, mesafe hesabı bozulmuyor.
    "IİŞĞÜÖÇÂÎÛ" "ışğüöçâîû",
    "iisguocaiu" "isguocaiu",
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


_HUCRE = re.compile(r"\|")
_RAKAMSAL_HUCRE = re.compile(r"^[\s\d.,%₺]*$")
TABLO_ASGARI_KOLON = 3
"""Bu kadar başlık hücresi görülmeden bir metin parçası tablo sayılmaz."""

TABLO_GUVEN_CARPANI = 0.78
"""Tablo hücresi, düz beyandan DAHA ZAYIF bir kanıttır.

Mesafe skorunun tabanı `0.80 * taban_guven` (bkz. `_baglam_skoru` sonundaki
`yakinlik` formülü), dolayısıyla 0,78 her düz beyanın altında kalır. Sonuç:
`en_yakin` seçen alanlarda cümle içindeki beyan tabloyu her zaman yener.

Neden gerekli: "Alınacak ücretler: 60 ay vadede 500 TL tahsis ücreti" cümlesi
bankanın doğrudan beyanıdır; tablodaki %0,50 aynı bilginin oransal biçimidir.
Etiketleyenler prose beyanı yazdı ve haklılar. Tablo hücrelerine düz
`taban_guven` verildiğinde `tahsis_ucreti` 0,967'den 0,933'e düşmüştü.

Sabit (mesafeye duyarsız) olması bilinçli: tablonun 18. satırı 1. satırından
daha az geçerli değildir. Mesafe kapısı burada uygulansaydı derin satırlar
elenir ve `en_dusuk` seçimi tablonun en düşük oranına ulaşamazdı."""


def _kolon_basligi(metin: str, baslangic: int) -> str | None:
    """Değer bir tablonun hangi kolonunda? O kolonun başlığını döndürür.

    NEDEN GEREKLİ:
        Banka sayfalarındaki oran tabloları düz metne serilince şuna dönüşüyor:

            Vade | Kâr Payı Oranı | Tahsis Ücreti | Aylık Maliyet | ...
             3   |     4,20%      |    0,50%      |    5,77%      | ...

        Karakter penceresine bakan bağlam kontrolü burada çaresiz: "oran"
        sözcüğü `0,50%`'e de `4,20%`'e de aynı uzaklıkta. `kar_payi_orani`
        kuralı `en_dusuk` seçtiği için TAHSİS ÜCRETİ kolonunu kâr payı sanıyordu
        — 15 Ağustos altın set ölçümünde 12 uyuşmazlığın 5'i tam olarak buydu.

        Tabloda anlamı belirleyen şey uzaklık değil, KOLONDUR.

    NASIL:
        Başlıklar ardışık bir "harf içeren hücreler" dizisidir; sayısı kolon
        sayısını verir. Sonraki veri hücreleri o sayıya göre modüler sayılır.
        Satır sonu bilgisi yok — tablo tek satıra serilmiş olabilir.

        Tablo değilse (boru yoksa ya da başlık bulunamazsa) None döner ve
        çağıran taraf eski karakter penceresi mantığına düşer.
    """
    parca = metin[:baslangic]
    hucreler = _HUCRE.split(parca)
    if len(hucreler) < TABLO_ASGARI_KOLON:
        return None

    # Değerden geriye doğru: önce veri hücreleri, sonra başlık koşusu.
    # `hucreler`in SONUNCUSU, değerin kendi hücresinin sol parçasıdır ("… | ")
    # — bir önceki hücre değil. Bu yüzden sayım 1 fazla başlar ve aşağıda
    # `veri - 1` kullanılır; ilk sürümde bu kayma her değeri komşu kolona
    # yazıyordu (kâr payı → tahsis ücreti).
    veri = 0
    i = len(hucreler) - 1
    while i >= 0 and _RAKAMSAL_HUCRE.match(hucreler[i]):
        veri += 1
        i -= 1

    basliklar: list[str] = []
    while i >= 0 and not _RAKAMSAL_HUCRE.match(hucreler[i]):
        basliklar.append(hucreler[i].strip())
        i -= 1
    basliklar.reverse()

    if len(basliklar) < TABLO_ASGARI_KOLON or veri == 0:
        return None
    return basliklar[(veri - 1) % len(basliklar)]


_KARSILASTIRMA = r"[-–—]|<=?|>=?|≤|≥|ile|ila"

_ARALIK_SOLU = re.compile(
    rf"(?:\d[\d.,]*\s*(?:tl|₺|milyon\s*tl|milyon)?|deger)\s*(?:{_KARSILASTIRMA})\s*$",
    re.IGNORECASE,
)
_ARALIK_SAGI = re.compile(
    rf"^\s*(?:tl|₺)?\s*(?:{_KARSILASTIRMA})\s*(?:\d|deger)",
    re.IGNORECASE,
)
_ARALIK_EKI = re.compile(
    # Araya parantezli açıklama girebiliyor: "20.000 TL'ye (yirmi bin Türk
    # Lirasına) kadar olan cep telefonu" — parantezi atlamazsak kaçırırız.
    r"^\s*(?:tl|₺)?\s*(?:milyon\s*tl\s*)?[a-z]{0,4}\s*(?:\([^)]{0,80}\)\s*)?[a-z]{0,4}\s*"
    r"(?:arasi|arasinda|araliginda|uzeri|uzerinde|altinda|ve altinda|"
    r"ust limit|alt limit|kadar olan|fazla olmasi|fazla olan)",
    re.IGNORECASE,
)
_ARALIK_ETIKETI_SOLDA = re.compile(r"(?:ust|alt)\s+limit\s*$", re.IGNORECASE)
"""«üst limit 44.500.000 TL» — etiket sayının SOLUNDA kalır.

`_ARALIK_EKI` yalnız sağa bakar; bu biçim onun aynadaki hâlidir."""
_ORAN_TABLOSU = re.compile(r"deger\s*x\s*\d|kredi[- ]deger oran", re.IGNORECASE)

TARIH_ARALIGI_CARPANI = 0.86
"""Yapısal kanıtla kabul edilen tarihin güven çarpanı.

Sözcükle desteklenen tarihten (0,80–1,00 bandı) bir tık aşağıda: "Kampanya
son başvuru: 31 Aralık" beyanı, çıplak bir tarih aralığından daha güçlü
kanıttır. Ama aralık da gerçek kanıttır, o yüzden tablo hücresi kadar
(0,78) aşağı çekilmez."""

_TIRE = r"[-–—]"

_TARIH_ARALIGI_SOLU = re.compile(
    rf"(?:{_GUN_AY}(?:\s+\d{{4}})?|{_SAYISAL_TARIH})\s*{_TIRE}\s*$",
    re.IGNORECASE,
)
_TARIH_ARALIGI_SAGI = re.compile(
    rf"^\s*{_TIRE}\s*(?:{_GUN_AY}|{_SAYISAL_TARIH})",
    re.IGNORECASE,
)
TARIH_ARALIGI_PENCERESI = 40


def _tarih_araligi_basi_mu(metin: str, bitis: int) -> bool:
    """Bu tarih bir «X - Y» aralığının BAŞI mı? Başıysa bitiş tarihi değildir.

    `_tarih_araligi_sonu_mu`'nun aynadaki hâli ve onunla birlikte zorunlu.
    Tek başına "sonu kabul et" kuralı eklemek yetmiyor:

        "Kampanya Dönemi: 2 Temmuz 2026 - 31 Aralık 2026"

    "kampanya donemi" bağlam sözcüğü İLK tarihe daha yakın olduğu için
    `en_yakin` seçimi başlangıcı seçiyordu — yani bağlam sözcüğü eklemek
    duyarlılığı artırırken kesinliği bozuyordu. Aralığın başını baştan
    aday olmaktan çıkarmak ikisini birden düzeltir.
    """
    return bool(
        _TARIH_ARALIGI_SAGI.match(
            arama_anahtari(metin[bitis : bitis + TARIH_ARALIGI_PENCERESI])
        )
    )


def _tarih_araligi_sonu_mu(metin: str, baslangic: int) -> bool:
    """Bu tarih bir «X - Y» aralığının SONU mu?

    NEDEN GEREKLİ — 16 Ağustos ölçümü, `kampanya_bitis` duyarlılığı 0,571:
        Kaçırılan 6 tarihin hepsi aralıktı ve 4'ünde yakınında hiçbir bağlam
        sözcüğü yoktu — menü metninin ardına düşmüş çıplak bir aralık:

            "... ÜRÜN VE HİZMETLERİMİZ 13 Mart 2026 - 31 Aralık 2026 Vakıf
             Katılım müşterileri ..."

        Sözcük eklemek bunları kurtarmaz çünkü ortada sözcük yok. Kanıt
        YAPISALDIR: iki tarih tire ile bağlanmışsa ikincisi bitiş tarihidir.
        Kampanya metinlerinde bu dizilişin başka anlamı yok.

    Yalnız SOLA bakılır: aralığın SONUNU arıyoruz, başlangıcını değil.
    "13 Mart 2026 - 31 Aralık 2026" ifadesinde 13 Mart'ın solunda tire yok,
    dolayısıyla o kabul edilmez — istenen tam olarak budur.
    """
    sol = metin[max(0, baslangic - TARIH_ARALIGI_PENCERESI) : baslangic]
    return bool(_TARIH_ARALIGI_SOLU.search(arama_anahtari(sol)))


ARALIK_UCU_PENCERESI = 45
"""Aralık işaretini ararken değerin sağına/soluna bakılacak karakter sayısı.

Dar tutuluyor: aralık bağlacı değere BİTİŞİKTİR ("1.200.001 TL – 2.000.000 TL").
Pencere genişlerse tabloda iki satır ötedeki tire de yakalanır ve gerçek
limitler elenmeye başlar."""


def _aralik_ucu_mu(metin: str, baslangic: int, bitis: int) -> bool:
    """Bu sayı bir ARALIĞIN UCU mu, yoksa tek başına bir limit mi?

    NEDEN GEREKLİ — 16 Ağustos ölçümü:
        `finansman_tutari_max` 15 yanlış pozitif üretiyordu ve 8'i tek bir
        hata biçimiydi: sayı bir dilim tablosundan geliyordu.

            "Nihai fatura bedeli 1.200.001 TL – 2.000.000 TL aralığında olan
             taşıt finansmanlarında en fazla 12 ay vade uygulanır."

        Buradaki 2.000.000 TL finansman limiti DEĞİL, vadeyi belirleyen taşıt
        fiyatı dilimidir — metin bunu kendisi söylüyor: "Belirtilen tutarlar
        yalnızca vade süresinin belirlenmesine esas alınmaktadır."

        Bağlam sözcüğü bunu kurtaramaz: cümlede "finansman" geçiyor, hem de
        sayının hemen yanında. Büyüklük sınırı da kurtaramaz — 2 milyon TL
        makul bir taşıt finansmanı limitidir. Ayıran tek şey, sayının bir
        ARALIĞIN UCU olarak yazılmış olmasıdır.

    Konut kredi-değer tabloları da aynı biçimde yakalanır:

        "KULLANDIRILABİLECEK AZAMİ KREDİ TUTARI | Konut Değeri
         Değer <= 5.000.000 TL | Değer x 22.5%"

        Finansman burada bir YÜZDEDİR; 5.000.000 TL konut değeri dilimidir.
    """
    sol = metin[max(0, baslangic - ARALIK_UCU_PENCERESI) : baslangic]
    sag = metin[bitis : bitis + ARALIK_UCU_PENCERESI]
    sol_anahtar = arama_anahtari(sol)
    sag_anahtar = arama_anahtari(sag)

    if _ARALIK_SOLU.search(sol_anahtar) or _ARALIK_SAGI.match(sag_anahtar):
        return True
    if _ARALIK_EKI.match(sag_anahtar) or _ARALIK_ETIKETI_SOLDA.search(sol_anahtar):
        return True
    # Kredi-değer tablosu: finansman yüzdeyle ifade ediliyorsa buradaki mutlak
    # sayılar konut değeri dilimidir.
    return bool(_ORAN_TABLOSU.search(sol_anahtar) or _ORAN_TABLOSU.search(sag_anahtar))


def _baglam_skoru(
    metin: str, kural: KuralTanimi, baslangic: int, bitis: int
) -> tuple[float, int] | None:
    """(güven, mesafe) döner. Bağlam sözcüğü yoksa None (=reddet).

    Mesafe ayrıca döndürülür çünkü SAHİPLİK çözümü onu kullanır: iki alan
    aynı sayıyı sahiplendiğinde kazanan, bağlam sözcüğü daha yakın olandır
    (bkz. `Aday.mesafe`, `_tek_atama`).

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

    # VETO mesafeden ÖNCE gelir: bu ifadeler pencerede geçiyorsa, bağlam
    # sözcüğü sayının ne kadar yakınında olursa olsun değer bu alana ait
    # değildir (bkz. `KuralTanimi.veto_ifadeleri`).
    if any(ifade in pencere for ifade in kural.veto_ifadeleri):
        return None

    # Değer bir tablo hücresindeyse KOLON BAŞLIĞI bir KAPIDIR: yanlış kolonun
    # değeri elenir. Ama puanlamayı devralmaz — eleme sonrası aday yine normal
    # mesafe skorundan geçer.
    #
    # İlk sürüm burada `taban_guven` döndürüp mesafe hesabını atlıyordu ve
    # `en_yakin` seçimi çalışamaz hâle geliyordu: "Alınacak ücretler: 60 ay
    # vadede 500 TL tahsis ücreti" gibi DÜZ BEYAN, tablodaki %0,50 hücresine
    # yeniliyordu. `tahsis_ucreti` doğruluğu 0,967'den 0,933'e düştü.
    # Kolon bilgisi neyin elenmesi gerektiğini söyler, hangisinin seçileceğini
    # değil.
    baslik = _kolon_basligi(metin, baslangic)
    if baslik is not None:
        baslik_anahtari = arama_anahtari(baslik)
        if any(s in baslik_anahtari for s in kural.dislayici_sozcukler):
            return None
        if not any(s in baslik_anahtari for s in kural.baglam_sozcukleri):
            return None  # başka bir kolonun değeri
        # Kolon başlığı hücreyi DOĞRUDAN adlandırır: sahiplik iddiası en güçlü
        # biçimidir, mesafe sıfırdır. (Tablo yolunda çifte sahiplenme zaten
        # oluşmuyor — yanlış kolonun kuralı yukarıda eleniyor.)
        return kural.taban_guven * TABLO_GUVEN_CARPANI, 0

    kapsayici = _en_yakin_uzaklik(pencere, kural.baglam_sozcukleri, hedef)
    if kapsayici is None:
        return None

    dislayici = _en_yakin_uzaklik(pencere, kural.dislayici_sozcukler, hedef)
    if dislayici is not None and dislayici < kapsayici:
        return None

    if kural.olumsuzlama_reddet and _olumsuz_cumle_mi(ham_pencere):
        return None

    yakinlik = max(0.0, 1.0 - kapsayici / (2 * kural.baglam_penceresi))
    return kural.taban_guven * (0.80 + 0.20 * yakinlik), kapsayici


def _veto_var_mi(metin: str, kural: KuralTanimi, baslangic: int, bitis: int) -> bool:
    """Veto ifadesi pencerede geçiyor mu — mesafeye bakılmaz.

    `_baglam_skoru` bunu zaten uyguluyor ama TEK YOLU kapatıyordu: skor None
    dönünce devreye giren "tarih aralığı sonu" yedek yolu vetoyu atlayıp adayı
    kabul ediyordu. 23 Ağustos'ta ölçüldü — "1.3.2021 Tarihinden Önce" tarihi
    veto edilmesine rağmen kampanya bitişi olarak kaydediliyordu, çünkü
    yakınındaki "Kapama-Kalan" tirosu yapıyı aralık sonu gibi gösteriyordu.
    Veto her yolu kapatmalı, yoksa hiçbirini kapatmış sayılmaz.
    """
    if not kural.veto_ifadeleri:
        return False
    if kural.ayni_cumle:
        sol, sag = _cumle_araligi(metin, baslangic, bitis, azami=kural.baglam_penceresi)
    else:
        sol = max(0, baslangic - kural.baglam_penceresi)
        sag = min(len(metin), bitis + kural.baglam_penceresi)
    pencere = _konum_koruyan_anahtar(metin[sol:sag])
    return any(ifade in pencere for ifade in kural.veto_ifadeleri)


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
            sifir_muafiyeti = kural.sifir_gecerli and float(deger) == 0.0
            if not sifir_muafiyeti and not alt < float(deger) < ust:
                continue

        if kural.aralik_ucu_reddet and _aralik_ucu_mu(metin, eslesme.start(), eslesme.end()):
            continue

        if kural.tarih_araligi_sonu_kabul and _tarih_araligi_basi_mu(metin, eslesme.end()):
            continue  # aralığın BAŞI — bitiş tarihi olamaz

        skor = _baglam_skoru(metin, kural, eslesme.start(), eslesme.end())
        if (
            skor is None
            and kural.tarih_araligi_sonu_kabul
            and not _veto_var_mi(metin, kural, eslesme.start(), eslesme.end())
            and _tarih_araligi_sonu_mu(metin, eslesme.start())
        ):
            # Sözcük yok ama YAPI var: "13 Mart 2026 - 31 Aralık 2026".
            # Bağlam sözcüğü olmadığı için sahiplik iddiası ZAYIF: mesafe
            # bilinçli olarak büyük bırakılır, sözcükle desteklenen bir
            # iddiaya karşı kaybetsin.
            skor = (kural.taban_guven * TARIH_ARALIGI_CARPANI, kural.baglam_penceresi)
        if skor is None:
            continue

        guven, mesafe = skor
        adaylar.append(Aday(deger, ham, eslesme.start(), eslesme.end(), guven, mesafe))
    return adaylar


GUVEN_BANDI = 0.15
"""`en_dusuk`/`en_yuksek` seçiminde "yeterince güvenilir" sayılan aralık.

NEDEN 0,05 DEĞİL — aynı tablonun iki hücresi farklı yoldan puanlanıyor:

    Finansman Tutarı | Vade | Aylık Kar Oranı
    250-40.000 TL    | 1-6 ay | 0%       <- tablo yolu:  0,93 * 0,78 = 0,725
    40.001-150.000   | 1-6 ay | 3,95%    <- mesafe yolu: 0,93 * 0,916 = 0,852

Tablo hücresi `TABLO_GUVEN_CARPANI` (0,78) yediği için düz metin gibi
puanlanan bir kardeşiyle asla aynı banda giremez. 0,05'lik bantta 0%
eleniyor, `en_dusuk` 3,95'i seçiyordu — oysa altın set 0 diyor ve haklı:
vade farksız dilim tablonun ilk satırında duruyor.

Ölçüm (16 Ağu, altın set): 0,05 ve 0,10 → `kar_payi_orani` F1 0,737;
0,15'ten itibaren 0,842 ve plato. En küçük kazançlı değer seçildi.

`tahsis_ucreti` ETKİLENMEZ (0,909 sabit): o alan `en_yakin` kullanıyor ve
bu bant yalnız değere göre seçim yapan iki kipe uygulanır. Yani geçen
sürümdeki "düz beyan tabloyu yener" düzeltmesi olduğu gibi duruyor."""


_ALAN_KURALI: dict[str, KuralTanimi] = {k.alan: k for k in KURALLAR}


def deger_makul_mu(
    alan_adi: str, deger: Any, metin: str, baslangic: int, bitis: int
) -> bool:
    """Bu DEĞER bu alana ait olabilir mi? Hangi katmandan geldiği önemsiz.

    NEDEN KURAL KATMANININ DIŞINDA — 16 Ağustos'ta bulunan sızıntı:
        Makullük sınırı, aralık-ucu denetimi ve veto ifadeleri `KuralTanimi`
        üzerinde duruyordu, yani YALNIZ kural katmanına uygulanıyordu.
        Uzlaştırıcıda ise şu satır var:

            if kural is None and llm is not None:
                return llm

        Yani kural katmanı bir değeri elediğinde susuyor, susunca da LLM'in
        değeri filtresiz geçiyor. Eleme, hatayı önlemek yerine hatanın
        kaynağını değiştiriyordu. Ölçülmüş örnek:

            finansman_tutari_max: sistem=66066.24 yontem=llm
            ham_ifade "66.066,24 TL"   <- "Geri Ödenecek Toplam Tutar"

        Kural katmanı için veto yazılmıştı; LLM aynı sayıyı aynı tablodan
        okuyup içeri sokuyordu.

    Bu yüzden denetim ALANIN özelliğidir, kuralın değil: kazanan değer hangi
    katmandan gelirse gelsin aynı kapıdan geçer.

    Konum gerekiyor çünkü aralık-ucu ve veto denetimleri metindeki YERE bakar.
    LLM sayısal değerleri de konum taşır — eleştirmen ajanı ham metinde
    doğruladığı için (`llm.py`, `elestirmen.dogrula` -> `konum`).
    """
    kural = _ALAN_KURALI.get(alan_adi)
    if kural is None:
        return True

    if kural.gecerli_aralik is not None and isinstance(deger, int | float | bool):
        if isinstance(deger, bool):
            return True  # bool alanlarda sayısal aralık anlamsız
        alt, ust = kural.gecerli_aralik
        sifir_muafiyeti = kural.sifir_gecerli and float(deger) == 0.0
        if not sifir_muafiyeti and not alt < float(deger) < ust:
            return False

    if kural.aralik_ucu_reddet and _aralik_ucu_mu(metin, baslangic, bitis):
        return False

    if kural.veto_ifadeleri:
        sol = max(0, baslangic - kural.baglam_penceresi)
        sag = min(len(metin), bitis + kural.baglam_penceresi)
        pencere = _konum_koruyan_anahtar(metin[sol:sag])
        if any(ifade in pencere for ifade in kural.veto_ifadeleri):
            return False

    return True


def _tek_atama(adaylar: dict[str, list[Aday]]) -> dict[str, list[Aday]]:
    """Bir metin parçasını YALNIZ BİR alan sahiplenebilir.

    NEDEN GEREKLİ — ölçülmüş hata (19 Ağustos, jüri tarzı düz metin):

        "…aylık kâr payı oranı %2,45'ten başlıyor. … Tahsis ücreti %0,75."

        kar_payi_orani = 0.75   span=(138,145)
        tahsis_ucreti  = 0.75   span=(138,145)   <- AYNI SPAN
        Doğru cevap %2,45 tümüyle kaçırıldı.

    Her kural metni BAĞIMSIZ tarıyordu ve aynı sayıyı iki alanın birden
    sahiplenmesini engelleyen hiçbir şey yoktu. `kar_payi_orani` kuralı
    `secim="en_dusuk"` olduğu için 2,45 yerine 0,75'i seçiyordu.

    Bu tek kaydın ezberi değil, SINIF hatasıdır: tahsis ücreti gerçek hayatta
    %0,5-1, kâr payı %2-4 seyreder. Yani oranın altında bir ücret yüzdesi
    olan HER düz metinde kâr payı yanlış çıkardı. Tablolarda oluşmuyordu
    (kolon başlığı yanlış kolonu zaten eliyor), ama jüri tablo değil düz
    metin yapıştırır.

    ÇÖZÜM ÖLÇÜTÜ — mesafe, güven DEĞİL:
        Güven, alanın taban güvenini (bir ÖNSEL) içerir ve o önsel bu span
        hakkında bir kanıt değildir. Yukarıdaki metinde `kar_payi_orani`
        %0,75 için 0,8828, `tahsis_ucreti` 0,8415 güven alıyor — güvene
        bakan bir kural span'ı yanlış alana verirdi. Sahiplik, yalnız bu
        span'a ait kanıtla çözülür: hangi alanın bağlam sözcüğü daha yakın.

    Eşitlikte `KURALLAR` bildirim sırası karar verir — keyfi ama
    DETERMİNİSTİK; aynı metin her koşuda aynı sonucu vermelidir.

    Kaybeden alan susmaz: span'ı listesinden düşer ve KALAN adaylarından
    seçim yapar. Yukarıdaki örnekte `kar_payi_orani` böylece %2,45'e ulaşır.
    """
    sira = {kural.alan: i for i, kural in enumerate(KURALLAR)}
    sahipler: dict[tuple[int, int], str] = {}

    for alan, alan_adaylari in adaylar.items():
        for aday in alan_adaylari:
            anahtar = (aday.baslangic, aday.bitis)
            mevcut = sahipler.get(anahtar)
            if mevcut is None:
                sahipler[anahtar] = alan
                continue
            mevcut_aday = next(
                a for a in adaylar[mevcut]
                if (a.baslangic, a.bitis) == anahtar
            )
            if (aday.mesafe, sira[alan]) < (mevcut_aday.mesafe, sira[mevcut]):
                log.debug(
                    "span %s: %s -> %s (mesafe %d < %d)",
                    anahtar, mevcut, alan, aday.mesafe, mevcut_aday.mesafe,
                )
                sahipler[anahtar] = alan

    return {
        alan: [a for a in alan_adaylari if sahipler[(a.baslangic, a.bitis)] == alan]
        for alan, alan_adaylari in adaylar.items()
    }


def _sec(adaylar: list[Aday], secim: Secim) -> Aday | None:
    if not adaylar:
        return None
    if secim == "ilk":
        return adaylar[0]
    if secim == "en_yakin":
        return max(adaylar, key=lambda a: a.guven)
    # Sayısal seçimlerde önce en güvenilir grubu al, sonra değere göre seç
    en_yuksek_guven = max(a.guven for a in adaylar)
    guvenli = [a for a in adaylar if a.guven >= en_yuksek_guven - GUVEN_BANDI]
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

    # ÖNCE tüm kuralların adayları toplanır, SONRA sahiplik çözülür.
    # Kurallar tek tek işlenseydi, bir alanın seçimi diğerinin ne
    # sahiplendiğinden habersiz kalırdı — çifte sahiplenmenin kaynağı buydu.
    tum_adaylar = {kural.alan: _adaylari_bul(metin, kural) for kural in KURALLAR}
    sahiplenilmis = _tek_atama(tum_adaylar)

    for kural in KURALLAR:
        secilen = _sec(sahiplenilmis[kural.alan], kural.secim)
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
            # Birim, değerin YANINDA taşınır. Tek birimli alanlarda sözleşmeden,
            # çok birimlide ham ifadeden çözülür — `birim_belirle` tek yol.
            birim=birim_belirle(secilen.ham_ifade, kural.alan),
        )

    if (masrafsiz := _masrafsizlik(metin, url, cekim_tarihi)) is not None:
        sonuc["masrafsiz_mi"] = masrafsiz

    # SIFIR KÂR PAYI BEYANI — sayısal kural bunu YAPISAL OLARAK bulamaz.
    #
    # `KuralTanimi.sifir_gecerli` docstring'i «"Vade farksız" / "0 kâr payı"
    # kampanyalarında oran gerçekten sıfırdır» diyor ve bayrak açık. Ama o
    # bayrak yalnız SAYIYI aralık denetiminden muaf tutar; "vade farksız"
    # ifadesinde ortada sayı yoktur, `D_ORAN` hiç eşleşmez. Niyet yazılmış,
    # uygulaması eksik kalmıştı.
    #
    # ÖLÇÜLDÜ: altın setin `kar_payi_orani=0` etiketli 3 kaydının 2'si tam
    # bu durumda (üç ayrı etiketleyici bağımsız olarak 0 yazmış). Korpusta
    # ifade **99/590 kayıtta** geçiyor, biri birebir «Kâr payı yok. ... vade
    # farksız destek» diyor — yani bu genel bir örüntü, birkaç kayda özgü değil.
    #
    # SAYISAL ORANA TABİDİR: yalnız kural katmanı sayısal bir oran bulamadığında
    # devreye girer. "Vade farksız 6 taksit" bir sayfada geçip aynı sayfa ayrıca
    # %2,05 ilan ediyorsa kampanyanın oranı %2,05'tir; ifade orada bir alt
    # teklifi anlatıyordur.
    if "kar_payi_orani" not in sonuc:
        if (sifir := _vade_farksiz_orani(metin, url, cekim_tarihi)) is not None:
            sonuc["kar_payi_orani"] = sifir

    # Dilim tablosu, tek tek sayı yakalayan regex kuralından DAHA GÜÇLÜ kanıttır:
    # tabloyu bütün olarak okur ve kılavuzun insana yaptırdığı hesabı (değer ×
    # oran, en büyüğü) yapar. Bu yüzden ürettiğinde `finansman_tutari_max`
    # kuralının sonucunu EZER. Çekimser kaldığında (`tutar is None`) mevcut
    # değere dokunmaz — "bilmiyorum" ile "yanlış" farklı şeylerdir.
    dilim = dilim_tablosundan_azami_finansman(metin)
    if dilim.tutar is not None:
        bas = metin.find(dilim.kanit)
        bit = bas + len(dilim.kanit) if bas >= 0 else 0
        sonuc["finansman_tutari_max"] = Alan(
            deger=dilim.tutar,
            ham_ifade=dilim.kanit,
            kaynak=Kaynak(
                url=url,
                cekim_tarihi=cekim_tarihi,
                alinti=dilim.kanit,
                karakter_baslangic=max(bas, 0),
                karakter_bitis=max(bit, 0),
            ),
            guven=0.85,
            yontem="kural",
            birim=birim_belirle(dilim.kanit, "finansman_tutari_max"),
        )

    return sonuc


_VADE_FARKSIZ = re.compile(
    r"[^.!?\n]{0,80}(?:vade\s*fark[sı]?[ıi]?z"
    r"|vade\s*fark[ıi]\s*(?:olmadan|yok|al[ıi]nma)"
    r"|k[âa]r\s*pay[ıi]\s*(?:yok|al[ıi]nma))[^.!?\n]{0,80}",
    re.IGNORECASE,
)
"""Sıfır kâr payı beyanı — kanıt cümlesiyle birlikte yakalanır.

Üç yazım da aynı şeyi söyler ve üçü de sahada geçiyor: «vade farksız»,
«vade farkı olmadan», «kâr payı yok». Katılım bankacılığında vade farkının
olmaması, kâr payının sıfır olması demektir."""


def _vade_farksiz_orani(metin: str, url: str, cekim_tarihi: datetime) -> Alan | None:
    """«Vade farksız» beyanından `kar_payi_orani = 0` üretir.

    Kanıt, ifadenin geçtiği cümledir — `ham_ifade` olarak saklanır ve
    eleştirmen ajanının birebir metin denetiminden geçer. Yani bu kural da
    kanıtsız değer üretmez; ürettiği kanıt sayı değil, cümledir.

    Güven 0,80: sayısal bir orandan (0,93) düşük, çünkü ifadeden çıkarım
    yapılıyor. LLM aynı sonuca varırsa uzlaştırıcı hibrit'e yükseltir.
    """
    eslesme = _VADE_FARKSIZ.search(metin)
    if eslesme is None:
        return None
    cumle = " ".join(eslesme.group(0).split())
    return Alan(
        deger=0.0,
        ham_ifade=cumle[:120],
        kaynak=Kaynak(
            url=url,
            cekim_tarihi=cekim_tarihi,
            alinti=cumle[:280],
            karakter_baslangic=eslesme.start(),
            karakter_bitis=eslesme.end(),
        ),
        guven=0.80,
        yontem="kural",
        birim=birim_belirle(cumle, "kar_payi_orani"),
    )


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


# ---------------------------------------------------------------------------
# Kampanya türü düzeltmeleri — altın setin yakaladığı iki hata biçimi
# ---------------------------------------------------------------------------
#
# 18 Ağustos 2026 ölçümü: `kampanya_turu` F1 = 0,600 (N=60, altın setteki EN
# BÜYÜK örneklem — yani en güvenilir ve en kötü skor). 24 hatanın 15'i iki
# desende toplanmıştı:
#
#   DESEN 1 (6 vaka) — LLM genel "finansman" diyor, altın set özel alt tür:
#       .../konut-finansmani.aspx   → altın konut_finansmani,  LLM finansman
#       .../tasit-finansmani        → altın tasit_finansmani,  LLM finansman
#       .../ihtiyac-finansmani.aspx → altın ihtiyac_finansmani, LLM finansman
#     Ürün türü URL'de BİREBİR yazıyor ama kimse okumuyordu.
#
#   DESEN 2 (9 vaka) — LLM "alisveris_puani" diyor, altın set başka:
#       .../arzumda-15-indirim         → altın diger  (indirim, puan değil)
#       .../biz-kart-dijital-uyelikler → altın kart
#       .../alisveris-finansmanlari    → altın ihtiyac_finansmani
#     Dokuzunun metninde "puan" kelimesi bile geçmiyordu (biri hariç).
#     Sınıflandırma alanları `KANIT_ZORUNLU_ALANLAR` dışında (bilinçli: enum
#     etiketleri metinde geçmez). Ama `alisveris_puani` istisnadır — ADI bir
#     metin sinyali vaat ediyor. Kanıt yoksa bu etiket verilmemeli.

_URL_TUR_ISARETLERI: tuple[tuple[str, str], ...] = (
    # Sıra önemli: özel olan genel olandan ÖNCE denenir.
    ("konut", "konut_finansmani"),
    ("gayrimenkul", "konut_finansmani"),
    ("mortgage", "konut_finansmani"),
    ("tasit", "tasit_finansmani"),
    ("taşıt", "tasit_finansmani"),
    ("arac", "tasit_finansmani"),
    ("araç", "tasit_finansmani"),
    ("otomobil", "tasit_finansmani"),
    ("ihtiyac", "ihtiyac_finansmani"),
    ("ihtiyaç", "ihtiyac_finansmani"),
    # Finansman dışı kategoriler. Tablo eskiden yalnız finansman alt
    # türlerini tanıyordu; oysa şema `kart` ve `yatirim_urunu` da tanımlıyor
    # ve `llm.TUR_TANIMLARI` bunları zaten anlatıyor. Aynı taksonominin iki
    # yerde farklı yazılması sessiz bir tutarsızlıktı: istem "altın bir
    # yatırım ürünüdür" derken URL tablosu altını hiç tanımıyordu.
    ("kart", "kart"),
    ("altin", "yatirim_urunu"),
    ("altın", "yatirim_urunu"),
    ("yatirim", "yatirim_urunu"),
    ("yatırım", "yatirim_urunu"),
    ("katilim-fonu", "yatirim_urunu"),
    ("katılım-fonu", "yatirim_urunu"),
)
"""URL yol parçasından ürün kategorisi çıkaran işaretler.

TEK TAKSONOMİ, İKİ KULLANIM YERİ: buradaki eşleme `llm.TUR_TANIMLARI`'nda
modele anlatılan sınıflarla AYNI olmak zorundadır. Biri değişip diğeri
kalırsa kural katmanı ile LLM katmanı farklı taksonomilere göre çalışır ve
"iki katman uzlaştı" kararı anlamını yitirir."""

_PUAN_KANITI = re.compile(
    r"\b(puan|mil|chip[- ]?para|world|bonus|para[- ]?puan|maxipuan|bankkart lira)\b",
    re.IGNORECASE,
)


def turu_urlden_cikar(url: str) -> str | None:
    """URL parçasından kampanya kategorisini okur.

    Banka siteleri ürün türünü yol parçasında neredeyse her zaman açıkça
    yazar (`/konut-finansmani`, `/kartlar`). Bu, LLM'in tahminine göre çok
    daha güçlü bir sinyaldir.

    Eskiden yalnız finansman alt türlerini tanıyordu; artık şemanın tanıdığı
    tüm kategorileri kapsıyor (bkz. `_URL_TUR_ISARETLERI`).
    """
    if not url:
        return None
    yol = url.lower()
    for isaret, tur in _URL_TUR_ISARETLERI:
        if isaret in yol:
            return tur
    return None


def puan_kaniti_var_mi(metin: str) -> bool:
    """Metinde alışveriş PUANI iddiasını destekleyen bir kelime var mı?

    "alışveriş" tek başına yetmez — indirim kampanyaları da alışverişle
    ilgilidir. Aranan şey puan/mil/chip gibi somut bir ödül birimi.
    """
    return bool(_PUAN_KANITI.search(metin or ""))


def kampanya_turunu_duzelt(tur: str, url: str, metin: str) -> tuple[str, str | None]:
    """Sınıflandırmayı URL ve metin kanıtıyla düzeltir.

    Döner: (düzeltilmiş_tür, düzeltme_sebebi | None)

    İki müdahale yapar, ikisi de KANITA dayanır:
      1. Genel `finansman` → URL özel alt tür söylüyorsa onu kullan (özelleştirme;
         LLM ile çelişmez, cevabını inceltir).
      2. `alisveris_puani` → metinde puan kanıtı yoksa etiketi düşür; URL bir
         tür söylüyorsa ona, söylemiyorsa `diger`'e in.
    """
    url_turu = turu_urlden_cikar(url)

    if tur == "finansman" and url_turu:
        return url_turu, f"URL alt türü söylüyor ({url_turu})"

    # `diger` de bir SIĞINAK etiketidir, tıpkı genel `finansman` gibi: ikisi de
    # "alt türü bilmiyorum" demektir. Adres bir ürün kategorisi söylüyorsa
    # bilmemek için sebep kalmaz.
    #
    # ÖLÇÜLDÜ (24 Ağu, 60 kayıtlık altın set): `kampanya_turu`'nun 10
    # hatasından **8'i** `X -> diger` yönündeydi ve URL'ler kategoriyi açıkça
    # yazıyordu (`/gayrimenkul-finansmani`, `/kartlar`, `/fiziki-altin`).
    # Yukarıdaki `finansman` kuralıyla aynı gerekçe, aynı kanıt: yol parçası.
    if tur == "diger" and url_turu:
        return url_turu, f"«diger» sığınağı, URL alt türü söylüyor ({url_turu})"

    if tur == "alisveris_puani" and not puan_kaniti_var_mi(metin):
        if "kart" in (url or "").lower():
            return "kart", "puan kanıtı yok, URL 'kart' diyor"
        if url_turu:
            return url_turu, f"puan kanıtı yok, URL '{url_turu}' diyor"
        return "diger", "metinde puan/mil/chip kanıtı yok"

    return tur, None



# ---------------------------------------------------------------------------
# Dilim tablosu ayrıştırıcı — finansman_tutari_max
# ---------------------------------------------------------------------------
#
# NEDEN AYRIŞTIRICI, NEDEN REGEX DEĞİL:
#   18 Ağustos'ta tek bir regex denendi ve BAŞARISIZ oldu: oran işaretini
#   isteğe bağlı (`%?`) bıraktığı için `48` vadesini oran sanıp
#   1.200.000 × %24 = 288.000 gibi değerler üretti. F1'i 0,400 → 0,200
#   düşürdü, geri alındı. Ders: tabloyu tablo olarak ayrıştır, metinde
#   sayı avlama.
#
# İKİ TABLO BİÇİMİ VAR VE ZIT ANLAMA GELİYOR:
#
#   BİÇİM A — taşıt: (araç değeri aralığı, ORAN, vade)
#       0-400.000 TL      %70   48
#       400.001-800.000   %50   36
#     Sayılar ARACIN değeri. `docs/ETIKETLEME_KILAVUZU.md` insana şunu
#     söylüyor: her satır için değer × oran, en büyüğünü al.
#     max(400k×.70, 800k×.50, 1.2M×.30, 2M×.20) = 400.000 — altın setle birebir.
#
#   BİÇİM B — ihtiyaç: (finansman tutarı aralığı, vade)
#       125.000 TL'ye kadar    36 ay
#       250.000 TL ve üzeri    12 ay
#     Sayılar zaten finansman tutarı. Ama en üst dilim SINIRSIZ ("ve üzeri"):
#     azami tutar BİLİNMİYOR. Doğru cevap `None` — uydurmaktan iyidir.
#
# Ayırt edici işaret: satırda AÇIKÇA `%` işaretli bir oran var mı.

_PARA = re.compile(r"(\d{1,3}(?:[.,]\d{3})+|\d{4,})\s*(?:TL|₺)?", re.IGNORECASE)
_ORAN_ISARETLI = re.compile(r"(?:%\s*(\d{1,3})|(\d{1,3})\s*%)")
_SINIRSIZ = re.compile(r"ve\s+üzeri|üzerinde|ve\s+ustu|ve\s+üstü", re.IGNORECASE)
_SATIR_AYIRICI = re.compile(r"[|\n]")
_SATIR_SADECE_YENI_SATIR = re.compile(r"\n")

_ASGARI_FINANSMAN = 10_000.0
"""Bir finansman kampanyası bundan azını duyurmaz — sonuç makullük tabanı."""

_ASGARI_DILIM_TUTARI = 1000.0
"""Bundan küçük sayılar dilim sınırı sayılmaz — tarih, adet, vade gürültüsü."""


@dataclass(frozen=True)
class _DilimSatiri:
    tutarlar: tuple[float, ...]
    oran: float | None
    sinirsiz: bool
    ham: str
    """Satırın BİREBİR metni — kanıt zinciri için.

    `deger` hesaplanmıştır (değer × oran) ve metinde geçmeyebilir; kanıt
    denetimi `ham_ifade`'ye bakar (`schema.kanit_denetimi`). Bu yüzden
    kazanan satırın kendi metni saklanır: hem denetimden geçer hem de
    kullanıcı sayının hangi satırdan çıktığını görür.
    """


def _dilim_satirlarini_ayristir(metin: str) -> list[_DilimSatiri]:
    """Tabloyu satırlara böler — İKİ bölme biçimi denenir.

    NEDEN İKİSİ BİRDEN: aynı tablo iki farklı biçimde geliyor.
        `| 0 TL – 400.000 TL 70% 48 |`   → tutar ve oran AYNI hücrede
        `| 0-400.000 TL | %70 | 48 |`    → tutar ve oran AYRI hücrelerde
    İkincisinde `|` ile bölmek satırı parçalar ve oran sütunu kaybolur;
    tablo oransız sanılıp yanlışlıkla «azami belirsiz» denir. 18 Ağu'da
    `.../tasit-finansmani` tam bu yüzden kaçırıldı.

    Çözüm: her iki bölmeyi de dene, oranlı satırı ÇOK olan yorumu kullan.
    """
    adaylar = [
        _tek_bicimde_ayristir(metin, _SATIR_AYIRICI),
        _tek_bicimde_ayristir(metin, _SATIR_SADECE_YENI_SATIR),
    ]
    return max(adaylar, key=lambda ss: sum(1 for s in ss if s.oran is not None))


def _tek_bicimde_ayristir(metin: str, ayirici: re.Pattern[str]) -> list[_DilimSatiri]:
    satirlar: list[_DilimSatiri] = []
    for ham in ayirici.split(metin or ""):
        parca = ham.strip()
        if not parca or len(parca) > 200:
            continue
        tutarlar = tuple(
            t for p in _PARA.findall(parca)
            if (t := _sayiya_cevir(p)) is not None and t >= _ASGARI_DILIM_TUTARI
        )
        if not tutarlar:
            continue
        m = _ORAN_ISARETLI.search(parca)
        oran = float(m.group(1) or m.group(2)) if m else None
        satirlar.append(
            _DilimSatiri(
                tutarlar=tutarlar,
                oran=oran,
                sinirsiz=bool(_SINIRSIZ.search(parca)),
                ham=parca,
            )
        )
    return satirlar


def _sayiya_cevir(s: str) -> float | None:
    """'400.000' / '1,200,000' -> float. Binlik ayırıcı iki biçimde de gelir."""
    t = re.sub(r"[.,](?=\d{3}\b)", "", s.strip())
    try:
        return float(t)
    except ValueError:
        return None


_KREDIYE_ESAS_DEGER = re.compile(
    r"(kasko|nihai fatura|fatura (?:tutar|değer|bedel)|"
    r"(?:taşıt|araç|konut|teminat) değerine oran|"
    r"değerine oranı|kredi(?:ye)? esas değer|azami (?:finansman|kredi) oran)",
    re.IGNORECASE,
)
"""Tablonun FİNANSMAN tablosu olduğunu gösteren başlık ifadeleri.

NEDEN ŞART: mevduat (günlük/katılma hesabı) kâr payı tablosu, taşıt finansmanı
dilim tablosuyla YAPISAL OLARAK BİREBİR AYNI — ikisi de (tutar aralığı, %, vade).
Yapıya bakarak ayırt edilemez. 18 Ağu'da bu kapı yokken ayrıştırıcı günlük
hesap tablosundan 55.500.000 TL «finansman» üretti. Oranın NE olduğunu ancak
tablo başlığı söyler: finansmanda «taşıt değerine oranı», mevduatta «kâr payı».
"""


@dataclass(frozen=True)
class DilimSonucu:
    """Dilim tablosu ayrıştırma sonucu.

    `kanit`, hesabın çıktığı tablo satırının BİREBİR metnidir. `tutar`
    hesaplanmıştır (değer × oran) ve metinde geçmeyebilir; kanıt denetimi
    `ham_ifade`'ye baktığı için (`schema.kanit_denetimi`) kanıt olarak bu
    satır taşınır — hem denetimden geçer hem de sayının kaynağını gösterir.
    """

    tutar: float | None
    sebep: str
    kanit: str = ""


def dilim_tablosundan_azami_finansman(metin: str) -> DilimSonucu:
    """Dilim tablosundan azami FİNANSMAN tutarını çıkarır.

    `tutar is None` "bu metinden çıkarılamaz" demektir ve bilinçli bir cevaptır.
    """
    if not _KREDIYE_ESAS_DEGER.search(metin or ""):
        return DilimSonucu(None, "finansman tablosu işareti yok (kasko / değerine oranı vb.)")

    satirlar = _dilim_satirlarini_ayristir(metin)
    if len(satirlar) < 2:
        return DilimSonucu(None, "dilim tablosu yok (en az 2 satır gerekir)")

    oranli = [s for s in satirlar if s.oran is not None and 0 < s.oran <= 100]

    # BİÇİM A — oran sütunu var: değer × oran, en büyüğü
    if len(oranli) >= 2:
        eslesme = {max(s.tutarlar) * s.oran / 100.0: s for s in oranli}
        en_buyuk = max(eslesme)
        kazanan = eslesme[en_buyuk].ham
        # Sonuç eşiği: hesabın kendisi doğru olsa da girdi tablo olmayabilir.
        # 1.000 × %1 = 10 TL gibi bir "finansman" gerçek değildir.
        if en_buyuk < _ASGARI_FINANSMAN:
            return DilimSonucu(None, f"hesaplanan tutar makul değil ({en_buyuk:,.0f} TL)")
        return DilimSonucu(en_buyuk, f"biçim A: {len(oranli)} oranlı satır, değer × oran", kazanan)

    # BİÇİM B — oransız: sayılar zaten finansman tutarı
    if any(s.sinirsiz for s in satirlar):
        return DilimSonucu(None, "biçim B: üst dilim sınırsız ('ve üzeri') — azami belirsiz")

    return DilimSonucu(None, "oran sütunu yok ve üst sınır kapalı değil — çıkarılamıyor")
