"""Mobil / tablet düzen denetimi (2026-10-03).

Panoyu (frontend/index_v30.html) gerçek veriyle (data/computed.json) yerel, kimlik doğrulamasız küçük bir
sunucuda açar ve başsız Chrome'da her ekran boyutunda tests/duzen/duzen_denetimi.js'i çalıştırır:
Anında Görünüm, menü, Trend, Kompozisyon, PDF / Ölçü Oluştur / Odak / Yenilikler pencereleri, Asistan ve
Dışa Aktar sırayla açılır; sayfa taşması, ekran dışına çıkan öğe, kesik yazı, üst üste binen düğme,
küçük dokunma hedefi ve çok küçük yazı aranır.

    python3 scripts/duzen_denetimi.py               # tüm boyutlar
    python3 scripts/duzen_denetimi.py --boyut 375x812 --dil en

Çıkış kodu: sorun yoksa 0, varsa 1. tests/test_duzen_mobil.py bunu çağırır.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
HTML = KOK / 'frontend' / 'index_v30.html'
DENETIM = KOK / 'tests' / 'duzen' / 'duzen_denetimi.js'
VERI = Path(os.environ.get('DATA_DIR', KOK / 'data')) / 'computed.json'
# telefon, büyük telefon, tablet dikey, tablet yatay
BOYUTLAR = ['375x812', '430x932', '768x1024', '1024x768']
# Denetimin açması gereken ekranlar (biri açılamazsa sonuç geçersiz sayılır)
BEKLENEN_EKRANLAR = ['anlik', 'menu', 'trend', 'kompozisyon', 'pdf_penceresi', 'olcu_olustur', 'odak_penceresi',
                     'yenilikler', 'asistan', 'disa_aktar']
CHROME_ADAYLARI = [
    os.environ.get('CHROME'),
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    shutil.which('google-chrome'), shutil.which('chromium'), shutil.which('chromium-browser'),
]

ME = {'id': 1, 'name': 'Denetim', 'email': 'denetim@local', 'role': 'admin',
      'izinler': ['export_veri', 'export_gorsel', 'olcu_olustur', 'asistan', 'odak_banka', 'sekme_trend', 'sekme_kompozisyon',
                  'kart_siralama', 'kart_ytd', 'kart_gruplar', 'kart_rakipler', 'menu_bdr'],
      'odak_banka': None, 'odak_varsayilan': None, 'odak_secili': None}
SABIT = {
    '/api/me': ME, '/api/my/measures': {'measures': []}, '/api/my/views': {'views': []},
    '/api/chat/status': {'enabled': True}, '/api/odak-katman': {},
    '/api/whats-new': [{'title': 'Denetim', 'items': ['Birinci madde', 'İkinci madde', 'Üçüncü madde']}],
    '/api/measure-info': {},
}
def chrome_yolu():
    return next((c for c in CHROME_ADAYLARI if c and Path(c).exists()), None)


def sunucu(dil, ek_css=''):
    veri = VERI.read_bytes()
    sayfa = HTML.read_text(encoding='utf-8')
    ek = '<script>%s</script>' % DENETIM.read_text(encoding='utf-8')
    if ek_css:   # testte bilerek bozulmuş düzen: denetimin gerçekten yakaladığı doğrulanır
        ek += '<style>%s</style>' % ek_css
    # Dil, sayfanın kendi betiklerinden ÖNCE belirlensin
    sayfa = sayfa.replace('<head>', '<head><script>try{localStorage.setItem("kt_dil","%s")}catch(e){}</script>' % dil, 1)
    sayfa = sayfa.replace('</body>', ek + '</body>', 1).encode('utf-8')

    class Isleyici(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _gonder(self, kod, govde, tur):
            self.send_response(kod)
            self.send_header('Content-Type', tur)
            self.send_header('Content-Length', str(len(govde)))
            self.end_headers()
            self.wfile.write(govde)

        def do_GET(self):
            yol = self.path.split('?')[0]
            if yol in ('/', '/index.html'):
                return self._gonder(200, sayfa, 'text/html; charset=utf-8')
            if yol == '/api/data':
                return self._gonder(200, veri, 'application/json')
            if yol in SABIT:
                return self._gonder(200, json.dumps(SABIT[yol]).encode(), 'application/json')
            return self._gonder(404, b'{}', 'application/json')

        def do_POST(self):
            return self._gonder(200, b'{}', 'application/json')

    srv = ThreadingHTTPServer(('127.0.0.1', 0), Isleyici)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


class _WS:
    """Standart kütüphaneyle en küçük WebSocket istemcisi (Chrome DevTools protokolü için)."""

    def __init__(self, url):
        import base64
        import socket
        from urllib.parse import urlparse
        u = urlparse(url)
        self.s = socket.create_connection((u.hostname, u.port), timeout=60)
        anahtar = base64.b64encode(os.urandom(16)).decode()
        istek = ('GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                 'Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n' % (u.path, u.hostname, u.port, anahtar))
        self.s.sendall(istek.encode())
        yanit = b''
        while b'\r\n\r\n' not in yanit:
            yanit += self.s.recv(4096)
        self.tampon = yanit.split(b'\r\n\r\n', 1)[1]
        self.n = 0

    def _oku(self, k):
        while len(self.tampon) < k:
            parca = self.s.recv(65536)
            if not parca:
                raise ConnectionError('websocket kapandı')
            self.tampon += parca
        v, self.tampon = self.tampon[:k], self.tampon[k:]
        return v

    def gonder(self, metin):
        import struct
        veri = metin.encode()
        maske = os.urandom(4)
        n = len(veri)
        bas = b'\x81' + (bytes([0x80 | n]) if n < 126 else
                          (b'\xfe' + struct.pack('>H', n)) if n < 65536 else (b'\xff' + struct.pack('>Q', n)))
        self.s.sendall(bas + maske + bytes(b ^ maske[i % 4] for i, b in enumerate(veri)))

    def al(self):
        import struct
        govde = b''
        while True:
            b1, b2 = self._oku(2)
            n = b2 & 0x7f
            if n == 126:
                n = struct.unpack('>H', self._oku(2))[0]
            elif n == 127:
                n = struct.unpack('>Q', self._oku(8))[0]
            govde += self._oku(n)
            if b1 & 0x80:
                return govde.decode('utf-8', 'replace')

    def cagir(self, yontem, **param):
        self.n += 1
        self.gonder(json.dumps({'id': self.n, 'method': yontem, 'params': param}))
        while True:
            m = json.loads(self.al())
            if m.get('id') == self.n:
                if 'error' in m:
                    raise RuntimeError(m['error'])
                return m.get('result', {})


def denetle(boyut, dil='tr', chrome=None, zaman_asimi=240, ek_css=''):
    import time
    import urllib.request
    chrome = chrome or chrome_yolu()
    w, h = (int(x) for x in boyut.split('x'))
    srv = sunucu(dil, ek_css)
    with tempfile.TemporaryDirectory() as profil:
        p = subprocess.Popen([chrome, '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
                              '--hide-scrollbars', '--remote-debugging-port=0', '--user-data-dir=' + profil,
                              '--window-size=%d,%d' % (w, h), 'about:blank'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            dosya = Path(profil) / 'DevToolsActivePort'
            for _ in range(100):
                if dosya.exists() and dosya.read_text().strip():
                    break
                time.sleep(0.1)
            port = int(dosya.read_text().split()[0])
            sayfalar = json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json/list' % port).read())
            ws = _WS(next(x for x in sayfalar if x['type'] == 'page')['webSocketDebuggerUrl'])
            ws.cagir('Emulation.setDeviceMetricsOverride', width=w, height=h, deviceScaleFactor=2, mobile=w < 768)
            if w <= 1024:
                ws.cagir('Emulation.setTouchEmulationEnabled', enabled=True, maxTouchPoints=5)
            ws.cagir('Page.navigate', url='http://127.0.0.1:%d/' % srv.server_address[1])
            bitis = time.time() + 60
            while time.time() < bitis:
                r = ws.cagir('Runtime.evaluate', expression="!!document.querySelector('.date-selector-bar .mode-btn')",
                             returnByValue=True)
                if r.get('result', {}).get('value'):
                    break
                time.sleep(0.5)
            else:
                return {'ekran': boyut, 'hata': 'pano yüklenmedi'}
            time.sleep(1)
            r = ws.cagir('Runtime.evaluate', expression='window.__duzenDenetimi()', awaitPromise=True,
                         returnByValue=True, timeout=zaman_asimi * 1000)
            if 'exceptionDetails' in r:
                return {'ekran': boyut, 'hata': str(r['exceptionDetails'])[:300]}
            return r['result']['value']
        finally:
            p.terminate()
            try:
                p.wait(10)
            except subprocess.TimeoutExpired:
                p.kill()
            srv.shutdown()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--boyut', action='append', help='ör. 375x812 (birden çok verilebilir)')
    ap.add_argument('--dil', default='tr', choices=['tr', 'en'])
    a = ap.parse_args(argv)
    if not chrome_yolu():
        print('Chrome bulunamadı (CHROME ortam değişkeniyle yol verilebilir)')
        return 2
    if not VERI.exists():
        print('veri yok:', VERI)
        return 2
    toplam = 0
    for b in a.boyut or BOYUTLAR:
        r = denetle(b, a.dil)
        if r.get('hata'):
            print('✗ %s: %s' % (b, r['hata']))
            toplam += 1
            continue
        s = r.get('sorunlar', [])
        eksik = [d for d in BEKLENEN_EKRANLAR if d not in r.get('gezilen', [])]
        toplam += len(s) + len(eksik)
        print('%s %s (%s): %d sorun, %d ekran denetlendi' % ('✓' if not (s or eksik) else '✗', b, a.dil, len(s),
                                                           len(r.get('gezilen', []))))
        if eksik:
            print('   açılamayan ekranlar:', ', '.join(eksik))
        for x in s:
            print('   [%s] %s — %s %s' % (x['durum'], x['tur'], x['oge'], x['bilgi']))
    return 0 if toplam == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
