"""Altın set araçlarının testleri (H-01 / H-02).

Bu araç cevap anahtarını üretiyor; buradaki bir hata tüm doğruluk metriklerini
sessizce bozar. En çok test edilen şey bu yüzden hücre çözümlemesi: boş hücre
ile '?' hücresinin farkı, ölçüme girip girmemeyi belirliyor.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import pytest

from src.schema import Alan, Kampanya
from tools import altin_set


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------


def _kampanya(kod: str, sira: int, tur: str = "finansman", metin: str = "kampanya metni") -> Kampanya:
    url = f"https://ornek.test/{kod}/{sira}"
    return Kampanya(
        banka_adi=f"Banka {kod}",
        banka_kodu=kod,
        kampanya_id=Kampanya.kimlik_uret(kod, url),
        kaynak_url=url,
        cekim_tarihi=datetime(2026, 8, 9, 12, 0),
        kampanya_turu=Alan(deger=tur, guven=0.9, yontem="llm"),
        ham_metin=metin,
    )


@pytest.fixture
def gold_dizini(tmp_path, monkeypatch):
    """Araç modülünü geçici bir data/gold dizinine yönlendirir.

    Modüldeki yol sabitleri içe aktarma anında `GOLD`'dan türetiliyor; yalnız
    `GOLD`'u yamalamak yetmez, ondan türeyen HER sabit ayrı ayrı yamalanmalıdır.
    `KALIBRASYON_KAYDI` bir süre listede yoktu ve `make test` her koşuşta gerçek
    `data/gold/kalibrasyon_listesi.json` dosyasını yeniden yazıyordu. O dosya
    kalibrasyon bloğunun köken kaydıdır (tohum + oluşturma zamanı); jüriye
    "bu 10 örneği nasıl seçtiniz?" sorusunun cevabı odur. Test koşusunun onu
    ezmesi, ölçümün kanıtını sessizce yok eder.
    """
    gercek_gold = altin_set.GOLD
    gold = tmp_path / "gold"
    gold.mkdir()
    monkeypatch.setattr(altin_set, "GOLD", gold)
    monkeypatch.setattr(altin_set, "METINLER", gold / "metinler")
    monkeypatch.setattr(altin_set, "ALTIN_SET", gold / "altin_set.jsonl")
    monkeypatch.setattr(altin_set, "ORNEK_KAYDI", gold / "ornek_listesi.json")
    monkeypatch.setattr(altin_set, "KALIBRASYON_KAYDI", gold / "kalibrasyon_listesi.json")

    # Bekçi: yamalamayı unutulan bir sabit kalırsa test gerçek veriye yazar.
    # Tek tek hatırlamak yerine burada kontrol ediyoruz — bundan sonra
    # eklenecek her yeni yol sabiti de kendiliğinden yakalanır.
    kacaklar = [
        ad
        for ad, deger in vars(altin_set).items()
        if isinstance(deger, Path) and deger.is_relative_to(gercek_gold)
    ]
    assert not kacaklar, (
        f"Bu yol sabitleri gerçek data/gold'u gösteriyor: {kacaklar}. "
        "gold_dizini fixture'ında yamalayın, yoksa testler gerçek veriyi ezer."
    )
    return gold


def _csv_doldur(yol, satirlar: list[dict[str, str]]) -> None:
    """Var olan etiketleme CSV'sini verilen değerlerle doldurur."""
    with yol.open(encoding="utf-8-sig", newline="") as dosya:
        mevcut = list(csv.DictReader(dosya))
    with yol.open("w", encoding="utf-8-sig", newline="") as dosya:
        yazici = csv.DictWriter(dosya, fieldnames=altin_set.csv_basliklari())
        yazici.writeheader()
        for satir, degerler in zip(mevcut, satirlar, strict=False):
            satir.update(degerler)
            yazici.writerow(satir)


# ---------------------------------------------------------------------------
# Hücre çözümleme — boş / '?' / değer ayrımı
# ---------------------------------------------------------------------------


def test_bos_hucre_belirtilmemis_olarak_sete_girer():
    """Boş hücre bir iddiadır: 'bu alan metinde yok'. Metriğe girmeli."""
    yazilsin, deger = altin_set._hucre_cozumle("kar_payi_orani", "")
    assert yazilsin is True
    assert deger is None


def test_soru_isareti_alani_olcumun_disinda_birakir():
    yazilsin, deger = altin_set._hucre_cozumle("kar_payi_orani", "?")
    assert yazilsin is False
    assert deger is None


def test_turkce_ondalik_virgul_floata_cevrilir():
    _, deger = altin_set._hucre_cozumle("kar_payi_orani", "1,89")
    assert deger == pytest.approx(1.89)


def test_binlik_ayirici_cozulur():
    _, deger = altin_set._hucre_cozumle("finansman_tutari_max", "1.000.000")
    assert deger == pytest.approx(1_000_000)


@pytest.mark.parametrize("ham", ["evet", "EVET", "true", "1", "var"])
def test_masrafsiz_evet_varyantlari(ham):
    _, deger = altin_set._hucre_cozumle("masrafsiz_mi", ham)
    assert deger is True


def test_masrafsiz_hayir():
    _, deger = altin_set._hucre_cozumle("masrafsiz_mi", "hayır")
    assert deger is False


