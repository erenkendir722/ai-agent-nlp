# SVARTAL — Katılım Bankacılığı Metin Madenciliği

TEKNOFEST 2026 Yapay Zekâ Dil Ajanları Yarışması, 2. Senaryo.
Dört kişilik takım: **Eren** (kaptan), **Samet**, **Görkem**, **Esra**.

**Bu projede Türkçe konuşulur.** Kod, yorum, commit mesajı, dokümantasyon —
hepsi Türkçe. Değişken ve fonksiyon adları da Türkçe (`kar_payi_orani`,
`kurallarla_cikar`, `Alan.yok()`).

---

## 🔴 HER OTURUMDA — GIT PROTOKOLÜ

Dört kişi aynı depoda çalışıyor. **Bu iki adım atlanırsa iş kaybı olur.**

### Çalışmaya BAŞLARKEN

**İlk iş: kullanıcıya "GitHub'daki değişiklikleri pull ettin mi?" diye sor.**

```bash
git pull --rebase origin main
```

Oturum başında bir hook otomatik `git fetch` yapar ve geride kalınmışsa uyarır.
**Uyarı geldiyse, kullanıcı pull etmeden hiçbir dosyayı düzenleme.** Pull
edilmeden yapılan düzenleme çakışma üretir; kötü ihtimalde arkadaşının işi ezilir.

Hook sessiz kaldıysa (ağ yoksa) yine de sor — hatırlatmak bedava, iş kaybı değil.

### Çalışmayı BİTİRİRKEN

**Son iş: kullanıcıya "pushladın mı?" diye sor.**

```bash
git add -A
git commit -m "..."
git push origin main
```

Pushlanmayan iş kimseye ulaşmaz. `GOREVLER.md`'de o işi bekleyen arkadaşı
boşuna bekletir.

Ayrıca: **bitirilen görevin yanına `GOREVLER.md`'de `[x]` atıldı mı?** Bunu da hatırlat.

> **Commit imzası:** Bu depoda commit'lere yapay zekâ imzası (`Co-Authored-By`
> vb.) **eklenmez**. Takım kendi adıyla commit atar.

---

## 📋 "Benim görevim ne?" — görev panosu

Tek doğruluk kaynağı [`GOREVLER.md`](GOREVLER.md). Kişi sorduğunda oradan cevapla.

```bash
make gorev ad=Esra        # kişinin yapabilecekleri + bloke olanlar
make gorev                # herkesin özeti + darboğazlar
make gorev-dogrula        # panonun bağımlılıklarını denetle
```

Görevler arasında **bağımlılık var**. Bir görevde `⛔ Önce bitmeli:` satırı
varsa, orada yazan görevler bitmeden o işe başlanamaz. Kullanıcı bloke bir işe
girmek isterse **uyar** ve listedeki bir sonraki yapılabilir işe yönlendir.
Boşta beklemek en pahalı şeydir.

Kritik yol: `H-01 (altın set) → S-12 (make eval) → S-13 (ablasyon) → ES-13 (sunum)`

---

## Sistem — kısa özet

`make crawl` → `make extract` → `make run`

