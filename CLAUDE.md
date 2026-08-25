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
| Jenerik toplayıcı | `src/collector/toplayici.py` |
| Hibrit çıkarım | `src/extraction/{kural,llm,uzlastirici}.py` |
| LLM sağlayıcı (EVREN / Ollama) | `src/extraction/saglayici.py` |
| Depolama | `src/depolama.py` |
| Karşılaştırma | `src/comparison/karsilastirma.py` |
| Chatbot + kalkan | `src/rag/chatbot.py` |
| Arayüz / API | `app/` · `src/api/sunucu.py` |

Ayrıntı: [`docs/MIMARI.md`](docs/MIMARI.md) · Durum: [`docs/SPRINT0_RAPORU.md`](docs/SPRINT0_RAPORU.md)

---

## Değiştirmeden önce bilinmesi gerekenler

**`src/schema.py` donmuştur (v1.0.0).** Dört kişi bu şemaya karşı çalışıyor.
Değiştirmek gerekiyorsa: takıma duyur, `docs/kararlar/` altına ADR yaz, sürümü
yükselt. Sessiz değişiklik dördünün işini birden bozar.

**Kanıtsız değer üretilemez.** Her `Alan` kaynağını, güvenini ve hangi katmandan
geldiğini taşır. `Alan(deger=2.05, yontem="belirtilmemis")` `ValueError` fırlatır.
Bu kısıtı gevşetme.

**Sayısal cevaplar yapısal veriden gelir, metin aramasından değil.** Chatbot'taki
sayısal doğrulama kalkanını (`sayisal_dogrulama`) zayıflatma — sistemin en özgün
iddiası bu. Kalkan yanlış pozitif veriyorsa çözüm kalkanı gevşetmek değil,
denetlenecek metni doğru seçmektir (`Cevap.dogrulanacak_metin`).

**Llama ve Gemma türevi model KULLANILMAZ.** Şartname 5.10 doğrudan bunları
hedefliyor. Yalnız Apache 2.0 / MIT (Qwen3.5, Qwen3.6). EVREN'deki `llm-large`
ve `llm-fast` ikisi de Qwen ailesi — yasağa takılmıyor. `vlm`, `guard`, `router`
ve `rerank` uçlarının modeli DOĞRULANMADI; bu senaryoda ihtiyaç da yok, ama
kullanılacaksa önce lisansı teyit et. **EVREN'in jenerik `embed` ucu da bu
sınıfta — gömme için `bge-m3-embed` ya da yerel `BAAI/bge-m3` (MIT) kullan.**
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
make crawl        # kampanya topla
make extract      # çıkarım (kural + LLM) -> SQLite  [EVREN]
make extract-yerel      # aynı çıkarım, yerel Ollama ile (yedek / hava boşluğu)
make saglayici-dogrula  # EVREN bağlantısı + şema kısıtı sınaması
make durum        # kaç kampanya, kaç banka
make run          # Streamlit arayüzü
make test         # testler (691 test)
make eval         # metrikler -> docs/SONUCLAR.md
make lisanslar    # bağımlılık + model lisans raporu
make lisanslar-teyit    # aynı rapor + model lisanslarını HF'ten teyit et (ağ)
make kanit        # veri toplama etiği kanıtları (robots günlüğü + KVKK taraması)
make gorev ad=X   # görev durumu
```

Değişiklikten sonra: **`make test` ve `make lint` yeşil olmalı.**
