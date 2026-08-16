"""
data/computed.json üzerinde regresyon/spot-check testleri.

Amaç: pipeline (compute_all / build_group_data / measures formülleri)
üzerinde yapılan bir kod değişikliğinin, GEÇMİŞTE zaten doğru hesaplanmış
değerleri sessizce bozmadığını yakalamak. Bu oturumda birkaç kez (2026-08-11)
elle bulunan regresyonların (BASELINE_PASSTHROUGH kaybı, grup agregasyonu,
QNB/KT #VALUE! bozulması) hepsi, böyle bir test seti olsaydı `/admin/rebuild`
öncesi otomatik yakalanabilirdi.

ÖNEMLİ — golden değerler NEDEN 2018-12-31 (yakın bir çeyrek DEĞİL):
Bu tarih, kullanıcının "bundan sonrası sabit kalacak, çeyreklik güncelleme
admin panelden" dediği mevcut arşivde uzun süredir değişmeyen, istikrarlı
bir geçmiş dönem. Yeni çeyrekler eklendikçe bu değerler ETKİLENMEMELİ —
eğer bu testler bir gün kırmızı çıkarsa ve kod DEĞİL, kasıtlı bir veri
düzeltmesi (ör. yeni "gerçek BDR" arşivi) sebebiyse, GOLDEN sözlüğü o zaman
bilinçli olarak güncellenmeli — sessizce değil.
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
COMPUTED_PATH = ROOT / 'data' / 'computed.json'

GOLDEN_DATE = '2018-12-31'
GOLDEN = {
    ('toplam_aktifler', 'Kuveyt Türk'): 74232325000.0,
    ('toplam_aktifler', 'Akbank'): 327642125000.0,
    ('krediler', 'Kuveyt Türk'): 47799034000.0,
    ('krediler', 'Akbank'): 186376300000.0,
    ('mevduat', 'Kuveyt Türk'): 53986278000.0,
    ('mevduat', 'Akbank'): 188391053000.0,
    ('ozkaynaklar', 'Kuveyt Türk'): 5438553000.0,
    ('ozkaynaklar', 'Akbank'): 43809089000.0,
    ('net_donem_kari', 'Kuveyt Türk'): 869812000.0,
    ('net_donem_kari', 'Akbank'): 5689644000.0,
}

# BASELINE_PASSTHROUGH: ham BDDK verisinden hesaplanamayan, önceki
# computed.json'dan devralınması gereken ölçütler. rebuild sırasında bunlar
# base_data olarak verilmezse sessizce kaybolur (bkz. 2026-08-09 bug).
# 2026-08-14: measures.docx tam DAX taraması ile 127→160 (33 yeni ölçü:
# RAV, Toplam Risk, Likidite Açığı×7, vade dilimleri vb.). Bilinçli artış.
EXPECTED_MEASURE_COUNT = 160
EXPECTED_BANK_COUNT = 27


@pytest.fixture(scope='module')
def computed():
    if not COMPUTED_PATH.exists():
        pytest.skip('data/computed.json yok — sistem henüz hiç build edilmemiş')
    with open(COMPUTED_PATH, encoding='utf-8') as f:
        return json.load(f)


def test_measure_count_kayip_yok(computed):
    """160 measure'ın tamamı mevcut mu — BASELINE_PASSTHROUGH kaybı gibi bir
    regresyon olursa bu sayı sessizce düşer (bkz. 2026-08-09 bug)."""
    assert len(computed['bank_data']) == EXPECTED_MEASURE_COUNT


def test_bank_count_kayip_yok(computed):
    ta = computed['bank_data'].get('toplam_aktifler', {})
    assert len(ta) == EXPECTED_BANK_COUNT


@pytest.mark.parametrize('mid,banka', list(GOLDEN.keys()))
def test_golden_deger_sapmadi(computed, mid, banka):
    actual = computed['bank_data'].get(mid, {}).get(banka, {}).get(GOLDEN_DATE)
    expected = GOLDEN[(mid, banka)]
    assert actual == pytest.approx(expected, rel=1e-9), (
        f"{mid}/{banka}/{GOLDEN_DATE}: beklenen {expected}, gelen {actual}. "
        f"Bu bir pipeline/measures.py kod değişikliğinden mi kaynaklandı, "
        f"yoksa kasıtlı bir veri düzeltmesi mi (öyleyse GOLDEN sözlüğünü "
        f"bilinçli güncelle)?"
    )


def test_baseline_passthrough_kaybolmadi(computed):
    """SYR gibi ham veriden hesaplanamayan ölçütler rebuild'ler arası korunmalı."""
    syr = computed['bank_data'].get('syr', {}).get('Kuveyt Türk', {})
    assert syr.get(GOLDEN_DATE) is not None


def test_date_coverage_meta_mevcut(computed):
    """Pazar payı/Bps hesaplamasının kısmi çeyrekleri filtreleyebilmesi için
    gerekli (bkz. 2026-08-11 pazar payı bug'ı). 2018-12-31'de henüz
    kurulmamış 4 banka (Hayat Finans, Dünya Katılım, TOM Bank, Enpara)
    olduğundan kapsam 27 DEĞİL 23 olmalı — bu da normal/beklenen bir durum
    (bkz. _dateReliableForShare: azalma değil, mutlak sayı önemli değil)."""
    assert 'date_coverage' in computed['meta']
    dc = computed['meta']['date_coverage']
    assert dc.get(GOLDEN_DATE) == 23
