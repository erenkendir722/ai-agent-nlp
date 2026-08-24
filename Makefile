.PHONY: help kur crawl extract extract-yerel saglayici-dogrula seed durum run api test lint eval lisanslar temiz temiz-db docker-up docker-down \
        birim-goc ablasyon eval-gorulmemis \
        altin-ornekle altin-genislet altin-denetle altin-uyum altin-derle \
        gorev gorev-dogrula git-kontrol hava-boslugu sunum veri-kalitesi \
        suresi-gecenleri-ele

PYTHON ?= .venv/bin/python
STREAMLIT ?= .venv/bin/streamlit

# PyArrow'un varsayılan mimalloc ayırıcısı macOS/arm64'te thread yeniden
# başlatılırken çöküyor (SIGSEGV, mi_thread_init). Streamlit her sayfa
# geçişinde yeni ScriptRunner thread'i açtığı için, `st.dataframe` olan bir
# sayfadan çıkınca uygulama komple ölüyor — 18 Ağustos'ta sayfa geçişinde
# yaşandı. Sistem ayırıcısı bu yolu kapatır.
# Ayrıntı: docs/ARAYUZ_INCELEME.md — «Ortam» bölümü.
ARROW_HAVUZ ?= ARROW_DEFAULT_MEMORY_POOL=system

help:  ## bu yardım metnini göster
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

kur:  ## sanal ortam + bağımlılıklar
	python3.12 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	@echo "✅ Kurulum tamam."
	@echo "   EVREN ile koşmak için: .env içine EVREN_API_ANAHTARI yazın."
	@echo "   Yerel yedek için:      ollama pull qwen3.5:4b-q4_K_M"

crawl:  ## banka sitelerinden kampanya topla
	$(PYTHON) -m src.boru_hatti crawl

extract:  ## ham kayıtlardan çıkarım yap (kural + LLM hibrit) — EVREN
	$(PYTHON) -m src.boru_hatti extract

extract-yerel:  ## çıkarım: yerel Ollama ile (hava boşluğu demosu / EVREN düştüğünde)
	LLM_SAGLAYICI=ollama CIKARIM_ISCI=1 AZAMI_METIN=6000 $(PYTHON) -m src.boru_hatti extract

saglayici-dogrula:  ## EVREN bağlantısını ve şema kısıtını sına
	$(PYTHON) -m src.extraction.saglayici

seed:  ## tohum veriden çıkarım yap (ağ gerekmez)
	$(PYTHON) -m src.boru_hatti seed

durum:  ## veritabanı özeti
	$(PYTHON) -m src.boru_hatti durum

run:  ## Streamlit arayüzünü başlat
	$(ARROW_HAVUZ) $(STREAMLIT) run app/Genel_Bakis.py

api:  ## REST API'yi başlat (3 uç nokta)
	$(PYTHON) -m uvicorn src.api.sunucu:uygulama --host 0.0.0.0 --port 8000

test:  ## testleri koş
	$(PYTHON) -m pytest tests/ -v
	$(PYTHON) -m doctest src/preprocessing/normalizasyon.py -v | tail -1

lint:  ## kod denetimi
	$(PYTHON) -m ruff check src app tests eval tools

eval:  ## metrikleri hesapla -> docs/SONUCLAR.md
	$(PYTHON) -m eval.calistir

eval-ablation:  ## ablasyon tablosu (kural / LLM / hibrit)
	$(PYTHON) -m eval.calistir --ablasyon

eval-gorulmemis:  ## görülmemiş metin ölçümü (llm=1 ile LLM katmanı da) -> docs/GORULMEMIS_METIN.md
	$(PYTHON) -m eval.gorulmemis $(if $(llm),--llm)

eval-robust:  ## dayanıklılık ölçümü (şartname 5.2) -> docs/DAYANIKLILIK.md
	$(PYTHON) -m eval.dayaniklilik

veri-kalitesi:  ## veri kalitesi denetimi -> docs/VERI_KALITESI.md (kati=1 ile esik asiminda kirilir)
	$(PYTHON) tools/veri_kalitesi.py $(if $(kati),--kati)

suresi-gecenleri-ele:  ## suresi gecmis kampanyalari sil (uygula=1 olmadan yalniz gosterir)
	$(PYTHON) tools/suresi_gecenleri_ele.py $(if $(uygula),--uygula)

lisanslar:  ## bağımlılık lisans raporu (şartname 5.10 kanıtı)
	$(PYTHON) -m eval.lisanslar
	@echo "✅ docs/LISANSLAR.md güncellendi"

ablasyon:  ## ATOMİK ablasyon: üç yapılandırma tek süreçte, tek kod izi (hizli=1 ile LLM'siz)
	$(PYTHON) -m eval.ablasyon $(if $(hizli),--yalniz-kural)
	@echo "Tablo için: make eval-ablation"

