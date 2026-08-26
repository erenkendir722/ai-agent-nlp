"""«Canlı Boru Hattı» sayfasının biriken durumu ve olay işleyicileri.

NEDEN AYRI MODÜL — Streamlit sayfa betiğini HER yeniden çizimde baştan
çalıştırır, yani sayfa dosyasında tanımlı bir `@dataclass` her koşuda YENİ bir
sınıf nesnesi olur. `st.session_state`'te duran örnek bir önceki koşunun
sınıfından geldiği için `isinstance(ornek, YeniSinif)` **False** döner ve
biriken durum sessizce sıfırlanır. Ölçüldü: `AppTest` ile sürülen çıkarımda
sayaç «1 / ?» kaldı, oysa iki kayıt işlenmişti.

Modül `sys.modules`'ta bir kez durduğu için buradaki sınıflar koşular arasında
AYNI nesnedir. Yan fayda: işleyiciler saf işlev olduğundan tarayıcısız
sınanabiliyorlar (`tests/test_boru_durumu.py`).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from app.akis import BankaDurumu, GunlukSatiri, KayitOzeti
from app.ui_utils import format_bank_name

AZAMI_GUNLUK_GECMISI = 120
"""Bellekte tutulan olay satırı. Günlük yalnız son ~12'sini çizer."""

AZAMI_KAYIT_GECMISI = 40
"""Bellekte tutulan kayıt özeti. Şerit yalnız son birkaçını çizer."""


@dataclass
class ToplamaDurumu:
  """Toplama koşusunun canlı biriktirdiği durum — hepsi olaylardan türer."""

  bankalar: dict[str, BankaDurumu] = field(default_factory=dict)
  olaylar: list[GunlukSatiri] = field(default_factory=list)
  sayfa: int = 0
  kesfedilen: int = 0
  atlanan: int = 0
  hata: int = 0
  robots_reddi: int = 0
  atlama_sebepleri: dict[str, int] = field(default_factory=dict)
  aktif_url: str = ""
  aktif_banka: str = ""
  """Üzerinde İŞLEM YAPILAN bankanın kodu — nabzı yalnız o kart atar.

  `topla` bankaları sırayla geziyor, yani aynı anda tek banka aktiftir.
  Aşamaya bakmak yetmiyordu: demo tavanıyla kesilen banka «bitti» olayı
  üretmediği için kartı `taraniyor`da kalıyor ve sonraki bankaya
  geçildiğinde iki kart birden yanıp sönüyordu.
  """

  urller: list[str] = field(default_factory=list)
  hedef: str = ""


@dataclass
class CikarimDurumu:
  """Çıkarım koşusunun canlı biriktirdiği durum."""

  olaylar: list[GunlukSatiri] = field(default_factory=list)
  kayitlar: list[KayitOzeti] = field(default_factory=list)
  islenen: int = 0
  toplam: int = 0
  hatali: int = 0
  yazilan: int = 0
  sure_toplami: float = 0.0
  hedef: str = ""

  kural: int = 0
  llm: int = 0
  hibrit: int = 0
  """Katman hattının canlı sayaçları — koşu SÜRERKEN de dolar.

  Değerler olaydan olduğu gibi ALINIR, toplanmaz: `cikarim_kos` bunları
  zaten koşan toplam olarak gönderiyor. Burada ikinci kez toplamak sayıyı
  ikiye katlardı.
  """


def toplama_olaylarini_isle(durum: ToplamaDurumu, olaylar: list) -> None:
  """`src.collector.temel_kaziyici.Ilerleme` olaylarını duruma işler.

  Olay nesneleri `getattr` ile okunuyor: kazıyıcı katmanına yeni bir aşama
  eklendiğinde arayüz KIRILMAZ, o aşamayı yok sayar.
  """
  for olay in olaylar:
    kod = getattr(olay, "banka_kodu", "")
    ad = getattr(olay, "banka_adi", "") or kod
    asama = getattr(olay, "asama", "")
    url = getattr(olay, "url", "") or ""
    mesaj = getattr(olay, "mesaj", "") or ""
    kart = durum.bankalar.get(kod, BankaDurumu(ad=ad))

    # BAYRAK DEVRİ — yeni bir bankadan olay geldiyse önceki banka bitmiştir.
    # Toplama sırayla ilerlediği için bu çıkarım güvenli; kartın sayfa
    # sayısına dokunulmaz, yalnız aşama kapatılıp nabız durdurulur.
    if kod and kod != durum.aktif_banka:
      onceki = durum.bankalar.get(durum.aktif_banka)
      if onceki is not None:
        durum.bankalar[durum.aktif_banka] = replace(
          onceki,
          aktif=False,
          asama="bitti" if onceki.asama == "taraniyor" else onceki.asama,
        )
      durum.aktif_banka = kod

    if asama == "url_kesfi":
      toplam = getattr(olay, "toplam", 0)
      if toplam:
        durum.kesfedilen += toplam
      kart = BankaDurumu(
        ad=ad, asama="taraniyor", sayfa=kart.sayfa,
        toplam=toplam or kart.toplam, mesaj=mesaj,
      )
      durum.olaylar.append(GunlukSatiri(tur="bilgi", metin=mesaj or ad, etiket=ad))
    elif asama == "sayfa":
      durum.sayfa += 1
      durum.aktif_url = url
      durum.urller.append(url)
      kart = BankaDurumu(
        ad=ad, asama="taraniyor", sayfa=kart.sayfa + 1,
        toplam=getattr(olay, "toplam", kart.toplam), mesaj=mesaj,
      )
      durum.olaylar.append(GunlukSatiri(tur="sayfa", metin=url, etiket=ad))
    elif asama == "atlandi":
      durum.atlanan += 1
      sebep = mesaj or "belirtilmedi"
      durum.atlama_sebepleri[sebep] = durum.atlama_sebepleri.get(sebep, 0) + 1
      # robots reddi AYRI sayılır: kusur değil, jüriye gösterilecek etik kanıtı.
      if "robots" in sebep.lower():
        durum.robots_reddi += 1
      kart = BankaDurumu(
        ad=ad, asama="taraniyor", sayfa=kart.sayfa,
        toplam=getattr(olay, "toplam", kart.toplam), mesaj=sebep,
      )
      durum.olaylar.append(
        GunlukSatiri(tur="atlandi", metin=f"atlandı ({sebep})", etiket=ad)
      )
    elif asama == "hata":
      durum.hata += 1
      kart = BankaDurumu(
        ad=ad, asama="hata", sayfa=kart.sayfa, toplam=kart.toplam, mesaj=mesaj,
      )
      durum.olaylar.append(GunlukSatiri(tur="hata", metin=mesaj or url, etiket=ad))
    elif asama == "bitti":
      kart = BankaDurumu(
        ad=ad, asama="bitti", sayfa=getattr(olay, "sira", kart.sayfa),
        toplam=getattr(olay, "toplam", kart.toplam), mesaj=mesaj,
      )
      durum.olaylar.append(GunlukSatiri(tur="bilgi", metin=mesaj, etiket=ad))
    else:
      continue

    durum.bankalar[kod] = replace(kart, aktif=kod == durum.aktif_banka)
    del durum.olaylar[:-AZAMI_GUNLUK_GECMISI]


