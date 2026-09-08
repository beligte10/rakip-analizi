# KT Rakip Analizi — Proje El Kitabı

**Son güncelleme:** 2026-09-08 · **Hedef okuyucu:** projeyi devralacak geliştirici

Bu dosya projenin **tek doğru kaynağıdır**: ne olduğu, nasıl çalıştığı, nasıl
işletildiği, bugüne kadar ne yapıldığı ve bundan sonra ne yapılacağı burada.
Daha önce bu bilgi `BACKLOG.md`, `PDF_FAZI_YOL_HARITASI.md` ve `CONTEXT.md`
arasında dağılmıştı; üçü bu dosyada birleştirildi ve kaldırıldı.

**Okuma sırası önerisi**
1. Projeyi hiç bilmiyorsanız: §1 → §2 (çalıştırın) → §3 (nasıl çalışıyor)
2. Veri yükleyecekseniz: §4 (işletme) — özellikle §4.2
3. Koda dokunacaksanız: §5 (tuzaklar) **önce okunmalı**, sonra §3
4. "Neden böyle yapılmış?" sorusu için: §9 (kararlar günlüğü) ve §6 (kronoloji)

**Derinlik dokümanları** (bu dosya özetler, detay oradadır):
`docs/ARCHITECTURE.md` (storage şeması) · `docs/MEASURES.md` (160 ölçünün
formülleri) · `docs/MEASURE_LISTESI.md` · `docs/EXTENDING.md` (yeni ölçü/banka
/grup ekleme adımları) · `docs/DATA_MIGRATION.md` (sunucu göçü) ·
`docs/CHANGELOG.md` (sürüm geçmişi)

---

## 1. Proje nedir

Türk bankacılık sektörü için **rakip analiz dashboard'u**. BDDK'nın kamuya
açık çeyreklik verilerinden beslenir; Kuveyt Türk'ün rakipleri karşısındaki
konumunu büyüklük, pazar payı, büyüme ve rasyo bazında gösterir.

**Sahibi:** Kuveyt Türk Strateji ekibi · **Canlı:** kt-strateji.space

**Bir bakışta**

| | |
|---|---|
| Banka | 27 |
| Dönem | 51 çeyrek (2013-12-31 → 2026-06-30) |
| Ölçü | 160 (147'si ham veriden hesaplanıyor, 13'ü dış kaynaktan taşınıyor) |
| Ham veri | ~1.193 xlsx, 2,85M satır konsolide |
| Banka grubu | 5 (Kuveyt Türk, Mevduat Bankaları, Rakip Bankalar, Katılım Bankaları, KT Hariç Katılım) |
| Görünüm | 4 mod: Anında Görünüm, Trend, Kompozisyon, Dışa Aktar |
| Test | 66 (pytest) |

**Neyi çözüyor:** Daha önce bu analiz, dışarıdan satın alınan hazır Excel
çıktıları (Rasyonet) ve elle hazırlanan PowerBI raporlarıyla yapılıyordu.
Sistem, ham BDDK verisinden başlayıp tüm rasyoları kendisi hesaplayarak bu
bağımlılığı kaldırmayı hedefliyor — bu geçiş hâlâ sürüyor (bkz. §8.3).

---

## 2. Hızlı başlangıç

**Gereksinimler:** Python 3.11+, ~500 MB disk (veri dahil)

```bash
cd "Rakip Analizi"
pip install -r requirements.txt
./start.sh                      # http://127.0.0.1:7860
```

> ⚠️ **`python3 app.py` ile başlatmayın.** `start.sh`, admin şifresini ve
> ultra-admin kimliğini ortam değişkeni olarak verir; doğrudan çalıştırma
> zayıf varsayılan şifreye düşer.

**Giriş:** Dashboard üyelik ister. Admin, kendi Basic Auth şifresiyle
`/login` üzerinden `{KT_USERNAME}@admin.local` hesabıyla girer (bu hesap her
açılışta otomatik senkronlanır). Admin paneli ayrıca `/admin` adresinde
HTTP Basic Auth ile korunur.

**Testler:**
```bash
python3 -m pytest tests/ -q     # 66 test
```

**Kod değiştirdiyseniz sunucuyu yeniden başlatın** — `uvicorn` `reload=False`
ile çalışıyor (bilinçli: tek worker garantisi için, bkz. §5).

---

## 3. Sistem nasıl çalışıyor

### 3.1 Veri akışı

```
BDDK xlsx (1 banka × 1 dönem)
      │  pipeline/ingest.py — parse + kalite kontrolü
      ▼
data/raw/<Banka>/<Banka> - GG.AA.YYYY.xlsx        ← ham arşiv, dokunulmaz
      │  update_parquet_incremental / rebuild_parquet
      ▼
data/veriler.parquet    (long format, 2,85M satır)
      │  pipeline/compute.py  → measures.py (147 ölçü)
      │  pipeline/groups.py   → grup toplamları
      │  pipeline/composition.py → kompozisyon + TP/YP
      ▼
data/computed.json      (dashboard'un okuduğu tek dosya, ~10 MB)
      │  FastAPI /api/data
      ▼
frontend/index_v30.html (React, CDN — build adımı yok)
```

**Temel ilke:** Frontend hesaplama yapmaz. Yeni bir ölçü eklemek yalnızca
pipeline tarafını ilgilendirir; frontend `computed.json`'u render eder.

### 3.2 Dosya yapısı

```
app.py                 FastAPI backend — tüm route'lar, auth, admin uçları (~2.000 satır)
users.py               üyelik katmanı (bcrypt + imzalı çerez)
catalog.seed.json      ölçü/kompozisyon/banka tanımları (git-tracked kaynak)
whats_new.json         "Yenilikler" penceresi içeriği

pipeline/
  ingest.py            xlsx → parquet, kalite kontrolü, dosya adı doğrulama
  lookup.py            LookupContext — parquet üzerinde kalem arama
  measures.py          147 ölçünün formülleri (en büyük dosya, ~1.365 satır)
  groups.py            grup toplamları / ağırlıklı rasyolar
  composition.py       kompozisyon ve TP/YP dağılımı
  compute.py           orkestratör (compute_all)
  datatable.py         ESKİ — PowerBI export yolu, artık kullanılmıyor

frontend/
  index_v30.html       dashboard (React CDN, ~4.800 satır, tek dosya)
  admin.html           admin paneli
  login.html, signup.html
  logos/               banka logoları

scripts/               CLI araçları (init_data, recompute, export_data_snapshot…)
tests/                 pytest (66 test)
data/                  GİT'TE DEĞİL — canlı veri (bkz. §5)
```

### 3.3 Veri formatları

**`data/veriler.parquet`** — long format, 8 kolon:

| Kolon | Tip | Açıklama |
|---|---|---|
| Tarih | datetime | Çeyrek sonu |
| Banka Adı | category | Görünen ad ("Kuveyt Türk") |
| Banka Türü | category | Mevduat \| Katılım |
| Tablo Türü | category | Ana Tablo \| … |
| Tablo Adı | category | Bilanço, Gelir Tablosu, Şube-Personel… (45 tablo) |
| Kalem Adı | category | BDDK kalem adı, orijinal Türkçe (1.891 farklı kalem) |
| Para Birimi | category | Toplam \| TP \| YP |
| Tutar | float64 | TL |

