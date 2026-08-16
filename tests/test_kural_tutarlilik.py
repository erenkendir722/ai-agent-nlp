"""Kural tablosunun YAPISAL tutarlılığı — tek tek davranışlar değil.

NEDEN BU TESTLER VAR:
    16 Ağustos'ta düzeltilen hata bir çıkarım hatası değil, bir TUTARSIZLIK
    hatasıydı: hesap makinesi widget'ının ürettiği tutar `finansman_tutari_max`
    için eleniyor, aynı widget'ın ürettiği oran `kar_payi_orani` için
    geçiyordu. Aynı bağlam türü bir alanda hata sayılıp diğerinde
    sayılmıyordu.

    Böyle bir hata tek tek alan testleriyle yakalanmaz — her test kendi
    alanında geçer. Yakalayan şey, kural tablosunun bütününe bakan bir
    sözleşmedir. Buradaki testler o sözleşmeyi yazıya döker: yeni bir kural
    eklendiğinde ortak korumaları almayı unutmak DERLENMEZ değil, ama
    TESTTEN GEÇMEZ.
"""

from __future__ import annotations

import re

import pytest

from src.preprocessing.normalizasyon import arama_anahtari
from src.extraction.kural import (
    AYLAR,
    D_TARIH,
    KURALLAR,
    SAYISAL_ALAN_VETOLARI,
    _ALAN_KURALI,
    _tarih_araligi_basi_mu,
    _tarih_araligi_sonu_mu,
)
from src.schema import SAYISAL_ALANLAR

# `kampanya_bitis` sayısal değil ama aynı bağlamlardan etkilenen tek
# istisna DEĞİL: tarih alanları hesap makinesi çıktısı üretmez.
ORTAK_VETO_BEKLENEN = tuple(a for a in SAYISAL_ALANLAR if a in _ALAN_KURALI)


def test_ortak_veto_bekleyen_alan_var():
    """Test kendi ön koşulunu doğrular — boş küme üstünde dönen test yeşil yalan söyler."""
    assert len(ORTAK_VETO_BEKLENEN) >= 4


@pytest.mark.parametrize("alan_adi", ORTAK_VETO_BEKLENEN)
def test_her_sayisal_alan_ortak_vetolari_tasir(alan_adi: str):
    """Bir bağlam türü bir alanda hataysa, hepsinde hatadır.

    Hesap makinesi çıktısı, örnek ödeme tablosu, mevduat ürünü ve vergi
    oranı — bunların hiçbiri kampanya koşulu değildir ve hangi alana
    düştüğü bunu değiştirmez.
    """
    kural = _ALAN_KURALI[alan_adi]
    eksik = set(SAYISAL_ALAN_VETOLARI) - set(kural.veto_ifadeleri)
    assert not eksik, f"{alan_adi} ortak vetoları taşımıyor: {sorted(eksik)}"


def test_veto_ifadeleri_normalize_bicimde_yazilir():
    """Vetolar `arama_anahtari` çıktısıyla karşılaştırılır: ASCII ve küçük harf.

    Şapkalı ya da büyük harfli yazılan bir veto HİÇBİR ZAMAN eşleşmez ve
    bu sessiz bir hatadır — kural çalışıyor görünür, hiçbir şey elemez.
    """
    for kural in KURALLAR:
        for ifade in kural.veto_ifadeleri:
            assert ifade == ifade.lower(), f"{kural.alan}: {ifade!r} küçük harf değil"
            assert not (set(ifade) & set("ıİşŞğĞüÜöÖçÇâîû")), (
                f"{kural.alan}: {ifade!r} ASCII'ye indirilmemiş"
            )


def test_dislayici_ve_baglam_sozcukleri_de_normalize():
    """Aynı sessiz hata bağlam ve dışlayıcı sözcükler için de geçerli."""
    for kural in KURALLAR:
        for ifade in kural.baglam_sozcukleri + kural.dislayici_sozcukler:
            assert ifade == ifade.lower()
            assert not (set(ifade) & set("ıİşŞğĞüÜöÖçÇâîû"))


