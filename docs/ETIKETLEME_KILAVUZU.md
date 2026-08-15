# Etiketleme Kılavuzu — Altın Veri Seti

**Görev:** H-02 · **Kime:** Eren, Samet, Görkem, Esra · **Sürüm:** 1.0 (12 Ağustos 2026)

Bu belge altın setin **tek karar mercii**dir. Bir hücreye ne yazacağından emin
değilsen buraya bak; burada da yoksa gruba yaz ve **cevabı buraya ekle**.
Dört kişi aynı kuralla etiketlemezse ölçtüğümüz şey model doğruluğu değil,
aramızdaki görüş farkı olur.

---

## 1. Altın set nedir, neden kritik

Altın set, **insanın doğru kabul ettiği cevap anahtarı**dır. `make eval` sistemin
çıkardığı değerleri bu anahtarla karşılaştırır ve şartnamenin **%30'luk «Model
Başarısı»** kriterinin sayıları buradan çıkar.

İki kural pazarlık dışıdır:

1. **Etiketi HİÇBİR modele sorma** — ne bizimkine, ne dışarıdakine.
   - *Kendi sistemimiz:* arayüzü açıp ne bulduğuna bakma, `make run` çıktısından
     kopyalama. Sistemin çıktısıyla doldurulan altın set, sistemi kendisiyle
     ölçer; doğruluk yapay olarak yükselir. CSV'de model tahmini bilerek **yok**.
   - *Dış modeller (ChatGPT, Gemini, Claude…):* metni yapıştırıp "alanları çıkar"
     demek de aynı hatadır, hatta daha sinsisi. İki dil modeli aynı metni okurken
     **aynı yerlerde yanılır** — ücret tarifesi tablosunda ikisi de tökezler.
     Doğruluk yüksek çıkar, gerçek hata görünmez kalır ve ablasyon tablosu da
     aynı sapmayı taşır.
   - Model **okuma yardımı** olarak kullanılabilir ("bu sayfada vade nerede
     geçiyor?"). Etiketi, kaynak metne bakarak **insan** yazar.
2. **Metne sadık kal.** Sayfada yazmayan bir şeyi "herhalde böyledir" diye yazma.
   Bilmiyorsan boş bırak (`Belirtilmemiş`), emin değilsen `?` koy.

> **Boş hücre ile `?` aynı şey değildir.** Boş = "baktım, metinde yok" — cevap
> anahtarına böyle girer ve sistem "Belirtilmemiş" derse **doğru** sayılır.
> `?` = "bakmadım / emin değilim" — o hücre metriğin tamamen dışında kalır.
> Bakmadan boş bırakmak, sisteme yanlışlıkla hata yazdırır.
> `make altin-denetle` boş bıraktığın ama sistemin değer bulduğu hücreleri
> ⚠ ile listeler; o listeyi bir kez gözden geçir.

---

## 2. Nasıl çalışırsın

```bash
git pull --rebase origin main          # önce senkron ol
make altin-ornekle                     # (bir kişi bir kez çalıştırır)
```

Sana ait dosya: **`data/gold/etiketleme_<adın>.csv`**

1. Dosyayı Google Sheets'te aç: **Dosya → İçe aktar → Yükle → "Yeni e-tablo"**,
   ayırıcı virgül. *(Excel'de Türkçe karakter bozuk görünürse dosya UTF-8'dir;
   içe aktarırken kodlamayı UTF-8 seç.)*
2. **Görünüm → Dondur → 1 satır.** Aşağı indikçe başlıklar kaybolmasın; 16
   sütunu başlıksız doldurmak en sık hata kaynağı.
3. **`metin` sütununu daralt.** Hücrede 2.500 karakter var, tabloyu okunmaz
   hâle getirir. Metni okumak için
   **`data/gold/metinler/<kampanya_id>.txt`** dosyasını bir metin
   düzenleyicide yan pencerede aç — asıl konforlu yol bu.
4. Her satır bir kampanya. `metin`, **sistemin gördüğü ham metindir** —
   etiketini buna göre ver, canlı siteye bakma.
5. `kampanya_id`, `banka_adi`, `kaynak_url`, `metin` sütunlarına **dokunma.**
6. **Önce aşağıdaki çekirdek 8 sütunu doldur.** **`kampanya_turu` her satırda
   dolu olmalı** — araç "bu satıra bakıldı mı" sorusunu bu sütundan anlıyor,
   boş kalırsa satır sete hiç girmez.
7. CSV olarak kaydet (Sheets: **Dosya → İndir → Virgülle ayrılmış değerler**),
   inen dosyayı **aynı adla** `data/gold/` içine koy.

```bash
make altin-denetle ad=<adın>           # ⬅️ ÖNCE BU — pushlamadan hataları gör
make altin-derle                       # CSV'leri altin_set.jsonl'e çevirir + denetler
make eval                              # metrikler -> docs/SONUCLAR.md
git add data/gold && git commit -m "Altın set: <adın> payı etiketlendi" && git push
```

### ⭐ Çekirdek 8 alan — önce bunlar

Vaktin kısıtlıysa **şu sekiz alanı bütün satırlarda doldur**, kalanlara `?` yaz:

`kampanya_turu` · `kar_payi_orani` · `vade_ay_max` · `finansman_tutari_max` ·
`tahsis_ucreti` · `masrafsiz_mi` · `odul_miktari` · `kampanya_bitis`

Sebebi ölçüm: `urun_turu` kampanyaların %0'ında, `alisveris_puani` ve
`masraf_bilgisi` %1'inde, `hedef_kitle` %4'ünde geçiyor. Bu alanlara harcanan
emek metrikte neredeyse hiç örnek üretmiyor. **Sekiz alanı çok örnekte
etiketlemek, on altı alanı az örnekte etiketlemekten hem ucuz hem
istatistiksel olarak daha sağlam** — `kar_payi_orani` kampanyaların yalnız
%28'inde geçtiği için 30 örnekte ~8 kez görünür, o doğruluk sayısı sunumda
savunulamayacak kadar geniş bir güven aralığı taşır.

### 🔎 `make altin-denetle` — pushlamadan önceki kalite kapısı

Dosyanı pushlamadan **mutlaka** çalıştır. Enum yerine serbest metin, bozuk
tarih, sayıya çevrilemeyen hücre ve boş `kampanya_turu` satırlarını satır
numarasıyla gösterir:

```
❌ satır 5  kampanya_turu='taşıt' geçersiz → tasit_finansmani
❌ satır 3  kampanya_bitis='16 ağustos' tarihe çevrilemedi → YYYY-AA-GG yaz
❌ satır 9  kampanya_turu BOŞ → bu satırın tamamı altın sete girmez.
```

> Bu komut 14 Ağustos'ta iki gerçek hatadan sonra eklendi: dört kişinin
> kişisel dosyası baştan sona boş kaldı ve kimse fark etmedi (altın set 60
> yerine 10 örnek oldu), ayrıca bir tur etiket enum yerine serbest metinle
> dolduruldu. İkisi de derleme anında değil, **senin masanda** yakalanmalı.

> ⚠️ **Canlı siteye bakma.** Sayfa 9 Ağustos'tan beri değişmiş olabilir. Canlı
> sayfaya göre etiketlersen, çıkarım hatası ile sayfa değişikliğini birbirine
> karıştırırız ve metrik anlamını yitirir.

---

## 3. Üç durum — en sık yapılan hata burada

| Hücreye ne yazarsın | Ne demek | JSONL'e nasıl gider | Metriğe girer mi |
|---|---|---|---|
| **boş bırak** | Metinde bu bilgi **yok** | `null` | ✅ **Evet** |
| `?` | **Emin değilim / karar veremedim** | alan hiç yazılmaz | ❌ Hayır |
| bir değer | Metinde bu bilgi var, değeri bu | değer | ✅ Evet |

**Boş ile `?` aynı şey değildir.** Boş bırakmak bir iddiadır: "bu sayfada kâr
payı oranı yazmıyor" dersin ve sistem bir oran uydurduysa **hata sayılır** —
halüsinasyonu yakalayan şey tam olarak budur. `?` ise "bilmiyorum" demektir ve
o alan ölçümün dışında kalır.

Emin olamadığın her yerde `?` kullanmaktan çekinme. **Tahmin edilmiş bir etiket,
eksik etiketten daha zararlıdır** — yanlış cevap anahtarı, modeli haksız yere
yanlış gösterir ve hata analizini de yanıltır.

---

## 4. Alan alan kurallar

### 4.1 Sınıflandırma

**`kampanya_turu`** — şu değerlerden **tam olarak biri** (küçük harf, alt çizgi):

`finansman` · `ihtiyac_finansmani` · `konut_finansmani` · `tasit_finansmani` ·
`kart` · `alisveris_puani` · `yeni_musteri` · `yatirim_urunu` · `diger`

Karar sırası:
1. Sayfa belirli bir finansman ürünü anlatıyorsa **o ürünü** seç
   (konut → `konut_finansmani`, taşıt/araç → `tasit_finansmani`,
   ihtiyaç → `ihtiyac_finansmani`).
2. Finansman ama türü belirsizse → `finansman`.
3. Kart harcaması, taksit, kart aidatı → `kart`.
4. Puan/mil/chip-para kazanma → `alisveris_puani`.
5. Sadece yeni müşteriye özel bir teklif ve ürün ikincil → `yeni_musteri`.
6. Katılma hesabı, altın, fon, sukuk → `yatirim_urunu`.
7. **Hiçbiri değilse → `diger`.** Zorlama sınıflandırma yapma.

> ℹ️ Sayfa aslında kampanya değilse (genel ürün tanıtımı, SSS, ana sayfa) yine
> `diger` yaz ve `notlar` yerine grup sohbetine bildir — bu, Görkem'in G-05
> ("kampanya olmayan sayfaları ayıkla") görevinin girdisidir.

**`hedef_kitle`** — `yeni_musteri` · `mevcut_musteri` · `maas_musterisi` ·
`segment` · `tum_musteriler`

`segment`: öğrenci, emekli, KOBİ, kadın girişimci, esnaf gibi tanımlı bir grup.
Sayfada kime özel olduğu yazmıyorsa **boş bırak** — "herkese açıktır" varsayma.

**`urun_turu`** — serbest metin, sayfadaki ürün adı. Örnek: `Konut Finansmanı`,
`Altın Katılma Hesabı`. Uydurma, sayfadaki adı kullan.

### 4.2 Sayısal alanlar

Ondalık ayırıcı **virgül** (`1,89`), binlik ayırıcı istersen nokta (`50.000`).
Birim yazma — `%`, `TL`, `ay` **koyma**, sadece sayı.

| Alan | Birim | Örnek metin | Hücreye |
|---|---|---|---|
| `kar_payi_orani` | **aylık %** | "aylık %2,05 kâr payı" | `2,05` |
| `finansman_tutari_max` | TL | "500.000 TL'ye kadar" | `500000` |
| `vade_ay_max` | ay | "36 aya varan vade" | `36` |
| `taksit_sayisi` | adet | "12 taksit" | `12` |
| `tahsis_ucreti` | TL veya % | "tahsis ücreti 750 TL" | `750` |
| `odul_miktari` | TL | "1.500 TL hediye" | `1500` |
| `indirim_orani` | % | "%20 indirim" | `20` |
| `alisveris_puani` | TL/puan | "2.000 TL chip-para" | `2000` |

Özel durumlar:

- **Yıllık oran verilmişse aya çevir:** "yıllık %24" → `2` (24 ÷ 12). Metinde
  hangisi olduğu yazmıyorsa: Türkiye'de katılım bankaları kâr payını **aylık**
  ilan eder; %5'in üstündeki bir değer büyük olasılıkla yıllıktır. Emin
  değilsen `?`.
- **Aralık verilmişse en avantajlı uçtan al:** "%1,89 – %2,45 arası" →
  `kar_payi_orani` = `1,89`. "50.000 – 500.000 TL" →
  `finansman_tutari_max` = `500000` (alan adı `_max`).
- **"…'dan başlayan" / "…'a varan"** → o sayıyı yaz.
- **Birden fazla ürün için farklı oran varsa** (konut %1,89, taşıt %2,45) →
  sayfanın ana konusu olan ürünün oranını yaz; ana konu yoksa `?`.
- **Vade "5 yıl" ise aya çevir:** `60`.

### 4.3 `masrafsiz_mi`

`evet` / `hayır` / boş.

- `evet`: "masrafsız", "dosya masrafı yok", "tahsis ücreti alınmaz" gibi
  **açık** bir ifade var.
- `hayır`: masraf/ücret alındığı açıkça yazıyor.
- **boş**: konu hiç geçmiyor. *Masraf yazmıyor olması masrafsız olduğu anlamına
  gelmez.*

### 4.4 `kampanya_bitis`

**`YYYY-AA-GG`** biçimi: `2026-09-30`.

- "30 Eylül 2026'ya kadar" → `2026-09-30`
- "Eylül ayı sonuna kadar" → `2026-09-30` (ayın son günü)
- "yıl sonuna kadar" → `2026-12-31`
- "stoklarla sınırlı", "kampanya süresince" → **boş** (tarih yok)

### 4.5 Serbest metin alanları

**`kampanya_avantaji`** — kampanyanın müşteriye vaadi, **tek cümle**.
Sayfadan kopyalayabilirsin ya da özetleyebilirsin, ama **sayı uydurma**:
yazdığın cümledeki her sayı metinde geçmeli.

> Şartname 5.2'nin dolaylı ifadeleri (*"avantajlı kâr payı fırsatı"*,
> *"özel oranlı finansman"*, *"düşük maliyetli finansman"*) burada yaşar.
> Sayfa "avantajlı oran" diyor ama **sayı vermiyorsa**: `kar_payi_orani` **boş**,
> `kampanya_avantaji` = `Avantajlı kâr payı oranı`. Sistem burada bir sayı
> uydurursa altın set bunu yakalar — testin özü budur.

