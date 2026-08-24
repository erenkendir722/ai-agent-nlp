"""Arayüz yardımcıları — grafik ve tablo etiketleri.

Banka kısa adları `data/banks.yaml`'daki `kisa_ad` alanından okunur. Burada
ikinci bir sözlük TUTULMAZ: elle yazılan kopya 16 Ağustos'ta kayıt defteriyle
yedi bankada ayrışmıştı ("Türkiye Emlak Katılım Bankası A.Ş." kayıt defterinde
"Emlak Katılım", kopyada hiç eşleşmiyordu). Kayıt defteri tek doğruluk kaynağı.
"""

from __future__ import annotations

from functools import lru_cache

import streamlit as st

from src.collector.toplayici import bankalari_yukle

# Kayıt defterinde olmayan bir banka için başlığı kısaltırken atılan ekler.
_EKLER = (
    " Katılım Bankası A.Ş.",
    " Bankası A.Ş.",
    " Katılım A.Ş.",
    " A.Ş.",
    " Anonim Şirketi",
)

_AZAMI_UZUNLUK = 15


@lru_cache(maxsize=1)
def _kisa_adlar() -> dict[str, str]:
    """banks.yaml'daki tam ad -> kısa ad eşlemesi (bir kez okunur)."""
    return {b.ad: b.kisa_ad for b in bankalari_yukle()}


def format_bank_name(bank_name: str | None) -> str:
    """Banka adını grafiklerde göstermek için standartlaştırır."""
    if not bank_name:
        return "Belirtilmemiş"

    temiz_girdi = bank_name.strip()
    if temiz_girdi.lower() == 'örnek' or temiz_girdi.lower() == 'ornek':
        return 'Albaraka Türk'

    kisa = _kisa_adlar().get(temiz_girdi)
    if kisa:
        return kisa

    # Kayıt defterinde yoksa (yeni banka, serbest metinden gelen ad) ekleri at.
    kisaltilmis = temiz_girdi
    for ek in _EKLER:
        kisaltilmis = kisaltilmis.replace(ek, "")
    kisaltilmis = kisaltilmis.strip()

    if len(kisaltilmis) > _AZAMI_UZUNLUK:
        return kisaltilmis[:_AZAMI_UZUNLUK] + "..."

    return kisaltilmis


_KATEGORI_ISIMLERI = {
    "konut": "Konut Finansmanı",
    "konut_finansmani": "Konut Finansmanı",
    "konut finansmani": "Konut Finansmanı",
    "konut finansmanı": "Konut Finansmanı",
    "ihtiyac": "İhtiyaç Finansmanı",
    "ihtiyac_finansmani": "İhtiyaç Finansmanı",
    "ihtiyac finansmani": "İhtiyaç Finansmanı",
    "ihtiyaç finansmanı": "İhtiyaç Finansmanı",
    "tasit": "Taşıt Finansmanı",
    "tasit_finansmani": "Taşıt Finansmanı",
    "tasit finansmani": "Taşıt Finansmanı",
    "taşıt finansmanı": "Taşıt Finansmanı",
    "kredi_karti": "Kredi Kartı",
    "kredi karti": "Kredi Kartı",
    "kredi kartı": "Kredi Kartı",
    "yatirim_urunu": "Yatırım Ürünü",
    "yatirim urunu": "Yatırım Ürünü",
    "yatırım ürünü": "Yatırım Ürünü",
    "altin": "Altın",
    "diger": "Diğer",
    "diğer": "Diğer"
}

def format_kategori(kategori_adi: str | None) -> str:
    """Kampanya türü için merkezi normalizasyon sağlar.
    Farklı yazımları ('Konut Finansmani', 'konut_finansmani') tek tipleştirir.
    """
    if not kategori_adi:
        return "Belirtilmemiş"
    
    temiz = str(kategori_adi).lower().strip()
    return _KATEGORI_ISIMLERI.get(temiz, temiz.replace('_', ' ').title())


def inject_custom_css():
    """Kurumsal SaaS arayüz standartlarına uygun özel CSS (glassmorphism, Inter font)."""
    st.markdown(
        """
        <style>
        /* Google Fonts - Inter */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
        }

        /* Hide Streamlit Default Elements */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Metric Cards Styling */
        [data-testid="stMetric"] {
            background-color: #25252D;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 15px 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            transition: all 0.3s ease;
        }
        
        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 168, 107, 0.2);
            border-color: rgba(0, 168, 107, 0.4);
        }

        /* DataFrame Styling */
        .dataframe {
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            overflow: hidden !important;
        }
        
        th {
            background-color: #1A1A1F !important;
            color: #E0E0E0 !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
        }
        
        td {
            font-size: 0.95rem;
            color: #D3D3D3 !important;
        }
        
        tr:hover td {
            background-color: rgba(0, 168, 107, 0.1) !important;
        }
        
        /* Buttons */
        .stButton > button {
            border-radius: 8px !important;
            font-weight: 500 !important;
            transition: all 0.2s ease;
        }
        
        /* Expanders */
        [data-testid="stExpander"] {
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            background-color: #25252D !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }
        
        /* Containers */
        [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
            background-color: #1A1A1F;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        /* Inputs & Selectboxes */
        .stSelectbox div[data-baseweb="select"] > div, 
        .stTextInput input, 
        .stNumberInput input {
            border-radius: 8px !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            background-color: #25252D !important;
            color: #E0E0E0 !important;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #121212 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

