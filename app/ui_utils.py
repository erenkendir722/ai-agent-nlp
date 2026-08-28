"""Arayüz yardımcıları — grafik ve tablo etiketleri.

Banka kısa adları `data/banks.yaml`'daki `kisa_ad` alanından okunur. Burada
ikinci bir sözlük TUTULMAZ: elle yazılan kopya 16 Ağustos'ta kayıt defteriyle
yedi bankada ayrışmıştı ("Türkiye Emlak Katılım Bankası A.Ş." kayıt defterinde
"Emlak Katılım", kopyada hiç eşleşmiyordu). Kayıt defteri tek doğruluk kaynağı.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from src.collector.toplayici import bankalari_yukle
from src.schema import alan_etiketi, tur_etiketi

_SONUC_DOSYASI = Path(__file__).resolve().parents[1] / "docs" / "SONUCLAR.md"


@dataclass(frozen=True)
class EvalOzeti:
    """`docs/SONUCLAR.md` — sunum ve arayüz aynı kaynaktan okur."""

    # Hepsi ORAN (0–1). `eval/calistir.py` da aynı birimi kullanır; markdown
    # tablosundaki "%0.45" yüzdeye çevrilmiş hâlidir, burada geri oran yapılır.
    halusinasyon_orani: float | None = None
    makro_f1: float | None = None
    makro_f1_ga: tuple[float, float] | None = None
    sayisal_dogruluk: float | None = None
    sema_gecerliligi: float | None = None
    altin_set_n: int | None = None
    kampanya_sayisi: int | None = None


def sonuclari_oku(yol: Path | None = None) -> EvalOzeti:
    """`make eval` çıktısını parse eder. Elle yazılmış sayı kullanılmaz."""
    dosya = yol or _SONUC_DOSYASI
    if not dosya.is_file():
        return EvalOzeti()
    metin = dosya.read_text(encoding="utf-8")

    def _ara(desen: str) -> str | None:
        m = re.search(desen, metin)
        return m.group(1) if m else None

    def _float(ham: str | None) -> float | None:
        if ham is None or ham == "ölçülmedi":
            return None
        return float(ham.replace(",", "."))

    def _yuzde(ham: str | None) -> float | None:
        """Tabloda yüzde yazan alanı ORANA çevirir: "0.45" -> 0.0045.

        Bu bölme olmadan alan, adının söylediği şey (oran) değil yüzde tutar;
        çizim yerinde ikinci kez 100'le çarpılınca halüsinasyon oranı ekranda
        %0,45 yerine %45 görünür. 26 Ağustos'ta jüri provasında yakalandı.
        """
        deger = _float(ham)
        return None if deger is None else deger / 100

    ga = re.search(
        r"\*\*Makro-F1\*\* \| [0-9.]+ _\(%95 GA: ([0-9.]+)[–-]([0-9.]+)\)_",
        metin,
    )
    return EvalOzeti(
        halusinasyon_orani=_yuzde(_ara(r"\*\*Halüsinasyon oranı\*\* \| %([0-9.,]+)")),
        makro_f1=_float(_ara(r"\*\*Makro-F1\*\* \| ([0-9.]+)")),
        makro_f1_ga=(float(ga.group(1)), float(ga.group(2))) if ga else None,
        sayisal_dogruluk=_float(_ara(r"Sayısal alan doğruluğu \| ([0-9.]+|ölçülmedi)")),
        sema_gecerliligi=_float(_ara(r"Şema geçerliliği \| ([0-9.]+)")),
        altin_set_n=int(n) if (n := _ara(r"Altın set boyutu: \*\*(\d+)\*\*")) else None,
        kampanya_sayisi=int(k) if (k := _ara(r"İşlenen kampanya: \*\*(\d+)\*\*")) else None,
    )


# ---------------------------------------------------------------------------
# Renk paleti — TEK KAYNAK
# ---------------------------------------------------------------------------
#
# NEDEN VAR: altı ekranda beş ayrı renk dili vardı. Genel Bakış yeşil
# (`#00A86B`) çiziyor, Banka Profili plotly'nin varsayılan mavisiyle ve AÇIK
# temayla çiziyordu (koyu sayfada beyaz bir kutu), karşılaştırma tablosu
# güven skorunu yeşil/sarı/kırmızı, kâr payını dört tonda maviye boyuyordu.
# Aynı uygulamanın iki ekranı birbirine benzemiyordu.
#
# Kural: renk YALNIZ üç şey söyler — vurgu (ana), ikinci seri (ikincil),
# dikkat (uyarı). Bir SAYIYI ölçeğe göre boyamak bunlardan hiçbiri değil:
# «0,82 güven» sarı olunca kullanıcı bir kusur arıyor, oysa eşik yok.
RENK_ANA = "#00A86B"
RENK_IKINCIL = "#2E7D9A"
RENK_UYARI = "#D9A441"
RENK_SOLUK = "#6E6E78"
GRAFIK_SIRASI = [RENK_ANA, RENK_IKINCIL, RENK_UYARI, "#8E7CC3", "#C4707A"]


def grafik_duzeni(sekil, *, yukseklik: int | None = None, baslik: str | None = None):
    """Her grafiğe aynı zemin, aynı kenar boşluğu, aynı ızgara.

    Sayfalar bunu ELLE yazıyordu ve her biri başka yazıyordu: kimi
    `template="plotly_dark"` veriyor kimi vermiyor, kenar boşlukları dört
    farklı değerdeydi. Tek çağrı — grafikler birbirine benzesin.
    """
    sekil.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 0, "r": 8, "t": 30 if baslik else 10, "b": 0},
        height=yukseklik,
        title=baslik,
        font={"size": 12},
    )
    # `automargin` ŞART (28 Ağustos). Kenar boşluğu `l: 0` verildiği için
    # yatay çubuk grafiklerinde uzun kategori etiketleri («Azami finansman
    # tutarı», «İhtiyaç Finansmanı») sola taşıp KIRPILIYORDU: ekranda yarım
    # kelimeler ve boşluklar görünüyordu. `automargin` etiketin gerçek
    # genişliğini ölçüp yer açar — sabit bir sol boşluk yazmak, en uzun
    # etiket değiştiğinde yine kırpardı.
    sekil.update_xaxes(showgrid=False, automargin=True)
    sekil.update_yaxes(showgrid=False, automargin=True)
    return sekil


def tr_sayi(deger: float, basamak: int = 2) -> str:
    """0.724 → '0,72' — sunumda sahte kesinlik yok."""
    return f"{deger:.{basamak}f}".replace(".", ",")

# Kayıt defterinde olmayan bir banka için başlığı kısaltırken atılan ekler.
_EKLER = (
    " Katılım Bankası A.Ş.",
    " Bankası A.Ş.",
    " Katılım A.Ş.",
    " A.Ş.",
    " Anonim Şirketi",
)

_AZAMI_UZUNLUK = 15


@lru_cache(maxsize=1)
def _kisa_adlar() -> dict[str, str]:
    """banks.yaml'daki tam ad -> kısa ad eşlemesi (bir kez okunur)."""
    return {b.ad: b.kisa_ad for b in bankalari_yukle()}