**`kampanya_kosullari`** — uygunluk şartları: "yeni müşteri olmak",
"maaşını bankaya taşımak", "minimum 10.000 TL". Tek cümlede birleştir.

**`masraf_bilgisi`** — masrafın ne olduğu yazıyorsa metniyle:
`Tahsis ücreti finansman tutarının %0,5'i`.

---

## 4.9. Doğrulama turu — hazır bir bloğu kontrol etmek

Elinde **zaten doldurulmuş** bir blok varsa (başkası doldurmuş, eski bir turdan
kalmış ya da bir modelle taslak çıkarılmış), onu sıfırdan etiketlemek yerine
**doğrulamak** yeterlidir. Sıfırdan etiketlemek kayıt başına ~4 dakika,
doğrulamak ~1 dakika.

```bash
make altin-dogrulama ad=Esra
```

Bu, her çekirdek alan için **mevcut etiketi** ve o alanla ilgili **kaynak metin
alıntılarını** yan yana koyan bir sayfa üretir:
`data/gold/dogrulama_etiketleme_<ad>.md`

```
**vade_ay_max** — şu an: `120`
> - Vade : TL cinsinden 120 aya kadar; USD veya EUR cinsinden ise azami 60 ay…
```

Sayfa **sistemin ne bulduğunu göstermez** — bilerek. Gösterseydi cevap anahtarı
sistemin kopyasına dönerdi. Dayanağın yalnızca banka metnidir.

