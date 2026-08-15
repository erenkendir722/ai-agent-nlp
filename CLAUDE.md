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
hedefliyor. Yalnız Apache 2.0 / MIT (Qwen3.5, Qwen3.6). Yeni bağımlılık
eklendiğinde `make lisanslar` çalıştır.

**`make extract` koşarken Streamlit'i kapat.** 8 GB makinede aynı anda açık
olunca kayıt başına 13 saniye yerine 2,5 dakika sürer (bellek takası).

---

## Komutlar

```bash
make kur          # kurulum
make crawl        # kampanya topla
make extract      # çıkarım (kural + LLM) -> SQLite
make durum        # kaç kampanya, kaç banka
make run          # Streamlit arayüzü
make test         # testler (296 test)
make eval         # metrikler -> docs/SONUCLAR.md
make lisanslar    # lisans raporu
make gorev ad=X   # görev durumu
```

Değişiklikten sonra: **`make test` ve `make lint` yeşil olmalı.**
