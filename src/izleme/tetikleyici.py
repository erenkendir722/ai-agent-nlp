"""Tetikleyici — denetimin NE ZAMAN koşacağının takvimi.

**TANIMLI AMA KURULU DEĞİL.** Bu modül hiçbir şeyi kendiliğinden
başlatmaz: iş parçacığı açmaz, zamanlayıcı kurmaz, `cron`'a satır yazmaz.
Yalnız «bir sonraki koşu ne zaman olmalıydı» sorusuna cevap veren saf
hesaplardan ibarettir. `kurulu` alanı bu yüzden varsayılan `False`.

NEDEN KURULU DEĞİL — iki gerekçe, ikisi de bilinçli:

1. `data/raw` ve `data/katilim.db` teslim için DONMUŞ durumda. Yayımlanan
   doğruluk, doluluk ve kapsam sayıları o veri üzerinde ölçüldü. Kendiliğinden
   koşan bir toplama işi, `make eval` çıktısı ile `docs/SONUCLAR.md` arasında
   sessiz bir ayrışma üretir — projenin en pahalı bulduğu hata biçimi.
2. Kurulu bir zamanlayıcının çalıştığı GÖSTERİLEMEZ. Dinleyici arayüzden elle
   koşturulup sonucu ekranda izlenebilir; `crontab` satırı izlenemez.

Ürünleşince kurulacak yer hazır: `docs/KURUMSAL_ENTEGRASYON.md` §5 ve §8 zaten
«gecelik iş (cron / Airflow / SQL Agent)» diyor. `cron_satiri()` o satırı
üretir — jüriye «tasarlandı, bilerek kurulmadı» demenin somut karşılığı.

Saatler mentör geri bildiriminden birebir alındı: kampanya açılış/kapanış
saatleri 08:00, 17:00 ve gece yarısı.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

KAMPANYA_SAATLERI: tuple[time, ...] = (time(8, 0), time(17, 0), time(0, 0))
"""Kampanyaların açılıp kapandığı saatler (mentör geri bildirimi, 26 Ağu).

Gece yarısı `time(0, 0)` olarak yazılıyor — `time(24, 0)` diye bir şey yok;
24:00 ile 00:00 aynı andır ve `datetime` ilkini kabul etmez.
"""

VARSAYILAN_KOMUT = "make tazelik"


@dataclass(frozen=True)
class Tetikleyici:
    """Periyodik denetim takvimi. Kendiliğinden HİÇBİR ŞEY çalıştırmaz."""

    saatler: tuple[time, ...] = KAMPANYA_SAATLERI
    kurulu: bool = False
    """Bilerek `False`. Modül başlığındaki iki gerekçe geçerli olduğu sürece
    `True` yapılmamalı; yapılırsa `data/izleme/` dışına yazan bir iş kurulmadığı
    ayrıca doğrulanmalı."""

    komut: str = VARSAYILAN_KOMUT
    _sirali: tuple[time, ...] = field(init=False, repr=False, default=())

    def __post_init__(self) -> None:
        if not self.saatler:
            raise ValueError(
                "Tetikleyici en az bir saat ister — boş takvim, hiç koşmayan "
                "bir işi «zamanlandı» gibi gösterirdi."
            )
        object.__setattr__(self, "_sirali", tuple(sorted(set(self.saatler))))

    def sonraki_calisma(self, simdi: datetime) -> datetime:
        """`simdi`'den SONRAKİ ilk tetikleme anı.

        Tam tetikleme anında çağrılırsa BİR SONRAKİNİ döner: «şimdi» zaten
        koşuyor demektir, aynı anı iki kez döndürmek sonsuz döngü üretirdi.
        """
        for saat in self._sirali:
            aday = simdi.replace(
                hour=saat.hour, minute=saat.minute, second=0, microsecond=0
            )
            if aday > simdi:
                return aday
        ilk = self._sirali[0]
        return (simdi + timedelta(days=1)).replace(
            hour=ilk.hour, minute=ilk.minute, second=0, microsecond=0
        )

    def onceki_calisma(self, simdi: datetime) -> datetime:
        """`simdi`'den önceki en son tetikleme anı."""
        for saat in reversed(self._sirali):
            aday = simdi.replace(
                hour=saat.hour, minute=saat.minute, second=0, microsecond=0
            )
            if aday <= simdi:
                return aday
        son = self._sirali[-1]
        return (simdi - timedelta(days=1)).replace(
            hour=son.hour, minute=son.minute, second=0, microsecond=0
        )

    def gecikmis_mi(self, son_calisma: datetime | None, simdi: datetime) -> bool:
        """Son koşudan bu yana bir tetikleme anı kaçırıldı mı?

        `son_calisma` `None` ise (hiç koşulmamış) `True` — hiç denetlenmemiş
        veri, gecikmiş sayılır.
        """
        if son_calisma is None:
            return True
        return son_calisma < self.onceki_calisma(simdi)

    def cron_satiri(self) -> str:
        """Ürünleşince kurulacak `crontab` satırı — burada yalnız ÜRETİLİR.

        Jüriye «tasarlandı ama bilerek kurulmadı» demenin somut karşılığı:
        satır elde, kurulum kararı operatörün.
        """
        saatler = ",".join(str(s.hour) for s in self._sirali)
        dakikalar = sorted({s.minute for s in self._sirali})
        if len(dakikalar) != 1:
            raise ValueError(
                "cron satırı tek dakika değeri ister; saatler farklı "
                f"dakikalarda: {dakikalar}"
            )
        return f"{dakikalar[0]} {saatler} * * * {self.komut}"


__all__ = ["KAMPANYA_SAATLERI", "VARSAYILAN_KOMUT", "Tetikleyici"]
