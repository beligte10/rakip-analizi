"""
scripts/embed_logos.py
=======================
frontend/logos/ klasöründeki banka logolarını base64 data URI olarak
frontend/index_v30.html içindeki `BANK_LOGOS` sözlüğüne gömer.

Neden gömüyoruz: HTML'in tek dosya / offline çalışır kalması için. Harici
URL kullanılsaydı her açılışta banka sunucularına istek gider, internet
olmadan logolar kırılırdı.

Kullanım:
    python scripts/embed_logos.py            # önizleme — dosya değişmez
    python scripts/embed_logos.py --yaz      # HTML'i güncelle (.bak yedeği alır)

Dosya adlandırma: logo dosyasının adı catalog.json'daki banka adıyla
BİREBİR aynı olmalı (Türkçe karakterler dahil).

    frontend/logos/Kuveyt Türk.svg
    frontend/logos/QNB Finansbank.png
    frontend/logos/Denizbank.svg
    frontend/logos/TEB.png
    frontend/logos/Vakıf Katılım.svg
    frontend/logos/Ziraat Katılım.png

Desteklenen: .svg .png .jpg .jpeg .webp
SVG tercih edilir (küçük, her ölçekte net). Logosu olmayan banka
otomatik olarak renkli baş-harf rozetine düşer — hata vermez.
"""
import argparse
import base64
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOGO_DIR = REPO_ROOT / 'frontend' / 'logos'
HTML_PATH = REPO_ROOT / 'frontend' / 'index_v30.html'

MIME = {
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.webp': 'image/webp',
}

# Tek logo için uyarı eşiği — gömülen her byte HTML boyutuna eklenir
WARN_KB = 60


def rasterize(src: Path, px: int = 64) -> bytes | None:
    """
    Büyük SVG'yi `px`×`px` şeffaf PNG'ye çevirir (macOS `qlmanage`).

    Neden: logolar arayüzde 18×18 px rozet olarak gösteriliyor. Kurumsal
    kimlik SVG'leri 600-1400 path içerebiliyor (QNB 447 KB) — bu detayın
    hiçbiri 18 px'de görünmez ama HTML'i şişirir. 64 px PNG ~3-6 KB.

    macOS'a özgüdür; qlmanage yoksa veya render başarısızsa None döner ve
    çağıran taraf orijinal dosyayı gömer (bozulma olmaz).
    """
    if not shutil.which('qlmanage'):
        return None
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        try:
            subprocess.run(
                ['qlmanage', '-t', '-s', str(px), '-o', td, str(src)],
                capture_output=True, timeout=30, check=False,
            )
        except (subprocess.SubprocessError, OSError):
            return None
        out = Path(td) / f'{src.name}.png'
        return out.read_bytes() if out.exists() else None


