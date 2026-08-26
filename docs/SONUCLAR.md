# Değerlendirme Sonuçları

_Otomatik üretildi: 26.08.2026 16:45 · `make eval`_

> Bu dosya elle düzenlenmez. Sunumdaki her sayı buradan kopyalanır.

> ✅ **Güncel.** Çıkarım 26.08.2026 16:25'de `hibrit` yapılandırmasıyla koştu (1020 kayıt) ve o tarihten beri çıkarım kodu değişmedi.

## Veri kapsamı

- İşlenen kampanya: **1024**
- Banka sayısı: **9**
- Toplam alan: 16384 · Dolu: 4228

## Altın set gerektirmeyen metrikler

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| Şema geçerliliği | 1.00 | 1,00 | ✅ |
| **Halüsinasyon oranı** | %0.43 | ≤ %3 | ✅ |
| Alan doluluğu | %25.8 | — | — |
| Ortalama güven | 0.795 | — | — |
| **Kalkan yanlış blok oranı** | %0.0 | %0 | ✅ |
| Denetimsiz cevap parçası | %0.0 | %0 | ✅ |

## Sayısal doğrulama kalkanı (köken tipli)

Kalkanın iki yönlü bir hata uzayı var; ikisi ayrı ölçülür:

- **Yanlış blok** — meşru cevabı engelleme: **0/35** (`eval/sorular.yaml`, 42 soru)
- **Gevşeme** — uydurma sayıyı geçirme: eşik değil ikili doğruluk; `tests/test_kalkan_kokenli.py` koruyor

| Parça kökeni | Sayı | Doğrulama ölçütü |
|---|---|---|
| `yapisal` | 21 | yapısal kayıtta birebir karşılığı olmalı |
| `alinti` | 38 | kaynak metnin alt dizesi + sayıları alıntının içinde |
| `sistem` | 8 | sayılar `hesap` girdilerinden yeniden üretilebilmeli |
| `duz` | 24 | sayı içeremez (yapıcıda denetlenir) |
| `denetimsiz` | 0 | **miras yol — atlanır ama sayılır** |

> ✅ **Meşru soruların hiçbiri engellenmedi.** 18 Ağustos ölçümünde bu oran %14,3'tü (35 meşru sorunun 5'i): bankanın kendi metnindeki sayılar — bir vaka **6698 sayılı KVKK kanun numarası** — yapısal alanda karşılığı olmadığı için «uydurma» sayılıyordu. Kalkan gevşetilmedi; parçaların kökeni bildirildi ve alıntılar KAYNAĞINA karşı denetlenir oldu. Aynı değişiklik, hesap bölümündeki kör noktayı da kapattı (skor ve ağırlıklar artık yeniden üretiliyor).

## Yöntem dağılımı (ablasyonun temeli)

| Yöntem | Alan sayısı |
|---|---|
| `llm` | 2826 |
| `kural` | 899 |
| `hibrit` | 503 |

## Halüsinasyon örnekleri (hata analizi)

- `kampanya_kosullari: özette geçen '60' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '22,50' sayısı ham metinde yok`
- `kampanya_avantaji: özette geçen '5.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '400.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '15.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '200.000' sayısı ham metinde yok`
- `kampanya_avantaji: özette geçen '1.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '15.000' sayısı ham metinde yok`
- `kampanya_kosullari: özette geçen '200.000' sayısı ham metinde yok`
- `kampanya_avantaji: özette geçen '1.000' sayısı ham metinde yok`

## Alan bazlı doluluk

| Alan | Doluluk |
|---|---|
| `kampanya_turu` | %100 |
| `kampanya_kosullari` | %83 |
| `kampanya_avantaji` | %64 |
| `kampanya_bitis` | %44 |
| `vade_ay_max` | %37 |
| `hedef_kitle` | %25 |
| `odul_miktari` | %17 |
| `kar_payi_orani` | %16 |
| `indirim_orani` | %7 |
| `finansman_tutari_max` | %6 |
| `masrafsiz_mi` | %6 |
| `tahsis_ucreti` | %4 |
| `alisveris_puani` | %3 |
| `urun_turu` | %0 |
| `taksit_sayisi` | %0 |
| `masraf_bilgisi` | %0 |

