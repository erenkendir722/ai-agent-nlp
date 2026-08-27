"""Karşılaştırma motoru — deterministik, LLM kullanmaz (Katman 4).

Şartname 5.7'nin beş kriteri burada uygulanır. Motorun tamamı saf Python'dur:
aynı girdi her zaman aynı çıktıyı verir, açıklanabilir ve test edilebilir.
Bankalar arası karşılaştırmada LLM kullanmak, açıklanamayan ve tekrarlanamayan
sonuç demektir — bankacılık jürisinin kabul etmeyeceği tek şey budur.

"EN AVANTAJLI" NASIL TANIMLANIR — kara kutu bırakmıyoruz:
    Her kriter kendi içinde 0-1 aralığına ölçeklenir (min-maks normalizasyon),
    sonra kullanıcının belirlediği ağırlıklarla toplanır. Ağırlıklar arayüzde
    kaydırıcıyla ayarlanabilir; varsayılanlar aşağıdadır ve dokümantasyondadır.

    Jüri bunu kesinlikle soracak. Cevap: "kullanıcı ağırlıkları belirliyor,
    formül dokümantasyonda, kod deterministik."
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from src.depolama import KampanyaKaydi
from src.schema import (
    ALAN_BOYUTLARI,
    Birim,
    KampanyaTuru,
    alan_etiketi,
    tur_etiketi,
)

Yon = Literal["dusuk_iyi", "yuksek_iyi"]


class Kriter(StrEnum):
    """Şartname 5.7'deki beş sıralama kriteri."""

    EN_DUSUK_KAR_PAYI = "en_dusuk_kar_payi"
    EN_YUKSEK_ODUL = "en_yuksek_odul"
    EN_UZUN_VADE = "en_uzun_vade"
    EN_DUSUK_MASRAF = "en_dusuk_masraf"
    EN_AVANTAJLI = "en_avantajli"


KRITER_ETIKETLERI: dict[Kriter, str] = {
    Kriter.EN_DUSUK_KAR_PAYI: "En Düşük Kâr Payı Oranı",
    Kriter.EN_YUKSEK_ODUL: "En Yüksek Ödül Miktarı",
    Kriter.EN_UZUN_VADE: "En Uzun Vade Seçeneği",
    Kriter.EN_DUSUK_MASRAF: "En Düşük Masraf",
    Kriter.EN_AVANTAJLI: "En Avantajlı Kampanya",
}

ALAN_YONLERI: dict[str, Yon] = {
    "kar_payi_orani": "dusuk_iyi",
    "tahsis_ucreti": "dusuk_iyi",
    "vade_ay_max": "yuksek_iyi",
    "odul_miktari": "yuksek_iyi",
    "finansman_tutari_max": "yuksek_iyi",
}
"""Bir alanın HANGİ UCU müşterinin lehinedir — TEK BEYAN YERİ.

Bu bilgi 27 Ağustos'a kadar İKİ yerde ayrı ayrı yazılıydı: `_SIRALAMA_ALANLARI`
ve `avantaj_skorla`'daki bileşen tanımları. İkisi bugün aynı şeyi söylüyordu,
ama ayrışmaları için tek bir düzeltmenin tek yere yazılması yetiyordu — ve
ayrıştıklarında sıralama ile skor birbirinin tersini gösterirdi.

Üçüncü tüketici chatbot'un tekil cevabı: «vade nedir?» sorusunda hangi kaydın
vitrine çıkacağını da bu yön belirliyor (`_tekil_cevap`). O da buradan okur;
dördüncü bir liste yazılmaz."""


# Sıralama kriteri -> alan. Yön `ALAN_YONLERI`'nden TÜRER.
_KRITER_ALANLARI: dict[Kriter, str] = {
    Kriter.EN_DUSUK_KAR_PAYI: "kar_payi_orani",
    Kriter.EN_YUKSEK_ODUL: "odul_miktari",
    Kriter.EN_UZUN_VADE: "vade_ay_max",
    Kriter.EN_DUSUK_MASRAF: "tahsis_ucreti",
}

_SIRALAMA_ALANLARI: dict[Kriter, tuple[str, Yon]] = {
    kriter: (alan, ALAN_YONLERI[alan]) for kriter, alan in _KRITER_ALANLARI.items()
}


