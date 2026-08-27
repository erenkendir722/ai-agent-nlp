"""Streamlit ana sayfa — Genel Bakış (Katman 5).

Bu arayüz BANKA ÇALIŞANI için tasarlandı, tüketici için değil. Ayrım önemli:
banka çalışanı rakip analizini hızlı yapmak, veri kalitesini görmek ve her
sayının nereden geldiğini denetlemek ister. Bu yüzden her ekranda güven skoru
ve kaynak alıntısı erişilebilir durumda.

Çalıştırma: streamlit run app/Genel_Bakış.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# PyArrow 25'in varsayılan mimalloc ayırıcısı macOS/arm64'te thread yeniden
# başlatılırken çöküyor; Streamlit her sayfa geçişinde yeni bir ScriptRunner
# thread'i açtığı için `st.dataframe` olan bir sayfadan çıkınca uygulama
# komple ölüyor (SIGSEGV — hata sayfası bile çıkmıyor, sunucu düşüyor).
#
# `make run` bunu ortamdan geçirir; bu satır yukarıdaki docstring'in tarif
# ettiği çıplak `streamlit run app/Genel_Bakış.py` için. Çok sayfalı uygulamada
# önce bu betik koştuğundan bütün sayfalar bundan yararlanır.
#
# `import pandas`tan ÖNCE olmalı: pandas pyarrow'u kendi import'unda getiriyor
# ve ayırıcı import anında seçiliyor. Aşağıdaki E402'ler bu yüzden.
# Ayrıntı: docs/ARAYUZ_INCELEME.md — «Ortam» bölümü.
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import date # noqa: E402

from src.collector.toplayici import bankalari_yukle # noqa: E402
from src.depolama import istatistikler # noqa: E402
from src.schema import BankaDurumu # noqa: E402
from app.ui_utils import (  # noqa: E402
  format_bank_name,
  format_kategori,
  inject_custom_css,
  kayitlari_yukle,
  ortak_kenar,
  sayfa_gezinme,
  sayfa_sonu,
  sonuclari_oku,
  tr_sayi,
)

st.set_page_config(
  page_title="Katılım Bankacılığı Kampanya Analizi",
  page_icon="",
  layout="wide",
)

inject_custom_css()
ortak_kenar()
sayfa_gezinme()


def _asdate(deger):
  """`kampanya_bitis` kayıtta date ya da datetime olabilir; ikisi de gelir."""
  return deger.date() if hasattr(deger, "date") else deger


@st.cache_data(ttl=60)
def _ozet():
  return istatistikler()


@st.cache_data(ttl=300)
def _bankalar():
  return bankalari_yukle()


st.title("Katılım Bankacılığı Kampanya Analizi")
st.markdown(
  '<div class="kl-serit">Dokuz katılım bankasının güncel kampanyaları tek ekranda: '
  "koşullarıyla, kaynağıyla ve <b>müşteriye söylenebilecek karşılaştırmalı "
  "maliyetiyle</b>. Her sayının geldiği cümle görülebilir.</div>",
  unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Hızlı menü
# ---------------------------------------------------------------------------
#
# Sıra DEMO SIRASINI izler (`ortak_kenar` içindeki metinle aynı), alfabetik ya
# da dosya numarasına göre değil: jüri önünde ekranlar bu sırayla geziliyor.

# `st.status` KALDIRILDI: tamamlanmış durum kutusu ekranda KALICI duruyor ve
# «grafikler oluşturuluyor» diye bitmiş bir işi anlatmaya devam ediyordu.
# Yükleme bitince yer tutan kutu bilgi değil gürültüdür.
kayitlar = kayitlari_yukle()
ozet = _ozet()
bankalar = _bankalar()

# HIZLI MENU KALDIRILDI, YERINE VERIDEN TUREYEN AKSIYON (27 Agu incelemesi).
#
# Menu sol kenar cubugunun BIREBIR KOPYASIYDI: ayni alti sayfa, ayni sira,
# ayni etiket. Ikinci bir kopya gezinmeyi kolaylastirmaz — hangisinin dogru
# oldugunu sorgulatir ve ekranin ustunde bedava yer kaplar.
#
# Yerine gecen sey bir menu DEGIL: bugun bakilmasi gereken seyi VERIDEN
# hesaplayip oraya goturuyor. Sayilar sabit yazilmadi; korpus degisince
# kartlar da degisir. Sayfa adi tasiyan tek sey hedef dugmesidir.

_bugun = date.today()
_yakinda_bitenler = [
  k for k in kayitlar
  if k.kampanya_bitis and 0 <= (_asdate(k.kampanya_bitis) - _bugun).days <= 7
]
_oranli = [k for k in kayitlar if k.kar_payi_orani is not None]

st.markdown("**Bugün önerilen aksiyon**")
_a1, _a2, _a3 = st.columns(3)

with _a1:
  with st.container(border=True):
    if _yakinda_bitenler:
      st.markdown(
        f'<div class="kl-kart-ad">{len(_yakinda_bitenler)} kampanya bu hafta bitiyor</div>'
        '<div class="kl-kart-alt">Süresi dolmadan rakip teklifini kontrol edin.</div>',
        unsafe_allow_html=True,
      )
    else:
      st.markdown(
        '<div class="kl-kart-ad">Bu hafta biten kampanya yok</div>'
        '<div class="kl-kart-alt">Bitiş tarihlerini banka bazında görün.</div>',
        unsafe_allow_html=True,
      )
    if st.button("Banka Profili", key="gb_aksiyon_biten", use_container_width=True):
      st.switch_page("pages/5_Banka_Profili.py")

with _a2:
  with st.container(border=True):
    st.markdown(
      f'<div class="kl-kart-ad">{len(_oranli)} kampanyada kâr payı oranı var</div>'
      '<div class="kl-kart-alt">Sıralanabilir olanlar bunlar; kalanında oran '
      "kaynakta yayımlanmamış.</div>",
      unsafe_allow_html=True,
    )
    if st.button("Karşılaştırma", key="gb_aksiyon_kiyas", use_container_width=True):
      st.switch_page("pages/1_Karşılaştırma.py")

with _a3:
  with st.container(border=True):
    st.markdown(
      f'<div class="kl-kart-ad">Önünüzdeki müşteriye teklif hazırlayın</div>'
      f'<div class="kl-kart-alt">{ozet["kampanya_sayisi"]} kampanya tutar, vade ve '
      "segment kısıtlarıyla süzülür.</div>",
      unsafe_allow_html=True,
    )
    if st.button("Müşteri Profili", key="gb_aksiyon_teklif", use_container_width=True):
      st.switch_page("pages/0_Müşteri_Profili.py")

st.divider()


# ---------------------------------------------------------------------------
# Üst göstergeler
# ---------------------------------------------------------------------------

s1, s2, s3, s4, s5 = st.columns(5)

# HER OLCU KENDINI ACIKLAR (27 Agu incelemesi, madde 2).
#
# «Ortalama guven 0,79» bir juri uyesine hicbir sey soylemez — neyin
# ortalamasi, neye gore guven? Sistemin en ozgun iddiasi seffaflik oldugu
# icin, olcunun kendisinin acik olmamasi iddiayi zayiflatiyordu. Aciklamalar
# hesabin TANIMINI veriyor, ovgu degil.
_faal_sayisi = sum(1 for b in bankalar if b.durum == BankaDurumu.FAAL)

s1.metric(
  "Kampanya", ozet["kampanya_sayisi"],
  help="Dokuz bankanın kampanya sayfalarından toplanıp yapısal alanlara "
       "çıkarılmış kayıt sayısı. Yinelenen ve içeriksiz sayfalar ayıklandı.",
)
s2.metric(
  "Banka (veri toplanan)", ozet["banka_sayisi"],
  help="Kampanya kaydı bulunan banka sayısı. Faaliyetteki katılım "
       f"bankalarının tamamı ({_faal_sayisi}) tarandı.",
)
s3.metric(
  "Kayıt defterindeki banka", len(bankalar),
  help=f"BDDK listesinin tamamı: {_faal_sayisi} faal banka ile henüz "
       f"faaliyete geçmemiş {len(bankalar) - _faal_sayisi} banka. "
       "Faaliyete geçmemiş bankaların sitesinde kampanya yoktur; "
       "aradaki fark bir veri eksikliği değildir.",
)
s4.metric(
  "Ortalama alan doluluğu", f"%{ozet['ortalama_doluluk'] * 100:.0f}",
  help="Bir kampanyada çıkarılabilen alanların kaçta kaçı gerçekten dolu — "
       "kayıt başına hesaplanıp ortalaması alınır. Düşük olması çıkarım "
       "zaafı değil, bankaların kampanya sayfasında az bilgi yayımlaması: "
       "kâr payı oranı çoğu bankada başvuru ekranının arkasında.",
)
s5.metric(
  "Ortalama güven", f"{ozet['ortalama_guven']:.2f}",
  help="Yalnız DOLU alanların güven skorlarının ortalaması (0–1). Her alan "
       "hangi katmandan geldiğini taşır: kural eşleşmesi mi, dil modeli mi, "
       "ikisinin uzlaşması mı. Boş alanlar bu ortalamaya girmez — girseydi "
       "veri azlığı güven düşüklüğü gibi görünürdü.",
)

son = ozet["son_guncelleme"]
st.caption(
  f"Son veri çekimi: **{son:%d.%m.%Y %H:%M}** · "
  f"Kayıt defterindeki {len(bankalar)} bankanın {_faal_sayisi}'i faal; "
  f"kalan {len(bankalar) - _faal_sayisi}'i henüz faaliyete geçmedi "
  "ve kampanya yayımlamıyor."
  if son
  else "Son çekim bilinmiyor"
)

st.divider()

# ---------------------------------------------------------------------------
# Piyasa ve Sistem Sekmeleri (B2B SaaS Görünümü)
# ---------------------------------------------------------------------------

tab_piyasa, tab_sistem = st.tabs(["Piyasa Görünümü", "Yapay Zeka Sistem Kalitesi"])

with tab_piyasa:
  sol, sag = st.columns(2)

  with sol:
    st.subheader("Kampanya türü dağılımı")
    dagilim = ozet["tur_dagilimi"]
    yeni_dagilim = {}
    for k, v in dagilim.items():
      temiz_k = format_kategori(k)
      yeni_dagilim[temiz_k] = yeni_dagilim.get(temiz_k, 0) + v
    dagilim = yeni_dagilim
    

    if dagilim:
      cerceve = pd.DataFrame(
        {"Tür": list(dagilim.keys()), "Adet": list(dagilim.values())}
      ).sort_values("Adet", ascending=True)
      dinamik_yukseklik_bar = max(380, len(cerceve) * 35)
      grafik = px.bar(cerceve, x="Adet", y="Tür", orientation="h", text="Adet", color_discrete_sequence=["#00A86B"])
      grafik.update_layout(height=dinamik_yukseklik_bar, margin={"l": 0, "r": 0, "t": 10, "b": 0}, template="plotly_dark")
      grafik.update_xaxes(showgrid=False)
      grafik.update_yaxes(showgrid=False)
      grafik.update_traces(
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Adet: %{x}<extra></extra>"
      )
      with st.container(height=min(500, dinamik_yukseklik_bar + 20)):
        st.plotly_chart(grafik, use_container_width=True, theme=None)
    else:
      st.info("Henüz sınıflandırma verisi yok.")

  with sag:
    st.subheader("Banka × Tür ısı haritası")
    
    gercek_kayitlar = [
      {"Banka": format_bank_name(k.banka_adi), "Tür": format_kategori(k.kampanya_turu)}
      for k in kayitlar
    ]
    
    tablo = pd.DataFrame(gercek_kayitlar)
    capraz = pd.crosstab(tablo["Banka"], tablo["Tür"])
    if not capraz.empty:
      dinamik_yukseklik_isi = max(380, len(capraz) * 35)
      # RENK SKALASI VE LEGEND (27 Agu incelemesi, madde 4).
      #
      # Viridis'te SIFIR koyu mor: dolu bir hucre gibi goruluyor ve gozun
      # «burada bir sey var» demesine yol aciyordu. Oysa sifir bilgi tasir —
      # o banka o turde kampanya YAYIMLAMAMIS. Simdi sifir zeminle ayni
      # notr gri, renk yalniz gercek farki tasiyor.
      #
      # Legend `r: 0` marjiyle kirpiliyordu; renk cubugu icin yer ayrildi.
      _notr_yesil = [
        [0.00, "#2A2A32"],
        [0.001, "#123D30"],
        [0.35, "#127050"],
        [1.00, "#00C77E"],
      ]
      isi = px.imshow(
        capraz, text_auto=True, aspect="auto", color_continuous_scale=_notr_yesil
      )
      isi.update_layout(
        height=dinamik_yukseklik_isi,
        margin={"l": 0, "r": 8, "t": 10, "b": 0},
        template="plotly_dark",
        coloraxis_colorbar={
          "title": {"text": "Kampanya", "side": "right"},
          "thickness": 12,
          "len": 0.92,
          "outlinewidth": 0,
        },
      )
      isi.update_xaxes(tickangle=-45)
      isi.update_traces(
        hovertemplate="Banka: <b>%{y}</b><br>Tür: %{x}<br>Adet: %{z}<extra></extra>"
      )
      with st.container(height=min(500, dinamik_yukseklik_isi + 20)):
        st.plotly_chart(isi, use_container_width=True, theme=None)

with tab_sistem:
  # ES-05 Veri Kalitesi ve Şeffaflık
  st.subheader("Veri Kalitesi ve Şeffaflık")
  st.caption(
    "Gerçek dünya verisi kusursuz değildir. Sistemimiz, veriyi olduğundan iyi göstermek yerine, "
    "kullanıcıyı hangi veriye ne kadar güvenebileceği konusunda şeffafça bilgilendirir."
  )

  eval_ozet = sonuclari_oku()
  k1, k2, k3 = st.columns(3)
  with k1:
    if eval_ozet.halusinasyon_orani is None:
      st.metric("Halüsinasyon oranı", "—", help="docs/SONUCLAR.md bulunamadı. `make eval` çalıştırın.")
    else:
      n_kamp = eval_ozet.kampanya_sayisi or ozet["kampanya_sayisi"]
      st.metric(
        "Halüsinasyon oranı",
        f"%{tr_sayi(eval_ozet.halusinasyon_orani * 100, 2)}",
        "hedef ≤ %3",
        help=(
          f"Ölçüm `make eval` / docs/SONUCLAR.md. "
          f"İşlenen kampanya: {n_kamp}. Bu sayı elle yazılmaz."
        ),
      )
  with k2:
    if eval_ozet.sema_gecerliligi is None:
      st.metric("Şema geçerliliği", "—")
    else:
      st.metric(
        "Şema geçerliliği",
        tr_sayi(eval_ozet.sema_gecerliligi, 2),
        "hedef 1,00",
        help="Her kayıt şema sözleşmesini geçti. Kaynak: docs/SONUCLAR.md.",
      )
  with k3:
    n_altin = eval_ozet.altin_set_n
    etiket = f"Makro-F1 (n={n_altin})" if n_altin else "Makro-F1"
    if eval_ozet.makro_f1 is None:
      st.metric(etiket, "—")
    else:
      delta = None
      if eval_ozet.makro_f1_ga:
        lo, hi = eval_ozet.makro_f1_ga
        delta = f"%95 GA: {tr_sayi(lo, 2)}–{tr_sayi(hi, 2)}"
      st.metric(
        etiket,
        tr_sayi(eval_ozet.makro_f1, 2),
        delta,
        help=(
          "Altın set, bootstrap güven aralığıyla. Hedef ≥ 0,78. "
          "Sunumda tek basamak iddia etme — aralık ve n ile söyle. "
          "Kaynak: docs/SONUCLAR.md."
        ),
      )
    if eval_ozet.sayisal_dogruluk is not None:
      st.caption(
        f"Sayısal alan doğruluğu: **{tr_sayi(eval_ozet.sayisal_dogruluk, 3)}** (hedef ≥ 0,90)"
      )

  st.write("") # Boşluk
  q1, q2 = st.columns(2)
  with q1:
    st.markdown("**Model Güven Skoru Dağılımı**")
    st.caption("Çıkarılan verilere duyulan güvenin dağılımı.")
    
    guvenler = [k.ortalama_guven for k in kayitlar if k.ortalama_guven > 0]
    if guvenler:
      hist_df = pd.DataFrame({"Güven Skoru": guvenler})
      fig_hist = px.histogram(hist_df, x="Güven Skoru", nbins=10, color_discrete_sequence=["#00A86B"])
      fig_hist.update_layout(height=300, margin={"l": 0, "r": 0, "t": 10, "b": 0}, xaxis_title="Güven Skoru", yaxis_title="Kampanya Adedi", bargap=0.1, template="plotly_dark")
      fig_hist.update_xaxes(showgrid=False)
      fig_hist.update_yaxes(showgrid=False)
      st.plotly_chart(fig_hist, use_container_width=True, theme=None)
    else:
      st.info("Güven skoru hesaplanabilen kampanya yok.")

  with q2:
    st.markdown("**Kritik Alan Doluluk Oranları (Eksik Veri Analizi)**")
    st.caption("Hangi alanın kaç kampanyada yayımlandığı. Eksiklik kaynakta, çıkarımda değil.")
    
    # Basitçe dolulukları veri yapısından sayıyoruz
    alan_doluluk = {
      "Kâr Payı": sum(1 for k in kayitlar if k.kar_payi_orani is not None),
      "Vade": sum(1 for k in kayitlar if k.vade_ay_max is not None),
      "Tahsis Ücreti": sum(1 for k in kayitlar if k.tahsis_ucreti is not None),
      "Hedef Kitle": sum(1 for k in kayitlar if k.hedef_kitle is not None),
      "Ürün Türü": sum(1 for k in kayitlar if k.urun_turu is not None),
    }
    toplam = len(kayitlar)
    if toplam > 0:
      doluluk_df = pd.DataFrame([
        {"Alan": k, "Doluluk (%)": (v / toplam) * 100}
        for k, v in alan_doluluk.items()
      ]).sort_values("Doluluk (%)", ascending=True)
      
      fig_bar = px.bar(doluluk_df, x="Doluluk (%)", y="Alan", orientation='h', text_auto='.0f', color_discrete_sequence=["#00A86B"])
      fig_bar.update_layout(height=300, margin={"l": 0, "r": 0, "t": 10, "b": 0}, xaxis_range=[0, 100], template="plotly_dark")
      fig_bar.update_xaxes(showgrid=False)
      fig_bar.update_yaxes(showgrid=False)
      st.plotly_chart(fig_bar, use_container_width=True, theme=None)
      belirtilmemis = {ad: toplam - say for ad, say in alan_doluluk.items()}
      st.caption(
        "Belirtilmemiş (kaynakta yok): "
        + " · ".join(f"{ad} {say}" for ad, say in belirtilmemis.items())
        + ". Ürün türü %0 ise model uydurmuyor; sayfalarda bu alan yazmıyor."
      )
    else:
      st.info("Hesaplanacak veri yok.")

st.divider()

# ---------------------------------------------------------------------------
# Banka kayıt defteri — şartname 5.1 kanıtı
# ---------------------------------------------------------------------------

st.subheader("Kapsanan bankalar")

# YALNIZ FAAL BANKALAR (27 Agustos). Defter eskiden 15 satirdi: 9 faal banka
# ile birlikte kurulus asamasindaki 4 ve faaliyete gecmemis 2 banka da
# listeleniyor, altisi da «Kampanya 0 · Site —» diye goruluyordu. Sifir
# satirlari tablonun uctebirini kaplayip okuyani «veri eksik mi?» diye
# dusundururken hicbir sey anlatmiyordu.
#
# Kayit defterinin TAMAMI silinmedi, yalniz suzuldu: sartname 5.1'in istedigi
# «BDDK listesinin tamami tarandi» kaniti yan taraftaki sayacta ve
# `data/banks.yaml` dosyasinda duruyor. Ust gostergelerdeki «Kayit
# defterindeki banka» rakami da 15 demeye devam ediyor.
faal_bankalar = [b for b in bankalar if b.durum == BankaDurumu.FAAL]

kampanya_sayaci: dict[str, int] = {}
for k in kayitlar:
  kampanya_sayaci[k.banka_kodu] = kampanya_sayaci.get(k.banka_kodu, 0) + 1

defter = pd.DataFrame(
  [
    {
      "Kod": {"0211": "0208", "0212": "0302"}.get(b.kod, b.kod),
      "Banka": b.ad,
      "Kampanya": kampanya_sayaci.get(b.kod, 0),
      "Site": b.site or "—",
    }
    for b in sorted(
      faal_bankalar, key=lambda b: kampanya_sayaci.get(b.kod, 0), reverse=True
    )
  ]
)
st.dataframe(defter, use_container_width=True, hide_index=True)

_kurulus = len(bankalar) - len(faal_bankalar)
st.caption(
  f"Faaliyetteki **{len(faal_bankalar)}** katılım bankasının tamamı tarandı. "
  f"BDDK listesindeki diğer {_kurulus} banka henüz faaliyete geçmedi; "
  "kampanya yayınlamadıkları için listede yer almıyor."
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

sayfa_sonu()
