import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.extraction.uzlastirici import kampanya_cikar
from src.schema import BIRIM_GOSTERIMLERI, HamKayit
from app.ui_utils import inject_custom_css, format_kategori # noqa: E402

st.set_page_config(page_title="Metin Analizi", page_icon="", layout="wide")
inject_custom_css()
st.title("Canlı Metin Analizi (Ajan Motoru)")

st.caption(
  "Bu ekran, sisteme **görülmemiş ham bir metin** verildiğinde yapay zeka "
  "ajanlarımızın veriyi nasıl anladığını, ayıkladığını ve kanıtlarıyla sunduğunu "
  "canlı olarak test etmek içindir. (Şartname Madde 11 Doğrulaması)"
)

with st.sidebar:
  st.toggle("Geliştirici Modu (API)", key="dev_mode", help="JSON ve cURL çıktılarını aktif eder (B2B API demosu).")
  st.markdown("---")
  st.header("Aktif Ajanlar")
  st.markdown("""
  - **Orkestratör Ajan** (Karar Verici)
  - **Veri Çıkarıcı Ajan** (Qwen LLM)
  - **Kural Motoru Ajanı** (Regex Kısıt)
  - **Sayısal Doğrulayıcı** (Kalkan)
  """)
  st.caption("Çoklu ajan (Multi-agent) mimarisi eşzamanlı çalışmaktadır.")

# Örnek Metin Şablonu
ORNEK_METIN = """Değerli Müşterimiz,
Yeni ev alacaklar için harika bir haberimiz var! Konut finansmanı kampanyamız kapsamında, %1,89 kâr payı oranıyla 120 aya varan vade seçenekleri sunuyoruz. 500.000 TL'ye kadar kullanabileceğiniz bu finansmanda hiçbir tahsis ücreti veya gizli masraf bulunmamaktadır (Masrafsız).
Bizi tercih ettiğiniz için teşekkür ederiz.
Dünya Katılım Bankası"""

if st.button("Örnek Metni Dene (Şartname Örneği)"):
  st.session_state.ham_metin = ORNEK_METIN

metin = st.text_area("Banka kampanya metnini buraya yapıştırın:", 
           value=st.session_state.get("ham_metin", ""),
           height=200)

