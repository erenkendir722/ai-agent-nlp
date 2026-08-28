"""Banka Profili — tek bir banka hakkında elimizdeki her şey.

NEDEN VAR:
    Beş ekran vardı; hepsi ya kampanya-merkezli ya karşılaştırma-merkezli.
    «Kuveyt Türk hakkında her şeyi göster» diyen bir kullanıcı hiçbir yerde
    cevap bulamıyordu — ne kaç kampanyası var, ne verisi ne zaman çekildi,
    ne hangi kampanyası bu hafta bitiyor.

    Bu sayfa yeni çıkarım YAPMAZ. Tamamı mevcut veriden türetilir; katkısı
    dağınık duran bilgiyi tek bakışta toplamak.

ÜÇ ŞEYİ BİLEREK ÖNE ÇIKARIR:

1. VERİ TAZELİĞİ. Tazelik bankadan bankaya değişiyor (ölçüldü: en eski
   19 Ağustos, en yeni 24 Ağustos) ama diğer ekranlar hepsini eşit tazelikte
   gösteriyordu. Projenin tüm anlatısı dürüstlük üzerine kurulu; bunu
   göstermemek o anlatıdaki tek boşluktu.

2. YAKINDA BİTEN KAMPANYALAR. Ölçüldü: bitiş tarihi olan 361 kampanyanın
   111'i yedi gün içinde bitiyor ve sistem bunu kimseye söylemiyordu.
   Rakip kampanyasının Cuma günü bittiğini bilmek, elimizdeki en aksiyon
   alınabilir bilgi.

3. NEYİ BİLMİYORUZ. Alan doluluğu banka bazında gösterilir. «Kâr payı oranı
   %84 kayıtta yok» cümlesi bir kusur itirafı değil, ölçüm: bankaların çoğu
   oranı kampanya sayfasında yayımlamıyor.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.comparison.karsilastirma import OLCUT_KAPSAMI  # noqa: E402
from src.schema import ALAN_ADLARI, alan_etiketi  # noqa: E402
from app.ui_utils import (  # noqa: E402
  RENK_ANA,
  RENK_IKINCIL,
  disa_aktar,
  format_bank_name,
  grafik_duzeni,
  format_kategori,
  inject_custom_css,
  kayitlari_yukle,
  gelistirici_anahtari,
  sayfa_gezinme,
  sayfa_sonu,
  tr_sayi,
)

st.set_page_config(page_title="Banka Profili", page_icon="", layout="wide")
inject_custom_css()
gelistirici_anahtari()
sayfa_gezinme()

st.title("Banka Profili")
st.markdown(
  '<div class="kl-serit">Tek bir banka hakkında elimizdeki her şey.</div>',
  unsafe_allow_html=True,
)

# Bu eşiğin altındaki kampanyalar «yakında bitiyor» sayılır.
YAKIN_GUN = 7


kayitlar = kayitlari_yukle()


# SATIR NESNESİ ŞEMANIN TAMAMI DEĞİL (28 Ağustos).
#
# `tum_kayitlar()` `KampanyaKaydi` döndürür: sorgulanabilir sütunlar. Üç
# METİNSEL alan (`kampanya_avantaji` · `kampanya_kosullari` ·
# `masraf_bilgisi`) sütun taşımaz, JSON kanıt zincirinde (`tam_kayit`)
# durur. Bu sayfa ikisini karıştırıyordu ve iki ayrı kusur üretiyordu:
#
#   1. Vurgu kartı `_vurgu.kampanya_avantaji` okuyup AttributeError ile
#      çöküyordu. Görünmez kalmasının sebebi başka bir hataydı: «Detay»
#      yanlış bankayı açtığı için vurgulanan kayıt hiç bulunamıyor, blok
#      hiç koşmuyordu. Banka seçimi düzelince bu ortaya çıktı.
#   2. «Alan doluluğu» grafiği `getattr(k, alan, None)` kullanıyordu —
#      olmayan alan sessizce `None` döner, yani üç metinsel alan HER
#      BANKADA %0 çiziliyordu. Ölçüldü: Ziraat'in 219 kaydının 170'inde
#      `kampanya_avantaji` DOLU. Grafik dolu veriyi boş gösteriyordu.
#
# Çözüm tek: doluluk `Kampanya` nesnesinden `var_mi` ile okunur. Bedeli
# ölçüldü — en kalabalık bankada (219 kayıt) 8 ms.
@st.cache_data(ttl=60, show_spinner=False)
def _sema_nesneleri(kampanya_idleri: tuple[str, ...]):
  """Satırları tam şema nesnesine çevirir. Anahtar id'ler — önbellek tutar."""
  dizin = {k.kampanya_id: k for k in kayitlar}
  return {kid: dizin[kid].kampanyaya_cevir() for kid in kampanya_idleri if kid in dizin}


