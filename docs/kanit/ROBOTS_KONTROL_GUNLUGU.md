# robots.txt Kontrol Günlüğü

_Otomatik üretildi: 2026-08-26T12:11:33+03:00 · `tools/robots_kanit.py`_

Bu günlük **G-14** (veri toplama etiği kanıtı) kapsamındadır;
`docs/kanit/VERI_TOPLAMA_ETIGI.md` onu kanıt olarak gösterir.

Kararları üreten kod, toplamayı yapan kodun ta kendisidir:
`src/collector/toplayici.RobotsBekcisi`. Ayrı bir denetleyici yazılsaydı bu
tablo toplayıcının değil, denetleyicinin davranışını gösterirdi.

## Kullanılan User-Agent

```
TEKNOFEST-2026-SVARTAL-Bot (+kendireren722@gmail.com)
```

Tanım: `src/collector/toplayici.py` · `KULLANICI_AJANI`. Aynı dize hem
robots.txt çekiminde hem sayfa çekiminde gönderilir; kimlik ve iletişim
adresi açıkça beyan edilir, **tarayıcı taklidi yapılmaz**.

Bu koşuda ağa **gerçekten gönderilen** başlıklar (iddia değil, kayıt):

```http
host: www.albaraka.com.tr
accept: */*
accept-encoding: gzip, deflate
connection: keep-alive
user-agent: TEKNOFEST-2026-SVARTAL-Bot (+kendireren722@gmail.com)
```

İstekler arası asgari bekleme: **2 saniye**,
eşzamanlı istek yok. robots.txt daha uzun bir `Crawl-delay` beyan ederse
büyüğü uygulanır (`RobotsBekcisi.bekleme_suresi`).

## Özet

| Alan adı | robots.txt | Beyan edilen crawl-delay | Uygulanan bekleme | Denetlenen URL | İzinli | Çekilmeyen |
|---|---|---|---|---|---|---|
| Albaraka Türk (faal)<br>`www.albaraka.com.tr` | HTTP 200 · 299 bayt | yok | 2 sn | 2 | 2 | 0 |
| Kuveyt Türk (faal)<br>`www.kuveytturk.com.tr` | HTTP 200 · 104 bayt | yok | 2 sn | 3 | 3 | 0 |
| Türkiye Finans (faal)<br>`www.turkiyefinans.com.tr` | HTTP 200 · 721 bayt | yok | 2 sn | 2 | 2 | 0 |
| Ziraat Katılım (faal)<br>`www.ziraatkatilim.com.tr` | HTTP 200 · 2246 bayt | yok | 2 sn | 2 | 2 | 0 |
| Vakıf Katılım (faal)<br>`www.vakifkatilim.com.tr` | HTTP 200 · 346 bayt | yok | 2 sn | 4 | 4 | 0 |
| Emlak Katılım (faal)<br>`www.emlakkatilim.com.tr` | HTTP 200 · 23 bayt | yok | 2 sn | 3 | 3 | 0 |
| Hayat Finans (faal)<br>`hayatfinans.com.tr` | HTTP 200 · 75 bayt | yok | 2 sn | 3 | 3 | 0 |
| TOM Katılım (faal)<br>`tombank.com.tr` | HTTP 404 · robots.txt yok | yok | 2 sn | 2 | 2 | 0 |
| Dünya Katılım (faal)<br>`dunyakatilim.com.tr` | HTTP 200 · 111 bayt | yok | 2 sn | 2 | 2 | 0 |
| Adil Katılım (faaliyete_gecmedi)<br>`www.adilkatilim.com.tr` | HTTP 200 · 1 bayt | yok | 2 sn | 1 | 1 | 0 |
| İktisat Katılım (faaliyete_gecmedi)<br>`www.iktisatkatilim.com.tr` | HTTP 404 · robots.txt yok | yok | 2 sn | 1 | 1 | 0 |
| Halk Katılım (kurulus_asamasinda) | — | — | — | 0 | — | _site yok — kuruluş aşamasında_ |
| Fuzul Katılım (kurulus_asamasinda) | — | — | — | 0 | — | _site yok — kuruluş aşamasında_ |
| Dost Katılım (kurulus_asamasinda) | — | — | — | 0 | — | _site yok — kuruluş aşamasında_ |
| Katılımevim Katılım (kurulus_asamasinda) | — | — | — | 0 | — | _site yok — kuruluş aşamasında_ |
| BDDK — kayıt defteri kaynağı (kampanya için taranmaz)<br>`www.bddk.org.tr` | ⚠️ çekilemedi (ConnectError) | yok | 2 sn | 1 | 0 | 1 |

**Toplam:** 25 URL izinli, 1 URL çekilmiyor.
Çekilmeyen URL toplayıcıya hiç gitmez — kapı `Toplayici._getir` içindedir
ve isteğe çıkmadan önce sorulur. İki farklı sebep aynı sonucu verir:
robots.txt `Disallow` ile reddetmiştir, ya da robots.txt okunamamıştır
(o zaman `izinli_mi` `False` döner — temkinli taraf).

