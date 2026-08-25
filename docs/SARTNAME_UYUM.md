# Şartname Uyum Takibi

**Görev:** E-12 · **Sorumlu:** Eren · **Son denetim:** 18 Ağustos 2026 (E-02 Docker · arayüz K1–K7)
**Kaynak:** `2026_TYDA_SARTNAME_Ikinci_Senaryo_TR_1_1IAJb.pdf` (20 sayfa, 2. Senaryo)

Jüri bu şartnameye göre puanlıyor. Bu dosya her maddeyi tek tek satır olarak
tutar; unutulan bir gereklilik yüzünden puan kaybetmenin panzehiri budur.

**Durum işaretleri:** ✅ tamam · 🟠 kısmi · ❌ eksik · ⬜ sırası gelmedi

> ⚠️ **Bu dosya bayatlarsa zararlıdır.** 15 Ağustos denetiminde "kritik" listesinin
> 6 maddesinden 4'ü aslında çözülmüştü; pano ise hâlâ ❌ gösteriyordu. Yanlış
> alarm, takımı çözülmüş işe koşturur. Değişiklik yapan burayı da günceller.

---

## 🚨 ÖNCE BUNLAR — açık ve riskli

| # | Sorun | Neden kritik | Kim |
|---|---|---|---|
| 1 | **10 faal bankanın 2'sinde veri yok** | Madde 5.1: veri seti BDDK listesindeki kuruluşların **tümünü** içermeli | Görkem (G-03, G-04) |
| 2 | **Demo videosu yok (5 dk *ve* 1 dk)** | Madde 6 ve madde 10 ayrı ayrı zorunlu tutuyor | Esra (ES-17, ES-18) |
| 3 | **Sunum materyali yok (PDF + PPTX)** | Madde 6 ikisini birden istiyor; `sunum/` klasörü boş | Esra (ES-13) |
| 4 | ~~Docker hiç çalıştırılmadı~~ → **18 Ağu'da koşuldu, çalışıyor** | %20'lik On-Prem kriterinin tek somut kanıtı — artık kanıt var, `docs/KURULUM.md` «Doğrulanmış çalıştırma» | Eren (E-02) |
| 5 | **Teslim tarihi belirsiz — aşağıya bak** | Şartname kendi içinde çelişiyor | Eren — **sor** |

### ✅ 15 Ağustos'ta kapandığı doğrulanan maddeler

Depo durumu GitHub API'sinden teyit edildi (`api.github.com/repos/erenkendir722/ai-agent-nlp`):

| Eski uyarı | Gerçek durum |
|---|---|
| ~~Depo private~~ | **Public** (`"private": false`) — madde 8 karşılandı |
| ~~`BilisimVadisi2026` etiketi yok~~ | **Var** (`bilisimvadisi2026`; GitHub topic'leri küçük harfe indirir) |
| ~~"Türkiye Açık Kaynak Platformu" etiketi yok~~ | **Var** (`turkiye-acik-kaynak-platformu`) |
| ~~Veri seti indirme bağlantısı yok~~ | **Var** — 96 ham kayıt (`data/raw/**/*.json`) depoda izleniyor, README'de «Veri seti» bölümünde belgelendi |

> Kalan tek repo eksiği: **depo açıklaması "SVARTAL"**. Madde 9 *"projeye ait
> tanımlamasının yapılması"* diyor; takım adı proje tanımı değildir.

### ⚠️ Şartnamede iki iç tutarsızlık var

**1. Teslim tarihi.** Madde 9 şöyle diyor:

> *"Yarışmamız **12.07.2026** tarihinde sona erecektir. Bu nedenle … **12.07.2026 tarihi saat 23:59'a kadar** … GitHub'a 'BilisimVadisi2026' etiketi ile yüklemeleri gerekmektedir."*

Ama madde 3'teki takvim tablosu **"Yarışma Çevrimiçi Süreci: 27 Temmuz – 26 Ağustos"** diyor.
Bu iki ifade bağdaşmıyor: 12 Temmuz, çevrimiçi sürecin *başlangıcından* iki hafta önce.

**2. Başvuru tarihi.** Madde 3 *"Son Başvuru Tarihi: 17 Temmuz"*, madde 8 ise
*"Başvurular, 12 Temmuz 2026 tarihine kadar"* diyor. Aynı 12 Temmuz tarihi.

**Okumamız:** Madde 9'daki 12.07.2026, başvuru tarihinden kopyalanmış eski bir
metin. Bağlayıcı takvim madde 3'teki tablodur (26 Ağustos) — 12 Temmuz gerçek
teslim tarihi olsaydı yarışma zaten bir ay önce bitmiş olurdu.

**✅ 18 Ağustos'ta büyük ölçüde çözüldü.** Takım fiziki finalde **27 Ağustos**'ta
Bilişim Vadisi Kocaeli Kampüsü'nde olacak (madde 10'un «son 24 saat fiziki»
maddesi). Bu, madde 9'daki 12.07.2026'nın **bayat metin olduğunu doğruluyor**:
fiziki final 27 Ağustos'taysa, teslim 12 Temmuz olamaz.