# ---------------------------------------------------------------------------
# Ay adları tek kaynaktan
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ay", AYLAR)
def test_her_ay_tarih_deseniyle_eslesir(ay: str):
    """`AYLAR` ile `D_TARIH` ayrı yazılsaydı biri eksik kalabilirdi."""
    assert D_TARIH.search(f"31 {ay} 2026")


@pytest.mark.parametrize("ay", AYLAR)
def test_her_ay_aralik_denetimlerinde_taninir(ay: str):
    """Aralık denetimleri de aynı kaynaktan türer — üç regex, tek liste."""
    metin = f"1 Ocak 2026 - 31 {ay} 2026"
    ikinci = metin.index(f"31 {ay}")
    assert _tarih_araligi_sonu_mu(metin, ikinci)


def test_aralik_basi_ve_sonu_birbirini_dislar():
    """Bir tarih aynı anda hem başlangıç hem bitiş olamaz."""
    metin = "Kampanya Dönemi: 2 Temmuz 2026 - 31 Aralık 2026"
    bas = metin.index("2 Temmuz 2026")
    son = metin.index("31 Aralık 2026")

    assert _tarih_araligi_basi_mu(metin, bas + len("2 Temmuz 2026"))
    assert not _tarih_araligi_sonu_mu(metin, bas)

    assert _tarih_araligi_sonu_mu(metin, son)
    assert not _tarih_araligi_basi_mu(metin, son + len("31 Aralık 2026"))


# ---------------------------------------------------------------------------
# Kural tablosunun genel sağlığı
# ---------------------------------------------------------------------------


def test_ortak_vetolar_derlemde_birden_cok_kayitta_gecer():
    """Tek kayıtta geçen veto, örüntü değil O KAYDIN EZBERİDİR.

    Bu testin varlık sebebi metodolojik: veto ifadeleri altın setin
    hatalarına bakılarak yazılıyor, yani aynı 60 örnek hem geliştirme hem
    ölçüm kümesi. Tek örneğe uydurulan bir ifade ölçümü şişirir ve
    görülmemiş metinde hiçbir işe yaramaz.

    16 Ağustos taraması dört böyle ifade buldu; ikisi derlemde HİÇ
    geçmiyordu (`ornek hesaplama`, `vergi kesil` — ikincisi "gelir vergiSİ
    kesilmesini" metnine bitişik eşleşmiyordu, yani hiç çalışmamıştı).
    Dördü de kaldırıldı, ölçüm değişmedi.

    Ağ gerektirmez: yerel veritabanı yoksa test atlanır.
    """
    try:
        from src.depolama import tum_kayitlar

        kayitlar = tum_kayitlar()
    except Exception:  # pragma: no cover - veritabanı yoksa
        pytest.skip("yerel veritabanı yok")

    if len(kayitlar) < 20:
        pytest.skip("derlem bu denetim için çok küçük")

    metinler = [arama_anahtari(k.ham_metin) for k in kayitlar]
    zayif = {
        ifade: sum(1 for m in metinler if ifade in m)
        for ifade in SAYISAL_ALAN_VETOLARI
    }
    tekil = {i: n for i, n in zayif.items() if n < 2}
    assert not tekil, f"derlemde 2'den az kayıtta geçen ortak veto: {tekil}"


def test_her_kural_baglam_sozcugu_tasir():
    """Bağlamsız kural, metindeki her sayıyı o alana yazar."""
    for kural in KURALLAR:
        assert kural.baglam_sozcukleri, f"{kural.alan} bağlam sözcüğü olmadan tanımlı"


def test_alan_adlari_tekil():
    """Aynı alan için iki kural olsaydı `_ALAN_KURALI` sessizce birini yutardı."""
    adlar = [k.alan for k in KURALLAR]
    assert len(adlar) == len(set(adlar))


def test_gecerli_aralik_tutarli():
    """Alt sınır üst sınırdan küçük olmalı — ters aralık her şeyi eler."""
    for kural in KURALLAR:
        if kural.gecerli_aralik is None:
            continue
        alt, ust = kural.gecerli_aralik
        assert alt < ust, f"{kural.alan}: ters aralık ({alt}, {ust})"


def test_desenler_derlenebilir():
    for kural in KURALLAR:
        assert isinstance(kural.deger_deseni, re.Pattern)
