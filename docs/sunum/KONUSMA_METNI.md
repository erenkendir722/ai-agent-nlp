# Konuşma metni — 4 dakika

Slaytlar `sunum.html`'de; **bu dosya slaytta YAZMAYAN kısımdır.** Slayt dayanağı
gösterir, anlatan sensin.

**Bütçe:** 4 dakika ≈ 520 kelime. Aşağıdaki notlar toplam ~500 kelime.
**Yedi anlatılan sayfa** (02–08; 09 kapanış) → sayfa başına **~34 saniye.**

> Prova ederken süre tut. 4 dakikayı aşan bir sunum, jüri sizi kesmek zorunda
> kaldığında kapanış cümlesini kaybettirir — en pahalı kayıp odur.

---

## 02 · Problem &nbsp;— Eren &nbsp;· 35 sn

> Katılım bankacılığında standart API yok. Üstelik aynı bilgi bankadan bankaya
> başka türlü yazılıyor: şartnamenin kendi örneğinde **ilkinde sayı var, diğer
> üçünde yok.** Sayı uyduran bir sistem son üçünde yanlış oran üretir.

Sağdaki tabloyu göster:

> Bir de şu tuzak var: en düşük oran en ucuz ürün demek değil. Manşette iyi
> görünen teklif toplamda **4.204 TL daha pahalı.** Bu yüzden sıralamayı orana
> göre değil, toplam maliyet fonksiyonuna göre yapıyoruz.

## 03 · Kapsam &nbsp;— Görkem &nbsp;· 30 sn

> Dokuz faal katılım bankasının tamamı, 1.019 kampanya, 1.761 geçen test, sıfır
> ticari dış servis bağımlılığı. Her kayıt **16 alanlı bir kanıt zinciri** taşır:
> kaynak URL, dayandığı cümle, güven skoru ve hangi katmandan çıktığı.

Dengesizliği kendin söyle, jüri sormadan:

> Dağılım dengesiz — en geniş kapsam en darın **11,5 katı.** Ölçtük ve raporladık.
> Sıralamayı bozmuyor, çünkü motor tekil ürünleri karşılaştırıyor, banka
> ortalaması almıyor.

## 04 · Mimari &nbsp;— Eren &nbsp;· 40 sn

Diyagramı **soldan sağa** anlat, kutuları okuma:

> Toplama Selenium ile; robots kapısı ve iki saniyelik nezaket kuralı burada.
> Türkçe normalizasyondan geçer. Sonra aynı metni **iki katman ayrı ayrı okur**:
> kural katmanı ve dil modeli. Uzlaştırıcı çelişkide karar verir.
> Beş ajan çalışır ve **beşi de dil modeli kullanmaz.**
> Altta duran şerit kanıt zinciri: her değer geldiği cümleyi, adresi ve güvenini
> yanında taşır — baştan sona.

## 05 · Karşılaştırma &nbsp;— Samet &nbsp;· 30 sn

> Kural motoru hiç uydurmuyor — halüsinasyon sıfır — ama az alan dolduruyor ve
> «bu bir konut kampanyası mı» sorusunu hiç cevaplayamıyor. Dil modeli çok alan
> dolduruyor ama isabeti düşük. **Üçüncü kolon ikisinin birleşimi.**

Dürüstlük notunu atlama — jüri bunu sorar:

> Bu tablo yalnız **ölçtüğümüz** üç yapılandırmayı kıyaslıyor. Vektör-RAG taban
> çizgisi kurmadık; ölçmediğimiz bir sistemle kıyaslama yapmıyoruz.

## 06 · Ablasyon &nbsp;— Samet &nbsp;· 40 sn

> Beş yapılandırmayı aynı kodla, aynı korpusta, tek koşuda ölçtük.
> Kural tek başına sayıda iyi ama az alan doldurur. Model çok doldurur, isabeti
> düşük. **Birlikte 0,79**, yüklem ajanı eklenince **0,82**.

Sonra son iki satırı işaret et — bu slaydın asıl noktası:

