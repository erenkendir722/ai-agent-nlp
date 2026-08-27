"""Orkestratörün testleri — yönlendirme, profil ayrıştırma, dürüstlük kapıları.

Ollama GEREKTİRMEZ: orkestratör kural tabanlıdır. Yönlendirmenin LLM'siz
olması bilinçli bir karar — demo sırasında öngörülebilir olması buna bağlı.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.ajanlar.muhakeme import MusteriProfili
from src.ajanlar.orkestrator import (
    PROFIL_SORGUSU,
    Orkestrator,
    profil_ayristir,
    profil_sorgusu_mu,
)
from src.schema import Alan, Birim, HedefKitle, Kampanya, UygunlukKosullari


def _alan(deger, ham: str) -> Alan:
    return Alan(deger=deger, ham_ifade=ham, guven=0.9, yontem="kural")


def _kampanya(
    ad="Test Bankası", *, oran=1.89, uygunluk=None, url=None,
    vade=None, tahsis=None, tahsis_birim=None, kimlik=None,
) -> Kampanya:
    return Kampanya(
        banka_adi=ad,
        banka_kodu="0299",
        kampanya_id=kimlik or f"0299-{ad}",
        kaynak_url=url or f"https://{ad}.test",
        cekim_tarihi=datetime(2026, 8, 14),
        kar_payi_orani=(
            _alan(oran, f"%{oran}") if oran is not None else Alan.yok()
        ),
        vade_ay_max=_alan(vade, f"{vade} ay") if vade is not None else Alan.yok(),
        tahsis_ucreti=(
            Alan(deger=tahsis, ham_ifade=f"%{tahsis}", guven=0.9,
                 yontem="kural", birim=tahsis_birim)
            if tahsis is not None
            else Alan.yok()
        ),
        uygunluk=uygunluk,
    )


@pytest.fixture
def ork() -> Orkestrator:
    return Orkestrator()


# ---------------------------------------------------------------------------
# Profil ayrıştırma
# ---------------------------------------------------------------------------


def test_tam_profil_okunur():
    profil, eksikler = profil_ayristir(
        "Maaş müşterisi, 800.000 TL konut finansmanı istiyor, 10 yıl vade"
    )
    assert eksikler == []
    assert profil == MusteriProfili(
        musteri_tipi=HedefKitle.MAAS_MUSTERISI, tutar=800_000.0, vade_ay=120
    )


def test_yil_aya_cevrilir():
    profil, _ = profil_ayristir("yeni müşteri 250 bin TL, 3 yıl")
    assert profil is not None
    assert profil.vade_ay == 36


def test_tutar_ve_vade_birbirine_karismaz():
    """'800.000 TL, 120 ay' — tutar ayrıştırıcısı vadeyi, vade ayrıştırıcısı
    tutarı yakalamamalı."""
    profil, _ = profil_ayristir("mevcut müşteri 800.000 TL, 120 ay")
    assert profil is not None
    assert (profil.tutar, profil.vade_ay) == (800_000.0, 120)


def test_segment_adi_okunur():
    profil, _ = profil_ayristir("emekli müşteri 300.000 TL, 60 ay")
    assert profil is not None
    assert profil.musteri_tipi == HedefKitle.SEGMENT
    assert profil.segment == "emekli"


@pytest.mark.parametrize(
    ("soru", "beklenen_eksik"),
    [
        ("maaş müşterisi 800.000 TL istiyor", "vade"),
        ("maaş müşterisi 120 ay vade istiyor", "tutar"),
    ],
)
def test_hesaba_giren_bilgi_tahmin_edilmez(soru, beklenen_eksik):
    """Varsayılan bir tutar veya vade koymak, taksitten toplam maliyete kadar
    her sayıyı sessizce yanlışlardı."""
    profil, eksikler = profil_ayristir(soru)
    assert profil is None
    assert any(beklenen_eksik in e for e in eksikler)


def test_musteri_tipi_eksikse_sorulmaz():
    """Tip hiçbir HESABA girmez, yalnız süzer — bilinmiyorken süzülmez.

    27 Ağustos, jüri havuzu 9. madde: «120 ay vadeli 1.000.000 TL konut
    finansmanı için en düşük kâr payı oranını hangi katılım bankası sunuyor?»
    bir SIRALAMA sorusudur, «ben uygun muyum?» değil. Tip sorulunca cevap
    yerine soru dönüyordu.
    """
    profil, eksikler = profil_ayristir("1.000.000 TL, 120 ay")
    assert profil is not None
    assert eksikler == []
    assert profil.musteri_tipi is None
    assert "belirtilmedi" in profil.ozet()


def test_belirtilmemis_tip_kampanyayi_elemez():
    """Tip belirtilmediğinde müşteri tipi kısıtı UYGULANMAZ."""
    from src.ajanlar.muhakeme import MuhakemeAjani

    profil = MusteriProfili(musteri_tipi=None, tutar=100_000.0, vade_ay=12)
    kampanya = _kampanya(
        uygunluk=UygunlukKosullari(musteri_tipi=[HedefKitle.YENI_MUSTERI])
    )

    sonuc = MuhakemeAjani().degerlendir(profil, kampanya)
    assert "musteri_tipi" not in [g.kural for g in sonuc.engelleyenler()]


# ---------------------------------------------------------------------------
# Yönlendirme
# ---------------------------------------------------------------------------


def test_tutar_ve_vade_profil_sorgusudur():
    assert profil_sorgusu_mu("800.000 TL, 120 ay") is True


def test_eksik_bilgili_profil_sorgusu_da_muhakemeye_gider():
    """Bu olmadan 'müşterim 500.000 TL istiyor' koşul sorgusu sanılıp kalkana
    takılıyordu; oysa yapılması gereken eksik vadeyi SORMAK."""
    assert profil_sorgusu_mu("Müşterim 500.000 TL istiyor") is True


def test_sayisiz_soru_profil_sorgusu_degildir():
    assert profil_sorgusu_mu("Kuveyt Türk mü daha avantajlı?") is False
    assert profil_sorgusu_mu("kampanya koşulları neler?") is False


def test_karsilastirma_sorusu_chatbota_gider(ork):
    assert ork.niyet_coz("Albaraka mı daha avantajlı, Kuveyt Türk mü?") != PROFIL_SORGUSU


def test_profil_sorusu_muhakemeye_gider(ork):
    assert ork.niyet_coz("maaş müşterisi 800.000 TL 120 ay") == PROFIL_SORGUSU


# ---------------------------------------------------------------------------
# Eksik bilgi -> sor
# ---------------------------------------------------------------------------


def test_eksik_bilgide_uydurmak_yerine_sorulur(ork):
    cevap, defter = ork.calistir("Müşterim 500.000 TL istiyor", [])
    assert "eksik" in cevap.metin.lower()
    assert "vade" in cevap.metin
    assert any("Tahmin edilmedi" in iz.karar_gerekcesi for iz in defter.izler)


# ---------------------------------------------------------------------------
# Dürüstlük kapısı — süzülmemiş liste süzülmüş gibi sunulmaz
# ---------------------------------------------------------------------------


def test_uygunluk_yoksa_liste_suzulmedigi_soylenir(ork):
    """96 mevcut kaydın hepsi böyle: uygunluk çıkarılmadığı için hiçbiri
    elenmiyor. Bunu satır aralarına gömmek, yapılmayan bir filtrelemeyi
    yapılmış gibi sunmak olurdu."""
    kampanyalar = [_kampanya("A", uygunluk=None), _kampanya("B", uygunluk=None)]
    cevap, _ = ork.calistir("maaş müşterisi 800.000 TL 120 ay", kampanyalar)
    assert "SÜZÜLMEMİŞTİR" in cevap.metin


def test_kismi_uygunlukta_sayi_bildirilir(ork):
    kampanyalar = [
        _kampanya("Dogrulanmis", uygunluk=UygunlukKosullari(max_vade_ay=120)),
        _kampanya("Bilinmeyen", uygunluk=None),
    ]
    cevap, _ = ork.calistir("maaş müşterisi 800.000 TL 120 ay", kampanyalar)
    assert "SÜZÜLMEMİŞTİR" not in cevap.metin
    assert "1 kampanyanın uygunluk koşulu çıkarılamadı" in cevap.metin


def test_hicbiri_uygun_degilse_sebepleri_yazilir(ork):
    kampanyalar = [_kampanya("Elenen", uygunluk=UygunlukKosullari(min_tutar=9_000_000.0))]
    cevap, _ = ork.calistir("maaş müşterisi 800.000 TL 120 ay", kampanyalar)
    assert "uygun kampanya bulunamadı" in cevap.metin
    assert "9.000.000" in cevap.metin


# ---------------------------------------------------------------------------
# İz kaydı
# ---------------------------------------------------------------------------


def test_izler_dogru_kurali_bildirir(ork):
    _, defter = ork.calistir("Müşterim 500.000 TL istiyor", [])
    gerekce = defter.izler[0].karar_gerekcesi
    assert "müşteri ipucu" in gerekce
    assert "tutar + vade birlikte" not in gerekce  # yanlış iz, mekanizmayı şüpheli yapar


def test_profil_yolunda_hicbir_ajan_llm_kullanmaz(ork):
    """Uygunluk muhakemesinin tamamı deterministik kod. Bu, 'aritmetiği ajana
    yaptırmıyoruz' iddiasının ekrandaki kanıtı."""
    _, defter = ork.calistir("maaş müşterisi 800.000 TL 120 ay", [_kampanya()])
    assert defter.llm_cagrisi_sayisi() == 0
    # orkestratör, profil, muhakeme, cevap, KALKAN
    # Kalkan izi 26 Ağustos'ta eklendi: profil kolu o güne dek kalkandan hiç
    # geçmiyordu ve taksit tutarları denetimsiz çıkıyordu.
    assert len(defter.izler) == 5


