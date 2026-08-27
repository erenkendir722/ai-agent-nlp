"""Sistem soruları, segment süzgeci, özel ölçütler, süresi dolmuş rozeti.

27 Ağustos'ta jüri havuzu (35 soru) baştan sona koşuldu ve dört desen çıktı.
Hepsinin ortak yanı, sorulan şeyin HİÇ TANINMAMASI ve sorudaki başka bir
sözcüğün ölçüt sanılmasıydı.

EZBER YOK: ne segment listesi ne konu listesi yazıldı. Segment dağarcığı
korpustaki `segment_detayi` değerlerinden, ölçüt eşlemesi terim sözlüğünden,
sistem sorusu ayrımı Türkçe şahıs ekinden geliyor.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from src.depolama import KampanyaKaydi
from src.rag.chatbot import (
    Niyet,
    _segment_filtrele,
    _sorulan_olcut,
    _sorulan_olcutler,
    _suresi_dolmus,
    segment_dagarcigi,
    sistem_sorusu_mu,
    sor,
)
from src.terim_sozlugu import (
    alan_eslemesi,
    hesaplanan_olcutler,
    karistirilan_olcutler,
)


def _kayit(kimlik: str, *, banka: str = "K Katılım Bankası A.Ş.", **alanlar: object):
    varsayilan: dict[str, object] = {
        "kampanya_id": kimlik,
        "banka_kodu": "0299",
        "banka_adi": banka,
        "kaynak_url": f"https://ornek.test/{kimlik}",
        "cekim_tarihi": datetime(2026, 8, 27),
        "kampanya_turu": "ihtiyac_finansmani",
        "tam_kayit": "{}",
        "ham_metin": "ornek",
        "ortalama_guven": 0.8,
        "doluluk_orani": 0.5,
    }
    return KampanyaKaydi(**{**varsayilan, **alanlar})  # type: ignore[arg-type]


def _segmentli(kimlik: str, segmentler: list[str], **alanlar: object) -> KampanyaKaydi:
    import json

    return _kayit(
        kimlik,
        tam_kayit=json.dumps({"uygunluk": {"segment_detayi": segmentler}}),
        **alanlar,
    )


# ---------------------------------------------------------------------------
# Ölçüt eşlemesi SÖZLÜKTEN türer
# ---------------------------------------------------------------------------


def test_olcut_eslemesi_sozlukten_gelir() -> None:
    """Elle yazılan ipucu listesinde olmayan karşılıklar sözlükte var."""
    esleme = alan_eslemesi()
    assert esleme.get("nakit iade") == "odul_miktari"
    assert esleme.get("mil") == "odul_miktari"
    assert esleme.get("vade") == "vade_ay_max"


def test_sozluk_vetolari_kimlik_saymaz() -> None:
    """«`kar_payi_orani` ile KARIŞTIRILMAZ» bir kimlik beyanı DEĞİLDİR."""
    karisan = karistirilan_olcutler()
    assert "kar payi dagitim orani" in karisan
    assert "kar payi dagitim orani" not in alan_eslemesi()


def test_ilk_beyan_kimligi_kurar() -> None:
    """«`odul_miktari`; `kar_payi_orani` VETOSU» -> ödül ölçütüdür.

    Sütunun tamamında veto sözcüğü aramak geçerli kimliği de silerdi.
    """
    assert "nakit iade" not in karistirilan_olcutler()


@pytest.mark.parametrize(
    ("soru", "beklenen"),
    [
        # KUSUR: «vade» baskın çıkıyordu
        ("48 ay vadeli taşıt finansmanında en düşük toplam maliyet", "vade_ay_max"),
        ("en uzun vadeyi kim veriyor", "vade_ay_max"),
        ("en yüksek nakit iadeyi kim veriyor", "odul_miktari"),
        ("finansman limiti en yüksek hangi banka", "finansman_tutari_max"),
        ("hangi bankada tahsis ücreti yok", "masrafsiz_mi"),
    ],
)
def test_en_ozgul_ipucu_kazanir(soru: str, beklenen: str) -> None:
    assert _sorulan_olcut(soru) == beklenen


def test_coklu_olcut_ozgullukten_siralanir() -> None:
    olcutler = _sorulan_olcutler("kâr payı oranı ve maksimum vade süresi nedir")
    assert olcutler[0] == "kar_payi_orani"
    assert "vade_ay_max" in olcutler


# ---------------------------------------------------------------------------
# Sıralanamayan ölçüt SIRALANMAZ, beyan edilir
# ---------------------------------------------------------------------------


def test_hesaplanan_olcut_tutari_sorar() -> None:
    """«Toplam maliyet» bir sütun değil formüldür; anapara ister.

    YALNIZ EKSİK OLANI SORAR (27 Ağustos): soruda vade zaten var («48 ay»)
    ve eski metin her koşulda «anapara ve vade» istiyordu — kullanıcının
    söylediğini görmezden gelip yeniden sormak, soruyu anlamamış görünmektir.
    """
    assert "finansman maliyeti" in hesaplanan_olcutler()

    cevap = sor(
        "48 ay vade sunan taşıt finansmanında en düşük toplam finansman "
        "maliyetini hangi banka sağlıyor",
        [_kayit("a", kar_payi_orani=1.9), _kayit("b", banka="L Katılım Bankası A.Ş.")],
    )
    assert "hesaplanan bir ölçüt" in cevap.metin
    assert "anapara" in cevap.metin
    assert "vade (örn." not in cevap.metin, "vade soruda vardı, yeniden sorulmamalı"
    assert cevap.beklenen_yuvalar == ("tutar",)


def test_hesaplanan_olcut_sorulan_yuvayi_beyan_eder() -> None:
    """Sorulan yuva bildirilmezse bir sonraki tur cevabı DUYAMAZ.

        tur 1: «48 ay vadeli … en düşük toplam maliyet?» -> «anapara gerekiyor»
        tur 2: «1.000.000 TL»                            -> «kapsam dışı»   ✗

    Çıplak nicelikte hiçbir alan sözcüğü geçmez; dayanak kapısı onu haklı
    olarak reddeder. Muafiyetin dayanağı metin değil, sistemin kendi sorusu.
    """
    from src.rag.baglam import soruyu_tamamla

    kayitlar = [_kayit("a", kar_payi_orani=1.9)]
    ilk = sor("en düşük toplam maliyet hangi bankada", kayitlar)
    assert ilk.beklenen_yuvalar == ("tutar", "vade")
    assert ilk.baglam is not None and ilk.baglam.beklenen_yuvalar == ("tutar", "vade")

    devir = soruyu_tamamla("1.000.000 TL", ilk.baglam, kayitlar)
    assert devir.beklenen_yuva_dolduruldu


def test_karisan_olcut_siralanmaz_beyan_edilir() -> None:
    """Katılma hesabının kâr paylaşım oranı finansman oranı DEĞİLDİR."""
    cevap = sor(
        "katılma hesaplarında en yüksek kâr paylaşım oranını veren bankalar",
        [_kayit("a", kar_payi_orani=1.9), _kayit("b", banka="L Katılım Bankası A.Ş.")],
    )
    assert "ayrı tutulan bir kavram" in cevap.metin
    assert "sıralayamıyorum" in cevap.metin


def test_normal_olcut_ozel_beyana_dusmez() -> None:
    """«Kâr payı oranı» sorusu «kâr payı dağıtım oranı» beyanına düşmemeli."""
    cevap = sor(
        "en düşük kâr payı oranı hangi bankada",
        [
            _kayit("a", kar_payi_orani=1.9),
            _kayit("b", banka="L Katılım Bankası A.Ş.", kar_payi_orani=2.5),
        ],
    )
    assert cevap.niyet is Niyet.KARSILASTIRMA


# ---------------------------------------------------------------------------
# Segment süzgeci — dağarcık VERİDEN
# ---------------------------------------------------------------------------


def test_segment_dagarcigi_veriden_turer() -> None:
    kayitlar = [
        _segmentli("a", ["emekli"]),
        _segmentli("b", ["KOBİ", "esnaf"]),
        _kayit("c"),
    ]
    assert set(segment_dagarcigi(kayitlar).values()) == {"emekli", "KOBİ", "esnaf"}


def test_segment_gosterimi_sapkasini_korur() -> None:
    """Eşleştirme ASCII anahtarla, gösterim ham biçimle."""
    dagarcik = segment_dagarcigi([_segmentli("a", ["çiftçi"])])
    assert dagarcik == {"ciftci": "çiftçi"}


def test_sorulan_segment_kumeyi_daraltir() -> None:
    """Süzgeç doğrudan sınanır — `sor` bu soruyu RAG'a yönlendirir ve o yol ağ ister.

    Ölçülen kusur süzgecin YOKLUĞUYDU; RAG'ın getirme başarısı ayrı bir konu.
    """
    kayitlar = [
        _segmentli("emekli", ["emekli"], kar_payi_orani=1.5),
        _segmentli("kobi", ["KOBİ"], kar_payi_orani=2.5, banka="L Katılım Bankası A.Ş."),
    ]
    suzulmus = _segment_filtrele("KOBİ segmentine özel kampanya", kayitlar)

    assert [k.kampanya_id for k in suzulmus] == ["kobi"]
    assert _segment_filtrele("emeklilere özel", kayitlar)[0].kampanya_id == "emekli"


def test_segment_gecmeyen_soru_kumeyi_daraltmaz() -> None:
    kayitlar = [_segmentli("a", ["emekli"]), _segmentli("b", ["KOBİ"])]
    assert len(_segment_filtrele("en düşük kâr payı hangi bankada", kayitlar)) == 2


def test_korpusta_olmayan_segment_uydurulmaz() -> None:
    """«Sağlık çalışanlarına özel» — korpusta öyle bir işaret yok."""
    kayitlar = [_segmentli("a", ["emekli"]), _segmentli("b", ["KOBİ"])]
    cevap = sor(
        "Belirli bir meslek grubuna (sağlık çalışanları) özel kampanya var mı",
        kayitlar,
    )
    assert "veri setinde yok" in cevap.metin
    assert "emekli" in cevap.metin and "KOBİ" in cevap.metin


# ---------------------------------------------------------------------------
# Sistem soruları — ayrım ŞAHIS EKİNDEN
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "soru",
    [
        "bu oranları standart formatta filtreleyebiliyor musun",
        "masrafsız finansman tamlamasını nasıl ayrıştırıyorsun",
        "dinamik sayfaları nasıl parse ettiniz",
        "on-premise çalışabilirliği nasıl garanti ediyorsunuz",
        "hangi yöntemleri kullandınız",
        "chatbot çelişkili bilgiyi nasıl raporluyor",
    ],
)
def test_bize_sorulan_soru_dokumantasyona_yonlendirir(soru: str) -> None:
    kayitlar = [_kayit("a", kar_payi_orani=1.9)]
    assert sistem_sorusu_mu(soru, kayitlar)

    cevap = sor(soru, kayitlar)
    assert "kendi işleyişi" in cevap.metin
    assert "docs/MIMARI.md" in cevap.metin
    assert not cevap.kaynaklar, "sistem sorusuna kampanya kaynağı gösterilmemeli"


@pytest.mark.parametrize(
    "soru",
    [
        # üçüncü şahıs — veri sorusu
        "Kuveyt Türk 500 ay vade veriyor mu",
        "hangi bankalar konut finansmanı sunuyor",
        "başvuru nasıl yapılır",
        "kampanyaya kimler katılabilir",
        # modül adı kullanıcının en sık yazdığı sözcük olabilir
        "Kuveyt Türk ile Albaraka karşılaştırması",
        # «sistem» bankacılık bağlamında da geçer
        "ödeme sistemi olan kampanya var mı",
    ],
)
def test_veri_sorusu_sistem_sorusu_sayilmaz(soru: str) -> None:
    kayitlar = [
        _kayit("a", banka="Kuveyt Türk Katılım Bankası A.Ş.", kar_payi_orani=1.9),
        _kayit("b", banka="Albaraka Türk Katılım Bankası A.Ş.", kar_payi_orani=2.5),
    ]
    assert not sistem_sorusu_mu(soru, kayitlar)


# ---------------------------------------------------------------------------
# Süresi dolmuş kampanya
# ---------------------------------------------------------------------------


def test_suresi_dolmus_kampanya_isaretlenir() -> None:
    dun = date.today() - timedelta(days=1)
    cevap = sor("kâr payı oranı kaç", [_kayit("a", kar_payi_orani=1.9, kampanya_bitis=dun)])

    assert "süresi dolmuş" in cevap.metin
    assert cevap.dogrulama_gecti, "tarih yazılmamalı — kalkan sayıyı reddederdi"


def test_gecerli_kampanya_isaretlenmez() -> None:
    yarin = date.today() + timedelta(days=1)
    cevap = sor("kâr payı oranı kaç", [_kayit("a", kar_payi_orani=1.9, kampanya_bitis=yarin)])
    assert "süresi dolmuş" not in cevap.metin


def test_tarihsiz_kayit_dolmus_sayilmaz() -> None:
    """Boş hücre bir bitiş beyanı DEĞİLDİR — bilinmeyeni geçersiz saymayız."""
    assert not _suresi_dolmus(_kayit("a", kar_payi_orani=1.9))


@pytest.mark.parametrize(
    "soru",
    [
        # KİBAR İSTEK — ikinci şahıs ama VERİ isteniyor (jüri havuzu 11)
        "kampanyaları en avantajlıdan en dezavantajlıya sıralar mısın",
        "bu bankaları karşılaştırır mısın",
        "en düşük kâr payı veren bankaları listeler misin",
    ],
)
def test_kibar_veri_istegi_sistem_sorusu_sayilmaz(soru: str) -> None:
    """Türkçe'de kibar istek de ikinci şahıstır; ayırt edici olan İSTENEN ŞEY."""
    kayitlar = [
        _kayit("a", kar_payi_orani=1.9),
        _kayit("b", banka="L Katılım Bankası A.Ş.", kar_payi_orani=2.5),
    ]
    assert not sistem_sorusu_mu(soru, kayitlar)


