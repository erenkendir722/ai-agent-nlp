"""Hedefli finansman çekimi testleri — `tools/finansman_cek.py`.

Ağsız ve tarayıcısız: `cek()` dışındaki her şey saf veri işleme, selenium
yalnız orada içeri alınıyor.

Buradaki en önemli test `test_diskte_olan_url_atlanir`. Aracın var oluş
sebebi o kapı: `kaydi_yaz` kimliğe göre ÜZERİNE YAZDIĞI için, envanterde
duran bir sayfa yeniden çekilirse gövdesi tazelenir. Altın setin 92 kaydının
29'u bu araçla dokunulan üç bankada (0206:18 · 0210:9 · 0214:2) ve gövdeleri
değişirse `make eval` ölçüm zemini kayar — iki koşunun farkı «iyileşme»
sanılır. Kapı delinirse bunu haber verecek başka bir şey yok.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.schema import Banka
from tools.finansman_cek import (
    arama_anahtari,
    banka_eslemesi,
    bankayi_bul,
    envanter_anahtarlari,
    planla,
    urlleri_oku,
)

BANKALAR = [
    Banka(
        kod="0206",
        ad="Türkiye Finans Katılım Bankası A.Ş.",
        kisa_ad="Türkiye Finans",
        site="https://www.turkiyefinans.com.tr",
        durum="faal",
        kod_dogrulandi=True,
    ),
    Banka(
        kod="0210",
        ad="Vakıf Katılım Bankası A.Ş.",
        kisa_ad="Vakıf Katılım",
        site="https://www.vakifkatilim.com.tr",
        durum="faal",
        kod_dogrulandi=True,
    ),
    Banka(
        kod="0214",
        ad="Dünya Katılım Bankası A.Ş.",
        kisa_ad="Dünya Katılım",
        site="https://dunyakatilim.com.tr",
        durum="faal",
        kod_dogrulandi=True,
    ),
    Banka(
        kod="0205",
        ad="Kuveyt Türk Katılım Bankası A.Ş.",
        kisa_ad="Kuveyt Türk",
        site="https://www.kuveytturk.com.tr",
        durum="faal",
        kod_dogrulandi=True,
    ),
]


def _envanter_yaz(dizin: Path, kayitlar: dict[str, str]) -> None:
    """kod -> url eşlemesinden sahte `data/raw` üretir."""
    for kod, url in kayitlar.items():
        banka_dizin = dizin / kod.split("-")[0]
        banka_dizin.mkdir(parents=True, exist_ok=True)
        (banka_dizin / f"{kod}.json").write_text(
            f'{{"banka_kodu": "{kod.split("-")[0]}", "url": "{url}"}}',
            encoding="utf-8",
        )


# -- Arama anahtarı ---------------------------------------------------------


@pytest.mark.parametrize(
    "a, b",
    [
        # http/https aynı sayfayı gösterir — Albaraka listesinde bir satır http
        ("http://albaraka.com.tr/tr/bireysel/x", "https://albaraka.com.tr/tr/bireysel/x"),
        # www varsa da yoksa da — Vakıf'ın seed_urls'ü www'siz yazılmış
        ("https://www.vakifkatilim.com.tr/tr/a", "https://vakifkatilim.com.tr/tr/a"),
        # sondaki eğik çizgi
        ("https://x.com.tr/a/b/", "https://x.com.tr/a/b"),
        # büyük/küçük harf — Türkiye Finans yollarında `Sayfalar` büyük S ile
        ("https://x.com.tr/tr-tr/Sayfalar/A.aspx", "https://x.com.tr/tr-tr/sayfalar/a.aspx"),
        # yüzde kodlaması çözülmüş biçimle aynı sayılmalı
        ("https://x.com.tr/tr/deste%C4%9Fi", "https://x.com.tr/tr/desteği"),
    ],
)
def test_arama_anahtari_ayni_sayfayi_esitler(a: str, b: str) -> None:
    assert arama_anahtari(a) == arama_anahtari(b)


def test_arama_anahtari_farkli_sayfayi_ayirir() -> None:
    """Yumuşak g'li ve g'siz yazım AYRI sayfadır — ölçüldü, 404 vs 200.

    `soik-finansman-desteği` 404 veriyor, sitenin kendi bağlantısı
    `soik-finansman-destegi`. Anahtar bunları eşitleseydi, listedeki yanlış
    yazım «envanterde var» sayılır ve doğru sayfa hiç çekilmezdi.
    """
    assert arama_anahtari("https://x.com.tr/a/soik-finansman-desteği") != arama_anahtari(
        "https://x.com.tr/a/soik-finansman-destegi"
    )


# -- Banka eşlemesi ---------------------------------------------------------


def test_alan_adindan_banka_cozulur() -> None:
    esleme = banka_eslemesi(BANKALAR)
    beklenen = {
        "https://www.turkiyefinans.com.tr/tr-tr/ticari/x": "0206",
        "https://www.vakifkatilim.com.tr/tr/isim-icin/y": "0210",
        "https://dunyakatilim.com.tr/kendim-icin/z": "0214",
    }
    for url, kod in beklenen.items():
        banka = bankayi_bul(url, esleme)
        assert banka is not None and banka.kod == kod


def test_alt_alan_adi_da_cozulur() -> None:
    """`saglamkart.kuveytturk.com.tr` Kuveyt Türk'tür — envanterde 12 kaydı var."""
    esleme = banka_eslemesi(BANKALAR)
    banka = bankayi_bul("https://saglamkart.kuveytturk.com.tr/kampanya", esleme)
    assert banka is not None and banka.kod == "0205"


