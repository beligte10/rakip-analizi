"""Odak bankaya göre rakip banka önerisi ve rakip listesinin uygulanması (2026-10-03).

- assistant.rakip_oneri: veriden benzerlik skoru + yapay zeka seçimi; model yoksa / geçersiz yanıtta
  benzerlik önerisi. Model yalnız listedeki bankalardan seçebilir.
- Kullanıcı kendi odağı için rakip listesini seçer (users.json 'rakipler'); otomatik listeyle aynıysa tutulmaz.
- Admin odak bankayı değiştirirken rakip listesini de verir.
- Asistan kişisel katmandaki grup üyeliği ve değerlerini kullanır.
"""
import copy
import json

import pytest

import app as A
import roles as R
import users as U
from assistant import llm, rakip_oneri as RO
from assistant.knowledge import Store, View
from pipeline.focus import rakipleri_normalle, set_rakipler

from test_focus import KATALOG

T = '2026-06-30'


def _computed():
    # Garanti ≈ Akbank ≈ Yapı Kredi (büyük, mevduat); Türkiye Finans ≈ Albaraka (küçük, katılım)
    ta = {'Kuveyt Türk': 100, 'Türkiye Finans': 60, 'Albaraka': 40, 'Garanti Bankası': 300,
          'Akbank': 280, 'Yapı Kredi': 290}
    kr = {'Kuveyt Türk': 60, 'Türkiye Finans': 62, 'Albaraka': 58, 'Garanti Bankası': 55, 'Akbank': 50,
          'Yapı Kredi': 54}
    return {'bank_data': {
        'toplam_aktifler': {b: {T: v} for b, v in ta.items()},
        'krediler_ta': {b: {T: v} for b, v in kr.items()},
    }}


def test_benzerlik_ayni_segment_ve_olcek_one_cikar():
    tarih, satir = RO.benzerlik_tablosu(_computed(), KATALOG, 'Albaraka')
    assert tarih == T and satir[0]['banka'] == 'Türkiye Finans'
    assert {r['banka'] for r in satir} == {'Kuveyt Türk', 'Türkiye Finans', 'Garanti Bankası', 'Akbank', 'Yapı Kredi'}
    _, satir = RO.benzerlik_tablosu(_computed(), KATALOG, 'Akbank')
    assert [r['banka'] for r in satir[:2]] == ['Yapı Kredi', 'Garanti Bankası']


def test_model_yoksa_benzerlik_onerisi():
    r = RO.rakip_oner(_computed(), KATALOG, 'Akbank', cfg=None, n=3)
    assert r['kaynak'] == 'benzerlik' and len(r['oneriler']) == 3
    assert r['oneriler'][0]['banka'] == 'Yapı Kredi' and 'benzerlik skoru' in r['oneriler'][0]['gerekce']
    assert 'Akbank' not in [o['banka'] for o in r['oneriler']]


def _sahte_model(monkeypatch, metin):
    def sahte(cfg, messages, tools=None, temperature=0.2):
        sahte.mesajlar = messages
        yield ('content', metin)
    monkeypatch.setattr(llm, 'stream_chat', sahte)
    return sahte


def test_yapay_zeka_onerisi_dogrulanir(monkeypatch):
    sahte = _sahte_model(monkeypatch, '```json\n{"rakipler": [{"banka": "Garanti Bankası", "gerekce": "1,07 kat"}, '
                                      '{"banka": "Uydurma Bank", "gerekce": "x"}, {"banka": "Akbank", "gerekce": "aynı"}, '
                                      '{"banka": "Kuveyt Türk", "gerekce": "katılım"}, {"banka": "Akbank", "gerekce": "tekrar"}]}\n```')
    r = RO.rakip_oner(_computed(), KATALOG, 'Yapı Kredi', cfg=llm.LLMConfig(api_key='x'), n=3)
    assert r['kaynak'] == 'yapay_zeka'
    assert [o['banka'] for o in r['oneriler']] == ['Garanti Bankası', 'Akbank', 'Kuveyt Türk']   # uydurma/tekrar atılır
    assert r['oneriler'][0]['gerekce'] == '1,07 kat' and r['oneriler'][0]['skor'] is not None
    istek = sahte.mesajlar[-1]['content']
    assert 'Odak banka: Yapı Kredi' in istek and '| Garanti Bankası |' in istek


