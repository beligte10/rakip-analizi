"""TP/YP mevduat vadeli-vadesiz kompozisyon ölçüleri (2026-10-13): her banka ve grupta vadeli + vadesiz payı %100 eder."""
import json
from pathlib import Path

import pytest

COMPUTED = Path(__file__).resolve().parent.parent / 'data' / 'computed.json'
CIFTLER = [('tp_vadeli_tp_mevduat', 'tp_vadesiz_tp_mevduat'), ('yp_vadeli_yp_mevduat', 'yp_vadesiz_yp_mevduat')]

pytestmark = pytest.mark.skipif(not COMPUTED.exists(), reason='data/computed.json yok')


@pytest.fixture(scope='module')
def veri():
    return json.loads(COMPUTED.read_text(encoding='utf-8'))


def test_banka_payları_toplam_yuz(veri):
    sayac = 0
    for vadeli, vadesiz in CIFTLER:
        bd = veri['bank_data']
        assert vadeli in bd and vadesiz in bd
        for banka, seri in bd[vadeli].items():
            for t, v in seri.items():
                w = (bd[vadesiz].get(banka) or {}).get(t)
                if v is None or w is None:
                    continue
                assert abs(v + w - 100) < 0.01, (banka, t, v, w)
                sayac += 1
    assert sayac > 500


def test_grup_payları_toplam_yuz(veri):
    gd = veri['group_data']
    for vadeli, vadesiz in CIFTLER:
        for grup, seri in gd[vadeli].items():
            for t, o in seri.items():
                v, w = o.get('value'), ((gd[vadesiz].get(grup) or {}).get(t) or {}).get('value')
                if v is None or w is None:
                    continue
                assert abs(v + w - 100) < 0.01, (grup, t, v, w)


def test_mevduat_kompozisyonu_ve_doviz_alt_dilimleri(veri):
    """Kompozisyon sekmesindeki 'Mevduat Kompozisyonu': bileşen yüzdeleri ve Döviz görünümündeki TP/YP × vadeli/vadesiz dilimleri %100 eder."""
    cd, cu = veri['composition_data']['mevduat'], veri['currency_data']['mevduat']
    assert 'mevduat' in veri['meta']['compositions'] and veri['meta']['compositions']['mevduat'].get('currency_alt')
    sayac = 0
    for tur in ('bank', 'group'):
        for ad, seri in cu[tur].items():
            for t, rec in seri.items():
                assert rec['alt'] and abs(sum(x['pct'] for x in rec['alt']) - 100) < 0.01, (ad, t)
                tp = sum(x['pct'] for x in rec['alt'] if x['id'].startswith('tp_'))
                assert abs(tp - rec['tp_pct']) < 0.05, (ad, t, tp, rec['tp_pct'])     # alt dilimler TP/YP toplamıyla tutarlı
                assert abs(sum(x['pct'] for x in cd[tur][ad][t]) - 100) < 0.01
                sayac += 1
    assert sayac > 500
