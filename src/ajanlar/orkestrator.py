"""Orkestratör — isteği çözümler, hangi ajanın çalışacağına karar verir.

NEDEN LLM DEĞİL, KURAL TABANLI:
    Yönlendirme beş sınıflı bir karar ve kelime örüntüsüyle güvenilir biçimde
    çözülüyor. LLM'e sormanın üç maliyeti var: her istekte ~2 sn gecikme,
    demo sırasında öngörülemez sıralama, ve ablasyonda kontrol edilemezlik.
    Kazancı ise yok — model "bu bir karşılaştırma sorusu" demekten fazlasını
    söylemiyor.

    Bu, "ajan sayısı için ajan eklemeyin" ilkesinin uygulaması: orkestratör
    var çünkü işi var, ama işini yapmak için LLM gerekmiyor.

PROFİL SORGUSU — yeni yetenek:
    "Maaş müşterisi, 800.000 TL konut, 10 yıl vade" gibi bir istek muhakeme
    ajanına yönlenir. Eksik bilgi varsa ORKESTRATÖR TAHMİN ETMEZ, sorar:
    tutar veya vade uydurmak, sistemin bütün maliyet hesabını sessizce
    yanlışlar.
"""

from __future__ import annotations

from src.ajanlar.muhakeme import MuhakemeAjani, MusteriProfili, UygunlukSonucu
from src.ajanlar.temel import AjanIzi, IzDefteri, iz_tut
from src.depolama import KampanyaKaydi
from src.preprocessing.normalizasyon import arama_anahtari, para_ayristir, vade_ayristir
from src.rag.chatbot import (
    Cevap,
    CevapParcasi,
    Kaynakca,
    Koken,
    Niyet,
    eksik_nicelikler,
    kalkandan_gecir,
    niyet_belirle,
    sayi_goster,
    sorulan_bankalar,
    sorulan_olcut_ve_yon,
    sorulan_urun,
    urun_etiketi_uyar,
)
from src.rag.baglam import Devir, SohbetBaglami, baglam_guncelle, soruyu_tamamla
from src.rag.chatbot import sor as chatbot_sor
from src.comparison.karsilastirma import ALAN_YONLERI, turu_olcut_kapsaminda
from src.rag.chatbot import alan_goster
from src.schema import TEK_BIRIMLI_ALANLAR, Alan, Birim, HedefKitle, Kampanya, alan_etiketi

PROFIL_SORGUSU = "profil_sorgusu"
"""`Niyet` bir StrEnum ve `chatbot.py` içinde donmuş durumda; yeni değeri
oraya eklemek yerine orkestratör düzeyinde tutuyoruz. Chatbot'un dört niyeti
ve sayısal doğrulama kalkanı olduğu gibi çalışmaya devam ediyor."""


# ---------------------------------------------------------------------------
# Profil ayrıştırma
# ---------------------------------------------------------------------------

_MUSTERI_TIPI_IPUCLARI: tuple[tuple[str, HedefKitle], ...] = (
    ("maas musterisi", HedefKitle.MAAS_MUSTERISI),
    ("maasli", HedefKitle.MAAS_MUSTERISI),
    ("maas alan", HedefKitle.MAAS_MUSTERISI),
    ("yeni musteri", HedefKitle.YENI_MUSTERI),
    ("mevcut musteri", HedefKitle.MEVCUT_MUSTERI),
    ("musterimiz", HedefKitle.MEVCUT_MUSTERI),
)

_SEGMENT_IPUCLARI: tuple[str, ...] = ("emekli", "ogrenci", "kobi", "esnaf", "ciftci")


def profil_ayristir(soru: str) -> tuple[MusteriProfili | None, list[str]]:
    """Serbest metinden müşteri profili çıkarır.

    Dönen: (profil, eksik_alanlar). Profil ancak üç bilgi de varsa kurulur.

    EKSİK BİLGİ TAHMİN EDİLMEZ. "Ne kadar?" sorusuna varsayılan bir tutar
    koymak, taksitten toplam maliyete kadar her sayıyı sessizce yanlışlardı
    ve kullanıcı bunu fark edemezdi.
    """
    anahtar = arama_anahtari(soru)
    eksikler: list[str] = []

    tutar = para_ayristir(soru, birim_zorunlu=True)
    if tutar is None or tutar <= 0:
        eksikler.append("tutar (örn. 800.000 TL)")

    vade = vade_ayristir(soru)
    if vade is None or vade <= 0:
        eksikler.append("vade (örn. 120 ay veya 10 yıl)")

    tip: HedefKitle | None = None
    segment: str | None = None
    for ipucu, deger in _MUSTERI_TIPI_IPUCLARI:
        if ipucu in anahtar:
            tip = deger
            break
    if tip is None:
        for ad in _SEGMENT_IPUCLARI:
            if ad in anahtar:
                tip, segment = HedefKitle.SEGMENT, ad
                break
    # MÜŞTERİ TİPİ EKSİKSE SORULMAZ (27 Ağustos, jüri havuzu 9. madde).
    #
    #     soru  : «120 ay vadeli 1.000.000 TL konut finansmanı için en düşük
    #              kâr payı oranını hangi katılım bankası sunuyor?»
    #     cevap : «Uygunluk değerlendirmesi için şu bilgiler eksik: müşteri
    #              tipi…»
    #
    # Soru bir SIRALAMA sorusu; «ben uygun muyum?» diye sormuyor. Tipi
    # bilmeden de cevaplanabilir, çünkü tip hiçbir hesaba girmez — yalnız
    # süzer. Tutar ve vade öyle değil: ikisi de taksit ve toplam maliyet
    # formülüne girer, uydurulan bir değer cevaptaki HER sayıyı yanlışlar.
    # O ikisi hâlâ sorulur; ayrım, tahmin edilenin sonuca ne yaptığıdır.
    if eksikler:
        return None, eksikler

    assert tutar is not None and vade is not None
    return (
        MusteriProfili(musteri_tipi=tip, tutar=tutar, vade_ay=vade, segment=segment),
        [],
    )


