# Banka Bazlı Kapsam Raporu

_Otomatik üretildi: 27.08.2026 22:10 · `make kapsam`_

Bu dosya elle düzenlenmez. Karşılaştırma sonuçlarını okurken **önce buraya**
bakın: kapsam dengesizliği, motorun tarafsızlığından bağımsız bir yanlılık
kaynağıdır (şartname 15.1).

## Kapsam

- Toplam kampanya: **726**
- Banka: **9** (BDDK listesindeki **faal** katılım bankalarının tamamı)
- En geniş kapsam / en dar kapsam oranı: **11.4×**

| Banka | Kampanya | Pay | Dolu alan / kayıt |
|---|---|---|---|
| Kuveyt Türk Katılım Bankası A.Ş. | 182 | %25.1 | 5.7 / 16 |
| Ziraat Katılım Bankası A.Ş. | 155 | %21.3 | 4.5 / 16 |
| Albaraka Türk Katılım Bankası A.Ş. | 116 | %16.0 | 4.7 / 16 |
| Türkiye Emlak Katılım Bankası A.Ş. | 77 | %10.6 | 6.0 / 16 |
| Türkiye Finans Katılım Bankası A.Ş. | 56 | %7.7 | 5.3 / 16 |
| T.O.M. Katılım Bankası A.Ş. | 49 | %6.7 | 6.2 / 16 |
| Dünya Katılım Bankası A.Ş. | 43 | %5.9 | 5.6 / 16 |
| Vakıf Katılım Bankası A.Ş. | 32 | %4.4 | 4.4 / 16 |
| Hayat Finans Katılım Bankası A.Ş. | 16 | %2.2 | 4.3 / 16 |

## Kampanya türü dağılımı

| Tür | Kayıt | Pay |
|---|---|---|
| `diger` | 283 | %39.0 |
| `kart` | 151 | %20.8 |
| `alisveris_puani` | 127 | %17.5 |
| `yatirim_urunu` | 41 | %5.6 |
| `tasit_finansmani` | 35 | %4.8 |
| `ihtiyac_finansmani` | 31 | %4.3 |
| `finansman` | 30 | %4.1 |
| `konut_finansmani` | 21 | %2.9 |
| `yeni_musteri` | 7 | %1.0 |

## `diger` neden bu kadar çok?

Kayıtların **283'i** (%39.0) `diger` türünde. Bu bir sınıflandırma başarısızlığı DEĞİL, bilinçli bir karardır:
şartname 5.4'teki sekiz tür finansman ve kart odaklıdır; bankaların yayımladığı
kampanyaların önemli bir bölümü o sekizin dışına düşer. **Zorlama sınıflandırma
yapmaktansa «diğer» demek daha dürüsttür** (ADR 002).

`diger` kayıtlarında geçen konular (ham metin taraması, bir kayıt birden çok
başlıkta sayılabilir):

| Konu | `diger` kaydı |
|---|---|
| taksit / vade farksız | 143 |
| indirim / iade | 118 |
| döviz / altın / yatırım | 110 |
| ücretsiz işlem / ATM | 44 |
| promosyon / hediye | 43 |
| sigorta | 33 |

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

