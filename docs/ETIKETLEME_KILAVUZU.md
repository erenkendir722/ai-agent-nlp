# Etiketleme Kılavuzu

**Sürüm 2.0** · Eren · Samet · Görkem · Esra

Altın set, sistemimizin doğruluğunu ölçtüğümüz **cevap anahtarı**. Şartnamedeki
"Model Başarısı" puanının (%30) sayıları buradan çıkıyor. Bizim yazdığımız
etiketler yanlışsa, ölçtüğümüz sayı da yanlış olur — o yüzden bu iş dikkat
istiyor. Ama uzun değil.

---

## Ne yapacaksın

| | |
|---|---|
| **Dosyan** | `data/gold/etiketleme_<adın>.csv` — 13-14 satır |
| **Ortak dosyan** | `data/gold/etiketleme_uyum_<adın>.csv` — 5 satır, dördümüz de aynı satırları etiketliyoruz |
| **Yardımcın** | `data/gold/okuma_<adın>.md` — her satır için ilgili cümleler önden çıkarılmış |
| **Doldurulacak** | Satır başına **8 hücre** |
| **Süre** | Yaklaşık **25 dakika** |

Her satır bir banka kampanyası. Metni oku, sekiz soruyu cevapla, sıradakine geç.

**Nasıl açarsın:** CSV'yi Google Sheets'e sürükle (Dosya → İçe aktar → Yükle).
`metin` sütununu daralt, yanında `okuma_<adın>.md` dosyasını aç. İlk üç sütuna
(`kampanya_id`, `banka_adi`, `kaynak_url`) ve son sütuna (`metin`) dokunma.

---

## 🚫 Tek yasak: etiketi yapay zekâya sordurma

Metni ChatGPT'ye/Claude'a yapıştırıp "alanları çıkar" deme. Kendi arayüzümüzden
(`make run`) kopyalama da aynı şey.

**Neden:** Altın set, sistemimizi ölçmek için var. Etiketi bir dil modeli
yazarsa, ölçtüğümüz şey doğruluk değil, iki modelin birbirine benzerliği olur.
Üstelik iki model aynı metni okurken **aynı yerlerde yanılır** — ücret tarifesi
tablosunda ikisi de tökezler. Sonuç: doğruluk yüksek görünür, gerçek hata
görünmez kalır, jüriye anlattığımız sayı boş çıkar.

Modeli **okuma yardımı** olarak kullanmak serbest: *"bu sayfada vade nerede
geçiyor?"* diye sorabilirsin. Etiketi sen, metne bakarak yazarsın.

> 🔒 Ortak (`_uyum_`) dosyanı **dördümüz bitirmeden pushlama.** Bitince doğrudan
> Eren'e gönder, o dördünü birden koyar. Erken pushlanan bir dosya, kalan üç
> kişiye cevap anahtarını göstermiş olur ve uyum oranı anlamsızlaşır.

---

## Üç durum — en sık burada hata yapılıyor

| Hücreye ne yazarsın | Ne demek | Metriğe girer mi |
|---|---|---|
| **boş bırak** | "Baktım, bu bilgi metinde **yok**" | ✅ Evet |
| **`?`** | "Bakmadım / emin değilim" | ❌ Hayır, hücre metrikten çıkar |
| **bir değer** | "Metinde var, değeri bu" | ✅ Evet |
| **`0`** | "Metin açıkça **yok/alınmaz** diyor" | ✅ Evet |

`0` ile boş aynı şey değil. *"Tahsis ücreti alınmaz"* → `tahsis_ucreti` = `0`
(bilgi var, değeri sıfır). Sayfa tahsis ücretinden hiç söz etmiyorsa → **boş**
(bilgi yok). Aynısı `kar_payi_orani` için: "vade farksız" → `0`.

**Boş bırakmak bir iddiadır.** "Bu sayfada kâr payı oranı yazmıyor" demiş
olursun; sistem bir oran uydurduysa **hata sayılır**. Halüsinasyonu yakalayan
şey tam olarak bu.

