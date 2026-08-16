"""
Auth katmanı testleri (2026-08-15 denetimi #11).

users.py'nin şifre/üyelik mantığını doğrudan test eder (HTTP katmanı olmadan —
httpx/TestClient bağımlılığı istemeden). Kapsam: şifre hash/doğrulama, kayıt
domain kısıtı, onay durumu kapıları, ŞİFRE DEĞİŞTİRME (yeni özellik) ve rol/
durum atama. Bir refactor bu mantığı bozarsa burada kırmızı çıkar.
"""
import json
import pytest

import users as U


@pytest.fixture
def users_file(tmp_path):
    """Boş, izole bir users.json — her test kendi dosyasıyla çalışır."""
    p = tmp_path / 'users.json'
    U.ensure_users_file(p)
    return p


def _approved_member(path, email='ali@kuveytturk.com.tr', pw='parola12345', name='Ali'):
    """Yardımcı: onaylı bir üye oluştur, id'sini döndür."""
    ok, err = U.create_signup(path, name, email, pw)
    assert ok, err
    uid = U.list_users(path)[-1]['id']
    U.set_status(path, uid, 'approved', 'test-admin')
    return uid


# --- Şifre hash/doğrulama ---

def test_hash_roundtrip():
    h = U.hash_password('gizli-parola')
    assert U.verify_password('gizli-parola', h)
    assert not U.verify_password('yanlis', h)


def test_verify_bozuk_hash_false():
    # bcrypt olmayan/bozuk hash → exception yerine False
    assert U.verify_password('x', 'bozuk-hash-degil') is False


# --- Kayıt (create_signup) ---

def test_signup_domain_kisiti(users_file):
    ok, err = U.create_signup(users_file, 'Veli', 'veli@gmail.com', 'parola12345')
    assert not ok and 'kuveytturk.com.tr' in err

    ok, _ = U.create_signup(users_file, 'Veli', 'veli@kuveytturk.com.tr', 'parola12345')
    assert ok


def test_signup_sifre_uzunlugu(users_file):
    ok, err = U.create_signup(users_file, 'Veli', 'veli@kuveytturk.com.tr', 'kisa')
    assert not ok and 'karakter' in err


def test_signup_pending_ve_member(users_file):
    U.create_signup(users_file, 'Veli', 'veli@kuveytturk.com.tr', 'parola12345')
    u = U.list_users(users_file)[-1]
    assert u['status'] == 'pending'
    assert u['role'] == 'member'


def test_signup_mukerrer_email(users_file):
    U.create_signup(users_file, 'Veli', 'veli@kuveytturk.com.tr', 'parola12345')
    ok, err = U.create_signup(users_file, 'Veli2', 'veli@kuveytturk.com.tr', 'parola12345')
    assert not ok and 'zaten' in err


def test_list_users_sifre_hash_sizmaz(users_file):
    U.create_signup(users_file, 'Veli', 'veli@kuveytturk.com.tr', 'parola12345')
    for u in U.list_users(users_file):
        assert 'password_hash' not in u


# --- Giriş (authenticate) ---

def test_authenticate_pending_engelli(users_file):
    U.create_signup(users_file, 'Veli', 'veli@kuveytturk.com.tr', 'parola12345')
    user, err = U.authenticate(users_file, 'veli@kuveytturk.com.tr', 'parola12345')
    assert user is None and 'onay' in err.lower()


def test_authenticate_onayli_basarili(users_file):
    _approved_member(users_file, 'veli@kuveytturk.com.tr', 'parola12345')
    user, err = U.authenticate(users_file, 'veli@kuveytturk.com.tr', 'parola12345')
    assert user is not None and err == ''


def test_authenticate_yanlis_sifre_generic(users_file):
    _approved_member(users_file, 'veli@kuveytturk.com.tr', 'parola12345')
    user, err = U.authenticate(users_file, 'veli@kuveytturk.com.tr', 'yanlis-parola')
    # e-posta enumeration'ı önlemek için "yok" ve "yanlış" aynı mesaj
    assert user is None
    yok, err2 = U.authenticate(users_file, 'olmayan@kuveytturk.com.tr', 'x')
    assert yok is None and err == err2


# --- Şifre değiştirme (change_password — yeni özellik) ---

def test_change_password_yanlis_mevcut(users_file):
    uid = _approved_member(users_file, pw='eskiparola123')
    ok, err = U.change_password(users_file, uid, 'YANLIS', 'yeniparola123')
    assert not ok and 'mevcut' in err.lower()


def test_change_password_kisa_yeni(users_file):
    uid = _approved_member(users_file, pw='eskiparola123')
    ok, err = U.change_password(users_file, uid, 'eskiparola123', 'kisa')
    assert not ok and 'karakter' in err


def test_change_password_basarili_ve_login(users_file):
    email = 'ali@kuveytturk.com.tr'
    uid = _approved_member(users_file, email=email, pw='eskiparola123')
    ok, err = U.change_password(users_file, uid, 'eskiparola123', 'yeniparola456')
    assert ok, err
    # Eski şifre artık çalışmaz, yeni şifre çalışır
    assert U.authenticate(users_file, email, 'eskiparola123')[0] is None
    assert U.authenticate(users_file, email, 'yeniparola456')[0] is not None


def test_change_password_olmayan_kullanici(users_file):
    ok, err = U.change_password(users_file, 9999, 'x', 'yeniparola123')
    assert not ok


# --- Rol / durum ---

def test_set_role(users_file):
    uid = _approved_member(users_file)
    assert U.set_role(users_file, uid, 'admin')
    assert U.get_user_by_id(users_file, uid)['role'] == 'admin'
    assert not U.set_role(users_file, uid, 'gecersiz-rol')


def test_set_status_red(users_file):
    U.create_signup(users_file, 'Veli', 'veli@kuveytturk.com.tr', 'parola12345')
    uid = U.list_users(users_file)[-1]['id']
    U.set_status(users_file, uid, 'rejected', 'admin')
    user, err = U.authenticate(users_file, 'veli@kuveytturk.com.tr', 'parola12345')
    assert user is None and 'reddedildi' in err.lower()


# --- Admin hesabı senkronu (upsert_admin_account) ---

def test_upsert_admin_idempotent_ve_sifre_sync(users_file):
    U.upsert_admin_account(users_file, 'faruk@admin.local', 'Faruk', 'ilk-sifre-123')
    u = next(x for x in U.list_users(users_file) if x['email'] == 'faruk@admin.local')
    assert u['status'] == 'approved' and u['role'] == 'admin'
    # İkinci çağrı yeni şifreyle senkronlar, mükerrer hesap açmaz
    U.upsert_admin_account(users_file, 'faruk@admin.local', 'Faruk', 'yeni-sifre-456')
    admins = [x for x in U.list_users(users_file) if x['email'] == 'faruk@admin.local']
    assert len(admins) == 1
    assert U.authenticate(users_file, 'faruk@admin.local', 'yeni-sifre-456')[0] is not None
