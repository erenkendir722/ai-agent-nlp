# Kullanım Kılavuzu

**Kime:** Bankada çalışan, günlük işinde rakip kampanyalara bakan kişiye.
**Teknik bilgi gerekmez.** Sistem beş ekrandan oluşur; her ekranın ne işe
yaradığı ve nasıl okunacağı aşağıda.

> Kurulum ve çalıştırma adımları ayrı dosyada: [`KURULUM.md`](KURULUM.md).
> Kısaca: `make run` komutu tarayıcıda arayüzü açar.

---

## Önce üç kavram

Ekranlarda sürekli karşınıza çıkacak üç şey var:

**Güven skoru (0–1).** Sistemin o değeri ne kadar sağlam bir kanıta dayandırdığı.
1'e yakınsa değer metinde açıkça yazıyordu; 0,7 civarındaysa yorumla çıkarıldı.
Skor, değerin *doğruluk garantisi* değil, *dayanağının gücüdür*.

**Yöntem (`kural` / `llm` / `hibrit`).** Değeri hangi katman buldu:
- `kural` — metinde kalıp eşleşmesiyle bulundu (örn. «%1,89»). En sağlamı.
- `llm` — dil modeli metni okuyup çıkardı. Kalıba sığmayan ifadeler için.
- `hibrit` — ikisi de aynı değeri buldu; en güvenilir durum.

**Belirtilmemiş.** Sistem o bilgiyi bulamadı ve **uydurmadı**. Boş hücre bir
arıza değil, bilinçli bir cevaptır: kampanya sayfasında o bilgi yoksa sistem
"bilmiyorum" der.

---

## 1. Genel Bakış — «elimde ne var?»

Açılış ekranı. Toplanan kampanyaların özeti:

- **Üst şeritte** kaç kampanya, kaç banka, son çekim tarihi.
- **Kampanya türü dağılımı** — hangi türden kaç kampanya var.
- **Banka × tür ısı haritası** — hangi banka hangi alanda yoğunlaşmış.
- **Veri Kalitesi ve Şeffaflık** bölümü — alan doluluk oranları ve güven skoru
  dağılımı.

**Nasıl okunur:** Doluluk oranı düşük bir alan (örn. kâr payı oranı) sistemin
başarısızlığı değil, çoğu bankanın oranı kampanya sayfasında yayımlamamasıdır.
Ekran bunu böyle söyler; olduğundan iyi göstermez.

---

## 2. Müşteri Profili — «karşımdaki müşteriye ne önerebilirim?»

Sistemin en çok iş gören ekranı. Soldaki panele müşteriyi tarif edersiniz:
müşteri tipi (yeni / mevcut / maaş müşterisi / segment), talep edilen tutar,
vade, müşterinin mevcut ürünleri.

Sistem her kampanyayı bu profile karşı **tek tek çözer** ve iki liste verir:

1. **Uygun kampanyalar** — toplam maliyete göre sıralı.
2. **Uygun olmayanlar ve sebepleri** — «minimum tutar 1.000.000 TL, talep
   800.000 TL» gibi. Elenen kampanyayı gizlemek yerine *neden* elendiğini
   söylemek, müşteriye verilecek cevabı da hazırlar.

**Sıralama neye göre?** Manşet orana göre değil, **toplam geri ödemeye** göre.
%1,87 oranlı ama 20.000 TL masraflı bir ürün, %1,89 oranlı masrafsız üründen
pahalı çıkabilir — sistem bu hesabı kendisi yapar.

**«Ajan izleri» paneli.** Her sonucun altında, o cevabı üreten adımların kaydı
durur: hangi adım çalıştı, ne kadar sürdü, dil modeli kullanıldı mı. Uygunluk
kontrolü ve tüm aritmetik **dil modeli olmadan**, sabit kodla yapılır; panel
bunu her koşuda gösterir.

---

## 3. Karşılaştırma — «hangi ürün daha avantajlı?»

Kampanyaları yan yana koyan ekran.

- **Filtreler:** banka, kampanya türü, tarih aralığı, serbest metin araması,
  minimum güven skoru.
