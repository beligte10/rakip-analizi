"""
scripts/export_data_snapshot.py
================================
Sunucu göçü/yeni deploy için `data/`'nın GÜNCEL ve DOĞRULANABİLİR bir
anlık görüntüsünü paketler.

NEDEN BU SCRIPT VAR: `data/` klasörü bilinçli olarak git'te değil (canlı veri
her deploy'da ezilmesin diye — bkz. .gitignore). Bu, tek bir dezavantaj
doğuruyor: yeni bir sunucuya taşırken "hangi data/ klasörünü kopyalamalıyım"
sorusu insan hafızasına/elle işe kalıyor. 2026-08-19'da tam bu yüzden bir
sunucuya YANLIŞLIKLA eski (Eylül 2025'te donmuş) bir data/ kopyası taşındı —
GitHub'dan gelen KOD güncel olsa da, birlikte ziplenen data/ klasörü güncel
DEĞİLDİ, kimse fark etmedi çünkü paketin içeriğini doğrulayan bir mekanizma
yoktu.

Bu script iki şeyi garanti eder:
1. Paket HER ZAMAN mevcut `data/computed.json`'dan taze üretilir (elle hangi
   dosyanın "doğru" olduğunu hatırlamaya gerek kalmaz).
2. Paketin içine, içeriği özetleyen bir MANIFEST.txt gömülür (son dönem,
   ölçü/banka sayısı, git commit) — hedef sunucuya geçmeden önce "bu gerçekten
   istediğim veri mi" diye göz ucuyla doğrulanabilir. Yanlış/eski bir paket
   asla sessizce taşınamaz — dosya adının kendisi bile son dönemi taşır.

Kullanım:
    python scripts/export_data_snapshot.py                  # temel paket (~16MB)
    python scripts/export_data_snapshot.py --include-raw     # + tam ham arşiv (~180MB)
    python scripts/export_data_snapshot.py --no-users        # üye hesaplarını hariç tut
    python scripts/export_data_snapshot.py --out /tmp/foo.zip

Çıktı: proje kökünde `rakip-analizi-data_<son-donem>_<üretim-zamanı>.zip`
(farklı bir yol istersen --out).

Hedef sunucuya taşıma adımları için: docs/DATA_MIGRATION.md
"""
import argparse
import json
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / 'data'

# Her zaman dahil edilen "temel" dosyalar — bir sunucunun ÇALIŞMASI için
# yeterli olan minimum set (~16MB). Sırayla: hesaplanmış sonuçlar, ham
# konsolide veri, kompozisyon/ölçü tanımları (runtime groups dahil, seed'den
# farklı olarak admin panelden yapılan grup düzenlemelerini de taşır),
# görünüm ayarları, yükleme geçmişi.
CORE_FILES = [
    'computed.json',
    'veriler.parquet',
    'catalog.json',
    'display_config.json',
    'upload_history.json',
]

# Bilinçli olarak ASLA dahil edilmeyen dosyalar:
#   - computed_backup_*.json / veriler_backup_*.parquet / computed_datatable_kaynakli_yedek.json
#     → eski yedekler; bunları taşımak tam bu script'in önlemeye çalıştığı
#       "yanlışlıkla eski veri taşıma" hatasını YENİDEN üretir.
#   - .session_secret → her deploy kendi oturum anahtarını üretmeli
#     (bkz. app.py::_get_or_create_session_secret); taşınırsa hiçbir zarar
#     vermez ama gereksiz, kalıcı olması gereken bir sır değil sunucu-özel.
#   - data/backups/ → app.py'nin kendi otomatik rebuild-öncesi yedekleri,
#     hedef sunucuda anlamsız (farklı bir geçmişe ait).


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or 'bilinmiyor'
    except Exception:
        return 'bilinmiyor (git yok/hata)'


