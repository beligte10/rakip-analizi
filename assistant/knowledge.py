"""
assistant.knowledge
====================
Chatbot araçlarının okuduğu veri katmanı: computed.json + catalog.json +
ölçü bilgi kartları (docs/olcu_info_kartlari.md) ve kullanıcının kendi özel
ölçüleri. SADECE okur — hiçbir dosyaya yazmaz.

Tasarım kararları:
- Sayılar her zaman buradan gelir; model sayı üretmez (bkz. service.py
  sistem mesajı). Her değerle birlikte Türkçe biçimlenmiş bir "gosterim"
  döner ki model birim/ölçek hatası yapmasın.
- computed.json ~10 MB — dosya değişmedikçe (mtime) bellekte tutulur, tek
  worker olduğu için süreç başına tek kopya.
- Özel ölçüler (custom_*) pipeline/custom_measure_rules ile, tarayıcıdaki
  injectCustomMeasures'ın aynısı olarak anlık hesaplanır: banka için banka
  serileri, grup için sunucunun grup serileri üzerinden.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pipeline import custom_measure_rules as R
from pipeline.measure_info import get_measure_info_cards

_FOLD = str.maketrans({'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
                       'â': 'a', 'î': 'i', 'û': 'u'})


def fold(s: str) -> str:
    """Türkçe duyarsız karşılaştırma anahtarı: küçük harf + ASCII."""
    s = (s or '').replace('İ', 'i').replace('I', 'ı').lower()
    return ' '.join(s.translate(_FOLD).split())


def _tokens(s: str) -> List[str]:
    out, cur = [], []
    for ch in fold(s):
        if ch.isalnum():
            cur.append(ch)
        elif cur:
            out.append(''.join(cur))
            cur = []
    if cur:
        out.append(''.join(cur))
    return out


# Yaygın kısaltma/eş anlamlılar → katalogda geçen kelimeler (fold edilmiş).
SYNONYMS: Dict[str, List[str]] = {
    'npl': ['donuk', 'alacaklar'],
    'takipteki': ['donuk'],
    'sorunlu': ['donuk'],
    'roa': ['roaa', 'aktif', 'karliligi'],
    'roe': ['roae', 'ozkaynak', 'karliligi'],
    'kar': ['kari', 'karliligi'],
    'kredi': ['krediler', 'kredileri'],
    'mevduat': ['mevduati'],
    'aktif': ['aktifler'],
    'buyukluk': ['aktifler'],
    'kkm': ['kur', 'korumali'],
    'maliyet': ['maliyeti'],
    'sube': ['sube', 'sayisi'],
    'calisan': ['personel'],
    'personel': ['personel'],
    'sermaye': ['sermaye', 'yeterlilik'],
    'syr': ['sermaye', 'yeterlilik'],
    'marj': ['marji', 'spread'],
    'faiz': ['faiz', 'kar', 'payi'],
}

GROUP_ALIASES = {
    'kt': 'Kuveyt Türk', 'kuveyt': 'Kuveyt Türk',
    'katilim': 'Katılım Bankaları', 'katilim bankalari': 'Katılım Bankaları',
    'mevduat bankalari': 'Mevduat Bankaları', 'mevduat': 'Mevduat Bankaları',
    'rakip': 'Rakip Bankalar', 'rakipler': 'Rakip Bankalar', 'rakip bankalar': 'Rakip Bankalar',
    'kt haric katilim': 'KT Hariç Katılım Bankaları',
    'kt haric katilim bankalari': 'KT Hariç Katılım Bankaları',
}


# ------------------------------------------------------------------
# Sayı biçimleme (Türkçe)
# ------------------------------------------------------------------

def _tr_num(v: float, nd: int) -> str:
    s = f'{v:,.{nd}f}'
    return s.replace(',', '§').replace('.', ',').replace('§', '.')


def format_value(v: Optional[float], meta: dict) -> Optional[str]:
    if v is None:
        return None
    birim = meta.get('birim')
    if birim == 'TL':
        a = abs(v)
        if a >= 1e12:
            return _tr_num(v / 1e12, 2) + ' trilyon TL'
        if a >= 1e9:
            return _tr_num(v / 1e9, 2) + ' milyar TL'
        if a >= 1e6:
            return _tr_num(v / 1e6, 1) + ' milyon TL'
        return _tr_num(v, 0) + ' TL'
    if birim == '%':
        return '%' + _tr_num(v, 2)
    if birim == 'kat':
        return _tr_num(v, 2) + ' kat'
    if birim == 'bin_TL':
        return _tr_num(v, 1) + ' bin TL'
    if birim == 'adet':
        return _tr_num(v, 0 if meta.get('tip') == 'buyukluk' else 1)
    return _tr_num(v, 2)


def change_info(v0: Optional[float], v1: Optional[float], meta: dict) -> Optional[dict]:
    """İki dönem arası değişim — rasyoda baz puan/fark, tutarda yüzde."""
    if v0 is None or v1 is None:
        return None
    if meta.get('tip') == 'rasyo':
        if meta.get('birim') == '%':
            bps = (v1 - v0) * 100
            return {'bps': round(bps, 1), 'gosterim': f'{_tr_num(bps, 0)} bps'}
        fark = v1 - v0
        return {'fark': fark, 'gosterim': format_value(fark, meta)}
    if v0 == 0:
        return None
    pct = (v1 / v0 - 1) * 100
    return {'yuzde': round(pct, 2), 'gosterim': '%' + _tr_num(pct, 1)}


# ------------------------------------------------------------------
# Veri deposu
# ------------------------------------------------------------------

class Store:
    """computed.json + catalog.json + bilgi kartları; mtime ile önbellekli."""

    def __init__(self, computed_path: Path, catalog_path: Path, info_md_path: Path):
        self.computed_path = computed_path
        self.catalog_path = catalog_path
        self.info_md_path = info_md_path
        self._lock = threading.Lock()
        self._key = None
        self.computed: dict = {}
        self.catalog: dict = {}

    def refresh(self) -> 'Store':
        key = tuple(p.stat().st_mtime if p.exists() else None
                    for p in (self.computed_path, self.catalog_path))
        with self._lock:
            if key != self._key:
                self.computed = json.loads(self.computed_path.read_text(encoding='utf-8'))
                self.catalog = json.loads(self.catalog_path.read_text(encoding='utf-8'))
                self._key = key
        return self

    # --- temel görünümler ---
    @property
    def measures(self) -> List[dict]:
        return self.catalog.get('measures', [])

    @property
    def by_id(self) -> Dict[str, dict]:
        return {m['id']: m for m in self.measures}

    @property
    def banks(self) -> List[dict]:
        return self.catalog.get('banks', [])

    @property
    def group_members(self) -> Dict[str, List[str]]:
        return (self.catalog.get('groups') or {}).get('members', {}) or {}

    @property
    def dates(self) -> List[str]:
        return self.computed.get('meta', {}).get('dates', [])

    @property
    def default_date(self) -> str:
        meta = self.computed.get('meta', {})
        return meta.get('default_date') or (self.dates[-1] if self.dates else '')

    def info_cards(self) -> Dict[str, dict]:
        try:
            return get_measure_info_cards(self.info_md_path)
        except OSError:
            return {}


class View:
    """Bir kullanıcının gördüğü veri: katalog + o kullanıcının özel ölçüleri."""

    def __init__(self, store: Store, custom_records: Optional[List[dict]] = None,
                 katman: Optional[dict] = None, gizli_olculer=None):
        self.s = store
        # Rolünde olmayan ölçüler (ör. Rekabet Analizi) asistana da görünmez: arama, değer, sıralama, paket.
        self.gizli = frozenset(gizli_olculer or ())
        # Kullanıcının odak katmanı (2026-10-03): kişisel odak banka / rakip listesi seçildiyse panodaki
        # gibi değişen grupların üyelikleri ve değerleri bu yamadan okunur (bkz. pipeline.focus.focus_overlay).
        self.katman = katman or {}
        self.cat = {k: v for k, v in store.by_id.items() if k not in self.gizli}
        self.custom: Dict[str, dict] = {}     # id → {meta, plan}
        for rec in custom_records or []:
            expr = R.record_expr(rec)
            plan, err = R.analyze(expr, self.cat) if expr else (None, 'geçersiz')
            if err:
                continue
            t = plan['type']
            self.custom[rec['id']] = {
                'meta': {'id': rec['id'], 'ad': rec['ad'], 'tip': t['tip'], 'birim': t['birim'],
                         'akim_stok': t['akim_stok'], 'kategori': 'Özel Ölçülerim',
                         'sort_direction': rec.get('sort_direction', 'desc'), 'custom': True,
                         'formul': R.formula_text(plan, self.cat)},
                'plan': plan,
            }

    @property
    def group_members(self) -> Dict[str, List[str]]:
        return (self.katman.get('meta') or {}).get('groups') or self.s.group_members

    @property
    def group_order(self) -> List[str]:
        return ((self.katman.get('meta') or {}).get('group_order')
                or self.s.computed.get('meta', {}).get('group_order', []))

    # --- ölçüler ---
    def meta(self, mid: str) -> Optional[dict]:
        if mid in self.custom:
            return self.custom[mid]['meta']
        return self.cat.get(mid)

    def resolve_measure(self, ref: str) -> Optional[str]:
        """id ya da tam ad (Türkçe duyarsız) → id."""
        if not ref:
            return None
        if self.meta(ref):
            return ref
        key = fold(ref)
        for mid, m in list(self.cat.items()) + [(k, v['meta']) for k, v in self.custom.items()]:
            if fold(m['ad']) == key or fold(mid) == key:
                return mid
        return None

    def search(self, query: str, limit: int = 10) -> List[dict]:
        q = _tokens(query)
        expanded = set(q)
        for t in q:
            expanded.update(SYNONYMS.get(t, []))
        qfold = fold(query)
        cards = self.s.info_cards()
        scored = []
        pool = [(m, False) for m in self.cat.values()] + [(v['meta'], True) for v in self.custom.values()]
        for m, is_custom in pool:
            ad_t = set(_tokens(m['ad']))
            ctx_t = set(_tokens(' '.join(filter(None, [m.get('kategori'), m.get('alt_kategori'),
                                                        (cards.get(m['id']) or {}).get('tanim')]))))
            score = 0.0
            if qfold and qfold == fold(m['ad']):
                score += 10
            elif qfold and qfold in fold(m['ad']):
                score += 4
            for t in expanded:
                w = 1.0 if t in q else 0.6
                if t in ad_t:
                    score += 3 * w
                elif any(a.startswith(t) or t.startswith(a) for a in ad_t if len(a) >= 3 and len(t) >= 3):
                    score += 2 * w
                elif t in ctx_t:
                    score += 0.7 * w
                if t == fold(m['id']):
                    score += 5
            if score > 0:
                scored.append((score, m, is_custom))
        scored.sort(key=lambda x: (-x[0], len(x[1]['ad'])))
        out = []
        for score, m, is_custom in scored[:limit]:
            card = cards.get(m['id']) or {}
            out.append({
                'id': m['id'], 'ad': m['ad'], 'tip': m.get('tip'), 'birim': m.get('birim'),
                'akim_stok': m.get('akim_stok'), 'kategori': m.get('kategori'),
                'alt_kategori': m.get('alt_kategori'),
                'tanim': (card.get('tanim') or m.get('formul') or '')[:220],
                'ozel': is_custom,
            })
        return out

    def info(self, mid: str) -> Optional[dict]:
        m = self.meta(mid)
        if not m:
            return None
        if mid in self.custom:
            return {**m, 'tanim': 'Kullanıcının kendi tanımladığı özel ölçü.'}
        card = self.s.info_cards().get(mid) or {}
        return {
            'id': mid, 'ad': m['ad'], 'tip': m.get('tip'), 'birim': m.get('birim'),
            'akim_stok': m.get('akim_stok'), 'kategori': m.get('kategori'),
            'alt_kategori': m.get('alt_kategori'), 'pazar_payi': m.get('pazar_payi'),
            'tanim': card.get('tanim'), 'formul': card.get('formul'), 'donem': card.get('donem'),
            'kaynak': card.get('kaynak'),
            'notlar': [n.get('text') for n in card.get('notlar') or []],
            'terimler': card.get('terimler') or [],
        }

    # --- varlıklar (banka / grup) ---
    def resolve_entity(self, name: str) -> Optional[Tuple[str, str]]:
        """Ad → ('banka'|'grup', kanonik ad). Bir ad hem banka hem tek üyeli
        grup olabilir ("Kuveyt Türk") — banka verisi asıl kaynak olduğundan
        önce banka eşleşir."""
        key = fold(name)
        banks = [b['banka_adi'] for b in self.s.banks]
        groups = list(self.group_members)
        target = GROUP_ALIASES.get(key)
        for b in banks:
            if fold(b) == key or b == target:
                return ('banka', b)
        for g in groups:
            if fold(g) == key or g == target:
                return ('grup', g)
        for b in banks:                 # kısmi: "garanti", "is bankasi"
            if key and (key in fold(b) or fold(b).startswith(key)):
                return ('banka', b)
        return None

    # --- seriler ---
    def _raw_series(self, mid: str, kind: str, name: str) -> Dict[str, Optional[float]]:
        c = self.s.computed
        if kind == 'banka':
            return (c.get('bank_data', {}).get(mid) or {}).get(name) or {}
        g = ((self.katman.get('group_data') or {}).get(mid) or {}).get(name) \
            or (c.get('group_data', {}).get(mid) or {}).get(name) or {}
        return {d: (v or {}).get('value') for d, v in g.items()}

    def value(self, mid: str, kind: str, name: str, date: str) -> Optional[float]:
        if mid in self.custom:
            plan = self.custom[mid]['plan']
            return R.evaluate(plan, lambda i: self._raw_series(i, kind, name), date)
        return self._raw_series(mid, kind, name).get(date)

    # --- tarih ---
    def resolve_date(self, ref: Optional[str]) -> Optional[str]:
        dates = self.s.dates
        if not ref or fold(ref) in ('son', 'guncel', 'latest', 'last'):
            return self.s.default_date
        ref = ref.strip()
        if ref in dates:
            return ref
        up = ref.upper().replace(' ', '')
        for sep in ('Q', 'C', '-Q', '-C'):     # 2026Q2 / 2026-Q2 / 2026C2
            if sep in up:
                y, _, q = up.partition(sep)
                y = y.rstrip('-')
                ay = {'1': '03-31', '2': '06-30', '3': '09-30', '4': '12-31'}.get(q)
                if ay and f'{y}-{ay}' in dates:
                    return f'{y}-{ay}'
        if len(ref) == 7:                       # 2026-06
            for d in dates:
                if d.startswith(ref):
                    return d
        if len(ref) == 4 and ref.isdigit():     # 2025 → yıl sonu (yoksa yılın son dönemi)
            yil = [d for d in dates if d.startswith(ref)]
            return yil[-1] if yil else None
        return None

    def bank_filter(self, filtre: Optional[str]) -> Tuple[Optional[List[str]], str]:
        """Sıralama evreni. (banka_listesi, açıklama) — None = bilinmeyen filtre."""
        f = fold(filtre or 'tumu')
        allb = [b['banka_adi'] for b in self.s.banks]
        if f in ('tumu', 'hepsi', 'sektor', 'tum bankalar', 'all'):
            return allb, 'Tüm bankalar'
        if f in ('katilim', 'katilim bankalari'):
            return [b['banka_adi'] for b in self.s.banks if b.get('tur') == 'Katılım'], 'Katılım bankaları'
        if f in ('mevduat', 'mevduat bankalari'):
            return [b['banka_adi'] for b in self.s.banks if b.get('tur') == 'Mevduat'], 'Mevduat bankaları'
        r = self.resolve_entity(filtre or '')
        if r and r[0] == 'grup':
            return list(self.group_members.get(r[1], [])), r[1]
        return None, ''
