# Backlog — KT Rakip Analizi

Bu doküman iki bölümden oluşur: **(1) Ne yapıldı** — projenin başından bugüne
ayrıntılı kronoloji, **(2) Ne yapılacak** — yeni özellik istekleri + ertelenmiş
konular, öncelik sırasıyla.

**Kaynaklar:** `docs/CHANGELOG.md`, git geçmişi (`git log`), Claude'un proje
hafıza notları, bu konuşmanın kendisi. Tarihler kaynağında ne yazıyorsa öyle
aktarıldı — bkz. aşağıdaki tarih notu.

**⚠️ Tarih notu:** `docs/CHANGELOG.md`'deki en eski dönem "2025-05" tarihleriyle
etiketli, ama proje git geçmişi ve yoğun geliştirme 2026-08'de başlıyor. Bu
tutarsızlık, projenin **kullanıcılar arasındaki devir sürecinden** kaynaklanıyor
— yani "2025-05" dönemi muhtemelen önceki sahip/geliştiriciye ait, tam takvim
karşılığı netleşmedi. Tarihler kaynak dokümanlarda yazdığı gibi bırakıldı,
düzeltme yapılmadı.

**Son güncelleme:** 2026-08-25

---

# BÖLÜM 1 — Ne Yapıldı (Kronoloji)

## Dönem 0 — İlk kuruluş ("2025-05" etiketli, devir öncesi dönem)

Kaynak: `docs/CHANGELOG.md`. Bu dönemin git karşılığı yok (repo henüz git'e
alınmamıştı).

- **Faz 1 — Repo İskeleti.** İlk tasarım: README/ARCHITECTURE/MEASURES/
  EXTENDING/DEPLOYMENT dokümantasyonu, `pipeline/` modülleri (lookup, measures,
  groups, ingest, compute), `scripts/` (init_data, recompute), `data/catalog.json`
  + `display_config.json`.
- **v17 — Kompozisyon modu.** 5 kompozisyon × stack chart, banka/grup × tarih
  filtreleri, Bileşen/Döviz alt-sekmeleri.
- **v17 → v26 (9 iterasyon, özet).** Trend modu görünümleri (Değer/YtD/YoY/QoQ
  Büyüme/Pazar Payı) eklendi. TP/YP refactor denendi, BDDK detayında TP/YP
  olmayan kalemler nedeniyle **geri alındı** — yerine ana kalem üzerinden
  2-segmentli döviz dağılımı yaklaşımına geçildi. Snapshot'ta cascading dropdown
  (Kategori → Alt Kategori → Measure), sabit top-20 set'i, YtD yatay liste
  grafiği kuruldu.
- **v27 — Export modu.** 4. mode: banka/grup multi-select × tarih aralığı ×
  hiyerarşik measure ağacı → wide-format tablo + Excel/CSV indirme. SheetJS
  (CDN) + bağımlılıksız CSV fallback (UTF-8 BOM + `;` ayraç + ondalık virgül,
  Türkçe Excel uyumlu).
