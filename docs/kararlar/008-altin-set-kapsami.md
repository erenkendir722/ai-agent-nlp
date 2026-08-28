# ADR 008 — Altın set 16 alanı değil, 8 alanı etiketler

**Tarih:** 15 Ağustos 2026
**Durum:** Kabul edildi
**Sahip:** Eren
**İlgili:** [001 — Şema sözleşmesi önce donar](001-sema-sozlesmesi.md) · [003 — Hibrit çıkarım](003-hibrit-cikarim.md)

## Bağlam

Altın set çalışması iki kez tökezledi ve ikisinin de kökü aynı yerdeydi.

**Birincisi ölçümü geçersiz kıldı.** Etiketlerin bir bölümü bir dil modeline
yaptırıldı. Bu, altın setin varlık sebebini ortadan kaldırır: set sistemi
ölçmek için var; etiketi başka bir model üretirse ölçtüğümüz şey doğruluk
değil, iki modelin birbirine benzerliğidir. Üstelik iki dil modeli aynı metni
okurken aynı yerlerde yanılır — gerçek hata görünmez kalır ve ablasyon tablosu
da aynı sapmayı taşır.

**İkincisi birincisinin sebebiydi.** Süreç, dört kişilik bir öğrenci takımının
kaldırabileceğinden ağırdı: 20 sütunlu CSV (16'sı etiketlenecek), 403 satırlık
kılavuz, 7 make komutu, üç ayrı dosya ailesi. Satır başına ~4 dakika, kişi
başına ~90 dakika. Kimse kötü niyetli davranmadı; süreç insanları modele itti.

Ölçüm tasarımını korurken maliyeti düşürmek gerekiyordu.

## Karar

Altın set **sekiz çekirdek alanı** etiketler:

`kampanya_turu` · `kar_payi_orani` · `vade_ay_max` · `finansman_tutari_max` ·
`tahsis_ucreti` · `masrafsiz_mi` · `odul_miktari` · `kampanya_bitis`

Kalan sekiz alan CSV'de **sorulmaz**. Uyum bloğu 10 satırdan 5'e iner. Örneklem
60'ta kalır.

`src/schema.py` **değişmez** — bu bir kapsam kararıdır, şema kararı değil.
Sistem on altı alanı çıkarmaya devam eder; yalnız sekizinin **cevap anahtarı**
vardır.

## Gerekçe

**Dışarıda kalan alanların yarısı zaten ölçüm üretmiyordu.** 96 kampanyada
`urun_turu` %0, `alisveris_puani` ve `masraf_bilgisi` %1, `hedef_kitle` %4
doluluğa sahip. 60 örneklik bir sette bu alanlar birkaç örnek bile üretmez;
oradan çıkan "doğruluk" sayısı sunumda savunulamaz.

**Diğer yarısı — serbest metin alanları — ölçülemez.** `kampanya_avantaji`,
`kampanya_kosullari`, `urun_turu` ve `masraf_bilgisi` yalnız LLM katmanından
geliyor (`src/extraction/llm.py`), kural katmanında karşılıkları yok. `eval`
bunları birebir küçük-harf string karşılaştırmasıyla ölçüyor
(`_degerler_esit`). Elle yazılmış bir cümlenin modelin ürettiği cümleyle harfi
harfine tutması pratikte imkânsız — bu alanların skoru, etiketleme ne kadar iyi
olursa olsun ~0 çıkardı.

Yani en yorucu dört alan, aynı zamanda skoru garanti sıfır olan alanlardı.
Etiketlemeye harcanan emeğin karşılığı yoktu.

**Sekiz alanı çok örnekte etiketlemek, on altı alanı az örnekte etiketlemekten
istatistiksel olarak daha sağlam.** `kar_payi_orani` kampanyaların %16'sında
geçiyor; 60 örnekte ~10 kez görünür. Örnek sayısını düşürüp alan sayısını
korumak, her alanı tek haneli örnek sayısına mahkûm ederdi.

**Uyum bloğu neden 5:** ortak blok dört kişinin de aynı satırları etiketlemesi
demek — tek satır dört kat emek. 5 satır × 8 alan, uyum oranını hesaplamaya
yetecek kadar dolu hücre üretiyor ve kişi başı ~8 dakikaya mal oluyor.

Toplam: kişi başı ~90 dakikadan ~25 dakikaya.

## Sonuçları

**`metinsel_dogruluk` artık ölçülmüyor.** `eval/calistir.py` bu metriği
`0,000 ❌` yerine **`ölçülmedi (—)`** diye raporluyor; ölçülmemişi başarısız
göstermek, ölçmemekten kötüdür. `docs/SONUCLAR.md` ve sunumda bu boşluk açıkça
söylenir — 0,78 hedefi karşılanmadı değil, **ölçülemedi**, sebebi de yukarıda.

**Sorulmayan alan `null` olarak sete girmemeli.** `tools/altin_set.py`
içindeki okuma, CSV'de gerçekten bulunan sütunlarla sınırlandı
(`_etiket_sutunlari`). Aksi hâlde eksik sütun boş hücreye, boş hücre de
"bu bilgi metinde yok" iddiasına dönüşür ve sistem doğru değeri bulduğunda
haksız yere hata sayılırdı. Bu davranış testle korunuyor.

**Kopya denetimi yeniden hedeflendi.** `kopya_suphesi` serbest metin alanlarına
bakıyordu; o alanlar gidince sessizce ölecekti. Artık sekiz çekirdek alana
bakıyor, eşiği %90 değil **%100** (yapısal alanlarda birebir eşleşme meşrudur —
doğru etiketleyen iki kişi aynı sayıyı yazar; kusursuz örtüşme değildir) ve
yalnız en az birinin değer yazdığı hücreleri sayıyor.

**Kalibrasyon bloğu kaldırıldı.** Yalnız "ilk uyum bloğu kirlendi" diye vardı;
sıfırdan başlayınca dayanağı kalmadı.

## Değerlendirilen alternatifler

**16 alanı korumak, örneklemi 30'a düşürmek.** Reddedildi: seyrek alanlar
tek haneli örnek sayısına düşerdi, güven aralığı sunumda savunulamazdı.

**`kampanya_avantaji`'yi tutmak.** Metinsel doğruluk metriği kâğıt üzerinde
yaşardı ama birebir eşleşme yüzünden skoru yine ~0 çıkardı. Ekstra emek,
karşılığı yok.

**`eval`'i bulanık eşleşmeye geçirmek** (F1 / token örtüşmesi). Metinsel
alanları gerçekten ölçülebilir kılardı ve şemanın docstring'i zaten "alan bazlı
F1" diyor — yani uygulama ile niyet arasında bir açık var. Ama bu ayrı bir iş
ve kritik yolun üstünde. Şimdilik boşluk dürüstçe
raporlanıyor; metrik düzeltilirse alanlar geri eklenebilir.
