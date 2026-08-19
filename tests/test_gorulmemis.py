"""Görülmemiş metin ölçüm takımı (jürinin 19 Ağustos cevabı).

Jüri «o anda kendisi de test verisi verebilir» dedi. Bu ölçüm, altın setin
cevaplamadığı soruyu cevaplar: *hiç görülmemiş bir metinde sistem kendi
sözleşmesine uyuyor mu?*

Buradaki testler ölçüm ARACINI korur — aracın kendisi test edilmeden
ölçüme güvenilmez (aynı ders `tools/hava_boslugu.py`'de `/dev/tcp` ile
öğrenilmişti).
"""

from __future__ import annotations

from pathlib import Path

from eval import gorulmemis as gm


class TestGorulmemisSecimi:
    def test_korpustaki_sayfalar_dislanir(self, tmp_path: Path) -> None:
        """`.json` üst verisi olan sayfa korpustadır, görülmemiş sayılmaz."""
        banka = tmp_path / "0203"
        banka.mkdir()
        (banka / "a.html").write_text("<html>korpusta</html>", encoding="utf-8")
        (banka / "a.json").write_text("{}", encoding="utf-8")
        (banka / "b.html").write_text("<html>gorulmemis</html>", encoding="utf-8")

        secilen = {p.stem for p in gm.gorulmemis_sayfalar(tmp_path)}
        assert secilen == {"b"}

    def test_bos_dizin_hata_uretmez(self, tmp_path: Path) -> None:
        assert gm.gorulmemis_sayfalar(tmp_path) == []


class TestCakismaSemantigi:
    """Ham çakışma bir TEŞHİS, çözülmemiş çakışma bir İHLAL.

    İkisini tek sayaçta toplamak teşhisi ihlal gibi gösterirdi — ilk sürümde
    tam olarak bu oldu ve rapor 124 çakışmayı ❌ ile basıyordu.
    """

    JURI_METNI = (
        "Emeklilere özel: 36 ay vadeli ihtiyaç finansmanında aylık kâr payı oranı "
        "%2,45'ten başlıyor. Tahsis ücreti %0,75."
    )

    def test_ham_cakisma_saptanir(self) -> None:
        ham, _ = gm._span_cakismasi(self.JURI_METNI)
        assert ham > 0, "bilinen çakışmalı metinde ham çakışma saptanmadı"

    def test_cakisma_cozulur(self) -> None:
        """Tek atama sonrası hiçbir span iki alana ait kalmamalı."""
        _, cozulmemis = gm._span_cakismasi(self.JURI_METNI)
        assert cozulmemis == 0

    def test_cakismasiz_metin_sifir_verir(self) -> None:
        ham, cozulmemis = gm._span_cakismasi("Vade 36 aydır.")
        assert cozulmemis == 0
        assert ham == 0


class TestRapor:
    def _olcum(self, **degisiklik: object) -> dict:
        taban = {
            "sayfa": 187, "islenen": 187, "atlanan": 0, "coken": 0,
            "banka_sayisi": 4, "toplam_alan": 2992, "dolu_alan": 245,
            "alan_dolulugu": 0.082, "kanit_ihlali": 0, "kanit_ihlali_orani": 0.0,
            "kanit_ihlali_ornekleri": [], "boyut_ihlali": 0,
            "cakisma_ham": 124, "cakisma_cozulmemis": 0,
            "alan_sayaci": {"vade_ay_max": 60}, "llm_kullanildi": False,
        }
        return {**taban, **degisiklik}

    def test_temiz_kosu_hepsi_yesil(self) -> None:
        metin = gm.rapor_yaz(self._olcum())
        assert "❌" not in metin

    def test_ham_cakisma_ihlal_olarak_gosterilmez(self) -> None:
        """REGRESYON — 124 çözülen çakışma ❌ ile basılıyordu."""
        metin = gm.rapor_yaz(self._olcum())
        assert "124" in metin
        assert "Teşhis (ihlal değil)" in metin

    def test_gercek_ihlal_isaretlenir(self) -> None:
        metin = gm.rapor_yaz(self._olcum(cakisma_cozulmemis=3, coken=2))
        assert "❌" in metin

    def test_dogruluk_olcmedigi_yazili(self) -> None:
        """Dürüst sınır raporun içinde durmalı; okuyan yanlış çıkarım yapmasın."""
        metin = gm.rapor_yaz(self._olcum())
        assert "DOĞRULUK ölçmez" in metin
        assert "altın set" in metin
