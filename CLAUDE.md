# SVARTAL — Katılım Bankacılığı Metin Madenciliği

TEKNOFEST 2026 Yapay Zekâ Dil Ajanları Yarışması, 2. Senaryo.
Dört kişilik takım: **Eren** (kaptan), **Samet**, **Görkem**, **Esra**.

**Bu projede Türkçe konuşulur.** Kod, yorum, commit mesajı, dokümantasyon —
hepsi Türkçe. Değişken ve fonksiyon adları da Türkçe (`kar_payi_orani`,
`kurallarla_cikar`, `Alan.yok()`).

---

## 🔴 HER OTURUMDA — GIT PROTOKOLÜ

Dört kişi aynı depoda çalışıyor. **Bu iki adım atlanırsa iş kaybı olur.**

### Çalışmaya BAŞLARKEN

**İlk iş: kullanıcıya "GitHub'daki değişiklikleri pull ettin mi?" diye sor.**

```bash
git pull --rebase origin main
```

Oturum başında bir hook otomatik `git fetch` yapar ve geride kalınmışsa uyarır.
**Uyarı geldiyse, kullanıcı pull etmeden hiçbir dosyayı düzenleme.** Pull
edilmeden yapılan düzenleme çakışma üretir; kötü ihtimalde arkadaşının işi ezilir.

Hook sessiz kaldıysa (ağ yoksa) yine de sor — hatırlatmak bedava, iş kaybı değil.

### Çalışmayı BİTİRİRKEN

**Son iş: kullanıcıya "pushladın mı?" diye sor.**

```bash
git add -A
git commit -m "..."
git push origin main
```

Pushlanmayan iş kimseye ulaşmaz. `GOREVLER.md`'de o işi bekleyen arkadaşı
boşuna bekletir.

Ayrıca: **bitirilen görevin yanına `GOREVLER.md`'de `[x]` atıldı mı?** Bunu da hatırlat.

> **Commit imzası:** Bu depoda commit'lere yapay zekâ imzası (`Co-Authored-By`
> vb.) **eklenmez**. Takım kendi adıyla commit atar.

---

## 📋 "Benim görevim ne?" — görev panosu

Tek doğruluk kaynağı [`GOREVLER.md`](GOREVLER.md). Kişi sorduğunda oradan cevapla.

```bash
make gorev ad=Esra        # kişinin yapabilecekleri + bloke olanlar
make gorev                # herkesin özeti + darboğazlar
make gorev-dogrula        # panonun bağımlılıklarını denetle
```

Görevler arasında **bağımlılık var**. Bir görevde `⛔ Önce bitmeli:` satırı
varsa, orada yazan görevler bitmeden o işe başlanamaz. Kullanıcı bloke bir işe
girmek isterse **uyar** ve listedeki bir sonraki yapılabilir işe yönlendir.
Boşta beklemek en pahalı şeydir.

Kritik yol: `H-01 (altın set) → S-12 (make eval) → S-13 (ablasyon) → ES-13 (sunum)`

---

## Sistem — kısa özet

`make crawl` → `make extract` → `make run`

