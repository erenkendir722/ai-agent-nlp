# Banka Bazlı Kapsam Raporu

_Otomatik üretildi: 26.08.2026 18:22 · `make kapsam`_

Bu dosya elle düzenlenmez. Karşılaştırma sonuçlarını okurken **önce buraya**
bakın: kapsam dengesizliği, motorun tarafsızlığından bağımsız bir yanlılık
kaynağıdır (şartname 15.1).

## Kapsam

- Toplam kampanya: **931**
- Banka: **9** (BDDK listesindeki **faal** katılım bankalarının tamamı)
- En geniş kapsam / en dar kapsam oranı: **11.9×**

| Banka | Kampanya | Pay | Dolu alan / kayıt |
|---|---|---|---|
| Kuveyt Türk Katılım Bankası A.Ş. | 190 | %20.4 | 5.0 / 16 |
| Türkiye Finans Katılım Bankası A.Ş. | 172 | %18.5 | 2.6 / 16 |
| Ziraat Katılım Bankası A.Ş. | 162 | %17.4 | 3.4 / 16 |
| Albaraka Türk Katılım Bankası A.Ş. | 126 | %13.5 | 4.4 / 16 |
| T.O.M. Katılım Bankası A.Ş. | 97 | %10.4 | 5.4 / 16 |
| Türkiye Emlak Katılım Bankası A.Ş. | 78 | %8.4 | 4.8 / 16 |
| Dünya Katılım Bankası A.Ş. | 54 | %5.8 | 2.0 / 16 |
| Vakıf Katılım Bankası A.Ş. | 36 | %3.9 | 4.7 / 16 |
| Hayat Finans Katılım Bankası A.Ş. | 16 | %1.7 | 4.5 / 16 |

## Kampanya türü dağılımı

| Tür | Kayıt | Pay |
|---|---|---|
| `diger` | 416 | %44.7 |
| `kart` | 194 | %20.8 |
| `alisveris_puani` | 108 | %11.6 |
| `yatirim_urunu` | 46 | %4.9 |
| `tasit_finansmani` | 46 | %4.9 |
| `finansman` | 43 | %4.6 |
| `ihtiyac_finansmani` | 41 | %4.4 |
| `konut_finansmani` | 29 | %3.1 |
| `yeni_musteri` | 8 | %0.9 |

## `diger` neden bu kadar çok?

Kayıtların **416'i** (%44.7) `diger` türünde. Bu bir sınıflandırma başarısızlığı DEĞİL, bilinçli bir karardır:
şartname 5.4'teki sekiz tür finansman ve kart odaklıdır; bankaların yayımladığı
kampanyaların önemli bir bölümü o sekizin dışına düşer. **Zorlama sınıflandırma
yapmaktansa «diğer» demek daha dürüsttür** (ADR 002).

`diger` kayıtlarında geçen konular (ham metin taraması, bir kayıt birden çok
başlıkta sayılabilir):

| Konu | `diger` kaydı |
|---|---|
| döviz / altın / yatırım | 150 |
| taksit / vade farksız | 123 |
| ücretsiz işlem / ATM | 99 |
| indirim / iade | 97 |
| sigorta | 39 |
| promosyon / hediye | 38 |

> Altın sette `kampanya_turu` alanının F1 skoru **0,80** — yani tür çıkarımı
> ölçülen bir başarıyla çalışıyor; `diger` oranı korpusun kendi özelliğidir.

## Bu dengesizlik neyi etkiler

En geniş kapsamlı bankada en dar kapsamlının **11.9 katı** kayıt var.
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

