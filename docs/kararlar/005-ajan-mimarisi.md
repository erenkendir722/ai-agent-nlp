# ADR 005 — Hiyerarşik ajan mimarisine geçiş

**Tarih:** 14 Ağustos 2026
**Durum:** Kabul edildi
**Sahip:** Eren
**İlgili:** [003 — Hibrit çıkarım](003-hibrit-cikarim.md) · [006 — Şema v1.1.0](006-sema-v1-1-uygunluk.md)

## Bağlam

Yarışmanın adı **"Yapay Zekâ Dil Ajanları Yarışması."** Ajanlar ismin içinde;
jüri muhtemelen ajan mimarisi görmeyi bekliyor. Bu teknik bir tercih değil,
stratejik bir zorunluluk.

Ama v3 planı 14 Ağustos'ta elimize geçtiğinde teslime **12 gün**, özellik
dondurmaya **7 gün** kalmıştı. "Sistemi ajan mimarisine göre yeniden yaz"
bu kapasitede karşılanamaz.

## Seçenekler

1. **Sıfırdan ajan çatısı** (LangChain / LangGraph vb. üzerine). Ajanlar
   "gerçek" olurdu ama: yeni bağımlılık yığınının şartname 5.10 lisans ve
   5.9 "dış servise bağımlı olmama" karşısında denetlenmesi gerekir, mevcut
   106 test ve ölçülmüş %0,25 halüsinasyon oranı sıfırlanır.
2. **Ajan mimarisini yalnız sunumda iddia etmek**, kodu olduğu gibi bırakmak.
   Jüri koda bakarsa iddia çöker; dürüst de değil.
3. **Var olan ajanları açığa çıkarmak + eksik olanı eklemek.**

## Karar

Seçenek 3. Depoyu inceleyince görülen şu: **ajanların çoğu zaten yazılmıştı,
yalnız adı konmamıştı.**

| Ajan | Zaten var olan karşılığı | Yapılan |
|---|---|---|
| Orkestratör | `chatbot.niyet_belirle()` | Genişletildi: profil sorgusu + iz kaydı |
| Toplayıcı | `collector/toplayici.py` | (Sprint 2) desen yetersizse LLM link seçimi |
| Çıkarım | `extraction/llm.py` şema kısıtlı üretim | Sarmalandı |
| **Eleştirmen** | `llm.py` içindeki kanıt reddi | **Ayrı modüle çıkarıldı** |
| **Muhakeme** | — | **Sıfırdan yazıldı** — tek gerçek yeni ajan |
| Karşılaştırma motoru | `comparison/karsilastirma.py` | Dokunulmadı |
| Cevap | `chatbot` şablonları + kalkan | Profil cevabı eklendi |

Yeni kod ~450 satır, refactor ~200 satır. Yedi günde yapılabilir olmasının
sebebi bu.

### Ajan çatısı kullanılmadı

İhtiyacımız olan şey bir çağrı grafiği değil, bir **sözleşme**: `temel.py`
30 satır. Yönlendirme kararları zaten deterministik. Dış çatı, doğrulanması
gereken yeni bir bağımlılık yığını getirirdi; protokolün kendisi bir öğleden
sonra, çatının lisans ve hava boşluğu denetimi günler sürerdi.

### Eleştirmenin ayrılması kozmetik değil

Kanıt doğrulaması `llm.py` içine gömülüydü. Ayrı ajana çıkarmanın somut
karşılığı **ablasyon tablosudur**: *"neden bu kadar ajan?"* sorusunun cevabı
olan tablo "ajan var, eleştirmen yok" satırını içeriyor ve o satır ancak
doğrulama kapatılabilir olduğunda ölçülebilir (`--elestirmen-yok`).

### `AjanIzi` — mimarinin kanıtı

Her ajan ne yaptığını, neden yaptığını ve **hangi motoru kullandığını**
(`llm_kullanildi`) bir ize yazar; arayüzde panel olarak görünür. Jüri ajan
mimarisinin *iddiasını* değil koşum kaydını görür. Bu alan aynı zamanda
sistemin en kırılgan iddiasını ekranda ispatlar: *"aritmetiği ajana
yaptırmıyoruz."*

### Aritmetik ajana verilmedi

Kısıt kontrolü, taksit hesabı ve sıralama saf koddur. Muhakeme ve eleştirmen
ajanlarının ikisi de `llm_kullanir = False`. LLM'in bu boru hattındaki tek
işi metinden alan çıkarmaktır. LLM'e aritmetik yaptırmak, halüsinasyon
savunmasıyla kazanılan güveni tek hamlede kaybettirirdi.

## Sonuç

- `src/ajanlar/`: `temel` · `elestirmen` · `muhakeme` · `orkestrator`
- Mevcut davranış korundu: refactor sonrası 253 test yeşil
- Ablasyon tablosunun kilidi açıldı (`--elestirmen-yok`)
- Refactor sırasında iki gerçek hata bulundu ve düzeltildi: `llm.py` ile
  `schema.py` iki ayrı "kanıt zorunlu alanlar" listesi tutuyordu (bugün aynı,
  yarın sessizce ayrışacaktı); ve `llm.py`'nin belgesi `% 1,89` biçim farkını
  kabul ettiğini söylerken kod reddediyordu — şartname 5.6 kabul edilmesini
  zorunlu tutuyor.
- **Kesilen v3 önerileri:** görsel model yedeği (Playwright bağımlılığı,
  ana planın WON'T listesinde), toplayıcının tam LLM'e devri (`make crawl`
  demonun bel kemiği), fastllm (Çince doküman, C++ bağımlılığı),
  DuckDB göçü (bkz. [ADR 007](007-duckdb-neden-degil.md)).
