# Düzeltme Tasarımı — Demo Hataları ve Ölçüm Metodolojisi

_Tasarım belgesi · 19 Ağustos 2026 · İnceleme raporu Bölüm 1 (🔴) ve Bölüm 2 (🟠)_

**Kapsam.** Bu belge iki blok bulguyu kapatır:

| Blok | Bulgular | Ne |
|---|---|---|
| **Bölüm 1** | 1.1 – 1.7 | Canlı demoda jürinin **ekranda göreceği** hatalar |
| **Bölüm 2** | 2.1 – 2.5 | Jürinin **ölçüm metodolojisine** yapacağı saldırı |

**Bu belgenin uyduğu kural.** Hiçbir çözüm ezber, sabit değer (hardcode) ya da
yama değildir. Her çözüm bir **sözleşme değişikliğidir**: bir bilgi bugün kod
içinde sessizce düşürülüyor; onu düşürmek yerine taşımaya başlıyoruz. Ölçütümüz
şudur — *"aynı hata sınıfının ikinci örneği kod değiştirmeden yakalanıyor mu?"*
Cevap hayırsa o çözüm bu belgeye girmedi.

---

## 0. Tek kök neden — bilgi düşürme

On iki bulgunun tamamı tek bir kalıptan doğuyor: **bir katman, bildiği bir
bilgiyi bir sonraki katmana aktarmadan atıyor.** Sonraki katman o bilgi olmadan
karar vermek zorunda kalınca hata üretiyor.