# ---------------------------------------------------------------------------
# Banka seçimi — ana alanın üstünde
# ---------------------------------------------------------------------------

bankalar = sorted({k.banka_adi for k in kayitlar})

# GENEL BAKIŞ'TAN GELEN SEÇİM.
#
# O sayfadaki banka düğmesi `bp_secili_banka` anahtarını yazıp buraya
# yönlendiriyor; aşağıdaki `st.selectbox` aynı anahtarı kullandığı için
# Streamlit değeri seçili kabul eder.
#
# Doğrulama şart: veri değişip banka listeden düştüyse (yeniden çıkarım,
# kayıt silme) Streamlit «seçenek listede yok» diye HATA fırlatır ve sayfa
# hiç açılmaz. Geçersiz değer sessizce düşürülür, ilk banka gösterilir.
if st.session_state.get("bp_secili_banka") not in bankalar:
  st.session_state.pop("bp_secili_banka", None)

with st.container(border=True):
  s1, s2 = st.columns([3, 2])
  secili = s1.selectbox(
    "Banka", options=bankalar, format_func=format_bank_name, key="bp_secili_banka"
  )

banka = [k for k in kayitlar if k.banka_adi == secili]
if not banka:
  st.info("Bu bankaya ait kayıt bulunamadı.")
  st.stop()


def _gun_farki(deger) -> int | None:
  """Bugüne göre kaç gün kaldı. Geçmişse negatif."""
  if deger is None:
    return None
  ham = str(deger)[:10]
  try:
    return (date.fromisoformat(ham) - date.today()).days
  except ValueError:
    return None


def _tazelik_gun() -> int | None:
  tarihler = [k.cekim_tarihi for k in banka if k.cekim_tarihi]
  if not tarihler:
    return None
  en_yeni = max(tarihler)
  if isinstance(en_yeni, datetime):
    en_yeni = en_yeni.date()
  return (date.today() - en_yeni).days


# ---------------------------------------------------------------------------
# Üst göstergeler
# ---------------------------------------------------------------------------

# KÂR PAYI ARALIĞI YALNIZ FİNANSMAN KAMPANYALARINDAN (28 Ağustos).
#
# Ölçü «%0,00 – %4,82» diye çıkıyordu ve dokuz bankanın dokuzunda alt sınır
# sıfırdı. Sebep ADR 020'de yazılı: `kar_payi_orani` dolu kayıtların çoğu
# kart/alışveriş kampanyası ve neredeyse hepsi sıfır («vade farksız 6
# taksit»). O sıfır DOĞRU bir veridir, yanlış olan onu bir ihtiyaç
# finansmanının oranıyla aynı aralığa sokmaktı.
#
# Kapı `karsilastirma.OLCUT_KAPSAMI` — sıralama, avantaj skoru ve chatbot
# aynı kapıdan geçiyor; burada ikinci bir eşik YAZILMAZ. Ölçüldü, kapı üç
# bankada aralığı düzeltti: TOM %0,00–%1,99 → %1,99 · Emlak %0,00–%1,69 →
# %1,69 · Vakıf %0,00–%3,47 → %3,45–%3,47.
_KAPSAM = OLCUT_KAPSAMI.get("kar_payi_orani", frozenset())
oranlar = [
  k.kar_payi_orani for k in banka
  if k.kar_payi_orani is not None and k.kampanya_turu in _KAPSAM
]


def _oran_yazi(deger: float) -> str:
  """Tam sıfırda ondalık YAZILMAZ: «%0,00» bozuk bir alan gibi okunuyor."""
  return "%0" if deger == 0 else f"%{tr_sayi(deger)}"
vadeler = [k.vade_ay_max for k in banka if k.vade_ay_max is not None]
masrafsizlar = [k for k in banka if k.masrafsiz_mi]
pay = len(banka) / len(kayitlar) * 100
tazelik = _tazelik_gun()

u1, u2, u3, u4 = st.columns(4)
u1.metric("Kampanya", len(banka))

if not oranlar:
  u2.metric("Finansman kâr payı", "Belirtilmemiş")
  u2.caption("Finansman kampanyasında oran yayımlanmamış")
