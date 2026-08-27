"""Banka Profili ekranının SÖZLEŞMESİ — AĞ İSTEMEZ.

Sayfa yeni çıkarım yapmaz; her sayı mevcut veritabanından türetilir. Testler
o türetmelerin doğruluğunu bağımsız hesapla karşılaştırır — ekranın çizilmesi
tek başına «sayı doğru» demek değildir.

ÜÇ İDDİA:
    «yalnız seçili bankanın kayıtları sayılır»      -> TestKapsam
    «yakında bitenler doğru süzülür»                -> TestYakindaBitenler
    «veri bayatsa kullanıcı uyarılır»               -> TestTazelik
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

SAYFA = KOK / "app" / "pages" / "5_Banka_Profili.py"


def _veri_var_mi() -> bool:
    try:
        from src.depolama import tum_kayitlar

        return len(tum_kayitlar()) >= 2
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _veri_var_mi(), reason="veritabanı boş — önce `make extract`"
)


@pytest.fixture(scope="module")
def kayitlar():
    from src.depolama import tum_kayitlar

    return tum_kayitlar()


def _kos(banka: str | None = None):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(SAYFA), default_timeout=300)
    at.run()
    if banka is not None:
        at.selectbox[0].set_value(banka).run()
    return at


def _gun_kaldi(deger) -> int | None:
    if deger is None:
        return None
    try:
        return (date.fromisoformat(str(deger)[:10]) - date.today()).days
    except ValueError:
        return None


class TestKapsam:
    def test_her_banka_istisnasiz_cizilir(self, kayitlar) -> None:
        for banka in sorted({k.banka_adi for k in kayitlar}):
            at = _kos(banka)
            assert not at.exception, (
                f"{banka}: " + " | ".join(str(e.value)[:160] for e in at.exception)
            )

    def test_kampanya_sayisi_yalniz_secili_bankadan(self, kayitlar) -> None:
        """Sızıntı testi: başka bankanın kaydı sayıya karışmamalı."""
        banka = max(
            {k.banka_adi for k in kayitlar},
            key=lambda b: sum(1 for k in kayitlar if k.banka_adi == b),
        )
        beklenen = sum(1 for k in kayitlar if k.banka_adi == banka)

        at = _kos(banka)
        kampanya_olcusu = next(m for m in at.metric if m.label == "Kampanya")
        assert int(str(kampanya_olcusu.value).replace(".", "")) == beklenen

    def test_kar_payi_araligi_gercek_degerlerden(self, kayitlar) -> None:
        """Aralık uydurulmaz: ekrandaki uçlar veritabanındaki uçlar olmalı."""
        adaylar = [
            b for b in {k.banka_adi for k in kayitlar}
            if sum(1 for k in kayitlar if k.banka_adi == b and k.kar_payi_orani is not None) >= 2
        ]
        assert adaylar, "kâr payı taşıyan banka yok — test kurgusu bozuk"
        banka = adaylar[0]
        oranlar = [
            k.kar_payi_orani for k in kayitlar
            if k.banka_adi == banka and k.kar_payi_orani is not None
        ]

        at = _kos(banka)
        yazi = str(next(m for m in at.metric if m.label == "Kâr payı oranı").value)
        for uc in (min(oranlar), max(oranlar)):
            assert f"{uc:.2f}".replace(".", ",") in yazi, (
                f"{uc} ekranda yok: {yazi!r}"
            )


class TestYakindaBitenler:
    def test_yalniz_yedi_gun_icindekiler_listelenir(self, kayitlar) -> None:
        """Geçmiş tarihli ya da uzak kampanya bu tabloya girmemeli."""
        for banka in sorted({k.banka_adi for k in kayitlar}):
            beklenen = sum(
                1 for k in kayitlar
                if k.banka_adi == banka
                and (kalan := _gun_kaldi(k.kampanya_bitis)) is not None
                and 0 <= kalan <= 7
            )
            at = _kos(banka)
            basliklar = [str(s.value) for s in at.subheader]
            varmi = any("Yakında biten" in b for b in basliklar)

            if beklenen == 0:
                assert not varmi, f"{banka}: biten kampanya yokken bölüm çizilmiş"
            else:
                assert varmi, f"{banka}: {beklenen} kampanya bitiyor ama bölüm yok"
                baslik = next(b for b in basliklar if "Yakında biten" in b)
                assert f"({beklenen})" in baslik, f"{banka}: sayı tutmuyor -> {baslik}"

    def test_gecmis_tarihli_kampanya_yakinda_bitenlere_girmez(self, kayitlar) -> None:
        """«Kalan gün» negatifse kampanya bitmiştir; «yakında bitiyor» değildir."""
        gecmisi_olan = [
            k for k in kayitlar
            if (kalan := _gun_kaldi(k.kampanya_bitis)) is not None and kalan < 0
        ]
        if not gecmisi_olan:
            pytest.skip("veritabanında süresi geçmiş kayıt yok")

        banka = gecmisi_olan[0].banka_adi
        at = _kos(banka)
        beklenen = sum(
            1 for k in kayitlar
            if k.banka_adi == banka
            and (kalan := _gun_kaldi(k.kampanya_bitis)) is not None
            and 0 <= kalan <= 7
        )
        baslik = [str(s.value) for s in at.subheader if "Yakında biten" in str(s.value)]
        if beklenen:
            assert f"({beklenen})" in baslik[0]
        else:
            assert not baslik


class TestTazelik:
    def test_bayat_veri_uyari_uretir(self, kayitlar) -> None:
        """Tazelik bankadan bankaya değişiyor; eşit tazelikte göstermek yanıltır."""
        def _gun(banka: str) -> int:
            tarihler = [k.cekim_tarihi for k in kayitlar if k.banka_adi == banka and k.cekim_tarihi]
            en_yeni = max(tarihler)
            if isinstance(en_yeni, datetime):
                en_yeni = en_yeni.date()
            return (date.today() - en_yeni).days

        bankalar = sorted({k.banka_adi for k in kayitlar})
        bayatlar = [b for b in bankalar if _gun(b) > 3]
        tazeler = [b for b in bankalar if _gun(b) <= 3]

        for banka in bayatlar:
            at = _kos(banka)
            metinler = " ".join(str(w.value) for w in at.warning)
            assert "gün önce çekildi" in metinler, (
                f"{banka} verisi {_gun(banka)} günlük ama uyarı yok"
            )

        for banka in tazeler:
            at = _kos(banka)
            metinler = " ".join(str(w.value) for w in at.warning)
            assert "gün önce çekildi" not in metinler, (
                f"{banka} verisi taze ({_gun(banka)} gün) ama bayat uyarısı çıkmış"
            )

    def test_esik_gun_farkiyla_hesaplanir(self) -> None:
        """Eşik sabit bir tarihe değil, BUGÜNE göre çalışmalı.

        Sabit tarihe bağlansaydı sayfa yarın yanlış sayı gösterirdi.
        """
        yarin = (date.today() + timedelta(days=1)).isoformat()
        uzak = (date.today() + timedelta(days=40)).isoformat()
        gecmis = (date.today() - timedelta(days=5)).isoformat()

        assert _gun_kaldi(yarin) == 1
        assert _gun_kaldi(uzak) == 40
        assert _gun_kaldi(gecmis) == -5
        assert _gun_kaldi(None) is None
        assert _gun_kaldi("gecersiz-tarih") is None
