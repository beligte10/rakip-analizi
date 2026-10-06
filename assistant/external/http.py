"""Dış servisler için küçük, bağımlılıksız JSON istemcisi (urllib) ve TTL önbelleği."""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Optional, Tuple

TIMEOUT = 30.0


class ExternalError(RuntimeError):
    """Kullanıcıya gösterilebilir dış servis hatası (anahtar/URL içermez)."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


def request_json(url: str, *, headers: Optional[dict] = None, data: Optional[dict] = None,
                 timeout: float = TIMEOUT, source: str = 'Servis') -> Any:
    """GET (data yoksa) ya da form POST; JSON döner. Hata mesajında URL ve
    başlık (anahtar) yer almaz."""
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=dict(headers or {}))
    if body is not None:
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raise ExternalError(f'{source} HTTP {e.code} döndürdü', status=e.code) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ExternalError(f'{source} yanıt vermedi (bağlantı ya da zaman aşımı)') from None
    try:
        return json.loads(raw.decode('utf-8'))
    except ValueError:
        raise ExternalError(f'{source} geçerli JSON döndürmedi') from None


class TTLCache:
    """İş parçacığı güvenli, anahtar başına süreli önbellek. Hatalar önbelleğe
    alınmaz (geçici servis sorunu kalıcı hale gelmesin)."""

    def __init__(self, ttl: float):
        self.ttl = ttl
        self._data: Dict[Any, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: Any, loader: Callable[[], Any]) -> Any:
        now = time.monotonic()
        with self._lock:
            hit = self._data.get(key)
            if hit and hit[0] > now:
                return hit[1]
        value = loader()
        with self._lock:
            self._data[key] = (time.monotonic() + self.ttl, value)
        return value

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
