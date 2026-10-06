"""Kullanıcı bazlı odak banka + banka adı eşlemesi (2026-10-02).

- 'QNB Finansbank' → 'QNB' (pipeline/banka_adlari.py) giriş noktalarında çevrilir.
- 'odak_banka' izni sonradan eklenen bir izin: mevcut roles.json'daki hazır rollere bir kez eklenir.
- İzni olan kullanıcı kendi odağını seçer; izni olmayan admin varsayılanını görür.
- focus_overlay yalnız odağa bağlı değişen grupları döndürür.
"""
import copy
import json

import pytest
from fastapi import HTTPException

import app as A
import roles as R
import users as U
from pipeline.banka_adlari import kanonik
from pipeline.ingest import parse_filename

from test_focus import KATALOG


def test_kanonik_banka_adi():
    assert kanonik('QNB Finansbank') == 'QNB'
    assert kanonik(' QNB Finansbank ') == 'QNB'
    assert kanonik('Akbank') == 'Akbank'
    # Dosya adı eski adla gelse de kanonik ada çevrilir
    assert parse_filename('QNB Finansbank - 30.06.2026.xlsx') == ('QNB', '2026-06-30')
    assert parse_filename('QNB - 30.06.2026.xlsx') == ('QNB', '2026-06-30')


def test_canli_grup_adlari_kanonik():
    g = {'order': ['Rakip Bankalar'], 'members': {'Rakip Bankalar': ['Akbank', 'QNB Finansbank']},
         'colors': {'Rakip Bankalar': '#B87333'}, 'focus': 'QNB Finansbank',
         'rakip_cikarilan': {'banka': 'QNB Finansbank', 'sira': 3}}
    k = A._groups_kanonik(g)
    assert k['members']['Rakip Bankalar'] == ['Akbank', 'QNB']
    assert k['focus'] == 'QNB' and k['rakip_cikarilan']['banka'] == 'QNB'


def test_ad_degistir_ozyinelemeli():
    veri = {'bank_data': {'x': {'QNB Finansbank': {'2026-06-30': 1.0}}},
            'meta': {'groups': {'Rakip': ['QNB Finansbank', 'Akbank']}, 'not': 'QNB Finansbank metni'}}
    out = A._ad_degistir(veri, {'QNB Finansbank': 'QNB'})
    assert 'QNB' in out['bank_data']['x'] and out['meta']['groups']['Rakip'] == ['QNB', 'Akbank']


def test_odak_izni_hazir_rollere_bir_kez_eklenir(tmp_path):
    p = tmp_path / 'roles.json'
    eski = {'roles': [
        {'id': 'goruntuleyici', 'ad': 'Görüntüleyici', 'izinler': [], 'asistan_gunluk': 0},
        {'id': 'analist', 'ad': 'Analist', 'izinler': ['asistan', 'export_veri'], 'asistan_gunluk': 50},
        {'id': 'ozel', 'ad': 'Özel', 'izinler': ['asistan'], 'asistan_gunluk': 5},
    ]}
    p.write_text(json.dumps(eski), encoding='utf-8')
    R.ensure_roles_file(p)
    roller = {r['id']: r for r in R.list_roles(p)}
    assert 'odak_banka' in roller['analist']['izinler']
    assert 'odak_banka' not in roller['goruntuleyici']['izinler']
    assert 'odak_banka' not in roller['ozel']['izinler']          # özel role kendiliğinden eklenmez
    # Admin izni kaldırırsa geri gelmez
    d = json.loads(p.read_text(encoding='utf-8'))
    for r in d['roles']:
        if r['id'] == 'analist':
            r['izinler'] = [k for k in r['izinler'] if k != 'odak_banka']
    p.write_text(json.dumps(d), encoding='utf-8')
    R.ensure_roles_file(p)
    assert 'odak_banka' not in {r['id']: r for r in R.list_roles(p)}['analist']['izinler']


