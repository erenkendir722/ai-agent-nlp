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

from src.schema import (
    ALAN_ADLARI,
    ALAN_BOYUTLARI,
    SAYISAL_ALANLAR,
    Alan,
    HamKayit,
    Kampanya,
    Kaynak,
)

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
    yuklem_duzeltme_sayisi: int = 0
    """Yüklem ajanının KANITINI düzelttiği değerler.

    Kural katmanı doğru sayıyı yanlış yerden bulmuş; ajan aynı değeri
    metnin doğru yerinden geri getirmiş. Değer korunur, kanıt zinciri
    onarılır — ret sayacından ayrı tutulur, çünkü biri veri kaybı diğeri
    veri onarımıdır."""

    yuklem_duzeltme_reddi_sayisi: int = 0
    """Yüklem ajanının önerdiği ama MAKUL OLMAYAN düzeltmeler.

    Ajan "doğru alan, yanlış hücre" deyip aynı tablodan başka bir sayı
    getirebiliyor; getirdiği sayı alanın makul aralığının dışındaysa düzeltme
    uygulanmaz ve eski değer korunur (26 Ağu ölçümü, `uzlastir` içindeki not).
    Ayrı sayaç, çünkü bu bir veri kaybı değil, bir düzeltmenin geri çevrilmesi."""

    yuklem_reddi_sayisi: int = 0
    """YÜKLEM AJANININ düşürdüğü kural-tek değerler.

    `elenen_alan_sayisi`'ndan ayrı sayaç, çünkü farklı bir kapı: makullük
    kapısı değerin BÜYÜKLÜĞÜNE bakar (aylık %40 kâr payı olamaz), yüklem
    kapısı değerin O ALANA AİT olup olmadığına bakar (125.000 TL metinde
    var ama azami finansman tutarı değil). Ayrı sayaçlar olmadan ablasyon
    tablosunda hangi kapının ne kazandırdığı ayırt edilemezdi."""

    trace_log: dict = field(default_factory=dict)
    """Gerçek zamanlı CoT izleme (trace) verileri (süreler, kararlar)."""

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

    if not alan.var_mi:
        return True

    # BOYUT KAPISI (şema v1.2.0) — çok birimli alanda birim çözülemediyse değer
    # düşer. Şema zaten birimsiz değeri reddediyor; buradaki kapı olmadan o red
    # `Kampanya` kurulurken patlar ve boru hattının kayıt düzeyindeki
    # `except` bloğu KAYDIN TAMAMINI düşürür — bir alanın birimsizliği yüzünden
    # on beş alan birden kaybolurdu. Aynı sessiz veri kaybı `llm.py`'deki
    # `_kismi_json_kurtar` yorumunda anlatılıyor; çözüm de aynı: alanı düşür,
    # kaydı yaşat.
    if alan_adi in ALAN_BOYUTLARI and len(ALAN_BOYUTLARI[alan_adi]) > 1:
        if alan.birim is None:
            log.info(
                "%s düşürüldü: çok birimli alanın birimi ham ifadeden "
                "çözülemedi (%r)", alan_adi, alan.ham_ifade,
            )
            return False

    if alan.kaynak is None:
        return True

    bas, bit = alan.kaynak.karakter_baslangic, alan.kaynak.karakter_bitis
    if bas == bit or bit > len(metin):
        return True  # konum yok ya da metne oturmuyor — denetlenemez

    return deger_makul_mu(alan_adi, alan.deger, metin, bas, bit)


