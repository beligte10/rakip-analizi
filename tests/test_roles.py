"""Rol bazlı erişim (2026-09-30): roles.py mantığı + app.py izin kapıları.
HTTP katmanı olmadan — bağımlılık fonksiyonları sahte istekle çağrılır."""
import json

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import app as A
import roles as R
import users as U


@pytest.fixture
def ortam(tmp_path, monkeypatch):
    users, roles = tmp_path / 'users.json', tmp_path / 'roles.json'
    U.ensure_users_file(users)
    R.ensure_roles_file(roles)
    monkeypatch.setattr(A, 'DATA_USERS', users)
    monkeypatch.setattr(A, 'DATA_ROLES', roles)
    return users, roles


def _uye(users, email, rol):
    ok, err = U.admin_create_user(users, email.split('@')[0], email, 'parola12345', 'test')
    assert ok, err
    uid = next(u['id'] for u in U.list_users(users) if u['email'] == email)
    assert U.set_role(users, uid, rol)
    return uid


def _istek(uid=None):
    return Request({'type': 'http', 'headers': [], 'session': {'user_id': uid} if uid else {}})


def test_hazir_roller_ve_varsayilan(ortam):
    _, roles = ortam
    ids = [r['id'] for r in R.list_roles(roles)]
    assert ids == ['goruntuleyici', 'analist', 'veri_yoneticisi', 'admin']
    assert R.get_role(roles, 'goruntuleyici')['izinler'] == []
    assert set(R.get_role(roles, 'admin')['izinler']) == set(R.IZIN_ANAHTARLARI)
    assert R.resolve_id(roles, 'member') == 'goruntuleyici'        # eski kayıt
    assert R.resolve_id(roles, 'silinmis_rol') == 'goruntuleyici'


def test_eski_member_kaydi_goruntuleyici_okunur(ortam):
    users, _ = ortam
    users.write_text(json.dumps({'users': [{'id': 1, 'name': 'X', 'email': 'x@kuveytturk.com.tr',
                                            'password_hash': 'h', 'status': 'approved', 'role': 'member'},
                                           {'id': 2, 'name': 'Y', 'email': 'y@kuveytturk.com.tr',
                                            'password_hash': 'h', 'status': 'approved'}]}))
    assert [u['role'] for u in U.list_users(users)] == ['goruntuleyici', 'goruntuleyici']


def test_rol_olustur_guncelle_sil(ortam):
    users, roles = ortam
    role, err = R.create_role(roles, 'Şube Analisti', ['asistan', 'export_gorsel'], 20)
    assert not err and role['id'] == 'sube_analisti'
    assert R.create_role(roles, 'şube analisti', [], 0)[1] == 'Bu adla bir rol zaten var'
    assert R.create_role(roles, 'Y', ['uydurma'], 0)[1] == 'Geçersiz izin'
    assert 'arasında' in R.create_role(roles, 'Z', [], 99999)[1]
    role, err = R.update_role(roles, 'sube_analisti', 'Şube Analisti', ['asistan'], 5)
    assert role['izinler'] == ['asistan'] and role['asistan_gunluk'] == 5
    uid = _uye(users, 'a@kuveytturk.com.tr', 'sube_analisti')
    assert not R.delete_role(roles, 'sube_analisti', U.count_by_role(users).get('sube_analisti', 0))[0]
    U.set_role(users, uid, 'analist')
    assert R.delete_role(roles, 'sube_analisti', 0) == (True, '')
    assert R.delete_role(roles, 'analist', 0) == (False, 'Hazır roller silinemez')


def test_admin_izinleri_kilitli(ortam):
    _, roles = ortam
    role, _ = R.update_role(roles, 'admin', 'Admin', [], 10)
    assert set(role['izinler']) == set(R.IZIN_ANAHTARLARI) and role['asistan_gunluk'] == 10