def test_profil_cevabi_kalkandan_gecer(ork):
    """Profil kolunun kalkan izi DEFTERDE olmalı — jüri ekranda görecek.

    NEDEN VAR: `Orkestrator.calistir` profil dalında `kalkandan_gecir`'i hiç
    çağırmıyordu. Chatbot yolu korunuyordu, profil yolu korunmuyordu; yani
    sistemin ürettiği en riskli sayılar (aylık taksit, toplam geri ödeme)
    denetimsiz geçiyordu.
    """
    cevap, defter = ork.calistir("maaş müşterisi 800.000 TL 120 ay", [_kampanya()])

    kalkan_izleri = [iz for iz in defter.izler if iz.ajan_adi == "kalkan"]
    assert len(kalkan_izleri) == 1, "Profil kolunda kalkan izi yok"
    assert cevap.dogrulama_gecti, f"Meşru cevap bloke edildi: {cevap.reddedilen_sayilar}"


def test_profil_cevabinda_denetimsiz_parca_kalmaz(ork):
    """Miras `metin=` yolu profil cevabından tümüyle çıktı.

    `DENETIMSIZ` köken kalkanın atladığı tek köken; `docs/SONUCLAR.md` bunu
    ölçülen teknik borç olarak raporluyor ve hedefi sıfır. Profil yolu bu
    ölçümün dışındaydı, çünkü ölçüm `eval/sorular.yaml` üzerinden yalnız
    `chatbot.sor`'u kat ediyor.
    """
    from src.rag.chatbot import Koken

    for soru, kampanyalar in (
        ("maaş müşterisi 800.000 TL 120 ay", [_kampanya()]),
        ("Müşterim 500.000 TL istiyor", []),  # eksik bilgi kolu
    ):
        cevap, _ = ork.calistir(soru, kampanyalar)
        assert cevap.denetimsiz_parca_sayisi() == 0, (
            f"{soru!r} cevabında denetimsiz parça var: "
            f"{[p.metin[:40] for p in cevap.parcalar if p.koken is Koken.DENETIMSIZ]}"
        )


