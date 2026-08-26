"""Eleştirmen ajan — çıkarılan her değerin kaynakta gerçekten geçtiğini doğrular.

Sistemin halüsinasyon savunması budur ve **LLM kullanmaz**. Model bir sayı
uydurursa o sayı sisteme giremez, çünkü ham metinde karşılığı yoktur. Kontrol
istem mühendisliği değil, koddur: modelin iyi niyetine güvenmez.

    Çıkarım ajanı  --"%1,89"-->  Eleştirmen  --metinde ara-->  kabul / ret

NEDEN AYRI MODÜL (önceden `extraction/llm.py` içindeydi):

1. **Ablasyon ölçülebilsin diye.** Sunumun *"neden bu kadar ajan?"* sorusuna
   cevabı olan tablo, "ajan var ama eleştirmen yok" satırını içeriyor. O satır
   ancak eleştirmen KAPATILABİLİR olduğunda ölçülebilir. Gömülü bir `if`
   bloğunu kapatmak mümkün değildi; ajan olarak ayrılınca `etkin=False` yeter.
2. **Jüriye tek dosya gösterilebilsin diye.** "Halüsinasyonu nasıl
   engelliyorsunuz?" sorusunun cevabı 40 satırlık bu dosyadır.

KANIT ZORUNLU ALANLARIN TEK KAYNAĞI:
    Liste `schema.KANIT_ZORUNLU_ALANLAR`'dan gelir. Önceden `llm.py` kendi
    listesini `frozenset(_AYRISTIRICILAR) - {"masrafsiz_mi"}` ile türetiyordu;
    ikisi bugün aynı kümeye çıkıyordu ama farklı yollardan. `_AYRISTIRICILAR`'a
    yeni bir ayrıştırıcı eklenmesi ikisini sessizce ayrıştırırdı — ve ayrışma
    halüsinasyon denetiminde delik açardı, testte değil.
"""

from __future__ import annotations

import logging

from src.ajanlar.temel import AjanIzi, iz_tut
from src.preprocessing.normalizasyon import arama_anahtari
from src.schema import KANIT_ZORUNLU_ALANLAR

log = logging.getLogger(__name__)

ALINTI_PENCERESI = 160
"""Bulunan değerin çevresinden alınacak bağlam genişliği (karakter).

Arayüzde kullanıcıya gösterilen alıntı budur; jüri "bu sayı nereden geldi?"
diye sorduğunda cevap tek tıkla ekranda olsun diye değerin yalnız kendisi
değil, içinde geçtiği cümle saklanır."""


