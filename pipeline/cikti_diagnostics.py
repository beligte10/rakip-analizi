"""
pipeline.cikti_diagnostics
============================
BDR-Kısayol JSON test yüklemesi için KALEM SEVİYESİNDE tanı raporu.

`pipeline.cikti_compare` sadece "measure X, banka Y'de farklı" diyordu —
bu modül bir adım ileri gidip HER farklı hücre için hangi HAM KALEM
lookup'larının (ctx.bilanco/gelir/mvy/...) başarısız (miss) olduğunu izler,
ayrıca tüm çalışma boyunca hangi ham kalemlerin HİÇ bulunamadığını
(sistematik eksik eşleme) özetler. Amaç: "hata nerede" sorusunu measure
adı seviyesinde değil, doğrudan `pipeline/cikti_ingest.py`'de düzeltilmesi
gereken kalem adı seviyesinde cevaplamak.

Faz 1 ilkesine sadıktır: pipeline.lookup.LookupContext'in KENDİSİ
değişmez — bu modül onu SADECE bu tanı çalışması için alt sınıflayıp
`_lookup`'ı izler (miras alınan davranış birebir aynı, sadece loglama
eklenir). Hiçbir dosyaya yazmaz.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from .lookup import LookupContext
from .measures import MEASURE_FUNCS, BASELINE_PASSTHROUGH


class TracingLookupContext(LookupContext):
    """LookupContext ile birebir aynı davranır, ek olarak her `_lookup`
    çağrısını (tablo, banka, tarih, kalem, pb, bulundu_mu, değer) olarak
    `self.trace`'e kaydeder."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trace: List[dict] = []

    def _lookup(self, table_key: str, banka, tarih, kalem, pb) -> float:
        idx = self._idx.get(table_key)
        hit = False
        value = 0.0
        if idx is not None and len(idx) > 0:
            try:
                v = idx.loc[(banka, self._norm_tarih(tarih), kalem, pb)]
                value = float(v.sum()) if isinstance(v, pd.Series) else float(v)
                hit = True
            except KeyError:
                pass
        self.trace.append({
            'tablo': table_key, 'banka': banka, 'tarih': str(self._norm_tarih(tarih).date()),
            'kalem': kalem, 'pb': pb, 'bulundu': hit,
        })
        return value


def _cell_diff(v_new: Optional[float], v_base: Optional[float],
               tol_abs: float, tol_rel: float) -> str:
    if v_new is None and v_base is None:
        return 'ATLA'
    if v_new is None:
        return 'KAYNAKTA_YOK'
    if v_base is None:
        return 'YENI'
    fark = abs(v_new - v_base)
    tolerans = max(tol_abs, abs(v_base) * tol_rel)
    return 'UYUSUYOR' if fark <= tolerans else 'FARKLI'


def diagnose(
    df: pd.DataFrame,
    banka_turu_map: Dict[str, str],
    catalog_measures: List[dict],
    banks: List[str],
    dates: List[str],
    base_bank_data: Dict[str, Dict[str, Dict[str, Optional[float]]]],
    tol_abs: float = 1.0,
    tol_rel: float = 0.002,
) -> dict:
    """Her (measure, banka, tarih) hücresi için ayrı ayrı hesaplar (compute_all
    ile AYNI sonucu üretir, ama her hücrenin hangi ham kalem lookup'larını
    tetiklediğini de kaydeder). Dönüş: {'satirlar': [...] (TÜMÜ, kapsız),
    'ozet': {...}, 'kalem_kapsama': [...] (hiç bulunamayan kalemler, en çok
    aranan önce)}."""
    ctx = TracingLookupContext(df, banka_turu_map)
    catalog_ids = {m['id'] for m in catalog_measures}

    satirlar: List[dict] = []
    ozet = {'UYUSUYOR': 0, 'FARKLI': 0, 'YENI': 0, 'KAYNAKTA_YOK': 0}
    kalem_arama: Dict[tuple, dict] = {}  # (tablo, kalem, pb) -> {aranan, bulunan}

    for mid, fn in MEASURE_FUNCS.items():
        if mid not in catalog_ids or mid in BASELINE_PASSTHROUGH:
            continue
        base_bank_map = base_bank_data.get(mid, {})
        for bank in banks:
            base_v = base_bank_map.get(bank, {})
            for tarih in dates:
                start = len(ctx.trace)
                try:
                    v_new = fn(ctx, bank, tarih)
                except Exception:
                    v_new = None
                cell_trace = ctx.trace[start:]

                for t in cell_trace:
                    key = (t['tablo'], t['kalem'], t['pb'])
                    rec = kalem_arama.setdefault(key, {'aranan': 0, 'bulunan': 0})
                    rec['aranan'] += 1
                    if t['bulundu']:
                        rec['bulunan'] += 1

                v_base = base_v.get(tarih)
                durum = _cell_diff(v_new, v_base, tol_abs, tol_rel)
                if durum == 'ATLA':
                    continue
                ozet[durum] += 1

                eksik_kalemler = [
                    {'tablo': t['tablo'], 'kalem': t['kalem'], 'pb': t['pb']}
                    for t in cell_trace if not t['bulundu']
                ]
                # aynı kalemi tekrar tekrar listelemesin (bir hücre içinde
                # birden fazla eksik lookup aynı kaleme denk gelebilir)
                seen = set()
                eksik_unique = []
                for e in eksik_kalemler:
                    k = (e['tablo'], e['kalem'], e['pb'])
                    if k not in seen:
                        seen.add(k)
                        eksik_unique.append(e)

                satirlar.append({
                    'measure': mid, 'banka': bank, 'tarih': tarih,
                    'durum': durum,
                    'json_degeri': v_new, 'mevcut_degeri': v_base,
                    'fark': (v_new - v_base) if (v_new is not None and v_base is not None) else None,
                    'fark_yuzde': (abs(v_new - v_base) / abs(v_base) * 100)
                                  if (v_new is not None and v_base is not None and v_base) else None,
                    'eksik_kalemler': eksik_unique,
                })

    satirlar.sort(key=lambda r: (
        {'FARKLI': 0, 'YENI': 1, 'KAYNAKTA_YOK': 2, 'UYUSUYOR': 3}[r['durum']],
        -(r['fark_yuzde'] or 0),
    ))

    kalem_kapsama = [
        {'tablo': tablo, 'kalem': kalem, 'pb': pb,
         'aranan': rec['aranan'], 'bulunan': rec['bulunan'],
         'eksik_oran': (rec['aranan'] - rec['bulunan']) / rec['aranan']}
        for (tablo, kalem, pb), rec in kalem_arama.items()
        if rec['bulunan'] < rec['aranan']
    ]
    kalem_kapsama.sort(key=lambda r: (-r['eksik_oran'], -r['aranan']))

    return {
        'ozet': {
            'uyusan': ozet['UYUSUYOR'], 'farkli': ozet['FARKLI'],
            'yeni': ozet['YENI'], 'kaynakta_yok': ozet['KAYNAKTA_YOK'],
        },
        'satirlar': satirlar,
        'kalem_kapsama': kalem_kapsama,
    }
