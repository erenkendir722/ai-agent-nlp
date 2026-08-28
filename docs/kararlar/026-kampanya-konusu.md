# ADR 026 — Kampanya konusu: soru kampanyayı adıyla değil konusuyla gösterir

**Tarih:** 28 Ağustos 2026 · **Durum:** kabul edildi · **Sorumlu:** Eren
**İlgili bulgu:** kullanıcı raporu — doğru banka, yanlış kampanya
**Şema etkisi:** yok (`SEMA_SURUMU` değişmedi)

## Bağlam

```
soru  : «TOM Katılım'ın AKARYAKIT kampanyasında ne kadar iade var?»
cevap : «T.O.M. Katılım Bankası A.Ş. — Hadi Kredi Kartı:
           Kâr payı oranı: aylık %0 · Azami vade: 12 ay · Taksit sayısı: 12
           Ödül miktarı: 250 TL · İndirim oranı: %30»
kaynak: …/a101lerde-meyve-sebze-alisverislerinde-10-nakit-iade

doğrusu: …/hadi-black-kredi-karti-ile-akaryakit-harcamalarina-toplam-500-tl-iade
         `odul_miktari = 500`
```

Doğru kayıt **aynı bankada, aynı kümede** duruyordu. Soruda dört şey vardı —
banka, konu, ölçüt, nicelik — ve sistem yalnız bankayı gördü:

* `_bankalari_bul` 123 TOM kaydını getirdi,
* `sorulan_urun` «akaryakıt» diye bir ürün SINIFI tanımıyor (o sözlük
  konut · taşıt · ihtiyaç · kart · katılma · altın'ı ayırır), küme daralmadı,
* «iade» sözlükte yalnız «nakit iade» olarak yazılıydı, ölçüt de çözülmedi,
* geriye tek hakem kaldı: `doluluk_orani` — **soruyla ilgisiz bir ölçü.**

**Kalkan bunu göremez.** «250» gerçekten yapısal veride var; kalkan «bu sayı
kayıtta var mı?» diye sorar, «bu kayıt, sorulan şey mi?» diye sormaz. Bu,
`yabanci_banka_soruluyor`'un **banka** için kapattığı boşluğun **kampanya**
için açık kalanıydı — ve daha sinsisi: yanlış banka gözle görülür, yanlış
kampanya kaynakça açılmadan görülmez.

## Karar

Kampanya **konusu** dördüncü bir süzgeç olur (`src/rag/konu.py`), banka ·
ürün · segment süzgeçlerinin ardından ve aynı sözleşmeyle: eşleşen kayıt
yoksa küme daralmaz.

### 1. Kampanyanın adı adresinin SON dilimidir

Konu metni = adres yaprağı + `urun_turu`. Üç aday vardı, ikisi **ölçülerek**
elendi:

| kaynak | «akaryakıt» ile eşleşen TOM kaydı | soru dilinden bulaşan |
|---|---|---|
| `ham_metin` (sayfa gövdesi) | 10 | — |
| `kampanya_avantaji` (LLM özeti) | — | güncel 4 · belirli 24 · olarak 13 · sunan 4 |
| **adres yaprağı + ürün türü** | **4** (2 kampanya, ikisi de akaryakıt) | güncel 0 · belirli 0 · olarak 0 · sunan 0 |

Gövde elenir çünkü bir kampanya sayfası başka kampanyalardan da söz eder.
LLM özeti elenir çünkü pazarlama düzyazısıdır ve sorunun kendi sözcüklerini
geri yankılar. Geriye kampanyanın **bankaca verilmiş adı** kalır; kimlik
iddiası için doğru olan da odur.

Yol **öneki** değil yaprağı alınır: önek site gezinmesidir
(`/kendim-icin/kart-kampanyalari/…`) ve «için» tek başına 232 kayda
eşleşiyordu. 979 kaydın **29'unda** yaprak bir ad taşımıyor (kategori
sayfaları); orada süzgeç sessizce devre dışı kalır.

### 2. Ayırt edicilik korpustan ölçülür — `KONU_TAVANI = %3`

Bir sözcük kampanya adlarının büyük bölümünde geçiyorsa bir kampanyayı
adlandırmaz, kampanyacılığı anlatır. Ölçülen sınır (979 kayıt, 1.010 sözcük):

```
varan 114 · fırsatı 103 · özel 77 · harcama 72 · toplam 37 · iade 37
———————————————————— %3 = 29 kayıt ————————————————————
harcamalarınıza 29 · ticari 28 · troy 25 · mobil 25 · worldpuan 20
akaryakıt 15 · sağlık 15 · a101 14 · market 12 · restoran 12 · pegasus 4
```

