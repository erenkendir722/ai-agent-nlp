# Veri Kalitesi Raporu

_Otomatik üretildi: 26.08.2026 16:45 · `make veri-kalitesi`_

> Bu dosya elle düzenlenmez. `make veri-kalitesi` her koşuda yeniden üretir.

> ✅ **Güncel.** Çıkarım 26.08.2026 16:25'de `hibrit` yapılandırmasıyla koştu (1020 kayıt) ve o tarihten beri çıkarım kodu değişmedi.

**1024 kampanya denetlendi.** 6 kontrol eşiği aştı, 8 kontrol temiz.

## Özet

| | Kontrol | Bulgu | Eşik |
|---|---|---|---|
| 🔴 | Kâr payı oranı > %5 | 1 | 0 |
| ℹ️ | Kâr payı oranı = 0 | 130 | 0 |
| ✅ | Finansman tutarı < 5.000 TL | 0 | 0 |
| 🔴 | Finansman tutarı > 10.000.000 TL | 3 | 0 |
| ✅ | Vade > 360 ay veya < 1 | 0 | 0 |
| ✅ | Taksit sayısı > 24 | 0 | 0 |
| ✅ | İndirim oranı > %100 | 0 | 0 |
| 🔴 | Kampanya bitişi geçmişte | 97 | 0 |
| 🔴 | Kampanya bitişi 5 yıldan uzak | 1 | 0 |
| ✅ | Masrafsız işaretli ama tahsis ücreti var | 0 | 0 |
| 🔴 | Banka içi kâr payı aralığı > 5 puan | 1 | 0 |
| ✅ | Aynı URL'den birden çok kayıt | 0 | 0 |
| ✅ | Hiçbir alanı çıkarılamayan kayıt | 0 | 0 |
| 🔴 | Kampanya türü `diger` | 433 | 358 |

## Aykırı değerler

### 🔴 Kâr payı oranı > %5 — 1 kayıt

Katılım bankaları kâr payını aylık ilan eder. Üstü ya yıllık orandır ya da başka bir yüzde (indirim, mil, iade) bu alana sızmıştır.

| Banka | Değer | Kaynak |
|---|---|---|
| 0206 | 11.0 | …efinans.com.tr/tr-tr/bireysel/Sayfalar/gunluk-hesap.aspx |

### ℹ️ Kâr payı oranı = 0 — 130 kayıt

Hata DEĞİL sayılır: vade farksız kampanyalarda kâr payı gerçekten sıfırdır. Sayının ani yükselmesi ayrıştırmanın bozulduğunu gösterir.

### ✅ Finansman tutarı < 5.000 TL — 0 kayıt

Bu tutarın altı kampanya limiti değil, büyük olasılıkla taksit ya da ücret rakamıdır.

### 🔴 Finansman tutarı > 10.000.000 TL — 3 kayıt

Bireysel kampanyada beklenmez; dilim tablosundan yanlış hücre alınmış olabilir.

| Banka | Değer | Kaynak |
|---|---|---|
| 0203 | doluluk %31 | …smanlar/ticari-gayri-nakdi-finansman/jet-teminat-mektubu |
| 0203 | doluluk %31 | …ansmanlar/kobi-gayri-nakdi-finansman/jet-teminat-mektubu |
| 0205 | 0.49 | …nsman/savunma-sanayii-baskanligi-finansman-destek-paketi |

### ✅ Vade > 360 ay veya < 1 — 0 kayıt

Konut finansmanında bile 360 ay üst sınırdır.

### ✅ Taksit sayısı > 24 — 0 kayıt

Kart taksitlendirmesinde üst sınır; aşılıyorsa vade ile karışmıştır.

### ✅ İndirim oranı > %100 — 0 kayıt

Tanımsız değer.

### 🔴 Kampanya bitişi geçmişte — 97 kayıt

Süresi dolmuş kampanya karşılaştırmayı yanıltır. Çok eski bir tarih kampanya tarihi değil, sayfadaki başka bir tarihtir.

