"""Bağımlılık lisans raporu üreteci — şartname 5.10 uyum kanıtı (`make lisanslar`).

NEDEN AYRI BİR ÜRETEÇ:
    `pip-licenses` tek başına 23 paketi "UNKNOWN" olarak raporluyor. Sebep bir
    hata değil: bu paketler lisansını PEP 639'un `License-Expression` alanında
    beyan ediyor, `pip-licenses` 5.0.0 ise eski `License` alanına ve
    sınıflandırıcılara bakıyor.

    "UNKNOWN" dolu bir tablo, lisans uyumunu KANITLAMAK için hazırlanan bir
    belgede tam tersi izlenim bırakır. Bu üreteç her iki alanı da okur.

Şartname 5.10: "Açık kaynaklı gözüküp, uygulama aşamasında lisans problemi
çıkarma potansiyeli olan çözümler kullanılmamalıdır."
"""

from __future__ import annotations

import importlib.metadata as md
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
CIKTI = KOK / "docs" / "LISANSLAR.md"

# İzin verici kabul ettiğimiz lisans aileleri.
IZIN_VERICI = (
    "MIT", "BSD", "Apache", "ISC", "PSF", "Python Software Foundation",
    "Public Domain", "Unlicense", "Zope", "HPND", "MPL",
)

# Şartname 5.10'un asıl hedefi: açık gibi görünen, kısıtlı lisanslar.
YASAKLI_IZLER = ("Llama", "Gemma", "Commons Clause", "SSPL", "BUSL", "Proprietary", "RAIL")

# Elle incelenmesi gereken lisanslar (kullanıyoruz ama gerekçesini yazıyoruz).
DIKKAT = {
    "python-dateutil": (
        "Dual License (Apache-2.0 VEYA BSD-3-Clause)",
        "Üst veride yalnızca \"Dual License\" yazdığı için otomatik tarama "
        "sınıflandıramıyor. Proje `LICENSE` dosyasında Apache-2.0 ve "
        "BSD-3-Clause olarak çift lisanslıdır; **Apache-2.0 seçilmiştir** ve "
        "projemizin lisansıyla aynıdır. Kısıt doğurmaz.",
    ),
    "tld": (
        "MPL-1.1 OR GPL-2.0-only OR LGPL-2.1-or-later",
        "Üçlü seçmeli (disjunctive) lisans. **MPL-1.1 seçilmiştir.** Seçmeli "
        "lisanslarda kullanıcı bir seçeneği seçer; MPL-1.1 dosya bazlı copyleft "
        "olup kütüphane olarak kullanımda projeyi etkilemez. `trafilatura`'nın "
        "dolaylı bağımlılığıdır, kodumuz doğrudan çağırmaz.",
    ),
}


def _lisans(dagitim: md.Distribution) -> str:
    """PEP 639 `License-Expression` -> eski `License` -> sınıflandırıcı sırasıyla."""
    ust_veri = dagitim.metadata
    for alan in ("License-Expression", "License"):
        deger = ust_veri.get(alan)
        if deger and len(deger) < 120 and "\n" not in deger:
            return deger.strip()

    siniflar = [
        c.split("License ::")[-1].strip()
        for c in (ust_veri.get_all("Classifier") or [])
        if "License ::" in c
    ]
    if siniflar:
        return " / ".join(siniflar)
    return "BELİRSİZ"


def _izin_verici_mi(lisans: str) -> bool:
    return any(anahtar.lower() in lisans.lower() for anahtar in IZIN_VERICI)


