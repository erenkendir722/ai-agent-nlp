"""Sızıntı (egress) testi — şartname 5.9 kanıtı.

*"Müşteri verilerinin kurum dışına çıkmaması"* ve *"dış servislere bağımlı
olmadan çalışabilmesi"* iddiaları, dokümantasyonda yazılı bir vaat olarak
kalmamalı. Bu test onları ÖLÇÜLEBİLİR hâle getirir:

    Çıkarım, karşılaştırma ve chatbot boru hattı çalışırken açılan HER
    soket bağlantısı yakalanır. İzinli host listesi dışına çıkan ilk
    bağlantıda test BAŞARISIZ olur.

Toplama (crawl) katmanı doğal olarak dışarı çıkar — banka sitelerini okur.
O yüzden bu test toplama SONRASI aşamaları hedefler: veri bir kez toplandıktan
sonra sistem tamamen kapalı devre çalışmalıdır.

Jüriye gösterilecek cümle: "Bunu iddia etmiyoruz, test ediyoruz."
"""

from __future__ import annotations

import socket
from datetime import datetime

import pytest

IZINLI_HOSTLAR = {
    "127.0.0.1", "localhost", "::1", "0.0.0.0",
    "ollama",      # docker compose servis adı
    "uygulama",    # docker compose servis adı
}


class DisAgaCikisHatasi(AssertionError):
    """Kurum dışına bağlantı denemesi yakalandı."""