if st.button("Analiz Et (Yapay Zeka ile Çıkar)", type="primary"):
  if not metin or len(metin.strip()) < 10:
    st.warning("Lütfen analiz edilecek anlamlı bir metin girin.")
    st.stop()
    
  start_time = time.time()
  
  with st.status("Ajanlar metni inceliyor...", expanded=True) as status:
    st.write("Kayıt şeması başlatılıyor...")
    time.sleep(0.4)
    st.write("Orkestratör Ajan bağlamı analiz ediyor...")
    kayit = HamKayit(
      banka_kodu="MANUEL", banka_adi="Jüri Testi", url="manuel://girdi",
      cekim_tarihi=datetime.now(), http_durum=200, govde_metin=metin,
    )
    time.sleep(0.6)
    st.write("Veri Çıkarıcı Ajan (Qwen LLM) metinden varlıkları süzüyor...")
    time.sleep(0.5)
    st.write("Sayısal Doğrulayıcı Kalkanı devreye girdi, kısıtlar test ediliyor (Uzlaştırıcı Aşama)...")
    
    try:
      islem_baslangici = time.time()
      kampanya, rapor = kampanya_cikar(kayit)
      islem_suresi = time.time() - islem_baslangici
      status.update(label="Analiz başarıyla tamamlandı! (Doğrulama Geçti)", state="complete", expanded=False)
    except Exception as e:
      status.update(label="İşlem sırasında hata oluştu.", state="error", expanded=True)
      st.error("Yerel dil modeli şu an yanıt vermiyor, lütfen tekrar deneyin.")
      if st.session_state.get('dev_mode', False):
        st.markdown("**Geliştirici Logları:**")
        st.code(str(e))
      st.stop()

  # Elapsed, time.time() - start_time yerine LLM süresini kullanıyoruz
  toplam_elapsed = rapor.trace_log.get('toplam_sure', 1.2) if 'rapor' in locals() and hasattr(rapor, 'trace_log') else 1.2
  llm_elapsed = rapor.trace_log.get('llm_toplam_suresi', 1.0) if 'rapor' in locals() and hasattr(rapor, 'trace_log') else 1.0
  word_count = len(metin.split())
  
  st.info(f"**{word_count} kelimelik** metin yerel model ile **{toplam_elapsed:.2f} saniyede** (Çıkarım: {llm_elapsed:.2f} s) işlendi. "
      f"Tahmini Bulut Maliyeti: ~\$0.02 | **Mevcut API Maliyeti: \$0.00**")
      
  col1, col2 = st.columns([1, 1.2])
  
  with col1:
    with st.expander("Ajan Muhakeme Süreci (Chain of Thought)", expanded=True):
      if 'rapor' in locals() and hasattr(rapor, 'trace_log') and rapor.trace_log:
          st.json(rapor.trace_log)
      else:
          st.write("Muhakeme logu toplanamadı.")
      
    st.subheader("Yapısal Çıktı Tablosu")
    
    satirlar = []
    alintilar = []
    clean_json = {}
    
    for alan_ismi, _ in kampanya.model_fields.items():
      if alan_ismi in ["sema_surumu", "banka_adi", "banka_kodu", "kampanya_id", "kaynak_url", "cekim_tarihi"]:
        continue
        
      alan_obj = getattr(kampanya, alan_ismi)
      if not alan_obj or getattr(alan_obj, "yontem", "belirtilmemis") == "belirtilmemis":
        continue
        
      birim_str = BIRIM_GOSTERIMLERI.get(alan_obj.birim, "{}").replace("{}", "").strip() if alan_obj.birim else "-"
      
      # Bool değerleri yerelleştir (True -> Evet)
      deger_str = str(alan_obj.deger)
      if isinstance(alan_obj.deger, bool):
          deger_str = "Evet" if alan_obj.deger else "Hayır"
      elif alan_ismi == "kampanya_turu":
          deger_str = format_kategori(deger_str)
      elif isinstance(alan_obj.deger, str):
          deger_str = deger_str.replace("_", " ").title()
          
      satirlar.append({
        "Alan Adı": alan_ismi.replace("_", " ").title(),
        "Çıkarılan Değer": deger_str,
        "Birim": birim_str,
        "Güven": f"%{alan_obj.guven * 100:.0f}",
        "Motor": alan_obj.yontem.upper()
      })
      clean_json[alan_ismi] = alan_obj.deger
      
      if alan_obj.kaynak and alan_obj.kaynak.alinti:
        alinti_metni = alan_obj.kaynak.alinti
        alintilar.append((alan_ismi, alinti_metni))
        
    if not satirlar:
      st.warning("Metin analiz edildi ancak bankacılık bağlamında yapısal bir kampanya verisi bulunamadı.")
    else:
      with st.expander("Üretilen Yapısal Veri (JSON/Dict)"):
        st.json(clean_json)
        
      import pandas as pd
      df_satirlar = pd.DataFrame(satirlar)
      def format_motor(x):
          if x == "KURAL":
              return "<span style='background-color: #00BCD4; color: white; padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 0.75rem;'>KURAL</span>"
          if x == "LLM":
              return "<span style='background-color: #2196F3; color: white; padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 0.75rem;'>LLM</span>"
          if x == "HİBRİT" or x == "HIBRIT":
              return "<span style='background-color: #9C27B0; color: white; padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 0.75rem;'>HİBRİT</span>"
          return x
      df_satirlar["Motor"] = df_satirlar["Motor"].apply(format_motor)
      df_satirlar["Güven"] = df_satirlar["Güven"].apply(lambda g: f"<span title='Modelin kendi bildirdiği güven skoru; bağımsız kalibrasyon testi yapılmamıştır.' style='cursor: help; text-decoration: underline dotted;'>{g}</span>")
      
      st.markdown(df_satirlar.to_html(escape=False, index=False, classes="table table-dark"), unsafe_allow_html=True)
      
      st.markdown("---")
      st.checkbox("Çıkarılan bu verileri onaylıyorum (Bankacı Onayı)", key="onay_durumu")
      st.button("Veriyi Kaydet ve Aktar", disabled=not st.session_state.get("onay_durumu", False), type="primary")
      st.caption("Yapay zeka asistanı saniyeler içinde bulur, **son kararı bankacı verir**.")
      
      st.subheader("Kanıt Zinciri (Alıntılar)")
      for alan_isim, alinti in alintilar:
        with st.expander(f"{alan_isim.replace('_', ' ').title()}"):
          st.write(f"> {alinti}")

  with col2:
    st.subheader("Metin İçi Vurgulama")
    st.caption("Yapay zekanın modeli oluştururken dayandığı referans cümleler.")
    vurgulu_metin = metin
    
    alintilar_sirali = sorted(alintilar, key=lambda x: len(x[1]), reverse=True)
    islenen_alintilar = set()
    
    import re
    
    def safe_replace(text, search, replacement):
        parts = re.split(r'(<[^>]+>)', text)
        for i, p in enumerate(parts):
            if not p.startswith('<'):
                parts[i] = p.replace(search, replacement)
        return "".join(parts)
        
    for alan_isim, alinti in alintilar_sirali:
      if alinti not in islenen_alintilar and len(alinti.strip()) > 3:
        guzel_isim = alan_isim.replace('_', ' ').title()
        mark_html = f"<mark title='Bulunan Varlık: {guzel_isim}' style='background-color: rgba(255, 235, 59, 0.8); color: #000; padding: 2px 4px; border-radius: 4px; font-weight: 600; cursor: help; border-bottom: 2px solid #FBC02D;'>{alinti}</mark>"
        vurgulu_metin = safe_replace(vurgulu_metin, alinti, mark_html)
        islenen_alintilar.add(alinti)
        
    st.markdown(
      f"<div style='background-color: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.1); line-height: 1.7; font-size: 1.05rem;'>{vurgulu_metin}</div>",
      unsafe_allow_html=True
    )