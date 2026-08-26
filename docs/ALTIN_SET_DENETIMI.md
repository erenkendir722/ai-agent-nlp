# Altın Set Denetimi — 25 Ağustos 2026

> 📁 **26 Ağustos notu — dosya yerleşimi değişti.** Aşağıdaki metin
> `etiketleme_ek_<ad>.csv` dosyalarından söz ediyor; o dosyalar 26 Ağustos'ta
> `etiketleme_<ad>.csv` içine birleştirildi (`tur` kolonu turu ayırıyor).
> Rapor 25 Ağustos'un kaydı olduğu için dosya adları **bilerek değiştirilmedi**
> — o gün gerçekten öyleydi. Uyum bloğu (`etiketleme_uyum_*`,
> `etiketleme_ek_uyum_*`) birleştirilmedi: bulgu 1'in konusu olan
> etiketleyici uyum ölçümü tam da o dosyaların ayrı olmasına dayanıyor.


Bu dosya `data/gold/` altındaki 16 etiketleme CSV'sinin, `altin_set.jsonl`'in,
`metinler/` klasörünün ve `ornek_listesi.json`'ın tam denetimidir. Denetim
çalışma ağacı ile `HEAD` karşılaştırılarak yapıldı; denetim sırasında hiçbir
etiket değiştirilmedi.

> **Durum (25 Ağustos, akşam):** ilk 9 bulgunun **8'i kapatıldı**; 9. bulgunun
> etiketleri yazıldı ama **kaynağı yapay zekâ olduğu için Esra'nın onayını
> bekliyor.** Düzeltmeler sırasında **dört bulgu daha** çıktı (10–13); üçü
> kapatıldı, biri (13) kapatılamaz cinsten — belgelendi.
>
> Tam korpus yeniden çıkarıldı (1022 kayıt, EVREN) ve `SONUCLAR.md` **✅ Güncel**.

---

## Özet

| # | Bulgu | Şiddet | Durum |
|---|---|---|---|
| 1 | Uyum bloğundaki bağımsız etiketler ezildi | 🔴 | ✅ kapandı |
| 2 | ADR 012'nin üç kaydından ikisinin etiketi geri alındı | 🔴 | ✅ kapandı |
| 3 | `masrafsiz_mi` tek sınıflı — pozitif örnek sıfır | 🔴 | ✅ kapandı |
| 4 | `altin_set.jsonl` ve `SONUCLAR.md` CSV'lerle uyumsuz | 🟠 | ✅ kapandı |
| 5 | `denetle` genişletme dosyalarına hiç bakmıyor | 🟠 | ✅ kapandı |
| 6 | `ornek_listesi.json` 98 kaydın yalnız 60'ını belgeliyor | 🟠 | ✅ kapandı |
| 7 | 12 öksüz metin dosyası | 🟡 | ✅ kapandı |
| 8 | `?` hiç kullanılmamış — 53 hücrede sessiz "metinde YOK" iddiası | 🟡 | ✅ kapandı |
| 9 | `etiketleme_ek_esra.csv` zayıf dolduruldu | 🟡 | ⚠️ **Esra onayı bekliyor** |
| 10 | `GOREVLER.md`'deki %80,8 hiçbir zaman veriden üretilmemiş | 🔴 | ✅ kapandı |
| 11 | Okuma kâğıtları da genişletme turunu görmüyordu | 🟠 | ✅ kapandı |
| 12 | `MALIYET_TABLOSU` vetosu doğru kolonu da kesiyordu | 🔴 | ✅ kapandı |
| 13 | EVREN sapması **sayısal alanlara da** vuruyor | 🟠 | 📌 belgelendi |

**Ölçüye etkisi** (98 kayıt, taze çıkarım, `SONUCLAR.md` artık ✅ Güncel):

| | önce | sonra |
|---|---|---|
| Makro-F1 | 0,708 | **0,724** |
| Sayısal doğruluk | 0,887 | **0,895** |
| `masrafsiz_mi` pozitif örnek | 0 | **2** |
| `tahsis_ucreti` F1 (ilk 60, taze) | 0,000 | **0,364** |

> ⚠️ **Bu sayılar ±0,01 gürültü taşıyor** — bkz. bulgu 13. «0,72» demek
> doğrudur, «0,724» yanlış bir kesinlik iddiasıdır.