def _summarize_computed(path: Path) -> dict:
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    bank_data = d.get('bank_data', {})
    measure_count = len(bank_data)
    ta = bank_data.get('toplam_aktifler', {})
    bank_count = len(ta)
    all_dates = sorted({dt for series in ta.values() for dt, v in series.items() if v is not None})
    kt_dates = sorted(dt for dt, v in ta.get('Kuveyt Türk', {}).items() if v is not None)
    latest_full = None
    if all_dates:
        # "Tam" son dönem = en az yarısı+ bankanın raporladığı en yeni tarih
        # (kısmi bir çeyreği "son dönem" diye göstermemek için kaba bir sezgisel).
        for dt in reversed(all_dates):
            n = sum(1 for series in ta.values() if series.get(dt) is not None)
            if n >= max(1, bank_count // 2):
                latest_full = (dt, n, bank_count)
                break
    return {
        'measure_count': measure_count,
        'bank_count': bank_count,
        'kt_period_count': len(kt_dates),
        'kt_latest': kt_dates[-1] if kt_dates else None,
        'overall_latest_date': all_dates[-1] if all_dates else None,
        'latest_full_period': latest_full,
        'timestamp_in_file': d.get('timestamp'),
    }


def _human_size(num_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if num_bytes < 1024:
            return f'{num_bytes:.1f}{unit}'
        num_bytes /= 1024
    return f'{num_bytes:.1f}TB'


def build_manifest(summary: dict, included_files: list[tuple[str, int]], git_commit: str,
                    include_raw: bool, include_users: bool) -> str:
    now = datetime.now().isoformat(timespec='seconds')
    lines = [
        '=' * 62,
        'RAKİP ANALİZİ — VERİ PAKETİ MANİFESTOSU',
        '=' * 62,
        '',
        f'Paket üretim zamanı : {now}',
        f'Kod (git commit)    : {git_commit}',
        '',
        '--- İçerik özeti (data/computed.json) ---',
        f'Ölçü sayısı          : {summary["measure_count"]}',
        f'Banka sayısı         : {summary["bank_count"]}',
        f'Kuveyt Türk dönemi   : {summary["kt_period_count"]} (en son: {summary["kt_latest"]})',
        f'Genel en yeni tarih  : {summary["overall_latest_date"]}',
    ]
    lf = summary.get('latest_full_period')
    if lf:
        lines.append(f'Son "dolu" çeyrek    : {lf[0]}  ({lf[1]}/{lf[2]} banka raporlamış)')
    lines += [
        '',
        '--- Paket içeriği ---',
    ]
    for name, size in included_files:
        lines.append(f'  {name:30s} {_human_size(size):>10s}')
    lines += [
        '',
        f'Ham arşiv (data/raw/) dahil mi : {"EVET" if include_raw else "HAYIR — sadece temel dosyalar"}',
        f'Üye hesapları (users.json) dahil mi : {"EVET (bcrypt hash içerir, güvenli sakla)" if include_users else "HAYIR"}',
        '',
        '=' * 62,
        'DOĞRULAMA: Hedef sunucuya yüklemeden önce yukarıdaki "En son',
        'dönem" ve "dolu çeyrek" satırlarının beklediğin tarihle eşleştiğini',
        'kontrol et. Eşleşmiyorsa bu paketi KULLANMA, önce yerel data/ı',
        'güncelle (rebuild) sonra bu script\'i TEKRAR çalıştır.',
        '=' * 62,
    ]
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out', type=str, default=None, help='Çıktı zip yolu (varsayılan: proje kökünde otomatik adlandırılmış)')
    p.add_argument('--include-raw', action='store_true', help='data/raw/ tam ham arşivini de pakete ekle (~180MB, sadece hedefte tam /admin/rebuild yapılacaksa gerekir)')
    p.add_argument('--no-users', action='store_true', help='data/users.json (üye hesapları) pakete dahil edilmesin')
    args = p.parse_args()

    computed_path = DATA_DIR / 'computed.json'
    if not computed_path.exists():
        print(f'HATA: {computed_path} yok. Önce lokal rebuild çalıştırılmalı.', file=sys.stderr)
        sys.exit(1)

    print('data/computed.json okunuyor ve özetleniyor...')
    summary = _summarize_computed(computed_path)
    git_commit = _git_commit()
    include_users = not args.no_users

    files_to_zip: list[Path] = []
    for name in CORE_FILES:
        fp = DATA_DIR / name
        if fp.exists():
            files_to_zip.append(fp)
        else:
            print(f'  UYARI: {name} bulunamadı, pakete eklenmiyor.')
    if include_users:
        users_fp = DATA_DIR / 'users.json'
        if users_fp.exists():
            files_to_zip.append(users_fp)

    if args.out:
        out_path = Path(args.out)
    else:
        latest = (summary.get('latest_full_period') or (summary.get('overall_latest_date'),))[0]
        latest_tag = (latest or 'bilinmiyor').replace('-', '')
        stamp = datetime.now().strftime('%Y%m%dT%H%M')
        out_path = REPO_ROOT / f'rakip-analizi-data_{latest_tag}_{stamp}.zip'

    included_files: list[tuple[str, int]] = []
    print(f'Paketleniyor → {out_path}')
    # NOT: arşiv içindeki yollar "data/" ÖNEKSİZ (doğrudan computed.json,
    # raw/<banka>/... vb). Böylece hedef sunucuda unzip'i doğrudan data/
    # klasörünün (Docker volume mount kökünün) İÇİNE açmak yeterli olur —
    # ayrıca bir "data/" alt klasörü taşımaya/silmeye gerek kalmaz.
    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for fp in files_to_zip:
            zf.write(fp, arcname=fp.name)
            included_files.append((fp.name, fp.stat().st_size))
            print(f'  + {fp.name}  ({_human_size(fp.stat().st_size)})')

        if args.include_raw:
            raw_dir = DATA_DIR / 'raw'
            raw_files = sorted(raw_dir.rglob('*.xlsx')) if raw_dir.exists() else []
            print(f'  + raw/ ({len(raw_files)} xlsx dosyası)...')
            raw_total = 0
            for rf in raw_files:
                arcname = f'raw/{rf.relative_to(raw_dir)}'
                zf.write(rf, arcname=arcname)
                raw_total += rf.stat().st_size
            included_files.append((f'raw/ ({len(raw_files)} dosya)', raw_total))

        manifest = build_manifest(summary, included_files, git_commit, args.include_raw, include_users)
        zf.writestr('MANIFEST.txt', manifest)

    print()
    print(manifest)
    print()
    print(f'✓ Paket hazır: {out_path}  ({_human_size(out_path.stat().st_size)})')
    print('  Hedef sunucuya taşıma adımları için: docs/DATA_MIGRATION.md')


if __name__ == '__main__':
    main()
