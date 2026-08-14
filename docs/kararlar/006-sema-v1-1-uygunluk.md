# ADR 006 — Şema v1.1.0: uygunluk koşulları eklendi

**Tarih:** 14 Ağustos 2026
**Durum:** Kabul edildi
**Sahip:** Eren
**İlgili:** [001 — Şema sözleşmesi önce donar](001-sema-sozlesmesi.md) · [005 — Ajan mimarisi](005-ajan-mimarisi.md)

## Bağlam

Mentör görüşmesi sonrası ürün tanımı genişledi: sistem artık yalnız kampanya
bilgisi çıkarmıyor, **banka çalışanının önündeki müşteri profiline göre hangi
kampanyaların gerçekten uygulanabilir olduğunu** buluyor.

Bu, çıkarımdan farklı bir yetenek. *"Maaş müşterisi, 800.000 TL, 120 ay"*
sorusu bir arama değil **kısıt çözme** problemidir: koşullar birbiriyle
kesişir (yeni müşteri VE tutar aralığı VE vade sınırı VE zorunlu ürün).

Mevcut şemada bu bilgi `kampanya_kosullari` içinde **serbest metin** olarak
duruyor. Serbest metinle kısıt çözülemez — "en az 500.000 TL" cümlesini her
sorguda yeniden yorumlamak, hem yavaş hem de LLM'e aritmetik yaptırmak demek
olurdu ([ADR 005](005-ajan-mimarisi.md): aritmetik ajana verilmez).

**Zorluk:** şema 9 Ağustos'ta v1.0.0 olarak donduruldu ([ADR 001](001-sema-sozlesmesi.md))
ve altın set etiketlemesi ona karşı yapıldı. Şemayı değiştirmek, etiketlenmiş
cevap anahtarını hizasız bırakma riski taşıyor.

## Seçenekler

1. **Şemayı hiç değiştirmemek**, uygunluğu sorgu anında serbest metinden
   çözmek. Kısıt çözücü her sorguda LLM çağırırdı; determinizm kaybolur,
   gecikme artar, `kampanya_kosullari` doluluğu %59 olduğu için kayıtların
   %41'i sessizce elenirdi.
2. **v2.0.0 kırıcı sürüm** — `uygunluk`'u zorunlu alan yapmak ve altın seti
   yeniden etiketlemek. 60 örneklik etiketleme emeği çöpe gider; 12 gün kala
   karşılanamaz.
3. **v1.1.0 toplama değişikliği** — `uygunluk`'u opsiyonel ve `Alan` tipinde
   **olmayan** bir alan olarak eklemek.

## Karar

Seçenek 3.

```python
class Kampanya(BaseModel):
    ...                                        # v1.0.0 alanları aynen
    uygunluk: UygunlukKosullari | None = None  # YENİ
```

**Neden donmuş sözleşme bozulmuyor — mekanizma:**

`ALAN_ADLARI` yalnız `annotation is Alan` olan alanları toplar
(`schema.py`), `cikarilan_alanlar()` da `isinstance(deger, Alan)` filtreler.
`uygunluk` farklı tipte olduğu için bu iki türetmenin ikisine de girmez.
Sonuç olarak değişmeden kalanlar:

| Etkilenmeyen | Neden |
|---|---|
| `ALAN_ADLARI` (16 alan) | tip filtresi dışında |
| `doluluk_orani()` · `ortalama_guven()` | `cikarilan_alanlar()` üzerinden çalışır |
| `kanit_denetimi()` | aynı |
| Altın set CSV başlıkları | `csv_basliklari()` `ALAN_ADLARI`'ndan beslenir |
| `depolama.kaydet()` düz sütunları | `SAYISAL_ALANLAR` üzerinden gider |

Bu, `tests/test_sema.py` içinde teste bağlandı — ileride biri `Alan` tipinde
yeni bir alan eklerse test kırılır ve altın set sessizce kaymaz.

### İki alt karar

**`musteri_tipi` için yeni sözcük dağarcığı tanımlanmadı.** Mevcut `HedefKitle`
enum'u yeniden kullanılıyor. Aynı kavram için ikinci bir liste
(`"yeni"/"mevcut"/"maas"`) tanımlamak, iki listenin zamanla ayrışmasını garanti
ederdi: çıkarım birini, muhakeme diğerini doldurur ve eşleşme sessizce bozulur.
`HedefKitle.SEGMENT` geniş olduğu için (öğrenci, emekli, KOBİ) segment adı
`segment_detayi` içinde ayrıca tutulur — emekliye açık bir kampanya öğrenciye
önerilmesin.

**Türetilmiş maliyet alanları şemaya KONMADI.** `toplam_geri_odeme`,
`aylik_taksit`, `efektif_maliyet` müşteri profiline (tutar, vade) bağlı
hesaplardır; aynı kampanya farklı profil için farklı taksit verir. Şemaya
konsalardı veritabanında bayat değer saklanır ve kanıt zinciri ilkesi
delinirdi — hesaplanmış bir sayının "kaynağı" yoktur. Yerleri muhakeme
ajanının döndürdüğü `UygunlukSonucu.maliyet`; hesap zaten
`comparison.toplam_maliyet()` içinde mevcut.

## Sonuç

- Sürüm `1.0.0` → `1.1.0`. Kayıtlar kendi `sema_surumu`'nu taşıdığı için eski
  kayıtlar `1.0.0` olarak okunmaya devam ediyor (96 kayıtla doğrulandı).
- Altın set **yeniden etiketlenmedi**; 60 örneklik emek korundu.
- `uygunluk` çoğunlukla mevcut alanlardan **türetilir** — `max_tutar` ←
  `finansman_tutari_max`, `max_vade_ay` ← `vade_ay_max`, `ek_sartlar` ←
  `kampanya_kosullari`. Yalnız `min_tutar`, `min_vade_ay` ve `zorunlu_urun`
  yeni çıkarım gerektirir. Bu, ek çıkarım maliyetini üç alana indirdi.
- Ters aralık (`min > max`) doğrulamada reddediliyor: sessizce her kampanyayı
  eleyen bir kısıt, hata olarak patlamaktan çok daha pahalıdır.