def test_iso_tarih_korunur():
    _, deger = altin_set._hucre_cozumle("kampanya_bitis", "2026-10-31")
    assert deger == "2026-10-31"


def test_turkce_tarih_isoya_cevrilir():
    _, deger = altin_set._hucre_cozumle("kampanya_bitis", "31 Ekim 2026")
    assert deger == "2026-10-31"


def test_serbest_metin_oldugu_gibi_kalir():
    _, deger = altin_set._hucre_cozumle("kampanya_avantaji", "  Avantajlı kâr payı  ")
    assert deger == "Avantajlı kâr payı"


# ---------------------------------------------------------------------------
# Örnekleme
# ---------------------------------------------------------------------------


def test_ornekleme_bankalari_dengeler():
    kampanyalar = [_kampanya(f"02{i:02d}", s) for i in range(4) for s in range(10)]
    secilen = altin_set.katmanli_ornekle(kampanyalar, 20)

    assert len(secilen) == 20
    dagilim = {}
    for k in secilen:
        dagilim[k.banka_kodu] = dagilim.get(k.banka_kodu, 0) + 1
    assert max(dagilim.values()) - min(dagilim.values()) <= 1


def test_ornekleme_nadir_turu_atlamaz():
    kampanyalar = [_kampanya("0203", s, tur="diger") for s in range(30)]
    kampanyalar.append(_kampanya("0203", 99, tur="tasit_finansmani"))
    secilen = altin_set.katmanli_ornekle(kampanyalar, 5)

    turler = {altin_set._tur(k) for k in secilen}
    assert "tasit_finansmani" in turler, "nadir tür örneklemin dışında kaldı"


def test_ornekleme_ayni_tohumla_ayni_sonucu_verir():
    kampanyalar = [_kampanya(f"02{i:02d}", s) for i in range(3) for s in range(8)]
    birinci = [k.kampanya_id for k in altin_set.katmanli_ornekle(kampanyalar, 10)]
    ikinci = [k.kampanya_id for k in altin_set.katmanli_ornekle(kampanyalar, 10)]
    assert birinci == ikinci


def test_ornekleme_istenenden_fazla_secmez():
    kampanyalar = [_kampanya("0203", s) for s in range(5)]
    assert len(altin_set.katmanli_ornekle(kampanyalar, 3)) == 3


# ---------------------------------------------------------------------------
# Çalışma sayfaları
# ---------------------------------------------------------------------------


def test_calisma_sayfalari_uyum_blogu_ve_kisisel_pay_uretir(gold_dizini):
    kampanyalar = [_kampanya(f"02{i:02d}", s) for i in range(4) for s in range(6)]
    secilen = altin_set.katmanli_ornekle(kampanyalar, 18)
    uyum_blogu, sayilar, _ = altin_set.calisma_sayfalari_yaz(secilen, altin_set.KISILER)

    assert len(uyum_blogu) == altin_set.UYUM_ADET
    assert sum(sayilar.values()) == 18 - altin_set.UYUM_ADET

    for kisi in altin_set.KISILER:
        assert (gold_dizini / f"etiketleme_{kisi.lower()}.csv").exists()
        assert (gold_dizini / f"etiketleme_uyum_{kisi.lower()}.csv").exists()


def test_uyum_blogu_herkeste_ayni(gold_dizini):
    kampanyalar = [_kampanya(f"02{i:02d}", s) for i in range(4) for s in range(6)]
    secilen = altin_set.katmanli_ornekle(kampanyalar, 18)
    altin_set.calisma_sayfalari_yaz(secilen, altin_set.KISILER)

    listeler = []
    for kisi in altin_set.KISILER:
        satirlar = altin_set._csv_oku(gold_dizini / f"etiketleme_uyum_{kisi.lower()}.csv")
        listeler.append([kimlik for _, kimlik, _, _ in satirlar])
    assert all(liste == listeler[0] for liste in listeler)


def test_kisisel_paylar_ortusmez(gold_dizini):
    kampanyalar = [_kampanya(f"02{i:02d}", s) for i in range(4) for s in range(6)]
    secilen = altin_set.katmanli_ornekle(kampanyalar, 18)
    altin_set.calisma_sayfalari_yaz(secilen, altin_set.KISILER)

    gorulen: set[str] = set()
    for kisi in altin_set.KISILER:
        for _, kimlik, _, _ in altin_set._csv_oku(gold_dizini / f"etiketleme_{kisi.lower()}.csv"):
            assert kimlik not in gorulen, f"{kimlik} birden fazla kişiye verilmiş"
            gorulen.add(kimlik)


def test_uzun_metin_kirpilir_ama_tam_metin_diske_yazilir(gold_dizini):
    uzun = "x" * (altin_set.METIN_KIRPMA + 5000)
    kampanyalar = [_kampanya("0203", s, metin=uzun) for s in range(12)]
    secilen = altin_set.katmanli_ornekle(kampanyalar, 12)
    altin_set.calisma_sayfalari_yaz(secilen, altin_set.KISILER)

    metin_dosyasi = gold_dizini / "metinler" / f"{secilen[0].kampanya_id}.txt"
    assert metin_dosyasi.read_text(encoding="utf-8") == uzun

    with (gold_dizini / "etiketleme_uyum_eren.csv").open(encoding="utf-8-sig") as dosya:
        satir = next(csv.DictReader(dosya))
    assert len(satir["metin"]) < len(uzun)
    assert "kırpıldı" in satir["metin"]


