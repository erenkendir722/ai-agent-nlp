# ADR 007 — DuckDB'ye geçilmedi, SQLite kalıyor

**Tarih:** 14 Ağustos 2026
**Durum:** Kabul edildi
**Sahip:** Eren
**İlgili:** [005 — Ajan mimarisi](005-ajan-mimarisi.md)

## Bağlam

Mentör görüşmesinde depolama katmanı sorgulandı ve DuckDB'ye geçilmesi
önerildi. Gerekçe olarak Docker ile SQLite karşılaştırıldı; bu karşılaştırma
kategori hatası içeriyor — **Docker paketleme aracı, SQLite depolama motoru;
biri diğerinin yerini tutmaz.** Yine de öneriyi kendi başına değerlendirdik.

v3 planı "DuckDB'ye geçin" diyor ve hemen ardından ekliyor:
*"Bu konuda tartışmayın. Puana etkisi sıfır."*

## Seçenekler

| Seçenek | Savunması | Maliyeti |
|---|---|---|
| JSONL + pandas | 500 kayıt için fazlasıyla yeterli | SQL sorgu kabiliyeti gider |
| DuckDB | "Veritabanı değil, analitik motor" | `depolama.py` yeniden yazımı, testler, Docker, arayüz sorguları |
| **SQLite (mevcut)** | Standart, tek dosya, sıfır yapılandırma | — |

## Karar

**Geçilmedi.** Gerekçe, önerinin kendi cümlesinde saklı: puana etkisi sıfırsa,
teslime 12 gün kala göç etmek net kayıptır. Kazanılan puan yok, harcanan
zaman gerçek, ve regresyon riski sıfır değil.

Asıl önemlisi: **itirazın karşılığı zaten mimaride var.** `depolama.py`
SQLAlchemy üzerine kurulu; "veritabanı bağımlılığı" eleştirisinin cevabı
şudur:

> `VERITABANI_URL` ortam değişkenini değiştirin, kod aynı kalır.
> PostgreSQL'e geçiş bir yapılandırma değişikliğidir.

Yani sorgulanan şey (tek bir veritabanına çakılı kalmak) zaten yaşanmıyor.
DuckDB'ye geçmek bu argümanı güçlendirmez, yalnız bir motoru başka bir
motorla değiştirir.

500 kayıt ölçeğinde üç seçenek de savunulabilir; seçim teknik değil,
retorik bir tercihti. Retorik ihtiyacını **göç ederek değil, bu ADR'yi
yazarak** karşılıyoruz.

## Sonuç

- `src/depolama.py` değişmedi: SQLite + SQLAlchemy.
- Mentöre verilecek cevap: *"Veritabanı motoru soyutlanmış durumda;
  `VERITABANI_URL` ile PostgreSQL veya başka bir motora geçiş yapılandırma
  işi. 500 kayıt ölçeğinde motor seçimi puanlanan bir kriter değil,
  bu yüzden kalan süreyi ölçüme ve dokümantasyona ayırdık."*
- Bu karar geri alınabilir: SQLAlchemy sayesinde göç, ihtiyaç doğarsa
  yarışma sonrasında da mümkün.