| Katman | Yer |
|---|---|
| Şema sözleşmesi (**DONMUŞ**) | `src/schema.py` |
| Türkçe normalizasyon | `src/preprocessing/normalizasyon.py` |
| Toplama altyapısı (kayıt defteri · robots · nezaket) | `src/collector/toplayici.py` |
| Banka kazıyıcıları (Selenium, 9 banka) | `src/collector/kaziyicilar/` |
| Hibrit çıkarım | `src/extraction/{kural,llm,uzlastirici}.py` |
| Ajanlar (5, dördü LLM'siz) | `src/ajanlar/{uygunluk,elestirmen,yuklem,muhakeme,orkestrator}.py` |
| LLM sağlayıcı (EVREN / Ollama) | `src/extraction/saglayici.py` |
| Depolama | `src/depolama.py` |
| Karşılaştırma | `src/comparison/karsilastirma.py` |
| Chatbot + kalkan | `src/rag/chatbot.py` |
| RAG gömme + kosinüs arama | `src/vektor_db.py` |
| Arayüz / API | `app/` · `src/api/sunucu.py` |
| Tetikleyici · dinleyici (G-17) | `src/izleme/{tetikleyici,dinleyici}.py` |
| Canlı boru hattı sayfası | `app/pages/4_Boru_Hattı.py` · `app/akis.py` · `app/boru_durumu.py` · `app/is_yurutucu.py` |

Ayrıntı: [`docs/MIMARI.md`](docs/MIMARI.md) · Güncel ölçüm: [`docs/SONUCLAR.md`](docs/SONUCLAR.md) ·
Sprint 0 raporu (tarihsel): [`docs/SPRINT0_RAPORU.md`](docs/SPRINT0_RAPORU.md)

---

## Değiştirmeden önce bilinmesi gerekenler

**`src/schema.py` donmuştur — güncel sürüm `SEMA_SURUMU` sabitinde.**
Dört kişi bu şemaya karşı çalışıyor. Değiştirmek gerekiyorsa: takıma duyur,
`docs/kararlar/` altına ADR yaz, sürümü yükselt. Sessiz değişiklik dördünün
işini birden bozar.

Donma "hiç değişmez" demek değil, **ADR'siz değişmez** demek. Şimdiye kadar iki
kez, ikisi de usulünce: v1.0.0 → v1.1.0 ([ADR 006](docs/kararlar/006-sema-v1-1-uygunluk.md),
uygunluk koşulları) → v1.2.0 ([ADR 009](docs/kararlar/009-boyutlu-nicelik.md),
`Alan.birim`). İkisi de eklemeli; kayıtlar kendi `sema_surumu`'nu taşıdığı için
eski veri geçerli kalır.

**Toplama Selenium ile yapılır, banka başına kazıyıcı vardır (26 Ağu).**
Burada eskiden *«tek jenerik toplayıcı, banka başına özel kod YOK»* yazıyordu.
Doğru değildi: kampanya listeleri JS ile render edilip «daha fazla yükle»
butonuyla sayfalandığı için httpx yolu kartların çoğunu göremiyordu ve
`data/raw`'daki 1.024 kaydı fiilen **Selenium kazıyıcıları** üretti. Kod artık
veriyi üreten yolu gösteriyor: `src/collector/kaziyicilar/` altında dokuz sınıf.

Banka başına değişen tek şey **URL keşfidir** (`kampanya_urlleri()`). Gezme,
robots kapısı, nezaket, gövde ayıklama ve `HamKayit` üretimi `TemelKaziyici`'de
tektir — dokuz yerde tekrarlanmaz. Başlangıç adresleri kazıyıcıda değil
`data/banks.yaml` · `seed_urls` içindedir; `tools/robots_kanit.py` robots
kanıtını o listeden üretiyor, ikiye ayrılırsa kanıt yanlış adresleri denetler.

**Kanıtsız değer üretilemez.** Her `Alan` kaynağını, güvenini ve hangi katmandan
geldiğini taşır. `Alan(deger=2.05, yontem="belirtilmemis")` `ValueError` fırlatır.
Bu kısıtı gevşetme.

**Sayısal cevaplar yapısal veriden gelir, metin aramasından değil.** Chatbot'taki
sayısal doğrulama kalkanını (`sayisal_dogrulama`) zayıflatma — sistemin en özgün
iddiası bu. Kalkan yanlış pozitif veriyorsa çözüm kalkanı gevşetmek değil,
denetlenecek metni doğru seçmektir (`Cevap.dogrulanacak_metin`).

**Llama ve Gemma türevi model KULLANILMAZ.** Şartname 5.10 doğrudan bunları
hedefliyor. Yalnız Apache 2.0 / MIT (Qwen3.5, Qwen3.6). EVREN'deki `llm-large`
ve `llm-fast` ikisi de Qwen ailesi — yasağa takılmıyor.

**EVREN'de sunulan modeller uygun sayılır (ADR 013, 25 Ağu).** Servis, yarışmayı
düzenleyen SSB'nin tahsis ettiği servistir. Ama buna **yaslanmıyoruz**: fiilen
kullandığımız her modelin lisansı ayrıca teyitli — üç Qwen (Apache-2.0) ve RAG
gömmesi `bge-m3-embed` → `BAAI/bge-m3` (MIT). Jüriye verilen cevap duruş değil,
`docs/kanit/model-lisanslari.json`.

**Gömme için `bge-m3-embed` kullanılır** — lisanstan önce gelen bir sebeple:
ölçüldü, o uç **1024 boyut** veriyor (`vektor_db.BOYUT` ile birebir, ayrıca
BGE-M3 kimliğinin teyidi). Jenerik `embed` ucu **2560** veriyor, yani bu koda
hiç uymuyor. `embedding` diye bir uç ise EVREN'de **yok** — kodun eski
varsayılanı buydu ve sessizce 404 alıyordu.

**RAG'da harici vektör veritabanı YOK (ADR 014, 25 Ağu).** `qdrant.ssyz.org.tr`
DNS'te çözülmüyordu ve öyle bir servisin tahsis edildiğine dair belge yoktu.
15.151 paragraf yerel bir `.npz` dosyasında duruyor, arama numpy nokta çarpımı
— milisaniyeler. `make vektor` ile kurulur (~70 sn), `make durum` kurulu olup
olmadığını gösterir. **İndeks 26 Ağustos'ta depoya alındı** (32 MB): ağsız
kurulamıyor — gömmeler EVREN'den geliyor — dolayısıyla türetilmiş değil,
taşınması gereken bir varlık. Çevrimdışı pakete elle kopyalama adımı kalktı.

`make durum` artık indeksin **bayat olup olmadığını** da söyler: indeks
kurulduğu korpusun izini (`vektor_db.korpus_izi`) taşır, `make extract` ya da
kayıt silme sonrası iz tutmaz ve uyarı çıkar. Bu denetim olmadan chatbot
silinmiş kampanyaları kaynak göstererek cevap veriyordu.

**Tazelik dinleyicisi kendi tabanını kurar, tetikleyici KURULU DEĞİL (27 Ağu).**
`src/izleme/` değişikliği TESPİT eder, veriyi TAZELEMEZ — `data/raw` ve
`data/katilim.db` teslim için donmuş, kendiliğinden koşan bir iş `make eval`
sayıları ile `docs/SONUCLAR.md`'yi sessizce ayrıştırırdı. Üç şey ölçüldü:
9 bankanın **2'si** `ETag`/`Last-Modified` veriyor (7'si vermiyor, içerik özeti
şart) · `httpx` ile Selenium **7/9** bankada birebir aynı gövdeyi veriyor, bu
yüzden taban çizgisi **dinleyicinin kendi yolundan** kurulur (ilk koşu
değişiklik iddia etmez) · özet **bütün boşlukları atar**, çünkü Albaraka aynı
sayfayı tek boşluk farkıyla iki biçimde veriyor ve dakikada bir yanlış alarm
üretiyordu. Ayrıntı: `docs/kararlar/018-tetikleyici-dinleyici.md`.

