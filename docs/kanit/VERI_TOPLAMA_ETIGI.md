# Veri Toplama Etiği — Kanıt Dosyası

**Görev:** G-14 · **Sorumlu:** Görkem · **Son koşu:** 24 Ağustos 2026

Jüri *"veri toplarken hukuki durum neydi?"* diye sorduğunda açılacak dosya budur.
Buradaki her cümlenin karşısında, onu üreten **komut** ve **kanıt dosyası** var.
Beyan tek başına kanıt değildir: aşağıdaki tabloların hepsi yeniden üretilebilir.

---

## 0. Kanıt dizini — ne nerede

| Kanıt | Neyi gösterir | Nasıl üretilir |
|---|---|---|
| [`bddk-liste.png`](bddk-liste.png) | Banka kayıt defterinin resmî kaynağı (BDDK Katılım Bankaları listesi, 10 banka) | Tarayıcıdan elle alındı |
| [`ROBOTS_KONTROL_GUNLUGU.md`](ROBOTS_KONTROL_GUNLUGU.md) | Her alan adı için robots.txt kararı, crawl-delay, gönderilen başlıklar | `make kanit-robots` |
| [`robots-kontrol-gunlugu.json`](robots-kontrol-gunlugu.json) | Aynı günlüğün makine okunur hâli (HTTP durumu, sha256) | `make kanit-robots` |
| [`robots/`](robots/) | Çekilen robots.txt dosyalarının bayt kopyaları | `make kanit-robots` |
| [`KVKK_TARAMASI.md`](KVKK_TARAMASI.md) | Toplanan metinde kişisel veri taraması (1024 kayıt) | `make kanit-kvkk` |
| `src/collector/toplayici.py` | Nezaket kurallarının **uygulandığı** kod (`RobotsBekcisi`, `NezaketSirasi`) — beyan değil, davranış | — |
| `src/collector/temel_kaziyici.py` | Kapının **çağrıldığı** yer: her kampanya sayfası çekilmeden önce | — |
| `tests/test_toplayici.py` | robots kapısının ve nezaket sırasının testleri | `make test` |
| `tests/test_kaziyicilar.py` | Kazıyıcının reddedilen URL'i gerçekten çekmediğinin testi | `make test` |

Günlükler **tarihlidir**. Banka siteleri robots.txt dosyalarını değiştirir; bayat
bir günlük yanlış bilgi verir. Teslim öncesi son kez koşulur.

---

## 1. Ne toplandı

| | |
|---|---|
| Toplanan ham kayıt | **1024** (`data/raw/*/*.json`) |
| Banka sayısı | **9** (kampanya yayımlayan tüm faal bankalar) |
| Toplama aralığı | 9 – 24 Ağustos 2026 |
| HTTP durumu | 1024 kaydın **tamamı 200** — hata sayfası, yönlendirme kalıntısı yok |
| Saklanan alanlar | banka kodu/adı, URL, çekim tarihi, HTTP durumu, sayfa başlığı, gövde metni |

Her kayıt **kaynak URL'sini ve çekim tarihini taşır**. Bu, izlenebilirliğin
teknik karşılığıdır: yayımlanan veri setindeki her satırın nereden geldiği,
ne zaman alındığı belli.

---

## 2. robots.txt — kontrol edildi, uyuldu

Kazıyıcı her alan adı için robots.txt'i ayrıştırır ve **her istekten önce**
izin sorar (`TemelKaziyici._sayfayi_cek` → `RobotsBekcisi.izinli_mi`).
robots.txt okunamazsa sayfa **çekilmez** — temkinli taraf seçilir. Kapı
tarayıcı adrese gitmeden önce sorulur: reddedilen URL'e `driver.get()` hiç
çağrılmaz (`tests/test_kaziyicilar.py::test_robots_reddettigi_url_hic_cekilmez`).

> **26 Ağu 2026 — aşağıdaki koşu YENİLENMELİ.** Toplama Selenium kazıyıcılarına
> taşınırken denetlenen URL kümesi değişti: Türkiye Finans 1 yerine 14 adresle,
> TOM Katılım gerçek kampanya alan adıyla (`tombankhadi.com`), Vakıf Katılım
> 3 yerine 2 adresle listede. Aşağıdaki sayılar 24 Ağustos koşusuna aittir ve
> yeni kümeyi kapsamaz. Teslimden önce `make kanit-robots` koşulmalı.

