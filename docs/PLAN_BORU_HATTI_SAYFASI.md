# Plan — Arayüze «Canlı Boru Hattı» sayfası

> Durum: **plan**, henüz kod yazılmadı. Hazırlandığı tarih: 26 Ağustos 2026.
>
> **Pano karşılığı: `G-18`** — Görkem, 26 Ağustos gecesi.
>
> **Bu iş mentör geri bildiriminden çıkmadı; takımın kendi isteğidir.** Mentörün
> sekiz başlığı ve karşılıkları ayrı dosyada:
> [`MENTOR_GERI_BILDIRIMI.md`](MENTOR_GERI_BILDIRIMI.md). Sayfanın mentör
> listesine dolaylı katkısı şudur: çıkarım katmanlarını (kural → LLM →
> uzlaştırıcı) ekranda görünür kılarak mimari şemanın canlı karşılığını verir.
>
> ⚠️ **Zaman daralırsa Sekme 2 (Çıkarım) önce bitirilir.** Mevcut `data/raw`
> kayıtları üzerinde koşar, Selenium'a ve Chrome'a hiç dokunmaz — demo sırasında
> kilitlenme riski taşıyan parça Sekme 1'dir.

## Bağlam

Bugün toplama ve çıkarım yalnız terminalden başlatılıyor (`make crawl`, `make extract`).
Jüri arayüzde yalnız **sonucu** görüyor; veriyi üreten iki katman (9 Selenium kazıyıcısı
ve hibrit çıkarım hattı) demonun hiçbir yerinde görünmüyor. Sunumun en güçlü iddiaları —
banka başına kazıyıcı, robots kapısı, kural + LLM + uzlaştırıcı katmanları — bir terminal
penceresinde akıp gidiyor.

Bu plan, arayüze **beşinci bir sayfa** ekler: toplama ve çıkarım oradan başlatılır, koşarken
canlı animasyonla izlenir, bitince ölçülmüş istatistiklerle özetlenir. Amaç hem gösterim
gücü hem de gerçek bir işlev — sayfa uydurma animasyon oynatmaz, **gerçek kazıyıcıyı ve
gerçek çıkarım hattını** sürer, animasyon o koşunun kendi olaylarından beslenir.

### Verilen kararlar

| Karar | Seçim |
|---|---|
| Yazma hedefi | **Ayrı demo alanı** — `data/demo_raw/` + `data/demo/demo.db`. Üretim verisine ve takipli dosyalara dokunulmaz. |
| Koşu kipi | **İki kip:** «Demo» (banka başına ~10 sayfa) ve «Tam koşu» (hepsi). İkisi de gerçek kazıma; kayıttan oynatma yok. |
| Tarayıcı | **Görünmez (headless)** — `topla(gorunmez=True)`. |

> **Açık varsayım (uygulamadan önce bir bakış at):** «Tam koşu» da varsayılan olarak demo
> alanına yazar. Tam koşu ~1.000 sayfa ve 30+ dakikadır; çıktısını atılabilir bir dizine
> yazmak boşa iş olabileceği için sekmeye ayrıca **kapalı gelen** bir onay kutusu koyuyorum:
> «üretim boru hattına yaz (`data/raw` + `data/katilim.db`)». İşaretlenmedikçe hiçbir koşu
> üretim verisine dokunmaz.

---

## Yapılacaklar

### 1. `src/collector/toplayici.py` — `topla()`'ya iki kwarg *(eklemeli, davranış değişmez)*

`topla()` zaten `dizin` ve `ilerleme` alıyor; demo dizini ve animasyon beslemesi bedava.
Eksik olan iki şey:

```python
def topla(
    bankalar=None, *, gorunmez=None, ilerleme=None, dizin=HAM_DIZIN,
    azami_sayfa: int | None = None,           # YENİ — banka başına sayfa tavanı (demo kipi)
    iptal: Callable[[], bool] | None = None,  # YENİ — işbirlikçi durdurma
) -> int:
```

- `azami_sayfa`: `for kayit in kaziyici.tara()` döngüsünde sayaç tavana varınca `break`.
  Üreteci kapatmak güvenli; `topla()`'nın `finally`'si sürücüyü zaten kapatıyor.
- `iptal`: her banka öncesi ve her sayfadan sonra yoklanır, `True` ise döngüden çıkılır.
  İş parçacığı öldürülmez — Selenium temiz kapanır.
- İkisi de `None` olduğunda kod yolu bugünküyle **birebir aynı** kalır; `make crawl`
  etkilenmez.

### 2. `src/boru_hatti.py` — çıkarım çekirdeğini argparse'tan ayır

