# ADR 016 — RAG gömmesi için yerel sağlayıcı seçeneği

**Tarih:** 26 Ağustos 2026
**Durum:** Kabul edildi
**İlgili:** [ADR 013](013-evren-model-lisans-durusu.md) · [ADR 014](014-vektor-db-yerine-yerel-kosinus.md) · [ADR 015](015-rag-indeksi-depoda.md)

## Bağlam

ADR 015 vektör indeksini depoya aldı ve bayatlık denetimi ekledi. Bu, indeksin
ağsız bir makinede **kurulabilmesi** sorununu çözdü — gömmeler EVREN'den geldiği
için indeks türetilemiyordu, dolayısıyla taşınması gereken bir varlıktı.

Ancak «RAG artık çevrimdışı çalışır» sonucu buradan **çıkmıyordu** ve yanlışlıkla
çıkarıldı. Ölçüldüğünde görüldü ki `vektor_ara`, indeks hazır olsa bile her
sorguda **sorgunun kendisini** gömmek zorunda:

```python
sorgu_vektoru = np.asarray(gom(sorgu), dtype=np.float32)   # src/vektor_db.py
```

`gom()` tek bir uca bakıyordu: EVREN. Yani hava boşluğu demosunda, 33 MB'lık
indeks depoda dururken bile chatbot'un koşul sorusu yolu çalışmıyordu.

**İndeksi taşımak gerekliydi; yeterli değildi.**

## Ölçüm

Aynı soru, aynı indeks, tek değişken gömme sağlayıcısı. Soket kilidi altında
(`tests/test_sizinti_yok.py` fixture'ıyla aynı yöntem):

| Sağlayıcı | Dış bağlantı denemesi | Sonuç |
|---|---|---|
| `evren` | **3** (195.142.26.68) | «gömme servisine ulaşılamadı» |
| `ollama` | **0** | 3 kaynaklı gerçek cevap |

Getirilen paragrafların örtüşmesi (3 soru × ilk 3 sonuç, depodaki EVREN indeksi
üzerinde):

| Soru | Örtüşme | Not |
|---|---|---|
| «Konut finansmanı için gerekli belgeler» | 3/3, sıra aynı | skor farkı ≤ 0,0004 |
| «Kampanya koşulları nelerdir?» | 3/3 metin, 2/3 kimlik | fark, aynı metnin iki kampanyada tekrarı |
| «Kredi kartı aidatı alınıyor mu?» | 3/3, sıra aynı | skor farkı ≤ 0,0015 |

Boyut: **1024** — `vektor_db.BOYUT` ve depodaki indeksle birebir.

## Karar

`GOMME_SAGLAYICI` ortam değişkeni eklendi; `LLM_SAGLAYICI`'nın gömme katmanındaki
karşılığı.

- `evren` (varsayılan) — `bge-m3-embed`, ölçüm koşuları için.
- `ollama` — `bge-m3`, hava boşluğu ve EVREN düştüğünde.

Ollama'nın OpenAI uyumlu `/v1` ucu kullanılıyor: aynı istemci, aynı kod yolu,
yalnız taban adres ve model adı değişiyor. Ayrı bir istemci sınıfı yazmak iki
ayrı hata yüzeyi açardı.

**İki sağlayıcı da aynı modeldir.** `bge-m3` ve `bge-m3-embed` ikisi de
`BAAI/bge-m3` (MIT, ADR 013). Ad farkı servislerin adlandırma tercihidir. Bu
yüzden `_model_ailesi()` adları normalleştirir: ham ad karşılaştırması yapılsaydı
EVREN'de kurulmuş indeksi Ollama ile sorgulamak her seferinde sahte bir
«model uyuşmuyor» uyarısı üretirdi. Gerçekten farklı bir modele geçilirse
(örn. `nomic-embed-text`) uyarı çıkar — sessiz bozulma bırakılmadı.

**Bilinmeyen sağlayıcı sessizce EVREN'e düşmez**, `ValueError` fırlatır. Bir
yapılandırma hatasını fark edilmeyen bir dış çağrıya çevirmek, bu dosyanın
tarihçesindeki sıfır-vektörü hatasının aynısı olurdu.

`docker-compose.yml` her iki uygulama servisine `GOMME_SAGLAYICI: "ollama"`
geçirir — sabit, interpolasyonsuz. Gerekçesi compose dosyasında yazılı:
Compose interpolasyonu proje kökündeki `.env`'i okur ve oradaki yerel-koşu
değerleri hava boşluğu varsayılanını sessizce ezer.

## Sonuçlar

- Hava boşluğu iddiası artık RAG metin aramasını da **kapsıyor**.
- Ollama tarafında bir kerelik `ollama pull bge-m3` gerekiyor (~1,2 GB).
  O adım internet ister; sonrası istemez. `docs/KURULUM.md` ve compose
  başlığı bunu yazıyor.
- Ölçüm koşuları değişmedi: varsayılan hâlâ `evren`, `docs/SONUCLAR.md`
  sayıları aynı yoldan üretiliyor.
- Regresyon: `tests/test_sizinti_yok.py::test_yerel_gomme_ucu_izinli_host_listesinde`
  ve `tests/test_vektor_db.py` içindeki dört sağlayıcı testi.