**`data/computed.json`** — dashboard payload'u:
```
meta              banka listesi, gruplar, tarihler, kapsam, top-20
catalog           160 ölçünün metadata'sı
bank_data         [ölçü][banka][tarih] = değer
group_data        [ölçü][grup][tarih] = {value: …}
composition_data  5 kompozisyon
currency_data     4 TP/YP dağılımı
timestamp         üretim zamanı
```

**`catalog.seed.json` ↔ `data/catalog.json`** — seed git'te tutulur (ölçü/
kompozisyon/banka tanımları = kod), runtime kopyası `data/`'da yaşar ve
admin panelden düzenlenen **grup üyeliklerini** korur. Açılışta seed'den
senkronlanır: config tazelenir, gruplar korunur.

### 3.4 Ölçü sistemi

- **`MEASURE_FUNCS` (147)** — ham veriden hesaplanır. Her fonksiyonun
  docstring'inde DAX-eşdeğer formülü vardır.
- **`BASELINE_PASSTHROUGH` (13)** — ham BDDK verisinde karşılığı olmayan ya
  da henüz türetilmemiş ölçüler (SYR, Çekirdek SYR, NIM, Spread, RORWA,
  Maliyet/Gelir…). Bunlar eski PowerBI baseline'ından **taşınır**, yani her
  yeni çeyrekte bir dönem geride kalırlar. Bu bilinçli bir borç ve
  kapatılması planlanıyor (§8.3, FAZ 3).

