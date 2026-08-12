# Scripts

CLI araçları.

- `init_data.py` — İlk kurulum: ZIP veya raw klasörden parquet+computed.json üret
- `recompute.py` — Mevcut raw'dan computed.json'u yeniden hesapla (yeni measure/banka eklendiğinde)

## Kullanım

```bash
# İlk kurulum
python scripts/init_data.py --raw-zip Veriler.zip

# Sonradan yeniden hesaplama (bug fix, yeni measure vb.)
python scripts/recompute.py
```