Bu yüzden: bakmadan boş bırakma. Emin değilsen `?` yaz, çekinme.
**Tahmin edilmiş bir etiket, eksik etiketten daha zararlıdır.**

---

## Önce: hangi ürün?

Bir sayfa çoğu zaman tek bir ürünü anlatır, ama bazen dokuz farklı finansmanı
birden listeler. Sekiz alanı doldurmadan önce **hangi ürünün sayılarını
yazacağına** karar vermelisin.

**Kural: `kaynak_url` hangi ürüne işaret ediyorsa o.**

URL bir kaydın kimliğidir; yorum değil. `.../konut-finansmani-kampanyasi`
diyorsa sayfa başka ürünlerden de söz etse bile **konut** finansmanının
sayılarını yazarsın.

URL genel bir listeleme sayfasıysa (`.../kampanyalar`, `.../finansman`) →
sayfadaki **ilk / başlıktaki** ürünü al. Diğer ürünlerin sayılarını **yazma**.
Bir ürünün oranını sayfanın tamamına mal etme.

`kampanya_turu` da bu ürüne göre yazılır — çok ürünlü diye `diger` deme.

> ⚠️ **Bu kural sayılara da uygulanır, sadece türe değil.** 15 Ağustos uyum
> turunda dördümüz birden şu hatayı yaptık: URL `gayrimenkul-finansmani`
> (konut) iken, sayfanın alt kısmındaki *"Alışverişlerinizde Bayide
> Finansman'ı tercih edin, 36 aya varan vadelerle"* cümlesinden
> `vade_ay_max = 36` yazdık. O 36 ay **Bayide Finansman'a** ait; konut kısmında
> sayı yok, sadece "uzun vade" yazıyor.
>
> Türü doğru seçip sayıyı başka üründen almak en kolay tuzak — üstelik
> **uyum oranı bunu yakalayamaz**, dördü birden yanılınca %100 görünür.
> Bir sayıyı yazmadan önce: *bu cümle URL'nin ürününden mi söz ediyor?*
> Değilse alan **boş** kalır.

---

## Sekiz alan

Birim yazma — `%`, `TL`, `ay` koyma, sadece sayı. Ondalıkta **nokta da virgül de
olur** (`0.99` ve `0,99` ikisi de doğru okunuyor); binlik ayracı istersen koy,
istersen koyma (`2000000` = `2.000.000`).

| Alan | Ne yazarsın | Örnek metin | → Hücre |
|---|---|---|---|
| **`kampanya_turu`** | Aşağıdaki listeden **tam olarak biri**. Her satırda dolu olmalı. | "Konut Finansmanı Kampanyası" | `konut_finansmani` |
| **`kar_payi_orani`** | **Aylık** yüzde | "aylık %0,99 kâr payı" | `0.99` |
| **`vade_ay_max`** | Ay cinsinden **en uzun** vade | "36 aya varan vade" | `36` |
| **`finansman_tutari_max`** | TL, **en yüksek** tutar | "500.000 TL'ye kadar" | `500000` |
| **`tahsis_ucreti`** | TL veya % | "tahsis ücreti 750 TL" | `750` |
| **`masrafsiz_mi`** | `evet` / `hayır` / boş | "dosya masrafı alınmaz" | `evet` |
| **`odul_miktari`** | TL | "1.500 TL hediye" | `1500` |
| **`kampanya_bitis`** | `YYYY-AA-GG` | "30 Eylül 2026'ya kadar" | `2026-09-30` |

> ⚠️ **`kar_payi_orani` bir maliyet oranıdır, bir kapsam oranı değil.**
> Sayfadaki her `%` kâr payı değildir. **Taşıt değerine oranı**, **peşinat
> oranı**, **kredi/değer oranı**, **azami finansman oranı** gibi kolonlar bu
> alana **yazılmaz** — onlar "ne kadarını finanse ediyoruz" der, "kaça mal
> oluyor" demez. Emin değilsen `?`.

### `kampanya_turu` seçenekleri

