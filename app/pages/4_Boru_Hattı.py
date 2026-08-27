"""Canlı Boru Hattı — toplama ve çıkarım arayüzden sürülür, canlı izlenir.

Bugüne kadar veriyi ÜRETEN iki katman (9 Selenium kazıyıcısı ve hibrit çıkarım
hattı) yalnız terminalde koşuyordu; arayüz sonucu gösteriyor, üretimi
göstermiyordu. Bu sayfa o iki katmanı görünür kılar.

DÜRÜSTLÜK SINIRI — bu sayfada yalan söyleyen tek piksel yok:
  - Animasyon GERÇEK olaylardan beslenir. Sahte ilerleme, sahte sayaç,
    uydurma gecikme yok; kuyruk boşsa çubuk ilerlemez.
  - «toplanan sayfa», «sn/kayıt», «doluluk», «güven» ölçülen değerlerdir.
  - Nezaket kuralı (istek arası ≥2 sn, alan adı başına tek sıra) demo hızı
    için GEVŞETİLMEZ. Demo kipi sayfa SAYISINI kısar, temposunu değil.
  - Eleştirmen ajanı, yüklem ajanı ve kanıt denetimi bu sayfada da açık.

YAZMA HEDEFİ: varsayılan olarak `data/demo_raw/` + `data/demo/demo.db`.
Üretim verisine (`data/raw`, `data/katilim.db`) ancak sekmedeki kapalı gelen
onay kutusu işaretlenirse dokunulur.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.boru_hatti import (  # noqa: E402
  CikarimAyarlari,
  CikarimOzeti,
  cikarim_kos,
  demo_veritabani,
)
from src.collector.toplayici import (  # noqa: E402
  DEMO_HAM_DIZIN,
  HAM_DIZIN,
  bankalari_yukle,
  faal_bankalar,
  ham_kayitlari_oku,
  topla,
)
from src.depolama import VERITABANI_URL  # noqa: E402
from src.izleme import (  # noqa: E402
  Tetikleyici,
  hedefleri_oku,
  kesif_kos,
  kesif_taban_oku,
  tazelik_denetle,
)
from src.izleme.dinleyici import taban_oku  # noqa: E402
from src.extraction.saglayici import (  # noqa: E402
  EVREN_MODEL,
  OLLAMA_MODEL,
  SAGLAYICI_ADI,
)
from app.akis import (  # noqa: E402
  akis_css,
  banka_izgarasi,
  ilerleme_cubugu,
  katman_hatti,
  kayit_seridi,
  olay_gunlugu,
)
from app.boru_durumu import (  # noqa: E402
  AZAMI_GUNLUK_GECMISI,
  CikarimDurumu,
  KesifDurumu,
  TazelikDurumu,
  ToplamaDurumu,
  acik_kartlari_kapat,
  cikarim_olaylarini_isle,
  kesif_olaylarini_isle,
  tazelik_kartlarini_kapat,
  tazelik_olaylarini_isle,
  toplama_olaylarini_isle,
)
from app.is_yurutucu import baslat, olaylari_cek  # noqa: E402
from app.ui_utils import (  # noqa: E402
  format_bank_name,
  format_kategori,
  inject_custom_css,
  ortak_kenar,
)

st.set_page_config(page_title="Canlı Boru Hattı", page_icon="", layout="wide")
inject_custom_css()
ortak_kenar()
st.markdown(akis_css(), unsafe_allow_html=True)

st.title("Canlı Boru Hattı")

# Demo kipinde banka başına yazılan sayfa tavanı.
DEMO_SAYFA_TAVANI = 10


# ---------------------------------------------------------------------------
# Oturum durumu
# ---------------------------------------------------------------------------
#
# `ToplamaDurumu` / `CikarimDurumu` BİLEREK `app/boru_durumu.py`'de duruyor:
# Streamlit bu betiği her çizimde baştan çalıştırdığı için burada tanımlanan
# bir sınıf her koşuda yeni bir nesne olur ve `_durum_al`'daki `isinstance`
# eski örneği tanımayıp biriken durumu sıfırlar. Gerekçe o dosyanın başında.


def _durum_al(anahtar: str, tip):
  if not isinstance(st.session_state.get(anahtar), tip):
    st.session_state[anahtar] = tip()
  return st.session_state[anahtar]


st.session_state.setdefault("bh_is", None)
st.session_state.setdefault("bh_is_turu", "")
st.session_state.setdefault("bh_toplama_ozet", None)
st.session_state.setdefault("bh_cikarim_ozet", None)
st.session_state.setdefault("bh_tazelik_ozet", None)
st.session_state.setdefault("bh_kesif_ozet", None)
st.session_state.setdefault("bh_oturum_urlleri", [])


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300)
def _kaziyicili_bankalar() -> list[tuple[str, str]]:
  """Kazıyıcısı olan faal bankalar: (kod, kısa ad).

  `src.collector.kaziyicilar` selenium'u içeri çekiyor; içe aktarma
  başarısız olursa (kurulum eksik) sayfa KIRILMAZ, kayıt defterindeki faal
  bankaların tamamı listelenir ve koşu denendiğinde gerçek hata görünür.
  """
  faal = faal_bankalar(bankalari_yukle())
  try:
    from src.collector.kaziyicilar import KAZIYICILAR

    return [(b.kod, b.kisa_ad) for b in faal if b.kod in KAZIYICILAR]
  except Exception:  # noqa: BLE001 — sebebi koşu anında zaten görünecek
    return [(b.kod, b.kisa_ad) for b in faal]


def _ham_kayit_sayisi(dizin: Path) -> int:
  """Dizindeki ham kayıt adedi — HTML okumadan, yalnız JSON sayarak."""
  return sum(1 for _ in dizin.rglob("*.json")) if dizin.is_dir() else 0


def _saglayici_rozeti() -> tuple[str, str]:
  if SAGLAYICI_ADI == "ollama":
    return "Ollama (yerel)", OLLAMA_MODEL
  return "EVREN (SSB)", EVREN_MODEL


def _hedef_yazi(uretime: bool, *, cikarim: bool) -> str:
  if cikarim:
    return "data/katilim.db (ÜRETİM)" if uretime else "data/demo/demo.db (demo)"
  return "data/raw (ÜRETİM)" if uretime else "data/demo_raw (demo)"


def _isi_bitir(anahtar_ozet: str) -> None:
  """İş bittiğinde sonucu saklar, iş yuvasını boşaltır."""
  is_ = st.session_state.bh_is
  st.session_state[anahtar_ozet] = {
    "sonuc": is_.sonuc,
    "hata": is_.hata,
    "iz": is_.iz,
    "sure": is_.gecen_sure(),
    "iptal": is_.iptal.is_set(),
  }
  st.session_state.bh_is = None
  st.session_state.bh_is_turu = ""


def _hata_kutusu(paket: dict) -> None:
  """İş parçacığındaki istisna — yutulmaz, kırmızı kutuyla gösterilir."""
  hata = paket.get("hata")
  if hata is None:
    return
  st.error(f"Koşu hata ile bitti: **{type(hata).__name__}** — {hata}")
  ad = type(hata).__name__
  if "WebDriver" in ad or "SessionNotCreated" in ad:
    st.info(
      "Chrome bulunamadı. Toplama gerçek tarayıcı gerektirir; yalnız "
      "çıkarımı denemek isterseniz 2. sekmeyi kullanabilirsiniz."
    )
  elif "HTTP" in ad or "Timeout" in ad or "Connect" in ad:
    st.info(
      "Dil modeli servisine ulaşılamadı. Ağ bağlantısını ve servis "
      "ayarlarını denetleyin."
    )
  if st.session_state.get("dev_mode", False) and paket.get("iz"):
    with st.expander("Yığın izi (geliştirici modu)"):
      st.code(paket["iz"])


def _gunluk_ciz(olaylar: list, *, anahtar: str) -> None:
  """Açılıp kapanan olay günlüğü: kapalıyken son satır, açıkken tamamı.

  Açıklık `st.toggle` ile `session_state`'te tutuluyor — `st.expander` ya da
  HTML `<details>` DEĞİL. Canlı alan 0,4 saniyede bir yeniden çiziliyor ve
  istemci tarafında duran bir açıklık her çizimde kendiliğinden kapanırdı.
  """
  acik = st.toggle(
    "Olay günlüğü",
    key=anahtar,
    help="Kapalıyken yalnız en son olay, açıkken tamamı görünür.",
  )
  st.markdown(
    olay_gunlugu(olaylar, azami=AZAMI_GUNLUK_GECMISI, acik=acik),
    unsafe_allow_html=True,
  )


def _bekleyen_isi_devral() -> bool:
  """Bitmiş ama sonucu HENÜZ ALINMAMIŞ işi devralır. Devraldıysa `True`.

  Bitiş normalde canlı parçada yakalanır. Ama canlı parça yalnız iş
  KOŞARKEN çiziliyor: kullanıcı koşu ortasında başka sayfaya geçip
  döndüğünde (ya da iş iki çizim arasında bittiğinde) o parça hiç koşmaz,
  sonuç da hiç devralınmazdı — kuyruk, özet ve hata sessizce kaybolurdu.
  Ölçüldü: `AppTest` ile sürülen koşuda bitiş paneli hiç gelmedi.

  Bu yüzden yoklama betiğin HER tam koşusunda burada da yapılır; canlı
  parça yalnız aynı işlevi erken çağırır.
  """
  is_ = st.session_state.bh_is
  if is_ is None or is_.calisiyor_mu():
    return False

  tur = st.session_state.bh_is_turu
  if tur == "toplama":
    durum = _durum_al("bh_toplama_durum", ToplamaDurumu)
    while (kalan := olaylari_cek(is_)):
      toplama_olaylarini_isle(durum, kalan)
    acik_kartlari_kapat(durum, iptal=is_.iptal.is_set())
    st.session_state.bh_oturum_urlleri = list(
      dict.fromkeys(st.session_state.bh_oturum_urlleri + durum.urller)
    )
    _isi_bitir("bh_toplama_ozet")
  elif tur == "cikarim":
    durum = _durum_al("bh_cikarim_durum", CikarimDurumu)
    while (kalan := olaylari_cek(is_)):
      cikarim_olaylarini_isle(durum, kalan)
    _isi_bitir("bh_cikarim_ozet")
  elif tur == "kesif":
    durum = _durum_al("bh_kesif_durum", KesifDurumu)
    while (kalan := olaylari_cek(is_)):
      kesif_olaylarini_isle(durum, kalan)
    _isi_bitir("bh_kesif_ozet")
  elif tur == "tazelik":
    durum = _durum_al("bh_tazelik_durum", TazelikDurumu)
    while (kalan := olaylari_cek(is_)):
      tazelik_olaylarini_isle(durum, kalan)
    tazelik_kartlarini_kapat(durum)
    _isi_bitir("bh_tazelik_ozet")
  else:  # tür bilinmiyorsa yuvayı boşalt — kilitli kalmasın
    st.session_state.bh_is = None
    st.session_state.bh_is_turu = ""
  return True


_bekleyen_isi_devral()

MESGUL = bool(st.session_state.bh_is and st.session_state.bh_is.calisiyor_mu())


# ---------------------------------------------------------------------------
# Sekmeler
# ---------------------------------------------------------------------------

sekme_toplama, sekme_cikarim, sekme_tazelik = st.tabs(
  ["1 · Veri Toplama", "2 · Çıkarım", "3 · Veri Denetimi"]
)


# === SEKME 1 — VERİ TOPLAMA ===============================================

with sekme_toplama:
  bankalar_secenegi = _kaziyicili_bankalar()

  k1, k2 = st.columns([1, 1.4])
  with k1:
    t_kip = st.radio(
      "Koşu kipi",
      [f"Demo (banka başına {DEMO_SAYFA_TAVANI} sayfa)", "Tam koşu (tüm sayfalar)"],
      key="bh_t_kip",
      disabled=MESGUL,
      help="İkisi de gerçek toplama yapar; demo kipi yalnız sayfa sayısını kısar.",
    )
  with k2:
    tum_kodlar = [kod for kod, _ in bankalar_secenegi]
    banka_adlari = dict(bankalar_secenegi)
    # Varsayılan `setdefault` ile veriliyor, `default=` ile DEĞİL: aynı
    # anahtara hem `default=` verip hem `session_state`'ten yazmak
    # «created with a default value but also had its value set via the
    # Session State API» uyarısı üretiyor (ölçüldü).
    st.session_state.setdefault("bh_t_bankalar", tum_kodlar)
    st.markdown("**Bankalar**")

    # DÜĞMELER MULTISELECT'TEN ÖNCE çiziliyor: bir widget'ın `session_state`
    # değeri ancak o widget oluşturulmadan ÖNCE yazılabilir; sonrasında
    # Streamlit `StreamlitAPIException` fırlatır.
    s1, s2 = st.columns(2)
    if s1.button(
      f"Tümünü seç ({len(tum_kodlar)})", disabled=MESGUL,
      use_container_width=True, key="bh_t_hepsi",
    ):
      st.session_state.bh_t_bankalar = tum_kodlar
    if s2.button(
      "Temizle", disabled=MESGUL, use_container_width=True, key="bh_t_temizle"
    ):
      st.session_state.bh_t_bankalar = []

    t_secili = st.multiselect(
      "Bankalar",
      options=tum_kodlar,
      format_func=lambda kod: banka_adlari.get(kod, kod),
      key="bh_t_bankalar",
      disabled=MESGUL,
      label_visibility="collapsed",
      placeholder="Banka seçin…",
    )
    st.caption(f"{len(t_secili)} / {len(tum_kodlar)} banka seçili")

  t_demo = t_kip.startswith("Demo")
  t_uretime = st.checkbox(
    "Üretim verisine yaz",
    value=False,
    key="bh_t_uretim",
    disabled=MESGUL,
    help="İşaretlenmedikçe koşu yalnız demo alanına yazar.",
  )
  t_dizin = HAM_DIZIN if t_uretime else DEMO_HAM_DIZIN

  d1, d2, _ = st.columns([1, 1, 3])
  t_basla = d1.button(
    "Toplamayı Başlat", type="primary", disabled=MESGUL or not t_secili,
    use_container_width=True, key="bh_t_basla",
  )
  t_iptal = d2.button(
    "İptal", disabled=not (MESGUL and st.session_state.bh_is_turu == "toplama"),
    use_container_width=True, key="bh_t_iptal",
  )

  if not t_secili:
    st.warning("En az bir banka seçin.")
  if MESGUL and st.session_state.bh_is_turu == "cikarim":
    st.info("Şu an bir çıkarım koşusu sürüyor — aynı anda tek iş çalışır.")

  if t_iptal and st.session_state.bh_is is not None:
    st.session_state.bh_is.iptal_et()
    st.toast("İptal istendi — açık sayfa bitince tarayıcı temiz kapanacak.")

  if t_basla:
    st.session_state.bh_toplama_ozet = None
    st.session_state["bh_toplama_durum"] = ToplamaDurumu(
      hedef=_hedef_yazi(t_uretime, cikarim=False)
    )
    hedef_bankalar = [b for b in bankalari_yukle() if b.kod in t_secili]
    tavan = DEMO_SAYFA_TAVANI if t_demo else None

    def _toplama_isi(is_, *, bankalar=hedef_bankalar, dizin=t_dizin, tavan=tavan):
      """İŞÇİ PARÇACIĞI — burada hiçbir `st.*` çağrılmaz."""
      return topla(
        bankalar,
        gorunmez=True,
        ilerleme=is_.bildir,
        dizin=dizin,
        azami_sayfa=tavan,
        iptal=is_.iptal_edildi_mi,
      )

    st.session_state.bh_is = baslat("toplama", _toplama_isi)
    st.session_state.bh_is_turu = "toplama"
    st.rerun()

  st.divider()

  t_durum = _durum_al("bh_toplama_durum", ToplamaDurumu)

  def _toplama_ciz(durum: ToplamaDurumu, *, akiyor: bool, gecen: float) -> None:
    """Canlı alan — hem koşarken hem bittikten sonra aynı çizim."""
    ust = st.columns(4)
    ust[0].metric("Toplanan sayfa", durum.sayfa)
    ust[1].metric("Keşfedilen URL", durum.kesfedilen)
    ust[2].metric("Atlanan", durum.atlanan)
    ust[3].metric("Geçen süre", f"{gecen:.0f} sn")
    st.markdown(
      ilerleme_cubugu(durum.sayfa, durum.kesfedilen, akiyor=akiyor),
      unsafe_allow_html=True,
    )
    if t_demo and durum.kesfedilen:
      st.caption(
        f"Demo kipinde banka başına yalnız ilk {DEMO_SAYFA_TAVANI} sayfa "
        "çekilir; bu yüzden çubuk sonuna kadar dolmaz."
      )
    st.markdown(
      banka_izgarasi(list(durum.bankalar.values())), unsafe_allow_html=True
    )
    if durum.aktif_url:
      st.caption(f"Son çekilen: {durum.aktif_url}")
    _gunluk_ciz(durum.olaylar, anahtar="bh_t_gunluk")

  if MESGUL and st.session_state.bh_is_turu == "toplama":

    @st.fragment(run_every=0.4)
    def _canli_toplama() -> None:
      is_ = st.session_state.bh_is
      if is_ is None:
        return
      durum = _durum_al("bh_toplama_durum", ToplamaDurumu)
      toplama_olaylarini_isle(durum, olaylari_cek(is_))
      if not is_.calisiyor_mu():
        # Kuyruk SONUNA KADAR boşaltılıp özet devralınır — son olaylar
        # kaybolmasın. Aynı işi betiğin tam koşusu da yapıyor; burası
        # yalnız erken çağırıyor.
        _bekleyen_isi_devral()
        st.rerun(scope="app")
      _toplama_ciz(durum, akiyor=True, gecen=is_.gecen_sure())

    _canli_toplama()

  elif st.session_state.bh_toplama_ozet:
    paket = st.session_state.bh_toplama_ozet
    _toplama_ciz(t_durum, akiyor=False, gecen=paket["sure"])
    _hata_kutusu(paket)

    st.subheader("Koşu özeti")
    if paket["iptal"]:
      st.warning("Koşu İPTAL edildi — sayılar kesildiği ana kadarki ölçümdür.")
    o1, o2, o3, o4 = st.columns(4)
    o1.metric("Süre", f"{paket['sure']:.0f} sn")
    o2.metric("Banka", len(t_durum.bankalar))
    o3.metric("Hata", t_durum.hata)
    o4.metric(
      "sn / sayfa",
      f"{paket['sure'] / t_durum.sayfa:.1f}" if t_durum.sayfa else "—",
    )
    st.caption(f"Yazma hedefi: **{t_durum.hedef}**")

    if t_durum.bankalar:
      df_banka = pd.DataFrame(
        [
          {"Banka": format_bank_name(k.ad), "Sayfa": k.sayfa}
          for k in t_durum.bankalar.values()
        ]
      ).sort_values("Sayfa", ascending=False)
      st.plotly_chart(
        px.bar(
          df_banka, x="Banka", y="Sayfa",
          title="Banka başına toplanan sayfa (ölçülen)",
          color_discrete_sequence=["#00A86B"],
        ),
        use_container_width=True,
      )

    if t_durum.robots_reddi:
      st.info(
        f"**robots.txt {t_durum.robots_reddi} URL'i reddetti** — bu bir kusur değil, "
        "toplama etiğinin kanıtı. Reddedilen adres çekilmedi."
      )
    if t_durum.atlama_sebepleri:
      st.markdown("**Atlama sebepleri**")
      st.dataframe(
        pd.DataFrame(
          [{"Sebep": s, "Adet": a} for s, a in sorted(
            t_durum.atlama_sebepleri.items(), key=lambda x: -x[1])]
        ),
        use_container_width=True, hide_index=True,
      )
  else:
    _toplama_ciz(t_durum, akiyor=False, gecen=0.0)


# === SEKME 2 — ÇIKARIM =====================================================

with sekme_cikarim:
  saglayici_ad, saglayici_model = _saglayici_rozeti()
  oturum_urlleri = set(st.session_state.bh_oturum_urlleri)
  demo_adet = _ham_kayit_sayisi(DEMO_HAM_DIZIN)
  uretim_adet = _ham_kayit_sayisi(HAM_DIZIN)

  c1, c2 = st.columns([1, 1.4])
  with c1:
    c_kip = st.radio(
      "Koşu kipi",
      ["Demo (demo alanındaki kayıtlar)", "Tam koşu (tüm kayıtlar)"],
      key="bh_c_kip",
      disabled=MESGUL,
      help="Demo kipi 1. sekmenin topladığı kayıtlarla çalışır.",
    )
  c_demo = c_kip.startswith("Demo")

  with c2:
    if c_demo:
      secenekler = {
        f"Bu oturumda toplananlar ({len(oturum_urlleri)})": "oturum",
        f"`data/demo_raw` tamamı ({demo_adet})": "demo",
      }
      c_kaynak = secenekler[
        st.selectbox(
          "Kaynak", list(secenekler), key="bh_c_kaynak", disabled=MESGUL,
        )
      ]
      havuz = len(oturum_urlleri) if c_kaynak == "oturum" else demo_adet
    else:
      c_kaynak = "uretim"
      havuz = uretim_adet
      st.selectbox(
        "Kaynak", [f"üretim `data/raw` ({uretim_adet})"], key="bh_c_kaynak_uretim",
        disabled=True,
      )

  if c_demo and havuz > 1:
    # Kaydırak yalnız SEÇİLECEK bir şey varken çizilir: Streamlit
    # `min_value == max_value` olduğunda istisna fırlatır ve sayfa kırılır
    # (tek kayıtlık demo_raw ile ölçüldü).
    c_sinir = st.slider(
      "İşlenecek kayıt adedi", min_value=1, max_value=min(50, havuz),
      value=min(10, havuz), key="bh_c_sinir", disabled=MESGUL,
    )
  elif c_demo:
    c_sinir = havuz
    st.caption(f"Kaynakta **{havuz}** kayıt var — adet sınırına gerek yok.")
  else:
    c_sinir = 0
    st.caption(f"Tam koşu: kaynaktaki **{havuz}** kaydın tamamı işlenir.")

  c_uretime = st.checkbox(
    "Üretim verisine yaz",
    value=False, key="bh_c_uretim", disabled=MESGUL,
    help="İşaretlenmedikçe demo alanına yazılır; diğer ekranlar etkilenmez.",
  )
  c_url = VERITABANI_URL if c_uretime else demo_veritabani()

  st.caption(
    f"Sağlayıcı: **{saglayici_ad} · `{saglayici_model}`** · "
    f"hedef: **{_hedef_yazi(c_uretime, cikarim=True)}** · "
    "eleştirmen, yüklem ajanı ve kanıt denetimi açık."
  )
  if SAGLAYICI_ADI == "ollama":
    st.warning(
      "Yerel model kullanılıyor — kayıt başına yaklaşık 2,5 dakika sürer. "
      "Demo kipinde kayıt sayısını düşük tutun."
    )

  e1, e2, _ = st.columns([1, 1, 3])
  c_basla = e1.button(
    "Çıkarımı Başlat", type="primary", disabled=MESGUL or not havuz,
    use_container_width=True, key="bh_c_basla",
  )
  c_iptal = e2.button(
    "İptal", disabled=not (MESGUL and st.session_state.bh_is_turu == "cikarim"),
    use_container_width=True, key="bh_c_iptal",
  )

  if not havuz:
    st.warning(
      "Bu kaynakta kayıt yok. Önce 1. sekmeden toplama yapın ya da "
      "koşu kipini «Tam koşu» olarak değiştirin."
    )
  if MESGUL and st.session_state.bh_is_turu == "toplama":
    st.info("Şu an bir toplama koşusu sürüyor — aynı anda tek iş çalışır.")

  if c_iptal and st.session_state.bh_is is not None:
    st.session_state.bh_is.iptal_et()
    st.toast("İptal istendi — açık öbek bitince koşu duracak.")

  if c_basla:
    st.session_state.bh_cikarim_ozet = None
    st.session_state["bh_cikarim_durum"] = CikarimDurumu(
      hedef=_hedef_yazi(c_uretime, cikarim=True)
    )

    def _cikarim_isi(
      is_, *, kaynak=c_kaynak, sinir=c_sinir, url=c_url, urller=oturum_urlleri
    ):
      """İŞÇİ PARÇACIĞI — burada hiçbir `st.*` çağrılmaz."""
      if kaynak == "uretim":
        kayitlar = list(ham_kayitlari_oku(HAM_DIZIN))
      elif kaynak == "demo":
        kayitlar = list(ham_kayitlari_oku(DEMO_HAM_DIZIN))
      else:
        # «Bu oturumda toplananlar» İKİ dizinde de aranır: kullanıcı 1.
        # sekmede «üretim boru hattına yaz» kutusunu işaretlediyse o kayıtlar
        # `data/raw`'a düşer. Yalnız demo dizinine bakmak, sayacın N
        # gösterip çıkarımın sıfır kayıt bulmasıyla biterdi.
        kayitlar = [
          k
          for dizin in (DEMO_HAM_DIZIN, HAM_DIZIN)
          for k in ham_kayitlari_oku(dizin)
          if k.url in urller
        ]
      if sinir:
        kayitlar = kayitlar[:sinir]
      return cikarim_kos(
        kayitlar,
        CikarimAyarlari(),
        url=url,
        ilerleme=is_.bildir,
        iptal=is_.iptal_edildi_mi,
      )

    st.session_state.bh_is = baslat("cikarim", _cikarim_isi)
    st.session_state.bh_is_turu = "cikarim"
    st.rerun()

  st.divider()

  c_durum = _durum_al("bh_cikarim_durum", CikarimDurumu)

  def _cikarim_ciz(
    durum: CikarimDurumu, ozet: CikarimOzeti | None, *, akiyor: bool, gecen: float
  ) -> None:
    ust = st.columns(4)
    ust[0].metric("İşlenen kayıt", f"{durum.islenen} / {durum.toplam or '?'}")
    ust[1].metric(
      "sn / kayıt",
      f"{durum.sure_toplami / durum.islenen:.2f}" if durum.islenen else "—",
      help="Kayıt başına ölçülen çıkarım süresi (`rapor.trace_log.toplam_sure`).",
    )
    ust[2].metric("Veritabanına yazılan", durum.yazilan)
    ust[3].metric("Geçen süre", f"{gecen:.0f} sn")
    st.markdown(
      ilerleme_cubugu(durum.islenen, durum.toplam, akiyor=akiyor),
      unsafe_allow_html=True,
    )

    # Koşarken canlı sayaçlar (`durum`), bitince özet — ikisi de ÖLÇÜLEN
    # değer. Özet yetkili kaynaktır: iptal edilmiş koşuda son olay ile
    # veritabanına yazılan arasında fark olabilir.
    sayaclar = (
      {
        "kural": ozet.kural_alan_sayisi,
        "llm": ozet.llm_alan_sayisi,
        "hibrit": ozet.hibrit_alan_sayisi,
      }
      if ozet is not None
      else {"kural": durum.kural, "llm": durum.llm, "hibrit": durum.hibrit}
    )
    sol, sag = st.columns([1, 1])
    with sol:
      st.markdown("**Katman hattı**")
      st.markdown(katman_hatti(sayaclar, akiyor=akiyor), unsafe_allow_html=True)
      st.caption(
        "Çıkarılan alanın hangi katmandan geldiği: yalnız kural motoru, "
        "yalnız LLM, ya da ikisinin uzlaştığı."
      )
    with sag:
      st.markdown("**Son işlenen kayıtlar**")
      st.markdown(kayit_seridi(durum.kayitlar), unsafe_allow_html=True)
      st.caption(
        "Yeşil çubuk: alanların yüzde kaçı dolduruldu · "
        "Mavi çubuk: çıkarılan alanların ortalama güveni"
      )
    _gunluk_ciz(durum.olaylar, anahtar="bh_c_gunluk")

  if MESGUL and st.session_state.bh_is_turu == "cikarim":

    @st.fragment(run_every=0.4)
    def _canli_cikarim() -> None:
      is_ = st.session_state.bh_is
      if is_ is None:
        return
      durum = _durum_al("bh_cikarim_durum", CikarimDurumu)
      cikarim_olaylarini_isle(durum, olaylari_cek(is_))
      if not is_.calisiyor_mu():
        _bekleyen_isi_devral()
        st.rerun(scope="app")
      _cikarim_ciz(durum, None, akiyor=True, gecen=is_.gecen_sure())

    _canli_cikarim()

  elif st.session_state.bh_cikarim_ozet:
    paket = st.session_state.bh_cikarim_ozet
    ozet: CikarimOzeti | None = paket["sonuc"]
    _cikarim_ciz(c_durum, ozet, akiyor=False, gecen=paket["sure"])
    _hata_kutusu(paket)

    if ozet is not None:
      st.subheader("Koşu özeti")
      if ozet.iptal_edildi:
        st.warning("Koşu İPTAL edildi — sayılar kesildiği ana kadarki ölçümdür.")
      m1, m2, m3, m4, m5 = st.columns(5)
      m1.metric("İşlenen kayıt", ozet.kayit_sayisi)
      m2.metric("Süre", f"{ozet.sure:.0f} sn")
      m3.metric("sn / kayıt", f"{ozet.saniye_basina_kayit:.2f}")
      m4.metric("Ort. doluluk", f"%{ozet.ortalama_doluluk * 100:.0f}")
      m5.metric("Ort. güven", f"{ozet.ortalama_guven:.2f}")

      if ozet.kanit_denetimi_hatasi:
        st.warning(
          f"Kanıt denetimi: **{ozet.kanit_denetimi_hatasi} alan** ham metinde "
          "doğrulanamadı."
        )
      else:
        st.success("Kanıt denetimi: tüm değerler ham metinde doğrulandı.")
      if ozet.hatali_kayit:
        st.warning(f"{ozet.hatali_kayit} kayıt çıkarım sırasında hata verdi ve atlandı.")
      st.caption(f"Yazma hedefi: **{c_durum.hedef}** · `{ozet.veritabani_url}`")

      df_katman = pd.DataFrame(
        [
          {"Katman": "Yalnız kural", "Alan": ozet.kural_alan_sayisi},
          {"Katman": "Yalnız LLM", "Alan": ozet.llm_alan_sayisi},
          {"Katman": "Hibrit (uzlaşan)", "Alan": ozet.hibrit_alan_sayisi},
        ]
      )
      st.plotly_chart(
        px.bar(
          df_katman, x="Katman", y="Alan",
          title="Katman katkısı — çıkarılan alan sayısı (ölçülen)",
          color_discrete_sequence=["#00A86B"],
        ),
        use_container_width=True,
      )

      if ozet.celiskiler:
        with st.expander(f"Çelişkiler ({len(ozet.celiskiler)}) — kural ≠ LLM"):
          st.code("\n".join(str(c) for c in ozet.celiskiler[:50]))

      if ozet.kampanyalar:
        st.markdown("**Üretilen kampanyalar**")
        st.caption(
          "Bu kayıtlar demo veritabanına yazıldığı için Genel Bakış'ta görünmez — "
          "verinin gerçekten aktığı burada görülür."
        )
        satirlar = []
        for k in ozet.kampanyalar:
          satirlar.append(
            {
              "Banka": format_bank_name(k.banka_adi),
              "Tür": format_kategori(
                str(k.kampanya_turu.deger) if k.kampanya_turu.var_mi else None
              ),
              "Kâr payı": k.kar_payi_orani.deger if k.kar_payi_orani.var_mi else None,
              "Vade (ay)": k.vade_ay_max.deger if k.vade_ay_max.var_mi else None,
              "Doluluk": round(k.doluluk_orani(), 2),
              "Güven": round(k.ortalama_guven(), 2),
              "Kaynak": k.kaynak_url,
            }
          )
        st.dataframe(pd.DataFrame(satirlar), use_container_width=True, hide_index=True)
  else:
    _cikarim_ciz(c_durum, None, akiyor=False, gecen=0.0)


# === SEKME 3 — VERİ DENETİMİ (A: keşif G-19 · B: tazelik G-17) =============

with sekme_tazelik:
  # ---------------------------------------------------------------------
  # A) YENİ KAMPANYA KEŞFİ (G-19) — «elimizde OLMAYAN kampanya çıktı mı?»
  # ---------------------------------------------------------------------
  st.subheader("A · Yeni Kampanya Keşfi")
  st.markdown(
    "Bankaların kampanya listesi yeniden taranır: **elimizde olmayan yeni "
    "kampanya çıkmış mı?**"
  )
  st.caption(
    "Yalnız liste taranır, kampanya sayfaları indirilmez."
  )

  kesif_taban = kesif_taban_oku()
  kesif_bankalar = _kaziyicili_bankalar()
  ka1, ka2 = st.columns([1.4, 1])
  with ka1:
    k_tum = [kod for kod, _ in kesif_bankalar]
    k_adlar = dict(kesif_bankalar)
    st.session_state.setdefault("bh_k_bankalar", k_tum)
    st.markdown("**Bankalar**")
    kb1, kb2 = st.columns(2)
    if kb1.button(
      f"Tümünü seç ({len(k_tum)})", disabled=MESGUL,
      use_container_width=True, key="bh_k_hepsi",
    ):
      st.session_state.bh_k_bankalar = k_tum
    if kb2.button(
      "Temizle", disabled=MESGUL, use_container_width=True, key="bh_k_temizle"
    ):
      st.session_state.bh_k_bankalar = []
    k_secili = st.multiselect(
      "Bankalar", options=k_tum,
      format_func=lambda kod: k_adlar.get(kod, kod),
      key="bh_k_bankalar", disabled=MESGUL,
      label_visibility="collapsed", placeholder="Banka seçin…",
    )
    st.caption(f"{len(k_secili)} / {len(k_tum)} banka seçili")
  with ka2:
    st.metric("Keşif tabanı", f"{len(kesif_taban)} banka")
    st.caption(
      "İlk keşif taban çizgisi kurar; «kaldırılmış» iddiası ikinci koşudan "
      "itibaren anlamlıdır."
    )

  # SÜRE ÖLÇÜLENDİR: Hayat Finans 9 sn, Albaraka 81 sn (27 Ağu, gerçek koşu).
  st.caption(
    f"Seçili **{len(k_secili)} banka** · banka başına 9–81 saniye · "
    "üretim verisine dokunulmaz."
  )

  kd1, kd2, _ = st.columns([1, 1, 3])
  k_basla = kd1.button(
    "Keşfi Başlat", type="primary", disabled=MESGUL or not k_secili,
    use_container_width=True, key="bh_k_basla",
  )
  k_iptal = kd2.button(
    "İptal", disabled=not (MESGUL and st.session_state.bh_is_turu == "kesif"),
    use_container_width=True, key="bh_k_iptal",
  )

  if not k_secili:
    st.warning("En az bir banka seçin.")
  if MESGUL and st.session_state.bh_is_turu != "kesif":
    st.info("Şu an başka bir koşu sürüyor — aynı anda tek iş çalışır.")

  if k_iptal and st.session_state.bh_is is not None:
    st.session_state.bh_is.iptal_et()
    st.toast("İptal istendi — açık banka bitince duracak.")

  if k_basla:
    st.session_state.bh_kesif_ozet = None
    st.session_state["bh_kesif_durum"] = KesifDurumu()
    k_hedefler = [b for b in bankalari_yukle() if b.kod in k_secili]

    def _kesif_isi(is_, *, bankalar=k_hedefler):
      """İŞÇİ PARÇACIĞI — burada hiçbir `st.*` çağrılmaz."""
      return kesif_kos(
        bankalar, gorunmez=True, ilerleme=is_.bildir, iptal=is_.iptal_edildi_mi
      )

    st.session_state.bh_is = baslat("kesif", _kesif_isi)
    st.session_state.bh_is_turu = "kesif"
    st.rerun()

  k_durum = _durum_al("bh_kesif_durum", KesifDurumu)

  def _kesif_ciz(durum: KesifDurumu, *, akiyor: bool, gecen: float) -> None:
    ku = st.columns(4)
    ku[0].metric(
      "YENİ kampanya", durum.yeni,
      help="Listede olup envanterimizde olmayan adres. Asıl hedef bu sayı.",
    )
    ku[1].metric("Listede bulunan", durum.bulunan)
    ku[2].metric(
      "Kaldırılmış", durum.kaldirilmis,
      help="Önceki keşifte olup bu koşuda listede çıkmayan.",
    )
    ku[3].metric("Geçen süre", f"{gecen:.0f} sn")
    st.markdown(
      ilerleme_cubugu(durum.biten, durum.toplam, akiyor=akiyor),
      unsafe_allow_html=True,
    )
    st.markdown(banka_izgarasi(list(durum.bankalar.values())), unsafe_allow_html=True)
    _gunluk_ciz(durum.olaylar, anahtar="bh_k_gunluk")

  if MESGUL and st.session_state.bh_is_turu == "kesif":

    @st.fragment(run_every=0.4)
    def _canli_kesif() -> None:
      is_ = st.session_state.bh_is
      if is_ is None:
        return
      durum = _durum_al("bh_kesif_durum", KesifDurumu)
      kesif_olaylarini_isle(durum, olaylari_cek(is_))
      if not is_.calisiyor_mu():
        _bekleyen_isi_devral()
        st.rerun(scope="app")
      _kesif_ciz(durum, akiyor=True, gecen=is_.gecen_sure())

    _canli_kesif()

  elif st.session_state.bh_kesif_ozet:
    k_paket = st.session_state.bh_kesif_ozet
    k_ozet = k_paket["sonuc"]
    _kesif_ciz(k_durum, akiyor=False, gecen=k_paket["sure"])
    _hata_kutusu(k_paket)

    if k_ozet is not None:
      if k_ozet.iptal_edildi:
        st.warning(
          "Keşif İPTAL edildi — sayılar kesildiği ana kadarkidir. "
          "Keşfedilen bankalar taban çizgisine yazıldı."
        )
      if k_ozet.toplam_yeni:
        st.warning(
          f"**{k_ozet.toplam_yeni} yeni kampanya bulundu.** Toplamak için "
          "1. sekmeyi kullanın."
        )
        st.dataframe(
          pd.DataFrame(
            [
              {"Banka": format_bank_name(s.banka_adi), "Yeni kampanya adresi": url}
              for s in k_ozet.sonuclar
              for url in s.yeni
            ]
          ),
          use_container_width=True, hide_index=True,
        )
      else:
        st.success(
          "**Listede elimizde olmayan kampanya yok.** Envanter, bankaların "
          "güncel kampanya listeleriyle örtüşüyor."
        )

      if k_ozet.taban_kuruldu_mu:
        st.info(
          "**Keşif tabanı kuruldu.** «Kaldırılmış» iddiası bu koşuda anlamlı "
          "değil: karşılaştırılacak önceki keşif yoktu."
        )

      k_satir = [
        {
          "Banka": format_bank_name(s.banka_adi),
          "Listede": s.bulunan,
          "YENİ": len(s.yeni),
          "Kaldırılmış": len(s.kaldirilmis),
          "Süre (sn)": round(s.sure),
          "Hata": s.hata[:40] if s.hata else "",
        }
        for s in k_ozet.sonuclar
      ]
      if k_satir:
        st.markdown("**Banka bazında**")
        st.dataframe(pd.DataFrame(k_satir), use_container_width=True, hide_index=True)

      kaldirilanlar = [
        (format_bank_name(s.banka_adi), u)
        for s in k_ozet.sonuclar
        for u in s.kaldirilmis
      ]
      if kaldirilanlar:
        with st.expander(f"Listeden düşenler ({len(kaldirilanlar)})"):
          st.caption(
            "Önceki taramada görünüp bu koşuda görünmeyenler. Kampanyanın "
            "bittiği anlamına gelmez — arşive taşınmış olabilir."
          )
          st.dataframe(
            pd.DataFrame(kaldirilanlar, columns=["Banka", "Kaynak"]),
            use_container_width=True, hide_index=True,
          )

      gorunmeyen = sum(s.envanterde_gorunmeyen for s in k_ozet.sonuclar)
      if gorunmeyen:
        with st.expander(f"Envanterde olup listede görünmeyen ({gorunmeyen}) — bilgi"):
          st.caption(
            "Elimizdeki kayıtların bir bölümü kampanya değil ürün sayfası; "
            "kampanya listesinde görünmemeleri normaldir. Bu sayı bir eksiklik "
            "belirtisi değildir."
          )
      st.caption(f"Keşif tabanı: `{k_ozet.taban_dosyasi}`")
  else:
    _kesif_ciz(k_durum, akiyor=False, gecen=0.0)

  st.divider()

  # ---------------------------------------------------------------------
  # B) VERİ TAZELİĞİ (G-17) — «elimizdekiler bayatladı mı?»  DEĞİŞMEDİ
  # ---------------------------------------------------------------------
  st.subheader("B · Elimizdekiler Güncel mi")

  tetikleyici = Tetikleyici()
  taban = taban_oku()

  st.markdown(
    "Elimizdeki kampanya sayfaları **son bakıştan beri değişmiş mi?**"
  )
  st.info(
    "Bu tarama yalnız **tespit eder**, veriyi tazelemez. Değişmiş bir sayfayı "
    "yeniden toplamak 1. sekmeden, sizin kararınızla yapılır."
  )

  z1, z2, z3 = st.columns(3)
  z1.metric("Taban çizgisi", f"{len(taban)} adres")
  z2.metric("Zamanlayıcı", "kurulu değil" if not tetikleyici.kurulu else "kurulu")
  z3.metric(
    "Tasarlanan sıradaki koşu",
    tetikleyici.sonraki_calisma(datetime.now()).strftime("%d %b %H:%M"),
  )
  st.caption(
    "Zamanlayıcı bilerek kapalı: otomatik koşu, üzerinde ölçüm yayımladığımız "
    "veriyi habersiz değiştirebilir. Kurulum satırı hazır, ürünleşince açılır."
  )

  st.divider()

  y1, y2 = st.columns([1, 1.4])
  with y1:
    t_kaynaklar = {
      f"üretim `data/raw` ({uretim_adet})": HAM_DIZIN,
      f"`data/demo_raw` ({demo_adet})": DEMO_HAM_DIZIN,
    }
    z_kaynak_ad = st.selectbox(
      "Kaynak", list(t_kaynaklar), key="bh_z_kaynak", disabled=MESGUL,
      help="Hangi ham kayıt kümesinin adresleri yoklanacak.",
    )
    z_dizin = t_kaynaklar[z_kaynak_ad]
  with y2:
    z_kip = st.radio(
      "Koşu kipi",
      ["Demo (ilk N adres)", "Tam koşu (tüm adresler)"],
      key="bh_z_kip", disabled=MESGUL, horizontal=True,
      help="Nezaket kuralı burada da geçerli: istek arası ≥2 sn.",
    )
  z_demo = z_kip.startswith("Demo")

  z_havuz = _ham_kayit_sayisi(z_dizin)
  if z_demo and z_havuz > 1:
    z_adet = st.slider(
      "Yoklanacak adres", min_value=1, max_value=min(100, z_havuz),
      value=min(20, z_havuz), key="bh_z_adet", disabled=MESGUL,
    )
  elif z_demo:
    z_adet = z_havuz
  else:
    z_adet = z_havuz

  # SÜRE UYARISI ölçülen nezaket kuralından türer, tahmin değil.
  st.caption(
    f"**{z_adet} adres** taranacak · yaklaşık "
    f"**{z_adet * 2 // 60} dk {z_adet * 2 % 60} sn** · üretim verisine dokunulmaz."
  )

  v1, v2, _ = st.columns([1, 1, 3])
  z_basla = v1.button(
    "Tazeliği Denetle", type="primary", disabled=MESGUL or not z_havuz,
    use_container_width=True, key="bh_z_basla",
  )
  z_iptal = v2.button(
    "İptal", disabled=not (MESGUL and st.session_state.bh_is_turu == "tazelik"),
    use_container_width=True, key="bh_z_iptal",
  )

  if not z_havuz:
    st.warning("Bu kaynakta ham kayıt bulunmuyor.")
  if MESGUL and st.session_state.bh_is_turu != "tazelik":
    st.info("Şu an başka bir koşu sürüyor — aynı anda tek iş çalışır.")

  if z_iptal and st.session_state.bh_is is not None:
    st.session_state.bh_is.iptal_et()
    st.toast("İptal istendi — açık yoklama bitince duracak.")

  if z_basla:
    st.session_state.bh_tazelik_ozet = None
    st.session_state["bh_tazelik_durum"] = TazelikDurumu()

    def _tazelik_isi(is_, *, dizin=z_dizin, adet=z_adet):
      """İŞÇİ PARÇACIĞI — burada hiçbir `st.*` çağrılmaz."""
      hedefler = hedefleri_oku(dizin)[:adet]
      return tazelik_denetle(
        hedefler, ilerleme=is_.bildir, iptal=is_.iptal_edildi_mi
      )

    st.session_state.bh_is = baslat("tazelik", _tazelik_isi)
    st.session_state.bh_is_turu = "tazelik"
    st.rerun()

  st.divider()

  z_durum = _durum_al("bh_tazelik_durum", TazelikDurumu)

  def _tazelik_ciz(durum: TazelikDurumu, *, akiyor: bool, gecen: float) -> None:
    ust = st.columns(5)
    ust[0].metric("Değişmedi", durum.degismedi)
    ust[1].metric("Değişti", durum.degisti)
    ust[2].metric(
      "Taban kuruldu", durum.ilk_kayit,
      help="İlk yoklama karşılaştıracak bir şey bulamaz; taban çizgisi kurar "
           "ve değişiklik İDDİA ETMEZ.",
    )
    ust[3].metric("Erişilemedi", durum.erisilemedi)
    ust[4].metric("Geçen süre", f"{gecen:.0f} sn")
    st.markdown(
      ilerleme_cubugu(durum.ilerleyen, durum.toplam, akiyor=akiyor),
      unsafe_allow_html=True,
    )
    if durum.dogrulayici_ile:
      st.caption(
        f"{durum.dogrulayici_ile} adres **sayfa indirilmeden** yanıtlandı — "
        "banka sunucusu «değişmedi» dedi."
      )
    st.markdown(banka_izgarasi(list(durum.bankalar.values())), unsafe_allow_html=True)
    if durum.aktif_url:
      st.caption(f"Son yoklanan: {durum.aktif_url}")
    _gunluk_ciz(durum.olaylar, anahtar="bh_z_gunluk")

  if MESGUL and st.session_state.bh_is_turu == "tazelik":

    @st.fragment(run_every=0.4)
    def _canli_tazelik() -> None:
      is_ = st.session_state.bh_is
      if is_ is None:
        return
      durum = _durum_al("bh_tazelik_durum", TazelikDurumu)
      tazelik_olaylarini_isle(durum, olaylari_cek(is_))
      if not is_.calisiyor_mu():
        _bekleyen_isi_devral()
        st.rerun(scope="app")
      _tazelik_ciz(durum, akiyor=True, gecen=is_.gecen_sure())

    _canli_tazelik()

  elif st.session_state.bh_tazelik_ozet:
    paket = st.session_state.bh_tazelik_ozet
    z_ozet = paket["sonuc"]
    _tazelik_ciz(z_durum, akiyor=False, gecen=paket["sure"])
    _hata_kutusu(paket)

    if z_ozet is not None:
      st.subheader("Yoklama özeti")
      if z_ozet.iptal_edildi:
        st.warning(
          "Yoklama İPTAL edildi — sayılar kesildiği ana kadarkidir. "
          "O ana kadar yoklanan adresler taban çizgisine yazıldı."
        )
      if z_ozet.taban_kuruldu_mu:
        st.info(
          f"**Başlangıç kaydı alındı** ({z_ozet.ilk_kayit} adres). "
          "Değişiklikler bir sonraki taramadan itibaren görünür."
        )
      elif z_ozet.degisti == 0:
        st.success(
          f"**{z_ozet.degismedi} adresin hiçbiri değişmemiş.** "
          "Kayıtlı kampanya verisi güncel."
        )
      else:
        st.warning(
          f"**{z_ozet.degisti} kampanya sayfası değişmiş.** Tazelemek için "
          "Sekme 1'den ilgili bankaları toplayın."
        )

      if z_ozet.degisenler:
        st.markdown("**Değişen kampanyalar**")
        st.dataframe(
          pd.DataFrame(
            [
              {"Banka": format_bank_name(o.banka_adi), "Kaynak": o.url}
              for o in z_ozet.degisenler
            ]
          ),
          use_container_width=True, hide_index=True,
        )

      if z_ozet.robots_reddi:
        st.info(
          f"**robots.txt {z_ozet.robots_reddi} adresi reddetti** — denetim de "
          "bir ziyarettir, kapı burada da işler."
        )
      st.caption(
        f"Taban çizgisi: `{z_ozet.taban_dosyasi}` · "
        f"yoklama süresi {z_ozet.sure:.0f} sn"
      )
  else:
    _tazelik_ciz(z_durum, akiyor=False, gecen=0.0)
