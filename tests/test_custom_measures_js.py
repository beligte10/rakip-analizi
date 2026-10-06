"""
Frontend <cm-rules> bloğunun (frontend/index_v30.html) Python kurallarıyla
aynı sonuçları verdiğini sınar: blok işaretler arasından çıkarılıp node
(yoksa macOS'un JavaScriptCore `jsc`'si) ile tests/fixtures/
custom_measure_cases.json üzerinde çalıştırılır. Çalışan bir JS motoru
yoksa atlanır.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = ROOT / 'tests' / 'fixtures' / 'custom_measure_cases.json'
JSC = Path('/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc')


def _js_engine():
    """Çalışan ilk JS motoru (node bozuk kurulu olabiliyor — önce dene)."""
    for cand in (shutil.which('node'), str(JSC) if JSC.exists() else None):
        if not cand:
            continue
        try:
            r = subprocess.run([cand, '-e', '1'] if cand.endswith('node') else [cand, '-e', 'print(1)'],
                               capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if r.returncode == 0:
            return cand
    return None


# Vakalar ve blok betiğe gömülür (motorlar arası dosya API'si farkı yok).
HARNESS = r"""
const cases = __CASES__;
const code = __CODE__;
const api = new Function(code + `; return { cmAnalyze, cmEval, cmParseFormula, cmRecordExpr,
  customMeasureSpec, cmFormulaText, cmSimpleForm, cmSeri };`)();
const cat = cases.catalog;
const out = { valid: [], invalid: [], eval: [], parse: [], parse_hata: [], metin: [], legacy: [], roundtrip: [] };
for (const c of cases.valid) { const r = api.cmAnalyze(c.expr, cat); out.valid.push(r.error || r.plan.type); }
for (const c of cases.invalid) { const r = api.cmAnalyze(c.expr, cat); out.invalid.push(r.error || null); }
for (const c of cases.eval) {
  const r = api.cmAnalyze(c.expr, cat);
  out.eval.push(r.error ? { error: r.error } : api.cmEval(r.plan, id => cases.series[id] || {}, c.tarih, null));
}
for (const c of cases.parse) { const r = api.cmParseFormula(c.metin, cat); out.parse.push(r.error ? { error: r.error } : r.expr); }
for (const c of cases.parse_hata) { const r = api.cmParseFormula(c.metin, cat); out.parse_hata.push(r.error || null); }
for (const c of cases.metin) { const s = api.customMeasureSpec({ expr: c.expr }, cat); out.metin.push(s.error || s.formul); }
for (const c of cases.legacy) out.legacy.push(api.cmRecordExpr(c.kayit));
// Düzenlenebilir metin → ayrıştır → aynı ağaç (bicim hariç: kökte ayrı seçilir)
for (const c of cases.valid) {
  const strip = n => n && n.op ? { op: n.op, l: strip(n.l), r: strip(n.r) } : n;
  const r = api.cmParseFormula(api.cmFormulaText(c.expr, cat), cat);
  out.roundtrip.push(JSON.stringify(r.expr ? strip(r.expr) : r) === JSON.stringify(strip(c.expr)));
}
(typeof console !== 'undefined' && console.log ? console.log : print)(JSON.stringify(out));
"""


@pytest.fixture(scope='module')
def js(tmp_path_factory):
    engine = _js_engine()
    if not engine:
        pytest.skip('çalışan bir JS motoru (node/jsc) yok')
    html = (ROOT / 'frontend' / 'index_v30.html').read_text(encoding='utf-8')
    m = re.search(r'// <cm-rules>[^\n]*\n(.*?)// </cm-rules>', html, re.S)
    assert m, '<cm-rules> işaretleri bulunamadı'
    d = tmp_path_factory.mktemp('cmjs')
    script = (HARNESS.replace('__CASES__', CASES_PATH.read_text(encoding='utf-8'))
              .replace('__CODE__', json.dumps(m.group(1))))
    (d / 'harness.js').write_text(script, encoding='utf-8')
    res = subprocess.run([engine, str(d / 'harness.js')], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr or res.stdout
    out = json.loads(res.stdout)
    for k in ('valid', 'invalid', 'eval', 'parse', 'parse_hata', 'metin', 'legacy'):
        assert len(out[k]) == len(CASES[k]) > 0, k   # zip sessizce boş geçmesin
    return out


CASES = json.loads(CASES_PATH.read_text(encoding='utf-8'))


def test_gecerli_ayni_tip(js):
    for c, got in zip(CASES['valid'], js['valid']):
        assert got == c['type'], (c['ad'], got)


def test_gecersiz_ayni_hata(js):
    for c, got in zip(CASES['invalid'], js['invalid']):
        assert got and c['hata'] in got, (c['ad'], got)


def test_hesap_ayni(js):
    for c, got in zip(CASES['eval'], js['eval']):
        if c['beklenen'] is None:
            assert got is None, (c, got)
        else:
            assert got == pytest.approx(c['beklenen'], rel=1e-12), (c, got)


def test_ayristirici(js):
    for c, got in zip(CASES['parse'], js['parse']):
        assert got == c['expr'], (c['metin'], got)
    for c, got in zip(CASES['parse_hata'], js['parse_hata']):
        assert got and c['hata'] in got, (c['metin'], got)


def test_okunur_formul(js):
    for c, got in zip(CASES['metin'], js['metin']):
        assert got == c['formul'], got


def test_eski_kayit(js):
    for c, got in zip(CASES['legacy'], js['legacy']):
        assert got == c['expr'], (c['kayit'], got)


def test_metin_gidis_donus(js):
    assert all(js['roundtrip']), js['roundtrip']
