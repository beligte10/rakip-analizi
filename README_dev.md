# KT Strategic Cockpit

Türk bankacılık sektörü rakip analiz dashboard'u. BDDK kamuya açık kuartelik raporlamasından beslenir, 27 banka × 48 dönem × 126 measure üzerinden interaktif kıyaslama, trend ve kompozisyon analizleri sunar.

## Hızlı bakış

- **Veri kaynağı:** BDDK kuartelik xlsx raporları (banka × dönem)
- **Kapsam:** 27 banka, 2013-Q4 → günümüz, 126 measure
- **Mod:** Snapshot (tek dönem kıyaslama), Trend (zaman serisi), Kompozisyon (Aktif/Kredi/Pasif/Kaynak/Gelir kırılımları), Export (tablo + Excel/CSV)
- **Stack:** FastAPI (backend) + React/HTML (frontend, single-file) + pandas (pipeline) + parquet (storage)

## Mimari

```
┌──────────────────────────────────────────────────────────────┐
│  FRONTEND (frontend/index.html)                              │
│  React, single-file, fetch('/data.json') → render            │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│  BACKEND (app.py — FastAPI)                                  │
│  • GET  /             → frontend HTML                        │
│  • GET  /data.json    → computed data                        │
│  • POST /admin/upload → xlsx ingest                          │
│  • POST /admin/recompute → trigger pipeline                  │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│  PIPELINE (pipeline/)                                        │
│  ingest.py  → xlsx → veriler.parquet                         │
│  measures.py → veriler.parquet → computed.json               │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│  STORAGE                                                     │
│  data/raw/<banka>/*.xlsx        (yüklenen ham, kalıcı)       │
│  data/veriler.parquet           (long-format konsolide)      │
│  data/computed.json             (dashboard payload)          │
│  data/catalog.json              (measure & banka metadata)   │
└──────────────────────────────────────────────────────────────┘
```

## Hızlı Başlangıç

### Yerel çalıştırma

```bash
git clone <repo-url>
cd kt_cockpit_repo
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_data.py    # ilk kez veri yükleme (BDDK xlsx ZIP gerekir)
python app.py                  # http://localhost:7860
```

### Yeni dönem verisi yükleme

1. Dashboard'da Admin tabına git
2. Yeni xlsx'leri sürükle-bırak (`<Banka> - DD.MM.YYYY.xlsx` formatında)
3. Pipeline otomatik tetiklenir (10-30 sn)
4. Sayfayı yenile, yeni dönem dashboard'da görünür

## Repo Yapısı

```
kt_cockpit_repo/
├── README.md                    # bu dosya
├── requirements.txt
├── app.py                       # FastAPI app (Faz 2'de eklenir)
├── catalog.json                 # measure & banka metadata (tek doğru kaynak)
├── pipeline/
│   ├── __init__.py
│   ├── ingest.py                # xlsx → parquet
│   ├── measures.py              # tüm measure formülleri
│   ├── lookup.py                # raw veri okuma yardımcıları
│   └── groups.py                # grup hesaplaması
├── frontend/
│   └── index.html               # tek dosya React/HTML dashboard
├── docs/
│   ├── ARCHITECTURE.md          # detaylı mimari
│   ├── MEASURES.md              # 126 measure'ın formülleri
│   └── CHANGELOG.md             # iterasyon geçmişi
├── data/
│   ├── raw/                     # banka klasörlerinde xlsx'ler
│   │   ├── Akbank/
│   │   ├── Garanti Bankası/
│   │   └── ...
│   ├── veriler.parquet          # konsolide ham
│   └── computed.json            # dashboard payload
└── scripts/
    ├── init_data.py             # baştan veri kurulumu
    └── recompute.py             # CLI'dan tüm pipeline'ı çalıştır
```

## Bakım

Yeni measure, banka veya grup eklemek için: [`docs/EXTENDING.md`](docs/EXTENDING.md)

## Lisans

Veri: BDDK kamuya açık (Bankacılık Düzenleme ve Denetleme Kurumu).
Kod: özel (proje sahibi belirlemeli).
