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


def test_llm_yalnizca_yerel_ollamaya_baglanir(ag_kilidi: list[str]) -> None:
    """LLM istemcisi varsayılan olarak localhost'a bakmalı.

    Yapılandırma hatası sonucu uzak bir uca yönlendirilmişse, bu test
    kurulumun on-prem iddiasını ihlal ettiğini erkenden söyler.
    """
    from urllib.parse import urlparse

    from src.extraction.llm import OLLAMA_SUNUCU

    sunucu = urlparse(OLLAMA_SUNUCU).hostname or ""
    assert sunucu in IZINLI_HOSTLAR, (
        f"OLLAMA_HOST kurum dışını gösteriyor: {OLLAMA_SUNUCU}. "
        "On-prem iddiası için yerel olmalı."
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