Alıntılar yol göstericidir, karar metnin tamamına aittir; şüphedeysen
`data/gold/metinler/<kampanya_id>.txt` dosyasını aç.

Düzeltmeleri **CSV'ye** yaz (sayfa salt okunur, `.gitignore`'da — CSV
değiştikçe yeniden üret). Bitince `make altin-denetle ad=<Ad>`.

Doğrulama turunda **kaç hücreyi düzelttiğini not et.** "Ön etiketlerin %X'i
insan doğrulamasında düzeltildi" cümlesi sunumda metodoloji ciddiyeti gösterir
— saklanacak değil, anlatılacak bir sayıdır.

---

## 5. Kalite: uyum ölçümü (H-02'nin "bitti" şartı)

### 🔒 Uyum bloğunun üç kuralı

Uyum oranı takıma verilen bir not **değildir** — bu kılavuzun sınavıdır. Dört
kişi aynı metni okuyup farklı etiketliyorsa kusur insanlarda değil, buradaki
bir maddenin belirsizliğindedir. Aşağıdaki üç kural o sınavı ölçülebilir tutar;
biri delinirse çıkan sayı hiçbir şey ifade etmez.

> **1 — Dosyanı, dördünüz bitirmeden depoya PUSHLAMA.**
> Herkes kendi dosyasını doldurur ve doğrudan kaptana gönderir. Kaptan dördünü
> birden koyar. Böylece kimse kimsenin cevabını görmeden etiketler.
>
> **2 — Her dosyayı, adı yazan kişi doldurur.**
> Bir arkadaşının vakti yoksa onun bloğu BOŞ KALIR; başkası dolduramaz. İki
> dosyayı tek kişi doldurduğunda uyum oranı o kişinin kendisiyle uyumunu ölçer
> ve her zaman yüksek çıkar — yani ölçüm çalıştığını sanırsınız, oysa hiçbir
> şey ölçmemişsinizdir.
>
> **3 — Etiketler dil modeliyle üretilmez.**
> Altın set, sistemi kendisine karşı ölçtüğümüz cevap anahtarıdır. Etiketler bir
> modelden gelirse ölçtüğümüz şey doğruluk değil, iki modelin birbirine
> benzerliği olur. Üstelik iki model aynı metni okuduğu için **aynı hatalara**
> düşer: gerçek doğruluğunuz ölçtüğünüzden düşük çıkar ve fark görünmez.
> Model bir okuma yardımı olarak kullanılabilir; **etiketi insan, kaynak metne
> bakarak** yazar.

