"""Karşılaştırma ekranı — şartname 5.7'nin beş kriteri.

Her satırın altında açılır panel: tüm alanlar + güven skoru + KAYNAK ALINTISI
ve URL. Bankacılıkta izlenebilirlik olmadan hiçbir sistem kabul edilmez;
bu panel o izlenebilirliğin arayüzdeki karşılığıdır.
"""

from __future__ import annotations

import io
import datetime
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.comparison.karsilastirma import ( # noqa: E402
  KRITER_ETIKETLERI,
  Agirliklar,
  Kriter,
  avantaj_skorla,
  sirala,
  toplam_maliyet,
  uyarilar,
)
from src.depolama import tum_kayitlar # noqa: E402
from src.rag.chatbot import alan_goster  # noqa: E402
from src.schema import HedefKitle, Kampanya  # noqa: E402
from app.ui_utils import format_bank_name, inject_custom_css, format_kategori, ortak_kenar # noqa: E402

st.set_page_config(page_title="Karşılaştırma", page_icon="", layout="wide")
inject_custom_css()
ortak_kenar()
st.title("Bankalar Arası Karşılaştırma")

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
  secili_tur = st.selectbox("Ürün / kampanya türü", ["(tümü)", *turler], format_func=lambda x: format_kategori(x) if x != "(tümü)" else x)

with f2:
  bankalar = sorted({k.banka_adi for k in kayitlar})
  c_biz, c_onlar = st.columns([1, 2])
  with c_biz:
    benim_bankam = st.selectbox("Benim Bankam (Biz)", ["(Seçilmedi)"] + bankalar)
  with c_onlar:
    secili_bankalar = st.multiselect("Rakip Seti (Onlar)", bankalar, default=bankalar)

st.markdown("<br>", unsafe_allow_html=True)
with st.expander("Gelişmiş Filtreler (Piyasa Özeti)", expanded=False):
  c1, c2, c3 = st.columns(3)
  with c1:
    arama_metni = st.text_input("Serbest Metin Arama (Ad, içerik, avantaj)")
    
    hedef_kitleler = [h.value for h in HedefKitle]
    secili_hedef_kitle = st.multiselect("Hedef Kitle (Segment İzolasyonu)", hedef_kitleler)
  with c2:
    tarih_filtresi = st.date_input("Geçerlilik Tarihi (Bu tarihten önce bitenleri gizle)", value=datetime.date.today())
    
    min_guven = st.slider("Minimum Yapay Zeka Güven Skoru", 0.0, 1.0, 0.0, 0.05, help="Modelin çıkardığı verilere olan güvenini filtreler. %100 doğru çalışma için yüksek tutun.")
  with c3:
    sadece_masrafsiz = st.toggle("Yalnızca Masrafsız (Dosya masrafı yok)")
    tam_dolu_mu = st.toggle("Veri Bütünlüğü (Kritik alanları eksiksiz olanlar)", help="Kâr payı, vade gibi temel bilgileri 'Belirtilmemiş' olan kampanyaları gizler.")

suzulmus = []
gorulen_kampanyalar = set()
aktif_bankalar = set(secili_bankalar)
if benim_bankam != "(Seçilmedi)":
  aktif_bankalar.add(benim_bankam)

for k in kayitlar:
  if secili_tur != "(tümü)" and k.kampanya_turu != secili_tur:
    continue
  if k.banka_adi not in aktif_bankalar:
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
  dedup_key = (k.banka_adi, k.kampanya_turu, k.kaynak_url)
  if dedup_key not in gorulen_kampanyalar:
    gorulen_kampanyalar.add(dedup_key)
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
  
  st.info("**Vade Ağırlığı:** Vade ağırlığı sol kaydırıcıyla kullanıcı tarafından belirlenir. Farklı vadeli kampanyalar karşılaştırıldığında tablonun üzerinde otomatik uyarı çıkar ve karar toplam maliyete bırakılır.")

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

def _alan_yazi(kayit, alan_adi: str) -> str:
  """Sayısal alanı birimine göre yazar — tahsis hem TL hem yüzde olabilir."""
  deger = getattr(kayit, alan_adi, None)
  if deger is None:
    return "Belirtilmemiş"
  if isinstance(deger, bool):
    return "Evet" if deger else "Hayır"
  if isinstance(deger, (int, float)):
    birim = kayit.birim(alan_adi) if hasattr(kayit, "birim") else None
    return alan_goster(alan_adi, deger, birim)
  return str(deger)


