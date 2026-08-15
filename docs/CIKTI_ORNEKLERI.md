# Model Çıktılarının Örnekleri

**Şartname madde 6**, proje dokümantasyonunda *"model çıktılarının örnekleri"*
başlığını zorunlu tutuyor. Bu dosyadaki çıktıların tamamı **gerçek koşudan**
alınmıştır (15 Ağustos 2026, 96 kampanya, Qwen3.5-4B Q4 + kural katmanı);
hiçbiri elle yazılmamış veya güzelleştirilmemiştir.

Yeniden üretmek için: `make extract && make eval`

---

## 1. Şartnamenin kendi örneği (madde 11, Senaryo-1)

Jüri şartnamede üç banka metni ve bunlardan çıkarılmasını beklediği tabloyu
veriyor. Sistemin bu metinlerdeki çıktısı:

**Girdi — A Bankası:**
> "Yeni ev sahibi olmak isteyen müşterilerimize özel %1,89 kâr payı oranı ile
> 120 aya kadar konut finansmanı fırsatı sunulmaktadır. Kampanya kapsamında
> 50.000 TL'ye kadar dosya masrafı alınmamaktadır. Kampanya 31 Aralık 2026
> tarihine kadar geçerlidir."

**Çıktı:**

| Alan | Değer | Yöntem |
|---|---|---|
| `kampanya_turu` | `konut_finansmani` | llm |
| `kar_payi_orani` | `1.89` | kural |
| `vade_ay_max` | `120` | kural |
| `masrafsiz_mi` | `True` | kural |
| `tahsis_ucreti` | **Belirtilmemiş** | — |
| `kampanya_bitis` | `2026-12-31` | kural |

Üç bankanın tamamında şartname tablosuyla **11/11 uyum**. Kalıcı test:
[`tests/test_kural.py::TestSartnameMadde11`](../tests/test_kural.py).

Dikkat edilecek iki nokta:

- `tahsis_ucreti` **Belirtilmemiş** — metindeki 50.000 TL bir ücret değil,
  ücretin *alınmadığı* üst sınırdır. Sistem "alınmamaktadır" olumsuzlamasını
  tanıyıp o sayıyı ücret olarak almaz.
- C Bankası metninde masraftan hiç söz edilmediği için `masrafsiz_mi` boş
  bırakılır — "masraf yok" demek, olmayan bir avantaj vaat etmek olurdu.

---

## 2. Kanıt zinciri — her değer nereden geldi

Sistemin en ayırt edici çıktısı budur: hiçbir alan kaynaksız üretilmez.

**Kaynak:** `https://www.albaraka.com.tr/tr/kampanyalar/detay/dijital-musterilere-ozel-pratik-finansman-kart`

```json
{
  "kar_payi_orani": {
    "deger": 3.95,
    "ham_ifade": "3,95%",
    "yontem": "kural",
    "guven": 0.852,
    "kaynak": {
      "url": "https://www.albaraka.com.tr/tr/kampanyalar/detay/dijital-...",
      "cekim_tarihi": "2026-08-09T14:00:04",
      "alinti": "3,95% |",
      "karakter_baslangic": 1183,
      "karakter_bitis": 1191
    }
  },
  "vade_ay_max": { "deger": 36, "ham_ifade": "36 aya", "yontem": "kural" }
}
```

`ham_ifade` metinde geçtiği hâli korur (`3,95%`), `deger` normalize edilmiş
hâlidir (`3.95`). Normalizasyon hatalı olsa bile kanıt kaybolmaz.

---

## 3. "Belirtilmemiş" — bilinmeyeni beyan etmek

Aynı kayıtta doldurulamayan alanlar `None` olarak gizlenmez:

```
urun_turu       : Belirtilmemiş   (yontem=belirtilmemis)
hedef_kitle     : Belirtilmemiş   (yontem=belirtilmemis)
kar_payi_orani  : Belirtilmemiş   (yontem=belirtilmemis)
tahsis_ucreti   : Belirtilmemiş   (yontem=belirtilmemis)
kampanya_bitis  : Belirtilmemiş   (yontem=belirtilmemis)
```

Şartnamenin madde 11 örnek tablosu da bu ifadeyi kullanıyor. Boş bırakmak,
uydurmaktan her zaman iyidir; `Alan(deger=..., yontem="belirtilmemis")`
şema düzeyinde `ValueError` fırlatır.

---

## 4. Bankalar arası karşılaştırma (şartname 5.7)

Konut finansmanı kampanyaları, "en avantajlı" kriterine göre:

| Banka | Kâr payı | Vade | Tutar | Masrafsız |
|---|---|---|---|---|
| Albaraka Türk | Belirtilmemiş | 120 ay | 20.000.000 TL | ✔ |
| Dünya Katılım | %1,00 | 36 ay | 20.000.000 TL | ✔ |
| Emlak Katılım | Belirtilmemiş | 120 ay | 5.000.000 TL | — |
| Kuveyt Türk | Belirtilmemiş | 60 ay | Belirtilmemiş | — |

