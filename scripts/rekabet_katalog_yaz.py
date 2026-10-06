#!/usr/bin/env python3
"""catalog.seed.json'a pipeline/rekabet_olculer.KATALOG kayıtlarını ekler / günceller (idempotent).

Mevcut (Rekabet Analizi dışı) ölçülere dokunmaz; KATALOG ölçüleri her çalıştırmada silinip sırasıyla sona yeniden yazılır (seçicideki sıra böyle belirlenir).
Kullanım: python3 scripts/rekabet_katalog_yaz.py
"""
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from pipeline.rekabet_olculer import KATALOG  # noqa: E402

yol = KOK / 'catalog.seed.json'
kat = json.loads(yol.read_text(encoding='utf-8'))
ids = {k['id'] for k in KATALOG}
eklenen = sum(1 for m in kat['measures'] if m['id'] not in ids and False)
var = {m['id'] for m in kat['measures']} & ids
kat['measures'] = [m for m in kat['measures'] if m['id'] not in ids] + KATALOG   # KATALOG sırasıyla, sona
eklenen, guncellenen = len(ids) - len(var), len(var)
yol.write_text(json.dumps(kat, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'{eklenen} ölçü eklendi, {guncellenen} güncellendi → toplam {len(kat["measures"])}')
