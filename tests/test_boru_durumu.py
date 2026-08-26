"""«Canlı Boru Hattı» durum biriktiricileri — olay → ekranda görünen sayı.

Animasyonun her sayısı bu işlevlerden geçiyor; burada bir hata olursa sayfa
GERÇEK olmayan bir şey gösterir. Sayfanın tek yasağı bu olduğu için sayaçlar,
kart aşamaları ve kapanış davranışı ayrı ayrı sınanır.

Saf işlevler: Streamlit, tarayıcı ve ağ gerekmez.
"""

from __future__ import annotations

from app.boru_durumu import (
    AZAMI_GUNLUK_GECMISI,
    CikarimDurumu,
    ToplamaDurumu,
    acik_kartlari_kapat,
    cikarim_olaylarini_isle,
    toplama_olaylarini_isle,
)
from src.boru_hatti import CikarimIlerlemesi
from src.collector.temel_kaziyici import Ilerleme


def _toplama(asama: str, **ayrinti) -> Ilerleme:
    ayrinti.setdefault("banka_kodu", "0203")
    ayrinti.setdefault("banka_adi", "Albaraka")
    return Ilerleme(asama=asama, **ayrinti)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Toplama
# ---------------------------------------------------------------------------


class TestToplamaDurumu:
    def test_url_kesfi_toplami_biriktirir(self) -> None:
        durum = ToplamaDurumu()
        toplama_olaylarini_isle(
            durum,
            [
                _toplama("url_kesfi", mesaj="liste taranıyor"),
                _toplama("url_kesfi", toplam=14, mesaj="14 kampanya bağlantısı"),
                _toplama("url_kesfi", banka_kodu="0205", banka_adi="Kuveyt", toplam=6),
            ],
        )
        assert durum.kesfedilen == 20
        assert durum.bankalar["0203"].toplam == 14
        # 0205'ten olay gelince 0203 kapandı: toplama sırayla ilerliyor.
        assert durum.bankalar["0203"].asama == "bitti"
        assert durum.bankalar["0205"].asama == "taraniyor"

    def test_sayfa_olayi_sayaci_ve_urlleri_isler(self) -> None:
        durum = ToplamaDurumu()
        toplama_olaylarini_isle(
            durum,
            [
                _toplama("sayfa", sira=1, toplam=3, url="https://a/1"),
                _toplama("sayfa", sira=2, toplam=3, url="https://a/2"),
            ],
        )
        assert durum.sayfa == 2
        assert durum.urller == ["https://a/1", "https://a/2"]
        assert durum.aktif_url == "https://a/2"
        assert durum.bankalar["0203"].sayfa == 2

    def test_robots_reddi_ayri_sayilir(self) -> None:
        """robots reddi kusur değil, jüriye gösterilecek etik kanıtı — ayrı sayaç."""
        durum = ToplamaDurumu()
        toplama_olaylarini_isle(
            durum,
            [
                _toplama("atlandi", url="https://a/1", mesaj="robots.txt reddetti"),
                _toplama("atlandi", url="https://a/2", mesaj="gövde 0 karakter"),
                _toplama("atlandi", url="https://a/3", mesaj="robots.txt reddetti"),
            ],
        )
        assert durum.atlanan == 3
        assert durum.robots_reddi == 2
        assert durum.atlama_sebepleri["robots.txt reddetti"] == 2
        assert durum.atlama_sebepleri["gövde 0 karakter"] == 1

    def test_atlanan_sayfa_sayilmaz(self) -> None:
        """Atlanan URL çekilmedi — «toplanan sayfa» sayacına girmemeli."""
        durum = ToplamaDurumu()
        toplama_olaylarini_isle(
            durum, [_toplama("atlandi", url="https://a/1", mesaj="gövde 0 karakter")]
        )
        assert durum.sayfa == 0

    def test_hata_karti_kirmiziya_doner(self) -> None:
        durum = ToplamaDurumu()
        toplama_olaylarini_isle(durum, [_toplama("hata", mesaj="TimeoutException")])
        assert durum.hata == 1
        assert durum.bankalar["0203"].asama == "hata"

    def test_bitti_olayi_karti_kapatir(self) -> None:
        durum = ToplamaDurumu()
        toplama_olaylarini_isle(
            durum,
            [
                _toplama("sayfa", url="https://a/1", toplam=3),
                _toplama("bitti", sira=1, toplam=3, mesaj="Albaraka: 1/3 kayıt"),
            ],
        )
        assert durum.bankalar["0203"].asama == "bitti"

    def test_bilinmeyen_asama_yok_sayilir(self) -> None:
        """Kazıyıcıya yeni aşama eklenirse arayüz kırılmamalı."""
        durum = ToplamaDurumu()
        toplama_olaylarini_isle(durum, [_toplama("gelecekteki_asama")])  # type: ignore[arg-type]
        assert durum.bankalar == {}
        assert durum.olaylar == []

    def test_gunluk_gecmisi_sinirlanir(self) -> None:
        durum = ToplamaDurumu()
        toplama_olaylarini_isle(
            durum, [_toplama("sayfa", url=f"https://a/{i}") for i in range(300)]
        )
        assert len(durum.olaylar) == AZAMI_GUNLUK_GECMISI
        assert durum.sayfa == 300  # sayaç kırpılmaz, yalnız günlük kırpılır