| Düşürülen bilgi | Nerede düşüyor | Doğurduğu bulgu |
|---|---|---|
| **Birim** (TL mi, % mi) | [normalizasyon.py:215](../src/preprocessing/normalizasyon.py#L215) `-> float` | 1.1 |
| **Köken** (yapısal / alıntı / hesap) | [chatbot.py](../src/rag/chatbot.py) `Cevap.metin` tek string | 1.2 |
| **Karşılaştırılabilirlik sınıfı** | [karsilastirma.py:51](../src/comparison/karsilastirma.py#L51) tek havuz | 1.3 |
| **Belge türü** (kampanya mı ücret tarifesi mi) | [toplayici.py](../src/collector/toplayici.py) yalnız uzunluk kapısı | 1.5 |
| **Alan üreticisi** (bu alanı kim doldurur) | [schema.py:287](../src/schema.py#L287) beyan yok | 1.4 |
| **Zaman** (kayıt hâlâ geçerli mi) | `kampanya_bitis` türetilmemiş | 1.6 |
| **Korpus seçim kuralı** | elle silme, kural yok | 1.7 |
| **Bölünme** (geliştirme / saklı) | bölünme kavramı yok | 2.1 |
| **Koşu kimliği** (ablasyon satırları) | üç ayrı elle koşu | 2.2 |
| **Metrik kapsamı** (payda) | makro-F1 çıplak yayınlanıyor | 2.3 |
| **Türetilmişlik** (doküman ↔ ölçüm) | elle kopyalama | 2.4, 2.5 |

Projenin donmuş ilkesi şudur:

> **"Kanıtsız değer üretilemez."** — `src/schema.py`

Bu belgenin ilkesi onun bir seviye derinidir:

> **"Bağlamsız değer taşınamaz."**
> Bir sayı; birimini, kökenini, sınıfını ve geçerlilik anını yanında
> taşımadan bir sonraki katmana geçemez.

Jüriye anlatılacak cümle budur. On iki ayrı düzeltme değil, **bir ilkenin
tutarlı uygulanması** sunuyoruz.

---

# BÖLÜM 1 — Demoda görünen hatalar

## 1.1 · Boyutlu nicelik: birim, değerin kendisi kadar veridir

> ✅ **1.1a UYGULANDI — 19 Ağustos 2026.** ADR 009 · şema **v1.2.0** ·
> `tests/test_boyut_sozlesmesi.py` (37 test) · `tools/birim_goc.py`
> (`make birim-goc`, 96 kayıt, 0 çözülemeyen).
> Ekranda **`0,50 TL` → `%0,50`**; senaryoda `%0,50` ile `500 TL` **eşit**.
> Birimsiz sayısal alan: 8 → **0** (şema reddediyor).
>
> ⬜ **1.1b `Dayanak` bekliyor (P2).** Vakıf'ın `%75`'i artık `yuzde` birimiyle
> duruyor ve senaryoda 75.000 TL'ye açılıp sıralamanın sonuna düşüyor — yani
> zararsız, ama semantik olarak hâlâ yanlış. Kökten çözümü aşağıdaki
> `Dayanak` tasarımıdır.
>
> **Uygulanan tasarım, aşağıdakinden bir noktada ayrıldı:** birim ayrı bir
> `Nicelik` değer nesnesine değil, **`Alan` üzerine** kondu. Gerekçe ölçüldü —
> ayrıştırıcıların 84 çağrı yeri var ve çoğu (`orkestrator` profil ayrıştırma,
> `altin_set` aracı, doctest'ler) çıplak `float` bekliyor, birimden fayda
> görmüyor. `Alan` zaten «değer + kanıt + güven + yöntem» taşıyıcısı; birim
> aynı ailedendir. Ayrıntı: ADR 009.

### Kök neden

Ayrıştırıcılar birimi **tespit ediyor, sonra atıyor**:

```python
# src/preprocessing/normalizasyon.py:215
def para_ayristir(parca: str, birim_zorunlu: bool = True) -> float | None:
    if birim_zorunlu and not _PARA_BIRIMI.search(parca):   # birimi GÖRDÜ
        return None
    ...
    return taban                                           # birimi ATTI
```

Sonuç, kural tanımında çıplak gözle görünüyor:

```python
# src/extraction/kural.py:338
ayristirici=lambda s: para_ayristir(s, birim_zorunlu=True) or oran_ayristir(s),
```

Bu satır *"önce TL dene, olmazsa yüzde dene"* diyor ve **hangisinin tuttuğunu
çağırana söylemiyor.** `500 TL` de `%0,50` de aynı sütuna `float` olarak
düşüyor. Şema bunu itiraf ediyor ama çözmüyor:

```python
# src/schema.py:274
tahsis_ucreti: Alan = Field(default_factory=Alan.yok)  # TL veya %, float
```

> **Yan bulgu.** `A or B` kalıbı `para_ayristir` `0.0` döndürdüğünde de
> `oran_ayristir`'a düşer — sıfır TL'lik bir ücret sessizce yüzde olarak
> yeniden yorumlanır. Aynı tasarım kokusunun ikinci belirtisi.

### Reddedilen yamalar

| Yama | Neden reddedildi |
|---|---|
| `tahsis_ucreti_tipi: str` alanı eklemek | Yalnız bir alanı kurtarır. `indirim_orani`, `alisveris_puani` (*"TL/puan"*), `odul_miktari` aynı hastalıkta. Onuncu alanda onuncu bayrak yazılır. |
| Ekranda `%` yazarken `< 100` ise yüzde varsaymak | Ezber. `%0,50` ile `0,50 TL` sayı olarak ayırt edilemez; 120 TL'lik gerçek bir ücret yüzde sanılır. |
| Vakıf'ın `%75`'i için `"komisyon indirimi"` vetosu | Tam olarak yasakladığımız şey: tek kaydın ezberi. Yarın *"aidat iadesi %60"* gelir, veto listesi büyür, sınıf kapanmaz. |

### Genel çözüm — `Nicelik` değer nesnesi

Sayı ile birimi **ayrılamaz** hale getiriyoruz. Birim artık yorum değil, veridir.

```python
# src/schema.py

class Birim(StrEnum):
    """Bir sayının ne olduğunu söyleyen boyut etiketi."""
    TL     = "tl"      # mutlak para tutarı
    YUZDE  = "yuzde"   # oransal — DAYANAĞI olmadan anlamsızdır
    AY     = "ay"
    ADET   = "adet"
    PUAN   = "puan"


class Dayanak(StrEnum):
    """Bir YÜZDE neyin yüzdesi? Yüzde ilişkiseldir; dayanaksız taşınamaz."""
    ANAPARA        = "anapara"          # finansman tutarı üzerinden
    HARCAMA        = "harcama"          # alışveriş tutarı üzerinden
    KOMISYON       = "komisyon"         # işlem komisyonu üzerinden
    LISTE_FIYATI   = "liste_fiyati"     # indirim tabanı
    BILINMIYOR     = "bilinmiyor"


class Nicelik(BaseModel):
    """Boyutlu sayı. `Alan.deger` içinde çıplak float'ın yerini alır."""
    model_config = ConfigDict(frozen=True)

    deger: float
    birim: Birim
    dayanak: Dayanak | None = None      # yalnız YUZDE için anlamlı
    yon: Literal["maliyet", "fayda"] | None = None   # indirim mi ücret mi

    @model_validator(mode="after")
    def _yuzde_dayanaksiz_olamaz(self) -> Nicelik:
        if self.birim is Birim.YUZDE and self.dayanak is None:
            raise ValueError(
                "Yüzde dayanaksız üretilemez: '%75' tek başına bir değer değil, "
                "bir ilişkidir. Neyin yüzdesi olduğu beyan edilmelidir."
            )
        return self
```

Bu `model_validator`, `Alan._kanit_zinciri`'nin kardeşidir: **kanıtsız değer
üretilemediği gibi, dayanaksız yüzde de üretilemez.** Aynı savunma refleksi.

### Ayrıştırıcılar birimi döndürür

```python
def para_ayristir(parca: str, birim_zorunlu: bool = True) -> Nicelik | None:
    ...
    return Nicelik(deger=taban, birim=Birim.TL)

def oran_ayristir(parca: str, dayanak: Dayanak) -> Nicelik | None:
    ...
    return Nicelik(deger=deger, birim=Birim.YUZDE, dayanak=dayanak)
```

`oran_ayristir` artık **dayanak istemeden çağrılamaz.** Bu, çağıranı
"bu yüzde neyin yüzdesi?" sorusunu cevaplamaya *tip sistemi düzeyinde* zorlar —
unutulabilir bir disiplin değil, derlenmeyen bir çağrı.

### Alan sözleşmesi: hangi alan hangi boyutu kabul eder

```python
# src/schema.py — tek doğruluk kaynağı, kural motorundan bağımsız

ALAN_BOYUTLARI: dict[str, frozenset[Birim]] = {
    "kar_payi_orani":       frozenset({Birim.YUZDE}),
    "finansman_tutari_max": frozenset({Birim.TL}),
    "vade_ay_max":          frozenset({Birim.AY}),
    "taksit_sayisi":        frozenset({Birim.ADET}),
    "tahsis_ucreti":        frozenset({Birim.TL, Birim.YUZDE}),   # ikisi de meşru
    "odul_miktari":         frozenset({Birim.TL}),
    "indirim_orani":        frozenset({Birim.YUZDE}),
    "alisveris_puani":      frozenset({Birim.TL, Birim.PUAN}),
}

ALAN_DAYANAKLARI: dict[str, frozenset[Dayanak]] = {
    "kar_payi_orani": frozenset({Dayanak.ANAPARA}),
    "tahsis_ucreti":  frozenset({Dayanak.ANAPARA}),
    "indirim_orani":  frozenset({Dayanak.HARCAMA, Dayanak.LISTE_FIYATI}),
}
```

### Kapı: mevcut `deger_makul_mu` boyut denetimi kazanır

Yeni kapı yazmıyoruz. [kural.py:888](../src/extraction/kural.py#L888)'deki
`deger_makul_mu`, projenin kendi ifadesiyle *"denetim ALANIN özelliğidir,
kuralın değil"* ilkesiyle zaten alan düzeyinde ve **her iki katmanı birden**
kapsıyor. Oraya iki satır ekleniyor:

```python
def deger_makul_mu(alan_adi, deger, metin, baslangic, bitis) -> bool:
    if isinstance(deger, Nicelik):
        if deger.birim not in ALAN_BOYUTLARI.get(alan_adi, frozenset()):
            return False                      # boyut uyuşmazlığı
        if deger.birim is Birim.YUZDE:
            izinli = ALAN_DAYANAKLARI.get(alan_adi, frozenset())
            if deger.dayanak not in izinli:
                return False                  # yanlış dayanak
    ...  # mevcut aralık / aralık-ucu / veto denetimleri aynen kalır
```

**Vakıf'ın `%75`'i burada, ezber olmadan düşer.** Metin şöyle:

```
… standart komisyon oranı yerine, on binde 5 komisyon oranı uygulanır.
Bu oran, %75 komisyon indirimi anlamına gelir.
```

Dayanak çözümlemesi (aşağıda) `Dayanak.KOMISYON` üretir.
`ALAN_DAYANAKLARI["tahsis_ucreti"] = {ANAPARA}` olduğu için değer reddedilir.
Yarın *"aidat iadesi %60"* gelirse dayanak yine `ANAPARA` olmayacak ve
**kod değiştirmeden** düşecek. Sınıf kapandı.

### Dayanak nasıl çözümlenir — mevcut mekanizma, yeni kullanım

Yeni bir çıkarıcı yazmıyoruz. Kural katmanının **zaten sahip olduğu** pencere
+ mesafe mekanizması (`baglam_sozcukleri`, `_ALAN_KURALI`) kullanılır: yüzdenin
penceresinde hangi dayanak kavramı sayıya en yakınsa o seçilir; hiçbiri
eşiği geçmezse `Dayanak.BILINMIYOR` döner ve `Nicelik` doğrulayıcısı değeri
reddeder.

Dayanak kavramlarının sözcük karşılıkları **`data/dayanaklar.yaml`** içinde,
Python'da değil, veri olarak durur:

```yaml
# data/dayanaklar.yaml — sürümlenmiş alan sözlüğü, ezber değil
anapara:
  - finansman tutarı
  - anapara
  - kullandırılan tutar
komisyon:
  - komisyon
  - işlem ücreti
harcama:
  - harcama tutarı
  - alışveriş tutarı
```

> **Ezber ile sözlük arasındaki fark ve onu koruyan test.** Kural katmanının
> `VERGI_VE_MEVZUAT` yorumundaki disiplini aynen devralıyoruz:
> *"Buradaki her ifade derlemde EN AZ İKİ kayıtta geçmelidir. Tek kayıtta
> geçen bir veto, örüntü değil o kaydın ezberidir."*
> `tests/test_sozluk_disiplini.py` bu kuralı `data/dayanaklar.yaml` ve
> taksonomi dosyaları için otomatik denetler. **Ezberi kod incelemesi değil,
> test engeller.**

### Gösterim ve karşılaştırma birimi okur

Sabit `"{} TL"` şablonu ([chatbot.py:276](../src/rag/chatbot.py#L276)) kalkar:

```python
def nicelik_goster(n: Nicelik) -> str:
    """Gösterim biçimi BİRİMDEN türer, alan adından değil."""
    match n.birim:
        case Birim.TL:    return f"{sayi_goster(n.deger)} TL"
        case Birim.YUZDE: return f"%{sayi_goster(n.deger)}"
        case Birim.AY:    return f"{sayi_goster(n.deger)} ay"
        ...
```

**"0,50 TL" ekranda bir daha oluşamaz** — çünkü onu üreten şablon artık yok.

Karşılaştırma tarafı ise ortak tabana indirilir. Bunun için yeni matematik
gerekmiyor; [karsilastirma.py](../src/comparison/karsilastirma.py) içindeki
`toplam_maliyet()` annüite hesabı zaten senaryo tabanlı çalışıyor:

```python
@dataclass(frozen=True)
class Senaryo:
    """Karşılaştırmanın ortak tabanı. Arayüzde ağırlık kaydırıcılarının yanında."""
    anapara: float
    vade_ay: int

def ortak_tabana_indir(n: Nicelik, senaryo: Senaryo | None) -> float | None:
    """Boyutlu niceliği TL'ye indirger. İndirgenemiyorsa None — uydurmaz."""
    if n.birim is Birim.TL:
        return n.deger
    if n.birim is Birim.YUZDE and n.dayanak is Dayanak.ANAPARA and senaryo:
        return senaryo.anapara * n.deger / 100.0
    return None
```

Senaryo verilmemişse `None` döner; `avantaj_skorla` bu değeri **zaten var olan**
`NOTR_SKOR` + `karsilastirilabilirlik` mekanizmasıyla işler ve kullanıcıya
*"masraf kriteri ortak tabana indirilemedi"* uyarısı `uyarilar()` üzerinden
gösterilir. Yani sessiz yanlış sıralama yerine **beyan edilmiş belirsizlik**.

### Şema sürümü ve göç

Bu bir **kırıcı** değişikliktir. `CLAUDE.md`'nin donmuş şema protokolü uygulanır:

1. `docs/kararlar/009-boyutlu-nicelik.md` (ADR) yazılır
2. `SEMA_SURUMU = "2.0.0"`
3. Takıma duyurulur

**Dokunulacak yerler — eksiksiz liste:**

| Dosya | Değişiklik |
|---|---|
| `src/schema.py` | `Birim`, `Dayanak`, `Nicelik`, `ALAN_BOYUTLARI`, `ALAN_DAYANAKLARI` |
| `src/preprocessing/normalizasyon.py` | 4 ayrıştırıcı `Nicelik` döndürür |
| `src/extraction/kural.py` | `deger_makul_mu` boyut kapısı · dayanak çözümleyici |
| `src/extraction/llm.py` | `_AYRISTIRICILAR` imzaları |
| `src/extraction/uzlastirici.py` | `_degerler_uyusuyor_mu` **birim eşitliği de arar** |
| `src/depolama.py` | sayısal sütunlar `+ *_birim` (sıralanabilirlik korunur) |
| `src/comparison/karsilastirma.py` | `Senaryo`, `ortak_tabana_indir` |
| `src/rag/chatbot.py` | `nicelik_goster`, kalkan izin listesi |
| `eval/calistir.py` | `_degerler_esit` birim duyarlı |
| `tools/altin_set.py` | CSV'ye `tahsis_ucreti_birim` sütunu |

**Altın set yeniden etiketlenmez.** Mevcut 60 etiketin yalnız `tahsis_ucreti`
sütunu birim kazanır ve bu **veriden türetilebilir**: etiketçinin baktığı
`data/gold/metinler/*.txt` içinde ilgili ifade `%` içeriyorsa `YUZDE`, `TL`
içeriyorsa `TL`. Göç betiği `tools/altin_set.py birim-goc` olarak yazılır,
sonucu insan onaylar. **Yeniden etiketleme maliyeti sıfır.**

### Testler

```
tests/test_nicelik.py
  · dayanaksız YUZDE üretilemez (ValueError)
  · para_ayristir → Birim.TL, oran_ayristir → Birim.YUZDE
  · 0,0 TL yüzdeye düşmez  (bugünkü `or` hatasının regresyon testi)

tests/test_boyut_kapisi.py
  · tahsis_ucreti YUZDE+KOMISYON reddedilir      ← Vakıf %75
  · tahsis_ucreti YUZDE+ANAPARA kabul edilir     ← Türkiye Finans %0,50
  · odul_miktari YUZDE reddedilir                ← sınıf genellemesi
  · uydurulmuş yeni bir alan/birim çifti reddedilir

tests/test_karsilastirma_taban.py
  · senaryosuz TL+YUZDE karışımı sıralanmaz, uyarı üretir
  · senaryoyla %0,50 × 100.000 TL = 500 TL ile eşitlenir
```

Son test kritik: **bugünkü hatanın tam tersini kanıtlıyor** — `%0,50` ile
`500 TL` doğru tabanda *eşit* çıkıyor, bugünse biri "en ucuz" diğeri "en pahalı".

### Jüri savunması

> *"Tahsis ücreti bazı bankalarda TL, bazılarında yüzdedir. Bu bizim
> problemimiz değil, alanın gerçeğidir. Biz bunu tek sütuna sıkıştırıp
> sessizce karşılaştırmıyoruz: her sayı birimini taşır, yüzdeler dayanağını
> taşır, karşılaştırma ancak beyan edilmiş bir senaryoda ortak tabana
> indirilerek yapılır. İndirilemiyorsa sıralama yapmıyor, 'karşılaştırılamaz'
> diyoruz. `%0,50` ile `500 TL`, 100.000 TL'lik senaryoda sistemimizde
> **eşittir** — nitekim gerçekte de eşittir."*

---

## 1.2 · Köken tipli doğrulama kalkanı

> ✅ **UYGULANDI — 19 Ağustos 2026.** ADR 010 · `src/rag/chatbot.py` ·
> `tests/test_kalkan_kokenli.py` (47 test) · `eval/kalkan.py` ·
> `eval/sorular.yaml` (42 soru).
> **Yanlış blok oranı %14,3 → %0** (35 meşru soru), denetimsiz parça %0.
> Ölçüm `docs/SONUCLAR.md` § «Sayısal doğrulama kalkanı»nda, her `make eval`
> koşusunda yeniden üretiliyor.

### Kök neden

Kalkan **tüm cevap metnini** yalnız **yapısal kayda** karşı denetliyor. Oysa bir
cevap üç ayrı köken sınıfından sayı taşır ve üçünün doğrulama ölçütü farklıdır:

| Köken | Örnek | Doğru ölçüt | Bugün ne oluyor |
|---|---|---|---|
| **Yapısal** | *"Azami vade: 60 ay"* | Yapısal alanda birebir | ✅ doğru |
| **Alıntı** | ham metinden alınan paragraf | **Kaynak metinde** birebir | ❌ **yanlış yere bakıyor → bloke** |
| **Sistem** | *"skor 0,625; ağırlık %40"* | **Yeniden hesapla** | ❌ **hiç bakılmıyor → kör nokta** |

Ölçülen sonuç — sabit soru kümesinde (`eval/sorular.yaml`) **35 meşru
sorunun 5'i engellendi, %14,3**:

```
"Hayat Finans başvuru nasıl yapılır?"        → ['17']    (17 iş günü)
"Başvuru için hangi belgeler gerekli?"       → ['6698']  (KVKK kanun numarası)
"Kampanya kapsamı nedir?"                    → ['60']
"Yeni müşteriler için hangi kampanyalar var?"→ ['95']
"Dünya Katılım kart kampanyası kapsamı?"     → ['0,1']
```

`6698` vakası tek başına yeterince açıklayıcı: sistem, bankanın sayfasındaki
**KVKK kanun numarasını** «doğrulanamayan sayı» sayıp cevabı engelliyordu.

Reddedilen sayılar **bankanın kendi metninden birebir alıntı**. Üstelik
`niyet_belirle` eşleşmeyen her soruyu varsayılan olarak bu yola gönderiyor.

Ve kör nokta, mevcut kaçış kapısının kendisi:

```python
# src/rag/chatbot.py — karşılaştırma cevabı
dogrulanacak_metin=veri_bolumu,   # "genel değerlendirme" bölümü HİÇ denetlenmiyor
```

`dogrulanacak_metin` ikili bir muafiyettir: bir metin ya tümüyle denetlenir ya
hiç denetlenmez. Skorun ve ağırlıkların olduğu bölüme **istediğimiz sayıyı
yazabiliriz, kalkan görmez.**

### Reddedilen yamalar

| Yama | Neden reddedildi |
|---|---|
| Kalkanın izin listesine `ham_metin`'in tüm sayılarını eklemek | Kalkanı kökten gevşetir: artık *"sayfada geçen herhangi bir sayı"* meşru olur. `CLAUDE.md`: *"Kalkanı zayıflatma."* |
| `_kosul_cevabi`'na `dogrulanacak_metin=""` vermek | Koşul yolunu tümüyle denetimsiz bırakır. Kör noktayı çoğaltır. |
| Alıntıları tırnak içine alıp regex ile atlamak | Biçime bağlı ezber; tırnak biçimi değişince sessizce çöker. |

### Genel çözüm — cevap, parçalardan oluşur ve her parça kökenini taşır

```python
class Koken(StrEnum):
    YAPISAL = "yapisal"   # yapısal alandan geldi
    ALINTI  = "alinti"    # kaynak metinden birebir alındı
    SISTEM  = "sistem"    # bizim hesabımız (skor, ağırlık)
    DUZ     = "duz"       # sayı içermeyen bağlaç metni

@dataclass(frozen=True)
class CevapParcasi:
    metin: str
    koken: Koken
    kayit_id: str | None = None    # ALINTI için zorunlu: hangi kaydın metni
    hesap: dict[str, float] | None = None   # SISTEM için: yeniden üretilecek girdiler

@dataclass
class Cevap:
    parcalar: list[CevapParcasi]
    ...
```

Kalkan artık parça başına, **kökene göre** doğrular:

```python
def kalkandan_gecir(cevap: Cevap, kayitlar) -> tuple[bool, list[str]]:
    reddedilen = []
    for parca in cevap.parcalar:
        match parca.koken:
            case Koken.YAPISAL:
                # bugünkü davranış, aynen korunur
                reddedilen += _yapisal_disi_sayilar(parca.metin, kayitlar)
            case Koken.ALINTI:
                # alıntı, KAYNAK METNİN birebir alt dizesi olmak zorunda
                kaynak = _kaydin_ham_metni(parca.kayit_id, kayitlar)
                if parca.metin.strip() not in kaynak:
                    reddedilen.append(f"alıntı kaynakta yok: {parca.metin[:40]!r}")
            case Koken.SISTEM:
                # sayılar İDDİA değil, HESAP — yeniden üretilebilmeli
                reddedilen += _yeniden_hesapla_ve_karsilastir(parca)
            case Koken.DUZ:
                pass
    return (not reddedilen), reddedilen
```

### Bu kalkanı gevşetmiyor — sertleştiriyor

| | Bugün | Sonra |
|---|---|---|
| Yapısal iddia | birebir denetleniyor | **aynı** |
| Alıntı | yanlış kaynağa karşı denetleniyor → yanlış blok | **doğru kaynağa karşı**; üstelik alt-dize şartı, bugün hiç olmayan **alıntı bütünlüğü** garantisi getiriyor |
| Sistem açıklaması | **hiç denetlenmiyor** | **yeniden hesaplanarak** denetleniyor |

Yani düzeltme, yanlış pozitifi kaldırırken **gerçek bir açığı da kapatıyor.**
Jüriye söylenecek cümle: *"Kalkanı gevşetmedik; ona eksik olan köken bilgisini
verdik."* — bu, `CLAUDE.md`'deki *"çözüm kalkanı gevşetmek değil, denetlenecek
metni doğru seçmektir"* talimatının tam karşılığıdır.

### Testler

```
tests/test_kalkan_kokenli.py
  · ALINTI parçasındaki kaynak sayısı BLOKLANMAZ   ← 2 yanlış blokun regresyonu
  · kaynakta olmayan bir alıntı BLOKLANIR          ← yeni garanti
  · SISTEM parçasına elle yanlış skor yazılırsa BLOKLANIR  ← kapatılan kör nokta
  · YAPISAL parçada uydurma oran BLOKLANIR         ← eski davranış korundu

tests/test_kalkan_kapsama.py
  · her CevapParcasi'nın kökeni atanmış olmalı (DUZ dahil) — kökensiz parça yasak
```

Son test, gelecekteki bir kaçağı yapısal olarak imkânsız kılar: yeni bir cevap
üreticisi köken atamayı unutursa **test kırmızı olur.**

### Ölçülebilir kabul ölçütü

`eval/` altına `kalkan_yanlis_blok_orani` metriği eklenir: sabit bir soru
kümesi (`eval/sorular.yaml`, en az 40 soru) koşulur; insan tarafından meşru
işaretlenmiş cevapların bloklanma oranı raporlanır.

**Hedef: %0. Taban ölçüm: %14,3 (5/35). Ulaşılan: %0 (0/35).** Sayı
`docs/SONUCLAR.md`'ye girdi — "düzelttik" iddiası artık ölçülü.

Ayrıca `denetimsiz_parca_orani` yayınlanır: miras `metin=` sözleşmesinden
gelen ve kalkanın atladığı parçaların oranı. Muafiyet yok olmadı, **görünür
ve sayılabilir** hâle geldi; hedef sıfır, chatbot üreticilerinde bugün sıfır.

---

## 1.3 + 1.5 · Karşılaştırılabilirlik sınıfı ve belge türü

_İki bulgu tek kök nedeni paylaşıyor, bu yüzden tek başlıkta çözülüyor._

### Kök neden

**(a) Belge düzeyinde:** Toplayıcının tek içerik kapısı `EN_AZ_GOVDE_UZUNLUGU
= 200`. Korpusa ne girdiği ölçüldüğünde:

```
kampanya_turu = "diger"          : 46/96  (%48)
hiç sayısal alanı olmayan kayıt  : 51/96  (%53)
```

Çünkü korpusta **kampanya olmayan sayfalar** var: ücret tarifesi, günlük hesap,
kurumsal tanıtım. Kanıtı, hatalı değerlerin kaynağı:

- `kar_payi_orani = 1.0` ← `/urun-ve-hizmet-ucretleri` (ücret tarifesi)
- `kar_payi_orani = 11.0` ← `/gunluk-hesap.aspx`, mevduat kademe tablosundan:
  `5.000.001 - 10.000.000 TL | %11,00 | %39,00 | …`

Bunlar çıkarım hatası değil, **kapsam hatası**: kampanya olmayan bir belgeden
kampanya alanı çıkarılıyor.

**(b) Sıralama düzeyinde:** `sirala()` tüm kayıtları tek havuza koyuyor. Sonuç:

```
Soru:  "En düşük kâr payı oranını hangi banka veriyor?"
Cevap: "… Albaraka Türk daha avantajlıdır, çünkü oran %0'dir."
```

`%0` değeri **doğru** (`sifir_gecerli=True` bilinçli ve haklı bir karar). Yanlış
olan, bir **kart kampanyasının** promosyonel `%0`'ı ile **konut finansmanı**
oranının aynı sıralamada yarışması. `uyarilar()` bunu fark edip uyarıyor ama
**yine de sıralıyor** — uyarmak, yanlış sıralamayı doğru yapmaz.

### Reddedilen yamalar

| Yama | Neden reddedildi |
|---|---|
| `kampanya_turu` sözlüğüne anahtar sözcük eklemek | Korpusa özgü ezber; `%48 diger` oranını kovalayarak düşürmek ölçüme uydurmaktır. |
| Sıfır oranları sıralamadan çıkarmak | Veriyi bozar. `%0` gerçek ve altın sette 3 kez etiketli. |
| URL'de `kampanya` geçmeyeni atmak | Kırılgan; `/bireysel/konut-finansmani` gerçek bir kampanya sayfası. |

### Genel çözüm — iki katmanlı sınıflandırma

#### Katman A: Belge türü (alan çıkarımından ÖNCE)

```python
class BelgeTuru(StrEnum):
    KAMPANYA      = "kampanya"        # süreli, koşullu teklif
    URUN          = "urun"            # sürekli ürün sayfası
    UCRET_TARIFESI = "ucret_tarifesi" # fiyat listesi
    MEVDUAT       = "mevduat"         # katılma hesabı / getiri tablosu
    KURUMSAL      = "kurumsal"        # yatırımcı ilişkileri, hakkımızda
    BELIRSIZ      = "belirsiz"
```

`HamKayit` bu alanı kazanır. **Kayıt silinmez** — veri seti eksiksiz kalır,
ama kampanya alanları yalnız `KAMPANYA` ve `URUN` belgelerinden çıkarılır.
Diğerleri korpusta durur ve metriklerin **paydasından** düşer.

Bu, `kural.py`'deki `MEVDUAT_URUNU` vetosunun doğru katmana taşınmış hâlidir:
bugün her sayısal alan için ayrı ayrı pencere içinde aranan bir şey, artık
**bir kez, belge düzeyinde** kararlaştırılıyor. Aynı iş, doğru yerde, bir kez.

#### Katman B: Karşılaştırma sınıfı

```python
@dataclass(frozen=True)
class KarsilastirmaSinifi:
    """İki kayıt ancak aynı sınıftaysa sıralanabilir."""
    urun_ailesi: str    # "konut" | "tasit" | "ihtiyac" | "kart" | "yatirim"
    olcut_birimi: Birim # 1.1'den: aynı boyut, yoksa ortak taban zorunlu

def sirala(kayitlar, kriter, *, sinif: KarsilastirmaSinifi | None = None):
    """Sınıf verilmezse kayıtlar sınıflara AYRILIR ve her sınıf kendi
    içinde sıralanır. Sınıflar arası tek liste ÜRETİLMEZ."""
```

Böylece *"en düşük kâr payı"* sorusunun cevabı şu hâle gelir:

```
Konut finansmanı  → Türkiye Finans, aylık %2,95
İhtiyaç finansmanı → Türkiye Finans, aylık %0,99
Kart              → Albaraka, %0 (vade farksız kampanya)

⚠️ Farklı ürün aileleri tek listede sıralanmaz; her aile kendi içinde
   karşılaştırılır.
```

Bu cevap hem **doğru** hem de bir bankacıya *daha faydalı*. Ve `%0` artık bir
arıza gibi değil, ait olduğu yerde görünüyor.

#### Taksonomi veri olarak durur

`data/taksonomi.yaml` — şartname 5.4 tablosundan türetilmiş, sürümlenmiş:

```yaml
konut_finansmani:
  urun_ailesi: konut
  tanimlayici_kavramlar: ["konut finansmanı", "ev finansmanı", "mortgage"]
  url_ipuclari: ["/konut", "/mortgage"]
```

Ve **ezber koruması** yine test ile: `tests/test_sozluk_disiplini.py`, her
tanımlayıcı kavramın derlemde en az iki kayıtta geçmesini şart koşar. Bir
kayıt için yazılmış kavram teste takılır.

### Testler

```
tests/test_belge_turu.py
  · /urun-ve-hizmet-ucretleri → UCRET_TARIFESI, kampanya alanı çıkarılmaz
  · /gunluk-hesap             → MEVDUAT   ← %11,00 hatasının regresyonu
  · kampanya sayfası          → KAMPANYA
  · sınıflandırılamayan belge alan üretmez (sessiz düşürme değil, beyan)

tests/test_karsilastirma_sinifi.py
  · kart %0 ile konut %2,95 AYNI listede sıralanmaz
  · her sınıf kendi içinde doğru sıralanır
  · sınıf başına en az 2 kayıt yoksa "karşılaştırılamaz" beyanı üretilir
```

### Yan kazanç

`%48 diger` oranı, sözcük ezberiyle değil **paydayı düzelterek** düşer:
kampanya olmayan belgeler kampanya metriğine girmediği için `diger` oranı
gerçek kampanya korpusunu yansıtır. Bu, jüriye **daha dürüst** bir sayıdır:
*"%48'i sınıflandıramadık"* yerine *"korpusun %X'i kampanya belgesi değildi;
kampanya belgelerinin %Y'sini sınıflandırdık"*.

---

## 1.4 · Alan üretici sözleşmesi ve `uygunluk` çıkarımı

### Kök neden

`Kampanya.uygunluk` şemada tanımlı ([schema.py:287](../src/schema.py#L287))
ama **hiçbir çıkarım katmanı onu yazmıyor.** Gerçek veriyle ölçüm:

```
96 kaydın 96'sında uygunluk = None
```

`MuhakemeAjani` — kendi belgesinde *"Ürünün asıl farkı burada"* diye tanıtılan
kısıt çözücü — bu yüzden hiçbir şey elemiyor. Gerçek profille koşuldu
(maaş müşterisi · 800.000 TL · 120 ay):

```
sonuç: 96 · uygun: 96 · "veri eksik" işaretli: 96 · maliyet hesaplanabilen: 10
```

Ajan doğru davranıyor (`kosul is None → kısıt yok = herkese açık`) ve dürüstçe
`veri_eksik` işaretliyor. **Hata ajanda değil, sözleşmede**: şema bir alan
tanımlıyor, hiçbir üretici o alanı doldurmayı taahhüt etmiyor ve **bu boşluk
hiçbir yerde alarm üretmiyor.**

İkinci kusur: `MusteriProfili`'nde **ürün türü alanı yok**. Yani senaryonun
kendisi ifade edilemiyor — *"konut finansmanı istiyorum"* denemiyor. Bu yüzden
sıralamanın tepesine Türkiye Finans'ın **hızlı finansman** sayfasındaki `%0,99`
oranı çıkıyor ve 800.000 TL / 10 yıllık **konut** talebine uygulanıp
1.370.669 TL hesaplanıyor. Bankacı jüri bunu ilk bakışta yakalar.

### Reddedilen yamalar

| Yama | Neden reddedildi |
|---|---|
| `uygunluk`'u şemadan silmek | Şartname 5.3 *"hedef kitle bilgileri (yeni/mevcut/maaş/segment)"* diyor. Alan gerekli; eksik olan üretici. |
| Müşteri Profili sayfasını demodan çıkarmak | En özgün özelliği saklamak. Sorun kapatılmaz, gizlenir. |
| `uygunluk`'u regex ile doldurmak | Kısıt cümleleri serbest metin; kural katmanının işi değil. |

### Genel çözüm A — üretici sözleşmesi (asıl düzeltme)

Sorun `uygunluk` değil, **beyansızlık**. Şema, her alanın kim tarafından
üretildiğini beyan eder ve bir test bu beyanı denetler:

```python
# src/schema.py
class Uretici(StrEnum):
    KURAL     = "kural"
    LLM       = "llm"
    TURETILMIS = "turetilmis"   # başka alanlardan hesaplanır
    DIS       = "dis"            # toplayıcıdan gelir (banka_adi, url)

ALAN_URETICILERI: dict[str, frozenset[Uretici]] = {
    "kar_payi_orani": frozenset({Uretici.KURAL, Uretici.LLM}),
    "uygunluk":       frozenset({Uretici.LLM}),
    "gecerlilik":     frozenset({Uretici.TURETILMIS}),
    ...
}
```

```
tests/test_uretici_kapsamasi.py
  · Kampanya'nın HER alanı ALAN_URETICILERI'nde beyan edilmiş olmalı
  · Beyan edilen her üretici, tohum korpusta o alanı EN AZ BİR KEZ üretmeli
```

İkinci iddia kritik: **beyan edilip üretilmeyen alan testi kırar.** `uygunluk`
bugün bu testi kırardı — ve altı gün önce kırmış olurdu. Bu, bulgunun tekrarını
sınıf düzeyinde imkânsız kılar; onuncu alan sessizce boş kalamaz.

### Genel çözüm B — `uygunluk` çıkarımı, mevcut mekanizmayla

Yeni altyapı yazılmıyor. LLM katmanının **zaten sahip olduğu** iki mekanizma
kullanılıyor:

1. **Şema kısıtlı üretim** — `ollama_json_semasi()` çıktısı `uygunluk` alt
   nesnesini kapsayacak şekilde genişletilir. Model şemanın dışına çıkamaz.
2. **Eleştirmen ajanı** — her kısıt, onu ifade eden cümleyi `alinti` olarak
   taşımak zorundadır. Kanıtsız kısıt reddedilir.

```python
class UygunlukKosullari(BaseModel):
    musteri_tipi: list[HedefKitle] = []
    segment_detayi: list[str] = []
    asgari_tutar: Nicelik | None = None     # 1.1'den: boyutlu
    azami_tutar: Nicelik | None = None
    zorunlu_urunler: list[str] = []
    alinti: str                              # ZORUNLU — kanıt zinciri
```

`alinti`'nin zorunlu olması, `Alan._kanit_zinciri` ile aynı savunmadır: kanıtsız
kısıt üretilemez. `masrafsiz_mi` için yazılan `_masraf_kaniti()` deseni birebir
tekrarlanır — yeni desen icat edilmiyor.

### Genel çözüm C — senaryo ifade edilebilir olmalı

```python
@dataclass(frozen=True)
class MusteriProfili:
    musteri_tipi: HedefKitle
    urun_ailesi: str          # ← YENİ: "konut" | "tasit" | "ihtiyac" | …
    tutar: Nicelik
    vade_ay: int
    ...
```

`MuhakemeAjani`, 1.3'teki `KarsilastirmaSinifi` kapısını kullanır: profilin
ürün ailesiyle uyuşmayan kayıt **maliyet hesabına hiç girmez**. Böylece
"ihtiyaç finansmanı oranıyla konut hesabı" yapısal olarak imkânsız hâle gelir —
kontrol değil, **tip uyuşmazlığı**.

### Testler

```
tests/test_uretici_kapsamasi.py   (yukarıda)
tests/test_uygunluk_cikarimi.py
  · kısıt cümlesi olan metinden UygunlukKosullari üretilir, alıntı taşır
  · kısıt cümlesi olmayan metinden kısıt UYDURULMAZ (None döner)
  · alıntısı ham metinde bulunmayan kısıt REDDEDİLİR
tests/test_muhakeme_urun_ailesi.py
  · konut profili, ihtiyaç finansmanı oranıyla maliyet HESAPLAMAZ  ← 1.370.669 regresyonu
  · uygun olmayan kayıt SEBEBİYLE döner (mevcut tasarım kararı korunur)
```

### Jüri savunması

> *"Şemamızda tanımlı her alanın beyan edilmiş bir üreticisi var ve bir test
> bunu denetliyor. Bir alan tanımlanıp doldurulmadan kalırsa `make test`
> kırmızı olur. Bu, 'unutulmuş alan' hatasını tek tek değil, sınıf olarak
> kapatır."*

---

## 1.6 · Zamansal geçerlilik birinci sınıf özelliktir

### Kök neden

Ölçüm (19 Ağustos itibarıyla):

```
bitiş tarihi olan kayıt : 23
süresi geçmiş           :  5   (biri 2021-03-01)
```

`kampanya_bitis` saklanıyor ama **hiçbir okuma yolu onu dikkate almıyor.**
Dashboard, karşılaştırma, chatbot ve API süresi dolmuş kampanyayı geçerliymiş
gibi sunuyor. 27 Ağustos'ta bu sayı en az 6 olur.

### Reddedilen yamalar

| Yama | Neden reddedildi |
|---|---|
| Arayüzde `if bitis < today: continue` | Dört okuma yoluna (UI, API, chatbot, karşılaştırma) dört kez yazılır; biri unutulur. |
| Süresi geçenleri veritabanından silmek | İzlenebilirlik kaybı. Ölçüm tekrar üretilemez hâle gelir. |
| `date.today()` doğrudan çağırmak | Test edilemez ve **belirlenimsiz**: `make eval` çıktısı koştuğu güne göre değişir — S-20'de kazanılan determinizm bozulur. |

### Genel çözüm — türetilmiş `gecerlilik` + tek filtre sözleşmesi

```python
class Gecerlilik(StrEnum):
    GECERLI    = "gecerli"
    SURESI_DOLDU = "suresi_doldu"
    BELIRSIZ   = "belirsiz"     # bitiş tarihi çıkarılamamış

class Kampanya(BaseModel):
    def gecerlilik(self, an: date) -> Gecerlilik:
        """Değerlendirme ANI DIŞARIDAN verilir — `date.today()` çağrılmaz.

        Gerekçe S-20 ile aynı: `make eval` iki kez koşulduğunda aynı sayıyı
        vermelidir. Sistem saatine bağlı bir metrik yeniden üretilemez.
        """
        if self.kampanya_bitis.deger is None:
            return Gecerlilik.BELIRSIZ
        return (Gecerlilik.GECERLI if self.kampanya_bitis.deger >= an
                else Gecerlilik.SURESI_DOLDU)
```

Ve **tek** filtre sözleşmesi — dört okuma yolunun tamamı bunu çağırır:

```python
# src/depolama.py
def kampanyalari_getir(*, an: date, gecerlilik: set[Gecerlilik] | None = None, ...):
    """`an` ZORUNLU parametre. Değerlendirme anı beyan edilmeden okuma yapılamaz."""
```

`an`'ın zorunlu olması anahtar: bir çağıran zamanı düşünmeyi *unutamaz*, çünkü
çağrı derlenmez. Bu, dört yere dört kontrol yazmanın tersidir — **kontrolü
tek yere koyup atlanmasını imkânsız kılmak.**

Arayüzde varsayılan `{GECERLI, BELIRSIZ}`, ama süresi dolanlar rozetle
gösterilebilir (`⏳ süresi doldu`) — veri gizlenmez, **etiketlenir**.

### Testler

```
tests/test_gecerlilik.py
  · bitiş < an  → SURESI_DOLDU · bitiş >= an → GECERLI · None → BELIRSIZ
  · kampanyalari_getir `an` olmadan çağrılamaz (TypeError)
  · varsayılan filtre süresi dolmuşu listelemez
  · aynı `an` ile iki koşu AYNI sonucu verir (determinizm)

tests/test_okuma_yolu_kapsamasi.py
  · UI, API, chatbot ve karşılaştırmanın tamamı kampanyalari_getir üzerinden okur
```

Son test, "beşinci okuma yolu eklenince filtre unutulur" riskini kapatır.

---

## 1.7 · Korpus seçimi beyan edilmiş bir kuraldan türer

### Kök neden

```
data/raw içinde HTML : 283
data/raw içinde JSON :  96      (banka başına tam 12)
Toplayıcı sınırı     :  60/banka
Çekim tarihi         :  tümü 09.08.2026
```

Banka başına **tam 12** rakamı koddan gelmiyor. ~187 kaydın üst verisi
toplandıktan sonra elle silinmiş ve **seçim ölçütü hiçbir yerde yazmıyor.**
`docs/VERI_METODOLOJISI.md` bu adımdan hiç söz etmiyor.

Bu, iki iddiayı birden çürütür: *"veri seti yeniden üretilebilir"* ve
*"seçimde yanlılık yok"*. Jürinin sorusu tek cümledir: **"96 kaydı nasıl
seçtiniz?"**

### Reddedilen yamalar

| Yama | Neden reddedildi |
|---|---|
| `VERI_METODOLOJISI.md`'ye "elle seçildi" yazmak | Dürüst ama yeniden üretilebilir değil; yanlılık iddiasına cevap vermez. |
| 187 kaydı geri koymak | Altın set 96 kayıt üzerinde etiketlendi; korpus büyürse eşleşme ve ölçüm bozulur. |

### Genel çözüm — seçim, kod olarak

Altın set örneklemesinde **zaten uygulanan** disiplin korpusa taşınır:
`tools/altin_set.py` sabit tohumla katmanlı örnekleme yapıyor ve gerekçesini
yazıyor (*"Jüri 'bu 60 örneği nasıl seçtiniz?' diye sorduğunda cevap
'rastgele' değil, 'şu tohumla katmanlı' olmalı."*). Aynı cevap korpus için de
verilmelidir.

```yaml
# data/korpus_secimi.yaml — sürümlenmiş, denetlenebilir
surum: 1
tohum: 20260809
kaynak_dizin: data/raw
kural:
  banka_basi_adet: 12
  katman: banka_kodu
  eleme:
    - belge_turu_disi: [KURUMSAL]      # 1.3'teki sınıflandırma
    - asgari_govde: 200
  siralama: kampanya_id                # belirlenimli, tohumdan bağımsız
gerekce: >
  8 GB makinede kayıt başına ~13 sn LLM çıkarımı ile 96 kayıt ~21 dakika sürer;
  283 kayıt ~1 saat. Banka başına eşit adet, banka bazlı yanlılığı önler
  (şartname 15.1). Adet, ablasyonun üç kez koşulabilmesi için seçildi.
```

```bash
make korpus     # data/raw + korpus_secimi.yaml -> işlenecek kayıt listesi
```

```
tests/test_korpus_secimi.py
  · kural iki kez koşulduğunda AYNI 96 kimliği üretir
  · veritabanındaki korpus == kuralın ürettiği liste
  · banka dağılımı kuralın beyan ettiği katmanlamaya uyar
```

İkinci iddia önemli: veritabanı ile kural ayrışırsa **test kırılır**. Yani
"elle müdahale" bir daha sessizce olamaz.

**Ve gerekçe yazılır.** Jüriye *"kaynak kısıtı nedeniyle banka başına 12 kayıt
seçtik, seçim kuralı depoda, banka bazlı yanlılığı önlemek için katmanlı"*
demek; *"96 kayıt topladık"* demekten hem daha dürüst hem daha güçlüdür.

---

# BÖLÜM 2 — Ölçüm metodolojisi

## 2.1 · Bölünme sözleşmesi: altın set ayrılmalıdır

### Kök neden — en tehlikeli bulgu

Zaman çizelgesi tek başına konuşuyor:

```
15 Ağu  76ea39b  Altın set tamamlandı (60 örnek)
15 Ağu  c9d6508  "Altın setin yakaladığı iki çıkarım hatası düzeltildi"
16 Ağu  e515f77  Alan bazlı F1 / makro-F1
18 Ağu  545c106  "dilim tablosu ayrıştırıcı — finansman_tutari_max 0,400 -> 0,714"
18 Ağu  fd4c7f8  "kampanya_turu — URL alt türü ve puan kanıtı düzeltmesi"
```

Altın set korpusun **%62,5'i** (60/96). Ayrılmış test kümesi yok. Yayınlanan
**makro-F1 0,778 bir eğitim skorudur**, görülmemiş veri skoru değil.

> Jürinin tek cümlelik sorusu: **"Bu 60 örneğin kaçını kural yazarken
> gördünüz?"** — Bugünkü cevap: *hepsini.*

Bu boşluk, ölçüm titizliğinizi (önyükleme GA, «hep boş» tabanı, N sütunu,
🔸 işareti — hepsi gerçekten iyi) **tek hamlede etkisiz kılabilir.**

### Reddedilen yamalar

| Yama | Neden reddedildi |
|---|---|
| Altın seti 60'tan 80'e çıkarmak | Boyut sorunu değil, **ayrım** sorunu. 80 örnek de eğitim skoru olur. |
| Sunumda "in-sample" diye dipnot düşmek | Dürüst ama yetersiz; jüri "peki gerçek skor kaç?" diye sorar, cevap yok. |
| Kural değişikliklerini geri almak | Düzeltmeler gerçek hataları kapattı; geri almak sistemi kötüleştirir. |

### Genel çözüm — belirlenimli bölünme + kirlenme koruması

#### Adım 1: Bölünme kod olarak tanımlanır

```python
# eval/bolunme.py
import hashlib

class Bolunme(StrEnum):
    GELISTIRME = "gelistirme"   # kural yazarken bakılabilir
    SAKLI      = "sakli"        # yalnız ölçümde açılır

def bolunme(kampanya_id: str, sakli_oran: float = 0.35) -> Bolunme:
    """Kimliğin özetinden belirlenimli bölünme.

    NEDEN HASH — rastgele bölünme her koşuda değişir, kayıtlar bölünmeler
    arasında gezinir ve 'saklı' garantisi çöker. Özet, kimlik sabit
    kaldıkça bölünmeyi de sabit tutar; korpus büyüdüğünde mevcut kayıtlar
    yerinde kalır, yalnız yeniler dağıtılır.
    """
    h = hashlib.sha256(kampanya_id.encode()).hexdigest()
    return (Bolunme.SAKLI if int(h[:8], 16) / 0xFFFFFFFF < sakli_oran
            else Bolunme.GELISTIRME)
```

#### Adım 2: Bugünkü durumdan temiz bir saklı küme çıkarmak

Korpusun **36 kaydı hiç etiketlenmedi** — dolayısıyla hiçbir F1 sayısı onlara
bakılarak iyileştirilemedi. Bu, doğal ve dürüst bir saklı kümedir.

| Küme | Kayıt | Rolü |
|---|---|---|
| Mevcut altın set (60) | etiketli, kural yazarken görüldü | **Geliştirme** — bundan sonra da geliştirme |
| Etiketlenmemiş 36 | hiç etiketlenmedi | **Saklı** — etiketlenip dondurulur |

36 kaydın etiketlenmesi `tools/altin_set.py` ile aynı yoldan yapılır: körleme
CSV, kişi başı dosya, `derle`. Dört kişiye bölününce **kişi başı 9 kayıt × 8
alan** — bir oturumluk iş. Mevcut araç zaten hazır, yeni kod yok.

Sonra **dondurma**:

```
data/gold/sakli_set.jsonl          # etiketler
data/gold/sakli_set.KILIT          # sha256 + tarih + "bu dosya değişmez"
tests/test_sakli_kilit.py          # kilit tutmuyorsa TEST KIRILIR
```

#### Adım 3: Kirlenme koruması

```python
# eval/calistir.py
def altin_set_metrikleri(kampanyalar, altin=None, *, bolunme: Bolunme):
    """Hangi bölünmenin ölçüldüğü ZORUNLU parametredir — varsayılan yok.
    Bölünme beyan edilmeden metrik üretilemez."""
```

`docs/SONUCLAR.md` iki tabloyu yan yana basar ve **manşet sayı saklı kümenin
sayısıdır**:

```markdown
| Metrik | Geliştirme (n=60) | **Saklı (n=36)** | Hedef |
|---|---|---|---|
| Makro-F1 | 0,778 _(GA 0,645–0,847)_ | **0,7XX** _(GA …)_ | ≥ 0,78 |

> Geliştirme kümesi kural yazarken görüldü; bu sütun **eğitim skorudur**.
> Saklı küme yalnız ölçümde açıldı, koşu sayısı: N (`sakli_kosu_defteri.json`).
```

Ve koşu defteri: her saklı ölçüm tarih + `kod_parmak_izi` ile kaydedilir. Jüri
*"saklı kümeye kaç kez baktınız?"* diye sorduğunda **sayılı cevap** vardır.
`kod_parmak_izi` mekanizması zaten mevcut — yeni altyapı yok.

### Testler

```
tests/test_bolunme.py
  · bölünme belirlenimli: aynı kimlik → aynı bölünme, 1000 koşuda
  · geliştirme ∩ saklı = ∅
  · korpus büyüdüğünde mevcut kayıtların bölünmesi DEĞİŞMEZ
tests/test_sakli_kilit.py
  · sakli_set.jsonl özeti KİLİT dosyasıyla uyuşmalı
tests/test_bolunme_beyani.py
  · altin_set_metrikleri bölünme parametresi olmadan çağrılamaz
```

### Jüri savunması — ezberlenecek cevap

> *"Altın setimiz iki bölünmeye ayrılmıştır. 60 örneklik geliştirme kümesini
> kural yazarken gördük ve bunu açıkça eğitim skoru olarak yayınlıyoruz.
> 36 örneklik saklı küme kimlik özetinden belirlenimli olarak ayrıldı,
> etiketlendikten sonra sha256 ile kilitlendi ve ölçümde N kez açıldı —
> koşu defteri depoda. Manşet makro-F1'imiz saklı kümenin sayısıdır."*

Bu cevap, **bugünkü en büyük açığı en güçlü savunmaya çevirir.** Çoğu takımın
ayrılmış test kümesi yoktur; kilit dosyası ve koşu defteri hiç yoktur.

---

## 2.2 · Ablasyon: karşılaştırılabilirlik koşumun kendisiyle garanti edilir

> ✅ **UYGULANDI — 19 Ağustos 2026.** ADR 011 · `eval/ablasyon.py` ·
> `make ablasyon` · `tests/test_ablasyon_butunlugu.py` (9 test).
> Tablodaki farklı kod izi **2 → 1** (yapısal garanti) · yarım tablo
> **imkânsız** · elle komut **6 → 1**.
>
> **Tasarımda olmayan ikinci bulgu çıktı ve o da kapatıldı:** ablasyon koşusu
> ÜRETİM veritabanına yazıyordu. `make extract-kural`, demoyu besleyen 96
> kaydı katman eksik hâlleriyle değiştiriyordu; sonrasında `make extract`
> koşulmazsa arayüz sessizce bozuk veri gösteriyordu. Artık her yapılandırma
> kendi veritabanına yazar (`data/ablasyon/{ad}.db`).

### Kök neden

`data/ablasyon.json`:

| Satır | Tarih | `kod_parmak_izi` |
|---|---|---|
| `llm` | 17 Ağu | `f797dd3f69630cfc` |
| `kural` | 17 Ağu | `f797dd3f69630cfc` |
| **`hibrit`** | **18 Ağu** | **`f835ccc2f7e8d116`** ← farklı |

Kodunuz bu durumu **zaten yakalıyor** ve *"🔴 Satırlar KARŞILAŞTIRILAMAZ"*
basıyor. Yani sunumun en güçlü grafiği (hibrit 0,778 vs kural 0,628 vs LLM
0,176) bugün geçersiz: hibrit satırı **daha yeni ve iyileştirilmiş kodla**
koşulmuş.

Eksik olan tespit değil, **koşum**: üç yapılandırma üç ayrı elle komutla,
farklı zamanlarda çalıştırılıyor. Sıranın bozulması bir insan hatası ve insan
hatasını uyarıyla değil, **yapıyla** engellemek gerekir.

### Genel çözüm — atomik ablasyon koşucusu

```bash
make ablasyon      # tek komut: üç yapılandırma + üç ölçüm + tablo
```

```python
# eval/ablasyon.py
def calistir() -> int:
    """Üç yapılandırmayı TEK süreçte, TEK kod parmak iziyle koşar.

    NEDEN TEK SÜREÇ — üç ayrı komut arasında kod değişebilir ve satırlar
    karşılaştırılamaz hâle gelir (17-18 Ağustos'ta tam olarak bu oldu).
    Tek süreçte parmak izi başta bir kez alınır; farklılık YAPISAL OLARAK
    imkânsızdır, uyarıya gerek kalmaz.
    """
    parmak_izi = kod_parmak_izi()
    sonuclar = {}
    for ad, bayraklar in (("kural", {"llm_kullan": False}),
                          ("llm",   {"kural_kullan": False}),
                          ("hibrit", {})):
        kampanyalar = cikarimi_kos(**bayraklar)
        sonuclar[ad] = altin_set_metrikleri(kampanyalar, bolunme=Bolunme.SAKLI)
    _tabloyu_yaz(sonuclar, parmak_izi)   # tek yazım, kısmi tablo YOK
```

İki yapısal garanti:

1. **Tek parmak izi** — satırların ayrışması imkânsız
2. **Atomik yazım** — koşu yarıda kalırsa `ablasyon.json` **hiç yazılmaz**;
   yarım tablo diye bir durum kalmaz

Mevcut `_ablasyon_notu()` içindeki parmak izi ve korpus büyüklüğü uyarıları
**silinmez** — savunma katmanı olarak kalır. Ama artık tetiklenmemeleri
gerekir; tetiklenirlerse gerçek bir arıza var demektir.

**Süre.** 96 kayıt × 3 yapılandırma; LLM'siz kural koşusu saniyeler,
LLM içeren iki koşu ~21'er dakika → toplam **~45 dakika.** Bir kahve molası.
Bu, sunumun en güçlü grafiğinin geçerliliği için makul bir bedel.

```
tests/test_ablasyon_butunlugu.py
  · üç satır aynı parmak izini ve aynı korpus büyüklüğünü taşır
  · koşu ortasında hata → ablasyon.json DEĞİŞMEZ (atomiklik)
  · eksik yapılandırmayla tablo üretilmez
```

---

## 2.3 · Metrik kapsamı: makro-F1 paydasıyla birlikte yayınlanır

### Kök neden — iki ayrı sorun

**(a) Payda gizli.** 16 alanın 9'u *"ölçülmedi"*. Makro-F1 yalnız ölçülen
7 alanın ortalaması ama **manşette bu görünmüyor**. Üstelik en sağlam
örneklenmiş alan (`kampanya_turu`, N=60) en zayıfı: F1 **0,717**, 17 yanlış
pozitif. Kalan 6 alanın 4'ünde N ≤ 7.

**(b) Ölçülemez sanılan alanlar aslında ölçülebilir.** ADR 008'in gerekçesi:

> *"Serbest metin alanları … `eval` bunları BİREBİR string karşılaştırmasıyla
> ölçüyor. Elle yazılmış bir cümlenin modelin cümlesiyle harfi harfine tutması
> pratikte imkânsız."*

Bu **birebir eşleşme için doğru, bilgi çıkarımı değerlendirmesi için yanlış.**
Alanın standart cevabı `belirteç düzeyinde F1`'dir (SQuAD ve tüm IE
literatürünün ölçütü). Yani 4 metinsel alan ölçülemez değil, **yanlış metrikle
ölçülmeye çalışılmış.**

### Genel çözüm A — alan tipine göre metrik

```python
# eval/metrikler.py
def alan_skoru(alan_adi: str, beklenen, bulunan) -> float:
    """Metrik, ALANIN TİPİNDEN türer — tek metrik hepsine dayatılmaz."""
    match ALAN_TIPLERI[alan_adi]:
        case AlanTipi.SAYISAL:  return 1.0 if _toleransli_esit(...) else 0.0
        case AlanTipi.ENUM:     return 1.0 if beklenen == bulunan else 0.0
        case AlanTipi.TARIH:    return 1.0 if beklenen == bulunan else 0.0
        case AlanTipi.METIN:    return _belirtec_f1(beklenen, bulunan)

def _belirtec_f1(beklenen: str, bulunan: str) -> float:
    """Normalize belirteç kümeleri üzerinden F1.

    `arama_anahtari()` ile normalize edilir — Türkçe küçültme, şapka ve
    kesme işareti sorunları zaten orada çözülmüş. Yeni normalizasyon
    yazılmıyor.
    """
    a, b = set(arama_anahtari(beklenen).split()), set(arama_anahtari(bulunan).split())
    if not a or not b:
        return 0.0
    ortak = len(a & b)
    if ortak == 0:
        return 0.0
    k, d = ortak / len(b), ortak / len(a)
    return 2 * k * d / (k + d)
```

Metinsel alanlar `tools/altin_set.py`'de **kısa referans ifade** olarak
etiketlenir (cümle değil, çekirdek ifade) — böylece etiketleme yükü artmaz.
`CEKIRDEK_ALANLAR` 8'den 12'ye çıkar; 4 yeni alan × 36 saklı kayıt ≈ kişi başı
36 hücre. Saklı set etiketlemesiyle **aynı oturumda** yapılır.

### Genel çözüm B — kapsam manşetin parçası

```markdown
| Metrik | Değer | Kapsam | Hedef |
|---|---|---|---|
| **Makro-F1** | 0,7XX _(GA …)_ | **11/16 alan · n=36** | ≥ 0,78 |
```

Ve `HEDEFLER` sözlüğüne bir eşik daha:

```python
HEDEFLER = {..., "olculen_alan_orani": 0.75}   # 16 alanın en az %75'i ölçülmeli
```

Kapsam düşerse rapor ❌ basar. Böylece *"az alanı ölçüp yüksek ortalama
göstermek"* mekanik olarak cezalandırılır.

```
tests/test_belirtec_f1.py
  · birebir aynı metin → 1,0
  · tümüyle farklı → 0,0
  · "masrafsız konut finansmanı" ↔ "konut finansmanında masraf yok" → makul kısmi skor
  · Türkçe büyük/küçük ve şapka farkı skoru DEĞİŞTİRMEZ
tests/test_kapsam_esigi.py
  · ölçülen alan oranı eşiğin altındaysa rapor ❌ basar
```

### Jüri savunması

> *"Makro-F1'imizi paydasıyla yayınlıyoruz: 16 alanın 11'i, 36 saklı örnek
> üzerinde. Metinsel alanları birebir eşleşmeyle ölçmek anlamsız olduğu için
> belirteç düzeyinde F1 kullanıyoruz — çıkarım değerlendirmesinin standart
> ölçütü. Ölçemediğimiz 5 alanı ortalamaya katmıyoruz ve bunu manşette
> söylüyoruz; kapsam eşiğin altına düşerse raporumuz kendi kendine
> başarısız işaretler."*

---

## 2.4 + 2.5 · Türetilmiş belge sözleşmesi

### Kök neden

Sayılar elle kopyalanıyor, dolayısıyla ayrışıyor:

| Yer | İddia | Gerçek |
|---|---|---|
| `545c106` commit | `finansman_tutari_max 0,400 -> 0,714` | `SONUCLAR.md`: **0,615** |
| `docs/HATA_ANALIZI.md` | makro-F1 **0,699** · `kampanya_turu` **0,567** | **0,778** · **0,717** |
| `docs/KURULUM.md:223` | *"**92 test** geçmeli"* | **459** |
| `CLAUDE.md:120` | *"**296 test**"* | **459** |

`eval/calistir.py` dosyanın başına *"Bu dosya elle düzenlenmez"* yazıyor ve
bayatlık uyarı mekanizması kuruyor — ama koruma **yalnız `SONUCLAR.md`'yi**
kapsıyor. Onu alıntılayan belgeler korumasız.

Takımın kendi uyarısı bu tuzağı tarif ediyor:

> *"⚠️ Bu dosya bayatlarsa zararlıdır. … Yanlış alarm, takımı çözülmüş işe
> koşturur."* — `docs/SARTNAME_UYUM.md`

### Reddedilen yamalar

| Yama | Neden reddedildi |
|---|---|
| Bayat sayıları elle düzeltmek | Bir hafta sonra yine bayatlar. Sınıf kapanmaz. |
| Belgeleri tümüyle üretmek | `HATA_ANALIZI.md`'nin değeri insan yorumunda; otomatik üretim onu öldürür. |

### Genel çözüm — sayılar alıntılanır, kopyalanmaz

Bir belge metrik içeriyorsa iki yoldan birini seçer:

**Yol 1 — türetilmiş bölüm.** İşaretlenmiş blok, `make belgeler` ile yeniden
üretilir:

```markdown
<!-- TURETILMIS:baslangic kaynak=data/ablasyon.json alan=hibrit.makro_f1 -->
Makro-F1 **0,778**
<!-- TURETILMIS:bitis -->
```

**Yol 2 — beyan edilmiş bağımlılık.** Belge, ön bilgide neye dayandığını yazar:

```yaml
---
kaynak: docs/SONUCLAR.md
kaynak_ozeti: sha256:4f3a…
---
```

Ve tek bir test bütün belgeleri denetler:

```
tests/test_belge_tazeligi.py
  · TURETILMIS blokları kaynak değerle uyuşmalı
  · `kaynak_ozeti` beyan eden belgelerin özeti tutmalı
  · hiçbir belgede beyansız metrik iddiası kalmamalı (regex tarama)
  · "N test geçmeli" iddiaları pytest'in TOPLADIĞI sayıyla uyuşmalı
```

Son iddia `KURULUM.md`, `CLAUDE.md` ve README'yi bir daha ayrışamaz hâle
getirir. Ve commit mesajı disiplini:

> **Commit mesajına metrik yazılmaz.** Metrik `docs/SONUCLAR.md`'dedir; commit
> yalnız *"hangi hata sınıfı kapandı"* der. Tek doğruluk kaynağı ilkesi commit
> geçmişine de uygulanır. İsteğe bağlı: `make olcum-notu` mevcut ölçümden
> commit gövdesine eklenecek satırı **üretir** — yazılmaz, üretilir.

---

# BÖLÜM 2B — Jürinin cevabından doğan bulgular

_19 Ağustos soru-cevap toplantısı sonrası eklendi._

Jüri şunu söyledi:

> *«Sizin değerlendirme kriterleriniz de önemli ama **o anda jüri kendisi de
> test verisi verebilir**.»*

Bu, ölçüm sorusunu değiştiriyor. Altın set *«bizim seçtiğimiz 60 örnekte ne
kadar iyiyiz?»* sorusunu cevaplıyor; jürininki farklı: **«hiç görmediğin bir
metinde ne oluyor?»** Cevabı aramak iki bulgu ortaya çıkardı.

## 2B.1 · Tek atama: bir sayıyı yalnız bir alan sahiplenebilir ✅

> ✅ **UYGULANDI — 19 Ağustos 2026.** `src/extraction/kural.py::_tek_atama` ·
> `tests/test_tek_atama.py` (12 test).

### Kök neden

Jüri tarzı **düz metin** denendi:

```
"…aylık kâr payı oranı %2,45'ten başlıyor. … Tahsis ücreti %0,75."

kar_payi_orani = 0.75   span=(138,145)
tahsis_ucreti  = 0.75   span=(138,145)   <- AYNI SPAN
Doğru cevap %2,45 tümüyle kaçırıldı.
```

Her kural metni **bağımsız** tarıyordu; aynı sayıyı iki alanın sahiplenmesini
engelleyen hiçbir şey yoktu. `kar_payi_orani` `secim="en_dusuk"` olduğu için
2,45 yerine 0,75'i seçiyordu.

**Sınıf hatasıdır:** tahsis ücreti gerçek hayatta %0,5–1, kâr payı %2–4 seyreder.
Yani *oranın altında bir ücret yüzdesi olan her düz metinde* kâr payı yanlış
çıkardı. Tablolarda oluşmuyordu (kolon başlığı yanlış kolonu eliyor) — **ama
jüri tablo değil düz metin yapıştırır.**

### Çözüm ölçütü: mesafe, güven DEĞİL

İlk sezgi «en güvenilir alan span'ı alsın» idi. Ölçüm bunu çürüttü:

| Alan | `%0,75` için güven | Bağlam sözcüğü |
|---|---|---|
| `kar_payi_orani` | **0,8828** | uzak (taban 0,93) |
| `tahsis_ucreti` | 0,8415 | **bitişik** (taban 0,85) |

Güven, alanın **taban güvenini** — bir *önseli* — içerir ve o önsel *bu span*
hakkında bir kanıt değildir. Güvene bakan bir kural span'ı **yanlış alana**
verirdi.

Sahiplik yalnız bu span'a ait kanıtla çözülür: **hangi alanın bağlam sözcüğü
daha yakın.** `Aday.mesafe` bu yüzden `guven`'den ayrı taşınır. Eşitlikte
`KURALLAR` bildirim sırası — keyfi ama deterministik.

Kaybeden alan susmaz: span'ı listesinden düşer ve **kalan** adaylarından seçim
yapar. Örnekte `kar_payi_orani` böylece `%2,45`'e ulaşır.

## 2B.2 · Görülmemiş metin ölçümü ✅

> ✅ **UYGULANDI — 19 Ağustos 2026.** `eval/gorulmemis.py` ·
> `make eval-gorulmemis` · `docs/GORULMEMIS_METIN.md` ·
> `tests/test_gorulmemis.py` (9 test).

### Veri ücretsizdi ve zaten depodaydı

`data/raw` altında **283 HTML ama 96 JSON** var. Aradaki **187 sayfa** 9
Ağustos taramasında gerçekten çekildi, korpus seçiminde dışarıda kaldı ve
**geliştirme boyunca hiç görülmedi** — ne kural yazarken bakıldı, ne altın sete
girdi, ne bir metrik onlara göre ayarlandı. Jürinin vereceği veriye en yakın
vekil budur ve **etiketleme maliyeti sıfırdır.**

### Etiketsiz ölçülebilenler — kanıt zinciri sayesinde

Sistemin kendi sözleşmesi, doğru cevabı bilmeden ölçüm yapmayı mümkün kılıyor:

| Denetim | 187 sayfada sonuç |
|---|---|
| Çöken kayıt | **0** |
| **Kanıt ihlali (halüsinasyon)** | **0** |
| Boyut ihlali (birimsiz değer) | **0** |
| Çözülmemiş span çakışması | **0** |
| Alan doluluğu | %8,2 (yalnız kural katmanı) |

Ayrıca bir **teşhis**: `_tek_atama` bu 187 sayfada **124 kez** devreye girdi.
Yani 2B.1'de düzeltilen hata nadir bir uç durum değildi.

### Dürüst sınır — raporun içinde yazılı

Bu ölçüm **doğruluk ölçmez.** Çıkarılan değerin doğru olup olmadığını
bilmiyoruz; yalnız **kanıtlı** olduğunu biliyoruz. Doğruluk için altın set
gerekir. İki ölçüm birbirinin yerine geçmez, farklı soruları cevaplar.

> İlk sürüm bu ayrımı kaçırdı: 124 *çözülen* çakışmayı «ihlal» sütununa yazıp
> ❌ basıyordu. Bir sayının ne anlama geldiğini yanlış etiketlemek, ölçmemekten
> kötüdür — `test_ham_cakisma_ihlal_olarak_gosterilmez` bunu sabitledi.

## 2B.3 · Metin yapıştırma ekranı ⬜ — Esra (ES-19)

Jüri metin verirse bugün **Swagger'da JSON göstermek** zorundayız; sistemin en
güçlü iddiasını en zayıf biçimde sunmuş oluruz. Ayrıca şartname madde 6, demo
videosunda *«metin girdisi verilmesi»* ve *«yapılandırılmış çıktı»* gösterilmesini
şart koşuyor — **tek iş, iki teslimat.**

Görev `GOREVLER.md`'de **ES-19** olarak, kabul ölçütleri ve gecikme stratejisiyle
birlikte yazıldı (kural katmanı anında → LLM `spinner` içinde zenginleştirir;
bu aynı zamanda hibrit mimariyi gözle gösterir).

---

# BÖLÜM 3 — Uygulama planı

## 3.1 Bağımlılık grafiği

Sıra keyfi değil; oklar gerçek bağımlılıkları gösterir.

```
1.1a Birim ──┬──► 1.1b Dayanak ──► (Vakıf %75 sınıfı kapanır)
             │
             ├──► 1.3b Karşılaştırma sınıfı ──► (%0 sıralaması düzelir)
             │
             └──► 1.4c Muhakeme ürün ailesi

1.3a Belge türü ──► 1.5 (diger oranı) ──► 1.7 Korpus seçim kuralı

1.2 Kalkan kökenleri        (bağımsız — hemen başlanabilir)
1.6 Zamansal geçerlilik     (bağımsız)
1.4a Üretici sözleşmesi     (bağımsız, 30 dk, hemen)
2.4+2.5 Belge tazeliği      (bağımsız, 30 dk, hemen)

2.1 Bölünme ──► 2.3 Kapsam ──► 2.2 Ablasyon ──► SONUCLAR.md manşeti
      ▲
      └── 36 kaydın etiketlenmesi (dört kişi, tek oturum)
```

**Kritik yol:** `36 kaydın etiketlenmesi → 2.1 → 2.3 → 2.2 → sunum sayıları`.
Etiketleme gecikirse manşet sayılar gecikir. **İlk başlatılacak iş budur** —
çünkü tek bloke eden iş odur ve dört kişinin eşzamanlı emeğini gerektirir.

## 3.2 Altı günlük gerçekçi plan

**Teslim: 25 Ağustos 20:00. Bugün 19 Ağustos.**

> ⚠️ **Bu belge, Esra'nın video + sunum işinin yerine geçmez.**
> Demo videosu (5 dk *ve* 1 dk) ve sunum PDF+PPTX **şartname madde 6 ve 10'un
> zorunlu teslimleridir** ve şu an `sunum/` klasörü boş. Kod ne kadar
> düzelirse düzelsin, o teslimler olmadan puan doğrudan kaybedilir.
> Aşağıdaki plan Eren + Samet + Görkem hattıdır; **Esra'nın hattı paralel
> koşar ve hiçbir koşulda bu işlere kaydırılmaz.**

### Kesme çizgisi

| Öncelik | İş | Kim | Süre | Neden bu tarafta |
|---|---|---|---|---|
| **P0** | 36 kaydın etiketlenmesi (saklı set) | **Dördü** | 1 oturum | Kritik yolun başı; ertelenirse hiçbir manşet sayı düzelmez |
| ~~P0~~ ✅ | ~~1.2 Kalkan köken tipleri~~ **BİTTİ (ADR 010)** | Eren | 4 sa | Demoda %20 yanlış blok; en özgün özellikte |
| ~~P0~~ ✅ | ~~1.1a `Birim`~~ **BİTTİ (ADR 009)** | Eren | 1 gün | *"0,50 TL"* ekranda; masraf sıralaması yanlış |
| **P0** | 2.1 Bölünme + kilit + koşu defteri | Eren | 4 sa | En tehlikeli jüri sorusunun cevabı |
| ~~P0~~ ✅ | ~~2.2 Atomik ablasyon~~ **BİTTİ (ADR 011)** | Eren | 1 sa + koşu | Sunumun en güçlü grafiği bugün geçersiz |
| **P0** | 2.4+2.5 Belge tazeliği testi | Görkem | 1 sa | Ucuz, görünür, tekrarı engeller |
| **P1** | 1.6 Zamansal geçerlilik | Görkem | 3 sa | Demoda süresi dolmuş kampanya görünür |
| **P1** | 1.3b Karşılaştırma sınıfı | Samet | 4 sa | *"oran %0'dır"* cevabı |
| **P1** | 1.4a Üretici sözleşmesi testi | Eren | 30 dk | Sınıfı kapatır, ucuz |
| **P1** | 2.3 Belirteç F1 + kapsam eşiği | Samet | 4 sa | 4 alan "ölçülmedi"den çıkar |
| **P1** | 1.7 Korpus seçim kuralı | Görkem | 3 sa | *"96 kaydı nasıl seçtiniz?"* |
| **P2** | 1.1b `Dayanak` | Samet | 4 sa | Vakıf `%75` sınıfı |
| **P2** | 1.4b `uygunluk` çıkarımı + yeniden koşu | Samet | 6 sa | Müşteri Profili sayfasının içi |
| **P2** | 1.3a Belge türü + yeniden koşu | Görkem | 1 gün | `%48 diger` paydası |

### P2 yetişmezse — dürüst geri çekilme

Bu belgenin ilkesi eksiği gizlemek değil. P2 kalemleri yetişmezse
**gizlenmez, beyan edilir:**

- **1.4b yetişmezse:** Müşteri Profili ekranı demoda gösterilir ama
  *"kısıt çözücü hazır ve deterministik; kısıt çıkarımı Sprint 2'de"*
  denir. `veri_eksik` işareti zaten ekranda — **sistem şu an da doğru
  davranıyor, yalnız girdisi yok.** Bu savunulabilir; gizlemek değildir.
- **1.3a yetişmezse:** `%48 diger` oranı `docs/HATA_ANALIZI.md`'de kök
  nedeniyle yazılır: *"korpusun bir bölümü kampanya belgesi değil; belge
  türü sınıflandırması Sprint 2."*
- **1.1b yetişmezse:** Vakıf `%75` kaydı bilinen hata olarak
  `HATA_ANALIZI.md`'ye girer. **`docs/SONUCLAR.md`'den elle silinmez.**

> **Kural:** Yetişmeyen iş için ölçüm bozulmaz, kayıt silinmez, sayı
> düzeltilmez. Yetişmeyen iş **yazılır.** Jüri, bilinen ve yazılmış bir
> eksiği; gizlenmiş bir eksikten çok daha iyi karşılar.

## 3.3 Yazılacak ADR'ler

`src/schema.py` donmuş olduğu için `CLAUDE.md` protokolü zorunlu:

| ADR | Konu | Sürüm etkisi |
|---|---|---|
| `009-boyutlu-nicelik.md` | `Birim` · `Dayanak` · `Nicelik` | **2.0.0** (kırıcı) |
| `010-koken-tipli-kalkan.md` | `CevapParcasi` · `Koken` | şema dışı |
| `011-bolunme-sozlesmesi.md` | geliştirme / saklı, kilit, koşu defteri | şema dışı |
| `012-belge-turu-ve-karsilastirma-sinifi.md` | iki katmanlı sınıflandırma | 2.1.0 |
| `013-metrik-alan-tipinden-turer.md` | belirteç F1, kapsam eşiği | şema dışı |

ADR 008 (*altın set kapsamı*) **geçersiz kılınmaz, güncellenir**: metinsel
alanların ölçülemez olduğu gerekçesi ADR 013 ile düşer; ADR 008'e
*"üzerine yazan: 013"* satırı eklenir. Kararın neden değiştiğini görmek,
kararı silmekten değerlidir.

## 3.4 Kabul ölçütleri

Bir iş, aşağıdaki üçü birden sağlanmadan "bitti" sayılmaz:

1. **Regresyon testi var** — bulguyu üreten tam senaryo teste dönüşmüş
2. **Sınıf testi var** — aynı hata sınıfının *başka* bir örneği de yakalanıyor
3. **`make test` ve `make lint` yeşil**

Sayılabilir hedefler:

| Ölçüt | Bugün | Hedef | Nerede ölçülür |
|---|---|---|---|
| Kalkan yanlış blok oranı | %20 | **%0** | `docs/SONUCLAR.md` (yeni metrik) |
| Birimsiz sayısal alan | 8 alan | **0** | `test_uretici_kapsamasi.py` |
| Ablasyon parmak izi sayısı | 2 | **1** | `test_ablasyon_butunlugu.py` |
| Ölçülen alan / toplam alan | 7/16 | **≥ 11/16** | `SONUCLAR.md` kapsam sütunu |
| Manşet makro-F1'in bölünmesi | beyansız | **saklı** | `SONUCLAR.md` |
| Beyansız metrik iddiası (belgeler) | ≥ 4 | **0** | `test_belge_tazeligi.py` |
| Süresi dolmuş kampanya (varsayılan liste) | 5 | **0** | `test_gecerlilik.py` |
| Üreticisiz şema alanı | 1 (`uygunluk`) | **0** | `test_uretici_kapsamasi.py` |

## 3.5 Jüri savunması — tek sayfa

Sunumda ve soru-cevapta kullanılacak beş cümle:

**1 · Birim.**
> *"Sistemimizde çıplak sayı yoktur. Her nicelik birimini, her yüzde
> dayanağını taşır. Farklı birimler ancak beyan edilmiş bir senaryoda ortak
> tabana indirilerek karşılaştırılır; indirilemiyorsa sıralama yapmayız,
> 'karşılaştırılamaz' deriz."*

**2 · Kalkan.**
> *"Sayısal doğrulama kalkanımız cevabın her parçasını kökenine göre
> denetler: yapısal iddia yapısal alana, alıntı kaynak metne, hesap ise
> yeniden hesaplanarak. Kalkanı gevşetmedik — ona eksik olan köken bilgisini
> verdik ve bu sayede hesap bölümündeki kör noktayı da kapattık."*

**3 · Bölünme.**
> *"Altın setimiz geliştirme ve saklı olmak üzere ikiye ayrılmıştır. Saklı
> küme kimlik özetinden belirlenimli ayrıldı, sha256 ile kilitlendi, koşu
> defteri depoda. Manşet makro-F1'imiz saklı kümenin sayısıdır — geliştirme
> skorunu da yayınlıyoruz ama onun eğitim skoru olduğunu söyleyerek."*

**4 · Ablasyon.**
> *"Üç yapılandırma tek süreçte, tek kod parmak iziyle koşar. Farklı
> sürümlerle koşulmuş satırların aynı tabloya girmesi yapısal olarak
> imkânsızdır; koşu yarıda kalırsa tablo hiç yazılmaz."*

**5 · Dürüstlük.**
> *"Ölçemediğimiz alanı sıfır göstermiyoruz, 'ölçülmedi' diyoruz.
> Yetişmeyen işi gizlemiyoruz, `HATA_ANALIZI.md`'ye yazıyoruz. Bildiğimiz
> kusurları biz söylüyoruz — çünkü ölçtük."*

---

## Ek A — Bulgu ↔ çözüm ↔ test izlenebilirlik tablosu

| # | Bulgu | Kök neden (düşen bilgi) | Çözüm | Sınıfı kapatan test |
|---|---|---|---|---|
| 1.1a ✅ | `tahsis_ucreti` TL/% karışımı, *"0,50 TL"* | Birim | `Alan.birim` + `ALAN_BOYUTLARI` sözleşmesi | `test_boyut_sozlesmesi.py` |
| 1.1b ⬜ | `%75 komisyon indirimi` ücret sanılıyor | Dayanak | `Dayanak` çözümleme | — |
| 1.2 ✅ | Kalkan meşru cevabı blokluyor | Köken | `CevapParcasi` + köken tipli denetim | `test_kalkan_kokenli.py` |
| 1.3 | *"en düşük kâr payı → %0"* | Karşılaştırma sınıfı | `KarsilastirmaSinifi` | `test_karsilastirma_sinifi.py` |
| 1.4 | `uygunluk` hiç dolmuyor | Üretici beyanı | `ALAN_URETICILERI` + kapsama testi | `test_uretici_kapsamasi.py` |
| 1.5 | `%48 diger`, mevduat tablosundan çıkarım | Belge türü | `BelgeTuru` kapısı | `test_belge_turu.py` |
| 1.6 | Süresi dolmuş kampanya aktif | Zaman | `Gecerlilik` + zorunlu `an` | `test_okuma_yolu_kapsamasi.py` |
| 1.7 | 96 kaydın seçimi belgesiz | Seçim kuralı | `korpus_secimi.yaml` + üretim | `test_korpus_secimi.py` |
| 2.1 | Altın set ayrılmamış | Bölünme | Belirlenimli bölünme + kilit | `test_bolunme.py` |
| 2.2 ✅ | Ablasyon satırları farklı kodla | Koşu kimliği | Atomik koşucu + ayrı veritabanı | `test_ablasyon_butunlugu.py` |
| 2.3 | Makro-F1 7/16 alan | Kapsam | Alan tipine göre metrik + eşik | `test_kapsam_esigi.py` |
| 2.4 | Commit ≠ yayınlanan sayı | Türetilmişlik | Commit'te metrik yasak | `test_belge_tazeligi.py` |
| 2.5 | Bayat belgeler (0,699 / 92 test) | Türetilmişlik | Beyan edilmiş kaynak özeti | `test_belge_tazeligi.py` |

## Ek B — Bu belgenin kendi kuralına uyduğunun denetimi

Her çözüm için sorulan soru: **"Aynı hata sınıfının ikinci örneği kod
değiştirmeden yakalanıyor mu?"**

| Çözüm | İkinci örnek | Kod değişir mi |
|---|---|---|
| `Nicelik` | *"aidat iadesi %60"* → dayanak `ANAPARA` değil | **Hayır** |
| Köken tipli kalkan | yeni bir cevap üreticisi köken atamayı unutur | **Hayır** — test kırılır |
| Üretici sözleşmesi | onbirinci alan eklenip doldurulmaz | **Hayır** — test kırılır |
| `BelgeTuru` | yeni bir "yatırımcı ilişkileri" sayfası | **Hayır** |
| `Gecerlilik` | beşinci okuma yolu eklenir | **Hayır** — test kırılır |
| Bölünme kilidi | saklı set sessizce düzenlenir | **Hayır** — kilit tutmaz |
| Atomik ablasyon | koşular arası kod değişir | **Hayır** — yapısal olarak imkânsız |
| Belge tazeliği | yeni bir belge metrik alıntılar | **Hayır** — tarama yakalar |

Hiçbiri "yeni bir sözcük ekle" ile çözülmüyor. Ölçüt sağlandı.
