"""robots.txt kontrol günlüğü üreteci — veri toplama etiği kanıtı (G-14).

NEDEN ELLE YAZILAN BİR BEYAN DEĞİL:
    "robots.txt'e uyuyoruz" cümlesi bir iddiadır; jüri iddia değil KANIT ister.
    Üstelik banka siteleri robots.txt dosyalarını değiştirir — yazıldığı gün
    doğru olan bir cümle iki hafta sonra yanlış olabilir. Bu araç, toplayıcının
    KENDİ nezaket katmanını (`src/collector/toplayici.RobotsBekcisi`) çağırarak
    her alan adı için kararı yeniden üretir ve tarihli günlüğe yazar.

    Kararı üreten kod ile toplamayı yapan kod AYNIDIR. Ayrı bir denetleyici
    yazılsaydı günlük "denetleyicinin ne düşündüğünü" gösterirdi; oysa kanıt
    olması gereken şey toplayıcının ne yaptığıdır.

ÜRETTİKLERİ (`docs/kanit/` altında, jüri üçünü birlikte okur):
  * `robots/<alan>.txt`            — çekilen robots.txt dosyalarının kopyası
  * `robots-kontrol-gunlugu.json`  — makine okur (sha256, HTTP durumu, karar)
  * `ROBOTS_KONTROL_GUNLUGU.md`    — insan okur (tablo + URL bazında karar)

KULLANIM:
    python tools/robots_kanit.py               # canlı kontrol, günlüğü yeniler
    python tools/robots_kanit.py --cevrimdisi  # ağ yok: JSON'dan MD'yi üret

ALAN BAŞINA İKİ İSTEK ATILIR ve bu bilinçlidir: biri arşiv kopyasını almak
için (sha256'lı kanıt), diğeri `RobotsBekcisi`'nin kendi çekimi. İkincisini
atlamanın tek yolu bekçinin iç önbelleğini elle doldurmak olurdu; o zaman da
günlük üretim kod yolunun kararını değil, bizim kurgumuzu gösterirdi.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

import httpx  # noqa: E402

from src.collector.toplayici import (  # noqa: E402
    ISTEK_ARASI_SANIYE,
    KULLANICI_AJANI,
    RobotsBekcisi,
    bankalari_yukle,
)

KANIT_DIZIN = KOK / "docs" / "kanit"
ROBOTS_DIZIN = KANIT_DIZIN / "robots"
GUNLUK_JSON = KANIT_DIZIN / "robots-kontrol-gunlugu.json"
GUNLUK_MD = KANIT_DIZIN / "ROBOTS_KONTROL_GUNLUGU.md"

# BDDK kayıt defterinin kaynağıdır, kampanya için taranmaz — ama kontrol edilir
# ve sonucu günlüğe yazılır. `data/banks.yaml` "BDDK otomatik taranmadı, liste
# elle alındı" diyor; bu satır o cümlenin kanıtıdır.
EK_ALANLAR: list[tuple[str, str]] = [
    ("BDDK — kayıt defteri kaynağı (kampanya için taranmaz)", "https://www.bddk.org.tr"),
]

ZAMAN_ASIMI = 15.0


def _alan_koku(url: str) -> str:
    parcalar = urlparse(url)
    return f"{parcalar.scheme}://{parcalar.netloc}"


def _goreli(yol: Path) -> str:
    """Depo köküne göre yol. Kök dışındaysa (testlerde tmp dizini) olduğu gibi."""
    try:
        yol = yol.relative_to(KOK)
    except ValueError:
        pass
    return str(yol).replace("\\", "/")


def robots_getir(alan: str) -> dict:
    """robots.txt'in arşiv kopyasını çeker. Hata da bir sonuçtur, yazılır."""
    adres = urljoin(alan + "/", "robots.txt")
    sonuc: dict = {
        "adres": adres,
        "kullanici_ajani": KULLANICI_AJANI,
        "durum": None,
        "hata": None,
        "uzunluk": 0,
        "sha256": None,
        "dosya": None,
        "gonderilen_basliklar": None,
        "beyan_edilen_gecikme": None,
        "sitemapler": [],
    }
    try:
        with httpx.Client(timeout=ZAMAN_ASIMI, follow_redirects=True) as istemci:
            yanit = istemci.get(adres, headers={"User-Agent": KULLANICI_AJANI})
    except httpx.HTTPError as hata:
        # Sertifika zinciri, DNS, zaman aşımı — hepsi buraya düşer. Toplayıcı bu
        # durumda sayfayı ÇEKMEZ (`izinli_mi` False döner); günlük bunu gizlemek
        # yerine yazar.
        sonuc["hata"] = f"{type(hata).__name__}: {hata}"
        return sonuc

    sonuc["durum"] = yanit.status_code
    sonuc["gonderilen_basliklar"] = dict(yanit.request.headers)
    icerik_turu = yanit.headers.get("content-type", "")
    metin = yanit.text

    # 404 gövdesi çoğu sunucuda HTML'dir; onu robots.txt diye arşivlemek kanıtı
    # kirletir. Yalnız gerçek robots.txt saklanır.
    if yanit.status_code == 200 and "html" not in icerik_turu.lower():
        # Sunucunun gönderdiği BAYTLAR arşivlenir ve özet onların üzerinden
        # alınır. `write_text` Windows'ta \n'i \r\n yapar; o zaman günlükteki
        # sha256 ile diskteki dosyanın özeti tutmaz ve kanıt doğrulanamaz hâle
        # gelir. Jüri `sha256sum docs/kanit/robots/*.txt` koşabilmelidir.
        ham = yanit.content
        sonuc["uzunluk"] = len(ham)
        sonuc["sha256"] = hashlib.sha256(ham).hexdigest()
        ROBOTS_DIZIN.mkdir(parents=True, exist_ok=True)
        dosya = ROBOTS_DIZIN / f"{urlparse(alan).netloc}.txt"
        dosya.write_bytes(ham)
        sonuc["dosya"] = _goreli(dosya)
        gecikmeler = [
            float(d.replace(",", "."))
            for d in re.findall(r"(?im)^\s*crawl-delay:\s*([0-9]+(?:[.,][0-9]+)?)", metin)
        ]
        sonuc["beyan_edilen_gecikme"] = max(gecikmeler) if gecikmeler else None
        sonuc["sitemapler"] = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", metin)
    return sonuc


