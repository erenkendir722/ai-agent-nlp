"""Chatbot ekranı — kaynak gösteren, sayısal doğrulamadan geçen cevaplar.

Şartname madde 11'deki iki senaryo birebir desteklenir:
 Senaryo 1: "A Bankası'nın konut finansmanı oranı ne?"    -> tekil bilgi
 Senaryo 2: "A Bankası mı daha avantajlı, C Bankası mı?"   -> gerekçeli karşılaştırma
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ajanlar.orkestrator import Orkestrator # noqa: E402
from src.depolama import tum_kayitlar # noqa: E402
from src.rag.chatbot import YASAL_UYARI, Niyet # noqa: E402
from app.ui_utils import inject_custom_css, ortak_kenar, uyarilari_goster # noqa: E402

st.set_page_config(page_title="Chatbot", page_icon="", layout="wide")
inject_custom_css()
ortak_kenar(demo_ipuclari=True)
st.title("Kampanya Asistanı")

st.caption(
  "Sayısal cevaplar **her zaman yapısal veriden** gelir, serbest metin "
  "aramasından değil. Her cevap kaynağıyla birlikte sunulur ve sayısal "
  "doğrulama kalkanından geçer."
)

kayitlar = tum_kayitlar()
if not kayitlar:
  st.warning("Veritabanı boş. `make crawl && make extract` çalıştırın.")
  st.stop()

NIYET_ETIKETLERI = {
  Niyet.TEKIL_SORGU: ("①", "Tekil sorgu", "Yapısal veritabanı sorgusu"),
  Niyet.KARSILASTIRMA: ("②", "Karşılaştırma", "Deterministik karşılaştırma motoru"),
  Niyet.KOSUL_SORGUSU: ("③", "Koşul sorgusu", "Metin arama (RAG)"),
  Niyet.KORPUS_SORGUSU: ("④", "Veri seti sorgusu", "Korpus kapsamı — sayım"),
  Niyet.TANIM_SORGUSU: ("⑤", "Terim sorgusu", "Terim sözlüğü (şartname 5.5)"),
  Niyet.KAPSAM_DISI: ("⑥", "Kapsam dışı", "Kibar ret"),
}

ORNEK_SORULAR = [
  "Kuveyt Türk'ün konut finansmanı oranı ne?",
  "Hangi banka daha avantajlı?",
  "En uzun vade hangi bankada?",
  "Taşıt finansmanı sunan bankalar hangileri?",
  "Veri setinde kaç kampanya var?",
  "Kâr payı nedir?",
]
KALKAN_ORNEGI = "Kampanya koşulları neler?"

with st.sidebar:
  st.header("Örnek sorular")
  for ornek in ORNEK_SORULAR:
    if st.button(ornek, use_container_width=True):
      st.session_state.bekleyen_soru = ornek
  if st.button("Kalkan gösterimi: " + KALKAN_ORNEGI, use_container_width=True):
    st.session_state.bekleyen_soru = KALKAN_ORNEGI
  st.caption(
    "İlk dört soru yapısal yoldan cevaplanır. Son düğme kalkanı göstermek içindir "
    "(kırmızı kutu hata değil, uydurma sayının yayına çıkmamasıdır)."
  )

  st.divider()
  st.header("Mimari")
  st.markdown(
    """
