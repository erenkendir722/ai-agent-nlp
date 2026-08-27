# ADR 021 — Soru anlama sözlükten ve veriden türer, elle yazılmaz

**Tarih:** 27 Ağustos 2026 · **Durum:** kabul edildi · **Sorumlu:** Eren
**İlgili bulgu:** jüri soru havuzu (35 soru) uçtan uca koşumu
**Şema etkisi:** yok — `SEGMENT_ORNEKLERI` sabiti eklendi, alan değişmedi

## Bağlam

Jüri soru havuzu baştan sona koşuldu. Yirmi beş veri sorusunun on üçü tam
cevaplanıyordu; kalanların deseni tekti: **sorulan şey hiç tanınmıyor, sorudaki
başka bir sözcük ölçüt sanılıyordu.**

```
S12: «48 ay vadeli taşıt finansmanında en düşük TOPLAM MALİYET…»
       -> «Vade en düşük olan banka: 3 ay»
S14: «Katılma hesaplarında en yüksek KÂR PAYLAŞIM oranı?»
       -> «Vade açısından Albaraka daha avantajlı: 120 ay»
S23: «KOBİ, esnaf ve tüzel segment müşterilerine özel…»
       -> «Kuveyt Türk — Alışveriş Puanı Kampanyası: aylık %1,99»
S17: «…standart tek bir formatta filtreleyebiliyor musun?»
       -> rastgele kampanya dökümü
```

Ortak sebep: chatbot'un soru anlama sözlüğü **elle yazılmıştı**. `_OLCUT_IPUCLARI`
sabit sıradaydı ve ilk eşleşen kazanıyordu; «vade» dört harfti ve her şeyi
yeniyordu. Segment ve sistem soruları için hiç dağarcık yoktu.

Elle yazılan listenin iki hatası da sessizdir: eksik kalır (segment), ve
veriyle/dokümanla ayrışır (ölçüt).

## Karar

Soru anlama üç kaynaktan **türetilir**, hiçbiri chatbot'ta elle tutulmaz.

### 1. Ölçüt eşlemesi — `docs/TERIM_SOZLUGU.md`

Sözlüğün «Sistemdeki karşılığı» sütunu terimi şema alanına zaten bağlıyor.
`terim_sozlugu.alan_eslemesi()` onu okur. Yan kazanç: «nakit iade» ve «mil»
sözlükte `odul_miktari`'na bağlı, elle yazılan listede yoktu.

Sütun kimlik kurmadığında **onu da beyan ediyor** ve iki davranış daha
buradan çıkıyor:

| Sütun der ki | Davranış |
|---|---|
| `` `odul_miktari` `` | ölçüt — sıralanır |
| `` `kar_payi_orani` `` ile **KARIŞTIRILMAZ** | ayrımı söyle, sıralama |
| tek alan değil, **hesaplanır** | formül — eksik girdiyi sor |

İki incelik ölçülerek çıktı:

* **İlk cümlecik kimliği kurar.** `` `odul_miktari`; `kar_payi_orani` VETOSU ``
  satırında terim ödül miktarıdır ve ayrıca «kâr payı değildir» diye uyarılır.
  Sütunun tamamında veto sözcüğü aramak geçerli kimliği de siliyordu.
* **Küçük harf şema alanıdır.** Şema alanları `snake_case`, veto sabitleri
  `BUYUK_HARF` (`MEVDUAT_URUNU`). Ayrım yazım biçiminden okunur.

**Sıra uzunluktan gelir**, elle yazılmış bir öncelikten değil: «toplam maliyet»
on üç harf, «vade» dört. Uzun olan daha özgüldür.

### 2. Segment dağarcığı — korpustan

`uygunluk.segment_detayi` 133 kayıtta dolu ve yedi segment taşıyor
(genç · KOBİ · emekli · çiftçi · esnaf · öğrenci · kadın girişimci). Uygunluk
ajanı bunu çıkarıyordu, chatbot bakmıyordu. Dağarcık her çağrıda kayıtlardan
okunur; çıkarım yeni segment üretirse süzgeç kendiliğinden tanır.

Sorulan segment korpusta yoksa **uydurma yerine kapsam** söylenir: «sağlık
çalışanlarına özel işaretlenmiş kampanya yok; işaretli segmentler şunlar».

### 3. Sistem soruları — Türkçe şahıs ekinden

Jüri havuzunun on sorusu sistemin kendisi hakkında ve kampanya verisinden
cevaplanamaz. Ayrım bir konu listesi değil, bir **dilbilgisi kuralı**: soru
ikinci şahısla bize hitap ediyorsa muhatap sistemdir.

```
«… filtreleyebiliyor MUSUN?»   «… nasıl ayrıştırıyorSUN?»
«… nasıl parse ettiNİZ?»       «… nasıl garanti ediyorSUNUZ?»
```

Veri soruları etkilenmez: «vade veriyor mu?» üçüncü şahıstır.

İki incelik, ikisi de ölçülerek:

* **Kibar istek de ikinci şahıstır.** «Kampanyaları en avantajlıdan sıralar
  mısın?» bir veri isteğidir. Ayırt edici kip değil **soru sözcüğüdür**:
  yöntem sorusu «nasıl» diye sorar, istek sormaz.
* **Alt dize eşleştirmesi yasak.** «geçEN kâr payı oranları» ifadesinde «en»
  bulunuyordu; ürün sözlüğündeki «ev»in «ters çEVrilir» içinde bulunmasının
  aynısı. Bütün ipuçları `terim_gecer` ile sözcük başına bağlanır.

Cevap kibar ret değil **doğru adrestir**: soru meşru, cevabı depoda yazılı —
`docs/MIMARI.md`, `docs/SARTNAME_UYUM.md`, `docs/kararlar/`.

## Reddedilenler

**Modül adlarından öz-gönderim dağarcığı türetmek.** `comparison/karsilastirma`
modülünün adı kullanıcının en sık yazdığı sözcüktür; «Kuveyt Türk ile Albaraka
karşılaştırması» sistem sorusu sayılırdı. Beş sözcüklük açık bir küme
(`sistem`, `chatbot`, `mimari`, `algoritma`, `yaklaşım`) tutuluyor ve tek
başına yetmiyor — «nasıl» ile birlikte ve soruda banka adlandırılmamışken.

**Tarih süzgeci.** `kampanya_bitis` 361/931 dolu ama süresi geçmiş olan **5**
kayıt var. Süzgeç yerine gösterilen kaydın yanına «süresi dolmuş» notu
düşülüyor; toplu eleme zaten `tools/suresi_gecenleri_ele.py`'nin işi.

**«X Katılım Bankası» gibi yer tutucuları yakalamak.** Kapıyı sıkılaştırmak
«katılım bankaları hangileri?» gibi meşru soruları düşürürdü. Gerçek jüri
şablon adla sormaz.

## Ölçüm

| | önce | sonra |
|---|---|---|
| Jüri havuzu — sistem sorusu doğru sınıflanan | 4/10, tesadüfen | **10/10** |
| Jüri havuzu — tam cevaplanan veri sorusu | 13/25 | ölçüm cevapta |
| 189 soruluk tarama | 0 sorun | 0 sorun |
| `make chatbot-test` | 31/31 | 31/31 |

## Alınan ders

Chatbot'un soru anlama sözlüğü, projenin **zaten sahip olduğu** üç bilgi
kaynağının hiçbirine bakmıyordu: terim sözlüğü, uygunluk çıkarımı ve Türkçe'nin
kendi dilbilgisi. Elle yazılmış üçüncü bir liste tutmak, o listenin
diğerlerinden ayrışmasını garanti etmekti.