Ölçü metadata'sı: `id, ad, tip (buyukluk|rasyo), akim_stok, birim, kategori,
alt_kategori, pazar_payi, sort_direction`. **Açıklama alanı henüz yok** —
bilgi baloncukları fazında eklenecek (§8.3, FAZ 4).

Yeni ölçü ekleme adımları: `docs/EXTENDING.md`.

### 3.5 Grup katmanı ve kısmi çeyrek kuralı

Grup toplamları `pipeline/groups.py`'da **tek yerde** tanımlıdır; hem
`app.py` hem `scripts/recompute.py` aynı fonksiyonu çağırır.

- Büyüklükler: üyelerin toplamı
- Rasyolar: **ağırlıklı ortalama** (Σpay / Σpayda) — basit ortalama değil

**Kritik kural:** Bir grup, üyelerinden biri o dönemi raporlamamışsa `None`
("—") döner. Yanıltıcı küçük toplam üretmektense veri yok demeyi tercih
ediyoruz. "Banka henüz kurulmamış" ile "bu çeyreği henüz raporlamadı" ayrımı
`first_date_map` ile yapılır (bkz. §5).

### 3.6 Kimlik doğrulama — iki ayrı katman

| Katman | Kim | Nasıl | Neye erişir |
|---|---|---|---|
| **Basic Auth** | Kök admin | `KT_USERNAME` / `KT_PASSWORD` | `/admin` paneli, tüm admin uçları |
| **Üyelik oturumu** | Üyeler | `/signup` → admin onayı → `/login` | Sadece `/api/data`, `/api/catalog` |

Onaylı bir üyeye admin panelden `role='admin'` verilebilir — bu, Basic Auth
ile **eş değer tam yetki** demektir (kısmi yetki yok). Ayrıca tek hesaba özel
**ultra admin** katmanı vardır (`KT_ULTRA_ADMIN_EMAIL`): diğer adminler bu
hesabı üye listesinde göremez ve üzerinde işlem yapamaz.

### 3.7 Koruma katmanları

Veri yazan her akışta sırayla:

1. **Ağır işlem kilidi** — upload/rebuild aynı anda çalışamaz (409 döner)
2. **Kalite kontrolü** — bozuk xlsx `data/raw/`'a hiç yazılmaz
3. **Otomatik yedek** — `_backup_computed()`, son 5 kopya `data/backups/`
4. **Boşluk kilidi** — sonuç tamamen boşsa yazma
5. **Regresyon kilidi** — sonuç mevcut veriden küçükse (ölçü/banka/dönem
   düşüyor ya da dolu hücre %2'den fazla azalıyor) **409 ile reddedilir**;
   admin panelde "Veri azalmasına izin ver" kutusuyla bilinçli olarak
   zorlanabilir
6. **Atomik yazım** — `.tmp` + `replace`
7. **Açılışta kurtarma** — `computed.json` bozuksa son sağlam yedeğe dönülür,
   bozuk dosya `computed.corrupt_<zaman>.json` olarak saklanır ve admin
   panelde uyarı gösterilir

---

## 4. İşletme rehberi

### 4.1 Yeni çeyrek yükleme

1. 27 bankanın xlsx'ini `<Banka Adı> - GG.AA.YYYY.xlsx` formatında hazırla
   (tarih çeyrek sonu olmalı: 31.03 / 30.06 / 30.09 / 31.12)
2. `/admin` → **📤 Veri Yükleme** → dosyaları sürükle
3. Sistem sırasıyla: yedek alır → her dosyayı doğrular → `data/raw/`'a yazar
   → parquet'i **sadece yeni dosyalar için** günceller → tüm bankalar için
   ölçüleri yeniden hesaplar → `computed.json`'u atomik yazar
4. **Veri Durumu** sekmesinden kapsamı doğrula (ör. "27 / 27")

Süre: 27 dosya ≈ 40 saniye.

### 4.2 Upload vs Rebuild — bunu karıştırmayın

| | **Upload** | **Rebuild** |
|---|---|---|
| Ne yapar | Sadece yüklenen dosyaları işler, mevcut veriye **ekler** (upsert) | `data/raw/`'ın **tamamını** okuyup her şeyi sıfırdan hesaplar |
| Ne zaman | **Normal çeyrek güncellemesi — varsayılan bu** | Pipeline'da formül değişikliği yaptıysanız |
| Risk | Yok; aynı banka+tarih temiz şekilde değişir | Sunucuda ham arşiv eksikse **geçmişi siler** |

> 🔴 2026-08-19'da canlıda Rebuild'e basıldı; sunucuda ham arşiv olmadığı
> için 51 dönemlik geçmiş silinip yerine 1 dönem yazıldı. Bugün regresyon
> kilidi bunu durdurur, ama **canlıda Rebuild'e basmayın** — ham arşiv
> yalnızca yerel makinede.

### 4.3 Sunucu taşıma

İki yol var, ikisi de `docs/DATA_MIGRATION.md`'de adım adım:

- **Admin panelden (SSH gerekmez, önerilen):** `/admin` → Sunucu Taşıma →
  "Veriyi İndir" → hedef sunucuda "İçe Aktar". Paket içinde manifest vardır
  (kaç ölçü/banka/dönem, hangi tarihe kadar) — yüklemeden önce doğrulayın.
- **CLI (SSH varsa):** `python scripts/export_data_snapshot.py` → `scp` →
  Docker volume'a aç → `chown -R 10001:10001` → container restart.

> **`data/` klasörünü asla elle zip'leyip taşımayın.** Git'te olmadığı için
> hangi kopyanın güncel olduğu belirsizleşir; 2026-08'de tam bu yüzden bir
> sunucuda Eylül 2025'te donmuş veri yayına çıktı.

### 4.4 Yedekleme ve kurtarma

- Her yazım öncesi otomatik: `data/backups/computed_<zaman>.json` (son 5)
- Elle tam yedek: `computed.json` + `veriler.parquet` kopyalayın
- `computed.json` bozulursa: sistem açılışta kendi kurtarır; müdahale
  gerekmiyorsa yalnızca admin panelindeki uyarıyı okuyun

### 4.5 Canlı ortam

| | |
|---|---|
| Sunucu | Contabo VPS (4 vCPU / 8 GB) |
| Orkestrasyon | Coolify · Traefik · Let's Encrypt |
| Domain | kt-strateji.space (Namecheap) |
| Deploy | GitHub App webhook — `main`'e push = otomatik deploy |
| Veri | Kalıcı Docker volume (`/app/data`), uid 10001 |
| Container | Non-root, healthcheck'li, tek worker |

**Kod ve veri birbirinden bağımsızdır:** push kodu günceller, `data/` volume'a
dokunmaz. Yeni sunucuya taşırken kod GitHub'dan gelir ama **veri gelmez** —
§4.3'teki yöntemlerden birini kullanın.

---

## 5. Tuzaklar — koda dokunmadan önce okuyun

Bunların her biri gerçekten yaşandı ve zaman kaybettirdi.

1. **NFD / NFC Türkçe karakter tuzağı (3 kez düşüldü).** macOS dosya adlarını
   NFD (ayrışık), JSON'lar NFC (birleşik) saklar. `"Dünya Katılım" ==
   "Dünya Katılım"` **sessizce `False` döner**. Karşılaştırmadan önce her iki
   tarafı da `unicodedata.normalize('NFC', s)` yapın.

2. **NBSP (`\xa0`) tuzağı.** BDDK ham verisinde bazı kalem/tablo adlarında
   normal boşluk yerine kırılmaz boşluk var. Normalize edilmezse ölçü %0,49
   çıkar (gerçeği %14,95).

3. **`reload=False` — kod değişince sunucu restart şart.** Bilinçli tercih:
   tek worker garantisi (kilitler ve rate-limit in-process).

4. **Tek worker zorunlu.** `users.json` kilidi, ağır işlem kilidi ve login
   rate-limit hepsi in-process. `--workers>1` bunları bozar.

5. **`ensure_data_dir()` sadece MainProcess'te.** `ProcessPoolExecutor`
   worker'ları `app.py`'yi yeniden import ediyor; bu kontrol olmazsa her
   worker `users.json`'a yazmaya çalışıp `BrokenProcessPool` üretiyor.

6. **Grup, eksik üyede `None` döner.** Yeni bir grup ölçüsü eklerken bunu
   bekleyin; "0" veya kısmi toplam üretmeyin.

7. **`data/` git'te değildir.** Bilinçli: `git pull` canlı veriyi ezmesin
   diye. Sonucu: kod ile veri ayrı taşınır (§4.3).

8. **13 passthrough ölçü bir dönem geride.** Yeni çeyrek yüklediğinizde
   SYR/NIM/RORWA boş görünür — bu bug değil, bilinen borç (§8.3 FAZ 3).

9. **Excel dosya adı bilgi taşır.** Banka ve dönem dosya adından okunur;
   format bozuksa dosya reddedilir.

---
## 6. Ne yapıldı — kronoloji

Projenin başından bugüne dönem dönem: ne yapıldı, hangi bug bulundu,
hangi karar neden alındı. Bir davranışın nedenini ararken buraya bakın.


### Dönem 0 — İlk kuruluş ("2025-05" etiketli, devir öncesi dönem)

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

### Dönem 1 — Veri kaynağı arayışı (2026-08-02 → 2026-08-09)

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

### Dönem 2 — Veri kalitesi, admin panel, performans (2026-08-09 → 2026-08-11)

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

### Dönem 3 — Üyelik, roller, formül hizalama, marka (2026-08-12)

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

### Dönem 4 — Deploy altyapısı + ölçü genişletme (2026-08-12 → 2026-08-18)

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

### Dönem 5 — Canlıya alma (2026-08-18 → 19, deploy operasyonu)

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

### Dönem 6 — Veri taşınabilirliği (2026-08-25)

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
- **Admin panele "🗺️ Yol Haritası" sekmesi eklendi.** Yeni
  `GET /admin/backlog` endpoint'i `docs/BACKLOG.md`'yi ham metin döner,
  admin.html `marked.js` (CDN) ile render edip gösterir — bu dosya git ile
  deploy edildiği için (data/'nın aksine) canlıda da her zaman güncel;
  kullanıcının "backlog dosyasına admin panelinden erişilmesini istiyorum"
  talebiyle eklendi.
- **Bug (aynı gün, canlıda bulundu): "Yol Haritası" 404 veriyordu.**
  `docs/` hem `.dockerignore`'da hariç tutuluyordu hem Dockerfile'da
  `COPY` edilmiyordu — yani `BACKLOG.md` image'a hiç girmiyordu. `docs/`
  hariç tutması `data/`'nın gizlilik/boyut mantığıyla karışıp yanlışlıkla
  genişletilmişti. Düzeltme: `.dockerignore`'dan `docs/` satırı kaldırıldı,
  `Dockerfile`'a `COPY docs/ docs/` eklendi (~100KB, image'ı şişirmiyor).
- **"Yenilikler" butonu yapıldı** (yukarıda Bölüm 2, madde 1 — artık kapalı).
- **Ölü deploy dosyaları kaldırıldı (2026-08-25).** `docker-compose.yml`,
  `Caddyfile`, `.github/workflows/deploy.yml` — Coolify'a geçmeden önce
  planlanan eski bir "kendi Caddy + GitHub Actions SSH deploy" yaklaşımından
  kalmıştı, gerçek canlı deploy hiç bunlara dokunmuyordu (Coolify kendi
  webhook + Traefik + Dockerfile sürecini kullanıyor). Repo'yu incelerken
  kafa karıştırdığı fark edilince silindi; `app.py`'deki ilgili güvenlik
  yorumu (`HOST=0.0.0.0` gerekçesi) Coolify/Traefik'e güncellendi.
- **Admin panelde "Yol Haritası" başlıkları accordion'a çevrildi.**
  Marked.js ile render edilen H2 (Dönem/tier başlıkları) ve H3 (tekil
  backlog maddeleri) artık DOM'da runtime'da sarmalanıp tıklanınca açılan/
  kapanan bölümlere dönüştürülüyor (varsayılan hepsi kapalı) — uzun
  dokümanı taramak kolaylaştı.

---

### Dönem 7 — Dashboard okunurluk ve kullanılabilirlik turu (2026-09-08)

Kullanıcının tek seferde ilettiği 6 maddelik iyileştirme listesi; her biri
uygulanmadan önce belirsiz noktalar (terim karşılıkları, sıralama referansı,
seçim hafızasının kapsamı, panel düzeni) kullanıcıya sorulup karara bağlandı.

- **Kompozisyon görünümü okunurluğu.** Geniş ekranda 3 yerine **2 panel yan
  yana** (grid min genişliği 360 → 520px), bar genişliği **60 → 110px**,
  bar yüksekliği 240 → 300px, tüm fontlar büyütüldü (segment yüzdesi 10 →
  12,5px, tarih etiketi 11 → 12,5px, panel başlığı 13 → 16px, lejant 11 →
  12,5px). Barlar yükseldiği için segment etiketi eşiği %6 → %5'e indi
  (daha küçük dilimler de yüzdesini gösteriyor).
- **Türkçeleştirme.** `(agrega)` → **`(grup toplamı)`**, `Measure` →
  **`Ölçü`**, `Snapshot` → **`Anında Görünüm`**, `Export` → **`Dışa Aktar`**,
  dışa aktarılan dosya adı `KT_Cockpit_Export_*` → `KT_Rakip_Analizi_*`
  (eski "Cockpit" markası da temizlendi). **KARAR:** YtD / YoY / QoQ / CAGR
  / Bps bankacılıkta yerleşik kısaltmalar olduğu için çevrilmedi.
- **Banka listesi sıralaması (Trend + Kompozisyon).** Kuveyt Türk her zaman
  başta, gerisi Toplam Aktifler büyüklüğüne göre azalan. **KARAR:** referans
  dönem sabit — üstteki yıl/çeyrek seçimi değişince chip'lerin yeri
  oynamasın diye "seçili dönem" değil, her bankanın en son veri verdiği
  dönem kullanılıyor (son çeyreği raporlamamış banka listenin dibine
  düşmüyor).
- **Trend grafiğinde seri adları.** Sol üstte grafiğin içini kapatan lejant
  kaldırıldı; adlar artık **çizginin bittiği yerde değerin yanında**
  ("Kuveyt Türk  1,47T"). Aynı hizaya düşen etiketler dikeyde en az 15px
  ayrıştırılıyor, kaydırılan etiket kendi veri noktasına ince bir bağ
  çizgisiyle bağlanıyor. Sağ boşluk 80 → 200px.
- **X ekseni tarih etiketlerinde adaptif seyreltme.** Trend'deki eski kural
  (her `n/10`'uncu etiket + "sonu her zaman yaz") 16-19 dönemlik
  aralıklarda çakışma üretiyordu; artık sığan etiket sayısı çizim
  genişliğinden hesaplanıp etiketler **sondan geriye eşit aralıkla**
  seçiliyor (en güncel dönem her zaman yazılı). Kompozisyonda bar alanının
  **gerçek genişliği ölçülüp** aynı mantık uygulanıyor — panel genişliği
  ekrana/sütun sayısına göre değiştiği için sabit bir kural yeterli
  olmuyordu. 51 dönem seçiliyken bile çakışma yok (tarayıcıda ölçülerek
  doğrulandı).
- **Sekme geçişlerinde seçimler korunuyor.** Trend ve Kompozisyon kendi
  `useState`'lerini kullandığı için sekme değişince bileşen unmount oluyor
  ve tüm seçimler (banka/grup, dönem, görünüm modu, yılsonu, alt sekme)
  varsayılana dönüyordu; state `App`'e taşındı. **KARAR:** iki sekme
  seçimini **ayrı** tutuyor, biri diğerini etkilemiyor.

Doğrulama: tarayıcıda uçtan uca test edildi — chip sırası, etiket çakışması
(trend ve kompozisyonda 0), sekme geçişinde state korunması, koyu mod
okunabilirliği, konsol hatası yok; 47 test yeşil.

**Aynı gün, ikinci tur (renk paleti + hover + eksen):**

- **Banka renkleri marka/logo paletlerine göre yeniden kuruldu.** Her banka
  kendi renk ailesinde kalıyor (yeşil / mavi / kırmızı / mor / turuncu),
  aynı ailedeki bankalar **parlaklık kademeleriyle** ayrılıyor — ton marka
  kimliğini taşıdığı için korunuyor. Repoda logosu bulunan 4 banka (KT, TEB,
  Vakıf Katılım, Ziraat Katılım) için renk doğrudan logo SVG'sinden alındı;
  kalan 23 banka için bilinen kurumsal renkler kullanıldı (kullanıcı kararı:
  "bildiğin marka renklerini kullan, sonra onaya sun" — palet görsel olarak
  onaya sunuldu). **Kuveyt Türk `#62AE41` olarak SABİTLENDİ**, kullanıcı
  belirledi, değiştirilmemeli.
  **Doğrulama:** CIELAB uzayında 27 rengin birbirine en yakın çifti
  **ΔE 15,4** (ayırt edilebilirlik eşiği ~15) — "aynı renkte iki banka"
  kalmadı. Palet üretimi/doğrulaması betikle yapıldı, elle göz kararı değil.
