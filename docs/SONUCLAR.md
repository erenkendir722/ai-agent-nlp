# Değerlendirme Sonuçları

_Otomatik üretildi: 27.08.2026 16:27 · `make eval`_

> Bu dosya elle düzenlenmez. Sunumdaki her sayı buradan kopyalanır.

> **BAYAT — bu sayıları sunuma kopyalamayın.**
> Çıkarım 27.08.2026 14:11'de koştu; çıkarım kodu o tarihten sonra değişti (677ae6c9186359c1 → f33faa847651b5aa).
> Kayıtlı koşu: `hibrit` yapılandırması, 4 kayıt.
> Düzeltmek için: `make extract && make eval`.

## Veri kapsamı

- İşlenen kampanya: **734**
- Banka sayısı: **9**
- Toplam alan: 11744 · Dolu: 3340

## Altın set gerektirmeyen metrikler

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| Şema geçerliliği | 1.00 | 1,00 | hedefte |
| **Halüsinasyon oranı** | %0.36 | ≤ %3 | hedefte |
| Alan doluluğu | %28.4 | — | — |
| Ortalama güven | 0.793 | — | — |
| **Kalkan yanlış blok oranı** | %0.0 | %0 | hedefte |
| Denetimsiz cevap parçası | %0.0 | %0 | hedefte |

## Sayısal doğrulama kalkanı (köken tipli)

Kalkanın iki yönlü bir hata uzayı var; ikisi ayrı ölçülür:

- **Yanlış blok** — meşru cevabı engelleme: **0/35** (`eval/sorular.yaml`, 42 soru)
- **Gevşeme** — uydurma sayıyı geçirme: eşik değil ikili doğruluk; `tests/test_kalkan_kokenli.py` koruyor

| Parça kökeni | Sayı | Doğrulama ölçütü |
|---|---|---|
| `yapisal` | 21 | yapısal kayıtta birebir karşılığı olmalı |
| `alinti` | 41 | kaynak metnin alt dizesi + sayıları alıntının içinde |
| `sistem` | 8 | sayılar `hesap` girdilerinden yeniden üretilebilmeli |
| `duz` | 24 | sayı içeremez (yapıcıda denetlenir) |
| `denetimsiz` | 0 | **miras yol — atlanır ama sayılır** |

> **Meşru soruların hiçbiri engellenmedi.** 18 Ağustos ölçümünde bu oran %14,3'tü (35 meşru sorunun 5'i): bankanın kendi metnindeki sayılar — bir vaka **6698 sayılı KVKK kanun numarası** — yapısal alanda karşılığı olmadığı için «uydurma» sayılıyordu. Kalkan gevşetilmedi; parçaların kökeni bildirildi ve alıntılar KAYNAĞINA karşı denetlenir oldu. Aynı değişiklik, hesap bölümündeki kör noktayı da kapattı (skor ve ağırlıklar artık yeniden üretiliyor).

## Yöntem dağılımı (ablasyonun temeli)

| Yöntem | Alan sayısı |
|---|---|
| `llm` | 2217 |
| `kural` | 732 |
| `hibrit` | 391 |

## Halüsinasyon örnekleri (hata analizi)

- `kampanya_kosullari: özette geçen '60' sayısı ham metinde yok`
- `kampanya_avantaji: özette geçen '5.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '400.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '2.500.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '15.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '200.000' sayısı ham metinde yok`
- `kampanya_avantaji: özette geçen '1.000' sayısı ham metinde yok`
- `kampanya_avantaji: özette geçen '7.500' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '100.000.000' sayısı ham metinde yok`
- `kampanya_avantaji: özette geçen '15.584' sayısı ham metinde yok`

## Alan bazlı doluluk

| Alan | Doluluk |
|---|---|
| `kampanya_turu` | %100 |
| `kampanya_kosullari` | %96 |
| `kampanya_avantaji` | %74 |
| `vade_ay_max` | %48 |
| `kampanya_bitis` | %44 |
| `hedef_kitle` | %28 |
| `kar_payi_orani` | %19 |
| `odul_miktari` | %14 |
| `indirim_orani` | %8 |
| `finansman_tutari_max` | %7 |
| `masrafsiz_mi` | %7 |
| `tahsis_ucreti` | %5 |
| `alisveris_puani` | %3 |
| `urun_turu` | %0 |
| `taksit_sayisi` | %0 |
| `masraf_bilgisi` | %0 |

