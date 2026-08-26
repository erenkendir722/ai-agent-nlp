# Jüri Soru-Cevap Provası (E-19)

_26 Ağustos 2026 · Eren_

> **Bu dosya elle yazılır ve elle güncellenir**, `make eval` tarafından
> üretilmez. Ama içindeki **her sayı üretilen bir dosyadan kopyalanmıştır** ve
> kaynağı satırında yazılıdır. Sayı değişirse burası da değişir — provada
> ezberlenen bayat bir sayı, sunumda söylenen bayat bir sayıdır.

## Nasıl kullanılır

Her sorunun **30 saniyelik** bir cevabı var. Ezber değil; iskelet:

1. **İlk cümle iddiayı kabul eder ya da reddeder.** Yuvarlanmaz.
2. **İkinci cümle sayıyı ve kaynağını verir.**
3. **Üçüncü cümle ne yaptığımızı söyler.**

En pahalı hata, bilmediğimiz bir şeyi biliyormuş gibi cevaplamaktır. Jüri
kanıt dosyasını açabilir — hepsi depoda. Bilinmiyorsa cevap şudur:
*«Onu ölçmedik.»*

**Zayıf noktalar 2, 8, 3 ve 11 numaralı sorulardadır.** Üçü de bizim kendi
ölçümümüzden çıktı ve saklanmıyor. Jüri bunları zaten bulacak; önce bizim
söylememiz, savunma değil güven üretir.

---

## 1. «Makro-F1 0,82 diyorsunuz. Kaç örnek üzerinde ölçtünüz?»

> **98 örnek.** Bu yüzden tek sayı söylemiyoruz: makro-F1 **0,818**, %95 güven
> aralığı **0,750–0,866** — 400 kez önyükleme ile hesaplandı. Aralık genişse
> sebebi modelin kararsızlığı değil, altın setin küçüklüğüdür. Sunumdaki her
> yerde aralığıyla ve örnek sayısıyla birlikte yazıyor.

**Kaynak:** [`docs/SONUCLAR.md`](SONUCLAR.md) · [`docs/DEGERLENDIRME_YONTEMI.md`](DEGERLENDIRME_YONTEMI.md)

**Devamı gelirse — «neden 98?»:** Etiketleme dört kişinin elinden geçti,
uyum ölçüldü ([H-02](../GOREVLER.md)). Daha büyük bir set zaman meselesiydi,
kalite meselesi değil. Setin kendi denetimi ayrı bir dosyada:
[`docs/ALTIN_SET_DENETIMI.md`](ALTIN_SET_DENETIMI.md).

---

## 2. «`kar_payi_orani` doluluğu %16. En önemli alan bu değil mi?»

> **Evet, en önemli alan bu ve bilerek boş bırakıyoruz.** 931 kayıtta 147'sinde
> dolu. Sebep model değil kaynak: bankaların çoğu oranı kampanya sayfasında
> değil başvuru ekranında veriyor, kart ve puan kampanyalarında oran zaten
> yok. Uydurmak yerine `Belirtilmemiş` diyoruz — **çıkardığımız yerde doğru
> çıkarıyoruz: altın set F1'i 0,780** (N=21, yani küçük bir örneklem).

**Kaynak:** [`docs/SONUCLAR.md`](SONUCLAR.md) doluluk tablosu · `make durum`

**Devamı gelirse — «neden yükseltmediniz?»:** Denendi, doluluk kaynaktan
geldiği için yükselmedi. Yükseltmenin tek yolu tahmin üretmekti; bu sistemde
her değer kanıt taşımak zorunda (`Alan(deger=..., yontem="belirtilmemis")`
`ValueError` fırlatır), o yüzden yapmadık.

---

## 3. «On-prem diyorsunuz ama modeliniz dışarı çıkıyor.»

