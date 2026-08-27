"""Sohbet bağlamı — çok turlu soruda YUVA DEVRİ.

BURADAKİ «HAFIZA» SOHBET GEÇMİŞİ DEĞİLDİR.

Chatbot deterministik: cevabı üreten şey kod, doldurulacak bir istem yok.
Önceki turları bir dil modeline vermenin bu mimaride karşılığı yoktur.
Karşılığı olan şey ANAFORA ÇÖZÜMÜ: önceki turda ÇÖZÜLMÜŞ varlıkları
(banka · ürün · ölçüt · yön · tutar · vade) sonraki turun BOŞ yuvalarına
taşımak.

ÖLÇÜLDÜ (27 Ağustos) — devir olmadan iki tur:

    tur 1: «Albaraka en yüksek kâr payı oranı ne?»
             -> Albaraka Türk, aylık %2,87                              ✓
    tur 2: «120 ay vade»
             -> Kuveyt Türk, Alışveriş Puanı Kampanyası, 48 ay          ✗

    tur 1: «1.000.000 TL konut finansmanı istiyorum»
             -> «Uygunluk değerlendirmesi için şu bilgiler eksik: vade»
    tur 2: «120 ay vade»
             -> Kuveyt Türk, Alışveriş Puanı Kampanyası                 ✗

İkincisi daha ağır: SİSTEM SORUYU KENDİ SORUYOR, CEVABINI KULLANAMIYOR.

DÖRT KURAL — hepsi depodaki mevcut ilkelerin devamı:

1. DEVİR YALNIZ BOŞ YUVAYA. Yeni turda adlandırılan her zaman kazanır;
   «peki Kuveyt Türk?» bankayı değiştirir, ölçütü ve yönü devralır.

2. KAPSAM KAPILARI HAM SORUYA UYGULANIR, devir sonradan gelir. Tersi
   kalkanı delerdi: «Python'da liste nasıl ters çevrilir?» bağlamla
   kurtarılıp konut kampanyası dökümü alırdı — `terim_gecer`'in kapattığı
   deliğin aynısı, bu sefer arka kapıdan.

3. TUTAR VE VADE YALNIZ PROFİL KİPİNDE DEVROLUR. Sistem «vade eksik»
   dediyse sonraki turun vadesi o yuvaya oturur; başıboş bir tutar sonraki
   olgusal soruyu profil sorgusuna çevirmez.

4. DEVRALINAN HER YUVA CEVAPTA BEYAN EDİLİR ve beyan kalkandan geçer
   (`Koken.SISTEM` + `hesap`). «Müşteri tipi belirtilmedi» dürüstlüğünün
   aynısı: kullanıcının yazmadığı bir kısıtla cevap verildiyse, bunu
   kullanıcı görmeli.

BAĞLAM KAYAN ÇERÇEVEDİR: her turda YENİDEN kurulur, geçmiş yığılmaz.
Devralınan yuva zaten o turun sorusuna girdiği için kendiliğinden korunur —
ayrıca bir birleştirme kuralı gerekmez, dolayısıyla sapma da birikemez.

Sözcük dağarcığı ELLE YAZILMAZ (ADR 021): devredilen ölçütün metni
`_OLCUT_ETIKETLERI`'nden, yönü `_YON_SOZU`'nden, ürünü `_URUN_ANAHTARLARI`'ndan
türer. İkinci bir liste, o listenin diğerleriyle ayrışmasını garanti ederdi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

# ÖZEL ADLAR BİLEREK İÇERİ ALINIYOR. Bu modül chatbot'un soru ayrıştırmasına
# İKİNCİ BİR KOPYA yazmıyor, ona SORUYOR: «bu soruda banka adlandırılmış mı?»
# sorusunun tek cevabı `_bankalari_bul`'dur. 27 Ağustos'ta `alan_disi_soru`
# eşleştirmeyi elle kopyaladığı için aynı soruya iki kapı iki farklı cevap
# veriyordu; o hata burada tekrarlanmıyor.
from src.depolama import KampanyaKaydi
from src.preprocessing.normalizasyon import arama_anahtari
from src.rag.chatbot import (
    _BELIRTEC_SOZCUKLERI,
    _LISTE_IPUCLARI,
    _OLCUT_ETIKETLERI,
    _URUN_ANAHTARLARI,
    _YON_SOZU,
    _bankalari_bul,
    _sorulan_olcut,
    _sorulan_yon,
    Cevap,
    CevapParcasi,
    Koken,
    Niyet,
    sayi_goster,
    sorulan_urun,
    terim_gecer,
)

AZAMI_DEVIR_BANKASI = 2
"""Bundan fazla banka kullanan cevap bir KONU değil, korpusun kendisidir.

