"""Gömme + kosinüs benzerliği ile RAG (S-09).

Serbest metin ("kampanya koşulları neler?") sorularının bağlamını getirir.
Sayısal cevaplar buradan GELMEZ — onlar yapısal veriden gelir. Bu ayrım
`src/rag/chatbot.py`'nin altın kuralıdır.

**Neden harici vektör veritabanı yok:** ADR 014. Kısası — `qdrant.ssyz.org.tr`
DNS'te çözülmüyor, öyle bir servisin bize tahsis edildiğine dair belge de yok.
Proje planı Qdrant altyapısını bütçe dışı ilan etmiş, S-09 zaten "kosinüs
benzerlik" istiyor. 15.151 paragraf × 1024 boyut; numpy ile tek nokta
çarpımı milisaniyeler sürer. Sunucu bu ölçekte hiçbir şey kazandırmıyor,
demoyu ağ bağlantısına bağımlı kılmak dışında.

Gömme modeli EVREN `bge-m3-embed` (= `BAAI/bge-m3`, MIT — ADR 013).
"""

from __future__ import annotations

import hashlib
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

# --- GÖMME SAĞLAYICISI (26 Ağu) --------------------------------------------
# `LLM_SAGLAYICI` çıkarım katmanı için ne yapıyorsa bu da gömme katmanı için
# aynısını yapar. Ayrı bir değişken, çünkü ikisi BAĞIMSIZ seçilebilmeli:
# çıkarımı EVREN'de koşup gömmeyi yerelde tutmak meşru bir yapılandırmadır.
#
# NEDEN EKLENDİ — ölçülmüş boşluk:
#     `indeks_kur` ADR 015 ile depoya alınınca «RAG artık çevrimdışı çalışır»
#     sanıldı. Ama indeksin HAZIR olması yetmiyor: `vektor_ara` her sorguda
#     SORGUYU gömmek zorunda ve o çağrı EVREN'e gidiyordu. Yani hava boşluğu
#     demosunda chatbot'un koşul sorusu yolu, indeks depoda dururken bile
#     çalışmıyordu. İndeksi taşımak gerekli ama YETERLİ değildi.
#
# Ollama'nın OpenAI uyumlu `/v1` ucu kullanılıyor: aynı istemci, aynı kod
# yolu, yalnız taban adres ve model adı değişiyor. Ayrı bir istemci sınıfı
# yazmak iki ayrı hata yüzeyi açardı.
GOMME_SAGLAYICI = os.getenv("GOMME_SAGLAYICI", "evren").strip().lower()

OLLAMA_GOMME_MODELI = os.getenv("OLLAMA_GOMME_MODELI", "bge-m3")
"""Yerel gömme modeli. `bge-m3` — EVREN'deki `bge-m3-embed` ile AYNI model.

İkisi de `BAAI/bge-m3` (MIT, ADR 013) ve ikisi de 1024 boyut veriyor, yani
`BOYUT` sabiti ve depodaki indeks ikisiyle de uyumlu. Adların farklı olması
servislerin adlandırma tercihidir, farklı model değildir —
`_model_ailesi()` bu ayrımı yönetir."""

BOYUT = 1024  # bge-m3-embed'in ölçülen boyutu — model değişirse burası da değişir
YIGIN = 64  # tek istekte gömülecek paragraf sayısı (ölçüldü: 64 metin ≈ 0,46 sn)
ASGARI_PARAGRAF = 40  # bundan kısa satırlar bağlam taşımıyor
INDEKS_DOSYASI = Path(os.getenv("VEKTOR_INDEKSI", KOK / "data" / "vektor_indeksi.npz"))

_istemci: OpenAI | None = None
_indeks: dict[str, np.ndarray] | None = None


class IndeksYok(RuntimeError):
    """Vektör indeksi kurulmamış. `make vektor` ile kurulur."""


def gomme_ucu() -> tuple[str, str, str]:
    """Seçili gömme sağlayıcısının (temel_url, anahtar, model) üçlüsü.

    Bilinmeyen sağlayıcı SESSİZCE EVREN'e düşmez: yapılandırma hatasını
    fark edilmeyen bir dış çağrıya çevirmek, bu dosyanın `gom_toplu`
    docstring'inde anlatılan sıfır-vektörü hatasının aynısı olurdu.
    """
    if GOMME_SAGLAYICI == "ollama":
        from src.extraction.saglayici import OLLAMA_SUNUCU

        # Ollama anahtar istemez ama OpenAI istemcisi boş dize kabul etmez.
        return f"{OLLAMA_SUNUCU.rstrip('/')}/v1", "ollama-yerel", OLLAMA_GOMME_MODELI
    if GOMME_SAGLAYICI == "evren":
        return EVREN_API_URL, EVREN_API_KEY or "anahtar-yok", GOMME_MODELI
    raise ValueError(
        f"Bilinmeyen gömme sağlayıcı: {GOMME_SAGLAYICI!r}. Beklenen: 'evren' veya 'ollama'."
    )