def format_bank_name(bank_name: str | None) -> str:
    """Banka adını grafiklerde göstermek için standartlaştırır."""
    if not bank_name:
        return "Belirtilmemiş"

    temiz_girdi = bank_name.strip()
    kisa = _kisa_adlar().get(temiz_girdi)
    if kisa:
        return kisa

    # Kayıt defterinde yoksa (yeni banka, serbest metinden gelen ad) ekleri at.
    kisaltilmis = temiz_girdi
    for ek in _EKLER:
        kisaltilmis = kisaltilmis.replace(ek, "")
    kisaltilmis = kisaltilmis.strip()

    if len(kisaltilmis) > _AZAMI_UZUNLUK:
        return kisaltilmis[:_AZAMI_UZUNLUK] + "..."

    return kisaltilmis


_KAMPANYASI_EKI = " Kampanyası"


def format_kategori(kategori_adi: str | None) -> str:
    """Kampanya türünün tablo/etiket gösterimi — kaynağı ŞEMA.

    İKİNCİ SÖZLÜK TUTULMAZ (bu dosyanın başındaki kuralın aynısı). Burada
    elle yazılmış bir `_KATEGORI_ISIMLERI` sözlüğü vardı ve dört türü
    (`alisveris_puani`, `yeni_musteri`, `kart`, `finansman`) hiç içermiyordu.
    Eksik türler `.title()` yedeğine düşüyor, Türkçe harfleri kaybediyordu:

        alisveris_puani  ->  "Alisveris Puani"   (ş ve ı yok)
        yeni_musteri     ->  "Yeni Musteri"      (ü yok)

    Bu yazımlar karşılaştırma tablosunda ve süzgeç açılırında görünüyordu.
    `schema.KAMPANYA_TURU_ETIKETLERI` doğru yazımları zaten tutuyor ve
    `.title()`'ın Türkçe'yi bozduğu o dosyada da yazılı.

    Şema uzun etiket verir («Konut Finansmanı Kampanyası»); tablo sütununda
    ve açılır listede tür adı yeter, «Kampanyası» eki her satırda tekrar
    ederdi. Ek yalnız GÖSTERİMDEN düşürülür, sözlükten değil.
    """
    if not kategori_adi:
        return "Belirtilmemiş"

    ham = str(kategori_adi).strip()
    etiket = tur_etiketi(ham)
    if not etiket:
        # Şemada olmayan serbest metin (`urun_turu`) olduğu gibi gösterilir:
        # `.title()` uygulamak «Alisveris» türü bozulmalara geri dönüş olurdu.
        return ham

    if etiket.endswith(_KAMPANYASI_EKI):
        return etiket[: -len(_KAMPANYASI_EKI)]
    return etiket


_HEDEF_KITLE_ETIKETLERI = {
    "yeni_musteri": "Yeni müşteri",
    "mevcut_musteri": "Mevcut müşteri",
    "maas_musterisi": "Maaş müşterisi",
    "segment": "Segment (emekli / öğrenci / KOBİ)",
    "tum_musteriler": "Tüm müşteriler",
}
"""Hedef kitle enum değeri → ekranda yazılan etiket.

Şemaya DEĞİL buraya konuyor. `src/schema.py` hem donmuş hem de
`CIKARIM_KAYNAKLARI` içinde: oraya eklenen her satır çıkarım parmak izini
değiştirir ve veritabanını «bayat» ilan eder. Salt gösterim için ölçümü
bayatlatmak orantısız olurdu; etiketin veriyle bir ilgisi yok.
"""


def format_hedef_kitle(deger) -> str:
    """`yeni_musteri` → «Yeni müşteri»."""
    if deger is None:
        return "Belirtilmemiş"
    ham = getattr(deger, "value", deger)
    return _HEDEF_KITLE_ETIKETLERI.get(str(ham).strip().lower(), str(ham))


def format_alan_adi(alan_adi: str) -> str:
    """Alan adının ekranda yazılan hâli — kaynağı ŞEMA.

    `.replace("_", " ").title()` KULLANILMAZ. `schema.ALAN_ETIKETLERI`'nin
    kendi notunda yazdığı gibi `.title()` Türkçe'yi sessizce bozar:

        kar_payi_orani  ->  "Kar Payi Orani"   (â ve ı kayıp)
        alisveris_puani ->  "Alisveris Puani"  (ş ve ı kayıp)

    Bu yazımlar karşılaştırma ekranındaki kampanya kartlarında görünüyordu.
    """
    return alan_etiketi(alan_adi) or alan_adi.replace("_", " ")


@st.cache_data(ttl=60, show_spinner=False)
def _kampanyalari_oku():
    """Veritabanı okuması — ÖNBELLEKLİ.

    Ölçüldü: 931 kaydın ilk okuması ~400 ms, sonraki ~90 ms. Karşılaştırma ve
    Chatbot bu okumayı önbelleksiz yapıyordu; Karşılaştırma'daki dört kaydırıcı
    her harekette sayfayı baştan koşturduğu için her tıklamada bedel ödeniyordu.
    """
    from src.depolama import tum_kayitlar

    return tum_kayitlar()


@st.cache_data(ttl=60, show_spinner=False)
def _kampanya_nesnelerini_oku():
    """Şema nesnesi olarak okuma — `Alan` ve `uygunluk` erişimi gerektiğinde.

    `_kampanyalari_oku`dan AYRI tutuluyor çünkü döndürdükleri tip farklı:
    biri düz satır (`KampanyaKaydi`), bu ise tam şema nesnesi (`Kampanya`).
    Tek fonksiyona zorlamak, çağıranın hangi tipi aldığını belirsizleştirirdi.
    """
    from src.depolama import kampanyalari_oku

    return list(kampanyalari_oku())


def _veri_hatasi(hata: Exception) -> None:
    """Okuma hatasının TEK sunumu — altı sayfa aynı cümleyi görsün."""
    st.error("Kampanya verisine ulaşılamadı.")
    st.caption("Veritabanı dosyası eksik ya da tablo şeması uyumsuz olabilir.")
    if st.session_state.get("dev_mode", False):
        with st.expander("Teknik teşhis"):
            st.code(f"{type(hata).__name__}: {hata}")


