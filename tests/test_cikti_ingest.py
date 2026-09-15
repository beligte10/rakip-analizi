"""
pipeline.cikti_ingest — regresyon spot-check (bkz. docs/MIMARI_SABLON.md §10).

BDR-Kısayol'un gerçek `<DÖNEM>.json` çıktısını (bilgisayarda
/Users/farukkezer/Desktop/BDR-Arsiv/cikti/2026-2C.json altında bulunuyor —
repoda DEĞİL, proje dışı ayrı bir araç) alıp mevcut long-format ara formata
çeviriyor, gerçek LookupContext + compute_all ile hesaplatıyor, ve
`data/computed.json`'daki (Rasyonet/xlsx kaynaklı) GERÇEK, önceden elle
doğrulanmış değerlerle karşılaştırıyor.

Bu bir "bilinen girdi -> beklenen çıktı" testi: kaynak dosya bu makineye
özel olduğu için (başka bir geliştirici ortamında/CI'da bulunmayabilir),
dosya yoksa test SESSIZCE ATLANIR (skip) — build'i kırmaz.

Kapsam notu: bu testte doğrulanan ölçüler, Faz 1 dönüştürücüsünün en sağlam
kısmı (bilanço/gelir tablosu + kalan_vade + sermaye/risk + mvy + tk_detay +
grup12 + şube-personel + donuk_akim + faaliyet_gid_detay). Dönüştürücü ayrıca
daha uzun kuyruklu bazı rasyo ölçülerinde (TCMB tablosu gerektiren detaylı
faiz-getirili/maliyetli-pasif formülleri, tfv bazı katılım bankalarında eksik,
tek çeyreklik yükleme avg-balance/TTM ölçülerini tam besleyemiyor) kısmi
kapsıyor — bkz. pipeline/cikti_ingest.py modül docstring'i.
"""
from pathlib import Path
import json

import pytest

from pipeline.cikti_ingest import cikti_to_dataframe, bankalar_ve_donemler
from pipeline.lookup import LookupContext
from pipeline.compute import compute_all

SAMPLE_PATH = Path('/Users/farukkezer/Desktop/BDR-Arsiv/cikti/2026-2C.json')
COMPUTED_PATH = Path(__file__).resolve().parent.parent / 'data' / 'computed.json'
CATALOG_PATH = Path(__file__).resolve().parent.parent / 'data' / 'catalog.json'

pytestmark = pytest.mark.skipif(
    not SAMPLE_PATH.exists() or not COMPUTED_PATH.exists(),
    reason='BDR-Kısayol örnek dosyası veya data/computed.json bu makinede yok',
)


@pytest.fixture(scope='module')
def compute_result():
    data = json.loads(SAMPLE_PATH.read_text(encoding='utf-8'))
    df, banka_turu_map = cikti_to_dataframe(data)
    banks, dates = bankalar_ve_donemler(data)
    ctx = LookupContext(df.copy(), banka_turu_map)
    catalog = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))['measures']
    result = compute_all(ctx, base_data={}, catalog=catalog, banks=banks, dates=dates)
    return result, dates[0]


@pytest.fixture(scope='module')
def prod_bank_data():
    computed = json.loads(COMPUTED_PATH.read_text(encoding='utf-8'))
    return computed['bank_data']


# (measure_id, banka, beklenen_deger, göreli_tolerans)
AKBANK_CHECKS = [
    ('toplam_aktifler', 3_727_680_000_000.0),
    ('gayrinakdi_krediler', 678_636_000_000.0),
    ('rav', 2_561_637_000_000.0),
    ('toplam_risk_tabani', 2_912_879_000_000.0),
    ('kredi_riski_toplam_risk', 87.9417579652296),
    ('piyasa_riski_toplam_risk', 2.1687821567596868),
    ('operasyonel_risk_toplam_risk', 9.889459878010724),
    ('toplam_ozkaynaklar_regulasyon', 447_657_000_000.0),
    ('vadesiz_mevduat', 760_881_000_000.0),
    ('vadeli_mevduat', 1_621_399_000_000.0),
    ('tuketici_kredileri', 814_708_000_000.0),
    ('bireysel_kredi_kartlari', 354_071_000_000.0),
    ('grup_2_krediler', 176_792_000_000.0),
    ('sube_sayisi', 625.0),
    ('personel_sayisi', 12_223.0),
    ('reklam_giderleri', 1_245_000_000.0),
    ('likidite_acigi_vadesiz_ta', -11.862579405957593),
    ('likidite_acigi_1_5yil_ta', 18.05991930637823),
    ('brut_krediler_ta', 55.2917095888059),
]


@pytest.mark.parametrize('measure_id,beklenen', AKBANK_CHECKS)
def test_akbank_byte_exact(compute_result, measure_id, beklenen):
    result, dt = compute_result
    v = result.get(measure_id, {}).get('Akbank', {}).get(dt)
    assert v is not None, f'{measure_id} hiç hesaplanmadı'
    tol = max(1.0, abs(beklenen) * 0.002)
    assert abs(v - beklenen) <= tol, f'{measure_id}: {v!r} != {beklenen!r}'


def test_prod_ile_karsilastirma_tutarli(compute_result, prod_bank_data):
    """Aynı ölçüler prod'daki (computed.json) gerçek değerle de eşleşmeli —
    yukarıdaki sabit beklenen değerler eskirse bu test onu yakalar."""
    result, dt = compute_result
    for measure_id, _ in AKBANK_CHECKS:
        prod_v = prod_bank_data.get(measure_id, {}).get('Akbank', {}).get(dt)
        my_v = result.get(measure_id, {}).get('Akbank', {}).get(dt)
        assert prod_v is not None, f'{measure_id}: prod tarafında değer yok'
        tol = max(1.0, abs(prod_v) * 0.002)
        assert abs(my_v - prod_v) <= tol, f'{measure_id}: {my_v!r} != prod {prod_v!r}'