| Katman | Yer |
|---|---|
| Şema sözleşmesi (**DONMUŞ**) | `src/schema.py` |
| Türkçe normalizasyon | `src/preprocessing/normalizasyon.py` |
| Toplama altyapısı (kayıt defteri · robots · nezaket) | `src/collector/toplayici.py` |
| Banka kazıyıcıları (Selenium, 9 banka) | `src/collector/kaziyicilar/` |
| Hibrit çıkarım | `src/extraction/{kural,llm,uzlastirici}.py` |
| Ajanlar (5, dördü LLM'siz) | `src/ajanlar/{uygunluk,elestirmen,yuklem,muhakeme,orkestrator}.py` |
| LLM sağlayıcı (EVREN / Ollama) | `src/extraction/saglayici.py` |
| Depolama | `src/depolama.py` |
| Karşılaştırma | `src/comparison/karsilastirma.py` |
| Chatbot + kalkan | `src/rag/chatbot.py` |
| Çok turlu sohbet (yuva devri) | `src/rag/baglam.py` |
| Kampanya konusu eşleşmesi | `src/rag/konu.py` |
| Chatbot boşluk taraması | `eval/soru_taramasi.py` |
| RAG gömme + kosinüs arama | `src/vektor_db.py` |
| Arayüz / API | `app/` · `src/api/sunucu.py` |
| Tetikleyici · dinleyici · keşif | `src/izleme/{tetikleyici,dinleyici,kesif}.py` |
| Canlı boru hattı sayfası | `app/pages/4_Boru_Hattı.py` · `app/akis.py` · `app/boru_durumu.py` · `app/is_yurutucu.py` |

Ayrıntı: [`docs/MIMARI.md`](docs/MIMARI.md) · Güncel ölçüm: [`docs/SONUCLAR.md`](docs/SONUCLAR.md) ·
Sprint 0 raporu (tarihsel): [`docs/SPRINT0_RAPORU.md`](docs/SPRINT0_RAPORU.md)

---

## Değiştirmeden önce bilinmesi gerekenler

**`src/schema.py` donmuştur — güncel sürüm `SEMA_SURUMU` sabitinde.**
Dört kişi bu şemaya karşı çalışıyor. Değiştirmek gerekiyorsa: takıma duyur,
`docs/kararlar/` altına ADR yaz, sürümü yükselt. Sessiz değişiklik dördünün
işini birden bozar.

Donma "hiç değişmez" demek değil, **ADR'siz değişmez** demek. Şimdiye kadar iki
kez, ikisi de usulünce: v1.0.0 → v1.1.0 ([ADR 006](docs/kararlar/006-sema-v1-1-uygunluk.md),
uygunluk koşulları) → v1.2.0 ([ADR 009](docs/kararlar/009-boyutlu-nicelik.md),
`Alan.birim`). İkisi de eklemeli; kayıtlar kendi `sema_surumu`'nu taşıdığı için
eski veri geçerli kalır.

**Toplama Selenium ile yapılır, banka başına kazıyıcı vardır (26 Ağu).**
Burada eskiden *«tek jenerik toplayıcı, banka başına özel kod YOK»* yazıyordu.
Doğru değildi: kampanya listeleri JS ile render edilip «daha fazla yükle»
butonuyla sayfalandığı için httpx yolu kartların çoğunu göremiyordu ve
`data/raw`'daki 1.024 kaydı fiilen **Selenium kazıyıcıları** üretti. Kod artık
veriyi üreten yolu gösteriyor: `src/collector/kaziyicilar/` altında dokuz sınıf.

Banka başına değişen tek şey **URL keşfidir** (`kampanya_urlleri()`). Gezme,
robots kapısı, nezaket, gövde ayıklama ve `HamKayit` üretimi `TemelKaziyici`'de
tektir — dokuz yerde tekrarlanmaz. Başlangıç adresleri kazıyıcıda değil
`data/banks.yaml` · `seed_urls` içindedir; `tools/robots_kanit.py` robots
kanıtını o listeden üretiyor, ikiye ayrılırsa kanıt yanlış adresleri denetler.

**Kanıtsız değer üretilemez.** Her `Alan` kaynağını, güvenini ve hangi katmandan
geldiğini taşır. `Alan(deger=2.05, yontem="belirtilmemis")` `ValueError` fırlatır.
Bu kısıtı gevşetme.

**Sayısal cevaplar yapısal veriden gelir, metin aramasından değil.** Chatbot'taki
sayısal doğrulama kalkanını (`sayisal_dogrulama`) zayıflatma — sistemin en özgün
iddiası bu. Kalkan yanlış pozitif veriyorsa çözüm kalkanı gevşetmek değil,
denetlenecek metni doğru seçmektir (`Cevap.dogrulanacak_metin`).

**Llama ve Gemma türevi model KULLANILMAZ.** Şartname 5.10 doğrudan bunları
hedefliyor. Yalnız Apache 2.0 / MIT (Qwen3.5, Qwen3.6). EVREN'deki `llm-large`
ve `llm-fast` ikisi de Qwen ailesi — yasağa takılmıyor.

**EVREN'de sunulan modeller uygun sayılır (ADR 013, 25 Ağu).** Servis, yarışmayı
düzenleyen SSB'nin tahsis ettiği servistir. Ama buna **yaslanmıyoruz**: fiilen
kullandığımız her modelin lisansı ayrıca teyitli — üç Qwen (Apache-2.0) ve RAG
gömmesi `bge-m3-embed` → `BAAI/bge-m3` (MIT). Jüriye verilen cevap duruş değil,
`docs/kanit/model-lisanslari.json`.

**Gömme için `bge-m3-embed` kullanılır** — lisanstan önce gelen bir sebeple:
ölçüldü, o uç **1024 boyut** veriyor (`vektor_db.BOYUT` ile birebir, ayrıca
BGE-M3 kimliğinin teyidi). Jenerik `embed` ucu **2560** veriyor, yani bu koda
hiç uymuyor. `embedding` diye bir uç ise EVREN'de **yok** — kodun eski
varsayılanı buydu ve sessizce 404 alıyordu.

**RAG'da harici vektör veritabanı YOK (ADR 014, 25 Ağu).** `qdrant.ssyz.org.tr`
DNS'te çözülmüyordu ve öyle bir servisin tahsis edildiğine dair belge yoktu.
15.151 paragraf yerel bir `.npz` dosyasında duruyor, arama numpy nokta çarpımı
— milisaniyeler. `make vektor` ile kurulur (~70 sn), `make durum` kurulu olup
olmadığını gösterir. **İndeks 26 Ağustos'ta depoya alındı** (32 MB): ağsız
kurulamıyor — gömmeler EVREN'den geliyor — dolayısıyla türetilmiş değil,
taşınması gereken bir varlık. Çevrimdışı pakete elle kopyalama adımı kalktı.

`make durum` artık indeksin **bayat olup olmadığını** da söyler: indeks
kurulduğu korpusun izini (`vektor_db.korpus_izi`) taşır, `make extract` ya da
kayıt silme sonrası iz tutmaz ve uyarı çıkar. Bu denetim olmadan chatbot
silinmiş kampanyaları kaynak göstererek cevap veriyordu.

**Tazelik dinleyicisi kendi tabanını kurar, tetikleyici KURULU DEĞİL (27 Ağu).**
`src/izleme/` değişikliği TESPİT eder, veriyi TAZELEMEZ — `data/raw` ve
`data/katilim.db` teslim için donmuş, kendiliğinden koşan bir iş `make eval`
sayıları ile `docs/SONUCLAR.md`'yi sessizce ayrıştırırdı. Üç şey ölçüldü:
9 bankanın **2'si** `ETag`/`Last-Modified` veriyor (7'si vermiyor, içerik özeti
şart) · `httpx` ile Selenium **7/9** bankada birebir aynı gövdeyi veriyor, bu
yüzden taban çizgisi **dinleyicinin kendi yolundan** kurulur (ilk koşu
değişiklik iddia etmez) · özet **bütün boşlukları atar**, çünkü Albaraka aynı
sayfayı tek boşluk farkıyla iki biçimde veriyor ve dakikada bir yanlış alarm
üretiyordu. Ayrıntı: `docs/kararlar/018-tetikleyici-dinleyici.md`.

