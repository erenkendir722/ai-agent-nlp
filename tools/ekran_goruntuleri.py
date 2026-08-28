"""Arayüz ekran görüntüleri — README ve dokümantasyon için (ES-14).

    make ekran-goruntuleri              # çalışan arayüzden görüntü al
    make ekran-goruntuleri adres=...    # başka bir adresten

NEDEN BETİK, ELLE ALINMIYOR:
    Elle alınan ekran görüntüsü, arayüz değişince sessizce eskir — depodaki en
    eski yalan türü budur (`docs/CIKTI_ORNEKLERI.md` aynı sebeple üretiliyor).
    Betik her koşuda hepsini yeniden alır; «bir tanesini güncellemeyi unutmak»
    diye bir durum kalmaz.

NEDEN ÇALIŞAN ARAYÜZE BAĞLANIYOR:
    Streamlit'i betiğin içinden başlatmak, portu ve süreç ömrünü yönetmek
    demekti; `make run` zaten var. Arayüz kapalıysa betik bunu söyleyip çıkar.

ÖLÇÜ 1440×900:
    Sunum projeksiyonu 1920×1080; README'de görüntü ölçeklenerek gösteriliyor.
    1440×900 iki yerde de okunur kalıyor, 1280×720'de kart yazıları küçülüyor.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from urllib.parse import quote

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

CIKTI = KOK / "docs" / "gorseller"
ADRES = "http://localhost:8501"

# (dosya adı, sayfa yolu, açıklama, tıklanacak düğmeler, kaydırma) — yol Streamlit'in
# çok sayfalı adresidir. Düğme sütunu BOŞ EKRAN sorununu çözer: asistan ve
# metin analizi ekranları ilk açılışta boştur ve boş bir sohbet penceresi
# README'de hiçbir şey anlatmaz. Düğmeler sırayla tıklanır, her tıklamadan
# sonra çizim beklenir.
SAYFALAR = [
    ("01-genel-bakis.png", "", "Genel Bakış — kapsam, dağılım, son çekim", (), 0),
    ("02-musteri-profili.png", "Müşteri_Profili", "Müşteri Profili — toplam maliyete göre sıralama", (), 0),
    ("03-karsilastirma.png", "Karşılaştırma", "Karşılaştırma — beş ölçüt, ağırlıklar kullanıcıda", (), 0),
    ("04-chatbot.png", "Chatbot", "Kampanya Asistanı — kaynaklı cevap ve kalkan",
     ("Kuveyt Türk'ün konut finansmanı oranı ne?",), 0),
    # Metin Analizi'nde asıl kanıt SONUÇ TABLOSUDUR (alan · değer · birim ·
    # güven · alıntı) ve o, düğmenin altında kalıyor — bu yüzden kaydırılıyor.
    ("05-metin-analizi.png", "Metin_Analizi", "Metin Analizi — yapıştırılan metinden alan çıkarımı",
     ("Örnek Metni Dene (Şartname Örneği)", "Analiz Et"), 620),
    ("06-banka-profili.png", "Banka_Profili", "Banka Profili — tazelik, biten kampanyalar, doluluk", (), 0),
    ("07-boru-hatti.png", "Boru_Hattı", "Canlı Boru Hattı — toplama ve çıkarım arayüzden", (), 0),
]

GENISLIK, YUKSEKLIK = 1440, 900
CIZIM_SURESI = 6.0
"""Sayfa yüklendikten sonra beklenen süre.

Streamlit iskeleti önce boş gönderir, içeriği WebSocket üzerinden doldurur;
`document.readyState` içerik gelmeden `complete` olur. Sabit bekleme, gerçek
çizim olayını dinlemekten çirkin ama tek koşuluk bir betikte yeterli."""


def _surucu():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    ayar = Options()
    ayar.add_argument("--headless=new")
    ayar.add_argument(f"--window-size={GENISLIK},{YUKSEKLIK}")
    ayar.add_argument("--hide-scrollbars")
    ayar.add_argument("--force-device-scale-factor=2")  # Retina keskinliği
    return webdriver.Chrome(options=ayar)


def _dugmeye_bas(surucu, etiket: str) -> bool:
    """Görünen metnine göre bir Streamlit düğmesine basar.

    Streamlit düğme metnini `<button>` içindeki `<p>`'ye koyuyor, o yüzden
    `contains(., ...)` kullanılıyor. Kesme işareti XPath'te tırnak sorunu
    çıkarır («Kuveyt Türk'ün»); `concat` ile kaçırılır.
    """
    from selenium.webdriver.common.by import By

    if "\'" in etiket:
        parcalar = etiket.split("\'")
        ifade = "concat(" + ", \"'\", ".join(f'"{p}"' for p in parcalar) + ")"
    else:
        ifade = f'"{etiket}"'
    try:
        dugme = surucu.find_element(By.XPATH, f"//button[contains(., {ifade})]")
    except Exception:
        return False
    surucu.execute_script("arguments[0].click();", dugme)
    return True


def _ayakta_mi(adres: str) -> bool:
    import httpx

    try:
        return httpx.get(adres, timeout=5.0).status_code < 500
    except Exception:
        return False


def calistir(adres: str = ADRES) -> int:
    if not _ayakta_mi(adres):
        print(f"❌ Arayüz {adres} adresinde ayakta değil. Önce `make run` koşun.")
        return 1

    CIKTI.mkdir(parents=True, exist_ok=True)
    surucu = _surucu()
    try:
        for dosya, yol, aciklama, dugmeler, kaydirma in SAYFALAR:
            # `embed=true` Streamlit'in kendi araç çubuğunu («Deploy», üç nokta)
            # gizler; README'ye giren görüntüde bizim arayüzümüz kalsın diye.
            surucu.get(f"{adres}/{quote(yol)}?embed=true" if yol else f"{adres}/?embed=true")
            time.sleep(CIZIM_SURESI)
            for etiket in dugmeler:
                if not _dugmeye_bas(surucu, etiket):
                    print(f"   '{etiket}' düğmesi bulunamadı — {dosya} eksik kalabilir")
                time.sleep(CIZIM_SURESI)
            if kaydirma:
                surucu.execute_script(f"window.scrollTo(0, {kaydirma});")
                time.sleep(1.5)
            hedef = CIKTI / dosya
            surucu.save_screenshot(str(hedef))
            print(f"  {hedef.relative_to(KOK)}  ({hedef.stat().st_size // 1024} KB) — {aciklama}")
    finally:
        surucu.quit()

    print(f"✅ {len(SAYFALAR)} görüntü: {CIKTI.relative_to(KOK)}/")
    return 0


def main() -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--adres", default=ADRES)
    return calistir(ayristirici.parse_args().adres)


if __name__ == "__main__":
    raise SystemExit(main())
