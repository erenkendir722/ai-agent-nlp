# Veri Kartı — SVARTAL Katılım Bankacılığı Kampanya Veri Seti

_Otomatik üretildi: 26.08.2026 · `make veri-seti`_

Türkiye'de faaliyet gösteren **katılım bankalarının** herkese açık kampanya
sayfalarından toplanmış, yapısal alanlara çıkarılmış kampanya kayıtları.
TEKNOFEST 2026 Yapay Zekâ Dil Ajanları Yarışması 2. Senaryo için üretildi.

## Özet

| | |
|---|---|
| Kayıt sayısı | **931** |
| Banka sayısı | **9** |
| Şema sürümü | `1.2.0` |
| Alan sayısı (kayıt başına) | 16 yapısal alan + uygunluk koşulları |
| Dolu hücre | 3752 / 14896 |
| Dil | Türkçe |
| Lisans | Apache-2.0 (kod ve derleme) · kaynak metinler ilgili bankalara aittir |

## Dosyalar

| Dosya | Kim için | İçerik |
|---|---|---|
| `svartal_kampanyalar.csv` | insan | Düz tablo: her alan + hangi katmandan geldiği + güven skoru |
| `svartal_kampanyalar.jsonl` | makine | Kanıt zinciri: değer + birim + ham ifade + **kaynak alıntısı** |

## Banka dağılımı

| Banka | Kayıt |
|---|---|
| Kuveyt Türk Katılım Bankası A.Ş. | 190 |
| Türkiye Finans Katılım Bankası A.Ş. | 172 |
| Ziraat Katılım Bankası A.Ş. | 162 |
| Albaraka Türk Katılım Bankası A.Ş. | 126 |
| T.O.M. Katılım Bankası A.Ş. | 97 |
| Türkiye Emlak Katılım Bankası A.Ş. | 78 |
| Dünya Katılım Bankası A.Ş. | 54 |
| Vakıf Katılım Bankası A.Ş. | 36 |
| Hayat Finans Katılım Bankası A.Ş. | 16 |

## Kampanya türü dağılımı

| Tür | Kayıt |
|---|---|
| `diger` | 416 |
| `kart` | 194 |
| `alisveris_puani` | 108 |
| `yatirim_urunu` | 46 |
| `tasit_finansmani` | 46 |
| `finansman` | 43 |
| `ihtiyac_finansmani` | 41 |
| `konut_finansmani` | 29 |
| `yeni_musteri` | 8 |

## Nasıl toplandı

- Yalnız **herkese açık** kampanya sayfaları; giriş gerektiren hiçbir sayfa yok.
- Her alan adresi için `robots.txt` çekilmeden önce kontrol edildi ve karar
  günlüğe yazıldı: [`docs/kanit/ROBOTS_KONTROL_GUNLUGU.md`](../../docs/kanit/ROBOTS_KONTROL_GUNLUGU.md).
  *(robots.txt: bir sitenin, otomatik programlara hangi sayfaları çekmelerinin
  uygun olduğunu bildirdiği metin dosyası.)*
- Kişisel veri taraması yapıldı, kimliği belirli gerçek kişiye ait veri
  bulunmadı: [`docs/kanit/KVKK_TARAMASI.md`](../../docs/kanit/KVKK_TARAMASI.md).
- Yöntem: [`docs/VERI_METODOLOJISI.md`](../../docs/VERI_METODOLOJISI.md).

## Bilinen sınırlar

- **Anlık görüntüdür.** Kampanyalar süreli; `cekim_tarihi` her kayıtta durur.
- **Alan doluluğu türe göre değişir.** Kart kampanyalarında kâr payı oranı
  yoktur; boş hücre eksik veri değil, o kampanyada olmayan bilgidir.
- **Dengesiz dağılım.** Bankaların sayfa sayısı farklı; karşılaştırma yaparken
  kapsam raporuna bakın: [`docs/KAPSAM_RAPORU.md`](../../docs/KAPSAM_RAPORU.md).
- **Değerler modelden gelebilir.** Her hücre `__yontem` sütununda hangi
  katmandan geldiğini (`kural` / `llm` / `hibrit`) beyan eder; `guven`
  sütunu 0–1 arasıdır. Ölçüm sonuçları: [`docs/SONUCLAR.md`](../../docs/SONUCLAR.md).

## Atıf

> Takım SVARTAL (2026). *SVARTAL Katılım Bankacılığı Kampanya Veri Seti.*
> TEKNOFEST 2026 Yapay Zekâ Dil Ajanları Yarışması.
> https://github.com/erenkendir722/ai-agent-nlp