def alan_denetle(bekci: RobotsBekcisi, ad: str, alan: str, urller: list[str]) -> dict:
    """Bir alan adı için arşiv kopyası + üretim kod yolunun kararları."""
    kayit: dict = {"ad": ad, "alan": alan, "robots": robots_getir(alan), "kararlar": []}
    for url in urller:
        kayit["kararlar"].append(
            {
                "url": url,
                "izinli": bekci.izinli_mi(url),
                "uygulanan_bekleme_sn": bekci.bekleme_suresi(url),
            }
        )
    return kayit


def kontrol_et(bankalar_yolu: Path | None = None) -> dict:
    """Kayıt defterindeki her alan adını + BDDK'yi kontrol eder."""
    bankalar = bankalari_yukle(bankalar_yolu) if bankalar_yolu else bankalari_yukle()
    bekci = RobotsBekcisi()
    kayitlar: list[dict] = []

    for banka in bankalar:
        if not banka.site:
            # Kuruluş aşamasındaki bankaların sitesi yok. Kayıt defterinde
            # kalırlar (docs/VERI_METODOLOJISI.md §1.2); kontrol edilecek bir
            # alan adı olmadığı da günlüğe yazılır — sessiz atlama olmaz.
            kayitlar.append(
                {
                    "ad": f"{banka.kisa_ad} ({banka.durum})",
                    "alan": None,
                    "atlandi": "site yok — kuruluş aşamasında",
                    "robots": None,
                    "kararlar": [],
                }
            )
            continue
        alan = _alan_koku(banka.site)
        urller = list(dict.fromkeys([banka.site.rstrip("/") or alan, *banka.seed_urls]))
        kayit = alan_denetle(bekci, f"{banka.kisa_ad} ({banka.durum})", alan, urller)
        kayit["robots_kontrol_acik"] = banka.robots_kontrol
        kayitlar.append(kayit)
        time.sleep(ISTEK_ARASI_SANIYE)

    for ad, alan in EK_ALANLAR:
        kayitlar.append(alan_denetle(bekci, ad, alan, [alan]))
        time.sleep(ISTEK_ARASI_SANIYE)

    return {
        "uretildi": datetime.now().astimezone().isoformat(timespec="seconds"),
        "kullanici_ajani": KULLANICI_AJANI,
        "asgari_istek_araligi_sn": ISTEK_ARASI_SANIYE,
        "uretici": "tools/robots_kanit.py",
        "alanlar": kayitlar,
    }


# ---------------------------------------------------------------------------
# Günlük metni
# ---------------------------------------------------------------------------


def _robots_ozeti(robots: dict | None) -> str:
    if robots is None:
        return "—"
    if robots["hata"]:
        return f"⚠️ çekilemedi ({robots['hata'].split(':')[0]})"
    if robots["dosya"]:
        return f"HTTP {robots['durum']} · {robots['uzunluk']} bayt"
    return f"HTTP {robots['durum']} · robots.txt yok"


def _gecikme_metni(deger: float | None) -> str:
    return "yok" if deger is None else f"{deger:g} sn"