- **Paletin iki yan etkisi düzeltildi:** (1) yeni palette hem çok koyu
  (`#0B2E63`) hem çok açık (`#FFB600`) tonlar var; seçili chip'lerdeki sabit
  beyaz yazı açık zeminlerde okunmuyordu → `contrastTextOn()` eklendi (beyaz
  ve koyu adaydan WCAG kontrast oranı yüksek olanı seçer), 27 chip'in tamamı
  artık ≥ 4,5:1. (2) Trend çizgi/noktaları koyu modda kaybolmasın diye
  `darkSafeColor` tonuna geçti — açık modda marka renginin birebir kendisi.
- **Kompozisyonda hover ile tam yüzde.** Bar sütununa gelince o dönemin
  **tüm bileşenleri** tam hassasiyetle (2 ondalık) ve TL karşılığıyla
  listeleniyor, imlecin üzerindeki segment vurgulanıyor. Eskiden yalnızca
  geç açılan, stilsiz native `title` vardı ve %5'in altındaki segmentlerin
  yüzdesi hiçbir yerde görünmüyordu.
- **Y ekseni sıfır tabanı.** Tüm değerler pozitifken eksen artık negatife
  inmiyor. Alt pay (%8-10) dar aralıklı serilerde tabanı sıfırın altına
  itiyordu; "eksi büyüklük" diye bir şey olmadığı için yanıltıcıydı.
  **KARAR:** taban 0'a *kırpılıyor* (her zaman 0'dan başlamıyor) — böylece
  dar bantlı rasyolarda trend farkı ezilmiyor. Gerçekten negatif veri varsa
  (QoQ/YoY düşüşleri) eksen yine eksiye iniyor. Hem ana trend hem snapshot
  mini trendinde uygulandı.

---

### Dönem 8 — 2026Q2 tamamlandı + kritik pipeline bug'ı (2026-09-08)

- **Kullanıcı "BDR Veriler" klasörünü yükledi:** 27 banka × 30.06.2026, düz
  klasör, dosya adları pipeline formatına (`<Banka> - GG.AA.YYYY.xlsx`)
  birebir uygun. Yüklemeden önce içerik doğrulaması yapıldı: dosyalar
  mevcutlardan ~%25 küçüktü (geçmişte "eklentisiz export → bozuk veri"
  belirtisi buydu), ama satır/tablo/kalem sayıları ve Toplam Aktifler
  değerleri **birebir aynı** çıktı — fark yalnızca hücre formatlaması.
  24 bankanın verisi değişmiyor, **3 banka için 2026Q2 ilk kez geliyordu**
  (Dünya Katılım, Hayat Finans, TOM Bank).
