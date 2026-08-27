# Sunum — Svartal_Sunum.pdf

**8 sayfa** (TEKNOFEST kapağı + 7 içerik), 16:9 (1280×720 ·
13,333in × 7,5in). Kaynak `sunum.html` + `stil.css`; PDF ondan üretilir,
**elle düzenlenmez.** Konuşma metni ayrı: [`KONUSMA_METNI.md`](KONUSMA_METNI.md).

```bash
make sunum          # sunum.html -> Svartal_Sunum.pdf
make sunum-metni    # slayt metin dökümü -> sunum_icerik.txt
```

Chrome başka bir yerdeyse: `make sunum KROM="/yol/chrome"`.

---

## Şablon: yalnız KAPAK zorunlu

`arkaplan/TEKNOFEST_sablon.pptx` yarışmanın verdiği şablon. İçinde iki slayt var
ve ikisi de tek bir tam sayfa görselden ibaret — yer tutucu, metin kutusu, tema
rengi yok.

**27 Ağustos'ta netleşti: içerik arka planının kullanımı ZORUNLU DEĞİL.**
Bu yüzden yalnız kapak şablonun kendi görselidir (`arkaplan/kapak.jpg`, PPTX'teki
kırpma birebir korunur); kalan on bir sayfa bize ait ve **tam tuval** kullanılır.

Daha önce düzen o arka planın beyaz kartına ve alt-orta çentiğine göre kısılmıştı
(x 27–1252 · y 33–686, çentik y≈550'den aşağıda x 460–830). O kısıt kalktı;
`arkaplan/icerik.jpg` artık kullanılmıyor ama şablonun kaydı olarak duruyor.

## Koyu tema — üç vurgu, ölçülerek seçildi

SVARTAL logosu siyah kare + turuncu «S» + mürekkep kelime işareti. Palet
o üçlüden başladı, sonra `dataviz` doğrulayıcısından geçirildi
(koyu zemin, `--pairs all`):

| Rol | Hex | |
|---|---|---|
| Zemin | `#15141A` | |
| Metin | `#F5F4F0` | |
| **Turuncu** | `#E85D2A` | marka · problem ve sonuç bölümleri |
| **Turkuaz** | `#2AA3AE` | kanıt ve ölçüm bölümleri |
| **Mor-mavi** | `#8A7BE0` | sistem/mimari bölümü |

**5/5 PASS** — lightness bandı, kroma tabanı, CVD ayrımı (en kötü çift
ΔE 9,6 deutan), normal görüş tabanı (ΔE 17,2), zemin kontrastı.

**Elenenler ve nedeni** — hepsi denendi, hiçbiri geçemedi:

| Renk | Neden elendi |
|---|---|
| sarı-yeşil `#7FA83A` | turuncuyla deuteranopide **ΔE 2,5** — kırmızı-yeşil renk körü bir jüri üyesi ayırt edemez |
| yeşil `#21C08A` | lightness 0,718; koyu zeminde bandın dışında |
| mor `#A96BC9` + mavi `#6E8CE8` | birbirine ΔE 4,8 (deutan) |
| nötr gri `#7A8494` | kroma tabanının altında, gri okuyor |

Yeşil özellikle istendi ve özellikle bu yüzden kullanılamadı — turuncuyla
çakışması ölçüldü. Renk eklemeden önce:

```bash
node scripts/validate_palette.js "<hex,...>" --mode dark --pairs all
```

### Bölüm rengi bir yapı işaretidir

Her sayfanın üst şeridi bölümün rengini taşır: **problem turuncu → sistem
mor-mavi → kanıt/ölçüm turkuaz → sonuç turuncu.** Jüri renk değişiminden
konunun değiştiğini anlar; renk süs değil.

### Logo her sayfada

Sol üstte mark + «SVARTAL» kelime işareti. Yalnız mark yetmez — jüri markayı
ilk kez görüyor, tanıması için adın yanında durması gerekir.

`marka/svartal-logo.png` **henüz yok**; yerinde vekil bir SVG duruyor
(krem kare + turuncu «S», koyu zemin için ters çevrilmiş). Gerçek dosya
konunca her sayfadaki `<svg><use href="#marka"/></svg>` yerine
`<img src="marka/svartal-logo.png">` yazmak yeter — yer ve boyut aynı.

## Metin bütçesi — ölçülür, tahmin edilmez

4 dakikada konuşulabilecek kelime **~520**. Slayttaki metin bunun katıysa jüri ya
okur ya dinler, ikisini birden yapamaz.

| Sürüm | Kelime | Konuşmaya oranı |
|---|---|---|
| 26 Ağustos (10 sayfa) | 1.882 | **3,6×** |
| 27 Ağustos, şablonlu (9+3 sayfa) | 1.029 | 2,0× |
| **Şimdiki (7 içerik sayfası)** | **865** | **1,7×** |

Slaytta görünmeyen kanıtlar **silinmedi, depoda duruyor.** Hangi sorunun
nereden cevaplanacağı `KONUSMA_METNI.md` sonunda tabloyla yazılı.

## Taşma denetimi — gözle değil, ölçerek

Her sayfa Chrome ile 1280×720 PNG'ye alınır; sayfanın **alt ve sağ 8 pikselinde**
zemin dışı renk varsa içerik kenara dayanmış demektir. Kapak hariç (tam sayfa
görsel) hepsi sıfır olmalı. Bu denetim 27 Ağustos'ta şablonlu sürümde gerçek bir
taşma yakaladı (166 px, sol kartın köşesi 3B görselin çentiğine giriyordu).

## Sayfa düzeni ve konuşan

Sunum **4 dakika** (şartname madde 10). Her sayfanın altbilgisinde konuşanın adı
yazar — madde 8 «tüm üyelerin görev tanımları sunumda olmalı» maddesi böyle
karşılanıyor, ayrı bir «ekip» slaydı yok. 01. sayfada dördünün rolü de yazılı.

| # | Sayfa | Bölüm rengi | Konuşan |
|---|---|---|---|
| 01 | TEKNOFEST kapağı | — | — |
| 02 | SVARTAL — iddia, beş rakam, ekip | turuncu | Eren |
| 03 | Problem — dört ifade, manşet oran tuzağı | turuncu | Eren |
| 04 | **Mimari** — altı aşamalı akış + kanıt zinciri şeridi | mor-mavi | Eren |
| 05 | Kanıt zinciri ve beş ajan | mor-mavi | Samet + Eren |
| 06 | **Ölçüm** — ablasyon (çubuklu tablo), dürüstlük | turkuaz | Samet |
| 07 | Asistan — gerçek cevap, sayısal doğrulama kalkanı | turkuaz | Esra |
| 08 | Sonuç, bilinen sınırlar, kapanış | turuncu | Eren |

Madde 8 («tüm üyelerin görev tanımları sunumda olmalı») 02. sayfanın
altbilgisinde dördünün rolüyle karşılanıyor; ayrı ekip slaydı yok.

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
