# Plan — «Elimizde olmayan yeni kampanya var mı?»

> Durum: **Adım 0 ölçüldü, Faz 1 uygulandı** (27 Ağustos 2026).
> Ölçüm sonuçları bölüm 4B'de — tasarımı değiştirdiler.
> Sahibi: Görkem · Pano karşılığı: henüz açılmadı (öneri: **G-19**)

## 1. Bağlam — iki ayrı soru, biri hâlâ cevapsız

G-17 ile gelen mekanizma şu soruyu cevaplıyor:

> **«Elimizdeki 1.024 sayfa son çekimden beri değişti mi?»**

Bu soru değerli ve mekanizma **yerinde kalacak** (Boru Hattı → *3 · Veri
Tazeliği*). Ama asıl istenen soru bu değildi:

> **«Son çekimden bu yana YENİ kampanya çıktı mı? Elimizde hiç olmayan.»**

İkisi farklı kümelere bakar ve tazelik denetimi ikincisini **yapısal olarak
göremez**: dinleyici yalnız elindeki URL listesini yoklar. Envanterde olmayan
bir kampanyanın URL'i hiç bilinmediği için hiç ziyaret edilmez.

| Soru | Bakılan küme | Mekanizma | Durum |
|---|---|---|---|
| Elimizdeki bayatladı mı? | envanterdeki URL'ler | tazelik dinleyicisi | ✅ var (G-17) |
| **Yeni kampanya çıktı mı?** | **bankanın güncel listesi** | **keşif farkı** | ❌ **bu plan** |
| Kampanya kaldırıldı mı? | ikisinin farkı | keşif farkı | ❌ bu plan (bedava yan ürün) |

---

## 2. Çekirdek fikir — envanter × keşif farkı

Bankanın kampanya **listesini** yeniden keşfet, elimizdeki URL envanteriyle
karşılaştır. Üç küme çıkar:

```
     BANKANIN GÜNCEL LİSTESİ              BİZİM ENVANTERİMİZ
     (kampanya_urlleri() çıktısı)          (data/raw'daki URL'ler)
              ┌─────────────┐         ┌─────────────┐
              │             │         │             │
              │    YENİ     │ ORTAK   │  KALDIRILMIŞ│
              │  listede ✓  │ ikisinde│  bizde ✓    │
              │  bizde ✗    │  de ✓   │  listede ✗  │
              │             │         │             │
              └─────────────┴─────────┴─────────────┘
                    ▲            ▲            ▲
                    │            │            │
              ASIL HEDEF   tazelik denetimi  süresi geçmiş
                             burayı yokluyor  olabilir
```

**Kritik nokta: detay sayfası ÇEKİLMEZ.** Yalnız liste keşfi koşar
(`kampanya_urlleri()`), dönen URL kümesi karşılaştırılır. Tam toplamanın
pahalı kısmı detay sayfalarıdır (URL başına ≥2 sn nezaket + 2 sn yerleşme);
keşif onun küçük bir bölümü.

---

## 3. Neden Selenium şart

Kampanya listeleri JS ile render edilip «daha fazla yükle» butonuyla
sayfalanıyor. Bu, jenerik `httpx` toplayıcısının kaldırılma gerekçesinin
kendisi (`src/collector/toplayici.py` başlığındaki TARİHÇE notu). Liste
keşfi için tarayıcı **zorunlu**.

G-17'deki ucuz yol (koşullu GET + içerik özeti) burada işe yaramaz: o yol
**bilinen bir URL'i** yokluyor. Bilinmeyeni keşfetmek listeyi render etmeyi
gerektiriyor.

> **Ama bir ucuz kademe ihtimali var ve ÖLÇÜLMELİ** — bkz. Adım 0.

---

## 4. ADIM 0 — Önce ölç, sonra yaz (bu plan buradan başlar)

Kod yazmadan önce üç şey ölçülmeli. Hiçbiri tahminle geçilmemeli.

