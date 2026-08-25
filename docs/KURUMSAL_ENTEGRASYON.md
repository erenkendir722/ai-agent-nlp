# Kurumsal Entegrasyon Mimarisi

*Şartname 5.9 (On-Premise) ve değerlendirme kriteri "Kurum sistemlerine entegre
edilebilir mimari yaklaşım sunulması" (%20).*

> **Bu belge bir tasarım önerisidir, teslim edilen kodun tamamı değildir.**
> Nelerin bugün çalıştığı ve nelerin kurum tarafında yapılacağı her bölümde
> ayrı ayrı işaretli. Yapılmamış bir şeyi yapılmış göstermek, bu projenin
> temel ilkesine aykırı olurdu.

---

## 1. Neden entegrasyon kolay: sistem zaten dışa kapalı

Tasarımın çıkış noktası şuydu — **hiçbir bileşen dış servise bağımlı
olmasın.** Bunun entegrasyon açısından üç sonucu var:

| Karar | Entegrasyon sonucu |
|---|---|
| Model ağırlıkları Apache-2.0 / MIT | Kurum kendi donanımında koşturabilir, lisans engeli yok |
| Depolama SQLite / SQLAlchemy | `VERITABANI_URL` değiştirilerek kurumsal PostgreSQL'e taşınır |
| Cevap üretimi şablon tabanlı | Denetlenebilir; "model ne dediyse o" riski yok |
| Kimlik doğrulama **uygulamada yok** | Kurumun kendi katmanına bırakılmış (bölüm 3) |

Yerel yol (`LLM_SAGLAYICI=ollama`) bulut bağımlılığının bir **tercih**
olduğunu, zorunluluk olmadığını gösterir: aynı kod yolu kurum içi GPU'da
koşar.

---

## 2. Yerleşim topolojisi

```
┌─────────────────────── KURUM AĞI ────────────────────────────────┐
│                                                                   │
│  ┌── İSTEMCİ KATMANI ──┐      ┌──── UYGULAMA KATMANI ────────┐   │
│  │                     │      │                               │   │
│  │  Banka çalışanı     │      │  Ters vekil (nginx / IIS)     │   │
│  │  tarayıcısı ────────┼─────▶│    + LDAP/AD kimlik           │   │
│  │                     │      │    + TLS sonlandırma          │   │
│  └─────────────────────┘      │    + erişim günlüğü           │   │
│                               │           │                    │   │
│                               │           ▼                    │   │
│                               │  ┌─────────────────────────┐  │   │
│                               │  │ Streamlit arayüz  :8501 │  │   │
│                               │  │ REST API          :8000 │  │   │
│                               │  └───────────┬─────────────┘  │   │
│                               └──────────────┼─────────────────┘   │
│                                              ▼                     │
│  ┌──── VERİ KATMANI ────────────────────────────────────────┐     │
│  │  Kampanya veritabanı (SQLite → kurumsal PostgreSQL)      │     │
│  │  RAG vektör indeksi (.npz — yerel dosya, sunucusuz)      │     │
│  └───────────┬──────────────────────────────────────────────┘     │
│              │ gecelik toplu besleme (bölüm 5)                     │
│              ▼                                                     │
│  ┌──── KURUMSAL VERİ AMBARI ────────────────────────────────┐     │
│  │  Mevcut BI / raporlama altyapısı                          │     │
│  └───────────────────────────────────────────────────────────┘     │
│                                                                     │
│  ┌──── MODEL KATMANI (kurum içi) ───────────────────────────┐      │
│  │  Ollama / vLLM  ·  Qwen3.5  ·  BGE-M3 gömme              │      │
│  └───────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ YALNIZ toplama adımı (make crawl)
                              │ kurumsal vekil üzerinden — bölüm 4
                        ┌─────┴──────┐
                        │  İnternet  │
                        └────────────┘
```

**Dikkat edilecek nokta:** internet oku yalnız **toplama** adımına gidiyor.
Çıkarım, karşılaştırma, chatbot ve arayüz kurum ağının dışına hiç çıkmaz.
Toplama zaten gecelik bir toplu iştir; kurum isterse tümüyle kapatıp veriyi
kendi kaynağından besleyebilir.

---

## 3. Kimlik ve yetkilendirme (LDAP / Active Directory)

**Bugünkü durum:** uygulamada kimlik doğrulama **yok** ve bu bilinçli bir
karardır — yarım bir kimlik katmanı, olmayandan daha tehlikelidir.

