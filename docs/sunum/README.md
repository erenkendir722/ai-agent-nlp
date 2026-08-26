# Sunum — Svartal_Sunum.pdf

**10 sayfa**, 16:9 (1280×720 · 13,333in × 7,5in). Kaynak `sunum.html` + `stil.css`;
PDF ondan üretilir, **elle düzenlenmez.**

```bash
make sunum          # sunum.html -> Svartal_Sunum.pdf
```

Font **Carlito** (SIL Open Font License) `fontlar/` içinde gömülü durur; makinede
kurulu olmasına gerek yok. Renkler `stil.css` başındaki değişkenlerden gelir:
mürekkep `#15141A`, krem `#F5F4F0`, turuncu `#E85D2A`, turkuaz `#2AA3AE`.

Chrome başka bir yerdeyse: `make sunum KROM="/yol/chrome"`.

## Sayfa düzeni ve konuşan

Sunum **4 dakika** (şartname madde 10). Her sayfanın altbilgisinde konuşanın adı yazar —
madde 8 «tüm üyelerin görev tanımları sunumda olmalı» maddesi böyle karşılanıyor,
ayrı bir «ekip» slaydı yok.

| # | Sayfa | Konuşan |
|---|---|---|
| 01 | Kapak — ad, iddia, sayılar, ekip | — |
| 02 | Problem — dağınık metin, dört ifade, manşet oran tuzağı | Eren |
| 03 | Sistem tek bakışta — beş katman, üç kullanım yüzeyi, teknoloji gerekçeleri | Eren |
| 04 | Veri — kapsam, toplama etiği, yayınlanan veri seti, dengesizlik | Görkem |
| 05 | Hibrit çıkarım — kural + model + uzlaştırıcı, kanıt zinciri | Samet |
| 06 | **Ajan mimarisi** — beş ajan, ajan izi, ajan tuzağı | Eren |
| 07 | **Ölçüm** — beş kollu ablasyon, altın set, dürüstlük bandı | Samet |
| 08 | Asistan — RAG, sayısal doğrulama kalkanı | Esra |
| 09 | Karşılaştırma ve müşteri profili — kriterler, kısıt çözme | Esra |
| 10 | Kurum içi çalışabilirlik, sonuçlar, bilinen sınırlar, kapanış | Eren |

## Anlatılmayan terim bırakmama kuralı

Jüri karma bir kurul; sunum bir uzman toplantısı değil. Şu terimler slaytta
**kutu içinde** açıklanıyor: `robots.txt` (04) · kanıt zinciri (03) ·
altın set (07) · makro-F1 (07) · RAG (08). Açıklanmayan terim kullanmıyoruz;
kullanılacaksa kutusu eklenir.

## Sayıların kaynağı

Slayttaki her sayı depodan gelir; hiçbiri elle yazılmaz.

| Sayı | Nereden |
|---|---|
| 1.024 kampanya · 9 banka · doluluk %25,8 | `make durum` · `docs/SONUCLAR.md` |
| Ablasyon tablosu (5 satır) | `data/ablasyon.json` — tek koşu, tek kod parmak izi (`make ablasyon`) |
| Makro-F1 ve %95 güven aralığı | `docs/SONUCLAR.md` (400 kez önyükleme) |
| Halüsinasyon · şema geçerliliği · kalkan 0/35 | `docs/SONUCLAR.md`, `eval/sorular.yaml` |
| Uygunluk %70,1 · zorunlu ürün %24,3 | `make uygunluk-goc --deneme` · `src/ajanlar/uygunluk.py` |
| Kapsam dengesizliği 13,6× | `docs/KAPSAM_RAPORU.md` (`make kapsam`) |
| 15.151 paragraf · 1024 boyut | `make durum` — RAG indeksi |
| Geçen test sayısı | `make test` |
| 89 paket · 0 kısıtlı lisans · 4 model teyitli | `docs/LISANSLAR.md` (`make lisanslar-teyit`) |
| Toplam maliyet tuzağı (2.033.129 / 2.028.925 TL) | `src.comparison.karsilastirma.toplam_maliyet` · `tests/test_muhakeme.py` |
| 31 soruluk asistan kümesi, doğruluk 1,00 | `make chatbot-test` |
| Madde 11 örneği 11/11 | `tests/test_kural.py::TestSartnameMadde11` |

**Sayı değişirse:** önce ilgili ölçümü yeniden koş, sonra `sunum.html` içindeki
karşılığını güncelle ve `make sunum` ile PDF'i yeniden üret. Bayat sayı, jüri
depoya baktığında en pahalı hatadır.

## Hâlâ eksik

- **PPTX sürümü** (şartname madde 6 PDF *ve* PPTX istiyor) — ES-13.
- **Demo videosu 5 dk** (madde 6) ve **sunum videosu 1 dk** (madde 10) — ES-17, ES-18.
