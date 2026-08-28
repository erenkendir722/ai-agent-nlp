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
  Senaryo,
  ortak_tabana_indir,
  sirala,
  toplam_maliyet,
  vade_duyarliligi,
  vade_tavsiyesi,
  uyarilar,
)
from src.rag.chatbot import alan_goster  # noqa: E402
from src.schema import HedefKitle, Kampanya  # noqa: E402
from app.ui_utils import (  # noqa: E402
  RENK_ANA,
  disa_aktar,
  RENK_IKINCIL,
  RENK_UYARI,
  format_bank_name,
  grafik_duzeni,
  format_alan_adi,
  format_hedef_kitle,
  format_kategori,
  inject_custom_css,
  kayitlari_yukle,
  gelistirici_anahtari,
  mimari_kenari,
  sonuclari_oku,
  tr_sayi,
  sayfa_gezinme,
  sayfa_sonu,
  uyarilari_goster,
)

st.set_page_config(page_title="Karşılaştırma", page_icon="", layout="wide")
inject_custom_css()
gelistirici_anahtari()
sayfa_gezinme()


def _halusinasyon_metni() -> str:
  """Ölçülmüş halüsinasyon oranı — elle yazılmaz, `docs/SONUCLAR.md`'den okunur."""
  oran = sonuclari_oku().halusinasyon_orani
  return "ölçülmedi" if oran is None else f"%{tr_sayi(oran * 100, 2)}"


st.title("Bankalar Arası Karşılaştırma")

kayitlar = kayitlari_yukle()

# ---------------------------------------------------------------------------
# Süzgeçler — ÜÇ KARAR ÜSTTE, GERİSİ PANELDE (28 Ağustos)
# ---------------------------------------------------------------------------
#
# Sayfanın tepesinde dokuz kontrol vardı: üçü açıkta, altısı «Gelişmiş
# filtreler» panelinde, hemen altında beş sıralama düğmesi ve bir ağırlık
# paneli daha. Ekranın ilk yarısı, henüz tek bir kampanya görmeden
# doldurulması gereken bir forma benziyordu.
#
# Ayrım şu: KİMİ karşılaştırdığın bir KARAR, geri kalanı bir RAFİNAJ.
# Karar üstte ve tek çerçevede durur; rafinaj panele iner ve panel kaç
# süzgecin etkin olduğunu BAŞLIĞINDA söyler — kapalı bir panelin arkasında
# sessizce çalışan süzgeç, kullanıcının «kampanyalar nereye gitti» dediği
# yerdir.
#
# «Asgari güven skoru» GELİŞTİRİCİ MODUNA taşındı: modelin kendi bildirdiği
# güvene göre süzmek bir bankacının işi değil, bizim iç ölçümümüz. Kapalı
# modda süzgeç yok sayılır (eşik 0), yani davranış değişmez.

bankalar = sorted({k.banka_adi for k in kayitlar})

# VARSAYILAN BANKA SECILI GELIR (27 Agu incelemesi, madde 5).
#
# «(Secilmedi)» ile aciliyordu: kullanici once bir banka secmeden
# «Biz vs Onlar» bolumu hic cizilmiyor, ekranin yarisi bos duruyordu. Bir
# bankacilik aracinda «kendi bankam» bos baslamaz.
#
# Hangisi? EN COK KAMPANYASI OLAN — demoda en dolu ekrani veren, elle
# secilmis degil veriden turetilmis.
_sayim: dict[str, int] = {}
for _k in kayitlar:
  _sayim[_k.banka_adi] = _sayim.get(_k.banka_adi, 0) + 1
_varsayilan = max(bankalar, key=lambda b: _sayim.get(b, 0))

with st.container(border=True):
  f1, f2, f3 = st.columns([2, 3, 2])

  with f1:
    _secenekler = ["(Seçilmedi)", *bankalar]
    benim_bankam = st.selectbox(
      "Benim bankam",
      _secenekler,
      index=_secenekler.index(_varsayilan),
      format_func=format_bank_name,
      help="Karşılaştırma bu bankanın gözünden yapılır.",
    )
  with f2:
    # KESIK ETIKET DUZELTMESI (madde 6): secim kutusu tam yasal unvani
    # gosteriyordu («Albaraka Turk Katilim Ba…»), etiketler tasip okunmaz
    # oluyordu. `format_bank_name` kayit defterindeki kisa adi verir; deger
    # yine tam unvandir, yalniz GOSTERIM kisalir.
    _rakipler = [b for b in bankalar if b != benim_bankam]
    secili_bankalar = st.multiselect(
      "Rakipler",
      bankalar,
      default=_rakipler,
      format_func=format_bank_name,
      placeholder="Banka seçin",
      help="Kendi bankanız ayrıca katılır.",
    )
  with f3:
    turler = sorted({k.kampanya_turu for k in kayitlar if k.kampanya_turu})
    secili_tur = st.selectbox(
      "Ürün türü", ["(tümü)", *turler],
      format_func=lambda x: format_kategori(x) if x != "(tümü)" else x,
    )

