# Sprint 0 Raporu — 9 Ağustos 2026

Sıfırdan başlayıp uçtan uca çalışan bir sistem kuruldu. Bu doküman, ne
yapıldığını, yol boyunca nelerin bozuk çıktığını ve neyin hâlâ eksik olduğunu
kayıt altına alır. 24 Ağustos'ta dokümantasyon maddesi 8 (*"Karşılaşılan
problemler ve çözüm yaklaşımları"*) bu dosyadan derlenecek.

> **Sprint hedefi neydi:** 9 Ağustos akşamı, bir metin girip yapısal JSON çıktı
> alabilen ve bunu ekranda gösterebilen çalışan bir sistem olacak.
> **Sonuç:** Hedef aşıldı — sistem yalnız çalışmıyor, gerçek veriyle ölçülüyor.

---

## 1. Kapı kontrolü sonucu (9 Ağustos 22:00)

| # | Soru | Sonuç |
|---|---|---|
| 1 | Ollama şemaya uygun JSON üretiyor mu? | ✅ Evet |
| 2 | Toplayıcı en az 2 bankadan sayfa çekiyor mu? | ✅ Evet — **8 banka, 96 sayfa** |
| 3 | Streamlit tablo gösteriyor mu? | ✅ Evet — 3 sayfa, 0 hata |

Üçü de geçti; 10 Ağustos'ta teknoloji değişikliği gerekmiyor.

---

## 2. Ölçülen sonuçlar

`make eval` ile otomatik üretildi → [`SONUCLAR.md`](SONUCLAR.md)

| Metrik | Değer | Hedef | Durum |
|---|---|---|---|
| **Halüsinasyon oranı** | **%0,25** | ≤ %3 | ✅ |
| Şema geçerliliği | 1,00 | 1,00 | ✅ |
| Alan doluluğu | %25,7 | — | — |
| Ortalama güven | 0,78 | — | — |
| İşlenen kampanya | 96 | — | — |
| Banka | 8 | — | — |

**Yöntem dağılımı** (ablasyon tablosunun ham verisi):

| Yöntem | Alan sayısı |
|---|---|
| `llm` | 244 |
| `kural` | 139 |
| `hibrit` (iki katman uyuştu) | 11 |
| Çelişki | 14 |

**Kampanya türü dağılımı** (şartname 5.4 taksonomisi):
`diger` 37 · `yatirim_urunu` 15 · `finansman` 12 · `alisveris_puani` 10 ·
`konut_finansmani` 6 · `kart` 6 · `ihtiyac_finansmani` 5 · `tasit_finansmani` 3 ·
`yeni_musteri` 1

Kalite: 100 test geçiyor, `ruff` temiz, 72 bağımlılığın tamamı izin verici lisanslı.

---

## 3. Kurulan katmanlar

