"""Gömme + kosinüs benzerliği ile RAG (S-09).

Serbest metin ("kampanya koşulları neler?") sorularının bağlamını getirir.
Sayısal cevaplar buradan GELMEZ — onlar yapısal veriden gelir. Bu ayrım
`src/rag/chatbot.py`'nin altın kuralıdır.

**Neden harici vektör veritabanı yok:** ADR 014. Kısası — `qdrant.ssyz.org.tr`
DNS'te çözülmüyor, öyle bir servisin bize tahsis edildiğine dair belge de yok.
Proje planı Qdrant altyapısını bütçe dışı ilan etmiş, S-09 zaten "kosinüs
benzerlik" istiyor. 15.519 paragraf × 1024 boyut = 61 MB; numpy ile tek nokta
çarpımı milisaniyeler sürer. Sunucu bu ölçekte hiçbir şey kazandırmıyor,
demoyu ağ bağlantısına bağımlı kılmak dışında.

Gömme modeli EVREN `bge-m3-embed` (= `BAAI/bge-m3`, MIT — ADR 013).
"""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path

import numpy as np
from openai import OpenAI

from src.depolama import KampanyaKaydi

log = logging.getLogger(__name__)

KOK = Path(__file__).resolve().parent.parent

# EVREN API Yapılandırması (gömme için)
EVREN_API_URL = os.getenv("EVREN_TEMEL_URL", "https://evren-llmapi.ssyz.org.tr/v1")
EVREN_API_KEY = os.getenv("EVREN_API_ANAHTARI", "")

# Gömme modeli — `bge-m3-embed`. Üç sebeple bu seçildi (25 Ağu, ölçüldü):
#   1. `embedding` diye bir uç EVREN'de YOK. Kodun eski varsayılanı buydu ve
#      her çağrıda 404 dönüyordu; hata yutulduğu için dört gün görülmedi.
#   2. Jenerik `embed` ucu çalışıyor ama 2560 boyut veriyor — BOYUT ile tutmaz.
#   3. `bge-m3-embed` 1024 boyut veriyor; BGE-M3'ün bilinen boyutu bu, yani
#      ada ek olarak kimlik teyidi sayılır. Lisans: MIT (ADR 013).
GOMME_MODELI = os.getenv("EVREN_EMBEDDING_MODEL", "bge-m3-embed")

BOYUT = 1024  # bge-m3-embed'in ölçülen boyutu — model değişirse burası da değişir
YIGIN = 64  # tek istekte gömülecek paragraf sayısı (ölçüldü: 64 metin ≈ 0,46 sn)
ASGARI_PARAGRAF = 40  # bundan kısa satırlar bağlam taşımıyor
INDEKS_DOSYASI = Path(os.getenv("VEKTOR_INDEKSI", KOK / "data" / "vektor_indeksi.npz"))

_istemci: OpenAI | None = None
_indeks: dict[str, np.ndarray] | None = None


class IndeksYok(RuntimeError):
    """Vektör indeksi kurulmamış. `make vektor` ile kurulur."""


def istemci_al() -> OpenAI:
    global _istemci
    if _istemci is None:
        _istemci = OpenAI(base_url=EVREN_API_URL, api_key=EVREN_API_KEY or "anahtar-yok")
    return _istemci


# ---------------------------------------------------------------------------
# Gömme
# ---------------------------------------------------------------------------


def _boyut_denetle(vektorler: list[list[float]]) -> None:
    """Model sessizce değişirse indeks bozulur; erken ve yüksek sesle patlat."""
    for v in vektorler:
        if len(v) != BOYUT:
            raise ValueError(
                f"Gömme boyutu beklenenden farklı: {GOMME_MODELI} {len(v)} boyut "
                f"verdi, BOYUT {BOYUT}. Model değiştiyse BOYUT da güncellenmeli."
            )