Sözleşme ihlali (`make altin-denetle` anlamında) **hiçbir dosyada yok** —
16 CSV'nin tamamı şema kısıtlarına uygun. Aşağıdaki bulgular biçim değil
**ölçüm geçerliliği** sorunlarıdır.

---

## 🔴 1. Uyum bloğundaki bağımsız etiketler ezildi

`etiketleme_uyum_{eren,samet,görkem,esra}.csv` çalışma ağacında **bayt
düzeyinde aynı** (md5 `028131a08e2807bdf2e1516aa33e417f`). `HEAD`'de dördü de
farklıydı.

| | HEAD | çalışma ağacı |
|---|---|---|
| Uyum oranı (dolu alanlar) | **%79,2** | %100,0 |
| Ham oran (boşlar dahil) | %93,8 | %100,0 |
| Ayrışan karar sayısı | 5 | 0 |

`make altin-uyum` şu an şunu basıyor:

```
🚨 KOPYA ŞÜPHESİ — uyum oranı bu haliyle GEÇERSİZ
❌ Bu oran SUNUMDA KULLANILAMAZ
```

Bu, [`GOREVLER.md`](../GOREVLER.md) H-02 satırındaki *«Kopya şüphesi YOK —
detektör sessiz, etiketleme bağımsız yapıldı, %80,8»* kaydıyla doğrudan
çelişiyor.

**Silinen beş gerçek ayrışma:**

| Kayıt | Alan | Eren | Samet | Görkem | Esra |
|---|---|---|---|---|---|
| `0212-cb6a4dc1dc98` | `kampanya_turu` | yeni_musteri | yeni_musteri | **yatirim_urunu** | yeni_musteri |
| `0212-cb6a4dc1dc98` | `odul_miktari` | 2000 | 2000 | **10000** | 2000 |
| `0206-d08e26c033db` | `kampanya_turu` | ihtiyac_finansmani | ihtiyac_finansmani | ihtiyac_finansmani | **finansman** |
| `0206-d08e26c033db` | `kar_payi_orani` | 0.99 | 0.99 | **1.00** | 0.99 |
| `0203-cfc1e9a26a6c` | `kampanya_turu` | konut_finansmani | **finansman** | konut_finansmani | konut_finansmani |

Genişletme bloğunda (`etiketleme_ek_uyum_*.csv`) da dört ayrışmadan üçü aynı
şekilde düzleşmiş. Ayrıca `etiketleme_ek_uyum_eren.csv` ile
`etiketleme_ek_uyum_esra.csv` **`HEAD`'de de birebir aynıydı** (md5
`772576119f88b5c83ea5e303b1f81749`) — genişletme turunun uyum bloğu baştan
dört değil üç bağımsız etiketleyiciyle ölçülmüş.

**Neden önemli:** uzlaşı toplantısı yapıp ortak karara varmak meşrudur, ama
uzlaşı kararı **bağımsız etiketlerin üstüne yazılmamalıdır**. Yazılırsa
etiketleyiciler arası uyum ölçümü yok olur ve «etiketleme uzlaşmamız %X»
cümlesi kurulamaz hâle gelir.

## 🔴 2. ADR 012'nin üç kaydından ikisinin etiketi geri alındı

[`docs/kararlar/012-sifir-kar-payi-beyani.md`](kararlar/012-sifir-kar-payi-beyani.md)
üç kaydı tek tek inceleyip *«etiketler doğruydu, kaçıran sistemdi»* sonucuna
varmış ve sistem buna göre düzeltilmişti.

| ADR'deki kayıt | Metindeki dayanak | Durum |
|---|---|---|
| `0203-7ab986a92e91` (Görkem) | tabloda birebir `0%` | ✅ duruyor |
| `0205-9f9ed7696f23` (uzlaşı) | «vade farksız 6 taksit» | ❌ `kar_payi_orani 0 → boş`, `vade_ay_max 6 → boş` — dört dosyada birden |
| `0205-735109071c75` (Esra) | «vade farksız 2 ile 5 taksit» | ❌ `kar_payi_orani 0 → boş`, `vade_ay_max 5 → boş`, `masrafsiz_mi evet → boş` |

**Sonuç:** ADR'nin düzelttiği iki doğru pozitif, bu haliyle **yanlış pozitif**
olarak sayılacak. Yani sistemde yapılan düzeltme metrikte cezaya dönüşüyor.

## 🔴 3. `masrafsiz_mi` tek sınıflı — pozitif örnek sıfır

