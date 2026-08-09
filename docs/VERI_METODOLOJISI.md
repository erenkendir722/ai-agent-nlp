# Veri Metodolojisi

Şartname madde 6'nın *"Kullanılan veri seti ve açıklaması"* ve *"Veri ön işleme
adımları"* başlıklarına karşılık gelir.

---

## 1. Veri kaynağı ve kapsam

### 1.1 Banka kayıt defteri (şartname 5.1)

Veri seti, BDDK'nın resmî listesindeki katılım bankalarının **tümünü** içerir:
<https://www.bddk.org.tr/Kurulus/Liste/77>

**BDDK listesi manuel olarak alınmıştır.** BDDK sitesi `robots.txt` ile otomatik
erişimi engellemektedir. Şartname 5.1 *"manuel veri toplama teknikleri"*
kullanımına açıkça izin verdiği için liste tarayıcıdan elle çıkarılmış,
`data/banks.yaml` dosyasına işlenmiştir.

Bu, bir kısıtın etrafından dolaşmak değil, kısıta uymaktır: bir sitenin
`robots.txt` dosyası otomatik erişimi reddediyorsa, o site otomatik olarak
taranmaz.

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

Tek bir jenerik toplayıcı kullanılır — **banka başına özel kod yoktur**.
Farklılıklar `data/banks.yaml` içindeki yapılandırmayla ifade edilir; yeni bir
banka eklemek 8 satır YAML demektir.

### 2.1 Uygulanan ilkeler

| İlke | Uygulama |
|---|---|
| `robots.txt` uyumu | Her alan adı için ayrıştırılır; reddedilen URL çekilmez |
| `crawl-delay` | robots.txt değeri ile kendi alt sınırımızın büyüğü uygulanır |
| Hız sınırı | İstekler arası **en az 2 saniye**, eşzamanlı istek yok |
| Kimlik beyanı | `User-Agent: TEKNOFEST-2026-SVARTAL-Bot (+iletişim)` |
| Erişim kapsamı | Yalnız **kamuya açık** sayfalar; giriş gerektiren alan yok |
| Kişisel veri | **Toplanmaz** (KVKK) |
| Derinlik | Seed URL'den en fazla 2 seviye |

`robots.txt` okunamadığında sayfa **çekilmez** — temkinli taraf seçilir.

### 2.2 URL keşfi

1. `sitemap.xml` varsa oradan aday URL'ler alınır
2. Yoksa seed URL'lerden bağlantı takibi yapılır
3. Adaylar `url_desenleri` ile süzülür (`/kampanya`, `/finansman`, …)
4. Yalnız aynı alan adı içindeki bağlantılar takip edilir

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
| Gövde ayıklama | Menü, altbilgi, reklamı atıp asıl metni bırakır (`trafilatura`) | `collector/toplayici.py` |
| Boşluk düzeltme | Görünmez karakterler, çoklu boşluk, NFC normalizasyonu | `preprocessing/normalizasyon.py` |
| Türkçe küçültme | `İ/I/ı/i` doğru eşlemesi | `tr_kucult()` |
| Arama anahtarı | Şapkalı harf, kesme işareti, aksan sadeleştirme | `arama_anahtari()` |
| Kısa sayfa eleme | 200 karakterden kısa gövdeler kampanya sayfası sayılmaz | `toplayici.py` |

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

---

## 6. Bilinen sınırlar

Dürüst raporlama, eksiği gizlemekten daha değerlidir:

1. **JavaScript ile render edilen sayfalar toplanamaz.** Statik HTML çekilir;
   Playwright bilinçli olarak kapsam dışı bırakıldı. Bu sitelerde manuel toplama
   yedeği kullanılır (şartname 5.1 izin veriyor).
2. **T.O.M. Katılım'da kampanya sayfası bulunamadı** (9 Ağustos 2026 sondajı).
   Manuel inceleme bekliyor.
3. **Kâr payı oranları çoğu kampanya sayfasında yazmaz;** başvuru ekranında
   veya hesaplama aracında bulunur. Bu, veri setinin gerçek bir özelliğidir ve
   `Belirtilmemiş` olarak raporlanır — uydurulmaz.
4. **Bazı EFT kodları doğrulanmamıştır** (§1.3).