class ElestirmenAjani:
    """Değer ↔ kaynak metin doğrulaması. Deterministik, LLM'siz."""

    ad = "elestirmen"
    llm_kullanir = False

    def __init__(self, *, etkin: bool = True) -> None:
        self.etkin = etkin
        """`False` yalnız ABLASYON içindir (`--elestirmen-yok`).

        Kapatınca çıkarılan değerler doğrulanmadan geçer ve halüsinasyon oranı
        yükselir — tablodaki 'eleştirmen yok' satırının ürettiği sayı budur.
        Üretimde asla kapatılmaz."""

        self.reddedilen: list[str] = []

    # -- Tekil alan doğrulaması -------------------------------------------

    def konum_bul(self, metin: str, ifade: str) -> tuple[int, int] | None:
        """İfadeyi metinde arar — üç aşamalı, giderek daha bağışlayıcı.

        Bağışlayıcılığın sınırı nettir: **biçim** farkı hoş görülür, **sayı**
        farkı görülmez. "%1,89" yerine "% 1,89" yazmak halüsinasyon değildir;
        şartname 5.6 zaten `%2,05` / `% 2.05` / `2.05 %` üçünü aynı değer
        saymamızı istiyor. Ama rakamların kendisi metinde geçmek zorundadır.

        1. Birebir arama — kesin konum.
        2. **Boşluktan bağımsız arama** — kesin konum. Boşluklar iki taraftan
           da atılır, kalan karakter dizisi birebir eşleşmek zorundadır.
        3. `arama_anahtari` normalizasyonu (küçük harf, şapka, kesme) —
           yaklaşık konum, çünkü bu dönüşüm uzunluğu değiştirebiliyor.

        2. adım 14 Ağustos'ta eklendi: `llm.py`'nin belgesi bu davranışı
        anlatıyordu ama kod yapmıyordu — `arama_anahtari` boşluğu tekilleştirir,
        kaldırmaz. Yani "% 1,89" reddediliyordu.
        """
        if not ifade:
            return None

        konum = metin.find(ifade)
        if konum != -1:
            return konum, konum + len(ifade)

        aralik = self._bosluksuz_ara(metin, ifade)
        if aralik is not None:
            return aralik

        anahtar = arama_anahtari(ifade)
        if len(anahtar) < 2:
            return None
        konum = arama_anahtari(metin).find(anahtar)
        if konum == -1:
            return None

        # Normalizasyon uzunluğu kaydırabilir; yaklaşık konum alıntı için yeterli.
        yaklasik = min(konum, max(0, len(metin) - len(ifade)))
        return yaklasik, min(len(metin), yaklasik + len(ifade))

    @staticmethod
    def _bosluksuz_ara(metin: str, ifade: str) -> tuple[int, int] | None:
        """Boşlukları yok sayarak arar ve ORİJİNAL metindeki kesin aralığı verir.

        Karakter haritası tutulmasının sebebi alıntı: kullanıcıya gösterilen
        kanıt ham metinden kesilir, dolayısıyla konumun yaklaşık değil gerçek
        olması gerekir.
        """
        hedef = "".join(ifade.split())
        if len(hedef) < 2:
            return None

        sikistirilmis: list[str] = []
        harita: list[int] = []
        for i, karakter in enumerate(metin):
            if not karakter.isspace():
                sikistirilmis.append(karakter)
                harita.append(i)

        yer = "".join(sikistirilmis).find(hedef)
        if yer == -1:
            return None
        return harita[yer], harita[yer + len(hedef) - 1] + 1

    def dogrula(
        self, alan_adi: str, ham_ifade: str, metin: str, *, url: str = ""
    ) -> tuple[bool, tuple[int, int] | None]:
        """(kabul_edildi_mi, konum) döndürür.

        Kanıt zorunlu olmayan alanlar (sınıflandırma etiketleri, serbest metin
        özetleri) her zaman kabul edilir: enum değeri metinde geçmez, özet ise
        modelin yeniden ifade etmesi meşrudur. Ret yalnız sayısal ve tarihsel
        alanlarda uygulanır — halüsinasyonun gerçekten zarar verdiği yer orası.
        """
        konum = self.konum_bul(metin, ham_ifade)

        if alan_adi not in KANIT_ZORUNLU_ALANLAR:
            return True, konum

        if not self.etkin:
            # Ablasyon: doğrulama kapalı, değer olduğu gibi geçer.
            return True, konum

        if konum is None:
            self.reddedilen.append(f"{alan_adi}={ham_ifade!r}")
            log.warning(
                "HALÜSİNASYON REDDİ | %s = %r metinde bulunamadı (%s)",
                alan_adi, ham_ifade, url,
            )
            return False, None

        return True, konum

    def alinti(self, metin: str, baslangic: int, bitis: int) -> str:
        """Değerin çevresindeki bağlamı döndürür — arayüzdeki kanıt."""
        sol = max(0, baslangic - ALINTI_PENCERESI)
        sag = min(len(metin), bitis + ALINTI_PENCERESI)
        return metin[sol:sag].strip()

    # -- Ajan sözleşmesi ---------------------------------------------------

    def calistir(self, girdi: dict[str, object]) -> tuple[dict[str, object], AjanIzi]:
        """Bir kayıt için toplu doğrulama; `{alan: ham_ifade}` bekler.

        Kabul edilen alanları döndürür. Boru hattı alan alan `dogrula()`
        çağırdığı için bu yol esas olarak orkestratör ve ablasyon içindir.
        """
        metin = str(girdi.get("metin", ""))
        alanlar = dict(girdi.get("alanlar", {}))  # type: ignore[arg-type]
        onceki_ret = len(self.reddedilen)

        with iz_tut(self.ad, llm=False, girdi=f"{len(alanlar)} alan") as iz:
            kabul = {
                ad: deger
                for ad, deger in alanlar.items()
                if self.dogrula(ad, str(deger), metin)[0]
            }
            reddedilen = len(self.reddedilen) - onceki_ret
            iz.cikti_ozeti = f"{len(kabul)} alan kabul"
            iz.karar_gerekcesi = (
                f"{reddedilen} alan reddedildi: değer ham metinde bulunamadı"
                if reddedilen
                else f"{len(kabul)} alanın tamamı ham metinde doğrulandı"
            )
            if not self.etkin:
                iz.karar_gerekcesi = "ABLASYON: doğrulama kapalı, hiçbir değer denetlenmedi"

        return kabul, iz


__all__ = ["ALINTI_PENCERESI", "ElestirmenAjani"]
