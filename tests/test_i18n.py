"""İngilizce sürüm (2026-10-02): sözlüklerin bütünlüğü ve çeviri motorları.

- frontend/i18n/olcu_en.json katalogdaki her ölçüyü, kategoriyi, kompozisyonu ve bileşeni kapsar.
- Pano, giriş, başvuru ve admin sayfalarına gömülü sözlükler JSON dosyalarıyla aynıdır (scripts/i18n_gom.py).
- Pano <i18n-cevir> bloğu ve sayfa motoru <kt-cevir> bloğu (frontend/i18n/sayfa_cevir.js) bir JS motorunda
  (node/jsc) çalıştırılır: tam eşleşme, ifade düzeyinde çeviri, "X Hariç …" grupları, banka adı koruması,
  tekil/çoğul, noktalama boşluğu.
- Giriş, başvuru ve admin sayfalarının statik HTML'indeki her Türkçe metin (translate="no" dışı) çevrilir.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import i18n_gom  # noqa: E402

from test_custom_measures_js import _js_engine  # noqa: E402

OLCU = json.loads((ROOT / 'frontend' / 'i18n' / 'olcu_en.json').read_text(encoding='utf-8'))
ARAYUZ = json.loads((ROOT / 'frontend' / 'i18n' / 'arayuz_en.json').read_text(encoding='utf-8'))
SEED = json.loads((ROOT / 'catalog.seed.json').read_text(encoding='utf-8'))
TURKCE_HARF = re.compile(r'[ÇĞİÖŞÜçğıöşü]')
# İngilizce metinde kalabilecek özel adlar
OZEL_ADLAR = ('Kuveyt Türk', 'STRATEJİ')


def _ozelsiz(t):
    for ad in OZEL_ADLAR:
        t = t.replace(ad, '')
    return t


def test_tum_olculer_ve_kategoriler_cevrilmis():
    olculer = SEED['measures']
    eksik = [m['id'] for m in olculer if not OLCU['olcu'].get(m['id'])]
    assert not eksik, eksik
    kategoriler = {m.get(k) for m in olculer for k in ('kategori', 'alt_kategori')} - {None, ''}
    assert not [k for k in kategoriler if k not in OLCU['kategori']]


def test_kompozisyon_ve_bilesenler_cevrilmis():
    for cid, c in SEED['compositions'].items():
        assert OLCU['kompozisyon'].get(cid), cid
        assert OLCU['kategori'].get(c.get('kategori')), (cid, c.get('kategori'))
        for b in c.get('components', []):
            assert OLCU['bilesen'].get(b['ad']), (cid, b['ad'])


def test_ingilizce_degerlerde_turkce_harf_yok():
    for bolum in ('kategori', 'olcu', 'kompozisyon', 'bilesen'):
        kotu = {k: v for k, v in OLCU[bolum].items() if not v.strip() or TURKCE_HARF.search(_ozelsiz(v))}
        assert not kotu, (bolum, kotu)
    kotu = {k: v for k, v in ARAYUZ.items() if TURKCE_HARF.search(_ozelsiz(v))}
    assert not kotu, kotu


def test_gomulu_sozlukler_guncel():
    assert i18n_gom.main(['--kontrol']) == 0, 'python3 scripts/i18n_gom.py çalıştırın'


SAYFA_SOZLUKLERI = ('giris_en.json', 'admin_en.json', 'sunucu_en.json')


def test_sayfa_sozluklerinde_turkce_harf_yok():
    for ad in SAYFA_SOZLUKLERI:
        d = json.loads((ROOT / 'frontend' / 'i18n' / ad).read_text(encoding='utf-8'))
        kotu = {k: v for k, v in d.items() if TURKCE_HARF.search(_ozelsiz(v).replace('BDR-Kısayol', ''))}
        assert not kotu, (ad, kotu)


HARNESS = r"""
var EN = true, window = {}, localStorage = { getItem: function(){ return null; } };
var DATA = { meta: { banks: [{banka_adi: 'Kuveyt Türk'}, {banka_adi: 'Garanti Bankası'}, {banka_adi: 'Ziraat Katılım'},
                             {banka_adi: 'İş Bankası'}] } };
