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

### Adımlar

```bash
git clone <depo-adresi>
cd katilim-lens

docker compose up -d
```

İlk çalıştırmada Ollama modeli indirilir (~3,4 GB). Sonrasında:

```bash
docker compose exec ollama ollama pull qwen3.5:4b-q4_K_M   # bir kez
docker compose exec uygulama python -m src.boru_hatti crawl
docker compose exec uygulama python -m src.boru_hatti extract
```

| Servis | Adres |
|---|---|
| Streamlit arayüzü | <http://localhost:8501> |
| REST API (Swagger) | <http://localhost:8000/docs> |

Durdurma: `docker compose down`

---

## Yol 2 — Yerel kurulum

### Gereksinimler

| Bileşen | Sürüm | Not |
|---|---|---|
| Python | **3.11+** | 3.10 altı çalışmaz (birleşim tipi sözdizimi) |
| Ollama | 0.6+ | <https://ollama.com/download> |
| Disk | ~5 GB | model + veri |
| RAM | 8 GB | 4B model için yeterli |

### Adımlar

```bash
# 1) Sanal ortam ve bağımlılıklar
make kur

# 2) Ollama'yı başlat (ayrı bir terminalde)
ollama serve

# 3) Modeli indir (tek seferlik, ~3,4 GB)
ollama pull qwen3.5:4b-q4_K_M

# 4) Ortam yapılandırması
cp .env.example .env

# 5) Veri topla (~5 dk, nezaket gecikmesi nedeniyle)
make crawl

# 6) Çıkarım yap (kayıt başına ~10 sn)
make extract

# 7) Arayüzü aç
make run
```

### Ağ olmadan deneme

Toplama adımını atlayıp tohum veriyle çalışabilirsiniz:

```bash
make seed && make run
```

---

## Doğrulama

Kurulumun doğru olduğunu şu üç komutla teyit edin:

```bash
make test      # 92 test geçmeli
make durum     # veritabanı özeti
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
| `robots.txt reddetti` günlüğü | Site otomatik erişimi kapatmış | Beklenen davranış; manuel toplama kullanın |

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

Sprint 1'de 300+ kampanya işlenecek: temiz koşuda ~65 dakika, çakışmalı koşuda
~12 saat. Bu fark planı doğrudan etkiler. Toplu çıkarımı arayüz kapalıyken
veya 3090 üzerinde koşturun.
