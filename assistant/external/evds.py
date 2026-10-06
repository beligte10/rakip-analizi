"""TCMB EVDS istemcisi (2026-09-30).

Servis: https://evds3.tcmb.gov.tr/igmevdsms-dis/ (evds2 adresi buraya
yönlendiriyor). Anahtar HTTP başlığında ("key") gönderilir; EVDS_API_KEY
ortam değişkeninden okunur. Kullanım şartları: veriler kaynak (TCMB EVDS)
gösterilerek kullanılabilir; yatırım tavsiyesi niteliği taşımaz.
"""
from __future__ import annotations

import os
import re
import unicodedata
from typing import Dict, List, Optional

from .http import ExternalError, TTLCache, request_json

BASE_URL = 'https://evds3.tcmb.gov.tr/igmevdsms-dis'
SOURCE = 'TCMB EVDS servisi'

FREKANS = {'gunluk': 1, 'isgunu': 2, 'haftalik': 3, 'ayda2': 4, 'aylik': 5,
           'ceyreklik': 6, 'altiaylik': 7, 'yillik': 8}
TOPLULASTIRMA = ('avg', 'min', 'max', 'first', 'last', 'sum')
FORMUL = {'duzey': 0, 'yuzde_degisim': 1, 'fark': 2, 'yillik_yuzde_degisim': 3, 'yillik_fark': 4,
          'yil_sonuna_gore_yuzde_degisim': 5, 'yil_sonuna_gore_fark': 6,
          'hareketli_ortalama': 7, 'hareketli_toplam': 8}
MAX_SERIES = 5
_SERIES_RE = re.compile(r'^[A-Z0-9_.]{3,40}$')

_groups = TTLCache(ttl=12 * 3600)
_series = TTLCache(ttl=12 * 3600)


def api_key() -> str:
    return os.environ.get('EVDS_API_KEY', '').strip()


def enabled() -> bool:
    return bool(api_key())


def _get(path: str, timeout: float = 45.0):
    return request_json(f'{BASE_URL}/{path}', headers={'key': api_key()}, timeout=timeout, source=SOURCE)


def _norm(s: str) -> str:
    s = unicodedata.normalize('NFKD', str(s or '')).casefold().replace('ı', 'i')
    return ''.join(c for c in s if not unicodedata.combining(c))


def datagroups() -> List[dict]:
    def load():
        rows = _get('datagroups/mode=0&type=json', timeout=60.0)
        if not isinstance(rows, list) or not rows:
            raise ExternalError('EVDS veri grubu listesi boş döndü')
        return [r for r in rows if isinstance(r, dict) and r.get('DATAGROUP_CODE')]
    return _groups.get('all', load)


def search(query: str, limit: int = 12) -> List[dict]:
    """Veri grubu adı (TR/EN), kaynak ve birimde tüm terimler geçenler; en
    yeni güncellenen önce."""
    terms = [t for t in _norm(query).split() if len(t) > 1]
    if not terms:
        return []
    out = []
    for g in datagroups():
        text = _norm(' '.join(str(g.get(k) or '') for k in
                              ('DATAGROUP_NAME', 'DATAGROUP_NAME_ENG', 'DATASOURCE', 'BIRIMI', 'DATAGROUP_CODE')))
        if all(t in text for t in terms):
            out.append(g)
    out.sort(key=lambda g: str(g.get('END_DATE') or ''), reverse=True)
    return out[:limit]


def series_list(group_code: str) -> List[dict]:
    if not re.fullmatch(r'[a-z0-9_]{3,40}', group_code or ''):
        raise ExternalError('Geçersiz veri grubu kodu')

    def load():
        rows = _get(f'serieList/type=json&code={group_code}')
        if not isinstance(rows, list):
            raise ExternalError('EVDS seri listesi alınamadı')
        return rows
    return _series.get(group_code, load)


def fetch(series: List[str], start: str, end: str, frequency: Optional[int] = None,
          aggregation: Optional[str] = None, formula: Optional[int] = None) -> List[dict]:
    """Seri değerleri. start/end: GG-AA-YYYY. Dönen satırlar: {Tarih, <seri>…}."""
    codes = [s.strip().upper() for s in series]
    if not codes or len(codes) > MAX_SERIES or not all(_SERIES_RE.match(c) for c in codes):
        raise ExternalError(f'1–{MAX_SERIES} geçerli EVDS seri kodu verin (ör. TP.DK.USD.A)')
    q = f"series={'-'.join(codes)}&startDate={start}&endDate={end}&type=json"
    if frequency:
        q += f'&frequency={int(frequency)}'
    if aggregation:
        q += '&aggregationTypes=' + '-'.join([aggregation] * len(codes))
    if formula is not None:
        q += '&formulas=' + '-'.join([str(int(formula))] * len(codes))
    data = _get(q)
    items = data.get('items') if isinstance(data, dict) else None
    if items is None:
        raise ExternalError('EVDS beklenmeyen yanıt döndürdü')
    return items


def clean_rows(items: List[dict], codes: List[str]) -> List[Dict[str, object]]:
    """EVDS satırlarını sadeleştirir: sütun adları seri koduna döner ('_' → '.',
    formül eki '-N' atılır), 'ND' (veri yok) → None, sayılar float."""
    out = []
    for it in items:
        row: Dict[str, object] = {'tarih': it.get('Tarih')}
        for k, v in it.items():
            if k in ('Tarih', 'UNIXTIME', 'YEARWEEK'):
                continue
            base = k.split('-')[0]
            code = next((c for c in codes if c.replace('.', '_') == base), base)
            try:
                row[code] = None if v in (None, 'ND', '') else round(float(v), 6)
            except (TypeError, ValueError):
                row[code] = None
        out.append(row)
    return out
