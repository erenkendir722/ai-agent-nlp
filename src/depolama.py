"""Depolama katmanı — SQLite + SQLAlchemy (Katman 3).

Tasarım kararı — İKİ TEMSİL BİR ARADA:
    1. Düz sütunlar (kar_payi_orani REAL, vade_ay_max INTEGER ...)
       Karşılaştırma motoru ve dashboard sıralaması bunlar üzerinden çalışır.
       SQL ile sıralamak, 300 kaydı Python'da gezmekten hem hızlı hem doğrudur.
    2. `tam_kayit` JSON sütunu
       Kanıt zincirinin tamamı (alıntı, karakter aralığı, güven, yöntem).
       Kullanıcı bir satırı açtığında gösterilen şey budur.

Düz sütunlar türetilmiştir; doğruluk kaynağı her zaman `tam_kayit`'tır.

SQLAlchemy kullanmamızın sebebi PostgreSQL'e geçişin bir yapılandırma
değişikliği olması. Jüriye "ölçeklenebilir mi?" sorusunun cevabı: `VERITABANI_URL`
ortam değişkenini değiştirin, kod aynı kalır.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from src.schema import SAYISAL_ALANLAR, Kampanya

KOK = Path(__file__).resolve().parents[1]
VARSAYILAN_VERITABANI = f"sqlite:///{KOK / 'data' / 'katilim.db'}"
VERITABANI_URL = os.getenv("VERITABANI_URL", VARSAYILAN_VERITABANI)


CIKARIM_KAYNAKLARI: tuple[str, ...] = (
    "src/schema.py",
    "src/preprocessing/normalizasyon.py",
    "src/extraction",
)
"""Çıktıyı belirleyen kaynaklar — parmak izi bunlardan hesaplanır.

