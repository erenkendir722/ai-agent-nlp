"""Uzlaştırıcı — kural ve LLM katmanlarını birleştirir (Katman 2c).

Karar tablosu:

    Kural    LLM      Sonuç
    -----    -----    ---------------------------------------------------------
    var      var      Değerler uyuşuyorsa  -> yontem="hibrit", güven yükseltilir
                      Uyuşmuyorsa          -> KURAL kazanır, güven düşürülür,
                                              çelişki kaydedilir
    var      yok      Kural değeri, yontem="kural"
    yok      var      LLM değeri, yontem="llm"
    yok      yok      Alan.yok(), yontem="belirtilmemis"

Neden çelişkide kural kazanıyor? Çünkü kural katmanı bir değeri ancak doğru
bağlam sözcüğünün yanında bulduğunda üretir; yanılma biçimi öngörülebilirdir.
LLM ise akla yatkın ama yanlış değer üretebilir. Sayısal alanlarda kesinlik,
kapsamdan önce gelir — bankacılık bağlamında yanlış oran, eksik orandan
çok daha pahalıdır.

Bu tercihin ölçülmüş gerekçesi ablasyon tablosudur (docs/SONUCLAR.md).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from src.schema import ALAN_ADLARI, SAYISAL_ALANLAR, Alan, HamKayit, Kampanya

log = logging.getLogger(__name__)

# Sayısal karşılaştırmada göreli tolerans. %1 fark aynı sayılır: "50.000 TL" ile
# "50 bin TL" farklı yazımlardır, farklı değer değil.
GORELI_TOLERANS = 0.01

GUVEN_UYUM_ODULU = 0.08  # iki katman da aynı şeyi diyorsa güven artar
GUVEN_CELISKI_CEZASI = 0.25  # çelişki varsa değeri kullanırız ama güvenmeyiz


@dataclass
class Celiski:
    """Kural ve LLM'in aynı alanda farklı şey söylediği durum.

    Bunları saklıyoruz çünkü veri kalitesi raporunun ve hata analizinin
    en verimli girdisi bunlar. `make eval` bu listeyi de raporlar.
    """

    alan: str
    kural_degeri: object
    llm_degeri: object
    url: str

    def __str__(self) -> str:
        return f"{self.alan}: kural={self.kural_degeri!r} llm={self.llm_degeri!r}"


@dataclass
class UzlastirmaRaporu:
    """Tek bir kampanyanın uzlaştırma istatistikleri — ablasyon tablosunun girdisi."""

    kural_alan_sayisi: int = 0
    llm_alan_sayisi: int = 0
    hibrit_alan_sayisi: int = 0
    celiskiler: list[Celiski] = field(default_factory=list)
    llm_reddedilen: int = 0  # metinde doğrulanamadığı için düşen alanlar
    elenen_alan_sayisi: int = 0
    """Uzlaştırmayı kazanıp ALAN MAKULLÜĞÜNDEN düşen değerler.

    Ayrı sayaç, çünkü ayrı bir hata sınıfını ölçüyor: değer metinde
    gerçekten geçiyor (`llm_reddedilen` değil) ama o alana ait değil —
    dilim tablosundan, hesap makinesi çıktısından ya da vergi oranından
    geliyor. Sıfırdan büyük olması sağlıklıdır; sıfır olması kapının
    çalışmadığı anlamına gelir."""


def _degerler_uyusuyor_mu(a: object, b: object) -> bool:
    """İki değerin 'aynı şeyi söyleyip söylemediği'.

    Sayılarda göreli tolerans, metinlerde kapsama, diğerlerinde eşitlik.
    """
    if a is None or b is None:
        return False
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, int | float) and isinstance(b, int | float):
        if a == b:
            return True
        buyuk = max(abs(float(a)), abs(float(b)))
        return buyuk > 0 and abs(float(a) - float(b)) / buyuk <= GORELI_TOLERANS
    if isinstance(a, str) and isinstance(b, str):
        x, y = a.strip().lower(), b.strip().lower()
        return x == y or x in y or y in x
    return a == b


def _birlestir(alan_adi: str, kural: Alan | None, llm: Alan | None) -> tuple[Alan, str]:
    """Tek bir alan için karar. (alan, durum) döner; durum istatistik içindir."""
    if kural is None and llm is None:
        return Alan.yok(), "yok"

    if kural is not None and llm is None:
        return kural, "kural"

    if kural is None and llm is not None:
        return llm, "llm"

    assert kural is not None and llm is not None  # tip daraltma

    if _degerler_uyusuyor_mu(kural.deger, llm.deger):
        # İki bağımsız yöntem aynı sonuca vardı — bu, güvenin en güçlü kanıtı.
        return (
            kural.model_copy(
                update={
                    "guven": round(min(1.0, max(kural.guven, llm.guven) + GUVEN_UYUM_ODULU), 3),
                    "yontem": "hibrit",
                }
            ),
            "hibrit",
        )

    # Çelişki: sayısal alanda kural kazanır, metinsel alanda LLM daha yetkin.
    kazanan = kural if alan_adi in SAYISAL_ALANLAR else llm
    return (
        kazanan.model_copy(
            update={"guven": round(max(0.0, kazanan.guven - GUVEN_CELISKI_CEZASI), 3)}
        ),
        "celiski",
    )


def _makul_mu(alan_adi: str, alan: Alan, metin: str) -> bool:
    """Kazanan alanın son makullük denetimi. Konumsuz değer denetlenmez.

    Konumu olmayan değerler (enum alanları, `masrafsiz_mi` gibi cümleden
    türetilenler) bu kapıdan muaftır: aralık-ucu ve veto denetimleri metindeki
    YERE bakar, yer yoksa uygulanamaz. Onların kendi kapıları zaten var
    (`masrafsiz_mi()` içindeki `FINANSMAN_DISI_UCRET` ve `_KAPSAM_DISI`).

    Konumun metinle tutarlı olduğu da doğrulanır: LLM katmanı bazı alanlarda
    `karakter_baslangic=0` ile kanıtsız kaynak üretiyor (bkz. `llm.py`),
    öyle bir konumdan pencere çıkarmak metnin başını denetlemek olurdu.
    """
    from src.extraction.kural import deger_makul_mu  # döngüsel içe aktarımı önler

    if not alan.var_mi or alan.kaynak is None:
        return True

    bas, bit = alan.kaynak.karakter_baslangic, alan.kaynak.karakter_bitis
    if bas == bit or bit > len(metin):
        return True  # konum yok ya da metne oturmuyor — denetlenemez

    return deger_makul_mu(alan_adi, alan.deger, metin, bas, bit)


def uzlastir(
    kural_alanlari: dict[str, Alan],
    llm_alanlari: dict[str, Alan],
    *,
    kayit: HamKayit,
    rapor: UzlastirmaRaporu | None = None,
) -> tuple[Kampanya, UzlastirmaRaporu]:
    """İki katmanın çıktısını tek bir kanonik Kampanya kaydına indirger."""
    rapor = rapor or UzlastirmaRaporu()
    alanlar: dict[str, Alan] = {}

    for alan_adi in ALAN_ADLARI:
        kural = kural_alanlari.get(alan_adi)
        llm = llm_alanlari.get(alan_adi)
        sonuc, durum = _birlestir(alan_adi, kural, llm)

        # SON KAPI — kazanan değer, geldiği katmandan bağımsız olarak alan
        # makullüğünden geçer. Bu kapı olmadan kural katmanının elediği bir
        # değer LLM yolundan geri giriyordu (bkz. `deger_makul_mu`): eleme,
        # hatayı önlemek yerine kaynağını değiştiriyordu.
        if not _makul_mu(alan_adi, sonuc, kayit.govde_metin):
            sonuc = Alan.yok()
            durum = "elendi"
            rapor.elenen_alan_sayisi += 1

        alanlar[alan_adi] = sonuc

        if durum == "kural":
            rapor.kural_alan_sayisi += 1
        elif durum == "llm":
            rapor.llm_alan_sayisi += 1
        elif durum == "hibrit":
            rapor.hibrit_alan_sayisi += 1
        elif durum == "celiski":
            rapor.celiskiler.append(
                Celiski(alan_adi, kural.deger if kural else None,
                        llm.deger if llm else None, kayit.url)
            )

    kampanya = Kampanya(
        banka_adi=kayit.banka_adi,
        banka_kodu=kayit.banka_kodu,
        kampanya_id=kayit.kampanya_id(),
        kaynak_url=kayit.url,
        cekim_tarihi=kayit.cekim_tarihi,
        ham_metin=kayit.govde_metin,
        **alanlar,
    )
    return kampanya, rapor


# ---------------------------------------------------------------------------
# Boru hattı
# ---------------------------------------------------------------------------


def kampanya_cikar(
    kayit: HamKayit,
    *,
    llm_cikarici: object | None = None,
    kural_kullan: bool = True,
    llm_kullan: bool = True,
) -> tuple[Kampanya, UzlastirmaRaporu]:
    """Ham kayıttan kanonik Kampanya üretir — çıkarım motorunun dış yüzü.

    `kural_kullan` / `llm_kullan` bayrakları ABLASYON TABLOSU içindir:
    aynı kod yolunu üç yapılandırmada koşarak (yalnız kural / yalnız LLM /
    hibrit) karşılaştırılabilir sayı üretiriz. Ayrı kod yolu yazmak,
    ölçümü karşılaştırılamaz hâle getirirdi.
    """
    from src.extraction.kural import kurallarla_cikar  # döngüsel içe aktarımı önler

    metin = kayit.govde_metin
    kural_alanlari: dict[str, Alan] = {}
    llm_alanlari: dict[str, Alan] = {}

    if kural_kullan:
        kural_alanlari = kurallarla_cikar(metin, kayit.url, kayit.cekim_tarihi)

    if llm_kullan:
        if llm_cikarici is None:
            from src.extraction.llm import LLMCikarici

            llm_cikarici = LLMCikarici()
        llm_alanlari = llm_cikarici.cikar(metin, kayit.url, kayit.cekim_tarihi)  # type: ignore[attr-defined]

    return uzlastir(kural_alanlari, llm_alanlari, kayit=kayit)


def tarih_damgali_kimlik(banka_kodu: str, url: str, tarih: datetime) -> str:
    """Aynı sayfanın farklı tarihlerdeki çekimlerini ayırt etmek gerekirse."""
    return f"{Kampanya.kimlik_uret(banka_kodu, url)}@{tarih:%Y%m%d}"


__all__ = [
    "Celiski",
    "UzlastirmaRaporu",
    "kampanya_cikar",
    "uzlastir",
]