_PROFIL_IPUCLARI: tuple[str, ...] = (
    "musteri", "musterim", "profil", "onerebilir", "uygun mu", "hangisini",
    "karsimda", "istiyor", "talep ediyor",
)


def profil_sorgusu_mu(soru: str) -> bool:
    """Bu istek muhakeme ajanına mı gitmeli?

    İki tetikleyici var ve ikincisi kritik:

    1. Tutar VE vade birlikte geçiyorsa — güçlü, deterministik sinyal.
    2. İkisinden BİRİ + bir müşteri ipucu ("müşterim 500.000 TL istiyor").
       Bu olmadan eksik bilgili profil sorguları hiç muhakemeye ulaşmaz,
       koşul sorgusu sanılıp kalkana takılır ve kullanıcı "cevabı
       doğrulayamadım" mesajı alır — oysa yapılması gereken eksik olan
       vadeyi SORMAKTIR.
    """
    tutar_var = para_ayristir(soru, birim_zorunlu=True) is not None
    vade_var = vade_ayristir(soru) is not None
    if tutar_var and vade_var:
        return True

    anahtar = arama_anahtari(soru)
    return (tutar_var or vade_var) and any(i in anahtar for i in _PROFIL_IPUCLARI)


# ---------------------------------------------------------------------------
# Cevap üretimi
# ---------------------------------------------------------------------------


LISTE_UST_SINIRI = 5
"""Profil cevabında kaç kalem listelenir.

Sayı ELLE ÜÇ YERE yazılıydı (`uygunlar[:5]`, `elenenler[:5]`, kaynakça) ve
hiçbiri kırpmayı BEYAN etmiyordu. Kırpmanın kendisi doğru — on kalemlik bir
döküm okunmaz — ama beyansız kırpma, cevabın kendi başlığıyla çelişmesidir:
başlık «10 kampanya uygun» diyor, gövde beşini gösteriyor, kalan beşin nerede
olduğu yazmıyor. Ölçüldü (27 Ağustos, jüri havuzu 9. madde): gizlenen beş
kaydın dördü Kuveyt Türk, biri Ziraat — «hangi katılım bankası» sorusunda
uygun altı bankanın üçü ekrana hiç çıkmıyordu.

`_profil_cevabi` içindeki yorum zaten «*«3 kampanya uygun» yazıp beş göstermek
bir iddiadır*» diyor; kapatılmamış olan onun ters yönüydü."""

BILINEN_ALANLAR: tuple[str, ...] = tuple(
    alan for alan in ALAN_YONLERI if alan != "kar_payi_orani"
)
"""Kâr payı yoksa CEVABIN SUSMAMASI için gösterilecek alanlar.

Liste elle yazılmadı: karşılaştırma motorunun kıyasladığı alanlardan
(`ALAN_YONLERI`) kâr payı çıkarılarak türetiliyor. Yeni bir ölçüt oraya
eklenince burada da kendiliğinden görünür."""


def _alan_birimi(alan_adi: str, alan: Alan) -> Birim | None:
    """Alanın boyutu: tek birimlide sözleşmeden, çok birimlide taşıyıcıdan.

    `KampanyaKaydi.birim()` aynı ayrımı sütun için yapıyor; buradaki taşıyıcı
    `Alan` nesnesinin kendisi. Sabit tek yerde (`TEK_BIRIMLI_ALANLAR`), yalnız
    okuma noktası farklı — birim olmadan gösterim YANLIŞ yazar: `%0,50`
    olarak çıkarılmış bir tahsis ücreti «0,50 TL» görünürdü (bulgu 1.1).
    """
    return TEK_BIRIMLI_ALANLAR.get(alan_adi) or alan.birim


def _bilinen_satirlar(
    kampanya: Kampanya | None, sira: int, hesap: dict[str, float]
) -> list[str]:
    """Kâr payı olmayan kampanyada BİLİNEN alanları yazar.

    NEDEN VAR — 27 Ağustos'ta ölçüldü. «Emlak Katılım'ın … toplam maliyeti
    Kuveyt Türk'ünkinden düşük mü?» sorusunda beş kampanyanın beşi de tek
    satırla geçiştiriliyordu:

        - Kâr payı oranı **Belirtilmemiş**, maliyet hesaplanamadı.

    Oysa o kayıtlarda tahsis ücreti (%0,50 · %1,10), azami vade ve finansman
    tutarı DOLUYDU. Bilinmeyeni beyan etmek doğrudur; bilineni saklamak
    değil — kullanıcı «bu sistemde hiçbir bilgi yok» sanıyordu.

    Her yazılan sayı `hesap`'a da girer: kalkan `SISTEM` parçasında sayının
    yeniden üretilebilir olmasını şart koşuyor.
    """
    if kampanya is None:
        return []
    satirlar: list[str] = []
    for alan_adi in BILINEN_ALANLAR:
        alan = getattr(kampanya, alan_adi, None)
        if alan is None or alan.deger is None:
            continue
        deger = float(alan.deger)
        gosterim = alan_goster(alan_adi, alan.deger, _alan_birimi(alan_adi, alan))
        satirlar.append(f"   - {alan_etiketi(alan_adi)}: {gosterim}")
        hesap[f"{alan_adi}_{sira}"] = deger
    return satirlar


