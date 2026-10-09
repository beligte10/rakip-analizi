"""
roles.py
========
Rol bazlı erişim (2026-09-30) — data/roles.json.

Her rol bir izin listesi ve asistan için günlük soru sınırı taşır. Admin
panelden yeni rol eklenip izinler kutucuklarla açılıp kapatılabilir. Kullanıcı
kaydındaki 'role' alanı rol kimliğini tutar (users.py).

- Hazır roller: Görüntüleyici (yalnız pano), Analist, Veri Yöneticisi, Admin.
  Hazır roller silinemez; Admin'in izinleri değiştirilemez (panelden kilitlenme
  olmasın), yalnız günlük soru sınırı değişir.
- Eski kayıtlar: 'member' → Görüntüleyici (kullanıcı kararı: mevcut üyeler
  görüntüleyici olarak başlar), bilinmeyen/silinmiş rol → Görüntüleyici.
- Basic Auth kök hesabı (KT_USERNAME/KT_PASSWORD) her zaman tüm izinlere sahip.
- Dışa aktarma izinleri arayüzde uygulanır: pano verisi (/api/data) tarayıcıya
  zaten tam geldiği için sunucu dosya üretimini engelleyemez.
"""
from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# (anahtar, ad, bölüm, açıklama) — sıra admin paneldeki satır sırasıdır.
IZINLER: List[Tuple[str, str, str, str]] = [
    ('asistan', 'AI asistan', 'Özellikler', 'Sohbet paneli; pano verisi üzerinde soru sorma'),
    ('asistan_dis_veri', 'Asistan: dış veri (TCMB EVDS)', 'Özellikler',
     'Asistanın EVDS gibi dış kaynaklardan makro veri çekmesi (AI asistan izniyle birlikte çalışır)'),
    ('rekabet_analizi', 'Rekabet Analizi ölçüleri', 'Özellikler',
     'Rekabet Analizi kategorisindeki ölçüleri (ZK sürüklemesi, TÜFEX, LCR vb.) pano, dışa aktarma ve asistanda görme; '
     'izni olmayan kullanıcıya bu ölçüler sunucudan hiç gönderilmez'),
    ('olcu_olustur', 'Ölçü Oluştur ve Görünümlerim', 'Özellikler', 'Özel ölçü tanımlama ve görünüm kaydetme'),
    ('export_veri', 'Veri dışa aktarma (Excel)', 'Özellikler', 'Dışa Aktar sekmesi ve tablolardan Excel indirme'),
    ('export_gorsel', 'Görsel dışa aktarma (PNG / PDF)', 'Özellikler', 'Grafik PNG ve sayfa PDF çıktısı'),
    ('odak_banka', 'Odak banka seçimi', 'Özellikler',
     'Kullanıcı kendi odak bankasını seçebilir; izni olmayan admin panelindeki varsayılanı görür'),
    ('sekme_trend', 'Trend sekmesi', 'Ekran', 'Trend görünümü (ölçü zaman serisi) sekmesi'),
    ('sekme_kompozisyon', 'Kompozisyon sekmesi', 'Ekran', 'Kompozisyon (bileşen dağılımı) sekmesi'),
    ('kart_siralama', 'Kart: Banka sıralaması', 'Ekran', 'Anlık Görünüm\'ün solundaki banka sıralaması listesi'),
    ('kart_ytd', 'Kart: YtD Büyüme / Rasyo özeti', 'Ekran', 'Tüm Banka YtD Büyüme kartı (rasyolarda Banka Grupları Rasyo kartı)'),
    ('kart_gruplar', 'Kart: Banka Grupları', 'Ekran', 'Banka Grupları büyüme / çeyreklik değişim kartı'),
    ('kart_rakipler', 'Kart: Rakip Bankalar', 'Ekran', 'Rakip Bankalar yıllık görünüm ve CAGR kartı'),
    ('menu_bdr', 'Menü: BDR', 'Ekran', 'Menüdeki BDR düğmesi'),
    ('admin_veri', 'Veri durumu, yükleme ve yedekler', 'Admin paneli',
     'Veri Durumu, Veri Yükleme, Yükleme Geçmişi; yeniden hesaplama ve veri yedeği'),
    ('admin_gruplar', 'Banka grupları', 'Admin paneli', 'Grup üyeliklerini düzenleme, grup ekleme/silme'),
    ('admin_kullanicilar', 'Kullanıcılar ve roller', 'Admin paneli',
     'Üyelik onayı, rol atama, şifre sıfırlama, rol tanımları'),
    ('admin_proje', 'Görev panosu, backlog ve el kitabı', 'Admin paneli', 'Proje yönetimi sekmeleri'),
]
IZIN_ANAHTARLARI = [k for k, *_ in IZINLER]
ADMIN_IZINLERI = [k for k in IZIN_ANAHTARLARI if k.startswith('admin_')]
# Ekran izinleri (2026-10-09): sonradan eklendi; mevcut TÜM rollere (özel roller dahil) varsayılan olarak açık eklenir,
# böylece bugün görünen ekran öğeleri kimseden kapanmaz.
EKRAN_IZINLERI = [k for k, _ad, bolum, _a in IZINLER if bolum == 'Ekran']
# Ölçü kategorisi gizleme: rolün 'izinler' listesindeki 'gizle:<kategori>' girdileri (varsayılan: hepsi görünür).
GIZLE_ON_EK = 'gizle:'


