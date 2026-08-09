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

from src.comparison.karsilastirma import Agirliklar, avantaj_skorla, uyarilar
from src.depolama import KampanyaKaydi, tum_kayitlar
from src.preprocessing.normalizasyon import arama_anahtari
from src.schema import SAYISAL_ALANLAR

log = logging.getLogger(__name__)

YASAL_UYARI = "Bağlayıcı teklif niteliği taşımaz."


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


@dataclass
class Cevap:
    metin: str
    niyet: Niyet
    kaynaklar: list[Kaynakca] = field(default_factory=list)
    kullanilan_kayitlar: list[KampanyaKaydi] = field(default_factory=list)
    uyarilar: list[str] = field(default_factory=list)
    dogrulama_gecti: bool = True
    reddedilen_sayilar: list[str] = field(default_factory=list)

    dogrulanacak_metin: str | None = None
    """Sayısal doğrulama kalkanının denetleyeceği bölüm. None ise `metin`.

    NEDEN AYRI BİR ALAN:
        Kalkan, cevaptaki her sayının yapısal kayıtta karşılığı olmasını arar.
        Ama bir cevap iki tür sayı içerir:

          1. VERİ İDDİASI  — "kâr payı oranı %1,89'dur"  → doğrulanmalı
          2. SİSTEM AÇIKLAMASI — "ağırlıklar: kâr payı %40, masraf %25",
             "skor 0,625"                                 → doğrulanamaz, çünkü
             bunlar veriden gelmiyor, bizim hesabımız.

        İkisini ayırmazsak kalkan kendi açıklamamızı halüsinasyon sanıp geçerli
        bir cevabı engeller. 9 Ağustos'ta karşılaştırma cevabı tam olarak bu
        yüzden bloke oldu (reddedilenler: 40, 25, 20, 15, 0.625).

        Kalkanı gevşetmek yanlış çözüm olurdu — asıl iş onun sıkı kalması.
        Doğru çözüm, denetlenecek metni doğru seçmek.
    """

    def denetlenecek(self) -> str:
        return self.dogrulanacak_metin if self.dogrulanacak_metin is not None else self.metin

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
)
_KOSUL_IPUCLARI = (
    "kosul", "sart", "nasil", "kimler", "gerekli", "basvuru", "uygun mu",
    "kapsam", "gecerli mi", "detay",
)
_TEKIL_IPUCLARI = (
    "oran", "kar payi", "vade", "tutar", "limit", "masraf", "ucret", "ne kadar",
    "kac", "odul", "indirim", "taksit",
)
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


def _bankalari_bul(soru: str, kayitlar: list[KampanyaKaydi]) -> list[KampanyaKaydi]:
    """Sorudaki banka adlarını kayıtlarla eşler."""
    anahtar = arama_anahtari(soru)
    eslesen: list[KampanyaKaydi] = []
    for kayit in kayitlar:
        banka_anahtari = arama_anahtari(kayit.banka_adi)
        # "kuveyt turk katilim bankasi a.s." -> ilk iki sözcük ayırt edici
        cekirdek = " ".join(banka_anahtari.split()[:2])
        if cekirdek and cekirdek in anahtar:
            eslesen.append(kayit)
    return eslesen


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
            if suzulmus:
                return suzulmus
    return kayitlar


# ---------------------------------------------------------------------------
# SAYISAL DOĞRULAMA KALKANI
# ---------------------------------------------------------------------------

_SAYI_DESENI = re.compile(r"\d[\d.,]*")