# PANEL BAŞLIĞI ETKİN SÜZGEÇ SAYISINI TAŞIR. Değerler `session_state`ten
# OKUNUR, widget'lar çizilmeden önce: başlık widget'ın kendi dönüş değerine
# bağlansaydı, sayı bir çizim geriden gelirdi (süzgeci açarsınız, başlık
# hâlâ «0 etkin» yazar).
_ETKIN_SORULARI = (
  ("ks_arama", lambda d: bool(d)),
  ("ks_hedef_kitle", lambda d: bool(d)),
  ("ks_gecmisi_gizle", lambda d: not d),   # varsayılan AÇIK — kapalıysa etkin
  ("ks_masrafsiz", lambda d: bool(d)),
  ("ks_tam_dolu", lambda d: bool(d)),
)
_VARSAYILANLAR = {"ks_gecmisi_gizle": True}
_etkin = sum(
  1 for _anahtar, _olcut in _ETKIN_SORULARI
  if _olcut(st.session_state.get(_anahtar, _VARSAYILANLAR.get(_anahtar, None)))
)
_panel_basligi = "Gelişmiş filtreler"
if _etkin:
  _panel_basligi += f"  ·  {_etkin} etkin"

with st.expander(_panel_basligi, expanded=False):
  c1, c2, c3 = st.columns([2, 2, 1.6])
  with c1:
    arama_metni = st.text_input(
      "Metin ara", key="ks_arama",
      placeholder="Banka, ürün ya da kampanya metni",
    )
  with c2:
    hedef_kitleler = [h.value for h in HedefKitle]
    # ETİKET, ENUM DEĞERİ DEĞİL (28 Ağustos). Liste `mevcut_musteri`,
    # `maas_musterisi`, `tum_musteriler` diye yazıyordu — veritabanı yazımı,
    # kullanıcı yazımı değil. `format_hedef_kitle` sözlüğü zaten var ve
    # sayfanın başka üç yerinde kullanılıyordu; süzgeç onu atlıyordu.
    secili_hedef_kitle = st.multiselect(
      "Hedef kitle", hedef_kitleler, key="ks_hedef_kitle",
      format_func=format_hedef_kitle, placeholder="Seçim yapın",
    )
  with c3:
    # TAKVİM YERİNE ANAHTAR. Burada bir tarih seçici vardı ve varsayılanı
    # «bugün»dü — yani aslında tek bir soruyu soruyordu: «süresi geçmişleri
    # görmek istiyor musunuz?» Takvim, o soruyu sormanın en pahalı yoluydu.
    st.toggle("Süresi geçenleri gizle", key="ks_gecmisi_gizle", value=True)
    sadece_masrafsiz = st.toggle("Yalnız masrafsız", key="ks_masrafsiz")
    tam_dolu_mu = st.toggle(
      "Yalnız eksiksiz kayıtlar", key="ks_tam_dolu",
      help="Kâr payı ya da vadesi yayımlanmamış kampanyaları gizler.",
    )

  # TEMİZLE DÜĞMESİ PANELİN İÇİNDE. Ana ekrana konsaydı, hiç süzgeç
  # kullanmayan kullanıcıya da bir düğme daha göstermiş olurduk; süzgeci
  # açan zaten burayı açıyor.
  if _etkin and st.button("Süzgeçleri temizle", key="ks_temizle"):
    for _anahtar, _ in _ETKIN_SORULARI:
      st.session_state.pop(_anahtar, None)
    st.rerun()

tarih_filtresi = datetime.date.today() if st.session_state.get("ks_gecmisi_gizle", True) else None

# Modelin kendi güvenine göre süzmek bankacının işi değil — geliştirici modu.
min_guven = 0.0
if st.session_state.get("dev_mode", False):
  min_guven = st.slider(
    "Asgari güven skoru", 0.0, 1.0, 0.0, 0.05,
    help="Çıkarılan alanların ortalama güveni. Sıfırda hiçbir kayıt elenmez.",
  )

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

# ---------------------------------------------------------------------------
# Kriter butonları (şartname 5.7)
# ---------------------------------------------------------------------------

st.subheader("Neye göre sıralansın?")
if "kriter" not in st.session_state:
  st.session_state.kriter = Kriter.EN_AVANTAJLI

sutunlar = st.columns(len(KRITER_ETIKETLERI))
for sutun, (kriter, etiket) in zip(sutunlar, KRITER_ETIKETLERI.items(), strict=True):
  if sutun.button(etiket, use_container_width=True, key=f"ks_kriter_{kriter.value}"):
    st.session_state.kriter = kriter

# AĞIRLIKLAR KENAR ÇUBUĞUNDAN BURAYA TAŞINDI (28 Ağustos).
#
# Dört kaydırıcı sol kenarda, seçili ölçütten 400 piksel uzakta duruyordu ve
# ekranda hiçbir şey ikisini birbirine bağlamıyordu: kullanıcı ne işe
# yaradıklarını göremiyordu. Oysa bağ dar — ağırlıklar YALNIZ «En avantajlı»
# sıralamasını etkiler; «En düşük kâr payı» seçiliyken hiçbir şey yapmazlar.
#
# Şimdi tam da o ölçüt seçiliyken, onun altında ve KAPALI bir panelde
# çıkıyorlar. Panelin başlığı ne yaptıklarını söylüyor; açmayan kullanıcı
# dengeli varsayılanla devam eder.
ONAYAR = {
  "Dengeli": (0.40, 0.25, 0.20, 0.15),
  "Fiyat odaklı": (0.70, 0.20, 0.05, 0.05),
  "Masraf odaklı": (0.20, 0.60, 0.10, 0.10),
  "Vade odaklı": (0.20, 0.10, 0.60, 0.10),
}

