"""Arayüz yardımcıları — grafik ve tablo etiketleri.

Banka kısa adları `data/banks.yaml`'daki `kisa_ad` alanından okunur. Burada
ikinci bir sözlük TUTULMAZ: elle yazılan kopya 16 Ağustos'ta kayıt defteriyle
yedi bankada ayrışmıştı ("Türkiye Emlak Katılım Bankası A.Ş." kayıt defterinde
"Emlak Katılım", kopyada hiç eşleşmiyordu). Kayıt defteri tek doğruluk kaynağı.
"""

from __future__ import annotations

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

    for uyari in engelleyiciler:
        st.warning(_uyari_metni(uyari))

    if not notlar:
        return

    # Tek not için panel açıp kapamak gereksiz tıklama; doğrudan gösterilir.
    if len(notlar) == 1:
        st.info(_uyari_metni(notlar[0]))
        return

    with st.expander(f"{baslik} ({len(notlar)})", expanded=False):
        for uyari in notlar:
            st.markdown(_uyari_metni(uyari))


def _uyari_metni(uyari) -> str:
    """Başlığı kalın, detayı alt satırda. Markdown'da satır sonu iki boşluktur."""
    baslik = getattr(uyari, "baslik", None)
    detay = getattr(uyari, "detay", None)
    if baslik and detay:
        return f"**{baslik}**  \n{detay}"
    return str(uyari)


def gelistirici_anahtari() -> None:
    """Ekranın sağ üstündeki tek anahtar: geliştirici modu.

    ESKİDEN KENAR ÇUBUĞUNUN TEPESİNDEYDİ ve yanında marka bloğu («Katılım
    Lens»), ekip adı ve demo sırası yazıyordu. Üçü de kullanıcının kararını
    değiştirmeyen SABİT metindi; altı sayfanın altısında, her çizimde tekrar
    ediyordu. Tekrar eden metin okunmaz, yalnız yer kaplar — kenar çubuğu
    artık sayfaya ait olana kalıyor (Chatbot'ta sohbet geçmişi,
    Karşılaştırma'da ağırlıklar).

    Anahtar SAĞ ÜSTTE çünkü sayfanın içeriğine ait değil, uygulamanın kipine
    ait: içerikle birlikte kaydırılmaz, ilk bakışta göze girmez.

    `dev_mode` anahtarı TEK KEZ tanımlanır — aynı `key` ile ikinci bir
    `st.toggle` Streamlit'te `DuplicateWidgetID` fırlatır.
    """
    _, sag = st.columns([6, 1])
    with sag:
        st.toggle(
            "Geliştirici",
            key="dev_mode",
            help="JSON ve cURL çıktılarını açar. Uçlar: GET /compare, "
            "POST /ask, POST /extract (localhost:8000).",
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
    """
    components.html(
        f"""
        <script>
          // imza: {imza}
          (function () {{
            const belge = window.parent && window.parent.document;
            if (!belge) return;
            const kaydir = function () {{
              const adaylar = [
                belge.querySelector('section.main'),
                belge.querySelector('[data-testid="stMain"]'),
                belge.querySelector('[data-testid="stAppViewContainer"] section'),
                belge.scrollingElement,
              ];
              adaylar.forEach(function (oge) {{
                if (oge) oge.scrollTop = oge.scrollHeight;
              }});
            }};
            kaydir();
            [80, 250, 600].forEach(function (ms) {{ setTimeout(kaydir, ms); }});
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
