"""
pipeline.custom_measure_rules
==============================
"Ölçü Oluştur" (kullanıcı tanımlı özel ölçü) için ANLAM kuralları: hangi
formül geçerli, sonuç hangi tip/birimde çıkar, değer nasıl hesaplanır.

Değer hesabı tarayıcıda da yapılır (frontend/index_v30.html, <cm-rules>
bloğu — AYNI kuralların JS karşılığı). Sunucu burada tanımın anlamlı olup
olmadığını doğrular ki API'ye doğrudan istek atılarak da saçma bir ölçü
kaydedilemesin; evaluate() ise sunucu tarafı önizleme içindir (chatbot).
İki taraf değişirse birlikte değişmeli — tests/fixtures/
custom_measure_cases.json her iki uygulamayı da aynı vakalarla sınar.

İfade ağacı (2026-09-25) — her düğüm şu üç biçimden biri:
    {"m": "<catalog ölçü id>"}                     ölçü
    {"k": 100}                                     sabit sayı
    {"op": "add|sub|mul|div", "l": düğüm, "r": düğüm, "bicim": "pct|kat"}
("bicim" yalnız iki ölçünün oranı olan div düğümünde; yoksa varsayılan.)
Eski tek işlemli tanımlar (op=ratio|diff|sum|scale, a, b, constant, bicim)
legacy_to_expr() ile birebir aynı anlamdaki ağaca çevrilir.

Kurallar:
- Toplama/çıkarma: iki taraf da ölçü ifadesi, aynı tip ve birim; tutar
  ölçülerde akım (gelir tablosu, YtD) ile stok (bilanço) karıştırılamaz.
  Sabit toplanamaz/çıkarılamaz.
- Çarpma: yalnız bir ölçü ifadesi × sabit (ölçü × ölçü anlamsız).
- Bölme: ifade / sabit (≠0) ölçekleme; ifade / ifade oran:
    rasyo / tutar ya da tutar / rasyo → geçersiz
    TL/TL     → yüzde (varsayılan) veya kat
    adet/adet → kat (varsayılan) veya yüzde
    TL/adet   → bin TL (birim başına; ör. personel başına kredi)
    adet/TL   → geçersiz
    rasyo/rasyo → kat (varsayılan) veya yüzde
  Akım tutar ile stok tutar oranlanırsa akım taraf son 12 aya (TTM), stok
  taraf 12 aylık ortalamaya çevrilir (ROAA deseni). Tutar alt ifadeleri
  yalnız toplama/çıkarma/sabitle ölçekleme içerdiğinden (hepsi doğrusal)
  bu dönüşüm yapraklara uygulanır.
- Bir işlemin iki tarafı aynı ifade olamaz (A−A, A/A anlamsız).
- En fazla MAX_LEAVES ölçü, MAX_DEPTH derinlik.
"""
from __future__ import annotations

import json
import math
from typing import Callable, Dict, List, Optional, Tuple

OPS = ('ratio', 'diff', 'sum', 'scale')          # eski (legacy) işlemler
EXPR_OPS = ('add', 'sub', 'mul', 'div')
BICIMLER = ('pct', 'kat')
# Oran biçimi → sonuç birimi ve çarpanı (frontend CM_BICIM ile aynı).
BICIM_BIRIM = {'pct': '%', 'kat': 'kat', 'bin_TL': 'bin_TL'}
BICIM_CARPAN = {'pct': 100.0, 'kat': 1.0, 'bin_TL': 0.001}

MAX_LEAVES = 10
MAX_DEPTH = 6
MAX_EXPR_JSON = 4000   # bayt — kötü niyetli/şişkin istek sınırı

_LEGACY_OP = {'ratio': 'div', 'diff': 'sub', 'sum': 'add', 'scale': 'mul'}


class ExprError(ValueError):
    """Kullanıcıya gösterilecek Türkçe hata mesajı taşır."""


def ratio_formats(ma: dict, mb: dict) -> List[str]:
    """Oran için izin verilen biçimler; ilki varsayılan. Boş liste = geçersiz.
    'bin_TL' sabit biçimdir (seçilemez)."""
    ta, tb = ma.get('tip'), mb.get('tip')
    if ta == 'rasyo' and tb == 'rasyo':
        return ['kat', 'pct']
    if ta != tb:
        return []
    ba, bb = ma.get('birim'), mb.get('birim')
    if ba == 'TL' and bb == 'TL':
        return ['pct', 'kat']
    if ba == 'adet' and bb == 'adet':
        return ['kat', 'pct']
    if ba == 'TL' and bb == 'adet':
        return ['bin_TL']
    return []


