"""Şema sözleşmesi — DONMUŞ (v1.0.0, 9 Ağustos 2026).

Bu dosya projenin tek doğruluk kaynağıdır. Toplayıcı, çıkarım motoru, depolama,
karşılaştırma ve arayüz bu şemaya karşı çalışır; kimse kimseyi beklemez.

Değiştirmek isteyen: önce takıma duyur, `docs/kararlar/` altına ADR yaz, sürüm
numarasını yükselt. Sessiz değişiklik dört kişinin işini birden bozar.

Temel ilke — KANIT ZİNCİRİ:
    Her alan kendi kanıtını taşır. Bir değer varsa, hangi metin parçasından,
    hangi URL'den, hangi tarihte, hangi yöntemle geldiği de vardır.
    Kanıtsız değer bu sistemde üretilemez.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SEMA_SURUMU = "1.1.0"
"""1.0.0 (9 Ağu) -> 1.1.0 (14 Ağu): `Kampanya.uygunluk` eklendi.

Toplama değişikliği — alan opsiyonel ve `Alan` tipinde olmadığı için mevcut
metrikler, altın set ve depolama etkilenmez. Gerekçe:
`docs/kararlar/006-sema-v1-1-uygunluk.md`"""


# ---------------------------------------------------------------------------
# Sınıflandırma sözlükleri (şartname 5.4)
# ---------------------------------------------------------------------------


class KampanyaTuru(StrEnum):
    """Kampanya türleri — şartname 5.4 tablosundan BİREBİR alınmıştır.

    Şartname "Örnek kampanya türleri aşağıdaki gibi olabilir" diyor, yani liste
    bağlayıcı değil. Yine de birebir uyuyoruz: jüri kendi tablosunu görmek ister
    ve sınıf adlarının şartnameyle örtüşmesi, çıktının doğrudan okunabilir
    olmasını sağlar.

    DIGER şartnamede yok; sınıflandırılamayan metinler için biz ekledik.
    Zorlama sınıflandırma yapmaktansa "diğer" demek daha dürüsttür.
    """

    FINANSMAN = "finansman"                      # Finansman Kampanyası (genel)
    IHTIYAC_FINANSMANI = "ihtiyac_finansmani"    # İhtiyaç Finansmanı Kampanyası
    KONUT_FINANSMANI = "konut_finansmani"        # Konut Finansmanı Kampanyası
    TASIT_FINANSMANI = "tasit_finansmani"        # Taşıt Finansmanı Kampanyası
    KART = "kart"                                # Kart Kampanyası
    ALISVERIS_PUANI = "alisveris_puani"          # Alışveriş Puanı Kampanyası
    YENI_MUSTERI = "yeni_musteri"                # Yeni Müşteri Kampanyası
    YATIRIM_URUNU = "yatirim_urunu"              # Yatırım Ürünü Kampanyası
    DIGER = "diger"


KAMPANYA_TURU_ETIKETLERI: dict[KampanyaTuru, str] = {
    KampanyaTuru.FINANSMAN: "Finansman Kampanyası",
    KampanyaTuru.IHTIYAC_FINANSMANI: "İhtiyaç Finansmanı Kampanyası",
    KampanyaTuru.KONUT_FINANSMANI: "Konut Finansmanı Kampanyası",
    KampanyaTuru.TASIT_FINANSMANI: "Taşıt Finansmanı Kampanyası",
    KampanyaTuru.KART: "Kart Kampanyası",
    KampanyaTuru.ALISVERIS_PUANI: "Alışveriş Puanı Kampanyası",
    KampanyaTuru.YENI_MUSTERI: "Yeni Müşteri Kampanyası",
    KampanyaTuru.YATIRIM_URUNU: "Yatırım Ürünü Kampanyası",
    KampanyaTuru.DIGER: "Diğer",
}
"""Arayüzde ve raporlarda gösterilecek insan-okur adlar (şartname yazımıyla)."""


class HedefKitle(StrEnum):
    """Kampanyanın hedeflediği müşteri kitlesi."""

    YENI_MUSTERI = "yeni_musteri"
    MEVCUT_MUSTERI = "mevcut_musteri"
    MAAS_MUSTERISI = "maas_musterisi"
    SEGMENT = "segment"  # öğrenci, emekli, KOBİ, kadın girişimci vb.
    TUM_MUSTERILER = "tum_musteriler"


class BankaDurumu(StrEnum):
    """BDDK kayıt durumu — faaliyete geçmemiş bankalar da listede tutulur."""

    FAAL = "faal"
    FAALIYETE_GECMEDI = "faaliyete_gecmedi"
    KURULUS_ASAMASINDA = "kurulus_asamasinda"


Yontem = Literal["kural", "llm", "hibrit", "belirtilmemis"]
"""Bir alanın hangi katmandan geldiği. Ablasyon tablosunun veri kaynağı."""


# ---------------------------------------------------------------------------
# Kanıt zinciri
# ---------------------------------------------------------------------------


class Kaynak(BaseModel):
    """Bir değerin geldiği tam metin konumu.

    `alinti`, ham metnin [karakter_baslangic:karakter_bitis] dilimidir. Arayüzde
    kullanıcıya bu alıntı gösterilir; jüri "bu sayı nereden geldi?" diye
    sorduğunda cevap tek tıkla ekrandadır.
    """

    model_config = ConfigDict(frozen=True)

    url: str
    cekim_tarihi: datetime
    alinti: str
    karakter_baslangic: int = Field(ge=0)
    karakter_bitis: int = Field(ge=0)

    @model_validator(mode="after")
    def _aralik_tutarli(self) -> Kaynak:
        if self.karakter_bitis < self.karakter_baslangic:
            raise ValueError(
                f"karakter_bitis ({self.karakter_bitis}) < "
                f"karakter_baslangic ({self.karakter_baslangic})"
            )
        return self


class Alan(BaseModel):
    """Tek bir çıkarılmış alan — değer + kanıt + güven + yöntem.

    Alan bulunamadıysa `Alan.yok()` kullanılır: değer None olur ama nesne
    yine de vardır ve `yontem="belirtilmemis"` işaretlenir. Şartnamenin örnek
    tablosu (madde 11) "Belirtilmemiş" ifadesini kullanıyor; jüri bunu birebir
    görmek isteyecek. Bu yüzden alanı hiç üretmemek değil, yokluğunu açıkça
    beyan etmek doğrudur.
    """

    deger: Any | None = None
    ham_ifade: str | None = None  # metinde geçtiği hâli: "%1,89", "120 aya kadar"
    kaynak: Kaynak | None = None
    guven: float = Field(default=0.0, ge=0.0, le=1.0)
    yontem: Yontem = "belirtilmemis"

    @model_validator(mode="after")
    def _kanit_zinciri(self) -> Alan:
        """Değer varsa yöntem 'belirtilmemis' olamaz — kanıtsız değer yasak."""
        if self.deger is not None and self.yontem == "belirtilmemis":
            raise ValueError(
                "Değer üretilmiş ama yöntem 'belirtilmemis'. Her değer hangi "
                "katmandan geldiğini beyan etmek zorundadır."
            )
        return self

    @classmethod
    def yok(cls) -> Alan:
        """Metinde bulunamayan alan. Arayüzde 'Belirtilmemiş' olarak görünür."""
        return cls(deger=None, ham_ifade=None, kaynak=None, guven=0.0, yontem="belirtilmemis")

    @property
    def var_mi(self) -> bool:
        return self.deger is not None

    def goster(self) -> str:
        """Arayüz ve rapor çıktısı için insan-okur gösterim."""
        if not self.var_mi:
            return "Belirtilmemiş"
        return self.ham_ifade or str(self.deger)


# ---------------------------------------------------------------------------
# Uygunluk koşulları (v1.1.0) — muhakeme ajanının girdisi
# ---------------------------------------------------------------------------


class UygunlukKosullari(BaseModel):
    """Bir kampanyanın KİME ve HANGİ KOŞULLARDA uygulanabileceği.

    Muhakeme ajanı, müşteri profilini bu yapıya karşı çözer. Serbest metin
    `kampanya_kosullari` ile eşleştirme yapılamaz — "yeni müşteri VE 500.000 TL
    üstü VE 60 ay altı" gibi kesişen kısıtlar yapısal alan ister.

    HEDEF KİTLE İÇİN NEDEN YENİ BİR SÖZLÜK YOK:
        `musteri_tipi` mevcut `HedefKitle` enum'unu yeniden kullanır. Aynı kavram
        için ikinci bir sözcük dağarcığı ("yeni"/"mevcut"/"maas") tanımlamak,
        iki listenin zamanla ayrışmasını garanti ederdi; çıkarım bir tarafı,
        muhakeme diğerini doldurur ve eşleşme sessizce bozulurdu.

        `HedefKitle.SEGMENT` bilinçli olarak geniştir (öğrenci, emekli, KOBİ).
        Emekliye açık bir kampanyayı öğrenciye önermemek için segment ADI
        `segment_detayi` içinde ayrıca tutulur; kısıt çözücü önce enum'a,
        SEGMENT ise ada bakar.

    PARA ALANLARI NEDEN `float`:
        Bu değerler `Alan.deger`'den türetilir ve orada zaten `float`turlar
        (`finansman_tutari_max` vb.); karşılaştırma motoru da `float` ile
        çalışır. `Decimal`e çevirmek, kaynağı `float` olan bir sayıya olmayan
        bir kesinlik atfetmek ve her sınırda dönüşüm borcu yaratmak olurdu.
    """

    musteri_tipi: list[HedefKitle] = Field(default_factory=list)
    segment_detayi: list[str] = Field(default_factory=list)  # "emekli", "öğrenci", "KOBİ"

    min_tutar: float | None = None
    max_tutar: float | None = None
    min_vade_ay: int | None = None
    max_vade_ay: int | None = None

    zorunlu_urun: list[str] = Field(default_factory=list)  # "maaş hesabı", "kredi kartı"
    ek_sartlar: list[str] = Field(default_factory=list)  # yapısallaştırılamayan kalan

    kaynak: Kaynak | None = None

    @model_validator(mode="after")
    def _aralik_tutarli(self) -> UygunlukKosullari:
        """Ters aralık sessizce her kampanyayı elerdi — erken patlaması iyidir."""
        if self.min_tutar is not None and self.max_tutar is not None:
            if self.min_tutar > self.max_tutar:
                raise ValueError(f"min_tutar ({self.min_tutar}) > max_tutar ({self.max_tutar})")
        if self.min_vade_ay is not None and self.max_vade_ay is not None:
            if self.min_vade_ay > self.max_vade_ay:
                raise ValueError(
                    f"min_vade_ay ({self.min_vade_ay}) > max_vade_ay ({self.max_vade_ay})"
                )
        return self

    def kisit_var_mi(self) -> bool:
        """Hiç kısıt yoksa kampanya herkese açıktır — muhakeme bunu ayırt etmeli."""
        return any(
            (
                self.musteri_tipi,
                self.min_tutar is not None,
                self.max_tutar is not None,
                self.min_vade_ay is not None,
                self.max_vade_ay is not None,
                self.zorunlu_urun,
            )
        )


# ---------------------------------------------------------------------------
# Ana kayıt
# ---------------------------------------------------------------------------


class Kampanya(BaseModel):
    """Tek bir kampanyanın kanonik gösterimi (şartname 5.3 + 5.4 + 5.6).

    Sayısal alanlar NORMALİZE edilmiş değerleri tutar (bkz. preprocessing/
    normalizasyon.py). Ham metindeki ifade her zaman `Alan.ham_ifade` içinde
    korunur — normalizasyon hatası olsa bile kanıt kaybolmaz.
    """

    model_config = ConfigDict(use_enum_values=False)

    sema_surumu: str = SEMA_SURUMU

    # --- Kimlik ve köken ---
    banka_adi: str
    banka_kodu: str
    kampanya_id: str
    kaynak_url: str
    cekim_tarihi: datetime

    # --- Sınıflandırma (şartname 5.4) ---
    kampanya_turu: Alan = Field(default_factory=Alan.yok)  # KampanyaTuru
    urun_turu: Alan = Field(default_factory=Alan.yok)  # serbest metin
    hedef_kitle: Alan = Field(default_factory=Alan.yok)  # HedefKitle

    # --- Finansman koşulları (şartname 5.3) ---
    kar_payi_orani: Alan = Field(default_factory=Alan.yok)  # aylık %, float
    finansman_tutari_max: Alan = Field(default_factory=Alan.yok)  # TL, float
    vade_ay_max: Alan = Field(default_factory=Alan.yok)  # ay, int
    taksit_sayisi: Alan = Field(default_factory=Alan.yok)  # int
    tahsis_ucreti: Alan = Field(default_factory=Alan.yok)  # TL veya %, float
    masraf_bilgisi: Alan = Field(default_factory=Alan.yok)  # serbest metin
    masrafsiz_mi: Alan = Field(default_factory=Alan.yok)  # bool

    # --- Kampanya avantajları ---
    odul_miktari: Alan = Field(default_factory=Alan.yok)  # TL, float
    indirim_orani: Alan = Field(default_factory=Alan.yok)  # %, float
    alisveris_puani: Alan = Field(default_factory=Alan.yok)  # TL/puan, float
    kampanya_avantaji: Alan = Field(default_factory=Alan.yok)  # serbest metin
    kampanya_bitis: Alan = Field(default_factory=Alan.yok)  # date
    kampanya_kosullari: Alan = Field(default_factory=Alan.yok)  # serbest metin

    # --- Uygunluk (v1.1.0) — muhakeme ajanının girdisi ---
    uygunluk: UygunlukKosullari | None = None
    """Yapısal uygunluk koşulları. `None` = henüz çıkarılmadı (eski kayıtlar).

    DONMUŞ SÖZLEŞMEYİ NEDEN BOZMUYOR — bu alan bilinçle `Alan` DEĞİL:
        `ALAN_ADLARI` yalnız `annotation is Alan` olanları toplar, `cikarilan_
        alanlar()` da `isinstance(deger, Alan)` filtreler. Farklı tipte
        opsiyonel bir alan eklemek bu iki türetmeyi de değiştirmez; dolayısıyla
        `doluluk_orani()`, `ortalama_guven()`, `kanit_denetimi()` ve altın set
        CSV başlıkları (`tools/altin_set.py: csv_basliklari()`) aynen kalır.
        Etiketlenmiş altın set yeniden etiketlenmez.

        Bu, sürümün 2.0.0 değil 1.1.0 olmasının sebebidir: toplama değişikliği,
        kırıcı değil.
    """

    # --- Köken metni ---
    ham_metin: str = ""

    # -- Yardımcılar ------------------------------------------------------

    @field_validator("banka_kodu")
    @classmethod
    def _kod_bicimi(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("banka_kodu boş olamaz")
        return v.strip()

    @classmethod
    def kimlik_uret(cls, banka_kodu: str, kaynak_url: str) -> str:
        """URL + banka kodundan deterministik kampanya kimliği.

        Deterministik olması şart: aynı sayfa tekrar çekildiğinde aynı kimlik
        üretilmeli ki yinelenen kayıt oluşmasın ve altın set etiketleri
        yeni çekimlerde de eşleşsin.
        """
        ozet = hashlib.sha1(f"{banka_kodu}|{kaynak_url}".encode()).hexdigest()[:12]
        return f"{banka_kodu}-{ozet}"

    def cikarilan_alanlar(self) -> dict[str, Alan]:
        """Yalnızca Alan tipindeki nitelikler — metrik hesabının girdisi."""
        return {ad: deger for ad, deger in self if isinstance(deger, Alan)}

    def doluluk_orani(self) -> float:
        """Kaç alan gerçekten bulunmuş? Veri kalitesi raporunun ana göstergesi."""
        alanlar = self.cikarilan_alanlar()
        if not alanlar:
            return 0.0
        return sum(1 for a in alanlar.values() if a.var_mi) / len(alanlar)

    def ortalama_guven(self) -> float:
        dolu = [a.guven for a in self.cikarilan_alanlar().values() if a.var_mi]
        return sum(dolu) / len(dolu) if dolu else 0.0

    def kanit_denetimi(self) -> list[str]:
        """Halüsinasyon denetimi — uydurulmuş değerleri bulur.

        `make eval` halüsinasyon oranını bu fonksiyonla ölçer, dolayısıyla
        NEYİN ihlal sayıldığı doğrudan puanlanan bir metriği etkiler. Üç ayrı
        alan sınıfına üç ayrı ölçüt uygulanır:

        1. KANIT_ZORUNLU_ALANLAR (sayısal + tarihsel): `ham_ifade` ham metinde
           birebir geçmek zorundadır. Bir oran veya tutar uydurulamaz.
        2. Sınıflandırma alanları (kampanya_turu, hedef_kitle): bunlar enum
           etiketidir, metinde geçmeleri BEKLENMEZ. "konut_finansmani" etiketi
           metinde aranmaz — geçerlilik zaten enum kısıtıyla garanti.
        3. Serbest metin alanları (avantaj, koşullar): model özetleyebilir,
           birebir kopyalaması gerekmez. Ama ÖZETİN İÇİNDEKİ SAYILAR metinde
           bulunmak zorundadır — gerçek halüsinasyon burada görünür
           ("48 aya varan" diyorsa metinde 48 geçmeli).

        Bu ayrımı yapmamak, sınıflandırma etiketlerini ve meşru özetleri
        halüsinasyon sayıp kendi metriğimizi hatalı biçimde kötü gösterirdi.
        """
        ihlaller: list[str] = []
        metin = self.ham_metin

        for ad, alan in self.cikarilan_alanlar().items():
            if not alan.var_mi or not alan.ham_ifade:
                continue

            if ad in KANIT_ZORUNLU_ALANLAR:
                if alan.ham_ifade not in metin:
                    ihlaller.append(f"{ad}: ham_ifade metinde yok → {alan.ham_ifade!r}")
            elif ad in METINSEL_ALANLAR:
                for sayi in _SAYI_BUL(str(alan.deger)):
                    if sayi not in metin:
                        ihlaller.append(
                            f"{ad}: özette geçen {sayi!r} sayısı ham metinde yok"
                        )

            if alan.kaynak and alan.kaynak.alinti and alan.kaynak.alinti not in metin:
                ihlaller.append(f"{ad}: alıntı metinde yok → {alan.kaynak.alinti[:60]!r}")

        return ihlaller


class Banka(BaseModel):
    """banks.yaml kayıt defterindeki tek banka (şartname 5.1)."""

    kod: str
    ad: str
    kisa_ad: str = ""
    site: str = ""
    durum: BankaDurumu = BankaDurumu.FAAL
    kod_dogrulandi: bool = False
    seed_urls: list[str] = Field(default_factory=list)
    url_desenleri: list[str] = Field(default_factory=list)
    robots_kontrol: bool = True
    not_: str | None = Field(default=None, alias="not")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def _kisa_ad_varsayilan(self) -> Banka:
        if not self.kisa_ad:
            object.__setattr__(self, "kisa_ad", self.ad.replace(" A.Ş.", "").strip())
        return self

    @property
    def kampanya_beklenir_mi(self) -> bool:
        """Faaliyete geçmemiş bankanın sitesinde kampanya olmaz — eksik sayılmaz."""
        return self.durum == BankaDurumu.FAAL


class HamKayit(BaseModel):
    """Toplayıcının diske yazdığı ham anlık görüntü (Katman 0 çıktısı)."""

    banka_kodu: str
    banka_adi: str
    url: str
    cekim_tarihi: datetime
    http_durum: int
    baslik: str | None = None
    ham_html: str = ""
    govde_metin: str = ""

    def kampanya_id(self) -> str:
        return Kampanya.kimlik_uret(self.banka_kodu, self.url)


# Alan adlarını tek yerden servis et (istem şablonu ve metrikler kullanır)
ALAN_ADLARI: tuple[str, ...] = tuple(
    ad
    for ad, alan in Kampanya.model_fields.items()
    if alan.annotation is Alan
)

SAYISAL_ALANLAR: tuple[str, ...] = (
    "kar_payi_orani",
    "finansman_tutari_max",
    "vade_ay_max",
    "taksit_sayisi",
    "tahsis_ucreti",
    "odul_miktari",
    "indirim_orani",
    "alisveris_puani",
)
"""Sayısal alanlar: metrikte 'normalize değer doğruluğu' ile ölçülür (hedef ≥0,90).
Chatbot'ta bu alanlar ASLA RAG'dan gelmez, yalnız yapısal veriden gelir."""

METINSEL_ALANLAR: tuple[str, ...] = (
    "urun_turu",
    "masraf_bilgisi",
    "kampanya_avantaji",
    "kampanya_kosullari",
)
"""Metinsel alanlar: alan bazlı F1 ile ölçülür (hedef ≥0,78)."""

KANIT_ZORUNLU_ALANLAR: frozenset[str] = frozenset(SAYISAL_ALANLAR) | {"kampanya_bitis"}
"""Değerin ham metinde BİREBİR geçmesi zorunlu olan alanlar.