# ---------------------------------------------------------------------------
# Derleme
# ---------------------------------------------------------------------------


def _hazirla(gold_dizini, adet: int = 14):
    kampanyalar = [_kampanya(f"02{i:02d}", s) for i in range(4) for s in range(6)]
    secilen = altin_set.katmanli_ornekle(kampanyalar, adet)
    altin_set.calisma_sayfalari_yaz(secilen, altin_set.KISILER)
    return kampanyalar, secilen


def test_derleme_kisisel_etiketleri_toplar(gold_dizini):
    _hazirla(gold_dizini)
    _csv_doldur(
        gold_dizini / "etiketleme_eren.csv",
        [{"kampanya_turu": "finansman", "kar_payi_orani": "2,05"}],
    )

    kayitlar, _ = altin_set.derle()
    eren = [k for k in kayitlar if k.get("etiketleyen") == "Eren"]
    assert eren and eren[0]["kar_payi_orani"] == pytest.approx(2.05)


def test_derleme_dokunulmamis_satiri_atlar(gold_dizini):
    """Açılmamış bir CSV, baştan sona 'Belirtilmemiş' dolu bir cevap anahtarına
    dönüşmemeli — bu, metriği sessizce çöpe çevirirdi."""
    _hazirla(gold_dizini)
    kayitlar, uyarilar = altin_set.derle()
    assert kayitlar == []
    assert any("etiketlenmemiş" in u for u in uyarilar)


def test_derleme_bos_birakilan_alani_belirtilmemis_sayar(gold_dizini):
    """Satıra dokunulduysa, boş hücreler gerçek bir 'yok' iddiasıdır."""
    _hazirla(gold_dizini)
    _csv_doldur(gold_dizini / "etiketleme_eren.csv", [{"kampanya_turu": "diger"}])

    kayitlar, _ = altin_set.derle()
    eren = [k for k in kayitlar if k.get("etiketleyen") == "Eren"]
    assert eren[0]["kampanya_turu"] == "diger"
    assert eren[0]["kar_payi_orani"] is None


def test_uzlasi_cogunluk_oyunu_alir(gold_dizini):
    _hazirla(gold_dizini)
    for kisi, deger in [("eren", "1,89"), ("samet", "1,89"), ("görkem", "1,89"), ("esra", "2,45")]:
        _csv_doldur(
            gold_dizini / f"etiketleme_uyum_{kisi}.csv",
            [{"kampanya_turu": "finansman", "kar_payi_orani": deger}],
        )

    kayitlar, notlar = altin_set.uyum_uzlasisi()
    assert kayitlar[0]["kar_payi_orani"] == pytest.approx(1.89)
    assert not notlar


def test_uzlasi_esitlikte_alani_sete_almaz(gold_dizini):
    """2-2 bölünmüş bir alan cevap anahtarına yazı-turayla girmemeli."""
    _hazirla(gold_dizini)
    for kisi, deger in [("eren", "1,89"), ("samet", "1,89"), ("görkem", "2,45"), ("esra", "2,45")]:
        _csv_doldur(
            gold_dizini / f"etiketleme_uyum_{kisi}.csv",
            [{"kampanya_turu": "finansman", "kar_payi_orani": deger}],
        )

    kayitlar, notlar = altin_set.uyum_uzlasisi()
    assert all("kar_payi_orani" not in k for k in kayitlar)
    assert any("çoğunluk yok" in n for n in notlar)


def test_uzlasi_kaydi_kisisel_kaydin_onune_gecer(gold_dizini):
    """Aynı kampanya hem uyum bloğunda hem kişisel payda ise tek kez girmeli."""
    _hazirla(gold_dizini)
    for kisi in ("eren", "samet", "görkem", "esra"):
        _csv_doldur(gold_dizini / f"etiketleme_uyum_{kisi}.csv", [{"kampanya_turu": "kart"}])

    kayitlar, _ = altin_set.derle()
    kimlikler = [k["kampanya_id"] for k in kayitlar]
    assert len(kimlikler) == len(set(kimlikler))


# ---------------------------------------------------------------------------
# Uyum ölçümü
# ---------------------------------------------------------------------------


def test_uyum_tam_mutabakatta_bir(gold_dizini):
    _hazirla(gold_dizini)
    for kisi in ("eren", "samet", "görkem", "esra"):
        _csv_doldur(gold_dizini / f"etiketleme_uyum_{kisi}.csv", [{"kampanya_turu": "kart"}])

    sonuc = altin_set.uyum_hesapla()
    assert sonuc["uyum"] == pytest.approx(1.0)
    assert sonuc["ayrisma"] == []


def test_uyum_ayrismayi_raporlar(gold_dizini):
    _hazirla(gold_dizini)
    for kisi, tur in [("eren", "kart"), ("samet", "kart"), ("görkem", "diger"), ("esra", "diger")]:
        _csv_doldur(gold_dizini / f"etiketleme_uyum_{kisi}.csv", [{"kampanya_turu": tur}])

    sonuc = altin_set.uyum_hesapla()
    # 4 kişi -> 6 çift; kart-kart ve diger-diger olmak üzere 2 çift uyuşur
    assert sonuc["uyum"] == pytest.approx(2 / 6)
    assert len(sonuc["ayrisma"]) == 1


