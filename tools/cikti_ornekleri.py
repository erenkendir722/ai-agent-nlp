"""Model çıktı örnekleri — dokümantasyon başlığı 9 (ES-15).

    python tools/cikti_ornekleri.py     # docs/CIKTI_ORNEKLERI.md üret

NEDEN ELLE YAZILMIYOR:
    Bu dosyanın tek değeri GERÇEK olmasıdır. Elle yazılan bir çıktı örneği,
    sistem değiştiğinde sessizce yalan söylemeye başlar — 15 Ağustos sürümü
    tam olarak böyle bayatladı: 96 kampanyalık, yerel 4B modelle koşulmuş
    örnekler, 1024 kayıtlık EVREN koşusundan sonra da dosyada duruyordu.

    Artık örnekler veritabanından SEÇİLİR ve alıntılarıyla birlikte basılır.
    Sistem değişince `make cikti-ornekleri` yeniden koşulur.

ÖRNEKLER NASIL SEÇİLİYOR (şartname madde 6: "model çıktılarının örnekleri"):
    1. temiz     — en çok alanı dolu kayıt
    2. sayısal   — kâr payı + vade + ücret birlikte çıkmış kayıt
    3. eksik     — az alan dolu; sistemin "Belirtilmemiş" dediği yer
    4. dolaylı   — "avantajlı / özel oranlı / düşük maliyetli" ifadesi geçen
    5. uygunluk  — uygunluk koşulu çıkarılmış kayıt (A-08)
    Seçim deterministiktir: aynı veritabanı aynı örnekleri verir.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.depolama import VERITABANI_URL, kampanyalari_oku  # noqa: E402
from src.schema import ALAN_ADLARI, ALAN_ETIKETLERI, Kampanya  # noqa: E402

KOK = Path(__file__).resolve().parents[1]
CIKTI = KOK / "docs" / "CIKTI_ORNEKLERI.md"

DOLAYLI = ("avantajlı", "özel oranlı", "düşük maliyetli", "cazip", "uygun kâr payı")

MADDE_11_METNI = (
    "Yeni ev sahibi olmak isteyen müşterilerimize özel %1,89 kâr payı oranı ile "
    "120 aya kadar konut finansmanı fırsatı sunulmaktadır. Kampanya kapsamında "
    "50.000 TL'ye kadar dosya masrafı alınmamaktadır. Kampanya 31 Aralık 2026 "
    "tarihine kadar geçerlidir."
)


def _dolu_sayisi(k: Kampanya) -> int:
    return sum(1 for a in k.cikarilan_alanlar().values() if a.var_mi)


def _kirp(metin: str, n: int = 420) -> str:
    duz = " ".join((metin or "").split())
    return duz[:n] + ("…" if len(duz) > n else "")


def _alan_tablosu(k: Kampanya) -> list[str]:
    satirlar = [
        "| Alan | Değer | Birim | Yöntem | Güven |",
        "|---|---|---|---|---|",
    ]
    for ad in ALAN_ADLARI:
        alan = getattr(k, ad)
        if not alan.var_mi:
            continue
        deger = getattr(alan.deger, "value", alan.deger)
        satirlar.append(
            f"| `{ad}` | {deger} | {alan.birim.value if alan.birim else '—'} "
            f"| {alan.yontem} | {alan.guven:.2f} |"
        )
    bos = [ALAN_ETIKETLERI.get(a, a) for a in ALAN_ADLARI if not getattr(k, a).var_mi]
    if bos:
        satirlar += ["", f"**Belirtilmemiş ({len(bos)} alan):** {', '.join(bos)}"]
    return satirlar


# Kanıt alıntısı SAYISAL/TARİHSEL alanlar için anlamlıdır: değerin metinde
# birebir geçtiği yeri gösterir. Sınıflandırma etiketlerinin (`kampanya_turu`)
# alıntısı sayfanın ilk paragrafı olur ve hiçbir şey kanıtlamaz — okuyucuya
# zayıf bir kanıt göstermek, kanıt göstermemekten kötüdür.
KANIT_ALANLARI = (
    "kar_payi_orani",
    "finansman_tutari_max",
    "vade_ay_max",
    "tahsis_ucreti",
    "odul_miktari",
    "indirim_orani",
    "kampanya_bitis",
)


def _deger_alintida_mi(alan) -> bool:
    """Alıntı, değerin kendisini içeriyor mu?

    İçermiyorsa o satır KANIT DEĞİLDİR. Değerin geçmediği bir cümleyi "kanıt"
    diye göstermek, kanıt göstermemekten kötüdür: okuyucu bakar, sayıyı bulamaz
    ve haklı olarak tüm zincirden şüphe eder. (Böyle bir satır 26 Ağustos'ta
    yakalandı: dilim tablosundan türeyen `finansman_tutari_max` değerinin
    alıntısı, tablonun BAŞKA bir satırıydı.)
    """
    alinti = (alan.kaynak.alinti if alan.kaynak else "") or ""
    deger = alan.deger
    if not isinstance(deger, int | float) or isinstance(deger, bool):
        return False
    tam = int(deger) if float(deger).is_integer() else None
    adaylar = {f"{deger:g}".replace(".", ",")}
    if tam is not None:
        adaylar |= {str(tam), f"{tam:,}".replace(",", ".")}
    return any(a in alinti for a in adaylar)


def _kanit_satirlari(k: Kampanya, en_fazla: int = 3) -> list[str]:
    satirlar: list[str] = []
    for ad in KANIT_ALANLARI:
        alan = getattr(k, ad)
        if alan.var_mi and alan.kaynak and alan.kaynak.alinti and _deger_alintida_mi(alan):
            satirlar.append(f"- `{ad}` ← «{_kirp(alan.kaynak.alinti, 180)}»")
        if len(satirlar) >= en_fazla:
            break
    return satirlar


def _ornek_bolumu(baslik: str, aciklama: str, k: Kampanya) -> list[str]:
    parcalar = [
        f"## {baslik}",
        "",
        aciklama,
        "",
        f"**Kaynak:** {k.banka_adi} · [{k.kaynak_url}]({k.kaynak_url}) · "
        f"çekim {k.cekim_tarihi:%d.%m.%Y}",
        "",
        "**Girdi (ham metinden):**",
        "",
        f"> {_kirp(k.ham_metin)}",
        "",
        "**Yapısal çıktı:**",
        "",
        *_alan_tablosu(k),
        "",
    ]
    kanit = _kanit_satirlari(k)
    if kanit:
        parcalar += ["**Kanıt zinciri (alıntılar):**", "", *kanit, ""]
    if k.uygunluk is not None and k.uygunluk.kisit_var_mi():
        u = k.uygunluk
        kisitlar = []
        if u.musteri_tipi:
            kisitlar.append("müşteri tipi: " + ", ".join(h.value for h in u.musteri_tipi))
        if u.segment_detayi:
            kisitlar.append("segment: " + ", ".join(u.segment_detayi))
        if u.min_tutar is not None:
            kisitlar.append(f"asgari tutar: {u.min_tutar:,.0f} TL".replace(",", "."))
        if u.max_tutar is not None:
            kisitlar.append(f"azami tutar: {u.max_tutar:,.0f} TL".replace(",", "."))
        if u.max_vade_ay is not None:
            kisitlar.append(f"azami vade: {u.max_vade_ay} ay")
        if u.zorunlu_urun:
            kisitlar.append("zorunlu ürün: " + ", ".join(u.zorunlu_urun))
        parcalar += ["**Uygunluk koşulları (muhakeme ajanının girdisi):**", "",
                     *[f"- {s}" for s in kisitlar], ""]
    return parcalar


def _madde_11() -> list[str]:
    """Şartnamenin kendi örneği — KURAL katmanı, ağsız ve deterministik."""
    from src.extraction.uzlastirici import kampanya_cikar
    from src.schema import HamKayit

    kayit = HamKayit(
        banka_kodu="0000",
        banka_adi="A Bankası (şartname örneği)",
        url="https://sartname.ornek/madde-11",
        cekim_tarihi=datetime(2026, 8, 26),
        http_durum=200,
        govde_metin=MADDE_11_METNI,
    )
    kampanya, _ = kampanya_cikar(kayit, kural_kullan=True, llm_kullan=False)
    return [
        "## 1. Şartnamenin kendi örneği (madde 11, A Bankası)",
        "",
        "Şartname üç banka metni ve bunlardan çıkarılmasını beklediği tabloyu veriyor.",
        "Aşağıdaki çıktı **yalnız kural katmanıyla** üretildi: ağ gerektirmez, her",
        "koşuda birebir aynıdır, yani jüri kendi makinesinde tekrarlayabilir.",
        "",
        "**Girdi:**",
        "",
        f"> {MADDE_11_METNI}",
        "",
        "**Çıktı:**",
        "",
        *_alan_tablosu(kampanya),
        "",
        "> Not: «50.000 TL'ye kadar dosya masrafı **alınmamaktadır**» cümlesi 15",
        "> Ağustos'a kadar 50.000 TL'lik bir tahsis ücreti olarak okunuyordu.",
        "> Olumsuzluk kipi (`-mAktAdır`) sözlüğe eklendi; `tests/test_kural.py::",
        "> TestSartnameMadde11` bu davranışı sabitler.",
        "",
    ]


def calistir(url: str = VERITABANI_URL) -> int:
    kampanyalar = list(kampanyalari_oku(url))
    if not kampanyalar:
        print(" Veritabanı boş. Önce `make extract` çalıştırın.")
        return 1

    sirali = sorted(kampanyalar, key=lambda k: (-_dolu_sayisi(k), k.kampanya_id))
    secilen: dict[str, Kampanya] = {}

    def _sec(anahtar: str, adaylar: list[Kampanya], sira: int = 0) -> None:
        """Aynı kaydı iki örnek diye göstermek örnek çeşitliliğini yok ederdi."""
        alinan = {k.kampanya_id for k in secilen.values()}
        kalan = [k for k in adaylar if k.kampanya_id not in alinan]
        if kalan:
            secilen[anahtar] = kalan[min(sira, len(kalan) - 1)]

    _sec("temiz", sirali)
    _sec(
        "sayisal",
        [
            k for k in sirali
            if k.kar_payi_orani.var_mi and k.vade_ay_max.var_mi and k.tahsis_ucreti.var_mi
        ],
    )
    # DOLAYLI ÖRNEK — asıl gösterilmek istenen davranış «sayı uydurmama».
    # Bu yüzden önce, dolaylı ifadesi olan AMA oranı yazmayan kayıt aranır:
    # orada `kar_payi_orani` boş kalır ve ifade `kampanya_avantaji`'na yazılır.
    dolayli = [k for k in sirali if any(d in (k.ham_metin or "").lower() for d in DOLAYLI)]
    _sec("dolayli", [k for k in dolayli if not k.kar_payi_orani.var_mi] or dolayli)
    eksik = [k for k in sirali if 1 <= _dolu_sayisi(k) <= 3]
    _sec("eksik", eksik, len(eksik) // 2)
    _sec(
        "uygunluk",
        [k for k in sirali if k.uygunluk is not None and k.uygunluk.zorunlu_urun],
    )

    parcalar = [
        "# Model Çıktılarının Örnekleri",
        "",
        f"_Otomatik üretildi: {datetime.now():%d.%m.%Y %H:%M} · `make cikti-ornekleri`_",
        "",
        "**Şartname madde 6**, proje dokümantasyonunda *«model çıktılarının örnekleri»*",
        "başlığını zorunlu tutuyor. Aşağıdaki çıktıların tamamı **işlenmiş",
        f"veritabanından** ({len(kampanyalar)} kayıt) seçilmiştir; hiçbiri elle yazılmadı",
        "veya güzelleştirilmedi. Her tabloda değerin hangi katmandan geldiği",
        "(`kural` / `llm` / `hibrit`) ve güven skoru yazar.",
        "",
        "Yeniden üretmek için: `make cikti-ornekleri`",
        "",
        "---",
        "",
        *_madde_11(),
        "---",
        "",
    ]

    basliklar = [
        ("temiz", "2. Temiz kayıt — alanların çoğu doldu",
         "Sayfada bilgi açıkça yazılıysa sistem alanların çoğunu çıkarır."),
        ("sayisal", "3. Sayısal alanlar birlikte — kâr payı, vade ve ücret",
         "Şartname 5.3'ün istediği sayısal alanların aynı kayıtta çıkması."),
        ("dolayli", "4. Dolaylı ifade — «avantajlı / özel oranlı»",
         "Şartname 5.2 bu ifadelerin yorumlanmasını istiyor. **Sistem sayı "
         "uydurmaz:** metinde sayı varsa çıkarılır, yoksa `kar_payi_orani` "
         "«Belirtilmemiş» kalır ve ifadenin kendisi `kampanya_avantaji` alanına "
         "yazılır. Aşağıdaki kayıt bu davranışı gösterir."),
        ("eksik", "5. Eksik bilgili kayıt — «Belirtilmemiş» demek",
         "Kampanya sayfası az bilgi veriyorsa sistem **boş bırakır**. Şartname "
         "madde 11'in tablosu da bu ifadeyi kullanıyor; uydurmak yerine bilmediğini "
         "söylemek doğru davranıştır."),
        ("uygunluk", "6. Uygunluk koşulu çıkarılmış kayıt",
         "Kampanyanın KİME açık olduğu yapısal alana çevrilir; müşteri profili "
         "ekranındaki muhakeme ajanı bu kısıtları çözer."),
    ]
    for anahtar, baslik, aciklama in basliklar:
        if anahtar in secilen:
            parcalar += _ornek_bolumu(baslik, aciklama, secilen[anahtar]) + ["---", ""]

    parcalar += [
        "## Bu örnekler neyi kanıtlar",
        "",
        "| İddia | Örnekte görülen |",
        "|---|---|",
        "| Kanıtsız değer üretilmez | Her tabloda `yöntem` ve `güven`; alıntılar bölümünde kaynak cümle |",
        "| Sistem sayı uydurmaz | Eksik bilgili kayıtta alanlar boş bırakılır, doldurulmaz |",
        "| Hibrit çıkarım | Aynı kayıtta `kural` ve `llm` yöntemli alanlar yan yana |",
        "| Yapısal uygunluk | Uygunluk bölümündeki kısıtlar serbest metinden değil, alanlardan gelir |",
        "",
        "Ölçülmüş sonuçlar: [`SONUCLAR.md`](SONUCLAR.md) · Hata analizi: "
        "[`HATA_ANALIZI.md`](HATA_ANALIZI.md)",
        "",
    ]

    CIKTI.write_text("\n".join(parcalar), encoding="utf-8")
    print(f" {CIKTI.relative_to(KOK)} yazıldı ({len(secilen) + 1} örnek)")
    for anahtar, kampanya in secilen.items():
        print(f"   {anahtar:9} {kampanya.kampanya_id}  ({_dolu_sayisi(kampanya)} dolu alan)")
    return 0


if __name__ == "__main__":
    raise SystemExit(calistir())
