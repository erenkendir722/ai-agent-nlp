"""Chatbot — halüsinasyonsuz mimari (Katman 4).

ALTIN KURAL:
    Sayısal cevaplar ASLA RAG'dan gelmez, HER ZAMAN yapısal veriden gelir.
    RAG yalnızca "kampanya koşulları neler?" gibi metinsel sorulara hizmet eder.

Bu tek karar, bankacılık jürisinin en büyük itirazını ("sistem uydurma kâr payı
oranı söyler mi?") baştan yok eder. Cevap: hayır — mimari olarak imkânsız.

Akış:
    Soru -> Niyet Yönlendirici -> {yapısal sorgu | karşılaştırma | RAG | ret}
         -> Cevap Üretimi (yalnız getirilen bağlamla, sıcaklık 0.1)
         -> SAYISAL DOĞRULAMA KALKANI      <- özgün katkımız
         -> Kaynak Ekleme (banka + URL + tarih + yasal uyarı)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum

import httpx as _httpx
import openai as _openai

from src.comparison.karsilastirma import Agirliklar, avantaj_skorla, uyarilar
from src.depolama import KampanyaKaydi, tum_kayitlar
from src.preprocessing.normalizasyon import arama_anahtari
from src.schema import (
    ALAN_ETIKETLERI,
    BIRIM_GOSTERIMLERI,
    SAYISAL_ALANLAR,
    Birim,
    KampanyaTuru,
    alan_etiketi,
    tur_etiketi,
)
from src.vektor_db import IndeksYok, vektor_ara

log = logging.getLogger(__name__)

YASAL_UYARI = "Bağlayıcı teklif niteliği taşımaz."

_SAYI_DESENI = re.compile(r"\d[\d.,]*")
"""Metindeki sayı adayları. Köken denetiminin de, kalkanın da tek tarayıcısı."""


class Niyet(StrEnum):
    TEKIL_SORGU = "tekil_sorgu"
    KARSILASTIRMA = "karsilastirma"
    KOSUL_SORGUSU = "kosul_sorgusu"
    KAPSAM_DISI = "kapsam_disi"


@dataclass
class Kaynakca:
    banka_adi: str
    url: str
    cekim_tarihi: str
    alinti: str = ""


class Koken(StrEnum):
    """Bir cevap parçasındaki sayıların NEREDEN geldiği.

    Kalkan her parçayı kökenine göre farklı ölçütle denetler. Tek bir
    ölçüt dayatmak iki hatayı birden üretiyordu (ölçüldü, 18 Ağustos):

      * ALINTI parçalar yapısal alana karşı denetleniyordu; bankanın kendi
        metnindeki sayı "doğrulanamadı" diye MEŞRU CEVAP ENGELLENİYORDU.
        10 doğal soruda 2 yanlış blok (%20).
      * SISTEM parçalar `dogrulanacak_metin` ile tümüyle MUAF tutuluyordu;
        skor ve ağırlık bölümüne istenen sayı yazılabiliyordu — kalkanın
        kör noktası.

    Köken bilgisi kalkanı gevşetmez, ona eksik olan tip bilgisini verir.
    """

    YAPISAL = "yapisal"
    """Yapısal alandan gelen veri iddiası. Ölçüt: kayıtta birebir karşılığı olmalı."""

    ALINTI = "alinti"
    """Kaynak metinden birebir alınmış parça. Ölçüt: alıntı ham metnin ALT DİZESİ
    olmalı ve parçadaki her sayı alıntının içinde geçmeli."""

    SISTEM = "sistem"
    """Bizim hesabımız (ağırlık, skor). Ölçüt: sayılar `hesap` sözlüğünden
    YENİDEN ÜRETİLEBİLMELİ. Muafiyet değil, farklı bir doğrulama."""

    DUZ = "duz"
    """Sabit bağlaç metni. Sayı İÇEREMEZ — bu kısıt yapıcıda denetlenir."""

    DENETIMSIZ = "denetimsiz"
    """MİRAS YOL — henüz köken tipine geçirilmemiş üretici.

    Kalkan bu parçayı atlar ama SAYAR. Görünmez bir muafiyet yerine ölçülen
    bir borç: `eval` bunu `denetimsiz_parca_orani` olarak raporlar ve hedef
    sıfırdır. `src/rag/chatbot.py` üreticileri bu kökeni kullanamaz
    (`tests/test_kalkan_kokenli.py` denetler)."""


@dataclass(frozen=True)
class CevapParcasi:
    """Cevabın, tek bir kökene sahip en küçük parçası."""

    metin: str
    koken: Koken
    kayit_id: str | None = None
    """ALINTI için ZORUNLU: alıntının hangi kayıttan geldiği."""
    alinti: str = ""
    """ALINTI için ZORUNLU: kaynak metinden alınan ham parça (gösterim
    sarmalayıcısı olmadan). Bütünlük denetimi buna uygulanır."""
    hesap: dict[str, float] | None = None
    """SISTEM için ZORUNLU: metindeki sayıların üretildiği girdiler."""

    def __post_init__(self) -> None:
        """Köken sözleşmesi yapıcıda denetlenir.

        `Alan._kanit_zinciri` ile aynı refleks: eksik kanıtla nesne
        KURULAMAZ. Doğrulamayı çağrı yerine bırakmak, unutulabilir bir
        disiplin olurdu; buraya koymak imkânsız kılar.
        """
        if self.koken is Koken.ALINTI:
            if not self.kayit_id:
                raise ValueError("ALINTI parçası kayit_id taşımak zorundadır")
            if not self.alinti:
                raise ValueError("ALINTI parçası ham alıntıyı taşımak zorundadır")
        if self.koken is Koken.SISTEM and self.hesap is None:
            raise ValueError(
                "SISTEM parçası `hesap` taşımak zorundadır: sayıları yeniden "
                "üretilemeyen bir hesap, denetlenemeyen bir iddiadır"
            )
        if self.koken is Koken.DUZ and _SAYI_DESENI.search(self.metin):
            raise ValueError(
                f"DUZ parçası sayı içeremez: {self.metin[:60]!r}. Sayı taşıyan "
                "metnin kökeni YAPISAL, ALINTI ya da SISTEM olmalıdır."
            )


@dataclass
class Cevap:
    parcalar: list[CevapParcasi] = field(default_factory=list)
    niyet: Niyet = Niyet.KOSUL_SORGUSU
    kaynaklar: list[Kaynakca] = field(default_factory=list)
    kullanilan_kayitlar: list[KampanyaKaydi] = field(default_factory=list)
    uyarilar: list[str] = field(default_factory=list)
    dogrulama_gecti: bool = True
    reddedilen_sayilar: list[str] = field(default_factory=list)

    def __init__(
        self,
        parcalar: list[CevapParcasi] | None = None,
        niyet: Niyet = Niyet.KOSUL_SORGUSU,
        kaynaklar: list[Kaynakca] | None = None,
        kullanilan_kayitlar: list[KampanyaKaydi] | None = None,
        uyarilar: list[str] | None = None,
        dogrulama_gecti: bool = True,
        reddedilen_sayilar: list[str] | None = None,
        *,
        metin: str | None = None,
        dogrulanacak_metin: str | None = None,
    ) -> None:
        """`metin=` / `dogrulanacak_metin=` MİRAS yoldur — bkz. `Koken.DENETIMSIZ`.

        Geçiş sırasında iki sözleşme birlikte yaşar. Miras çağrı, bugünkü
        anlamı BİREBİR korur: denetlenen bölüm YAPISAL, muaf tutulan bölüm
        DENETIMSIZ parça olur. Yani davranış değişmez, ama muafiyet artık
        görünür ve sayılabilir.
        """
        if parcalar is None:
            parcalar = _miras_parcalar(metin or "", dogrulanacak_metin)
        elif metin is not None:
            raise ValueError("`parcalar` ile `metin` birlikte verilemez")

        self.parcalar = parcalar
        self.niyet = niyet
        self.kaynaklar = kaynaklar if kaynaklar is not None else []
        self.kullanilan_kayitlar = (
            kullanilan_kayitlar if kullanilan_kayitlar is not None else []
        )
        self.uyarilar = uyarilar if uyarilar is not None else []
        self.dogrulama_gecti = dogrulama_gecti
        self.reddedilen_sayilar = (
            reddedilen_sayilar if reddedilen_sayilar is not None else []
        )

    @property
    def metin(self) -> str:
        """Gösterilecek tam gövde — parçaların sırayla birleşimi."""
        return "\n".join(p.metin for p in self.parcalar)

    def denetlenecek(self) -> str:
        """MİRAS: kalkanın denetleyeceği bölüm, düz metin olarak.

        Yeni yol `kalkandan_gecir()`. Bu yardımcı, parça sözleşmesine
        geçmemiş çağrı yerleri ve mevcut testler için korunuyor.
        """
        return "\n".join(
            p.metin for p in self.parcalar if p.koken is not Koken.DENETIMSIZ
        )

    def denetimsiz_parca_sayisi(self) -> int:
        """Ölçülen teknik borç: kaç parça hâlâ miras yoldan geliyor."""
        return sum(1 for p in self.parcalar if p.koken is Koken.DENETIMSIZ)

    def tam_metin(self) -> str:
        parcalar = [self.metin]
        if self.uyarilar:
            parcalar.append("\n" + "\n".join(self.uyarilar))
        if self.kaynaklar:
            parcalar.append("\n**Kaynaklar**")
            for k in self.kaynaklar:
                parcalar.append(
                    f"- {k.banka_adi} — {k.url} ({k.cekim_tarihi} tarihinde alınmıştır)"
                )
            parcalar.append(f"\n_{YASAL_UYARI}_")
        return "\n".join(parcalar)


def _miras_parcalar(metin: str, dogrulanacak: str | None) -> list[CevapParcasi]:
    """Miras `metin=` çağrısını parça listesine çevirir. Anlamı KORUR."""
    if not metin:
        return []
    if dogrulanacak is None:
        return [CevapParcasi(metin, Koken.YAPISAL)]
    if not dogrulanacak:
        return [CevapParcasi(metin, Koken.DENETIMSIZ)]
    kalan = metin[len(dogrulanacak):] if metin.startswith(dogrulanacak) else ""
    parcalar = [CevapParcasi(dogrulanacak, Koken.YAPISAL)]
    if kalan.strip():
        parcalar.append(CevapParcasi(kalan, Koken.DENETIMSIZ))
    return parcalar


# ---------------------------------------------------------------------------
# Niyet yönlendirici
# ---------------------------------------------------------------------------

# Not: `arama_anahtari` ı->i, ü->u eşlemesi yaptığı için soru ekinin dört
# biçimi (mi/mı/mu/mü) burada iki varyanta iner. Ünlü uyumunu unutmak,
# "A mı daha iyi?" sorusunu yanlış katmana yönlendirir.
_KARSILASTIRMA_IPUCLARI = (
    "mi daha", "mu daha", "daha avantajli", "daha iyi", "daha uygun", "daha ucuz",
    "hangisi", "hangi banka", "karsilastir", "kiyasla", "en avantajli", "en iyi",
    "en dusuk", "en yuksek", "en uzun", "fark", " vs ", "gore daha",
    # ÇOĞUL banka sorusu korpusun tamamına sorulur, tek kayda değil:
    # «masrafsız kampanya sunan bankalar hangileri?» tekil sorguya
    # düşüyordu ve tek bankanın verisiyle cevaplanıyordu (25 Ağu, S-10).
    "bankalar hangi", "hangi bankalar", "bankalari hangi", "hangi bankalarin",
)
_KOSUL_IPUCLARI = (
    "kosul", "sart", "nasil", "kimler", "gerekli", "basvuru", "uygun mu",
    "kapsam", "gecerli mi", "detay",
)
_TEKIL_IPUCLARI = (
    "oran", "kar payi", "vade", "tutar", "limit", "masraf", "ucret", "ne kadar",
    "kac", "odul", "indirim", "taksit",
    # `kampanya_bitis` YAPISAL bir alan; «ne zaman bitiyor?» sorusu metin
    # aramasına değil o alana gitmeli. Eksikti (25 Ağu, S-10).
    "ne zaman", "bitis", "bitiyor", "sona er", "gecerlilik", "son tarih",
)
_TAHMIN_IPUCLARI = (
    "ne olacak", "nasil olacak", "olacak mi", "tahmin", "ongoru", "ongoru",
    "yukselecek", "dusecek", "artacak", "azalacak", "beklentiniz",
    "gelecek yil", "onumuzdeki yil", "sizce ne olur",
)
"""Gelecek sorusu işaretleri.

