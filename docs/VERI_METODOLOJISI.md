# Veri Metodolojisi

Şartname madde 6'nın *"Kullanılan veri seti ve açıklaması"* (başlık 3) ve
*"Veri ön işleme adımları"* (başlık 4) başlıklarına karşılık gelir.

**Son güncelleme: 26 Ağustos 2026** — sayılar işlenmiş veritabanından alındı.

---

## 0. Veri setinin bugünkü hâli

| | |
|---|---|
| Kampanya kaydı | **1.024** |
| Banka | **9** — BDDK listesindeki **faal** katılım bankalarının tamamı |
| Şema sürümü | `1.2.0` (16 yapısal alan + uygunluk koşulları) |
| Dolu hücre | 4.221 / 16.384 (%25,8) |
| Uygunluk koşulu çıkarılan kayıt | 718 (%70,1) |
| Son çekim | 24 Ağustos 2026 |
| Yayınlanan sürüm | [`data/exports/`](../data/exports/) — CSV + JSONL + [veri kartı](../data/exports/DATASET_CARD.md) |

Banka ve tür bazlı dağılım, dengesizliğin etkisiyle birlikte ayrı bir dosyada:
[`KAPSAM_RAPORU.md`](KAPSAM_RAPORU.md) (`make kapsam` ile yeniden üretilir).

> **Boş hücre her zaman eksik veri değildir.** Kart kampanyasında kâr payı oranı
> yoktur; kampanya sayfası oranı yazmıyorsa sistem `Belirtilmemiş` der. Doluluk
> oranını okurken tür karışımına bakın.

---

## 1. Veri kaynağı ve kapsam

### 1.1 Banka kayıt defteri (şartname 5.1)

Veri seti, BDDK'nın resmî listesindeki katılım bankalarının **tümünü** içerir:
<https://www.bddk.org.tr/Kurulus/Liste/77>

Kayıt defteri 15 kuruluş taşır; bunların **9'u faal**, kalanı faaliyete
geçmemiş ya da kuruluş aşamasındadır (§1.2). Kampanya verisi faal olan
dokuzunun **hepsinde** vardır.

**BDDK listesi manuel olarak alınmıştır.** Şartname 5.1 *"manuel veri toplama
teknikleri"* kullanımına açıkça izin verdiği için liste tarayıcıdan elle
çıkarılmış, `data/banks.yaml` dosyasına işlenmiştir. Ekran görüntüsü:
`docs/kanit/bddk-liste.png`.

**24 Ağustos 2026 ölçümü — gerekçe düzeltildi.** Burada daha önce *"BDDK sitesi
robots.txt ile otomatik erişimi engellemektedir"* yazıyordu; ölçüm bunu
doğrulamadı. Gerçek durum iki gözlemden çıkıyor: (1) toplayıcı `bddk.org.tr`
alan adına **bağlanamıyor**, çünkü TLS sertifika zinciri varsayılan sertifika
deposuyla doğrulanamıyor (`unable to get local issuer certificate`) — kanıt
`docs/kanit/ROBOTS_KONTROL_GUNLUGU.md`, BDDK satırı; (2) tek seferlik tanı
denemesinde (sertifika doğrulaması kapatılarak, yalnız bu soruyu yanıtlamak
için) `/robots.txt` **HTTP 404** döndü — sitenin robots.txt dosyası yok, bir
reddetme de yok. Toplayıcı kodu sertifika doğrulamasını asla kapatmaz.

Karar değişmedi, gerekçesi düzeltildi: **BDDK sitesi otomatik taranmıyor.** Bir
sitenin `robots.txt` dosyası otomatik erişimi reddediyorsa ya da site güvenli
biçimde çekilemiyorsa, o site otomatik olarak taranmaz — kısıtın etrafından
dolaşılmaz.

### 1.2 Faaliyette olmayan bankalar da kayıt defterinde

Kuruluş izni almış ama henüz faaliyete geçmemiş bankaların web sitesinde kampanya
bulunmaz. Bu bankalar listeden **çıkarılmaz**, `durum` alanıyla işaretlenir:

| `durum` | Anlamı | Kampanya beklenir mi? |
|---|---|---|
| `faal` | Faaliyette | Evet |
| `faaliyete_gecmedi` | Kuruluş/faaliyet izni var, henüz açılmadı | Hayır |
| `kurulus_asamasinda` | BDDK kuruluş izni verdi | Hayır |

Bu bankalarda kampanya bulunmaması bir **veri eksikliği değil**, kayıt defterinin
eksiksizliğidir. Toplayıcı bunları atlar ve günlüğe sebebini yazar.

### 1.3 Doğrulanmamış alanlar — dürüstlük notu

`banks.yaml` içinde `kod_dogrulandi: false` işaretli bankaların EFT kodları
bağımsız kaynaktan teyit edilememiştir. Kod yalnız kimlik üretiminde kullanılır
ve çıkarım doğruluğunu etkilemez, ancak yayınlanan veri setinde hatalı olmaması
için BDDK/TBB kaynağından teyit edilecektir.

---

## 2. Toplama disiplini

Toplama **Selenium** ile yapılır ve banka başına bir kazıyıcı vardır
(`src/collector/kaziyicilar/`). Bunun sebebi tercih değil ölçüm: katılım
bankalarının kampanya listeleri JavaScript ile render ediliyor ve «daha fazla
yükle» butonuyla sayfalanıyor; ham HTML'i indirip ayrıştıran bir toplayıcı
kartların çoğunu hiç görmüyor.

Banka başına değişen tek şey **URL keşfidir** — yani kampanya bağlantılarının
o sitede nasıl bulunduğu (`kampanya_urlleri()`). Sayfaların gezilmesi, robots
kapısı, hız sınırı, gövde ayıklama, eleme ve kayıt üretimi ortak taban sınıfta
(`TemelKaziyici`) **tektir**; dokuz kazıyıcıda dokuz kez yazılmaz.

Yeni banka eklemek: `data/banks.yaml`'a bir kayıt (kod, ad, site, `seed_urls`)
ve bir kazıyıcı sınıfı — pratikte tek bir CSS seçicisi ya da XPath.

### 2.1 Uygulanan ilkeler

| İlke | Uygulama |
|---|---|
| `robots.txt` uyumu | Her alan adı için ayrıştırılır; reddedilen URL çekilmez |
| `crawl-delay` | robots.txt değeri ile kendi alt sınırımızın büyüğü uygulanır |
| Hız sınırı | İstekler arası **en az 2 saniye**, eşzamanlı istek yok |
| Kimlik beyanı | `User-Agent: TEKNOFEST-2026-SVARTAL-Bot (+iletişim)` |
| Erişim kapsamı | Yalnız **kamuya açık** sayfalar; giriş gerektiren alan yok |
| Kişisel veri | **Toplanmaz** (KVKK) |
| Kapsam | Yalnız `seed_urls`'ten keşfedilen kampanya sayfaları; site geneli taranmaz |

`robots.txt` okunamadığında sayfa **çekilmez** — temkinli taraf seçilir.

Bu tablo bir beyandır; **kanıtı** `docs/kanit/VERI_TOPLAMA_ETIGI.md` dosyasıdır:
alan adı başına robots.txt kararları, ağa gerçekten gönderilen User-Agent
başlığı ve korpusun KVKK taraması orada, yeniden üretilebilir hâlde durur
(`make kanit`).

### 2.2 URL keşfi

1. Kampanya liste sayfası açılır (`data/banks.yaml` · `seed_urls`)
2. Varsa «daha fazla yükle» düğmesine **kart sayısı artmayı bırakana dek** basılır
   — düğmenin kaybolmasını beklemek yetmiyor, bazı sitelerde son sayfadan sonra
   da görünür kalıyor
3. Varsa sekmeler (bireysel / kurumsal) sırayla açılır
4. Yalnız **görünür** kart bağlantıları alınır: kapalı sekmenin kartları DOM'da
   durur ama o listeye ait değildir (`offsetParent` denetimi)
5. Yinelenenler sıra bozulmadan atılır; her URL bir kez çekilir

Tek istisna **Türkiye Finans**: kampanya listesi gezilebilir bir yapıda
olmadığı için URL'ler `seed_urls` içinde elle tutulur (şartname 5.1 manuel
toplamaya izin veriyor). Bedeli açıktır: yeni kampanya çıkarsa listeye elle
eklenmelidir, otomatik keşif yoktur.

