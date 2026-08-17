# Değerlendirme Sonuçları

_Otomatik üretildi: 17.08.2026 17:26 · `make eval`_

> Bu dosya elle düzenlenmez. Sunumdaki her sayı buradan kopyalanır.

> ✅ **Güncel.** Çıkarım 17.08.2026 17:26'de `hibrit` yapılandırmasıyla koştu (96 kayıt) ve o tarihten beri çıkarım kodu değişmedi.

## Veri kapsamı

- İşlenen kampanya: **96**
- Banka sayısı: **8**
- Toplam alan: 1536 · Dolu: 311

## Altın set gerektirmeyen metrikler

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| Şema geçerliliği | 1.00 | 1,00 | ✅ |
| **Halüsinasyon oranı** | %0.32 | ≤ %3 | ✅ |
| Alan doluluğu | %20.2 | — | — |
| Ortalama güven | 0.799 | — | — |

## Yöntem dağılımı (ablasyonun temeli)

| Yöntem | Alan sayısı |
|---|---|
| `llm` | 195 |
| `kural` | 102 |
| `hibrit` | 14 |

## Halüsinasyon örnekleri (hata analizi)

- `kampanya_kosullari: özette geçen '28' sayısı ham metinde yok`

## Alan bazlı doluluk

| Alan | Doluluk |
|---|---|
| `kampanya_turu` | %100 |
| `kampanya_kosullari` | %56 |
| `kampanya_avantaji` | %42 |
| `vade_ay_max` | %32 |
| `kampanya_bitis` | %24 |
| `masrafsiz_mi` | %16 |
| `kar_payi_orani` | %11 |
| `finansman_tutari_max` | %8 |
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
| Sayısal alan doğruluğu | 0.933 | ≥ 0,90 | ✅ |
| Metinsel alan doğruluğu | ölçülmedi | ≥ 0,78 | — |
| **Makro-F1** | 0.736 _(%95 GA: 0.610–0.810)_ | ≥ 0,78 | ❌ |

> Metinsel alanlar altın sette etiketlenmiyor (ADR 008): yalnız LLM katmanından geliyorlar ve birebir string karşılaştırmasıyla ölçülemezler.

> 📏 **Güven aralığı 60 örnek üzerinden önyükleme (bootstrap) ile hesaplandı** — kayıtlar yerine konarak 400 kez yeniden örneklendi. Aralık genişse sebebi modelin kararsızlığı değil, altın setin küçüklüğüdür. **Sunumda makro-F1 tek başına değil, aralığıyla ve örnek sayısıyla söylenmelidir** — aynı disiplin H-02'de etiketleyici uyumu için de uygulandı.

### Alan bazlı doğruluk ve F1

> **Doğruluk sütununu tek başına okumayın.** Altın setin çoğu hücresi boş, dolayısıyla «iki taraf da boş» hücreler doğruluğu şişiriyor. *Hep boş* sütunu, hiçbir şey çıkarmayan bir sistemin alacağı doğruluktur: doğruluk o sütunun altındaysa, sistem o alanda hiçbir şey yapmamaktan daha kötüdür. F1 doğru negatifi saymaz, bu yüzden gerçek başarıyı gösterir.

> **N sütunu, F1 sütunu kadar önemlidir.** N, altın sette o alanın DOLU olduğu hücre sayısıdır (DP+YN). N=3 olan bir alanda tek bir kaydın düzelmesi F1'i 33 puan oynatır; oradaki 0,900 ile N=60 olan bir alandaki 0,900 aynı şey değildir. Küçük N'li satırları tek başına alıntılamayın.

| Alan | N | Doğruluk | Hep boş | Kesinlik | Duyarlılık | **F1** | DP/YP/YN |
|---|---|---|---|---|---|---|---|
| `kampanya_turu` | 60 | 0.600 | 0.000 | 0.600 | 0.600 | **0.600** | 36/24/24 |
| `urun_turu` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `hedef_kitle` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kar_payi_orani` | 10 | 0.950 | 0.833 | 0.889 | 0.800 | **0.842** | 8/1/2 |
| `finansman_tutari_max` | 5 🔸 | 0.900 ⚠️ | 0.917 | 0.400 | 0.400 | **0.400** | 2/3/3 |
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

## Ablasyon tablosu

Üç yapılandırma **aynı kod yolundan** koşulur; yalnız katman bayrakları değişir.
Ayrı kod yolu yazmak ölçümü karşılaştırılamaz hâle getirirdi.

```bash
make extract-kural && make eval   # yalnız kural
make extract-llm   && make eval   # yalnız LLM
make extract       && make eval   # hibrit
```

| Yapılandırma | Kâr payı F1 | Vade F1 | Makro-F1 | Halüsinasyon | Doluluk |
|---|---|---|---|---|---|
| Yalnız kural (regex) | 0.842 | 0.791 | **0.628** | %0.00 | %7.3 |
| Yalnız LLM (şema kısıtlı) | 0.000 | 0.000 | **0.176** | %0.48 | %13.7 |
| **Hibrit (bizim)** | 0.842 | 0.791 | **0.736** | %0.32 | %20.2 |

> 🔴 **Satırlar KARŞILAŞTIRILAMAZ** — farklı kod sürümleriyle koşulmuşlar (3a40d94a27700f6f, f797dd3f69630cfc). Üçünü de aynı kodla yeniden koşun.

