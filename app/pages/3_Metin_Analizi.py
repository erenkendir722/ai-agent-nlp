import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.extraction.uzlastirici import kampanya_cikar
from src.schema import BIRIM_GOSTERIMLERI, HamKayit

st.set_page_config(page_title="Metin Analizi", page_icon="🔍", layout="wide")
st.title("🔍 Canlı Metin Analizi (Ajan Motoru)")

st.caption(
    "Bu ekran, sisteme **görülmemiş ham bir metin** verildiğinde yapay zeka "
    "ajanlarımızın veriyi nasıl anladığını, ayıkladığını ve kanıtlarıyla sunduğunu "
    "canlı olarak test etmek içindir. (Şartname Madde 11 Doğrulaması)"
)

# Örnek Metin Şablonu
ORNEK_METIN = """Değerli Müşterimiz,
Yeni ev alacaklar için harika bir haberimiz var! Konut finansmanı kampanyamız kapsamında, %1,89 kâr payı oranıyla 120 aya varan vade seçenekleri sunuyoruz. 500.000 TL'ye kadar kullanabileceğiniz bu finansmanda hiçbir tahsis ücreti veya gizli masraf bulunmamaktadır (Masrafsız).
Bizi tercih ettiğiniz için teşekkür ederiz.
Dünya Katılım Bankası"""

if st.button("📝 Örnek Metni Dene (Şartname Örneği)"):
    st.session_state.ham_metin = ORNEK_METIN

metin = st.text_area("Banka kampanya metnini buraya yapıştırın:", 
                     value=st.session_state.get("ham_metin", ""),
                     height=200)

if st.button("🚀 Analiz Et (Yapay Zeka ile Çıkar)", type="primary"):
    if not metin or len(metin.strip()) < 10:
        st.warning("Lütfen analiz edilecek anlamlı bir metin girin.")
        st.stop()
        
    start_time = time.time()
    
    with st.status("🤖 Ajanlar metni inceliyor...", expanded=True) as status:
        st.write("Kayıt şeması başlatılıyor...")
        kayit = HamKayit(
            banka_kodu="MANUEL", banka_adi="Jüri Testi", url="manuel://girdi",
            cekim_tarihi=datetime.now(), http_durum=200, govde_metin=metin,
        )
        st.write("Yerel LLM (Qwen) ve Kural Motoru çalıştırılıyor (Uzlaştırıcı Aşama)...")
        
        try:
            kampanya, rapor = kampanya_cikar(kayit)
            status.update(label="✅ Analiz başarıyla tamamlandı!", state="complete", expanded=False)
        except Exception as e:
            status.update(label="⛔ İşlem sırasında hata oluştu.", state="error", expanded=True)
            st.error("Yerel dil modeli yanıt vermedi (Ollama kapalı olabilir) veya beklenmedik bir çökme yaşandı.")
            with st.expander("Geliştirici Logları"):
                st.code(str(e))
            st.stop()

    elapsed = time.time() - start_time
    word_count = len(metin.split())
    
    st.info(f"⏱️ **{word_count} kelimelik** metin yerel model ile **{elapsed:.1f} saniyede** işlendi. "
            f"Bulut API kullanılsaydı ~$0.02 maliyet oluşacaktı | **Mevcut API Maliyeti: $0.00**")
            
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        st.subheader("📊 Yapısal Çıktı Tablosu")
        
        satirlar = []
        alintilar = []
        
        for alan_ismi, _ in kampanya.model_fields.items():
            if alan_ismi in ["sema_surumu", "banka_adi", "banka_kodu", "kampanya_id", "kaynak_url", "cekim_tarihi"]:
                continue
                
            alan_obj = getattr(kampanya, alan_ismi)
            if not alan_obj or getattr(alan_obj, "yontem", "belirtilmemis") == "belirtilmemis":
                continue
                
            birim_str = BIRIM_GOSTERIMLERI.get(alan_obj.birim, "{}").replace("{}", "").strip() if alan_obj.birim else "-"
            
            satirlar.append({
                "Alan Adı": alan_ismi.replace("_", " ").title(),
                "Çıkarılan Değer": str(alan_obj.deger),
                "Birim": birim_str,
                "Güven": f"%{alan_obj.guven * 100:.0f}",
                "Motor": alan_obj.yontem.upper()
            })
            
            if alan_obj.kaynak and alan_obj.kaynak.alinti:
                alintilar.append((alan_ismi, alan_obj.kaynak.alinti))
                
        if not satirlar:
            st.warning("Metin analiz edildi ancak bankacılık bağlamında yapısal bir kampanya verisi bulunamadı.")
        else:
            st.dataframe(satirlar, hide_index=True, use_container_width=True)
            
            st.markdown("---")
            st.checkbox("✅ Çıkarılan bu verileri onaylıyorum (Bankacı Onayı)")
            st.caption("Yapay zeka asistanı saniyeler içinde bulur, **son kararı bankacı verir**.")
            
            st.subheader("🔍 Kanıt Zinciri (Alıntılar)")
            for alan_isim, alinti in alintilar:
                with st.expander(f"📌 {alan_isim.replace('_', ' ').title()}"):
                    st.write(f"> {alinti}")

    with col2:
        st.subheader("✨ Metin İçi Vurgulama")
        st.caption("Yapay zekanın modeli oluştururken dayandığı referans cümleler.")
        vurgulu_metin = metin
        
        alintilar_sirali = sorted(alintilar, key=lambda x: len(x[1]), reverse=True)
        islenen_alintilar = set()
        
        for _, alinti in alintilar_sirali:
            if alinti not in islenen_alintilar and len(alinti.strip()) > 3:
                vurgulu_metin = vurgulu_metin.replace(
                    alinti, 
                    f"<mark style='background-color: rgba(39, 174, 96, 0.4); padding: 2px 4px; border-radius: 4px; font-weight: 500;'>{alinti}</mark>"
                )
                islenen_alintilar.add(alinti)
                
        st.markdown(
            f"<div style='background-color: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.1); line-height: 1.7; font-size: 1.05rem;'>{vurgulu_metin}</div>",
            unsafe_allow_html=True
        )