Sınırın üstü pazarlama kalıbı, altı konu adı. Ağırlık `ln(N/eşleşen)`:
soru birden çok konu sözcüğü taşıdığında hangisinin baskın olduğu elle
sıralanmaz — «kentsel» (2 kayıt) «dönüşüm»den (7 kayıt) kendiliğinden ağır
basar.

### 3. Süzgeç birleşimdir, kesişim değil

«Yalnız belirli sektörlerdeki (ör. **akaryakıt, market, beyaz eşya**)
harcamalara…» sorusunda en çok sözcüğü tutan kayda daralmak 444 kaydı 2'ye
indiriyordu. Kullanıcı üç konuyu **sayıyor**; üçünü birden taşıyan tek
kampanyayı sormuyor. Konulardan birini taşıyan kayıt kümede kalır, kaçını
taşıdığı **sırayı** belirler.

### 4. Konu, ölçütün avantajlı ucundan ÖNCE gelir

Sıra: `konu → sorulan alanı taşımak → güncellik → ölçüt değeri → doluluk`.

«iade» ölçüt olarak çözülünce (§6) sıralama `odul_miktari`'nin avantajlı
ucuna, yani en yüksek ödüle bakar ve TOM'un **10.000 TL**'lik restoran
kampanyası akaryakıt kampanyasının önüne geçer. Kullanıcı bir üstünlük
sormadı, **bir kampanyayı** sordu: konu bir tercih değil kimlik kısıtıdır.

**Güncellik** aynı zincire 28 Ağustos'ta katıldı: Ziraat'in üç market
kampanyasından ikisi arşivde ve seçilen o ikisinden biriydi — aynı tutarı
yazan güncel kayıt kümedeydi. «Süresi dolmuş» beyanı doğruydu ama geçmiş bir
teklifi vitrine koymak jüri havuzunun 27. maddesinin sorduğu şeydir. Basamak
sorulan alanı **taşımanın altında** durur: güncel ama boş bir kayıt uğruna
cevabı olan kaydı düşürmek, bu sefer bilgiyi saklamak olurdu.

### 5. Konu sözcüğü ARTIKTIR — dördüncü bir liste yazılmaz

Konu sözcükleri elle yazılmaz; sorudan, sistemin **zaten çözdüğü** her şey
düşürülerek elde edilir (`_cozulmus_sozcukler`): şema alanları · ürün
anahtarları · ölçüt ipuçları · sözlük terimleri · banka adları · segment
dağarcığı · niyet ipuçları · ay adları. Beşinci bir dağarcık tutmak, onun
diğer dördüyle ayrışmasını garanti ederdi.

Geriye kalanı iki **dilbilgisi kapısı** eler:

* `cekimli_fiil_mi` — «yapılıyor» (4 kampanya adına eşleşiyordu),
  «geldiğinde» (2), «sunduğu». Ek **sonek değil içerme** olarak aranır,
  çünkü Türkçe'de fiilimsi ekinden sonra hâl eki gelir.
* `niteleyen_fiil_mi` — «olan», «veren», «sunan». `sifat_fiil_mi` bu işi
  yapamaz: o kural yalnız «banka» sözcüğünün önündeki sözcüğe bakar, orada
  geniş olmak bedavadır. Her sözcüğe uygulanınca korpusun konu
  dağarcığından **43 sözcük** yutuyordu — `restoran` (10 kampanya),
  `worldpuan` (8), `gümüş` (5) ve bütün ayrılma hâlleri (`mobilden`,
  `mağazadan`, `marketten`). Ayrım gövde uzunluğundan: sıfat-fiil gövdesi
  fiildir ve fiil gövdeleri kısadır (`ol-`, `ver-`, `sun-`), ad ise ekten
  sonra uzun bir gövde bırakır (`restor-`, `mobild-`).

Kapalı sözcük sınıfları (zamir · edat · bağlaç) `ISLEV_SOZCUKLERI`'nde
yazılıdır. Bu bir alan listesi değil bir **sözcük sınıfıdır**: açık sınıflar
(ad, sıfat) sonsuzdur ve yazılamaz, kapalı sınıflar sonludur. Gerekçesi
ölçülmüştür — «Bana bir şiir yaz» ve «Konut finansmanı **için** hangi
belgeler» soruları, kampanya adlarındaki rastlantısal «bana»/«için»
geçişleriyle 979 kaydı 2 kayda indiriyordu.

### 6. «iade» sözlüğe eklendi, koda değil