# ------------------------------------------------------------------
# Eski (tek işlemli) tanım → ağaç
# ------------------------------------------------------------------

def legacy_to_expr(op: str, a: Optional[str], b: Optional[str] = None,
                   constant=None, bicim: Optional[str] = None) -> Optional[dict]:
    """Geçersiz işlemde None. scale'de sabit yoksa 1 kullanılır (sabitin
    kendisi users.py'de ayrıca doğrulanır)."""
    if op not in _LEGACY_OP:
        return None
    if op == 'scale':
        return {'op': 'mul', 'l': {'m': a}, 'r': {'k': 1 if constant is None else constant}}
    node = {'op': _LEGACY_OP[op], 'l': {'m': a}, 'r': {'m': b}}
    if op == 'ratio' and bicim is not None:
        node['bicim'] = bicim
    return node


def record_expr(rec: dict) -> Optional[dict]:
    """Kayıtlı özel ölçünün ağacı (yeni kayıtlarda 'expr', eskilerde op/a/b)."""
    if rec.get('expr') is not None:
        return rec['expr']
    return legacy_to_expr(rec.get('op'), rec.get('a'), rec.get('b'),
                          rec.get('constant'), rec.get('bicim'))


# ------------------------------------------------------------------
# Biçim (şekil) doğrulaması — katalogdan bağımsız
# ------------------------------------------------------------------

def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _shape(node, depth: int, counter: List[int]) -> None:
    if depth > MAX_DEPTH:
        raise ExprError(f'Formül çok iç içe (en fazla {MAX_DEPTH} seviye)')
    if not isinstance(node, dict):
        raise ExprError('Geçersiz formül yapısı')
    if 'm' in node:
        if set(node) != {'m'} or not isinstance(node['m'], str) or not node['m'].strip():
            raise ExprError('Geçersiz ölçü düğümü')
        counter[0] += 1
        if counter[0] > MAX_LEAVES:
            raise ExprError(f'Formülde en fazla {MAX_LEAVES} ölçü olabilir')
        return
    if 'k' in node:
        if set(node) != {'k'} or not _is_num(node['k']):
            raise ExprError('Sabit geçerli bir sayı olmalı')
        return
    op = node.get('op')
    if op not in EXPR_OPS:
        raise ExprError(f"Geçersiz işlem: '{op}'")
    allowed = {'op', 'l', 'r', 'bicim'} if op == 'div' else {'op', 'l', 'r'}
    if not set(node) <= allowed or 'l' not in node or 'r' not in node:
        raise ExprError('Geçersiz formül yapısı')
    if 'bicim' in node and node['bicim'] is not None and node['bicim'] not in BICIMLER:
        raise ExprError(f"Geçersiz biçim: '{node['bicim']}'")
    _shape(node['l'], depth + 1, counter)
    _shape(node['r'], depth + 1, counter)


def check_shape(expr) -> Optional[str]:
    """Yalnız yapı + boyut sınırları (katalog gerektirmez). Hata ya da None."""
    try:
        if len(json.dumps(expr, ensure_ascii=False)) > MAX_EXPR_JSON:
            raise ExprError('Formül çok uzun')
        _shape(expr, 1, [0])
    except ExprError as e:
        return str(e)
    except (TypeError, ValueError, RecursionError):
        return 'Geçersiz formül yapısı'
    return None


# ------------------------------------------------------------------
# Anlam analizi (tip çıkarımı) → hesap planı
# ------------------------------------------------------------------
# Plan düğümü: {'kind': 'm'|'k'|op, ..., 'type': {tip, birim, akim_stok}}
# div düğümünde ek olarak: 'scale_only' (sabite bölme), 'modes' (l, r için
# 'ttm'|'avg'|None), 'bicim', 'formats', 'carpan'.