def test_ham_uyum_bos_alan_mutabakatiyla_siser(gold_dizini):
    """Dolu-alan oranı ile ham oranın neden ayrıldığını sabitler."""
    _hazirla(gold_dizini)
    for kisi, tur in [("eren", "kart"), ("samet", "kart"), ("görkem", "diger"), ("esra", "diger")]:
        _csv_doldur(gold_dizini / f"etiketleme_uyum_{kisi}.csv", [{"kampanya_turu": tur}])

    sonuc = altin_set.uyum_hesapla()
    assert sonuc["ham_uyum"] > sonuc["uyum"]


def test_uyum_soru_isaretini_oylamaya_katmaz(gold_dizini):
    _hazirla(gold_dizini)
    for kisi, tur in [("eren", "kart"), ("samet", "kart"), ("görkem", "?"), ("esra", "?")]:
        _csv_doldur(gold_dizini / f"etiketleme_uyum_{kisi}.csv", [{"kampanya_turu": tur}])

    sonuc = altin_set.uyum_hesapla()
    # Görkem ve Esra '?' yazdı -> kampanya_turu alanında oylamaya girmezler.
    # Geriye tek karşılaştırılabilir çift kalır: Eren-Samet.
    assert sonuc["kisi_sayisi"] == 4
    assert sonuc["karsilastirilan"] == 1
    assert sonuc["uyum"] == pytest.approx(1.0)


def test_uyum_tek_kisiyle_hesaplanmaz(gold_dizini):
    _hazirla(gold_dizini)
    for kisi in ("samet", "görkem", "esra"):
        (gold_dizini / f"etiketleme_uyum_{kisi}.csv").unlink()
    assert altin_set.uyum_hesapla()["uyum"] is None


# ---------------------------------------------------------------------------
# Denetim
# ---------------------------------------------------------------------------


def test_denetim_bilinmeyen_kampanyayi_yakalar():
    kampanyalar = [_kampanya("0203", 1)]
    hatalar = altin_set.denetle([{"kampanya_id": "yok-123"}], kampanyalar)
    assert any("veritabanında böyle bir kampanya yok" in h for h in hatalar)


def test_denetim_gecersiz_turu_yakalar():
    kampanyalar = [_kampanya("0203", 1)]
    kayit = {"kampanya_id": kampanyalar[0].kampanya_id, "kampanya_turu": "kredi"}
    assert any("geçersiz" in h for h in altin_set.denetle([kayit], kampanyalar))


def test_denetim_sacma_kar_payini_yakalar():
    kampanyalar = [_kampanya("0203", 1)]
    kayit = {"kampanya_id": kampanyalar[0].kampanya_id, "kar_payi_orani": 48.0}
    assert any("şüpheli" in h for h in altin_set.denetle([kayit], kampanyalar))


def test_denetim_sacma_vadeyi_yakalar():
    kampanyalar = [_kampanya("0203", 1)]
    kayit = {"kampanya_id": kampanyalar[0].kampanya_id, "vade_ay_max": 999}
    assert any("şüpheli" in h for h in altin_set.denetle([kayit], kampanyalar))


def test_denetim_temiz_kayda_hata_uretmez():
    kampanyalar = [_kampanya("0203", 1)]
    kayit = {
        "kampanya_id": kampanyalar[0].kampanya_id,
        "kampanya_turu": "konut_finansmani",
        "hedef_kitle": "yeni_musteri",
        "kar_payi_orani": 1.89,
        "vade_ay_max": 120,
        "tahsis_ucreti": None,
    }
    assert altin_set.denetle([kayit], kampanyalar) == []


# ---------------------------------------------------------------------------
# eval ile sözleşme
# ---------------------------------------------------------------------------


def test_uretilen_jsonl_eval_tarafindan_okunabilir(gold_dizini, monkeypatch):
    """Araç ile `eval/calistir.py` arasındaki biçim sözleşmesi.

    Bu test kırılırsa altın set üretilir ama metrik hesaplanmaz — sessiz
    başarısızlık. En pahalı hata tipi bu.
    """
    from eval import calistir as degerlendirme

    kampanyalar, secilen = _hazirla(gold_dizini)
    _csv_doldur(
        gold_dizini / "etiketleme_eren.csv",
        [{"kampanya_turu": "finansman", "kar_payi_orani": "1,89"}],
    )
    kayitlar, _ = altin_set.derle()
    altin_set.jsonl_yaz(kayitlar)

    monkeypatch.setattr(degerlendirme, "ALTIN_SET", gold_dizini / "altin_set.jsonl")
    yuklenen = degerlendirme.altin_seti_yukle()
    assert yuklenen, "eval altın seti okuyamadı"

    sonuc = degerlendirme.altin_set_metrikleri(kampanyalar)
    assert sonuc is not None
    assert sonuc["eslesen_ornek"] >= 1
    assert 0.0 <= sonuc["sayisal_dogruluk"] <= 1.0


# ---------------------------------------------------------------------------
# Üzerine yazma koruması
# ---------------------------------------------------------------------------


def test_doldurulmus_sayfa_tespit_edilir(gold_dizini):
    _hazirla(gold_dizini)
    assert altin_set.doldurulmus_sayfalar() == []

    _csv_doldur(gold_dizini / "etiketleme_eren.csv", [{"kampanya_turu": "kart"}])
    dolu = altin_set.doldurulmus_sayfalar()
    assert len(dolu) == 1
    assert "etiketleme_eren.csv" in dolu[0]


