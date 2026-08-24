# Değerlendirme Sonuçları

_Otomatik üretildi: 24.08.2026 17:31 · `make eval`_

> Bu dosya elle düzenlenmez. Sunumdaki her sayı buradan kopyalanır.

> ✅ **Güncel.** Çıkarım 24.08.2026 17:29'de `hibrit` yapılandırmasıyla koştu (1021 kayıt) ve o tarihten beri çıkarım kodu değişmedi.

## Veri kapsamı

- İşlenen kampanya: **1023**
- Banka sayısı: **9**
- Toplam alan: 16368 · Dolu: 4235

## Altın set gerektirmeyen metrikler

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| Şema geçerliliği | 1.00 | 1,00 | ✅ |
| **Halüsinasyon oranı** | %0.38 | ≤ %3 | ✅ |
| Alan doluluğu | %25.9 | — | — |
| Ortalama güven | 0.794 | — | — |
| **Kalkan yanlış blok oranı** | %0.0 | %0 | ✅ |
| Denetimsiz cevap parçası | %0.0 | %0 | ✅ |

## Sayısal doğrulama kalkanı (köken tipli)

Kalkanın iki yönlü bir hata uzayı var; ikisi ayrı ölçülür:

- **Yanlış blok** — meşru cevabı engelleme: **0/35** (`eval/sorular.yaml`, 42 soru)
- **Gevşeme** — uydurma sayıyı geçirme: eşik değil ikili doğruluk; `tests/test_kalkan_kokenli.py` koruyor

| Parça kökeni | Sayı | Doğrulama ölçütü |
|---|---|---|
| `yapisal` | 24 | yapısal kayıtta birebir karşılığı olmalı |
| `alinti` | 37 | kaynak metnin alt dizesi + sayıları alıntının içinde |
| `sistem` | 9 | sayılar `hesap` girdilerinden yeniden üretilebilmeli |
| `duz` | 18 | sayı içeremez (yapıcıda denetlenir) |
| `denetimsiz` | 0 | **miras yol — atlanır ama sayılır** |

> ✅ **Meşru soruların hiçbiri engellenmedi.** 18 Ağustos ölçümünde bu oran %14,3'tü (35 meşru sorunun 5'i): bankanın kendi metnindeki sayılar — bir vaka **6698 sayılı KVKK kanun numarası** — yapısal alanda karşılığı olmadığı için «uydurma» sayılıyordu. Kalkan gevşetilmedi; parçaların kökeni bildirildi ve alıntılar KAYNAĞINA karşı denetlenir oldu. Aynı değişiklik, hesap bölümündeki kör noktayı da kapattı (skor ve ağırlıklar artık yeniden üretiliyor).

## Yöntem dağılımı (ablasyonun temeli)

| Yöntem | Alan sayısı |
|---|---|
| `llm` | 2823 |
| `kural` | 942 |
| `hibrit` | 470 |

## Halüsinasyon örnekleri (hata analizi)

- `kampanya_kosullari: özette geçen '1,5' sayısı ham metinde yok`
- `kampanya_avantaji: özette geçen '5.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '400.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '15.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '200.000' sayısı ham metinde yok`
- `kampanya_avantaji: özette geçen '1.000' sayısı ham metinde yok`
- `kampanya_avantaji: özette geçen '1.250' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '15.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '200.000' sayısı ham metinde yok`
- `kampanya_avantaji: özette geçen '1.000' sayısı ham metinde yok`

## Alan bazlı doluluk

| Alan | Doluluk |
|---|---|
| `kampanya_turu` | %100 |
| `kampanya_kosullari` | %82 |
| `kampanya_avantaji` | %65 |
| `kampanya_bitis` | %44 |
| `vade_ay_max` | %37 |
| `hedef_kitle` | %25 |
| `odul_miktari` | %17 |
| `kar_payi_orani` | %16 |
| `masrafsiz_mi` | %8 |
| `indirim_orani` | %7 |
| `finansman_tutari_max` | %6 |
| `alisveris_puani` | %3 |
| `tahsis_ucreti` | %3 |
| `urun_turu` | %0 |
| `taksit_sayisi` | %0 |
| `masraf_bilgisi` | %0 |

