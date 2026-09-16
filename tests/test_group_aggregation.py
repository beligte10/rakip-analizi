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

3. (2026-09-17) SADECE ORTALAMA/RASYO agregasyonlarında (_agg_simple_avg,
   _agg_ratio — SUM/_agg_size'da DEĞİL): kurulmuş bir üyenin bu ÖLÇÜDE
   verisi/uygulanabilirliği yoksa (ör. Enpara/TOM Bank gibi dijital
   bankalarda "Gayrinakdi Krediler" hiç sunulmadığı için payda 0'a düşüp
   rasyo None dönüyorsa) o üye HARİÇ TUTULUR, kalan üyelerle ortalama
   hesaplanır — None DÖNMEMELİ. Kullanıcı kararı: "verisi olmayanları
   exclude, veri yüklendikçe include" — bkz. pipeline/groups.py
   _agg_ratio/_agg_simple_avg docstring'leri. _agg_size bundan MUAF: bir
   SUM'da bir üyeyi sessizce dışlamak toplamı gerçekte olduğundan küçük
   gösterir (kural 1'in gerekçesiyle aynı), o yüzden orada hâlâ None döner.
"""
from pipeline.groups import _agg_size, _agg_simple_avg, _agg_ratio, RATIO_NUM_DEN


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


def test_agg_simple_avg_excludes_member_without_this_measure():
    """(2026-09-17 davranış değişikliği) BankB'de bu ölçü hiç yok (ör.
    yapısal olarak uygulanamaz) — eskiden tüm grup None dönerdi, artık
    BankB dışlanıp kalan üyenin (BankA) değeri döner, None DEĞİL."""
    bank_data = {
        'npl_rasyosu': {
            'BankA': {'2026-03-31': 2.0},
            'BankB': {},
        }
    }
    result = _agg_simple_avg(bank_data, 'npl_rasyosu', ['BankA', 'BankB'], '2026-03-31')
    assert result == 2.0


def test_agg_simple_avg_returns_none_when_all_members_missing():
    bank_data = {'npl_rasyosu': {'BankA': {}, 'BankB': {}}}
    result = _agg_simple_avg(bank_data, 'npl_rasyosu', ['BankA', 'BankB'], '2026-03-31')
    assert result is None


def test_agg_ratio_excludes_member_without_applicable_data():
    """(2026-09-17) Gayrinakdi Komisyon/Gayrinakdi Krediler vakası: BankB bu
    ürünü hiç sunmuyor (payda 0 → fn None, None döner) — dışlanır, kalan
    üyenin (BankA) num/den'inden grup oranı hesaplanır."""
    def fake_nd(ctx, b, t):
        vals = {'BankA': (10.0, 100.0), 'BankB': (None, None)}
        return vals[b]
    RATIO_NUM_DEN['__test_ratio__'] = fake_nd
    try:
        result = _agg_ratio(None, '__test_ratio__', ['BankA', 'BankB'], '2026-06-30')
    finally:
        del RATIO_NUM_DEN['__test_ratio__']
    assert result == 10.0  # (10/100) * 100


def test_agg_ratio_returns_none_when_all_members_lack_data():
    def fake_nd(ctx, b, t):
        return (None, None)
    RATIO_NUM_DEN['__test_ratio__'] = fake_nd
    try:
        result = _agg_ratio(None, '__test_ratio__', ['BankA', 'BankB'], '2026-06-30')
    finally:
        del RATIO_NUM_DEN['__test_ratio__']
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
