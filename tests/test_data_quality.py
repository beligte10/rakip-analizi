"""
pipeline.ingest.check_data_quality — Bloomberg/FactSet eklentisi olmadan
export edilmiş (Tutar hücreleri '#VALUE!'/boş) bozuk xlsx dosyalarının
tespiti (2026-08-11'de eklendi — bkz. memory: admin-upload-toplu-duzeltme.md
madde 5).

Gerçek dosyaya bağımlı değil — sentetik BDDK-formatlı xlsx'ler bellekte
üretilip test edilir.
"""
import io
import openpyxl
import pytest

from pipeline.ingest import check_data_quality, VALUE_ERROR_THRESHOLD


def _make_xlsx(rows, sheet_name='Sheet1'):
    """13 satır dolgu + header (14. satır) + verilen data satırlarından
    BDDK formatına uygun bir xlsx oluşturur, BytesIO döner."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    for _ in range(13):
        ws.append([None] * 7)
    ws.append(['Banka Türü', 'Tablo Türü', 'Tablo Adı', 'Kalem Adı',
               'Para Birimi', 'Item Code', 'Tutar'])
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _toplam_aktifler_row(tutar):
    return ['Katılım', 'Ana Tablo', 'Bilanço', 'Toplam Aktifler', 'Toplam', None, tutar]


def test_saglam_dosya_kabul_edilir():
    rows = [
        _toplam_aktifler_row(1_000_000),
        ['Katılım', 'Ana Tablo', 'Bilanço', 'Krediler', 'Toplam', None, 500_000],
    ]
    ok, err = check_data_quality(_make_xlsx(rows))
    assert ok is True
    assert err == ""


def test_toplam_aktifler_bos_reddedilir():
    """Bloomberg export hatasının en yaygın belirtisi: temel kalem boş string."""
    rows = [
        _toplam_aktifler_row(''),
        ['Katılım', 'Ana Tablo', 'Bilanço', 'Krediler', 'Toplam', None, 500_000],
    ]
    ok, err = check_data_quality(_make_xlsx(rows))
    assert ok is False
    assert 'Toplam Aktifler' in err


def test_toplam_aktifler_hic_yoksa_reddedilir():
    rows = [
        ['Katılım', 'Ana Tablo', 'Bilanço', 'Krediler', 'Toplam', None, 500_000],
    ]
    ok, err = check_data_quality(_make_xlsx(rows))
    assert ok is False


def test_asiri_value_error_reddedilir():
    """Toplam Aktifler sağlam olsa bile, dosyanın geri kalanı #VALUE! doluysa reddedilmeli."""
    rows = [_toplam_aktifler_row(1_000_000)]
    rows += [['Katılım', 'Ana Tablo', 'Gelir Tablosu', f'Kalem {i}', 'Toplam', None, '#VALUE!']
             for i in range(VALUE_ERROR_THRESHOLD + 1)]
    ok, err = check_data_quality(_make_xlsx(rows))
    assert ok is False
    assert '#VALUE!' in err


def test_esik_alti_value_error_kabul_edilir():
    """Eşiğin altında birkaç #VALUE! (ör. gerçekten uygulanamaz bir dipnot kalemi) sorun değil."""
    rows = [_toplam_aktifler_row(1_000_000)]
    rows += [['Katılım', 'Ana Tablo', 'Gelir Tablosu', f'Kalem {i}', 'Toplam', None, '#VALUE!']
             for i in range(5)]
    ok, err = check_data_quality(_make_xlsx(rows))
    assert ok is True


def test_sheet1_yoksa_reddedilir():
    ok, err = check_data_quality(_make_xlsx([_toplam_aktifler_row(1_000_000)], sheet_name='Rapor'))
    assert ok is False
    assert 'Sheet1' in err


def test_gecersiz_dosya_reddedilir():
    ok, err = check_data_quality(io.BytesIO(b'bu bir xlsx degil'))
    assert ok is False
