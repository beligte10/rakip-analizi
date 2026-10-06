"""
"Ölçü Oluştur" (özel ölçü) testleri: anlam kuralları
(pipeline/custom_measure_rules) ve kayıt mantığı (users.py). HTTP katmanı
olmadan, test_auth.py ile aynı desen.
"""
import json
import math
from pathlib import Path

import pytest

import users as U
from pipeline import custom_measure_rules as R

CAT = {
    'krediler': {'tip': 'buyukluk', 'birim': 'TL', 'akim_stok': 'stok'},
    'mevduat': {'tip': 'buyukluk', 'birim': 'TL', 'akim_stok': 'stok'},
    'net_kar': {'tip': 'buyukluk', 'birim': 'TL', 'akim_stok': 'akim'},
    'faiz_gel': {'tip': 'buyukluk', 'birim': 'TL', 'akim_stok': 'akim'},
    'personel': {'tip': 'buyukluk', 'birim': 'adet', 'akim_stok': 'stok'},
    'sube': {'tip': 'buyukluk', 'birim': 'adet', 'akim_stok': 'stok'},
    'roaa': {'tip': 'rasyo', 'birim': '%', 'akim_stok': 'akim'},
    'roae': {'tip': 'rasyo', 'birim': '%', 'akim_stok': 'akim'},
    'fga_mp': {'tip': 'rasyo', 'birim': 'kat', 'akim_stok': 'stok'},
}


# --- Anlam kuralları ---

@pytest.mark.parametrize('op,a,b,bicim', [
    ('ratio', 'krediler', 'mevduat', None),
    ('ratio', 'krediler', 'mevduat', 'kat'),
    ('ratio', 'net_kar', 'krediler', 'pct'),     # akım/stok: TTM/ortalama ile
    ('ratio', 'krediler', 'personel', None),     # TL/adet → bin TL
    ('ratio', 'personel', 'sube', None),
    ('ratio', 'roae', 'roaa', None),             # rasyo/rasyo → kat
    ('ratio', 'roaa', 'fga_mp', 'pct'),
    ('diff', 'krediler', 'mevduat', None),
    ('sum', 'net_kar', 'faiz_gel', None),        # akım + akım
    ('diff', 'roae', 'roaa', None),
    ('scale', 'krediler', None, None),
    ('scale', 'roaa', None, None),
])
def test_gecerli_kombinasyonlar(op, a, b, bicim):
    assert R.check(op, a, b, bicim, CAT) is None


@pytest.mark.parametrize('op,a,b,bicim,parca', [
    ('ratio', 'krediler', 'krediler', None, 'aynı ölçü'),
    ('diff', 'krediler', 'krediler', None, 'aynı ölçü'),
    ('ratio', 'roaa', 'krediler', None, 'anlamlı değil'),        # rasyo / tutar
    ('ratio', 'krediler', 'roaa', None, 'anlamlı değil'),
    ('ratio', 'personel', 'krediler', None, 'anlamlı değil'),    # adet / TL
    ('ratio', 'krediler', 'personel', 'pct', 'geçersiz biçim'),  # TL/adet sabit bin TL
    ('diff', 'krediler', 'personel', None, 'Birimler uyuşmuyor'),
    ('sum', 'roaa', 'fga_mp', None, 'Birimler uyuşmuyor'),
    ('sum', 'net_kar', 'krediler', None, 'toplanamaz'),          # akım + stok
    ('diff', 'yok', 'krediler', None, 'geçerli bir ölçü değil'),
    ('ratio', 'krediler', None, None, 'geçerli bir ölçü değil'),
    ('carp', 'krediler', 'mevduat', None, 'Geçersiz işlem'),
])
def test_gecersiz_kombinasyonlar(op, a, b, bicim, parca):
    err = R.check(op, a, b, bicim, CAT)
    assert err and parca in err, err


