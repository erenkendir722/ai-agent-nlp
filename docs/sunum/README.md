# Sunum — Svartal_Sunum.pdf

**9 sayfa** (TEKNOFEST kapağı + 8 içerik), 16:9 (1280×720 ·
13,333in × 7,5in), **açık tema**. Kaynak `sunum.html` + `stil.css`; PDF ondan üretilir,
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

## Tasarım nereden geliyor

Düzen, 28 Ağustos'ta beğenilen `TEKNOFEST_2026_SVARTAL_Final_Sunumu_Kusursuz.pdf`
şablonundan alındı: ince üst bant (marka çipi + alt başlık + bölüm rozeti),
beyaz kartlar, aşama rozetli boru hattı, **çubuğun içine yazılan değer**,
monospace veri satırları, altbilgide turuncu çerçeveli sayfa çipi.

**O PDF'in kaynağı yoktu** — yalnız çıktı dosyası vardı. Bu yüzden tasarım
burada yeniden kuruldu. Kazanç: `tests/test_sunum_sayilari.py`'deki **13 nöbetçi**
slayttaki her sayıyı ölçüm dosyasına bağlı tutmaya devam ediyor.

### O şablonda düzeltilen teknik yanlışlar

Tasarım alındı, **iddialar depoya karşı denetlendi.** Düzeltilenler:

| Şablonda yazıyordu | Gerçek |
|---|---|
| «LangGraph & Ajan Mimarisi», `@state_graph.node(...)` | **LangGraph kullanılmıyor** — `requirements.txt`'te de `src/`'de de yok. Protokol 30 satır |
| «Yerel LLM (Qwen 3.5 **GGUF**)» | GGUF yok. Çıkarım EVREN'de `Qwen/Qwen3.5-122B-A10B`, BF16 |
| Kanıt zincirinde «**SHA256** hash» | SHA256 yalnız *kod parmak izinde* (`depolama.kod_parmak_izi`), kayıt başına değil |
| `SELECT * FROM campaigns` | Tablo adı **`kampanyalar`** |
| Vakıf 142 · TOM 14 · «**FUPS**/Diğer» · Dünya Katılım yok | Gerçek dokuz banka: Ziraat 219 · Kuveyt Türk 213 · Albaraka 137 · TOM 123 · Emlak 110 · T.Finans 64 · Vakıf 49 · Dünya 45 · Hayat 19 |
| Ablasyonda «Tam Hiyerarşi %0.21» | Ablasyonun kendi değeri **%0,42**; %0,19 *eval*'den, başka koşu |
| «**Klasik Vektör RAG** %83.3 / %0.70» kolonu | O değerler ablasyonun «Yalnız dil modeli» kolu. **Vektör-RAG taban çizgisi hiç ölçülmedi** — kolon, ölçülmüş üç kolla değiştirildi |
| Grup başına «%100 Tam kapsam» | Kapsam **11,5× dengesiz**; şablonun kendi sonuç sayfası da bunu söylüyordu (kendi içinde çelişki) |

## Palet — ölçülerek seçildi

`dataviz` doğrulayıcısı, **açık** zemin, `--pairs all`:

| Rol | Hex | |
|---|---|---|
| **Mavi** | `#1B6FC4` | ablasyon çubukları — taban çizgisi kolları |
| **Turuncu** | `#E8622A` | marka · bizim yapılandırma |

**5/5 PASS** (CVD ΔE 24,0 protan · normal görüş ΔE 34,0).

**Durum renkleri ayrıdır ve tek başına kullanılmaz:** yeşil `#2E9E5B` ✓ ·
kırmızı `#D93B3B` ✕ · kehribar `#B4780E` —. Bu üçlü doğrulayıcıda CVD'de
**ayrışmıyor** (yeşil↔kırmızı ΔE 4,5 deutan); kırmızı-yeşil renk körü bir jüri
üyesi ayırt edemez. Bu yüzden **her durum çipi ikon + metin taşır.** İkonu kaldırma.

```bash
node scripts/validate_palette.js "<hex,...>" --mode light --pairs all
```

### Logo her sayfada

Üst bantta koyu marka çipi (mark + «SVARTAL»). `marka/svartal-logo.png`
**henüz yok**; yerinde vekil SVG duruyor. Gerçek dosya konunca her sayfadaki
`<use href="#marka"/>` yerine `<img src="marka/svartal-logo.png">` yazmak yeter —
yer ve boyut aynı.

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

| # | Sayfa | Konuşan |
|---|---|---|
| 01 | TEKNOFEST kapağı | — |
| 02 | Problem — dört ifade, manşet oran tuzağı | Eren |
| 03 | Kapsam — dört rakam, banka dağılımı, 16 alanlı kanıt zinciri | Görkem |
| 04 | **Mimari** — 5 katmanlı boru hattı + çekirdek ilke | Eren |
| 05 | Karşılaştırma — kural vs. model vs. SVARTAL (üçü de ölçülmüş) | Samet |
| 06 | **Ablasyon** — çubuklu tablo, dürüstlük kutusu | Samet |
| 07 | Asistan — cevap kartı + karar izi konsolu | Esra |
| 08 | Sonuçlar ve bilinen sınırlar | Eren |
| 09 | Kapanış · soru & cevap | — |

Madde 8 («tüm üyelerin görev tanımları sunumda olmalı») her sayfanın
altbilgisindeki konuşmacı adıyla karşılanıyor.

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