def gom_toplu(metinler: list[str]) -> list[list[float]]:
    """Metinleri yığın hâlinde vektöre çevirir.

    Hata YUTULMAZ. Eskiden burada sıfır vektörü dönülüyordu; yanlış model
    adının 404'ü o yüzden görülmedi. Sıfır vektörü de uydurma bir değerdir —
    bu depoda kanıtsız değer üretilmez.
    """
    if not metinler:
        return []
    yanit = istemci_al().embeddings.create(input=metinler, model=GOMME_MODELI)
    vektorler = [d.embedding for d in yanit.data]
    _boyut_denetle(vektorler)
    return vektorler


def gom(metin: str) -> list[float]:
    """Tek metni vektöre çevirir."""
    return gom_toplu([metin])[0]


_MADDE_ISARETI = re.compile(r"^[\s\-–—•*·.\d)]+")


def _tekrar_imzasi(metin: str) -> str:
    """Aynı metnin farklı biçimlenmiş hâllerini eşitleyen imza.

    Korpusta aynı sözleşme cümlesi kimi sayfada madde işaretli, kimisinde
    düz geçiyor: «- Kampanya diğer kampanyalarla birleştirilemez.» ile
    «Kampanya diğer kampanyalarla birleştirilemez.» iki ayrı sonuç olarak
    dönüyor ve üç sonuçluk yerin ikisini harcıyordu.
    """
    return " ".join(_MADDE_ISARETI.sub("", metin).lower().split())


def _birimlestir(m: np.ndarray) -> np.ndarray:
    """L2 normalizasyonu — böylece kosinüs benzerliği düz nokta çarpımı olur."""
    norm = np.linalg.norm(m, axis=1, keepdims=True)
    norm[norm == 0] = 1.0  # sıfır vektörü indekse girmemeli, yine de bölme koruması
    return (m / norm).astype(np.float32)


# ---------------------------------------------------------------------------
# İndeks kurma
# ---------------------------------------------------------------------------


def paragraflara_ayir(kayit: KampanyaKaydi) -> list[str]:
    ham = kayit.ham_metin or ""
    return [p.strip() for p in re.split(r"\n+", ham) if len(p.strip()) >= ASGARI_PARAGRAF]


def indeks_kur(kayitlar: list[KampanyaKaydi], ilerleme: bool | None = None) -> int:
    """Kayıtları paragraflara ayırıp gömer ve indeksi diske yazar.

    Döndürdüğü sayı indekslenen paragraf adedidir.
    """
    paragraflar: list[str] = []
    kampanya_idleri: list[str] = []
    banka_adlari: list[str] = []

    for kayit in kayitlar:
        for paragraf in paragraflara_ayir(kayit):
            paragraflar.append(paragraf)
            kampanya_idleri.append(kayit.kampanya_id)
            banka_adlari.append(kayit.banka_adi)

    if not paragraflar:
        raise ValueError("İndekslenecek paragraf yok — önce `make extract` koşun.")

    # İlerleme yalnız gerçek terminalde basılır; boruya yazınca `\r` işe
    # yaramıyor ve günlükleri çöpe çeviriyor.
    if ilerleme is None:
        ilerleme = sys.stdout.isatty()

    vektorler: list[list[float]] = []
    for bas in range(0, len(paragraflar), YIGIN):
        vektorler.extend(gom_toplu(paragraflar[bas : bas + YIGIN]))
        if ilerleme:
            print(
                f"\r  gömülen paragraf: {len(vektorler)}/{len(paragraflar)}",
                end="",
                flush=True,
            )
    if ilerleme:
        print()

    dizey = _birimlestir(np.asarray(vektorler, dtype=np.float32))
    INDEKS_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        INDEKS_DOSYASI,
        vektorler=dizey,
        kampanya_id=np.asarray(kampanya_idleri, dtype=object),
        banka_adi=np.asarray(banka_adlari, dtype=object),
        metin=np.asarray(paragraflar, dtype=object),
        model=np.asarray([GOMME_MODELI], dtype=object),
    )
    global _indeks
    _indeks = None  # bellekteki eski indeksi düşür
    log.info("%d paragraf indekslendi → %s", len(paragraflar), INDEKS_DOSYASI)
    return len(paragraflar)


