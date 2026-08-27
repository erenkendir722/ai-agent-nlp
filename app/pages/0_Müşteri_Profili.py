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
from app.ui_utils import format_hedef_kitle, inject_custom_css, ortak_kenar  # noqa: E402

st.set_page_config(page_title="Müşteri Profili", page_icon="", layout="wide")
inject_custom_css()
ortak_kenar()

st.title("Müşteri Profiline Göre Uygunluk")

# NE YAPTIĞIMIZI İLK EKRANDA SÖYLE (27 Ağustos).
#
# Sayfaya giren kişi önce bir yükleme kutusu, sonra büyük bir uyarı, sonra üç
# sayı görüyordu; ne yaptığımızı anlatan cümle yukarıda kalıp kayboluyordu.
# Şerit `Genel Bakış` sayfasındakiyle aynı `kl-serit` sınıfını kullanır —
# ekranlar arası tek görsel dil.
st.markdown(
    '<div class="kl-serit">Önünüzdeki müşteriyi tanımlayın; hangi rakip '
    "kampanyanın <b>gerçekten uygulanabilir</b> olduğunu, hangisinin neden "
    "elendiğini ve toplam maliyeti görün.</div>",
    unsafe_allow_html=True,
)
# Üstte YALNIZ kullanıcının bilmesi gereken kalır: sıralamanın neye göre
# yapıldığı kararı etkiler. «Deterministik kod, dil modeli çalışmaz» iddiası
# yöntem anlatımıdır — sayfanın en altına, ajan izleri panelinin yanına indi.
st.caption(
    "Kampanya listesi değil, **kısıt çözümü**. Sıralama **manşet orana değil, "
    "toplam maliyete** göre yapılır."
)


@st.cache_data(show_spinner=False)
def _kampanyalar():
    return list(kampanyalari_oku())


try:
    # `st.status` DEĞİL: tamamlanmış durum kutusu ekranda KALICI duruyordu ve
    # «grafikler oluşturuluyor» diyordu — bu sayfada grafik yok. Yükleme bittikten
    # sonra ekranda yer tutan bir kutu bilgi değil gürültüdür. `st.spinner`
    # bitince kaybolur; veri zaten önbelleklendiği için ikinci çizimde hiç görünmez.
    with st.spinner("Kampanya verisi okunuyor…"):
        kampanyalar = _kampanyalar()
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

# ---------------------------------------------------------------------------
# Girdi — ANA ALANIN ÜSTÜNDE (27 Ağustos)
# ---------------------------------------------------------------------------
#
# Form eskiden kenar çubuğundaydı ve `ortak_kenar()` marka bloğunu ÖNCE
# yazdığı için en alta düşüyordu: sayfanın tek etkileşimli parçası, dizüstü
# ekranında kaydırmadan görünmüyordu. Yukarı alındı — giren kişi ilk bakışta
# hem ne yaptığımızı hem neyi değiştirebileceğini görüyor.

MUSTERI_TIPI_SECENEKLERI = [
    HedefKitle.MAAS_MUSTERISI,
    HedefKitle.YENI_MUSTERI,
    HedefKitle.MEVCUT_MUSTERI,
    HedefKitle.SEGMENT,
    HedefKitle.TUM_MUSTERILER,
]

with st.container(border=True):
    st.markdown("**Müşteri bilgileri**")
    s1, s2, s3, s4 = st.columns([2, 2, 1, 3])

    tip = s1.selectbox(
        "Müşteri tipi",
        options=MUSTERI_TIPI_SECENEKLERI,
        format_func=format_hedef_kitle,
    )
    tutar = s2.number_input(
        "Finansman tutarı (TL)", min_value=1_000, max_value=50_000_000,
        value=800_000, step=50_000,
    )
    vade = s3.number_input(
        "Vade (ay)", min_value=1, max_value=360, value=120, step=12
    )
    mevcut_urunler = s4.multiselect(
        "Müşterinin mevcut ürünleri",
        options=["maaş hesabı", "kredi kartı", "katılma hesabı", "sigorta", "otomatik ödeme"],
        placeholder="Varsa seçin",
        help="Zorunlu ürün koşulu olan kampanyalar bunlara göre değerlendirilir.",
    )

    # Segment adı yalnız gerektiğinde çıkar; her zaman duran boş bir kutu
    # kullanıcıya «burayı doldurmalı mıyım» diye sordururdu.
    segment = None
    if tip == HedefKitle.SEGMENT:
        segment = s1.text_input("Segment adı", value="emekli")

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
maliyetli = sum(1 for s in uygunlar if s.maliyet)

