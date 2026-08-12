# Frontend

Bu klasör tek-dosya HTML/React dashboard'unu içerir.

## Dosyalar

- `index_v29_baseline.html` — v29 sürümü (embedded JSON dahil). Faz 1 baseline'ı.
- `index.html` (Faz 2'de eklenecek) — embedded JSON sökülmüş, `fetch('/data.json')` kullanan production sürümü.

## Geliştirme

Lokal'de hızlı iterasyon için: `index_v29_baseline.html`'i tarayıcıda aç.
Production: `index.html` FastAPI tarafından `GET /` endpoint'inde serve edilir.
