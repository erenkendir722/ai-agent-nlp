"""Uygunluk ajanı — kampanyanın KİME ve HANGİ KOŞULLARDA uygulandığını çıkarır.

Muhakeme ajanı (`src/ajanlar/muhakeme.py`) bir kısıt ÇÖZÜCÜDÜR; çözeceği kısıt
yapısal olmak zorundadır. Şema o yapıyı 14 Ağustos'ta kazandı
(`UygunlukKosullari`, ADR 006) ama DOLDURAN kimse yoktu: 26 Ağustos sabahına
kadar veritabanındaki 1024 kaydın **1024'ünde de** `uygunluk` alanı `None`'dı
ve müşteri profili ekranı her kaydı «uygunluk çıkarılamadı» uyarısıyla
listeliyordu. Bu modül o boşluğu kapatır.

ÜÇ TASARIM KARARI

1. **LLM ÇAĞIRMAZ.** Alanların çoğu zaten çıkarılmış alanların yeniden
   yorumlanmasıdır (`max_tutar` ← `finansman_tutari_max`, `max_vade_ay` ←
   `vade_ay_max`, `musteri_tipi` ← `hedef_kitle`). Zaten kanıtlanmış bir
   değeri ikinci kez modele sormak, yeni bir halüsinasyon yüzeyi açmaktan
   başka bir şey yapmazdı. Kalan üç alan (`min_tutar`, `min_vade_ay`,
   `zorunlu_urun`) kalıp işidir — «en az 100.000 TL», «maaşını bankamızdan
   alan» — ve regex bunu modelden daha ucuz, daha tekrarlanabilir yapar.

2. **KISIT YOKLUĞU DA BİR BULGUDUR.** Metinde hiçbir koşul geçmiyorsa nesne
   yine üretilir ve `kisit_var_mi()` `False` döner: "kampanya herkese açık".
   `None` ise "hiç bakılmadı" demektir. İkisini aynı kutuya koymak, muhakeme
   ajanının dürüstlük kapısını (`veri_eksik`) anlamsızlaştırırdı.

3. **ÇELİŞEN ARALIK YAZILMAZ.** Metinden gelen `min_tutar`, alandan gelen
   `max_tutar`'ı aşıyorsa metinden geleni DÜŞÜRÜRÜZ. `UygunlukKosullari`
   doğrulayıcısı ters aralıkta `ValueError` fırlatıyor; çıkarımın bir kenar
   durumu yüzünden 1024 kayıtlık koşuyu düşürmesi kabul edilemez, ama sessizce
   ters aralık yazmak da kabul edilemez — ikisi arasındaki tek dürüst yol,
   daha zayıf kanıtı (metin kalıbı) bırakmaktır.
"""

from __future__ import annotations

import re
from datetime import datetime

from src.ajanlar.temel import AjanIzi, iz_tut
from src.schema import HedefKitle, Kampanya, Kaynak, UygunlukKosullari

# --- Kalıplar ---------------------------------------------------------------
# Tümü `re.IGNORECASE`; metin normalizasyondan geçmiş gövde metnidir.

_MIN_TUTAR = re.compile(
    r"(?:en az|asgari|minimum|min\.)\s+"
    r"(?P<tutar>[\d.,]+\s*(?:bin|milyon)?\s*(?:TL|₺|Türk\s*Lirası))",
    re.IGNORECASE,
)
"""YALNIZ AÇIK ASGARİ İFADESİ — «X TL ve üzeri» kalıbı bilerek DIŞARIDA.

Ölçüldü (26 Ağu): «üzeri» kalıbı 1024 kayıtta 100 eşleşme veriyordu ve elle
okunan örneklerin çoğu **kademe tablosuydu** — «250.000 TL üzeri ise vade 12
ay», «399.000 TL üstü | 797,68 TL ücret». Bunlar kampanyaya girme koşulu değil,
fiyat/vade kademesidir. Kalıbı bağlam denetimiyle kurtarmaya çalışmak yerine
kaldırdık: bir kampanyanın asgari finansman tutarı gerçekten varsa metinde
«asgari 250 TL» diye yazılıyor."""

_MIN_VADE = re.compile(
    r"(?:en az|asgari|minimum|min\.)\s+(?P<ay>\d{1,3})\s*ay",
    re.IGNORECASE,
)