**PyArrow ayırıcısı `system` olmalı — `ARROW_DEFAULT_MEMORY_POOL`.**
PyArrow 25 macOS/arm64'te varsayılan `mimalloc` ile, thread yeniden
başlatılırken SIGSEGV veriyor. Streamlit her sayfa geçişinde yeni ScriptRunner
thread'i açtığı için `st.dataframe` olan bir sayfadan çıkınca **sunucu komple
ölüyor** — hata sayfası bile çıkmadan. Değişken üç yerde kurulu: `Makefile`
(`export`, tüm hedefler), `tests/conftest.py`, `app/Genel_Bakış.py`. Üçü de
`pyarrow` import'undan önce çalışmak zorunda; `pandas` pyarrow'u kendi
import'unda getirdiği için sonradan kurmak hiçbir şey değiştirmez. Bu satırları
«gereksiz» diye temizleme — 18 ve 27 Ağustos'ta iki kez ısırdı, ikincisinde
`make test`'i komple çökertti. Nöbetçi: `tests/test_arayuz_pyarrow_ayirici.py`.
Ayrıntı: [`docs/ARAYUZ_INCELEME.md`](docs/ARAYUZ_INCELEME.md) — «Ortam».

**Sessiz yutma yasak.** Gömme hatası da, arama hatası da fırlatılır. Bu kural
bedava öğrenilmedi: `embed_text` sıfır vektörü, `vektor_ara` boş liste
döndürdüğü için RAG dört gün hiç çalışmadan çalışıyor göründü. Sıfır vektörü de
uydurma bir değerdir — `Alan(deger=..., yontem="belirtilmemis")` neden
patlıyorsa o da patlamalı.

