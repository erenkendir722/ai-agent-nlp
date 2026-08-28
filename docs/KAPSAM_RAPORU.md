# Banka Bazlı Kapsam Raporu

_Otomatik üretildi: 28.08.2026 09:34 · `make kapsam`_

Bu dosya elle düzenlenmez. Karşılaştırma sonuçlarını okurken **önce buraya**
bakın: kapsam dengesizliği, motorun tarafsızlığından bağımsız bir yanlılık
kaynağıdır (şartname 15.1).

## Kapsam

- Toplam kampanya: **1019**
- Banka: **9** (BDDK listesindeki **faal** katılım bankalarının tamamı)
- En geniş kapsam / en dar kapsam oranı: **11.5×**

| Banka | Kampanya | Pay | Dolu alan / kayıt |
|---|---|---|---|
| Ziraat Katılım Bankası A.Ş. | 219 | %21.5 | 4.7 / 16 |
| Kuveyt Türk Katılım Bankası A.Ş. | 213 | %20.9 | 5.7 / 16 |
| Albaraka Türk Katılım Bankası A.Ş. | 137 | %13.4 | 4.9 / 16 |
| T.O.M. Katılım Bankası A.Ş. | 123 | %12.1 | 6.2 / 16 |
| Türkiye Emlak Katılım Bankası A.Ş. | 110 | %10.8 | 5.4 / 16 |
| Vakıf Katılım Bankası A.Ş. | 76 | %7.5 | 4.0 / 16 |
| Türkiye Finans Katılım Bankası A.Ş. | 70 | %6.9 | 5.0 / 16 |
| Dünya Katılım Bankası A.Ş. | 52 | %5.1 | 5.4 / 16 |
| Hayat Finans Katılım Bankası A.Ş. | 19 | %1.9 | 4.4 / 16 |

## Kampanya türü dağılımı

| Tür | Kayıt | Pay |
|---|---|---|
| `diger` | 387 | %38.0 |
| `alisveris_puani` | 192 | %18.8 |
| `kart` | 190 | %18.6 |
| `finansman` | 73 | %7.2 |
| `tasit_finansmani` | 51 | %5.0 |
| `yatirim_urunu` | 48 | %4.7 |
| `ihtiyac_finansmani` | 42 | %4.1 |
| `konut_finansmani` | 29 | %2.8 |
| `yeni_musteri` | 7 | %0.7 |

## `diger` neden bu kadar çok?

Kayıtların **387'i** (%38.0) `diger` türünde. Bu bir sınıflandırma başarısızlığı DEĞİL, bilinçli bir karardır:
şartname 5.4'teki sekiz tür finansman ve kart odaklıdır; bankaların yayımladığı
kampanyaların önemli bir bölümü o sekizin dışına düşer. **Zorlama sınıflandırma
yapmaktansa «diğer» demek daha dürüsttür** (ADR 002).

`diger` kayıtlarında geçen konular (ham metin taraması, bir kayıt birden çok
başlıkta sayılabilir):

| Konu | `diger` kaydı |
|---|---|
| taksit / vade farksız | 186 |
| indirim / iade | 155 |
| döviz / altın / yatırım | 144 |
| ücretsiz işlem / ATM | 64 |
| promosyon / hediye | 56 |
| sigorta | 45 |

> Altın sette `kampanya_turu` alanının F1 skoru **0,80** — yani tür çıkarımı
> ölçülen bir başarıyla çalışıyor; `diger` oranı korpusun kendi özelliğidir.

## Bu dengesizlik neyi etkiler

En geniş kapsamlı bankada en dar kapsamlının **11.5 katı** kayıt var.
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

