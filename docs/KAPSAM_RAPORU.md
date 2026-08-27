# Banka Bazlı Kapsam Raporu

_Otomatik üretildi: 27.08.2026 19:08 · `make kapsam`_

Bu dosya elle düzenlenmez. Karşılaştırma sonuçlarını okurken **önce buraya**
bakın: kapsam dengesizliği, motorun tarafsızlığından bağımsız bir yanlılık
kaynağıdır (şartname 15.1).

## Kapsam

- Toplam kampanya: **727**
- Banka: **9** (BDDK listesindeki **faal** katılım bankalarının tamamı)
- En geniş kapsam / en dar kapsam oranı: **11.4×**

| Banka | Kampanya | Pay | Dolu alan / kayıt |
|---|---|---|---|
| Kuveyt Türk Katılım Bankası A.Ş. | 183 | %25.2 | 5.0 / 16 |
| Ziraat Katılım Bankası A.Ş. | 154 | %21.2 | 3.4 / 16 |
| Albaraka Türk Katılım Bankası A.Ş. | 116 | %16.0 | 4.6 / 16 |
| Türkiye Emlak Katılım Bankası A.Ş. | 77 | %10.6 | 4.9 / 16 |
| Türkiye Finans Katılım Bankası A.Ş. | 55 | %7.6 | 5.1 / 16 |
| T.O.M. Katılım Bankası A.Ş. | 49 | %6.7 | 5.4 / 16 |
| Dünya Katılım Bankası A.Ş. | 45 | %6.2 | 4.4 / 16 |
| Vakıf Katılım Bankası A.Ş. | 32 | %4.4 | 4.9 / 16 |
| Hayat Finans Katılım Bankası A.Ş. | 16 | %2.2 | 4.5 / 16 |

## Kampanya türü dağılımı

| Tür | Kayıt | Pay |
|---|---|---|
| `diger` | 261 | %35.9 |
| `kart` | 179 | %24.6 |
| `alisveris_puani` | 107 | %14.7 |
| `finansman` | 40 | %5.5 |
| `yatirim_urunu` | 39 | %5.4 |
| `ihtiyac_finansmani` | 35 | %4.8 |
| `tasit_finansmani` | 35 | %4.8 |
| `konut_finansmani` | 23 | %3.2 |
| `yeni_musteri` | 8 | %1.1 |

## `diger` neden bu kadar çok?

Kayıtların **261'i** (%35.9) `diger` türünde. Bu bir sınıflandırma başarısızlığı DEĞİL, bilinçli bir karardır:
şartname 5.4'teki sekiz tür finansman ve kart odaklıdır; bankaların yayımladığı
kampanyaların önemli bir bölümü o sekizin dışına düşer. **Zorlama sınıflandırma
yapmaktansa «diğer» demek daha dürüsttür** (ADR 002).

`diger` kayıtlarında geçen konular (ham metin taraması, bir kayıt birden çok
başlıkta sayılabilir):

| Konu | `diger` kaydı |
|---|---|
| taksit / vade farksız | 132 |
| indirim / iade | 116 |
| döviz / altın / yatırım | 96 |
| promosyon / hediye | 41 |
| ücretsiz işlem / ATM | 38 |
| sigorta | 26 |

> Altın sette `kampanya_turu` alanının F1 skoru **0,80** — yani tür çıkarımı
> ölçülen bir başarıyla çalışıyor; `diger` oranı korpusun kendi özelliğidir.

## Bu dengesizlik neyi etkiler

En geniş kapsamlı bankada en dar kapsamlının **11.4 katı** kayıt var.
Sonuçları okurken üç kural:

1. **«En avantajlı» ifadesi, TOPLADIĞIMIZ kümede en avantajlı demektir.**
   Az temsil edilen bir bankanın daha iyi teklifi kümede olmayabilir.
2. **Banka karşılaştırması kayıt sayısına değil, kayıt İÇERİĞİNE dayanmalı.**
   Arayüzdeki sıralama tekil ürünleri karşılaştırır, banka ortalaması almaz —
   dengesizlik bu yüzden sıralamayı doğrudan bozmaz.
3. **Tür dağılımı da dengesizdir.** Kart kampanyalarında kâr payı oranı
   bulunmaz; alan doluluğunu bankalar arası kıyaslarken tür karışımına bakın.

## Neden bazı bankalarda daha az kayıt var

- Bazı bankalar kampanya sayfalarını **JavaScript ile parça parça** yüklüyor
  («daha fazla göster» düğmesi). Toplayıcı ilk grubu alır; kalanı elle eklenir.
  Ayrıntı ve banka bazlı notlar: `data/banks.yaml`.
- İki banka (Adil Katılım, İktisat Katılım) **BDDK kaydı var ama faaliyete
  geçmemiş** durumda; kampanya sayfaları yok. Listede tutulur, sayılmaz.

