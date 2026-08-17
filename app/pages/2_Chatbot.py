"""Chatbot ekranı — kaynak gösteren, sayısal doğrulamadan geçen cevaplar.

Şartname madde 11'deki iki senaryo birebir desteklenir:
  Senaryo 1: "A Bankası'nın konut finansmanı oranı ne?"        -> tekil bilgi
  Senaryo 2: "A Bankası mı daha avantajlı, C Bankası mı?"      -> gerekçeli karşılaştırma
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.depolama import tum_kayitlar  # noqa: E402
from src.rag.chatbot import YASAL_UYARI, Niyet, sor  # noqa: E402

st.set_page_config(page_title="Chatbot", page_icon="💬", layout="wide")
st.title("💬 Kampanya Asistanı")

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
    Niyet.TEKIL_SORGU: ("🎯", "Tekil sorgu", "Yapısal veritabanı sorgusu"),
    Niyet.KARSILASTIRMA: ("⚖️", "Karşılaştırma", "Deterministik karşılaştırma motoru"),
    Niyet.KOSUL_SORGUSU: ("📄", "Koşul sorgusu", "Metin arama (RAG)"),
    Niyet.KAPSAM_DISI: ("🚫", "Kapsam dışı", "Kibar ret"),
}

ORNEK_SORULAR = [
    "Kuveyt Türk'ün konut finansmanı oranı ne?",
    "Hangi banka daha avantajlı?",
    "En uzun vade hangi bankada?",
    "Kampanya koşulları neler?",
]

with st.sidebar:
    st.header("Örnek sorular")
    for ornek in ORNEK_SORULAR:
        if st.button(ornek, use_container_width=True):
            st.session_state.bekleyen_soru = ornek

    st.divider()
    st.header("Mimari")
    st.markdown(
        """
```
Soru
 └─ Niyet Yönlendirici
     ├─ tekil_sorgu   → SQLite yapısal sorgu
     ├─ karsilastirma → karşılaştırma motoru
     ├─ kosul_sorgusu → metin arama
     └─ kapsam_disi   → kibar ret
 └─ SAYISAL DOĞRULAMA KALKANI
 └─ Kaynak ekleme
```
        """
    )

if "gecmis" not in st.session_state:
    st.session_state.gecmis = []

for girdi in st.session_state.gecmis:
    with st.chat_message("user"):
        st.markdown(girdi["soru"])
    with st.chat_message("assistant"):
        st.markdown(girdi["cevap"])

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
                cevap = sor(soru, kayitlar)
                gecen_sure = time.time() - baslangic
            # `ollama` paketi yerleşik ConnectionError fırlatır, requests'inkini
            # DEĞİL — requests ile yakalamak bu dalı sessizce ölü bırakıyordu.
            except ConnectionError as e:
                st.error("Yerel dil modeli sunucusuna (Ollama) şu anda erişilemiyor.")
                with st.expander("Teknik Teşhis (Jüri / Geliştirici İçin)"):
                    st.write("Bağlantı reddedildi. Docker container'ların veya yerel Ollama servisinin çalıştığından emin olun.")
                    st.code(str(e))
                st.stop()
            except Exception as e:
                st.error("Bilinmeyen bir hata oluştu.")
                with st.expander("Teknik Teşhis"):
                    st.code(str(e))
                st.stop()

        simge, etiket, aciklama = NIYET_ETIKETLERI[cevap.niyet]
        st.caption(f"{simge} **{etiket}** — {aciklama}")
        st.caption(f"⏱️ Yanıt {gecen_sure:.1f} saniyede üretildi | Model: Yerel Qwen (Ollama) | Donanım: Yerel CPU/GPU")

        st.markdown(cevap.metin)

        for mesaj in cevap.uyarilar:
            st.warning(mesaj)

        if cevap.dogrulama_gecti:
            st.success(
                "✅ Sayısal doğrulama geçti — cevaptaki her sayının yapısal "
                "kayıtta karşılığı var."
            )
        else:
            st.error(
                f"⛔ Sayısal doğrulama başarısız. Doğrulanamayan değerler: "
                f"{', '.join(cevap.reddedilen_sayilar)}. Cevap verilmedi."
            )

        if cevap.kaynaklar:
            st.markdown("**Kaynaklar**")
            for kaynak in cevap.kaynaklar:
                with st.container(border=True):
                    st.markdown(f"**{kaynak.banka_adi}**")
                    st.caption(f"{kaynak.url}")
                    st.caption(f"Çekim tarihi: {kaynak.cekim_tarihi}")
                    if kaynak.alinti:
                        st.markdown(f"> {kaynak.alinti}")
            st.caption(f"_{YASAL_UYARI}_")

    st.session_state.gecmis.append({"soru": soru, "cevap": cevap.tam_metin()})
