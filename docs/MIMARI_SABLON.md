# Mimari Şablon — Bu Proje Nasıl Kurgulandı

**Bu dosyanın amacı farklı:** Diğer `docs/*.md` dosyaları bu projenin *kendi*
verisini, ölçülerini ve kronolojisini anlatır. Bu dosya onları anlatmaz —
projenin **yapısal iskeletini**, yani başka herhangi bir "küçük-orta ölçekli,
dosya tabanlı, admin panelli, tek sunuculu" uygulamaya taşınabilecek
**tasarım kalıplarını** anlatır.

Bu dosya bir başka Claude oturumuna (farklı bir proje üzerinde çalışan) referans
olarak verilmek üzere yazıldı: "buna benzer bir sistem kurmak istiyorum"
dendiğinde okunacak doküman budur. Banka/ölçü/rasyo gibi domain detayları
kasıtlı olarak sadece **örnek** olarak geçer — kopyalanacak olan onlar değil,
etraflarındaki mimaridir.

---

## 1. Bir cümlede ne bu

FastAPI tabanlı, **veritabanısız**, dosya tabanlı depolamayla çalışan, tek bir
sunucu üzerinde tek worker ile koşan, admin panelinden yönetilen bir
"veri işleme + sunum" uygulaması. Build adımı olmayan tek-dosya React
frontend'i ve Docker/Coolify ile "push = deploy" akışı var.

**Bu kalıp ne zaman doğru seçim:**
- Veri hacmi tek makinenin belleğine/diskine rahat sığıyor (bu projede
  ~2,85M satır parquet ≈ 10 MB sıkıştırılmış JSON çıktı)
- Eşzamanlı yazan kullanıcı sayısı azı — genelde tek bir admin veya küçük
  bir ekip veri yüklüyor, çok sayıda kullanıcı sadece **okuyor**
- Yazma işlemleri seyrek ve öngörülebilir (çeyreklik veri yükleme gibi),
  sürekli/yüksek-frekanslı yazma yok
- Basit, denetlenebilir, "neden bu sayı böyle çıktı" sorusuna dosya açıp
  cevap verilebilen bir sistem isteniyor (PostgreSQL + ORM + migration
  karmaşıklığına gerek yok)

