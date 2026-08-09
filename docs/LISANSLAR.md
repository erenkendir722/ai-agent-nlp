# Bağımlılık Lisans Raporu

_Otomatik üretildi: 09.08.2026 18:10 · `make lisanslar`_

Şartname 5.10: *"Açık kaynaklı gözüküp, uygulama aşamasında lisans problemi çıkarma potansiyeli olan çözümler kullanılmamalıdır."*

## Sonuç

- Taranan paket: **77**
- Kısıtlı/şüpheli lisans: **0**

✅ **Tüm bağımlılıklar izin verici (permissive) lisanslıdır.** Kısıtlı kullanım şartı olan hiçbir bileşen yoktur.

## Model lisansları

| Model | Lisans | Kullanım |
|---|---|---|
| Qwen3.5 (2B/4B/9B/27B) | **Apache 2.0** | Çıkarım ve chatbot |
| Qwen3.6-27B | **Apache 2.0** | Final ölçüm koşusu |

### Bilinçli olarak KULLANILMAYAN modeller

| Model ailesi | Lisans | Neden kullanılmadı |
|---|---|---|
| Llama 3.x/4, Turkish-Llama | Llama Community License | Kullanıcı sayısı eşiği, adlandırma ve kullanım kısıtları içerir. "Açık gibi görünen ama kısıtlı" tanımına birebir uyar — şartname 5.10'un hedefi budur. |
| Gemma, Türkçe-Gemma, EmbeddingGemma | Gemma Terms of Use | Kullanım kısıtlaması ve geri çağırma hükmü içerir. Aynı gerekçe. |

## Elle incelenen lisanslar

### `python-dateutil` — Dual License (Apache-2.0 VEYA BSD-3-Clause)

Üst veride yalnızca "Dual License" yazdığı için otomatik tarama sınıflandıramıyor. Proje `LICENSE` dosyasında Apache-2.0 ve BSD-3-Clause olarak çift lisanslıdır; **Apache-2.0 seçilmiştir** ve projemizin lisansıyla aynıdır. Kısıt doğurmaz.

### `tld` — MPL-1.1 OR GPL-2.0-only OR LGPL-2.1-or-later

Üçlü seçmeli (disjunctive) lisans. **MPL-1.1 seçilmiştir.** Seçmeli lisanslarda kullanıcı bir seçeneği seçer; MPL-1.1 dosya bazlı copyleft olup kütüphane olarak kullanımda projeyi etkilemez. `trafilatura`'nın dolaylı bağımlılığıdır, kodumuz doğrudan çağırmaz.

## Tam liste

