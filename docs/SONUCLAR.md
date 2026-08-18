# Değerlendirme Sonuçları

_Otomatik üretildi: 18.08.2026 23:45 · `make eval`_

> Bu dosya elle düzenlenmez. Sunumdaki her sayı buradan kopyalanır.

> ✅ **Güncel.** Çıkarım 18.08.2026 23:36'de `hibrit` yapılandırmasıyla koştu (96 kayıt) ve o tarihten beri çıkarım kodu değişmedi.

## Veri kapsamı

- İşlenen kampanya: **96**
- Banka sayısı: **8**
- Toplam alan: 1536 · Dolu: 316

## Altın set gerektirmeyen metrikler

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| Şema geçerliliği | 1.00 | 1,00 | ✅ |
| **Halüsinasyon oranı** | %0.32 | ≤ %3 | ✅ |
| Alan doluluğu | %20.6 | — | — |
| Ortalama güven | 0.799 | — | — |

## Yöntem dağılımı (ablasyonun temeli)

| Yöntem | Alan sayısı |
|---|---|
| `llm` | 197 |
| `kural` | 103 |
| `hibrit` | 16 |

## Halüsinasyon örnekleri (hata analizi)

- `kampanya_kosullari: özette geçen '1,5' sayısı ham metinde yok`

## Alan bazlı doluluk

| Alan | Doluluk |
|---|---|
| `kampanya_turu` | %100 |
| `kampanya_kosullari` | %61 |
| `kampanya_avantaji` | %39 |
| `vade_ay_max` | %32 |
| `kampanya_bitis` | %24 |
| `masrafsiz_mi` | %16 |
| `kar_payi_orani` | %11 |
| `finansman_tutari_max` | %11 |
| `odul_miktari` | %8 |
| `taksit_sayisi` | %7 |
| `tahsis_ucreti` | %6 |
| `indirim_orani` | %6 |
| `hedef_kitle` | %4 |
| `masraf_bilgisi` | %1 |
| `alisveris_puani` | %1 |
| `urun_turu` | %0 |

## Altın set metrikleri

- Altın set boyutu: **60** örnek (eşleşen: 60)

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| Sayısal alan doğruluğu | 0.937 | ≥ 0,90 | ✅ |
| Metinsel alan doğruluğu | ölçülmedi | ≥ 0,78 | — |
| **Makro-F1** | 0.778 _(%95 GA: 0.645–0.847)_ | ≥ 0,78 | ❌ |

> Metinsel alanlar altın sette etiketlenmiyor (ADR 008): yalnız LLM katmanından geliyorlar ve birebir string karşılaştırmasıyla ölçülemezler.

> 📏 **Güven aralığı 60 örnek üzerinden önyükleme (bootstrap) ile hesaplandı** — kayıtlar yerine konarak 400 kez yeniden örneklendi. Aralık genişse sebebi modelin kararsızlığı değil, altın setin küçüklüğüdür. **Sunumda makro-F1 tek başına değil, aralığıyla ve örnek sayısıyla söylenmelidir** — aynı disiplin H-02'de etiketleyici uyumu için de uygulandı.

### Alan bazlı doğruluk ve F1

> **Doğruluk sütununu tek başına okumayın.** Altın setin çoğu hücresi boş, dolayısıyla «iki taraf da boş» hücreler doğruluğu şişiriyor. *Hep boş* sütunu, hiçbir şey çıkarmayan bir sistemin alacağı doğruluktur: doğruluk o sütunun altındaysa, sistem o alanda hiçbir şey yapmamaktan daha kötüdür. F1 doğru negatifi saymaz, bu yüzden gerçek başarıyı gösterir.

> **N sütunu, F1 sütunu kadar önemlidir.** N, altın sette o alanın DOLU olduğu hücre sayısıdır (DP+YN). N=3 olan bir alanda tek bir kaydın düzelmesi F1'i 33 puan oynatır; oradaki 0,900 ile N=60 olan bir alandaki 0,900 aynı şey değildir. Küçük N'li satırları tek başına alıntılamayın.

| Alan | N | Doğruluk | Hep boş | Kesinlik | Duyarlılık | **F1** | DP/YP/YN |
|---|---|---|---|---|---|---|---|
| `kampanya_turu` | 60 | 0.717 | 0.000 | 0.717 | 0.717 | **0.717** | 43/17/17 |
| `urun_turu` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `hedef_kitle` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kar_payi_orani` | 10 | 0.950 | 0.833 | 0.889 | 0.800 | **0.842** | 8/1/2 |
| `finansman_tutari_max` | 5 🔸 | 0.917 | 0.917 | 0.500 | 0.800 | **0.615** | 4/4/1 |
| `vade_ay_max` | 20 | 0.867 | 0.667 | 0.739 | 0.850 | **0.791** | 17/6/3 |
| `taksit_sayisi` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `tahsis_ucreti` | 5 🔸 | 0.983 | 0.917 | 0.833 | 1.000 | **0.909** | 5/1/0 |
| `masraf_bilgisi` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `masrafsiz_mi` | 7 🔸 | 0.933 | 0.883 | 0.714 | 0.714 | **0.714** | 5/2/2 |
| `odul_miktari` | 3 🔸 | 0.967 | 0.950 | 0.667 | 0.667 | **0.667** | 2/1/1 |
| `indirim_orani` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `alisveris_puani` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kampanya_avantaji` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kampanya_bitis` | 14 | 0.983 | 0.767 | 0.933 | 1.000 | **0.966** | 14/1/0 |
| `kampanya_kosullari` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |

> ⚠️ = doğruluk «hep boş» tabanının altında. Bu alanlarda sistem boş olması gereken hücrelere değer yazıyor (yanlış pozitif); önce kesinliği düzeltmek gerekir.

> **DP/YP/YN** — doğru pozitif / yanlış pozitif / yanlış negatif. Yanlış değer hem YP hem YN sayılır: uydurulmuş bir değerdir ve aynı anda doğru cevap kaçırılmıştır.
