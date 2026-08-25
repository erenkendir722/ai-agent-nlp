# Benzer Ürünler Nasıl Karşılaştırılıyor

*Şartname madde 6, doküman başlığı 6.*

Karşılaştırma motoru **tamamen deterministiktir ve LLM kullanmaz**
(`src/comparison/karsilastirma.py`). Sebep tek cümle: bankalar arası
karşılaştırmada dil modeli kullanmak, açıklanamayan ve tekrarlanamayan sonuç
demektir. Bir banka çalışanına *"bu ürün neden önde çıktı?"* diye
sorulduğunda cevap verilebilmelidir.

---

## 1. Beş sıralama kriteri

Şartname 5.7'nin beş kriteri doğrudan desteklenir:

| Kriter | Alan | Yön |
|---|---|---|
| En Düşük Kâr Payı Oranı | `kar_payi_orani` | düşük iyi |
| En Yüksek Ödül Miktarı | `odul_miktari` | yüksek iyi |
| En Uzun Vade Seçeneği | `vade_ay_max` | yüksek iyi |
| En Düşük Masraf | `tahsis_ucreti` | düşük iyi |
| **En Avantajlı Kampanya** | bileşik skor | bölüm 3 |

İlk dördü tek alanlı sıralamadır ve tartışmasızdır. Beşincisi bir karardır —
o yüzden aşağıda açıkça anlatılıyor.

---

## 2. Karşılaştırmadan önce: ortak taban

İki sayıyı yan yana koymadan önce **aynı tabanda olduklarından emin olmak**
gerekir. Bu, sistemin en sık gözden kaçan işidir.

### Çok birimli alanlar

Bazı alanlar tek birimlidir ve sorun çıkarmaz: `kar_payi_orani` her zaman
yüzde, `vade_ay_max` her zaman aydır. Ama `tahsis_ucreti` **TL de olabilir
yüzde de**:

```
A bankası:  tahsis ücreti 500 TL
B bankası:  tahsis ücreti %0,50
```

Bu ikisi doğrudan karşılaştırılamaz. Senaryo (anapara) biliniyorsa yüzde TL'ye
indirgenir:

```
%0,50 × 100.000 TL = 500 TL   →  artık A ile B eşit
```

Senaryo yoksa indirgeme **yapılmaz** ve değer `None` döner. Bu bir hata değil,
bir **beyandır**: *"bu değeri diğerleriyle aynı tabana getiremiyorum."* Çağıran
taraf bunu eksik veri gibi işler.

Şemanın `Alan.birim` alanı ([ADR 009](kararlar/009-boyutlu-nicelik.md)) tam da
bu yüzden var: birim bilgisi olmadan çok birimli bir alan karşılaştırılamaz,
ve şema birimsiz kaydı zaten reddeder.

### Birim karışımı sessiz geçmez

Karşılaştırılan kayıtlarda aynı alan farklı birimlerde geliyorsa kullanıcıya
**uyarı** çıkar. Sessizce sıralamaktansa durumu beyan etmek tercih edilir.

---

## 3. "En Avantajlı" kara kutu değildir

Bileşik skor dört adımda üretilir ve her adım kullanıcıya görünür:

**1. Her kriter kendi içinde 0–1'e ölçeklenir** (min-maks normalizasyon).
Böylece "ay" ile "yüzde" toplanabilir hâle gelir.

**2. Ağırlıklarla toplanır.** Varsayılanlar:

| Bileşen | Ağırlık |
|---|---|
| Kâr payı | %40 |
| Masraf | %25 |
| Vade | %20 |
| Ödül | %15 |

**Bu varsayılanlar bir tercihtir, gerçek değil.** Tipik bir tüketici için kâr
payı baskındır; ama ödül peşindeki bir kullanıcı için değildir. Bu yüzden
ağırlıklar arayüzde **kaydırıcıyla değiştirilir** ve sıralama anında yeniden
hesaplanır. Ağırlıklar toplamı 1 değilse normalize edilir.

**3. Eksik veri nötr (0,5) sayılır** — ne ödül ne ceza.

**4. Karşılaştırılabilirlik oranı raporlanır.** Skorun kaç alanın gerçek
verisine dayandığı ayrıca gösterilir; kullanıcı yarım veriye dayalı bir
sıralamayı tam veri sanmasın. Bu oran düştükçe sıralamaya duyulacak güven de
düşmelidir ve bunu kullanıcıdan saklamak yanıltmak olurdu.

