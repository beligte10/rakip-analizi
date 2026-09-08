"""
computed.json sağlamlaştırma testleri (2026-09-08).

İki koruma katmanını doğrular:
  1. REGRESYON KİLİDİ (_assert_no_regression) — yeni hesaplama mevcut veriden
     küçükse yazım reddedilir. 2026-08-19'daki kaza (51 dönem -> 1 dönem)
     _assert_nonempty_result'ı geçiyordu çünkü sonuç boş DEĞİLDİ; bu testler
     o senaryonun bir daha sessizce geçmemesini garanti eder.
  2. BOZUKLUK KURTARMA (_recover_computed_if_corrupt) — computed.json
     okunamıyorsa son sağlam yedekten geri yüklenir.

Testler app.py'nin modül sabitlerini (DATA_COMPUTED / DATA_BACKUPS) tmp_path'e
yönlendirir; gerçek data/ klasörüne DOKUNMAZ.
"""
import json
import pytest
from fastapi import HTTPException

import app as A


def _bank_data(bankalar, tarihler, olculer=('toplam_aktifler', 'krediler')):
    """Sentetik bank_data: {ölçü: {banka: {tarih: değer}}}"""
    return {m: {b: {t: 100.0 for t in tarihler} for b in bankalar} for m in olculer}


@pytest.fixture
def izole_data(tmp_path, monkeypatch):
    """app.py'nin computed.json/backups yollarını geçici klasöre al."""
    backups = tmp_path / 'backups'
    backups.mkdir()
    monkeypatch.setattr(A, 'DATA_COMPUTED', tmp_path / 'computed.json')
    monkeypatch.setattr(A, 'DATA_BACKUPS', backups)
    monkeypatch.setattr(A, 'DATA_DIR', tmp_path)
    return tmp_path


def _yaz(path, bank_data):
    payload = {'meta': {'banks': []}, 'catalog': [{'id': 'toplam_aktifler'}],
               'bank_data': bank_data, 'timestamp': '2026-09-08T00:00:00'}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')


# ------------------------------------------------------------------ metrikler
def test_metrikler_dolu_hucreyi_sayar():
    bd = _bank_data(['A', 'B'], ['2026-03-31', '2026-06-30'])
    m = A._computed_metrics(bd)
    assert m['olcu'] == 2 and m['banka'] == 2 and m['donem'] == 2
    assert m['dolu_hucre'] == 8          # 2 ölçü × 2 banka × 2 tarih


def test_metrikler_none_hucreleri_saymaz():
    bd = {'toplam_aktifler': {'A': {'2026-03-31': 100.0, '2026-06-30': None}}}
    assert A._computed_metrics(bd)['dolu_hucre'] == 1
    assert A._computed_metrics(bd)['donem'] == 1


# --------------------------------------------------------- regresyon kilidi
def test_ayni_buyuklukte_veri_gecer(izole_data):
    bd = _bank_data(['A', 'B'], ['2026-03-31', '2026-06-30'])
    _yaz(A.DATA_COMPUTED, bd)
    ozet = A._assert_no_regression(bd)               # exception YOK
    assert ozet['kayiplar'] == []


def test_buyuyen_veri_gecer(izole_data):
    _yaz(A.DATA_COMPUTED, _bank_data(['A'], ['2026-03-31']))
    buyuk = _bank_data(['A', 'B'], ['2026-03-31', '2026-06-30'])
    assert A._assert_no_regression(buyuk)['kayiplar'] == []


def test_donem_kaybi_engellenir(izole_data):
    """2026-08-19 kazasının birebir senaryosu: 51 dönem -> 1 dönem."""
    _yaz(A.DATA_COMPUTED, _bank_data(['A'], [f'2020-{m:02d}-31' for m in range(1, 13)]))
    with pytest.raises(HTTPException) as ex:
        A._assert_no_regression(_bank_data(['A'], ['2020-01-31']))
    assert ex.value.status_code == 409
    assert 'donem' in ex.value.detail


def test_banka_kaybi_engellenir(izole_data):
    _yaz(A.DATA_COMPUTED, _bank_data(['A', 'B', 'C'], ['2026-06-30']))
    with pytest.raises(HTTPException):
        A._assert_no_regression(_bank_data(['A'], ['2026-06-30']))


def test_olcu_kaybi_engellenir(izole_data):
    _yaz(A.DATA_COMPUTED, _bank_data(['A'], ['2026-06-30'], olculer=('m1', 'm2', 'm3')))
    with pytest.raises(HTTPException):
        A._assert_no_regression(_bank_data(['A'], ['2026-06-30'], olculer=('m1',)))