def rapor_uret() -> tuple[str, list[str]]:
    paketler: list[tuple[str, str, str, str]] = []
    for dagitim in md.distributions():
        ad = dagitim.metadata.get("Name")
        if not ad:
            continue
        surum = dagitim.metadata.get("Version", "?")
        lisans = _lisans(dagitim)
        url = (
            dagitim.metadata.get("Home-page")
            or dagitim.metadata.get("Project-URL", "").split(", ")[-1]
            or "—"
        )
        paketler.append((ad, surum, lisans, url))

    paketler.sort(key=lambda p: p[0].lower())

    sorunlar: list[str] = []
    for ad, _, lisans, _ in paketler:
        if any(iz.lower() in lisans.lower() for iz in YASAKLI_IZLER):
            sorunlar.append(f"{ad}: KISITLI LİSANS — {lisans}")
        elif lisans == "BELİRSİZ":
            sorunlar.append(f"{ad}: lisans tespit edilemedi, elle inceleyin")
        elif not _izin_verici_mi(lisans) and ad.lower() not in DIKKAT:
            sorunlar.append(f"{ad}: izin verici listede değil — {lisans}")

    satirlar = [
        "# Bağımlılık Lisans Raporu",
        "",
        f"_Otomatik üretildi: {datetime.now():%d.%m.%Y %H:%M} · `make lisanslar`_",
        "",
        "Şartname 5.10: *\"Açık kaynaklı gözüküp, uygulama aşamasında lisans "
        "problemi çıkarma potansiyeli olan çözümler kullanılmamalıdır.\"*",
        "",
        "## Sonuç",
        "",
        f"- Taranan paket: **{len(paketler)}**",
        f"- Kısıtlı/şüpheli lisans: **{len(sorunlar)}**",
        "",
    ]

    if sorunlar:
        satirlar += ["### ⚠️ İncelenmesi gerekenler", ""]
        satirlar += [f"- {s}" for s in sorunlar]
        satirlar.append("")
    else:
        satirlar += [
            "✅ **Tüm bağımlılıklar izin verici (permissive) lisanslıdır.** "
            "Kısıtlı kullanım şartı olan hiçbir bileşen yoktur.",
            "",
        ]

    satirlar += [
        "## Model lisansları",
        "",
        "| Model | Lisans | Kullanım |",
        "|---|---|---|",
        "| Qwen3.5 (2B/4B/9B/27B) | **Apache 2.0** | Çıkarım ve chatbot |",
        "| Qwen3.6-27B | **Apache 2.0** | Final ölçüm koşusu |",
        "",
        "### Bilinçli olarak KULLANILMAYAN modeller",
        "",
        "| Model ailesi | Lisans | Neden kullanılmadı |",
        "|---|---|---|",
        "| Llama 3.x/4, Turkish-Llama | Llama Community License | Kullanıcı sayısı "
        "eşiği, adlandırma ve kullanım kısıtları içerir. \"Açık gibi görünen ama "
        "kısıtlı\" tanımına birebir uyar — şartname 5.10'un hedefi budur. |",
        "| Gemma, Türkçe-Gemma, EmbeddingGemma | Gemma Terms of Use | Kullanım "
        "kısıtlaması ve geri çağırma hükmü içerir. Aynı gerekçe. |",
        "",
        "## Elle incelenen lisanslar",
        "",
    ]

    for paket, (lisans, aciklama) in DIKKAT.items():
        satirlar += [f"### `{paket}` — {lisans}", "", aciklama, ""]

    satirlar += [
        "## Tam liste",
        "",
        "| Paket | Sürüm | Lisans |",
        "|---|---|---|",
    ]
    satirlar += [f"| `{ad}` | {surum} | {lisans} |" for ad, surum, lisans, _ in paketler]
    satirlar += [
        "",
        "---",
        "",
        "_Not: Lisans bilgisi PEP 639 `License-Expression` alanından, yoksa eski "
        "`License` alanından, o da yoksa sınıflandırıcılardan okunur. "
        "`pip-licenses` tek başına modern alanı okumadığı için 23 paketi "
        "\"UNKNOWN\" gösteriyordu; bu rapor her iki kaynağa da bakar._",
    ]

    return "\n".join(satirlar), sorunlar


def main() -> int:
    icerik, sorunlar = rapor_uret()
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(icerik, encoding="utf-8")

    print(f"✅ {CIKTI.relative_to(KOK)} yazıldı")
    if sorunlar:
        print(f"⚠️  {len(sorunlar)} paket incelenmeli:")
        for s in sorunlar:
            print(f"     - {s}")
        return 1
    print("   Tüm bağımlılıklar izin verici lisanslı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
