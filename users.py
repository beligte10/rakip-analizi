"""
users.py
=========
Dosya tabanlı (data/users.json) üyelik sistemi.

Tasarım kararları:
- Kayıt olan HERKES 'pending' durumunda ve Görüntüleyici rolüyle oluşur —
  onaylanana kadar dashboard'a giriş yapamaz.
- Sadece mevcut admin hesabı (app.py::verify_admin — HTTP Basic Auth, ayrı
  ve değişmeden kalır) onaylayabilir/reddedebilir/rol atayabilir.
- ROL (2026-09-30): 'role' alanı roles.py'deki bir rol kimliğidir
  (goruntuleyici | analist | veri_yoneticisi | admin | admin panelden
  eklenen roller); izinler rolden gelir. Eski 'member' kayıtları okurken
  Görüntüleyici'ye çevrilir (roles.resolve_id).
- Şifreler bcrypt ile hash'lenir; düz metin hiçbir yerde saklanmaz/loglanmaz.
- Tüm oku-değiştir-yaz işlemleri _users_file_lock (threading.Lock) ile
  korunuyor (2026-08-12 düzeltmesi) — eşzamanlı iki yazma isteği artık
  birbirinin verisini sessizce silemiyor. Atomik dosya yazımı (.tmp +
  replace) ayrıca uygulanıyor, diğer data/*.json dosyalarıyla tutarlı.
"""
from __future__ import annotations
import json
import math
import os
import re
import secrets
import threading
import bcrypt
from datetime import datetime
from pathlib import Path
from typing import Optional

import roles as roles_mod
from pipeline import custom_measure_rules as cm_rules

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MIN_PASSWORD_LEN = 8

# Kayıt olabilecek e-posta uzantıları (2026-08-12): kurumsal domain +
# admin.local (upsert_admin_account'un kendi admin hesabı için kullandığı
# sentetik domain, bkz. app.py::ensure_data_dir).
ALLOWED_SIGNUP_DOMAINS = {'kuveytturk.com.tr', 'admin.local'}

# Bu modüldeki TÜM oku-değiştir-yaz (_load + değiştir + _save) adımlarını
# korur (2026-08-12 düzeltmesi): kilit olmadan, iki eşzamanlı yazma isteği
# (örn. bir kayıt + bir admin onayı aynı anda) aynı users.json anlık
# görüntüsünü okuyup üstüne yazabiliyor — hangisi son yazarsa diğerinin
# değişikliği sessizce kayboluyordu (veri kaybı, hata fırlatılmıyor).
# Uygulama tek process/tek worker olarak çalıştığı sürece (bkz.
# app.py::uvicorn.run, --workers verilmiyor) bir threading.Lock yeterli;
# süreç sayısı artarsa (örn. gunicorn multi-worker) bu YETERSİZ kalır,
# process-level bir kilit (fcntl.flock) gerekir.
_users_file_lock = threading.Lock()


def ensure_users_file(path: Path) -> None:
    if not path.exists():
        path.write_text(json.dumps({'users': []}, ensure_ascii=False, indent=2))


def _load(path: Path) -> dict:
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    # Geriye dönük uyumluluk (2026-08-12 rol özelliği eklendi): eski
    # kayıtlarda 'role' alanı yok — okurken varsayılan rol atanır; 2026-09-30
    # rol kimliklerine geçişte 'member' → Görüntüleyici.
    # (2026-09-17: aynı desenle custom_measures/saved_views eklendi —
    # bkz. add_custom_measure/add_saved_view.)
    for u in data.get('users', []):
        u['role'] = roles_mod.ESKI_ROLLER.get(u.get('role') or 'member', u.get('role'))
        u.setdefault('custom_measures', [])
        u.setdefault('saved_views', [])
    return data


def _save(path: Path, data: dict) -> None:
    """
    Atomik yazma — geçici dosya adı PID+random ile BENZERSİZ (2026-08-12
    düzeltmesi): sabit bir '.tmp' adı kullanılıyordu, bu da app.py'nin
    (ensure_data_dir üzerinden) yanlışlıkla birden fazla süreçte eşzamanlı
    çalıştığı durumda ("BrokenProcessPool" bug'ı, bkz. app.py yorumu) bir
    sürecin diğerinin .tmp dosyasını silmesine ve FileNotFoundError'a yol
    açıyordu. Kök neden ayrıca düzeltildi ama bu fonksiyon da tek başına
    güvenli olmalı — defense in depth.
    """
    tmp = path.with_name(f'{path.stem}.{os.getpid()}.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


_SAHTE_HASH = bcrypt.hashpw(b'zamanlama-denemesi', bcrypt.gensalt()).decode('utf-8')


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode('utf-8'), hashed.encode('utf-8'))
    except (ValueError, TypeError):
        return False


