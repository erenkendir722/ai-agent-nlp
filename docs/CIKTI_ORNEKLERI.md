# Model Çıktılarının Örnekleri

_Otomatik üretildi: 26.08.2026 18:22 · `make cikti-ornekleri`_

**Şartname madde 6**, proje dokümantasyonunda *«model çıktılarının örnekleri»*
başlığını zorunlu tutuyor. Aşağıdaki çıktıların tamamı **işlenmiş
veritabanından** (931 kayıt) seçilmiştir; hiçbiri elle yazılmadı
veya güzelleştirilmedi. Her tabloda değerin hangi katmandan geldiği
(`kural` / `llm` / `hibrit`) ve güven skoru yazar.

Yeniden üretmek için: `make cikti-ornekleri`

---

## 1. Şartnamenin kendi örneği (madde 11, A Bankası)

Şartname üç banka metni ve bunlardan çıkarılmasını beklediği tabloyu veriyor.
Aşağıdaki çıktı **yalnız kural katmanıyla** üretildi: ağ gerektirmez, her
koşuda birebir aynıdır, yani jüri kendi makinesinde tekrarlayabilir.

**Girdi:**

> Yeni ev sahibi olmak isteyen müşterilerimize özel %1,89 kâr payı oranı ile 120 aya kadar konut finansmanı fırsatı sunulmaktadır. Kampanya kapsamında 50.000 TL'ye kadar dosya masrafı alınmamaktadır. Kampanya 31 Aralık 2026 tarihine kadar geçerlidir.

**Çıktı:**

| Alan | Değer | Birim | Yöntem | Güven |
|---|---|---|---|---|
| `kar_payi_orani` | 1.89 | yuzde | kural | 0.93 |
| `vade_ay_max` | 120 | ay | kural | 0.92 |
| `masrafsiz_mi` | True | — | kural | 0.91 |
| `kampanya_bitis` | 2026-12-31 | — | kural | 0.89 |

**Belirtilmemiş (12 alan):** Kampanya türü, Ürün türü, Hedef kitle, Azami finansman tutarı, Taksit sayısı, Tahsis ücreti, Masraf bilgisi, Ödül miktarı, İndirim oranı, Alışveriş puanı, Kampanya avantajı, Kampanya koşulları

> Not: «50.000 TL'ye kadar dosya masrafı **alınmamaktadır**» cümlesi 15
> Ağustos'a kadar 50.000 TL'lik bir tahsis ücreti olarak okunuyordu.
> Olumsuzluk kipi (`-mAktAdır`) sözlüğe eklendi; `tests/test_kural.py::
> TestSartnameMadde11` bu davranışı sabitler.

---

## 2. Temiz kayıt — alanların çoğu doldu

Sayfada bilgi açıkça yazılıysa sistem alanların çoğunu çıkarır.

