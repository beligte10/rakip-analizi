"""EVDS araçları (2026-09-30) — ağa çıkmadan: tarih çevirisi, satır
sadeleştirme, arama, doğrulama, anahtar yokken araçların gizlenmesi."""
import json

import pytest

from assistant.external import evds, tuik
from assistant.external import tools as T
from assistant.external.http import ExternalError


@pytest.fixture(autouse=True)
def anahtarsiz(monkeypatch, tmp_path):
    from assistant.external import evds_katalog as _K        # gerçek data/evds_katalog.json testleri etkilemesin
    monkeypatch.setattr(_K, 'KATALOG_YOLU', tmp_path / 'katalog_yok.json')
    _K.yenile()
    monkeypatch.delenv('EVDS_API_KEY', raising=False)
    monkeypatch.delenv('TUIK_API_KEY', raising=False)
    monkeypatch.delenv('TUIK_ETKIN', raising=False)
    evds._groups.clear()
    evds._series.clear()


def test_tarih_cevirisi():
    assert T._evds_date('2025-03-07') == '07-03-2025'
    assert T._evds_date('2025-02') == '01-02-2025'
    assert T._evds_date('2024-02', end=True) == '29-02-2024'   # artık yıl
    assert T._evds_date('2025') == '01-01-2025'
    assert T._evds_date('2025', end=True) == '31-12-2025'
    assert T._evds_date('Mart 2025') is None


def test_satir_sadelestirme():
    items = [{'Tarih': '2025-1', 'TP_DK_USD_A': '35.45595909', 'TP_FG_J0-3': '42.1', 'UNIXTIME': {'$numberLong': '1'}},
             {'Tarih': '2025-2', 'TP_DK_USD_A': 'ND', 'TP_FG_J0-3': None}]
    rows = evds.clean_rows(items, ['TP.DK.USD.A', 'TP.FG.J0'])
    assert rows[0] == {'tarih': '2025-1', 'TP.DK.USD.A': 35.455959, 'TP.FG.J0': 42.1}
    assert rows[1]['TP.DK.USD.A'] is None and rows[1]['TP.FG.J0'] is None


def test_arama_tum_terimler_turkce_harf_duyarsiz(monkeypatch):
    gruplar = [
        {'DATAGROUP_CODE': 'bie_kt100h', 'DATAGROUP_NAME': 'Kredi Faiz Oranları (Akım)', 'END_DATE': '18-09-2026'},
        {'DATAGROUP_CODE': 'bie_mevfaiz', 'DATAGROUP_NAME': 'Mevduat Faiz Oranları', 'END_DATE': '18-09-2026'},
        {'DATAGROUP_CODE': 'bie_dkdovytl', 'DATAGROUP_NAME': 'Döviz Kurları', 'END_DATE': '29-09-2026'},
    ]
    monkeypatch.setattr(evds, 'datagroups', lambda: gruplar)
    assert [g['DATAGROUP_CODE'] for g in evds.search('KREDİ faiz')] == ['bie_kt100h']
    assert [g['DATAGROUP_CODE'] for g in evds.search('doviz')] == ['bie_dkdovytl']
    assert evds.search('') == []


def test_seri_kodu_dogrulamasi_istek_atmadan():
    with pytest.raises(ExternalError):
        evds.fetch(['tp.dk.usd.a; DROP'], '01-01-2025', '31-01-2025')
    with pytest.raises(ExternalError):
        evds.fetch(['TP.A'] * 6, '01-01-2025', '31-01-2025')      # en fazla 5 seri
    with pytest.raises(ExternalError):
        evds.series_list('../etc')


def test_istek_parametreleri(monkeypatch):
    istenen = {}
    monkeypatch.setattr(evds, '_get', lambda path, timeout=45.0: istenen.setdefault('p', path) and {'items': []})
    evds.fetch(['TP.DK.USD.A', 'TP.FG.J0'], '01-01-2025', '31-12-2025', frequency=5, aggregation='avg', formula=3)
    p = istenen['p']
    assert 'series=TP.DK.USD.A-TP.FG.J0' in p and 'frequency=5' in p
    assert 'aggregationTypes=avg-avg' in p and 'formulas=3-3' in p


def test_satir_siniri_en_yeni_satirlari_tutar(monkeypatch):
    monkeypatch.setenv('EVDS_API_KEY', 'test')
    items = [{'Tarih': f'{i:03d}', 'TP_X': str(i)} for i in range(T.EVDS_MAX_ROWS + 30)]
    monkeypatch.setattr(evds, 'fetch', lambda *a, **k: items)
    r, _ = T.execute('evds_veri', {'seriler': ['TP.X'], 'baslangic': '2020'})
    assert r['kisaltildi'] and len(r['satirlar']) == T.EVDS_MAX_ROWS
    assert r['satirlar'][-1]['TP.X'] == T.EVDS_MAX_ROWS + 29
    assert r['kaynak'].startswith('TCMB EVDS')