### 2.3 Saklanan veri

Her sayfa için ham anlık görüntü diske yazılır:
- `data/raw/{banka_kodu}/{kampanya_id}.json` — üst veri (URL, tarih, HTTP durum, gövde metni)
- `data/raw/{banka_kodu}/{kampanya_id}.html` — ham HTML

`kampanya_id`, `banka_kodu + URL` üzerinden **deterministik** üretilir. Aynı sayfa
tekrar çekildiğinde aynı kimlik oluşur; yinelenen kayıt üretilmez ve altın set
etiketleri yeni çekimlerde de eşleşir.

Ham HTML dosyaları depoya **commit edilmez** (`.gitignore`): depo şişer ve telif
riski doğar. Üst veri JSON'ları izlenebilirlik kanıtı olarak kalır.

---

## 3. Ön işleme (şartname 5.8)

| Adım | Ne yapar | Nerede |
|---|---|---|
| Gövde ayıklama | Menü, altbilgi, reklamı atıp asıl metni bırakır (`trafilatura`) | `collector/temel_kaziyici.py` |
| Boşluk düzeltme | Görünmez karakterler, çoklu boşluk, NFC normalizasyonu | `preprocessing/normalizasyon.py` |
| Türkçe küçültme | `İ/I/ı/i` doğru eşlemesi | `tr_kucult()` |
| Arama anahtarı | Şapkalı harf, kesme işareti, aksan sadeleştirme | `arama_anahtari()` |
| Kısa sayfa eleme | 200 karakterden kısa gövdeler kampanya sayfası sayılmaz | `EN_AZ_GOVDE_UZUNLUGU` |

### 3.1 Türkçe'ye özgü tuzaklar ve çözümleri

**`.lower()` Türkçe için yanlıştır.**
`"İSTANBUL".lower()` → `"i̇stanbul"` (birleşik nokta kalır), `"IRAK".lower()` →
`"irak"` (olması gereken `"ırak"`). Kendi `tr_kucult()` fonksiyonumuz kullanılır.
Bu tek karar, eşleştirme ve sınıflandırmada saatlerce sürecek sessiz hata avını
önler.

**Binlik/ondalık ayracı.**
Türkçe'de `1.500,50` = bin beş yüz. Standart `float()` bunu `1.5` okur. Ayrı bir
ayrıştırıcı kullanılır; karar kuralı `sayi_ayristir()` içinde belgelidir.

**Şapkalı â.**
"kâr" ve "kar" metinlerde iki türlü de geçer. Aramada birleştirilir, kullanıcıya
gösterimde korunur.

**Kesme işareti.**
`TL'ye`, `Bankası'nın`, `2026'da` tokenizasyonu bozar; arama anahtarında temizlenir.

---

## 4. Normalizasyon (şartname 5.6)

| Girdi varyantları | Normalize değer |
|---|---|
| `%2,05` · `% 2.05` · `2.05 %` · `yüzde 2,05` | `2.05` |
| `500 TL` · `500₺` · `500 Türk Lirası` · `500TL` | `500.0` |
| `50.000 TL` · `50 bin TL` · `1,5 milyon TL` | `50000` · `50000` · `1500000` |
| `120 ay` · `120 aya kadar` · `10 yıl` · `120 taksit` | `vade_ay_max = 120` |
| `31 Aralık 2026` · `31.12.2026` · `2026 yıl sonuna kadar` | `2026-12-31` |
| `masraf alınmaz` · `masrafsız` · `dosya masrafı yok` | `masrafsiz_mi = True` |

Her varyant `tests/test_normalizasyon.py` içinde test edilir. **Yeni bir yazım
varyantı görüldüğünde önce test eklenir, sonra düzeltilir.**

---

## 5. Veri seti yayını

Yayınlanan veri setinde **tam sayfa metni yer almaz**. Bunun yerine:

- Yapısal alanlar (normalize değerler)
- Kaynak URL ve çekim tarihi
- Değerin geldiği **alıntı parçası** (tam metin değil)
- Güven skoru ve çıkarım yöntemi

