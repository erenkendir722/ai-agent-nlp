# Model ve Kural Yapısının Açıklaması

*Şartname madde 6, doküman başlığı 5.*

Sistem tek bir modele dayanmaz. Üç farklı karar mekanizması vardır ve
**hangisinin ne zaman söz sahibi olduğu koda yazılıdır**, çalışma anında
belirlenmez:

| Mekanizma | Türü | Söz sahibi olduğu yer |
|---|---|---|
| Kural motoru | Deterministik, regex + bağlam | Sayısal alanlar (çelişkide kazanır) |
| Dil modeli | Qwen3.5, JSON şema kısıtlı | Serbest metin, kuralın bulamadığı alanlar |
| Şema sözleşmesi | Pydantic, donmuş | Her ikisinin üstünde — kanıtsız değeri reddeder |

Gerekçe: [ADR 003 — hibrit çıkarım](kararlar/003-hibrit-cikarim.md).

---

## 1. Şema sözleşmesi — en üstteki kural

Model de kural motoru da aynı sözleşmeye tabidir: **kanıtsız değer
üretilemez.** Bu bir stil tercihi değil, çalışma anında dayatılan bir kısıttır.

```python
Alan(deger=2.05, yontem="belirtilmemis")   # ValueError
```

Her `Alan` şunları taşımak zorundadır:

- **değer** — normalize edilmiş hâli
- **ham ifade** — metinde geçtiği hâli
- **güven** — 0–1 arası
- **yöntem** — `kural` · `llm` · `hibrit` (hangi katmandan geldiği)
- **birim** — çok birimli alanlarda zorunlu (`tahsis_ucreti` TL mi yüzde mi?)

Şema **donmuştur** (`src/schema.py`, sürüm sabiti dosyada). Dört kişi ona karşı
çalışır; değiştirmek için ADR yazılır ve sürüm yükseltilir. Sessiz bir değişiklik
dört kişinin işini birden bozar.

Sözleşmenin bir sonucu: *"model şunu söyledi"* bir gerekçe değildir. Değerin
nereden geldiği veriye yazılıdır, sonradan sorulabilir.

---

## 2. Kural motorunun yapısı

Kurallar **kod değil, veridir.** Tek bir demette (`KURALLAR`) dururlar; yeni bir
alan eklemek yeni bir kayıt eklemektir, yeni bir fonksiyon yazmak değil.

**Banka başına özel kural yoktur.** Bu bilinçli bir kısıt: banka başına kural
yazmak, on bankada çalışıp on birincide çöken bir sistem üretir. Şartnamenin
*"görülmemiş metin"* kriteri de bunu ölçer.

### Bir kural ne söyler

| Alan | İşlevi |
|---|---|
| `alan` | Hangi şema alanını dolduruyor |
| `deger_deseni` | Değerin biçimi (oran / para / vade / tarih) |
| `ayristirici` | Eşleşen metni normalize değere çeviren saf fonksiyon |
| `baglam_sozcukleri` | **Zorunlu.** Değeri o alan yapan çevre sözcükler |
| `baglam_penceresi` | Bağlamın aranacağı karakter yarıçapı |
| `dislayici_sozcukler` | Yakındaysa değeri reddeden sözcükler |
| `ayni_cumle` | Bağlam değerle aynı cümlede olmak zorunda mı |
| `olumsuzlama_reddet` | *"alınmaz / yok / ücretsiz"* bağlamından sayı çıkarma |
| `taban_guven` | Kuralın kendine biçtiği güven |

**Bağlam sözcüğü olmadan hiçbir değer kabul edilmez.** `"50.000 TL"` metnin
herhangi bir yerinde geçebilir; onu `finansman_tutari_max` yapan şey, yakınında
*"finansman limiti"* yazmasıdır. Halüsinasyon önlemenin kural katmanındaki
karşılığı budur.

### Kısıtlar ölçülmüş hatalardan doğdu

Kural yapısındaki her ek kısıt, gerçek bir yanlış çıkarımın sonucudur:

> *"5.000.000 TL'ye kadar finansman. Dosya masrafı alınmaz."*

Naif bir yakınlık kuralı 5 milyon TL'yi **tahsis ücreti** sanıyordu. `ayni_cumle`
ve `olumsuzlama_reddet` bu yüzden var — ikisi de bir teoriden değil, bir
testten doğdu.

### Vetolar ve tablo tuzağı

Bazı ifadeler bir değeri toptan reddeder (*"toplam maliyet"* gibi). Ama tablo
biçimli metinde bağlam penceresi **komşu kolonların başlıklarını** da kapsar ve
veto yanlış hedefi vurabilir:

```
Vade | Kâr Oranı | Tahsis Ücreti | Aylık Toplam Maliyet
  3  |  3,67%    |    0,50%      |     5,07%
```

