"""Yüklem ajanı — kural katmanının kanıtsız iddialarını denetler.

ELEŞTİRMENDEN FARKI, VE NEDEN AYRI BİR AJAN:

    `ElestirmenAjani` şunu sorar: *"bu dizi ham metinde geçiyor mu?"*
    Deterministiktir, LLM kullanmaz, ve halüsinasyon savunmasının tamamıdır.
    **O dosyaya model sokulmaz** — sistemin en güçlü iddiası onun LLM'siz
    olmasıdır.

    Ama ölçüldü ki asıl kayıp orada değil. 24 Ağustos altın set denetiminde
    16 yanlış pozitifin **13'ü** kural katmanından geliyordu ve hepsinde sayı
    metinde GERÇEKTEN vardı:

        finansman_tutari_max = 125.000 TL   ← metinde var, ama o kampanyanın
                                              azami finansman tutarı değil
        vade_ay_max = 36 ay                 ← metinde var, ama başka bir
                                              ürünün vadesi
        tahsis_ucreti = %75                 ← metinde var, ama tahsis ücreti
                                              bir yüzde bile değil

    Yani eleştirmen doğru çalışıyordu: sorduğu soruya doğru cevap veriyordu.
    Sorun sorunun kendisiydi. Doğrulanan şey **varlık**, doğrulanması gereken
    **yüklem**: metin bu sayının BU ALANIN değeri olduğunu söylüyor mu?

    Varlık denetimi bir dizi aramasıdır — kod yapar. Yüklem denetimi cümlenin
    neyi neye yüklediğini anlamayı gerektirir — dil modeli yapar. İki ayrı
    soru, iki ayrı yöntem, iki ayrı ajan.

NEDEN YALNIZ KURAL-TEK DEĞERLERDE:

    Hibrit değerler (iki katman aynı sonuca vardı) zaten çapraz doğrulanmış.
    Ölçülen kesinlikleri: hibrit 0,870 · llm 0,820 · **kural-tek 0,696**.
    Kanıtı zayıf olan tek küme kural-tek; denetim oraya uygulanır. Bu bir
    ayrıcalık değil, kanıt seviyesine göre orantılı şüphedir.

RET DEĞİL, DÜZELTME — ölçümle öğrenildi:

    İlk sürüm yüklemi desteklenmeyen değeri DÜŞÜRÜYORDU. Eşli deneyde (çıkarım
    sabit, yalnız kapı açılıp kapandı) makro-F1 0,764 → 0,730'a indi. Sebep
    incelenince ilginç çıktı: ajan 8 değer reddetti, **5'i haklıydı**, 3'ü
    altın sete göre DOĞRU değerlerdi — ama o üçünün de kanıtı gerçekten
    bozuktu:

        finansman_tutari_max=400.000  kanıt: "1.200.001 TL- 2.000.000 TL 20% 12"
                                      (bir tablo satırı; gerçek dayanak
                                       metnin başka yerinde: "400.000 TL'ye kadar")
        masrafsiz_mi=True             kanıt: "000 TL ve üzeri taksitlendirmeye..."
                                      (kural, sayının ORTASINDAN yakalamış)

    Yani değerler doğruydu, kanıtları çöptü — tesadüfen doğru çıkmışlardı.
    Ajan haklıydı; onları düşürmek F1'i düşürdü çünkü altın set değere bakıyor,
    kanıta bakmıyor.

    Doğru davranış ikisini de kurtarmaktır: yüklem desteklenmiyorsa değeri atma,
    **modele o alanın değerini kanıtıyla sor**. Kural katmanı doğru sayıyı
    yanlış yerden bulmuşsa düzeltme aynı sayıyı doğru cümleyle geri getirir;
    sayı gerçekten yoksa alan boş kalır. Her iki durumda da kanıt zinciri sağlam.

AJAN KENDİ GEREKÇESİNİ UYDURAMAZ:

    Model yalnız "destekliyor mu?" demekle kalmaz, **kanıt cümlesini** de
    döndürmek zorundadır. O cümle ham metinde aranır; bulunamazsa cevap
    reddedilir. Yani ajan bir değeri onaylamak için gerekçe uyduramaz —
    eleştirmenin denetimi bu ajanın da üstünde kalır.

KAPATILABİLİR: `etkin=False`. Ablasyon tablosunun "yüklem ajanı yok" satırı
bununla ölçülür; ayrı kod yolu yazmak ölçümü karşılaştırılamaz kılardı.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.ajanlar.temel import AjanIzi, iz_tut
from src.alan_tanimlari import ALAN_TANIMLARI
from src.schema import KANIT_ZORUNLU_ALANLAR

log = logging.getLogger(__name__)

DENETLENEN_ALANLAR: frozenset[str] = KANIT_ZORUNLU_ALANLAR | {"masrafsiz_mi"}
"""Yüklem denetimine giren alanlar.

