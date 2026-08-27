"""Karşılaştırma cevabının SÖZLEŞMESİ — AĞ İSTEMEZ.

Karşılaştırma tamamen yapısal: SQLite kaydı + deterministik skorlama. Ne dil
modeli ne gömme çağrılır, bu yüzden testler ağsız koşar.

NEDEN VAR — 26 Ağustos'ta ölçülen kusur:
    Kaynakça `skorlar[:5]`ten, yani AĞIRLIKLI SKORDA ilk beşten seçiliyordu.
    Cevap gövdesi ise kriter kriter kazananı yazıyor. İki bağımsız seçim
    olduğu için cevapta adı geçen bir banka kaynaklarda hiç olmayabiliyordu:

        "En uzun vadeyi kim veriyor?"
          cevapta  : Albaraka Türk, Türkiye Finans, Kuveyt Türk
          kaynakta : Türkiye Finans, Kuveyt Türk

    Projenin merkez iddiası «kanıtsız değer üretilemez»; jüri kaynaklara bakıp
    cevaptaki bankayı bulamıyorsa iddia orada kırılır.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.depolama import KampanyaKaydi
from src.rag.chatbot import Niyet, _bankalari_bul, _karsilastirma_cevabi

CEKIM = datetime(2026, 8, 26, 12, 0)


def _kayit(
    kimlik: str,
    banka: str,
    *,
    kar_payi: float | None = None,
    vade: int | None = None,
    tutar: float | None = None,
    odul: float | None = None,
    masrafsiz: bool | None = None,
) -> KampanyaKaydi:
    return KampanyaKaydi(
        kampanya_id=kimlik,
        banka_kodu=kimlik.split("-")[0],
        banka_adi=banka,
        kaynak_url=f"https://ornek.test/{kimlik}",
        cekim_tarihi=CEKIM,
        kampanya_turu="konut_finansmani",
        kar_payi_orani=kar_payi,
        vade_ay_max=vade,
        finansman_tutari_max=tutar,
        odul_miktari=odul,
        masrafsiz_mi=masrafsiz,
        ortalama_guven=0.9,
        doluluk_orani=0.5,
        tam_kayit="{}",
        ham_metin="ornek kampanya metni",
    )


@pytest.fixture
def kayitlar() -> list[KampanyaKaydi]:
    """Kazananları ağırlıklı skorun ALTINA iten kasıtlı kurgu.

    Eski kod kaynakçayı `skorlar[:5]`ten seçiyordu. Kümede beş ya da daha az
    kayıt varsa o dilim HERKESİ kapsar ve hata görünmez — testin ayırt edici
    olması için küme beşten büyük olmalı ve en az bir kriter kazananı ilk
    beşin dışında kalmalı.

    `Z` bankası vadeyi (240 ay) ve finansman tutarını (90 milyon) kazanır ama
    kâr payı berbat (%9,9), masrafsız değil ve ödülü yok; ağırlıklar kâr payına
    %40 verdiği için skorda dibe düşer. Doğru kaynakça onu yine de göstermek
    zorundadır: cevapta iki kriterin kazananı olarak ADI GEÇİYOR.
    """
    return [
        _kayit("0001-a", "A Katılım Bankası A.Ş.", kar_payi=0.99, vade=12, tutar=100_000, odul=1_000),
        _kayit("0002-b", "B Katılım Bankası A.Ş.", kar_payi=1.10, vade=60, tutar=200_000, odul=2_000),
        _kayit("0003-c", "C Katılım Bankası A.Ş.", kar_payi=1.20, vade=48, tutar=300_000, odul=3_000),
        _kayit("0004-d", "D Katılım Bankası A.Ş.", kar_payi=1.30, vade=36, odul=50_000),
        _kayit("0005-e", "E Katılım Bankası A.Ş.", kar_payi=1.40, vade=18, masrafsiz=True),
        _kayit("0006-f", "F Katılım Bankası A.Ş.", kar_payi=1.50, vade=24, tutar=150_000),
        _kayit("0007-g", "G Katılım Bankası A.Ş.", kar_payi=1.60, vade=30, tutar=180_000),
        _kayit("0008-z", "Z Katılım Bankası A.Ş.", kar_payi=9.90, vade=240, tutar=90_000_000),
    ]


def _cevapta_gecen_bankalar(metin: str, kayitlar: list[KampanyaKaydi]) -> set[str]:
    """Adı cevap metninde birebir geçen bankalar.

    Metinden ad ÇIKARMAK yerine bilinen adları metinde ARIYORUZ: «Finansman
    tutarı» başlığı «Finans» içerdiği için desenle ad avlamak yanlış pozitif
    üretiyor.
    """
    return {k.banka_adi for k in kayitlar if k.banka_adi in metin}


def test_cevapta_adi_gecen_her_banka_kaynakta_var(kayitlar) -> None:
    cevap = _karsilastirma_cevabi("Hangi banka daha avantajlı?", kayitlar)

    cevapta = _cevapta_gecen_bankalar(cevap.metin, kayitlar)
    kaynakta = {k.banka_adi for k in cevap.kaynaklar}

    assert cevapta, "cevapta hiçbir banka adı geçmiyor — test kurgusu bozuk"
    assert not (cevapta - kaynakta), (
        "cevapta adı geçip kaynakta olmayan banka: " + ", ".join(sorted(cevapta - kaynakta))
    )


def test_kaynakca_uydurma_banka_tasimaz(kayitlar) -> None:
    """Ters yön: kaynakta olup cevapta hiç geçmeyen banka da olmamalı.

    Kaynakça «ilgili olabilecekler» listesi değil, cevabın DAYANAĞIDIR.
    """
    cevap = _karsilastirma_cevabi("Hangi banka daha avantajlı?", kayitlar)

    cevapta = _cevapta_gecen_bankalar(cevap.metin, kayitlar)
    kaynakta = {k.banka_adi for k in cevap.kaynaklar}

    assert not (kaynakta - cevapta), (
        "kaynakta olup cevapta geçmeyen banka: " + ", ".join(sorted(kaynakta - cevapta))
    )


def test_masrafsiz_satirindaki_her_banka_kaynakta(kayitlar) -> None:
    """Masraf satırı TEK cümlede birden çok banka adı yazar.

    Her biri için bir temsilci kayıt kaynakçaya girmezse, o satırdaki adlar
    kaynaksız kalır.
    """
    kayitlar.append(
        _kayit("0009-h", "H Katılım Bankası A.Ş.", kar_payi=4.0, vade=6, masrafsiz=True)
    )
    cevap = _karsilastirma_cevabi("Masrafsız kampanya veren bankalar hangileri?", kayitlar)

    kaynakta = {k.banka_adi for k in cevap.kaynaklar}
    for kayit in kayitlar:
        if kayit.masrafsiz_mi:
            assert kayit.banka_adi in kaynakta, (
                f"{kayit.banka_adi} masraf satırında geçiyor ama kaynakta yok"
            )


def test_kaynakca_yinelemesiz(kayitlar) -> None:
    """Aynı kampanya birden çok kriteri kazanabilir; kaynakçada bir kez görünmeli."""
    cevap = _karsilastirma_cevabi("Hangi banka daha avantajlı?", kayitlar)
    urller = [k.url for k in cevap.kaynaklar]
    assert len(urller) == len(set(urller)), f"kaynakça yinelenen kayıt taşıyor: {urller}"


def test_tek_kayitla_karsilastirma_yapilmaz() -> None:
    cevap = _karsilastirma_cevabi("Hangi banka daha avantajlı?", [
        _kayit("0001-a", "A Katılım Bankası A.Ş.", kar_payi=1.0)
    ])
    assert cevap.niyet is Niyet.KARSILASTIRMA
    assert "en az iki" in cevap.metin


# ---------------------------------------------------------------------------
# Sorulan ölçüt başa alınır (26 Ağustos)
# ---------------------------------------------------------------------------
#
# Ölçülen kusur: `_karsilastirma_cevabi` `soru` parametresini alıyor ama
# gövdesinde SIFIR kez kullanıyordu. «En uzun vadeyi kim veriyor?» sorusunun
# cevabı «Kâr payı oranı açısından…» diye başlıyor, sorulan şey ikinci maddede
# kalıyordu.


def _ilk_olcut_satiri(metin: str) -> str:
    return next(satir for satir in metin.splitlines() if satir.startswith("- **"))


@pytest.mark.parametrize(
    ("soru", "beklenen_etiket"),
    [
        ("En uzun vadeyi kim veriyor?", "Vade"),
        ("En düşük kâr payı oranı hangi bankada?", "Kâr payı oranı"),
        ("Hangi bankada tahsis ücreti yok?", "Masraf"),
        ("En yüksek ödülü kim veriyor?", "Ek ödül"),
        ("Hangi bankanın finansman tutarı limiti daha yüksek?", "Finansman tutarı"),
    ],
)
def test_sorulan_olcut_ilk_maddede(kayitlar, soru: str, beklenen_etiket: str) -> None:
    cevap = _karsilastirma_cevabi(soru, kayitlar)
    ilk = _ilk_olcut_satiri(cevap.metin)
    assert ilk.startswith(f"- **{beklenen_etiket}**"), (
        f"{soru!r} sorusunda ilk madde {beklenen_etiket!r} olmalıydı, gelen: {ilk[:70]!r}"
    )


def test_sorulan_olcut_giris_cumlesinde_bildirilir(kayitlar) -> None:
    """Kullanıcı hangi ölçütün öne alındığını görmeli — sessiz sıralama olmasın."""
    cevap = _karsilastirma_cevabi("En uzun vadeyi kim veriyor?", kayitlar)
    assert "Sorduğunuz ölçüt **Vade**" in cevap.metin


def test_olcut_belirtilmeyen_soru_genel_dokumde_kalir(kayitlar) -> None:
    """«Hangi banka daha iyi?» bir ölçüt sormuyor; eski biçim doğrusudur."""
    cevap = _karsilastirma_cevabi("Hangi banka daha iyi?", kayitlar)
    assert cevap.metin.startswith("Bu kampanyalar farklı avantajlar sunmaktadır.")
    assert "Sorduğunuz ölçüt" not in cevap.metin


def test_olcut_one_alinsa_da_digerleri_kaybolmaz(kayitlar) -> None:
    """Sıralama değişir, kapsam değişmez.

    Kullanıcı yalnız sorduğunu değil, kararı etkileyen diğer ölçütleri de
    görmeli; aksi hâlde «en uzun vade» cevabı kâr payının berbat olduğunu
    gizlerdi.
    """
    cevap = _karsilastirma_cevabi("En uzun vadeyi kim veriyor?", kayitlar)
    for etiket in ("Vade", "Kâr payı oranı", "Finansman tutarı", "Ek ödül"):
        assert f"- **{etiket}**" in cevap.metin, f"{etiket} ölçütü cevaptan düşmüş"


def test_olcut_one_alininca_kaynakca_yine_tam(kayitlar) -> None:
    """Sıralama değişikliği kanıt zincirini bozmamalı."""
    cevap = _karsilastirma_cevabi("En uzun vadeyi kim veriyor?", kayitlar)
    cevapta = _cevapta_gecen_bankalar(cevap.metin, kayitlar)
    kaynakta = {k.banka_adi for k in cevap.kaynaklar}
    assert not (cevapta - kaynakta)


# ---------------------------------------------------------------------------
# Liste soruları sıralama değil liste döndürür (26 Ağustos)
# ---------------------------------------------------------------------------
#
# «Hangi bankalar konut finansmanı sunuyor?» karşılaştırma NİYETİNE düşer ve
# doğrusu odur — soru korpusun tamamına sorulur. Ama cevap sıralama biçiminde
# dönüyordu: kullanıcı liste istiyor, «kim kazandı» cevabı alıyordu.


def test_liste_sorusu_banka_listesi_dondurur(kayitlar) -> None:
    cevap = _karsilastirma_cevabi("Hangi bankalar konut finansmanı sunuyor?", kayitlar)

    assert "uyan bankalar" in cevap.metin
    assert "daha avantajlıdır" not in cevap.metin, "liste sorusu sıralama biçiminde cevaplanmış"


def test_liste_sorusu_her_bankayi_bir_kez_yazar(kayitlar) -> None:
    """Bir bankanın birden çok kampanyası olabilir; listede bir kez görünmeli."""
    kayitlar.append(_kayit("0001-a2", "A Katılım Bankası A.Ş.", kar_payi=1.05, vade=24))
    cevap = _karsilastirma_cevabi("Hangi bankalar konut finansmanı sunuyor?", kayitlar)

    assert cevap.metin.count("**A Katılım Bankası A.Ş.**") == 1


def test_liste_sorusu_olcute_gore_suzer(kayitlar) -> None:
    """«Masrafsız … bankalar hangileri?» yalnız masrafsız olanları listelemeli.

    Ürün süzgeci burada daralmaz: masrafsızlık bir ürün türü değil KOŞULdur.
    Süzülmezse kümedeki her banka listelenirdi.
    """
    cevap = _karsilastirma_cevabi("Masrafsız kampanya sunan bankalar hangileri?", kayitlar)

    listelenen = _cevapta_gecen_bankalar(cevap.metin, kayitlar)
    masrafsiz_olanlar = {k.banka_adi for k in kayitlar if k.masrafsiz_mi}
    assert listelenen == masrafsiz_olanlar, (
        f"masrafsız olmayan banka listeye girdi: {sorted(listelenen - masrafsiz_olanlar)}"
    )


def test_liste_sorusunda_her_banka_kaynakli(kayitlar) -> None:
    cevap = _karsilastirma_cevabi("Hangi bankalar konut finansmanı sunuyor?", kayitlar)

    cevapta = _cevapta_gecen_bankalar(cevap.metin, kayitlar)
    kaynakta = {k.banka_adi for k in cevap.kaynaklar}
    assert cevapta == kaynakta


def test_liste_cevabinda_rakam_yok(kayitlar) -> None:
    """Kalkan sözleşmesi: listede sayı yazılmaz.

    Kampanya BAŞLIKLARI «500 TL Hediye» gibi sayı taşıyor; başlık yazılsaydı
    her sayının yapısal karşılığı aranacak ve kalkan cevabı bloklayacaktı.
    Tür etiketi (enum karşılığı) sayısızdır.
    """
    cevap = _karsilastirma_cevabi("Hangi bankalar konut finansmanı sunuyor?", kayitlar)
    assert not any(karakter.isdigit() for karakter in cevap.metin), (
        f"liste cevabında rakam var: {cevap.metin!r}"
    )


def test_siralama_isareti_olan_soru_liste_olmaz(kayitlar) -> None:
    """«En uzun vadeyi hangi bankalar veriyor?» ÖLÇÜT sorar; listeye çevrilirse kaybolur."""
    cevap = _karsilastirma_cevabi("En uzun vadeyi hangi bankalar veriyor?", kayitlar)

    assert "daha avantajlıdır" in cevap.metin
    assert _ilk_olcut_satiri(cevap.metin).startswith("- **Vade**")


# ---------------------------------------------------------------------------
# Baş başa karşılaştırma: kaybeden de görünür (26 Ağustos)
# ---------------------------------------------------------------------------


def _iki_banka() -> list[KampanyaKaydi]:
    return [
        _kayit("0001-a", "A Katılım Bankası A.Ş.", kar_payi=1.0, vade=120, tutar=1_000_000, odul=5_000),
        _kayit("0002-b", "B Katılım Bankası A.Ş.", kar_payi=2.5, vade=12, tutar=50_000, odul=100),
    ]


def test_basbasa_kiyasta_kaybeden_de_anilir() -> None:
    """«A mı B mi?» sorusuna tek bankalık monolog dönmemeli.

    Ölçüldü: «Ziraat Katılım mı Türkiye Finans mı?» sorusunda Türkiye Finans
    beş ölçütü birden kazanıyor ve Ziraat cevapta HİÇ geçmiyordu. Kullanıcı iki
    banka sordu; aradaki farkı göremediği için kazananın ne kadar önde olduğunu
    da bilmiyordu.
    """
    cevap = _karsilastirma_cevabi("A mı daha iyi B mi?", _iki_banka())

    assert "A Katılım Bankası A.Ş." in cevap.metin
    assert "B Katılım Bankası A.Ş." in cevap.metin, "kaybeden banka cevapta hiç geçmiyor"


def test_basbasa_kiyasta_kaybedenin_degeri_yazilir() -> None:
    """Farkın büyüklüğü kararı değiştirir: 120 ay ile 12 ay aynı şey değil."""
    cevap = _karsilastirma_cevabi("A mı daha iyi B mi?", _iki_banka())
    vade_satiri = next(s for s in cevap.metin.splitlines() if s.startswith("- **Vade**"))

    assert "120 ay" in vade_satiri
    assert "12 ay" in vade_satiri, f"kaybedenin değeri yok: {vade_satiri!r}"


def test_basbasa_kiyasta_kaybeden_kaynakli() -> None:
    cevap = _karsilastirma_cevabi("A mı daha iyi B mi?", _iki_banka())
    kaynakta = {k.banka_adi for k in cevap.kaynaklar}

    assert "B Katılım Bankası A.Ş." in kaynakta, "kaybeden anılıyor ama kaynaksız"


def test_esitlik_daha_avantajli_diye_yazilmaz() -> None:
    """İki banka da %0 sunarken birini öne çıkarmak veriyle çelişir."""
    esitler = [
        _kayit("0001-a", "A Katılım Bankası A.Ş.", kar_payi=0.0, vade=12),
        _kayit("0002-b", "B Katılım Bankası A.Ş.", kar_payi=0.0, vade=24),
    ]
    cevap = _karsilastirma_cevabi("A mı daha iyi B mi?", esitler)
    kar_satiri = next(s for s in cevap.metin.splitlines() if s.startswith("- **Kâr payı"))

    assert "EŞİT" in kar_satiri, f"beraberlik avantaj gibi yazılmış: {kar_satiri!r}"
    assert "daha avantajlıdır" not in kar_satiri


def test_uc_bankada_rakip_degerleri_dizilmez(kayitlar) -> None:
    """Üç ve fazlasında her ölçütün yanına bütün rakipleri dizmek satırı boğar."""
    cevap = _karsilastirma_cevabi("Hangi banka daha iyi?", kayitlar)
    vade_satiri = next(s for s in cevap.metin.splitlines() if s.startswith("- **Vade**"))

    assert "için bu değer" not in vade_satiri


def test_olcute_uyan_kayit_yoksa_uydurmaz() -> None:
    """Süzgeç boş küme bırakırsa liste uydurulmaz."""
    cevap = _karsilastirma_cevabi(
        "Masrafsız kampanya sunan bankalar hangileri?",
        [_kayit("0001-a", "A Katılım Bankası A.Ş.", kar_payi=1.0, masrafsiz=False)],
    )
    assert "bulunmuyor" in cevap.metin
    assert not cevap.kaynaklar


# ---------------------------------------------------------------------------
# Bitişik yazılan banka adı (27 Ağustos)
# ---------------------------------------------------------------------------
#
# Ölçülen kusur: kullanıcı «kuveyttürk ve albarakatürk arasında hangisinin kâr
# payı daha yüksek» diye sordu; `_bankalari_bul` HİÇ eşleşme döndürmedi, `sor`
# içindeki `or kayitlar` yedeği devreye girdi ve soru dokuz bankanın 931
# kaydına birden soruldu. Cevapta sorulmayan Türkiye Finans «daha avantajlıdır»
# diye yazıyordu.


_GERCEK_BANKALAR = (
    "Albaraka Türk Katılım Bankası A.Ş.",
    "Kuveyt Türk Katılım Bankası A.Ş.",
    "Türkiye Finans Katılım Bankası A.Ş.",
    "Vakıf Katılım Bankası A.Ş.",
    "Ziraat Katılım Bankası A.Ş.",
    "T.O.M. Katılım Bankası A.Ş.",
)


@pytest.fixture
def korpus() -> list[KampanyaKaydi]:
    return [
        _kayit(f"{i:04d}-x", ad, kar_payi=1.0 + i, vade=12 * (i + 1))
        for i, ad in enumerate(_GERCEK_BANKALAR)
    ]


@pytest.mark.parametrize(
    ("soru", "beklenen"),
    [
        ("kuveyttürk kampanyaları", {"Kuveyt Türk Katılım Bankası A.Ş."}),
        ("albarakatürk kâr payı", {"Albaraka Türk Katılım Bankası A.Ş."}),
        ("vakıfkatılım masrafsız mı", {"Vakıf Katılım Bankası A.Ş."}),
        ("ziraatkatılım vade", {"Ziraat Katılım Bankası A.Ş."}),
        # Ad korpusta noktalı duruyor, kullanıcı noktasız yazıyor.
        ("TOM Katılım kampanyaları", {"T.O.M. Katılım Bankası A.Ş."}),
        # Boşluklu yazım eskiden de çalışıyordu; kırılmamalı.
        ("kuveyt türk mü albaraka mı", {
            "Kuveyt Türk Katılım Bankası A.Ş.",
            "Albaraka Türk Katılım Bankası A.Ş.",
        }),
    ],
)
def test_bitisik_yazilan_banka_adi_eslesir(korpus, soru: str, beklenen: set[str]) -> None:
    bulunan = {k.banka_adi for k in _bankalari_bul(soru, korpus)}
    assert bulunan == beklenen, f"{soru!r} -> {sorted(bulunan)}"


def test_bitisik_yazimda_sorulmayan_banka_cevaba_girmez(korpus) -> None:
    """Kusurun ta kendisi: iki banka soruluyor, üçüncüsü cevapta boy gösteriyordu."""
    soru = "kuveyttürk ve albarakatürk arasında hangisinin kâr payı daha yüksek"
    ilgili = _bankalari_bul(soru, korpus)

    cevap = _karsilastirma_cevabi(soru, ilgili)
    assert "Türkiye Finans" not in cevap.metin
    assert {k.banka_adi for k in cevap.kaynaklar} <= {
        "Kuveyt Türk Katılım Bankası A.Ş.",
        "Albaraka Türk Katılım Bankası A.Ş.",
    }


@pytest.mark.parametrize(
    "soru",
    [
        "hangi banka daha avantajlı",
        "tüm katılım bankaları arasında en düşük kâr payı hangisinde",
        "masrafsız kampanya sunan bankalar hangileri",
    ],
)
def test_banka_adlandirmayan_soru_eslesmez(korpus, soru: str) -> None:
    """`or kayitlar` yedeği bu sorular İÇİN var; bitişik eşleşme onu çalmamalı.

    Boşluk atılarak eşleştirme yapıldığı için bitişen sözcüklerin sahte bir
    banka adı üretmediği burada denetlenir.
    """
    assert _bankalari_bul(soru, korpus) == []


# ---------------------------------------------------------------------------
# Sorulan UÇ — «daha yüksek mi?» ile «daha düşük mü?» (27 Ağustos)
# ---------------------------------------------------------------------------
#
# Ölçülen kusur: hangi ALANIN sorulduğu okunuyor, hangi UCUN sorulduğu
# okunmuyordu. «Hangisinin kâr payı daha yüksek?» sorusuna en DÜŞÜK oran
# «daha avantajlıdır» diye dönüyordu.


def _olcut_satiri(metin: str, etiket: str) -> str:
    return next(s for s in metin.splitlines() if s.startswith(f"- **{etiket}**"))


def test_daha_yuksek_sorusu_yuksek_ucu_verir(kayitlar) -> None:
    cevap = _karsilastirma_cevabi("Hangisinin kâr payı daha yüksek?", kayitlar)
    satir = _olcut_satiri(cevap.metin, "Kâr payı oranı")

    assert "Z Katılım Bankası A.Ş." in satir, f"en yüksek oran yazılmamış: {satir!r}"
    assert "A Katılım Bankası A.Ş." not in satir


def test_yuksek_uc_avantaj_diye_sunulmaz(kayitlar) -> None:
    """Kullanıcı dezavantajlı ucu sordu; onu «avantaj» diye sunmak yanıltmadır."""
    cevap = _karsilastirma_cevabi("Hangisinin kâr payı daha yüksek?", kayitlar)
    satir = _olcut_satiri(cevap.metin, "Kâr payı oranı")

    assert "daha avantajlıdır" not in satir, f"dezavantajlı uç avantaj diye yazılmış: {satir!r}"
    assert "en yüksek olan banka" in satir
    assert "maliyettir" in cevap.metin, "kâr payının maliyet olduğu notu düşmüş"


def test_dusuk_uc_sorusu_avantaj_bicimini_korur(kayitlar) -> None:
    """Sorulan uç avantajlı uçla aynıysa cümle değişmez."""
    cevap = _karsilastirma_cevabi("En düşük kâr payı oranı hangi bankada?", kayitlar)
    satir = _olcut_satiri(cevap.metin, "Kâr payı oranı")

    assert "A Katılım Bankası A.Ş." in satir
    assert "daha avantajlıdır" in satir
    assert "maliyettir" not in cevap.metin, "gereksiz not eklenmiş"


def test_yon_yalniz_odak_olcute_uygulanir(kayitlar) -> None:
    """«En düşük kâr payı» sorusu vadeyi de en kısaya çevirmemeli.

    Yön sorudaki ÖLÇÜTE aittir. Bütün ölçütlere uygulanırsa vade 240 aylık
    Z yerine 12 aylık A ile cevaplanır — kullanıcının sormadığı bir sıralama.
    """
    cevap = _karsilastirma_cevabi("En düşük kâr payı oranı hangi bankada?", kayitlar)
    vade_satiri = _olcut_satiri(cevap.metin, "Vade")

    assert "Z Katılım Bankası A.Ş." in vade_satiri, f"vade ucu ters dönmüş: {vade_satiri!r}"


def test_yon_belirtilmeyen_soru_avantajli_ucta_kalir(kayitlar) -> None:
    cevap = _karsilastirma_cevabi("Kâr payı oranını karşılaştır", kayitlar)
    satir = _olcut_satiri(cevap.metin, "Kâr payı oranı")

    assert "daha avantajlıdır" in satir
    assert "A Katılım Bankası A.Ş." in satir
