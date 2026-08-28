# Bağımlılık ve Model Lisans Raporu

_Otomatik üretildi: 28.08.2026 09:45 · `make lisanslar`_

Şartname 5.10: *"Açık kaynaklı gözüküp, uygulama aşamasında lisans problemi çıkarma potansiyeli olan çözümler kullanılmamalıdır."*

## Sonuç

- Taranan paket: **101** (bunun **92** tanesi `requirements.txt` kapanışında)
- Taranan model: **4**
- Vendorlanan varlık: **2** (pip taramasının dışında)
- Kısıtlı/şüpheli lisans: **0**

## Depoya elle konmuş üçüncü taraf varlıklar

`pip-licenses` yalnız kurulu Python paketlerini görür. Depoya elle konan JS/CSS dosyaları taramanın dışında kalır; bu tablo o boşluğu kapatır.

| Dosya | Proje | Sürüm | Lisans | Not |
|---|---|---|---|---|
| `src/api/statik/swagger-ui-bundle.js` | [swagger-ui-dist](https://github.com/swagger-api/swagger-ui) | 5.17.14 | Apache-2.0 | `/docs` arayüzü. Sürüm PİNLİ: CDN'in `@5` etiketi zamanla kayar. |
| `src/api/statik/swagger-ui.css` | [swagger-ui-dist](https://github.com/swagger-api/swagger-ui) | 5.17.14 | Apache-2.0 | Aynı paketin stil dosyası. |

 **Tüm bağımlılıklar ve modeller izin verici (permissive) lisanslıdır.** Kısıtlı kullanım şartı olan hiçbir bileşen yoktur.

## Model lisansları

Modeller pip paketi değildir; yukarıdaki tarama onları görmez. Şartname
5.10'un asıl hedefi ise model lisanslarıdır — bu bölüm o yüzden var.

Lisanslar **2026-08-26** tarihinde Hugging Face depo üst verisinden çekilmiştir; ham yanıt: [`docs/kanit/model-lisanslari.json`](kanit/model-lisanslari.json). Modelin kendi beyanına ya da bizim hafızamıza dayanılmıyor.

| Kullanım | Nerede koşuyor | Hugging Face deposu | Lisans | Teyit |
|---|---|---|---|---|
| Çıkarım — varsayılan, ölçüm koşuları | EVREN `llm-large` | `Qwen/Qwen3.5-122B-A10B` | **apache-2.0** |  HF API · 2026-08-26 |
| Çıkarım — seçilebilir hızlı uç, **varsayılan değil** | EVREN `llm-fast` (`--model llm-fast`) | `Qwen/Qwen3.6-35B-A3B` | **apache-2.0** |  HF API · 2026-08-26 |
| Çıkarım — yerel yedek, hava boşluğu demosu | Ollama `qwen3.5:4b-q4_K_M` | `Qwen/Qwen3.5-4B` | **apache-2.0** |  HF API · 2026-08-26 |
| RAG gömme — **kullanılıyor** (`src/vektor_db.py`) | EVREN `bge-m3-embed` · yerel `BAAI/bge-m3` | `BAAI/bge-m3` | **mit** |  HF API · 2026-08-26 |

Notlar:

- `Qwen/Qwen3.5-122B-A10B` — MoE, 122B toplam / 10B aktif, BF16, 262.144 token bağlam.
- `Qwen/Qwen3.6-35B-A3B` — MoE. Ölçümde şema geçerliliği `llm-large`'ın altında kaldığı için varsayılan yapılmadı; bayrakla seçilebildiği sürece lisansı da teyitli olmalı.
- `Qwen/Qwen3.5-4B` — EVREN düştüğünde aynı kod yolu yerelde koşar (`LLM_SAGLAYICI=ollama`).
- `BAAI/bge-m3` — RAG gömme modeli. EVREN'de `bge-m3-embed` ucu **1024 boyut** veriyor — BGE-M3'ün bilinen boyutu; ada ek kimlik teyidi (ADR 013).

### EVREN uçları — hangisi kullanılıyor, hangisi neden kullanılmıyor

Çıkarım, T.C. Cumhurbaşkanlığı SSB'nin yarışmaya tahsis ettiği **EVREN**
servisinde koşuyor. Servis `GET /v1/models` ile on uç yayımlıyor; hepsi
takma addır, model kimliği döndürmez.

**Duruş (ADR 013):** EVREN yarışmayı düzenleyen kurumun yarışmacılara
tahsis ettiği servistir; sunduğu modeller lisans açısından uygun sayılır.
Buna yaslanmak zorunda değiliz — aşağıda işaretli, yani **fiilen
kullandığımız** uçların hepsinin lisansı bağımsız olarak teyitlidir.
Kalanlar lisans yüzünden değil, **bu senaryoda ihtiyaç olmadığı için**
kullanılmıyor.

| Uç | Model kimliği | Durum |
|---|---|---|
| `llm-large` | Qwen3.5-122B-A10B — Apache-2.0 |  kullanılıyor |
| `llm-fast` | Qwen3.6-35B-A3B — Apache-2.0 |  `--model llm-fast` ile seçilebilir; varsayılan değil, ölçüm koşuları `llm-large` ile yapıldı |
| `bge-m3-embed` | BGE-M3 — MIT; 1024 boyut ölçüldü (kimlik teyidi) |  kullanılıyor — RAG gömme |
| `bge-m3-sparse` · `bge-m3-colbert` | adı BGE-M3'ü işaret ediyor — MIT |  kullanılmıyor — ihtiyaç yok |
| `embed` | kimlik doğrulanmadı — 2560 boyut |  kullanılmıyor — lisanstan bağımsız olarak da uymuyor: 2560 boyut veriyor, `VECTOR_SIZE` 1024 |
| `rerank` | kimlik doğrulanmadı |  kullanılmıyor — bu senaryoda ihtiyaç yok |
| `router` | kimlik doğrulanmadı |  kullanılmıyor |
| `guard` | kimlik doğrulanmadı |  kullanılmıyor |
| `vlm` | kimlik doğrulanmadı |  kullanılmıyor — görsel girdi yok |

### Servis üzerinden kullanmak lisans durumunu değiştirir mi?

Hayır — üç sebeple, üçü de teslimde sorulabilir:

1. **Depoda model ağırlığı yok.** Apache-2.0 bir dağıtım lisansıdır;
   biz ağırlık dağıtmıyoruz, servisi HTTP ile çağırıyoruz. Yeniden
   dağıtım yükümlülüğü doğmuyor.
2. **Modelin kendisi Apache-2.0 olduğu için kurum kendi sunucusunda da
   koşturabilir.** Şartname 5.10'un derdi "uygulama aşamasında lisans
   problemi çıkarma potansiyeli"dir; Apache-2.0 bir model bu potansiyeli
   taşımaz. Kısıtlı lisanslı bir model olsaydı servis üzerinden çağırmak
   sorunu çözmezdi — kurum içine taşındığı gün patlardı.
3. **Servise kilitlenme yok, ölçülmüş durumda.** `LLM_SAGLAYICI=ollama`
   ile aynı kod yolu yerel modelle koşuyor (`make extract-yerel`); hava
   boşluğu demosu bunu 18 Ağustos'ta doğruladı. EVREN'in kullanım
   şartları bir **hizmet** sözleşmesidir, yazılım lisansı değil; projenin
   açık kaynak durumunu etkilemez.

### Bilinçli olarak KULLANILMAYAN modeller

| Model ailesi | Lisans | Neden kullanılmadı |
|---|---|---|
| Llama 3.x/4, Turkish-Llama | Llama Community License | Kullanıcı sayısı eşiği, adlandırma ve kullanım kısıtları içerir. "Açık gibi görünen ama kısıtlı" tanımına birebir uyar — şartname 5.10'un hedefi budur. |
| Gemma, Türkçe-Gemma, EmbeddingGemma | Gemma Terms of Use | Kullanım kısıtlaması ve geri çağırma hükmü içerir. Aynı gerekçe. **Gömme modeli seçilirken asıl tuzak budur:** EmbeddingGemma teknik olarak uygun görünür, lisansı uygun değildir. |

## Elle incelenen lisanslar

### `python-dateutil` — Dual License (Apache-2.0 VEYA BSD-3-Clause)

Üst veride yalnızca "Dual License" yazdığı için otomatik tarama sınıflandıramıyor. Proje `LICENSE` dosyasında Apache-2.0 ve BSD-3-Clause olarak çift lisanslıdır; **Apache-2.0 seçilmiştir** ve projemizin lisansıyla aynıdır. Kısıt doğurmaz.

### `pypdfium2` — (Apache-2.0 OR BSD-3-Clause) AND LicenseRef-PdfiumThirdParty

Bileşik ifade: sarmalayıcı kod seçmeli (Apache-2.0 **seçilmiştir**), gömülü PDFium ikilisi ise kendi üçüncü taraf bildirimlerini taşır — hepsi izin verici (BSD/MIT/zlib türevleri, Chromium'un PDF motoru). Yalnız `make sunum-pptx` kullanır: PDF sayfasını görüntüye çevirir. Yaygın alternatif `PyMuPDF` **AGPL-3.0**'dır ve Apache-2.0 lisanslı bir teslimatın bağımlılık ağacına giremezdi; seçim lisans gerekçesiyle yapıldı.

### `tld` — MPL-1.1 OR GPL-2.0-only OR LGPL-2.1-or-later

Üçlü seçmeli (disjunctive) lisans. **MPL-1.1 seçilmiştir.** Seçmeli lisanslarda kullanıcı bir seçeneği seçer; MPL-1.1 dosya bazlı copyleft olup kütüphane olarak kullanımda projeyi etkilemez. `trafilatura`'nın dolaylı bağımlılığıdır, kodumuz doğrudan çağırmaz.

## Tam liste

Sanal ortamda kurulu **101** paketin **92** tanesi
`requirements.txt`'ten (doğrudan ya da geçişli olarak) gelir; kalanlar ortamda
kalmış, teslim edilen koda dahil olmayan paketlerdir. Ayrımı yazmak gerekiyor:
`pip install -r requirements.txt` ile kurulan temiz bir ortamda **ortam**
kapsamlı satırlar bulunmaz.

> Ortam kapsamlı paketler: `grpcio`, `grpcio-tools`, `h2`, `hpack`, `hyperframe`, `pip`, `portalocker`, `qdrant-client`, `setuptools`. Ortamda durmaları onları bağımlılık yapmaz. `qdrant-client` **artık kullanılmıyor** — harici vektör veritabanı yolu bırakıldı (ADR 014), `requirements.txt`'ten çıkarıldı; sanal ortamda kalıntı olarak duruyor. Çıkarım yolu EVREN'e düz `httpx` ile gider (`src/extraction/saglayici.py`); `openai` istemcisi yalnız gömme ucu için kullanılır (`src/vektor_db.py`) ve `requirements.txt`'te yazılıdır.

| Paket | Sürüm | Lisans | Kapsam |
|---|---|---|---|
| `altair` | 5.5.0 | OSI Approved :: BSD License | proje |
| `annotated-types` | 0.8.0 | MIT | proje |
| `anyio` | 4.14.2 | MIT | proje |
| `attrs` | 26.1.0 | MIT | proje |
| `babel` | 2.18.0 | BSD-3-Clause | proje |
| `blinker` | 1.9.0 | OSI Approved :: MIT License | proje |
| `cachetools` | 5.5.2 | MIT | proje |
| `certifi` | 2026.7.22 | MPL-2.0 | proje |
| `charset-normalizer` | 3.4.9 | MIT | proje |
| `click` | 8.4.2 | BSD-3-Clause | proje |
| `courlan` | 1.4.0 | Apache-2.0 | proje |
| `dateparser` | 1.4.2 | BSD-3-Clause | proje |
| `distro` | 1.9.0 | Apache License, Version 2.0 | proje |
| `fastapi` | 0.115.5 | OSI Approved :: MIT License | proje |
| `gitdb` | 4.0.12 | BSD License | proje |
| `GitPython` | 3.1.58 | BSD-3-Clause | proje |
| `grpcio` | 1.83.0 | Apache-2.0 | ortam |
| `grpcio-tools` | 1.71.2 | Apache License 2.0 | ortam |
| `h11` | 0.16.0 | MIT | proje |
| `h2` | 4.4.1 | MIT | ortam |
| `hpack` | 4.2.0 | MIT | ortam |
| `htmldate` | 1.10.0 | Apache-2.0 | proje |
| `httpcore` | 1.0.9 | BSD-3-Clause | proje |
| `httpx` | 0.27.2 | BSD-3-Clause | proje |
| `hyperframe` | 6.1.0 | OSI Approved :: MIT License | ortam |
| `idna` | 3.18 | BSD-3-Clause | proje |
| `iniconfig` | 2.3.0 | MIT | proje |
| `Jinja2` | 3.1.6 | OSI Approved :: BSD License | proje |
| `jiter` | 0.16.0 | MIT | proje |
| `jsonschema` | 4.26.0 | MIT | proje |
| `jsonschema-specifications` | 2025.9.1 | MIT | proje |
| `jusText` | 3.0.2 | The BSD 2-Clause License | proje |
| `lxml` | 6.1.1 | BSD-3-Clause | proje |
| `lxml_html_clean` | 0.4.5 | BSD-3-Clause | proje |
| `markdown-it-py` | 4.2.0 | OSI Approved :: MIT License | proje |
| `MarkupSafe` | 3.0.3 | BSD-3-Clause | proje |
| `mdurl` | 0.1.2 | OSI Approved :: MIT License | proje |
| `narwhals` | 2.24.0 | MIT | proje |
| `numpy` | 2.1.3 | OSI Approved :: BSD License | proje |
| `ollama` | 0.6.2 | MIT | proje |
| `openai` | 1.55.0 | Apache-2.0 | proje |
| `outcome` | 1.3.0.post0 | MIT OR Apache-2.0 | proje |
| `packaging` | 24.2 | OSI Approved :: Apache Software License / OSI Approved :: BSD License | proje |
| `pandas` | 2.2.3 | OSI Approved :: BSD License | proje |
| `pillow` | 11.3.0 | MIT-CMU | proje |
| `pip` | 26.2.1 | MIT | ortam |
| `pip-licenses` | 5.0.0 | MIT | proje |
| `plotly` | 5.24.1 | MIT | proje |
| `pluggy` | 1.6.0 | MIT | proje |
| `portalocker` | 2.10.1 | BSD-3-Clause | ortam |
| `prettytable` | 3.18.0 | BSD-3-Clause | proje |
| `protobuf` | 5.29.6 | 3-Clause BSD License | proje |
| `pyarrow` | 25.0.0 | Apache-2.0 | proje |
| `pydantic` | 2.9.2 | MIT | proje |
| `pydantic_core` | 2.23.4 | MIT | proje |
| `pydeck` | 0.9.3 | Apache License 2.0 | proje |
| `Pygments` | 2.20.0 | BSD-2-Clause | proje |
| `pypdfium2` | 4.30.0 | (Apache-2.0 OR BSD-3-Clause) AND LicenseRef-PdfiumThirdParty | proje |
| `PySocks` | 1.7.1 | BSD | proje |
| `pytest` | 8.3.3 | MIT | proje |
| `python-dateutil` | 2.9.0.post0 | Dual License | proje |
| `python-dotenv` | 1.0.1 | BSD-3-Clause | proje |
| `python-pptx` | 1.0.2 | MIT | proje |
| `pytz` | 2026.3.post1 | MIT | proje |
| `PyYAML` | 6.0.2 | MIT | proje |
| `qdrant-client` | 1.12.1 | Apache-2.0 | ortam |
| `referencing` | 0.37.0 | MIT | proje |
| `regex` | 2026.7.19 | Apache-2.0 AND CNRI-Python | proje |
| `requests` | 2.34.2 | Apache-2.0 | proje |
| `rich` | 13.9.4 | MIT | proje |
| `rpds-py` | 2026.6.3 | MIT | proje |
| `ruff` | 0.7.4 | MIT | proje |
| `selectolax` | 0.3.27 | MIT license | proje |
| `selenium` | 4.27.1 | Apache 2.0 | proje |
| `setuptools` | 84.0.0 | MIT | ortam |
| `six` | 1.17.0 | MIT | proje |
| `smmap` | 5.0.3 | BSD-3-Clause | proje |
| `sniffio` | 1.3.1 | MIT OR Apache-2.0 | proje |
| `sortedcontainers` | 2.4.0 | Apache 2.0 | proje |
| `SQLAlchemy` | 2.0.36 | MIT | proje |
| `starlette` | 0.41.3 | BSD-3-Clause | proje |
| `streamlit` | 1.40.1 | Apache License 2.0 | proje |
| `tenacity` | 9.1.4 | Apache 2.0 | proje |
| `tld` | 0.13.2 | MPL-1.1 OR GPL-2.0-only OR LGPL-2.1-or-later | proje |
| `toml` | 0.10.2 | MIT | proje |
| `tomli` | 2.4.1 | MIT | proje |
| `tornado` | 6.5.8 | Apache-2.0 | proje |
| `tqdm` | 4.70.0 | MPL-2.0 AND MIT | proje |
| `trafilatura` | 1.12.2 | Apache-2.0 | proje |
| `trio` | 0.34.0 | MIT OR Apache-2.0 | proje |
| `trio-websocket` | 0.12.2 | OSI Approved :: MIT License | proje |
| `typing_extensions` | 4.16.0 | PSF-2.0 | proje |
| `tzdata` | 2026.3 | Apache-2.0 | proje |
| `tzlocal` | 5.4.4 | MIT | proje |
| `urllib3` | 2.7.0 | MIT | proje |
| `uvicorn` | 0.32.1 | BSD-3-Clause | proje |
| `wcwidth` | 0.8.2 | MIT | proje |
| `webdriver-manager` | 4.0.2 | OSI Approved :: Apache Software License | proje |
| `websocket-client` | 1.9.0 | Apache-2.0 | proje |
| `wsproto` | 1.3.2 | MIT | proje |
| `xlsxwriter` | 3.2.9 | BSD-2-Clause | proje |

---

_Not: Lisans bilgisi PEP 639 `License-Expression` alanından, yoksa eski `License` alanından, o da yoksa sınıflandırıcılardan okunur. `pip-licenses` tek başına modern alanı okumadığı için 23 paketi "UNKNOWN" gösteriyordu; bu rapor her iki kaynağa da bakar._