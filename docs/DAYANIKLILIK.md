# Dayanıklılık ölçümü

Şartname 5.2 — *«eksik veya farklı yazılmış bilgiler karşısında doğru sonuç»*.

**369 bozuk varyant** üretildi ve kural katmanında ölçüldü.
Varyantlar `eval/dayaniklilik.py` tarafından KODLA üretilir; elle yazılmaz.

Taban kuralı: bozulmamış metinde zaten bulunamayan değerler ölçüme
girmez — bozma, bulunamayan bir şeyi kaybettiremez.

## İki aile ayrı ölçülür

| Aile | Varyant | Beklenen davranış | Başarı |
|---|---|---|---|
| Biçim bozma | 318 | Değer hâlâ bulunmalı | **%100.0** |
| Alan silme | 51 | Sistem SUSMALI | **%52.9** |

> Alan silmede «başarı», değer üretMEmektir. İki aileyi tek orana
> katmak, susması gereken yerde susmamayı başarı gibi gösterirdi.

### Alan silindiğinde ne oluyor

| Davranış | Vaka | Anlamı |
|---|---|---|
| `sustu` | 27 | Doğru — değer yok, sistem de üretmedi |
| `kaydi` | 24 | Sayfadaki BAŞKA bir sayıya kaydı — **kanıtı var**, seçim hatası |
| `uydurdu` | 0 | Kanıtsız değer — gerçek halüsinasyon |

> 🔑 **`uydurdu` = 0.** Kanıt zinciri tutuyor: kural katmanı,
> doğru cümle silindiğinde bile ham metinde karşılığı olmayan bir değer
> ÜRETMİYOR. Kalan kusur uydurma değil, **seçim** kusuru — sayfadaki
> yanlış sayıya kayıyor. Bu ayrım seçim katmanının alanını belirler:
> düzeltilecek şey çıkarım değil, adaylar arasından seçim.

## Bozma türüne göre

| Bozma | Varyant | Korunan | Oran |
|---|---|---|---|
| `alan_sil` | 51 | 27 | %52.9 |
| `yuzde_bicimi` | 53 | 53 | %100.0 |
| `ondalik_ayraci` | 53 | 53 | %100.0 |
| `bosluk_ekle` | 53 | 53 | %100.0 |
| `buyuk_harf` | 53 | 53 | %100.0 |
| `para_birimi` | 53 | 53 | %100.0 |
| `satir_karistir` | 53 | 53 | %100.0 |

## Alana göre (yalnız biçim bozma)

| Alan | Varyant | Korunan | Oran |
|---|---|---|---|
| `odul_miktari` | 12 | 12 | %100.0 |
| `kampanya_bitis` | 84 | 84 | %100.0 |
| `kar_payi_orani` | 48 | 48 | %100.0 |
| `vade_ay_max` | 102 | 102 | %100.0 |
| `tahsis_ucreti` | 30 | 30 | %100.0 |
| `masrafsiz_mi` | 30 | 30 | %100.0 |
| `finansman_tutari_max` | 12 | 12 | %100.0 |
