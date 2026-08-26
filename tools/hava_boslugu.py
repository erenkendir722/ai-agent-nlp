"""Hava boşluğu (air-gap) ölçümü — şartname 5.9 kanıtı.

NEDEN VAR:
    On-prem iddiası "dışarı çağrı yapmıyoruz" demekle kanıtlanmaz. Bu betik
    KONTEYNERİN İÇİNDEN dışarıya çıkmayı DENER ve başarısız olduğunu gösterir.
    Ölçüm tekrar edilebilir olmalı ki jüri önünde tek komutla gösterilebilsin.

NE ÖLÇER:
    Her servisin dışarıya çıkış durumu ayrı ayrı. `ollama` çıkamamalı
    (`internal: true` ağı). `uygulama` ve `api` port yayını için `sunum`
    ağında da oldukları için ÇIKABİLİR — bu bilinen ve belgelenmiş sınırdır,
    hata değildir. Betik bunu gizlemez, ayrı ayrı raporlar.

    18 Ağustos 2026'da öğrenilen ders: `internal: true` tek ağda açılırsa
    Docker `ports:` yayınını da düşürür ve arayüz erişilemez olur. Bu yüzden
    iki ağ var. Ayrıntı: docs/KURULUM.md «Hava boşluğu».

KULLANIM:
    make hava-boslugu
"""

from __future__ import annotations

import json
import subprocess
import sys

# Dışarıya çıkış denemesi için hedefler. DNS'e güvenmemek için ham IP:
# DNS zaten engelliyse test "ad çözülemedi" ile biter ve rota engelini ölçemeyiz.
HEDEFLER = [
    ("Google DNS", "8.8.8.8", 53),
    ("Cloudflare", "1.1.1.1", 443),
]
ALAN_ADLARI = ["huggingface.co", "api.openai.com"]

# Dışarı çıkması BEKLENMEYEN servisler. Buradaki bir sızıntı gerçek kusurdur.
KAPALI_OLMALI = ["ollama"]


def _kabuk(servis: str, betik: str, kabuk: str = "bash") -> tuple[int, str]:
    sonuc = subprocess.run(
        ["docker", "compose", "exec", "-T", servis, kabuk, "-c", betik],
        capture_output=True,
        text=True,
        timeout=90,
    )
    return sonuc.returncode, (sonuc.stdout + sonuc.stderr).strip()


def _tcp_denemesi(servis: str, ip: str, port: int) -> bool:
    """TCP bağlantısı kurulabiliyor mu? `bash` /dev/tcp ile.

    DİKKAT — `sh` (dash) `/dev/tcp` DESTEKLEMEZ ve her zaman başarısız olur.
    18 Ağu'da bu yüzden yanlış «engellendi» raporlandı: prob bozuktu, sonuç
    değil. Bu yüzden `bash` kullanılır ve ayrıca `_prob_saglam_mi()` ile
    probun çalıştığı KANITLANIR. Kanıtlanmadan hiçbir «engellendi» sonucuna
    güvenilmez.
    """
    betik = f'timeout 4 bash -c "echo > /dev/tcp/{ip}/{port}" 2>/dev/null && echo ACIK || echo KAPALI'
    _, cikti = _kabuk(servis, betik)
    return cikti.strip().endswith("ACIK")


def _prob_saglam_mi(servis: str) -> tuple[bool, str]:
    """POZİTİF KONTROL: ulaşılabilen bir hedefe bağlanmayı dene.

    Ulaşılması GEREKEN bir hedef (kendi localhost'u ya da ollama) kapalı
    görünüyorsa, prob bozuktur — o servisin «engellendi» sonuçları çöptür.
    """
    if _kabuk(servis, "command -v bash >/dev/null")[0] != 0:
        return False, "bash yok — /dev/tcp probu çalışmaz"

    hedef = ("127.0.0.1", 11434) if servis == "ollama" else ("ollama", 11434)
    if _tcp_denemesi(servis, *hedef):
        return True, f"pozitif kontrol geçti ({hedef[0]}:{hedef[1]} ulaşıldı)"
    return False, f"pozitif kontrol BAŞARISIZ ({hedef[0]}:{hedef[1]} kapalı görünüyor)"


