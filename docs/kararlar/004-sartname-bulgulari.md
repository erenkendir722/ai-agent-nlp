# ADR 004 — Şartname okumasından çıkan düzeltmeler ve açık sorular

**Tarih:** 9 Ağustos 2026
**Durum:** Kabul edildi · tüm maddeler kapalı
**Sahip:** Eren
**Kaynak:** `2026_TYDA_SARTNAME_Ikinci_Senaryo_TR_1_1IAJb.pdf` (23 sayfa)

## 1. ✅ TESLİM TARİHİ ÇELİŞKİSİ — KAPANDI, ÖNEMİ YOK

> **KARAR (Eren, 9 Ağustos 2026): Bu maddenin önemi yok, kapatıldı.**
> Şartname madde 9'daki 12.07.2026 tarihi eski/hatalı metindir. İşleyen takvim
> Tablo 1'deki **27 Temmuz – 26 Ağustos** aralığıdır. Konu takıma sorulmayacak,
> plan 26 Ağustos'a göre yürüyecek, hedef teslim 25 Ağustos 20:00 olarak kalıyor.
> Önümüze bakıyoruz.

Aşağıdaki bölüm kayıt amaçlı bırakılmıştır.

### (Kayıt) Tespit edilen tutarsızlık

Şartname kendi içinde tutarsız:

| Yer | Tarih |
|---|---|
| Madde 9 (Proje Bilgileri Sunumları) | *"Yarışmamız **12.07.2026** tarihinde sona erecektir... 12.07.2026 saat 23:59'a kadar... GitHub'a yüklemeleri gerekmektedir."* |
| Tablo 1 (Yarışma Takvimi) | Yarışma Çevrimiçi Süreci: **27 Temmuz – 26 Ağustos** |
| Madde 8 | Başvurular **12 Temmuz 2026**'ya kadar |
| Tablo 1 | Son Başvuru Tarihi: **17 Temmuz** |

Madde 9'daki 12.07.2026, başvuru tarihinden kopyalanmış eski bir metin gibi
görünüyor: bugün 9 Ağustos ve yarışma çevrimiçi süreci devam ediyor, Kick Off
27 Temmuz'da yapıldı. Dolayısıyla işleyen tarih **26 Ağustos** olmalı.

**Ama bu bizim yorumumuz, teyit değil.** Teslim tarihini yanlış anlamak
yarışmayı tamamen kaybettirir.

**Aksiyon (Eren, bugün):** Yarışma e-posta grubuna sor:
> "Şartname madde 9'da teslim tarihi 12.07.2026 olarak geçiyor, Tablo 1'de ise
> çevrimiçi süreç 27 Temmuz – 26 Ağustos aralığında görünüyor. GitHub son
> yükleme tarihi hangisidir?"

Cevap gelene kadar plan **26 Ağustos**'a göre yürür, ancak hedef teslim
25 Ağustos 20:00 olarak korunur — tampon zaten bu belirsizlik içindir.

## 2. Doğrulanan varsayımlar (plan doğruymuş)

- **Değerlendirme ağırlıkları** planla birebir aynı: Model Başarısı %30,
  Fonksiyonellik %20, Teknik İmplementasyon %20, On-Prem %20, Yenilikçilik %10.
- **Final yeri:** Bilişim Vadisi Kocaeli Kampüsü, son 24 saat fiziki (madde 10). ✅
- **Sunum:** 4 dakika + 1 dakikalık demo videosu (madde 10). ✅
- **Demo videosu:** maks. 5 dakika, içinde arayüz, dashboard, chatbot, metin
  girdisi, yapılandırılmış çıktı ve karşılaştırma sonuçları görünmeli (madde 6). ✅
- **`BilisimVadisi2026` etiketi** ve "Türkiye Açık Kaynak Platformu" etiketlemesi
  zorunlu (madde 9). ✅
- **En az haftalık güncelleme** zorunlu (madde 9). ✅
- **Karşılaştırma kriterleri (5.7)** planla birebir aynı, beş kriter. ✅
- **Normalizasyon örnekleri (5.6)** planla birebir: `%2,05 / % 2.05 / 2.05 %`
  ve `500 TL / 500₺ / 500 Türk Lirası`. ✅

