# Veri Kalitesi Raporu

_Otomatik üretildi: 27.08.2026 19:08 · `make veri-kalitesi`_

> Bu dosya elle düzenlenmez. `make veri-kalitesi` her koşuda yeniden üretir.

> **BAYAT — bu rapor eski bir çıkarımı anlatıyor.**
> Çıkarım 27.08.2026 14:11'de koştu; çıkarım kodu o tarihten sonra değişti (677ae6c9186359c1 → cd99b4f2c988a243).
> Düzeltmek için: `make extract && make veri-kalitesi`.

**727 kampanya denetlendi.** 6 kontrol eşiği aştı, 8 kontrol temiz.

## Özet

| | Kontrol | Bulgu | Eşik |
|---|---|---|---|
| aşıldı | Kâr payı oranı > %5 | 1 | 0 |
| bilgi | Kâr payı oranı = 0 | 116 | 0 |
| tamam | Finansman tutarı < 5.000 TL | 0 | 0 |
| aşıldı | Finansman tutarı > 10.000.000 TL | 1 | 0 |
| tamam | Vade > 360 ay veya < 1 | 0 | 0 |
| tamam | Taksit sayısı > 24 | 0 | 0 |
| tamam | İndirim oranı > %100 | 0 | 0 |
| aşıldı | Kampanya bitişi geçmişte | 6 | 0 |
| aşıldı | Kampanya bitişi 5 yıldan uzak | 1 | 0 |
| tamam | Masrafsız işaretli ama tahsis ücreti var | 0 | 0 |
| aşıldı | Banka içi kâr payı aralığı > 5 puan | 1 | 0 |
| tamam | Aynı URL'den birden çok kayıt | 0 | 0 |
| tamam | Hiçbir alanı çıkarılamayan kayıt | 0 | 0 |
| aşıldı | Kampanya türü `diger` | 261 | 254 |

## Aykırı değerler

### aşıldı Kâr payı oranı > %5 — 1 kayıt

Katılım bankaları kâr payını aylık ilan eder. Üstü ya yıllık orandır ya da başka bir yüzde (indirim, mil, iade) bu alana sızmıştır.

| Banka | Değer | Kaynak |
|---|---|---|
| 0206 | 11.0 | …efinans.com.tr/tr-tr/bireysel/Sayfalar/gunluk-hesap.aspx |

### bilgi Kâr payı oranı = 0 — 116 kayıt

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

### aşıldı Kampanya bitişi geçmişte — 6 kayıt

Süresi dolmuş kampanya karşılaştırmayı yanıltır. Çok eski bir tarih kampanya tarihi değil, sayfadaki başka bir tarihtir.

| Banka | Değer | Kaynak |
|---|---|---|
| 0214 | 2026-04-30 | …https://dunyakatilim.com.tr/kampanyalar/jack-jones |
| 0214 | 2026-04-30 | …https://dunyakatilim.com.tr/kampanyalar/koton |
| 0206 | 2020-11-30 | …raclari/Sayfalar/finansman-odeme-plani.aspx?financeID=16 |
| 0206 | 2020-11-30 | …araclari/Sayfalar/finansman-odeme-plani.aspx?financeID=1 |
| 0209 | 2026-07-09 | …rislerinize-toplam-1500-tl-bankkart-lira?IsArchived=true |
| … | | *1 kayıt daha* |

### aşıldı Kampanya bitişi 5 yıldan uzak — 1 kayıt

Ayrıştırma hatası göstergesi.

| Banka | Değer | Kaynak |
|---|---|---|
| 0205 | 0.0 | …icin/kart-kampanyalari/bella-maisonda-25-indirim-firsati |

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

### aşıldı Kampanya türü `diger` — 261 kayıt

Sınıflandırılamayan kayıt. Oranın yükselmesi ya toplayıcının kampanya olmayan sayfa getirdiğini ya da sınıflandırmanın kırıldığını gösterir.

| Banka | Değer | Kaynak |
|---|---|---|
| 0203 | 0.0 | …/detay/limitsiz-imm-sigortasinda-vade-farksiz-3-taksit-2 |
| 0203 | 0.5 | …r/tr/kampanyalar/detay/taksitliocom-alisveris-finansmani |
| 0203 | 2026-12-31 | …detay/restoran-harcamalariniza-ozel-10-indirim-firsati-1 |
| 0203 | 2026-12-31 | …/tr/kampanyalar/detay/8-taksit-firsatiyla-kasko-zamani-3 |
| 0203 | 0.0 | …https://www.albaraka.com.tr/tr/kampanyalar |
| … | | *256 kayıt daha* |

## Alan doluluk oranları

| Alan | Boş | Boş oranı |
|---|---|---|
| `taksit_sayisi` | 727 | %100 |
| `alisveris_puani` | 703 | %97 |
| `tahsis_ucreti` | 690 | %95 |
| `masrafsiz_mi` | 678 | %93 |
| `finansman_tutari_max` | 675 | %93 |
| `indirim_orani` | 665 | %91 |
| `odul_miktari` | 621 | %85 |
| `kar_payi_orani` | 586 | %81 |
| `hedef_kitle` | 520 | %72 |
| `kampanya_bitis` | 409 | %56 |
| `vade_ay_max` | 374 | %51 |
| `kampanya_turu` | 0 | %0 |

## Banka kapsamı

Dengesizlik gizlenmez: bir bankadan 100, diğerinden 16 kampanya varsa karşılaştırma yanlıdır ve bunu bilerek raporlamak fark etmemekten iyidir.

| Kod | Banka | Kampanya | Ort. doluluk | `diger` |
|---|---|---|---|---|
| 0203 | Albaraka Türk Katılım Bankası A.Ş. | 116 | %29 | 35 (%30) |
| 0205 | Kuveyt Türk Katılım Bankası A.Ş. | 183 | %31 | 31 (%17) |
| 0206 | Türkiye Finans Katılım Bankası A.Ş. | 55 | %32 | 13 (%24) |
| 0209 | Ziraat Katılım Bankası A.Ş. | 154 | %21 | 29 (%19) |
| 0210 | Vakıf Katılım Bankası A.Ş. | 32 | %30 | 20 (%62) |
| 0211 | Türkiye Emlak Katılım Bankası A.Ş. | 77 | %31 | 51 (%66) |
| 0212 | Hayat Finans Katılım Bankası A.Ş. | 16 | %28 | 6 (%38) |
| 0213 | T.O.M. Katılım Bankası A.Ş. | 49 | %34 | 35 (%71) |
| 0214 | Dünya Katılım Bankası A.Ş. | 45 | %27 | 41 (%91) |
