# Arayüz İncelemesi — ES-05 / ES-06 / ES-07

**Tarih:** 18 Ağustos 2026 · **İnceleyen:** Eren · **Kapsam:** `app/` (4 sayfa, 1073 satır)
**İncelenen commit'ler:** `6923ce6`, `d28f08f`, `720d8fc`, `168a301`, `0eb9f13`

> **Esra — bu dosya sana.** Kodun teknik olarak sağlam; testler ve lint yeşil,
> hiçbir sayfa çökmüyor. Sorun kodda değil, **arayüzün kod hakkında söylediklerinde**:
> üç yerde sistemin yapmadığı bir şeyi yapıyor diye anlatıyor. Jüri sunumunda en
> pahalı hata türü bu, o yüzden ayrı bir dosya açtım.
>
> Aşağıdaki her iddiayı kendin doğrulayabilirsin — her maddenin altında çalıştırılacak
> komut var.
>
> **Pano karşılığı: `ES-19` (📅 19 Ağu, 🔴).** K1–K7 orada işaretlenebilir
> madde olarak duruyor. `ES-12` (demo senaryosu) artık `ES-19`'u bekliyor —
> yanlış iddialar düzeltilmeden demo prova edilmemeli.

---

## Önce: neyin çalıştığı

| Kontrol | Sonuç |
|---|---|
| `make test` | ✅ 449 test geçti |
| `make lint` | ✅ temiz |
| 4 sayfa headless açılış (`AppTest`) | ✅ istisnasız, `dev_mode` açık ve kapalıyken |
| ES-05 doluluk grafiği matematiği | ✅ ORM modeline karşı doğru |
| ES-06 geçmiş refaktörü | ✅ temiz — `cevap_renderla` tek render yolu |

**ES-06 iyi iş.** Tekrar eden render bloğunu tek fonksiyona indirmen, `gecmis`'e
`tam_metin()` yerine `Cevap` nesnesi koyman doğru karar; kaynak kartları ve rozet
artık geçmişte de duruyor. Tip değişimi güvenli, `gecmis` başka hiçbir yerde
kullanılmıyor (kontrol ettim).

---

## 🔴 K1 — Vade iddiası kodun tam tersini söylüyor

**Nerede:** `app/pages/1_Karsilastirma.py:146` ve `:260`

Her iki metin de şunu diyor:

> *"algoritmamız, uzun vadeli kampanyaların skorunu vade farkı riskini gözeterek
> daha düşük hesaplar"*

**Gerçek:** `src/comparison/karsilastirma.py:141`

```python
("vade", "vade_ay_max", "yuksek_iyi", a.vade),
```

`yuksek_iyi` = uzun vade **yüksek** skor alır. Ölçüm:

```
  3 ay → vade katkısı 0.0
120 ay → vade katkısı 0.20   ← tavan değer
```

**Kendin doğrula:**
```bash
.venv/bin/python -c "
from src.depolama import tum_kayitlar
from src.comparison.karsilastirma import avantaj_skorla, Agirliklar
d = {x.kampanya_id: x for x in avantaj_skorla(tum_kayitlar(), Agirliklar())}
v = sorted((k.vade_ay_max, d[k.kampanya_id].bilesenler.get('vade'))
           for k in tum_kayitlar() if k.vade_ay_max is not None)
print('en kisa vade:', v[0], '| en uzun vade:', v[-1])"
```

**Not:** Gerçek vade farkı uyarısı **zaten var ve zaten ekranda** —
`karsilastirma.py::uyarilar()` üretiyor, `1_Karsilastirma.py:166` basıyor:

> *"⚠️ Karşılaştırılan ürünlerin vadeleri farklı (… ay). Farklı vadeli ürünler
> doğrudan karşılaştırılamaz; toplam maliyet üzerinden değerlendirin."*

Yani ES-07'nin "vade farkı uyarısı" kısmı aslında bitmişti. Eklenen metin onun
üstüne yanlış bir açıklama koyuyor.

**Yapılacak:** İki metni de kaldır ya da kodun gerçekten yaptığını yaz —
*"vade ağırlığı kullanıcı tarafından belirlenir; uzun vade tek başına avantaj
sayılır, ama farklı vadeli ürünler için yukarıdaki uyarı çıkar ve karar toplam
maliyete bırakılır."*

---

## 🔴 K2 — Var olmayan bir "Güven Skoru" kuralı anlatılıyor

**Nerede:** `app/pages/1_Karsilastirma.py:276`

> *"Kural 2 (Güven Skoru): Eğer iki bankanın sayısal değeri tamamen aynıysa,
> … Güven Skoru daha yüksek olan üste çıkar."*