if st.session_state.kriter == Kriter.EN_AVANTAJLI:
  with st.expander("«En avantajlı» neye göre? — ağırlıkları siz belirlersiniz", expanded=False):
    _p = st.columns(len(ONAYAR))
    for _i, (_ad, _degerler) in enumerate(ONAYAR.items()):
      if _p[_i].button(_ad, key=f"ks_onayar_{_ad}", use_container_width=True):
        for _anahtar, _deger in zip(
          ("ks_a_kar", "ks_a_masraf", "ks_a_vade", "ks_a_odul"), _degerler, strict=True
        ):
          st.session_state[_anahtar] = _deger
        st.rerun()

    _k1, _k2, _k3, _k4 = st.columns(4)
    a_kar = _k1.slider("Kâr payı oranı", 0.0, 1.0, 0.40, 0.05, key="ks_a_kar")
    a_masraf = _k2.slider("Masraf", 0.0, 1.0, 0.25, 0.05, key="ks_a_masraf")
    a_vade = _k3.slider("Vade", 0.0, 1.0, 0.20, 0.05, key="ks_a_vade")
    a_odul = _k4.slider("Ödül", 0.0, 1.0, 0.15, 0.05, key="ks_a_odul")
else:
  # Panel çizilmese de değerler okunur: `session_state` kaydırıcıların son
  # hâlini tutuyor, yoksa varsayılan. Ölçüt değişince ağırlık sıfırlanmaz.
  a_kar = st.session_state.get("ks_a_kar", 0.40)
  a_masraf = st.session_state.get("ks_a_masraf", 0.25)
  a_vade = st.session_state.get("ks_a_vade", 0.20)
  a_odul = st.session_state.get("ks_a_odul", 0.15)

agirliklar = Agirliklar(a_kar, a_masraf, a_vade, a_odul)

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


def _enum_yazi(alan) -> str:
  """Alan değerinin ekran yazısı: enum ise ETİKETİ, değilse olduğu gibi.

  Eskiden `alan.goster().replace("_", " ").title()` yazılıyordu. `.title()`
  Türkçe'yi sessizce bozuyor — `schema.ALAN_ETIKETLERI`'nin kendi notunda da
  yazılı olan tuzak:

      yeni_musteri     ->  "Yeni Musteri"      (ü kayıp)
      alisveris_puani  ->  "Alisveris Puani"   (ş ve ı kayıp)

  Enum değerlerinin etiket sözlüğü zaten var; serbest metne dokunulmaz.
  """
  deger = getattr(alan, "deger", None)
  if isinstance(deger, str):
    etiket = format_kategori(deger)
    if etiket != deger:
      return etiket
    hedef = format_hedef_kitle(deger)
    if hedef != deger:
      return hedef
  return alan.goster()


