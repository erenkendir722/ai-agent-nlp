"""Terim sözlüğü biçim ve içerik testleri (G-09).

`docs/TERIM_SOZLUGU.md` iki işi birden görüyor: insan başvuru belgesi ve
LLM isteminin kaynağı. İkincisi yüzünden dosyanın biçimi bir SÖZLEŞMEDİR —
G-10'da `src/extraction/llm.py` içindeki `TERIMLER` sabiti bu dosyadan
üretilecek. Biri tabloya beşinci sütun eklerse ya da başlığı değiştirirse
ayrıştırma sessizce boş liste döndürür ve istem alan bilgisi olmadan koşar:
çıkarım bozulur ama hiçbir şey hata vermez.

Bu testler o sessiz bozulmayı gürültülü hâle getirir.

Şartname 5.5 ayrıca sözlüğün kapsamını bağlıyor; `G-09` en az 60 terim
istiyor. Terim sayısının eşiği de burada denetleniyor.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.preprocessing.normalizasyon import tr_kucult

KOK = Path(__file__).resolve().parents[1]
SOZLUK = KOK / "docs" / "TERIM_SOZLUGU.md"

ASGARI_TERIM = 60
"""G-09'un bitti sayılma ölçütü. Düşürülürse görev şartı ihlal edilir."""

TERIM_TABLOSU_BASLIGI = "| Terim | Tanım | Sistemdeki karşılığı | İstem |"
"""Terim tablolarının değişmez başlığı — ayrıştırıcının tutunduğu yer.

Sözlükte başka tablolar da var ("İfade | Sistem ne yapar", "Karışan | ...",
§10'un ölçüm tabloları). Onlar terim tablosu DEĞİLDİR ve sayıma girmemelidir;
ayrım bu başlıkla yapılıyor."""

AYIRICI = re.compile(r"\|[\s:|-]+\|")
"""Markdown tablo ayıracı satırı: `|---|---|`."""


# ---------------------------------------------------------------------------
# Ayrıştırma — G-10 bu sözleşmeye yaslanacak
# ---------------------------------------------------------------------------


def _satirlar() -> list[str]:
    return SOZLUK.read_text(encoding="utf-8").splitlines()


def resmi_terimler(satirlar: list[str]) -> list[str]:
    """§1'deki beş resmî kavram — `### ` başlıkları.

    Yalnız `## 1.` ile `## 2.` arası taranır: §10'da da `### ` başlıkları var
    ve onlar terim değil, bölüm başlığıdır.

    Başlık EŞ ANLAMLI YAZIM taşıyabilir («Finansman Maliyeti / Toplam
    Maliyet»); burada ayrılmaz, çünkü bu liste TERİM SAYAR ve iki yazım tek
    terimdir. Yazımları ayıran yer `_resmi_yazimlar` — şartname 5.5 denetimi
    oradan geçer.
    """
    icinde, bulunan = False, []
    for satir in satirlar:
        if satir.startswith("## 1."):
            icinde = True
            continue
        if satir.startswith("## ") and icinde:
            break
        if icinde and satir.startswith("### "):
            bulunan.append(satir[4:].strip())
    return bulunan


def _resmi_yazimlar(satirlar: list[str]) -> set[str]:
    """§1 başlıklarındaki BÜTÜN yazımlar — `terim_sozlugu._adlari_ayir` kuralı.

    Eğik çizgi sözlükte eş anlamlı yazımları ayırır ve ayrıştırıcı da öyle
    okur. Denetim aynı kuralı kullanmazsa, resmî ad yerinde dururken bir
    takma ad eklemek şartname 5.5 uyumunu yanlışlıkla kırık gösterir.
    """
    return {
        tr_kucult(parca.strip())
        for baslik in resmi_terimler(satirlar)
        for parca in baslik.split("/")
        if parca.strip()
    }


def tablo_terimleri(satirlar: list[str]) -> list[list[str]]:
    """Terim tablolarının satırları — her biri dört hücre."""
    icinde, bulunan = False, []
    for satir in satirlar:
        if satir.startswith(TERIM_TABLOSU_BASLIGI):
            icinde = True
            continue
        if not icinde:
            continue
        if not satir.startswith("|"):
            icinde = False
            continue
        if AYIRICI.fullmatch(satir.strip()):
            continue
        bulunan.append([h.strip() for h in satir.strip("|").split("|")])
    return bulunan


def _ad(hucre: str) -> str:
    """`**Kâr payı**` -> `kâr payı`. Eş anlamlılar `/` ile ayrık kalır.

    `casefold()` DEĞİL `tr_kucult()`: Python "İcara".casefold() sonucunu
    `i` + U+0307 (birleşik nokta) olarak üretir, yani "icara" araması tutmaz.
    Bu testi ilk koşuşta düşüren hata tam olarak buydu — projenin kendi
    Türkçe küçültmesi zaten bunun için var.
    """
    return tr_kucult(hucre.strip("* "))