def _veri_yok(bos_mesaji: str | None) -> None:
    """Boş veri durumunun TEK sunumu.

    Terminal komutu YAZMAZ. Aynı işi yapan «Canlı Boru Hattı» ekranı var;
    kullanıcıyı terminale göndermek gereksiz.
    """
    st.info(
        bos_mesaji
        or "Henüz kampanya verisi yok. **Canlı Boru Hattı** ekranından "
        "toplama ve çıkarım çalıştırabilirsiniz."
    )


def kampanyalari_yukle(*, bos_mesaji: str | None = None):
    """Şema nesnesi olarak yükler (`Alan`, `uygunluk` erişimi için)."""
    try:
        with st.spinner("Kampanya verisi okunuyor…"):
            kampanyalar = _kampanya_nesnelerini_oku()
    except Exception as hata:  # noqa: BLE001 — sebebi kullanıcıya gösteriliyor
        _veri_hatasi(hata)
        st.stop()

    if not kampanyalar:
        _veri_yok(bos_mesaji)
        st.stop()

    return kampanyalar


def kayitlari_yukle(*, bos_mesaji: str | None = None):
    """Kampanya kayıtlarını yükler; olmazsa sayfayı DURDURUR.

    NEDEN ORTAK — 27 Ağustos'ta ölçüldü: aynı blok altı sayfada kopyalanmıştı ve
    aynı durum için ÜÇ FARKLI cümle gösteriyordu:

        «Yerel veritabanına ulaşılamadı veya tablo bulunamadı.»        3 sayfa
        «Görüntülenecek kampanya verisi bulunamadı. Önce `make crawl`…» 2 sayfa
        «Veritabanı boş. `make crawl && make extract` çalıştırın.»      2 sayfa

    Kullanıcı hangi sayfada olduğuna göre başka cümle görüyordu. İkisi ayrıca
    terminal komutu yazıyordu; oysa aynı işi yapan «Canlı Boru Hattı» ekranı
    var — kullanıcıyı terminale göndermek gereksiz.

    `st.stop()` burada çağrılır: çağıran sayfa veri yokken çizmeye devam
    ederse boş listeyle hesap yapıp yanlış sıfırlar gösterir.
    """
    try:
        with st.spinner("Kampanya verisi okunuyor…"):
            kayitlar = _kampanyalari_oku()
    except Exception as hata:  # noqa: BLE001 — sebebi kullanıcıya gösteriliyor
        _veri_hatasi(hata)
        st.stop()

    if not kayitlar:
        _veri_yok(bos_mesaji)
        st.stop()

    return kayitlar


def uyarilari_goster(
    uyari_listesi,
    *,
    baslik: str = "Karşılaştırma notları",
    panelde_topla: bool = False,
) -> None:
    """Uyarıları ÖNEMİNE göre ayırarak çizer.

    NEDEN VAR — 26 Ağustos'ta ölçüldü: her uyarı ayrı bir `st.warning` kutusuydu.
    Dört özdeş sarı kutu 1.060 karakterle ekranı dolduruyor, cevabı ve kaynakları
    aşağı itiyordu. Hepsi aynı ağırlıkta göründüğü için kullanıcı hangisinin
    kararını değiştirdiğini seçemiyordu.

    Ayrım şu: `engelleyici` uyarı bir kriteri SIRALAMADAN DÜŞÜRÜR — kullanıcı
    onu görmeden karar veremez, o yüzden açıkta durur. Kalanlar bağlam notudur
    («farklı türler karşılaştırılıyor»); bilinmesi iyidir ama ekranı kapatmamalı,
    katlanabilir tek panelde toplanır.

    Metin taşımayan sade `str` uyarılar da kabul edilir: `engelleyici` alanı
    olmayan her şey bağlam notu sayılır. Böylece bu yardımcı, uyarıyı nereden
    alırsa alsın (API, chatbot, karşılaştırma) çalışır.
    """
    if not uyari_listesi:
        return

    # `panelde_topla` — ENGELLEYICI UYARI DA PANELE GIRER (27 Agustos).
    #
    # Ayrim normalde dogru: engelleyici uyari bir olcutu siralamadan dusurur,
    # kullanici onu gormeden karar veremez. Ama Karsilastirma ekraninda o uyari
    # SABIT: tahsis ucreti alani her zaman karisik birimde oldugu icin kutu her
    # acilista cikiyordu. Her koside cikan bir uyari, uyari olmaktan cikip
    # arayuzun bir parcasi olur ve okunmaz. Bilgi silinmez, panele iner.
    if panelde_topla:
        engelleyiciler = []
        notlar = list(uyari_listesi)
    else:
        engelleyiciler = [u for u in uyari_listesi if getattr(u, "engelleyici", False)]
        notlar = [u for u in uyari_listesi if not getattr(u, "engelleyici", False)]

    # SARI ALARM KUTUSU YERİNE SAKİN NOT ŞERİDİ (28 Ağustos).
    #
    # `st.warning` bankacılık arayüzünde bir ŞEY BOZULDU der: tam genişlikte,
    # sarı zemin, ünlem simgesi. Buradaki uyarıların hiçbiri arıza değil —
    # «tahsis ücreti karışık birimde, sıralamaya katılmadı» bir ÖLÇÜM
    # beyanıdır. Alarm rengi kullanıcıyı olmayan bir sorunu aramaya itiyordu.
    #
    # Bilgi aynen duruyor, yalnız tonu düştü: ince amber çizgi + koyu zemin.
    # Rengin alarm anlamı böylece gerçek hatalara (`st.error`) saklanır.
    for uyari in engelleyiciler:
        st.markdown(
            f'<div class="kl-not">{_uyari_metni(uyari, html=True)}</div>',
            unsafe_allow_html=True,
        )

    if not notlar:
        return

    # Tek not için panel açıp kapamak gereksiz tıklama; doğrudan gösterilir.
    if len(notlar) == 1:
        st.markdown(
            f'<div class="kl-not kl-not-soluk">{_uyari_metni(notlar[0], html=True)}</div>',
            unsafe_allow_html=True,
        )
        return

    with st.expander(f"{baslik} ({len(notlar)})", expanded=False):
        for uyari in notlar:
            st.markdown(_uyari_metni(uyari))


def _uyari_metni(uyari, *, html: bool = False) -> str:
    """Başlığı kalın, detayı alt satırda. Markdown'da satır sonu iki boşluktur.

    `html=True` aynı metni not şeridi için üretir: şerit bir `<div>` olduğu
    için Streamlit markdown'ı orada ÇÖZMEZ — `**kalın**` olduğu gibi görünür.
    """
    baslik = getattr(uyari, "baslik", None)
    detay = getattr(uyari, "detay", None)
    if baslik and detay:
        return f"<b>{baslik}</b><br>{detay}" if html else f"**{baslik}**  \n{detay}"
    return str(uyari)