def _manset_parcasi(
    soru: str,
    uygunlar: list[UygunlukSonucu],
    kimlik_kampanya: dict[str, Kampanya],
) -> CevapParcasi | None:
    """SORULAN ÖLÇÜTÜN cevabını tek cümleyle, listeden ÖNCE söyler.

    NEDEN VAR (27 Ağustos, jüri havuzu 9. madde):

        soru  : «… en düşük kâr payı oranını hangi katılım bankası sunuyor?»
        cevap : «**… profiline 10 kampanya uygun.** … 1. Albaraka …»

    Cevap doğruydu ama soruya CÜMLEYLE karşılık vermiyordu: sorulan şey bir
    banka adı, dönen şey bir döküm. Jüri «hangi banka» cevabını listenin ilk
    maddesinden kendi çıkarmak zorundaydı.

    SIRALAMA DEĞİŞMİYOR — liste toplam maliyete göre kalır; muhakeme ajanının
    docstring'i bunu savunuyor («en düşük oran her zaman en ucuz değildir») ve
    doğrudur. Değişen tek şey, sorulan ölçütün cevabının da AYRICA yazılması.
    İkisi ayrıştığında bunu görmek gerekir: manşet oranı, liste maliyeti
    söyler ve fark okunur olur. Ölçüldü — bu soruda ikisi örtüşüyor
    (%2,87 hem en düşük oran hem en düşük maliyet), ama tahsis ücreti
    farklıysa örtüşmeyebilirler.

    Ölçüt ya da yön çözülemezse manşet YAZILMAZ: uydurulmuş bir yön, yanlış
    kaydı vitrine koymaktır (ADR 023).
    """
    olcut, yon = sorulan_olcut_ve_yon(soru)
    if olcut is None or yon is None:
        return None

    # ADR 020 KAPISI MANŞETE DE UYGULANIR. `_maliyet_hesapla` oranı zaten
    # makullük için süzüyor (0 < oran < 15) ama ÜRÜN SINIFI için süzmüyordu;
    # manşet oranı doğrudan okuduğu için «vade farksız 6 taksit» promosyonunun
    # %0'ı «en düşük kâr payı oranı» diye vitrine çıkabilirdi. Kapı
    # `karsilastirma`'daki tek beyandan okunur — ikinci bir eşik yazılmaz.
    adaylar: list[tuple[float, UygunlukSonucu, Alan]] = []
    for sonuc in uygunlar:
        kampanya = kimlik_kampanya.get(sonuc.kampanya_id)
        alan = getattr(kampanya, olcut, None)
        if alan is None or alan.deger is None:
            continue
        turu = kampanya.kampanya_turu.deger if kampanya.kampanya_turu else None
        if not turu_olcut_kapsaminda(turu, olcut):
            continue
        adaylar.append((float(alan.deger), sonuc, alan))
    if not adaylar:
        return None

    # ANAHTAR ŞART: demet sıralamasına güvenilirse iki kayıt AYNI değerde
    # eşitlendiğinde Python ikinci öğeyi kıyaslamaya geçer ve `UygunlukSonucu`
    # sıralanabilir değildir — `TypeError` ile çöker. Eşitlik istisna değil
    # kural: «500.000 TL taşıt finansmanı, 48 ay» sorgusunda uygun kayıtların
    # çoğu aynı oranı taşıyor. Kıyas yalnız SAYIYA yapılır; eşitlikte ilk
    # gelen kazanır ve sıra `MuhakemeAjani` tarafından zaten belirlenmiştir.
    def _deger(aday: tuple[float, UygunlukSonucu, Alan]) -> float:
        return aday[0]

    en_iyi = min(adaylar, key=_deger) if yon == "dusuk_iyi" else max(adaylar, key=_deger)
    deger, sonuc, alan = en_iyi
    nitelik = "en düşük" if yon == "dusuk_iyi" else "en yüksek"
    gosterim = alan_goster(olcut, alan.deger, _alan_birimi(olcut, alan))
    return CevapParcasi(
        f"**Profile uyan kampanyalar arasında {nitelik} "
        f"{alan_etiketi(olcut).lower()}: {sonuc.banka_adi} — {gosterim}.**\n",
        Koken.SISTEM,
        hesap={"manset_deger": deger},
    )


