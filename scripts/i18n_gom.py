"""İngilizce sözlükleri sayfalara gömer (2026-10-02).

Pano (frontend/index_v30.html):
    frontend/i18n/arayuz_en.json (arayüz metinleri) ve frontend/i18n/olcu_en.json (ölçü / kategori /
    kompozisyon / bileşen adları) işaretli yerlere yazılır:
        var I18N_ARAYUZ = /*I18N_ARAYUZ*/{...}/*/I18N_ARAYUZ*/;
        var I18N_OLCU = /*I18N_OLCU*/{...}/*/I18N_OLCU*/;

Giriş, başvuru ve admin sayfaları (login.html, signup.html, admin.html):
    <script>/*I18N_SAYFA*/ ... /*/I18N_SAYFA*/</script> arasına sayfanın sözlüğü (+ sunucu mesajları),
    banka adları (catalog.seed.json, çeviride korunur) ve frontend/i18n/sayfa_cevir.js motoru yazılır.

Sözlük ya da motor değiştiğinde çalıştırın:  python3 scripts/i18n_gom.py
--kontrol: dosyalar güncel değilse 1 ile çıkar (test / CI için).
"""
import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
I18N = KOK / 'frontend' / 'i18n'
HTML = KOK / 'frontend' / 'index_v30.html'
KAYNAK = {
    'I18N_ARAYUZ': I18N / 'arayuz_en.json',
    'I18N_OLCU': I18N / 'olcu_en.json',
}
# sayfa → sözlük dosyaları (sonraki dosya öncekini ezer)
SAYFALAR = {
    KOK / 'frontend' / 'login.html': ['sunucu_en.json', 'giris_en.json'],
    KOK / 'frontend' / 'signup.html': ['sunucu_en.json', 'giris_en.json'],
    KOK / 'frontend' / 'admin.html': ['sunucu_en.json', 'admin_en.json'],
}
MOTOR = I18N / 'sayfa_cevir.js'
SAYFA_DESEN = re.compile(r'/\*I18N_SAYFA\*/.*?/\*/I18N_SAYFA\*/', re.S)


def _js(obj) -> str:
    # </script> kapanışını ve satır ayraçlarını kaçır; HTML içinde güvenli tek satır JSON
    t = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    return t.replace('</', '<\\/').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def gomulu(metin: str) -> str:
    """index_v30.html: I18N_ARAYUZ / I18N_OLCU işaretlerini doldurur."""
    for ad, yol in KAYNAK.items():
        veri = json.loads(yol.read_text(encoding='utf-8'))
        desen = re.compile(r'/\*%s\*/.*?/\*/%s\*/' % (ad, ad), re.S)
        if not desen.search(metin):
            raise SystemExit('işaret bulunamadı: %s' % ad)
        yeni = '/*%s*/%s/*/%s*/' % (ad, _js(veri), ad)
        metin = desen.sub(lambda _m: yeni, metin, count=1)
    return metin


def sayfa_sozlugu(dosyalar) -> dict:
    sozluk = {}
    for ad in dosyalar:
        sozluk.update(json.loads((I18N / ad).read_text(encoding='utf-8')))
    return sozluk


def banka_adlari() -> list:
    seed = json.loads((KOK / 'catalog.seed.json').read_text(encoding='utf-8'))
    return sorted({b['banka_adi'] for b in seed.get('banks', []) if b.get('banka_adi')})


def sayfa_gomulu(metin: str, dosyalar) -> str:
    """login/signup/admin: I18N_SAYFA işaretine sözlük + banka adları + motor yazar."""
    if not SAYFA_DESEN.search(metin):
        raise SystemExit('işaret bulunamadı: I18N_SAYFA')
    motor = MOTOR.read_text(encoding='utf-8').replace('</', '<\\/')
    icerik = ('window.KT_I18N = %s;\n%s'
              % (_js({'sozluk': sayfa_sozlugu(dosyalar), 'bankalar': banka_adlari()}), motor))
    yeni = '/*I18N_SAYFA*/\n%s/*/I18N_SAYFA*/' % icerik
    return SAYFA_DESEN.sub(lambda _m: yeni, metin, count=1)


def _hedefler():
    yield HTML, gomulu
    for yol, dosyalar in SAYFALAR.items():
        yield yol, (lambda m, d=dosyalar: sayfa_gomulu(m, d))


def main(argv) -> int:
    eski_kalan = []
    for yol, fn in _hedefler():
        eski = yol.read_text(encoding='utf-8')
        yeni = fn(eski)
        if yeni == eski:
            continue
        if '--kontrol' in argv:
            eski_kalan.append(yol.name)
        else:
            yol.write_text(yeni, encoding='utf-8')
            print('gömüldü:', yol.name)
    if '--kontrol' in argv:
        if eski_kalan:
            print('sözlükler güncel değil (%s): python3 scripts/i18n_gom.py' % ', '.join(eski_kalan))
            return 1
        return 0
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
