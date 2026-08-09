# ADR 002 — Kampanya türü sınıflandırması

**Tarih:** 9 Ağustos 2026 (aynı gün revize edildi)
**Durum:** ✅ Kabul edildi — şartname metniyle doğrulandı
**Sahip:** Samet

## Bağlam

Şartname 5.4, kampanya metinlerinin belirli kategorilere ayrılmasını istiyor.
Şartname metni elimize geçmeden önce, katılım bankacılığı ürün yelpazesinden
hareketle geçici bir taksonomi tanımlanmıştı (bkz. "Reddedilen taksonomi").

## Karar

Şartname 5.4 tablosundaki liste **birebir** benimsendi:

| # | Şartnamedeki ad | Enum değeri |
|---|---|---|
| 1 | Finansman Kampanyası | `finansman` |
| 2 | İhtiyaç Finansmanı Kampanyası | `ihtiyac_finansmani` |
| 3 | Konut Finansmanı Kampanyası | `konut_finansmani` |
| 4 | Taşıt Finansmanı Kampanyası | `tasit_finansmani` |
| 5 | Kart Kampanyası | `kart` |
| 6 | Alışveriş Puanı Kampanyası | `alisveris_puani` |
| 7 | Yeni Müşteri Kampanyası | `yeni_musteri` |
| 8 | Yatırım Ürünü Kampanyası | `yatirim_urunu` |
| — | *(şartnamede yok, biz ekledik)* | `diger` |

Şartname "örnek kampanya türleri aşağıdaki gibi **olabilir**" diyor — liste
bağlayıcı değil. Yine de birebir uyuyoruz: jüri kendi tablosunu görmek ister ve
çıktının şartname diliyle örtüşmesi değerlendirmeyi kolaylaştırır.

`diger` sınıfı bizim eklememiz. Sınıflandırılamayan bir metni zorla sekiz
kategoriden birine sokmak, ölçülen makro-F1'i şişirir ama gerçekte yanlış veri
üretir. "Diğer" demek daha dürüsttür.

## Reddedilen taksonomi (kayıt için)

Şartname öncesi tahminimiz şuydu ve **önemli ölçüde yanlıştı**:

`konut_finansmani`, `tasit_finansmani`, `ihtiyac_finansmani`,
`isyeri_ticari_finansman`, `kredi_karti`, `katilma_hesabi`,
`altin_kiymetli_maden`, `dijital_bankacilik`

Dört sınıf fazlaydı (`isyeri_ticari_finansman`, `katilma_hesabi`,
`altin_kiymetli_maden`, `dijital_bankacilik`), dört sınıf eksikti
(`finansman`, `alisveris_puani`, `yeni_musteri`, `yatirim_urunu`),
biri yanlış adlandırılmıştı (`kredi_karti` → `kart`).

**Alınan ders:** Taksonomi tahmin edilemez. ADR 002'nin ilk hâlinde konan
"altın set etiketlemesi bu doğrulama yapılmadan başlamasın" kuralı doğruydu —
tahmini taksonomiyle 100 örnek etiketlenseydi, hepsi yeniden etiketlenecekti.

## Değişimin maliyeti

Tasarım gereği düşük tutulmuştu ve öyle çıktı: tek enum değişti, istem şablonu
ve JSON şeması enum'dan türediği için kendiliğinden güncellendi, `make extract`
yeniden koşuldu. Toplam ~10 dakika, hiçbir çağrı yerinde değişmedi.

## Sonuç

- Sprint 0 bloke olmadı, taksonomi aynı gün doğrulandı.
- Altın set etiketlemesi (15-16 Ağustos) artık doğru taksonomiyle başlayabilir.