Tüm CSV'lerdeki 29 dolu `masrafsiz_mi` hücresinin **hepsi `hayır`**. Tek `evet`
yukarıdaki `0205-735109071c75` kaydındaydı ve bu turda silindi.

[`docs/SONUCLAR.md`](SONUCLAR.md) tablosundaki `masrafsiz_mi | 17 | F1 0.895 |
17/4/0` satırı bu yüzden yalnız *«hayır diyebilme»* becerisini ölçüyor —
kampanyanın masrafsız olduğunu **tespit edebilme** becerisi hiç ölçülmüyor.
Katılım bankacılığında «masrafsız» başlık iddiası olduğu için bu ciddi bir
ölçüm boşluğu.

**Kural katmanının 0,91 güvenle `True` bulduğu, insanın boş bıraktığı iki aday:**

- `0203-4a4c087b579a` — *«masrafsız bir bankacılık sunuyoruz»*, *«Masrafsız Hesap»*,
  *«Masrafsız Para Transferi»*
- `0206-32cbb264a824` — *«Dosya Masrafsız Finansman Fırsatı … dosya masrafı
  olmadan kullanabilirsin»*

İkisi de insan gözüyle karara bağlanmalı; karar `ETIKETLEME_KILAVUZU.md`
kararlar defterine yazılmalı.

## 🟠 4. `altin_set.jsonl` ve `SONUCLAR.md` CSV'lerle uyumsuz

`derle` şu an koşsa **3 kayıt değişir**:

```
0205-9f9ed7696f23  vade_ay_max: 6.0 → None
0206-d08e26c033db  kar_payi_orani: 0.99 → 1.0
0206-d2ea9ee0f388  vade_ay_max: None → 3.0 | finansman_tutari_max: None → 50000.0
```

`SONUCLAR.md` 25.08.2026 16:31'de üretildi, CSV'ler 17:05–17:15'te değişti.
Yani yayımlanan sayılar mevcut etiketlerden gelmiyor.

Ayrıca `0206-d08e26c033db` kaydında `kar_payi_orani` 0.99 → 1.00 değişimi bir
**karardır**: metin hem tabloda `Kâr Oranı | %1.00 |` hem düz yazıda
`0.99% oran avantajları ile` diyor. Hangisinin alınacağı kararlar defterine
yazılmalı.

## 🟠 5. `denetle` genişletme dosyalarına hiç bakmıyor

[`tools/altin_set.py`](../tools/altin_set.py) satır 1454:

```python
onekler = ("etiketleme_", UYUM_ONEK)
```

`EK_ONEK` ve `EK_UYUM_ONEK` listede yok. `derle` dördünü de okuyor (satır 655
ve 700), `denetle` ise sekiz dosyayı **hiç açmadan** `✅ Pushlayabilirsin`
diyor. Bu, `EK_UYUM_ONEK` docstring'inde yazılı olan 25 Ağustos `derle`
açığının aynısı — bu sefer `denetle` yolunda.

Elle koşturuldu: ek dosyalarda sözleşme ihlali **yok** (0 hata). Sorun bulunan
hata değil, açık kalan kapı.

## 🟠 6. `ornek_listesi.json` 98 kaydın yalnız 60'ını belgeliyor

`komut_genislet` `ORNEK_KAYDI`'nı hiç yazmıyor; yalnız `komut_ornekle` yazıyor
(satır 389). `ornek_listesi.json` hâlâ `"adet": 60` diyor ve genişletme
turunun 38 kaydı için tohum / dağılım / kişi ataması kaydı yok.

`TOHUM` sabitinin docstring'i şunu söylüyor: *«Jüri "bu 60 örneği nasıl
seçtiniz?" diye sorduğunda cevap "rastgele" değil, "şu tohumla katmanlı"
olmalı.»* Bu cevap şu an setin %39'u için verilemiyor.

## 🟡 7. 12 öksüz metin dosyası

`data/gold/metinler/` 110 `.txt` içeriyor, altın sette 98 kayıt var. Hiçbir
CSV'de geçmeyen 12 dosya — iptal edilmiş bir `genislet` koşusundan artakalma:

```
0203-d49fd46650dc  0205-f2ab3ac65c43  0206-1831a04541ca  0206-6673dd6a5a23
0209-6e6a3e087b27  0210-23a5ee5a3344  0210-f60abad8a1b0  0211-05bd14ec12f4
0212-a17b8a9fb71e  0214-2ae200e061f6  0214-a47c782088da  0214-b0cbc205fd4d
```

