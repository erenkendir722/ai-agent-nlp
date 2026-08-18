# ADR 009 — Sayısal alanlar birimlerini taşır

**Tarih:** 19 Ağustos 2026 · **Durum:** kabul edildi · **Sorumlu:** Eren
**İlgili bulgu:** `docs/DUZELTME_TASARIMI.md` § 1.1
**Şema etkisi:** **v1.1.0 → v1.2.0** (eklemeli; `Alan.birim` alanı)

## Bağlam

`docs/SONUCLAR.md`'nin dayandığı veritabanında `tahsis_ucreti` sütunu şunları
yan yana tutuyordu:

| Değer | Ham ifade | Gerçekte |
|---|---|---|
| `0.5` | `0,50%` | maliyet tablosundaki **oran** |
| `75.0` | `%75` | komisyon **indirimi** (ayrı hata, bkz. ADR 011 planı) |
| `500.0` | `500 TL` | gerçek **TL** tutarı |

Şema bunu itiraf ediyordu ama çözmüyordu:

```python
tahsis_ucreti: Alan = Field(default_factory=Alan.yok)  # TL veya %, float
```

Bilginin kaybolduğu satır tekti:

```python
ayristirici=lambda s: para_ayristir(s, birim_zorunlu=True) or oran_ayristir(s)
```

Bu `or`, "önce TL dene, olmazsa yüzde dene" diyor ve **hangisinin tuttuğunu
çağırana söylemiyor**. Ayrıştırıcılar birimi tespit ediyor (`_PARA_BIRIMI.search`,
`"%" in temiz`) ve hemen ardından atıyorlardı.

### Ölçülen iki sonuç

**1. Arayüz yanlış yazıyordu.** `chatbot._ALAN_ETIKETLERI` alan başına sabit bir
şablon tutuyordu (`"tahsis_ucreti": ("Tahsis ücreti", "{} TL")`), dolayısıyla
`%0,50` ekranda **«Tahsis ücreti: 0,50 TL»** görünüyordu. Bankacılık jürisinin
saniyeler içinde yakalayacağı bir hata.

**2. Sıralama tersine dönüyordu.** `Kriter.EN_DUSUK_MASRAF` ve `avantaj_skorla`,
`{0,5 · 75,0 · 500,0}` kümesini ortak birimmiş gibi min-maks normalize ediyordu.
Sonuç: `%0,50`'lik ücret **«en ucuz»**, `500 TL` **«en pahalı»**. Oysa
100.000 TL'lik bir finansmanda **ikisi de 500 TL'dir** — yani eşittirler.

Hata `tahsis_ucreti`'ne özgü değildi: `alisveris_puani` (TL/puan),
`indirim_orani`, `odul_miktari` aynı hastalığın taşıyıcılarıydı.

## Değerlendirilen seçenekler

