# Kurulum ve Çalıştırma

Şartname madde 6, *"Projenin çalıştırılması için adım adım talimatlar (kurulum,
çalıştırma)"* istiyor. Bu doküman o maddedir.

> **Test edilmiş ortam:** Apple M1, 8 GB RAM, macOS 15.6 (Profil C — GPU yok).
> Sistem bu donanımda uçtan uca çalışacak şekilde ayarlanmıştır.

---

## Yol 1 — Docker (önerilen, tek komut)

### Gereksinimler
- Docker Engine 24+ ve Docker Compose v2
- ~10 GB boş disk (model dahil)

> **`crawl` konteynerde koşmaz (26 Ağu 2026).** Toplama Selenium'a taşındı ve
> `python:3.12-slim` imajında Chrome yok. İmaja Chrome koymak, bankacılık
> ortamına giden imajın boyutunu ve saldırı yüzeyini ciddi biçimde büyütür;
> bilinçli olarak koyulmadı. Konteyner **toplanmış** `data/raw`'ı işler
> (`extract`, `seed`, `durum`, arayüz). Yeniden toplamak gerekiyorsa yerel
> kurulumda `make crawl` koşulur, `data/raw` bağlı hacme kopyalanır.

### Adımlar

```bash
git clone https://github.com/erenkendir722/ai-agent-nlp.git
cd ai-agent-nlp

docker compose up -d
```

Üç servis ayağa kalkar: `katilim-ollama`, `katilim-uygulama`, `katilim-api`.
`uygulama` ve `api`, `ollama` sağlıklı olana kadar bekler (`depends_on`).

**Model otomatik inmez** — bir kez elle çekilir (~3,4 GB):

```bash
docker compose exec ollama ollama pull qwen3.5:4b-q4_K_M
```

Model adlandırılmış hacimde (`ollama-modelleri`) durur; `docker compose down`
sonrası da kalır, tekrar indirilmez.

Sonra boru hattı:

```bash
docker compose exec uygulama python -m src.boru_hatti durum     # veritabanı özeti
# crawl KONTEYNERDE YOK — Chrome gerektiriyor, bkz. yukarıdaki uyarı
docker compose exec uygulama python -m src.boru_hatti seed      # ağ GEREKMEZ
docker compose exec uygulama python -m src.boru_hatti extract
```

| Servis | Adres | Sağlık ucu |
|---|---|---|
| Streamlit arayüzü | <http://localhost:8501> | `/_stcore/health` |
| REST API (Swagger) | <http://localhost:8000/docs> | `/saglik` |

Durdurma: `docker compose down` · Hacimlerle birlikte: `docker compose down -v`

> ⚠️ **`down -v` modeli de siler.** Air-gap ortamında tekrar indiremezsiniz.

### Doğrulanmış çalıştırma — 18 Ağustos 2026

E-02 kapsamında gerçekten koşuldu (Apple M1, 8 GB RAM, Docker 29.7.2, 5,8 GB
konteyner belleği, aarch64):

| Adım | Sonuç |
|---|---|
| `docker compose build` | ✅ ilk denemede, hatasız (`svartal-uygulama`, `svartal-api`) |
| `docker compose up -d` | ✅ üç konteyner de **healthy** |
| Streamlit `:8501` | ✅ HTTP 200 · `/_stcore/health` 200 |
| API `:8000/docs` | ✅ HTTP 200 · `/saglik` → `{"durum":"ayakta","kampanya_sayisi":96,"dis_bagimlilik":false}` |
| `/compare?kriter=en_uzun_vade` | ✅ 96 sonuç + 3 finansal uyarı |
| Konteynerler arası ağ | ✅ `uygulama` → `http://ollama:11434` |
| Konteynerde LLM çıkarımı | ✅ 19,1 sn (soğuk başlangıç, CPU) · `qwen3.5:4b-q4_K_M` |
| `exec … boru_hatti durum` | ✅ 96 kampanya, 8 banka |
| `exec … boru_hatti crawl` | ✅ 18 Ağu'da (httpx toplayıcısıyla) çalışıyordu. **26 Ağu'dan beri geçersiz:** toplama Selenium'a taşındı, imajda Chrome yok |
| `exec … boru_hatti seed` | ✅ **1 dk 36 sn** · hibrit çıkarım: kuraldan 10 alan, LLM'den 6 alan, 0 çelişki · «✅ Kanıt denetimi: tüm değerler ham metinde doğrulandı» |
| Eleştirmen ajanı (konteynerde) | ✅ devreye girdi: `masrafsiz_mi reddedildi: kararı destekleyen cümle yok` |

