"""Chatbot boşluk taraması — soru kümesi VERİDEN türetilir, elle yazılmaz.

    make chatbot-tarama            # bulguları dök
    make chatbot-tarama adet=40    # ilk N soru (hızlı bakış)

NEDEN `eval/chatbot_sorulari.yaml`'DAN AYRI BİR ARAÇ:

O dosya 31 soruyu ELLE tutuyor ve her birinin beklenen davranışını yazıyor —
derinlemesine, ama kapsamı elle yazıldığı kadar. Bu araç tersini yapar:
soruları korpustan ve şemadan **üretir** (dokuz banka × beş ölçüt × altı ürün
× yazım biçimleri), beklenen cevabı bilmez, yalnız PATOLOJİ arar.

27 Ağustos'ta ilk koşumu iki kusur çıkardı ve ikisi de elle yazılan test
setinin göremeyeceği türdendi, çünkü o set ikisini de sormuyordu:

    «Kâr payı oranı en düşük OLAN BANKA aynı zamanda…»  -> kibar ret
    «… en düşük TOPLAM MALİYET hangi bankada?»          -> «Vade: 3 ay»

Aranan patolojiler:

    P1  meşru soru kapsam dışı ilan edildi
    P2  sorulan ölçüt ile cevaplanan ölçüt farklı
    P3  adlandırılan banka ile kaynak bankası farklı
    P4  kalkan meşru cevabı reddetti
    P5  istisna
    P6  gerçekten kapsam dışı soru içeri sızdı
    P7  reddedilebilir iddia reddedilmedi («500 ay vade veriyor mu?»)
    P8  tanım sorusu tanınmadı

AĞ KULLANIR: koşul sorguları RAG'a gider, RAG gömme için EVREN'e. Bu yüzden
`tests/` altında değil `eval/` altında — `make test` ağsız kalmak zorunda.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter

from src.ajanlar.orkestrator import Orkestrator
from src.depolama import KampanyaKaydi, tum_kayitlar
from src.preprocessing.normalizasyon import arama_anahtari
from src.rag.chatbot import (
    _OLCUT_ETIKETLERI,
    _URUN_ANAHTARLARI,
    Niyet,
    _sorulan_olcut,
)
from src.schema import SEGMENT_ORNEKLERI

_KAYNAK_ONEKI = re.compile(r"^\[\d+\]\s*")
"""RAG kolu kaynakları «[1] » ile numaralar; ad ondan sonra başlar."""

KAPSAM_DISI_SORULAR = (
    "bugun hava nasil",
    "bana bir siir yaz",
    "python'da liste nasil ters cevrilir",
    "bitcoin fiyati kac",
)
"""Gerçekten kapsam dışı — sızarsa kalkanın allowlist'i gevşemiş demektir.