- **v28 — Pasifler wrap bug fix.**
- **v29 — Yeni 21 measure aktivasyonu.**
- **Faz 1.5 — Ham BDDK'dan tam hesaplama pipeline'ı.** v29'daki 128 measure'ın
  tamamını raw BDDK xlsx'lerinden Python ile yeniden üretme hedefi. Sonuç: KT
  2025-Q3'te 102/102 raw measure v29 baseline ile birebir eşleşti; 27 banka ×
  48 çeyrek × 128 measure'da **%91,8 exact match**. `MEASURE_FUNCS` (104) +
  `BASELINE_PASSTHROUGH` (24, raw'dan türetilemeyen kalemler) mimarisi kuruldu.
  **Kritik NBSP encoding bug'ı** bulundu: BDDK ham verisinde bazı kalem/tablo
  adlarında normal boşluk yerine non-breaking space (`\xa0`) var — normalize
  edilmeden `dis_ticaret_toplam` %0,49 (gerçek %14,95) çıkıyordu.

---

## Dönem 1 — Veri kaynağı arayışı (2026-08-02 → 2026-08-09)

- **2026-08-02:** `data/raw/` boş olduğundan, `datatable_1.xlsx` (zaten
  hesaplanmış PowerBI export'u) geçici birincil kaynak yapıldı
  (`scripts/load_datatable.py`, `pipeline/datatable.py`). Bu, `measures.py`/
  `groups.py`/`lookup.py`'yi fiilen ölü koda çeviriyordu — bilinen bir risk
  olarak not edildi.
- **2026-08-09:** Kullanıcı tam ham BDDK arşivini sağladı: **27 banka ×
  2013-Q4→2026-Q1, 1.170 dosya**, hepsi doğrulandı (dosya adı, banka eşleşmesi,
  KT 2025-09-30 referans değeriyle birebir). "Ham veriye geç, denetlediğimiz
  formülleri kullan" talimatıyla `measures.py`/`groups.py`/`lookup.py` yeniden
  birincil hesaplama yolu oldu; datatable dönemi geçmişe düştü.
- **2026-08-09 — kritik bug:** `/admin/rebuild`, `compute_all`'ı `base_data={}`
  ile çağırıyordu — bu, ham BDDK'da hiç bulunmayan 13 `BASELINE_PASSTHROUGH`
  measure'ı (SYR, Çekirdek SYR, RORWA, NIM, Spread vb.) **her rebuild'de
  siliyordu**. Düzeltme: rebuild artık mevcut computed.json'daki passthrough
  değerlerini `base_data` olarak taşıyor (self-sustaining).
- **2026-08-09 — tekrarlayan hata (3. kez):** macOS Türkçe karakterli dosya
  adlarını **NFD** (ayrışık), `catalog.json` **NFC** (birleşik) saklıyor — düz
  string karşılaştırması görsel olarak özdeş string'lerde bile sessizce
  `False` dönüyordu. 3 farklı yerde (logo embed script'i, "Rakip Analizi
  Veriler" doğrulaması, parquet banka adı filtresi) aynı hataya düşüldü.
  Kalıcı kural: karşılaştırmadan önce her iki tarafı da `NFC`'ye normalize et.

---

## Dönem 2 — Veri kalitesi, admin panel, performans (2026-08-09 → 2026-08-11)

- **2026-08-09 — `/admin/upload` 3 bug:**
  1. **422 hatası** — backend tekil `file`, frontend çoğul `files` gönderiyordu,
     upload hiç çalışmıyordu.
  2. **N dosya = N kere tam pipeline** (potansiyel 40 dk) — düzeltme: tüm
     dosyalar önce kaydedilir, pipeline tek sefer çalışır.
  3. **Kritik veri kaybı** — üzerine yazma + hata senaryosunda rollback, VAR
     OLAN dosyayı siliyordu (gerçekten oldu: Akbank/Denizbank 2014-06-30
     kaybedildi, orijinal kaynaktan geri yüklendi). Düzeltme: eski içerik
     belleğe alınır, hata durumunda geri yazılır.
  4. Aynı gün: `rebuild_parquet` `ProcessPoolExecutor` ile paralelleştirildi
     (10 çekirdek) — 1170 dosyalık arşivde 70,7sn → 14,8sn.
- **2026-08-11 — "Gerçek BDR" arşivine geçiş.** Kullanıcı "Rakip Analizi Güncel
  BDR'ler" klasörünü sağladı (22 banka, 1.117 dosya). 4 banka (Dünya Katılım,
  Emlak Katılım, Enpara, Hayat Finans) bu klasörde yoktu — eski arşivden
  dokunulmadan korundu. Sonuç: `data/raw/` 1.176 dosya, 27/27 banka.
- **2026-08-11 — veri kalitesi taraması.** Sistematik kontrol (Toplam Aktifler
  boş mu, aşırı `#VALUE!` var mı, temel measure'larda >%50 düşüş var mı) şunu
  buldu: **QNB Finansbank** (2013-2024 arası 42 dosya, Bloomberg/FactSet
  eklentisi olmadan export edilmiş, `#VALUE!` dolu), **Kuveyt Türk** (4 eski
  dosya boş hücreli), **Türkiye Finans** (5 dosya), **TOM Bank** (4 dosya),
  **HSBC** (1 dosya kısmen bozuk), **TEB** (1 dosya NFD/NFC yüzünden "var"
  gözükürken aslında yoktu), **Vakıf Katılım + Ziraat Katılım** (13 erken dönem
  dosyası, muhtemelen banka henüz kurulmamış → silindi, yanlış "0" göstermek
  yerine "veri yok" tercih edildi). 61 dosya eski arşivden geri yüklendi, 13
  dosya silindi.
- **2026-08-11 — otomatik kalite kontrolü.** `check_data_quality()` eklendi —
  upload öncesi Toplam Aktifler dolu mu / aşırı `#VALUE!` var mı kontrol eder,
  başarısızsa dosya `data/raw/`'a hiç yazılmaz.
- **2026-08-11 — incremental parquet güncelleme.** `update_parquet_incremental`
  — tek dosyalık upload artık TÜM 1176 dosyayı değil sadece yüklenen dosyayı
  okur (52sn → 33sn). `compute_all`/`build_group_data`/`composition` adımları
  BİLEREK hâlâ full-recompute (grup toplamları tüm bankaların güncel verisine
  muhtaç).
- **2026-08-11 — regresyon test suite.** `tests/` + pytest kuruldu (27 test):
  grup agregasyon birim testleri, veri kalitesi testleri, golden-value
  spot-check (KT+Akbank, 2018-12-31 referans).
- **2026-08-11 — coverage endpoint bug.** `/api/admin/coverage` yanıtında
  `banks_missing_latest` alanı hiç yoktu → "eksik banka" sayısı hep 0
  gösteriyordu, iki admin panel kutusu birbiriyle çelişiyordu.
- **2026-08-11 — kısmi çeyrek grup agregasyonu (3 bağımsız bug, aynı kök
  aileden):**
  1. Grup toplamları (Mevduat Bankaları vb.), üyelerden biri eksikse sessizce
     onu dışlayıp yanıltıcı küçük toplamlar üretiyordu → düzeltme: TÜM üyeler
     veri sağlamazsa `None` ("—") dönsün.
  2. Bu düzeltmenin YAN ETKİSİ: "banka henüz kurulmamış" (ör. Enpara ilk
     raporlama 2024-12-31) ile "banka bu çeyreği henüz raporlamadı" ayırt
     edilmiyordu — Mevduat Bankaları grubu 51 çeyrekten sadece 6'sında dolu
     çıkıyordu. `first_date_map` + `_active_members` ile düzeltildi.
  3. Frontend'de pazar payı hesabı da aynı sorundan etkileniyordu (kısmi
     çeyrekte payda küçülüp herkesin payı yapay şişiyordu) — `date_coverage`
     ile "güvenilir tarih" kontrolü eklendi.
- **2026-08-11 — güvenlik.** Sunucu `0.0.0.0`'a (ağdaki herkese açık) bağlıydı
  → `127.0.0.1`'e sabitlendi. Varsayılan admin şifresi zayıftı (`faruk`/
  `faruk123`) → `start.sh` ile güçlü şifre zorunlu kılındı.

---

## Dönem 3 — Üyelik, roller, formül hizalama, marka (2026-08-12)

- **Üyelik sistemi.** Açık kayıt (`/signup`) + admin onaylı giriş. İki ayrı
  yetki seviyesi: Basic Auth (admin, upload/rebuild) ve session tabanlı üyelik
  (`users.py`, bcrypt + `itsdangerous` imzalı çerez, sadece `/api/data` okuma).
  Admin, kendi Basic Auth şifresiyle de dashboard'a girebiliyor
  (`{KT_USERNAME}@admin.local`, `upsert_admin_account` ile otomatik senkron).
- **Rol tabanlı admin + banka grupları.** Onaylı bir üyeye "Admin Yap"
  denilince Basic Auth ile EŞ DEĞER tam yetki veriliyor. "Rakip Bankalar" gibi
  gruplar artık admin panelden CRUD edilebiliyor (`/api/admin/groups`), "Kuveyt
  Türk" grubu silinemez korunuyor.
- **PowerBI DAX formül hizalama.** Kullanıcının paylaştığı gerçek PowerBI DAX
  formülleriyle `composition.py` karşılaştırıldı, 4 fark bulundu: Menkul
  Kıymetler (ürün-türü → TFRS9 sınıflandırma bazlı), **Diğer Aktifler**
  (residual'dan **açık kalem toplamına** — en kritik fark), Pasif kompozisyon
  yapısı (Alınan Krediler ayrı bileşen oldu), Diğer Faaliyet Gelirleri
  (Temettü eksikti). Ayrıca yüzde normalizasyonu (mutlak değer bazlı, her
  zaman %100'e tamamlanan) uygulandı.
  **Kritik yan bulgu:** `ensure_data_dir()` modül seviyesinde çağrılıyordu,
  `ProcessPoolExecutor` worker'ları `app.py`'yi yeniden import edip bunu HER
  WORKER'DA tekrar tetikliyordu → eşzamanlı `users.json` yazımı yarış
  durumuna, `BrokenProcessPool` hatasına yol açıyordu. `MainProcess` kontrolü
  ile düzeltildi.
- **Dashboard header + tarih seçici.** Topbar'a merkezi KT logo + "Rakip
  Analizi" marka bloğu. Eski tek dropdown yerine Yıl/Çeyrek buton seçicisi
  (sonra Yıl, tıklanınca açılan listeye çevrildi).

---

## Dönem 4 — Deploy altyapısı + ölçü genişletme (2026-08-12 → 2026-08-18)

*Bu dönemden itibaren git commit geçmişi var.*

- **2026-08-12:** `git init`, ilk commit ("canlıya alma altyapısı"), GitHub'a
  private repo olarak push (`beligte10/rakip-analizi`).
- **~2026-08-14/15:** `measures.docx` (PowerBI DAX referansı) tam tarandı —
  catalog **127 → 160 ölçü**. 33 yeni measure (RAV, Toplam Risk, Likidite
  Açığı×7, vade dilimleri, Toplam Brüt/Canlı Krediler vb.) + **9 mevcut
  ölçünün paydası** ("X/Toplam Krediler" ailesi) net krediler yerine Toplam
  Brüt Krediler'e düzeltildi. Şube&Personel akım ölçüleri (net kar, personel
  gideri) TTM ile yıllıklandırıldı — ara çeyreklerdeki "testere-dişi" sorunu
  giderildi. Grup katmanı (`groups.py`) tüm bu düzeltmelerle senkronize
  edildi (banka-seviyesi bir formül değişince grup'un da güncellenmesi
  gerektiği, unutulursa dashboard'da sessiz tutarsızlık yarattığı öğrenildi).
- **Şifre değiştirme + ultra admin.** Üyeler kendi şifresini değiştirebiliyor.
  **Ultra admin** — tek bir hesaba (`faruk@admin.local`) özel, diğer
  adminlerin göremediği/dokunamadığı en üst yetki katmanı (env değişkeniyle
  tanımlı, UI'dan atanamaz).
- **catalog.json git'e alındı (seed mimarisi).** `catalog.json` çift doğalıydı
  (measures/compositions/banks = kod, groups = runtime/admin panelden
  düzenlenen). `catalog.seed.json` (git-tracked config kaynağı) + startup'ta
  canlı `groups`'u koruyarak merge eden mekanizma kuruldu — kod↔config
  uyumsuzluğu (bu turda pasif kompozisyonunda yaşanan) kökten çözüldü.
- **Deploy denetimi ve sertleştirme (14 madde bulundu, hepsi kapatıldı):**
  ağır endpoint'lerin (upload/rebuild) event loop'u bloke etmesi (→ `def`'e
  çevrildi, threadpool), eşzamanlılık kilidi, Dockerfile'ın gereksiz `data/`
  kopyalaması, prod bayrağı (HTTPS-only çerez + `/docs` kapatma), pinlenmemiş
  bağımlılıklar, root container, healthcheck yokluğu, login rate-limit,
  rebuild öncesi otomatik yedek, tek-worker güvencesi, auth test eksikliği.
- **UI iyileştirmeleri:** marka metni "Stratejik Kokpit" → "Rakip Analizi",
  measure arama kutusu, mode butonlarının yıl-çeyrek satırına taşınması, koyu
  mod okunabilirlik bug'ı (aktif sekme beyaz zemin üstünde beyaz yazı
  görünmez oluyordu).

---

## Dönem 5 — Canlıya alma (2026-08-18 → 19, deploy operasyonu)

*Bu dönem büyük ölçüde git commit'e dökülmedi — operasyonel/altyapı işlemleri.*

- Contabo VPS kiralandı (4 vCPU/8GB), Coolify kuruldu.
- GitHub App entegrasyonu ile otomatik webhook deploy (push-to-deploy) kuruldu.
- Kalıcı Docker volume (`/app/data`) + izin (uid 10001) ayarlandı, veri
  sunucuya taşındı.
- Domain (`kt-strateji.space`, Namecheap) + DNS + HTTPS (Let's Encrypt)
  kuruldu — birkaç deneme-yanılma sonrası (yanlış Port alanı, protokol
  ayarının kaydolmaması gibi Coolify UI sorunları) başarılı oldu.
- **Kaza (2026-08-19):** Admin panelden hem "Upload" hem "Rebuild" tetiklendi;
  sunucuda `data/raw/` arşivi henüz taşınmamış olduğundan Rebuild, TÜM geçmişi
  (51 dönem) silip yerine sadece o an yüklenen 1 dönemi yazdı. **Ders:**
  production'da normal güncelleme için sadece "Upload" kullanılmalı, "Rebuild"
  yalnızca tam arşiv sunucudayken güvenli.
- 2026-06-30 (yeni çeyrek) verisi locale eklendi, 24/27 banka raporlamış
  durumda (rebuild ile doğrulandı: 160 ölçü, 51 dönem, geçmiş korunmuş).
  Site tarafının aynı şekilde düzeltilmesi **beklemede** (kullanıcı "daha
  sonra siteyle ilgileniriz" dedi).

---

## Dönem 6 — Veri taşınabilirliği (2026-08-25)

- **Yeni belirti, aynı kök neden ailesi:** Kullanıcı, GitHub repo'yu indirip
  **başka (üçüncü) bir sunucuya** taşıdı — proje klasörü olduğu gibi zip'lenip
  yüklendi (`data/` dahil), sunucuya SSH erişimi yok. Sonuç: kod güncel ama
  dashboard'da sadece **2025-09** verisi görünüyor, 2025-12 → 2026-06 arası
  tamamen eksik. Neden: `data/` bilinçli olarak git'te değil (bkz. Dönem 5
  kazası) — zip'e dahil edilen `data/` kopyası hangi kaynaktan/ne zaman
  geldiği belirsiz, eski/donmuş bir sürümdü. Kod güncelliği ile veri
  güncelliği birbirinden bağımsız iki şey, ama bunu ayırt edecek/uyaracak
  hiçbir mekanizma yoktu — "hangi zip güncel" bilgisi tamamen elle takip
  ediliyordu.
- **Bu sunucu için düzeltme yapılamadı** (kullanıcının erişimi yok) — sadece
  ileriye dönük süreç iyileştirmesi olarak ele alındı.
- **Çözüm — İKİ tamamlayıcı araç:**
  1. **`/admin` panelinde "🚚 Sunucu Taşıma" bölümü (önerilen, SSH gerekmez):**
     `/admin/export-data` + `/admin/import-data` endpoint'leri (`app.py`) +
     admin.html'de iki buton. Kaynak sunucudan tek tıkla veri ZIP'i indirilir
     (manifest.json gömülü: ölçü/banka/dönem sayısı, tarih aralığı, git
     commit), hedef sunucunun admin paneline sürükle-bırakla yüklenir.
     İçe aktarmadan önce mevcut veri otomatik yedeklenir
     (`_backup_computed()`), bozuk/boş ZIP reddedilir. `users.json` isteğe
     bağlı (varsayılan hariç). SSH erişimi olmayan kullanıcı için asıl
     çözüm bu — tam da bu dönemin başındaki "sunucuya erişimim yok" ihtiyacı
     için tasarlandı.
  2. **`scripts/export_data_snapshot.py` (SSH + terminal erişimi olan
     durumlar için):** `data/computed.json`'dan HER ZAMAN taze bir paket
     üretir; içine gömülü `MANIFEST.txt` ile içeriği hedefe taşımadan ÖNCE
     doğrulanabilir kılar. `--include-raw` (tam ham arşiv, tam rebuild
     kapasitesi için), `--no-users` seçenekleri var.
- **`docs/DATA_MIGRATION.md` eklendi:** iki yöntemi karşılaştıran bir tablo +
  her ikisi için adım adım kılavuz + her iki yöntemde de geçerli olan
  Upload/Rebuild karışıklığı uyarısı (Dönem 5'teki kazaya doğrudan atıf).
- Test edildi: hem admin panel export→import round-trip'i (gerçek lokal
  veriyle, curl ve tarayıcıdan, manifest doğru üretiliyor, backup düzgün
  alınıyor, bozuk ZIP reddediliyor) hem CLI script'i (160 ölçü, 27 banka,
  son dönem 2026-06-30) çalıştırıldı — regresyon test suite'i (47 test)
  değişiklik sonrası yeşil.

---

## Açık/bekleyen konular (şu an, 2026-08-25 itibarıyla)

- **Site tarafında geçmiş veri eksik (Contabo/`kt-strateji.space`)** —
  `data/raw/` tam arşivin (178MB, ~1193 dosya) sunucuya taşınıp rebuild
  yapılması gerekiyor. Kullanıcı bunu ertelemeyi seçti.
- **Üçüncü, kullanıcının SSH erişimi olmadığı bir sunucuda veri Eylül
  2025'te donmuş** — artık SSH gerekmiyor: o sunucunun `/admin` paneline
  tarayıcıdan girebilen biri, bu makinedeki `/admin`'den indirilecek güncel
  bir ZIP'i "İçe Aktar" ile yükleyebilir. Şu an aktif bir aksiyon yok,
  araç hazır.
- **`ktstrateji.com/kokpit`'e taşıma isteği — ERTELENDİ (2026-08-19).**
  `kt-strateji.space`'i, GoDaddy'de kayıtlı ama içeriği bağımsız bir platformda
  barınan `ktstrateji.com`'un `/kokpit` alt-yoluna taşıma fikri gündeme
  gelmişti. Kullanıcı kararı: **şimdilik `kt-strateji.space` üzerinden devam
  edilecek**, taşıma işi ileriye ertelendi. Tekrar gündeme gelirse: `ktstrateji.com`
  bağımsız bir platformda (Varnish/Fastly cache + StatiCrypt şifreli statik
  sayfa görüldü, hangi araç olduğu netleşmemişti) barınıyor — path-bazlı
  yönlendirme o platformun kendi ayarlarından yapılmalı, bu VPS'ten değil.
- **measures.docx taramasından kalan 1 madde** (veri eksikliği nedeniyle
  henüz eklenmedi):
  - *Zorunlu Karşılıklar / Diğer Pasifler / DEK Krediler* — ham BDDK verisinde
    karşılığı yok veya belirsiz, tahmin yürütülmedi.
  - ~~*Toplam Kredi Kartları*~~ — **KARAR VERİLDİ (2026-08-19):** DAX
    formülüne birebir sadık kalınacak (3. terim 2. ile aynı kalır, YP kartlar
    dahil edilmez) — mevcut implementasyon zaten bu şekilde, değişiklik
    gerekmiyor. Kapatıldı.

---

# BÖLÜM 2 — Ne Yapılacak (Backlog)

## 🔴 Sprint 1 (küçük işler, hemen başlanabilir)

### 1. What's New butonu
**Ne:** Topbar'a, son değişiklikleri gösteren bir "Yenilikler" butonu.
**KARAR (2026-08-19):** İçerik elle güncellenen basit bir liste olacak
(`data/whats_new.json` gibi) — her önemli değişiklikte kısa, kullanıcı-dostu
bir not eklenecek.
**Durum:** 📋 Backlog'da, uygulanmayı bekliyor.

### 2. Role-bazlı ölçü erişimi + PDF export (BİRLEŞİK — birbirine bağımlı)
**KARAR (2026-08-19):** Bu iki madde aslında tek bir özellik seti — ayrı ayrı
değil, birlikte planlanmalı:
- **Role sistemi:** Birden fazla özel rol tanımlanacak (basit "yönetici/analist"
  değil — kaç rol ve isimleri henüz netleşmedi). Her role, **hangi
  ölçülere/measure'lara erişebileceği ayrı ayrı atanacak** (measure-seviyesinde
  izin, sadece özet/detay ayrımı değil).
- **PDF export:** Bir kullanıcı, **kendi rolüne atanmış tüm ölçüleri kalem
  kalem** (her ölçü kendi çıktısıyla, çoklu-sayfa) PDF olarak indirebilecek.
**Bağımlılık:** PDF export, role sisteminden ÖNCE ya da onunla BİRLİKTE
kurulmalı — rolsüz bir "hangi ölçüler dahil olsun" kapsamı tanımlanamaz.
**Açık soru:** Kaç rol olacak, isimleri ne, hangi rol hangi ölçülere erişsin?
**Durum:** 📋 Backlog'da, rol listesi netleşince başlanabilir.

---

## 🟠 Sprint 2 adayı

### 3. OTP güvenlik özelliği
**KARAR (2026-08-19):** Teslimat yöntemi **e-posta**. Mevcut altyapıda SMTP
entegrasyonu yok — bu, alt-görev olarak eklenmeli (bkz. üyelik sistemi,
`users.py`/`app.py`).
**Durum:** 📋 Backlog'da, uygulanmayı bekliyor.

### 4. Chat LLM entegrasyonu (2 fazlı)
**KARAR (2026-08-19):** Aşamalı yaklaşım:
- **Faz 1 (önce):** Dar kapsamlı — sadece bu dashboard'un verisini (computed.json/
  ölçüler) yorumlayan bir asistan. Daha ucuz, kullanıcının role-bazlı ölçü
  erişimine (bkz. madde 2) saygı gösterebilir.
- **Faz 2 (sonra):** Genel amaçlı, geniş kapsamlı bir asistana genişletilecek.
**Açık soru (Faz 1 için):** Hangi LLM/API, kim ödeyecek?
**Durum:** 📋 Backlog'da, Faz 1 kapsamı netleşince başlanabilir.

---

## 🟣 Büyük R&D projesi (kendi spike'ı gerekiyor)

### 5. Rasyonet'in yerine BDR otomasyonu (Claude destekli)
**Ne:** Bankaların yayımladığı Bağımsız Denetim Raporu PDF'lerinden (bkz.
bdr-kisayol.netlify.app) ilgili kalemleri otomatik çekip, Rasyonet'in bugün
ürettiğiyle aynı Excel formatında çıktı üretmek.
**Neden büyük:** Yüzlerce sayfa/kalem, hassas finansal veri — doğrulama şart.
**Önerilen yaklaşım:** 1 banka/1 dönem spike, mevcut Rasyonet çıktısıyla
satır satır karşılaştırma.
**Açık soru:** Örnek Rasyonet Excel çıktısı var mı? Hedef tam otomasyon mu,
elle tetiklenen bir araç mı?
**Durum:** 🔬 Keşif aşamasında, örnek dosya bekleniyor.

