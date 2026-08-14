"""Ajan protokolü ve iz kaydı — ajan mimarisinin ortak sözleşmesi.

Yarışmanın adı "Yapay Zekâ Dil AJANLARI Yarışması." Jüri ajan mimarisi
görmeyi bekliyor; ama *iddia etmek* ile *göstermek* farklı şeyler.

BU MODÜLÜN ASIL İŞİ — `AjanIzi`:
    Her ajan, ne yaptığını ve NEDEN yaptığını bir ize yazar. Arayüzdeki
    "Ajan izleri" paneli bu izleri gösterir. Jüri ajan mimarisinin varlığını
    bizim sözümüze değil, ekrandaki koşum kaydına bakarak görür.

    `llm_kullanildi` alanı özellikle önemli: sistemin en kırılgan iddiası
    *"aritmetiği ajana yaptırmıyoruz, deterministik kodla yapıyoruz"*.
    Bu alan o iddiayı ekranda ispatlar — karşılaştırma motorunun ve
    eleştirmenin izinde `llm_kullanildi=False` yazar.

NEDEN AĞIR BİR ÇATI (LangChain vb.) KULLANMIYORUZ:
    Ajanlarımızın ihtiyacı olan şey bir çağrı grafiği değil, bir sözleşme.
    Yönlendirme kararları zaten deterministik; dış çatı, şartname 5.9'un
    "dış servise bağımlı olmama" ve 5.10'un lisans kısıtları karşısında
    doğrulanması gereken yeni bir bağımlılık yığını getirirdi. Protokol
    30 satır, çatının denetimi günler.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class AjanIzi(BaseModel):
    """Tek bir ajan koşusunun görülebilir kaydı."""

    ajan_adi: str
    girdi_ozeti: str = ""
    cikti_ozeti: str = ""
    llm_kullanildi: bool = False
    sure_ms: int = 0
    karar_gerekcesi: str = ""
    """İnsan-okur tek cümle: "3 kampanya elendi: min_tutar > 800.000".

    Boş bırakılmamalı. Gerekçesini tek cümlede anlatamayan bir ajanın var olma
    sebebi de yoktur (bkz. Plan_Guncellemeleri_v3.md, "ajan tuzağı")."""

    def satir(self) -> str:
        """Günlük ve panel için tek satırlık gösterim."""
        motor = "LLM" if self.llm_kullanildi else "kod"
        return f"[{self.ajan_adi} · {motor} · {self.sure_ms} ms] {self.karar_gerekcesi}"


class IzDefteri(BaseModel):
    """Bir isteğin tüm ajan izleri, çalışma sırasıyla."""

    izler: list[AjanIzi] = Field(default_factory=list)

    def ekle(self, iz: AjanIzi) -> None:
        self.izler.append(iz)

    def toplam_sure_ms(self) -> int:
        return sum(iz.sure_ms for iz in self.izler)

    def llm_cagrisi_sayisi(self) -> int:
        return sum(1 for iz in self.izler if iz.llm_kullanildi)

    def ozet(self) -> str:
        """"4 ajan · 2 LLM çağrısı · 1.240 ms" — panel başlığı."""
        return (
            f"{len(self.izler)} ajan · {self.llm_cagrisi_sayisi()} LLM çağrısı · "
            f"{self.toplam_sure_ms()} ms"
        )


@contextmanager
def iz_tut(
    ajan_adi: str, *, llm: bool = False, girdi: str = ""
) -> Iterator[AjanIzi]:
    """Bir ajan koşusunu ölçer ve izini kurar.

    Kullanım:

        with iz_tut("muhakeme", girdi=profil.ozet()) as iz:
            sonuc = ...
            iz.cikti_ozeti = f"{len(sonuc)} uygun kampanya"
            iz.karar_gerekcesi = "3 kampanya min_tutar kısıtından elendi"

    Süre `finally` içinde yazılır: ajan hata fırlatsa bile iz eksik kalmaz —
    "hangi ajan patladı" sorusu tam da hata anında sorulur.
    """
    iz = AjanIzi(ajan_adi=ajan_adi, llm_kullanildi=llm, girdi_ozeti=girdi)
    baslangic = time.monotonic()
    try:
        yield iz
    finally:
        iz.sure_ms = int((time.monotonic() - baslangic) * 1000)


@runtime_checkable
class Ajan(Protocol):
    """Bir ajanın taşıması gereken en az sözleşme.

    `calistir` her zaman `(sonuç, iz)` döndürür — depodaki mevcut gelenek bu
    (`extraction.uzlastirici.kampanya_cikar` da `(kampanya, rapor)` döndürüyor).
    Ayrı bir sonuç sarmalayıcı tipi eklemek, iki farklı dönüş geleneği yaratıp
    çağrı yerlerini gereksizce böler.
    """

    ad: str
    llm_kullanir: bool

    def calistir(self, girdi: Any) -> tuple[Any, AjanIzi]: ...


__all__ = ["Ajan", "AjanIzi", "IzDefteri", "iz_tut"]