def test_kalkan_sonucu_ize_yazilir(ork):
    _, defter = ork.calistir("kampanya koşulları neler?")
    assert any("kalkan" in iz.karar_gerekcesi.lower() for iz in defter.izler)


# ---------------------------------------------------------------------------
# Kalkan × çok banka — `hesap` anahtar çakışması
# ---------------------------------------------------------------------------


def _limitli(ad: str, *, max_tutar: float, max_vade: int) -> Kampanya:
    """Talebi karşılamayan, yani ELENECEK bir kampanya."""
    return _kampanya(
        ad,
        uygunluk=UygunlukKosullari(max_tutar=max_tutar, max_vade_ay=max_vade),
    )


def test_birden_cok_elenen_bankanin_sayilari_izin_listesinde_kalir(ork):
    """Farklı limitli beş banka elendiğinde HİÇBİRİNİN sayısı düşmemeli.

    NEDEN VAR (26 Ağu, uçtan uca sağlık taramasında bulundu):
    `_engel_parcasi` her gerekçenin sayılarını `hesap.update(gerekce.sayilar)`
    ile yazıyordu. Anahtarlar bankadan bağımsız sabit adlar (`max_tutar`,
    `max_vade_ay`), dolayısıyla **son banka öncekileri eziyordu**. Ezilen sayı
    izin listesinden düşünce `_sistem_dogrula` onu «doğrulanamadı» sayıyor ve
    kalkan cevabın TAMAMINI reddediyordu.

    Gerçek veriyle ölçülen sonuç: «Maaş müşterisiyim, 800.000 TL konut
    finansmanı istiyorum, 120 ay vade» sorgusu — chatbot'un amiral gemisi
    senaryosu — kullanıcıya yalnız *«cevabı vermiyorum»* döndürüyordu.

    Hata mevcut testlerden kaçtı çünkü hepsi TEK kampanya veriyordu; çakışma
    en az iki elenen banka gerektiriyor.
    """
    kampanyalar = [
        _limitli("A Bankası", max_tutar=125_000, max_vade=36),
        _limitli("B Bankası", max_tutar=250_000, max_vade=48),
        _limitli("C Bankası", max_tutar=400_000, max_vade=60),
    ]
    cevap, _ = ork.calistir("maaş müşterisi 800.000 TL 120 ay", kampanyalar)

    assert cevap.dogrulama_gecti, (
        f"Meşru cevap bloke edildi: {cevap.reddedilen_sayilar}. "
        "`hesap` anahtarları bankalar arasında çakışıyor olabilir."
    )
    assert not cevap.reddedilen_sayilar

    # Her bankanın kendi limiti metinde görünmeli — biri elenirse sayı da düşer.
    metin = cevap.tam_metin()
    for beklenen in ("125.000", "250.000", "400.000"):
        assert beklenen in metin, f"{beklenen} sebep listesinden düşmüş"


