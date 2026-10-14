"""Görev panosu sütunları (2026-10-14): To Do → In Progress → To Check → Done."""
import json

import app as A


def test_sutunlar_ve_eski_dosya_uyumu(tmp_path, monkeypatch):
    assert A.BOARD_COLUMNS == ['yapilacak', 'planlanan', 'kontrol', 'yapildi']
    yol = tmp_path / 'board.json'
    # 'kontrol' anahtarı olmayan eski dosya boş sütunla yüklenir, kartlar korunur
    yol.write_text(json.dumps({'columns': {'yapilacak': [{'id': 'a', 'baslik': 'x'}], 'planlanan': [], 'yapildi': [{'id': 'b'}]}}), encoding='utf-8')
    monkeypatch.setattr(A, 'DATA_BOARD', yol)
    b = A._load_board()
    assert list(b['columns']) == A.BOARD_COLUMNS
    assert b['columns']['kontrol'] == [] and b['columns']['yapilacak'][0]['id'] == 'a' and b['columns']['yapildi'][0]['id'] == 'b'
    assert A._find_card(b, 'b') == ('yapildi', 0)