# --- ablasyon yardımcıları ---
# NOT: Bu iki hedef TEK yapılandırma koşar ve satırların aynı kodla koşulmasını
# GARANTİ ETMEZ. Ablasyon tablosu için `make ablasyon` kullanın; 18 Ağustos'ta
# tablo tam olarak bu yüzden karşılaştırılamaz hâle gelmişti.
extract-kural:  ## ablasyon: yalnız kural katmanı
	$(PYTHON) -m src.boru_hatti extract --yalniz-kural

extract-llm:  ## ablasyon: yalnız LLM katmanı
	$(PYTHON) -m src.boru_hatti extract --yalniz-llm

# --- Docker ---
docker-up:  ## tek komut kurulum (on-prem kanıtı)
	docker compose up -d
	@echo "✅ Arayüz: http://localhost:8501"

hava-boslugu:  ## hava boşluğu ölçümü — konteynerden dışarı çıkılabiliyor mu (şartname 5.9)
	$(PYTHON) tools/hava_boslugu.py

docker-down:
	docker compose down

temiz:  ## önbellekleri sil (ham veri VE veritabanı KORUNUR)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
	find . -name .DS_Store -delete 2>/dev/null || true
	@echo "✅ Önbellekler silindi. data/ dokunulmadı."
	@echo "   Veritabanını da silmek için: make temiz-db"

temiz-db:  ## ⚠️ data/katilim.db'yi sil — DEPODA TAKİPLİ DOSYA, yeniden üretmen gerekir
	@echo "⚠️  data/katilim.db artık depoda TAKİPLİ (590 kampanya, commit cc2b9af)."
	@echo "   Silersen geri getirmek için: git checkout data/katilim.db"
	@echo "   Yeniden üretmek ~5 dk sürer: make extract"
	@printf "   Devam? [e/H] " && read c && [ "$$c" = "e" ] && rm -f data/katilim.db && echo "silindi" || echo "iptal"

# --- altın set (H-01 / H-02) ---
altin-ornekle:  ## katmanlı örneklem -> kişi başı CSV + okuma kâğıdı
	@$(PYTHON) tools/altin_set.py ornekle --adet $(or $(adet),60)

altin-genislet:  ## zayıf alanlar için ek örneklem planı (hedef=20 ile hedef N)
	@$(PYTHON) tools/altin_set.py genislet --hedef-n $(or $(hedef),20)

altin-denetle:  ## KENDİ etiketlerini pushlamadan önce kontrol et (ad=Esra)
	@$(PYTHON) tools/altin_set.py denetle $(if $(ad),--ad $(ad))

altin-uyum:  ## etiketleyiciler arası uyum oranı
	@$(PYTHON) tools/altin_set.py uyum

altin-derle:  ## doldurulmuş CSV'ler -> data/gold/altin_set.jsonl
	@$(PYTHON) tools/altin_set.py derle

birim-goc:  ## eski veritabanına birim ekler (şema v1.1.0 -> v1.2.0)
	$(PYTHON) tools/birim_goc.py $(if $(deneme),--deneme)

# --- görev panosu ---
gorev:  ## görev durumu (ad=Esra ile kişiye özel)
	@$(PYTHON) tools/gorevler.py $(ad)

gorev-dogrula:  ## görev panosunun bağımlılıklarını denetle
	@$(PYTHON) tools/gorevler.py --dogrula

git-kontrol:  ## GitHub ile senkron mu (pull/push gerekiyor mu)
	@python3 tools/git_kontrol.py baslangic | $(PYTHON) -c "import json,sys; d=json.load(sys.stdin); print(d.get('systemMessage','✅ Temiz'))"

# --- sunum ---
# HTML kaynaktan PDF üretir. Carlito fontu docs/sunum/fontlar/ içinde gömülü
# durur (LibreOffice dağıtımından, SIL Open Font License) — makinede kurulu
# olmasına gerek yok. Tarayıcı yolu değişirse KROM değişkeniyle geçilebilir.
KROM ?= /Applications/Google Chrome.app/Contents/MacOS/Google Chrome

sunum:  ## docs/sunum/sunum.html -> docs/sunum/Svartal_Sunum.pdf (8 sayfa, 16:9)
	@"$(KROM)" --headless --disable-gpu --no-sandbox \
	  --allow-file-access-from-files --no-pdf-header-footer \
	  --print-to-pdf="$(CURDIR)/docs/sunum/Svartal_Sunum.pdf" \
	  "file://$(CURDIR)/docs/sunum/sunum.html" 2>/dev/null
	@echo "✅ docs/sunum/Svartal_Sunum.pdf"
