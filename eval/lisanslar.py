"""Bağımlılık lisans raporu üreteci — şartname 5.10 uyum kanıtı (`make lisanslar`).

NEDEN AYRI BİR ÜRETEÇ:
    `pip-licenses` tek başına 23 paketi "UNKNOWN" olarak raporluyor. Sebep bir
    hata değil: bu paketler lisansını PEP 639'un `License-Expression` alanında
    beyan ediyor, `pip-licenses` 5.0.0 ise eski `License` alanına ve
    sınıflandırıcılara bakıyor.

    "UNKNOWN" dolu bir tablo, lisans uyumunu KANITLAMAK için hazırlanan bir
    belgede tam tersi izlenim bırakır. Bu üreteç her iki alanı da okur.

MODELLER PAKET DEĞİLDİR — ve asıl risk oradadır:
    `md.distributions()` kurulu paketleri görür; EVREN'de koşan 122B'lik modeli
    görmez. Şartname 5.10'un hedefi ise tam olarak model lisanslarıdır (Llama,
    Gemma). Bu yüzden model tablosu elle tutulur ama iddiası elle doğrulanmaz:

        python -m eval.lisanslar --model-teyit

    her modelin Hugging Face deposundaki lisans etiketini çeker, beklenenle
    karşılaştırır, tutmazsa çıkış kodu 1 verir ve kanıtı
    `docs/kanit/model-lisanslari.json` dosyasına yazar. Teyitsiz koşu (ağ yok,
    hava boşluğu demosu) son teyidin tarihini raporlar — "teyit edildi" demez.

Şartname 5.10: "Açık kaynaklı gözüküp, uygulama aşamasında lisans problemi
çıkarma potansiyeli olan çözümler kullanılmamalıdır."
"""

from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import re
import sys
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
CIKTI = KOK / "docs" / "LISANSLAR.md"
MODEL_KANITI = KOK / "docs" / "kanit" / "model-lisanslari.json"
HF_API = "https://huggingface.co/api/models/{depo}"

# Windows konsolu cp1254; rapordaki ✅ işaretleri orada UnicodeEncodeError
# fırlatır. Takımın yarısı Windows'ta çalışıyor.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# İzin verici kabul ettiğimiz lisans aileleri.
IZIN_VERICI = (
    "MIT", "BSD", "Apache", "ISC", "PSF", "Python Software Foundation",
    "Public Domain", "Unlicense", "Zope", "HPND", "MPL",
)

# Şartname 5.10'un asıl hedefi: açık gibi görünen, kısıtlı lisanslar.
YASAKLI_IZLER = ("Llama", "Gemma", "Commons Clause", "SSPL", "BUSL", "Proprietary", "RAIL")

# Kullandığımız modeller. `depo` alanı Hugging Face deposudur; `--model-teyit`
# lisansı oradan çeker. Kimlik (hangi takma ad hangi depoya karşılık geliyor)
# EVREN model kartından gelir — servisin `/v1/models` ucu yalnız takma ad
# döndürür, model kimliği yayımlamaz. Bu sınır raporda da yazılıdır.
MODELLER = [
    {
        "kullanim": "Çıkarım — varsayılan, ölçüm koşuları",
        "nerede": "EVREN `llm-large`",
        "depo": "Qwen/Qwen3.5-122B-A10B",
        "beklenen": "apache-2.0",
        "not": "MoE, 122B toplam / 10B aktif, BF16, 262.144 token bağlam.",
    },
    {
        "kullanim": "Çıkarım — seçilebilir hızlı uç, **varsayılan değil**",
        "nerede": "EVREN `llm-fast` (`--model llm-fast`)",
        "depo": "Qwen/Qwen3.6-35B-A3B",
        "beklenen": "apache-2.0",
        "not": "MoE. Ölçümde şema geçerliliği `llm-large`'ın altında kaldığı için "
        "varsayılan yapılmadı; bayrakla seçilebildiği sürece lisansı da teyitli olmalı.",
    },
    {
        "kullanim": "Çıkarım — yerel yedek, hava boşluğu demosu",
        "nerede": "Ollama `qwen3.5:4b-q4_K_M`",
        "depo": "Qwen/Qwen3.5-4B",
        "beklenen": "apache-2.0",
        "not": "EVREN düştüğünde aynı kod yolu yerelde koşar (`LLM_SAGLAYICI=ollama`).",
    },
    {
        "kullanim": "Gömme (S-09) — **aday**, henüz kullanılmıyor",
        "nerede": "EVREN `bge-m3-embed` · yerel `BAAI/bge-m3`",
        "depo": "BAAI/bge-m3",
        "beklenen": "mit",
        "not": "S-09'un gömme modeli. Gemma tabanlı alternatiflere gerek yok.",
    },
]