**Önerilen mimari — kimlik uygulamanın DIŞINDA:**

```
Tarayıcı ──TLS──▶ Ters vekil ──▶ LDAP/AD (Kerberos ya da LDAP bind)
                      │
                      │ kimlik doğrulandıktan sonra
                      ▼
              X-Kullanici / X-Rol başlıkları eklenir
                      │
                      ▼
              Streamlit / REST API
```

Gerekçe: kurumlar kimlik altyapısını **uygulamalara devretmez.** nginx
(`ldap-auth` modülü), Apache (`mod_authnz_ldap`) ya da IIS Windows
Authentication zaten kurumda çalışıyordur. Uygulama yalnız vekilin eklediği
başlığa güvenir.

**Önerilen rol modeli:**

| Rol | Yetki |
|---|---|
| `okuyucu` | Arayüz, karşılaştırma, chatbot |
| `analist` | + veri dışa aktarma, ağırlık ayarları |
| `yonetici` | + toplama/çıkarım tetikleme, yapılandırma |

**Kurum tarafında yapılacak:** vekil yapılandırması, rol eşlemesi. Uygulama
tarafında yapılacak: başlıktan rol okuma (bugün yok — bir orta katman yeterli).

---

## 4. Kurumsal vekil (proxy) arkasında çalışma

Toplama adımı `httpx` kullanıyor; bu kütüphane standart ortam
değişkenlerini kendiliğinden okur:

```bash
HTTP_PROXY=http://vekil.kurum.local:8080
HTTPS_PROXY=http://vekil.kurum.local:8080
NO_PROXY=localhost,127.0.0.1,.kurum.local
REQUESTS_CA_BUNDLE=/etc/ssl/certs/kurum-koku.pem   # TLS araya girme
SSL_CERT_FILE=/etc/ssl/certs/kurum-koku.pem
```

**TLS araya girme (SSL interception) uyarısı.** Çoğu kurumsal vekil TLS'i
açıp kendi kök sertifikasıyla yeniden imzalar. Kök sertifika tanıtılmazsa
toplama adımı sertifika hatasıyla düşer. Bu, kurulumda en sık karşılaşılan
engeldir ve çözümü yukarıdaki iki değişkendir.

> Bu senaryonun bir örneğini kendi verimizde gördük: BDDK sitesinin sertifika
> zinciri doğrulanamadığı için otomatik taranmıyor, gerekçesi
> `docs/VERI_METODOLOJISI.md`'de yazılı. Yani sorun teorik değil.

**Hava boşluğu modunda vekil de gerekmez** — `docker-compose.yml` içindeki
`internal: true` açıldığında servislerin dışarı çıkışı altyapı düzeyinde
kapanır.

---

## 5. Veri ambarına toplu besleme

Şema **donmuş** ve sürümlü (`SEMA_SURUMU`), her kayıt kendi sürümünü taşır.
Bu, ambar tarafında sözleşmeye güvenilebileceği anlamına gelir.

```
  make crawl ──▶ make extract ──▶ kampanya veritabanı
                                        │
                                        │ gecelik iş (cron / Airflow / SQL Agent)
                                        ▼
                              ┌─────────────────────┐
                              │  Dışa aktarma       │
                              │  · CSV / Parquet    │
                              │  · REST /compare    │
                              │  · doğrudan SQL     │
                              └──────────┬──────────┘
                                         ▼
                                  Kurumsal ambar
                                  (yavaş değişen boyut)
```

**Önerilen tablo yapısı — üç tablo yeterli:**

| Tablo | İçerik | Tazeleme |
|---|---|---|
| `kampanya` | Kanonik alanlar + `sema_surumu` | Gecelik, tam yükleme |
| `kampanya_kanit` | Alan başına kaynak, alıntı, güven, yöntem | Gecelik |
| `cikarim_kosusu` | Koşu tarihi, yapılandırma, kod parmak izi | Koşu başına bir satır |

Üçüncüsü kritik: her sayının **hangi kod sürümüyle** üretildiği ambarda
saklanır. Bir metrik sorgulandığında "bu rakam hangi koşudan geldi?" sorusu
cevaplanabilir olur. Bugün `cikarim_kosusu_yaz` bunu zaten yazıyor.

