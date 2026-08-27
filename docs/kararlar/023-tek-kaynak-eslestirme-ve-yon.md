# ADR 023 — Eşleştirme ve yön tek kaynaktan: banka süzgeci, ölçüt sırası, kesme eki

**Tarih:** 27 Ağustos 2026 · **Durum:** kabul edildi · **Sorumlu:** Eren
**İlgili bulgu:** [ADR 022](022-sohbet-baglami.md)'nin «kapsam dışı» listesi
**Şema etkisi:** yok

## Bağlam

ADR 022 çok turlu sohbeti açtı ve üç eksiği **görünür kıldı**. Üçü de tek
turlu sorularda da vardı; sohbet onları yalnız gün yüzüne çıkardı.

```
1) «Albaraka'dan 1.000.000 TL konut finansmanı, 120 ay vade»
     -> dokuz bankanın 18 kampanyası, toplam maliyete göre sıralı
     Adlandırılan banka cevapta hiç dikkate alınmıyor.

2) «Albaraka … 120 ay vade»
     -> «Albaraka Türk — Diğer: … Azami vade: 6 ay»
     Sorulan ölçütü TAŞIYAN kayıt seçiliyor ama taşıyanlar arasında sıra yok.

3) «Albaraka'dan …», «Albaraka'nın vadesi kaç ay?»
     -> HİÇBİR bankaya eşleşmiyor.
```

Üçüncüsü ikisinin de altında yatıyordu: `arama_anahtari` kesme işaretini
**siler** ve `_bankalari_bul` sözcük kümesini kurarken `anahtar.replace("'", " ")`
yazıyordu — yani niyet doğruydu ama `anahtar` zaten kesmesizdi. **Satır
ölüydü** ve kimse fark etmemişti, çünkü testler kesmesiz yazımları deniyordu.

## Karar

### 1. Banka eşleştirmesi tip bağımsızdır — `sorulan_bankalar`

Eşleştirme banka **adından** başka hiçbir alana bakmıyor. O yüzden çekirdek
imza artık `(soru, banka_adlari) -> eşleşen adlar`; `_bankalari_bul` bunun
`KampanyaKaydi` sarmalayıcısı, `_banka_suz` ise `Kampanya` sarmalayıcısı.

Profil kolu artık aynı kapıdan geçiyor: yazım hatası toleransı, benzersiz
sözcük kapısı ve «hangi banka» ayrımı orada da kendiliğinden geçerli.
İkinci bir eşleştirici yazmak bu depoda **ölçülmüş** bir hata — 27 Ağustos'ta
`alan_disi_soru`'nun kopyası geride kalmış ve aynı soruya iki kapı iki farklı
cevap vermişti.

**Banka süzgeci üründen ÖNCE koşar.** Sonra koşsaydı ad kümesi ürün süzgeci
tarafından daraltılmış olurdu: «Albaraka konut» sorusunda Albaraka'nın konut
kaydı yoksa «albaraka» hiçbir ada eşleşmez, süzgeç boş döner ve **dokuz
bankanın tamamı** geri gelirdi — yani sorulmayan bankalar. Nöbetçi:
`test_banka_suzgeci_urun_suzgecinden_once_kosar`.

### 2. «Hangi uç avantajlı» tek yerde beyan edilir — `ALAN_YONLERI`

Bu bilgi iki yerde ayrı yazılıydı: `_SIRALAMA_ALANLARI` ve `avantaj_skorla`'nın
bileşen tanımları. İkisi bugün aynı şeyi söylüyordu, ama ayrışmaları için tek
bir düzeltmenin tek yere yazılması yetiyordu — ve ayrıştıklarında **sıralama
ile skor birbirinin tersini** gösterirdi.

Artık tek beyan `ALAN_YONLERI`; iki tüketici oradan **türer**, üçüncüsü
chatbot'un tekil cevabıdır:

```
_odak_sirasi(kayit, alan, yon)
    kullanıcı ucu söylediyse ondan          («en kısa vade»)
    söylemediyse ALAN_YONLERI'nden          (vade -> yuksek_iyi)
    hiçbiri yoksa SIRALAMA YAPILMAZ         (karar dolulukla kalır)
```

