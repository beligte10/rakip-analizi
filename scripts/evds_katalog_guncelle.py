#!/usr/bin/env python3
"""EVDS seri kataloğunu çeker ve data/evds_katalog.json'a yazar (asistanın seri araması bunu kullanır).

Kullanım (proje kökünden; EVDS_API_KEY ortamda tanımlı olmalı):
    python3 scripts/evds_katalog_guncelle.py            # JSON
    python3 scripts/evds_katalog_guncelle.py --md       # ayrıca evds_out/ altında kategori başına Markdown + CSV

Kök dizindeki evds_katalog_olustur.py'nin uygulama içi karşılığıdır (aynı hiyerarşi); fark: tüm
veri gruplarını tek istekle (datagroups/mode=0) alır, 4 iş parçacığıyla serileri çeker ve sonucu
asistanın aradığı JSON biçiminde saklar.
"""
import csv
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assistant.external import evds, evds_katalog as K  # noqa: E402


def _slug(t):
    t = (t or 'kategori').lower().translate(str.maketrans('çğıöşüÇĞİÖŞÜ', 'cgiosuCGIOSU'))
    return re.sub(r'[^a-z0-9]+', '_', t).strip('_') or 'kategori'


def md_yaz(kat, out_dir):
    out = Path(out_dir)
    (out / 'katalog').mkdir(parents=True, exist_ok=True)
    gruplar_kat = {}
    for kod, g in kat['gruplar'].items():
        gruplar_kat.setdefault(g['kat'], []).append(kod)
    seri_grup = {}
    for s in kat['seriler']:
        seri_grup.setdefault(s[2], []).append(s)
    tam = ['# EVDS Seri Kataloğu\n', 'Hiyerarşi: Kategori > Veri Grubu > Seri. Seri anlamı için SERIE_NAME esas alınır.\n']
    rows = []
    for cid, kodlar in sorted(gruplar_kat.items()):
        cname = kat['kategoriler'].get(cid, {}).get('ad', f'Kategori {cid}')
        parca = [f'# Kategori {cid}: {cname}\n']
        for kod in kodlar:
            g = kat['gruplar'][kod]
            parca += [f"\n## {g['ad']} (`{kod}`)\n", f"- Frekans: {g['frekans']}", f"- Birim: {g['birim']}", '']
            parca += ['| Seri kodu | Ad | Frekans | Varsayılan toplulaştırma | Başlangıç | Bitiş |', '|---|---|---|---|---|---|']
            for s in seri_grup.get(kod, []):
                parca.append(f"| `{s[0]}` | {s[1].replace('|', '/')} | {s[3]} | {s[4]} | {s[5]} | {s[6]} |")
                rows.append([cid, cname, kod, g['ad'], s[0], s[1], s[3], s[4], s[5], s[6]])
        metin = '\n'.join(parca) + '\n'
        (out / 'katalog' / f'{cid}_{_slug(cname)}.md').write_text(metin, encoding='utf-8')
        tam.append(metin)
    (out / 'evds_katalog.md').write_text('\n'.join(tam), encoding='utf-8')
    with open(out / 'evds_katalog.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['category_id', 'category', 'datagroup_code', 'datagroup', 'serie_code', 'serie_name',
                    'frequency', 'default_aggregation', 'start_date', 'end_date'])
        w.writerows(rows)


def main():
    if not evds.enabled():
        sys.exit('EVDS_API_KEY ortam değişkeni tanımlı değil.')
    son = {'t': 0}

    def ilerleme(i, n):
        if i == n or i - son['t'] >= 50:
            son['t'] = i
            print(f'  {i}/{n} veri grubu', flush=True)
    print('EVDS kataloğu çekiliyor…', flush=True)
    kat = K.olustur(ilerleme)
    yol = K.kaydet(kat)
    print(f"Bitti: {len(kat['kategoriler'])} kategori, {len(kat['gruplar'])} veri grubu, "
          f"{len(kat['seriler'])} seri → {yol}")
    if '--md' in sys.argv:
        md_yaz(kat, os.environ.get('OUT_DIR', 'evds_out'))
        print('Markdown/CSV: evds_out/')


if __name__ == '__main__':
    main()
