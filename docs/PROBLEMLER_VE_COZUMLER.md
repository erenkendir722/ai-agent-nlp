# Karşılaşılan Problemler ve Çözüm Yaklaşımları

**Dokümantasyon başlığı 8** (şartname madde 6) · Derleyen: Eren · 26 Ağustos 2026

Bu dosya, projenin yol boyunca **gerçekten karşılaştığı** ve çözdüğü problemleri
toplar. Hiçbiri varsayımsal değil: her maddenin belirtisi ölçüldü, sebebi
bulundu, çözümü bir teste ya da bir karar kaydına (ADR) bağlandı.

> **Neden bu kadar ayrıntılı yazıldı?** Bir hatanın nasıl bulunduğu, hatanın
> kendisinden değerlidir. Aşağıdaki maddelerin yarısı, "düzeldi sanılan" bir
> şeyin aslında **yanlış sebepten** düzelmiş olduğunun fark edilmesiyle
> bulundu. Ekip olarak öğrendiğimiz asıl şey buydu.

---

## 1. Dil modeli katmanı

### 1.1 Model boş cevap döndürüyordu

**Belirti:** LLM çağrısı başarılı görünüyor, `content` boş geliyordu
(`done_reason: length`, üretilen token: 1200).
**Sebep:** Qwen3.5 bir *düşünme* modelidir; üretim bütçesinin tamamını akıl
yürütmeye harcıyor, cevaba sıra gelmiyordu.
**Çözüm:** Akıl yürütme kapatıldı (`think=False` / `chat_template_kwargs`).
Kayıt başına süre ~3 dakikadan ~13 saniyeye indi.
**Ders:** Yapısal çıkarımda düşünmeye ihtiyaç yok — şema kısıtı çıktıyı zaten
zorluyor.

### 1.2 Servis katmanında üç sessiz tuzak

EVREN'e (SSB'nin yarışmaya tahsis ettiği model servisi) geçerken üç ayar
**hata vermeden** yok sayılıyordu: `chat_template_kwargs` üst seviyede
olmalıydı, `guided_json` yok sayılıyordu, `max_tokens` sınırı 4096'ydı.
**Çözüm:** Üçü de `src/extraction/saglayici.py` başında yazılı; ayarın işe
yarayıp yaramadığını sınayan bir doğrulama komutu eklendi: `make saglayici-dogrula`.
**Ders:** "Ayarı gönderdim" ile "ayar uygulandı" farklı şeylerdir; ikincisini
ölçmek gerekir.

### 1.3 Aynı girdi, farklı çıktı — determinizm ölçüldü

**Belirti:** `temperature=0` ve sabit tohuma rağmen aynı kayıt farklı sonuç
verdi.
**Sebep:** Ortak vLLM sunucusunda sürekli yığınlama (continuous batching);
istekler başkalarının istekleriyle aynı yığında toplanıyor.
**Ölçüm (25 Ağustos, 98 kayıt, iki koşu):** 784 hücrenin 7'si (%0,9) oynadı;
makro-F1 0,735 ↔ 0,724.
**Çözüm:** Sayı gizlenmedi, **belirsizlik bandı ilan edildi**: `make eval`
sonucu ±0,01 gürültü taşır. Bayt düzeyinde tekrar gerekiyorsa yerel yol
(`make extract-yerel`) aynı kod yolunu çalıştırır.
**Ders:** Ölçemediğin belirsizliği yok sayarsan, gürültüyü iyileşme sanırsın.

### 1.4 Tek takılan istek, bütün öbeği durduruyor

**Belirti (26 Ağustos, teslim öncesi koşu):** 1024 kayıtlık çıkarım 977. kayıtta
dört dakika hiç ilerlemedi; servis ise başka bir istekte 0,7 saniyede cevap
veriyordu.
**Sebep:** Paralel çıkarım **öbekli** çalışıyor ve bir öbek, en yavaş isteği
kadar sürüyor. EVREN ortak bir servis; nadiren tek bir istek okuma zaman
aşımına (300 sn) kadar asılı kalıyor. O sırada 15 işçi boşta bekliyor.
**Bugünkü davranış:** Zaman aşımı sonunda istek düşüyor, kayıt hata olarak
günlüğe yazılıyor ve koşu devam ediyor — 1024 kayıtta **4 kayıt** böyle düştü
(2 zaman aşımı, 1 sunucu hatası, 1 kesik cevap). Düşen kayıtlar sonradan tek
tek yeniden çıkarıldı.
**Ablasyona etkisi ve çözümü:** Beş yapılandırma farklı kayıtları düşürürse
satırlar farklı korpusu ölçer ve tablo geçersiz olur. Eski davranış tabloyu
hiç yazmamaktı (25 dakikalık koşu çöpe giderdi). Artık koşucu her kolda
başarılı kayıtların **kesişimini** ölçüyor ve düşen sayıyı yazıyor — satırlar
tanım gereği aynı korpustan gelir.