`KANIT_ZORUNLU_ALANLAR` (sayısal + tarihsel) artı `masrafsiz_mi`. Sınıflandırma
ve serbest metin alanları DIŞARIDA: onlarda "metin bu değeri şu alana yüklüyor
mu?" sorusunun karşılığı yok — enum etiketi metinde geçmez, özet zaten özettir.

Liste ALAN BAZLI SEÇİLMEDİ. Ölçümde bazı alanların kural kesinliği daha
düşüktü (`finansman_tutari_max` 0,33), ama yalnız onları denetlemek altın sete
uydurmak olurdu. Kural aynı: kanıtı tek katmandan gelen her sayısal değer
denetlenir."""

PENCERE = 400
"""Değerin çevresinden modele verilecek bağlam (karakter, iki yana).

Tüm sayfayı vermek yanlış olurdu: soru "bu sayfada 125.000 TL geçiyor mu?"
değil, "bu sayının geçtiği YERDE metin onu azami finansman tutarı olarak mı
tanımlıyor?" Bağlamı geniş tutmak tam da ayırt etmesi istenen gürültüyü geri
sokar."""

_SEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "destekliyor": {"type": "boolean"},
        "kanit_cumlesi": {"type": ["string", "null"]},
    },
    "required": ["destekliyor", "kanit_cumlesi"],
}

_DUZELTME_SEMASI: dict[str, Any] = {
    "type": "object",
    "properties": {
        "deger_ifadesi": {"type": ["string", "null"]},
    },
    "required": ["deger_ifadesi"],
}

_DUZELTME_SISTEMI = """Sen bir katılım bankacılığı metin madenciliği uzmanısın.
Sana bir metin parçası ve bir alan adı verilecek.

GÖREVİN: Metinde bu alanın değeri geçiyor mu? Geçiyorsa, değeri METİNDE
GEÇTİĞİ HÂLİYLE BİREBİR kopyala (biçimi değiştirme, yuvarlama, hesaplama yapma).

- Metinde bu alanın değeri YOKSA `deger_ifadesi` alanına null yaz.
- Başka bir alana ait bir sayıyı buraya yazma.
- Tahmin etme. Boş bırakmak yanlış cevap vermekten HER ZAMAN daha iyidir."""

_SISTEM = """Sen bir katılım bankacılığı metin denetçisisin.
Sana bir metin parçası, bir alan adı ve o alana atanmış bir değer verilecek.

TEK GÖREVİN: Metin, bu değerin O ALANIN değeri olduğunu söylüyor mu?

- Sayı metinde geçiyor olabilir ama BAŞKA bir şeyi anlatıyor olabilir
  (başka bir ürünün vadesi, bir tablo satırı, bir örnek hesaplama,
  ilgisiz bir tutar). Bu durumda destekliyor=false.
- Değeri o alana bağlayan bir ifade varsa destekliyor=true ve o cümleyi
  `kanit_cumlesi` alanına METİNDE GEÇTİĞİ HÂLİYLE BİREBİR kopyala.