**Gerçek:** `karsilastirma.py::sirala()` sıralama anahtarı `(0/1, deger)` —
güven skoru terimi yok. Python sıralaması kararlı olduğu için eşitlikte
**girdi sırası** korunur, güven sırası değil.

**Ölçüm:** dört eşitlik grubu iddiayı çürütüyor, örneğin

```
120 ay grubu güven skorları: [0.805, 0.816, 0.823]   ← artan, iddianın tersi
```

**Kendin doğrula:**
```bash
.venv/bin/python -c "
from itertools import groupby
from src.depolama import tum_kayitlar
from src.comparison.karsilastirma import sirala, Kriter
s = [(k.vade_ay_max, round(k.ortalama_guven,3))
     for k in sirala(tum_kayitlar(), Kriter.EN_UZUN_VADE) if k.vade_ay_max]
for d, g in groupby(s, key=lambda t: t[0]):
    g = [x[1] for x in g]
    if len(g) > 1 and g != sorted(g, reverse=True):
        print(d, 'ay grubu BOZUK:', g)"
```

**Aynı paneldeki "Kural 1" DOĞRU** — `(1, 0.0)` anahtarı gerçekten eksikleri
sona itiyor. O satır kalsın.

**Yapılacak:** İki seçenek —
1. Kural 2'yi metinden çıkar (10 saniye), **veya**
2. `sirala()`'ya gerçekten güven tie-break'i ekle. Bu şema sözleşmesini değil
   karşılaştırma motorunu değiştirir, ama `tests/` altında karşılığı yazılmalı
   ve bana haber ver — sıralama motoru E-06'nın konusu.

---

## 🔴 K3 — Uydurma metrikler, hem de "Şeffaflık" panelinde

**Nerede:** `app/Genel_Bakis.py:149` ve `:153-155`

```python
st.metric("Sayısal Doğrulama Kalkanı Düzeltme Oranı", "%14", …
          help="LLM'in yaptığı 42 halüsinasyon/hatayı …")
…
# Sahte ama gerçekçi bir kelime hesabı (kayıt sayısı * 500 kelime * GPT-4 fiyatı vs.)
tasarruf = len(kayitlar) * 0.04
```

Bu sayıların hiçbirinin ölçüm karşılığı yok. `docs/SONUCLAR.md`'nin ilk satırı:

> *"Bu dosya elle düzenlenmez. **Sunumdaki her sayı buradan kopyalanır.**"*

Panel "Veri Kalitesi ve **Şeffaflık**" başlığını taşıyor ve alt yazısı
*"veriyi olduğundan iyi göstermek yerine … şeffafça bilgilendirir"* diyor.
Uydurma sayı için mümkün olan en kötü yer burası.

**Önemli:** Gerçek sayılarımız uydurulandan **daha etkileyici**:

| Şu anki (uydurma) | Olması gereken (`docs/SONUCLAR.md`, `make eval`) |
|---|---|
| "%14 düzeltme oranı" | **Halüsinasyon oranı %0,32** (hedef ≤%3) ✅ |
| "42 halüsinasyon" | **Sayısal alan doğruluğu 0,933** (hedef ≥0,90) ✅ |
| "GPT-4 tasarrufu ~$3.84" | **Şema geçerliliği 1,00** · 6 sızıntı testi geçiyor |

Yanına makro-F1'i **güven aralığıyla** koy: `0,736 (%95 GA: 0,610–0,810), n=60`.
Hedefin (0,78) altında — ama hedefin altında olduğunu kendisi söyleyen bir ekran
jüriye "bu takım kendi sayısını biliyor" der. Saklarsak zaten soracaklar.

**Yapılacak:** Üç kartı `docs/SONUCLAR.md`'den besle. Elle yazma — sayı orada
değiştiğinde ekran da değişsin.

---

## 🟠 K4 — Banka adları sayfadan sayfaya değişiyor

**Nerede:** `app/pages/1_Karsilastirma.py:195`

Genel Bakış `format_bank_name()` kullanıyor, Karşılaştırma ham `.replace()`.
**8 bankanın 4'ü farklı görünüyor:**

| Ham ad | Genel Bakış | Karşılaştırma |
|---|---|---|
| Ziraat Katılım Bankası A.Ş. | Ziraat Katılım | **Ziraat** |
| Vakıf Katılım Bankası A.Ş. | Vakıf Katılım | **Vakıf** |
| Dünya Katılım Bankası A.Ş. | Dünya Katılım | **Dünya** |
| Türkiye Emlak Katılım Bankası A.Ş. | Emlak Katılım | **Türkiye Emlak** |