**Bağlayıcı takvim madde 3'teki tablodur.** Kesinleşen zaman çizelgesi:

| Tarih | Ne |
|---|---|
| **25 Ağu 20:00** | TESLİM — her şey GitHub'da, `v1.0` etiketi (E-18) |
| 26 Ağu | Jüri soru-cevap provası (E-19) · çevrimiçi sürecin son günü |
| **27 Ağu** | **FİZİKİ SUNUM** — Bilişim Vadisi Kocaeli |

⚠️ **Yine de resmî teyit alınmadı.** Madde 13'teki kanaldan
(`iletisim@teknofest.org`) saatin ve yerin yazılı teyidi hâlâ istenmeli —
özellikle **sunum saati** ve **salonda hangi donanımın bulunacağı**
(projeksiyon bağlantısı, internet, priz). Profil C testi (E-08) bu cevaba göre
planlanmalı.

---

## Madde 5 — Temel Beklentiler (teknik)

| Madde | Gereklilik | Durum | Kanıt / not | Kim |
|---|---|---|---|---|
| 5.1 | Veri BDDK listesindeki katılım bankalarının **tümünü** içermeli | 🟠 | `data/banks.yaml` 10 faal banka listeliyor ama **8'inde kampanya var**; T.O.M. ve Adil'de 0 | Görkem |
| 5.1 | Python tabanlı toplama / web scraping / **manuel** toplama serbest | ✅ | `src/collector/toplayici.py` · manuel yedek şartnameye uygun. **24 Ağu (G-14): toplama etiğinin kanıtı yazıldı** — `docs/kanit/VERI_TOPLAMA_ETIGI.md`: robots.txt kontrol günlüğü (12 alan adı, 2'si çekilmiyor), ağa gerçekten gönderilen User-Agent başlığı, BDDK ekran görüntüsü, KVKK taraması. Yenile: `make kanit` | Görkem |
| 5.2 | *"%2,05 kâr payı oranı"* yorumlanmalı | ✅ | `src/extraction/kural.py` · `tests/test_normalizasyon.py` · `tests/test_kural.py` | Samet |
| **11** | **Şartnamenin kendi örnek tablosu (madde 11, A/B/C Bankası)** | ✅ | `tests/test_kural.py::TestSartnameMadde11` — 15 Ağu: 12 iddiadan 4'ü başarısızdı, düzeltildi, hibrit hat **11/11** | Eren |
| 5.2 | *"avantajlı kâr payı fırsatı"* yorumlanmalı | 🟠 | Sayı uydurmama davranışı test edilecek | Samet (S-08) |
| 5.2 | *"özel oranlı finansman"* yorumlanmalı | 🟠 | S-08 | Samet |
| 5.2 | *"düşük maliyetli finansman"* yorumlanmalı | 🟠 | S-08 | Samet |
| 5.3 | Kâr payı oranı çıkarımı | 🟠 | Doluluk %28 — hedef ≥%50 | Samet (S-02) |
| 5.3 | Finansman tutarı · vade · taksit sayısı · tahsis ücreti · masraf bilgisi | ✅ | `src/schema.py` alanları mevcut, doluluk `docs/SONUCLAR.md`'de | Samet |
| 5.3 | Kampanya türü · ödül miktarı · indirim oranı · alışveriş puanı · kampanya süresi · koşulları | ✅ | Şemada tam karşılığı var | Samet |
| 5.3 | Hedef kitle bilgileri (yeni/mevcut/maaş/segment) | ✅ | `HedefKitle` enum'u dördünü de kapsıyor | Samet |
| 5.4 | 8 kampanya türü şartnamedeki tabloyla birebir | ✅ | `KampanyaTuru` — `docs/kararlar/002-kampanya-turleri.md` | Samet |
| 5.5 | 5 resmî kavramın doğru yorumlanması | 🟠 | Terim sözlüğü henüz yok | Görkem (G-09) |
| 5.6 | `%2,05` / `% 2.05` / `2.05 %` aynı değer | ✅ | `oran_ayristir` · doctest'li | Samet |
| 5.6 | `500 TL` / `500₺` / `500 Türk Lirası` aynı değer | ✅ | `para_ayristir` | Samet |
| 5.7 | Ürünlerin karşılaştırılabilir hale getirilmesi | ✅ | `src/comparison/karsilastirma.py` | Eren |
| 5.7 | 5 karşılaştırma kriteri (en düşük kâr payı, en yüksek ödül, en uzun vade, en düşük masraf, en avantajlı) | ✅ | Beşi de kodda | Eren |
| 5.8 | Veri ön işleme adımları | ✅ | `src/preprocessing/normalizasyon.py` | Samet |
| 5.9 | Kurum sistemlerine entegre edilebilir mimari | ✅ | **25 Ağu (E-10):** [`docs/KURUMSAL_ENTEGRASYON.md`](KURUMSAL_ENTEGRASYON.md) — yerleşim topolojisi, LDAP/AD kimliğinin uygulama DIŞINDA çözülmesi, kurumsal vekil ve TLS araya girme (kök sertifika tuzağı), veri ambarına gecelik besleme (üç tablo + kod parmak izi), denetim izi (kanıt zinciri zaten veri modelinde), ölçeklenebilirlik değerlendirmesi. Neyin bugün çalıştığı ve neyin kurum tarafında yapılacağı ayrı ayrı işaretli. | Eren (E-10) |
| 5.9 | Kurum içi sunucularda çalışabilirlik | ✅ | **18 Ağu: `docker compose up -d` koşuldu.** 3 konteyner healthy · Streamlit :8501 ve API :8000/docs 200 · LLM konteyner içinde çıkarım yaptı (19,1 sn) · `exec` ile boru hattı koştu. Kanıt: `docs/KURULUM.md` | Eren (E-02) |
| 5.9 | Veri güvenliği · müşteri verisi kurum dışına çıkmamalı | ✅ | `tests/test_sizinti_yok.py` (6 test). **24 Ağu — kapsam netleşti:** kural, normalizasyon, karşılaştırma ve chatbot katmanları hâlâ tamamen kapalı devre; testler bunu ölçmeye devam ediyor. Çıkarım LLM'i T.C. Cumhurbaşkanlığı SSB tahsisli **EVREN** servisine çıkar (`evren-llmapi.ssyz.org.tr`) — ticari bulut değil, yarışma altyapısı. İzinli tek dış uç odur ve `test_llm_ucu_yalnizca_yerel_veya_evren` bunu sözleşme hâline getirir. **24 Ağu (G-14):** korpusun kendisi de tarandı — 1024 ham kayıtta kimliği belirli gerçek kişiye ait veri **yok** (`docs/kanit/KVKK_TARAMASI.md`, `make kanit-kvkk`). | Eren · Görkem |
| 5.9 | Dış servislere bağımlı olmadan çalışabilme | ✅ | **Bağımlılık yok: EVREN düşerse `make extract-yerel` ile yerel Ollama'ya tek komutla dönülür** (`LLM_SAGLAYICI=ollama`), kod yolu aynıdır. **18 Ağu: hava boşluğu ölçüldü.** `ic-ag` ağı `internal: true`; ollama yalnız orada → 8.8.8.8/1.1.1.1/DNS **anında engellendi** (rota yok). Bu haldeyken LLM çıkarımı 24,4 sn'de koştu, chatbot kaynak gösterdi. Sınır: uygulama/api port yayını için `sunum` ağında da, oradan çıkış var — kanıtı `tests/test_sizinti_yok.py`. Ayrıntı: `docs/KURULUM.md` | Eren (E-07) |
| 5.10 | Tüm kodlar açık kaynak teknolojilerle | ✅ | `docs/LISANSLAR.md` — **24 Ağu (G-13)**: 85 kurulu paketin 79'u `requirements.txt` kapanışında, kısıtlı/şüpheli lisans **0**. Rapor artık proje bağımlılığı ile ortamda kalmış paketi ayırıyor (`openai` kurulu ama kullanılmıyor — EVREN'e düz `httpx` ile gidilir) | Görkem |
| 5.10 | Lisans problemi çıkarabilecek çözüm kullanılmamalı | ✅ | Llama / Gemma türevi **yok**, yalnız Apache-2.0 / MIT. Çıkarım modeli **`Qwen/Qwen3.5-122B-A10B`** (EVREN `llm-large`), yerel yedek `qwen3.5:4b-q4_K_M`. **24 Ağu — lisans teyit edildi, iki bağımsız kaynak:** (1) EVREN model kartı HF deposunu `Qwen/Qwen3.5-122B-A10B` olarak veriyor (122B toplam / 10B aktif, MoE, BF16, 262.144 token); (2) o depo Hugging Face'te **`apache-2.0`** etiketli. Modelin kendi beyanına dayanılmıyor. **24 Ağu — teyit otomatikleşti (G-13):** `make lisanslar-teyit` kullandığımız dört modelin lisansını HF API'sinden çeker, beklenenle karşılaştırır, tutmazsa çıkış kodu 1 verir. Ham yanıt: `docs/kanit/model-lisanslari.json` (`llm-large`, `llm-fast`, yerel yedek → Apache-2.0; S-09 adayı `BAAI/bge-m3` → MIT). **25 Ağu — duruş netleştirildi (ADR 013):** EVREN, yarışmayı düzenleyen SSB'nin tahsis ettiği servistir; sunduğu modeller lisans açısından uygun sayılır. Buna **yaslanmak zorunda değiliz**: fiilen kullandığımız dört modelin dördü de teyitli (üç Qwen → Apache-2.0, RAG gömme `bge-m3-embed` → `BAAI/bge-m3`, **MIT**). Gömme ucu ölçümle seçildi — `bge-m3-embed` 1024 boyut veriyor, bu BGE-M3'ün bilinen boyutu (kimlik teyidi); jenerik `embed` ucu 2560 veriyor ve zaten kodumuza uymuyor. Kalan uçlar (`rerank`, `router`, `guard`, `vlm`) bu senaryoda kullanılmıyor — ihtiyaç yok. | Görkem |
| 5.10 | Model ölçeklenebilir konumlandırılmalı | 🟡 | **24 Ağu ölçüldü — yerel 4B ↔ servis 122B, aynı kod yolu.** Önceden kırpılan 20 kayıtta doluluk %33 → %41 (15 iyileşti, 5 aynı, **0 kötüleşti**). Süre: 13 sn/kayıt → 0,43 sn/kayıt (16 işçi), 590 kayıt ~2 sa 8 dk → ~4,5 dk. Sağlayıcı `LLM_SAGLAYICI` ile değişir: `src/extraction/saglayici.py`. 9B/27B satırları eksik. | Samet (S-15) |

