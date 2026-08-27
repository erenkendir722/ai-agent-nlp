# Konuşma metni — 4 dakika

Slaytlar `sunum.html`'de; **bu dosya slaytta YAZMAYAN kısımdır.** Slayt dayanağı
gösterir, anlatan sensin.

**Bütçe:** 4 dakika ≈ 520 kelime. Aşağıdaki notlar toplam ~500 kelime.
**Yedi içerik sayfası** → sayfa başına **~34 saniye.**

> Prova ederken süre tut. 4 dakikayı aşan bir sunum, jüri sizi kesmek zorunda
> kaldığında kapanış cümlesini kaybettirir — en pahalı kayıp odur.

---

## 02 · SVARTAL &nbsp;— Eren &nbsp;· 25 sn

> Dokuz katılım bankasının kampanya metinlerini yapısal veriye çeviriyoruz.
> Sistemin tek kuralı var: **kaynağı olmayan hiçbir sayı üretilmez.**
> Bunu slaytta değil, kodda kısıt olarak uyguluyoruz — kanıtı olmayan bir değer
> üretmeye kalkan program çöker.

Rakamları tek tek okuma; jüri zaten görüyor. Yalnız **sıfırı** göster:
sıfır ticari dış servis bağımlılığı.

## 03 · Problem &nbsp;— Eren &nbsp;· 30 sn

> Ortak veri biçimi yok: ne API var, ne indirilebilir tablo. Üstelik aynı bilgi
> bankadan bankaya başka türlü yazılıyor. Şartnamenin kendi örneği bu:
> ilkinde sayı var, **diğer üçünde yok.** Sayı uyduran bir sistem son üçünde
> yanlış oran üretir — ve bankacılıkta yanlış oran, eksik orandan çok daha pahalı.

Sağdaki tabloyu göstererek bitir:

> Bir de şu var: en düşük oran en ucuz ürün demek değil. Manşette iyi görünen
> ürün toplamda **4.204 TL pahalı.** Bu yüzden sıralamayı orana göre değil,
> toplam geri ödemeye göre yapıyoruz.

## 04 · Mimari &nbsp;— Eren &nbsp;· 40 sn

Diyagramı **soldan sağa** anlat, kutuları okuma:

> Toplama Selenium ile; robots kapısı ve iki saniyelik nezaket kuralı burada.
> Türkçe normalizasyondan geçer. Sonra aynı metni **iki katman ayrı ayrı okur**:
> kural katmanı ve dil modeli. Uzlaştırıcı çelişkide karar verir.
> Beş ajan çalışır ve **beşi de dil modeli kullanmaz.**
> Altta duran şerit kanıt zinciri: her değer geldiği cümleyi, adresi ve güvenini
> yanında taşır — baştan sona.

## 05 · Kanıt zinciri ve beş ajan &nbsp;— Samet + Eren &nbsp;· 40 sn

> Kural katmanı uydurma yapamaz ama “bu konut kampanyası mı” diyemez.
> Dil modeli anlamı çözer ama sayıda zayıf. Uzlaştırıcı çelişkide sayısal alanda
> kuralı, anlamsal alanda modeli seçer.

Tablodaki iki satırı göster:

> **“%0” bir boşluk değil, bir beyandır** — “kâr paysız” demek sıfır oran demek.
> Bunu boş bıraktığımızda kampanya karşılaştırmadan tamamen düşüyordu.
> Son satır da önemli: sayfa ücret bilgisi vermiyorsa **boş bırakıyoruz, uydurmuyoruz.**


> “Ajan” demek her adımı bir modele sormak değil. Aritmetiği ve kısıt kontrolünü
> modele yaptırsaydık, halüsinasyon savunmasıyla kazandığımız güveni tek hamlede
> kaybederdik. Dil modeli **tek bir işte** kullanılıyor: metinden alan çıkarmak.
> Gerisi deterministik kod — soldaki koşum kaydında her satırda “kod” yazıyor.

## 06 · Ölçüm &nbsp;— Samet &nbsp;· 40 sn

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

> Sınırları saklamıyoruz. Kâr payı doluluğu %19 — çoğu banka oranı başvuru
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
| “Uygunluk nasıl çıkarılıyor?” | Kayıtların **%70,1'inde** kısıt çıkıyor; zorunlu ürün yükümlülük kanıtına bağlanınca %59'dan **%24,3'e** indi | `src/ajanlar/uygunluk.py` |
| “Kurum içinde çalışır mı?” | Docker üç konteyner; hava boşluğu testinde DNS ve internet kapalıyken çalıştı; **10 sızıntı testi** | `docker-compose.yml` |
| “Model lisansları?” | 89 paket tarandı, kısıtlı lisans **0**; dört model kaynağından teyitli, Llama/Gemma yok | `docs/LISANSLAR.md` |
| “RAG nasıl?” | **12.383** paragraf yerel dosyada, arama numpy nokta çarpımı; harici vektör veritabanı yok | `src/vektor_db.py` |

## Canlı demo

Şartname madde 10 canlı demoyu **zorunlu** tutuyor. `make run` ile aç —
Docker'daki konteyner bayat kalabilir. Demo sırası kenar çubuğunda yazılı:
Genel Bakış → Boru Hattı → Metin Analizi → Banka Profili → Karşılaştırma →
Müşteri Profili → Chatbot.