```
Soru
 └─ Niyet Yönlendirici
   ├─ tekil_sorgu  SQLite yapısal sorgu
   ├─ karsilastirma karşılaştırma motoru
   ├─ kosul_sorgusu metin arama
   └─ kapsam_disi  kibar ret
 └─ SAYISAL DOĞRULAMA KALKANI
 └─ Kaynak ekleme
```
    """
  )
  st.markdown("---")

if "gecmis" not in st.session_state:
  st.session_state.gecmis = []

def cevap_renderla(cevap, gecen_sure=None):
  simge, etiket, aciklama = NIYET_ETIKETLERI[cevap.niyet]
  
  # Sayısal doğrulama kalkanı — bu yolda Eleştirmen Ajan yok.
  with st.expander("Ajanın Düşünce Süreci (Loglar)", expanded=False):
    st.caption(f"**Log 1:** Niyet anlaşıldı: `{etiket}` ({aciklama})")
    kaynak_sayisi = len(cevap.kaynaklar) if cevap.kaynaklar else 0
    st.caption(f"**Log 2:** SQLite veritabanından {kaynak_sayisi} ilgili kayıt getirildi.")
    if cevap.dogrulama_gecti:
      st.caption("**Log 3:** Sayısal doğrulama kalkanı geçti (yapısal kayıtta karşılığı olmayan sayı yok).")
    else:
      tekil = list(dict.fromkeys(cevap.reddedilen_sayilar))
      st.caption(
        f"**Log 3:** Sayısal doğrulama kalkanı reddetti. "
        f"Doğrulanamayan sayılar: {', '.join(tekil)}."
      )
    
  st.caption(f"{simge} **{etiket}** — {aciklama}")
  if gecen_sure is not None:
    if cevap.niyet in (Niyet.TEKIL_SORGU, Niyet.KARSILASTIRMA):
      motor = "LLM yok — yapısal sorgu / karşılaştırma motoru"
    elif cevap.niyet == Niyet.KOSUL_SORGUSU:
      motor = "Metin arama + sayısal kalkan"
    else:
      motor = "Kapsam dışı ret"
    st.caption(f"Yanıt {gecen_sure:.1f} saniyede · {motor}")

  st.markdown(cevap.metin)

  uyarilari_goster(cevap.uyarilar, baslik="Bu cevapla ilgili notlar")

  if cevap.dogrulama_gecti:
    st.success(
      "Sayısal doğrulama geçti — cevaptaki her sayının yapısal "
      "kayıtta karşılığı var."
    )
  else:
    st.error(
      f"Sayısal doğrulama başarısız. Doğrulanamayan değerler: "
      f"{', '.join(dict.fromkeys(cevap.reddedilen_sayilar))}. Cevap verilmedi."
    )

  if cevap.kaynaklar:
    st.markdown("**Kaynaklar**")
    for kaynak in cevap.kaynaklar:
      with st.container(border=True):
        st.markdown(f"**{kaynak.banka_adi}**")
        st.markdown(f"[Kaynağa git]({kaynak.url})")
        st.caption(f"Çekim tarihi: {kaynak.cekim_tarihi}")
        if kaynak.alinti:
          st.markdown(f"> {kaynak.alinti}")
    st.caption(f"_{YASAL_UYARI}_")


for girdi in st.session_state.gecmis:
  with st.chat_message("user"):
    st.markdown(girdi["soru"])
  with st.chat_message("assistant"):
    cevap_renderla(girdi["cevap"], girdi.get("gecen_sure"))

soru = st.chat_input("Kampanyalar hakkında bir soru sorun…")
if not soru and (bekleyen := st.session_state.pop("bekleyen_soru", None)):
  soru = bekleyen

if soru:
  with st.chat_message("user"):
    st.markdown(soru)

  with st.chat_message("assistant"):
    with st.spinner("Yapısal veri sorgulanıyor…"):
      baslangic = time.time()
      try:
        # ORKESTRATÖR ÜZERİNDEN (26 Ağustos). Doğrudan `sor()` çağrılırken
        # beşinci niyet (profil sorgusu) erişilemiyordu: «maaş müşterisi,
        # 800.000 TL, 10 yıl vade» sorusu muhakeme ajanına hiç gitmiyor,
        # `tekil_sorgu`ya düşüp müşterinin kısıtlarını yok sayıyordu.
        # `kayitlar` geçiriliyor ki chatbot aynı listeyi yeniden okumasın.
        cevap, iz_defteri = Orkestrator().calistir(soru, kayitlar=kayitlar)
        gecen_sure = time.time() - baslangic
      except ConnectionError as e:
        # Yerleşik ConnectionError — Ollama/vektör yolu kapalıyken yakalanır.
        # requests.exceptions.ConnectionError da bunun alt sınıfıdır.
        st.error("Yerel dil modeli sunucusuna (Ollama) veya vektör veritabanına şu anda erişilemiyor.")
        if st.session_state.get("dev_mode", False):
          with st.expander("Teknik Teşhis (Jüri / Geliştirici İçin)"):
            st.write("Bağlantı reddedildi. Docker container'ların veya yerel Ollama servisinin çalıştığından emin olun.")
            st.code(str(e))
        st.stop()
      except Exception as e:
        st.error("Bilinmeyen bir hata oluştu.")
        if st.session_state.get("dev_mode", False):
          with st.expander("Teknik Teşhis"):
            st.code(str(e))
        st.stop()

    cevap_renderla(cevap, gecen_sure)

    # AJAN İZLERİ — `ajanlar/temel.py`: "jüri ajan mimarisinin varlığını bizim
    # sözümüze değil, ekrandaki koşum kaydına bakarak görür". Panel 26 Ağustos'a
    # kadar hiç çizilmiyordu, çünkü izleri üreten orkestratör çağrılmıyordu.
    with st.expander(f"Ajan izleri — {iz_defteri.ozet()}", expanded=False):
      st.caption(
        "Her satır bir ajan koşusu. **motor** sütunu kritik: karşılaştırma, "
        "kısıt çözme ve sayısal kalkan deterministik KODDUR — aritmetiği "
        "dil modeline yaptırmıyoruz ve bu iddia burada denetlenebilir."
      )
      st.dataframe(
        [
          {
            "Ajan": iz.ajan_adi,
            "Motor": "LLM" if iz.llm_kullanildi else "kod",
            "Süre (ms)": iz.sure_ms,
            "Karar gerekçesi": iz.karar_gerekcesi,
          }
          for iz in iz_defteri.izler
        ],
        # `width="stretch"` DEĞİL — o API Streamlit 1.44'te geldi, burada
        # 1.40.1 pinli (requirements.txt) ve `width` int bekliyor. Yanlış tip
        # `TypeError` firlatiyordu ve istisna ajan izleri panelinde patladigi
        # icin CEVAP EKRANA BASILDIKTAN SONRA olusuyordu: kullanici cevabi
        # goruyor, altinda kirmizi hata kutusu goruyor ve `gecmis`e ekleme
        # satirina hic gelinmediginden sohbet gecmisi de kayboluyordu.
        use_container_width=True,
        hide_index=True,
      )
      if iz_defteri.llm_cagrisi_sayisi() == 0:
        st.success("Bu cevapta hiçbir ajan dil modeli çağırmadı.")

    # Geliştirici Modu (API)
    if st.session_state.get("dev_mode", False):
      st.markdown("---")
      st.subheader("Geliştirici Entegrasyonu (Chatbot API)")
      st.caption("**API Yanıt Özeti (JSON)**")
      st.json({
        "niyet": cevap.niyet,
        "metin": cevap.metin,
        "dogrulama_gecti": cevap.dogrulama_gecti,
        "reddedilen_sayilar": cevap.reddedilen_sayilar,
        "kaynak_sayisi": len(cevap.kaynaklar) if cevap.kaynaklar else 0
      })
      st.markdown("Aşağıdaki cURL komutuyla bu asistanı gerçek API üzerinden sorgulayabilirsiniz (`make api` ile başlatın):")
      curl_cmd = f"""curl -X POST "http://localhost:8000/ask" \\
 -H "Content-Type: application/json" \\
 -d '{{
    "soru": "{soru}"
   }}'
"""
      st.code(curl_cmd, language="bash")

  st.session_state.gecmis.append({"soru": soru, "cevap": cevap, "gecen_sure": gecen_sure})