def _karar_metni(robots: dict, karar: dict) -> str:
    """Çekilmeme sebebini ayırır — ikisi aynı şey değildir.

    `Disallow` gerçek bir REDDİR; robots.txt'in okunamaması ise bizim kendi
    temkinimizdir. Günlükte ikisini "reddedildi" diye birleştirmek, sitenin
    bize yasak koyduğu izlenimi verir — jüriye yanlış bilgi olur.
    """
    if karar["izinli"]:
        return "✅ izinli"
    if robots["hata"]:
        return "⛔ çekilmez — robots.txt okunamadı (temkinli davranış)"
    return "⛔ çekilmez — robots.txt `Disallow` ile reddetti"


def gunluk_uret(veri: dict) -> str:
    satirlar = [
        "# robots.txt Kontrol Günlüğü",
        "",
        f"_Otomatik üretildi: {veri['uretildi']} · `{veri['uretici']}`_",
        "",
        "Bu günlük **G-14** (veri toplama etiği kanıtı) kapsamındadır;",
        "`docs/kanit/VERI_TOPLAMA_ETIGI.md` onu kanıt olarak gösterir.",
        "",
        "Kararları üreten kod, toplamayı yapan kodun ta kendisidir:",
        "`src/collector/toplayici.RobotsBekcisi`. Ayrı bir denetleyici yazılsaydı bu",
        "tablo toplayıcının değil, denetleyicinin davranışını gösterirdi.",
        "",
        "## Kullanılan User-Agent",
        "",
        "```",
        veri["kullanici_ajani"],
        "```",
        "",
        "Tanım: `src/collector/toplayici.py` · `KULLANICI_AJANI`. Aynı dize hem",
        "robots.txt çekiminde hem sayfa çekiminde gönderilir; kimlik ve iletişim",
        "adresi açıkça beyan edilir, **tarayıcı taklidi yapılmaz**.",
        "",
    ]

    ornek = next(
        (
            alan["robots"]["gonderilen_basliklar"]
            for alan in veri["alanlar"]
            if alan.get("robots") and alan["robots"].get("gonderilen_basliklar")
        ),
        None,
    )
    if ornek:
        satirlar += [
            "Bu koşuda ağa **gerçekten gönderilen** başlıklar (iddia değil, kayıt):",
            "",
            "```http",
            *[f"{ad}: {deger}" for ad, deger in ornek.items()],
            "```",
            "",
        ]

    satirlar += [
        f"İstekler arası asgari bekleme: **{veri['asgari_istek_araligi_sn']:g} saniye**,",
        "eşzamanlı istek yok. robots.txt daha uzun bir `Crawl-delay` beyan ederse",
        "büyüğü uygulanır (`RobotsBekcisi.bekleme_suresi`).",
        "",
        "## Özet",
        "",
        "| Alan adı | robots.txt | Beyan edilen crawl-delay | Uygulanan bekleme | Denetlenen URL | İzinli | Çekilmeyen |",
        "|---|---|---|---|---|---|---|",
    ]

    toplam_izinli = toplam_red = 0
    for alan in veri["alanlar"]:
        if alan.get("atlandi"):
            satirlar.append(f"| {alan['ad']} | — | — | — | 0 | — | _{alan['atlandi']}_ |")
            continue
        robots = alan["robots"]
        izinli = sum(1 for karar in alan["kararlar"] if karar["izinli"])
        red = len(alan["kararlar"]) - izinli
        toplam_izinli += izinli
        toplam_red += red
        bekleme = max((k["uygulanan_bekleme_sn"] for k in alan["kararlar"]), default=0.0)
        satirlar.append(
            f"| {alan['ad']}<br>`{urlparse(alan['alan']).netloc}` "
            f"| {_robots_ozeti(robots)} "
            f"| {_gecikme_metni(robots['beyan_edilen_gecikme'])} "
            f"| {bekleme:g} sn "
            f"| {len(alan['kararlar'])} | {izinli} | {red} |"
        )

    satirlar += [
        "",
        f"**Toplam:** {toplam_izinli} URL izinli, {toplam_red} URL çekilmiyor.",
        "Çekilmeyen URL kazıyıcıya hiç gitmez — kapı `TemelKaziyici._sayfayi_cek`",
        "içindedir ve tarayıcı adrese gitmeden önce sorulur. İki farklı sebep aynı",
        "sonucu verir: robots.txt `Disallow` ile reddetmiştir, ya da okunamamıştır",
        "(o zaman `izinli_mi` `False` döner — temkinli taraf).",
        "",
        "Arşiv kopyaları sunucunun gönderdiği baytlardır; doğrulamak için:",
        "`sha256sum docs/kanit/robots/*.txt` çıktısı aşağıdaki özetlerle eşleşmelidir.",
        "",
        "## Alan adı ayrıntıları",
        "",
    ]

    for alan in veri["alanlar"]:
        satirlar += [f"### {alan['ad']}", ""]
        if alan.get("atlandi"):
            satirlar += [f"Atlandı: {alan['atlandi']}.", ""]
            continue
        robots = alan["robots"]
        satirlar.append(f"- robots.txt: `{robots['adres']}` → {_robots_ozeti(robots)}")
        if robots["hata"]:
            satirlar += [
                f"- Hata ayrıntısı: `{robots['hata']}`",
                "- **Sonuç: bu alan adı otomatik taranmaz.** `RobotsBekcisi.izinli_mi`,",
                "  robots.txt okunamadığında `False` döner — temkinli taraf seçilir.",
            ]
        elif robots["dosya"] is None:
            satirlar += [
                "- robots.txt **yok**. RFC 9309: dosya yoksa erişim kısıtlanmamıştır;",
                "  yine de kendi hız sınırımız ve kapsam kısıtlarımız uygulanır.",
            ]
        if robots["dosya"]:
            dosya_adi = Path(robots["dosya"]).name
            satirlar.append(
                f"- Arşiv kopyası: [`{robots['dosya']}`](robots/{dosya_adi}) · "
                f"`sha256:{robots['sha256'][:16]}…`"
            )
        if robots["sitemapler"]:
            satirlar.append(
                "- robots.txt'in beyan ettiği sitemap: "
                + ", ".join(f"`{s}`" for s in robots["sitemapler"])
            )
        satirlar += ["", "| URL | Karar | Uygulanan bekleme |", "|---|---|---|"]
        for karar in alan["kararlar"]:
            satirlar.append(
                f"| `{karar['url']}` | {_karar_metni(robots, karar)} "
                f"| {karar['uygulanan_bekleme_sn']:g} sn |"
            )
        satirlar.append("")

    satirlar += [
        "---",
        "",
        "## Yeniden üretim",
        "",
        "```bash",
        "make kanit-robots        # canlı kontrol; günlüğü ve arşiv kopyalarını yeniler",
        "```",
        "",
        "Ağ yokken (hava boşluğu demosunda) günlük metni kayıtlı JSON'dan üretilir:",
        "",
        "```bash",
        "python tools/robots_kanit.py --cevrimdisi",
        "```",
        "",
        "Günlük **tarihlidir**: banka siteleri robots.txt dosyalarını değiştirir.",
        "Bayatlamasının sorumlusu günlük değil, kontrolü koşmayandır.",
    ]
    return "\n".join(satirlar) + "\n"


