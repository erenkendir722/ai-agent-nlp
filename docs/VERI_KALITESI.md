# Veri Kalitesi Raporu

_Otomatik üretildi: 27.08.2026 22:10 · `make veri-kalitesi`_

> Bu dosya elle düzenlenmez. `make veri-kalitesi` her koşuda yeniden üretir.

> **Güncel.** Çıkarım 27.08.2026 21:17'de `hibrit` yapılandırmasıyla koştu (3 kayıt) ve o tarihten beri çıkarım kodu değişmedi.

**726 kampanya denetlendi.** 5 kontrol eşiği aştı, 9 kontrol temiz.

## Özet

| | Kontrol | Bulgu | Eşik |
|---|---|---|---|
| aşıldı | Kâr payı oranı > %5 | 1 | 0 |
| bilgi | Kâr payı oranı = 0 | 115 | 0 |
| tamam | Finansman tutarı < 5.000 TL | 0 | 0 |
| aşıldı | Finansman tutarı > 10.000.000 TL | 1 | 0 |
| tamam | Vade > 360 ay veya < 1 | 0 | 0 |
| tamam | Taksit sayısı > 24 | 0 | 0 |
| tamam | İndirim oranı > %100 | 0 | 0 |
| aşıldı | Kampanya bitişi geçmişte | 4 | 0 |
| tamam | Kampanya bitişi 5 yıldan uzak | 0 | 0 |
| tamam | Masrafsız işaretli ama tahsis ücreti var | 0 | 0 |
| aşıldı | Banka içi kâr payı aralığı > 5 puan | 1 | 0 |
| tamam | Aynı URL'den birden çok kayıt | 0 | 0 |
| tamam | Hiçbir alanı çıkarılamayan kayıt | 0 | 0 |
| aşıldı | Kampanya türü `diger` | 283 | 254 |

## Aykırı değerler

### aşıldı Kâr payı oranı > %5 — 1 kayıt

Katılım bankaları kâr payını aylık ilan eder. Üstü ya yıllık orandır ya da başka bir yüzde (indirim, mil, iade) bu alana sızmıştır.

| Banka | Değer | Kaynak |
|---|---|---|
| 0206 | 11.0 | …efinans.com.tr/tr-tr/bireysel/Sayfalar/gunluk-hesap.aspx |

### bilgi Kâr payı oranı = 0 — 115 kayıt

Hata DEĞİL sayılır: vade farksız kampanyalarda kâr payı gerçekten sıfırdır. Sayının ani yükselmesi ayrıştırmanın bozulduğunu gösterir.

### tamam Finansman tutarı < 5.000 TL — 0 kayıt

Bu tutarın altı kampanya limiti değil, büyük olasılıkla taksit ya da ücret rakamıdır.

### aşıldı Finansman tutarı > 10.000.000 TL — 1 kayıt

Bireysel kampanyada beklenmez; dilim tablosundan yanlış hücre alınmış olabilir.

| Banka | Değer | Kaynak |
|---|---|---|
| 0203 | doluluk %31 | …ansmanlar/kobi-gayri-nakdi-finansman/jet-teminat-mektubu |

### tamam Vade > 360 ay veya < 1 — 0 kayıt

Konut finansmanında bile 360 ay üst sınırdır.

### tamam Taksit sayısı > 24 — 0 kayıt

Kart taksitlendirmesinde üst sınır; aşılıyorsa vade ile karışmıştır.

### tamam İndirim oranı > %100 — 0 kayıt

Tanımsız değer.

### aşıldı Kampanya bitişi geçmişte — 4 kayıt

Süresi dolmuş kampanya karşılaştırmayı yanıltır. Çok eski bir tarih kampanya tarihi değil, sayfadaki başka bir tarihtir.

| Banka | Değer | Kaynak |
|---|---|---|
| 0206 | 2020-11-30 | …raclari/Sayfalar/finansman-odeme-plani.aspx?financeID=16 |
| 0206 | 2020-11-30 | …araclari/Sayfalar/finansman-odeme-plani.aspx?financeID=1 |
| 0209 | 2026-07-09 | …rislerinize-toplam-1500-tl-bankkart-lira?IsArchived=true |
| 0209 | 2026-07-09 | …lya-alisverisinize-1500-tl-bankkart-lira?IsArchived=true |

