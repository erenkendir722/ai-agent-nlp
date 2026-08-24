# Veri Kalitesi Raporu

_Otomatik üretildi: 24.08.2026 12:02 · `make veri-kalitesi`_

> Bu dosya elle düzenlenmez. `make veri-kalitesi` her koşuda yeniden üretir.

> ✅ **Güncel.** Çıkarım 23.08.2026 20:47'de `hibrit` yapılandırmasıyla koştu (590 kayıt) ve o tarihten beri çıkarım kodu değişmedi.

**590 kampanya denetlendi.** 5 kontrol eşiği aştı, 9 kontrol temiz.

## Özet

| | Kontrol | Bulgu | Eşik |
|---|---|---|---|
| 🔴 | Kâr payı oranı > %5 | 1 | 0 |
| ℹ️ | Kâr payı oranı = 0 | 11 | 0 |
| ✅ | Finansman tutarı < 5.000 TL | 0 | 0 |
| ✅ | Finansman tutarı > 10.000.000 TL | 0 | 0 |
| ✅ | Vade > 360 ay veya < 1 | 0 | 0 |
| ✅ | Taksit sayısı > 24 | 0 | 0 |
| ✅ | İndirim oranı > %100 | 0 | 0 |
| 🔴 | Kampanya bitişi geçmişte | 16 | 0 |
| ✅ | Kampanya bitişi 5 yıldan uzak | 0 | 0 |
| 🔴 | Masrafsız işaretli ama tahsis ücreti var | 1 | 0 |
| 🔴 | Banka içi kâr payı aralığı > 5 puan | 1 | 0 |
| ✅ | Aynı URL'den birden çok kayıt | 0 | 0 |
| ✅ | Hiçbir alanı çıkarılamayan kayıt | 0 | 0 |
| 🔴 | Kampanya türü `diger` | 276 | 206 |

## Aykırı değerler

### 🔴 Kâr payı oranı > %5 — 1 kayıt

Katılım bankaları kâr payını aylık ilan eder. Üstü ya yıllık orandır ya da başka bir yüzde (indirim, mil, iade) bu alana sızmıştır.

| Banka | Değer | Kaynak |
|---|---|---|
| 0206 | 11.0 | …efinans.com.tr/tr-tr/bireysel/Sayfalar/gunluk-hesap.aspx |

### ℹ️ Kâr payı oranı = 0 — 11 kayıt

Hata DEĞİL sayılır: vade farksız kampanyalarda kâr payı gerçekten sıfırdır. Sayının ani yükselmesi ayrıştırmanın bozulduğunu gösterir.

### ✅ Finansman tutarı < 5.000 TL — 0 kayıt

Bu tutarın altı kampanya limiti değil, büyük olasılıkla taksit ya da ücret rakamıdır.

### ✅ Finansman tutarı > 10.000.000 TL — 0 kayıt

Bireysel kampanyada beklenmez; dilim tablosundan yanlış hücre alınmış olabilir.

### ✅ Vade > 360 ay veya < 1 — 0 kayıt

Konut finansmanında bile 360 ay üst sınırdır.

### ✅ Taksit sayısı > 24 — 0 kayıt

Kart taksitlendirmesinde üst sınır; aşılıyorsa vade ile karışmıştır.

### ✅ İndirim oranı > %100 — 0 kayıt

Tanımsız değer.

### 🔴 Kampanya bitişi geçmişte — 16 kayıt

Süresi dolmuş kampanya karşılaştırmayı yanıltır. Çok eski bir tarih kampanya tarihi değil, sayfadaki başka bir tarihtir.

| Banka | Değer | Kaynak |
|---|---|---|
| 0203 | 1.0 | …https://www.albaraka.com.tr/tr/urun-ve-hizmet-ucretleri |
| 0205 | 2026-01-01 | …kuveyt-turk-mobilden-pratik-bes-planiniza-2000-tl-hediye |
| 0205 | 2026-07-31 | …icin/kart-kampanyalari/bella-maisonda-25-indirim-firsati |
| 0205 | 2026-02-01 | …icaret-pazaryeri-saticilarina-ozel-vade-farksiz-3-taksit |
| 0206 | 2026-02-26 | …om.tr/tr-tr/bireysel/Sayfalar/urun-hizmet-ucretleri.aspx |
| … | | *11 kayıt daha* |