**Tarihsel izleme:** kampanyalar zamanla değişir. Yavaş değişen boyut (SCD
Tip 2) ile `cekim_tarihi` üzerinden versiyonlanırsa, *"bu bankanın oranı üç
ayda nasıl değişti?"* sorusu ambardan cevaplanır — sistemde bugün yok, ama
veri modeli buna hazır.

---

## 6. Denetim izi

Bankacılıkta *"bu sayı nereden geldi?"* sorusunun cevabı **zorunludur**.
Sistem bunu sonradan eklenen bir günlükle değil, **veri modelinin kendisiyle**
sağlıyor.

**Bugün mevcut olan — kanıt zinciri:**

Her `Alan` şunları taşır ve bunlarsız **kurulamaz** (şema `ValueError` atar):

```
değer · ham ifade · kaynak URL · çekim tarihi · metin içi konum
      · güven · yöntem (kural | llm | hibrit)
```

Yani her sayı için *"hangi sayfanın hangi karakter aralığından, hangi
katmanın çıkardığı"* veriden okunabilir. Denetçiye gösterilecek şey bir
günlük satırı değil, kaydın kendisidir.

**Bugün mevcut olan — koşu izi:** `cikarim_kosusu` tablosu her çıkarım
koşusunun tarihini, yapılandırmasını ve **kod parmak izini** saklar.

**Kurum tarafında eklenecek — erişim izi:**

| Kaydedilecek | Nerede |
|---|---|
| Kim, ne zaman, hangi sorguyu çalıştırdı | Ters vekil erişim günlüğü |
| Hangi karşılaştırma hangi ağırlıklarla yapıldı | Uygulama günlüğü (bugün yok) |
| Dışa aktarılan veri | Ambar yükleme günlüğü |

Chatbot cevapları zaten kaynakçalıdır (banka, URL, çekim tarihi); ekran
görüntüsü tek başına denetim kanıtı sayılabilir.

---

## 7. Ölçeklenebilirlik — dürüst değerlendirme

| Bileşen | Bugünkü ölçek | Kurumsal ölçekte |
|---|---|---|
| Veritabanı | SQLite, binlerce kayıt | `VERITABANI_URL` ile PostgreSQL — **kod değişikliği yok** |
| RAG indeksi | ~15 bin paragraf, tek `.npz`, milisaniyeler | Yüz binlere kadar aynı yöntem; ötesinde FAISS/pgvector |
| Çıkarım | Toplu iş, kayıt başına saniyeler | Yatay ölçeklenir; işçi sayısı `CIKARIM_ISCI` |
| Arayüz | Streamlit, tek süreç | Onlarca eşzamanlı kullanıcıya yeter; yüzlerce için REST + kurumsal ön yüz |

**Söylenmesi gereken:** Streamlit bir prototip arayüzüdür. Yüzlerce eşzamanlı
kullanıcı için doğru yol, REST API'yi (`src/api/sunucu.py`, dört uç nokta)
kurumun kendi ön yüzüne bağlamaktır. API bu yüzden ayrı bir katman olarak
duruyor — arayüze gömülü değil.

---

## 8. Kurulum sırası (kurum BT ekibi için)

1. Model sunucusu kurulur (Ollama / vLLM), ağırlıklar bir kez indirilir
2. Uygulama kurulur — çevrimdışı paketle de yapılabilir (`docs/KURULUM.md`)
3. `VERITABANI_URL` kurumsal veritabanına çevrilir
4. Ters vekil + LDAP/AD yapılandırılır (bölüm 3)
5. Vekil değişkenleri tanıtılır (bölüm 4) — **kök sertifika unutulmaz**
6. Gecelik toplama/çıkarım işi zamanlanır
7. Ambar besleme işi zamanlanır (bölüm 5)
8. `make test` ile doğrulanır

---

## İlgili belgeler

| Konu | Dosya |
|---|---|
| Katman mimarisi | [`MIMARI.md`](MIMARI.md) |
| Kurulum ve hava boşluğu | [`KURULUM.md`](KURULUM.md) |
| Şema sözleşmesi | [ADR 001](kararlar/001-sema-sozlesmesi.md) |
| Model lisansları | [`LISANSLAR.md`](LISANSLAR.md) · [ADR 013](kararlar/013-evren-model-lisans-durusu.md) |
| RAG'ın sunucusuz tasarımı | [ADR 014](kararlar/014-vektor-db-yerine-yerel-kosinus.md) |