Bu listeye giren dosya değiştiğinde veritabanındaki değerler eskir. Toplayıcı
(`src/collector/`) ve arayüz (`app/`) DIŞARIDA: ham metni değiştirmezler,
dolayısıyla aynı ham metinden aynı değerler çıkar.
"""


class Temel(DeclarativeBase):
    pass


class KampanyaKaydi(Temel):
    """Kanonik kampanya tablosu."""

    __tablename__ = "kampanyalar"

    kampanya_id: Mapped[str] = mapped_column(String(64), primary_key=True)

    banka_kodu: Mapped[str] = mapped_column(String(32), index=True)
    banka_adi: Mapped[str] = mapped_column(String(160))
    kaynak_url: Mapped[str] = mapped_column(Text)
    cekim_tarihi: Mapped[datetime] = mapped_column(DateTime, index=True)

    # -- Sınıflandırma (sorgulanabilir) --
    kampanya_turu: Mapped[str | None] = mapped_column(String(64), index=True)
    urun_turu: Mapped[str | None] = mapped_column(String(160))
    hedef_kitle: Mapped[str | None] = mapped_column(String(64), index=True)

    # -- Sayısal alanlar (karşılaştırma motorunun sıralama anahtarları) --
    kar_payi_orani: Mapped[float | None] = mapped_column(Float, index=True)
    finansman_tutari_max: Mapped[float | None] = mapped_column(Float)
    vade_ay_max: Mapped[int | None] = mapped_column(Integer, index=True)
    taksit_sayisi: Mapped[int | None] = mapped_column(Integer)
    tahsis_ucreti: Mapped[float | None] = mapped_column(Float)
    odul_miktari: Mapped[float | None] = mapped_column(Float)
    indirim_orani: Mapped[float | None] = mapped_column(Float)
    alisveris_puani: Mapped[float | None] = mapped_column(Float)
    masrafsiz_mi: Mapped[bool | None] = mapped_column(Boolean)
    kampanya_bitis: Mapped[date | None] = mapped_column(Date)

    # -- Kalite göstergeleri --
    ortalama_guven: Mapped[float] = mapped_column(Float, default=0.0)
    doluluk_orani: Mapped[float] = mapped_column(Float, default=0.0)

    # -- Kanıt zinciri ve köken --
    tam_kayit: Mapped[dict] = mapped_column(JSON)
    ham_metin: Mapped[str] = mapped_column(Text, default="")

    def kampanyaya_cevir(self) -> Kampanya:
        """JSON sütunundan tam kanıt zincirli nesneyi geri kurar."""
        return Kampanya.model_validate(self.tam_kayit)


class CikarimKosusu(Temel):
    """Çıkarımın NE ZAMAN ve HANGİ KODLA koştuğunun kaydı.

    NEDEN VAR — 15 Ağustos'ta yaşanan hata:
        Veritabanı 17:49'da yazıldı, çıkarım düzeltmeleri 18:05'te commit
        edildi. `docs/SONUCLAR.md` bir gün boyunca güncel göründü ama
        düzeltmeleri içermeyen sayıları taşıyordu. Kimse fark etmedi; sunuma
        yanlış rakam gitmesine bir adım kalmıştı.

        `cekim_tarihi` bunu yakalayamaz — o kampanyanın TOPLANDIĞI tarihtir,
        çıkarımın koştuğu tarih değil. Aradaki farkı tutan hiçbir alan yoktu.

    `kod_parmak_izi` neden zaman damgasından daha güvenilir:
        Zaman karşılaştırması dosya mtime'ına muhtaçtır; git checkout mtime'ı
        bozar, temiz klonda her şey «yeni» görünür. Parmak izi içeriğe bakar:
        kod gerçekten değiştiyse değişir, checkout'tan etkilenmez.
    """

    __tablename__ = "cikarim_kosulari"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zaman: Mapped[datetime] = mapped_column(DateTime, index=True)
    yapilandirma: Mapped[str] = mapped_column(String(16))
    """`kural` | `llm` | `hibrit` — ablasyon tablosunun hangi satırı olduğu.

    Ablasyon koşuları aynı veritabanının üzerine yazar. Bu alan olmadan
    `make extract-kural && make eval` sonrasında rapora bakan biri, kural-only
    sayıları hibrit sanır."""
    kayit_sayisi: Mapped[int] = mapped_column(Integer, default=0)
    kod_parmak_izi: Mapped[str] = mapped_column(String(16))


# ---------------------------------------------------------------------------
# Oturum yönetimi
# ---------------------------------------------------------------------------

_motorlar: dict[str, Any] = {}
"""URL başına motor. Tek global motor DEĞİL — sebebi önemli:

Bu modüldeki her fonksiyon `url` parametresi ilan ediyor. Tek global motorla
o parametre yalnız İLK çağrıda işe yarardı; sonraki her çağrı, farklı bir URL
verilse bile ilk açılan veritabanına giderdi. Test geçici bir veritabanı
isterken üretim veritabanına yazabilirdi.

