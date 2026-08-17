"""Streamlit ana sayfa — Genel Bakış (Katman 5).

Bu arayüz BANKA ÇALIŞANI için tasarlandı, tüketici için değil. Ayrım önemli:
banka çalışanı rakip analizini hızlı yapmak, veri kalitesini görmek ve her
sayının nereden geldiğini denetlemek ister. Bu yüzden her ekranda güven skoru
ve kaynak alıntısı erişilebilir durumda.

Çalıştırma:  streamlit run app/Genel_Bakis.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.collector.toplayici import bankalari_yukle  # noqa: E402
from src.depolama import istatistikler, tum_kayitlar  # noqa: E402
from app.ui_utils import format_bank_name  # noqa: E402

st.set_page_config(
    page_title="Katılım Bankacılığı Kampanya Analizi",
    page_icon="🏦",
    layout="wide",
)


@st.cache_data(ttl=60)
def _veri():
    kayitlar = tum_kayitlar()
    return kayitlar, istatistikler()


@st.cache_data(ttl=300)
def _bankalar():
    return bankalari_yukle()


st.title("🏦 Katılım Bankacılığı Kampanya Analizi")
st.caption(
    "TEKNOFEST 2026 · Yapay Zekâ Dil Ajanları · Katılım Bankacılığı Finansal Metin Madenciliği · "
    "Takım SVARTAL"
)

try:
    with st.status("⏳ Sistem verileri hazırlanıyor...", expanded=False) as status:
        st.write("Orkestratör veritabanını tarıyor...")
        kayitlar, ozet = _veri()
        st.write("Banka kayıt defteri yükleniyor...")
        bankalar = _bankalar()
        status.update(label="✅ Veriler yüklendi ve grafikler oluşturuluyor!", state="complete", expanded=False)
except Exception as e:
    st.error("Yerel veritabanına ulaşılamadı veya tablo bulunamadı.")
    with st.expander("Teknik Teşhis (Jüri / Geliştirici İçin)"):
        st.write("Veritabanı bağlantısı reddedildi veya tablo şeması eksik.")
        st.code(str(e))
    st.stop()

if not kayitlar:
    st.info("Veri ambarı şu an boş. Orkestratör ajanı çalıştırarak katılım bankalarından veri toplayın.")
    st.code("make crawl\nmake extract", language="bash")
    st.stop()

# ---------------------------------------------------------------------------
# Üst göstergeler
# ---------------------------------------------------------------------------

s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Kampanya", ozet["kampanya_sayisi"])
s2.metric("Banka (veri toplanan)", ozet["banka_sayisi"])
s3.metric("Kayıt defterindeki banka", len(bankalar))
s4.metric("Ortalama alan doluluğu", f"%{ozet['ortalama_doluluk'] * 100:.0f}")
s5.metric("Ortalama güven", f"{ozet['ortalama_guven']:.2f}")

son = ozet["son_guncelleme"]
st.caption(f"Son veri çekimi: **{son:%d.%m.%Y %H:%M}**" if son else "Son çekim bilinmiyor")

st.divider()

# ---------------------------------------------------------------------------
# Dağılımlar
# ---------------------------------------------------------------------------

sol, sag = st.columns(2)

with sol:
    st.subheader("Kampanya türü dağılımı")
    dagilim = ozet["tur_dagilimi"]
    if dagilim:
        cerceve = pd.DataFrame(
            {"Tür": list(dagilim.keys()), "Adet": list(dagilim.values())}
        )
        dinamik_yukseklik_bar = max(380, len(cerceve) * 35)
        grafik = px.bar(cerceve, x="Adet", y="Tür", orientation="h", text="Adet")
        grafik.update_layout(height=dinamik_yukseklik_bar, margin={"l": 0, "r": 0, "t": 10, "b": 0})
        grafik.update_traces(
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Adet: %{x}<extra></extra>"
        )
        with st.container(height=min(500, dinamik_yukseklik_bar + 20)):
            st.plotly_chart(grafik, use_container_width=True)
    else:
        st.info("Henüz sınıflandırma verisi yok.")

with sag:
    st.subheader("Banka × Tür ısı haritası")
    tablo = pd.DataFrame(
        [
            {
                "Banka": format_bank_name(k.banka_adi),
                "Tür": k.kampanya_turu or "belirtilmemiş",
            }
            for k in kayitlar
        ]
    )
    capraz = pd.crosstab(tablo["Banka"], tablo["Tür"])
    if not capraz.empty:
        dinamik_yukseklik_isi = max(380, len(capraz) * 35)
        isi = px.imshow(capraz, text_auto=True, aspect="auto", color_continuous_scale="Blues")
        isi.update_layout(height=dinamik_yukseklik_isi, margin={"l": 0, "r": 0, "t": 10, "b": 0})
        isi.update_traces(
            hovertemplate="Banka: <b>%{y}</b><br>Tür: %{x}<br>Adet: %{z}<extra></extra>"
        )
        with st.container(height=min(500, dinamik_yukseklik_isi + 20)):
            st.plotly_chart(isi, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Banka kayıt defteri — şartname 5.1 kanıtı
# ---------------------------------------------------------------------------

st.subheader("Banka kayıt defteri (BDDK listesi)")
st.caption(
    "Faaliyete geçmemiş bankalar da listede tutulur ve işaretlenir. "
    "Bu bankaların sitesinde kampanya bulunmaması bir veri eksikliği değildir."
)

kampanya_sayaci: dict[str, int] = {}
for k in kayitlar:
    kampanya_sayaci[k.banka_kodu] = kampanya_sayaci.get(k.banka_kodu, 0) + 1

defter = pd.DataFrame(
    [
        {
            "Kod": b.kod,
            "Banka": b.ad,
            "Durum": b.durum.value,
            "Kampanya": kampanya_sayaci.get(b.kod, 0),
            "Site": b.site or "—",
        }
        for b in bankalar
    ]
)
st.dataframe(defter, use_container_width=True, hide_index=True)

durum_sayaci = defter["Durum"].value_counts().to_dict()
st.caption(
    " · ".join(f"**{durum}**: {adet}" for durum, adet in durum_sayaci.items())
    + f" · Toplam **{len(bankalar)}** banka"
)

with st.expander("Veri toplama metodolojisi ve etik ilkeler"):
    st.markdown(
        """
- **BDDK listesi manuel alınmıştır.** BDDK sitesi `robots.txt` ile otomatik
  erişimi engellediği için liste tarayıcıdan elle çıkarılmıştır. Şartname
  manuel veri toplama tekniklerine izin vermektedir.
- **robots.txt uyumu:** Her banka sitesi için `robots.txt` kontrol edilir,
  `crawl-delay` uygulanır.
- **Hız sınırı:** İstekler arası en az 2 saniye, eşzamanlı istek yok.
- **Tanımlı User-Agent:** İletişim adresi ile birlikte gönderilir.
- **Yalnız kamuya açık sayfalar.** Giriş gerektiren hiçbir alana erişilmez.
- **Kişisel veri toplanmaz** (KVKK).
- **Yayınlanan veri setinde tam sayfa metni değil**, yapısal alanlar + URL +
  alıntı parçası yer alır. Telif riski böyle sıfırlanır.
        """
    )
