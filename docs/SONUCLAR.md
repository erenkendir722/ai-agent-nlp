# Değerlendirme Sonuçları

_Otomatik üretildi: 16.08.2026 16:45 · `make eval`_

> Bu dosya elle düzenlenmez. Sunumdaki her sayı buradan kopyalanır.

> 🔴 **BAYAT — bu sayıları sunuma kopyalamayın.**
> Çıkarım koşusu kaydı yok — veritabanı bu özellik eklenmeden önce üretilmiş.
> Düzeltmek için: `make extract && make eval`.

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
| **Makro-F1** | 0.491 | ≥ 0,78 | ❌ |

> Metinsel alanlar altın sette etiketlenmiyor (ADR 008): yalnız LLM katmanından geliyorlar ve birebir string karşılaştırmasıyla ölçülemezler.

### Alan bazlı doğruluk ve F1

> **Doğruluk sütununu tek başına okumayın.** Altın setin çoğu hücresi boş, dolayısıyla «iki taraf da boş» hücreler doğruluğu şişiriyor. *Hep boş* sütunu, hiçbir şey çıkarmayan bir sistemin alacağı doğruluktur: doğruluk o sütunun altındaysa, sistem o alanda hiçbir şey yapmamaktan daha kötüdür. F1 doğru negatifi saymaz, bu yüzden gerçek başarıyı gösterir.

| Alan | Doğruluk | Hep boş | Kesinlik | Duyarlılık | **F1** | DP/YP/YN |
|---|---|---|---|---|---|---|
| `kampanya_turu` | 0.600 | 0.000 | 0.600 | 0.600 | **0.600** | 36/24/24 |
| `urun_turu` | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `hedef_kitle` | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kar_payi_orani` | 0.867 | 0.833 | 0.500 | 0.600 | **0.545** | 6/6/4 |
| `finansman_tutari_max` | 0.733 ⚠️ | 0.917 | 0.118 | 0.400 | **0.182** | 2/15/3 |
| `vade_ay_max` | 0.833 | 0.667 | 0.680 | 0.850 | **0.756** | 17/8/3 |
| `taksit_sayisi` | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `tahsis_ucreti` | 0.933 | 0.917 | 0.333 | 0.400 | **0.364** | 2/4/3 |
| `masraf_bilgisi` | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `masrafsiz_mi` | 0.833 ⚠️ | 0.883 | 0.222 | 0.286 | **0.250** | 2/7/5 |
| `odul_miktari` | 0.917 ⚠️ | 0.950 | 0.286 | 0.667 | **0.400** | 2/5/1 |
| `indirim_orani` | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `alisveris_puani` | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kampanya_avantaji` | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kampanya_bitis` | 0.933 | 0.767 | 1.000 | 0.714 | **0.833** | 10/0/4 |
| `kampanya_kosullari` | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |

> ⚠️ = doğruluk «hep boş» tabanının altında. Bu alanlarda sistem boş olması gereken hücrelere değer yazıyor (yanlış pozitif); önce kesinliği düzeltmek gerekir.

> **DP/YP/YN** — doğru pozitif / yanlış pozitif / yanlış negatif. Yanlış değer hem YP hem YN sayılır: uydurulmuş bir değerdir ve aynı anda doğru cevap kaçırılmıştır.