`finansman` · `ihtiyac_finansmani` · `konut_finansmani` · `tasit_finansmani` ·
`kart` · `alisveris_puani` · `yeni_musteri` · `yatirim_urunu` · `diger`

Yukarıdan aşağı bak, ilk uyanı seç:

1. Belirli bir finansman ürünü mü? → konut / taşıt-araç / ihtiyaç karşılığını seç
2. Finansman ama türü belirsiz mi? → `finansman`
3. Kart harcaması, taksit, kart aidatı? → `kart`
4. Puan / mil / chip-para kazanma? → `alisveris_puani`
5. Sadece yeni müşteriye özel, ürün ikincil? → `yeni_musteri`
6. Katılma hesabı, altın, fon, sukuk? → `yatirim_urunu`
7. **Hiçbiri değilse → `diger`.** Zorlama sınıflandırma yapma.

---

## Sık takılınan yerler

**Oran aylık mı yıllık mı belli değil?**
Katılım bankaları kâr payını **aylık** ilan eder. %5'in üstündeki bir değer büyük
olasılıkla yıllıktır, 12'ye böl ("yıllık %24" → `2`). Emin değilsen `?`.

**Aralık verilmiş ("%1,89 – %2,45")?**
Müşterinin lehine olan ucu al → `1,89`. Tutarda ise en yükseği
("50.000 – 500.000 TL" → `500000`), çünkü alan adı `_max`.

**Kademeli tablo var (vade arttıkça oran değişiyor)?**
`vade_ay_max` = tablodaki **en büyük** vade. Alan adları `_max`; en küçüğü
yazarsan alan adı yalan söyler ve her satır hata sayılır.

**`finansman_tutari_max` = bankanın verdiği para, malın değeri değil.**
Taşıt tablolarında sık karışıyor. "Aracın kasko değeri 2.000.000 TL, taşıt
değerine oranı %20" ise banka **400.000 TL** veriyor — `finansman_tutari_max`
= `400000`, `2000000` değil. Kademeli tabloda her satır için değer × oran
hesapla, **en büyüğünü** yaz.

| Aracın değeri | Oran | Finansman |
|---|---|---|
| 400.000 | %70 | 280.000 |
| 800.000 | %50 | 400.000 |
| 1.200.000 | %30 | 360.000 |
| 2.000.000 | %20 | **400.000** ← en yükseği |

Çarpım yapmak zorunda kaldığın yerde emin değilsen `?` yaz.

**Ödül hem kişi başı hem toplam veriliyor?**
`odul_miktari` = **kişi başı / işlem başı** tutar. "Kişi başı maksimum 2.000 TL,
toplamda 5 kişi için 10.000 TL" → `2000`. Toplam, kampanyanın tavanıdır;
müşterinin bir işlemden kazandığı değil.

**Sayfada oran tablosu var — kullanılır mı?** İki tür tablo var, karıştırma:

**a) Bankanın oran tablosu → KULLAN.** Başlığında `Kâr Payı Oranı` kolonu olan,
vade kademelerine göre oran veren tablo. Bu, ilan edilen oranın kendisidir.

```
Vade | Kâr Payı Oranı | Tahsis Ücreti | Aylık Maliyet
  3  |     4,20%      |    0,50%      |    5,77%
 36  |     3,80%      |    0,50%      |    4,98%     ← en düşük: 3.80
```

Kademe çoksa **en düşük kâr payı oranını** yaz (müşteri lehine uç — aralık
kuralının aynısı). Sigortalı/sigortasız gibi varyantlar varsa yine en düşüğü.
**`Tahsis Ücreti` kolonunu `kar_payi_orani`'ye yazma** — sistem tam bu hatayı
yapıyor, altın setin yakalaması gereken şey bu.

**b) Tek satırlık örnek ödeme planı → sayfa ayrıca oran ilan ediyorsa onu yaz.**
"Kâr Oranı %1.00 · Toplam Geri Ödenen 66.066,24 TL" bir simülasyondur; sayfa
"0.99% oran avantajları" diyorsa hücreye `0.99` girer. **Ama örnek tablo
sayfadaki tek oran kaynağıysa onu yaz** — boş bırakmak "bu sayfada oran yok"
demektir ve yanlış olur.

