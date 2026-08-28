"""`data/seed/finansman_urlleri.txt` içindeki EKSİK sayfaları çeker.

NEDEN AYRI BİR ARAÇ — 28 Ağustos'ta ölçüldü:
Listedeki 149 finansman URL'inin **41'i** envanterde yoktu. Sebebi toplama
aşamasındaydı; üç ayrı biçimde aynı hata:

    Vakıf Katılım (0210)   27 eksik  `urun_bolumleri` yalnız `.../finansmanlar`,
                                     alt ürünler KATEGORİ sayfalarından linkli
                                     ve `urun_urlleri()` tek seviye geziyor
    Dünya Katılım (0214)    7 eksik  `urun_bolumleri` HİÇ tanımlı değil
    Türkiye Finans (0206)   6 eksik  `/tr-tr/ticari` kökü yok
    Albaraka (0203)         1 eksik  sayfa 404 — ölü, listede yorumda

NEDEN TAM YENİDEN TOPLAMA DEĞİL:
`toplayici.kaydi_yaz` kimliğe göre ÜZERİNE YAZAR. `make crawl --banka 0210`
eksikleri getirirdi ama mevcut sayfaları da yeniden çeker ve gövdelerini
tazelerdi. Altın setin 92 kaydının **29'u** tam bu üç bankada (0206:18 ·
0210:9 · 0214:2); gövdeleri değişirse `make eval` ölçüm zemini kayar ve iki
koşunun farkı «iyileşme» sanılır. Bu yüzden buradaki kapı DAR:

    DİSKTE JSON'U OLAN URL ATLANIR. Mevcut kaydın üzerine YAZILMAZ.

Nöbetçisi `tests/test_finansman_cek.py::test_diskte_olan_url_atlanir`.

NEDEN «TÜMÜNÜ GÖSTER» BUTONUNA TIKLANMIYOR:
Vakıf'ın finansman sayfalarında içeriğin bir kısmı `btn btn-link
mask-area-open-btn` düğmesinin arkasında GÖRÜNMÜYOR. Ölçüldü: düğme salt CSS
kırpmasıdır, maskelenen metin `page_source` içinde eksiksiz duruyor ve
trafilatura zaten çıkarıyor — `konut-finansmani` sayfası httpx ile 6001
karakter, depodaki Selenium kaydıyla BİREBİR aynı. Kazıyıcı görüntü alanını
değil DOM'u okuyor. Tıklayan kod hiçbir şey kazandırmadan sayfa başına 2-3
etkileşim maliyeti eklerdi.

NEDEN SELENIUM, httpx DEĞİL:
Dünya Katılım'ın finansman sayfaları httpx'e 6971 karakterlik **çerez
aydınlatma metnini** döndürüyor. `acilir_pencereleri_kapat()` şart, o da
tarayıcı ister. Diğer iki banka httpx ile de çalışırdı; ikinci bir çekme
yolu yazmamak için üçü de aynı yoldan geçer.

GÜVENLİK: Varsayılan koşu ÇEKMEZ, ne çekileceğini gösterir. Çekmek için
`--uygula` gerekir (`make finansman-cek uygula=1`).
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

KOK = Path(__file__).resolve().parent.parent
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from src.collector.toplayici import (  # noqa: E402
    HAM_DIZIN,
    NezaketSirasi,
    RobotsBekcisi,
    bankalari_yukle,
    kaydi_yaz,
)
from src.schema import Banka  # noqa: E402

URL_LISTESI = KOK / "data" / "seed" / "finansman_urlleri.txt"


def arama_anahtari(url: str) -> str:
    """İki adresin AYNI sayfayı gösterip göstermediğini söyleyen anahtar.

    Karşılaştırma ham metinle yapılamaz: envanterdeki adres `https://www.`
    ile yazılmışken listede `http://` (Albaraka'da bir satır) ya da `www`siz
    (Vakıf'ın `seed_urls`'ü) duruyor; Türkçe karakterli yollar bir yerde
    yüzde kodlu, bir yerde çözülmüş geliyor. Anahtar üretilmezse aynı sayfa
    «eksik» sanılıp ikinci kez çekilir — yani tam da kaçınılmak istenen
    üzerine yazma.

    NFC şart: `ğ` tek kod noktası olarak da (U+011F), `g`+birleşen olarak da
    yazılabiliyor ve ikisi görsel olarak ayırt edilemez.
    """
    p = urlsplit(unicodedata.normalize("NFC", unquote(url.strip())))
    konak = p.netloc.lower().removeprefix("www.")
    return konak + p.path.rstrip("/").lower()


def urlleri_oku(yol: Path = URL_LISTESI) -> list[str]:
    """Liste dosyasını okur. `#` yorum, boş satır atlanır, sıra korunur."""
    if not yol.exists():
        raise FileNotFoundError(f"URL listesi yok: {yol}")
    gorulen: set[str] = set()
    urller: list[str] = []
    for satir in yol.read_text(encoding="utf-8").splitlines():
        u = satir.strip()
        if not u or u.startswith("#"):
            continue
        anahtar = arama_anahtari(u)
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        urller.append(u)
    return urller


def envanter_anahtarlari(dizin: Path = HAM_DIZIN) -> set[str]:
    """`data/raw` içindeki her kaydın arama anahtarı.

    Gövde okunmaz — yalnız `url` alanı gerekiyor ve 979 dosyanın HTML'ini
    yüklemek (bkz. `ham_kayitlari_oku`) bu iş için gereksiz.
    """
    anahtarlar: set[str] = set()
    for yol in dizin.rglob("*.json"):
        try:
            veri = json.loads(yol.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        url = veri.get("url")
        if url:
            anahtarlar.add(arama_anahtari(url))
    return anahtarlar


def banka_eslemesi(bankalar: list[Banka]) -> dict[str, Banka]:
    """Alan adı -> banka. `banks.yaml` · `site` alanından türer.

    Elle yazılmış ikinci bir alan adı listesi tutulmaz: `site` zaten kayıt
    defterinde ve bir banka adres değiştirdiğinde tek yerde düzeltilir.
    """
    esleme: dict[str, Banka] = {}
    for banka in bankalar:
        if not banka.site:
            continue
        konak = urlsplit(banka.site).netloc.lower().removeprefix("www.")
        if konak:
            esleme[konak] = banka
    return esleme


def bankayi_bul(url: str, esleme: dict[str, Banka]) -> Banka | None:
    """URL'in alan adından bankayı çözer; alt alan adlarını da kapsar.

    Alt alan adı gerçek: Kuveyt Türk'ün 12 kaydı `saglamkart.kuveytturk.com.tr`
    altında. Bu araç bugün o adresleri çekmiyor ama eşleme dar yazılırsa
    liste büyüdüğünde sessizce «banka bulunamadı» derdi.
    """
    konak = urlsplit(url).netloc.lower().removeprefix("www.")
    if konak in esleme:
        return esleme[konak]
    for bilinen, banka in esleme.items():
        if konak.endswith("." + bilinen):
            return banka
    return None


def planla(
    urller: list[str],
    esleme: dict[str, Banka],
    envanter: set[str],
) -> tuple[dict[str, list[str]], list[str], list[str]]:
    """Çekilecekleri banka koduna göre gruplar.

    Döner: (banka kodu -> URL'ler, zaten var olanlar, banka bulunamayanlar)
    """
    cekilecek: dict[str, list[str]] = {}
    var: list[str] = []
    eslesmeyen: list[str] = []
    for url in urller:
        if arama_anahtari(url) in envanter:
            var.append(url)
            continue
        banka = bankayi_bul(url, esleme)
        if banka is None:
            eslesmeyen.append(url)
            continue
        cekilecek.setdefault(banka.kod, []).append(url)
    return cekilecek, var, eslesmeyen


def cek(
    cekilecek: dict[str, list[str]],
    bankalar: list[Banka],
    *,
    gorunmez: bool | None = None,
    dizin: Path = HAM_DIZIN,
) -> tuple[list[tuple[str, str]], list[str]]:
    """Planı yürütür. Döner: (yazılanlar [(kimlik, url)], çekilemeyenler).

    selenium yalnız BURADA içeri alınır — kuru koşu ve testler tarayıcı
    bağımlılığı olmadan çalışsın diye (`toplayici.topla` ile aynı gerekçe).
    """
    from src.collector.kaziyicilar import kaziyici_sinifi
    from src.collector.tarayici import surucu_olustur

    kod_banka = {b.kod: b for b in bankalar}
    bekci = RobotsBekcisi()
    sira = NezaketSirasi(bekci)
    yazilan: list[tuple[str, str]] = []
    basarisiz: list[str] = []

    print("Tarayıcı başlatılıyor...")
    surucu, bekleme = surucu_olustur(gorunmez=gorunmez)
    try:
        for kod, urller in sorted(cekilecek.items()):
            banka = kod_banka[kod]
            sinif = kaziyici_sinifi(kod)
            if sinif is None:
                print(f"  {banka.kisa_ad}: kazıyıcı yok (kod {kod}) — atlanıyor")
                basarisiz += urller
                continue
            kaziyici = sinif(banka, surucu, bekleme, bekci=bekci, sira=sira)
            print(f"\n{banka.kisa_ad} ({kod}) — {len(urller)} sayfa")
            for sayi, url in enumerate(urller, 1):
                kayit = kaziyici.sayfa_kaydi(url)
                if kayit is None:
                    # `sayfa_kaydi` None dönerse sebebi zaten günlüğe düştü
                    # (robots reddi · sayfa yüklenemedi · gövde eşiğin altında).
                    print(f"  {sayi:>3}/{len(urller)}  ATLANDI  ...{url[-58:]}")
                    basarisiz.append(url)
                    continue
                kaydi_yaz(kayit, dizin)
                kimlik = kayit.kampanya_id()
                yazilan.append((kimlik, url))
                print(
                    f"  {sayi:>3}/{len(urller)}  {kimlik}  "
                    f"{len(kayit.govde_metin):>5} krk  ...{url[-42:]}"
                )
    finally:
        print("\nTarayıcı kapatılıyor...")
        surucu.quit()
    return yazilan, basarisiz


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Listede olup envanterde olmayan finansman sayfalarını çek"
    )
    ap.add_argument(
        "--uygula", action="store_true", help="gerçekten çek (varsayılan: yalnız göster)"
    )
    ap.add_argument(
        "--gorunmez", action="store_true", help="tarayıcıyı görünmez kipte aç"
    )
    ap.add_argument(
        "--liste", type=Path, default=URL_LISTESI, help="URL listesi dosyası"
    )
    args = ap.parse_args(argv[1:])

    urller = urlleri_oku(args.liste)
    bankalar = bankalari_yukle()
    esleme = banka_eslemesi(bankalar)
    envanter = envanter_anahtarlari()
    cekilecek, var, eslesmeyen = planla(urller, esleme, envanter)

    toplam = sum(len(v) for v in cekilecek.values())
    kod_ad = {b.kod: b.kisa_ad for b in bankalar}

    print(f"Liste          : {len(urller)} URL  ({args.liste})")
    print(f"Envanterde var : {len(var)}  — atlanacak, üzerine YAZILMAZ")
    print(f"Çekilecek      : {toplam}")
    if eslesmeyen:
        print(f"Banka bulunamadı: {len(eslesmeyen)}")
        for url in eslesmeyen:
            print(f"    {url}")
    print()

    if not toplam:
        print("Eksik sayfa yok — envanter listeyle örtüşüyor.")
        return 0

    for kod, banka_urlleri in sorted(cekilecek.items()):
        print(f"  {kod_ad.get(kod, kod)} ({kod}): {len(banka_urlleri)}")
        for url in banka_urlleri:
            print(f"      {urlsplit(url).path}")
    print()

    if not args.uygula:
        print("Çekmek için: make finansman-cek uygula=1")
        print("  (Windows: .venv/Scripts/python.exe -m tools.finansman_cek --uygula)")
        return 0

    yazilan, basarisiz = cek(cekilecek, bankalar, gorunmez=args.gorunmez or None)

    print()
    print(f"YAZILAN: {len(yazilan)} kayıt")
    if basarisiz:
        print(f"ÇEKİLEMEDİ: {len(basarisiz)}")
        for url in basarisiz:
            print(f"    {url}")
    if yazilan:
        kimlikler = " ".join(kimlik for kimlik, _ in yazilan)
        print()
        print("Sırada — YALNIZ yeni kimlikler için çıkarım:")
        print(f"  python -m src.boru_hatti extract --kimlik {kimlikler}")
        print()
        print("Ardından (korpus izi değişti): python -m src.boru_hatti vektor")
        print()
        print("NOT: `--banka` ile çıkarım YAPMAYIN — o bankaların TÜM kayıtlarını")
        print("     yeniden çıkarır ve altın setteki 29 satırın değerleri oynar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
