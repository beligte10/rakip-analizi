# Scripts

CLI araçları.

- `init_data.py` — İlk kurulum: ZIP veya raw klasörden parquet+computed.json üret
- `recompute.py` — Mevcut raw'dan computed.json'u yeniden hesapla (yeni measure/banka eklendiğinde)
- `export_data_snapshot.py` — Sunucu göçü için `data/`'nın güncel, doğrulanabilir bir paketini üretir (bkz. `docs/DATA_MIGRATION.md`)
- `i18n_gom.py` — İngilizce sözlükleri sayfalara gömer: pano için `frontend/i18n/arayuz_en.json` + `olcu_en.json`; giriş/başvuru/admin için `giris_en.json`, `admin_en.json`, `sunucu_en.json` ve `sayfa_cevir.js` motoru. Sözlük ya da motor değiştikten sonra çalıştırın (`--kontrol` güncel değilse 1 döner)

## Kullanım

```bash
# İlk kurulum
python scripts/init_data.py --raw-zip Veriler.zip

# Sonradan yeniden hesaplama (bug fix, yeni measure vb.)
python scripts/recompute.py

# Sunucu göçü için veri paketi üretme
python scripts/export_data_snapshot.py

# İngilizce sözlükleri panoya gömme
python scripts/i18n_gom.py
```

## Rekabet Analizi ölçüleri (2026-10-06)

- `rekabet_katalog_yaz.py` — `pipeline/rekabet_olculer.KATALOG` kayıtlarını `catalog.seed.json`'a ekler/günceller (idempotent).
- `manuel_olcu_yukle.py` — BDR'den okunan, BDDK verisinde olmayan değerleri (Basel III kaldıraç, LCR, serbest karşılık, TÜFEX tamponu, altın vadesiz) Excel/CSV'den `DATA_DIR/manuel_olculer.json`'a yükler; sonra `recompute.py` çalıştırılır.

