# ADR 022 — Çok turlu sohbet: yuva devri, sohbet geçmişi değil

**Tarih:** 27 Ağustos 2026 · **Durum:** kabul edildi · **Sorumlu:** Eren
**İlgili bulgu:** iki turlu koşum, `data/katilim.db` (931 kayıt)
**Şema etkisi:** yok — `Cevap.baglam` alanı eklendi, `schema.py` değişmedi

## Bağlam

Chatbot her soruyu sıfırdan okuyordu; takip sorusu diye bir şey yoktu.
İki tur ölçüldü:

```
tur 1: «Albaraka en yüksek kâr payı oranı ne?»
         -> Albaraka Türk, aylık %2,87 (Konut Finansmanı)              ✓
tur 2: «120 ay vade»
         -> Kuveyt Türk, Alışveriş Puanı Kampanyası, 48 ay             ✗

tur 1: «1.000.000 TL konut finansmanı istiyorum»
         -> «Uygunluk değerlendirmesi için şu bilgiler eksik: vade
             (örn. 120 ay veya 10 yıl)»
tur 2: «120 ay vade»
         -> Kuveyt Türk, Alışveriş Puanı Kampanyası                    ✗
```

İkincisi ağır olanı: **sistem soruyu kendi soruyor, cevabını kullanamıyor.**
Sebebi yönlendirmedeydi — niyet HAM soruya bakılarak çözülüyor, «120 ay vade»
tutar yuvası boş olduğu için `profil_sorgusu_mu` kapısını geçemiyor ve
muhakeme ajanına hiç ulaşmıyordu.

## Karar

Sohbet hafızası **yuva devri** olarak kurulur (`src/rag/baglam.py`), LLM
sohbet geçmişi olarak değil.

Bu chatbot deterministik: cevabı üreten şey kod, doldurulacak bir istem yok.
Önceki turları bir dil modeline vermenin bu mimaride karşılığı yoktur.
Karşılığı olan şey anafora çözümüdür: önceki turda **çözülmüş** varlıkları
(banka · ürün · ölçüt · yön · tutar · vade) sonraki turun **boş** yuvalarına
taşımak.

Devir metne yazılarak yapılır. Sebebi tek: soruyu okuyan on ayrı ayrıştırıcı
var (`_bankalari_bul`, `sorulan_urun`, `_sorulan_olcut`, `_sorulan_yon`,
`profil_ayristir`, `niyet_belirle` …) ve hepsi soru **metnini** okuyor.
Yuvayı metne yazmak onların hepsini tek noktadan besler; her birine ayrı bir
`baglam` parametresi geçirmek aynı kararı on yerde tekrar etmek olurdu.

Hangi yuvanın boş olduğuna metin değil **ayrıştırıcının kendisi** karar verir:
«soruda banka var mı?» sorusunu `_bankalari_bul` cevaplar. İkinci bir
eşleştirme kopyası yazılmadı — 27 Ağustos'ta `alan_disi_soru`'nun kopyası
geride kalmış ve aynı soruya iki kapı iki farklı cevap vermişti.

### Dört kısıt

**1. Devir yalnız boş yuvaya.** Soruda yazılan her zaman kazanır.
«peki Kuveyt Türk?» bankayı değiştirir, ölçütü ve yönü devralır.

**2. Kapsam kapıları HAM soruya çalışır, devir sonradan gelir.** Tersi
kalkanı delerdi: alakasız bir soru önceki turdan banka devralıp kapsam içi
sayılırdı — `terim_gecer`'in kapattığı deliğin aynısı, arka kapıdan.
Nöbetçi: `test_kapsam_disi_soru_baglamla_kurtarilmaz`.

**3. Tutar ve vade yalnız profil kipinde devrolur.** Sistem «vade eksik»
dediyse sonraki turun vadesi o yuvaya oturur; başıboş bir tutar sonraki
olgusal soruyu profil sorgusuna çevirmez.

**4. Devralınan her yuva cevapta beyan edilir** ve beyan kalkandan geçer
(`Koken.SISTEM` + `hesap`). Kullanıcının yazmadığı bir kısıtla cevap
verildiyse bunu görmeli — «müşteri tipi belirtilmedi» dürüstlüğünün aynısı.

### Bağlam kayan çerçevedir

Her turda **yeniden** kurulur, geçmiş yığılmaz. Devralınan yuva zaten o turun
sorusuna yazıldığı için kendiliğinden korunur; ayrıca bir birleştirme kuralı
gerekmez, dolayısıyla hangi yuvanın kaç tur yaşayacağı diye bir bakım yükü ve
sapma kaynağı da doğmaz.