def test_anahtar_yoksa_arac_sunulmaz_ve_calismaz():
    assert T.active_specs() == []
    r, _ = T.execute('evds_ara', {'query': 'kur'})
    assert 'etkin değil' in r['hata']


def test_tuik_bekleme_modunda(monkeypatch):
    monkeypatch.setenv('EVDS_API_KEY', 'x')
    monkeypatch.setenv('TUIK_API_KEY', 'y')
    names = [s['function']['name'] for s in T.active_specs()]
    assert names == ['evds_ara', 'evds_seriler', 'evds_veri', 'evds_rehber']      # TÜİK kapalı (TUIK_ETKIN yok)
    monkeypatch.setenv('TUIK_ETKIN', '1')
    assert tuik.enabled()


def test_servis_hatasi_sohbeti_dusurmez(monkeypatch):
    monkeypatch.setenv('EVDS_API_KEY', 'test')

    def boom(*a, **k):
        raise ExternalError('TCMB EVDS servisi HTTP 503 döndürdü', status=503)
    monkeypatch.setattr(evds, 'datagroups', boom)
    r, _ = T.execute('evds_ara', {'query': 'kur'})
    assert r['hata'] == 'TCMB EVDS servisi HTTP 503 döndürdü'


# --- Katalog, rehber ve doğrulama (2026-10-02) ---
from assistant.external import evds_katalog as K
from assistant.external import evds_rehber as RH

MINI = {
    'surum': 1, 'olusturma': '2026-10-02T00:00:00',
    'kategoriler': {'1': {'ad': 'Kurlar', 'ad_en': 'FX', 'ust': ''}, '2': {'ad': 'Fiyat Endeksleri', 'ad_en': 'Prices', 'ust': ''}},
    'gruplar': {
        'bie_dk': {'ad': 'Döviz Kurları', 'ad_en': 'FX rates', 'kat': '1', 'frekans': 'GÜNLÜK', 'birim': 'Türk lirası',
                   'kurum': 'TCMB', 'baslangic': '02-01-1950', 'bitis': '02-10-2026', 'not': '', 'metaveri': ''},
        'bie_tufe': {'ad': 'Tüketici Fiyat Endeksi (2025=100)', 'ad_en': 'CPI', 'kat': '2', 'frekans': 'AYLIK', 'birim': '',
                     'kurum': 'TÜİK', 'baslangic': '01-01-2005', 'bitis': '01-08-2026', 'not': '', 'metaveri': ''},
        'bie_eski': {'ad': 'Tüketici Fiyat Endeksi (2003=100)', 'ad_en': 'CPI old', 'kat': '2', 'frekans': 'AYLIK', 'birim': '',
                     'kurum': 'TÜİK', 'baslangic': '01-01-2003', 'bitis': '01-12-2025', 'not': '', 'metaveri': ''},
    },
    'seriler': [
        ['TP.DK.USD.A.YTL', '(USD) ABD Doları (Döviz Alış)', 'bie_dk', 'GÜNLÜK', 'avg', '02-01-1950', '02-10-2026', '', '', 'aflxn'],
        ['TP.DK.USD.S.YTL', '(USD) ABD Doları (Döviz Satış)', 'bie_dk', 'GÜNLÜK', 'avg', '02-01-1950', '02-10-2026', '', '', 'aflxn'],
        ['TP.TUKFIY2025.GENEL', 'Genel Endeks', 'bie_tufe', 'AYLIK', 'avg', '01-01-2005', '01-08-2026', '', '', 'aflxn'],
        ['TP.FG.J0', 'GENEL (Tüketici) (Arşiv)', 'bie_eski', 'AYLIK', 'avg', '01-01-2003', '01-12-2025', '', '', 'aflxn'],
        ['TP.AB.N07', '2A1 Brüt Döviz Rezervleri', 'bie_dk', 'HAFTALIK(CUMA)', 'last', '01-01-2000', '02-10-2026', '', '', 'aflxn'],
    ],
}


@pytest.fixture
def katalog(tmp_path, monkeypatch):
    yol = tmp_path / 'evds_katalog.json'
    yol.write_text(json.dumps(MINI), encoding='utf-8')
    monkeypatch.setattr(K, 'KATALOG_YOLU', yol)
    K.yenile()
    yield K.yukle()
    K.yenile()


def test_katalog_seri_arama_ve_siralama(katalog):
    assert katalog.seri('tp.dk.usd.a.ytl')['ad'].startswith('(USD)')
    ilk = [s['kod'] for s in katalog.ara('dolar kuru', 3)]
    assert ilk[:2] == ['TP.DK.USD.A.YTL', 'TP.DK.USD.S.YTL']          # önerilen kısayol + eş anlam (dolar→usd)
    enf = [s['kod'] for s in katalog.ara('enflasyon', 5)]
    assert enf[0] == 'TP.TUKFIY2025.GENEL'                             # güncel TÜFE öne
    assert enf.index('TP.FG.J0') > 0 if 'TP.FG.J0' in enf else True    # arşiv seri geriye düşer
    assert katalog.ara('TP.AB.N07')[0]['kod'] == 'TP.AB.N07'           # kod doğrudan
    assert katalog.ara('') == [] and katalog.ara('zzzyok') == []
    assert len({s['kod'] for s in katalog.ara('dolar', 10)}) == len(katalog.ara('dolar', 10))   # yineleme yok
    assert katalog.seri_bilgi(katalog.seri('TP.FG.J0'))['uyari'].startswith('Arşiv')