| Banka | Değer | Kaynak |
|---|---|---|
| 0206 | 2023-08-05 | …r/kampanyalar/Sayfalar/gunluk-hesap-vade-kampanyasi.aspx |
| 0211 | 2026-06-30 | …kampanya/paraf-ile-ds-damatta-6-aya-varan-taksit-firsati |
| 0211 | 0.0 | …er-notebookta-pesin-fiyatina-12-aya-varan-taksit-firsati |
| 0213 | 2026-07-30 | …-limitini-artir-harcamalarindan-toplam-500-tl-iade-kazan |
| 0213 | 2026-07-30 | …-limitini-artir-harcamalarindan-toplam-500-tl-iade-kazan |
| … | | *92 kayıt daha* |

### 🔴 Kampanya bitişi 5 yıldan uzak — 1 kayıt

Ayrıştırma hatası göstergesi.

| Banka | Değer | Kaynak |
|---|---|---|
| 0205 | 0.0 | …icin/kart-kampanyalari/bella-maisonda-25-indirim-firsati |

## Çelişkiler

### ✅ Masrafsız işaretli ama tahsis ücreti var — 0 kayıt

İki alan birbirini yalanlıyor.

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

### 🔴 Kampanya türü `diger` — 433 kayıt

Sınıflandırılamayan kayıt. Oranın yükselmesi ya toplayıcının kampanya olmayan sayfa getirdiğini ya da sınıflandırmanın kırıldığını gösterir.

| Banka | Değer | Kaynak |
|---|---|---|
| 0203 | 0.0 | …/detay/limitsiz-imm-sigortasinda-vade-farksiz-3-taksit-2 |
| 0203 | 2026-08-31 | ….com.tr/tr/kampanyalar/detay/emekli-promosyon-kampanyasi |
| 0203 | 0.5 | …r/tr/kampanyalar/detay/taksitliocom-alisveris-finansmani |
| 0203 | 2026-12-31 | …detay/restoran-harcamalariniza-ozel-10-indirim-firsati-1 |
| 0203 | doluluk %6 | …/tr/kampanyalar/detay/8-taksit-firsatiyla-kasko-zamani-3 |
| … | | *428 kayıt daha* |

## Alan doluluk oranları

| Alan | Boş | Boş oranı |
|---|---|---|
| `taksit_sayisi` | 1024 | %100 |
| `alisveris_puani` | 991 | %97 |
| `tahsis_ucreti` | 982 | %96 |
| `masrafsiz_mi` | 967 | %94 |
| `finansman_tutari_max` | 959 | %94 |
| `indirim_orani` | 956 | %93 |
| `kar_payi_orani` | 863 | %84 |
| `odul_miktari` | 847 | %83 |
| `hedef_kitle` | 767 | %75 |
| `vade_ay_max` | 644 | %63 |
| `kampanya_bitis` | 571 | %56 |
| `kampanya_turu` | 0 | %0 |

## Banka kapsamı

Dengesizlik gizlenmez: bir bankadan 100, diğerinden 16 kampanya varsa karşılaştırma yanlıdır ve bunu bilerek raporlamak fark etmemekten iyidir.

| Kod | Banka | Kampanya | Ort. doluluk | `diger` |
|---|---|---|---|---|
| 0203 | Albaraka Türk Katılım Bankası A.Ş. | 136 | %29 | 44 (%32) |
| 0205 | Kuveyt Türk Katılım Bankası A.Ş. | 209 | %32 | 41 (%20) |
| 0206 | Türkiye Finans Katılım Bankası A.Ş. | 173 | %16 | 110 (%64) |
| 0209 | Ziraat Katılım Bankası A.Ş. | 217 | %24 | 38 (%18) |
| 0210 | Vakıf Katılım Bankası A.Ş. | 36 | %28 | 24 (%67) |
| 0211 | Türkiye Emlak Katılım Bankası A.Ş. | 80 | %31 | 53 (%66) |
| 0212 | Hayat Finans Katılım Bankası A.Ş. | 16 | %29 | 6 (%38) |
| 0213 | T.O.M. Katılım Bankası A.Ş. | 103 | %34 | 70 (%68) |
| 0214 | Dünya Katılım Bankası A.Ş. | 54 | %10 | 47 (%87) |