Arşiv kopyaları sunucunun gönderdiği baytlardır; doğrulamak için:
`sha256sum docs/kanit/robots/*.txt` çıktısı aşağıdaki özetlerle eşleşmelidir.

## Alan adı ayrıntıları

### Albaraka Türk (faal)

- robots.txt: `https://www.albaraka.com.tr/robots.txt` → HTTP 200 · 299 bayt
- Arşiv kopyası: [`docs/kanit/robots/www.albaraka.com.tr.txt`](robots/www.albaraka.com.tr.txt) · `sha256:e54ab0a24cefb230…`
- robots.txt'in beyan ettiği sitemap: `https://www.albaraka.com.tr/sitemap.xml`

| URL | Karar | Uygulanan bekleme |
|---|---|---|
| `https://www.albaraka.com.tr` | ✅ izinli | 2 sn |
| `https://www.albaraka.com.tr/tr/kampanyalar` | ✅ izinli | 2 sn |

### Kuveyt Türk (faal)

- robots.txt: `https://www.kuveytturk.com.tr/robots.txt` → HTTP 200 · 104 bayt
- Arşiv kopyası: [`docs/kanit/robots/www.kuveytturk.com.tr.txt`](robots/www.kuveytturk.com.tr.txt) · `sha256:2223315634c91186…`
- robots.txt'in beyan ettiği sitemap: `https://www.kuveytturk.com.tr/sitemap.xml`

| URL | Karar | Uygulanan bekleme |
|---|---|---|
| `https://www.kuveytturk.com.tr` | ✅ izinli | 2 sn |
| `https://www.kuveytturk.com.tr/kampanyalar/kendim-icin` | ✅ izinli | 2 sn |
| `https://www.kuveytturk.com.tr/kampanyalar/isim-icin` | ✅ izinli | 2 sn |

### Türkiye Finans (faal)

- robots.txt: `https://www.turkiyefinans.com.tr/robots.txt` → HTTP 200 · 721 bayt
- Arşiv kopyası: [`docs/kanit/robots/www.turkiyefinans.com.tr.txt`](robots/www.turkiyefinans.com.tr.txt) · `sha256:8206dfaf868e0eec…`
- robots.txt'in beyan ettiği sitemap: `https://www.turkiyefinans.com.tr/sitemap.xml`

| URL | Karar | Uygulanan bekleme |
|---|---|---|
| `https://www.turkiyefinans.com.tr` | ✅ izinli | 2 sn |
| `https://www.turkiyefinans.com.tr/tr-tr/kampanyalar/Sayfalar/default.aspx` | ✅ izinli | 2 sn |

### Ziraat Katılım (faal)

- robots.txt: `https://www.ziraatkatilim.com.tr/robots.txt` → HTTP 200 · 2246 bayt
- Arşiv kopyası: [`docs/kanit/robots/www.ziraatkatilim.com.tr.txt`](robots/www.ziraatkatilim.com.tr.txt) · `sha256:eaeb02cf26815ab0…`
- robots.txt'in beyan ettiği sitemap: `https://www.ziraatkatilim.com.tr/en/sitemap.xml`, `https://www.ziraatkatilim.com.tr/ar/sitemap.xml`

| URL | Karar | Uygulanan bekleme |
|---|---|---|
| `https://www.ziraatkatilim.com.tr` | ✅ izinli | 2 sn |
| `https://www.ziraatkatilim.com.tr/kart-kampanyalari` | ✅ izinli | 2 sn |

### Vakıf Katılım (faal)

- robots.txt: `https://www.vakifkatilim.com.tr/robots.txt` → HTTP 200 · 346 bayt
- Arşiv kopyası: [`docs/kanit/robots/www.vakifkatilim.com.tr.txt`](robots/www.vakifkatilim.com.tr.txt) · `sha256:3b3c490e0489680f…`
- robots.txt'in beyan ettiği sitemap: `https://www.vakifkatilim.com.tr/sitemap-tr.xml`, `https://www.vakifkatilim.com.tr/sitemap-en.xml`

| URL | Karar | Uygulanan bekleme |
|---|---|---|
| `https://www.vakifkatilim.com.tr` | ✅ izinli | 2 sn |
| `https://www.vakifkatilim.com.tr/tr/kendim-icin/kampanyalar` | ✅ izinli | 2 sn |
| `https://www.vakifkatilim.com.tr/tr/kendim-icin/kampanyalar/mevcut-kampanyalar?page=2&kendimIcin=false&isimIcin=false` | ✅ izinli | 2 sn |
| `https://www.vakifkatilim.com.tr/tr/kendim-icin/kampanyalar/mevcut-kampanyalar?page=3&kendimIcin=false&isimIcin=false` | ✅ izinli | 2 sn |

### Emlak Katılım (faal)

- robots.txt: `https://www.emlakkatilim.com.tr/robots.txt` → HTTP 200 · 23 bayt
- Arşiv kopyası: [`docs/kanit/robots/www.emlakkatilim.com.tr.txt`](robots/www.emlakkatilim.com.tr.txt) · `sha256:eaeaa8d3511d1622…`