def test_gecersiz_model_yanitinda_benzerlige_duser(monkeypatch):
    _sahte_model(monkeypatch, 'Önerim: Garanti ve Akbank.')
    r = RO.rakip_oner(_computed(), KATALOG, 'Yapı Kredi', cfg=llm.LLMConfig(api_key='x'), n=3)
    assert r['kaynak'] == 'benzerlik' and r['uyari'] and len(r['oneriler']) == 3


def test_model_hatasinda_benzerlige_duser(monkeypatch):
    def boom(*a, **k):
        raise llm.LLMError('Yapay zeka servisine ulaşılamadı.')
        yield  # noqa
    monkeypatch.setattr(llm, 'stream_chat', boom)
    r = RO.rakip_oner(_computed(), KATALOG, 'Akbank', cfg=llm.LLMConfig(api_key='x'), n=3, anahtar='v1')
    assert r['kaynak'] == 'benzerlik' and 'ulaşılamadı' in r['uyari']
    assert ('Akbank', 3, 'v1', True, 'tr') not in RO._onbellek   # geçici hata önbelleğe alınmaz


def test_rakip_listesi_normallestirilir_ve_uygulanir():
    k = copy.deepcopy(KATALOG)
    assert rakipleri_normalle(k, 'Kuveyt Türk', ['Akbank', 'Kuveyt Türk', 'Yok Bank', 'Akbank', 'Albaraka']) \
        == ['Akbank', 'Albaraka']
    assert rakipleri_normalle(k, 'Kuveyt Türk', []) is None
    k['groups']['rakip_cikarilan'] = {'banka': 'Kuveyt Türk', 'sira': 0}
    assert set_rakipler(k, ['Albaraka', 'Türkiye Finans'])
    assert k['groups']['members']['Rakip Bankalar'] == ['Albaraka', 'Türkiye Finans']
    assert 'rakip_cikarilan' not in k['groups']
    assert set_rakipler(k, ['Albaraka', 'Türkiye Finans']) == []   # aynı liste → değişiklik yok


@pytest.fixture
def ortam(tmp_path, monkeypatch):
    users, roles = tmp_path / 'users.json', tmp_path / 'roles.json'
    U.ensure_users_file(users)
    R.ensure_roles_file(roles)
    monkeypatch.setattr(A, 'DATA_USERS', users)
    monkeypatch.setattr(A, 'DATA_ROLES', roles)
    katalog = copy.deepcopy(KATALOG)
    monkeypatch.setattr(A, '_load_catalog', lambda: copy.deepcopy(katalog))
    cagri = []
    monkeypatch.setattr(A, '_odak_katman_dosyasi', lambda catalog, banka, rakipler=None: cagri.append((banka, rakipler)))
    ok, err = U.admin_create_user(users, 'a', 'a@kuveytturk.com.tr', 'parola12345', 'test')
    uid = next(u['id'] for u in U.list_users(users) if u['email'] == 'a@kuveytturk.com.tr')
    U.set_role(users, uid, 'analist')
    return users, uid, cagri


def test_kullanici_rakip_listesi(ortam):
    users, uid, cagri = ortam
    u = U.get_user_by_id(users, uid)
    r = A.api_set_odak_banka(A.OdakSecimPayload(banka='Albaraka', rakipler=['Türkiye Finans', 'Kuveyt Türk', 'Albaraka']), u)
    assert r['rakipler'] == ['Türkiye Finans', 'Kuveyt Türk']   # odak listeden çıkarılır
    u = U.get_user_by_id(users, uid)
    assert u['rakipler'] == ['Türkiye Finans', 'Kuveyt Türk']
    assert A._kullanici_rakipler(u, A._load_catalog()) == ['Türkiye Finans', 'Kuveyt Türk']
    assert cagri[-1] == ('Albaraka', ['Türkiye Finans', 'Kuveyt Türk'])

    # Otomatik listeyle aynı seçim ayrıca tutulmaz
    r = A.api_set_odak_banka(A.OdakSecimPayload(banka='Albaraka', rakipler=['Garanti Bankası', 'Akbank']), u)
    assert 'rakipler' not in U.get_user_by_id(users, uid) and r['rakipler'] == ['Garanti Bankası', 'Akbank']

    # Varsayılan odakta da kişisel rakip listesi tutulabilir → katman üretilir
    A.api_set_odak_banka(A.OdakSecimPayload(banka='Kuveyt Türk', rakipler=['Albaraka']), U.get_user_by_id(users, uid))
    u = U.get_user_by_id(users, uid)
    assert 'odak_banka' not in u and u['rakipler'] == ['Albaraka']
    assert cagri[-1] == ('Kuveyt Türk', ['Albaraka'])


