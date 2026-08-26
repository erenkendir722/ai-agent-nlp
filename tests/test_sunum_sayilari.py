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
