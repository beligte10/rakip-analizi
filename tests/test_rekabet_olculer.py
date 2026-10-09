"""Rekabet Analizi çalışmasından alınan ölçülerin testleri (2026-10-06).

Beklenen değerler Rekabet Analizi/KT_Rekabet_Analizi_Teknik_Devir.md'deki 30.06.2026 çıpalarıdır (KT_veri.js).
Ham veri testleri data/veriler.parquet yoksa atlanır.
"""
import json
from pathlib import Path

import pytest

from pipeline import groups as G
from pipeline import manuel_veri
from pipeline import rekabet_olculer as R
from pipeline.lookup import LookupContext
from pipeline.measures import MEASURE_FUNCS

ROOT = Path(__file__).resolve().parent.parent
PARQUET = ROOT / 'data' / 'veriler.parquet'
CATALOG = ROOT / 'data' / 'catalog.json'
SEED = json.loads((ROOT / 'catalog.seed.json').read_text(encoding='utf-8'))
T = '2026-06-30'
KT = 'Kuveyt Türk'

veri_var = pytest.mark.skipif(not (PARQUET.exists() and CATALOG.exists()), reason='ham veri yok')


@pytest.fixture(scope='module')
def ctx():
    cat = json.loads(CATALOG.read_text(encoding='utf-8'))
    return LookupContext.from_parquet(PARQUET, {b['banka_adi']: b['tur'] for b in cat['banks']})


def test_katalog_tutarli():
    seed_ids = {m['id'] for m in SEED['measures']}
    assert set(R.IDS) <= seed_ids, set(R.IDS) - seed_ids
    assert set(R.IDS) <= set(MEASURE_FUNCS)
    assert len(R.IDS) == len(set(R.IDS))
    for m in R.KATALOG:
        assert m['tip'] in ('rasyo', 'buyukluk') and m['akim_stok'] in ('akim', 'stok')
        assert m['birim'] in ('%', 'TL', 'bin_TL')
    # rasyo ölçüler grup toplama kuralına bağlı olmalı (yoksa grup değeri üye ortalamasına düşer)
    for m in R.KATALOG:
        if m['tip'] == 'rasyo' and m['id'] not in R.GRUPSUZ and m['id'] not in R.GRUP_OZEL:
            assert m['id'] in G.RATIO_NUM_DEN, m['id']


def test_manuel_veri_yuklenir():
    assert manuel_veri.deger('basel_kaldirac_orani', KT, T) == pytest.approx(6.29)
    assert manuel_veri.deger('lcr', 'QNB', T) == pytest.approx(129.2)
    assert manuel_veri.deger('serbest_karsilik', 'Denizbank', T) == pytest.approx(8700e6)   # mn TL → TL
    assert manuel_veri.deger('lcr', KT, '2026-03-31') == pytest.approx(240.68)   # son 8 çeyrek BDR arşivinden dolduruldu (2026-10-09)
    assert manuel_veri.deger('lcr', KT, '2023-12-31') is None                    # 8 çeyrek öncesi boş
    assert manuel_veri.deger('lcr', 'Halk Bank', T) == pytest.approx(159.62)   # 17 banka PDF'ten (2026-10-07)
    assert manuel_veri.deger('lcr', 'Olmayan Banka', T) is None
    assert manuel_veri.deger('serbest_karsilik', 'Enpara', T) is None            # bakiye belirsiz → boş
    assert manuel_veri.deger('serbest_karsilik', 'Emlak Katılım', T) == pytest.approx(13000e6)
    assert manuel_veri.deger('tufex_tamponu', 'Ziraat Bankası', T) == pytest.approx(13307e6)
    assert manuel_veri.metin('denetci_gorusu', 'QNB', T) == 'Sınırlı olumlu (şartlı)'


def test_manuel_veri_data_dizini_ustune_yazar(tmp_path, monkeypatch):
    (tmp_path / 'manuel_olculer.json').write_text(json.dumps(
        {'olculer': {'lcr': {'carpan': 1.0, 'veri': {T: {KT: 210.0}, '2026-09-30': {KT: 190.0}}}}}), encoding='utf-8')
    monkeypatch.setenv('DATA_DIR', str(tmp_path))
    assert manuel_veri.deger('lcr', KT, T) == 210.0            # üstteki dosya ezer
    assert manuel_veri.deger('lcr', KT, '2026-09-30') == 190.0  # yeni dönem eklenir
    assert manuel_veri.deger('lcr', 'QNB', T) == pytest.approx(129.2)   # dokunulmayan değer korunur