**Arayüzden koşan boru hattı DEMO ALANINA yazar (26 Ağu).** «Canlı Boru Hattı»
sayfası (`app/pages/4_Boru_Hattı.py`) gerçek kazıyıcıyı ve gerçek çıkarım hattını
sürer, ama hedefi `data/demo_raw/` + `data/demo/demo.db`'dir. Üretim verisine
ancak sekmedeki **kapalı gelen** onay kutusu işaretlenirse dokunulur. Demo kipi
sayfa SAYISINI kısar (`topla(azami_sayfa=...)`), temposunu değil — nezaket kuralı
ve robots kapısı demoda da işler. Animasyon koşunun kendi olaylarından beslenir;
sahte ilerleme, sahte sayaç, uydurma gecikme yoktur.

**Streamlit sayfasında `@dataclass` TANIMLAMA — bedeli ölçüldü.** Sayfa betiği her
çizimde baştan koşar, yani orada tanımlı bir sınıf her koşuda YENİ nesne olur;
`st.session_state`'te duran örnek eski sınıftan geldiği için `isinstance` **False**
döner ve biriken durum sessizce sıfırlanır. Ölçüldü: canlı sayaç iki kayıt
işlenmişken «1 / ?» kaldı. Bu yüzden durum sınıfları `app/boru_durumu.py`'de,
modül düzeyinde durur. Aynı sebeple bitmiş işin sonucu yalnız canlı parçada değil,
betiğin **her tam koşusunda** devralınır (`_bekleyen_isi_devral`) — sayfa
değiştirilip dönüldüğünde sonuç kaybolmasın diye.

Yeni bağımlılık eklendiğinde `make lisanslar`, yeni model eklendiğinde
`make lisanslar-teyit` çalıştır (lisansı HF'ten çeker, tutmazsa kırılır).

**Çıkarım EVREN'de koşuyor (24 Ağu).** T.C. Cumhurbaşkanlığı SSB'nin yarışmaya
tahsis ettiği servis. `llm-large` = **`Qwen/Qwen3.5-122B-A10B`** — MoE, 122B
toplam / 10B aktif, BF16 (kuantizasyon yok), 262.144 token bağlam, tensör
paralelliği 4. Lisans **Apache-2.0**, iki kaynaktan teyitli (EVREN model kartı
+ HF deposu) — şartname 5.10 kanıtı `docs/SARTNAME_UYUM.md`'de.
Ölçülen: 13 sn/kayıt → 0,43 sn/kayıt (16 işçi), doluluk kırpılan kayıtlarda
+8 puan. Sağlayıcı katmanı `src/extraction/saglayici.py`; orada ölçülmüş **üç
sessiz tuzak** yazılı (`chat_template_kwargs` üst seviyede olmalı, `guided_json`
yok sayılıyor, `max_tokens` 4096) — okumadan o dosyaya dokunma.

**Yerel yol silinmedi, yedektir.** `make extract-yerel` (`LLM_SAGLAYICI=ollama`)
aynı kod yolunu yerel Ollama ile koşar: EVREN düştüğünde ve hava boşluğu
demosunda. Yerelde `CIKARIM_ISCI=1` zorunlu ve **Streamlit'i kapat** — 8 GB
makinede aynı anda açık olunca kayıt başına 13 saniye yerine 2,5 dakika sürer
(bellek takası). EVREN'de bu kısıtların ikisi de yok, iş bizim makinemizde değil.

**EVREN bayt düzeyinde deterministik DEĞİL — ölçüldü.** `temperature=0` ve sabit
tohuma rağmen aynı girdi 5 kayıttan 3'ünde farklı çıktı verdi (ortak vLLM
sunucusunda sürekli yığınlama).