Bu tercih telif riskini sıfırlar ve izlenebilirliği korur: kullanıcı her değerin
nereden geldiğini görebilir, ama bankanın sayfa içeriği yeniden yayımlanmış olmaz.

**Yayınlanan dosyalar** (`make veri-seti` ile yeniden üretilir):

| Dosya | Kim için | İçerik |
|---|---|---|
| [`data/exports/svartal_kampanyalar.csv`](../data/exports/svartal_kampanyalar.csv) | insan | Düz tablo — her alan + yöntemi + güven skoru |
| [`data/exports/svartal_kampanyalar.jsonl`](../data/exports/svartal_kampanyalar.jsonl) | makine | Kanıt zinciri — değer + birim + ham ifade + kaynak alıntısı + uygunluk koşulları |
| [`data/exports/DATASET_CARD.md`](../data/exports/DATASET_CARD.md) | ikisi | Veri kartı: kapsam, dağılım, toplama yöntemi, bilinen sınırlar |

Ham anlık görüntülerin üst verisi ayrıca `data/raw/` altında depoda durur; taze
bir klonda `make extract` ağ olmadan koşabilir.

---

## 6. Bilinen sınırlar

Dürüst raporlama, eksiği gizlemekten daha değerlidir:

1. **Toplama gerçek bir tarayıcı ister.** JavaScript ile render edilen
   sayfalar 26 Ağustos'ta çözüldü — toplama Selenium'a taşındı (§2), «daha
   fazla yükle» düğmesi kart sayısı artmayı bırakana dek basılıyor. Bedeli:
   `make crawl` için makinede **Chrome** gerekir; bu yüzden Docker imajında
   toplama adımı yoktur (imaj toplanmış veriyi işler). Yeniden toplama yerel
   kurulumda yapılır.
   *Not: burada eskiden "statik HTML çekilir, Playwright kapsam dışı, kalanı
   manuel toplanır" yazıyordu; `data/raw`'daki 1.024 kaydı fiilen Selenium
   kazıyıcıları üretti. Madde düzeltildi.*
2. **Bir bankada otomatik URL keşfi yok.** Türkiye Finans'ın kampanya listesi
   gezilebilir bir yapıda olmadığı için adresler `data/banks.yaml` ·
   `seed_urls` içinde elle tutulur (şartname 5.1 manuel toplamaya izin veriyor).
   Yeni kampanya çıkarsa listeye elle eklenmelidir — eksik kalırsa sistem
   uyarmaz.
3. **Kapsam bankalar arasında dengesiz.** En geniş kapsamlı bankada, en dar
   kapsamlının 13,6 katı kayıt var. Bu bir yanlılık kaynağıdır ve ölçülüp
   yazılmıştır: [`KAPSAM_RAPORU.md`](KAPSAM_RAPORU.md) (şartname 15.1).
   *Not: 9 Ağustos'ta "T.O.M. Katılım'da kampanya sayfası bulunamadı" yazıyordu;
   toplayıcı yeniden koşulduğunda o bankadan 103 kayıt geldi. Madde düzeltildi.*
4. **Kâr payı oranları çoğu kampanya sayfasında yazmaz;** başvuru ekranında
   veya hesaplama aracında bulunur. Bu, veri setinin gerçek bir özelliğidir ve
   `Belirtilmemiş` olarak raporlanır — uydurulmaz. Ölçülen doluluk: %16.
5. **Veri bir anlık görüntüdür.** Kampanyalar sürelidir; her kayıt kendi
   `cekim_tarihi`'ni taşır. Süresi geçmiş kayıtlar `make suresi-gecenleri-ele`
   ile ayıklanabilir.
6. **Yabancı para cinsinden tutarlar TL sayılabiliyor.** Şema
   `finansman_tutari_max` alanını TL olarak tanımlar; "600 Milyon Euro"
   gibi bir ifade sayı olarak çıkarılır ama birimi TL varsayılır. 1.024
   kayıtta bir örneği var ve `make veri-kalitesi` raporunda «> 10.000.000 TL»
   satırında görünür — gizlenmiyor, ama düzeltilmesi şema değişikliği
   gerektirir (yeni bir para birimi boyutu).
7. **Bazı EFT kodları doğrulanmamıştır** (§1.3).
