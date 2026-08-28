# ADR 017 — Kod parmak izi yalnız çıkarım zamanı kaynaklarını kapsar

**Tarih:** 26 Ağustos 2026
**Durum:** Kabul edildi
**Sahip:** Eren
**İlgili:** [005 — Ajan mimarisi](005-ajan-mimarisi.md) · [011 — Atomik ablasyon](011-atomik-ablasyon.md)

## Bağlam

`src/depolama.kod_parmak_izi()`, veritabanındaki değerlerin bayat olup
olmadığını anlamak için "çıktıyı belirleyen kaynakların" içerik özetini alır.
Koşu bitiminde damga veritabanına yazılır; `cikarim_durumu()` bugünkü izle
karşılaştırır. Tutmazsa `make eval`, jüriye giden `docs/SONUCLAR.md`'nin en
başına şunu yazar:

> 🔴 **BAYAT — bu sayıları sunuma kopyalamayın.**

Liste 26 Ağustos sabahı genişletilmişti; `src/ajanlar` **klasörünün tamamı**
eklendi. Gerekçe doğruydu: eleştirmen, yüklem ve uygunluk ajanları çıkarım
hattının içinde koşuyor ve değerleri değiştiriyor. Onlarsız liste, bayatlık
tespitini körleştiriyordu.

## Sorun

Klasörün tamamını almak **fazla kaba** çıktı. Beş ajanın ikisi çıkarım hattında
hiç çağrılmıyor:

| Ajan | Nerede çağrılıyor | Çıkarım çıktısını değiştirir mi |
|---|---|---|
| Eleştirmen | `extraction/llm.py:273` | **evet** — kanıtsız değeri düşürür |
| Yüklem | `extraction/uzlastirici.py:261` | **evet** — yanlış alana yazılmış sayıyı düzeltir |
| Uygunluk | `extraction/uzlastirici.py:466` | **evet** — kayda yeni alan yazar |
| Muhakeme | `ajanlar/orkestrator.py` · `app/pages/0_*` | hayır — **sorgu zamanı** |
| Orkestratör | `api/sunucu.py` · `app/pages/2_*` | hayır — **sorgu zamanı** |

26 Ağustos akşamı uçtan uca sağlık taramasında ölçüldü: chatbot cevap
biçiminde yapılan bir düzeltme (`orkestrator.py`, kalkanın `hesap` anahtar
çakışması) parmak izini kaydırdı ve `cikarim_durumu()` **"BAYAT"** dedi.
Çıkarılan tek bir değer bile değişmemişti.

Bu, `kod_parmak_izi()`'nin kendi belgesinde anlatılan **CRLF hikâyesiyle aynı
sınıf hata**: iz, çıktıyı belirleyen şeyi değil, ona *yakın duran* şeyi
özetliyordu. Orada satır sonu, burada klasör sınırı.

Maliyeti teslim arifesinde ciddi: yanlış bayrak, ekibi gereksiz bir `make
extract`'e iter. EVREN bayt düzeyinde deterministik olmadığı için yeniden
çıkarım makro-F1'i ±0,01 oynatır, `docs/SONUCLAR.md` yeniden üretilir, RAG
korpus izi düşer, slayta bağlı testler yeniden denetlenir. Hiçbiri gerekmezken.

## Seçenekler

1. **Bırak, jüriye açıkla.** Bayrak yanlış kalır; `make eval` koşan herkes onu
   görür. Sunumda "o uyarıyı boş verin" demek, uyarı mekanizmasının kendisini
   değersizleştirir.
2. **`make extract`'i yeniden koş.** Bayrağı temizler ama sorunu çözmez —
   sorgu zamanı ajanlarına bir daha dokunulduğunda aynı yanlış alarm döner.
   Üstelik ölçüm setini teslim arifesinde oynatır.
3. **Listeyi daralt, damgayı ispatla taşı.**

## Karar

Seçenek 3.

### Liste daraltıldı

`src/ajanlar` yerine dört dosya: `__init__.py`, `temel.py`, `elestirmen.py`,
`yuklem.py`, `uygunluk.py`. `muhakeme.py` ve `orkestrator.py` **bilerek dışarıda**.

Kural şu: **listeye bir dosya, çıkarım çıktısını değiştirebiliyorsa girer.**
Ajan olması yetmez; `boru_hatti.py`'nin kat ettiği yolda olması gerekir.

### Damga uydurulmadı, ispatlandı

Tanım değişince eski damga (`db13673d57462b44`) yeni tanımla hesaplanan değere
(`e2e7423991d16e91`) eşit olmaz. Damgayı körlemesine yeniden yazmak,
`Alan(deger=..., yontem="belirtilmemis")` yasağının ihlali olurdu.

`tools/parmak_izi_goc.py` bunun yerine önce **ispatlar**: dar kümedeki dosyalar,
veritabanının çıkarıldığı commit'ten (`9a9ffc2`) bu yana bayt bayt aynı mı?
Aynıysa yeni tanımın o koşudaki değeri bugünkü değerle özdeştir ve yeniden
çıkarım yapmadan bilinebilir. Değilse araç **yazmaz** ve `make extract` ister.

Reddetme yolu sınandı: referans olarak kural düzeltmesinden önceki commit
verildiğinde araç `src/extraction/kural.py`'yi gösterip `--uygula` verilmesine
rağmen yazmayı reddetti.

## Sonuç

- `CIKARIM_KAYNAKLARI` 4 girdiden 8 girdiye çıktı ama **kapsamı daraldı**
- `data/katilim.db` damgası taşındı; ölçüm sayıları **değişmedi**
- `tests/test_parmak_izi.py` sözleşmeyi bağlar: sorgu zamanı ajanları listede
  görünürse test kırılır
- Yeniden çıkarım **gerekmedi** — 931 kayıt, `docs/SONUCLAR.md` ve RAG indeksi
  olduğu gibi geçerli

## Not — bu bayrak ne zaman DOĞRU çalışır

Bayrak hâlâ gerçek bayatlığı yakalar. Aynı taramada sınandı: `kural.py`
değişmiş bir referansla göç aracı reddetti. Daraltma, bayrağı zayıflatmadı;
**yanlış pozitifini kaldırdı** — kalkanın yanlış pozitifine verilen cevabın
aynısı (proje kuralı: *"çözüm kalkanı gevşetmek değil, denetlenecek metni doğru
seçmektir"*).
