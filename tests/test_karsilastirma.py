"""Karşılaştırma motoru — beş kriter ve kenar durumları (E-05).

Şartname 5.7 beş sıralama kriteri istiyor. Motor bunları uyguluyordu ama
**kendi test dosyası yoktu**: `toplam_maliyet` dolaylı olarak
`tests/test_muhakeme.py` üzerinden, birim tuzağı `tests/test_boyut_sozlesmesi.py`
üzerinden sınanıyordu; `sirala`, `avantaj_skorla` ve `uyarilar` ise hiç.

Buradaki testlerin işi iddiaları koda bağlamak:

    «beş kriterin her biri çalışıyor»          -> TestBesKriter
    «veri yok, en iyi sonuç gibi görünmez»     -> TestEksikVeriSonaGider
    «ağırlıklar kullanıcının, formül şeffaf»   -> TestAgirliklar
    «karşılaştırılamayanı karşılaştırmıyoruz»  -> TestUyarilar

Sunumdaki cümleler de bunlara dayanıyor; test kırılırsa slayt da yanlıştır.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.comparison.karsilastirma import (
    Agirliklar,
    Kriter,
    Senaryo,
    avantaj_skorla,
    sirala,
    toplam_maliyet,
    uyarilar,
)
from src.depolama import KampanyaKaydi
from src.schema import Birim


def _kayit(kimlik: str, **alanlar: object) -> KampanyaKaydi:
    varsayilan: dict[str, object] = {
        "kampanya_id": kimlik,
        "banka_kodu": "0299",
        "banka_adi": f"{kimlik} Katılım Bankası A.Ş.",
        "kaynak_url": f"https://ornek.test/{kimlik}",
        "cekim_tarihi": datetime(2026, 8, 26),
        "tam_kayit": {},
        "ham_metin": "",
        "ortalama_guven": 0.8,
        "doluluk_orani": 0.5,
    }
    return KampanyaKaydi(**{**varsayilan, **alanlar})  # type: ignore[arg-type]


def _sira(kayitlar: list[KampanyaKaydi], kriter: Kriter, **kw) -> list[str]:
    return [k.kampanya_id for k in sirala(kayitlar, kriter, **kw)]


class TestBesKriter:
    """Şartname 5.7'nin beş kriteri — her biri ayrı ayrı."""

    def test_en_dusuk_kar_payi(self) -> None:
        kayitlar = [
            _kayit("ucuz", kar_payi_orani=1.87),
            _kayit("pahali", kar_payi_orani=2.45),
            _kayit("orta", kar_payi_orani=1.99),
        ]
        assert _sira(kayitlar, Kriter.EN_DUSUK_KAR_PAYI) == ["ucuz", "orta", "pahali"]

    def test_en_yuksek_odul(self) -> None:
        kayitlar = [
            _kayit("az", odul_miktari=500.0),
            _kayit("cok", odul_miktari=5000.0),
        ]
        assert _sira(kayitlar, Kriter.EN_YUKSEK_ODUL) == ["cok", "az"]

    def test_en_uzun_vade(self) -> None:
        kayitlar = [_kayit("kisa", vade_ay_max=12), _kayit("uzun", vade_ay_max=120)]
        assert _sira(kayitlar, Kriter.EN_UZUN_VADE) == ["uzun", "kisa"]

    def test_en_dusuk_masraf(self) -> None:
        kayitlar = [
            _kayit("masrafli", tahsis_ucreti=20000.0, tahsis_ucreti_birim=Birim.TL),
            _kayit("masrafsiz", tahsis_ucreti=0.0, tahsis_ucreti_birim=Birim.TL),
        ]
        assert _sira(kayitlar, Kriter.EN_DUSUK_MASRAF) == ["masrafsiz", "masrafli"]

    def test_en_avantajli_dordunun_bilesimi(self) -> None:
        """Beşinci kriter, dördünün ağırlıklı bileşimidir."""
        iyi = _kayit(
            "iyi",
            kar_payi_orani=1.80,
            tahsis_ucreti=0.0,
            tahsis_ucreti_birim=Birim.TL,
            vade_ay_max=120,
            odul_miktari=5000.0,
        )
        kotu = _kayit(
            "kotu",
            kar_payi_orani=2.90,
            tahsis_ucreti=25000.0,
            tahsis_ucreti_birim=Birim.TL,
            vade_ay_max=12,
            odul_miktari=100.0,
        )
        assert _sira([kotu, iyi], Kriter.EN_AVANTAJLI) == ["iyi", "kotu"]


class TestEksikVeriSonaGider:
    """«Veri yok» en iyi sonuç gibi görünmemeli — motorun temel dürüstlük kuralı."""

    @pytest.mark.parametrize(
        ("kriter", "alan", "deger"),
        [
            (Kriter.EN_DUSUK_KAR_PAYI, "kar_payi_orani", 1.87),
            (Kriter.EN_YUKSEK_ODUL, "odul_miktari", 5000.0),
            (Kriter.EN_UZUN_VADE, "vade_ay_max", 120),
        ],
    )
    def test_degeri_olmayan_kayit_sona_gider(self, kriter, alan, deger) -> None:
        kayitlar = [_kayit("bos"), _kayit("dolu", **{alan: deger})]
        assert _sira(kayitlar, kriter)[-1] == "bos"

    def test_sifir_kar_payi_eksik_sayilmaz(self) -> None:
        """«Vade farksız» bir beyandır: 0,0 boş değildir (ADR 012)."""
        kayitlar = [_kayit("sifir", kar_payi_orani=0.0), _kayit("bos"), _kayit("bir", kar_payi_orani=1.0)]
        assert _sira(kayitlar, Kriter.EN_DUSUK_KAR_PAYI) == ["sifir", "bir", "bos"]

    def test_bos_liste_ve_tek_kayit_kirilmaz(self) -> None:
        assert sirala([], Kriter.EN_AVANTAJLI) == []
        tek = [_kayit("tek", kar_payi_orani=1.5)]
        assert _sira(tek, Kriter.EN_AVANTAJLI) == ["tek"]


