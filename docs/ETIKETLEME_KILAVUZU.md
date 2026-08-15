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

**Boş bırakmak bir iddiadır.** "Bu sayfada kâr payı oranı yazmıyor" demiş
olursun; sistem bir oran uydurduysa **hata sayılır**. Halüsinasyonu yakalayan
şey tam olarak bu.

Bu yüzden: bakmadan boş bırakma. Emin değilsen `?` yaz, çekinme.
**Tahmin edilmiş bir etiket, eksik etiketten daha zararlıdır.**

---

## Sekiz alan

Ondalık ayırıcı **virgül** (`1,89`). Birim yazma — `%`, `TL`, `ay` koyma, sadece sayı.

| Alan | Ne yazarsın | Örnek metin | → Hücre |
|---|---|---|---|
| **`kampanya_turu`** | Aşağıdaki listeden **tam olarak biri**. Her satırda dolu olmalı. | "Konut Finansmanı Kampanyası" | `konut_finansmani` |
| **`kar_payi_orani`** | **Aylık** yüzde | "aylık %2,05 kâr payı" | `2,05` |
| **`vade_ay_max`** | Ay cinsinden en uzun vade | "36 aya varan vade" | `36` |
| **`finansman_tutari_max`** | TL, en yüksek tutar | "500.000 TL'ye kadar" | `500000` |
| **`tahsis_ucreti`** | TL veya % | "tahsis ücreti 750 TL" | `750` |
| **`masrafsiz_mi`** | `evet` / `hayır` / boş | "dosya masrafı alınmaz" | `evet` |
| **`odul_miktari`** | TL | "1.500 TL hediye" | `1500` |
| **`kampanya_bitis`** | `YYYY-AA-GG` | "30 Eylül 2026'ya kadar" | `2026-09-30` |

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

**"…'a varan", "…'dan başlayan"?** O sayıyı yaz.

**Vade "5 yıl" yazıyor?** Aya çevir → `60`.

**Sayfa birden çok ürün listeliyor (9 farklı finansman gibi)?**
`kampanya_turu` = `diger`, sayısal alanlar hangi ürüne ait belli değilse `?`.
Bir ürünün sayısını sayfanın tamamına mal etme.

**Masraftan hiç söz edilmiyor?**
`masrafsiz_mi` **boş** bırak. Yazmıyor olması masrafsız olduğu anlamına gelmez.

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
| 12 Ağu | Sayfa birden çok ürün listeliyorsa? | `diger`; sayısal alanlar belirsizse `?` |
| 12 Ağu | Masraftan hiç söz edilmiyorsa? | **Boş** — "yazmıyor" ile "masraf var" aynı şey değil |
| 15 Ağu | Kâr payı sıfırsa ("vade farksız")? | `0` yaz — boş değil. Sıfır bir bilgidir. |

---

## Üç örnek

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

---

Bir hücreye ne yazacağından emin değilsen: önce buraya bak, yoksa gruba yaz ve
**cevabı buraya ekle.** Dördümüz aynı kuralla etiketlemezsek ölçtüğümüz şey model
doğruluğu değil, aramızdaki görüş farkı olur.

*Altın setin kapsamı neden 8 alan: [`kararlar/008-altin-set-kapsami.md`](kararlar/008-altin-set-kapsami.md)*