- **KRİTİK BUG — yeni çeyrek hesaplanmıyordu (`pipeline/compute.py`).**
  27 dosya sorunsuz yüklenip parquet'e işlendiği hâlde 3 bankanın verisi
  dashboard'a yansımadı; coverage 24/27'de kaldı. Kök neden: `compute_all`,
  bir banka için hesaplanacak tarihleri **yalnızca baseline'dan** (mevcut
  `computed.json`) alıyordu; ham veri (parquet) tarihlerine ancak baseline
  o banka için TAMAMEN boşsa düşüyordu. Yani mevcut bir bankaya **yeni bir
  çeyrek** eklendiğinde o tarih baseline'da olmadığı için hiçbir measure
  hesaplanmıyordu. Upload akışı baseline ile çağırdığından bu yol **her
  yeni çeyrekte** tetikleniyordu — yani canlıda da her yeni dönem
  yüklemesinde aynı sorun yaşanacaktı.
  **Düzeltme:** tarih kümesi artık `baseline ∪ ham veri`. Baseline'da olup
  raw'da olmayan tarihler (passthrough geçmişi) korunur, raw'a yeni gelen
  dönemler hesaplanır.
- **Sonuç:** 2026-06-30 raporlayan banka **24/27 → 27/27**, coverage'da
  "eksik banka: YOK". Eksik üyeler tamamlanınca 2026Q2 için hesaplanamayan
  grup toplamları da geldi: **Katılım Bankaları "—" → 4.903.083 mn TL**,
  **KT Hariç Katılım "—" → 3.430.769 mn TL** (dashboard'da YtD %13,50 ve
  %15,59). Geçmiş bozulmadı: 1157 banka×dönem karşılaştırmasında **0
  değişiklik**; 51 dönem, 160 ölçü, kompozisyon/döviz payload'ları yerinde.
  47 test yeşil.
- İşlem öncesi `computed.json` + `veriler.parquet` elle yedeklendi
  (`data/backups/manuel_<zaman>/`); yükleme production'daki gerçek
  `/admin/upload` akışıyla yapıldı (kalite kontrolü, otomatik yedek,
  rollback ve kompozisyon üretimi bu akışın içinde).
- `BDR Veriler/` `.gitignore`'a eklendi — ham veri git'e girmez (`data/`
  ile aynı ilke).
- **computed.json sağlamlaştırıldı (aynı gün).** Mevcut korumalar yetersizdi:
  `_assert_nonempty_result` yalnızca sonucun TAMAMEN boş olmasını yakalıyordu,
  bu yüzden 2026-08-19'daki "51 dönem → 1 dönem" kazası kilidi geçmişti.
  İki katman eklendi (kullanıcı seçimi):
  1. **Regresyon kilidi.** Yazımdan önce yeni sonuç mevcut `computed.json` ile
     kıyaslanır; ölçü/banka/dönem sayısı düşerse ya da dolu hücre sayısı %2'den
     fazla azalırsa yazma **409 ile reddedilir**, mevcut veri korunur ve neyin
     ne kadar düştüğü raporlanır. Üç yazma akışında da devrede (upload,
     upload-zip, rebuild). **KARAR:** meşru küçülmeler için kaçış kapısı var —
     admin panelde "Veri azalmasına izin ver" onay kutusu.
  2. **Bozukluk kurtarma.** Açılışta `computed.json` okunamıyor/şeması bozuksa
     (yarım yazım, disk dolması) uygulama çökmek yerine `data/backups/`
     içindeki en yeni **sağlam** yedeğe döner; bozuk dosya
     `computed.corrupt_<zaman>.json` olarak saklanır ve admin panelde ne
     olduğunu anlatan bir uyarı gösterilir.
  **19 yeni test** eklendi (`tests/test_computed_guards.py`) — 2026-08-19
  kazasının birebir senaryosu dahil. Toplam 66 test yeşil.

---

## 7. Açık ve bekleyen konular


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

## 8. Yol haritası — ne yapılacak


### 🔴 Sprint 1 (küçük işler, hemen başlanabilir)

#### 1. What's New butonu
**Ne:** Topbar'a, son değişiklikleri gösteren bir "Yenilikler" butonu.
**KARAR (2026-08-19):** İçerik elle güncellenen basit bir liste olacak
(`data/whats_new.json` gibi) — her önemli değişiklikte kısa, kullanıcı-dostu
bir not eklenecek.
**Durum:** ✅ Yapıldı (2026-08-25). `whats_new.json` repo kökünde (git-tracked,
`data/` değil — `catalog.seed.json` deseniyle aynı), `GET /api/whats-new`
üzerinden servis ediliyor, dashboard topbar'ında "🆕 Yenilikler" butonu +
modal (BDR'nin yanından Çıkış'ın sonuna, logo bloğunun hemen öncesine
taşındı). Yeni bir sürüm notu eklemek için `whats_new.json`'a en üste yeni
bir `{date, title, items}` girdisi eklenip commit/push yeterli.
**Düzeltme (aynı gün):** İlk içerik yanlışlıkla admin-only özellikleri
(Sunucu Taşıma, Yol Haritası sekmesi) anlatıyordu — normal dashboard
kullanıcısı `/admin`'e erişemediği için bunları hiç göremezdi. İçerik
gerçekten dashboard'da görünen değişikliklere çevrildi (yeni ölçüler,
arama kutusu, CAGR düzeltmesi, koyu mod düzeltmesi vb.). **Ders:** Bu
buton için içerik yazarken her zaman "normal üye bunu dashboard'da görebilir
mi" testi uygulanmalı, admin panel değişiklikleri buraya girmemeli.

#### 2. Role-bazlı ölçü erişimi + PDF export (BİRLEŞİK — birbirine bağımlı)
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

#### 3. Passthrough ölçülerin ham veriden türetilmesi (13 ölçü)
**Ne:** SYR, Çekirdek SYR, NIM, Düzeltilmiş NIM, Spread, RORWA, Maliyet/Gelir,
Düzeltilmiş Maliyet/Gelir, Net Faiz Geliri/Ort. Aktifler, Gayrinakdi Krediler,
Gayrinakdi Kredi Komisyonları, Faiz Getirili Aktifler, BZK Sonrası Düzeltilmiş
NIM — bu 13 ölçü ham BDDK verisinden hesaplanmıyor, eski PowerBI baseline'ından
taşınıyor (`BASELINE_PASSTHROUGH`).
**Neden önemli:** Baseline sabit olduğu için bu ölçüler **her yeni çeyrekte bir
dönem geride kalıyor** — 2026Q2 yüklendiği hâlde 13'ünün de son dolu dönemi
2026-03-31. Kullanıcının "bir dahaki çeyrekte sadece veri yükleyeceğim, formül
türetmeyi de sistem içinden yapacağız" hedefinin önündeki tek engel bu.
**Fizibilite (2026-09-08 tespiti):** ham veride karşılıkları VAR —
`Sermaye Yeterlilik Rasyosu (%)`, `Çekirdek Sermaye Yeterliliği Oranı (%)`,
`Çekirdek Sermaye Toplamı`, `Net Faiz Geliri/Gideri` gibi kalemler
`Özkaynak Kalemlerine İlişkin Bilgiler` ve `Gelir Tablosu` tablolarında mevcut.
**Önerilen yöntem:** her ölçüyü tek tek türet, mevcut baseline değerleriyle
birebir karşılaştır (geçmiş dönemlerde tutuyorsa formül doğrudur), sonra
`MEASURE_FUNCS`'a taşı. SYR/Çekirdek SYR gibi doğrudan okunabilenlerle başla.
**Durum:** 📋 Backlog'da. **KARAR (2026-09-08):** kullanıcı "sadece
sağlamlaştırma, ölçüler sonra" dedi — bu iş ayrı bir tura bırakıldı.