**AYIKLAMA ÇIKARIMIN PARÇASI DEĞİL — `make extract` sonrası YENİDEN KOŞULUR
(28 Ağu).** Korpus 726'dan 1.019'a çıktığında sayının 98'i şişkindi: 95 kayıt
birebir kopya, 7'si kategori listeleme sayfası. Sebep basit ve kalıcı:
ayıklama araçları veritabanına yazar, `data/raw` DEĞİŞMEZ (izlenebilirlik
kanıtı odur), dolayısıyla her yeni `make extract` sildiklerini geri getirir.
Kopyanın kaynağı da kalıcı: kimlik URL'den türer (`Kampanya.kimlik_uret`) ve
bankalar aynı sayfayı iki adresten yayımlıyor — TOM Bank `/kampanyalar/X` ile
`/cok-kazananlar-kulubu-kampanya/X` (61 kayıt), Albaraka/Kuveyt/T. Finans'ta
takma adres ve `.aspx` harf varyantları. **Çıkarımdan sonraki sıra:**
`make yinelenenleri-ele uygula=1` → `make liste-sayfalarini-ele uygula=1` →
`make vektor` (korpus izi değişti) → `make kapsam veri-seti cikti-ornekleri
veri-kalitesi` → `make eval`. Altın set kayıtları iki araçta da muaf, ölçüm
zemini kaymaz. `make durum` iki sayıyı yan yana gösterir: **1.019 gezilen
sayfa, 921 kampanya** — ikisi de doğru, ikisi ayrı şey.

**İndekslenemeyen sayfa kampanya sayılmaz (27 Ağu).** Korpustaki 8 kayıt
Ziraat'in kategori LİSTELEME sayfasıydı (`/kampanyalar/market-ve-gida`,
`/kart-kampanyalari`), gövdeleri baştan sona «Son Gün …» tekrarı. Zararsız
değillerdi: `market-ve-gida` sayfasında dokuz ayrı tarih var ve
`kampanya_bitis` onlardan biri seçilmişti — var olmayan bir kampanyanın keyfî
bitiş tarihi, kaynak alıntısıyla birlikte. Ölçüt `vektor_db.paragraflara_ayir`
— **ikinci bir eşik yazılmaz**: RAG katmanı bu sekizi zaten dışarıda
bırakıyordu (indeks 726, veritabanı 734) ve ayrı bir eşik ikisinin sessizce
ayrışmasını garanti ederdi. Uzunluk aldatır: en büyüğü 3.970 karakter, en uzun
paragrafı 18. `make liste-sayfalarini-ele` (uygula=1 olmadan yalnız gösterir).
Yedisi silindi, biri **altın set muafiyetiyle** kaldı — Esra etiketlemiş,
silmek `make eval` zeminini kaydırırdı. `data/raw` DEĞİŞMEZ; `make extract`
kayıtları geri getirir. Silme sonrası korpus izi değişir, `make vektor` şart.

**Keşif diff'inin iki yönü AYRI tabana bakar (27 Ağu).** `src/izleme/kesif.py`
«listede olup elimizde olmayan kampanya var mı» sorusunu cevaplar — tazelik
dinleyicisi bunu yapısal olarak göremez. **YENİ** envantere (`data/raw`) karşı,
**KALDIRILMIŞ** ise ÖNCEKİ KEŞFE karşı hesaplanır. Sebebi ölçüldü: envanter
kampanya detayından ibaret değil — Albaraka'nın 136 kaydının 88'i ürün sayfası
ve `kampanya_urlleri()` onları hiç döndürmüyor; envantere karşı diff her koşuda
88 sahte «kaldırıldı» üretiyordu. YENİ yönü bu kirlilikten etkilenmez, envanter
fazlalığı o kümeyi yalnız küçültür. Sitemap ucuz kademe olarak denendi ve
reddedildi: kapsama 9 bankada %0–%100 arasında oynuyor. Ayrıntı:
`docs/kararlar/019-yeni-kampanya-kesfi.md`.

**PyArrow ayırıcısı `system` olmalı — `ARROW_DEFAULT_MEMORY_POOL`.**
PyArrow 25 macOS/arm64'te varsayılan `mimalloc` ile, thread yeniden
başlatılırken SIGSEGV veriyor. Streamlit her sayfa geçişinde yeni ScriptRunner
thread'i açtığı için `st.dataframe` olan bir sayfadan çıkınca **sunucu komple
ölüyor** — hata sayfası bile çıkmadan. Değişken üç yerde kurulu: `Makefile`
(`export`, tüm hedefler), `tests/conftest.py`, `app/Genel_Bakış.py`. Üçü de
`pyarrow` import'undan önce çalışmak zorunda; `pandas` pyarrow'u kendi
import'unda getirdiği için sonradan kurmak hiçbir şey değiştirmez. Bu satırları
«gereksiz» diye temizleme — 18 ve 27 Ağustos'ta iki kez ısırdı, ikincisinde
`make test`'i komple çökertti. Nöbetçi: `tests/test_arayuz_pyarrow_ayirici.py`.
Ayrıntı: [`docs/ARAYUZ_INCELEME.md`](docs/ARAYUZ_INCELEME.md) — «Ortam».

