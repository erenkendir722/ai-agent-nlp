# Sunum — Svartal_Sunum.pdf

**7 sayfa**, 16:9 (1280×720 · 13,333in × 7,5in). Kaynak `sunum.html` + `stil.css`;
PDF ondan üretilir, **elle düzenlenmez.**

```bash
make sunum          # sunum.html -> Svartal_Sunum.pdf
make sunum-metni    # slayt metin dökümü -> sunum_icerik.txt
```

Chrome başka bir yerdeyse: `make sunum KROM="/yol/chrome"`.

---

## Arka plan TEKNOFEST'in resmî şablonundan gelir

`arkaplan/TEKNOFEST_sablon.pptx` yarışmanın verdiği şablondur. İçinde **iki
slayt** var ve ikisi de tek bir tam sayfa görselden ibaret: yer tutucu yok,
metin kutusu yok, tema rengi yok. Yani şablon bir tasarım değil, iki arka plan:

| Dosya | Nereden | Nerede kullanılıyor |
|---|---|---|
| `arkaplan/kapak.jpg` | şablonun 1. slaydı | PDF'in 1. sayfası — **üstüne hiçbir şey yazılmaz** |
| `arkaplan/icerik.jpg` | şablonun 2. slaydı | 6 içerik sayfasının tamamı |

Şablonun slayt boyutu 12192000×6858000 EMU = 13,333in × 7,5in — bu deponun
`@page` boyutuyla zaten aynıydı, dönüşüm gerekmedi. Kapak görselinin yerleşimi
(`off -1,0` · `ext 12499547×7030995`) `stil.css`'te `--kapak-en/--kapak-boy`
olarak birebir kopyalandı; şablonun kendi kırpmasını korur.

**Kapak görselinde boşluk yok** — logo, başlık, 3B görsel ve bakanlık logoları
tüm alanı dolduruyor. Bu yüzden «SVARTAL» kimliği kapağa değil, **01. içerik
sayfasına** konuldu.

### Güvenli alan — uydurma değil, ölçüm

`icerik.jpg` piksel piksel ölçüldü (1280×720 ölçeğinde):

```
beyaz kart      : x 27 → 1252   ·   y 33 → 686
alt-orta çentik : y≈550'den aşağıda x 460 → 830 arası 3B görsel dolu
                  (x=700'de beyaz y=607'de bitiyor)
```

Bu yüzden içerik `.icerik` kutusuna hapsedilir (x 68 → 1212, y 56 → 544) ve
**altbilgi 3B görselin iki yanına** konur: konuşan solda, sayfa numarası sağda.
Çentiğin üstünden geçen bir kutu beyaz kartın dışına taşar ve uzay zeminin
üstünde okunmaz hâle gelir.

**Taşma gözle denetlenmez, ölçülür.** Yöntem: her sayfa Chrome ile 1280×720
PNG'ye alınır, **boş bir `.sayfa`** referans olarak aynı şekilde çizilir, ikisinin
farkı «bizim koyduğumuz içerik» maskesini verir; o maskenin beyaz kart maskesi
dışına düşen pikseli **sıfır olmalıdır.** Bu denetim 02. sayfada gerçek bir
taşma yakaladı (166 px, sol kartın köşesi çentiğe giriyordu).

### Renkler de şablondan örneklendi

| | | |
|---|---|---|
| Kırmızı | `#CA0703` | iki arka plan görselindeki en sık kırmızı ton |
| Lacivert | `#1F406B` | aynı görsellerin uzay zemini |
| Mürekkep | `#17181C` | metin |

Önceki turuncu (`#E85D2A`) / turkuaz kimliği şablonun kırmızısının yanında
bulanık duruyordu; vurgu rengi şablonunkiyle aynı kırmızıya çekildi.

Font **Carlito** (SIL Open Font License) `fontlar/` içinde gömülü durur;
makinede kurulu olmasına gerek yok.

---

## Sayfa düzeni ve konuşan

Sunum **4 dakika** (şartname madde 10). Her sayfanın altbilgisinde konuşanın adı
yazar — madde 8 «tüm üyelerin görev tanımları sunumda olmalı» maddesi böyle
karşılanıyor, ayrı bir «ekip» slaydı yok. 01. sayfada dördünün rolü de yazılı.