def _profil_cevabi(
    profil: MusteriProfili,
    sonuclar: list[UygunlukSonucu],
    kampanyalar: list[Kampanya] | None = None,
    *,
    soru: str = "",
) -> Cevap:
    """Uygunluk sonuçlarını gerekçeli metne çevirir — KÖKEN TİPLİ parçalarla.

    ESKİDEN MİRAS YOLDAYDI ve iki ayrı delik açıyordu (26 Ağustos, ölçüldü):

        `metin=` / `dogrulanacak_metin=` çağrısı, taksit ve toplam geri ödeme
        satırlarını `Koken.DENETIMSIZ` yapıyordu. Yani sistemin ürettiği en
        riskli sayılar — müşteriye söylenecek aylık taksit — hiçbir denetimden
        geçmiyordu. Üstelik `Orkestrator.calistir` profil kolunda kalkanı hiç
        çağırmıyordu; yani çağrılsa bile o parçalar atlanacaktı.

    NEDEN HEPSİ `SISTEM`, HİÇBİRİ `YAPISAL`:
        Bu cevaptaki sayıların TAMAMI ya bizim hesabımızdır ya da müşterinin
        kendi girdisidir; hiçbiri bir kampanya kaydının sütununda durmuyor.
        `YAPISAL` ölçütü («kayıtta birebir karşılığı olmalı») uygulanırsa
        müşterinin yazdığı «800.000 TL» bile uydurma sayılır ve meşru cevap
        bloke olur — ölçüldü:

            kalkan ÇAĞRILSA sonucu : REDDETTİ ['800.000', '120']

        `SISTEM` ölçütü doğru olanıdır: «sayılar `hesap` girdilerinden yeniden
        üretilebilmeli». Bu bir GEVŞETME DEĞİL sertleştirmedir — eskiden bu
        satırlar hiç denetlenmiyordu, artık her biri kendi girdisine karşı
        doğrulanıyor. Açıklamaya elle yazılmış bir taksit tutarı yakalanır.
    """
    uygunlar = [s for s in sonuclar if s.uygun_mu]
    elenenler = [s for s in sonuclar if not s.uygun_mu]
    kimlik_kampanya = {k.kampanya_id: k for k in (kampanyalar or [])}

    # Müşterinin kendi girdisi her parçada geçebilir (profil özeti) — ortak taban.
    profil_hesabi = {"talep_tutar": profil.tutar, "talep_vade": float(profil.vade_ay)}

    def _engel_parcasi(baslik: str) -> CevapParcasi | None:
        """Elenen kampanyaların sebepleri + o sebeplerin KAYNAK sayıları.

        Sayılar `Gerekce.sayilar`'dan geliyor: açıklamayı yazan kontrol,
        içindeki sayıyı da beyan ediyor. Bu olmadan «Azami vade 60 ay; talep
        120 ay.» cümlesi denetlenemezdi — iki sayı da gerçek ama ikisi de
        yapısal sütunlarda yok.
        """
        satirlar: list[str] = []
        hesap = dict(profil_hesabi)
        for sira, sonuc in enumerate(elenenler[:LISTE_UST_SINIRI], 1):
            for no, gerekce in enumerate(sonuc.engelleyenler()):
                satirlar.append(f"- **{sonuc.banka_adi}**: {gerekce.aciklama}")
                # DİKKAT: `hesap.update(gerekce.sayilar)` DEĞİL — anahtarlar bankadan
                # bağımsız sabit adlar (`max_tutar`, `max_vade_ay`, ...). Beş banka
                # listelenince sonuncusu öncekileri EZİYORDU; ezilen sayı izin
                # listesinden düşünce kalkan, sistemin kendi beyan ettiği değeri
                # «doğrulanamadı» diye reddediyordu. Ölçüldü (26 Ağu): «Maaş
                # müşterisiyim, 800.000 TL, 120 ay» sorgusu 125.000 ve 36 yüzünden
                # tamamen reddediliyordu — chatbot'un amiral gemisi senaryosu.
                # `_sistem_dogrula` yalnız `.values()` okur; anahtarın adı değil
                # BENZERSİZLİĞİ önemlidir.
                for anahtar, deger in gerekce.sayilar.items():
                    hesap[f"{anahtar}_{sira}_{no}"] = deger
        if not satirlar:
            return None
        # KIRPMA BEYAN EDİLİR — bkz. `LISTE_UST_SINIRI`.
        if len(elenenler) > LISTE_UST_SINIRI:
            gizli = len(elenenler) - LISTE_UST_SINIRI
            satirlar.append(
                f"- *(ayrıca {gizli} kampanya daha elendi; ilk "
                f"{LISTE_UST_SINIRI} sebep gösteriliyor)*"
            )
            hesap["elenen_gizli"] = float(gizli)
            hesap["liste_ust_siniri"] = float(LISTE_UST_SINIRI)
        govde = baslik + "\n" + "\n".join(satirlar)
        return CevapParcasi(govde, Koken.SISTEM, hesap=hesap)

    if not uygunlar:
        parcalar = [
            CevapParcasi(
                f"**{profil.ozet()}** profiline uygun kampanya bulunamadı.",
                Koken.SISTEM,
                hesap=profil_hesabi,
            )
        ]
        engel = _engel_parcasi("\n**Neden uygun değiller:**")
        if engel is not None:
            parcalar.append(engel)
        return Cevap(parcalar=parcalar, niyet=Niyet.KOSUL_SORGUSU)

    # DÜRÜSTLÜK KAPISI: `uygunluk` koşulları henüz çıkarılmamış kayıtlar
    # elenmedikleri için "uygun" görünür. Hepsi böyleyse hiçbir kısıt
    # doğrulanmamış demektir; bunu satır başlarına gömüp geçmek, sistemin
    # yapmadığı bir filtrelemeyi yapmış gibi sunmak olurdu.
    dogrulanmamis = sum(1 for s in uygunlar if s.veri_eksik)

    # BANKA SAYISI DA SÖYLENİR: «hangi banka» sorusunda kampanya sayısı tek
    # başına yanıltır — on kampanyanın üçü aynı bankadan olabilir ve nitekim
    # öyleydi (ilk beşin üçü Albaraka).
    uygun_bankalar = {s.banka_adi for s in uygunlar}
    baslik_satirlari = [
        f"**{profil.ozet()}** profiline **{len(uygunlar)} kampanya** uygun "
        f"({len(uygun_bankalar)} banka)."
    ]
    if len(uygunlar) > LISTE_UST_SINIRI:
        baslik_satirlari.append(
            f"\n> Aşağıda maliyeti en düşük **{LISTE_UST_SINIRI} kampanya** "
            f"listeleniyor; kalan {len(uygunlar) - LISTE_UST_SINIRI} kampanya "
            "gösterilmiyor.\n"
        )
    if dogrulanmamis == len(uygunlar):
        baslik_satirlari.append(
            "\n> **Bu kampanyaların hiçbirinde uygunluk koşulu çıkarılamadı.**\n"
            "> Liste profile göre SÜZÜLMEMİŞTİR; yalnız maliyete göre sıralanmıştır.\n"
        )
    elif dogrulanmamis:
        baslik_satirlari.append(
            f"\n> {dogrulanmamis} kampanyanın uygunluk koşulu çıkarılamadı; "
            "onlar için kısıtlar doğrulanmadı.\n"
        )

    parcalar: list[CevapParcasi] = []
    manset = _manset_parcasi(soru, uygunlar, kimlik_kampanya)
    if manset is not None:
        parcalar.append(manset)
    parcalar.append(
        CevapParcasi(
            "\n".join(baslik_satirlari),
            Koken.SISTEM,
            # Sayımlar da denetlenir: «3 kampanya uygun» yazıp beş göstermek
            # bir iddiadır ve yeniden üretilebilir olmalıdır.
            hesap={
                **profil_hesabi,
                "uygun_sayisi": float(len(uygunlar)),
                "uygun_banka_sayisi": float(len(uygun_bankalar)),
                "liste_ust_siniri": float(LISTE_UST_SINIRI),
                "gizlenen_sayisi": float(max(0, len(uygunlar) - LISTE_UST_SINIRI)),
                "dogrulanmamis_sayisi": float(dogrulanmamis),
            },
        )
    )

    # -- Maliyet listesi: her sayı kendi hesabından yeniden üretilebilmeli --
    #
    # SIRALAMA İDDİASI KOŞULA BAĞLI (27 Ağustos). Başlık koşulsuz yazılıyordu
    # ve hiçbir kalemin maliyeti hesaplanamadığında bile «Toplam maliyete göre
    # sıralı» diyordu — yapılmamış bir sıralamayı yapılmış gibi sunmak.
    # Ölçüldü: Kuveyt Türk ve Emlak Katılım'ın 11 konut kaydının HİÇBİRİNDE
    # kâr payı oranı yayımlanmamış (sayfalardaki yüzdeler kredi/değer oranı ve
    # tahsis ücreti; oran bankanın hesaplama aracının arkasında).
    hesaplanabilir = sum(1 for s in uygunlar[:LISTE_UST_SINIRI] if s.maliyet)
    if hesaplanabilir:
        maliyet_basligi = "**Toplam maliyete göre sıralı:**"
    else:
        maliyet_basligi = (
            "**Toplam maliyet sıralaması yapılamadı** — aşağıdaki kampanyaların "
            "hiçbirinde kâr payı oranı yayımlanmamış. Bilinen alanlar veriliyor; "
            "oran için bankanın kendi hesaplama aracına bakılmalı."
        )
    maliyet_satirlari: list[str] = ["", maliyet_basligi, ""]
    maliyet_hesabi = dict(profil_hesabi)

    for sira, sonuc in enumerate(uygunlar[:LISTE_UST_SINIRI], 1):
        maliyet_satirlari.append(f"{sira}. **{sonuc.banka_adi}**")
        # Sıra numarası tek haneli olduğu sürece kalkan onu zaten atlıyor
        # (`_metindeki_sayilar` tek haneleri saymaz). Yine de hesaba yazılıyor:
        # liste bir gün beşten uzarsa «10.» sessiz bir rede dönüşmesin.
        maliyet_hesabi[f"sira_{sira}"] = float(sira)

        if sonuc.maliyet:
            # ORAN DA YAZILIR (27 Ağustos, jüri havuzu 9. madde).
            #
            # «En düşük kâr payı oranını hangi banka sunuyor?» sorusuna cevap
            # yalnız taksit ve toplam geri ödeme veriyordu. Sıralamayı toplam
            # maliyete göre yapmak DOĞRUDUR — sunumun 02. sayfası bunu
            # savunuyor — ama sorulan sayıyı hiç yazmamak, soruyu
            # yanıtlamamaktır. İkisi birden gösterilir; kullanıcı manşet oranla
            # gerçek maliyetin ayrıştığını da görür.
            oran = getattr(kimlik_kampanya.get(sonuc.kampanya_id), "kar_payi_orani", None)
            if oran is not None and oran.deger is not None:
                maliyet_satirlari.append(
                    f"   - Kâr payı oranı: aylık %{sayi_goster(float(oran.deger))}"
                )
                maliyet_hesabi[f"oran_{sira}"] = float(oran.deger)

            aylik = f"{sonuc.maliyet['aylik_taksit']:,.0f}".replace(",", ".")
            toplam = f"{sonuc.maliyet['toplam_geri_odeme']:,.0f}".replace(",", ".")
            maliyet_satirlari.append(f"   - Aylık taksit: {aylik} TL")
            maliyet_satirlari.append(f"   - Toplam geri ödeme: {toplam} TL")
            maliyet_hesabi[f"aylik_taksit_{sira}"] = sonuc.maliyet["aylik_taksit"]
            maliyet_hesabi[f"toplam_{sira}"] = sonuc.maliyet["toplam_geri_odeme"]
        else:
            maliyet_satirlari.append(
                "   - Kâr payı oranı **Belirtilmemiş**, maliyet hesaplanamadı."
            )
            # BİLİNENİ SAKLAMA: tahsis ücreti, vade ve tutar dolu olabilir.
            maliyet_satirlari += _bilinen_satirlar(
                kimlik_kampanya.get(sonuc.kampanya_id), sira, maliyet_hesabi
            )
        if sonuc.veri_eksik:
            maliyet_satirlari.append(
                "   - Uygunluk koşulları metinden çıkarılamadı; kısıtlar doğrulanmadı."
            )

    parcalar.append(
        CevapParcasi("\n".join(maliyet_satirlari), Koken.SISTEM, hesap=maliyet_hesabi)
    )

    engel = _engel_parcasi("\n**Uygun olmayanlar ve sebepleri:**")
    if engel is not None:
        parcalar.append(engel)

    # (kimlik_kampanya yukarıda kuruldu — kaynakça da, oran satırı da onu kullanır.)
    # KAYNAK URL'İ BOŞ GEÇİLMEZ (27 Ağustos).
    #
    # `UygunlukSonucu` yalnız `kampanya_id` ve `banka_adi` taşıyor; URL ve
    # çekim tarihi `Kampanya` nesnesinde duruyor ve buraya hiç geçirilmiyordu.
    # Sonuç, kaynakçanın beş satırının da adresinin BOŞ olmasıydı:
    #
    #     Türkiye Finans Katılım Bankası A.Ş.  |  (adres yok)
    #
    # Projenin merkez iddiası «kanıtsız değer üretilemez»; jüri aylık taksit
    # ve toplam geri ödemeyi görüp kaynağa tıklayamıyorsa iddia orada kırılır.
    # Chatbot yolu bunu `_kaynakca` ile doğru yapıyordu, profil yolu yapmıyordu.
    return Cevap(
        parcalar=parcalar,
        niyet=Niyet.KOSUL_SORGUSU,
        kaynaklar=[_profil_kaynagi(s, kimlik_kampanya) for s in uygunlar[:LISTE_UST_SINIRI]],
    )