### 0.1 — Bu özellik gerçekten bir şey buluyor mu?

**En önemli ölçüm.** Envanter 26 Ağustos'ta donduruldu. Tek bir banka için
keşfi koştur, envanterle karşılaştır:

```
Beklenen çıktı:  Albaraka — listede 51, envanterde 48, YENİ 3, KALDIRILMIŞ 0
```

**Eğer dokuz bankada da YENİ = 0 çıkıyorsa**, özellik teslim için bir şey
üretmiyor demektir; o zaman jüriye «mekanizma var, şu an yeni kampanya yok»
denir — bu da dürüst ve savunulabilir bir sonuçtur, ama önceden bilinmeli.

### 0.2 — Keşif ne kadar sürüyor?

Banka başına `kampanya_urlleri()` süresi ölçülmeli. Kaba beklenti (kod
okunarak, **ölçülmedi**): liste açılışı ~5 sn + «daha fazla» turu başına
~5–8 sn. Albaraka'da 48 kampanya ≈ 6 tur ≈ **35–50 sn**.

Dokuz banka toplam **5–10 dakika** bandında olmalı. Tam toplama ~35 dakika
olduğuna göre keşif kabaca **1/5 – 1/7 maliyetli**. Bu oran doğrulanmadan
arayüze «hızlı denetim» diye yazılmamalı.

### 0.3 — Ucuz kademe var mı? (sitemap / feed / JSON ucu)

Bankaların `sitemap.xml`, RSS ya da liste sayfasını besleyen bir JSON ucu
sunup sunmadığı yoklanmalı. Varsa o banka için **Selenium'suz keşif** mümkün
olur ve maliyet saniyelere iner.

G-17'de aynı türden bir ölçüm yapıldı ve sonuç tasarımı değiştirdi (9 bankanın
yalnız 2'si `ETag` veriyordu). Burada da aynı disiplin: **önce yokla, sonra
tasarla.**

> Sonuç ne çıkarsa çıksın `docs/kararlar/019-*.md` içine yazılmalı — «denedik,
> yoktu» da bir bulgudur.

---

## 4B. ADIM 0 SONUÇLARI (27 Ağustos — ölçüldü, tasarımı DEĞİŞTİRDİ)

### 0.3 — Ucuz kademe: sitemap birincil kaynak OLAMAZ

8/9 banka `sitemap.xml` beyan ediyor. Ama kapsama ölçüldü — envanterdeki
kampanya URL'lerinin kaçı sitemap'te var:

| Banka | Kapsama | Banka | Kapsama |
|---|---|---|---|
| Hayat Finans | %100 | Albaraka | %43 |
| Emlak Katılım | %96 | Vakıf Katılım | %43 |
| Kuveyt Türk | %89 | Türkiye Finans | **%0** |
| | | Ziraat Katılım | **%0** |
| | | Dünya Katılım | **%0** (CMS sunucusu) |
| | | TOM Katılım | sitemap yok |

**Kısmi kapsama bu iş için yokluktan kötüdür.** %43 kapsayan bir sitemap'i
keşif kaynağı yapmak envanterin %57'sini «kaldırılmış» diye raporlardı.
Karar: **keşif Selenium ile yapılır**, sitemap kullanılmaz.

### 0.1 / 0.2 — Keşif bir şey buluyor, ama diff'in bir yönü güvenilmez

Gerçek keşif koşuldu (yalnız `kampanya_urlleri()`, detay sayfası çekilmedi):

| Banka | Süre | Listede | Envanterde | YENİ | KALDIRILMIŞ |
|---|---|---|---|---|---|
| Hayat Finans (0212) | **9 sn** | 13 | 16 | **1** | 4 |
| Albaraka (0203) | **81 sn** | 48 | 136 | 0 | **88** |

