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
from src.schema import Kampanya, HedefKitle  # noqa: E402

st.set_page_config(page_title="Karşılaştırma", page_icon="⚖️", layout="wide")
st.title("⚖️ Bankalar Arası Karşılaştırma")

kayitlar = tum_kayitlar()
if not kayitlar:
    st.warning("Veritabanı boş. `make crawl && make extract` çalıştırın.")
    st.stop()

# ---------------------------------------------------------------------------
# Süzgeçler
# ---------------------------------------------------------------------------

import datetime

f1, f2 = st.columns([2, 3])

with f1:
    turler = sorted({k.kampanya_turu for k in kayitlar if k.kampanya_turu})
    secili_tur = st.selectbox("Ürün / kampanya türü", ["(tümü)", *turler])

with f2:
    bankalar = sorted({k.banka_adi for k in kayitlar})
    secili_bankalar = st.multiselect("Bankalar", bankalar, default=bankalar)

with st.expander("Gelişmiş Filtreler (Yapay Zeka Komuta Merkezi)", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        arama_metni = st.text_input("Serbest Metin Arama (Ad, içerik, avantaj)")
        
        hedef_kitleler = [h.value for h in HedefKitle]
        secili_hedef_kitle = st.multiselect("Hedef Kitle (Kapsam İzolasyonu)", hedef_kitleler)
    with c2:
        tarih_filtresi = st.date_input("Geçerlilik Tarihi (Bu tarihten önce bitenleri gizle)", value=datetime.date.today())
        
        min_guven = st.slider("Minimum Yapay Zeka Güven Skoru", 0.0, 1.0, 0.0, 0.05, help="Modelin çıkardığı verilere olan güvenini filtreler. %100 doğru çalışma için yüksek tutun.")
    with c3:
        sadece_masrafsiz = st.toggle("Yalnızca Masrafsız (Dosya masrafı yok)")
        tam_dolu_mu = st.toggle("Veri Bütünlüğü (Kritik alanları eksiksiz olanlar)", help="Kâr payı, vade gibi temel bilgileri 'Belirtilmemiş' olan kampanyaları gizler.")

suzulmus = []
for k in kayitlar:
    if secili_tur != "(tümü)" and k.kampanya_turu != secili_tur:
        continue
    if k.banka_adi not in secili_bankalar:
        continue
        
    # 1. Yeni: Hedef Kitle Filtresi
    if secili_hedef_kitle and k.hedef_kitle not in secili_hedef_kitle:
        continue
        
    # 2. Yeni: Minimum Güven Skoru
    if k.ortalama_guven < min_guven:
        continue
        
    # 3. Yeni: Veri Bütünlüğü (Kritik Alanlar Dolu Mu?)
    if tam_dolu_mu:
        # kar_payi ve vade gibi temel sayısal alanların var olup olmadığı depolama katmanında
        # direkt alan değerinin None olmamasıyla kontrol edilebilir.
        if k.kar_payi_orani is None or k.vade_ay_max is None:
            continue
            
    if sadece_masrafsiz:
        masrafsiz = k.masrafsiz_mi
        is_masrafsiz = (masrafsiz.deger is True) if hasattr(masrafsiz, "var_mi") and masrafsiz.var_mi else (masrafsiz is True)
        if not is_masrafsiz:
            continue
    if arama_metni:
        urun = k.urun_turu if hasattr(k, "urun_turu") and k.urun_turu else ""
        hedef = k.hedef_kitle if hasattr(k, "hedef_kitle") and k.hedef_kitle else ""
        arama_alani = f"{k.banka_adi} {urun} {hedef} {k.ham_metin}".lower()
        if arama_metni.lower() not in arama_alani:
            continue
    if tarih_filtresi:
        bitis = k.kampanya_bitis
        deger = bitis.deger if hasattr(bitis, "var_mi") and bitis.var_mi else bitis if not hasattr(bitis, "var_mi") else None
        
        if deger:
            try:
                if isinstance(deger, datetime.date):
                    bitis_tarihi = deger
                else:
                    bitis_str = str(deger).strip()
                    if len(bitis_str) >= 10:
                        bitis_tarihi = datetime.datetime.strptime(bitis_str[:10], "%Y-%m-%d").date()
                    else:
                        bitis_tarihi = None
                
                if bitis_tarihi and bitis_tarihi < tarih_filtresi:
                    continue # Tarihi geçmiş, gösterme
            except Exception:
                pass # Parse edilemeyen tarihleri sakla (False Negative olmasın)
    suzulmus.append(k)

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

if not sirali:
    st.warning("Seçili kriterlere (Vade, Kar Payı vb.) uygun kampanya bulunamadı.")
    if st.button("Filtreleri Sıfırla"):
        # Yalnızca rerun atıp filtreleri manuel temizlemesini önermek de bir seçenektir,
        # ancak Session State kullanmadığı için bu aşamada st.rerun() Streamlit <= 1.26'da st.experimental_rerun()
        # Streamlit 1.27+ için st.rerun() kullanılır.
        st.info("Sol taraftaki filtreleri gevşetip tekrar deneyebilirsiniz.")
    st.stop()

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

def _renklendir_guven(val):
    if val == "Belirtilmemiş" or pd.isna(val):
        return ""
    try:
        v = float(str(val).replace(",", "."))
        if v >= 0.90:
            return "background-color: rgba(39, 174, 96, 0.2)"
        elif v >= 0.70:
            return "background-color: rgba(241, 196, 15, 0.2)"
        else:
            return "background-color: rgba(231, 76, 60, 0.2)"
    except Exception:
        return ""

def _renklendir_kar(val):
    if val == "Belirtilmemiş" or pd.isna(val):
        return ""
    try:
        v = float(str(val).replace(",", "."))
        if v < 1.50:
            return "background-color: rgba(173, 216, 230, 0.4)" # LightBlue
        elif v < 2.50:
            return "background-color: rgba(135, 206, 235, 0.5)" # SkyBlue
        elif v < 3.50:
            return "background-color: rgba(70, 130, 180, 0.6)" # SteelBlue
        else:
            return "background-color: rgba(25, 25, 112, 0.5); color: white" # MidnightBlue
    except Exception:
        return ""

# pandas >= 2.1 için map, eski sürümler için applymap
styler = tablo.style
if hasattr(styler, "map"):
    styled_tablo = styler.map(_renklendir_guven, subset=["Güven"]) \
                         .map(_renklendir_kar, subset=["Kâr payı (aylık %)"])
else:
    styled_tablo = styler.applymap(_renklendir_guven, subset=["Güven"]) \
                         .applymap(_renklendir_kar, subset=["Kâr payı (aylık %)"])

st.dataframe(styled_tablo, use_container_width=True, hide_index=True)

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
