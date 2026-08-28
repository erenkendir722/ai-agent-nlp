# Veri Kalitesi Raporu

_Otomatik üretildi: 28.08.2026 10:19 · `make veri-kalitesi`_

> Bu dosya elle düzenlenmez. `make veri-kalitesi` her koşuda yeniden üretir.

> **Güncel.** Çıkarım 28.08.2026 03:09'de `hibrit` yapılandırmasıyla koştu (38 kayıt) ve o tarihten beri çıkarım kodu değişmedi.

**921 kampanya denetlendi.** 5 kontrol eşiği aştı, 9 kontrol temiz.

## Özet

| | Kontrol | Bulgu | Eşik |
|---|---|---|---|
| aşıldı | Kâr payı oranı > %5 | 1 | 0 |
| bilgi | Kâr payı oranı = 0 | 131 | 0 |
| tamam | Finansman tutarı < 5.000 TL | 0 | 0 |
| aşıldı | Finansman tutarı > 10.000.000 TL | 1 | 0 |
| tamam | Vade > 360 ay veya < 1 | 0 | 0 |
| tamam | Taksit sayısı > 24 | 0 | 0 |
| tamam | İndirim oranı > %100 | 0 | 0 |
| aşıldı | Kampanya bitişi geçmişte | 95 | 0 |
| tamam | Kampanya bitişi 5 yıldan uzak | 0 | 0 |
| tamam | Masrafsız işaretli ama tahsis ücreti var | 0 | 0 |
| aşıldı | Banka içi kâr payı aralığı > 5 puan | 1 | 0 |
| tamam | Aynı URL'den birden çok kayıt | 0 | 0 |
| tamam | Hiçbir alanı çıkarılamayan kayıt | 0 | 0 |
| aşıldı | Kampanya türü `diger` | 330 | 322 |

## Aykırı değerler

### aşıldı Kâr payı oranı > %5 — 1 kayıt

Katılım bankaları kâr payını aylık ilan eder. Üstü ya yıllık orandır ya da başka bir yüzde (indirim, mil, iade) bu alana sızmıştır.

| Banka | Değer | Kaynak |
|---|---|---|
| 0206 | 11.0 | …efinans.com.tr/tr-tr/bireysel/Sayfalar/gunluk-hesap.aspx |

### bilgi Kâr payı oranı = 0 — 131 kayıt

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

### aşıldı Kampanya bitişi geçmişte — 95 kayıt

Süresi dolmuş kampanya karşılaştırmayı yanıltır. Çok eski bir tarih kampanya tarihi değil, sayfadaki başka bir tarihtir.

| Banka | Değer | Kaynak |
|---|---|---|
| 0206 | 2020-11-30 | …raclari/Sayfalar/finansman-odeme-plani.aspx?financeID=16 |
| 0206 | 2020-11-30 | …araclari/Sayfalar/finansman-odeme-plani.aspx?financeID=1 |
| 0209 | 2026-07-09 | …rislerinize-toplam-1500-tl-bankkart-lira?IsArchived=true |
| 0209 | 2026-07-09 | …lya-alisverisinize-1500-tl-bankkart-lira?IsArchived=true |
| 0203 | 2026-07-31 | …tura-odeme-talimatlariniza-toplamda-2000-tl-worldpuan-11 |
| … | | *90 kayıt daha* |

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

### aşıldı Kampanya türü `diger` — 330 kayıt

Sınıflandırılamayan kayıt. Oranın yükselmesi ya toplayıcının kampanya olmayan sayfa getirdiğini ya da sınıflandırmanın kırıldığını gösterir.

| Banka | Değer | Kaynak |
|---|---|---|
| 0203 | 0.0 | …/detay/limitsiz-imm-sigortasinda-vade-farksiz-3-taksit-2 |
| 0203 | 2.99 | …r/tr/kampanyalar/detay/taksitliocom-alisveris-finansmani |
| 0203 | 2026-12-31 | …/tr/kampanyalar/detay/8-taksit-firsatiyla-kasko-zamani-3 |
| 0203 | 0.0 | …https://www.albaraka.com.tr/tr/kampanyalar |
| 0203 | 2026-08-31 | …/otopark-ve-vale-harcamalariniza-50-iade-albarakada-troy |
| … | | *325 kayıt daha* |

## Alan doluluk oranları

| Alan | Boş | Boş oranı |
|---|---|---|
| `alisveris_puani` | 889 | %97 |
| `tahsis_ucreti` | 883 | %96 |
| `masrafsiz_mi` | 868 | %94 |
| `finansman_tutari_max` | 863 | %94 |
| `hedef_kitle` | 860 | %93 |
| `indirim_orani` | 853 | %93 |
| `kar_payi_orani` | 761 | %83 |
| `odul_miktari` | 745 | %81 |
| `taksit_sayisi` | 688 | %75 |
| `vade_ay_max` | 512 | %56 |
| `kampanya_bitis` | 505 | %55 |
| `kampanya_turu` | 0 | %0 |

## Banka kapsamı

Dengesizlik gizlenmez: bir bankadan 100, diğerinden 16 kampanya varsa karşılaştırma yanlıdır ve bunu bilerek raporlamak fark etmemekten iyidir.

| Kod | Banka | Kampanya | Ort. doluluk | `diger` |
|---|---|---|---|---|
| 0203 | Albaraka Türk Katılım Bankası A.Ş. | 127 | %31 | 48 (%38) |
| 0205 | Kuveyt Türk Katılım Bankası A.Ş. | 205 | %36 | 45 (%22) |
| 0206 | Türkiye Finans Katılım Bankası A.Ş. | 64 | %31 | 17 (%27) |
| 0209 | Ziraat Katılım Bankası A.Ş. | 211 | %30 | 32 (%15) |
| 0210 | Vakıf Katılım Bankası A.Ş. | 72 | %26 | 37 (%51) |
| 0211 | Türkiye Emlak Katılım Bankası A.Ş. | 109 | %34 | 64 (%59) |
| 0212 | Hayat Finans Katılım Bankası A.Ş. | 19 | %28 | 5 (%26) |
| 0213 | T.O.M. Katılım Bankası A.Ş. | 62 | %39 | 41 (%66) |
| 0214 | Dünya Katılım Bankası A.Ş. | 52 | %34 | 41 (%79) |