**Kâr payı karşılaştırması YALNIZ finansman kampanyalarını kıyaslar (27 Ağu).**
`kar_payi_orani` dolu 119 kaydın 110'u kart/alışveriş/«diğer» kampanyalarından
geliyor ve neredeyse hepsi sıfır — «vade farksız 6 taksit» promosyonları. O
sıfır ADR 012'ye göre doğrudur; yanlış olan onu bir ihtiyaç finansmanının
aylık %2,87'siyle aynı min-maks ölçeğine sokmaktı. Sonuç, hangi iki banka
sorulursa sorulsun aynı cümleydi: «iki banka EŞİT: aylık %0». Dokuz bankanın
beşinde kâr payı verisinin TAMAMI bu türdendi. Kapı
`comparison.karsilastirma.OLCUT_KAPSAMI`'nda; `sirala`, `avantaj_skorla` ve
chatbot aynı kapıdan geçer — kopya tutma. Kapsam dışı kayıt SİLİNMEZ, yalnız
sıralamadan düşer. Ayrıntı: [ADR 020](docs/kararlar/020-olcut-kapsami.md).

**Chatbot'un soru anlama sözlüğü ELLE YAZILMAZ (ADR 021, 27 Ağu).** Üç kaynak
var ve üçü de zaten depoda: ölçüt eşlemesi `docs/TERIM_SOZLUGU.md`'nin
«Sistemdeki karşılığı» sütunundan (`terim_sozlugu.alan_eslemesi`), segment
dağarcığı korpustaki `uygunluk.segment_detayi` değerlerinden, sistem sorusu
ayrımı Türkçe ikinci şahıs ekinden (`MUHATAP_EKLERI`). Elle yazılan dördüncü
bir liste, o listenin diğer üçüyle ayrışmasını garanti eder — nitekim
`_OLCUT_IPUCLARI` sabit sıradaydı ve «vade» dört harf olduğu için «toplam
maliyet»i yeniyordu. **Sıra uzunluktan gelir, elle yazılmış öncelikten değil.**

Sözlük kimlik kurmadığında onu da beyan ediyor ve chatbot buna uyar:
«`kar_payi_orani` ile KARIŞTIRILMAZ» → sıralama, ayrımı söyle · «tek alan
değil, hesaplanır» → formül, eksik girdiyi sor. **İlk cümlecik kimliği kurar**
(`odul_miktari`; `kar_payi_orani` VETOSU → terim ödüldür), **küçük harf şema
alanı, BÜYÜK HARF veto sabitidir**.

**Bütün ipucu eşleştirmeleri `terim_gecer`'den geçer.** Alt dize araması bu
depoda üç kez ısırdı: «ev» ~ «ters çEVrilir», «en» ~ «geçEN», «tanımla» ~
«tanımLAnmış». Yeni ipucu eklerken `in` kullanma.

**Sayı BİRİMİNE bağlanır — `para_ayristir` metnin ilk sayısını almaz.**
Eski kod «metinde TL geçiyor mu?» diye sorup ilk sayıyı alıyordu; ikisi
arasında bağ yoktu. «120 ay vadeli 1.000.000 TL konut finansmanı» → **120 TL**.
Profil ekranı bunu «120 TL · 120 ay» diye çözüp 357 kampanyayı uygun buluyordu.
`_AY_DESENI` vadeyi ilk günden birimine bağlıyordu; tutar bağlanmamıştı.
Çarpan sözcüğü de bağlıdır: «bin» artık metnin herhangi bir yerinden değil,
sayının yanından okunur. Çarpan **`tr_kucult` ile** çözülür, düz `.lower()`
ile değil — desen `MİLYON`u yakalıyor, `"MİLYON".lower()` `'mi̇lyon'` (i +
U+0307) veriyor ve sözlükte öyle bir anahtar yok. Sonucu sessiz bir yanlış
değil, `KeyError`'dı: kural katmanı çöküyor, `make kural-olc` altın sette hiç
koşamıyordu. Aynı dosyanın 22. satırında «TUZAK 1» diye yazılı.

**Türkçe ek listesi TEK KAYNAKTIR — `normalizasyon.TR_EKLER`.** Aday deseni
(`kural.D_VADE`, `kural.D_TAKSIT`) ile ayrıştırıcı (`_AY_DESENI`) aynı ekleri
tanımak zorunda: desen «6 taksitle»yi yakalayıp `vade_ayristir` onu tanımazsa
aday sessizce düşer. Vasıta hâli (`le|la`) listede yoktu ve tam olarak bu
oluyordu. İkinci bir kopya yazma.

**«6 taksit» hem vadedir hem taksit sayısıdır — ayırmak DENENDİ, ölçüldü,
geri alındı (27 Ağu).** `taksit_sayisi` 734 kaydın 734'ünde boştu ve sebebi
`_tek_atama` hakemliğiydi: iki kural da aynı span'ı üretiyor, mesafe ikisinde
de 0, beraberliği `KURALLAR` bildirim sırası çözüyor ve `vade_ay_max` önce
bildirildiği için taksit **hiçbir zaman kazanamıyordu**.

İlk çözüm «taksit»i `D_VADE`'den çıkarmaktı; gerekçe makuldü (353 vadenin
181'inin `ham_ifade`'sinde «taksit» geçiyor, 173'ü kart kampanyası). **Altın
set aksini söyledi:** dört etiketleyici bağımsız olarak «vade farksız 6
taksit» ifadesine `vade_ay_max = 6` yazmış. `make kural-olc` (deterministik,
LLM yok): vade F1 **0,7671 → 0,6866**, beş doğru pozitif yanlış negatife
döndü. «N taksitle öde» katılım bankacılığında N ay ertelenmiş ödemedir; ikisi
ayrı olgu değil, aynı olgunun iki adı.

Doğru çözüm ayırmak değil, hakemliği delmekti: `KuralTanimi.sahiplik_disi`.
`taksit_sayisi` vadeyle **yarışmaz, onu niteler** — makro-F1 birebir aynı
kaldı (0,7018). Tam koşuda ölçüldü (27 Ağu, 726 kayıt): alan **0'dan
215'e** çıktı (%30), **29'unda değer vadeden farklı**. Kazanç köken bilgisidir: `vade_ay_max=6` + `taksit_sayisi=6` «bu bir
kart taksidi» der, `vade_ay_max=36` tek başına «bu gerçek bir vade» der.
Bayrak DAR tutulur — sahiplik dışı kural kimsenin span'ını düşürmez de.