def gelistirici_anahtari() -> None:
    """Ekranın sağ üstündeki tek anahtar: geliştirici modu.

    ESKİDEN KENAR ÇUBUĞUNUN TEPESİNDEYDİ ve yanında marka bloğu («Katılım
    Lens»), ekip adı ve demo sırası yazıyordu. Üçü de kullanıcının kararını
    değiştirmeyen SABİT metindi; altı sayfanın altısında, her çizimde tekrar
    ediyordu. Tekrar eden metin okunmaz, yalnız yer kaplar — kenar çubuğu
    artık sayfaya ait olana kalıyor (Chatbot'ta sohbet geçmişi,
    Karşılaştırma'da ağırlıklar).

    Anahtar SAĞ ÜSTTE, Streamlit'in kendi üst çubuğunda — «Deploy»un solunda.
    Sayfanın içeriğine ait değil, uygulamanın KİPİNE ait: içerikle birlikte
    kaydırılmaz ve başlıkla ekranın tepesi arasında yer açmaz.

    NASIL: Streamlit'in üst çubuğuna widget konamaz, o yüzden anahtar normal
    akışta çiziliyor ve CSS ile oraya SABİTLENİYOR. Bağ `.kl-dev-isaret`
    işaretçisi: `:has()` ile onu içeren yatay blok `position: fixed` oluyor.
    İşaretçi olmadan seçici sayfadaki ilk `st.columns`'a çarpardı.

    `dev_mode` anahtarı TEK KEZ tanımlanır — aynı `key` ile ikinci bir
    `st.toggle` Streamlit'te `DuplicateWidgetID` fırlatır.
    """
    _, sag = st.columns([6, 1])
    with sag:
        st.markdown('<span class="kl-dev-isaret"></span>', unsafe_allow_html=True)
        st.toggle(
            "Geliştirici",
            key="dev_mode",
            help="JSON ve cURL çıktılarını açar. Uçlar: GET /compare, "
            "POST /ask, POST /extract (localhost:8000).",
        )


# ---------------------------------------------------------------------------
# Mimari şeridi — «bu ekran zincirin neresi?»
# ---------------------------------------------------------------------------
#
# NEDEN VAR: sistem beş katmandan geçiyor ve her ekran bunlardan yalnız
# birini gösteriyor. Ekranlar arasında gezen biri (özellikle jüri) hangi
# parçaya baktığını bilmiyordu; Chatbot'ta bir ASCII kutu vardı, o da yalnız
# orada ve yalnız chatbot'u anlatıyordu.
#
# Diyagram HER SAYFADA AYNI, değişen tek şey vurgulu satır. Aynı şekli
# tekrar görmek zincirin kendisini öğretir; sayfaya özel beş ayrı çizim
# beş ayrı şey öğretirdi.
#
# Metinler KISA tutulur: kenar çubuğu bir doküman değil, bir konum
# göstergesi. Ayrıntı `docs/MIMARI.md`'de.
_ASAMALAR = (
    ("Toplama", "9 bankanın kampanya sayfaları"),
    ("Çıkarım", "kural + dil modeli + uzlaştırıcı"),
    ("Depolama", "şema sözleşmesi · her değer kaynaklı"),
    ("Motor", "karşılaştırma ve muhakeme — kod"),
    ("Arayüz", "cevap + sayısal doğrulama kalkanı"),
)


def _csv_bayt(cerceve) -> bytes:
    """Excel'in Türkçe yerelinde doğru açtığı CSV.

    Ayraç NOKTALI VİRGÜL, kodlama BOM'lu UTF-8: Türkçe Windows'ta Excel
    virgülü ondalık ayracı sayıyor ve virgülle ayrılmış dosyayı tek sütuna
    yığıyor; BOM olmadan da «Ş» ve «ğ» bozuluyor. İkisi de ölçülmüş değil,
    bilinen Excel davranışı — ama bedeli sıfır.
    """
    return cerceve.to_csv(index=False, sep=";").encode("utf-8-sig")


def _word_bayt(cerceve, baslik: str) -> bytes:
    """Word'ün açtığı HTML tablo — `.doc` uzantısıyla.

    `python-docx` EKLENMEDİ. Yeni bağımlılık `make lisanslar` gerektirir ve
    hava boşluklu kurulumda bir paket daha taşımak demektir; Word, HTML'i
    `.doc` uzantısıyla sorunsuz açıyor. Aynı hile Excel çıktısında 27
    Ağustos'tan beri kullanılıyor (`_excel_html`), yani ikinci bir yol
    açmıyoruz.
    """
    return (
        "<html><head><meta charset='utf-8'>"
        "<style>body{font-family:Calibri,sans-serif;font-size:11pt;}"
        "table{border-collapse:collapse;}"
        "th,td{border:1px solid #999;padding:5px 8px;text-align:left;}"
        "th{background:#EFEFEF;}</style></head><body>"
        f"<h2>{baslik}</h2>"
        + cerceve.to_html(index=False)
        + "</body></html>"
    ).encode("utf-8")


_KALIN_DESENI = re.compile(r"\*\*(.+?)\*\*")
_BASLIK_DESENI = re.compile(r"^\s*#{1,6}\s*(.+)$")
_MADDE_DESENI = re.compile(r"^\s*[-*\u2022]\s+(.+)$")
_NUMARALI_DESENI = re.compile(r"^\s*\d+[.)]\s+(.{1,90})$")


def _satir_ici(ham: str) -> str:
    """Satır içi biçim — ÖNCE kaçır, SONRA kalınlaştır.

    Ters sıra bir enjeksiyon yolu açardı: `<b>` etiketini biz koyup sonra
    kaçırsaydık kendi etiketimizi de kaçırırdık; kullanıcı metnindeki `<`
    ise kaçırılmadan geçerdi.
    """
    return _KALIN_DESENI.sub(r"<b>\1</b>", html.escape(ham))