def test_katalog_yoksa_ve_frekans_kodu(tmp_path, monkeypatch):
    monkeypatch.setattr(K, 'KATALOG_YOLU', tmp_path / 'yok.json')
    K.yenile()
    assert K.yukle() is None and K.ozet() == {'var': False}
    assert K.frekans_kodu('GÜNLÜK') == 1 and K.frekans_kodu('aylık') == 5 and K.frekans_kodu('x') is None


def test_evds_ara_katalogla_seri_doner(katalog, monkeypatch):
    monkeypatch.setenv('EVDS_API_KEY', 'test')
    r, _ = T.execute('evds_ara', {'query': 'dolar kuru'})
    assert r['seriler'][0]['kod'] == 'TP.DK.USD.A.YTL' and r['seriler'][0]['birim'] == 'Türk lirası'
    assert r['veri_gruplari'] and r['veri_gruplari'][0]['kod'] == 'bie_dk'
    r2, _ = T.execute('evds_seriler', {'grup_kodu': 'bie_dk'})        # katalogdan, ağ yok
    assert r2['seri_sayisi'] == 3 and r2['birim'] == 'Türk lirası'


def test_evds_veri_dogrulamalari(katalog, monkeypatch):
    monkeypatch.setenv('EVDS_API_KEY', 'test')
    cagrilar = []
    monkeypatch.setattr(evds, 'fetch', lambda *a, **k: cagrilar.append(a) or [{'Tarih': '2025-1', 'TP_AB_N07': '5'}])
    r, _ = T.execute('evds_veri', {'seriler': ['TP.TUKFIY2025.GENEL'], 'baslangic': '2025', 'frekans': 'gunluk'})
    assert 'daha sık' in r['hata'] and not cagrilar                    # aylık seri günlüğe çevrilemez
    r, _ = T.execute('evds_veri', {'seriler': ['TP.AB.N07'], 'baslangic': '2025', 'frekans': 'aylik', 'toplulastirma': 'sum'})
    assert "'sum'" in r['hata'] or 'sum' in r['hata']
    r, _ = T.execute('evds_veri', {'seriler': ['TP.AB.N07'], 'baslangic': '2025', 'frekans': 'aylik', 'toplulastirma': 'last'})
    assert r['seri_bilgi'][0]['frekans'] == 'HAFTALIK(CUMA)' and cagrilar and r['toplulastirma'] == 'last'
    assert any('geçici' in n for n in r['notlar'])
    r, _ = T.execute('evds_veri', {'seriler': ['TP.FG.J0'], 'baslangic': '2025'})
    assert any('Arşiv' in n for n in r['notlar'])                      # arşiv seri uyarısı


def test_evds_veri_bilinmeyen_kod_katalogda_yok_uyarisi(katalog, monkeypatch):
    monkeypatch.setenv('EVDS_API_KEY', 'test')

    def hata(*a, **k):
        raise ExternalError('TCMB EVDS servisi HTTP 400 döndürdü', status=400)
    monkeypatch.setattr(evds, 'fetch', hata)
    r, _ = T.execute('evds_veri', {'seriler': ['TP.UYDURMA.X'], 'baslangic': '2025'})
    assert 'katalogda yok' in r['hata'] and 'TP.UYDURMA.X' in r['hata']


def test_evds_rehber_bolumleri():
    assert set(RH.bolumler()) >= set(range(1, 12))
    assert 'aggregationTypes' in RH.getir('toplulastirma') and 'frequency' in RH.getir('frekans')
    assert RH.getir('yok') is None
    assert all(RH.getir(k) for k in RH.KONULAR)
    assert 'tahmin etme' in RH.davranis_kurallari()


def test_evds_rehber_araci(monkeypatch):
    monkeypatch.setenv('EVDS_API_KEY', 'test')
    r, _ = T.execute('evds_rehber', {'konu': 'formul'})
    assert 'Yıllık yüzde değişim' in r['icerik']
    r, _ = T.execute('evds_rehber', {'konu': 'bilinmeyen'})
    assert r['hata'] == 'Bilinmeyen konu' and len(r['konular']) == len(RH.KONULAR)


def test_sistem_istemi_evds_kurallari(monkeypatch):
    from assistant import service as S
    monkeypatch.setenv('EVDS_API_KEY', 'test')
    monkeypatch.delenv('TUIK_API_KEY', raising=False)
    metin = S._dis_kaynak_metni(True)
    assert 'EVDS KURALLARI' in metin and 'TP.TUKFIY2025.GENEL' in metin and 'evds_rehber' in metin
    monkeypatch.delenv('EVDS_API_KEY')
    assert S._dis_kaynak_metni(True) == ''