def test_yeniden_ornekleme_dolu_sayfayi_korur(gold_dizini, capsys):
    """Dört kişinin emeği tek komutla silinmemeli; boş sayfalar yenilenebilir."""
    _hazirla(gold_dizini)
    _csv_doldur(gold_dizini / "etiketleme_eren.csv", [{"kampanya_turu": "kart"}])
    onceki = (gold_dizini / "etiketleme_eren.csv").read_text(encoding="utf-8-sig")

    assert altin_set.komut_ornekle(18) == 0
    assert "KORUNAN" in capsys.readouterr().out
    assert (gold_dizini / "etiketleme_eren.csv").read_text(encoding="utf-8-sig") == onceki


def test_zorla_dolu_sayfayi_da_yeniler(gold_dizini):
    _hazirla(gold_dizini)
    _csv_doldur(gold_dizini / "etiketleme_eren.csv", [{"kampanya_turu": "kart"}])

    assert altin_set.komut_ornekle(18, zorla=True) == 0
    assert altin_set.doldurulmus_sayfalar() == []


def test_metin_sutunu_en_sonda(gold_dizini):
    """Etiket sütunları kimlik sütunlarının yanında kalmalı — kayma tuzağı."""
    basliklar = altin_set.csv_basliklari()
    assert basliklar[-1] == "metin"
    assert basliklar.index("kampanya_turu") < basliklar.index("metin")


# ---------------------------------------------------------------------------
# Kanıt denetimi — etiketlenen sayı ham metinde geçiyor mu
# ---------------------------------------------------------------------------


def test_kanit_denetimi_metinde_gecen_sayiyi_onaylar():
    kampanyalar = [_kampanya("0203", 1, metin="aylık %1,89 kâr payı, 120 aya varan vade")]
    kayit = {
        "kampanya_id": kampanyalar[0].kampanya_id,
        "kar_payi_orani": 1.89,
        "vade_ay_max": 120,
    }
    assert altin_set.kanit_uyarilari([kayit], kampanyalar) == []


def test_kanit_denetimi_uydurulmus_sayiyi_yakalar():
    kampanyalar = [_kampanya("0203", 1, metin="avantajlı kâr payı fırsatı")]
    kayit = {"kampanya_id": kampanyalar[0].kampanya_id, "kar_payi_orani": 2.05}
    uyarilar = altin_set.kanit_uyarilari([kayit], kampanyalar)
    assert any("kar_payi_orani=2.05 ham metinde geçmiyor" in u for u in uyarilar)


def test_kanit_denetimi_binlik_ayiraci_taniir():
    kampanyalar = [_kampanya("0203", 1, metin="500.000 TL'ye varan finansman")]
    kayit = {"kampanya_id": kampanyalar[0].kampanya_id, "finansman_tutari_max": 500000}
    assert altin_set.kanit_uyarilari([kayit], kampanyalar) == []


def test_kanit_denetimi_turkce_tarihi_taniir():
    kampanyalar = [_kampanya("0203", 1, metin="Kampanya 31 Ekim 2026 tarihine kadar geçerli")]
    kayit = {"kampanya_id": kampanyalar[0].kampanya_id, "kampanya_bitis": "2026-10-31"}
    assert altin_set.kanit_uyarilari([kayit], kampanyalar) == []


def test_kanit_denetimi_bos_alani_sikayet_etmez():
    kampanyalar = [_kampanya("0203", 1, metin="avantajlı fırsat")]
    kayit = {"kampanya_id": kampanyalar[0].kampanya_id, "kar_payi_orani": None}
    assert altin_set.kanit_uyarilari([kayit], kampanyalar) == []


def test_uyum_tek_etiketleyiciyi_dogru_raporlar(gold_dizini):
    """Bir kişi bitirdiğinde 'hiç etiket yok' denmemeli — emeği yok saymış olur."""
    _hazirla(gold_dizini)
    _csv_doldur(gold_dizini / "etiketleme_uyum_eren.csv", [{"kampanya_turu": "kart"}])

    sonuc = altin_set.uyum_hesapla()
    assert sonuc["uyum"] is None
    assert sonuc["etiketleyenler"] == ["Eren"]
    assert sorted(sonuc["bekleyenler"]) == ["Esra", "Görkem", "Samet"]


# ---------------------------------------------------------------------------
# Kopya tespiti — uyum oranı ancak bağımsız etiketlemede anlamlıdır
# ---------------------------------------------------------------------------


def test_kopya_suphesi_ayni_serbest_metni_yakalar(gold_dizini):
    """Tamamlanmış bir dosya depoya girip kopyalanırsa uyum oranı sahte olur."""
    _hazirla(gold_dizini, adet=18)
    cumleler = [
        {"kampanya_turu": "kart", "kampanya_avantaji": f"Kampanya {i} avantajı",
         "kampanya_kosullari": f"Kampanya {i} koşulu"}
        for i in range(8)
    ]
    for kisi in ("eren", "samet"):
        _csv_doldur(gold_dizini / f"etiketleme_uyum_{kisi}.csv", cumleler)

    uyarilar = altin_set.kopya_suphesi()
    assert any("Eren" in u and "Samet" in u for u in uyarilar)
    assert "BİREBİR" in uyarilar[0]