def test_ilk_bankanin_sayisi_sonuncusu_tarafindan_ezilmez(ork):
    """Çakışmayı doğrudan hedefleyen dar test: ilk gerekçenin sayısı korunur."""
    kampanyalar = [
        _limitli("İlk Banka", max_tutar=125_000, max_vade=36),
        _limitli("Son Banka", max_tutar=999_000, max_vade=240),
    ]
    cevap, _ = ork.calistir("maaş müşterisi 800.000 TL 120 ay", kampanyalar)
    assert "125.000" not in cevap.reddedilen_sayilar
    assert "36" not in cevap.reddedilen_sayilar


# ---------------------------------------------------------------------------
# Profil kolu: ürün süzgeci, kaynak adresi, sorulan oran (27 Ağustos)
# ---------------------------------------------------------------------------
#
# Jüri havuzu 9. madde bu üç eksiği birden gösterdi:
#
#     «120 ay vadeli 1.000.000 TL KONUT FİNANSMANI için en düşük kâr payı
#      oranını hangi katılım bankası sunuyor?»
#
#   * ürün süzgeci yalnız chatbot kolundaydı -> 357 kampanya sıralanıyor,
#     listenin başında kart ve döviz kampanyaları duruyordu
#   * kaynakçanın beş satırının da ADRESİ boştu
#   * sıralama toplam maliyete göre doğruydu ama sorulan ORAN hiç yazılmıyordu


def _konut(ad: str, oran: float) -> Kampanya:
    kampanya = _kampanya(ad, oran=oran)
    return kampanya.model_copy(
        update={
            "kampanya_turu": Alan(
                deger="konut_finansmani", ham_ifade="konut", guven=0.9, yontem="kural"
            )
        }
    )


def _kart(ad: str, oran: float) -> Kampanya:
    kampanya = _kampanya(ad, oran=oran)
    return kampanya.model_copy(
        update={
            "kampanya_turu": Alan(
                deger="kart", ham_ifade="kart", guven=0.9, yontem="kural"
            )
        }
    )


SORU = "1.000.000 TL, 120 ay konut finansmanı için en düşük kâr payı oranı"