Tekil sorgu bir bankayı, karşılaştırma iki bankayı adlandırır; «hangi
bankalar taşıt finansmanı sunuyor?» dokuzunu birden döndürür. Dokuzunu
devretmek sonraki soruya hiçbir şey söylemez, yalnız soruyu uzatır."""

BAGLAM_TASIMAYAN_NIYETLER = frozenset(
    {Niyet.TANIM_SORGUSU, Niyet.KORPUS_SORGUSU, Niyet.KAPSAM_DISI}
)
"""Bu turlar bağlamı ne KURAR ne de BOZAR.

«Kâr payı nedir?» konuyu değiştirmez, bir terimi açıklar; araya giren bir
kapsam dışı soru da öncesindeki konuyu silmemelidir. Sohbet şöyle akıyor
ve ortadaki tur bağlamı süpürseydi üçüncü tur yine boşa düşerdi:

    «Albaraka'nın kâr payı?» · «Murabaha nedir?» · «peki vadesi?»
"""


@dataclass(frozen=True)
class SohbetBaglami:
    """Bir turun ÇÖZÜLMÜŞ yuvaları — soruda geçen ham metin değil.

    Banka adı kullanıcının yazdığı «albraka» değil, cevabın fiilen
    kullandığı kayıtların `banka_adi` alanıdır. Devredilen şeyin veriye
    bağlı olması, yazım hatasının ikinci tura taşınmasını da engeller.
    """

    bankalar: tuple[str, ...] = ()
    urun: str | None = None
    olcut: str | None = None
    yon: str | None = None
    tutar: float | None = None
    vade_ay: int | None = None
    profil_kipi: bool = False
    """Önceki tur muhakeme ajanına gitti mi? `tutar`/`vade_ay` devrinin kapısı."""

    def bos_mu(self) -> bool:
        return not (
            self.bankalar
            or self.urun
            or self.olcut
            or self.yon
            or self.tutar
            or self.vade_ay
        )


@dataclass(frozen=True)
class Devir:
    """`soruyu_tamamla`'nın sonucu: tamamlanmış soru + beyan edilecek yuvalar."""

    soru: str
    yuvalar: tuple[tuple[str, str], ...] = ()
    """(yuva etiketi, gösterim) — cevabın altındaki beyan bundan yazılır."""
    hesap: dict[str, float] = field(default_factory=dict)
    """Beyandaki sayıların kaynağı — `Koken.SISTEM` sözleşmesi bunu istiyor."""

    def var_mi(self) -> bool:
        return bool(self.yuvalar)

    def parca(self) -> CevapParcasi | None:
        """Devri BEYAN eden cevap parçası. Devir yoksa None.

        `Koken.SISTEM`: beyan sayı taşıyabilir (devralınan tutar ve vade) ve o
        sayılar `hesap`'tan yeniden üretilebilir olmalıdır. `DUZ` seçilseydi
        yapıcı haklı olarak reddederdi — `Koken` sözleşmesi zaten bu ayrımı
        yapmak için var.

        Parça, kalkandan GEÇMEDEN önce cevaba eklenir: beyanın kendisi de
        denetlenen bir iddiadır, muaf bir dipnot değil.
        """
        if not self.var_mi():
            return None
        ozet = " · ".join(
            f"{etiket}: {gosterim}" for etiket, gosterim in self.yuvalar
        )
        return CevapParcasi(
            f"\n_Bağlam: bu cevapta önceki sorudan devralındı — {ozet}._",
            Koken.SISTEM,
            hesap=self.hesap,
        )


# ---------------------------------------------------------------------------
# Korpusa sorulan soruya banka devredilmez
# ---------------------------------------------------------------------------

