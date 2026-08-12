"""
scripts/init_data.py
=====================
İlk kurulum: raw xlsx ZIP'ten parquet ve computed.json üret.

Kullanım:
    python scripts/init_data.py --raw-zip /path/to/Veriler.zip
    python scripts/init_data.py --raw-dir /path/to/Veriler/  # zaten extract edilmişse

İşlem:
1) ZIP varsa data/raw/'a extract eder
2) Banka klasör adlarını decode eder (#UXXXX → Türkçe)
3) Tüm xlsx'leri yükleyip data/veriler.parquet üretir
4) compute_all() ile data/computed.json üretir
"""
import argparse
import re
import sys
import shutil
import zipfile
from pathlib import Path

# Repo root'u sys.path'e ekle
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline.ingest import rebuild_parquet
from pipeline.compute import compute_all
import json


def decode_unicode_filename(name: str) -> str:
    """`Kuveyt T#U00fcrk` → `Kuveyt Türk`"""
    return re.sub(r'#U([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), name)


def normalize_bank_dirs(raw_dir: Path):
    """Banka klasörlerini #UXXXX kodlarından arınmış hale getir."""
    for d in list(raw_dir.iterdir()):
        if not d.is_dir():
            continue
        decoded = decode_unicode_filename(d.name)
        if decoded != d.name:
            target = raw_dir / decoded
            if target.exists():
                # Mevcut klasöre merge
                for f in d.iterdir():
                    f.rename(target / f.name)
                d.rmdir()
            else:
                d.rename(target)
            print(f"  rename: {d.name} → {decoded}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw-zip', type=Path, help='Veriler.zip yolu')
    ap.add_argument('--raw-dir', type=Path, help='Önceden extract edilmiş Veriler klasörü')
    ap.add_argument('--data-dir', type=Path, default=REPO_ROOT / 'data',
                     help='Veri klasörü (default: repo/data)')
    ap.add_argument('--base-json', type=Path,
                     help='Mevcut computed.json baseline (Faz 1 için v29\'dan)')
    args = ap.parse_args()

    raw_target = args.data_dir / 'raw'
    raw_target.mkdir(parents=True, exist_ok=True)

    # ZIP'ten extract
    if args.raw_zip:
        print(f"\n📦 ZIP extract ediliyor: {args.raw_zip}")
        with zipfile.ZipFile(args.raw_zip) as zf:
            # ZIP içinde Veriler/<banka>/ yapısı bekleniyor
            zf.extractall(args.data_dir / '_zip_extract')
        # Veriler/ alt klasörünü raw'a taşı
        zip_root = args.data_dir / '_zip_extract' / 'Veriler'
        if not zip_root.exists():
            zip_root = args.data_dir / '_zip_extract'
        for d in zip_root.iterdir():
            if d.is_dir():
                target = raw_target / d.name
                if target.exists():
                    shutil.rmtree(target)
                shutil.move(str(d), str(target))
        shutil.rmtree(args.data_dir / '_zip_extract')
    elif args.raw_dir:
        print(f"\n📂 Raw klasör kullanılıyor: {args.raw_dir}")
        for d in args.raw_dir.iterdir():
            if d.is_dir():
                target = raw_target / d.name
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(d, target)

    # Klasör adlarını decode et
    print(f"\n🔤 Klasör adları decode ediliyor")
    normalize_bank_dirs(raw_target)

    # Catalog'u oku — banka türü map'i için
    catalog_path = args.data_dir / 'catalog.json'
    with open(catalog_path) as f:
        catalog_doc = json.load(f)
    bank_turu_map = {b['banka_adi']: b['tur'] for b in catalog_doc['banks']}

    # Parquet üret
    print(f"\n🛠  Parquet inşa ediliyor...")
    parquet_path = args.data_dir / 'veriler.parquet'
    rebuild_parquet(raw_target, parquet_path, bank_turu_map=bank_turu_map)

    # computed.json üret
    print(f"\n🧮 Measure'lar hesaplanıyor...")
    base = None
    if args.base_json:
        with open(args.base_json) as f:
            base = json.load(f)
    out_path = args.data_dir / 'computed.json'
    compute_all(parquet_path, catalog_path, out_path, base_data=base)

    print(f"\n🎉 İlk kurulum tamam.")
    print(f"   Sıradaki: app.py (Faz 2'de) ile dashboard'u serve et.")


if __name__ == '__main__':
    main()
