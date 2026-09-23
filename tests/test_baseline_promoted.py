"""
Ham veriden hesaplanan rasyoların GERÇEK PBI çıktısıyla uyumu (regresyon).

Referans: `data/computed_datatable_kaynakli_yedek.json` — PBI raporunun
kendi datatable export'undan (datatable_1.xlsx) üretilmiş değerler, 2015-03
→ 2026-03. 2026-09-23'e kadar bu test referans olarak canlı
`data/computed.json`'u, yani PIPELINE'IN KENDİ ÇIKTISINI kullanıyordu —
döngüseldi: yanlış bir formül, kendi eski yanlış değerleriyle "uyumlu"
görünüyordu (ör. Maliyetli Pasif Maliyeti KT'de %10,8 hesaplanıyordu, PBI
%19,8). Şimdi bağımsız PBI değerlerine karşı ölçülüyor.

Yalnız 2019 ve sonrası: 2013-2018 arası bazı BDDK şablon kalemleri farklı
adlandırıldığı için eski dönemlerde yapısal sapma var (bkz. docs/
PROJE_EL_KITABI.md Dönem 33). Eşikler 2026-09-23 ölçümünün biraz altında.

Gerçek `data/veriler.parquet` + PBI referans JSON'una bağımlı (bu makineye
özel, .gitignore'da) — yoksa test SESSİZCE ATLANIR.
"""
from pathlib import Path
import json
import statistics

import pytest

from pipeline.lookup import LookupContext
from pipeline import measures as m

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
VERILER_PATH = DATA_DIR / 'veriler.parquet'
PBI_PATH = DATA_DIR / 'computed_datatable_kaynakli_yedek.json'
CATALOG_PATH = DATA_DIR / 'catalog.json'
SINCE = '2019-03-31'

pytestmark = pytest.mark.skipif(
    not VERILER_PATH.exists() or not PBI_PATH.exists(),
    reason='data/veriler.parquet veya PBI referans JSON bu makinede yok',
)


@pytest.fixture(scope='module')
def ctx():
    import pandas as pd
    df = pd.read_parquet(VERILER_PATH)
    catalog = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
    bank_turu_map = {b['banka_adi']: b['tur'] for b in catalog['banks']}
    return LookupContext(df, bank_turu_map)


@pytest.fixture(scope='module')
def pbi():
    return json.loads(PBI_PATH.read_text(encoding='utf-8'))['bank_data']


def _diffs(ctx, pbi, measure_id, fn):
    diffs = []
    for bank, dates in pbi.get(measure_id, {}).items():
        for date, pbi_v in dates.items():
            if pbi_v is None or date < SINCE:
                continue
            try:
                my_v = fn(ctx, bank, date)
            except Exception:
                my_v = None
            if my_v is None:
                continue
            diffs.append(abs(my_v - pbi_v))
    return diffs


# (measure_id, fonksiyon, min_kabul_orani (<=0.5pp), min_nokta_sayisi)
# Yorumdaki yüzde: 2026-09-23 ölçümü (2019+).
PBI_UYUMLU = [
    ('syr', m.m_syr, 0.95, 500),                                          # 98.3
    ('cekirdek_syr', m.m_cekirdek_syr, 0.95, 500),                        # 99.0
    ('rorwa', m.m_rorwa, 0.93, 500),                                      # 96.0
    ('net_faiz_ort_rav', m.m_net_faiz_ort_rav, 0.90, 500),                # 94.4
    ('faiz_getirili_aktif_getirisi', m.m_faiz_getirili_aktif_getirisi, 0.90, 500),  # 94.2
    ('faiz_getirili_ozkaynak', m.m_faiz_getirili_ozkaynak, 0.95, 500),    # 97.7
    ('gayrinakdi_komisyon_gayrinakdi', m.m_gayrinakdi_komisyon_gayrinakdi, 0.95, 500),  # 99.9
    ('maliyet_gelir', m.m_maliyet_gelir, 0.90, 500),                      # 94.9
    ('maliyet_gelir_duzeltilmis', m.m_maliyet_gelir_duzeltilmis, 0.90, 500),  # 94.2
    ('nim', m.m_nim, 0.93, 500),                                          # 96.2
    ('nim_duzeltilmis', m.m_nim_duzeltilmis, 0.92, 500),                  # 95.3
    ('nim_bzk_sonrasi', m.m_nim_bzk_sonrasi, 0.90, 500),                  # 92.8
    ('spread', m.m_spread, 0.90, 500),                                    # 94.5
    ('kredi_mevduat_spread', m.m_kredi_mevduat_spread, 0.93, 500),        # 97.0
    ('cost_of_risk', m.m_cost_of_risk, 0.93, 500),                        # 97.0
    ('npl_formasyonu', m.m_npl_formasyonu, 0.95, 500),                    # 98.4
    ('grup_2_tuzel_tuzel', m.m_grup_2_tuzel_tuzel, 0.90, 500),            # 94.7
    ('tuzel_krediler_tuzel_mevduat', m.m_tuzel_krediler_tuzel_mevduat, 0.92, 500),  # 95.6
    ('tp_pasifler_toplam_pasifler_ozkaynak_haric', m.m_tp_pasifler_toplam_pasifler_ozkaynak_haric, 0.97, 500),  # 99.7
    ('tp_alinan_toplam_alinan', m.m_tp_alinan_toplam_alinan, 0.97, 500),  # 99.9
    ('faiz_gideri_faiz_geliri', m.m_faiz_gideri_faiz_geliri, 0.93, 500),  # 96.9
    ('komisyon_gid_gel', m.m_komisyon_gid_gel, 0.93, 500),                # 97.7
    ('reklam_net_kar', m.m_reklam_net_kar, 0.93, 500),                    # 97.6
    ('faaliyet_gid_ort_aktif', m.m_faaliyet_gid_ort_aktif, 0.85, 500),    # 89.5
    ('net_ucret_operasyonel', m.m_net_ucret_operasyonel, 0.92, 500),      # 96.3
    ('faiz_maliyetli_pasif_maliyeti', m.m_faiz_maliyetli_pasif_maliyeti, 0.95, 500),  # 97.5
    # PBI datatable'ında yalnız 2026-03-31 var.
    ('personel_net_kar', m.m_personel_net_kar, 0.95, 20),                 # 100
]


@pytest.mark.parametrize('measure_id,fn,min_oran,min_n', PBI_UYUMLU)
def test_pbi_ile_uyum(ctx, pbi, measure_id, fn, min_oran, min_n):
    diffs = _diffs(ctx, pbi, measure_id, fn)
    assert len(diffs) >= min_n, f'{measure_id}: yeterli karşılaştırma noktası yok ({len(diffs)})'
    oran = sum(1 for d in diffs if d < 0.5) / len(diffs)
    medyan = statistics.median(diffs)
    assert oran >= min_oran, f'{measure_id}: ±0.5pp uyum oranı {oran:.1%} < {min_oran:.0%}'
    assert medyan < 0.5, f'{measure_id}: medyan fark {medyan:.4f} beklenenden büyük'
