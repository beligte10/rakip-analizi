"""
users.py
=========
Dosya tabanlı (data/users.json) üyelik sistemi.

Tasarım kararları:
- Kayıt olan HERKES 'pending' durumunda ve role='member' olarak oluşur —
  dashboard'a giriş yapamaz.
- Sadece mevcut admin hesabı (app.py::verify_admin — HTTP Basic Auth, ayrı
  ve değişmeden kalır) onaylayabilir/reddedebilir/rol atayabilir.
- ROL (2026-08-12 eklendi): 'member' (varsayılan) sadece dashboard'u
  görüntüler; 'admin' TÜM admin panel yetkilerine sahiptir (upload/
  rebuild/ZIP/üyelik onayı/banka grubu düzenleme — bkz.
  app.py::require_admin_access). Admin, onaylı bir üyeye admin panelden
  rol atayabilir — bu, ikinci bir "tam yetkili admin" hesabı yaratır
  (Basic Auth hesabıyla eş değer, ayrı bir kısıtlama katmanı YOK).
- Şifreler bcrypt ile hash'lenir; düz metin hiçbir yerde saklanmaz/loglanmaz.
- Tüm oku-değiştir-yaz işlemleri _users_file_lock (threading.Lock) ile
  korunuyor (2026-08-12 düzeltmesi) — eşzamanlı iki yazma isteği artık
  birbirinin verisini sessizce silemiyor. Atomik dosya yazımı (.tmp +
  replace) ayrıca uygulanıyor, diğer data/*.json dosyalarıyla tutarlı.
"""
from __future__ import annotations
import json
import os
import re
import threading
import bcrypt
from datetime import datetime
from pathlib import Path
from typing import Optional

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
    # kayıtlarda 'role' alanı yok — okurken varsayılan 'member' atanır.
    for u in data.get('users', []):
        u.setdefault('role', 'member')
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
            'role': 'member',     # member | admin (2026-08-12) — sadece admin atayabilir
            'created_at': datetime.now().isoformat(),
            'approved_at': None,
            'approved_by': None,
        })
        _save(path, data)
    return True, ''


def authenticate(path: Path, email: str, password: str) -> tuple[Optional[dict], str]:
    """Başarılıysa (user_dict, ''), değilse (None, hata_mesajı)."""
    email = (email or '').strip().lower()
    data = _load(path)
    user = next((u for u in data['users'] if u['email'] == email), None)

    # Kullanıcı yok VEYA şifre yanlış — aynı hata mesajı (e-posta enumeration'ı önlemek için)
    if not user or not verify_password(password, user['password_hash']):
        return None, 'E-posta veya şifre hatalı'
    if user['status'] == 'pending':
        return None, 'Hesabınız henüz onay bekliyor — admin onayladıktan sonra giriş yapabilirsiniz'
    if user['status'] == 'rejected':
        return None, 'Başvurunuz reddedildi'
    return user, ''


def get_user_by_id(path: Path, user_id: int) -> Optional[dict]:
    data = _load(path)
    return next((u for u in data['users'] if u['id'] == user_id), None)


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


def set_role(path: Path, user_id: int, role: str) -> bool:
    """role: 'member' | 'admin'. Admin rolü, tüm admin panel yetkilerini
    (upload/rebuild/ZIP/üyelik onayı/grup düzenleme) verir — bkz.
    app.py::require_admin_access (2026-08-12)."""
    if role not in ('member', 'admin'):
        return False
    with _users_file_lock:
        data = _load(path)
        for u in data['users']:
            if u['id'] == user_id:
                u['role'] = role
                _save(path, data)
                return True
    return False