- Emin değilsen destekliyor=false. Yanlış onay, kaçırmaktan pahalıdır.
- Cümle uydurma. `kanit_cumlesi` metinde birebir aranacak; uydurursan
  cevabın tamamı reddedilir."""


class YuklemAjani:
    """Değer ↔ alan yüklemi doğrulaması. LLM kullanır."""

    ad = "yuklem"
    llm_kullanir = True

    def __init__(self, saglayici: Any | None = None, *, etkin: bool = True) -> None:
        self.etkin = etkin
        self._saglayici = saglayici
        self.reddedilen: list[str] = []
        self.onaylanan = 0
        self.duzeltilen = 0

    @property
    def saglayici(self) -> Any:
        """Sağlayıcı ilk kullanımda kurulur.

        Tembel kurulum bilinçli: `etkin=False` ile koşan ablasyon satırı ve
        testler EVREN anahtarı olmadan da çalışabilmeli."""
        if self._saglayici is None:
            from src.extraction.saglayici import saglayici_kur

            self._saglayici = saglayici_kur()
        return self._saglayici

    def denetle(self, alan_adi: str, deger: Any, ham_ifade: str, metin: str) -> str | None:
        """Yüklem denetimi. Dönüş:

            None            → değer olduğu gibi kalsın (kabul, ya da denetim
                              yapılamadı; şüphede değer korunur)
            "" (boş dizi)   → alan boşaltılsın (metin bu alanı hiç anlatmıyor)
            başka bir dizi  → değer bu ham ifadeden YENİDEN türetilsin
                              (doğru sayı, yanlış kanıt durumunun düzeltmesi)
        """
        if not self.etkin or alan_adi not in DENETLENEN_ALANLAR:
            return None

        pencere = self._pencere(metin, ham_ifade)
        if pencere is None:
            # İfade metinde bulunamadı. Eleştirmenin işi bu; burada kararı
            # ona bırakıyoruz — iki ajan aynı şeyi iki kez reddetmesin.
            return None

        try:
            cevap = self._sor(alan_adi, deger, ham_ifade, pencere)
        except Exception as hata:  # servis hatası değeri düşürmemeli
            log.warning("Yüklem denetimi yapılamadı (%s): %s — değer korunuyor", alan_adi, hata)
            return None

        if cevap is None:
            return None

        destekliyor, kanit = cevap
        # Gerekçe denetimi: ajan kendi kanıtını uyduramaz.
        kanit_gecerli = bool(kanit) and "".join(kanit.split()) in "".join(metin.split())

        if destekliyor and kanit_gecerli:
            self.onaylanan += 1
            return None

        # Yüklem desteklenmiyor. Değeri ATMADAN önce doğrusunu SOR —
        # kural katmanı doğru sayıyı yanlış yerden bulmuş olabilir.
        try:
            duzeltme = self._duzelt(alan_adi, metin)
        except Exception as hata:
            log.warning("Düzeltme sorulamadı (%s): %s — değer korunuyor", alan_adi, hata)
            return None

        if duzeltme:
            self.duzeltilen += 1
            return duzeltme

        self.reddedilen.append(f"{alan_adi}={ham_ifade!r} yüklem desteklenmiyor, karşılığı da yok")
        return ""

    # -- iç -----------------------------------------------------------------

    @staticmethod
    def _pencere(metin: str, ham_ifade: str) -> str | None:
        konum = metin.find(ham_ifade)
        if konum == -1:
            sikistirilmis = "".join(ham_ifade.split())
            if not sikistirilmis or sikistirilmis not in "".join(metin.split()):
                return None
            konum = 0
        bas = max(0, konum - PENCERE)
        return metin[bas : konum + len(ham_ifade) + PENCERE]

    def _sor(
        self, alan_adi: str, deger: Any, ham_ifade: str, pencere: str
    ) -> tuple[bool, str | None] | None:
        tanim = ALAN_TANIMLARI.get(alan_adi, alan_adi)
        kullanici = (
            f"--- METİN ---\n{pencere}\n--- METİN SONU ---\n\n"
            f"Alan: {alan_adi} — {tanim}\n"
            f"Metinden alınan ifade: {ham_ifade!r}\n"
            f"Bu ifadeden çıkarılan değer: {deger!r}\n\n"
            f"Metin, bu değerin yukarıdaki alanın değeri olduğunu söylüyor mu?"
        )
        icerik = self.saglayici.uret(_SISTEM, kullanici, _SEMA)
        try:
            veri = json.loads(icerik)
        except json.JSONDecodeError:
            return None
        return bool(veri.get("destekliyor")), veri.get("kanit_cumlesi")

    def _duzelt(self, alan_adi: str, metin: str) -> str | None:
        """Alanın değerini metinden yeniden sorar. Bulamazsa None.

        Bağlam TÜM metindir, pencere değil: kural katmanının baktığı yer
        yanlış olduğu için buradayız. Aynı pencereyi vermek aynı hatayı
        tekrarlatırdı.
        """
        tanim = ALAN_TANIMLARI.get(alan_adi, alan_adi)
        kullanici = (
            f"--- METİN ---\n{metin[:12000]}\n--- METİN SONU ---\n\n"
            f"Alan: {alan_adi} — {tanim}\n\n"
            f"Bu alanın değeri metinde geçiyor mu? Geçiyorsa birebir kopyala."
        )
        icerik = self.saglayici.uret(_DUZELTME_SISTEMI, kullanici, _DUZELTME_SEMASI)
        try:
            ifade = json.loads(icerik).get("deger_ifadesi")
        except json.JSONDecodeError:
            return None
        if not ifade or not isinstance(ifade, str):
            return None
        # Uydurulmuş ifade kabul edilmez — eleştirmenin ölçütü burada da geçerli.
        if "".join(ifade.split()) not in "".join(metin.split()):
            return None
        return ifade

    def calistir(self, girdi: dict[str, object]) -> tuple[dict[str, object], AjanIzi]:
        with iz_tut(self.ad, llm=self.llm_kullanir) as iz:
            kabul = self.denetle(
                str(girdi["alan_adi"]),
                girdi.get("deger"),
                str(girdi.get("ham_ifade") or ""),
                str(girdi.get("metin") or ""),
            )
        return {"karar": kabul}, iz


__all__ = ["DENETLENEN_ALANLAR", "YuklemAjani"]