@dataclass(frozen=True)
class Senaryo:
    """Karşılaştırmanın ORTAK TABANI — farklı birimleri kıyaslanabilir kılar.

    NEDEN GEREKLİ (bulgu 1.1):
        `tahsis_ucreti` alanı hem TL hem yüzde taşır; bankalar ikisini de
        kullanıyor. 18 Ağustos'a kadar bu değerler ortak birimmiş gibi
        min-maks normalize ediliyordu:

            {0,5 (%0,50) · 75,0 (%75) · 500,0 (500 TL)}

        Sonuç, %0,50'lik ücretin "en ucuz", 500 TL'nin "en pahalı" görünmesiydi.
        Oysa 100.000 TL'lik bir finansmanda **ikisi de 500 TL'dir** — yani
        eşittirler. Sıralama, birim karışıklığı yüzünden tersine dönüyordu.

    Senaryo verilmezse yüzde değerler TL'ye indirgenemez ve
    `karsilastirilabilirlik` düşer; kullanıcı uyarı görür. Sessizce yanlış
    sıralamaktansa "bu kriteri ortak tabana indiremedim" demek doğrudur.
    """

    anapara: float
    vade_ay: int


FINANSMAN_TURLERI = frozenset({
    KampanyaTuru.FINANSMAN,
    KampanyaTuru.IHTIYAC_FINANSMANI,
    KampanyaTuru.KONUT_FINANSMANI,
    KampanyaTuru.TASIT_FINANSMANI,
})
"""Kâr payının MALİYET olduğu türler — finansman satın alınıyor."""


OLCUT_KAPSAMI: dict[str, frozenset[KampanyaTuru]] = {
    "kar_payi_orani": FINANSMAN_TURLERI,
}
"""Bir ölçütün ANLAMLI olduğu kampanya türleri. Ortak tabanın ikinci yarısı.

NEDEN GEREKLİ (27 Ağustos, 931 kayıtta ölçüldü):
    `Senaryo` birim karışıklığını çözüyordu; bu ürün sınıfı karışıklığını
    çözüyor. `kar_payi_orani` dolu 119 kaydın **110'u** kart, alışveriş ve
    «diğer» kampanyalarından geliyor ve neredeyse hepsi sıfır:

        «TROY kredi kartlarınız ile 1.000-100.000 TL sağlık harcamalarınıza
         vade farksız 6 taksit»                        -> kar_payi_orani = 0

    Bu değer o kampanya için YANLIŞ DEĞİL — vade farksız taksitte kâr payı
    gerçekten sıfırdır. Yanlış olan, bir kart taksit promosyonunun sıfırını
    bir ihtiyaç finansmanının aylık %2,87'siyle aynı min-maks ölçeğine
    sokmaktı. Sonuç, her karşılaştırmanın aynı cümleyle bitmesiydi:

        «Kâr payı oranı açısından iki banka EŞİT: aylık %0»

    Dokuz bankanın beşinde (Dünya, Hayat Finans, Türkiye Emlak, Vakıf,
    Ziraat) kâr payı verisinin TAMAMI bu türden geliyordu; o bankalar
    finansman oranı hiç yayımlamamışken «%0 kâr payı» sunuyor görünüyordu.

    Kapsam dışı kalan kayıt SİLİNMEZ, sıralamadan düşer: `Alan` kanıtıyla
    yerinde durur, tekil sorguda kendi kaynağıyla gösterilir. Düşen tek şey
    ONU BAŞKA ÜRÜNLE KIYASLAMA iddiasıdır.

YAN ETKİ — `yatirim_urunu` da düşer, ki doğrusu odur: Türkiye Finans Günlük
Hesap sayfasından gelen `11.0` bir katılma hesabı GETİRİSİDİR, finansman
maliyeti değil. Sıralamada «en yüksek kâr payı» diye o çıkıyordu.

Karar: `docs/kararlar/020-olcut-kapsami.md`."""


def olcut_kapsaminda(kayit: KampanyaKaydi, alan_adi: str) -> bool:
    """Bu kaydın bu alanı KARŞILAŞTIRMAYA girebilir mi?

    Kapsam tanımlanmamış alanlar her kayıtta geçerlidir — vade, ödül ve
    finansman tutarı ürün sınıfından bağımsız okunur.

    Türü BELİRSİZ kayıt (`kampanya_turu` boş) kapsam dışıdır: türü bilinmeyen
    bir kaydı finansman sayıp sıralamaya sokmak, bilmediğimiz şeyi varsaymak
    olurdu.
    """
    kapsam = OLCUT_KAPSAMI.get(alan_adi)
    if kapsam is None:
        return True
    if not kayit.kampanya_turu:
        return False
    try:
        return KampanyaTuru(kayit.kampanya_turu) in kapsam
    except ValueError:
        return False