@pytest.fixture(scope="module")
def satirlar() -> list[str]:
    if not SOZLUK.exists():
        pytest.fail(f"{SOZLUK} yok — G-09'un çıktısı eksik")
    return _satirlar()


@pytest.fixture(scope="module")
def terimler(satirlar) -> list[list[str]]:
    return tablo_terimleri(satirlar)


# ---------------------------------------------------------------------------
# Kapsam
# ---------------------------------------------------------------------------


def test_asgari_terim_sayisi(satirlar, terimler) -> None:
    """G-09: en az 60 terim."""
    toplam = len(resmi_terimler(satirlar)) + len(terimler)
    assert toplam >= ASGARI_TERIM, (
        f"Sözlükte {toplam} terim var, en az {ASGARI_TERIM} gerekiyor (G-09)."
    )


def test_sartname_5_5_besi_de_var(satirlar) -> None:
    """Şartnamenin resmî tanımları eksikse 5.5 uyumu iddia edilemez."""
    beklenen = {
        "kâr payı oranı",
        "finansman maliyeti",
        "katılım fonu",
        "masrafsız finansman",
        "avantajlı finansman",
    }
    bulunan = _resmi_yazimlar(satirlar)
    assert beklenen <= bulunan, f"Şartname 5.5 kavramı eksik: {beklenen - bulunan}"


def test_fikhi_sozlesme_turleri_var(terimler) -> None:
    """G-09 bu terimleri adıyla istiyor — katılım bankacılığının çekirdeği."""
    metin = " ".join(_ad(t[0]) for t in terimler)
    for terim in ("murabaha", "muşaraka", "mudaraba", "icara", "sukuk", "tekafül"):
        assert terim in metin, f"Sözlükte '{terim}' yok (G-09 açıkça istiyor)"


# ---------------------------------------------------------------------------
# Biçim sözleşmesi — G-10'un ayrıştırıcısı buna güvenecek
# ---------------------------------------------------------------------------


def test_her_terim_satiri_dort_hucreli(terimler) -> None:
    """Sütun eklenirse `TERIMLER` üretimi kayar; erken patlaması iyidir."""
    bozuk = [t for t in terimler if len(t) != 4]
    assert not bozuk, f"Dört hücreli olmayan satır(lar): {bozuk}"


def test_terim_ve_tanim_dolu(terimler) -> None:
    ad_bos = [t for t in terimler if not _ad(t[0])]
    tanim_bos = [_ad(t[0]) for t in terimler if not t[1]]
    assert not ad_bos, f"Adsız satır: {ad_bos}"
    assert not tanim_bos, f"Tanımsız terim: {tanim_bos}"


def test_istem_sutunu_yalniz_iki_deger_alir(terimler) -> None:
    """`✓` ya da `—`. Üçüncü bir işaret ayrıştırıcıyı ikircikli bırakır."""
    gecersiz = {t[3] for t in terimler} - {"✓", "—"}
    assert not gecersiz, f"İstem sütununda beklenmeyen değer: {gecersiz}"


def test_terimler_yinelenmiyor(terimler) -> None:
    """Aynı terim iki tabloda tanımlıysa hangi tanımın isteme gireceği belirsizdir."""
    gorulen: set[str] = set()
    yinelenen = []
    for t in terimler:
        ad = _ad(t[0])
        if ad in gorulen:
            yinelenen.append(ad)
        gorulen.add(ad)
    assert not yinelenen, f"Yinelenen terim: {yinelenen}"


def test_isteme_giren_terim_var(terimler) -> None:
    """Hiçbiri ✓ değilse `TERIMLER` boş üretilir — istem alan bilgisiz kalır."""
    isaretli = [t for t in terimler if t[3] == "✓"]
    assert len(isaretli) >= 20, (
        f"İsteme yalnız {len(isaretli)} terim giriyor; alan bilgisi zayıflar."
    )


# ---------------------------------------------------------------------------
# Kökenlik — metindeki sayılar tablodan mı geliyor
# ---------------------------------------------------------------------------


def test_giristeki_terim_sayisi_guncel(satirlar, terimler) -> None:
    """«78 terim» yazıp 60 terim bırakmak sessiz bayatlamadır.

    `test_kokenlik.py` ile aynı fikir: belgeye elle yazılan sayı, belgenin
    kendi içeriğinden doğrulanabilmeli.
    """
    toplam = len(resmi_terimler(satirlar)) + len(terimler)
    metin = "\n".join(satirlar)
    iddia = re.search(r"\*\*(\d+) terim\*\* tanımlıdır", metin)
    assert iddia, "Giriş paragrafındaki «**N terim** tanımlıdır» cümlesi bulunamadı"
    assert int(iddia.group(1)) == toplam, (
        f"Giriş «{iddia.group(1)} terim» diyor ama sözlükte {toplam} terim var."
    )


