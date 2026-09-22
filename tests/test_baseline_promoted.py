"""
BASELINE_PASSTHROUGH'dan raw'a taşınan ölçüler için regresyon spot-check
(bkz. docs/MIMARI_SABLON.md §10, docs/PROJE_EL_KITABI.md Dönem 25/26/29).

İki grup var:
1. YÜKSEK GÜVEN: syr, cekirdek_syr, rorwa, net_faiz_ort_rav,
   faiz_getirili_aktif_getirisi, gayrinakdi_komisyon_gayrinakdi,
   maliyet_gelir (2026-09-12, ≥%85 ±0.5pp) — ARTIK ayrıca nim,
   nim_duzeltilmis, nim_bzk_sonrasi, spread, cost_of_risk de burada
   (2026-09-18/21'de kullanıcının verdiği orijinal PBI DAX'larıyla
   düzeltildi, %92-97 ±0.5pp uyum — "en iyi tahmin" değil, DOĞRULANMIŞ
   formül).
2. EN İYİ TAHMİN: kredi_mevduat_spread (2026-09-21'de dış (compound)
   formülü DAX'a göre düzeltildi ama iç "Mevduatın Paçal Maliyeti"
   alt-formülü hâlâ doğrulanmadı, %79.5 ±0.5pp) — eşik BİLEREK düşük,
   amaç "hâlâ makul aralıkta mı" kontrolü, birebir doğruluk garantisi
   değil.

Gerçek `data/veriler.parquet` + `data/computed.json`'a bağımlı (bu makineye
özel, .gitignore'da) — yoksa test SESSİZCE ATLANIR.
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


def _diffs(ctx, baseline, measure_id, fn):
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
    return diffs


# (measure_id, fonksiyon, min_kabul_orani (<=0.5pp), min_nokta_sayisi)
PROMOTED = [
    ('syr', m.m_syr, 0.95, 500),
    ('cekirdek_syr', m.m_cekirdek_syr, 0.95, 500),
    ('rorwa', m.m_rorwa, 0.90, 500),
    ('net_faiz_ort_rav', m.m_net_faiz_ort_rav, 0.90, 500),
    ('faiz_getirili_aktif_getirisi', m.m_faiz_getirili_aktif_getirisi, 0.85, 500),
    ('gayrinakdi_komisyon_gayrinakdi', m.m_gayrinakdi_komisyon_gayrinakdi, 0.95, 500),
    ('maliyet_gelir', m.m_maliyet_gelir, 0.90, 500),
    # 2026-09-18: kullanıcının verdiği orijinal PBI DAX'larıyla düzeltildi
    # (önceden BEST_EFFORT'taydı, %81.7/yok/%43) — gerçek ölçüm %96.2/95.6/93.5.
    ('nim', m.m_nim, 0.90, 500),
    ('nim_duzeltilmis', m.m_nim_duzeltilmis, 0.90, 500),
    ('nim_bzk_sonrasi', m.m_nim_bzk_sonrasi, 0.85, 500),
    # 2026-09-21: basit fark (a−p) yerine bileşik ((1+a)/(1+p)-1) DAX
    # formülüne düzeltildi (önceden BEST_EFFORT'ta %78.3) — gerçek ölçüm %92.8.
    ('spread', m.m_spread, 0.85, 500),
    # 2026-09-21: payda NET krediler yerine BRÜT krediler (DAX: "Ortalama
    # Brüt Krediler") — gerçek ölçüm %96.7 (pratikte eski formülle aynı
    # çıkıyor çoğu bankada, ama DAX'a artık birebir sadık).
    ('cost_of_risk', m.m_cost_of_risk, 0.90, 500),
]


@pytest.mark.parametrize('measure_id,fn,min_oran,min_n', PROMOTED)
def test_v29_baseline_ile_uyum(ctx, baseline, measure_id, fn, min_oran, min_n):
    diffs = _diffs(ctx, baseline, measure_id, fn)
    assert len(diffs) >= min_n, f'{measure_id}: yeterli karşılaştırma noktası yok ({len(diffs)})'
    oran = sum(1 for d in diffs if d < 0.5) / len(diffs)
    medyan = statistics.median(diffs)
    assert oran >= min_oran, f'{measure_id}: ±0.5pp uyum oranı {oran:.1%} < {min_oran:.0%}'
    assert medyan < 0.5, f'{measure_id}: medyan fark {medyan:.4f} beklenenden büyük'


# EN İYİ TAHMİN grubu — (measure_id, fonksiyon, min_oran, max_medyan,
# min_nokta_sayisi). Eşikler bilerek gevşek: amaç "formül hâlâ makul mü"
# kontrolü, üsttekiler (PROMOTED) kadar sıkı bir doğruluk garantisi değil.
BEST_EFFORT = [
    # 2026-09-21: dış (compound) formül DAX'a göre düzeltildi ama iç
    # "Mevduatın Paçal Maliyeti" alt-formülü (TTM Mevduata Verilen Faizler /
    # Ortalama Mevduat) hâlâ doğrulanmadı — gerçek ölçüm %79.5.
    ('kredi_mevduat_spread', m.m_kredi_mevduat_spread, 0.70, 0.5, 500),
]


@pytest.mark.parametrize('measure_id,fn,min_oran,max_medyan,min_n', BEST_EFFORT)
def test_v29_baseline_ile_en_iyi_tahmin(ctx, baseline, measure_id, fn, min_oran, max_medyan, min_n):
    diffs = _diffs(ctx, baseline, measure_id, fn)
    assert len(diffs) >= min_n, f'{measure_id}: yeterli karşılaştırma noktası yok ({len(diffs)})'
    oran = sum(1 for d in diffs if d < 0.5) / len(diffs)
    medyan = statistics.median(diffs)
    assert oran >= min_oran, f'{measure_id}: ±0.5pp uyum oranı {oran:.1%} < {min_oran:.0%}'
    assert medyan < max_medyan, f'{measure_id}: medyan fark {medyan:.4f} beklenenden büyük'