**Ne oldu (12–15 Ağustos).** İlk uyum bloğunda 28 serbest metin alanının 27'si
iki dosyada harfi harfine aynıydı. İlk teşhis "dolu dosya pushlandı, sonraki
gördü" idi ve 1. kural buna karşı yazıldı. 15 Ağustos'ta gerçek sebep ortaya
çıktı: **iki dosyayı da aynı kişi doldurmuştu ve etiketler bir dil modelinden
geliyordu.** 1. kural bunu engellemezdi; 2. ve 3. kurallar bu yüzden eklendi.

O bloktan çıkan uyum oranı geçersiz sayıldı. Ölçüm taze bir kalibrasyon bloğuyla
tekrarlanır (`make altin-kalibrasyon`); `aktif_uyum_kaynagi` kalibrasyon bloğunda
etiket varsa otomatik olarak onu kullanır.

> `make altin-uyum` 1. kuralı otomatik denetler: iki kişinin serbest metin
> alanları %90'dan fazla birebir aynıysa **kopya şüphesi** verir ve oranı
> geçersiz sayar. 2. ve 3. kuralı araç denetleyemez — onlar söze bağlıdır.

Etiketlemeye dağılmadan önce **ilk 10 örneği dördünüz de ayrı ayrı**
etiketleyin — aynı 10 satırı. Sonra karşılaştırın:

```bash
make altin-uyum          # dördünün ilk 10 satırdaki uyum oranını hesaplar
```

- **Uyum ≥ %85** → dağılın, kalanı paylaşarak etiketleyin.
- **Uyum < %85** → uyuşmadığınız alanları konuşun, kararı **bu belgeye 6.
  bölüme yazın**, sonra dağılın. Kuralı yazmadan devam etmek, aynı tartışmayı
  60 kez yapmak demektir.

Ölçülen uyum oranı sunuma girer: *"etiketleme uzlaşmamız %X"* cümlesi akademik
jüriye metodoloji ciddiyeti gösterir.

---

## 6. Kararlar defteri

Tartışıp karara bağladığınız her kenar durumu **buraya, tarihiyle** yazın.

| Tarih | Soru | Karar |
|---|---|---|
| 12 Ağu | Yıllık/aylık oran ayrımı yoksa? | %5 üstü yıllık kabul, aya bölünür; şüpheliyse `?` |
| 12 Ağu | Oran aralığı verilmişse? | En düşük (müşteri lehine) uç yazılır |
| 12 Ağu | Sayfa kampanya değilse? | `kampanya_turu = diger`, gruba bildirilir (G-05 girdisi) |
| 12 Ağu | Sayfa **birden çok ürün listeliyorsa** (ör. 9 farklı finansman) | `kampanya_turu = diger`; sayısal alanlar hangi ürüne ait belli değilse `?`. Bir ürünün sayısını sayfanın tamamına mal etme. |
| 12 Ağu | Masraftan hiç söz edilmiyorsa `masrafsiz_mi`? | **Boş** — "yazmıyor" ile "masraf var" aynı şey değil |
| | | |