def test_uye_izin_kapisi(ortam):
    users, _ = ortam
    gor = U.get_user_by_id(users, _uye(users, 'g@kuveytturk.com.tr', 'goruntuleyici'))
    ana = U.get_user_by_id(users, _uye(users, 'a@kuveytturk.com.tr', 'analist'))
    dep = A.require_perm('asistan')
    assert dep(ana) is ana
    with pytest.raises(HTTPException) as e:
        dep(gor)
    assert e.value.status_code == 403


def test_admin_paneli_izin_kapisi(ortam):
    users, _ = ortam
    gor = _uye(users, 'g@kuveytturk.com.tr', 'goruntuleyici')
    vy = _uye(users, 'v@kuveytturk.com.tr', 'veri_yoneticisi')
    veri = A.require_admin_perm('admin_veri')
    kul = A.require_admin_perm('admin_kullanicilar')
    assert veri(_istek(vy), None) == 'v@kuveytturk.com.tr'
    with pytest.raises(HTTPException) as e:
        kul(_istek(vy), None)
    assert e.value.status_code == 403
    with pytest.raises(HTTPException) as e:
        A.require_admin_access(_istek(gor), None)          # hiç admin izni yok
    assert e.value.status_code == 403
    with pytest.raises(HTTPException) as e:
        veri(_istek(), None)                                  # oturum yok → Basic Auth iste
    assert e.value.status_code == 401


def test_yetki_yukseltme_engellenir(ortam, monkeypatch):
    users, roles = ortam
    R.create_role(roles, 'Kullanıcı Sorumlusu', ['admin_kullanicilar'], 0)
    sor = _uye(users, 's@kuveytturk.com.tr', 'kullanici_sorumlusu')
    hedef = _uye(users, 'h@kuveytturk.com.tr', 'goruntuleyici')
    adm = _uye(users, 'ad@kuveytturk.com.tr', 'admin')
    ben = 's@kuveytturk.com.tr'
    # kendinden geniş rol atayamaz
    with pytest.raises(HTTPException) as e:
        A.admin_set_user_role(hedef, A.RolePayload(role='admin'), ben)
    assert e.value.status_code == 403
    # daha geniş yetkili kullanıcıya dokunamaz
    with pytest.raises(HTTPException):
        A.admin_reject_user(adm, ben)
    # kendi rolünü değiştiremez
    with pytest.raises(HTTPException) as e:
        A.admin_set_user_role(sor, A.RolePayload(role='goruntuleyici'), ben)
    assert e.value.status_code == 400
    # kendinden geniş rol tanımlayamaz
    with pytest.raises(HTTPException):
        A.admin_create_role(A.RoleDefPayload(ad='Süper', izinler=['admin_veri'], asistan_gunluk=0), ben)
    # kendi izinleri içinde kalan atama serbest
    assert A.admin_set_user_role(hedef, A.RolePayload(role='goruntuleyici'), ben) == {'status': 'ok'}


def test_basic_auth_koku_tum_izinler(ortam):
    assert A.identity_perms(A.USERNAME) == set(R.IZIN_ANAHTARLARI)


def test_asistan_gunluk_siniri_rolden(monkeypatch):
    monkeypatch.setattr(A, '_chat_calls', {})
    monkeypatch.setattr(A, 'CHAT_PER_MIN', 100)
    assert A._chat_rate_error(7, 2) is None
    assert A._chat_rate_error(7, 2) is None
    assert '2 soru' in A._chat_rate_error(7, 2)
    assert A._chat_rate_error(8, 0) is not None           # sınır 0 → asistan kapalı


def test_dis_veri_izni_yoksa_evds_araclari_yok(monkeypatch):
    from assistant import tools as T
    monkeypatch.setenv('EVDS_API_KEY', 'x')
    adlar = lambda specs: {s['function']['name'] for s in specs}
    assert 'evds_veri' in adlar(T.active_specs(True))
    assert 'evds_veri' not in adlar(T.active_specs(False))
    r, _ = T.execute(None, 'evds_ara', '{"query": "kur"}', dis_veri=False)
    assert 'kapalı' in r['hata']