**Kaynak:** Kuveyt Türk Katılım Bankası A.Ş. · [https://www.kuveytturk.com.tr/kampanyalar/kendim-icin/musteri-ol-kampanyalari/evlenecek-olan-veya-yeni-evli-ciftlere-kuveyt-turkten-mujde-evlilik-paketi](https://www.kuveytturk.com.tr/kampanyalar/kendim-icin/musteri-ol-kampanyalari/evlenecek-olan-veya-yeni-evli-ciftlere-kuveyt-turkten-mujde-evlilik-paketi) · çekim 20.08.2026

**Girdi (ham metinden):**

> Evlilik süreci, pek çok çift için hayatlarının en özel ve anlamlı dönemlerinden biri olduğu kadar, aynı zamanda planlama, bütçe yönetimi ve karar süreçleri açısından oldukça yoğun ve maliyetli bir dönem olabilir. Kuveyt Türk olarak, siz değerli müşterilerimizin bu özel yolculuğunda yanlarında olmak ve süreci daha kolay, planlı ve keyifli hale getirmek amacıyla Müjde Evlilik Paketi’mizi oluşturduk. Bu paketimizi tasar…

**Yapısal çıktı:**

| Alan | Değer | Birim | Yöntem | Güven |
|---|---|---|---|---|
| `kampanya_turu` | alisveris_puani | — | llm | 0.80 |
| `hedef_kitle` | yeni_musteri | — | llm | 0.80 |
| `kar_payi_orani` | 1.99 | yuzde | hibrit | 0.93 |
| `finansman_tutari_max` | 100000.0 | tl | kural | 0.55 |
| `vade_ay_max` | 48 | ay | kural | 0.92 |
| `odul_miktari` | 7250.0 | tl | kural | 0.85 |
| `indirim_orani` | 50.0 | yuzde | kural | 0.88 |
| `kampanya_avantaji` | 10.000 TL ve 50.000 TL arasında yapılan 3 harcamanın vade farksız 10 taksite bölünmesi, araç finansmanında 10 puan indirim ayrıcalığı, 50.000-100.000 TL arası harcamalarda Haziran ayına özel vade farksız 5 taksit imkanı. | — | llm | 0.70 |
| `kampanya_bitis` | 2026-09-30 | — | kural | 0.89 |
| `kampanya_kosullari` | 2026 yılında evlenmiş veya evlenecek olan, KTAILE26 referans kodunu kullanarak görüntülü görüşme veya şubelerden müşteri olan yeni müşteriler yararlanabilir. Kampanya Sağlam Kart ve Sağlam Sanal Kart ile geçerlidir. Telekomünikasyon, doğrudan pazarlama, yurt dışı harcamalar, yemek, gıda, akaryakıt, fatura, kozmetik, ofis malzemesi, kuyum, hediye kart/çeki, havayolları, seyahat acenteleri ve taşımacılık harcamaları taksitlendirme kapsamı dışındadır. Araç satışlarında taksitlendirme uygulanmaz. | — | llm | 0.70 |

**Belirtilmemiş (6 alan):** Ürün türü, Taksit sayısı, Tahsis ücreti, Masraf bilgisi, Masrafsız mı, Alışveriş puanı

**Kanıt zinciri (alıntılar):**

- `kar_payi_orani` ← «ınız. - 2 ay ertelemeli İhtiyaç Kart, yeni müşterilere özel 100.000 TL’ye kadar %1,99 oranla 12 aya varan taksit fırsatı sunuyor! - Kuveyt Türk Mobil uygulamasından»
- `finansman_tutari_max` ← «- 2 ay ertelemeli İhtiyaç Kart, yeni müşterilere özel 100.000 TL’ye kadar %1,99 oranla 12 aya varan taksit fırsatı sunuyor!»
- `vade_ay_max` ← «Üstelik başvuru aşamasında 48 aya varan vade seçeneklerinden yararlanabilmek mümkündür.»

**Uygunluk koşulları (muhakeme ajanının girdisi):**

- müşteri tipi: yeni_musteri
- azami tutar: 100.000 TL
- azami vade: 48 ay
- zorunlu ürün: kredi kartı

---

## 3. Sayısal alanlar birlikte — kâr payı, vade ve ücret

Şartname 5.3'ün istediği sayısal alanların aynı kayıtta çıkması.

**Kaynak:** Türkiye Finans Katılım Bankası A.Ş. · [https://www.turkiyefinans.com.tr/tr-tr/kampanyalar/Sayfalar/ihtiyac-finansmani-kampanyasi.aspx](https://www.turkiyefinans.com.tr/tr-tr/kampanyalar/Sayfalar/ihtiyac-finansmani-kampanyasi.aspx) · çekim 24.08.2026

**Girdi (ham metinden):**

> Mobilden Türkiye Finanslı Ol, Kâr Paysız 50.000 TL'ye Varan İhtiyaç Finansmanını Kaçırma! Şimdi mobilden Türkiye Finanslı olanlar %0 kar payı ile 50.000 TL'ye varan İhtiyaç Finansmanından yararlanıyor. Siz de Türkiye Finans Mobil’i hemen indirin, dakikalar içinde müşterimiz olun, hem avantajlı dijital bankacılık dünyası ile tanışın hem de aradığınız nakde kâr payı ödemeden kavuşun. Kâr Paysız 50.000 TL’ye Varan İhtiy…

**Yapısal çıktı:**

| Alan | Değer | Birim | Yöntem | Güven |
|---|---|---|---|---|
| `kampanya_turu` | ihtiyac_finansmani | — | llm | 0.80 |
| `hedef_kitle` | yeni_musteri | — | llm | 0.80 |
| `kar_payi_orani` | 0.0 | yuzde | hibrit | 1.00 |
| `finansman_tutari_max` | 50000.0 | tl | hibrit | 0.94 |
| `vade_ay_max` | 36 | ay | kural | 0.92 |
| `tahsis_ucreti` | 0.5 | yuzde | hibrit | 0.91 |
| `masrafsiz_mi` | False | — | kural | 0.91 |
| `odul_miktari` | 11000.0 | tl | hibrit | 0.85 |
| `kampanya_bitis` | 2026-08-31 | — | hibrit | 0.96 |
| `kampanya_kosullari` | Kampanya 1 Ağustos - 31 Ağustos 2026 tarihleri arasında geçerlidir. Mobilden Türkiye Finanslı olan ve Findeks kredi notu 1875 ve üzerinde olan yeni müşteriler için, 3 ay vadeli ve 50.000 TL'ye kadar sigortalı ihtiyaç finansmanı başvurusunda %0 kâr payı oranı uygulanır. Finansman tahsis ücreti tutarın %0,5'idir (%15 BSMV dahil). Her müşteri yalnızca 1 defa yararlanabilir. Kâr payı oranı ve onay, müşterinin KKB/Findeks skoru ve gelir bilgilerine göre banka tarafından belirlenir ve değiştirilebilir. Görüntülü görüşme ile mobil şube üzerinden katılım sağlanır. | — | llm | 0.70 |

**Belirtilmemiş (6 alan):** Ürün türü, Taksit sayısı, Masraf bilgisi, İndirim oranı, Alışveriş puanı, Kampanya avantajı

**Kanıt zinciri (alıntılar):**

- `kar_payi_orani` ← «%0 kar payı ile 50.»
- `finansman_tutari_max` ← «- Kampanya kapsamında yukarıdaki tarih aralığında mobilden Türkiye Finanslı olan müşterilere %0 kâr payı oranı ve 3 ay vadeli olarak 50.000 TL’ye kadar İhtiyaç Finansmanı başvurusu…»
- `vade_ay_max` ← «125.000TL’ye kadar olması durumunda maksimum vade 36 ayı, 125.»

**Uygunluk koşulları (muhakeme ajanının girdisi):**

- müşteri tipi: yeni_musteri
- azami tutar: 50.000 TL
- azami vade: 36 ay

---

## 4. Dolaylı ifade — «avantajlı / özel oranlı»

Şartname 5.2 bu ifadelerin yorumlanmasını istiyor. **Sistem sayı uydurmaz:** metinde sayı varsa çıkarılır, yoksa `kar_payi_orani` «Belirtilmemiş» kalır ve ifadenin kendisi `kampanya_avantaji` alanına yazılır. Aşağıdaki kayıt bu davranışı gösterir.

**Kaynak:** Kuveyt Türk Katılım Bankası A.Ş. · [https://www.kuveytturk.com.tr/kendim-icin/finansmanlar/arac-finansmanlari/arac-finansmani](https://www.kuveytturk.com.tr/kendim-icin/finansmanlar/arac-finansmanlari/arac-finansmani) · çekim 24.08.2026

**Girdi (ham metinden):**

> “Şimdi bir otomobilim olsaydı şuraya giderdim!” cümlesini sık sık kurmaya mı başladınız? Yoksa çok istediğiniz araç için finansman desteğine mi ihtiyacınız var? Eğer Kuveyt Türk müşterisi değilseniz, hızlı ve pratik bir şekilde Kuveyt Türk Mobil ile Kuveyt Türk müşterisi olabilirsiniz. O halde Kuveyt Türk Araç Finansmanı ile tanışmanın vakti çoktan gelmiş demektir. Araç Finansmanı Nedir? Kuveyt Türk Araç Finansmanı, …

**Yapısal çıktı:**

| Alan | Değer | Birim | Yöntem | Güven |
|---|---|---|---|---|
| `kampanya_turu` | tasit_finansmani | — | llm | 0.80 |
| `hedef_kitle` | tum_musteriler | — | llm | 0.80 |
| `finansman_tutari_max` | 400000.0 | tl | kural | 0.85 |
| `vade_ay_max` | 48 | ay | kural | 0.92 |
| `tahsis_ucreti` | 0.5 | yuzde | kural | 0.83 |
| `masrafsiz_mi` | False | — | kural | 0.91 |
| `kampanya_avantaji` | Sıfır ve ikinci el araçlar için finansman desteği, 18 yaşını dolduran herkes için uygun, 48 aya varan vade seçenekleri, ikinci el araçlarda 10 yaşa kadar finansman imkanı, Kuveyt Türk Mobil üzerinden şubeye gitmeden başvuru imkanı. | — | llm | 0.70 |
| `kampanya_kosullari` | Sıfır araçlarda satış, ikinci elde kasko değeri dikkate alınır. 0-5 yaş araçlar için maksimum 48 ay, 6-10 yaş araçlar için maksimum 36 ay vade. Finansman tutarı oranları: 0-400.000 TL için %70, 400.001-800.000 TL için %50, 800.001-1.200.000 TL için %30, 1.200.001-2.000.000 TL için %20, 2.000.001 TL ve üzeri için kullandırım yapılmaz. Sıfır araçlarda maksimum 2 yaşa kadar, ikinci el araçlarda maksimum 10 yaşa kadar olan araçlar için kullanılabilir. | — | llm | 0.70 |

**Belirtilmemiş (8 alan):** Ürün türü, Kâr payı oranı, Taksit sayısı, Masraf bilgisi, Ödül miktarı, İndirim oranı, Alışveriş puanı, Kampanya bitişi

**Kanıt zinciri (alıntılar):**

- `vade_ay_max` ← «Üstelik başvuru aşamasında 48 aya varan vade seçeneklerinden yararlanabilmek mümkündür.»
- `tahsis_ucreti` ← «Finansman tahsis ücreti finansman tutarının 0,5%’i (binde beş) olacak şekilde hesaplanmaktadır.»

**Uygunluk koşulları (muhakeme ajanının girdisi):**

- müşteri tipi: tum_musteriler
- azami tutar: 400.000 TL
- azami vade: 48 ay

---

## 5. Eksik bilgili kayıt — «Belirtilmemiş» demek

Kampanya sayfası az bilgi veriyorsa sistem **boş bırakır**. Şartname madde 11'in tablosu da bu ifadeyi kullanıyor; uydurmak yerine bilmediğini söylemek doğru davranıştır.

**Kaynak:** Dünya Katılım Bankası A.Ş. · [https://dunyakatilim.com.tr/kampanyalar/fiziki-altin](https://dunyakatilim.com.tr/kampanyalar/fiziki-altin) · çekim 09.08.2026

**Girdi (ham metinden):**

> ⏰ Kampanya Süresi Dolmuştur! ✨ Yeni Kampanyalarımız İçin Bizi Takip Etmeyi Unutmayın! Dünya Katılım’dan Yeni Müşterilere Altın Değerinde Fırsat! Dünya Katılım, yeni müşterilerine özel yepyeni bir kampanya ile karşınızda! 13.01.2026-31.03.2026 tarihleri arasında Dünya Katılım Mobil Şube veya İnternet Şube üzerinden fiziki altın siparişi veren yeni müşterilerimize, siparişlerine ek olarak altın hediye ediyoruz. Dünya K…

**Yapısal çıktı:**

| Alan | Değer | Birim | Yöntem | Güven |
|---|---|---|---|---|
| `kampanya_turu` | yatirim_urunu | — | llm | 0.80 |
| `hedef_kitle` | yeni_musteri | — | llm | 0.80 |
| `kampanya_bitis` | 2026-03-31 | — | hibrit | 0.96 |

**Belirtilmemiş (13 alan):** Ürün türü, Kâr payı oranı, Azami finansman tutarı, Azami vade, Taksit sayısı, Tahsis ücreti, Masraf bilgisi, Masrafsız mı, Ödül miktarı, İndirim oranı, Alışveriş puanı, Kampanya avantajı, Kampanya koşulları

**Uygunluk koşulları (muhakeme ajanının girdisi):**

- müşteri tipi: yeni_musteri
- zorunlu ürün: dijital kanal

---

## 6. Uygunluk koşulu çıkarılmış kayıt

Kampanyanın KİME açık olduğu yapısal alana çevrilir; müşteri profili ekranındaki muhakeme ajanı bu kısıtları çözer.

**Kaynak:** Kuveyt Türk Katılım Bankası A.Ş. · [https://saglamkart.kuveytturk.com.tr/kampanyalar/saglam-kart-tatilde-de-yaninizda-2042](https://saglamkart.kuveytturk.com.tr/kampanyalar/saglam-kart-tatilde-de-yaninizda-2042) · çekim 24.08.2026

**Girdi (ham metinden):**

> - Sağlam Kart sahipleri Halalbooking'de de avantajlı! - 31 Aralık 2026 tarihine kadar yapacağınız tatil harcamalarınızda 9 aya varan taksit avantajından yararlanabilir, Halalbooking’e kaydolurken 1000 TL değerinde indirim kazanabilirsiniz. - İndirim kampanyası Halalbooking’e ilk defa bu link üzerinden kaydolan müşteriler için geçerlidir ve 10,000 TL ve üzerindeki rezervasyonlarda kullanılabilecektir. - Halalbooking h…

**Yapısal çıktı:**

| Alan | Değer | Birim | Yöntem | Güven |
|---|---|---|---|---|
| `kampanya_turu` | kart | — | llm | 0.80 |
| `hedef_kitle` | mevcut_musteri | — | llm | 0.80 |
| `kar_payi_orani` | 0.0 | yuzde | kural | 0.80 |
| `vade_ay_max` | 9 | ay | kural | 0.92 |
| `odul_miktari` | 1000.0 | tl | hibrit | 0.85 |
| `indirim_orani` | 20.0 | yuzde | kural | 0.87 |
| `kampanya_avantaji` | Halalbooking'de 9 aya varan taksit avantajı, ilk kayıtta 1000 TL değerinde indirim, seçili otellerde %20'ye varan indirim, private hizmetler ve ücretsiz havaalanı transferi | — | llm | 0.70 |
| `kampanya_bitis` | 2026-12-31 | — | kural | 0.89 |
| `kampanya_kosullari` | İndirim kampanyası Halalbooking'e ilk defa bu link üzerinden kaydolan müşteriler için geçerlidir ve 10,000 TL ve üzerindeki rezervasyonlarda kullanılabilecektir. Harcamaların ödeme esnasında taksitlendirilmesi gerekmektedir. KKTC için yapılan harcamalara vade farksız 3 taksit fırsatı sunulmaktadır. Yurtdışı tatil harcamaları taksitlendirilememektedir. Kampanya 31 Aralık 2026 tarihine kadar geçerlidir. Mevzuat gereği yurtdışı harcamalar taksitlendirilemez. Kart numarasının ilk 6 hanesi ile Halalbooking'e kayıt gereklidir. Kredi kartı segmentine göre ilk yıl Gold, Platin veya Diamond üyelik kazanılır. Kuveyt Türk koşulları değiştirme veya sonlandırma hakkını saklı tutar. | — | llm | 0.70 |

**Belirtilmemiş (7 alan):** Ürün türü, Azami finansman tutarı, Taksit sayısı, Tahsis ücreti, Masraf bilgisi, Masrafsız mı, Alışveriş puanı

**Kanıt zinciri (alıntılar):**

- `vade_ay_max` ← «- 31 Aralık 2026 tarihine kadar yapacağınız tatil harcamalarınızda 9 aya varan taksit avantajından yararlanabilir, Halalbooking’e kaydolurken 1000 TL değerinde indirim kazanabilirs…»
- `odul_miktari` ← «ızda 9 aya varan taksit avantajından yararlanabilir, Halalbooking’e kaydolurken 1000 TL değerinde indirim kazanabilirsiniz. - İndirim kampanyası Halalbooking’e ilk def»
- `indirim_orani` ← «- Kredi kartı segmentinize göre ilk yıl Gold, Platin veya Diamond üyelik kazanarak seçili otellerde %20'ye varan indirim, private hizmetler ve ücretsiz havaalanı transferi ayrıcalı…»

**Uygunluk koşulları (muhakeme ajanının girdisi):**

- müşteri tipi: mevcut_musteri
- azami vade: 9 ay
- zorunlu ürün: kredi kartı

---

## Bu örnekler neyi kanıtlar

| İddia | Örnekte görülen |
|---|---|
| Kanıtsız değer üretilmez | Her tabloda `yöntem` ve `güven`; alıntılar bölümünde kaynak cümle |
| Sistem sayı uydurmaz | Eksik bilgili kayıtta alanlar boş bırakılır, doldurulmaz |
| Hibrit çıkarım | Aynı kayıtta `kural` ve `llm` yöntemli alanlar yan yana |
| Yapısal uygunluk | Uygunluk bölümündeki kısıtlar serbest metinden değil, alanlardan gelir |

Ölçülmüş sonuçlar: [`SONUCLAR.md`](SONUCLAR.md) · Hata analizi: [`HATA_ANALIZI.md`](HATA_ANALIZI.md)