def aktif_gomme_modeli() -> str:
    """Şu anda kullanılan gömme modelinin adı — indekse bu ad yazılır."""
    return gomme_ucu()[2]


def _model_ailesi(ad: str) -> str:
    """Model adını AİLESİNE indirger: `bge-m3-embed` ve `bge-m3` aynı ailedir.

    İndeks kendi model adını taşıyor. Aile karşılaştırması olmadan, EVREN'de
    kurulmuş bir indeksi Ollama ile sorgulamak sahte bir uyumsuzluk uyarısı
    üretirdi; tersine, ham ad karşılaştırması yapmamak gerçekten farklı bir
    modele geçildiğinde sessiz kalırdı. İkisinin arasındaki tek dürüst yol
    adı normalleştirmek.
    """
    return ad.strip().lower().removesuffix("-embed").removesuffix(":latest")


def istemci_al() -> OpenAI:
    global _istemci
    if _istemci is None:
        temel_url, anahtar, _ = gomme_ucu()
        _istemci = OpenAI(base_url=temel_url, api_key=anahtar)
    return _istemci


# ---------------------------------------------------------------------------
# Gömme
# ---------------------------------------------------------------------------


def _boyut_denetle(vektorler: list[list[float]], model: str | None = None) -> None:
    """Model sessizce değişirse indeks bozulur; erken ve yüksek sesle patlat.

    `model` verilmezse AKTİF modele düşer — varsayılan uydurma bir ad değil,
    çağrının gerçekten kullanacağı addır, dolayısıyla hata metni yanıltmaz.
    """
    model = model or aktif_gomme_modeli()
    for v in vektorler:
        if len(v) != BOYUT:
            raise ValueError(
                f"Gömme boyutu beklenenden farklı: {model} {len(v)} boyut "
                f"verdi, BOYUT {BOYUT}. Model değiştiyse BOYUT da güncellenmeli."
            )


def gom_toplu(metinler: list[str]) -> list[list[float]]:
    """Metinleri yığın hâlinde vektöre çevirir.

    Hata YUTULMAZ. Eskiden burada sıfır vektörü dönülüyordu; yanlış model
    adının 404'ü o yüzden görülmedi. Sıfır vektörü de uydurma bir değerdir —
    bu depoda kanıtsız değer üretilmez.

    Hangi uca gittiği `GOMME_SAGLAYICI`'ya bağlı (EVREN ya da yerel Ollama);
    boyut denetimi ikisinde de aynı, çünkü denetlenen şey servis değil MODEL.
    """
    if not metinler:
        return []
    model = aktif_gomme_modeli()
    yanit = istemci_al().embeddings.create(input=metinler, model=model)
    vektorler = [d.embedding for d in yanit.data]
    _boyut_denetle(vektorler, model)
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


def korpus_izi(kayitlar: list[KampanyaKaydi]) -> str:
    """İndeksin ÜRETİLDİĞİ korpusun içerik özeti (kısa sha256).

    NEDEN VAR — 26 Ağustos'ta ölçülen boşluk:
        `src/depolama.kod_parmak_izi` çıkarım kodunun bayatlığını yakalıyor,
        ama RAG indeksinin bayatlığını hiçbir şey yakalamıyordu. `make durum`
        yalnız «kurulu mu» diyordu, «güncel mi» demiyordu.

        Somut zarar: 93 süresi geçmiş kampanya silindikten sonra indeks
        yeniden kurulmazsa chatbot SİLİNMİŞ kampanyaları kaynak gösterir —
        üstelik kaynak alıntısıyla, yani güvenilir görünerek. Aynı şey
        `make extract` sonrası da olur: metin değişir, indeks eski metni
        aramaya devam eder.

    NE KAPSAR:
        İndekse fiilen giren şey: kampanya kimliği + o kaydın paragrafları.
        `paragraflara_ayir` neyi üretiyorsa iz onu özetler — böylece
        indekslenmeyen bir alanın değişmesi boşuna «bayat» demez.

    Kayıtlar kimliğe göre SIRALANIR: veritabanı sırası değişse de iz değişmez.
    """
    ozet = hashlib.sha256()
    for kayit in sorted(kayitlar, key=lambda k: k.kampanya_id):
        ozet.update(kayit.kampanya_id.encode("utf-8"))
        for paragraf in paragraflara_ayir(kayit):
            ozet.update(b"\x00")  # sınır: bitişik paragraflar karışmasın
            ozet.update(paragraf.encode("utf-8"))
    return ozet.hexdigest()[:16]


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
        model=np.asarray([aktif_gomme_modeli()], dtype=object),
        korpus_izi=np.asarray([korpus_izi(kayitlar)], dtype=object),
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