`docs/TERIM_SOZLUGU.md` → **Nakit iade / iade**. Eğik çizgi sözlükte zaten
eş anlamlı yazım ayıracı; `alan_eslemesi()` ikisini de `odul_miktari`'ne
bağlar. Tanım ve veto («`kar_payi_orani` VETOSU») değişmedi.

### 7. Kapı üç kolda da aynı ölçüyü kullanır

`_cevapla` (chatbot), `kayit_sirala` (kapsam listesi ve metinsel cevabın
yapısal eki) ve orkestratörün profil kolu aynı `konu_agirliklari`
çıktısını paylaşır. Ağırlık **soru başına bir kez** hesaplanır ve aşağı
geçirilir: süzgeç bir ölçüyle daraltıp sıralama başka bir ölçüyle karar
verirse, «akaryakıt» sorusuna akaryakıt kampanyalarını süzüp içinden başka
bir kaydı vitrine koymak olurdu.

### 8. Sohbette KONU bir yuvadır — ve devir sorunun şeklini değiştirmez

Konu süzgeci tek turda doğru çalışıyordu ama sohbet onu unutuyordu; sonuç,
kullanıcının «hafıza sağlıklı çalışmıyor» dediği davranıştı:

```
tur 1: «TOM'un AKARYAKIT kampanyasında ne kadar iade var?»
         -> Hadi Black, akaryakıt kampanyası, 500 TL                    ✓
tur 2: «peki vadesi ne kadar?»
         -> Alışveriş Kredisi, 36 ay · kaynak: …/istikbal               ✗
```

Devralınan yalnız bankaydı; ikinci tur o bankanın 123 kaydına açılıyordu.
Birinci cevap doğru, ikincisi alakasız — kusurun en can sıkıcı biçimi.
`SohbetBaglami.konu` eklendi ([ADR 022](022-sohbet-baglami.md)'nin dört
kuralı aynen geçerli):

* **Yuva ÇÖZÜLMÜŞ sözcükle dolar.** «peki vadesi ne kadar?» sorusundaki
  «peki» dört harflidir ve konu sözcüğü sanılıyordu; korpusta karşılığı
  olmayan sözcük yuvayı dolu göstermez (`gecerli_konu_sozcukleri`). «peki»
  ayrıca `ISLEV_SOZCUKLERI`'ne girdi — söylem belirteci, kapalı sınıf.
* **Ürün adlandırılırsa konu düşer.** «akaryakıt» konuşulurken gelen «peki
  konut finansmanı vadesi?» yeni bir ürüne geçer; iki kısıtı birden
  uygulamak boş küme üretir ve beyan olmayan bir daralmayı iddia ederdi.
  **Banka değişimi konuyu düşürmez** — «peki Kuveyt Türk?» aynı konuyu
  başka bankada sorar ve doğrusu da budur.
* **Beyan gösterim biçimiyle yazılır** (`gosterim_bicimi`): yuva anahtarı
  ASCII, kullanıcıya yazılan «akaryakıt». `segment_dagarcigi`'nin ölçerek
  düzelttiği hatanın aynısı.

Aynı sohbet taramasında ikinci bir kusur çıktı ve o ADR 022'nin **kendi
kuralının** eksik yarısıydı — *«devir bir yuvayı DOLDURUR, sorunun ŞEKLİNİ
değiştirmez»*:

```
tur 1: «Ziraat'in Karaca kampanyası kaç taksit?»   -> Vade: 3 ay
tur 2: «ne kadar indirim var?»
         -> devralınan «Vade» soruya eklendi, cevap yine VADE oldu       ✗
```