## 3. Düzeltilen varsayımlar

### 3.1 Kampanya türleri — bkz. [ADR 002](002-kampanya-turleri.md)
Tahmini taksonomi önemli ölçüde yanlıştı; şartname 5.4 listesi benimsendi.

### 3.2 Lisans — daha esnekmiş
Plan "madde 8 özellikle Apache 2.0 istiyor" diyordu. Şartname aslında
*"Açık Kaynak herhangi bir lisans ile (Apache, MIT, GNU vb.)"* diyor. Ancak
devamında: *"yarışma bitiş tarihinde **Apache lisansı (Apache License 2.0)** ile
lisanslanarak Türkiye Açık Kaynak Platformu GitHub hesabında paylaşılacağını
kabul eder."*

**Karar değişmiyor:** Apache 2.0 kullanıyoruz — sonunda zaten o gerekiyor.

### 3.3 Terim sözlüğü — şartnamede hazır tanımlar varmış
Madde 5.5 beş kavramı resmî tanımlarıyla veriyor: Kâr Payı Oranı, Finansman
Maliyeti, Katılım Fonu, Masrafsız Finansman, Avantajlı Finansman.

Bu tanımlar LLM istem enjeksiyonuna **birebir** kondu (`src/extraction/llm.py`,
`TERIMLER`). Jürinin kendi tanımlarıyla çalışan bir model, "terminolojiye uyum"
kriterinde tartışmasız durumdadır.

## 4. Yeni öğrenilenler — plana eklenmeli

### 4.1 Yenilikçilik kriteri "ek veri alanları" istiyor
Madde 7, Yenilikçilik (%10) altında açıkça **"Ek veri alanlarının çıkarılması"**
diyor. Bu, şartnamenin istediği alanların ÖTESİNE geçmeyi ödüllendiriyor.

Bizde zaten var ve sunumda **yenilikçilik** başlığı altında anlatılmalı:
`masrafsiz_mi` (bool), alan bazlı `guven` skoru, `yontem` (kural/llm/hibrit),
kanıt zinciri (alıntı + karakter aralığı), `doluluk_orani`.

### 4.2 Chatbot cevap biçimi şartnamede örneklenmiş
Madde 11, Senaryo 2 cevabı kriter kriter ve **gerekçeli** ("çünkü oran
%1,87'dir"). Chatbot'un karşılaştırma cevabı bu biçime uyacak şekilde
yeniden yazıldı (`src/rag/chatbot.py`, `_karsilastirma_cevabi`).

### 4.3 Proje yarışma döneminde geliştirilmiş olmalı
Madde 8: *"önceden tamamlanmış veya hâlihazırda devam etmekte olan projeler
dâhil edilemez"*, başvuru dosyası Turnitin'e yüklenecek. Depo geçmişimiz
7 Ağustos'ta başlıyor — bu lehimize kanıt. Commit geçmişini temiz tutun.

### 4.4 Ücretli yazılım ve üçüncü taraf hizmet yasak
Madde 8: *"projenin bağımlı olduğu ücretli herhangi bir yazılım kullanamaz"*,
*"üçüncü taraflardan hizmet ya da ürün satın alamaz"*. Yığınımızda ücretli
bileşen yok; `docs/LISANSLAR.md` bunun kanıtı olacak.

## 5. Şartnamede olmayan ama bizde olan şeyler

Bunlar eksik değil, **fazladan** — ve hepsi puanlanan bir kritere bağlı:

| Bizde olan | Hangi kritere hizmet ediyor |
|---|---|
| Kanıt zinciri (alıntı + karakter aralığı + URL + tarih) | Model Başarısı %30 · Yenilikçilik %10 |
| Sayısal doğrulama kalkanı | Model Başarısı %30 |
| Ablasyon tablosu | Model Başarısı %30 · Teknik İmplementasyon %20 |
| Hava boşluğu (air-gap) testi | On-Prem %20 |
| Donanım profilleri (4B/9B/27B) | On-Prem %20 |
| Şeffaf, ayarlanabilir ağırlıklı skor | Fonksiyonellik %20 |
| Vade farkı uyarısı | Fonksiyonellik %20 |