Sınıflandırma alanları (kampanya_turu, hedef_kitle) bilinçli olarak DIŞARIDA:
onlar enum etiketidir, metinde geçmeleri beklenmez. `masrafsiz_mi` de dışarıda,
çünkü "masraf alınmaz" cümlesinden çıkarılan bir bool'dur.
"""

AYLIK_KAR_PAYI_UST_SINIRI = 15.0
"""Aylık kâr payı oranı için makul üst sınır (yüzde).

Katılım bankacılığında aylık kâr payı tek haneli yüzdelerde seyreder; %15'in
üstü aylık oran DEĞİLDİR. Çıkarımda "%80'e varan indirim" gibi ifadelerin
`kar_payi_orani` alanına düşmesi gerçek bir hata biçimi — 14 Ağustos'ta
veritabanında 84,93'e kadar değerler ölçüldü.

Sınırın işi değeri düzeltmek değil, ondan HESAP YAPILMASINI engellemek:
saçma bir orandan üretilen taksit tutarı, kendinden emin biçimde sunulduğunda
"Belirtilmemiş" demekten çok daha zararlıdır. Aynı sınır altın set
denetleyicisinde de kullanılır (`tools/altin_set.py`)."""

AYLIK_KAR_PAYI_ALT_SINIRI = 0.10
"""Aylık kâr payı oranı için makul ALT sınır (yüzde).

