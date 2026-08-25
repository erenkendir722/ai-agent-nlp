"""LLM sağlayıcı katmanı — yerel Ollama ve SSB EVREN servisi.

NEDEN AYRI BİR KATMAN:
    Çıkarım artık iki yerde koşabiliyor: kurum içi Ollama ve TEKNOFEST'in
    tahsis ettiği EVREN servisi (8×H200, vLLM, BF16). İkisi de gerekli —
    EVREN ölçüm koşuları için (122B model, ~28 kat hızlı), Ollama ise
    servis düştüğünde ve hava boşluğu demosunda yedek.

    `LLMCikarici` hangisinde koştuğunu BİLMEZ. Sağlayıcı sözleşmesi tek
    bir yöntemdir: şema ver, geçerli JSON metni al. Ablasyon tablosuna
    "yerel 4B vs servis 122B" satırı bu yüzden eklenebilir.

ÖLÇÜLMÜŞ TUZAKLAR — üçü de SESSİZ bozar, hata vermez:

  1. `chat_template_kwargs` ÜST SEVİYEDE olmalı, `extra_body` içinde değil.
     Ağ geçidi `extra_body`'yi açmıyor; parametre sessizce düşüyor, akıl
     yürütme açık kalıyor ve üretim bütçesinin tamamını yiyor:
         extra_body içinde:  finish=length  tok=1500  içerik=""  reasoning=4496 krk
         üst seviyede:       finish=stop    tok=111   içerik=geçerli JSON
     Bu, `llm.ham_cikar`'daki `think=False` dersinin aynısıdır (SPRINT0 §104).

     AKIL YÜRÜTMEYİ AÇMAK DENENDİ VE REDDEDİLDİ (24 Ağu, 14 gerçek kayıt).
     Model kartı akıl yürütmeyi `llm-large`'ın güçlü yanı olarak gösteriyor,
     o yüzden ölçüldü. Bütçe iki katına (8192) çıkarılmasına rağmen:

                         doluluk   boş  kesik   süre/kayıt
         kapalı (4096)    %37,5     0     0       0,46 sn
         açık   (8192)    %32,1     2     2       9,16 sn

     Yani −5,4 puan doluluk, 4 bozuk yanıt ve **20 kat** süre. Sebep açık:
     yapısal çıkarımda muhakeme edilecek bir şey yok — şema kısıtı çıktıyı
     zaten zorluyor, model yalnız metinden kopyalıyor. Akıl yürütme burada
     doğruluk değil, bütçe tüketimi getiriyor.

     Kısacası: `enable_thinking` **her zaman `False`**. Açmak isteyen önce
     bu tabloyu yeniden üretsin.

  2. `guided_json` YOK SAYILIYOR. vLLM doğrudan konuşulsa çalışırdı ama
     önde bir ağ geçidi var (`system_fingerprint: vllm-0.27.1-tp4`).
     Ölçüm: şemaya modelin asla kendiliğinden seçmeyeceği bir enum
     (`ZZZ_YESIL`) konup istendi —
         guided_json                 -> düz metin döndü, şema uygulanmadı
         response_format.json_schema -> {"kampanya_turu": "ZZZ_YESIL"} ✅
     `guided_json` ile geçilseydi "şema geçerliliği 1,00" iddiası sessizce
     çökerdi: çıktı geçerli JSON olurdu ama ŞEMANIN JSON'ı olmazdı.

  3. `max_tokens` 4096. 2048'de uzun kampanya metinlerinde 24 kayıtta 1
     `finish_reason=length` ile kesiliyordu. `_kismi_json_kurtar` bunu
     kurtarıyor ama kurtarma kaybı olmayan yol değildir.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Protocol

log = logging.getLogger(__name__)

# --- Ortam anahtarları -----------------------------------------------------

SAGLAYICI_ADI = os.getenv("LLM_SAGLAYICI", "evren").strip().lower()

EVREN_TEMEL_URL = os.getenv("EVREN_TEMEL_URL", "https://evren-llmapi.ssyz.org.tr/v1")
EVREN_MODEL = os.getenv("EVREN_MODEL", "llm-large")
EVREN_ANAHTAR = os.getenv("EVREN_API_ANAHTARI", "")

OLLAMA_SUNUCU = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b-q4_K_M")

AZAMI_URETIM = 4096
"""Üretim bütçesi (token). 1200 -> 2048 -> 4096.

2048'de EVREN ölçümünde 24 kayıtta 1 tanesi `finish_reason=length` ile
cümlenin ortasında kesiliyordu. `_kismi_json_kurtar` bunu kurtarıyor, ama
kurtarma kayıpsız yol değildir — kesilen alan gerçekten kaybolur."""

SICAKLIK = 0.0
"""Örnekleme sıcaklığı. 0,1'den sıfıra indirildi (S-20).