> Bu iki satırın makro-F1'i **aynı**. Eleştirmen ajanını kapattığımızda skor hiç
> değişmiyor, ama halüsinasyon %0,39'dan %0,51'e çıkıyor.
> **Eleştirmenin işi skoru yükseltmek değil, uydurmayı kesmek.**

Sağdaki kutuyu atlama:

> Aralığı da söylüyoruz. 92 örnekle tek ondalık hane üzerinden övünmek
> yanlış bir kesinlik iddiasıdır.

## 07 · Asistan &nbsp;— Esra &nbsp;· 30 sn

> Sorulan soru: Kuveyt Türk'ün konut finansmanında kâr payı oranı ne?
> Sistem vadeyi, tahsis ücretini ve masrafı veriyor; kâr payı oranı için
> **“Belirtilmemiş”** diyor — çünkü o sayfada yayımlanmamış.
> **Uydurmuyor, ama bildiğini de saklamıyor.**
> Altta “0 LLM çağrısı” yazıyor: bu cevabı bir dil modeli üretmedi.

## 08 · Sonuç &nbsp;— Eren &nbsp;· 25 sn

Tabloyu okuma, sınırlara geç:

> Sınırları saklamıyoruz. Kâr payı doluluğu %18 — çoğu banka oranı başvuru
> ekranında veriyor, biz uydurmak yerine “Belirtilmemiş” diyoruz.
> Kapsam dengesiz, ölçtük ve rapor ettik.
> **Sakladığımız an, sakladığımız şeyin dışındaki her sayı da şüpheli hâle gelir.**

Kapanış:

> Kaynağı olmayan sayı üretmeyen bir sistem. Kod, veri seti, ölçüm betikleri ve
> her kararın gerekçesi depoda, açık kaynak.

---

## Yedek slayt YOK — soruya sözlü cevap

8 sayfaya inerken yedek sayfalar kaldırıldı. Aşağıdaki kanıtlar slaytta
görünmüyor ama **depoda duruyor**; soru gelirse ekrandan değil ağızdan cevaplanır,
gerekirse depo açılır.

| Soru gelirse | Cevap | Nerede |
|---|---|---|
| “Veriyi nasıl topladınız, izin aldınız mı?” | robots kapısı, 2 sn nezaket, 16 alan adının kararı günlükte, KVKK taraması temiz | `docs/kanit/` |
| “Şartnamedeki örneği denediniz mi?” | İlk koşuda 12 iddiadan 4'ü hatalıydı; düzeltildi, teste bağlandı — **11/11** | `tests/test_kural.py` |
| “Sıralamayı neye göre yapıyorsunuz?” | Beş kriter, ağırlığı kullanıcı belirler (%40/%25/%20/%15), formül açık | `src/comparison/` |
| “Uygunluk nasıl çıkarılıyor?” | Kayıtların **%87,1'inde** kısıt çıkıyor; zorunlu ürün yükümlülük kanıtına bağlanınca %59'dan **%24,3'e** indi | `src/ajanlar/uygunluk.py` |
| “Kurum içinde çalışır mı?” | Docker üç konteyner; hava boşluğu testinde DNS ve internet kapalıyken çalıştı; **10 sızıntı testi** | `docker-compose.yml` |
| “Model lisansları?” | 89 paket tarandı, kısıtlı lisans **0**; dört model kaynağından teyitli, Llama/Gemma yok | `docs/LISANSLAR.md` |
| “RAG nasıl?” | **15.916** paragraf yerel dosyada, arama numpy nokta çarpımı; harici vektör veritabanı yok | `src/vektor_db.py` |

## Canlı demo

Şartname madde 10 canlı demoyu **zorunlu** tutuyor. `make run` ile aç —
Docker'daki konteyner bayat kalabilir. Demo sırası kenar çubuğunda yazılı:
Genel Bakış → Boru Hattı → Metin Analizi → Banka Profili → Karşılaştırma →
Müşteri Profili → Chatbot.
