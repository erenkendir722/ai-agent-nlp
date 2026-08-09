"""Karşılaştırma ekranı — şartname 5.7'nin beş kriteri.

Her satırın altında açılır panel: tüm alanlar + güven skoru + KAYNAK ALINTISI
ve URL. Bankacılıkta izlenebilirlik olmadan hiçbir sistem kabul edilmez;
bu panel o izlenebilirliğin arayüzdeki karşılığıdır.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.comparison.karsilastirma import (  # noqa: E402
    KRITER_ETIKETLERI,
    Agirliklar,
    Kriter,
    avantaj_skorla,
    sirala,
    toplam_maliyet,
    uyarilar,
)
from src.depolama import tum_kayitlar  # noqa: E402
from src.schema import Kampanya  # noqa: E402

st.set_page_config(page_title="Karşılaştırma", page_icon="⚖️", layout="wide")
st.title("⚖️ Bankalar Arası Karşılaştırma")

kayitlar = tum_kayitlar()
if not kayitlar:
    st.warning("Veritabanı boş. `make crawl && make extract` çalıştırın.")
    st.stop()

# ---------------------------------------------------------------------------
# Süzgeçler
# ---------------------------------------------------------------------------

f1, f2 = st.columns([2, 3])

with f1:
    turler = sorted({k.kampanya_turu for k in kayitlar if k.kampanya_turu})
    secili_tur = st.selectbox("Ürün / kampanya türü", ["(tümü)", *turler])

with f2:
    bankalar = sorted({k.banka_adi for k in kayitlar})
    secili_bankalar = st.multiselect("Bankalar", bankalar, default=bankalar)

suzulmus = [
    k for k in kayitlar
    if (secili_tur == "(tümü)" or k.kampanya_turu == secili_tur)
    and k.banka_adi in secili_bankalar
]

if not suzulmus:
    st.info("Seçime uyan kampanya yok.")
    st.stop()

# ---------------------------------------------------------------------------
# Ağırlıklar — "en avantajlı" kara kutu değil
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Skor ağırlıkları")
    st.caption(
        "«En Avantajlı» sıralaması bu ağırlıklarla hesaplanır. "
        "Formül dokümantasyondadır; sıralama kara kutu değildir."
    )
    a_kar = st.slider("Kâr payı oranı", 0.0, 1.0, 0.40, 0.05)
    a_masraf = st.slider("Masraf", 0.0, 1.0, 0.25, 0.05)
    a_vade = st.slider("Vade", 0.0, 1.0, 0.20, 0.05)
    a_odul = st.slider("Ödül", 0.0, 1.0, 0.15, 0.05)
    agirliklar = Agirliklar(a_kar, a_masraf, a_vade, a_odul)
    st.caption(f"Ağırlık toplamı {agirliklar.toplam():.2f} — otomatik normalize edilir.")

# ---------------------------------------------------------------------------
# Kriter butonları (şartname 5.7)
# ---------------------------------------------------------------------------

st.subheader("Hızlı sıralama")
if "kriter" not in st.session_state:
    st.session_state.kriter = Kriter.EN_AVANTAJLI

sutunlar = st.columns(len(KRITER_ETIKETLERI))
for sutun, (kriter, etiket) in zip(sutunlar, KRITER_ETIKETLERI.items(), strict=True):
    if sutun.button(etiket, use_container_width=True):
        st.session_state.kriter = kriter

secili_kriter: Kriter = st.session_state.kriter
st.caption(f"Sıralama ölçütü: **{KRITER_ETIKETLERI[secili_kriter]}**")

sirali = sirala(suzulmus, secili_kriter, agirliklar)

for mesaj in uyarilar(sirali):
    st.warning(mesaj)

# ---------------------------------------------------------------------------
# Tablo
# ---------------------------------------------------------------------------


def _gorunum(deger, birim: str = "") -> str:
    if deger is None:
        return "Belirtilmemiş"
    if isinstance(deger, bool):
        return "Evet" if deger else "Hayır"
    if isinstance(deger, float):
        return f"{deger:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + birim
    return f"{deger}{birim}"


tablo = pd.DataFrame(
    [
        {
            "Banka": k.banka_adi.replace(" Katılım Bankası A.Ş.", ""),
            "Tür": k.kampanya_turu or "—",
            "Kâr payı (aylık %)": _gorunum(k.kar_payi_orani),
            "Azami vade (ay)": _gorunum(k.vade_ay_max),
            "Azami tutar (TL)": _gorunum(k.finansman_tutari_max),
            "Tahsis ücreti": _gorunum(k.tahsis_ucreti),
            "Masrafsız": _gorunum(k.masrafsiz_mi),
            "Ödül (TL)": _gorunum(k.odul_miktari),
            "Güven": f"{k.ortalama_guven:.2f}",
        }
        for k in sirali
    ]
)
st.dataframe(tablo, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Avantaj skorunun dökümü
# ---------------------------------------------------------------------------

if secili_kriter == Kriter.EN_AVANTAJLI:
    with st.expander("«En Avantajlı» skoru nasıl hesaplandı?"):
        st.markdown(
            "Her kriter kendi içinde 0–1 aralığına ölçeklenir (min-maks "
            "normalizasyon), sonra yukarıdaki ağırlıklarla toplanır. "
            "Eksik veri nötr (0,5) sayılır ve *karşılaştırılabilirlik* oranı düşer."
        )
        for detay in avantaj_skorla(sirali, agirliklar):
            st.markdown(
                f"**{detay.banka_adi}** — {detay.aciklama()}  \n"
                f"Karşılaştırılabilirlik: {detay.karsilastirilabilirlik:.2f}"
            )

st.divider()

# ---------------------------------------------------------------------------
# Kanıt panelleri — her sayının kaynağı
# ---------------------------------------------------------------------------

st.subheader("Kayıt detayları ve kaynak kanıtı")

for kayit in sirali[:20]:
    baslik = (
        f"{kayit.banka_adi.replace(' Katılım Bankası A.Ş.', '')} — "
        f"{kayit.urun_turu or kayit.kampanya_turu or 'kampanya'} "
        f"(doluluk %{kayit.doluluk_orani * 100:.0f})"
    )
    with st.expander(baslik):
        kampanya: Kampanya = kayit.kampanyaya_cevir()
        st.markdown(f"**Kaynak:** {kayit.kaynak_url}")
        st.caption(f"Çekim tarihi: {kayit.cekim_tarihi:%d.%m.%Y %H:%M}")

        for alan_adi, alan in kampanya.cikarilan_alanlar().items():
            if not alan.var_mi:
                continue
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.markdown(f"**{alan_adi}**")
            c2.markdown(f"{alan.goster()}")
            c3.markdown(f"`{alan.yontem}` · {alan.guven:.2f}")
            if alan.kaynak and alan.kaynak.alinti:
                st.caption(f"↳ Kaynak alıntısı: _{alan.kaynak.alinti[:280]}_")

        bos = [ad for ad, a in kampanya.cikarilan_alanlar().items() if not a.var_mi]
        if bos:
            st.caption(f"**Belirtilmemiş alanlar:** {', '.join(bos)}")

st.divider()

# ---------------------------------------------------------------------------
# Toplam maliyet hesaplayıcı
# ---------------------------------------------------------------------------

st.subheader("Toplam maliyet hesaplayıcı")
st.caption(
    "Eşit taksitli (annüite) ödeme planı. Katılım bankacılığında murabaha ile "
    "satış bedeli baştan sabitlenir; taksit hesabı matematiksel olarak aynıdır."
)

h1, h2, h3, h4 = st.columns(4)
anapara = h1.number_input("Finansman tutarı (TL)", min_value=1000.0, value=500_000.0, step=10_000.0)
oran = h2.number_input("Aylık kâr payı oranı (%)", min_value=0.0, value=2.05, step=0.01)
vade = h3.number_input("Vade (ay)", min_value=1, value=120, step=6)
tahsis = h4.number_input("Tahsis ücreti (TL)", min_value=0.0, value=0.0, step=500.0)

if st.button("Hesapla", type="primary"):
    sonuc = toplam_maliyet(anapara, oran, int(vade), tahsis)
    m1, m2, m3 = st.columns(3)
    m1.metric("Aylık taksit", f"{sonuc['aylik_taksit']:,.2f} TL".replace(",", "."))
    m2.metric("Toplam geri ödeme", f"{sonuc['toplam_geri_odeme']:,.2f} TL".replace(",", "."))
    m3.metric("Toplam kâr payı", f"{sonuc['toplam_kar_payi']:,.2f} TL".replace(",", "."))
    st.caption(f"Toplam maliyet oranı: %{sonuc['toplam_maliyet_orani']:.2f}")
