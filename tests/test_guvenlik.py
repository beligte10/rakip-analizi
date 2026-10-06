"""Güvenlik katmanı testleri (2026-10-04 denetimi): hız sınırları, Origin denetimi, güvenlik başlıkları,
varsayılan şifre, ZIP bombası, yükleme sınırları, zamanlama ve bilgi sızıntısı."""
import io
import time
import zipfile
from types import SimpleNamespace

import pytest

import security as S


# --- RateLimiter ---

def test_hiz_siniri_pencere_ve_sifirlama():
    rl = S.RateLimiter(3, 0.3)
    for _ in range(3):
        assert rl.izinli('a')
        rl.hata('a')
    assert not rl.izinli('a') and rl.izinli('b')       # anahtar başına
    time.sleep(0.35)
    assert rl.izinli('a')                               # pencere geçince açılır
    rl.hata('a'); rl.hata('a'); rl.hata('a')
    rl.sifirla('a')
    assert rl.izinli('a')


def test_hiz_siniri_bellek_sinirli():
    rl = S.RateLimiter(5, 60, en_cok_anahtar=50)
    for i in range(500):
        rl.hata(f'ip{i}')
    assert len(rl._d) <= 51


# --- IP ve Origin ---

def _req(headers=None, host='127.0.0.1'):
    return SimpleNamespace(headers={k.lower(): v for k, v in (headers or {}).items()}, client=SimpleNamespace(host=host))


def test_client_ip_proxy_arkasinda_son_girdi():
    r = _req({'X-Forwarded-For': '6.6.6.6, 10.0.0.9'})
    assert S.client_ip(r, True) == '10.0.0.9'           # ilk girdi sahtelenebilir, son girdi proxy'nin
    assert S.client_ip(r, False) == '127.0.0.1'         # proxy yoksa başlığa güvenilmez


def test_origin_denetimi():
    assert S.origin_ok(_req({'Host': 'kt.example', 'Origin': 'https://kt.example'}))
    assert not S.origin_ok(_req({'Host': 'kt.example', 'Origin': 'https://evil.example'}))
    assert not S.origin_ok(_req({'Host': 'kt.example', 'Origin': 'null'}))
    assert S.origin_ok(_req({'Host': 'internal:7860', 'X-Forwarded-Host': 'kt.example', 'Origin': 'https://kt.example'}))
    assert not S.origin_ok(_req({'Host': 'kt.example', 'Referer': 'https://evil.example/x'}))
    assert S.origin_ok(_req({'Host': 'kt.example'}))     # başlık yok (curl / sunucu-sunucu)


# --- Kimlik bilgisi ---

def test_varsayilan_sifre_yok():
    k, s, rastgele = S.kimlik_bilgisi_coz(None, None, production=False)
    assert rastgele and len(s) >= 20 and k == 'admin'
    assert S.kimlik_bilgisi_coz('faruk', 'faruk123', production=False)[2] is True     # bilinen zayıf değer reddedilir
    with pytest.raises(RuntimeError):
        S.kimlik_bilgisi_coz('faruk', None, production=True)
    with pytest.raises(RuntimeError):
        S.kimlik_bilgisi_coz('faruk', 'faruk123', production=True)
    assert S.kimlik_bilgisi_coz('faruk', 'cok-guclu-bir-sifre-42', production=True) == ('faruk', 'cok-guclu-bir-sifre-42', False)


# --- ZIP ---

def _zip(girisler, sikistir=zipfile.ZIP_DEFLATED):
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w', sikistir) as z:
        for ad, veri in girisler:
            z.writestr(ad, veri)
    return zipfile.ZipFile(io.BytesIO(b.getvalue()))


def test_zip_guvenli():
    assert S.zip_guvenli(_zip([('a/x.xlsx', b'abc' * 1000)]), 10 ** 6, 10 ** 7) is None
    assert 'çok büyük' in S.zip_guvenli(_zip([('a/x.xlsx', b'x' * 5000)]), 1000, 10 ** 7)
    assert 'toplamda' in S.zip_guvenli(_zip([('a/1.xlsx', b'x' * 600), ('a/2.xlsx', b'y' * 600)]), 1000, 1000)
    bomba = _zip([('a/bomba.xlsx', b'\0' * (50 * 1024 * 1024))])          # ~50 MB sıfır → çok yüksek oran
    assert 'sıkıştırma' in S.zip_guvenli(bomba, 10 ** 9, 10 ** 10)


# --- Uç noktalar (gerçek yerel uvicorn sunucusu + standart kütüphane istemcisi; httpx gerekmez) ---

class _Istemci:
    def __init__(self, port):
        self.port, self.cerez = port, {}

    def __call__(self, yontem, yol, json_=None, basliklar=None, auth=None):
        import base64
        import http.client
        import json as _json
        b = dict(basliklar or {})
        veri = None
        if json_ is not None:
            veri = _json.dumps(json_).encode()
            b['Content-Type'] = 'application/json'
        if auth:
            b['Authorization'] = 'Basic ' + base64.b64encode(f'{auth[0]}:{auth[1]}'.encode('utf-8')).decode()
        if self.cerez:
            b['Cookie'] = '; '.join(f'{k}={v}' for k, v in self.cerez.items())
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=20)
        c.request(yontem, yol, body=veri, headers=b)
        r = c.getresponse()
        govde = r.read()
        for k, v in r.getheaders():
            if k.lower() == 'set-cookie':
                ad, _, deger = v.split(';')[0].partition('=')
                self.cerez[ad] = deger
        c.close()
        try:
            js = _json.loads(govde)
        except ValueError:
            js = None
        return SimpleNamespace(status_code=r.status, headers={k.lower(): v for k, v in r.getheaders()}, json=lambda: js)

    def get(self, yol, **kw):
        return self('GET', yol, **kw)

    def post(self, yol, json=None, **kw):
        return self('POST', yol, json_=json, **kw)