def indeks_durumu(kayitlar: list[KampanyaKaydi] | None = None) -> dict[str, object]:
    """İndeksin varlığını, boyutunu ve BAYATLIĞINI bildirir (`make durum` için).

    `kayitlar` verilirse indeksin üretildiği korpus izi bugünküyle
    karşılaştırılır. Verilmezse bayatlık DENETLENMEZ ve bu açıkça bildirilir —
    «denetlemedik» ile «temiz» aynı şey değildir.
    """
    if not INDEKS_DOSYASI.exists():
        return {"var": False, "yol": str(INDEKS_DOSYASI)}
    veri = indeks_yukle()
    durum: dict[str, object] = {
        "var": True,
        "yol": str(INDEKS_DOSYASI),
        "paragraf": int(veri["vektorler"].shape[0]),
        "boyut": int(veri["vektorler"].shape[1]),
        "kampanya": len(set(veri["kampanya_id"].tolist())),
        "model": str(veri["model"][0]),
    }

    kayitli = str(veri["korpus_izi"][0]) if "korpus_izi" in veri else None
    durum["korpus_izi"] = kayitli

    if kayitlar is None:
        durum["bayat"] = None
        durum["sebep"] = "korpus verilmedi — bayatlık denetlenmedi"
        return durum

    if kayitli is None:
        # `depolama.cikarim_durumu` ile aynı duruş: bilmemek, güncel varsaymak
        # için gerekçe değildir.
        durum["bayat"] = True
        durum["sebep"] = (
            "İndekste korpus izi yok — bu denetim eklenmeden önce kurulmuş. "
            "`make vektor` ile yeniden kurun."
        )
        return durum

    simdiki = korpus_izi(kayitlar)
    if simdiki != kayitli:
        durum["bayat"] = True
        durum["sebep"] = (
            f"İndeks {durum['kampanya']} kampanyadan kuruldu; veritabanındaki "
            f"korpus o tarihten sonra değişti ({kayitli} → {simdiki}). "
            "Chatbot silinmiş ya da eski metni kaynak gösterebilir — "
            "`make vektor` ile yeniden kurun."
        )
        return durum

    durum["bayat"] = False
    durum["sebep"] = ""
    return durum


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

    # MODEL AİLESİ KAPISI — indeks bir modelle kurulup başka bir modelle
    # sorgulanırsa skorlar anlamsızlaşır ama HATA VERMEZ: kosinüs yine bir
    # sayı döndürür, yalnız ilgisiz paragrafları getirir. Sessiz bozulmanın
    # en sinsi biçimi bu, o yüzden burada yüksek sesle söyleniyor.
    # `bge-m3-embed` (EVREN) ile `bge-m3` (Ollama) AYNI ailedir, uyarı çıkmaz.
    indeks_modeli = str(veri["model"][0]) if "model" in veri else ""
    if indeks_modeli and _model_ailesi(indeks_modeli) != _model_ailesi(aktif_gomme_modeli()):
        log.warning(
            "Gömme modeli uyuşmuyor: indeks %r ile kuruldu, sorgu %r ile "
            "gömülüyor. Sonuçlar güvenilmezdir — `make vektor` ile indeksi "
            "yeniden kurun.",
            indeks_modeli, aktif_gomme_modeli(),
        )

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
    "GOMME_SAGLAYICI",
    "OLLAMA_GOMME_MODELI",
    "INDEKS_DOSYASI",
    "IndeksYok",
    "aktif_gomme_modeli",
    "gom",
    "gom_toplu",
    "gomme_ucu",
    "indeks_durumu",
    "korpus_izi",
    "indeks_kur",
    "vektor_ara",
]
