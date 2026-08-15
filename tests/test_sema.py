"""Donmuş şema sözleşmesinin testleri.

`src/schema.py` dört kişinin ortak sözleşmesidir ve altın set ona karşı
etiketlenmiştir. Buradaki testler şemanın GENİŞLETİLEBİLİR ama BOZULAMAZ
olduğunu koruma altına alır:

  - `ALAN_ADLARI` çıkarılan alanların listesidir ve metriklerin, altın set
    CSV başlıklarının, doluluk hesabının ortak kaynağıdır.
  - Bu listeye sessizce bir alan eklemek, etiketlenmiş altın setle üretilen
    kayıtları hizasız bırakır: `make eval` yanlış sütunu karşılaştırır ve
    doğruluk sayıları sessizce anlamını yitirir.

v1.1.0'da `uygunluk` alanı tam da bu yüzden `Alan` tipinde DEĞİL.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.schema import (
    ALAN_ADLARI,
    Alan,
    HedefKitle,
    Kampanya,
    UygunlukKosullari,
)
from tools.altin_set import CEKIRDEK_ALANLAR, csv_basliklari

# v1.0.0'da dondurulan on altı alan. Bu demet DEĞİŞMEMELİ; değişmesi
# gerekiyorsa docs/kararlar/ altına ADR yazılır ve altın set yeniden
# etiketlenir (bkz. CLAUDE.md "Değiştirmeden önce bilinmesi gerekenler").
DONMUS_ALANLAR = (
    "kampanya_turu",
    "urun_turu",
    "hedef_kitle",
    "kar_payi_orani",
    "finansman_tutari_max",
    "vade_ay_max",
    "taksit_sayisi",
    "tahsis_ucreti",
    "masraf_bilgisi",
    "masrafsiz_mi",
    "odul_miktari",
    "indirim_orani",
    "alisveris_puani",
    "kampanya_avantaji",
    "kampanya_bitis",
    "kampanya_kosullari",
)


def _kampanya(**ek) -> Kampanya:
    return Kampanya(
        banka_adi="Test Katılım Bankası A.Ş.",
        banka_kodu="0299",
        kampanya_id="0299-test",
        kaynak_url="https://ornek.test/kampanya",
        cekim_tarihi=datetime(2026, 8, 14, 12, 0),
        ham_metin="kampanya metni",
        **ek,
    )


# ---------------------------------------------------------------------------
# Donmuş sözleşme
# ---------------------------------------------------------------------------


def test_alan_adlari_donmus_listeyle_ayni():
    assert ALAN_ADLARI == DONMUS_ALANLAR


def test_altin_set_basliklari_semanin_alt_kumesi():
    """Altın set sekiz alanı soruyor (ADR 008), on altısını değil.

    Sorulan her sütun yine de ŞEMADA tanımlı bir alan olmalı — uydurma bir
    sütun adı sessizce metriğin dışında kalır, hiçbir yere bağlanmaz.
    """
    basliklar = csv_basliklari()
    etiket_sutunlari = set(basliklar) - {"kampanya_id", "banka_adi", "kaynak_url", "metin"}
    assert etiket_sutunlari <= set(ALAN_ADLARI)
    assert etiket_sutunlari == set(CEKIRDEK_ALANLAR)


# ---------------------------------------------------------------------------
# v1.1.0 — `uygunluk` genişletmesi sözleşmeyi bozmuyor
# ---------------------------------------------------------------------------


def test_uygunluk_cikarilan_alan_sayilmaz():
    """`uygunluk` bir `Alan` değil; metriklerin ve altın setin dışında kalmalı."""
    assert "uygunluk" not in ALAN_ADLARI
    assert "uygunluk" not in csv_basliklari()
    assert "uygunluk" not in _kampanya().cikarilan_alanlar()


def test_uygunluk_doluluk_ve_guveni_etkilemez():
    """Aynı çıkarım, uygunluk dolu ya da boş olsun, aynı metriği vermeli —
    yoksa v1.1.0 öncesi ve sonrası ölçümler karşılaştırılamaz olurdu."""
    alanlar = {"kar_payi_orani": Alan(deger=2.05, ham_ifade="%2,05", guven=0.9, yontem="kural")}
    yalin = _kampanya(**alanlar)
    zengin = _kampanya(
        **alanlar,
        uygunluk=UygunlukKosullari(
            musteri_tipi=[HedefKitle.MAAS_MUSTERISI], min_tutar=100_000.0
        ),
    )
    assert yalin.doluluk_orani() == zengin.doluluk_orani()
    assert yalin.ortalama_guven() == zengin.ortalama_guven()
    assert yalin.kanit_denetimi() == zengin.kanit_denetimi()


def test_uygunluksuz_kayit_hala_gecerli():
    """Eski kayıtlar (uygunluk çıkarılmadan önce) okunabilir kalmalı."""
    assert _kampanya().uygunluk is None


# ---------------------------------------------------------------------------
# UygunlukKosullari davranışı
# ---------------------------------------------------------------------------


def test_ters_tutar_araligi_reddedilir():
    """Ters aralık her kampanyayı sessizce elerdi; erken patlaması iyidir."""
    with pytest.raises(ValueError, match="min_tutar"):
        UygunlukKosullari(min_tutar=500_000.0, max_tutar=100_000.0)


def test_ters_vade_araligi_reddedilir():
    with pytest.raises(ValueError, match="min_vade_ay"):
        UygunlukKosullari(min_vade_ay=120, max_vade_ay=36)


def test_kisitsiz_kosul_herkese_acik_sayilir():
    assert UygunlukKosullari().kisit_var_mi() is False
    assert UygunlukKosullari(ek_sartlar=["şubeye başvuru"]).kisit_var_mi() is False


@pytest.mark.parametrize(
    "kosul",
    [
        UygunlukKosullari(musteri_tipi=[HedefKitle.YENI_MUSTERI]),
        UygunlukKosullari(min_tutar=50_000.0),
        UygunlukKosullari(max_vade_ay=36),
        UygunlukKosullari(zorunlu_urun=["maaş hesabı"]),
    ],
)
def test_kisitli_kosul_taninir(kosul):
    assert kosul.kisit_var_mi() is True


def test_musteri_tipi_hedef_kitle_sozlugunu_kullanir():
    """Aynı kavram için ikinci bir sözcük dağarcığı tanımlanmadı — çıkarım ile
    muhakemenin ayrışmaması buna bağlı."""
    kosul = UygunlukKosullari(musteri_tipi=[HedefKitle.MAAS_MUSTERISI])
    assert kosul.musteri_tipi == [HedefKitle.MAAS_MUSTERISI]
    with pytest.raises(ValueError):
        UygunlukKosullari(musteri_tipi=["maas"])  # enum dışı ham metin