---

### 🟠 Sprint 2 adayı

#### 3. OTP güvenlik özelliği
**KARAR (2026-08-19):** Teslimat yöntemi **e-posta**. Mevcut altyapıda SMTP
entegrasyonu yok — bu, alt-görev olarak eklenmeli (bkz. üyelik sistemi,
`users.py`/`app.py`).
**Durum:** 📋 Backlog'da, uygulanmayı bekliyor.

#### 4. Chat LLM entegrasyonu (2 fazlı)
**KARAR (2026-08-19):** Aşamalı yaklaşım:
- **Faz 1 (önce):** Dar kapsamlı — sadece bu dashboard'un verisini (computed.json/
  ölçüler) yorumlayan bir asistan. Daha ucuz, kullanıcının role-bazlı ölçü
  erişimine (bkz. madde 2) saygı gösterebilir.
- **Faz 2 (sonra):** Genel amaçlı, geniş kapsamlı bir asistana genişletilecek.
**Açık soru (Faz 1 için):** Hangi LLM/API, kim ödeyecek?
**Durum:** 📋 Backlog'da, Faz 1 kapsamı netleşince başlanabilir.

---

### 🟣 Büyük R&D projesi (kendi spike'ı gerekiyor)

#### 5. PDF fazı — BDR'den otomatik veri, türetilmiş formüller, etiketli erişim
**Ne:** Projenin bir sonraki büyük fazı. Veri girişi Excel'den **BDR PDF'lerine**
taşınır, tüm rasyolar sistem içinde türetilir, ölçülere açıklama/içgörü
baloncukları eklenir, kimin hangi ölçüyü göreceği etiketle belirlenir ve
kullanıcılar ham kalemlerden kendi formüllerini oluşturabilir.

**KARARLAR (2026-09-08, kullanıcıya sorularak netleştirildi):**
- Bugüne kadarki Excel verisi kalır; **2026Q3'ten itibaren** çeyreklik
  güncellemeler tamamen PDF üzerinden.
- **Arada Excel olmasın** — PDF doğrudan Python veri katmanına yazsın.
- PDF'leri **sistem otomatik indirsin** (bdr-kisayol panosu).
- Kullanıcı formülleri **ham BDDK kalemleri** üzerinden; sadece oluşturan
  görür; **log tutulur**; **şimdilik canlıya alınmayacak** (özellik bayrağı).
- Baloncuk içeriğini **Claude taslak üretir, kullanıcı onaylar**; metin
  statik tutulur (her açılışta LLM çağrısı yok).
- Etiket: bir kullanıcıya **birden fazla**; etiket → **tekil ölçü seçimi**;
  filtreleme **sunucu tarafında**.

**Fizibilite (doğrulandı):** BDR PDF'lerinde gerçek metin katmanı var (OCR
gerekmeyebilir); bdr-kisayol panosunda dönem seçimi + doğrudan PDF linkleri
var; elimizdeki 51 dönemlik doğrulanmış veri, çıkarımı kanıtlamak için altın
standart olarak kullanılacak.

**Fazlar:** 0) fizibilite kanıtı (karar noktası, %99+ eşleşme eşiği) →
1) PDF→veri motoru (elle yükleme) → 2) otomatik indirme (insan onay kapısıyla).
Paralel: 3) 13 passthrough ölçünün türetilmesi · 4) bilgi baloncukları ·
5) etiket bazlı erişim → 6) kullanıcı formülleri (bayrak arkasında).

**Durum:** 📋 Plan hazır, uygulama başlamadı. Önce FAZ 0 (fizibilite kanıtı)
çalıştırılmalı — olumlu çıkmadan üzerine sistem kurulmamalı.

---


#### PDF fazı — faz detayları

##### FAZ 0 — Fizibilite kanıtı (KARAR NOKTASI)
**Neden ilk:** PDF çıkarımının güvenilirliği kanıtlanmadan üzerine sistem
kurmak, projenin en pahalı hatası olur. Finansal veride "çoğunlukla doğru"
kabul edilemez.

**İşler**
1. 3 banka × 1 dönem seç (Kuveyt Türk + bir büyük mevduat + bir katılım) —
   formatları farklı olduğu için çeşitlilik önemli.
2. PDF'i metin/tablo olarak çıkar (pdfplumber; gerekirse camelot).
3. Çıkan kalemleri **aynı dönemin mevcut Excel verisiyle satır satır
   karşılaştır**.
4. Rapor: kalem eşleşme oranı, birebir tutan değer oranı, tutmayanların
   nedeni (kalem adı farkı / birim / tablo yapısı / okunamayan sayfa).

**Çıktı:** doğruluk raporu + **git/devam kararı**.
**Başarı ölçütü:** ana tablolarda (Bilanço, Gelir Tablosu) **%99+ birebir
eşleşme**. Altındaysa: hangi tabloların güvenilir olduğu belirlenip kapsam
daraltılır ya da yaklaşım değişir.

---

##### FAZ 1 — PDF → veri motoru (elle yükleme ile)
**Bağımlılık:** FAZ 0 olumlu sonuçlanmalı.

**İşler**
1. `pipeline/pdf_ingest.py` — PDF → uzun format DataFrame (mevcut parquet
   şemasıyla **birebir aynı**: Tarih, Banka Adı, Banka Türü, Tablo Türü,
   Tablo Adı, Kalem Adı, Para Birimi, Tutar). Böylece alt katmanların
   (measures, groups, composition) hiçbiri değişmez.
2. **Kalem eşleme sözlüğü** — BDR'deki kalem adı ile mevcut kalem adları
   arasında eşleme; NFC normalizasyonu ve NBSP temizliği zorunlu (bu iki
   tuzağa proje geçmişinde 3 kez düşüldü).
3. **Kalite kapıları** (yazmadan önce):
   - Bilanço denkliği: Toplam Aktifler = Toplam Pasifler
   - Toplam Aktifler bir önceki çeyreğe göre makul aralıkta mı (ör. ±%40)
   - Beklenen tabloların hepsi bulundu mu
   - Herhangi biri başarısızsa dosya **işlenmez** — sessizce yanlış veri
     yazmaktansa "işlenemedi" demek yeğdir.
4. Admin panele **PDF yükleme** (mevcut Excel yüklemenin yanına).
5. **Geriye dönük doğrulama:** son 4 çeyrek PDF'ten yeniden üretilip Excel
   sonucuyla farkları raporlanır.

**Çıktı:** PDF yükleyerek çeyrek güncellemesi yapılabilir hâle gelmek.

---

##### FAZ 2 — Otomatik indirme
**Bağımlılık:** FAZ 1.

