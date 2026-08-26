# Tek aşamalı, sade imaj. Kurum içi dağıtımda okunabilirlik, birkaç yüz megabayt
# imaj boyutundan daha değerlidir — güvenlik ekibi bu dosyayı okuyacak.
FROM python:3.12-slim

# On-prem sertleştirme: kütüphanelerin varsayılan telemetrisi kapalı.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    ANONYMIZED_TELEMETRY=False \
    DO_NOT_TRACK=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    ARROW_DEFAULT_MEMORY_POOL=system

WORKDIR /uygulama

# Bağımlılıklar önce: kod değişince katman önbelleği bozulmasın.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY app/ ./app/
COPY data/banks.yaml ./data/banks.yaml
# Terim sözlüğü — LLM istemi buradan besleniyor (G-10). Kopyalanmazsa çıkarım
# başlarken hata verir; sessizce terimsiz koşmaz.
COPY docs/TERIM_SOZLUGU.md ./docs/TERIM_SOZLUGU.md
COPY eval/ ./eval/

# TOPLAMA (`crawl`) BU İMAJDA YOK — 26 Ağu 2026.
# Kampanya listeleri JS ile render edildiği için toplama Selenium'a taşındı;
# `python:3.12-slim` içinde Chrome yok. Chrome eklemek imajı birkaç yüz MB
# büyütür ve bankacılık ortamına giden imajın saldırı yüzeyini genişletir —
# bilinçli olarak eklenmedi. İmaj TOPLANMIŞ veriyi işler: `extract`, `seed`,
# `durum` ve arayüz. Yeniden toplama yerel kurulumda yapılır.
#
# Makefile BİLEREK kopyalanmıyor: `python:3.12-slim` içinde `make` ikilisi yok
# ve Makefile'ın varsayılanı `.venv/bin/python` — imajda sanal ortam da yok.
# Kopyalamak, çalışmayan bir arayüzü varmış gibi göstermek olurdu. Konteyner
# içinde boru hattı doğrudan çağrılır (bkz. docs/KURULUM.md):
#     docker compose exec uygulama python -m src.boru_hatti extract
# Bankacılık ortamına giden imajda `make` kurup paket sayısını artırmaktansa
# tek bir çağrı biçimi belgelemek tercih edildi.

# Kök olmayan kullanıcı — bankacılık ortamının standart beklentisi.
RUN useradd --create-home --uid 10001 uygulamaci \
    && mkdir -p /uygulama/data/raw /uygulama/data/processed \
    && chown -R uygulamaci:uygulamaci /uygulama
USER uygulamaci

EXPOSE 8501 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import httpx;httpx.get('http://127.0.0.1:8501/_stcore/health',timeout=4).raise_for_status()"

CMD ["streamlit", "run", "app/Genel_Bakis.py", \
     "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