def main(argv: list[str] | None = None) -> int:
    # Windows konsolu cp1254 ile açılır; aşağıdaki ✅/⛔ işaretleri orada
    # UnicodeEncodeError fırlatır ve kanıt üreten araç son satırda çöker.
    # Yalnız CLI yolunda yapılır — modül içe aktarıldığında (testler) stdout'a
    # dokunulmaz.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ayristirici = argparse.ArgumentParser(description="robots.txt kontrol günlüğü (G-14)")
    ayristirici.add_argument(
        "--cevrimdisi",
        action="store_true",
        help="ağa çıkma; kayıtlı JSON'dan yalnız Markdown günlüğünü üret",
    )
    secenekler = ayristirici.parse_args(argv)

    if secenekler.cevrimdisi:
        if not GUNLUK_JSON.exists():
            print(f"❌ {GUNLUK_JSON.relative_to(KOK)} yok — önce ağ varken bir kez koşun.")
            return 1
        veri = json.loads(GUNLUK_JSON.read_text(encoding="utf-8"))
    else:
        veri = kontrol_et()
        KANIT_DIZIN.mkdir(parents=True, exist_ok=True)
        GUNLUK_JSON.write_text(
            json.dumps(veri, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    GUNLUK_MD.write_text(gunluk_uret(veri), encoding="utf-8")

    denetlenen = [alan for alan in veri["alanlar"] if not alan.get("atlandi")]
    red = sum(1 for alan in denetlenen for karar in alan["kararlar"] if not karar["izinli"])
    okunamayan = [alan["ad"] for alan in denetlenen if alan["robots"] and alan["robots"]["hata"]]

    print(f"✅ {GUNLUK_MD.relative_to(KOK)} yazıldı ({len(denetlenen)} alan adı denetlendi)")
    if red:
        print(f"   ⛔ {red} URL çekilmiyor (Disallow ya da robots.txt okunamadı).")
    for ad in okunamayan:
        print(f"   ⚠️  robots.txt okunamadı: {ad} — bu alan adı otomatik taranmaz.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