@pytest.fixture
def istemci(tmp_path, monkeypatch):
    import socket
    import threading
    import uvicorn
    import app as A
    import users as U
    import roles as R
    users, roles = tmp_path / 'users.json', tmp_path / 'roles.json'
    U.ensure_users_file(users)
    R.ensure_roles_file(roles)
    monkeypatch.setattr(A, 'DATA_USERS', users)
    monkeypatch.setattr(A, 'DATA_ROLES', roles)
    for rl in (A._RL_BASIC, A._RL_LOGIN_IP, A._RL_SIGNUP_IP):
        rl._d.clear()
    A._login_attempts.clear()
    with socket.socket() as sk:
        sk.bind(('127.0.0.1', 0))
        port = sk.getsockname()[1]
    sunucu = uvicorn.Server(uvicorn.Config(A.app, host='127.0.0.1', port=port, log_level='error'))
    t = threading.Thread(target=sunucu.run, daemon=True)
    t.start()
    for _ in range(100):
        if sunucu.started:
            break
        time.sleep(0.05)
    yield _Istemci(port), A, U, users
    sunucu.should_exit = True
    t.join(5)


def test_guvenlik_basliklari(istemci):
    c, A, *_ = istemci
    r = c.get('/healthz')
    assert r.headers['x-content-type-options'] == 'nosniff' and r.headers['x-frame-options'] == 'DENY'
    assert "frame-ancestors 'none'" in r.headers['content-security-policy']
    assert 'referrer-policy' in r.headers


def test_bilgi_sizintisi_yok(istemci):
    c, *_ = istemci
    assert 'data_dir' not in c.get('/healthz').json()
    assert 'data_dir' not in c.get('/api/version').json()


def test_origin_baska_siteden_post_reddedilir(istemci):
    c, *_ = istemci
    r = c.post('/api/login', json={'email': 'a@b.c', 'password': 'x'}, basliklar={'Origin': 'https://evil.example'})
    assert r.status_code == 403
    r = c.post('/api/login', json={'email': 'a@b.c', 'password': 'x'}, basliklar={'Origin': f'http://127.0.0.1:{c.port}'})
    assert r.status_code == 401        # kendi sitesinden gelen istek normal işlenir


def test_giris_ip_siniri_farkli_epostalarla(istemci):
    c, A, *_ = istemci
    for i in range(A._RL_LOGIN_IP.limit):
        assert c.post('/api/login', json={'email': f'k{i}@kuveytturk.com.tr', 'password': 'yanlis'}).status_code == 401
    r = c.post('/api/login', json={'email': 'yeni@kuveytturk.com.tr', 'password': 'yanlis'})
    assert r.status_code == 429


def test_signup_sel_korumasi(istemci):
    c, A, *_ = istemci
    kodlar = [c.post('/api/signup', json={'name': 'A', 'email': f'u{i}@gmail.com', 'password': 'parola12345'}).status_code
              for i in range(A._RL_SIGNUP_IP.limit + 2)]
    assert kodlar[-1] == 429 and kodlar[0] == 400


def test_admin_basic_auth_kaba_kuvvet_siniri(istemci):
    c, A, *_ = istemci
    for _ in range(A._RL_BASIC.limit):
        assert c.get('/api/admin/coverage', auth=('admin', 'yanlis')).status_code == 401
    # doğru şifre bile sınır dolunca denenemez
    assert c.get('/api/admin/coverage', auth=(A.USERNAME, A.PASSWORD)).status_code == 429


def test_basic_auth_ascii_disi_500_vermez(istemci):
    c, *_ = istemci
    assert c.get('/api/admin/coverage', auth=('kullanıcı', 'şifre')).status_code == 401


def test_giriste_oturum_temizlenir_ve_calisir(istemci):
    c, A, U, users = istemci
    ok, err = U.admin_create_user(users, 'Ali', 'ali@kuveytturk.com.tr', 'parola12345', 'test')
    assert ok, err
    r = c.post('/api/login', json={'email': 'ali@kuveytturk.com.tr', 'password': 'parola12345'})
    assert r.status_code == 200
    assert c.get('/api/me').status_code == 200


def test_kullanici_yok_ile_yanlis_sifre_ayni_yanit_ve_benzer_sure(tmp_path):
    import users as U
    p = tmp_path / 'u.json'
    U.ensure_users_file(p)
    U.admin_create_user(p, 'Ali', 'ali@kuveytturk.com.tr', 'parola12345', 't')
    t0 = time.perf_counter(); r1 = U.authenticate(p, 'yok@kuveytturk.com.tr', 'x'); t1 = time.perf_counter() - t0
    t0 = time.perf_counter(); r2 = U.authenticate(p, 'ali@kuveytturk.com.tr', 'yanlis'); t2 = time.perf_counter() - t0
    assert r1 == r2 == (None, 'E-posta veya şifre hatalı')
    assert t1 > t2 * 0.4          # kullanıcı yokken de bcrypt maliyeti ödenir (yaklaşık aynı süre)


def test_yukleme_sinirli_okuma():
    import app as A
    from fastapi import HTTPException
    assert A._sinirli_oku(io.BytesIO(b'a' * 10), 10, 'x') == b'a' * 10
    with pytest.raises(HTTPException) as e:
        A._sinirli_oku(io.BytesIO(b'a' * 11), 10, 'dosya')
    assert e.value.status_code == 413
