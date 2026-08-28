"""pytest ön ayarı — PyArrow ayırıcısı.

NEDEN VAR:
    PyArrow 25.0.0 macOS/arm64'te varsayılan `mimalloc` ayırıcısıyla, bir
    thread yeniden başlatılırken çöküyor (SIGSEGV, `mi_thread_init`).
    Streamlit'in `AppTest`'i her sayfa için yeni bir ScriptRunner thread'i
    açtığından `make test` ikinci sayfayı çizerken süreci komple öldürüyordu:

        tests/test_arayuz_sayfalari.py::test_sayfa_istisnasiz_yuklenir
        Fatal Python error: Segmentation fault
          pyarrow/pandas_compat.py, line 638 in convert_column
        make: *** [test] Segmentation fault: 11

    Çöken şey tek bir test değil, SÜRECİN KENDİSİYDİ: pytest özet satırına
    hiç gelinemediği için «kaç test geçti» bilgisi de kayboluyordu ve
    kalan testler hiç koşmuyordu.

    `Makefile` bu değişkeni artık her hedefe geçiriyor; burası çıplak
    `pytest` (IDE, CI, elle koşum) için ikinci kapı.

    Değişken `pyarrow` içe aktarılmadan ÖNCE kurulmalı — ayırıcı import
    anında seçiliyor, sonradan kurmak hiçbir şey değiştirmiyor. `pandas`
    pyarrow'u kendi import'unda getirdiği için bu dosya `pandas`'a dokunan
    hiçbir şeyden sonra çalışamaz; conftest.py pytest'in en erken kancası
    olduğu için burada duruyor.

"""

from __future__ import annotations

import os

os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
