# Değerlendirme Sonuçları

_Otomatik üretildi: 15.08.2026 17:49 · `make eval`_

> Bu dosya elle düzenlenmez. Sunumdaki her sayı buradan kopyalanır.

## Veri kapsamı

- İşlenen kampanya: **96**
- Banka sayısı: **8**
- Toplam alan: 1536 · Dolu: 337

## Altın set gerektirmeyen metrikler

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| Şema geçerliliği | 1.00 | 1,00 | ✅ |
| **Halüsinasyon oranı** | %0.30 | ≤ %3 | ✅ |
| Alan doluluğu | %21.9 | — | — |
| Ortalama güven | 0.807 | — | — |

## Yöntem dağılımı (ablasyonun temeli)

| Yöntem | Alan sayısı |
|---|---|
| `llm` | 199 |
| `kural` | 126 |
| `hibrit` | 12 |

## Halüsinasyon örnekleri (hata analizi)

- `kampanya_kosullari: özette geçen '28' sayısı ham metinde yok`

## Alan bazlı doluluk

| Alan | Doluluk |
|---|---|
| `kampanya_turu` | %100 |
| `kampanya_kosullari` | %59 |
| `kampanya_avantaji` | %39 |
| `vade_ay_max` | %34 |
| `finansman_tutari_max` | %22 |
| `masrafsiz_mi` | %22 |
| `kampanya_bitis` | %18 |
| `kar_payi_orani` | %16 |
| `odul_miktari` | %12 |
| `tahsis_ucreti` | %8 |
| `taksit_sayisi` | %7 |
| `indirim_orani` | %7 |
| `hedef_kitle` | %4 |
| `masraf_bilgisi` | %1 |
| `alisveris_puani` | %1 |
| `urun_turu` | %0 |

## Altın set metrikleri

- Altın set boyutu: **60** örnek (eşleşen: 60)

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| Sayısal alan doğruluğu | 0.857 | ≥ 0,90 | ❌ |
| Metinsel alan doğruluğu | ölçülmedi | ≥ 0,78 | — |

> Metinsel alanlar altın sette etiketlenmiyor (ADR 008): yalnız LLM katmanından geliyorlar ve birebir string karşılaştırmasıyla ölçülemezler.

### Alan bazlı doğruluk

| Alan | Doğruluk |
|---|---|
| `kampanya_turu` | 0.600 |
| `urun_turu` | — |
| `hedef_kitle` | — |
| `kar_payi_orani` | 0.867 |
| `finansman_tutari_max` | 0.733 |
| `vade_ay_max` | 0.833 |
| `taksit_sayisi` | — |
| `tahsis_ucreti` | 0.933 |
| `masraf_bilgisi` | — |
| `masrafsiz_mi` | 0.833 |
| `odul_miktari` | 0.917 |
| `indirim_orani` | — |
| `alisveris_puani` | — |
| `kampanya_avantaji` | — |
| `kampanya_bitis` | 0.933 |
| `kampanya_kosullari` | — |