def _same(a: dict, b: dict) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def _analyze(node: dict, by_id: Dict[str, dict]) -> dict:
    if 'm' in node:
        m = by_id.get(node['m'])
        if m is None:
            raise ExprError(f"'{node['m']}' geçerli bir ölçü değil")
        return {'kind': 'm', 'id': node['m'],
                'type': {'tip': m.get('tip'), 'birim': m.get('birim'),
                         'akim_stok': m.get('akim_stok')}}
    if 'k' in node:
        return {'kind': 'k', 'k': float(node['k']), 'type': {'tip': 'sabit'}}

    op = node['op']
    L = _analyze(node['l'], by_id)
    R = _analyze(node['r'], by_id)
    tl, tr = L['type'], R['type']
    ks = (tl['tip'] == 'sabit', tr['tip'] == 'sabit')
    out = {'kind': op, 'l': L, 'r': R}

    if op in ('add', 'sub'):
        if any(ks):
            raise ExprError('Sabit sayı yalnız çarpma ve bölmede kullanılabilir')
        if _same(node['l'], node['r']):
            raise ExprError('A ve B aynı ölçü olamaz')
        if tl['birim'] != tr['birim']:
            raise ExprError(f"Birimler uyuşmuyor ({tl['birim']} ≠ {tr['birim']}) — "
                            f"fark/toplam için aynı birimde iki ölçü seçin")
        if tl['tip'] != tr['tip']:
            raise ExprError('Tutar ile rasyo toplanamaz/çıkarılamaz')
        if tl['tip'] == 'buyukluk' and tl['akim_stok'] != tr['akim_stok']:
            raise ExprError('Gelir tablosu kalemi (yılbaşından kümülatif) ile bilanço kalemi '
                            '(dönem sonu bakiye) toplanamaz/çıkarılamaz')
        out['type'] = dict(tl)
        return out

    if op == 'mul':
        if all(ks):
            raise ExprError('İki sabit sayı çarpılamaz — sonucu doğrudan yazın')
        if not any(ks):
            raise ExprError('İki ölçü çarpılamaz — çarpma yalnız bir sabit sayıyla yapılabilir')
        k = (L if ks[0] else R)['k']
        if k == 0:
            raise ExprError('Sabit 0 olamaz (sonuç her zaman 0 olur)')
        out['type'] = dict(tr if ks[0] else tl)
        return out

    # div
    if ks[0]:
        raise ExprError('Sabit sayı bir ölçüye bölünemez')
    if ks[1]:
        if R['k'] == 0:
            raise ExprError('Sıfıra bölünemez')
        if node.get('bicim') is not None:
            raise ExprError('Sabite bölmede sonuç biçimi seçilemez')
        out.update(scale_only=True, type=dict(tl))
        return out
    if _same(node['l'], node['r']):
        raise ExprError('A ve B aynı ölçü olamaz')
    formats = ratio_formats(tl, tr)
    if not formats:
        raise ExprError('Bu iki ölçünün oranı anlamlı değil (rasyo ile tutar ya da adet / TL)')
    bicim = node.get('bicim')
    if bicim is not None and bicim not in formats:
        raise ExprError(f"Bu oran için geçersiz biçim: '{bicim}'")
    bicim = bicim or formats[0]
    karisik = (tl['tip'] == 'buyukluk' and tr['tip'] == 'buyukluk'
               and tl['akim_stok'] != tr['akim_stok'])
    modes = ((('ttm' if tl['akim_stok'] == 'akim' else 'avg'),
              ('ttm' if tr['akim_stok'] == 'akim' else 'avg')) if karisik else (None, None))
    out.update(scale_only=False, bicim=bicim, formats=formats, modes=modes,
               carpan=BICIM_CARPAN[bicim],
               type={'tip': 'rasyo', 'birim': BICIM_BIRIM[bicim],
                     'akim_stok': 'akim' if 'akim' in (tl['akim_stok'], tr['akim_stok']) else 'stok'})
    return out


def analyze(expr, by_id: Dict[str, dict]) -> Tuple[Optional[dict], Optional[str]]:
    """(plan, None) ya da (None, hata_mesajı)."""
    err = check_shape(expr)
    if err:
        return None, err
    try:
        plan = _analyze(expr, by_id)
    except ExprError as e:
        return None, str(e)
    if plan['type']['tip'] == 'sabit':
        return None, 'Formülde en az bir ölçü olmalı'
    return plan, None


def check_expr(expr, by_id: Dict[str, dict]) -> Optional[str]:
    """Hata mesajı ya da None (geçerli)."""
    return analyze(expr, by_id)[1]


def check(op: str, a: str, b: Optional[str], bicim: Optional[str],
          by_id: Dict[str, dict]) -> Optional[str]:
    """Eski tek işlemli tanım için geriye uyumlu kontrol."""
    expr = legacy_to_expr(op, a, b, None, bicim)
    if expr is None:
        return f"Geçersiz işlem: '{op}'"
    if op != 'scale' and not b:
        return f"'{b}' geçerli bir ölçü değil"
    return check_expr(expr, by_id)