---

## Madde 6 — Tespit Edilmesi Gerekenler (teslim edilecekler)

| Gereklilik | Durum | Kanıt / not | Kim |
|---|---|---|---|
| Çalışan proje kodu, tüm kaynak kodlar | ✅ | Depo — **ama private (bkz. E-01)** | Eren |
| Kurulum adımları net belirtilmiş | ✅ | `docs/KURULUM.md` — E-02 sonrası gerçek çıktıyla güncellenecek | Eren |
| **Demo videosu — maks. 5 dakika** | ❌ | | Esra (ES-17) |
| Videoda: kullanıcı arayüzü | ❌ | | Esra |
| Videoda: dashboard | ❌ | | Esra |
| Videoda: chatbot | ❌ | | Esra |
| Videoda: metin girdisi verilmesi | ❌ | | Esra |
| Videoda: yapılandırılmış çıktı | ❌ | | Esra |
| Videoda: karşılaştırma sonuçları | ❌ | | Esra |
| **Sunum materyali — PDF *ve* PPTX** | ❌ | | Esra (ES-13) |

### Proje dokümantasyonu — 10 başlık (madde 6)

| # | Başlık | Durum | Dosya | Kim |
|---|---|---|---|---|
| 1 | Sistem mimarisi ve veri akışı | ✅ | `docs/MIMARI.md` | Eren (E-15) |
| 2 | Kullanılan NLP yaklaşımı | ✅ | [`docs/MIMARI.md`](MIMARI.md) bölüm 3 — beş katman (normalizasyon · kural · LLM · uzlaştırma · RAG) | Eren (S-16) |
| 3 | Kullanılan veri seti ve açıklaması | 🟠 | `docs/VERI_METODOLOJISI.md` — gerçek sayılarla güncellenecek | Görkem (G-15) |
| 4 | Veri ön işleme adımları | 🟠 | `docs/VERI_METODOLOJISI.md` | Görkem (G-15) |
| 5 | Model veya kural yapısının açıklaması | ✅ | [`docs/MODEL_VE_KURAL_YAPISI.md`](MODEL_VE_KURAL_YAPISI.md) | Eren (S-16) |
| 6 | Benzer ürünler nasıl karşılaştırılıyor | ✅ | [`docs/KARSILASTIRMA_YONTEMI.md`](KARSILASTIRMA_YONTEMI.md) | Eren (E-15) |
| 7 | Adım adım çalıştırma talimatları | ✅ | `docs/KURULUM.md` | Eren (E-15) |
| 8 | Karşılaşılan problemler ve çözümler | 🟠 | `docs/SPRINT0_RAPORU.md` böl. 5 + `docs/kararlar/` — derlenecek | Eren (E-16) |
| 9 | Model çıktılarının örnekleri | ❌ | `docs/CIKTI_ORNEKLERI.md` | Esra (ES-15) |
| 10 | Performans değerlendirme yöntemleri | ✅ | [`docs/DEGERLENDIRME_YONTEMI.md`](DEGERLENDIRME_YONTEMI.md) — yöntem; sayılar [`SONUCLAR.md`](SONUCLAR.md)'de | Eren (S-16) |