elif min(oranlar) == max(oranlar):
  # Tek değerde «%1,69 – %1,69» yazmak aralık olmayan şeyi aralık gösterir.
  u2.metric("Finansman kâr payı", _oran_yazi(oranlar[0]))
  u2.caption(f"{len(oranlar)} finansman kampanyası")
else:
  u2.metric(
    "Finansman kâr payı",
    f"{_oran_yazi(min(oranlar))} – {_oran_yazi(max(oranlar))}",
  )
  _sifirli = sum(1 for o in oranlar if o == 0)
  u2.caption(
    f"{_sifirli} kampanyada kâr payı yok" if _sifirli
    else f"{len(oranlar)} finansman kampanyası"
  )

if vadeler:
  u3.metric("En uzun vade", f"{max(vadeler)} ay")
else:
  u3.metric("En uzun vade", "Belirtilmemiş")

u4.metric("Masrafsız kampanya", len(masrafsizlar))

# VERİ TAZELİĞİ — diğer ekranlarda hiç görünmüyordu.
if tazelik is not None and tazelik > 3:
  st.markdown(
    f'<div class="kl-not">Veri <b>{tazelik} gün</b> önce çekildi — banka '
    "sayfası o tarihten sonra değişmiş olabilir.</div>",
    unsafe_allow_html=True,
  )

st.divider()


# ---------------------------------------------------------------------------
# Yakında biten kampanyalar
# ---------------------------------------------------------------------------

bitenler = []
for k in banka:
  kalan = _gun_farki(k.kampanya_bitis)
  if kalan is not None and 0 <= kalan <= YAKIN_GUN:
    bitenler.append({
      "Kampanya": format_kategori(k.urun_turu or k.kampanya_turu),
      "Bitiş": str(k.kampanya_bitis)[:10],
      "Kalan": f"{kalan} gün" if kalan else "bugün",
      "Kaynak": k.kaynak_url,
    })

if bitenler:
  bitenler.sort(key=lambda s: s["Bitiş"])
  st.subheader(f"Yakında biten kampanyalar ({YAKIN_GUN} gün)")
  st.dataframe(
    pd.DataFrame(bitenler),
    use_container_width=True,
    hide_index=True,
    column_config={"Kaynak": st.column_config.LinkColumn("Kaynak", display_text="sayfaya git")},
  )
  st.divider()


# ---------------------------------------------------------------------------
# Dağılımlar
# ---------------------------------------------------------------------------

sol, sag = st.columns(2)

with sol:
  st.subheader("Kampanya türleri")
  turler: dict[str, int] = {}
  for k in banka:
    ad = format_kategori(k.kampanya_turu)
    turler[ad] = turler.get(ad, 0) + 1
  cizim = pd.DataFrame({"Tür": list(turler), "Adet": list(turler.values())})
  _tur_grafik = grafik_duzeni(
    px.bar(
      cizim.sort_values("Adet"), x="Adet", y="Tür", orientation="h",
      text="Adet", color_discrete_sequence=[RENK_ANA],
    ),
    yukseklik=max(300, len(cizim) * 34),
  )
  # İPUCU AÇIKÇA YAZILIR: plotly'nin üretttiği varsayılan şablon sütun
  # adlarını ham hâliyle basıyor ve `text` alanına bağlandığında imlecin
  # altında tanımsız değer gösterebiliyordu.
  _tur_grafik.update_traces(
    textposition="outside",
    hovertemplate="<b>%{y}</b><br>Kampanya: %{x}<extra></extra>",
  )
  _tur_grafik.update_layout(xaxis_title=None, yaxis_title=None)
  st.plotly_chart(_tur_grafik, use_container_width=True, theme=None)

with sag:
  st.subheader("Alan doluluğu")
  _nesneler = _sema_nesneleri(tuple(k.kampanya_id for k in banka))
  satirlar = []
  for alan in ALAN_ADLARI:
    dolu = sum(1 for n in _nesneler.values() if getattr(n, alan).var_mi)
    satirlar.append({"Alan": alan_etiketi(alan) or alan, "Doluluk": dolu / len(banka) * 100})
  doluluk = pd.DataFrame(satirlar).sort_values("Doluluk")
  _doluluk_grafik = grafik_duzeni(
    px.bar(
      doluluk, x="Doluluk", y="Alan", orientation="h",
      color_discrete_sequence=[RENK_IKINCIL],
    ),
    yukseklik=max(300, len(doluluk) * 26),
  )
  _doluluk_grafik.update_layout(xaxis_range=[0, 100], xaxis_title=None, yaxis_title=None)
  _doluluk_grafik.update_traces(
    hovertemplate="<b>%{y}</b><br>Doluluk: %{x:.0f}%<extra></extra>"
  )
  st.plotly_chart(_doluluk_grafik, use_container_width=True, theme=None)