def test_kopya_suphesi_farkli_ifadelerde_sessiz(gold_dizini):
    _hazirla(gold_dizini, adet=18)
    _csv_doldur(
        gold_dizini / "etiketleme_uyum_eren.csv",
        [{"kampanya_turu": "kart", "kampanya_avantaji": f"Eren cümlesi {i}"} for i in range(8)],
    )
    _csv_doldur(
        gold_dizini / "etiketleme_uyum_samet.csv",
        [{"kampanya_turu": "kart", "kampanya_avantaji": f"Samet cümlesi {i}"} for i in range(8)],
    )
    assert altin_set.kopya_suphesi() == []


def test_kopya_suphesi_az_ornekte_alarm_vermez(gold_dizini):
    """Tek tük eşleşme kopya değildir; eşik altında sessiz kalmalı."""
    _hazirla(gold_dizini, adet=18)
    for kisi in ("eren", "samet"):
        _csv_doldur(
            gold_dizini / f"etiketleme_uyum_{kisi}.csv",
            [{"kampanya_turu": "kart", "kampanya_avantaji": "aynı cümle"}],
        )
    assert altin_set.kopya_suphesi() == []


# ---------------------------------------------------------------------------
# Kalibrasyon bloğu — uyum ölçümü için ayrı örnek kümesi
# ---------------------------------------------------------------------------


def test_kalibrasyon_altin_set_ornekleminin_disindan_secer(gold_dizini, monkeypatch):
    """Kalibrasyon altın sete dokunmamalı; aksi hâlde etiketlenmiş örnek
    hem cevap anahtarında hem uyum ölçümünde olur."""
    kampanyalar = [_kampanya(f"02{i:02d}", s) for i in range(4) for s in range(10)]
    monkeypatch.setattr(altin_set, "kampanyalari_oku", lambda: iter(kampanyalar))

    secilen = altin_set.katmanli_ornekle(kampanyalar, 20)
    altin_set.calisma_sayfalari_yaz(secilen, altin_set.KISILER)
    assert altin_set.komut_kalibrasyon(10) == 0

    orneklemde = altin_set.altin_set_orneklemi()
    kalibrasyonda = {
        kimlik
        for _, kimlik, _, _ in altin_set._csv_oku(
            gold_dizini / f"{altin_set.KALIBRASYON_ONEK}eren.csv"
        )
    }
    assert kalibrasyonda, "kalibrasyon bloğu boş"
    assert not (kalibrasyonda & orneklemde), "kalibrasyon altın set örneklemiyle çakışıyor"


def test_kalibrasyon_herkeste_ayni_ornekler(gold_dizini, monkeypatch):
    kampanyalar = [_kampanya(f"02{i:02d}", s) for i in range(4) for s in range(10)]
    monkeypatch.setattr(altin_set, "kampanyalari_oku", lambda: iter(kampanyalar))
    altin_set.calisma_sayfalari_yaz(altin_set.katmanli_ornekle(kampanyalar, 20), altin_set.KISILER)
    altin_set.komut_kalibrasyon(10)

    listeler = [
        [k for _, k, _, _ in altin_set._csv_oku(gold_dizini / f"{altin_set.KALIBRASYON_ONEK}{p.lower()}.csv")]
        for p in altin_set.KISILER
    ]
    assert all(liste == listeler[0] for liste in listeler)


def test_kalibrasyon_dolu_dosyayi_ezmez(gold_dizini, monkeypatch):
    kampanyalar = [_kampanya(f"02{i:02d}", s) for i in range(4) for s in range(10)]
    monkeypatch.setattr(altin_set, "kampanyalari_oku", lambda: iter(kampanyalar))
    altin_set.calisma_sayfalari_yaz(altin_set.katmanli_ornekle(kampanyalar, 20), altin_set.KISILER)
    altin_set.komut_kalibrasyon(10)
    _csv_doldur(gold_dizini / f"{altin_set.KALIBRASYON_ONEK}eren.csv", [{"kampanya_turu": "kart"}])

    assert altin_set.komut_kalibrasyon(10) == 1


def test_uyum_kalibrasyon_varsa_onu_kullanir(gold_dizini, monkeypatch):
    kampanyalar = [_kampanya(f"02{i:02d}", s) for i in range(4) for s in range(10)]
    monkeypatch.setattr(altin_set, "kampanyalari_oku", lambda: iter(kampanyalar))
    altin_set.calisma_sayfalari_yaz(altin_set.katmanli_ornekle(kampanyalar, 20), altin_set.KISILER)
    altin_set.komut_kalibrasyon(10)

    assert altin_set.aktif_uyum_kaynagi()[0] == altin_set.UYUM_ONEK
    _csv_doldur(gold_dizini / f"{altin_set.KALIBRASYON_ONEK}eren.csv", [{"kampanya_turu": "kart"}])
    assert altin_set.aktif_uyum_kaynagi()[0] == altin_set.KALIBRASYON_ONEK


# ---------------------------------------------------------------------------
# Sözleşme denetleyicisi (make altin-denetle)
# ---------------------------------------------------------------------------
#
# Bu komut, 14 Ağustos'ta ortaya çıkan iki gerçek hatanın panzehiridir:
# kişisel CSV'lerin baştan sona boş kalması (kimse fark etmedi, altın set
# 60 yerine 10 örnek oldu) ve enum yerine serbest metin yazılması
# ('konut' / 'taşıt' / '16 ağustos'). İkisi de derleme anında değil,
# etiketleyenin masasında yakalanmalı.