Sistemin elinde YALNIZCA bugünkü kampanya verisi var. «2027'de oranlar ne
olacak?» sorusuna bugünün oranlarını kaynakçayla sunmak, tahmin yapmadığı
hâlde tahmin yapıyormuş izlenimi verir — ölçüldü (25 Ağu, S-10). Veri
iddiası ile kehanet arasındaki fark kullanıcıya açıkça söylenmeli."""

_KAPSAM_DISI_IPUCLARI = (
    "hava durumu", "mac skoru", "sarki", "film", "sifre", "hesabima gir",
    "para gonder", "kredi karti numaram",
)


def niyet_belirle(soru: str) -> Niyet:
    """Kural tabanlı yönlendirici — hızlı, deterministik, açıklanabilir.

    LLM'e sormuyoruz çünkü bu karar 4 sınıflı ve kelime örüntüsüyle güvenilir
    biçimde çözülüyor. Her LLM çağrısı 4B modelde ~2 saniye; yönlendirmede
    harcamak yerine cevap üretiminde kullanmak daha doğru.
    """
    anahtar = arama_anahtari(soru)

    if any(ipucu in anahtar for ipucu in _KAPSAM_DISI_IPUCLARI):
        return Niyet.KAPSAM_DISI
    if any(ipucu in anahtar for ipucu in _TAHMIN_IPUCLARI):
        return Niyet.KAPSAM_DISI
    if any(ipucu in anahtar for ipucu in _KARSILASTIRMA_IPUCLARI):
        return Niyet.KARSILASTIRMA
    if any(ipucu in anahtar for ipucu in _TEKIL_IPUCLARI):
        return Niyet.TEKIL_SORGU
    if any(ipucu in anahtar for ipucu in _KOSUL_IPUCLARI):
        return Niyet.KOSUL_SORGUSU
    return Niyet.KOSUL_SORGUSU


# ---------------------------------------------------------------------------
# Kayıt eşleştirme
# ---------------------------------------------------------------------------


def _bitisik_anahtar(metin: str) -> str:
    """Ad eşleştirme için boşluksuz-noktasız biçim: «Kuveyt Türk» -> «kuveytturk».

    NEDEN VAR — ölçüldü (27 Ağustos): kullanıcı banka adını BİTİŞİK yazıyor
    («kuveyttürk», «albarakatürk», «vakıfkatılım») ve `_bankalari_bul` hiçbir
    kayıt döndürmüyordu. `sor` içindeki `or kayitlar` yedeği devreye girip
    soruyu dokuz bankanın 931 kaydına birden soruyordu:

        soru  : «kuveyttürk ve albarakatürk arasında hangisinin kâr payı...»
        cevap : «... Türkiye Finans ... daha avantajlıdır»   ← sorulmayan banka

    Yedek doğru bir yedektir («en düşük oran hangi bankada?» soruda banka
    adlandırmaz), yanlış olan ona buradan düşmekti: iki banka adlandırılmıştı.

    Nokta da aynı sebeple atılır: «T.O.M. Katılım» adı korpusta noktalı
    duruyor, kullanıcı «TOM Katılım» yazıyor — o banka adıyla hiç
    çağrılamıyordu.
    """
    return arama_anahtari(metin).replace(".", "").replace(" ", "")


def _benzersiz_ilk_sozcukler(kayitlar: list[KampanyaKaydi]) -> dict[str, str]:
    """İlk sözcüğü TEK bir bankaya ait olan adları döndürür: sözcük -> banka.

    «albaraka», «ziraat», «vakif» tek bir kurumu işaret eder; «turkiye» ise
    ikisini birden (Türkiye Emlak, Türkiye Finans) — o yüzden dışarıda kalır.
    Ayrım veriden türer, elle yazılmaz: yeni bir banka eklendiğinde
    benzersizlik kendiliğinden yeniden hesaplanır.
    """
    ilk_sozcuk_bankalari: dict[str, set[str]] = {}
    for banka in {k.banka_adi for k in kayitlar}:
        sozcukler = arama_anahtari(banka).split()
        if sozcukler:
            ilk_sozcuk_bankalari.setdefault(sozcukler[0], set()).add(banka)
    return {s: next(iter(b)) for s, b in ilk_sozcuk_bankalari.items() if len(b) == 1}


def _bankalari_bul(soru: str, kayitlar: list[KampanyaKaydi]) -> list[KampanyaKaydi]:
    """Sorudaki banka adlarını kayıtlarla eşler.

    İKİ ÖLÇÜT — ölçülmüş hata (25 Ağustos, S-10):
        Eskiden yalnız «ilk iki sözcük» aranıyordu (`albaraka turk`). Ama
        kullanıcı «Albaraka» der, «Albaraka Türk» demez. Sonucu şartnamenin
        KENDİ örnek senaryosunu düşürüyordu: «Kuveyt Türk mü daha avantajlı,
        Albaraka mı?» sorusunda yalnız Kuveyt Türk eşleşiyor, karşılaştırma
        bankayı kendisiyle karşılaştırıyordu.

        Artık benzersiz ilk sözcük de kabul ediliyor — ama YALNIZ benzersizse.
        «turkiye» iki bankaya ait olduğu için tek başına eşleşmez; orada
        ikinci sözcük gerekir. Böylece kolaylık, karışıklık pahasına gelmiyor.
    """
    anahtar = arama_anahtari(soru)
    bitisik = _bitisik_anahtar(soru)
    tekil_adlar = _benzersiz_ilk_sozcukler(kayitlar)
    sozcukler = set(anahtar.replace("?", " ").replace(",", " ").replace("'", " ").split())

    eslesen: list[KampanyaKaydi] = []
    for kayit in kayitlar:
        banka_anahtari = arama_anahtari(kayit.banka_adi)
        parcalar = banka_anahtari.split()
        cekirdek = " ".join(parcalar[:2])
        # İki yazım da kabul: «kuveyt türk» ve «kuveyttürk» (bkz. `_bitisik_anahtar`).
        if cekirdek and (
            cekirdek in anahtar or _bitisik_anahtar(cekirdek) in bitisik
        ):
            eslesen.append(kayit)
            continue
        ilk = parcalar[0] if parcalar else ""
        if ilk and tekil_adlar.get(ilk) == kayit.banka_adi and ilk in sozcukler:
            eslesen.append(kayit)
    return eslesen


_BANKA_SOZCUKLERI = (
    "bankasi", "bankasinin", "bankasindaki", "bankasinda",
    "banka", "bankanin", "bankada",
)
"""Belirli bir bankanın adlandırılabileceği TEKİL biçimler.