def _banka_suz(soru: str, kampanyalar: list[Kampanya]) -> list[Kampanya]:
    """Soruda banka adlandırılmışsa kampanyaları ona daraltır.

    NEDEN VAR — 27 Ağustos'ta ölçüldü (çok turlu sohbet bunu görünür kıldı):

        soru  : «Albaraka'dan 1.000.000 TL konut finansmanı, 120 ay vade»
        cevap : dokuz bankanın 18 kampanyası, toplam maliyete göre sıralı

    Adlandırılan banka cevapta hiç dikkate alınmıyordu. Ürün süzgeci profil
    koluna eklenmişti (`_urun_suz`), bankanınki hiç yoktu.

    Eşleştirme `rag.chatbot`'tan gelir (`sorulan_bankalar`); iki kolda iki
    eşleştirici tutulmaz — yazım hatası toleransı, benzersiz sözcük kapısı ve
    «hangi banka» ayrımı burada da kendiliğinden geçerlidir.

    BANKA SÜZGECİ ÜRÜNDEN ÖNCE koşar. Sonra koşsaydı ad kümesi ürün süzgeci
    tarafından daraltılmış olurdu: «Albaraka konut» sorusunda Albaraka'nın
    konut kaydı yoksa Albaraka ad kümesinden düşer, süzgeç hiçbir şey bulamaz
    ve DOKUZ bankanın tamamını geri verirdi — yani sorulmayan bankalar.
    """
    adlar = set(sorulan_bankalar(soru, (k.banka_adi for k in kampanyalar)))
    if not adlar:
        return kampanyalar
    return [k for k in kampanyalar if k.banka_adi in adlar]


