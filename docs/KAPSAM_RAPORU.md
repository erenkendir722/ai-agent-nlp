# Banka Bazlı Kapsam Raporu

_Otomatik üretildi: 26.08.2026 16:45 · `make kapsam`_

Bu dosya elle düzenlenmez. Karşılaştırma sonuçlarını okurken **önce buraya**
bakın: kapsam dengesizliği, motorun tarafsızlığından bağımsız bir yanlılık
kaynağıdır (şartname 15.1).

## Kapsam

- Toplam kampanya: **1024**
- Banka: **9** (BDDK listesindeki **faal** katılım bankalarının tamamı)
- En geniş kapsam / en dar kapsam oranı: **13.6×**

| Banka | Kampanya | Pay | Dolu alan / kayıt |
|---|---|---|---|
| Ziraat Katılım Bankası A.Ş. | 217 | %21.2 | 3.8 / 16 |
| Kuveyt Türk Katılım Bankası A.Ş. | 209 | %20.4 | 5.1 / 16 |
| Türkiye Finans Katılım Bankası A.Ş. | 173 | %16.9 | 2.6 / 16 |
| Albaraka Türk Katılım Bankası A.Ş. | 136 | %13.3 | 4.6 / 16 |
| T.O.M. Katılım Bankası A.Ş. | 103 | %10.1 | 5.4 / 16 |
| Türkiye Emlak Katılım Bankası A.Ş. | 80 | %7.8 | 4.9 / 16 |
| Dünya Katılım Bankası A.Ş. | 54 | %5.3 | 1.6 / 16 |
| Vakıf Katılım Bankası A.Ş. | 36 | %3.5 | 4.6 / 16 |
| Hayat Finans Katılım Bankası A.Ş. | 16 | %1.6 | 4.6 / 16 |

## Kampanya türü dağılımı

| Tür | Kayıt | Pay |
|---|---|---|
| `diger` | 433 | %42.3 |
| `kart` | 210 | %20.5 |
| `alisveris_puani` | 168 | %16.4 |
| `yatirim_urunu` | 47 | %4.6 |
| `tasit_finansmani` | 46 | %4.5 |
| `ihtiyac_finansmani` | 43 | %4.2 |
| `finansman` | 43 | %4.2 |
| `konut_finansmani` | 28 | %2.7 |
| `yeni_musteri` | 6 | %0.6 |

## `diger` neden bu kadar çok?

Kayıtların **433'i** (%42.3) `diger` türünde. Bu bir sınıflandırma başarısızlığı DEĞİL, bilinçli bir karardır:
şartname 5.4'teki sekiz tür finansman ve kart odaklıdır; bankaların yayımladığı
kampanyaların önemli bir bölümü o sekizin dışına düşer. **Zorlama sınıflandırma
yapmaktansa «diğer» demek daha dürüsttür** (ADR 002).

`diger` kayıtlarında geçen konular (ham metin taraması, bir kayıt birden çok
başlıkta sayılabilir):

| Konu | `diger` kaydı |
|---|---|
| döviz / altın / yatırım | 158 |
| taksit / vade farksız | 135 |
| ücretsiz işlem / ATM | 104 |
| indirim / iade | 103 |
| sigorta | 45 |
| promosyon / hediye | 42 |

> Altın sette `kampanya_turu` alanının F1 skoru **0,80** — yani tür çıkarımı
> ölçülen bir başarıyla çalışıyor; `diger` oranı korpusun kendi özelliğidir.

## Bu dengesizlik neyi etkiler

En geniş kapsamlı bankada en dar kapsamlının **13.6 katı** kayıt var.
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