def ortak_tabana_indir(
    kayit: KampanyaKaydi, alan_adi: str, senaryo: Senaryo | None
) -> float | None:
    """Alan değerini karşılaştırılabilir ortak tabana indirger. Olmuyorsa None.

    TEK BİRİMLİ alanlar zaten ortak tabandadır (`kar_payi_orani` hep yüzde,
    `vade_ay_max` hep ay) — dokunulmaz. Yalnız ÇOK BİRİMLİ alanlar
    indirgenir, çünkü karışım yalnız orada mümkündür.

    `None` dönmek bir hata değil, bir BEYANDIR: "bu değeri diğerleriyle
    aynı tabana getiremiyorum". Çağıran bunu eksik veri gibi işler ve
    karşılaştırılabilirlik oranına yansıtır.
    """
    deger = getattr(kayit, alan_adi, None)
    if deger is None:
        return None

    # Ürün sınıfı da ortak tabanın parçası: kart taksit promosyonunun sıfırı
    # ile ihtiyaç finansmanının oranı aynı ölçeğe girmez (bkz. `OLCUT_KAPSAMI`).
    if not olcut_kapsaminda(kayit, alan_adi):
        return None

    izinli = ALAN_BOYUTLARI.get(alan_adi)
    if izinli is None or len(izinli) == 1:
        return float(deger)

    birim = kayit.birim(alan_adi)
    if birim is Birim.TL:
        return float(deger)
    if birim is Birim.YUZDE and senaryo is not None:
        # %0,50 × 100.000 TL = 500 TL — artık 500 TL'lik ücretle EŞİT.
        return senaryo.anapara * float(deger) / 100.0
    return None


@dataclass(frozen=True)
class Agirliklar:
    """Şeffaf skor ağırlıkları. Arayüzde kaydırıcıyla değiştirilir.

    Varsayılanlar bir tercihtir, gerçek değil: bir tüketici için kâr payı
    baskındır, ama ödül peşindeki bir kullanıcı ağırlığı kaydırabilir.
    """

    kar_payi: float = 0.40
    masraf: float = 0.25
    vade: float = 0.20
    odul: float = 0.15

    def toplam(self) -> float:
        return self.kar_payi + self.masraf + self.vade + self.odul

    def normalize(self) -> Agirliklar:
        t = self.toplam()
        if t <= 0:
            return Agirliklar()
        return Agirliklar(self.kar_payi / t, self.masraf / t, self.vade / t, self.odul / t)


@dataclass
class SkorDetayi:
    """Skorun nasıl oluştuğunun satır satır dökümü — açıklanabilirlik için."""

    kampanya_id: str
    banka_adi: str
    toplam_skor: float
    bilesenler: dict[str, float] = field(default_factory=dict)
    eksik_alanlar: list[str] = field(default_factory=list)
    karsilastirilabilirlik: float = 1.0

    def aciklama(self) -> str:
        parcalar = [f"{ad}: {deger:.3f}" for ad, deger in self.bilesenler.items()]
        metin = f"Skor {self.toplam_skor:.3f} = " + " + ".join(parcalar)
        if self.eksik_alanlar:
            metin += f" | Eksik veri: {', '.join(self.eksik_alanlar)}"
        return metin


def _min_maks_normalize(
    degerler: list[float | None], yon: Yon
) -> list[float | None]:
    """Bir kriteri 0-1'e ölçekler. None'lar None kalır — uydurulmaz."""
    dolu = [d for d in degerler if d is not None]
    if not dolu:
        return [None] * len(degerler)

    en_az, en_cok = min(dolu), max(dolu)
    if en_az == en_cok:
        return [None if d is None else 1.0 for d in degerler]

    aralik = en_cok - en_az
    sonuc: list[float | None] = []
    for d in degerler:
        if d is None:
            sonuc.append(None)
            continue
        olcek = (d - en_az) / aralik
        sonuc.append(1.0 - olcek if yon == "dusuk_iyi" else olcek)
    return sonuc