def create_signup(path: Path, name: str, email: str, password: str) -> tuple[bool, str]:
    """Yeni başvuru oluştur. Başarılıysa (True, ''), değilse (False, sebep)."""
    name = (name or '').strip()
    email = (email or '').strip().lower()

    if not name:
        return False, 'İsim boş olamaz'
    if not EMAIL_RE.match(email):
        return False, 'Geçerli bir e-posta adresi girin'
    domain = email.rsplit('@', 1)[-1]
    if domain not in ALLOWED_SIGNUP_DOMAINS:
        return False, 'Sadece kuveytturk.com.tr uzantılı kurumsal e-posta adresleriyle başvuru yapılabilir'
    if len(password or '') < MIN_PASSWORD_LEN:
        return False, f'Şifre en az {MIN_PASSWORD_LEN} karakter olmalı'

    with _users_file_lock:
        data = _load(path)
        if any(u['email'] == email for u in data['users']):
            return False, 'Bu e-posta ile zaten bir başvuru/hesap mevcut'

        new_id = max((u['id'] for u in data['users']), default=0) + 1
        data['users'].append({
            'id': new_id,
            'name': name,
            'email': email,
            'password_hash': hash_password(password),
            'status': 'pending',  # pending | approved | rejected
            'role': roles_mod.VARSAYILAN_ROL,
            'created_at': datetime.now().isoformat(),
            'approved_at': None,
            'approved_by': None,
        })
        _save(path, data)
    return True, ''


def admin_create_user(path: Path, name: str, email: str, password: str,
                      created_by: str) -> tuple[bool, str]:
    """Admin, self-signup + onay adımlarını atlayıp doğrudan ONAYLI bir üye
    ekler (2026-09-09). create_signup ile aynı doğrulamalar (isim, e-posta
    formatı, kurumsal domain, şifre uzunluğu, tekil e-posta) geçerli — tek
    fark, kayıt 'pending' değil doğrudan 'approved' olarak oluşturulur.
    Başarılıysa (True, ''), değilse (False, sebep)."""
    name = (name or '').strip()
    email = (email or '').strip().lower()

    if not name:
        return False, 'İsim boş olamaz'
    if not EMAIL_RE.match(email):
        return False, 'Geçerli bir e-posta adresi girin'
    domain = email.rsplit('@', 1)[-1]
    if domain not in ALLOWED_SIGNUP_DOMAINS:
        return False, 'Sadece kuveytturk.com.tr uzantılı kurumsal e-posta adresleriyle üye eklenebilir'
    if len(password or '') < MIN_PASSWORD_LEN:
        return False, f'Şifre en az {MIN_PASSWORD_LEN} karakter olmalı'

    with _users_file_lock:
        data = _load(path)
        if any(u['email'] == email for u in data['users']):
            return False, 'Bu e-posta ile zaten bir başvuru/hesap mevcut'

        new_id = max((u['id'] for u in data['users']), default=0) + 1
        now = datetime.now().isoformat()
        data['users'].append({
            'id': new_id,
            'name': name,
            'email': email,
            'password_hash': hash_password(password),
            'status': 'approved',
            'role': roles_mod.VARSAYILAN_ROL,
            'created_at': now,
            'approved_at': now,
            'approved_by': created_by,
        })
        _save(path, data)
    return True, ''