Bu dördü ELLE yazılı, çünkü «alan dışı» ancak alanın DIŞINDAN örnekle
sınanabilir; veriden türetilemez."""

SISTEM_SORULARI = (
    "verileri nasil topluyorsunuz",
    "hangi modeli kullaniyorsunuz",
    "kaynak gosteriyor musunuz",
)


def sorulari_uret(kayitlar: list[KampanyaKaydi]) -> list[tuple[str, dict]]:
    """Korpus ve şemadan soru matrisi. Elle yazılan tek şey CÜMLE KALIBIDIR."""
    bankalar = sorted({k.banka_adi for k in kayitlar})
    cekirdekler = [" ".join(arama_anahtari(b).split()[:2]) for b in bankalar]
    olcutler = list(_OLCUT_ETIKETLERI.items())
    urunler = sorted(set(_URUN_ANAHTARLARI.values()))
    sorular: list[tuple[str, dict]] = []

    def ekle(soru: str, **beklenti: object) -> None:
        sorular.append((soru, beklenti))

    for banka, cekirdek in zip(bankalar, cekirdekler, strict=True):
        for alan, etiket in olcutler:
            ekle(f"{cekirdek} {etiket} nedir", banka=banka, olcut=alan)
        # Kesme eki: özel adı ekinden ayırmak (ADR 023).
        ekle(f"{cekirdek}'in vade suresi kac ay", banka=banka, olcut="vade_ay_max")
        ekle(f"{cekirdek} kar payi orani ve azami vade nedir", banka=banka)
        ekle(f"{cekirdek} 500 ay vade veriyor mu", banka=banka, hayir=True)
        for urun in urunler:
            ekle(f"{cekirdek}'in {urun} kampanyasi var mi", banka=banka)

    for alan, etiket in olcutler:
        for yon in ("en yuksek", "en dusuk"):
            ekle(f"{yon} {etiket} hangi bankada", olcut=alan)
        # Sıfat-fiil: «olan banka» bir kurumu adlandırmaz (ADR 024).
        ekle(f"{etiket} en iyi olan banka hangisi", olcut=alan)
        ekle(f"{etiket} sunan bankalar hangileri")
        for urun in urunler:
            ekle(f"{urun} kampanyalarinda en iyi {etiket} hangi bankada", olcut=alan)

    for segment in SEGMENT_ORNEKLERI:
        ekle(f"{arama_anahtari(segment)} musterilere ozel kampanya var mi")

    for soru in SISTEM_SORULARI:
        ekle(soru, sistem=True)
    for terim in ("murabaha", "kar payi", "katilim fonu", "toplam maliyet"):
        ekle(f"{terim} nedir", tanim=True)
    for soru in KAPSAM_DISI_SORULAR:
        ekle(soru, kapsam_disi=True)

    return sorular


def tara(adet: int | None = None) -> tuple[Counter[str], dict[str, list[str]], int]:
    kayitlar = tum_kayitlar()
    ork = Orkestrator()
    sorular = sorulari_uret(kayitlar)[:adet]

    bulgular: Counter[str] = Counter()
    ornekler: dict[str, list[str]] = {}

    def bulgu(tur: str, soru: str, ayrinti: str = "") -> None:
        bulgular[tur] += 1
        ornekler.setdefault(tur, []).append(f"{soru}  ->  {ayrinti}")

    for soru, beklenti in sorular:
        try:
            cevap, _ = ork.calistir(soru, kayitlar=kayitlar)
        except Exception as hata:  # noqa: BLE001 — tarama hiçbir istisnayı yutmaz
            bulgu("P5 istisna", soru, f"{type(hata).__name__}: {hata}")
            continue

        kapsam_disi_bekleniyor = bool(beklenti.get("kapsam_disi"))
        if cevap.niyet is Niyet.KAPSAM_DISI and not kapsam_disi_bekleniyor:
            bulgu("P1 mesru soru reddedildi", soru, cevap.metin[:70])
            continue
        if kapsam_disi_bekleniyor and cevap.niyet is not Niyet.KAPSAM_DISI:
            bulgu("P6 kapsam disi sizdi", soru, f"{cevap.niyet.value}: {cevap.metin[:50]}")
            continue
        if not cevap.dogrulama_gecti:
            bulgu("P4 kalkan reddi", soru, ", ".join(cevap.reddedilen_sayilar[:4]))
            continue
        if beklenti.get("sistem") and cevap.niyet is not Niyet.SISTEM_SORGUSU:
            bulgu("P1 mesru soru reddedildi", soru, f"sistem sorusu -> {cevap.niyet.value}")
            continue
        if beklenti.get("tanim") and cevap.niyet is not Niyet.TANIM_SORGUSU:
            bulgu("P8 tanim taninmadi", soru, cevap.niyet.value)
            continue
        if beklenti.get("hayir") and not cevap.metin.startswith("**Hayır"):
            bulgu("P7 iddia reddedilmedi", soru, cevap.metin[:70])
            continue

        bankalar = {
            _KAYNAK_ONEKI.sub("", k.banka_adi) for k in cevap.kaynaklar
        }
        beklenen_banka = beklenti.get("banka")
        if beklenen_banka and bankalar and bankalar != {beklenen_banka}:
            bulgu("P3 yanlis banka", soru, f"{sorted(bankalar)} != {beklenen_banka}")
            continue

        beklenen_olcut = beklenti.get("olcut")
        if beklenen_olcut and _sorulan_olcut(soru) != beklenen_olcut:
            bulgu("P2 olcut kaymasi", soru, f"{_sorulan_olcut(soru)} != {beklenen_olcut}")

    return bulgular, ornekler, len(sorular)


def main() -> int:
    ayristirici = argparse.ArgumentParser(description="Chatbot boşluk taraması")
    ayristirici.add_argument("--adet", type=int, default=None, help="ilk N soru")
    ayristirici.add_argument("--ornek", type=int, default=5, help="tür başına örnek")
    secenek = ayristirici.parse_args()

    bulgular, ornekler, soru_sayisi = tara(secenek.adet)
    toplam = sum(bulgular.values())

    print("\n=== CHATBOT BOŞLUK TARAMASI ===\n")
    print(f"  Üretilen soru: {soru_sayisi}\n")
    if not bulgular:
        print("  Bulgu yok — soruların hepsi patolojisiz.")
        return 0

    for tur, sayi in bulgular.most_common():
        print(f"  {tur}: {sayi}")
        for ornek in ornekler[tur][: secenek.ornek]:
            print(f"      {ornek[:160]}")
        print()
    print(f"  Toplam bulgu: {toplam}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
