#!/usr/bin/env python3
"""Git senkron denetimi — çalışma başında ve sonunda otomatik uyarı.

    python tools/git_kontrol.py baslangic   # uzak depoyu getir, geride miyiz?
    python tools/git_kontrol.py bitis       # pushlanmamış iş var mı?

NEDEN VAR:
    Dört kişi aynı depoda çalışıyor. İki klasik hata projeyi saatlerce geri atar:

      1. PULL ETMEDEN BAŞLAMAK → arkadaşının değiştirdiği dosyayı sen de
         değiştirirsin, çakışma çıkar; kötü ihtimalde onun işini ezersin.
      2. PUSHLAMADAN BIRAKMAK  → yaptığın iş kimseye ulaşmaz. Bloke olan
         arkadaşın (bkz. GOREVLER.md bağımlılıkları) boşuna bekler.

    Bu betik `.claude/settings.json` içindeki SessionStart ve Stop hook'larına
    bağlıdır; yani yapay zekâ hatırlamayı unutsa bile harness çalıştırır.
    Hatırlatma modelin iyi niyetine değil, koda bağlıdır.

Çıktı, Claude Code hook sözleşmesine uygun JSON'dur:
    systemMessage      -> kullanıcıya gösterilir
    additionalContext  -> modele bağlam olarak enjekte edilir
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
ZAMAN_ASIMI = 15  # saniye; ağ yoksa oturumu bekletmeyelim


def _git(*argumanlar: str, zaman_asimi: int = 5) -> tuple[int, str]:
    """Git komutu çalıştırır. (çıkış_kodu, çıktı) döner; asla exception atmaz."""
    try:
        sonuc = subprocess.run(
            ["git", *argumanlar],
            cwd=KOK,
            capture_output=True,
            text=True,
            timeout=zaman_asimi,
        )
        return sonuc.returncode, (sonuc.stdout + sonuc.stderr).strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return 1, ""


def _git_deposu_mu() -> bool:
    kod, _ = _git("rev-parse", "--git-dir")
    return kod == 0


def _dal() -> str:
    _, ad = _git("rev-parse", "--abbrev-ref", "HEAD")
    return ad or "main"


def _sayi(cikti: str) -> int:
    try:
        return int(cikti.strip())
    except (ValueError, AttributeError):
        return 0


def _cikti(mesaj: str | None, baglam: str | None, olay: str) -> None:
    """Hook sözleşmesine uygun JSON yaz. Mesaj yoksa sessiz kal."""
    if mesaj is None and baglam is None:
        print(json.dumps({"suppressOutput": True}))
        return
    veri: dict[str, object] = {}
    if mesaj:
        veri["systemMessage"] = mesaj
    if baglam:
        veri["hookSpecificOutput"] = {
            "hookEventName": olay,
            "additionalContext": baglam,
        }
    print(json.dumps(veri, ensure_ascii=False))


# ---------------------------------------------------------------------------
# ÇALIŞMA BAŞLANGICI
# ---------------------------------------------------------------------------


def baslangic() -> int:
    if not _git_deposu_mu():
        _cikti(None, None, "SessionStart")
        return 0

    dal = _dal()

    # Uzak depoyu getir. Ağ yoksa sessizce devam et — çevrimdışı çalışmak
    # engellenmemeli (bu proje zaten on-prem çalışabilmeyi iddia ediyor).
    kod, _ = _git("fetch", "--quiet", "origin", zaman_asimi=ZAMAN_ASIMI)
    if kod != 0:
        _cikti(
            " GitHub'a ulaşılamadı — uzak depo durumu bilinmiyor. "
            "Bağlantın varsa `git pull` yapmayı unutma.",
            "Uzak depo kontrol edilemedi (ağ yok veya kimlik doğrulama gerekli). "
            "Kullanıcıya çalışmaya başlamadan önce `git pull` yapmasını hatırlat.",
            "SessionStart",
        )
        return 0

    _, gerideki = _git("rev-list", "--count", f"HEAD..origin/{dal}")
    _, ilerideki = _git("rev-list", "--count", f"origin/{dal}..HEAD")
    _, kirli = _git("status", "--porcelain")

    geride = _sayi(gerideki)
    ileride = _sayi(ilerideki)
    degisiklik = len([s for s in kirli.split("\n") if s.strip()])

    if geride == 0 and ileride == 0 and degisiklik == 0:
        _cikti(
            f" Depo güncel ({dal}) — çalışmaya başlayabilirsin.",
            f"Git durumu temiz ve origin/{dal} ile eşit. Pull gerekmiyor.",
            "SessionStart",
        )
        return 0

    satirlar = [" ÇALIŞMAYA BAŞLAMADAN ÖNCE"]
    baglam = ["ÇALIŞMA BAŞLANGICI GIT DURUMU:"]

    if geride:
        satirlar.append(
            f" GitHub'da {geride} yeni commit var — **PULL ETMEDEN BAŞLAMA**"
        )
        satirlar.append("      git pull --rebase origin " + dal)
        baglam.append(
            f"- Yerel depo origin/{dal} dalının {geride} commit GERİSİNDE. "
            "KULLANICIYA İLK İŞ OLARAK `git pull --rebase` YAPMASINI SÖYLE. "
            "Pull yapılmadan dosya düzenlemek çakışmaya ve arkadaşlarının "
            "işinin ezilmesine yol açar."
        )

    if degisiklik:
        satirlar.append(f" {degisiklik} dosyada kaydedilmemiş değişiklik var")
        baglam.append(
            f"- Çalışma ağacında {degisiklik} kaydedilmemiş değişiklik var. "
            "Pull öncesi bunları commit'lemek veya stash'lemek gerekebilir."
        )

    if ileride:
        satirlar.append(f" {ileride} commit pushlanmamış — sonunda pushla")
        baglam.append(f"- {ileride} yerel commit henüz pushlanmamış.")

    _cikti("\n".join(satirlar), "\n".join(baglam), "SessionStart")
    return 0


# ---------------------------------------------------------------------------
# ÇALIŞMA SONU
# ---------------------------------------------------------------------------


def bitis() -> int:
    if not _git_deposu_mu():
        _cikti(None, None, "Stop")
        return 0

    dal = _dal()
    _, kirli = _git("status", "--porcelain")
    _, ilerideki = _git("rev-list", "--count", f"origin/{dal}..HEAD")

    degisiklik = len([s for s in kirli.split("\n") if s.strip()])
    ileride = _sayi(ilerideki)

    # Yapacak bir şey yoksa sessiz kal — her durakta uyarı vermek gürültü olur
    # ve gürültülü uyarı okunmaz hâle gelir.
    if degisiklik == 0 and ileride == 0:
        _cikti(None, None, "Stop")
        return 0

    satirlar = [" İŞİNİ BIRAKMADAN ÖNCE"]
    baglam = ["ÇALIŞMA SONU GIT DURUMU — kullanıcıya hatırlat:"]

    if degisiklik:
        satirlar.append(f" {degisiklik} dosya kaydedilmemiş — commit'le:")
        satirlar.append('      git add -A && git commit -m "..."')
        baglam.append(
            f"- {degisiklik} dosyada kaydedilmemiş değişiklik var. "
            "Kullanıcıya commit'lemesini söyle."
        )

    if ileride:
        satirlar.append(f" {ileride} commit pushlanmamış — **PUSHLA**:")
        satirlar.append(f"      git push origin {dal}")
        baglam.append(
            f"- {ileride} commit pushlanmamış. KULLANICIYA `git push origin {dal}` "
            "YAPMASINI SÖYLE. Pushlanmayan iş takım arkadaşlarına ulaşmaz ve "
            "GOREVLER.md'de bu işi bekleyen kişiler boşuna bekler."
        )

    satirlar.append("   (GOREVLER.md'de bitirdiğin görevin yanına [x] atmayı unutma)")

    _cikti("\n".join(satirlar), "\n".join(baglam), "Stop")
    return 0


def main(argv: list[str]) -> int:
    kip = argv[1] if len(argv) > 1 else "baslangic"
    if kip in ("baslangic", "start", "SessionStart"):
        return baslangic()
    if kip in ("bitis", "stop", "Stop"):
        return bitis()
    print(f"Bilinmeyen kip: {kip}. Kullanım: git_kontrol.py [baslangic|bitis]")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
