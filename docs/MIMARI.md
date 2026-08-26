# Sistem Mimarisi ve Veri Akışı

Şartname madde 6'nın *"Sistem mimarisinin genel açıklaması ve veri akışının
özetlenmesi"*, *"Kullanılan NLP yaklaşımının açıklaması"* ve *"Model veya kural
yapısının açıklaması"* başlıklarına karşılık gelir.

---

## 1. Genel bakış

```mermaid
flowchart TB
    subgraph L0["KATMAN 0 — Toplama"]
        A1[BDDK Listesi<br/>manuel] --> A2[banks.yaml]
        A2 --> A3[Jenerik Toplayıcı<br/>httpx + trafilatura]
        A3 --> A4[(Ham Anlık Görüntü<br/>HTML + URL + tarih)]
    end

    subgraph L1["KATMAN 1 — Ön İşleme"]
        A4 --> B1[Gövde Ayıklama]
        B1 --> B2[Türkçe Normalizasyon<br/>İ/ı · sayı · para · tarih]
    end

    subgraph L2["KATMAN 2 — Çıkarım"]
        B2 --> C1[Kural Katmanı<br/>bağlam + cümle + olumsuzlama]
        B2 --> C2[LLM Katmanı<br/>Qwen3.5 + JSON şema kısıtı]
        C1 --> C3{Uzlaştırıcı}
        C2 --> C3
        C3 --> C4[Kaynak Bağlama<br/>alıntı + karakter aralığı]
        C4 --> C5[Güven Skoru]
    end

    subgraph L3["KATMAN 3 — Depolama"]
        C5 --> E1[(SQLite<br/>düz sütun + JSON kanıt)]
    end

    subgraph L4["KATMAN 4 — Zekâ"]
        E1 --> F1[Karşılaştırma Motoru<br/>deterministik]
        E1 --> F3[Yapısal Sorgu]
        F3 --> F5[Niyet Yönlendirici]
        F5 --> F6[SAYISAL DOĞRULAMA KALKANI]
    end

    subgraph L5["KATMAN 5 — Sunum"]
        F1 --> G1[Streamlit Dashboard]
        F6 --> G1
        F1 --> G2[REST API<br/>3 uç nokta]
    end

    style L2 fill:#fff4e6
    style L4 fill:#f0e8f8
```

---

## 2. Temel ilke: kanıt zinciri

Sistemin tamamı tek bir kısıt üzerine kuruludur:

> **Kanıtsız değer üretilemez.**

Her alan (`src/schema.py::Alan`) şunları birlikte taşır:

| Bileşen | Ne işe yarar |
|---|---|
| `deger` | Normalize edilmiş değer (float, int, date, bool, enum) |
| `ham_ifade` | Metindeki yazımı (`"%1,89"`, `"120 aya kadar"`) |
| `kaynak.alinti` | Değerin geldiği cümle |
| `kaynak.karakter_baslangic/bitis` | Metindeki tam konum |
| `kaynak.url` + `cekim_tarihi` | Köken ve tazelik |
| `guven` | 0–1 arası güven skoru |
| `yontem` | `kural` / `llm` / `hibrit` / `belirtilmemis` |

Bu bir sözleşmedir, öneri değil: `Alan(deger=2.05, yontem="belirtilmemis")`
çağrısı **`ValueError` fırlatır**. Değeri olan bir alan, hangi katmandan
geldiğini beyan etmek zorundadır.

