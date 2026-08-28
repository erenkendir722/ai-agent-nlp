"""«Canlı Boru Hattı» sayfasının çizim bileşenleri — hepsi SAF işlev.

Her işlev HTML dizesi döner, hiçbiri `st.*` çağırmaz. İki sebebi var:
saf oldukları için testte doğrulanabiliyorlar (`tests/test_akis_bilesenleri.py`)
ve çizimin nereden çağrıldığı önemsiz hâle geliyor.

DIŞ KAYNAKLI METİN KAÇIRILIR. Buraya banka sayfa başlığı, URL ve hata mesajı
giriyor — üçü de bizim yazmadığımız, uzak siteden gelen metin. `unsafe_allow_
html=True` ile basıldıkları için `html.escape` atlanırsa banka sayfasındaki bir
`<script>` arayüzde koşar. Testler bunu ayrıca sınıyor.

DIŞ VARLIK YOK. Yalnız `@keyframes` ve satır içi stil — CDN, dış font, dış JS
yok. `ui_utils.inject_custom_css` ile aynı kısıt: demo hava boşluğunda koşuyor.

BİÇİMLENDİRME NOTU: HTML girintisiz üretilir. Streamlit markdown'ı 4 boşlukla
girintili satırı KOD BLOĞU sayar; girintili HTML ekrana kod olarak basılırdı.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Literal

from app.ui_utils import RENK_ANA

# Palet TEK KAYNAKTAN. Burada `YESIL = "#00A86B"` diye elle yazılıydı ve
# «ui_utils ile aynı» diyen bir yorum taşıyordu — o yorumun kendisi ikinci
# kopyanın itirafıydı: birini değiştiren diğerini unutur.
YESIL = RENK_ANA
KART_ZEMIN = "rgba(37, 37, 45, 0.7)"
KENAR = "rgba(255, 255, 255, 0.15)"
METIN = "#E0E0E0"
SOLUK = "#9A9AA5"

BankaAsamasi = Literal["bekliyor", "taraniyor", "bitti", "atlandi", "hata"]
OlayTuru = Literal["bilgi", "sayfa", "kayit", "atlandi", "hata"]

_ASAMA_BICIMI: dict[str, tuple[str, str]] = {
    # asama: (kenar rengi, rozet)
    "bekliyor": ("rgba(255,255,255,0.12)", "○"),
    "taraniyor": (YESIL, "◉"),
    "bitti": (YESIL, "✓"),
    "atlandi": ("#E0A800", "⤼"),
    "hata": ("#E05A5A", "!"),
}

_OLAY_RENGI: dict[str, str] = {
    "bilgi": SOLUK,
    "sayfa": YESIL,
    "kayit": YESIL,
    "atlandi": "#E0A800",
    "hata": "#E05A5A",
}

AZAMI_GUNLUK = 12
"""Günlükte gösterilen satır sayısı. Fazlası ekranı kaydırır, okunmaz olur."""


@dataclass(frozen=True)
class BankaDurumu:
    """Izgaradaki tek banka kartı."""

    ad: str
    asama: BankaAsamasi = "bekliyor"
    sayfa: int = 0
    toplam: int = 0
    mesaj: str = ""
    aktif: bool = False
    """Şu an ÜZERİNDE İŞLEM YAPILAN banka mı — nabzı yalnız bu kart atar.

    `taraniyor` aşaması tek başına yetmiyor: demo tavanıyla kesilen banka
    «bitti» olayı üretmediği için kartı `taraniyor`da kalıyordu ve bir sonraki
    bankaya geçildiğinde ikisi birden yanıp sönüyordu. Aktiflik `topla`'nın
    sırayla ilerlemesinden türetiliyor (`boru_durumu`), aşamadan değil.
    """

    alt: str = ""
    """Kartın alt satırı. Boşsa `sayfa`/`toplam`'dan türetilir.

    Tazelik sekmesi burada «12 URL · 2 değişti» gibi kendi özetini yazıyor;
    o sekmede sayılan şey sayfa değil denetlenen adres.
    """


@dataclass(frozen=True)
class GunlukSatiri:
    """Olay günlüğündeki tek satır."""

    tur: OlayTuru
    metin: str
    etiket: str = ""


@dataclass(frozen=True)
class KayitOzeti:
    """Çıkarımdan geçmiş tek kayıt — ölçülen değerlerle."""

    banka: str
    doluluk: float
    guven: float
    sure: float
    url: str = ""


def akis_css() -> str:
    """Sayfanın keyframe'leri. Sayfa başında bir kez basılır."""
    return (
        "<style>"
        "@keyframes kl-nabiz{"
        "0%{box-shadow:0 0 0 0 rgba(0,168,107,0.45);}"
        "70%{box-shadow:0 0 0 10px rgba(0,168,107,0);}"
        "100%{box-shadow:0 0 0 0 rgba(0,168,107,0);}}"
        "@keyframes kl-kayan{"
        "0%{background-position:0 0;}100%{background-position:36px 0;}}"
        "@keyframes kl-belir{"
        "from{opacity:0;transform:translateY(-6px);}"
        "to{opacity:1;transform:translateY(0);}}"
        "@keyframes kl-supurme{"
        "0%{left:-30%;}100%{left:100%;}}"
        f".kl-kart{{background:{KART_ZEMIN};border:1px solid {KENAR};"
        "border-radius:10px;padding:10px 12px;transition:all .3s ease;}"
        ".kl-nabizli{animation:kl-nabiz 1.6s infinite;}"
        ".kl-izgara{display:grid;gap:10px;"
        "grid-template-columns:repeat(auto-fill,minmax(150px,1fr));}"
        f".kl-kart-ad{{color:{METIN};font-weight:600;font-size:.9rem;}}"
        f".kl-kart-alt{{color:{SOLUK};font-size:.76rem;margin-top:3px;"
        "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
        f".kl-cubuk{{height:10px;border-radius:6px;background:rgba(255,255,255,.07);"
        "overflow:hidden;}"
        f".kl-cubuk-ic{{height:100%;background-image:repeating-linear-gradient("
        f"45deg,{YESIL} 0 10px,rgba(0,168,107,.55) 10px 18px);"
        "background-size:36px 36px;animation:kl-kayan 1s linear infinite;"
        "transition:width .4s ease;}"
        ".kl-cubuk-ic.kl-durgun{animation:none;}"
        f".kl-gunluk{{background:rgba(0,0,0,.28);border:1px solid {KENAR};"
        "border-radius:10px;padding:8px 10px;font-size:.8rem;"
        "font-family:Consolas,'Courier New',monospace;max-height:270px;"
        "overflow-y:auto;}"
        ".kl-gunluk-kapali{max-height:none;overflow-y:hidden;}"
        ".kl-gunluk-satir{animation:kl-belir .35s ease;padding:2px 0;"
        "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
        f".kl-serit-kutu{{position:relative;overflow:hidden;background:{KART_ZEMIN};"
        f"border:1px solid {KENAR};border-radius:10px;padding:10px 12px;}}"
        ".kl-supurge{position:absolute;top:0;bottom:0;width:30%;"
        "background:linear-gradient(90deg,transparent,rgba(0,168,107,.16),transparent);"
        "animation:kl-supurme 2.2s linear infinite;}"
        f".kl-oran{{height:6px;border-radius:4px;background:rgba(255,255,255,.08);"
        "overflow:hidden;}"
        ".kl-oran-ic{height:100%;border-radius:4px;}"
        "</style>"
    )