# EVREN'in yayımladığı uçlar (`GET /v1/models`, 24 Ağu 2026 koşusu). Kullandığımız
# uçların kimliği model kartından teyitli; kalanların DEĞİL. Bu tablo "bakmadık"
# ile "baktık, gerek yok" arasındaki farkı yazıya döker.
EVREN_UCLARI = [
    ("`llm-large`", "Qwen3.5-122B-A10B — Apache-2.0", "✅ kullanılıyor"),
    ("`llm-fast`", "Qwen3.6-35B-A3B — Apache-2.0", "🟡 `--model llm-fast` ile seçilebilir; varsayılan değil, ölçüm koşuları `llm-large` ile yapıldı"),
    ("`bge-m3-embed` · `bge-m3-sparse` · `bge-m3-colbert`", "adı BGE-M3'ü işaret ediyor — MIT", "🟡 S-09 adayı; kullanılmadan önce kimlik model kartından teyit edilecek"),
    ("`embed`", "**kimlik doğrulanmadı**", "⛔ kullanılmıyor — jenerik ad; EmbeddingGemma gibi kısıtlı bir model olma ihtimali dışlanamaz"),
    ("`rerank`", "**kimlik doğrulanmadı**", "⛔ kullanılmıyor — bu senaryoda ihtiyaç yok"),
    ("`router`", "**kimlik doğrulanmadı**", "⛔ kullanılmıyor"),
    ("`guard`", "**kimlik doğrulanmadı**", "⛔ kullanılmıyor"),
    ("`vlm`", "**kimlik doğrulanmadı**", "⛔ kullanılmıyor — görsel girdi yok"),
]

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


def _ad_normal(ad: str) -> str:
    return re.sub(r"[-_.]+", "-", ad).lower()


def proje_bagimliliklari() -> set[str]:
    """`requirements.txt` köklerinden başlayarak geçişli bağımlılık kapanışı.

    NEDEN GEREKLİ: bu rapor sanal ortamda KURULU olan her şeyi tarar; oysa
    teslim edilen şey `requirements.txt`. İkisi ayrışır — biri bir şeyi denemek
    için `pip install` yapar, paket ortamda kalır. 24 Ağustos'ta ortamda
    `openai` duruyordu; oysa `src/extraction/saglayici.py` o paketi bilerek
    eklemiyor, EVREN'e düz `httpx` ile gidiyor.

    Listede bırakmak "OpenAI kullanıyorlar" izlenimi verir, silmek ise raporu
    eksiltir. Doğrusu ikisini de göstermek ve KAPSAMI yazmaktır.
    """
    sira: list[tuple[str, str | None]] = []
    gereksinim_dosyasi = KOK / "requirements.txt"
    if gereksinim_dosyasi.exists():
        for satir in gereksinim_dosyasi.read_text(encoding="utf-8").splitlines():
            sira += _gereksinim_ayristir(satir.split("#")[0])

    kapanis: set[str] = set()
    gorulen: set[tuple[str, str | None]] = set()
    while sira:
        ad, ek = sira.pop()
        if (ad, ek) in gorulen:
            continue
        gorulen.add((ad, ek))
        kapanis.add(ad)
        try:
            dagitim = md.distribution(ad)
        except md.PackageNotFoundError:
            continue
        for gereksinim in dagitim.metadata.get_all("Requires-Dist") or []:
            # `; extra == "dev"` ile gelen satırlar isteğe bağlı eklerdir:
            # yalnız o ek İSTENMİŞSE bağımlılıktır. `lxml[html_clean]` böyle
            # gelir — ek atlanırsa `lxml_html_clean` yanlışlıkla "ortam
            # paketi" görünür, oysa trafilatura onu çalışırken kullanır.
            # Ek adı da normalleştirilir: `jusText` `lxml[html_clean]` yazar,
            # `lxml` ise ekini `extra == "html-clean"` diye ilan eder.
            ek_eslesme = re.search(r"""extra\s*==\s*['"]([^'"]+)['"]""", gereksinim)
            if ek_eslesme and _ad_normal(ek_eslesme.group(1)) != ek:
                continue
            sira += _gereksinim_ayristir(gereksinim.split(";")[0])
    return kapanis


