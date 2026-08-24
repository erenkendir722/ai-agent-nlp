"""SVARTAL — katılım bankacılığı metin madenciliği.

`.env` BURADA YÜKLENİR — bilerek paket düzeyinde.

Sebep: yapılandırma sabitleri modül seviyesinde `os.getenv` ile okunuyor
(`saglayici.SAGLAYICI_ADI`, `llm.AZAMI_METIN`, `boru_hatti._varsayilan_isci`).
Bunlar içe aktarma anında değerlenir; `.env` daha sonra yüklenirse hiçbir
etkisi olmaz ve kimse fark etmez — yalnız yanlış modelle koşulur.

`override=False`: gerçek ortam değişkeni `.env`'i ezer. Docker Compose ve CI
değerleri dosyadan güçlüdür.
"""

from __future__ import annotations

from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv yoksa ortam değişkenleriyle çalışmaya devam
    pass
else:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
