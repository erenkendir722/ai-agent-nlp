# Sunum — Svartal_Sunum.pdf

9 sayfa, 16:9 (960×540 pt — jüriye gönderilen örnek dosyayla aynı ölçü).
Kaynak `sunum.html` + `stil.css`; PDF ondan üretilir, elle düzenlenmez.

```bash
make sunum          # sunum.html -> Svartal_Sunum.pdf
```

Font **Carlito** (SIL Open Font License) `fontlar/` içinde gömülü durur;
makinede kurulu olmasına gerek yok. Renkler `stil.css` başındaki değişkenlerden
gelir: mürekkep `#15141A`, krem `#F5F4F0`, turuncu `#E85D2A`, turkuaz `#2AA3AE`.

Chrome başka bir yerdeyse: `make sunum KROM="/yol/chrome"`.

## Sayfa düzeni ve konuşan

| # | Sayfa | Konuşan |
|---|---|---|
| 01 | Kapak | — |
| 02 | Problem | Eren |
| 03 | Çözüm, mimari ve teknoloji seçimleri | Eren |
| 04 | **Ajan mimarisi ve eleştirmen** | Eren |
| 05 | Kanıt zinciri — gerçek bir kayıt | Samet |
| 06 | Hibrit çıkarım — nasıl çalışıyor | Samet |
| 07 | Ölçüm ve ablasyon | Samet |
| 08 | Asistan, kalkan ve karşılaştırma | Eren · Esra |
| 09 | Kurum içi çalışabilirlik, ekip ve kapanış | Eren · Esra |

## Sayıların kaynağı

Slayttaki her sayı depodan geliyor; hiçbiri elle yazılmadı.

| Sayı | Nereden |
|---|---|
| 96 kampanya · 8 banka · 306 dolu alan · 3 kanıt ihlali (%0,98) | `eval.calistir.temel_metrikler`, `data/katilim.db` |
| Ablasyon tablosu (0,69 / 0,21 / 0,78) | `data/ablasyon.json` — tek koşu, tek kod parmak izi |
| Makro-F1 %95 GA 0,65–0,85 | `docs/SONUCLAR.md` (400 kez önyükleme) |
| 369 varyant · %100 biçim · uydurdu 0 | `docs/DAYANIKLILIK.md` |
| 187 görülmemiş sayfa · 0/0/0 | `docs/GORULMEMIS_METIN.md` |
| Kalkan parça sayıları · yanlış blok 0/35 | `docs/SONUCLAR.md`, `eval/sorular.yaml` |
| 573 test | `pytest tests/` |
| 77 paket · 0 kısıtlı lisans | `docs/LISANSLAR.md` |
| 10 faal banka · 15 kayıt | `data/banks.yaml` |
| Türkiye Finans örnek kaydı (sayfa 04) | `data/katilim.db`, `tam_kayit` JSON'u |
| Toplam maliyet tuzağı (2.033.129 / 2.028.925 TL) | `src.comparison.karsilastirma.toplam_maliyet` |
| Hava boşluğu: 19,1 sn · 24,4 sn | `docs/KURULUM.md` — «Doğrulanmış çalıştırma» |
| Ajan izi (sayfa 04) | `Orkestrator.calistir()` canlı koşumu — `IzDefteri` çıktısı |
| `uygunluk` 96/96 boş · 72 ajan testi | `data/katilim.db`, `pytest tests/test_{muhakeme,orkestrator,elestirmen}.py` |

**Sayı değişirse:** önce ilgili ölçümü yeniden koş, sonra `sunum.html` içindeki
karşılığını güncelle ve `make sunum` ile PDF'i yeniden üret. Bayat sayı, jüri
depoya baktığında en pahalı hatadır.

## Mentör sorularının karşılığı

`Plan_Guncellemeleri_v3.md` içindeki geri bildirimlerin sunumdaki yeri:

| Mentörün dediği | Sunumda |
|---|---|
| *"Yarışmanın adı Dil AJANLARI"* | 04 — beş ajan, canlı ajan izi, ajan tuzağı |
| *"Regex ile bu değerler yakalanamaz"* | 07 — ablasyon; kural sayısalda 0,84, LLM 0,00 |
| *"Qwen 3.7 kullanın"* | 03 — kapalı ağırlıklı, 5.9/5.10/8 ihlali |
| RAG ile determinizmin karıştırılması | 08 — «dayanaklandırma determinizm değildir» |
| *"SQLite yerine DuckDB"* | 03 — geçilmedi, ADR 007 |
| *"Şemaya uygunluk koşulları ekleyin"* | 04 — `UygunlukKosullari` var, çıkarımı bağlanmadı |
| Manşet oran tuzağı | 02 — kendi motorumuzun hesabı |
| Jüri: *"kendi test verimizi verebiliriz"* | 07 — 187 görülmemiş sayfa |

**Hâlâ karşılıksız:** MoE / donanım profilleri (ölçüm yok, S-01 açık) ·
yeni ablasyon tablosu (ajan var / eleştirmen yok / tam hiyerarşi — A-09 koşulmadı) ·
çelişki tespiti (kural↔LLM çelişkisi kayda yazılmıyor, sayfa-içi çelişki hiç yok).
Bunlar ölçülürse sunuma girer; ölçülmeden girmez.