### tamam Kampanya bitişi 5 yıldan uzak — 0 kayıt

Ayrıştırma hatası göstergesi.

## Çelişkiler

### tamam Masrafsız işaretli ama tahsis ücreti var — 0 kayıt

İki alan birbirini yalanlıyor.

### aşıldı Banka içi kâr payı aralığı > 5 puan — 1 kayıt

Aynı bankanın kampanyaları arasında bu kadar fark beklenmez.

| Banka | Değer | Kaynak |
|---|---|---|
| 0206 | 0.00 | 11.00 | 11.00 puan |

### tamam Aynı URL'den birden çok kayıt — 0 kayıt

Kimlik URL'den deterministik üretilir; mükerrer varsa toplayıcı aynı sayfayı iki farklı adresten almıştır.

## Eksiklik

### tamam Hiçbir alanı çıkarılamayan kayıt — 0 kayıt

Doluluk sıfırsa sayfa büyük olasılıkla kampanya değildir ya da sitenin yapısı değişmiştir.

### aşıldı Kampanya türü `diger` — 283 kayıt

Sınıflandırılamayan kayıt. Oranın yükselmesi ya toplayıcının kampanya olmayan sayfa getirdiğini ya da sınıflandırmanın kırıldığını gösterir.

| Banka | Değer | Kaynak |
|---|---|---|
| 0203 | 0.0 | …/detay/limitsiz-imm-sigortasinda-vade-farksiz-3-taksit-2 |
| 0203 | 2.99 | …r/tr/kampanyalar/detay/taksitliocom-alisveris-finansmani |
| 0203 | 2026-12-31 | …/tr/kampanyalar/detay/8-taksit-firsatiyla-kasko-zamani-3 |
| 0203 | 0.0 | …https://www.albaraka.com.tr/tr/kampanyalar |
| 0203 | 2026-08-31 | …/otopark-ve-vale-harcamalariniza-50-iade-albarakada-troy |
| … | | *278 kayıt daha* |

## Alan doluluk oranları

| Alan | Boş | Boş oranı |
|---|---|---|
| `alisveris_puani` | 702 | %97 |
| `tahsis_ucreti` | 690 | %95 |
| `hedef_kitle` | 682 | %94 |
| `masrafsiz_mi` | 680 | %94 |
| `finansman_tutari_max` | 679 | %94 |
| `indirim_orani` | 665 | %92 |
| `odul_miktari` | 621 | %86 |
| `kar_payi_orani` | 585 | %81 |
| `taksit_sayisi` | 511 | %70 |
| `kampanya_bitis` | 415 | %57 |
| `vade_ay_max` | 371 | %51 |
| `kampanya_turu` | 0 | %0 |

## Banka kapsamı

Dengesizlik gizlenmez: bir bankadan 100, diğerinden 16 kampanya varsa karşılaştırma yanlıdır ve bunu bilerek raporlamak fark etmemekten iyidir.

| Kod | Banka | Kampanya | Ort. doluluk | `diger` |
|---|---|---|---|---|
| 0203 | Albaraka Türk Katılım Bankası A.Ş. | 116 | %30 | 45 (%39) |
| 0205 | Kuveyt Türk Katılım Bankası A.Ş. | 182 | %36 | 38 (%21) |
| 0206 | Türkiye Finans Katılım Bankası A.Ş. | 56 | %33 | 14 (%25) |
| 0209 | Ziraat Katılım Bankası A.Ş. | 155 | %28 | 32 (%21) |
| 0210 | Vakıf Katılım Bankası A.Ş. | 32 | %28 | 21 (%66) |
| 0211 | Türkiye Emlak Katılım Bankası A.Ş. | 77 | %37 | 53 (%69) |
| 0212 | Hayat Finans Katılım Bankası A.Ş. | 16 | %27 | 5 (%31) |
| 0213 | T.O.M. Katılım Bankası A.Ş. | 49 | %39 | 36 (%73) |
| 0214 | Dünya Katılım Bankası A.Ş. | 43 | %35 | 39 (%91) |
