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
from src.rag.chatbot import Niyet, _karsilastirma_cevabi

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


def test_olcute_uyan_kayit_yoksa_uydurmaz() -> None:
    """Süzgeç boş küme bırakırsa liste uydurulmaz."""
    cevap = _karsilastirma_cevabi(
        "Masrafsız kampanya sunan bankalar hangileri?",
        [_kayit("0001-a", "A Katılım Bankası A.Ş.", kar_payi=1.0, masrafsiz=False)],
    )
    assert "bulunmuyor" in cevap.metin
    assert not cevap.kaynaklar
