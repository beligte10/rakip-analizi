"""OPEX/gelir büyümesi, reel OPEX ve makas ölçüleri (slayt 'Gider performansı', 6A2026)."""
import json
from pathlib import Path

import pytest

from pipeline.makro import tufe_yillik
from pipeline.measures import reel_buyume

COMPUTED = Path(__file__).resolve().parent.parent / 'data' / 'computed.json'


def test_reel_buyume_fisher():
    assert reel_buyume(49.6, 32.11) == pytest.approx(13.2, abs=0.05)
    assert reel_buyume(None, 30.0) is None
    assert reel_buyume(10.0, None) is None


def test_tufe_dosyasi():
    assert tufe_yillik('2026-06-30') == pytest.approx(32.109, abs=0.01)
    assert tufe_yillik('1999-01-01') is None


@pytest.mark.skipif(not COMPUTED.exists(), reason='computed.json yok')
def test_slayt_degerleri():
    bd = json.loads(COMPUTED.read_text(encoding='utf-8'))['bank_data']
    t = '2026-06-30'
    beklenen = {'Kuveyt Türk': (49.6, 13.2), 'Denizbank': (48.2, 12.2), 'Garanti Bankası': (46.3, 10.8),
                'Akbank': (36.5, 3.3), 'Yapı Kredi': (34.5, 1.8), 'QNB': (32.8, 0.5)}
    for b, (nom, reel) in beklenen.items():
        assert bd['opex_yoy_buyumesi'][b][t] == pytest.approx(nom, abs=0.06), b
        assert bd['reel_opex_buyumesi'][b][t] == pytest.approx(reel, abs=0.06), b
    kt = 'Kuveyt Türk'
    assert bd['gelir_yoy_buyumesi'][kt][t] == pytest.approx(40.4, abs=0.06)
    assert bd['opex_gelir_makasi'][kt][t] == pytest.approx(
        bd['gelir_yoy_buyumesi'][kt][t] - bd['opex_yoy_buyumesi'][kt][t], abs=1e-9)