@pytest.fixture
def ortam(tmp_path, monkeypatch):
    users, roles = tmp_path / 'users.json', tmp_path / 'roles.json'
    U.ensure_users_file(users)
    R.ensure_roles_file(roles)
    monkeypatch.setattr(A, 'DATA_USERS', users)
    monkeypatch.setattr(A, 'DATA_ROLES', roles)
    monkeypatch.setattr(A, '_load_catalog', lambda: copy.deepcopy(KATALOG))
    monkeypatch.setattr(A, '_odak_katman_dosyasi', lambda catalog, banka, rakipler=None: None)   # ağır hesap atlanır
    return users


def _uye(users, email, rol):
    ok, err = U.admin_create_user(users, email.split('@')[0], email, 'parola12345', 'test')
    assert ok, err
    uid = next(u['id'] for u in U.list_users(users) if u['email'] == email)
    assert U.set_role(users, uid, rol)
    return U.get_user_by_id(users, uid)


def test_kullanici_odagi_izne_bagli(ortam):
    users = ortam
    ana = _uye(users, 'a@kuveytturk.com.tr', 'analist')
    gor = _uye(users, 'g@kuveytturk.com.tr', 'goruntuleyici')
    assert A._kullanici_odak(ana) == 'Kuveyt Türk'

    r = A.api_set_odak_banka(A.OdakSecimPayload(banka='Garanti Bankası'), ana)
    assert r['odak_banka'] == 'Garanti Bankası' and r['odak_secili'] == 'Garanti Bankası'
    assert r['rakipler'] == ['Akbank']   # kişisel liste yok → odak bankaya göre otomatik liste
    ana = U.get_user_by_id(users, ana['id'])
    assert A._kullanici_odak(ana) == 'Garanti Bankası'
    # Başka kullanıcı etkilenmez; izni olmayan kayıtlı alanı olsa bile varsayılanı görür
    assert A._kullanici_odak(gor) == 'Kuveyt Türk'
    assert A._kullanici_odak(dict(gor, odak_banka='Garanti Bankası')) == 'Kuveyt Türk'
    with pytest.raises(HTTPException) as e:
        A.require_perm('odak_banka')(gor)
    assert e.value.status_code == 403

    # Bilinmeyen banka reddedilir; varsayılanı seçmek kişisel seçimi temizler
    with pytest.raises(HTTPException):
        A.api_set_odak_banka(A.OdakSecimPayload(banka='Yok Bank'), ana)
    A.api_set_odak_banka(A.OdakSecimPayload(banka='Kuveyt Türk'), ana)
    assert 'odak_banka' not in U.get_user_by_id(users, ana['id'])


def test_focus_overlay_yalniz_degisen_gruplar(monkeypatch):
    import pipeline.groups as G
    import pipeline.composition as C
    from pipeline.focus import focus_overlay

    gorulen = {}

    def sahte_group_data(bank_data, catalog, ctx):
        gorulen['gruplar'] = list(catalog['groups']['members'])
        return {'toplam_aktifler': {g: {'2026-06-30': {'value': 1.0}} for g in catalog['groups']['members']}}

    def sahte_komp(ctx, catalog):
        gorulen['komp_bankalar'] = [b['banka_adi'] for b in catalog['banks']]
        return ({'aktif': {'bank': {'x': {}}, 'group': {g: {} for g in catalog['groups']['members']}}}, {})

    monkeypatch.setattr(G, 'build_group_data', sahte_group_data)
    monkeypatch.setattr(C, 'build_composition_payload', sahte_komp)
    computed = {'bank_data': {'toplam_aktifler': {'Garanti Bankası': {'2026-03-31': 5.0, '2026-06-30': 6.0}}}}
    k = focus_overlay(copy.deepcopy(KATALOG), computed, None, 'Garanti Bankası')

    assert k['meta']['focus_bank'] == 'Garanti Bankası' and k['meta']['default_date'] == '2026-06-30'
    assert set(gorulen['gruplar']) == {'Garanti Bankası', 'Rakip Bankalar', 'Garanti Hariç Mevduat Bankaları'}
    assert set(k['kaldirilan']) == {'Kuveyt Türk', 'KT Hariç Katılım Bankaları'}
    assert set(gorulen['komp_bankalar']) == {'Garanti Bankası', 'Akbank', 'Yapı Kredi'}
    assert list(k['composition_group']['aktif']) and 'bank' not in k['composition_group']['aktif']
    assert k['meta']['groups']['Rakip Bankalar'] == ['Akbank']