@veri_var
@pytest.mark.parametrize('mid, beklenen, tol', [
    ('zk_faiz_gelirleri_orani', 9.3, 0.05),
    ('tcmb_hesabi_getirili_aktif', 21.2, 0.05),
    ('ortuk_tcmb_getirisi', 7.15, 0.01),
    ('zk_haric_getirili_aktif_getirisi', 18.76, 0.01),
    ('zk_surukleme', -2.46, 0.01),
    ('nim_getirili_aktif', 6.81, 0.01),
    ('nim_swap_duzeltilmis', 3.77, 0.01),
    ('donuk_tahsilat_intikal', 47.2, 0.05),
    ('donuk_portfoy_temizligi', 10.9, 0.1),
    ('npl_3_asama_karsilama', 71.4, 0.05),
    ('grup_2_karsilama', 10.31, 0.01),
    ('personel_sayisi_yoy', 1.94, 0.02),
    ('personel_basina_personel_gideri_yoy', 38.85, 0.05),
    ('personel_basina_opex_yoy', 46.68, 0.05),
    ('net_ucret_faaliyet_gelirleri', 18.61, 0.01),
    ('efektif_vergi_orani', 24.13, 0.01),
    ('net_kar_yoy_buyumesi', 25.68, 0.01),
    ('yp_toplam_fonlama_payi', 62.47, 0.01),
    ('krediler_toplam_fonlama', 60.9, 0.05),
    ('yp_fonlama_fazlasi_aktif', 31.6, 0.05),
    ('rav_yogunlugu', 58.54, 0.01),
    ('basit_kaldirac', 9.42, 0.01),
    ('altin_vadesiz_payi', 87.34, 0.01),
])
def test_kt_haziran_2026_cipalari(ctx, mid, beklenen, tol):
    assert MEASURE_FUNCS[mid](ctx, KT, T) == pytest.approx(beklenen, abs=tol)


@veri_var
def test_tutar_olculer_kt_haziran_2026(ctx):
    f = MEASURE_FUNCS
    assert f['zorunlu_karsilik_geliri'](ctx, KT, T) / 1e6 == pytest.approx(9325)
    assert f['faaliyet_gelirleri'](ctx, KT, T) / 1e6 == pytest.approx(66119)
    assert f['vergi_oncesi_kar'](ctx, KT, T) / 1e6 == pytest.approx(31338)
    assert f['donuk_net_olusum'](ctx, KT, T) / 1e6 == pytest.approx(11058)
    assert f['turev_kar_zarar'](ctx, KT, T) / 1e6 == pytest.approx(-47846)
    assert f['kambiyo_kar_zarar'](ctx, KT, T) / 1e6 == pytest.approx(48690)


@veri_var
def test_surukleme_ayristirma_kimligi(ctx):
    """Sürükleme = w/(1−w) × (getiri − örtük TCMB getirisi), w = TCMB'nin getirili aktif payı (doküman §5.16)."""
    for b in ('Kuveyt Türk', 'Akbank', 'QNB'):
        w = MEASURE_FUNCS['tcmb_hesabi_getirili_aktif'](ctx, b, T) / 100
        getiri = G._nd_iea_getiri(ctx, b, T)
        getiri = getiri[0] / getiri[1] * 100
        fark = getiri - MEASURE_FUNCS['ortuk_tcmb_getirisi'](ctx, b, T)
        assert -MEASURE_FUNCS['zk_surukleme'](ctx, b, T) == pytest.approx(w / (1 - w) * fark, abs=0.02)


@veri_var
def test_eski_donemde_olculer_hata_vermez_ve_mantikli(ctx):
    for b in (KT, 'Akbank'):
        for yil in range(2014, 2026):
            t = f'{yil}-12-31'
            for mid in R.IDS:
                v = MEASURE_FUNCS[mid](ctx, b, t)
                assert v is None or v == v    # NaN değil
            kars = MEASURE_FUNCS['npl_3_asama_karsilama'](ctx, b, t)
            assert kars is None or 20 < kars < 150, (b, t, kars)   # 0 değil, veri yoksa None


@veri_var
def test_grup_degerleri(ctx):
    sr, au = G._sum_ratio, G._active_members
    ilk = {b: '2013-12-31' for b in (KT, 'QNB', 'Denizbank')}
    # tek üyeli grup = banka değeri
    assert R.GRUP_OZEL['zk_surukleme'](ctx, [KT], T, ilk, sr, au) == pytest.approx(MEASURE_FUNCS['zk_surukleme'](ctx, KT, T))
    # çok üyeli grup: kişi başı yıllık büyüme üye oranlarının ortalaması değil toplamlardan türetilir
    g = R.GRUP_OZEL['personel_basina_personel_gideri_yoy'](ctx, [KT, 'QNB', 'Denizbank'], T, ilk, sr, au)
    uye = [MEASURE_FUNCS['personel_basina_personel_gideri_yoy'](ctx, b, T) for b in (KT, 'QNB', 'Denizbank')]
    assert min(uye) - 1e-6 <= g <= max(uye) + 1e-6
    # LCR/kaldıraç için grup paçalı yoktur
    assert {'lcr', 'lcr_yp', 'basel_kaldirac_orani'} == R.GRUPSUZ


def test_rekabet_tutar_grubu_verisi_olmayan_uyeyi_dislar():
    bd = {'serbest_karsilik': {'A': {T: 5.0}, 'B': {T: None}, 'C': {T: 7.0}}}
    assert G._agg_size_mevcut(bd, 'serbest_karsilik', ['A', 'B', 'C'], T) == 12.0
    assert G._agg_size_mevcut(bd, 'serbest_karsilik', ['B'], T) is None
    # sistemin genel kuralı (diğer ölçüler) değişmedi: eksik üye grubu boşaltır
    assert G._agg_size(bd, 'serbest_karsilik', ['A', 'B', 'C'], T) is None


