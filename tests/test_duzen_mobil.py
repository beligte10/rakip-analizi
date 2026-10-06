"""Mobil / tablet düzen testleri (2026-10-03).

scripts/duzen_denetimi.py ile pano başsız Chrome'da telefon (375, 430 px), tablet dikey (768 px) ve tablet
yatay (1024 px) boyutlarında açılır; Anında Görünüm, menü, Trend, Kompozisyon, pencereler, Asistan ve Dışa
Aktar ekranlarında sayfa taşması, ekran dışı / yarım görünen öğe, kesik yazı, üst üste binen düğme, küçük
dokunma hedefi ve çok küçük yazı aranır (tests/duzen/duzen_denetimi.js).

Chrome ya da data/computed.json yoksa atlanır. Uzun sürer (~2,5 dk); KT_DUZEN_ATLA=1 ile atlanabilir.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import duzen_denetimi as D  # noqa: E402

pytestmark = pytest.mark.skipif(
    os.environ.get('KT_DUZEN_ATLA') == '1' or not D.chrome_yolu() or not D.VERI.exists(),
    reason='Chrome / data/computed.json yok ya da KT_DUZEN_ATLA=1')


def _ozet(r):
    return '\n'.join('[%s] %s — %s %s' % (x['durum'], x['tur'], x['oge'], x['bilgi']) for x in r.get('sorunlar', []))


@pytest.mark.parametrize('boyut,dil', [(b, 'tr') for b in D.BOYUTLAR] + [('375x812', 'en'), ('1024x768', 'en')])
def test_duzen_temiz(boyut, dil):
    r = D.denetle(boyut, dil)
    assert not r.get('hata'), r.get('hata')
    eksik = [d for d in D.BEKLENEN_EKRANLAR if d not in r.get('gezilen', [])]
    assert not eksik, 'açılamayan ekranlar: %s' % eksik
    assert not r['sorunlar'], '%s (%s) düzen sorunları:\n%s' % (boyut, dil, _ozet(r))


def test_denetim_bozuk_duzeni_yakalar():
    # Bilerek bozulmuş düzen: sabit genişlikli ızgara (yatay taşma) ve minik düğmeler
    r = D.denetle('375x812', 'tr', ek_css='.dashboard-grid { min-width: 900px !important; } '
                                         '.bank-filter-tab { height: 16px !important; min-height: 0 !important; }')
    turler = {x['tur'] for x in r.get('sorunlar', [])}
    assert 'tasma' in turler, _ozet(r)
    assert 'kucuk_hedef' in turler, _ozet(r)