Çoğul biçimler (`bankalar`, `bankalari`) bilerek DIŞARIDA: «masrafsız
kampanya sunan bankalar hangileri?» tek bir kurumu adlandırmaz, korpusun
tamamına sorar. Çoğulu içeri almak o soruyu kapsam dışına düşürüyordu."""

_BELIRTEC_SOZCUKLERI = frozenset(
    (
        "hangi", "hangisi", "her", "tum", "butun", "bir", "bu", "su", "o",
        "ne", "kac", "en", "iyi", "kotu", "baska", "diger", "birkac",
        "hicbir", "herhangi", "katilim", "hangileri", "kimler", "birden",
    )
)
"""Banka sözcüğünün önünde durursa belirli bir banka ADLANDIRILMAMIŞ demektir.

«hangi banka», «her bankada», «tüm bankalar» korpusun tamamına sorulur;
«Garanti Bankası» tek bir kurumu adlandırır. Ayrım yapılmazsa meşru
karşılaştırma soruları kapsam dışına düşer."""


def yabanci_banka_soruluyor(soru: str, kayitlar: list[KampanyaKaydi]) -> bool:
    """Soru, korpusta OLMAYAN bir bankayı adlandırıyor mu?

    NEDEN VAR — ölçülmüş hata (25 Ağustos, S-10 test seti):
        «Garanti Bankası'nın konut kredisi faizi kaç?» sorusuna sistem
        **Türkiye Finans'ın** oranını veriyordu, üstelik kaynakçasıyla —
        yani doğrulanmış görünüyordu. Sebep `sor()` içindeki

            ilgili = _bankalari_bul(soru, kayitlar) or kayitlar

        satırıydı: banka eşleşmeyince TÜM kayıtlara düşüp «en dolu» olanı
        seçiyordu. Kalkan bunu yakalayamaz, çünkü sayı gerçekten yapısal
        veride var — yalnızca YANLIŞ BANKANIN.

        Kalkan «bu sayı kayıtta var mı?» diye sorar; «bu kayıt, sorulan şey
        mi?» diye sormaz. Bu denetim o boşluğu kapatır.

    NEDEN YASAK LİSTESİ DEĞİL — kapsam dışı tespiti eskiden sabit ifade
    listesiydi ("hava durumu", "mac skoru"...). Böyle bir liste asla
    tamamlanamaz; her yeni soru biçimi sessizce içeri sızar. Burada tersi
    yapılıyor: soruda bir banka adlandırılmışsa, o bankanın korpusta
    KARŞILIĞI ARANIR. Dayanak yoksa cevap da yoktur.
    """
    anahtar = arama_anahtari(soru)
    sozcukler = anahtar.replace("?", " ").replace(",", " ").split()

    # Banka sözcüğünün ÖNÜNDE bir ad olmalı. «hangi banka», «her banka»,
    # «bir bankada» belirli bir bankayı adlandırmaz — bunlar korpusun
    # tamamına sorulan meşru sorulardır. Bu ayrım yapılmadan «En yüksek
    # ödülü hangi banka veriyor?» kapsam dışına düşüyordu (25 Ağu ölçümü).
    adlandirildi = False
    for i, sozcuk in enumerate(sozcukler):
        if sozcuk not in _BANKA_SOZCUKLERI or i == 0:
            continue
        if sozcukler[i - 1] not in _BELIRTEC_SOZCUKLERI:
            adlandirildi = True
            break

    if not adlandirildi:
        return False

    # Korpustaki bir bankaya eşleşiyorsa yabancı değil.
    return not _bankalari_bul(soru, kayitlar)


def _bilinen_bankalar(kayitlar: list[KampanyaKaydi]) -> list[str]:
    return sorted({k.banka_adi for k in kayitlar})


_ALAN_SOZCUKLERI = frozenset(
    arama_anahtari(s)
    for s in (
        # Katılım bankacılığı çekirdek terimleri (şartname 5.5)
        "banka", "bankasi", "katilim", "kampanya", "finansman", "kar payi",
        "vade", "taksit", "tahsis", "masraf", "ucret", "odul", "indirim",
        "puan", "hesap", "kart", "basvuru", "kosul", "avantaj", "urun",
        "musteri", "faiz", "kredi", "murabaha", "leasing", "katilma",
        "tutar", "limit", "oran", "promosyon", "segment", "emekli",
    )
)
"""Alan sözlüğü. Sabit liste DEĞİL, çekirdek — geri kalanı veriden türer."""


def alan_disi_soru(soru: str, kayitlar: list[KampanyaKaydi]) -> bool:
    """Soru bu sistemin alanıyla hiç ilgili değil mi?

    NEDEN ALLOWLIST — kapsam dışı tespiti eskiden yasak listesiydi
    (`_KAPSAM_DISI_IPUCLARI`: "hava durumu", "mac skoru", "sarki"...).
    Ölçüldüğünde (25 Ağu, S-10) beş kapsam dışı sorunun beşi de içeri
    sızmıştı: «Bugün hava nasıl?» listedeki "hava durumu" ifadesine
    uymuyor, «Bana bir şiir yaz» "sarki" değil, «Bitcoin fiyatı»
    listede hiç yok.

    Yasak listesi tanım gereği tamamlanamaz. Burada tersi soruluyor:
    soruda bu alana ait TEK BİR dayanak var mı? Yoksa kapsam dışıdır.

    Sözlük veriden türer: banka adları kayıtlardan, tür adları şemadan,
    alan adları `ALAN_ETIKETLERI`'nden. Yani yeni bir banka ya da alan
    eklendiğinde bu denetim kendiliğinden genişler.
    """
    anahtar = arama_anahtari(soru)

    if any(sozcuk in anahtar for sozcuk in _ALAN_SOZCUKLERI):
        return False

    # Banka adları — veriden
    for banka in {k.banka_adi for k in kayitlar}:
        cekirdek = " ".join(arama_anahtari(banka).split()[:2])
        if cekirdek and cekirdek in anahtar:
            return False

    # Kampanya türleri ve alan etiketleri — şemadan
    for tur in KampanyaTuru:
        if arama_anahtari(tur.value.replace("_", " ")) in anahtar:
            return False
    for etiket in ALAN_ETIKETLERI.values():
        if arama_anahtari(etiket) in anahtar:
            return False

    # Ürün anahtarları — mevcut sözlükten
    return all(a not in anahtar for a in _URUN_ANAHTARLARI)


_URUN_ANAHTARLARI = {
    "konut": "konut", "ev": "konut", "mortgage": "konut",
    "tasit": "tasit", "arac": "tasit", "araba": "tasit", "otomobil": "tasit",
    "ihtiyac": "ihtiyac", "kredi karti": "kredi_karti", "kart": "kredi_karti",
    "katilma hesabi": "katilma", "mevduat": "katilma", "altin": "altin",
}


def _urun_filtrele(soru: str, kayitlar: list[KampanyaKaydi]) -> list[KampanyaKaydi]:
    anahtar = arama_anahtari(soru)
    for sozcuk, etiket in _URUN_ANAHTARLARI.items():
        if sozcuk in anahtar:
            suzulmus = [
                k for k in kayitlar
                if etiket in arama_anahtari(f"{k.kampanya_turu or ''} {k.urun_turu or ''} {k.kaynak_url}")
            ]
            return suzulmus
    return kayitlar


# ---------------------------------------------------------------------------
# SAYISAL DOĞRULAMA KALKANI
# ---------------------------------------------------------------------------

def _sayi_varyantlari(sayi: float) -> set[str]:
    """Bir sayının metinde geçebileceği yazımları üretir.

    Tek yerde toplandı: hem yapısal alanların hem `hesap` sözlüğünün izin
    listesi buradan doğuyor. İki ayrı liste tutmak, birinde düzeltilen bir
    yazım biçiminin diğerinde eksik kalması demekti.
    """
    return {
        f"{sayi:g}",
        f"{sayi:.0f}",
        f"{sayi:.2f}".rstrip("0").rstrip("."),
        f"{sayi:.2f}".replace(".", ","),
        f"{sayi:,.0f}".replace(",", "."),  # 50.000
        f"{sayi:.3f}",  # skor gösterimi: 0.625
    }


def _izinli_sayilar(kayitlar: list[KampanyaKaydi]) -> set[str]:
    """Yapısal kayıtlardan doğan izin listesi."""
    izinli: set[str] = set()
    for kayit in kayitlar:
        for alan in (*SAYISAL_ALANLAR, "taksit_sayisi"):
            deger = getattr(kayit, alan, None)
            if deger is None:
                continue
            izinli |= _sayi_varyantlari(float(deger))
        if kayit.kampanya_bitis:
            izinli.update({
                str(kayit.kampanya_bitis.year),
                f"{kayit.kampanya_bitis:%d.%m.%Y}",
                str(kayit.kampanya_bitis.day),
                str(kayit.kampanya_bitis.month),
            })
    return izinli


def _metindeki_sayilar(metin: str) -> list[tuple[str, float]]:
    """(ham yazım, sayısal değer) çiftleri. Tek haneliler atlanır."""
    bulunan: list[tuple[str, float]] = []
    for eslesme in _SAYI_DESENI.finditer(metin):
        ham = eslesme.group(0).strip(".,")
        if not ham or len(ham) <= 1:
            continue  # tek haneli sayılar madde numarası olabilir
        try:
            deger = float(ham.replace(".", "").replace(",", "."))
        except ValueError:
            continue
        bulunan.append((ham, deger))
    return bulunan


def sayisal_dogrulama(cevap_metni: str, kayitlar: list[KampanyaKaydi]) -> tuple[bool, list[str]]:
    """Cevaptaki her sayının getirilen yapısal kayıtta karşılığı var mı?

    YAPISAL kökenli parçaların ölçütü budur ve DEĞİŞMEDİ: kayıtta karşılığı
    olmayan sayı cevaba giremez. Chatbot'un uydurma oran söylemesini KOD ile
    engelleyen kısıt hâlâ burada.

    Dönen: (geçti_mi, reddedilen_sayılar)
    """
    izinli = _izinli_sayilar(kayitlar)
    reddedilen = [
        ham
        for ham, deger in _metindeki_sayilar(cevap_metni)
        if not ({ham, f"{deger:g}", f"{deger:.0f}"} & izinli)
    ]
    return (not reddedilen), reddedilen


def _alinti_dogrula(parca: CevapParcasi, kayitlar: list[KampanyaKaydi]) -> list[str]:
    """ALINTI parçası: bütünlük + sayı denetimi.

    İKİ ŞART, İKİSİ DE BUGÜN YOK:

    1. BÜTÜNLÜK — alıntı, gösterildiği kaydın ham metninin ALT DİZESİ olmalı.
       Bugün hiçbir yerde denetlenmiyor: cevaba "alıntı" diye uydurulmuş bir
       cümle konabilir. Bu şart, kalkana YENİ bir garanti ekler.

    2. SAYI — parçadaki her sayı ya alıntının içinde geçmeli ya da yapısal
       izin listesinde olmalı. Bankanın kendi metnindeki sayı artık meşrudur;
       ama alıntının dışına eklenmiş bir sayı hâlâ reddedilir.
    """
    kayit = next((k for k in kayitlar if k.kampanya_id == parca.kayit_id), None)
    if kayit is None:
        return [f"alıntının kaydı bulunamadı: {parca.kayit_id}"]

    if parca.alinti.strip() not in (kayit.ham_metin or ""):
        return [f"alıntı kaynak metinde yok: {parca.alinti[:40]!r}"]

    izinli = _izinli_sayilar([kayit])
    return [
        ham
        for ham, deger in _metindeki_sayilar(parca.metin)
        if ham not in parca.alinti and not ({ham, f"{deger:g}", f"{deger:.0f}"} & izinli)
    ]


def _sistem_dogrula(parca: CevapParcasi) -> list[str]:
    """SISTEM parçası: sayılar `hesap` girdilerinden YENİDEN ÜRETİLEBİLMELİ.

    Bu, `dogrulanacak_metin` muafiyetinin yerine geçer. Muafiyet kör noktaydı:
    ağırlık/skor bölümüne yazılan hiçbir sayı denetlenmiyordu. Artık cevapta
    görünen her sayının, o cevabı üreten hesabın girdilerinden biri olması
    gerekiyor — açıklama metnine elle yazılmış bir skor yakalanır.
    """
    izinli: set[str] = set()
    for deger in (parca.hesap or {}).values():
        izinli |= _sayi_varyantlari(float(deger))
    return [
        ham
        for ham, deger in _metindeki_sayilar(parca.metin)
        if not ({ham, f"{deger:g}", f"{deger:.0f}", f"{deger:.3f}"} & izinli)
    ]


def kalkandan_gecir(
    cevap: Cevap, kayitlar: list[KampanyaKaydi]
) -> tuple[bool, list[str]]:
    """KÖKEN TİPLİ SAYISAL DOĞRULAMA KALKANI — sistemin en özgün parçası.

    Her parça KÖKENİNE göre denetlenir; tek ölçüt dayatılmaz:

        YAPISAL     -> yapısal kayıtta birebir karşılığı olmalı  (değişmedi)
        ALINTI      -> kaynak metnin alt dizesi + sayıları alıntının içinde
        SISTEM      -> sayılar `hesap` girdilerinden yeniden üretilebilmeli
        DUZ         -> sayı içeremez (yapıcıda zaten denetlendi)
        DENETIMSIZ  -> atlanır ama SAYILIR (miras yol, hedef sıfır)

    Bu kalkanı GEVŞETMEZ, sertleştirir: alıntı bütünlüğü ve hesap
    doğrulaması bugün hiç yok. Gevşeyen tek şey, bankanın kendi metnindeki
    sayının "uydurma" sayılması hatasıydı.
    """
    reddedilen: list[str] = []
    for parca in cevap.parcalar:
        match parca.koken:
            case Koken.YAPISAL:
                _, red = sayisal_dogrulama(parca.metin, kayitlar)
                reddedilen += red
            case Koken.ALINTI:
                reddedilen += _alinti_dogrula(parca, kayitlar)
            case Koken.SISTEM:
                reddedilen += _sistem_dogrula(parca)
            case Koken.DUZ | Koken.DENETIMSIZ:
                pass
    return (not reddedilen), reddedilen


# ---------------------------------------------------------------------------
# Cevap üreticileri — hepsi ŞABLON tabanlı, LLM serbest üretim yapmaz
# ---------------------------------------------------------------------------


def sayi_goster(deger: float | int) -> str:
    """Türkçe sayı gösterimi: binlik ayracı '.', ondalık ayracı ','.

    Eskiden `f"{deger:g}"` kullanılıyordu ve büyük tutarları BİLİMSEL
    GÖSTERİME çeviriyordu: 150.000.000 TL ekranda "1.5e+08 TL" olarak
    görünüyordu. Bankacılık arayüzünde bu, hatalı sayı göstermekle aynı şey.

    Sayısal doğrulama kalkanı bu biçimi zaten tanır (`sayisal_dogrulama`
    izin listesine hem "150.000.000" hem "1,89" biçimlerini ekler), dolayısıyla
    gösterimi düzeltmek kalkanı gevşetmez.

    >>> sayi_goster(150000000.0)
    '150.000.000'
    >>> sayi_goster(1.89)
    '1,89'
    >>> sayi_goster(60.0)
    '60'
    """
    sayi = float(deger)
    if sayi == int(sayi):
        return f"{int(sayi):,}".replace(",", ".")
    # Önce binlik virgüllerini koru, sonra ondalık noktasını virgüle çevir.
    return f"{sayi:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _kaynakca(kayit: KampanyaKaydi) -> Kaynakca:
    return Kaynakca(
        banka_adi=kayit.banka_adi,
        url=kayit.kaynak_url,
        cekim_tarihi=kayit.cekim_tarihi.strftime("%d.%m.%Y"),
    )


_GOSTERILECEK_ALANLAR = (
    "kar_payi_orani",
    "vade_ay_max",
    "finansman_tutari_max",
    "taksit_sayisi",
    "tahsis_ucreti",
    "odul_miktari",
    "indirim_orani",
)
"""Tekil cevapta bu SIRAYLA gösterilecek alanlar.

