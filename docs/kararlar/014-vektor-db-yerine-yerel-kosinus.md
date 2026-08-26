# ADR 014 — Harici vektör veritabanı yok: gömme + yerel kosinüs

**Tarih:** 25 Ağustos 2026 · **Durum:** kabul edildi · **Sorumlu:** Eren
**İlgili görev:** S-09 (gömme boru hattı + kosinüs benzerlik RAG)
**Şema etkisi:** yok · **Önceki karar:** [ADR 013](013-evren-model-lisans-durusu.md)

## Bağlam

25 Ağustos'ta RAG katmanı (`src/vektor_db.py`) Qdrant istemcisiyle yazıldı ve
`QDRANT_URL=https://qdrant.ssyz.org.tr` adresine bağlanmayı denedi. Kod çalışır
görünüyordu; koşul soruları «bu konuda veri setinde bilgi bulamadım» diye
cevaplanıyordu.

Denetlendiğinde üç ayrı sorunun üst üste bindiği görüldü:

1. **`qdrant.ssyz.org.tr` DNS'te çözülmüyor.** EVREN'in LLM ucu
   (`evren-llmapi.ssyz.org.tr`) çözülüyor, Qdrant sunucusu yok. Depoda böyle bir
   servisin bize tahsis edildiğine dair tek satır belge de yok; `.env.example`
   satırı bir varsayımdı. API anahtarı da hiç verilmemişti.
2. **Gömme modeli adı yanlıştı** — `embedding` diye bir uç EVREN'de yok, her
   çağrı 404 dönüyordu (bkz. ADR 013).
3. **İkisi de sessizdi.** `embed_text` hatayı yakalayıp sıfır vektörü,
   `vektor_ara` boş liste dönüyordu. Sistem sağlıklı görünüp yanlış cevap
   veriyordu.

Ayrıca proje planı Qdrant altyapısını zaten bütçe dışı ilan etmiş:

> Bu süreyle şunlar **yapılamaz**: … PostgreSQL + Qdrant altyapısı, mikroservis
> mimarisi.

Ve S-09'un tanımı hiç Qdrant demiyor: *«Gömme boru hattı + **kosinüs benzerlik**
RAG»*, bitti ölçütü *«`src/rag/` içinde gömme + kosinüs arama var»*.

## Karar

**Harici vektör veritabanı kullanılmıyor.** Paragraflar EVREN `bge-m3-embed`
ile gömülüyor, vektörler yerel bir `.npz` dosyasına yazılıyor, arama numpy ile
tek nokta çarpımı olarak yapılıyor.

```
make vektor        # indeksi kurar (~70 sn, 15.151 paragraf)
make durum         # indeksin var olup olmadığını da gösterir
```

Vektörler kurulum sırasında L2 normalize edildiği için kosinüs benzerliği düz
nokta çarpımına iniyor: `skorlar = dizey @ sorgu`.

### Neden sunucu gerekmiyor

| | ölçülen |
|---|---|
| Paragraf | 15.151 |
| Vektör boyutu | 1024 (`bge-m3-embed`) |
| İndeks dosyası | 36 MB (sıkıştırılmış `.npz`) |
| İndeks kurma | 69 sn (64'lük yığınlar) |
| Arama | milisaniyeler — 15k × 1024 tek nokta çarpımı |

Bu ölçekte Qdrant hiçbir şey kazandırmıyor. Kaybettirdiği ise somut: var
olmayan bir sunucuya bağımlılık, demoda ağ riski, kurulacak bir servis daha.

**Hava boşluğu demosu için de doğru karar bu** — CLAUDE.md'nin yerel yedek yolu
(`LLM_SAGLAYICI=ollama`) sunucusuz çalışmak üzere kurgulanmış; RAG'ın buna
aykırı olması tutarsızlık olurdu.

## Sonuçları

- `src/vektor_db.py` yeniden yazıldı — Qdrant istemcisi yok, numpy var
- `qdrant-client` bağımlılığı `requirements.txt`'ten kaldırıldı
- `make vektor` eklendi; `make durum` indeks durumunu da basıyor
- `tests/test_vektor_db.py` — 14 test, **ağ istemiyor** (gömme sahteleniyor)
- `data/vektor_indeksi.npz` `.gitignore`'a girdi (36 MB, türetilmiş)
  — **26 Ağu'da geri alındı:** türetilmiş değilmiş, ağsız kurulamıyor ([ADR 015](015-rag-indeksi-depoda.md))
- Chatbot indeks yokluğunu bağlantı hatasından **ayrı** karşılıyor: «`make
  vektor` ile kurulur» diyor, çökmüyor

### Açık kalan

> ✅ **Bu madde [ADR 015](015-rag-indeksi-depoda.md) ile kapandı (26 Ağu):**
> indeks depoya alındı. Aşağıdaki uyarı kaydın bütünlüğü için duruyor.

⚠️ **Çevrimdışı paket (E-14) indeks dosyasını elle içermeli.** İndeks depoda
durmuyor ve kurulması EVREN'e bağlı; hava boşluğu demosunda ağ olmayacağı için
`data/vektor_indeksi.npz` pakete konmazsa koşul soruları cevapsız kalır.

⚠️ **Sorgu gömmesi hâlâ EVREN'e gidiyor.** İndeks yerelde ama sorunun vektörü
çalışma anında üretiliyor. Tam hava boşluğu için yerel `BAAI/bge-m3` (MIT)
gerekir — bu senaryoda kapsam dışı, ama demoda ağ yoksa chatbot sayısal
sorulara cevap vermeye devam eder, yalnız koşul soruları «erişilemiyor» der.