**Hayat Finans'ta gerçek bir yeni kampanya bulundu:**
`hayatfinans.com.tr/kampanyalar/biz-kart-ile-okula-donus-kampanyasi` —
envanterde yok. Özellik işe yarıyor.

**Ama Albaraka'nın 88 «kaldırılmış»ı sahte.** Bakıldı: envanterdeki
`/bireysel/finansmanlar/...` adresleri **ürün sayfaları**, kampanya detayı
değil. `kampanya_urlleri()` onları tasarımı gereği hiç döndürmüyor. Hayat
Finans'ın 4'ü de aynı türden (`/kampanyalar`, `/kartlar` — liste sayfaları).

### Tasarım kararı — diff'in iki yönü AYRI kaynaklara karşı çalışır

| Yön | Karşılaştırma tabanı | Güven | Gerekçe |
|---|---|---|---|
| **YENİ** | `data/raw` envanteri | ✅ yüksek | Keşifte çıkıp elimizde olmayan gerçekten yenidir. Kirli envanter YENİ'yi yalnız küçültür, şişirmez. |
| **KALDIRILMIŞ** | **önceki KEŞİF koşusu** | ✅ yüksek | Elmayla elma: aynı mekanizmanın iki koşusu. İlk koşu taban kurar, iddia etmez. |
| Envanterde olup listede yok | `data/raw` | ⚠️ düşük | Ürün/liste sayfalarıyla dolu. Yalnız BİLGİ olarak, açık uyarıyla gösterilir. |

Bu, ADR 018'deki dersin aynısı: **karşılaştırma, karşılaştırılanı üreten yola
karşı yapılır.** Orada Selenium gövdesi ile `httpx` gövdesi karışmasın diye
taban kendi yolundan kurulmuştu; burada `data/raw` ile `kampanya_urlleri()`
karışmasın diye kaldırılmış yönü kendi tabanına bakıyor.

---

## 5. Envanterin bugünkü hâli — çözülmesi gereken kirlilik

Ölçüldü (27 Ağu, `data/raw`):

| | |
|---|---|
| Toplam kayıt | **1.024** |
| Sorgu parametreli URL | **155** |
| Liste sayfası gibi görünen URL | **174** |

Banka başına: `0203` 136 · `0205` 209 · `0206` 173 · `0209` 217 · `0210` 36 ·
`0211` 80 · `0212` 16 · `0213` 103 · `0214` 54

**Sorun:** envanterde kampanya DETAY sayfası olmayan URL'ler var. Örnekler:

```
https://www.albaraka.com.tr/tr/kampanyalar                        ← liste sayfası
https://www.albaraka.com.tr/tr/kampanyalar?slug=bireysel          ← liste filtresi
https://www.albaraka.com.tr/tr/kampanyalar?slug=gecmis-kampanyalar ← GEÇMİŞ kampanyalar
https://www.vakifkatilim.com.tr/tr/kendim-icin/kampanyalar?page=3 ← sayfalama
```

Bu kirlilik diff'i doğrudan bozar:

- Liste sayfası her keşifte **ORTAK** çıkar → zararsız ama gürültü.
- `?page=3` gibi sayfalama URL'leri liste uzayınca **KALDIRILMIŞ** görünür →
  yanlış alarm.
- `gecmis-kampanyalar` zaten süresi geçmiş kampanyaları taşıyor; oradan gelen
  bir URL «yeni» sanılabilir.

**Karar (plan): envanter süzülür, ama `data/raw` DEĞİŞTİRİLMEZ.** Süzgeç
diff sırasında uygulanır ve neyi elediği raporlanır. Donmuş veriye
dokunulmaması G-17'nin de kuralıydı.

---

## 6. URL eşleştirme tuzakları

Diff bir küme farkı; kümenin elemanı **normalize edilmiş URL** olmalı.

