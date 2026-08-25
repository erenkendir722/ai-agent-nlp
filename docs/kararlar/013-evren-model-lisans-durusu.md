# ADR 013 — EVREN'de sunulan modeller lisans açısından uygun sayılır

**Tarih:** 25 Ağustos 2026 · **Durum:** kabul edildi · **Sorumlu:** Eren
**İlgili bulgu:** `src/vektor_db.py` gömme ucu · şartname 5.10
**Şema etkisi:** yok

## Bağlam

24 Ağustos'ta lisans duruşumuz şöyle yazılmıştı: EVREN'in yalnız kimliği model
kartından teyit edilmiş uçları kullanılır (`llm-large`, `llm-fast`), kimliği
belirsiz jenerik uçları (`embed`, `rerank`, `router`, `guard`, `vlm`)
kullanılmaz. Gerekçe: jenerik `embed` ucunun arkasında EmbeddingGemma gibi
kısıtlı lisanslı bir model olma ihtimali dışlanamıyordu, şartname 5.10 ise
Gemma türevlerini doğrudan hedefliyor.

25 Ağustos'ta `src/vektor_db.py` (RAG gömme katmanı) depoya girdi ve EVREN'in
gömme ucunu çağırmaya başladı. Bu, yukarıdaki üç belgedeki «kullanılmıyor»
ifadesini yanlış hale getirdi — kod ile jüriye sunulan kanıt çelişir oldu.

## Karar

**İki ayrı karar alındı. İkisi bağımsız olarak yeterlidir.**

### 1. Duruş: EVREN'de sunulan modeller uygun sayılır

EVREN, T.C. Cumhurbaşkanlığı SSB'nin **yarışma için tahsis ettiği** servistir.
Yarışmayı düzenleyen kurumun yarışmacılara açtığı bir modeli kullanmak, o
yarışmanın şartnamesine aykırı sayılamaz. Servisteki uçların tamamı bu kapsamda
kullanılabilir.

Bu, 24 Ağustos'taki «kimliği doğrulanmamış uç kullanılmaz» kuralının yerini
alır. O kural fazla ihtiyatlıydı ve elimizdeki bir kaynağı gereksiz yere
kapatıyordu.

### 2. Buna rağmen: fiilen kullandığımız her modelin lisansı teyitli

Duruşa yaslanmak zorunda kalmıyoruz. Kullandığımız modeller:

| Nerede | Uç | Model | Lisans | Teyit |
|---|---|---|---|---|
| Çıkarım | `llm-large` | `Qwen/Qwen3.5-122B-A10B` | Apache-2.0 | HF API |
| Çıkarım (seçenek) | `llm-fast` | `Qwen/Qwen3.6-35B-A3B` | Apache-2.0 | HF API |
| Yerel yedek | — | `Qwen/Qwen3.5-4B` | Apache-2.0 | HF API |
| **RAG gömme** | **`bge-m3-embed`** | **`BAAI/bge-m3`** | **MIT** | **HF API + boyut** |

Yani jüri «bu modelin lisansı ne?» diye sorarsa cevabımız duruş değil, belge:
`docs/kanit/model-lisanslari.json`.

## Gömme ucu neden `bge-m3-embed`? — lisanstan önce gelen sebep

Tartışma sırasında EVREN'e üç uç birden soruldu ve **ölçüldü** (25 Ağustos):

| Model adı | Sonuç |
|---|---|
| `embedding` | **404 — EVREN'de böyle bir model yok** |
| `embed` (jenerik) | çalışıyor, **2560 boyut** |
| `bge-m3-embed` | çalışıyor, **1024 boyut** |

Üç sonucun da bağlayıcı sonucu var:

1. Kodun eski varsayılanı `embedding` idi — yani **hiç çalışmamıştı.** Her çağrı
   404 dönüyordu, hata yutulduğu için kimse görmedi (aşağıya bakınız).
2. Jenerik `embed` 2560 boyut veriyor; kodun `VECTOR_SIZE` sabiti 1024. O uç
   seçilseydi Qdrant upsert'i reddedecekti. Yani jenerik uç lisanstan bağımsız
   olarak da bu koda uymuyor.
3. `bge-m3-embed` 1024 veriyor — BGE-M3'ün bilinen boyutu tam olarak budur.
   Bu, ada ek olarak **kimlik teyidi** sayılır: 1024 boyutlu çıktı BGE-M3 ile
   tutarlı, EmbeddingGemma (768) ile değil.

Yani gömme ucu seçimi lisans tartışmasının sonucu değil; lisans tartışması
olmasa da tek doğru seçenek `bge-m3-embed` idi.

## Yan bulgu — sessiz yutma neden yasak

`embedding` ucunun 404'ü dört gün fark edilmedi, çünkü `embed_text` hatayı
yakalayıp **sıfır vektörü** dönüyordu ve `vektor_ara` da arama hatasını **boş
liste**ye çeviriyordu. Sonuç: RAG hiç çalışmadığı halde sistem sağlıklı
görünüyordu; kullanıcıya «bu konuda veri setinde bilgi bulamadım» diyordu.

Sıfır vektörü de uydurma bir değerdir. `Alan(deger=..., yontem="belirtilmemis")`
neden `ValueError` fırlatıyorsa, gömme hatası da o yüzden yutulmamalıdır.
İkisi de aynı ilkenin uygulamasıdır: **kanıtsız değer üretilmez.**

Her iki yutma da kaldırıldı. Bağlantı hataları hâlâ zarifçe karşılanıyor, ama
artık hata *metnine* değil *türüne* bakılarak — eski kural Windows'un DNS hata
metnine göre yazılmıştı ve macOS'ta tutmuyordu.

## Sonuçları

- `src/vektor_db.py` — varsayılan gömme modeli `bge-m3-embed`, boyut denetimi eklendi
- `docs/SARTNAME_UYUM.md` · `docs/LISANSLAR.md` · `CLAUDE.md` — «jenerik uç
  kullanılmaz» ifadeleri bu ADR'ye göre güncellendi
- `eval/lisanslar.py` — `BAAI/bge-m3` artık «aday» değil, **kullanılıyor**
- ✅ Qdrant sorunu **ADR 014** ile kapandı: `qdrant.ssyz.org.tr` DNS'te
  çözülmüyordu ve öyle bir servisin tahsis edildiğine dair belge yoktu.
  Harici vektör veritabanı bırakıldı; arama yerel kosinüs benzerliğiyle
  yapılıyor. RAG artık uçtan uca çalışıyor.