Bugün çıkarım mantığı `_cikar_ve_kaydet(kayitlar, args)` içinde ve girdi olarak bir
`argparse.Namespace` istiyor; arayüzden çağrılamaz. Ayrıca ilerleme yalnız `log.info`'ya
gidiyor. Üç veri sınıfı + bir işlev eklenir, mevcut gövde oraya taşınır:

```python
@dataclass(frozen=True)
class CikarimAyarlari:      # yalniz_kural, yalniz_llm, elestirmen_yok, yuklem_yok, model

@dataclass(frozen=True)
class CikarimIlerlemesi:    # collector'daki `Ilerleme` ile aynı desen
    asama: Literal["basladi", "kayit", "ara_kayit", "bitti"]
    sira: int; toplam: int; banka_adi: str; url: str
    doluluk: float; guven: float; sure: float; mesaj: str

@dataclass
class CikarimOzeti:         # kayit_sayisi, kural/llm/hibrit alan sayıları, yüklem sayaçları,
                            # celiskiler, kanit_denetimi_hatasi, sure, saniye_basina_kayit,
                            # yapilandirma, veritabani_url, banka_dagilimi

def cikarim_kos(kayitlar, ayarlar, *, url=None, ilerleme=None, iptal=None) -> CikarimOzeti:
```

- Mevcut `ThreadPoolExecutor` + öbekli paralellik + ara kayıt + `cikarim_kosusu_yaz`
  mantığı **aynen** taşınır. `log.info` satırları kalır; yanlarına geri çağrı eklenir.
- Kayıt başına süre `kampanya_cikar`'ın döndürdüğü `rapor.trace_log` içinde zaten var
  (`toplam_sure`, `llm_toplam_suresi`) — yeni ölçüm yazılmaz, oradan okunur.
- `_cikar_ve_kaydet` ince bir CLI sarmalayıcısına iner: `args` → `CikarimAyarlari`,
  `cikarim_kos(...)` çağrısı, sonra bugünkü 64 karakterlik özet bloğunu `CikarimOzeti`'nden
  basar. **Terminal çıktısı ve dönüş kodu değişmemeli.**
- `eval/ablasyon.py` `kampanya_cikar`'ı doğrudan çağırıyor, `_cikar_ve_kaydet`'i değil —
  ablasyon bu refactor'dan etkilenmez. Yine de `tests/test_ablasyon_butunlugu.py` ve
  `tests/test_determinizm.py` koşulmadan bu adım kapanmaz.

### 3. `app/is_yurutucu.py` *(yeni)* — arka plan işi + olay kuyruğu

```python
class ArkaPlanIsi:   # kuyruk: queue.Queue · thread · iptal: threading.Event
                     # sonuc · hata · baslangic · bitis
def baslat(hedef) -> ArkaPlanIsi
def olaylari_cek(is_) -> list        # kuyruğu bloklamadan boşaltır
```

Tek katı kural: **işçi iş parçacığı hiçbir `st.*` çağırmaz.** Olayları kuyruğa koyar, çizimi
betik iş parçacığı yapar. Bu, `temel_kaziyici.py`'deki «kazıyıcı ekrana hiçbir şey yazmaz»
tasarımının aynısı — geri çağrı arayüzü zaten bunun için var.

İkinci kural: **sessiz yutma yok.** İş parçacığındaki istisna `is.hata`'ya alınır ve arayüzde
kırmızı kutuyla gösterilir (`dev_mode` açıksa tam iz). Yakalanıp yok sayılmaz.

### 4. `app/akis.py` *(yeni)* — animasyon bileşenleri, hepsi saf işlev

