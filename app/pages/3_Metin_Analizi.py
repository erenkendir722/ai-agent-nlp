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
from src.schema import BIRIM_GOSTERIMLERI, METINSEL_ALANLAR, HamKayit  # noqa: E402
from app.ui_utils import (  # noqa: E402
  RENK_ANA,
  RENK_IKINCIL,
  format_alan_adi,
  format_kategori,
  inject_custom_css,
  gelistirici_anahtari,
  mimari_kenari,
  sayfa_gezinme,
  sayfa_sonu,
)

st.set_page_config(page_title="Metin Analizi", page_icon="", layout="wide")
inject_custom_css()
gelistirici_anahtari()
sayfa_gezinme()
st.title("Canlı Metin Analizi")

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
    # SERBEST METİN İŞARETİ. Bu alanlar müşteriye doğrudan söylenecek
    # cümleler ve çoğunu dil modeli üretir — sayısal alanlardan daha
    # riskliler. Liste ELLE YAZILMAZ: `METINSEL_ALANLAR` şemadan gelir.
    # İşaret eskiden yan yana karşılaştırma tablosundaydı; o tablo kalkınca
    # buraya taşındı, yoksa uyarı komple kaybolurdu.
    isaret = (
      " ⚠"
      if alan_ismi in METINSEL_ALANLAR
      and str(alan_obj.yontem).upper() != "KURAL"
      else ""
    )
    satirlar.append({
      "Alan": format_alan_adi(alan_ismi) + isaret,
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
  bg = MOTOR_RENKLERI.get(x, MOTOR_RENKLERI.get("HİBRİT") if x == "HIBRIT" else "#607D8B")
  return (
    f"<span style='background-color:{bg};color:white;padding:2px 6px;"
    f"border-radius:4px;font-weight:600;font-size:0.75rem;'>{x}</span>"
  )


# Rozet renkleri TEK YERDE (lejant ile tablo aynı kaynaktan okur — ikisi
# ayrışırsa lejant yalan söyler).
MOTOR_RENKLERI = {"KURAL": RENK_IKINCIL, "LLM": "#8E7CC3", "HİBRİT": RENK_ANA}


def _lejant() -> str:
    """Renklerin ne anlama geldiği (2. madde).

    Renk kodlaması vardı ama hiçbir yerde açıklanmıyordu: ilk kez bakan biri
    mavi ile morun farkını tahmin etmek zorundaydı. Renkler `MOTOR_RENKLERI`
    sözlüğünden geliyor, elle yazılmadı.
    """
    noktalar = "".join(
        f"<span style='display:inline-flex;align-items:center;gap:5px;"
        f"margin-right:14px;font-size:0.8rem;color:#B4B4BE;'>"
        f"<span style='width:9px;height:9px;border-radius:50%;"
        f"background:{renk};display:inline-block;'></span>{ad}</span>"
        for ad, renk in MOTOR_RENKLERI.items()
    )
    return (
        f"<div style='margin:2px 0 10px 0;'>{noktalar}</div>"
    )


def _guven_ipucu(yazi: str) -> str:
    """Güven hücresi — noktalı alt çizgi ve açıklama balonu.

    Düz alt çizgi «tıklanabilir bağlantı» izlenimi veriyordu; noktalı çizgi
    HTML'de kısaltma/açıklama işaretidir ve `cursor:help` tıklanamayacağını
    söyler.
    """
    return (
        "<span title='Modelin kendi bildirdiği güven; bağımsız kalibrasyon yok.' "
        "style='cursor:help;text-decoration:underline dotted;"
        f"text-underline-offset:3px;'>{yazi}</span>"
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
    df["Güven"] = df["Güven"].map(_guven_ipucu)
    st.markdown(_lejant(), unsafe_allow_html=True)
    st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)
    with st.expander("Yapısal JSON"):
      st.json(clean_json)
    st.caption("Bu metin veritabanına yazılmaz.")
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
      st.session_state.analiz_metin = metin
      with st.spinner("Kural motoru ve dil modeli çalışıyor (13–100 sn olabilir)…"):
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

  # SURE DOKUMU AYRISTIRILDI (5. madde). Eskiden «hibrit 3,45 s · LLM 3,45 s»
  # yaziyordu: iki sayi birebir ayni oldugu icin kural motorunun suresi
  # gorunmuyor, «milisaniye» iddiasi metinde kaliyordu. `kural_suresi` zaten
  # OLCULUYOR (`uzlastirici` trace'i) — yalnizca ekrana yazilmiyordu.
  kural_s = iz.get("kural_suresi")
  llm_s = iz.get("llm_toplam_suresi")
  toplam = iz.get("toplam_sure")

  def _sure(saniye: float) -> str:
    return f"{saniye * 1000:.0f} ms" if saniye < 1 else f"{saniye:.2f} s"

  parcalar = [f"**{kelime} kelime**"]
  if kural_s is not None:
    parcalar.append(f"kural **{_sure(kural_s)}**")
  if llm_s is not None:
    parcalar.append(f"dil modeli **{_sure(llm_s)}**")
  if toplam is not None:
    parcalar.append(f"toplam **{_sure(toplam)}**")
  st.info(" · ".join(parcalar))

  hibrit_k = st.session_state.get("analiz_kampanya")
  if hibrit_k is not None:
    st.divider()
    _sonucu_ciz(hibrit_k, iz, ham, "Kural + dil modeli + uzlaştırıcı")

mimari_kenari("Çıkarım")
sayfa_sonu()