**İşler**
1. Link toplayıcı: bdr-kisayol panosundan banka + dönem + PDF linki.
2. İndirme + arşivleme (`data/raw_pdf/<Banka>/<Banka> - GG.AA.YYYY.pdf`).
3. Zamanlanmış kontrol (çeyrek sonrası periyodik tarama).
4. **İnsan onayı kapısı:** indirilen PDF otomatik işlenir ama sonuç
   **doğrudan yayına girmez**; admin panelde "şu bankalar geldi, farklar
   şunlar, onayla" ekranı. Otomasyon veriyi *hazırlar*, yayına alma kararı
   insanda kalır.
5. Eksik/başarısız banka uyarısı (ör. "3 banka henüz yayımlamadı").
6. **Elle yükleme her zaman yedek yol olarak kalır** — dış kaynak kırılırsa
   sistem durmasın.

**Risk:** linkler bankaların kendi sitelerine gidiyor; adres/format
değişiklikleri kaçınılmaz. Bu yüzden indirme katmanı, çıkarım katmanından
**tamamen ayrı** tutulur — biri kırılınca diğeri çalışmaya devam eder.

---

##### FAZ 3 — 13 passthrough ölçünün türetilmesi
**Bağımlılık:** yok (Excel verisiyle de yapılabilir), ama PDF fazıyla
birlikte anlamlı: "dışarıdan hesaplanmış değer almayalım" hedefinin ikinci
yarısı.

**İşler**
1. Her ölçü için ham kalem karşılığını bul. Tespit edilenler: PDF/Excel'de
   `Sermaye Yeterlilik Rasyosu (%)`, `Çekirdek Sermaye Yeterliliği Oranı (%)`,
   `Çekirdek Sermaye Toplamı`, `Net Faiz Geliri/Gideri` **doğrudan mevcut**.
2. Türet, sonra **geçmiş dönemlerde baseline değeriyle karşılaştır** — tutuyorsa
   formül doğrudur.
3. `BASELINE_PASSTHROUGH`'tan çıkar, `MEASURE_FUNCS`'a taşı.
4. Doğrudan okunabilenlerle başla (SYR, Çekirdek SYR), sonra türetilmesi
   gerekenlere geç (NIM, Spread, RORWA).

**Çıktı:** yeni çeyrek yüklendiğinde 160 ölçünün **tamamı** dolu gelir.

---

##### FAZ 4 — Bilgi baloncukları
**Bağımlılık:** yok — diğer fazlardan bağımsız ilerleyebilir.

**İşler**
1. `catalog.seed.json`'a ölçü başına yeni alanlar:
   `tanim` (bu ölçü nedir), `nasil_hesaplanir` (sade formül anlatımı),
   `icgoru` (yüksek/düşük olması ne anlama gelir, nelere dikkat edilmeli).
2. Claude 160 ölçü için taslak üretir → kullanıcı düzeltir/onaylar.
   Metinler dosyada durur, sonradan düzenlenebilir.
3. UI: ölçü seçicide ve panel başlıklarında ⓘ ikonu → baloncuk.
4. Admin panelde metin düzenleme ekranı (kod değiştirmeden güncelleme).

**Not:** İçerik **statik** tutulur (her açılışta LLM çağrısı yok) — maliyet
ve tutarlılık için. İleride dinamik yorum istenirse Chat LLM fazına eklenir.

---

##### FAZ 5 — Etiket bazlı ölçü erişimi
**Bağımlılık:** yok. FAZ 6'nın önkoşulu.

**İşler**
1. `data/tags.json` — etiket tanımları: `{ad, aciklama, olculer: [ölçü id]}`.
2. `users.json`'a `etiketler: []` (bir kullanıcıda birden fazla; görebildiği
   ölçüler etiketlerinin **birleşimi**).
3. Admin panelde etiket yönetimi: oluştur/düzenle/sil + **aranabilir ölçü
   seçici** (160 ölçü içinden tek tek seçim; kategori bazlı toplu seçim
   kısayolları kolaylık için eklenebilir).
4. **Sunucu tarafında filtreleme** — `/api/data` ve `/api/catalog` kullanıcının
   göremeyeceği ölçüleri **hiç göndermez**. Frontend'de gizlemek yeterli
   değildir; veri ağdan geçmemelidir.
5. Etiketsiz kullanıcı için varsayılan davranış belirlenir (bkz. açık soru).

---

##### FAZ 6 — Kullanıcı formülleri (canlıya alınmayacak)
**Bağımlılık:** FAZ 5 (kullanıcının hangi kalemleri kullanabileceği
etiketiyle sınırlanmalı).
**Karar:** bu faz geliştirilecek ama **şimdilik canlıya alınmayacak** —
özellik bayrağı (`KT_FEATURE_USER_FORMULAS`) arkasında kapalı durur.

**İşler**
1. **Güvenli ifade değerlendirici** — kullanıcı metnini `eval` ile çalıştırmak
   kesinlikle yasak. AST tabanlı, yalnız izin verilen düğümler (sayı, dört
   işlem, parantez, kalem referansı) ve sıfıra bölme koruması.
2. Ham kalem seçici: ~1.891 kalem içinden aranabilir liste (kullanıcının
   etiketiyle sınırlı).
3. Kişisel formüller: `data/user_formulas.json` — oluşturan görür.
4. **Log:** kim, ne zaman, hangi formülü oluşturdu/düzenledi/sildi
   (denetim izi — kullanıcı isteği).
5. Önizleme: formül kaydedilmeden önce seçili banka/dönem için sonucu göster.

---

#### PDF fazı — bağımlılık akışı

```
FAZ 0 (kanıt) ──► FAZ 1 (PDF motoru) ──► FAZ 2 (otomatik indirme)
                        │
                        └──► FAZ 3 (13 ölçünün türetilmesi)   [Excel ile de yapılabilir]

FAZ 4 (baloncuklar)     — bağımsız, paralel ilerleyebilir
FAZ 5 (etiketler) ──► FAZ 6 (kullanıcı formülleri, bayrak arkasında)
```

---

#### PDF fazı — riskler

| Risk | Neden ciddi | Azaltım |
|---|---|---|
| **Sessiz yanlış çıkarım** | PDF'ten yanlış hücre okunur, kimse fark etmez, yanlış rakamla karar alınır | Excel ile çapraz doğrulama, bilanço denkliği kontrolü, dönemsel sıçrama kontrolü, mevcut regresyon kilidi |
| **Banka format çeşitliliği** | 27 banka, farklı denetim firmaları, farklı şablonlar | Banka bazlı şablon; başarısızlıkta "işlenemedi" — asla tahmin yürütme |
| **Solo/Konsolide karışması** | Yanlış rapor tipi tüm seriyi bozar, fark gözle görülmez | Rapor tipi dosya adına ve manifest'e yazılır; mevcut veriyle karşılaştırılarak doğrulanır (bkz. açık soru) |
| **Otomatik indirme kırılganlığı** | Dış site/link değişir, çeyrek kaçar | İndirme ve çıkarım ayrı katman; elle yükleme her zaman açık; eksik banka uyarısı |
| **Yayın takvimi dağınıklığı** | Bankalar aynı anda yayımlamaz | Kısmi çeyrek mantığı zaten var (grup toplamları eksik üyede "—" döner) |
| **Etiket filtresinin atlanması** | Yetkisiz kişi gizli ölçüyü görür | Filtreleme **sunucuda**; frontend'e hiç gönderilmez; testle doğrulanır |
| **Kullanıcı formülünde kod çalıştırma** | `eval` ile sunucuda kod çalıştırma açığı | AST whitelist, `eval` yok, bayrak arkasında kapalı başlangıç |