---

## 2. Kural katmanı — Türkçe metnin tuzakları

### 2.1 5.000.000 TL "tahsis ücreti" sanıldı

**Belirti:** *"5.000.000 TL'ye kadar finansman. Dosya masrafı alınmaz."*
cümlesinde 5 milyon TL ücret sayıldı, finansman tutarı tamamen kaçırıldı.
**Sebep:** Dışlayıcı sözcük denetimi mesafeye duyarsızdı.
**Çözüm:** Üç katman — dışlayıcı sözcük ancak kapsayıcıdan *daha yakınsa*
reddeder · ücret alanlarında bağlam sözcüğü değerle *aynı cümlede* olmalı ·
olumsuzlanmış ifadelerden ("alınmaz", "ücretsiz") sayı çıkarılmaz.
**Test:** `test_tutar_tahsis_ucreti_ile_karistirilmaz`

### 2.2 Düzelme yanlış sebepten olmuştu

**Belirti:** 2.1'in düzeltmesinden sonra kural **gerçek** tahsis ücretlerini de
reddetmeye başladı.
**Sebep:** Cümle penceresi yarıçapı 0 verilmişti; pencere sayının kendisine
çöküyor, hiçbir bağlam sözcüğü bulunamıyordu. Yani "artık yanlış sayı
çıkarmıyor" doğruydu ama sebebi "hiçbir şey çıkarmıyor"du.
**Nasıl yakalandı:** Sadece "reddediyor mu" değil, **"doğru olanı hâlâ kabul
ediyor mu"** diye soran karşı kontrol testi yazıldığı için.
**Ders — bu proje boyunca tekrar tekrar işe yaradı:** Her kısıt testinin bir
karşı kontrolü olmalı.

### 2.3 Şartnamenin kendi örneği 12 iddiadan 4'ünde hatalıydı

Şartname madde 11'deki üç örnek metin sisteme verildiğinde 4 iddia hatalı
çıktı: "dosya masrafı **alınmamaktadır**" cümlesinden 50.000 TL ücret
çıkarılıyor, "5.000 TL değerinde alışveriş çeki" finansman tutarı sanılıyordu.
**Çözüm:** `-mAktAdır` olumsuzluk kipi sözlüğe eklendi; ödül/finansman ayrımı
bağlam sözcüğüne bağlandı. Hibrit hat şimdi **11/11**.
**Test:** `tests/test_kural.py::TestSartnameMadde11`
**Ders:** Jürinin verdiği örneği çalıştırmak, en ucuz denetimdir.

### 2.4 Türkçe soru eki dört biçimlidir

*"Kuveyt Türk **mü** daha avantajlı?"* sorusu karşılaştırma değil, koşul
sorgusu sayılıyordu — yönlendiricide yalnız "mi daha" kalıbı vardı.
**Çözüm:** Normalizasyon ı→i, ü→u yaptığı için iki varyant yetiyor.
**Ders:** Türkçe'ye özgü biçim bilgisi (ünlü uyumu, ekler) İngilizce için
yazılmış hazır araçlarda yok; kendi normalizasyonumuzu yazmamızın sebebi bu.

---

## 3. Ölçüm katmanı — en pahalı hatalar buradaydı

### 3.1 Halüsinasyon denetimi kendi metriğini bozuyordu

**Belirti:** 11 alan "ham metinde doğrulanamadı" işaretlendi.
**Sebep:** Denetim, sınıflandırma etiketlerini (`konut_finansmani`) ve meşru
özetleri de metinde birebir arıyordu; ikisi de metinde geçmez.
**Çözüm:** Üç alan sınıfına üç ölçüt (sayısal → birebir · etiket → hiç aranmaz,
şema zaten kısıtlıyor · özet → içindeki sayılar aranır).
**Sonuç:** 11 yanlış pozitif → 0.
**Ders:** Yanlış ölçüm, kendi sonucunu **olduğundan kötü** de gösterebilir.

### 3.2 Doğrulama kalkanı meşru cevabı engelliyordu

