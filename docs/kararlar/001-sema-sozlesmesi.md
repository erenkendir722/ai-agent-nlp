# ADR 001 — Şema sözleşmesi önce donar

**Tarih:** 9 Ağustos 2026
**Durum:** Kabul edildi
**Sahip:** Eren

## Bağlam

Dört kişilik ekip, kişi başı günde 1-2 saat kapasiteyle çalışıyor (~180 kişi-saat).
Bu kapasitede en pahalı şey **bloke olmaktır**: Esra'nın arayüzü Samet'in
çıkarımını, Samet'in çıkarımı Görkem'in toplayıcısını beklerse, üç kişi aynı
anda boşta kalır ve o saatler geri gelmez.

## Seçenekler

1. **Modülleri sırayla geliştirmek.** Toplayıcı bitsin, sonra çıkarım, sonra arayüz.
   Doğal görünür ama seri bağımlılık yaratır; bir gecikme tüm zinciri kaydırır.
2. **Herkes kendi veri yapısını tanımlasın, sonda birleştirelim.** Entegrasyon
   maliyeti sona yığılır — tam da özellik dondurma tarihine.
3. **Şemayı en başta dondurup herkesi şemaya karşı çalıştırmak.**

## Karar

Seçenek 3. `src/schema.py` 9 Ağustos'ta v1.0.0 olarak donduruldu.

Herkes gerçek veri yerine şemaya karşı çalışır: Esra sahte `Kampanya` nesneleriyle
arayüzü kurar, Samet çıkarımı şemaya doldurur, Görkem toplayıcıyı `HamKayit`
üretecek şekilde yazar. Kimse kimseyi beklemez.

Şema değişikliği yasak değil, ama **sessiz değişiklik yasak**: takıma duyurulur,
ADR yazılır, sürüm numarası yükselir.

## Sonuç

- Paralel çalışma mümkün oldu; 9 Ağustos'ta dikey dilim uçtan uca çalıştı.
- Kanıt zinciri (`Alan` içinde kaynak + güven + yöntem) şemanın kendisine gömülü
  olduğu için, "kaynak göstermeyi sonra ekleriz" tuzağına düşmedik. Sonradan
  eklenemezdi — her katmanın onu taşıması gerekiyordu.
- Maliyet: şemayı ilk gün doğru tasarlamak ~2 saat aldı.