def test_profil_kolunda_urun_suzgeci_isler(ork) -> None:
    kampanyalar = [_konut("Konutçu", 1.89), _kart("Kartçı", 0.5)]
    cevap, _ = ork.calistir(SORU, kampanyalar=kampanyalar)

    assert "Konutçu" in cevap.metin
    assert "Kartçı" not in cevap.metin, "sorulmayan ürün cevaba girmiş"


def test_profil_kaynakcasi_adres_tasir(ork) -> None:
    cevap, _ = ork.calistir(SORU, kampanyalar=[_konut("Konutçu", 1.89)])

    assert cevap.kaynaklar, "kaynakça boş"
    for kaynak in cevap.kaynaklar:
        assert kaynak.url, f"{kaynak.banka_adi} kaynağının adresi boş"
        assert kaynak.cekim_tarihi, f"{kaynak.banka_adi} çekim tarihi boş"


def test_profil_cevabi_sorulan_orani_yazar(ork) -> None:
    """Sıralama toplam maliyete göre yapılır ama ORAN da gösterilir."""
    cevap, _ = ork.calistir(SORU, kampanyalar=[_konut("Konutçu", 1.89)])

    assert "Kâr payı oranı: aylık %1,89" in cevap.metin
    assert "Toplam geri ödeme" in cevap.metin
    assert cevap.dogrulama_gecti, f"kalkan reddetti: {cevap.reddedilen_sayilar}"


def test_urun_suzgeci_bosaltirsa_uydurmaz(ork) -> None:
    """Sorulan ürüne ait kampanya yoksa başka ürünle doldurulmaz."""
    cevap, _ = ork.calistir(SORU, kampanyalar=[_kart("Kartçı", 0.5)])
    assert "bulunamadı" in cevap.metin
    assert not cevap.kaynaklar


# ---------------------------------------------------------------------------
# Profil kolunda BANKA SÜZGECİ (27 Ağustos)
# ---------------------------------------------------------------------------
#
#     soru  : «Albaraka'dan 1.000.000 TL konut finansmanı, 120 ay vade»
#     cevap : dokuz bankanın 18 kampanyası, toplam maliyete göre sıralı
#
# Adlandırılan banka cevapta hiç dikkate alınmıyordu. Ürün süzgeci profil
# koluna 27 Ağustos'ta eklenmişti; bankanınki hiç yoktu.


def _profil_bankalari(ork: Orkestrator, soru: str, kampanyalar) -> set[str]:
    cevap, _ = ork.calistir(soru, kampanyalar)
    return {k.banka_adi for k in cevap.kaynaklar}


def test_profil_kolunda_adlandirilan_banka_suzulur(ork) -> None:
    kampanyalar = [_kampanya("Albaraka Türk Katılım Bankası A.Ş."),
                   _kampanya("Ziraat Katılım Bankası A.Ş.")]
    bulunan = _profil_bankalari(ork, "Albaraka 800.000 TL 120 ay", kampanyalar)
    assert bulunan == {"Albaraka Türk Katılım Bankası A.Ş."}


def test_profil_kolunda_kesme_ekli_banka_da_suzulur(ork) -> None:
    """«Albaraka'dan …» — kesme eki eşleştirmeyi düşürmemeli."""
    kampanyalar = [_kampanya("Albaraka Türk Katılım Bankası A.Ş."),
                   _kampanya("Ziraat Katılım Bankası A.Ş.")]
    bulunan = _profil_bankalari(ork, "Albaraka'dan 800.000 TL 120 ay", kampanyalar)
    assert bulunan == {"Albaraka Türk Katılım Bankası A.Ş."}


def test_banka_adlandirilmazsa_kume_daralmaz(ork) -> None:
    """Süzgeç yalnız ADLANDIRILMIŞ bankada daraltır; yoksa korpus tamdır."""
    kampanyalar = [_kampanya("Albaraka Türk Katılım Bankası A.Ş."),
                   _kampanya("Ziraat Katılım Bankası A.Ş.")]
    bulunan = _profil_bankalari(ork, "800.000 TL 120 ay", kampanyalar)
    assert len(bulunan) == 2