---

#### PDF fazı — açık sorular

1. **Solo mu, konsolide mi?** bdr-kisayol her banka için iki rapor sunuyor.
   Mevcut BDDK verisi hangisine karşılık geliyor? Yanlış seçim tüm seriyi
   sessizce kaydırır — FAZ 0'da mevcut veriyle karşılaştırılarak
   kanıtlanmalı.
2. **Kapsam genişleyecek mi?** Panoda kalkınma/yatırım bankaları da var;
   sistem şu an 27 banka izliyor. Yeni bankalar eklenecek mi?
3. **Etiketsiz kullanıcı ne görür?** Hiçbir şey mi (güvenli varsayılan),
   yoksa temel bir set mi?
4. **Kullanıcı formülleri ne zaman canlıya alınacak?** Bayrak hangi koşulda
   açılacak?
5. **Excel yolu tamamen kapanacak mı?** Karar "2026Q3'ten itibaren PDF" —
   Excel yükleme ekranı acil durum yedeği olarak kalsın mı?


### 🔵 v2'ye ertelenmiş konular (daha önce karara bağlanmış, unutulmasın)

#### 6. Konfigüre edilebilir odak banka
**Ne:** Kuveyt Türk yerine başka bir bankayı "odak" yapabilme.
**Neden ertelendi:** Grup katmanının kırılgan geçmişi (bkz. Dönem 2'deki
grup agregasyon bug'ları) nedeniyle riskli bulundu.
**Uygulama haritası hazır** (Claude'un hafıza notunda) — v2'de sıfırdan
araştırma gerekmeyecek: `KT_NAME` sabiti `DATA.meta.odak_banka`'ya
bağlanacak, `PROTECTED_GROUPS` ve varsayılan grup üyeliği odağa göre
güncellenecek.
**Durum:** ⏸️ v2'ye ertelendi.

#### 7. Screenshot / PDF-öncesi PNG indirme
**Ne:** Bulunduğun görünümü PNG olarak indirme butonu.
**Neden ertelendi:** Kullanıcı v2'de yapmaya karar verdi.
**Durum:** ⏸️ Kod `feature/v2-screenshot` branch'inde hazır (2 commit),
Firefox'ta `toBlob` SecurityError sorunu vardı, son fix canlı doğrulanmadı —
v2'de ya bu fix'i test et ya da native `getDisplayMedia`'ya geç.

---

### ⚙️ Süreç

- **Backlog dokümanı:** ✅ Bu dosya (son güncelleme 2026-09-08).
- **Otomatik güncelleme talimatı (2026-08-25):** Bundan sonra yapılan her
  büyük işlemde bu dosya VE görsel HTML artifact'ı sorulmadan güncellenecek.
- **Zaman planı:** 📋 Sprint 1 tamamlanınca tarih hedefleri eklenecek.
- **Sprint oluşturma:** ✅ Sprint 1 yukarıda tanımlı. Rasyonet otomasyonu
  boyutu nedeniyle sprint'e alınmadı, önce spike gerekiyor.

---

## 9. Kararlar günlüğü — neden böyle yapıldı

Bir şeyi değiştirmeden önce buraya bakın; çoğu "tuhaf" görünen tercih, bedeli
ödenmiş bir dersin sonucudur.

| Karar | Gerekçe |
|---|---|
| **`data/` git'te değil** | Git-push-to-deploy kurulumunda sunucudaki `git pull`, tracked bir veri dosyasını eski kopyayla ezip canlı veriyi geri alabilirdi. Bedeli: kod ve veri ayrı taşınır (§4.3). |
| **Ham xlsx arşivi kalıcı, dokunulmaz** | Her şey yeniden hesaplanabilir olmalı. Yeni ölçü eklemek ham veriye dokunmaz. |
| **Frontend hesaplama yapmaz** | Formül değişikliği tek yerde (pipeline) olur, frontend'e dokunulmaz; tutarsızlık riski kalkar. |
| **Grup, eksik üyede `None` döner** | Yanıltıcı küçük toplam üretmektense "veri yok" demek. 2026-08-11'de tam tersi davranış yanlış grup toplamları üretiyordu. |
| **Grup rasyoları ağırlıklı ortalama** | Basit ortalama, büyük bankayı küçükle eşitleyip sektör gerçeğini bozar. |
| **Tek worker** | Kilitler ve rate-limit in-process; çoklu worker bunları sessizce devre dışı bırakırdı. |
| **`catalog.seed.json` + runtime `catalog.json`** | Config (ölçüler) kodla, gruplar (admin panelden düzenlenen) veriyle gelmeli. Seed mimarisi ikisini ayırıp kod↔config uyumsuzluğunu bitirdi. |
| **Regresyon kilidi (2026-09-08)** | "Sonuç boş mu" kontrolü yetmiyordu: 51 dönem → 1 döneme düşen kaza bu kontrolü geçmişti. Artık küçülme reddediliyor, bilinçliyse elle zorlanıyor. |
| **Sunucu taşıma paketi manifest'li** | "Hangi zip güncel" sorusu insan hafızasına kalınca, bir sunucuda Eylül 2025'te donmuş veri yayına çıktı. Manifest bunu görünür kılıyor. |
| **Otomasyon veriyi hazırlar, yayına insan alır** | PDF fazında da aynı ilke: indirme otomatik, yayın kararı admin onayında (§8, FAZ 2). |
| **13 ölçü hâlâ passthrough** | Ham veriden türetilmeleri doğrulama gerektiriyor; yanlış formülle "dolu ama hatalı" veri üretmektense bilinen bir boşluk bırakıldı. |

---

## 10. Referans dokümanlar

| Dosya | Ne zaman bakılır |
|---|---|
| `docs/MEASURES.md` | Bir ölçünün formülünü/tanımını ararken (445 satır, DAX eşdeğerleriyle) |
| `docs/MEASURE_LISTESI.md` | 160 ölçünün hızlı listesi |
| `docs/EXTENDING.md` | Yeni ölçü, banka, grup veya kompozisyon eklerken — adım adım |
| `docs/ARCHITECTURE.md` | Storage şeması ve pipeline modüllerinin detayı |
| `docs/DATA_MIGRATION.md` | Sunucu göçü / veri paketi üretimi |
| `docs/CHANGELOG.md` | Sürüm geçmişi (v17 → v29 dönemi) |
| `docs/backlog-visual.html` | Bu dosyanın görsel özeti (yayınlanmış sayfa) |
| `docs/pdf-fazi-gorsel.html` | PDF fazının görsel yol haritası |

**Kod içindeki yorumlar birincil kaynaktır.** `app.py` ve `pipeline/*.py`
içinde her kritik kararın yanında tarihli açıklama vardır (ör. "2026-08-11
düzeltmesi: …"). Bir satırın neden öyle yazıldığını merak ettiğinizde önce
oradaki yoruma bakın.