def yetki_izinleri(izinler) -> List[str]:
    """Yetki yükseltme denetimlerinde sayılan izinler: 'gizle:<kategori>' kısıtları ve salt-görünüm 'Ekran' izinleri
    (sekme/kart/menü) bir yetki genişletmesi değildir, sayılmaz."""
    return [k for k in (izinler or []) if not str(k).startswith(GIZLE_ON_EK) and k not in EKRAN_IZINLERI]


def gizli_kategoriler(izinler) -> List[str]:
    return [str(k)[len(GIZLE_ON_EK):] for k in (izinler or []) if str(k).startswith(GIZLE_ON_EK)]


def _izin_gecerli(k) -> bool:
    return k in IZIN_ANAHTARLARI or (isinstance(k, str) and k.startswith(GIZLE_ON_EK) and 1 < len(k) - len(GIZLE_ON_EK) <= 80)


def _izin_sirala(izinler) -> List[str]:
    kume = set(izinler or [])
    return [k for k in IZIN_ANAHTARLARI if k in kume] + sorted(k for k in kume if str(k).startswith(GIZLE_ON_EK) and _izin_gecerli(k))

VARSAYILAN_ROL = 'goruntuleyici'
ADMIN_ROL = 'admin'
GUNLUK_MIN, GUNLUK_MAX = 0, 2000

_ANALIST = ['asistan', 'asistan_dis_veri', 'rekabet_analizi', 'olcu_olustur', 'export_veri', 'export_gorsel', 'odak_banka'] + list(EKRAN_IZINLERI)
# Sonradan eklenen izinler: mevcut roles.json'daki HAZIR rollere varsayılanları bir kez eklenir
# (bkz. _normalize, 'bilinen_izinler'); admin'in sonradan kaldırdığı izin geri gelmez.
SONRADAN_EKLENEN = {'odak_banka', 'rekabet_analizi'} | set(EKRAN_IZINLERI)
HAZIR_ROLLER: List[dict] = [
    {'id': 'goruntuleyici', 'ad': 'Görüntüleyici', 'izinler': list(EKRAN_IZINLERI), 'asistan_gunluk': 0, 'hazir': True},
    {'id': 'analist', 'ad': 'Analist', 'izinler': list(_ANALIST), 'asistan_gunluk': 50, 'hazir': True},
    {'id': 'veri_yoneticisi', 'ad': 'Veri Yöneticisi',
     'izinler': _ANALIST + ['admin_veri', 'admin_gruplar'], 'asistan_gunluk': 100, 'hazir': True},
    {'id': ADMIN_ROL, 'ad': 'Admin', 'izinler': list(IZIN_ANAHTARLARI), 'asistan_gunluk': 300, 'hazir': True},
]
ESKI_ROLLER = {'member': VARSAYILAN_ROL}
_ID_RE = re.compile(r'^[a-z0-9_]{2,32}$')

_lock = threading.Lock()


def _defaults() -> dict:
    return {'roles': json.loads(json.dumps(HAZIR_ROLLER)), 'bilinen_izinler': list(IZIN_ANAHTARLARI)}


def _normalize(data: dict) -> dict:
    """Eksik hazır rolleri ekler, izinleri bilinen anahtarlara indirger, Admin'i
    her zaman tam yetkili tutar."""
    roles = [r for r in data.get('roles', []) if isinstance(r, dict) and _ID_RE.match(str(r.get('id', '')))]
    bilinen = data.get('bilinen_izinler')
    if bilinen is None:
        bilinen = [k for k in IZIN_ANAHTARLARI if k not in SONRADAN_EKLENEN]
    yeni = [k for k in IZIN_ANAHTARLARI if k not in set(bilinen)]
    hazir_izin = {h['id']: set(h['izinler']) for h in HAZIR_ROLLER}
    for r in roles:
        if yeni and r.get('id') in hazir_izin:
            r['izinler'] = list(r.get('izinler') or []) + [k for k in yeni if k in hazir_izin[r['id']]]
        elif yeni:   # özel roller: yalnız ekran izinleri varsayılan açık gelir
            r['izinler'] = list(r.get('izinler') or []) + [k for k in yeni if k in EKRAN_IZINLERI]
    have = {r['id'] for r in roles}
    for h in HAZIR_ROLLER:
        if h['id'] not in have:
            roles.append(json.loads(json.dumps(h)))
    for r in roles:
        r['hazir'] = r['id'] in {h['id'] for h in HAZIR_ROLLER}
        r['izinler'] = _izin_sirala(r.get('izinler'))
        r['asistan_gunluk'] = _gunluk(r.get('asistan_gunluk'))
        r['ad'] = str(r.get('ad') or r['id'])[:40]
        if r['id'] == ADMIN_ROL:
            r['izinler'] = list(IZIN_ANAHTARLARI)
    return {'roles': roles, 'bilinen_izinler': list(IZIN_ANAHTARLARI)}