| URL | Karar | Uygulanan bekleme |
|---|---|---|
| `https://www.emlakkatilim.com.tr` | ✅ izinli | 2 sn |
| `https://www.emlakkatilim.com.tr/tr/bireysel/kampanyalar` | ✅ izinli | 2 sn |
| `https://www.emlakkatilim.com.tr/tr/kurumsal/kampanyalar` | ✅ izinli | 2 sn |

### Hayat Finans (faal)

- robots.txt: `https://hayatfinans.com.tr/robots.txt` → HTTP 200 · 75 bayt
- Arşiv kopyası: [`docs/kanit/robots/hayatfinans.com.tr.txt`](robots/hayatfinans.com.tr.txt) · `sha256:0ba165ca6cae48ec…`
- robots.txt'in beyan ettiği sitemap: `https://www.hayatfinans.com.tr/sitemap.xml`

| URL | Karar | Uygulanan bekleme |
|---|---|---|
| `https://hayatfinans.com.tr` | ✅ izinli | 2 sn |
| `https://hayatfinans.com.tr/kampanyalar` | ✅ izinli | 2 sn |
| `https://hayatfinans.com.tr/isim-kampanyalar` | ✅ izinli | 2 sn |

### TOM Katılım (faal)

- robots.txt: `https://tombank.com.tr/robots.txt` → HTTP 404 · robots.txt yok
- robots.txt **yok**. RFC 9309: dosya yoksa erişim kısıtlanmamıştır;
  yine de kendi hız sınırımız ve kapsam kısıtlarımız uygulanır.

| URL | Karar | Uygulanan bekleme |
|---|---|---|
| `https://tombank.com.tr` | ✅ izinli | 2 sn |
| `https://tombank.com.tr/kampanyalar.html` | ✅ izinli | 2 sn |

### Dünya Katılım (faal)

- robots.txt: `https://dunyakatilim.com.tr/robots.txt` → HTTP 200 · 111 bayt
- Arşiv kopyası: [`docs/kanit/robots/dunyakatilim.com.tr.txt`](robots/dunyakatilim.com.tr.txt) · `sha256:3397ad62438da107…`
- robots.txt'in beyan ettiği sitemap: `https://dunyakatilimsite.blueprint.com.tr/sitemap.xml`

| URL | Karar | Uygulanan bekleme |
|---|---|---|
| `https://dunyakatilim.com.tr` | ✅ izinli | 2 sn |
| `https://dunyakatilim.com.tr/kampanyalar` | ✅ izinli | 2 sn |

### Adil Katılım (faaliyete_gecmedi)

- robots.txt: `https://www.adilkatilim.com.tr/robots.txt` → HTTP 200 · 1 bayt
- Arşiv kopyası: [`docs/kanit/robots/www.adilkatilim.com.tr.txt`](robots/www.adilkatilim.com.tr.txt) · `sha256:01ba4719c80b6fe9…`

| URL | Karar | Uygulanan bekleme |
|---|---|---|
| `https://www.adilkatilim.com.tr` | ✅ izinli | 2 sn |

### İktisat Katılım (faaliyete_gecmedi)

- robots.txt: `https://www.iktisatkatilim.com.tr/robots.txt` → HTTP 404 · robots.txt yok
- robots.txt **yok**. RFC 9309: dosya yoksa erişim kısıtlanmamıştır;
  yine de kendi hız sınırımız ve kapsam kısıtlarımız uygulanır.

| URL | Karar | Uygulanan bekleme |
|---|---|---|
| `https://www.iktisatkatilim.com.tr` | ✅ izinli | 2 sn |

### Halk Katılım (kurulus_asamasinda)

Atlandı: site yok — kuruluş aşamasında.

### Fuzul Katılım (kurulus_asamasinda)

Atlandı: site yok — kuruluş aşamasında.

### Dost Katılım (kurulus_asamasinda)

Atlandı: site yok — kuruluş aşamasında.

### Katılımevim Katılım (kurulus_asamasinda)

Atlandı: site yok — kuruluş aşamasında.

### BDDK — kayıt defteri kaynağı (kampanya için taranmaz)

- robots.txt: `https://www.bddk.org.tr/robots.txt` → ⚠️ çekilemedi (ConnectError)
- Hata ayrıntısı: `ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)`
- **Sonuç: bu alan adı otomatik taranmaz.** `RobotsBekcisi.izinli_mi`,
  robots.txt okunamadığında `False` döner — temkinli taraf seçilir.

| URL | Karar | Uygulanan bekleme |
|---|---|---|
| `https://www.bddk.org.tr` | ⛔ çekilmez — robots.txt okunamadı (temkinli davranış) | 2 sn |

---

## Yeniden üretim

```bash
make kanit-robots        # canlı kontrol; günlüğü ve arşiv kopyalarını yeniler
```

Ağ yokken (hava boşluğu demosunda) günlük metni kayıtlı JSON'dan üretilir:

```bash
python tools/robots_kanit.py --cevrimdisi
```

Günlük **tarihlidir**: banka siteleri robots.txt dosyalarını değiştirir.
Bayatlamasının sorumlusu günlük değil, kontrolü koşmayandır.
