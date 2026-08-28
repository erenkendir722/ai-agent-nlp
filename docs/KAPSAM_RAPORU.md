# Banka Bazlı Kapsam Raporu

_Otomatik üretildi: 28.08.2026 10:19 · `make kapsam`_

Bu dosya elle düzenlenmez. Karşılaştırma sonuçlarını okurken **önce buraya**
bakın: kapsam dengesizliği, motorun tarafsızlığından bağımsız bir yanlılık
kaynağıdır (şartname 15.1).

## Kapsam

- Toplam kampanya: **921**
- Banka: **9** (BDDK listesindeki **faal** katılım bankalarının tamamı)
- En geniş kapsam / en dar kapsam oranı: **11.1×**

| Banka | Kampanya | Pay | Dolu alan / kayıt |
|---|---|---|---|
| Ziraat Katılım Bankası A.Ş. | 211 | %22.9 | 4.8 / 16 |
| Kuveyt Türk Katılım Bankası A.Ş. | 205 | %22.3 | 5.7 / 16 |
| Albaraka Türk Katılım Bankası A.Ş. | 127 | %13.8 | 4.9 / 16 |
| Türkiye Emlak Katılım Bankası A.Ş. | 109 | %11.8 | 5.5 / 16 |
| Vakıf Katılım Bankası A.Ş. | 72 | %7.8 | 4.2 / 16 |
| Türkiye Finans Katılım Bankası A.Ş. | 64 | %6.9 | 5.0 / 16 |
| T.O.M. Katılım Bankası A.Ş. | 62 | %6.7 | 6.2 / 16 |
| Dünya Katılım Bankası A.Ş. | 52 | %5.6 | 5.4 / 16 |
| Hayat Finans Katılım Bankası A.Ş. | 19 | %2.1 | 4.4 / 16 |

## Kampanya türü dağılımı

| Tür | Kayıt | Pay |
|---|---|---|
| `diger` | 330 | %35.8 |
| `alisveris_puani` | 191 | %20.7 |
| `kart` | 172 | %18.7 |
| `finansman` | 68 | %7.4 |
| `yatirim_urunu` | 44 | %4.8 |
| `tasit_finansmani` | 44 | %4.8 |
| `ihtiyac_finansmani` | 38 | %4.1 |
| `konut_finansmani` | 27 | %2.9 |
| `yeni_musteri` | 7 | %0.8 |

## `diger` neden bu kadar çok?

Kayıtların **330'i** (%35.8) `diger` türünde. Bu bir sınıflandırma başarısızlığı DEĞİL, bilinçli bir karardır:
şartname 5.4'teki sekiz tür finansman ve kart odaklıdır; bankaların yayımladığı
kampanyaların önemli bir bölümü o sekizin dışına düşer. **Zorlama sınıflandırma
yapmaktansa «diğer» demek daha dürüsttür** (ADR 002).

`diger` kayıtlarında geçen konular (ham metin taraması, bir kayıt birden çok
başlıkta sayılabilir):

| Konu | `diger` kaydı |
|---|---|
| taksit / vade farksız | 155 |
| döviz / altın / yatırım | 136 |
| indirim / iade | 131 |
| ücretsiz işlem / ATM | 63 |
| promosyon / hediye | 48 |
| sigorta | 42 |

> Altın sette `kampanya_turu` alanının F1 skoru **0,80** — yani tür çıkarımı
> ölçülen bir başarıyla çalışıyor; `diger` oranı korpusun kendi özelliğidir.

## Bu dengesizlik neyi etkiler

En geniş kapsamlı bankada en dar kapsamlının **11.1 katı** kayıt var.
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