def test_veri_istegi_isareti_sozcuk_sinirina_baglidir() -> None:
    """«geçEN kâr payı oranları» — «en» alt dize olarak bulunuyordu.

    17. madde bu yüzden veri isteği sanılıp sistem sorusu olmaktan çıkıyordu;
    ürün sözlüğündeki «ev» ~ «ters çEVrilir» hatasının aynısı.
    """
    kayitlar = [_kayit("a", kar_payi_orani=1.9)]
    assert sistem_sorusu_mu(
        "metinlerde geçen kâr payı oranlarını tek formatta "
        "filtreleyebiliyor musun",
        kayitlar,
    )


# ---------------------------------------------------------------------------
# Sistem sorusu KİBAR RET DEĞİLDİR — kendi niyeti var (27 Ağustos)
# ---------------------------------------------------------------------------


def test_sistem_cevabi_kapsam_disi_etiketlenmez() -> None:
    """`_sistem_cevabi`'nin kendi açıklaması «kibar ret DEĞİL» diyordu.

    Etiket `KAPSAM_DISI`'ydı; arayüzdeki rozet «⑥ Kapsam dışı — Kibar ret»
    yazıyor, cevap ise dokümantasyon adresi veriyordu. Jüri «Hangi modeli
    kullanıyorsunuz?» diye sorup cevabını alırken ekranda reddedildiğini
    görüyordu. Etiket cevabın kendisiyle çelişemez.
    """
    kayitlar = [_kayit("a", kar_payi_orani=1.9)]
    for soru in ("verileri nasıl topluyorsunuz",
                 "hangi modeli kullanıyorsunuz",
                 "kaynak gösteriyor musunuz"):
        cevap = sor(soru, kayitlar)
        assert cevap.niyet is Niyet.SISTEM_SORGUSU, f"{soru} -> {cevap.niyet}"
        assert "docs/MIMARI.md" in cevap.metin


def test_gercek_kapsam_disi_hala_reddediliyor() -> None:
    """Yeni niyet kapıyı gevşetmedi."""
    kayitlar = [_kayit("a", kar_payi_orani=1.9)]
    for soru in ("bugün hava nasıl", "bana bir şiir yaz", "bitcoin fiyatı kaç"):
        assert sor(soru, kayitlar).niyet is Niyet.KAPSAM_DISI, soru
