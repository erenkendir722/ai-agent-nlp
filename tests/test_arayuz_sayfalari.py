"""Streamlit sayfaları gerçekten çiziliyor mu — 26 Ağustos'ta açılan boşluk.

NEDEN VAR:
    `tests/test_ui_utils.py` yalnız saf yardımcı fonksiyonları sınıyordu;
    hiçbir test bir SAYFAYI çizmiyordu. Bu boşluktan sayfayı komple bozan bir
    hata geçti:

        app/pages/2_Chatbot.py
        st.dataframe(..., width="stretch")
        TypeError: 'str' object cannot be interpreted as an integer

    `width="stretch"` Streamlit 1.44 API'sidir; `requirements.txt` 1.40.1'e
    pinli ve orada `width` int bekler. Hata ajan izleri panelinde, yani
    CEVAP EKRANA BASILDIKTAN SONRA oluşuyordu: kullanıcı cevabı görüyor,
    altında kırmızı istisna kutusu görüyor ve `st.session_state.gecmis`e
    ekleme satırına hiç gelinmediği için sohbet geçmişi kayboluyordu.
    Dışarıdan bakınca «chatbot yazdığıma cevap vermiyor» gibi görünüyordu.

    Sayfa yüklemesi tek başına yetmez — hata ancak SORU SORULUNCA çıkıyor.
    Bu yüzden aşağıdaki test soruyu da soruyor.

AĞ KULLANMAZ:
    Seçilen soru karşılaştırma niyetine düşer; karşılaştırma tamamen yapısal
    SQLite sorgusu + deterministik skorlamadır. Koşul sorgusu (RAG) seçilseydi
    sorgunun kendisi gömülecekti ve test ağa bağımlı hâle gelirdi.
"""

from __future__ import annotations

from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
SAYFALAR = [
    KOK / "app" / "Genel_Bakis.py",
    KOK / "app" / "pages" / "0_Müşteri_Profili.py",
    KOK / "app" / "pages" / "1_Karşılaştırma.py",
    KOK / "app" / "pages" / "2_Chatbot.py",
    KOK / "app" / "pages" / "3_Metin_Analizi.py",
]

# Yapısal yoldan cevaplanır: iki banka adı geçtiği için karşılaştırma niyeti,
# karşılaştırma da ağ kullanmaz.
YAPISAL_SORU = "Ziraat Katılım ile Vakıf Katılım'ı karşılaştır"


def _veri_var_mi() -> bool:
    try:
        from src.depolama import tum_kayitlar

        return len(tum_kayitlar()) >= 2
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _veri_var_mi(),
    reason="veritabanı boş ya da erişilemiyor — önce `make extract`",
)


def _kos(yol: Path, zaman_asimi: int = 300):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(yol), default_timeout=zaman_asimi)
    at.run()
    return at


def _istisna_yok(at, baglam: str) -> None:
    assert not at.exception, (
        f"{baglam} istisna firlatti: "
        + " | ".join(str(e.value)[:200] for e in at.exception)
    )


@pytest.mark.parametrize("yol", SAYFALAR, ids=lambda y: y.name)
def test_sayfa_istisnasiz_yuklenir(yol: Path) -> None:
    _istisna_yok(_kos(yol), yol.name)


def test_chatbot_manuel_soruya_istisnasiz_cevap_verir() -> None:
    """Asıl regresyon: `chat_input`a yazılan soru sayfayı bozmamalı.

    Sayfanın yalnız açılması bu hatayı YAKALAMAZ; istisna cevap çizilirken
    oluşuyor.
    """
    at = _kos(KOK / "app" / "pages" / "2_Chatbot.py")
    assert at.chat_input, "chat_input yok — manuel giriş hiç mümkün değil"

    at.chat_input[0].set_value(YAPISAL_SORU).run()
    _istisna_yok(at, "chatbot manuel soru")


def test_chatbot_manuel_soru_cevap_ve_ajan_izi_cizer() -> None:
    """Cevap metni VE ajan izleri tablosu ekrana gelmeli.

    İstisna yokluğu yetmez: hata `st.dataframe` çağrısındaydı, yani panel
    çizilmiyordu. Tablonun varlığını ölçmezsek aynı hata sessizce dönebilir.
    """
    at = _kos(KOK / "app" / "pages" / "2_Chatbot.py")
    at.chat_input[0].set_value(YAPISAL_SORU).run()

    _istisna_yok(at, "chatbot manuel soru")
    assert at.dataframe, "ajan izleri tablosu çizilmedi"

    metinler = " ".join(m.value for m in at.markdown)
    assert "Katılım" in metinler, "cevapta hiçbir banka adı geçmiyor"


def test_chatbot_ornek_soru_dugmesi_calisir() -> None:
    """Kenar çubuğundaki hazır sorular da aynı kod yolundan geçer."""
    at = _kos(KOK / "app" / "pages" / "2_Chatbot.py")
    assert at.button, "örnek soru düğmesi yok"

    at.button[0].click().run()
    _istisna_yok(at, "chatbot örnek soru düğmesi")