# Zorunlu ürün: anahtar -> kanonik ad. Kanonik ad muhakemede müşterinin
# `mevcut_urunler` listesiyle karşılaştırılır, o yüzden sade tutuluyor.
_ZORUNLU_URUN: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"maaş(?:ını|ını\s+bankamızdan|\s+hesab)", re.IGNORECASE), "maaş hesabı"),
    (re.compile(r"maaş\s*müşteri", re.IGNORECASE), "maaş hesabı"),
    (re.compile(r"kredi\s*kart", re.IGNORECASE), "kredi kartı"),
    (re.compile(r"otomatik\s*ödeme\s*talimat", re.IGNORECASE), "otomatik ödeme talimatı"),
    (re.compile(r"düzenli\s*ödeme\s*talimat", re.IGNORECASE), "otomatik ödeme talimatı"),
    (re.compile(r"sigorta\s*(?:poliçe|yaptır)", re.IGNORECASE), "sigorta poliçesi"),
    (re.compile(r"katılım\s*hesab|birikim\s*hesab", re.IGNORECASE), "katılım hesabı"),
    (re.compile(r"mobil\s*şube|internet\s*şube|dijital\s*kanal", re.IGNORECASE), "dijital kanal"),
)

_SEGMENT: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"emekli", re.IGNORECASE), "emekli"),
    (re.compile(r"öğrenci|üniversiteli", re.IGNORECASE), "öğrenci"),
    (re.compile(r"\bKOBİ\b|küçük\s+ve\s+orta", re.IGNORECASE), "KOBİ"),
    (re.compile(r"esnaf", re.IGNORECASE), "esnaf"),
    (re.compile(r"çiftçi|tarım\s*müşteri", re.IGNORECASE), "çiftçi"),
    (re.compile(r"kadın\s*girişimci", re.IGNORECASE), "kadın girişimci"),
    (re.compile(r"\bgenç(?:lere|ler)?\b", re.IGNORECASE), "genç"),
)

_YUKUMLULUK = re.compile(
    r"sahip\s+ol|olan\s+müşteri|müşterisi\s+ol|bulunan\s+müşteri|kullanan|kullanıl"
    r"|şartıyla|koşuluyla|kaydıyla|gerekmekte|gereklidir|zorunlu|talimat\s+ver"
    r"|aktif\s+ol|açtır|sahibi\s+ol",
    re.IGNORECASE,
)
"""ZORUNLU ÜRÜN İÇİN YÜKÜMLÜLÜK KANITI ARANIR — ölçülmüş yanlış pozitif.

İlk sürüm ürün adını metinde GÖRMEYİ yeterli saydı ve 1024 kaydın 608'inde
(%59) zorunlu ürün buldu. Oysa bir kredi kartı kampanyasının metninde "kredi
kartı" geçmesi, o kampanyaya girmek için kredi kartı SAHİBİ OLMAK gerektiği
anlamına gelmez. Muhakeme ajanı bu kısıtı gerçek sanıp müşteriyi eler ve
gerekçesini ekrana yazar — yani hata sessiz değil, GÖRÜNÜR biçimde yanlış olur.

Kural: ürün adı, `YUKUMLULUK_PENCERESI` karakterlik pencerede bir yükümlülük
ifadesiyle birlikte geçmelidir. Kanıt yoksa kısıt yoktur."""

_FINANSMAN_BAGLAMI = re.compile(
    r"finansman|kredi\s+kullan|kullandır|taksitlendir|vade", re.IGNORECASE
)
_TUTAR_OLUMSUZ = re.compile(
    r"alışveriş|harcama|işlem|sepet|puan|iade|ücret|komisyon|EFT|havale|bakiye"
    r"|market|akaryakıt|BSMV|masraf|prim|hesap\s+aç",
    re.IGNORECASE,
)
"""«5.000 TL ve üzeri ALIŞVERİŞLERDE» bir finansman alt sınırı DEĞİLDİR.

ÖLÇÜLDÜ (26 Ağu, 1024 kayıt): bağlam denetimi olmadan `min_tutar` 252 kayıtta
doluyordu ve elle okunan ilk 12 eşleşmenin yalnız 2'si gerçek bir finansman alt
sınırıydı; kalanı ücret tarifesi tablosu, harcama eşiği ve kampanya sepet
tutarıydı. Yanlış bir `min_tutar` muhakemede müşteriyi ELER ve gerekçesini
ekrana yazar — yani hata görünür biçimde yanlış olur.

Kural: eşleşmenin çevresinde finansman bağlamı geçmeli, işlem/harcama/ücret
bağlamı GEÇMEMELİ. Kesinliği duyarlılığa tercih ediyoruz; bulunamayan kısıt
«kampanya herkese açık» der, uydurulan kısıt müşteriyi haksız yere eler."""