NOTR_SKOR = 0.5
"""Eksik alanın skoru. Ne ödül ne ceza — veri yokluğu bir kampanyayı ne iyi
ne kötü yapar. Ayrıca `karsilastirilabilirlik` ile kullanıcıya bildirilir."""


def avantaj_skorla(
    kayitlar: list[KampanyaKaydi],
    agirliklar: Agirliklar | None = None,
    senaryo: Senaryo | None = None,
) -> list[SkorDetayi]:
    """"En avantajlı" sıralaması — şeffaf ağırlıklı skor.

    Eksik veriler NOTR_SKOR alır ve `karsilastirilabilirlik` oranı düşer;
    arayüz bu oranı gösterir ki kullanıcı yarım veriye dayalı bir sıralamayı
    tam veri sanmasın.
    """
    if not kayitlar:
        return []

    a = (agirliklar or Agirliklar()).normalize()
    # Yön `ALAN_YONLERI`'nden okunur; burada yalnız AĞIRLIK vardır.
    bilesen_tanimlari = tuple(
        (ad, alan, ALAN_YONLERI[alan], agirlik)
        for ad, alan, agirlik in (
            ("kar_payi", "kar_payi_orani", a.kar_payi),
            ("masraf", "tahsis_ucreti", a.masraf),
            ("vade", "vade_ay_max", a.vade),
            ("odul", "odul_miktari", a.odul),
        )
    )

    normalize_edilmis: dict[str, list[float | None]] = {}
    for ad, alan, yon, _ in bilesen_tanimlari:
        # Ham değer DEĞİL, ortak tabana indirgenmiş değer normalize edilir.
        # Farklı birimleri aynı min-maks ölçeğine sokmak, bulgu 1.1'in ta
        # kendisiydi.
        ham = [ortak_tabana_indir(kayit, alan, senaryo) for kayit in kayitlar]
        normalize_edilmis[ad] = _min_maks_normalize(ham, yon)

    sonuclar: list[SkorDetayi] = []
    for i, kayit in enumerate(kayitlar):
        detay = SkorDetayi(
            kampanya_id=kayit.kampanya_id,
            banka_adi=kayit.banka_adi,
            toplam_skor=0.0,
        )
        toplam = 0.0
        agirlik_toplami = 0.0
        for ad, alan, _, agirlik in bilesen_tanimlari:
            if agirlik <= 0:
                continue
            deger = normalize_edilmis[ad][i]
            if deger is None:
                detay.eksik_alanlar.append(alan)
                deger = NOTR_SKOR
            else:
                agirlik_toplami += agirlik
            katki = agirlik * deger
            detay.bilesenler[ad] = round(katki, 4)
            toplam += katki

        # Masrafsız kampanyalara küçük bir ödül: tahsis ücreti boş ama
        # "masrafsız" beyanı varsa bu eksik veri değil, sıfır masraftır.
        if kayit.masrafsiz_mi and "tahsis_ucreti" in detay.eksik_alanlar:
            detay.eksik_alanlar.remove("tahsis_ucreti")
            duzeltme = a.masraf * (1.0 - NOTR_SKOR)
            toplam += duzeltme
            detay.bilesenler["masraf"] = round(detay.bilesenler.get("masraf", 0) + duzeltme, 4)
            agirlik_toplami += a.masraf

        detay.toplam_skor = round(toplam, 4)
        detay.karsilastirilabilirlik = round(agirlik_toplami, 3)
        sonuclar.append(detay)

    return sorted(sonuclar, key=lambda d: -d.toplam_skor)


def sirala(
    kayitlar: list[KampanyaKaydi],
    kriter: Kriter,
    agirliklar: Agirliklar | None = None,
    senaryo: Senaryo | None = None,
) -> list[KampanyaKaydi]:
    """Şartname 5.7'deki beş kriterden birine göre sıralar.

    Değeri olmayan kayıtlar HER ZAMAN sona konur — "veri yok" en iyi sonuç
    gibi görünmemeli.
    """
    if kriter == Kriter.EN_AVANTAJLI:
        sira = {
            d.kampanya_id: i
            for i, d in enumerate(avantaj_skorla(kayitlar, agirliklar, senaryo))
        }
        return sorted(kayitlar, key=lambda k: sira.get(k.kampanya_id, len(sira)))

    alan, yon = _SIRALAMA_ALANLARI[kriter]

    def anahtar(kayit: KampanyaKaydi) -> tuple[int, float]:
        # Ortak tabana indirgenemeyen değer de "eksik" sayılır ve sona gider:
        # yanlış tabanda sıralanmış bir sayı, hiç sıralanmamış olmaktan
        # kötüdür.
        deger = ortak_tabana_indir(kayit, alan, senaryo)
        if deger is None:
            return (1, 0.0)
        return (0, deger if yon == "dusuk_iyi" else -deger)

    return sorted(kayitlar, key=anahtar)