**Belirti:** *"Albaraka mı avantajlı, Kuveyt Türk mü?"* sorusuna cevap
verilmedi; reddedilen sayılar `40, 25, 20, 15, 0.625`.
**Sebep:** Bunlar veri değil, sistemin **kendi açıklamasıydı** (skor
ağırlıkları ve hesaplanan skor). Kalkan cevaptaki her sayıyı veri iddiası
sanıyordu.
**Çözüm:** Kalkan gevşetilmedi — asıl işi sıkı kalmak. Bunun yerine cevap
parçalarına **köken tipi** verildi (`yapisal` / `alinti` / `sistem` / `duz`) ve
her tip kendi kaynağına karşı denetlenir oldu (ADR 010).
**Ölçüm:** Yanlış blok oranı %14,3 → **%0** (35 meşru soru), uydurma sayı
geçirme oranı değişmedi.
**Ders:** Bir savunma yanlış pozitif veriyorsa çözüm savunmayı zayıflatmak
değil, **neyi denetlediğini düzeltmektir.**

### 3.3 Birimsiz sayı: 0,5 ile 500 TL yan yana duruyordu

`tahsis_ucreti` sütununda «%0,50» ile «500 TL» aynı sütunda, ayırt edilmeden
duruyordu. "En düşük masraf" sıralaması bu ikisini aynı ölçekte karşılaştırıp
yanlış sonuç veriyordu.
**Çözüm:** Şema v1.2.0 — her sayı **birimini taşır** (ADR 009). Mevcut kayıtlar
için LLM'siz bir göç yazıldı (`make birim-goc`).
**Ders:** "Kanıtsız değer üretilemez" ilkesinin bir seviye derini: **birimsiz
sayı taşınamaz.**

### 3.4 Ablasyon tablosu ölçtüğü şeyi ölçmüyordu

**Belirti:** Sunumun en güçlü grafiği olan üç satırlık ablasyon tablosunun
satırları **farklı kod sürümleriyle** koşulmuştu (iki ayrı kod parmak izi).
**Sebep:** Üç yapılandırma üç ayrı elle komutla, farklı zamanlarda
çalıştırılıyordu. Uyarı mekanizması vardı; eksik olan tespit değil koşumdu.
**Çözüm:** Atomik koşucu (ADR 011) — üç (bugün beş) yapılandırma **tek
süreçte**, aralarında insan olmadan koşar; tablo ancak hepsi bitince tek
seferde yazılır.
**Ders:** İnsan hatasını uyarıyla değil, **yapıyla** engelle.

### 3.5 Altın setin ilk sürümü geçersizdi

**Belirti:** Etiketleyiciler arası uyum %34,9 (hedef ≥%85) ve iki kişinin 28
serbest metin alanının 27'si birebir aynıydı.
**Sebep:** Etiketlerin bir bölümü dil modelinden alınmıştı. Cevap anahtarı
modelden gelirse ölçülen şey doğruluk değil, iki modelin benzerliği olur.
**Çözüm:** Altın set sıfırdan kuruldu ve **sadeleştirildi** (ADR 008): 16 alan
yerine çekirdek 8 alan, kişi başı süre ~90 dk → ~25 dk. Bugün **98 örnek**,
uyum %79,2.
**Ders:** Ölçüm aracının bağımsızlığı, ölçümün kendisinden önce gelir.

### 3.6 Yayımlanmış sayılar yeniden üretilemiyordu

**Belirti:** 15 Ağustos'ta yarım kalan bir çıkarım koşusu iyi kayıtların
üstüne yazmış; alan doluluğu %25,7'den %13,7'ye düşmüştü. Ama `SONUCLAR.md`
hâlâ eski, iyi koşunun sayılarını gösteriyordu.
**Çözüm:** Her koşu **kod parmak izi** ve zaman damgasıyla kaydedilir;
`make eval` sayıların bayat olup olmadığını dosyanın başına yazar.
**Ders:** Yayımlanan her sayının, hangi kodun hangi veriyle ürettiğini
söyleyebilmesi gerekir.

### 3.7 Ajanın düzeltmesi, makullük kapısını atlıyordu