_KORPUS_BELIRTECLERI: tuple[str, ...] = (
    *_LISTE_IPUCLARI,
    *(f"{belirtec} banka" for belirtec in sorted(_BELIRTEC_SOZCUKLERI)),
)
"""«hangi bankalar», «tüm banka…», «her banka…» — soru korpusun TAMAMINA.

ELLE YAZILMADI: `_BELIRTEC_SOZCUKLERI` zaten «banka sözcüğünün önünde
durursa belirli bir banka adlandırılmamış demektir» ayrımını tutuyor;
buradaki ikili o kümeden türetiliyor. Çoğul biçimler ayrıca yazılmıyor,
çünkü `terim_gecer` sözcüğün sonunu serbest bırakır: «her banka» ikilisi
«her bankada» ve «her bankanın» için de eşleşir.

KORPUSA SORULAN SORU HİÇBİR YUVA DEVRALMAZ — kuruluşta ölçüldü:

    tur 1: «Albaraka en yüksek kâr payı oranı ne?»
    tur 2: «hangi bankalar konut finansmanı sunuyor?»
             -> devralınan «en yüksek» + «Vade» soruyu LİSTE olmaktan
                çıkarıp SIRALAMAYA çeviriyor (`_SIRALAMA_ISARETLERI`
                «en » ile eşleşiyor); dokuz bankalık liste yerine tek
                bankalık kıyas dönüyor                                  ✗

Devir bir yuvayı DOLDURUR, sorunun ŞEKLİNİ değiştirmez. Korpusa sorulan
soruda eksik yuva zaten yoktur: muhatap dokuz bankanın hepsidir ve ürünü
soru kendisi adlandırır. Bedeli, «peki hangi bankada daha düşük?» gibi
korpusa açılan takip sorularının ölçüt devralmaması — bilerek ödendi,
çünkü ters yön (meşru bir liste sorusunu tek bankaya daraltmak) sessizce
yanlış cevap üretiyor."""


def korpusa_soruluyor(soru: str) -> bool:
    """Soru tek bir kuruma değil, korpusun tamamına mı soruluyor?"""
    anahtar = arama_anahtari(soru)
    return any(terim_gecer(anahtar, ipucu) for ipucu in _KORPUS_BELIRTECLERI)


@lru_cache(maxsize=None)
def _urun_sozcugu(etiket: str) -> str:
    """Ürün etiketi -> soruya eklenecek sözcük. `_URUN_ANAHTARLARI`'nın tersi.

    Etiketin kendisi her zaman bir anahtar değil: «katilma» etiketine giden
    anahtar «katilma hesabi»dır ve yalnız «katilma» eklemek `sorulan_urun`'ü
    eşleştirmez.
    """
    for sozcuk, sozcuk_etiketi in _URUN_ANAHTARLARI.items():
        if sozcuk_etiketi == etiket:
            return sozcuk
    return etiket


