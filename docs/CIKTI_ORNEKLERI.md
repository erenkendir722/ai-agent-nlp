# Model Çıktılarının Örnekleri

_Otomatik üretildi: 26.08.2026 16:45 · `make cikti-ornekleri`_

**Şartname madde 6**, proje dokümantasyonunda *«model çıktılarının örnekleri»*
başlığını zorunlu tutuyor. Aşağıdaki çıktıların tamamı **işlenmiş
veritabanından** (1024 kayıt) seçilmiştir; hiçbiri elle yazılmadı
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
| `tahsis_ucreti` | 0.5 | yuzde | kural | 0.83 |
| `masrafsiz_mi` | False | — | kural | 0.91 |
| `odul_miktari` | 11000.0 | tl | hibrit | 0.85 |
| `kampanya_avantaji` | Mobilden müşteri olanlara özel %0 kâr payı oranı, 3 ay vade ve 50.000 TL'ye varan ihtiyaç finansmanı fırsatı. Ayrıca mobilden müşteri olanlara özel 11.000 TL'ye varan bonus kazanma fırsatı. | — | llm | 0.70 |
| `kampanya_bitis` | 2026-08-31 | — | hibrit | 0.96 |
| `kampanya_kosullari` | Kampanya 1 Ağustos - 31 Ağustos 2026 tarihleri arasında geçerlidir. Mobilden Türkiye Finanslı olan, Findeks kredi notu 1875 ve üzerinde olan yeni müşteriler için geçerlidir. 50.000 TL'ye kadar %0 kâr payı oranı 3 ay vadeli sigortalı ihtiyaç finansmanı başvurusu yapılması durumunda geçerlidir. İhtiyaç Finansmanı tahsis ücreti finansman tutarının %0,5'idir. Kampanyadan her müşteri yalnızca 1 defa yararlanabilir. Son 30 gün içerisinde mobilden Türkiye Finans müşterisi olan kişiler faydalanabilir. | — | llm | 0.70 |

**Belirtilmemiş (5 alan):** Ürün türü, Taksit sayısı, Masraf bilgisi, İndirim oranı, Alışveriş puanı

**Kanıt zinciri (alıntılar):**

- `kar_payi_orani` ← «%0 kar payı ile 50.»
- `finansman_tutari_max` ← «- Kampanya kapsamında yukarıdaki tarih aralığında mobilden Türkiye Finanslı olan müşterilere %0 kâr payı oranı ve 3 ay vadeli olarak 50.000 TL’ye kadar İhtiyaç Finansmanı başvurusu…»
- `vade_ay_max` ← «000TL’ye kadar olması durumunda maksimum vade 36 ayı, 125.»

**Uygunluk koşulları (muhakeme ajanının girdisi):**

- müşteri tipi: yeni_musteri
- azami tutar: 50.000 TL
- azami vade: 36 ay

---

## 3. Sayısal alanlar birlikte — kâr payı, vade ve ücret

Şartname 5.3'ün istediği sayısal alanların aynı kayıtta çıkması.