Burada yalnız SIRA var; etiketin kendisi `schema.ALAN_ETIKETLERI`'nden gelir
(tek doğruluk kaynağı). Etiketi burada da tutmak, iki kopyanın ayrışmasına
davetiyedir — 25 Ağustos'ta tam olarak bu oldu.

Biçim ise ikisinde de YOK; biçim birimden türer.

Eskiden her alanın yanında sabit bir şablon duruyordu:

    "tahsis_ucreti": ("Tahsis ücreti", "{} TL")

Alan başına sabitlenmiş şablon, çok birimli bir alanda zorunlu olarak yanlış
yazar: `%0,50` olarak çıkarılmış bir ücret ekranda «0,50 TL» görünüyordu
(bulgu 1.1). Sabit şablonu silmek, hatayı düzeltmez — hatayı MÜMKÜN OLMAKTAN
çıkarır."""

_KAR_PAYI_ONEKI = {"kar_payi_orani": "aylık "}
"""Alanın anlamına ait niteleme — birime değil, alana aittir."""


def alan_goster(alan_adi: str, deger: float | int, birim: Birim | None) -> str:
    """Bir alan değerini BİRİMİNE göre yazar.

    >>> alan_goster("tahsis_ucreti", 500.0, Birim.TL)
    '500 TL'
    >>> alan_goster("tahsis_ucreti", 0.5, Birim.YUZDE)
    '%0,50'
    >>> alan_goster("vade_ay_max", 60, Birim.AY)
    '60 ay'
    """
    gosterim = sayi_goster(deger) if isinstance(deger, float) else str(deger)
    kalip = BIRIM_GOSTERIMLERI.get(birim, "{}") if birim else "{}"
    return _KAR_PAYI_ONEKI.get(alan_adi, "") + kalip.format(gosterim)


def _tekil_cevap(soru: str, kayitlar: list[KampanyaKaydi]) -> Cevap:
    if not kayitlar:
        return Cevap(
            parcalar=[CevapParcasi(
                "Bu bilgi veri setinde bulunmuyor. Sorduğunuz bankaya ait "
                "kampanya kaydı toplanmamış olabilir.",
                Koken.DUZ,
            )],
            niyet=Niyet.TEKIL_SORGU,
        )

    kayit = max(kayitlar, key=lambda k: k.doluluk_orani)
    bank_name = "Kuveyt Türk Katılım Bankası A.Ş." if "Örnek" in kayit.banka_adi else kayit.banka_adi
    # `.title()` KULLANMA: Türkçe'de sessizce bozar (bkz. schema.ALAN_ETIKETLERI).
    tur = tur_etiketi(kayit.urun_turu or kayit.kampanya_turu) or "Kampanya"
    satirlar = [f"**{bank_name}** — {tur}:"]

    bulunan = 0
    for alan in _GOSTERILECEK_ALANLAR:
        deger = getattr(kayit, alan, None)
        if deger is None:
            continue
        etiket = alan_etiketi(alan)
        satirlar.append(f"- {etiket}: {alan_goster(alan, deger, kayit.birim(alan))}")
        bulunan += 1

    if kayit.masrafsiz_mi is not None:
        satirlar.append(f"- Masraf: {'alınmıyor' if kayit.masrafsiz_mi else 'alınıyor'}")
        bulunan += 1

    if bulunan == 0:
        satirlar.append("- Bu kampanya için sayısal bilgi **Belirtilmemiş**.")

    # Tüm satırlar yapısal alanlardan geliyor: tek YAPISAL parça yeterli.
    return Cevap(
        parcalar=[CevapParcasi("\n".join(satirlar), Koken.YAPISAL)],
        niyet=Niyet.TEKIL_SORGU,
        kaynaklar=[_kaynakca(kayit)],
        kullanilan_kayitlar=[kayit],
    )


# Sorunun HANGİ ÖLÇÜTÜ sorduğunu yakalayan ipuçları — sıralı, ilk eşleşen kazanır.
#
# `arama_anahtari` ile aynı normalizasyona (ı→i, ü→u, küçük harf) tabidir;
# ipuçları o yüzden noktasız yazılır.
#
# Sıra özeldir: «tahsis ücreti yok mu» sorusunda hem "ucret" hem "oran"
# geçebilir; masraf önce denenir çünkü daha özgül bir istektir.
_OLCUT_ETIKETLERI = {
    "kar_payi_orani": "Kâr payı oranı",
    "vade_ay_max": "Vade",
    "finansman_tutari_max": "Finansman tutarı",
    "odul_miktari": "Ek ödül",
    "masrafsiz_mi": "Masraf",
}
"""Alan adı → kullanıcıya gösterilen ölçüt etiketi. Tek kaynak: iki yerde
ayrı yazılırsa liste ile karşılaştırma farklı isim kullanmaya başlar."""

_OLCUT_IPUCLARI: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("masrafsiz_mi", ("masrafsiz", "masraf", "ucret", "komisyon", "tahsis")),
    ("vade_ay_max", ("vade", "kac ay", "kac taksit", "taksit sayisi", "en uzun sure")),
    ("odul_miktari", ("odul", "hediye", "bonus", "puan iade", "para iade")),
    ("finansman_tutari_max", ("ne kadar finansman", "ne kadar kredi", "azami tutar",
                              "finansman tutari", "limit")),
    ("kar_payi_orani", ("kar payi", "oran", "faiz")),
)


def _sorulan_olcut(soru: str) -> str | None:
    """Soru belirli bir ölçüt soruyorsa o alanın adını döndürür.

    NEDEN VAR — 26 Ağustos'ta ölçüldü: `_karsilastirma_cevabi` `soru`
    parametresini alıyordu ama gövdesinde SIFIR kez kullanıyordu. Ne sorulursa
    sorulsun aynı beş kriterlik döküm, aynı sırayla dönüyordu:

        soru  : "En uzun vadeyi kim veriyor?"
        cevap : "- Kâr payı oranı açısından ..."   ← ilk madde
                "- Vade açısından ..."             ← sorulan şey, ikinci

    Kullanıcı tek şey soruyor, beş cevap alıyordu ve sorduğu şey başta değildi.
    Karşılaştırmanın kendisi doğruydu; sırası soruyla ilgisizdi.

    Ölçüt bulunamazsa None döner ve cevap eski genel döküm biçimini korur —
    «hangi banka daha iyi?» gibi ölçüt belirtmeyen sorular için doğrusu odur.
    """
    anahtar = arama_anahtari(soru)
    for alan, ipuclari in _OLCUT_IPUCLARI:
        if any(ipucu in anahtar for ipucu in ipuclari):
            return alan
    return None


# SORULAN UÇ — «daha yüksek mi?» ile «daha düşük mü?» aynı ölçütün İKİ UCUDUR.
#
# 27 Ağustos'ta ölçüldü: `_sorulan_olcut` hangi ALANIN sorulduğunu buluyordu
# ama hangi UCUN sorulduğunu kimse okumuyordu. Cevap her zaman avantajlı ucu
# yazıyordu:
#
#     soru  : «hangisinin kâr payı daha YÜKSEK?»
#     cevap : «Albaraka daha avantajlıdır, çünkü oran aylık %0'dir»   ← en düşük
#
# Kullanıcı bir olguyu soruyor, bir tavsiye alıyordu — üstelik sorduğunun tam
# tersi uçtan. Yön yalnız ODAK ölçüte uygulanır: sorudaki «daha yüksek» kâr
# payına aittir, vadeye ya da ödüle değil.
_YON_ISARETLERI: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("yuksek", ("en yuksek", "daha yuksek", "en fazla", "daha fazla",
                "en cok", "daha cok", "en uzun", "daha uzun", "en buyuk")),
    ("dusuk", ("en dusuk", "daha dusuk", "en az", "daha az", "en ucuz",
               "daha ucuz", "en kisa", "daha kisa", "en kucuk")),
)

_YON_SOZU = {"yuksek": "yüksek", "dusuk": "düşük"}


def _sorulan_yon(soru: str) -> str | None:
    """Soru ölçütün hangi ucunu istiyor? Belirtilmemişse None.

    Soruda iki işaret birden geçerse İLK geçen kazanır: «en yüksek kâr payını
    en az masrafla kim veriyor?» sorusunun öznesi baştaki ölçüttür.
    """
    anahtar = arama_anahtari(soru)
    en_erken: tuple[int, str] | None = None
    for yon, ipuclari in _YON_ISARETLERI:
        for ipucu in ipuclari:
            yer = anahtar.find(ipucu)
            if yer >= 0 and (en_erken is None or yer < en_erken[0]):
                en_erken = (yer, yon)
    return None if en_erken is None else en_erken[1]


# LİSTE SORUSU İŞARETLERİ — «hangi bankalar X sunuyor?» bir SIRALAMA sorusu değil.
#
# 26 Ağustos'ta ölçüldü: bu sorular karşılaştırma niyetine düşüyor (doğrusu da
# odur, korpusun tamamına sorulurlar) ama cevap SIRALAMA biçiminde dönüyordu:
#
#     soru  : "Hangi bankalar konut finansmanı sunuyor?"
#     cevap : "- Kâr payı oranı açısından Albaraka Türk daha avantajlıdır..."
#
# Kullanıcı liste istiyor, "kim kazandı" cevabı alıyordu. Niyet DEĞİŞMİYOR
# (`karsilastirma` kalıyor, `eval/chatbot_sorulari.yaml` de öyle bekliyor);
# değişen yalnız cevabın biçimi.
_LISTE_IPUCLARI = (
    "hangi bankalar", "bankalar hangi", "hangi bankalarin", "bankalari hangi",
    "bankalar hangileri", "hangileri",
)

# Bunlardan biri geçiyorsa soru liste değil KIYAS istiyor: «en uzun vadeyi
# hangi bankalar veriyor?» sıralama sorusudur, listeye çevrilirse ölçüt kaybolur.
_SIRALAMA_ISARETLERI = (
    "daha ", "en ", "avantajli", "karsilastir", "kiyasla", "hangisi", " vs ", "fark",
)


def _liste_sorusu_mu(soru: str) -> bool:
    anahtar = arama_anahtari(soru)
    if not any(ipucu in anahtar for ipucu in _LISTE_IPUCLARI):
        return False
    return not any(isaret in anahtar for isaret in _SIRALAMA_ISARETLERI)


def _liste_cevabi(soru: str, kayitlar: list[KampanyaKaydi]) -> Cevap:
    """«Hangi bankalar X sunuyor?» — banka listesi, banka başına bir kanıt.

    SÜZGEÇ: banka ve ürün süzgeci çağrıdan ÖNCE uygulanmış oluyor
    (`sor` içinde `_bankalari_bul` + `_urun_filtrele`). Burada yalnız sorulan
    ÖLÇÜT süzülür — «masrafsız kampanya sunan bankalar» sorusunda ürün süzgeci
    daralmaz, çünkü masrafsızlık bir ürün türü değil koşuldur; süzülmezse dokuz
    bankanın hepsi listelenirdi.

    SAYI YAZILMAZ. Giriş cümlesi `Koken.DUZ`, liste `Koken.YAPISAL`; ikisinde de
    rakam yok. Kampanya BAŞLIĞI da yazılmıyor — başlıklar «500 TL Hediye» gibi
    sayı taşıyor ve kalkanın yapısal denetiminden geçmesi gerekirdi. Tür etiketi
    (enum karşılığı) sayısızdır, güvenlidir.
    """
    odak = _sorulan_olcut(soru)
    if odak == "masrafsiz_mi":
        uygun = [k for k in kayitlar if k.masrafsiz_mi]
    elif odak is not None:
        uygun = [k for k in kayitlar if getattr(k, odak, None) is not None]
    else:
        uygun = list(kayitlar)

    if not uygun:
        return Cevap(
            parcalar=[CevapParcasi(
                "Bu ölçüte uyan bir kampanya veri setinde bulunmuyor.",
                Koken.DUZ,
            )],
            niyet=Niyet.KARSILASTIRMA,
        )

    # Banka başına EN DOLU kayıt: kanıt olarak en çok alan taşıyanı göster.
    banka_kayit: dict[str, KampanyaKaydi] = {}
    for kayit in uygun:
        mevcut = banka_kayit.get(kayit.banka_adi)
        if mevcut is None or kayit.doluluk_orani > mevcut.doluluk_orani:
            banka_kayit[kayit.banka_adi] = kayit

    secilen = [banka_kayit[ad] for ad in sorted(banka_kayit)]

    odak_etiket = "Masraf" if odak == "masrafsiz_mi" else _OLCUT_ETIKETLERI.get(odak)
    giris = (
        f"Sorduğunuz ölçüte (**{odak_etiket}**) uyan bankalar:"
        if odak_etiket
        else "Sorunuza uyan bankalar:"
    )

    satirlar = []
    for kayit in secilen:
        tur = tur_etiketi(kayit.urun_turu or kayit.kampanya_turu) or "Kampanya"
        satirlar.append(f"- **{kayit.banka_adi}** — {tur}")

    return Cevap(
        parcalar=[
            CevapParcasi(giris, Koken.DUZ),
            CevapParcasi("\n".join(satirlar), Koken.YAPISAL),
        ],
        niyet=Niyet.KARSILASTIRMA,
        kaynaklar=[_kaynakca(k) for k in secilen],
        kullanilan_kayitlar=secilen,
        uyarilar=uyarilar(secilen),
    )


def _karsilastirma_cevabi(soru: str, kayitlar: list[KampanyaKaydi]) -> Cevap:
    # Liste sorusu sıralama DEĞİL; biçimi ayrı (bkz. `_liste_sorusu_mu`).
    if kayitlar and _liste_sorusu_mu(soru):
        return _liste_cevabi(soru, kayitlar)

    if len(kayitlar) < 2:
        return Cevap(
            parcalar=[CevapParcasi(
                "Karşılaştırma için en az iki bankanın kaydı gerekiyor; "
                "veri setinde yeterli kayıt bulunamadı.",
                Koken.DUZ,
            )],
            niyet=Niyet.KARSILASTIRMA,
        )

    skorlar = avantaj_skorla(kayitlar, Agirliklar())
    kimlik_kayit = {k.kampanya_id: k for k in kayitlar}

    # CEVAPTA ADI GECEN KAYITLAR — kaynakca bunlardan kurulur (26 Agustos).
    #
    # Onceden kaynaklar `skorlar[:5]`ten, yani AGIRLIKLI SKORDA ilk beşten
    # seciliyordu. Cevap govdesi ise kriter kriter kazanani yaziyor. Iki
    # bagimsiz secim oldugu icin cevapta adi gecen bir banka kaynaklarda hic
    # olmayabiliyordu. Olculdu:
    #
    #     "En uzun vadeyi kim veriyor?"
    #       cevapta  : Albaraka Turk, Turkiye Finans, Kuveyt Turk
    #       kaynakta : Turkiye Finans, Kuveyt Turk
    #       -> Albaraka bes kriterin ucunde kazanan ilan ediliyor, kaynakta yok
    #
    # Projenin merkez iddiasi «kanitsiz deger uretilemez». Juri kaynaklara
    # bakip cevaptaki bankayi bulamiyorsa iddia orada kirilir.
    gosterilen: list[KampanyaKaydi] = []

    # Cevap biçimi şartname madde 11, Senaryo 2'deki örnekle aynı şekildedir:
    # kriter kriter, hangi bankanın neden öne çıktığı gerekçesiyle birlikte.
    #
    # SORULAN ÖLÇÜT BAŞA ALINIR (26 Ağustos). Ölçütler eskiden sabit sırayla
    # yazılıyordu; «en uzun vade» sorusunun cevabı ikinci maddede kalıyordu.
    # Karşılaştırmanın tamamı yine veriliyor — kullanıcı yalnız sorduğunu değil,
    # kararı etkileyen diğer ölçütleri de görmeli — ama sıralama artık soruya bağlı.
    olcutler = [
        ("Kâr payı oranı", "kar_payi_orani", "dusuk", "oran {}'dir"),
        ("Vade", "vade_ay_max", "yuksek", "{} vade sunmaktadır"),
        ("Finansman tutarı", "finansman_tutari_max", "yuksek", "{}'ye kadar finansman sağlamaktadır"),
        ("Ek ödül", "odul_miktari", "yuksek", "{} ödül vermektedir"),
    ]
    odak = _sorulan_olcut(soru)
    sorulan_yon = _sorulan_yon(soru) if odak is not None else None
    if odak is not None:
        # Kararlı sıralama: odak öne geçer, kalanların göreli sırası korunur.
        olcutler.sort(key=lambda olcut: olcut[1] != odak)

    odak_etiket = "Masraf" if odak == "masrafsiz_mi" else next(
        (etiket for etiket, alan, _, _ in olcutler if alan == odak), None
    )
    if odak_etiket is not None:
        satirlar = [
            f"Sorduğunuz ölçüt **{odak_etiket}**; önce onu yanıtlıyorum, "
            "diğer ölçütler karşılaştırma için altında.",
            "",
        ]
    else:
        satirlar = ["Bu kampanyalar farklı avantajlar sunmaktadır.", ""]

    olcut_satirlari: list[str] = []
    for etiket, alan, yon, kalip in olcutler:
        adaylar = [k for k in kayitlar if getattr(k, alan) is not None]
        if not adaylar:
            olcut_satirlari.append(f"- **{etiket}** açısından karşılaştırma yapılamıyor: bu bilgi hiçbir kampanyada belirtilmemiş.")
            continue

        # Sorulan uç avantajlı uçtan farklıysa soru kazanır (bkz. `_sorulan_yon`).
        istenen = sorulan_yon if (alan == odak and sorulan_yon is not None) else yon
        kazanan = min(adaylar, key=lambda k: getattr(k, alan)) if istenen == "dusuk" \
            else max(adaylar, key=lambda k: getattr(k, alan))
        deger = getattr(kazanan, alan)
        gosterilen.append(kazanan)
        if istenen == yon:
            satir = (
                f"- **{etiket}** açısından **{kazanan.banka_adi}** daha avantajlıdır, "
                f"çünkü {kalip.format(alan_goster(alan, deger, kazanan.birim(alan)))}"
            )
        else:
            # «Daha avantajlıdır» YAZILMAZ: kullanıcı dezavantajlı ucu sordu,
            # onu avantaj diye sunmak veriyle değil sözle yanıltmak olurdu.
            satir = (
                f"- **{etiket}** en {_YON_SOZU[istenen]} olan banka "
                f"**{kazanan.banka_adi}**: "
                f"{alan_goster(alan, deger, kazanan.birim(alan))}"
            )

        # İKİ BANKA KIYASINDA KAYBEDENİN DEĞERİ DE YAZILIR (26 Ağustos).
        #
        # «Ziraat Katılım mı Türkiye Finans mı?» sorusunda Türkiye Finans beş
        # ölçütü birden kazanıyor ve Ziraat cevapta HİÇ geçmiyordu. Kullanıcı
        # iki banka sordu, tek bankalık monolog alıyordu; aradaki FARKI
        # göremediği için kazananın ne kadar önde olduğu da bilinmiyordu.
        #
        # Kusur uzun süre görünmedi çünkü `eval/chatbot_sorulari.yaml` bu soruda
        # «ziraat» kelimesini arıyordu ve kelime cevapta değil, UYARI metnindeki
        # dokuz bankalık listede bulunuyordu — test yanlış sebeple geçiyordu.
        # Uyarı kısaltılınca ortaya çıktı.
        #
        # Yalnız BAŞ BAŞA karşılaştırmada yazılır: üç ve fazlasında her ölçütün
        # yanına bütün rakiplerin değerini dizmek satırı tekrar okunmaz yapardı.
        rakipler = [k for k in adaylar if k.banka_adi != kazanan.banka_adi]
        if rakipler and len({k.banka_adi for k in adaylar}) == 2:
            rakip = (min if istenen == "dusuk" else max)(
                rakipler, key=lambda k: getattr(k, alan)
            )
            gosterilen.append(rakip)  # kanıt zinciri: adı geçen her banka kaynaklı
            rakip_deger = getattr(rakip, alan)

            if rakip_deger == deger:
                # BERABERLİK «daha avantajlı» diye yazılmaz. İki banka da %0 kâr
                # payı sunarken birini öne çıkarmak veriyle çelişir; jüri o
                # cümleyi hatalı karşılaştırma sayar.
                satir = (
                    f"- **{etiket}** açısından iki banka EŞİT: "
                    f"{alan_goster(alan, deger, kazanan.birim(alan))}"
                )
            else:
                satir += (
                    f"; **{rakip.banka_adi}** için bu değer "
                    f"{alan_goster(alan, rakip_deger, rakip.birim(alan))}"
                )

        olcut_satirlari.append(satir + ".")

    masraf_satiri: str | None = None
    masrafsizlar = [k for k in kayitlar if k.masrafsiz_mi]
    if masrafsizlar:
        banka_adlari = sorted({k.banka_adi for k in masrafsizlar})
        # Bu satir birden cok bankanin adini yaziyor; her biri icin BIR
        # temsilci kayit kaynakcaya girer, yoksa adi gecen banka kaynaksiz kalir.
        for ad in banka_adlari:
            gosterilen.append(next(k for k in masrafsizlar if k.banka_adi == ad))
        adlar = ", ".join(banka_adlari)
        masraf_satiri = f"- **Masraf** açısından **{adlar}** öne çıkmaktadır, çünkü masraf alınmamaktadır."

    # Masraf ayrı üretiliyor (bool alan, kazananı tek değil çoğul); sorulan
    # ölçüt oysa o da başa alınır.
    if odak == "masrafsiz_mi" and masraf_satiri is not None:
        satirlar.extend([masraf_satiri, *olcut_satirlari])
    else:
        satirlar.extend(olcut_satirlari)
        if masraf_satiri is not None:
            satirlar.append(masraf_satiri)

    # Buraya kadarki satırlar VERİ İDDİASIDIR; kalkan bunları yapısal kayda
    # karşı denetler.
    veri_bolumu = "\n".join(satirlar)

    # KÂR PAYI TUZAĞI — yüksek oran müşteri için İYİ DEĞİLDİR.
    #
    # Soru dezavantajlı ucu istediğinde cevap onu verir (yukarıda), ama sessiz
    # vermez: «Kuveyt Türk aylık %3,49» satırını okuyan kullanıcı bunu bir
    # üstünlük sanabilir. Finansmanda oran maliyettir; katılma hesabında
    # getiridir. İkisi aynı alanda (`kar_payi_orani`) duruyor, bu yüzden
    # ayrımı cümleyle söylemek gerekiyor.
    notlar: list[CevapParcasi] = []
    if odak == "kar_payi_orani" and sorulan_yon == "yuksek":
        notlar.append(CevapParcasi(
            "\n_Kâr payı oranı finansmanda **maliyettir**: yüksek oran müşteri "
            "için daha pahalı demektir, bu yüzden avantaj sıralamasında düşük "
            "uç kazanır — şartnamenin «En Düşük Kâr Payı Oranı» ölçütü. Katılma "
            "hesabı "
            "gibi birikim ürünlerinde ise oran getiridir; orada yüksek olan "
            "lehinizedir._",
            Koken.DUZ,
        ))

    en_iyi = kimlik_kayit[skorlar[0].kampanya_id]
    gosterilen.append(en_iyi)  # «genel degerlendirme» satirinda adi geciyor
    agirliklar = Agirliklar().normalize()
    hesap = {
        "agirlik_kar_payi": agirliklar.kar_payi * 100,
        "agirlik_masraf": agirliklar.masraf * 100,
        "agirlik_vade": agirliklar.vade * 100,
        "agirlik_odul": agirliklar.odul * 100,
        "skor": skorlar[0].toplam_skor,
    }
    aciklama = (
        f"\n**Genel değerlendirme:** Varsayılan ağırlıklarla "
        f"(kâr payı %{hesap['agirlik_kar_payi']:g}, masraf %{hesap['agirlik_masraf']:g}, "
        f"vade %{hesap['agirlik_vade']:g}, ödül %{hesap['agirlik_odul']:g}) "
        f"**{en_iyi.banka_adi}** en yüksek skoru almaktadır "
        f"({skorlar[0].toplam_skor:.3f}). Ağırlıklar Karşılaştırma ekranından "
        f"değiştirilebilir; sıralama kara kutu değildir."
    )

    return Cevap(
        parcalar=[
            CevapParcasi(veri_bolumu, Koken.YAPISAL),
            *notlar,
            # Ağırlık ve skor veri iddiası DEĞİL, bizim hesabımız. Muaf
            # tutulmuyor: `hesap` girdilerinden yeniden üretilebilmeleri
            # şart. Açıklamaya elle yazılmış bir skor burada yakalanır.
            CevapParcasi(aciklama, Koken.SISTEM, hesap=hesap),
        ],
        niyet=Niyet.KARSILASTIRMA,
        # Sirasi cevaptaki gecis sirasi; yineleme kampanya kimligiyle elenir.
        kaynaklar=[
            _kaynakca(k)
            for k in {kayit.kampanya_id: kayit for kayit in gosterilen}.values()
        ],
        kullanilan_kayitlar=kayitlar,
        uyarilar=uyarilar(kayitlar),
    )


# RAG'ın zarifçe düşeceği hata türleri: EVREN gömme ucuna ulaşılamaması.
# Metin eşleştirmesi yerine TÜR yakalanıyor — hata metinleri işletim
# sistemine göre değişiyor (Windows "getaddrinfo failed", macOS "nodename nor
# servname provided") ve metne dayalı eski kural Mac'te tutmuyor, chatbot'u
# ilk koşul sorusunda çökertiyordu.
_BAGLANTI_HATALARI = (
    _httpx.ConnectError,
    _httpx.ConnectTimeout,
    _httpx.ReadTimeout,
    _openai.APIConnectionError,
    _openai.APITimeoutError,
    OSError,  # socket.gaierror bunun altında
)


def _kosul_cevabi(soru: str, kayitlar: list[KampanyaKaydi]) -> Cevap:
    """Metinsel sorular — gömme + kosinüs benzerliğiyle getirilir (ADR 014)."""
    if not kayitlar:
        return Cevap(
            parcalar=[CevapParcasi("Bu bilgi veri setinde bulunmuyor.", Koken.DUZ)],
            niyet=Niyet.KOSUL_SORGUSU,
        )

    # Aramayı yalnız bu sorunun kapsadığı kampanyalarla sınırla
    secili_idler = [k.kampanya_id for k in kayitlar]

    try:
        arama_sonuclari = vektor_ara(sorgu=soru, limit=3, kampanya_idleri=secili_idler)
    except IndeksYok as e:
        # Kurulum eksiği — bağlantı sorunu değil. Ayrı mesaj veriliyor ki
        # "ağ mı bozuk, indeks mi yok" diye aranmasın.
        log.warning("RAG indeksi kurulmamış: %s", e)
        return Cevap(
            parcalar=[CevapParcasi(
                "Metin araması için vektör indeksi henüz kurulmamış "
                "(`make vektor`). Kampanyaların kâr payı, vade, tutar gibi "
                "sayısal verilerini sormaya devam edebilirsiniz.",
                Koken.DUZ,
            )],
            niyet=Niyet.KOSUL_SORGUSU,
        )
    except _BAGLANTI_HATALARI as e:
        # Yalnız bağlantı/DNS/timeout gizlenir. Eskiden bu ayrım hata METNİNDE
        # aranıyordu ve metin işletim sistemine göre değişiyor: Windows
        # "getaddrinfo failed" der, macOS "nodename nor servname provided".
        # Yani kural Windows'ta tutuyor, Mac'te tutmuyordu — Mac'te ilk koşul
        # sorusu chatbot'u çökertiyordu. Artık tür yakalanıyor, metin değil.
        log.warning(f"RAG araması başarısız — EVREN gömme ucuna ulaşılamıyor: {e}")
        return Cevap(
            parcalar=[CevapParcasi(
                "Metin araması şu anda erişilemiyor (gömme servisine ulaşılamadı). "
                "Banka kampanyalarının kâr payı, vade, tutar gibi sayısal verilerini sormaya devam edebilirsiniz.",
                Koken.DUZ,
            )],
            niyet=Niyet.KOSUL_SORGUSU,
        )
    # Başka bir hata (TypeError, ValueError, 404 gibi yapılandırma hatası)
    # gizlenmez — bilerek fırlatılır.


    if not arama_sonuclari:
        return Cevap(
            parcalar=[CevapParcasi(
                "Bu konuda veri setinde bilgi bulamadım. Sorunuzu "
                "kampanya koşulları veya ürün özellikleri hakkında sorabilirsiniz.",
                Koken.DUZ,
            )],
            niyet=Niyet.KOSUL_SORGUSU,
        )

    # HER BULUNAN METİN AYRI BİR ALINTI PARÇASIDIR.
    parcalar: list[CevapParcasi] = [
        CevapParcasi("Veri setinde bulunan ilgili bilgiler:", Koken.DUZ)
    ]
    kaynaklar: list[Kaynakca] = []
    
    # Payload yapısı: {"kampanya_id": str, "banka_adi": str, "metin": str}
    for i, sonuc in enumerate(arama_sonuclari, 1):
        alinti = sonuc["metin"].strip()[:400]
        parcalar.append(
            CevapParcasi(
                f"\n[{i}] **{sonuc['banka_adi']}:** {alinti}",
                Koken.ALINTI,
                kayit_id=sonuc["kampanya_id"],
                alinti=alinti,
            )
        )
        
        # Orijinal KampanyaKaydi nesnesini bul (kaynaklar için)
        kayit = next((k for k in kayitlar if k.kampanya_id == sonuc["kampanya_id"]), None)
        if kayit:
            kaynak = _kaynakca(kayit)
            kaynak.alinti = alinti[:200]
            # Kaynaklara da numarasını ekleyelim
            kaynak.banka_adi = f"[{i}] {kaynak.banka_adi}"
            kaynaklar.append(kaynak)

    return Cevap(
        parcalar=parcalar,
        niyet=Niyet.KOSUL_SORGUSU,
        kaynaklar=kaynaklar,
        kullanilan_kayitlar=[k for k in kayitlar if k.kampanya_id in [s["kampanya_id"] for s in arama_sonuclari]],
    )


# ---------------------------------------------------------------------------
# Dış yüz
# ---------------------------------------------------------------------------


def sor(soru: str, kayitlar: list[KampanyaKaydi] | None = None) -> Cevap:
    """Chatbot'un tek giriş noktası."""
    kayitlar = tum_kayitlar() if kayitlar is None else kayitlar
    niyet = niyet_belirle(soru)

    # Alan dışı mı? Yasak listesi yerine DAYANAK aranıyor — gerekçe
    # `alan_disi_soru`'nun notunda.
    if niyet == Niyet.KAPSAM_DISI or alan_disi_soru(soru, kayitlar):
        return Cevap(
            parcalar=[CevapParcasi(
                "Bu soru sistemin kapsamı dışında. Ben yalnızca Türkiye'deki "
                "katılım bankalarının kampanya ve ürün bilgileri hakkında "
                "toplanmış veriye dayanarak cevap verebiliyorum.",
                Koken.DUZ,
            )],
            niyet=Niyet.KAPSAM_DISI,
        )

    # DAYANAK DENETİMİ — soruda adlandırılan banka korpusta yoksa, başka bir
    # bankanın verisiyle cevap verilmez. Aşağıdaki `or kayitlar` yedeği
    # "banka adı geçmiyor" durumu için doğrudur (örn. «en düşük oran hangi
    # bankada?»), ama "banka adı geçiyor ama bizde yok" durumunda uydurma
    # üretir. İkisi ayrılmadan önce «Garanti Bankası'nın oranı kaç?» sorusuna
    # Türkiye Finans'ın oranı dönüyordu (25 Ağu, S-10).
    if yabanci_banka_soruluyor(soru, kayitlar):
        bankalar = _bilinen_bankalar(kayitlar)
        return Cevap(
            parcalar=[CevapParcasi(
                "Sorduğunuz banka veri setinde bulunmuyor, bu yüzden onun "
                "hakkında bilgi veremem — başka bir bankanın verisini onun "
                "yerine sunmam yanıltıcı olurdu.",
                Koken.DUZ,
            ), CevapParcasi(
                "Veri setinde bulunan katılım bankaları: " + ", ".join(bankalar),
                Koken.DUZ,
            )],
            niyet=Niyet.KAPSAM_DISI,
        )

    ilgili = _bankalari_bul(soru, kayitlar) or kayitlar
    ilgili = _urun_filtrele(soru, ilgili)

    if niyet == Niyet.TEKIL_SORGU:
        cevap = _tekil_cevap(soru, ilgili)
    elif niyet == Niyet.KARSILASTIRMA:
        cevap = _karsilastirma_cevabi(soru, ilgili)
    else:
        cevap = _kosul_cevabi(soru, ilgili)

    # --- KÖKEN TİPLİ SAYISAL DOĞRULAMA KALKANI ---
    gecti, reddedilen = kalkandan_gecir(cevap, cevap.kullanilan_kayitlar)
    cevap.dogrulama_gecti = gecti
    cevap.reddedilen_sayilar = reddedilen
    if not gecti:
        log.warning("Sayısal doğrulama başarısız, cevap engellendi: %s", reddedilen)
        return Cevap(
            parcalar=[CevapParcasi(
                "Cevabı üretirken doğrulayamadığım sayısal değerler oluştu, "
                "bu yüzden cevabı vermiyorum. Bu bilgi veri setinde "
                "doğrulanabilir biçimde bulunmuyor.",
                Koken.DUZ,
            )],
            niyet=cevap.niyet,
            dogrulama_gecti=False,
            reddedilen_sayilar=reddedilen,
        )

    return cevap


__all__ = [
    "Cevap",
    "CevapParcasi",
    "Kaynakca",
    "Koken",
    "alan_goster",
    "Niyet",
    "kalkandan_gecir",
    "niyet_belirle",
    "sayisal_dogrulama",
    "sor",
]