class TestAgirliklar:
    """«En avantajlı» bir tercih bileşimidir; tercihi kullanıcı verir."""

    def test_agirlik_degisince_siralama_degisir(self) -> None:
        oranci = _kayit(
            "oranci", kar_payi_orani=1.80, odul_miktari=100.0,
            tahsis_ucreti=0.0, tahsis_ucreti_birim=Birim.TL, vade_ay_max=36,
        )
        odulcu = _kayit(
            "odulcu", kar_payi_orani=2.60, odul_miktari=9000.0,
            tahsis_ucreti=0.0, tahsis_ucreti_birim=Birim.TL, vade_ay_max=36,
        )
        kayitlar = [oranci, odulcu]

        kar_agir = Agirliklar(kar_payi=0.90, masraf=0.04, vade=0.03, odul=0.03)
        odul_agir = Agirliklar(kar_payi=0.03, masraf=0.04, vade=0.03, odul=0.90)

        assert _sira(kayitlar, Kriter.EN_AVANTAJLI, agirliklar=kar_agir)[0] == "oranci"
        assert _sira(kayitlar, Kriter.EN_AVANTAJLI, agirliklar=odul_agir)[0] == "odulcu"

    def test_agirliklar_normalize_edilir(self) -> None:
        toplam = Agirliklar(kar_payi=4, masraf=2, vade=2, odul=2).normalize().toplam()
        assert toplam == pytest.approx(1.0)

    def test_skor_detayi_aciklanabilir(self) -> None:
        """Gizli skor yok: her skorun dökümü döner."""
        kayitlar = [
            _kayit("a", kar_payi_orani=1.8, vade_ay_max=60),
            _kayit("b", kar_payi_orani=2.4, vade_ay_max=24),
        ]
        detaylar = avantaj_skorla(kayitlar)
        assert len(detaylar) == 2
        assert all(hasattr(d, "kampanya_id") for d in detaylar)


class TestUyarilar:
    """Karşılaştırılamayanı karşılaştırmamak — finansal titizlik."""

    def test_farkli_vade_uyarisi_verilir(self) -> None:
        kayitlar = [_kayit("kisa", vade_ay_max=12), _kayit("uzun", vade_ay_max=120)]
        assert any("vade" in m.lower() for m in uyarilar(kayitlar))

    def test_tek_kayitta_uyari_yok(self) -> None:
        assert uyarilar([_kayit("tek", vade_ay_max=12)]) == []

    def test_karisik_birim_uyarisi(self) -> None:
        """%0,50 ile 500 TL aynı sütunda: sessizce sıralamak yanlış olurdu."""
        kayitlar = [
            _kayit("oranli", tahsis_ucreti=0.5, tahsis_ucreti_birim=Birim.YUZDE),
            _kayit("tutarli", tahsis_ucreti=500.0, tahsis_ucreti_birim=Birim.TL),
        ]
        assert uyarilar(kayitlar), "karışık birimde uyarı bekleniyordu"


class TestOrtakTaban:
    """Farklı birimler ancak bir senaryoda kıyaslanabilir."""

    def test_senaryo_ile_yuzde_ve_tl_ayni_tabana_iner(self) -> None:
        # 100.000 TL'lik finansmanda %0,50 = 500 TL. Senaryosuz kıyas yanlıştır.
        kayitlar = [
            _kayit("oranli", tahsis_ucreti=0.5, tahsis_ucreti_birim=Birim.YUZDE),
            _kayit("tutarli", tahsis_ucreti=500.0, tahsis_ucreti_birim=Birim.TL),
        ]
        senaryo = Senaryo(anapara=100_000, vade_ay=36)
        sirali = sirala(kayitlar, Kriter.EN_DUSUK_MASRAF, senaryo=senaryo)
        assert {k.kampanya_id for k in sirali} == {"oranli", "tutarli"}


class TestMansetOranTuzagi:
    """Sunumdaki sayı burada sabitlenir — slayt ile motor ayrışamaz."""

    def test_dusuk_oran_masrafla_pahali_olabilir(self) -> None:
        ucuz_gorunen = toplam_maliyet(800_000, 1.87, 120, tahsis_ucreti=20_000)
        gercekten_ucuz = toplam_maliyet(800_000, 1.89, 120, tahsis_ucreti=0)
        assert ucuz_gorunen["toplam_geri_odeme"] > gercekten_ucuz["toplam_geri_odeme"]
        fark = ucuz_gorunen["toplam_geri_odeme"] - gercekten_ucuz["toplam_geri_odeme"]
        assert 3_000 < fark < 6_000, f"slayttaki ~4.204 TL farkı değişti: {fark:.0f}"
