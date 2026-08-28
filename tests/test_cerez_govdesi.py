"""Çerez gövdesi nöbetçisi — kusurun NÜKSÜNÜ yakalar.

NEDEN BU DOSYA VAR:
Aynı kusur iki kez oldu. Dünya Katılım'ın kayıtlarında `govde_metin`,
kampanya metni değil KVKK çerez aydınlatma metniydi; çıkarım o metinden
alan üretti (33 kayıtta `vade_ay_max`, 7'sinde `kar_payi_orani`) ve ortaya
kaynak alıntılı, yani güvenilir görünen uydurma veri çıktı.

    27 Ağu · `e86ac41`  düzeltildi — «45 kaydın 44'ünde gövde aynı 7058
                        karakterlik sayfa iskeletiydi»
    28 Ağu · `2207ec4`  GERİ GELDİ — commit chatbot cevaplarıyla ilgiliydi,
                        veri değişikliği fark edilmeden içine bindi

İlk düzeltme VERİYE uygulandı, SEBEBE değil; nöbetçisi de yoktu. Bu yüzden
yeniden toplandığında sessizce nüksetti. Sebep artık kapalı
(`TemelKaziyici.cerez_katmanini_kaldir`), geçmiş onarıldı
(`tools/cerez_govdesini_onar.py`) ve üçüncü kez olmasın diye burası var.

BU TEST ÜRETİM VERİSİNİ OKUR. Depodaki `data/raw` teslim edilen korpustur;
sözleşme «bu korpusta çerez metni gövdeli kayıt YOKTUR» der. Kırılırsa
yapılacak şey testi gevşetmek değil, `make cerez-govdesini-onar` koşmaktır.
"""

from __future__ import annotations

import json

from src.collector.temel_kaziyici import CEREZ_KATMANI_SECICILER
from src.collector.toplayici import HAM_DIZIN
from tools.cerez_govdesini_onar import bozuk_kayitlar, cerez_metni_mi


def test_korpusta_cerez_govdeli_kayit_yok() -> None:
    """Teslim korpusunda hiçbir kaydın gövdesi çerez metni olmamalı."""
    bozuk = bozuk_kayitlar()
    assert bozuk == [], (
        f"{len(bozuk)} kaydın gövdesi çerez aydınlatma metni. "
        "Onarmak için: make cerez-govdesini-onar uygula=1 — "
        "ardından `extract --kimlik` ve `vektor`. "
        f"İlk üç: {[p.stem for p in bozuk[:3]]}"
    )


def test_cerez_izi_yalniz_govdenin_basinda_aranir() -> None:
    """Altında çerez politikasına değinen GERÇEK kampanya bozuk sayılmaz.

    Yanlış alarm burada pahalı: «aydınlatma» Türkçede ışıklandırma da
    demek ve Emlak Katılım'ın enerji verimliliği finansmanı sayfası tam da
    onu anlatıyor. O kayıt bozuk sayılsaydı, onarım aracı gerçek içeriği
    başka bir şeyle değiştirmeye çalışırdı.
    """
    gercek = (
        "Enerji Verimliliği Yönetim Finansmanı\n"
        "Apartman ve site yönetimlerine bina aydınlatma sistemlerinin "
        "yenilenmesi için finansman.\n" + "x" * 400 + "\n"
        "ÇEREZ KULLANIMINA İLİŞKİN AYDINLATMA METNİ"
    )
    assert not cerez_metni_mi(gercek)


def test_cerez_govdesi_yakalanir() -> None:
    bozuk = "ÇEREZ KULLANIMINA İLİŞKİN AYDINLATMA METNİ\n1. Giriş Bu metin, 6698 sayılı..."
    assert cerez_metni_mi(bozuk)


def test_onarim_ve_tarayici_ayni_sozcuk_dagarcigini_kullanir() -> None:
    """İkinci bir liste tutulmaz — ayrışırsa biri temizler, öbürü temizlemez.

    Onarım aracı seçicileri `temel_kaziyici`'den içe aktarır; bu test o bağın
    kopmadığını söyler.
    """
    from tools import cerez_govdesini_onar

    assert cerez_govdesini_onar.CEREZ_KATMANI_SECICILER is CEREZ_KATMANI_SECICILER


def test_her_ham_kayit_okunabilir_govde_tasir() -> None:
    """Gövdesi boş kayıt diske hiç yazılmamalı (eşik `_sayfayi_cek`'te)."""
    bos = [
        yol.stem
        for yol in HAM_DIZIN.rglob("*.json")
        if not (json.loads(yol.read_text(encoding="utf-8")).get("govde_metin") or "").strip()
    ]
    assert bos == [], f"gövdesi boş kayıt: {bos[:5]}"
