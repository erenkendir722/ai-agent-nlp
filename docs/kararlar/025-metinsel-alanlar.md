# ADR 025 — `urun_turu` doldurulur, `masraf_bilgisi` doldurulmaz

**Tarih:** 27 Ağustos 2026 · **Durum:** kabul edildi · **Sorumlu:** Eren
**İlgili bulgu:** şemada duran ama 734/734 kayıtta boş kalan iki metinsel alan
**Şema etkisi:** `SEMA_SURUMU` DEĞİŞMEDİ — `ollama_json_semasi().required`
bir üretim kapısıdır, veri sözleşmesi değil; `KampanyaKaydi`'nin şekli aynı

## Bağlam

`docs/SONUCLAR.md` iki alanı **%0 doluluk** ve **«ölçülmedi»** olarak
raporluyor, ama metrik tablosunda hâlâ bir hedef satırı duruyor:

```
| Metinsel alan doğruluğu | ölçülmedi | ≥ 0,78 | — |
```

Yani sistem, hiç üretmediği bir şey için hedef beyan ediyordu. 734 kayıt:

| Alan | Dolu |
|---|---|
| `kampanya_kosullari` | 704 |
| `kampanya_avantaji` | 546 |
| `hedef_kitle` | 207 |
| **`urun_turu`** | **0** |
| **`masraf_bilgisi`** | **0** |

Sıfırlar bir kaza değil, iki kapının birlikte kapalı olmasıydı:

1. **İstem bu iki alanı hiç anlatmıyordu.** `MUTLAK KURALLAR`ın 4. maddesi
   metinsel alanları sayarken yalnız «(avantaj, koşullar)» diyordu.
   `alan_tanimlari.ALAN_TANIMLARI` on alan tanımlıyor ve ikisi orada da yok —
   üstelik o blok isteme bilerek konmuyor (ölçüldü, makro-F1'i düşürüyor).
2. **`ollama_json_semasi().required` yalnız `kampanya_turu` içeriyordu.**
   Tipler `["string", "null"]` olduğu için model anahtarı ATLAYABİLİYOR ve
   atlıyordu: ham çıktı 16 alandan 4'ünü döndürüyor.

İkisi birleşince model için rasyonel davranış belliydi. 2. kural
«Emin değilsen null yaz», 3. kural «Tahmin etme» diyor; kimsenin tanımlamadığı
bir alan için doğru cevap sessizliktir. Model kusursuz davranıyordu — soru
sorulmamıştı.

## Ölçüm

Aynı 10 kayıt, EVREN `llm-large`, üç yapılandırma:

| Yapılandırma | `urun_turu` dolu | `masraf_bilgisi` dolu |
|---|---|---|
| bugünkü (taban) | 0 / 10 | 0 / 10 |
| + istemde tanıtıldı | 0 / 10 | 0 / 10 |
| + `required`'a eklendi | **9 / 10** | 3 / 10 |

**İstem tek başına yetmiyor** — kapının ikisi de açılmalı.

Çıktı kalitesi ikisinde AYRIŞIYOR ve karar buradan çıktı.

`urun_turu` temiz; alan ne isteniyorsa onu veriyor:

> «Sağlam Business Kredi Kartı» · «Pratik BES» · «Referans Mektupları» ·
> «Hac/Umre Finansmanı» · «Leasing (Yatırım Finansmanı)»

`masraf_bilgisi` zorlandığında **uyduruyor**. Dolan üç kaydın ikisi masrafla
ilgili değil, vade bilgisi:

> «vade farksız» · «vade farksız 9 aya varan taksit imkanı»

## Karar

**`urun_turu` `required` listesine eklenir.** İsteme de kısa bir tanım
konur («kampanyanın bağlı olduğu ÜRÜNÜN adı; kampanyanın adı değildir»).

**`masraf_bilgisi` eklenmez.** İstemde tanımı durur — model gerçekten görürse
yazabilir — ama zorlanmaz.

**Hedef satırı bu alan için düşürülür.** «Metinsel alan doğruluğu ≥ 0,78»
ölçütü `masraf_bilgisi` için geçersizdir ve öyle kalır.

## Gerekçe

**Ölçülemeyen bir alanı zorlamak, kanıtsız değer üretmektir.** ADR 008
`masraf_bilgisi`'ni altın setten çıkardı: alan yalnız LLM katmanından geliyor
ve birebir string karşılaştırmasıyla ölçülemiyor. Cevap anahtarı olmayan bir
alana zorla içerik ürettirmek, o içeriğin yanlış olduğunu KİMSENİN göremeyeceği
anlamına gelir. Bu deponun `Alan(deger=..., yontem="belirtilmemis")` kuralıyla
aynı ilkenin ihlali olurdu — orada da sorun uydurmanın kendisi değil, sessiz
olmasıdır.

`urun_turu` de aynı sebeple altın sette yok, ama farkı ölçüldü: zorlandığında
uydurmuyor. Boş bıraktığı tek kayıtta gerçekten ürün adı yoktu.

**Bedeli ölçüldü ve kabul edildi.** İki alan birden zorlandığında aynı 10
kayıtta üretim bütçesi (`max_tokens=4096`) 3 kez doldu ve kısmi JSON
kurtarmaya düşüldü; yalnız `urun_turu` ile bu 2'ye iniyor. Kurtarma yolu
zaten var ve test edilmiş (`TestKismiJsonKurtarma`), ama bedava değil —
`masraf_bilgisi`'ni dışarıda bırakmanın ikinci kazancı bu.

**`SEMA_SURUMU` neden yükselmedi.** `required` modele ne SORULACAĞINI belirler,
kaydın NE TAŞIYACAĞINI değil. `KampanyaKaydi`'nin alanları, tipleri ve kanıt
zinciri aynı; eski kayıtlar aynı şemaya karşı geçerli kalır. Donma kuralının
istediği şey (ADR'siz değişmesin) burada yerine getirildi, sürüm yükseltmenin
istediği şey (veri şekli değişti) gerçekleşmedi.

## Sonuçları

* `urun_turu` bir sonraki `make extract` koşusunda dolmaya başlar. **Bu ADR
  tek başına veriyi değiştirmez** — `data/katilim.db` yeniden çıkarılana kadar
  alan 0/734 kalır.
* `docs/SONUCLAR.md` doluluk tablosunda `urun_turu` satırı %0'dan çıkacak;
  `masraf_bilgisi` %0'da KALACAK ve bu artık bir kusur değil, beyan edilmiş
  bir karardır.
* Jüriye verilecek cevap: «on altı alanın on beşini üretiyoruz; on altıncısını
  ölçemediğimiz için zorlamıyoruz» — ölçümü olan bir cümle.

## İlgili

* [ADR 008](008-altin-set-kapsami.md) — metinsel alanlar altın sette neden yok
* [ADR 013](013-evren-model-lisans-durusu.md) — EVREN `llm-large` sözleşmesi
* `src/extraction/saglayici.py` — `response_format.json_schema`, üç sessiz tuzak
