"""Makro serileri EVDS'den çekip pipeline/ altına yazar (EVDS_API_KEY ortamda):

    python3 scripts/tufe_guncelle.py

1. pipeline/tufe_yillik.json — çeyrek sonu TÜFE yıllık % değişimi (Reel OPEX büyümesi ölçüsü).
   Önce güncel baz serisi (2025=100), eksik aylar için eski seri (2003=100).
2. pipeline/makro_seriler.json — aylık TÜFE endeks düzeyi (2025=100) ile USD/TRY döviz alış
   kurunun ay sonu ve aylık ortalaması. Panodaki "Reel TL" ve "USD" bazları bunları kullanır
   (pipeline/makro.donem_makro → computed.json meta.makro).

Yeni çeyrek verisi geldiğinde yeniden çalıştırın; ardından pano verisi yeniden hesaplanmalı
(admin → yeniden hesapla) ki meta.makro güncellensin.
"""
import calendar
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from assistant.external import evds  # noqa: E402

SERILER = ['TP.TUKFIY2025.GENEL', 'TP.FG.J0']   # öncelik sırasıyla


def main() -> None:
    bugun = date.today()
    out = {}
    for kod in reversed(SERILER):          # önce eski seri, sonra yeni seri üstüne yazar
        try:
            items = evds.fetch([kod], '01-01-2012', f'01-{bugun.month:02d}-{bugun.year}', formula=3)
        except Exception as e:             # noqa: BLE001
            print(f'{kod}: alınamadı ({e})')
            continue
        for r in items:
            y, _, m = str(r.get('Tarih', '')).partition('-')
            v = next((x for k, x in r.items() if k not in ('Tarih', 'UNIXTIME')), None)
            if not (y.isdigit() and m.isdigit() and int(m) % 3 == 0) or v in (None, '', 'ND'):
                continue
            yil, ay = int(y), int(m)
            out[f'{yil}-{ay:02d}-{calendar.monthrange(yil, ay)[1]:02d}'] = round(float(v), 4)
    if not out:
        sys.exit('Hiç veri alınamadı')
    (ROOT / 'pipeline' / 'tufe_yillik.json').write_text(
        json.dumps(dict(sorted(out.items())), ensure_ascii=False, indent=1), encoding='utf-8')
    print(len(out), 'çeyrek yazıldı; son:', max(out), out[max(out)])


def _aylik(kod, bas, bit, frekans=None, toplama=None):
    items = evds.fetch([kod], bas, bit, frequency=frekans, aggregation=toplama, formula=0)
    out = {}
    for r in items:
        y, _, m = str(r.get('Tarih', '')).partition('-')
        v = next((x for k, x in r.items() if k not in ('Tarih', 'UNIXTIME')), None)
        if y.isdigit() and m.isdigit() and v not in (None, '', 'ND'):
            out[f'{int(y)}-{int(m):02d}'] = round(float(v), 6)
    return out


def makro_seriler() -> None:
    bugun = date.today()
    bit = f'{calendar.monthrange(bugun.year, bugun.month)[1]:02d}-{bugun.month:02d}-{bugun.year}'
    veri = {
        'tufe_endeks': _aylik('TP.TUKFIY2025.GENEL', '01-01-2012', bit),
        'usd_ay_sonu': _aylik('TP.DK.USD.A.YTL', '01-01-2012', bit, frekans=5, toplama='last'),
        'usd_ay_ort': _aylik('TP.DK.USD.A.YTL', '01-01-2012', bit, frekans=5, toplama='avg'),
        'kaynak': {'tufe_endeks': 'TCMB EVDS TP.TUKFIY2025.GENEL (2025=100)',
                   'usd': 'TCMB EVDS TP.DK.USD.A.YTL (döviz alış; aylık son / ortalama)'},
        'guncelleme': bugun.isoformat(),
    }
    if not veri['tufe_endeks'] or not veri['usd_ay_sonu']:
        sys.exit('Makro seriler alınamadı')
    (ROOT / 'pipeline' / 'makro_seriler.json').write_text(
        json.dumps(veri, ensure_ascii=False, indent=1), encoding='utf-8')
    print('makro_seriler.json: TÜFE', max(veri['tufe_endeks']), '· USD', max(veri['usd_ay_sonu']))


if __name__ == '__main__':
    main()
    makro_seriler()
