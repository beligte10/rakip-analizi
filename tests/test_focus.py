"""Odak banka (2026-10-01): grup yapısı dönüşümü + admin uç noktaları (HTTP'siz, sahte katalogla)."""
import copy
import json

import pytest
from fastapi import HTTPException

import app as A
from pipeline.focus import apply_focus_bank, focus_of, kisa_ad

KATALOG = {
    'banks': [{'banka_adi': b, 'tur': t} for b, t in [
        ('Kuveyt Türk', 'Katılım'), ('Türkiye Finans', 'Katılım'), ('Albaraka', 'Katılım'),
        ('Garanti Bankası', 'Mevduat'), ('Akbank', 'Mevduat'), ('Yapı Kredi', 'Mevduat')]],
    'groups': {
        'order': ['Kuveyt Türk', 'Mevduat Bankaları', 'Rakip Bankalar', 'Katılım Bankaları', 'KT Hariç Katılım Bankaları'],
        'members': {
            'Kuveyt Türk': ['Kuveyt Türk'],
            'Mevduat Bankaları': ['Garanti Bankası', 'Akbank', 'Yapı Kredi'],
            'Rakip Bankalar': ['Garanti Bankası', 'Akbank'],
            'Katılım Bankaları': ['Kuveyt Türk', 'Türkiye Finans', 'Albaraka'],
            'KT Hariç Katılım Bankaları': ['Türkiye Finans', 'Albaraka'],
        },
        'colors': {'Kuveyt Türk': '#559D87', 'Mevduat Bankaları': '#2C3E50', 'Rakip Bankalar': '#B87333',
                   'Katılım Bankaları': '#7c3aed', 'KT Hariç Katılım Bankaları': '#DB2777'},
    },
}


def test_varsayilan_odak_kuveyt_turk():
    assert focus_of(KATALOG) == 'Kuveyt Türk'
    assert focus_of({}) == 'Kuveyt Türk'
    assert kisa_ad('Kuveyt Türk') == 'KT' and kisa_ad('Garanti Bankası') == 'Garanti' and kisa_ad('Halk Bank') == 'Halk'


def test_mevduat_bankasi_odak():
    k = copy.deepcopy(KATALOG)
    r = apply_focus_bank(k, 'Garanti Bankası')
    g = k['groups']
    assert r['degisti'] and r['onceki'] == 'Kuveyt Türk' and g['focus'] == 'Garanti Bankası'
    assert g['order'] == ['Garanti Bankası', 'Mevduat Bankaları', 'Rakip Bankalar', 'Katılım Bankaları',
                          'Garanti Hariç Mevduat Bankaları']                       # sıra korunur
    assert g['members']['Garanti Bankası'] == ['Garanti Bankası']
    assert g['members']['Garanti Hariç Mevduat Bankaları'] == ['Akbank', 'Yapı Kredi']
    assert g['members']['Rakip Bankalar'] == ['Akbank']                            # odak rakipten çıkar
    assert 'Kuveyt Türk' not in g['members'] and 'KT Hariç Katılım Bankaları' not in g['members']
    assert g['colors']['Garanti Bankası'] == '#559D87'                              # odak grubu rengini korur
    assert set(g['order']) == set(g['members']) == set(g['colors'])


def test_katilim_bankasi_odak_ve_geri_donus():
    k = copy.deepcopy(KATALOG)
    apply_focus_bank(k, 'Türkiye Finans')
    g = k['groups']
    assert g['members']['Türkiye Finans Hariç Katılım Bankaları'] == ['Kuveyt Türk', 'Albaraka']
    assert g['members']['Rakip Bankalar'] == ['Garanti Bankası', 'Akbank']
    apply_focus_bank(k, 'Kuveyt Türk')
    assert k['groups']['order'] == KATALOG['groups']['order']
    assert k['groups']['members']['KT Hariç Katılım Bankaları'] == ['Türkiye Finans', 'Albaraka']


def test_ayni_banka_degisiklik_yapmaz_ve_hatalar():
    k = copy.deepcopy(KATALOG)
    assert apply_focus_bank(k, 'Kuveyt Türk') == {'degisti': False, 'odak': 'Kuveyt Türk'}
    assert k['groups'] == KATALOG['groups']
    with pytest.raises(ValueError):
        apply_focus_bank(k, 'Olmayan Banka')
    k['groups']['members']['Akbank'] = ['Akbank']                                  # çakışan grup adı
    k['groups']['order'].append('Akbank')
    with pytest.raises(ValueError):
        apply_focus_bank(k, 'Akbank')


def test_admin_uc_noktalari(tmp_path, monkeypatch):
    kat = tmp_path / 'catalog.json'
    kat.write_text(json.dumps(copy.deepcopy(KATALOG)), encoding='utf-8')
    monkeypatch.setattr(A, 'DATA_CATALOG', kat)
    cagri = []
    monkeypatch.setattr(A, '_recompute_groups_and_save', lambda c: cagri.append(c['groups']['focus']))
    liste = A.admin_list_groups('x')
    assert liste['focus'] == 'Kuveyt Türk' and liste['protected'] == ['Kuveyt Türk']
    sonuc = A.admin_set_focus_bank(A.FocusBankPayload(bank='Garanti Bankası'), 'x')
    assert sonuc['odak'] == 'Garanti Bankası' and cagri == ['Garanti Bankası']
    assert A.admin_list_groups('x')['protected'] == ['Garanti Bankası']
    with pytest.raises(HTTPException) as e:                                         # odak grup silinemez
        A.admin_delete_group('Garanti Bankası', 'x')
    assert e.value.status_code == 400
    A.admin_delete_group('Rakip Bankalar', 'x')                                     # diğer gruplar silinebilir
    with pytest.raises(HTTPException) as e:
        A.admin_set_focus_bank(A.FocusBankPayload(bank='Yok'), 'x')
    assert e.value.status_code == 400
    assert len(cagri) == 2                                                          # (odak + silme) — yok için çağrılmadı


def test_rakip_grubu_gidis_donusle_ayni_kalir():
    k = copy.deepcopy(KATALOG)
    ilk = list(k['groups']['members']['Rakip Bankalar'])
    apply_focus_bank(k, 'Garanti Bankası')
    assert 'Garanti Bankası' not in k['groups']['members']['Rakip Bankalar']
    r = apply_focus_bank(k, 'Kuveyt Türk')
    assert k['groups']['members']['Rakip Bankalar'] == ilk
    assert 'rakip_cikarilan' not in k['groups']
    assert any('geri eklendi' in x for x in r['degisiklikler'])