**Belirti (26 Ağustos):** Bir katılma hesabı sayfasında `kar_payi_orani`
**%44,00** olarak kayıtlıydı — üstelik 0,84 güvenle ve "hibrit" damgasıyla.
Aylık kâr payı üst sınırı %15; bu değerin geçmemesi gerekiyordu.
**Sebep:** Kural katmanı doğru değeri (%11,00) bulmuştu. Yüklem ajanı "doğru
alan, yanlış hücre" deyip aynı tablonun tepesindeki oranı önerdi ve değer
**yeniden kuruldu**. Ama makullük kapısı uzlaştırmanın hemen ardında çalışıyor,
yani düzeltilmiş değere hiç uygulanmıyordu.
**Neden tanıdık:** Bu, `deger_makul_mu`'nun doğuş sebebiyle **birebir aynı hata
sınıfı** (bkz. 3.1 ve 2.2): bir eleme, hatayı önlemek yerine kaynağını
değiştiriyor. Orada LLM yolundan giriyordu, burada ajan yolundan.
**Çözüm:** Düzeltilmiş değer de aynı kapıdan geçiyor; geçemezse **eski değer
korunuyor** ve reddedilen düzeltme ayrı bir sayaca yazılıyor
(`yuklem_duzeltme_reddi_sayisi`). İki test: biri makul olmayan düzeltmenin
uygulanmadığını, diğeri **doğru düzeltmelerin hâlâ uygulandığını** sınıyor —
karşı kontrol olmadan "artık hiçbir düzeltme yapmıyor" hâline düşebilirdik.

### 3.8 Ağ düştü, tablo eski sayıları yeni damgayla yazdı

**Belirti (26 Ağustos akşamı):** Teslim öncesi son ablasyon koşusu "başarıyla"
bitti. Tablo tamdı, beş satır da aynı kod parmak izini taşıyordu, sayılar
makuldü. **Hepsi bir önceki koşunun sayılarıydı.**
**Sebep:** Koşu sırasında makinenin ağı düştü. LLM'li üç kolun 1024 kaydının
**tamamı** hata verdi; `kaydet([])` hiçbir şey yazmadı ve koşucu, ölçüm için
veritabanını okuyunca **önceki koşudan kalan kayıtları** buldu. Yani ölçüm,
o koşuda hiç üretilmemiş verinin üzerinde yapıldı ve sonuç yeni kod parmak
iziyle damgalandı.
**Neden tehlikeli:** Bütün savunmalar yeşildi. Parmak izi tekti, korpus
büyüklükleri eşitti, tablo eksiksizdi. Yanlış olan tek şey sayılardı.
**Çözüm — iki katman:**
1. Kolun veritabanı koşudan **önce siliniyor**; eski satır hayatta kalamaz.
2. Kayıtların **%90'ından azı** çıkarılabildiyse koşu **patlıyor**
   (`ASGARI_BASARI_ORANI`). Kırpılmış korpusta ölçüm yapmak, ölçmemekten kötüdür.

**Ders:** «Sessiz başarısızlık yasağı» yalnız üretim koduna değil, **ölçüm
koduna da** uygulanmalı. Ölçüm aracının sessizce yanlış cevap vermesi, ölçtüğü
sistemin hata vermesinden daha pahalıdır — çünkü kimse ölçüme itiraz etmez.

---

## 4. RAG ve altyapı

### 4.1 Dört gün "çalışıyor" görünen bir RAG

**Belirti:** Chatbot metin sorularına cevap veriyordu ama kaynaklar alakasızdı.
**Sebep:** Gömme fonksiyonu hata durumunda **sıfır vektörü**, arama ise **boş
liste** döndürüyordu. Sistem hiç çalışmadan çalışıyor göründü.
**Çözüm:** Sessiz yutma yasaklandı — gömme hatası da, arama hatası da fırlatılır.
**Ders:** Sıfır vektörü de uydurma bir değerdir; `Alan(deger=...,
yontem="belirtilmemis")` neden yasaksa o da yasaktır.

### 4.2 Var olmayan bir uç noktaya istek atıyorduk

Kodun varsayılan gömme ucu (`embedding`) EVREN'de **yok**; her çağrı sessizce
404 alıyordu. Jenerik `embed` ucu ise 2560 boyut veriyor, kodun beklediği 1024
ile uyuşmuyordu.
**Çözüm:** Ölçülerek doğru uç seçildi: `bge-m3-embed` → 1024 boyut (BGE-M3
kimliğinin de teyidi), lisans MIT.
**Ders:** Boyut uyuşmazlığı bir lisans tartışmasından önce gelen, ölçülebilir
bir gerçektir.

### 4.3 Tahsis edildiği sanılan vektör veritabanı yoktu

