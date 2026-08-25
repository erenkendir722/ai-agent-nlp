# Değerlendirme Sonuçları

_Otomatik üretildi: 25.08.2026 16:31 · `make eval`_

> Bu dosya elle düzenlenmez. Sunumdaki her sayı buradan kopyalanır.

> ✅ **Güncel.** Çıkarım 25.08.2026 16:31'de `hibrit` yapılandırmasıyla koştu (1023 kayıt) ve o tarihten beri çıkarım kodu değişmedi.

## Veri kapsamı

- İşlenen kampanya: **1024**
- Banka sayısı: **9**
- Toplam alan: 16384 · Dolu: 4232

## Altın set gerektirmeyen metrikler

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| Şema geçerliliği | 1.00 | 1,00 | ✅ |
| **Halüsinasyon oranı** | %0.45 | ≤ %3 | ✅ |
| Alan doluluğu | %25.8 | — | — |
| Ortalama güven | 0.793 | — | — |
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
| `llm` | 2844 |
| `kural` | 893 |
| `hibrit` | 495 |

## Halüsinasyon örnekleri (hata analizi)

- `kampanya_kosullari: özette geçen '01.01.2026' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '60' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '1,5' sayısı ham metinde yok`
- `kampanya_avantaji: özette geçen '5.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '400.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '2.500.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '15.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '200.000' sayısı ham metinde yok`
- `kampanya_avantaji: özette geçen '1.000' sayısı ham metinde yok`
- `kampanya_avantaji: özette geçen '1.250' sayısı ham metinde yok`

## Alan bazlı doluluk

| Alan | Doluluk |
|---|---|
| `kampanya_turu` | %100 |
| `kampanya_kosullari` | %84 |
| `kampanya_avantaji` | %67 |
| `kampanya_bitis` | %44 |
| `vade_ay_max` | %37 |
| `hedef_kitle` | %24 |
| `odul_miktari` | %17 |
| `kar_payi_orani` | %16 |
| `indirim_orani` | %7 |
| `finansman_tutari_max` | %6 |
| `masrafsiz_mi` | %5 |
| `alisveris_puani` | %3 |
| `tahsis_ucreti` | %3 |
| `urun_turu` | %0 |
| `taksit_sayisi` | %0 |
| `masraf_bilgisi` | %0 |

## Altın set metrikleri

- Altın set boyutu: **98** örnek (eşleşen: 98)

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| Sayısal alan doğruluğu | 0.887 | ≥ 0,90 | ❌ |
| Metinsel alan doğruluğu | ölçülmedi | ≥ 0,78 | — |
| **Makro-F1** | 0.708 _(%95 GA: 0.621–0.774)_ | ≥ 0,78 | ❌ |

> Metinsel alanlar altın sette etiketlenmiyor (ADR 008): yalnız LLM katmanından geliyorlar ve birebir string karşılaştırmasıyla ölçülemezler.

> 📏 **Güven aralığı 98 örnek üzerinden önyükleme (bootstrap) ile hesaplandı** — kayıtlar yerine konarak 400 kez yeniden örneklendi. Aralık genişse sebebi modelin kararsızlığı değil, altın setin küçüklüğüdür. **Sunumda makro-F1 tek başına değil, aralığıyla ve örnek sayısıyla söylenmelidir** — aynı disiplin H-02'de etiketleyici uyumu için de uygulandı.

### Alan bazlı doğruluk ve F1

> **Doğruluk sütununu tek başına okumayın.** Altın setin çoğu hücresi boş, dolayısıyla «iki taraf da boş» hücreler doğruluğu şişiriyor. *Hep boş* sütunu, hiçbir şey çıkarmayan bir sistemin alacağı doğruluktur: doğruluk o sütunun altındaysa, sistem o alanda hiçbir şey yapmamaktan daha kötüdür. F1 doğru negatifi saymaz, bu yüzden gerçek başarıyı gösterir.

> **N sütunu, F1 sütunu kadar önemlidir.** N, altın sette o alanın DOLU olduğu hücre sayısıdır (DP+YN). N=3 olan bir alanda tek bir kaydın düzelmesi F1'i 33 puan oynatır; oradaki 0,900 ile N=60 olan bir alandaki 0,900 aynı şey değildir. Küçük N'li satırları tek başına alıntılamayın.

| Alan | N | Doğruluk | Hep boş | Kesinlik | Duyarlılık | **F1** | DP/YP/YN |
|---|---|---|---|---|---|---|---|
| `kampanya_turu` | 98 | 0.796 | 0.000 | 0.796 | 0.796 | **0.796** | 78/20/20 |
| `urun_turu` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `hedef_kitle` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kar_payi_orani` | 16 | 0.878 | 0.837 | 0.579 | 0.688 | **0.629** | 11/8/5 |
| `finansman_tutari_max` | 13 | 0.907 | 0.866 | 0.667 | 0.462 | **0.545** | 6/3/7 |
| `vade_ay_max` | 31 | 0.845 | 0.680 | 0.692 | 0.871 | **0.771** | 27/12/4 |
| `taksit_sayisi` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `tahsis_ucreti` | 16 | 0.867 | 0.837 | 0.500 | 0.375 | **0.429** | 6/6/10 |
| `masraf_bilgisi` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `masrafsiz_mi` | 17 | 0.959 | 0.827 | 0.810 | 1.000 | **0.895** | 17/4/0 |
| `odul_miktari` | 14 | 0.939 | 0.857 | 0.667 | 0.714 | **0.690** | 10/5/4 |
| `indirim_orani` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `alisveris_puani` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kampanya_avantaji` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kampanya_bitis` | 28 | 0.959 | 0.714 | 0.897 | 0.929 | **0.912** | 26/3/2 |
| `kampanya_kosullari` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |

> ⚠️ = doğruluk «hep boş» tabanının altında. Bu alanlarda sistem boş olması gereken hücrelere değer yazıyor (yanlış pozitif); önce kesinliği düzeltmek gerekir.

> **DP/YP/YN** — doğru pozitif / yanlış pozitif / yanlış negatif. Yanlış değer hem YP hem YN sayılır: uydurulmuş bir değerdir ve aynı anda doğru cevap kaçırılmıştır.
