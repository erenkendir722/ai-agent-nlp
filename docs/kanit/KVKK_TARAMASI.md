# KVKK Taraması — toplanan metinde kişisel veri var mı?

_Otomatik üretildi: 2026-08-25T13:27:18+03:00 · `tools/kvkk_taramasi.py`_

Bu rapor **G-14** (veri toplama etiği kanıtı) kapsamındadır ve
`docs/kanit/VERI_TOPLAMA_ETIGI.md` tarafından kanıt olarak gösterilir.

Taranan ham kayıt: **1024** (`data/raw/*/*.json` — başlık + gövde metni).

## Sonuç

✅ **Kimliği belirli gerçek kişiye ait veri bulunmadı.**

Sağlama toplamı tutan tek bir T.C. kimlik numarası yok. Bulunan 11 haneli
sayılar örnek form değerleridir (aşağıda) — sağlama toplamını geçemezler.

11 haneli sayı bulguları: `11111111111` (34 kez).

## Kurumsal iletişim bilgileri

Kampanya sayfalarında bankanın kendi iletişim bilgileri geçer. Bunlar
**tüzel kişiye** aittir ve KVKK anlamında kişisel veri değildir; yine de
sayılır ve maskelenerek raporlanır — kanıt belgesinde ikinci kez
yayımlanmasınlar diye.

| Tür | Farklı değer | Toplam geçiş | Örnekler (maskeli) |
|---|---|---|---|
| e-posta | 4 | 56 | `…@hs01.kep.tr`, `…@kuveytturk.com.tr`, `…@collwave.com`, `…@Alldayesim.com` |
| IBAN | 6 | 6 | `…0011`, `…0117`, `…0118`, `…0001` |
| cep telefonu | 1 | 2 | `…3944` |

## Kapsam ve sınırlar

- Tarama **desen tabanlıdır**: ad-soyad gibi serbest metin kimlik bilgisini
  yakalamaz. Toplayıcı yalnız kamuya açık kampanya sayfalarını çektiği ve
  giriş gerektiren hiçbir alana girmediği için müşteri verisi bu korpusa
  girmez; tarama bunu **destekler**, tek başına kanıtlamaz.
- Tarandığı an ne varsa odur: yeni çekimden sonra yeniden koşulmalıdır.

```bash
make kanit-kvkk          # bu raporu yeniler
make kanit-kvkk kati=1   # şüpheli bulguda çıkış kodu 1 (teslim öncesi)
```