## Altın set metrikleri

- Altın set boyutu: **60** örnek (eşleşen: 60)

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| Sayısal alan doğruluğu | 0.950 | ≥ 0,90 | ✅ |
| Metinsel alan doğruluğu | ölçülmedi | ≥ 0,78 | — |
| **Makro-F1** | 0.785 _(%95 GA: 0.654–0.865)_ | ≥ 0,78 | ✅ |

> Metinsel alanlar altın sette etiketlenmiyor (ADR 008): yalnız LLM katmanından geliyorlar ve birebir string karşılaştırmasıyla ölçülemezler.

> 📏 **Güven aralığı 60 örnek üzerinden önyükleme (bootstrap) ile hesaplandı** — kayıtlar yerine konarak 400 kez yeniden örneklendi. Aralık genişse sebebi modelin kararsızlığı değil, altın setin küçüklüğüdür. **Sunumda makro-F1 tek başına değil, aralığıyla ve örnek sayısıyla söylenmelidir** — aynı disiplin H-02'de etiketleyici uyumu için de uygulandı.

### Alan bazlı doğruluk ve F1

> **Doğruluk sütununu tek başına okumayın.** Altın setin çoğu hücresi boş, dolayısıyla «iki taraf da boş» hücreler doğruluğu şişiriyor. *Hep boş* sütunu, hiçbir şey çıkarmayan bir sistemin alacağı doğruluktur: doğruluk o sütunun altındaysa, sistem o alanda hiçbir şey yapmamaktan daha kötüdür. F1 doğru negatifi saymaz, bu yüzden gerçek başarıyı gösterir.

> **N sütunu, F1 sütunu kadar önemlidir.** N, altın sette o alanın DOLU olduğu hücre sayısıdır (DP+YN). N=3 olan bir alanda tek bir kaydın düzelmesi F1'i 33 puan oynatır; oradaki 0,900 ile N=60 olan bir alandaki 0,900 aynı şey değildir. Küçük N'li satırları tek başına alıntılamayın.

| Alan | N | Doğruluk | Hep boş | Kesinlik | Duyarlılık | **F1** | DP/YP/YN |
|---|---|---|---|---|---|---|---|
| `kampanya_turu` | 60 | 0.850 | 0.000 | 0.850 | 0.850 | **0.850** | 51/9/9 |
| `urun_turu` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `hedef_kitle` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kar_payi_orani` | 10 | 0.983 | 0.833 | 0.909 | 1.000 | **0.952** | 10/1/0 |
| `finansman_tutari_max` | 5 🔸 | 0.917 | 0.917 | 0.500 | 0.600 | **0.545** | 3/3/2 |
| `vade_ay_max` | 20 | 0.900 | 0.667 | 0.818 | 0.900 | **0.857** | 18/4/2 |
| `taksit_sayisi` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `tahsis_ucreti` | 5 🔸 | 0.983 | 0.917 | 0.833 | 1.000 | **0.909** | 5/1/0 |
| `masraf_bilgisi` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `masrafsiz_mi` | 7 🔸 | 0.933 | 0.883 | 0.714 | 0.714 | **0.714** | 5/2/2 |
| `odul_miktari` | 3 🔸 | 0.967 | 0.950 | 0.667 | 0.667 | **0.667** | 2/1/1 |
| `indirim_orani` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `alisveris_puani` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kampanya_avantaji` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kampanya_bitis` | 14 | 0.933 | 0.767 | 0.786 | 0.786 | **0.786** | 11/3/3 |
| `kampanya_kosullari` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |

> ⚠️ = doğruluk «hep boş» tabanının altında. Bu alanlarda sistem boş olması gereken hücrelere değer yazıyor (yanlış pozitif); önce kesinliği düzeltmek gerekir.

> **DP/YP/YN** — doğru pozitif / yanlış pozitif / yanlış negatif. Yanlış değer hem YP hem YN sayılır: uydurulmuş bir değerdir ve aynı anda doğru cevap kaçırılmıştır.
