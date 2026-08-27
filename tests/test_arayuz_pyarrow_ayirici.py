"""PyArrow ayırıcısı — sayfa geçişinde süreç ölmemeli.

NEDEN VAR:
    27 Ağustos'ta `make test` bir testin başarısız olmasıyla değil,
    SÜRECİN ÇÖKMESİYLE bitiyordu:

        make: *** [test] Segmentation fault: 11

    PyArrow 25.0.0 macOS/arm64'te varsayılan `mimalloc` ayırıcısıyla bir
    thread yeniden başlatılırken SIGSEGV veriyor (`mi_thread_init`).
    Streamlit her sayfa geçişinde yeni bir ScriptRunner thread'i açar;
    `st.dataframe` olan ikinci sayfada süreç ölüyordu. Aynı hata `make run`
    altında da vardı: kullanıcı sayfa değiştirince SUNUCU düşüyordu, hata
    sayfası bile çıkmadan.

    Bu testler iki kapıyı da tutuyor:
      1. ayırıcı gerçekten `system` mi (ucuz, doğrudan),
      2. iki ardışık çizim aynı süreçte hayatta kalıyor mu (asıl davranış).

    (2) alt süreçte koşmak ZORUNDA: segfault yakalanabilir bir istisna
    değildir, süreci komple öldürür — testin içinden görülemez, ancak
    çocuk sürecin çıkış kodundan anlaşılır.

    Ayrıntı: docs/ARAYUZ_INCELEME.md — «Ortam» bölümü.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]


def test_ayirici_mimalloc_degil() -> None:
    """Ayırıcı `system` olmalı — `mimalloc` bu platformda çöküyor."""
    import pyarrow as pa

    assert pa.default_memory_pool().backend_name == "system", (
        "PyArrow ayırıcısı `system` değil — sayfa geçişinde segfault riski. "
        "ARROW_DEFAULT_MEMORY_POOL `pyarrow` import'undan önce kurulmalı "
        "(bkz. tests/conftest.py)."
    )


def _veri_var_mi() -> bool:
    try:
        from src.depolama import tum_kayitlar

        return len(tum_kayitlar()) >= 2
    except Exception:
        return False


@pytest.mark.skipif(
    not _veri_var_mi(),
    reason="veritabanı boş ya da erişilemiyor — önce `make extract`",
)
def test_ayni_surecte_iki_cizim_hayatta_kalir() -> None:
    """Asıl regresyon: ikinci çizim süreci öldürmemeli.

    Düzeltme geri alınırsa bu test `exit 139` görür ve kırılır.
    """
    betik = textwrap.dedent(
        """
        import sys
        sys.path.insert(0, {kok!r})
        from streamlit.testing.v1 import AppTest

        for _ in range(2):
            AppTest.from_file({sayfa!r}, default_timeout=300).run()
        print("İKİ ÇİZİM TAMAM")
        """
    ).format(kok=str(KOK), sayfa=str(KOK / "app" / "Genel_Bakış.py"))

    sonuc = subprocess.run(
        [sys.executable, "-c", betik],
        capture_output=True,
        text=True,
        timeout=600,
        cwd=KOK,
    )

    assert sonuc.returncode == 0, (
        f"ikinci çizimde süreç öldü (çıkış {sonuc.returncode}"
        + (" — SIGSEGV)" if sonuc.returncode in (139, -11) else ")")
        + f"\nstderr kuyruğu:\n{sonuc.stderr[-1500:]}"
    )
    assert "İKİ ÇİZİM TAMAM" in sonuc.stdout
