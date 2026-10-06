#!/usr/bin/env python3
"""BDR'den okunan, BDDK ham verisinde olmayan ölçü değerlerini (Basel III kaldıraç, LCR, serbest karşılık,
TÜFEX tamponu, altın vadesiz tutarı) DATA_DIR/manuel_olculer.json'a ekler / günceller.

Girdi (Excel veya CSV, UZUN biçim — her satır bir banka-dönem değeri):

    olcu                  tarih        banka          deger
    basel_kaldirac_orani  2026-09-30   Kuveyt Türk    6.10
    lcr                   2026-09-30   Kuveyt Türk    198.0
    serbest_karsilik      2026-09-30   Denizbank      8700        (mn TL)

- `olcu`: basel_kaldirac_orani · lcr · lcr_yp · serbest_karsilik · tufex_tamponu · altin_vadesiz_tutar
- `deger` birimi: oranlar yüzde (6,29 = %6,29); tutarlar BDR'deki gibi mn TL (betik TL'ye çevirmez,
  pipeline/manuel_olculer.json'daki `carpan` 1e6 ile çevirir).
- `banka`: katalogdaki banka adı (Kuveyt Türk, QNB, Garanti Bankası, ...).
- Metin alanları (denetçi görüşü vb.) için isteğe bağlı `metin` sayfası/sütunu: alan · tarih · banka · deger.

Kullanım:
    python3 scripts/manuel_olcu_yukle.py dosya.xlsx            # DATA_DIR/manuel_olculer.json'a yazar
    python3 scripts/manuel_olcu_yukle.py dosya.csv --kuru      # yazmadan özetler

Sonra yeniden hesaplayın (python3 scripts/recompute.py) — yoksa yeni değerler panoda görünmez.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from pipeline import manuel_veri  # noqa: E402

BILINEN = {'basel_kaldirac_orani', 'lcr', 'lcr_yp', 'serbest_karsilik', 'tufex_tamponu', 'altin_vadesiz_tutar'}


def _oku(yol: Path):
    if yol.suffix.lower() in ('.xlsx', '.xlsm', '.xls'):
        sayfalar = pd.read_excel(yol, sheet_name=None)
    else:
        sayfalar = {'olcu': pd.read_csv(yol)}
    return sayfalar


def _norm(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={c: str(c).strip().lower() for c in df.columns})
    return df


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('dosya', type=Path)
    ap.add_argument('--kuru', action='store_true', help='Yazma, yalnız özet göster')
    a = ap.parse_args(argv)

    sayfalar = _oku(a.dosya)
    mevcut_yol = Path(os.environ.get('DATA_DIR') or KOK / 'data') / 'manuel_olculer.json'
    try:
        hedef = json.loads(mevcut_yol.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        hedef = {}
    hedef.setdefault('olculer', {})
    hedef.setdefault('metinler', {})
    tohum = manuel_veri.yukle()['olculer']

    sayi = 0
    hatalar = []
    olcu_df = _norm(sayfalar.get('olcu', next(iter(sayfalar.values()))))
    for i, r in olcu_df.iterrows():
        mid, tarih, banka, deger = (str(r.get('olcu', '')).strip(), str(r.get('tarih', ''))[:10],
                                    str(r.get('banka', '')).strip(), r.get('deger'))
        if mid not in BILINEN:
            hatalar.append(f'satır {i + 2}: bilinmeyen ölçü "{mid}"')
            continue
        if pd.isna(deger):
            continue
        carpan = (tohum.get(mid) or {}).get('carpan', 1.0)
        d = hedef['olculer'].setdefault(mid, {'carpan': carpan, 'veri': {}})
        d['veri'].setdefault(tarih, {})[banka] = float(deger)
        sayi += 1
    if 'metin' in sayfalar:
        for i, r in _norm(sayfalar['metin']).iterrows():
            alan, tarih, banka, deger = (str(r.get('alan', '')).strip(), str(r.get('tarih', ''))[:10],
                                         str(r.get('banka', '')).strip(), r.get('deger'))
            if alan and not pd.isna(deger):
                hedef['metinler'].setdefault(alan, {}).setdefault(tarih, {})[banka] = str(deger)
                sayi += 1

    for h in hatalar:
        print('UYARI', h)
    print(f'{sayi} değer okundu.')
    if a.kuru:
        return 0
    mevcut_yol.parent.mkdir(parents=True, exist_ok=True)
    mevcut_yol.write_text(json.dumps(hedef, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'Yazıldı: {mevcut_yol}\nŞimdi: python3 scripts/recompute.py')
    return 1 if hatalar else 0


if __name__ == '__main__':
    sys.exit(main())