def test_bilinmeyen_alan_adi_none_doner() -> None:
    esleme = banka_eslemesi(BANKALAR)
    assert bankayi_bul("https://baskabanka.com.tr/x", esleme) is None


# -- Liste okuma ------------------------------------------------------------


def test_yorum_ve_bos_satir_atlanir(tmp_path: Path) -> None:
    yol = tmp_path / "liste.txt"
    yol.write_text(
        "# başlık yorumu\n"
        "\n"
        "https://www.vakifkatilim.com.tr/tr/a\n"
        "   \n"
        "# https://www.vakifkatilim.com.tr/tr/olu-sayfa\n"
        "https://www.vakifkatilim.com.tr/tr/b\n",
        encoding="utf-8",
    )
    assert urlleri_oku(yol) == [
        "https://www.vakifkatilim.com.tr/tr/a",
        "https://www.vakifkatilim.com.tr/tr/b",
    ]


def test_tekrar_eden_url_bir_kez_dondurulur(tmp_path: Path) -> None:
    """Kaynak listede 8 satır tekrarlıydı; iki kez çekmenin karşılığı yok."""
    yol = tmp_path / "liste.txt"
    yol.write_text(
        "https://www.vakifkatilim.com.tr/tr/a\n"
        "https://vakifkatilim.com.tr/tr/a/\n"
        "https://www.vakifkatilim.com.tr/tr/b\n",
        encoding="utf-8",
    )
    assert urlleri_oku(yol) == [
        "https://www.vakifkatilim.com.tr/tr/a",
        "https://www.vakifkatilim.com.tr/tr/b",
    ]


def test_liste_yoksa_sessiz_kalinmaz(tmp_path: Path) -> None:
    """Boş liste «eksik yok» diye okunmamalı — kırıldığını söylemeyen hata."""
    with pytest.raises(FileNotFoundError):
        urlleri_oku(tmp_path / "yok.txt")


# -- Envanter kapısı — bu dosyanın en önemli testi --------------------------


def test_diskte_olan_url_atlanir(tmp_path: Path) -> None:
    """Envanterde duran sayfa ÇEKİLMEZ; mevcut kaydın üzerine yazılmaz.

    Bu kapı delinirse altın setteki 29 kaydın gövdesi tazelenir ve
    `make eval` ölçüm zemini sessizce kayar.
    """
    _envanter_yaz(tmp_path, {"0210-aaaa": "https://www.vakifkatilim.com.tr/tr/var"})
    envanter = envanter_anahtarlari(tmp_path)
    cekilecek, var, eslesmeyen = planla(
        [
            "https://www.vakifkatilim.com.tr/tr/var",
            "https://www.vakifkatilim.com.tr/tr/yok",
        ],
        banka_eslemesi(BANKALAR),
        envanter,
    )
    assert var == ["https://www.vakifkatilim.com.tr/tr/var"]
    assert cekilecek == {"0210": ["https://www.vakifkatilim.com.tr/tr/yok"]}
    assert eslesmeyen == []


def test_envanter_esleme_yazim_farkina_takilmaz(tmp_path: Path) -> None:
    """Envanterde `https://www.` ile duran sayfa, listede `http://`sız yazılsa da atlanır."""
    _envanter_yaz(tmp_path, {"0203-bbbb": "https://www.albaraka.com.tr/tr/bireysel/x/"})
    envanter = envanter_anahtarlari(tmp_path)
    assert arama_anahtari("http://albaraka.com.tr/tr/bireysel/x") in envanter


def test_banka_bulunamayan_url_sessizce_dusmez(tmp_path: Path) -> None:
    """Eşleşmeyen adres raporlanır — sessizce atılırsa kimse fark etmez."""
    cekilecek, var, eslesmeyen = planla(
        ["https://bilinmeyenbanka.com.tr/finansman"],
        banka_eslemesi(BANKALAR),
        set(),
    )
    assert cekilecek == {}
    assert var == []
    assert eslesmeyen == ["https://bilinmeyenbanka.com.tr/finansman"]


def test_bos_envanter_dizini_hata_vermez(tmp_path: Path) -> None:
    assert envanter_anahtarlari(tmp_path) == set()


# -- Kuru koşu --------------------------------------------------------------


def test_kuru_kosu_cekmeye_hic_girmez(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--uygula` verilmeden `cek()` HİÇ çağrılmaz.

    Ölçüt çağrının kendisi: `cek()` tarayıcıyı açan, robots'a soran ve
    `kaydi_yaz` ile diske yazan tek yol. Çağrılmadıysa hiçbir sayfa
    çekilmemiş, hiçbir kaydın üzerine yazılmamıştır.
    """
    from tools import finansman_cek

    liste = tmp_path / "liste.txt"
    liste.write_text("https://www.vakifkatilim.com.tr/tr/kuru-kosu-testi\n", encoding="utf-8")

    cagrildi: list[object] = []
    asil_cek = finansman_cek.cek
    finansman_cek.cek = lambda *a, **k: cagrildi.append(a) or ([], [])  # type: ignore[assignment]
    try:
        kod = finansman_cek.main(["finansman_cek", "--liste", str(liste)])
    finally:
        finansman_cek.cek = asil_cek  # type: ignore[assignment]

    assert kod == 0
    assert cagrildi == [], "kuru koşuda `cek()` çağrılmamalı"
    cikti = capsys.readouterr().out
    assert "Çekmek için" in cikti
    assert "Çekilecek      : 1" in cikti