class TestAktifBanka:
    """Nabız yalnız üzerinde işlem yapılan kartta atmalı."""

    def test_yalniz_son_banka_aktiftir(self) -> None:
        durum = ToplamaDurumu()
        toplama_olaylarini_isle(
            durum,
            [
                _toplama("url_kesfi", toplam=5),
                _toplama("sayfa", url="https://a/1"),
                _toplama("url_kesfi", banka_kodu="0205", banka_adi="Kuveyt", toplam=3),
                _toplama("sayfa", banka_kodu="0205", banka_adi="Kuveyt", url="https://b/1"),
            ],
        )
        assert durum.aktif_banka == "0205"
        assert [k for k, v in durum.bankalar.items() if v.aktif] == ["0205"]

    def test_devredilen_banka_kapanir_ama_sayfasi_korunur(self) -> None:
        """Demo tavanıyla kesilen banka «bitti» olayı üretmez — devirde kapanır."""
        durum = ToplamaDurumu()
        toplama_olaylarini_isle(
            durum,
            [
                _toplama("sayfa", url="https://a/1", toplam=14),
                _toplama("sayfa", url="https://a/2", toplam=14),
                _toplama("url_kesfi", banka_kodu="0205", banka_adi="Kuveyt", toplam=3),
            ],
        )
        onceki = durum.bankalar["0203"]
        assert onceki.asama == "bitti"
        assert onceki.aktif is False
        assert onceki.sayfa == 2  # ölçülen sayfa sayısı DEĞİŞMEZ
        assert onceki.toplam == 14

    def test_hatali_banka_devirde_bitti_gosterilmez(self) -> None:
        durum = ToplamaDurumu()
        toplama_olaylarini_isle(
            durum,
            [
                _toplama("hata", mesaj="TimeoutException"),
                _toplama("sayfa", banka_kodu="0205", banka_adi="Kuveyt", url="https://b/1"),
            ],
        )
        assert durum.bankalar["0203"].asama == "hata"
        assert durum.bankalar["0203"].aktif is False

    def test_kapatma_tum_nabizlari_durdurur(self) -> None:
        durum = ToplamaDurumu()
        toplama_olaylarini_isle(durum, [_toplama("sayfa", url="https://a/1")])
        acik_kartlari_kapat(durum, iptal=False)
        assert not any(k.aktif for k in durum.bankalar.values())
        assert durum.aktif_banka == ""