Son satır önemli: uydurulmuş bir yön, sessizce yanlış kaydı vitrine koymak
olurdu. `Alan(deger=..., yontem="belirtilmemis")` neden patlıyorsa aynı sebep.

Tekil cevabın sıralamayla aynı yönü kullanması bir **tutarlılık şartı**:
«en uzun vadeyi kim veriyor?» ile «Albaraka'nın vadesi ne?» aynı kaydı
göstermeli. Aynı sebeple ADR 020'nin kapsam kapısı (`olcut_kapsaminda`)
sıralamaya da uygulanıyor — karşılaştırmanın dışladığı kart promosyonunu
tekil cevap vitrine koyamaz.

Kapı **yalnız sıralamaya** uygulanır, kaydın seçilebilirliğine değil:
«sorulan alanı taşıyan kayıt önceliklidir» kuralı kapsamdan bağımsız durur,
yoksa `kampanya_turu` boş olan bir kaydın yazdığı oran hiç görünmez olurdu.

### 3. Kesme işareti özel adı ekinden ayırır — `kesmeden_ayir`

`arama_anahtari` kesmeyi silmeye devam ediyor; tokenizasyon için doğrusu
odur («TL'ye» tek belirteçtir). Özel ad eşleştirmesi ise sorunun sözcüklerini
`kesmeden_ayir`'dan geçirerek kuruyor: «Albaraka'dan» → «albaraka dan».

## Reddedilen

**Ekin serbest bırakılması.** `terim_gecer` gibi baş bağlayıp sonu serbest
bırakmak daha genel görünürdü ve «Albaraka'dan»ı kesmesiz de çözerdi. Ama
«emlakçı» o zaman Türkiye Emlak'a eşleşirdi — `YAKINLIK_ESIGI` bu eşleşmeyi
**ölçerek** dışarıda bırakmıştı (0,833 < 0,88). Kesme kullanıcının kendi
koyduğu bir sınırdır; ek serbestliği bizim tahminimiz olurdu. Nöbetçi:
`test_kesme_ayrimi_ek_serbestligi_getirmez`.

## Ölçüm

| | önce | sonra |
|---|---|---|
| «Albaraka'dan 1.000.000 TL konut, 120 ay» | 18 kampanya / 4 banka | **5 kampanya / yalnız Albaraka** |
| Banka adlandırılmayan aynı soru | 18 kampanya / 4 banka | **değişmedi** |
| «Albaraka … 120 ay vade» | Diğer, azami vade 6 ay | **Konut Finansmanı, azami vade 120 ay** |
| «Albaraka'nın vadesi kaç ay?» | eşleşme yok → Kuveyt Türk | **Albaraka, 120 ay** |
| «emlakçı kredisi» | eşleşme yok | **değişmedi** (eşleşme yok) |
| `make chatbot-test` | 31/31 | 31/31 |
| `eval/kalkan` köken dağılımı | duz 24 · alıntı 44 · yapısal 21 · sistem 8 | **birebir aynı** |
| `make test` | 1459 | 1536 |

Köken dağılımı satırı HEAD'de ayrı bir çalışma ağacı kurularak ölçüldü:
kalkan metrikleri bayt düzeyinde değişmedi.

> ⚠️ `docs/SONUCLAR.md` alıntı parçası sayısını **38** yazıyor; gerçek değer
> bu değişikliklerden ÖNCE de 44'tü. Dosya 9a9ffc2'de üretilmiş, sonraki üç
> chatbot commit'i onu tazelemedi. Bu ADR'nin açtığı bir sapma değil; bir
> sonraki `make eval` koşusunda kendiliğinden düzelir.

## Alınan ders

Üç kusurun üçü de **ikinci bir kopya** yüzündendi: ikinci bir eşleştirici
(banka), ikinci bir yön beyanı (`dusuk_iyi`), ve niyeti doğru ama girdisi
yanlış ikinci bir ayırıcı (`replace("'", " ")`). Kopyanın maliyeti yazıldığı
gün değil, biri güncellenip diğeri unutulduğu gün ödeniyor — ve o gün hiçbir
test kırılmıyor.
