# Makro-F1 0,724 → 0,78 — Sorun Neresi, Ne Denendi, Ne Kaldı

**Son güncelleme:** 25 Ağustos 2026, akşam
**Hedef:** şartname eşiği **makro-F1 ≥ 0,78** · **Şu an:** 0,724 (%95 GA 0,651–0,781)

Bu dosya "skoru nasıl yükseltiriz" sorusunun çalışma defteri. Ölçülmüş her
şey buraya yazılır — **denenip başarısız olanlar da**, çünkü aynı fikri iki kez
denemek en pahalı hatadır.

---

## 0. Önce şunu bilmek gerekiyor: sayı ±0,01 oynuyor

25 Ağustos'ta ölçüldü. **Aynı kod, aynı girdi, iki ayrı koşu:**

```
oynayan hücre: 7 / 784 (%0,9) — hepsi sayısal/enum alanlarda
  kampanya_turu 2 · tahsis_ucreti 2 · kar_payi_orani 1 · vade_ay_max 1 · masrafsiz_mi 1

örnek:  tahsis_ucreti 0,5 → 20,0        vade_ay_max 84 → 60
makro-F1:  koşu-1 0,735    koşu-2 0,724
```

Sebep: EVREN ortak bir vLLM sunucusu, sürekli yığınlama yapıyor; `temperature=0`
ve sabit tohum bayt düzeyinde determinizm getirmiyor.

**Bunun üç sonucu var ve üçü de bu belgenin geri kalanını yönetiyor:**

1. Sunumda **"0,72"** denir. "0,724" demek yanlış bir kesinlik iddiasıdır.
2. Bir değişikliğin etkisi ancak **±0,01 bandının dışındaysa** gerçektir.
   Tek koşuda "yükseldi" görmek kanıt değildir.
3. Küçük iyileştirmeler ölçülemez. Bu yüzden aşağıdaki liste **etki
   büyüklüğüne göre** sıralı, "kolaylığa" göre değil.

> Bayt düzeyinde tekrarlanabilirlik gerekirse: `LLM_SAGLAYICI=ollama`.

---

## 1. Makro-F1 neden bu kadar kırılgan

Makro-F1 **sekiz alanın düz ortalaması**. Ağırlık yok — `kampanya_turu` 98
örnekte ölçülüyor, `odul_miktari` 14'te, ama ortalamaya ikisi de 1/8 giriyor.

25 Ağustos, 98 kayıtlık altın set:

| alan | F1 | altın sette dolu N |
|---|---|---|
| `masrafsiz_mi` | 0,905 | 20 |
| `kampanya_bitis` | 0,877 | 28 |
| `kampanya_turu` | 0,806 | 98 |
| `vade_ay_max` | 0,795 | 34 |
| `kar_payi_orani` | 0,737 | 19 |
| `odul_miktari` | 0,714 | 14 |
| **`finansman_tutari_max`** | **0,615** | **16** |
| **`tahsis_ucreti`** | **0,345** | **17** |
| | **0,724** | |

**Aritmetik:** 0,78'e ulaşmak için sekiz F1'in toplamı 5,79'dan 6,24'e çıkmalı,
yani **+0,45**. Sekiz alanı birden düzeltmeye gerek yok:

```
tahsis_ucreti         0,345 → 0,80   →  makro-F1  0,781  ✅ tek başına yeter
finansman_tutari_max  0,615 → 0,80   →  makro-F1  0,747
ikisi birden                          →  makro-F1  0,804
```

**En dipteki iki alan hedefi tek başına belirliyor.** Diğer altı alana
dokunmanın getirisi düşük.

Aynı sebep tersinden de geçerli: N=14 olan `odul_miktari`'nda **tek kaydın
düzelmesi F1'i 4,4 puan oynatır** (0,714 → 0,759). Yani o alandaki "iyileşme" büyük ihtimalle
gürültüdür.

---

## 2. `tahsis_ucreti` — F1 0,345, en dipteki alan

### Hata dağılımı (98 kayıt)

```
DP 5  ·  YP 3  ·  YN 8  ·  YANLIŞ DEĞER 4
```

### Asıl sorun: alan ÇOK BİRİMLİ, sistem yanlış birimi seçiyor

`src/schema.py` bunu zaten beyan ediyor:

```python
# ÇOK BİRİMLİ — bankalar tahsis ücretini hem TL hem oran olarak yazıyor.
"tahsis_ucreti": frozenset({Birim.TL, Birim.YUZDE})
```

Altın setin 12 dolu hücresinin **10'u oran** (`0.5` = binde 5). Sistem ise
sık sık TL tutarını kapıyor:

