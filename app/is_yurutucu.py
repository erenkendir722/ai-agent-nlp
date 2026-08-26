"""Arka plan işi + olay kuyruğu — «Canlı Boru Hattı» sayfasının motoru.

Streamlit betiği her yeniden çizimde BAŞTAN koşar. Dakikalarca süren bir
toplama ya da çıkarım işi bu yüzden betiğin içinde koşamaz: koşarsa arayüz
donar, kullanıcı sekme değiştirdiğinde iş kaybolur. İş ayrı bir parçacığa
alınır, ilerlemesi kuyruğa akar, çizimi betik parçacığı yapar.

TEK KATI KURAL: işçi iş parçacığı hiçbir `st.*` çağırmaz.
    Streamlit'in çizim bağlamı betik parçacığına bağlıdır; başka bir
    parçacıktan `st.write` çağırmak ya sessizce hiçbir şey yapmaz ya da
    "missing ScriptRunContext" uyarısı üretir. Bu, `temel_kaziyici.py`'deki
    «kazıyıcı ekrana hiçbir şey yazmaz» tasarımının aynısıdır — geri çağrı
    arayüzü (`Ilerleme`, `CikarimIlerlemesi`) zaten bunun için var.

İKİNCİ KURAL: sessiz yutma yok.
    İş parçacığındaki istisna `is.hata`'ya alınır ve arayüzde kırmızı kutuyla
    gösterilir; `dev_mode` açıksa tam yığın izi de. Yakalanıp yok sayılmaz —
    `embed_text`'in sıfır vektör döndürüp RAG'ı dört gün çalışıyor
    göstermesinin dersi (bkz. CLAUDE.md, «Sessiz yutma yasak»).
"""

from __future__ import annotations

import queue
import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

AZAMI_CEKIS = 400
"""Tek çizimde kuyruktan alınacak azami olay.

Çıkarım 16 işçiyle koşarken kuyruk çizimden hızlı doluyor. Sınır olmadan
`olaylari_cek` üretici kadar hızlı tüketmeye çalışır ve çizim gecikir;
kalan olaylar kuyrukta bekler, bir sonraki çizimde alınır — kaybolmazlar.
"""


@dataclass
class ArkaPlanIsi:
    """Tek bir arka plan koşusu: parçacık + olay kuyruğu + iptal bayrağı."""

    ad: str
    kuyruk: queue.Queue = field(default_factory=queue.Queue)
    iptal: threading.Event = field(default_factory=threading.Event)
    parcacik: threading.Thread | None = None
    sonuc: Any = None
    hata: BaseException | None = None
    iz: str = ""
    baslangic: float = field(default_factory=time.monotonic)
    bitis: float | None = None

    # -- İşçi tarafı (bu iki metot İŞ PARÇACIĞINDAN çağrılır) -------------

    def bildir(self, olay: Any) -> None:
        """İlerleme olayını kuyruğa koyar. Çizim yapmaz, bloklamaz."""
        self.kuyruk.put(olay)

    def iptal_edildi_mi(self) -> bool:
        """`topla`/`cikarim_kos` bu geri çağrıyı yoklar."""
        return self.iptal.is_set()

    # -- Arayüz tarafı ----------------------------------------------------

    def iptal_et(self) -> None:
        """İşbirlikçi durdurma: bayrağı kaldırır, parçacığı ÖLDÜRMEZ.

        Selenium'un temiz kapanması buna bağlı: `topla` yarıda öldürülürse
        Chrome süreci makinede asılı kalır.
        """
        self.iptal.set()

    def calisiyor_mu(self) -> bool:
        return self.parcacik is not None and self.parcacik.is_alive()

    def gecen_sure(self) -> float:
        """Ölçülen süre — koşarken canlı, bitince donmuş."""
        return (self.bitis or time.monotonic()) - self.baslangic


def baslat(ad: str, hedef: Callable[[ArkaPlanIsi], Any]) -> ArkaPlanIsi:
    """`hedef`'i arka planda koşturur ve işi döner.

    `hedef` tek argüman alır: işin kendisi. İlerlemeyi `is_.bildir(...)` ile
    yollar, iptali `is_.iptal_edildi_mi` ile yoklar. Dönüş değeri
    `is_.sonuc`'a yazılır.

    `daemon=True`: Streamlit kapanırken asılı bir parçacık süreci canlı
    tutmasın. İptal yolu zaten var, bu yalnız son çare.
    """
    is_ = ArkaPlanIsi(ad=ad)

    def _sar() -> None:
        try:
            is_.sonuc = hedef(is_)
        except BaseException as hata:  # noqa: BLE001 — yutmuyoruz, taşıyoruz
            is_.hata = hata
            is_.iz = traceback.format_exc()
        finally:
            is_.bitis = time.monotonic()

    parcacik = threading.Thread(target=_sar, name=f"kl-{ad}", daemon=True)
    is_.parcacik = parcacik
    parcacik.start()
    return is_


def olaylari_cek(is_: ArkaPlanIsi, azami: int = AZAMI_CEKIS) -> list[Any]:
    """Kuyruğu BLOKLAMADAN boşaltır.

    Bloklamak, çizim parçacığını işçiye bağlardı: iş yavaşladığında arayüz de
    donardı. Kuyruk boşsa boş liste döner — çizim yine de yapılır, çünkü
    geçen süre sayacı akmaya devam etmeli.
    """
    olaylar: list[Any] = []
    for _ in range(azami):
        try:
            olaylar.append(is_.kuyruk.get_nowait())
        except queue.Empty:
            break
    return olaylar


__all__ = ["AZAMI_CEKIS", "ArkaPlanIsi", "baslat", "olaylari_cek"]
