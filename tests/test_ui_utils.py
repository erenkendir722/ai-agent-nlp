import pytest
from app.ui_utils import format_bank_name

def test_format_bank_name_known_dict():
    """Sözlükteki (Dictionary) bankaların doğru kısaltıldığını test eder."""
    assert format_bank_name("T.O.M. Katılım Bankası A.Ş.") == "TOM Katılım"
    assert format_bank_name("Kuveyt Türk Katılım Bankası A.Ş.") == "Kuveyt Türk"
    assert format_bank_name("Albaraka Türk Katılım Bankası A.Ş.") == "Albaraka Türk"

def test_format_bank_name_unknown_fallback():
    """Sözlükte olmayan bankalar için agresif temizlik ve kırpma (fallback) test eder."""
    # 15 karakterden kısa, A.Ş. olan bir test
    assert format_bank_name("X Bankası A.Ş.") == "X"
    assert format_bank_name("Çok Çok Uzun Bir Banka Katılım A.Ş.") == "Çok Çok Uzun Bi..."
    
def test_format_bank_name_empty():
    """Boş değerlerin 'Belirtilmemiş' döndürdüğünü test eder."""
    assert format_bank_name(None) == "Belirtilmemiş"
    assert format_bank_name("") == "Belirtilmemiş"
