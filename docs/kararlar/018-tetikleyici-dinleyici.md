# ADR 018 — Tetikleyici tanımlı ama kurulu değil; dinleyici içerik özetiyle çalışır

**Tarih:** 27 Ağustos 2026
**Durum:** kabul edildi
**Bağlam:** G-17 · mentör geri bildirimi madde 3 ([`../MENTOR_GERI_BILDIRIMI.md`](../MENTOR_GERI_BILDIRIMI.md))

## Bağlam

Mentör, «klasik try-catch ötesinde tetikleyici (trigger) ve dinleyici (listener)
mantıkları; kampanya açılış/kapanış saatlerine göre (08:00, 17:00, 24:00)
periyodik tetikleyici ya da metadata kontrolü» önerdi. O ana kadar toplama
yalnız elle tetikleniyordu (`make crawl`); `docs/JURI_PROVASI.md` §11 bunu
açıkça «yok» diye yazıyordu.

## Karar

Mekanizma **iki parçaya ayrıldı ve yalnız biri kuruldu.**

| Parça | Durum | Yer |
|---|---|---|
| **Dinleyici** — sayfa değişmiş mi | ✅ **kodda ve koşuyor** | `src/izleme/dinleyici.py` |
| **Tetikleyici** — ne zaman koşacak | 🔒 **tanımlı ama kurulu değil** | `src/izleme/tetikleyici.py` |

Dinleyici **değişikliği TESPİT eder, veriyi TAZELEMEZ.** Değişmiş bulduğu
sayfayı kendiliğinden yeniden çekmez.

### Neden tetikleyici kurulmadı

1. `data/raw` ve `data/katilim.db` teslim için **donmuş** durumda; yayımlanan
   doğruluk, doluluk ve kapsam sayıları o veri üzerinde ölçüldü. Kendiliğinden
   koşan bir toplama işi, `make eval` çıktısı ile `docs/SONUCLAR.md` arasında
   sessiz bir ayrışma üretirdi.
2. Kurulu bir zamanlayıcının çalıştığı **gösterilemez.** Dinleyici arayüzden
   elle koşturulup sonucu ekranda izlenebilir; `crontab` satırı izlenemez.

`Tetikleyici.kurulu` bu yüzden `False` ve bunu koruyan bir test var
(`tests/test_izleme.py::test_varsayilan_olarak_kurulu_degildir`) — kurulum bir
karardır, kaza olamaz. Ürünleşince kurulacak satır `cron_satiri()` ile
üretiliyor: `0 0,8,17 * * * make tazelik`.

## Dinleyici neden iki kademeli — ÖLÇÜM

Dokuz bankanın her birinden bir kampanya URL'i yoklandı (27 Ağustos):

| | |
|---|---|
| `ETag` ya da `Last-Modified` veren | **2 / 9** (Kuveyt Türk, Türkiye Finans) |
| Hiçbir doğrulayıcı vermeyen | **7 / 9** |
| Koşullu GET'e `304` dönen | **2 / 2** — veren iki banka da doğru davrandı |

Yani G-17'nin önerdiği «ucuz yol» tek başına bankaların yedisini kapsamıyor;
içerik özeti şart. Tersi de doğru: veren ikisinde sayfa gövdesi hiç
indirilmiyor. Bu yüzden **önce koşullu GET, olmazsa içerik özeti.**

## Taban çizgisi kendi yolundan kurulur — en kritik karar

Özet, `data/raw`'daki `govde_metin` ile **karşılaştırılmaz.** O gövdeyi
Selenium üretti; dinleyici ise tarayıcısız (`httpx`) çekiyor. Ölçüldü:

| | |
|---|---|
| İki yolun birebir aynı gövdeyi verdiği banka | **7 / 9** |
| Farklı verdiği banka | **2 / 9** — Vakıf Katılım, Dünya Katılım |

Farkın ne olduğuna bakıldı: Vakıf Katılım'da `httpx` fazladan menü başlığı
görüyor (`SİZE ÖZEL ÇÖZÜMLER`), Dünya Katılım'da `trafilatura` tablo satırlarını
`| ` önekiyle basıyor. **İkisi de içerik değişikliği değil, render yolu farkı.**
Selenium tabanına karşı karşılaştırılsaydı bu iki banka her koşuda «değişti»
derdi.

Bu yüzden **ilk yoklama `ilk_kayit` döner**: taban çizgisi kurulur, değişiklik
iddia edilmez. Karşılaştırma ikinci yoklamadan itibaren, elmayla elma.

## Özet bütün boşlukları atar — ikinci ölçüm

Boşluk *dizilerini* daraltmak yetmedi. Albaraka
`konut-ve-tasit-finansmani-kampanyasi` sekiz ardışık çekimde iki ayrı gövde
verdi ve fark **tek bir boşluktu**:

```
çekim 1,2,3,4,6,8  →  "%3,19 'danbaşlayan kâr oranı"   (682 karakter)
çekim 5,7          →  "%3,19 'dan başlayan kâr oranı"  (683 karakter)
```

`" ".join(metin.split())` boşluk dizilerini daraltır ama **eksik boşluğu
ekleyemez**; iki varyant farklı özet üretiyordu ve sayfa dakikada bir
«değişti» diyordu.

Karar: özet `"".join(metin.split())` üzerinden alınır — boşluk tamamen atılır.
Gerekçe: **değişiklik tespitinde boşluk içerik değildir.** Gerçek bir kampanya
değişikliği rakam ya da kelime değiştirir (`%1,89` → `%2,49`, `120 ay` →
`60 ay`); bunların hiçbiri boşluk atılınca kaybolmaz. Yanlış alarm ise
kaçırılan değişiklikten pahalıdır: her koşuda bağıran bir uyarı okunmaz hâle
gelir ve gerçek değişiklik de onunla birlikte gözden kaçar.

**Düzeltme sonrası ölçüm:** aynı 6 adreslik küme, 5 ardışık koşu →
1. koşu 6 `ilk_kayit`, 2.–5. koşular **6 `değişmedi`, 0 yanlış alarm.**

## Sonuçlar

- `make tazelik [adet=N] [demo=1]` · arayüzde **Boru Hattı → 3 · Veri Tazeliği**
- Yazılan tek yer `data/izleme/tazelik.json` (`.gitignore`'da — taban çizgisi
  onu kuran makinenin ağ yolundan üretilir, taşınamaz)
- `docs/JURI_PROVASI.md` §11 artık «hiçbiri yok» demiyor: dinleyici ve içerik
  özeti var, periyodik tetikleyici bilinçli olarak kurulu değil
- Şemaya dokunulmadı (`SEMA_SURUMU` değişmedi) — `HamKayit` üzerinde yeni alan
  yok, taban çizgisi ayrı dosyada duruyor

## Reddedilen seçenekler

**Zamanlayıcıyı kurmak.** Donmuş ölçüm verisine yazma riski ve
gösterilemezlik; yukarıdaki iki gerekçe.

**Değişeni otomatik yeniden toplamak.** Selenium'a bağımlı, koşu süresi
öngörülemez ve `data/raw`'a yazar. Tazeleme operatörün kararı olarak kaldı.

**Farkı normalize edip Selenium tabanına karşı karşılaştırmak.** Menü
başlığını ve tablo önekini eleyen bir temizlik yazılabilirdi; ama her
normalizasyon kuralı aynı zamanda bir **körleşme** kuralıdır — elenen şey bir
gün gerçekten değişebilir. Aynı yoldan taban kurmak bu kurallara hiç ihtiyaç
duymuyor.