def _ifadeden_alan(
    alan_adi: str, ifade: str, kayit: HamKayit, eski: Alan
) -> Alan | None:
    """Düzeltilmiş ham ifadeden alanı yeniden kurar. Türetilemezse None.

    Ayrıştırıcılar `extraction.llm`'den alınır — aynı ifadeyi iki farklı
    yerde iki farklı biçimde sayıya çevirmek, iki katmanın "aynı değeri
    buldu" kararını anlamsız kılardı.
    """
    from src.extraction.llm import _AYRISTIRICILAR

    ayristirici = _AYRISTIRICILAR.get(alan_adi)
    if ayristirici is None:
        return None
    try:
        deger = ayristirici(ifade)
    except (ValueError, TypeError):
        return None
    if deger is None:
        return None

    konum = kayit.govde_metin.find(ifade)
    kaynak = None
    if konum != -1:
        kaynak = Kaynak(
            url=kayit.url,
            cekim_tarihi=kayit.cekim_tarihi,
            alinti=kayit.govde_metin[max(0, konum - 80) : konum + len(ifade) + 80],
            karakter_baslangic=konum,
            karakter_bitis=konum + len(ifade),
        )
    return Alan(
        deger=deger,
        ham_ifade=ifade,
        kaynak=kaynak,
        guven=eski.guven,
        yontem="hibrit",
        birim=eski.birim,
    )