Örnek plandaki **taksit tutarı ve toplam geri ödeme** hiçbir zaman
`finansman_tutari_max` değildir.

**"Arkadaşını davet et" / referans kampanyası?**
`kampanya_turu` = `yeni_musteri`. Kampanyanın konusu müşteri kazanımıdır; ödülün
yatırıldığı hesap (katılma hesabı, vadesiz vb.) **araçtır, konu değildir** —
`yatirim_urunu` yazma.

**"…'a varan", "…'dan başlayan"?** O sayıyı yaz.

**Vade "5 yıl" yazıyor?** Aya çevir → `60`.

**Masraftan hiç söz edilmiyor?**
`masrafsiz_mi` **boş** bırak. Yazmıyor olması masrafsız olduğu anlamına gelmez.
`hayır` da yazma — `hayır`, metnin masraf **alındığını** açıkça söylediği
durumdur.

**"Kart ücreti yok" yazıyor, masrafsız mı?**
**Hayır.** `masrafsiz_mi`, **finansmanın** masrafını anlatır: tahsis ücreti,
dosya masrafı, komisyon. Kart aidatı / kart ücreti ayrı bir şeydir.

| Metinde geçen | `masrafsiz_mi` |
|---|---|
| "tahsis ücreti alınmaz", "dosya masrafı yok", "masrafsız finansman" | `evet` |
| "kart aidatı yok", "kart ücreti alınmaz" | **boş** (finansman masrafı hakkında bilgi yok) |
| "tahsis ücreti finansman tutarının %0,5'i" | `hayır` |
| Masraftan hiç söz yok | **boş** |

**"Avantajlı kâr payı" diyor ama sayı vermiyor?**
`kar_payi_orani` **boş**. Sistem burada bir sayı uydurursa altın set yakalar —
testin özü tam olarak bu.

**Tarih "Eylül sonuna kadar" / "yıl sonuna kadar"?**
Ayın son günü → `2026-09-30`, `2026-12-31`.
"Stoklarla sınırlı", "kampanya süresince" → **boş** (tarih yok).

**Sayfa aslında kampanya değil (ürün tanıtımı, SSS, ana sayfa)?**
`diger` yaz ve grup sohbetine bildir.

> ⚠️ **Canlı siteye bakma.** Sayfa 9 Ağustos'tan beri değişmiş olabilir. Etiketi
> CSV'deki `metin` sütununa ve `data/gold/metinler/<kampanya_id>.txt` dosyasına
> göre ver — sistemin gördüğü metin bu.

---

## Bitirince

```bash
make altin-denetle ad=<Adın>    # ⬅️ ÖNCE BU. Hataları satır numarasıyla gösterir.
```

Enum yerine serbest metin, bozuk tarih, sayıya çevrilemeyen hücre ve boş
`kampanya_turu` satırlarını yakalar:

```
❌ satır 5  kampanya_turu='taşıt' geçersiz → tasit_finansmani
❌ satır 3  kampanya_bitis='16 ağustos' tarihe çevrilemedi → YYYY-AA-GG yaz
❌ satır 9  kampanya_turu BOŞ → bu satırın tamamı altın sete girmez.
```

Ayrıca "boş bıraktın ama sistem burada bir değer buldu" uyarısı verir. Bu bir
hata değil — bilerek boş bıraktıysan öyle kalsın, bakmadan bıraktıysan `?` yaz.

Temizse:

```bash
git add data/gold && git commit -m "Altın set: <adın> payı etiketlendi"
git push origin main
```

> Ortak (`_uyum_`) dosyanı bu adımda **gönderme** — dördümüz bitirene kadar bekle.

Dördümüz de bitirince kaptan çalıştırır:

```bash
make altin-uyum      # etiketleyiciler arası uyum oranı (hedef ≥ %85)
make altin-derle     # CSV'ler -> data/gold/altin_set.jsonl
make eval            # metrikler -> docs/SONUCLAR.md
```

