# Pipeline

`xlsx → parquet → computed.json` veri akışının modülleri.

## Dosyalar

- `lookup.py` — Long-format raw veriden okuma yardımcıları (`LookupContext` sınıfı)
- `measures.py` — Measure formülleri (her biri bir Python fonksiyonu, docstring'inde DAX-eşdeğer)
- `groups.py` — Grup aggregation kuralları (büyüklük SUM, rasyo ağırlıklı ortalama)
- `ingest.py` — xlsx dosyalarını parquet'e dönüştürme
- `compute.py` — Tüm pipeline'ı orkestre eden ana fonksiyon

## Test

```python
from pipeline.lookup import LookupContext
from pipeline.measures import compute_measure

ctx = LookupContext.from_parquet('data/veriler.parquet')
v = compute_measure('toplam_aktifler', ctx, 'Kuveyt Türk', '2025-09-30')
assert abs(v - 1_217_286_799_000) < 1
```

## Yeni Measure Ekleme

Bkz. [`docs/EXTENDING.md`](../docs/EXTENDING.md).