def uzlastir(
    kural_alanlari: dict[str, Alan],
    llm_alanlari: dict[str, Alan],
    *,
    kayit: HamKayit,
    rapor: UzlastirmaRaporu | None = None,
    yuklem: object | None = None,
) -> tuple[Kampanya, UzlastirmaRaporu]:
    """İki katmanın çıktısını tek bir kanonik Kampanya kaydına indirger.

    `yuklem` verilirse (bkz. `ajanlar.yuklem.YuklemAjani`) KURAL-TEK değerler
    ek bir kapıdan geçer: metin bu değeri gerçekten o alana yüklüyor mu?
    Hibrit, LLM ve çelişki değerleri denetlenmez — gerekçeler aşağıda.
    """
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
        from src.extraction.kural import dilim_turevi_mi  # döngüsel içe aktarım

        # ÇELİŞKİ DE KAPSANIR (26 Ağu). Baypas önce yalnız `durum == "kural"`
        # için açıktı ve doğru cevap tam da çelişki halinde ölüyordu:
        #
        #     0206-d7223804788b (altın 400000)
        #        kural 400000  ·  llm 2000000 (tablonun tepesi)  ->  SONUÇ None
        #
        # LLM de bir değer ürettiği için durum "celiski" oluyor, baypas
        # kapanıyor, makullük kapısı doğru cevabı eliyordu. Oysa
        # `finansman_tutari_max` sayısal bir alan, yani `_birlestir` çelişkide
        # ZATEN kuralı kazandırıyor — kazanan değer kuralın ürettiğinin aynısı.
        # Ayrımı `durum` etiketi üzerinden kurmak, değerin nereden geldiğini
        # değil rakibinin olup olmadığını sormaktı.
        #
        # Genişletmek güvenli, çünkü kapıyı `dilim_turevi_mi` tutuyor: hem
        # değer hem kanıt ayrıştırıcının yeniden ürettiğiyle birebir aynı
        # olmadıkça False döner. LLM'in kaptığı 2000000 o denetimden geçemez.
        tablo_turevi = durum in {"kural", "celiski"} and dilim_turevi_mi(
            alan_adi, sonuc, kayit.govde_metin
        )

        if not tablo_turevi and not _makul_mu(alan_adi, sonuc, kayit.govde_metin):
            sonuc = Alan.yok()
            durum = "elendi"
            rapor.elenen_alan_sayisi += 1

        # YÜKLEM KAPISI — KANITI ZAYIF olan değerlerde.
        #
        # Ölçülen kesinlikler: hibrit 0,870 · llm 0,820 · kural-tek 0,696.
        # Kural-tek değerlerde sayı metinde GERÇEKTEN geçiyor (eleştirmen bunu
        # zaten doğruladı) ama çoğu kez başka bir şeyi anlatıyor: başka ürünün
        # vadesi, bir tablo satırı, bir koşul eşiği. Varlık denetimi bunu
        # göremez; yüklem denetimi görebilir.
        #
        # ÇELİŞKİYE UYGULANMASI DENENDİ VE GERİ ALINDI (24 Ağu).
        #
        # Gerekçe sağlamdı: `_birlestir` çelişki çıktığında kazanana GÜVEN
        # CEZASI veriyor, yani kod çelişkiyi zaten zayıf kanıt sayıyor. İki
        # katmanın ANLAŞAMADIĞI bir değerin dayanağı, tek katmanın ürettiğinden
        # güçlü olmamalıydı. Üstelik `finansman_tutari_max`'ın iki yanlış
        # pozitifi tam bu delikten geçiyordu ve ajan onları tek tek
        # sorulduğunda 3/3 tutarlılıkla reddediyordu.
        #
        # K=3 ölçüm aksini söyledi:
        #     yalnız kural   : makro-F1 0,782 · finansman_tutari_max 0,515
        #     kural+çelişki  : makro-F1 0,764 · finansman_tutari_max 0,400
        #
        # Sebep: çelişkilerin çoğunda kural katmanı HAKLI. Kapı yanlış
        # pozitifleri elerken doğru çözümleri de düşürüyor ve net zarar
        # veriyor. Çelişki "zayıf kanıt" demek, ama "yanlış" demek değil.
        #
        # HİBRİTE UYGULANMAZ: iki katmanın aynı sonuca varması zaten daha güçlü
        # bir kanıttır; gereksiz LLM çağrısı hem yavaşlatır hem yeni bir hata
        # kaynağı açar.
        elif (
            durum == "kural"
            and not tablo_turevi
            and yuklem is not None
            and sonuc.deger is not None
        ):
            karar = yuklem.denetle(
                alan_adi, sonuc.deger, sonuc.ham_ifade or "", kayit.govde_metin
            )
            if karar == "":
                # Metin bu alanı hiç anlatmıyor — değer düşer.
                sonuc = Alan.yok()
                durum = "yuklem_reddi"
                rapor.yuklem_reddi_sayisi += 1
            elif karar:
                # Doğru alan, yanlış kanıt: değeri düzeltilmiş ifadeden
                # yeniden türet. Türetilemezse eski değere DOKUNMA —
                # ajan yalnız kanıtı iyileştirebilir, veri kaybettiremez.
                #
                # DÜZELTME DE MAKULLÜK KAPISINDAN GEÇER — ölçülmüş hata (26 Ağu):
                #     turkiyefinans.com.tr/.../gunluk-hesap.aspx
                #     kural %11,00  ->  yüklem düzeltmesi %44,00  (0,842 güvenle)
                #
                #     Sayfa bir katılma hesabı getiri tablosu; ajan "doğru alan,
                #     yanlış hücre" deyip aynı tablonun tepesindeki oranı
                #     getirdi. Aylık kâr payı üst sınırı %15 olduğu için o değer
                #     makullük kapısından ZATEN geçemezdi — ama kapı bu satırın
                #     ÜSTÜNDE, yani düzeltilmiş değere hiç uygulanmıyordu.
                #     Sonuç: kural katmanının elediği bir büyüklük, ajan yolundan
                #     geri giriyordu. Bu, `deger_makul_mu`'nun doğuş sebebiyle
                #     birebir aynı hata sınıfı — eleme hatayı önlemek yerine
                #     kaynağını değiştiriyor.
                yenilenmis = _ifadeden_alan(alan_adi, karar, kayit, sonuc)
                if yenilenmis is not None and not _makul_mu(
                    alan_adi, yenilenmis, kayit.govde_metin
                ):
                    log.info(
                        "%s: yüklem düzeltmesi makul değil, eski değer korundu "
                        "(%r -> %r)", alan_adi, sonuc.deger, yenilenmis.deger,
                    )
                    rapor.yuklem_duzeltme_reddi_sayisi += 1
                    yenilenmis = None
                if yenilenmis is not None:
                    sonuc = yenilenmis
                    durum = "yuklem_duzeltmesi"
                    rapor.yuklem_duzeltme_sayisi += 1

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
    yuklem: object | None = None,
) -> tuple[Kampanya, UzlastirmaRaporu]:
    """Ham kayıttan kanonik Kampanya üretir — çıkarım motorunun dış yüzü.

    `kural_kullan` / `llm_kullan` bayrakları ABLASYON TABLOSU içindir:
    aynı kod yolunu üç yapılandırmada koşarak (yalnız kural / yalnız LLM /
    hibrit) karşılaştırılabilir sayı üretiriz. Ayrı kod yolu yazmak,
    ölçümü karşılaştırılamaz hâle getirirdi.
    """
    from src.extraction.kural import kurallarla_cikar  # döngüsel içe aktarımı önler
    import time

    metin = kayit.govde_metin
    kural_alanlari: dict[str, Alan] = {}
    llm_alanlari: dict[str, Alan] = {}
    
    trace = {}

    # SÜRE ÖLÇÜMÜ `perf_counter` İLE — `time.time()` DEĞİL (27 Ağustos).
    #
    # `time.time()` bir DUVAR SAATİDİR: Windows'ta çözünürlüğü ~15,6 ms ve NTP
    # düzeltmesinde geriye bile gidebilir. Kural katmanı tek bir küçük kaydı bir
    # saat tıkından hızlı bitirince `time.time() - t0` tam olarak 0,0 çıkıyordu.
    #
    # Ölçülen zarar: `tests/test_boru_hatti_ilerleme.py` içindeki «kayıt olayı
    # ölçülen değerleri taşır» testi KARARSIZ hâle gelmişti — `sure > 0` tam
    # koşuda düşüyor, tek başına koşunca geçiyordu (önbellek soğukken yavaş,
    # sıcakken bir tıktan hızlı). Canlı boru hattı sayfasındaki süre göstergesi
    # de aynı sebeple 0 ms gösterirdi.
    #
    # `perf_counter` monotondur ve alt-mikrosaniye çözünürlüklüdür; süre
    # ölçmenin doğru aracı odur. Çıkarılan DEĞERLERE dokunmaz, yalnız
    # `trace_log` sayılarını düzeltir.
    t0 = time.perf_counter()

    if kural_kullan:
        t_kural = time.perf_counter()
        kural_alanlari = kurallarla_cikar(metin, kayit.url, kayit.cekim_tarihi)
        trace["kural_suresi"] = time.perf_counter() - t_kural

    if llm_kullan:
        t_llm = time.perf_counter()
        if llm_cikarici is None:
            t_load = time.perf_counter()
            from src.extraction.llm import LLMCikarici

            llm_cikarici = LLMCikarici()
            trace["llm_load_suresi"] = time.perf_counter() - t_load
        
        t_inf = time.perf_counter()
        llm_alanlari = llm_cikarici.cikar(metin, kayit.url, kayit.cekim_tarihi)  # type: ignore[attr-defined]
        trace["llm_cikarim_suresi"] = time.perf_counter() - t_inf
        trace["llm_toplam_suresi"] = time.perf_counter() - t_llm

    t_uz = time.perf_counter()
    kampanya, rapor = uzlastir(kural_alanlari, llm_alanlari, kayit=kayit, yuklem=yuklem)
    trace["uzlastirma_suresi"] = time.perf_counter() - t_uz

    # UYGUNLUK AJANI — uzlaştırmadan SONRA koşar (A-08).
    # Kısıtların çoğu uzlaştırılmış alanlardan türer (`max_tutar` ←
    # `finansman_tutari_max`); kural ve LLM katmanları ayrı ayrı çıkarım
    # yaparken türetmek, uzlaştırıcının seçmediği bir değeri kısıta yazma
    # riski taşırdı. LLM çağırmaz, bu yüzden ablasyonun her kolunda koşar.
    t_uygunluk = time.perf_counter()
    from src.ajanlar.uygunluk import UygunlukAjani

    kampanya.uygunluk = UygunlukAjani().cikar(kampanya)
    trace["uygunluk_suresi"] = time.perf_counter() - t_uygunluk
    trace["toplam_sure"] = time.perf_counter() - t0
    
    rapor.trace_log = trace
    return kampanya, rapor


def tarih_damgali_kimlik(banka_kodu: str, url: str, tarih: datetime) -> str:
    """Aynı sayfanın farklı tarihlerdeki çekimlerini ayırt etmek gerekirse."""
    return f"{Kampanya.kimlik_uret(banka_kodu, url)}@{tarih:%Y%m%d}"


__all__ = [
    "Celiski",
    "UzlastirmaRaporu",
    "kampanya_cikar",
    "uzlastir",
]