**`ollama_json_semasi().required` bir ÜRETİM KAPISIDIR (ADR 025, 27 Ağu).**
Liste yalnız `kampanya_turu` iken model 16 alandan 4'ünü döndürüyordu ve
`urun_turu` · `masraf_bilgisi` 734/734 kayıtta boştu. Alanı **isteme tanıtmak
tek başına yetmiyor** (10 kayıtta 0 dolu); kapının ikisi de açılmalı.
`required`'a eklenince `urun_turu` 9/10 doldu ve çıktı temiz. `masraf_bilgisi`
BİLEREK eklenmedi: zorlandığında 3/10 dolduruyor ve ikisi masraf değil vade
bilgisi. Alan altın sette etiketlenmiyor (ADR 008), yani o gürültüyü kimse
göremez — ölçülemeyen alanı zorlamak kanıtsız değer üretmektir. `SEMA_SURUMU`
yükselmedi: `required` modele ne SORULACAĞINI belirler, kaydın ne taşıyacağını
değil.

**Müşteri tipi eksikse SORULMAZ, tutar ve vade eksikse sorulur.** Ayrım
tahmin edilenin sonuca ne yaptığıdır: tutar ve vade taksit ile toplam maliyet
formülüne girer, uydurulan değer cevaptaki her sayıyı yanlışlar. Müşteri tipi
hiçbir hesaba girmez, yalnız süzer — bilinmiyorken süzmemek dürüst olanıdır ve
cevapta «müşteri tipi belirtilmedi» diye yazılır. Bu olmadan şartname jürisinin
soru havuzundaki «120 ay vadeli 1.000.000 TL konut finansmanı için en düşük kâr
payı oranını hangi banka sunuyor?» sorusuna cevap değil soru dönüyordu.

**Terim eşleştirmesi ALT DİZE değil, sözcük başıdır.** `chatbot.terim_gecer`
baştan bağlar, sonu serbest bırakır — Türkçe eklemeli olduğu için «vade»
«vadesi»ni bulmalı. Alt dize araması sessizce yanlış eşleşiyordu: ürün
sözlüğündeki «ev» (konut) «ters çEVrilir» içinde bulunuyor ve «Python'da liste
nasıl ters çevrilir?» sorusu üç kaynakla konut kampanyası dökümü alıyordu.
Üç harf ve altı tam sözcük aranır, yoksa «ev» «evrak»ı da yakalar.

**Yapılmamış sıralama YAPILMIŞ gibi sunulmaz; bilinen alan SAKLANMAZ
(27 Ağu).** `_profil_cevabi` başlığı koşulsuz «Toplam maliyete göre sıralı»
yazıyordu — hiçbir kalemin maliyeti hesaplanamadığında bile. Ölçüldü: Kuveyt
Türk ve Emlak Katılım'ın **11 konut kaydının hiçbirinde kâr payı oranı
yayımlanmamış** (sayfalardaki yüzdeler kredi/değer oranı ve tahsis ücreti;
oran bankanın hesaplama aracının arkasında). Yani veri doğruydu, kusur
cevaptaydı: beş kalem de tek satırla geçiştiriliyor, o kayıtlarda DOLU olan
tahsis ücreti · vade · tutar hiç gösterilmiyordu ve kullanıcı «bu sistemde
hiçbir bilgi yok» sanıyordu. Gösterilecek alanlar elle yazılmaz,
`ALAN_YONLERI`'nden türer; birim `TEK_BIRIMLI_ALANLAR`'dan çözülür — birimsiz
gösterim `%0,50`'yi «0,50 TL» yazardı (bulgu 1.1).

**Kullanıcıdan bilgi isteyen cevap, HANGİ YUVAYI istediğini beyan eder
(ADR 024, 27 Ağu).** `Cevap.beklenen_yuvalar` — iki üretici var (profil kolu
ve hesaplanan ölçüt cevabı) ve ikisi de aynı ölçüyü kullanır
(`chatbot.eksik_nicelikler`). Beyan olmadan sistem kendi sorduğu sorunun
cevabını duyamıyordu: «toplam maliyet için anapara gerekiyor» → «1.000.000 TL»
→ *«bu soru sistemin kapsamı dışında»*. Dayanak kapısının muafiyeti DAR —
yalnız `alan_disi_soru` yarısı, yalnız SORULAN yuvayı dolduran nicelik geldiğinde.
Muafiyetin dayanağı metin değil, konuşma durumudur.

**Kapılar dilbilgisine bağlanır, sözcük listesine değil (ADR 024).**
`SIFAT_FIIL_EKLERI` — «olan banka», «sunan banka», «veren banka» bir kurumu
ADLANDIRMAZ, niteler. Liste tutulsaydı «olan» eklenir, «sunan» unutulurdu;
nitekim `_BELIRTEC_SOZCUKLERI`'nde «olan» yoktu ve «kâr payı en düşük OLAN
BANKA…» sorusu dokuz bankalık kibar ret alıyordu. `MUHATAP_EKLERI` ile aynı
refleks. Dört harf sınırı şart: «en» iki harftir.

**Sistem sorusunun kendi niyeti var: `Niyet.SISTEM_SORGUSU`.** Etiket cevabın
kendisiyle çelişemez — `_sistem_cevabi` «kibar ret DEĞİL, doğru adres» diyor
ama `KAPSAM_DISI` etiketiyle dönüyordu ve arayüzdeki rozet «Kibar ret» yazıyordu.

