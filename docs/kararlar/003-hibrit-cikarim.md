# ADR 003 — Hibrit çıkarım: kural + LLM, çelişkide kural kazanır

**Tarih:** 9 Ağustos 2026
**Durum:** Kabul edildi
**Sahip:** Samet

## Bağlam

Kampanya metinlerinden alan çıkarımı için üç yol var. Jüri "neden sadece LLM
kullanmadınız?" diye soracak; cevabın ölçülmüş olması gerekiyor.

## Seçenekler

1. **Yalnız kural (regex).** Kesin ama kırılgan. Yalnız öngördüğümüz kalıpları
   yakalar; "avantajlı kâr payı fırsatı" gibi dolaylı ifadelerde hiçbir şey bulmaz.
   Halüsinasyon oranı yapısal olarak %0.
2. **Yalnız LLM.** Esnek ama akla yatkın yanlış üretebilir. Bankacılıkta yanlış
   oran, eksik orandan çok daha pahalıdır.
3. **Hibrit.**

## Karar

Seçenek 3, şu iş bölümüyle:

| Alan sınıfı | Birincil katman | Gerekçe |
|---|---|---|
| Sayısal (oran, tutar, vade, ücret) | **Kural** | Kesinlik kapsamdan önce gelir |
| Tarih | Kural | Biçim varyantları sonlu ve bilinir |
| Sınıflandırma (tür, hedef kitle) | **LLM** | Anlamsal karar, regex'in işi değil |
| Serbest metin (avantaj, koşullar) | **LLM** | Özetleme gerekir |

**Çelişkide kural kazanır** (sayısal alanlarda). Kural katmanı bir değeri ancak
doğru bağlam sözcüğünün yakınında, aynı cümlede ve olumsuzlanmamış bir ifadede
bulursa üretir — yanılma biçimi öngörülebilirdir. LLM'in yanılma biçimi değildir.

İki katman **aynı** değeri bulursa `yontem="hibrit"` işaretlenir ve güven
yükseltilir: bağımsız iki yöntemin uzlaşması, güvenin en güçlü kanıtıdır.

## Ölçüm yükümlülüğü

Bu karar iddia olarak kalamaz. Üç yapılandırma **aynı kod yolundan** koşulur —
yalnız katman bayrakları değişir (`--yalniz-kural`, `--yalniz-llm`):

```bash
make extract-kural && make eval
make extract-llm   && make eval
make extract       && make eval
```

Ayrı kod yolu yazmak ölçümü karşılaştırılamaz hâle getirirdi. Ablasyon tablosu
altın set hazır olduğunda (16 Ağustos sonrası) doldurulacak.

## Sonuç (9 Ağustos, altın set öncesi ilk gözlem)

Tohum veride kural katmanı 5 sayısal alanı yakaladı, LLM 2 sınıflandırma alanını.
Örtüşme sıfır — yani iki katman şu an **birbirini tamamlıyor, tekrar etmiyor**.

Bu, ablasyon tablosunun güçlü çıkacağının erken işareti: hiçbir katman tek başına
alanların yarısından fazlasını üretemiyor. Ancak `hibrit` sayısının sıfır olması,
"iki katmanın birbirini doğrulaması" iddiasının şu an ölçülemediği anlamına da
geliyor — LLM'in sayısal alanlarda da üretim yapması sağlanmalı ki uzlaşma
oranı ölçülebilsin.

**Yapılacak (Samet, Sprint 1):** LLM istemini sayısal alanlarda daha üretken
hâle getir, sonra kural/LLM uzlaşma oranını ölç. Uzlaşma oranı güven skorunun
kalibrasyonu için de gerekli.