| Tuzak | Örnek | Karar |
|---|---|---|
| Fragment | `.../kampanya#detay` | atılır (`benzersiz()` zaten yapıyor) |
| Sondaki `/` | `.../kampanya` vs `.../kampanya/` | tekilleştirilir |
| İzleme parametresi | `?utm_source=...`, `?gclid=...` | atılır |
| **Anlamlı parametre** | `?slug=bireysel`, `?page=3` | **atılamaz** — sayfayı belirliyor |
| Şema/host farkı | `http` vs `https`, `www` var/yok | tekilleştirilir |
| Büyük/küçük harf | yol kısmında | **dokunulmaz** (sunucu ayırt edebilir) |

> ⚠️ İzleme parametresi ile anlamlı parametreyi ayırmak **liste tabanlı**
> olmalı (bilinen izleme anahtarları atılır, gerisi korunur). Ters yönde
> «tanımadığımı at» kuralı, `?slug=` gibi anlam taşıyan parametreleri silip
> farklı kampanyaları tek URL'e indirirdi.

### Slug değişimi — «yeni» sanılan eski kampanya

Banka kampanyanın adresini değiştirirse (`.../yaz-kampanyasi` →
`.../yaz-kampanyasi-2026`) diff bunu **YENİ + KALDIRILMIŞ** çifti olarak
görür; oysa aynı kampanyadır.

**Öneri:** rapor bunu iddia etmesin, **işaretlesin**. Aynı koşuda hem YENİ hem
KALDIRILMIŞ çıkan bir bankada, iki URL'in son yol parçası birbirine çok
benziyorsa (`difflib` oranı ≥ 0,8) satır *«muhtemelen adres değişikliği»*
notuyla gösterilir. Karar operatörün.

> Daha kesin yol (başlık/içerik karşılaştırması) **detay sayfası çekmeyi**
> gerektirir; bu planın kapsamı dışında, Faz 2'ye bırakıldı.

---

## 7. Tasarım

### 7.1 Yeni modül: `src/izleme/kesif.py`

`src/izleme/` altında, dinleyicinin yanına. Aynı olay/iptal deseni.

```
KesifHedefi        banka + kazıyıcı sınıfı
KesifOlayi         asama: "banka_basladi" | "liste_yuklendi" | "banka_bitti" | "hata"
                   banka_kodu · banka_adi · bulunan · yeni · kaldirilmis · mesaj
KesifSonucu        banka başına: bulunan / yeni / kaldirilmis / ortak / sure
KesifOzeti         koşu geneli + banka başına sonuçlar + elenen (kirlilik süzgeci)

envanter_oku(dizin)            -> dict[banka_kodu, set[normalize URL]]
url_normalize(url)             -> str          (bölüm 6 kuralları)
kampanya_urli_mi(url)          -> bool         (liste/sayfalama süzgeci)
kesif_kos(bankalar, *, ilerleme, iptal, gorunmez) -> KesifOzeti
```

`kesif_kos` içinde: tek tarayıcı oturumu (tıpkı `topla()` gibi), banka başına
kazıyıcı kurulur, **yalnız `kampanya_urlleri()` çağrılır** — `tara()` DEĞİL.
Detay sayfası hiç açılmaz.

> `topla()`'ya dokunulmuyor. Keşif ayrı bir giriş noktası; toplama yolu
> teslim edilmiş hâliyle kalıyor.

### 7.2 Depolama: `data/izleme/kesif.json`

```
{ "surum": 1,
  "kosular": [ { "zaman": ..., "banka_kodu": ...,
                 "bulunan": 51, "yeni": [...], "kaldirilmis": [...] } ] }
```

`data/raw` ve `data/katilim.db` **dokunulmaz** — G-17 kuralı aynen geçerli.
`.gitignore`'a girer (taban çizgisi gibi, makineye özgü ve türetilmiş).

Son koşu saklandığı için ikinci bir soru da cevaplanabilir hâle gelir:
*«dünkü keşiften bu yana ne değişti?»*

### 7.3 CLI

