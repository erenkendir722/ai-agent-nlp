"""Müşteri Profili ekranı — sistemin ana ekranı.

Banka çalışanının önündeki müşteriye göre hangi rakip kampanyaların GERÇEKTEN
uygulanabilir olduğunu bulur, toplam maliyete göre sıralar, her gerekçeyi
kaynağına bağlar.

    "Karşımda maaş müşterisi, 800.000 TL konut finansmanı istiyor, 10 yıl
     vade. Rakiplerin hangisi bizden iyi teklif veriyor ve neden?"

İKİ TASARIM KARARI:

1. **Kart, bankanın kendi kampanya listesi gibi okunur.** Solda ne vaat
   edildiği, ortada rakam, sağda eylem. Banka çalışanı bu düzeni tanır.
2. **Ajan izleri panelde açıktır.** Jüri ajan mimarisinin iddiasını değil,
   koşum kaydını görür: hangi ajan LLM kullandı, hangisi kod. "Aritmetiği
   ajana yaptırmıyoruz" cümlesi burada ispatlanır.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ajanlar.muhakeme import MuhakemeAjani, MusteriProfili  # noqa: E402
from src.ajanlar.orkestrator import BILINEN_ALANLAR  # noqa: E402
from src.rag.chatbot import YASAL_UYARI, alan_goster  # noqa: E402
from src.schema import TEK_BIRIMLI_ALANLAR, HedefKitle, alan_etiketi  # noqa: E402
from app.ui_utils import (  # noqa: E402
    format_hedef_kitle,
    inject_custom_css,
    kampanyalari_yukle,
    ortak_kenar,
    sayfa_gezinme,
    sayfa_sonu,
)

st.set_page_config(page_title="Müşteri Profili", page_icon="", layout="wide")
inject_custom_css()
ortak_kenar()
sayfa_gezinme()

st.title("Müşteri Profiline Göre Uygunluk")

# NE YAPTIĞIMIZI İLK EKRANDA SÖYLE (27 Ağustos).
#
# Sayfaya giren kişi önce bir yükleme kutusu, sonra büyük bir uyarı, sonra üç
# sayı görüyordu; ne yaptığımızı anlatan cümle yukarıda kalıp kayboluyordu.
# Şerit `Genel Bakış` sayfasındakiyle aynı `kl-serit` sınıfını kullanır —
# ekranlar arası tek görsel dil.
st.markdown(
    '<div class="kl-serit">Önünüzdeki müşteriyi tanımlayın; hangi rakip '
    "kampanyanın <b>gerçekten uygulanabilir</b> olduğunu ve müşteriye "
    "söylenebilecek toplam maliyeti görün.</div>",
    unsafe_allow_html=True,
)
# Üstte YALNIZ kullanıcının bilmesi gereken kalır: sıralamanın neye göre
# yapıldığı kararı etkiler. «Deterministik kod, dil modeli çalışmaz» iddiası
# yöntem anlatımıdır — sayfanın en altına, ajan izleri panelinin yanına indi.
st.caption(
    "Kampanya listesi değil, **kısıt çözümü**. Sıralama **manşet orana değil, "
    "toplam maliyete** göre yapılır."
)


kampanyalar = kampanyalari_yukle()

# ---------------------------------------------------------------------------
# Girdi — ANA ALANIN ÜSTÜNDE (27 Ağustos)
# ---------------------------------------------------------------------------
#
# Form eskiden kenar çubuğundaydı ve `ortak_kenar()` marka bloğunu ÖNCE
# yazdığı için en alta düşüyordu: sayfanın tek etkileşimli parçası, dizüstü
# ekranında kaydırmadan görünmüyordu. Yukarı alındı — giren kişi ilk bakışta
# hem ne yaptığımızı hem neyi değiştirebileceğini görüyor.

MUSTERI_TIPI_SECENEKLERI = [
    HedefKitle.MAAS_MUSTERISI,
    HedefKitle.YENI_MUSTERI,
    HedefKitle.MEVCUT_MUSTERI,
    HedefKitle.SEGMENT,
    HedefKitle.TUM_MUSTERILER,
]

with st.container(border=True):
    st.markdown("**Müşteri bilgileri**")
    s1, s2, s3, s4 = st.columns([2, 2, 1, 3])

    tip = s1.selectbox(
        "Müşteri tipi",
        options=MUSTERI_TIPI_SECENEKLERI,
        format_func=format_hedef_kitle,
    )
    tutar = s2.number_input(
        "Finansman tutarı (TL)", min_value=1_000, max_value=50_000_000,
        value=800_000, step=50_000,
    )
    vade = s3.number_input(
        "Vade (ay)", min_value=1, max_value=360, value=120, step=12
    )
    mevcut_urunler = s4.multiselect(
        "Müşterinin mevcut ürünleri",
        options=["maaş hesabı", "kredi kartı", "katılma hesabı", "sigorta", "otomatik ödeme"],
        placeholder="Varsa seçin",
        help="Zorunlu ürün koşulu olan kampanyalar bunlara göre değerlendirilir.",
    )

    # Segment adı yalnız gerektiğinde çıkar; her zaman duran boş bir kutu
    # kullanıcıya «burayı doldurmalı mıyım» diye sordururdu.
    segment = None
    if tip == HedefKitle.SEGMENT:
        segment = s1.text_input("Segment adı", value="emekli")

profil = MusteriProfili(
    musteri_tipi=tip,
    tutar=float(tutar),
    vade_ay=int(vade),
    mevcut_urunler=list(mevcut_urunler),
    segment=segment,
)

sonuclar, iz = MuhakemeAjani().calistir((profil, kampanyalar))
uygunlar = [s for s in sonuclar if s.uygun_mu]
elenenler = [s for s in sonuclar if not s.uygun_mu]
kayit_dizini = {k.kampanya_id: k for k in kampanyalar}

# ---------------------------------------------------------------------------
# Dürüstlük kapısı
# ---------------------------------------------------------------------------

dogrulanmamis = sum(1 for s in uygunlar if s.veri_eksik)
toplam_uygun = len(uygunlar)
maliyetli = sum(1 for s in uygunlar if s.maliyet)

# ÖLÇÜLER ÖNCE, UYARI SONRA (27 Ağustos). Uyarı en üstteydi ve ekranın en
# büyük ögesiydi; kullanıcı daha ne baktığını bilmeden bir kusur listesi
# okuyordu. Önce sonuç, sonra sonucun sınırı.
ust1, ust2, ust3 = st.columns(3)
ust1.metric(
    "Uygun kampanya", toplam_uygun,
    help="Seçilen müşteri profili (vade, tutar, segment) kısıtlarına uyan toplam kampanya sayısı.",
)
ust2.metric(
    "Elenen", len(elenenler),
    help="Kısıtlara uymadığı için kural motoru tarafından elenen kampanyalar.",
)
ust3.metric(
    "Maliyeti hesaplanan", maliyetli,
    help="Kâr payı ve masraf verisi eksiksiz olup toplam geri ödemesi hesaplanabilenler.",
)

# «Maliyeti hesaplanan: 4» sıradan üçüncü bir sayı gibi duruyordu; oysa
# sayfanın asıl sınırı bu. «Toplam maliyete göre sıralı» iddiası yalnız o
# kayıtlar için geçerli, kalanlar maliyetsiz sıralanıyor. Söylemek zorundayız.
if toplam_uygun and maliyetli < toplam_uygun:
    ust3.caption(
        f"{toplam_uygun} uygun kampanyanın {maliyetli} tanesi. "
        "Maliyet sıralaması yalnız bunları kapsar."
    )

# UYARI KUTUSU KALDIRILDI (27 Agustos). Ayni bilgi «Maliyeti hesaplanan»
# olcusunun altindaki aciklamada zaten yaziyor; sari kutu onu ikinci kez, iki
# kat buyuk ve alarm renginde tekrarliyordu. Kisit dogrulanamamasi bir ARIZA
# degil, kaynak verinin ozelligi — alarm rengi yanlis bilgi veriyordu.
# Kart basina da yaziliyor (asagida `veri_eksik`), yani ucuncu kopyaydi.

# ---------------------------------------------------------------------------
# Uygun kampanyalar
# ---------------------------------------------------------------------------


def _tl(deger: float) -> str:
    return f"{deger:,.0f} TL".replace(",", ".")


def _kisalt(metin: str, sinir: int = 155) -> str:
    metin = " ".join(str(metin).split())
    return metin if len(metin) <= sinir else metin[: sinir - 1].rstrip() + "…"

def _bilinen_alanlar(kampanya) -> list[tuple[str, str]]:
    """Kâr payı yoksa kartın SUSMAMASI için bu kayıtta dolu olan alanlar.

    LİSTE ELLE YAZILMAZ (CLAUDE.md, 27 Ağustos). Karşılaştırma motorunun
    kıyasladığı alanlardan (`ALAN_YONLERI`) kâr payı çıkarılarak türeyen
    `BILINEN_ALANLAR` kullanılır; yeni bir ölçüt oraya eklenince burada da
    kendiliğinden görünür. Chatbot'un profil cevabı da aynı listeden okuyor —
    iki ekranın aynı kayıt için farklı şey göstermesi böyle engellenir.

    BİRİM ŞART: tek birimli alanlarda sözleşmeden (`TEK_BIRIMLI_ALANLAR`),
    çok birimlide taşıyıcı `Alan`'dan çözülür. Birimsiz gösterim `%0,50`
    olarak çıkarılmış bir tahsis ücretini «0,50 TL» yazardı.
    """
    if kampanya is None:
        return []
    satirlar: list[tuple[str, str]] = []
    for alan_adi in BILINEN_ALANLAR:
        alan = getattr(kampanya, alan_adi, None)
        if alan is None or alan.deger is None:
            continue
        birim = TEK_BIRIMLI_ALANLAR.get(alan_adi) or alan.birim
        satirlar.append(
            (alan_etiketi(alan_adi), alan_goster(alan_adi, alan.deger, birim))
        )
    return satirlar


st.subheader("Uygun kampanyalar")
# SIRALAMA IDDIASI KOSULA BAGLI (CLAUDE.md, 27 Agustos): hicbir kalemin
# maliyeti hesaplanamadiginda «toplam maliyete gore sirali» demek, yapilmamis
# bir siralamayi yapilmis gibi sunmaktir.
st.caption(
    (
        "Maliyeti hesaplanabilenler başta, toplam geri ödemeye göre sıralı. "
        if maliyetli
        else "Bu profilde hiçbir kampanyanın kâr payı oranı yayımlanmamış; "
        "maliyet sıralaması yapılamadı. "
    )
    + "**Devam et** bankanın kendi sayfasını açar, **Detay** kampanyanın "
    "kayıt dökümüne götürür."
)

if not uygunlar:
    st.info("Bu profile uyan kampanya bulunamadı. Tutarı ya da vadeyi değiştirip tekrar deneyin.")

for sira, sonuc in enumerate(uygunlar[:15], 1):
    kampanya = kayit_dizini.get(sonuc.kampanya_id)
    with st.container(border=True):
        sol, orta, sag = st.columns([4.1, 3.5, 1.7])

        # -- SOL: kurum ve kampanyanin ne vaat ettigi --------------------
        #
        # Eskiden burada yalniz banka adi ve «Kaynaga git» bagi vardi; kartin
        # geri kalani «Belirtilmemis» diyordu. Oysa maliyeti hesaplanamayan
        # 179 kaydin 148'inde `kampanya_avantaji` DOLU — kampanyanin ne
        # verdigi yaziyor. Bos bir hucre gostermek yerine elimizdekini
        # gosteriyoruz.
        with sol:
            st.markdown(
                f'<div class="kl-kart-ad">{sira}. {sonuc.banka_adi}</div>',
                unsafe_allow_html=True,
            )
            aciklama = ""
            if kampanya is not None and kampanya.kampanya_avantaji.var_mi:
                aciklama = _kisalt(kampanya.kampanya_avantaji.deger)
            if aciklama:
                st.markdown(
                    f'<div class="kl-kart-alt">{aciklama}</div>', unsafe_allow_html=True
                )
            elif sonuc.veri_eksik:
                st.markdown(
                    '<div class="kl-kart-alt">Kampanya koşulları kaynak sayfada '
                    "ayrıntılı verilmemiş.</div>",
                    unsafe_allow_html=True,
                )

        # -- ORTA: rakamlar ----------------------------------------------
        with orta:
            if sonuc.maliyet:
                d1, d2 = st.columns(2)
                d1.markdown(
                    '<div class="kl-kart-etiket">Toplam geri ödeme</div>'
                    f'<div class="kl-kart-deger">{_tl(sonuc.maliyet["toplam_geri_odeme"])}</div>',
                    unsafe_allow_html=True,
                )
                d2.markdown(
                    '<div class="kl-kart-etiket">Aylık taksit</div>'
                    f'<div class="kl-kart-deger">{_tl(sonuc.maliyet["aylik_taksit"])}</div>',
                    unsafe_allow_html=True,
                )
            else:
                # «BELIRTILMEMIS» DEV PUNTODA YAZILMIYOR ARTIK.
                #
                # Olculdu: uygun 183 kaydin 179'unda (%98) `kar_payi_orani`
                # HIC YOK — bankalar orani kampanya sayfasinda degil basvuru
                # ekraninda veriyor. Yani bu bir cikarim zaafi degil, kaynak
                # verinin ozelligi. Paranin durdugu yerde dev puntoyla
                # «Belirtilmemis» yazmak, olmayan bir kusuru ekranin en
                # buyuk ogesi yapiyordu. Elimizde ne varsa o gosteriliyor.
                bilinen = _bilinen_alanlar(kampanya)
                if bilinen:
                    for _s, (_e, _d) in zip(st.columns(2), bilinen[:2], strict=False):
                        _s.markdown(
                            f'<div class="kl-kart-etiket">{_e}</div>'
                            f'<div class="kl-kart-deger">{_d}</div>',
                            unsafe_allow_html=True,
                        )
                st.markdown(
                    '<div class="kl-kart-alt">Kâr payı oranı bu sayfada '
                    "yayımlanmamış — maliyet hesaplanamıyor.</div>",
                    unsafe_allow_html=True,
                )

        # -- SAG: eylemler -----------------------------------------------
        with sag:
            if kampanya is not None:
                st.link_button(
                    "Devam et", kampanya.kaynak_url, use_container_width=True, type="primary"
                )
                if st.button("Detay", key=f"mp_detay_{sonuc.kampanya_id}", use_container_width=True):
                    # Banka Profili sayfasi bu iki anahtari okur: ilki banka
                    # secicisini, ikincisi vurgulanacak kampanyayi kurar.
                    st.session_state["bp_secili_banka"] = kampanya.banka_kodu
                    st.session_state["bp_vurgu_kampanya"] = sonuc.kampanya_id
                    st.switch_page("pages/5_Banka_Profili.py")

        # Gercekten DEGERLENDIRILMIS bir kisit varsa gerekce gosterilir.
        # Kisit verisi olmayan kayitta cumle her kartta ayniydi (302/331) ve
        # ayni bilgi zaten yukarida.
        if not sonuc.veri_eksik:
            for gerekce in sonuc.gerekceler:
                st.caption(str(gerekce))

# ELENENLER BOLUMU KALDIRILDI (27 Agustos).
#
# «Uygun olmayanlar ve sebepleri» 15 kart daha basiyordu ve sayfanin alt
# yarisini kaplıyordu. Elenen sayisi ust olculerde duruyor; banka calisani
# musteriye SUNULABILECEK teklifi ariyor, sunulamayacaklarin dokumunu degil.
# Eleme mantiginin denetlenebilirligi kayboldu sayilmaz: `Elenen` olcusu,
# ajan izleri paneli ve `make eval` ciktisi ayni bilgiyi tasiyor.

# Ajan izleri — mimarinin kanıtı
# ---------------------------------------------------------------------------

with st.expander(f"Nasıl hesaplandı? — {iz.ajan_adi} · {iz.sure_ms} ms", expanded=False):
    st.code(iz.satir(), language=None)
    st.caption(
        f"Bu ekranda dil modeli çağrısı: **{0 if not iz.llm_kullanildi else 1}**. "
        "Kısıt çözümü ve taksit hesabı deterministik koddur — aynı girdi her "
        "zaman aynı sonucu verir."
    )

st.caption(f"_{YASAL_UYARI}_")

st.divider()
if uygunlar:
  st.subheader("Teklif Raporu Çıktısı")
  st.caption("Müşteriye sunulmak üzere hazırlanan özel teklif özetini indirebilirsiniz.")
  
  rapor_metni = f"MÜŞTERİ TEKLİF FORMU\n------------------\nFinansman Tutarı: {_tl(profil.tutar)}\nVade: {profil.vade_ay} Ay\nMüşteri Tipi: {tip.value}\n\nUYGUN KAMPANYALAR:\n"
  for i, s in enumerate(uygunlar[:5], 1):
      maliyet_str = _tl(s.maliyet['toplam_geri_odeme']) if s.maliyet else "Belirtilmemiş"
      rapor_metni += f"{i}. {s.banka_adi} - Toplam Geri Ödeme: {maliyet_str}\n"
  
  st.download_button(
      label="Teklif raporunu indir (TXT)",
      data=rapor_metni,
      file_name="musteri_teklif_formu.txt",
      mime="text/plain",
      type="primary"
  )

sayfa_sonu()