def nfc(s: str) -> str:
    """Unicode normalize (NFC).

    macOS dosya sistemi dosya adlarını NFD (ayrışık) biçimde tutar: 'ü'
    karakteri 'u' + birleşen umlaut (U+0308) olarak iki kod noktasıdır.
    catalog.json ise NFC (birleşik) kullanır. Normalize etmeden karşılaştırınca
    'Kuveyt Türk' == 'Kuveyt Türk' FALSE döner ve logo sessizce atlanır.
    """
    return unicodedata.normalize('NFC', s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--yaz', action='store_true',
                    help='Belirtilmezse sadece rapor basar, HTML değişmez.')
    ap.add_argument('--logo-dir', type=Path, default=LOGO_DIR)
    ap.add_argument('--html', type=Path, default=HTML_PATH)
    ap.add_argument('--optimize', action='store_true',
                    help=f'{WARN_KB} KB üstü SVG\'leri 64px PNG\'ye çevirip öyle göm '
                         f'(orijinal dosyalar KORUNUR). macOS qlmanage gerekir.')
    ap.add_argument('--px', type=int, default=64,
                    help='--optimize ile üretilecek PNG kenar uzunluğu (varsayılan 64)')
    args = ap.parse_args()

    if not args.logo_dir.exists():
        print(f"❌ {args.logo_dir} yok. Klasörü oluşturup logo dosyalarını koyun.")
        sys.exit(1)
    if not args.html.exists():
        print(f"❌ {args.html} bulunamadı"); sys.exit(1)

    # catalog'daki banka adları — dosya adı doğrulaması için
    catalog_path = REPO_ROOT / 'data' / 'catalog.json'
    valid_banks = set()
    if catalog_path.exists():
        with open(catalog_path, encoding='utf-8') as f:
            valid_banks = {nfc(b['banka_adi']) for b in json.load(f)['banks']}

    logos, uyarilar = {}, []
    for p in sorted(args.logo_dir.iterdir()):
        if p.name.startswith('.') or p.suffix.lower() not in MIME:
            continue
        banka = nfc(p.stem)   # macOS NFD → NFC (bkz. nfc() docstring)
        data = p.read_bytes()
        kb = len(data) / 1024
        if valid_banks and banka not in valid_banks:
            uyarilar.append(f"'{p.name}' → '{banka}' catalog.json'da YOK, atlandı "
                            f"(dosya adı banka adıyla birebir aynı olmalı)")
            continue

        mime = MIME[p.suffix.lower()]
        note = ''
        if args.optimize and kb > WARN_KB and p.suffix.lower() == '.svg':
            png = rasterize(p, args.px)
            if png:
                note = f'  → {args.px}px PNG  ({len(png)/1024:.1f} KB)'
                data, mime = png, 'image/png'
            else:
                uyarilar.append(f"'{p.name}' küçültülemedi (qlmanage yok/başarısız), "
                                f"orijinal gömüldü")
        elif kb > WARN_KB:
            uyarilar.append(f"'{p.name}' {kb:.0f} KB — büyük; --optimize ile küçültebilirsiniz")

        b64 = base64.b64encode(data).decode('ascii')
        logos[banka] = f"data:{mime};base64,{b64}"
        print(f"  ✓ {banka:<24} {p.suffix:<5} {kb:>7.1f} KB{note}")

    if not logos:
        print(f"\n⚠ {args.logo_dir} içinde geçerli logo dosyası bulunamadı.")
        print(f"  Desteklenen: {', '.join(MIME)}")
        print(f"  Dosya adı catalog.json'daki banka adıyla aynı olmalı, örn:")
        print(f"     {args.logo_dir}/Kuveyt Türk.svg")
        if not args.yaz:
            sys.exit(0)
        # --yaz açıkça verildiyse boş sözlük yazılır: klasörden logo silmek
        # HTML'den de kaldırsın (aksi halde eski logolar gömülü kalırdı).
        print("  → --yaz verildiği için BANK_LOGOS temizlenecek.")

    for u in uyarilar:
        print(f"  ⚠ {u}")

    html = args.html.read_text(encoding='utf-8')
    pattern = re.compile(r'^(\s*)var BANK_LOGOS = .*?;\s*$', re.MULTILINE | re.DOTALL)
    m = pattern.search(html)
    if not m:
        print("\n❌ HTML içinde 'var BANK_LOGOS = ...;' satırı bulunamadı.")
        sys.exit(1)

    indent = m.group(1)
    yeni = f"{indent}var BANK_LOGOS = {json.dumps(logos, ensure_ascii=False)};"
    yeni_html = html[:m.start()] + yeni + html[m.end():]

    eski_kb = len(html.encode()) / 1024
    yeni_kb = len(yeni_html.encode()) / 1024
    print(f"\n  {len(logos)} logo gömülecek — HTML {eski_kb:.0f} KB → {yeni_kb:.0f} KB")

    if not args.yaz:
        print("\n💡 Önizleme modu — hiçbir dosya değiştirilmedi. Uygulamak için: --yaz")
        return

    bak = args.html.with_suffix('.html.bak')
    shutil.copy(args.html, bak)
    args.html.write_text(yeni_html, encoding='utf-8')
    print(f"🗄  Yedek : {bak}")
    print(f"✅ Yazıldı: {args.html}")
    print("\n   Tarayıcıda hard refresh yapın (Cmd+Shift+R).")


if __name__ == '__main__':
    main()