| Paket | Sürüm | Lisans |
|---|---|---|
| `altair` | 5.5.0 | OSI Approved :: BSD License |
| `annotated-types` | 0.8.0 | MIT |
| `anyio` | 4.14.2 | MIT |
| `attrs` | 26.1.0 | MIT |
| `babel` | 2.18.0 | BSD-3-Clause |
| `blinker` | 1.9.0 | OSI Approved :: MIT License |
| `cachetools` | 5.5.2 | MIT |
| `certifi` | 2026.7.22 | MPL-2.0 |
| `charset-normalizer` | 3.4.9 | MIT |
| `click` | 8.4.2 | BSD-3-Clause |
| `courlan` | 1.4.0 | Apache-2.0 |
| `dateparser` | 1.4.2 | BSD-3-Clause |
| `fastapi` | 0.115.5 | OSI Approved :: MIT License |
| `gitdb` | 4.0.12 | BSD License |
| `GitPython` | 3.1.58 | BSD-3-Clause |
| `h11` | 0.16.0 | MIT |
| `htmldate` | 1.10.0 | Apache-2.0 |
| `httpcore` | 1.0.9 | BSD-3-Clause |
| `httpx` | 0.27.2 | BSD-3-Clause |
| `idna` | 3.18 | BSD-3-Clause |
| `iniconfig` | 2.3.0 | MIT |
| `Jinja2` | 3.1.6 | OSI Approved :: BSD License |
| `jsonschema` | 4.26.0 | MIT |
| `jsonschema-specifications` | 2025.9.1 | MIT |
| `jusText` | 3.0.2 | The BSD 2-Clause License |
| `lxml` | 6.1.1 | BSD-3-Clause |
| `lxml_html_clean` | 0.4.5 | BSD-3-Clause |
| `markdown-it-py` | 4.2.0 | OSI Approved :: MIT License |
| `MarkupSafe` | 3.0.3 | BSD-3-Clause |
| `mdurl` | 0.1.2 | OSI Approved :: MIT License |
| `narwhals` | 2.24.0 | MIT |
| `numpy` | 2.1.3 | OSI Approved :: BSD License |
| `ollama` | 0.6.2 | MIT |
| `packaging` | 24.2 | OSI Approved :: Apache Software License / OSI Approved :: BSD License |
| `pandas` | 2.2.3 | OSI Approved :: BSD License |
| `pillow` | 11.3.0 | MIT-CMU |
| `pip` | 26.2.1 | MIT |
| `pip-licenses` | 5.0.0 | MIT |
| `plotly` | 5.24.1 | MIT |
| `pluggy` | 1.6.0 | MIT |
| `prettytable` | 3.18.0 | BSD-3-Clause |
| `protobuf` | 5.29.6 | 3-Clause BSD License |
| `pyarrow` | 25.0.0 | Apache-2.0 |
| `pydantic` | 2.9.2 | MIT |
| `pydantic_core` | 2.23.4 | MIT |
| `pydeck` | 0.9.3 | Apache License 2.0 |
| `Pygments` | 2.20.0 | BSD-2-Clause |
| `pytest` | 8.3.3 | MIT |
| `python-dateutil` | 2.9.0.post0 | Dual License |
| `python-dotenv` | 1.0.1 | BSD-3-Clause |
| `pytz` | 2026.3.post1 | MIT |
| `PyYAML` | 6.0.2 | MIT |
| `referencing` | 0.37.0 | MIT |
| `regex` | 2026.7.19 | Apache-2.0 AND CNRI-Python |
| `requests` | 2.34.2 | Apache-2.0 |
| `rich` | 13.9.4 | MIT |
| `rpds-py` | 2026.6.3 | MIT |
| `ruff` | 0.7.4 | MIT |
| `selectolax` | 0.3.27 | MIT license |
| `six` | 1.17.0 | MIT |
| `smmap` | 5.0.3 | BSD-3-Clause |
| `sniffio` | 1.3.1 | MIT OR Apache-2.0 |
| `SQLAlchemy` | 2.0.36 | MIT |
| `starlette` | 0.41.3 | BSD-3-Clause |
| `streamlit` | 1.40.1 | Apache License 2.0 |
| `tenacity` | 9.1.4 | Apache 2.0 |
| `tld` | 0.13.2 | MPL-1.1 OR GPL-2.0-only OR LGPL-2.1-or-later |
| `toml` | 0.10.2 | MIT |
| `tomli` | 2.4.1 | MIT |
| `tornado` | 6.5.8 | Apache-2.0 |
| `trafilatura` | 1.12.2 | Apache-2.0 |
| `typing_extensions` | 4.16.0 | PSF-2.0 |
| `tzdata` | 2026.3 | Apache-2.0 |
| `tzlocal` | 5.4.4 | MIT |
| `urllib3` | 2.7.0 | MIT |
| `uvicorn` | 0.32.1 | BSD-3-Clause |
| `wcwidth` | 0.8.2 | MIT |

---

_Not: Lisans bilgisi PEP 639 `License-Expression` alanından, yoksa eski `License` alanından, o da yoksa sınıflandırıcılardan okunur. `pip-licenses` tek başına modern alanı okumadığı için 23 paketi "UNKNOWN" gösteriyordu; bu rapor her iki kaynağa da bakar._