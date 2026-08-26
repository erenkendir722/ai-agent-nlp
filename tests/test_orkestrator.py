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
from src.schema import Alan, HedefKitle, Kampanya, UygunlukKosullari


def _kampanya(ad="Test Bankası", *, oran=1.89, uygunluk=None) -> Kampanya:
    return Kampanya(
        banka_adi=ad,
        banka_kodu="0299",
        kampanya_id=f"0299-{ad}",
        kaynak_url=f"https://{ad}.test",
        cekim_tarihi=datetime(2026, 8, 14),
        kar_payi_orani=(
            Alan(deger=oran, ham_ifade=f"%{oran}", guven=0.9, yontem="kural")
            if oran is not None
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
        ("800.000 TL, 120 ay", "müşteri tipi"),
    ],
)
def test_eksik_bilgi_tahmin_edilmez(soru, beklenen_eksik):
    """Varsayılan bir tutar veya vade koymak, taksitten toplam maliyete kadar
    her sayıyı sessizce yanlışlardı."""
    profil, eksikler = profil_ayristir(soru)
    assert profil is None
    assert any(beklenen_eksik in e for e in eksikler)


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