def _gunluk(v) -> int:
    try:
        return max(GUNLUK_MIN, min(GUNLUK_MAX, int(v)))
    except (TypeError, ValueError):
        return 0


def _load(path: Path) -> dict:
    try:
        with open(path, encoding='utf-8') as f:
            return _normalize(json.load(f))
    except FileNotFoundError:
        return _normalize(_defaults())


def _save(path: Path, data: dict) -> None:
    tmp = path.with_name(f'{path.stem}.{os.getpid()}.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def ensure_roles_file(path: Path) -> None:
    with _lock:
        _save(path, _load(path))


def list_roles(path: Path) -> List[dict]:
    return _load(path)['roles']


def get_role(path: Path, role_id: Optional[str]) -> dict:
    """Kullanıcının rolü; eski/bilinmeyen kimlik Görüntüleyici'ye düşer."""
    rid = resolve_id(path, role_id)
    return next(r for r in list_roles(path) if r['id'] == rid)


def resolve_id(path: Path, role_id: Optional[str]) -> str:
    rid = ESKI_ROLLER.get(role_id or '', role_id or '')
    return rid if any(r['id'] == rid for r in list_roles(path)) else VARSAYILAN_ROL


def exists(path: Path, role_id: str) -> bool:
    return any(r['id'] == role_id for r in list_roles(path))


def _slug(ad: str) -> str:
    tr = str.maketrans('çğıöşüÇĞİÖŞÜ', 'cgiosuCGIOSU')
    s = re.sub(r'[^a-z0-9]+', '_', ad.translate(tr).lower()).strip('_')
    return (s or 'rol')[:28]


def _check_payload(ad: str, izinler, gunluk) -> Tuple[Optional[str], List[str], int]:
    ad = (ad or '').strip()
    if not ad or len(ad) > 40:
        return 'Rol adı 1–40 karakter olmalı', [], 0
    if not isinstance(izinler, list) or any(not _izin_gecerli(k) for k in izinler):
        return 'Geçersiz izin', [], 0
    try:
        g = int(gunluk)
    except (TypeError, ValueError):
        return 'Günlük soru sınırı sayı olmalı', [], 0
    if not GUNLUK_MIN <= g <= GUNLUK_MAX:
        return f'Günlük soru sınırı {GUNLUK_MIN}–{GUNLUK_MAX} arasında olmalı', [], 0
    return None, _izin_sirala(izinler), g


def create_role(path: Path, ad: str, izinler: list, gunluk) -> Tuple[Optional[dict], str]:
    err, izinler, g = _check_payload(ad, izinler, gunluk)
    if err:
        return None, err
    with _lock:
        data = _load(path)
        if any(r['ad'].casefold() == ad.strip().casefold() for r in data['roles']):
            return None, 'Bu adla bir rol zaten var'
        base, rid, n = _slug(ad), _slug(ad), 2
        while any(r['id'] == rid for r in data['roles']):
            rid, n = f'{base}_{n}', n + 1
        role = {'id': rid, 'ad': ad.strip(), 'izinler': izinler, 'asistan_gunluk': g, 'hazir': False}
        data['roles'].append(role)
        _save(path, data)
    return role, ''


def update_role(path: Path, role_id: str, ad: str, izinler: list, gunluk) -> Tuple[Optional[dict], str]:
    err, izinler, g = _check_payload(ad, izinler, gunluk)
    if err:
        return None, err
    with _lock:
        data = _load(path)
        role = next((r for r in data['roles'] if r['id'] == role_id), None)
        if role is None:
            return None, 'Rol bulunamadı'
        if any(r['id'] != role_id and r['ad'].casefold() == ad.strip().casefold() for r in data['roles']):
            return None, 'Bu adla bir rol zaten var'
        role['ad'] = ad.strip()
        role['asistan_gunluk'] = g
        if role_id != ADMIN_ROL:
            role['izinler'] = izinler
        _save(path, data)
    return dict(role), ''


def delete_role(path: Path, role_id: str, in_use: int) -> Tuple[bool, str]:
    with _lock:
        data = _load(path)
        role = next((r for r in data['roles'] if r['id'] == role_id), None)
        if role is None:
            return False, 'Rol bulunamadı'
        if role['hazir']:
            return False, 'Hazır roller silinemez'
        if in_use:
            return False, f'Bu rol {in_use} kullanıcıya atanmış; önce kullanıcılara başka rol verin'
        data['roles'] = [r for r in data['roles'] if r['id'] != role_id]
        _save(path, data)
    return True, ''


def all_permissions() -> List[str]:
    return list(IZIN_ANAHTARLARI)


def catalog() -> List[dict]:
    return [{'id': k, 'ad': ad, 'bolum': b, 'aciklama': a} for k, ad, b, a in IZINLER]
