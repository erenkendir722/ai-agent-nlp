"""Sayfa gezinme düğmeleri her ekranda kurulu mu.

NEDEN VAR:
    `sayfa_gezinme()` sağ alta «başa dön / sona git» düğmelerini basar, aşağı
    okun hedefi olan `#kl-alt` çapasını ise `sayfa_sonu()` basar. İkisi ayrı
    çağrı çünkü çapaların ARASINDA sayfanın kendi içeriği duruyor.

    Bir sayfa `sayfa_sonu()` çağırmayı unutursa aşağı ok SESSİZCE çalışmaz:
    tıklanır, hiçbir şey olmaz, hata da çıkmaz. Kullanıcının fark edeceği tek
    şey düğmenin bozuk olduğudur. Sessiz bozulmayı testin yakalaması gerekir.

    Yeni bir sayfa eklendiğinde bu test onu kendiliğinden kapsar — dosya
    listesi elle yazılmadı, `app/` taranıyor.
"""

from __future__ import annotations

from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
APP = KOK / "app"


def _sayfalar() -> list[Path]:
    """Gerçek Streamlit sayfaları — yardımcı modüller değil.

    Ayrım `st.set_page_config` çağrısıdır: Streamlit onu sayfa başına bir kez
    ve YALNIZ sayfa betiğinde kabul eder. `app/` altındaki `akis.py`,
    `boru_durumu.py`, `is_yurutucu.py` gibi destek modülleri onu çağırmaz ve
    bir ekran çizmedikleri için gezinme düğmesi de istemezler.

    Dosya adına göre elemek kırılgan olurdu — yeni bir yardımcı modül eklenince
    test yanlış yere bakardı. Sayfa olmanın teknik tanımı bu çağrıdır.
    """
    hepsi = sorted([*APP.glob("*.py"), *(APP / "pages").glob("*.py")])
    return [y for y in hepsi if "st.set_page_config(" in y.read_text(encoding="utf-8")]


SAYFALAR = _sayfalar()


def test_sayfa_listesi_bos_degil() -> None:
    """Süzgeç yanlışlıkla her şeyi elerse yukarıdaki testler sessizce boş geçer."""
    assert len(SAYFALAR) >= 7, f"yalnız {len(SAYFALAR)} sayfa bulundu — süzgeç bozuk"


@pytest.mark.parametrize("sayfa", SAYFALAR, ids=lambda y: y.name)
def test_sayfa_gezinme_dugmelerini_kuruyor(sayfa: Path) -> None:
    metin = sayfa.read_text(encoding="utf-8")
    assert "sayfa_gezinme()" in metin, (
        f"{sayfa.name} `sayfa_gezinme()` çağırmıyor — sağ alttaki gezinme "
        "düğmeleri o sayfada çıkmaz."
    )


@pytest.mark.parametrize("sayfa", SAYFALAR, ids=lambda y: y.name)
def test_sayfa_sonu_capasi_var(sayfa: Path) -> None:
    metin = sayfa.read_text(encoding="utf-8")
    assert "sayfa_sonu()" in metin, (
        f"{sayfa.name} `sayfa_sonu()` çağırmıyor — aşağı ok tıklanır ama "
        "hiçbir şey olmaz (hedef çapa basılmamış)."
    )


def test_gezinme_capalari_yardimcida_eslesiyor() -> None:
    """Düğmenin hedefi ile basılan çapanın kimliği aynı olmalı."""
    kaynak = (APP / "ui_utils.py").read_text(encoding="utf-8")
    assert 'href="#kl-ust"' in kaynak and 'id="kl-ust"' in kaynak
    assert 'href="#kl-alt"' in kaynak, "aşağı okun hedefi yok"
    assert 'id="kl-alt"' in kaynak, "`sayfa_sonu()` `#kl-alt` çapasını basmıyor"