def sayisal_dogrulama(cevap_metni: str, kayitlar: list[KampanyaKaydi]) -> tuple[bool, list[str]]:
    """Cevaptaki her sayının getirilen yapısal kayıtta karşılığı var mı?

    Yoksa cevap reddedilir. Bu, chatbot'un uydurma oran söylemesini KOD ile
    engeller — istem mühendisliğiyle değil. Sistemin en özgün parçası budur.

    Dönen: (geçti_mi, reddedilen_sayılar)
    """
    izinli: set[str] = set()
    for kayit in kayitlar:
        for alan in (*SAYISAL_ALANLAR, "taksit_sayisi"):
            deger = getattr(kayit, alan, None)
            if deger is None:
                continue
            sayi = float(deger)
            izinli.add(f"{sayi:g}")
            izinli.add(f"{sayi:.0f}")
            izinli.add(f"{sayi:.2f}".rstrip("0").rstrip("."))
            izinli.add(f"{sayi:.2f}".replace(".", ","))
            izinli.add(f"{sayi:,.0f}".replace(",", "."))  # 50.000
        if kayit.kampanya_bitis:
            izinli.update({
                str(kayit.kampanya_bitis.year),
                f"{kayit.kampanya_bitis:%d.%m.%Y}",
                str(kayit.kampanya_bitis.day),
                str(kayit.kampanya_bitis.month),
            })

    reddedilen: list[str] = []
    for eslesme in _SAYI_DESENI.finditer(cevap_metni):
        ham = eslesme.group(0).strip(".,")
        if not ham or len(ham) <= 1:
            continue  # tek haneli sayılar madde numarası olabilir
        normalize = ham.replace(".", "").replace(",", ".")
        try:
            deger = float(normalize)
        except ValueError:
            continue
        adaylar = {ham, f"{deger:g}", f"{deger:.0f}"}
        if not (adaylar & izinli):
            reddedilen.append(ham)

    return (not reddedilen), reddedilen


# ---------------------------------------------------------------------------
# Cevap üreticileri — hepsi ŞABLON tabanlı, LLM serbest üretim yapmaz
# ---------------------------------------------------------------------------


def _kaynakca(kayit: KampanyaKaydi) -> Kaynakca:
    return Kaynakca(
        banka_adi=kayit.banka_adi,
        url=kayit.kaynak_url,
        cekim_tarihi=kayit.cekim_tarihi.strftime("%d.%m.%Y"),
    )


_ALAN_ETIKETLERI = {
    "kar_payi_orani": ("Kâr payı oranı", "aylık %{}"),
    "vade_ay_max": ("Azami vade", "{} ay"),
    "finansman_tutari_max": ("Azami finansman tutarı", "{} TL"),
    "taksit_sayisi": ("Taksit sayısı", "{}"),
    "tahsis_ucreti": ("Tahsis ücreti", "{} TL"),
    "odul_miktari": ("Ödül miktarı", "{} TL"),
    "indirim_orani": ("İndirim oranı", "%{}"),
}


def _tekil_cevap(soru: str, kayitlar: list[KampanyaKaydi]) -> Cevap:
    if not kayitlar:
        return Cevap(
            metin="Bu bilgi veri setinde bulunmuyor. Sorduğunuz bankaya ait "
                  "kampanya kaydı toplanmamış olabilir.",
            niyet=Niyet.TEKIL_SORGU,
        )

    kayit = max(kayitlar, key=lambda k: k.doluluk_orani)
    satirlar = [f"**{kayit.banka_adi}** — {kayit.urun_turu or kayit.kampanya_turu or 'kampanya'}:"]

    bulunan = 0
    for alan, (etiket, bicim) in _ALAN_ETIKETLERI.items():
        deger = getattr(kayit, alan, None)
        if deger is None:
            continue
        gosterim = f"{deger:g}" if isinstance(deger, float) else str(deger)
        satirlar.append(f"- {etiket}: {bicim.format(gosterim)}")
        bulunan += 1

    if kayit.masrafsiz_mi is not None:
        satirlar.append(f"- Masraf: {'alınmıyor' if kayit.masrafsiz_mi else 'alınıyor'}")
        bulunan += 1

    if bulunan == 0:
        satirlar.append("- Bu kampanya için sayısal bilgi **Belirtilmemiş**.")

    return Cevap(
        metin="\n".join(satirlar),
        niyet=Niyet.TEKIL_SORGU,
        kaynaklar=[_kaynakca(kayit)],
        kullanilan_kayitlar=[kayit],
    )