def test_derlem_olcumu_toplami_tutuyor(satirlar, terimler) -> None:
    """§10: «N'i geçiyor, M'si geçmiyor» toplamı terim sayısına eşit olmalı.

    Sözlüğe terim eklenip §10 güncellenmezse bu iki sayı sessizce toplamı
    tutturamaz hâle gelir; jürinin ilk kontrol edeceği aritmetik budur.
    """
    toplam = len(resmi_terimler(satirlar)) + len(terimler)
    metin = "\n".join(satirlar)
    iddia = re.search(
        r"\*\*(\d+)'[ıiuü]\*\* derlemde geçiyor, \*\*(\d+)'[ıiuü]\*\* hiç geçmiyor",
        metin,
    )
    assert iddia, "§10'un «**N**'i derlemde geçiyor, **M**'si hiç geçmiyor» cümlesi yok"
    gecen, gecmeyen = int(iddia.group(1)), int(iddia.group(2))
    assert gecen + gecmeyen == toplam, (
        f"§10 {gecen}+{gecmeyen}={gecen + gecmeyen} diyor ama sözlükte {toplam} terim var."
    )


def test_gecmeyen_terim_tablosu_basligiyla_tutarli(satirlar) -> None:
    """«Derlemde hiç geçmeyen 18 terim» başlığı §10'daki sayıyla aynı olmalı."""
    metin = "\n".join(satirlar)
    govde = re.search(r"\*\*(\d+)'[ıiuü]\*\* hiç geçmiyor", metin)
    baslik = re.search(r"### Derlemde hiç geçmeyen (\d+) terim", metin)
    assert govde and baslik, "§10'un sayı cümlesi veya alt başlığı bulunamadı"
    assert govde.group(1) == baslik.group(1), (
        f"Gövde «{govde.group(1)}» diyor, başlık «{baslik.group(1)}» diyor."
    )


def test_istem_sayisi_guncel(satirlar, terimler) -> None:
    """«30'unu isteme taşır» iddiası ✓ sayısıyla tutmalı."""
    isaretli = sum(1 for t in terimler if t[3] == "✓")
    metin = "\n".join(satirlar)
    iddia = re.search(r"\*\*(\d+)'[ıiuü]n[ıu]\*\* isteme taşır", metin)
    assert iddia, "«**N**'ini isteme taşır» cümlesi bulunamadı"
    assert int(iddia.group(1)) == isaretli, (
        f"Giriş «{iddia.group(1)}» diyor ama ✓ işaretli terim {isaretli} tane."
    )


# ---------------------------------------------------------------------------
# G-10 — istem bloğu sözlükten okunuyor (26 Ağustos)
# ---------------------------------------------------------------------------


class TestIstemBagi:
    """Sözlük ile modelin gördüğü metin TEK KAYNAK olmalı.

    Önceden iki kopya vardı: `llm.py` içinde elle tutulan bir sabit ve bu
    dosyadaki tablolar. İki kopya ayrışmayı garanti eder — sözlük büyür, model
    eski terimlerle çalışmaya devam eder ve kimse fark etmez.
    """

    def test_istem_blogu_sozlukten_geliyor(self) -> None:
        from src.extraction.llm import TERIMLER, terimleri_yukle

        assert TERIMLER == terimleri_yukle()
        assert "Kâr Payı Oranı" in TERIMLER

    def test_bes_resmi_kavram_isteme_giriyor(self) -> None:
        """Şartname 5.5'in beşi de modele taşınmalı."""
        from src.extraction.llm import TERIMLER

        for kavram in (
            "Kâr Payı Oranı",
            "Finansman Maliyeti",
            "Katılım Fonu",
            "Masrafsız Finansman",
            "Avantajlı Finansman",
        ):
            assert kavram in TERIMLER, f"{kavram} isteme girmiyor"

    def test_dolayli_ifadeler_isteme_giriyor(self) -> None:
        """Şartname 5.2'nin üç ifadesi — sayı uydurmama talimatıyla birlikte."""
        from src.extraction.llm import TERIMLER

        for ifade in ("avantajlı kâr payı", "özel oranlı finansman", "düşük maliyetli"):
            assert ifade in TERIMLER
        assert "UYDURMA" in TERIMLER

    def test_sozluk_yoksa_sessizce_devam_etmez(self, tmp_path) -> None:
        """Terimsiz istem çıkarımı sessizce kötüleştirir — patlaması doğrudur."""
        import pytest

        from src.extraction.llm import terimleri_yukle

        with pytest.raises(FileNotFoundError):
            terimleri_yukle(tmp_path / "yok.md")

    def test_isaretciler_bozuksa_patlar(self, tmp_path) -> None:
        import pytest

        from src.extraction.llm import terimleri_yukle

        bozuk = tmp_path / "TERIM_SOZLUGU.md"
        bozuk.write_text("# Sözlük\nişaretçi yok", encoding="utf-8")
        with pytest.raises(ValueError):
            terimleri_yukle(bozuk)
