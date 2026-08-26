from pathlib import Path

import pytest

from app.ui_utils import format_bank_name, sonuclari_oku, tr_sayi
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


# ---------------------------------------------------------------------------
# Ölçüm birimi sözleşmesi — 26 Ağustos'ta jüri provasında yakalanan hata
# ---------------------------------------------------------------------------
#
# `eval/calistir.py` halüsinasyon oranını ORAN üretir (0,0045) ve markdown
# tablosuna yazarken 100'le çarpar ("%0.45"). `sonuclari_oku` o yüzdeyi geri
# okuyor; oranla aynı ada koyup bölmeyi unutunca Genel Bakış ekranı ikinci kez
# çarpıyordu ve "≤ %3 hedef" rozetinin yanında **%45,00** yazıyordu.


def _sahte_sonuclar(tmp_path, yuzde: str) -> Path:
    dosya = tmp_path / "SONUCLAR.md"
    dosya.write_text(
        "| Metrik | Değer | Hedef | Durum |\n"
        "|---|---|---|---|\n"
        "| Şema geçerliliği | 1.00 | 1,00 | ✅ |\n"
        f"| **Halüsinasyon oranı** | %{yuzde} | ≤ %3 | ✅ |\n",
        encoding="utf-8",
    )
    return dosya


def test_halusinasyon_orani_oran_birimindedir(tmp_path):
    """Tabloda "%0.45" yazıyorsa alan 0,0045 tutar — yüzde değil, oran."""
    ozet = sonuclari_oku(_sahte_sonuclar(tmp_path, "0.45"))
    assert ozet.halusinasyon_orani == pytest.approx(0.0045)
    assert ozet.sema_gecerliligi == pytest.approx(1.0)


@pytest.mark.parametrize("yuzde", ["0.45", "0.00", "2.50", "3.00", "12.75"])
def test_ekranda_gorunen_sayi_sonuclar_dosyasiyla_ayni(tmp_path, yuzde):
    """Çift çevrimi yakalayan asıl kapı: ekrandaki dize = dosyadaki dize.

    Genel_Bakis.py halüsinasyon oranını `tr_sayi(oran * 100, 2)` ile çiziyor.
    Bölme geri alınırsa bu eşitlik bozulur ve test kırmızıya döner.
    """
    ozet = sonuclari_oku(_sahte_sonuclar(tmp_path, yuzde))
    ekranda = tr_sayi(ozet.halusinasyon_orani * 100, 2)
    assert ekranda == f"{float(yuzde):.2f}".replace(".", ",")


def test_halusinasyon_orani_esik_altinda_kalir(tmp_path):
    """Şartname hedefi ≤ %3. Birim kayarsa hedef sessizce aşılmış görünür."""
    ozet = sonuclari_oku(_sahte_sonuclar(tmp_path, "0.45"))
    assert ozet.halusinasyon_orani <= 0.03


def test_sonuc_dosyasi_yoksa_bos_ozet(tmp_path):
    """`make eval` hiç koşmamışsa ekran çökmez, "—" gösterir."""
    ozet = sonuclari_oku(tmp_path / "yok.md")
    assert ozet.halusinasyon_orani is None
    assert ozet.makro_f1 is None


def test_gercek_sonuclar_dosyasi_makul_aralikta():
    """Depodaki gerçek ölçüm dosyası da sözleşmeye uymalı."""
    ozet = sonuclari_oku()
    if ozet.halusinasyon_orani is not None:
        assert 0.0 <= ozet.halusinasyon_orani <= 0.03, (
            "docs/SONUCLAR.md'deki halüsinasyon oranı ya hedefi aştı ya da "
            "birim kaydı (oran bekleniyor, yüzde değil)."
        )