- **Ağırlık kaydırıcıları:** kâr payı, masraf, vade ve ödülün sıralamadaki
  ağırlığını siz belirlersiniz. Varsayılan %40 / %25 / %20 / %15.
  *«En avantajlı» mutlak bir gerçek değil, bir tercih bileşimidir; sistem o
  tercihi gizlemez, size verir.*
- **Toplam maliyet hesabı:** ortak bir anapara ve vade girip kampanyaları aynı
  tabanda karşılaştırabilirsiniz.
- **Satır açıldığında** o kampanyanın tüm alanları, güven skorları ve **kaynak
  alıntısı** görünür — değerin geldiği cümle ve sayfanın adresi.
- **Dışa aktarma:** tablo tek tıkla CSV olarak iner (Excel'de açılır).

**Uyarılar.** Karşılaştırılamayacak şeyler karşılaştırıldığında ekran uyarı
verir (örn. farklı vadeler, biri masrafsız diğeri masraflı ürünler).

---

## 4. Kampanya Asistanı — «sorup öğrenmek»

Serbest yazılı soru sorabileceğiniz sohbet ekranı. Örnek: *«En uzun vade hangi
bankada?»*, *«Konut finansmanında en düşük kâr payı kimde?»*

Her cevapta şunlar görünür:
- **Niyet etiketi** — sorunun nasıl anlaşıldığı.
- **Kaynak kartları** — cevabın dayandığı kampanya kayıtları, adresleriyle.
- **Doğrulama rozeti** — ✅ ya da ⛔.

**Doğrulama rozeti nedir?** Sistem, cevabın içindeki her sayının yapısal
veritabanında ya da kaynak metinde karşılığı olup olmadığını denetler.
Karşılığı olmayan bir sayı varsa cevap **gösterilmez**. Yani asistan
"muhtemelen %2 civarıdır" gibi bir cümle kuramaz — mimari olarak kuramaz.

Örnek sorulardan biri (**«Kampanya koşulları neler?»**) bu kalkanı bilerek
tetikler: sistemin kendi kendini nasıl frenlediğini görmek için oradadır.

---

## 5. Metin Analizi — «kendi metnimi verip deneyeyim»

Elinizdeki herhangi bir kampanya metnini yapıştırıp **Çıkar** düğmesine
basarsınız; sistem o metinden alanları çıkarır ve tabloyu gösterir: alan,
değer, birim, güven, yöntem ve her satırın kaynak alıntısı.

Şartnamedeki örnek metin hazır bir düğmeyle yüklenebilir. Bu ekran, sistemin
daha önce hiç görmediği bir metinde nasıl davrandığını göstermek içindir.

---

## Sık sorulanlar

**Veriler ne kadar günceldir?**
Her kayıt kendi çekim tarihini taşır; Genel Bakış'ta son çekim tarihi yazar.
Kampanyalar sürelidir, tarihi geçmiş kayıtlar ayıklanabilir.

**Sistem internete veri gönderiyor mu?**
Kural katmanı, karşılaştırma, uygunluk ve asistanın hesap kısmı tamamen yerel
çalışır. Metinden alan çıkarımı için kullanılan dil modeli, yarışma için tahsis
edilmiş servis üzerinden çalışır; kurum içi kurulumda tamamen yerel modele
(`make extract-yerel`) tek komutla dönülür. Müşteri verisi hiçbir koşulda dışarı
çıkmaz.

**Bir değerin yanlış olduğunu düşünüyorum.**
Satırı açın: kaynak alıntısı ve sayfa adresi orada. Alıntı yanlışsa sorun
çıkarımdadır; alıntı doğru ama sayfa güncel değilse veri eskimiştir.

**Neden bazı kampanyalarda hiç kâr payı oranı yok?**
Çoğu banka oranı kampanya sayfasında yayımlamıyor, başvuru ekranında
gösteriyor. Sistem olmayan sayıyı uydurmaz.

---

**İlgili belgeler:** [`KURULUM.md`](KURULUM.md) ·
[`KARSILASTIRMA_YONTEMI.md`](KARSILASTIRMA_YONTEMI.md) (sıralama formülü) ·
[`SONUCLAR.md`](SONUCLAR.md) (ölçülen doğruluk) ·
[`KAPSAM_RAPORU.md`](KAPSAM_RAPORU.md) (veri kapsamı ve sınırları)
