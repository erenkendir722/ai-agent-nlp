# Değerlendirme Sonuçları

_Otomatik üretildi: 17.08.2026 15:20 · `make eval`_

> Bu dosya elle düzenlenmez. Sunumdaki her sayı buradan kopyalanır.

> ✅ **Güncel.** Çıkarım 17.08.2026 15:20'de `kural` yapılandırmasıyla koştu (96 kayıt) ve o tarihten beri çıkarım kodu değişmedi.

## Veri kapsamı

- İşlenen kampanya: **96**
- Banka sayısı: **8**
- Toplam alan: 1536 · Dolu: 112

## Altın set gerektirmeyen metrikler

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| Şema geçerliliği | 1.00 | 1,00 | ✅ |
| **Halüsinasyon oranı** | %0.00 | ≤ %3 | ✅ |
| Alan doluluğu | %7.3 | — | — |
| Ortalama güven | 0.871 | — | — |

## Yöntem dağılımı (ablasyonun temeli)

| Yöntem | Alan sayısı |
|---|---|
| `kural` | 112 |

## Alan bazlı doluluk

| Alan | Doluluk |
|---|---|
| `vade_ay_max` | %32 |
| `kampanya_bitis` | %24 |
| `masrafsiz_mi` | %16 |
| `kar_payi_orani` | %11 |
| `finansman_tutari_max` | %8 |
| `taksit_sayisi` | %7 |
| `tahsis_ucreti` | %6 |
| `indirim_orani` | %6 |
| `odul_miktari` | %4 |
| `alisveris_puani` | %1 |
| `kampanya_turu` | %0 |
| `urun_turu` | %0 |
| `hedef_kitle` | %0 |
| `masraf_bilgisi` | %0 |
| `kampanya_avantaji` | %0 |
| `kampanya_kosullari` | %0 |

## Altın set metrikleri

- Altın set boyutu: **60** örnek (eşleşen: 60)

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| Sayısal alan doğruluğu | 0.930 | ≥ 0,90 | ✅ |
| Metinsel alan doğruluğu | ölçülmedi | ≥ 0,78 | — |
| **Makro-F1** | 0.628 | ≥ 0,78 | ❌ |

> Metinsel alanlar altın sette etiketlenmiyor (ADR 008): yalnız LLM katmanından geliyorlar ve birebir string karşılaştırmasıyla ölçülemezler.

### Alan bazlı doğruluk ve F1

> **Doğruluk sütununu tek başına okumayın.** Altın setin çoğu hücresi boş, dolayısıyla «iki taraf da boş» hücreler doğruluğu şişiriyor. *Hep boş* sütunu, hiçbir şey çıkarmayan bir sistemin alacağı doğruluktur: doğruluk o sütunun altındaysa, sistem o alanda hiçbir şey yapmamaktan daha kötüdür. F1 doğru negatifi saymaz, bu yüzden gerçek başarıyı gösterir.

| Alan | Doğruluk | Hep boş | Kesinlik | Duyarlılık | **F1** | DP/YP/YN |
|---|---|---|---|---|---|---|
| `kampanya_turu` | 0.000 | 0.000 | 0.000 | 0.000 | **0.000** | 0/0/60 |
| `urun_turu` | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `hedef_kitle` | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kar_payi_orani` | 0.950 | 0.833 | 0.889 | 0.800 | **0.842** | 8/1/2 |
| `finansman_tutari_max` | 0.900 ⚠️ | 0.917 | 0.400 | 0.400 | **0.400** | 2/3/3 |
| `vade_ay_max` | 0.867 | 0.667 | 0.739 | 0.850 | **0.791** | 17/6/3 |
| `taksit_sayisi` | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `tahsis_ucreti` | 0.983 | 0.917 | 0.833 | 1.000 | **0.909** | 5/1/0 |
| `masraf_bilgisi` | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `masrafsiz_mi` | 0.933 | 0.883 | 0.714 | 0.714 | **0.714** | 5/2/2 |
| `odul_miktari` | 0.950 | 0.950 | 0.500 | 0.333 | **0.400** | 1/1/2 |
| `indirim_orani` | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `alisveris_puani` | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kampanya_avantaji` | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kampanya_bitis` | 0.983 | 0.767 | 0.933 | 1.000 | **0.966** | 14/1/0 |
| `kampanya_kosullari` | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |

> ⚠️ = doğruluk «hep boş» tabanının altında. Bu alanlarda sistem boş olması gereken hücrelere değer yazıyor (yanlış pozitif); önce kesinliği düzeltmek gerekir.

> **DP/YP/YN** — doğru pozitif / yanlış pozitif / yanlış negatif. Yanlış değer hem YP hem YN sayılır: uydurulmuş bir değerdir ve aynı anda doğru cevap kaçırılmıştır.
