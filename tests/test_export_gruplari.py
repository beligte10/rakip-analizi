"""Excel dışa aktarım grupları (2026-10-04): Tüm Bankalar, İlk 20 Banka (tarihe göre değişen üyelik) ve
'Rakip Bankalar + <odak>' — group_data'da, meta.export_groups ile bildirilir; panoda grup olarak görünmez."""
import copy

from pipeline import groups as G

from test_focus import KATALOG


def _bank_data(n_banka=25):
    ad = [b['banka_adi'] for b in KATALOG['banks']]
    ekstra = [f'Banka{i}' for i in range(n_banka - len(ad))]
    ta = {}
    for i, b in enumerate(ad + ekstra):
        ta[b] = {'2026-03-31': 100.0 + i, '2026-06-30': 200.0 + i}
    return ad, ekstra, {'toplam_aktifler': ta}


def test_export_grup_adlari():
    k = copy.deepcopy(KATALOG)
    assert G.export_grup_adlari(k) == ['Tüm Bankalar', 'İlk 20 Banka', 'Rakip Bankalar + KT']
    del k['groups']['members']['Rakip Bankalar']
    assert G.export_grup_adlari(k) == ['Tüm Bankalar', 'İlk 20 Banka']
    assert G.export_grup_adlari([]) == []


def test_group_data_export_gruplari():
    k = copy.deepcopy(KATALOG)
    ad, ekstra, bd = _bank_data()
    k['banks'] = k['banks'] + [{'banka_adi': b, 'tur': 'Mevduat'} for b in ekstra]
    k['measures'] = [{'id': 'toplam_aktifler', 'tip': 'buyukluk'}]
    gd = G.build_group_data(bd, k, ctx=None)['toplam_aktifler']
    t = '2026-06-30'
    tum = sum(v[t] for v in bd['toplam_aktifler'].values())
    assert gd['Tüm Bankalar'][t]['value'] == tum
    en_buyuk20 = sorted(bd['toplam_aktifler'].values(), key=lambda v: -v[t])[:20]
    assert gd['İlk 20 Banka'][t]['value'] == sum(v[t] for v in en_buyuk20)
    assert gd['İlk 20 Banka'][t]['value'] < tum
    rakip = KATALOG['groups']['members']['Rakip Bankalar']
    assert gd['Rakip Bankalar + KT'][t]['value'] == sum(bd['toplam_aktifler'][b][t] for b in ['Kuveyt Türk'] + rakip)
    # panodaki kayıtlı gruplar etkilenmez
    assert 'Rakip Bankalar' in gd and set(gd) >= set(KATALOG['groups']['members'])
    assert 'Tüm Bankalar' not in k['groups']['members']      # catalog'a yazılmaz


def test_odak_degisince_birlesik_grup_adi():
    k = copy.deepcopy(KATALOG)
    k['groups']['focus'] = 'Garanti Bankası'
    assert G.export_grup_adlari(k)[-1] == 'Rakip Bankalar + Garanti'
