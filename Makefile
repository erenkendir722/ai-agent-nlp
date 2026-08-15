.PHONY: help kur crawl extract seed durum run api test lint eval lisanslar temiz docker-up docker-down \
        altin-ornekle altin-kalibrasyon altin-denetle altin-uyum altin-derle altin-dogrula \
        altin-dogrulama \
        gorev gorev-dogrula git-kontrol

PYTHON ?= .venv/bin/python
STREAMLIT ?= .venv/bin/streamlit

help:  ## bu yardım metnini göster
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

kur:  ## sanal ortam + bağımlılıklar
	python3.12 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	@echo "✅ Kurulum tamam. Model indirmek için: ollama pull qwen3.5:4b-q4_K_M"

crawl:  ## banka sitelerinden kampanya topla
	$(PYTHON) -m src.boru_hatti crawl

extract:  ## ham kayıtlardan çıkarım yap (kural + LLM hibrit)
	$(PYTHON) -m src.boru_hatti extract

seed:  ## tohum veriden çıkarım yap (ağ gerekmez)
	$(PYTHON) -m src.boru_hatti seed

durum:  ## veritabanı özeti
	$(PYTHON) -m src.boru_hatti durum

run:  ## Streamlit arayüzünü başlat
	$(STREAMLIT) run app/Genel_Bakis.py

api:  ## REST API'yi başlat (3 uç nokta)
	$(PYTHON) -m uvicorn src.api.sunucu:uygulama --host 0.0.0.0 --port 8000

test:  ## testleri koş
	$(PYTHON) -m pytest tests/ -v
	$(PYTHON) -m doctest src/preprocessing/normalizasyon.py -v | tail -1

lint:  ## kod denetimi
	$(PYTHON) -m ruff check src app tests

eval:  ## metrikleri hesapla -> docs/SONUCLAR.md
	$(PYTHON) -m eval.calistir

eval-ablation:  ## ablasyon tablosu (kural / LLM / hibrit)
	$(PYTHON) -m eval.calistir --ablasyon

lisanslar:  ## bağımlılık lisans raporu (şartname 5.10 kanıtı)
	$(PYTHON) -m eval.lisanslar
	@echo "✅ docs/LISANSLAR.md güncellendi"

# --- ablasyon yardımcıları ---
extract-kural:  ## ablasyon: yalnız kural katmanı
	$(PYTHON) -m src.boru_hatti extract --yalniz-kural

extract-llm:  ## ablasyon: yalnız LLM katmanı
	$(PYTHON) -m src.boru_hatti extract --yalniz-llm

# --- Docker ---
docker-up:  ## tek komut kurulum (on-prem kanıtı)
	docker compose up -d
	@echo "✅ Arayüz: http://localhost:8501"

docker-down:
	docker compose down

temiz:  ## türetilmiş dosyaları sil (ham veri KORUNUR)
	rm -f data/katilim.db
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Temizlendi. data/raw/ dokunulmadı."

# --- altın set (H-01 / H-02) ---
altin-ornekle:  ## katmanlı örneklem -> kişi başı etiketleme CSV'si
	@$(PYTHON) tools/altin_set.py ornekle --adet $(or $(adet),60)

altin-kalibrasyon:  ## uyum ölçümü için taze blok çek (altın set dışından)
	@$(PYTHON) tools/altin_set.py kalibrasyon --adet $(or $(adet),10)

altin-denetle:  ## KENDİ etiketlerini pushlamadan önce kontrol et (ad=Esra)
	@$(PYTHON) tools/altin_set.py denetle $(if $(ad),--ad $(ad))

altin-dogrulama:  ## etiketleri kaynak metinle yan yana koyan sayfa (ad=Esra)
	@$(PYTHON) tools/altin_set.py dogrulama $(if $(ad),--ad $(ad))

altin-uyum:  ## etiketleyiciler arası uyum oranı
	@$(PYTHON) tools/altin_set.py uyum

altin-derle:  ## doldurulmuş CSV'ler -> data/gold/altin_set.jsonl
	@$(PYTHON) tools/altin_set.py derle

altin-dogrula:  ## mevcut altın seti denetle
	@$(PYTHON) tools/altin_set.py dogrula

# --- görev panosu ---
gorev:  ## görev durumu (ad=Esra ile kişiye özel)
	@$(PYTHON) tools/gorevler.py $(ad)

gorev-dogrula:  ## görev panosunun bağımlılıklarını denetle
	@$(PYTHON) tools/gorevler.py --dogrula

git-kontrol:  ## GitHub ile senkron mu (pull/push gerekiyor mu)
	@python3 tools/git_kontrol.py baslangic | $(PYTHON) -c "import json,sys; d=json.load(sys.stdin); print(d.get('systemMessage','✅ Temiz'))"