Uyum %85'in altında çıkarsa: ayrıştığımız alanları konuşup kararı aşağıdaki
tabloya yazıyoruz. Kuralı yazmadan devam etmek, aynı tartışmayı 60 kez yapmak demek.

---

## Kararlar defteri

Tartışıp karara bağladığımız her kenar durum buraya, tarihiyle yazılır.

| Tarih | Soru | Karar |
|---|---|---|
| 12 Ağu | Yıllık/aylık oran ayrımı yoksa? | %5 üstü yıllık kabul, 12'ye bölünür; şüpheliyse `?` |
| 12 Ağu | Oran aralığı verilmişse? | En düşük (müşteri lehine) uç yazılır |
| 12 Ağu | Sayfa kampanya değilse? | `kampanya_turu = diger`, gruba bildirilir |
| 12 Ağu | Masraftan hiç söz edilmiyorsa? | **Boş** — "yazmıyor" ile "masraf var" aynı şey değil |
| 15 Ağu | Kâr payı sıfırsa ("vade farksız")? | `0` yaz — boş değil. Sıfır bir bilgidir. |
| 15 Ağu | Sayfa birden çok ürün listeliyorsa? | **`kaynak_url`'in ürünü** esas alınır, türü de o ürüne göre yazılır. URL genelse ilk/başlıktaki ürün. *(12 Ağu'daki "`diger` + `?`" kuralının yerine geçti: fazla `?` üretiyor ve uyum oranını hesaplanamaz hâle getiriyordu.)* |
| 15 Ağu | Kademeli tabloda hangi değer? | En büyüğü — alan adları `_max` |
| 15 Ağu | "Taşıt değerine oranı", "peşinat oranı" kâr payı mı? | **Hayır.** Kapsam oranı, maliyet oranı değil. `kar_payi_orani`'ye yazılmaz |
| 15 Ağu | "Kart ücreti yok" masrafsız mı? | **Hayır** — `masrafsiz_mi` finansman masrafını anlatır, kart aidatını değil. Boş bırakılır |
| 15 Ağu | Ondalık ayırıcı nokta mı virgül mü? | İkisi de serbest; ayrıştırıcı ikisini de aynı sayıya çeviriyor |
| 15 Ağu | URL kuralı sayılara da uygulanır mı? | **Evet.** Türü doğru seçip sayıyı başka üründen almak en sık hata; uyum turunda dördümüz birden yaptık |
| 15 Ağu | `finansman_tutari_max` malın değeri mi? | **Hayır**, bankanın verdiği tutar. Kademeli tabloda değer × oran, en büyüğü |
| 15 Ağu | Ödül kişi başı mı toplam mı? | **Kişi başı / işlem başı.** Toplam, kampanya tavanıdır |
| 15 Ağu | Bankanın oran tablosu (`Vade \| Kâr Payı Oranı \| …`)? | **Kullanılır**, en düşük oran yazılır. `Tahsis Ücreti` kolonu karıştırılmaz |
| 15 Ağu | Tek satırlık örnek ödeme planındaki oran? | Sayfa ayrıca oran ilan ediyorsa o yazılır; **örnek tek kaynaksa** o yazılır. Boş bırakmak "sayfada oran yok" demektir |
| 15 Ağu | "Arkadaşını davet et" kampanyası? | `yeni_musteri` — ödülün yatırıldığı hesap araçtır, konu değil |
| 25 Ağu | Değer metinde VAR ama hangi ürüne ait olduğu seçilemiyorsa? | **`?`** — boş hücre "metinde yok" iddiasıdır ve burada yanlıştır. Sayı gerçekten yazıyor, atfedilemiyor. `0206-0a6668cc5df3` (hesaplama aracı: 500 TL konut, 1000 TL arsa, "binde 5" bir arada), `0206-32cbb264a824` (altı kategoriye altı ayrı bonus) |
| 25 Ağu | Sayfa "masrafsız bankacılık" diyor ama finansmandan hiç söz etmiyorsa? | **Boş.** 15 Ağu kuralı aynen geçerli: hesap işletim ücreti / EFT / kart aidatı muafiyeti `masrafsiz_mi` değildir. Başlıktaki iddia kuralı değiştirmez (`0203-4a4c087b579a`) |
| 25 Ağu | "Dosya masrafı olmadan" — dipnot "dosya masrafı = tahsis ücreti" diyorsa? | `masrafsiz_mi = evet` **ve** `tahsis_ucreti = 0`. Muaf tutulan şey finansman masrafının ta kendisi; yukarıdaki kuralın diğer yüzü (`0206-32cbb264a824`) |
| 25 Ağu | Tabloda `%1.00`, düz yazıda `0.99%` — hangisi? | **%0,99.** Tablo örnek ödeme planıdır; sayfa oranı ayrıca ilan ediyor (15 Ağu kuralı) ve düşük uç müşteri lehinedir. Uyum turunda 4 kişiden 3'ü zaten böyle yazmıştı (`0206-d08e26c033db`) |
| 25 Ağu | Kredi kartı nakit avans tavanı `finansman_tutari_max` mı? | **Evet** — bankanın verdiği tutar ve açık bir üst sınır. Kart limitinin kendisi değil, "maksimum X TL" ifadesi yazılır (`0205-a323f782dfd5` → 20.000) |