### ✅ Kampanya bitişi 5 yıldan uzak — 0 kayıt

Ayrıştırma hatası göstergesi.

## Çelişkiler

### 🔴 Masrafsız işaretli ama tahsis ücreti var — 1 kayıt

İki alan birbirini yalanlıyor.

| Banka | Değer | Kaynak |
|---|---|---|
| 0205 | 2026-12-31 | …lari/kuveyt-turkten-yeni-musterilere-ozel-pos-kampanyasi |

### 🔴 Banka içi kâr payı aralığı > 5 puan — 1 kayıt

Aynı bankanın kampanyaları arasında bu kadar fark beklenmez.

| Banka | Değer | Kaynak |
|---|---|---|
| 0206 | 0.00 | 11.00 | 11.00 puan |

### ✅ Aynı URL'den birden çok kayıt — 0 kayıt

Kimlik URL'den deterministik üretilir; mükerrer varsa toplayıcı aynı sayfayı iki farklı adresten almıştır.

## Eksiklik

### ✅ Hiçbir alanı çıkarılamayan kayıt — 0 kayıt

Doluluk sıfırsa sayfa büyük olasılıkla kampanya değildir ya da sitenin yapısı değişmiştir.

### 🔴 Kampanya türü `diger` — 276 kayıt

Sınıflandırılamayan kayıt. Oranın yükselmesi ya toplayıcının kampanya olmayan sayfa getirdiğini ya da sınıflandırmanın kırıldığını gösterir.

| Banka | Değer | Kaynak |
|---|---|---|
| 0203 | 2026-12-31 | …/detay/limitsiz-imm-sigortasinda-vade-farksiz-3-taksit-2 |
| 0203 | doluluk %12 | ….tr/tr/kampanyalar/detay/hizli-doviz-islemleri-yaninizda |
| 0203 | 0.5 | …r/tr/kampanyalar/detay/taksitliocom-alisveris-finansmani |
| 0203 | 2026-12-31 | …detay/restoran-harcamalariniza-ozel-10-indirim-firsati-1 |
| 0203 | doluluk %6 | …/tr/kampanyalar/detay/8-taksit-firsatiyla-kasko-zamani-3 |
| … | | *271 kayıt daha* |

## Alan doluluk oranları

| Alan | Boş | Boş oranı |
|---|---|---|
| `taksit_sayisi` | 590 | %100 |
| `tahsis_ucreti` | 582 | %99 |
| `alisveris_puani` | 574 | %97 |
| `kar_payi_orani` | 558 | %95 |
| `finansman_tutari_max` | 537 | %91 |
| `indirim_orani` | 532 | %90 |
| `odul_miktari` | 465 | %79 |
| `masrafsiz_mi` | 433 | %73 |
| `hedef_kitle` | 416 | %71 |
| `vade_ay_max` | 305 | %52 |
| `kampanya_bitis` | 250 | %42 |
| `kampanya_turu` | 0 | %0 |

## Banka kapsamı

Dengesizlik gizlenmez: bir bankadan 100, diğerinden 16 kampanya varsa karşılaştırma yanlıdır ve bunu bilerek raporlamak fark etmemekten iyidir.

| Kod | Banka | Kampanya | Ort. doluluk | `diger` |
|---|---|---|---|---|
| 0203 | Albaraka Türk Katılım Bankası A.Ş. | 58 | %27 | 31 (%53) |
| 0205 | Kuveyt Türk Katılım Bankası A.Ş. | 117 | %29 | 40 (%34) |
| 0206 | Türkiye Finans Katılım Bankası A.Ş. | 26 | %32 | 7 (%27) |
| 0209 | Ziraat Katılım Bankası A.Ş. | 106 | %29 | 15 (%14) |
| 0210 | Vakıf Katılım Bankası A.Ş. | 30 | %25 | 19 (%63) |
| 0211 | Türkiye Emlak Katılım Bankası A.Ş. | 80 | %28 | 52 (%65) |
| 0212 | Hayat Finans Katılım Bankası A.Ş. | 16 | %26 | 9 (%56) |
| 0213 | T.O.M. Katılım Bankası A.Ş. | 103 | %34 | 53 (%51) |
| 0214 | Dünya Katılım Bankası A.Ş. | 54 | %8 | 50 (%93) |