def _serbest_metin_html(metin: str) -> str:
    """Dil modelinin markdown'ımsı çıktısını okunur HTML'e çevirir.

    NEDEN GEREKLİ: satış notu bir TABLO DEĞİL, bir metindir. Tek hücreye
    sıkıştırılınca başlıklar, maddeler ve paragraf araları kayboluyor;
    Word'de tek satırlık dev bir hücre açılıyordu.

    Numaralı satır İKİ ANLAMA gelebiliyor — «1. Avantajlar» bir başlık,
    «1. Vade 120 aya çıkarılabilir.» bir madde. Ayrım uzunluk ve noktalama:
    kısa ve noktasız olan başlıktır. İstemde markdown başlığı isteniyor,
    bu yalnız yedek yol.
    """
    parcalar: list[str] = []
    liste_acik = False

    def _listeyi_kapat() -> None:
        nonlocal liste_acik
        if liste_acik:
            parcalar.append("</ul>")
            liste_acik = False

    for ham in metin.splitlines():
        satir = ham.strip()
        if not satir:
            _listeyi_kapat()
            continue

        if baslik := _BASLIK_DESENI.match(satir):
            _listeyi_kapat()
            parcalar.append(f"<h3>{_satir_ici(baslik.group(1))}</h3>")
        elif madde := _MADDE_DESENI.match(satir):
            if not liste_acik:
                parcalar.append("<ul>")
                liste_acik = True
            parcalar.append(f"<li>{_satir_ici(madde.group(1))}</li>")
        elif (
            (numarali := _NUMARALI_DESENI.match(satir))
            and not numarali.group(1).rstrip().endswith((".", ",", ";", ":"))
        ):
            _listeyi_kapat()
            parcalar.append(f"<h3>{_satir_ici(numarali.group(1))}</h3>")
        else:
            _listeyi_kapat()
            parcalar.append(f"<p>{_satir_ici(satir)}</p>")

    _listeyi_kapat()
    return "".join(parcalar)


_BELGE_BICIMI = """
@page { margin: 2.2cm 2cm; }
body { font-family: Calibri, Segoe UI, sans-serif; font-size: 11pt;
       color: #1a1a1a; line-height: 1.55; }
h1 { font-size: 18pt; margin: 0 0 2pt 0; }
h3 { font-size: 12.5pt; margin: 16pt 0 4pt 0; color: #0B6B4A;
     border-bottom: 1px solid #D8D8D8; padding-bottom: 3pt; }
p  { margin: 0 0 8pt 0; }
ul { margin: 0 0 10pt 0; padding-left: 18pt; }
li { margin-bottom: 4pt; }
.ust { border-bottom: 2px solid #0B6B4A; padding-bottom: 8pt; margin-bottom: 14pt; }
.alt-bilgi { color: #666666; font-size: 9pt; margin-top: 2pt; }
.dipnot { margin-top: 22pt; padding-top: 8pt; border-top: 1px solid #D8D8D8;
          color: #666666; font-size: 9pt; }
"""


def metin_word_indir(
    metin: str,
    *,
    dosya_adi: str,
    anahtar: str,
    baslik: str,
    alt_bilgi: str = "",
    dipnot: str = "",
    etiket: str = "Word olarak indir",
) -> None:
    """Serbest metni biçimlendirilmiş bir Word belgesi olarak indirtir.

    `disa_aktar`dan AYRI: o tablo indirir (CSV + Word), bu metin indirir.
    İkisini tek fonksiyona zorlamak, çağıranın elindeki şeyin tablo mu metin
    mi olduğunu belirsizleştirirdi — nitekim satış notu bir süre tek hücreli
    bir CSV olarak iniyordu ve o dosyanın kimseye faydası yoktu.
    """
    belge = (
        "<html><head><meta charset='utf-8'>"
        f"<style>{_BELGE_BICIMI}</style></head><body>"
        f"<div class='ust'><h1>{html.escape(baslik)}</h1>"
        + (f"<div class='alt-bilgi'>{html.escape(alt_bilgi)}</div>" if alt_bilgi else "")
        + "</div>"
        + _serbest_metin_html(metin)
        + (f"<div class='dipnot'>{html.escape(dipnot)}</div>" if dipnot else "")
        + "</body></html>"
    )
    st.download_button(
        etiket,
        data=belge.encode("utf-8"),
        file_name=f"{dosya_adi}.doc",
        mime="application/msword",
        use_container_width=True,
        key=anahtar,
    )


def disa_aktar(cerceve, *, dosya_adi: str, anahtar: str, baslik: str = "") -> None:
    """CSV ve Word indirme düğmelerini yan yana çizer.

    NEDEN ORTAK: Karşılaştırma ekranı kendi CSV/Excel üreticisini yazmıştı,
    Müşteri Profili elle kurduğu bir TXT veriyordu, kalan üç ekranda hiç
    çıktı yoktu. Üç ayrı biçim, üç ayrı ayraç kararı, üç ayrı kodlama.
    Tek yardımcı — hangi ekrandan indirilirse indirilsin dosya aynı.
    """
    ad = baslik or dosya_adi
    s1, s2 = st.columns(2)
    s1.download_button(
        "CSV indir",
        data=_csv_bayt(cerceve),
        file_name=f"{dosya_adi}.csv",
        mime="text/csv",
        use_container_width=True,
        key=f"{anahtar}_csv",
    )
    s2.download_button(
        "Word indir",
        data=_word_bayt(cerceve, ad),
        file_name=f"{dosya_adi}.doc",
        mime="application/msword",
        use_container_width=True,
        key=f"{anahtar}_doc",
    )


def ipucu_simgesi(metin: str) -> str:
    """Etiket yanına konan «?» simgesinin HTML'i — üzerine gelince açılır.

    `st.markdown(..., unsafe_allow_html=True)` ile basılır. Metindeki tırnak
    işareti `data-ipucu` özniteliğini kapatıp balonu kırardı; kaçırılıyor.
    """
    guvenli = metin.replace('"', "&quot;")
    return f'<div class="kl-ipucu-kutu"><span class="kl-ipucu" data-ipucu="{guvenli}">?</span></div>'


def mimari_kenari(aktif: str | None = None) -> None:
    """Kenar çubuğuna beş aşamalı zinciri çizer, `aktif` olanı vurgular.

    `aktif` aşama adıdır («Çıkarım»); tanınmayan ad verilirse hiçbiri
    vurgulanmaz — sayfa KIRILMAZ. Yazım hatası bir istisna değil, sönük bir
    şerit üretir.
    """
    satirlar = []
    for sira, (ad, alt) in enumerate(_ASAMALAR, 1):
        sinif = "kl-adim aktif" if ad == aktif else "kl-adim"
        satirlar.append(
            f'<div class="{sinif}"><div class="kl-adim-no">{sira}</div>'
            f'<div><div class="kl-adim-ad">{ad}</div>'
            f'<div class="kl-adim-alt">{alt}</div></div></div>'
        )
    # Kenar çubuğunun EN ALTINDA çağrılır (sayfalar `sayfa_sonu()`dan hemen
    # önce çağırıyor): şerit bir konum göstergesi, sayfanın ana aracı değil.
    # Ayıraç onu sayfanın kendi kenar içeriğinden ayırır.
    with st.sidebar:
        st.divider()
        st.caption("Sistem akışı")
        st.markdown(
            f'<div class="kl-mimari">{"".join(satirlar)}</div>',
            unsafe_allow_html=True,
        )