def _csv_olustur(kayitlar):
  satirlar = []
  for k in kayitlar:
    satirlar.append({
      "Banka": format_bank_name(k.banka_adi),
      "Kampanya/Ürün": (k.urun_turu or k.kampanya_turu or "—").replace("_", " ").title(),
      "Hedef Kitle": k.hedef_kitle or "—",
      "Kâr Payı": _alan_yazi(k, "kar_payi_orani"),
      "Azami Vade": _alan_yazi(k, "vade_ay_max"),
      "Azami Tutar": _alan_yazi(k, "finansman_tutari_max"),
      "Tahsis Ücreti": _alan_yazi(k, "tahsis_ucreti"),
      "Güven Skoru": f"{k.ortalama_guven:.2f}",
      "Kaynak URL": k.kaynak_url,
      "Çekim Tarihi": k.cekim_tarihi.strftime("%Y-%m-%d %H:%M") if k.cekim_tarihi else "—"
    })
  df = pd.DataFrame(satirlar)
  return df.to_csv(index=False, sep=';').encode('utf-8-sig')


def _excel_html(kayitlar) -> bytes:
  """Excel'in açtığı HTML tablo — ek paket yok, on-prem uyumlu."""
  df = pd.read_csv(io.BytesIO(_csv_olustur(kayitlar)), sep=';')
  return (
    "<html><head><meta charset='utf-8'></head><body>"
    + df.to_html(index=False)
    + "</body></html>"
  ).encode("utf-8")

secili_kriter: Kriter = st.session_state.kriter

col_c, col_d, col_e = st.columns([2, 1, 1])
with col_c:
  st.caption(f"Sıralama ölçütü: **{KRITER_ETIKETLERI[secili_kriter]}**")
sirali_export = sirala(suzulmus, secili_kriter, agirliklar)
with col_d:
  st.download_button(
    label="CSV İndir",
    data=_csv_olustur(sirali_export),
    file_name="kampanyalar_export.csv",
    mime="text/csv",
    use_container_width=True
  )
with col_e:
  st.download_button(
    label="Excel İndir",
    data=_excel_html(sirali_export),
    file_name="kampanyalar_export.xls",
    mime="application/vnd.ms-excel",
    use_container_width=True
  )

sirali = sirala(suzulmus, secili_kriter, agirliklar)

for mesaj in uyarilar(sirali):
  st.warning(mesaj)

# ---------------------------------------------------------------------------
# Tablo
# ---------------------------------------------------------------------------

tablo = pd.DataFrame(
  [
    {
      "Banka": format_bank_name(k.banka_adi),
      "Tür": format_kategori(k.kampanya_turu),
      "Kâr payı": _alan_yazi(k, "kar_payi_orani"),
      "Azami vade": _alan_yazi(k, "vade_ay_max"),
      "Azami tutar": _alan_yazi(k, "finansman_tutari_max"),
      "Tahsis ücreti": _alan_yazi(k, "tahsis_ucreti"),
      "Masrafsız": _alan_yazi(k, "masrafsiz_mi"),
      "Ödül": _alan_yazi(k, "odul_miktari"),
      "Güven": f"{k.ortalama_guven:.2f}",
    }
    for k in sirali
  ]
)

# Tamamı 'Belirtilmemiş' olan sütunları gizle (Temiz Görünüm)
gizlenecek_sutunlar = []
for col in tablo.columns:
    if col not in ["Banka", "Tür", "Güven"]:
        if (tablo[col] == "Belirtilmemiş").all() or (tablo[col] == "—").all():
            gizlenecek_sutunlar.append(col)

if gizlenecek_sutunlar:
    tablo.drop(columns=gizlenecek_sutunlar, inplace=True)

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

def _highlight_biz(row):
  hedef_ad = format_bank_name(benim_bankam)
  if benim_bankam != "(Seçilmedi)" and row['Banka'] == hedef_ad:
    return ['background-color: rgba(46, 204, 113, 0.15)'] * len(row)
  return [''] * len(row)

# pandas >= 2.1 için map, eski sürümler için applymap
styler = tablo.style.apply(_highlight_biz, axis=1)
kar_sutun = ["Kâr payı"] if "Kâr payı" in tablo.columns else []
if hasattr(styler, "map"):
  styled_tablo = styler.map(_renklendir_guven, subset=["Güven"])
  if kar_sutun:
    styled_tablo = styled_tablo.map(_renklendir_kar, subset=kar_sutun)
