"""27 Ağustos arayüz incelemesinde düzeltilen maddelerin nöbetçisi.

Buradaki üç şey SESSİZCE geri gelebilir: hepsi «çalışmayan kod» değil,
«kullanıcıya bir şey anlatmayan ekran». Test yoksa kimse fark etmez.
"""

from __future__ import annotations

import re
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
APP = KOK / "app"
GENEL_BAKIS = APP / "Genel_Bakış.py"
KARSILASTIRMA = APP / "pages" / "1_Karşılaştırma.py"


def test_ust_gostergelerin_hepsi_kendini_acikliyor() -> None:
    """Her `st.metric` bir `help=` taşımalı.

    «Ortalama güven 0,79» bir jüri üyesine hiçbir şey söylemez: neyin
    ortalaması, neye göre güven? Sistemin en özgün iddiası şeffaflık olduğu
    için, ölçünün kendisinin açık olmaması iddiayı zayıflatır.
    """
    metin = GENEL_BAKIS.read_text(encoding="utf-8")
    bas = metin.index("s1, s2, s3, s4, s5 = st.columns(5)")
    son = metin.index("son = ozet[", bas)
    bolge = metin[bas:son]

    cagrilar = re.findall(r"s\d\.metric\((.*?)\n\)", bolge, flags=re.S)
    assert len(cagrilar) == 5, f"beş üst gösterge bekleniyordu, {len(cagrilar)} bulundu"
    for cagri in cagrilar:
        etiket = re.search(r'"([^"]+)"', cagri)
        assert "help=" in cagri, (
            f"«{etiket.group(1) if etiket else cagri[:30]}» ölçüsünde açıklama yok — "
            "kullanıcı bu sayının nasıl hesaplandığını göremez."
        )


def test_genel_bakis_kenar_menusunu_kopyalamiyor() -> None:
    """Genel Bakış sayfa adlarından bir menü BASMAMALI.

    Sol kenar çubuğu Streamlit'in kendi sayfa gezinmesidir ve altı sayfayı
    zaten listeler. Sayfanın içinde aynı listeyi ikinci kez basmak gezinmeyi
    kolaylaştırmaz — hangisinin doğru olduğunu sorgulatır.

    Aksiyon kartlarının hedef düğmeleri hariç: onlar bir menü değil, veriden
    hesaplanmış bir öneriye eşlik eden tek düğmedir. Sayı ile ayrılıyor —
    dörtten az sayfa düğmesi menü sayılmaz.
    """
    metin = GENEL_BAKIS.read_text(encoding="utf-8")
    sayfa_dugmeleri = re.findall(r'st\.switch_page\("pages/', metin)
    assert len(sayfa_dugmeleri) <= 3, (
        f"{len(sayfa_dugmeleri)} sayfa düğmesi var — kenar çubuğu menüsü "
        "yeniden kopyalanmış görünüyor."
    )


def test_karsilastirmada_kendi_bankam_secili_geliyor() -> None:
    """«Benim Bankam» boş başlamamalı.

    «(Seçilmedi)» ile açıldığında «Biz vs Onlar» bölümü hiç çizilmiyor ve
    ekranın yarısı boş duruyordu. Varsayılan ELLE YAZILMAZ — en çok kampanyası
    olan bankadan türer, yoksa korpus değişince yanlış bankayı gösterirdi.
    """
    metin = KARSILASTIRMA.read_text(encoding="utf-8")
    assert "_varsayilan = max(bankalar, key=" in metin, (
        "varsayılan banka veriden türetilmiyor"
    )
    assert "index=_secenekler.index(_varsayilan)" in metin, (
        "«Benim Bankam» seçim kutusu varsayılana konumlanmıyor — "
        "«(Seçilmedi)» ile açılır ve ekranın yarısı boş kalır."
    )
