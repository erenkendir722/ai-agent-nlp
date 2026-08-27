# ADR 024 — Sorulan yuva duyulur, kapılar dilbilgisine bağlanır

**Tarih:** 27 Ağustos 2026 · **Durum:** kabul edildi · **Sorumlu:** Eren
**İlgili bulgu:** tek bir «zor soru» + 194 soruluk üretilmiş tarama
**Şema etkisi:** yok — `Niyet.SISTEM_SORGUSU` eklendi, `schema.py` değişmedi

## Bağlam

Sisteme kasten zor bir soru soruldu:

> «Emlak Katılım'ın 120 ay vadeli konut finansmanında toplam maliyeti,
> Kuveyt Türk'ünkinden düşük mü?»

Yedi kapıyı birden zorluyor: adın ortasından tutan benzersiz ikili · iki
kesme eki · iki banka · ürün sınıfı · sayısal kısıt · **hesaplanan** ölçüt ·
evet/hayır biçimi. Bankaları tanıdı ([ADR 023](023-tek-kaynak-eslestirme-ve-yon.md)),
ama sorulan ölçütü «Vade» sandı. Yanındaki soru daha kötüsünü yaptı:

```
«Kâr payı oranı en düşük OLAN BANKA aynı zamanda en uzun vadeyi de veriyor mu?»
  -> «Sorduğunuz banka bir katılım bankası değil…» + dokuz bankanın listesi
```

Soruda hiçbir banka adlandırılmamıştı.

## Karar

### 1. «Toplam maliyet» sözlüğe eş anlamlı yazım olarak girer

`_sorulan_olcutler` «… en düşük **toplam maliyet** …» sorusunda `vade_ay_max`
döndürüyordu. Bu, [ADR 021](021-sozlukten-turetilen-soru-anlama.md)'in manşet
örneğidir ve o ADR düzeltildiğini söylüyordu. Çözümü («sıra uzunluktan gelir»)
doğruydu ama **ipucunun sözlükte olmasına bağlıydı** — sözlükte yalnız resmî
ad vardı: «Finansman Maliyeti». Kullanıcı öyle konuşmuyor.

Düzeltme koda değil, `docs/TERIM_SOZLUGU.md`'ye yazıldı:

```
### Finansman Maliyeti / Toplam Maliyet
```

Eğik çizgi sözlükte zaten EŞ ANLAMLI YAZIM ayıracıdır («dosya masrafı / dosya
parası»); `hesaplanan_olcutler()` iki anahtarı da kendiliğinden üretir. Kod
satırı eklenmedi.

> Sözlük gövdesi KULLANICIYA OKUNUR. İlk denemede gerekçe oraya yazılmış ve
> chatbot ADR metnini cevap diye okumuştu. Sözlük tanım tutar, gerekçe ADR'de.

### 2. Sorulan yuva CEVAPTA BEYAN EDİLİR — `Cevap.beklenen_yuvalar`

[ADR 022](022-sohbet-baglami.md)'nin dersi bir kez daha, başka bir kolda:

```
tur 1: «48 ay vadeli … en düşük toplam maliyet hangi bankada?»
         -> «Hesap için anapara gerekiyor»
tur 2: «1.000.000 TL»
         -> «Bu soru sistemin kapsamı dışında»                        ✗
```

Çıplak nicelikte hiçbir alan sözcüğü geçmez; dayanak kapısı onu **haklı
olarak** reddediyordu — sistemin kendi sorusuna verilen cevabı.

Artık kullanıcıdan bilgi isteyen her cevap, hangi yuvayı istediğini bildirir
(`Cevap.beklenen_yuvalar`). İki üretici var ve ikisi de aynı ölçüyü kullanır
(`chatbot.eksik_nicelikler`): profil kolu ve hesaplanan ölçüt cevabı. Bağlam
bunu taşır, devir sonraki turda o yuvayı doldurur.

**Dayanak kapısının muafiyeti DAR:** yalnız `alan_disi_soru` yarısını kapsar,
`Niyet.KAPSAM_DISI` (açık kapsam dışı işaret) yarısını değil; ve yalnız
sistemin SORDUĞU yuvayı dolduran bir nicelik geldiyse açılır. Muafiyetin
dayanağı metin değil, **konuşma durumudur**.

Yan kazanç: cevap artık yalnız EKSİK olanı sorar. «48 ay vadeli … toplam
maliyet» sorusunda vade zaten verilmişti ve sistem yine de «anapara ve vade»
istiyordu — kullanıcının söylediğini görmezden gelip yeniden sormak, soruyu
anlamamış görünmektir.

### 3. Banka kapısı SIFAT-FİİL ekine bağlanır

`_BELIRTEC_SOZCUKLERI` sabit bir listeydi ve «olan» orada yoktu. Listeye
«olan» eklemek aynı hatayı «sunan», «veren», «sağlayan», «uygulayan»,
«düzenlediği» için tekrar etmek olurdu.