def test_oneri_turkce_harfi_normalize_eder():
    """'taşıt' -> 'tasit_finansmani'. Normalizasyon olmadan difflib harf
    örtüşmesine bakıp 'kart' öneriyordu — yanlış öneri, önerisizlikten kötü."""
    assert altin_set._yakin_oneri("taşıt", altin_set.GECERLI_TURLER) == "tasit_finansmani"
    assert altin_set._yakin_oneri("ihtiyaç", altin_set.GECERLI_TURLER) == "ihtiyac_finansmani"
    assert altin_set._yakin_oneri("konut", altin_set.GECERLI_TURLER) == "konut_finansmani"


def test_oneri_kilavuz_esanlamlisini_kullanir():
    assert altin_set._yakin_oneri("kredi kartı", altin_set.GECERLI_TURLER) == "kart"
    assert altin_set._yakin_oneri("katılma", altin_set.GECERLI_TURLER) == "yatirim_urunu"
    assert altin_set._yakin_oneri("herkes", altin_set.GECERLI_KITLELER) == "tum_musteriler"


def test_oneri_emin_olmadiginda_tahmin_etmez():
    """Karşılığı bilinmeyen değerde tüm geçerli değerler basılır; uydurma
    öneri, son tarihe yetişmeye çalışan etiketleyici tarafından sorgusuz
    kabul edilirdi."""
    oneri = altin_set._yakin_oneri("zurna", altin_set.GECERLI_TURLER)
    assert oneri.startswith("geçerliler:")


def test_denetleyici_bos_kampanya_turunu_yakalar(gold_dizini):
    """En pahalı sessiz hata: kampanya_turu boşsa satırın TAMAMI derlemede
    atlanır. 14 Ağustos'ta dört kişinin kişisel dosyası bu yüzden 0 satır
    saydı ve kimse fark etmedi."""
    _hazirla(gold_dizini)
    hatalar, etiketlenen, toplam = altin_set.dosya_denetle(
        gold_dizini / "etiketleme_eren.csv"
    )
    assert etiketlenen == 0
    assert toplam > 0
    assert all("kampanya_turu BOŞ" in h for h in hatalar)


def test_denetleyici_gecersiz_enum_ve_tarihi_yakalar(gold_dizini):
    _hazirla(gold_dizini)
    _csv_doldur(
        gold_dizini / "etiketleme_eren.csv",
        [{"kampanya_turu": "konut", "hedef_kitle": "yeni", "kampanya_bitis": "16 ağustos"}],
    )
    hatalar, _, _ = altin_set.dosya_denetle(gold_dizini / "etiketleme_eren.csv")
    birlesik = " ".join(hatalar)
    assert "konut_finansmani" in birlesik
    assert "yeni_musteri" in birlesik
    assert "YYYY-AA-GG" in birlesik


def test_denetleyici_bos_ve_soru_isaretini_hata_saymaz(gold_dizini):
    """Boş = 'metinde yok', '?' = 'emin değilim'. İkisi de geçerli beyandır;
    denetleyici bunları ihlal sayarsa etiketleyiciyi değer uydurmaya iter."""
    _hazirla(gold_dizini)
    _csv_doldur(
        gold_dizini / "etiketleme_eren.csv",
        [{"kampanya_turu": "diger", "kar_payi_orani": "", "vade_ay_max": "?"}],
    )
    hatalar, etiketlenen, _ = altin_set.dosya_denetle(gold_dizini / "etiketleme_eren.csv")
    assert etiketlenen == 1
    assert hatalar == []


def test_denetleyici_supheli_arama_yakalar(gold_dizini):
    """Yıllık oran aylık sanılırsa tüm maliyet hesabı kayar."""
    _hazirla(gold_dizini)
    _csv_doldur(
        gold_dizini / "etiketleme_eren.csv",
        [{"kampanya_turu": "finansman", "kar_payi_orani": "48", "vade_ay_max": "900"}],
    )
    hatalar, _, _ = altin_set.dosya_denetle(gold_dizini / "etiketleme_eren.csv")
    birlesik = " ".join(hatalar)
    assert "AYLIK" in birlesik
    assert "şüpheli" in birlesik


# ---------------------------------------------------------------------------
# Atlanma uyarısı — "baktım, yok" ile "bakmadım" ayrımı
# ---------------------------------------------------------------------------


