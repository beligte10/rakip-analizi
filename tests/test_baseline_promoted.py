"""
2026-09-12'de BASELINE_PASSTHROUGH'dan raw'a taşınan 7 ölçü için regresyon
spot-check (bkz. docs/MIMARI_SABLON.md §10, docs/PROJE_EL_KITABI.md Dönem 25):
syr, cekirdek_syr, rorwa, net_faiz_ort_rav, faiz_getirili_aktif_getirisi,
gayrinakdi_komisyon_gayrinakdi, maliyet_gelir.

Gerçek `data/veriler.parquet` + `data/computed.json`'a bağımlı (bu makineye
özel, .gitignore'da) — yoksa test SESSİZCE ATLANIR.

Doğrulama metodolojisi: her ölçü, v29 baseline'ın (computed.json'daki DONMUŞ
passthrough değerleri) TÜM tarihsel (banka, tarih) noktalarıyla karşılaştırıldı;
kabul eşiği ±0.5 yüzde puanı, medyan fark hedefi 0. Tam istatistikler için
pipeline/measures.py'deki ilgili fonksiyonların docstring'lerine bakın.
"""
from pathlib import Path
import json
import statistics

import pytest

from pipeline.lookup import LookupContext
from pipeline import measures as m

VERILER_PATH = Path(__file__).resolve().parent.parent / 'data' / 'veriler.parquet'
COMPUTED_PATH = Path(__file__).resolve().parent.parent / 'data' / 'computed.json'
CATALOG_PATH = Path(__file__).resolve().parent.parent / 'data' / 'catalog.json'

pytestmark = pytest.mark.skipif(
    not VERILER_PATH.exists() or not COMPUTED_PATH.exists(),
    reason='data/veriler.parquet veya data/computed.json bu makinede yok',
)


@pytest.fixture(scope='module')
def ctx():
    import pandas as pd
    df = pd.read_parquet(VERILER_PATH)
    catalog = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
    bank_turu_map = {b['banka_adi']: b['tur'] for b in catalog['banks']}
    return LookupContext(df, bank_turu_map)


@pytest.fixture(scope='module')
def baseline():
    return json.loads(COMPUTED_PATH.read_text(encoding='utf-8'))['bank_data']


# (measure_id, fonksiyon, min_kabul_orani (<=0.5pp), min_nokta_sayisi)
PROMOTED = [
    ('syr', m.m_syr, 0.95, 500),
    ('cekirdek_syr', m.m_cekirdek_syr, 0.95, 500),
    ('rorwa', m.m_rorwa, 0.90, 500),
    ('net_faiz_ort_rav', m.m_net_faiz_ort_rav, 0.90, 500),
    ('faiz_getirili_aktif_getirisi', m.m_faiz_getirili_aktif_getirisi, 0.85, 500),
    ('gayrinakdi_komisyon_gayrinakdi', m.m_gayrinakdi_komisyon_gayrinakdi, 0.95, 500),
    ('maliyet_gelir', m.m_maliyet_gelir, 0.90, 500),
]


@pytest.mark.parametrize('measure_id,fn,min_oran,min_n', PROMOTED)
def test_v29_baseline_ile_uyum(ctx, baseline, measure_id, fn, min_oran, min_n):
    prod = baseline.get(measure_id, {})
    diffs = []
    for bank, dates in prod.items():
        for date, prod_v in dates.items():
            if prod_v is None:
                continue
            try:
                my_v = fn(ctx, bank, date)
            except Exception:
                my_v = None
            if my_v is None:
                continue
            diffs.append(abs(my_v - prod_v))

    assert len(diffs) >= min_n, f'{measure_id}: yeterli karşılaştırma noktası yok ({len(diffs)})'
    oran = sum(1 for d in diffs if d < 0.5) / len(diffs)
    medyan = statistics.median(diffs)
    assert oran >= min_oran, f'{measure_id}: ±0.5pp uyum oranı {oran:.1%} < {min_oran:.0%}'
    assert medyan < 0.5, f'{measure_id}: medyan fark {medyan:.4f} beklenenden büyük'
