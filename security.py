"""
security
========
Güvenlik yardımcıları (2026-10-04 denetimi). app.py'den bağımsız, test edilebilir küçük parçalar:

- RateLimiter: kayan pencereli, iş parçacığı güvenli sayaç (giriş / kayıt / Basic Auth denemeleri).
- client_ip: istemci IP'si (TLS proxy arkasında X-Forwarded-For'un PROXY'NİN eklediği SON değeri).
- origin_ok: durum değiştiren isteklerde Origin başlığı sitenin kendi adresiyle aynı mı (CSRF savunması).
- SECURITY_HEADERS: tüm yanıtlara eklenen güvenlik başlıkları.
- zip_guvenli: ZIP bombası / aşırı büyük giriş denetimi.
- kimlik_bilgisi_coz: KT_USERNAME / KT_PASSWORD yoksa güvensiz varsayılana düşmeden başlangıç kararı.
"""
from __future__ import annotations

import secrets
import threading
import time
import zipfile
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse


class RateLimiter:
    """`limit` başarısız deneme / `pencere` saniye. Anahtar başına tutulur; eski kayıtlar temizlenir."""

    def __init__(self, limit: int, pencere: float, en_cok_anahtar: int = 10000):
        self.limit, self.pencere, self.en_cok = limit, pencere, en_cok_anahtar
        self._d: Dict[str, List[float]] = {}
        self._kilit = threading.Lock()

    def _temizle(self, simdi: float) -> None:
        if len(self._d) <= self.en_cok:
            return
        for k in [k for k, v in self._d.items() if not v or simdi - v[-1] >= self.pencere]:
            self._d.pop(k, None)
        if len(self._d) > self.en_cok:   # hâlâ doluysa en eskileri at (bellek koruması)
            for k in sorted(self._d, key=lambda k: self._d[k][-1] if self._d[k] else 0)[: len(self._d) - self.en_cok]:
                self._d.pop(k, None)

    def izinli(self, anahtar: str) -> bool:
        simdi = time.time()
        with self._kilit:
            arr = [t for t in self._d.get(anahtar, []) if simdi - t < self.pencere]
            self._d[anahtar] = arr
            return len(arr) < self.limit

    def hata(self, anahtar: str) -> None:
        simdi = time.time()
        with self._kilit:
            self._d.setdefault(anahtar, []).append(simdi)
            self._temizle(simdi)

    def sifirla(self, anahtar: str) -> None:
        with self._kilit:
            self._d.pop(anahtar, None)


def client_ip(request, proxy_arkasinda: bool) -> str:
    """İstemci IP'si. Proxy arkasındaysa X-Forwarded-For'un SON girdisi (bizim proxy'nin eklediği);
    ilk girdi istemci tarafından sahtelenebildiği için kullanılmaz."""
    if proxy_arkasinda:
        xff = request.headers.get('x-forwarded-for', '')
        if xff:
            son = xff.split(',')[-1].strip()
            if son:
                return son
    return request.client.host if request.client else 'bilinmiyor'


def origin_ok(request) -> bool:
    """Origin (yoksa Referer) başlığı varsa sitenin kendi adresiyle aynı olmalı. Başlık hiç yoksa
    (curl, sunucu-sunucu, eski tarayıcı) izin verilir: çerezli tarayıcı isteklerinde modern
    tarayıcılar Origin gönderir; asıl savunma SameSite=Lax çerezidir, bu ikinci katmandır."""
    kaynak = request.headers.get('origin') or ''
    if not kaynak or kaynak == 'null':
        ref = request.headers.get('referer') or ''
        if not ref:
            return kaynak != 'null'
        kaynak = ref
    host = urlparse(kaynak).netloc.lower()
    izinli = {request.headers.get('host', '').lower(), request.headers.get('x-forwarded-host', '').split(',')[0].strip().lower()}
    izinli.discard('')
    return host in izinli


SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=()',
    'Cross-Origin-Opener-Policy': 'same-origin',
    # Tam bir script-src CSP sayfadaki satır içi betikleri bozar; clickjacking/base/obje enjeksiyonu kapatılır.
    'Content-Security-Policy': "frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'",
}
HSTS = 'max-age=31536000; includeSubDomains'


def zip_guvenli(zf: zipfile.ZipFile, giris_basina: int, toplam: int, en_cok_oran: int = 200) -> Optional[str]:
    """ZIP'in ZIP-bombası / aşırı büyük olup olmadığını denetler. Sorun varsa Türkçe mesaj, yoksa None."""
    top = 0
    for info in zf.infolist():
        if info.is_dir():
            continue
        if info.file_size > giris_basina:
            return f'ZIP içindeki "{info.filename[:80]}" çok büyük ({info.file_size // (1024 * 1024)} MB)'
        if info.compress_size and info.file_size / info.compress_size > en_cok_oran and info.file_size > 1024 * 1024:
            return f'ZIP içindeki "{info.filename[:80]}" şüpheli sıkıştırma oranı içeriyor'
        top += info.file_size
        if top > toplam:
            return f'ZIP içeriği toplamda çok büyük (> {toplam // (1024 * 1024)} MB)'
    return None


def kimlik_bilgisi_coz(env_kullanici: Optional[str], env_sifre: Optional[str],
                       production: bool) -> Tuple[str, str, bool]:
    """(kullanıcı, şifre, rastgele_mi). Env'de şifre yoksa: production'da başlatma reddedilir; aksi halde
    bu süreç için rastgele bir şifre üretilir (kaynak kodda tahmin edilebilir varsayılan YOK)."""
    kullanici = (env_kullanici or '').strip() or 'admin'
    sifre = env_sifre or ''
    if sifre and sifre not in ('faruk123', 'admin', 'password', '123456', 'changeme'):
        return kullanici, sifre, False
    if production:
        raise RuntimeError('KT_PASSWORD tanımlı değil ya da güvensiz bir varsayılan: production\'da güçlü bir '
                           'KT_PASSWORD gerekli (start.sh / ortam değişkeni).')
    return kullanici, secrets.token_urlsafe(18), True