var BANK_SHORT = { 'Ziraat Katılım': 'Ziraat Kat.' };
var I18N_ARAYUZ = __ARAYUZ__;
__CODE__
var girdi = __GIRDI__, cikti = {};
girdi.forEach(function(s){ cikti[s] = cevir(s); });
(typeof console !== 'undefined' && console.log ? console.log : print)(JSON.stringify(cikti));
"""

BEKLENEN = {
    'Katılım Bankaları': 'Participation Banks',
    'KT Hariç Katılım Bankaları': 'Participation Banks excl. KT',
    'Garanti Hariç Mevduat Bankaları': 'Deposit Banks excl. Garanti',
    'Tüm Banka Büyüklükleri (Milyon TL)': 'All Banks — Size (TL million)',
    'Kuveyt Türk sırası:': 'Kuveyt Türk rank:',
    'İş Bankası': 'İş Bankası',                     # banka adı çevrilmez
    'Ziraat Kat.': 'Ziraat Kat.',                   # kısa banka adı da korunur
    '1 banka · 0 grup': '1 bank · 0 groups',        # 1 için tekil
    '27 banka': '27 banks',
    'Mart': 'March',
    '12,5': '12,5',                                 # harfsiz metin olduğu gibi
}


@pytest.fixture(scope='module')
def cevrilen(tmp_path_factory):
    motor = _js_engine()
    if not motor:
        pytest.skip('çalışan bir JS motoru (node/jsc) yok')
    html = (ROOT / 'frontend' / 'index_v30.html').read_text(encoding='utf-8')
    m = re.search(r'// <i18n-cevir>[^\n]*\n(.*?)// </i18n-cevir>', html, re.S)
    assert m, '<i18n-cevir> işaretleri bulunamadı'
    sozluk = dict(ARAYUZ)
    for k, v in OLCU['kategori'].items():
        sozluk.setdefault(k, v)
    betik = (HARNESS.replace('__ARAYUZ__', json.dumps(sozluk, ensure_ascii=False))
             .replace('__GIRDI__', json.dumps(list(BEKLENEN), ensure_ascii=False))
             .replace('__CODE__', m.group(1)))
    d = tmp_path_factory.mktemp('i18n')
    (d / 'harness.js').write_text(betik, encoding='utf-8')
    res = subprocess.run([motor, str(d / 'harness.js')], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr or res.stdout
    return json.loads(res.stdout)


@pytest.mark.parametrize('girdi', list(BEKLENEN))
def test_cevir(cevrilen, girdi):
    assert cevrilen[girdi] == BEKLENEN[girdi]


# ---------------------------------------------------------------------------
# Giriş / başvuru / admin sayfaları (sayfa_cevir.js)
# ---------------------------------------------------------------------------
from html.parser import HTMLParser  # noqa: E402

SAYFA_HARNESS = r"""
var EN = true, window = {};
var veri = { bankalar: __BANKALAR__ };
var SOZLUK = __SOZLUK__;
__CODE__
var girdi = __GIRDI__, cikti = {};
girdi.forEach(function(s){ cikti[s] = cevir(s); });
(typeof console !== 'undefined' && console.log ? console.log : print)(JSON.stringify(cikti));
"""


class _StatikMetin(HTMLParser):
    """Statik HTML'deki metin düğümleri ve placeholder/title/alt/aria-label (script/style ve translate="no" hariç)."""
    ATTRS = ('placeholder', 'title', 'alt', 'aria-label')
    BOS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.yigin, self.out = [], []

    def _atla(self):
        return any(a for a in self.yigin)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if not self._atla():
            self.out += [v for k, v in attrs if k in self.ATTRS and v]
        if tag not in self.BOS:
            self.yigin.append(tag in ('script', 'style', 'textarea') or a.get('translate') == 'no')

    def handle_endtag(self, tag):
        if tag not in self.BOS and self.yigin:
            self.yigin.pop()

    def handle_data(self, data):
        if not self._atla() and data.strip():
            self.out.append(data)


