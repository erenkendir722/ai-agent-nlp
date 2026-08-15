# Şartname Uyum Takibi

**Görev:** E-12 · **Sorumlu:** Eren · **Son denetim:** 15 Ağustos 2026
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
| 4 | **Docker hiç çalıştırılmadı** | %20'lik On-Prem kriterinin tek somut kanıtı | Eren (E-02) |
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

**Yine de bu bir varsayım ve teslim tarihi üzerine varsayım yapılmaz.**
Madde 13'teki resmî kanaldan (`iletisim@teknofest.org` ve yarışma e-posta grubu)
**bugün yazılı olarak sorulmalı**, cevap bu dosyaya eklenmeli.
Planımız 25 Ağustos hedefiyle devam ediyor; erken bitirmek her iki okumada da güvenli.

---

## Madde 5 — Temel Beklentiler (teknik)

| Madde | Gereklilik | Durum | Kanıt / not | Kim |
|---|---|---|---|---|
| 5.1 | Veri BDDK listesindeki katılım bankalarının **tümünü** içermeli | 🟠 | `data/banks.yaml` 10 faal banka listeliyor ama **8'inde kampanya var**; T.O.M. ve Adil'de 0 | Görkem |
| 5.1 | Python tabanlı toplama / web scraping / **manuel** toplama serbest | ✅ | `src/collector/toplayici.py` · manuel yedek şartnameye uygun | Görkem |
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
| 5.9 | Kurum içi sunucularda çalışabilirlik | 🟠 | `Dockerfile` yazıldı, **hiç çalıştırılmadı** | Eren (E-02) |
| 5.9 | Veri güvenliği · müşteri verisi kurum dışına çıkmamalı | ✅ | `tests/test_sizinti_yok.py` (6 test) | Eren |
| 5.9 | Dış servislere bağımlı olmadan çalışabilme | 🟠 | Yerel Ollama; hava boşluğu testi yapılmadı | Eren (E-07) |
| 5.10 | Tüm kodlar açık kaynak teknolojilerle | ✅ | `docs/LISANSLAR.md` — 72 paket temiz | Görkem |
| 5.10 | Lisans problemi çıkarabilecek çözüm kullanılmamalı | ✅ | Llama / Gemma türevi **yok**, yalnız Apache-2.0 / MIT | Görkem |
| 5.10 | Model ölçeklenebilir konumlandırılmalı | ⬜ | 4B/9B/27B ölçüm tablosu | Samet (S-15) |

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
| 2 | Kullanılan NLP yaklaşımı | 🟠 | `docs/MIMARI.md` bölüm 3 — genişletilecek | Samet (S-16) |
| 3 | Kullanılan veri seti ve açıklaması | 🟠 | `docs/VERI_METODOLOJISI.md` — gerçek sayılarla güncellenecek | Görkem (G-15) |
| 4 | Veri ön işleme adımları | 🟠 | `docs/VERI_METODOLOJISI.md` | Görkem (G-15) |
| 5 | Model veya kural yapısının açıklaması | 🟠 | `docs/kararlar/003-hibrit-cikarim.md` iyi başlangıç | Samet (S-16) |
| 6 | Benzer ürünler nasıl karşılaştırılıyor | ❌ | Yazılacak | Eren (E-15) |
| 7 | Adım adım çalıştırma talimatları | ✅ | `docs/KURULUM.md` | Eren (E-15) |
| 8 | Karşılaşılan problemler ve çözümler | 🟠 | `docs/SPRINT0_RAPORU.md` böl. 5 + `docs/kararlar/` — derlenecek | Eren (E-16) |
| 9 | Model çıktılarının örnekleri | ❌ | `docs/CIKTI_ORNEKLERI.md` | Esra (ES-15) |
| 10 | Performans değerlendirme yöntemleri | 🟠 | `docs/SONUCLAR.md` + `eval/` — altın set sonrası tamamlanır | Samet (S-16) |

---

## Madde 7 — Değerlendirme Kriterleri (%100)

| Ağırlık | Kriter | Bizdeki dayanak | Risk |
|---|---|---|---|
| **%30** | Model Başarısı ve Anlamlandırma | Altın set + `make eval` + ablasyon | 🔴 Altın set 16 Ağu'da bitmezse ölçüm yok |
| **%20** | Fonksiyonellik ve Senaryo Kapsamı | Uçtan uca boru hattı, 3 ekran, API | 🟠 96/300 kampanya |
| **%20** | Teknik İmplementasyon ve Mimari | Donmuş şema, hibrit çıkarım, modüler yapı | ✅ |
| **%20** | On-Prem Uygulanabilirlik | Docker, yerel LLM, sızıntı testleri | 🔴 Docker hiç çalıştırılmadı |
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
