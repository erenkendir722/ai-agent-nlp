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

    Genel_Bakış.py halüsinasyon oranını `tr_sayi(oran * 100, 2)` ile çiziyor.
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


# ---------------------------------------------------------------------------
# Serbest metin → Word belgesi
# ---------------------------------------------------------------------------
#
# Satış notu bir TABLO DEĞİL, bir metindir. Bir süre tek hücreli bir CSV
# olarak iniyordu: Word'de açıldığında başlıksız, satırsız, tek bir dev
# hücreydi ve kimsenin işine yaramıyordu. Aşağısı, indirilen belgenin
# gerçekten biçimlenmiş olduğunu tutuyor.


def test_serbest_metin_baslik_ve_madde_uretir():
    """Markdown başlığı `<h3>`, madde `<li>` olmalı."""
    from app.ui_utils import _serbest_metin_html

    html_cikti = _serbest_metin_html("## Güçlü Yönlerimiz\n- 120 ay vade\n- Masrafsız")

    assert "<h3>Güçlü Yönlerimiz</h3>" in html_cikti
    assert html_cikti.count("<li>") == 2
    assert "<ul>" in html_cikti and "</ul>" in html_cikti


def test_numarali_satir_baslik_mi_madde_mi():
    """Kısa ve noktasız numaralı satır BAŞLIK, cümle olan MADDE değil paragraf.

    Dil modeli bazen `## Başlık` yerine `1. Başlık` yazıyor. İkisini de
    başlık saymak «1. Vade 120 aya çıkarılabilir.» gibi bir cümleyi de
    başlığa çevirirdi — ayrım uzunluk ve noktalama.
    """
    from app.ui_utils import _serbest_metin_html

    assert "<h3>Görüşmede Ne Söylenmeli</h3>" in _serbest_metin_html(
        "1. Görüşmede Ne Söylenmeli"
    )
    cumle = _serbest_metin_html("1. Vade 120 aya çıkarılabilir.")
    assert "<h3>" not in cumle, "cümle başlığa çevrildi"


def test_metin_html_kacirilir_sonra_kalinlastirilir():
    """Kullanıcı metnindeki `<` kaçırılmalı, bizim `<b>`imiz kaçırılmamalı.

    Ters sıra bir enjeksiyon yolu açardı: indirilen belge Word'de açılıyor
    ama aynı üretici bir gün tarayıcıya basılırsa metindeki etiket çalışırdı.
    """
    from app.ui_utils import _serbest_metin_html

    cikti = _serbest_metin_html("**kalın** ve <script>alert(1)</script>")

    assert "<b>kalın</b>" in cikti
    assert "<script>" not in cikti
    assert "&lt;script&gt;" in cikti


def test_satis_notu_word_belgesi_bicim_tasir():
    """Belge başlık bloğu, gövde ve dipnot taşımalı — düz metin yığını değil."""
    from app.ui_utils import _BELGE_BICIMI, _serbest_metin_html

    assert "@page" in _BELGE_BICIMI, "sayfa kenar boşluğu tanımlı değil"
    assert "Calibri" in _BELGE_BICIMI, "Word'ün tanıdığı bir yazı tipi yok"
    # Gövde çeviricisi belge üreticisiyle aynı yerden gelmeli.
    assert _serbest_metin_html("## X").startswith("<h3>")


# ---------------------------------------------------------------------------
# Tablo → Word belgesi: SAYFAYA SIĞMALI
# ---------------------------------------------------------------------------
#
# Tablo `df.to_html()` ile olduğu gibi gömülüyordu, yani sayfa genişliği hiç
# hesaba katılmıyordu. Word varsayılan dikey A4 açar; on sütunluk
# karşılaştırma tablosu ve içindeki tam kaynak adresleri sayfanın dışına
# taşıyordu — indirilen belge okunmuyordu.


def _cerceve(sutun_sayisi: int, url_ekle: bool = False):
    import pandas as pd

    satir = {f"S{i}": f"kısa{i}" for i in range(sutun_sayisi - (1 if url_ekle else 0))}
    if url_ekle:
        satir["Kaynak URL"] = "https://www.ornekbanka.com.tr/" + "uzun-adres-" * 6
    return pd.DataFrame([satir])


def test_genis_tablo_yatay_sayfaya_doner():
    """Beş sütunu aşan tablo yatay A4 istemeli."""
    from app.ui_utils import _word_bayt

    dar = _word_bayt(_cerceve(4), "dar").decode()
    genis = _word_bayt(_cerceve(10), "geniş").decode()

    assert "landscape" not in dar, "dört sütun için yatay sayfa gereksiz"
    assert "landscape" in genis, "on sütunluk tablo dikey sayfaya sığmaz"
    # `size` tek başına Word'de yön değiştirmiyor.
    assert "mso-page-orientation" in genis, "Word'ün yön özelliği yok"


def test_tablo_sayfaya_uyar_satir_tasmaz():
    """Tablo sayfaya uymalı; uzun adres hücreyi dışarı itmemeli."""
    from app.ui_utils import _word_bayt

    belge = _word_bayt(_cerceve(6, url_ekle=True), "kaynaklı").decode()

    assert "table-layout: fixed" in belge, (
        "tablo en uzun hücreye göre genişler — tek URL tabloyu dışarı iter"
    )
    assert "width: 100%" in belge, "tablo sayfa genişliğine oturmuyor"
    assert "overflow-wrap: anywhere" in belge, (
        "adres boşluk taşımaz; bölünecek yer bulamazsa hücreyi zorlar"
    )


def test_sutun_genisligi_icerikten_turer():
    """Uzun adres sütunu, kısa sayı sütunundan geniş olmalı."""
    import re

    from app.ui_utils import _word_bayt

    belge = _word_bayt(_cerceve(6, url_ekle=True), "kaynaklı").decode()
    genislikler = [float(g) for g in re.findall(r"width:([\d.]+)%", belge)]

    assert len(genislikler) == 6, "her sütuna genişlik verilmemiş"
    assert abs(sum(genislikler) - 100) < 1.5, f"toplam %100 değil: {sum(genislikler)}"
    # URL son sütun; kısa sütunların hepsinden geniş olmalı.
    assert genislikler[-1] > max(genislikler[:-1]), (
        "eşit bölüşüm: adres dar sütuna sıkışıp onlarca satıra sarılır"
    )
    # Ama tabloyu da yutmamalı.
    assert genislikler[-1] < 60, "tek sütun tabloyu yuttu"