Tersi yok: altın setteki 98 kaydın **hepsinin** metin dosyası mevcut.

## 🟡 8. `?` hiç kullanılmamış — 53 hücrede sessiz "metinde YOK" iddiası

16 CSV'nin tamamında `?` yazılmış **sıfır** hücre var. Aracın sözleşmesine göre
boş hücre «metinde YOK» demektir ve cevap anahtarına öyle girer; bakılmadan
bırakılan hücreye `?` yazılmalıydı.

İnsanın boş bıraktığı ama sistemin değer bulduğu 53 hücre var (52'si yüksek
kesinlikli kural/hibrit katmandan):

| alan | boş ama sistem buldu | kural/hibrit olanı |
|---|---|---|
| `vade_ay_max` | 21 | 21 |
| `kar_payi_orani` | 10 | 10 |
| `masrafsiz_mi` | 7 | 7 |
| `tahsis_ucreti` | 6 | 5 |
| `kampanya_bitis` | 5 | 5 |
| `finansman_tutari_max` | 2 | 2 |
| `odul_miktari` | 2 | 2 |
| `kampanya_turu` | 0 | 0 |

Bunların bir kısmı **sistemin yanlış pozitifi** — ki ölçmek istediğimiz tam da
budur, dokunulmamalı. Örnek: `0206-0a6668cc5df3` ve `0206-4db63f5eca2f` için
kural katmanı `kampanya_bitis = 2020-11-30` buluyor; altın setin boş bırakması
doğru.

Bir kısmı ise **insan atlaması** — ve bunlar cevap anahtarını zehirler.
Gözden geçirilmesi gereken en olası adaylar:

```
kar_payi_orani        0206-b5db11e3633c → 3.59   (kural, güven 0.917)
                      0206-55c5393fc72f → 11.0   (kural, güven 0.592)
vade_ay_max           0213-8e662b576a6b → 12     (kural, güven 0.918)
                      0203-d7b3a1e8609d → 36     (kural, güven 0.918)
                      0205-54bc08fa0088 → 60     (kural, güven 0.918)
finansman_tutari_max  0205-a323f782dfd5 → 20000  (hibrit, güven 0.938)
tahsis_ucreti         0206-0a6668cc5df3 → 500    (kural, güven 0.846)
odul_miktari          0206-32cbb264a824 → 200    (kural, güven 0.856)
```

## 🟡 9. `etiketleme_ek_esra.csv` zayıf dolduruldu

Genişletme turunda çekirdek sekiz alanın doluluk oranı:

| dosya | dolu / gereken |
|---|---|
| `etiketleme_ek_eren.csv` | 28 / 72 |
| `etiketleme_ek_görkem.csv` | 26 / 64 |
| `etiketleme_ek_samet.csv` | 22 / 64 |
| **`etiketleme_ek_esra.csv`** | **13 / 64** |

Genişletme turunun amacı zayıf alanları (`finansman_tutari_max` N=5 vb.)
kapatmaktı; en az dolan sayfa bu amacı en az besliyor.

---

## 🔴 10. `GOREVLER.md`'deki %80,8 hiçbir zaman veriden üretilmemiş

Bulgu 1 düzeltilip bağımsız etiketler geri konunca oran %79,2 çıktı — ama
`GOREVLER.md` H-02 ve `eca1466` commit mesajı **%80,8** diyordu. Aradaki 1,6
puan araştırıldı ve sebebi bulundu: **böyle bir ölçüm hiç yapılmamış.**

`eca1466` ayrı bir çalışma ağacına alınıp KENDİ dosyalarıyla koşturuldu:

```
Karşılaştırılan alan çifti: 72 (dolu)
📊 UYUM ORANI: %79.2
```

Yani %80,8'i ilan eden commit'in kendisi %79,2 veriyor. CSV'ler, `_hucre_cozumle`,
`uyum_hesapla`, `ALAN_ADLARI` ve sayı ayrıştırma o tarihten beri **birebir aynı**
(tek tek karşılaştırıldı), dolayısıyla fark koddan da gelmiyor.

**Neden kimse fark etmedi:** `make altin-uyum` Windows konsolunda oranı basacağı
satırda çöküyordu —