**Yeni ölçüt yazımı SÖZLÜĞE eklenir, koda değil.** «Toplam maliyet» tanınmıyordu
çünkü sözlükte yalnız resmî ad vardı («Finansman Maliyeti»); eğik çizgi zaten eş
anlamlı yazım ayıracıdır. **Sözlük gövdesi kullanıcıya OKUNUR** — oraya gerekçe
yazma, chatbot onu cevap diye okur. Tanım sözlükte, gerekçe ADR'de.

**Kampanyanın KONUSU dördüncü süzgeçtir; sözlüğü korpustur (ADR 026, 28 Ağu).**
«TOM Katılım'ın **akaryakıt** kampanyasında ne kadar iade var?» sorusuna A101
meyve-sebze kampanyasının 250 TL'si dönüyordu — doğru kayıt aynı bankada,
aynı kümedeydi. Banka · ürün · segment tanınıyor, kampanyanın KONUSU hiçbir
yerde okunmuyordu ve kararı `doluluk_orani` veriyordu. **Kalkan bunu göremez:**
o «bu sayı kayıtta var mı?» diye sorar, «bu kayıt sorulan şey mi?» diye sormaz.

Konu sözlüğü ELLE YAZILMAZ — ürün sınıfı şemada sonludur, kampanya konusu
değildir; yazılan liste ilk `make crawl`'da geride kalır. Üç ölçüm:
**kampanyanın adı adresinin SON dilimidir** (gövde başka kampanyalardan söz
eder: TOM'un 10 kaydı «akaryakıt» diyor, adında taşıyan 4'ü · LLM özeti soru
dilini yankılar: «güncel» 4, «belirli» 24 kayda eşleşiyordu, adres diliminde
ikisi de sıfır) · **ayırt edicilik `KONU_TAVANI`'yla ölçülür** (%3'ün üstü
kampanyayı değil kampanyacılığı adlandırır: «varan» 114, «özel» 77) ·
**süzgeç birleşimdir** (üç konu sayan soru, üçünü birden taşıyan kampanyayı
sormaz). Sıra `konu → sorulan alan → güncellik → ölçüt değeri → doluluk`:
konu bir tercih değil KİMLİK kısıtıdır, yoksa «akaryakıt kampanyasında ne
kadar iade» sorusu bankanın EN YÜKSEK ödülünü gösterir.

Konu sözcüğü ARTIKTIR: sistemin zaten çözdüğü her şey (`_cozulmus_sozcukler`)
düşürülür, kalanı iki dilbilgisi kapısı eler. **`sifat_fiil_mi` burada
KULLANILAMAZ** — o kural yalnız «banka»nın önündeki sözcüğe bakar; her
sözcüğe uygulanınca korpustan 43 konu adı yutuyordu («restoran», «worldpuan»
ve bütün ayrılma hâlleri: «mağazadan», «marketten»). Ayrım gövde
uzunluğundadır (`AZAMI_FIIL_GOVDESI`): fiil gövdesi kısadır («ol-», «ver-»),
ad uzun gövde bırakır («restor-»).

**`make chatbot-tarama` — sorular korpustan ÜRETİLİR.** 248 soru (dokuz banka ×
beş ölçüt × altı ürün × banka başına üç KONU × yazım biçimleri), beklenen cevap
bilinmez, yalnız patoloji aranır (kapsam dışı reddedilen meşru soru · ölçüt
kayması · yanlış banka · yanlış KAMPANYA · kalkan reddi · sızan kapsam dışı).
Elle yazılan 31 soruluk set
(`make chatbot-test`) derindir ama kapsamı yazıldığı kadardır; ADR 024'ün iki
kusurunu da göremezdi. Ağ kullanır, o yüzden `eval/` altında.

**Eşleştirme ve yön TEK KAYNAKTAN okunur (ADR 023, 27 Ağu).** Üç kopya
temizlendi, üçü de aynı deseni tekrarlıyordu:

* **Banka eşleştirmesi tip bağımsızdır** — `chatbot.sorulan_bankalar(soru,
  banka_adlari)`. `_bankalari_bul` (kayıt) ve orkestratördeki `_banka_suz`
  (kampanya) onun sarmalayıcısı. Profil kolunda banka süzgeci YOKTU: «Albaraka'dan
  1.000.000 TL konut» dokuz bankayı sıralıyordu. **Banka süzgeci üründen ÖNCE
  koşar** — sonra koşarsa ad kümesi ürünle daralır ve sorulmayan bankalar geri gelir.
* **«Hangi uç avantajlı» yalnız `karsilastirma.ALAN_YONLERI`'nde beyan edilir.**
  Sıralama, avantaj skoru ve chatbot'un tekil cevabı oradan okur. Yön hiçbir
  kaynakta yoksa (kullanıcı da söylememişse) SIRALAMA YAPILMAZ — uydurulmuş bir
  yön, sessizce yanlış kaydı vitrine koymaktır. Tekil cevap sıralamayla aynı
  yönü kullanmak zorunda: «en uzun vadeyi kim veriyor?» ile «Albaraka'nın vadesi
  ne?» aynı kaydı göstermeli. ADR 020'nin kapsam kapısı da sıralamaya uygulanır.
* **Kesme işareti özel adı EKİNDEN ayırır** (`normalizasyon.kesmeden_ayir`).
  `arama_anahtari` kesmeyi siler — tokenizasyon için doğrusu odur — ve
  `_bankalari_bul`'un `anahtar.replace("'", " ")` satırı bu yüzden ÖLÜYDÜ:
  «Albaraka'dan» hiçbir bankaya eşleşmiyordu. Çözüm **ek serbestliği DEĞİL**:
  baş bağlayıp sonu serbest bırakmak «emlakçı»yı Türkiye Emlak'a bağlardı ve
  `YAKINLIK_ESIGI` o eşleşmeyi ölçerek dışarıda bırakmıştı.