def _karsilastirma_cevabi(soru: str, kayitlar: list[KampanyaKaydi]) -> Cevap:
    if len(kayitlar) < 2:
        return Cevap(
            metin="Karşılaştırma için en az iki bankanın kaydı gerekiyor; "
                  "veri setinde yeterli kayıt bulunamadı.",
            niyet=Niyet.KARSILASTIRMA,
        )

    skorlar = avantaj_skorla(kayitlar, Agirliklar())
    kimlik_kayit = {k.kampanya_id: k for k in kayitlar}

    # Cevap biçimi şartname madde 11, Senaryo 2'deki örnekle aynı şekildedir:
    # kriter kriter, hangi bankanın neden öne çıktığı gerekçesiyle birlikte.
    satirlar = ["Bu kampanyalar farklı avantajlar sunmaktadır.", ""]

    for etiket, alan, yon, bicim in (
        ("Kâr payı oranı", "kar_payi_orani", "dusuk", "oran %{}'dir"),
        ("Vade", "vade_ay_max", "yuksek", "{} ay vade sunmaktadır"),
        ("Finansman tutarı", "finansman_tutari_max", "yuksek", "{} TL'ye kadar finansman sağlamaktadır"),
        ("Ek ödül", "odul_miktari", "yuksek", "{} TL ödül vermektedir"),
    ):
        adaylar = [k for k in kayitlar if getattr(k, alan) is not None]
        if not adaylar:
            satirlar.append(f"- **{etiket}** açısından karşılaştırma yapılamıyor: bu bilgi hiçbir kampanyada belirtilmemiş.")
            continue

        kazanan = min(adaylar, key=lambda k: getattr(k, alan)) if yon == "dusuk" \
            else max(adaylar, key=lambda k: getattr(k, alan))
        deger = getattr(kazanan, alan)
        gosterim = f"{deger:g}" if isinstance(deger, float) else str(deger)
        satirlar.append(
            f"- **{etiket}** açısından **{kazanan.banka_adi}** daha avantajlıdır, "
            f"çünkü {bicim.format(gosterim)}."
        )

    masrafsizlar = [k for k in kayitlar if k.masrafsiz_mi]
    if masrafsizlar:
        adlar = ", ".join(sorted({k.banka_adi for k in masrafsizlar}))
        satirlar.append(f"- **Masraf** açısından **{adlar}** öne çıkmaktadır, çünkü masraf alınmamaktadır.")

    # Buraya kadarki satırlar VERİ İDDİASIDIR; kalkan bunları denetler.
    veri_bolumu = "\n".join(satirlar)

    en_iyi = kimlik_kayit[skorlar[0].kampanya_id]
    aciklama = (
        f"\n**Genel değerlendirme:** Varsayılan ağırlıklarla (kâr payı %40, masraf %25, "
        f"vade %20, ödül %15) **{en_iyi.banka_adi}** en yüksek skoru almaktadır "
        f"({skorlar[0].toplam_skor:.3f}). Ağırlıklar Karşılaştırma ekranından "
        f"değiştirilebilir; sıralama kara kutu değildir."
    )

    return Cevap(
        metin=veri_bolumu + "\n" + aciklama,
        dogrulanacak_metin=veri_bolumu,  # ağırlık ve skor sayıları veri iddiası değil
        niyet=Niyet.KARSILASTIRMA,
        kaynaklar=[_kaynakca(kimlik_kayit[d.kampanya_id]) for d in skorlar[:5]],
        kullanilan_kayitlar=kayitlar,
        uyarilar=uyarilar(kayitlar),
    )