def test_gelistirici_anahtari_her_sayfada_bir_kez() -> None:
    """Sağ üstteki geliştirici anahtarı her sayfada TAM BİR KEZ kurulmalı.

    NEDEN NÖBETÇİ — iki yönde de sessiz bozuluyor:

        hiç çağrılmazsa  ->  `dev_mode` hiç tanımlanmaz, sayfadaki JSON ve
                             cURL blokları ölür; kimse hata görmez, yalnız
                             açılmazlar.
        iki kez çağrılırsa -> aynı `key` ile ikinci `st.toggle`,
                             Streamlit'te `DuplicateWidgetID` fırlatır.

    Anahtar 28 Ağustos'ta kenar çubuğundaki marka bloğundan (`ortak_kenar`)
    ayrıldı; o blokla birlikte silinme riski bu testin var olma sebebi.
    """
    eksik, fazla = [], []
    for sayfa in SAYFALAR:
        sayi = sayfa.read_text(encoding="utf-8").count("gelistirici_anahtari()")
        if sayi == 0:
            eksik.append(sayfa.name)
        elif sayi > 1:
            fazla.append(sayfa.name)

    assert not eksik, f"geliştirici anahtarı yok: {', '.join(eksik)}"
    assert not fazla, f"anahtar birden çok kez kuruluyor: {', '.join(fazla)}"


# ---------------------------------------------------------------------------
# Sayfalar arası seçim devri — `bp_secili_banka`
# ---------------------------------------------------------------------------
#
# İki sayfa bu anahtarı YAZIYOR (Müşteri Profili «Detay», Karşılaştırma
# «Devam et»), bir sayfa OKUYOR (Banka Profili). Okuyan taraftaki seçicinin
# seçenekleri banka ADLARI; yazan taraf kod yazarsa değer hiçbir seçeneğe
# uymaz. Banka Profili'ndeki geçerlilik kapısı o değeri sessizce düşürür ve
# seçici alfabetik İLK bankaya konumlanır.
#
# 28 Ağustos'ta tam bu oldu: Müşteri Profili `banka_kodu` yazıyordu ve
# «Detay» hangi kampanyada tıklanırsa tıklansın Albaraka Türk açılıyordu.
# Hata vermiyor, log basmıyor — yalnız yanlış bankayı gösteriyor.

BP_ANAHTARI = "bp_secili_banka"


def test_banka_profili_secimi_ADLA_kurulur() -> None:
    """`bp_secili_banka`ya yazılan her değer banka ADI olmalı, kod değil."""
    hatalar = []
    for sayfa in SAYFALAR:
        for satir in sayfa.read_text(encoding="utf-8").splitlines():
            govde = satir.strip()
            if govde.startswith("#") or f'"{BP_ANAHTARI}"' not in govde:
                continue
            if "=" not in govde or govde.lstrip().startswith("if "):
                continue  # okuma/doğrulama satırı, atama değil
            if ".banka_kodu" in govde:
                hatalar.append(f"{sayfa.name}: {govde}")

    assert not hatalar, (
        "`bp_secili_banka` banka KODU ile kuruluyor; Banka Profili'ndeki "
        "seçicinin seçenekleri banka ADLARI, değer eşleşmez ve sayfa "
        "alfabetik ilk bankayı açar:\n  " + "\n  ".join(hatalar)
    )


def test_banka_profili_secimi_bilinen_bir_bankayi_acar() -> None:
    """Uçtan uca: anahtar kurulup sayfa koşunca O banka seçili gelmeli.

    Statik denetim yazanı tutar; bu test okuyan tarafı da tutar — seçicinin
    seçenek kümesi bir gün koda dönerse burada patlar.
    """
    pytest.importorskip("streamlit.testing.v1")
    from streamlit.testing.v1 import AppTest

    try:
        from src.depolama import tum_kayitlar

        kayitlar = tum_kayitlar()
    except Exception:  # noqa: BLE001 — veri yoksa denetlenecek bir şey yok
        pytest.skip("veritabanı okunamadı")
    if len(kayitlar) < 2:
        pytest.skip("veritabanı boş")

    # ALFABETİK İLK OLMAYAN bir banka seçilir: hedef banka zaten varsayılansa
    # test, seçim hiç kurulmadığında da geçerdi.
    adlar = sorted({k.banka_adi for k in kayitlar})
    hedef = adlar[-1]

    at = AppTest.from_file(str(APP / "pages" / "5_Banka_Profili.py"), default_timeout=300)
    at.session_state[BP_ANAHTARI] = hedef
    at.run()

    assert not at.exception, "Banka Profili istisna fırlattı"
    assert at.session_state[BP_ANAHTARI] == hedef, (
        f"«{hedef}» seçilmesi bekleniyordu, sayfa "
        f"«{at.session_state[BP_ANAHTARI]}» ile açıldı"
    )
