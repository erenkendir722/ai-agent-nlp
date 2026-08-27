"""Tek atama — bir sayıyı yalnız bir alan sahiplenebilir (bulgu: jüri metni).

19 Ağustos'ta jüri, «o anda kendi test verimizi verebiliriz» dedi. Jüri tarzı
DÜZ METİN denendi ve sistem yanlış cevap verdi:

    "…aylık kâr payı oranı %2,45'ten başlıyor. … Tahsis ücreti %0,75."

    kar_payi_orani = 0.75   span=(138,145)
    tahsis_ucreti  = 0.75   span=(138,145)   <- AYNI SPAN
    Doğru cevap %2,45 tümüyle kaçırıldı.

Her kural metni bağımsız tarıyordu; aynı sayıyı iki alanın sahiplenmesini
engelleyen hiçbir şey yoktu. `kar_payi_orani` `secim="en_dusuk"` olduğu için
2,45 yerine 0,75'i seçiyordu.

SINIF HATASI: tahsis ücreti gerçek hayatta %0,5-1, kâr payı %2-4 seyreder.
Yani oranın altında ücret yüzdesi olan HER düz metinde kâr payı yanlış çıkardı.
Tablolarda oluşmuyordu (kolon başlığı yanlış kolonu eliyor) — ama jüri tablo
değil düz metin yapıştırır.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.extraction.kural import KURALLAR, Aday, _adaylari_bul, _tek_atama, kurallarla_cikar

URL = "manuel://juri"


def _cikar(metin: str) -> dict:
    return kurallarla_cikar(metin, URL, datetime(2026, 8, 19))


# ---------------------------------------------------------------------------
# 1) Bulgunun kendisi
# ---------------------------------------------------------------------------


JURI_METNI = (
    "Emeklilere özel: 36 ay vadeli ihtiyaç finansmanında aylık kâr payı oranı "
    "%2,45'ten başlıyor. 250.000 TL'ye kadar finansman. Tahsis ücreti %0,75. "
    "Kampanya 15 Ekim 2026'da sona erer."
)


class TestJuriMetni:
    def test_kar_payi_ucret_yuzdesini_almaz(self) -> None:
        """REGRESYON — kâr payı %0,75 çıkıyordu, doğrusu %2,45."""
        alanlar = _cikar(JURI_METNI)
        assert alanlar["kar_payi_orani"].deger == pytest.approx(2.45)

    def test_tahsis_ucreti_dogru_kalir(self) -> None:
        """Düzeltme, doğru olan alanı bozmamalı."""
        alanlar = _cikar(JURI_METNI)
        assert alanlar["tahsis_ucreti"].deger == pytest.approx(0.75)

    def test_iki_alan_ayni_deger_spanini_sahiplenmez(self) -> None:
        """Değişmez DEĞER span'ı üzerinedir, alıntı aralığı üzerinde değil.

        `Alan.kaynak` çevreleyen CÜMLEYİ tutar; aynı cümleden iki farklı alan
        çıkması meşrudur ("...%2,45... 36 ay..."). Tek atama kuralı, metindeki
        aynı SAYIYI iki alanın birden sahiplenmesini yasaklar.
        """
        sahipler: dict[tuple[int, int], str] = {}
        for kural in KURALLAR:
            for aday in _adaylari_bul(JURI_METNI, kural):
                sahipler.setdefault((aday.baslangic, aday.bitis), []).append(kural.alan)  # type: ignore[union-attr]
        cakisan = {s: a for s, a in sahipler.items() if len(a) > 1}
        assert cakisan, "önkoşul değişmiş: bu metinde artık çakışma yok"

        kalan = _tek_atama(
            {kural.alan: _adaylari_bul(JURI_METNI, kural) for kural in KURALLAR}
        )
        atanmis: dict[tuple[int, int], str] = {}
        for alan, adaylar in kalan.items():
            for aday in adaylar:
                anahtar = (aday.baslangic, aday.bitis)
                assert anahtar not in atanmis, (
                    f"span {anahtar} hem {atanmis[anahtar]} hem {alan} tarafından "
                    "sahiplenildi"
                )
                atanmis[anahtar] = alan

    def test_diger_alanlar_bozulmadi(self) -> None:
        alanlar = _cikar(JURI_METNI)
        assert alanlar["vade_ay_max"].deger == 36
        assert alanlar["finansman_tutari_max"].deger == pytest.approx(250_000.0)
        assert alanlar["kampanya_bitis"].deger.isoformat() == "2026-10-15"


# ---------------------------------------------------------------------------
# 2) SINIF — aynı kalıbın başka örnekleri de yakalanıyor mu
# ---------------------------------------------------------------------------


class TestSinifKapandiMi:
    def test_ucret_orani_kar_payindan_dusukken(self) -> None:
        """Genel kalıp: düşük ücret yüzdesi + yüksek kâr payı, aynı paragrafta."""
        metin = (
            "Konut finansmanında aylık kâr payı oranı %3,10'dur. "
            "Tahsis ücreti %0,25 olarak uygulanır."
        )
        alanlar = _cikar(metin)
        assert alanlar["kar_payi_orani"].deger == pytest.approx(3.10)
        assert alanlar["tahsis_ucreti"].deger == pytest.approx(0.25)

    def test_dosya_masrafi_yazimiyla_da_calisir(self) -> None:
        """Ezber değil: farklı sözcük (`dosya masrafı`) aynı kapıdan geçer."""
        metin = (
            "İhtiyaç finansmanında aylık kâr payı oranı %2,89. "
            "Dosya masrafı %0,40 tutarındadır."
        )
        alanlar = _cikar(metin)
        assert alanlar["kar_payi_orani"].deger == pytest.approx(2.89)

    def test_tek_oran_varsa_davranis_degismez(self) -> None:
        metin = "Aylık kâr payı oranı %1,89'dan başlayan konut finansmanı."
        assert _cikar(metin)["kar_payi_orani"].deger == pytest.approx(1.89)


# ---------------------------------------------------------------------------
# 3) Çözüm ölçütü: MESAFE, güven değil
# ---------------------------------------------------------------------------


class TestSahiplikOlcutu:
    def test_mesafe_kazanir_guven_degil(self) -> None:
        """Sahiplik ÖNSELLE değil, bu span'a ait kanıtla çözülür.

        Ölçülen değerler (jüri metni, span 138-145):
            kar_payi_orani guven=0,8828  (taban 0,93 — sözcük UZAK)
            tahsis_ucreti  guven=0,8415  (taban 0,85 — sözcük BİTİŞİK)

        Güvene bakan bir kural span'ı yanlış alana verirdi.
        """
        kp = next(k for k in KURALLAR if k.alan == "kar_payi_orani")
        tu = next(k for k in KURALLAR if k.alan == "tahsis_ucreti")
        kp_aday = next(a for a in _adaylari_bul(JURI_METNI, kp) if a.deger == 0.75)
        tu_aday = next(a for a in _adaylari_bul(JURI_METNI, tu) if a.deger == 0.75)

        assert kp_aday.guven > tu_aday.guven, "önkoşul değişmiş: güven artık ayırt ediyor"
        assert tu_aday.mesafe < kp_aday.mesafe, "mesafe doğru sahibi göstermiyor"

        kalan = _tek_atama({"kar_payi_orani": [kp_aday], "tahsis_ucreti": [tu_aday]})
        assert kalan["tahsis_ucreti"] == [tu_aday]
        assert kalan["kar_payi_orani"] == []

    def test_kaybeden_alan_susmaz_sonrakine_gecer(self) -> None:
        """Span'ı kaybeden alan, KALAN adaylarından seçim yapar."""
        alanlar = _cikar(JURI_METNI)
        assert alanlar["kar_payi_orani"].deger == pytest.approx(2.45)

    def test_esitlikte_deterministik(self) -> None:
        """Aynı mesafe -> `KURALLAR` bildirim sırası. Keyfi ama TEKRARLANABİLİR."""
        a = Aday(deger=1.0, ham_ifade="%1", baslangic=10, bitis=12, guven=0.5, mesafe=5)
        b = Aday(deger=1.0, ham_ifade="%1", baslangic=10, bitis=12, guven=0.9, mesafe=5)
        ilk = _tek_atama({"kar_payi_orani": [a], "indirim_orani": [b]})
        ikinci = _tek_atama({"kar_payi_orani": [a], "indirim_orani": [b]})
        assert [k for k, v in ilk.items() if v] == [k for k, v in ikinci.items() if v]

    def test_cakisma_yoksa_hicbir_aday_dusmez(self) -> None:
        a = Aday(deger=1.0, ham_ifade="%1", baslangic=10, bitis=12, guven=0.9, mesafe=3)
        b = Aday(deger=2.0, ham_ifade="%2", baslangic=40, bitis=42, guven=0.9, mesafe=3)
        kalan = _tek_atama({"kar_payi_orani": [a], "indirim_orani": [b]})
        assert kalan["kar_payi_orani"] == [a] and kalan["indirim_orani"] == [b]


