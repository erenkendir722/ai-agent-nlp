# ADR 012 — «Vade farksız» bir kâr payı beyanıdır, boşluk değil

**Tarih:** 24 Ağustos 2026 · **Durum:** kabul edildi · **Sorumlu:** Eren
**İlgili bulgu:** altın set `kar_payi_orani` denetimi
**Şema etkisi:** yok

## Bağlam

Makro-F1 çalışmasında `kar_payi_orani` alanının iki yanlış negatifi incelendi.
Altın set üç kayıtta `kar_payi_orani = 0` diyordu; sistem üçünde de `None`
üretiyordu.

İlk teşhis **yanlıştı**. «Metinde *kâr payı*, *%0*, *faizsiz* hiç geçmiyor,
demek ki etiket metinden çıkarım değil yorum» denildi ve etiketlerin
düzeltilmesi önerildi. Kaynak metinler tek tek okununca tablo değişti:

| Kayıt | Metinde geçen | Etiketleyen |
|---|---|---|
| Albaraka Pratik Finansman Kart | tabloda birebir **`0%`** | Görkem |
| Kuveyt Türk Kredi Kartı | «**vade farksız** taksitlendirebilir» | uzlaşı |
| Kuveyt Türk Eğitim/Sağlık | «**vade farksız** 2 ila 5 taksit» | Esra |

Üç ayrı etiketleyici, birbirinden bağımsız olarak aynı kararı vermişti.
Katılım bankacılığında **vade farkının olmaması, kâr payının sıfır olması
demektir**; korpustaki bir sayfa bunu birebir yazıyor:

> «**Kâr payı yok.** Beklemek yok. 140.000 TL'ye kadar **vade farksız** destek»

Yani etiketler doğruydu. Kaçıran sistemdi.

## Neden sistem üretemiyordu

`KuralTanimi.sifir_gecerli` bayrağı **zaten vardı** ve docstring'i aynen şunu
söylüyordu:

> *«Vade farksız» / «0 kâr payı» kampanyalarında oran gerçekten sıfırdır ve bu,
> boş hücreden FARKLI bir bilgidir.*

Ama o bayrak yalnız **sayıyı** `gecerli_aralik` alt sınırından muaf tutuyordu.
«Vade farksız» ifadesinde ortada sayı yoktur; `D_ORAN` deseni hiç eşleşmez.
Niyet yazılmış, uygulaması eksik kalmıştı — bayrak açıktı ama tetikleyecek
bir yol yoktu.

## Karar

1. **Altın set etiketleri DEĞİŞTİRİLMEZ.** Üçü de metne dayanıyor.
2. Kural katmanına cümle düzeyinde bir sıfır beyanı kuralı eklenir
   (`_vade_farksiz_orani`). Üç yazım tanınır: «vade farksız», «vade farkı
   olmadan/yok», «kâr payı yok/alınmaz».
3. **Sayısal orana tabidir:** yalnız kural katmanı sayısal bir oran
   bulamadığında devreye girer. Bir sayfa hem «vade farksız 6 taksit» hem
   «aylık %2,05» diyorsa kampanyanın oranı %2,05'tir; ifade orada bir alt
   teklifi anlatır.
4. Güven **0,80** — sayısal orandan (0,93) düşük, çünkü ifadeden çıkarımdır.
   LLM aynı sonuca varırsa uzlaştırıcı `hibrit`e yükseltir.

## Kanıt zinciri bozulmaz

Üretilen değer sayı değildir ama **kanıtı vardır**: ifadenin geçtiği cümle
`ham_ifade` olarak saklanır ve eleştirmen ajanının birebir metin denetiminden
geçer. `masrafsiz_mi` ile aynı desen — bir bool'un ya da sıfırın kanıtı, o
kararı veren cümledir.

## Kapsam

İfade korpusta **99/590 kayıtta** geçiyor (%16,8). Yani bu, altın setin üç
kaydına özel bir yama değil, veri setinin altıda birini ilgilendiren genel
bir örüntüdür.

## Alınan ders

Bir alanın **etiketi ile çıkarıcısı farklı sözleşmelere** bakıyordu:
kılavuz etiketleyene «sıfır geçerlidir, yaz» derken, kural katmanı sıfır
üretebileceği hiçbir yola sahip değildi. Ölçüm bunu iki koşu boyunca
«sistemin hatası» değil «etiketin hatası» gibi gösterdi.

**Bir etiket sistemle çelişiyorsa, hangisinin yanlış olduğuna kaynak metne
bakmadan karar verilmez.** Etiketi düzeltmek her zaman daha kolaydır ve tam
bu yüzden tehlikelidir: ölçüm aracını sisteme uydurmak, ölçmeyi bırakmaktır.