def _yuzde(oran: float) -> float:
    """0–1 aralığına kırpar ve yüzdeye çevirir — CSS'e taşan genişlik gitmesin."""
    return max(0.0, min(1.0, float(oran))) * 100


def ilerleme_cubugu(tamamlanan: int, toplam: int, *, akiyor: bool = True) -> str:
    """Ölçülen ilerleme. `toplam` bilinmiyorsa (0) çubuk BOŞ kalır.

    Bilinmeyen toplamı «%100» ya da tahminî bir değerle doldurmak, sayfanın
    tek yasağını çiğnerdi: uydurma ilerleme yok.
    """
    oran = _yuzde(tamamlanan / toplam) if toplam > 0 else 0.0
    durgun = "" if akiyor else " kl-durgun"
    etiket = f"{tamamlanan} / {toplam}" if toplam > 0 else f"{tamamlanan} / ?"
    return (
        f'<div class="kl-cubuk"><div class="kl-cubuk-ic{durgun}" '
        f'style="width:{oran:.1f}%"></div></div>'
        f'<div class="kl-kart-alt">{html.escape(etiket)}</div>'
    )


def banka_izgarasi(durumlar: list[BankaDurumu]) -> str:
    """Banka kartları ızgarası. Boş liste kırılmaz — boş ızgara döner."""
    if not durumlar:
        return '<div class="kl-izgara"></div>'

    kartlar: list[str] = []
    for durum in durumlar:
        renk, rozet = _ASAMA_BICIMI.get(durum.asama, _ASAMA_BICIMI["bekliyor"])
        # Nabız YALNIZ üzerinde işlem yapılan kartta. Toplama sırayla
        # ilerlediği için aynı anda birden fazla kartın yanıp sönmesi
        # gerçeği yanlış gösterirdi.
        ek_sinif = " kl-nabizli" if (durum.asama == "taraniyor" and durum.aktif) else ""
        if durum.alt:
            alt = durum.alt
        elif durum.toplam > 0:
            alt = f"{durum.sayfa}/{durum.toplam} sayfa"
        elif durum.sayfa > 0:
            alt = f"{durum.sayfa} sayfa"
        else:
            alt = durum.mesaj or "bekliyor"
        kartlar.append(
            f'<div class="kl-kart{ek_sinif}" style="border-color:{renk}">'
            f'<div class="kl-kart-ad"><span style="color:{renk}">{rozet}</span> '
            f"{html.escape(durum.ad)}</div>"
            f'<div class="kl-kart-alt" title="{html.escape(durum.mesaj)}">'
            f"{html.escape(alt)}</div>"
            "</div>"
        )
    return f'<div class="kl-izgara">{"".join(kartlar)}</div>'