def en_alta_kaydir(imza) -> None:
    """Sayfayı en alta kaydırır — yeni mesaj ekranın dışında kalmasın.

    NEDEN JAVASCRIPT: Streamlit'in kaydırma API'si yok ve `st.markdown` script
    etiketlerini temizler (`sayfa_gezinme` de bu yüzden saf HTML çapası
    kullanıyor). `components.html` gerçek bir iframe açar; aynı kökten
    sunulduğu için `window.parent` erişimi çalışır.

    `imza` yalnız İÇERİĞİ DEĞİŞTİRMEK için var: Streamlit aynı içerikli
    bileşeni yeniden çizmez, imzasız script ikinci mesajda hiç koşmazdı.

    Seçici listesi bilerek uzun: kaydırılan öge Streamlit sürümüyle değişiyor
    (`section.main` → `[data-testid="stMain"]`). Hiçbiri tutmazsa sayfa
    BOZULMAZ, yalnız kaydırma olmaz.

    ÖNCE ÇAPA, SONRA `scrollTop` (28 Ağustos). `scrollTop = scrollHeight` tek
    başına yetmiyordu: kullanıcı YUKARI KAYDIRMIŞKEN soru sorduğunda cevap
    aşağıda kalıyordu. Sebep sırada — cevabın altındaki ajan izleri tablosu ve
    açılır paneller yerleştikçe sayfa uzuyor, 600 ms'de alınan `scrollHeight`
    nihai yükseklik değil. Çapa (`#kl-sohbet-sonu`) sayfanın sonunda duran
    GERÇEK bir öge; `scrollIntoView` onu her seferinde bulur. Israr 1,4
    saniyeye çıktı, aralıklar sıklaştı.
    """
    st.markdown('<div id="kl-sohbet-sonu"></div>', unsafe_allow_html=True)
    components.html(
        f"""
        <script>
          // imza: {imza}
          (function () {{
            const belge = window.parent && window.parent.document;
            if (!belge) return;
            const kaydir = function () {{
              const capa = belge.querySelector('#kl-sohbet-sonu');
              if (capa && capa.scrollIntoView) {{
                capa.scrollIntoView({{block: "end", inline: "nearest"}});
              }}
              const adaylar = [
                belge.querySelector('section.main'),
                belge.querySelector('[data-testid="stMain"]'),
                belge.querySelector('[data-testid="stAppViewContainer"] section'),
                belge.scrollingElement,
                belge.documentElement,
              ];
              adaylar.forEach(function (oge) {{
                if (oge) oge.scrollTop = oge.scrollHeight;
              }});
            }};
            kaydir();
            [40, 120, 260, 500, 900, 1400].forEach(function (ms) {{
              setTimeout(kaydir, ms);
            }});
          }})();
        </script>
        """,
        height=0,
    )