else:
  styled_tablo = styler.applymap(_renklendir_guven, subset=["Güven"])
  if kar_sutun:
    styled_tablo = styled_tablo.applymap(_renklendir_kar, subset=kar_sutun)

st.dataframe(styled_tablo, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Yapay Zeka Battlecard (Biz vs Onlar)
# ---------------------------------------------------------------------------
if benim_bankam != "(Seçilmedi)" and sirali:
  st.subheader("Yapay Zeka Battlecard: Biz vs Onlar")
  st.caption(
    "Serbest metin özetidir — sayısal iddia tablodaki yapısal kayıtlardan gelir. "
    "Hava boşluğu demosunda EVREN yoksa bu düğme çalışmaz; sıra tabloda kalır."
  )
  st.warning(
    "Bu çıktı sayısal doğrulama kalkanından geçmez. Oran ve vade için yukarıdaki tabloyu kullanın."
  ) 
  if st.button("Battlecard Üret (EVREN API)"):
    biz_data = [k for k in sirali if format_bank_name(k.banka_adi) == format_bank_name(benim_bankam)]
    onlar_data = [k for k in sirali if format_bank_name(k.banka_adi) != format_bank_name(benim_bankam) and format_bank_name(k.banka_adi) in [format_bank_name(b) for b in secili_bankalar]]
    
    if not biz_data:
      st.warning(f"{benim_bankam} bankasına ait filtrelenmiş kampanya bulunamadı.")
    elif not onlar_data:
      st.warning("Karşılaştırma yapılacak Rakip Seti kampanyası bulunamadı.")
    else:
      with st.spinner("EVREN API analiz ediyor..."):
        import os
        from openai import OpenAI
        
        api_key = os.getenv("EVREN_API_ANAHTARI", "dummy_key")
        api_url = os.getenv("EVREN_TEMEL_URL", "https://evren-llmapi.ssyz.org.tr/v1")
        model_adi = os.getenv("LLM_MODEL", "llm-fast") 
        
        try:
          client = OpenAI(base_url=api_url, api_key=api_key)
          
          # Veriyi hazırlama
          biz_ozet = "\n".join([f"- Ürün: {k.urun_turu or k.kampanya_turu} | Kâr: {k.kar_payi_orani} | Vade: {k.vade_ay_max} | Tahsis: {k.tahsis_ucreti}" for k in biz_data])
          onlar_ozet = "\n".join([f"- Banka: {k.banka_adi} | Ürün: {k.urun_turu or k.kampanya_turu} | Kâr: {k.kar_payi_orani} | Vade: {k.vade_ay_max} | Tahsis: {k.tahsis_ucreti}" for k in onlar_data])
          
          prompt = f"""Sen kıdemli bir katılım bankacılığı ürün yöneticisisin. Aşağıdaki ürün özelliklerine dayanarak, "Bizim Bankamız"ın satış ekipleri için bir "Battlecard" (Rakip analiz kartı) hazırla.
          
Bizim Ürünlerimiz ({benim_bankam}):
{biz_ozet}

Rakip Ürünleri:
{onlar_ozet}

Lütfen analizini şu başlıklarla yap:
1. Bizim Üstün Olduğumuz Yönler (Avantajlar)
2. Rakiplerin Üstün Olduğu Yönler (Zayıflıklar)
3. Satış Stratejisi (Müşteriye ne söylemeliyiz?)

Sadece analizi ver, profesyonel bir B2B dili kullan."""

          response = client.chat.completions.create(
              model=model_adi,
              messages=[
                  {"role": "system", "content": "Sen kıdemli bir finansal analiz uzmanısın."},
                  {"role": "user", "content": prompt}
              ],
              temperature=0.3
          )
          st.success("Battlecard başarıyla üretildi!")
          st.markdown(f"> **Not:** {model_adi} modeli kullanıldı.")
          st.info(response.choices[0].message.content)
        except Exception as e:
          st.error(f"EVREN API'sine ulaşılamadı: {str(e)}")

# ---------------------------------------------------------------------------
# Avantaj skorunun dökümü
# ---------------------------------------------------------------------------

if secili_kriter == Kriter.EN_AVANTAJLI:
  with st.expander("«En Avantajlı» skoru nasıl hesaplandı?"):
    st.markdown(
      "Her kriter kendi içinde 0–1 aralığına ölçeklenir (min-maks "
      "normalizasyon), sonra yukarıdaki ağırlıklarla toplanır. "
      "Eksik veri nötr (0,5) sayılır ve *karşılaştırılabilirlik* oranı düşer.\n\n"
      "**Not:** Vade ağırlığı kullanıcı tarafından belirlenir; uzun vade tek başına avantaj "
      "sayılır, ama farklı vadeli ürünler için yukarıdaki uyarı çıkar ve karar toplam maliyete bırakılır."
    )
    for detay in avantaj_skorla(sirali, agirliklar):
      st.markdown(
        f"**{detay.banka_adi}** — {detay.aciklama()} \n"
        f"Karşılaştırılabilirlik: {detay.karsilastirilabilirlik:.2f}"
      )
else:
  with st.expander(f"«{KRITER_ETIKETLERI[secili_kriter]}» sıralaması nasıl yapıldı?"):
    st.markdown(
      "Bu sıralama, bankaların sağladığı spesifik veri alanı üzerinden "
      "saf matematiksel büyüklük/küçüklük kuralı (deterministik karşılaştırma motoru) "
      "kullanılarak yapılmıştır. Yapay zeka halüsinasyon riski tamamen sıfırlanmıştır.\n\n"
      "- **Kural 1 (Şeffaflık):** İlgili veriyi eksik ('Belirtilmemiş') sunan bankalar, "
      "karşılaştırılamaz oldukları için doğrudan **en alta** itilir.\n"
      "- **Kural 2 (Denge):** Eşit değerli kampanyalarda Python'un kararlı "
      "sıralama garantisi girdi sırasını korur — öngörülebilir, tekrarlanabilir sonuç."
    )

st.divider()

# ---------------------------------------------------------------------------
# Kanıt panelleri — her sayının kaynağı
# ---------------------------------------------------------------------------

st.subheader("Kayıt detayları ve kaynak kanıtı")

for kayit in sirali[:20]:
  baslik = (
    f"{format_bank_name(kayit.banka_adi)} — "
    f"{str(kayit.urun_turu or kayit.kampanya_turu or 'kampanya').replace('_', ' ').title()} "
    f"(doluluk %{kayit.doluluk_orani * 100:.0f})"
  )
  with st.expander(baslik):
    kampanya: Kampanya = kayit.kampanyaya_cevir()
    st.markdown(f"**Kaynak:** [{kayit.kaynak_url}]({kayit.kaynak_url})")
    st.markdown("---")
    st.caption(f"Çekim tarihi: {kayit.cekim_tarihi:%d.%m.%Y %H:%M}")

    for alan_adi, alan in kampanya.cikarilan_alanlar().items():
      if not alan.var_mi:
        continue
      c1, c2, c3 = st.columns([2, 2, 1])
      c1.markdown(f"**{alan_adi.replace('_', ' ').title()}**")
      c2.markdown(f"{alan.goster().replace('_', ' ').title() if hasattr(alan, 'deger') and isinstance(alan.deger, str) else alan.goster()}")
      c3.markdown(f"`{alan.yontem}` · {alan.guven:.2f}")
      if alan.kaynak and alan.kaynak.alinti:
        st.caption(f" Kaynak alıntısı: _{alan.kaynak.alinti[:280]}_")

    bos = [ad.replace('_', ' ').title() for ad, a in kampanya.cikarilan_alanlar().items() if not a.var_mi]
    if bos:
      st.caption(f"**Belirtilmemiş alanlar:** {', '.join(bos)}")
    
    # Geliştirici Modu açıksa, o kampanyanın ham JSON halini göster
    if st.session_state.get("dev_mode", False):
      st.markdown("---")
      st.caption("**API Yanıtı (JSON)**")
      st.json(kampanya.model_dump())

st.divider()

if st.session_state.get("dev_mode", False):
  st.subheader("Geliştirici Entegrasyonu (B2B API)")
  st.markdown("Aşağıdaki cURL komutuyla filtrelenmiş sonuçları gerçek API'den çekebilirsiniz (`make api` ile başlatın):")
  
  curl_cmd = f"""curl "http://localhost:8000/compare?kriter={secili_kriter.value}&limit=10"
"""
  st.code(curl_cmd, language="bash")
  st.divider()

# ---------------------------------------------------------------------------
# ES-08: Yan Yana Karşılaştırma ve Maliyet
# ---------------------------------------------------------------------------

st.subheader("Yan Yana Toplam Maliyet Karşılaştırması")
st.caption(
  "Eşit taksitli (annüite) ödeme planı. Katılım bankacılığında murabaha ile "
  "satış bedeli baştan sabitlenir; taksit hesabı matematiksel olarak aynıdır."
)

if not sirali:
  st.info("Karşılaştırılacak kampanya yok.")
else:
  # Kampanya Seçimi
  kampanya_secenekleri = {f"{format_bank_name(k.banka_adi)} - {format_kategori(k.urun_turu or k.kampanya_turu)}": k for k in sirali}
  secilen_adlar = st.multiselect(
    "Karşılaştırmak istediğiniz kampanyaları seçin (En fazla 3)",
    options=list(kampanya_secenekleri.keys()),
    default=list(kampanya_secenekleri.keys())[:2],
    max_selections=3
  )

  if secilen_adlar:
    h1, h2 = st.columns(2)
    ortak_anapara = h1.number_input("İhtiyaç Duyulan Finansman (TL)", min_value=1000.0, value=500_000.0, step=10_000.0)
    ortak_vade = h2.number_input("İstenen Vade (Ay)", min_value=1, value=120, step=6)
    
    st.write("") # Boşluk
    
    # Kartları yan yana diz
    cols = st.columns(len(secilen_adlar))
    
    maliyet_sonuclari = []
    for i, ad in enumerate(secilen_adlar):
      kayit = kampanya_secenekleri[ad]
      with cols[i]:
        st.markdown(f"### {format_bank_name(kayit.banka_adi)}")
        st.caption(format_kategori(kayit.urun_turu or kayit.kampanya_turu))
        
        # Veri eksikliği kontrolü
        if pd.isna(kayit.kar_payi_orani) or kayit.kar_payi_orani == "Belirtilmemiş":
          st.warning("Kâr payı verisi eksik olduğu için hesaplanamıyor.")
          maliyet_sonuclari.append(float('inf'))
          continue
          
        # 1. İş Mantığı Zırhı: Limit Kontrolleri
        limit_asti_mi = False
        if kayit.finansman_tutari_max and kayit.finansman_tutari_max != "Belirtilmemiş":
          if ortak_anapara > float(kayit.finansman_tutari_max):
            st.error(f"Bankanın belirlediği azami finansman limitini ({kayit.finansman_tutari_max:,.0f} TL) aşıyor.")
            limit_asti_mi = True
        
        if kayit.vade_ay_max and kayit.vade_ay_max != "Belirtilmemiş":
          if ortak_vade > float(kayit.vade_ay_max):
            st.error(f"Bankanın belirlediği azami vadeyi ({kayit.vade_ay_max:.0f} ay) aşıyor.")
            limit_asti_mi = True
            
        if limit_asti_mi:
          maliyet_sonuclari.append(float('inf'))
          continue
        
        # Limitleri geçti, hesapla
        tahsis = float(kayit.tahsis_ucreti) if (kayit.tahsis_ucreti and kayit.tahsis_ucreti != "Belirtilmemiş") else 0.0
        sonuc = toplam_maliyet(ortak_anapara, float(kayit.kar_payi_orani), int(ortak_vade), tahsis)
        maliyet_sonuclari.append(sonuc['toplam_geri_odeme'])
        
        st.metric("Aylık Taksit", f"{sonuc['aylik_taksit']:,.2f} TL".replace(",", "."))
        st.metric("Toplam Geri Ödeme", f"{sonuc['toplam_geri_odeme']:,.2f} TL".replace(",", "."))
        
        # Görsel Maliyet Dağılımı (Plotly Donut)
        df_donut = pd.DataFrame({
          "Kategori": ["Anapara", "Kâr Payı", "Masraflar"],
          "Tutar": [ortak_anapara, sonuc['toplam_kar_payi'], tahsis]
        })
        fig = px.pie(df_donut, values='Tutar', names='Kategori', hole=0.6, 
               color_discrete_sequence=['#1f77b4', '#aec7e8', '#ff7f0e'])
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=150)
        st.plotly_chart(fig, use_container_width=True)
        
    # Kazananı Vurgulama
    gecerli_maliyetler = [m for m in maliyet_sonuclari if m != float('inf')]
    if gecerli_maliyetler:
      en_dusuk_maliyet = min(gecerli_maliyetler)
      for i, ad in enumerate(secilen_adlar):
        if maliyet_sonuclari[i] == en_dusuk_maliyet:
          with cols[i]:
            st.success("**En Uygun Seçenek**")
            st.caption("Düşük kâr payı illüzyonuna düşmediniz; gizli masraflar dâhil cebinizden çıkacak en düşük tutar.")