def _gunluk_satiri(olay: GunlukSatiri) -> str:
    renk = _OLAY_RENGI.get(olay.tur, SOLUK)
    etiket = (
        f'<span style="color:{SOLUK}">{html.escape(olay.etiket)}</span> '
        if olay.etiket
        else ""
    )
    return (
        f'<div class="kl-gunluk-satir" title="{html.escape(olay.metin)}">'
        f'{etiket}<span style="color:{renk}">{html.escape(olay.metin)}</span>'
        "</div>"
    )


def olay_gunlugu(
    olaylar: list[GunlukSatiri], *, azami: int = AZAMI_GUNLUK, acik: bool = True
) -> str:
    """Son olaylar, YENİSİ ÜSTTE. Boş liste için bilgilendirici bir satır.

    `acik=False` KAPALI gösterimdir: yalnız en son olay, tek satır, kaydırma
    yok. Açıkken kutu kaydırılabilir hâle gelir ve `azami` satır çizilir.

    Açık/kapalı durumu BURADA tutulmaz — çağıran taraf `st.toggle` ile tutar.
    Sebebi ölçülmüş: canlı alan 0,4 saniyede bir yeniden çiziliyor; `<details>`
    ya da `st.expander` gibi istemci tarafında duran bir açıklık her çizimde
    kapanırdı. `session_state`'te duran bir anahtar yeniden çizimden etkilenmez.
    """
    if not olaylar:
        return (
            f'<div class="kl-gunluk kl-gunluk-kapali"><div class="kl-gunluk-satir" '
            f'style="color:{SOLUK}">— henüz olay yok —</div></div>'
        )

    if not acik:
        return (
            f'<div class="kl-gunluk kl-gunluk-kapali">{_gunluk_satiri(olaylar[-1])}</div>'
        )

    satirlar = [_gunluk_satiri(olay) for olay in list(reversed(olaylar))[:azami]]
    return f'<div class="kl-gunluk">{"".join(satirlar)}</div>'