def _cikis_var_mi(servis: str) -> tuple[bool, list[str]]:
    """Servis dışarı çıkabiliyor mu? (çıkabiliyorsa True) + satır satır kanıt."""
    satirlar: list[str] = []
    cikabiliyor = False

    for ad, ip, port in HEDEFLER:
        acik = _tcp_denemesi(servis, ip, port)
        cikabiliyor |= acik
        satirlar.append(f"{' ULASILDI' if acik else ' engellendi'} {ad} ({ip}:{port})")

    for alan in ALAN_ADLARI:
        _, cikti = _kabuk(servis, f'getent hosts {alan} >/dev/null 2>&1 && echo ACIK || echo KAPALI')
        acik = cikti.strip().endswith("ACIK")
        cikabiliyor |= acik
        satirlar.append(f"{' COZULDU ' if acik else ' engellendi'} DNS {alan}")

    return cikabiliyor, satirlar


def _aglar() -> dict[str, list[str]]:
    """Hangi konteyner hangi ağlarda + ağ internal mi."""
    cikti: dict[str, list[str]] = {}
    for kap in ["katilim-ollama", "katilim-uygulama", "katilim-api"]:
        r = subprocess.run(
            ["docker", "inspect", kap, "--format", "{{json .NetworkSettings.Networks}}"],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            continue
        cikti[kap] = sorted(json.loads(r.stdout).keys())
    return cikti


def main() -> int:
    print("\n=== HAVA BOŞLUĞU ÖLÇÜMÜ (şartname 5.9) ===\n")

    aglar = _aglar()
    if not aglar:
        print(" Konteyner bulunamadı. Önce: docker compose up -d")
        return 1

    print("Ağ yerleşimi:")
    for kap, ag_listesi in aglar.items():
        isaretli = []
        for ag in ag_listesi:
            r = subprocess.run(
                ["docker", "network", "inspect", ag, "--format", "{{.Internal}}"],
                capture_output=True, text=True,
            )
            ic = r.stdout.strip() == "true"
            isaretli.append(f"{ag}{' [internal]' if ic else ''}")
        print(f"  {kap:20} {', '.join(isaretli)}")

    print()
    kusur = 0
    for servis in ["ollama", "uygulama", "api"]:
        saglam, not_ = _prob_saglam_mi(servis)
        if not saglam:
            print(f" [{servis}] ÖLÇÜM GEÇERSİZ — {not_}")
            print("      Bu servisin sonuçlarına GÜVENMEYİN.\n")
            kusur += 1
            continue

        cikabiliyor, satirlar = _cikis_var_mi(servis)
        beklenen_kapali = servis in KAPALI_OLMALI

        if beklenen_kapali:
            baslik = " İZOLE" if not cikabiliyor else " SIZINTI"
            if cikabiliyor:
                kusur += 1
        else:
            baslik = "ℹ çıkış var (bilinen sınır)" if cikabiliyor else " İZOLE"

        print(f"  [{servis}] {baslik}   ({not_})")
        for satir in satirlar:
            print(f"      {satir}")
        print()

    print("-" * 62)
    if kusur:
        print(f" {kusur} serviste beklenmeyen çıkış var — `internal: true` bozulmuş.")
        return 1

    print(" Model sunucusunun (ollama) internete rotası YOK.")
    print()
    print("   Sınır — sunumda böyle söyleyin:")
    print("   «Model sunucusunun internete rotası altyapı düzeyinde kapalı.")
    print("    Uygulama katmanı port yayını için ayrı ağda; onun dış çağrı")
    print("    yapmadığı tests/test_sizinti_yok.py ile kanıtlı (6 test).")
    print("    Tam kapalı gösterim için host'un Wi-Fi'ı kapatılır.»")
    print()
    print("   «Hiçbir konteyner dışarı çıkamıyor» DEMEYİN — jüri")
    print("   `docker network inspect` ile bakabilir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