def soruyu_tamamla(
    soru: str, baglam: SohbetBaglami | None, kayitlar: list[KampanyaKaydi]
) -> Devir:
    """Boş yuvaları önceki turdan doldurur. Dolu yuvaya DOKUNMAZ.

    Devir METİN EKLEYEREK yapılır, çünkü bu chatbot'ta soruyu okuyan on
    ayrı ayrıştırıcı var (`_bankalari_bul`, `sorulan_urun`, `_sorulan_olcut`,
    `_sorulan_yon`, `profil_ayristir`, `niyet_belirle` …) ve hepsi soru
    METNİNİ okuyor. Yuvayı metne yazmak, on ayrıştırıcının hepsini tek
    noktadan besler; her birine ayrı bir `baglam` parametresi geçirmek aynı
    kararı on yerde tekrar etmek olurdu.

    Hangi yuvanın boş olduğuna karar veren şey metin değil, ayrıştırıcının
    KENDİSİ: «soruda banka var mı?» sorusunu `_bankalari_bul` cevaplıyor.
    """
    if baglam is None or baglam.bos_mu():
        return Devir(soru)
    if korpusa_soruluyor(soru):
        return Devir(soru)

    ekler: list[str] = []
    yuvalar: list[tuple[str, str]] = []
    hesap: dict[str, float] = {}

    # BANKA — soru bir banka adlandırmıyorsa.
    if baglam.bankalar and not _bankalari_bul(soru, kayitlar):
        ekler += list(baglam.bankalar)
        yuvalar.append(("Banka", ", ".join(baglam.bankalar)))

    # ÜRÜN SINIFI — «konut», «taşıt», «kart» …
    if baglam.urun and sorulan_urun(soru) is None:
        ekler.append(_urun_sozcugu(baglam.urun))
        yuvalar.append(("Ürün", baglam.urun))

    # ÖLÇÜT — sorulan alan. Etiket hem eklenen metin hem beyan: tek kaynak.
    olcut_devroldu = baglam.olcut is not None and _sorulan_olcut(soru) is None
    if olcut_devroldu:
        etiket = _OLCUT_ETIKETLERI[baglam.olcut]
        ekler.append(etiket)
        yuvalar.append(("Ölçüt", etiket))

    # YÖN — YALNIZ ÖLÇÜTLE BİRLİKTE. Yön ölçütün bir NİTELEMESİDİR; kendi
    # başına devredilirse soruya sorulmamış bir uç ekler:
    #
    #     tur 1: «en yüksek kâr payı hangi bankada?»
    #     tur 2: «Albaraka'nın vadesi kaç ay?»  -> olgu sorusu
    #              devralınan «en yüksek» bunu SIRALAMAYA çevirir      ✗
    #
    # Kullanıcı yeni bir ölçüt adlandırdıysa o ölçütün ucunu sormamıştır.
    if olcut_devroldu and baglam.yon and _sorulan_yon(soru) is None:
        soz = _YON_SOZU[baglam.yon]
        ekler.append(f"en {soz}")
        yuvalar.append(("Yön", f"en {soz}"))

    # TUTAR VE VADE — YALNIZ PROFİL KİPİNDE (bkz. modül başlığı, kural 3).
    if baglam.profil_kipi:
        from src.preprocessing.normalizasyon import para_ayristir, vade_ayristir

        if baglam.tutar and para_ayristir(soru, birim_zorunlu=True) is None:
            gosterim = f"{sayi_goster(baglam.tutar)} TL"
            ekler.append(gosterim)
            yuvalar.append(("Tutar", gosterim))
            hesap["devralinan_tutar"] = float(baglam.tutar)
        if baglam.vade_ay and vade_ayristir(soru) is None:
            gosterim = f"{baglam.vade_ay} ay"
            ekler.append(gosterim)
            yuvalar.append(("Vade", gosterim))
            hesap["devralinan_vade_ay"] = float(baglam.vade_ay)

    if not ekler:
        return Devir(soru)
    return Devir(f"{soru} {' '.join(ekler)}", tuple(yuvalar), hesap)


def baglam_guncelle(
    soru: str,
    cevap: Cevap,
    onceki: SohbetBaglami | None,
    *,
    profil_kipi: bool = False,
    tutar: float | None = None,
    vade_ay: int | None = None,
) -> SohbetBaglami:
    """Bu turun yuvalarından YENİ bağlamı kurar.

    `soru` TAMAMLANMIŞ sorudur: devralınan yuva zaten metne yazıldığı için
    bir sonraki tura kendiliğinden taşınır. Bağlamı «birleştiren» bir kural
    yok; olsaydı, hangi yuvanın kaç tur yaşayacağı ayrı bir bakım yükü ve
    ayrı bir sapma kaynağı olurdu.

    Banka adı SORUDAN değil CEVAPTAN okunur (`kullanilan_kayitlar`): «en
    yüksek kâr payını hangi banka veriyor?» sorusunda banka adı geçmez ama
    cevap Albaraka'yı adlandırır — devredilmesi gereken şey odur.
    """
    onceki = onceki or SohbetBaglami()
    if cevap.niyet in BAGLAM_TASIMAYAN_NIYETLER:
        return onceki

    bankalar = tuple(dict.fromkeys(k.banka_adi for k in cevap.kullanilan_kayitlar))
    if len(bankalar) > AZAMI_DEVIR_BANKASI:
        bankalar = ()

    return SohbetBaglami(
        bankalar=bankalar,
        urun=sorulan_urun(soru),
        olcut=_sorulan_olcut(soru),
        yon=_sorulan_yon(soru),
        tutar=tutar,
        vade_ay=vade_ay,
        profil_kipi=profil_kipi,
    )


__all__ = [
    "AZAMI_DEVIR_BANKASI",
    "BAGLAM_TASIMAYAN_NIYETLER",
    "Devir",
    "SohbetBaglami",
    "baglam_guncelle",
    "korpusa_soruluyor",
    "soruyu_tamamla",
]
