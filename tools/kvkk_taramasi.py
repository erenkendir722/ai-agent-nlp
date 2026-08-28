"""KVKK taraması — toplanan ham metinde kişisel veri var mı? (veri toplama etiği kanıtı)

NEDEN BİR CÜMLE YETMEZ:
    `docs/VERI_METODOLOJISI.md` "kişisel veri toplanmaz" diyor. Bu bir NİYET
    beyanıdır: toplayıcı kişisel veri hedeflemez. Ama toplanan şey kamuya açık
    sayfa metnidir ve bankalar o sayfalara iletişim bilgisi, örnek form değeri,
    kurumsal IBAN koyar. Niyet ile SONUÇ arasındaki farkı ancak tarama gösterir.

    Jüri "KVKK açısından durum ne?" diye sorduğunda gösterilecek şey, niyet
    beyanı değil, korpusun taranmış hâli olmalıdır.

AYRIM ŞU: kişisel veri, KİMLİĞİ BELİRLİ/BELİRLENEBİLİR GERÇEK KİŞİYE aittir.
Bankanın kurumsal e-postası, KEP adresi, kurumsal IBAN'ı ve müşteri hizmetleri
hattı tüzel kişiye aittir — kişisel veri değildir. Bu yüzden rapor bulguları
sayar ama ikisini ayırır:

  * ŞÜPHELİ  — sağlama toplamı TUTAN T.C. kimlik numarası. Gerçek bir kişiyi
    işaret eder; bulunursa iş durur, sayfa korpustan çıkarılır.
  * KURUMSAL — e-posta / IBAN / telefon. Sayılır, örneklenir, MASKELENİR.

MASKELEME BİLİNÇLİDİR: kurumsal bile olsa iletişim bilgisini bir kanıt
belgesine tam hâliyle yazmak, veriyi ikinci kez yayımlamaktır. Rapor
e-postaların yalnız alan adını, IBAN ve telefonların yalnız son dört hanesini
gösterir; tam değer ham kayıtta zaten durur ve oradan denetlenebilir.

KULLANIM:
    python tools/kvkk_taramasi.py            # rapor üret
    python tools/kvkk_taramasi.py --kati     # şüpheli bulguda çıkış kodu 1
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

HAM_DIZIN = KOK / "data" / "raw"
RAPOR_YOLU = KOK / "docs" / "kanit" / "KVKK_TARAMASI.md"

EPOSTA = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
IBAN = re.compile(r"(?i)\bTR\s?\d{2}[\s\d]{20,30}")
CEP = re.compile(r"(?<!\d)(?:\+90|0)?\s?\(?5\d{2}\)?[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}(?!\d)")
ONBIR_HANE = re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)")


def tckn_gecerli_mi(numara: str) -> bool:
    """T.C. kimlik numarası sağlama toplamı.

    Örnek form değerleri (`11111111111`, `12345678901`) bu sınamayı GEÇEMEZ.
    Ayrım bu yüzden önemli: onları kişisel veri saymak yanlış alarm üretir,
    gerçek bir numarayı kaçırmak ise asıl hatadır.
    """
    if len(numara) != 11 or not numara.isdigit() or numara[0] == "0":
        return False
    hane = [int(k) for k in numara]
    tek = hane[0] + hane[2] + hane[4] + hane[6] + hane[8]
    cift = hane[1] + hane[3] + hane[5] + hane[7]
    if (tek * 7 - cift) % 10 != hane[9]:
        return False
    return sum(hane[:10]) % 10 == hane[10]


def _maskele(deger: str, tur: str) -> str:
    deger = deger.strip()
    if tur == "e-posta":
        return "…@" + deger.split("@")[-1]
    haneler = re.sub(r"\D", "", deger)
    return f"…{haneler[-4:]}" if len(haneler) >= 4 else "…"


def tara(ham_dizin: Path = HAM_DIZIN) -> dict:
    """Ham kayıtların başlık ve gövde metnini tarar."""
    bulgular: dict[str, Counter] = defaultdict(Counter)
    supheliler: list[dict] = []
    ornek_form_degerleri: Counter = Counter()
    kayit_sayisi = 0

    for yol in sorted(ham_dizin.glob("*/*.json")):
        try:
            kayit = json.loads(yol.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        kayit_sayisi += 1
        metin = f"{kayit.get('baslik', '')} {kayit.get('govde_metin', '')}"

        for deger in EPOSTA.findall(metin):
            bulgular["e-posta"][_maskele(deger, "e-posta")] += 1
        for deger in IBAN.findall(metin):
            bulgular["IBAN"][_maskele(deger, "IBAN")] += 1
        for deger in CEP.findall(metin):
            bulgular["cep telefonu"][_maskele(deger, "cep telefonu")] += 1
        for deger in ONBIR_HANE.findall(metin):
            if tckn_gecerli_mi(deger):
                supheliler.append(
                    {
                        "tur": "T.C. kimlik numarası (sağlama toplamı tutuyor)",
                        "kayit": yol.name,
                        "banka_kodu": kayit.get("banka_kodu"),
                        "url": kayit.get("url"),
                        "maskeli": _maskele(deger, "tckn"),
                    }
                )
            else:
                ornek_form_degerleri[deger] += 1

    return {
        "uretildi": datetime.now().astimezone().isoformat(timespec="seconds"),
        "kayit_sayisi": kayit_sayisi,
        "bulgular": {tur: dict(sayac) for tur, sayac in bulgular.items()},
        "ornek_form_degerleri": dict(ornek_form_degerleri),
        "supheliler": supheliler,
    }


def rapor_uret(veri: dict) -> str:
    satirlar = [
        "# KVKK Taraması — toplanan metinde kişisel veri var mı?",
        "",
        f"_Otomatik üretildi: {veri['uretildi']} · `tools/kvkk_taramasi.py`_",
        "",
        "Bu rapor veri toplama etiği kanıtı kapsamındadır ve",
        "`docs/kanit/VERI_TOPLAMA_ETIGI.md` tarafından kanıt olarak gösterilir.",
        "",
        f"Taranan ham kayıt: **{veri['kayit_sayisi']}** (`data/raw/*/*.json` — başlık + gövde metni).",
        "",
        "## Sonuç",
        "",
    ]

    if veri["supheliler"]:
        satirlar += [
            f" **{len(veri['supheliler'])} şüpheli bulgu var — gerçek kişiye ait olabilir.**",
            "",
            "| Tür | Banka | Kayıt | Maskeli değer |",
            "|---|---|---|---|",
        ]
        satirlar += [
            f"| {b['tur']} | {b['banka_kodu']} | `{b['kayit']}` | `{b['maskeli']}` |"
            for b in veri["supheliler"]
        ]
        satirlar += [
            "",
            "**Yapılacak:** ilgili kayıt korpustan çıkarılır, kaynak URL `banks.yaml`",
            "notuna işlenir. Şüpheli bulgu varken veri seti yayımlanmaz.",
            "",
        ]
    else:
        satirlar += [
            " **Kimliği belirli gerçek kişiye ait veri bulunmadı.**",
            "",
            "Sağlama toplamı tutan tek bir T.C. kimlik numarası yok. Bulunan 11 haneli",
            "sayılar örnek form değerleridir (aşağıda) — sağlama toplamını geçemezler.",
            "",
        ]

    if veri["ornek_form_degerleri"]:
        dokum = ", ".join(
            f"`{deger}` ({sayi} kez)"
            for deger, sayi in sorted(
                veri["ornek_form_degerleri"].items(), key=lambda ikili: -ikili[1]
            )[:5]
        )
        satirlar += [f"11 haneli sayı bulguları: {dokum}.", ""]

    satirlar += [
        "## Kurumsal iletişim bilgileri",
        "",
        "Kampanya sayfalarında bankanın kendi iletişim bilgileri geçer. Bunlar",
        "**tüzel kişiye** aittir ve KVKK anlamında kişisel veri değildir; yine de",
        "sayılır ve maskelenerek raporlanır — kanıt belgesinde ikinci kez",
        "yayımlanmasınlar diye.",
        "",
        "| Tür | Farklı değer | Toplam geçiş | Örnekler (maskeli) |",
        "|---|---|---|---|",
    ]
    for tur in ("e-posta", "IBAN", "cep telefonu"):
        sayac = veri["bulgular"].get(tur, {})
        ornekler = ", ".join(f"`{d}`" for d, _ in sorted(sayac.items(), key=lambda i: -i[1])[:4])
        satirlar.append(
            f"| {tur} | {len(sayac)} | {sum(sayac.values())} | {ornekler or '—'} |"
        )

    satirlar += [
        "",
        "## Kapsam ve sınırlar",
        "",
        "- Tarama **desen tabanlıdır**: ad-soyad gibi serbest metin kimlik bilgisini",
        "  yakalamaz. Toplayıcı yalnız kamuya açık kampanya sayfalarını çektiği ve",
        "  giriş gerektiren hiçbir alana girmediği için müşteri verisi bu korpusa",
        "  girmez; tarama bunu **destekler**, tek başına kanıtlamaz.",
        "- Tarandığı an ne varsa odur: yeni çekimden sonra yeniden koşulmalıdır.",
        "",
        "```bash",
        "make kanit-kvkk          # bu raporu yeniler",
        "make kanit-kvkk kati=1   # şüpheli bulguda çıkış kodu 1 (teslim öncesi)",
        "```",
    ]
    return "\n".join(satirlar) + "\n"


def main(argv: list[str] | None = None) -> int:
    # Windows konsolu cp1254; rapor işaretleri orada çökmesin. Yalnız CLI
    # yolunda — modül içe aktarıldığında stdout'a dokunulmaz (bkz. robots_kanit).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ayristirici = argparse.ArgumentParser(description="KVKK kişisel veri taraması")
    ayristirici.add_argument(
        "--kati", action="store_true", help="şüpheli bulgu varsa çıkış kodu 1 döndür"
    )
    secenekler = ayristirici.parse_args(argv)

    veri = tara()
    RAPOR_YOLU.parent.mkdir(parents=True, exist_ok=True)
    RAPOR_YOLU.write_text(rapor_uret(veri), encoding="utf-8")

    print(f" {RAPOR_YOLU.relative_to(KOK)} yazıldı ({veri['kayit_sayisi']} kayıt tarandı)")
    if veri["supheliler"]:
        print(f" {len(veri['supheliler'])} şüpheli bulgu — rapora bakın.")
        return 1 if secenekler.kati else 0
    print("   Kimliği belirli gerçek kişiye ait veri bulunmadı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
