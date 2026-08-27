"""İkinci arayüz incelemesinde düzeltilen maddelerin nöbetçisi.

Hepsi «çalışan ama anlatmayan ekran» kusuruydu: kod hata vermiyor, kullanıcı
anlamıyor. Test yoksa sessizce geri gelirler.
"""

from __future__ import annotations

from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
APP = KOK / "app"
METIN_ANALIZI = APP / "pages" / "3_Metin_Analizi.py"
KARSILASTIRMA = APP / "pages" / "1_Karşılaştırma.py"


def _kodu_oku(yol: Path) -> str:
    """Yorum satırlarını atarak kaynağı okur.

    Bu dosyadaki testler kodda BİR ŞEYİN OLMADIĞINI da denetliyor. Yorumlar
    ayıklanmazsa, düzeltmeyi anlatan yorum düzeltmenin kendisini bozuk
    gösterir: `showlegend=False` idi» diye yazan bir açıklama satırı,
    «showlegend=False kalmamış olmalı» testini kırıyordu.
    """
    satirlar = yol.read_text(encoding="utf-8").splitlines()
    return "\n".join(s for s in satirlar if not s.lstrip().startswith("#"))


def test_kural_suresi_ekranda_gosteriliyor() -> None:
    """Kural motorunun süresi AYRI yazılmalı.

    Ekranda «hibrit 3,45 s · LLM 3,45 s» yazıyordu: iki sayı birebir aynı
    olduğu için kural motorunun süresi hiç görünmüyordu ve sayfanın kendi
    iddiası olan «kural motoru — regex, milisaniye» rakamla desteklenmiyordu.

    `kural_suresi` uzlaştırıcının izinde ZATEN ölçülüyor (`uzlastirici.py`);
    eksik olan tek şey ekrana yazmaktı.
    """
    metin = METIN_ANALIZI.read_text(encoding="utf-8")
    assert 'iz.get("kural_suresi")' in metin, (
        "kural motoru süresi okunmuyor — hız avantajı metinde iddia edilip "
        "rakamla gösterilmiyor"
    )
    assert "kural **" in metin, "kural süresi ekrana yazılmıyor"


def test_yontem_rozetlerinin_lejandi_var() -> None:
    """Renk kodlamasının ne anlama geldiği yazılmalı.

    KURAL/HİBRİT/LLM rozetleri tutarlı renkler kullanıyordu ama hiçbir yerde
    açıklanmıyordu; ilk kez bakan biri mavi ile morun farkını tahmin etmek
    zorundaydı.
    """
    metin = METIN_ANALIZI.read_text(encoding="utf-8")
    assert "def _lejant(" in metin, "lejant fonksiyonu yok"
    assert "MOTOR_RENKLERI" in metin, "lejant renkleri tek kaynaktan okumuyor"
    # Lejant, rozetle AYNI sözlükten türemeli; ikisi ayrışırsa lejant yalan söyler.
    assert metin.count("MOTOR_RENKLERI") >= 3, (
        "lejant ile rozet aynı renk sözlüğünü kullanmıyor"
    )


def test_serbest_metin_isareti_semadan_turer() -> None:
    """«Dikkatli kullan» işareti elle yazılmış bir listeden gelmemeli.

    Serbest metin alanları müşteriye doğrudan söylenecek cümlelerdir ve dil
    modeli üretir — sayısal alanlardan daha riskliler. Hangi alanların
    metinsel olduğu `schema.METINSEL_ALANLAR`'da yazılı; ikinci bir liste, o
    listenin şemadan ayrışmasını garanti ederdi.
    """
    metin = METIN_ANALIZI.read_text(encoding="utf-8")
    assert "METINSEL_ALANLAR" in metin, "serbest metin işareti şemadan türemiyor"
    assert "⚠" in metin, "serbest metin alanları işaretlenmiyor"


def test_halka_grafigin_lejandi_acik() -> None:
    """Dilimlerin neyi temsil ettiği görünmeli.

    `showlegend=False` idi: ekranda yalnız «%0» ve «%100» yazıyor, dilimlerin
    anapara mı kâr payı mı olduğu hiçbir yerde belirtilmiyordu.
    """
    metin = _kodu_oku(KARSILASTIRMA)
    assert "showlegend=False" not in metin, (
        "halka grafiğin lejandı kapalı — dilimlerin ne olduğu görünmez"
    )
    assert "showlegend=True" in metin


def test_turkce_arayuzde_ingilizce_yer_tutucu_yok() -> None:
    """Çok seçimli alanlar Türkçe yer tutucu taşımalı.

    Streamlit'in varsayılanı «Choose an option»; Türkçe arayüzde göze batıyor.
    Yer tutucu verilmeyen her `st.multiselect` o İngilizce metni gösterir.
    """
    metin = _kodu_oku(KARSILASTIRMA)
    eksik = metin.count("st.multiselect(") - metin.count("placeholder=")
    assert eksik <= 0, (
        f"{eksik} `st.multiselect` yer tutucusuz — İngilizce «Choose an option» çıkar"
    )


def test_ai_ciktisi_rozetle_ayriliyor() -> None:
    """Serbest metin üretimi ölçülmüş veriden görsel olarak ayrılmalı.

    Sayfadaki her şey yapısal kayıttan gelir; rakip analizi taslağı tek
    istisnadır ve sayısal doğrulama kalkanından geçmez. Ayrım küçük bir
    uyarı kutusunda kalırsa jüri «bu da mı ölçülmüş?» diye sorar.
    """
    metin = _kodu_oku(KARSILASTIRMA)
    assert "AI ÜRETİMİ — DOĞRULANMAMIŞ" in metin, "AI çıktısı rozetle ayrılmamış"
    assert "EVREN API)" not in metin, (
        "düğme hâlâ servis adı taşıyor — kullanıcıya hangi servise gidildiği "
        "değil, çıktının ne olduğu lazım"
    )
