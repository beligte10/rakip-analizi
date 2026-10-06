"""pipeline.makro — ölçülerde kullanılan makro seriler (EVDS'den önceden indirilmiş).

- pipeline/tufe_yillik.json: çeyrek sonu TÜFE yıllık % değişimi ({'2026-06-30': 32.109, ...}).
- pipeline/makro_seriler.json: aylık TÜFE endeksi (2025=100) ve USD/TRY ay sonu / aylık ortalama.
Her ikisini scripts/tufe_guncelle.py yeniler; pipeline çalışırken ağa çıkılmaz.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

_YOL = Path(__file__).with_name('tufe_yillik.json')


@lru_cache(maxsize=1)
def _tufe() -> dict:
    try:
        return json.loads(_YOL.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def tufe_yillik(tarih) -> Optional[float]:
    """Çeyrek sonu tarihi için TÜFE yıllık % değişimi (ör. 32.109); yoksa None."""
    return _tufe().get(str(tarih)[:10])


_MAKRO_YOL = Path(__file__).with_name('makro_seriler.json')


@lru_cache(maxsize=1)
def _makro() -> dict:
    try:
        return json.loads(_MAKRO_YOL.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def donem_makro(tarihler) -> dict:
    """Pano dönemleri (çeyrek sonu 'YYYY-MM-DD') için reel/USD çevirme katsayılarının kaynağı
    (2026-10-02, panodaki 'Reel TL' ve 'USD' bazları → computed.json meta.makro).

    Her dönem için:
      tufe      dönem sonu ayının TÜFE endeksi (stok kalemleri: dönem sonu fiyatı)
      tufe_ytd  yılbaşından dönem sonuna aylık endekslerin ortalaması (akım/YtD kalemleri)
      usd       dönem sonu ayının son USD/TRY kuru (stok kalemleri)
      usd_ytd   yılbaşından dönem sonuna aylık ortalama kurların ortalaması (akım/YtD kalemleri)
    Eksik ayı olan değer yazılmaz (istemci o dönemi boş gösterir).
    """
    m = _makro()
    tufe, sonu, ort = m.get('tufe_endeks') or {}, m.get('usd_ay_sonu') or {}, m.get('usd_ay_ort') or {}
    out = {}
    for t in tarihler:
        y, ay = int(str(t)[:4]), int(str(t)[5:7])
        aylar = [f'{y}-{a:02d}' for a in range(1, ay + 1)]
        son = aylar[-1]
        kayit = {}
        if son in tufe:
            kayit['tufe'] = tufe[son]
        if all(a in tufe for a in aylar):
            kayit['tufe_ytd'] = round(sum(tufe[a] for a in aylar) / len(aylar), 6)
        if son in sonu:
            kayit['usd'] = sonu[son]
        if all(a in ort for a in aylar):
            kayit['usd_ytd'] = round(sum(ort[a] for a in aylar) / len(aylar), 6)
        if kayit:
            out[str(t)[:10]] = kayit
    return {'donem': out, 'kaynak': m.get('kaynak') or {}, 'guncelleme': m.get('guncelleme')}
