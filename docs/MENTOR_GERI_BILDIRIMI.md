# Mentör Geri Bildirimi — Karşılığı ve Durumu

_26 Ağustos 2026 · derleyen: Eren_

> Mentör hocamızla yapılan görüşmede sekiz başlık açıldı. Bu dosya her başlığın
> **bizdeki karşılığını** ve **kanıt dosyasını** gösterir. Amaç savunma değil
> envanter: hangi öneri zaten karşılanmış, hangisi bugün yapıldı, hangisi
> bilerek yapılmadı.
>
> Kural: *"var"* diyorsak satırında **çalıştırılabilir bir kanıt** olacak.
> Yoksa *"yok"* yazar.

**Teslim penceresi:** bugün 26 Ağustos, teslim 27 Ağustos. Öneriler bu pencereye
göre ayıklandı; ertelenenler gerekçesiyle yazılı.

---

## Özet tablo

| # | Mentör önerisi | Durum | Kanıt |
|---|---|---|---|
| 1 | Multi-agent mimarisi belirli bir desene dayanmalı | ✅ **vardı** (ADR 005, hiyerarşik) | [`kararlar/005`](kararlar/005-ajan-mimarisi.md) |
| 2 | Ajan sayısının gerekçelendirilmesi + orkestrasyon diyagramı | ✅ **bugün eklendi** | [`MIMARI.md`](MIMARI.md) §3.5 |
| 3 | Tetikleyici / dinleyici mantığı, periyodik güncelleme | ✅ **dinleyici kodda** (27 Ağu) · tetikleyici tanımlı, bilerek kurulu değil | [`kararlar/018-tetikleyici-dinleyici.md`](kararlar/018-tetikleyici-dinleyici.md) |
| 4 | LLM'e doğrudan DB analizi yaptırma; TAG/DAG, Text-to-SQL, Vanna.ai | ✅ **zaten yapmıyoruz** — bilinçli karar | [`JURI_PROVASI.md`](JURI_PROVASI.md) §9 |
| 5 | Saf RAG yerine hibrit (Regex + LLM) | ✅ **vardı ve ölçüldü** | [`kararlar/003`](kararlar/003-hibrit-cikarim.md) · `data/ablasyon.json` |
| 6 | Karar destek: vade/tutar karşılaştırması, segment bazlı alternatif | ⬆️ **bugün genişletildi** | Karşılaştırma sayfası · [`karsilastirma.py`](../src/comparison/karsilastirma.py) |
| 7 | EDA grafikleri / dashboard | ✅ **vardı** — demoda gösterilmiyordu | `app/Genel_Bakis.py` |
| 8 | Arayüzdeki metrik yazım hataları (halüsinasyon %40) | 🔴 **gerçekti, düzeltildi** | `tests/test_ui_utils.py` |
| 9 | Hackathon / canlı görev hazırlığı | ⏭️ teslim sonrası | — |

---

## 1–2. Ajan mimarisi ve orkestrasyon diyagramı

**Mimari zaten hiyerarşikti**, eksik olan tek şey **şemaydı**.
[ADR 005](kararlar/005-ajan-mimarisi.md) (14 Ağustos) hiyerarşiye geçişi,
fonksiyonel ayrımı ve hazır ajan çatısı kullanmama gerekçesini yazıyor.

**26 Ağustos'ta eklenen:** [`MIMARI.md`](MIMARI.md) §3.5 altına orkestrasyon
şeması. Şema iki bağlamı ayırıyor — mentörün "alt-ajanlar / hiyerarşi" sorusunun
cevabı bu ayrım:

- **Çıkarım zamanı** (çevrimdışı, `make extract`): sürücü `boru_hatti.py` ve
  **o bir ajan değildir**; eleştirmen, yüklem ve uygunluk ajanları oraya kanca
  olarak takılır.
- **Sorgu zamanı** (çevrimiçi): kök ajan **orkestratördür**; niyeti çözer,
  muhakeme ajanına ya da chatbot koluna yönlendirir, izleri toplar.