Üst sınırın ikizi. 15 Ağustos ölçümünde bir kayıtta `kar_payi_orani = %0,05`
görüldü; kaynağı bir ücret tarifesi tablosuydu:

    Giden Fon Transferi | USD | 25 | % 0.05 | 5000

Bu bir havale komisyonu oranıdır, finansman kâr payı değil. Aylık kâr payı
binde beş olmaz; olsaydı bile "en düşük kâr payı" sıralamasının tepesine
oturup tüm karşılaştırmayı bozardı — nitekim bozuyordu."""

EN_AZ_FINANSMAN_TUTARI = 5_000.0
"""`finansman_tutari_max` için makul alt sınır (TL).

15 Ağustos ölçümü: dolu 31 kaydın 8'i finansman limiti DEĞİLDİ. Yakalananlar
harcama eşiği, ödül tavanı ve tablo hücreleriydi:

    "1.000 TL ve üzeri harcamanıza"        -> kampanya eşiği
    "günlük maksimum 100 TL"               -> ödül tavanı
    "100 TL'lik katkı payı ... 120 TL"     -> emeklilik katkısı
    "2.500 TL'ye kadar ... kâr payı işletilmez" -> yedek hesap limiti

Bağlam kontrolü bunları kurtarmaz: hepsinin yakınında "finansman" ya da
"limit" sözcüğü geçiyor. Ayıran tek şey büyüklük — hiçbir katılım bankası
1.000 TL finansman kampanyası yapmaz. Üst sınır KONULMADI: kurumsal
finansmanda yüz milyonlu limitler gerçektir (Ziraat Katılım: 150.000.000 TL)."""

_SAYI_DESENI_DENETIM = re.compile(r"\d[\d.,]*\d|\d")


def _SAYI_BUL(metin: str) -> list[str]:
    """Bir özetin içindeki sayıları döndürür — halüsinasyon denetimi için.

    Tek haneli sayılar atlanır: madde numarası, "1 yıl" gibi ifadelerde gürültü
    üretir ve gerçek halüsinasyon riski taşımaz.
    """
    return [
        e.group(0).strip(".,")
        for e in _SAYI_DESENI_DENETIM.finditer(metin)
        if len(e.group(0).strip(".,")) > 1
    ]


def ollama_json_semasi() -> dict[str, Any]:
    """LLM katmanına verilecek JSON Schema — Ollama `format` parametresi.

    Kısıtlı üretim, şema geçerliliğini 1,00 yapar. Kampanya modelinin tamamını
    değil, LLM'in üretmesi gereken düz alanları isteriz; kanıt zinciri (kaynak,
    güven, yöntem) LLM'e bırakılmaz, uzlaştırıcı tarafından kod ile eklenir.
    """
    return {
        "type": "object",
        "properties": {
            "kampanya_turu": {
                "type": "string",
                "enum": [t.value for t in KampanyaTuru],
            },
            "urun_turu": {"type": ["string", "null"]},
            "hedef_kitle": {
                "type": ["string", "null"],
                "enum": [h.value for h in HedefKitle] + [None],
            },
            "kar_payi_orani": {"type": ["string", "null"]},
            "finansman_tutari_max": {"type": ["string", "null"]},
            "vade_ay_max": {"type": ["string", "null"]},
            "taksit_sayisi": {"type": ["string", "null"]},
            "tahsis_ucreti": {"type": ["string", "null"]},
            "masraf_bilgisi": {"type": ["string", "null"]},
            "masrafsiz_mi": {"type": ["boolean", "null"]},
            "odul_miktari": {"type": ["string", "null"]},
            "indirim_orani": {"type": ["string", "null"]},
            "alisveris_puani": {"type": ["string", "null"]},
            "kampanya_avantaji": {"type": ["string", "null"]},
            "kampanya_bitis": {"type": ["string", "null"]},
            "kampanya_kosullari": {"type": ["string", "null"]},
        },
        "required": ["kampanya_turu"],
    }


__all__ = [
    "AYLIK_KAR_PAYI_ALT_SINIRI",
    "AYLIK_KAR_PAYI_UST_SINIRI",
    "EN_AZ_FINANSMAN_TUTARI",
    "SEMA_SURUMU",
    "ALAN_ADLARI",
    "SAYISAL_ALANLAR",
    "METINSEL_ALANLAR",
    "Alan",
    "Banka",
    "BankaDurumu",
    "HamKayit",
    "HedefKitle",
    "Kampanya",
    "KampanyaTuru",
    "Kaynak",
    "UygunlukKosullari",
    "Yontem",
    "ollama_json_semasi",
]
