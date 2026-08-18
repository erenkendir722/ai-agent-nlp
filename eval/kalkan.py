"""Kalkan ölçümü — köken tipli doğrulamanın yanlış blok oranı (bulgu 1.2).

NEDEN AYRI BİR METRİK:
    "Kalkanı düzelttik" bir iddiadır. Kalkanın iki yönlü bir hata uzayı var
    ve tek yönü ölçmek yanıltıcıdır:

      * ÇOK SIKI  -> meşru cevabı engeller (yanlış blok). 18 Ağustos: %20.
      * ÇOK GEVŞEK -> uydurma sayıyı geçirir. Bunu `test_kalkan_kokenli.py`
        koruyor; testler kırmızıya dönmeden gevşeyemez.

    Bu modül birinci yönü SAYIYA çevirir. İkinci yön testlerde kaldı çünkü
    orada eşik değil, ikili doğruluk aranır: bir uydurma sayı ya geçer ya
    geçmez, "oranı" olmaz.

Ölçüm `eval/sorular.yaml` üzerinden koşar; soru kümesi sabittir ki iki koşu
karşılaştırılabilsin.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.depolama import KampanyaKaydi
from src.rag.chatbot import sor

KOK = Path(__file__).resolve().parents[1]
SORU_DOSYASI = KOK / "eval" / "sorular.yaml"


def sorulari_yukle(yol: Path = SORU_DOSYASI) -> list[dict[str, Any]]:
    if not yol.exists():
        return []
    return yaml.safe_load(yol.read_text(encoding="utf-8")) or []


def olc(kayitlar: list[KampanyaKaydi] | None = None) -> dict[str, Any] | None:
    """Yanlış blok oranı + denetimsiz parça oranı. Soru kümesi yoksa None."""
    sorular = sorulari_yukle()
    if not sorular:
        return None

    yanlis_bloklar: list[dict[str, Any]] = []
    mesru_sayisi = 0
    toplam_parca = 0
    denetimsiz_parca = 0
    koken_dagilimi: dict[str, int] = {}

    for kayit in sorular:
        cevap = sor(kayit["soru"], kayitlar)
        toplam_parca += len(cevap.parcalar)
        denetimsiz_parca += cevap.denetimsiz_parca_sayisi()
        for parca in cevap.parcalar:
            koken_dagilimi[parca.koken.value] = koken_dagilimi.get(parca.koken.value, 0) + 1

        if not kayit.get("mesru"):
            continue
        mesru_sayisi += 1
        if not cevap.dogrulama_gecti:
            yanlis_bloklar.append(
                {"soru": kayit["soru"], "reddedilen": cevap.reddedilen_sayilar[:5]}
            )

    return {
        "soru_sayisi": len(sorular),
        "mesru_soru_sayisi": mesru_sayisi,
        "yanlis_blok_sayisi": len(yanlis_bloklar),
        "yanlis_blok_orani": len(yanlis_bloklar) / mesru_sayisi if mesru_sayisi else 0.0,
        "yanlis_blok_ornekleri": yanlis_bloklar[:5],
        "toplam_parca": toplam_parca,
        "denetimsiz_parca": denetimsiz_parca,
        # Miras yolun ölçülen borcu. Hedef sıfır; sıfırdan büyükse bir
        # üretici hâlâ `metin=` sözleşmesiyle yazılmış demektir.
        "denetimsiz_parca_orani": denetimsiz_parca / toplam_parca if toplam_parca else 0.0,
        "koken_dagilimi": koken_dagilimi,
    }


__all__ = ["olc", "sorulari_yukle"]