def test_varsayilan_bicimler():
    assert R.ratio_formats(CAT['krediler'], CAT['mevduat'])[0] == 'pct'
    assert R.ratio_formats(CAT['personel'], CAT['sube'])[0] == 'kat'
    assert R.ratio_formats(CAT['roae'], CAT['roaa'])[0] == 'kat'
    assert R.ratio_formats(CAT['krediler'], CAT['personel']) == ['bin_TL']


# --- Kayıt (users.py) ---

@pytest.fixture
def uid(tmp_path):
    p = tmp_path / 'users.json'
    U.ensure_users_file(p)
    ok, err = U.create_signup(p, 'Ali', 'ali@kuveytturk.com.tr', 'parola12345')
    assert ok, err
    return p, U.list_users(p)[-1]['id']


def test_kayit_bicim_saklanir_ve_oran_disinda_silinir(uid):
    # Eski tek işlemli istek ağaca çevrilerek saklanır; biçim yalnız oranda.
    p, u = uid
    ok, rec = U.add_custom_measure(p, u, 'Kredi/Mevduat', 'ratio', 'krediler', 'mevduat', bicim='kat')
    assert ok and rec['expr'] == {'op': 'div', 'l': {'m': 'krediler'}, 'r': {'m': 'mevduat'}, 'bicim': 'kat'}
    ok, rec2 = U.add_custom_measure(p, u, 'Kredi - Mevduat', 'diff', 'krediler', 'mevduat', bicim='kat')
    assert ok and rec2['expr'] == {'op': 'sub', 'l': {'m': 'krediler'}, 'r': {'m': 'mevduat'}}
    assert 'op' not in rec and 'bicim' not in rec


def test_ayni_ad_engellenir_buyuk_kucuk_harf_ve_bosluk_duyarsiz(uid):
    p, u = uid
    assert U.add_custom_measure(p, u, 'Kredi / Mevduat', 'ratio', 'krediler', 'mevduat')[0]
    ok, err = U.add_custom_measure(p, u, '  kredi   /  MEVDUAT ', 'ratio', 'mevduat', 'krediler')
    assert not ok and 'zaten var' in err


def test_guncellemede_kendi_adi_serbest_baskasininki_degil(uid):
    p, u = uid
    _, r1 = U.add_custom_measure(p, u, 'Birinci', 'ratio', 'krediler', 'mevduat')
    _, r2 = U.add_custom_measure(p, u, 'İkinci', 'ratio', 'mevduat', 'krediler')
    assert U.update_custom_measure(p, u, r1['id'], 'Birinci', 'ratio', 'krediler', 'mevduat', bicim='kat')[0]
    ok, err = U.update_custom_measure(p, u, r2['id'], 'birinci', 'ratio', 'mevduat', 'krediler')
    assert not ok and 'zaten var' in err


@pytest.mark.parametrize('sabit,parca', [
    (None, 'sayısal'), (0, '0 olamaz'), (math.inf, 'sayısal'), (math.nan, 'sayısal'), (True, 'sayısal'),
])
def test_sabit_dogrulamasi(uid, sabit, parca):
    p, u = uid
    ok, err = U.add_custom_measure(p, u, 'Ölçek', 'scale', 'krediler', constant=sabit)
    assert not ok and parca in err


def test_gecersiz_bicim_reddedilir(uid):
    p, u = uid
    ok, err = U.add_custom_measure(p, u, 'X', 'ratio', 'krediler', 'mevduat', bicim='bps')
    assert not ok and 'biçim' in err


def test_ad_bosluklari_normalize_edilir(uid):
    p, u = uid
    _, rec = U.add_custom_measure(p, u, '  Kredi    Mevduat  ', 'ratio', 'krediler', 'mevduat')
    assert rec['ad'] == 'Kredi Mevduat'


# --- İfade ağacı (2026-09-25) — ortak vakalar, JS ile aynı dosya ---

CASES = json.loads((Path(__file__).parent / 'fixtures' / 'custom_measure_cases.json')
                   .read_text(encoding='utf-8'))
FCAT = CASES['catalog']


