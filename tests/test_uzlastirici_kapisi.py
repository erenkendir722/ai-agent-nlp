"""Uzlaştırmadan sonraki ALAN MAKULLÜĞÜ kapısı.

NEDEN BU TESTLER VAR — 16 Ağustos'ta bulunan sızıntı:
    Makullük sınırı, aralık-ucu denetimi ve veto ifadeleri `KuralTanimi`
    üzerindeydi, yani yalnız kural katmanına uygulanıyordu. Uzlaştırıcı ise
    kural susunca LLM değerini doğrudan geçiriyordu:

        if kural is None and llm is not None:
            return llm

    Sonuç: kural katmanına yazılan her eleme, hatayı ÖNLEMEK yerine
    KAYNAĞINI DEĞİŞTİRİYORDU. Ölçülmüş örnek — altın sette `finansman_
    tutari_max` için `sistem=66066.24 yontem=llm`, ham ifade "66.066,24 TL",
    kaynağı bir "Geri Ödenecek Toplam Tutar" satırı.

    Buradaki testler kapının hangi katmandan gelirse gelsin çalıştığını
    ve konumsuz değerleri yanlışlıkla elemediğini kanıtlar.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.extraction.kural import kurallarla_cikar
from src.extraction.uzlastirici import uzlastir
from src.schema import Alan, HamKayit, Kaynak

CEKIM = datetime(2026, 8, 16, 12, 0)

HESAP_MAKINESI = (
    "Konut finansmanı başvurunuzu hemen yapın. % Oranı kendim gireceğim. "
    "Aylık Taksit Tutarı 11.349,76 TL Geri Ödenecek Toplam Tutar 261.044,84 TL "
    "Yıllık Maliyet Oranı % 84,93 Ücretler Toplamı 750,00"
)


def _kayit(metin: str) -> HamKayit:
    return HamKayit(
        banka_kodu="0299",
        banka_adi="Test Katılım Bankası A.Ş.",
        url="https://ornek.test/kampanya",
        cekim_tarihi=CEKIM,
        http_durum=200,
        govde_metin=metin,
    )


def _llm_alani(deger: float, ham: str, metin: str) -> Alan:
    """Metinde gerçekten geçen, konumu doğrulanmış bir LLM değeri."""
    bas = metin.index(ham)
    return Alan(
        deger=deger,
        ham_ifade=ham,
        kaynak=Kaynak(
            url="https://ornek.test/kampanya",
            cekim_tarihi=CEKIM,
            alinti=ham,
            karakter_baslangic=bas,
            karakter_bitis=bas + len(ham),
        ),
        guven=0.75,
        yontem="llm",
    )


def test_kural_susunca_llm_degeri_filtresiz_gecmez() -> None:
    """Sızıntının ta kendisi: kural eledi, LLM aynı sayıyı içeri sokuyordu."""
    kayit = _kayit(HESAP_MAKINESI)
    llm = {"finansman_tutari_max": _llm_alani(261044.84, "261.044,84 TL", HESAP_MAKINESI)}

    kampanya, rapor = uzlastir({}, llm, kayit=kayit)

    assert kampanya.finansman_tutari_max.var_mi is False
    assert rapor.elenen_alan_sayisi == 1


def test_dilim_tablosundan_gelen_llm_degeri_elenir() -> None:
    """Aralık-ucu denetimi de artık LLM yolunda çalışıyor."""
    metin = (
        "Nihai fatura bedeli 1.200.001 TL – 2.000.000 TL aralığında olan taşıt "
        "finansmanlarında en fazla 12 ay vade uygulanır."
    )
    kayit = _kayit(metin)
    llm = {"finansman_tutari_max": _llm_alani(2_000_000.0, "2.000.000 TL", metin)}

    kampanya, _ = uzlastir({}, llm, kayit=kayit)

    assert kampanya.finansman_tutari_max.var_mi is False


def test_makul_deger_gecer() -> None:
    """Kapı yalnız hatalıyı elemeli — asıl risk doğruyu elemek."""
    metin = "Kurumsal müşterilerimize 150.000.000 TL'ye varan proje finansmanı sağlanır."
    kayit = _kayit(metin)
    llm = {"finansman_tutari_max": _llm_alani(150_000_000.0, "150.000.000 TL", metin)}

    kampanya, rapor = uzlastir({}, llm, kayit=kayit)

    assert kampanya.finansman_tutari_max.deger == pytest.approx(150_000_000.0)
    assert rapor.elenen_alan_sayisi == 0


def test_konumsuz_deger_elenmez() -> None:
    """Enum ve cümleden türeyen alanlar konum taşımaz; kapı onlara uygulanmaz.

    `karakter_baslangic == karakter_bitis` LLM katmanının kanıtsız kaynak
    biçimidir; oradan pencere çıkarmak metnin başını denetlemek olurdu.
    """
    kayit = _kayit(HESAP_MAKINESI)
    konumsuz = Alan(
        deger=500_000.0,
        ham_ifade="500.000 TL",
        kaynak=Kaynak(
            url="https://ornek.test/kampanya",
            cekim_tarihi=CEKIM,
            alinti="",
            karakter_baslangic=0,
            karakter_bitis=0,
        ),
        guven=0.6,
        yontem="llm",
    )

    kampanya, rapor = uzlastir({}, {"finansman_tutari_max": konumsuz}, kayit=kayit)

    assert kampanya.finansman_tutari_max.var_mi is True
    assert rapor.elenen_alan_sayisi == 0


def test_kaynaksiz_alan_kapiyi_dusurmez() -> None:
    """`kaynak=None` (masrafsiz_mi'nin LLM biçimi) çökmeye yol açmamalı."""
    kayit = _kayit(HESAP_MAKINESI)
    kaynaksiz = Alan(
        deger=True, ham_ifade="masraf yok", kaynak=None, guven=0.65, yontem="llm"
    )

    kampanya, _ = uzlastir({}, {"masrafsiz_mi": kaynaksiz}, kayit=kayit)

    assert kampanya.masrafsiz_mi.deger is True


DILIM_TABLOSU = (
    "Taşıt Finansmanı Kampanyası. Nihai fatura bedeline göre azami finansman "
    "oranları:\n"
    "| Nihai Fatura Bedeli | Finansman Oranı | Azami Vade |\n"
    "|---|---|---|\n"
    "| 0 TL - 400.000 TL | 70% | 48 |\n"
    "| 400.000 - 800.000 TL | 50% | 36 |\n"
    "| 800.000 - 1.200.000 TL | 30% | 24 |\n"
    "| 1.200.001 - 2.000.000 TL | 20% | 12 |\n"
)


def test_dilim_degeri_CELISKIDE_de_korunur() -> None:
    """Dilim baypası çelişkiyi de kapsar — 26 Ağustos'ta ölçülen kayıp.

    Baypas önce yalnız `durum == "kural"` için açıktı. LLM tablonun TEPESİNİ
    (2.000.000) kapınca durum "celiski" oluyor, baypas kapanıyor ve makullük
    kapısı kuralın doğru cevabını (800.000 × %50 = 400.000) eliyordu. Altın
    setin dört taşıt kaydında ölçüldü: `SONUÇ None`, `elenen=1`.

    `finansman_tutari_max` sayısal bir alan olduğu için `_birlestir` çelişkide
    zaten kuralı kazandırıyor — yani elenen değer, tek başına gelseydi geçecek
    olan değerin ta kendisiydi. Ayrım değerin kaynağına değil, rakibinin olup
    olmadığına bakıyordu.
    """
    kayit = _kayit(DILIM_TABLOSU)
    kural = kurallarla_cikar(DILIM_TABLOSU, kayit.url, CEKIM)
    assert kural["finansman_tutari_max"].deger == pytest.approx(400_000.0), (
        "ön koşul: kural katmanı dilim hesabını üretmeli"
    )

    llm = {"finansman_tutari_max": _llm_alani(2_000_000.0, "2.000.000 TL", DILIM_TABLOSU)}
    kampanya, _ = uzlastir(kural, llm, kayit=kayit)

    assert kampanya.finansman_tutari_max.deger == pytest.approx(400_000.0)


def test_dilim_baypasi_llm_uydurmasini_gecirmez() -> None:
    """Baypas genişledi ama kapıyı `dilim_turevi_mi` tutuyor.

    Kural susmuşken LLM'in tablodan kaptığı değer hâlâ elenmeli — genişletme
    bir delik açmamalı.
    """
    kayit = _kayit(DILIM_TABLOSU)
    llm = {"finansman_tutari_max": _llm_alani(2_000_000.0, "2.000.000 TL", DILIM_TABLOSU)}

    kampanya, _ = uzlastir({}, llm, kayit=kayit)

    assert kampanya.finansman_tutari_max.var_mi is False


BSMV_METNI = (
    "İhtiyaç Finansmanı Kampanyası. "
    "İhtiyaç Finansmanı tahsis ücreti finansman tutarının %0,5'idir. "
    "Tahsis ücreti %15 BSMV içermektedir."
)


def test_komsu_cumledeki_bsmv_dogru_orani_elemez() -> None:
    """Vergi vetosu KENDİ cümlesinde aranır — 26 Ağustos'ta ölçülen kayıp.

    `bsmv` ±140 karakterlik pencerede aranıyordu. Doğru değer (%0,5) bir
    önceki cümlede olduğu için o da eleniyordu; altın setin beş kaydında
    kural katmanı doğru cevabı üretip kapıda kaybediyordu.

    Veto kalkmadı, DARALDI: %15 hâlâ elenir (kendi cümlesinde `bsmv` geçer),
    %0,5 geçer.
    """
    kayit = _kayit(BSMV_METNI)
    kural = kurallarla_cikar(BSMV_METNI, kayit.url, CEKIM)

    kampanya, _ = uzlastir(kural, {}, kayit=kayit)

    assert kampanya.tahsis_ucreti.deger == pytest.approx(0.5)


def test_bsmv_orani_kendi_cumlesinde_hala_elenir() -> None:
    """Daraltma bir delik açmamalı: BSMV oranının kendisi tahsis ücreti değildir."""
    metin = "Kampanya koşulları geçerlidir. Tahsis ücreti %15 BSMV içermektedir."
    kayit = _kayit(metin)
    kural = kurallarla_cikar(metin, kayit.url, CEKIM)

    kampanya, _ = uzlastir(kural, {}, kayit=kayit)

    assert kampanya.tahsis_ucreti.var_mi is False


def test_binde_yazimi_tahsis_ucreti_olarak_okunur() -> None:
    """«binde 5» = %0,5 — işaretsiz oran yazımı.

    Üç ayrı yerde birden eksikti ve üçü de sessizdi: `D_ORAN` aday üretmiyor,
    üretilse `birim_belirle` birimi çözemiyor, çözülmezse çok birimli alanın
    boyut kapısı değeri düşürüyordu. Bankaların standart deyimi bu.
    """
    metin = "Tahsis ücreti vergiler hariç finansman tutarının binde 5'i oranındadır."
    kayit = _kayit(metin)
    kural = kurallarla_cikar(metin, kayit.url, CEKIM)

    kampanya, _ = uzlastir(kural, {}, kayit=kayit)

    assert kampanya.tahsis_ucreti.deger == pytest.approx(0.5)
    assert kampanya.tahsis_ucreti.birim is not None, "birimsiz değer boyut kapısında düşer"