> **Doğru, çıkıyor — tek bir uca.** Çıkarım LLM'i T.C. Cumhurbaşkanlığı SSB'nin
> bu yarışma için tahsis ettiği **EVREN** servisine gidiyor; ticari bulut değil,
> yarışma altyapısı. İzinli tek dış uç odur ve bunu bir test sözleşme hâline
> getiriyor: `test_llm_ucu_yalnizca_yerel_veya_evren`. Kural, normalizasyon,
> karşılaştırma ve chatbot katmanları tamamen kapalı devre.

**Kaynak:** `tests/test_sizinti_yok.py` (6 test) · [`ADR 013`](kararlar/013-evren-model-lisans-durusu.md) ·
[`docs/KURUMSAL_ENTEGRASYON.md`](KURUMSAL_ENTEGRASYON.md)

**Devamı gelirse — «kurumda internet yoksa?»:** Aynı kod yolu yerel Ollama ile
koşuyor: `make extract-yerel`. Gömme de yerelleşti ([ADR 016](kararlar/016-yerel-gomme-saglayicisi.md)),
yani RAG dahil sistemin tamamı hava boşluğunda çalışıyor. Bunu 18 Ağustos'ta
Docker içinde ölçtük (`make hava-boslugu`).

**Dürüst kalan sınır:** `uygulama` ve `api` konteynerleri port yayını için
`sunum` ağında ve oradan çıkabiliyorlar. Tam kapatmak ters vekil gerektirir,
yapılmadı. **«Hiçbir konteyner dışarı çıkamıyor» DEMEYİN** — jüri
`docker network inspect` ile bakabilir.

---

## 4. «Chatbot uydurmuyor mu? Sayı halüsinasyonu?»

> **Sayısal cevaplar metin aramasından değil, yapısal veriden geliyor** ve
> önlerinde bir kalkan var: cevabın her parçası kökenine göre denetleniyor —
> yapısal değer kayıtta birebir bulunmalı, alıntı kaynak metnin alt dizesi
> olmalı, hesap girdilerinden yeniden üretilebilmeli. **Meşru soruların
> engellenme oranı 0/35.** Denetimsiz geçen parça: 0.

**Kaynak:** [`docs/SONUCLAR.md`](SONUCLAR.md) kalkan bölümü ·
[`ADR 010`](kararlar/010-koken-tipli-kalkan.md) · `tests/test_kalkan_kokenli.py`

**Devamı gelirse — «çok mu sıkı?»:** Kalkanın iki yönlü hata uzayı var ve
ikisi de ayrı ölçülüyor. 18 Ağustos'ta yanlış blok oranı %14,3'tü — bankanın
kendi metnindeki sayılar, bir vakada **6698 sayılı KVKK kanun numarası**,
uydurma sayılıyordu. Kalkanı gevşetmedik; denetlenecek metni doğru seçtik.

---

## 5. «Bu veriyi toplamaya hakkınız var mı?»

> **robots.txt her istekten önce sorulur**, okunamazsa sayfa çekilmez —
> temkinli taraf seçilir. Bot kimliğini açıkça beyan ediyor, tarayıcı taklidi
> yapmıyoruz: `TEKNOFEST-2026-SVARTAL-Bot (+e-posta)`. Kararları üreten kod,
> toplamayı yapan kodun kendisi — ayrı bir denetleyici yazsaydık denetleyicinin
> davranışını göstermiş olurduk.

**Kaynak:** [`docs/kanit/ROBOTS_KONTROL_GUNLUGU.md`](kanit/ROBOTS_KONTROL_GUNLUGU.md) ·
[`docs/kanit/VERI_TOPLAMA_ETIGI.md`](kanit/VERI_TOPLAMA_ETIGI.md) · `make kanit`

**Devamı gelirse — «KVKK?»:** 1.024 ham kaydın tamamı tarandı, kimliği belirli
gerçek kişiye ait veri **yok** ([`docs/kanit/KVKK_TARAMASI.md`](kanit/KVKK_TARAMASI.md),
`make kanit-kvkk`). Toplanan şey kamuya açık kampanya sayfaları.

---

## 6. «Size şu an bir metin versek çalışır mı?»