> Skor bir **cevap parçası** olarak üretildiğinde kökeni `SISTEM`'dir ve
> içindeki her sayının `hesap` girdilerinden yeniden üretilebilmesi zorunludur
> (`MIMARI.md` bölüm 6). Yani "skoru elle yazmak" mimari olarak mümkün değildir.

---

## 4. Manşet oran tuzağı — ürünün asıl iddiası

En düşük kâr payı oranına sahip ürün, **en ucuz ürün değildir.** Manşetteki
oran maliyetin yalnız bir bileşenidir; tahsis ücreti ve vade de toplamı
değiştirir.

Bu yüzden sistem **toplam maliyet** hesaplar. Katılım bankacılığında murabaha
ile satış bedeli baştan sabitlenir; taksit hesabı matematiksel olarak annüite
formülüyle aynıdır:

```
taksit = A · i / (1 − (1 + i)^−n)
```

Üretilen kalemler: aylık taksit · toplam geri ödeme · toplam kâr payı · tahsis
ücreti · **toplam maliyet oranı**.

Sıralama, manşet orana değil bu toplama göre yapılır. Aynı vadede daha düşük
oranlı ama masraflı bir ürün, masrafsız rakibinden pahalı çıkabilir — sistemin
yakaladığı şey budur.

> ⚠️ **Bu iddia AYNI VADEDE kurulur.** Farklı vadeleri toplam geri ödemeyle
> karşılaştırmak yanlıştır: kısa vade toplamda her zaman daha ucuzdur, çünkü
> daha az ay kâr payı işler. Bu ayrım `tests/test_muhakeme.py`'de sayısal
> olarak sabitlenmiştir — sunumdaki cümle ile sistemin davranışı ayrışamaz.

---

## 5. Karşılaştırılamayanı karşılaştırmamak

Motor, kullanıcıyı yanıltabilecek durumları **kendisi bildirir**:

- **Farklı vadeli ürünler** yan yana konduğunda *"doğrudan karşılaştırılamaz"*
  uyarısı çıkar.
- **Birim karışımı** olduğunda uyarı çıkar (bölüm 2).
- **Eksik veri** karşılaştırılabilirlik oranına yansır (bölüm 3).

Farklı vadeli iki ürünü yan yana koyup *"bu daha ucuz"* demek finansal olarak
yanlıştır. Uyarıyı yazmak birkaç satırlık iştir; yazmamak, doğru görünen yanlış
bir sıralama üretir.

---

## 6. Uygunluk: karşılaştırmadan önce elenenler

Bir ürün müşteriye **uygun değilse**, ne kadar avantajlı olduğu önemsizdir.
Muhakeme ajanı (`src/ajanlar/muhakeme.py`, **LLM kullanmaz**) profil ile ürünün
kısıtlarını karşılaştırır: müşteri tipi, tutar alt/üst sınırı, azami vade,
zorunlu ürün.

İki tasarım kararı:

- **Elenen ürün gizlenmez, sebebiyle döner.** Banka çalışanının müşteriye ne
  diyeceğini öğrenmesi gerekir.
- **Uygunluk kısıtı çıkarılamamışsa ürün "uygun" gösterilir ama işaretlenir.**
  Açıklama iki olasılığı da söyler: kısıt kampanya metninde belirtilmemiş
  olabilir ya da bizim çıkarımımız kaçırmış olabilir. Hangisi olduğunu
  bilmiyoruz ve bilmediğimizi iddia etmiyoruz.

Maliyeti hesaplanamayan uygun bir kayıt sıralamada **sona** gider — "veri yok"
en iyi sonuç gibi görünmemelidir.

---

## İlgili belgeler

| Konu | Dosya |
|---|---|
| Motorun mimarideki yeri | [`MIMARI.md`](MIMARI.md) bölüm 7 |
| Birim sözleşmesi | [ADR 009](kararlar/009-boyutlu-nicelik.md) |
| Cevap parçası köken denetimi | [ADR 010](kararlar/010-koken-tipli-kalkan.md) |
| Ölçüm yöntemi | [`DEGERLENDIRME_YONTEMI.md`](DEGERLENDIRME_YONTEMI.md) |