Yuvanın boş olup olmadığını `_sorulan_olcut` tek başına söyleyemiyor: o beş
kıyas ölçütünü tanır (`OLCUT_ALANLARI`), kullanıcı ise şemanın herhangi bir
alanını sorabilir. `indirim_orani` o beşten biri değil, dolayısıyla yuva boş
sanılıyor ve kullanıcının **açıkça yazdığı alan** devralınanla eziliyordu.
Kapı `alan_adlandirilmis` ile kapandı; dağarcığı yine türetilmiş: sözlüğün
şema eşlemesi + **etiketlerde yalnız bir kez geçen sözcükler**
(`_benzersiz_sozcukler`'in banka adları için yaptığının aynısı). Sezgi
burada yanıltıyordu — «kampanya» dört etikette geçer ve hiçbir alanı
adlandırmaz, «azami» ikisinde; ikisi de listeden kendiliğinden düşüyor.

## Reddedilen

**Konu sözlüğü yazmak** («akaryakıt», «restoran», «market» → etiket).
`_URUN_ANAHTARLARI`'nın yaptığı iş budur ve orada doğrudur: ürün sınıfı
şemada tanımlı, sonlu bir kümedir. Kampanya konusu değil — korpus her
tazelendiğinde yeni marka, yeni sektör, yeni iş birliği gelir. Liste
yazılsaydı ilk `make crawl` onu geride bırakırdı.

**Kesişim süzgeci (en çok sözcüğü tutan kayıt).** §3'te ölçüldü.

**Gömme ile anlamsal eşleşme.** RAG katmanı zaten var ve koşul sorularında
işini yapıyor. Ama kayıt SEÇİMİ deterministik olmak zorunda: `make eval`
sayılarının ve kalkanın altındaki zemin bu. Gömmeye bağlanan bir süzgeç,
EVREN'in bayt düzeyinde deterministik olmadığı ölçülmüş bir ortamda
(proje kuralı) aynı soruya iki farklı kampanya döndürebilirdi.

**`sifat_fiil_mi`'yi dar kurala çevirip iki yerde birden kullanmak.**
Dar kural «sağlayan banka»yı kaçırır ve ADR 024'ün kapattığı kusur geri
gelirdi. İki kural iki farklı hatayı tutuyor; ölçütleri de farklı olmak
zorunda.

## Ölçüm

| | önce | sonra |
|---|---|---|
| «TOM … akaryakıt kampanyasında ne kadar iade» | A101 meyve-sebze, 250 TL | **akaryakıt kampanyası, 500 TL** |
| «Emlak … kentsel dönüşüm … kâr payı oranı» (jüri 5) | 5 konut kaydının dökümü | **Kentsel Dönüşüm Finansmanı** |
| «Albaraka … kazanılacak Worldpuan» (jüri 4) | otel rezervasyonu kampanyası | **Worldpuan kampanyası** |
| «… akaryakıt, market, beyaz eşya … kart kampanyaları» | ürün-hizmet ücretleri sayfası | **beyaz eşya kampanyası** |
| «Ziraat … market kampanyası» | arşivdeki kayıt | **güncel kayıt** |
| 260 mevcut soruda değişen cevap | — | **6** (4 iyileşme · 1 nötr · 1 tartışmalı) |
| `make chatbot-tarama` | 194 soru, 0 bulgu | **248 soru, 0 bulgu** |
| aynı tarama, konu süzgeci kapalı | — | **49 P9 bulgusu** (nöbetçi boş değil) |
| «TOM akaryakıt» → «peki vadesi ne kadar?» | Alışveriş Kredisi, 36 ay | **akaryakıt kayıtları, «vade yayımlanmamış»** |
| «Karaca kampanyası» → «ne kadar indirim var?» | ECA kombi kampanyası | **Karaca kampanyası** |
| `make chatbot-test` (elle yazılan 31 soru) | 31/31 | 31/31 |
| `eval/kalkan` köken dağılımı | düz 22 · alıntı 44 · yapısal 36 · sistem 9 | **birebir aynı** |
| `make test` | 1654 | **1707** |
| kalkan reddi | 0 | **0** |

Köken dağılımı HEAD'e dönülerek ölçüldü: yanlış blok oranı da denetimsiz
parça oranı da 0,0'da kaldı, yani `docs/SONUCLAR.md`'nin kalkan sayıları bu
değişiklikten etkilenmiyor.

Tarama 54 soru büyüdü ve hepsi **korpustan üretildi**: banka başına en
yaygın üç konu sözcüğü (`konu_sozcukleri_banka_basina`), chatbot'un
süzgeciyle **aynı** kapılardan geçirilerek. Yeni patoloji **P9 — yanlış
kampanya**: cevabın gösterdiği kaynak, soruda adlandırılan konuyu taşımıyor.
Ölçüt kaynağın adresidir, cevabın metni değil — «250 TL» doğru bir sayıdır
ve yine de yanlış kampanyanın sayısıdır.

## Alınan ders

Kalkan bir **doğruluk** kalkanıdır, **ilgi** kalkanı değil. Bir cevabın her
sayısı doğrulanabilir olabilir ve cevap yine de sorulan şeyle ilgisiz
olabilir. Bu depoda ilginin üç kapısı vardı — banka, ürün, segment — ve
üçü de şemada tanımlı, sonlu kümelerdi. Dördüncüsü sonlu değil: kampanyanın
konusu korpusla birlikte değişir. Sonlu olmayan bir kümeyi liste tutarak
değil, **korpusu ölçerek** tanımak gerekiyordu.
