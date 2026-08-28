# Model Çıktılarının Örnekleri

_Otomatik üretildi: 28.08.2026 10:19 · `make cikti-ornekleri`_

**Şartname madde 6**, proje dokümantasyonunda *«model çıktılarının örnekleri»*
başlığını zorunlu tutuyor. Aşağıdaki çıktıların tamamı **işlenmiş
veritabanından** (921 kayıt) seçilmiştir; hiçbiri elle yazılmadı
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
| `kampanya_turu` | diger | — | llm | 0.80 |
| `urun_turu` | Müjde Evlilik Paketi | — | llm | 0.70 |
| `hedef_kitle` | yeni_musteri | — | llm | 0.80 |
| `kar_payi_orani` | 1.99 | yuzde | hibrit | 0.93 |
| `finansman_tutari_max` | 100000.0 | tl | kural | 0.80 |
| `vade_ay_max` | 48 | ay | kural | 0.92 |
| `taksit_sayisi` | 10 | adet | kural | 0.90 |
| `odul_miktari` | 7250.0 | tl | kural | 0.85 |
| `indirim_orani` | 50.0 | yuzde | kural | 0.88 |
| `kampanya_avantaji` | Evlilik sürecine özel paket; çeyiz, ev kurma, balayı ve araç ihtiyaçlarında vade farksız taksitler, markalarda indirimler, araç ve konut finansmanında puan indirimi, yeni müşteriye özel İhtiyaç Kart oranı, hediye puan ve mil kazanım fırsatları. | — | llm | 0.70 |
| `kampanya_bitis` | 2026-09-30 | — | kural | 0.89 |
| `kampanya_kosullari` | 2026 yılında evlenmiş veya evlenecek olan, KTAILE26 referans kodunu kullanarak görüntülü görüşme veya şubelerden müşteri olan yeni müşteriler. İhtiyaç Kart kampanyası için son 30 gün içinde müşteri olma ve başvuru tarihinden itibaren 30 gün içinde başvuru şartı. Araç ve konut finansmanı için şubeden başvuru zorunluluğu. Miles&Smiles kart kampanyası için 30.04.2026 tarihine kadar mobilden müşteri olma ve kart alma şartı. Fatura talimatı ve davet kodu kampanyaları için mobil veya self noktadan müşteri olma şartı. Bazı harcamalar (telekom, gıda, akaryakıt, fatura vb.) taksitlendirme kapsamı dışındadır. Araç satışlarında taksitlendirme uygulanmaz. Kampanya koşulları değişiklik hakkı saklıdır. | — | llm | 0.70 |