| kayıt | altın | sistem | ne olmuş |
|---|---|---|---|
| `0206-016254a2c9b8` | 0.5 | **500.0** | örnek tablodaki TL tutarı |
| `0206-58784db119eb` | 0.5 | **500.0** | aynı |
| `0206-61006b35204e` | 0.5 | **500.0** | aynı |
| `0205-5eb79ce53d45` | 0.5 | **20.0** | alakasız sayı |
| `0206-4db63f5eca2f` | — | 500.0 | yanlış pozitif |

Metinlerde ikisi birden geçiyor:

> "Tahsis ücreti vergiler hariç finansman tutarının **binde 5'i** oranındadır."
> "Alınacak ücretler: 60 ay vadede **1000 TL** tahsis ücreti…"

İnsan oranı yazıyor (kampanyanın koşulu o), sistem örnek hesaplamadaki TL'yi
alıyor.

### 🔴 Bu bir KILAVUZ boşluğu, kod hatası değil

`docs/ETIKETLEME_KILAVUZU.md` kararlar defterinde **"tahsis ücreti TL mi oran
mı yazılır"** diye bir kural YOK. Etiketleyiciler sezgiyle oranı yazmış,
sistemin böyle bir tercihi yok.

**Yapılacak ilk iş kod değil, kural yazmak:** kararlar defterine
*"tahsis ücreti hem oran hem TL verilmişse **ORAN** yazılır — TL tutarı örnek
finansman tutarına bağlıdır, kampanyanın koşulu değildir"* satırı eklenmeli.
Sonra çıkarım tarafında aynı tercih uygulanmalı.

### İkincil sorun: 8 kaçırma

8 yanlış negatifin çoğu `0.5` değeri. Bunların bir kısmı yukarıdaki birim
tercihiyle birlikte çözülür.

---

## 3. `finansman_tutari_max` — F1 0,615

### Hata dağılımı (98 kayıt)

```
DP 8  ·  YP 1  ·  YN 7  ·  YANLIŞ DEĞER 1
```

Yanlış pozitif neredeyse yok — bu bir **duyarlılık (recall)** sorunu. Sistem
uydurmuyor, **bulamıyor**.

### 🔴 7 kaçırmanın 5'i TEK BİR DESEN — ve kodu zaten var

Kaçan beş kaydın hepsinde aynı kademeli taşıt finansmanı tablosu var:

```
0 TL – 400.000 TL       | 70% | 48 |
400.000 - 800.000 TL    | 50% | 36 |
800.000 - 1.200.000 TL  | 30% | 24 |
1.200.001 - 2.000.000 TL| 20% | 12 |
```

Kararlar defteri (15 Ağu) bu durumu zaten karara bağlamış:
*"`finansman_tutari_max` malın değeri mi? **Hayır**, bankanın verdiği tutar.
Kademeli tabloda **değer × oran, en büyüğü**"*

→ 800.000 × %50 = **400.000** = altın etiketle birebir aynı.

Ve bu hesabı yapan fonksiyon **zaten yazılmış**:
`src/extraction/kural.py::dilim_tablosundan_azami_finansman`. Test edildi,
beş kaydın dördünde doğru cevabı üretiyor:

```
0203-fcb188f0e696  → 400000.0  'biçim A: 4 oranlı satır, değer × oran'
0205-5eb79ce53d45  → 400000.0  'biçim A: 7 oranlı satır, değer × oran'
0206-d7223804788b  → 400000.0  'biçim A: 4 oranlı satır, değer × oran'
0214-ffb6cd0c6e56  → 400000.0  'biçim A: 4 oranlı satır, değer × oran'
0206-97aa0685d8fb  → None      'finansman tablosu işareti yok'
```

**Yani doğru cevap üretiliyor ama veritabanına ulaşmıyor.**

### 🔴 Nerede öldüğü bulundu — `uzlastirici.py:271`

25 Ağustos'ta tek kayıt üzerinde EVREN'li tam yol izlendi:

```
0206-d7223804788b   (altın = 400000)
   kural : 400000.0     ← DOĞRU
   llm   : 2000000.0    ← tablonun tepesini kapmış
   SONUÇ : None         ← elendi
   elenen=1
```

LLM'siz koşulduğunda **aynı kayıt 400000 veriyor**. Fark tek satırda:

```python
# src/extraction/uzlastirici.py
tablo_turevi = durum == "kural" and dilim_turevi_mi(alan_adi, sonuc, kayit.govde_metin)

if not tablo_turevi and not _makul_mu(alan_adi, sonuc, kayit.govde_metin):
    sonuc = Alan.yok()      # ← doğru cevap burada ölüyor
    durum = "elendi"
```