> **Evet, ve bunu ölçtük.** 9 Ağustos taramasında çekilip korpus seçiminde
> dışarıda kalan **187 sayfa** geliştirme boyunca hiç görülmedi — ne kural
> yazarken bakıldı, ne altın sete girdi, ne bir metrik onlara göre ayarlandı.
> O sayfalarda çöken kayıt **0**, kanıt ihlali **0**, birimsiz değer **0**.
> Arayüzde metin yapıştırma ekranı da var, canlı deneyebilirsiniz.

**Kaynak:** [`docs/GORULMEMIS_METIN.md`](GORULMEMIS_METIN.md) · `make eval-gorulmemis`

---

## 7. «Sonuçlarınız tekrarlanabilir mi?»

> **Bayt düzeyinde değil, ve bunu ölçüp yazdık.** `temperature=0` ve sabit
> tohuma rağmen EVREN aynı girdiye farklı çıktı verebiliyor — ortak vLLM
> sunucusunda sürekli yığınlama var. 98 kayıtlık altın seti aynı kodla iki kez
> çıkardık: 784 hücrenin **7'si oynadı (%0,9)**, makro-F1 0,735 ve 0,724 çıktı.
> **Bu yüzden `make eval` sayısı ±0,01 gürültü taşır** ve biz «0,72» diyoruz,
> «0,724» demiyoruz.

**Kaynak:** [`CLAUDE.md`](../CLAUDE.md) determinizm bölümü ·
[`docs/PROBLEMLER_VE_COZUMLER.md`](PROBLEMLER_VE_COZUMLER.md)

**Devamı gelirse — «peki tekrarlanabilirlik şartsa?»:** `LLM_SAGLAYICI=ollama`
ile yerel yol bayt düzeyinde deterministik. Ayrıca her koşu kod parmak izini
ve kayıt sayısını bir koşu defterine yazıyor (`cikarim_kosulari` tablosu), yani
hangi sayının hangi kodla üretildiği geriye dönük bulunabiliyor.

---

## 8. «`diger` oranı %44,7. Sınıflandırma çalışmıyor mu?»

> **Sistemin en zayıf noktası burası ve kapatmıyoruz.** 931 kaydın 416'sı
> `diger`. Ama dikkat: bu **doluluk** değil **doğruluk** sorusu değildir —
> `kampanya_turu` altın sette 98 örnekle ölçüldü ve **F1 0,796**, yani sınıf
> atadığımız yerde çoğunlukla doğru atıyoruz. `diger`'in yüksekliği asıl olarak
> **veri** sorunu: toplanan sayfaların bir kısmı kampanya değil, genel ürün
> sayfası. Hata analizi ikinci bir modu daha ayırıyor — kategoride haklı ama
> özgüllükte eksik olan vakalar (`konut_finansmani` → `finansman`).

**Kaynak:** [`docs/SONUCLAR.md`](SONUCLAR.md) alan bazlı F1 tablosu · `make durum`

> ⚠️ [`docs/HATA_ANALIZI.md`](HATA_ANALIZI.md) 17 Ağustos ölçümüne ait ve
> `kampanya_turu` için **F1 0,567 · 26/60 yanlış** diyor. O sayı bayattır —
> güncel ölçüm 98 örnekle **0,796** (78/20/20). Hata **modları** hâlâ geçerli,
> **sayıları** alıntılamayın.

**Devamı gelirse — «neden düzeltmediniz?»:** Bir kısmı model değil **veri**
sorunu — kampanya olmayan sayfaları elemek gerekiyor, bu da toplama katmanına
dokunmak demek. Teslim penceresinde ölçümü dondurmayı tercih ettik; düzeltmeyi
yarım yapıp sayıları yeniden üretmek, elimizdeki tutarlı ölçüm setini bozardı.

---

---

## 9. «Neden Text-to-SQL / Vanna.ai kullanmadınız? Yapısal veriyi LLM'e sorsanız daha esnek olmaz mıydı?»

