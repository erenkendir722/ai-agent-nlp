# ADR 015 — RAG indeksi depoya alındı, bayatlığı denetleniyor

**Tarih:** 26 Ağustos 2026 · **Durum:** kabul edildi · **Sorumlu:** Esra
**Şema etkisi:** yok · **Önceki karar:** [ADR 014](014-vektor-db-yerine-yerel-kosinus.md)

## Bağlam

ADR 014, `data/vektor_indeksi.npz` dosyasını **türetilmiş** sayıp `.gitignore`'a
koydu ve iki uyarıyı «açık kalan» olarak bıraktı. 26 Ağustos'ta ikisi de somut
zarara dönüştü.

### 1. Türetilmiş değildi

Türetilmiş dosya, elindeki girdilerden **yeniden üretilebilen** dosyadır. Bu
dosya öyle değil: `make vektor` gömmeleri EVREN'den alıyor, yani **ağ ve API
anahtarı** istiyor. Yerel gömme yedeği yok — `src/vektor_db.py` yalnız EVREN
ucunu tanıyor.

Sonuç, sistem analizi sırasında ölçüldü. Windows makinesinde `.env` içinde
anahtar yoktu; gömme ucu **401** döndü, indeks kurulamadı ve chatbot şöyle
ölçüldü:

```
make chatbot-test    doğruluk 0,742  (hedef ≥0,88)   ❌
                     kaynak gösterme 0,692 (hedef 1,00) ❌
```

31 sorunun 8'i başarısızdı ve **8'inin de sebebi aynıydı**: metin araması
isteyen sorular kaynaksız cevaplanıyordu. Görev panosunda aynı test için
**1,000 / 1,000** kayıtlıydı. Kodda gerileme yoktu — dosya yoktu.

Bu, "her geliştirici kendi indeksini kursun" varsayımının maliyeti: indeksi
kurmamış her makinede sistem **bozuk ama sessiz** çalışıyor.

### 2. Elle kopyalama adımı atlanabilir bir adımdı

ADR 014 çevrimdışı paket için «indeks dosyasını elle içermeli» dedi. Atlanınca
hata çıkmıyor: chatbot açılıyor, sayısal sorular cevaplanıyor, yalnız koşul
soruları sessizce kaynaksız kalıyor. Fiziki finalde bunun fark edilmesi
jürinin soru sormasına bağlı.

### 3. Bayatlık hiç denetlenmiyordu

`src/depolama.kod_parmak_izi` çıkarım kodunun bayatlığını yakalıyor; indeks
için karşılığı yoktu. `make durum` yalnız «kurulu mu» diyordu.

26 Ağustos'ta 93 süresi geçmiş kampanya silindi. İndeks yeniden kurulmasaydı
chatbot **silinmiş kampanyaları kaynak göstererek** cevap verecekti — üstelik
alıntısıyla, yani güvenilir görünerek. Aynısı `make extract` sonrası da olur:
metin değişir, indeks eski metni aramaya devam eder.

## Karar

**1. İndeks depoya alındı.** `.gitignore`'dan çıkarıldı (32 MB).

**2. Binary olarak işaretlendi.** `.gitattributes`'a `*.npz binary` ve
`*.db binary` eklendi. Git binary'yi sezgisel tanır ve genelde doğru bilir, ama
`core.autocrlf=true` olan makinelerde yanlış bilirse dosyayı sessizce bozar. Bu
depoda satır sonu dönüşümü iki kez ölçülmüş zarar verdi (robots kanıtlarının
sha256'sı, 24 Ağu; `kod_parmak_izi`nin Windows/macOS ayrışması, 26 Ağu).

**3. İndeks kendi korpus izini taşıyor.** `vektor_db.korpus_izi(kayitlar)`,
indekse fiilen giren şeyin — kampanya kimliği + `paragraflara_ayir` çıktısı —
sha256 özetini üretir; `indeks_kur` bunu `.npz` içine yazar. `indeks_durumu()`
bugünkü korpusla karşılaştırır, `make durum` sonucu basar.

Korpus verilmezse bayatlık **denetlenmez ve öyle bildirilir** (`bayat=None`).
İzi olmayan eski indeks bayat sayılır — `depolama.cikarim_durumu` ile aynı
duruş: bilmemek, güncel varsaymak için gerekçe değildir.

## Bedeli

- Depoda 32 MB binary. `.npz` sıkıştırılmış olduğu için git delta yapamaz:
  indeks her yeniden kurulup commit edildiğinde geçmişe yeni bir 32 MB blob
  eklenir. **İndeksi her koşuda değil, korpus değiştiğinde commit edin.**
- Depoda zaten `data/katilim.db` (14 MB) takipliydi; ilke değişmiyor, tekrar
  ediyor.

## Sonuçları

- `data/vektor_indeksi.npz` takipli
- `.gitattributes` — `*.npz binary`, `*.db binary`
- `src/vektor_db.py` — `korpus_izi()` eklendi, `indeks_durumu()` bayatlık döner
- `src/boru_hatti.py` — `make durum` korpus izini ve bayatlığı basar
- `tests/test_vektor_db.py` — 14 → 21 test (sıra bağımsızlığı, silme, metin
  değişimi, denetlenmemiş durum)
- `docs/KURULUM.md` — USB'ye kopyalanacaklar dörtten **ikiye** indi
- `Makefile` `paket` hedefi aynı yönde güncellendi
- ADR 014'ün «çevrimdışı paket indeksi elle içermeli» uyarısı **kapandı**

### Açık kalan

⚠️ **Sorgu gömmesi hâlâ EVREN'e gidiyor** (ADR 014'ten devralındı). İndeks
yerelde ama sorunun vektörü çalışma anında üretiliyor. Tam hava boşluğu için
yerel `BAAI/bge-m3` (MIT) gerekir. Ağsız demoda chatbot sayısal sorulara cevap
vermeye devam eder, koşul soruları «erişilemiyor» der — ama artık indeks
eksikliği yüzünden değil.

⚠️ **Bayatlık uyarı verir, engellemez.** `make durum` söyler; `sor()` bayat
indeksle çalışmaya devam eder. Sert kapı (bayatsa cevap vermeme) bilinçli
olarak konmadı: demoda indeksi bir gün eski diye chatbot'u komple susturmak,
uyarmaktan kötüdür.