**Sohbet hafızası YUVA DEVRİDİR, sohbet geçmişi değil (ADR 022, 27 Ağu).**
Chatbot deterministik: cevabı üreten şey kod, doldurulacak bir istem yok.
Önceki turları bir dil modeline vermenin karşılığı yok; karşılığı olan şey
anafora çözümü — önceki turda ÇÖZÜLMÜŞ varlıkları (banka · ürün · ölçüt · yön ·
tutar · vade) sonraki turun BOŞ yuvalarına taşımak. Devir metne yazılır, çünkü
soruyu okuyan on ayrıştırıcının hepsi metni okuyor; hangi yuvanın boş olduğuna
ayrıştırıcının KENDİSİ karar verir (`_bankalari_bul`), ikinci bir kopya yok.

Ölçülen kusur şuydu: «1.000.000 TL konut» → sistem «vade eksik» diye SORUYOR,
gelen «120 ay vade» cevabı muhakeme ajanına hiç ulaşmıyordu. **Bir arayüzün
kullanıcıya soru sorması, o cevabın gideceği yuvanın var olduğunu taahhüt
etmektir.**

**Yuvalar: banka · ürün · KONU · ölçüt · yön · tutar · vade.** Konu yuvası
28 Ağustos'ta eklendi (ADR 026 §8): tek turda doğru kampanyayı bulan sistem
ikinci turda onu unutuyor, bankanın 123 kaydına geri açılıyordu — «hafızası
yok» denen davranış buydu. Üç kısıt: yuva ÇÖZÜLMÜŞ sözcükle dolar
(«peki» konu değildir, korpusta karşılığı yok) · ürün adlandırılırsa konu
DÜŞER, banka değişirse DÜŞMEZ · beyan gösterim biçimiyle yazılır
(«akaryakıt», «akaryakit» değil).

**Devir yuvayı DOLDURUR, sorunun ŞEKLİNİ değiştirmez — kapı `_sorulan_olcut`
DEĞİL, `alan_adlandirilmis`.** «Karaca kampanyası kaç taksit?» → «ne kadar
indirim var?» sorusunda devralınan «Vade» kullanıcının açıkça yazdığı alanı
eziyordu: `indirim_orani` beş kıyas ölçütünden biri olmadığı için yuva BOŞ
sanılıyor. Alan dağarcığı türetilir — sözlüğün şema eşlemesi + etiketlerde
YALNIZ BİR KEZ geçen sözcükler; «kampanya» dört etikette geçtiği için
kendiliğinden düşer.

Dört kısıt gevşetilmez: devir yalnız BOŞ yuvaya (soruda yazılan kazanır) ·
kapsam kapıları HAM soruya çalışır, devir sonradan (yoksa alakasız soru banka
devralıp kapsam içi sayılır) · tutar/vade yalnız PROFİL KİPİNDE devrolur ·
devralınan her yuva cevapta beyan edilir ve beyan kalkandan geçer. Ayrıca
**korpusa sorulan soru hiçbir yuva devralmaz** ve **yön yalnız ölçütle
birlikte devrolur** — ikisi de ölçülmüş hatanın karşılığı: devir bir yuvayı
DOLDURUR, sorunun ŞEKLİNİ değiştirmez.

`make eval` tek turlu koşuyor; bağlamsız çağrı birebir eski cevabı verir ve
bunu bir nöbetçi denetliyor (`test_baglamsiz_cagri_davranisi_degistirmez`).

**Sessiz yutma yasak.** Gömme hatası da, arama hatası da fırlatılır. Bu kural
bedava öğrenilmedi: `embed_text` sıfır vektörü, `vektor_ara` boş liste
döndürdüğü için RAG dört gün hiç çalışmadan çalışıyor göründü. Sıfır vektörü de
uydurma bir değerdir — `Alan(deger=..., yontem="belirtilmemis")` neden
patlıyorsa o da patlamalı.

**Arayüzden koşan boru hattı DEMO ALANINA yazar (26 Ağu).** «Canlı Boru Hattı»
sayfası (`app/pages/4_Boru_Hattı.py`) gerçek kazıyıcıyı ve gerçek çıkarım hattını
sürer, ama hedefi `data/demo_raw/` + `data/demo/demo.db`'dir. Üretim verisine
ancak sekmedeki **kapalı gelen** onay kutusu işaretlenirse dokunulur. Demo kipi
sayfa SAYISINI kısar (`topla(azami_sayfa=...)`), temposunu değil — nezaket kuralı
ve robots kapısı demoda da işler. Animasyon koşunun kendi olaylarından beslenir;
sahte ilerleme, sahte sayaç, uydurma gecikme yoktur.

**Streamlit sayfasında `@dataclass` TANIMLAMA — bedeli ölçüldü.** Sayfa betiği her
çizimde baştan koşar, yani orada tanımlı bir sınıf her koşuda YENİ nesne olur;
`st.session_state`'te duran örnek eski sınıftan geldiği için `isinstance` **False**
döner ve biriken durum sessizce sıfırlanır. Ölçüldü: canlı sayaç iki kayıt
işlenmişken «1 / ?» kaldı. Bu yüzden durum sınıfları `app/boru_durumu.py`'de,
modül düzeyinde durur. Aynı sebeple bitmiş işin sonucu yalnız canlı parçada değil,
betiğin **her tam koşusunda** devralınır (`_bekleyen_isi_devral`) — sayfa
değiştirilip dönüldüğünde sonuç kaybolmasın diye.