**Skor kara kutu değildir** — her satırın dökümü verilir:

```
Albaraka Türk  -> Skor 0.725 = kar_payi: 0.200 + masraf: 0.250 + vade: 0.200
                             + odul: 0.075 | Eksik veri: kar_payi_orani, odul_miktari
Dünya Katılım  -> Skor 0.725 = kar_payi: 0.400 + masraf: 0.250 + vade: 0.000
                             + odul: 0.075 | Eksik veri: odul_miktari
```

Eksik alanlar nötr (0,5) sayılır ve **kullanıcıya bildirilir**; ağırlıklar
arayüzden değiştirilebilir.

### Toplam maliyet (finansman maliyeti kavramı)

`toplam_maliyet(anapara=1.000.000 TL, aylık kâr payı %2,05, vade 120 ay, tahsis 5.000 TL)`

```json
{ "aylik_taksit": 22467.89, "toplam_geri_odeme": 2701147.03,
  "toplam_kar_payi": 1696147.03, "toplam_maliyet_orani": 170.11 }
```

---

## 5. Chatbot çıktıları

**Tekil sorgu** — sayısal cevap yapısal veriden gelir, RAG'dan değil:

```
SORU : En uzun vade hangi bankada?
NİYET: karsilastirma · sayısal doğrulama: GEÇTİ

- **Vade** açısından **Albaraka Türk Katılım Bankası A.Ş.** daha avantajlıdır,
  çünkü 120 ay vade sunmaktadır.
- **Finansman tutarı** açısından **Ziraat Katılım Bankası A.Ş.** daha
  avantajlıdır, çünkü 150.000.000 TL'ye kadar finansman sağlamaktadır.
```

**Kapsam dışı soru** — reddedilir, uydurulmaz:

```
SORU : Hava durumu nasıl?
NİYET: kapsam_disi

Bu soru sistemin kapsamı dışında. Ben yalnızca Türkiye'deki katılım
bankalarının kampanya ve ürün bilgileri hakkında toplanmış veriye dayanarak
cevap verebiliyorum.
```

**Sayısal doğrulama kalkanı** — cevaptaki her sayının yapısal kayıtta karşılığı
aranır; bulunamazsa cevap **verilmez**:

```
Cevabı üretirken doğrulayamadığım sayısal değerler oluştu, bu yüzden cevabı
vermiyorum. Bu bilgi veri setinde doğrulanabilir biçimde bulunmuyor.
```

---

## 6. Toplu metrikler (15 Ağustos koşusu)

| Metrik | Değer | Hedef |
|---|---|---|
| İşlenen kampanya | 96 (8 banka) | — |
| Şema geçerliliği | 1,00 | 1,00 ✅ |
| Halüsinasyon oranı | %0,28 | ≤ %3 ✅ |
| Alan doluluğu | %23,0 | — |
| Ortalama güven | 0,777 | — |
| `kampanya_turu` doluluğu | %100 | — |

Yöntem dağılımı: kural 116 alan · LLM 212 alan · hibrit 11 alan.
Güncel tablo: [`docs/SONUCLAR.md`](SONUCLAR.md) (`make eval` üretir).

### Yakalanan halüsinasyon örneği

Denetim, LLM'in özete soktuğu ve ham metinde bulunmayan bir sayıyı yakaladı:

```
kampanya_kosullari: özette geçen '1,89' sayısı ham metinde yok
  -> https://www.albaraka.com.tr/tr/bireysel/finansmanlar/tasit-finansmani
```

Bu tür ihlaller raporlanır ve `make eval` çıktısında sayılır.

---

## 7. Bilinen sınırlar — dürüst değerlendirme

Jüriye eksiksiz bir sistem sunmuyoruz; ölçülmüş bir sistem sunuyoruz.

**Ücret tarifesi tablolarında kâr payı oranı yanılıyor.** Bankaların
"ürün ve hizmet ücretleri" sayfalarındaki tablolarda tahsis ücreti oranı
(%0,2–0,5) kâr payı oranı sanılabiliyor:

```
Tahsis Ücreti | % 0.5 | ...        -> kar_payi_orani = 0.5   ❌
6 | 4,42% | 0,50% | 13,35% | ...   -> kar_payi_orani = 0.5   ❌ (gerçek: 4,42%)
```

Nedeni, "en düşük oran vitrin oranıdır" varsayımının (`secim="en_dusuk"`)
tablo sayfalarında ters çalışması. Kampanya sayfalarında doğru davranıyor.
Çözüm yönü: tablo sütun semantiği veya `tahsis`/`bsmv` dışlayıcıları.

**Kapsam.** 10 faal katılım bankasının 8'inden veri var; T.O.M. ve Adil
Katılım'ın kampanya sayfaları bulunamadı (bkz. `data/banks.yaml` notları).

**Altın set metrikleri beklemede.** Alan bazlı doğruluk, F1 ve ablasyon
tablosu etiketleme bitince hesaplanacak; yukarıdaki metrikler altın set
gerektirmeyenlerdir.
