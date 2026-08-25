"""Alan tanımları — çıkarım katmanlarının TEK doğruluk kaynağı.

NEDEN VAR:
    `finansman_tutari_max` üç yerde farklı anlaşılıyordu ve hiçbirinde
    yazılı değildi: kural katmanı "sayfadaki en büyük TL tutarı" gibi
    davranıyordu, istem alan adını modele çıplak veriyordu, yüklem ajanı
    kendi kısa tanımını taşıyordu. Üçü de tahmin ediyordu.

    24 Ağustos altın set denetiminde bu alanın 4 yanlış pozitifinin
    DÖRDÜ de aynı karışıklıktı — sayı bir KOŞUL EŞİĞİ idi, kampanyanın
    azami tutarı değil:

        "125.000 TL'ye kadar olan finansmanlarda [masraf alınmaz]"
             ↳ ücret koşulunun eşiği
        "konut finansmanı oranlarımız 100.000 TL ile sınırlıdır"
             ↳ oranın geçerlilik sınırı
        "1.200.001 TL - 2.000.000 TL | %20 | 12"
             ↳ oran tablosunun dilim sınırı

    Bir alanın ne olduğu tek yerde yazılmazsa her katman kendi tanımını
    uydurur; "iki katman uzlaştı" kararı da o noktada anlamını yitirir —
    aynı ada farklı şeyler diyorlardır.

KULLANIM: `extraction.llm` istemi ve `ajanlar.yuklem` denetimi buradan
okur. Tanım değişirse ikisi birden değişir; ayrışamazlar.

TANIMLAR ÖRNEK DEĞER İÇERMEZ. Örnek vermek modeli o örneğe yakın sayıları
kabul etmeye iter ve ölçtüğümüz şey çıkarım kalitesi olmaktan çıkar.
"""

from __future__ import annotations

ALAN_TANIMLARI: dict[str, str] = {
    "kar_payi_orani": (
        "kampanyanın kâr payı oranı (katılım bankacılığında faiz yerine geçen oran). "
        "Vergi, komisyon veya indirim yüzdesi DEĞİLDİR. "
        "SIFIR GEÇERLİ BİR DEĞERDİR ve boş hücreden farklıdır: «vade farksız», "
        "«vade farkı yok/olmadan», «kâr payı yok/alınmaz» ifadeleri oranın SIFIR "
        "olduğunu söyler — katılım bankacılığında vade farkının olmaması, kâr "
        "payının alınmaması demektir. Bu ifadeler oran beyanı sayılır."
    ),
    "finansman_tutari_max": (
        "bu kampanyada kullandırılabilecek AZAMİ finansman tutarı. "
        "KOŞUL EŞİĞİ DEĞİLDİR: «X TL'ye kadar olan finansmanlarda ücret alınmaz» "
        "cümlesindeki X, ücret koşulunun eşiğidir; «oranlarımız X TL ile sınırlıdır» "
        "cümlesindeki X, oranın geçerlilik sınırıdır. Oran/ücret tablolarındaki "
        "dilim sınırları da azami tutar değildir. Yalnız «X TL'ye varan finansman» "
        "gibi doğrudan üst sınır bildiren ifadeler bu alana yazılır."
    ),
    "vade_ay_max": (
        "bu kampanyada sunulan AZAMİ vade (ay). Başka bir ürünün vadesi, "
        "bir tablo satırındaki vade veya örnek hesaplamadaki vade DEĞİLDİR."
    ),
    "taksit_sayisi": (
        "bu kampanyada sunulan taksit sayısı. Vade ile karıştırılmamalıdır."
    ),
    "tahsis_ucreti": (
        "finansman tahsisinde alınan TEK SEFERLİK masraf (dosya masrafı). "
        "Tutar ya da oran olabilir; ama her yüzde bir tahsis ücreti değildir."
    ),
    "odul_miktari": (
        "kampanya kapsamında müşteriye verilen ödül/hediye tutarı. "
        "Harcama koşulu (şu kadar harcarsan) ödül tutarı DEĞİLDİR."
    ),
    "indirim_orani": "kampanya kapsamında uygulanan indirim oranı",
    "alisveris_puani": (
        "kampanya kapsamında kazanılan alışveriş puanı. Puan/mil/chip-para gibi "
        "somut bir ödül birimi olmalı; TL indirimi puan değildir."
    ),
    "kampanya_bitis": (
        "kampanyanın sona erdiği tarih. Kampanyanın BAŞLANGIÇ tarihi ya da "
        "bir tarih aralığının ilk ucu DEĞİLDİR."
    ),
    "masrafsiz_mi": (
        "bu kampanyada ücret/komisyon/masraf alınmadığının metinde açıkça "
        "söylenip söylenmediği. Pazarlama başlığı («Masraf yok, kazanç var!») "
        "tek başına yeterli değildir; kampanyanın masraf koşulunu bildirmelidir."
    ),
}
"""Sayısal, tarihsel ve mantıksal alanların anlamı."""

TUR_TANIMLARI = """
kampanya_turu için sınıf tanımları:
- konut_finansmani : konut, ev, gayrimenkul, mortgage alımına yönelik finansman
- tasit_finansmani : taşıt, araç, otomobil, motosiklet alımına yönelik finansman
- ihtiyac_finansmani: belirli bir mala bağlı olmayan genel amaçlı finansman;
                     alışveriş finansmanı, eğitim, tatil, evlilik gibi ihtiyaçlar
- finansman        : finansman ürünü olduğu belli ama ALT TÜRÜ metinden anlaşılmıyor
- kart             : kredi kartı / banka kartı ürünü veya kart kampanyası
- alisveris_puani  : kazanılan PUAN/mil/chip-para gibi somut bir ödül birimi var
- yatirim_urunu    : altın, döviz, katılım fonu, yatırım hesabı gibi ürünler
- yeni_musteri     : kampanyanın konusu yeni müşteri kazanımının kendisi
- diger            : YALNIZCA yukarıdakilerin HİÇBİRİ uymuyorsa

`diger` bir SIĞINAK DEĞİLDİR. Sayfa bir ürün kategorisini açıkça anlatıyorsa
(başlıkta, adreste veya metinde) o kategoriyi seç. Kararsız kaldığında en
belirgin ürün kategorisini seç; `diger` son çaredir.

hedef_kitle için sınıf tanımları:
- yeni_musteri     : yalnız bankaya yeni gelen müşteriler yararlanabilir
- mevcut_musteri   : yalnız hâlihazırda müşteri olanlar yararlanabilir
- maas_musterisi   : maaşını bu bankadan alanlara özel
- segment          : belirli bir segmente özel (öğrenci, emekli, KOBİ, özel bankacılık)
- tum_musteriler   : herkes yararlanabilir; kısıt belirtilmemiş
Metin bir kısıt söylemiyorsa null bırak — "herkes" varsayımı yapma.
"""
"""Sınıflandırma alanlarının taksonomisi.

`extraction.kural._URL_TUR_ISARETLERI` bu taksonomiyle AYNI sınıfları
tanımak zorundadır: biri değişip diğeri kalırsa iki katman farklı
taksonomilere göre çalışır."""

__all__ = ["ALAN_TANIMLARI", "TUR_TANIMLARI"]
