"""LLM katmanı — şema kısıtlı yapısal üretim (Katman 2b).

Şema, dilbilgisi kısıtlaması olarak uygulanır; model şemanın dışına ÇIKAMAZ.
Bu, "şema geçerliliği 1,00" metriğini garanti eder — JSON ayrıştırma hatası
diye bir kategori kalmaz. Kısıtın hangi parametreyle iletildiği sağlayıcıya
göre değişir (Ollama'da `format`, EVREN'de `response_format.json_schema`);
ayrıntı ve ölçülen tuzaklar: `src/extraction/saglayici.py`.

BU MODÜL HANGİ SAĞLAYICIDA KOŞTUĞUNU BİLMEZ. Taşıma katmanı ayrıldı ki
"yerel 4B vs servis 122B" ablasyon satırı ölçülebilsin.

HALÜSİNASYON ÖNLEME — bu modülün en önemli tasarım kararı:
    Modelden değeri yorumlaması değil, metinde geçtiği hâliyle BİREBİR
    kopyalaması istenir. Dönen ifade ham metinde `str.find` ile aranır.
    Bulunamazsa alan REDDEDİLİR. Yani model bir sayı uydurursa, o sayı
    sisteme giremez — çünkü metinde karşılığı yoktur.

    Bu kontrol istem mühendisliği değil, koddur. Modelin iyi niyetine
    güvenmez. Ölçülen halüsinasyon oranımızın düşük olmasının sebebi budur.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import Any

from src.ajanlar.elestirmen import ElestirmenAjani
from src.alan_tanimlari import TUR_TANIMLARI
from src.extraction.saglayici import (
    SABIT_TOHUM,
    SICAKLIK,
    Saglayici,
    saglayici_kur,
)
from src.preprocessing.normalizasyon import (
    birim_belirle,
    masrafsiz_mi,
    oran_ayristir,
    para_ayristir,
    tarih_ayristir,
    vade_ayristir,
)
from src.schema import Alan, HedefKitle, KampanyaTuru, Kaynak, ollama_json_semasi

log = logging.getLogger(__name__)

VARSAYILAN_MODEL = None
"""Model seçimi sağlayıcıya bırakıldı (`saglayici_kur`).

Eskiden burada `qwen3.5:4b-q4_K_M` yazıyordu. Artık `LLM_SAGLAYICI` hangi
sağlayıcıyı seçerse onun varsayılanı geçerli: EVREN'de `llm-large`, yerelde
`OLLAMA_MODEL`. Tek bir `--model` bayrağı ikisini de karşılar."""

AZAMI_METIN = int(os.getenv("AZAMI_METIN", "40000"))
"""Modele verilen azami metin uzunluğu (karakter).

6000'den yükseltildi. Eski değerin gerekçesi *"4B modelde bağlamı dar tutmak
doğruluğu artırıyor"* idi — 262K bağlamlı 122B modelde bu kısıt yalnız
zarar veriyor.

ÖLÇÜLEN KAYIP: 590 kayıdın **66'sı (%11,2)** 6000 karakterde kırpılıyordu.
Kırpılan bölgedeki alanlar sessizce kayboluyordu; çıkarım hatası olarak da
görünmüyorlardı, çünkü model o metni hiç görmemişti.

