# Veri Kalitesi Raporu

_Otomatik üretildi: 26.08.2026 23:21 · `make veri-kalitesi`_

> Bu dosya elle düzenlenmez. `make veri-kalitesi` her koşuda yeniden üretir.

> ✅ **Güncel.** Çıkarım 26.08.2026 17:54'de `hibrit` yapılandırmasıyla koştu (1023 kayıt) ve o tarihten beri çıkarım kodu değişmedi.

**931 kampanya denetlendi.** 6 kontrol eşiği aştı, 8 kontrol temiz.

## Özet

| | Kontrol | Bulgu | Eşik |
|---|---|---|---|
| 🔴 | Kâr payı oranı > %5 | 1 | 0 |
| ℹ️ | Kâr payı oranı = 0 | 119 | 0 |
| ✅ | Finansman tutarı < 5.000 TL | 0 | 0 |
| 🔴 | Finansman tutarı > 10.000.000 TL | 2 | 0 |
| ✅ | Vade > 360 ay veya < 1 | 0 | 0 |
| ✅ | Taksit sayısı > 24 | 0 | 0 |
| ✅ | İndirim oranı > %100 | 0 | 0 |
| 🔴 | Kampanya bitişi geçmişte | 5 | 0 |
| 🔴 | Kampanya bitişi 5 yıldan uzak | 1 | 0 |
| ✅ | Masrafsız işaretli ama tahsis ücreti var | 0 | 0 |
| 🔴 | Banka içi kâr payı aralığı > 5 puan | 1 | 0 |
| ✅ | Aynı URL'den birden çok kayıt | 0 | 0 |
| ✅ | Hiçbir alanı çıkarılamayan kayıt | 0 | 0 |
| 🔴 | Kampanya türü `diger` | 416 | 325 |

## Aykırı değerler

### 🔴 Kâr payı oranı > %5 — 1 kayıt

Katılım bankaları kâr payını aylık ilan eder. Üstü ya yıllık orandır ya da başka bir yüzde (indirim, mil, iade) bu alana sızmıştır.

| Banka | Değer | Kaynak |
|---|---|---|
| 0206 | 11.0 | …efinans.com.tr/tr-tr/bireysel/Sayfalar/gunluk-hesap.aspx |

### ℹ️ Kâr payı oranı = 0 — 119 kayıt

Hata DEĞİL sayılır: vade farksız kampanyalarda kâr payı gerçekten sıfırdır. Sayının ani yükselmesi ayrıştırmanın bozulduğunu gösterir.

### ✅ Finansman tutarı < 5.000 TL — 0 kayıt

Bu tutarın altı kampanya limiti değil, büyük olasılıkla taksit ya da ücret rakamıdır.

### 🔴 Finansman tutarı > 10.000.000 TL — 2 kayıt

Bireysel kampanyada beklenmez; dilim tablosundan yanlış hücre alınmış olabilir.

| Banka | Değer | Kaynak |
|---|---|---|
| 0203 | doluluk %31 | …smanlar/ticari-gayri-nakdi-finansman/jet-teminat-mektubu |
| 0203 | doluluk %31 | …ansmanlar/kobi-gayri-nakdi-finansman/jet-teminat-mektubu |

### ✅ Vade > 360 ay veya < 1 — 0 kayıt

Konut finansmanında bile 360 ay üst sınırdır.

### ✅ Taksit sayısı > 24 — 0 kayıt

Kart taksitlendirmesinde üst sınır; aşılıyorsa vade ile karışmıştır.

### ✅ İndirim oranı > %100 — 0 kayıt

Tanımsız değer.

### 🔴 Kampanya bitişi geçmişte — 5 kayıt

Süresi dolmuş kampanya karşılaştırmayı yanıltır. Çok eski bir tarih kampanya tarihi değil, sayfadaki başka bir tarihtir.

| Banka | Değer | Kaynak |
|---|---|---|
| 0214 | 2026-03-31 | …https://dunyakatilim.com.tr/kampanyalar/fiziki-altin |
| 0206 | 2020-11-30 | …raclari/Sayfalar/finansman-odeme-plani.aspx?financeID=16 |
| 0206 | 2020-11-30 | …araclari/Sayfalar/finansman-odeme-plani.aspx?financeID=1 |
| 0209 | 2026-07-09 | …rislerinize-toplam-1500-tl-bankkart-lira?IsArchived=true |
| 0209 | 2026-07-09 | …lya-alisverisinize-1500-tl-bankkart-lira?IsArchived=true |

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

### 🔴 Kampanya türü `diger` — 416 kayıt

Sınıflandırılamayan kayıt. Oranın yükselmesi ya toplayıcının kampanya olmayan sayfa getirdiğini ya da sınıflandırmanın kırıldığını gösterir.

| Banka | Değer | Kaynak |
|---|---|---|
| 0203 | 0.0 | …/detay/limitsiz-imm-sigortasinda-vade-farksiz-3-taksit-2 |
| 0203 | 0.5 | …r/tr/kampanyalar/detay/taksitliocom-alisveris-finansmani |
| 0203 | 2026-12-31 | …detay/restoran-harcamalariniza-ozel-10-indirim-firsati-1 |
| 0203 | doluluk %6 | …/tr/kampanyalar/detay/8-taksit-firsatiyla-kasko-zamani-3 |
| 0203 | 0.0 | …https://www.albaraka.com.tr/tr/kampanyalar |
| … | | *411 kayıt daha* |

## Alan doluluk oranları

| Alan | Boş | Boş oranı |
|---|---|---|
| `taksit_sayisi` | 931 | %100 |
| `alisveris_puani` | 906 | %97 |
| `tahsis_ucreti` | 890 | %96 |
| `masrafsiz_mi` | 877 | %94 |
| `finansman_tutari_max` | 870 | %93 |
| `indirim_orani` | 866 | %93 |
| `odul_miktari` | 815 | %88 |
| `kar_payi_orani` | 784 | %84 |
| `hedef_kitle` | 702 | %75 |
| `vade_ay_max` | 574 | %62 |
| `kampanya_bitis` | 570 | %61 |
| `kampanya_turu` | 0 | %0 |

## Banka kapsamı

Dengesizlik gizlenmez: bir bankadan 100, diğerinden 16 kampanya varsa karşılaştırma yanlıdır ve bunu bilerek raporlamak fark etmemekten iyidir.

| Kod | Banka | Kampanya | Ort. doluluk | `diger` |
|---|---|---|---|---|
| 0203 | Albaraka Türk Katılım Bankası A.Ş. | 126 | %28 | 38 (%30) |
| 0205 | Kuveyt Türk Katılım Bankası A.Ş. | 190 | %31 | 33 (%17) |
| 0206 | Türkiye Finans Katılım Bankası A.Ş. | 172 | %16 | 111 (%65) |
| 0209 | Ziraat Katılım Bankası A.Ş. | 162 | %21 | 37 (%23) |
| 0210 | Vakıf Katılım Bankası A.Ş. | 36 | %29 | 24 (%67) |
| 0211 | Türkiye Emlak Katılım Bankası A.Ş. | 78 | %30 | 51 (%65) |
| 0212 | Hayat Finans Katılım Bankası A.Ş. | 16 | %28 | 6 (%38) |
| 0213 | T.O.M. Katılım Bankası A.Ş. | 97 | %34 | 69 (%71) |
| 0214 | Dünya Katılım Bankası A.Ş. | 54 | %13 | 47 (%87) |
