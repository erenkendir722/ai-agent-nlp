# ADR 019 — Yeni kampanya keşfi: diff'in iki yönü ayrı tabana karşı çalışır

**Tarih:** 27 Ağustos 2026
**Durum:** kabul edildi
**Bağlam:** yeni kampanya keşfi
· devamı olduğu karar: [ADR 018](018-tetikleyici-dinleyici.md)

## Bağlam

ADR 018'deki tazelik dinleyicisi şu soruyu cevaplıyordu: *«elimizdeki 1.024
sayfa değişti mi?»* Ama asıl istenen soru bu değildi:

> **«Son çekimden bu yana YENİ kampanya çıktı mı? Elimizde hiç olmayan.»**

Dinleyici bunu **yapısal olarak göremez**: yalnız bildiği URL'leri yoklar,
envanterde olmayan bir kampanyanın adresi hiç ziyaret edilmez.

## Karar

Bankanın kampanya **listesi** yeniden keşfedilir (`kampanya_urlleri()`),
dönen URL kümesi karşılaştırılır. **Detay sayfası çekilmez** — tam toplamanın
pahalı kısmı odur.

**Diff'in iki yönü AYRI tabana karşı çalışır.** Bu dosyanın asıl kararı:

| Yön | Karşılaştırma tabanı | Güven |
|---|---|---|
| **YENİ** | `data/raw` envanteri | yüksek |
| **KALDIRILMIŞ** | **önceki KEŞİF koşusu** | yüksek |
| Envanterde olup listede yok | `data/raw` | düşük — yalnız bilgi |

## Neden — ÖLÇÜM 1: envanter kampanya detayından ibaret değil

Gerçek keşif koşuldu (27 Ağustos):

| Banka | Süre | Listede | Envanterde | YENİ | Envantere göre "kaldırılmış" |
|---|---|---|---|---|---|
| Hayat Finans (0212) | **9 sn** | 13 | 16 | **1** | 4 |
| Albaraka (0203) | **81 sn** | 48 | 136 | 0 | **88** |

Hayat Finans'ta **gerçek bir yeni kampanya bulundu**:
`hayatfinans.com.tr/kampanyalar/biz-kart-ile-okula-donus-kampanyasi`.

Ama Albaraka'nın 88'i **sahte**. Bakıldı: envanterdeki
`/tr/bireysel/finansmanlar/...` adresleri **ürün sayfaları**, kampanya detayı
değil; `kampanya_urlleri()` onları tasarımı gereği hiç döndürmüyor. Hayat
Finans'ın 4'ü de aynı türden (`/kampanyalar`, `/kartlar` — liste sayfaları).

Envantere karşı diff alınsaydı mekanizma her koşuda **88 sahte «kaldırıldı»**
üretirdi. Yanlış alarm, kaçırılan değişiklikten pahalıdır: her koşuda bağıran
bir uyarı okunmaz hâle gelir.

**YENİ yönü aynı kirlilikten etkilenmez:** envanterde fazladan URL bulunması
YENİ kümesini yalnız KÜÇÜLTÜR, şişirmez. Asıl hedef bu yüzden güvenle
raporlanabiliyor.

Bu, ADR 018'deki dersin aynısı: **karşılaştırma, karşılaştırılanı ÜRETEN yola
karşı yapılır.** Orada Selenium gövdesi ile `httpx` gövdesi karışmasın diye
taban kendi yolundan kurulmuştu.

## Neden — ÖLÇÜM 2: sitemap birincil kaynak olamaz

Ucuz kademe arandı. 8/9 banka `sitemap.xml` beyan ediyor; kapsama ölçüldü
(envanterdeki URL'lerin kaçı sitemap'te var):

| Banka | Kapsama | Banka | Kapsama |
|---|---|---|---|
| Hayat Finans | %100 | Albaraka | %43 |
| Emlak Katılım | %96 | Vakıf Katılım | %43 |
| Kuveyt Türk | %89 | Türkiye Finans | **%0** |
| | | Ziraat Katılım | **%0** |
| | | Dünya Katılım | **%0** (CMS sunucusu) |
| | | TOM Katılım | sitemap yok |

**Kısmi kapsama bu iş için yokluktan kötüdür.** %43 kapsayan bir sitemap'i
keşif kaynağı yapmak envanterin %57'sini «kaldırılmış» diye raporlardı.
Karar: keşif **Selenium** ile yapılır, sitemap kullanılmaz.

> «Denedik, olmadı» da bir bulgudur — ADR 014'ün (qdrant) ve ADR 018'in
> (`ETag`) aynı disiplini.

## URL normalizasyonu — kara liste, beyaz liste değil

İzleme parametreleri (`utm_*`, `gclid`, `fbclid` …) atılır; **bilinmeyen
parametre korunur.** Ters yönde («tanımadığımı at») çalışılsaydı
`?slug=bireysel` ve `?page=3` gibi SAYFAYI BELİRLEYEN parametreler silinir,
farklı sayfalar tek URL'e indirgenirdi.

Ayrıca: şema ve `www.` tekilleştirilir, sondaki `/` atılır, fragment atılır,
kalan parametreler sıralanır. **Yolun büyük/küçük harfine dokunulmaz** —
sunucu ayırt edebilir, birleştirmek veri kaybıdır.

## Sonuçlar

- `make kesif [banka=0203] [gorunur=1]` · arayüzde **Boru Hattı → 3 · Veri
  Denetimi → A · Yeni Kampanya Keşfi**
- Sekme 3 ikiye ayrıldı: **A** yeni kampanya keşfi, **B** veri tazeliği
  (değişmeden korundu). Sekme adı «Veri Tazeliği» → «Veri Denetimi».
- Yazılan tek yer `data/izleme/kesif.json` (`.gitignore`'da). `data/raw` ve
  `data/katilim.db` **dokunulmaz** — uçtan uca doğrulandı.
- Şemaya dokunulmadı, `SEMA_SURUMU` değişmedi.

## Dürüstlük sınırı

- Keşif kampanyayı **çekmez ve çıkarmaz.** «N yeni kampanya bulundu» der;
  toplamayı operatör başlatır.
- **«Kaldırılmış» ≠ «süresi geçmiş».** Arşive taşınmış ya da o turda
  kaçırılmış olabilir; arayüz bunu açıkça yazar.
- Keşif de bir ziyarettir: robots kapısı ve nezaket kuralı işler.
- İlk keşif taban çizgisi kurar, «kaldırılmış» iddia etmez.

## Reddedilen seçenekler

**Envantere karşı iki yönlü diff.** Ölçüm 1: 88 sahte kaldırıldı.

**Sitemap'i keşif kaynağı yapmak.** Ölçüm 2: kapsama %0–%100 arasında
oynuyor.

**Envanteri temizleyip `data/raw`'ı düzeltmek.** Donmuş veri; yayımlanan
ölçümler onun üzerinde koştu. Süzgeç diff sırasında uygulanır, dosyalar
değişmez.

**Değişeni otomatik toplamak.** Faz 2'ye bırakıldı: `topla()`'ya URL listesi
verebilmeyi gerektiriyor ve teslim gününde açılmamalı.