Alan bulunamadığında `None` döndürülmez — `Alan.yok()` ile **"Belirtilmemiş"**
işaretlenir (şartname madde 11'in örnek tablosu bu ifadeyi kullanıyor).

---

## 3. NLP yaklaşımı

*Şartname madde 6, doküman başlığı 2.*

Sistemde **dört ayrı NLP katmanı** vardır ve her biri farklı bir işi yapar.
Hiçbiri tek başına yeterli değildir; ayrılmalarının sebebi de bu.

| # | Katman | Yöntem | Nerede |
|---|---|---|---|
| 3.0 | Türkçe normalizasyon | Kural tabanlı, saf fonksiyonlar | `src/preprocessing/normalizasyon.py` |
| 3.1 | Kural çıkarımı | Regex + bağlam penceresi | `src/extraction/kural.py` |
| 3.2 | LLM çıkarımı | Qwen3.5, JSON şema kısıtlı | `src/extraction/llm.py` |
| 3.3 | Uzlaştırma | Deterministik öncelik tablosu | `src/extraction/uzlastirici.py` |
| 3.4 | Anlamsal getirme (RAG) | Gömme + kosinüs benzerliği | `src/vektor_db.py` |

**Sayısal alanlar 3.1–3.3 ile çıkarılır; 3.4 yalnız serbest metin sorularına
bağlam getirir.** Bu ayrım mimarinin belkemiğidir — sayısal bir cevabın
anlamsal aramadan gelmesi yapısal olarak imkânsızdır (bölüm 6).

### 3.0 Türkçe normalizasyon (`src/preprocessing/normalizasyon.py`)

Şartname 5.6'nın ve *"eksik veya farklı yazılmış bilgiler"* kriterinin kalbi.
Türkçe'ye özgü tuzaklar tek tek ele alınır; en pahalısı **İ/I/ı/i sorunudur**:

```python
"IRAK".lower()      # -> "irak"      YANLIŞ, olması gereken "ırak"
"İSTANBUL".lower()  # -> "i̇stanbul"  birleşik nokta (U+0307) kalır
```

Python'un `str.lower()` metodu Türkçe için yanlıştır ve bu **sessiz** bir
hatadır — eşleştirme ve sınıflandırmada saatler süren hata avına yol açar.
Önce Türkçe'ye özgü harfler elle eşlenir, sonra genel küçültme uygulanır.

Modül **saf**tır: girdi metin parçası, çıktı normalize değer. Metin *içinde*
arama yapmak bu katmanın işi değildir — o iş 3.1'in. Ayrım, her fonksiyonun
doctest ile sınanabilmesini sağlar (`make test` doctest'leri de koşar).

### 3.1 Kural katmanı (`src/extraction/kural.py`)

Regex tabanlı, **yüksek kesinlikli**. Bir sayıyı ancak dört koşul birden
sağlanırsa kabul eder:

1. **Değer deseni** eşleşir (oran / para / vade / tarih)
2. **Bağlam sözcüğü** yakında bulunur — `"50.000 TL"` tek başına bir şey ifade
   etmez; onu `finansman_tutari_max` yapan şey yakınında *"finansman limiti"*
   yazmasıdır
3. **Dışlayıcı sözcük**, kapsayıcı sözcükten daha yakın değildir
4. İsteğe bağlı: **aynı cümle** kısıtı ve **olumsuzlama reddi**

Son iki kısıt gerçek bir hatadan doğdu:

> *"5.000.000 TL'ye kadar finansman. Dosya masrafı alınmaz."*

Naif bir yakınlık kuralı, 5 milyon TL'yi **tahsis ücreti** sanıyordu. Cümle
sınırı ve olumsuzlama denetimi eklenerek düzeltildi
(`tests/test_kalkan.py::test_tutar_tahsis_ucreti_ile_karistirilmaz`).

Kurallar veri olarak durur (`KURALLAR` demeti); yeni alan eklemek bir satır
eklemektir. **Banka başına özel kural yoktur.**

### 3.2 LLM katmanı (`src/extraction/llm.py`)

Qwen3.5, **JSON şema kısıtıyla**. Şema `format` parametresiyle verildiği için
model şemanın dışına çıkamaz — "JSON ayrıştırma hatası" kategorisi yapısal
olarak yok edilir (şema geçerliliği = 1,00).

**İki koşum yolu, tek kod yolu** (`src/extraction/saglayici.py`):

| Yol | Model | Ne zaman |
|---|---|---|
| **EVREN** (varsayılan) | `Qwen/Qwen3.5-122B-A10B` — MoE, Apache-2.0 | `make extract` |
| Yerel yedek | `qwen3.5:4b-q4_K_M`, Ollama | `make extract-yerel` — EVREN düştüğünde, hava boşluğu demosunda |

EVREN, T.C. Cumhurbaşkanlığı SSB'nin yarışmaya tahsis ettiği servistir. Yedek
yol silinmedi: aynı kod yolunu yerelde koşar, yani bulut bağımlılığı bir
tercihtir, zorunluluk değil.

İki kritik ayar:

- **Düşünme kapalı.** Qwen3.5 bir düşünme modelidir; varsayılan davranışta
  üretim bütçesinin tamamını akıl yürütmeye harcar ve içerik boş döner.
  Kapatınca kayıt başına süre dakikalardan saniyelere iner. (EVREN'de
  `chat_template_kwargs`, Ollama'da `think=False` — sağlayıcı katmanı bu farkı
  gizler.)
- **`temperature=0.1`.** Yapısal çıkarımda yaratıcılık istenmez.

> ⚠️ **Ortak servis deterministik değildir.** EVREN'de `temperature=0` ve sabit
> tohumla bile aynı girdi farklı çıktı verebilir (sürekli yığınlama). Ölçüme
> etkisi ve nasıl raporlandığı: [`DEGERLENDIRME_YONTEMI.md`](DEGERLENDIRME_YONTEMI.md)
> bölüm 4.

**Halüsinasyon önleme:** Modelden değeri yorumlaması değil, *metinde geçtiği
hâliyle birebir kopyalaması* istenir. Dönen ifade ham metinde aranır;
bulunamazsa alan **reddedilir** ve günlüğe yazılır. Bu bir istem mühendisliği
vaadi değil, koddur — modelin iyi niyetine güvenmez.

Katılım bankacılığı terimleri (şartname 5.5'teki resmî tanımlar) isteme
enjekte edilir.

### 3.3 Uzlaştırıcı (`src/extraction/uzlastirici.py`)

| Kural | LLM | Sonuç |
|---|---|---|
| var | var, **uyuşuyor** | `hibrit`, güven **yükseltilir** (+0,08) |
| var | var, **çelişiyor** | Sayısal alanda **kural** kazanır, güven düşürülür, çelişki kaydedilir |
| var | yok | `kural` |
| yok | var | `llm` |
| yok | yok | `belirtilmemis` |

Sayısal karşılaştırmada %1 göreli tolerans uygulanır: `"50.000 TL"` ile
`"50 bin TL"` farklı yazımlardır, farklı değer değil.

### 3.4 Anlamsal getirme — RAG (`src/vektor_db.py`)

Yukarıdaki üç katman **sayısal ve kategorik** alanları çıkarır. Ama
*"kampanya koşulları neler?"* gibi sorular yapısal bir alana karşılık gelmez;
bunlar için kaynak metinden ilgili parçayı **getirmek** gerekir.

Yöntem: paragraflar gömme vektörüne çevrilir, sorgu da aynı uzaya taşınır,
**kosinüs benzerliği** en yakın paragrafları verir.

| | |
|---|---|
| Gömme modeli | EVREN `bge-m3-embed` = `BAAI/bge-m3`, **MIT** ([ADR 013](kararlar/013-evren-model-lisans-durusu.md)) |
| Vektör boyutu | 1024 |
| İndeks | Yerel `.npz`, `make vektor` ile kurulur |
| Arama | numpy nokta çarpımı (vektörler L2 normalize, kosinüs = nokta çarpımı) |

**Harici vektör veritabanı kullanılmaz** ([ADR 014](kararlar/014-vektor-db-yerine-yerel-kosinus.md)).
Bu ölçekte tek nokta çarpımı milisaniyeler sürer; bir sunucu eklemek yalnız
demoyu ağa bağımlı kılardı. Karar aynı zamanda hava boşluğu senaryosuyla
tutarlıdır.

Anahtar sözcük araması yerine gömme kullanılmasının sebebi Türkçe'nin
kendisidir: *"emekliye özel"* ile *"emekli müşterilerimize ayrıcalık"* hiçbir
ortak sözcük taşımaz ama aynı şeyi söyler. Kosinüs benzerliği bunu yakalar.

> **Kritik sınır:** bu katman **cevap üretmez**, yalnız alıntı getirir. Getirilen
> parça cevaba *alıntı* olarak girer ve kalkanın bütünlük denetiminden geçer —
> alıntının ham metnin alt dizesi olması ve içindeki her sayının alıntıda birebir
> bulunması şarttır (bölüm 6).

### 3.5 Ajan katmanı (`src/ajanlar/`)

Beş ajan var ve **dördü dil modeli kullanmaz.** Ajan burada "her adımı modele
sormak" değil, *ne yaptığını ve neden yaptığını yazan bir bileşen* demektir;
ortak sözleşme `src/ajanlar/temel.py` içindeki `AjanIzi` — her koşu ekrandaki
"Ajan izleri" panelinde görünür ve `llm_kullanildi` alanını taşır.

| Ajan | Dosya | Ne yapar | LLM |
|---|---|---|---|
| **Uygunluk** | `uygunluk.py` | Kampanyanın kime açık olduğunu yapısal alana çevirir: müşteri tipi, tutar/vade sınırı, zorunlu ürün, segment | ✗ |
| **Eleştirmen** | `elestirmen.py` | Modelin ürettiği her değeri ham metne karşı doğrular; kanıtı olmayanı düşürür | ✗ |
| **Yüklem** | `yuklem.py` | Sayının hangi alana ait olduğunu cümlenin yüklemine bakarak denetler | ✗ |
| **Muhakeme** | `muhakeme.py` | Müşteri profilini kısıtlara karşı çözer, toplam maliyeti hesaplar, sıralar | ✗ |
| **Orkestratör** | `orkestrator.py` | Soruyu doğru ajana yönlendirir, izleri toplar, dürüstlük uyarılarını ekler | ✗ |

**Uygunluk ajanı neden LLM'siz** (A-08, 26 Ağustos): alanların çoğu zaten
uzlaştırılmış alanların yeniden yorumlanmasıdır — `max_tutar` ←
`finansman_tutari_max`, `max_vade_ay` ← `vade_ay_max`, `musteri_tipi` ←
`hedef_kitle`. Kanıtlanmış bir değeri ikinci kez modele sormak yeni bir
halüsinasyon yüzeyi açardı. Kalan alanlar (`min_tutar`, `min_vade_ay`,
`zorunlu_urun`) kalıp işidir ve **bağlam denetimiyle** çıkarılır: ürün adı tek
başına zorunluluk sayılmaz, yanında bir yükümlülük ifadesi aranır.

Ajan katkıları ölçülür, iddia edilmez: ablasyon tablosunun son iki satırı
eleştirmen ve yüklem ajanlarının katkısını gösterir
([`DEGERLENDIRME_YONTEMI.md`](DEGERLENDIRME_YONTEMI.md) §5).

---

## 4. Veri akışı

```
banks.yaml
   │  bankalari_yukle()
   ▼
Toplayıcı ──► HamKayit ──► data/raw/{kod}/{id}.{json,html}
   │                            │
   │                            │ ham_kayitlari_oku()
   │                            ▼
   │                     kampanya_cikar()
   │                       ├─ kurallarla_cikar()  → dict[str, Alan]
   │                       ├─ LLMCikarici.cikar() → dict[str, Alan]
   │                       └─ uzlastir()          → Kampanya
   │                            │
   │                            │ kaydet()  (10 kayıtta bir ara kayıt)
   │                            ▼
   │                     SQLite: kampanyalar
   │                       ├─ düz sütunlar  → karşılaştırma, sıralama
   │                       └─ tam_kayit JSON → kanıt zinciri
   │                            │
   │            ┌───────────────┼───────────────┐
   ▼            ▼               ▼               ▼
Streamlit   Karşılaştırma   Chatbot        REST API
```

`kampanya_id`, `banka_kodu + URL` üzerinden **deterministik** üretilir. Yazma
işlemi `merge` (upsert) olduğu için koşu tekrarlanabilir; yeniden çekim
yinelenen kayıt üretmez.

---

## 5. Depolama: iki temsil bir arada

| Temsil | Kullanım |
|---|---|
| **Düz sütunlar** (`kar_payi_orani REAL`, `vade_ay_max INTEGER`, …) | Karşılaştırma ve sıralama — SQL ile hızlı ve doğru |
| **`tam_kayit` JSON** | Kanıt zincirinin tamamı — kullanıcı bir satırı açtığında gösterilen şey |

Düz sütunlar türetilmiştir; doğruluk kaynağı her zaman `tam_kayit`'tır.

SQLAlchemy kullanılması PostgreSQL'e geçişi bir yapılandırma değişikliğine
indirger (`VERITABANI_URL`).

---

## 6. Chatbot: halüsinasyonsuz mimari

```
Kullanıcı sorusu
   ▼
[Niyet Yönlendirici]  kural tabanlı, 4 sınıf, deterministik
   ├── tekil_sorgu    → SQLite yapısal sorgu
   ├── karsilastirma  → karşılaştırma motoru
   ├── kosul_sorgusu  → metin arama
   └── kapsam_disi    → kibar ret
   ▼
[Şablon tabanlı cevap üretimi]   — serbest LLM üretimi YOK
   ▼
[SAYISAL DOĞRULAMA KALKANI]      ← özgün katkımız
   Cevaptaki her sayının getirilen yapısal kayıtta karşılığı var mı?
   Yoksa → cevap REDDEDİLİR
   ▼
[Kaynak ekleme]  banka + URL + çekim tarihi + yasal uyarı
```

**Altın kural:** *Sayısal cevaplar asla metin aramasından gelmez, her zaman
yapısal veriden gelir.* Metin arama yalnız *"kampanya koşulları neler?"* gibi
metinsel sorulara hizmet eder.

### Dayanak denetimi — kalkanın göremediği hata

Kalkan *"bu sayı kayıtta var mı?"* diye sorar. Sormadığı bir soru vardı:
***"bu kayıt, sorulanın kendisi mi?"***

Ölçüldü (25 Ağustos, S-10 test seti): *«Garanti Bankası'nın konut kredisi
faizi kaç?»* sorusuna sistem **Türkiye Finans'ın** oranını veriyordu — üstelik
kaynakçasıyla, yani doğrulanmış görünerek. Kalkan bunu yakalayamaz, çünkü sayı
gerçekten yapısal veride var; yalnızca **yanlış bankanın**.

Sebep, kayıt seçimindeki `or kayitlar` yedeğiydi: banka eşleşmeyince tüm
korpusa düşüp en dolu kaydı seçiyordu. Artık iki durum ayrılıyor:

| Soru | Davranış |
|---|---|
| Banka adı geçmiyor (*«en düşük oran hangi bankada?»*) | Tüm korpus — doğru |
| Banka adlandırılmış ve korpusta VAR | O bankanın kayıtları |
| Banka adlandırılmış ama korpusta YOK | **Cevap verilmez**, mevcut bankalar listelenir |

Kapsam dışı tespiti de aynı ilkeye çevrildi. Eskiden **yasak listesiydi**
(*"hava durumu"*, *"mac skoru"*…) ve ölçümde beş kapsam dışı sorunun beşi de
içeri sızıyordu — *«Bugün hava nasıl?»* listedeki ifadeye uymuyor. Yasak
listesi tanım gereği tamamlanamaz. Şimdi tersi soruluyor: **soruda bu alana
ait tek bir dayanak var mı?** Sözlük veriden türer (banka adları
kayıtlardan, tür ve alan adları şemadan), yani yeni banka eklendiğinde
denetim kendiliğinden genişler.

Niyet yönlendirici bilinçli olarak kural tabanlıdır: karar 4 sınıflı ve kelime
örüntüsüyle güvenilir biçimde çözülüyor. Her LLM çağrısı 4B modelde ~10 saniye;
bunu yönlendirmede harcamak yerine cevabın doğruluğunda kullanmak daha doğru.

> Türkçe ayrıntı: soru eki dört biçimlidir (mi/mı/mu/mü). `arama_anahtari`
> normalizasyonu bunu ikiye indirir; ünlü uyumunu hesaba katmamak
> *"A mı daha iyi?"* sorusunu yanlış katmana yönlendirir.

---

## 7. Karşılaştırma motoru

Tamamen deterministik, **LLM kullanmaz**. Bankalar arası karşılaştırmada LLM
kullanmak, açıklanamayan ve tekrarlanamayan sonuç demektir.

Şartname 5.7'nin beş kriteri (`Kriter` enum) desteklenir. *"En Avantajlı"*
kara kutu değildir:

1. Her kriter kendi içinde min-maks ile 0–1'e ölçeklenir
2. Kullanıcının belirlediği ağırlıklarla toplanır (varsayılan: kâr payı %40,
   masraf %25, vade %20, ödül %15)
3. Eksik veri nötr (0,5) sayılır ve **karşılaştırılabilirlik** oranı düşer —
   kullanıcı yarım veriye dayalı bir sıralamayı tam veri sanmasın
4. Ağırlıklar arayüzde kaydırıcıyla değiştirilir

Ayrıca finansal titizlik uyarıları üretilir: farklı vadeli ürünler yan yana
konduğunda *"doğrudan karşılaştırılamaz"* uyarısı çıkar.

---

## 8. Modülerlik

| Modül | Sorumluluk | Bağımlılığı |
|---|---|---|
| `schema.py` | Veri sözleşmesi | — (hiçbir şeye bağlı değil) |
| `preprocessing/` | Türkçe normalizasyon | — (saf fonksiyonlar) |
| `collector/` | Toplama | `schema` |
| `extraction/` | Çıkarım | `schema`, `preprocessing` |
| `depolama.py` | Kalıcılık | `schema` |
| `comparison/` | Karşılaştırma | `depolama` |
| `rag/` | Chatbot | `depolama`, `comparison` |
| `api/`, `app/` | Sunum | yukarıdakiler |

Bağımlılık yönü tek yönlüdür; `schema` hiçbir şeye bağlı değildir ve bu yüzden
dondurulabilmiştir ([ADR 001](kararlar/001-sema-sozlesmesi.md)).