def test_banka_suzgeci_urun_suzgecinden_once_kosar(ork) -> None:
    """Sıra tersine dönerse SORULMAYAN bankalar cevaba girer.

    Ürün önce koşsaydı, ad kümesi ürüne göre daralmış olurdu: Albaraka'nın
    konut kaydı yoksa «albaraka» hiçbir ada eşleşmez, banka süzgeci boş
    döner ve DOKUZ bankanın tamamı geri gelirdi.
    """
    from src.ajanlar.orkestrator import _banka_suz, _urun_suz

    kampanyalar = [
        # Sorulan banka — ama KONUT kaydı yok.
        _kampanya("Albaraka Türk Katılım Bankası A.Ş.", url="https://a.test/tasit"),
        # Sorulmayan banka — konut kaydı var.
        _kampanya("Ziraat Katılım Bankası A.Ş.", url="https://z.test/konut"),
    ]
    soru = "Albaraka konut finansmanı 800.000 TL 120 ay"

    assert _urun_suz(soru, _banka_suz(soru, kampanyalar)) == []
    # Ters sıra sorulmayan bankayı geri veriyor — testin ayırt ettiği şey bu.
    ters = _banka_suz(soru, _urun_suz(soru, kampanyalar))
    assert [k.banka_adi for k in ters] == ["Ziraat Katılım Bankası A.Ş."]


# ---------------------------------------------------------------------------
# Kâr payı yoksa: SIRALAMA İDDİA EDİLMEZ, BİLİNEN SAKLANMAZ (27 Ağustos)
# ---------------------------------------------------------------------------
#
#     soru  : «mevcut müşteri 1.000.000 TL … toplam maliyeti … düşük mü?»
#     cevap : «Toplam maliyete göre sıralı:» + beş kez
#             «Kâr payı oranı Belirtilmemiş, maliyet hesaplanamadı.»
#
# İki kusur bir arada: yapılmamış bir sıralama yapılmış gibi sunuluyordu ve
# o kayıtlarda DOLU olan tahsis ücreti · vade · tutar hiç gösterilmiyordu.
# Kullanıcı «bu sistemde hiçbir bilgi yok» sanıyordu. Ölçüldü: Kuveyt Türk ve
# Emlak Katılım'ın 11 konut kaydının hiçbirinde kâr payı oranı YAYIMLANMAMIŞ
# (sayfalardaki yüzdeler kredi/değer oranı ve tahsis ücreti) — yani veri
# doğruydu, kusur cevabın kendisindeydi.


def _oransiz(ad: str, **alanlar) -> Kampanya:
    return _kampanya(ad, oran=None, kimlik=f"0299-{ad}", **alanlar)


def test_maliyet_hesaplanamayinca_siralama_iddia_edilmez(ork) -> None:
    kampanyalar = [
        _oransiz("A Katılım Bankası A.Ş.", vade=120),
        _oransiz("B Katılım Bankası A.Ş.", vade=120),
    ]
    cevap, _ = ork.calistir("mevcut müşteri 1.000.000 TL 120 ay", kampanyalar)

    assert "Toplam maliyete göre sıralı" not in cevap.metin
    assert "sıralaması yapılamadı" in cevap.metin
    assert "hesaplama aracına" in cevap.metin


def test_kar_payi_yoksa_bilinen_alanlar_gosterilir(ork) -> None:
    """Bilinmeyeni beyan etmek doğrudur; bilineni saklamak değil."""
    kampanyalar = [
        _oransiz("A Katılım Bankası A.Ş.", vade=120, tahsis=0.5, tahsis_birim=Birim.YUZDE),
    ]
    cevap, _ = ork.calistir("mevcut müşteri 1.000.000 TL 120 ay", kampanyalar)

    assert "Tahsis ücreti: %0,50" in cevap.metin, cevap.metin
    assert "Azami vade: 120 ay" in cevap.metin
    assert cevap.dogrulama_gecti, cevap.reddedilen_sayilar


def test_bilinen_alan_birimine_gore_yazilir(ork) -> None:
    """`%0,50` ile `500 TL` aynı sütunda durur — birimsiz gösterim yanlış yazar."""
    kampanyalar = [
        _oransiz("A Katılım Bankası A.Ş.", vade=120, tahsis=500.0, tahsis_birim=Birim.TL),
    ]
    cevap, _ = ork.calistir("mevcut müşteri 1.000.000 TL 120 ay", kampanyalar)
    assert "Tahsis ücreti: 500 TL" in cevap.metin, cevap.metin


