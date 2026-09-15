"""
pipeline.cikti_compare
========================
BDR-Kısayol JSON'undan hesaplanan (measure, banka, tarih) hücrelerini,
`data/computed.json`'daki mevcut (Rasyonet/xlsx kaynaklı) değerlerle
karşılaştırır. Faz 1 — destekleyici/test: bu modül hiçbir dosyaya yazmaz,
sadece bir rapor sözlüğü üretir.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .measures import BASELINE_PASSTHROUGH


def compare_against_baseline(
    new_data: Dict[str, Dict[str, Dict[str, Optional[float]]]],
    base_data: Dict[str, Dict[str, Dict[str, Optional[float]]]],
    banks: List[str],
    dates: List[str],
    tol_abs: float = 1.0,
    tol_rel: float = 0.002,
    max_detail: int = 200,
) -> dict:
    """`new_data`'nın SADECE `banks`/`dates` kapsadığı hücreleri değerlendirir.
    BASELINE_PASSTHROUGH ölçüleri hiç karşılaştırmaya girmez (bu JSON'dan
    gelmeleri mümkün değil). Sonuç: {'ozet': {...}, 'farkli': [...]}."""
    uyusan = farkli = yeni = eksik = 0
    farkli_detay: List[dict] = []

    for mid, bank_map in new_data.items():
        if mid in BASELINE_PASSTHROUGH:
            continue
        base_bank_map = base_data.get(mid, {})
        for bank in banks:
            new_v = bank_map.get(bank, {})
            base_v = base_bank_map.get(bank, {})
            for tarih in dates:
                v_new = new_v.get(tarih)
                v_base = base_v.get(tarih)
                if v_new is None and v_base is None:
                    continue
                if v_new is None:
                    eksik += 1
                    continue
                if v_base is None:
                    yeni += 1
                    continue
                fark = abs(v_new - v_base)
                tolerans = max(tol_abs, abs(v_base) * tol_rel)
                if fark <= tolerans:
                    uyusan += 1
                else:
                    farkli += 1
                    farkli_detay.append({
                        'measure': mid, 'banka': bank, 'tarih': tarih,
                        'json_degeri': v_new, 'mevcut_degeri': v_base,
                        'fark': v_new - v_base,
                        'fark_yuzde': (fark / abs(v_base) * 100) if v_base else None,
                    })

    farkli_detay.sort(key=lambda r: abs(r['fark_yuzde'] or 0), reverse=True)

    return {
        'ozet': {'uyusan': uyusan, 'farkli': farkli, 'yeni': yeni, 'kaynakta_yok': eksik},
        'farkli': farkli_detay[:max_detail],
        'farkli_toplam': farkli,
    }