**Belirtilmemiş (4 alan):** Tahsis ücreti, Masraf bilgisi, Masrafsız mı, Alışveriş puanı

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
| `urun_turu` | İhtiyaç Finansmanı | — | llm | 0.70 |
| `kar_payi_orani` | 0.0 | yuzde | kural | 0.93 |
| `finansman_tutari_max` | 50000.0 | tl | kural | 0.86 |
| `vade_ay_max` | 36 | ay | kural | 0.92 |
| `tahsis_ucreti` | 0.5 | yuzde | kural | 0.83 |
| `masrafsiz_mi` | False | — | kural | 0.91 |
| `odul_miktari` | 11000.0 | tl | hibrit | 0.85 |
| `kampanya_avantaji` | Mobilden müşteri olanlara özel %0 kâr payı oranı ile 50.000 TL'ye varan ihtiyaç finansmanı fırsatı ve 11.000 TL'ye varan bonus kazanma imkanı. | — | llm | 0.70 |
| `kampanya_bitis` | 2026-08-31 | — | kural | 0.88 |
| `kampanya_kosullari` | Kampanya 1 Ağustos - 31 Ağustos 2026 tarihleri arasında geçerlidir. Mobilden Türkiye Finanslı olan, son 30 gün içinde müşteri olan, KKB skoru 1875 ve üzerinde olan yeni müşteriler yararlanabilir. 50.000 TL'ye kadar %0 kâr payı oranı sadece 3 ay vadeli sigortalı finansman başvurusu için geçerlidir. Finansman kullandırımı mobil, internet şube ve müşteri iletişim merkezinden yapılabilir. Her müşteri yalnızca 1 defa yararlanabilir. Tahsis ücreti finansman tutarının %0,5'idir (BSMV dahil). Kredi notu ve gelir durumuna göre oranlar değişebilir, banka teklif değiştirme hakkına sahiptir. 50.001 TL üzeri finansmanlar için farklı kâr payı oranları uygulanır (sigortalı/sigortasız ve vadeye göre değişkenlik gösterir). 70.000 TL üzeri finansmanlar için oranlar ürün hizmet ücretleri sayfasında yer alır. Maksimum vade tutara göre 12, 24 veya 36 ay ile sınırlıdır. Sigorta masrafları maliyet tablosuna dahil edilmemiştir. Kampanya süresi bitmeden kullandırılan finansmanlar kampanyalı orandan yararlanır, bitiminden sonra kullandırılanlar güncel orana tabidir. Başvuru reddi durumunda kampanyadan faydalanılamaz. Banka koşulları değiştirme ve kampanyayı durdurma hakkını saklı tutar. 11.000 TL bonus fırsatı mobilden müşteri olanlara özeldir. Kredi kartı başvurusu mobil üzerinden yapılabilir. Detaylı bilgi için 0850 222 22 44 aranabilir veya şubeler ziyaret edilebilir. 10.000 TL ve 60.000 TL bazlı örnek ödeme tabloları hazırlanmıştır. Yasal vergiler ve komisyonlar maliyet tablosuna dahildir. Tahsis ücreti vergiler hariç finansman tutarının binde 5'idir. Sigortalı finansman için kâr payı oranları Finansman Güvence Sigortası alınması durumunda geçerlidir. 50.000 TL'ye kadar sigortasız finansman için 3 ay vadede %1,90 kâr payı oranı uygulanır. 50.001 TL üzeri sigortalı finansman için 3 ay vadede %4,09, 36 ay vadede %3,89 kâr payı oranı uygulanır. 50.001 TL üzeri sigortasız finansman için 3 ay vadede %5,99, 36 ay vadede %5,79 kâr payı oranı uygulanır. Tahsis ücreti finansman fiyatlamasının bir parçasıdır. Banka başvuruları serbestçe değerlendirme, kefil ve ek belge isteme, fiyatlamada değişiklik yapma hakkına sahiptir. Ürün ve hizmet ücretleri sayfasından genel ücret ve masraflara ilişkin bilgiye ulaşılabilir. Kampanya koşulları banka tarafından değiştirilebilir. Kampanya süresi içinde başvurusu yapılan ve onaylanan finansmanlar, kampanya süresi sona ermeden kullandırıldığı takdirde kampanyalı kâr payı oranından yararlanır. Kampanya dönemi bittikten sonra, finansmanlar onaylanmış dahi olsa kullandırım sırasındaki güncel kâr payı oranları geçerli olacaktır. Kampanya kapsamında bankaya iletilen finansman talepleri bankanın kredi ve tahsis politikaları çerçevesinde, müşterinin aylık gelir bilgileri, kredi skoru vb. kriterler göz önünde bulundurularak müşteri özelinde değerlendirilecektir. Bu doğrultuda, başvurunun olumsuz sonuçlanması durumunda kampanyadan faydalanılması mümkün olmayacaktır. Banka uygun görmediği başvuruları reddetme, kampanya koşullarını değiştirme, gerekli görmesi halinde ek bilgi ve belge talebinde bulunma ve kampanyayı durdurma hakkını saklı tutar. Kampanyadan sadece son 30 gün içerisinde mobilden Türkiye Finans müşterisi olan kişiler faydalanabilir. Ekstra 11.000 TL Bonus kazanma Fırsatı! 50.000 TL %0 kar paylı nakit desteğine ek olarak mobilden müşteri olanlara özel 11.000 TL'ye varan bonus kazanma fırsatı seni bekliyor. Ayrıntılı bilgi için tıklayınız. 50.000 TL' ye Kadar Sigortalı İhtiyaç Finansmanı Kâr Oranları ve Maliyet Tablosu Vade | Kar Oranı | Tahsis Ücreti | Aylık Toplam Maliyet | Yıllık Toplam Maliyet | ---|---|---|---|---| 3 | 0,00% | 0,50% | 0,29% | 3,52% | 50.000 TL' ye Kadar Sigortasız İhtiyaç Finansmanı Kâr Oranları ve Maliyet Tablosu Vade | Kar Oranı | Tahsis Ücreti | Aylık Toplam Maliyet | Yıllık Toplam Maliyet | ---|---|---|---|---| 3 | 1,90% | 0,50% | 2,77% | 38,78% | 10.000 TL baz alınarak oluşturulan ihtiyaç finansmanı örnek ödeme tablosunda yasal vergiler toplam komisyon tutarına dahildir. Sigortalı İhtiyaç Finansmanı Kâr Payı Oranları maliyet tablosu hesaplamasında yer alan kar payı oranları; Finansman Güvence Sigortası’nın finansman başvurusu ile birlikte alınması durumunda geçerlidir. 70.000 TL üzeri finansmanlar için kar payı oranları ürün hizmet ücretleri sayfasında yer almaktadır. Finansman tutarı; 125.000TL’ye kadar olması durumunda maksimum vade 36 ayı, 125.001-250.000 TL’ye kadar olması durumunda 24 ayı, 250.000 TL’den fazla olması durumunda 12 ayı aşamaz. Tahsis ücreti finansman fiyatlamasının bir parçasıdır. Tahsis ücreti vergiler hariç finansman tutarının binde 5'i oranındadır. Aylık ve yıllık maliyet oranlarına komisyon ve yasal vergiler dahil edilmiş olup, sigorta masrafları dahil edilmemiştir. Banka finansman başvurularını serbestçe değerlendirme, kefil ve başkaca teminatlar ile ek belge isteme, uygun görmediği başvuruları onaylamama, fiyatlamada değişiklik yapma hakkına sahiptir. Yukarıda yazılı ürünlere sahip olmaksızın kullanılacak finansmana uygulanan genel ücret ve masraflara ilişkin bilgiyi Ürün ve Hizmet Ücretleri sayfamızdan ulaşabilirsiniz. Detaylı bilgi için şubelerimizi ziyaret edebilirsiniz. 50.001 TL Üzeri Sigortalı İhtiyaç Finansmanı Kâr Oranları ve Maliyet Tablosu Vade | Kar Oranı | Tahsis Ücreti | Aylık Toplam Maliyet | Yıllık Toplam Maliyet | ---|---|---|---|---| 3 | 4,09% | 0,50% | 5,63% | 92,88% | 12 | 4,05% | 0,50% | 5,37% | 87,29% | 18 | 4,05% | 0,50% | 5,34% | 86,68% | 24 | 3,99% | 0,50% | 5,25% | 84,72% | 35 | 3,94% | 0,50% | 5,17% | 83,07% | 36 | 3,89% | 0,50% | 5,10% | 81,69% | 50.001 TL Üzeri Sigortasız İhtiyaç Finansmanı Kâr Oranları ve Maliyet Tablosu Vade | Kar Oranı | Tahsis Ücreti | Aylık Toplam Maliyet | Yıllık Toplam Maliyet | ---|---|---|---|---| 3 | 5,99% | 0,50% | 8,11% | 154,81% | 12 | 5,95% | 0,50% | 7,85% | 147,53% | 18 | 5,95% | 0,50% | 7,82% | 146,76% | 24 | 5,89% | 0,50% | 7,73% | 144,23% | 35 | 5,84% | 0,50% | 7,65% | 142,12% | 36 | 5,79% | 0,50% | 7,58% | 140,35% | 60.000 TL baz alınarak oluşturulan ihtiyaç finansmanı örnek ödeme tablosunda yasal vergiler toplam komisyon tutarına dahildir. Sigortalı İhtiyaç Finansmanı Kâr Payı Oranları maliyet tablosu hesaplamasında yer alan kar payı oranları; Finansman Güvence Sigortası’nın finansman başvurusu ile birlikte alınması durumunda geçerlidir. 70.000 TL üzeri finansmanlar için kar payı oranları ürün hizmet ücretleri sayfasında yer almaktadır. Finansman tutarı; 125.000TL’ye kadar olması durumunda maksimum vade 36 ayı, 125.001-250.000 TL’ye kadar olması durumunda 24 ayı, 250.000 TL’den fazla olması durumunda 12 ayı aşamaz. Tahsis ücreti finansman fiyatlamasının bir parçasıdır. Tahsis ücreti vergiler hariç finansman tutarının binde 5'i oranındadır. Aylık ve yıllık maliyet oranlarına komisyon ve yasal vergiler dahil edilmiş olup, sigorta masrafları dahil edilmemiştir. Banka finansman başvurularını serbestçe değerlendirme, kefil ve başkaca teminatlar ile ek belge isteme, uygun görmediği başvuruları onaylamama, fiyatlamada değişiklik yapma hakkına sahiptir. Yukarıda yazılı ürünlere sahip olmaksızın kullanılacak finansmana uygulanan genel ücret ve masraflara ilişkin bilgiyi Ürün ve Hizmet Ücretleri sayfamızdan ulaşabilirsiniz. Detaylı bilgi için şubelerimizi ziyaret edebilirsiniz. Kampanya Hakkında İletişim Kampanya hakkında detaylı bilgi almak için bizimle 0850 222 22 44 Müşteri İletişim Merkezimiz üzerinden iletişime geçebilirsiniz. Henüz kredi kartı sahibi değilseniz kredi kartı başvurunuzu “Türkiye Finans Mobil > Başvurular > Kredi Kartı Başvurusu” adımlarını takip ederek yapabilirsiniz. HEMEN BAŞVUR Bu bağlantı yeni sekmede açılacak. | — | llm | 0.70 |