@pytest.mark.parametrize('case', CASES['valid'], ids=lambda c: c['ad'])
def test_agac_gecerli(case):
    plan, err = R.analyze(case['expr'], FCAT)
    assert err is None, err
    assert plan['type'] == case['type']


@pytest.mark.parametrize('case', CASES['invalid'], ids=lambda c: c['ad'])
def test_agac_gecersiz(case):
    err = R.check_expr(case['expr'], FCAT)
    assert err and case['hata'] in err, err


@pytest.mark.parametrize('case', CASES['eval'], ids=lambda c: json.dumps(c['expr'])[:60])
def test_agac_hesap(case):
    plan, err = R.analyze(case['expr'], FCAT)
    assert err is None, err
    v = R.evaluate(plan, lambda i: CASES['series'].get(i, {}), case['tarih'])
    if case['beklenen'] is None:
        assert v is None
    else:
        assert v == pytest.approx(case['beklenen'], rel=1e-12)


@pytest.mark.parametrize('case', CASES['legacy'], ids=lambda c: c['kayit']['op'])
def test_eski_kayit_agaca_cevrilir(case):
    assert R.record_expr(case['kayit']) == case['expr']


def test_eski_kayit_ile_agac_ayni_sonucu_verir():
    # Eski check() ile ağaç üzerinden kontrol aynı kararı verir.
    for op, a, b in [('ratio', 'net_kar', 'aktif'), ('diff', 'net_kar', 'krediler'),
                     ('ratio', 'roaa', 'krediler'), ('sum', 'krediler', 'menkul')]:
        assert R.check(op, a, b, None, FCAT) == R.check_expr(R.legacy_to_expr(op, a, b), FCAT)


def test_measure_ids_sirali_tekrarsiz():
    e = CASES['valid'][11]['expr']   # (A-B)/A
    assert R.measure_ids(e) == ['krediler', 'mevduat']


def test_kayit_agac_ile(uid):
    p, u = uid
    expr = {'op': 'div', 'l': {'op': 'add', 'l': {'m': 'krediler'}, 'r': {'m': 'menkul'}},
            'r': {'m': 'aktif'}}
    ok, rec = U.add_custom_measure(p, u, 'Kredi+Menkul / Aktif', expr=expr)
    assert ok and rec['expr'] == expr
    assert U.list_custom_measures(p, u)[0]['expr'] == expr


def test_kayit_bozuk_agac_reddedilir(uid):
    p, u = uid
    ok, err = U.add_custom_measure(p, u, 'Bozuk', expr={'op': 'div', 'l': {'m': 'krediler'}})
    assert not ok and 'yapısı' in err
    ok, err = U.add_custom_measure(p, u, 'Uzun', expr={'m': 'x' * 5000})
    assert not ok and 'uzun' in err


def test_eski_kayit_guncellenince_agaca_gecer(uid):
    p, u = uid
    data = json.loads(p.read_text(encoding='utf-8'))
    eski = {'id': 'custom_eski', 'ad': 'Eski', 'op': 'ratio', 'a': 'krediler', 'b': 'mevduat',
            'constant': None, 'sort_direction': 'desc', 'bicim': 'kat', 'created_at': 'x'}
    data['users'][-1].setdefault('custom_measures', []).append(eski)
    p.write_text(json.dumps(data), encoding='utf-8')
    assert R.record_expr(U.list_custom_measures(p, u)[0])['bicim'] == 'kat'
    expr = {'op': 'mul', 'l': {'m': 'krediler'}, 'r': {'k': 2}}
    ok, rec = U.update_custom_measure(p, u, 'custom_eski', 'Eski', expr=expr)
    assert ok and rec['expr'] == expr and 'op' not in rec and 'a' not in rec


@pytest.mark.parametrize('case', CASES['metin'], ids=lambda c: c['formul'][:40])
def test_okunur_formul_js_ile_ayni(case):
    plan, err = R.analyze(case['expr'], FCAT)
    assert err is None, err
    assert R.formula_text(plan, FCAT) == case['formul']