def measure_ids(expr) -> List[str]:
    """Formülde geçen ölçü id'leri (ilk görülme sırasıyla, tekrarsız)."""
    out: List[str] = []

    def walk(n):
        if not isinstance(n, dict):
            return
        if 'm' in n:
            if n['m'] not in out:
                out.append(n['m'])
        elif 'op' in n:
            walk(n.get('l'))
            walk(n.get('r'))
    walk(expr)
    return out


# ------------------------------------------------------------------
# Hesap — frontend cmNokta/cmEval ile aynı formül
# ------------------------------------------------------------------

def _yil_once(t: str) -> str:
    return f'{int(t[:4]) - 1}{t[4:]}'


def point(seri: Dict[str, Optional[float]], t: str, mode: Optional[str]) -> Optional[float]:
    """Bir serinin t dönemindeki değeri; mode 'ttm' | 'avg' | None
    (pipeline/lookup.py ttm_flow/avg_balance ile aynı formül)."""
    v = seri.get(t)
    if v is None:
        return None
    if mode == 'ttm':
        ay = int(t[5:7])
        if ay == 12:
            return v
        yil_sonu = seri.get(f'{int(t[:4]) - 1}-12-31')
        gecen = seri.get(_yil_once(t))
        return v + yil_sonu - gecen if (yil_sonu is not None and gecen is not None) else v * 12 / ay
    if mode == 'avg':
        once = seri.get(_yil_once(t))
        return v if once is None else (v + once) / 2
    return v


def evaluate(plan: dict, series: Callable[[str], Dict[str, Optional[float]]],
             t: str, mode: Optional[str] = None) -> Optional[float]:
    """Plan'ı t döneminde hesaplar. series(ölçü_id) → {tarih: değer}."""
    kind = plan['kind']
    if kind == 'm':
        return point(series(plan['id']) or {}, t, mode)
    if kind == 'k':
        return plan['k']
    if kind == 'div' and not plan['scale_only']:
        ml, mr = plan['modes']
        va = evaluate(plan['l'], series, t, ml or mode)
        if va is None:
            return None
        vb = evaluate(plan['r'], series, t, mr or mode)
        if vb is None or vb == 0:
            return None
        return va / vb * plan['carpan']
    va = evaluate(plan['l'], series, t, mode)
    if va is None:
        return None
    vb = evaluate(plan['r'], series, t, mode)
    if vb is None:
        return None
    if kind == 'add':
        return va + vb
    if kind == 'sub':
        return va - vb
    if kind == 'mul':
        return va * vb
    return va / vb   # div, sabite bölme (sıfır analizde engellendi)


# ------------------------------------------------------------------
# Okunur formül metni — frontend cmExprText ile aynı çıktı
# ------------------------------------------------------------------

_ISARET = {'add': ' + ', 'sub': ' − ', 'mul': ' × ', 'div': ' / '}
_OPERATOR_IN_AD = ('/', '+', '×', '−', ' - ')


def _sabit_metin(k: float) -> str:
    s = repr(float(k))
    if s.endswith('.0'):
        s = s[:-2]
    return s.replace('.', ',')


def _prec(kind: str) -> int:
    return 1 if kind in ('add', 'sub') else 2 if kind in ('mul', 'div') else 3


def formula_text(plan: dict, by_id: Dict[str, dict], mode: Optional[str] = None,
                 parent: Optional[dict] = None, sag: bool = False) -> str:
    """analyze() planından okunur formül (TTM/Ort. önekleri, × 100 dahil)."""
    kind = plan['kind']
    if kind == 'm':
        ad = by_id[plan['id']]['ad']
        if parent is not None and any(o in ad for o in _OPERATOR_IN_AD):
            ad = f'({ad})'
        return ('TTM ' if mode == 'ttm' else 'Ort. ' if mode == 'avg' else '') + ad
    if kind == 'k':
        return _sabit_metin(plan['k'])
    oran = kind == 'div' and not plan['scale_only']
    ml = (plan['modes'][0] or mode) if oran else mode
    mr = (plan['modes'][1] or mode) if oran else mode
    metin = (formula_text(plan['l'], by_id, ml, plan, False) + _ISARET[kind]
             + formula_text(plan['r'], by_id, mr, plan, True))
    if oran and plan['bicim'] == 'pct':
        metin += ' × 100'
    if parent is not None:
        pp, cp = _prec(parent['kind']), _prec(kind)
        if cp < pp or (sag and cp == pp and parent['kind'] != 'add') or (oran and plan['bicim'] == 'pct'):
            metin = f'({metin})'
    return metin