YUKUMLULUK_PENCERESI = 120

EK_SART_SINIRI = 3
"""Kaç serbest koşul cümlesi taşınır. Sınırsız taşımak `ek_sartlar`'ı
kampanya metninin ikinci bir kopyası hâline getirirdi; muhakeme onu zaten
okumuyor, kullanıcıya gösteriyoruz."""


def _cumle_penceresi(metin: str, bas: int, bit: int, pencere: int = 140) -> tuple[int, int]:
    """Eşleşmeyi içeren makul bir alıntı aralığı — kanıt zinciri için."""
    alt = max(0, bas - pencere)
    ust = min(len(metin), bit + pencere)
    return alt, ust


def _pencere(metin: str, eslesme: re.Match[str], kalip: re.Pattern[str]) -> bool:
    """Eşleşmenin çevresinde `kalip` geçiyor mu — bağlam denetimi."""
    alt = max(0, eslesme.start() - YUKUMLULUK_PENCERESI)
    ust = min(len(metin), eslesme.end() + YUKUMLULUK_PENCERESI)
    return kalip.search(metin[alt:ust]) is not None


def _tutar_coz(parca: str) -> float | None:
    from src.preprocessing.normalizasyon import para_ayristir

    return para_ayristir(parca, birim_zorunlu=False)


def _metin_havuzu(kampanya: Kampanya) -> str:
    """Koşulların arandığı metin.

    Ham metin bilerek EN SONDA: koşullar önce yapısal alanlarda aranır, çünkü
    oradaki metin zaten çıkarımdan geçmiş ve kısa. Ham metin uzun olduğu için
    kalıpların yanlış pozitif üretme ihtimali orada en yüksektir.
    """
    parcalar = [
        kampanya.kampanya_kosullari.ham_ifade or "",
        kampanya.kampanya_avantaji.ham_ifade or "",
        kampanya.ham_metin or "",
    ]
    return "\n".join(p for p in parcalar if p)


def _kaynak_kur(kampanya: Kampanya, metin: str, bas: int, bit: int) -> Kaynak:
    alt, ust = _cumle_penceresi(metin, bas, bit)
    return Kaynak(
        url=kampanya.kaynak_url,
        cekim_tarihi=kampanya.cekim_tarihi or datetime.now(),
        alinti=metin[alt:ust].strip(),
        karakter_baslangic=alt,
        karakter_bitis=ust,
    )