def _urun_suz(soru: str, kampanyalar: list[Kampanya]) -> list[Kampanya]:
    """Soruda ürün adlandırılmışsa kampanyaları ona daraltır.

    Eşleştirme `rag.chatbot`'tan gelir; iki kolda iki sözlük tutulmaz.
    """
    etiket = sorulan_urun(soru)
    if etiket is None:
        return kampanyalar
    return [
        k for k in kampanyalar
        if urun_etiketi_uyar(
            etiket, k.kampanya_turu.deger, k.urun_turu.deger, k.kaynak_url
        )
    ]


def _profil_kaynagi(
    sonuc: UygunlukSonucu, kimlik_kampanya: dict[str, Kampanya]
) -> Kaynakca:
    """Uygunluk sonucunu kaynakçaya çevirir — adresiyle birlikte."""
    kampanya = kimlik_kampanya.get(sonuc.kampanya_id)
    if kampanya is None:
        return Kaynakca(banka_adi=sonuc.banka_adi, url="", cekim_tarihi="")
    return Kaynakca(
        banka_adi=sonuc.banka_adi,
        url=kampanya.kaynak_url,
        cekim_tarihi=kampanya.cekim_tarihi.strftime("%d.%m.%Y")
        if kampanya.cekim_tarihi
        else "",
    )


# ---------------------------------------------------------------------------
# Orkestratör
# ---------------------------------------------------------------------------


