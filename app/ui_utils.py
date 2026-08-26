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
from src.schema import alan_etiketi, tur_etiketi

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


_KAMPANYASI_EKI = " Kampanyası"


def format_kategori(kategori_adi: str | None) -> str:
    """Kampanya türünün tablo/etiket gösterimi — kaynağı ŞEMA.

    İKİNCİ SÖZLÜK TUTULMAZ (bu dosyanın başındaki kuralın aynısı). Burada
    elle yazılmış bir `_KATEGORI_ISIMLERI` sözlüğü vardı ve dört türü
    (`alisveris_puani`, `yeni_musteri`, `kart`, `finansman`) hiç içermiyordu.
    Eksik türler `.title()` yedeğine düşüyor, Türkçe harfleri kaybediyordu:

        alisveris_puani  ->  "Alisveris Puani"   (ş ve ı yok)
        yeni_musteri     ->  "Yeni Musteri"      (ü yok)

    Bu yazımlar karşılaştırma tablosunda ve süzgeç açılırında görünüyordu.
    `schema.KAMPANYA_TURU_ETIKETLERI` doğru yazımları zaten tutuyor ve
    `.title()`'ın Türkçe'yi bozduğu o dosyada da yazılı.

    Şema uzun etiket verir («Konut Finansmanı Kampanyası»); tablo sütununda
    ve açılır listede tür adı yeter, «Kampanyası» eki her satırda tekrar
    ederdi. Ek yalnız GÖSTERİMDEN düşürülür, sözlükten değil.
    """
    if not kategori_adi:
        return "Belirtilmemiş"

    ham = str(kategori_adi).strip()
    etiket = tur_etiketi(ham)
    if not etiket:
        # Şemada olmayan serbest metin (`urun_turu`) olduğu gibi gösterilir:
        # `.title()` uygulamak «Alisveris» türü bozulmalara geri dönüş olurdu.
        return ham

    if etiket.endswith(_KAMPANYASI_EKI):
        return etiket[: -len(_KAMPANYASI_EKI)]
    return etiket


_HEDEF_KITLE_ETIKETLERI = {
    "yeni_musteri": "Yeni müşteri",
    "mevcut_musteri": "Mevcut müşteri",
    "maas_musterisi": "Maaş müşterisi",
    "segment": "Segment (emekli / öğrenci / KOBİ)",
    "tum_musteriler": "Tüm müşteriler",
}
"""Hedef kitle enum değeri → ekranda yazılan etiket.

Şemaya DEĞİL buraya konuyor. `src/schema.py` hem donmuş hem de
`CIKARIM_KAYNAKLARI` içinde: oraya eklenen her satır çıkarım parmak izini
değiştirir ve veritabanını «bayat» ilan eder. Salt gösterim için ölçümü
bayatlatmak orantısız olurdu; etiketin veriyle bir ilgisi yok.
"""


def format_hedef_kitle(deger) -> str:
    """`yeni_musteri` → «Yeni müşteri»."""
    if deger is None:
        return "Belirtilmemiş"
    ham = getattr(deger, "value", deger)
    return _HEDEF_KITLE_ETIKETLERI.get(str(ham).strip().lower(), str(ham))


def format_alan_adi(alan_adi: str) -> str:
    """Alan adının ekranda yazılan hâli — kaynağı ŞEMA.

    `.replace("_", " ").title()` KULLANILMAZ. `schema.ALAN_ETIKETLERI`'nin
    kendi notunda yazdığı gibi `.title()` Türkçe'yi sessizce bozar:

        kar_payi_orani  ->  "Kar Payi Orani"   (â ve ı kayıp)
        alisveris_puani ->  "Alisveris Puani"  (ş ve ı kayıp)

    Bu yazımlar karşılaştırma ekranındaki kampanya kartlarında görünüyordu.
    """
    return alan_etiketi(alan_adi) or alan_adi.replace("_", " ")


def uyarilari_goster(
    uyari_listesi,
    *,
    baslik: str = "Karşılaştırma notları",
) -> None:
    """Uyarıları ÖNEMİNE göre ayırarak çizer.

    NEDEN VAR — 26 Ağustos'ta ölçüldü: her uyarı ayrı bir `st.warning` kutusuydu.
    Dört özdeş sarı kutu 1.060 karakterle ekranı dolduruyor, cevabı ve kaynakları
    aşağı itiyordu. Hepsi aynı ağırlıkta göründüğü için kullanıcı hangisinin
    kararını değiştirdiğini seçemiyordu.

    Ayrım şu: `engelleyici` uyarı bir kriteri SIRALAMADAN DÜŞÜRÜR — kullanıcı
    onu görmeden karar veremez, o yüzden açıkta durur. Kalanlar bağlam notudur
    («farklı türler karşılaştırılıyor»); bilinmesi iyidir ama ekranı kapatmamalı,
    katlanabilir tek panelde toplanır.

    Metin taşımayan sade `str` uyarılar da kabul edilir: `engelleyici` alanı
    olmayan her şey bağlam notu sayılır. Böylece bu yardımcı, uyarıyı nereden
    alırsa alsın (API, chatbot, karşılaştırma) çalışır.
    """
    if not uyari_listesi:
        return

    engelleyiciler = [u for u in uyari_listesi if getattr(u, "engelleyici", False)]
    notlar = [u for u in uyari_listesi if not getattr(u, "engelleyici", False)]

    for uyari in engelleyiciler:
        st.warning(_uyari_metni(uyari))

    if not notlar:
        return

    # Tek not için panel açıp kapamak gereksiz tıklama; doğrudan gösterilir.
    if len(notlar) == 1:
        st.info(_uyari_metni(notlar[0]))
        return

    with st.expander(f"{baslik} ({len(notlar)})", expanded=False):
        for uyari in notlar:
            st.markdown(_uyari_metni(uyari))


def _uyari_metni(uyari) -> str:
    """Başlığı kalın, detayı alt satırda. Markdown'da satır sonu iki boşluktur."""
    baslik = getattr(uyari, "baslik", None)
    detay = getattr(uyari, "detay", None)
    if baslik and detay:
        return f"**{baslik}**  \n{detay}"
    return str(uyari)


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

