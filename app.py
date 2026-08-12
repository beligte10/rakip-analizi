"""
KT Stratejik Kokpit — Web Sunucusu
=============================================
FastAPI tabanlı, tamamen yerel çalışan uygulama.

Mimari:
- Uygulama kodu ve veri aynı repo içinde birlikte yaşar.
- data/        → kalıcı veri klasörü (repo içinde)
                  ├── raw/                    yüklenmiş xlsx'ler
                  ├── veriler.parquet         pipeline parquet
                  ├── computed.json           hesaplanmış JSON
                  ├── catalog.json            measure & banka metadata
                  ├── upload_history.json     upload geçmişi log
                  ├── users.json              üyelik başvuruları/hesapları
                  └── .session_secret         oturum çerez imzalama anahtarı

İki AYRI yetki seviyesi (2026-08-12'den itibaren):
- ADMIN (HTTP Basic Auth, KT_USERNAME/KT_PASSWORD) — upload/rebuild/coverage
  + üyelik başvurularını onaylama/reddetme. TEK hesap, değişmedi.
- ÜYE (users.json + oturum çerezi) — sadece dashboard'u (Cockpit) görüntüler.
  Kayıt herkese açık ama 'pending' başlar; admin onaylamadan giriş yapılamaz.

Endpoint'ler:
- GET  /                          → frontend HTML
- GET  /admin                     → admin paneli HTML (Basic Auth)
- GET  /login , /signup           → üyelik giriş/kayıt HTML
- GET  /healthz                   → liveness (auth-free)
- POST /api/signup                → yeni üyelik başvurusu (pending)
- POST /api/login , /api/logout   → oturum aç/kapat
- GET  /api/me                    → oturumdaki üyenin bilgisi
- GET  /api/data , /api/catalog   → computed.json/catalog.json (üye girişi gerekir)
- GET  /api/version                → metadata
- GET  /api/admin/coverage         → banka × çeyrek var/yok matrisi
- GET  /api/admin/history          → son upload'lar
- GET  /api/admin/users            → üyelik başvuruları listesi
- POST /api/admin/users/{id}/approve|reject → üyelik onayı/reddi
- POST /admin/upload                → xlsx yükle, pipeline çalıştır

ENV vars (opsiyonel, hiçbiri zorunlu değil):
- KT_USERNAME    (default: faruk)     — admin panel kullanıcı adı
- KT_PASSWORD    (default: faruk123)  — admin panel şifresi
- DATA_DIR       (default: ./data)    — veri klasörünün yolu
- PORT           (default: 7860)      — sunucu portu
"""
from __future__ import annotations
import os
import io
import json
import shutil
import secrets
import traceback
import multiprocessing
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, status, Depends
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel

import users as users_mod


# ============================================================
# Konfigürasyon
# ============================================================
APP_ROOT = Path(__file__).parent.resolve()
FRONTEND_DIR = APP_ROOT / 'frontend'

# Tüm veri tek bir yerel klasörde yaşar — repo'nun kendi data/ klasörü
DATA_DIR = Path(os.environ.get('DATA_DIR', APP_ROOT / 'data')).resolve()
DATA_RAW = DATA_DIR / 'raw'
DATA_PARQUET = DATA_DIR / 'veriler.parquet'
DATA_COMPUTED = DATA_DIR / 'computed.json'
DATA_CATALOG = DATA_DIR / 'catalog.json'
DATA_HISTORY = DATA_DIR / 'upload_history.json'
DATA_USERS = DATA_DIR / 'users.json'
SESSION_SECRET_PATH = DATA_DIR / '.session_secret'

# Auth — admin (mevcut, tek hesap, upload/rebuild/coverage kontrolü)
USERNAME = os.environ.get('KT_USERNAME', 'faruk')
PASSWORD = os.environ.get('KT_PASSWORD', 'faruk123')

# auto_error=False: credentials verilmemişse (kullanıcı Basic Auth yerine
# session ile geliyorsa) 401 fırlatmadan None döner — require_admin_access
# bu durumda session/rol kontrolüne geçer (bkz. aşağı).
security_optional = HTTPBasic(auto_error=False)


def require_admin_access(
    request: Request,
    credentials: Optional[HTTPBasicCredentials] = Depends(security_optional),
) -> str:
    """
    Admin panel erişimi (2026-08-12 genişletildi) — İKİ yoldan biri yeterli:
    1. HTTP Basic Auth (mevcut tek admin hesabı, KT_USERNAME/KT_PASSWORD).
    2. Üyelik oturumu (session) + role='admin' — admin, onaylı bir üyeye
       admin panelden bu rolü atayabilir (bkz. users.py::set_role). Bu,
       ikinci hesaba Basic Auth hesabıyla EŞ DEĞER tam yetki verir (upload/
       rebuild/ZIP/üyelik onayı/grup düzenleme) — kısmi yetki YOK, kullanıcı
       bunu açıkça bu şekilde istedi.
    """
    if credentials is not None:
        valid_user = secrets.compare_digest(credentials.username, USERNAME)
        valid_pass = secrets.compare_digest(credentials.password, PASSWORD)
        if valid_user and valid_pass:
            return credentials.username

    user_id = request.session.get('user_id')
    if user_id:
        user = users_mod.get_user_by_id(DATA_USERS, user_id)
        if user and user['status'] == 'approved' and user.get('role') == 'admin':
            return user['email']

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Admin yetkisi gerekiyor',
        headers={'WWW-Authenticate': 'Basic'},
    )


def require_member(request: Request) -> dict:
    """
    Üyelik oturumu kontrolü (2026-08-12 eklendi) — dashboard'u sadece admin
    tarafından ONAYLANMIŞ üyeler görebilir. Admin erişimiyle
    (require_admin_access) KARIŞTIRILMAMALI: role='member' bir kullanıcı
    için bu, upload/rebuild/coverage gibi hiçbir yazma yetkisi vermez,
    sadece /api/data ve /api/catalog okuma erişimi içindir. role='admin'
    kullanıcılar için de aynı geçerli — admin yetkisi AYRI bir dependency
    (require_admin_access) ile kontrol edilir, require_member ile OTOMATİK
    gelmez.
    """
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail='Giriş yapmalısınız')
    user = users_mod.get_user_by_id(DATA_USERS, user_id)
    if not user or user['status'] != 'approved':
        request.session.clear()
        raise HTTPException(status_code=401, detail='Oturum geçersiz — tekrar giriş yapın')
    return user

# Frontend
HTML_USER = FRONTEND_DIR / 'index_v30.html'
HTML_ADMIN = FRONTEND_DIR / 'admin.html'
HTML_LOGIN = FRONTEND_DIR / 'login.html'
HTML_SIGNUP = FRONTEND_DIR / 'signup.html'