ÖLÇÜLEN SORUN: `temperature=0,1` ile aynı kod, aynı girdi ve aynı model iki
koşu arasında **6/96 kayıtta** farklı sınıflandırma üretiyordu; dördü altın
sette, üçü doğrudan yanlışa dönüyordu. Tek başına bedeli −0,006 makro-F1 —
hedefe olan farktan büyük.

Sıfır sıcaklık üretimi açgözlü (greedy) hâle getirir: her adımda en yüksek
olasılıklı token seçilir, örnekleme devre dışı kalır. Yapılandırılmış
çıkarımda bu standarttır ve kaliteyi düşürmez; şema kısıtı çıktıyı zaten
zorluyor, sıcaklığın kattığı tek şey gürültüydü."""

SABIT_TOHUM = 20260820
"""Örnekleyici tohumu. Değeri anlamlı değildir, sabit olması anlamlıdır.

Yerelde (llama.cpp) determinizmi sağlayan asıl ayar sıcaklıktır; tohum eşit
olasılıklı iki token'da bağın nasıl çözüldüğünü sabitler.

⚠️  EVREN'DE DETERMİNİZM GARANTİ DEĞİLDİR — ÖLÇÜLDÜ.
    `temperature=0` ve bu tohumla, aynı girdi 5 kez gönderildiğinde
    **5 kayıttan 3'ü** bayt düzeyinde farklı çıktı verdi. Sebep örnekleme
    değil: ortak vLLM sunucusunda sürekli yığınlama (continuous batching)
    yığın bileşimine göre kayan nokta indirgeme sırasını değiştirir, MoE
    yönlendirmesi de buna eklenir. Tohum bunu düzeltemez, çünkü açgözlü
    üretimde örnekleyici zaten devrede değildir.

    ANCAK — 8 kayıt × 4 koşuluk ölçümde oynayan alanların TAMAMI serbest
    metindi (`kampanya_kosullari` 4 kez, `kampanya_avantaji` 1 kez).
    Sayısal veya enum alanlarda **sıfır** sapma görüldü. Yani:

        bayt düzeyinde tekrarlanabilirlik : ✗ kayboldu
        ölçülen metriklerde tekrarlanabilirlik : ✓ korunuyor (bu örneklemde)

    `docs/SONUCLAR.md` sayıları yine de yeniden üretilebilir kalır, çünkü
    kaynakları işlenmiş veritabanıdır (`data/katilim.db`, depoda) — modelin
    o anki çıktısı değil. Ablasyon koşularında da her yapılandırmanın kendi
    `.db` dosyası saklanır.

    Bayt düzeyinde tekrarlanabilirlik şart olduğunda: `LLM_SAGLAYICI=ollama`."""

ZAMAN_ASIMI = 300.0


class Saglayici(Protocol):
    """Şema kısıtlı üretim sözleşmesi.

    `uret` GEÇERLİ JSON METNİ döndürmek zorunda değildir — kesilmiş çıktı da
    dönebilir. Ayrıştırma ve kurtarma `llm.ham_cikar`'ın işidir; sağlayıcı
    yalnız taşıma katmanıdır.
    """

    ad: str
    model: str

    def uret(self, sistem: str, kullanici: str, sema: dict[str, Any]) -> str: ...


class OllamaSaglayici:
    """Kurum içi Ollama. Hava boşluğu demosunun ve yedek yolun sağlayıcısı."""

    ad = "ollama"

    def __init__(self, model: str | None = None, sunucu: str | None = None) -> None:
        import ollama

        self.model = model or OLLAMA_MODEL
        self.istemci = ollama.Client(host=sunucu or OLLAMA_SUNUCU)

    def uret(self, sistem: str, kullanici: str, sema: dict[str, Any]) -> str:
        yanit = self.istemci.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": sistem},
                {"role": "user", "content": kullanici},
            ],
            format=sema,
            think=False,  # bkz. modül başlığı, tuzak 1
            options={
                "temperature": SICAKLIK,
                "seed": SABIT_TOHUM,
                "num_predict": AZAMI_URETIM,
            },
        )
        return yanit["message"]["content"]


class EvrenSaglayici:
    """SSB EVREN — OpenAI uyumlu, 8×H200 üzerinde vLLM.

    `httpx` kullanılıyor; `openai` paketi BİLEREK eklenmedi. Kullandığımız
    yüzey tek bir POST'tur ve yeni her bağımlılık `make lisanslar`
    denetimine yeni bir satır ekler.
    """

    ad = "evren"

    def __init__(
        self,
        model: str | None = None,
        temel_url: str | None = None,
        anahtar: str | None = None,
    ) -> None:
        import httpx

        self.model = model or EVREN_MODEL
        self.temel_url = (temel_url or EVREN_TEMEL_URL).rstrip("/")
        anahtar = anahtar if anahtar is not None else EVREN_ANAHTAR
        if not anahtar:
            raise RuntimeError(
                "EVREN_API_ANAHTARI tanımlı değil. `.env` dosyasına ekleyin "
                "(.env.example'a DEĞİL — o dosya depoya giriyor). Yerel modelle "
                "koşmak için: LLM_SAGLAYICI=ollama"
            )
        self.istemci = httpx.Client(
            base_url=self.temel_url,
            headers={
                "Authorization": f"Bearer {anahtar}",
                "Content-Type": "application/json",
            },
            timeout=ZAMAN_ASIMI,
        )

    def uret(self, sistem: str, kullanici: str, sema: dict[str, Any]) -> str:
        govde = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sistem},
                {"role": "user", "content": kullanici},
            ],
            "max_tokens": AZAMI_URETIM,
            "temperature": SICAKLIK,
            "seed": SABIT_TOHUM,
            # ÜST SEVİYE — `extra_body` içinde sessizce düşer (tuzak 1)
            "chat_template_kwargs": {"enable_thinking": False},
            # `guided_json` DEĞİL — ağ geçidi onu yok sayıyor (tuzak 2)
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "kampanya", "schema": sema, "strict": True},
            },
        }
        yanit = self.istemci.post("/chat/completions", json=govde)
        yanit.raise_for_status()
        veri = yanit.json()
        secim = veri["choices"][0]
        if secim.get("finish_reason") == "length":
            log.warning(
                "Üretim bütçesi doldu (%s tok) — kısmi JSON kurtarmaya kalıyor",
                veri.get("usage", {}).get("completion_tokens"),
            )
        return secim["message"].get("content") or ""

    def kapat(self) -> None:
        self.istemci.close()


def saglayici_kur(ad: str | None = None, model: str | None = None) -> Saglayici:
    """Ortama göre sağlayıcı seçer.

    `model` verilirse seçilen sağlayıcının modeli olarak yorumlanır —
    `--model llm-fast` ile `--model qwen3.5:4b-q4_K_M` aynı bayrağı paylaşır,
    çünkü ikisi de "bu sağlayıcıdaki model" demektir.
    """
    ad = (ad or SAGLAYICI_ADI).strip().lower()
    if ad == "ollama":
        return OllamaSaglayici(model=model)
    if ad == "evren":
        return EvrenSaglayici(model=model)
    raise ValueError(f"Bilinmeyen LLM sağlayıcı: {ad!r}. Beklenen: 'evren' veya 'ollama'.")


__all__ = [
    "AZAMI_URETIM",
    "EvrenSaglayici",
    "OllamaSaglayici",
    "SABIT_TOHUM",
    "SICAKLIK",
    "Saglayici",
    "saglayici_kur",
]


def _dogrula() -> int:
    """`make saglayici-dogrula` — bağlantıyı ve ŞEMA KISITINI sınar.

    Şema kısıtı, ağ geçidi tarafında sessizce yok sayılabilen tek şeydir
    (`guided_json` başına gelen tam olarak budur). Bu yüzden bağlantı testi
    yetmez: modele, metinde KARŞILIĞI OLMAYAN bir enum değerini üretmesi
    dayatılır. Şema gerçekten uygulanıyorsa model başka bir şey YAZAMAZ.
    """
    # Windows konsolu cp1254; aşağıdaki ✅/❌ işaretleri orada
    # UnicodeEncodeError fırlatıyordu — sınama GEÇTİĞİ hâlde son satırda
    # yığın izi basıyordu. Yalnız bu CLI yolunda yapılır: modül içe
    # aktarıldığında (16 işçili çıkarım, Streamlit) stdout'a dokunulmaz.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tuzak = {
        "type": "object",
        "properties": {"kampanya_turu": {"type": "string", "enum": ["ZZZ_MOR", "ZZZ_YESIL"]}},
        "required": ["kampanya_turu"],
    }
    try:
        s = saglayici_kur()
    except Exception as hata:
        print(f"❌ Sağlayıcı kurulamadı: {hata}")
        return 1

    print(f"sağlayıcı : {s.ad}\nmodel     : {s.model}")
    try:
        cikti = s.uret(
            "Kampanyayı sınıflandır. Yalnız JSON döndür.",
            "Aylık %2,05 kâr payı ile konut finansmanı.",
            tuzak,
        )
    except Exception as hata:
        print(f"❌ Çağrı başarısız: {hata}")
        return 1

    try:
        secim = json.loads(cikti).get("kampanya_turu")
    except json.JSONDecodeError:
        print(f"❌ Geçersiz JSON döndü: {cikti[:200]!r}")
        return 1

    if secim in ("ZZZ_MOR", "ZZZ_YESIL"):
        print(f"✅ Şema kısıtı uygulanıyor (model {secim!r} üretmek zorunda kaldı).")
        return 0
    print(
        f"❌ ŞEMA KISITI UYGULANMIYOR — model {secim!r} döndürdü.\n"
        "   Çıktı geçerli JSON olsa bile ŞEMANIN JSON'ı değil; "
        "'şema geçerliliği 1,00' iddiası bu hâlde geçersizdir."
    )
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_dogrula())