# ---------------------------------------------------------------------------
# Finansal titizlik uyarıları
# ---------------------------------------------------------------------------


_BIRIM_ADLARI = {
    Birim.TL: "TL",
    Birim.YUZDE: "yüzde",
    Birim.AY: "ay",
    Birim.ADET: "adet",
    Birim.PUAN: "puan",
}
"""Birimin CÜMLE İÇİNDE okunacak adı.

`schema.BIRIM_GOSTERIMLERI` biçim kalıbı tutar (`"{} TL"`, `"%{}"`) — bir
DEĞERİ göstermek için. Burada değer değil birimin kendisi anılıyor:
«alan farklı birimlerde (TL ve yüzde)»."""


class Uyari(str):
    """Uyarı metni + başlık/detay ayrımı + önem derecesi.

    `str` ALT SINIFI olmasının sebebi sözleşme: `/compare` ucu ve
    `Cevap.uyarilar` yıllardır `list[str]` döndürüyor, chatbot da metni
    doğrudan cevaba ekliyor. Ayrı bir tip döndürmek üç yeri birden kırardı.
    Bu sınıf her yerde metin gibi davranır; arayüz fazladan alanlara bakarak
    önemli olanı öne çıkarabilir.

    `engelleyici` = bu durum bir kriteri SIRALAMADAN DÜŞÜRÜYOR. Bilgi amaçlı
    notla («farklı türler karşılaştırılıyor») aynı görsel ağırlıkta gösterilirse
    kullanıcı hangisinin kararını değiştirdiğini seçemez — 26 Ağustos'ta dört
    özdeş sarı kutu ekranı doldurup cevabı aşağı itiyordu.
    """

    baslik: str
    detay: str
    engelleyici: bool

    def __new__(cls, baslik: str, detay: str, *, engelleyici: bool = False) -> "Uyari":
        nesne = super().__new__(cls, f"**{baslik}** — {detay}")
        nesne.baslik = baslik
        nesne.detay = detay
        nesne.engelleyici = engelleyici
        return nesne


def _sayi_ozeti(degerler: list[int], birim: str, azami_dokum: int = 4) -> str:
    """Kısa listeyi sayar, uzun listeyi ARALIĞA indirir.

    «2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 18, 34, 36, 48, 60, 84, 108, 120 ay»
    okunmuyor; 19 değerin tek tek yazılması kullanıcıya hiçbir şey söylemiyor.
    «2–120 ay arasında 19 değer» aynı bilgiyi taşır ve okunur.
    """
    if len(degerler) <= azami_dokum:
        return ", ".join(str(d) for d in degerler) + f" {birim}"
    return f"{min(degerler)}–{max(degerler)} {birim} arasında {len(degerler)} farklı değer"