Yeni bağımlılık eklendiğinde `make lisanslar`, yeni model eklendiğinde
`make lisanslar-teyit` çalıştır (lisansı HF'ten çeker, tutmazsa kırılır).

**Çıkarım EVREN'de koşuyor (24 Ağu).** T.C. Cumhurbaşkanlığı SSB'nin yarışmaya
tahsis ettiği servis. `llm-large` = **`Qwen/Qwen3.5-122B-A10B`** — MoE, 122B
toplam / 10B aktif, BF16 (kuantizasyon yok), 262.144 token bağlam, tensör
paralelliği 4. Lisans **Apache-2.0**, iki kaynaktan teyitli (EVREN model kartı
+ HF deposu) — şartname 5.10 kanıtı `docs/SARTNAME_UYUM.md`'de.
Ölçülen: 13 sn/kayıt → 0,43 sn/kayıt (16 işçi), doluluk kırpılan kayıtlarda
+8 puan. Sağlayıcı katmanı `src/extraction/saglayici.py`; orada ölçülmüş **üç
sessiz tuzak** yazılı (`chat_template_kwargs` üst seviyede olmalı, `guided_json`
yok sayılıyor, `max_tokens` 4096) — okumadan o dosyaya dokunma.

**Yerel yol silinmedi, yedektir.** `make extract-yerel` (`LLM_SAGLAYICI=ollama`)
aynı kod yolunu yerel Ollama ile koşar: EVREN düştüğünde ve hava boşluğu
demosunda. Yerelde `CIKARIM_ISCI=1` zorunlu ve **Streamlit'i kapat** — 8 GB
makinede aynı anda açık olunca kayıt başına 13 saniye yerine 2,5 dakika sürer
(bellek takası). EVREN'de bu kısıtların ikisi de yok, iş bizim makinemizde değil.

**EVREN bayt düzeyinde deterministik DEĞİL — ölçüldü.** `temperature=0` ve sabit
tohuma rağmen aynı girdi 5 kayıttan 3'ünde farklı çıktı verdi (ortak vLLM
sunucusunda sürekli yığınlama).

**SAPMA SAYISAL ALANLARA DA VURUYOR — 25 Ağustos'ta 98 kayıtta ölçüldü.**
Buradaki eski kayıt *«8 kayıt × 4 koşuda oynayan alanların tamamı serbest
metindi; sayısal ve enum alanlarda sıfır sapma»* diyordu. O ölçüm 8 kayıtlıktı
ve **yanıltıcı çıktı.** Altın setin 98 kaydı aynı kodla iki kez çıkarıldığında:

```
oynayan hücre: 7 / 784 (%0,9) — hepsi sayısal/enum
  kampanya_turu 2 · tahsis_ucreti 2 · kar_payi_orani 1 · vade_ay_max 1 · masrafsiz_mi 1
örnek: tahsis_ucreti 0,5 → 20,0   ·   vade_ay_max 84 → 60
makro-F1: koşu-1 0,735   koşu-2 0,724      ← aynı kod, aynı girdi
```

**Sonuç: `make eval` sayısı ±0,01 gürültü taşır.** Sunumda «makro-F1 0,72»
demek doğrudur, «0,724» demek yanlış bir kesinlik iddiasıdır. İki koşunun
farkını iyileşme sanmayın — bir değişikliğin etkisi ancak bu bandın dışındaysa
gerçektir.

`docs/SONUCLAR.md` sayıları işlenmiş veritabanından üretildiği için o dosya
kendi içinde tutarlı kalır; yeniden üretilen şey veritabanının kendisi değildir.
Bayt düzeyinde tekrarlanabilirlik şartsa: `LLM_SAGLAYICI=ollama`.

---

## Komutlar

```bash
make kur          # kurulum
make crawl        # kampanya topla  [Chrome gerekir; gorunmez=1 headless, banka=0212 tek banka]
make extract      # çıkarım (kural + LLM) -> SQLite  [EVREN]
make extract-yerel      # aynı çıkarım, yerel Ollama ile (yedek / hava boşluğu)
make saglayici-dogrula  # EVREN bağlantısı + şema kısıtı sınaması
make durum        # kaç kampanya, kaç banka, RAG indeksi kurulu mu
make vektor       # RAG vektör indeksini kur (gömme + kosinüs, ~70 sn)
make tazelik      # kampanya sayfaları değişmiş mi (G-17) [adet=N demo=1]
make kesif        # listede olup elimizde olmayan kampanya var mı (G-19) [banka=X]
make run          # Streamlit arayüzü
make test         # testler (1761 test)
make eval         # metrikler -> docs/SONUCLAR.md
make chatbot-tarama # chatbot boşluk taraması (248 üretilmiş soru) [adet=N]
make ablasyon     # 5 kollu ablasyon (katman + ajan katkısı), ~25 dk
make uygunluk-goc # mevcut kayıtlara uygunluk koşullarını yaz (A-08, LLM'siz)
make kapsam       # banka bazlı kapsam raporu -> docs/KAPSAM_RAPORU.md
make cikti-ornekleri    # model çıktı örnekleri -> docs/CIKTI_ORNEKLERI.md
make veri-seti    # yayınlanabilir veri seti + veri kartı -> data/exports/
make sunum        # docs/sunum/sunum.html -> Svartal_Sunum.pdf (9 sayfa, acik tema)
make lisanslar    # bağımlılık + model lisans raporu
make lisanslar-teyit    # aynı rapor + model lisanslarını HF'ten teyit et (ağ)
make kanit        # veri toplama etiği kanıtları (robots günlüğü + KVKK taraması)
make gorev ad=X   # görev durumu
```

Değişiklikten sonra: **`make test` ve `make lint` yeşil olmalı.**
