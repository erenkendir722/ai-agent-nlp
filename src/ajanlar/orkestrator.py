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
    kalkandan_gecir,
    niyet_belirle,
)
from src.rag.chatbot import sor as chatbot_sor
from src.schema import HedefKitle, Kampanya

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
    if tip is None:
        eksikler.append("müşteri tipi (yeni / mevcut / maaş / emekli)")

    if eksikler:
        return None, eksikler

    assert tutar is not None and vade is not None and tip is not None
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


def _profil_cevabi(
    profil: MusteriProfili, sonuclar: list[UygunlukSonucu]
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
        for sira, sonuc in enumerate(elenenler[:5], 1):
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

    baslik_satirlari = [
        f"**{profil.ozet()}** profiline **{len(uygunlar)} kampanya** uygun."
    ]
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

    parcalar = [
        CevapParcasi(
            "\n".join(baslik_satirlari),
            Koken.SISTEM,
            # Sayımlar da denetlenir: «3 kampanya uygun» yazıp beş göstermek
            # bir iddiadır ve yeniden üretilebilir olmalıdır.
            hesap={
                **profil_hesabi,
                "uygun_sayisi": float(len(uygunlar)),
                "dogrulanmamis_sayisi": float(dogrulanmamis),
            },
        )
    ]

    # -- Maliyet listesi: her sayı kendi hesabından yeniden üretilebilmeli --
    maliyet_satirlari: list[str] = ["", "**Toplam maliyete göre sıralı:**", ""]
    maliyet_hesabi = dict(profil_hesabi)

    for sira, sonuc in enumerate(uygunlar[:5], 1):
        maliyet_satirlari.append(f"{sira}. **{sonuc.banka_adi}**")
        # Sıra numarası tek haneli olduğu sürece kalkan onu zaten atlıyor
        # (`_metindeki_sayilar` tek haneleri saymaz). Yine de hesaba yazılıyor:
        # liste bir gün beşten uzarsa «10.» sessiz bir rede dönüşmesin.
        maliyet_hesabi[f"sira_{sira}"] = float(sira)

        if sonuc.maliyet:
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

    return Cevap(
        parcalar=parcalar,
        niyet=Niyet.KOSUL_SORGUSU,
        kaynaklar=[
            Kaynakca(banka_adi=s.banka_adi, url="", cekim_tarihi="")
            for s in uygunlar[:5]
        ],
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
        """
        defter = IzDefteri()

        with iz_tut(self.ad, llm=False, girdi=soru[:80]) as iz:
            niyet = self.niyet_coz(soru)
            iz.cikti_ozeti = niyet
            iz.karar_gerekcesi = self._yonlendirme_gerekcesi(soru, niyet)
        defter.ekle(iz)

        if niyet != PROFIL_SORGUSU:
            cevap, chatbot_izi = self._chatbot_yolu(soru, kayitlar)
            defter.ekle(chatbot_izi)
            return cevap, defter

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
            return (
                Cevap(
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
                ),
                defter,
            )

        if kampanyalar is None:
            from src.depolama import kampanyalari_oku

            kampanyalar = list(kampanyalari_oku())

        sonuclar, muhakeme_izi = self.muhakeme.calistir((profil, kampanyalar))
        defter.ekle(muhakeme_izi)

        with iz_tut("cevap", llm=False, girdi=f"{len(sonuclar)} sonuç") as iz:
            cevap = _profil_cevabi(profil, sonuclar)
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
        return self._kalkandan_gecir(cevap, defter), defter

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
    def _chatbot_yolu(
        soru: str, kayitlar: list[KampanyaKaydi] | None = None
    ) -> tuple[Cevap, AjanIzi]:
        """Chatbot kolu. Kalkan `chatbot.sor`'un İÇİNDE uygulanır, burada değil.

        `kayitlar` geçirilirse chatbot yeniden okuma yapmaz — çağıran zaten
        elinde tutuyorsa aynı listeyi iki kez diskten çekmenin anlamı yok.
        """
        with iz_tut("cevap", llm=False, girdi=soru[:80]) as iz:
            cevap = chatbot_sor(soru, kayitlar)
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
