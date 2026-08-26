"""Chatbot 30 soruluk test seti — doğruluk ve kaynak gösterme ölçümü (S-10).

    make chatbot-test          # tablo + başarısız soruların dökümü
    make chatbot-test -q       # yalnız özet

NEDEN BEKLENEN CEVAP METNİ TUTMUYORUZ — bkz. `eval/chatbot_sorulari.yaml`
başlığı. Kısaca: sabit bir "beklenen cevap" dizesi ya çıkarım yenilendiğinde
yanlış yere kırılır ya da testi geçirmek için güncellenip ölçmeyi bırakır.
Onun yerine her soru için DAVRANIŞ ÖZELLİKLERİ sınanır.

Ölçülen iki sayı:

    doğruluk               sınanan özelliklerin hepsini geçen soru oranı
    kaynak gösterme oranı  veri iddiası taşıyan cevaplarda kaynakça oranı

İkincisinin hedefi 1,00'dır ve pazarlık konusu değildir: kaynağını
gösteremeyen bir veri iddiası, bu sistemde üretilmemeliydi.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from src.depolama import KampanyaKaydi, tum_kayitlar
from src.rag.chatbot import Niyet, sor

KOK = Path(__file__).resolve().parents[1]
SORU_DOSYASI = KOK / "eval" / "chatbot_sorulari.yaml"

DOGRULUK_HEDEFI = 0.88
KAYNAK_HEDEFI = 1.00


def sorulari_yukle(yol: Path = SORU_DOSYASI) -> list[dict[str, Any]]:
    if not yol.exists():
        return []
    return yaml.safe_load(yol.read_text(encoding="utf-8")) or []


def _soruyu_sina(kayit: dict[str, Any], kayitlar: list[KampanyaKaydi]) -> dict[str, Any]:
    """Tek soruyu koşar ve hangi özelliklerin tuttuğunu döndürür."""
    cevap = sor(kayit["soru"], kayitlar)
    metin = cevap.tam_metin().lower()
    hatalar: list[str] = []

    # `niyet` bir liste olabilir: bazı sorular iki katmandan da makul biçimde
    # cevaplanır. Örnek: «X bankasının taşıt kampanyası var mı?» yapısal
    # sorguyla da (alanları listeler) metin aramasıyla da (koşul metnini
    # getirir) doğru cevaplanır. Böyle sorularda tek bir sınıfı doğru ilan
    # etmek, ölçümü keyfîleştirir — kabul edilenler açıkça yazılır.
    beklenen_niyet = kayit.get("niyet")
    if beklenen_niyet:
        kabul = [beklenen_niyet] if isinstance(beklenen_niyet, str) else beklenen_niyet
        if cevap.niyet.value not in kabul:
            hatalar.append(
                f"niyet: beklenen {' | '.join(kabul)}, gelen {cevap.niyet.value}"
            )

    kaynak_bekleniyor = kayit.get("kaynak")
    if kaynak_bekleniyor is True and not cevap.kaynaklar:
        hatalar.append("kaynakça yok — veri iddiası kaynaksız sunulmuş")
    if kaynak_bekleniyor is False and cevap.kaynaklar:
        hatalar.append("kapsam dışı cevapta kaynakça var")

    for parca in kayit.get("icermeli", []):
        if parca.lower() not in metin:
            hatalar.append(f"eksik: {parca!r}")

    for parca in kayit.get("icermemeli", []):
        if parca.lower() in metin:
            hatalar.append(f"olmamalıydı: {parca!r}")

    # Kalkan bu cevabı engellemiş mi? Sayısal iddia taşıyan MEŞRU bir soruda
    # blok, yanlış pozitiftir — ölçülmesi gereken tam olarak bu.
    if kayit.get("sayisal") and not cevap.dogrulama_gecti:
        hatalar.append(f"kalkan engelledi (reddedilen: {cevap.reddedilen_sayilar[:3]})")

    # Miras yol borcu: hiçbir üretici denetimsiz parça üretmemeli.
    if cevap.denetimsiz_parca_sayisi():
        hatalar.append(f"{cevap.denetimsiz_parca_sayisi()} denetimsiz parça")

    return {
        "soru": kayit["soru"],
        "gecti": not hatalar,
        "hatalar": hatalar,
        "niyet": cevap.niyet.value,
        "kaynak_sayisi": len(cevap.kaynaklar),
        "kaynak_bekleniyor": kaynak_bekleniyor,
        "sartname_senaryosu": kayit.get("sartname_senaryosu"),
        "cevap": cevap.tam_metin(),
    }


def olc(kayitlar: list[KampanyaKaydi] | None = None) -> dict[str, Any] | None:
    """30 soruluk kümeyi koşar. Küme yoksa None."""
    sorular = sorulari_yukle()
    if not sorular:
        return None
    if kayitlar is None:
        kayitlar = tum_kayitlar()

    sonuclar = [_soruyu_sina(k, kayitlar) for k in sorular]
    gecen = [s for s in sonuclar if s["gecti"]]

    kaynak_gerekenler = [s for s in sonuclar if s["kaynak_bekleniyor"] is True]
    kaynak_verenler = [s for s in kaynak_gerekenler if s["kaynak_sayisi"] > 0]

    senaryolar = {
        s["sartname_senaryosu"]: s["gecti"]
        for s in sonuclar
        if s["sartname_senaryosu"]
    }

    return {
        "soru_sayisi": len(sonuclar),
        "gecen": len(gecen),
        "dogruluk": len(gecen) / len(sonuclar),
        "kaynak_gereken": len(kaynak_gerekenler),
        "kaynak_gosterme_orani": (
            len(kaynak_verenler) / len(kaynak_gerekenler) if kaynak_gerekenler else None
        ),
        "sartname_senaryolari": senaryolar,
        "basarisizlar": [s for s in sonuclar if not s["gecti"]],
        "niyet_dagilimi": {
            n.value: sum(1 for s in sonuclar if s["niyet"] == n.value) for n in Niyet
        },
    }


def _yazdir(olcum: dict[str, Any], ayrintili: bool) -> None:
    print("\n=== CHATBOT TEST SETİ (S-10) ===\n")
    dogruluk = olcum["dogruluk"]
    kaynak = olcum["kaynak_gosterme_orani"]

    def durum(deger: float | None, hedef: float) -> str:
        if deger is None:
            return "—"
        return "hedefte" if deger >= hedef else "hedef altı"

    print(f"  Soru sayısı           : {olcum['soru_sayisi']}")
    print(f"  Geçen                 : {olcum['gecen']}")
    print(
        f"  Doğruluk              : {dogruluk:.3f}  "
        f"(hedef ≥ {DOGRULUK_HEDEFI})  {durum(dogruluk, DOGRULUK_HEDEFI)}"
    )
    if kaynak is not None:
        print(
            f"  Kaynak gösterme oranı : {kaynak:.3f}  "
            f"(hedef {KAYNAK_HEDEFI:.2f})  {durum(kaynak, KAYNAK_HEDEFI)}"
        )

    print("\n  Şartname senaryoları:")
    for no, gecti in sorted(olcum["sartname_senaryolari"].items()):
        print(f"    Senaryo {no}: {'geçti' if gecti else 'KALDI'}")

    if olcum["basarisizlar"]:
        print(f"\n Başarısız {len(olcum['basarisizlar'])} soru:\n")
        for s in olcum["basarisizlar"]:
            print(f"    • {s['soru']}")
            for h in s["hatalar"]:
                print(f"        - {h}")
            if ayrintili:
                print(f"        cevap: {s['cevap'][:200]}...")
        print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chatbot test seti (S-10)")
    ap.add_argument("-v", "--ayrintili", action="store_true", help="cevapları da bas")
    args = ap.parse_args(argv)

    olcum = olc()
    if olcum is None:
        print(f"Soru kümesi bulunamadı: {SORU_DOSYASI}")
        return 1

    _yazdir(olcum, args.ayrintili)

    kaynak = olcum["kaynak_gosterme_orani"]
    tamam = olcum["dogruluk"] >= DOGRULUK_HEDEFI and (kaynak is None or kaynak >= KAYNAK_HEDEFI)
    return 0 if tamam else 1


if __name__ == "__main__":
    sys.exit(main())