# --- Rekabet Analizi ölçüleri rol izni (2026-10-06) ---------------------------------------------
def test_rekabet_izni_hazir_roller(ortam):
    _, roles = ortam
    assert 'rekabet_analizi' in R.IZIN_ANAHTARLARI
    assert 'rekabet_analizi' not in R.get_role(roles, 'goruntuleyici')['izinler']
    for rid in ('analist', 'veri_yoneticisi', 'admin'):
        assert 'rekabet_analizi' in R.get_role(roles, rid)['izinler']


def test_rekabet_izni_mevcut_roles_json_e_eklenir(tmp_path):
    """İzinden önce yazılmış roles.json'daki hazır roller varsayılan izni bir kez alır; özel rol almaz."""
    yol = tmp_path / 'roles.json'
    bilinen = [k for k in R.IZIN_ANAHTARLARI if k != 'rekabet_analizi']
    yol.write_text(json.dumps({'bilinen_izinler': bilinen, 'roles': [
        {'id': 'analist', 'ad': 'Analist', 'izinler': ['asistan'], 'asistan_gunluk': 50},
        {'id': 'ozel', 'ad': 'Özel', 'izinler': ['asistan'], 'asistan_gunluk': 5}]}), encoding='utf-8')
    assert 'rekabet_analizi' in R.get_role(yol, 'analist')['izinler']
    assert 'rekabet_analizi' not in R.get_role(yol, 'ozel')['izinler']


def test_olcu_filtrele_rekabet_olculerini_cikarir():
    from pipeline.rekabet_olculer import IDS
    veri = {'catalog': [{'id': 'krediler'}, {'id': IDS[0]}], 'bank_data': {'krediler': {}, IDS[0]: {}, IDS[1]: {}},
            'group_data': {IDS[0]: {}, 'krediler': {}}, 'meta': {'available_measures': ['krediler', IDS[0]], 'x': 1}}
    out = A._olcu_filtrele(veri, frozenset(IDS))
    assert [m['id'] for m in out['catalog']] == ['krediler']
    assert list(out['bank_data']) == ['krediler'] and list(out['group_data']) == ['krediler']
    assert out['meta'] == {'available_measures': ['krediler'], 'x': 1}
    assert IDS[0] in veri['bank_data']                     # özgün nesne değişmez


def test_gizli_olculer_izne_bagli(ortam):
    users, roles = ortam
    from pipeline.rekabet_olculer import IDS
    g = U.list_users(users)  # noqa: F841
    uid_g = _uye(users, 'g@kuveytturk.com.tr', 'goruntuleyici')
    uid_a = _uye(users, 'a@kuveytturk.com.tr', 'analist')
    kullanici = lambda uid: next(u for u in U.list_users(users) if u['id'] == uid)  # noqa: E731
    assert A._gizli_olculer(kullanici(uid_g)) == frozenset(IDS)
    assert A._gizli_olculer(kullanici(uid_a)) == frozenset()


def test_asistan_gorunumu_gizli_olcuyu_bilmez(monkeypatch):
    from assistant.knowledge import View, Store
    from pipeline.rekabet_olculer import IDS
    import app as A2
    store = Store(A2.DATA_COMPUTED, A2.DATA_CATALOG, A2.MEASURE_INFO_MD) if hasattr(Store, '__init__') else None
    if store is None or not A2.DATA_COMPUTED.exists():
        pytest.skip('veri yok')
    store.refresh()
    tam, kisitli = View(store), View(store, gizli_olculer=IDS)
    assert tam.meta('zk_surukleme') is not None
    assert kisitli.meta('zk_surukleme') is None
    assert kisitli.resolve_measure('zk_surukleme') is None
    assert all(r['id'] not in IDS for r in kisitli.search('zorunlu karşılık sürüklemesi tufex lcr', 15))