> **Bilerek kullanmadık, çünkü sayısal doğrulama kalkanı Text-to-SQL'i
> denetleyemez.** Bizim iddiamız «model iyi SQL yazıyor» değil, «ekranda görünen
> her sayının yapısal bir karşılığı var». Kalkan cevaptaki her sayıyı
> veritabanındaki kayıtla birebir eşliyor; üretilen SQL'in kendisi yanlış tabloyu
> ya da yanlış satırı seçtiyse dönen sayı **da** yapısaldır ve kalkandan geçer.
> Yani Text-to-SQL, savunmamızın kör noktasına düşen bir katman olurdu.

**Bizim yaptığımız:** niyet yönlendirmesi deterministik (`niyet_belirle`,
kelime örüntüsü), sorgu **kod**, cevap şablonu **kod**. LLM'in bu boru hattındaki
tek işi metinden alan çıkarmaktır — sorgulamak değil.

**Token limiti sorusu buraya bağlanır:** 931 kaydı modele göndermiyoruz, hiç
göndermedik. Karşılaştırma ve sıralama SQLite + saf Python üzerinde koşuyor;
bağlam penceresi bu mimaride bir kısıt değil.

**Kaynak:** [`docs/MIMARI.md`](MIMARI.md) §3.5 orkestrasyon şeması ·
[`kararlar/010-koken-tipli-kalkan.md`](kararlar/010-koken-tipli-kalkan.md)

> **Dürüst sınır:** Text-to-SQL'i ölçmedik, denemedik. «Daha kötü» demiyoruz;
> «savunma modelimize uymuyor» diyoruz. Sorulursa böyle söylenir.

---

## 10. «Neden bu kadar ajan? Beş ajan bir mimari mi, yoksa isimlendirme mi?»

> **Ölçtük: eleştirmen kapatılınca halüsinasyon %0,39'dan %0,51'e çıkıyor.**
> Ajan mimarisi bizde iddia değil, ablasyon tablosunda satırı olan bir şey.
> Beş ajanın her biri **tek bir soruya** bakıyor: kanıt var mı (eleştirmen),
> sayı doğru alana mı ait (yüklem), kampanya kime açık (uygunluk), bu müşteriye
> uyuyor mu (muhakeme), bu soru kime gider (orkestratör).

**Hiyerarşi:** kök ajan sorgu zamanında orkestratördür; çıkarım zamanında sürücü
`boru_hatti.py`'dir ve **o bir ajan değildir** — ajanlar oraya kanca olarak
takılır. Bu ayrımı yapmak «her şey ajandır» bulanıklığını önlüyor.
Şema: [`docs/MIMARI.md`](MIMARI.md) §3.5.

**Beşten dördü LLM kullanmaz.** Aritmetiği ve kısıt çözümünü kasten modele
vermedik. `AjanIzi` her koşuda hangi ajanın LLM kullandığını yazıyor ve arayüzde
panel olarak açılıyor — jüri iddiayı değil koşum kaydını görür.

**Neden hazır ajan çatısı (LangChain/LangGraph) yok:** ihtiyacımız çağrı grafiği
değil sözleşmeydi; `temel.py` 30 satır. Dış çatı, şartname 5.10 lisans ve hava
boşluğu denetiminden geçirilmesi gereken yeni bir bağımlılık yığını getirirdi.

**Kaynak:** [`kararlar/005-ajan-mimarisi.md`](kararlar/005-ajan-mimarisi.md) ·
[`data/ablasyon.json`](../data/ablasyon.json)

---

## 11. «Banka sitesi yarın değişirse ne olur? Sisteminiz bunu nasıl fark eder?»

> **Bugün fark etmez — toplama elle tetiklenir (`make crawl`), zamanlanmış bir
> iş yok.** Bunu saklamıyoruz. Sistemin bu sürümünde tazeleme operatörün
> kararıdır; kurumsal yerleşimde gecelik iş olarak zamanlanması tasarlandı ama
> **kodlanmadı**.

**Kırılmaya karşı bugün ne var:**
- Kazıyıcılarda banka başına değişen tek şey URL keşfidir; gezme, robots kapısı
  ve gövde ayıklama `TemelKaziyici`'de tektir — bir banka bozulduğunda diğer
  sekizi etkilenmez.
