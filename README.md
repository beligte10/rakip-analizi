# KT Strategic Cockpit

Kuveyt Türk Strateji ekibi için Türkiye bankacılık sektörü rekabet analizi dashboard'u. 27 banka × 48 çeyrek (2013-Q4 → 2025-Q3) × 128 measure, BDDK kamuya açık çeyreklik raporlarından üretilir.

Tamamen yerel çalışır — harici bir hosting servisine bağımlılığı yoktur.

**Modlar:** Snapshot (anlık karşılaştırma), Trend (zaman serisi), Composition (kategori dağılımı), Export (Excel/CSV indir).

## Mimari

- **Backend:** FastAPI (Python) + Pandas pipeline
- **Frontend:** Tek dosya React (CDN) + custom CSS
- **Veri:** BDDK xlsx → Parquet → JSON pipeline (hepsi `data/` klasöründe, repo'nun içinde)
- **Auth:** HTTP Basic Auth (admin panel için)
- **Roller:** üyelik oturumu + rol bazlı izinler (`roles.py`, `data/roles.json`); roller ve izinler admin panelindeki 🔐 Roller sekmesinden yönetilir. Basic Auth hesabı her izne sahiptir.

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
- `OPENROUTER_API_KEY` (ya da `QWEN_API_KEY` / `DASHSCOPE_API_KEY`) — Asistan (Qwen chatbot) için API anahtarı. Tanımlı değilse asistan kapalıdır. `sk-or-` ile başlayan anahtarlar otomatik OpenRouter'a yönlenir.
- `EVDS_API_KEY` — TCMB EVDS anahtarı (evds3.tcmb.gov.tr → Profil → API Anahtarı). Tanımlıysa asistan faiz, kur, enflasyon, sektör kredi/mevduat gibi makro verileri EVDS'den çekebilir (`evds_ara`, `evds_seriler`, `evds_veri`). Sunucunun `evds3.tcmb.gov.tr`'ye çıkışı olmalı.
- `TUIK_API_KEY` + `TUIK_ETKIN=1` — TÜİK SDMX araçları (beklemede: servis isteklerin bir kısmına yanıt vermiyor; kod `assistant/external/tuik.py`'de hazır, ikisi birlikte tanımlanmadıkça kapalı).
- `QWEN_MODEL` — model adı (default: OpenRouter'da `qwen/qwen3.5-plus-20260420`, Model Studio'da `qwen3.5-plus`)
- `QWEN_API_BASE` — OpenAI uyumlu uç (default: anahtara göre `https://openrouter.ai/api/v1` ya da `https://maas.qwencloudapi.com/compatible-mode/v1`)
- `QWEN_ENABLE_THINKING` — `1` ise modelin düşünme modu açılır (daha yavaş; default kapalı)
- `CHAT_PER_MIN` / `CHAT_PER_DAY` — kullanıcı başına asistan istek sınırı (default: 8 / 300)

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