---

## 🔵 v2'ye ertelenmiş konular (daha önce karara bağlanmış, unutulmasın)

### 6. Konfigüre edilebilir odak banka
**Ne:** Kuveyt Türk yerine başka bir bankayı "odak" yapabilme.
**Neden ertelendi:** Grup katmanının kırılgan geçmişi (bkz. Dönem 2'deki
grup agregasyon bug'ları) nedeniyle riskli bulundu.
**Uygulama haritası hazır** (Claude'un hafıza notunda) — v2'de sıfırdan
araştırma gerekmeyecek: `KT_NAME` sabiti `DATA.meta.odak_banka`'ya
bağlanacak, `PROTECTED_GROUPS` ve varsayılan grup üyeliği odağa göre
güncellenecek.
**Durum:** ⏸️ v2'ye ertelendi.

### 7. Screenshot / PDF-öncesi PNG indirme
**Ne:** Bulunduğun görünümü PNG olarak indirme butonu.
**Neden ertelendi:** Kullanıcı v2'de yapmaya karar verdi.
**Durum:** ⏸️ Kod `feature/v2-screenshot` branch'inde hazır (2 commit),
Firefox'ta `toBlob` SecurityError sorunu vardı, son fix canlı doğrulanmadı —
v2'de ya bu fix'i test et ya da native `getDisplayMedia`'ya geç.

---

## ⚙️ Süreç

- **Backlog dokümanı:** ✅ Bu dosya (son güncelleme 2026-08-25).
- **Otomatik güncelleme talimatı (2026-08-25):** Bundan sonra yapılan her
  büyük işlemde bu dosya VE görsel HTML artifact'ı sorulmadan güncellenecek.
- **Zaman planı:** 📋 Sprint 1 tamamlanınca tarih hedefleri eklenecek.
- **Sprint oluşturma:** ✅ Sprint 1 yukarıda tanımlı. Rasyonet otomasyonu
  boyutu nedeniyle sprint'e alınmadı, önce spike gerekiyor.
