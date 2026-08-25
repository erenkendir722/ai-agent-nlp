# Performans Değerlendirme Yöntemleri

*Şartname madde 6, doküman başlığı 10.*

> **Bu dosya YÖNTEMİ anlatır, sayıları değil.** Güncel sayıların tek kaynağı
> [`docs/SONUCLAR.md`](SONUCLAR.md)'dir ve o dosya `make eval` tarafından
> üretilir — elle düzenlenmez. Buradaki hiçbir cümle bir sayıya bağlı değildir;
> ölçüm yenilendiğinde bu dosya geçerliliğini korur.

Tek komut her şeyi üretir:

```bash
make eval        # metrikler -> docs/SONUCLAR.md
make ablasyon    # katman katkıları -> ablasyon tablosu
```

---

## 1. İki ayrı metrik ailesi

Metrikler, **altın set gerektirenler** ve **gerektirmeyenler** diye ikiye
ayrılır. Bu ayrım kasıtlıdır: altın set elle etiketlenir ve emek pahalıdır,
ama bazı kalite iddiaları tüm korpus üzerinde ölçülebilir. Güncel kayıt
sayıları [`SONUCLAR.md`](SONUCLAR.md)'de.

### Altın set gerektirmeyenler — tüm korpus

| Metrik | Ne ölçer | Hedef |
|---|---|---|
| Şema geçerliliği | Üretilen kayıtların şemaya uyma oranı | 1,00 |
| Halüsinasyon oranı | Özette geçip ham metinde bulunmayan sayı | ≤ %3 |
| Alan doluluğu | Doldurulan hücre / toplam hücre | — (tanısal) |
| Ortalama güven | Kanıt zincirinin bildirdiği güven | — (tanısal) |
| Kalkan yanlış blok oranı | Meşru cevabın engellenme oranı | %0 |
| Denetimsiz cevap parçası | Kalkanın atladığı parça oranı | %0 |

Doluluk ve güven **hedefsizdir** — bilerek. Yüksek doluluk iyi bir sistemin de
aşırı çıkarım yapan bir sistemin de belirtisi olabilir; tek başına okunamaz.

### Altın set gerektirenler — etiketli alt küme

| Metrik | Hedef |
|---|---|
| Sayısal alan doğruluğu | ≥ 0,90 |
| Metinsel alan doğruluğu | ≥ 0,78 |
| **Makro-F1** | ≥ 0,78 |

Metinsel alanlar altın sette etiketlenmez ([ADR 008](kararlar/008-altin-set-kapsami.md)):
serbest metin birebir dize karşılaştırmasıyla ölçülemez, ölçüyormuş gibi
yapmak sahte bir sayı üretirdi.

---

## 2. Neden yalnız doğruluk değil, F1 de

Doğruluk tek başına **yanıltıcıdır** ve bunun somut sebebi var: altın setin
hücrelerinin çoğu boştur. Doğruluk «iki taraf da boş» hücreleri doğru sayar,
dolayısıyla **hiçbir şey çıkarmayan bir sistem** seyrek alanlarda çok yüksek
doğruluk alır. Gerçek başarı, değer *üretilmesi gereken* hücrelerde ölçülür.

F1 doğru negatifi hiç saymaz; sayaç yalnız bir taraf değer ürettiğinde işler.
Bu yüzden aşırı çıkarım doğruluğu az, F1'i çok düşürür — istenen tam olarak
budur.

### Yuva doldurma (slot filling) sözleşmesi

| Sayaç | Koşul |
|---|---|
| **DP** | Altın dolu, sistem dolu, değerler eşit |
| **YP** | Sistem değer üretti ama isabet etmedi (altın boş ya da farklı) |
| **YN** | Altın dolu ama sistem ıskaladı (boş bıraktı ya da yanlış yazdı) |

**Yanlış bir değer hem YP hem YN sayılır.** Hem uydurulmuş bir değerdir, hem de
doğru cevap kaçırılmıştır. Tek sayaca yazmak ikisinden birini gizlerdi.

### Eşitlik ölçütü

Sayısal alanlarda **%1 göreli tolerans** uygulanır: `"50.000 TL"` ile
`"50 bin TL"` farklı yazımlardır, farklı değer değil. Metinsel karşılaştırma
kırpma ve küçük harfe indirme sonrası birebirdir.

### Ölçülmemiş, sıfır değildir

Bir alanda hiç pozitif hücre yoksa kesinlik/duyarlılık/F1 **`None`** döner,
`0.0` değil. Ölçülmemiş bir alanı başarısız göstermek, ölçmemekten kötüdür —
makro ortalamayı sahte bir sıfırla aşağı çekerdi.

---

## 3. Güven aralığı — sayının ne kadarı ölçüm, ne kadarı gürültü

Makro-F1 tek başına raporlanmaz; yanında **%95 önyükleme (bootstrap) güven
aralığı** verilir.

**Neden gerekli:** altın set küçüktür ve bazı alanların dolu hücre sayısı tek
hanelidir. Böyle bir tabanda tek bir kaydın düzelmesi o alanın F1'ini onlarca
puan oynatır. Aralıksız bir makro-F1, jürinin ilk sorusunda — *"kaç örnek
üzerinde?"* — savunulamaz hâle gelir.

**Neden önyükleme:** makro-F1 bir oran değil, oranların ortalamasıdır; Wilson
gibi oran aralıkları uygulanamaz. Kayıtları yerine koyarak yeniden örneklemek,
dağılım varsayımı yapmadan aralığı verir.

Üç uygulama kararı:

- Yeniden örnekleme **kayıt düzeyinde** yapılır, hücre düzeyinde değil —
  belirsizliğin kaynağı hangi kampanyaların seçildiğidir.
- **Tohum sabittir.** Aynı veri aynı aralığı vermelidir; yoksa rapor her koşuda
  oynar ve hangi sayının doğru olduğu bilinemez.
- Aralık, raporlanan sayıyla **aynı ölçüm yolunu** kullanır. Ayrı bir hesap
  yolu yazmak, aralığın ölçtüğü şeyin raporlanan sayı olmadığı anlamına gelirdi.

---

## 4. Ölçüm gürültüsü — bir sayı ne zaman gerçekten değişmiştir

Çıkarım EVREN'de koşar ve **EVREN bayt düzeyinde deterministik değildir**:
ortak vLLM sunucusundaki sürekli yığınlama yüzünden `temperature=0` ve sabit
tohumla bile aynı girdi farklı çıktı verebilir.

25 Ağustos'ta bu ölçüldü: altın setin tamamı **aynı kodla iki kez** çıkarıldı
(ölçümün kendisi [`ALTIN_SET_DENETIMI.md`](ALTIN_SET_DENETIMI.md) bulgu 13'te).
Oynayan hücre oranı binde birler seviyesindeydi ama **sayısal ve enum alanlara
da vuruyordu** — daha önceki 8 kayıtlık ölçüm bunu göremediği için «yalnız
serbest metin oynuyor» sanılıyordu.

**Pratik sonucu üç maddedir:**

1. `make eval` çıktısı **±0,01 bandında gürültü taşır.**
2. Sunumda makro-F1 **iki haneli** söylenir. Üç hane, sahip olmadığımız bir
   kesinliği iddia etmektir.
3. **Bir değişikliğin etkisi, ancak bu bandın dışındaysa gerçektir.** İki koşu
   arasındaki küçük farkı iyileşme saymak, gürültüyü başarı diye raporlamaktır.

Bayt düzeyinde tekrarlanabilirlik gereken durumda yerel yol kullanılır
(`LLM_SAGLAYICI=ollama`) — aynı kod yolu, deterministik sunucu.

---

## 5. Ablasyon — hangi katman ne kadar katkı veriyor

`make ablasyon` üç yapılandırmayı koşar (yalnız kural / yalnız LLM / hibrit) ve
katkıları tablolar.

Kritik kısıt: **üç satır da aynı kod sürümüyle, tek komutta üretilir.** Bu
kural ölçülmüş bir hatadan doğdu — ablasyon tablosunun satırları bir dönem
farklı kod sürümleriyle doldurulmuştu ve karşılaştırma anlamsızdı. Her koşu
kendi veritabanına yazar; üretim verisine dokunmaz.

Ablasyon ayrıca **kanıt doğrulaması** ve **yüklem denetimi** gibi tek tek
bileşenler için de bayrak taşır (`--elestirmen-yok`, `--yuklem-yok`). Böylece
"bu bileşen işe yarıyor mu?" sorusu iddia değil ölçüm olur.

---

## 6. Kalkanın iki yönlü hata uzayı

Sayısal doğrulama kalkanı sistemin en özgün iddiasıdır, bu yüzden **iki yönü de
ayrı ölçülür.** Tek yönü ölçmek yanıltıcı olurdu:

| Hata yönü | Sonucu | Nasıl ölçülür |
|---|---|---|
| **Çok sıkı** | Meşru cevabı engeller | `make eval` → yanlış blok oranı (hedef %0) |
| **Çok gevşek** | Uydurma sayıyı geçirir | `tests/test_kalkan_kokenli.py` — testler kırmızıya dönmeden gevşeyemez |

Yanlış blok oranı `eval/sorular.yaml`'daki doğal soru kümesi üzerinde ölçülür.

Ayrıca **denetimsiz parça oranı** raporlanır: kalkanın atladığı cevap
parçalarının payı. Bu görünmez bir muafiyet değil, **ölçülen bir borçtur** ve
hedefi sıfırdır.

---

## 7. Ölçümün güncelliği denetlenir

`docs/SONUCLAR.md` başında bir **tazelik damgası** taşır: çıkarımın hangi
tarihte, hangi yapılandırmayla, kaç kayıt üzerinde koştuğu ve o tarihten sonra
çıkarım kodunun değişip değişmediği. Kod değiştiyse rapor kendini «bayat»
işaretler.

Gerekçe: bayat bir metrik, yanlış bir metrikten daha tehlikelidir — yanlış olan
fark edilir, bayat olan doğru görünür.

---

## Ölçüm dosyaları

| Dosya | İçerik |
|---|---|
| [`docs/SONUCLAR.md`](SONUCLAR.md) | Güncel sayılar — `make eval` üretir |
| [`docs/HATA_ANALIZI.md`](HATA_ANALIZI.md) | Hata örnekleri ve sınıflandırma |
| [`docs/ALTIN_SET_DENETIMI.md`](ALTIN_SET_DENETIMI.md) | Altın setin kendi denetimi |
| [`docs/DAYANIKLILIK.md`](DAYANIKLILIK.md) | Bozuk/eksik girdiye karşı davranış |
| [`docs/GORULMEMIS_METIN.md`](GORULMEMIS_METIN.md) | Eğitimde görülmemiş metin sınaması |
| `eval/calistir.py` | Metriklerin tanımı ve hesabı |
| `eval/ablasyon.py` · `eval/kalkan.py` | Ablasyon ve kalkan ölçümü |