**SAPMA SAYISAL ALANLARA DA VURUYOR — 25 Ağustos'ta 98 kayıtta ölçüldü.**
Buradaki eski kayıt *«8 kayıt × 4 koşuda oynayan alanların tamamı serbest
metindi; sayısal ve enum alanlarda sıfır sapma»* diyordu. O ölçüm 8 kayıtlıktı
ve **yanıltıcı çıktı.** Altın setin 98 kaydı aynı kodla iki kez çıkarıldığında:

```
oynayan hücre: 7 / 784 (%0,9) — hepsi sayısal/enum
  kampanya_turu 2 · tahsis_ucreti 2 · kar_payi_orani 1 · vade_ay_max 1 · masrafsiz_mi 1
örnek: tahsis_ucreti 0,5 → 20,0   ·   vade_ay_max 84 → 60
makro-F1: koşu-1 0,735   koşu-2 0,724      ← aynı kod, aynı girdi
```

**Sonuç: `make eval` sayısı ±0,01 gürültü taşır.** Sunumda «makro-F1 0,72»
demek doğrudur, «0,724» demek yanlış bir kesinlik iddiasıdır. İki koşunun
farkını iyileşme sanmayın — bir değişikliğin etkisi ancak bu bandın dışındaysa
gerçektir.

`docs/SONUCLAR.md` sayıları işlenmiş veritabanından üretildiği için o dosya
kendi içinde tutarlı kalır; yeniden üretilen şey veritabanının kendisi değildir.
Bayt düzeyinde tekrarlanabilirlik şartsa: `LLM_SAGLAYICI=ollama`.

---

## Komutlar

```bash
make kur          # kurulum
make crawl        # kampanya topla  [Chrome gerekir; gorunmez=1 headless, banka=0212 tek banka]
make extract      # çıkarım (kural + LLM) -> SQLite  [EVREN]
make extract-yerel      # aynı çıkarım, yerel Ollama ile (yedek / hava boşluğu)
make saglayici-dogrula  # EVREN bağlantısı + şema kısıtı sınaması
make durum        # kaç kampanya, kaç banka, RAG indeksi kurulu mu
make vektor       # RAG vektör indeksini kur (gömme + kosinüs, ~70 sn)
make tazelik      # kampanya sayfaları değişmiş mi (G-17) [adet=N demo=1]
make run          # Streamlit arayüzü
make test         # testler (1064 test)
make eval         # metrikler -> docs/SONUCLAR.md
make ablasyon     # 5 kollu ablasyon (katman + ajan katkısı), ~25 dk
make uygunluk-goc # mevcut kayıtlara uygunluk koşullarını yaz (A-08, LLM'siz)
make kapsam       # banka bazlı kapsam raporu -> docs/KAPSAM_RAPORU.md
make cikti-ornekleri    # model çıktı örnekleri -> docs/CIKTI_ORNEKLERI.md
make veri-seti    # yayınlanabilir veri seti + veri kartı -> data/exports/
make sunum        # docs/sunum/sunum.html -> Svartal_Sunum.pdf (10 sayfa)
make lisanslar    # bağımlılık + model lisans raporu
make lisanslar-teyit    # aynı rapor + model lisanslarını HF'ten teyit et (ağ)
make kanit        # veri toplama etiği kanıtları (robots günlüğü + KVKK taraması)
make gorev ad=X   # görev durumu
```

Değişiklikten sonra: **`make test` ve `make lint` yeşil olmalı.**