| Seçenek | Neden reddedildi |
|---|---|
| `tahsis_ucreti_tipi: str` bayrağı | Yalnız bir alanı kurtarır. Onuncu alanda onuncu bayrak yazılır; sınıf kapanmaz. |
| Ekranda `< 100` ise yüzde varsaymak | Ezber. `%0,50` ile `0,50 TL` sayı olarak ayırt edilemez; 120 TL'lik gerçek ücret yüzde sanılır. |
| Vakıf'ın `%75`'i için `"komisyon indirimi"` vetosu | Tek kaydın ezberi. Yarın *"aidat iadesi %60"* gelir, liste büyür. |
| Ayrıştırıcıların `Nicelik` döndürmesi | 84 çağrı yeri var; çoğu (`orkestrator` profil ayrıştırma, `altin_set` aracı, doctest'ler) çıplak `float` bekliyor ve birimden fayda görmüyor. Kazançsız geniş yüzey. |

## Karar

**Birim, `Alan` üzerinde taşınır** — `deger`'in içinde değil.

```python
class Alan(BaseModel):
    deger: Any | None = None
    ham_ifade: str | None = None
    kaynak: Kaynak | None = None
    guven: float = 0.0
    yontem: Yontem = "belirtilmemis"
    birim: Birim | None = None      # <- yeni
```

Gerekçe: `deger` sıralama, depolama ve metrik yollarında çıplak sayı olarak
kullanılıyor; boyutu değere gömmek o yolların hepsini kırardı. `Alan` ise
zaten **"değer + kanıt + güven + yöntem"** taşıyıcısıdır — birim aynı ailedendir,
bir KÖKEN bilgisidir.

### Sözleşme: `ALAN_BOYUTLARI`

Hangi alanın hangi boyutu kabul ettiği `src/schema.py`'de, kural motorundan ve
LLM katmanından **bağımsız** olarak durur. Gerekçe `deger_makul_mu`'nunkiyle
aynı: *denetim ALANIN özelliğidir, kuralın değil.*

Sözleşme iki sınıf üretir:

- **Tek birimli alanlar** (`kar_payi_orani` hep yüzde, `vade_ay_max` hep ay):
  birim **sözleşmeden çıkarılır**, metne bakılmaz. Her çıkarım yolunda ayrıca
  yazmak, bir yolda unutulmasını garanti ederdi.
- **Çok birimli alanlar** (`tahsis_ucreti`, `alisveris_puani`): birim ham
  ifadeden çözülür ve **zorunludur**. Bilgi tam burada kayboluyordu, denetim
  de tam burada olmalı.

`Kampanya._boyut_sozlesmesi` doğrulayıcısı bunu zorlar: birimsiz bir
`tahsis_ucreti` artık `Kampanya` nesnesi olarak **kurulamaz**. Bu,
`Alan._kanit_zinciri` ile aynı reflekstir.

> Şemanın ilkesi *«kanıtsız değer üretilemez»*di.
> Bu ADR onun bir seviye derinidir: **«birimsiz sayı taşınamaz.»**

### Tek çözümleyici

`normalizasyon.birim_belirle(ham_ifade, alan_adi)` tek uygulamadır ve **hem
çıkarım hem göç** onu çağırır. İki ayrı uygulama, göç edilmiş kayıtla yeni
çıkarılan kaydın sessizce ayrışması demekti.

### Karşılaştırma: ortak taban ya da sessizlik

```python
@dataclass(frozen=True)
class Senaryo:
    anapara: float
    vade_ay: int
```

`ortak_tabana_indir()` çok birimli alanları TL'ye indirger. Senaryo yoksa
yüzde değerler indirgenemez ve `None` döner — bu bir hata değil, bir
**beyandır**. Çağıran bunu eksik veri gibi işler, `karsilastirilabilirlik`
oranı düşer ve `uyarilar()` kullanıcıya *"bu kriter sıralamaya katılmadı"*
der. **Sessizce yanlış sıralamaktansa beyan edilmiş belirsizlik.**

### Gösterim

`chatbot._ALAN_ETIKETLERI` artık yalnız **etiket** tutar; biçim
`BIRIM_GOSTERIMLERI`'nden, yani birimden türer. Sabit şablonu silmek hatayı
düzeltmez — hatayı **mümkün olmaktan çıkarır**.

## Göç

`tools/birim_goc.py` (`make birim-goc`), mevcut 96 kaydı **yeniden LLM
çıkarımı olmadan** v1.2.0'a taşır: birim `ham_ifade`'den deterministik olarak
çözülür, kalan her değer birebir korunur.

```
Okunan kayıt: 96 · doğrulanan: 96 · çözülemeyen: 0
vade_ay_max 31 · finansman_tutari_max 11 · kar_payi_orani 11 · odul_miktari 8
taksit_sayisi 7 · tahsis_ucreti 6 · indirim_orani 6 · alisveris_puani 1
```

Göç, `tam_kayit` JSON yuvarlak yolunun **tip-sadık olmadığını** da ortaya
çıkardı: `Alan.deger` bilinçli olarak `Any` olduğu için pydantic tarihi
JSON'dan okurken çözmüyor ve `"2026-12-31"` string kalıyor. Göç bunu onarır
(`_tarih_tipini_onar`); yeni çıkarımda sorun yok, çünkü orada değer hiç
JSON'a uğramıyor.

## Sonuç

| Ölçüt | Önce | Sonra |
|---|---|---|
| Ekranda `%0,50` gösterimi | `0,50 TL` | **`%0,50`** |
| `%0,50` ile `500 TL` (100.000 TL senaryo) | biri "en ucuz", diğeri "en pahalı" | **eşit (500 TL)** |
| Birimsiz sayısal alan | 8 alan | **0** (şema reddediyor) |
| Test sayısı | 506 | **543** |
| Makro-F1 / sayısal doğruluk | 0,778 / 0,937 | **değişmedi** (göç değer oynatmaz) |

Sınıf kapandı mı? `odul_miktari`'na yüzde yazılamaz, `ALAN_BOYUTLARI`'na
eklenen üçüncü bir çok birimli alan depolama sütunu olmadan teste takılır
(`tests/test_boyut_sozlesmesi.py::TestSozlesmeButunlugu`). **Yeni sözcük
eklemeden yakalanıyor.**

## Kapsam dışı — bilerek

Vakıf Katılım'ın `%75`'i (*"%75 komisyon indirimi"*) hâlâ `tahsis_ucreti`
olarak duruyor; artık `yuzde` birimiyle ve senaryoda 75.000 TL'ye açılıp
sıralamanın **sonuna** düşüyor, yani zararsızlaştı. Ama semantik olarak
yanlış: bu bir ücret değil, komisyona uygulanan bir indirimdir.

Kökten çözümü **`Dayanak`** kavramıdır (yüzde neyin yüzdesi?) ve
`docs/DUZELTME_TASARIMI.md` § 1.1b'de tasarlandı. Bu ADR'nin kapsamına
alınmadı çünkü ayrı bir mekanizma (dayanak çözümleme) gerektiriyor ve
`ALAN_BOYUTLARI` sözleşmesi onu eklemeye hazır. Bilinen kusur olarak
`docs/HATA_ANALIZI.md`'ye yazılır — gizlenmez.