def test_admin_odak_ile_rakipleri_uygular(monkeypatch):
    katalog = copy.deepcopy(KATALOG)
    kayit = {}
    monkeypatch.setattr(A, '_load_catalog', lambda: katalog)
    monkeypatch.setattr(A, '_save_catalog', lambda c: kayit.setdefault('catalog', c))
    monkeypatch.setattr(A, '_recompute_groups_and_save', lambda c: kayit.setdefault('recompute', True))
    r = A.admin_set_focus_bank(A.FocusBankPayload(bank='Albaraka', rakipler=['Türkiye Finans', 'Kuveyt Türk']), 'admin')
    g = kayit['catalog']['groups']
    assert g['focus'] == 'Albaraka' and g['members']['Rakip Bankalar'] == ['Türkiye Finans', 'Kuveyt Türk']
    assert kayit['recompute'] and any('Rakip Bankalar' in x for x in r['degisiklikler'])

    # Odak aynı, yalnız rakip listesi değişir → yine kaydedilip yeniden hesaplanır
    kayit.clear()
    r = A.admin_set_focus_bank(A.FocusBankPayload(bank='Albaraka', rakipler=['Kuveyt Türk']), 'admin')
    assert r['degisti'] and kayit['catalog']['groups']['members']['Rakip Bankalar'] == ['Kuveyt Türk']


def test_asistan_kisisel_katmani_kullanir(tmp_path):
    computed = {'meta': {'dates': [T], 'default_date': T, 'group_order': ['Rakip Bankalar']},
                'bank_data': {}, 'group_data': {'roae': {'Rakip Bankalar': {T: {'value': 20.0}}}}}
    katalog = {'banks': KATALOG['banks'], 'groups': KATALOG['groups'],
               'measures': [{'id': 'roae', 'ad': 'ROAE', 'tip': 'rasyo', 'birim': '%'}]}
    (tmp_path / 'c.json').write_text(json.dumps(computed), encoding='utf-8')
    (tmp_path / 'k.json').write_text(json.dumps(katalog), encoding='utf-8')
    (tmp_path / 'i.md').write_text('', encoding='utf-8')
    store = Store(tmp_path / 'c.json', tmp_path / 'k.json', tmp_path / 'i.md').refresh()
    ortak = View(store)
    assert ortak.value('roae', 'grup', 'Rakip Bankalar', T) == 20.0
    katman = {'meta': {'groups': dict(KATALOG['groups']['members'], **{'Rakip Bankalar': ['Albaraka']}),
                       'group_order': ['Albaraka', 'Rakip Bankalar']},
              'group_data': {'roae': {'Rakip Bankalar': {T: {'value': 31.5}}}}}
    kisisel = View(store, None, katman)
    assert kisisel.value('roae', 'grup', 'Rakip Bankalar', T) == 31.5
    assert kisisel.group_members['Rakip Bankalar'] == ['Albaraka'] and kisisel.group_order[0] == 'Albaraka'


def test_cince_karakterler_temizlenir(monkeypatch):
    _sahte_model(monkeypatch, '{"rakipler": [{"banka": "Garanti Bankası", "gerekce": "stratejik对标 sağlar"}, '
                              '{"banka": "Akbank", "gerekce": "a"}, {"banka": "Kuveyt Türk", "gerekce": "b"}]}')
    r = RO.rakip_oner(_computed(), KATALOG, 'Yapı Kredi', cfg=llm.LLMConfig(api_key='x'), n=3)
    assert r['oneriler'][0]['gerekce'] == 'stratejik sağlar'
    assert llm.cjk_temizle('NIM对标 %6,32') == 'NIM %6,32' and llm.cjk_temizle('Şube ağı') == 'Şube ağı'
