"""Muhakeme ajanının testleri — uygunluk kısıt çözücü.

Bu ajan ürünün asıl farkı ve **LLM kullanmaz**: kısıt kontrolü ile aritmetik
saf koddur. Testlerin Ollama'sız koşabiliyor olması iddianın bir parçasıdır.

Buradaki testlerin ikinci işi, sunumdaki sayısal iddiaları koda bağlamaktır.
"Manşet oran tuzağı" slaydı bir eşiğe dayanıyor; eşik testte yazılıysa,
slayttaki cümle ile sistemin davranışı ayrışamaz.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.ajanlar.muhakeme import MuhakemeAjani, MusteriProfili, UygunlukSonucu
from src.comparison.karsilastirma import toplam_maliyet
from src.schema import Alan, Birim, HedefKitle, Kampanya, UygunlukKosullari


def _kampanya(
    ad: str = "Test Bankası",
    *,
    oran: float | None = 1.89,
    tahsis: float | None = None,
    uygunluk: UygunlukKosullari | None = None,
) -> Kampanya:
    return Kampanya(
        banka_adi=ad,
        banka_kodu="0299",
        kampanya_id=f"0299-{ad}",
        kaynak_url=f"https://{ad}.test/kampanya",
        cekim_tarihi=datetime(2026, 8, 14),
        kar_payi_orani=(
            Alan(deger=oran, ham_ifade=f"%{oran}", guven=0.9, yontem="kural")
            if oran is not None
            else Alan.yok()
        ),
        tahsis_ucreti=(
            # `tahsis_ucreti` ÇOK BİRİMLİ (TL ya da yüzde); şema birim beyanı
            # olmadan kaydı reddeder. Fikstür de sözleşmeye uymak zorundadır —
            # bu kısıtın işini yaptığının kanıtı.
            Alan(
                deger=tahsis,
                ham_ifade=f"{tahsis} TL",
                guven=0.9,
                yontem="kural",
                birim=Birim.TL,
            )
            if tahsis is not None
            else Alan.yok()
        ),
        uygunluk=uygunluk,
    )


PROFIL = MusteriProfili(musteri_tipi=HedefKitle.MAAS_MUSTERISI, tutar=800_000, vade_ay=120)


@pytest.fixture
def ajan() -> MuhakemeAjani:
    return MuhakemeAjani()


# ---------------------------------------------------------------------------
# Kısıt çözme
# ---------------------------------------------------------------------------


def test_tutar_alt_sinirindan_elenir(ajan):
    kampanya = _kampanya(uygunluk=UygunlukKosullari(min_tutar=1_000_000.0))
    sonuc = ajan.degerlendir(PROFIL, kampanya)
    assert sonuc.uygun_mu is False
    assert "1.000.000" in str(sonuc.engelleyenler()[0])


def test_vade_ust_sinirindan_elenir(ajan):
    kampanya = _kampanya(uygunluk=UygunlukKosullari(max_vade_ay=96))
    sonuc = ajan.degerlendir(PROFIL, kampanya)
    assert sonuc.uygun_mu is False
    assert sonuc.engelleyenler()[0].kural == "max_vade_ay"


def test_musteri_tipi_uymayan_elenir(ajan):
    kampanya = _kampanya(uygunluk=UygunlukKosullari(musteri_tipi=[HedefKitle.YENI_MUSTERI]))
    assert ajan.degerlendir(PROFIL, kampanya).uygun_mu is False


def test_tum_musteriler_herkese_acik(ajan):
    kampanya = _kampanya(uygunluk=UygunlukKosullari(musteri_tipi=[HedefKitle.TUM_MUSTERILER]))
    assert ajan.degerlendir(PROFIL, kampanya).uygun_mu is True


def test_zorunlu_urun_eksikse_elenir(ajan):
    kampanya = _kampanya(uygunluk=UygunlukKosullari(zorunlu_urun=["maaş hesabı", "kredi kartı"]))
    profil = MusteriProfili(
        musteri_tipi=HedefKitle.MAAS_MUSTERISI,
        tutar=800_000,
        vade_ay=120,
        mevcut_urunler=["maaş hesabı"],
    )
    sonuc = ajan.degerlendir(profil, kampanya)
    assert sonuc.uygun_mu is False
    assert "kredi kartı" in str(sonuc.engelleyenler()[0])


def test_segment_adi_da_dogrulanir(ajan):
    """`HedefKitle.SEGMENT` geniş bir kutu; emekliye özel bir kampanya
    öğrenciye uygun değildir."""
    kampanya = _kampanya(
        uygunluk=UygunlukKosullari(
            musteri_tipi=[HedefKitle.SEGMENT], segment_detayi=["emekli"]
        )
    )
    ogrenci = MusteriProfili(
        musteri_tipi=HedefKitle.SEGMENT, tutar=800_000, vade_ay=120, segment="öğrenci"
    )
    emekli = MusteriProfili(
        musteri_tipi=HedefKitle.SEGMENT, tutar=800_000, vade_ay=120, segment="emekli"
    )
    assert ajan.degerlendir(ogrenci, kampanya).uygun_mu is False
    assert ajan.degerlendir(emekli, kampanya).uygun_mu is True


# ---------------------------------------------------------------------------
# Dürüstlük — eksik veri gizlenmez
# ---------------------------------------------------------------------------


def test_uygunluk_cikarilmamis_kayit_isaretlenir(ajan):
    """96 mevcut kaydın hepsi böyle. 'Uygun' gösterilirler ama sistemin
    bilmediği bir şeyi biliyormuş gibi sunmaması için işaretlenirler."""
    sonuc = ajan.degerlendir(PROFIL, _kampanya(uygunluk=None))
    assert sonuc.veri_eksik is True
    assert any(
        "doğrulanmadı" in g.aciklama or "doğrulanamadı" in g.aciklama
        for g in sonuc.gerekceler
    )


def test_uygunluk_eksigi_kaynagi_suclamaz(ajan):
    """Eksik kısıt, bankanın YAYINLAMADIĞI iddiasına çevrilemez.

    `veri_eksik` iki durumu birden kapsıyor — banka hiç yazmamış olabilir ya
    da bizim çıkarımımız kaçırmış olabilir — ve ikisini ayırt edemiyor.
    Açıklamanın birini seçmesi, elimizde olmayan bir bilgiyi varmış gibi
    sunmaktır; sistemin tüm iddiası bunun tersi.

    25 Ağustos'ta bu İKİ kez yapıldı: önce metin «veri kaynağında
    yayınlanmadığı için» diye değiştirildi (`5afcac8`), sonra kırılan test
    o metni dayatacak şekilde güncellendi (`2edf0b9`) — yani bilinçli bir
    tercihti, dalgınlık değil. Kaptan kararıyla geri alındı: doluluk oranımız
    %26, dolayısıyla çıkarılamamış kısıtın çoğu bankanın suskunluğu değil
    bizim sınırımız. Bu test o yolu bir daha sessizce açtırmıyor.
    """
    sonuc = ajan.degerlendir(PROFIL, _kampanya(uygunluk=None))
    aciklamalar = " ".join(g.aciklama for g in sonuc.gerekceler).lower()

    for suclayici in ("yayınlanmadığı", "yayımlanmadığı", "paylaşılmadığı"):
        assert suclayici not in aciklamalar, (
            f"Açıklama kaynağı suçluyor ({suclayici!r}): kısıtın neden eksik "
            f"olduğunu bilmiyoruz, yalnız eksik olduğunu biliyoruz."
        )

    # İki olasılığın ikisi de anılmalı — belirsizlik gizlenmemeli.
    assert "belirtilmemiş" in aciklamalar
    assert "çıkarılamamış" in aciklamalar


def test_oran_yoksa_maliyet_uydurulmaz(ajan):
    sonuc = ajan.degerlendir(PROFIL, _kampanya(oran=None))
    assert sonuc.maliyet is None
    assert sonuc.toplam_geri_odeme is None


def test_uygun_olmayanlar_da_sebebiyle_doner(ajan):
    """Sessizce elemek yerine sebebini söylemek, banka çalışanının müşteriye
    ne diyeceğini öğrenmesini sağlar."""
    kampanyalar = [
        _kampanya("Uygun", uygunluk=UygunlukKosullari(max_vade_ay=120)),
        _kampanya("Elenen", uygunluk=UygunlukKosullari(min_tutar=5_000_000.0)),
    ]
    sonuclar, _ = ajan.calistir((PROFIL, kampanyalar))
    assert len(sonuclar) == 2
    elenen = next(s for s in sonuclar if not s.uygun_mu)
    assert elenen.engelleyenler()


# ---------------------------------------------------------------------------
# Sıralama — toplam maliyete göre, manşet orana göre DEĞİL
# ---------------------------------------------------------------------------


def test_siralama_toplam_maliyete_gore(ajan):
    kampanyalar = [
        _kampanya("Pahali", oran=2.30, uygunluk=UygunlukKosullari(max_vade_ay=120)),
        _kampanya("Ucuz", oran=1.85, uygunluk=UygunlukKosullari(max_vade_ay=120)),
    ]
    sonuclar, _ = ajan.calistir((PROFIL, kampanyalar))
    assert sonuclar[0].banka_adi == "Ucuz"
    assert sonuclar[0].toplam_geri_odeme < sonuclar[1].toplam_geri_odeme


def test_maliyeti_hesaplanamayan_uygun_kayit_sona_gider(ajan):
    """'Veri yok' en iyi sonuç gibi görünmemeli."""
    kampanyalar = [
        _kampanya("OranYok", oran=None, uygunluk=UygunlukKosullari(max_vade_ay=120)),
        _kampanya("OranVar", oran=2.50, uygunluk=UygunlukKosullari(max_vade_ay=120)),
    ]
    sonuclar, _ = ajan.calistir((PROFIL, kampanyalar))
    assert sonuclar[0].banka_adi == "OranVar"


def test_elenenler_en_sona_gider(ajan):
    kampanyalar = [
        _kampanya("Elenen", oran=1.00, uygunluk=UygunlukKosullari(min_tutar=9_000_000.0)),
        _kampanya("Uygun", oran=2.50, uygunluk=UygunlukKosullari(max_vade_ay=120)),
    ]
    sonuclar, _ = ajan.calistir((PROFIL, kampanyalar))
    assert sonuclar[0].banka_adi == "Uygun"
    assert sonuclar[-1].uygun_mu is False


# ---------------------------------------------------------------------------
# "Manşet oran tuzağı" — sunum iddiasının sayısal dayanağı
# ---------------------------------------------------------------------------
#
# Plan_Guncellemeleri_v3.md şu örneği veriyordu:
#   "%1,87 / 96 ay / 5.000 TL masraflı bir ürün, %1,89 / 120 ay / masrafsız
#    bir üründen PAHALI olabilir."
# Bu örnek YANLIŞ: 800.000 TL'de 96 ay toplam 1.739.844 TL, 120 ay ise
# 2.028.925 TL. Kısa vade toplamda her zaman daha ucuzdur; belge toplam geri
# ödemeyi aylık taksitle karıştırmış. Doğru iddia AYNI VADEDE kurulur ve
# masrafın oran avantajını aşmasını gerektirir.


def test_ayni_vadede_kucuk_masraf_orani_yenemez():
    """5.000 TL, %0,02'lik oran avantajını çevirmeye yetmiyor — v3'teki
    örneğin sayısal olarak tutmamasının sebebi bu."""
    dusuk = toplam_maliyet(800_000, 1.87, 120, 5_000)["toplam_geri_odeme"]
    yuksek = toplam_maliyet(800_000, 1.89, 120, 0)["toplam_geri_odeme"]
    assert dusuk < yuksek


def test_ayni_vadede_yeterince_buyuk_masraf_sıralamayı_cevirir():
    """Savunulabilir örnek: masraf, oran avantajının parasal değerini
    (800.000 TL / 120 ay için ~15.800 TL) aşarsa manşet oran yanıltır."""
    oran_avantaji = (
        toplam_maliyet(800_000, 1.89, 120, 0)["toplam_geri_odeme"]
        - toplam_maliyet(800_000, 1.87, 120, 0)["toplam_geri_odeme"]
    )
    assert 15_000 < oran_avantaji < 16_500  # ~15.796 TL

    dusuk = toplam_maliyet(800_000, 1.87, 120, 20_000)["toplam_geri_odeme"]
    yuksek = toplam_maliyet(800_000, 1.89, 120, 0)["toplam_geri_odeme"]
    assert dusuk > yuksek  # manşet oran düşük ama ürün PAHALI


def test_tuzak_siralamada_gercekten_gorunur(ajan):
    """İddia yalnız hesapta değil, ajanın sıralamasında da görünmeli."""
    kampanyalar = [
        _kampanya(
            "ManşetUcuz", oran=1.87, tahsis=20_000, uygunluk=UygunlukKosullari(max_vade_ay=120)
        ),
        _kampanya(
            "GerçektenUcuz", oran=1.89, uygunluk=UygunlukKosullari(max_vade_ay=120)
        ),
    ]
    sonuclar, _ = ajan.calistir((PROFIL, kampanyalar))
    assert sonuclar[0].banka_adi == "GerçektenUcuz"


# ---------------------------------------------------------------------------
# İz kaydı
# ---------------------------------------------------------------------------


def test_iz_llm_kullanilmadigini_bildirir(ajan):
    """Aritmetiği ajana yaptırmıyoruz iddiasının ekrandaki kanıtı."""
    _, iz = ajan.calistir((PROFIL, [_kampanya()]))
    assert iz.llm_kullanildi is False
    assert ajan.llm_kullanir is False
    assert "kod" in iz.satir()


def test_iz_eleme_gerekcesini_yazar(ajan):
    kampanyalar = [_kampanya("Elenen", uygunluk=UygunlukKosullari(min_tutar=9_000_000.0))]
    _, iz = ajan.calistir((PROFIL, kampanyalar))
    assert "min_tutar" in iz.karar_gerekcesi


def test_sonuc_tipi_beklendigi_gibi(ajan):
    sonuclar, _ = ajan.calistir((PROFIL, [_kampanya()]))
    assert all(isinstance(s, UygunlukSonucu) for s in sonuclar)


# ---------------------------------------------------------------------------
# Makul olmayan orandan hesap yapılmaz
# ---------------------------------------------------------------------------
#
# 14 Ağustos: veritabanında kar_payi_orani 0 ile 84,93 arasında değerler
# taşıyor. Üst uçtakiler "%80'e varan indirim" gibi ifadelerden yanlış
# çıkarılmış; 0 ise ham ifadesi '0%' olan bir kayıttan geliyor. İkisi de
# hesaplanırsa sonuç listenin uçlarına yerleşir ve kendinden emin biçimde
# sunulur — "Belirtilmemiş" demek her zaman daha dürüst.


@pytest.mark.parametrize("oran", [0.0, 15.0, 42.0, 84.93])
def test_makul_olmayan_orandan_maliyet_hesaplanmaz(ajan, oran):
    sonuc = ajan.degerlendir(PROFIL, _kampanya(oran=oran))
    assert sonuc.maliyet is None


@pytest.mark.parametrize("oran", [0.5, 1.89, 2.05, 14.9])
def test_makul_oranlardan_maliyet_hesaplanir(ajan, oran):
    """Karşı kontrol: sınır, geçerli oranları elemiyor."""
    sonuc = ajan.degerlendir(PROFIL, _kampanya(oran=oran))
    assert sonuc.maliyet is not None


def test_sifir_oranli_kayit_listenin_tepesine_cikmaz(ajan):
    """'800.000 TL alıp 800.000 TL geri ödüyorsunuz' bankacı jüri önünde
    sistemin güvenilirliğini tek satırda bitirirdi."""
    kampanyalar = [
        _kampanya("SifirOran", oran=0.0, uygunluk=UygunlukKosullari(max_vade_ay=120)),
        _kampanya("Gercek", oran=1.89, uygunluk=UygunlukKosullari(max_vade_ay=120)),
    ]
    sonuclar, _ = ajan.calistir((PROFIL, kampanyalar))
    assert sonuclar[0].banka_adi == "Gercek"


# ---------------------------------------------------------------------------
# 27 Ağustos — maliyetsiz kalemlerin kendi içinde sırası
# ---------------------------------------------------------------------------


def test_maliyetsiz_kalemler_dolu_olandan_bosa_siralanir() -> None:
    """Gösterecek bilgisi olan kayıt, boş sayfanın ÖNÜNE geçmeli.

    Sıralama anahtarının orta basamağı sabit `0` iken kâr payı olmayan
    kayıtlar aralarında hiç sıralanmıyordu; jüri sorgusunda ilk beşin iki
    sırasını gösterilebilir alanı SIFIR olan hesaplama aracı sayfaları aldı.
    Ölçüt doluluktur — URL kalıbı değil (ADR 017 ile aynı refleks).
    """
    bos = _kampanya("Bos Sayfa", oran=None)
    dolu = _kampanya("Dolu Kayit", oran=None, tahsis=0.5)

    profil = MusteriProfili(musteri_tipi=None, tutar=1_000_000.0, vade_ay=120)
    sonuclar, _ = MuhakemeAjani().calistir((profil, [bos, dolu]))

    uygunlar = [s for s in sonuclar if s.uygun_mu]
    assert [s.banka_adi for s in uygunlar] == ["Dolu Kayit", "Bos Sayfa"]


def test_maliyetli_kayit_her_zaman_maliyetsizin_onunde() -> None:
    """Doluluk sıralaması yalnız MALİYETSİZ kova içinde çalışır."""
    maliyetli = _kampanya("Oranli", oran=2.95)
    maliyetsiz_dolu = _kampanya("Oransiz", oran=None, tahsis=0.5)

    profil = MusteriProfili(musteri_tipi=None, tutar=1_000_000.0, vade_ay=120)
    sonuclar, _ = MuhakemeAjani().calistir((profil, [maliyetsiz_dolu, maliyetli]))

    uygunlar = [s for s in sonuclar if s.uygun_mu]
    assert uygunlar[0].banka_adi == "Oranli"


def test_segment_gerekcesi_segment_adini_yazar() -> None:
    """«Kampanya segment için» bozuk cümleydi ve elde olan adı saklıyordu."""
    kampanya = _kampanya(
        "Emeklici",
        uygunluk=UygunlukKosullari(
            musteri_tipi=[HedefKitle.SEGMENT], segment_detayi=["emekli"]
        ),
    )
    profil = MusteriProfili(
        musteri_tipi=HedefKitle.MEVCUT_MUSTERI, tutar=100_000.0, vade_ay=12
    )
    sonuc = MuhakemeAjani().degerlendir(profil, kampanya)

    gerekce = next(g for g in sonuc.engelleyenler() if g.kural == "musteri_tipi")
    assert "emekli" in gerekce.aciklama
    assert "Kampanya segment için" not in gerekce.aciklama