24 Ağustos 2026 koşusunun sonucu ([tam günlük](ROBOTS_KONTROL_GUNLUGU.md)):

| | |
|---|---|
| Denetlenen alan adı | 12 (9 faal banka + 2 faaliyete geçmemiş + BDDK) |
| İzinli URL | 24 |
| Çekilmeyen URL | 2 — ikisi de `Disallow` yüzünden değil, **robots.txt okunamadığı** için |
| robots.txt'te `Crawl-delay` beyan eden site | yok — yine de kendi 2 saniyelik alt sınırımız uygulandı |

Çekilmeyen ikisi: `www.iktisatkatilim.com.tr` (TLS el sıkışması zaman aşımına
uğradı — banka henüz faaliyete geçmemiş) ve `www.bddk.org.tr` (bkz. §6).
İkisinde de sonuç aynı: **otomatik tarama yapılmadı.**

Arşiv kopyaları sunucunun gönderdiği baytlardır; `sha256sum docs/kanit/robots/*.txt`
çıktısı günlükteki özetlerle eşleşir. Kanıt "bize göre şöyleydi" değil,
doğrulanabilir.

> Bu yüzden `.gitattributes` içinde `docs/kanit/robots/*.txt -text` kuralı var.
> Takımın bir kısmı `core.autocrlf=true` ile çalışıyor; o ayarla git, CRLF içeren
> dosyaları depoya LF olarak yazar ve özetler tutmaz. Dokuz arşiv dosyasının
> beşi CRLF ile geldiği için sorun kuramsal değildi — kural olmadan özetlerin
> çoğu doğrulanamazdı.

---

## 3. Kullanılan User-Agent — kayıt

```
TEKNOFEST-2026-SVARTAL-Bot (+kendireren722@gmail.com)
```