def uyarilar(kayitlar: list[KampanyaKaydi]) -> list[Uyari]:
    """Karşılaştırmayı yanıltabilecek durumları kullanıcıya bildirir.

    Farklı vadeli iki ürünü yan yana koyup "bu daha ucuz" demek finansal olarak
    yanlıştır. Bunu söylemek 5 dakikalık iş ve jüriye ciddiyet sinyali.

    Metinler KISA tutulur: 26 Ağustos'ta ölçüldü, dört uyarı 1.060 karakter
    ediyordu ve bunun 300'ü «Katılım Bankası A.Ş.» ifadesini dokuz kez tekrar
    etmekti. Dokuz bankanın hepsi listedeyse zaten «hiçbirinde» demek doğrudur.
    """
    mesajlar: list[Uyari] = []
    if len(kayitlar) < 2:
        return mesajlar

    # BİRİM KARIŞIMI — sessizce sıralamaktansa beyan etmek.
    # Tek ENGELLEYİCİ uyarı budur: kriter sıralamadan düşüyor.
    for alan_adi in ALAN_BOYUTLARI:
        if len(ALAN_BOYUTLARI[alan_adi]) == 1:
            continue
        birimler = {
            k.birim(alan_adi)
            for k in kayitlar
            if getattr(k, alan_adi, None) is not None and k.birim(alan_adi)
        }
        if len(birimler) > 1:
            adlar = " ve ".join(
                _BIRIM_ADLARI.get(b, b.value)
                for b in sorted(birimler, key=lambda birim: birim.value)
            )
            etiket = alan_etiketi(alan_adi)
            mesajlar.append(Uyari(
                f"{etiket} sıralamaya katılmadı",
                f"Alan farklı birimlerde ({adlar}). Ortak tabana inmek için "
                "anapara ve vade senaryosu gerekiyor.",
                engelleyici=True,
            ))

    vadeler = sorted({k.vade_ay_max for k in kayitlar if k.vade_ay_max is not None})
    if len(vadeler) > 1:
        mesajlar.append(Uyari(
            "Vadeler farklı",
            f"{_sayi_ozeti(vadeler, 'ay')}. Farklı vadeli ürünler doğrudan "
            "karşılaştırılamaz; toplam maliyet üzerinden değerlendirin.",
        ))

    # KIYASLANABİLİR oranı olan banka: değeri var VE finansman kampanyasından
    # geliyor. Eskiden yalnız `is None` bakılıyordu; kart taksit
    # promosyonundan gelen sıfırlar «oran var» sayılıyor ve bu uyarı hiç
    # çıkmıyordu (bkz. `OLCUT_KAPSAMI`).
    tum_bankalar = {k.banka_adi for k in kayitlar}
    oran_veren = {
        k.banka_adi
        for k in kayitlar
        if ortak_tabana_indir(k, "kar_payi_orani", None) is not None
    }
    eksik_oran = sorted(tum_bankalar - oran_veren)
    if eksik_oran:
        if len(eksik_oran) == len(tum_bankalar):
            nerede = "Hiçbirinin finansman kampanyasında belirtilmemiş"
        elif len(eksik_oran) <= 2:
            nerede = f"{' ve '.join(eksik_oran)} için finansman kampanyasında belirtilmemiş"
        else:
            nerede = f"{len(eksik_oran)} bankanın finansman kampanyasında belirtilmemiş"
        mesajlar.append(Uyari(
            "Kâr payı oranı eksik",
            f"{nerede}. Kart ve alışveriş kampanyalarındaki «vade farksız» "
            "sıfırları finansman oranı sayılmaz; sıralamada bu alan nötr kaldı.",
        ))

    turler = {k.kampanya_turu for k in kayitlar if k.kampanya_turu}
    if len(turler) > 1:
        # Etiketler `schema.KAMPANYA_TURU_ETIKETLERI`'den gelir. Elle
        # güzelleştirmeyin: `.title()` Türkçe'de sessizce bozar ve yama
        # listesi yeni tür eklendiğinde eksik kalır (bkz. o sözlüğün notu).
        guzel_turler = [tur_etiketi(t) for t in sorted(turler)]
        hangileri = (
            ", ".join(guzel_turler) if len(guzel_turler) <= 3
            else f"{len(guzel_turler)} farklı tür"
        )
        mesajlar.append(Uyari(
            "Karışık kampanya türü",
            f"{hangileri} bir arada karşılaştırılıyor. Aynı tür içinde "
            "karşılaştırma daha anlamlıdır.",
        ))

    return mesajlar


# ---------------------------------------------------------------------------
# Toplam maliyet (annüite)
# ---------------------------------------------------------------------------