`qdrant.ssyz.org.tr` adresi DNS'te çözülmüyordu ve böyle bir servisin tahsis
edildiğine dair belge yoktu.
**Çözüm:** Harici vektör veritabanı tamamen kaldırıldı (ADR 014). 15.151
paragraf yerel bir `.npz` dosyasında; arama numpy nokta çarpımı — milisaniyeler.
**Yan fayda:** Şartname 5.9'un "dış servise bağımlı olmama" maddesi kendiliğinden
karşılandı.

### 4.4 Docker yazılmıştı ama hiç çalıştırılmamıştı

On-prem puanının (%20) tamamı buna dayanıyordu. 18 Ağustos'ta ilk kez
çalıştırıldı; üç kırık nokta bulundu ve düzeltildi. Bugün üç konteyner sağlıklı,
hava boşluğu ölçümü belgeli.
**Ders:** Yazılmış ama koşulmamış altyapı, olmayan altyapıdır.

### 4.5 Çevrimdışı kurulum paketinin işletim sistemi tuzağı

`pip download` **koşulduğu makinenin** ikili paketlerini indirir. Bizim
koşumuzda 80 paketin 18'i macOS'a özgü çıktı; final bilgisayarı macOS değilse
paket çalışmaz.
**Çözüm:** Tuzak `docs/KURULUM.md`'ye ve görev panosuna yazıldı; paket final
bilgisayarının kendisinde üretilecek.

---

## 5. Ekip ve süreç

### 5.1 Belgeler bayatladı ve yanlış alarm üretti

15 Ağustos denetiminde "kritik" listesinin 6 maddesinden 4'ü aslında
çözülmüştü; pano hâlâ ❌ gösteriyordu. Yanlış alarm, takımı çözülmüş işe
koşturur.
**Çözüm:** Sayı üreten her dosya **otomatik üretilir** hâle getirildi
(`SONUCLAR.md`, `LISANSLAR.md`, `KAPSAM_RAPORU.md`, `CIKTI_ORNEKLERI.md`,
veri kartı). Elle yazılan tek belgeler karar kayıtları ve bu dosyadır.

### 5.2 Şema dört kişinin ortak sözleşmesiydi

Dört kişi aynı şemaya karşı çalışıyordu; sessiz bir alan değişikliği dördünün
işini birden bozardı.
**Çözüm:** Şema donduruldu — **ADR'siz değişmez.** İki kez usulünce değişti
(v1.1.0 uygunluk koşulları, v1.2.0 birim). Kayıtlar kendi şema sürümünü
taşıdığı için eski veri geçerli kalır.

### 5.3 Şemada alan vardı, dolduran yoktu

`uygunluk` alanı 14 Ağustos'ta eklendi ama 26 Ağustos sabahına kadar 1024
kaydın **tamamında boştu**; müşteri profili ekranı her kaydı "uygunluk
çıkarılamadı" uyarısıyla listeliyordu.
**Çözüm:** Uygunluk ajanı yazıldı (LLM'siz, deterministik). Kayıtların
**%70,1'ünde** en az bir kısıt çıkarılıyor.
**Yanlış pozitif kapısı:** İlk sürüm ürün adını metinde görmeyi yeterli sayıyor
ve kayıtların %59'unda "zorunlu ürün" buluyordu. Oysa bir kredi kartı
kampanyasının metninde "kredi kartı" geçmesi, kampanyaya girmek için kredi
kartı **sahibi olmak** gerektiği anlamına gelmez. Yükümlülük kanıtı şartı
eklendi: %59 → %24,3. Aynı şekilde "5.000 TL ve üzeri alışverişlerde" ifadesi
finansman alt sınırı sayılmıyor.
**Ders:** Doldurulmayan bir alan, olmayan bir alandan daha tehlikelidir —
sistem onu doldurduğunu sanır.

---

## Özet — üç yinelenen kalıp

1. **Sessiz başarısızlık en pahalısıdır.** Boş JSON, sıfır vektörü, 404 alan
   uç nokta, yarım kalan koşu: hepsi "çalışıyor" görünüyordu. Bugün sistemin
   her katmanı hata durumunda **patlar**.
2. **Düzelme, doğru sebepten mi düzeldi?** Kısıt testlerinin karşı kontrolü
   olmadan bu soru cevaplanamaz.
3. **Ölçümün kendisi de ölçülmelidir.** Halüsinasyon denetimi, kalkan ve
   ablasyon tablosu — üçü de bir dönem ölçmeleri gereken şeyi ölçmüyordu.

**İlgili belgeler:** [`kararlar/`](kararlar/) (14 ADR) ·
[`HATA_ANALIZI.md`](HATA_ANALIZI.md)