def test_tufex_yapisal_sifir_ve_tahmin_kullanan_bos():
    assert manuel_veri.deger('tufex_tamponu', 'Dünya Katılım', T) == 0.0                 # Hazine endeksiyle değerler, tahmini enflasyon yok
    assert manuel_veri.deger('tufex_tamponu', 'Fibabanka', '2025-12-31') is None        # o çeyrekte "tahmini enflasyon oranı" kullanmış, varsayımı açıklamamış
    assert manuel_veri.deger('tufex_tamponu', 'Burgan Bank', T) is None                  # tahmin kullanıyor, varsayım açıklamıyor


@veri_var
def test_kar_tamponu_iki_bilesen_gerektirir(ctx):
    f = MEASURE_FUNCS['kar_tamponu_net_kar']
    assert f(ctx, 'Burgan Bank', T) is None       # TÜFEX bilinmiyor → kısmi tampon gösterilmez
    assert f(ctx, 'Dünya Katılım', T) is not None  # serbest karşılık 0 + TÜFEX 0 (yapısal sıfır)


@veri_var
def test_altin_vadesiz_payi_mevduat_bankalarinda_bddk_verisinden(ctx):
    f = MEASURE_FUNCS['altin_vadesiz_payi']
    assert f(ctx, 'Halk Bank', T) == pytest.approx(91.2, abs=0.1)      # elle yükleme yokken de hesaplanır
    assert f(ctx, 'Halk Bank', '2025-12-31') is not None               # geçmiş dönemler de dolu


@veri_var
def test_bos_neden_kurallari(ctx):
    from pipeline import bos_nedenleri as B
    assert B.neden(ctx, 'sube_basina_opex', 'TOM Bank', T)[0] == 'tanimsiz'                       # şubesiz banka
    assert B.neden(ctx, 'net_kar_yoy_buyumesi', 'TOM Bank', T)[0] == 'tanimsiz'                   # önceki yıl zarar
    assert B.neden(ctx, 'tufex_tamponu', 'Burgan Bank', T)[0] == 'veri_yok'                       # tahmin kullanıyor, açıklamıyor
    assert B.neden(ctx, 'lcr', 'Kuveyt Türk', '2023-12-31')[0] == 'veri_yok'                      # BDR verisi yüklenmeyen dönem
    assert B.neden(ctx, 'altin_vadesiz_payi', 'TOM Bank', T)[0] == 'tanimsiz'                     # altın hesabı yok


def test_bos_neden_arayuz_ve_ceviri_eslesmesi():
    """Sunucunun ürettiği her neden metni arayüz sözlüğünde İngilizce karşılığa sahip olmalı."""
    import re
    from pipeline import bos_nedenleri as B
    sozluk = json.loads((ROOT / 'frontend' / 'i18n' / 'arayuz_en.json').read_text(encoding='utf-8'))
    kaynak = (ROOT / 'pipeline' / 'bos_nedenleri.py').read_text(encoding='utf-8')
    metinler = {m for m in re.findall(r"(?:TANIMSIZ|VERI_YOK),\s*'([^']+)'", kaynak)}
    assert metinler, 'neden metni bulunamadı'
    eksik = sorted(m for m in metinler if m not in sozluk)
    assert not eksik, eksik


@veri_var
def test_bos_nedenlerinde_genel_metne_dusen_hucre_yok(ctx):
    """Son 12 çeyrekte değeri boş her Rekabet hücresinin özel (kurala bağlı) bir nedeni olmalı."""
    from pipeline import bos_nedenleri as B
    bd = json.loads((ROOT / 'data' / 'computed.json').read_text(encoding='utf-8'))['bank_data']
    cat = json.loads(CATALOG.read_text(encoding='utf-8'))
    o = B.uret(ctx, cat, bd)
    genel = [(m, b, t) for m, bs in o.items() for b, ts in bs.items() for t, (_k, x) in ts.items() if x.startswith('Gerekli kalemler')]
    assert not genel, genel[:5]


def test_tufex_cikarici_birim_ve_isaret():
    """BDR dipnot cümlelerinden TÜFEX: milyar/bin TL birimi ve 'azalarak' işareti doğru okunur."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
    import bdr_rekabet_cikar as C
    c = ('değerlemesi yıllık %48,0 enflasyon tahminine göre yapılmıştır. TÜFE tahmininin %1 artması veya azalması durumunda, '
         'vergi öncesi dönem karı yaklaşık 1 milyar (tam tutar) TL artacak.')
    assert C.tufex_bilgisi(c) == (48.0, 1000.0)
    d = ('Tutarlar Bin Türk Lirası olarak ifade edilmiştir. referans endekse göre yapılsaydı, değerleme farkları 47.296 TL artacak, '
         'net dönem karı 280.471 TL azalarak 40.207.236 TL olacaktı.')
    assert round(C.tufex_aciklanmis(d), 1) == -280.5
