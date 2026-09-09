"""
pipeline.measures.m_gayrinakdi_krediler — saf birim test.

Gerçek veriye bağımlı değil. 2026-09-09'da bu ölçü BASELINE_PASSTHROUGH'dan
çıkarılıp raw'dan hesaplanır hale getirildi (bkz. docs/PROJE_EL_KITABI.md
Dönem 9). Kaynak: 'Bilanço Dışı Yükümlülükler' tablosundaki
'Garanti Ve Kefaletler, Toplam' kalemi.

Üretim verisinde KT 2020-06-30'da bu 'Toplam' satırı bozuktu (-2.15 trilyon,
alt kalemler toplamı ~12.1 milyar). Bu testler o korumayı (negatifse alt
kalemlere düş) senkron ve gerçek veriden bağımsız şekilde kilitler.
"""
from pipeline.measures import m_gayrinakdi_krediler, _GAYRINAKDI_LEAF_KALEMLER


class _FakeCtx:
    """ctx.bd(banka, tarih, kalem) arayüzünü taklit eder — LookupContext._lookup
    ile aynı sözleşme: bulunamayan kalem 0.0 döner, None değil."""

    def __init__(self, values: dict):
        self._values = values

    def bd(self, banka, tarih, kalem, pb='Toplam'):
        return self._values.get((banka, tarih, kalem), 0.0)


def test_pozitif_toplam_dogrudan_kullanilir():
    ctx = _FakeCtx({('KT', '2026-06-30', 'Garanti Ve Kefaletler, Toplam'): 221597000000.0})
    assert m_gayrinakdi_krediler(ctx, 'KT', '2026-06-30') == 221597000000.0


def test_negatif_toplam_alt_kalemler_toplamina_duser():
    """KT 2020-06-30 kazasının birebir senaryosu: Toplam satırı bozuk (-2.15T),
    alt kalemler toplamı doğru (~12.1B)."""
    leaf_values = {
        'Garanti Ve Kefaletler, Teminat Mektupları': 10238500000.0,
        'Garanti Ve Kefaletler, Banka Kredileri': 43724000.0,
        'Garanti Ve Kefaletler, Akreditifler': 1404471000.0,
        'Garanti Ve Kefaletler, Garanti Verilen Prefinansmanlar': 0.0,
        'Garanti Ve Kefaletler, Cirolar': 0.0,
        'Garanti ve Kefaletler, Menkul Kıy. İh. Satın Alma Garantilerimizden': 0.0,
        'Garanti ve Kefaletler, Faktoring Garantilerimizden': 0.0,
        'Garanti Ve Kefaletler, Diğer Garantilerimizden': 434114000.0,
        'Garanti ve Kefaletler, Diğer Kefaletlerimizden': 0.0,
    }
    values = {('KT', '2020-06-30', k): v for k, v in leaf_values.items()}
    values[('KT', '2020-06-30', 'Garanti Ve Kefaletler, Toplam')] = -2146826259000.0
    ctx = _FakeCtx(values)

    result = m_gayrinakdi_krediler(ctx, 'KT', '2020-06-30')

    assert result == sum(leaf_values.values())
    assert result > 0


def test_veri_yoksa_sifir_doner():
    """Banka o dönem hiç raporlamamışsa (ctx.bd → 0.0 her iki taraf için)."""
    ctx = _FakeCtx({})
    assert m_gayrinakdi_krediler(ctx, 'YeniBanka', '2015-03-31') == 0.0


def test_leaf_kalem_listesi_9_eleman():
    """Sabit liste yanlışlıkla değiştirilirse (ör. bir kalem silinirse) burada yakalanır."""
    assert len(_GAYRINAKDI_LEAF_KALEMLER) == 9
    assert len(set(_GAYRINAKDI_LEAF_KALEMLER)) == 9