def acik_kartlari_kapat(durum: ToplamaDurumu, *, iptal: bool) -> None:
  """Koşu bittiğinde hâlâ «taranıyor» görünen kartları kapatır.

  DEMO TAVANI «bitti» OLAYI ÜRETMEZ — ölçüldü (Türkiye Finans, 3 sayfa
  tavanı): `topla` üreteci tavana varınca kapatıyor, `tara()` bu yüzden
  kapanış bildirimine hiç ulaşmıyor. Bu kapatma olmadan kart, koşu bitmiş
  olmasına rağmen sonsuza dek yeşil nabız atardı — sayfanın tek yasağı olan
  «gerçeği yanlış gösteren piksel» tam olarak budur.

  Kartın SAYFA SAYISI değiştirilmez: gösterilen sayı toplanan gerçek sayfa
  adedidir; kapatılan yalnız aşamadır.
  """
  for kod, kart in list(durum.bankalar.items()):
    if kart.asama != "taraniyor":
      if kart.aktif:
        durum.bankalar[kod] = replace(kart, aktif=False)
      continue
    durum.bankalar[kod] = replace(
      kart,
      asama="bitti",
      aktif=False,
      mesaj="iptal edildi" if iptal else (kart.mesaj or "tamamlandı"),
    )
  durum.aktif_banka = ""


def cikarim_olaylarini_isle(durum: CikarimDurumu, olaylar: list) -> None:
  """`src.boru_hatti.CikarimIlerlemesi` olaylarını duruma işler."""
  for olay in olaylar:
    asama = getattr(olay, "asama", "")
    ad = getattr(olay, "banka_adi", "") or ""
    if asama == "basladi":
      durum.toplam = getattr(olay, "toplam", 0)
      durum.olaylar.append(GunlukSatiri(tur="bilgi", metin=getattr(olay, "mesaj", "")))
    elif asama == "kayit":
      durum.islenen += 1
      sure = float(getattr(olay, "sure", 0.0))
      durum.sure_toplami += sure
      durum.kural = int(getattr(olay, "kural", durum.kural))
      durum.llm = int(getattr(olay, "llm", durum.llm))
      durum.hibrit = int(getattr(olay, "hibrit", durum.hibrit))
      durum.kayitlar.append(
        KayitOzeti(
          banka=format_bank_name(ad),
          doluluk=float(getattr(olay, "doluluk", 0.0)),
          guven=float(getattr(olay, "guven", 0.0)),
          sure=sure,
          url=getattr(olay, "url", ""),
        )
      )
      durum.olaylar.append(
        GunlukSatiri(
          tur="kayit",
          metin=(
            f"doluluk %{float(getattr(olay, 'doluluk', 0.0)) * 100:.0f} · "
            f"güven {float(getattr(olay, 'guven', 0.0)):.2f} · {sure:.2f} sn"
          ),
          etiket=format_bank_name(ad),
        )
      )
    elif asama == "hata":
      durum.hatali += 1
      durum.olaylar.append(
        GunlukSatiri(
          tur="hata", metin=getattr(olay, "mesaj", ""), etiket=format_bank_name(ad)
        )
      )
    elif asama == "ara_kayit":
      durum.yazilan = getattr(olay, "sira", durum.yazilan)
      durum.olaylar.append(GunlukSatiri(tur="bilgi", metin=getattr(olay, "mesaj", "")))
    elif asama == "bitti":
      durum.olaylar.append(
        GunlukSatiri(tur="bilgi", metin=f"koşu {getattr(olay, 'mesaj', '')}")
      )
    else:
      continue
    del durum.kayitlar[:-AZAMI_KAYIT_GECMISI]
    del durum.olaylar[:-AZAMI_GUNLUK_GECMISI]


__all__ = [
  "AZAMI_GUNLUK_GECMISI",
  "AZAMI_KAYIT_GECMISI",
  "CikarimDurumu",
  "ToplamaDurumu",
  "acik_kartlari_kapat",
  "cikarim_olaylarini_isle",
  "toplama_olaylarini_isle",
]
