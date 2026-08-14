"""Muhakeme ajanı — müşteri profiline uyan kampanyaları bulur.

Ürünün asıl farkı burada. Sistem artık *"kampanyaları listele"* değil,
banka çalışanının gerçek sorusunu cevaplıyor:

    "Karşımda maaş müşterisi, 800.000 TL konut finansmanı istiyor, 10 yıl
     vade. Rakiplerin hangisi bizden iyi teklif veriyor ve neden?"

Bu bir arama değil **kısıt çözme** problemidir: koşullar birbiriyle kesişir
(müşteri tipi VE tutar aralığı VE vade sınırı VE zorunlu ürün).

⚠️ BU AJAN LLM KULLANMAZ — bilinçli bir karar:
    Kısıt kontrolü ve aritmetik saf koddur. `1.87 < 1.89` karşılaştırmasını,
    taksit hesabını veya sıralamayı LLM'e yaptırmak, halüsinasyon savunmasıyla
    kazanılan güveni tek hamlede kaybettirir. LLM'in bu boru hattındaki tek
    işi, `uygunluk` alanlarını METİNDEN ÇIKARMAKTIR (çıkarım ajanı); çıkarılmış
    kısıtı çözmek koda aittir.

    Taksit hesabı için yeni kod da yazılmadı: `comparison.toplam_maliyet()`
    annüite formülünü zaten uyguluyor.

İKİ TASARIM KARARI:

1. **Uygun OLMAYANLAR da döner, sebebiyle.** "120 ay vade sunuyor ama minimum
   tutar 1.000.000 TL" demek, sessizce elemekten çok daha kullanışlıdır —
   banka çalışanı müşteriye ne söyleyeceğini öğrenir.
2. **Sıralama toplam maliyete göredir, manşet orana göre değil.** %1,87 / 96 ay
   / 5.000 TL masraflı bir ürün, %1,89 / 120 ay / masrafsız bir üründen pahalı
   olabilir. "En düşük oran her zaman en ucuz değildir."
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.ajanlar.temel import AjanIzi, iz_tut
from src.comparison.karsilastirma import toplam_maliyet
from src.schema import AYLIK_KAR_PAYI_UST_SINIRI, HedefKitle, Kampanya


@dataclass(frozen=True)
class MusteriProfili:
    """Banka çalışanının önündeki müşteri."""

    musteri_tipi: HedefKitle
    tutar: float
    vade_ay: int
    mevcut_urunler: list[str] = field(default_factory=list)
    segment: str | None = None
    """SEGMENT tipinde ayrım adı: "emekli", "öğrenci", "KOBİ".

    `HedefKitle.SEGMENT` geniş bir kutudur; emekliye açık bir kampanyayı
    öğrenciye önermemek için ad ayrıca tutulur."""

    def ozet(self) -> str:
        return (
            f"{self.musteri_tipi.value} · {self.tutar:,.0f} TL · {self.vade_ay} ay"
        ).replace(",", ".")


@dataclass(frozen=True)
class Gerekce:
    """Tek bir kısıtın sonucu — arayüzde satır satır gösterilir."""

    kural: str
    gecti_mi: bool
    aciklama: str
    alinti: str = ""

    def __str__(self) -> str:
        return ("✅ " if self.gecti_mi else "❌ ") + self.aciklama


@dataclass
class UygunlukSonucu:
    kampanya_id: str
    banka_adi: str
    uygun_mu: bool
    gerekceler: list[Gerekce] = field(default_factory=list)
    maliyet: dict[str, float] | None = None
    veri_eksik: bool = False
    """Kampanyanın `uygunluk` koşulları hiç çıkarılmamış.

    Bu kayıtlar 'uygun' sayılır ama işaretlenir: eksik veriyi sessizce
    'uygun' diye göstermek, sistemin bilmediği bir şeyi biliyormuş gibi
    sunması olurdu."""

    @property
    def toplam_geri_odeme(self) -> float | None:
        return self.maliyet["toplam_geri_odeme"] if self.maliyet else None

    def engelleyenler(self) -> list[Gerekce]:
        return [g for g in self.gerekceler if not g.gecti_mi]


class MuhakemeAjani:
    """Profil ↔ kampanya kısıt çözücü. Deterministik, LLM'siz."""

    ad = "muhakeme"
    llm_kullanir = False

    # -- Tekil kısıt kontrolleri ------------------------------------------

    @staticmethod
    def _musteri_tipi_uyar(profil: MusteriProfili, kampanya: Kampanya) -> Gerekce | None:
        kosul = kampanya.uygunluk
        if kosul is None or not kosul.musteri_tipi:
            return None  # kısıt yok = herkese açık

        hedefler = set(kosul.musteri_tipi)
        if HedefKitle.TUM_MUSTERILER in hedefler or profil.musteri_tipi in hedefler:
            # SEGMENT eşleşmesi ad düzeyinde de doğrulanmalı: "emekliye özel"
            # bir kampanya öğrenciye uygun değildir.
            if (
                profil.musteri_tipi == HedefKitle.SEGMENT
                and kosul.segment_detayi
                and profil.segment
                and profil.segment.casefold()
                not in {s.casefold() for s in kosul.segment_detayi}
            ):
                return Gerekce(
                    "musteri_tipi",
                    False,
                    f"Kampanya {', '.join(kosul.segment_detayi)} segmentine özel; "
                    f"müşteri {profil.segment} segmentinde.",
                )
            return Gerekce(
                "musteri_tipi", True, f"Müşteri tipi uygun ({profil.musteri_tipi.value})."
            )

        adlar = ", ".join(h.value for h in sorted(hedefler, key=lambda h: h.value))
        return Gerekce(
            "musteri_tipi",
            False,
            f"Kampanya {adlar} için; müşteri {profil.musteri_tipi.value}.",
        )

    @staticmethod
    def _tutar_uyar(profil: MusteriProfili, kampanya: Kampanya) -> Gerekce | None:
        kosul = kampanya.uygunluk
        if kosul is None:
            return None

        if kosul.min_tutar is not None and profil.tutar < kosul.min_tutar:
            return Gerekce(
                "min_tutar",
                False,
                f"Minimum tutar {kosul.min_tutar:,.0f} TL; "
                f"talep {profil.tutar:,.0f} TL.".replace(",", "."),
            )
        if kosul.max_tutar is not None and profil.tutar > kosul.max_tutar:
            return Gerekce(
                "max_tutar",
                False,
                f"Azami tutar {kosul.max_tutar:,.0f} TL; "
                f"talep {profil.tutar:,.0f} TL.".replace(",", "."),
            )
        if kosul.min_tutar is not None or kosul.max_tutar is not None:
            return Gerekce("tutar", True, "Talep edilen tutar aralıkta.")
        return None

    @staticmethod
    def _vade_uyar(profil: MusteriProfili, kampanya: Kampanya) -> Gerekce | None:
        kosul = kampanya.uygunluk
        if kosul is None:
            return None

        if kosul.min_vade_ay is not None and profil.vade_ay < kosul.min_vade_ay:
            return Gerekce(
                "min_vade_ay",
                False,
                f"Asgari vade {kosul.min_vade_ay} ay; talep {profil.vade_ay} ay.",
            )
        if kosul.max_vade_ay is not None and profil.vade_ay > kosul.max_vade_ay:
            return Gerekce(
                "max_vade_ay",
                False,
                f"Azami vade {kosul.max_vade_ay} ay; talep {profil.vade_ay} ay.",
            )
        if kosul.min_vade_ay is not None or kosul.max_vade_ay is not None:
            return Gerekce("vade", True, f"{profil.vade_ay} ay vade kampanya sınırları içinde.")
        return None

    @staticmethod
    def _zorunlu_urun_uyar(profil: MusteriProfili, kampanya: Kampanya) -> Gerekce | None:
        kosul = kampanya.uygunluk
        if kosul is None or not kosul.zorunlu_urun:
            return None

        sahip = {u.casefold() for u in profil.mevcut_urunler}
        eksik = [u for u in kosul.zorunlu_urun if u.casefold() not in sahip]
        if eksik:
            return Gerekce(
                "zorunlu_urun",
                False,
                f"Şu ürünler gerekli: {', '.join(eksik)}.",
            )
        return Gerekce(
            "zorunlu_urun", True, f"Gerekli ürünler mevcut: {', '.join(kosul.zorunlu_urun)}."
        )

    # -- Maliyet -----------------------------------------------------------

    @staticmethod
    def _maliyet_hesapla(profil: MusteriProfili, kampanya: Kampanya) -> dict[str, float] | None:
        """Toplam geri ödemeyi hesaplar. Oran yoksa ya da MAKUL DEĞİLSE hesap yapılmaz.

        Makullük kontrolü şart: veritabanında `kar_payi_orani` 0 ile 84,93
        arasında değerler taşıyor — üst uçtakiler "%80'e varan indirim" gibi
        ifadelerden yanlış çıkarılmış. Böyle bir orandan taksit hesaplayıp
        sonucu tabloda göstermek, saçma bir sayıyı kendinden emin biçimde
        sunmak olur. "Belirtilmemiş" demek her zaman daha dürüsttür.
        """
        oran_alani = kampanya.kar_payi_orani
        if not oran_alani.var_mi:
            return None
        try:
            oran = float(oran_alani.deger)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        # Sıfır de makul değil: aylık %0 kâr payı, müşterinin anaparayı birebir
        # geri ödemesi demek olurdu — kampanyalı bir katılım finansmanında
        # böyle bir ürün yok. Veritabanındaki tek 0 değeri ham ifadesi '0%'
        # olan bir kayıttan geliyor ve büyük olasılıkla "0 masraf" benzeri bir
        # ifadeden yanlış çıkarılmış. Hesaplanırsa listenin EN TEPESİNE çıkar.
        # Altın set denetleyicisi de aynı aralığı kullanıyor (0 < oran < 15).
        if not 0 < oran < AYLIK_KAR_PAYI_UST_SINIRI:
            return None

        tahsis = 0.0
        if kampanya.tahsis_ucreti.var_mi:
            try:
                tahsis = float(kampanya.tahsis_ucreti.deger)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                tahsis = 0.0

        try:
            return toplam_maliyet(profil.tutar, oran, profil.vade_ay, tahsis)
        except ValueError:
            return None

    # -- Ana akış ----------------------------------------------------------

    def degerlendir(self, profil: MusteriProfili, kampanya: Kampanya) -> UygunlukSonucu:
        """Tek kampanyayı profile karşı çözer."""
        kontroller = (
            self._musteri_tipi_uyar,
            self._tutar_uyar,
            self._vade_uyar,
            self._zorunlu_urun_uyar,
        )
        gerekceler = [g for kontrol in kontroller if (g := kontrol(profil, kampanya))]

        veri_eksik = kampanya.uygunluk is None or not kampanya.uygunluk.kisit_var_mi()
        if veri_eksik:
            gerekceler.append(
                Gerekce(
                    "uygunluk",
                    True,
                    "Kampanyanın uygunluk koşulları metinden çıkarılamadı; "
                    "kısıtlar doğrulanamadı.",
                )
            )

        uygun = all(g.gecti_mi for g in gerekceler)
        return UygunlukSonucu(
            kampanya_id=kampanya.kampanya_id,
            banka_adi=kampanya.banka_adi,
            uygun_mu=uygun,
            gerekceler=gerekceler,
            maliyet=self._maliyet_hesapla(profil, kampanya) if uygun else None,
            veri_eksik=veri_eksik,
        )

    def calistir(
        self, girdi: tuple[MusteriProfili, list[Kampanya]]
    ) -> tuple[list[UygunlukSonucu], AjanIzi]:
        """Tüm kampanyaları çözer ve TOPLAM MALİYETE göre sıralar.

        Sıralama:
          1. Uygun olanlar, toplam geri ödemesi düşükten yükseğe
          2. Maliyeti hesaplanamayanlar (oran yok) — "veri yok" en iyi sonuç
             gibi görünmemeli
          3. Uygun olmayanlar (yine de döner, sebepleriyle)
        """
        profil, kampanyalar = girdi

        with iz_tut(self.ad, llm=False, girdi=profil.ozet()) as iz:
            sonuclar = [self.degerlendir(profil, k) for k in kampanyalar]

            def anahtar(s: UygunlukSonucu) -> tuple[int, int, float]:
                if not s.uygun_mu:
                    return (2, 0, 0.0)
                if s.toplam_geri_odeme is None:
                    return (1, 0, 0.0)
                return (0, 0, s.toplam_geri_odeme)

            sonuclar.sort(key=anahtar)

            uygun = [s for s in sonuclar if s.uygun_mu]
            elenen = len(sonuclar) - len(uygun)
            iz.cikti_ozeti = f"{len(uygun)}/{len(sonuclar)} uygun"
            iz.karar_gerekcesi = (
                f"{elenen} kampanya elendi: "
                + ", ".join(
                    sorted({g.kural for s in sonuclar if not s.uygun_mu for g in s.engelleyenler()})
                )
                if elenen
                else f"{len(uygun)} kampanyanın tamamı profile uygun"
            )

        return sonuclar, iz


__all__ = ["Gerekce", "MuhakemeAjani", "MusteriProfili", "UygunlukSonucu"]