CSS yalnız `@keyframes` — **dış CDN, dış font, dış JS yok** (hava boşluğu kısıtı,
`inject_custom_css`'in yaptığının aynısı).

| İşlev | Ne çizer |
|---|---|
| `akis_css()` | Keyframe'ler: nabız (aktif kart), kayan şerit (ilerleme çubuğu), belirme (günlük satırı), tarama süpürmesi |
| `banka_izgarasi(durumlar)` | 9 banka kartı: `bekliyor` gri · `taraniyor` yeşil nabız · `bitti` ✓ · `atlandi` · `hata` |
| `olay_gunlugu(olaylar)` | Son ~12 olay, yenisi üstte, belirerek girer |
| `katman_hatti(sayaclar)` | Çıkarım için üç şerit: KURAL → LLM → UZLAŞTIRICI, akan noktalar |
| `kayit_seridi(kayitlar)` | Son işlenen kayıtlar: banka · doluluk çubuğu · güven çubuğu · süre |

**Kaçırılmaması gereken:** bu işlevler `unsafe_allow_html=True` ile basılıyor ve içine
banka sayfa başlığı, URL, hata mesajı gibi **dış kaynaklı metin** giriyor. Her dış dize
`html.escape()`'ten geçmeli. Saf işlev oldukları için testte doğrulanabilir.

Renkler mevcut paletten: `#00A86B` (yeşil), kart zemini `rgba(37,37,45,.7)` —
`ui_utils.inject_custom_css` ile aynı dil.

### 5. `app/pages/4_Boru_Hattı.py` *(yeni sayfa)*

Sayfa başlığı: **Canlı Boru Hattı**. Üstte `kl-serit` şeridi + hedef rozeti:
«Bu sayfa `data/demo_raw/` ve `data/demo/demo.db` içine yazar — üretim verisine dokunmaz.»

```
st.tabs(["1 · Veri Toplama", "2 · Çıkarım"])
```

**Sekme 1 — Veri Toplama**
- Kip: `st.radio` → «Demo (banka başına 10 sayfa)» · «Tam koşu (tüm sayfalar)»
- Banka çoklu seçimi (varsayılan: `KAZIYICILAR` sözlüğündeki 9 banka)
- `[Toplamayı Başlat]` `[İptal]` — koşarken başlat düğmesi kilitli
- Canlı alan `@st.fragment(run_every=0.4)`: ilerleme çubuğu + geçen süre + banka kartları
  ızgarası + aktif URL + olay günlüğü. Kuyruğu boşaltır, `st.session_state`'teki durumu
  günceller, yeniden çizer. İş bitince `st.rerun(scope="app")`.
- Bitiş paneli: **süre · toplanan sayfa · gezilen URL · banka · atlanan · hata · sn/sayfa**
  + banka×sayfa çubuk grafiği (`px.bar`, `format_bank_name`) + atlama sebepleri tablosu.
  «robots.txt N URL'i reddetti» satırı ayrıca gösterilir — bu bir kusur değil, jüriye
  gösterilecek bir etik kanıtı.

**Sekme 2 — Çıkarım**
- Kaynak: «Bu oturumda toplananlar (N)» · «`data/demo_raw` tamamı» · «üretim `data/raw`
  (1.024)» — üçü de `ham_kayitlari_oku(dizin)` ile okunur, yeni kod gerekmez
- Adet sınırı kaydırağı (demo için 10–50)
- Sağlayıcı rozeti: **EVREN `llm-large`** ya da **Ollama**. Ollama ise uyarı:
  *«Yerelde Streamlit açıkken kayıt başına ~2,5 dk (ölçüm: CLAUDE.md). Demo kipinde adedi düşür.»*
- Canlı alan: katman hattı animasyonu + kayıt sayacı + anlık sn/kayıt + son kayıtlar şeridi
  + canlı artan **kural-tek / LLM-tek / hibrit** alan sayaçları
- Bitiş paneli: **işlenen kayıt · süre · sn/kayıt · ortalama doluluk · ortalama güven ·
  kanıt denetimi** + katman katkısı çubuk grafiği + çelişkiler (expander) + üretilen
  kampanyaların tablosu.
  Son tablo **şart**: demo veritabanı ayrı olduğu için bu kayıtlar Genel Bakış'ta
  görünmez; jürinin «veri gerçekten aktı» görmesi bu tabloyla olur.

**Hata ve kenar durumları** (ES-03 disiplini, sayfa kırılmamalı):
Chrome/chromedriver yok · ağ yok · EVREN 401/timeout · seçili banka yok ·
hiç kayıt toplanmadı · koşu ortasında sayfa değiştirildi (iş `session_state`'te
sürer, dönünce yeniden bağlanır) · aynı anda ikinci iş başlatma (tek iş yuvası, kilit).

### 6. `app/ui_utils.py` — tek satır

`ortak_kenar()` içindeki demo sırası ipucu güncellenir:
`Genel Bakış → **Boru Hattı** → Metin Analizi → Karşılaştırma → Müşteri Profili → Chatbot`

### 7. Testler *(`make test` ve `make lint` yeşil kalmalı; lint `app`'i de tarıyor)*

- `tests/test_akis_bilesenleri.py` — saf HTML üreticileri: durum sınıfları doğru mu,
  `<script>` içeren banka başlığı **kaçırılıyor mu**, boş liste kırılmıyor mu.
- `tests/test_boru_hatti_ilerleme.py` — `cikarim_kos` 2–3 tohum `HamKayit` ile,
  `yalniz_kural=True` (ağ yok), geçici sqlite URL'i: olaylar sırayla geliyor mu, `CikarimOzeti`
  sayaçları rapordaki değerlerle tutuyor mu, `iptal` erken durduruyor mu, tek kaydın hatası
  koşuyu düşürmüyor mu.
- `tests/test_toplayici.py` — genişlet: `azami_sayfa` banka başına tavanı uyguluyor mu,
  `iptal` döngüyü kesiyor mu (dosyadaki mevcut sahte sürücü / monkeypatch desenini kullan).

---

## Dürüstlük sınırı — bu sayfada yapılmayacaklar

Sayfanın işi «jürinin gözünü boyamak» olsa da, **yalan söyleyen tek bir piksel olamaz**;
jüri 30 saniyede çürütebileceği bir şey yakalarsa doğru olan her şeyin güvenilirliği gider
(`docs/ARAYUZ_INCELEME.md` K1–K2'nin dersi).

- Animasyon **gerçek olaylardan** beslenir. Sahte ilerleme, sahte sayaç, uydurma gecikme yok.
- «Toplanan sayfa», «sn/kayıt», «doluluk», «güven» ölçülen değerlerdir; hiçbiri
  yuvarlanıp güzelleştirilmez.
- Nezaket kuralı (istek arası ≥2 sn, alan adı başına tek sıra) demo hızı için
  **gevşetilmez**. Demo kipi sayfa sayısını kısar, temposunu değil.
- `Alan(... yontem="belirtilmemis")` kısıtı, eleştirmen ajanı ve sayısal kalkan
  bu sayfa için devre dışı bırakılmaz.

---

## Doğrulama

Windows'ta `make` yok — hedefleri elle koştur:

```powershell
.venv\Scripts\python -m pytest tests/test_akis_bilesenleri.py tests/test_boru_hatti_ilerleme.py tests/test_toplayici.py -v
.venv\Scripts\python -m pytest tests/ -q                 # 814 test yeşil kalmalı
.venv\Scripts\python -m ruff check src app tests eval tools
```

Regresyon kapıları (refactor bir şeyi kaydırdıysa burada yakalanır):

```powershell
.venv\Scripts\python -m pytest tests/test_ablasyon_butunlugu.py tests/test_determinizm.py -v
.venv\Scripts\python -m src.boru_hatti seed --yalniz-kural   # CLI çıktısı eskisiyle aynı mı
```

Uçtan uca (arayüz):

```powershell
$env:ARROW_DEFAULT_MEMORY_POOL="system"
.venv\Scripts\streamlit run app/Genel_Bakış.py
```

1. **Boru Hattı** sayfası → Demo kipi → tek banka seç → Toplamayı Başlat.
   Kartlar sırayla yanıyor mu, günlük akıyor mu, ~10 sayfada duruyor mu, bitiş
   metrikleri geliyor mu. `data/demo_raw/` doldu, `data/raw/` **dokunulmadı**.
2. Çıkarım sekmesi → «Bu oturumda toplananlar» → Başlat. Katman animasyonu akıyor mu,
   sn/kayıt makul mü, bitiş tablosunda kampanyalar görünüyor mu.
   `data/demo/demo.db` doldu, `data/katilim.db` **dokunulmadı**.
3. Koşu ortasında **İptal** → temiz duruyor mu, Chrome kapanıyor mu.
4. Koşu ortasında başka sayfaya geçip dön → iş sürüyor mu, animasyon yeniden bağlanıyor mu.
5. `git status` — takipli hiçbir dosya değişmemiş olmalı.

> `ARROW_DEFAULT_MEMORY_POOL=system` şart: bu sayfa **hem iş parçacığı hem `st.dataframe`**
> kullanıyor; `Makefile`'daki not tam bu birleşimin macOS'ta çökmesiyle ilgili.

---

## Takım notu

- `app/` **Esra'nın alanı** (`GOREVLER.md`: «Esra — arayüz, dashboard, sunum ve video»);
  `src/collector/` ve veri toplama **Görkem'in**. Bu iş ikisinin kesişimi — başlamadan
  Esra'ya haber ver, sonra `GOREVLER.md`'ye yeni bir madde aç.
- `src/schema.py`'ye dokunulmuyor → ADR gerekmiyor.
- `.gitignore`'a iki satır gerekecek: `data/demo_raw/` ve `data/demo/` — türetilmiş,
  atılabilir veri.
- Bitirince: `git add -A` → commit (yapay zekâ imzası **yok**) → `git push origin main`,
  `GOREVLER.md`'de maddeye `[x]`.