**Belirtilmemiş (5 alan):** Hedef kitle, Taksit sayısı, Masraf bilgisi, İndirim oranı, Alışveriş puanı

**Kanıt zinciri (alıntılar):**

- `kar_payi_orani` ← «%0 kar payı ile 50.»
- `finansman_tutari_max` ← «- Kampanya kapsamında yukarıdaki tarih aralığında mobilden Türkiye Finanslı olan müşterilere %0 kâr payı oranı ve 3 ay vadeli olarak 50.000 TL’ye kadar İhtiyaç Finansmanı başvurusu…»
- `vade_ay_max` ← «125.000TL’ye kadar olması durumunda maksimum vade 36 ayı, 125.»

**Uygunluk koşulları (muhakeme ajanının girdisi):**

- azami tutar: 50.000 TL
- azami vade: 36 ay

---

## 4. Dolaylı ifade — «avantajlı / özel oranlı»

Şartname 5.2 bu ifadelerin yorumlanmasını istiyor. **Sistem sayı uydurmaz:** metinde sayı varsa çıkarılır, yoksa `kar_payi_orani` «Belirtilmemiş» kalır ve ifadenin kendisi `kampanya_avantaji` alanına yazılır. Aşağıdaki kayıt bu davranışı gösterir.

**Kaynak:** Kuveyt Türk Katılım Bankası A.Ş. · [https://www.kuveytturk.com.tr/kendim-icin/finansmanlar/arac-finansmanlari/dijital-arac-finansmani](https://www.kuveytturk.com.tr/kendim-icin/finansmanlar/arac-finansmanlari/dijital-arac-finansmani) · çekim 24.08.2026

**Girdi (ham metinden):**

> Beğendiğiniz bir araca vakit kaybetmeden sahip olmak mı istiyorsunuz? Kuveyt Türk Dijital Araç Finansmanı ile ihtiyacınız olan finansman desteğine cazip oranlar ve vade seçeneklerinden faydalanarak hızlıca kavuşabilirsiniz. Dijital Araç Finansmanı fırsatlarından yararlanmak için Kuveyt Türk Mobil’i telefonunuza şimdi indirebilirsiniz! Dijital Araç Finansmanı Nedir? Dijital Araç Finansmanı, Kuveyt Türk Mobil aracılığı…

**Yapısal çıktı:**

| Alan | Değer | Birim | Yöntem | Güven |
|---|---|---|---|---|
| `kampanya_turu` | tasit_finansmani | — | llm | 0.80 |
| `urun_turu` | Dijital Araç Finansmanı | — | llm | 0.70 |
| `finansman_tutari_max` | 400000.0 | tl | kural | 0.85 |
| `vade_ay_max` | 48 | ay | kural | 0.92 |
| `tahsis_ucreti` | 0.5 | yuzde | kural | 0.83 |
| `masrafsiz_mi` | False | — | kural | 0.91 |
| `kampanya_avantaji` | Fırsat Ürünleri seçilerek finansman taksit ödemelerine indirim kazanma imkanı; BES, kredi kartı, Kredili Hayat ve Kasko ürünlerinin aktif kullanımı ile taksit indirimleri. | — | llm | 0.70 |
| `kampanya_kosullari` | Fırsat ürünlerinin her ay aktif kullanılması gereklidir. BES ödemesi yapılmaması veya iptal edilmesi, kartın aktif kullanılmaması durumunda indirimden yararlanılamaz. Sıfır araçlarda maksimum 2 yaş, ikinci el araçlarda maksimum 10 yaş sınırı vardır. 0-5 yaş araçlar için maksimum 48 ay, 6-10 yaş araçlar için maksimum 36 ay vade uygulanır. Finansman tutarı araç değerine göre %70, %50, %30 veya %20 oranında sınırlıdır. Dijital başvuru Kuveyt Türk Mobil üzerinden yapılır. Anlaşmalı firmalardan araç alınması durumunda Kampanya No paylaşımı gereklidir. Notere giderek araç satış işlemi tamamlanmalıdır. Mevcut bir kredi kartı veya ürün varsa indirim hakkı kazanılır. Pasife düşen ürünlerin tekrar aktifleştirilmesi durumunda indirim devam eder. Rehin tesis masrafı ödenmelidir. Dosya masrafı (tahsis ücreti) finansman tutarının binde 5'i (0,5%) olarak hesaplanır. 2.000.001 TL ve üzeri araçlar için kullandırım yapılmaz. Mevcut müşteriler ve yeni müşteriler yararlanabilir (yeni müşteriler mobil üzerinden müşteri olabilir). Vade seçenekleri 48 aya kadar değişir. Hesaplama aracı kullanılabilir. Geri ödeme planı görüntülenebilir. Başvuru adımları mobil üzerinden takip edilebilir. Satıcı bilgileri girilmelidir. Belge kontrolleri yapılır. Satıcıya ödeme gerçekleşir. Hayallerinizdeki araca sahip olabilirsiniz. Dijital Araç Finansmanı, Kuveyt Türk Mobil aracılığıyla başvurabileceğiniz, finansman işlemlerinizin hızlıca tamamlanmasına imkan veren bir araç finansmanı türüdür. Hem sıfır hem 2. el araçlar için Dijital Araç Finansmanı başvurusu yapabilirsiniz. Satın almayı planladığınız aracın kullanım durumuna bağlı olarak 48 aya kadar vade seçeneklerinden faydalanabilirsiniz. Dijital Araç Finansmanı’na Nasıl Başvurulur? Kuveyt Türk Mobil üzerinden dakikalar içerisinde Dijital Araç Finansmanı'na başvurabilirsiniz. Kuveyt Türk müşterisi değil misiniz? O halde, Kuveyt Türk Mobil'den hızlıca Kuveyt Türk müşterisi olabilirsiniz. Hemen ardından dijitale özel oranlarla, ihtiyacınız olan finansman desteğine kavuşabilirsiniz. Dijital Araç Finansmanı Özellikleri Dijital Araç Finansmanı, kendine has özellikleri ile ön plana çıkar: - Sıfır ve ikinci el araçlar için finansman başvurusu yapılabilir. - 2. el araç finansmanlarında 10 yaşa kadar finansman desteği sağlanmaktadır. Ancak, 0-5 yaş araçlar için maksimum 48 ay, 6-10 yaş araçlar için maksimum 36 ay taksit ile finansman kullanılabilir. - Dijital Araç Finansmanı’da kullanılabilecek maksimum finansman tutarı ve vade seçenekleri için sıfır araçlarda satış değeri ve 2. el araçlarda ise kasko değeri dikkate alınmaktadır. Detaylı bilgi için aşağıdaki tabloyu inceleyebilirsiniz. Kasko/Satış Değeri | Finansman Tutarının Taşıt Tutarına Oranı | Vade Üst Sınırı (Ay) | ---|---|---| 0 - 400.000 TL | %70 | 48 | 400.001 - 800.000 TL | %50 | 36 | 800.001 - 1.200.000 TL | %30 | 24 | 1.200.001 - 2.000.000 TL | %20 | 12 | 2.000.001 TL ve üzeri | %0 | Kullandırım yapılmaz. | Dijital Araç Finansmanı Hesaplama Aracı Vade süresine göre ne kadarlık geri ödeme yapılacağı hakkında fikir sahibi olmayı düşündüğünüzde hesaplama aracını kullanabilirsiniz. Dijital Araç Finansmanı’na Nasıl Başvuru Yapılabilir? Dijital Araç Finansmanı başvurunuzu, Kuveyt Türk Mobil aracılığıyla kolayca gerçekleştirebilirsiniz. Başvuru aşamasında takip etmeniz gereken adımlar şunlardır: - Kuveyt Türk Mobil’e giriş yapılır ve sağ menüden Finansman > Finansman Başvurusu > Araç Finansmanı Başvurusu seçilir. - Satın alınmak istenen araç bilgileri girilir. - Kullanılmak istenen finansman bilgileri girilir. - Kuveyt Türk ile anlaşmalı olan firmalardan araç alınacağı durumda firmalar, müşteri ile Kampanya No paylaşır. Kuveyt Türk Mobil’deki Kampanya No alanı bu numara ile doldurulduğunda anlaşmanın içerdiği fırsatlardan yararlanılır. - Fırsat Ürünleri seçilerek finansman taksit ödemelerinize indirim kazanılır. Başvuru anında seçilen fırsat ürünlerinin işlemleri Kuveyt Türk Mobil ve şube üzerinden tamamlanabilir. - Geri Ödeme Planı görüntülenir. Geri Ödeme Planı’nda aylık ödenecek tutar, toplam ödenecek tutar ve aylık ödeme planının detayları görülebilir. - Geri Ödeme Planı incelendikten sonra gelir bilgileri doldurulur. - Girilen bilgiler onaylandığında finansman başvurusu tamamlanır. - Satıcı bilgileri (şahıs, bayi) girilir. - Masraflar görüntülenir ve tutarlara onay verilir. - Finansman sözleşmeleri okunarak onay verilir. - Notere giderek araç satış işlemi tamamlanır ve belgeler Kuveyt Türk Mobil’e yüklenir. - Belge kontrollerinden sonra satıcıya ödeme gerçekleşir. Tebrikler, hayallerinizdeki araca artık siz de sahipsiniz! Fırsat Ürünleri İndirimi Hayalinizdeki aracı satın almak için dijital finansman desteğini tercih ettiğinizde birçok avantajdan yararlanabilirsiniz. İşte birbirinden cazip Dijital Araç Finansmanı avantajları: - Başvurunuz sırasında seçtiğiniz fırsat ürünlerini her ay aktif kullanmanız halinde bir sonraki taksit ödemenize indirim yansıyacaktır. Kazandığınız indirimle beraber size özel sunduğumuz taksit tutarını Geri Ödeme Planı safhasında görebilirsiniz. - Seçtiğiniz fırsat ürünlerinin başvurusunu Kuveyt Türk Mobil üzerinden ya da şube aracılığı ile yapabilirsiniz. Ayrıca, Kuveyt Türk Mobil’e giriş yaparak sol menüden Finansman > Finansman Başvurusu > Başvurularım sayfasında aktif finansmanınızı seçtiğinizde sağ üst köşede bulunan hediye paketi ikonuna tıklayarak tüm ürünler için başvurunuzu tamamlayabilirsiniz. - Fırsat ürünleri sayfasında Bireysel Emeklilik Sistemi’ni seçmeniz halinde her ay sizin belirlediğiniz tutarda Bireysel Emeklilik Sistemi’nize yatırım yaparsanız bu üründen kazanacağınız indirim tutarı bir sonraki taksitinizden düşecektir. BES’inize bir ay ödeme yapmamanız veya iptal etmeniz durumunda bir sonraki ayın taksit indiriminden faydalanamayacaksınız. - Kredi kartından indirim kazanabilmeniz için kartınızı her ay aktif olarak kullanmanız gerekmektedir. Kartınızdan ödeme yapmadığınız ya da kartınızı iptal ettiğininiz durumda bir sonraki ayın taksit indirimden yararlanamayacaksınız. - Eğer finansman başvurusu sırasında mevcutta bir kredi kartınız varsa ürününüz varsa bu üründen indirim almaya hak kazanırsınız. - Kredili Hayat ürünün finansman taksitleriniz boyunca aktif olması taksitlerinize indirim yansıtacaktır - Kasko ürünün finansman taksitleriniz boyunca aktif olması taksitlerinize indirim yansıtacaktır. - Seçtiğiniz ürünleri pasife düştükten sonra tekrardan kullanarak aktifleştirirseniz taksit ödemelerinize indirim yansımaya devam edecektir. Cazip indirim fırsatlarıyla araç finansmanı desteği için hemen Kuveyt Türk Mobil’i indirin ve başvurunuzu yapın! Düşlediğiniz araca sahip olmak için daha fazla beklemeyin! Dijital Araç Finansmanı Hakkında Sıkça Sorulan Sorular Dijital Araç Finansmanı sürecini tamamlamak için gerekli belgeler nelerdir? Dijital Araç Finansmanı başvurusu için sıfır araçlarda proforma fatura, ikinci el araçlarda ise yeni ruhsat, noter satış sözleşmesi ve kasko poliçesi gereklidir. Dijital Araç Finansmanı kaç yaşındaki taşıtlar için kullanılabilir? Sıfır araçlarda maksimum 2 yaşına kadar, ikinci el araçlarda ise maksimum 10 yaşına kadar olan araçlar için finansman kullanılabilir. Kaç TL tutarında Dijital Araç Finansmanı kullanılabilir? Kaç TL tutarında Dijital Araç Finansmanı kullanılabileceği sıfır araçlarda satış, ikinci elde ise kasko değerleri göz önünde bulundurularak hesaplanır. Bu koşula uygun olarak finansman desteği limitleri şu şekilde sıralanır: - Satış / kasko değeri 400 bin TL ve altında olan araçlar için maksimum %70 - Değeri 400.001 ila 800.000 TL aralığındaki araçlar için maksimum %50 - Değeri 800.001 ila 1.200.000 TL aralığındaki araçlar için maksimum %30 - Değeri 1.200.001 ila 2.000.000 TL aralığındaki araçlar için maksimum %20 Araç finansmanlarında araca rehin konulması zorunlu mudur? Kuveyt Türk, satın alınan araca teminat karşılığı olarak rehin koyar. Bu süreç, Noterler Birliği’ne ödenmek amacıyla rehin tesis masrafı temin edildikten sonra tarafımızdan yürütülür. Finansman ödemesi bittiğinde araç üzerindeki rehin otomatikman kalkar. Dosya masrafı nedir? Finansman tahsis ücreti finansman tutarının 0,5%’i (binde beş) olacak şekilde hesaplanmaktadır. | — | llm | 0.70 |

**Belirtilmemiş (8 alan):** Hedef kitle, Kâr payı oranı, Taksit sayısı, Masraf bilgisi, Ödül miktarı, İndirim oranı, Alışveriş puanı, Kampanya bitişi

**Kanıt zinciri (alıntılar):**

- `vade_ay_max` ← «Satın almayı planladığınız aracın kullanım durumuna bağlı olarak 48 aya kadar vade seçeneklerinden faydalanabilirsiniz.»
- `tahsis_ucreti` ← «Finansman tahsis ücreti finansman tutarının 0,5%’i (binde beş) olacak şekilde hesaplanmaktadır.»

**Uygunluk koşulları (muhakeme ajanının girdisi):**

- müşteri tipi: segment
- segment: emekli
- azami tutar: 400.000 TL
- azami vade: 48 ay
- zorunlu ürün: kredi kartı

---

## 5. Eksik bilgili kayıt — «Belirtilmemiş» demek

Kampanya sayfası az bilgi veriyorsa sistem **boş bırakır**. Şartname madde 11'in tablosu da bu ifadeyi kullanıyor; uydurmak yerine bilmediğini söylemek doğru davranıştır.

**Kaynak:** Türkiye Emlak Katılım Bankası A.Ş. · [https://www.emlakkatilim.com.tr/tr/kurumsal/finansmanlar/nakdi-finansman/e-fatura-teminatli-finansman](https://www.emlakkatilim.com.tr/tr/kurumsal/finansmanlar/nakdi-finansman/e-fatura-teminatli-finansman) · çekim 27.08.2026

**Girdi (ham metinden):**

> E-Fatura Teminatlı Finansman × E-Fatura Teminatlı Finansman Nedir? E-Fatura Teminatlı Finansman; Kobi, Ticari ve Kurumsal segmentteki müşterilerimizin finansman ihtiyacını karşılamak adına E-Fatura alacaklarını teminat olarak göstererek, ihtiyaç duydukları finansmana ulaşabilecekleri murabaha temelli finansman ürünüdür. E-Fatura Teminatlı Finansman ile tedarikçilere, mal alan alıcı firmalara sattıkları mal veya hizme…

**Yapısal çıktı:**

| Alan | Değer | Birim | Yöntem | Güven |
|---|---|---|---|---|
| `kampanya_turu` | finansman | — | llm | 0.80 |
| `urun_turu` | E-Fatura Teminatlı Finansman | — | llm | 0.70 |
| `kampanya_kosullari` | Kobi, Ticari ve Kurumsal segmentteki müşterilere yöneliktir. E-Fatura alacaklarının teminat gösterilmesi gerekir. Fatura üzerinde vade (son ödeme tarihi) bulunması şarttır. Ek teminata ihtiyaç duyulmaz. Murabaha temelli bir üründür. Operasyonel süreçleri kısaltır ve fiziki evrak sirkülasyonunu ortadan kaldırır. Detaylı bilgi için şubeye başvurulmalıdır. | — | llm | 0.70 |

**Belirtilmemiş (13 alan):** Hedef kitle, Kâr payı oranı, Azami finansman tutarı, Azami vade, Taksit sayısı, Tahsis ücreti, Masraf bilgisi, Masrafsız mı, Ödül miktarı, İndirim oranı, Alışveriş puanı, Kampanya avantajı, Kampanya bitişi

**Uygunluk koşulları (muhakeme ajanının girdisi):**

- müşteri tipi: segment
- segment: KOBİ

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
| `urun_turu` | Sağlam Kart | — | llm | 0.70 |
| `kar_payi_orani` | 0.0 | yuzde | kural | 0.80 |
| `vade_ay_max` | 9 | ay | kural | 0.92 |
| `taksit_sayisi` | 3 | adet | kural | 0.90 |
| `odul_miktari` | 1000.0 | tl | hibrit | 0.85 |
| `indirim_orani` | 20.0 | yuzde | kural | 0.87 |
| `kampanya_avantaji` | Halalbooking'e ilk defa kayıt olanlara 1000 TL değerinde indirim, 9 aya varan taksit avantajı, seçili otellerde %20'ye varan indirim, private hizmetler ve ücretsiz havaalanı transferi ayrıcalıkları | — | llm | 0.70 |
| `kampanya_bitis` | 2026-12-31 | — | kural | 0.89 |
| `kampanya_kosullari` | İndirim kampanyası Halalbooking'e ilk defa bu link üzerinden kaydolan müşteriler için geçerlidir ve 10,000 TL ve üzerindeki rezervasyonlarda kullanılabilecektir. Harcamaların ödeme esnasında taksitlendirilmesi gerekmektedir. Yurtdışı tatil harcamaları taksitlendirilememektedir. KKTC için yapılan harcamalara vade farksız 3 taksit fırsatı sunulmaktadır. Kampanyadan faydalanabilmek için ilgili linkler üzerinden e-posta adresi ile kayıt olduktan sonra Sağlam Kart üzerindeki kart numarasının ilk 6 hanesi ile Halalbooking'e kaydolmak gerekmektedir. Kredi kartı segmentine göre ilk yıl Gold, Platin veya Diamond üyelik kazanılması gereklidir. 31 Aralık 2026 tarihine kadar geçerlidir. Banka koşulları önceden haber vermeden değiştirebilir veya kampanyayı sonlandırabilir. | — | llm | 0.70 |

**Belirtilmemiş (6 alan):** Hedef kitle, Azami finansman tutarı, Tahsis ücreti, Masraf bilgisi, Masrafsız mı, Alışveriş puanı

**Kanıt zinciri (alıntılar):**

- `vade_ay_max` ← «- 31 Aralık 2026 tarihine kadar yapacağınız tatil harcamalarınızda 9 aya varan taksit avantajından yararlanabilir, Halalbooking’e kaydolurken 1000 TL değerinde indirim kazanabilirs…»
- `odul_miktari` ← «ızda 9 aya varan taksit avantajından yararlanabilir, Halalbooking’e kaydolurken 1000 TL değerinde indirim kazanabilirsiniz. - İndirim kampanyası Halalbooking’e ilk def»
- `indirim_orani` ← «- Kredi kartı segmentinize göre ilk yıl Gold, Platin veya Diamond üyelik kazanarak seçili otellerde %20'ye varan indirim, private hizmetler ve ücretsiz havaalanı transferi ayrıcalı…»

**Uygunluk koşulları (muhakeme ajanının girdisi):**

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