def _csv_olustur(kayitlar):
  satirlar = []
  for k in kayitlar:
    satirlar.append({
      "Banka": format_bank_name(k.banka_adi),
      "Kampanya/Ürün": format_kategori(k.urun_turu or k.kampanya_turu) if (k.urun_turu or k.kampanya_turu) else "—",
      "Hedef Kitle": format_hedef_kitle(k.hedef_kitle) if k.hedef_kitle else "—",
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
    label="CSV indir",
    data=_csv_olustur(sirali_export),
    file_name="kampanyalar_export.csv",
    mime="text/csv",
    use_container_width=True
  )
with col_e:
  st.download_button(
    label="Excel indir",
    data=_excel_html(sirali_export),
    file_name="kampanyalar_export.xls",
    mime="application/vnd.ms-excel",
    use_container_width=True
  )

sirali = sirala(suzulmus, secili_kriter, agirliklar)

# SARI KUTU KALDIRILDI: «tahsis ucreti siralamaya katilmadi» bir ARIZA
# degil, olcut kapsaminin beyani. Alarm renginde gostermek kullaniciyi
# bir sorun oldugunu sanmaya itiyordu. Bilgi silinmedi — katlanabilir
# panele indi (`panelde_topla`), bir tiklama uzakta.
uyarilari_goster(uyarilar(sirali), panelde_topla=True)
# ---------------------------------------------------------------------------
# ES-08: Yan yana maliyet ve vade duyarliligi
# ---------------------------------------------------------------------------
#
# BU IKI BOLUM SAYFANIN EN ALTINDAYDI (27 Agustos). Tablonun altinda, 270
# satir asagida, kaydirmadan gorulmuyorlardi. Oysa banka calisaninin karar
# cumlesini uretenler bunlar: «ayni tutarda su banka su kadar ucuz» ve
# «vadeyi kisaltirsan su kadar kazanirsin». Tablo ham veriyi gosterir, bunlar
# CEVABI uretir — cevap ustte durur.
#
# SEKME, ALT ALTA DEGIL: ikisi ayni secimi (kampanyalar, anapara, vade)
# paylasiyor ve ayni anda ikisine birden bakilmiyor. Sekme, secimi bir kez
# yapip iki farkli soruyu sormayi saglar. Genel Bakis'taki sekme duzeniyle
# ayni gorsel dil.
#
# `secilen_adlar` sekmeden ONCE ilklendirilir: vade sekmesi onu maliyet
# sekmesinden okur ve `sirali` bossa maliyet sekmesi ona hic deger atamaz.

secilen_adlar: list[str] = []
_sk_maliyet, _sk_vade = st.tabs(["Yan yana toplam maliyet", "Vade duyarlılığı"])

with _sk_maliyet:
  if not sirali:
    st.info("Karşılaştırılacak kampanya yok.")
  else:
    # Kampanya Seçimi
    kampanya_secenekleri = {}
    for k in sirali:
      isim = f"{format_bank_name(k.banka_adi)} - {format_kategori(k.urun_turu or k.kampanya_turu)}"
      # Aynı isimde birden fazla kampanya varsa, kâr payı olan (üstte çıkan) ezilmesin
      if isim not in kampanya_secenekleri:
        kampanya_secenekleri[isim] = k
      
    secilen_adlar = st.multiselect(
      "Karşılaştırılacak kampanyalar (en fazla 3)",
      options=list(kampanya_secenekleri.keys()),
      default=list(kampanya_secenekleri.keys())[:2],
      max_selections=3,
      placeholder="Kampanya seçin",
    )

    if secilen_adlar:
      h1, h2 = st.columns(2)
      ortak_anapara = h1.number_input("Finansman tutarı (TL)", min_value=1000.0, value=500_000.0, step=10_000.0)
      ortak_vade = h2.number_input("Vade (ay)", min_value=1, value=120, step=6)
    
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
            st.markdown(
              '<div class="kl-not kl-not-soluk">Kâr payı oranı kaynakta '
              "yayımlanmamış; toplam maliyet hesaplanamıyor.</div>",
              unsafe_allow_html=True,
            )
            maliyet_sonuclari.append(float('inf'))
            continue
          
          # 1. İş Mantığı Zırhı: Limit Kontrolleri
          limit_asti_mi = False
          if kayit.finansman_tutari_max and kayit.finansman_tutari_max != "Belirtilmemiş":
            if ortak_anapara > float(kayit.finansman_tutari_max):
              st.markdown(
                '<div class="kl-not">Bu kampanyanın azami tutarı '
                f"<b>{kayit.finansman_tutari_max:,.0f} TL</b>".replace(",", ".")
                + " — istenen tutar üstünde kalıyor.</div>",
                unsafe_allow_html=True,
              )
              limit_asti_mi = True
        
          if kayit.vade_ay_max and kayit.vade_ay_max != "Belirtilmemiş":
            if ortak_vade > float(kayit.vade_ay_max):
              st.markdown(
                '<div class="kl-not">Bu kampanyanın azami vadesi '
                f"<b>{kayit.vade_ay_max:.0f} ay</b> — istenen vade üstünde kalıyor.</div>",
                unsafe_allow_html=True,
              )
              limit_asti_mi = True
            
          if limit_asti_mi:
            maliyet_sonuclari.append(float('inf'))
            continue
        
          # TAHSİS ÜCRETİ ORTAK TABANA İNDİRİLİR (27 Ağustos).
          #
          # Alan HEM TL HEM YÜZDE taşıyor; ham değer doğrudan `toplam_maliyet`e
          # verilirse yüzde, lira sanılıp toplama eklenir. Ölçüldü: `tahsis_ucreti`
          # dolu 41 kaydın 40'ı (%98) yüzde birimli.
          #
          #     %0,5 tahsis · 500.000 TL finansman
          #       gerçek  : 2.500 TL
          #       hatalı  :     0,50 TL      → 5.000 kat sapma
          #
          # `ortak_tabana_indir` bu işi zaten yapıyor ve kullanıcıdan aldığımız
          # anapara + vade tam olarak bir `Senaryo`. Birim çözülemezse `None`
          # döner — o zaman sıfır varsaymak yerine DURUMU SÖYLERİZ; sessizce
          # eksik masrafla hesaplanan bir «en uygun» yanıltıcıdır.
          senaryo = Senaryo(anapara=float(ortak_anapara), vade_ay=int(ortak_vade))
          tahsis = ortak_tabana_indir(kayit, "tahsis_ucreti", senaryo)
          tahsis_cozulemedi = kayit.tahsis_ucreti is not None and tahsis is None
          tahsis = tahsis or 0.0

          sonuc = toplam_maliyet(ortak_anapara, float(kayit.kar_payi_orani), int(ortak_vade), tahsis)
          maliyet_sonuclari.append(sonuc['toplam_geri_odeme'])
        
          st.metric("Aylık taksit", f"{sonuc['aylik_taksit']:,.2f} TL".replace(",", "."))
          st.metric("Toplam geri ödeme", f"{sonuc['toplam_geri_odeme']:,.2f} TL".replace(",", "."))

          if tahsis_cozulemedi:
            st.caption(
              "Tahsis ücretinin birimi çözülemedi; toplama **dâhil edilmedi**. "
              "Gerçek maliyet buradakinden yüksek olabilir."
            )
          elif tahsis:
            st.caption(f"Tahsis ücreti dâhil: {tahsis:,.0f} TL".replace(",", "."))
        
          # HALKA GRAFIK — LEJANT ACILDI (27 Agu, 2. inceleme).
          #
          # `showlegend=False` idi: ekranda yalniz «%0» ve «%100» yaziyor,
          # dilimlerin neyi temsil ettigi HICBIR YERDE yazmiyordu. Kullanici
          # anapara/kar payi ayrimi mi, odenen/kalan mi bilemiyordu. Ustelik
          # masraf sifirken «%0» diye bir dilim etiketi cikiyor, grafik iki
          # anlamsiz sayiya donuyordu.
          #
          # Sifir kalemler artik hic cizilmiyor; kalanlar adiyla ve tutariyla
          # etiketli.
          _kalemler = [
            ("Anapara", ortak_anapara, RENK_IKINCIL),
            ("Kâr payı", sonuc["toplam_kar_payi"], RENK_ANA),
            ("Masraflar", tahsis, RENK_UYARI),
          ]
          _dolu = [(ad, tutar, renk) for ad, tutar, renk in _kalemler if tutar and tutar > 0]
          if _dolu:
            fig = px.pie(
              pd.DataFrame({
                "Kategori": [a for a, _, _ in _dolu],
                "Tutar": [t for _, t, _ in _dolu],
              }),
              values="Tutar", names="Kategori", hole=0.6,
              color_discrete_sequence=[r for _, _, r in _dolu],
            )
            fig.update_traces(
              textposition="inside", textinfo="percent",
              hovertemplate="<b>%{label}</b><br>%{value:,.0f} TL<br>%{percent}<extra></extra>",
            )
            grafik_duzeni(fig, yukseklik=190)
            fig.update_layout(
              showlegend=True,
              legend={"orientation": "h", "y": -0.12, "font": {"size": 10}},
              margin={"t": 6, "b": 6, "l": 6, "r": 6},
            )
            st.plotly_chart(fig, use_container_width=True, key=f"donut_karsilastirma_{i}")
        
      # «NEDEN AYNI RAKAM?» (27 Agu, 2. inceleme). Farkli urunler (konut ve
      # tasit) ayni tutar ve vadede birebir ayni maliyeti verebiliyor —
      # dogrudur, cunku hesap YALNIZ kar payi oranina, tutara ve vadeye
      # bakar; urun turu hesaba girmez. Ama kullanici bunu bilmedigi icin
      # ayni sayiyi bir hata saniyordu. Not yalniz GERCEKTEN esitlik varken
      # cikar; her zaman yazsaydi gurultu olurdu.
      _gecerliler = [m for m in maliyet_sonuclari if m != float("inf")]
      if len(_gecerliler) > 1 and len({round(m, 2) for m in _gecerliler}) < len(_gecerliler):
        st.caption(
          "Aynı maliyet, aynı oran demektir: hesaba yalnız **kâr payı oranı, "
          "tutar ve vade** girer; ürün türü girmez."
        )

      # Kazananı Vurgulama
      gecerli_maliyetler = [m for m in maliyet_sonuclari if m != float('inf')]
      if gecerli_maliyetler:
        en_dusuk_maliyet = min(gecerli_maliyetler)
        for i, ad in enumerate(secilen_adlar):
          if maliyet_sonuclari[i] == en_dusuk_maliyet:
            kazanan = kampanya_secenekleri[ad]
            with cols[i]:
              st.success("**En uygun seçenek**")
              st.caption("Tahsis ücreti dâhil toplam geri ödemeye göre.")

              # DEVAM YOLU — karşılaştırma bir cevap verir, sonrası boşluktu.
              # Kullanıcı «peki bu banka nasıl bir kurum» ya da «kaynağı nerede»
              # diye sorduğunda gidecek yeri yoktu.
              if st.button(
                "Devam et — banka detayına git",
                key=f"kars_devam_{i}",
                type="primary",
                use_container_width=True,
              ):
                # Anahtar, Banka Profili'ndeki `st.selectbox`'ın KEY'i ile aynı.
                st.session_state["bp_secili_banka"] = kazanan.banka_adi
                st.switch_page("pages/5_Banka_Profili.py")

              st.markdown(f"[Kampanyanın kaynak sayfası]({kazanan.kaynak_url})")
              st.caption(f"{kazanan.cekim_tarihi:%d.%m.%Y} tarihinde alınmıştır")


with _sk_vade:
  if not secilen_adlar:
    st.info(
      "Önce **Yan yana toplam maliyet** sekmesinden en az bir kampanya seçin; "
      "vade duyarlılığı o seçim üzerinden hesaplanır."
    )
  else:

    # -----------------------------------------------------------------------
    # Vade duyarlılığı — karar desteği
    # -----------------------------------------------------------------------
    #
    # Tekil teklif «hangi banka?» sorusunu cevaplar. Banka çalışanının müşteriye
    # kuracağı cümle ise genelde şudur: «aynı kampanyada vadeyi kısaltırsan şu
    # kadar az ödersin». Aşağısı o cümlenin sayısını üretir.
    #
    # Hesap `src/comparison/karsilastirma.vade_duyarliligi` içinde ve saf koddur —
    # bu bölümde dil modeli çalışmaz.

    st.divider()
    st.subheader("Kısa vade ne kazandırır?")

    v1, v2 = st.columns(2)
    duyarlilik_kampanyasi = v1.selectbox(
      "Hangi kampanya için?",
      options=secilen_adlar,
      help="Yukarıda seçtiğiniz kampanyalar arasından.",
    )
    taksit_tavani_acik = v2.toggle(
      "Aylık ödeme tavanı belli",
      help="Tavan olmadan «en iyi vade» hep en kısa vade çıkar; "
           "sistem o yüzden tavsiye vermez.",
    )
    azami_taksit = None
    if taksit_tavani_acik:
      azami_taksit = v2.number_input(
        "Aylık azami taksit (TL)", min_value=1000.0, value=25_000.0, step=1_000.0
      )

    d_kayit = kampanya_secenekleri[duyarlilik_kampanyasi]
    if pd.isna(d_kayit.kar_payi_orani) or d_kayit.kar_payi_orani == "Belirtilmemiş":
      st.markdown(
        f'<div class="kl-not"><b>{format_bank_name(d_kayit.banka_adi)}</b> için kâr '
        "payı oranı yayımlanmamış; vade tablosu üretilemez. Eksik veriyi "
        "varsayımla doldurmuyoruz.</div>",
        unsafe_allow_html=True,
      )
    else:
      d_tahsis = (
        float(d_kayit.tahsis_ucreti)
        if (d_kayit.tahsis_ucreti and d_kayit.tahsis_ucreti != "Belirtilmemiş")
        else 0.0
      )
      d_vade_max = (
        float(d_kayit.vade_ay_max)
        if (d_kayit.vade_ay_max and d_kayit.vade_ay_max != "Belirtilmemiş")
        else None
      )
      secenekler = vade_duyarliligi(
        ortak_anapara,
        float(d_kayit.kar_payi_orani),
        referans_vade=int(ortak_vade),
        tahsis_ucreti=d_tahsis,
        vade_ay_max=d_vade_max,
      )

      cumle = vade_tavsiyesi(secenekler, int(ortak_vade), azami_taksit=azami_taksit)
      if cumle:
        st.info(cumle)

      satirlar = []
      for sec in secenekler:
        if not sec.uygun_mu:
          satirlar.append({
            "Vade (ay)": sec.vade_ay,
            "Aylık taksit": None,
            "Toplam geri ödeme": None,
            f"{int(ortak_vade)} aya göre fark": None,
            "Durum": f"Uygulanamaz — {sec.engel}",
          })
          continue
        satirlar.append({
          "Vade (ay)": sec.vade_ay,
          "Aylık taksit": sec.aylik_taksit,
          "Toplam geri ödeme": sec.toplam_geri_odeme,
          f"{int(ortak_vade)} aya göre fark": sec.toplam_farki,
          "Durum": "Seçili vade" if sec.referans_mi else "",
        })

      st.dataframe(
        pd.DataFrame(satirlar),
        use_container_width=True,
        hide_index=True,
        column_config={
          "Aylık taksit": st.column_config.NumberColumn(format="%.0f TL"),
          "Toplam geri ödeme": st.column_config.NumberColumn(format="%.0f TL"),
          f"{int(ortak_vade)} aya göre fark": st.column_config.NumberColumn(
            format="%.0f TL",
            help="Negatif = bu vade seçili vadeden daha ucuz.",
          ),
        },
      )

      cizilebilir = [s for s in secenekler if s.uygun_mu]
      if len(cizilebilir) > 1:
        cizim = pd.DataFrame({
          "Vade (ay)": [s.vade_ay for s in cizilebilir],
          "Toplam geri ödeme": [s.toplam_geri_odeme for s in cizilebilir],
          "Aylık taksit": [s.aylik_taksit for s in cizilebilir],
        })
        g1, g2 = st.columns(2)
        with g1:
          fig_toplam = px.line(
            cizim, x="Vade (ay)", y="Toplam geri ödeme", markers=True,
            color_discrete_sequence=[RENK_ANA],
          )
          grafik_duzeni(fig_toplam, yukseklik=260, baslik="Vade uzadıkça toplam maliyet")
          st.plotly_chart(fig_toplam, use_container_width=True)
        with g2:
          fig_taksit = px.line(
            cizim, x="Vade (ay)", y="Aylık taksit", markers=True,
            color_discrete_sequence=[RENK_IKINCIL],
          )
          grafik_duzeni(fig_taksit, yukseklik=260, baslik="Vade uzadıkça aylık taksit")
          st.plotly_chart(fig_taksit, use_container_width=True)






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

# DEĞER BAZLI RENKLENDİRME KALDIRILDI (28 Ağustos).
#
# Tablo iki sütunu ölçeğe göre boyuyordu: güven skoru yeşil/sarı/kırmızı,
# kâr payı dört tonda mavi. İkisi de yanlış bilgi veriyordu.
#
# Güven skoru KIRMIZI olunca kullanıcı bir hata arıyor; oysa eşik yok —
# 0,68 «yanlış» demek değil, «bu alanı yalnız bir katman doğruladı» demek.
# Renk bir yargı bildirir, orada bir yargı yoktu. Kâr payının mavi tonları
# ise sıralamayı ikinci kez, daha bulanık biçimde anlatıyordu; tablo zaten
# seçili ölçüte göre sıralı.
#
# Kalan tek renk KENDİ BANKAN: karşılaştırma onun gözünden yapılıyor,
# satırın nerede olduğunu görmek kararın kendisi.
def _kendi_bankam(satir):
  hedef_ad = format_bank_name(benim_bankam)
  if benim_bankam != "(Seçilmedi)" and satir["Banka"] == hedef_ad:
    return ["background-color: rgba(0, 168, 107, 0.13)"] * len(satir)
  return [""] * len(satir)


st.dataframe(
  tablo.style.apply(_kendi_bankam, axis=1),
  use_container_width=True,
  hide_index=True,
)

# ---------------------------------------------------------------------------
# Satış notu taslağı
# ---------------------------------------------------------------------------
#
# BÖLÜM NE İŞE YARIYOR: yukarıdaki tablo rakamı verir, bu bölüm o rakamdan
# müşteriye SÖYLENECEK CÜMLEYİ yazar — nerede öndeyiz, nerede geride,
# görüşmede hangi sırayla anlatılır. Satış ekibinin «battlecard» dediği şey.
#
# Adı «Rakip analizi taslağı (yapay zekâ)» idi ve ne ürettiğini söylemiyordu;
# kullanıcı düğmeye basmadan ne çıkacağını bilemiyordu. Başlık artık çıktıyı
# adlandırıyor, panel kapalı açılıyor: isteyen açar.
#
# ROZET «AI TASLAK» OLDU (28 Ağustos). Öncesi «AI ÜRETİMİ — DOĞRULANMAMIŞ»
# idi: büyük harfle, uyarı renginde, üstelik «doğrulanmamış» kelimesiyle.
# Ayrım doğruydu ama tonu yanlıştı — kullanıcı düğmeye BASMAYA çekiniyordu,
# oysa çıktı bir taslak; zaten düzeltilmek üzere üretiliyor.
#
# Ayrım SİLİNMEDİ, sözcüğü değişti: «taslak» hem dil modelinin yazdığını
# hem de olduğu gibi kullanılmayacağını söylüyor, korkutmadan.
# Nöbetçi: `test_ai_ciktisi_isaretle_ayriliyor`.
if benim_bankam != "(Seçilmedi)" and sirali:
  st.subheader("Satış notu taslağı")
  st.markdown(
    '<div class="kl-meta"><span class="kl-cip" title="Bu metni dil modeli '
    "yazar. Sayfadaki tek serbest metin çıktısı; rakam için yukarıdaki "
    'tabloyu esas alın.">AI taslak</span></div>',
    unsafe_allow_html=True,
  )
  st.caption(
    "Tablodaki rakamlardan müşteriye söylenecek cümleyi yazar: nerede "
    "öndeyiz, nerede gerideyiz, görüşmede ne anlatılır."
  )
  if st.button("Satış notu üret", type="primary"):
    biz_data = [k for k in sirali if format_bank_name(k.banka_adi) == format_bank_name(benim_bankam)]
    onlar_data = [k for k in sirali if format_bank_name(k.banka_adi) != format_bank_name(benim_bankam) and format_bank_name(k.banka_adi) in [format_bank_name(b) for b in secili_bankalar]]
    
    if not biz_data:
      st.info(f"{format_bank_name(benim_bankam)} için süzgeçlerden geçen kampanya yok.")
    elif not onlar_data:
      st.info("Rakip setinde süzgeçlerden geçen kampanya yok.")
    else:
      with st.spinner("Satış notu yazılıyor…"):
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
          # ÜRETİLEN TASLAK OTURUMDA SAKLANIR. `st.download_button` sayfayı
          # yeniden koşturur; taslak yalnız bu blokta yaşasaydı indirme
          # tıklandığı anda kaybolur ve düğme boş dosya verirdi.
          st.session_state["ks_satis_notu"] = {
            "metin": response.choices[0].message.content,
            "banka": format_bank_name(benim_bankam),
            "model": model_adi,
          }
        except Exception as e:
          st.info("Dil modeli servisine şu anda ulaşılamıyor; sayfanın geri "
                  "kalanı bundan etkilenmez.")
          if st.session_state.get("dev_mode", False):
            st.code(str(e))

  # Taslak, üretildiği koşuda da sonrakilerde de BURADA çizilir — tek yer.
  _not = st.session_state.get("ks_satis_notu")
  if _not:
    st.info(_not["metin"])
    _i1, _i2 = st.columns([3, 1])
    with _i1:
      disa_aktar(
        pd.DataFrame([{"Banka": _not["banka"], "Satış notu": _not["metin"]}]),
        dosya_adi=f"satis_notu_{_not['banka'].lower().replace(' ', '_')}",
        anahtar="ks_satis_notu_indir",
        baslik=f"{_not['banka']} — satış notu taslağı",
      )
    _i2.caption(f"{_not['model']} modeliyle üretildi.")

# ---------------------------------------------------------------------------
# Avantaj skorunun dökümü
# ---------------------------------------------------------------------------

# «NASIL HESAPLANDI» PANELLERI KALDIRILDI (27 Agustos). Iki panel de
# yontem anlatiyordu: min-maks normalizasyon, notr deger, kararli
# siralama garantisi. Banka calisani hangi bankanin avantajli oldugunu
# ariyor, skorun nasil olctuklendigini degil. Yontem kaybolmadi:
# `docs/MIMARI.md` ve `src/comparison/karsilastirma.py` ayni seyi
# yaziyor, kaynak kaniti da asagidaki «Kayit detaylari» bolumunde.

st.divider()

# ---------------------------------------------------------------------------
# Kanıt panelleri — her sayının kaynağı
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Kayıt kanıtı — YİRMİ PANEL YERİNE TEK KAYIT (28 Ağustos)
# ---------------------------------------------------------------------------
#
# Burada `sirali[:20]` üzerinde dönen yirmi katlanabilir panel vardı. Her
# panel açıldığında alanlar üç sütunlu bir ızgaraya dökülüyor, her alanın
# altına kaynak alıntısı `st.caption` olarak giriyordu: tek bir kayıt için
# 40'a yakın satır. Yirmi panel yan yana durunca bölüm, sayfanın en karışık
# yeriydi ve hangisine bakılacağı belli değildi.
#
# Kanıtın kendisi kalkmadı — bankacılıkta izlenebilirlik olmadan sistem
# kabul edilmez. Değişen şey ERİŞİM BİÇİMİ: önce hangi kaydın kanıtına
# bakılacağı seçilir, sonra o kayıt tek ve düzenli bir tabloda açılır.
# Alıntılar ayrı bir panelde toplanır; alan listesini bölmezler.

st.subheader("Kayıt kanıtı")
st.caption("Her alanın hangi katmandan geldiği, güveni ve kaynaktaki karşılığı.")

_kanit_secenekleri = {
  f"{format_bank_name(k.banka_adi)} — "
  f"{format_kategori(k.urun_turu or k.kampanya_turu) if (k.urun_turu or k.kampanya_turu) else 'Kampanya'}"
  f"  (doluluk %{k.doluluk_orani * 100:.0f})": k
  for k in sirali[:20]
}

if _kanit_secenekleri:
  _secili_kanit = st.selectbox(
    "Kayıt", list(_kanit_secenekleri), label_visibility="collapsed"
  )
  kayit = _kanit_secenekleri[_secili_kanit]
  kampanya: Kampanya = kayit.kampanyaya_cevir()

  _b1, _b2 = st.columns([3, 1])
  _b1.markdown(f"**Kaynak:** [{kayit.kaynak_url}]({kayit.kaynak_url})")
  _b2.caption(f"Çekim: {kayit.cekim_tarihi:%d.%m.%Y %H:%M}")

  # ALANLAR TABLODA, `st.columns` YIĞINI DEĞİL. Üç sütunlu markdown ızgarası
  # her alan için üç ayrı Streamlit ögesi üretiyordu; tablo tek öge ve
  # hizalaması kendiliğinden doğru.
  _dolu_alanlar = [
    {
      "Alan": format_alan_adi(alan_adi),
      "Değer": _enum_yazi(alan),
      "Katman": alan.yontem,
      "Güven": f"{alan.guven:.2f}",
    }
    for alan_adi, alan in kampanya.cikarilan_alanlar().items()
    if alan.var_mi
  ]
  if _dolu_alanlar:
    st.dataframe(
      pd.DataFrame(_dolu_alanlar), use_container_width=True, hide_index=True
    )

  _alintilar = [
    (format_alan_adi(ad), alan.kaynak.alinti)
    for ad, alan in kampanya.cikarilan_alanlar().items()
    if alan.var_mi and alan.kaynak and alan.kaynak.alinti
  ]
  if _alintilar:
    with st.expander(f"Kaynak alıntıları ({len(_alintilar)})", expanded=False):
      for _ad, _alinti in _alintilar:
        st.markdown(f"**{_ad}**")
        st.markdown(f"> {_alinti[:280]}")

  _bos = [
    format_alan_adi(ad)
    for ad, alan in kampanya.cikarilan_alanlar().items()
    if not alan.var_mi
  ]
  if _bos:
    st.caption(f"Kaynakta yayımlanmamış: {', '.join(_bos)}")

  if st.session_state.get("dev_mode", False):
    with st.expander("Kaydın ham JSON'u"):
      st.json(kampanya.model_dump())

st.divider()

if st.session_state.get("dev_mode", False):
  st.caption("**Filtrelenmiş sonuçlar API'den** (`make api` ile başlatın):")
  
  curl_cmd = f"""curl "http://localhost:8000/compare?kriter={secili_kriter.value}&limit=10"
"""
  st.code(curl_cmd, language="bash")
  st.divider()

mimari_kenari("Motor")
sayfa_sonu()