def indeks_yukle() -> dict[str, np.ndarray]:
    """İndeksi diskten okur ve bellekte tutar."""
    global _indeks
    if _indeks is None:
        if not INDEKS_DOSYASI.exists():
            raise IndeksYok(
                f"Vektör indeksi bulunamadı ({INDEKS_DOSYASI}). "
                f"`make vektor` ile kurulur."
            )
        with np.load(INDEKS_DOSYASI, allow_pickle=True) as veri:
            _indeks = {ad: veri[ad] for ad in veri.files}
    return _indeks


def indeks_durumu() -> dict[str, object]:
    """İndeksin var olup olmadığını ve boyutunu bildirir (`make durum` için)."""
    if not INDEKS_DOSYASI.exists():
        return {"var": False, "yol": str(INDEKS_DOSYASI)}
    veri = indeks_yukle()
    return {
        "var": True,
        "yol": str(INDEKS_DOSYASI),
        "paragraf": int(veri["vektorler"].shape[0]),
        "boyut": int(veri["vektorler"].shape[1]),
        "kampanya": len(set(veri["kampanya_id"].tolist())),
        "model": str(veri["model"][0]),
    }


# ---------------------------------------------------------------------------
# Arama
# ---------------------------------------------------------------------------


def vektor_ara(
    sorgu: str, limit: int = 3, kampanya_idleri: list[str] | None = None
) -> list[dict]:
    """Sorguya en benzer paragrafları kosinüs benzerliğiyle getirir.

    `kampanya_idleri` verilirse yalnız o kampanyaların paragraflarında arar.
    Hata yutulmaz: arama başarısızlığını boş listeye çevirmek "veri setinde
    yok" demektir, kullanıcı da yanlış cevabı doğru sanır.
    """
    veri = indeks_yukle()
    dizey: np.ndarray = veri["vektorler"]

    maske = None
    if kampanya_idleri is not None:
        istenen = set(kampanya_idleri)
        maske = np.fromiter(
            (kid in istenen for kid in veri["kampanya_id"].tolist()),
            dtype=bool,
            count=dizey.shape[0],
        )
        if not maske.any():
            return []

    sorgu_vektoru = np.asarray(gom(sorgu), dtype=np.float32)
    sorgu_vektoru /= np.linalg.norm(sorgu_vektoru) or 1.0

    skorlar = dizey @ sorgu_vektoru
    if maske is not None:
        skorlar = np.where(maske, skorlar, -np.inf)

    mevcut = int(maske.sum()) if maske is not None else dizey.shape[0]
    if mevcut <= 0:
        return []

    # Yinelenen paragraf için fazladan aday çekiliyor: korpusta aynı sözleşme
    # metni birden çok kampanyada geçiyor ve tekrar, üç sonuçluk yerin ikisini
    # boşa harcıyordu (ölçüldü — "konut finansmanı gerekli belgeler").
    aday = min(mevcut, max(limit * 5, limit))
    en_iyiler = np.argpartition(-skorlar, aday - 1)[:aday]
    en_iyiler = en_iyiler[np.argsort(-skorlar[en_iyiler])]

    sonuclar: list[dict] = []
    gorulen: set[str] = set()
    for i in en_iyiler:
        metin = str(veri["metin"][i])
        imza = _tekrar_imzasi(metin)
        if imza in gorulen:
            continue
        gorulen.add(imza)
        sonuclar.append(
            {
                "kampanya_id": str(veri["kampanya_id"][i]),
                "banka_adi": str(veri["banka_adi"][i]),
                "metin": metin,
                "benzerlik": float(skorlar[i]),
            }
        )
        if len(sonuclar) == limit:
            break
    return sonuclar


__all__ = [
    "BOYUT",
    "GOMME_MODELI",
    "INDEKS_DOSYASI",
    "IndeksYok",
    "gom",
    "gom_toplu",
    "indeks_durumu",
    "indeks_kur",
    "vektor_ara",
]