# ============================================================
# İlk açılış — data/ klasörünün var olduğundan emin ol
# ============================================================
def ensure_data_dir():
    """data/ ve data/raw/ klasörlerini oluşturur, upload_history.json/users.json yoksa yaratır."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_RAW.mkdir(parents=True, exist_ok=True)

    if not DATA_HISTORY.exists():
        DATA_HISTORY.write_text(json.dumps({'uploads': []},
                                            ensure_ascii=False, indent=2))
        print(f"[startup] {DATA_HISTORY} oluşturuldu")

    users_mod.ensure_users_file(DATA_USERS)

    # Admin, kendi Basic Auth şifresiyle üyelik sistemi (session tabanlı)
    # üzerinden de dashboard'a girebilsin — ayrı bir üye hesabı açıp kendi
    # onayını beklemesi gerekmesin. Idempotent, her başlangıçta senkronize
    # edilir (bkz. users.py::upsert_admin_account).
    users_mod.upsert_admin_account(
        DATA_USERS, f'{USERNAME}@admin.local', USERNAME.capitalize(), PASSWORD
    )


def _get_or_create_session_secret() -> str:
    """
    Oturum çerezlerini imzalamak için kullanılan secret — dosyada kalıcı
    olmalı, aksi halde her sunucu restart'ında (bu projede sık oluyor,
    bkz. memory: kismi-ceyrek-grup-agregasyonu-bug.md) TÜM üyelerin
    oturumu sessizce geçersiz kalırdı.
    """
    if SESSION_SECRET_PATH.exists():
        return SESSION_SECRET_PATH.read_text().strip()
    secret = secrets.token_urlsafe(32)
    SESSION_SECRET_PATH.write_text(secret)
    try:
        os.chmod(SESSION_SECRET_PATH, 0o600)
    except OSError:
        pass
    return secret


# KRİTİK (2026-08-12'de bulunan bug): ensure_data_dir() (ve içindeki
# upsert_admin_account, users.json'a KOŞULSUZ yazan bir işlem) modül
# seviyesinde çağrılıyor. pipeline/ingest.py::rebuild_parquet'in kullandığı
# ProcessPoolExecutor, her worker'ı 'spawn' ile başlatırken bu dosyayı
# (app.py) YENİDEN İÇE AKTARIYOR — bu da ensure_data_dir()'ı HER WORKER'DA
# (10'a kadar paralel) TEKRAR ÇALIŞTIRIYORDU. Çoklu worker AYNI ANDA
# users.json/.tmp dosyasına yazmaya çalışınca yarış durumu oluşuyor,
# bir worker diğerinin .tmp dosyasını zaten taşımış oluyor,
# FileNotFoundError ile worker çöküyor, tüm rebuild 'BrokenProcessPool'
# hatasıyla başarısız oluyordu. Fix: SADECE ana süreçte çalıştır.
if multiprocessing.current_process().name == 'MainProcess':
    ensure_data_dir()


# ============================================================
# FastAPI app
# ============================================================
app = FastAPI(
    title='KT Stratejik Kokpit',
    description='Kuveyt Türk rekabet analizi dashboard',
    version='3.0.0',
)

# Üyelik oturumları için imzalı çerez tabanlı session (2026-08-12).
# https_only=False: sunucu şu an sadece HTTP üzerinde çalışıyor (bkz.
# memory: guvenlik-sunucu-erisimi.md) — HTTPS'e geçilirse True yapılmalı.
app.add_middleware(
    SessionMiddleware,
    secret_key=_get_or_create_session_secret(),
    session_cookie='kt_session',
    max_age=14 * 24 * 60 * 60,  # 14 gün
    same_site='lax',
    https_only=False,
)


# ============================================================
# Public endpoint'ler (auth gerek yok)
# ============================================================
@app.get('/healthz', include_in_schema=False)
def healthz():
    return {
        'status': 'ok',
        'has_data': DATA_COMPUTED.exists(),
        'data_dir': str(DATA_DIR),
        'data_dir_writable': os.access(DATA_DIR, os.W_OK),
    }


# ============================================================
# Frontend
# ============================================================
# HTML yanıtlarında önbellek KAPALI: frontend tek büyük dosya olduğu için
# tarayıcı onu agresif cache'liyordu ve her kod değişikliğinden sonra elle
# hard-refresh (Cmd+Shift+R) gerekiyordu. Yerel kullanımda dosya diskten
# anında okunduğu için cache'in bir faydası yok.
NO_CACHE = {
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0',
}


@app.get('/', response_class=HTMLResponse)
def root():
    """Ana sayfa — cockpit HTML."""
    if not HTML_USER.exists():
        return HTMLResponse(
            f'<h1>Frontend bulunamadı</h1><p>{HTML_USER}</p>',
            status_code=500,
        )
    return FileResponse(HTML_USER, media_type='text/html', headers=NO_CACHE)


@app.get('/admin', response_class=HTMLResponse)
def admin_page(_: str = Depends(require_admin_access)):
    """Admin paneli — coverage + upload + history + üyelik onayları."""
    if not HTML_ADMIN.exists():
        return HTMLResponse(
            f'<h1>Admin sayfası bulunamadı</h1><p>{HTML_ADMIN}</p>',
            status_code=500,
        )
    return FileResponse(HTML_ADMIN, media_type='text/html', headers=NO_CACHE)


@app.get('/login', response_class=HTMLResponse)
def login_page():
    if not HTML_LOGIN.exists():
        return HTMLResponse(f'<h1>Giriş sayfası bulunamadı</h1><p>{HTML_LOGIN}</p>', status_code=500)
    return FileResponse(HTML_LOGIN, media_type='text/html', headers=NO_CACHE)


@app.get('/signup', response_class=HTMLResponse)
def signup_page():
    if not HTML_SIGNUP.exists():
        return HTMLResponse(f'<h1>Kayıt sayfası bulunamadı</h1><p>{HTML_SIGNUP}</p>', status_code=500)
    return FileResponse(HTML_SIGNUP, media_type='text/html', headers=NO_CACHE)


# ============================================================
# Üyelik: kayıt / giriş / çıkış (2026-08-12)
# ============================================================
class SignupPayload(BaseModel):
    name: str
    email: str
    password: str


class LoginPayload(BaseModel):
    email: str
    password: str


@app.post('/api/signup')
def api_signup(payload: SignupPayload):
    """Herkese açık kayıt — oluşan hesap 'pending' durumunda, admin
    onaylamadan giriş yapılamaz (bkz. users.py, /api/admin/users/*)."""
    ok, err = users_mod.create_signup(DATA_USERS, payload.name, payload.email, payload.password)
    if not ok:
        raise HTTPException(status_code=400, detail=err)
    return {'status': 'ok', 'message': 'Başvurunuz alındı. Admin onayından sonra giriş yapabilirsiniz.'}


@app.post('/api/login')
def api_login(payload: LoginPayload, request: Request):
    user, err = users_mod.authenticate(DATA_USERS, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail=err)
    request.session['user_id'] = user['id']
    return {'status': 'ok', 'name': user['name']}


@app.post('/api/logout')
def api_logout(request: Request):
    request.session.clear()
    return {'status': 'ok'}


@app.get('/api/me')
def api_me(user: dict = Depends(require_member)):
    return {'name': user['name'], 'email': user['email'], 'role': user.get('role', 'member')}


# ============================================================
# Veri okuma endpoint'leri — SADECE onaylı üyeler (2026-08-12'den önce
# auth'suzdu, bkz. memory: guvenlik-sunucu-erisimi.md madde 2)
# ============================================================
@app.get('/api/data')
def api_data(_: dict = Depends(require_member)):
    """Frontend'in çektiği ana JSON."""
    if not DATA_COMPUTED.exists():
        raise HTTPException(
            status_code=503,
            detail='computed.json yok. Admin paneli üzerinden veri yükleyin.',
        )
    return FileResponse(
        DATA_COMPUTED,
        media_type='application/json',
        headers=NO_CACHE,   # veri her yüklemede değişebilir
    )


@app.get('/api/catalog')
def api_catalog(_: dict = Depends(require_member)):
    if not DATA_CATALOG.exists():
        raise HTTPException(status_code=503, detail='catalog.json yok')
    return FileResponse(DATA_CATALOG, media_type='application/json', headers=NO_CACHE)


@app.get('/api/version')
def api_version():
    last_modified = None
    if DATA_COMPUTED.exists():
        last_modified = datetime.fromtimestamp(
            DATA_COMPUTED.stat().st_mtime
        ).isoformat()
    return {
        'app_version': '3.0.0',
        'phase': 'Faz 3 — Admin Upload UI',
        'has_data': DATA_COMPUTED.exists(),
        'data_last_modified': last_modified,
        'data_dir': str(DATA_DIR),
    }


# ============================================================
# Admin: coverage matrix
# ============================================================
@app.get('/api/admin/coverage')
def admin_coverage(_: str = Depends(require_admin_access)):
    """
    Banka × çeyrek var/yok matrisi.

    Dönüş:
    {
      'banks': ['Kuveyt Türk', 'Akbank', ...],
      'quarters': ['2013-12-31', '2014-03-31', ...],
      'matrix': {'Kuveyt Türk': {'2025-09-30': True, ...}},
      'summary': {
        'total_banks': 27,
        'latest_quarter': '2025-09-30',
        'banks_with_latest': 19,
        'banks_missing_latest': ['Banka X', ...],
        'total_cells': 1296,
        'filled_cells': 1180,
        'fill_rate': 0.91,
      },
      'last_updated': '2026-05-02T14:00:00'
    }
    """
    if not DATA_COMPUTED.exists():
        raise HTTPException(status_code=503, detail='computed.json yok')
    if not DATA_CATALOG.exists():
        raise HTTPException(status_code=503, detail='catalog.json yok')

    with open(DATA_CATALOG, encoding='utf-8') as f:
        catalog = json.load(f)
    with open(DATA_COMPUTED, encoding='utf-8') as f:
        data = json.load(f)

    # Sadece gerçek bankalar (grup değil)
    GROUP_NAMES = {'Sektör', 'Mevduat Sektörü', 'Katılım'}
    banks = [b['banka_adi'] for b in catalog['banks']
             if b['banka_adi'] not in GROUP_NAMES]

    # Quarters: en yaygın referans olarak 'toplam_aktifler' kullan
    bank_data = data.get('bank_data', {})
    ref_measure = 'toplam_aktifler'
    quarters_set = set()
    for banka in banks:
        if banka in bank_data.get(ref_measure, {}):
            quarters_set.update(bank_data[ref_measure][banka].keys())
    quarters = sorted(quarters_set)

    # Matrix: hangi banka × çeyrekte değer var/yok
    matrix = {}
    for banka in banks:
        bank_q = bank_data.get(ref_measure, {}).get(banka, {})
        matrix[banka] = {q: bank_q.get(q) is not None for q in quarters}

    # Summary
    latest = quarters[-1] if quarters else None
    banks_with_latest = [b for b in banks if matrix[b].get(latest, False)]
    banks_missing_latest = [b for b in banks if not matrix[b].get(latest, False)]

    # Beklenen çeyrek = latest + 3 ay (ör. 2025-09-30 → 2025-12-31)
    expected = None
    banks_with_expected = []
    banks_missing_expected = []
    if latest:
        from datetime import date
        y, m, d = map(int, latest.split('-'))
        # Çeyrek sonları: Mart 31, Haziran 30, Eylül 30, Aralık 31
        next_q = {3: (6, 30), 6: (9, 30), 9: (12, 31), 12: (3, 31)}
        nm, nd = next_q.get(m, (12, 31))
        ny = y + 1 if m == 12 else y
        expected = f'{ny:04d}-{nm:02d}-{nd:02d}'

        # Bekleyen çeyreğin matrix'te kaydı var mı (genelde yok, henüz hiç yüklenmemiş)
        # Eğer var ise, hangi bankalar yüklemiş hangisi yüklememiş hesapla
        for b in banks:
            bank_q = bank_data.get(ref_measure, {}).get(b, {})
            if bank_q.get(expected) is not None:
                banks_with_expected.append(b)
            else:
                banks_missing_expected.append(b)

    total = len(banks) * len(quarters)
    filled = sum(sum(1 for v in m.values() if v) for m in matrix.values())

    last_modified = None
    if DATA_COMPUTED.exists():
        last_modified = datetime.fromtimestamp(
            DATA_COMPUTED.stat().st_mtime
        ).isoformat()

    return {
        'banks': banks,
        'quarters': quarters,
        'matrix': matrix,
        'summary': {
            'total_banks': len(banks),
            'latest_quarter': latest,
            'banks_with_latest': len(banks_with_latest),
            'banks_missing_latest': banks_missing_latest,
            'expected_quarter': expected,
            'banks_with_expected': len(banks_with_expected),
            'banks_missing_expected': banks_missing_expected,
            'total_cells': total,
            'filled_cells': filled,
            'fill_rate': filled / total if total else 0,
        },
        'last_updated': last_modified,
    }


# ============================================================
# Admin: upload geçmişi
# ============================================================
@app.get('/api/admin/users')
def admin_list_users(_: str = Depends(require_admin_access)):
    """Tüm üyelik başvuruları (pending/approved/rejected) — sadece admin görür."""
    users = users_mod.list_users(DATA_USERS)
    return {'users': list(reversed(users))}  # en yeni başvuru başta


@app.post('/api/admin/users/{user_id}/approve')
def admin_approve_user(user_id: int, admin_user: str = Depends(require_admin_access)):
    ok = users_mod.set_status(DATA_USERS, user_id, 'approved', admin_user)
    if not ok:
        raise HTTPException(status_code=404, detail='Kullanıcı bulunamadı')
    return {'status': 'ok'}


@app.post('/api/admin/users/{user_id}/reject')
def admin_reject_user(user_id: int, admin_user: str = Depends(require_admin_access)):
    ok = users_mod.set_status(DATA_USERS, user_id, 'rejected', admin_user)
    if not ok:
        raise HTTPException(status_code=404, detail='Kullanıcı bulunamadı')
    return {'status': 'ok'}


class RolePayload(BaseModel):
    role: str  # 'member' | 'admin'


@app.post('/api/admin/users/{user_id}/role')
def admin_set_user_role(user_id: int, payload: RolePayload, admin_user: str = Depends(require_admin_access)):
    """
    Bir kullanıcıya admin rolü ver/al (2026-08-12). role='admin' verilen
    kullanıcı, Basic Auth hesabıyla EŞ DEĞER tam admin panel yetkisi kazanır
    (bkz. require_admin_access docstring'i) — kısmi/sınırlı yetki YOK.
    """
    ok = users_mod.set_role(DATA_USERS, user_id, payload.role)
    if not ok:
        raise HTTPException(status_code=400, detail='Geçersiz kullanıcı veya rol')
    return {'status': 'ok'}


@app.get('/api/admin/history')
def admin_history(limit: int = 20, _: str = Depends(require_admin_access)):
    """Son N upload kaydı."""
    if not DATA_HISTORY.exists():
        return {'uploads': []}
    try:
        with open(DATA_HISTORY, encoding='utf-8') as f:
            history = json.load(f)
    except (json.JSONDecodeError, OSError):
        history = {'uploads': []}
    uploads = history.get('uploads', [])[-limit:]
    return {'uploads': list(reversed(uploads))}  # en yeni başta


def _append_history(entry: dict):
    """Upload geçmişine kayıt ekle (atomik)."""
    try:
        if DATA_HISTORY.exists():
            with open(DATA_HISTORY, encoding='utf-8') as f:
                hist = json.load(f)
        else:
            hist = {'uploads': []}
    except (json.JSONDecodeError, OSError):
        hist = {'uploads': []}

    hist.setdefault('uploads', []).append(entry)
    # Son 200 kaydı tut, eski olanları kırp
    hist['uploads'] = hist['uploads'][-200:]

    tmp = DATA_HISTORY.with_suffix('.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(hist, f, ensure_ascii=False, indent=2)
    tmp.replace(DATA_HISTORY)


# ============================================================
# Banka grupları yönetimi (2026-08-12) — catalog.json'daki groups.members'ı
# admin panelinden düzenlemeyi sağlar (ör. "Rakip Bankalar" üyeliği).
# Tek, ORTAK set — herkesin dashboard'unda aynı görünür (kişiye özel değil,
# kullanıcı bu şekilde istedi).
# ============================================================

def _load_catalog() -> dict:
    if not DATA_CATALOG.exists():
        raise HTTPException(status_code=500, detail='catalog.json yok')
    with open(DATA_CATALOG, encoding='utf-8') as f:
        return json.load(f)


def _save_catalog(catalog: dict) -> None:
    tmp = DATA_CATALOG.with_suffix('.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    tmp.replace(DATA_CATALOG)


def _recompute_groups_and_save(catalog: dict) -> None:
    """
    Grup üyeliği değiştiğinde SADECE group_data + composition_data'yı
    yeniden hesaplar (bank_data'ya DOKUNMAZ) — tam rebuild'in (~50sn,
    1176 xlsx'i yeniden okur) aksine sadece parquet'i okuyup mevcut
    bank_data üzerinden agregasyon yapar (~5-10sn). meta.group_order/
    meta.groups/meta.group_colors da (bunlar 'statik' kabul edilip
    normal rebuild'lerde korunuyordu — bkz. _rebuild_dynamic_meta
    yorumu) YENİ catalog'dan güncellenir, aksi halde yeni oluşturulan
    bir grup dashboard'da hiç görünmezdi.
    """
    from pipeline import LookupContext, build_group_data
    from pipeline.composition import build_composition_payload

    bank_turu_map = {b['banka_adi']: b['tur'] for b in catalog['banks']}
    ctx = LookupContext.from_parquet(DATA_PARQUET, bank_turu_map)

    if not DATA_COMPUTED.exists():
        raise HTTPException(status_code=500, detail='computed.json yok — önce /admin/rebuild çalıştırın')
    with open(DATA_COMPUTED, encoding='utf-8') as f:
        computed = json.load(f)

    bank_data = computed.get('bank_data', {})
    group_data = build_group_data(bank_data, catalog, ctx)
    composition_data, currency_data = build_composition_payload(ctx, catalog)

    meta = computed.get('meta', {})
    meta['group_order'] = catalog['groups']['order']
    meta['group_colors'] = catalog['groups']['colors']
    meta['groups'] = catalog['groups']['members']

    computed['meta'] = meta
    computed['group_data'] = group_data
    computed['composition_data'] = composition_data
    computed['currency_data'] = currency_data
    computed['timestamp'] = datetime.now().isoformat()

    tmp = DATA_COMPUTED.with_suffix('.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(computed, f, ensure_ascii=False, separators=(',', ':'))
    tmp.replace(DATA_COMPUTED)


class GroupMembersPayload(BaseModel):
    members: List[str]


class GroupCreatePayload(BaseModel):
    name: str
    members: List[str]
    color: Optional[str] = None


PROTECTED_GROUPS = {'Kuveyt Türk'}  # temel referans grubu, silinemez


@app.get('/api/admin/groups')
def admin_list_groups(_: str = Depends(require_admin_access)):
    catalog = _load_catalog()
    real_banks = sorted(b['banka_adi'] for b in catalog['banks'] if b['tur'] != 'Grup')
    groups = catalog.get('groups', {})
    return {
        'order': groups.get('order', []),
        'members': groups.get('members', {}),
        'colors': groups.get('colors', {}),
        'all_banks': real_banks,
        'protected': sorted(PROTECTED_GROUPS),
    }


@app.put('/api/admin/groups/{group_name}')
def admin_update_group(group_name: str, payload: GroupMembersPayload, _: str = Depends(require_admin_access)):
    catalog = _load_catalog()
    groups = catalog.setdefault('groups', {'order': [], 'members': {}, 'colors': {}})
    if group_name not in groups.get('members', {}):
        raise HTTPException(status_code=404, detail='Grup bulunamadı')
    real_banks = set(b['banka_adi'] for b in catalog['banks'] if b['tur'] != 'Grup')
    invalid = [m for m in payload.members if m not in real_banks]
    if invalid:
        raise HTTPException(status_code=400, detail=f'Geçersiz banka(lar): {invalid}')
    if not payload.members:
        raise HTTPException(status_code=400, detail='Grup en az 1 üye içermeli')
    groups['members'][group_name] = payload.members
    _save_catalog(catalog)
    _recompute_groups_and_save(catalog)
    return {'status': 'ok'}


@app.post('/api/admin/groups')
def admin_create_group(payload: GroupCreatePayload, _: str = Depends(require_admin_access)):
    catalog = _load_catalog()
    groups = catalog.setdefault('groups', {'order': [], 'members': {}, 'colors': {}})
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail='Grup adı boş olamaz')
    if name in groups.get('members', {}):
        raise HTTPException(status_code=400, detail='Bu isimde bir grup zaten var')
    real_banks = set(b['banka_adi'] for b in catalog['banks'] if b['tur'] != 'Grup')
    invalid = [m for m in payload.members if m not in real_banks]
    if invalid:
        raise HTTPException(status_code=400, detail=f'Geçersiz banka(lar): {invalid}')
    if not payload.members:
        raise HTTPException(status_code=400, detail='Grup en az 1 üye içermeli')
    groups.setdefault('order', []).append(name)
    groups.setdefault('members', {})[name] = payload.members
    groups.setdefault('colors', {})[name] = payload.color or '#64748b'
    _save_catalog(catalog)
    _recompute_groups_and_save(catalog)
    return {'status': 'ok'}


@app.delete('/api/admin/groups/{group_name}')
def admin_delete_group(group_name: str, _: str = Depends(require_admin_access)):
    catalog = _load_catalog()
    if group_name in PROTECTED_GROUPS:
        raise HTTPException(status_code=400, detail=f"'{group_name}' grubu silinemez")
    groups = catalog.get('groups', {})
    if group_name not in groups.get('members', {}):
        raise HTTPException(status_code=404, detail='Grup bulunamadı')
    groups['members'].pop(group_name, None)
    groups.get('colors', {}).pop(group_name, None)
    if group_name in groups.get('order', []):
        groups['order'].remove(group_name)
    _save_catalog(catalog)
    _recompute_groups_and_save(catalog)
    return {'status': 'ok'}


def _result_period_count(bank_data: dict) -> int:
    """Hesaplanan bank_data'da kaç (banka × tarih) hücresi dolu — boşluk kontrolü için."""
    ta = (bank_data or {}).get('toplam_aktifler', {})
    return sum(len(series) for series in ta.values())


def _assert_nonempty_result(bank_data: dict):
    """GÜVENLİK KİLİDİ: Hesaplama boş sonuç verdiyse yazma — mevcut veriyi koru.

    Faz 4 bug'ı: rebuild boş data/raw veya banks=None ile boş bank_data üretip
    canlı computed.json'u sıfırlamıştı. Bu kilit, boş/şüpheli sonucun diske
    yazılmasını engeller (atomik yazımdan ÖNCE çağrılmalı).
    """
    n = _result_period_count(bank_data)
    if n == 0:
        raise HTTPException(
            status_code=500,
            detail=('Hesaplama boş sonuç verdi (toplam_aktifler için 0 dönem). '
                    'Mevcut veri KORUNDU, yazma iptal edildi. '
                    'Olası neden: data/raw boş ya da parquet eksik.'),
        )


def _rebuild_dynamic_meta(meta: dict, bank_data: dict, catalog: dict) -> dict:
    """meta'nın DİNAMİK alanlarını hesaplanan bank_data'dan yeniden üretir.

    Statik alanlar (banks, groups, group_order, group_colors, kt_ramp,
    neutral_ramp, accent, compositions) carried meta'dan korunur.
    Dinamik alanlar (dates, total_periods, bank_coverage, top20_by_date,
    available_measures) her zaman gerçek veriden türetilir — böylece meta
    asla bank_data ile tutarsız / boş kalmaz.
    """
    meta = dict(meta or {})
    real_banks = [b['banka_adi'] for b in catalog.get('banks', [])]
    real_set = set(real_banks)
    ta = bank_data.get('toplam_aktifler', {})

    # dates: gerçek bankalarda dolu görülen tüm tarihlerin birleşimi (artan)
    date_set = set()
    for bydict in bank_data.values():
        for bname, series in bydict.items():
            if bname in real_set:
                for d, v in series.items():
                    if v is not None:
                        date_set.add(d)
    dates = sorted(date_set)
    meta['dates'] = dates
    meta['total_periods'] = len(dates)

    # default_date: dashboard açılışında seçili gelecek dönem. dates[-1] (tüm
    # bankalar arasındaki EN YENİ tarih) kullanılırsa, çeyreklik veri bankalar
    # tek tek admin panelinden yüklendikçe (bkz. 2026-08-11), sadece birkaç
    # bankanın raporladığı yarım bir çeyrek varsayılan görünüm olur — grup
    # kartları büyük ölçüde boş/yanıltıcı kalır. Bunun yerine KT'nin (birincil
    # banka, her zaman en düzenli yüklenen) son raporladığı tarih kullanılır.
    kt_dates = sorted(d for d, v in ta.get('Kuveyt Türk', {}).items() if v is not None)
    meta['default_date'] = kt_dates[-1] if kt_dates else (dates[-1] if dates else None)

    # bank_coverage: her gerçek banka için toplam_aktifler dolu dönem sayısı
    meta['bank_coverage'] = {
        b: sum(1 for v in ta.get(b, {}).values() if v is not None)
        for b in real_banks
    }

    # date_coverage: her tarihte kaç gerçek banka toplam_aktifler raporlamış.
    # Yeni banka kuruldukça bu sayı zamanla artar (20→27, normal). Ama bir
    # çeyrek admin panelden banka banka yüklenirken (bkz. default_date notu)
    # geçici olarak SAYI GERİYE DÜŞER (ör. 26'dan 7'ye) — bu durumda pazar
    # payı/Bps hesaplaması (frontend marketShare/msDeltaBps) o tarihi
    # güvenilmez saymalı, aksi halde eksik bankalar paydan düşünce diğer
    # herkesin payı yapay şekilde şişer (bkz. 2026-08-11 kullanıcı raporu:
    # "pazar payı değişimlerinde bozulmalar vardı").
    meta['date_coverage'] = {
        d: sum(1 for b in real_banks if ta.get(b, {}).get(d) is not None)
        for d in dates
    }

    # top20_by_date: her tarih için Toplam Aktifler'e göre ilk 20 banka
    top20 = {}
    for d in dates:
        rows = [(b, ta.get(b, {}).get(d)) for b in real_banks
                if ta.get(b, {}).get(d) is not None]
        rows.sort(key=lambda x: x[1], reverse=True)
        top20[d] = [b for b, _ in rows[:20]]
    meta['top20_by_date'] = top20

    # available_measures: en az bir gerçek bankada dolu değeri olan measure'lar
    avail = []
    for c in catalog.get('measures', []):
        mid = c['id']
        bydict = bank_data.get(mid, {})
        if any(v is not None for b in real_banks for v in bydict.get(b, {}).values()):
            avail.append(mid)
    meta['available_measures'] = avail

    return meta


# Grup (Kuveyt Türk, Mevduat Bankaları, Rakip Bankalar, Katılım Bankaları,
# KT Hariç Katılım Bankaları) aggregate hesaplama TEK yerde yaşıyor:
# pipeline.groups.build_group_data(). Daha önce burada ikinci, birebir aynı
# işi yapan yerel bir kopya (`_build_group_data`) vardı — kaldırıldı, aşağıda
# `from pipeline import build_group_data` ile aynı fonksiyon kullanılıyor.


# ============================================================
# Admin: upload endpoint
# ============================================================
@app.post('/admin/upload')
async def admin_upload(
    files: List[UploadFile] = File(...),
    user: str = Depends(require_admin_access),
):
    """
    Bir veya birden fazla xlsx yükle, pipeline'ı BİR KEZ çalıştır, computed.json'u güncelle.

    NOT (2026-08-09 düzeltmesi): Bu endpoint önceden `file: UploadFile` (tekil)
    bekliyordu ama admin.html'deki frontend her zaman çoklu-dosya alanı olarak
    `files` (çoğul) gönderiyordu — FastAPI eşleşmeyen alan adını `file` olarak
    zorunlu kabul ettiğinden HER upload denemesi `422 Field required` ile
    başarısız oluyordu. Ayrıca eskiden N dosya, N kere tam pipeline çalıştırırdı
    (her biri data/raw/'daki TÜM dosyaları yeniden tarardı) — 27 dosyalık bir
    çeyrek yüklemesi ~40 dakika sürerdi. Artık: dosyalar önce hepsi kaydedilir,
    pipeline (parquet güncelleme + compute_all + group + composition) TEK sefer
    çalışır.

    NOT (2026-08-11 düzeltmesi): Parquet adımı artık INCREMENTAL —
    data/raw/'daki TÜM dosyaları değil, SADECE bu istekte yüklenenleri parse
    eder (bkz. pipeline.ingest.update_parquet_incremental). Önceden tek
    dosyalık bir yükleme bile ~50 saniye sürerdi (%42'si — dokunulmamış
    1170+ dosyayı yeniden okumaktan); artık o adım N dosyayla orantılı.
    compute_all/build_group_data/composition adımları GÜVENLİK GEREĞİ hâlâ
    TÜM bankalar için tam yeniden hesaplanıyor (grup agregasyonları/pazar
    payı tüm bankaların güncel değerine muhtaç — kısmi hesaplama yanlış
    sonuç riski taşırdı, bkz. 2026-08-11'de bulunan grup/pazar payı bug'ları).

    Adımlar:
    1. Her dosya için ad doğrulama (banka + çeyrek-sonu tarih formatı)
    2. İçerik kalite kontrolü (2026-08-11 eklendi) — bkz.
       pipeline.ingest.check_data_quality: Bloomberg/FactSet eklentisi
       olmadan export edilmiş (Tutar hücreleri '#VALUE!'/boş) dosyalar
       reddedilir, aksi halde ölçütler sessizce 0'a düşerdi.
    3. Geçerli olanlar data/raw/<Banka>/<Banka> - DD.MM.YYYY.xlsx olarak kaydedilir
    4. Parquet incremental güncelleme (SADECE yüklenen dosyalar — bkz. yukarı)
    5. compute_all → data/computed.json (TEK yazma)
    6. Upload geçmişine, her dosya için ayrı kayıt
    """
    if not files:
        raise HTTPException(status_code=400, detail='Dosya gönderilmedi')

    # Lazy import — pipeline modülleri ağır
    from pipeline.ingest import (
        parse_filename, validate_filename, check_data_quality,
        update_parquet_incremental,
    )
    from pipeline import LookupContext, compute_all, build_group_data
    from pipeline.composition import build_composition_payload

    # Catalog yükle
    if not DATA_CATALOG.exists():
        raise HTTPException(status_code=500, detail='catalog.json yok')
    with open(DATA_CATALOG, encoding='utf-8') as f:
        catalog = json.load(f)

    valid_banks = [b['banka_adi'] for b in catalog['banks']
                   if b['tur'] != 'Grup']
    bank_turu_map = {b['banka_adi']: b['tur'] for b in catalog['banks']}
    all_bank_names = [b['banka_adi'] for b in catalog['banks']]

    # 1. Her dosyayı doğrula + data/raw/'a kaydet. Geçersiz dosyalar
    # ATLANIR (tek dosyanın adı yanlışsa tüm batch iptal olmasın), rapora
    # 'skipped' olarak düşer. Kaydedilenler hata durumunda geri alınabilsin
    # diye ayrı listelenir.
    saved: list[dict] = []
    skipped: list[dict] = []
    for file in files:
        if not file.filename.lower().endswith('.xlsx'):
            skipped.append({'filename': file.filename, 'sebep': 'Sadece .xlsx kabul edilir'})
            await file.close()
            continue
        ok, err = validate_filename(file.filename, valid_banks)
        if not ok:
            skipped.append({'filename': file.filename, 'sebep': err})
            await file.close()
            continue

        # İçeriği belleğe oku — hem kalite kontrolü hem diske yazma bunun
        # üzerinden yapılır (stream'i iki kere tüketmemek için).
        try:
            content = await file.read()
        finally:
            await file.close()

        # İçerik kalite kontrolü (2026-08-11 eklendi): Bloomberg/FactSet
        # eklentisi olmadan export edilen dosyalarda Tutar hücreleri
        # '#VALUE!' veya boş kalır. Bu fark edilmeden kabul edilirse
        # LookupContext._lookup() eksik veriyi sessizce 0.0'a çevirir —
        # ölçütler yanlışlıkla "gerçek sıfır" gibi görünür, hiçbir hata
        # vermeden (bkz. pipeline/ingest.py::check_data_quality docstring).
        ok, err = check_data_quality(io.BytesIO(content))
        if not ok:
            skipped.append({'filename': file.filename, 'sebep': f'Veri kalitesi: {err}'})
            continue

        banka, tarih = parse_filename(file.filename)
        bank_dir = DATA_RAW / banka
        bank_dir.mkdir(parents=True, exist_ok=True)
        target = bank_dir / file.filename

        # Üzerine yazma durumunda ÖNCEKİ içeriği belleğe al — pipeline bu
        # istekte başarısız olursa geri yüklenecek. (2026-08-09 bug: eskiden
        # hata durumunda dosya doğrudan silinirdi; bu, aynı ada sahip VAR
        # OLAN bir dosyayı — örn. çeyrek dosyası yanlışlıkla tekrar
        # yüklendiğinde — kalıcı olarak kaybettiriyordu.)
        onceki_icerik = target.read_bytes() if target.exists() else None

        target.write_bytes(content)
        saved.append({
            'filename': file.filename, 'banka': banka, 'tarih': tarih,
            'target': target, 'file_size': target.stat().st_size,
            'onceki_icerik': onceki_icerik,
        })

    if not saved:
        raise HTTPException(
            status_code=400,
            detail=f'Geçerli dosya yok. Atlananlar: {skipped}',
        )

    # Pipeline çalıştır — TÜM dosyalar için TEK sefer
    try:
        # 2. Parquet güncelleme — INCREMENTAL (2026-08-11): data/raw/'daki
        # TÜM 1176 dosyayı değil, SADECE bu istekte yüklenen dosyaları
        # parse eder. Önceden burada rebuild_parquet (tam tarama) vardı —
        # tek dosyalık bir yüklemede bile ~50 saniyenin ~22 saniyesi
        # (rebuild_parquet adımı) sırf dokunulmamış 1170+ dosyayı yeniden
        # okumaya gidiyordu (bkz. verimlilik raporu, madde 2).
        update_parquet_incremental(
            [(s['target'], s['banka'], s['tarih'], bank_turu_map.get(s['banka']))
             for s in saved],
            DATA_PARQUET,
        )

        # 3. Mevcut computed.json'u baseline olarak yükle
        base_data = {}
        meta = {}
        if DATA_COMPUTED.exists():
            with open(DATA_COMPUTED, encoding='utf-8') as f:
                base = json.load(f)
            base_data = base.get('bank_data', {})
            meta = base.get('meta', {})

        # 4. compute_all — banks AÇIKÇA verilir (Faz 4 fix'iyle tutarlı):
        # base_data ilk yüklemede boş/eksik olabilir, banks=None o durumda
        # banka listesini boş baseline'dan türetip veri kaybına yol açardı.
        ctx = LookupContext.from_parquet(DATA_PARQUET, bank_turu_map)
        new_bank_data = compute_all(ctx, base_data, catalog, banks=all_bank_names, verbose=False)

        # 4a. GÜVENLİK KİLİDİ + dinamik meta yeniden üretimi
        _assert_nonempty_result(new_bank_data)
        meta = _rebuild_dynamic_meta(meta, new_bank_data, catalog)
        group_data = build_group_data(new_bank_data, catalog, ctx)

        # 4b. Kompozisyon + döviz (TP/YP) dağılımı
        composition_data, currency_data = build_composition_payload(ctx, catalog)

        # 5. Çıktıyı yaz (atomik)
        timestamp = datetime.now().isoformat()
        out_data = {
            'meta': meta,
            'catalog': catalog['measures'],
            'bank_data': new_bank_data,
            'group_data': group_data,
            'composition_data': composition_data,
            'currency_data': currency_data,
            'timestamp': timestamp,
        }
        tmp = DATA_COMPUTED.with_suffix('.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(out_data, f, ensure_ascii=False, separators=(',', ':'))
        tmp.replace(DATA_COMPUTED)

        # 6. Geçmişe kayıt — her dosya için ayrı satır (denetim izi)
        for s in saved:
            _append_history({
                'timestamp': timestamp,
                'user': user,
                'filename': s['filename'],
                'banka': s['banka'],
                'tarih': s['tarih'],
                'file_size': s['file_size'],
                'status': 'ok',
            })

        # 7. Spot check — yüklenen ilk dosyanın banka × tarihi için
        ilk = saved[0]
        spot_check = {}
        for mid in ['toplam_aktifler', 'krediler', 'mevduat',
                    'ozkaynaklar', 'net_donem_kari']:
            spot_check[mid] = new_bank_data.get(mid, {}).get(ilk['banka'], {}).get(ilk['tarih'])

        return JSONResponse({
            'status': 'ok',
            'files_processed': len(saved),
            'files_skipped': skipped,
            'banks_affected': sorted({s['banka'] for s in saved}),
            'measures_computed': len(new_bank_data),
            'banks_in_pipeline': len({b for m in new_bank_data.values()
                                       for b in m.keys()}),
            'timestamp': timestamp,
            'spot_check': spot_check,
        })

    except Exception as exc:
        # Hata: BU istekte yazılan dosyaları geri al.
        # - Dosya YENİ eklenmişse (öncesinde yoktu) → sil.
        # - Dosya VAR OLAN birinin üzerine yazılmışsa → eski içeriğini geri
        #   yükle, SİLME (aksi halde bu istekten önce var olan gerçek veri
        #   kaybolur — bkz. yukarıdaki 'onceki_icerik' yorumu).
        for s in saved:
            try:
                if s['onceki_icerik'] is not None:
                    s['target'].write_bytes(s['onceki_icerik'])
                else:
                    s['target'].unlink()
            except FileNotFoundError:
                pass
            _append_history({
                'timestamp': datetime.now().isoformat(),
                'user': user,
                'filename': s['filename'],
                'banka': s['banka'],
                'tarih': s['tarih'],
                'file_size': s['file_size'],
                'status': 'error',
                'error': f'{type(exc).__name__}: {exc}',
            })
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f'Pipeline hatası: {type(exc).__name__}: {exc}',
        )


# ============================================================
# Admin: ZIP upload — bulk replace raw + auto rebuild (Faz 3.6)
# ============================================================
@app.post('/admin/upload-zip')
async def admin_upload_zip(
    file: UploadFile = File(...),
    user: str = Depends(require_admin_access),
):
    """
    ZIP yükle, içindeki tüm xlsx'leri data/raw/'a yerleştir, pipeline çalıştır.

    KULLANIM SENARYOSU:
    - Bloomberg/FactSet eklentisi olmadan extract edilince #NAME? alan xlsx'ler
    - ZIP'in içindeki cached değerler bozulmadan korunur
    - Tarayıcının/işletim sisteminin Türkçe karakter sorunlarını bypass eder

    BEKLENEN ZIP YAPISI (esnek):
        Veriler/Akbank/Akbank - 30.06.2014.xlsx          ← üstte 'Veriler/' wrapper varsa otomatik atlanır
        Veriler/Kuveyt Türk/Kuveyt Türk - 30.09.2025.xlsx
        ...
    veya doğrudan banka klasörleri:
        Akbank/Akbank - 30.06.2014.xlsx
        Kuveyt Türk/Kuveyt Türk - 30.09.2025.xlsx

    Süre: 5-15 dakika (ZIP'e bağlı). Tarayıcı sekmesini kapatma.
    """
    import zipfile
    import io
    import tempfile

    started = datetime.now().isoformat()

    if not file.filename.lower().endswith('.zip'):
        raise HTTPException(status_code=400, detail='Sadece .zip kabul edilir')

    # Catalog yükle
    if not DATA_CATALOG.exists():
        raise HTTPException(status_code=500, detail='catalog.json yok')
    with open(DATA_CATALOG, encoding='utf-8') as f:
        catalog = json.load(f)
    bank_turu_map = {b['banka_adi']: b['tur'] for b in catalog['banks']}
    valid_banks = set(b['banka_adi'] for b in catalog['banks']
                       if b['tur'] != 'Grup')

    # ZIP'i geçici dosyaya yaz (büyük ZIP'leri belleğe yüklemek riskli)
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmpf:
        try:
            shutil.copyfileobj(file.file, tmpf)
            tmp_zip_path = Path(tmpf.name)
        finally:
            await file.close()

    zip_size = tmp_zip_path.stat().st_size

    def _safe_filename(info: zipfile.ZipInfo) -> str:
        """
        ZIP entry filename'ini UTF-8 olarak döndür.

        ZIP encoding hakikatleri:
        - Standartta filename CP437 olmalı, UTF-8 ise flag_bits bit 11 set
        - Pratikte: Windows ZIP araçları bu flag'i unutur veya mojibake yapar
        - 'Kuveyt Türk' → 'Kuveyt T├╝rk' gibi karakterler ortaya çıkar

        Strateji: cp437 → utf-8 round-trip dene. Başarılı olursa ve sonuç
        ASCII olmayan Türkçe karakter içeriyorsa onu kullan (orijinal
        muhtemelen mojibake idi). Aksi takdirde orijinali döndür.
        """
        original = info.filename
        try:
            # Orijinal string'i cp437 olarak yorumla (her byte 1:1 eşlenir),
            # sonra UTF-8 olarak decode et
            candidate = original.encode('cp437').decode('utf-8')
            # Eğer candidate non-ASCII Türkçe karakter içeriyorsa → mojibake çözüldü
            # (Türkçe karakterler: ş, ç, ğ, ı, ö, ü, İ, Ş, Ç, Ğ, Ö, Ü)
            tr_chars = set('şçğıöüŞÇĞİÖÜâêîôûÂÊÎÔÛ')
            if any(ch in tr_chars for ch in candidate):
                return candidate
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        return original

    try:
        # 1. ZIP'i validate et — banka klasörü yapısı doğru mu?
        with zipfile.ZipFile(tmp_zip_path, 'r') as zf:
            xlsx_entries = [
                info for info in zf.infolist()
                if not info.is_dir()
                and _safe_filename(info).lower().endswith('.xlsx')
            ]
            if not xlsx_entries:
                raise HTTPException(
                    status_code=400,
                    detail='ZIP içinde .xlsx dosyası yok'
                )

            # Banka klasör adlarını çıkar (UTF-8 safe)
            banks_in_zip = set()
            for info in xlsx_entries:
                fname = _safe_filename(info)
                parts = fname.replace('\\', '/').split('/')
                if len(parts) >= 2:
                    banka = parts[-2]
                    banks_in_zip.add(banka)

            unknown_banks = banks_in_zip - valid_banks
            if unknown_banks:
                raise HTTPException(
                    status_code=400,
                    detail=f'Catalog\'ta tanımlı olmayan banka(lar): '
                           f'{sorted(unknown_banks)}. ZIP yapısı: '
                           f'<banka_klasoru>/<banka> - DD.MM.YYYY.xlsx'
                )

            # 2. data/raw/ altındaki mevcut banka klasörlerini sil
            existing_dirs = [d for d in DATA_RAW.iterdir()
                              if d.is_dir() and not d.name.startswith('.')]
            for d in existing_dirs:
                shutil.rmtree(d)
            print(f"[upload-zip] {len(existing_dirs)} eski banka klasörü silindi")

            # 3. ZIP içindeki dosyaları locale-safe şekilde extract et
            n_extracted = 0
            for info in xlsx_entries:
                fname = _safe_filename(info)
                parts = fname.replace('\\', '/').split('/')
                if len(parts) < 2:
                    continue
                banka = parts[-2]
                file_name = parts[-1]

                target_dir = DATA_RAW / banka
                target_dir.mkdir(parents=True, exist_ok=True)
                target_path = target_dir / file_name

                with zf.open(info) as src:
                    target_path.write_bytes(src.read())
                n_extracted += 1

            print(f"[upload-zip] {n_extracted} xlsx data/raw/'a yerleştirildi")

        # 4. Pipeline çalıştır
        from pipeline.ingest import rebuild_parquet
        rebuild_parquet(DATA_RAW, DATA_PARQUET, bank_turu_map)

        # 5. Baseline'dan compute_all (mevcut computed.json'u baseline al)
        from pipeline import LookupContext, compute_all, build_group_data

        base_data = {}
        meta = {}
        group_data = {}
        if DATA_COMPUTED.exists():
            with open(DATA_COMPUTED, encoding='utf-8') as f:
                base = json.load(f)
            base_data = base.get('bank_data', {})
            meta = base.get('meta', {})
            group_data = base.get('group_data', {})

        ctx = LookupContext.from_parquet(DATA_PARQUET, bank_turu_map)
        new_bank_data = compute_all(ctx, base_data, catalog, verbose=False)

        # 5a. GÜVENLİK KİLİDİ + dinamik meta yeniden üretimi
        _assert_nonempty_result(new_bank_data)
        meta = _rebuild_dynamic_meta(meta, new_bank_data, catalog)
        group_data = build_group_data(new_bank_data, catalog, ctx)

        # 5b. Kompozisyon + döviz (TP/YP) dağılımı
        from pipeline.composition import build_composition_payload
        composition_data, currency_data = build_composition_payload(ctx, catalog)

        # 6. Atomik yaz
        timestamp = datetime.now().isoformat()
        out_data = {
            'meta': meta,
            'catalog': catalog['measures'],
            'bank_data': new_bank_data,
            'group_data': group_data,
            'composition_data': composition_data,
            'currency_data': currency_data,
            'timestamp': timestamp,
        }
        tmp = DATA_COMPUTED.with_suffix('.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(out_data, f, ensure_ascii=False, separators=(',', ':'))
        tmp.replace(DATA_COMPUTED)

        # 7. History
        _append_history({
            'timestamp': timestamp,
            'user': user,
            'filename': f'[ZIP-UPLOAD] {file.filename}',
            'banka': '*ALL*',
            'tarih': '*ALL*',
            'file_size': zip_size,
            'status': 'ok',
            'rebuild': True,
            'banks_in_zip': len(banks_in_zip),
            'files_extracted': n_extracted,
        })

        # 8. Spot check
        spot_check = {}
        ta = new_bank_data.get('toplam_aktifler', {}).get('Kuveyt Türk', {})
        if ta:
            # Sadece sayısal değer olan en son dönem
            valid_quarters = [q for q, v in ta.items() if v is not None]
            if valid_quarters:
                latest_q = max(valid_quarters)
                for mid in ['toplam_aktifler', 'krediler', 'mevduat',
                            'ozkaynaklar', 'net_donem_kari']:
                    v = new_bank_data.get(mid, {}).get('Kuveyt Türk', {}).get(latest_q)
                    spot_check[mid] = v
                spot_check['_quarter'] = latest_q

        return JSONResponse({
            'status': 'ok',
            'banks_processed': len(banks_in_zip),
            'files_processed': n_extracted,
            'measures_computed': len(new_bank_data),
            'banks_in_pipeline': len({b for m in new_bank_data.values()
                                       for b in m.keys()}),
            'zip_size': zip_size,
            'started': started,
            'completed': timestamp,
            'spot_check': spot_check,
        })

    except HTTPException:
        raise
    except Exception as exc:
        _append_history({
            'timestamp': datetime.now().isoformat(),
            'user': user,
            'filename': f'[ZIP-UPLOAD-FAILED] {file.filename}',
            'banka': '*ALL*',
            'tarih': '*ALL*',
            'file_size': zip_size,
            'status': 'error',
            'error': f'{type(exc).__name__}: {exc}',
            'rebuild': True,
        })
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f'ZIP upload hatası: {type(exc).__name__}: {exc}',
        )
    finally:
        # Geçici ZIP'i temizle
        try:
            tmp_zip_path.unlink()
        except Exception:
            pass


# ============================================================
# Admin: rebuild — tüm raw'dan baştan hesapla (Faz 3.5)
# ============================================================
@app.post('/admin/rebuild')
async def admin_rebuild(user: str = Depends(require_admin_access)):
    """
    data/raw/ altındaki tüm xlsx'leri tarayıp parquet'i baştan üret,
    compute_all ile tüm computed.json'u yeniden hesapla.

    KULLANIM SENARYOSU:
    - Pipeline'da bug fix yapıldı, tüm geçmişi yeniden hesaplamak gerekiyor
    - İlk seferinde tüm raw veriyi cloud'a yükledikten sonra hepsini işle

    Süre: 27 banka × ~48 çeyrek × 128 measure → ~5-10 dakika
    """
    started = datetime.now().isoformat()

    # Catalog yükle
    if not DATA_CATALOG.exists():
        raise HTTPException(status_code=500, detail='catalog.json yok')
    with open(DATA_CATALOG, encoding='utf-8') as f:
        catalog = json.load(f)
    bank_turu_map = {b['banka_adi']: b['tur'] for b in catalog['banks']}

    # Raw klasörünü kontrol et
    if not DATA_RAW.exists() or not any(DATA_RAW.iterdir()):
        raise HTTPException(
            status_code=400,
            detail=f'data/raw boş. Önce raw xlsx dosyalarını yükleyin.'
        )

    bank_dirs = [d for d in DATA_RAW.iterdir()
                  if d.is_dir() and not d.name.startswith('.')]

    if not bank_dirs:
        raise HTTPException(
            status_code=400,
            detail='data/raw altında banka klasörü yok'
        )

    n_files_total = sum(len(list(d.glob('*.xlsx'))) for d in bank_dirs)

    try:
        # 1. Tüm raw'dan parquet rebuild
        from pipeline.ingest import rebuild_parquet
        rebuild_parquet(DATA_RAW, DATA_PARQUET, bank_turu_map)

        # 2. compute_all — MEASURE_FUNCS'takiler HER ZAMAN taze ham veriden
        # hesaplanır (base_data'da ne olursa olsun override edilir). Ama
        # BASELINE_PASSTHROUGH'taki measure'lar (SYR, RORWA, NIM, Spread gibi
        # ham BDDK ana raporunda hiç bulunmayan ~13 kalem) raw'dan ASLA
        # hesaplanamaz — compute_all bunları base_data'dan olduğu gibi
        # kopyalar. base_data={} verilirse bu kalemler yeni bank_data'da HİÇ
        # OLUŞMAZ (bug: 2026-08-09'da SYR dahil 13 measure tüm rebuild'lerde
        # sessizce kayboluyordu). Düzeltme: mevcut computed.json'daki
        # passthrough değerlerini oku, base_data olarak ver — böylece her
        # rebuild bir öncekinin passthrough verisini taşır (self-sustaining).
        from pipeline import LookupContext, compute_all, build_group_data
        from pipeline.measures import BASELINE_PASSTHROUGH
        ctx = LookupContext.from_parquet(DATA_PARQUET, bank_turu_map)

        passthrough_base = {}
        if DATA_COMPUTED.exists():
            with open(DATA_COMPUTED, encoding='utf-8') as f:
                prev_bank_data = json.load(f).get('bank_data', {})
            passthrough_base = {
                mid: series for mid, series in prev_bank_data.items()
                if mid in BASELINE_PASSTHROUGH
            }

        # FIX (Faz 4): banks AÇIKÇA verilmeli. base_data boş/az olduğunda
        # banks=None ile compute_all banka listesini base_data'dan türetiyor
        # → eksik banka → boş bank_data → canlı veri siliniyordu. KÖK NEDEN BUYDU.
        all_bank_names = [b['banka_adi'] for b in catalog['banks']]
        new_bank_data = compute_all(
            ctx, passthrough_base, catalog, banks=all_bank_names, verbose=False,
        )

        # GÜVENLİK KİLİDİ: boş/şüpheli sonuç → yazma, mevcut veriyi koru
        _assert_nonempty_result(new_bank_data)

        # Statik meta + group_data'yı koru
        meta = {}
        group_data = {}
        if DATA_COMPUTED.exists():
            with open(DATA_COMPUTED, encoding='utf-8') as f:
                old = json.load(f)
            meta = old.get('meta', {})
            group_data = old.get('group_data', {})

        # Dinamik meta'yı (dates, total_periods, top20_by_date, bank_coverage,
        # available_measures) gerçek veriden yeniden üret
        meta = _rebuild_dynamic_meta(meta, new_bank_data, catalog)
        group_data = build_group_data(new_bank_data, catalog, ctx)

        # 3. Atomik yaz
        from pipeline.composition import build_composition_payload
        composition_data, currency_data = build_composition_payload(ctx, catalog)
        timestamp = datetime.now().isoformat()
        out_data = {
            'meta': meta,
            'catalog': catalog['measures'],
            'bank_data': new_bank_data,
            'group_data': group_data,
            'composition_data': composition_data,
            'currency_data': currency_data,
            'timestamp': timestamp,
        }
        tmp = DATA_COMPUTED.with_suffix('.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(out_data, f, ensure_ascii=False, separators=(',', ':'))
        tmp.replace(DATA_COMPUTED)

        # 4. History'e özel rebuild kaydı düş
        _append_history({
            'timestamp': timestamp,
            'user': user,
            'filename': f'[REBUILD] {len(bank_dirs)} banka, {n_files_total} dosya',
            'banka': '*ALL*',
            'tarih': '*ALL*',
            'file_size': 0,
            'status': 'ok',
            'rebuild': True,
        })

        # 5. Spot check — KT için son çeyrek (varsa)
        spot_check = {}
        # En son çeyreği bul
        ta = new_bank_data.get('toplam_aktifler', {}).get('Kuveyt Türk', {})
        if ta:
            latest_q = max(ta.keys())
            for mid in ['toplam_aktifler', 'krediler', 'mevduat',
                        'ozkaynaklar', 'net_donem_kari']:
                v = new_bank_data.get(mid, {}).get('Kuveyt Türk', {}).get(latest_q)
                spot_check[mid] = v

        return JSONResponse({
            'status': 'ok',
            'banks_processed': len(bank_dirs),
            'files_processed': n_files_total,
            'measures_computed': len(new_bank_data),
            'banks_in_pipeline': len({b for m in new_bank_data.values()
                                       for b in m.keys()}),
            'started': started,
            'completed': timestamp,
            'spot_check': spot_check,
        })

    except Exception as exc:
        _append_history({
            'timestamp': datetime.now().isoformat(),
            'user': user,
            'filename': f'[REBUILD-FAILED]',
            'banka': '*ALL*',
            'tarih': '*ALL*',
            'file_size': 0,
            'status': 'error',
            'error': f'{type(exc).__name__}: {exc}',
            'rebuild': True,
        })
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f'Rebuild hatası: {type(exc).__name__}: {exc}',
        )


# ============================================================
# Hata sayfaları
# ============================================================
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(
        {'error': 'Sayfa bulunamadı', 'path': str(request.url.path)},
        status_code=404,
    )


# ============================================================
# Local dev
# ============================================================
if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 7860))
    # NOT (2026-08-11 güvenlik düzeltmesi, 2026-08-12 HOST env ile genişletildi):
    # varsayılan host='127.0.0.1' — sunucu SADECE bu makineden erişilebilir.
    # 0.0.0.0'a geçmek, HTTPS/reverse-proxy olmadan tüm ağa (ofis/ev WiFi veya
    # internet) auth'suz /api/data ve admin paneli açar. Docker+Caddy
    # kurulumunda (bkz. docker-compose.yml) HOST=0.0.0.0 ZORUNLU — ama
    # konteyner dışarıya port açmadığı, sadece Caddy container'ı içeriden
    # erişebildiği için dışa açıklık değişmez, tek public yüzey Caddy kalır.
    # Docker dışı bir ortamda (yerel geliştirme, bu makine) HOST'u ASLA elle
    # 0.0.0.0 yapma.
    host = os.environ.get('HOST', '127.0.0.1')
    uvicorn.run('app:app', host=host, port=port, reload=False)