---

## Dört örnek

**1 — Temiz**

> Konut Finansmanı Kampanyası. 1.000.000 TL'ye varan konut finansmanında aylık
> %1,89 kâr payı oranı, 120 aya varan vade. Dosya masrafı alınmaz.
> Kampanya 31 Ekim 2026 tarihine kadar geçerlidir.

`konut_finansmani` · `1,89` · `120` · `1000000` · *(tahsis boş)* · `evet` ·
*(ödül boş)* · `2026-10-31`

**2 — Dolaylı ifade, sayı yok**

> Yeni müşterilerimize özel avantajlı kâr payı fırsatı! Hemen başvurun.

`finansman` · *(oran **boş** — sayı verilmemiş)* · *(kalanı boş)*

**3 — Yıllık oran**

> Taşıt finansmanında yıllık %24'ten başlayan oranlar. Detaylar şubelerimizde.

`tasit_finansmani` · `2` *(24 ÷ 12)* · *(kalanı boş)*

**4 — Çok ürünlü sayfa + tuzak oran** ← yeni kuralların ikisi birden

`kaynak_url`: `.../tasit-finansmani`

> **Taşıt Finansmanı.** Taşıt değerinin **%70**'ine kadar finansman.
> Sıfır araçta aylık **%2,45**, ikinci elde **%2,89**.
>
> | Vade | Tutar |
> |---|---|
> | 12 ay | 500.000 TL |
> | 24 ay | 750.000 TL |
> | 36 ay | 1.000.000 TL |
>
> Kart aidatı alınmaz. *(Sayfanın altında ayrıca konut ve ihtiyaç finansmanı
> tabloları var.)*

| Alan | Değer | Neden |
|---|---|---|
| `kampanya_turu` | `tasit_finansmani` | URL taşıta işaret ediyor — çok ürünlü diye `diger` denmez |
| `kar_payi_orani` | `2.45` | **%70 değil** — o kapsam oranı. Sıfır araç sayfanın ana konusu |
| `vade_ay_max` | `36` | Tablodaki en büyük |
| `finansman_tutari_max` | `1000000` | Tablodaki en yüksek |
| `masrafsiz_mi` | **boş** | "Kart aidatı yok" finansman masrafı hakkında bilgi vermez |
| konut/ihtiyaç sayıları | **yazılmaz** | URL'nin ürünü değil |

---

Bir hücreye ne yazacağından emin değilsen: önce buraya bak, yoksa gruba yaz ve
**cevabı buraya ekle.** Dördümüz aynı kuralla etiketlemezsek ölçtüğümüz şey model
doğruluğu değil, aramızdaki görüş farkı olur.

*Altın setin kapsamı neden 8 alan: [`kararlar/008-altin-set-kapsami.md`](kararlar/008-altin-set-kapsami.md)*
