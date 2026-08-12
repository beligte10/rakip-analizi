"""
pipeline.groups — grup agregasyonu (Kuveyt Türk, Mevduat Bankaları, Rakip
Bankalar, Katılım Bankaları vb.) kısmi kapsama koruması.

Gerçek veriye bağımlı değil — saf birim test.

İKİ AYRI kural, birbirine KARIŞTIRILMAMALI:

1. (2026-08-11) Bir çeyrek admin panelden banka banka yüklenirken, grubun
   KURULMUŞ bir üyesi henüz o çeyreği raporlamamışsa (`first_date_map`'te
   ilk tarihi tarih'ten önce/eşit ama o tarihte değeri yok) grup değeri
   None olmalı — kısmi toplam ASLA döndürülmemeli (bkz. memory:
   kismi-ceyrek-grup-agregasyonu-bug.md).

2. (2026-08-12) Bir üye HENÜZ KURULMAMIŞSA (first_date_map'teki ilk
   tarihi sorgulanan tarihten SONRA — ör. Enpara 2024-12-31 öncesi hiç
   yoktu), bu üye MEŞRU şekilde gruptan hariç tutulur, kalan üyelerin
   toplamı hesaplanır — None DÖNMEMELİ. Bu ayrım olmadan "Mevduat
   Bankaları"/"Katılım Bankaları" gibi çok üyeli gruplar, en yeni kurulan
   üyenin ilk raporlama tarihinden ÖNCEKİ HİÇBİR dönemde değer
   göstermiyordu (bkz. memory: kismi-ceyrek-grup-agregasyonu-bug.md,
   kullanıcı raporu: "Mevduat Bankaları... büyüme oranları neden
   yazmıyor").
"""
from pipeline.groups import _agg_size, _agg_simple_avg


def test_agg_size_full_coverage_sums():
    bank_data = {
        'toplam_aktifler': {
            'BankA': {'2026-03-31': 100.0},
            'BankB': {'2026-03-31': 200.0},
            'BankC': {'2026-03-31': 50.0},
        }
    }
    result = _agg_size(bank_data, 'toplam_aktifler', ['BankA', 'BankB', 'BankC'], '2026-03-31')
    assert result == 350.0


def test_agg_size_returns_none_on_partial_coverage():
    """Bir üye o tarihte hiç veri sağlamamış (henüz yüklenmemiş) — None dönmeli, 250 DEĞİL."""
    bank_data = {
        'toplam_aktifler': {
            'BankA': {'2026-03-31': 100.0},
            'BankB': {'2026-03-31': 200.0},
            'BankC': {},  # bu tarihte veri yok
        }
    }
    result = _agg_size(bank_data, 'toplam_aktifler', ['BankA', 'BankB', 'BankC'], '2026-03-31')
    assert result is None


def test_agg_size_returns_none_when_member_value_is_none():
    """Üye anahtarı var ama değeri None (ör. ölçüt o bankada hiç hesaplanamamış)."""
    bank_data = {
        'toplam_aktifler': {
            'BankA': {'2026-03-31': 100.0},
            'BankB': {'2026-03-31': None},
        }
    }
    result = _agg_size(bank_data, 'toplam_aktifler', ['BankA', 'BankB'], '2026-03-31')
    assert result is None


def test_agg_size_empty_members_returns_none():
    result = _agg_size({'toplam_aktifler': {}}, 'toplam_aktifler', [], '2026-03-31')
    assert result is None


def test_agg_simple_avg_full_coverage():
    bank_data = {
        'npl_rasyosu': {
            'BankA': {'2026-03-31': 2.0},
            'BankB': {'2026-03-31': 4.0},
        }
    }
    result = _agg_simple_avg(bank_data, 'npl_rasyosu', ['BankA', 'BankB'], '2026-03-31')
    assert result == 3.0


def test_agg_simple_avg_returns_none_on_partial_coverage():
    bank_data = {
        'npl_rasyosu': {
            'BankA': {'2026-03-31': 2.0},
            'BankB': {},
        }
    }
    result = _agg_simple_avg(bank_data, 'npl_rasyosu', ['BankA', 'BankB'], '2026-03-31')
    assert result is None


def test_agg_size_henuz_kurulmamis_uye_haric_tutulur():
    """BankC 2025-03-31'de henüz kurulmamış (ilk tarihi 2025-12-31) — bu
    üye hariç tutulup kalan üyelerin toplamı (300.0) dönmeli, None DEĞİL."""
    bank_data = {
        'toplam_aktifler': {
            'BankA': {'2025-03-31': 100.0},
            'BankB': {'2025-03-31': 200.0},
            'BankC': {'2025-12-31': 50.0},  # henüz kurulmamış: ilk tarihi 2025-12-31
        }
    }
    first_date_map = {'BankA': '2025-03-31', 'BankB': '2025-03-31', 'BankC': '2025-12-31'}
    result = _agg_size(bank_data, 'toplam_aktifler',
                        ['BankA', 'BankB', 'BankC'], '2025-03-31', first_date_map)
    assert result == 300.0

    # BankC ARTIK kurulmuş olduğu (2025-12-31) tarihte, hepsi mevcutsa
    # normal şekilde toplama dahil edilmeli.
    bank_data['toplam_aktifler']['BankA']['2025-12-31'] = 110.0
    bank_data['toplam_aktifler']['BankB']['2025-12-31'] = 210.0
    result_full = _agg_size(bank_data, 'toplam_aktifler',
                             ['BankA', 'BankB', 'BankC'], '2025-12-31', first_date_map)
    assert result_full == 370.0


def test_agg_size_kurulmus_uye_veri_eksikse_none_doner():
    """BankC 2025-03-31'de zaten kurulmuş (first_date <= tarih) ama o
    tarihte veri sağlamamış — bu GERÇEK eksiklik, None dönmeli."""
    bank_data = {
        'toplam_aktifler': {
            'BankA': {'2025-03-31': 100.0},
            'BankB': {'2025-03-31': 200.0},
            'BankC': {},  # kurulmuş (first_date verilecek) ama bu tarihte veri yok
        }
    }
    first_date_map = {'BankA': '2025-03-31', 'BankB': '2025-03-31', 'BankC': '2024-12-31'}
    result = _agg_size(bank_data, 'toplam_aktifler',
                        ['BankA', 'BankB', 'BankC'], '2025-03-31', first_date_map)
    assert result is None


def test_agg_size_first_date_map_none_eski_davranis():
    """first_date_map verilmezse (eski çağrı yolu), TÜM üyeler aktif sayılır —
    geriye dönük uyumluluk."""
    bank_data = {
        'toplam_aktifler': {
            'BankA': {'2026-03-31': 100.0},
            'BankB': {},
        }
    }
    result = _agg_size(bank_data, 'toplam_aktifler', ['BankA', 'BankB'], '2026-03-31')
    assert result is None