`app/ui_utils.py`'nin docstring'i bu hatanın 16 Ağustos'ta yaşandığını ve kayıt
defteri tek doğruluk kaynağı yapılarak çözüldüğünü yazıyor. Karşılaştırma sayfası
hâlâ eski yöntemi kullanıyor.

> **Not — bu satır Esra'nın değil.** `git blame` Sprint 0'a çıkıyor (`ec313d8`,
> Eren). ES-05/06/07 commit'lerinden gelmiyor; sayfa Esra'nın alanı olduğu için
> listeye alındı.

**Yapılacak:** `format_bank_name(k.banka_adi)` kullan. Tek satır.

---

## 🟠 K5 — "Eleştirmen Ajan" chatbot'ta yok (ama çıkarımda VAR)

> 🔁 **18 Ağu akşamı düzeltildi.** İlk yazdığımda "eleştirmen ajanı hiç
> çalışmıyor" demiştim — bu yanlıştı. E-02 Docker testinde ajan gözümün önünde
> devreye girdi. Doğrusu aşağıda.

Ajan **iki kod yolundan yalnız birinde** var:

| Kod yolu | Eleştirmen ajanı | Kanıt |
|---|---|---|
| **Çıkarım** (`boru_hatti` → `extraction/llm.py`) | ✅ **çalışıyor** | `boru_hatti.py:104` · `llm.py:212` |
| **Chatbot** (`rag/chatbot.py`) | ❌ yok | `grep ElestirmenAjani src/rag/chatbot.py` → 0 |

Çıkarım hattında gerçekten iş yapıyor. 18 Ağustos'ta konteynerde koşan `seed`
çıktısından, canlı:

```
INFO src.extraction.llm: masrafsiz_mi reddedildi: kararı destekleyen cümle yok
                         (https://ornek.test/kampanya/kart)
```

**Dolayısıyla iki yer farklı muamele görmeli:**

- `app/pages/2_Chatbot.py:88` — **yanlış, düzelt.** Chatbot'ta sayıları reddeden
  `sayisal_dogrulama` kalkanıdır, eleştirmen ajanı değil. "Sayısal Doğrulama
  Kalkanı devreye girdi" yaz.
- `app/Genel_Bakis.py:149` — "Eleştirmen Ajan Aktif" ifadesi **savunulabilir**,
  çünkü çıkarım hattı gerçekten onu kullanıyor. Buradaki sorun ajanın adı değil,
  yanındaki **uydurma sayılar** (bkz. K3).

**Bonus:** Jüri "eleştirmen ajanını çalışırken gösterin" derse artık gösterilecek
şey var — `python -m src.boru_hatti -v seed` çıktısındaki ret satırı. Bu ES-15
(model çıktı örnekleri) için de birinci sınıf malzeme.

---

## 🟠 K6 — cURL örnekleri hayali adrese gidiyor

**Nerede:** `1_Karsilastirma.py:329`, `2_Chatbot.py:169`

```
https://api.svartal.bank/v1/…   +   Bearer YOUR_API_KEY
```

Böyle bir alan adı yok. Oysa **gerçek sunucu var** — `src/api/sunucu.py`:

| Uç | Yöntem | Girdi |
|---|---|---|
| `/compare` | GET | `kriter`, `banka_kodu`, `kampanya_turu`, 4 ağırlık (query) |
| `/ask` | POST | `{"soru": "…"}` |
| `/extract` | POST | `{"metin": "…", "url": "…"}` |
| `/saglik` | GET | — |

Çalışan API'yi saklayıp sahtesini göstermek, elimizdeki en somut B2B kanıtını
harcıyor. Jüri önünde `make api` açıp komutu **canlı çalıştırmak** çok daha güçlü.

**Yapılacak:** cURL'leri `http://localhost:8000/...` gerçek uçlarına çevir.

---

## 🟠 K7 — Örnek soru tuzağı (demo riski)

`2_Chatbot.py:46` — kenar çubuğundaki örnek sorulardan biri:

> *"Kampanya koşulları neler?"*

Bu soru kalkanı tetikliyor ve ekrana kırmızı ⛔ *"Sayısal doğrulama başarısız"*
kutusu geliyor. Sistem **doğru** çalışıyor (model uydurdu, kalkan yayınlatmadı) —
ama jürinin ilk tıkladığı butonda kırmızı hata görmesi kötü.

İki seçenek:
1. Soruyu listeden çıkar.
2. **Bırak, ama planla:** yanına "🛡️ Kalkan gösterimi" etiketi koy. Doğru
   anlatılırsa %10'luk yenilikçilik kaleminde en güçlü 20 saniyemiz olur —
   *"bakın, model uydurdu, sistemimiz yayınlamadı."* Ama sürpriz olarak değil,
   **kasıtlı** olmalı. Bu ES-10'un tam konusu.