def authenticate(path: Path, email: str, password: str) -> tuple[Optional[dict], str]:
    """Başarılıysa (user_dict, ''), değilse (None, hata_mesajı)."""
    email = (email or '').strip().lower()
    data = _load(path)
    user = next((u for u in data['users'] if u['email'] == email), None)

    # Kullanıcı yok VEYA şifre yanlış — aynı hata mesajı (e-posta enumeration'ı önlemek için).
    # Kullanıcı yokken de bcrypt çalıştırılır: yanıt süresi farkıyla hesap varlığı anlaşılamasın (2026-10-04).
    if not user:
        verify_password(password or '', _SAHTE_HASH)
        return None, 'E-posta veya şifre hatalı'
    if not verify_password(password, user['password_hash']):
        return None, 'E-posta veya şifre hatalı'
    if user['status'] == 'pending':
        return None, 'Hesabınız henüz onay bekliyor — admin onayladıktan sonra giriş yapabilirsiniz'
    if user['status'] == 'rejected':
        return None, 'Başvurunuz reddedildi'
    return user, ''


def get_user_by_id(path: Path, user_id: int) -> Optional[dict]:
    data = _load(path)
    return next((u for u in data['users'] if u['id'] == user_id), None)


def get_user_by_email(path: Path, email: str) -> Optional[dict]:
    email = (email or '').strip().lower()
    data = _load(path)
    return next((u for u in data['users'] if u['email'] == email and u['status'] == 'approved'), None)


def count_by_role(path: Path) -> dict:
    """Rol kimliği → o roldeki onaylı kullanıcı sayısı."""
    out: dict = {}
    for u in _load(path)['users']:
        if u['status'] == 'approved':
            out[u['role']] = out.get(u['role'], 0) + 1
    return out


def set_focus_bank(path: Path, user_id: int, banka: Optional[str],
                   rakipler: Optional[list] = None) -> bool:
    """Kullanıcının kendi odak bankası (2026-10-02). None/'' → admin varsayılanına döner.
    rakipler (2026-10-03): kullanıcının bu odak için seçtiği rakip listesi; None → odak bankaya
    göre otomatik kurulan liste."""
    with _users_file_lock:
        data = _load(path)
        u = next((x for x in data['users'] if x['id'] == user_id), None)
        if u is None:
            return False
        if banka:
            u['odak_banka'] = banka
        else:
            u.pop('odak_banka', None)
        if rakipler:
            u['rakipler'] = list(rakipler)
        else:
            u.pop('rakipler', None)
        _save(path, data)
        return True


def list_users(path: Path) -> list[dict]:
    """Şifre hash'i HARİÇ tüm alanlar (admin panelde gösterilecek)."""
    data = _load(path)
    return [{k: v for k, v in u.items() if k != 'password_hash'} for u in data['users']]


def upsert_admin_account(path: Path, email: str, name: str, password: str) -> None:
    """
    Admin'in KENDİ Basic Auth şifresiyle üyelik sistemi üzerinden de
    (session tabanlı) dashboard'a giriş yapabilmesi için — aksi halde
    admin ayrı bir üye hesabı açıp kendi onayını beklemesi gibi saçma bir
    duruma düşerdi. Her sunucu başlangıcında çağrılır, idempotent:
    - Kayıt yoksa oluşturur (status='approved').
    - Kayıt varsa şifre hash'ini GÜNCEL parola ile senkronize eder (env
      değişkeni KT_PASSWORD değişirse eski hash'te takılı kalmasın diye).
    """
    email = email.strip().lower()
    with _users_file_lock:
        data = _load(path)
        existing = next((u for u in data['users'] if u['email'] == email), None)
        new_hash = hash_password(password)
        if existing:
            existing['password_hash'] = new_hash
            existing['status'] = 'approved'
            existing['role'] = 'admin'
        else:
            new_id = max((u['id'] for u in data['users']), default=0) + 1
            now = datetime.now().isoformat()
            data['users'].append({
                'id': new_id,
                'name': name,
                'email': email,
                'password_hash': new_hash,
                'status': 'approved',
                'role': 'admin',
                'created_at': now,
                'approved_at': now,
                'approved_by': 'system',
            })
        _save(path, data)


def set_status(path: Path, user_id: int, status: str, approved_by: str) -> bool:
    with _users_file_lock:
        data = _load(path)
        for u in data['users']:
            if u['id'] == user_id:
                u['status'] = status
                if status == 'approved':
                    u['approved_at'] = datetime.now().isoformat()
                    u['approved_by'] = approved_by
                _save(path, data)
                return True
    return False


