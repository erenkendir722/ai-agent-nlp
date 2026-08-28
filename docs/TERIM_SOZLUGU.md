# Katılım Bankacılığı Terim Sözlüğü

**Şartname 5.5** — *"Model katılım bankacılığına özgü finansal kavramları doğru
şekilde analiz edebilmelidir."*

Bu sözlük süs değildir: içeriği doğrudan LLM istemine enjekte edilir
([`src/extraction/llm.py`](../src/extraction/llm.py) → `TERIMLER`). Genel amaçlı
bir model "kâr payı"nı faiz sanabilir; alan bilgisini modele taşıyan şey bu
metindir. Buradaki bir tanımı değiştirmek çıkarım davranışını değiştirir.

**78 terim** tanımlıdır: şartnamenin beş resmî kavramı, katılım bankacılığının
fıkhî sözleşme türleri ve derlemimizde fiilen geçen operasyonel terimler.

---

## Nasıl okunur

Terim tabloları dört sütunludur ve hepsi aynı biçimdedir:

| Sütun | Anlamı |
|---|---|
| **Terim** | Kanonik yazım. Eş anlamlılar aynı hücrede `/` ile verilir. |
| **Tanım** | Tek cümle. İsteme giren metin budur — uzun tanım istem bütçesi yer. |
| **Sistemdeki karşılığı** | Şema alanı, kod sabiti veya "—" (yapısal karşılığı yok). |
| **İstem** | ✓ ise `TERIMLER` sabitine girer, — ise yalnız insan başvurusu içindir. |

**İstem kuralı — neden her terim modele verilmiyor:**
Bir terim isteme yalnız iki koşul birden sağlanırsa girer:

1. **Derlemde geçiyor.** 590 kayıtta hiç görünmeyen bir terim, modele
   verildiğinde yalnız istem bütçesi tüketir; kötü ihtimalde metinde olmayan
   bir kavramı aramaya kışkırtır. `muşaraka`, `tekafül`, `garar` bu yüzden ✓
   değildir — sektör bilgisidir, çıkarım bilgisi değil (bkz. §10).
2. **Bir çıkarım kararını değiştiriyor.** `taksit` derlemde 299 kayıtta geçer
   ama hiçbir modelin öğrenmeye ihtiyacı yoktur. `vade farksız` ise
   `kar_payi_orani = 0` demektir — bunu bilmeyen model alanı boş bırakır.

