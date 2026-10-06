"""Reel TL / USD bazı (2026-10-02): pipeline/makro.donem_makro katsayıları."""
import json

import pytest

import pipeline.makro as M


@pytest.fixture
def sahte_makro(monkeypatch, tmp_path):
    veri = {
        'tufe_endeks': {'2025-10': 100.0, '2025-11': 102.0, '2025-12': 104.0, '2026-01': 110.0, '2026-02': 112.0, '2026-03': 114.0},
        'usd_ay_sonu': {'2025-12': 42.0, '2026-03': 44.0},
        'usd_ay_ort': {'2026-01': 42.5, '2026-02': 43.0, '2026-03': 43.5},
        'kaynak': {'tufe_endeks': 'test'}, 'guncelleme': '2026-10-02',
    }
    p = tmp_path / 'makro_seriler.json'
    p.write_text(json.dumps(veri), encoding='utf-8')
    monkeypatch.setattr(M, '_MAKRO_YOL', p)
    M._makro.cache_clear()
    yield
    M._makro.cache_clear()


def test_donem_katsayilari(sahte_makro):
    d = M.donem_makro(['2025-12-31', '2026-03-31'])['donem']
    # Stok: dönem sonu ayı; akım: yılbaşından ortalama
    assert d['2026-03-31']['tufe'] == 114.0
    assert d['2026-03-31']['tufe_ytd'] == pytest.approx((110 + 112 + 114) / 3)
    assert d['2026-03-31']['usd'] == 44.0
    assert d['2026-03-31']['usd_ytd'] == pytest.approx(43.0)
    # 2025 ayları eksik → tufe_ytd / usd_ytd yazılmaz, ama dönem sonu değerleri yazılır
    assert d['2025-12-31']['tufe'] == 104.0 and 'tufe_ytd' not in d['2025-12-31']
    assert d['2025-12-31']['usd'] == 42.0 and 'usd_ytd' not in d['2025-12-31']


def test_gercek_dosya_son_ceyrek():
    M._makro.cache_clear()
    d = M.donem_makro(['2026-06-30'])['donem'].get('2026-06-30')
    assert d and d['tufe'] > 0 and d['usd'] > 0 and d['tufe_ytd'] < d['tufe']