---

## Madde 7 — Değerlendirme Kriterleri (%100)

| Ağırlık | Kriter | Bizdeki dayanak | Risk |
|---|---|---|---|
| **%30** | Model Başarısı ve Anlamlandırma | Altın set + `make eval` + ablasyon | 🔴 Altın set 16 Ağu'da bitmezse ölçüm yok |
| **%20** | Fonksiyonellik ve Senaryo Kapsamı | Uçtan uca boru hattı, 3 ekran, API | 🟠 96/300 kampanya |
| **%20** | Teknik İmplementasyon ve Mimari | Donmuş şema, hibrit çıkarım, modüler yapı | ✅ |
| **%20** | On-Prem Uygulanabilirlik | Docker (**18 Ağu'da koşuldu**), yerel LLM yolu, hava boşluğu ölçümü, sızıntı testleri, **[`KURUMSAL_ENTEGRASYON.md`](KURUMSAL_ENTEGRASYON.md)** (LDAP/AD · vekil · ambar besleme · denetim izi) | ✅ Bu satır 18 Ağu'dan beri bayattı — Docker koşulmuştu, tabloya yansımamıştı |
| **%10** | Yenilikçilik ve Yaratıcılık | Kanıt zinciri, sayısal doğrulama kalkanı, hava boşluğu | 🟠 Dokümantasyon netliği de bu kalemde |

> Madde 7 «Eksik veya farklı yazılmış bilgiler karşısında doğru sonuç üretebilmesi»
> maddesini **doğrudan** S-07 dayanıklılık seti ölçüyor.

---

## Madde 8 — Katılım Şartları

| Gereklilik | Durum | Not | Kim |
|---|---|---|---|
| Kodlar/veri kümeleri GitHub'da **açık kaynak** paylaşılmalı | ✅ | Depo **public** — 15 Ağu'da API ile teyit edildi | Eren |
| Açık kaynak lisans (Apache/MIT/GNU) | ✅ | `LICENSE` — Apache 2.0 | Eren |
| Yarışma bitişinde Apache 2.0 ile Türkiye Açık Kaynak Platformu hesabında paylaşım kabulü | ✅ | Apache 2.0 seçildi | Eren |
| Sunumda **tüm üyelerin görev tanımları** olmalı | ⬜ | Slayt köşesinde ad + rol | Esra (ES-13) |
| Ücretli yazılım bağımlılığı **yok** | ✅ | `docs/LISANSLAR.md` · yerel Ollama, ücretli API yok | Görkem |
| Üçüncü taraftan hizmet/ürün satın alınmamış | ✅ | Dış servis çağrısı yok — `tests/test_sizinti_yok.py` | Eren |
| Proje yarışma döneminde geliştirilmiş olmalı | ✅ | Commit geçmişi 7 Ağustos'ta başlıyor | Eren |
| Dokümantasyon özgün (Turnitin) | ✅ | Tüm doküman takım tarafından yazıldı | Herkes |
| Takım tanıtım sunumu KYS'ye yüklenmeli | ⬜ | Başvuru aşaması | Eren |

---

## Madde 9 — Proje Bilgileri Sunumları

| Gereklilik | Durum | Not | Kim |
|---|---|---|---|
| GitHub'da **`BilisimVadisi2026`** etiketi | ✅ | `bilisimvadisi2026` topic'i mevcut | Eren |
| **"Türkiye Açık Kaynak Platformu"** etiketlenmesi | ✅ | `turkiye-acik-kaynak-platformu` topic'i mevcut | Eren |
| Ekip adı repo'da belirtilmiş | 🟠 | README: "Takım SVARTAL" ✅ — ama **repo açıklaması yalnız "SVARTAL"**; madde 9 proje tanımı istiyor | Eren (E-01) |
| (1) Bağımlılıkların **eksiksiz** listesi | ✅ | `requirements.txt` + `docs/LISANSLAR.md` | Eren |
| (2) Çalıştırma adımlarının tamamı | ✅ | `docs/KURULUM.md` + README «Veri seti» | Eren |
| (3) Veri setinin **herkese açık indirme bağlantısı** | ✅ | 96 ham kayıt `data/raw/**/*.json` olarak depoda; README'de belgelendi. Taze klonda `make extract` ağsız koşar | Eren |
| **En az haftalık** güncelleme | ✅ | 7, 9, 10, 12, 14, 15 Ağustos commit'leri | Eren (E-03) |
| Sürüm etiketleri | ❌ | Depoda hiç git tag yok (şartname zorunlu tutmuyor, izlenebilirlik için istiyoruz) | Eren (E-03) |

---

## Madde 10 — Yarışma Sunumları

| Gereklilik | Durum | Not | Kim |
|---|---|---|---|
| Son 24 saat **fiziki** — Bilişim Vadisi **Kocaeli** Kampüsü | ⬜ | Çanta listesi hazırlanacak | Eren (E-13) |
| Sunum **4 dakika** | 🟠 | Görev dağılımı `GOREVLER.md`'de hazır | Esra (ES-13) |
| Demo videosu **1 dakika** | ❌ | 5 dakikalıktan kesilecek | Esra (ES-18) |
| Sunumda canlı demo gösterimi **zorunlu** | ⬜ | Prova edilecek | Esra (ES-12) |
| Tüm üyeler birlikte sunacak | ⬜ | Dağılım yapıldı | Herkes |
| **Sunum GitHub hesabına da yüklenmeli** | ❌ | `sunum/` klasörüne PDF+PPTX konacak | Esra (ES-13) |

> ⚠️ Madde 6 **5 dakikalık**, madde 10 **1 dakikalık** video istiyor.
> **İkisi de ayrı ayrı teslim edilecek** — biri diğerinin yerine geçmez.

---

## Madde 11–16 — Puanlama, ödül, iletişim, kurallar

| Madde | Gereklilik | Durum | Not |
|---|---|---|---|
| 11 | 100'lük sistem | ✅ | Bilgi amaçlı |
| 13 | Takımdan **en az 1 kişi** yarışma e-posta grubuna üye olmalı | ⬜ | **Kim üye? Teyit edilmeli** — duyuru kaçırmak takımın sorumluluğunda |
| 13 | Başvuru sistemindeki iletişim bilgileri güncel | ⬜ | Eren teyit etsin |
| 14 | TEKNOFEST Genel Yarışma Kuralları geçerli | ⬜ | Çelişki halinde genel kurallar esas |
| 15 | Etik kurallar · intihal yasağı | ✅ | Tüm kod ve doküman özgün |
| 15.1 | Sistem Türkçe konuşan tüm bireyler için **adil ve yanlılıktan arındırılmış** olmalı | 🟠 | Banka bazlı kapsam dengesizliği yanlılık üretebilir — G-08 bunu ölçüyor |
| 16 | Sorumluluk beyanı | ⬜ | Teslimde imzalanacak |

---

## Denetim günlüğü

| Tarih | Denetleyen | Bulgu |
|---|---|---|
| 12 Ağu | Eren | İlk tam tarama. Depo private, 2 etiket eksik, veri seti bağlantısı yok, 2 bankada veri yok, madde 9'da tarih çelişkisi bulundu. |
| 15 Ağu | Eren | **Panonun kendisi bayattı:** depo public'e alınmış, iki etiket de eklenmiş, veri seti (96 ham kayıt) zaten depodaydı — pano üçüne de ❌ diyordu. Düzeltildi. |
| 15 Ağu | Eren | **Şartname madde 11'in kendi örneği koşuldu, 12 iddiadan 4'ü başarısızdı.** (1) «dosya masrafı **alınmamaktadır**» cümlesinden 50.000 TL tahsis ücreti çıkarılıyordu — `-mAktAdır` olumsuzlama kipi sözlükte yoktu; (2) aynı kayıtta `masrafsiz_mi=True` ile çelişiyordu; (3) «5.000 TL değerinde alışveriş çeki» finansman tutarı sanılıyordu; (4) masraftan hiç söz etmeyen metinden `masrafsiz_mi=True` uyduruluyordu. Dördü de düzeltildi ve `tests/test_kural.py`'de sabitlendi. |
| 15 Ağu | Eren | **Veritabanı bozuktu.** 12 Ağu'daki yarım kalan çıkarım koşusu iyi kayıtların üstüne yazmış; alan doluluğu %25,7'den %13,7'ye, `kampanya_turu` %99'dan %20,8'e düşmüştü. `docs/SONUCLAR.md` ise 9 Ağu'daki iyi koşudan kalmıştı — yayımlanan sayılar yeniden üretilemiyordu. Çıkarım yeniden koşuldu. |