`SIFAT_FIIL_EKLERI` bir sözcük listesi değil, bir dilbilgisi kuralıdır —
`MUHATAP_EKLERI` ile aynı refleks. Türkçe'de fiil bu eklerle sıfata dönüşür ve
ardındaki adı **niteler**; nitelenen ad bir kurum adı değil, bir tariftir.

Dört harf sınırı var: «an» ve «en» iki harf, tek başına aranırsa ad olan
sözcükleri de yakalar. «olan» (4) içeri, «en» (2) dışarı.

İki kural yan yana duruyor: belirteç (hangi · her · tüm) ve sıfat-fiil (olan ·
sunan · veren) — iki farklı dilbilgisi olgusu, iki ayrı kapı.

### 4. Sistem sorusunun kendi niyeti var — `Niyet.SISTEM_SORGUSU`

`_sistem_cevabi`'nin docstring'i «Kibar ret DEĞİL, DOĞRU ADRES» diyordu ama
etiketi `KAPSAM_DISI`'ydı. Arayüzdeki rozet «⑥ Kapsam dışı — Kibar ret»
yazıyor, cevap ise dokümantasyon adresi veriyordu. Jüri «Hangi modeli
kullanıyorsunuz?» diye sorup cevabını alırken ekranda reddedildiğini
görüyordu. **Etiket cevabın kendisiyle çelişemez.**

`eval/chatbot_sorulari.yaml`'daki `kapsam_disi` beklentilerinin hiçbiri sistem
sorusu değil (hava durumu · şiir · Bitcoin · Garanti · kehanet), dolayısıyla
ölçüm etkilenmedi.

### 5. Kayıt kullanmayan cevapta banka SORUDAN devrolur

Kullanıcıdan bilgi isteyen cevabın yapısal parçası yoktur: «Albaraka'dan
1.000.000 TL konut» → «vade eksik» cevabı hiçbir kayıt göstermez. Bağlam
bankayı yalnız `kullanilan_kayitlar`'dan okuduğu için sohbet o bankayı
unutuyordu ve sonraki tur dokuz bankayı sıralıyordu — tam da kullanıcının
adlandırdığı bankayı yok sayarak.

Kural dar: yalnız cevap HİÇ kayıt kullanmadığında soruya bakılır. Üçten çok
banka kullanan cevabın bankalarını sıfırlayan kural ([ADR 022](022-sohbet-baglami.md))
yerinde duruyor; ikisi farklı durumlardır.

### 6. Boşluk taraması kalıcı araç oldu — `make chatbot-tarama`

`eval/chatbot_sorulari.yaml` 31 soruyu ELLE tutuyor ve her birinin beklenen
davranışını yazıyor: derin, ama kapsamı elle yazıldığı kadar. Yeni araç
tersini yapar — soruları **korpustan ve şemadan üretir** (dokuz banka × beş
ölçüt × altı ürün × yazım biçimleri = 194 soru), beklenen cevabı bilmez,
yalnız patoloji arar:

```
P1 meşru soru reddedildi · P2 ölçüt kayması · P3 yanlış banka
P4 kalkan reddi · P5 istisna · P6 kapsam dışı sızdı
P7 reddedilebilir iddia reddedilmedi · P8 tanım tanınmadı
```

Buradaki iki kusuru da elle yazılan set göremezdi, çünkü ikisini de sormuyordu.
Ağ kullandığı için `eval/` altında, `tests/` altında değil.

## Ölçüm

| | önce | sonra |
|---|---|---|
| «… en düşük toplam maliyet hangi bankada?» | «Vade en düşük: 3 ay» | **formül beyan edilir, anapara sorulur** |
| «… toplam maliyet» → «1.000.000 TL» | kapsam dışı | **16 kampanya, toplam maliyete göre sıralı** |
| «kâr payı en düşük olan banka…» | kibar ret + 9 banka listesi | **karşılaştırma cevabı** |
| «Emlak Katılım … Kuveyt Türk'ünkinden düşük mü?» → «1.000.000 TL» | 9 bankaya açılıyordu | **yalnız o iki banka** |
| «Hangi modeli kullanıyorsunuz?» rozeti | ⑥ Kapsam dışı — Kibar ret | **⑥ Sistem sorusu — Dokümantasyon adresi** |
| «Garanti Bankası…», «Akbank…» | reddedilir | **değişmedi** |
| `make chatbot-tarama` | — | **194 soru, 0 bulgu** |
| `make chatbot-test` | 31/31 | 31/31 |
| `make test` | 1545 | 1566 |

## Alınan ders

Üç kusurun üçü de **elle yazılmış bir listenin** eksik kalmasıydı: sözlükte
olmayan bir yazım, belirteç listesinde olmayan bir sözcük, cevabın neyi
sorduğunu bildirmeyen bir alan. Liste tamamlanamaz; kural tamamlanır.

Ve bir kez daha aynı ders: **bir arayüzün kullanıcıya soru sorması, o cevabın
gideceği yuvanın var olduğunu taahhüt etmektir.** ADR 022 bunu profil kolunda
öğrendi; hesaplanan ölçüt kolunda aynı delik açık duruyordu.