def change_password(path: Path, user_id: int, current_password: str,
                    new_password: str) -> tuple[bool, str]:
    """Kullanıcı kendi şifresini değiştirir (2026-08-15). Mevcut şifre
    doğrulanır, yeni şifre uzunluk kontrolünden geçer, bcrypt ile yeniden
    hash'lenir. Başarılıysa (True, ''), değilse (False, sebep).

    NOT: Env-senkron admin hesapları (…@admin.local) upsert_admin_account
    tarafından her başlangıçta KT_PASSWORD'e sıfırlandığından, onların
    şifresi bu yolla kalıcı değiştirilemez — çağıran katman (app.py) bu
    hesapları ayrıca engeller."""
    if len(new_password or '') < MIN_PASSWORD_LEN:
        return False, f'Yeni şifre en az {MIN_PASSWORD_LEN} karakter olmalı'
    with _users_file_lock:
        data = _load(path)
        user = next((u for u in data['users'] if u['id'] == user_id), None)
        if not user:
            return False, 'Kullanıcı bulunamadı'
        if not verify_password(current_password, user['password_hash']):
            return False, 'Mevcut şifre hatalı'
        user['password_hash'] = hash_password(new_password)
        _save(path, data)
    return True, ''


def admin_reset_password(path: Path, user_id: int, new_password: str) -> tuple[bool, str]:
    """Admin, başka bir üyenin ŞİFRESİNİ UNUTMASI durumunda mevcut şifreyi
    bilmeden yeni bir şifre atar (2026-09-09) — change_password'dan farkı bu:
    orada kullanıcı kendi mevcut şifresini doğrulamak zorunda, burada admin
    doğrudan atıyor. Aynı uzunluk kuralına tabi. Başarılıysa (True, ''),
    değilse (False, sebep)."""
    if len(new_password or '') < MIN_PASSWORD_LEN:
        return False, f'Yeni şifre en az {MIN_PASSWORD_LEN} karakter olmalı'
    with _users_file_lock:
        data = _load(path)
        user = next((u for u in data['users'] if u['id'] == user_id), None)
        if not user:
            return False, 'Kullanıcı bulunamadı'
        user['password_hash'] = hash_password(new_password)
        _save(path, data)
    return True, ''


def set_role(path: Path, user_id: int, role: str, roles_path: Optional[Path] = None) -> bool:
    """role: roles.json'daki bir rol kimliği (2026-09-30). roles_path
    verilmezse users.json'un yanındaki roles.json kullanılır."""
    if not roles_mod.exists(roles_path or path.with_name('roles.json'), role):
        return False
    with _users_file_lock:
        data = _load(path)
        for u in data['users']:
            if u['id'] == user_id:
                u['role'] = role
                _save(path, data)
                return True
    return False


# ============================================================
# Özel ölçüler (custom measures) + kayıtlı görünümler (saved views)
# (2026-09-17) — kullanıcı mevcut 160 ölçüyü (catalog.json) birleştirerek
# kendi ölçüsünü kurup profiline kaydedebiliyor, istediği ölçüleri seçip
# adlandırılmış bir "Görünüm" olarak da saklayabiliyor. Her ikisi de
# SADECE kendi kullanıcısına özel — app.py::require_member ile korunan
# /api/my/* uçlarından erişiliyor, başka kullanıcı/admin göremiyor.
#
# Formül gövdesi bilerek burada hesaplanmıyor — istemci tarafında
# (frontend/index_v30.html::injectCustomMeasures) hesaplanıyor, çünkü ölçü
# değerleri zaten computed.json'da hazır. Burası sadece TANIMI saklıyor.
#
# Tanım biçimi (2026-09-25): yeni/güncellenen kayıtlar formülü ifade ağacı
# olarak 'expr' alanında tutar (bkz. pipeline/custom_measure_rules). Eski
# tek işlemli kayıtlar (op/a/b/constant/bicim) diskte olduğu gibi kalır ve
# okunurken custom_measure_rules.record_expr ile ağaca çevrilir. Burada
# yalnız ad/sıralama ve ağacın YAPISI doğrulanır; ölçülerin katalogda olup
# olmadığı ve birim uyumu (anlam) app.py'de katalogla birlikte kontrol edilir.
# ============================================================
CUSTOM_MEASURE_OPS = {'ratio', 'diff', 'sum', 'scale'}
# Oran sonucunun biçimi: 'pct' (×100, %), 'kat' (×1). None = ölçü çiftinin
# varsayılanı (bkz. pipeline/custom_measure_rules.ratio_formats).
CUSTOM_MEASURE_BICIMLER = {None, 'pct', 'kat'}
MAX_AD_LEN = 60
_LEGACY_FIELDS = ('op', 'a', 'b', 'constant', 'bicim')


