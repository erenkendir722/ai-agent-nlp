# Demo senaryosu — 5 dakikalık video · 1 dakikalık kesit · canlı demo

Şartname madde 6 **5 dakikalık** bir demo videosu, madde 10 sunum sırasında
oynatılacak **1 dakikalık** bir video istiyor. İkisi ayrı teslimattır
(ES-17 · ES-18); bu dosya ikisinin de çekim planı ve jüri önünde yapılacak
canlı demonun sırasıdır.

**Kural:** ekranda görünen her sayı depodan gelir. Demo için veri hazırlanmaz,
sayı yuvarlanmaz, ekran «temizlenmez». Bir alan boşsa boş gösterilir — sistemin
iddiası zaten «bilmediğini söyler» olduğu için, boş alan demoyu **güçlendirir**.

---

## 0. Çekimden önce — 10 dakikalık hazırlık

```bash
make durum          # 921 kampanya · 9 banka · RAG indeksi «güncel» demeli
make test           # yeşil olmalı; kırmızıysa çekime başlama
GOMME_SAGLAYICI=ollama .venv/bin/python -c "import src.vektor_db as v; v.gom('x')"
                    # yerel gömme yolu bir kez sınanır (aşağıda «kurtarma»)
make run            # arayüz
```

| Kontrol | Neden |
|---|---|
| Ekran **1280×720**, tarayıcı tam ekran, yakınlaştırma %100 | Video sıkıştırması küçük yazıyı okunmaz yapıyor |
| Bildirimler kapalı, ikinci ekran kapalı | Bir e-posta bildirimi 5 dakikalık çekimi baştan aldırır |
| `make extract` KOŞMUYOR olmalı | 8 GB makinede arayüzle aynı anda koşarsa arayüz donuyor (KURULUM.md ölçümü) |
| Sohbet geçmişi temiz («Yeni sohbet») | Önceki turdan devralınan yuva, cevabı değiştirir (ADR 022) |

---

## 1. Beş dakikalık demo videosu (ES-17 · madde 6)

Madde 6 videodan **kullanıcı arayüzünü ve işleyişi** göstermesini istiyor;
mimari anlatımı değil. Sıra, sistemin iddiasını en hızlı kanıtlayan sıradır:
önce veri, sonra karar, sonra dürüstlük.

| Süre | Ekran | Ne yapılır | Söylenecek tek cümle |
|---|---|---|---|
| 0:00–0:25 | **Genel Bakış** | Kapsam kartları, banka dağılımı, son çekim tarihi | «Dokuz faal katılım bankasının tamamı, 921 kampanya — hepsi kaynağıyla birlikte.» |
| 0:25–1:15 | **Müşteri Profili** | Maaş müşterisi · 800.000 TL · 120 ay → sırala | «Sıralama manşet orana göre değil, toplam maliyete göre.» |
| 1:15–1:40 | aynı ekran | Bir kalemi aç: kâr payı, vade, tahsis ücreti ve **kaynak alıntısı** | «Her değerin altında geldiği cümle ve adresi var.» |
| 1:40–2:20 | **Karşılaştırma** | İki bankayı seç, ağırlıkları oynat, sıralamanın değiştiğini göster | «Ağırlık bizim değil kullanıcının; formül açık.» |
| 2:20–3:10 | **Kampanya Asistanı** | «Kuveyt Türk'ün konut finansmanı oranı ne?» | «Oran yayımlanmamış — sistem *Belirtilmemiş* diyor, ama bildiği vadeyi ve ücreti saklamıyor.» |
| 3:10–3:35 | aynı ekran | **«Kampanya koşulları neler?»** (kalkan örneği) | «Denetlenemeyen sayı içeren cevabı sistem kendi kesiyor.» |
| 3:35–4:20 | **Metin Analizi** | Şartname madde 11 metnini düğmeyle yükle → **Çıkar** | «Bu metni sistem daha önce görmedi; alan, değer, birim, güven, yöntem ve alıntı.» |
| 4:20–4:50 | **Canlı Boru Hattı** | Demo kipinde tek banka topla, olay akışını göster | «Veriyi biz topluyoruz; nezaket kuralı ve robots kapısı demoda da açık.» |
| 4:50–5:00 | **Genel Bakış** | Kapanış karesi | «Kaynağı olmayan sayı üretmeyen bir sistem.» |

