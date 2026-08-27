"""Boyut sözleşmesi — birimsiz sayı taşınamaz (bulgu 1.1).

18 Ağustos ölçümünde `tahsis_ucreti` sütununda şunlar yan yanaydı:

    0.5   <- "0,50%"  maliyet tablosundaki ORAN
    75.0  <- "%75"    komisyon indirimi (ayrı bir hata, bkz. 1.1b)
    500.0 <- "500 TL" gerçek TL tutarı

Ayrıştırıcılar birimi görüyor ama atıyordu:

    ayristirici=lambda s: para_ayristir(s, ...) or oran_ayristir(s)

İki yerde birden patlıyordu: arayüz «Tahsis ücreti: 0,50 TL» yazıyor, «en
düşük masraf» sıralaması %0,50'yi en ucuz sayıyordu. Oysa 100.000 TL'lik bir
finansmanda %0,50 = 500 TL, yani ikisi EŞİT.

Bu testler üç katmanı birden sabitler: şema sözleşmesi, gösterim, sıralama.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.comparison.karsilastirma import (
    Kriter,
    Senaryo,
    ortak_tabana_indir,
    sirala,
    uyarilar,
)
from src.depolama import COK_BIRIMLI_ALANLAR, KampanyaKaydi
from src.preprocessing.normalizasyon import birim_belirle
from src.rag.chatbot import alan_goster
from src.schema import (
    ALAN_BOYUTLARI,
    TEK_BIRIMLI_ALANLAR,
    Alan,
    Birim,
    Kampanya,
)


def _kampanya(**alanlar: Alan) -> Kampanya:
    return Kampanya(
        banka_adi="Test Katılım Bankası A.Ş.",
        banka_kodu="0299",
        kampanya_id="0299-test",
        kaynak_url="https://ornek.test/kampanya",
        cekim_tarihi=datetime(2026, 8, 9),
        **alanlar,
    )


def _kayit(**alanlar: object) -> KampanyaKaydi:
    varsayilan = {
        "kampanya_id": "0299-test",
        "banka_kodu": "0299",
        "banka_adi": "Test Katılım Bankası A.Ş.",
        "kaynak_url": "https://ornek.test/kampanya",
        "cekim_tarihi": datetime(2026, 8, 9),
        "tam_kayit": {},
        "ham_metin": "",
        "ortalama_guven": 0.0,
        "doluluk_orani": 0.0,
        # Kâr payı sıralaması yalnız FİNANSMAN kampanyalarını kıyaslar
        # (`karsilastirma.OLCUT_KAPSAMI`); bu testler sıralama mekaniğini
        # ölçüyor, ürün sınıfını değil.
        "kampanya_turu": "ihtiyac_finansmani",
    }
    return KampanyaKaydi(**{**varsayilan, **alanlar})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 1) Birim çözümleme — tek çözümleyici, iki soru
# ---------------------------------------------------------------------------


class TestBirimBelirle:
    @pytest.mark.parametrize(
        ("ham", "alan", "beklenen"),
        [
            ("0,50%", "tahsis_ucreti", Birim.YUZDE),
            ("%0,50", "tahsis_ucreti", Birim.YUZDE),
            ("500 TL", "tahsis_ucreti", Birim.TL),
            ("500₺", "tahsis_ucreti", Birim.TL),
            ("%75", "tahsis_ucreti", Birim.YUZDE),
        ],
    )
    def test_cok_birimli_alan_ham_ifadeden_cozulur(
        self, ham: str, alan: str, beklenen: Birim
    ) -> None:
        assert birim_belirle(ham, alan) is beklenen

    @pytest.mark.parametrize("alan", sorted(TEK_BIRIMLI_ALANLAR))
    def test_tek_birimli_alan_metne_bakmaz(self, alan: str) -> None:
        """Sözleşme zaten biliyor; metne bakmak gereksiz risk olurdu."""
        assert birim_belirle("anlamsız girdi", alan) is TEK_BIRIMLI_ALANLAR[alan]
        assert birim_belirle(None, alan) is TEK_BIRIMLI_ALANLAR[alan]

    def test_cozulemeyen_cok_birimli_none_doner(self) -> None:
        assert birim_belirle("belirsiz bir ifade", "tahsis_ucreti") is None


# ---------------------------------------------------------------------------
# 2) Şema sözleşmesi — birimsiz sayı taşınamaz
# ---------------------------------------------------------------------------


class TestBoyutSozlesmesi:
    def test_cok_birimli_alan_birimsiz_tasinmaz(self) -> None:
        """Bulgunun kalbi: `0.5` ile `500.0` bir daha aynı sütunda ayrımsız duramaz."""
        with pytest.raises(ValidationError, match="birim beyan etmeden"):
            _kampanya(
                tahsis_ucreti=Alan(
                    deger=0.5, ham_ifade="0,50%", guven=0.9, yontem="kural"
                )
            )

    def test_tek_birimli_alanin_birimi_sozlesmeden_dolar(self) -> None:
        """Her çıkarım yolunda ayrıca yazmak, bir yolda unutulmasını garantiler."""
        k = _kampanya(
            kar_payi_orani=Alan(deger=1.89, ham_ifade="%1,89", guven=0.9, yontem="kural")
        )
        assert k.kar_payi_orani.birim is Birim.YUZDE

    def test_kabul_edilmeyen_birim_reddedilir(self) -> None:
        """`odul_miktari` yüzde olamaz — sınıf genellemesi."""
        with pytest.raises(ValidationError, match="geçersiz"):
            _kampanya(
                odul_miktari=Alan(
                    deger=75.0,
                    ham_ifade="%75",
                    guven=0.9,
                    yontem="kural",
                    birim=Birim.YUZDE,
                )
            )

    def test_bos_alan_birim_istemez(self) -> None:
        assert _kampanya(tahsis_ucreti=Alan.yok()).tahsis_ucreti.birim is None

    def test_beyan_edilmis_birim_korunur(self) -> None:
        k = _kampanya(
            tahsis_ucreti=Alan(
                deger=500.0, ham_ifade="500 TL", guven=0.9, yontem="kural",
                birim=Birim.TL,
            )
        )
        assert k.tahsis_ucreti.birim is Birim.TL


# ---------------------------------------------------------------------------
# 3) Gösterim birimden türer — "0,50 TL" bir daha yazılamaz
# ---------------------------------------------------------------------------


class TestGosterim:
    def test_yuzde_ucret_tl_olarak_yazilmaz(self) -> None:
        """REGRESYON — ekrandaki «Tahsis ücreti: 0,50 TL»."""
        yazi = alan_goster("tahsis_ucreti", 0.5, Birim.YUZDE)
        assert yazi == "%0,50"
        assert "TL" not in yazi

    def test_tl_ucret_tl_olarak_yazilir(self) -> None:
        assert alan_goster("tahsis_ucreti", 500.0, Birim.TL) == "500 TL"

    def test_ayni_sayi_farkli_birimde_farkli_yazilir(self) -> None:
        """Sabit şablon olsaydı ikisi de aynı yazılırdı — hatanın kaynağı buydu."""
        assert alan_goster("tahsis_ucreti", 500.0, Birim.TL) != alan_goster(
            "tahsis_ucreti", 500.0, Birim.YUZDE
        )


# ---------------------------------------------------------------------------
# 4) Karşılaştırma ortak tabana indirir ya da SUSAR
# ---------------------------------------------------------------------------


SENARYO = Senaryo(anapara=100_000.0, vade_ay=36)


class TestOrtakTaban:
    def test_yuzde_ve_tl_senaryoda_esitlenir(self) -> None:
        """Bulgunun finansal özü: 100.000 TL'de %0,50 = 500 TL."""
        yuzde = _kayit(kampanya_id="a", tahsis_ucreti=0.5, tahsis_ucreti_birim="yuzde")
        tl = _kayit(kampanya_id="b", tahsis_ucreti=500.0, tahsis_ucreti_birim="tl")
        assert ortak_tabana_indir(yuzde, "tahsis_ucreti", SENARYO) == pytest.approx(
            ortak_tabana_indir(tl, "tahsis_ucreti", SENARYO)
        )

    def test_senaryosuz_yuzde_indirgenmez(self) -> None:
        """Uydurulmuş bir taban yerine «indiremiyorum» demek."""
        yuzde = _kayit(tahsis_ucreti=0.5, tahsis_ucreti_birim="yuzde")
        assert ortak_tabana_indir(yuzde, "tahsis_ucreti", None) is None

    def test_senaryosuz_yuzde_siralamada_sona_gider(self) -> None:
        """REGRESYON — %0,50 «en ucuz» görünüyordu."""
        yuzde = _kayit(kampanya_id="a", tahsis_ucreti=0.5, tahsis_ucreti_birim="yuzde")
        tl = _kayit(kampanya_id="b", tahsis_ucreti=500.0, tahsis_ucreti_birim="tl")
        sirali = sirala([yuzde, tl], Kriter.EN_DUSUK_MASRAF)
        assert sirali[0].kampanya_id == "b", "indirgenemeyen değer başa geçti"

    def test_senaryoda_gercek_ucuz_one_gecer(self) -> None:
        ucuz = _kayit(kampanya_id="a", tahsis_ucreti=0.1, tahsis_ucreti_birim="yuzde")
        pahali = _kayit(kampanya_id="b", tahsis_ucreti=500.0, tahsis_ucreti_birim="tl")
        sirali = sirala([pahali, ucuz], Kriter.EN_DUSUK_MASRAF, senaryo=SENARYO)
        assert sirali[0].kampanya_id == "a"  # %0,1 x 100.000 = 100 TL

    def test_tek_birimli_alan_senaryosuz_da_siralanir(self) -> None:
        """Ortak taban zorunluluğu yalnız çok birimli alanlara aittir."""
        a = _kayit(kampanya_id="a", kar_payi_orani=2.95)
        b = _kayit(kampanya_id="b", kar_payi_orani=1.89)
        assert sirala([a, b], Kriter.EN_DUSUK_KAR_PAYI)[0].kampanya_id == "b"

    def test_birim_karisimi_beyan_edilir(self) -> None:
        """Sessiz yanlış sıralama yerine beyan edilmiş belirsizlik."""
        yuzde = _kayit(kampanya_id="a", tahsis_ucreti=0.5, tahsis_ucreti_birim="yuzde")
        tl = _kayit(kampanya_id="b", tahsis_ucreti=500.0, tahsis_ucreti_birim="tl")
        mesajlar = uyarilar([yuzde, tl])
        assert any("farklı birimlerde" in m for m in mesajlar)


