# Katılım Bankacılığı Terim Sözlüğü

**Şartname 5.5** — *"Model katılım bankacılığına özgü finansal kavramları doğru
şekilde analiz edebilmelidir."*

Bu sözlük süs değildir: içeriği doğrudan LLM istemine enjekte edilir
([`src/extraction/llm.py`](../src/extraction/llm.py) → `TERIMLER`). Genel amaçlı
bir model "kâr payı"nı faiz sanabilir; alan bilgisini modele taşıyan şey bu
metindir. Buradaki bir tanımı değiştirmek çıkarım davranışını değiştirir.

---

## 1. Şartnamedeki beş resmî kavram

Tanımlar şartname 5.5 tablosundan **birebir** alınmıştır.

### Kâr Payı Oranı
Katılım bankacılığında **faiz yerine** kullanılan, finansman işlemine konu olan
mal veya hizmet üzerinden oluşan kâr payı oranını ifade eder.

- **Şemadaki karşılığı:** `kar_payi_orani` (aylık yüzde, `float`)
- **Neden faiz değil:** Katılım bankası parayı ödünç vermez; müşterinin
  istediği malı satın alıp vadeli olarak ona satar. Aradaki fark kâr payıdır.
  Terminolojiyi karıştırmak sektör jürisinin ilk yakalayacağı hatadır.
- **Makullük sınırı:** aylık kâr payı tek haneli yüzdelerde seyreder. Sistem
  %15 üstünü aylık oran saymaz (`AYLIK_KAR_PAYI_UST_SINIRI`) — "Yıllık Maliyet
  Oranı %82,44" gibi ifadeler bu alana düşmesin diye.

### Finansman Maliyeti
Kullandırılan finansman kapsamında oluşan **toplam geri ödeme tutarını** ve
müşterinin katlandığı toplam maliyeti ifade eder.

- **Şemadaki karşılığı:** tek alan değil, **hesaplanır** —
  [`karsilastirma.toplam_maliyet()`](../src/comparison/karsilastirma.py)
- Kâr payı oranı + vade + tahsis ücretinden annüite formülüyle üretilir.
  Murabahada satış bedeli baştan sabitlendiği için taksit hesabı matematiksel
  olarak annüite ile aynıdır.

### Katılım Fonu
Katılım bankacılığı prensiplerine uygun olarak değerlendirilen ve fon sahipleri
ile banka arasında **kâr-zarar paylaşımına** dayanan hesap türü.

- **Şemadaki karşılığı:** `kampanya_turu = yatirim_urunu`, `urun_turu` serbest metni
- Mevduat **değildir**: getiri garanti edilmez, kâr da zarar da paylaşılır.
  Bu yüzden katılma hesabı ürünlerinde "faiz oranı" gibi bir alan aranmaz.

### Masrafsız Finansman
Finansman işlemi kapsamında tahsis ücreti, dosya masrafı veya benzeri ek
maliyetlerin **uygulanmadığı** finansman türü.

- **Şemadaki karşılığı:** `masrafsiz_mi` (`bool`), `tahsis_ucreti`, `masraf_bilgisi`
- **Türkçe tuzağı:** bankalar bunu ekle söyler, sözcükle değil —
  "alınmaz", "alınmıyor", "**alınmamaktadır**", "tahsil edilmemektedir",
  "uygulanmamaktadır". Sistem `-mAz / -mIyor / -mAmAktA(dır)` eklerini yapısal
  olarak tanır ([`olumsuzlanmis_mi`](../src/preprocessing/normalizasyon.py)).
- **İnce durum:** *"Ekspertiz ücreti banka tarafından karşılanmaktadır"* yüklemi
  **olumludur** ama masraf müşteriye yansımaz → masrafsız sayılır.

### Avantajlı Finansman
Standart finansman koşullarına göre daha uygun maliyet, kâr payı oranı veya
ek fayda sunan **kampanyalı** finansman ürünü.

- **Şemadaki karşılığı:** `kampanya_avantaji` (serbest metin)
- **Sayı uydurulmaz:** "avantajlı kâr payı fırsatı" ifadesinde rakam yoksa
  `kar_payi_orani` **boş bırakılır**, ifade `kampanya_avantaji`'ye yazılır
  (şartname 5.2). Boş bırakmak yanlış sayı vermekten her zaman iyidir.

