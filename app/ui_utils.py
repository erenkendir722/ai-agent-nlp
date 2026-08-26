"""Arayüz yardımcıları — grafik ve tablo etiketleri.

Banka kısa adları `data/banks.yaml`'daki `kisa_ad` alanından okunur. Burada
ikinci bir sözlük TUTULMAZ: elle yazılan kopya 16 Ağustos'ta kayıt defteriyle
yedi bankada ayrışmıştı ("Türkiye Emlak Katılım Bankası A.Ş." kayıt defterinde
"Emlak Katılım", kopyada hiç eşleşmiyordu). Kayıt defteri tek doğruluk kaynağı.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import streamlit as st

from src.collector.toplayici import bankalari_yukle

_SONUC_DOSYASI = Path(__file__).resolve().parents[1] / "docs" / "SONUCLAR.md"


@dataclass(frozen=True)
class EvalOzeti:
    """`docs/SONUCLAR.md` — sunum ve arayüz aynı kaynaktan okur."""

    # Hepsi ORAN (0–1). `eval/calistir.py` da aynı birimi kullanır; markdown
    # tablosundaki "%0.45" yüzdeye çevrilmiş hâlidir, burada geri oran yapılır.
    halusinasyon_orani: float | None = None
    makro_f1: float | None = None
    makro_f1_ga: tuple[float, float] | None = None
    sayisal_dogruluk: float | None = None
    sema_gecerliligi: float | None = None
    altin_set_n: int | None = None
    kampanya_sayisi: int | None = None


def sonuclari_oku(yol: Path | None = None) -> EvalOzeti:
    """`make eval` çıktısını parse eder. Elle yazılmış sayı kullanılmaz."""
    dosya = yol or _SONUC_DOSYASI
    if not dosya.is_file():
        return EvalOzeti()
    metin = dosya.read_text(encoding="utf-8")

    def _ara(desen: str) -> str | None:
        m = re.search(desen, metin)
        return m.group(1) if m else None

    def _float(ham: str | None) -> float | None:
        if ham is None or ham == "ölçülmedi":
            return None
        return float(ham.replace(",", "."))

    def _yuzde(ham: str | None) -> float | None:
        """Tabloda yüzde yazan alanı ORANA çevirir: "0.45" -> 0.0045.

        Bu bölme olmadan alan, adının söylediği şey (oran) değil yüzde tutar;
        çizim yerinde ikinci kez 100'le çarpılınca halüsinasyon oranı ekranda
        %0,45 yerine %45 görünür. 26 Ağustos'ta jüri provasında yakalandı.
        """
        deger = _float(ham)
        return None if deger is None else deger / 100

    ga = re.search(
        r"\*\*Makro-F1\*\* \| [0-9.]+ _\(%95 GA: ([0-9.]+)[–-]([0-9.]+)\)_",
        metin,
    )
    return EvalOzeti(
        halusinasyon_orani=_yuzde(_ara(r"\*\*Halüsinasyon oranı\*\* \| %([0-9.,]+)")),
        makro_f1=_float(_ara(r"\*\*Makro-F1\*\* \| ([0-9.]+)")),
        makro_f1_ga=(float(ga.group(1)), float(ga.group(2))) if ga else None,
        sayisal_dogruluk=_float(_ara(r"Sayısal alan doğruluğu \| ([0-9.]+|ölçülmedi)")),
        sema_gecerliligi=_float(_ara(r"Şema geçerliliği \| ([0-9.]+)")),
        altin_set_n=int(n) if (n := _ara(r"Altın set boyutu: \*\*(\d+)\*\*")) else None,
        kampanya_sayisi=int(k) if (k := _ara(r"İşlenen kampanya: \*\*(\d+)\*\*")) else None,
    )


def tr_sayi(deger: float, basamak: int = 2) -> str:
    """0.724 → '0,72' — sunumda sahte kesinlik yok."""
    return f"{deger:.{basamak}f}".replace(".", ",")

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


def ortak_kenar(*, demo_ipuclari: bool = True) -> None:
    """Her sayfada aynı kimlik + geliştirici anahtarı.

    Kenar çubuğunun geri kalanı (ağırlık, müşteri formu, örnek soru) sayfaya
    aittir; burası yalnız ortak başlığı yazar. `dev_mode` anahtarı tek kez
    tanımlanır — aynı key ile ikinci `st.toggle` Streamlit'te DuplicateWidgetID
    fırlatır.
    """
    with st.sidebar:
        st.markdown("**Katılım Lens**")
        st.caption("Takım SVARTAL · banka çalışanı aracı")
        if demo_ipuclari:
            st.caption(
                "Demo sırası: Genel Bakış → **Boru Hattı** → Metin Analizi → "
                "Karşılaştırma → Müşteri Profili → Chatbot"
            )
        st.toggle(
            "Geliştirici Modu (API)",
            key="dev_mode",
            help="JSON ve cURL çıktılarını açar. Uçlar: GET /compare, POST /ask, POST /extract (localhost:8000).",
        )
        st.markdown("---")


def inject_custom_css():
    """On-prem koyu tema — dış font CDN'si yok (hava boşluğu)."""
    st.markdown(
        """
        <style>
        html, body, [class*="css"] {
            font-family: "Segoe UI", system-ui, sans-serif !important;
        }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        /* Üst çubuğu gizleme: projeksiyonda sayfa adı ve menü okunur kalsın. */

        .kl-serit {
            background: linear-gradient(90deg, rgba(0,168,107,0.18), transparent);
            border: 1px solid rgba(0, 168, 107, 0.35);
            border-radius: 10px;
            padding: 10px 16px;
            margin-bottom: 12px;
            color: #E0E0E0;
            font-size: 0.92rem;
        }
        
        /* Metric Cards Styling (Glassmorphism & Elevation) */
        [data-testid="stMetric"] {
            background: rgba(37, 37, 45, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            padding: 15px 20px;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
            transition: all 0.3s ease;
        }
        
        [data-testid="stMetric"]:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 24px rgba(0, 168, 107, 0.3);
            border-color: rgba(0, 168, 107, 0.5);
        }
        
        /* Metric Caption / Delta Visibility */
        [data-testid="stMetricDelta"] > div {
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            opacity: 0.95 !important;
        }

        /* Alerts Semantic Coloring (Info, Warning, Error) */
        div.stAlert > div {
            backdrop-filter: blur(8px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            border-radius: 8px;
        }
        div[data-baseweb="notification"] {
            border: 1px solid rgba(255, 255, 255, 0.1);
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

