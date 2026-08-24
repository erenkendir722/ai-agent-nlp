"""Veri kalitesi denetimi — `docs/VERI_KALITESI.md` üretir (G-07).

NEDEN ELLE YAZILAN BİR BELGE DEĞİL:
Jürinin "bankalar sitelerini değiştirirse ne olur?" sorusunun cevabı, elle
yazılmış bir kalite iddiası olamaz — o iddia yazıldığı gün bayatlar. Cevap,
her koşuda yeniden ölçen ve eşiği aşınca sesini yükselten bir rapordur.

Üç kontrol ailesi var; üçü de farklı bir kırılmayı yakalar:

  * AYKIRI DEĞER — çıkarım yanlış alanı doldurdu (indirim oranı kâr payına
    yazıldı gibi). Eleştirmen ajanı bunu yakalayamaz: sayı metinde gerçekten
    geçtiği için halüsinasyon değildir. Yalnız aralık kontrolü yakalar.
  * ÇELİŞKİ — iki alan birbirini yalanlıyor (masrafsız ama tahsis ücreti var).
  * EKSİKLİK — alan boş kaldı. Boşluk tek başına hata değildir; ani ARTIŞI
    hatadır, çünkü sitenin yapısı değişmiş demektir.

Eşikler `--kati` ile bağlayıcı olur (çıkış kodu 1). Varsayılan koşu raporu
üretir ama kırmaz — takım dört kişi, sürekli kırmızı bir depo kimsenin işine
yaramaz. CI ve sunum öncesi denetim `--kati` kullanır.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from src.depolama import cikarim_durumu, tum_kayitlar  # noqa: E402

RAPOR_YOLU = KOK / "docs" / "VERI_KALITESI.md"

# Kâr payı katılım bankalarında AYLIK ilan edilir (bkz. ETIKETLEME_KILAVUZU).
# %5'in üstü ya yıllık orandır ya da başka bir yüzde (indirim, mil) sızmıştır.
AYLIK_KAR_PAYI_TAVANI = 5.0
ASGARI_FINANSMAN = 5_000.0
AZAMI_FINANSMAN = 10_000_000.0
AZAMI_VADE_AY = 360
AZAMI_TAKSIT = 24
AZAMI_BITIS_YIL = 5  # bundan uzak bir bitiş tarihi ayrıştırma hatasıdır

# `diger` oranı için eşik: bu oranın üstü ya toplayıcının kampanya olmayan
# sayfa getirdiğini ya da sınıflandırmanın kırıldığını gösterir.
DIGER_ESIK_ORANI = 0.35


class Bulgu:
    """Tek bir kontrolün sonucu."""

    def __init__(
        self,
        ad: str,
        aciklama: str,
        kayitlar: list,
        esik: int,
        seviye: str = "uyari",
    ) -> None:
        self.ad = ad
        self.aciklama = aciklama
        self.kayitlar = kayitlar
        self.esik = esik
        self.seviye = seviye  # "uyari" | "bilgi"

    @property
    def sayi(self) -> int:
        return len(self.kayitlar)

    @property
    def asildi(self) -> bool:
        return self.seviye == "uyari" and self.sayi > self.esik

    @property
    def isaret(self) -> str:
        if self.seviye == "bilgi":
            return "ℹ️"
        return "🔴" if self.asildi else "✅"


def _tr_sayi(deger: float) -> str:
    """Türkçe binlik ayracı: 5.000 (İngilizce biçim 5,000 okuru yanıltır)."""
    return f"{deger:,.0f}".replace(",", ".")


def _yil_farki(gun: date) -> float:
    return (gun - date.today()).days / 365.25


def aykiri_degerler(kayitlar: list) -> list[Bulgu]:
    """Değer aralığı dışına çıkan alanlar."""

    def suz(kosul) -> list:
        return [k for k in kayitlar if kosul(k)]

    return [
        Bulgu(
            "Kâr payı oranı > %5",
            "Katılım bankaları kâr payını aylık ilan eder. Üstü ya yıllık orandır "
            "ya da başka bir yüzde (indirim, mil, iade) bu alana sızmıştır.",
            suz(
                lambda k: k.kar_payi_orani is not None
                and k.kar_payi_orani > AYLIK_KAR_PAYI_TAVANI
            ),
            esik=0,
        ),
        Bulgu(
            "Kâr payı oranı = 0",
            "Hata DEĞİL sayılır: vade farksız kampanyalarda kâr payı gerçekten "
            "sıfırdır. Sayının ani yükselmesi ayrıştırmanın bozulduğunu gösterir.",
            suz(lambda k: k.kar_payi_orani == 0),
            esik=0,
            seviye="bilgi",
        ),
        Bulgu(
            f"Finansman tutarı < {_tr_sayi(ASGARI_FINANSMAN)} TL",
            "Bu tutarın altı kampanya limiti değil, büyük olasılıkla taksit ya da "
            "ücret rakamıdır.",
            suz(
                lambda k: k.finansman_tutari_max is not None
                and k.finansman_tutari_max < ASGARI_FINANSMAN
            ),
            esik=0,
        ),
        Bulgu(
            f"Finansman tutarı > {_tr_sayi(AZAMI_FINANSMAN)} TL",
            "Bireysel kampanyada beklenmez; dilim tablosundan yanlış hücre "
            "alınmış olabilir.",
            suz(
                lambda k: k.finansman_tutari_max is not None
                and k.finansman_tutari_max > AZAMI_FINANSMAN
            ),
            esik=0,
        ),
        Bulgu(
            f"Vade > {AZAMI_VADE_AY} ay veya < 1",
            "Konut finansmanında bile 360 ay üst sınırdır.",
            suz(
                lambda k: k.vade_ay_max is not None
                and not (1 <= k.vade_ay_max <= AZAMI_VADE_AY)
            ),
            esik=0,
        ),
        Bulgu(
            f"Taksit sayısı > {AZAMI_TAKSIT}",
            "Kart taksitlendirmesinde üst sınır; aşılıyorsa vade ile karışmıştır.",
            suz(
                lambda k: k.taksit_sayisi is not None
                and k.taksit_sayisi > AZAMI_TAKSIT
            ),
            esik=0,
        ),
        Bulgu(
            "İndirim oranı > %100",
            "Tanımsız değer.",
            suz(lambda k: k.indirim_orani is not None and k.indirim_orani > 100),
            esik=0,
        ),
        Bulgu(
            "Kampanya bitişi geçmişte",
            "Süresi dolmuş kampanya karşılaştırmayı yanıltır. Çok eski bir tarih "
            "kampanya tarihi değil, sayfadaki başka bir tarihtir.",
            suz(
                lambda k: k.kampanya_bitis is not None
                and k.kampanya_bitis < date.today()
            ),
            esik=0,
        ),
        Bulgu(
            f"Kampanya bitişi {AZAMI_BITIS_YIL} yıldan uzak",
            "Ayrıştırma hatası göstergesi.",
            suz(
                lambda k: k.kampanya_bitis is not None
                and _yil_farki(k.kampanya_bitis) > AZAMI_BITIS_YIL
            ),
            esik=0,
        ),
    ]


def celiskiler(kayitlar: list) -> list[Bulgu]:
    """Birbirini yalanlayan alanlar."""
    bulgular: list[Bulgu] = [
        Bulgu(
            "Masrafsız işaretli ama tahsis ücreti var",
            "İki alan birbirini yalanlıyor.",
            [
                k
                for k in kayitlar
                if k.masrafsiz_mi is True and (k.tahsis_ucreti or 0) > 0
            ],
            esik=0,
        )
    ]

    # Aynı bankada kâr payı aralığı: geniş aralık ya gerçek ürün çeşitliliğidir
    # ya da bir kayıtta yanlış yüzde vardır. Rapor işaret eder, karar insanındır.
    banka_oran: dict[str, list[float]] = defaultdict(list)
    for k in kayitlar:
        if k.kar_payi_orani is not None:
            banka_oran[k.banka_kodu].append(k.kar_payi_orani)
    genis = [
        (kod, f"{min(o):.2f}", f"{max(o):.2f}", f"{max(o) - min(o):.2f} puan")
        for kod, o in sorted(banka_oran.items())
        if len(o) > 1 and max(o) - min(o) > AYLIK_KAR_PAYI_TAVANI
    ]
    bulgular.append(
        Bulgu(
            f"Banka içi kâr payı aralığı > {AYLIK_KAR_PAYI_TAVANI:.0f} puan",
            "Aynı bankanın kampanyaları arasında bu kadar fark beklenmez.",
            genis,
            esik=0,
        )
    )

    mukerrer: dict[str, int] = defaultdict(int)
    for k in kayitlar:
        mukerrer[k.kaynak_url] += 1
    bulgular.append(
        Bulgu(
            "Aynı URL'den birden çok kayıt",
            "Kimlik URL'den deterministik üretilir; mükerrer varsa toplayıcı aynı "
            "sayfayı iki farklı adresten almıştır.",
            [(u, n) for u, n in mukerrer.items() if n > 1],
            esik=0,
        )
    )
    return bulgular


ALANLAR = (
    "kampanya_turu",
    "hedef_kitle",
    "kar_payi_orani",
    "finansman_tutari_max",
    "vade_ay_max",
    "taksit_sayisi",
    "tahsis_ucreti",
    "odul_miktari",
    "indirim_orani",
    "alisveris_puani",
    "masrafsiz_mi",
    "kampanya_bitis",
)


def eksiklik(kayitlar: list) -> tuple[list[Bulgu], list[tuple[str, int, float]]]:
    """Boş kalan alanlar ve sınıflandırılamayan kayıtlar."""
    bos_tablo = []
    for alan in ALANLAR:
        bos = sum(1 for k in kayitlar if getattr(k, alan, None) is None)
        bos_tablo.append((alan, bos, bos / len(kayitlar) * 100))
    bos_tablo.sort(key=lambda satir: -satir[2])

    bulgular = [
        Bulgu(
            "Hiçbir alanı çıkarılamayan kayıt",
            "Doluluk sıfırsa sayfa büyük olasılıkla kampanya değildir ya da "
            "sitenin yapısı değişmiştir.",
            [k for k in kayitlar if (k.doluluk_orani or 0) == 0],
            esik=0,
        ),
        Bulgu(
            "Kampanya türü `diger`",
            "Sınıflandırılamayan kayıt. Oranın yükselmesi ya toplayıcının kampanya "
            "olmayan sayfa getirdiğini ya da sınıflandırmanın kırıldığını gösterir.",
            [k for k in kayitlar if k.kampanya_turu == "diger"],
            esik=int(len(kayitlar) * DIGER_ESIK_ORANI),
        ),
    ]
    return bulgular, bos_tablo


def banka_kapsami(kayitlar: list) -> list[tuple[str, str, int, float, int]]:
    """Banka başına kampanya sayısı, doluluk ve `diger` oranı."""
    veri: dict[str, list] = defaultdict(list)
    for k in kayitlar:
        veri[k.banka_kodu].append(k)
    satirlar = []
    for kod, kayit_listesi in sorted(veri.items()):
        dig = sum(1 for k in kayit_listesi if k.kampanya_turu == "diger")
        ort = sum(k.doluluk_orani or 0 for k in kayit_listesi) / len(kayit_listesi)
        satirlar.append((kod, kayit_listesi[0].banka_adi, len(kayit_listesi), ort, dig))
    return satirlar


def _kokenlik_notu(durum: dict) -> list[str]:
    """Raporun EN BAŞINA giden bayatlık uyarısı — `make eval` ile aynı sözleşme."""
    kosu = durum.get("kosu")
    if not durum.get("bayat"):
        return [
            f"> ✅ **Güncel.** Çıkarım {kosu['zaman']:%d.%m.%Y %H:%M}'de "
            f"`{kosu['yapilandirma']}` yapılandırmasıyla koştu "
            f"({kosu['kayit_sayisi']} kayıt) ve o tarihten beri çıkarım kodu değişmedi.",
            "",
        ]
    return [
        "> 🔴 **BAYAT — bu rapor eski bir çıkarımı anlatıyor.**",
        f"> {durum.get('sebep', '')}",
        "> Düzeltmek için: `make extract && make veri-kalitesi`.",
        "",
    ]


def _ornek_satiri(ornek) -> str:
    if isinstance(ornek, tuple):
        return "| " + " | ".join(str(x)[:60] for x in ornek) + " |"
    deger = ornek.kar_payi_orani
    if deger is None:
        deger = ornek.kampanya_bitis
    if deger is None:
        deger = f"doluluk %{(ornek.doluluk_orani or 0) * 100:.0f}"
    return f"| {ornek.banka_kodu} | {deger} | …{ornek.kaynak_url[-56:]} |"


def rapor_yaz(kayitlar: list, durum: dict) -> str:
    ayk = aykiri_degerler(kayitlar)
    cel = celiskiler(kayitlar)
    eks, bos_tablo = eksiklik(kayitlar)
    tum = ayk + cel + eks
    asilan = [b for b in tum if b.asildi]

    s = [
        "# Veri Kalitesi Raporu",
        "",
        f"_Otomatik üretildi: {datetime.now():%d.%m.%Y %H:%M} · `make veri-kalitesi`_",
        "",
        "> Bu dosya elle düzenlenmez. `make veri-kalitesi` her koşuda yeniden üretir.",
        "",
    ]
    s += _kokenlik_notu(durum)
    s += [
        f"**{len(kayitlar)} kampanya denetlendi.** "
        f"{len(asilan)} kontrol eşiği aştı, {len(tum) - len(asilan)} kontrol temiz.",
        "",
        "## Özet",
        "",
        "| | Kontrol | Bulgu | Eşik |",
        "|---|---|---|---|",
    ]
    s += [f"| {b.isaret} | {b.ad} | {b.sayi} | {b.esik} |" for b in tum]
    s.append("")

    for baslik, grup in (
        ("Aykırı değerler", ayk),
        ("Çelişkiler", cel),
        ("Eksiklik", eks),
    ):
        s += [f"## {baslik}", ""]
        for b in grup:
            s += [f"### {b.isaret} {b.ad} — {b.sayi} kayıt", "", b.aciklama, ""]
            if b.sayi and b.seviye == "uyari":
                s += ["| Banka | Değer | Kaynak |", "|---|---|---|"]
                s += [_ornek_satiri(o) for o in b.kayitlar[:5]]
                if b.sayi > 5:
                    s.append(f"| … | | *{b.sayi - 5} kayıt daha* |")
                s.append("")

    s += ["## Alan doluluk oranları", "", "| Alan | Boş | Boş oranı |", "|---|---|---|"]
    s += [f"| `{alan}` | {bos} | %{oran:.0f} |" for alan, bos, oran in bos_tablo]

    s += [
        "",
        "## Banka kapsamı",
        "",
        "Dengesizlik gizlenmez: bir bankadan 100, diğerinden 16 kampanya varsa "
        "karşılaştırma yanlıdır ve bunu bilerek raporlamak fark etmemekten iyidir.",
        "",
        "| Kod | Banka | Kampanya | Ort. doluluk | `diger` |",
        "|---|---|---|---|---|",
    ]
    for kod, ad, n, ort, dig in banka_kapsami(kayitlar):
        s.append(f"| {kod} | {ad} | {n} | %{ort * 100:.0f} | {dig} (%{dig / n * 100:.0f}) |")
    s.append("")
    return "\n".join(s)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Veri kalitesi denetimi (G-07)")
    ap.add_argument(
        "--kati", action="store_true", help="eşik aşılırsa çıkış kodu 1 döner"
    )
    args = ap.parse_args(argv[1:])

    kayitlar = tum_kayitlar()
    if not kayitlar:
        print("❌ Veritabanı boş. Önce `make crawl && make extract` çalıştırın.")
        return 1

    durum = cikarim_durumu()
    RAPOR_YOLU.write_text(rapor_yaz(kayitlar, durum), encoding="utf-8")

    tum = aykiri_degerler(kayitlar) + celiskiler(kayitlar) + eksiklik(kayitlar)[0]
    asilan = [b for b in tum if b.asildi]

    print(f"Rapor yazıldı: {RAPOR_YOLU.relative_to(KOK)}")
    print(f"  {len(kayitlar)} kampanya · {len(asilan)} kontrol eşiği aştı")
    for b in asilan:
        print(f"  🔴 {b.ad}: {b.sayi} (eşik {b.esik})")
    if durum.get("bayat"):
        print(f"  🔴 BAYAT — {durum.get('sebep')}")
    return 1 if (args.kati and asilan) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