---

## 2. Şartname 5.2'nin dolaylı ifadeleri

Şartname bu dört ifadenin doğru yorumlanmasını açıkça istiyor:

| İfade | Sistem ne yapar |
|---|---|
| "%2,05 kâr payı oranı" | `kar_payi_orani = 2.05` — sayı açık |
| "avantajlı kâr payı fırsatı" | Oran alanı **boş**; ifade `kampanya_avantaji`'ye |
| "özel oranlı finansman" | Oran alanı **boş**; ifade `kampanya_avantaji`'ye |
| "düşük maliyetli finansman" | Oran alanı **boş**; ifade `kampanya_avantaji`'ye |

Ortak kural: **sayısız ifadeden sayı türetilmez.** Bu kısıt istemle değil kodla
uygulanır — eleştirmen ajanı, LLM'in ürettiği her sayıyı ham metinde birebir
arar, bulamazsa alanı düşürür.

---

## 3. Sistemin tanıdığı diğer terimler

| Terim | Anlamı | Not |
|---|---|---|
| **Finansman** | Kredinin katılım bankacılığındaki karşılığı | "Kredi" sözcüğü de tanınır ama çıktıda "finansman" kullanılır |
| **Murabaha** | Maliyet + kâr payı ile vadeli satış | Bireysel finansmanın baskın yöntemi |
| **Tahsis ücreti** | Finansman tahsisinde alınan tek seferlik masraf | **Dosya masrafı** ile eş anlamlı kullanılır |
| **Ekspertiz ücreti** | Konut finansmanında değerleme masrafı | Sıklıkla "banka karşılar" biçiminde geçer |
| **Katılma hesabı** | Kâr-zarar ortaklığına dayalı hesap | Katılım fonunun müşteri tarafındaki adı |
| **Kâr payı avantajı** | Faiz indiriminin katılım bankacılığındaki karşılığı | `indirim_orani` ile karıştırılmamalı |
| **Alışveriş puanı / çeki** | Harcama karşılığı verilen ödül | `alisveris_puani` ve `odul_miktari` alanları |
| **Vade** | Geri ödeme süresi (ay) | "X aya kadar", "X ay vadeli", "X aya varan" biçimleri tanınır |

---

## 4. Karıştırılmaması gerekenler

Bunlar gerçek hata biçimleridir; her biri sistemde ayrı bir korumaya karşılık gelir.

| Karışan | Neden ayrı | Koruma |
|---|---|---|
| **Kâr payı oranı** ↔ **indirim oranı** | "%80'e varan indirim" bir kâr payı değildir | Makullük aralığı + dışlayıcı sözcükler |
| **Finansman tutarı** ↔ **ödül miktarı** | "5.000 TL değerinde alışveriş çeki" limit değil hediyedir | "değerinde", "… çeki" dışlayıcıları |
| **Tahsis ücreti** ↔ **finansman limiti** | "50.000 TL'ye kadar masraf alınmaz" cümlesinde 50.000 TL ücret değildir | Olumsuzlama reddi + aynı cümle kısıtı |
| **Aylık oran** ↔ **yıllık maliyet oranı** | Hesaplama araçlarındaki yıllık oran aylık sanılırdı | `AYLIK_KAR_PAYI_UST_SINIRI = %15` |
| **Kâr payı** ↔ **faiz** | Kavramsal olarak farklıdır | İstem enjeksiyonu (bu dosya) |

---

## 5. Kaynaklar

- TEKNOFEST 2026 TYDA Şartnamesi, 2. Senaryo, madde 5.2 ve 5.5 (resmî tanımlar)
- BDDK Kuruluş Listesi — <https://www.bddk.org.tr/Kurulus/Liste/77>
- Katılım bankalarının kamuya açık ürün ve kampanya sayfaları (bkz.
  [`docs/VERI_METODOLOJISI.md`](VERI_METODOLOJISI.md))

> Sözlüğe terim eklerken [`src/extraction/llm.py`](../src/extraction/llm.py)
> içindeki `TERIMLER` metnini de güncelleyin — model yalnız oradakini görür.