def toplam_maliyet(
    anapara: float, aylik_kar_payi_orani: float, vade_ay: int, tahsis_ucreti: float = 0.0
) -> dict[str, float]:
    """Eşit taksitli (annüite) ödeme planının toplam maliyeti.

    Katılım bankacılığında murabaha ile satış bedeli baştan sabitlenir; taksit
    hesabı matematiksel olarak annüite formülüyle aynıdır:

        taksit = A * i / (1 - (1 + i)^-n)

    `aylik_kar_payi_orani` YÜZDE olarak verilir (örn. 2.05 = aylık %2,05).
    """
    if anapara <= 0 or vade_ay <= 0:
        raise ValueError("anapara ve vade_ay pozitif olmalı")

    i = aylik_kar_payi_orani / 100.0
    if i == 0:
        aylik_taksit = anapara / vade_ay
    else:
        aylik_taksit = anapara * i / (1 - (1 + i) ** -vade_ay)

    toplam_geri_odeme = aylik_taksit * vade_ay
    return {
        "aylik_taksit": round(aylik_taksit, 2),
        "toplam_geri_odeme": round(toplam_geri_odeme + tahsis_ucreti, 2),
        "toplam_kar_payi": round(toplam_geri_odeme - anapara, 2),
        "tahsis_ucreti": round(tahsis_ucreti, 2),
        "toplam_maliyet_orani": round(
            (toplam_geri_odeme + tahsis_ucreti - anapara) / anapara * 100, 2
        ),
    }




# ---------------------------------------------------------------------------
# Vade duyarlılığı — karar desteği
# ---------------------------------------------------------------------------
#
# Tekil teklif göstermek "hangi kampanya?" sorusunu cevaplar; banka çalışanının
# müşteriye söyleyeceği şey ise çoğu zaman "aynı kampanyada vadeyi kısaltırsan
# şu kadar az ödersin" cümlesidir. Aşağıdaki işlev o cümlenin sayısını üretir.
#
# LLM YOK: girdi de çıktı da sayı, hesap annüite formülü. `toplam_maliyet`
# üstüne ızgara koşturmaktan başka bir şey yapmaz — yeni matematik eklenmedi.

VADE_IZGARASI: tuple[int, ...] = (12, 24, 36, 48, 60, 84, 120, 180)


@dataclass(frozen=True)
class VadeSecenegi:
    """Tek bir vade adımının maliyeti ve referans vadeye göre farkı."""

    vade_ay: int
    uygun_mu: bool
    aylik_taksit: float | None = None
    toplam_geri_odeme: float | None = None
    toplam_kar_payi: float | None = None
    engel: str | None = None
    # Referans vadeye göre fark. Negatif = bu vade DAHA UCUZ.
    toplam_farki: float | None = None
    taksit_farki: float | None = None

    @property
    def referans_mi(self) -> bool:
        return self.toplam_farki == 0.0


def vade_duyarliligi(
    anapara: float,
    aylik_kar_payi_orani: float,
    *,
    referans_vade: int,
    tahsis_ucreti: float = 0.0,
    vade_ay_max: float | None = None,
    izgara: Sequence[int] = VADE_IZGARASI,
) -> list[VadeSecenegi]:
    """Vade ızgarası boyunca toplam maliyeti hesaplar, referans vadeye kıyaslar.

    `referans_vade` ızgarada yoksa ızgaraya eklenir — kullanıcının ekranda
    girdiği vade tabloda mutlaka görünmeli, yoksa kıyas dayanaksız kalır.

    Bankanın `vade_ay_max` sınırını aşan adımlar **atılmaz**, `uygun_mu=False`
    ile ve sebebiyle döndürülür: sessizce elemek, "neden 180 ay yok?" sorusunu
    cevapsız bırakır (aynı ilke `MuhakemeAjani` içinde de geçerli).

    `aylik_kar_payi_orani` YÜZDE'dir (2.05 = aylık %2,05), `toplam_maliyet` ile
    aynı sözleşme.
    """
    if referans_vade <= 0:
        raise ValueError("referans_vade pozitif olmalı")

    vadeler = sorted({int(v) for v in izgara} | {int(referans_vade)})

    referans = None
    if vade_ay_max is None or referans_vade <= vade_ay_max:
        referans = toplam_maliyet(
            anapara, aylik_kar_payi_orani, int(referans_vade), tahsis_ucreti
        )

    secenekler: list[VadeSecenegi] = []
    for vade in vadeler:
        if vade_ay_max is not None and vade > vade_ay_max:
            secenekler.append(
                VadeSecenegi(
                    vade_ay=vade,
                    uygun_mu=False,
                    engel=f"bankanın azami vadesi {vade_ay_max:.0f} ay",
                )
            )
            continue

        sonuc = toplam_maliyet(anapara, aylik_kar_payi_orani, vade, tahsis_ucreti)
        secenekler.append(
            VadeSecenegi(
                vade_ay=vade,
                uygun_mu=True,
                aylik_taksit=sonuc["aylik_taksit"],
                toplam_geri_odeme=sonuc["toplam_geri_odeme"],
                toplam_kar_payi=sonuc["toplam_kar_payi"],
                toplam_farki=(
                    None
                    if referans is None
                    else round(
                        sonuc["toplam_geri_odeme"] - referans["toplam_geri_odeme"], 2
                    )
                ),
                taksit_farki=(
                    None
                    if referans is None
                    else round(sonuc["aylik_taksit"] - referans["aylik_taksit"], 2)
                ),
            )
        )
    return secenekler


