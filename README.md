# KT Strategic Cockpit

Kuveyt Türk Strateji ekibi için Türkiye bankacılık sektörü rekabet analizi dashboard'u. 27 banka × 48 çeyrek (2013-Q4 → 2025-Q3) × 128 measure, BDDK kamuya açık çeyreklik raporlarından üretilir.

Tamamen yerel çalışır — harici bir hosting servisine bağımlılığı yoktur.

**Modlar:** Snapshot (anlık karşılaştırma), Trend (zaman serisi), Composition (kategori dağılımı), Export (Excel/CSV indir).

## Mimari

- **Backend:** FastAPI (Python) + Pandas pipeline
- **Frontend:** Tek dosya React (CDN) + custom CSS
- **Veri:** BDDK xlsx → Parquet → JSON pipeline (hepsi `data/` klasöründe, repo'nun içinde)
- **Auth:** HTTP Basic Auth (admin panel için)

## Yerel Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Tarayıcıda açın:

- Dashboard: `http://localhost:7860`
- Admin panel: `http://localhost:7860/admin`

## Ortam Değişkenleri (opsiyonel)

- `KT_USERNAME` — admin panel kullanıcı adı (default: `faruk`)
- `KT_PASSWORD` — admin panel şifresi (default: `faruk123` — paylaşmadan önce DEĞİŞTİRİN)
- `DATA_DIR` — veri klasörünün yolu (default: proje içindeki `./data`)
- `PORT` — sunucu portu (default: `7860`)

## Docker ile çalıştırma (opsiyonel)

```bash
docker build -t kt-cockpit .
docker run -p 7860:7860 -e KT_PASSWORD=degistirin kt-cockpit
```

## Geliştirici Dökümanları

Tam mimari, measure formülleri, pipeline iç işleyişi için `docs/` klasörüne bakın:

- `docs/ARCHITECTURE.md` — Sistem mimarisi
- `docs/MEASURES.md` — 128 measure formülleri
- `docs/EXTENDING.md` — Yeni measure ekleme
- `docs/CHANGELOG.md` — Sürüm geçmişi
- `README_dev.md` — Geliştirici notları