class TestAcikKartlariKapat:
    def test_demo_tavani_kartini_kapatir(self) -> None:
        """Tavanla kesilen banka «bitti» olayı üretmez — kart yeşil nabızda kalırdı."""
        durum = ToplamaDurumu()
        toplama_olaylarini_isle(
            durum,
            [
                _toplama("url_kesfi", toplam=14),
                _toplama("sayfa", url="https://a/1", toplam=14),
                _toplama("sayfa", url="https://a/2", toplam=14),
            ],
        )
        assert durum.bankalar["0203"].asama == "taraniyor"

        acik_kartlari_kapat(durum, iptal=False)
        kart = durum.bankalar["0203"]
        assert kart.asama == "bitti"
        assert kart.sayfa == 2  # ölçülen sayfa sayısı DEĞİŞMEZ
        assert kart.toplam == 14

    def test_iptal_edilen_kosu_karta_yazilir(self) -> None:
        durum = ToplamaDurumu()
        toplama_olaylarini_isle(durum, [_toplama("sayfa", url="https://a/1")])
        acik_kartlari_kapat(durum, iptal=True)
        assert durum.bankalar["0203"].mesaj == "iptal edildi"

    def test_hata_karti_kapatilmaz(self) -> None:
        """Hatalı banka «bitti» gösterilmemeli — hata gizlenmez."""
        durum = ToplamaDurumu()
        toplama_olaylarini_isle(durum, [_toplama("hata", mesaj="TimeoutException")])
        acik_kartlari_kapat(durum, iptal=False)
        assert durum.bankalar["0203"].asama == "hata"

    def test_hic_baslamamis_banka_bekliyor_kalir(self) -> None:
        durum = ToplamaDurumu()
        acik_kartlari_kapat(durum, iptal=True)
        assert durum.bankalar == {}


# ---------------------------------------------------------------------------
# Çıkarım
# ---------------------------------------------------------------------------


class TestCikarimDurumu:
    def test_sayaclar_ve_olculen_sure_birikir(self) -> None:
        durum = CikarimDurumu()
        cikarim_olaylarini_isle(
            durum,
            [
                CikarimIlerlemesi(asama="basladi", toplam=3, mesaj="hibrit · 16 işçi"),
                CikarimIlerlemesi(
                    asama="kayit", sira=1, toplam=3, banka_adi="Albaraka Türk Katılım Bankası A.Ş.",
                    doluluk=0.4, guven=0.8, sure=2.0,
                ),
                CikarimIlerlemesi(
                    asama="kayit", sira=2, toplam=3, banka_adi="Kuveyt Türk Katılım Bankası A.Ş.",
                    doluluk=0.2, guven=0.6, sure=1.0,
                ),
            ],
        )
        assert durum.toplam == 3
        assert durum.islenen == 2
        assert durum.sure_toplami == 3.0
        assert [k.banka for k in durum.kayitlar] == ["Albaraka Türk", "Kuveyt Türk"]
        assert durum.kayitlar[0].doluluk == 0.4

    def test_katman_sayaclari_kosu_sirasinda_dolar(self) -> None:
        """Çubuklar koşu BİTİNCE değil, her kayıtta güncellenmeli."""
        durum = CikarimDurumu()
        cikarim_olaylarini_isle(
            durum,
            [CikarimIlerlemesi(asama="kayit", sira=1, kural=3, llm=5, hibrit=2)],
        )
        assert (durum.kural, durum.llm, durum.hibrit) == (3, 5, 2)

        cikarim_olaylarini_isle(
            durum,
            [CikarimIlerlemesi(asama="kayit", sira=2, kural=7, llm=9, hibrit=4)],
        )
        # Olay KOŞAN TOPLAMI taşıyor — ikinci kez toplanırsa sayı ikiye katlanır.
        assert (durum.kural, durum.llm, durum.hibrit) == (7, 9, 4)

    def test_ara_kayit_yazilan_sayisini_gunceller(self) -> None:
        durum = CikarimDurumu()
        cikarim_olaylarini_isle(
            durum,
            [CikarimIlerlemesi(asama="ara_kayit", sira=10, mesaj="10 kayıt yazıldı")],
        )
        assert durum.yazilan == 10

    def test_hata_olayi_sessizce_yutulmaz(self) -> None:
        durum = CikarimDurumu()
        cikarim_olaylarini_isle(
            durum, [CikarimIlerlemesi(asama="hata", mesaj="ValueError: patladı")]
        )
        assert durum.hatali == 1
        assert "patladı" in durum.olaylar[-1].metin
        assert durum.islenen == 0  # düşen kayıt «işlendi» sayılmaz

    def test_bilinmeyen_asama_yok_sayilir(self) -> None:
        durum = CikarimDurumu()
        cikarim_olaylarini_isle(durum, [CikarimIlerlemesi(asama="gelecek")])  # type: ignore[arg-type]
        assert durum.olaylar == []
        assert durum.islenen == 0

    def test_bos_olay_listesi_kirilmaz(self) -> None:
        durum = CikarimDurumu()
        cikarim_olaylarini_isle(durum, [])
        assert durum.islenen == 0
