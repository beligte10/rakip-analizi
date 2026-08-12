"""
pipeline.compute
=================
Orkestratör. base_data (örn. v29 baseline JSON'undaki bank_data) ile başlar,
MEASURE_FUNCS'taki her measure'ı raw'dan hesaplayıp override eder.
BASELINE_PASSTHROUGH'taki measure'lar dokunulmadan kalır (SYR gibi raw'da
olmayan veya v29 PBI hesabıyla raw'dan tam eşleşmeyen kalemler).

Bu fonksiyon SADECE banka-level `bank_data`'yı üretir. Grup (Kuveyt Türk,
Mevduat Bankaları, Rakip Bankalar, Katılım Bankaları, KT Hariç Katılım
Bankaları) aggregate'leri ayrı, tek bir yerde tanımlı: `pipeline.groups.
build_group_data()`. Çağıran taraf (app.py, scripts/recompute.py) bu
fonksiyonu `compute_all()`'dan sonra ayrıca çağırmalı.
"""
from __future__ import annotations
import copy
from typing import Dict, List, Optional
import pandas as pd

from .lookup import LookupContext
from .measures import MEASURE_FUNCS, BASELINE_PASSTHROUGH


def _date_str(t) -> str:
    """Tarih → 'YYYY-MM-DD' (bank_data dict key formatı)."""
    if isinstance(t, str):
        return t
    return pd.Timestamp(t).strftime('%Y-%m-%d')


def compute_all(
    ctx: LookupContext,
    base_data: Dict[str, Dict[str, Dict[str, Optional[float]]]],
    catalog: List[dict],
    *,
    banks: Optional[List[str]] = None,
    dates: Optional[List[str]] = None,
    verbose: bool = False,
) -> Dict[str, Dict[str, Dict[str, Optional[float]]]]:
    """
    Pipeline'ı çalıştır — SADECE banka-level bank_data üretir (grup yok).

    Args:
      ctx: LookupContext (raw parquet'e indekslenmiş)
      base_data: v29 baseline'dan bank_data (measure_id → banka → tarih → value)
      catalog: catalog.json'daki measures listesi (sadece IDs için)
      banks: hesaplanacak bankalar (None ise base_data'daki tüm bankalar)
      dates: hesaplanacak tarihler (None ise her banka için kendi tarihleri)
      verbose: True ise her measure için sayım yazdırır

    Returns:
      Yeni bank_data (deep copy) — MEASURE_FUNCS'taki her measure raw'dan
      override edilmiş, BASELINE_PASSTHROUGH'takiler base_data'dan korunmuş.
      Grup aggregate'leri için ayrıca `pipeline.groups.build_group_data()`
      çağırın.
    """
    out = copy.deepcopy(base_data)

    # Catalog hem dict ({'measures':[...],'banks':[...]}) hem list ([{id,..},...]) olabilir
    if isinstance(catalog, dict):
        measures_list = catalog.get('measures', [])
    else:
        measures_list = catalog

    # Banka listesi
    if banks is None:
        banks = sorted({b for m in out.values() for b in m.keys()})

    # Catalog'daki tüm measure ID'leri
    catalog_ids = {c['id'] for c in measures_list}
    raw_ids = set(MEASURE_FUNCS.keys())
    passthrough_ids = BASELINE_PASSTHROUGH

    # Sanity check: raw + passthrough = catalog tam kapsamı (mümkünse)
    missing = catalog_ids - raw_ids - passthrough_ids
    if missing and verbose:
        print(f"  ⚠ Catalog'daki bu measure'lar registry'de yok: {missing}")

    if verbose:
        print(f"  → {len(raw_ids)} raw measure, {len(passthrough_ids)} passthrough")
        print(f"  → {len(banks)} banka")

    # Group bankalarını dışlayacağız (Sektör, Katılım, vb.) — sadece gerçek bankalar için raw hesabı
    GROUP_NAMES = {'Sektör', 'Mevduat Sektörü', 'Katılım'}
    real_banks = [b for b in banks if b not in GROUP_NAMES]

    overrides = 0
    for mid, fn in MEASURE_FUNCS.items():
        if mid not in catalog_ids:
            continue  # registry'de var ama catalog'da yok
        out.setdefault(mid, {})
        for banka in real_banks:
            # Bu banka için tarihler
            if dates is not None:
                bank_dates = dates
            else:
                bank_dates = list(out.get(mid, {}).get(banka, {}).keys())
                # Eğer baseline'da yoksa bu banka için ctx tarihlerini kullan
                if not bank_dates:
                    bank_dates = [d.strftime('%Y-%m-%d') for d in ctx.get_dates(banka)]

            out[mid].setdefault(banka, {})
            for d in bank_dates:
                try:
                    v = fn(ctx, banka, d)
                except Exception as e:
                    if verbose:
                        print(f"    EXC {mid} {banka} {d}: {e}")
                    v = None
                out[mid][banka][d] = v
                overrides += 1

    if verbose:
        print(f"  → {overrides} (banka × tarih × measure) override yapıldı")

    return out