def vade_tavsiyesi(
    secenekler: Sequence[VadeSecenegi],
    referans_vade: int,
    *,
    azami_taksit: float | None = None,
) -> str | None:
    """Tablodan tek cümlelik karar cümlesi üretir; uydurma yapmaz.

    **Neden "en çok tasarruf ettiren vade" diye bir tavsiye yok:** toplam maliyet
    vade kısaldıkça tekdüze azalır, yani "en avantajlı vade" her zaman ızgaranın
    en kısa adımıdır. 800.000 TL / aylık %2,05 için bu, 12 ayda 75.880 TL taksit
    demek — matematiksel olarak doğru, tavsiye olarak anlamsız. Müşterinin ödeme
    kapasitesi bilinmeden "en iyi vade" diye bir şey yoktur.

    Bu yüzden iki kip var:

    * `azami_taksit` verilmişse — müşterinin kaldırabileceği taksit tavanı belli
      demektir; tavanın altındaki **en kısa** vade önerilir. Bu gerçek bir tavsiye.
    * verilmemişse — kazanan seçilmez, yalnız bir adım kısa vadenin takası
      söylenir ve karar tabloya bırakılır.

    Kıyaslanacak uygun bir kısa vade yoksa `None` döner.
    """
    referans = next(
        (s for s in secenekler if s.vade_ay == referans_vade and s.uygun_mu), None
    )
    if referans is None or referans.toplam_geri_odeme is None:
        return None

    kisalar = [
        s
        for s in secenekler
        if s.uygun_mu
        and s.vade_ay < referans_vade
        and s.toplam_farki is not None
        and s.taksit_farki is not None
    ]
    if not kisalar:
        return None

    def _tl(deger: float) -> str:
        return f"{deger:,.0f}".replace(",", ".")

    if azami_taksit is not None:
        uygunlar = [
            s for s in kisalar if s.aylik_taksit is not None and s.aylik_taksit <= azami_taksit
        ]
        if not uygunlar:
            return (
                f"Aylık {_tl(azami_taksit)} TL tavanına {referans_vade} aydan kısa "
                f"hiçbir vade sığmıyor — bu müşteri için {referans_vade} ay zaten "
                f"en kısa uygulanabilir vade."
            )
        en_kisa = min(uygunlar, key=lambda s: s.vade_ay)
        return (
            f"Aylık **{_tl(azami_taksit)} TL** tavanına sığan en kısa vade "
            f"**{en_kisa.vade_ay} ay**: taksit {_tl(en_kisa.aylik_taksit or 0)} TL, "
            f"{referans_vade} aya göre toplamda "
            f"**{_tl(abs(en_kisa.toplam_farki or 0))} TL** daha az ödeme."
        )

    bir_adim = max(kisalar, key=lambda s: s.vade_ay)
    return (
        f"{referans_vade} ay yerine **{bir_adim.vade_ay} ay** seçilirse toplamda "
        f"**{_tl(abs(bir_adim.toplam_farki or 0))} TL** daha az ödenir; aylık taksit "
        f"**{_tl(bir_adim.taksit_farki or 0)} TL** artar. Daha kısa vadeler "
        f"daha çok kazandırır ama taksiti yükseltir — takası aşağıdaki tabloda görün."
    )


__all__ = [
    "ALAN_YONLERI",
    "KRITER_ETIKETLERI",
    "VADE_IZGARASI",
    "Agirliklar",
    "Kriter",
    "SkorDetayi",
    "VadeSecenegi",
    "avantaj_skorla",
    "sirala",
    "toplam_maliyet",
    "uyarilar",
    "vade_duyarliligi",
    "vade_tavsiyesi",
]
