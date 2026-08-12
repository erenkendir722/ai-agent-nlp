# Şartname Uyum Takibi

**Görev:** E-12 · **Sorumlu:** Eren · **Son denetim:** 12 Ağustos 2026
**Kaynak:** `2026_TYDA_SARTNAME_Ikinci_Senaryo_TR_1_1IAJb.pdf` (20 sayfa, 2. Senaryo)

Jüri bu şartnameye göre puanlıyor. Bu dosya her maddeyi tek tek satır olarak
tutar; unutulan bir gereklilik yüzünden puan kaybetmenin panzehiri budur.

**Durum işaretleri:** ✅ tamam · 🟠 kısmi · ❌ eksik · ⬜ sırası gelmedi

---

## 🚨 ÖNCE BUNLAR — açık ve riskli

| # | Sorun | Neden kritik | Kim |
|---|---|---|---|
| 1 | **Depo private** | Madde 8 açık kaynak paylaşımı **zorunlu** tutuyor; madde 9 yüklenmemiş projelerin **değerlendirmeye alınmayacağını** söylüyor | Eren (E-01) |
| 2 | **`BilisimVadisi2026` etiketi yok** | Madde 9 bu etiketle yüklemeyi şart koşuyor | Eren (E-01) |
| 3 | **"Türkiye Açık Kaynak Platformu" etiketi yok** | Madde 9: *"yükleme işlemi gerçekleştirilirken … etiketlenmesi gerekmektedir"* | Eren (E-01) |
| 4 | **10 faal bankanın 2'sinde veri yok** | Madde 5.1: veri seti BDDK listesindeki kuruluşların **tümünü** içermeli | Görkem (G-03, G-04) |
| 5 | **Veri seti indirme bağlantısı yok** | Madde 9 herkese açık bağlantıyı zorunlu tutuyor | Görkem (G-11, G-12) |
| 6 | **Teslim tarihi belirsiz — aşağıya bak** | Şartname kendi içinde çelişiyor | Eren — **bugün sor** |

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
| 5.2 | *"%2,05 kâr payı oranı"* yorumlanmalı | ✅ | `src/extraction/kural.py` · `tests/test_normalizasyon.py` | Samet |
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
| Kodlar/veri kümeleri GitHub'da **açık kaynak** paylaşılmalı | ❌ | **Depo private** | Eren (E-01) |
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
| GitHub'da **`BilisimVadisi2026`** etiketi | ❌ | Topic yok | Eren (E-01) |
| **"Türkiye Açık Kaynak Platformu"** etiketlenmesi | ❌ | Topic yok | Eren (E-01) |
| Ekip adı repo'da belirtilmiş | ✅ | README: "Takım SVARTAL" — repo açıklaması boş, doldurulacak | Eren (E-01) |
| (1) Bağımlılıkların **eksiksiz** listesi | ✅ | `requirements.txt` + `docs/LISANSLAR.md` | Eren |
| (2) Çalıştırma adımlarının tamamı | ✅ | `docs/KURULUM.md` | Eren |
| (3) Veri setinin **herkese açık indirme bağlantısı** | ❌ | Yayınlanmadı | Görkem (G-11, G-12) |
| **En az haftalık** güncelleme | ✅ | 7, 9, 10, 12 Ağustos commit'leri | Eren (E-03) |
| Sürüm etiketleri | ❌ | Depoda hiç git tag yok | Eren (E-03) |

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