```
print(f"\n  📊 UYUM ORANI: %{oran * 100:.1f} …")
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f4ca'
```

Oran ekrana hiç gelmedi; yazılan sayı tahmindi. Çökme giderildi
(`tools/altin_set.py:main`, `tools/gorevler.py`'deki düzeltmenin aynısı).
Aynı hata `eval/calistir.py`'de de vardı: `make eval` `SONUCLAR.md`'yi
yazdıktan SONRA çöküyor, yani kabuğa hata dönüp "metrikler tazelenmedi"
izlenimi veriyordu. O da giderildi.

## 🟠 11. Okuma kâğıtları da genişletme turunu görmüyordu

`okuma_kagitlari_yaz` (satır 1497) aynı eksik ön ek listesini taşıyordu:

```python
for onek in (UYUM_ONEK, "etiketleme_")
```

Yani genişletme turunun 38 kaydı için okuma kâğıdı **hiç üretilmedi.** Kâğıt,
etiketleyene alan alan aday cümleleri hazır veren tek araç — `komut_ornekle`
docstring'i *«etiketlemeyi ucuzlatan asıl şeyin ayrı bir adım olmaması
gerekiyor»* diyor. En çok ihtiyaç duyulduğu turda yoktu.

Bulgu 9 ile birlikte okunmalı: genişletme turunun en az dolan sayfasının
`etiketleme_ek_esra.csv` olmasının sebebi büyük ihtimalle budur.

Aynı ön ek listesi bu depoda artık **üç yerde** unutulmuş oldu (`derle`,
`denetle`, `okuma_kagitlari_yaz`). Üçü de düzeltildi ve üçünü birbirine
bağlayan testler yazıldı (`TestGenisletmeTuruDosyalari`).

## 🔴 12. `MALIYET_TABLOSU` vetosu doğru kolonu da kesiyordu

`bd7595e` `tahsis_ucreti`'ye `MALIYET_TABLOSU = ("toplam maliyet",)` vetosu
ekledi. Ama bağlam penceresi tablo satırında **komşu kolonların başlıklarını da
görüyor**:

```
Vade | Kâr Oranı | Tahsis Ücreti | Aylık Toplam Maliyet | ...
  3  |  3,67%    |    0,50%      |     5,07%            | ...
```

Hücrenin KENDİ başlığı `Tahsis Ücreti` olmasına rağmen, aynı satırdaki «Toplam
Maliyet» yüzünden veto `0,50%`'yi kesiyordu. Üstelik veto **kolon başlığı
kapısından ÖNCE** çalışıyor, yani doğru kapı değeri hiç görmüyordu.

Bilanço iki yönlü ölçüldü:

* Veto, **yazıldığı yanlış pozitifi hiç yakalamadı** — hedefi `157,50 ₺`, o
  değer LLM katmanından geliyor, `veto_ifadeleri` ise yalnız kural katmanına
  uygulanır.
* Buna karşılık **iki doğru pozitifi öldürdü** (ikisi de `hibrit`, güven 0,83).
  `tahsis_ucreti` F1'i ilk turun 60 kaydında 0,364 → **0,000**.

**Düzeltme:** `KuralTanimi.kolonun_asabilecegi_vetolar` eklendi — kolon başlığı
alanı doğrudan adlandırıyorsa veto düşer. Veto silinmedi; kolonsuz düz yazıda
hâlâ çalışıyor. Kodun kendi yorumu zaten bunu söylüyordu: *«Kolon başlığı
hücreyi DOĞRUDAN adlandırır: sahiplik iddiası en güçlü biçimidir.»*

Regresyon testi `tests/test_kural.py::TestTabloKolonAyrimi`'ye eklendi ve
`bd7595e` çalışma ağacında koşturulup **kırıldığı doğrulandı**.

## 🟠 13. EVREN sapması sayısal alanlara da vuruyor

`CLAUDE.md` şunu yazıyordu: *«8 kayıt × 4 koşuda oynayan alanların tamamı
serbest metindi; sayısal ve enum alanlarda sıfır sapma.»* O ölçüm 8 kayıtlıktı.
Altın setin **98 kaydı aynı kodla iki kez** çıkarıldığında:

```
oynayan hücre: 7 / 784 (%0,9) — hepsi sayısal/enum
  kampanya_turu 2 · tahsis_ucreti 2 · kar_payi_orani 1 · vade_ay_max 1 · masrafsiz_mi 1

örnek:  tahsis_ucreti 0,5 → 20,0        vade_ay_max 84 → 60
makro-F1:  koşu-1 0,735    koşu-2 0,724
```

**Sunumda anlamı:** `make eval` sayısı ±0,01 gürültü taşır. «Makro-F1 0,72»
savunulabilir; «0,724» yanlış bir kesinlik iddiasıdır. Daha önemlisi: bir
değişikliğin etkisi ancak bu bandın DIŞINDAysa gerçektir. `CLAUDE.md`
güncellendi.

---

## Yapılacaklar

- [x] **1.** Uyum bloğunun dört dosyası bağımsız etiketlere döndürüldü
      (`bd7595e^` hâli). Uyum %100 → **%79,2**, kopya alarmı sustu, 5 gerçek
      ayrışma geri geldi. Bonus: düzleştirmede `0212`'nin `kampanya_bitis`'i
      2026-09-17 yapılmıştı; metin *«Kampanya Dönemi: 16 Temmuz – 16 Ağustos
      2026»* diyor, yani dördünün ortak etiketi (2026-08-16) doğruydu.
      *(Rapordaki `git checkout HEAD` komutu artık iş görmez — o değişiklikler
      bu rapor yazıldıktan sonra `bd7595e`'ye commit'lendi.)*
- [x] **2.** ADR 012 geri kondu. `0205-9f9ed7696f23` madde 1 ile döndü;
      `0205-735109071c75` (`etiketleme_esra.csv`) cerrahi olarak düzeltildi —
      `kar_payi_orani=0`, `vade_ay_max=5`, `masrafsiz_mi=evet`. Aynı
      commit'teki diğer düzeltmeleri (`tahsis_ucreti 500→0.50` vb.) korundu.
- [x] **3.** `masrafsiz_mi` artık **2 pozitif** taşıyor (önce 0).
      `0206-32cbb264a824` → `evet` + `tahsis_ucreti=0`: dipnot *«dosya masrafı
      = tahsis ücreti»* diyor, muaf tutulan şey finansman masrafının kendisi.
      `0203-4a4c087b579a` → **boş bırakıldı**: sayfa baştan sona "masrafsız"
      diyor ama saydığı her şey hesap işletim ücreti / EFT / kart aidatı;
      finansmandan hiç söz etmiyor, 15 Ağu kuralı aynen geçerli. Sistemin
      0,91 güvenle bulduğu `True` gerçek bir yanlış pozitiftir ve ölçülmelidir.
- [x] **4.** `0206-d08e26c033db` → **%0,99.** Tablo (`%1.00`) örnek ödeme
      planıdır; sayfa oranı ayrıca ilan ediyor (*«0.99% oran avantajları»*) ve
      düşük uç müşteri lehinedir. Çoğunluk oyu zaten bunu veriyordu (4'te 3).
- [x] **5.** `denetle` artık dört ön eki de açıyor — 8 dosya yerine 16.
- [x] **6.** `ornek_listesi.json` v2'ye geçirildi: tur listesi tutuyor,
      `komut_genislet` kendi turunu deftere EKLİYOR (ilk turu ezmeden).
      24 Ağustos turu diskteki sayfalardan geri çatıldı. **98/98 kayıt
      belgeleniyor** (önce 60/98).
- [x] **7.** 12 öksüz metin silindi — 110 → 98, altın setle birebir.
      *Kaynağı raporda yazılandan farklı çıktı:* iptal edilmiş bir `genislet`
      koşusu değil, **12 Ağustos'taki ilk `ornekle` turu**; o tur 15 Ağustos'ta
      sıfırdan yeniden örneklenince (`f5f0d0a`) geçersizleşmiş. 12'sinin 12'si
      o turun örnekleminde, yenisinde hiçbiri yok.
- [x] **8.** 8 aday hücre kaynak metne dönülerek incelendi. **Beşi sistemin
      yanlış pozitifi** çıktı — kararlar defterindeki «`kaynak_url`'in ürünü»
      kuralı zaten kapatıyor, insan haklı, dokunulmadı:
      `0206-b5db11e3633c` (biten kampanyalar listesi), `0206-55c5393fc72f`
      (Günlük Hesap — getiri oranı, `kar_payi_orani` şemada *finansmanın aylık
      %*'sidir), `0213-8e662b576a6b` (12 taksit başka kampanyanın),
      `0203-d7b3a1e8609d` ve `0205-54bc08fa0088` (36/60 ay komşu ürünün).
      **Üçü karara bağlandı:** `0205-a323f782dfd5` → `finansman_tutari_max
      = 20000`; `0206-0a6668cc5df3` (tahsis) ve `0206-32cbb264a824` (ödül) →
      **`?`** — değer metinde VAR ama hangi ürüne ait olduğu seçilemiyor.
      Bu, 16 CSV'de `?` işaretinin **ilk kullanımıdır.**
- [~] **9.** ⚠️ **`etiketleme_ek_esra.csv` gözden geçirildi — AMA ETİKETLER
      YAPAY ZEKÂ TARAFINDAN YAZILDI, ESRA'NIN ONAYI GEREKİR.**

      Takım kararıyla (25 Ağu) sekiz kaydın ham metni okunup boş hücreler
      dolduruldu. **Kaynak insan değil, Claude'dur.** Bu satırlar jüriye
      «dört kişi etiketledi» diye sunulamaz; Esra tek tek onaylayana kadar
      geçici sayılmalıdır.

      **Ölçüde ne anlama geliyor:** çıkarım sistemi de bir dil modeli. Aynı
      cümleyi ikimiz aynı şekilde yanlış okursak hata «doğru cevap» sayılıp
      F1'i yapay yükseltir (bağıntılı hata). `finansman_tutari_max` (N=16) ve
      `odul_miktari` (N=14) küçük olduğu için bu risk oransal olarak büyüktür.
      Bu yüzden aşağıdaki ölçüm **iki türlü** raporlandı.

      **Yazılan hücreler — toplam 7, ikisi dışında hepsi zaten BOŞ kaldı:**

      | kayıt | alan | değer | dayanak |
      |---|---|---|---|
      | `0205-8f21909fe25c` | `kar_payi_orani` | `0` | *«vade farksız 5 taksit»* (15 Ağu kuralı) |
      | | `vade_ay_max` | `5` | aynı cümle. ⚠️ *Sayfada ayrıca «en fazla 6 taksit» var ama o mevzuat tavanı, ürünün teklifi değil — **Esra'nın bakması gereken ilk hücre budur**.* |
      | | `finansman_tutari_max` | `100` | *«kart limitinin %10'u kadar, en fazla 100 TL nakit avans»* (25 Ağu kuralı) |
      | `0206-0a6668cc5df3` | `kar_payi_orani` | `?` | hesaplama aracı sayfası; `financeID=16`'nın hangi ürün olduğu belirsiz |
      | | `vade_ay_max` | `?` | aynı |
      | | `finansman_tutari_max` | `?` | aynı |
      | | `masrafsiz_mi` | `hayır` | ürün fark etmeksizin her dipnotta tahsis/ipotek/ekspertiz ücreti yazıyor |

      **Asıl bulgu şu: sayfa zaten büyük ölçüde DOĞRUYDU.** Kalan 43 hücrenin
      doğru cevabı **boş** — o kayıtlar banka kartı tanıtımı, sadakat programı,
      market ParafPara kampanyası gibi sayfalar; finansman koşulu hiç
      içermiyorlar. Aracın sözleşmesinde boş hücre bir iddiadır («metinde
      YOK») ve doğru iddiadır.

      Yani **«%20 dolu» rakamı yanıltıcıydı.** `_cekirdek_ilerleme` dolu
      hücreyi sayıyor, «bakıldı ve yok» ile «hiç bakılmadı»yı ayırt edemiyor —
      bulgu 8'in ta kendisi. Kaptanın beklediği *«Esra'nın sayfası bitince
      `finansman_tutari_max` ve `odul_miktari` hedefe ulaşır»* sonucu bu
      yüzden gerçekleşmiyor: o sekiz sayfada aranan alanlar **yok**.
      `finansman_tutari_max` 15 → 16, `odul_miktari` 14 → 14.
- [x] **10.** Tam korpus `extract` (1022 kayıt, EVREN, ~18 dk) → `derle` →
      `eval` koşuldu. `SONUCLAR.md` artık **✅ Güncel** — bayat damgası kalktı.
      `GOREVLER.md` (H-02 + H-06), kararlar defteri (5 yeni satır, 16→21) ve
      `CLAUDE.md` (determinizm kaydı) tazelendi.
      `make test` **688** ✅, `make lint` ✅.
