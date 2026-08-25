from app.ui_utils import format_bank_name
from src.collector.toplayici import bankalari_yukle


def test_format_bank_name_kayit_defterinden():
    """Kayıt defterindeki bankaların doğru kısaltıldığını test eder."""
    assert format_bank_name("T.O.M. Katılım Bankası A.Ş.") == "TOM Katılım"
    assert format_bank_name("Kuveyt Türk Katılım Bankası A.Ş.") == "Kuveyt Türk"
    assert format_bank_name("Albaraka Türk Katılım Bankası A.Ş.") == "Albaraka Türk"


def test_format_bank_name_tum_kayit_defteriyle_uyumlu():
    """Elle yazılan kopyanın kayıt defterinden ayrılmasını engelleyen sözleşme.

    16 Ağustos'ta ui_utils kendi sözlüğünü tutuyordu ve 15 bankanın 7'sinde
    `banks.yaml`'dan ayrılmıştı — "Türkiye Emlak Katılım Bankası A.Ş."
    sözlükte hiç eşleşmiyordu. Bu test o ayrışmayı bir daha bırakmaz.
    """
    for banka in bankalari_yukle():
        assert format_bank_name(banka.ad) == banka.kisa_ad, (
            f"{banka.ad} -> beklenen {banka.kisa_ad!r}"
        )


def test_format_bank_name_bilinmeyen_banka():
    """Kayıt defterinde olmayanlar için ek atma ve kırpma (fallback)."""
    assert format_bank_name("X Bankası A.Ş.") == "X"
    assert format_bank_name("Çok Çok Uzun Bir Banka Katılım A.Ş.") == "Çok Çok Uzun Bi..."


def test_format_bank_name_bos():
    """Boş değerlerin 'Belirtilmemiş' döndürdüğünü test eder."""
    assert format_bank_name(None) == "Belirtilmemiş"
    assert format_bank_name("") == "Belirtilmemiş"


def test_format_bank_name_ornek_uydurulmaz():
    """'Örnek' banka adı Albaraka'ya çevrilmez — jüriye sahte etiket gösterme."""
    assert format_bank_name("Örnek") != "Albaraka Türk"
    assert format_bank_name("ornek") != "Albaraka Türk"