- **Tanım:** `src/collector/toplayici.py` · `KULLANICI_AJANI`
- **Nerede kullanılır:** hem robots.txt çekiminde hem sayfa çekiminde, tek dize.
- **Gerçekten gönderildiğinin kaydı:** [`ROBOTS_KONTROL_GUNLUGU.md` → «Kullanılan
  User-Agent»](ROBOTS_KONTROL_GUNLUGU.md#kullanılan-user-agent) — o bölümdeki
  başlıklar iddia değil, koşuda ağa çıkan `httpx` isteğinden okunmuştur.

**Tarayıcı taklidi yapılmadı.** Ajan kendini yarışma botu olarak tanıtır ve
iletişim adresi verir; site yöneticisi kim olduğumuzu günlüklerinden görebilir
ve bize ulaşabilir. Bot kimliğini gizleyip Chrome gibi görünmek, robots.txt'e
uymanın anlamını da ortadan kaldırırdı.

---

## 4. Siteye bindirilen yük

| İlke | Değer | Kod |
|---|---|---|
| İstekler arası asgari bekleme | 2 saniye | `ISTEK_ARASI_SANIYE` |
| Eşzamanlı istek | **yok** — alan adı başına tek sıra | `NezaketSirasi.bekle` |
| `Crawl-delay` | robots.txt değeri ile 2 saniyenin **büyüğü** | `RobotsBekcisi.bekleme_suresi` |
| Tarama kapsamı | yalnız `seed_urls`'ten keşfedilen kampanya sayfaları; site geneli taranmaz | `TemelKaziyici.kampanya_urlleri` |
| Sayfa zaman aşımı | 180 sn | `tarayici.SAYFA_ZAMAN_ASIMI` |
| robots.txt zaman aşımı | 10 sn | `ROBOTS_ZAMAN_ASIMI` |

İki haftaya yayılmış 1024 sayfa, saniyede birden az istek demektir. Hiçbir
bankanın sunucusuna ölçülebilir yük binmedi.

---

## 5. Kapsam — neye dokunulmadı

- **Giriş gerektiren hiçbir alan çekilmedi.** İnternet şubesi, mobil uygulama
  uçları, müşteri paneli: hiçbirine istek gitmedi.
- **Kimlik doğrulama, CAPTCHA veya bot koruması aşılmadı.** Bir sayfa JavaScript
  ile yükleniyorsa (Albaraka, Kuveyt Türk, T.O.M.) tarayıcı otomasyonuyla
  zorlanmadı; o kampanyalar **elle** alındı — `data/banks.yaml` notlarında yazılı.
- **Ücretli/abonelikli içerik yok.** Toplanan her sayfa herkese açık.
- **Yalnız aynı alan adı içinde kalındı**; üçüncü taraf sitelere geçilmedi.

---

## 6. BDDK listesi neden elle alındı

Banka kayıt defterinin kaynağı BDDK'nın Kuruluş Listesi'dir
(<https://www.bddk.org.tr/Kurulus/Liste/77>) ve liste **tarayıcıdan elle**
alınmıştır — ekran görüntüsü: [`bddk-liste.png`](bddk-liste.png).

**24 Ağustos 2026 kontrolünde ölçülen durum — iki ayrı gözlem, kaynakları ayrı:**

1. **Toplayıcının gördüğü** ([robots günlüğü](ROBOTS_KONTROL_GUNLUGU.md), BDDK satırı):
   alan adının TLS sertifika zinciri varsayılan sertifika deposuyla
   **doğrulanamıyor** — `CERTIFICATE_VERIFY_FAILED — unable to get local issuer
   certificate`. Toplayıcının HTTP istemcisi bu alan adına **bağlanamıyor**,
   dolayısıyla `izinli_mi` `False` döner ve hiçbir sayfa çekilmez.
2. **Tek seferlik tanı denemesi** (günlükte yok, çünkü toplayıcı bunu yapmaz):
   *"BDDK robots.txt ile bizi reddediyor mu?"* sorusunu yanıtlamak için, sertifika
   doğrulaması kapatılarak `https://www.bddk.org.tr/robots.txt` bir kez istendi →
   **HTTP 404**. Yani sitenin robots.txt dosyası **yok**; bir reddetme de yok.
   Bu istek tanı amaçlıdır, **veri toplama değildir**: hiçbir sayfa alınmadı ve
   toplayıcı kodu sertifika doğrulamasını asla kapatmaz.

> **Düzeltme.** Depoda daha önce *"BDDK robots.txt ile otomatik erişimi
> engelliyor"* yazıyordu. Ölçüm bunu doğrulamadı: ortada bir robots.txt yok;
> engel, doğrulanamayan sertifika zinciri. Kaynak dosyalar (`data/banks.yaml`,
> `docs/VERI_METODOLOJISI.md`) buna göre düzeltildi. **Karar değişmedi**,
> gerekçesi düzeltildi: BDDK sitesi otomatik taranmıyor.

Sertifika doğrulaması kapatılarak listeyi programla çekmek teknik olarak
mümkündü; **yapılmadı**. Doğrulamayı kapatmak bankacılık verisi toplayan bir
projede alışkanlık hâline getirilemez ve elde edilecek şey zaten 10 satırlık bir
listedir — tarayıcıdan elle alınması hem daha dürüst hem daha ucuzdur.

Şartname 5.1 *"manuel veri toplama teknikleri"*ne açıkça izin veriyor; elle alma
bir kısıtın etrafından dolaşmak değil, **kısıta uymanın** yoludur.

**Ekran görüntüsünün kapsamı — dürüstlük notu:** görüntü BDDK'nın *"Katılım
Bankaları (10)"* listesini gösterir, yani **faal** bankaları. Kuruluş/faaliyet
izni almış ama henüz açılmamış beş banka (İktisat, Halk, Fuzul, Dost,
Katılımevim) bu listede yer almaz; onlar BDDK duyurularından alınmış ve izin
tarihleri `data/banks.yaml` notlarına yazılmıştır. Katılımevim satırının
duyuru teyidi hâlâ açıktır (`kod_dogrulandi: false`).

---

## 7. KVKK — kişisel veri toplanmadı

Toplayıcı kişisel veri hedeflemez; ama toplanan şey kamuya açık sayfa metnidir
ve bankalar o sayfalara iletişim bilgisi koyar. Niyet ile sonucun aynı olduğunu
**tarama** gösterir: [`KVKK_TARAMASI.md`](KVKK_TARAMASI.md) (`make kanit-kvkk`).

24 Ağustos 2026 taraması, 1024 kayıt:

| Bulgu | Sonuç |
|---|---|
| Kimliği belirli gerçek kişiye ait veri | **0** |
| Sağlama toplamı tutan T.C. kimlik numarası | **0** (bulunan 11 haneli sayıların hepsi `11111111111` örnek form değeri) |
| Kurumsal e-posta / IBAN / hat | 4 e-posta, 6 IBAN, 1 telefon — tamamı **tüzel kişiye** ait, raporda maskeli |

Kurumsal iletişim bilgisi KVKK anlamında kişisel veri değildir (kişisel veri
kimliği belirli/belirlenebilir **gerçek kişiye** aittir). Yine de kanıt
belgesinde ikinci kez yayımlanmasınlar diye maskelenerek raporlanır.

Taramanın sınırı yazılıdır: desen tabanlıdır, serbest metindeki ad-soyadı
yakalamaz. Müşteri verisinin bu korpusa girmemesinin asıl sebebi taramanın
temizliği değil, **giriş gerektiren hiçbir alana istek gitmemesidir** (§5).

---

## 8. Telif ve yeniden yayım

- **Ham HTML depoya girmez** (`.gitignore`: `data/raw/**/*.html`). Çalışma
  dizininde 516 HTML dosyası duruyor; hiçbiri depoya girmiyor, yayımlanmıyor:
  bankaların sayfa tasarımını yeniden dağıtmak telif riski doğurur.
- **Üst veri JSON'ları depoda kalır** — izlenebilirlik kanıtıdır ve gövde metni
  yalnız çıkarımın dayanağı olarak taşınır.
- Yayımlanan veri seti **yapılandırılmış çıkarım sonucudur** (oran, tutar, vade,
  kampanya türü) ve her satır kaynak URL'sini taşır. Sayfaların kopyası değil,
  onlardan çıkarılmış olgular yayımlanır; her olgunun yanında kaynağı gösterilir.

---

## 9. Şartname bağı

| Madde | Gereklilik | Bu dosyadaki karşılığı |
|---|---|---|
| 5.1 | Veri BDDK listesindeki kuruluşların tümünü içermeli | §6 — kayıt defteri BDDK kaynaklı, 15 banka |
| 5.1 | Python tabanlı toplama / web scraping / **manuel** toplama serbest | §5, §6 — JS ile yüklenen kampanyalar ve BDDK listesi elle alındı |
| 5.9 | Veri güvenliği, müşteri verisi kurum dışına çıkmamalı | §7 — korpusta müşteri verisi yok |
| 9 | Veri setinin yayımlanması | §8 — yayımlanan şey çıkarım sonucu + kaynak URL |

---

## 10. Açık uçlar

- `www.iktisatkatilim.com.tr` TLS el sıkışmasında zaman aşımına uğruyor; banka
  faaliyete geçmediği için kampanya da beklenmiyor. Tekrar denenecek.
- Katılımevim Katılım'ın BDDK duyuru teyidi alınmadı (`kod_dogrulandi: false`).
- Günlükler 24 Ağustos 2026 koşusuna aittir; teslimden önce yeniden koşulmalı.

---

## 11. İletişim ve kaldırma talebi

User-Agent dizesindeki adres gerçek ve izlenen bir adrestir. Bir bankadan
"sayfalarımızı toplamayın" talebi gelirse yapılacak iş bellidir: ilgili banka
`data/banks.yaml` içinde `robots_kontrol` ve `seed_urls` düzeyinde kapatılır,
toplanmış kayıtları veri setinden çıkarılır. Toplama, izin verilen kapsamla
sınırlıdır ve o kapsam koddan okunabilir.

---

## Yeniden üretim

```bash
make kanit           # robots günlüğü + KVKK taraması, ikisi birden
make kanit-robots    # yalnız robots.txt kontrol günlüğü (ağ gerekir)
make kanit-kvkk      # yalnız KVKK taraması (ağ gerekmez)
```