@pytest.fixture
def ag_kilidi(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """socket.connect'i yamalar; izinli olmayan her hedefte hata fırlatır."""
    girisimler: list[str] = []
    gercek_connect = socket.socket.connect

    def denetimli_connect(self: socket.socket, adres, *args, **kwargs):  # type: ignore[no-untyped-def]
        hedef = adres[0] if isinstance(adres, tuple) else str(adres)
        girisimler.append(str(hedef))
        if str(hedef) not in IZINLI_HOSTLAR:
            raise DisAgaCikisHatasi(
                f"Kurum dışına bağlantı denendi: {hedef}. "
                f"İzinli hostlar: {sorted(IZINLI_HOSTLAR)}"
            )
        return gercek_connect(self, adres, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", denetimli_connect)
    return girisimler


ORNEK_METIN = (
    "Konut Finansmanı kampanyası. Aylık kâr payı oranı %1,89'dan başlayan "
    "oranlarla, 120 aya kadar vade imkânı. 5.000.000 TL'ye kadar finansman. "
    "Dosya masrafı alınmaz. Kampanya 31 Aralık 2026 tarihine kadar geçerlidir."
)


def test_kural_katmani_ag_kullanmaz(ag_kilidi: list[str]) -> None:
    """Kural tabanlı çıkarım tamamen yereldir — hiç soket açmamalı."""
    from src.extraction.kural import kurallarla_cikar

    alanlar = kurallarla_cikar(ORNEK_METIN, "https://ornek.test", datetime.now())

    assert alanlar, "Kural katmanı hiçbir alan çıkaramadı"
    assert ag_kilidi == [], f"Kural katmanı ağ bağlantısı açtı: {ag_kilidi}"


def test_normalizasyon_ag_kullanmaz(ag_kilidi: list[str]) -> None:
    from src.preprocessing.normalizasyon import oran_ayristir, tarih_ayristir, vade_ayristir

    assert oran_ayristir("%1,89") == pytest.approx(1.89)
    assert vade_ayristir("120 aya kadar") == 120
    assert tarih_ayristir("31 Aralık 2026") is not None
    assert ag_kilidi == []


def test_karsilastirma_motoru_ag_kullanmaz(ag_kilidi: list[str]) -> None:
    """Karşılaştırma deterministiktir ve LLM dahi kullanmaz."""
    from src.comparison.karsilastirma import toplam_maliyet

    sonuc = toplam_maliyet(500_000, 2.05, 120, 5_000)

    assert sonuc["aylik_taksit"] > 0
    assert ag_kilidi == []


def test_chatbot_yapisal_sorgu_ag_kullanmaz(ag_kilidi: list[str]) -> None:
    """Sayısal cevaplar yerel veritabanından gelir; dış çağrı yoktur."""
    from src.rag.chatbot import niyet_belirle, sayisal_dogrulama

    assert niyet_belirle("A Bankası mı daha avantajlı, C Bankası mı?") is not None
    gecti, _ = sayisal_dogrulama("Bu bilgi veri setinde bulunmuyor.", [])
    assert gecti
    assert ag_kilidi == []


# Çıkarım LLM'inin çıkabileceği TEK dış uç. Yarışma kapsamında T.C.
# Cumhurbaşkanlığı SSB tarafından tahsis edilen EVREN servisi; ticari bir
# bulut sağlayıcısı değildir ve müşteri verisi bu kapsamda kurum dışı
# sayılmamaktadır. Listeye başka bir ad EKLENMEZ.
IZINLI_LLM_UCLARI = IZINLI_HOSTLAR | {"evren-llmapi.ssyz.org.tr"}


def test_llm_ucu_yalnizca_yerel_veya_evren(ag_kilidi: list[str]) -> None:
    """Çıkarım LLM'i yalnız yerele veya EVREN'e bakabilir.

    KAPSAM DEĞİŞTİ — 24 Ağustos 2026: çıkarım katmanı EVREN'e taşındı
    (`src/extraction/saglayici.py`). Dolayısıyla "LLM localhost'a bakmalı"
    artık doğru şart değil. Ama testin görevi aynı kalıyor: yapılandırma
    hatasıyla ÜÇÜNCÜ bir uca yönlendirilmişsek burada yakalanmalı.

    Bu testin gevşemesi, dosyadaki diğer testleri GEVŞETMEZ. Kural,
    normalizasyon, karşılaştırma ve chatbot yapısal sorgu katmanları hâlâ
    `IZINLI_HOSTLAR` ile sınanıyor ve hâlâ hiçbir dış bağlantı yapamıyor —
    sistemin en özgün iddiası olan "sayısal cevap yapısal veriden gelir"
    tam olarak o katmanlarda ölçülüyor.
    """
    from urllib.parse import urlparse

    from src.extraction.saglayici import EVREN_TEMEL_URL, OLLAMA_SUNUCU

    for ad, adres in (("OLLAMA_HOST", OLLAMA_SUNUCU), ("EVREN_TEMEL_URL", EVREN_TEMEL_URL)):
        sunucu = urlparse(adres).hostname or ""
        assert sunucu in IZINLI_LLM_UCLARI, (
            f"{ad} izinsiz bir uca bakıyor: {adres}. "
            f"İzinli uçlar: {sorted(IZINLI_LLM_UCLARI)}"
        )


def test_compose_uygulama_katmanina_saglayici_gecirir() -> None:
    """`docker compose up` hava boşluğu duruşuyla açılmalı — VARSAYILANI ile.

    NEDEN VAR — ölçülmüş çelişki (26 Ağustos 2026):
        `docker-compose.yml` `ollama`'yı `internal: true` ağına koyup hava
        boşluğunu ALTYAPI düzeyinde kuruyordu, ama `uygulama` ve `api`
        servislerine `LLM_SAGLAYICI` GEÇMİYORDU. Kodun varsayılanı ise
        `evren` (`saglayici.SAGLAYICI_ADI`). Sonuç, dosyanın kendi başlığıyla
        çelişmesiydi:

            yanı başında rotası kapalı bir model sunucusu ayakta duruyor,
            uygulama dış HTTPS'e çıkmaya çalışıyor; anahtar yoksa
            `EvrenSaglayici.__init__` daha kurulurken RuntimeError atıyor.

        Bunu yakalayacak hiçbir test yoktu, çünkü bu dosyadaki testlerin
        tamamı KOD yolunu ölçüyor; hatanın yaşadığı yer YAPILANDIRMAYDI.

    İNTERPOLASYON DA REDDEDİLİR — ikinci ölçüm, aynı gün:
        İlk düzeltme `${LLM_SAGLAYICI:-ollama}` yazmıştı, "üzerine yazılabilir
        olsun" diye. `docker compose config` çıktısı hatayı GERİ GETİRDİĞİNİ
        gösterdi: Compose interpolasyonu varsayılana düşmeden önce proje
        kökündeki `.env`'i okur, `.env` ise yerel koşular için
        `LLM_SAGLAYICI=evren` taşır. Sonuç:

            uygulama: LLM_SAGLAYICI: evren       <- hava boşluğu sessizce bitti

        Bu yüzden denetim SABİT dize ister: `${...}` biçimi düzeltmenin
        kendisini geçersiz kılıyor.
    """
    from pathlib import Path

    import yaml

    kok = Path(__file__).resolve().parents[1]
    compose = yaml.safe_load((kok / "docker-compose.yml").read_text(encoding="utf-8"))

    # `ollama` model sunucusudur, sağlayıcı seçmez — denetim uygulama katmanına.
    for servis in ("uygulama", "api"):
        ortam = compose["services"][servis].get("environment") or {}
        assert "LLM_SAGLAYICI" in ortam, (
            f"docker-compose.yml `{servis}` servisine LLM_SAGLAYICI geçirmiyor. "
            "Değişken yoksa kod varsayılanı `evren` olur ve konteyner, rotası "
            "kapalı bir Ollama'nın yanında dış HTTPS'e çıkmaya çalışır."
        )
        deger = str(ortam["LLM_SAGLAYICI"]).strip()
        assert deger == "ollama", (
            f"`{servis}` servisinin LLM_SAGLAYICI değeri {deger!r}. Sabit "
            "'ollama' olmalı — `${...}` interpolasyonu proje kökündeki `.env`'i "
            "okur ve oradaki `evren` değeri varsayılanı sessizce ezer."
        )

        # Sır sızıntısı: sağlayıcı yerelken EVREN anahtarının konteyner
        # ortamında işi yok; `docker inspect` ile okunabilir hâle gelir.
        sizanlar = [ad for ad in ortam if ad.startswith("EVREN_")]
        assert not sizanlar, (
            f"`{servis}` servisine EVREN değişkeni geçiriliyor: {sizanlar}. "
            "Sağlayıcı yerel; bu değişkenler gereksiz ve anahtar konteyner "
            "ortamında görünür olur. EVREN ile koşmanın yolu yerel sanal ortamdır."
        )


def test_kodda_sabit_kodlanmis_dis_api_ucu_yok() -> None:
    """Kaynak kodda bulut LLM sağlayıcısı adresi geçmemeli.

    Bu, çalışma zamanı değil KAYNAK KOD denetimidir: bir dış API ucu
    yanlışlıkla koda girdiyse, çalıştırılmasa bile burada yakalanır.
    """
    from pathlib import Path

    yasakli = (
        "api.openai.com", "api.anthropic.com", "generativelanguage.googleapis.com",
        "api.cohere.ai", "api.mistral.ai", "huggingface.co/api",
    )
    kok = Path(__file__).resolve().parents[1]
    ihlaller: list[str] = []

    for yol in list((kok / "src").rglob("*.py")) + list((kok / "app").rglob("*.py")):
        icerik = yol.read_text(encoding="utf-8")
        for uc in yasakli:
            if uc in icerik:
                ihlaller.append(f"{yol.relative_to(kok)}: {uc}")

    assert not ihlaller, f"Kodda dış servis adresi bulundu: {ihlaller}"
