"""
pipeline.manuel_veri
=====================
BDDK ham verisinde (veriler.parquet) bulunmayan, yalnız bankaların bağımsız denetim raporlarından
(BDR) okunabilen değerler için elle yüklenen ölçü verisi: Basel III kaldıraç oranı, LCR, serbest
karşılık bakiyesi, TÜFEX tamponu.

Dosya biçimi (`pipeline/manuel_olculer.json`; aynı yapıdaki `DATA_DIR/manuel_olculer.json` ÜSTÜNE yazar):

    {"olculer": {"<ölçü id>": {"carpan": 1.0,
                               "veri": {"2026-06-30": {"Kuveyt Türk": 6.29, ...}}}},
     "metinler": {"<alan>": {"2026-06-30": {"Kuveyt Türk": "Temiz", ...}}}}

`carpan`: dosyadaki değerin sistemin birimine çevrilmesi (BDR'deki mn TL → TL için 1e6).
Yeni dönem eklemek için `scripts/manuel_olcu_yukle.py` (Excel/JSON → bu dosya) kullanılır; sonra yeniden
hesaplama gerekir. Sayısal olmayan alanlar (denetçi görüşü, TÜFEX kaynağı) `metinler` altında tutulur:
ölçü olarak gösterilmez, asistanın bilgi kaynağıdır.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Dict, Optional

_SEED = Path(__file__).with_name('manuel_olculer.json')
_kilit = threading.Lock()
_onbellek: Dict[str, object] = {'imza': None, 'veri': {'olculer': {}, 'metinler': {}}}


def _data_dosyasi() -> Path:
    kok = Path(os.environ.get('DATA_DIR') or Path(__file__).resolve().parent.parent / 'data')
    return kok / 'manuel_olculer.json'


def _oku(yol: Path) -> dict:
    try:
        return json.loads(yol.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def _imza(yollar) -> tuple:
    out = []
    for y in yollar:
        try:
            s = y.stat()
            out.append((str(y), s.st_mtime_ns, s.st_size))
        except OSError:
            out.append((str(y), None, None))
    return tuple(out)


def _birlestir(taban: dict, ust: dict) -> dict:
    """Ölçü bazında, dönem bazında birleştirir (üstteki dosya aynı banka-dönem değerini ezer)."""
    sonuc = {'olculer': {}, 'metinler': {}}
    for kaynak in (taban, ust):
        for mid, tanim in (kaynak.get('olculer') or {}).items():
            hedef = sonuc['olculer'].setdefault(mid, {'carpan': tanim.get('carpan', 1.0), 'veri': {}})
            hedef['carpan'] = tanim.get('carpan', hedef['carpan'])
            for tarih, bankalar in (tanim.get('veri') or {}).items():
                hedef['veri'].setdefault(tarih, {}).update(bankalar)
        for alan, donemler in (kaynak.get('metinler') or {}).items():
            hedef = sonuc['metinler'].setdefault(alan, {})
            for tarih, bankalar in donemler.items():
                hedef.setdefault(tarih, {}).update(bankalar)
    return sonuc


def yukle() -> dict:
    """Birleşik manuel veri (dosyalar değişince tazelenir)."""
    yollar = (_SEED, _data_dosyasi())
    imza = _imza(yollar)
    with _kilit:
        if _onbellek['imza'] != imza:
            _onbellek['veri'] = _birlestir(_oku(yollar[0]), _oku(yollar[1]))
            _onbellek['imza'] = imza
        return _onbellek['veri']   # type: ignore[return-value]


def deger(olcu_id: str, banka: str, tarih) -> Optional[float]:
    """Banka-dönem değeri (sistem birimi); veri yoksa None."""
    tanim = yukle()['olculer'].get(olcu_id)
    if not tanim:
        return None
    v = (tanim['veri'].get(str(tarih)[:10]) or {}).get(banka)
    return None if v is None else float(v) * float(tanim.get('carpan', 1.0))


def metin(alan: str, banka: str, tarih) -> Optional[str]:
    return ((yukle()['metinler'].get(alan) or {}).get(str(tarih)[:10]) or {}).get(banka)


def olcu_idleri() -> list:
    return sorted(yukle()['olculer'])