## Altın set metrikleri

- Altın set boyutu: **92** örnek (eşleşen: 92)

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| Sayısal alan doğruluğu | 0.925 | ≥ 0,90 | hedefte |
| Metinsel alan doğruluğu | ölçülmedi | ≥ 0,78 | — |
| **Makro-F1** | 0.812 _(%95 GA: 0.753–0.865)_ | ≥ 0,78 | hedefte |

> Metinsel alanlar altın sette etiketlenmiyor (ADR 008): yalnız LLM katmanından geliyorlar ve birebir string karşılaştırmasıyla ölçülemezler.

> **Güven aralığı 92 örnek üzerinden önyükleme (bootstrap) ile hesaplandı** — kayıtlar yerine konarak 400 kez yeniden örneklendi. Aralık genişse sebebi modelin kararsızlığı değil, altın setin küçüklüğüdür. **Sunumda makro-F1 tek başına değil, aralığıyla ve örnek sayısıyla söylenmelidir** — aynı disiplin H-02'de etiketleyici uyumu için de uygulandı.

### Alan bazlı doğruluk ve F1

> **Doğruluk sütununu tek başına okumayın.** Altın setin çoğu hücresi boş, dolayısıyla «iki taraf da boş» hücreler doğruluğu şişiriyor. *Hep boş* sütunu, hiçbir şey çıkarmayan bir sistemin alacağı doğruluktur: doğruluk o sütunun altındaysa, sistem o alanda hiçbir şey yapmamaktan daha kötüdür. F1 doğru negatifi saymaz, bu yüzden gerçek başarıyı gösterir.

> **N sütunu, F1 sütunu kadar önemlidir.** N, altın sette o alanın DOLU olduğu hücre sayısıdır (DP+YN). N=3 olan bir alanda tek bir kaydın düzelmesi F1'i 33 puan oynatır; oradaki 0,900 ile N=60 olan bir alandaki 0,900 aynı şey değildir. Küçük N'li satırları tek başına alıntılamayın.

| Alan | N | Doğruluk | Hep boş | Kesinlik | Duyarlılık | **F1** | DP/YP/YN |
|---|---|---|---|---|---|---|---|
| `kampanya_turu` | 92 | 0.783 | 0.000 | 0.783 | 0.783 | **0.783** | 72/20/20 |
| `urun_turu` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `hedef_kitle` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kar_payi_orani` | 21 | 0.912 | 0.769 | 0.800 | 0.762 | **0.780** | 16/4/5 |
| `finansman_tutari_max` | 15 | 0.934 | 0.835 | 0.833 | 0.667 | **0.741** | 10/2/5 |
| `vade_ay_max` | 35 | 0.868 | 0.615 | 0.778 | 0.800 | **0.789** | 28/8/7 |
| `taksit_sayisi` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `tahsis_ucreti` | 17 | 0.967 | 0.813 | 0.889 | 0.941 | **0.914** | 16/2/1 |
| `masraf_bilgisi` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `masrafsiz_mi` | 19 | 0.957 | 0.793 | 0.857 | 0.947 | **0.900** | 18/3/1 |
| `odul_miktari` | 14 | 0.945 | 0.846 | 0.714 | 0.714 | **0.714** | 10/4/4 |
| `indirim_orani` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `alisveris_puani` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kampanya_avantaji` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kampanya_bitis` | 27 | 0.946 | 0.707 | 0.857 | 0.889 | **0.873** | 24/4/3 |
| `kampanya_kosullari` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |

> = doğruluk «hep boş» tabanının altında. Bu alanlarda sistem boş olması gereken hücrelere değer yazıyor (yanlış pozitif); önce kesinliği düzeltmek gerekir.

> **DP/YP/YN** — doğru pozitif / yanlış pozitif / yanlış negatif. Yanlış değer hem YP hem YN sayılır: uydurulmuş bir değerdir ve aynı anda doğru cevap kaçırılmıştır.