def inject_custom_css():
    """On-prem koyu tema — dış font CDN'si yok (hava boşluğu)."""
    st.markdown(
        """
        <style>
        html, body, [class*="css"] {
            font-family: "Segoe UI", system-ui, sans-serif !important;
        }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        /* ÜST BOŞLUK — Streamlit ana bloğa ~6rem üst dolgu veriyor. Geniş
           düzende bu, dizüstü ekranında başlığın altındaki ilk içeriği
           katlamanın altına itiyordu: sayfanın tepesinde bir avuç boşluk,
           altında sıkışmış içerik. Dolgu okunurluğu bozmayacak kadar
           kısaldı; sayfa adı hâlâ nefes alıyor. */
        [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewBlockContainer"],
        .block-container {
            padding-top: 2.1rem !important;
        }
        [data-testid="stSidebarUserContent"] { padding-top: 1.4rem; }
        h1 { padding-top: 0 !important; margin-top: 0 !important; }

        /* GELİŞTİRİCİ ANAHTARI ÜST ÇUBUKTA — «Deploy»un solunda.
           Streamlit'in üst çubuğuna widget konamıyor; anahtar normal akışta
           çiziliyor ve buradan oraya SABİTLENİYOR. Böylece hem başlıkla
           ekranın tepesi arasında yer kaplamıyor hem de kaydırınca kaybolmuyor.
           Bağ `.kl-dev-isaret`: onu içeren yatay bloğu seçiyoruz, sayfadaki
           ilk `st.columns`'ı değil. */
        div[data-testid="stHorizontalBlock"]:has(.kl-dev-isaret) {
            position: fixed;
            top: 0.45rem;
            right: 7.4rem;
            width: auto;
            min-width: 0;
            z-index: 1000;
            gap: 0;
        }
        div[data-testid="stHorizontalBlock"]:has(.kl-dev-isaret)
            > div[data-testid="stColumn"]:first-child { display: none; }
        div[data-testid="stHorizontalBlock"]:has(.kl-dev-isaret)
            > div[data-testid="stColumn"] { width: auto !important; flex: 0 0 auto; }
        .kl-dev-isaret { display: none; }
        div[data-testid="stHorizontalBlock"]:has(.kl-dev-isaret) label p {
            font-size: 0.78rem !important;
            color: #9A9AA5 !important;
        }

        /* STREAMLIT İPUCU BALONU — genişlik sınırı.
           Kenar çubuğunun dar sütununda açılan balon ekranın dışına taşıyor
           ve metnin bir kısmı okunmuyordu. Balon açıldığı ögeye göre
           konumlanıyor; sınır olmadan uzun bir `help=` metni sağa doğru
           büyümeye devam ediyor. */
        [data-testid="stTooltipContent"] {
            max-width: 300px;
            white-space: normal;
            overflow-wrap: break-word;
            font-size: 0.8rem;
            line-height: 1.5;
        }
        [data-testid="stSidebar"] [data-testid="stTooltipContent"] {
            max-width: 230px;
        }

        /* SAYI/METİN KUTUSU İPUCU — Streamlit bu satırı İngilizce basıyor
           ve dilini yapılandırmanın yolu yok: «Press Enter to apply».
           Türkçe arayüzün ortasında tek İngilizce cümleydi. Metin CSS ile
           değiştiriliyor; gizlemek yerine ÇEVİRİYORUZ, çünkü ipucunun
           kendisi doğru — değer Enter'a basılmadan uygulanmıyor. */
        [data-testid="InputInstructions"] {
            visibility: hidden;
            position: relative;
        }
        [data-testid="InputInstructions"]::after {
            content: "Uygulamak için Enter'a basın";
            visibility: visible;
            position: absolute;
            left: 0; top: 0;
            white-space: nowrap;
        }
        /* Çok satırlı kutuda Streamlit Ctrl+Enter istiyor; tek çeviri
           ikisine birden yanlış olurdu. */
        [data-testid="stTextArea"] [data-testid="InputInstructions"]::after {
            content: "Uygulamak için Ctrl+Enter'a basın";
        }

        /* İPUCU SİMGESİ — `st.metric`in etiket yanındaki «?» simgesinin
           karşılığı. Streamlit o simgeyi yalnız ETİKETLİ widget'larda
           çiziyor; `st.button`da `help=` verilince ayrı bir simge çıkmıyor,
           tooltip düğmenin kendisine bağlanıyor. Aynı görüntüyü elde etmenin
           yolu simgeyi kendimiz çizmek.
           `title` KULLANILMADI: yerleşik ipucu ~1 sn gecikmeyle açılıyor ve
           açık temada beyaz bir kutu veriyor — sayfanın geri kalanıyla
           uyumsuz. Balon anında açılır ve paletin rengini taşır. */
        .kl-ipucu-kutu {
            display: flex; align-items: center; justify-content: flex-start;
            height: 2.4rem;
        }
        .kl-ipucu {
            display: inline-flex; align-items: center; justify-content: center;
            width: 15px; height: 15px; border-radius: 50%;
            border: 1px solid rgba(255,255,255,0.28);
            color: #9A9AA5; font-size: 0.62rem; font-weight: 700;
            cursor: help; position: relative;
        }
        .kl-ipucu:hover { color: #FFFFFF; border-color: rgba(0,168,107,0.65); }
        .kl-ipucu::after {
            content: attr(data-ipucu);
            position: absolute; top: calc(100% + 8px); right: -6px;
            width: 258px; padding: 9px 12px; border-radius: 8px;
            background: #0E0E12; color: #D8D8E0;
            border: 1px solid rgba(255,255,255,0.14);
            font-size: 0.76rem; font-weight: 400; line-height: 1.5;
            text-align: left; white-space: normal;
            opacity: 0; visibility: hidden; transition: opacity 0.14s ease;
            box-shadow: 0 6px 18px rgba(0,0,0,0.55);
            z-index: 1001;
        }
        .kl-ipucu:hover::after { opacity: 1; visibility: visible; }
        /* Balon sütun sınırında kırpılmasın. */
        div[data-testid="stHorizontalBlock"]:has(.kl-ipucu),
        div[data-testid="stColumn"]:has(.kl-ipucu) { overflow: visible; }

        /* MİMARİ ŞERİDİ — kenar çubuğunda, sayfanın hangi aşamayı gösterdiği
           vurgulu. Beş satır, sabit sıra: aynı diyagram her ekranda. */
        .kl-mimari { margin: 2px 0 6px 0; }
        .kl-adim {
            display: flex; gap: 9px; align-items: flex-start;
            padding: 6px 9px; border-radius: 8px; margin-bottom: 3px;
            border: 1px solid transparent;
        }
        .kl-adim-no {
            flex: 0 0 18px; height: 18px; border-radius: 50%;
            background: rgba(255,255,255,0.07); color: #9A9AA5;
            font-size: 0.68rem; font-weight: 700;
            display: flex; align-items: center; justify-content: center;
            margin-top: 1px;
        }
        .kl-adim-ad { font-size: 0.82rem; font-weight: 600; color: #C4C4CE; line-height: 1.3; }
        .kl-adim-alt { font-size: 0.72rem; color: #8E8E99; line-height: 1.4; margin-top: 1px; }
        .kl-adim.aktif {
            background: rgba(0,168,107,0.10);
            border-color: rgba(0,168,107,0.32);
        }
        .kl-adim.aktif .kl-adim-no { background: #00A86B; color: #10231B; }
        .kl-adim.aktif .kl-adim-ad { color: #FFFFFF; }
        .kl-adim.aktif .kl-adim-alt { color: #A8C9BB; }
        /* Üst çubuğu gizleme: projeksiyonda sayfa adı ve menü okunur kalsın. */

        /* SAYFA ALT BASLIGI — eskiden yesil gradyanli bir SERITTI.
           Banka arayuzunde uyari renkleri (yesil/sari) DURUM bildirir: islem
           basarili, dikkat gerekiyor. Sayfanin ne ise yaradigini anlatan sabit
           bir metni yesile boyamak, o rengin durum anlamini tuketir ve gercek
           bir uyari geldiginde kullanici artik fark etmez. Alt baslik alt
           basliktir: sakin renk, okunur punto. */
        .kl-serit {
            border-left: 3px solid rgba(0, 168, 107, 0.55);
            padding: 2px 0 2px 14px;
            margin: -4px 0 18px 0;
            color: #C4C4CE;
            font-size: 0.95rem;
            line-height: 1.55;
            letter-spacing: 0.1px;
        }
        .kl-serit b { color: #D8D8E0; font-weight: 600; }

        /* BANKA URUN KARTI — bankalarin kendi kampanya listeleriyle ayni
           duzen: solda kurum ve aciklama, ortada rakamlar, sagda eylem. */
        .kl-kart {
            background: #1E1E24;
            border: 1px solid rgba(255,255,255,0.09);
            border-radius: 12px;
            padding: 16px 18px;
            margin-bottom: 10px;
            transition: border-color 0.18s ease, box-shadow 0.18s ease;
        }
        .kl-kart:hover {
            border-color: rgba(0,168,107,0.45);
            box-shadow: 0 4px 14px rgba(0,0,0,0.35);
        }
        .kl-kart-ad { font-size: 1.02rem; font-weight: 600; color: #F0F0F4; }
        .kl-kart-alt { font-size: 0.86rem; color: #B4B4BE; margin-top: 3px; line-height: 1.5; }
        .kl-kart-etiket {
            font-size: 0.74rem; color: #AFAFB8; text-transform: uppercase;
            letter-spacing: 0.6px; margin-bottom: 2px;
        }
        .kl-kart-deger { font-size: 1.16rem; font-weight: 650; color: #FFFFFF; }
        .kl-kart-deger.yok { font-size: 0.92rem; font-weight: 500; color: #AFAFB8; }

        /* KONTRAST — projeksiyonda okunurluk (27 Agu incelemesi, madde 8).
           Streamlit'in kendi `st.caption` grisi #808495 civari: koyu zeminde
           ~3.4:1 kontrast veriyor, WCAG AA kucuk metin icin 4.5:1 istiyor.
           Salonda isik varken «Son veri cekimi» satiri okunmuyordu. */
        [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
            color: #ADADB8 !important;
        }
        /* NOT ŞERİDİ — `st.warning`ın sakin karşılığı. Tam genişlikte sarı
           kutu «bir şey bozuldu» der; buradaki notların hiçbiri arıza değil,
           ölçümün sınırının beyanı. */
        .kl-not {
            border-left: 3px solid rgba(217,164,65,0.55);
            background: rgba(217,164,65,0.06);
            padding: 9px 14px; border-radius: 0 8px 8px 0;
            margin: 0 0 10px 0; color: #C4C4CE;
            font-size: 0.88rem; line-height: 1.55;
        }
        .kl-not b { color: #E0D3B0; font-weight: 600; }
        .kl-not-soluk {
            border-left-color: rgba(255,255,255,0.18);
            background: rgba(255,255,255,0.03);
        }
        .kl-not-soluk b { color: #D8D8E0; }

        /* CEVAP ÜSTBİLGİSİ — niyet ve doğrulama tek satırda, küçük çip.
           Eskiden ikisi de ayrı kutuydu: yeşil `st.success` kutusu üç satır
           kaplayıp «doğrulama geçti» diye HER cevapta çıkıyordu. Her koşuda
           çıkan bir başarı kutusu bilgi taşımaz, yalnız cevabı aşağı iter —
           bilgi kayboldu sayılmaz, çipin `title`'ında duruyor. BAŞARISIZLIK
           hâlâ tam boy kırmızı kutudur: o gerçekten seyrek ve kritik. */
        .kl-meta { margin: 2px 0 12px 0; }
        .kl-cip {
            display: inline-block; font-size: 0.74rem; font-weight: 600;
            padding: 2px 10px; border-radius: 20px; margin-right: 6px;
            background: rgba(255,255,255,0.05); color: #B4B4BE;
            border: 1px solid rgba(255,255,255,0.10);
            cursor: help;
        }
        .kl-cip-uyari {
            background: rgba(217,164,65,0.16); color: #E0B85E;
            border-color: rgba(217,164,65,0.38);
        }
        .kl-cip-onay {
            background: rgba(0,168,107,0.14); color: #4FD1A0;
            border-color: rgba(0,168,107,0.30);
        }

        .kl-rozet {
            display: inline-block; font-size: 0.72rem; font-weight: 600;
            padding: 2px 9px; border-radius: 20px; margin-left: 8px;
            background: rgba(0,168,107,0.16); color: #4FD1A0;
            border: 1px solid rgba(0,168,107,0.3);
        }

        /* HIZLI MENU — kucuk, tek kenarda. Tam genislikte dev dugmeler
           sayfanin en onemli seyinin gezinme oldugunu soyluyordu; degil. */
        .kl-menu .stButton > button {
            padding: 3px 10px !important;
            font-size: 0.82rem !important;
            font-weight: 500 !important;
            min-height: 0 !important;
            height: 30px !important;
            background: #22222A !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
            color: #C8C8D2 !important;
        }
        .kl-menu .stButton > button:hover {
            border-color: rgba(0,168,107,0.5) !important;
            color: #FFFFFF !important;
        }

        /* SAYFA GEZINME — sag altta sabit yukari/asagi. */
        .kl-gezinme {
            position: fixed; right: 22px; bottom: 26px; z-index: 999;
            display: flex; flex-direction: column; gap: 6px;
        }
        .kl-gezinme a {
            width: 34px; height: 34px; border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            background: rgba(34,34,42,0.94);
            border: 1px solid rgba(255,255,255,0.14);
            color: #C8C8D2; text-decoration: none;
            font-size: 0.95rem; line-height: 1;
        }
        .kl-gezinme a:hover {
            background: rgba(0,168,107,0.22);
            border-color: rgba(0,168,107,0.5);
            color: #FFFFFF;
        }
        
        /* Metric Cards Styling (Glassmorphism & Elevation) */
        [data-testid="stMetric"] {
            background: rgba(37, 37, 45, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            padding: 15px 20px;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
            transition: all 0.3s ease;
        }
        
        [data-testid="stMetric"]:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 24px rgba(0, 168, 107, 0.3);
            border-color: rgba(0, 168, 107, 0.5);
        }
        
        /* Metric Caption / Delta Visibility */
        [data-testid="stMetricDelta"] > div {
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            opacity: 0.95 !important;
        }

        /* Alerts Semantic Coloring (Info, Warning, Error) */
        div.stAlert > div {
            backdrop-filter: blur(8px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            border-radius: 8px;
        }
        div[data-baseweb="notification"] {
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        /* DataFrame Styling */
        .dataframe {
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            overflow: hidden !important;
        }
        
        th {
            background-color: #1A1A1F !important;
            color: #E0E0E0 !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
        }
        
        td {
            font-size: 0.95rem;
            color: #D3D3D3 !important;
        }
        
        tr:hover td {
            background-color: rgba(0, 168, 107, 0.1) !important;
        }
        
        /* Buttons */
        .stButton > button {
            border-radius: 8px !important;
            font-weight: 500 !important;
            transition: all 0.2s ease;
        }
        
        /* Expanders */
        [data-testid="stExpander"] {
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            background-color: #25252D !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }
        
        /* Inputs & Selectboxes */
        .stSelectbox div[data-baseweb="select"] > div, 
        .stTextInput input, 
        .stNumberInput input {
            border-radius: 8px !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            background-color: #25252D !important;
            color: #E0E0E0 !important;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #121212 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def sayfa_gezinme() -> None:
    """Sağ altta sabit «başa dön / sona git» düğmeleri.

    NEDEN ÇAPA, NEDEN JAVASCRIPT DEĞİL:
        `st.markdown` script etiketlerini temizler — Streamlit'in güvenlik
        kısıtı. Kaydırma bu yüzden saf HTML çapasıyla yapılır: burası `#kl-ust`
        çapasını ve düğmeleri basar, sayfanın sonundaki `sayfa_sonu()` de
        `#kl-alt` çapasını. İkisi ayrı çağrı çünkü çapaların ARASINDA sayfanın
        kendi içeriği var.

        Sayfa `sayfa_sonu()` çağırmayı unutursa aşağı oku çalışmaz, sayfa
        bozulmaz — bilinçli olarak bu yönde başarısız oluyor. Nöbetçi:
        `tests/test_arayuz_gezinme.py`.
    """
    st.markdown(
        '<div id="kl-ust"></div>'
        '<div class="kl-gezinme">'
        '<a href="#kl-ust" title="Sayfa başı">&#8593;</a>'
        '<a href="#kl-alt" title="Sayfa sonu">&#8595;</a>'
        "</div>",
        unsafe_allow_html=True,
    )


def sayfa_sonu() -> None:
    """`sayfa_gezinme()` aşağı okunun hedefi. Sayfanın EN SONUNDA çağrılır."""
    st.markdown('<div id="kl-alt"></div>', unsafe_allow_html=True)