# ---------------------------------------------------------------------------
# 5) SINIF TESTLERİ — sözleşme büyüdüğünde eksik kalan yeri gösterir
# ---------------------------------------------------------------------------


class TestSozlesmeButunlugu:
    @pytest.mark.parametrize("alan", sorted(COK_BIRIMLI_ALANLAR))
    def test_cok_birimli_alanin_depolama_sutunu_var(self, alan: str) -> None:
        """`ALAN_BOYUTLARI`'na yeni bir çok birimli alan eklenirse sütunu da gerekir.

        Aksi hâlde birim çıkarımda üretilir ama depolamada kaybolur — bulgunun
        ta kendisi, bir katman ötede.
        """
        assert hasattr(KampanyaKaydi, f"{alan}_birim"), (
            f"{alan} çok birimli ama `KampanyaKaydi.{alan}_birim` sütunu yok"
        )

    @pytest.mark.parametrize("alan", sorted(ALAN_BOYUTLARI))
    def test_her_sayisal_alanin_boyutu_beyan_edilmis(self, alan: str) -> None:
        assert ALAN_BOYUTLARI[alan], f"{alan} için izinli birim kümesi boş"

    def test_tek_birimli_kumesi_sozlesmeden_turer(self) -> None:
        """İki liste elle tutulsaydı zamanla ayrışırdı."""
        for ad, birimler in ALAN_BOYUTLARI.items():
            if len(birimler) == 1:
                assert TEK_BIRIMLI_ALANLAR[ad] is next(iter(birimler))
            else:
                assert ad not in TEK_BIRIMLI_ALANLAR