**Ek:** reddedilen sayılar tekrarlı basılıyor —
`25, 1.000, 500, 500, 25, 1.000, 500, 500`. Tekilleştirme gerek.

---

## 🟢 Küçük temizlik

| Yer | Sorun |
|---|---|
| `1_Karsilastirma.py:92, 96, 103` | `hasattr(x, "var_mi")` savunması **ölü kod** — ORM modelinde `Alan` yok, düz sütun var. Pydantic şeması ile ORM şeması karışmış. |
| `1_Karsilastirma.py:183-190` | `if not sirali:` bloğu **erişilemez** — üstte `if not suzulmus: st.stop()` var. İçindeki Streamlit sürüm yorumu da alakasız. |
| `1_Karsilastirma.py:320-322` | Arka arkaya iki `st.divider()` |
| `Genel_Bakis.py:166` | `# Jüri tavsiyesi üzerine nbins=10` — bağlamsız yorum |
| `Genel_Bakis.py:200` | `# Sidebar: Geliştirici Modu taşındı` — ölü yorum |
| `0_Musteri_Profili.py:36` | Geliştirici modu anahtarı var ama o sayfada **hiç dev içeriği yok** — ölü anahtar |
| `2_Chatbot.py:92` | "Model: Yerel Qwen (Ollama)" yazıyor, ama tekil sorgu ve karşılaştırma yollarında LLM hiç çalışmıyor (ölçüm: 0,0 sn). Yanıltıcı. |
| `d28f08f` | `ConnectionError`'ın neden yerleşik olanın yakalandığını açıklayan yorum silinmiş. O yorum gerçek bir hata düzeltmesini belgeliyordu — geri konmalı, yoksa tekrar bozulur. |
| `Genel_Bakis.py` doluluk grafiği | **Ürün Türü %0** çıkıyor. Sayı doğru (`SONUCLAR.md` de %0 diyor) ama açıklamasız duruyor; jüri soracak. |

---

## ⚙️ Ortam — PyArrow çökmesi (Esra'nın kodu değil)

18 Ağustos'ta sayfa geçişinde uygulama **komple çöktü** (SIGSEGV, Python crash
raporu, sonra "sunucuya bağlanılamıyor"). Sebep:

```
libarrow.2500.dylib   mi_heap_main
libarrow.2500.dylib   mi_thread_init      ← mimalloc
      ⋮
pyarrow.Table.from_pandas
```

PyArrow 25.0.0 macOS/arm64'te varsayılan **mimalloc** ayırıcısıyla, thread
yeniden başlatılırken çöküyor. Streamlit her sayfa geçişinde yeni ScriptRunner
thread'i açtığı için `st.dataframe` olan bir sayfadan çıkınca tetikleniyor.

**Çözüm:** `ARROW_DEFAULT_MEMORY_POOL=system`

Doğrulama: dört sayfa tek süreçte önce `exit 139` (segfault), sonra `exit 0`.

Bunu `Makefile`'ın `run` hedefine kalıcı olarak eklemek gerekiyor — yoksa
`make run` diyen herkeste, **jüri önünde dahil** tekrar çöker.

---

## Sıra önerisi

| # | İş | Süre | Neden |
|---|---|---|---|
| 1 | K1, K2, K3 — üç yanlış iddiayı kaldır | ~30 dk | Jüri birini yakalarsa doğru olan her şeyin güvenilirliği gider |
| 2 | K3 — kartları `SONUCLAR.md`'den besle | ~1 sa | En yüksek getiri; gerçek sayılar zaten daha iyi |
| 3 | K7 — örnek soru seti (ES-10) | ~15 dk | Demo riski |
| 4 | K6 — gerçek API uçları | ~20 dk | Canlı çalışan B2B kanıtı |
| 5 | K4 — `format_bank_name` | ~10 dk | Tek satır |
| 6 | Makefile Arrow düzeltmesi | ~5 dk | Demo çökme riski |
| 7 | ES-08 yan yana karşılaştırma | ~yarım gün | Şartname madde 11'in örnek tablosu tam olarak bu; motor hazır |
| 8 | ES-09 CSV/Excel indir | ~2 sa | `download_button` kodda hiç geçmiyor |

1–6 birlikte yaklaşık 2 saat ve arayüzün jüri riskini sıfırlıyor.
Bunlar panoda **ES-19** altında tek tek işaretlenebilir madde olarak duruyor.
7 ve 8 zaten ES-08 ve ES-09.
