# Altın Set Denetimi — 25 Ağustos 2026

Bu dosya `data/gold/` altındaki 16 etiketleme CSV'sinin, `altin_set.jsonl`'in,
`metinler/` klasörünün ve `ornek_listesi.json`'ın tam denetimidir. Denetim
çalışma ağacı ile `HEAD` karşılaştırılarak yapıldı; denetim sırasında hiçbir
etiket değiştirilmedi.

> **Durum:** bulgular tespit edildi, **düzeltmeler HENÜZ YAPILMADI.**
> Aşağıdaki «Yapılacaklar» listesi takım kararı bekliyor.

---

## Özet

| # | Bulgu | Şiddet | Durum |
|---|---|---|---|
| 1 | Uyum bloğundaki bağımsız etiketler ezildi | 🔴 | açık |
| 2 | ADR 012'nin üç kaydından ikisinin etiketi geri alındı | 🔴 | açık |
| 3 | `masrafsiz_mi` tek sınıflı — pozitif örnek sıfır | 🔴 | açık |
| 4 | `altin_set.jsonl` ve `SONUCLAR.md` CSV'lerle uyumsuz | 🟠 | açık |
| 5 | `denetle` genişletme dosyalarına hiç bakmıyor | 🟠 | açık |
| 6 | `ornek_listesi.json` 98 kaydın yalnız 60'ını belgeliyor | 🟠 | açık |
| 7 | 12 öksüz metin dosyası | 🟡 | açık |
| 8 | `?` hiç kullanılmamış — 53 hücrede sessiz "metinde YOK" iddiası | 🟡 | açık |
| 9 | `etiketleme_ek_esra.csv` zayıf dolduruldu | 🟡 | açık |

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

## Yapılacaklar

- [ ] **1.** `git checkout HEAD -- data/gold/etiketleme_uyum_*.csv` — %79,2
      savunulabilir bir sayıdır, %100 değildir. Uzlaşı kararları bağımsız
      etiketlerin üstüne değil, `ETIKETLEME_KILAVUZU.md` kararlar defterine
      yazılmalı.
- [ ] **2.** ADR 012'nin iki kaydını geri koy: `0205-9f9ed7696f23` (dört uyum
      dosyasında) ve `0205-735109071c75` (`etiketleme_esra.csv`).
- [ ] **3.** `masrafsiz_mi` için `0203-4a4c087b579a` ve `0206-32cbb264a824`
      kayıtlarını insan gözüyle karara bağla; kararı kararlar defterine yaz.
- [ ] **4.** `0206-d08e26c033db` için %1.00 mü %0.99 mu — karara bağla ve yaz.
- [ ] **5.** `tools/altin_set.py:1454` — `denetle`ye `EK_ONEK` ve
      `EK_UYUM_ONEK` eklensin.
- [ ] **6.** `komut_genislet` `ornek_listesi.json`'ı güncellesin (genişletme
      turunun tohumu, dağılımı, ataması kaydedilsin).
- [ ] **7.** 12 öksüz metin dosyası silinsin ya da neden durduğu yazılsın.
- [ ] **8.** Yukarıdaki 8 aday hücre kaynak metne dönülerek gözden geçirilsin.
- [ ] **9.** `etiketleme_ek_esra.csv` tamamlansın.
- [ ] **10.** Hepsi bittikten sonra: `make altin-derle` → `make eval` →
      `SONUCLAR.md` ve `GOREVLER.md` (H-02 uyum oranı, H-06 kutusu) tazelensin.