Bu ayrımı yapmak "her şey ajandır" bulanıklığını önlüyor.

### Ajan sayısının gerekçesi

Beş ajanın her biri **tek bir soruya** bakar:

| Ajan | Sorusu | LLM |
|---|---|---|
| Eleştirmen | bu değerin kanıtı var mı? | ✗ |
| Yüklem | bu sayı doğru alana mı ait? | ✓ |
| Uygunluk | bu kampanya kime açık? | ✗ |
| Muhakeme | bu müşteriye uyuyor mu? | ✗ |
| Orkestratör | bu soru kime gider? | ✗ |

**Beşten dördü dil modeli kullanmaz.** Aritmetik ve kısıt çözümü kasten modele
verilmedi. Ajan katkısı iddia değil ölçüm: eleştirmen kapatılınca halüsinasyon
**%0,39 → %0,51** (`data/ablasyon.json`), yüklem eklenince makro-F1
**0,795 → 0,827**.

> ⚠️ **Bugün bulunan tutarsızlık:** `MIMARI.md` ajan tablosu beş ajanın beşine
> birden "LLM ✗" koymuştu, oysa `YuklemAjani.llm_kullanir = True`. Belge ile kod
> ayrışmıştı. Düzeltildi ve `tests/test_mimari_belgesi.py` ile koda bağlandı —
> bir ajanın bayrağı değişirse test kırılır.

---

## 3. Tetikleyici ve dinleyici — dinleyici var, tetikleyici bilerek kurulu değil

**Yapıldı (27 Ağustos).** `src/izleme/` altında iki parça:

- **Dinleyici** (`dinleyici.py`) — kodda ve koşuyor. Koşullu GET
  (`ETag`/`Last-Modified`), olmazsa içerik özeti (sha256). `make tazelik` ya da
  arayüzde **Boru Hattı → 3 · Veri Tazeliği**.
- **Tetikleyici** (`tetikleyici.py`) — 08:00 / 17:00 / 24:00 takvimi tanımlı,
  **kurulu değil**. `data/raw` ve `data/katilim.db` teslim için donmuş; kurulu
  bir iş ölçümlerle belgeleri ayrıştırırdı. Ürünleşince kurulacak satır hazır:
  `0 0,8,17 * * * make tazelik`.

**Ölçüldü:** 9 bankanın **2'si** `ETag`/`Last-Modified` veriyor (ikisi de `304`
dönüyor), **7'si** vermiyor → içerik özeti şart. İlk koşu taban çizgisi kurar,
değişiklik iddia etmez. Yanlış alarm: 6 adres × 5 koşu → **0**. Gerekçeler ve
iki ayrı ölçüm: [`kararlar/018-tetikleyici-dinleyici.md`](kararlar/018-tetikleyici-dinleyici.md)

**Kalan dürüst sınır:** değişen sayfa **otomatik yeniden çekilmiyor** — sistem
tespit eder, tazelemeyi operatör başlatır.

**Bugün var olan kırılganlık savunması:**

- Kazıyıcılarda banka başına değişen tek şey URL keşfidir; gezme, robots kapısı,
  nezaket ve gövde ayıklama `TemelKaziyici`'de tektir. Bir banka bozulunca
  diğer sekizi etkilenmez.
- Çıkarım sayfa yapısına değil **metne** bakar: 318 biçim bozma varyantında
  değer **%100** korunuyor ([`DAYANIKLILIK.md`](DAYANIKLILIK.md)).
- Alan silindiğinde sistem **uydurmuyor** — 51 vakada `uydurdu = 0`.
- `make durum` RAG indeksinin bayat olup olmadığını söyler (korpus izi).

**Sahibi:** Görkem, 26 Ağustos gecesi. Tasarım dayanağı
[`KURUMSAL_ENTEGRASYON.md`](KURUMSAL_ENTEGRASYON.md) §5 ve §8'de zaten yazılı
(gecelik iş / cron / Airflow).