`dilim_turevi_mi` bu değerler için **`True` dönüyor** (doğrulandı). Ama baypas
`durum == "kural"` koşuluna bağlı. LLM de bir değer ürettiği için `durum`
`"celiski"` oluyor → baypas kapanıyor → makullük kapısı doğru cevabı eliyor.

Baypasın kendi docstring'i şunu söylüyor:

> *"Makullük ve yüklem kapıları CÜMLE ölçeğinde çalışır; dilim değeri ise
> tablonun tamamı üzerinden yapılan bir hesaptır ve hiçbir tek cümlede geçmez.
> Kapıların kusuru değil, uygulanamayacakları bir değer sınıfına
> uygulanmalarıdır."*

Bu gerekçe çelişki durumunda da aynen geçerli — koşul fazla dar yazılmış.

### Beklenen etki

Bu tek satır düzeltilirse `finansman_tutari_max` 4–5 doğru pozitif kazanır:

```
F1 0,615 → ~0,85   →  makro-F1 0,724 → ~0,754
```

**+0,03 — gürültü bandının (±0,01) belirgin biçimde dışında.** Bugüne kadar
bulunan en yüksek getirili tek değişiklik bu.

---

## 4. Denenen ve BAŞARISIZ olanlar — tekrar denemeyin

### ❌ "Kolon kapısı her zaman vetodan önce gelsin"

Tablo hücrelerinde kolon başlığının vetoyu ezmesi mantıklı görünüyordu.
Kural katmanı 98 altın kayıtta ölçüldü:

| | kural katmanı makro-F1 |
|---|---|
| mevcut | **0,6615** |
| "kolon önce" | 0,6522 ❌ |

`kar_payi_orani` +0,011 kazanıyor, `finansman_tutari_max` −0,086 kaybediyor
(yanlış pozitif 7 → 12). **Net zarar, geri alındı.**

### ❌ `MALIYET_TABLOSU` vetosunu düz veto listesinde tutmak (`bd7595e`)

"Toplam maliyet" ifadesi `tahsis_ucreti` vetosuna eklenmişti. Ölçüldü:

* Hedeflediği yanlış pozitifi **hiç yakalamadı** — o değer LLM katmanından
  geliyor, veto yalnız kural katmanına uygulanıyor.
* Buna karşılık **iki doğru pozitifi öldürdü**; `tahsis_ucreti` F1'i ilk turun
  60 kaydında 0,364 → **0,000**.

Düzeltildi (`kolonun_asabilecegi_vetolar`), regresyon testi yazıldı.

### ⚠️ "Esra'nın sayfası bitince zayıf alanlar hedefe ulaşır"

Tutmadı. Sekiz kaydın ham metni okundu: **43 hücrenin doğru cevabı boş.** O
sayfalar banka kartı tanıtımı, sadakat programı, market kampanyası — finansman
koşulu içermiyorlar.

```
finansman_tutari_max  15 → 16
odul_miktari          14 → 14
```

"%20 dolu" rakamı yanıltıcıydı: `_cekirdek_ilerleme` dolu hücreyi sayıyor,
*"baktım, yok"* ile *"hiç bakmadım"*ı ayırt edemiyor.

---

## 5. Yapılan ve İŞE YARAYAN düzeltmeler

| ne | etki |
|---|---|
| `tahsis_ucreti` veto regresyonu geri alındı | F1 (ilk 60) 0,000 → 0,364 |
| Tablo ayraç satırı (`---\|---`) kolon başlığını bozuyordu | kural katmanı `kar_payi_orani` 0,737 → 0,769 |
| Birimli hücre (`10.000 TL`, `12 Ay`) veri sayılmıyordu | aynı düzeltmenin parçası |
| Altın set bütünlüğü onarıldı (bağımsız etiketler, ADR 012) | makro-F1 0,708 → 0,724 |

---

## 6. Ölçümün kendisiyle ilgili açık sorunlar

Bunlar skoru yükseltmez ama **skorun anlamını** etkiler:

### 🔴 `data/katilim.db` şu an BAYAT

Ayraç düzeltmesi çıkarım kodunu değiştirdi; veritabanı o düzeltmeden önce
çıkarıldı.

```
DB koşusu   : b4f228c040f56dbf
şimdiki kod : 27d96fc8344c362e
```

`docs/SONUCLAR.md` hâlâ "✅ Güncel" diyor — **bu iddia artık doğru değil.**
`make extract && make eval` koşulmadan buradaki 0,724 sayısı da güncel değil.
Üstelik bölüm 3'teki düzeltme yapılırsa zaten yeniden çıkarım gerekecek.

### ⚠️ Altın sette 7 hücreyi yapay zekâ yazdı