| Katman | Dosya | Ne yapar |
|---|---|---|
| Sözleşme | `src/schema.py` | Donmuş veri şeması (v1.0.0), kanıt zinciri gömülü |
| Ön işleme | `src/preprocessing/normalizasyon.py` | Türkçe normalizasyon |
| Toplama | `src/collector/toplayici.py` | Tek jenerik toplayıcı, robots.txt uyumlu _(26 Ağu'da Selenium kazıyıcılarıyla değiştirildi — bkz. §8 notu)_ |
| Çıkarım | `src/extraction/{kural,llm,uzlastirici}.py` | Hibrit çıkarım |
| Depolama | `src/depolama.py` | SQLite + SQLAlchemy |
| Karşılaştırma | `src/comparison/karsilastirma.py` | Deterministik, 5 kriter |
| Chatbot | `src/rag/chatbot.py` | Niyet yönlendirici + sayısal doğrulama kalkanı |
| API | `src/api/sunucu.py` | 3 uç nokta |
| Arayüz | `app/` | Streamlit 3 ekran |
| Değerlendirme | `eval/calistir.py`, `eval/lisanslar.py` | `make eval`, `make lisanslar` |

---

## 4. Şartname okumasından çıkan düzeltmeler

Şartname PDF'i 9 Ağustos öğleden sonra elimize geçti ve **üç varsayımı
düzeltti**. Ayrıntı: [`kararlar/004-sartname-bulgulari.md`](kararlar/004-sartname-bulgulari.md)

1. **8 kampanya türü tahminimiz yanlıştı.** Dört sınıf fazla, dört eksik, biri
   yanlış adlandırılmıştı. Şartname 5.4 listesi birebir benimsendi.
   → *Ders: taksonomi tahmin edilemez. Altın set etiketlemesine bu doğrulama
   yapılmadan başlanmaması kararı doğru çıktı; yoksa 100 örnek iki kez
   etiketlenecekti.*
2. **Terim sözlüğü şartnamede hazırmış** (5.5, beş resmî tanım). LLM istemine
   birebir kondu — jürinin kendi tanımlarıyla çalışan bir model, "terminolojiye
   uyum" kriterinde tartışmasız durumdadır.
3. **Chatbot cevap biçimi madde 11'de örneklenmiş.** Karşılaştırma cevabı o
   biçime getirildi: kriter kriter, "çünkü" gerekçeli.

**Teslim tarihi:** Şartname içinde bir tutarsızlık var (madde 9: 12.07.2026 /
Tablo 1: 27 Temmuz – 26 Ağustos). **Bu konu kapatıldı, önemi yok.** Plan
26 Ağustos'a göre yürüyor, hedef teslim 25 Ağustos 20:00.

---

## 5. Yol boyunca bulunan ve düzeltilen 6 gerçek hata

Bunlar dokümantasyon maddesi 8'in ham malzemesidir. Hepsi test altına alındı.

### 5.1 LLM boş JSON döndürüyordu
**Belirti:** `content` boş, `done_reason: length`, `eval_count: 1200`.
**Sebep:** Qwen3.5 bir düşünme modeli; üretim bütçesinin tamamını akıl yürütmeye
harcıyor, cevaba sıra gelmiyordu.
**Çözüm:** `think=False`. Kayıt başına süre ~3 dakikadan ~13 saniyeye indi.
`ollama` Python paketi 0.5+ olmalı (bu parametre o sürümle geldi).

### 5.2 5.000.000 TL "tahsis ücreti" olarak etiketlendi
**Belirti:** *"5.000.000 TL'ye kadar finansman. Dosya masrafı alınmaz."*
cümlelerinde 5 milyon TL tahsis ücreti sanıldı, finansman tutarı ise tamamen
kaçırıldı.
**Sebep:** Dışlayıcı sözcük kontrolü mesafeye duyarsızdı — pencerede "masraf"
geçtiği için `finansman_tutari_max` reddediliyor, aynı sayı `tahsis_ucreti`
kuralına takılıyordu.
**Çözüm:** Üç katmanlı düzeltme — (a) dışlayıcı sözcük ancak kapsayıcıdan
**daha yakınsa** reddeder, (b) ücret alanlarında bağlam sözcüğü değerle
**aynı cümlede** olmalı, (c) olumsuzlanmış ifadelerden ("alınmaz", "yok",
"ücretsiz") sayı çıkarılmaz.
**Test:** `test_tutar_tahsis_ucreti_ile_karistirilmaz`

### 5.3 Cümle penceresi sıfıra çöküyordu
**Belirti:** 5.2'nin düzeltmesinden sonra kural gerçek bir tahsis ücretini de
reddediyordu.
**Sebep:** `ayni_cumle` kısıtı `azami=0` ile çağrılıyordu; `azami` cümle
sınırının **arandığı yarıçap**, pencerenin kendisi değil. Sıfır verilince
pencere sayının kendisine çöküyor, hiçbir bağlam sözcüğü bulunamıyordu.
**Yani 5.2'nin "düzelmesi" yanlış sebepten olmuştu** — kural her şeyi
reddediyordu, doğru olanı da.
**Nasıl yakalandı:** Yalnız "reddet" davranışını değil, **karşı kontrolü** de
test eden bir vaka yazıldığı için (`test_gercek_tahsis_ucreti_yakalanir`).
→ *Ders: bir kısıtı test ederken sadece "reddediyor mu" diye bakmak yetmez;
"doğru olanı hâlâ kabul ediyor mu" da sorulmalı.*

### 5.4 Halüsinasyon denetimi kendi metriğini bozuyordu
**Belirti:** 11 alan "ham metinde doğrulanamadı" diye işaretlendi.
**Sebep:** Denetim, `kampanya_turu` gibi **sınıflandırma etiketlerini**
("konut_finansmani") ve `kampanya_avantaji` gibi **meşru özetleri** de metinde
birebir arıyordu. İkisi de metinde geçmez.
**Neden önemli:** Halüsinasyon oranı puanlanan bir metrik. Yanlış sayım, kendi
sonucumuzu olduğundan kötü gösteriyordu.
**Çözüm:** Üç alan sınıfına üç ölçüt — sayısal/tarihsel alanlar birebir
doğrulanır; sınıflandırma etiketleri hiç aranmaz (enum kısıtı zaten garanti
ediyor); serbest metin özetlerinde **içindeki sayılar** aranır.
**Sonuç:** 11 yanlış pozitif → 0. Gerçek halüsinasyon oranı %0,25.

### 5.5 Doğrulama kalkanı geçerli bir cevabı engelliyordu
**Belirti:** *"Albaraka mı daha avantajlı, Kuveyt Türk mü?"* sorusuna cevap
verilmedi. Reddedilen sayılar: `40, 25, 20, 15, 0.625`.
**Sebep:** Bunlar veri değil, **sistemin kendi açıklaması** — skor ağırlıkları
(%40/%25/%20/%15) ve hesaplanan skor (0,625). Kalkan cevaptaki her sayıyı veri
iddiası sanıyordu.
**Çözüm:** Kalkanı gevşetmek yanlış olurdu — asıl iş onun sıkı kalması. Doğru
çözüm denetlenecek metni doğru seçmek: `Cevap.dogrulanacak_metin` alanı eklendi,
kalkan yalnız veri iddiası içeren bölümü denetliyor.
**Test:** `test_sistem_aciklamasi_veri_iddiasi_sayilmaz` + karşı kontrol
`test_kalkan_hala_uydurma_orani_yakaliyor`
→ *Bu hata demo sırasında patlardı.*

### 5.6 Türkçe ünlü uyumu chatbot'u yanlış yönlendiriyordu
**Belirti:** *"Kuveyt Türk **mü** daha avantajlı?"* sorusu karşılaştırma değil,
koşul sorgusu sayılıyordu.
**Sebep:** Yönlendirici ipuçlarında yalnız `"mi daha"` vardı. Türkçe soru eki
dört biçimlidir: mi/mı/mu/mü.
**Çözüm:** `arama_anahtari` normalizasyonu ı→i, ü→u yaptığı için iki varyant
yeter: `"mi daha"` ve `"mu daha"`.

### Ayrıca: `50.000TL` (boşluksuz) yakalanmıyordu
`\bTL\b` deseni rakamla harf arasında sözcük sınırı görmüyor. "Önünde harf
olmasın" koşuluyla değiştirildi; `HTL`/`ATL` gibi kısaltmalar hâlâ eşleşmiyor.

---

## 6. Ölçülen kapasite uyarısı — planı etkiler

`make extract` çalışırken Streamlit açık bırakılırsa 8 GB makinede sistem takasa
düşüyor:

| Durum | Kayıt başına | 96 kayıt | 300 kayıt (Sprint 1 hedefi) |
|---|---|---|---|
| Streamlit açıkken | ~2,5 dk | **~4 saat** | ~12 saat |
| Streamlit kapalıyken | **13,2 sn** | ~21 dk | **~65 dk** |

Ölçüm sırasında 1,19 milyon pageout, boş bellek %15. Sebep model değil, bellek
çakışması.

**Kural: toplu çıkarım sırasında arayüzü kapatın, ya da 3090'da koşturun.**

---

## 7. Bilinen eksikler ve veri kalitesi sorunları

| # | Konu | Etki | Kime |
|---|---|---|---|
| E1 | **Docker yolu test edilmedi** — bu makinede Docker kurulu değil | On-prem iddiasının merkezi | Eren |
| E2 | **Altın veri seti yok** → %30'luk kriterin doğruluk metrikleri hesaplanamıyor | Kritik | Hepsi |
| E3 | `kampanya_turu` = `diger` oranı **%38** (37/96) | Sınıflandırma zayıf | Samet |
| E4 | `kar_payi_orani` doluluğu yalnız **%28** | En önemli alan | Samet |
| E5 | `finansman_tutari_max` bazı kayıtlarda saçma (ör. 1000 TL) | Yanlış veri | Samet |
| E6 | T.O.M. Katılım'da kampanya sayfası bulunamadı | 1 banka eksik | Görkem |
| E7 | 3 bankanın EFT kodu doğrulanmadı (`kod_dogrulandi: false`) | Yayın kalitesi | Görkem |
| E8 | Gömme/RAG yok — koşul soruları anahtar sözcükle çalışıyor | Chatbot kalitesi | Samet |
| E9 | Dayanıklılık seti yok | %30 kriterinin bir parçası | Samet |
| E10 | Ablasyon tablosu boş | Sunumun en güçlü slaydı | Samet |
| E11 | Video ve sunum yok | Zorunlu teslimat | Esra |
| E12 | GitHub topic/etiket eksik | Değerlendirmeye alınmama riski | Eren |

Not: E3–E5 gerçek veriyle ölçülmüş sorunlardır, tahmin değil. Kampanya
sayfalarının çoğu kâr payı oranını yazmıyor (başvuru ekranında oluyor); bu
veri setinin gerçek bir özelliğidir ve `Belirtilmemiş` olarak raporlanır —
uydurulmaz.

---

## 8. Bilinçli olarak yapılmayanlar

Bunlar eksik değil, **kapsam kararıdır**. Dokümantasyonda savunulacak.

| Yapılmayan | Yerine | Gerekçe |
|---|---|---|
| React + Vite arayüz | Streamlit | Kurum içi dağıtımda tek runtime, Node bağımlılığı yok |
| PostgreSQL + pgvector | SQLite + numpy | SQLAlchemy sayesinde geçiş config değişikliği |
| BERT ince ayarı | LLM zero-shot | Aynı kod yolu, ölçülebilir |
| Banka başına özel scraper | Jenerik toplayıcı + YAML | Yeni banka = 8 satır YAML |
| Playwright / JS render | Statik HTML + manuel yedek | Şartname manuel toplamaya izin veriyor |
| Ayrı mikroservis mimarisi | Python paketi + ince API | Entegre edilebilirlik kanıtı yeterli |

> **26 Ağustos 2026 — bu tablonun iki satırı geri alındı.** «Banka başına özel
> scraper» ve «JS render» kalemleri kapsam dışı bırakılmıştı; ölçüm bu kararı
> bozdu. Katılım bankalarının kampanya listeleri JavaScript ile render edilip
> «daha fazla yükle» butonuyla sayfalanıyor, yani statik HTML yolu kartların
> çoğunu hiç görmüyor. `data/raw` altındaki 1.024 kaydı fiilen üreten şey
> Selenium kazıyıcılarıydı; kod ise hâlâ jenerik toplayıcıyı gösteriyordu.
> Kod veriyi üreten yola taşındı: `src/collector/kaziyicilar/`, dokuz sınıf.
> Banka başına değişen tek şey URL keşfi; gezme, robots kapısı, nezaket ve
> gövde ayıklama hâlâ ortak taban sınıfta tek. Ayrıntı:
> [`docs/VERI_METODOLOJISI.md`](VERI_METODOLOJISI.md) §2.

---

## 9. Sonraki adım

Görev dağılımı ve tikli takip: [`../GOREVLER.md`](../GOREVLER.md)