---

## 7. Örnekler

**Örnek 1 — temiz**

> Konut Finansmanı Kampanyası. 1.000.000 TL'ye varan konut finansmanında aylık
> %1,89 kâr payı oranı, 120 aya varan vade. Dosya masrafı alınmaz.
> Kampanya 31 Ekim 2026 tarihine kadar geçerlidir.

| Alan | Değer |
|---|---|
| `kampanya_turu` | `konut_finansmani` |
| `kar_payi_orani` | `1,89` |
| `finansman_tutari_max` | `1000000` |
| `vade_ay_max` | `120` |
| `masrafsiz_mi` | `evet` |
| `kampanya_bitis` | `2026-10-31` |
| `kampanya_avantaji` | `1.000.000 TL'ye varan konut finansmanında aylık %1,89 kâr payı` |
| diğerleri | boş |

**Örnek 2 — dolaylı ifade, sayı yok**

> Yeni müşterilerimize özel avantajlı kâr payı fırsatı! Hemen başvurun.

| Alan | Değer |
|---|---|
| `kampanya_turu` | `finansman` |
| `hedef_kitle` | `yeni_musteri` |
| `kar_payi_orani` | **boş** ← sayı verilmemiş |
| `kampanya_avantaji` | `Yeni müşterilere özel avantajlı kâr payı fırsatı` |
| diğerleri | boş |

**Örnek 3 — belirsiz**

> Taşıt finansmanında yıllık %24'ten başlayan oranlar. Detaylar şubelerimizde.

| Alan | Değer |
|---|---|
| `kampanya_turu` | `tasit_finansmani` |
| `kar_payi_orani` | `2` ← yıllık %24 ÷ 12 |
| `kampanya_avantaji` | `Taşıt finansmanında yıllık %24'ten başlayan oranlar` |
| `kampanya_kosullari` | boş |
| diğerleri | boş |

---

## 8. Bilinen sınırlar — dokümantasyona da girecek

Dürüst olmak, sonradan yakalanmaktan iyidir. Bunlar `docs/SONUCLAR.md` ve
sunumda açıkça söylenir:

1. **Örneklem katmanlaması model tahminine dayanıyor.** Kampanya türüne göre
   dengeli örnek seçtik ama o türler sistemin kendi tahmini (bugün %38'i
   `diger`). Doğru katmanlama için zaten altın set gerekiyordu; elimizdeki tek
   sinyalle dengeledik.
2. **Nadir türlerde örnek az.** 96 kampanyanın içinde 1 `yeni_musteri`,
   3 `tasit_finansmani` var; bu türlerde alan bazlı doğruluk **istatistiksel
   olarak anlamlı değil** ve öyle raporlanacak.
3. **Etiketleyen sayısı 4, çapraz kontrol yalnız ilk 10 örnekte.** Kalan
   örneklerde tek etiketleyen var; uyum oranı ilk 10'dan tahmin ediliyor.
