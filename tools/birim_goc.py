"""Boyut göçü — şema v1.1.0 kayıtlarına birim ekler (bulgu 1.1).

    python tools/birim_goc.py --deneme    # ne değişecek, YAZMADAN göster
    python tools/birim_goc.py             # uygula

NEDEN GÖÇ, NEDEN YENİDEN ÇIKARIM DEĞİL:
    Birim, ham ifadeden DETERMİNİSTİK olarak çözülür (`birim_belirle`).
    Aynı sonucu almak için 96 kaydı LLM'den geçirmek ~21 dakika sürer ve
    modelin örneklemesi yüzünden başka alanların değerlerini de oynatır —
    yani ölçülen makro-F1 birimden bağımsız sebeplerle değişirdi. Göç,
    yalnız eklenen alanı doldurur; kalan her değer BİREBİR korunur.

    Bu, `docs/SONUCLAR.md`'nin köken takibiyle de tutarlı: çıkarım koşusu
    değişmediği için kayıtlı koşu bilgisi geçerliliğini korur.

NEDEN AYRI BİR ÇÖZÜMLEYİCİ YAZILMADI:
    Göç, çıkarımın kullandığı `birim_belirle` fonksiyonunun TA KENDİSİNİ
    çağırır. İkinci bir uygulama, göç edilmiş kayıtla yeni çıkarılan kaydın
    sessizce ayrışması demekti.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.depolama import VERITABANI_URL, Temel, kaydet  # noqa: E402
from src.preprocessing.normalizasyon import birim_belirle  # noqa: E402
from src.schema import ALAN_BOYUTLARI, Kampanya  # noqa: E402


def ham_kayitlari_oku(url: str) -> list[dict]:
    """`tam_kayit` JSON'larını ORM'i atlayarak okur.

    ORM kullanılamaz: tablo eski şemada, model yeni sütunları bekliyor.
    Göçün doğası bu — kendi hedefinden önceki hâli okumak zorunda.
    """
    motor = create_engine(url)
    with motor.connect() as baglanti:
        satirlar = baglanti.execute(text("SELECT tam_kayit FROM kampanyalar")).all()
    return [json.loads(s[0]) if isinstance(s[0], str) else s[0] for s in satirlar]


def _tarih_tipini_onar(ham: dict) -> None:
    """JSON gidiş-dönüşünde kaybolan `date` tipini geri kurar.

    `Alan.deger` bilinçli olarak `Any` (alan başına farklı tip taşır), bu
    yüzden pydantic JSON'dan okurken tarihi ÇÖZMEZ — "2026-12-31" string
    olarak kalır ve SQLite `Date` sütunu onu reddeder.

    Göçün ortaya çıkardığı gerçek bir tip kaybı: `tam_kayit` yuvarlak yolu
    tip-sadık değil. Burada onarılıyor çünkü göç, kaydı JSON'dan yeniden
    kuran TEK yol. Yeni çıkarımda sorun yok — orada değer hiç JSON'a uğramaz.
    """
    alan = ham.get("kampanya_bitis")
    if isinstance(alan, dict) and isinstance(alan.get("deger"), str):
        alan["deger"] = date.fromisoformat(alan["deger"])


def birim_ekle(ham: dict) -> tuple[dict, list[str]]:
    """Bir kaydın sayısal alanlarına birim yazar. (kayıt, değişenler) döner."""
    degisenler: list[str] = []
    for alan_adi in ALAN_BOYUTLARI:
        alan = ham.get(alan_adi)
        if not isinstance(alan, dict) or alan.get("deger") is None:
            continue
        if alan.get("birim"):
            continue
        birim = birim_belirle(alan.get("ham_ifade"), alan_adi)
        if birim is not None:
            alan["birim"] = birim.value
            degisenler.append(f"{alan_adi}={alan['deger']!r} -> {birim.value}")
    return ham, degisenler


def calistir(deneme: bool, url: str = VERITABANI_URL) -> int:
    hamlar = ham_kayitlari_oku(url)
    if not hamlar:
        print("❌ Veritabanı boş.")
        return 1

    kampanyalar: list[Kampanya] = []
    sayac: Counter[str] = Counter()
    cozulemeyen: list[str] = []

    for ham in hamlar:
        _tarih_tipini_onar(ham)
        guncel, degisenler = birim_ekle(ham)
        for d in degisenler:
            sayac[d.split("=")[0]] += 1
        try:
            kampanyalar.append(Kampanya.model_validate(guncel))
        except ValueError as hata:
            # Boyut sözleşmesi reddetti: çok birimli bir alanın birimi ham
            # ifadeden çözülemedi. Sessizce atlamak, kaydı kaybetmek olurdu.
            cozulemeyen.append(f"{guncel.get('kampanya_id')}: {hata}")

    print(f"Okunan kayıt: {len(hamlar)} · doğrulanan: {len(kampanyalar)}")
    print("Birim yazılan alanlar:")
    for ad, n in sorted(sayac.items(), key=lambda x: -x[1]):
        print(f"   {ad:24} {n}")

    if cozulemeyen:
        print(f"\n🔴 Boyutu çözülemeyen {len(cozulemeyen)} kayıt:")
        for c in cozulemeyen[:10]:
            print(f"   {c}")
        print("   Bu kayıtlar YAZILMAZ — birimsiz sayı taşınamaz.")

    if deneme:
        print("\n(deneme modu — hiçbir şey yazılmadı)")
        return 0

    motor = create_engine(url)
    Temel.metadata.drop_all(motor, tables=[Temel.metadata.tables["kampanyalar"]])
    Temel.metadata.create_all(motor)
    kaydet(kampanyalar, url)
    print(f"\n✅ {len(kampanyalar)} kayıt yeni şemayla yazıldı (v1.2.0).")
    return 0 if not cozulemeyen else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Boyut göçü (şema v1.1.0 -> v1.2.0)")
    ap.add_argument("--deneme", action="store_true", help="yazmadan göster")
    return calistir(ap.parse_args().deneme)


if __name__ == "__main__":
    raise SystemExit(main())