`etiketleme_ek_esra.csv`. Esra'nın onayı bekleniyor. İki türlü ölçüldü:
bu satırlarla 0,724, onlarsız 0,727 — yani **şişirmiyor**, hatta biraz
katı. Yine de jüriye "dört kişi etiketledi" denemez.
Ayrıntı: `docs/ALTIN_SET_DENETIMI.md` bulgu 9.

### ⚠️ Zayıf alanların N'i hâlâ küçük

`odul_miktari` 14, `finansman_tutari_max` 16, `tahsis_ucreti` 17. Bu
büyüklüklerde F1 tek kayda çok duyarlı. Güven aralığı bu yüzden geniş
(0,651–0,781) ve **üst ucu zaten 0,78'in üstünde** — yani hedefe
ulaşıp ulaşmadığımızı mevcut örneklem büyüklüğüyle kesin söyleyemiyoruz.

### 📌 `kar_payi_orani` iki tur arasında uçurumda

İlk 60 kayıtta 0,952, genişletme turunun 38 kaydında 0,471. Genişletme turu
`hedefli_ornekle` ile **bilerek zor** seçildi (alanın konuşulduğu sayfalar),
yani bu beklenen yönde — ama büyüklüğü, ilk turdaki 0,952'nin fazla iyimser
olduğunu gösteriyor.

---

## 7. Sıradaki işler — etki büyüklüğüne göre

### 1️⃣ `uzlastirici.py` dilim baypası çelişkiyi de kapsasın

Bölüm 3. Tek satırlık koşul değişikliği, beklenen **+0,03**.
Yapıldıktan sonra `finansman_tutari_max`'ın yanlış pozitifi artmadığı
doğrulanmalı — `dilim_turevi_mi` fazla geniş dönerse kazanç geri gider.

### 2️⃣ `tahsis_ucreti` için birim kuralı

Bölüm 2. Önce kararlar defterine kural yazılacak (oran mı TL mi), sonra
çıkarım o tercihi uygulayacak. Beklenen **+0,03 ila +0,05** — ama bu ikisi
üst üste binmiyor, ikisi birden yapılırsa hedef geçilir.

### 3️⃣ Yeni bir `genislet` turu — yalnız iki zayıf alan için

`odul_miktari` ve `finansman_tutari_max`'ın N'ini 14–16'dan 25+'a çıkarmak.
Skoru yükseltmez ama **güven aralığını daraltır** ve yukarıdaki iki
düzeltmenin gerçekten işe yarayıp yaramadığını ölçülebilir kılar.
Mevcut 98 kaydı etiketlemeye devam etmek bu alanları büyütmüyor (bölüm 4).

### 4️⃣ Her değişiklikten sonra İKİ KEZ ölçün

Bölüm 0. Tek koşu ±0,01 oynuyor. Aradaki fark bu bandın içindeyse
"iyileşti" denemez.

---

## 8. Ölçüm araçları

```bash
# tam ölçüm (EVREN gerekir, ~18 dk + ~1 dk)
.venv/Scripts/python.exe -m src.boru_hatti extract
.venv/Scripts/python.exe -m eval.calistir

# kural katmanı tek başına — LLM yok, ağ yok, saniyeler sürer
# kural katmanında deneme/yanılma için BUNU kullanın
make kural-olc          #  ya da: .venv/Scripts/python.exe tools/kural_olc.py
```

> **`tools/kural_olc.py` neden var:** tam ölçüm 18 dakika sürüyor ve üstüne
> ±0,01 gürültü taşıyor — kural katmanındaki küçük bir değişikliğin işe
> yarayıp yaramadığını bu döngüyle anlamak imkânsız. Bu araçta LLM yok, yani
> **rastgelelik de yok**: aynı girdi her zaman aynı sayıyı verir, iki ölçüm
> arasındaki fark gerçek bir farktır.
>
> Bölüm 4'teki başarısız deney bu araçla **iki dakikada** elendi; tam ölçümle
> 36 dakika sürecekti.
>
> ⚠️ Bu araçtaki makro-F1 **hibrit skorla karşılaştırılamaz** —
> `kampanya_turu` kural katmanında yok, hep 0 çıkar. Anlamlı olan tek şey
> aynı araçla alınmış iki ölçümün FARKI.

---

*İlgili belgeler: [`docs/ALTIN_SET_DENETIMI.md`](docs/ALTIN_SET_DENETIMI.md)
(13 bulgu) · [`docs/SONUCLAR.md`](docs/SONUCLAR.md) (otomatik üretilen
metrikler) · [`docs/ETIKETLEME_KILAVUZU.md`](docs/ETIKETLEME_KILAVUZU.md)
(kararlar defteri)*
