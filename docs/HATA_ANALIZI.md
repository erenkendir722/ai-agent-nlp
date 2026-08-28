# Hata Analizi

_17 Ağustos 2026 · altın set: 60 örnek · ölçüm: `make eval` + `make eval-robust`_

> ⚠️ **SAYILARI BAYAT, MODLARI GEÇERLİ (26 Ağu notu).** Bu analiz **60 örneklik**
> altın sete ve 17 Ağustos'taki koda dayanıyor. Altın set o zamandan beri **98
> örneğe** çıktı, kural kodu değişti ve korpus ayıklandı. Somut fark:
> `kampanya_turu` burada **F1 0,567 · 26/60 yanlış** yazıyor, güncel ölçümde
> **0,796** (98 örnek, 78/20/20). **Buradan sayı alıntılamayın** — güncel sayı
> [`SONUCLAR.md`](SONUCLAR.md)'dedir. Hatanın *kökleri* ve *modları* hâlâ
> geçerli; belgenin değeri orada.

Bu belge "neyi bilmiyoruz"u yazar. Üç en hatalı alan, hatanın **kökü** ve
alınan aksiyon. Dokümantasyon başlığı 8'in malzemesi.

## Önce ölçümün sınırı

Makro-F1 **0,699**, %95 güven aralığı **0,578 – 0,781**. Aralığın genişliği
0,20 ve sebebi modelin kararsızlığı değil, **altın setin küçüklüğü**:

| Alan | N (altın sette dolu hücre) | F1 |
|---|---|---|
| `kampanya_turu` | 60 | 0,567 |
| `vade_ay_max` | 20 | 0,791 |
| `kampanya_bitis` | 14 | 0,966 |
| `kar_payi_orani` | 10 | 0,842 |
| `masrafsiz_mi` | 7 🔸 | 0,714 |
| `tahsis_ucreti` | 5 🔸 | 0,909 |
| `finansman_tutari_max` | 5 🔸 | 0,400 |
| `odul_miktari` | 3 🔸 | 0,400 |

Sekiz alanın **dördünde N ≤ 7**. N=3'te tek kaydın düzelmesi F1'i 33 puan
oynatır. Aşağıdaki sayılar bu çerçevede okunmalı; 🔸 işaretli satırlar tek
başına alıntılanmamalıdır.

---

## 1. `finansman_tutari_max` — F1 0,400 (N=5)

**Tek "hep boş" tabanının altında kalan alan.** Yani bu alanda sistem,
hiçbir şey çıkarmayan bir sistemden daha kötü puan alıyor.

Beş hatanın **hepsi taşıt/konut dilim tablosundan** geliyor. İki yönü var:

**Iskaladıkları (3 vaka, hepsinde beklenen 400.000):**

```
0-400.000 TL | %70 | 48 ay
400.001 – 800.000 TL | %50 | 36 ay
800.001 – 1.200.000 TL | %30 | 24 ay
1.200.001 – 2.000.000 TL | %20 | 12 ay
```

Etiketleme kılavuzu (satır 158-161) diyor ki: *"`finansman_tutari_max` =
bankanın verdiği para, malın değeri değil. Kademeli tabloda her satır için
**değer × oran** hesapla, **en büyüğünü** yaz."*

Hesap: 400.000×%70 = 280.000 · **800.000×%50 = 400.000** · 1.200.000×%30 =
360.000 · **2.000.000×%20 = 400.000** → en büyüğü **400.000**. Altın setteki
değer bu. **Etiketleyiciler kılavuzu doğru uygulamış.**

### 🔴 Kök sebep: kılavuz ile mimari çelişiyor

Beklenen değer **hesaplanarak** üretiliyor. Ama bu depoda her `Alan`
kaynağını taşımak zorunda ve `kanit_denetimi`, sayısal alanların
`ham_ifade`'sinin ham metinde **birebir** geçmesini şart koşuyor. Hesapla
üretilmiş bir 400.000'in metinde birebir karşılığı yok.

Yani bu alan, mevcut sözleşme altında **tanım gereği** yüksek F1 alamaz.
Regex de LLM de bunu çözmez; sorun çıkarımda değil, iki kuralın çelişmesinde.

**Aksiyon: karar gerekiyor, kod değil.** İki seçenek var ve biri seçilip
`docs/kararlar/` altına ADR yazılmalı:

- **(a) Kılavuzu daraltmak** — yalnız metinde birebir yazan tutar etiketlenir,
  hesap istenmez. Kanıt zinciri korunur, alan ölçülebilir hale gelir.
- **(b) Şemaya türetilmiş değer kavramı eklemek** — `Alan.ham_ifade`
  hesabın girdisini (tablo satırını) gösterir, `yontem="turetilmis"` olur.
  Daha güçlü ama şema donmuş durumda (v1.0.0), ADR + sürüm yükseltme ister.

Önerim **(a)**: 8 gün kaldı ve (b) dört kişinin işini birden etkiler.

**Fazladan ürettikleri (3 vaka)** aynı madalyonun diğer yüzü: *"Finansman
tutarı 125.000 TL'ye kadar olması durumunda maksimum vade 36 ay"* — burada
125.000 bir **vade dilimi eşiği**, finansman limiti değil. `aralik_ucu_reddet`
iki uçlu aralıkları yakalıyor ama bu tek uçlu "X'e kadar → vade Y" satırını
kaçırıyor. Kılavuz satır 115 ise *"500.000 TL'ye kadar" → `500000`* diyor.
**Kılavuzun kendi içinde de bir gerilim var** ve (a) kararı bunu da çözmeli.

---

## 2. `odul_miktari` — F1 0,400 → **0,667** (N=3)

Üç hata, iki farklı kök:

### (a) Veto yan hasarı — 2 vaka ✅ DÜZELTİLDİ

`veto_ifadeleri` içinde `"toplamda"` vardı. Amacı şu cümleydi:
*"kişi başı maksimum 2.000 TL, **toplamda** 5 kişi için maksimum 10.000 TL"* —
`secim="en_yuksek"` toplamı alıyordu.

Ama "toplamda" jenerik bir sözcük ve masum bir cümleyi de eliyordu:

> *"kazanılabilecek maksimum nakit ödül tutarı **toplamda** 300 TL'dir"*

Burada 300 TL **gerçek ödül tutarı**. Toplamı işaret eden asıl imleç
"toplamda" değil, kişi sayısına bölünmüş ifade: **"5 kişi için"**.

**Aksiyon:** veto `"toplamda"` → `"kisi icin"` olarak daraltıldı.

| Varyant | odul F1 | DP/YP/YN | Karar |
|---|---|---|---|
| Mevcut (`toplamda`) | 0,400 | 1/1/2 | — |
| Veto tamamen kaldırıldı | 0,571 | 2/2/1 | ❌ reddedildi |
| **Daraltıldı (`kisi icin`)** | **0,667** | **2/1/1** | ✅ alındı |

Vetoyu tamamen kaldırmak da F1'i yükseltiyordu — **ama yeni bir yanlış
pozitif üreterek**: 2.000'i bulamadığı yerde 10.000 yazıyor. Bu depoda
yanlış değer, eksik değerden pahalıdır; sessizliği yanlış sayıyla takas
etmedik. Daraltma ise yeni yanlış pozitif üretmiyor.

### (b) Eşik / ödül karışması — 1 vaka ⏳ AÇIK

> *"en az **1.000 TL** tutarlı EFT veya FAST transferlerinde nakit ödül
> kazanırsınız"*

1.000 TL burada **hak kazanma eşiği**, ödülün kendisi değil. Ama "ödül" ve
"kazan" bağlam sözcükleri sayının hemen yanında olduğu için geçiyor.
Çözümü `"en az"` gibi bir öncül imleci gerektirir — ama S-12b'nin dersi
burada da geçerli: bu bir **eleme değil sıralama** sorunu. N=3 iken tek
kayda bakarak veto yazmak, bir sonraki ölçümde iki yeni hata açabilir.
**Altın set büyüyene kadar bilinçli olarak açık bırakıldı.**

---

## 3. `kampanya_turu` — F1 0,567 (N=60)

**İstatistiksel olarak en sağlam ölçülen alan ve en kötülerden biri.**
60 kaydın 26'sı yanlış. Buradaki kazanç gerçek olur — gürültü değil.

İki baskın hata modu 15 vakayı açıklıyor:

**(a) Genel/özel karışması — 6 vaka.** Sistem üst kategoriyi yazıyor:

| Altın | Sistem | Adet |
|---|---|---|
| `konut_finansmani` | `finansman` | 2 |
| `ihtiyac_finansmani` | `finansman` | 2 |
| `tasit_finansmani` | `finansman` | 2 |

