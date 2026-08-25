"""Canlı metin → yapısal çıktı — şartname madde 6 / 11.

Jüri metin yapıştırabilir. Kural katmanı anında, LLM katmanı spinner içinde.
Onay kutusu veritabanına yazmaz: jüri metni ambarı kirletmesin.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.extraction.uzlastirici import kampanya_cikar  # noqa: E402
from src.rag.chatbot import alan_goster  # noqa: E402
from src.schema import BIRIM_GOSTERIMLERI, HamKayit  # noqa: E402
from app.ui_utils import format_kategori, inject_custom_css, ortak_kenar  # noqa: E402

st.set_page_config(page_title="Metin Analizi", page_icon="", layout="wide")
inject_custom_css()
ortak_kenar()
st.title("Canlı Metin Analizi")

st.caption(
  "Görülmemiş ham metin → yapısal alanlar + kanıt alıntısı. "
  "Şartname madde 6 (metin girdisi + yapılandırılmış çıktı) ve madde 11."
)

with st.sidebar:
  st.header("Hibrit çıkarım")
  st.markdown(
    """
- **Kural motoru** — regex, milisaniye
- **LLM çıkarıcı** — Qwen (EVREN veya yerel Ollama)
- **Uzlaştırıcı** — iki katmanı birleştirir
- **Eleştirmen** — çıkarım hattında uydurma alanı düşürür
    """
  )
  st.caption("Sıra: önce kural (anında), sonra LLM. Eşzamanlı değil; hibrit görünür olsun diye.")

ORNEK_METIN = """Değerli Müşterimiz,
Yeni ev alacaklar için harika bir haberimiz var! Konut finansmanı kampanyamız kapsamında, %1,89 kâr payı oranıyla 120 aya varan vade seçenekleri sunuyoruz. 500.000 TL'ye kadar kullanabileceğiniz bu finansmanda hiçbir tahsis ücreti veya gizli masraf bulunmamaktadır (Masrafsız).
Bizi tercih ettiğiniz için teşekkür ederiz.
Dünya Katılım Bankası"""

if st.button("Örnek Metni Dene (Şartname Örneği)"):
  st.session_state.ham_metin = ORNEK_METIN

metin = st.text_area(
  "Banka kampanya metnini buraya yapıştırın:",
  key="ham_metin",
  height=200,
)

_ATLANAN = {
  "sema_surumu", "banka_adi", "banka_kodu", "kampanya_id",
  "kaynak_url", "cekim_tarihi",
}


def _deger_yazi(alan_ismi: str, alan_obj) -> str:
  deger = alan_obj.deger
  if isinstance(deger, bool):
    return "Evet" if deger else "Hayır"
  if alan_ismi == "kampanya_turu":
    return format_kategori(str(deger))
  if isinstance(deger, (int, float)):
    return alan_goster(alan_ismi, deger, alan_obj.birim)
  if isinstance(deger, str):
    return deger.replace("_", " ").title()
  return str(deger)


def _tablo_kur(kampanya):
  satirlar = []
  alintilar = []
  clean_json = {}
  for alan_ismi in kampanya.model_fields:
    if alan_ismi in _ATLANAN:
      continue
    alan_obj = getattr(kampanya, alan_ismi)
    if not alan_obj or getattr(alan_obj, "yontem", "belirtilmemis") == "belirtilmemis":
      continue
    birim_str = (
      BIRIM_GOSTERIMLERI.get(alan_obj.birim, "{}").replace("{}", "").strip()
      if alan_obj.birim else "—"
    )
    satirlar.append({
      "Alan": alan_ismi.replace("_", " ").title(),
      "Değer": _deger_yazi(alan_ismi, alan_obj),
      "Birim": birim_str or "—",
      "Güven": f"%{alan_obj.guven * 100:.0f}",
      "Yöntem": str(alan_obj.yontem).upper(),
    })
    clean_json[alan_ismi] = alan_obj.deger
    if alan_obj.kaynak and alan_obj.kaynak.alinti:
      alintilar.append((alan_ismi, alan_obj.kaynak.alinti))
  return satirlar, alintilar, clean_json


def _motor_rozet(x: str) -> str:
  renk = {"KURAL": "#00BCD4", "LLM": "#2196F3", "HİBRİT": "#9C27B0", "HIBRIT": "#9C27B0"}
  bg = renk.get(x, "#607D8B")
  return (
    f"<span style='background-color:{bg};color:white;padding:2px 6px;"
    f"border-radius:4px;font-weight:600;font-size:0.75rem;'>{x}</span>"
  )


def _sonucu_ciz(kampanya, rapor_iz, ham, baslik: str):
  st.subheader(baslik)
  satirlar, alintilar, clean_json = _tablo_kur(kampanya)
  if rapor_iz:
    with st.expander("Süre izi (ölçülen)", expanded=False):
      st.json(rapor_iz)
  if not satirlar:
    st.warning("Metin incelendi; yapısal kampanya alanı bulunamadı.")
    return
  col1, col2 = st.columns([1, 1.2])
  with col1:
    df = pd.DataFrame(satirlar)
    df["Yöntem"] = df["Yöntem"].map(_motor_rozet)
    df["Güven"] = df["Güven"].map(
      lambda g: (
        "<span title='Modelin kendi bildirdiği güven; bağımsız kalibrasyon yok.' "
        f"style='cursor:help;text-decoration:underline dotted;'>{g}</span>"
      )
    )
    st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)
    with st.expander("Yapısal JSON"):
      st.json(clean_json)
    st.caption("Jüri metni veritabanına yazılmaz. Bankacı onayı burada gösterim içindir.")
    st.subheader("Kanıt zinciri")
    for alan_isim, alinti in alintilar:
      with st.expander(alan_isim.replace("_", " ").title()):
        st.markdown(f"> {alinti}")
  with col2:
    st.subheader("Metin içi vurgu")
    vurgulu = ham

    def _safe_replace(text: str, search: str, replacement: str) -> str:
      parts = re.split(r"(<[^>]+>)", text)
      for i, p in enumerate(parts):
        if not p.startswith("<"):
          parts[i] = p.replace(search, replacement)
      return "".join(parts)

    for alan_isim, alinti in sorted(alintilar, key=lambda x: len(x[1]), reverse=True):
      if len(alinti.strip()) <= 3:
        continue
      guzel = alan_isim.replace("_", " ").title()
      mark = (
        f"<mark title='{guzel}' style='background-color:rgba(255,235,59,0.8);"
        f"color:#000;padding:2px 4px;border-radius:4px;font-weight:600;'>{alinti}</mark>"
      )
      vurgulu = _safe_replace(vurgulu, alinti, mark)
    st.markdown(
      f"<div style='background-color:rgba(255,255,255,0.05);padding:20px;"
      f"border-radius:8px;border:1px solid rgba(255,255,255,0.1);"
      f"line-height:1.7;'>{vurgulu}</div>",
      unsafe_allow_html=True,
    )


if st.button("Analiz Et", type="primary"):
  if not metin or len(metin.strip()) < 10:
    st.warning("Lütfen en az birkaç cümlelik bir kampanya metni girin.")
  else:
    kayit = HamKayit(
      banka_kodu="MANUEL",
      banka_adi="Jüri metni",
      url="manuel://girdi",
      cekim_tarihi=datetime.now(),
      http_durum=200,
      govde_metin=metin,
    )
    try:
      kampanya_kural, rapor_kural = kampanya_cikar(kayit, llm_kullan=False)
      st.session_state.analiz_kural = kampanya_kural
      st.session_state.analiz_kural_iz = getattr(rapor_kural, "trace_log", {})
      st.session_state.analiz_metin = metin
      with st.spinner("LLM katmanı çalışıyor (13–100 sn olabilir)…"):
        kampanya, rapor = kampanya_cikar(kayit, llm_kullan=True)
      st.session_state.analiz_kampanya = kampanya
      st.session_state.analiz_iz = getattr(rapor, "trace_log", {})
    except Exception as e:
      st.error("Dil modeli yanıt vermedi. EVREN veya yerel Ollama ayakta mı bakın.")
      if st.session_state.get("dev_mode", False):
        st.code(str(e))

ham = st.session_state.get("analiz_metin")
if ham:
  kelime = len(ham.split())
  iz = st.session_state.get("analiz_iz") or {}
  toplam = iz.get("toplam_sure")
  llm_s = iz.get("llm_toplam_suresi")
  parcalar = [f"**{kelime} kelime**"]
  if toplam is not None:
    parcalar.append(f"hibrit **{toplam:.2f} s**")
  if llm_s is not None:
    parcalar.append(f"LLM **{llm_s:.2f} s**")
  st.info(" · ".join(parcalar) + " · maliyet iddiası yok (on-prem / EVREN kotası)")

  if st.session_state.get("analiz_kural") is not None:
    with st.expander("1. Kural katmanı (anında)", expanded=False):
      _sonucu_ciz(
        st.session_state.analiz_kural,
        st.session_state.get("analiz_kural_iz"),
        ham,
        "Yalnız regex",
      )
  if st.session_state.get("analiz_kampanya") is not None:
    _sonucu_ciz(
      st.session_state.analiz_kampanya,
      iz,
      ham,
      "2. Hibrit sonuç (kural + LLM + uzlaştırıcı)",
    )