def _find(items: list, item_id: str) -> Optional[dict]:
    return next((x for x in items if x['id'] == item_id), None)


def _ad_key(ad: str) -> str:
    return ' '.join((ad or '').split()).casefold()


def _ad_cakisiyor(existing: list, ad: str, haric_id: Optional[str] = None) -> bool:
    key = _ad_key(ad)
    return any(_ad_key(m['ad']) == key for m in existing if m['id'] != haric_id)


def _validate_legacy_def(op: str, a: Optional[str], b: Optional[str],
                         constant, bicim: Optional[str]) -> tuple[bool, str]:
    if op not in CUSTOM_MEASURE_OPS:
        return False, f"Geçersiz işlem: '{op}'"
    if not (a or '').strip():
        return False, 'Ölçü A seçilmeli'
    if op == 'scale':
        if (constant is None or isinstance(constant, bool)
                or not isinstance(constant, (int, float)) or not math.isfinite(constant)):
            return False, 'A×Sabit için sayısal bir sabit girilmeli'
        if constant == 0:
            return False, 'Sabit 0 olamaz (sonuç her zaman 0 olur)'
    else:
        if not (b or '').strip():
            return False, 'Ölçü B seçilmeli'
    if bicim not in CUSTOM_MEASURE_BICIMLER:
        return False, f"Geçersiz biçim: '{bicim}'"
    return True, ''


def _resolve_custom_measure(ad: str, op: Optional[str], a: Optional[str], b: Optional[str],
                            constant, sort_direction: str, bicim: Optional[str],
                            expr: Optional[dict]) -> tuple[Optional[dict], str]:
    """Doğrular; (kaydedilecek_ağaç, '') ya da (None, hata_mesajı).
    expr verilmişse eski alanlar (op/a/b/constant/bicim) yok sayılır."""
    ad = (ad or '').strip()
    if not ad:
        return None, 'Ölçü adı boş olamaz'
    if len(ad) > MAX_AD_LEN:
        return None, f'Ölçü adı en fazla {MAX_AD_LEN} karakter olabilir'
    if expr is None:
        ok, err = _validate_legacy_def(op, a, b, constant, bicim)
        if not ok:
            return None, err
        expr = cm_rules.legacy_to_expr(op, a, b, constant, bicim if op == 'ratio' else None)
    err = cm_rules.check_shape(expr)
    if err:
        return None, err
    if sort_direction not in ('asc', 'desc'):
        return None, "sort_direction 'asc' veya 'desc' olmalı"
    return expr, ''


def add_custom_measure(path: Path, user_id: int, ad: str, op: Optional[str] = None,
                       a: Optional[str] = None, b: Optional[str] = None,
                       constant: Optional[float] = None,
                       sort_direction: str = 'desc',
                       bicim: Optional[str] = None,
                       expr: Optional[dict] = None) -> tuple[bool, object]:
    """Başarılıysa (True, yeni_kayit_dict), değilse (False, hata_mesaji)."""
    tree, err = _resolve_custom_measure(ad, op, a, b, constant, sort_direction, bicim, expr)
    if tree is None:
        return False, err
    record = {'id': 'custom_' + secrets.token_hex(4),
              'ad': ' '.join(ad.split()), 'expr': tree, 'sort_direction': sort_direction,
              'created_at': datetime.now().isoformat()}
    with _users_file_lock:
        data = _load(path)
        user = _find(data['users'], user_id)
        if not user:
            return False, 'Kullanıcı bulunamadı'
        if _ad_cakisiyor(user['custom_measures'], ad):
            return False, 'Bu adla bir özel ölçünüz zaten var'
        user['custom_measures'].append(record)
        _save(path, data)
    return True, record