Banka adı **sorudan değil cevaptan** okunur (`kullanilan_kayitlar`): «en
yüksek kâr payını hangi banka veriyor?» sorusunda banka adı geçmez, cevapta
geçer. Yan kazanç: kullanıcının «albraka» yazım hatası ikinci tura taşınmaz.

## Reddedilenler

**Sunucuda oturum tutmak.** API'ye oturum kimliği verip bağlamı sunucuda
saklamak, ölçeklendiğinde paylaşılan durum ve temizlik işi demek. Bağlam
istemcide durur, her istekte geri gönderilir; `/ask` idempotent kalır — aynı
(soru, bağlam) çifti aynı cevabı verir.

**Yönü tek başına devretmek.** İlk kuruluşta yön, ölçütten bağımsız
devroluyordu ve ölçüldü:

```
bağlam: «en DÜŞÜK kâr payı» · soru: «Albaraka'nın vadesi kaç ay?»
  -> «Vade en düşük olan banka Kuveyt Türk: 2 ay»                      ✗
```

Kullanıcı Albaraka'nın vadesini soruyor, en kısa vadeyi alıyor. Yön ölçütün
bir **nitelemesidir**: kullanıcı yeni bir ölçüt adlandırdıysa o ölçütün ucunu
sormamıştır. Artık yalnız ölçütle birlikte devrolur.

**Korpusa sorulan soruya devir.** Bu da kuruluşta ölçüldü:

```
tur 1: «Albaraka en yüksek kâr payı oranı ne?»
tur 2: «hangi bankalar konut finansmanı sunuyor?»
         -> devralınan «en yüksek» soruyu LİSTE olmaktan çıkarıp
            SIRALAMAYA çeviriyor; dokuz bankalık liste tek bankaya iniyor ✗
```

Devir bir yuvayı **doldurur**, sorunun **şeklini** değiştirmez. Korpusa
sorulan soruda eksik yuva zaten yoktur. Kapı `_BELIRTEC_SOZCUKLERI`'nden
türetilir — o küme «banka sözcüğünün önünde durursa belirli bir banka
adlandırılmamış demektir» ayrımını zaten tutuyor.

Bedeli: «peki hangi bankada daha düşük?» gibi korpusa açılan takip soruları
ölçüt devralmaz. Bilerek ödendi — ters yön (meşru bir liste sorusunu tek
bankaya daraltmak) sessizce yanlış cevap üretiyor.

## Ölçüm

| | önce | sonra |
|---|---|---|
| «Albaraka … kâr payı» → «120 ay vade» | Kuveyt Türk | **Albaraka** |
| «1.000.000 TL konut» → «120 ay vade» | Kuveyt Türk kampanyası | **18 uygun kampanya, taksit ve toplam maliyetle** |
| «… kâr payı» → «peki Kuveyt Türk?» | ölçüt kayboluyor | **ölçüt devrolur** |
| Kapsam dışı soru (bağlam doluyken) | — | **kapsam dışı kalır** |
| `make eval` (tek turlu) | — | **değişmez** — bağlamsız çağrı birebir eski cevabı verir |
| `make test` | 1434 | 1459 |

Son satır bir nöbetçiyle korunuyor: `test_baglamsiz_cagri_davranisi_degistirmez`
dört soru için `sor(s, k)` ile `sor(s, k, baglam=None)` metinlerinin birebir
aynı olduğunu denetler. Bu olmadan çok turlu yolda yapılan bir düzeltme
`docs/SONUCLAR.md` sayılarını sessizce oynatabilirdi.

## Görünür kıldığı eksikler — [ADR 023](023-tek-kaynak-eslestirme-ve-yon.md)

Çok turlu sohbet üç eksiği gün yüzüne çıkardı; üçü de tek turlu sorularda da
vardı ve **aynı gün çözüldü**:

- **Profil kolunda banka süzgeci yoktu** — «peki Albaraka?» dokuz bankayı
  sıralıyordu. Artık `_banka_suz` var ve eşleştirme chatbot'unkiyle aynı.
- **`_tekil_cevap` sorulan ölçütü sıralamıyordu** — «120 ay vade» doğru
  bankaya gidiyor ama en dolu kaydı gösteriyordu. Artık ölçütün avantajlı
  ucu seçiliyor, yön `ALAN_YONLERI`'nden okunuyor.
- **Kesme eki eşleştirmeyi düşürüyordu** — «Albaraka'dan» hiçbir bankaya
  eşleşmiyordu. `kesmeden_ayir` özel adı ekinden ayırıyor.

## Alınan ders

Sistem, kullanıcıya soru soruyordu ve cevabını okuyacak yeri yoktu. Bir
arayüzün kullanıcıya soru sorması, o cevabın gideceği yuvanın var olduğunu
taahhüt etmektir.