Motorlar süreç boyunca yaşar; havuzu her seferinde kurmak SQLite'ta da
pahalıdır, bu yüzden önbellek korunuyor — yalnız anahtarı URL oldu."""


def motor(url: str = VERITABANI_URL):
    if url not in _motorlar:
        yeni = create_engine(url, echo=False, future=True)
        Temel.metadata.create_all(yeni)
        _motorlar[url] = yeni
    return _motorlar[url]


def oturum(url: str = VERITABANI_URL) -> Session:
    return Session(motor(url), future=True)


def semayi_kur(url: str = VERITABANI_URL) -> None:
    """`make init-db` — tabloları oluşturur."""
    Temel.metadata.create_all(motor(url))


# ---------------------------------------------------------------------------
# Yazma
# ---------------------------------------------------------------------------


def _duz_deger(kampanya: Kampanya, alan_adi: str) -> object:
    alan = getattr(kampanya, alan_adi, None)
    return alan.deger if alan is not None and alan.var_mi else None


def kaydet(kampanyalar: Kampanya | list[Kampanya], url: str = VERITABANI_URL) -> int:
    """Kampanyaları yazar/günceller (upsert). Yazılan kayıt sayısını döner.

    Aynı kampanya_id tekrar geldiğinde ÜZERİNE yazılır — yeniden çekim
    yinelenen kayıt üretmez. Kimlik deterministik olduğu için bu güvenlidir.
    """
    if isinstance(kampanyalar, Kampanya):
        kampanyalar = [kampanyalar]

    with oturum(url) as oturum_:
        for kampanya in kampanyalar:
            duz: dict[str, object] = {ad: _duz_deger(kampanya, ad) for ad in SAYISAL_ALANLAR}
            duz["masrafsiz_mi"] = _duz_deger(kampanya, "masrafsiz_mi")
            duz["kampanya_bitis"] = _duz_deger(kampanya, "kampanya_bitis")

            tur = _duz_deger(kampanya, "kampanya_turu")
            kitle = _duz_deger(kampanya, "hedef_kitle")

            kayit = KampanyaKaydi(
                kampanya_id=kampanya.kampanya_id,
                banka_kodu=kampanya.banka_kodu,
                banka_adi=kampanya.banka_adi,
                kaynak_url=kampanya.kaynak_url,
                cekim_tarihi=kampanya.cekim_tarihi,
                kampanya_turu=getattr(tur, "value", tur),
                urun_turu=_duz_deger(kampanya, "urun_turu"),
                hedef_kitle=getattr(kitle, "value", kitle),
                ortalama_guven=kampanya.ortalama_guven(),
                doluluk_orani=kampanya.doluluk_orani(),
                tam_kayit=json.loads(kampanya.model_dump_json()),
                ham_metin=kampanya.ham_metin,
                **duz,  # type: ignore[arg-type]
            )
            oturum_.merge(kayit)
        oturum_.commit()
    return len(kampanyalar)


# ---------------------------------------------------------------------------
# Çıkarım koşusu — köken ve bayatlık
# ---------------------------------------------------------------------------


def kod_parmak_izi(kok: Path = KOK) -> str:
    """`CIKARIM_KAYNAKLARI` dosyalarının içerik özeti (kısa sha256).

    Aynı kod her makinede aynı izi verir: yollar göreli ve sıralıdır, mutlak
    yol ya da dosya tarihi karışmaz.
    """
    yollar: list[Path] = []
    for gosterge in CIKARIM_KAYNAKLARI:
        hedef = kok / gosterge
        if hedef.is_dir():
            yollar.extend(hedef.rglob("*.py"))
        elif hedef.is_file():
            yollar.append(hedef)

    ozet = hashlib.sha256()
    for yol in sorted(yollar):
        ozet.update(yol.relative_to(kok).as_posix().encode())
        ozet.update(yol.read_bytes())
    return ozet.hexdigest()[:16]


def cikarim_kosusu_yaz(
    yapilandirma: str, kayit_sayisi: int, url: str = VERITABANI_URL
) -> None:
    """Çıkarım bitiminde koşuyu kaydeder. `make eval` bayatlığı buradan anlar."""
    with oturum(url) as oturum_:
        oturum_.add(
            CikarimKosusu(
                zaman=datetime.now(),
                yapilandirma=yapilandirma,
                kayit_sayisi=kayit_sayisi,
                kod_parmak_izi=kod_parmak_izi(),
            )
        )
        oturum_.commit()


def son_cikarim_kosusu(url: str = VERITABANI_URL) -> dict[str, object] | None:
    """En son çıkarım koşusu; hiç kaydedilmemişse None."""
    sorgu = select(CikarimKosusu).order_by(CikarimKosusu.id.desc()).limit(1)
    with oturum(url) as oturum_:
        kayit = oturum_.scalars(sorgu).first()
        if kayit is None:
            return None
        return {
            "zaman": kayit.zaman,
            "yapilandirma": kayit.yapilandirma,
            "kayit_sayisi": kayit.kayit_sayisi,
            "kod_parmak_izi": kayit.kod_parmak_izi,
        }


def cikarim_durumu(url: str = VERITABANI_URL) -> dict[str, object]:
    """Veritabanındaki değerler GÜNCEL kodla mı üretildi?

    `bayat` True ise rapordaki sayılar eski koddan geliyordur ve sunuma
    kopyalanmamalıdır — `make extract` yeniden koşmalıdır.

    Koşu kaydı olmayan eski veritabanları `bayat=True` sayılır: bilmemek,
    güncel varsaymak için gerekçe değildir.
    """
    kosu = son_cikarim_kosusu(url)
    simdiki = kod_parmak_izi()
    if kosu is None:
        return {
            "kosu": None,
            "bayat": True,
            "sebep": "Çıkarım koşusu kaydı yok — veritabanı bu özellik eklenmeden önce üretilmiş.",
        }
    if kosu["kod_parmak_izi"] != simdiki:
        return {
            "kosu": kosu,
            "bayat": True,
            "sebep": (
                f"Çıkarım {kosu['zaman']:%d.%m.%Y %H:%M}'de koştu; çıkarım kodu "
                f"o tarihten sonra değişti ({kosu['kod_parmak_izi']} → {simdiki})."
            ),
        }
    return {"kosu": kosu, "bayat": False, "sebep": ""}


# ---------------------------------------------------------------------------
# Okuma
# ---------------------------------------------------------------------------


def tum_kayitlar(url: str = VERITABANI_URL) -> list[KampanyaKaydi]:
    with oturum(url) as oturum_:
        return list(oturum_.scalars(select(KampanyaKaydi)).all())


def kampanyalari_getir(
    *,
    banka_kodu: str | None = None,
    kampanya_turu: str | None = None,
    url: str = VERITABANI_URL,
) -> list[KampanyaKaydi]:
    """Yapısal sorgu — chatbot'un sayısal cevapları BURADAN gelir, RAG'dan değil."""
    sorgu = select(KampanyaKaydi)
    if banka_kodu:
        sorgu = sorgu.where(KampanyaKaydi.banka_kodu == banka_kodu)
    if kampanya_turu:
        sorgu = sorgu.where(KampanyaKaydi.kampanya_turu == kampanya_turu)
    with oturum(url) as oturum_:
        return list(oturum_.scalars(sorgu).all())


def kampanyalari_oku(url: str = VERITABANI_URL) -> Iterator[Kampanya]:
    """Tam kanıt zincirli Kampanya nesneleri."""
    for kayit in tum_kayitlar(url):
        yield kayit.kampanyaya_cevir()


def istatistikler(url: str = VERITABANI_URL) -> dict[str, object]:
    """Genel Bakış ekranının beslendiği özet."""
    kayitlar = tum_kayitlar(url)
    if not kayitlar:
        return {"kampanya_sayisi": 0, "banka_sayisi": 0, "son_guncelleme": None,
                "tur_dagilimi": {}, "ortalama_doluluk": 0.0}

    tur_dagilimi: dict[str, int] = {}
    for k in kayitlar:
        anahtar = k.kampanya_turu or "belirtilmemis"
        tur_dagilimi[anahtar] = tur_dagilimi.get(anahtar, 0) + 1

    return {
        "kampanya_sayisi": len(kayitlar),
        "banka_sayisi": len({k.banka_kodu for k in kayitlar}),
        "son_guncelleme": max(k.cekim_tarihi for k in kayitlar),
        "tur_dagilimi": dict(sorted(tur_dagilimi.items(), key=lambda x: -x[1])),
        "ortalama_doluluk": sum(k.doluluk_orani for k in kayitlar) / len(kayitlar),
        "ortalama_guven": sum(k.ortalama_guven for k in kayitlar) / len(kayitlar),
    }


__all__ = [
    "CIKARIM_KAYNAKLARI",
    "VERITABANI_URL",
    "CikarimKosusu",
    "KampanyaKaydi",
    "cikarim_durumu",
    "cikarim_kosusu_yaz",
    "istatistikler",
    "kampanyalari_getir",
    "kampanyalari_oku",
    "kaydet",
    "kod_parmak_izi",
    "oturum",
    "semayi_kur",
    "son_cikarim_kosusu",
    "tum_kayitlar",
]
