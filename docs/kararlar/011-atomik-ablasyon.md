# ADR 011 — Ablasyon tek süreçte, tek kod izinde koşar

**Tarih:** 19 Ağustos 2026 · **Durum:** kabul edildi · **Sorumlu:** Eren
**İlgili bulgu:** `docs/DUZELTME_TASARIMI.md` § 2.2
**Şema etkisi:** yok

## Bağlam

Ablasyon tablosu, projenin **en güçlü sunum grafiğidir**: hibrit çıkarımın
kural ve LLM katmanlarının her birinden daha iyi olduğunu gösterir, yani
mimari kararı ölçümle savunur.

18 Ağustos'ta `data/ablasyon.json` şöyleydi:

| Satır | Tarih | `kod_parmak_izi` |
|---|---|---|
| `llm` | 17 Ağu | `f797dd3f69630cfc` |
| `kural` | 17 Ağu | `f797dd3f69630cfc` |
| **`hibrit`** | **18 Ağu** | **`f835ccc2f7e8d116`** |

Yani *«hibrit 0,778 vs kural 0,628 vs LLM 0,176»* karşılaştırması **geçersizdi**:
hibrit satırı, aradaki iki gün içinde iyileştirilmiş kodla koşulmuştu
(`545c106` dilim tablosu ayrıştırıcı, `fd4c7f8` kampanya_turu düzeltmesi).
Fark, mimariden değil kod sürümünden gelmiş olabilirdi.

**Eksik olan tespit değildi.** `eval.calistir._ablasyon_notu` bu durumu zaten
yakalıyor ve *«🔴 Satırlar KARŞILAŞTIRILAMAZ»* basıyordu. Sistem doğruyu
söylüyordu; kimse dinlememişti.

**Eksik olan koşumdu.** Üç yapılandırma üç ayrı elle komutla, farklı
zamanlarda çalıştırılıyordu:

```bash
make extract-kural && make eval
make extract-llm   && make eval
make extract       && make eval
```

Aralarında insan var, dolayısıyla araya kod değişikliği girebilir. **İnsan
hatasını uyarıyla değil, yapıyla engellemek gerekir.**

### İkinci bulgu — ölçüm, ölçtüğü sistemi bozuyordu

`_cikar_ve_kaydet` her koşuda **üretim veritabanına** yazıyordu. Yani
`make extract-kural`, demoyu besleyen 96 kaydı *katman eksik* hâlleriyle
değiştiriyordu. Sonrasında `make extract` koşulmazsa arayüz ve chatbot
sessizce bozuk veri gösterirdi — ve bunu gösteren hiçbir işaret yoktu.

## Karar

### 1. Tek süreç, tek parmak izi

`eval/ablasyon.py` üç yapılandırmayı **tek süreçte** koşar; parmak izi başta
bir kez alınır ve üç satıra da yazılır. Satırların ayrışması **yapısal olarak
imkânsızdır** — aralarında insan yoktur.

Sıra da bilinçlidir: **kural önce**. LLM gerektirmediği için saniyeler sürer;
bir sorun varsa iki saatlik LLM koşularından *önce* ortaya çıkar.

### 2. Atomik yazım

Tablo ancak **üçü de bittikten sonra**, geçici dosyaya yazılıp `os.replace`
ile yerine konarak oluşur. Koşu yarıda kalırsa `data/ablasyon.json` değişmez.

Bu kural **kendi hızlı moduna da uygulanır**: `make ablasyon hizli=1` bir
duman testidir ve tabloyu **yazmaz**. İlk sürüm yazıyordu — tek satır koyup
diğer ikisini siliyordu, yani önlemeye çalıştığımız yarım tablonun ta
kendisini üretiyordu. Kusuru kendi testimiz yakaladı.

### 3. Ölçüm koşusu üretim verisine dokunmaz

Her yapılandırma kendi veritabanına yazar (`data/ablasyon/{ad}.db`).
`make extract-kural` ve `make extract-llm` de artık oraya yazıyor;
`data/katilim.db` yalnız hibrit koşusuyla değişir.

### 4. Tek yazıcı — `make eval` tabloya dokunmaz

Uygulama sırasında çıktı ve **kök nedenin ikinci yarısıydı**: `eval.calistir`
içindeki `ablasyon_kaydet()`, HER `make eval` koşusunda veritabanının koşu
kaydından yapılandırmayı okuyup `data/ablasyon.json`'a *kendi satırını*
ekliyordu.

Satırların farklı zamanlarda ve farklı kodlarla birikmesine izin veren
mekanizma buydu. Atomik koşucuyu eklemek tek başına yetmezdi: koşudan sonra
atılacak tek bir `make eval`, geçerli tabloyu tek satırla ezerdi. (Nitekim
uygulama sırasında tam olarak bu oldu.)

`ablasyon_kaydet` **kaldırıldı**. Artık:

- **Tek yazıcı:** `eval/ablasyon.py` (`make ablasyon`)
- **Tek okuyucu:** `eval.calistir._ablasyon_notu` (`make eval-ablation`)

`tests/test_ablasyon.py::test_eval_ablasyon_tablosunu_yazmaz` artımlı
yazıcının geri gelmesini engeller.

### 5. Savunma katmanı silinmedi

`_ablasyon_notu` içindeki parmak izi ve korpus büyüklüğü uyarıları **duruyor**.
Koşucu garanti veriyor diye kaldırmak, garantinin bozulduğu günü sessiz
kılardı. Artık tetiklenmemeleri gerekir; tetiklenirlerse gerçek bir arıza var.

## Kullanım

```bash
make ablasyon           # üç yapılandırma + üç ölçüm + tablo (~3 saat)
make ablasyon hizli=1   # LLM'siz duman testi, tablo YAZILMAZ
make eval-ablation      # tabloyu SONUCLAR.md'ye bas
```

## Sonuç

| Ölçüt | Önce | Sonra |
|---|---|---|
| Tablodaki farklı kod izi sayısı | 2 | **1** (yapısal garanti) |
| Yarım tablo mümkün mü | evet | **hayır** (atomik + eksik koşu yazmaz) |
| Ablasyon üretim verisini bozar mı | **evet** | hayır |
| Elle koşulacak komut sayısı | 6 | **1** |
| Tabloyu yazan yer sayısı | 2 (`make eval` + elle) | **1** (`make ablasyon`) |

`tests/test_ablasyon_butunlugu.py` yayınlanan tablonun tek kod iziyle
koşulduğunu denetler. Bu test, düzeltmeden önce **kırmızıydı** — bulgu
testle sabitlendi, iddiayla değil.