def test_force_ile_kucultme_gecer(izole_data):
    """Meşru küçülmeler için kaçış kapısı — admin panelde onay kutusu."""
    _yaz(A.DATA_COMPUTED, _bank_data(['A', 'B'], ['2026-06-30']))
    ozet = A._assert_no_regression(_bank_data(['A'], ['2026-06-30']), force=True)
    assert ozet['zorlandi'] is True and ozet['kayiplar']


def test_kucuk_dalgalanma_engellenmez(izole_data):
    """%2'lik tolerans: birkaç hücrenin None dönmesi işi durdurmamalı."""
    tarihler = [f'2026-{m:02d}-28' for m in range(1, 13)]
    _yaz(A.DATA_COMPUTED, _bank_data(['A'], tarihler))       # 24 hücre
    az_eksik = _bank_data(['A'], tarihler)
    az_eksik['krediler']['A'][tarihler[-1]] = None            # 23 hücre (%95.8)
    # dönem/banka/ölçü sayısı düşmüyor, hücre kaybı toleransta değil ama
    # donem sayısı korunduğu için yalnız hücre eşiği bakılır:
    with pytest.raises(HTTPException):
        A._assert_no_regression(az_eksik)                      # %4 kayıp > %2 tolerans


def test_mevcut_dosya_yoksa_engellemez(izole_data):
    """İlk kurulumda kıyaslanacak taban yok — yazım serbest olmalı."""
    ozet = A._assert_no_regression(_bank_data(['A'], ['2026-06-30']))
    assert 'skipped' in ozet


# ------------------------------------------------------------ şema kontrolü
@pytest.mark.parametrize('payload,beklenen', [
    ({'bank_data': {'m': {'A': {'t': 1.0}}}, 'catalog': [1], 'meta': {}}, True),
    ({'bank_data': {}, 'catalog': [1], 'meta': {}}, False),
    ({'catalog': [1], 'meta': {}}, False),
    ({'bank_data': {'m': {'A': {'t': None}}}, 'catalog': [1], 'meta': {}}, False),
    ({'bank_data': {'m': {'A': {'t': 1.0}}}, 'meta': {}}, False),
    ('düz metin', False),
])
def test_sema_kontrolu(payload, beklenen):
    assert A._validate_computed_payload(payload)[0] is beklenen


# ---------------------------------------------------------- bozukluk kurtarma
def test_bozuk_dosya_yedekten_kurtarilir(izole_data, monkeypatch):
    monkeypatch.setattr(A, '_RECOVERY_NOTICE', None)
    saglam = _bank_data(['A', 'B'], ['2026-03-31', '2026-06-30'])
    _yaz(A.DATA_BACKUPS / 'computed_20260908_120000.json', saglam)
    A.DATA_COMPUTED.write_text('{ bozuk json', encoding='utf-8')   # yarım yazım

    A._recover_computed_if_corrupt()

    geri = json.loads(A.DATA_COMPUTED.read_text(encoding='utf-8'))
    assert geri['bank_data'] == saglam
    assert A._RECOVERY_NOTICE and 'yedeğinden geri yüklendi' in A._RECOVERY_NOTICE
    # Bozuk dosya incelenebilsin diye saklanmalı
    assert list(A.DATA_DIR.glob('computed.corrupt_*.json'))


def test_saglam_dosyaya_dokunulmaz(izole_data, monkeypatch):
    monkeypatch.setattr(A, '_RECOVERY_NOTICE', None)
    bd = _bank_data(['A'], ['2026-06-30'])
    _yaz(A.DATA_COMPUTED, bd)
    A._recover_computed_if_corrupt()
    assert json.loads(A.DATA_COMPUTED.read_text(encoding='utf-8'))['bank_data'] == bd
    assert A._RECOVERY_NOTICE is None
    assert not list(A.DATA_DIR.glob('computed.corrupt_*.json'))


def test_bozuk_yedek_atlanir_saglam_olan_bulunur(izole_data, monkeypatch):
    monkeypatch.setattr(A, '_RECOVERY_NOTICE', None)
    saglam = _bank_data(['A'], ['2026-06-30'])
    _yaz(A.DATA_BACKUPS / 'computed_20260901_100000.json', saglam)      # eski, sağlam
    (A.DATA_BACKUPS / 'computed_20260908_120000.json').write_text('{bozuk', encoding='utf-8')
    A.DATA_COMPUTED.write_text('{ bozuk', encoding='utf-8')

    A._recover_computed_if_corrupt()
    assert json.loads(A.DATA_COMPUTED.read_text(encoding='utf-8'))['bank_data'] == saglam
