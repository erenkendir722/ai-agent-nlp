# Görülmemiş Metin Ölçümü

_Otomatik üretildi: 19.08.2026 15:32 · `make eval-gorulmemis`_

> Bu dosya elle düzenlenmez.

## Soru

Jüri 19 Ağustos'ta *«o anda jüri kendisi de test verisi verebilir»* dedi.
Altın set «bizim seçtiğimiz 60 örnekte ne kadar iyiyiz?» sorusunu
cevaplıyor. Bu ölçüm farklı bir soruyu cevaplıyor: **hiç görülmemiş bir
metinde sistem sözleşmesine uyuyor mu?**

## Veri

- Görülmemiş sayfa: **187** · işlenen: 187 · gövdesi kısa/atlanan: 0
- Banka: 4 · çıkarım katmanı: yalnız kural

> Bu sayfalar 9 Ağustos taramasında gerçekten çekildi, korpus seçimi
> sırasında dışarıda kaldı ve **geliştirme boyunca hiç görülmedi** —
> ne kural yazarken bakıldı, ne altın sete girdi, ne bir metrik onlara
> göre ayarlandı. Jürinin vereceği veriye en yakın vekil budur.

## Sözleşme ihlalleri (etiket gerektirmez)

| Denetim | Değer | Hedef | Durum |
|---|---|---|---|
| Çöken kayıt | 0 | 0 | ✅ |
| **Kanıt ihlali** (halüsinasyon) | 0 (%0.00) | 0 | ✅ |
| Boyut ihlali (birimsiz değer) | 0 | 0 | ✅ |
| Çözülmemiş span çakışması | 0 | 0 | ✅ |

> 🔎 **Teşhis (ihlal değil):** aynı sayıya iki kuralın talip olduğu **124** durum saptandı ve `_tek_atama` hepsini çözdü. Bu sayının sıfır olması BEKLENMEZ — iki kuralın aynı sayıya talip olması doğaldır. Anlamı şu: tek atama düzeltmesi görülmemiş 187 sayfada **124 kez** devreye girdi, yani düzeltilen hata nadir bir uç durum değildi.

> **Ne ölçmez — dürüst sınır.** Bu tablo DOĞRULUK ölçmez. Çıkarılan
> değerin doğru olup olmadığını bilmiyoruz; yalnız **kanıtlı** olduğunu
> biliyoruz. Doğruluk için altın set gerekir. İki ölçüm birbirinin
> yerine geçmez, farklı soruları cevaplar.

## Kapsam

- Alan doluluğu: **%8.2** (246/2992)

| Alan | Dolu kayıt |
|---|---|
| `vade_ay_max` | 81 |
| `finansman_tutari_max` | 38 |
| `masrafsiz_mi` | 38 |
| `kampanya_bitis` | 26 |
| `tahsis_ucreti` | 17 |
| `kar_payi_orani` | 15 |
| `odul_miktari` | 14 |
| `alisveris_puani` | 10 |
| `indirim_orani` | 7 |