## Altın set metrikleri

- Altın set boyutu: **98** örnek (eşleşen: 98)

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| Sayısal alan doğruluğu | 0.932 | ≥ 0,90 | ✅ |
| Metinsel alan doğruluğu | ölçülmedi | ≥ 0,78 | — |
| **Makro-F1** | 0.820 _(%95 GA: 0.757–0.868)_ | ≥ 0,78 | ✅ |

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
| `kar_payi_orani` | 21 | 0.928 | 0.784 | 0.810 | 0.810 | **0.810** | 17/4/4 |
| `finansman_tutari_max` | 16 | 0.938 | 0.835 | 0.846 | 0.688 | **0.759** | 11/2/5 |
| `vade_ay_max` | 36 | 0.887 | 0.629 | 0.789 | 0.833 | **0.811** | 30/8/6 |
| `taksit_sayisi` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `tahsis_ucreti` | 17 | 0.959 | 0.825 | 0.842 | 0.941 | **0.889** | 16/3/1 |
| `masraf_bilgisi` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `masrafsiz_mi` | 20 | 0.959 | 0.796 | 0.864 | 0.950 | **0.905** | 19/3/1 |
| `odul_miktari` | 14 | 0.948 | 0.856 | 0.714 | 0.714 | **0.714** | 10/4/4 |
| `indirim_orani` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `alisveris_puani` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kampanya_avantaji` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |
| `kampanya_bitis` | 28 | 0.949 | 0.714 | 0.862 | 0.893 | **0.877** | 25/4/3 |
| `kampanya_kosullari` | 0 | — | — | ölçülmedi | ölçülmedi | **ölçülmedi** | 0/0/0 |

> ⚠️ = doğruluk «hep boş» tabanının altında. Bu alanlarda sistem boş olması gereken hücrelere değer yazıyor (yanlış pozitif); önce kesinliği düzeltmek gerekir.

> **DP/YP/YN** — doğru pozitif / yanlış pozitif / yanlış negatif. Yanlış değer hem YP hem YN sayılır: uydurulmuş bir değerdir ve aynı anda doğru cevap kaçırılmıştır.

## Ablasyon tablosu

Beş yapılandırma **aynı kod yolundan, tek süreçte** koşulur; yalnız katman ve
ajan bayrakları değişir. Ayrı kod yolu yazmak ölçümü karşılaştırılamaz hâle getirirdi.

İlk üç satır *hangi çıkarım katmanı ne katıyor*, son iki satır *hangi ajan ne katıyor*
sorusunu cevaplar: `hibrit` → `hibrit_elestirmensiz` farkı **eleştirmen ajanının**,
`hibrit` → `tam` farkı **yüklem ajanının** katkısıdır. `tam`, `make extract`'in
koştuğu üretim yapılandırmasıdır.

```bash
make ablasyon            # beş yapılandırma, tek komut, tek kod izi
make ablasyon altin=1    # yalnız altın set korpusunda (hızlı)
make eval-ablation       # tabloyu bu dosyaya bas
```

| Yapılandırma | Kâr payı F1 | Vade F1 | Makro-F1 | Halüsinasyon | Doluluk |
|---|---|---|---|---|---|
| Yalnız kural (regex) | 0.780 | 0.779 | **0.691** | %0.00 | %9.2 |
| Yalnız LLM (şema kısıtlı) | 0.581 | 0.105 | **0.498** | %0.49 | %20.1 |
| Hibrit (kural + LLM) | 0.810 | 0.779 | **0.794** | %0.32 | %26.3 |
| Hibrit · eleştirmen KAPALI | 0.810 | 0.779 | **0.791** | %0.63 | %26.4 |
| **Tam hiyerarşi (bizim)** | 0.810 | 0.827 | **0.819** | %0.36 | %25.8 |