class UygunlukAjani:
    """Kampanya kaydından yapısal uygunluk koşulları türetir. LLM kullanmaz."""

    ad = "uygunluk"
    llm_kullanir = False

    def cikar(self, kampanya: Kampanya) -> UygunlukKosullari:
        metin = _metin_havuzu(kampanya)
        kaynak: Kaynak | None = None

        # --- 1. Çıkarılmış alanlardan türeyenler -------------------------
        musteri_tipi: list[HedefKitle] = []
        hedef = kampanya.hedef_kitle
        if hedef.var_mi:
            try:
                musteri_tipi = [HedefKitle(hedef.deger)]
            except ValueError:  # sözlük dışı değer — sessizce atlanır, uydurulmaz
                musteri_tipi = []
            if hedef.kaynak is not None:
                kaynak = hedef.kaynak

        max_tutar = None
        if kampanya.finansman_tutari_max.var_mi:
            max_tutar = float(kampanya.finansman_tutari_max.deger)
            kaynak = kaynak or kampanya.finansman_tutari_max.kaynak

        max_vade = None
        if kampanya.vade_ay_max.var_mi:
            max_vade = int(kampanya.vade_ay_max.deger)
            kaynak = kaynak or kampanya.vade_ay_max.kaynak

        # --- 2. Metinden çıkanlar ----------------------------------------
        min_tutar = None
        for eslesme in _MIN_TUTAR.finditer(metin):
            if _pencere(metin, eslesme, _TUTAR_OLUMSUZ):
                continue  # harcama eşiği / ücret tarifesi — finansman sınırı değil
            if not _pencere(metin, eslesme, _FINANSMAN_BAGLAMI):
                continue  # neyin alt sınırı olduğu belli değil
            min_tutar = _tutar_coz(eslesme.group("tutar"))
            if min_tutar is not None:
                kaynak = kaynak or _kaynak_kur(kampanya, metin, eslesme.start(), eslesme.end())
                break

        min_vade = None
        eslesme = _MIN_VADE.search(metin)
        if eslesme is not None:
            ay = eslesme.group("ay")
            if ay is not None:
                min_vade = int(ay)
                kaynak = kaynak or _kaynak_kur(kampanya, metin, eslesme.start(), eslesme.end())

        zorunlu_urun: list[str] = []
        for kalip, kanonik in _ZORUNLU_URUN:
            if kanonik in zorunlu_urun:
                continue
            for eslesme in kalip.finditer(metin):
                if _pencere(metin, eslesme, _YUKUMLULUK):
                    zorunlu_urun.append(kanonik)
                    kaynak = kaynak or _kaynak_kur(
                        kampanya, metin, eslesme.start(), eslesme.end()
                    )
                    break

        segment_detayi: list[str] = []
        for kalip, ad in _SEGMENT:
            if ad not in segment_detayi and kalip.search(metin):
                segment_detayi.append(ad)

        # Segment adı bulunduysa ve hedef kitle hiç çıkarılmamışsa, kampanya
        # en azından SEGMENT'e özeldir. Uydurma değil, metnin söylediğidir.
        if segment_detayi and not musteri_tipi:
            musteri_tipi = [HedefKitle.SEGMENT]

        # --- 3. Çelişen aralık: zayıf kanıt düşer ------------------------
        if min_tutar is not None and max_tutar is not None and min_tutar > max_tutar:
            min_tutar = None
        if min_vade is not None and max_vade is not None and min_vade > max_vade:
            min_vade = None

        return UygunlukKosullari(
            musteri_tipi=musteri_tipi,
            segment_detayi=segment_detayi,
            min_tutar=min_tutar,
            max_tutar=max_tutar,
            min_vade_ay=min_vade,
            max_vade_ay=max_vade,
            zorunlu_urun=zorunlu_urun,
            ek_sartlar=_ek_sartlar(kampanya),
            kaynak=kaynak,
        )

    def cikar_izli(self, kampanya: Kampanya) -> tuple[UygunlukKosullari, AjanIzi]:
        """Arayüzün «Ajan izleri» paneli için izli sürüm."""
        with iz_tut(self.ad, llm=False, girdi=kampanya.kampanya_id) as iz:
            kosul = self.cikar(kampanya)
            iz.cikti_ozeti = "kısıt var" if kosul.kisit_var_mi() else "herkese açık"
            iz.karar_gerekcesi = _gerekce(kosul)
        return kosul, iz


def _ek_sartlar(kampanya: Kampanya) -> list[str]:
    """Yapısallaştırılamayan koşul cümleleri — kullanıcıya gösterilir."""
    ham = kampanya.kampanya_kosullari.ham_ifade
    if not ham:
        return []
    cumleler = [c.strip() for c in re.split(r"(?<=[.!?])\s+|\n+", ham) if len(c.strip()) > 15]
    return cumleler[:EK_SART_SINIRI]


def _gerekce(kosul: UygunlukKosullari) -> str:
    if not kosul.kisit_var_mi():
        return "Metinde uygunluk kısıtı bulunamadı — kampanya herkese açık kabul edildi."
    parcalar = []
    if kosul.musteri_tipi:
        parcalar.append("müşteri tipi " + ", ".join(h.value for h in kosul.musteri_tipi))
    if kosul.min_tutar is not None or kosul.max_tutar is not None:
        parcalar.append(
            f"tutar {kosul.min_tutar or 0:,.0f}–{kosul.max_tutar or 0:,.0f} TL".replace(",", ".")
        )
    if kosul.min_vade_ay is not None or kosul.max_vade_ay is not None:
        parcalar.append(f"vade {kosul.min_vade_ay or 0}–{kosul.max_vade_ay or 0} ay")
    if kosul.zorunlu_urun:
        parcalar.append("zorunlu ürün: " + ", ".join(kosul.zorunlu_urun))
    return "Çıkarılan kısıtlar: " + " · ".join(parcalar)


def uygunluk_ekle(kampanya: Kampanya) -> Kampanya:
    """Kampanyaya uygunluk koşullarını yazar ve aynı nesneyi döndürür."""
    kampanya.uygunluk = UygunlukAjani().cikar(kampanya)
    return kampanya