**Kuralın üç bilinçli istisnası var** (hepsi §10'da gerekçeli):

- **Şartname 5.5'in beş resmî kavramı koşulsuz girer.** Sözleşme gereğidir;
  derlem sayısına bakılmaz.
- **Riba**, derlemde hiç geçmez ama isteme girer. İsteme giren şey sözcük
  değil *ayrımdır*: modele "kâr payı faiz değildir" dedirten tanım budur.
- **Dosya masrafı**, derlemde hiç geçmez ama isteme girer — "tahsis ücreti"nin
  eş anlamlısıdır ve görülmemiş bir bankada bu yazımla çıkabilir.

Bu süzgeç 78 terimden **30'unu** isteme taşır. Kalan 48 terim, sözlüğün insan
tarafını oluşturur: etiketleyici, jüri ve yeni ekip üyesi için.

---

## 1. Şartnamedeki beş resmî kavram

Tanımlar şartname 5.5 tablosundan **birebir** alınmıştır.

### Kâr Payı Oranı
Katılım bankacılığında **faiz yerine** kullanılan, finansman işlemine konu olan
mal veya hizmet üzerinden oluşan kâr payı oranını ifade eder.

- **Şemadaki karşılığı:** `kar_payi_orani` (aylık yüzde, `float`)
- **Neden faiz değil:** Katılım bankası parayı ödünç vermez; müşterinin
  istediği malı satın alıp vadeli olarak ona satar. Aradaki fark kâr payıdır.
  Terminolojiyi karıştırmak sektör jürisinin ilk yakalayacağı hatadır.
- **Makullük sınırı:** aylık kâr payı tek haneli yüzdelerde seyreder. Sistem
  %15 üstünü aylık oran saymaz (`AYLIK_KAR_PAYI_UST_SINIRI`) — "Yıllık Maliyet
  Oranı %82,44" gibi ifadeler bu alana düşmesin diye.

### Finansman Maliyeti / Toplam Maliyet
Kullandırılan finansman kapsamında oluşan **toplam geri ödeme tutarını** ve
müşterinin katlandığı toplam maliyeti ifade eder.

- **Şemadaki karşılığı:** tek alan değil, **hesaplanır** —
  [`karsilastirma.toplam_maliyet()`](../src/comparison/karsilastirma.py)
- Kâr payı oranı + vade + tahsis ücretinden annüite formülüyle üretilir.
  Murabahada satış bedeli baştan sabitlendiği için taksit hesabı matematiksel
  olarak annüite ile aynıdır.

### Katılım Fonu
Katılım bankacılığı prensiplerine uygun olarak değerlendirilen ve fon sahipleri
ile banka arasında **kâr-zarar paylaşımına** dayanan hesap türü.

- **Şemadaki karşılığı:** `kampanya_turu = yatirim_urunu`, `urun_turu` serbest metni
- Mevduat **değildir**: getiri garanti edilmez, kâr da zarar da paylaşılır.
  Bu yüzden katılma hesabı ürünlerinde "faiz oranı" gibi bir alan aranmaz.

### Masrafsız Finansman
Finansman işlemi kapsamında tahsis ücreti, dosya masrafı veya benzeri ek
maliyetlerin **uygulanmadığı** finansman türü.

- **Şemadaki karşılığı:** `masrafsiz_mi` (`bool`), `tahsis_ucreti`, `masraf_bilgisi`
- **Türkçe tuzağı:** bankalar bunu ekle söyler, sözcükle değil —
  "alınmaz", "alınmıyor", "**alınmamaktadır**", "tahsil edilmemektedir",
  "uygulanmamaktadır". Sistem `-mAz / -mIyor / -mAmAktA(dır)` eklerini yapısal
  olarak tanır ([`olumsuzlanmis_mi`](../src/preprocessing/normalizasyon.py)).
- **Ölçüm bunu doğruluyor (23 Ağu, 590 kayıt):** "masrafsız" **sözcüğü** yalnız
  **2** kayıtta geçer; sistem `masrafsiz_mi` alanını **157** kayıtta doldurur.
  Aradaki 155 kayıt tamamen ekten okunmuştur. Sözcük listesiyle çalışan bir
  çıkarım bu kavramın neredeyse tamamını kaçırırdı.
- **İnce durum:** *"Ekspertiz ücreti banka tarafından karşılanmaktadır"* yüklemi
  **olumludur** ama masraf müşteriye yansımaz → masrafsız sayılır.

### Avantajlı Finansman
Standart finansman koşullarına göre daha uygun maliyet, kâr payı oranı veya
ek fayda sunan **kampanyalı** finansman ürünü.

- **Şemadaki karşılığı:** `kampanya_avantaji` (serbest metin)
- **Sayı uydurulmaz:** "avantajlı kâr payı fırsatı" ifadesinde rakam yoksa
  `kar_payi_orani` **boş bırakılır**, ifade `kampanya_avantaji`'ye yazılır
  (şartname 5.2). Boş bırakmak yanlış sayı vermekten her zaman iyidir.

---

## 2. Şartname 5.2'nin dolaylı ifadeleri

Şartname bu dört ifadenin doğru yorumlanmasını açıkça istiyor:

| İfade | Sistem ne yapar |
|---|---|
| "%2,05 kâr payı oranı" | `kar_payi_orani = 2.05` — sayı açık |
| "avantajlı kâr payı fırsatı" | Oran alanı **boş**; ifade `kampanya_avantaji`'ye |
| "özel oranlı finansman" | Oran alanı **boş**; ifade `kampanya_avantaji`'ye |
| "düşük maliyetli finansman" | Oran alanı **boş**; ifade `kampanya_avantaji`'ye |

Ortak kural: **sayısız ifadeden sayı türetilmez.** Bu kısıt istemle değil kodla
uygulanır — eleştirmen ajanı, LLM'in ürettiği her sayıyı ham metinde birebir
arar, bulamazsa alanı düşürür.

---

## 3. İlkeler ve fıkhî sözleşme türleri

Katılım bankacılığının *neden* böyle çalıştığını açıklayan katman. Bu terimlerin
çoğu kampanya sayfalarında geçmez (§10) — ama bir ürünün neden "finansman" olup
"kredi" olmadığını bunlar açıklar.

| Terim | Tanım | Sistemdeki karşılığı | İstem |
|---|---|---|---|
| **Katılım bankacılığı** | Faiz yerine ticaret, kiralama ve ortaklık üzerinden çalışan bankacılık modeli. | Projenin tüm kapsamı; `banks.yaml` | ✓ |
| **Faizsiz bankacılık ilke ve standartları** | BDDK'nın katılım bankalarını bağlayan uyum çerçevesi. | — | — |
| **Riba** | Faiz. Borç üzerinden vade karşılığı alınan fazlalık; katılım bankacılığının reddettiği temel işlem. | Kavramsal — `kar_payi_orani` faiz DEĞİLDİR | ✓ |
| **Garar** | Sözleşmedeki aşırı belirsizlik: konusu, bedeli veya teslimi belirsiz akit. | — | — |
| **Meysir** | Kumar ve şansa dayalı kazanç. | — | — |
| **Murabaha** | Bankanın malı satın alıp, maliyeti ve kâr payını açıklayarak müşteriye vadeli satması. | Bireysel finansmanın baskın yöntemi; `toplam_maliyet()` bu yüzden annüite | ✓ |
| **Muşaraka / Müşareke** | Tarafların birlikte sermaye koyup kârı orana, zararı sermaye payına göre paylaştığı ortaklık. | — | — |
| **Azalan muşaraka** | Müşterinin bankanın payını taksitle devraldığı, konut finansmanında kullanılan muşaraka türü. | — | — |
| **Mudaraba / Mudarebe** | Bir taraf sermaye, diğer taraf emek koyar; kâr paylaşılır, zarar sermayedarındır. | Katılma hesabının hukukî temeli | — |
| **İcara / İcâre** | Kiralama. Bankanın satın aldığı varlığı müşteriye kiralaması. | `urun_turu` serbest metni | — |
| **İcara muntehiye bit-temlik** | Kira süresi sonunda mülkiyetin müşteriye geçtiği kiralama; finansal kiralamanın karşılığı. | — | — |
| **Selem** | Bedeli peşin ödenip malı ileri tarihte teslim edilen satış; tarımsal finansmanda kullanılır. | — | — |
| **İstisna** | Sipariş üzerine imalat veya inşaat sözleşmesi; ödeme aşamalı yapılır. | — | — |
| **Karz-ı hasen** | Kâr payı alınmayan, yalnız anaparası geri ödenen iyilik amaçlı ödünç. | `kar_payi_orani = 0` meşru olabilir (`sifir_gecerli`) | ✓ |
| **Vekâlet** | Bankanın müşteri adına ücret karşılığı işlem yapması. | — | — |
| **Teverruk** | Vadeli alınan malın nakde çevrilmesiyle likidite sağlanması. | — | — |
| **Sukuk / Kira sertifikası** | Bir varlığın gelirine ortaklık veren menkul kıymet; Türkiyede varlık kiralama şirketi ihraç eder. | `kampanya_turu = yatirim_urunu` | ✓ |
| **Tekafül / Katılım sigortacılığı** | Katılımcıların bağış esaslı ortak havuzdan birbirinin riskini karşıladığı sigorta modeli. | `uygunluk.zorunlu_urun` = "sigorta" | — |
| **Danışma kurulu** | Ürünlerin faizsiz bankacılık ilkelerine uygunluğunu denetleyen kurul. | — | — |
| **Kâr-zarar ortaklığı** | Getirinin garanti edilmediği, kârın da zararın da paylaşıldığı ilişki. | Katılma hesaplarında "faiz oranı" alanı ARANMAZ | ✓ |

---

## 4. Fon toplama tarafı — hesaplar

| Terim | Tanım | Sistemdeki karşılığı | İstem |
|---|---|---|---|
| **Katılma hesabı** | Kâr-zarar ortaklığına dayalı, getirisi garanti edilmeyen hesap. | `kampanya_turu = yatirim_urunu`; `MEVDUAT_URUNU` vetosu | ✓ |
| **Özel cari hesap** | Kâr payı ödenmeyen, istendiğinde çekilebilen hesap. | `kampanya_turu = yatirim_urunu` | — |
| **Havuz** | Katılma hesaplarının vade ve para birimine göre toplandığı fon kümesi. | — | — |
| **Birim hesap değeri** | Havuzun günlük değeri; kâr payı dağıtımı bu değerin değişimiyle yapılır. | — | — |
| **Kâr payı dağıtım oranı / katılım oranı / kâr paylaşım oranı** | Havuz kârının banka ile hesap sahibi arasındaki paylaşım yüzdesi. | `kar_payi_orani` ile KARIŞTIRILMAZ — finansman oranı değildir | ✓ |
| **Kıymetli maden hesabı** | Altın veya gümüş cinsinden tutulan katılma ya da cari hesap. | `urun_turu`; `Birim` TL olmayabilir | — |
| **TMSF güvencesi** | Katılım fonunun yasal limite kadar sigortalı olması. | — | — |
| **Katılım endeksi** | Faizsiz bankacılık ölçütlerine göre taranmış hisse endeksi (Katılım 30 vb.). | `kampanya_turu = yatirim_urunu` | — |

---

## 5. Fon kullandırma tarafı — finansman

| Terim | Tanım | Sistemdeki karşılığı | İstem |
|---|---|---|---|
| **Finansman** | Kredinin katılım bankacılığındaki karşılığı; banka mal alıp satar, para ödünç vermez. | `kampanya_turu = finansman` | ✓ |
| **İhtiyaç finansmanı** | Belirli bir mala bağlı olmayan bireysel finansman. | `kampanya_turu = ihtiyac_finansmani` | ✓ |
| **Konut finansmanı** | Konut alımına yönelik, teminatı genellikle ipotek olan finansman. | `kampanya_turu = konut_finansmani` | ✓ |
| **Taşıt finansmanı** | Araç alımına yönelik, teminatı araç rehni olan finansman. | `kampanya_turu = tasit_finansmani` | ✓ |
| **Finansman tutarı / limiti** | Kullandırılabilecek azami anapara. | `finansman_tutari_max` (TL) | ✓ |
| **Vade** | Geri ödeme süresi (ay). "X aya kadar", "X ay vadeli", "X aya varan" biçimleri tanınır. | `vade_ay_max` (`Birim.AY`) | ✓ |
| **Taksit** | Ödeme planındaki tek bir ödeme. | `taksit_sayisi` (`Birim.ADET`) | — |
| **Peşinat** | Alışta müşterinin baştan ödediği, finansmana konu olmayan kısım. | `uygunluk.ek_sartlar` | — |
| **Ödeme planı / annüite** | Eşit taksitli geri ödeme tablosu. | [`toplam_maliyet()`](../src/comparison/karsilastirma.py) | — |
| **Vade farksız** | Taksitlendirmede ek maliyet alınmaması; kâr payı gerçekten sıfırdır. | `kar_payi_orani = 0` — `sifir_gecerli=True` bunun için var | ✓ |
| **Ara ödeme** | Taksit planı dışında yapılan, anaparayı azaltan ödeme. | `kampanya_kosullari` | — |
| **Ödemesiz dönem / erteleme** | Taksitin belirli süre başlamaması veya ötelenmesi. | `kampanya_avantaji` | ✓ |
| **Erken ödeme / erken kapama** | Borcun vadesinden önce kapatılması. | `kampanya_kosullari` | — |
| **Erken ödeme tazminatı** | Erken kapamada alınan, yasal üst sınırı olan tutar. | `kar_payi_orani` VETOSU — kâr payı değildir | ✓ |
| **Gecikme / temerrüt** | Taksitin vadesinde ödenmemesi ve buna bağlı yaptırım. | `kampanya_kosullari` | — |
| **Kredi-değer oranı (KDO)** | Finansman tutarının teminat değerine oranı. | `_KREDIYE_ESAS_DEGER` — `kar_payi_orani`na sızmasın diye | ✓ |
| **Yıllık maliyet oranı** | Tüm masraflar dâhil yıllıklandırılmış toplam maliyet yüzdesi. | `HESAP_ARACI_CIKTISI` vetosu — AYLIK oran değildir | ✓ |
| **Finansal kiralama / leasing** | Varlığın kiralanıp sonunda mülkiyetin devredildiği finansman; icaranın karşılığı. | `urun_turu` | — |

---

## 6. Masraf ve ücret kalemleri

Bu grup `masrafsiz_mi` alanının doğruluğunu belirler. Ayrımın tamamı şu
sorudadır: **ücret finansmana mı ait, başka bir hizmete mi?**

| Terim | Tanım | Sistemdeki karşılığı | İstem |
|---|---|---|---|
| **Tahsis ücreti** | Finansman tahsisinde alınan tek seferlik masraf. | `tahsis_ucreti` — TL **veya** yüzde olabilir, `Birim` zorunlu | ✓ |
| **Dosya masrafı / dosya parası** | Tahsis ücretinin yaygın diğer adı. | `FINANSMAN_MASRAFI` | ✓ |
| **Ekspertiz ücreti** | Konut ve taşıt finansmanında değerleme masrafı. | `FINANSMAN_MASRAFI`; "banka karşılar" → masrafsız | ✓ |
| **Komisyon** | Bir hizmet karşılığı alınan ücret; finansmana ait olmayabilir. | `MASRAF_SOZCUKLERI` | — |
| **Kart aidatı** | Kredi kartının yıllık ücreti — finansman masrafı **değildir**. | `FINANSMAN_DISI_UCRET` | ✓ |
| **Hesap işletim ücreti** | Hesabın işletilmesi için alınan ücret — finansman masrafı **değildir**. | `FINANSMAN_DISI_UCRET` | — |
| **Sigorta primi** | Poliçe bedeli — finansman masrafı **değildir**. | `FINANSMAN_DISI_UCRET` | — |
| **BSMV / KKDF** | Yasal kesintiler; bankanın sunduğu koşul değil, mevzuat gereğidir. | `VERGI_VE_MEVZUAT` vetosu | ✓ |

---

## 7. Kart, ödül ve harcama

| Terim | Tanım | Sistemdeki karşılığı | İstem |
|---|---|---|---|
| **Kart kampanyası** | Kredi veya banka kartı harcamasına bağlı kampanya. | `kampanya_turu = kart` | — |
| **Alışveriş puanı** | Harcama karşılığı kazanılan, harcamada kullanılabilen puan. | `alisveris_puani` (`Birim.TL` veya `Birim.PUAN`) | ✓ |
| **Nakit iade / iade** | Harcamanın bir kısmının hesaba geri ödenmesi. | `odul_miktari`; `kar_payi_orani` VETOSU | ✓ |
| **Mil** | Uçuş programlarında kazanılan puan birimi. | `odul_miktari`; `kar_payi_orani` VETOSU | ✓ |
| **Taksitlendirme** | Kart harcamasının taksitlere bölünmesi. | `taksit_sayisi` | — |
| **Ekstre** | Kart dönem hesap özeti. | `FINANSMAN_DISI_UCRET` | — |
| **Asgari ödeme** | Ekstrenin gecikmeye düşmemek için ödenmesi gereken en az kısmı. | — | — |
| **POS / sanal POS** | Üye işyeri ödeme terminali; kart kampanyalarının çoğu buna bağlıdır. | `uygunluk.ek_sartlar` | — |
| **Yeni müşteri kampanyası** | Yalnız bankada hesabı olmayanlara açık kampanya. | `hedef_kitle = yeni_musteri` | — |

---

## 8. Teminat, sigorta ve mevzuat

| Terim | Tanım | Sistemdeki karşılığı | İstem |
|---|---|---|---|
| **Teminat** | Geri ödemenin güvencesi olarak gösterilen varlık veya kişi. | `uygunluk.ek_sartlar` | — |
| **Kefil / kefalet** | Borcun ödenmemesi hâlinde sorumluluğu üstlenen üçüncü kişi. | `uygunluk.ek_sartlar` | — |
| **İpotek / rehin** | Taşınmaz (ipotek) veya taşınır (rehin) üzerine konan teminat hakkı. | `uygunluk.ek_sartlar` | — |
| **DASK** | Zorunlu deprem sigortası; konut finansmanında aranır. | `uygunluk.zorunlu_urun` | — |
| **BES** | Bireysel emeklilik sistemi; katılım esaslı fonları vardır. | `uygunluk.zorunlu_urun` | — |
| **BDDK** | Bankacılık düzenleme ve denetleme otoritesi; banka listemizin kaynağı. | `banks.yaml`, `docs/kanit/bddk-liste.png` | — |
| **KGF** | Teminatı yetersiz işletmelere kefalet veren fon. | — | — |
| **Maaş müşterisi** | Maaşını bankadan alan, çoğu kampanyada ayrıcalıklı müşteri. | `hedef_kitle = maas_musterisi` | ✓ |
| **KOBİ / esnaf** | Ticari kampanyaların baskın hedef segmenti. | `hedef_kitle = segment`, `uygunluk.segment_detayi` | ✓ |
| **Segment** | Öğrenci, emekli, kadın girişimci gibi tanımlı müşteri kümesi. | `hedef_kitle = segment` | ✓ |

---

## 9. Karıştırılmaması gerekenler

Bunlar gerçek hata biçimleridir; her biri sistemde ayrı bir korumaya karşılık gelir.

| Karışan | Neden ayrı | Koruma |
|---|---|---|
| **Kâr payı oranı** ↔ **indirim oranı** | "%80'e varan indirim" bir kâr payı değildir | Makullük aralığı + dışlayıcı sözcükler |
| **Kâr payı oranı** ↔ **kâr payı dağıtım oranı** | İlki finansmanın fiyatı, ikincisi hesabın paylaşım yüzdesi | `MEVDUAT_URUNU` vetosu |
| **Finansman tutarı** ↔ **ödül miktarı** | "5.000 TL değerinde alışveriş çeki" limit değil hediyedir | "değerinde", "… çeki" dışlayıcıları |
| **Tahsis ücreti** ↔ **finansman limiti** | "50.000 TL'ye kadar masraf alınmaz" cümlesinde 50.000 TL ücret değildir | Olumsuzlama reddi + aynı cümle kısıtı |
| **Aylık oran** ↔ **yıllık maliyet oranı** | Hesaplama araçlarındaki yıllık oran aylık sanılırdı | `AYLIK_KAR_PAYI_UST_SINIRI = %15` |
| **Finansman masrafı** ↔ **kart/hesap ücreti** | "Kart aidatı yok" finansmanın masrafsız olduğunu söylemez | `FINANSMAN_DISI_UCRET` |
| **Kâr payı** ↔ **faiz** | Kavramsal olarak farklıdır | İstem enjeksiyonu (bu dosya) |
| **Kâr payı** ↔ **nakit iade / mil** | "%10 oranında mil kazanırsınız" kâr payı değildir | `kar_payi_orani` veto ifadeleri |

---

## 10. Derlem ölçümü — hangi terim gerçekten geçiyor

*Ölçüm: 23 Ağustos 2026, `data/katilim.db`, 590 kayıt. Sayı, terimin geçtiği
**kayıt** sayısıdır (toplam geçiş değil). Eşleşme ham metin üzerinde,
[`tr_kucult`](../src/preprocessing/normalizasyon.py) ile küçültülerek, sol
tarafta kesin sözcük sınırı ve sağ tarafta Türkçe ad çekim ekine izin verilerek
yapıldı — `mil` sayılır, `milyon` sayılmaz. Hücredeki `/` ile ayrılmış eş
anlamlılar birlikte sayıldı.*

78 terimin **60'ı** derlemde geçiyor, **18'i** hiç geçmiyor. Bu ayrım sözlüğün
en işlevsel parçasıdır: isteme neyin gireceğini o belirliyor.

### Derlemde hiç geçmeyen 18 terim

| Sektör terimi | Derlemde | Neden yine de sözlükte |
|---|---|---|
| riba, garar, meysir | 0 | Modelin *neden* faiz aramadığını açıklayan çerçeve. Üçünden yalnız `riba` isteme girer — çünkü isteme giren şey sözcük değil, "kâr payı ≠ faiz" ayrımıdır. |
| muşaraka, azalan muşaraka, mudaraba | 0 | Ürünlerin fıkhî temeli; jüri sektör bilgisi bekliyor |
| icara, icara muntehiye bit-temlik | 0 | Aynı gerekçe; ürün adı olarak "finansal kiralama" kullanılıyor (5 kayıt) |
| selem, istisna | 0 | **Eş sesli tuzağı:** "istisna" derlemde 4 kez geçer ama hepsi *vergi istisnası* anlamındadır, fıkhî akit değil. Sistem bunları zaten `VERGI_VE_MEVZUAT` ile veto ediyor. |
| vekâlet, teverruk, tekafül | 0 | Sektör bilgisi; kampanya diline girmiyor |
| danışma kurulu | 0 | Uyum denetiminin kurumsal karşılığı |
| birim hesap değeri | 0 | Katılma hesabı getirisinin nasıl hesaplandığı |
| dosya masrafı | 0 | **Eş anlamlı tuzağı:** bankalar "tahsis ücreti" yazıyor (17 kayıt), "dosya masrafı" hiç yazmıyor. İsteme yine de girer — görülmemiş bir bankada bu yazımla çıkabilir. |
| asgari ödeme | 0 | Kart ekstresi kavramı; kampanya metinlerine girmiyor |
| KGF | 0 | Ticari finansmanda yaygın, kampanya sayfalarında değil |

**Bulgu:** Kampanya sayfaları fıkhî sözleşme adlarını kullanmıyor. Katılım
bankaları ürünü müşteriye "murabaha" diye değil "ihtiyaç finansmanı" diye
satıyor — `murabaha` 590 kayıtta yalnız **3** kez geçiyor. Bu terimleri isteme
koymak, modeli metinde olmayan bir şeyi aramaya iter.

### Derlemde en çok geçen 15 terim

| Sektör terimi | Derlemde | Not |
|---|---|---|
| taksit | 299 | İsteme girmez — model zaten biliyor |
| katılım bankacılığı | 229 | Alan çerçevesi |
| POS / sanal POS | 196 | Kampanya koşulu, çıkarım alanı değil |
| vade | 194 | `vade_ay_max` 285 kayıtta dolduruldu |
| finansman | 104 | Kredinin karşılığı |
| vade farksız | 99 | `kar_payi_orani = 0`; `sifir_gecerli` bu yüzden var |
| taksitlendirme | 83 | Kart kampanyalarının baskın biçimi |
| avantajlı finansman | 58 | Şartname 5.2'nin dolaylı ifadesi |
| ekstre | 44 | Kart tarafı |
| alışveriş puanı | 36 | `alisveris_puani` 16 kayıtta dolduruldu |
| teminat | 27 | Uygunluk koşulu |
| komisyon | 22 | Masraf ailesi |
| KOBİ / esnaf | 21 | Ticari segment |
| ödemesiz dönem / erteleme | 20 | `kampanya_avantaji` |
| nakit iade | 20 | `kar_payi_orani` vetosu — sık karışan yüzde |

### Sözcük değil, ek

Bu derlemin en güçlü tek bulgusu §1'de duruyor ve tekrar edilmeye değer:

| | "masrafsız" sözcüğü | `masrafsiz_mi` dolu |
|---|---|---|
| Kayıt sayısı | **2** | **157** |

Kavram, sözcükle değil **Türkçe olumsuzlama ekiyle** anlatılıyor:
"alınmamaktadır", "tahsil edilmemektedir". Terim listesiyle çalışan bir çıkarım
bu alanın neredeyse tamamını kaçırırdı; sistemin morfolojik yaklaşımı
(`olumsuzlanmis_mi`) bir tercih değil, zorunluluktur.

---

## 11. Kaynaklar

- TEKNOFEST 2026 TYDA Şartnamesi, 2. Senaryo, madde 5.2 ve 5.5 (resmî tanımlar)
- 5411 sayılı Bankacılık Kanunu — "katılım bankası" ve "katılım fonu" tanımları
- BDDK, *Faizsiz Bankacılık İlke ve Standartlarına Uyuma İlişkin Tebliğ*
- BDDK Kuruluş Listesi — <https://www.bddk.org.tr/Kurulus/Liste/77>
- TKBB (Türkiye Katılım Bankaları Birliği) faizsiz bankacılık standartları
- Katılım bankalarının kamuya açık ürün ve kampanya sayfaları (bkz.
  [`docs/VERI_METODOLOJISI.md`](VERI_METODOLOJISI.md))

---

## Sözlüğe terim eklerken

1. **Tabloların dört sütunlu biçimini bozma.** Sözlük makine tarafından
   okunuyor; [`tests/test_terim_sozlugu.py`](../tests/test_terim_sozlugu.py)
   biçimi ve terim sayısını denetler.
2. **İstem sütununu ölçmeden ✓ yapma.** Derlemde geçmeyen terim isteme girmez
   (§10). Şüpheliysen ham metinde ara.
3. **İsteme girecek terimi §12'deki bloğa yaz.** Kod o bloğu bu dosyadan
   okur (26 Ağustos); artık `src/extraction/llm.py` içinde elle tutulan
   bir kopya yoktur. Bloğu değiştirdiysen çıkarım değişir: `make extract &&
   make eval` koşmadan sonuç yayımlama.

---

## 12. İsteme beslenen blok

Aşağıdaki blok, dil modeline gönderilen sistem isteminin içine **bu dosyadan
okunarak** yerleştirilir (`src/extraction/llm.py::terimleri_yukle`). Yani sözlük
ile modelin gördüğü metin **tek kaynaktır**; ikisi ayrışamaz.

**Blok neden sözlüğün tamamı değil?** İstem bütçesi sınırlı ve §10'da ölçüldü:
derlemde hiç geçmeyen bir terimi isteme koymak, modele işe yaramayan bağlam
yüklemektir. Buraya şartnamenin beş resmî kavramı, sık geçen kalıplar ve 5.2'nin
dolaylı ifadeleri girer. Blok değişirse **çıkarım da değişir** — değiştirdikten
sonra `make extract && make eval` koşulmalıdır.

⚠️ İşaretçi satırlarını (`ISTEM:BASLA` / `ISTEM:BITIR`) silmeyin; kod bu iki
satır arasını okur, bulamazsa **hata fırlatır** (sessizce boş istem göndermez).

<!-- ISTEM:BASLA -->
```text
Katılım bankacılığı terimleri (şartname 5.5'teki resmî tanımlar):
- Kâr Payı Oranı: Katılım bankacılığında FAİZ YERİNE kullanılan, finansman
  işlemine konu olan mal veya hizmet üzerinden oluşan kâr payı oranını ifade eder.
- Finansman Maliyeti: Kullandırılan finansman kapsamında oluşan toplam geri ödeme
  tutarını ve müşterinin katlandığı toplam maliyeti ifade eder.
- Katılım Fonu: Katılım bankacılığı prensiplerine uygun olarak değerlendirilen ve
  fon sahipleri ile banka arasında kâr-zarar paylaşımına dayanan hesap türü.
- Masrafsız Finansman: Finansman işlemi kapsamında tahsis ücreti, dosya masrafı
  veya benzeri ek maliyetlerin UYGULANMADIĞI finansman türü.
- Avantajlı Finansman: Standart finansman koşullarına göre daha uygun maliyet,
  kâr payı oranı veya ek fayda sunan kampanyalı finansman ürünü.

Ek notlar:
- "Finansman" sözcüğü kredi anlamındadır; "kâr payı" faiz DEĞİLDİR.
- Kâr payı oranı genellikle AYLIK yüzde olarak verilir (örn. aylık %2,05).
- Tahsis ücreti = dosya masrafı; finansman tahsisinde alınan tek seferlik masraf.

Dolaylı ifadeler de kâr payı avantajını anlatır ve tanınmalıdır (şartname 5.2):
"avantajlı kâr payı fırsatı", "özel oranlı finansman", "düşük maliyetli finansman".
Bu ifadelerde SAYI YOKSA kar_payi_orani alanını null bırak — dolaylı ifadeden
sayı UYDURMA. İfadeyi kampanya_avantaji alanına yaz.
```
<!-- ISTEM:BITIR -->
