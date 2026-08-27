"""Sunumdaki sayılar ölçümle aynı mı — bayat slayt savunması.

NEDEN VAR:
    Sunum, jürinin gördüğü tek yüzey. Slayttaki bir sayı ölçümden ayrışırsa
    jüri depoya baktığında **çelişki** bulur; o an doğru olan her şeyin
    güvenilirliği de gider. Bu proje aynı hatayı bir kez yaşadı: `SONUCLAR.md`
    15 Ağustos'ta bozulan veritabanının değil, ondan önceki iyi koşunun
    sayılarını gösteriyordu.

    Bu yüzden sunum sayıları elle değil, ölçüm dosyalarından denetlenir.
    `sunum.html` içindeki ablasyon tablosu `data-tablo="ablasyon"` işaretini
    taşır; test o tabloyu `data/ablasyon.json` ile karşılaştırır.

Test kırıldığında yapılacak: **slaytı düzelt**, testi değil.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
SUNUM = KOK / "docs" / "sunum" / "sunum.html"
ABLASYON = KOK / "data" / "ablasyon.json"
SONUCLAR = KOK / "docs" / "SONUCLAR.md"

# Slayttaki satır etiketi -> ablasyon.json anahtarı
SATIRLAR = {
    "Yalnız kural": "kural",
    "Yalnız dil modeli": "llm",
    "Hibrit (kural + model)": "hibrit",
    "Hibrit · eleştirmen kapalı": "hibrit_elestirmensiz",
    "Tam hiyerarşi (bizim)": "tam",
}


def _tablo(isaret: str) -> str:
    metin = SUNUM.read_text(encoding="utf-8")
    bas = metin.index(f'data-tablo="{isaret}"')
    return metin[bas : metin.index("</table>", bas)]


def _sayi(parca: str) -> float:
    return float(parca.replace("%", "").replace(",", ".").strip())


@pytest.mark.skipif(not ABLASYON.exists(), reason="ablasyon koşulmamış")
class TestAblasyonTablosu:
    def test_her_satir_olcumle_ayni(self) -> None:
        tablo = _tablo("ablasyon")
        olcum = json.loads(ABLASYON.read_text(encoding="utf-8"))

        for etiket, anahtar in SATIRLAR.items():
            assert etiket in tablo, f"slaytta '{etiket}' satırı yok"
            satir = tablo[tablo.index(etiket) :].split("</tr>", 1)[0]
            hucreler = re.findall(r">([%\d,\.]+)<", satir)
            assert len(hucreler) >= 4, f"{etiket}: slaytta 4 sayı bekleniyordu"

            f1, sayisal, halusinasyon, doluluk = (_sayi(h) for h in hucreler[:4])
            kayit = olcum[anahtar]
            assert f1 == pytest.approx(kayit["makro_f1"], abs=0.001), f"{etiket} makro-F1"
            assert sayisal == pytest.approx(kayit["sayisal_dogruluk"], abs=0.001), f"{etiket} sayısal"
            assert halusinasyon == pytest.approx(
                kayit["halusinasyon_orani"] * 100, abs=0.01
            ), f"{etiket} halüsinasyon"
            assert doluluk == pytest.approx(
                kayit["alan_dolulugu"] * 100, abs=0.1
            ), f"{etiket} doluluk"

    def test_satirlar_ayni_korpustan(self) -> None:
        """Slayt tek bir korpus ve tek bir kod izi iddia ediyor."""
        olcum = json.loads(ABLASYON.read_text(encoding="utf-8"))
        assert len({k["kampanya_sayisi"] for k in olcum.values()}) == 1
        assert len({k["kod_parmak_izi"] for k in olcum.values()}) == 1

    def test_slayttaki_korpus_buyuklugu_dogru(self) -> None:
        olcum = json.loads(ABLASYON.read_text(encoding="utf-8"))
        boyut = next(iter(olcum.values()))["kampanya_sayisi"]
        metin = SUNUM.read_text(encoding="utf-8")
        assert f"{boyut:,}".replace(",", ".") in metin, "slayttaki kampanya sayısı ölçümle uyuşmuyor"


def test_slayttaki_test_sayisi_dogru() -> None:
    """Kapaktaki «geçen test» rakamı GERÇEK test sayısı olmalı.

    NEDEN VAR — 27 Ağustos'ta yakalandı: slayt «787 geçen test» diyordu, gerçek
    sayı 1.296'ydı. `data-sayi="test"` işareti denetim için konmuş ama denetimi
    yazılmamıştı; rakam altı hafta boyunca sessizce eskidi.

    Bu, jüriye söylenen bir sayı. Ablasyon ve sonuç tabloları ölçüm dosyalarına
    bağlı; bu rakamın bağlanacağı dosya yok, o yüzden pytest'in KENDİSİNE
    sorulur.

    Toplama ayrı bir süreçte yapılır: bu testin içinden `session.items`
    okumak, alt küme koşulduğunda (tek dosya, `-k` süzgeci) yanlış düşerdi.
    """
    import re
    import subprocess
    import sys

    metin = SUNUM.read_text(encoding="utf-8")
    eslesme = re.search(r'data-sayi="test"[^>]*>([\d.]+)<', metin)
    assert eslesme, "slaytta `data-sayi=\"test\"` işaretli rakam yok"
    slayttaki = int(eslesme.group(1).replace(".", ""))

    sonuc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        cwd=KOK,
    )
    toplanan = re.search(r"(\d+)\s+tests? collected", sonuc.stdout)
    assert toplanan, f"pytest toplama çıktısı okunamadı:\n{sonuc.stdout[-600:]}"
    gercek = int(toplanan.group(1))

    assert slayttaki == gercek, (
        f"slayt {slayttaki} test diyor, gerçek {gercek}. Slaytı düzeltin."
    )


@pytest.mark.skipif(not SONUCLAR.exists(), reason="eval koşulmamış")
class TestSonucTablosu:
    def test_kapanis_sayilari_sonuclarla_ayni(self) -> None:
        tablo = _tablo("sonuclar")
        sonuclar = SONUCLAR.read_text(encoding="utf-8")

        makro = float(re.search(r"\*\*Makro-F1\*\* \| ([\d.]+)", sonuclar).group(1))
        sayisal = float(re.search(r"Sayısal alan doğruluğu \| ([\d.]+)", sonuclar).group(1))
        halus = float(re.search(r"\*\*Halüsinasyon oranı\*\* \| %([\d.]+)", sonuclar).group(1))

        slayt = {e: _sayi(d) for e, d in re.findall(r">([^<>]+)</td><td[^>]*>([\d,%.]+)<", tablo)}
        assert any(abs(v - round(makro, 2)) < 0.005 for v in slayt.values()), "makro-F1 ayrışmış"
        assert any(abs(v - round(sayisal, 2)) < 0.005 for v in slayt.values()), "sayısal doğruluk ayrışmış"
        assert any(abs(v - round(halus, 2)) < 0.005 for v in slayt.values()), "halüsinasyon ayrışmış"


@pytest.mark.skipif(not ABLASYON.exists(), reason="ablasyon koşulmamış")
class TestAnlatiSayilari:
    """Tablonun ALTINDAKİ düz metin de ölçüme bağlı olmalı.

    26 Ağustos'ta yakalandı: ablasyon tablosunun hücreleri doğruydu (%0,51 ve
    %0,42) ama hemen altındaki «Okuma:» paragrafı **%0,32'den %0,63'e … yani
    iki katına** diyordu. İkisi de aynı slaytta, yan yana. Jüri tabloyu değil
    cümleyi okur.

    Sebebi testin kapsamıydı: `TestAblasyonTablosu` yalnız `<table>` hücrelerini
    ayrıştırıyor, anlatıya hiç bakmıyordu. Kapsam boşluğu bir sayıyı dört gün
    bayat tuttu.
    """

    def test_elestirmen_cumlesi_olcumle_ayni(self) -> None:
        metin = SUNUM.read_text(encoding="utf-8")
        olcum = json.loads(ABLASYON.read_text(encoding="utf-8"))

        cumle = re.search(
            r"halüsinasyon %([\d,]+)'dan %([\d,]+)'e çıkıyor", metin
        )
        assert cumle, "slayttaki eleştirmen cümlesi bulunamadı (biçimi mi değişti?)"

        acik, kapali = (_sayi(g) for g in cumle.groups())
        assert acik == pytest.approx(
            olcum["hibrit"]["halusinasyon_orani"] * 100, abs=0.01
        ), "eleştirmen AÇIKKEN ki halüsinasyon oranı ölçümle tutmuyor"
        assert kapali == pytest.approx(
            olcum["hibrit_elestirmensiz"]["halusinasyon_orani"] * 100, abs=0.01
        ), "eleştirmen KAPALIYKEN ki halüsinasyon oranı ölçümle tutmuyor"
        assert kapali > acik, "eleştirmen kapatılınca halüsinasyon artmalı"

    def test_kat_iddiasi_abartilmamis(self) -> None:
        """«İki katına» gibi bir çarpan iddiası ölçülen orana uymalı."""
        metin = SUNUM.read_text(encoding="utf-8")
        olcum = json.loads(ABLASYON.read_text(encoding="utf-8"))
        oran = (
            olcum["hibrit_elestirmensiz"]["halusinasyon_orani"]
            / olcum["hibrit"]["halusinasyon_orani"]
        )
        if "iki katına" in metin:
            assert oran >= 1.8, (
                f"slayt «iki katına» diyor ama ölçülen çarpan {oran:.2f}× — "
                "abartılı iddia, düzelt."
            )

    def test_yuklem_katkisi_cumlesi_dogru(self) -> None:
        """«Birlikte 0,79 · yüklem eklenince 0,82» iddiası ölçümle tutmalı.

        Tam eşitlik aranmaz: CLAUDE.md'ye göre EVREN bayt düzeyinde deterministik
        değil ve makro-F1 **±0,01 gürültü** taşıyor. Slaytta 0,79 mu 0,80 mı
        yazdığı o bandın içinde kalır; testin işi kesinlik dayatmak değil,
        slaytın ölçümden **bandın dışına** kaymasını yakalamak.
        """
        metin = SUNUM.read_text(encoding="utf-8")
        olcum = json.loads(ABLASYON.read_text(encoding="utf-8"))
        GURULTU = 0.011

        birlikte = re.search(r"<b>Birlikte ([\d,]+)\.</b>", metin)
        assert birlikte, "«Birlikte …» cümlesi bulunamadı"
        assert abs(_sayi(birlikte.group(1)) - olcum["hibrit"]["makro_f1"]) <= GURULTU

        eklenince = re.search(r"eklenince <b>([\d,]+)</b>", metin)
        assert eklenince, "«… eklenince …» cümlesi bulunamadı"
        assert abs(_sayi(eklenince.group(1)) - olcum["tam"]["makro_f1"]) <= GURULTU

    def test_slaytta_bayat_sayi_kalmamis(self) -> None:
        """Eski koşudan kalan sayı çiftleri slaytta geçmemeli."""
        metin = SUNUM.read_text(encoding="utf-8")
        for bayat in ("%0,32", "%0,63"):
            assert bayat not in metin, (
                f"{bayat} 26 Ağustos öncesi ablasyon koşusundan kalma bayat sayı"
            )


class TestSinirlarPaneli:
    """«Bilinen sınırlar — saklamıyoruz» panelindeki sayılar da ölçüme bağlı.

    NEDEN AYRI BİR SINIF:
        27 Ağustos'ta korpus 1.024'ten 734 kayda indi (bozuk gövde, yinelenen
        ve içeriksiz sayfalar ayıklandı). Kapanış tablosunu bir test yakaladı
        ve düzeltildi; ama bu panelin ÜÇ sayısını hiçbir test denetlemiyordu ve
        üçü birden sessizce bayat kaldı:

            kâr payı doluluğu   %16  ->  %19
            kapsam dengesizliği 11,9× -> 11,4×
            «diğer» payı        %45  ->  %37

        Panelin adı «saklamıyoruz» — bir dürüstlük iddiası. Yanlış tarafa
        sapmış olsalardı (sınırı olduğundan küçük göstermek) iddia tersine
        dönerdi. Denetimsiz bir dürüstlük beyanı, beyanın kendisini çürütür.
    """

    @pytest.mark.skipif(not SONUCLAR.exists(), reason="eval koşulmamış")
    def test_kar_payi_dolulugu_sonuclarla_ayni(self) -> None:
        sonuclar = SONUCLAR.read_text(encoding="utf-8")
        olculen = re.search(r"`kar_payi_orani` \| %(\d+)", sonuclar)
        assert olculen, "SONUCLAR.md doluluk tablosunda `kar_payi_orani` yok"

        metin = SUNUM.read_text(encoding="utf-8")
        slayt = re.search(r"Kâr payı oranı doluluğu <b[^>]*>%(\d+)</b>", metin)
        assert slayt, "slaytta kâr payı doluluğu iddiası bulunamadı"
        assert slayt.group(1) == olculen.group(1), (
            f"slayt %{slayt.group(1)} diyor, ölçüm %{olculen.group(1)}. Slaytı düzeltin."
        )

    def test_kapsam_ve_diger_payi_canli_veriyle_ayni(self) -> None:
        from src.depolama import tum_kayitlar

        try:
            kayitlar = tum_kayitlar()
        except Exception:  # pragma: no cover - veritabanı yoksa atla
            pytest.skip("veritabanı okunamadı")
        if not kayitlar:
            pytest.skip("veritabanı boş")

        metin = SUNUM.read_text(encoding="utf-8")

        # «diğer» payı — şartnamenin sekiz türüne girmeyen kampanyalar.
        diger = sum(1 for k in kayitlar if (k.kampanya_turu or "") == "diger")
        beklenen_pay = round(diger / len(kayitlar) * 100)
        slayt_pay = re.search(r"Kayıtların <b[^>]*>%(\d+)'\w+</b> «diğer»", metin)
        assert slayt_pay, "slaytta «diğer» payı iddiası bulunamadı"
        assert int(slayt_pay.group(1)) == beklenen_pay, (
            f"slayt %{slayt_pay.group(1)} diyor, gerçek %{beklenen_pay}. Slaytı düzeltin."
        )

        # Kapsam dengesizliği — en çok kayıtlı banka / en az kayıtlı banka.
        sayim: dict[str, int] = {}
        for k in kayitlar:
            sayim[k.banka_adi] = sayim.get(k.banka_adi, 0) + 1
        beklenen_kat = round(max(sayim.values()) / min(sayim.values()), 1)
        slayt_kat = re.search(r"dengesiz \(<b[^>]*>([\d,]+)×</b>\)", metin)
        assert slayt_kat, "slaytta kapsam dengesizliği iddiası bulunamadı"
        assert abs(_sayi(slayt_kat.group(1)) - beklenen_kat) < 0.05, (
            f"slayt {slayt_kat.group(1)}× diyor, gerçek {beklenen_kat}×. Slaytı düzeltin."
        )
