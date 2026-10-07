"""Admin panelden asistan API anahtarı yönetimi (assistant/anahtarlar.py, 2026-10-07)."""
import json
import os
import stat

import pytest

from assistant import anahtarlar as A
from assistant import llm


@pytest.fixture
def temiz_ortam(monkeypatch):
    """Her test boş ortamla başlar; açılış değerleri de boş sayılır."""
    for k in A.ADLAR + ['QWEN_API_KEY', 'DASHSCOPE_API_KEY']:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(A, '_ORTAM_ILK', {k: None for k in A.ADLAR})
    yield


def test_kaydet_ortama_uygular_ve_asistani_acar(tmp_path, temiz_ortam):
    yol = tmp_path / '.asistan_anahtarlari.json'
    assert llm.LLMConfig.from_env() is None
    assert A.kaydet(yol, {'OPENROUTER_API_KEY': '  sk-or-v1-abcdef1234567890  '}) is None
    assert os.environ['OPENROUTER_API_KEY'] == 'sk-or-v1-abcdef1234567890'
    assert llm.LLMConfig.from_env() is not None


def test_dosya_gizli_ve_yalniz_bilinen_anahtarlar(tmp_path, temiz_ortam):
    yol = tmp_path / '.asistan_anahtarlari.json'
    A.kaydet(yol, {'EVDS_API_KEY': 'evds-anahtar-123'})
    assert stat.S_IMODE(yol.stat().st_mode) == 0o600
    assert json.loads(yol.read_text()) == {'EVDS_API_KEY': 'evds-anahtar-123'}
    assert 'Bilinmeyen' in A.kaydet(yol, {'PATH': '/tmp/xxxxxxxx'})


def test_durum_duz_degeri_sizdirmaz(tmp_path, temiz_ortam):
    yol = tmp_path / '.asistan_anahtarlari.json'
    deger = 'sk-or-v1-gizlideger9876543210'
    A.kaydet(yol, {'OPENROUTER_API_KEY': deger})
    satirlar = A.durum(yol)
    assert deger not in json.dumps(satirlar)
    s = next(x for x in satirlar if x['anahtar'] == 'OPENROUTER_API_KEY')
    assert s['kaynak'] == 'panel' and s['maske'] == 'sk-or-…3210'
    assert next(x for x in satirlar if x['anahtar'] == 'TUIK_API_KEY')['kaynak'] == 'yok'


def test_silince_sunucu_ortamindaki_deger_geri_gelir(tmp_path, temiz_ortam, monkeypatch):
    yol = tmp_path / '.asistan_anahtarlari.json'
    monkeypatch.setattr(A, '_ORTAM_ILK', {**A._ORTAM_ILK, 'OPENROUTER_API_KEY': 'sk-or-sunucu-0000000'})
    A.kaydet(yol, {'OPENROUTER_API_KEY': 'sk-or-panel-11111111'})
    assert os.environ['OPENROUTER_API_KEY'] == 'sk-or-panel-11111111'   # panel ezer
    A.kaydet(yol, {'OPENROUTER_API_KEY': None})
    assert os.environ['OPENROUTER_API_KEY'] == 'sk-or-sunucu-0000000'   # sunucu değeri geri
    assert next(x for x in A.durum(yol) if x['anahtar'] == 'OPENROUTER_API_KEY')['kaynak'] == 'sunucu'


def test_silince_ortamdan_kalkar(tmp_path, temiz_ortam):
    yol = tmp_path / '.asistan_anahtarlari.json'
    A.kaydet(yol, {'TUIK_API_KEY': 'tuik-anahtar-xyz'})
    A.kaydet(yol, {'TUIK_API_KEY': ''})
    assert 'TUIK_API_KEY' not in os.environ


@pytest.mark.parametrize('deger', ['kisa', 'iki parca anahtar', 'satir\nsonu-anahtar', 'x' * 401])
def test_gecersiz_degerler_reddedilir(tmp_path, temiz_ortam, deger):
    yol = tmp_path / '.asistan_anahtarlari.json'
    assert A.kaydet(yol, {'OPENROUTER_API_KEY': deger})
    assert not yol.exists() and 'OPENROUTER_API_KEY' not in os.environ


def test_uygula_acilista_dosyadan_okur(tmp_path, temiz_ortam):
    yol = tmp_path / '.asistan_anahtarlari.json'
    yol.write_text(json.dumps({'OPENROUTER_API_KEY': 'sk-or-dosyadan-12345', 'BASKA': 'x'}))
    A.uygula(yol)
    assert os.environ['OPENROUTER_API_KEY'] == 'sk-or-dosyadan-12345'
    assert 'BASKA' not in os.environ


def test_bozuk_dosya_cokertmez(tmp_path, temiz_ortam):
    yol = tmp_path / '.asistan_anahtarlari.json'
    yol.write_text('{bozuk')
    A.uygula(yol)
    assert all(x['kaynak'] == 'yok' for x in A.durum(yol))


def test_sunucu_tasima_paketine_girmez():
    import app
    adlar = {ad for ad, _ in app.EXPORT_DATA_FILES}
    assert app.DATA_ASISTAN_ANAHTAR.name not in adlar