def katman_hatti(sayaclar: dict[str, int], *, akiyor: bool = True) -> str:
    """KURAL → LLM → UZLAŞTIRICI şeritleri; sayaçlar ÖLÇÜLEN alan sayıları.

    Üç şerit `UzlastirmaRaporu`'nun üç sayacına birebir karşılık gelir:
    yalnız kuraldan gelen, yalnız LLM'den gelen, iki katmanın uzlaştığı.
    """
    hatlar = (
        ("KURAL", "kural", "regex · milisaniye"),
        ("LLM", "llm", "Qwen · EVREN/Ollama"),
        ("UZLAŞTIRICI", "hibrit", "iki katmanın kesiştiği"),
    )
    en_buyuk = max((sayaclar.get(anahtar, 0) for _, anahtar, _ in hatlar), default=0)

    parcalar: list[str] = []
    for baslik, anahtar, aciklama in hatlar:
        deger = int(sayaclar.get(anahtar, 0))
        oran = _yuzde(deger / en_buyuk) if en_buyuk > 0 else 0.0
        supurge = '<div class="kl-supurge"></div>' if akiyor else ""
        parcalar.append(
            '<div class="kl-serit-kutu" style="margin-bottom:8px">'
            f"{supurge}"
            '<div style="position:relative;display:flex;justify-content:space-between;'
            'align-items:baseline">'
            f'<span class="kl-kart-ad">{html.escape(baslik)}</span>'
            f'<span class="kl-kart-ad" style="color:{YESIL}">{deger}</span>'
            "</div>"
            f'<div class="kl-kart-alt">{html.escape(aciklama)}</div>'
            '<div class="kl-oran" style="margin-top:6px">'
            f'<div class="kl-oran-ic" style="width:{oran:.1f}%;background:{YESIL}">'
            "</div></div></div>"
        )
    return "".join(parcalar)


def kayit_seridi(kayitlar: list[KayitOzeti], *, azami: int = 6) -> str:
    """Son işlenen kayıtlar: banka · doluluk · güven · ölçülen süre."""
    if not kayitlar:
        return (
            f'<div class="kl-kart" style="color:{SOLUK}">'
            "— henüz kayıt işlenmedi —</div>"
        )

    satirlar: list[str] = []
    for kayit in list(reversed(kayitlar))[:azami]:
        satirlar.append(
            '<div class="kl-kart" style="margin-bottom:8px;animation:kl-belir .35s ease">'
            '<div style="display:flex;justify-content:space-between;align-items:baseline">'
            f'<span class="kl-kart-ad">{html.escape(kayit.banka)}</span>'
            f'<span class="kl-kart-alt">{kayit.sure:.2f} sn</span>'
            "</div>"
            f'<div class="kl-kart-alt" title="{html.escape(kayit.url)}">'
            f"doluluk %{_yuzde(kayit.doluluk):.0f} · güven {kayit.guven:.2f}</div>"
            # İki çubuğun ne olduğu imleçle de okunabilsin: renk tek başına
            # anlatmıyor, sayfada bir kez sorulup öğrenilmesi gerekti.
            '<div class="kl-oran" style="margin-top:5px" '
            f'title="doluluk: şemadaki alanların %{_yuzde(kayit.doluluk):.0f} kadarı '
            'dolduruldu">'
            f'<div class="kl-oran-ic" style="width:{_yuzde(kayit.doluluk):.1f}%;'
            f'background:{YESIL}"></div></div>'
            '<div class="kl-oran" style="margin-top:3px" '
            f'title="güven: çıkarılan alanların ortalama güven skoru {kayit.guven:.2f}">'
            f'<div class="kl-oran-ic" style="width:{_yuzde(kayit.guven):.1f}%;'
            'background:#4A90D9"></div></div>'
            "</div>"
        )
    return "".join(satirlar)


__all__ = [
    "AZAMI_GUNLUK",
    "BankaDurumu",
    "GunlukSatiri",
    "KayitOzeti",
    "akis_css",
    "banka_izgarasi",
    "ilerleme_cubugu",
    "katman_hatti",
    "kayit_seridi",
    "olay_gunlugu",
]
