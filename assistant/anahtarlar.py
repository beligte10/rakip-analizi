"""
Asistan API anahtarlarının admin panelden yönetimi (2026-10-07).

Neden: anahtarlar normalde sunucu ortam değişkeni (Coolify → Environment
Variables) olarak verilir; panele erişilemediğinde asistan canlıda hiç
açılamıyordu. Admin, anahtarı panelden girer; değer data/ altındaki
gizli dosyaya yazılır ve süreç ortamına (os.environ) anında uygulanır —
LLMConfig.from_env ve dış veri istemcileri anahtarı her çağrıda ortamdan
okuduğu için yeniden başlatma/deploy gerekmez.

Kurallar:
- Panelden girilen değer sunucu ortamındakini EZER; panel değeri silinince
  sunucu ortamındaki (açılıştaki) değer geri gelir.
- Dosya 0600 izinli, data/ git'e ve imaja girmez, sunucu taşıma paketine
  (EXPORT_DATA_FILES) dahil DEĞİLDİR — sır taşınmaz, yeni sunucuda yeniden girilir.
- Değer hiçbir uçta düz metin dönmez; yalnız maskeli hali (sk-or-…a1b2).
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# (ortam değişkeni, panel adı, açıklama)
ANAHTARLAR: List[Tuple[str, str, str]] = [
    ('OPENROUTER_API_KEY', 'OpenRouter API anahtarı',
     'Asistanın çalışması için gerekli (sk-or-… ile başlar).'),
    ('EVDS_API_KEY', 'TCMB EVDS anahtarı',
     'İsteğe bağlı: asistanın TCMB EVDS\'ten makro veri çekmesi için.'),
    ('TUIK_API_KEY', 'TÜİK anahtarı',
     'İsteğe bağlı: asistanın TÜİK verisi çekmesi için.'),
]
ADLAR = [k for k, *_ in ANAHTARLAR]
EN_KISA, EN_UZUN = 8, 400

_LOCK = threading.Lock()
# Açılıştaki (sunucu ortamından gelen) değerler — panel değeri silinince geri yüklenir.
_ORTAM_ILK: Dict[str, Optional[str]] = {k: os.environ.get(k) for k in ADLAR}


def maskele(deger: Optional[str]) -> Optional[str]:
    if not deger:
        return None
    if len(deger) <= 14:
        return '•' * 8
    return deger[:6] + '…' + deger[-4:]


def _oku(path: Path) -> Dict[str, str]:
    try:
        veri = json.loads(Path(path).read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    if not isinstance(veri, dict):
        return {}
    return {k: v for k, v in veri.items() if k in ADLAR and isinstance(v, str) and v}


def _yaz(path: Path, veri: Dict[str, str]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix='.anahtar_', suffix='.tmp')
    try:
        os.chmod(tmp, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _ortama_uygula(veri: Dict[str, str]) -> None:
    for k in ADLAR:
        if veri.get(k):
            os.environ[k] = veri[k]
        elif _ORTAM_ILK.get(k):
            os.environ[k] = _ORTAM_ILK[k]
        else:
            os.environ.pop(k, None)


def uygula(path: Path) -> None:
    """Açılışta: dosyadaki değerleri ortama uygula."""
    with _LOCK:
        _ortama_uygula(_oku(path))


def gecerli_mi(deger: str) -> Optional[str]:
    """Hata mesajı ya da None."""
    if len(deger) < EN_KISA or len(deger) > EN_UZUN:
        return f'Anahtar {EN_KISA}-{EN_UZUN} karakter olmalı'
    if any(c.isspace() or ord(c) < 32 for c in deger):
        return 'Anahtar boşluk ya da satır sonu içeremez'
    return None


def kaydet(path: Path, degisiklik: Dict[str, Optional[str]]) -> Optional[str]:
    """degisiklik: {AD: yeni değer | '' / None (paneldeki değeri sil)}.
    Listede olmayan anahtar dokunulmaz. Hata mesajı ya da None döner."""
    temiz: Dict[str, Optional[str]] = {}
    for k, v in degisiklik.items():
        if k not in ADLAR:
            return f'Bilinmeyen anahtar: {k}'
        if v is None or (isinstance(v, str) and not v.strip()):
            temiz[k] = None
            continue
        if not isinstance(v, str):
            return f'{k}: geçersiz değer'
        v = v.strip()
        hata = gecerli_mi(v)
        if hata:
            return f'{k}: {hata}'
        temiz[k] = v
    with _LOCK:
        veri = _oku(path)
        for k, v in temiz.items():
            if v is None:
                veri.pop(k, None)
            else:
                veri[k] = v
        _yaz(path, veri)
        _ortama_uygula(veri)
    return None


def durum(path: Path) -> List[dict]:
    """Panel tablosu: her anahtarın kaynağı ve maskeli değeri (düz değer asla)."""
    panel = _oku(path)
    sonuc = []
    for k, ad, aciklama in ANAHTARLAR:
        if panel.get(k):
            kaynak, deger = 'panel', panel[k]
        elif _ORTAM_ILK.get(k):
            kaynak, deger = 'sunucu', _ORTAM_ILK[k]
        else:
            kaynak, deger = 'yok', None
        sonuc.append({'anahtar': k, 'ad': ad, 'aciklama': aciklama,
                      'kaynak': kaynak, 'maske': maskele(deger)})
    return sonuc