def update_custom_measure(path: Path, user_id: int, measure_id: str, ad: str,
                          op: Optional[str] = None, a: Optional[str] = None,
                          b: Optional[str] = None,
                          constant: Optional[float] = None,
                          sort_direction: str = 'desc',
                          bicim: Optional[str] = None,
                          expr: Optional[dict] = None) -> tuple[bool, object]:
    tree, err = _resolve_custom_measure(ad, op, a, b, constant, sort_direction, bicim, expr)
    if tree is None:
        return False, err
    with _users_file_lock:
        data = _load(path)
        user = _find(data['users'], user_id)
        if not user:
            return False, 'Kullanıcı bulunamadı'
        record = _find(user['custom_measures'], measure_id)
        if not record:
            return False, 'Özel ölçü bulunamadı'
        if _ad_cakisiyor(user['custom_measures'], ad, haric_id=measure_id):
            return False, 'Bu adla bir özel ölçünüz zaten var'
        for k in _LEGACY_FIELDS:   # eski biçimden ağaca geçiş
            record.pop(k, None)
        record.update({'ad': ' '.join(ad.split()), 'expr': tree,
                       'sort_direction': sort_direction})
        _save(path, data)
        return True, record


def delete_custom_measure(path: Path, user_id: int, measure_id: str) -> bool:
    """Siler; ayrıca bu kullanıcının saved_views'larındaki measure_ids
    listelerinden de temizler (2026-09-17) — aksi halde bir Görünüm,
    artık var olmayan bir ölçüye sessizce referans vermeye devam ederdi."""
    with _users_file_lock:
        data = _load(path)
        user = _find(data['users'], user_id)
        if not user:
            return False
        before = len(user['custom_measures'])
        user['custom_measures'] = [m for m in user['custom_measures'] if m['id'] != measure_id]
        if len(user['custom_measures']) == before:
            return False
        for v in user['saved_views']:
            v['measure_ids'] = [mid for mid in v['measure_ids'] if mid != measure_id]
        _save(path, data)
        return True


def list_custom_measures(path: Path, user_id: int) -> list[dict]:
    user = get_user_by_id(path, user_id)
    return list(user['custom_measures']) if user else []


def _validate_saved_view(ad: str, measure_ids: list) -> tuple[bool, str]:
    ad = (ad or '').strip()
    if not ad:
        return False, 'Görünüm adı boş olamaz'
    if len(ad) > MAX_AD_LEN:
        return False, f'Görünüm adı en fazla {MAX_AD_LEN} karakter olabilir'
    if not measure_ids or not isinstance(measure_ids, list):
        return False, 'Görünüm en az 1 ölçü içermeli'
    return True, ''


def add_saved_view(path: Path, user_id: int, ad: str, measure_ids: list) -> tuple[bool, object]:
    ok, err = _validate_saved_view(ad, measure_ids)
    if not ok:
        return False, err
    record = {
        'id': 'view_' + secrets.token_hex(4),
        'ad': ad.strip(),
        'measure_ids': list(measure_ids),
        'created_at': datetime.now().isoformat(),
    }
    with _users_file_lock:
        data = _load(path)
        user = _find(data['users'], user_id)
        if not user:
            return False, 'Kullanıcı bulunamadı'
        user['saved_views'].append(record)
        _save(path, data)
    return True, record


def update_saved_view(path: Path, user_id: int, view_id: str, ad: str,
                      measure_ids: list) -> tuple[bool, object]:
    ok, err = _validate_saved_view(ad, measure_ids)
    if not ok:
        return False, err
    with _users_file_lock:
        data = _load(path)
        user = _find(data['users'], user_id)
        if not user:
            return False, 'Kullanıcı bulunamadı'
        record = _find(user['saved_views'], view_id)
        if not record:
            return False, 'Görünüm bulunamadı'
        record.update({'ad': ad.strip(), 'measure_ids': list(measure_ids)})
        _save(path, data)
        return True, record


def delete_saved_view(path: Path, user_id: int, view_id: str) -> bool:
    with _users_file_lock:
        data = _load(path)
        user = _find(data['users'], user_id)
        if not user:
            return False
        before = len(user['saved_views'])
        user['saved_views'] = [v for v in user['saved_views'] if v['id'] != view_id]
        if len(user['saved_views']) == before:
            return False
        _save(path, data)
        return True


def list_saved_views(path: Path, user_id: int) -> list[dict]:
    user = get_user_by_id(path, user_id)
    return list(user['saved_views']) if user else []