# ---------------------------------------------------------------------------
# 4) Şartname madde 11'in kendi örneği bozulmadı
# ---------------------------------------------------------------------------


def test_sartname_ornegi_korundu() -> None:
    """Jürinin kendi tablosu — düzeltme bunu bozmamalı."""
    metin = (
        "A Bankası konut finansmanı kampanyası: %1,89 kâr payı oranı ile 120 aya "
        "kadar konut finansmanı. 5.000.000 TL'ye kadar. Dosya masrafı alınmamaktadır. "
        "Kampanya 31 Aralık 2026 tarihine kadar geçerlidir."
    )
    alanlar = _cikar(metin)
    assert alanlar["kar_payi_orani"].deger == pytest.approx(1.89)
    assert alanlar["vade_ay_max"].deger == 120
    assert alanlar["finansman_tutari_max"].deger == pytest.approx(5_000_000.0)
    assert alanlar["masrafsiz_mi"].deger is True


# ---------------------------------------------------------------------------
# 5) Sahiplik dışı kurallar — `taksit_sayisi` vadeyle YARIŞMAZ
# ---------------------------------------------------------------------------


class TestSahiplikDisi:
    """`taksit_sayisi` 27 Ağustos'a kadar 0/734 kayıtta doluydu.

    Sebep tam da bu dosyanın anlattığı hakemlikti: «6 taksit» için hem
    `vade_ay_max` hem `taksit_sayisi` AYNI span'ı üretiyor, mesafe ikisinde de
    0, ve beraberliği `KURALLAR` bildirim sırası çözüyordu. `vade_ay_max` önce
    bildirildiği için `taksit_sayisi` hiçbir zaman kazanamıyordu — şemada duran
    ama yapısal olarak erişilemeyen bir alan.

    Hakemliğin varsayımı («iki alan aynı sayıyı sahiplenmişse biri yanılıyor»)
    bu çift için yanlış: «6 taksit» hem 6 aylık ertelenmiş ödemedir hem 6
    taksittir. Altın seti etiketleyen dört kişi de bu ifadelere `vade_ay_max`
    yazmış — yani vadeyi taksitten AYIRMAK ölçülmüş bir gerileme getiriyordu
    (`make kural-olc`: vade F1 0,7671 -> 0,6866). Çözüm ayırmak değil, ikisinin
    birlikte var olmasına izin vermekti.
    """

    def test_taksit_ifadesi_iki_alani_birden_doldurur(self) -> None:
        alanlar = _cikar("Alışverişlerde vade farksız 6 taksit ile ödeyin.")
        assert alanlar["vade_ay_max"].deger == 6
        assert alanlar["taksit_sayisi"].deger == 6

    def test_ay_ve_taksit_ayri_yazildiginda_ayri_okunur(self) -> None:
        """Kesişim her zaman aynı sayı demek değil."""
        alanlar = _cikar("36 aya kadar vade ve 12 taksit imkanı.")
        assert alanlar["vade_ay_max"].deger == 36
        assert alanlar["taksit_sayisi"].deger == 12

    def test_saf_ay_ifadesi_taksit_uretmez(self) -> None:
        """Köken bilgisi ancak ayırt edebiliyorsa değerlidir."""
        alanlar = _cikar("%1,89 kâr payı oranı ile 120 aya kadar konut finansmanı.")
        assert alanlar["vade_ay_max"].deger == 120
        assert "taksit_sayisi" not in alanlar

    def test_sahiplik_disi_kural_kimseyi_dusurmez(self) -> None:
        """Bayrak DAR: okur, ama başka alanın span'ını çalmaz."""
        adaylar = {
            kural.alan: _adaylari_bul(
                "Alışverişlerde vade farksız 6 taksit ile ödeyin.", kural
            )
            for kural in KURALLAR
        }
        kalan = _tek_atama(adaylar)
        assert kalan["vade_ay_max"], "sahiplik dışı kural vadeyi düşürmüş"
        assert kalan["taksit_sayisi"], "sahiplik dışı kural kendi adayını kaybetmiş"

    def test_yarisan_kurallar_hala_hakemlikten_geciyor(self) -> None:
        """Bayrak, dosyanın asıl konusu olan düzeltmeyi delmemeli."""
        alanlar = _cikar(
            "…aylık kâr payı oranı %2,45'ten başlıyor. … Tahsis ücreti %0,75."
        )
        assert alanlar["kar_payi_orani"].deger == pytest.approx(2.45)
        assert alanlar["tahsis_ucreti"].deger == pytest.approx(0.75)