| # | Sayfa | Konuşan |
|---|---|---|
| — | TEKNOFEST kapağı (şablonun kendi slaydı) | — |
| 01 | SVARTAL — iddia, sayılar, ekip ve roller | — |
| 02 | Problem ve sistemin cevabı — beş katman, manşet oran tuzağı, üç kullanım yüzeyi | Eren |
| 03 | Veri ve hibrit çıkarım — kapsam, toplama etiği, kanıt zinciri | Görkem · Samet |
| 04 | **Ajan mimarisi ve ölçüm** — beş ajan, ablasyon, dürüstlük bandı | Samet |
| 05 | Asistan, karşılaştırma ve müşteri profili — kalkan, kısıt çözme | Esra |
| 06 | Kurum içi çalışabilirlik, sonuçlar, bilinen sınırlar, kapanış | Eren |

## Anlatılmayan terim bırakmama kuralı

Jüri karma bir kurul; sunum bir uzman toplantısı değil. Şu terimler slaytta
**kutu içinde** açıklanıyor: kanıt zinciri (02) · `robots.txt` (03) ·
altın set (04) · makro-F1 (04) · RAG (05). Açıklanmayan terim kullanmıyoruz;
kullanılacaksa kutusu eklenir.

## Sayıların kaynağı

Slayttaki her sayı depodan gelir; hiçbiri elle yazılmaz.

| Sayı | Nereden |
|---|---|
| 734 işlenmiş kampanya · 9 banka | `docs/SONUCLAR.md` · `src.depolama.tum_kayitlar` |
| 12.391 paragraf · 1024 boyut | `make durum` — RAG indeksi (`data/vektor_indeksi.npz`) |
| Ablasyon tablosu (5 satır) · 1.024 ham kayıt | `data/ablasyon.json` — tek koşu, tek kod parmak izi (`make ablasyon`) |
| Makro-F1 ve %95 güven aralığı | `docs/SONUCLAR.md` (400 kez önyükleme) |
| Halüsinasyon · şema geçerliliği · kalkan 0/35 | `docs/SONUCLAR.md`, `eval/sorular.yaml` |
| Uygunluk %70,1 · zorunlu ürün %24,3 | `make uygunluk-goc --deneme` · `src/ajanlar/uygunluk.py` |
| Kâr payı doluluğu %19 · «diğer» %37 · dengesizlik 11,4× | canlı veritabanı — `TestSinirlarPaneli` denetliyor |
| Geçen test sayısı | `make test` |
| 89 paket · 0 kısıtlı lisans · 4 model teyitli | `docs/LISANSLAR.md` (`make lisanslar-teyit`) |
| Toplam maliyet tuzağı (2.033.129 / 2.028.925 TL) | `src.comparison.karsilastirma.toplam_maliyet` · `tests/test_muhakeme.py` |
| 31 soruluk asistan kümesi, doğruluk 1,00 | `make chatbot-test` |
| Madde 11 örneği 11/11 | `tests/test_kural.py::TestSartnameMadde11` |

**Sayı değişirse:** önce ilgili ölçümü yeniden koş, sonra `sunum.html` içindeki
karşılığını güncelle ve `make sunum` ile PDF'i yeniden üret. Bayat sayı, jüri
depoya baktığında en pahalı hatadır. Nöbetçi: `tests/test_sunum_sayilari.py`.

## Hâlâ eksik

- **`data-sayi="test"` teyit edilmedi.** 27 Ağustos'ta bu makinede
  `from lxml import etree` **Windows Uygulama Denetimi ilkesiyle engellendi**;
  pytest 5 modülü toplayamadığı için sayım 1456'da kaldı (gerçek sayı daha
  yüksek). Slayttaki 1604 rakamı **bu makinede doğrulanamadı** —
  `make test`'in koştuğu bir makinede `pytest tests/test_sunum_sayilari.py`
  gerçek sayıyı söyleyip slaytı düzelttirecek.
- **PPTX sürümü** (şartname madde 6 PDF *ve* PPTX istiyor) — ES-13.
- **Demo videosu 5 dk** (madde 6) ve **sunum videosu 1 dk** (madde 10) — ES-17, ES-18.
- `docs/KAPSAM_RAPORU.md` 1.024 kayıtlık korpustan üretilmiş (11,9×); canlı
  veritabanı 734 kayıt ve 11,4× diyor. Slayt canlı değeri kullanıyor,
  raporun `make kapsam` ile tazelenmesi gerekiyor.