st.divider()


# ---------------------------------------------------------------------------
# Kampanya listesi
# ---------------------------------------------------------------------------

st.subheader(f"Kampanyalar ({len(banka)})")

# MUSTERI PROFILI'NDEN GELEN KAMPANYA (27 Agustos). O ekrandaki «Detay»
# dugmesi `bp_vurgu_kampanya` anahtarini yazip buraya yonlendiriyor. Kullanici
# tek bir kampanyanin detayini istedi; onu 183 satirlik tablonun icinde
# aratmak, dugmenin verdigi sozu tutmamak olur.
#
# Anahtar OKUNUR OKUNMAZ SILINIR: kalici olsaydi kullanici bankayi elle
# degistirdiginde alakasiz bir kampanya vurgulu kalirdi.
_vurgu_id = st.session_state.pop("bp_vurgu_kampanya", None)
_vurgu = next((k for k in banka if k.kampanya_id == _vurgu_id), None) if _vurgu_id else None

if _vurgu is not None:
  with st.container(border=True):
    st.markdown(
      "<div class='kl-kart-ad'>Müşteri Profili'nden seçilen kampanya"
      "<span class='kl-rozet'>seçili</span></div>",
      unsafe_allow_html=True,
    )
    v1, v2, v3, v4 = st.columns(4)
    v1.metric("Tür", format_kategori(_vurgu.urun_turu or _vurgu.kampanya_turu))
    v2.metric(
      "Kâr payı",
      f"%{tr_sayi(_vurgu.kar_payi_orani)}" if _vurgu.kar_payi_orani is not None else "—",
    )
    v3.metric("Azami vade", f"{_vurgu.vade_ay_max} ay" if _vurgu.vade_ay_max is not None else "—")
    v4.metric("Güven", round(_vurgu.ortalama_guven or 0.0, 2))
    # `.deger` ŞART: `Alan` nesnesinin `str()`i değeri değil temsilini verir.
    _avantaj = _sema_nesneleri((_vurgu.kampanya_id,)).get(_vurgu.kampanya_id)
    if _avantaj is not None and _avantaj.kampanya_avantaji.var_mi:
      st.markdown(
        f'<div class="kl-kart-alt">'
        f'{" ".join(str(_avantaj.kampanya_avantaji.deger).split())}</div>',
        unsafe_allow_html=True,
      )
    st.link_button("Bankanın kampanya sayfasını aç", _vurgu.kaynak_url, type="primary")


tablo = []
for k in sorted(banka, key=lambda x: x.doluluk_orani, reverse=True):
  tablo.append({
    "Tür": format_kategori(k.urun_turu or k.kampanya_turu),
    "Kâr payı": f"%{tr_sayi(k.kar_payi_orani)}" if k.kar_payi_orani is not None else "—",
    "Azami vade": f"{k.vade_ay_max} ay" if k.vade_ay_max is not None else "—",
    "Bitiş": str(k.kampanya_bitis)[:10] if k.kampanya_bitis else "—",
    "Güven": round(k.ortalama_guven or 0.0, 2),
    "Kaynak": k.kaynak_url,
  })

_tablo_cerceve = pd.DataFrame(tablo)
st.dataframe(
  _tablo_cerceve,
  use_container_width=True,
  hide_index=True,
  column_config={"Kaynak": st.column_config.LinkColumn("Kaynak", display_text="sayfaya git")},
)
disa_aktar(
  _tablo_cerceve,
  dosya_adi=f"{format_bank_name(secili).lower().replace(' ', '_')}_kampanyalar",
  anahtar="bp_kampanyalar",
  baslik=f"{secili} — kampanyalar",
)


# ---------------------------------------------------------------------------
# Dürüstlük paneli — bu bankada neyi bilmiyoruz
# ---------------------------------------------------------------------------

eksikler = []
for alan in ("kar_payi_orani", "vade_ay_max", "finansman_tutari_max", "tahsis_ucreti"):
  bos = sum(1 for k in banka if getattr(k, alan, None) is None)
  if bos:
    eksikler.append(f"**{alan_etiketi(alan) or alan}** — {bos} / {len(banka)} kampanyada yok")

if eksikler:
  with st.expander("Bu bankada neyi bilmiyoruz"):
    for satir in eksikler:
      st.markdown(f"- {satir}")

sayfa_sonu()