Burada `0,50%` hücresinin kendi başlığı *"Tahsis Ücreti"* — yani alanı doğrudan
adlandırıyor. Buna rağmen komşu kolondaki *"toplam maliyet"* ifadesi vetoyu
tetikliyordu. Çözüm: **kolon başlığı alanı adlandırıyorsa veto düşer**
(`kolonun_asabilecegi_vetolar`).

Bu düzeltmenin ölçülen etkisi ve nasıl doğrulandığı:
[`ALTIN_SET_DENETIMI.md`](ALTIN_SET_DENETIMI.md) bulgu 12.

---

## 3. Dil modeli yapısı

### Model seçimi ve gerekçesi

| Yol | Model | Lisans |
|---|---|---|
| EVREN (varsayılan) | `Qwen/Qwen3.5-122B-A10B` — MoE, 122B toplam / 10B aktif | Apache-2.0 |
| EVREN (seçenek) | `Qwen/Qwen3.6-35B-A3B` — `--model llm-fast` | Apache-2.0 |
| Yerel yedek | `qwen3.5:4b-q4_K_M` (Ollama) | Apache-2.0 |
| RAG gömme | `bge-m3-embed` = `BAAI/bge-m3` | MIT |

**Llama ve Gemma türevi kullanılmaz** — şartname 5.10 doğrudan bunları hedefler.
Lisanslar modelin beyanına değil, Hugging Face depo üst verisine dayanır ve
`make lisanslar-teyit` ile her koşuda yeniden doğrulanır; tutmazsa komut kırılır.
Kanıt: `docs/kanit/model-lisanslari.json`. Duruş:
[ADR 013](kararlar/013-evren-model-lisans-durusu.md).

### Modelin serbestliği nerede biter

Model **serbest metin üretmez**, şema doldurur:

- Çıktı **JSON şema kısıtıyla** alınır; model şemanın dışına çıkamaz. Bunun
  ölçülen sonucu, "JSON ayrıştırma hatası" kategorisinin yapısal olarak yok
  olmasıdır (şema geçerliliği 1,00).
- Modelden değeri **yorumlaması değil, metinde geçtiği hâliyle kopyalaması**
  istenir. Dönen ifade ham metinde aranır; bulunamazsa alan **reddedilir**.
  Bu bir istem mühendisliği vaadi değil, koddur.
- `temperature=0.1` — yapısal çıkarımda yaratıcılık istenmez.
- Düşünme kapalıdır; açık bırakılırsa model üretim bütçesini akıl yürütmeye
  harcar ve içerik boş döner.

Katılım bankacılığı terimleri (şartname 5.5'teki resmî tanımlar) isteme
enjekte edilir — model "kâr payı"nın faiz olmadığını varsaymaz, söylenir.

---

## 4. İki katman çeliştiğinde ne olur

Uzlaştırma **deterministik bir tablodur**, bir model kararı değil:

| Kural | LLM | Sonuç |
|---|---|---|
| var | var, uyuşuyor | `hibrit`, güven yükseltilir |
| var | var, çelişiyor | **Sayısal alanda kural kazanır**, güven düşürülür, çelişki kaydedilir |
| var | yok | `kural` |
| yok | var | `llm` |
| yok | yok | `belirtilmemis` |

**Neden sayısal alanda kural kazanır:** kural motoru bir değeri ancak dört koşul
birden sağlanırsa üretir, yani yanlış pozitifi pahalıdır. Model ise akıcı ve
ikna edici biçimde yanılabilir. Çelişki **gizlenmez**, kayda yazılır ve
sayılabilir.

Sayısal karşılaştırmada %1 göreli tolerans uygulanır: `"50.000 TL"` ile
`"50 bin TL"` farklı yazımlardır, farklı değer değil.

---

## 5. Cevap üretiminde model kullanılmaz

Chatbot **şablon tabanlıdır**; serbest LLM üretimi yoktur. Karşılaştırma motoru
da tamamen deterministiktir. Sebep tek cümleyle: bankalar arası karşılaştırmada
LLM kullanmak, açıklanamayan ve tekrarlanamayan sonuç demektir.

Üretilen her cevap parçası **kökenini** taşır (yapısal / alıntı / sistem hesabı)
ve kalkan her parçayı kökenine göre farklı ölçütle denetler. Ayrıntı:
[`MIMARI.md`](MIMARI.md) bölüm 6.

---

## İlgili belgeler

| Konu | Dosya |
|---|---|
| Katmanların bütünü ve veri akışı | [`MIMARI.md`](MIMARI.md) |
| Hibrit çıkarım kararının gerekçesi | [ADR 003](kararlar/003-hibrit-cikarim.md) |
| Model lisans duruşu | [ADR 013](kararlar/013-evren-model-lisans-durusu.md) |
| RAG mimarisi | [ADR 014](kararlar/014-vektor-db-yerine-yerel-kosinus.md) |
| Ölçüm yöntemi | [`DEGERLENDIRME_YONTEMI.md`](DEGERLENDIRME_YONTEMI.md) |