40.000 karakter dağılımın p99'unu (9.827) rahatça kapsar. Tek bir 88.832
karakterlik kayıt hâlâ kırpılır; o sayfa birleştirilmiş bir dizin sayfasıdır,
tek kampanya değildir. Yerel 4B ile koşarken `AZAMI_METIN=6000` verin."""

# SICAKLIK, SABIT_TOHUM ve AZAMI_URETIM artık `saglayici.py`'de tanımlı:
# örnekleme ayarları taşıma katmanının işidir ve sağlayıcıya göre farklı
# parametre adlarıyla iletilir. EVREN'de determinizmin neden garanti
# OLMADIĞI da orada ölçümüyle birlikte yazılı — okumadan değiştirmeyin.


def _kismi_json_kurtar(icerik: str) -> dict[str, Any]:
    """Yarıda kesilmiş JSON'dan tamamlanmış alanları kurtarır.

    NEDEN GEREKLİ — bu sessiz bir veri kaybıydı:
        `json.loads` hata verince tüm kayıt için `{}` dönüyordu. Yani model 15
        alanın 14'ünü doğru üretmiş olsa bile, son alan yarım kaldığı için
        14'ü birden çöpe gidiyordu. Kayıt yine de yazıldığından hata hiçbir
        yerde görünmüyor, yalnız doluluk oranı sessizce düşüyordu.

    NASIL: JSON nesnesi sıralı yazılır; son tam anahtar-değer çiftinden
    sonrasını atıp süslü parantezi kapatmak geçerli bir nesne verir. En sondaki
    virgülden başlayarak geriye doğru denenir, ilk ayrıştırılabilen kabul edilir.

    Kanıt zinciri BOZULMAZ: kurtarılan alanlar da eleştirmen ajanının birebir
    metin doğrulamasından geçer. Kurtarma yalnız ayrıştırma katmanındadır.
    """
    govde = icerik.strip()
    if (bas := govde.find("{")) == -1:
        return {}
    govde = govde[bas:]

    # Zaten geçerliyse dokunma. Üretimde buraya yalnız `json.loads` başarısız
    # olunca gelinir, ama fonksiyonun tek başına da doğru olması test
    # edilebilirliği ve yeniden kullanımı güvenli kılar.
    for aday in (govde, govde + "}"):
        try:
            sonuc = json.loads(aday)
        except json.JSONDecodeError:
            continue
        return sonuc if isinstance(sonuc, dict) else {}

    for konum in reversed([i for i, karakter in enumerate(govde) if karakter == ","]):
        try:
            sonuc = json.loads(govde[:konum] + "}")
        except json.JSONDecodeError:
            continue
        return sonuc if isinstance(sonuc, dict) else {}
    return {}


# ---------------------------------------------------------------------------
# Katılım bankacılığı terminolojisi — istem enjeksiyonu
# ---------------------------------------------------------------------------
# Genel amaçlı bir model "kâr payı"nı faiz sanabilir veya "murabaha"yı bilmeyebilir.
# Bu sözlük, alan bilgisini modele doğrudan taşır. Sözlüğün tamamı
# docs/TERIM_SOZLUGU.md'de yayınlanacak (Görkem, Sprint 2).

TERIMLER = """
Katılım bankacılığı terimleri (şartname 5.5'teki resmî tanımlar):
- Kâr Payı Oranı: Katılım bankacılığında FAİZ YERİNE kullanılan, finansman
  işlemine konu olan mal veya hizmet üzerinden oluşan kâr payı oranını ifade eder.
- Finansman Maliyeti: Kullandırılan finansman kapsamında oluşan toplam geri ödeme
  tutarını ve müşterinin katlandığı toplam maliyeti ifade eder.
- Katılım Fonu: Katılım bankacılığı prensiplerine uygun olarak değerlendirilen ve
  fon sahipleri ile banka arasında kâr-zarar paylaşımına dayanan hesap türü.
- Masrafsız Finansman: Finansman işlemi kapsamında tahsis ücreti, dosya masrafı
  veya benzeri ek maliyetlerin UYGULANMADIĞI finansman türü.
- Avantajlı Finansman: Standart finansman koşullarına göre daha uygun maliyet,
  kâr payı oranı veya ek fayda sunan kampanyalı finansman ürünü.

Ek notlar:
- "Finansman" sözcüğü kredi anlamındadır; "kâr payı" faiz DEĞİLDİR.
- Kâr payı oranı genellikle AYLIK yüzde olarak verilir (örn. aylık %2,05).
- Tahsis ücreti = dosya masrafı; finansman tahsisinde alınan tek seferlik masraf.

Dolaylı ifadeler de kâr payı avantajını anlatır ve tanınmalıdır (şartname 5.2):
"avantajlı kâr payı fırsatı", "özel oranlı finansman", "düşük maliyetli finansman".
Bu ifadelerde SAYI YOKSA kar_payi_orani alanını null bırak — dolaylı ifadeden
sayı UYDURMA. İfadeyi kampanya_avantaji alanına yaz.
"""

SISTEM_ISTEMI = f"""Sen bir katılım bankacılığı metin madenciliği uzmanısın.
Sana bir katılım bankasının kampanya/ürün sayfasının metni verilecek.
Görevin, istenen alanları bu metinden çıkarmaktır.

{TERIMLER}

MUTLAK KURALLAR:
1. Sayısal ve tarihsel alanlar için, değeri METİNDE GEÇTİĞİ HÂLİYLE BİREBİR
   kopyala. Biçimi değiştirme, yuvarlama, hesaplama yapma.
   Metinde "%1,89" yazıyorsa "%1,89" yaz — "1.89" veya "1,89" değil.
2. Metinde olmayan hiçbir bilgiyi üretme. Emin değilsen null yaz.
   Boş bırakmak yanlış cevap vermekten HER ZAMAN daha iyidir.
3. Tahmin etme, çıkarım yapma, "genelde böyledir" deme.
4. Metinsel alanlarda (avantaj, koşullar) metni kısa özetleyebilirsin,
   ama sayı eklersen o sayı metinde geçmek zorundadır.
"""


# ALAN TANIMLARI BU İSTEME BİLEREK KONMUYOR — ölçüldü, zarar verdi.
#
# `alan_tanimlari.ALAN_TANIMLARI` blok hâlinde isteme eklendi ve makro-F1
# 3 tekrarlı ölçümde **0,765 → 0,750** düştü (yayılım 0,002, yani gürültü
# değil). Düşüş iki alanda toplandı: `odul_miktari` 0,667→0,571,
# `kampanya_bitis` 0,815→0,786.
#
# Yorum: aynı tanımlar YÜKLEM AJANINDA fayda sağlıyor (`tahsis_ucreti`
# 0,833→0,909). Fark görevin şeklinde: denetçi TEK bir değer hakkında
# TEK bir karar verir, tanım orada odaklıdır. Çıkarıcı ise 16 alanı aynı
# anda dolduruyor; 10 alanın uzun tanımı istemi şişirip asıl metinden
# dikkat çalıyor.
#
# Tanımlar silinmedi, yeri değişti: `ajanlar/yuklem.py` kullanıyor.


def _kullanici_istemi(metin: str, azami: int | None = None) -> str:
    turler = ", ".join(t.value for t in KampanyaTuru)
    kitleler = ", ".join(h.value for h in HedefKitle)
    return f"""Aşağıdaki kampanya metnini analiz et.

kampanya_turu şunlardan biri olmalı: {turler}
hedef_kitle şunlardan biri olmalı (veya null): {kitleler}
{TUR_TANIMLARI}

--- METİN BAŞLANGICI ---
{metin[: azami or AZAMI_METIN]}
--- METİN SONU ---

Alanları JSON olarak çıkar. Sayısal alanları metindeki yazımıyla birebir kopyala."""


# ---------------------------------------------------------------------------
# Alan tipi eşlemesi
# ---------------------------------------------------------------------------

# Her alanın ham ifadeyi hangi normalizasyon fonksiyonundan geçireceği.
_AYRISTIRICILAR = {
    "kar_payi_orani": oran_ayristir,
    "indirim_orani": oran_ayristir,
    "finansman_tutari_max": lambda s: para_ayristir(s, birim_zorunlu=False),
    "odul_miktari": lambda s: para_ayristir(s, birim_zorunlu=False),
    "alisveris_puani": lambda s: para_ayristir(s, birim_zorunlu=False),
    "tahsis_ucreti": lambda s: para_ayristir(s, birim_zorunlu=False) or oran_ayristir(s),
    "vade_ay_max": vade_ayristir,
    "taksit_sayisi": vade_ayristir,
    "kampanya_bitis": tarih_ayristir,
    "masrafsiz_mi": masrafsiz_mi,
}

_SERBEST_METIN = ("urun_turu", "masraf_bilgisi", "kampanya_avantaji", "kampanya_kosullari")

_CUMLE_SINIRI = re.compile(r"(?<=[.!?\n])\s+")


def _masraf_kaniti(metin: str, karar: bool) -> str | None:
    """Modelin `masrafsiz_mi` kararını destekleyen cümleyi bulur.

    Kural katmanıyla AYNI ölçüt (`kural._masrafsizlik`): bir bool'un kanıtı,
    o kararı veren bir cümledir. Model kararı doğruysa cümle zaten metindedir;
    bulunamıyorsa ortada çıkarım değil varsayım vardır.
    """
    for parca in _CUMLE_SINIRI.split(metin):
        cumle = " ".join(parca.split())
        if cumle and masrafsiz_mi(cumle) is karar:
            return cumle[:120]
    return None


class LLMCikarici:
    """Ollama üzerinden şema kısıtlı çıkarım yapar.

    Kanıt doğrulaması bu sınıfta DEĞİL, `ajanlar.elestirmen.ElestirmenAjani`
    içindedir. Ayrılmasının sebebi ablasyon: "ajan var, eleştirmen yok"
    yapılandırması ancak doğrulama kapatılabilir olduğunda ölçülebilir.
    """

    def __init__(
        self,
        model: str | None = None,
        *,
        saglayici: Saglayici | None = None,
        elestirmen: ElestirmenAjani | None = None,
    ) -> None:
        self.saglayici = saglayici or saglayici_kur(model=model)
        self.model = self.saglayici.model
        self.elestirmen = elestirmen or ElestirmenAjani()

    def ham_cikar(self, metin: str) -> dict[str, Any]:
        """Modelden şemaya uygun ham JSON alır. Normalizasyon YAPMAZ.

        AKIL YÜRÜTME HER İKİ SAĞLAYICIDA DA KAPALI — bu kritiktir. Qwen3.5
        bir düşünme modelidir; varsayılan davranışta üretim bütçesinin
        tamamını akıl yürütmeye harcar ve `content` BOŞ döner. Yapısal
        çıkarımda düşünmeye ihtiyacımız yok; şema kısıtı çıktıyı zaten
        zorluyor. Kapatmanın ölçülen bedeli: yerelde kayıt başına ~3 dakika
        yerine ~13 saniye, EVREN'de bütçe dolup boş dönmek yerine ~2 saniye.

        Parametrenin nasıl iletileceği sağlayıcıya göre değişir ve ikisinde
        de sessiz bir tuzağı var — `saglayici.py` modül başlığına bakın.
        """
        icerik = self.saglayici.uret(SISTEM_ISTEMI, _kullanici_istemi(metin), ollama_json_semasi())
        try:
            return json.loads(icerik)
        except json.JSONDecodeError:
            kurtarilan = _kismi_json_kurtar(icerik)
            if kurtarilan:
                log.warning("JSON kesilmiş, %d alan kurtarıldı", len(kurtarilan))
                return kurtarilan
            log.error("Şema kısıtına rağmen JSON ayrıştırılamadı: %.200s", icerik)
            return {}

    def cikar(self, metin: str, url: str, cekim_tarihi: datetime) -> dict[str, Alan]:
        """Doğrulanmış, normalize edilmiş, kaynağa bağlanmış alanlar döner.

        Metinde karşılığı bulunamayan sayısal alanlar sessizce DÜŞÜRÜLÜR ve
        halüsinasyon sayacına yazılır.
        """
        ham = self.ham_cikar(metin)
        sonuc: dict[str, Alan] = {}

        for alan_adi, ham_deger in ham.items():
            if ham_deger in (None, "", "null", "belirtilmemiş", "Belirtilmemiş"):
                continue

            alan = self._alani_kur(alan_adi, ham_deger, metin, url, cekim_tarihi)
            if alan is not None:
                sonuc[alan_adi] = alan

        return sonuc

    # -- iç ---------------------------------------------------------------

    def _alani_kur(
        self,
        alan_adi: str,
        ham_deger: Any,
        metin: str,
        url: str,
        cekim_tarihi: datetime,
    ) -> Alan | None:
        ham_ifade = str(ham_deger).strip()

        # 1) Sınıflandırma alanları — enum doğrulaması yeter, metinde aranmaz
        if alan_adi == "kampanya_turu":
            # Altın setin yakaladığı iki hata biçimi burada düzeltilir:
            # genel «finansman» URL'deki alt türle özelleştirilir ve kanıtsız
            # «alisveris_puani» düşürülür. Gerekçe ve ölçüm:
            # `kural.kampanya_turunu_duzelt`.
            from src.extraction.kural import kampanya_turunu_duzelt

            duzeltilmis, sebep = kampanya_turunu_duzelt(ham_ifade, url, metin)
            if sebep:
                log.info(
                    "kampanya_turu düzeltildi: %s -> %s (%s) %s",
                    ham_ifade, duzeltilmis, sebep, url,
                )
                ham_ifade = duzeltilmis
            return self._enum_alani(KampanyaTuru, ham_ifade, url, cekim_tarihi, metin)
        if alan_adi == "hedef_kitle":
            return self._enum_alani(HedefKitle, ham_ifade, url, cekim_tarihi, metin)

        # 2) Serbest metin alanları — özet meşru, birebir aranmaz
        if alan_adi in _SERBEST_METIN:
            return Alan(
                deger=ham_ifade,
                ham_ifade=ham_ifade[:200],
                kaynak=Kaynak(
                    url=url,
                    cekim_tarihi=cekim_tarihi,
                    alinti=metin[:280],
                    karakter_baslangic=0,
                    karakter_bitis=min(280, len(metin)),
                ),
                guven=0.70,
                yontem="llm",
            )

        # 3) Sayısal / tarihsel alanlar — KANIT ZORUNLU
        if alan_adi == "masrafsiz_mi":
            # `masrafsiz_mi` bir bool olduğu için `KANIT_ZORUNLU_ALANLAR`
            # dışındadır: modelin döndürdüğü "true"/"false" metinde birebir
            # aranamaz. Kanıt zincirindeki bu deliği kapatmanın yolu, kararı
            # DESTEKLEYEN bir cümle istemektir.
            #
            # Önceki sürüm belge düzeyinde bakıyordu: metinde "ücret" geçiyorsa
            # modelin bool'u kabul ediliyordu. Bu fazla gevşekti — 15 Ağustos
            # altın set ölçümünde `masrafsiz_mi`'nin 15 uyuşmazlığından 8'i,
            # modelin `ham_ifade='False'` ile ürettiği ve metinde hiçbir masraf
            # beyanı bulunmayan kayıtlardı. Model "masraf var mı?" sorusuna
            # varsayılan olarak "hayır" diyordu; bu bir çıkarım değil.
            #
            # Artık kural katmanıyla aynı ölçüt: metinde, modelin verdiği
            # kararın AYNISINI veren bir cümle olmalı. Yoksa değer düşer.
            deger = ham_deger if isinstance(ham_deger, bool) else masrafsiz_mi(ham_ifade)
            if deger is None:
                return None
            kanit = _masraf_kaniti(metin, deger)
            if kanit is None:
                log.info("masrafsiz_mi reddedildi: kararı destekleyen cümle yok (%s)", url)
                return None
            return Alan(deger=deger, ham_ifade=kanit, kaynak=None, guven=0.65, yontem="llm")

        ayristirici = _AYRISTIRICILAR.get(alan_adi)
        if ayristirici is None:
            return None

        # ELEŞTİRMEN AJANI — değer kaynakta gerçekten geçiyor mu?
        kabul, konum = self.elestirmen.dogrula(alan_adi, ham_ifade, metin, url=url)
        if not kabul:
            return None

        try:
            deger = ayristirici(ham_ifade)
        except (ValueError, TypeError):
            return None
        if deger is None:
            return None

        baslangic, bitis = konum if konum else (0, 0)
        return Alan(
            deger=deger,
            ham_ifade=ham_ifade,
            kaynak=Kaynak(
                url=url,
                cekim_tarihi=cekim_tarihi,
                alinti=self.elestirmen.alinti(metin, baslangic, bitis),
                karakter_baslangic=baslangic,
                karakter_bitis=bitis,
            ),
            guven=0.75,
            yontem="llm",
            birim=birim_belirle(ham_ifade, alan_adi),
        )

    def _enum_alani(
        self, enum_sinifi: type, ham: str, url: str, cekim_tarihi: datetime, metin: str
    ) -> Alan | None:
        try:
            uye = enum_sinifi(ham)
        except ValueError:
            log.info("Geçersiz enum değeri düşürüldü: %s = %r", enum_sinifi.__name__, ham)
            return None
        return Alan(
            deger=uye,
            ham_ifade=ham,
            kaynak=Kaynak(
                url=url,
                cekim_tarihi=cekim_tarihi,
                alinti=metin[:280],
                karakter_baslangic=0,
                karakter_bitis=min(280, len(metin)),
            ),
            guven=0.80,
            yontem="llm",
        )


# SICAKLIK ve SABIT_TOHUM burada KULLANILMIYOR ama bilerek yeniden
# yayımlanıyor: `tests/test_determinizm.py` ve ablasyon betikleri bu
# modülden içe aktarıyor. Sabitlerin tanımı `saglayici.py`'de.
__all__ = [
    "AZAMI_METIN",
    "SABIT_TOHUM",
    "SICAKLIK",
    "LLMCikarici",
    "SISTEM_ISTEMI",
    "TERIMLER",
    "TUR_TANIMLARI",
]