> **`seed` neden `extract` yerine kullanıldı:** ikisi de aynı `_cikar_ve_kaydet`
> yolunu (kural + LLM + eleştirmen) koşar; `seed` ağ gerektirmez ve altın setin
> dayandığı 9 Ağustos ham verisine dokunmaz. Kanıt değeri aynı, yan etkisi yok.

**Bellek:** `ollama` tek başına 4,36 GB, `uygulama` 175 MB, `api` 64 MB —
toplam ~4,6 GB. 8 GB makinede çalışır ama **yerel Ollama ve Streamlit'i kapatın**,
yoksa takas başlar.

**Kaynak kullanımını görmek için:** `docker stats --no-stream`

### Hava boşluğu (air-gap) — E-07, 18 Ağustos 2026

Yığın iki ağa ayrıldı. Amaç: **model sunucusunun internete rotası fiziksel
olarak olmasın**, ama arayüz tarayıcıdan açılabilsin.

| Ağ | `internal` | Kim var | Ne için |
|---|---|---|---|
| `ic-ag` | ✅ **true** | ollama, uygulama, api | Konteynerler arası; dışarı çıkış YOK |
| `sunum` | false | uygulama, api | Yalnız 8501/8000'in host'a yayınlanması |

`ollama` **yalnız `ic-ag`'de**. Ölçüm tek komutla tekrarlanabilir:

```bash
make hava-boslugu
```

Çıktı (konteyner içinden):

```
✅ engellendi: 8.8.8.8:53
✅ engellendi: 1.1.1.1:443
✅ engellendi: DNS huggingface.co
```

Hepsi **anında** başarısız — zaman aşımı değil, *rota yok*. Bu bir vaat değil,
altyapı kısıtı: uygulama kodu değiştirilse bile model sunucusundan paket
dışarı çıkamaz.

> 🔬 **Ölçüm neden güvenilir — pozitif kontrol.** «Engellendi» sonucu ancak
> probun çalıştığı kanıtlanırsa anlamlıdır. `make hava-boslugu` her servis
> için önce **ulaşılması gereken** bir hedefe bağlanır (ollama kendi
> `127.0.0.1:11434`'üne, diğerleri `ollama:11434`'e); o başarısızsa ölçümü
> geçersiz sayar ve sonuç raporlamaz.
>
> Bu kontrol gerçek bir hatayı yakaladı: ilk ölçüm `sh -c 'echo > /dev/tcp/…'`
> kullanıyordu, ama **`/dev/tcp` bir bash özelliği** ve `sh` (dash) onu
> desteklemiyor — prob her zaman «engellendi» diyordu. `bash`'e geçildi.
> Ölçüm aracının kendisi test edilmeden ölçüme güvenilmez.

Ve bu haldeyken sistem tam çalışıyor:

| Kontrol | Sonuç |
|---|---|
| Streamlit + 3 alt sayfa | ✅ 200 |
| API `/docs`, `/saglik` | ✅ 200 · `dis_bagimlilik: false` |
| `uygulama` → `ollama` | ✅ 200, model listeleniyor |
| **LLM çıkarımı** | ✅ **24,4 sn** · `qwen3.5:4b-q4_K_M` |
| Chatbot `/ask` | ✅ kaynak göstererek cevap verdi |

#### ⚠️ Dürüst sınır — fazla iddia etmeyin