---

## 4. LLM'e doğrudan veritabanı analizi — bilinçli olarak yapmıyoruz

Mentörün uyardığı sorun (token limiti, yapısal veriyi modele yıkma) bu mimaride
zaten oluşmuyor: **931 kaydı modele hiç göndermiyoruz.** Niyet yönlendirmesi
deterministik, sorgu kod, cevap şablonu kod. Dil modelinin bu boru hattındaki
tek işi metinden alan çıkarmaktır.

**Text-to-SQL / Vanna.ai neden yok:** sayısal doğrulama kalkanı onu denetleyemez.
Kalkan cevaptaki her sayının veritabanında birebir karşılığını arar; üretilen
SQL yanlış satırı seçtiyse dönen sayı **da** yapısaldır ve kalkandan geçer.
Yani Text-to-SQL tam olarak savunmamızın kör noktasına düşer.

> **Dürüst sınır:** denemedik, ölçmedik. "Daha kötü" demiyoruz; "savunma
> modelimize uymuyor" diyoruz.

---

## 5. Hibrit çıkarım — mentör teyit etti

[ADR 003](kararlar/003-hibrit-cikarim.md) ve ablasyon tablosu bunu ölçüyor:

| Kol | Makro-F1 | Alan doluluğu |
|---|---|---|
| Yalnız kural | 0,689 | %9,1 |
| Yalnız dil modeli | 0,459 | %20,2 |
| Hibrit | 0,795 | %26,5 |
| **Tam hiyerarşi** | **0,827** | %26,0 |

Kaynak: `data/ablasyon.json` (1.024 kayıt, tek kod parmak izi).

---

## 6. Karar destek — bugün genişletildi

**Vardı:** müşteri profili sayfası (tip, tutar, vade, segment, zorunlu ürün
kısıtlarını çözer), toplam maliyet karşılaştırması, uygun olmayanların
sebebiyle gösterilmesi.

**Bugün eklendi — vade duyarlılığı.** Mentörün örneği ("800 bin TL / 120 ay
yerine 60 ay seçilirse avantajı nedir?") artık ekranda:

```
Aylık 25.000 TL tavanına sığan en kısa vade 60 ay: taksit 23.294 TL,
120 aya göre toplamda 759.288 TL daha az ödeme.
```

Hesap `src/comparison/karsilastirma.vade_duyarliligi` içinde, saf kod, LLM yok.

> **Bir dürüstlük kararı:** "en avantajlı vade" diye bir tavsiye üretmiyoruz.
> Toplam maliyet vade kısaldıkça tekdüze azaldığı için kazanan her zaman
> ızgaranın en kısa adımı olurdu — 800.000 TL için aylık 75.880 TL taksit.
> Matematiksel olarak doğru, tavsiye olarak anlamsız. Bu yüzden iki kip var:
> müşterinin **ödeme tavanı** girilirse gerçek bir tavsiye üretilir; girilmezse
> kazanan seçilmez, takas tabloya bırakılır.

Bankanın azami vadesini aşan adımlar **elenmez**, sebebiyle gösterilir —
"neden 180 ay yok?" sorusu cevapsız kalmasın diye.

---

## 7. EDA ve dashboard — vardı, demoda gösterilmiyordu

`app/Genel_Bakis.py` iki sekme taşıyor:

- **Piyasa Görünümü:** kampanya türü dağılımı, banka × tür ısı haritası
- **Yapay Zeka Sistem Kalitesi:** halüsinasyon oranı, şema geçerliliği,
  makro-F1 (güven aralığı ve n ile), güven skoru histogramı, alan bazlı
  doluluk grafiği, banka kayıt defteri

Yapılacak iş kod değil **sunum**: demo videosunda (ES-17) bu sekmeye süre
ayrılacak.

---

## 8. Metrik yazım hatası — gerçekti

Mentörün işaret ettiği hata **doğrulandı ve düzeltildi**. Genel Bakış ekranı
halüsinasyon oranını **%45,00** gösteriyordu; doğrusu **%0,45**.

**Kök sebep — çift birim çevrimi:**

```
eval/calistir.py:110   halusinasyon_orani = ihlal / dolu_alan   → 0,0045  (ORAN)
eval/calistir.py:433   markdown'a yazarken  × 100               → "%0.45"
app/ui_utils.py:57     "%" sonrasını okur, AYNI ADLA saklar     → 0,45    (YÜZDE)
app/Genel_Bakis.py:177 çizerken ikinci kez  × 100               → "%45,00"
```

Aynı ad, iki farklı birim. Düzeltme birimi tekilleştirdi (`_yuzde()` yardımcısı
oranı geri kurar) ve `tests/test_ui_utils.py` sözleşmeyi bağladı: **ekranda
görünen dize, `SONUCLAR.md`'deki dizeyle aynı olmalı.**

### Aynı taramada bulunan iki hata daha

**a) Karşılaştırma sayfasında aşırı iddia.** *"Yapay zeka halüsinasyon riski
tamamen sıfırlanmıştır"* yazıyordu — kendi ölçtüğümüz sayı %0,45 iken. Metin
artık ölçüm dosyasından okunuyor, elle yazılmıyor.