class Orkestrator:
    """İsteği çözümler, ajanları sıralar, izleri toplar."""

    ad = "orkestrator"
    llm_kullanir = False

    def __init__(self, muhakeme: MuhakemeAjani | None = None) -> None:
        self.muhakeme = muhakeme or MuhakemeAjani()

    def niyet_coz(self, soru: str) -> str:
        """Beş sınıf: dört mevcut niyet + profil sorgusu."""
        if profil_sorgusu_mu(soru):
            return PROFIL_SORGUSU
        return niyet_belirle(soru).value

    def calistir(
        self,
        soru: str,
        kampanyalar: list[Kampanya] | None = None,
        *,
        kayitlar: list[KampanyaKaydi] | None = None,
        baglam: SohbetBaglami | None = None,
    ) -> tuple[Cevap, IzDefteri]:
        """Tek giriş noktası. `(cevap, iz_defteri)` döner.

        İKİ AYRI KOLEKSİYON, İKİ AYRI TİP — karıştırmayın:
          * `kampanyalar` (`Kampanya`) muhakeme ajanının girdisi; kanıt
            zinciri ve `uygunluk` kısıtları orada duruyor.
          * `kayitlar` (`KampanyaKaydi`) chatbot'un girdisi; düz sütunlar
            üzerinden sorgulanıyor ve sayısal kalkanın izin listesi ondan
            doğuyor.

        İkisi de opsiyonel ve verilmezse ilgili kol kendi okumasını yapar.
        Arayüz ikisini de geçirebilir: Streamlit her etkileşimde betiği baştan
        koşturduğu için, sayfanın önbelleğindeki listeyi tekrar okutmak
        1.024 kaydı ve ~12 MB ham metni boşuna diskten çekmek olurdu.

        `baglam` ÇOK TURLU SOHBETİ açar (bkz. `src/rag/baglam.py`). Devir
        YÖNLENDİRMEDEN ÖNCE uygulanır ve sebebi ölçüldü (27 Ağustos):

            tur 1: «1.000.000 TL konut finansmanı istiyorum»
                     -> «Uygunluk değerlendirmesi için eksik: vade»
            tur 2: «120 ay vade»
                     -> Kuveyt Türk, Alışveriş Puanı Kampanyası      ✗

        Yani SİSTEM SORUYU KENDİ SORUYOR, CEVABINI KULLANAMIYOR: niyet ham
        soruya bakılarak çözüldüğü için «120 ay vade» muhakeme ajanına hiç
        ulaşmıyor, tutar yuvası boş kaldığı için profil kurulamıyordu.
        """
        defter = IzDefteri()
        devir = self._devir(soru, baglam, kayitlar)

        with iz_tut(self.ad, llm=False, girdi=soru[:80]) as iz:
            niyet = self.niyet_coz(devir.soru)
            iz.cikti_ozeti = niyet
            iz.karar_gerekcesi = self._yonlendirme_gerekcesi(devir.soru, niyet)
            if devir.var_mi():
                iz.karar_gerekcesi += (
                    " · devralınan yuva: "
                    + ", ".join(etiket for etiket, _ in devir.yuvalar)
                )
        defter.ekle(iz)

        if niyet != PROFIL_SORGUSU:
            # HAM SORU geçiriliyor, devir değil: `chatbot.sor` aynı devri
            # kendi kapılarından SONRA uygular (kapsam kalkanı ham soruya
            # çalışmak zorunda) ve beyanı kendi kalkanından geçirir.
            cevap, chatbot_izi = self._chatbot_yolu(soru, kayitlar, baglam)
            defter.ekle(chatbot_izi)
            return cevap, defter

        soru = devir.soru
        if kayitlar is None:
            # Bağlam bankayı SORUDAN çözüyor (cevabın yapısal parçası yok);
            # bunun için ad kümesi gerekiyor. API kolu kayıt geçirmiyor.
            from src.depolama import tum_kayitlar

            kayitlar = tum_kayitlar()
        profil, eksikler = self._profil_izi(soru, defter)
        if profil is None:
            # KÖKEN `SISTEM`, `DUZ` DEĞİL — kalkan bu hatayı kuruluşta yakaladı.
            # `eksikler` girdileri ÖRNEK SAYI taşıyor ("vade (örn. 120 ay veya
            # 10 yıl)"), dolayısıyla metin sayısız değil. `DUZ` sözleşmesi
            # («sayı içeremez») haklı olarak reddetti; doğru köken, sayıları
            # `hesap`'tan yeniden üretilebilen `SISTEM`.
            #
            # Bu sayılar bir veri iddiası değil, arayüz metnindeki örnekler —
            # ama denetimsiz de bırakılmıyorlar: hiçbir parça `DENETIMSIZ`
            # kalmadığı için `eval`'deki denetimsiz parça oranı sıfır kalır.
            eksik_cevap = Cevap(
                parcalar=[
                    CevapParcasi(
                        "Uygunluk değerlendirmesi için şu bilgiler eksik: "
                        + ", ".join(eksikler)
                        + ".\n\nÖrnek: *\"Maaş müşterisi, 800.000 TL konut "
                        "finansmanı, 10 yıl vade\"*",
                        Koken.SISTEM,
                        hesap={
                            # `profil_ayristir`'ın ürettiği ipuçlarındaki
                            # örnek değerler + örnek cümledeki tutar.
                            "ornek_tutar": 800_000.0,
                            "ornek_vade_ay": 120.0,
                            "ornek_vade_yil": 10.0,
                        },
                    )
                ],
                niyet=Niyet.KOSUL_SORGUSU,
                # SORULAN YUVA BEYAN EDİLİR — sonraki tur duyabilsin.
                beklenen_yuvalar=eksik_nicelikler(soru),
            )
            # EKSİK BİLGİ DALI DA KALKANDAN GEÇER. İki sebep: devir beyanı
            # devralınan TUTARI yazabiliyor (sayı taşıyan bir iddia), ve bu
            # daldaki örnek değerler («800.000 TL … 10 yıl») bugüne dek hiç
            # denetlenmemişti — `hesap` doğru kuruluysa kalkan sessiz kalır.
            self._beyan_ekle(eksik_cevap, devir)
            eksik_cevap = self._kalkandan_gecir(eksik_cevap, defter)
            eksik_cevap.baglam = baglam_guncelle(
                soru,
                eksik_cevap,
                baglam,
                kayitlar=kayitlar,
                profil_kipi=True,
                tutar=para_ayristir(soru, birim_zorunlu=True),
                vade_ay=vade_ayristir(soru),
            )
            return eksik_cevap, defter

        if kampanyalar is None:
            from src.depolama import kampanyalari_oku

            kampanyalar = list(kampanyalari_oku())

        # ÜRÜN SÜZGECİ PROFİL KOLUNDA DA İŞLER (27 Ağustos).
        #
        # Jüri havuzu 9. madde: «120 ay vadeli 1.000.000 TL KONUT FİNANSMANI
        # için en düşük kâr payı oranını hangi banka sunuyor?» Süzgeç yalnız
        # chatbot kolundaydı; profil kolu 357 kampanyanın tamamını sıralıyor
        # ve listenin başına kart, döviz, hızlı finansman kampanyaları
        # koyuyordu. Sorulan ürün cevapta hiç dikkate alınmıyordu.
        #
        # Süzgeç kümeyi boşaltırsa sonuç boş kalır ve cevap «uygun kampanya
        # bulunamadı» der — sorulmayan ürünle doldurmaktan doğrudur.
        #
        # BANKA SÜZGECİ 27 Ağustos'ta eklendi ve aynı gerekçeyle ÖNCE koşar
        # (bkz. `_banka_suz`).
        kampanyalar = _urun_suz(soru, _banka_suz(soru, kampanyalar))


        sonuclar, muhakeme_izi = self.muhakeme.calistir((profil, kampanyalar))
        defter.ekle(muhakeme_izi)

        with iz_tut("cevap", llm=False, girdi=f"{len(sonuclar)} sonuç") as iz:
            cevap = _profil_cevabi(profil, sonuclar, kampanyalar, soru=soru)
            uygun = sum(1 for s in sonuclar if s.uygun_mu)
            iz.cikti_ozeti = f"{uygun} uygun kampanya sunuldu"
            iz.karar_gerekcesi = "Gerekçeler ve maliyetler kaynaklarıyla yazıldı"
        defter.ekle(iz)

        # SAYISAL DOĞRULAMA KALKANI — profil kolunda da (26 Ağustos).
        #
        # Bu çağrı EKSİKTİ. Chatbot yolu `chatbot.sor` içinde kalkandan
        # geçiyordu ama profil yolu doğrudan dönüyordu; yani sistemin ürettiği
        # en riskli sayılar — müşteriye söylenecek aylık taksit ve toplam geri
        # ödeme — hiçbir denetimden geçmeden ekrana gidiyordu.
        #
        # `docs/SONUCLAR.md`'deki «denetimsiz cevap parçası %0,0» ölçümü bu
        # deliği göremiyordu: o ölçüm `eval/sorular.yaml` üzerinden yalnız
        # `chatbot.sor` yolunu kat ediyor, profil yolunu hiç ziyaret etmiyor.
        #
        # `kullanilan_kayitlar` boş: bu cevapta YAPISAL parça yok, tamamı
        # SISTEM kökenli (gerekçesi `_profil_cevabi` docstring'inde).
        self._beyan_ekle(cevap, devir)
        cevap = self._kalkandan_gecir(cevap, defter)
        cevap.baglam = baglam_guncelle(
            soru,
            cevap,
            baglam,
            kayitlar=kayitlar,
            profil_kipi=True,
            tutar=profil.tutar,
            vade_ay=profil.vade_ay,
        )
        return cevap, defter

    @staticmethod
    def _kalkandan_gecir(cevap: Cevap, defter: IzDefteri) -> Cevap:
        """Kalkanı uygular ve kararını ize yazar — jüri ekranda görebilsin."""
        with iz_tut("kalkan", llm=False, girdi=f"{len(cevap.parcalar)} parça") as iz:
            gecti, reddedilen = kalkandan_gecir(cevap, cevap.kullanilan_kayitlar)
            cevap.dogrulama_gecti = gecti
            cevap.reddedilen_sayilar = reddedilen
            iz.cikti_ozeti = "geçti" if gecti else "REDDETTİ"
            iz.karar_gerekcesi = (
                f"{len(cevap.parcalar)} parçanın tamamı kökenine göre doğrulandı"
                if gecti
                else f"Doğrulanamayan sayılar: {', '.join(reddedilen[:6])}"
            )
        defter.ekle(iz)

        if gecti:
            return cevap

        return Cevap(
            parcalar=[
                CevapParcasi(
                    "Cevabı üretirken doğrulayamadığım sayısal değerler oluştu, "
                    "bu yüzden cevabı vermiyorum. Bu bilgi veri setinde "
                    "doğrulanabilir biçimde bulunmuyor.",
                    Koken.DUZ,
                )
            ],
            niyet=cevap.niyet,
            dogrulama_gecti=False,
            reddedilen_sayilar=reddedilen,
        )

    # -- iç ---------------------------------------------------------------

    @staticmethod
    def _yonlendirme_gerekcesi(soru: str, niyet: str) -> str:
        """Hangi kuralın tetiklendiğini DOĞRU söyler.

        İz kaydı jüriye gösterilen kanıt; "tutar + vade birlikte geçiyor"
        yazarken aslında anahtar sözcük yolunun çalışmış olması, mekanizmanın
        kendisini şüpheli hâle getirir.
        """
        if niyet != PROFIL_SORGUSU:
            return f"kelime örüntüsü → {niyet}"
        tutar_var = para_ayristir(soru, birim_zorunlu=True) is not None
        vade_var = vade_ayristir(soru) is not None
        if tutar_var and vade_var:
            return "tutar + vade birlikte geçiyor → muhakeme ajanı"
        bulunan = "tutar" if tutar_var else "vade"
        return f"{bulunan} + müşteri ipucu → muhakeme ajanı (eksik bilgi sorulacak)"

    @staticmethod
    def _devir(
        soru: str,
        baglam: SohbetBaglami | None,
        kayitlar: list[KampanyaKaydi] | None,
    ) -> Devir:
        """Yuva devri. Bağlam boşken korpus OKUNMAZ — tek turlu yol eskisi gibi."""
        if baglam is None or baglam.bos_mu():
            return Devir(soru)
        if kayitlar is None:
            from src.depolama import tum_kayitlar

            kayitlar = tum_kayitlar()
        return soruyu_tamamla(soru, baglam, kayitlar)

    @staticmethod
    def _beyan_ekle(cevap: Cevap, devir: Devir) -> None:
        """Devir beyanını cevaba ekler — KALKANDAN ÖNCE çağrılmalıdır."""
        beyan = devir.parca()
        if beyan is not None:
            cevap.parcalar.append(beyan)

    @staticmethod
    def _chatbot_yolu(
        soru: str,
        kayitlar: list[KampanyaKaydi] | None = None,
        baglam: SohbetBaglami | None = None,
    ) -> tuple[Cevap, AjanIzi]:
        """Chatbot kolu. Kalkan `chatbot.sor`'un İÇİNDE uygulanır, burada değil.

        `kayitlar` geçirilirse chatbot yeniden okuma yapmaz — çağıran zaten
        elinde tutuyorsa aynı listeyi iki kez diskten çekmenin anlamı yok.
        """
        with iz_tut("cevap", llm=False, girdi=soru[:80]) as iz:
            cevap = chatbot_sor(soru, kayitlar, baglam=baglam)
            iz.cikti_ozeti = cevap.niyet.value
            iz.karar_gerekcesi = (
                f"Sayısal doğrulama kalkanı: "
                f"{'geçti' if cevap.dogrulama_gecti else 'REDDETTİ'}"
            )
        return cevap, iz

    @staticmethod
    def _profil_izi(soru: str, defter: IzDefteri) -> tuple[MusteriProfili | None, list[str]]:
        with iz_tut("profil_ayristirma", llm=False, girdi=soru[:80]) as iz:
            profil, eksikler = profil_ayristir(soru)
            if profil is None:
                iz.cikti_ozeti = "eksik bilgi"
                iz.karar_gerekcesi = f"Tahmin edilmedi, soruldu: {', '.join(eksikler)}"
            else:
                iz.cikti_ozeti = profil.ozet()
                iz.karar_gerekcesi = "Tutar, vade ve müşteri tipi metinden okundu"
        defter.ekle(iz)
        return profil, eksikler


__all__ = ["PROFIL_SORGUSU", "Orkestrator", "profil_ayristir", "profil_sorgusu_mu"]