```
make kesif                 # dokuz banka
make kesif banka=0203      # tek banka
make kesif gorunur=1       # tarayıcı görünür (hata ayıklama)
```

`Tetikleyici`'nin `cron_satiri()`'si ürünleşince `make tazelik && make kesif`
olacak şekilde genişletilir — **kurulmaz**, G-17'deki iki gerekçe aynen
geçerli.

---

## 8. Arayüz — aynı sayfa, mevcut mekanizma korunur

**Boru Hattı → Sekme 3, iki bölüme ayrılır.** Sekme adı *«3 · Veri Tazeliği»*
yerine *«3 · Veri Denetimi»* olur; içinde:

```
┌─ 3 · Veri Denetimi ──────────────────────────────────────────┐
│                                                              │
│  A) YENİ KAMPANYA KEŞFİ            ← bu planın işi           │
│     [Bankalar ▾]  [Keşfi Başlat] [İptal]                     │
│     ● bulunan · ● YENİ · ● kaldırılmış · ● süre              │
│     banka ızgarası + olay günlüğü (mevcut bileşenler)        │
│     ▸ Yeni kampanyalar tablosu: banka · URL · [Topla]        │
│     ▸ Kaldırılmışlar (expander)                              │
│     ▸ Elenen liste sayfaları (expander, şeffaflık)           │
│                                                              │
│  ─────────────────────────────────────────────────────────   │
│                                                              │
│  B) ELİMİZDEKİLER GÜNCEL Mİ        ← G-17, AYNEN KALIYOR     │
│     [Kaynak ▾] [Kip ▾] [Tazeliği Denetle] [İptal]           │
│     (bugünkü ekranın tamamı, hiç değişmeden)                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

Yeniden kullanılan altyapı — yeni bileşen yazılmıyor:
`app/is_yurutucu.py` (arka plan işi + kuyruk) · `app/akis.py`
(`banka_izgarasi`, `olay_gunlugu`, `ilerleme_cubugu`) ·
`app/boru_durumu.py` (durum sınıfı + olay işleyici deseni).

Tek iş yuvası kuralı (`bh_is`) aynen geçerli: keşif koşarken toplama,
çıkarım ve tazelik düğmeleri kilitli.

---

## 9. Fazlar

| Faz | Kapsam | Teslim ilişkisi |
|---|---|---|
| **0** | Ölçüm (bölüm 4) — üç yoklama, ADR taslağı | **önce bu** |
| **1** | `kesif.py` + diff + rapor + Sekme 3A · salt okuma | asıl iş |
| **2** | «Yalnız yenileri topla» → `data/demo_raw` + demo veritabanı | teslim sonrası |
| **3** | Tetikleyici kurulur, keşif de zamanlanır | teslim sonrası |

**Faz 2 notu:** yeni bulunan URL'ler zaten elimizde olduğu için onları
toplamak `topla()`'ya *«şu URL listesini gez»* diyebilmeyi gerektirir —
bugün `topla()` yalnız banka alıyor. Küçük bir eklemeli değişiklik
(`urller=` kwarg), ama teslim gününde açılmamalı.

---

## 10. Doğrulama

### Ağsız (test takımına girer)
- `url_normalize` — bölüm 6 tablosundaki her satır için bir vaka
- `kampanya_urli_mi` — liste sayfası, sayfalama, `gecmis-kampanyalar` elenir;
  gerçek detay URL'i elenmez
- `envanter_oku` — banka başına doğru küme, kirli URL'ler süzülüyor
- diff — YENİ / KALDIRILMIŞ / ORTAK kümeleri; boş envanter; boş keşif
- slug-değişimi işareti — benzer çift yakalanıyor, benzemeyen çift
  işaretlenmiyor
- `iptal` — banka arasında kesiyor, tarayıcı temiz kapanıyor
  (sahte kazıyıcı ile, `tests/test_toplayici.py` deseni)

### Gerçek ağ (elle, kaydedilir)
1. Tek banka keşfi → süre ölçülür, bulunan sayısı envanterle karşılaştırılır
2. Aynı banka **iki kez** keşfedilir → ikinci koşuda YENİ = 0 olmalı
   (yanlış alarm ölçümü — G-17'de bu ölçüm bir hata yakalamıştı)
3. Dokuz banka tam keşif → toplam süre ve YENİ sayısı ADR'ye yazılır

### Regresyon kapıları
```
data/raw dosya sayısı    değişmemeli (1.024)
data/katilim.db          dokunulmamış olmalı
make test · make lint    yeşil
python -m src.boru_hatti seed --yalniz-kural   → çıktı birebir aynı
```

---

## 11. Dürüstlük sınırı

- **Keşif, kampanyayı ÇEKMEZ ve ÇIKARMAZ.** «3 yeni kampanya bulundu» der;
  toplamayı operatör başlatır. Gerekçe G-17 ile aynı: `data/raw` ve
  `data/katilim.db` yayımlanan ölçümlerin verisi, kendiliğinden değişemez.
- **«YENİ» kesin değil, ADAYdır.** Slug değişimi ve liste kirliliği yüzünden
  yanlış pozitif mümkün; rapor bunu saklamaz, işaretler.
- **Kaldırılmış ≠ süresi geçmiş.** Listeden düşmüş olabilir, arşive taşınmış
  olabilir, kazıyıcı o turda kaçırmış olabilir. Rapor «listede görünmedi» der,
  fazlasını iddia etmez.
- **Keşif de bir ziyarettir.** robots kapısı ve nezaket kuralı (istek arası
  ≥2 sn) keşifte de işler; demo için gevşetilmez.
- Bulunan sayılar **ölçülendir**, yuvarlanmaz.

---

## 12. Açık sorular — başlamadan cevaplanmalı

1. **Envanter kaynağı `data/raw` mı, veritabanı mı?** `data/raw` 1.024 ham
   sayfa; veritabanı 931 işlenmiş kampanya (26 Ağu'da süresi geçenler
   ayıklandı). *Öneri: `data/raw`* — diff URL düzeyinde ve toplama katmanının
   kendi envanteri orası. Ama «yeni kampanya» ifadesi jüriye 931 üzerinden
   anlatılıyorsa aradaki 93 kaydın durumu raporda açıklanmalı.
2. **`gecmis-kampanyalar` listesi keşfe dahil mi?** Dahil edilirse her arşiv
   kaydı «yeni» görünme riski taşır. *Öneri: hariç, ve bu kararın kendisi
   raporda yazılı olsun.*
3. **Sekme adı değişimi kabul mü?** *«3 · Veri Tazeliği»* → *«3 · Veri
   Denetimi»*. `app/` Esra'nın alanı — haber verilmeli.
4. **Faz 1 teslim gününde mi açılsın?** Ölçüm (Adım 0) bugün yapılabilir ve
   ucuz; kod yazımı teslim sonrasına bırakılabilir. Karar Adım 0'ın sonucuna
   bakılarak verilmeli: **YENİ = 0 çıkarsa bugün kod yazmaya değmez.**

---

## 13. Takım notu

- `src/collector/` ve toplama **Görkem'in**, `app/` **Esra'nın** alanı —
  Sekme 3'e dokunulacağı için haber verilmeli.
- `src/schema.py`'ye dokunulmuyor → ADR şart değil; ama Adım 0'ın ölçümleri
  ve verilen kararlar için `docs/kararlar/019-yeni-kampanya-kesfi.md` yazılmalı
  (018'in deseni).
- `.gitignore`'a bir satır: `data/izleme/` zaten var, `kesif.json` onun içinde.
- Panoya **G-19** olarak açılmalı; G-17 (tazelik) ve G-18 (boru hattı sayfası)
  ile kardeş.
