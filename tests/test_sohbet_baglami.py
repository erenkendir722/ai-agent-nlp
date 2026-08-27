"""Çok turlu sohbet — YUVA DEVRİ. AĞ İSTEMEZ.

27 Ağustos'ta ölçüldü: chatbot her soruyu SIFIRDAN okuyordu ve takip
sorusu diye bir şey yoktu.

    tur 1: «Albaraka en yüksek kâr payı oranı ne?» -> Albaraka, aylık %2,87
    tur 2: «120 ay vade»                          -> Kuveyt Türk, 48 ay   ✗

    tur 1: «1.000.000 TL konut finansmanı istiyorum»
             -> «Uygunluk değerlendirmesi için eksik: vade»
    tur 2: «120 ay vade»                          -> Kuveyt Türk          ✗

İkincisi ağır olanı: SİSTEM SORUYU KENDİ SORUYOR, CEVABINI KULLANAMIYOR.

Buradaki testler devrin ÇALIŞTIĞINI değil, DOĞRU YERDE DURDUĞUNU da
denetler: kapsam kalkanı ham soruya çalışmalı, korpusa sorulan soru yuva
devralmamalı, soruda yazılan her zaman devralınanı ezmeli.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.ajanlar.orkestrator import Orkestrator
from src.depolama import KampanyaKaydi
from src.rag.baglam import (
    AZAMI_DEVIR_BANKASI,
    SohbetBaglami,
    korpusa_soruluyor,
    soruyu_tamamla,
)
from src.rag.chatbot import _OLCUT_ETIKETLERI, Koken, Niyet, _sorulan_olcut, sor

ALBARAKA = "Albaraka Türk Katılım Bankası A.Ş."
KUVEYT = "Kuveyt Türk Katılım Bankası A.Ş."
ZIRAAT = "Ziraat Katılım Bankası A.Ş."


def _kayit(kimlik: str, banka: str, **alanlar: object) -> KampanyaKaydi:
    varsayilan: dict[str, object] = {
        "kampanya_id": kimlik,
        "banka_kodu": kimlik[:4],
        "banka_adi": banka,
        "kaynak_url": f"https://ornek.test/{kimlik}",
        "cekim_tarihi": datetime(2026, 8, 27),
        "tam_kayit": "{}",
        "ham_metin": "ornek",
        "kampanya_turu": "konut",
        "urun_turu": "Konut Finansmanı",
        "ortalama_guven": 0.9,
        "doluluk_orani": 0.8,
    }
    return KampanyaKaydi(**{**varsayilan, **alanlar})  # type: ignore[arg-type]


@pytest.fixture
def korpus() -> list[KampanyaKaydi]:
    """Üç banka, banka başına İKİ kampanya.

    İkinci kampanya şart: `_karsilastirma_cevabi` tek kayıtla «karşılaştırma
    için en az iki bankanın kaydı gerekiyor» diyor ve banka süzgecinden
    sonra tek kayıt kalırsa cevap boşa düşüyor — devrin denetlenmesi
    gereken yol hiç koşmuyordu.
    """
    return [
        _kayit("alba-1", ALBARAKA, kar_payi_orani=2.87, vade_ay_max=120,
               finansman_tutari_max=2_000_000.0),
        _kayit("alba-2", ALBARAKA, kar_payi_orani=1.75, vade_ay_max=36,
               finansman_tutari_max=750_000.0, kampanya_turu="tasit",
               urun_turu="Taşıt Finansmanı"),
        _kayit("kuvt-1", KUVEYT, kar_payi_orani=1.99, vade_ay_max=60,
               finansman_tutari_max=1_500_000.0),
        _kayit("kuvt-2", KUVEYT, kar_payi_orani=1.25, vade_ay_max=24,
               finansman_tutari_max=500_000.0, kampanya_turu="tasit",
               urun_turu="Taşıt Finansmanı"),
        _kayit("zirt-1", ZIRAAT, kar_payi_orani=1.45, vade_ay_max=36,
               finansman_tutari_max=1_000_000.0),
        _kayit("zirt-2", ZIRAAT, kar_payi_orani=1.10, vade_ay_max=12,
               finansman_tutari_max=300_000.0, kampanya_turu="tasit",
               urun_turu="Taşıt Finansmanı"),
    ]


def _bankalar(cevap: object) -> set[str]:
    return {k.banka_adi for k in cevap.kullanilan_kayitlar}  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Devrin kendisi
# ---------------------------------------------------------------------------


def test_takip_sorusu_bankayi_devralir(korpus: list[KampanyaKaydi]) -> None:
    """Kullanıcının bildirdiği kusur: «120 ay vade» dediğimde konu Albaraka."""
    ilk = sor("Albaraka en yüksek kâr payı oranı ne?", korpus)
    assert _bankalar(ilk) == {ALBARAKA}

    takip = sor("120 ay vade", korpus, baglam=ilk.baglam)
    assert _bankalar(takip) == {ALBARAKA}, "banka devralınmadı"


def test_soruda_adlandirilan_banka_devralinani_ezer(korpus: list[KampanyaKaydi]) -> None:
    """«peki Kuveyt Türk?» — dolu yuvaya devir DOKUNMAZ, ölçüt devrolur."""
    ilk = sor("Albaraka en yüksek kâr payı oranı ne?", korpus)
    takip = sor("peki Kuveyt Türk?", korpus, baglam=ilk.baglam)

    assert _bankalar(takip) == {KUVEYT}
    assert takip.baglam.olcut == "kar_payi_orani", "ölçüt yuvası boştu, devralmalıydı"


def test_devir_cevapta_beyan_edilir(korpus: list[KampanyaKaydi]) -> None:
    """Kullanıcının yazmadığı bir kısıtla cevap verildiyse bunu görmeli.

    «Müşteri tipi belirtilmedi» dürüstlüğünün aynısı. Beyan `Koken.SISTEM`
    olduğu için kalkandan da geçer — muaf bir dipnot değil.
    """
    ilk = sor("Albaraka en yüksek kâr payı oranı ne?", korpus)
    takip = sor("120 ay vade", korpus, baglam=ilk.baglam)

    beyanlar = [p for p in takip.parcalar if p.metin.strip().startswith("_Bağlam:")]
    assert len(beyanlar) == 1, "devir beyan edilmedi"
    assert ALBARAKA in beyanlar[0].metin
    assert beyanlar[0].koken is Koken.SISTEM
    assert takip.dogrulama_gecti, takip.reddedilen_sayilar


def test_devir_yoksa_beyan_da_yok(korpus: list[KampanyaKaydi]) -> None:
    """Soru kendi başına ayaktaysa cevabın altına dipnot eklenmez."""
    ilk = sor("Albaraka en yüksek kâr payı oranı ne?", korpus)
    takip = sor("Ziraat Katılım'ın vadesi ne kadar?", korpus, baglam=ilk.baglam)
    assert not any("_Bağlam:" in p.metin for p in takip.parcalar)


# ---------------------------------------------------------------------------
# Devrin DURMASI gereken yerler
# ---------------------------------------------------------------------------


def test_kapsam_disi_soru_baglamla_kurtarilmaz(korpus: list[KampanyaKaydi]) -> None:
    """Kapsam kapıları HAM soruya çalışır — devir kalkanı delemez.

    Sıra tersine dönseydi `terim_gecer`'in kapattığı delik arka kapıdan
    geri açılırdı: alakasız soru, önceki turdan banka devralıp kapsam içi
    sayılırdı.
    """
    ilk = sor("Albaraka en yüksek kâr payı oranı ne?", korpus)
    takip = sor("Python'da liste nasıl ters çevrilir?", korpus, baglam=ilk.baglam)
    assert takip.niyet is Niyet.KAPSAM_DISI


def test_korpusa_sorulan_soru_yuva_devralmaz(korpus: list[KampanyaKaydi]) -> None:
    """«hangi bankalar…» dokuz bankaya sorulur; devir onu bire indiremez.

    Devralınan «en yüksek» soruyu LİSTE olmaktan çıkarıp SIRALAMAYA
    çeviriyordu (`_SIRALAMA_ISARETLERI` «en » ile eşleşiyor).
    """
    ilk = sor("Albaraka en yüksek kâr payı oranı ne?", korpus)
    takip = sor("hangi bankalar konut finansmanı sunuyor?", korpus, baglam=ilk.baglam)

    assert _bankalar(takip) == {ALBARAKA, KUVEYT, ZIRAAT}
    assert not any("_Bağlam:" in p.metin for p in takip.parcalar)


@pytest.mark.parametrize(
    "soru",
    ["hangi bankalar taşıt sunuyor", "tüm bankaların vadesi", "her bankada masraf var mı"],
)
def test_korpus_belirteci_tanınır(soru: str) -> None:
    assert korpusa_soruluyor(soru)


@pytest.mark.parametrize("soru", ["peki Kuveyt Türk?", "120 ay vade", "hangisi daha ucuz"])
def test_takip_sorusu_korpus_sayılmaz(soru: str) -> None:
    assert not korpusa_soruluyor(soru)


def test_yon_yalniz_olcutle_devrolur(korpus: list[KampanyaKaydi]) -> None:
    """Yön ölçütün NİTELEMESİDİR; tek başına devredilirse yanlış uç sorulur.

    Ölçüldü: «en düşük kâr payı» bağlamı taşınırken «vadesi kaç ay?»
    sorusuna EN KISA vade cevap olarak dönüyordu.
    """
    baglam = SohbetBaglami(bankalar=(ALBARAKA,), olcut="kar_payi_orani", yon="dusuk")
    devir = soruyu_tamamla("vadesi kaç ay", baglam, korpus)

    yuvalar = dict(devir.yuvalar)
    assert "Ölçüt" not in yuvalar, "soru ölçütü kendisi adlandırıyor"
    assert "Yön" not in yuvalar, "ölçüt devrolmadan yön devredilemez"


def test_ikiden_fazla_banka_devrolmaz(korpus: list[KampanyaKaydi]) -> None:
    """Üç bankalı bir cevap bir KONU değil, korpusun kendisidir."""
    cevap = sor("hangi bankalar konut finansmanı sunuyor?", korpus)
    assert len(_bankalar(cevap)) > AZAMI_DEVIR_BANKASI
    assert cevap.baglam.bankalar == ()


def test_tanim_sorusu_baglami_ne_kurar_ne_bozar(korpus: list[KampanyaKaydi]) -> None:
    """Araya giren «murabaha nedir?» konuyu silmemeli — üçüncü tur çalışsın."""
    ilk = sor("Albaraka en yüksek kâr payı oranı ne?", korpus)
    ara = sor("murabaha nedir", korpus, baglam=ilk.baglam)

    assert ara.niyet is Niyet.TANIM_SORGUSU
    assert ara.baglam == ilk.baglam
    assert _bankalar(sor("120 ay vade", korpus, baglam=ara.baglam)) == {ALBARAKA}


# ---------------------------------------------------------------------------
# Tek turlu yol değişmedi
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "soru",
    [
        "Albaraka en yüksek kâr payı oranı ne?",
        "hangi bankalar konut finansmanı sunuyor?",
        "Kuveyt Türk'ün vadesi kaç ay?",
        "murabaha nedir",
    ],
)
def test_baglamsiz_cagri_davranisi_degistirmez(
    soru: str, korpus: list[KampanyaKaydi]
) -> None:
    """`make eval` tek turlu koşuyor: bağlamsız cevap BİREBİR eski cevap.

    Bu nöbetçi olmadan, çok turlu yolda yapılan bir düzeltme ölçülen
    metrikleri sessizce oynatabilirdi.
    """
    assert sor(soru, korpus).metin == sor(soru, korpus, baglam=None).metin


def test_olcut_etiketi_kendi_alanina_geri_eslesir() -> None:
    """Devir metni ELLE YAZILMIYOR, `_OLCUT_ETIKETLERI`'nden türüyor (ADR 021).

    Türetimin şartı: etiket soruya eklendiğinde `_sorulan_olcut` onu AYNI
    alana geri çevirmeli. Etiket bir gün «Kâr payı» yerine «Getiri oranı»
    olursa bu test kırılır — devir sessizce yanlış alanı sormaya başlamaz.
    """
    for alan, etiket in _OLCUT_ETIKETLERI.items():
        assert _sorulan_olcut(etiket) == alan, f"{etiket!r} -> {alan} eşleşmiyor"


# ---------------------------------------------------------------------------
# Profil kolu — sistemin kendi sorduğu sorunun cevabı
# ---------------------------------------------------------------------------


def test_eksik_vade_sonraki_turda_tamamlanir(korpus: list[KampanyaKaydi]) -> None:
    """Ağır kusur: sistem «vade eksik» diyor, gelen cevabı kullanamıyordu."""
    ork = Orkestrator()
    ilk, _ = ork.calistir("1.000.000 TL konut finansmanı istiyorum", [], kayitlar=korpus)
    assert "eksik" in ilk.metin
    assert ilk.baglam.profil_kipi and ilk.baglam.tutar == 1_000_000.0

    takip, defter = ork.calistir("120 ay vade", [], kayitlar=korpus, baglam=ilk.baglam)

    assert "eksik" not in takip.metin, "vade devralınmadı, profil yine kurulamadı"
    assert "1.000.000 TL" in takip.metin and "120 ay" in takip.metin
    assert any(iz.ajan_adi == "muhakeme" for iz in defter.izler)
    assert takip.dogrulama_gecti, takip.reddedilen_sayilar


def test_devralinan_tutar_profil_kolunda_beyan_edilir(
    korpus: list[KampanyaKaydi],
) -> None:
    """Devralınan TUTAR sayı taşıyan bir iddiadır: beyan edilir ve denetlenir."""
    ork = Orkestrator()
    ilk, _ = ork.calistir("1.000.000 TL konut finansmanı istiyorum", [], kayitlar=korpus)
    takip, _ = ork.calistir("120 ay vade", [], kayitlar=korpus, baglam=ilk.baglam)

    beyan = next(p for p in takip.parcalar if p.metin.strip().startswith("_Bağlam:"))
    assert "1.000.000 TL" in beyan.metin
    assert beyan.hesap == {"devralinan_tutar": 1_000_000.0}
    assert takip.dogrulama_gecti


def test_tutar_yalniz_profil_kipinde_devrolur(korpus: list[KampanyaKaydi]) -> None:
    """Başıboş bir tutar sonraki OLGU sorusunu profil sorgusuna çevirmemeli."""
    baglam = SohbetBaglami(tutar=1_000_000.0, vade_ay=120, profil_kipi=False)
    devir = soruyu_tamamla("Albaraka'nın kâr payı oranı ne?", baglam, korpus)
    assert devir.yuvalar == ()


# ---------------------------------------------------------------------------
# API — durum SUNUCUDA değil, istemcide
# ---------------------------------------------------------------------------


def test_api_baglami_sozluge_ve_geri_cevirir() -> None:
    """`/ask` oturum tutmaz: bağlam cevapla gider, istekle geri gelir.

    Gidiş-dönüş kayıpsız olmalı — aksi hâlde ikinci turda yuva sessizce
    boşalır ve kullanıcı «sistem beni unuttu» der, sebebi hiçbir yere
    yazılmaz.
    """
    from src.api.sunucu import _baglam_coz, _baglam_sozluk

    baglam = SohbetBaglami(
        bankalar=(ALBARAKA,), urun="konut", olcut="kar_payi_orani",
        yon="yuksek", tutar=1_000_000.0, vade_ay=120, profil_kipi=True,
    )
    assert _baglam_coz(_baglam_sozluk(baglam)) == baglam
    assert _baglam_coz(None) is None


def test_api_bilinmeyen_baglam_alanini_reddeder() -> None:
    """Yazım hatası SESSİZCE ATILMAZ: devrolmayan yuvanın sebebi görünür olsun."""
    from fastapi import HTTPException

    from src.api.sunucu import _baglam_coz

    with pytest.raises(HTTPException) as hata:
        _baglam_coz({"banka": [ALBARAKA]})
    assert hata.value.status_code == 400
    assert "banka" in str(hata.value.detail)


def test_kayit_kullanmayan_cevapta_banka_sorudan_devrolur(
    korpus: list[KampanyaKaydi],
) -> None:
    """Kullanıcıdan bilgi isteyen cevabın YAPISAL PARÇASI YOKTUR.

    «Albaraka'dan 1.000.000 TL konut» -> «vade eksik» cevabı hiçbir kayıt
    göstermez. Banka yalnız `kullanilan_kayitlar`'dan okunsaydı sohbet o
    bankayı unuturdu ve sonraki tur dokuz bankayı sıralardı — tam da
    kullanıcının adlandırdığı bankayı yok sayarak.
    """
    ork = Orkestrator()
    ilk, _ = ork.calistir(
        "Albaraka'dan 1.000.000 TL konut finansmanı istiyorum", [], kayitlar=korpus
    )
    assert ilk.kullanilan_kayitlar == []
    assert ilk.baglam.bankalar == (ALBARAKA,), "banka sorudan devralınmadı"


def test_hesaplanan_olcut_iki_bankayi_da_devreder(korpus: list[KampanyaKaydi]) -> None:
    """Amiral gemisi soru: iki banka + hesaplanan ölçüt + eksik anapara."""
    ork = Orkestrator()
    ilk, _ = ork.calistir(
        "Albaraka'nın 120 ay vadeli konut finansmanında toplam maliyeti "
        "Kuveyt Türk'ünkinden düşük mü?",
        [],
        kayitlar=korpus,
    )
    assert ilk.beklenen_yuvalar == ("tutar",), "vade soruda vardı"
    assert set(ilk.baglam.bankalar) == {ALBARAKA, KUVEYT}
    assert ilk.baglam.vade_ay == 120