**Çekim notları**

- Fare imlecini konuşulan yere götür, ama tıklamadan önce **yarım saniye
  beklet** — video sıkıştırması ani hareketi bulanıklaştırıyor.
- Chatbot cevabı 2–4 saniyede geliyor; bekleme kesilmez. Kesilirse jüri
  «hızlandırılmış mı?» diye sorar, kaybedilen güven kazanılan saniyeden pahalı.
- Boru hattı sekmesinde **üretim onay kutusuna dokunma** — demo `data/demo/`
  altına yazar, üretim veritabanı çekim sırasında değişmemeli.

---

## 2. Bir dakikalık sunum videosu (ES-18 · madde 10)

Beş dakikalıktan **kesilerek** çıkarılır, ayrı çekilmez: aynı ekranın iki farklı
sürümü olması, jüri ikisini yan yana gördüğünde açıklanması gereken bir fark
yaratır.

| Süre | Kaynak | Neden bu parça |
|---|---|---|
| 0:00–0:20 | Müşteri Profili — sıralama | Ürünün ne işe yaradığı tek karede anlaşılıyor |
| 0:20–0:40 | Asistan — «Belirtilmemiş» cevabı | Projenin en özgün iddiası |
| 0:40–0:55 | Metin Analizi — madde 11 metni | Şartnamenin kendi örneğiyle çalıştığı görülüyor |
| 0:55–1:00 | Genel Bakış kapanış karesi | Kapanış cümlesi sunumcuda, videoda ses yok |

Sunum 4 dakika, video 1 dakika (madde 10). **Video sesli oynatılmaz** —
konuşan sunumcudur; ses üst üste binerse ikisi de anlaşılmaz.

---

## 3. Jüri önünde canlı demo (soru-cevap sırasında)

Canlı demo istenirse sıra kısalır — üç ekran, en fazla 90 saniye:

1. **Müşteri Profili** — jürinin verdiği tutar/vade ile sırala.
2. **Asistan** — jürinin kendi sorusunu yaz.
3. **Metin Analizi** — jüri kendi metnini yapıştırsın (madde 11 düğmesi de var).

### Kurtarma planı — bir şey çalışmazsa

| Belirti | Sebep | Yapılacak |
|---|---|---|
| Asistan «Metin araması şu anda erişilemiyor» diyor | EVREN gömme ucu düşmüş (28 Ağu'da yaşandı) | `GOMME_SAGLAYICI=ollama` ile yeniden başlat — indeks zaten depoda, yerel `bge-m3` aynı model |
| Sayfa donuyor | Aynı anda `make extract` koşuyor | Çıkarımı durdur; ölçüm sonuçları zaten `docs/SONUCLAR.md`'de |
| İnternet yok | — | Demo internetsiz koşar: veri, indeks ve model yerelde. Yalnız `make crawl` ağ ister |
| Bir ekran hata veriyor | — | Ekranı kapatma, **`docs/SONUCLAR.md` ve depoyu göster.** Ölçüm dosyaları demonun yedeğidir |

> Demoyu kurtarmanın en kötü yolu, çalışmayan şeyi çalışıyormuş gibi anlatmaktır.
> Bu projenin tek iddiası dürüstlük; demo hatası anlatılabilir, gizlenmiş hata
> anlatılamaz.

---

**İlgili:** [`KONUSMA_METNI.md`](KONUSMA_METNI.md) (4 dakikalık sunum metni) ·
[`README.md`](README.md) (slayt kaynakları) ·
[`../KULLANIM_KILAVUZU.md`](../KULLANIM_KILAVUZU.md) (ekranların ayrıntısı) ·
[`../JURI_PROVASI.md`](../JURI_PROVASI.md) (soru-cevap)