- Çıkarım sayfa yapısına değil **metne** bakıyor. Sayfa şablonu değişse bile
  kural + LLM katmanı metinden çalışır; ölçüldü: 318 biçim bozma varyantında
  **%100** değer korunuyor ([`docs/DAYANIKLILIK.md`](DAYANIKLILIK.md)).
- Alan silindiğinde sistem **uydurmuyor**: 51 vakada `uydurdu = 0`.
- `make durum` RAG indeksinin bayat olup olmadığını söyler (korpus izi).

**Ne yok:** `ETag`/`Last-Modified` dinleyicisi, içerik özeti karşılaştırması,
periyodik tetikleyici. Yol haritasında ve
[`docs/KURUMSAL_ENTEGRASYON.md`](KURUMSAL_ENTEGRASYON.md) §5'te tasarımı yazılı.

**Kaynak:** [`docs/DAYANIKLILIK.md`](DAYANIKLILIK.md) · `src/collector/kaziyicilar/`

---

## Sayı sorulursa — hızlı kart

| Ne | Değer | Nereden |
|---|---|---|
| Ham sayfa (toplanan) | **1.024** | `data/raw/**/*.json` |
| İşlenen kampanya | **931** | `make durum` |
| Banka | **9 faal** (BDDK listesinin tamamı) | `make durum` |
| Makro-F1 | **0,818** (GA 0,750–0,866, n=98) | `docs/SONUCLAR.md` |
| Sayısal alan doğruluğu | **0,930** | `docs/SONUCLAR.md` |
| Halüsinasyon oranı | **%0,45** (hedef ≤%3) | `docs/SONUCLAR.md` |
| Kalkan yanlış blok | **%0** (0/35) | `docs/SONUCLAR.md` |
| Alan doluluğu | **%25,2** (3.752/14.896) | `docs/SONUCLAR.md` |
| Test | **847** + doctest | `make test` |
| RAG paragraf | **13.763** · 1024 boyut | `make durum` |

> ⚠️ **1.024 ile 931 karıştırılmamalı.** 1.024 toplanan ham sayfadır (KVKK
> taraması o küme üzerinde koştu); 931 ölçümlerin üzerinde koştuğu işlenmiş
> kampanyadır — 26 Ağustos'ta süresi geçmiş kampanyalar ayıklandı. Doğruluk,
> doluluk ve kapsam sayıları hep **931**'e aittir.
>
> Tek istisna [`data/ablasyon.json`](../data/ablasyon.json): ayıklamadan önce
> 1.024 kayıt üzerinde koşuldu ve yeniden koşulmadı. Sunumdaki ablasyon tablosu
> bu etiketi taşıyor. **Sorulursa saklanmaz:** ablasyonun karşılaştırdığı şey
> kollar arası farktır, beş kol da aynı 1.024 kayıt üzerinde koştuğu için
> karşılaştırma kendi içinde geçerlidir.

---

## Kim neyi savunuyor

| Alan | Kim | Dayanak |
|---|---|---|
| Şema, mimari, hibrit çıkarım | **Eren** | `src/schema.py` · [`docs/MIMARI.md`](MIMARI.md) · [`kararlar/`](kararlar/) |
| Ölçüm, altın set, ablasyon | **Eren** (S-* devri) | [`docs/DEGERLENDIRME_YONTEMI.md`](DEGERLENDIRME_YONTEMI.md) |
| Veri toplama, etik, lisans | **Görkem** | [`docs/kanit/`](kanit/) · [`docs/LISANSLAR.md`](LISANSLAR.md) |
| Arayüz, chatbot, demo | **Esra** | `app/` · [`docs/KULLANIM_KILAVUZU.md`](KULLANIM_KILAVUZU.md) |

Samet 18 Ağustos'tan beri çalışamaz durumda; `S-*` görevleri Eren'e devredildi
ve bu panoda açıkça yazılı. **Sorulursa olduğu gibi söylenir.**
