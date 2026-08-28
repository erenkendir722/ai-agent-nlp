"""Lisans raporu üretecinin testleri (şartname 5.10).

Bu raporun tek işi bir iddiayı KANITLAMAK: "kısıtlı lisanslı bileşen yok."
Sessizce yanlış bir rapor, hiç rapor olmamasından kötüdür — jüri ona bakarak
puanlıyor. Testler üç kırılganlığı tutar:

  * model lisansı beklenenden farklı çıkarsa rapor bunu YUTMAMALI,
  * teyit hiç yapılmadıysa rapor "teyit edildi" DEMEMELİ,
  * `requirements.txt` kapanışı ile ortamda kalmış paketler karışmamalı.
"""

from __future__ import annotations

from eval import lisanslar


def _kanit(bulunan: str = "apache-2.0", *, durum: int = 200, hata: str | None = None) -> dict:
    return {
        "teyit_tarihi": "2026-08-24T23:00:00+03:00",
        "yontem": "test",
        "modeller": [
            {
                "depo": "Qwen/Qwen3.5-122B-A10B",
                "kaynak": "https://huggingface.co/api/models/Qwen/Qwen3.5-122B-A10B",
                "beklenen": "apache-2.0",
                "bulunan": bulunan,
                "durum": durum,
                "hata": hata,
                "son_degisiklik": None,
            }
        ],
    }


class TestModelTeyidi:
    def test_beklenen_lisans_tutuyorsa_sorun_yok(self) -> None:
        assert lisanslar.model_sorunlari(_kanit()) == []

    def test_lisans_degismisse_sorun_bildirilir(self) -> None:
        sorunlar = lisanslar.model_sorunlari(_kanit("cc-by-nc-4.0"))
        assert len(sorunlar) == 1
        assert "BEKLENEN apache-2.0" in sorunlar[0]

    def test_teyit_edilemediyse_sorun_bildirilir(self) -> None:
        sorunlar = lisanslar.model_sorunlari(_kanit(durum=404, hata=None))
        assert "teyit edilemedi" in sorunlar[0]

    def test_hic_teyit_yoksa_rapor_teyit_edildi_demez(self) -> None:
        metin = "\n".join(lisanslar._model_bolumu(None))
        assert "teyit edilmedi" in metin
        assert "HF API" not in metin

    def test_teyit_varsa_kaynak_ve_tarih_yazilir(self) -> None:
        metin = "\n".join(lisanslar._model_bolumu(_kanit()))
        assert "2026-08-24" in metin
        assert "model-lisanslari.json" in metin

    def test_yasakli_aileler_listede_kalir(self) -> None:
        assert "Llama" in lisanslar.YASAKLI_IZLER
        assert "Gemma" in lisanslar.YASAKLI_IZLER

    def test_kullanilan_modellerin_hepsi_izin_verici_bekliyor(self) -> None:
        for model in lisanslar.MODELLER:
            assert model["beklenen"] in {"apache-2.0", "mit"}
            assert not any(
                iz.lower() in model["depo"].lower() for iz in lisanslar.YASAKLI_IZLER
            )


class TestBagimlilikKapanisi:
    def test_gereksinim_satiri_ekleriyle_ayristirilir(self) -> None:
        assert lisanslar._gereksinim_ayristir("lxml[html_clean]>=5.2") == [
            ("lxml", "html-clean")
        ]
        assert lisanslar._gereksinim_ayristir("httpx==0.27.2") == [("httpx", None)]
        assert lisanslar._gereksinim_ayristir("   ") == []

    def test_kapanis_requirements_koklerini_icerir(self) -> None:
        kapanis = lisanslar.proje_bagimliliklari()
        assert {"streamlit", "httpx", "pydantic"} <= kapanis

    def test_kurulum_araci_proje_bagimliligi_sayilmaz(self) -> None:
        """`pip` ortamda hep vardır; teslim edilen kodun bağımlılığı değildir."""
        assert "pip" not in lisanslar.proje_bagimliliklari()
