"""
scripts/load_datatable.py
==========================
datatable xlsx (PBI export) → data/computed.json

Kullanım:
    python scripts/load_datatable.py datatable_1.xlsx              # önizleme (yazmaz)
    python scripts/load_datatable.py datatable_1.xlsx --yaz        # computed.json'u güncelle
    python scripts/load_datatable.py datatable_1.xlsx --yaz --out /tmp/test.json

Çeyreklik güncelleme akışı: yeni dönem eklenmiş datatable dosyasını alın,
önce önizleme çalıştırıp raporu okuyun, sorun yoksa `--yaz` ile uygulayın.
Mevcut computed.json otomatik olarak `.bak` olarak yedeklenir.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline.datatable import build_payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('xlsx', type=Path, help='datatable xlsx yolu')
    ap.add_argument('--data-dir', type=Path, default=REPO_ROOT / 'data')
    ap.add_argument('--out', type=Path, help='Çıktı yolu (varsayılan: data/computed.json)')
    ap.add_argument('--yaz', action='store_true',
                    help='Belirtilmezse SADECE rapor basar, hiçbir dosya değişmez.')
    args = ap.parse_args()

    if not args.xlsx.exists():
        print(f"❌ {args.xlsx} bulunamadı"); sys.exit(1)

    catalog_path = args.data_dir / 'catalog.json'
    if not catalog_path.exists():
        print(f"❌ {catalog_path} bulunamadı"); sys.exit(1)
    with open(catalog_path, encoding='utf-8') as f:
        catalog = json.load(f)

    out_path = args.out or (args.data_dir / 'computed.json')

    old_meta = None
    if out_path.exists():
        with open(out_path, encoding='utf-8') as f:
            old_meta = json.load(f).get('meta', {})

    print(f"📖 Okunuyor: {args.xlsx}")
    payload, rapor = build_payload(args.xlsx, catalog, old_meta)

    dates = rapor['dates']
    print(f"\n{'='*64}\nRAPOR\n{'='*64}")
    print(f"  Banka          : {rapor['banks']}")
    print(f"  Dönem          : {len(dates)}  ({dates[0]} → {dates[-1]})")
    print(f"  Eşleşen measure: {rapor['mapped']} / {len(catalog['measures'])}")
    print(f"  Kompozisyon    : {', '.join(rapor['compositions'])}")

    n_bank_cells = sum(len(v) for s in payload['bank_data'].values() for v in s.values())
    n_group_cells = sum(len(v) for s in payload['group_data'].values() for v in s.values())
    print(f"  bank_data      : {n_bank_cells:,} hücre")
    print(f"  group_data     : {n_group_cells:,} hücre")

    if rapor['unmapped']:
        print(f"\n  ⚠ Eşleşmeyen {len(rapor['unmapped'])} measure (boş kalacak):")
        for u in rapor['unmapped']:
            print(f"      {u['id']:<40} {u['sebep']}")

    if rapor.get('yaklasik_agirlikli_rasyolar'):
        yak = rapor['yaklasik_agirlikli_rasyolar']
        print(f"\n  ℹ {len(yak)} rasyonun GRUP değeri YAKLAŞIK ağırlıkla hesaplandı")
        print(f"    (gerçek payda kaynakta yok — örn. RAV; banka bazı değerler TAM doğru):")
        for a in yak:
            print(f"      {a['id']:<34} ağırlık: {a['agirlik']}")

    if rapor['agirliksiz_rasyolar']:
        print(f"\n  ⚠ Grup değeri hesaplanamayan {len(rapor['agirliksiz_rasyolar'])} rasyo")
        print(f"    (payda kalemi bulunamadı — banka bazında değerler NORMAL çalışır):")
        for a in rapor['agirliksiz_rasyolar']:
            print(f"      {a['id']:<40} {a['ad']}")

    if not args.yaz:
        print(f"\n💡 Önizleme modu — hiçbir dosya değiştirilmedi.")
        print(f"   Uygulamak için: --yaz ekleyin")
        return

    if out_path.exists():
        bak = out_path.with_suffix('.json.bak')
        shutil.copy(out_path, bak)
        print(f"\n🗄  Yedek: {bak}")

    tmp = out_path.with_suffix('.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
    tmp.replace(out_path)
    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"✅ Yazıldı: {out_path} ({size_mb:.1f} MB)")


if __name__ == '__main__':
    main()
