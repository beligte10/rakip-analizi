"""docs/olcu_info_kartlari.md'deki ölçü bilgi kartlarını parse eder.

Format (bkz. docs/olcu_info_kartlari.md başlığı): her kart "---" satırıyla
ayrılır, "## <Ad>" ile başlar, hemen altında `id: <ölçü_id>` bulunur.
Frontend bu id'yle DATA.catalog'daki ölçü id'sini eşleştirip ÖLÇÜ
seçicisinin yanındaki info kartında gösterir.
"""
from __future__ import annotations

import re
import threading
from pathlib import Path

_TERM_RE = re.compile(r'^-\s+\*(.+?):\*\s*(.*)$')
_NOTE_RE = re.compile(r'^>\s*(.*)$')
_TITLE_RE = re.compile(r'^##\s+(.+)$')
_ID_RE = re.compile(r'^`id:\s*([A-Za-z0-9_]+)`$')

_lock = threading.Lock()
_cache: dict = {'mtime': None, 'cards': {}}


def _parse_block(block: str) -> dict | None:
    title = None
    measure_id = None
    fields: dict[str, str] = {}
    terms = []
    notes = []

    for raw_line in block.strip('\n').split('\n'):
        line = raw_line.strip()
        if not line:
            continue

        m = _TITLE_RE.match(line)
        if m:
            title = m.group(1).strip()
            continue

        m = _ID_RE.match(line)
        if m:
            measure_id = m.group(1).strip()
            continue

        m = _TERM_RE.match(line)
        if m:
            terms.append({'term': m.group(1).strip(), 'aciklama': m.group(2).strip()})
            continue

        m = _NOTE_RE.match(line)
        if m:
            text = m.group(1).strip()
            kind = 'warning' if text.startswith('⚠️') else 'info'
            notes.append({'type': kind, 'text': text})
            continue

        # Bir satırda birden fazla alan olabiliyor, ör:
        # "**Kategori:** X · **Tip:** Y · **Birim:** Z" veya
        # "**Hesaplama dönemi:** Pay: ... · Payda: ..." (ikincisinde " · "
        # değerin İÇİNDE — bu yüzden satırı " · "'ya göre değil, "**Label:**"
        # etiketlerinin konumuna göre bölüyoruz).
        labels = list(re.finditer(r'\*\*(.+?):\*\*', line))
        for i, lm in enumerate(labels):
            key = lm.group(1).strip()
            start = lm.end()
            end = labels[i + 1].start() if i + 1 < len(labels) else len(line)
            val = line[start:end].strip().rstrip(' ·').strip()
            if val:
                fields.setdefault(key, val)

    if not measure_id:
        return None

    return {
        'id': measure_id,
        'baslik': title,
        'tanim': fields.get('Tanım'),
        'formul': fields.get('Formül'),
        'donem': fields.get('Hesaplama dönemi'),
        'kaynak': fields.get('Kaynak'),
        'kategori': fields.get('Kategori'),
        'tip': fields.get('Tip'),
        'birim': fields.get('Birim'),
        'durum': fields.get('Durum'),
        'terimler': terms,
        'notlar': notes,
    }


def parse_measure_info_markdown(text: str) -> dict:
    cards = {}
    for block in text.split('\n---\n'):
        card = _parse_block(block)
        if card:
            cards[card['id']] = card
    return cards


def get_measure_info_cards(path: Path) -> dict:
    """docs/olcu_info_kartlari.md'yi parse eder; dosya değişmediyse cache'ten döner."""
    if not path.exists():
        return {}
    mtime = path.stat().st_mtime
    with _lock:
        if _cache['mtime'] == mtime:
            return _cache['cards']
        cards = parse_measure_info_markdown(path.read_text(encoding='utf-8'))
        _cache['mtime'] = mtime
        _cache['cards'] = cards
        return cards
