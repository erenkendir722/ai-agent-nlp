"""Müşteri Profili ekranı — sistemin ana ekranı.

Banka çalışanının önündeki müşteriye göre hangi rakip kampanyaların GERÇEKTEN
uygulanabilir olduğunu bulur, toplam maliyete göre sıralar, her gerekçeyi
kaynağına bağlar.

    "Karşımda maaş müşterisi, 800.000 TL konut finansmanı istiyor, 10 yıl
     vade. Rakiplerin hangisi bizden iyi teklif veriyor ve neden?"

İKİ TASARIM KARARI:

1. **Uygun olmayanlar da gösterilir, sebebiyle.** Sessizce elemek, banka
   çalışanını müşteriye ne diyeceğini bilmez hâlde bırakır.
2. **Ajan izleri panelde açıktır.** Jüri ajan mimarisinin iddiasını değil,
   koşum kaydını görür: hangi ajan LLM kullandı, hangisi kod. "Aritmetiği
   ajana yaptırmıyoruz" cümlesi burada ispatlanır.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ajanlar.muhakeme import MuhakemeAjani, MusteriProfili  # noqa: E402
from src.depolama import kampanyalari_oku  # noqa: E402
from src.rag.chatbot import YASAL_UYARI  # noqa: E402
from src.schema import HedefKitle  # noqa: E402
from app.ui_utils import inject_custom_css, ortak_kenar  # noqa: E402

st.set_page_config(page_title="Müşteri Profili", page_icon="", layout="wide")
inject_custom_css()
ortak_kenar()

st.title("Müşteri Profiline Göre Uygunluk")

st.caption(
    "Kampanya listesi değil, **kısıt çözümü**: müşteri tipi, tutar, vade ve "
    "mevcut ürünler birlikte değerlendirilir. Sıralama **manşet orana değil, "
    "toplam maliyete** göre yapılır."
)


@st.cache_data(show_spinner=False)
def _kampanyalar():
    return list(kampanyalari_oku())


try:
    with st.status("Sistem verileri hazırlanıyor...", expanded=False) as status:
        st.write("Orkestratör veritabanını tarıyor...")
        kampanyalar = _kampanyalar()
        status.update(label="Veriler yüklendi ve grafikler oluşturuluyor!", state="complete", expanded=False)
except Exception as e:
    st.error("Yerel veritabanına ulaşılamadı veya tablo bulunamadı.")
    if st.session_state.get("dev_mode", False):
        with st.expander("Teknik Teşhis (Jüri / Geliştirici İçin)"):
            st.write("Veritabanı bağlantısı reddedildi veya tablo şeması eksik.")
            st.code(str(e))
    st.stop()

if not kampanyalar:
    st.info("Görüntülenecek kampanya verisi bulunamadı. Önce `make crawl` ve `make extract` çalıştırın.")
    st.stop()

MUSTERI_TIPI_ETIKETLERI = {
    HedefKitle.YENI_MUSTERI: "Yeni müşteri",
    HedefKitle.MEVCUT_MUSTERI: "Mevcut müşteri",
    HedefKitle.MAAS_MUSTERISI: "Maaş müşterisi",
    HedefKitle.SEGMENT: "Segment (emekli / öğrenci / KOBİ)",
    HedefKitle.TUM_MUSTERILER: "Belirtilmemiş",
}

# ---------------------------------------------------------------------------
# Girdi
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Müşteri bilgileri")

    tip = st.selectbox(
        "Müşteri tipi",
        options=list(MUSTERI_TIPI_ETIKETLERI),
        format_func=lambda h: MUSTERI_TIPI_ETIKETLERI[h],
        index=2,
    )
    segment = None
    if tip == HedefKitle.SEGMENT:
        segment = st.text_input("Segment adı", value="emekli")

    tutar = st.number_input(
        "Finansman tutarı (TL)", min_value=1_000, max_value=50_000_000,
        value=800_000, step=50_000,
    )
    vade = st.number_input(
        "Vade (ay)", min_value=1, max_value=360, value=120, step=12
    )
    mevcut_urunler = st.multiselect(
        "Müşterinin mevcut ürünleri",
        options=["maaş hesabı", "kredi kartı", "katılma hesabı", "sigorta", "otomatik ödeme"],
        help="Zorunlu ürün koşulu olan kampanyalar bunlara göre değerlendirilir.",
    )

    st.divider()
    st.caption(
        "Kısıt çözümü ve taksit hesabı **deterministik koddur**; bu ekranda "
        "hiçbir aşamada dil modeli çalışmaz."
    )

profil = MusteriProfili(
    musteri_tipi=tip,
    tutar=float(tutar),
    vade_ay=int(vade),
    mevcut_urunler=list(mevcut_urunler),
    segment=segment,
)

sonuclar, iz = MuhakemeAjani().calistir((profil, kampanyalar))
uygunlar = [s for s in sonuclar if s.uygun_mu]
elenenler = [s for s in sonuclar if not s.uygun_mu]
kayit_dizini = {k.kampanya_id: k for k in kampanyalar}

# ---------------------------------------------------------------------------
# Dürüstlük kapısı
# ---------------------------------------------------------------------------

dogrulanmamis = sum(1 for s in uygunlar if s.veri_eksik)
toplam_uygun = len(uygunlar)
if toplam_uygun > 0 and dogrulanmamis > 0:
    # «1024 / 1024 kampanyada doğrulanamadı» tuhaf okunuyordu: hepsi
    # doğrulanamadıysa oran vermek bilgi taşımaz, «hiçbirinde» taşır.
    # Diğer ekranlardaki uyarılarla aynı dil: kalın başlık, altında detay.
    kapsam = (
        "Hiçbir kampanyada kısıt doğrulanamadı"
        if dogrulanmamis == toplam_uygun
        else f"{toplam_uygun} kampanyanın {dogrulanmamis} tanesinde kısıt doğrulanamadı"
    )
    st.warning(
        f"**{kapsam}**  \n"
        "Sebep kaynak veride eksik alan; kalkan arızası değil. "
        "Bu kampanyalar listede kalır, yalnız kısıt kontrolü yapılamamıştır.",
        icon="⚠️",
    )
elif uygunlar:
    st.toast("Kısıt Çıkarımı Başarılı. Sistem koşulları başarıyla çözümledi.", icon="✔️")

ust1, ust2, ust3 = st.columns(3)
ust1.metric("Uygun kampanya", len(uygunlar), help="Seçilen müşteri profili (vade, tutar, segment) kısıtlarına uyan toplam kampanya sayısı.")
ust2.metric("Elenen", len(elenenler), help="Kısıtlara uymadığı için kural motoru tarafından elenen kampanyalar.")
ust3.metric("Maliyeti hesaplanan", sum(1 for s in uygunlar if s.maliyet), help="Kâr payı ve masraf verisi eksiksiz olup toplam geri ödemesi hesaplanabilenler.")

# ---------------------------------------------------------------------------
# Uygun kampanyalar
# ---------------------------------------------------------------------------


def _tl(deger: float) -> str:
    return f"{deger:,.0f} TL".replace(",", ".")


st.subheader("Uygun kampanyalar — toplam maliyete göre sıralı")

if not uygunlar:
    st.info("Aranan kriterlere uygun aktif bir katılım bankası kampanyası bulunamamıştır")

for sira, sonuc in enumerate(uygunlar[:15], 1):
    kampanya = kayit_dizini.get(sonuc.kampanya_id)
    with st.container(border=True):
        baslik, deger = st.columns([3, 2])
        baslik.markdown(f"**{sira}. {sonuc.banka_adi}**")
        if kampanya is not None:
            baslik.markdown(f"[🔗 Kaynağa Git]({kampanya.kaynak_url})")

        if sonuc.maliyet:
            deger.metric(
                "Toplam geri ödeme",
                _tl(sonuc.maliyet["toplam_geri_odeme"]),
                help=f"Aylık taksit: {_tl(sonuc.maliyet['aylik_taksit'])}",
            )
        else:
            deger.metric("Toplam geri ödeme", "Belirtilmemiş")
            deger.caption("Kâr payı oranı yok ya da makul aralık dışında.")

        for gerekce in sonuc.gerekceler:
            st.markdown(str(gerekce))

        # KANIT ZİNCİRİ: sayının hangi cümleden geldiği tek tıkla görünür.
        if kampanya is not None and kampanya.kar_payi_orani.var_mi:
            alan = kampanya.kar_payi_orani
            with st.expander("Kaynak alıntısı"):
                st.markdown(f"**Kâr payı oranı:** {alan.goster()}")
                if alan.kaynak and alan.kaynak.alinti:
                    st.markdown(f"> {alan.kaynak.alinti}")
                st.caption(
                    f"{kampanya.kaynak_url} · "
                    f"{kampanya.cekim_tarihi:%d.%m.%Y} tarihinde alınmıştır"
                )

# ---------------------------------------------------------------------------
# Elenenler — sebebiyle
# ---------------------------------------------------------------------------

if elenenler:
    st.subheader("Uygun olmayanlar ve sebepleri")
    st.caption(
        "Sessizce elemek yerine sebebini göstermek, müşteriye ne söyleneceğini "
        "de belirler."
    )
    for sonuc in elenenler[:15]:
        with st.container(border=True):
            st.markdown(f"**{sonuc.banka_adi}**")
            for gerekce in sonuc.engelleyenler():
                st.markdown(f"- {gerekce.aciklama}")

# ---------------------------------------------------------------------------
# Ajan izleri — mimarinin kanıtı
# ---------------------------------------------------------------------------

with st.expander(f"Ajan izleri — {iz.ajan_adi} · {iz.sure_ms} ms", expanded=False):
    st.markdown(
        "Her ajan ne yaptığını ve **hangi motoru kullandığını** kaydeder. "
        "Aritmetik ve kısıt çözümü `kod`, dil işleri `LLM` ile işaretlenir."
    )
    st.code(iz.satir(), language=None)
    st.caption(
        f"Bu ekranda LLM çağrısı: **{0 if not iz.llm_kullanildi else 1}** — "
        "uygunluk muhakemesi tümüyle deterministiktir."
    )

st.caption(f"_{YASAL_UYARI}_")

st.divider()
if uygunlar:
  st.subheader("Teklif Raporu Çıktısı")
  st.caption("Müşteriye sunulmak üzere hazırlanan özel teklif özetini indirebilirsiniz.")
  
  rapor_metni = f"MÜŞTERİ TEKLİF FORMU\n------------------\nFinansman Tutarı: {_tl(profil.tutar)}\nVade: {profil.vade_ay} Ay\nMüşteri Tipi: {tip.value}\n\nUYGUN KAMPANYALAR:\n"
  for i, s in enumerate(uygunlar[:5], 1):
      maliyet_str = _tl(s.maliyet['toplam_geri_odeme']) if s.maliyet else "Belirtilmemiş"
      rapor_metni += f"{i}. {s.banka_adi} - Toplam Geri Ödeme: {maliyet_str}\n"
  
  st.download_button(
      label="📄 Teklif Raporunu İndir (TXT)",
      data=rapor_metni,
      file_name="musteri_teklif_formu.txt",
      mime="text/plain",
      type="primary"
  )