class TestAtlanmaUyarilari:
    """Boş hücre 'metinde yok' demektir; bakmadan boş bırakmak sessiz hatadır.

    Sözleşmede kapatılamayan tek delik buydu: hücre düzeyinde "bakıldı" işareti
    yok. Uyarı, sistemin değer bulduğu boş hücreleri etiketleyene bir kez
    sorar — kararı yine insan verir.
    """

    def _hazirla(self, gold_dizini, hucreler: dict[str, str]):
        kampanya = _kampanya("0203", 1, metin="Aylık kâr payı %1,89 ile 120 aya kadar.")
        kampanya.kar_payi_orani = Alan(
            deger=1.89, ham_ifade="%1,89", guven=0.9, yontem="kural"
        )
        yol = gold_dizini / "etiketleme_test.csv"
        altin_set._csv_yaz(yol, [kampanya])
        _csv_doldur(yol, [{"kampanya_turu": "finansman", **hucreler}])
        return yol, [kampanya]

    def test_bos_hucrede_sistem_deger_bulduysa_uyarir(self, gold_dizini) -> None:
        yol, kampanyalar = self._hazirla(gold_dizini, {})
        uyarilar = altin_set.atlanma_uyarilari(yol, kampanyalar)
        assert len(uyarilar) == 1
        assert "kar_payi_orani" in uyarilar[0]

    def test_etiketlenmis_hucre_uyari_uretmez(self, gold_dizini) -> None:
        yol, kampanyalar = self._hazirla(gold_dizini, {"kar_payi_orani": "1,89"})
        assert altin_set.atlanma_uyarilari(yol, kampanyalar) == []

    def test_soru_isareti_uyari_uretmez(self, gold_dizini) -> None:
        """'?' zaten 'bakmadım' demek — uyarının amacı bunu söyletmek."""
        yol, kampanyalar = self._hazirla(gold_dizini, {"kar_payi_orani": "?"})
        assert altin_set.atlanma_uyarilari(yol, kampanyalar) == []

    def test_dokunulmamis_satir_atlanir(self, gold_dizini) -> None:
        """kampanya_turu boşsa satıra hiç bakılmamıştır; zaten hata raporlanıyor.

        Bu satır için ayrıca atlanma uyarısı üretmek, aynı sorunu iki kez
        söylemek olurdu — etiketleyen hangisine bakacağını şaşırır.
        """
        kampanya = _kampanya("0203", 1, metin="Aylık kâr payı %1,89 ile.")
        kampanya.kar_payi_orani = Alan(
            deger=1.89, ham_ifade="%1,89", guven=0.9, yontem="kural"
        )
        yol = gold_dizini / "etiketleme_test.csv"
        altin_set._csv_yaz(yol, [kampanya])  # hiç doldurulmadı: tüm hücreler boş
        assert altin_set.atlanma_uyarilari(yol, [kampanya]) == []


class TestSifirKarPayi:
    """'Vade farksız' kampanyada kâr payı gerçekten sıfırdır, bilinmiyor değil."""

    def test_sifir_kabul_edilir(self, gold_dizini) -> None:
        kampanya = _kampanya("0203", 1)
        yol = gold_dizini / "etiketleme_test.csv"
        altin_set._csv_yaz(yol, [kampanya])
        _csv_doldur(yol, [{"kampanya_turu": "finansman", "kar_payi_orani": "0"}])
        hatalar, _, _ = altin_set.dosya_denetle(yol)
        assert not [h for h in hatalar if "kar_payi_orani" in h]

    def test_makul_olmayan_oran_hala_yakalanir(self, gold_dizini) -> None:
        kampanya = _kampanya("0203", 1)
        yol = gold_dizini / "etiketleme_test.csv"
        altin_set._csv_yaz(yol, [kampanya])
        _csv_doldur(yol, [{"kampanya_turu": "finansman", "kar_payi_orani": "84"}])
        hatalar, _, _ = altin_set.dosya_denetle(yol)
        assert [h for h in hatalar if "kar_payi_orani" in h]


class TestDogrulamaSayfasi:
    """Doğrulama sayfası mevcut etiketi ve kaynak metni yan yana koyar."""

    def test_etiket_ve_alinti_birlikte_gosterilir(self, gold_dizini) -> None:
        kampanya = _kampanya(
            "0203", 1,
            metin="Konut finansmanında 120 aya kadar vade imkânı sunulmaktadır.",
        )
        yol = gold_dizini / "etiketleme_test.csv"
        altin_set._csv_yaz(yol, [kampanya])
        _csv_doldur(yol, [{"kampanya_turu": "konut_finansmani", "vade_ay_max": "120"}])

        sayfa = altin_set.dogrulama_sayfasi(yol)
        assert "**vade_ay_max** — şu an: `120`" in sayfa
        assert "120 aya kadar vade" in sayfa

    def test_sistemin_cikarimi_sayfada_YER_ALMAZ(self, gold_dizini) -> None:
        """Sayfa sistemin tahminini gösterseydi cevap anahtarı kopyasına dönerdi."""
        kampanya = _kampanya("0203", 1, metin="Aylık kâr payı %1,89.")
        kampanya.kar_payi_orani = Alan(
            deger=1.89, ham_ifade="SISTEM_TAHMINI", guven=0.9, yontem="kural"
        )
        yol = gold_dizini / "etiketleme_test.csv"
        altin_set._csv_yaz(yol, [kampanya])
        _csv_doldur(yol, [{"kampanya_turu": "finansman"}])
        assert "SISTEM_TAHMINI" not in altin_set.dogrulama_sayfasi(yol)

    def test_bos_hucre_anlami_yazili(self, gold_dizini) -> None:
        kampanya = _kampanya("0203", 1)
        yol = gold_dizini / "etiketleme_test.csv"
        altin_set._csv_yaz(yol, [kampanya])
        _csv_doldur(yol, [{"kampanya_turu": "finansman"}])
        sayfa = altin_set.dogrulama_sayfasi(yol)
        assert 'metinde yok' in sayfa and '`?`' in sayfa