**b) Sunumda bayat sayı.** Ablasyon tablosunun hücreleri doğruydu (%0,51 · %0,42)
ama hemen altındaki "Okuma" paragrafı *"%0,32'den %0,63'e … yani iki katına"*
diyordu. `tests/test_sunum_sayilari.py` yalnız `<table>` hücrelerini
denetliyordu, düz metni hiç denetlemiyordu — kapsam boşluğu bir sayıyı bayat
tuttu. Paragraf düzeltildi, test anlatıyı da kapsayacak şekilde genişletildi
(çarpan iddialarını da denetliyor).

---

## 9. Hackathon / canlı görev — teslim sonrası

Mentör finalde 1,5–2 günlük ek görev gelebileceğini, veri bilimi ve öznitelik
analizi sorularının sorulabileceğini söyledi. Bu bir kod işi değil **hâkimiyet**
işi: ekibin uçtan uca boru hattına ve veri setine tam hâkim olması.

Hazırlık malzemesi zaten depoda: [`VERI_METODOLOJISI.md`](VERI_METODOLOJISI.md) ·
[`DEGERLENDIRME_YONTEMI.md`](DEGERLENDIRME_YONTEMI.md) ·
[`KAPSAM_RAPORU.md`](KAPSAM_RAPORU.md) · `data/exports/` veri kartı.

---

## Bugün yapılan değişikliklerin listesi

| Dosya | Değişiklik |
|---|---|
| `app/ui_utils.py` | `_yuzde()` — birim çevrimi tekilleştirildi |
| `app/pages/1_Karşılaştırma.py` | aşırı iddia düzeltildi · vade duyarlılığı bölümü |
| `src/comparison/karsilastirma.py` | `vade_duyarliligi()` · `vade_tavsiyesi()` |
| `docs/MIMARI.md` | orkestrasyon şeması · KATMAN 0 Selenium · yüklem LLM ✓ |
| `docs/JURI_PROVASI.md` | 9, 10, 11 numaralı sorular |
| `docs/sunum/sunum.html` | ablasyon anlatısındaki bayat sayılar |
| `tests/test_ui_utils.py` | metrik birimi sözleşmesi (+6 test) |
| `tests/test_karsilastirma.py` | vade duyarlılığı (+13 test) |
| `tests/test_mimari_belgesi.py` | **yeni** — belge ↔ kod sözleşmesi (10 test) |
| `tests/test_sunum_sayilari.py` | slayt anlatısı da ölçüme bağlandı (+4 test) |

`make test`: **883 geçti** (önceki 847). `make lint`: temiz.