def _gereksinim_ayristir(metin: str) -> list[tuple[str, str | None]]:
    """`lxml[html_clean]>=5` -> [("lxml", "html_clean")]. Eksiz ise ek None."""
    metin = metin.strip()
    if not metin:
        return []
    eslesme = re.match(r"^([A-Za-z0-9._-]+)\s*(?:\[([^\]]+)\])?", metin)
    if not eslesme:
        return []
    ad = _ad_normal(eslesme.group(1))
    ekler = [_ad_normal(e) for e in (eslesme.group(2) or "").split(",") if e.strip()]
    return [(ad, ek) for ek in ekler] or [(ad, None)]


# ---------------------------------------------------------------------------
# Model lisansları
# ---------------------------------------------------------------------------


def model_lisanslarini_teyit_et() -> dict:
    """Her modelin HF deposundaki lisans etiketini çeker (ağ gerekir)."""
    import httpx

    kayitlar = []
    for model in MODELLER:
        depo = model["depo"]
        kayit = {
            "depo": depo,
            "kaynak": HF_API.format(depo=depo),
            "beklenen": model["beklenen"],
            "bulunan": None,
            "durum": None,
            "hata": None,
            "son_degisiklik": None,
        }
        try:
            yanit = httpx.get(HF_API.format(depo=depo), timeout=30.0, follow_redirects=True)
            kayit["durum"] = yanit.status_code
            if yanit.status_code == 200:
                veri = yanit.json()
                bulunan = (veri.get("cardData") or {}).get("license")
                if not bulunan:
                    etiketler = [e for e in veri.get("tags", []) if e.startswith("license:")]
                    bulunan = etiketler[0].split(":", 1)[1] if etiketler else None
                kayit["bulunan"] = bulunan
                kayit["son_degisiklik"] = veri.get("lastModified")
        except Exception as hata:  # ağ, JSON, ne olursa — teyit edilemedi demektir
            kayit["hata"] = f"{type(hata).__name__}: {hata}"
        kayitlar.append(kayit)

    kanit = {
        "teyit_tarihi": datetime.now().astimezone().isoformat(timespec="seconds"),
        "yontem": "Hugging Face model API'si — depo üst verisindeki lisans etiketi",
        "modeller": kayitlar,
    }
    MODEL_KANITI.parent.mkdir(parents=True, exist_ok=True)
    MODEL_KANITI.write_text(json.dumps(kanit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return kanit


def model_kanitini_oku() -> dict | None:
    if not MODEL_KANITI.exists():
        return None
    try:
        return json.loads(MODEL_KANITI.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def model_sorunlari(kanit: dict | None) -> list[str]:
    """Beklenen lisansla teyit edilen lisans tutuyor mu?"""
    if kanit is None:
        return []
    sorunlar = []
    for kayit in kanit["modeller"]:
        if kayit["hata"] or kayit["durum"] != 200:
            sorunlar.append(f"{kayit['depo']}: lisans teyit edilemedi ({kayit['hata'] or kayit['durum']})")
        elif (kayit["bulunan"] or "").lower() != kayit["beklenen"].lower():
            sorunlar.append(
                f"{kayit['depo']}: BEKLENEN {kayit['beklenen']}, BULUNAN {kayit['bulunan']}"
            )
        elif any(iz.lower() in kayit["depo"].lower() for iz in YASAKLI_IZLER):
            sorunlar.append(f"{kayit['depo']}: yasaklı model ailesi")
    return sorunlar


def _model_bolumu(kanit: dict | None) -> list[str]:
    teyitler = {k["depo"]: k for k in (kanit or {}).get("modeller", [])}

    if kanit:
        tarih = kanit["teyit_tarihi"][:10]
        teyit_notu = (
            f"Lisanslar **{tarih}** tarihinde Hugging Face depo üst verisinden "
            f"çekilmiştir; ham yanıt: [`docs/kanit/model-lisanslari.json`](kanit/model-lisanslari.json). "
            "Modelin kendi beyanına ya da bizim hafızamıza dayanılmıyor."
        )
    else:
        teyit_notu = (
            "⚠️ Model lisansları bu koşuda teyit edilmedi "
            "(`python -m eval.lisanslar --model-teyit` ile teyit edilir)."
        )

    satirlar = [
        "## Model lisansları",
        "",
        "Modeller pip paketi değildir; yukarıdaki tarama onları görmez. Şartname",
        "5.10'un asıl hedefi ise model lisanslarıdır — bu bölüm o yüzden var.",
        "",
        teyit_notu,
        "",
        "| Kullanım | Nerede koşuyor | Hugging Face deposu | Lisans | Teyit |",
        "|---|---|---|---|---|",
    ]
    for model in MODELLER:
        teyit = teyitler.get(model["depo"])
        if teyit and teyit["durum"] == 200 and teyit["bulunan"]:
            lisans = f"**{teyit['bulunan']}**"
            isaret = f"✅ HF API · {(kanit or {}).get('teyit_tarihi', '')[:10]}"
        else:
            lisans = f"{model['beklenen']} (beklenen)"
            isaret = "⚠️ teyit edilmedi"
        satirlar.append(
            f"| {model['kullanim']} | {model['nerede']} | `{model['depo']}` | {lisans} | {isaret} |"
        )

    satirlar += [
        "",
        "Notlar:",
        "",
    ]
    satirlar += [f"- `{model['depo']}` — {model['not']}" for model in MODELLER]

    satirlar += [
        "",
        "### EVREN uçları — hangisi kullanılıyor, hangisi neden kullanılmıyor",
        "",
        "Çıkarım, T.C. Cumhurbaşkanlığı SSB'nin yarışmaya tahsis ettiği **EVREN**",
        "servisinde koşuyor. Servis `GET /v1/models` ile on uç yayımlıyor; hepsi",
        "takma addır, model kimliği döndürmez. Kullandığımız uçların kimliği EVREN",
        "model kartından teyitlidir, kalanlarınki **değildir** — o yüzden kullanılmıyorlar.",
        "",
        "| Uç | Model kimliği | Durum |",
        "|---|---|---|",
    ]
    satirlar += [f"| {uc} | {kimlik} | {durum} |" for uc, kimlik, durum in EVREN_UCLARI]

    satirlar += [
        "",
        "### Servis üzerinden kullanmak lisans durumunu değiştirir mi?",
        "",
        "Hayır — üç sebeple, üçü de teslimde sorulabilir:",
        "",
        "1. **Depoda model ağırlığı yok.** Apache-2.0 bir dağıtım lisansıdır;",
        "   biz ağırlık dağıtmıyoruz, servisi HTTP ile çağırıyoruz. Yeniden",
        "   dağıtım yükümlülüğü doğmuyor.",
        "2. **Modelin kendisi Apache-2.0 olduğu için kurum kendi sunucusunda da",
        "   koşturabilir.** Şartname 5.10'un derdi \"uygulama aşamasında lisans",
        "   problemi çıkarma potansiyeli\"dir; Apache-2.0 bir model bu potansiyeli",
        "   taşımaz. Kısıtlı lisanslı bir model olsaydı servis üzerinden çağırmak",
        "   sorunu çözmezdi — kurum içine taşındığı gün patlardı.",
        "3. **Servise kilitlenme yok, ölçülmüş durumda.** `LLM_SAGLAYICI=ollama`",
        "   ile aynı kod yolu yerel modelle koşuyor (`make extract-yerel`); hava",
        "   boşluğu demosu bunu 18 Ağustos'ta doğruladı. EVREN'in kullanım",
        "   şartları bir **hizmet** sözleşmesidir, yazılım lisansı değil; projenin",
        "   açık kaynak durumunu etkilemez.",
        "",
        "### Bilinçli olarak KULLANILMAYAN modeller",
        "",
        "| Model ailesi | Lisans | Neden kullanılmadı |",
        "|---|---|---|",
        "| Llama 3.x/4, Turkish-Llama | Llama Community License | Kullanıcı sayısı "
        "eşiği, adlandırma ve kullanım kısıtları içerir. \"Açık gibi görünen ama "
        "kısıtlı\" tanımına birebir uyar — şartname 5.10'un hedefi budur. |",
        "| Gemma, Türkçe-Gemma, EmbeddingGemma | Gemma Terms of Use | Kullanım "
        "kısıtlaması ve geri çağırma hükmü içerir. Aynı gerekçe. **Gömme modeli "
        "seçilirken (S-09) asıl tuzak budur:** EmbeddingGemma teknik olarak "
        "uygun görünür, lisansı uygun değildir. |",
        "",
    ]
    return satirlar


def rapor_uret(model_kaniti: dict | None = None) -> tuple[str, list[str]]:
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

    sorunlar += model_sorunlari(model_kaniti)

    kapanis = proje_bagimliliklari()
    proje_paketleri = {_ad_normal(ad) for ad, _, _, _ in paketler} & kapanis
    ortam_paketleri = [ad for ad, _, _, _ in paketler if _ad_normal(ad) not in kapanis]

    satirlar = [
        "# Bağımlılık ve Model Lisans Raporu",
        "",
        f"_Otomatik üretildi: {datetime.now():%d.%m.%Y %H:%M} · `make lisanslar`_",
        "",
        "Şartname 5.10: *\"Açık kaynaklı gözüküp, uygulama aşamasında lisans "
        "problemi çıkarma potansiyeli olan çözümler kullanılmamalıdır.\"*",
        "",
        "## Sonuç",
        "",
        f"- Taranan paket: **{len(paketler)}** "
        f"(bunun **{len(proje_paketleri)}** tanesi `requirements.txt` kapanışında)",
        f"- Taranan model: **{len(MODELLER)}**",
        f"- Kısıtlı/şüpheli lisans: **{len(sorunlar)}**",
        "",
    ]

    if sorunlar:
        satirlar += ["### ⚠️ İncelenmesi gerekenler", ""]
        satirlar += [f"- {s}" for s in sorunlar]
        satirlar.append("")
    else:
        satirlar += [
            "✅ **Tüm bağımlılıklar ve modeller izin verici (permissive) lisanslıdır.** "
            "Kısıtlı kullanım şartı olan hiçbir bileşen yoktur.",
            "",
        ]

    satirlar += _model_bolumu(model_kaniti)
    satirlar += [
        "## Elle incelenen lisanslar",
        "",
    ]

    for paket, (lisans, aciklama) in DIKKAT.items():
        satirlar += [f"### `{paket}` — {lisans}", "", aciklama, ""]

    satirlar += [
        "## Tam liste",
        "",
        f"Sanal ortamda kurulu **{len(paketler)}** paketin **{len(proje_paketleri)}** tanesi",
        "`requirements.txt`'ten (doğrudan ya da geçişli olarak) gelir; kalanlar ortamda",
        "kalmış, teslim edilen koda dahil olmayan paketlerdir. Ayrımı yazmak gerekiyor:",
        "`pip install -r requirements.txt` ile kurulan temiz bir ortamda **ortam**",
        "kapsamlı satırlar bulunmaz.",
        "",
    ]
    if ortam_paketleri:
        satirlar += [
            "> ⚠️ Ortam kapsamlı paketler: "
            + ", ".join(f"`{ad}`" for ad in ortam_paketleri)
            + ". Bunlardan `openai`, projenin **kullanmadığı** bir istemcidir — EVREN'e "
            "düz `httpx` ile gidilir (`src/extraction/saglayici.py`), bu bilinçli bir "
            "karardır. Ortamda durması onu bağımlılık yapmaz.",
            "",
        ]
    satirlar += [
        "| Paket | Sürüm | Lisans | Kapsam |",
        "|---|---|---|---|",
    ]
    satirlar += [
        f"| `{ad}` | {surum} | {lisans} "
        f"| {'proje' if _ad_normal(ad) in proje_paketleri else 'ortam'} |"
        for ad, surum, lisans, _ in paketler
    ]
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


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description="lisans raporu (şartname 5.10)")
    ayristirici.add_argument(
        "--model-teyit",
        action="store_true",
        help="model lisanslarını Hugging Face'ten çek ve kanıtı yaz (ağ gerekir)",
    )
    secenekler = ayristirici.parse_args(argv)

    if secenekler.model_teyit:
        model_kaniti = model_lisanslarini_teyit_et()
        print(f"   Model lisansları teyit edildi → {MODEL_KANITI.relative_to(KOK)}")
    else:
        # Ağsız koşuda son teyit kullanılır; rapor tarihini yazar, "bugün teyit
        # edildi" demez. Hava boşluğu demosunda `make lisanslar` çalışmalı.
        model_kaniti = model_kanitini_oku()

    icerik, sorunlar = rapor_uret(model_kaniti)
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(icerik, encoding="utf-8")

    print(f"✅ {CIKTI.relative_to(KOK)} yazıldı")
    if model_kaniti is None:
        print("   ⚠️  Model lisansları teyit edilmemiş: `python -m eval.lisanslar --model-teyit`")
    if sorunlar:
        print(f"⚠️  {len(sorunlar)} bileşen incelenmeli:")
        for sorun in sorunlar:
            print(f"     - {sorun}")
        return 1
    print("   Tüm bağımlılıklar ve modeller izin verici lisanslı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
