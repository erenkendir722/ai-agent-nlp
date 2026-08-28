"""Chatbot ekranı — kaynak gösteren, sayısal doğrulamadan geçen cevaplar.

Şartname madde 11'deki iki senaryo birebir desteklenir:
 Senaryo 1: "A Bankası'nın konut finansmanı oranı ne?"    -> tekil bilgi
 Senaryo 2: "A Bankası mı daha avantajlı, C Bankası mı?"   -> gerekçeli karşılaştırma

EKRAN DÜZENİ — 28 Ağustos'ta sadeleştirildi. Cevabın etrafında dört ayrı
kutu vardı (düşünce günlüğü · niyet satırı · süre satırı · yeşil doğrulama
kutusu) ve dördü de HER cevapta çıkıyordu. Her koşuda çıkan bir kutu bilgi
taşımaz, yalnız cevabı ekranın dışına iter. Kalanı tek satırlık çip:

    ① Tekil sorgu   ✓ Doğrulandı        <- ikisi de `title` ile açıklanır

Kaybolan hiçbir şey yok: motorun adı çipin ipucunda, ajan koşumu «Ajan
izleri» panelinde, kaynaklar açılır «Kaynaklar» kutusunda duruyor.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ajanlar.orkestrator import Orkestrator # noqa: E402
from src.rag.chatbot import YASAL_UYARI, Niyet # noqa: E402
from app.ui_utils import (  # noqa: E402
  en_alta_kaydir,
  gelistirici_anahtari,
  mimari_kenari,
  inject_custom_css,
  kayitlari_yukle,
  sayfa_gezinme,
  sayfa_sonu,
  uyarilari_goster,
)

st.set_page_config(page_title="Chatbot", page_icon="", layout="wide")
inject_custom_css()
gelistirici_anahtari()
sayfa_gezinme()
st.title("Kampanya Asistanı")

kayitlar = kayitlari_yukle()

# Üçüncü alan (açıklama) EKRANA YAZILMAZ, çipin `title` ipucunda durur:
# «Deterministik karşılaştırma motoru» cümlesi ilk cevapta bilgi, onuncuda
# gürültüdür. Merak eden imlecini götürür.
NIYET_ETIKETLERI = {
  Niyet.TEKIL_SORGU: ("①", "Tekil sorgu", "Yapısal veritabanı sorgusu"),
  Niyet.KARSILASTIRMA: ("②", "Karşılaştırma", "Deterministik karşılaştırma motoru"),
  Niyet.KOSUL_SORGUSU: ("③", "Koşul sorgusu", "Metin arama (RAG)"),
  Niyet.KORPUS_SORGUSU: ("④", "Veri seti sorgusu", "Korpus kapsamı — sayım"),
  Niyet.TANIM_SORGUSU: ("⑤", "Terim sorgusu", "Terim sözlüğü (şartname 5.5)"),
  Niyet.SISTEM_SORGUSU: ("⑥", "Sistem sorusu", "Dokümantasyon adresi — ret değil"),
  Niyet.KAPSAM_DISI: ("⑦", "Kapsam dışı", "Kibar ret"),
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

_BASLIK_SINIRI = 32


# ---------------------------------------------------------------------------
# Sohbetler — «sıfırla» yerine geçmiş
# ---------------------------------------------------------------------------
#
# Kenar çubuğunda «Sohbeti sıfırla» düğmesi ve altında dört satırlık bir
# açıklama vardı. Düğmenin yaptığı tek şey biriken sohbeti SİLMEKTİ; silmek
# bir özellik değil kayıptır — kullanıcı yeni bir konuya geçmek için önceki
# cevapları çöpe atmak zorunda kalıyordu.
#
# Yerine geçen model her sohbet arayüzünde aynı: birden çok sohbet, biri
# aktif. «Yeni sohbet» eskiyi ARŞİVLER, listeden tıklanınca geri gelir.
#
# YUVA DEVRİ SOHBET BAŞINA TUTULUR (ADR 022). `baglam` eskiden tek bir
# oturum anahtarıydı; sohbetler ayrılınca onun da ayrılması ZORUNLU, yoksa
# yeni sohbet önceki sohbetin bankasını devralırdı — «hafızası karışıyor»
# denen davranış tam olarak bu olurdu.
#
# Sözlük kullanılıyor, `@dataclass` DEĞİL: sayfa betiği her çizimde baştan
# koşar, burada tanımlanan bir sınıf her koşuda yeni bir nesne olur ve
# `st.session_state`'teki örnek eski sınıftan geldiği için `isinstance`
# false döner (CLAUDE.md — Streamlit sayfasında `@dataclass` tanımlama).


def _bos_sohbet() -> dict:
  return {"gecmis": [], "baglam": None}


if "sohbetler" not in st.session_state:
  st.session_state.sohbetler = [_bos_sohbet()]
  st.session_state.aktif_sohbet = 0

sohbetler = st.session_state.sohbetler
aktif_no = min(st.session_state.aktif_sohbet, len(sohbetler) - 1)
st.session_state.aktif_sohbet = aktif_no
aktif = sohbetler[aktif_no]


def _sohbet_basligi(sohbet: dict) -> str:
  """Sohbetin adı İLK SORUSUDUR — elle isim istemek gereksiz bir adım."""
  if not sohbet["gecmis"]:
    return "Yeni sohbet"
  ilk = " ".join(sohbet["gecmis"][0]["soru"].split())
  return ilk if len(ilk) <= _BASLIK_SINIRI else ilk[: _BASLIK_SINIRI - 1].rstrip() + "…"


with st.sidebar:
  if st.button(
    "＋  Yeni sohbet",
    use_container_width=True,
    type="primary",
    disabled=not aktif["gecmis"],
    help="Bu sohbet listede kalır; istediğinizde geri dönebilirsiniz.",
  ):
    sohbetler.append(_bos_sohbet())
    st.session_state.aktif_sohbet = len(sohbetler) - 1
    st.rerun()

  # BOŞ SOHBET HİÇ LİSTELENMEZ — aktif olan da (28 Ağustos).
  #
  # Aktif sohbet listeye giriyordu ve boşken adı «Yeni sohbet» oluyordu:
  # ekranda üstteki düğmeyle BİREBİR aynı yazıyı taşıyan ikinci bir satır.
  # Kullanıcı hangisinin gerçek düğme olduğunu ayırt edemiyordu; üstelik
  # o satıra tıklamak hiçbir şey yapmıyor (zaten oradasınız).
  #
  # Liste artık yalnız ADI OLAN sohbetleri taşır — adı ilk soru veriyor.
  # Aktif sohbet boşsa hiçbir satır vurgulu olmaz; nerede olduğunuzu boş
  # sohbet alanının kendisi zaten söylüyor.
  listelenecek = [
    (no, sohbet) for no, sohbet in enumerate(sohbetler) if sohbet["gecmis"]
  ]
  if listelenecek:
    st.caption("Sohbetler")
    for no, sohbet in reversed(listelenecek):
      if st.button(
        ("●  " if no == aktif_no else "○  ") + _sohbet_basligi(sohbet),
        key=f"cb_sohbet_{no}",
        use_container_width=True,
      ):
        st.session_state.aktif_sohbet = no
        st.rerun()

  st.divider()
  st.caption("Örnek sorular")
  for sira, ornek in enumerate(ORNEK_SORULAR):
    if st.button(ornek, key=f"cb_ornek_{sira}", use_container_width=True):
      st.session_state.bekleyen_soru = ornek
  if st.button(
    KALKAN_ORNEGI,
    key="cb_kalkan",
    use_container_width=True,
    help="Kalkan gösterimi: sistemin kendini nasıl frenlediğini gösterir.",
  ):
    st.session_state.bekleyen_soru = KALKAN_ORNEGI


def cevap_renderla(cevap) -> None:
  """Önce CEVAP, sonra tek satır künye. Sıra bilerek böyle.

  Eskiden ekranın en üstünde katlanmış bir günlük paneli, altında iki künye
  satırı, cevap ise onların altında duruyordu: kullanıcı cevabı okumak için
  önce sistemin kendi hakkında söylediklerini geçmek zorundaydı.
  """
  st.markdown(cevap.metin)

  simge, etiket, aciklama = NIYET_ETIKETLERI[cevap.niyet]
  cipler = [f'<span class="kl-cip" title="{aciklama}">{simge} {etiket}</span>']
  if cevap.dogrulama_gecti:
    cipler.append(
      '<span class="kl-cip kl-cip-onay" title="Cevaptaki her sayının yapısal '
      'kayıtta karşılığı bulundu; eşleşmeyen sayı olsaydı cevap verilmezdi.">'
      "✓ Doğrulandı</span>"
    )
  st.markdown(f'<div class="kl-meta">{"".join(cipler)}</div>', unsafe_allow_html=True)

  # BAŞARISIZLIK TAM BOY KALIR. Başarı her cevapta olur, bu seyrek ve
  # kritiktir: kullanıcı sayı görmediğinin farkında olmalı.
  if not cevap.dogrulama_gecti:
    st.error(
      "Sayısal doğrulama başarısız — cevap verilmedi. Doğrulanamayan "
      f"değerler: {', '.join(dict.fromkeys(cevap.reddedilen_sayilar))}."
    )

  uyarilari_goster(cevap.uyarilar, baslik="Bu cevapla ilgili notlar")

  # KAYNAKLAR AÇILIR PANELDE. Her cevabın altında üç kart açık duruyordu:
  # alıntılarıyla birlikte cevaptan uzun oluyor, ikinci soruyu ekranın
  # dışına itiyordu.
  #
  # `st.popover` DENENDİ, GERİ ALINDI: üstteki notlar `st.expander` ile
  # açılıyor ve iki kutu yan yana iki farklı biçimde açılınca aynı ekranda
  # iki ayrı etkileşim dili oluyordu — biri sayfayı iterek, diğeri üstüne
  # binerek. Aynı işi yapan iki öge aynı görünmeli.
  if cevap.kaynaklar:
    with st.expander(f"Kaynaklar ({len(cevap.kaynaklar)})", expanded=False):
      for sira, kaynak in enumerate(cevap.kaynaklar):
        if sira:
          st.divider()
        st.markdown(f"**{kaynak.banka_adi}** — [kaynağa git]({kaynak.url})")
        st.caption(f"Çekim tarihi: {kaynak.cekim_tarihi}")
        if kaynak.alinti:
          st.markdown(f"> {kaynak.alinti}")
      st.caption(f"_{YASAL_UYARI}_")


for girdi in aktif["gecmis"]:
  with st.chat_message("user"):
    st.markdown(girdi["soru"])
  with st.chat_message("assistant"):
    cevap_renderla(girdi["cevap"])

soru = st.chat_input("Kampanyalar hakkında bir soru sorun…")
if not soru and (bekleyen := st.session_state.pop("bekleyen_soru", None)):
  soru = bekleyen

if soru:
  with st.chat_message("user"):
    st.markdown(soru)

  with st.chat_message("assistant"):
    with st.spinner("Yapısal veri sorgulanıyor…"):
      try:
        # ORKESTRATÖR ÜZERİNDEN (26 Ağustos). Doğrudan `sor()` çağrılırken
        # beşinci niyet (profil sorgusu) erişilemiyordu: «maaş müşterisi,
        # 800.000 TL, 10 yıl vade» sorusu muhakeme ajanına hiç gitmiyor,
        # `tekil_sorgu`ya düşüp müşterinin kısıtlarını yok sayıyordu.
        # `kayitlar` geçiriliyor ki chatbot aynı listeyi yeniden okumasın.
        cevap, iz_defteri = Orkestrator().calistir(
          soru, kayitlar=kayitlar, baglam=aktif["baglam"]
        )
      except ConnectionError as e:
        # Yerleşik ConnectionError — Ollama/vektör yolu kapalıyken yakalanır.
        # requests.exceptions.ConnectionError da bunun alt sınıfıdır.
        st.error("Yerel dil modeli sunucusuna (Ollama) veya vektör veritabanına şu anda erişilemiyor.")
        if st.session_state.get("dev_mode", False):
          with st.expander("Teknik teşhis"):
            st.code(str(e))
        st.stop()
      except Exception as e:
        st.error("Bilinmeyen bir hata oluştu.")
        if st.session_state.get("dev_mode", False):
          with st.expander("Teknik teşhis"):
            st.code(str(e))
        st.stop()

    cevap_renderla(cevap)

    # AJAN İZLERİ — `ajanlar/temel.py`: "jüri ajan mimarisinin varlığını bizim
    # sözümüze değil, ekrandaki koşum kaydına bakarak görür". Panel 26 Ağustos'a
    # kadar hiç çizilmiyordu, çünkü izleri üreten orkestratör çağrılmıyordu.
    with st.expander(f"Ajan izleri — {iz_defteri.ozet()}", expanded=False):
      st.caption(
        "**Motor** sütunu: karşılaştırma, kısıt çözme ve sayısal kalkan "
        "deterministik KODDUR — aritmetik dil modeline yaptırılmaz."
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
        # Yeşil `st.success` kutusu değil: bu bir «işlem başarılı» bildirimi
        # değil, tablonun ÖZETİ. Kutu, altındaki tabloyla aynı şeyi iki kat
        # büyük söylüyordu.
        st.markdown(
          '<div class="kl-meta"><span class="kl-cip kl-cip-onay" title="Motor '
          'sütununun tamamı «kod»: aritmetik ve karşılaştırma dil modeline '
          'yaptırılmadı.">Bu cevapta dil modeli çağrısı yok</span></div>',
          unsafe_allow_html=True,
        )

    # Geliştirici Modu (API)
    if st.session_state.get("dev_mode", False):
      st.markdown("---")
      st.caption("**API yanıt özeti (JSON)** — aynı cevap `POST /ask` ucundan da alınır.")
      st.json({
        "niyet": cevap.niyet,
        "metin": cevap.metin,
        "dogrulama_gecti": cevap.dogrulama_gecti,
        "reddedilen_sayilar": cevap.reddedilen_sayilar,
        "kaynak_sayisi": len(cevap.kaynaklar) if cevap.kaynaklar else 0
      })
      curl_cmd = f"""curl -X POST "http://localhost:8000/ask" \\
 -H "Content-Type: application/json" \\
 -d '{{
    "soru": "{soru}"
   }}'
"""
      st.code(curl_cmd, language="bash")

  # BAĞLAM CEVAPTAN ALINIR, sorudan değil: devredilecek banka adı kullanıcının
  # yazdığı metinde değil, cevabın kullandığı kayıtlarda duruyor.
  aktif["baglam"] = cevap.baglam
  aktif["gecmis"].append({"soru": soru, "cevap": cevap})

# YENİ MESAJDAN SONRA EN ALTA (28 Ağustos). Sohbet uzayınca Streamlit
# kaydırmayı olduğu yerde bırakıyor: kullanıcı soru soruyor, cevap ekranın
# altında görünmeyen yere yazılıyor ve «cevap vermedi» sanılıyordu.
# İmza mesaj sayısı: içerik değişmezse bileşen yeniden çizilmez.
if aktif["gecmis"]:
  en_alta_kaydir(len(aktif["gecmis"]))

mimari_kenari("Arayüz")
sayfa_sonu()