**Kaynak:** Türkiye Finans Katılım Bankası A.Ş. · [https://www.turkiyefinans.com.tr/tr-tr/bireysel/tasit-finansmani/Sayfalar/dijital-tasit-finansmani.aspx](https://www.turkiyefinans.com.tr/tr-tr/bireysel/tasit-finansmani/Sayfalar/dijital-tasit-finansmani.aspx) · çekim 24.08.2026

**Girdi (ham metinden):**

> Dijital Taşıt Finansmanı Taşıt Finansmanı Artık Cebinde! Hayalindeki sıfır ya da ikinci el arabaya kavuşmak için Dijital Taşıt Finansmanı başvurunu Mobil Şube üzerinden kolayca yap; şubeye gitmeden, sıra beklemeden tüm belgelerini yükle. Finansman Güvence Sigortası, Kasko Sigortası ve Trafik Sigortası işlemlerini de başvurun sırasında tamamla, daha avantajlı kâr payı oranlarından yararlan. Hem yeni arabanın keyfini h…

**Yapısal çıktı:**

| Alan | Değer | Birim | Yöntem | Güven |
|---|---|---|---|---|
| `kampanya_turu` | tasit_finansmani | — | llm | 0.80 |
| `hedef_kitle` | tum_musteriler | — | llm | 0.80 |
| `kar_payi_orani` | 3.42 | yuzde | hibrit | 0.83 |
| `finansman_tutari_max` | 400000.0 | tl | kural | 0.60 |
| `vade_ay_max` | 48 | ay | kural | 0.92 |
| `tahsis_ucreti` | 0.5 | yuzde | hibrit | 0.90 |
| `masrafsiz_mi` | False | — | hibrit | 0.99 |
| `kampanya_avantaji` | Sigorta (Kasko, Trafik, Finansman Güvence) işlemlerinin başvuru sırasında tamamlanması durumunda daha avantajlı kâr payı oranlarından yararlanma imkanı. | — | llm | 0.70 |
| `kampanya_kosullari` | Kâr payı oranları, Kasko, Finansman Güvence Sigortası ürünlerinin tamamının finansman başvurusu ile birlikte alınması şartına bağlıdır. Vade süreleri araç değeri aralığına göre değişmektedir (0-400.000 TL için 48 ay, 400.001-800.000 TL için 36 ay, 800.001-1.200.000 TL için 24 ay, 1.200.001-2.000.000 TL için 12 ay). Taşıt teminatlı finansmanlarda maksimum vade 36 aydır. Tahsis ücreti finansman tutarının binde 5'idir. | — | llm | 0.70 |

**Belirtilmemiş (7 alan):** Ürün türü, Taksit sayısı, Masraf bilgisi, Ödül miktarı, İndirim oranı, Alışveriş puanı, Kampanya bitişi

**Kanıt zinciri (alıntılar):**

- `kar_payi_orani` ← «48 | 3,42% | 0,50% | 4,48% | 69,16% |»
- `vade_ay_max` ← «000 TL'ye kadar vade 48 ayı, 400.»

**Uygunluk koşulları (muhakeme ajanının girdisi):**

- müşteri tipi: tum_musteriler
- azami tutar: 400.000 TL
- azami vade: 48 ay
- zorunlu ürün: dijital kanal

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
| `finansman_tutari_max` | 400000.0 | tl | kural | 0.60 |
| `vade_ay_max` | 48 | ay | kural | 0.92 |
| `tahsis_ucreti` | 0.5 | yuzde | hibrit | 0.91 |
| `masrafsiz_mi` | False | — | kural | 0.91 |
| `kampanya_avantaji` | Sıfır ve ikinci el araçlar için finansman desteği, 48 aya varan vade seçenekleri, 18 yaşını dolduran herkesin faydalanabilmesi, şubeye gitmeden mobil başvuru imkanı. | — | llm | 0.70 |
| `kampanya_kosullari` | Sıfır araçlarda satış, ikinci elde kasko değeri baz alınarak finansman tutarı belirlenir. İkinci el araçlarda 10 yaşa kadar, sıfır araçlarda 2 yaşa kadar olan araçlar için kullanılabilir. Rehin koyma uygulaması zorunludur. Dosya masrafı (tahsis ücreti) finansman tutarının %0,5'idir. | — | llm | 0.70 |

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

**Kaynak:** Kuveyt Türk Katılım Bankası A.Ş. · [https://www.kuveytturk.com.tr/kendim-icin/finansmanlar](https://www.kuveytturk.com.tr/kendim-icin/finansmanlar) · çekim 24.08.2026

**Girdi (ham metinden):**

> Konut Finansmanları Kuveyt Türk’ün Konut Finansmanı ile siz de hayal ettiğiniz eve kolayca sahip olabilirsiniz! Araç Finansmanları Hemen araç sahibi olabilmek için yapmanız gereken tek şey, Kuveyt Türk'e başvurmak! Alışveriş Finansmanları Kuveyt Türk Alışveriş Finansmanı ihtiyacınız olduğu an yanınızda! İhtiyaç Finansmanları Seyahatten eğitime, hac ve umreden evlilik harcamalarınıza kadar tüm ihtiyaçlarınız için Kuve…

**Yapısal çıktı:**

| Alan | Değer | Birim | Yöntem | Güven |
|---|---|---|---|---|
| `kampanya_turu` | diger | — | llm | 0.80 |
| `kampanya_avantaji` | Metinde konut, araç, alışveriş, ihtiyaç ve sürdürülebilir finansman kategorileri genel olarak tanıtılmıştır ancak belirli bir kampanya, özel oran, vade veya avantaj detayı içermemektedir. | — | llm | 0.70 |

**Belirtilmemiş (14 alan):** Ürün türü, Hedef kitle, Kâr payı oranı, Azami finansman tutarı, Azami vade, Taksit sayısı, Tahsis ücreti, Masraf bilgisi, Masrafsız mı, Ödül miktarı, İndirim oranı, Alışveriş puanı, Kampanya bitişi, Kampanya koşulları

---

## 6. Uygunluk koşulu çıkarılmış kayıt

Kampanyanın KİME açık olduğu yapısal alana çevrilir; müşteri profili ekranındaki muhakeme ajanı bu kısıtları çözer.

**Kaynak:** Kuveyt Türk Katılım Bankası A.Ş. · [https://www.kuveytturk.com.tr/kampanyalar/kendim-icin/musteri-ol-kampanyalari/evlenecek-olan-veya-yeni-evli-ciftlere-kuveyt-turkten-mujde-evlilik-paketi](https://www.kuveytturk.com.tr/kampanyalar/kendim-icin/musteri-ol-kampanyalari/evlenecek-olan-veya-yeni-evli-ciftlere-kuveyt-turkten-mujde-evlilik-paketi) · çekim 20.08.2026

**Girdi (ham metinden):**

> Evlilik süreci, pek çok çift için hayatlarının en özel ve anlamlı dönemlerinden biri olduğu kadar, aynı zamanda planlama, bütçe yönetimi ve karar süreçleri açısından oldukça yoğun ve maliyetli bir dönem olabilir. Kuveyt Türk olarak, siz değerli müşterilerimizin bu özel yolculuğunda yanlarında olmak ve süreci daha kolay, planlı ve keyifli hale getirmek amacıyla Müjde Evlilik Paketi’mizi oluşturduk. Bu paketimizi tasar…

**Yapısal çıktı:**

| Alan | Değer | Birim | Yöntem | Güven |
|---|---|---|---|---|
| `kampanya_turu` | diger | — | llm | 0.80 |
| `hedef_kitle` | yeni_musteri | — | llm | 0.80 |
| `kar_payi_orani` | 1.99 | yuzde | hibrit | 1.00 |
| `finansman_tutari_max` | 100000.0 | tl | hibrit | 0.88 |
| `vade_ay_max` | 48 | ay | kural | 0.92 |
| `odul_miktari` | 7250.0 | tl | kural | 0.85 |
| `indirim_orani` | 50.0 | yuzde | kural | 0.88 |
| `kampanya_avantaji` | Müjde Evlilik Paketi kapsamında; evlilik sürecindeki çeyiz, ev kurma, balayı ve araç ihtiyaçları için vade farksız taksit imkanları, araç ve konut finansmanında puan indirimleri, alışveriş finansmanları, kart harcamalarında mil ve puan kazanımları, fatura talimatı ve davet kodu ile hediye kazanma fırsatları sunulmaktadır. | — | llm | 0.70 |
| `kampanya_bitis` | 2026-09-30 | — | kural | 0.89 |
| `kampanya_kosullari` | Kampanyadan 2026 yılında evlenmiş veya evlenecek olan, KTAILE26 referans kodunu kullanarak görüntülü görüşme veya şubelerden müşteri olan yeni müşteriler yararlanabilir. İhtiyaç Kart kampanyası için başvuru, müşteri olma tarihinden itibaren 30 gün içinde yapılmalıdır. Araç ve konut finansmanı indirimleri için başvuru şubelerden yapılmalıdır. Bazı harcamalar (telekomünikasyon, fatura, gıda vb.) taksitlendirme kapsamı dışındadır. | — | llm | 0.70 |

**Belirtilmemiş (6 alan):** Ürün türü, Taksit sayısı, Tahsis ücreti, Masraf bilgisi, Masrafsız mı, Alışveriş puanı

**Kanıt zinciri (alıntılar):**

- `kar_payi_orani` ← «000 TL’ye kadar %1,99 oranla 12 aya varan taksit fırsatı sunuyor!»
- `finansman_tutari_max` ← «- 2 ay ertelemeli İhtiyaç Kart, yeni müşterilere özel 100.000 TL’ye kadar %1,99 oranla 12 aya varan taksit fırsatı sunuyor!»
- `vade_ay_max` ← «Üstelik başvuru aşamasında 48 aya varan vade seçeneklerinden yararlanabilmek mümkündür.»

**Uygunluk koşulları (muhakeme ajanının girdisi):**

- müşteri tipi: yeni_musteri
- azami tutar: 100.000 TL
- azami vade: 48 ay
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
