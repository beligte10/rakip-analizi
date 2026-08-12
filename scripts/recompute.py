"""
scripts/recompute.py
=====================
Yeniden hesaplama scripti — data/raw'dan parquet'i yükler, baseline JSON'unu
overlay eder, computed.json üretir (bank_data + group_data).

Kullanım:
    python scripts/recompute.py                                    # data/computed.json üret
    python scripts/recompute.py --base data/v29_baseline.json
    python scripts/recompute.py --skip-groups                      # sadece banka değerleri, group_data yazma

Ne zaman çağırılır:
- Yeni measure / grup eklediğinde (bu durumda measures.py + groups.py güncellenir)
- Pipeline bug fix sonrası
- Yeni çeyrek raw verisi geldikten sonra (önce init_data.py, sonra bu)

NOT: Grup aggregate hesabı (build_group_data) admin panelin kullandığı
app.py ile AYNI, TEK fonksiyon — bu script de artık admin endpoint'leriyle
birebir aynı sonucu üretir.
"""
import argparse
import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline import LookupContext, compute_all, build_group_data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-dir', type=Path, default=REPO_ROOT / 'data')
    ap.add_argument('--base', type=Path,
                    help='Baseline JSON (örn. v29 export). Belirtilmezse '
                         'data/computed.json varsa onu kullanır.')
    ap.add_argument('--out', type=Path,
                    help='Çıktı yolu (varsayılan: data/computed.json)')
    ap.add_argument('--skip-groups', action='store_true',
                    help='build_group_data() çağrısını atla, sadece bank_data üret (debug için).')
    ap.add_argument('--bank', help='Sadece tek banka için hesapla (debug)')
    ap.add_argument('--date', help='Sadece tek tarih için hesapla (debug)')
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()

    parquet_path = args.data_dir / 'veriler.parquet'
    catalog_path = args.data_dir / 'catalog.json'
    out_path = args.out or (args.data_dir / 'computed.json')

    if not parquet_path.exists():
        print(f"❌ {parquet_path} yok. Önce scripts/init_data.py çalıştır.")
        sys.exit(1)

    if not catalog_path.exists():
        print(f"❌ {catalog_path} yok.")
        sys.exit(1)

    with open(catalog_path) as f:
        catalog = json.load(f)

    # Baseline yükle
    base_data = {}
    if args.base and args.base.exists():
        print(f"📥 Baseline yükleniyor: {args.base}")
        with open(args.base) as f:
            base = json.load(f)
        base_data = base.get('bank_data', base)
    elif out_path.exists():
        print(f"📥 Mevcut çıktıyı baseline olarak kullan: {out_path}")
        with open(out_path) as f:
            base = json.load(f)
        base_data = base.get('bank_data', base)
    else:
        print("⚠ Baseline yok — sadece raw'dan hesaplanacak (passthrough kalemler boş kalır)")

    # LookupContext kur
    print(f"📊 Parquet yükleniyor: {parquet_path}")
    BANK_TURU = {b['banka_adi']: b['tur'] for b in catalog['banks']}
    ctx = LookupContext.from_parquet(parquet_path, BANK_TURU)

    banks = [args.bank] if args.bank else None
    dates = [args.date] if args.date else None

    print(f"🚀 compute_all çalıştırılıyor...")
    out = compute_all(
        ctx, base_data, catalog,
        banks=banks, dates=dates,
        verbose=args.verbose,
    )

    group_data = {}
    if not args.skip_groups:
        print(f"🚀 build_group_data çalıştırılıyor...")
        group_data = build_group_data(out, catalog, ctx)

    # Çıktı baseline yapısında: {'bank_data': out, 'group_data': ..., 'catalog': catalog['measures']}
    output = {
        'catalog': catalog['measures'],
        'bank_data': out,
        'group_data': group_data,
        'timestamp': __import__('datetime').datetime.now().isoformat(),
    }

    print(f"💾 Yazılıyor: {out_path}")
    with open(out_path, 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ Bitti. {sum(len(v) for v in out.values())} (measure, banka) çifti")


if __name__ == '__main__':
    main()
