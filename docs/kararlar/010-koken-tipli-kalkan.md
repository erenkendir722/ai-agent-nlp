# ADR 010 — Sayısal doğrulama kalkanı köken tipli hâle getirildi

**Tarih:** 19 Ağustos 2026 · **Durum:** kabul edildi · **Sorumlu:** Eren
**İlgili bulgu:** `docs/DUZELTME_TASARIMI.md` § 1.2
**Şema etkisi:** yok (`src/schema.py` değişmedi, v1.1.0 korunuyor)

## Bağlam

Sayısal doğrulama kalkanı sistemin en özgün iddiasıdır: *"chatbot uydurma kâr
payı oranı söyleyemez, çünkü mimari olarak imkânsız."* Kalkan, cevaptaki her
sayının getirilen **yapısal kayıtta** karşılığı olmasını arıyordu.

18 Ağustos ölçümü bu tasarımın iki yönlü hata verdiğini gösterdi.

**Yanlış blok — %14,3.** `eval/sorular.yaml`'daki 35 meşru sorunun 5'i
engellendi. Reddedilen sayıların hepsi **bankanın kendi metninden birebir
alıntıydı**:

```
"Hayat Finans başvuru nasıl yapılır?"        -> ['17']      (17 iş günü)
"Başvuru için hangi belgeler gerekli?"       -> ['6698']    (KVKK kanun no)
"Kampanya kapsamı nedir?"                    -> ['60']
"Yeni müşteriler için hangi kampanyalar var?"-> ['95']
"Dünya Katılım kart kampanyası kapsamı?"     -> ['0,1']
```

Koşul sorularında (`_kosul_cevabi`) cevap, kaynak metinden getirilen
paragraflardan oluşuyor; kalkan ise onları **yapısal alana** karşı
denetliyordu. Yanlış yere bakıyordu. Üstelik `niyet_belirle` eşleşmeyen her
soruyu varsayılan olarak bu yola gönderiyor — yani jüri serbest bir soru
yazdığında blok olasılığı yüksekti.

**Kör nokta.** `Cevap.dogrulanacak_metin` ikili bir muafiyetti: bir metin ya
tümüyle denetlenir ya hiç denetlenmezdi. Karşılaştırma cevabının "genel
değerlendirme" bölümü tümüyle muaftı; oraya yazılan skor ve ağırlıklar
hiçbir denetimden geçmiyordu.

## Değerlendirilen seçenekler

| Seçenek | Neden reddedildi |
|---|---|
| İzin listesine `ham_metin`'in tüm sayılarını eklemek | Kalkanı kökten gevşetir: "sayfada geçen herhangi bir sayı" meşru olurdu. `CLAUDE.md`: *"Kalkanı zayıflatma."* |
| `_kosul_cevabi`'na `dogrulanacak_metin=""` vermek | Koşul yolunu tümüyle denetimsiz bırakır; kör noktayı çoğaltır. |
| Alıntıları tırnak/regex ile atlamak | Biçime bağlı ezber; tırnak biçimi değişince sessizce çöker. |

Üçü de yamadır: aynı hata sınıfının ikinci örneğini yakalamazlar.

## Karar

**Cevap artık tek bir metin değil, her biri kökenini taşıyan parçalardan
oluşur.** Kalkan her parçayı kökenine göre farklı ölçütle denetler.

| Köken | Ölçüt | Durum |
|---|---|---|
| `YAPISAL` | yapısal kayıtta birebir karşılığı olmalı | **değişmedi** |
| `ALINTI` | alıntı kaynak metnin ALT DİZESİ olmalı; sayıları alıntının içinde geçmeli | **yeni garanti** |
| `SISTEM` | sayılar `hesap` girdilerinden yeniden üretilebilmeli | **kör nokta kapandı** |
| `DUZ` | sayı içeremez — yapıcıda denetlenir | yeni |
| `DENETIMSIZ` | atlanır ama SAYILIR (miras yol) | ölçülen borç |

Sözleşme `CevapParcasi.__post_init__` içinde denetlenir: `ALINTI` kayıt
kimliği ve ham alıntı olmadan, `SISTEM` `hesap` olmadan, `DUZ` sayı içererek
**kurulamaz**. Bu, `Alan._kanit_zinciri` ile aynı reflekstir — eksik kanıtla
nesne oluşturulamaz.

## Sonuç

Bu değişiklik kalkanı **gevşetmez, sertleştirir**:

- Alıntı bütünlüğü denetimi **bugün hiç yoktu** — uydurulmuş bir "alıntı"
  cevaba girebilirdi. Artık giremez.
- Hesap doğrulaması **bugün hiç yoktu** — açıklama bölümüne istenen skor
  yazılabilirdi. Artık yakalanır.
- Gevşeyen tek şey, bankanın kendi metnindeki sayının "uydurma" sayılması
  hatasıydı.

`CLAUDE.md`'nin talimatı birebir uygulandı: *"Kalkan yanlış pozitif veriyorsa
çözüm kalkanı gevşetmek değil, denetlenecek metni doğru seçmektir."* Doğru
seçim, metnin kökenini bildirmekten geçiyordu.

### Ölçüm

| Metrik | 18 Ağu | 19 Ağu | Nerede |
|---|---|---|---|
| Yanlış blok oranı (35 meşru soru) | %14,3 (5) | **%0 (0)** | `docs/SONUCLAR.md` |
| Denetimsiz parça oranı | — | **%0** | `docs/SONUCLAR.md` |
| Test sayısı | 459 | **506** | `make test` |

Ölçüm `eval/sorular.yaml` üzerinden `make eval` ile her koşuda tekrarlanır;
soru kümesi sabittir ki iki koşu karşılaştırılabilsin.

## Geriye dönük uyum

`Cevap(metin=…, dogrulanacak_metin=…)` miras çağrısı **çalışmaya devam eder**
ve bugünkü anlamını birebir korur: denetlenen bölüm `YAPISAL`, muaf tutulan
bölüm `DENETIMSIZ` parça olur. Muafiyet yok olmadı — **görünür ve sayılabilir**
hâle geldi. `src/ajanlar/orkestrator.py` hâlâ bu yolu kullanıyor;
`denetimsiz_parca_orani` metriği o borcu takip eder, hedef sıfırdır.

`tests/test_kalkan_kokenli.py::TestUreticiKapsamasi` chatbot üreticilerinin
miras yola dönmesini engeller: yeni bir üretici `metin=` ile yazılırsa test
kırmızıya döner.