def _statik_turkce(yol):
    p = _StatikMetin()
    p.feed(yol.read_text(encoding='utf-8'))
    return sorted({re.sub(r'\s+', ' ', t).strip() for t in p.out if TURKCE_HARF.search(t)})


def _sayfa_cevir(motor, tmp, sozluk, girdiler):
    kod = (ROOT / 'frontend' / 'i18n' / 'sayfa_cevir.js').read_text(encoding='utf-8')
    m = re.search(r'// <kt-cevir>[^\n]*\n(.*?)// </kt-cevir>', kod, re.S)
    assert m, '<kt-cevir> işaretleri bulunamadı'
    betik = (SAYFA_HARNESS.replace('__BANKALAR__', json.dumps(i18n_gom.banka_adlari(), ensure_ascii=False))
             .replace('__SOZLUK__', json.dumps(sozluk, ensure_ascii=False))
             .replace('__GIRDI__', json.dumps(girdiler, ensure_ascii=False))
             .replace('__CODE__', m.group(1)))
    (tmp / 'sayfa.js').write_text(betik, encoding='utf-8')
    res = subprocess.run([motor, str(tmp / 'sayfa.js')], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr or res.stdout
    return json.loads(res.stdout)


@pytest.fixture(scope='module')
def motor():
    m = _js_engine()
    if not m:
        pytest.skip('çalışan bir JS motoru (node/jsc) yok')
    return m


@pytest.mark.parametrize('sayfa', ['login.html', 'signup.html', 'admin.html'])
def test_sayfanin_statik_metinleri_cevriliyor(motor, tmp_path, sayfa):
    yol = ROOT / 'frontend' / sayfa
    dosyalar = next(d for p, d in i18n_gom.SAYFALAR.items() if p.name == sayfa)
    girdiler = _statik_turkce(yol)
    assert girdiler, sayfa
    cikti = _sayfa_cevir(motor, tmp_path, i18n_gom.sayfa_sozlugu(dosyalar), girdiler)
    kalan = {k: v for k, v in cikti.items()
             if TURKCE_HARF.search(_ozelsiz(v).replace('BDR-Kısayol', '').replace('PROJE_EL_KITABI', ''))}
    assert not kalan, kalan


SAYFA_BEKLENEN = {
    'E-posta veya şifre hatalı': 'Incorrect email or password',
    '📥 2026-Q2 — 3 banka verisi henüz yüklenmedi:': '📥 2026-Q2 — 3 banks not uploaded yet:',
    '(1 banka)': '(1 bank)',
    '3 kullanıcı · hazır · kilitli': '3 users · built-in · locked',
    'Akbank Hariç Mevduat Bankaları güncellendi': 'Deposit Banks excl. Akbank updated',
    'Kuveyt Türk Rakip Bankalar grubundan çıkarıldı': 'Kuveyt Türk removed from Peer Banks',
    'Bilinmeyen banka: Ziraat Katılım': 'Unknown bank: Ziraat Katılım',
    ' üzerinden başvurur. Onaylanana kadar giriş yapamazlar. Yeni üyeler ':
        '. They cannot sign in until approved. New members start with the ',   # noktalama önü boşluk atılır
    '  ... ve 2 dosya daha': '  ... and 2 more files',                         # "..." ile başlayan korunur
    '12.345': '12.345',
}


def test_sayfa_motoru_ornekler(motor, tmp_path):
    sozluk = i18n_gom.sayfa_sozlugu(['sunucu_en.json', 'admin_en.json'])
    cikti = _sayfa_cevir(motor, tmp_path, sozluk, list(SAYFA_BEKLENEN))
    assert cikti == SAYFA_BEKLENEN
