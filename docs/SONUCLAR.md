# Değerlendirme Sonuçları

_Otomatik üretildi: 15.08.2026 15:35 · `make eval`_

> Bu dosya elle düzenlenmez. Sunumdaki her sayı buradan kopyalanır.

## Veri kapsamı

- İşlenen kampanya: **96**
- Banka sayısı: **8**
- Toplam alan: 1536 · Dolu: 353

## Altın set gerektirmeyen metrikler

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| Şema geçerliliği | 1.00 | 1,00 | ✅ |
| **Halüsinasyon oranı** | %0.28 | ≤ %3 | ✅ |
| Alan doluluğu | %23.0 | — | — |
| Ortalama güven | 0.787 | — | — |

## Yöntem dağılımı (ablasyonun temeli)

| Yöntem | Alan sayısı |
|---|---|
| `llm` | 223 |
| `kural` | 119 |
| `hibrit` | 11 |

## Halüsinasyon örnekleri (hata analizi)

- `kampanya_kosullari: özette geçen '1,89' sayısı ham metinde yok`

## Alan bazlı doluluk

| Alan | Doluluk |
|---|---|
| `kampanya_turu` | %100 |
| `kampanya_kosullari` | %67 |
| `kampanya_avantaji` | %39 |
| `vade_ay_max` | %34 |
| `masrafsiz_mi` | %31 |
| `finansman_tutari_max` | %22 |
| `kampanya_bitis` | %19 |
| `kar_payi_orani` | %16 |
| `odul_miktari` | %12 |
| `taksit_sayisi` | %7 |
| `tahsis_ucreti` | %7 |
| `indirim_orani` | %7 |
| `hedef_kitle` | %4 |
| `masraf_bilgisi` | %1 |
| `alisveris_puani` | %1 |
| `urun_turu` | %0 |

## Altın set metrikleri

> ⏳ **Beklemede.** `data/gold/altin_set.jsonl` henüz yok.
> Altın set olmadan alan bazlı doğruluk, F1 ve makro-F1 hesaplanamaz.
> Bunlar şartnamenin %30'luk «Model Başarısı» kriterinin temelidir.
> **Son tarih: 16 Ağustos 2026.**