# ÖLÇÜLER ÖNCE, UYARI SONRA (27 Ağustos). Uyarı en üstteydi ve ekranın en
# büyük ögesiydi; kullanıcı daha ne baktığını bilmeden bir kusur listesi
# okuyordu. Önce sonuç, sonra sonucun sınırı.
ust1, ust2, ust3 = st.columns(3)
ust1.metric(
    "Uygun kampanya", toplam_uygun,
    help="Seçilen müşteri profili (vade, tutar, segment) kısıtlarına uyan toplam kampanya sayısı.",
)
ust2.metric(
    "Elenen", len(elenenler),
    help="Kısıtlara uymadığı için kural motoru tarafından elenen kampanyalar.",
)
ust3.metric(
    "Maliyeti hesaplanan", maliyetli,
    help="Kâr payı ve masraf verisi eksiksiz olup toplam geri ödemesi hesaplanabilenler.",
)

# «Maliyeti hesaplanan: 4» sıradan üçüncü bir sayı gibi duruyordu; oysa
# sayfanın asıl sınırı bu. «Toplam maliyete göre sıralı» iddiası yalnız o
# kayıtlar için geçerli, kalanlar maliyetsiz sıralanıyor. Söylemek zorundayız.
if toplam_uygun and maliyetli < toplam_uygun:
    ust3.caption(
        f"{toplam_uygun} uygun kampanyanın {maliyetli} tanesi. "
        "Maliyet sıralaması yalnız bunları kapsar."
    )

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
        "Bu kampanyalar listede kalır, yalnız kısıt kontrolü yapılamamıştır."
    )
elif uygunlar:
    st.toast("Kısıt çözümü tamam — tüm koşullar değerlendirildi.")

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
            baslik.markdown(f"[Kaynağa git]({kampanya.kaynak_url})")

        if sonuc.maliyet:
            deger.metric(
                "Toplam geri ödeme",
                _tl(sonuc.maliyet["toplam_geri_odeme"]),
                help=f"Aylık taksit: {_tl(sonuc.maliyet['aylik_taksit'])}",
            )
        else:
            deger.metric("Toplam geri ödeme", "Belirtilmemiş")
            deger.caption("Kâr payı oranı yok ya da makul aralık dışında.")

        # TEKRAR EDEN CÜMLE KISALTILDI (27 Ağustos).
        #
        # Kısıt verisi olmayan kayıtta gerekçe her seferinde aynı uzun cümle
        # oluyordu: «Uygun — Uygunluk kısıtı bu kayıtta yok — kampanya
        # metninde belirtilmemiş ya da çıkarılamamış olabilir; kısıtlar
        # doğrulanmadı.» 331 kartın 302'sinde birebir aynı. Üstelik aynı bilgi
        # sayfanın başındaki uyarıda toplu hâlde zaten yazıyor; kart başına
        # tekrar etmek listeyi okunmaz yapıyordu.
        #
        # Gerçekten DEĞERLENDİRİLMİŞ bir kısıt varsa gerekçe tam hâliyle
        # gösterilir — asıl bilgi orada.
        if sonuc.veri_eksik:
            st.caption("Kısıt bilgisi bu kayıtta yok; koşullar doğrulanmadı.")
        else:
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

with st.expander(f"Nasıl hesaplandı? — {iz.ajan_adi} · {iz.sure_ms} ms", expanded=False):
    st.code(iz.satir(), language=None)
    st.caption(
        f"Bu ekranda dil modeli çağrısı: **{0 if not iz.llm_kullanildi else 1}**. "
        "Kısıt çözümü ve taksit hesabı deterministik koddur — aynı girdi her "
        "zaman aynı sonucu verir."
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
      label="Teklif raporunu indir (TXT)",
      data=rapor_metni,
      file_name="musteri_teklif_formu.txt",
      mime="text/plain",
      type="primary"
  )
