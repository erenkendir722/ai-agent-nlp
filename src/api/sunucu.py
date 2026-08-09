"""İnce REST API — 3 uç nokta (Katman 5).

Amaç, ayrı bir mikroservis mimarisi kurmak DEĞİL. Amaç, "kurum sistemlerine
entegre edilebilirlik" iddiasını somut kanıta çevirmek: aynı çekirdek paket,
Streamlit'in yanı sıra HTTP üzerinden de kullanılabiliyor. Bu dosya bilinçli
olarak incedir — iş mantığı `src/` altındaki modüllerde, burada yalnız aktarım.

Çalıştırma:  make api      ->  http://localhost:8000/docs
"""

from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from src.comparison.karsilastirma import Agirliklar, Kriter, sirala, uyarilar
from src.depolama import kampanyalari_getir, tum_kayitlar
from src.rag.chatbot import sor
from src.schema import Kampanya

uygulama = FastAPI(
    title="Katılım Bankacılığı Kampanya API",
    description=(
        "Katılım bankalarının kampanya metinlerinden yapısal bilgi çıkarımı, "
        "karşılaştırma ve soru-cevap. Tüm veri kurum içinde kalır; dış servis "
        "çağrısı yoktur."
    ),
    version="0.1.0",
)


class CikarimIstegi(BaseModel):
    metin: str = Field(min_length=20, description="Kampanya metni")
    url: str = Field(default="manuel://girdi", description="Kaynak URL (izlenebilirlik)")
    banka_adi: str = "Bilinmiyor"
    banka_kodu: str = "MANUEL"


class SoruIstegi(BaseModel):
    soru: str = Field(min_length=3)


@uygulama.get("/saglik", tags=["sistem"])
def saglik() -> dict[str, object]:
    """Ayakta mı? Docker healthcheck ve air-gap demosu bunu kullanır."""
    kayitlar = tum_kayitlar()
    return {
        "durum": "ayakta",
        "kampanya_sayisi": len(kayitlar),
        "zaman": datetime.now().isoformat(),
        "dis_bagimlilik": False,
    }


@uygulama.post("/extract", tags=["çıkarım"])
def extract(istek: CikarimIstegi) -> Kampanya:
    """Serbest metinden yapısal kampanya kaydı üretir (kanıt zinciriyle)."""
    from src.extraction.uzlastirici import kampanya_cikar
    from src.schema import HamKayit

    kayit = HamKayit(
        banka_kodu=istek.banka_kodu,
        banka_adi=istek.banka_adi,
        url=istek.url,
        cekim_tarihi=datetime.now(),
        http_durum=200,
        govde_metin=istek.metin,
    )
    kampanya, _ = kampanya_cikar(kayit)
    return kampanya


@uygulama.get("/compare", tags=["karşılaştırma"])
def compare(
    kriter: Kriter = Query(default=Kriter.EN_AVANTAJLI),
    kampanya_turu: str | None = Query(default=None),
    banka_kodu: str | None = Query(default=None),
    kar_payi_agirligi: float = Query(default=0.40, ge=0.0, le=1.0),
    masraf_agirligi: float = Query(default=0.25, ge=0.0, le=1.0),
    vade_agirligi: float = Query(default=0.20, ge=0.0, le=1.0),
    odul_agirligi: float = Query(default=0.15, ge=0.0, le=1.0),
) -> dict[str, object]:
    """Şartname 5.7'deki beş kritere göre sıralanmış karşılaştırma."""
    kayitlar = kampanyalari_getir(banka_kodu=banka_kodu, kampanya_turu=kampanya_turu)
    if not kayitlar:
        raise HTTPException(status_code=404, detail="Ölçütlere uyan kampanya yok")

    agirliklar = Agirliklar(
        kar_payi=kar_payi_agirligi,
        masraf=masraf_agirligi,
        vade=vade_agirligi,
        odul=odul_agirligi,
    )
    sirali = sirala(kayitlar, kriter, agirliklar)

    return {
        "kriter": kriter.value,
        "agirliklar": agirliklar.normalize().__dict__,
        "uyarilar": uyarilar(sirali),
        "sonuclar": [
            {
                "banka_adi": k.banka_adi,
                "kampanya_turu": k.kampanya_turu,
                "kar_payi_orani": k.kar_payi_orani,
                "vade_ay_max": k.vade_ay_max,
                "finansman_tutari_max": k.finansman_tutari_max,
                "tahsis_ucreti": k.tahsis_ucreti,
                "masrafsiz_mi": k.masrafsiz_mi,
                "odul_miktari": k.odul_miktari,
                "guven": k.ortalama_guven,
                "kaynak_url": k.kaynak_url,
                "cekim_tarihi": k.cekim_tarihi.isoformat(),
            }
            for k in sirali
        ],
    }


@uygulama.post("/ask", tags=["chatbot"])
def ask(istek: SoruIstegi) -> dict[str, object]:
    """Kaynak gösteren, sayısal doğrulamadan geçmiş cevap."""
    cevap = sor(istek.soru)
    return {
        "soru": istek.soru,
        "niyet": cevap.niyet.value,
        "cevap": cevap.metin,
        "uyarilar": cevap.uyarilar,
        "sayisal_dogrulama_gecti": cevap.dogrulama_gecti,
        "kaynaklar": [
            {"banka_adi": k.banka_adi, "url": k.url, "cekim_tarihi": k.cekim_tarihi}
            for k in cevap.kaynaklar
        ],
    }