def test_maliyet_hesaplanabiliyorsa_baslik_degismez(ork) -> None:
    """Düzeltme yalnız hesaplanamayan hâli değiştirir — gerileme nöbetçisi."""
    cevap, _ = ork.calistir(
        "mevcut müşteri 1.000.000 TL 120 ay", [_kampanya(oran=2.5, vade=120)]
    )
    assert "**Toplam maliyete göre sıralı:**" in cevap.metin


# ---------------------------------------------------------------------------
# 27 Ağustos düzeltmeleri — jüri havuzu 9. madde
# ---------------------------------------------------------------------------


def test_manset_sorulan_olcutu_dogru_uctan_cevaplar(ork) -> None:
    """«En DÜŞÜK oran» sorusu en düşüğü söylemeli — yön çevrimi sessiz bozuluyordu.

    `_sorulan_yon` «dusuk» der, `ALAN_YONLERI` «dusuk_iyi». İkisi
    `_yon_tercihi` ile birleşiyor; kopyalanmadığında karşılaştırma tutmuyor
    ve manşete EN PAHALI kayıt çıkıyordu.
    """
    cevap, _ = ork.calistir(
        SORU, kampanyalar=[_konut("Ucuzcu", 1.50), _konut("Pahalici", 2.95)]
    )

    assert "en düşük kâr payı oranı: Ucuzcu" in cevap.metin
    assert "Pahalici — aylık" not in cevap.metin.split("\n")[0]
    assert cevap.dogrulama_gecti, f"kalkan reddetti: {cevap.reddedilen_sayilar}"


def test_manset_yon_cozulemezse_yazilmaz(ork) -> None:
    """Ölçüt yoksa manşet de yok — uydurulmuş yön yanlış kaydı vitrine koyar."""
    cevap, _ = ork.calistir(
        "1.000.000 TL, 120 ay konut finansmanı", kampanyalar=[_konut("Tek", 1.89)]
    )
    assert "arasında en" not in cevap.metin


def test_liste_kirpmasi_beyan_edilir(ork) -> None:
    """«10 kampanya uygun» deyip beş göstermek beyansız kalamaz."""
    from src.ajanlar.orkestrator import LISTE_UST_SINIRI

    kampanyalar = [_konut(f"Banka{i}", 1.5 + i / 10) for i in range(LISTE_UST_SINIRI + 3)]
    cevap, _ = ork.calistir(SORU, kampanyalar=kampanyalar)

    assert f"kalan {3} kampanya gösterilmiyor" in cevap.metin
    assert f"**{LISTE_UST_SINIRI} kampanya** listeleniyor" in cevap.metin
    assert cevap.dogrulama_gecti, f"kalkan reddetti: {cevap.reddedilen_sayilar}"


def test_kirpma_yoksa_beyan_da_yok(ork) -> None:
    """Sınırın altındaki liste için «gösterilmiyor» cümlesi yazılmaz."""
    cevap, _ = ork.calistir(SORU, kampanyalar=[_konut("Tek", 1.89)])
    assert "gösterilmiyor" not in cevap.metin


def test_banka_sayisi_kampanya_sayisindan_ayri_yazilir(ork) -> None:
    """Aynı bankanın üç kampanyası «üç banka» sanılmamalı."""
    cevap, _ = ork.calistir(
        SORU,
        kampanyalar=[
            _konut("Aynı Banka", 1.5).model_copy(update={"kampanya_id": "0299-a"}),
            _konut("Aynı Banka", 1.6).model_copy(update={"kampanya_id": "0299-b"}),
        ],
    )
    assert "**2 kampanya** uygun (1 banka)" in cevap.metin


def test_manset_kapsam_disi_orani_vitrine_koymaz(ork) -> None:
    """ADR 020: kart promosyonunun %0'ı «en düşük kâr payı» olamaz.

    `_maliyet_hesapla` oranı makullük için süzüyordu ama ÜRÜN SINIFI için
    süzmüyordu; manşet oranı doğrudan okuduğu için kapı ayrıca uygulanmalı.
    """
    kampanyalar = [_konut("Konutcu", 2.50), _kart("Kartci", 0.0)]
    cevap, _ = ork.calistir(SORU, kampanyalar=kampanyalar)

    assert "en düşük kâr payı oranı: Konutcu" in cevap.metin
    assert "Kartci" not in cevap.metin