**Bu kalıp ne zaman YANLIŞ seçim:** çok sayıda eşzamanlı yazar, gerçek
zamanlı güncelleme gereksinimi, yatay ölçeklenme ihtiyacı (birden fazla
worker/instance — bu mimari kasıtlı olarak **tek worker'a kilitli**, bkz. §6),
karmaşık ilişkisel sorgular. O senaryoda bu şablonu değil, DB + ORM + queue
tabanlı klasik bir backend'i düşünün.

---

## 2. Üç katmanlı veri akışı (bu kalıbın kalbi)

```
HAM KAYNAK  →  İŞLENMİŞ ARA FORMAT  →  ÖNCEDEN HESAPLANMIŞ SUNUM KATMANI
(dokunulmaz)   (tek, konsolide dosya)   (frontend'in okuduğu TEK dosya)
```

Somut örnek (bu projede):

```
xlsx dosyaları (data/raw/)
      │  ingest: parse + doğrula + normalize et
      ▼
veriler.parquet  (uzun/long format, tek konsolide tablo)
      │  compute: iş kurallarını uygula
      ▼
computed.json  (frontend'in tek okuduğu dosya — hesaplama YOK, sadece render)
```

**Neden üç katman, neden ikisi değil:**
- Ham kaynak asla değişmez → herhangi bir hesaplama hatası bulunduğunda
  **sıfırdan yeniden üretilebilir** (audit/rollback garantisi). Bu, "veriyi
  elle düzelt" dürtüsüne karşı en güçlü savunma.
- Ara format (parquet/CSV/SQLite — ne olursa olsun) kaynak dosyaların
  dağınıklığını (yüzlerce dosya, farklı formatlar) **tek bir sorgulanabilir
  tabloya** indirger. Bu katman olmadan her hesaplama yüzlerce dosyayı tekrar
  tekrar parse eder.
- Son katman (computed.json / computed cache) **frontend'i backend'den
  tamamen ayırır**: frontend hiçbir iş kuralı bilmez, sadece JSON'u render
  eder. Bir formül değişikliği asla frontend koduna dokunmaz.

**Genelleme:** Domain ne olursa olsun (log analizi, envanter, finansal
raporlama, sensör verisi) bu üç-katman ayrımını koruyun: *ham/dokunulmaz →
normalize edilmiş ara → önceden hesaplanmış sunum*. Ara katmayı atlayıp
ham dosyalardan direkt JSON üretmeye çalışmak, dosya sayısı arttıkça
pipeline'ı katlanarak yavaşlatır ve hata ayıklamayı zorlaştırır.

---

## 3. Dosya/dizin haritası (genel kalıp + bu projedeki karşılığı)

| Genel kalıp | Bu projedeki karşılığı | Rolü |
|---|---|---|
| `app.py` (tek backend dosyası) | `app.py` (~2.170 satır) | Tüm route'lar, auth, admin uçları — bilinçli olarak **tek dosya**, mikroservise bölünmedi (bkz. §9) |
| `<auth-modülü>.py` | `users.py` | Kimlik/üyelik mantığı, ana dosyadan ayrık çünkü test edilebilirliği ve okunabilirliği artırıyor |
| `pipeline/` | `pipeline/` | Saf hesaplama mantığı — FastAPI'den, HTTP'den habersiz, tek başına import edilip test edilebilir |
| `<config-seed>.json` (git'te) ↔ `data/<config>.json` (runtime) | `catalog.seed.json` ↔ `data/catalog.json` | Kod ile veri arasındaki **konfigürasyon** katmanı — git'te taşınır ama runtime'da admin panelden düzenlenen kısımları da korur (bkz. §7) |
| `frontend/` (build'siz) | `frontend/index_v30.html`, `admin.html`, `login.html`, `signup.html` | Her biri **tek dosya**, CDN'den React/kütüphane çeker, `npm install` yok |
| `scripts/` | `scripts/` | CLI yardımcıları — pipeline'ı HTTP olmadan tetiklemek için (ör. `export_data_snapshot.py`, SSH'lı ortamlarda admin panelin CLI eşdeğeri) |
| `tests/` | `tests/` (66 test) | pytest — çoğunlukla **regresyon spot-check**: "bilinen bir girdi için çıktı hâlâ doğru mu" |
| `data/` (git'te DEĞİL) | `data/` | Tüm çalışma zamanı verisi — `.gitignore`'da, bkz. §8 |

**Neden tek `app.py` ve mikroservis değil:** Bu ölçekte (tek admin, düşük
trafik) servisler arası ağ çağrısı, ayrı deploy pipeline'ları ve dağıtık
işlem karmaşıklığı hiçbir fayda getirmeden gecikme ve operasyonel yük
ekler. Route'lar mantıksal olarak yorum bloklarıyla (`# ====...====`)
bölümlere ayrılır (public / member / admin), bu FastAPI'de ayrı router
modüllerine bölünmeden de okunabilirliği korur.

---

## 4. Kimlik doğrulama — iki-buçuk katmanlı model

Bu proje, tek bir auth mekanizması yerine **amaca göre ayrılmış üç seviye**
kullanıyor. Bu ayrım, "her kullanıcı aynı yetkiye sahip" varsayımının
yanlış olduğu her admin-panelli sistemde işe yarar.

```
┌─────────────────────────────────────────────────────────┐
│ 1. KÖK ADMIN — HTTP Basic Auth (env değişkeni)           │  ← sunucu operatörü
│    Tüm admin uçlarına erişir. Şifre kod dışında (env).   │
├─────────────────────────────────────────────────────────┤
│ 2. ÜYELİK OTURUMU — imzalı session çerezi                │  ← normal kullanıcılar
│    Kayıt → admin onayı → giriş. Varsayılan: sadece okuma.│
│    role='admin' atanırsa Basic Auth ile EŞ DEĞER olur.   │
├─────────────────────────────────────────────────────────┤
│ 2.5. ULTRA ADMIN — tek hesaba özel, gizli üst katman      │  ← sistem sahibi
│    Diğer adminler bu hesabı listede GÖREMEZ, hedefleyemez│
│    (404 döner, varlığı sızdırılmaz — 403 değil).         │
└─────────────────────────────────────────────────────────┘
```

**Neden bu üç seviye, ikisi değil:**
- Kök admin (env-tabanlı Basic Auth) her zaman çalışır — üyelik sistemi
  bozulsa/veritabanı silinse bile sunucuya girilebilir. Bu bir **kilitlenme
  önleyici** (break-glass) katman.
- Üyelik oturumu, sıradan kullanıcıların kendi hesaplarıyla (parola
  değiştirme, kendi profili gibi) etkileşmesini sağlar, ama admin yetkisi
  **açıkça atanmadıkça** hiçbir okuma-dışı yetki vermez.
- "Admin rolü ver" ile "tam admin" arasında kısmi yetki YOK — bu proje
  bilinçli olarak ayrıntılı izin matrisinden kaçındı (basitlik tercih
  edildi). Daha büyük bir sistemde bu noktada izin-bazlı (permission-based)
  bir modele geçmek gerekebilir — bkz. §10, "Rol-bazlı ölçü erişimi" backlog
  maddesi tam da bunun bir sonraki adımı.
- Ultra admin katmanı, "adminler birbirini yönetemesin" ihtiyacından
  doğdu — sistem sahibinin hesabını sıradan bir adminin yanlışlıkla (ya da
  kötü niyetle) değiştirememesi/silememesi için. Hedef kullanıcı sorgusunda
  bu hesap eşleşirse **404** döner (403 değil) — varlığı bile sızdırılmaz.

**Uygulama detayı — `auto_error=False` dependency zinciri:** FastAPI'de bir
endpoint'in "Basic Auth VEYA session" kabul etmesi gerekiyorsa,
`HTTPBasic(auto_error=False)` kullanılır: kimlik bilgisi verilmemişse hata
fırlatmadan `None` döner, dependency fonksiyonu bu durumda ikinci yönteme
(session) düşer. Bu, tek bir `require_admin_access` fonksiyonunda iki farklı
giriş yolunu temiz şekilde birleştirir.

---

## 5. Admin paneli — bir "operasyon konsolu" olarak tasarım

Admin paneli CRUD ekranı değil, **operasyon konsolu**: sistemin yaşam
döngüsündeki riskli/seyrek işlemleri, hepsi tek yerden, hepsi kendi
güvenlik önlemleriyle sunar. Sekmeler ve genel karşılıkları:

| Sekme (bu projede) | Genel kalıp | Ne işe yarar |
|---|---|---|
| 📊 Veri Durumu | **Durum paneli** | Sistemin şu anki halini özetler (kapsam matrisi, son güncelleme) — herhangi bir işlem yapmadan önce bakılacak ilk yer |
| 📤 Veri Yükleme | **Artımlı (incremental) veri girişi** | Sadece YENİ veriyi işler, mevcut olanı korur (upsert). Günlük/rutin operasyonun varsayılan yolu |
| *(Rebuild — ayrı, gizli/dikkatli uç)* | **Tam yeniden hesaplama** | TÜM ham arşivi baştan işler. Formül değişikliği sonrası gerekir ama **yıkıcı olabilir** (bkz. §6) — bilinçli olarak Upload kadar kolay erişilebilir yapılmadı |
| 🚚 Sunucu Taşıma | **Export/Import (taşınabilirlik)** | SSH'siz, tarayıcıdan veri paketini indir/yükle — bkz. §8 |
| 👥 Üyelik Başvuruları | **Onay akışı (approval workflow)** | Kayıt olan herkes "pending" başlar, admin onaylamadan sisteme giremez |
| 🏷️ Banka Grupları | **Segment/kategori yönetimi** | Domain'e özel gruplama mantığı — genelde herhangi bir "varlıkları kategorilere ata" ihtiyacının karşılığı |
| 📜 Yükleme Geçmişi | **Audit log** | Kim, ne zaman, ne yaptı — her yazma işlemi burada iz bırakır |

**Tasarım ilkesi — riskli işlemler kolay-erişilebilir olmamalı:** "Upload"
(güvenli, artımlı) ile "Rebuild" (yıkıcı olabilir, tam yeniden hesaplama)
arayüzde kasıtlı olarak eşit ağırlıkta sunulmaz. Bu proje bunu sert şekilde
öğrendi: bir üretim ortamında Rebuild'e basıldığında, sunucuda ham arşivin
tamamı olmadığı için **51 dönemlik geçmiş 1 döneme düştü**. Bundan sonra
eklenen koruma: rebuild sonucu mevcut veriden önemli ölçüde küçükse (§6)
istek otomatik reddedilir; bilinçli olarak zorlamak isteyen admin ayrı bir
onay kutusunu (`force=true`) işaretlemek zorunda.

---

## 6. Yazma işlemlerini koruyan katmanlar (herhangi bir "yaz + hesapla" sistemine uygulanabilir)

Veri yazan her akışta (bu projede upload/rebuild/import), sırayla:

1. **Ağır işlem kilidi** (`threading.Lock`) — iki ağır işlem aynı anda
   çalışamaz, ikincisi 409 alır. *Neden gerekli:* tek worker'da bile
   FastAPI senkron endpoint'leri threadpool'da paralel çalıştırır; kilit
   olmadan iki yazma yarışıp veriyi bozar.
2. **Girdi kalite kontrolü** — bozuk/geçersiz girdi ham arşive bile
   yazılmadan reddedilir.
3. **Yazmadan önce otomatik yedek** — mevcut "doğru" durum, yeni (yanlış
   olabilecek) veri yazılmadan önce zaman damgalı olarak yedeklenir, son
   N kopya tutulur.
4. **Boşluk kilidi** — sonuç tamamen/anormal derecede boşsa yazma iptal
   edilir.
5. **Regresyon kilidi** — sonuç, mevcut veriden **anlamlı ölçüde küçükse**
   (örnekte: ölçü/varlık/dönem sayısı düşüyor ya da dolu hücre oranı
   belirli bir eşiği aşarak azalıyor) istek **409 ile reddedilir**; admin
   panelde açık bir "veri azalmasına izin ver" seçeneğiyle bilinçli olarak
   aşılabilir. *Bu, §5'teki üretim olayından sonra eklendi — "az önce
   olanın bir daha olmaması" için yazılmış somut bir savunma.*
6. **Atomik yazım** — geçici dosyaya (`.tmp`) yaz, sonra `os.replace()` ile
   değiştir. Yazma yarıda kesilirse (sunucu çöker, disk dolar) asıl dosya
   hiç bozulmaz — ya eski hali ya da tamamen yeni hali vardır, ara hal yok.
7. **Açılışta kendi kendini kurtarma** — ana veri dosyası açılışta
   bozuk/geçersiz bulunursa, sistem otomatik olarak son sağlam yedeğe
   döner, bozuk dosyayı ayrı bir isimle saklar (silmeden — adli inceleme
   için) ve admin panelde görünür bir uyarı bırakır. Bu sayede "sunucu
   bozuk veriyle sessizce ayağa kalktı" senaryosu insan müdahalesi
   olmadan da fark edilir.

**Genelleme:** Bu 7 katman, veri kaybının **geri dönüşü olmayan** olduğu
her sistemde (tek doğru kaynak dosyaya yazan, versiyon kontrolü olmayan
her pipeline) uygulanabilir bir kontrol listesi. Hepsi birlikte, "kötü bir
komut çalıştırıldığında ne kadar veri kaybedilir" sorusunun cevabını
sıfıra ya da en azından "son N yedek" seviyesine indirir.

**Tek-worker zorunluluğunun nedeni tam olarak burada:** Yukarıdaki
kilitlerin hepsi process-içi (`threading.Lock`, in-memory rate-limit
sayaçları). Birden fazla worker/process ile çalıştırılırsa her worker
kendi kilidine sahip olur ve bu korumalar **sessizce devre dışı kalır**.
Bu yüzden `uvicorn.run(..., workers=1)` ve `reload=False` bilinçli
tercihler — otomatik reload bile kodu değiştiğinde arka planda ikinci bir
process başlatıp kilitleri ikiye bölebilir.

---

## 7. Konfigürasyon katmanı: "seed dosyası ↔ runtime kopyası" kalıbı

Bir sistemde hem **kod tarafından tanımlanan** (deploy ile gelen) hem de
**kullanıcı tarafından runtime'da düzenlenen** (admin panelden değişen)
konfigürasyon bir arada olduğunda ortaya çıkan klasik problem: `git pull`
kullanıcının yaptığı değişiklikleri ezer, ya da kullanıcının değişiklikleri
korunursa kod tarafındaki güncellemeler hiç uygulanamaz.

Bu proje bunu **seed + runtime ayrımı** ile çözüyor:

```
catalog.seed.json  (git'te — "ölçü şu, kompozisyon bu" gibi KOD tanımları)
        │  her açılışta senkronize edilir
        ▼
data/catalog.json  (runtime — seed'den gelen taze config + admin'in
                     düzenlediği "banka grupları" gibi runtime-only alanlar
                     KORUNARAK)
```

Açılışta çalışan senkronizasyon fonksiyonu, seed'deki alanları her zaman
üzerine yazar (kod güncellemesi her zaman kazanır) ama runtime'a özgü
alanları (ör. admin panelden düzenlenen grup üyelikleri) olduğu gibi taşır.
Bu, "hangi ayar koddan geliyor, hangisi kullanıcı tercihi" sorusunu dosya
seviyesinde netleştirir.

---

## 8. Veri taşınabilirliği — "elle zip'leme" anti-kalıbına karşı çözüm

`data/` git'te değil (bilinçli — canlı veri `git pull` ile ezilmesin diye).
Ama bu, kod ile veri arasındaki bağı zayıflatıyor: bir depoyu yeni bir
sunucuya taşırken **kod GitHub'dan gelir ama veri gelmez** — biri onu ayrıca
taşımak zorunda.

Bu proje, "proje klasörünü elle zip'le, karşı tarafa at" yönteminin
**neden anti-kalıp olduğunu** yaşayarak öğrendi: bu yöntem `.gitignore`'u
görmez (kodla birlikte hangi data/ anlık görüntüsünün taşındığı belirsiz
kalır), ve hiçbir yerde "bu veri hangi tarihte donduruldu" bilgisi
kaydedilmez. Sonuç: bir sunucuda aylar önce donmuş bir veri anlık görüntüsü
sessizce üretime çıktı.

**Çözüm — admin panelinden tetiklenen, doğrulanabilir export/import:**

```
GET  /admin/export-data   → tüm çalışma-zamanı verisini + bir manifest.json
                             içeren TEK bir ZIP döner (indirilebilir)
POST /admin/import-data   → aynı ZIP'i doğrular, mevcut veriyi önce
                             yedekler, sonra atomik olarak değiştirir
```

`manifest.json` içinde: dışa aktarma zamanı, kaynak git commit hash'i, veri
özeti (kaç kayıt/varlık/dönem var), tarih aralığı. Böylece içe aktarmadan
önce "bu doğru paket mi, ne kadar güncel" sorusu **görsel olarak** (admin
panelde) yanıtlanabilir — SSH açıp dosya tarihine bakmaya gerek kalmaz.

**Genelleme:** Git'te tutulmayan (ve tutulmaması GEREKEN — büyük, sık
değişen, kullanıcıya özel) her veri katmanı için, "kod + veri ayrı taşınır"
gerçeğini gizlemek yerine **açıkça bir taşıma mekanizması sağlayın**, ve o
mekanizma sağlanan paketin *neyi, ne zaman* içerdiğini kendi içinde
belgelesin (bir manifest/metadata dosyası ile). SSH erişimi olan ortamlar
için ayrıca bir CLI eşdeğeri (`scripts/export_data_snapshot.py`) sağlamak,
admin paneline erişimi olmayan/otomatikleştirme yapan senaryoları da
kapsar — aynı doğrulama mantığını iki arayüzde (HTTP + CLI) tekrarlamak,
tek bir "gerçek" export fonksiyonunu her ikisinden çağırmaktan daha
kırılgandır; mümkünse ortak bir fonksiyonda birleştirin.

---

## 9. Deployment mimarisi

```
GitHub repo (main branch)
      │  push → webhook (GitHub App entegrasyonu)
      ▼
Coolify (self-hosted PaaS, VPS üzerinde)
      │  Dockerfile build
      ▼
Docker container (non-root, healthcheck'li, TEK worker)
      │  reverse proxy
      ▼
Traefik  →  Let's Encrypt (otomatik HTTPS sertifikası)
      │
      ▼
Kalıcı Docker volume (/app/data) — container'ın YAŞAM DÖNGÜSÜNDEN BAĞIMSIZ
```

**Kod/veri ayrımının deployment'a yansıması:** `Dockerfile` bilinçli olarak
`data/`'yı image'a KOPYALAMAZ (COPY talimatı yok). Nedenleri: (a) deploy'da
zaten kalıcı bir volume mount edileceği için kopyalanan içerik gölgelenirdi,
(b) image'ı gereksiz şişirirdi, (c) en önemlisi — image içine gömülü bir veri
anlık görüntüsü, "hangi veri şu an canlıda" sorusunu belirsizleştirirdi (tam
olarak §8'de çözülen problemin kendisi). Image sadece KOD taşır; veri her
zaman ayrı, kalıcı bir katmandan gelir.

**Non-root container + healthcheck:** Container `uid 10001` ile, root
olmayan bir kullanıcı olarak çalışır (deploy denetimlerinin standart
maddesi). `/healthz` endpoint'i orkestratöre (Coolify/Docker) "bu container
canlı mı, veri dizinine yazabiliyor mu" bilgisini verir — `curl` yerine
Python'un kendi `urllib`'i kullanılır çünkü `python:3.11-slim` imajında
`curl` yok, ekstra bir sistem paketi kurmaya gerek bırakmaz.

**Gizli bilgiler asla image'da değil:** `KT_USERNAME`/`KT_PASSWORD` gibi
sırlar `Dockerfile`'da **set edilmez** — sadece `docker run -e ...` ya da
Coolify'ın environment-variable arayüzünden gelir. Kodun kendisindeki
fallback değerler (ör. yerel geliştirme için zayıf bir varsayılan şifre)
sadece yerel çalıştırma içindir; üretim ortamı env değişkeni olmadan asla
başlatılmamalı — bu proje bunu `KT_PRODUCTION` bayrağıyla da pekiştiriyor
(bkz. aşağı).

**Ortam bayrağı ile davranış değişimi (`KT_PRODUCTION`):** Tek bir env
değişkeni, kodun "üretimde miyim" sorusuna cevap vermesini sağlıyor ve buna
göre: (a) session çerezini `Secure`/HTTPS-only yapıyor, (b) API şema
sayfalarını (`/docs`, `/redoc`) kapatıyor. Bu kalıp — "aynı kod tabanı, tek
bayrakla iki davranış modu" — yerelde geliştirmeyi HTTP üzerinden rahat
tutarken üretimde güvenliği zorlamanın basit bir yolu.

**"Push = deploy" akışının riski ve önlemi:** GitHub App entegrasyonu
main branch'e her push'ta otomatik build+deploy tetikler. Bu hız kazandırır
ama "kod deploy edilirken veri de bir şekilde değişir mi" endişesini
doğurur — cevap **hayır**, çünkü yukarıdaki ayrım (image sadece kod, veri
her zaman ayrı volume) bunu yapısal olarak imkânsız kılıyor. Bu garanti
olmasaydı, otomatik deploy'a güvenmek çok daha riskli olurdu.

---

## 10. Test stratejisi: "regresyon spot-check", uçtan uca test değil

`tests/` klasöründeki testlerin çoğu klasik unit test değil, **bilinen
girdi → beklenen çıktı** doğrulamaları: gerçek (ya da gerçeğe yakın) bir
veri kümesi üzerinde pipeline çalıştırılır, belirli hücrelerin/toplamların
beklenen değerle eşleştiği kontrol edilir. Ayrıca:

- **Ölçü/kalem sayısı sabitleri** testte hardcode edilir (ör. "sistemde şu
  an X tane hesaplanan ölçü olmalı") — biri yanlışlıkla bir tanımı silerse
  test hemen kırılır, sessizce eksik veri üretilmez.
- **Grup agregasyon testleri** — toplama mantığının (basit toplam / ağırlıklı
  ortalama) tip bazında doğru seçildiğini doğrular.
- **Auth testleri** (`test_auth.py`) — parola/rol/onay akışının mantığını
  HTTP katmanından bağımsız, doğrudan modül üzerinde test eder.

**Genelleme:** Hesaplama-ağırlıklı bir sistemde ("şu ham veriden şu sayı
çıkmalı" tipi doğruluk kritikse) klasik "her fonksiyona bir unit test"
yaklaşımından çok, **bilinen bir anlık görüntü üzerinde uçtan uca
regresyon** yazmak daha değerli — çünkü asıl risk "fonksiyon X yanlış
davranıyor" değil, "iki fonksiyonun birleşimi, ya da bir veri kalitesi
sorunu, beklenmedik şekilde yanlış bir sayı üretiyor" riskidir.

---

## 11. Bu şablonu başka bir projeye uygularken — kontrol listesi

Yeni bir projede bu mimariyi temel alacaksanız, şu kararları **bilinçli**
verin (kopyalamayın, düşünün):

1. **Ham kaynak neresi, gerçekten dokunulmaz mı?** Eğer kaynak veri zaten
   bir API/DB'den geliyorsa (dosya değil), "ham arşiv" katmanı gerekmeyebilir
   — o zaman iki katmana (ara format + sunum) inebilirsiniz.
2. **Ara format neyle temsil edilecek?** Parquet burada "uzun format,
   tek tablo, kategori kolonlar" için uygundu (2-3M satır, columnar). Daha
   küçük/daha ilişkisel veri için SQLite (hâlâ dosya tabanlı, hâlâ tek
   worker'la uyumlu, ama SQL sorgu gücü ekler) daha iyi olabilir.
3. **Auth katmanlarını gerçekten ihtiyaç kadar karmaşıklaştırın.** Tek
   kullanıcılı bir araçta "ultra admin" kavramı anlamsız; ama "birden fazla
   admin birbirini yönetebilir mi" sorusu varsa bu kalıbı düşünün.
4. **Hangi yazma işlemi "yıkıcı" olabilir, onu UI'da kasıtlı olarak
   zorlaştırın.** §5-6'daki Upload/Rebuild ayrımını kendi domain'inize
   uyarlayın: "güvenli, artımlı, varsayılan yol" ile "tam yeniden
   işleme, riskli, ayrı onay gerektiren yol"u net ayırın.
5. **Tek worker'a gerçekten ihtiyacınız var mı?** Eğer trafik/yazma hacmi
   büyüyecekse, in-memory kilitler yerine baştan Redis-tabanlı kilit ya da
   gerçek bir DB'nin transaction garantilerine geçmeyi planlayın — bu
   şablon o ölçeğe geldiğinde **kırılır**, o yüzden ölçek beklentisini
   baştan netleştirin.
6. **Veri taşınabilirliğini gün 1'de düşünün, olay olduktan sonra değil.**
   Bu projede export/import özelliği bir üretim veri kaybı olayından SONRA
   eklendi. Yeni bir projede, "data/ nasıl git dışı ama yine de taşınabilir
   olacak" sorusunu ilk deploy'dan önce yanıtlayın.
7. **Frontend'i gerçekten build'siz tutmak istiyor musunuz?** Tek-dosya
   CDN React, küçük/orta ölçekli bir dashboard için deploy'u basitleştirir
   ama component sayısı büyüdükçe (state yönetimi, çoklu sayfa) klasik bir
   build zinciri (Vite/Next.js) daha sürdürülebilir hale gelir. Bu şablon
   "büyümeyecek, tek sayfalık bir iç araç" varsayımıyla bu seçimi yaptı.

---

## 12. Referans: bu projenin somut dosya haritası

Yukarıdaki kalıpların gerçek karşılıklarını görmek isteyen için (bu proje
özelinde, domain detayları dahil):

- `app.py` — backend, route'lar, auth, admin uçları
- `pipeline/ingest.py`, `pipeline/measures.py`, `pipeline/groups.py`,
  `pipeline/composition.py`, `pipeline/compute.py` — hesaplama motoru
- `frontend/index_v30.html`, `admin.html` — sunum katmanı
- `Dockerfile`, `start.sh` — deployment
- `scripts/export_data_snapshot.py` — CLI taşınabilirlik aracı
- `docs/DATA_MIGRATION.md` — export/import özelliğinin adım adım kullanım
  kılavuzu (bu dosyadaki §8'in operasyonel/pratik karşılığı)
- `docs/PROJE_EL_KITABI.md` — bu projenin kendi verisi, kronolojisi ve
  yol haritası (bu dosyanın **kapsamadığı** her şey orada)

Bu dosyayı yeni bir projeye taşırken §1-11'i temel alın, §12'yi (ve
domain'e özgü her örneği) yeni projenin kendi dosya haritasıyla değiştirin.