Sistem **kategoride haklı, özgüllükte eksik**. Düz F1 bunu tam hata sayıyor;
oysa `finansman`, diğer üçünün üst kümesi. Hiyerarşik bir ölçüt kısmi puan
verirdi. Bu bir sınıflandırıcı hatası olduğu kadar bir **taksonomi** sorunu.

**(b) `alisveris_puani` aşırı ateşlemesi — 9 vaka.** `diger`→`alisveris_puani`
(4), `kart`→`alisveris_puani` (3), `ihtiyac_finansmani`→`alisveris_puani` (2).
Sınıf gereğinden geniş tanımlanmış.

**Aksiyon:** ikisi de açık. Ama dikkat — `kampanya_turu`'nun bir kısmı
**model değil veri** sorunu: `diger` oranı %38 ve bu, kampanya olmayan
sayfaların ayıklanmasına bağlı. Genel ürün
sayfaları korpustan çıkmadan sınıflandırıcıyı zorlamak, gürültüyü
ezberletmek olur. **Sıra: önce ayıklama, sonra bu madde.**

---

## Dayanıklılık tarafında hata var mı?

`make eval-robust` ayrı bir soruyu cevaplıyor ve tablosu temiz:

- **Biçim bozmada %100** (318 varyant) — `%1,89`→`1,89 %`, `TL`→`₺`, tamamı
  büyük harf, boşluk kaydırma. Normalizasyon katmanı işini yapıyor.
- **Alan silindiğinde `uydurdu` = 0.** Değeri taşıyan cümle silindiğinde
  sistem 51 vakanın 27'sinde susuyor, 24'ünde sayfadaki başka bir sayıya
  kayıyor — ama **hiçbirinde kanıtsız değer üretmiyor**.

Yani buradaki kusur da **seçim** kusuru, uydurma değil. Üç alanın analizi de
aynı yere çıkıyor: **sistemin sorunu değer uydurmak değil, doğru adayı
seçmek.**

### ⚠️ Tek istisna: LLM'in serbest metin özetleri

`odul_miktari` düzeltmesinden sonraki koşuda kanıt denetimi **bir** ihlal
buldu ve yeri anlamlı:

```
0210-963c04bc483b · Vakıf Katılım
kampanya_kosullari: özette geçen '28' sayısı ham metinde yok
```

**Sayısal ve tarihsel alanların hiçbirinde ihlal yok (0).** İhlal, LLM'in
özetlediği serbest metin alanında. Şema bunu bilerek farklı ölçüyor
(`kanit_denetimi` üçüncü sınıf): model özetleyebilir, birebir kopyalaması
gerekmez — ama **özetin içindeki sayılar** metinde bulunmak zorundadır.
Denetim tam da bu yüzden var ve çalıştı.

Bu ihlal kural katmanındaki değişiklikten gelmiyor; iki koşu arasındaki
LLM belirsizliğinden geliyor. Aynı sebeple `kampanya_turu` 0,567 → 0,600
oynadı — o da düzeltmenin değil, koşu farkının sonucu. **Sunumda
"halüsinasyon %0" demek yerine "sayısal alanlarda %0, serbest metin
özetlerinde koşuya göre 0-1 vaka" demek doğru olur.**

---

## Ne YAPILMAMALI

Makro-F1'i 0,85-0,90'a çıkarmak bu altın sette **teknik olarak kolay**:
`odul_miktari` (N=3) ve `finansman_tutari_max` (N=5) üzerinde birkaç veto
oynatmak yeter. Ama bu ölçüm değil **ezber** olur — toplam ~10 kaydı
ezberlemeye denk ve jürinin *"kaç örnek üzerinde ölçtünüz?"* sorusunda çöker.

Doğru yol sırayla:

1. **Korpus genişletmesi** — 96 → 300+. Seyrek alanları içeren kayıt havuzu olmadan
   altın set büyüyemez.
2. **Hedefli katmanlı örneklem** — rastgele değil, seyrek alanları içeren
   kayıtlara özel katman; alan başına ~25-30 pozitif hücre hedefi.
3. **dev/test ayrımı** — geliştirme bir yarıda, ölçüm diğerinde.
4. Ondan sonra alan bazlı iyileştirme.

**200 örnekte savunulan 0,80, 60 örnekte iddia edilen 0,90'dan güçlüdür.**