def _kosul_cevabi(soru: str, kayitlar: list[KampanyaKaydi]) -> Cevap:
    """Metinsel sorular — ham metinden ilgili parçalar getirilir.

    v0'da anahtar sözcük örtüşmesi kullanılıyor. Sprint 2'de gömme tabanlı
    kosinüs benzerliği ile değiştirilecek (turkish-e5-large). Arayüz sözleşmesi
    aynı kalacağı için değişim yerel olacak.
    """
    if not kayitlar:
        return Cevap(metin="Bu bilgi veri setinde bulunmuyor.", niyet=Niyet.KOSUL_SORGUSU)

    soru_sozcukleri = set(arama_anahtari(soru).split()) - {"ne", "nedir", "mi", "mu", "icin"}

    puanli: list[tuple[float, KampanyaKaydi, str]] = []
    for kayit in kayitlar:
        for paragraf in re.split(r"\n+", kayit.ham_metin):
            if len(paragraf) < 40:
                continue
            p_sozcukler = set(arama_anahtari(paragraf).split())
            ortak = soru_sozcukleri & p_sozcukler
            if ortak:
                puanli.append((len(ortak) / max(1, len(soru_sozcukleri)), kayit, paragraf))

    puanli.sort(key=lambda x: -x[0])
    if not puanli:
        return Cevap(
            metin="Bu konuda veri setinde bilgi bulamadım. Sorunuzu "
                  "kampanya koşulları veya ürün özellikleri hakkında sorabilirsiniz.",
            niyet=Niyet.KOSUL_SORGUSU,
        )

    satirlar = ["Veri setinde bulunan ilgili bilgiler:", ""]
    kaynaklar: list[Kaynakca] = []
    for _, kayit, paragraf in puanli[:3]:
        satirlar.append(f"**{kayit.banka_adi}:** {paragraf.strip()[:400]}")
        satirlar.append("")
        kaynak = _kaynakca(kayit)
        kaynak.alinti = paragraf.strip()[:200]
        kaynaklar.append(kaynak)

    return Cevap(
        metin="\n".join(satirlar),
        niyet=Niyet.KOSUL_SORGUSU,
        kaynaklar=kaynaklar,
        kullanilan_kayitlar=[k for _, k, _ in puanli[:3]],
    )


# ---------------------------------------------------------------------------
# Dış yüz
# ---------------------------------------------------------------------------


def sor(soru: str, kayitlar: list[KampanyaKaydi] | None = None) -> Cevap:
    """Chatbot'un tek giriş noktası."""
    kayitlar = tum_kayitlar() if kayitlar is None else kayitlar
    niyet = niyet_belirle(soru)

    if niyet == Niyet.KAPSAM_DISI:
        return Cevap(
            metin="Bu soru sistemin kapsamı dışında. Ben yalnızca Türkiye'deki "
                  "katılım bankalarının kampanya ve ürün bilgileri hakkında "
                  "toplanmış veriye dayanarak cevap verebiliyorum.",
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

    # --- SAYISAL DOĞRULAMA KALKANI ---
    gecti, reddedilen = sayisal_dogrulama(cevap.denetlenecek(), cevap.kullanilan_kayitlar)
    cevap.dogrulama_gecti = gecti
    cevap.reddedilen_sayilar = reddedilen
    if not gecti:
        log.warning("Sayısal doğrulama başarısız, cevap engellendi: %s", reddedilen)
        return Cevap(
            metin="Cevabı üretirken doğrulayamadığım sayısal değerler oluştu, "
                  "bu yüzden cevabı vermiyorum. Bu bilgi veri setinde "
                  "doğrulanabilir biçimde bulunmuyor.",
            niyet=cevap.niyet,
            dogrulama_gecti=False,
            reddedilen_sayilar=reddedilen,
        )

    return cevap


__all__ = ["Cevap", "Kaynakca", "Niyet", "niyet_belirle", "sayisal_dogrulama", "sor"]
