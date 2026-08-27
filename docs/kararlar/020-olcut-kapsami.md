# ADR 020 — Ürün sınıfı ortak tabanın ikinci yarısıdır

**Tarih:** 27 Ağustos 2026 · **Durum:** kabul edildi · **Sorumlu:** Eren
**İlgili bulgu:** chatbot karşılaştırmasında her cevabın «aylık %0» ile bitmesi
**Şema etkisi:** yok — alan, birim ve kanıt sözleşmesi değişmedi

## Bağlam

Chatbot'a hangi iki banka sorulursa sorulsun kâr payı satırı aynı geliyordu:

```
- Kâr payı oranı açısından iki banka EŞİT: aylık %0.
```

931 kayıt sayıldı. `kar_payi_orani` dolu **119** kaydın dağılımı:

| Kampanya türü | = 0 | > 0 |
|---|---|---|
| kart · alışveriş puanı · diğer | **110** | 9 |
| ihtiyaç · taşıt · konut · finansman | 9 | 18 |
| yatırım ürünü | 0 | 1 |

Sıfırların kaynağı tek bir örüntü:

> «TROY kredi kartlarınız ile 1.000-100.000 TL arası sağlık harcamalarınıza
> **vade farksız 6 taksit** fırsatı!»

Bu kayıt için `kar_payi_orani = 0` **yanlış değildir** — ADR 012 tam olarak
bunu karara bağladı: vade farkının olmaması kâr payının sıfır olması demektir
ve bu, boş hücreden farklı bir bilgidir.

Yanlış olan, o sıfırı bir ihtiyaç finansmanının aylık %2,87'siyle **aynı
min-maks ölçeğine sokmaktı**. Bir kart taksit promosyonu ile bir finansman
ürünü aynı şeyi satmıyor; ikisinin oranı yan yana konulunca ortaya çıkan sayı
bir karşılaştırma değil, bir kategori hatasıdır.

Etkisi ölçüldü: dokuz bankanın **beşinde** (Dünya, Hayat Finans, Türkiye
Emlak, Vakıf, Ziraat) kâr payı verisinin tamamı bu türdendi. Yani finansman
oranı hiç yayımlamamış bankalar, sistemde «%0 kâr payı sunuyor» görünüyordu.

Ters yönde ikinci bir hata: Türkiye Finans Günlük Hesap sayfasından gelen
`11.0` bir **katılma hesabı yıllık getirisidir**, finansman maliyeti değil.
«En yüksek kâr payı hangi bankada?» sorusunun cevabı o oluyordu.

## Karar

`kar_payi_orani` karşılaştırmaya yalnız **finansman kampanyalarından** girer:
`finansman`, `ihtiyac_finansmani`, `konut_finansmani`, `tasit_finansmani`.

Kapı `src/comparison/karsilastirma.py` · `OLCUT_KAPSAMI` sözlüğünde ve
`ortak_tabana_indir` içinde durur; `sirala`, `avantaj_skorla` ve chatbot
cevabı aynı kapıdan geçer. Ayrı kopya tutulmaz — 27 Ağustos'ta banka
eşleştirmesinin iki yere kopyalanmasından çıkan kusur bunun bedelidir.

Dört sonuç:

1. **Kapsam dışı kayıt SİLİNMEZ.** `Alan` kanıtıyla yerinde durur, tekil
   sorguda kendi kaynağıyla gösterilir, `data/katilim.db` değişmez. Düşen tek
   şey onu **başka bir ürünle kıyaslama** iddiasıdır.
2. **Sessiz daralma yok.** Kıyaslanabilir oranı olmayan banka için `uyarilar`
   sebebini yazar; chatbot da «bu bankaların finansman kampanyalarında
   belirtilmemiş» der. «Hiç belirtilmemiş» demek yanlış olurdu — kullanıcı
   kampanya sayfasında sıfırı görüyor.
3. **`diger` kapsam dışıdır.** Sınıflandırılamamış bir kampanyayı finansman
   saymak, ADR 002'nin «zorlama sınıflandırma yapmaktansa *diğer* demek daha
   dürüsttür» kararını tersine çevirirdi. 47 kayıt bu yüzden düşüyor; bir
   kısmı gerçekten finansmandır ve bu, kabul edilen maliyettir.
4. **`urun_turu` kullanılamadı.** Alan 931 kaydın 931'inde boş; kapı
   `kampanya_turu` üzerinden kuruldu.

## ADR 012 ile çelişmez

ADR 012 **çıkarım** hakkındadır: «vade farksız» ifadesinden sıfır üretilir ve
bu bir beyandır. ADR 020 **karşılaştırma** hakkındadır: o sıfır, hangi ürünün
sıfırı olduğu bilinmeden sıralanamaz.

Sınama ikisini birden tutuyor: finansman kampanyasındaki `0,0` sıralamayı
kazanır (`test_finansman_kampanyasinin_sifiri_gecerlidir`), kart
kampanyasındaki `0,0` sıralamaya girmez
(`test_kart_kampanyasinin_sifiri_orani_kiyaslamaz`).

## Alternatifler

**Çıkarımı değiştirip kart kampanyalarında alanı boş bırakmak.** Reddedildi:
değer o kampanya için doğru, kanıtı var ve tekil sorguda işe yarıyor. Ayrıca
`data/katilim.db` teslim için donmuş; yeniden çıkarım `make eval` sayılarını
ve `docs/SONUCLAR.md`'yi ±0,01 gürültü bandının dışında oynatmadan
yapılamazdı.

**Hiçbir şey yapmayıp uyarı yazmak.** Reddedildi: uyarı zaten vardı ve cevap
yine «iki banka EŞİT: aylık %0» diyordu. Yanlış sıralamayı doğru bir dipnotla
sunmak, yanlış sıralamadır.

## Alınan ders

`Senaryo` (ADR 009) birim karışıklığını çözerken sorulan soru şuydu: *bu iki
sayı aynı tabanda mı?* Cevabın yalnız yarısı birimdi. Diğer yarısı ürün
sınıfı ve o yarı üç ay boyunca sorulmadı — çünkü sayılar aynı alandaydı ve
aynı birimdeydi, yani karşılaştırılabilir **görünüyorlardı**.