`uygulama` ve `api`, port yayını için `sunum` ağında da olmak zorunda ve
**o ağ üzerinden dışarı çıkabiliyorlar** (ölçüldü: 8.8.8.8'e ulaştılar).
Yani altyapı kısıtı **model katmanında** var, uygulama katmanında yok.

Uygulama katmanının dış çağrı yapmadığının kanıtı testtir:
`tests/test_sizinti_yok.py` (6 test) — kural katmanı, normalizasyon,
karşılaştırma motoru ve chatbot'un yapısal sorgu yolu ağ kullanmıyor,
sabit kodlanmış dış API ucu yok, LLM yalnız yerel Ollama'ya bağlanıyor.

**Tam kapalı gösterim için host'un Wi-Fi'ını kapatın.** O zaman `sunum` ağının
da gidecek yeri kalmaz ve iddia eksiksiz olur.

#### 🔴 Tek ağ yapmayın — 18 Ağu'da öğrenildi

İlk denemede `ic-ag` tek ağdı ve `internal: true` açıldı. Sonuç:

```
önce:  0.0.0.0:8501->8501/tcp        sonra:  8501/tcp
```

`internal: true` olan bir ağda Docker **`ports:` yayınını da düşürüyor**.
Konteynerler sağlıklıydı, içeriden 200 dönüyorlardı, ama host'tan 8501 ve
8000 **erişilemez** oldu. Jüri demosunda bu, ekranın kararması demekti.

#### Demo adımları (E-07)

```bash
docker compose up -d
docker compose exec ollama sh -c 'timeout 4 sh -c "echo > /dev/tcp/8.8.8.8/53"' \
  || echo "model sunucusunun internete cikisi YOK"
# Wi-Fi'ı kapat (ekranda görünsün)
# Dashboard ve chatbot çalışmaya devam ediyor
```

---

## Yol 2 — Yerel kurulum

### Gereksinimler

| Bileşen | Sürüm | Not |
|---|---|---|
| Python | **3.11+** | 3.10 altı çalışmaz (birleşim tipi sözdizimi) |
| Google Chrome | güncel | **yalnız `make crawl` için.** Kampanya listeleri JS ile render ediliyor; toplama Selenium ile yapılıyor. Chrome yoksa `crawl` dışındaki her şey çalışır |
| Ollama | 0.6+ | <https://ollama.com/download> |
| Disk | ~5 GB | model + veri |
| RAM | 8 GB | 4B model için yeterli |

### Adımlar

```bash
# 1) Sanal ortam ve bağımlılıklar
make kur

# 2) Ollama'yı başlat (ayrı bir terminalde)
ollama serve

# 3) Modelleri indir (tek seferlik, ~3,4 GB + ~1,2 GB)
ollama pull qwen3.5:4b-q4_K_M   # yedek çıkarım modeli
ollama pull bge-m3              # yedek GÖMME modeli — RAG'ın yerel yolu

# 4) Ortam yapılandırması
cp .env.example .env

# 5) Veri topla (Chrome açılır; nezaket gecikmesi nedeniyle uzun sürer)
#    Tarayıcı penceresi istemiyorsanız:
#        .venv/bin/python -m src.boru_hatti crawl --gorunmez
#    Tek banka denemek için:  ... crawl --banka 0212
make crawl

# 6) Çıkarım yap
make extract

# 7) RAG vektör indeksini kur (~70 sn)
#    Bu adım atlanırsa chatbot sayısal sorulara cevap verir ama
#    "kampanya koşulları neler?" gibi metin sorularında
#    "indeks kurulmamış" der. Ağ ister (EVREN gömme ucu).
make vektor

# 8) Arayüzü aç
make run
```

### Ağ olmadan deneme

Toplama adımını atlayıp tohum veriyle çalışabilirsiniz:

```bash
make seed && make run
```

---

## Çevrimdışı kurulum paketi (fiziki final)

Şartname son 24 saatin fiziki olacağını söylüyor ve orada ek geliştirme
istenebilir. **Etkinlik Wi-Fi'ıyla `pip install` yapmayı planlamayın.**

### Paketi hazırlama (ağ VARKEN, önceden)

```bash
make paket        # bağımlılıkları paketler/ altına indirir
```

USB'ye **iki şey** kopyalanır:

| # | Ne | Neden |
|---|---|---|
| 1 | `paketler/` | Bağımlılıklar (~140 MB) |
| 2 | Deponun kendisi | Kod **+ `data/katilim.db` + `data/vektor_indeksi.npz`** |

> ℹ️ **26 Ağustos'ta değişti: RAG indeksi artık depoda.** Önceden `.gitignore`
> içindeydi ve USB'ye elle kopyalanması gerekiyordu. Adım atlanabilir bir
> adımdı ve atlandığında hata vermiyordu — chatbot açılıyor, sayısal sorulara
> cevap veriyor, yalnız koşul sorularında sessizce kaynaksız kalıyordu.
>
> İndeksi ağsız yeniden kurmak MÜMKÜN DEĞİL: `make vektor` gömmeleri EVREN'den
> alır, yani ağ ve API anahtarı ister. Yerel gömme yedeği yok. Türetilebilir
> olmayan bir dosyayı türetilmiş sayıp depo dışında tutmak yanlıştı.
>
> Bedeli: depoda 32 MB'lık binary. `.gitattributes` onu satır sonu
> dönüşümünden muaf tutar (`*.npz binary`).

### Hedef makinede kurulum (ağ YOKKEN)

```bash
make kur-cevrimdisi
make test
```

**Doğrulandı (25 Ağustos):** temiz bir sanal ortama, indeks sunucusu kapalı
biçimde (`--no-index`) tüm bağımlılıklar kuruldu ve içe aktarıldı.

### 🔴 İŞLETİM SİSTEMİ UYARISI — bu adım atlanırsa paket işe yaramaz

`pip download` **koşulduğu makinenin** tekerleklerini indirir. 25 Ağustos
koşusunda 80 paketin dağılımı şöyleydi:

| Tür | Adet | Taşınabilir mi |
|---|---|---|
| `py3-none-any` (saf Python) | 62 | ✅ her yerde çalışır |
| macOS'a özgü ikili | **18** | ❌ yalnız macOS |

macOS'a bağlı olanlar: `numpy`, `pandas`, `pyarrow`, `pydantic_core`,
`lxml`, `pillow`, `protobuf`, `ruff`, `PyYAML`, `SQLAlchemy`, `tornado`,
`regex`, `selectolax`, `jiter`, `rpds_py`, `markupsafe`,
`charset_normalizer`, `tomli`.

**Final laptopu macOS değilse** paketi o makinede yeniden üretin:

```bash
# Final laptopunun kendisinde, ağ varken:
make paket
```

Bu mümkün değilse hedef platformu belirterek indirin:

```bash
.venv/bin/python -m pip download -r requirements.txt -d paketler/ \
    --platform win_amd64 --python-version 3.12 --only-binary=:all:
```

> Kural: **paketi, üzerinde koşacağı makinede üretin.** En ucuz sigorta bu.

---

## Doğrulama

Kurulumun doğru olduğunu şu üç komutla teyit edin:

```bash
make test      # tüm testler geçmeli (sayı için `make test` çıktısına bakın)
make lint      # temiz olmalı
make durum     # veritabanı özeti + RAG indeksinin durumu
make eval      # docs/SONUCLAR.md üretilmeli
```

---

## Model seçimi (donanıma göre)

`.env` dosyasındaki `OLLAMA_MODEL` değerini değiştirin; **kod aynı kalır.**

| Donanım | Model | Boyut |
|---|---|---|
| 24 GB+ VRAM | `qwen3.6:27b-q4_K_M` | ~17 GB |
| 24 GB VRAM | `qwen3.5:9b-q4_K_M` | ~6,6 GB |
| **8 GB RAM, GPU yok** | `qwen3.5:4b-q4_K_M` | **~3,4 GB** |
| Düşük bellek | `qwen3.5:2b-q4_K_M` | ~1,9 GB |

Uzak bir sunucudaki Ollama'yı kullanmak için:
```bash
OLLAMA_HOST=http://sunucu-adresi:11434
```

---

## Kurum içi (on-prem) çalıştırma

Sistem tasarım gereği **dış servise bağlanmaz**. `.env.example` içindeki şu
değişkenler kütüphanelerin varsayılan telemetrisini kapatır:

```bash
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
ANONYMIZED_TELEMETRY=False
DO_NOT_TRACK=1
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
```

### Hava boşluğu (air-gap) doğrulaması

Model bir kez indirildikten sonra sistem internetsiz çalışır:

```bash
docker compose up -d
# ağ bağlantısını kesin
ping -c 2 8.8.8.8        # başarısız olmalı
curl http://localhost:8000/saglik   # çalışmaya devam etmeli
```

`docker-compose.yml` içindeki `internal: true` satırı açıldığında, servislerin
dışarıya çıkışı **altyapı düzeyinde** engellenir.

---

## Sorun giderme

| Belirti | Sebep | Çözüm |
|---|---|---|
| `SyntaxError` (`X \| None`) | Python 3.10 altı | Python 3.11+ kurun |
| LLM boş JSON döndürüyor | Düşünme modu bütçeyi yiyor | `ollama` paketi 0.5+ olmalı (`think=False` desteği) |
| `Connection refused :11434` | Ollama çalışmıyor | `ollama serve` |
| Bellek yetersiz / çok yavaş | Model donanıma büyük | `.env`'de `qwen3.5:2b-q4_K_M` |
| Çıkarım aşırı yavaş (dakikalarca/kayıt) | **Aynı anda Streamlit açık** | Aşağıya bakın |
| Toplayıcı 0 sayfa döndürüyor | Seed URL değişmiş | `data/banks.yaml` içindeki `seed_urls` güncelleyin |
| `WebDriverException` / `chromedriver` hatası | Chrome kurulu değil ya da sürücü indirilemedi | Chrome'u kurun; ağ kısıtlıysa `webdriver-manager` yerine Selenium Manager devreye girer, ikisi de erişemiyorsa toplama yapılamaz |
| Bir bankadan hiç kayıt gelmiyor, diğerleri geliyor | O bankanın sitesi yapı değiştirmiş — CSS seçicisi tutmuyor | `src/collector/kaziyicilar/<banka>.py` içindeki seçiciyi güncelleyin; `crawl --banka <kod>` ile tek başına deneyin |
| `robots.txt reddetti` günlüğü | Site otomatik erişimi kapatmış | Beklenen davranış; manuel toplama kullanın |
| Chatbot: «Metin araması şu anda erişilemiyor» | **EVREN'in gömme ucu düşmüş** (`bge-m3-embed`) | Aşağıya bakın — yerel gömmeye geçin |

### EVREN gömme ucu düştüğünde — 28 Ağustos 2026'da yaşandı

Belirti: sayısal sorular çalışıyor, «kampanya koşulları neler?» gibi METİN
soruları «erişilemiyor» diyor. `make saglayici-dogrula` **başarılı** olur —
o, sohbet ucunu sınar; düşen taraf gömme ucudur:

```bash
.venv/bin/python -c "import src.vektor_db as v; print(len(v.gom('deneme')))"
# openai.InternalServerError: 500 — "Cannot connect to host ... bge-m3-embed"
```

Çözüm tek satır: **gömmeyi yerele al.** İndeks zaten depoda (ADR 015) ve
`bge-m3` ile `bge-m3-embed` aynı modeldir (`BAAI/bge-m3`, 1024 boyut):

```bash
ollama pull bge-m3                 # bir kez, ~1,2 GB
GOMME_SAGLAYICI=ollama make run    # ya da .env'e yazın
```

Çıkarım (`make extract`) EVREN'de kalmaya devam eder — düşen yalnız gömme
ucudur. Demo öncesi bu yolu **bir kez deneyin**: model indirilmemişse
komut ağ ister ve salonda ağ olmayabilir.

### 8 GB makinede çıkarım hızı — ölçülmüş uyarı

`make extract` çalışırken **Streamlit'i (`make run`) kapatın.**

9 Ağustos 2026'da 96 kampanyalık koşuda ölçülen fark:

| Durum | Kayıt başına süre | 96 kayıt |
|---|---|---|
| Streamlit açıkken | ~2,5 dakika | **~4 saat** |
| Streamlit kapalıyken | **13,2 saniye** | ~21 dakika |

Sebep model değil, **bellek çakışması**: 8 GB RAM'de 3,4 GB'lık model +
Streamlit + pandas/pyarrow aynı anda durunca sistem takasa (swap) düşüyor
(ölçüm sırasında 1,19 milyon pageout, boş bellek %15).

Bu fark planı doğrudan etkiler. **Toplu çıkarımı arayüz kapalıyken koşturun.**
Yukarıdaki sayılar yerel Ollama yolunundur (`make extract-yerel`); orada
`CIKARIM_ISCI=1` zorunludur. Varsayılan yol EVREN'dir (`make extract`) —
iş bizim makinemizde koşmadığı için bu kısıtların ikisi de geçerli değil:
ölçülen 0,43 sn/kayıt (16 işçi).
