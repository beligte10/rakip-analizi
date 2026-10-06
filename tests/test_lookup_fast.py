"""LookupContext hızlı erişim yolu (2026-09-29) — düz sözlük, pandas .loc ile
aynı sonucu vermeli; NBSP temizliği kategori etiketlerinde de doğru çalışmalı."""
import pandas as pd

from pipeline.lookup import LookupContext


def _df():
    rows = []
    for banka in ['A Bank', 'B Bank']:
        for i, t in enumerate(pd.date_range('2024-03-31', periods=6, freq='QE')):
            rows.append(('Mevduat', 'Ana Tablo', 'Bilanço', 'Krediler\xa0Ve Alacaklar (Toplam)', 'Toplam',
                         100.0 + i, banka, t))
            rows.append(('Mevduat', 'Ana Tablo', 'Bilanço', 'Mevduat', 'TP', 50.0 + i, banka, t))
            # Aynı kalem NBSP'li ve NBSP'siz iki satır: temizlik sonrası toplanmalı
            rows.append(('Mevduat', 'Ana Tablo', 'Gelir Tablosu', 'Faiz\xa0Gelirleri', 'Toplam', 3.0, banka, t))
            rows.append(('Mevduat', 'Ana Tablo', 'Gelir Tablosu', 'Faiz Gelirleri', 'Toplam', 2.0, banka, t))
    df = pd.DataFrame(rows, columns=['Banka Türü', 'Tablo Türü', 'Tablo Adı', 'Kalem Adı',
                                     'Para Birimi', 'Tutar', 'Banka Adı', 'Tarih'])
    for c in ['Banka Türü', 'Tablo Türü', 'Tablo Adı', 'Kalem Adı', 'Para Birimi', 'Banka Adı']:
        df[c] = df[c].astype('category')
    return df


def _loc(ctx, table, banka, tarih, kalem, pb):
    s = ctx._idx[table]
    try:
        v = s.loc[(banka, pd.Timestamp(tarih), kalem, pb)]
    except KeyError:
        return 0.0
    return float(v.sum()) if isinstance(v, pd.Series) else float(v)


def test_hizli_lookup_pandas_ile_ayni():
    ctx = LookupContext(_df())
    for banka in ['A Bank', 'B Bank', 'Yok Bank']:
        for tarih in ['2024-03-31', '2024-12-31', '2025-06-30', '2030-12-31']:
            for kalem, pb in [('Krediler Ve Alacaklar (Toplam)', 'Toplam'), ('Mevduat', 'TP'),
                              ('Mevduat', 'YP'), ('Olmayan Kalem', 'Toplam')]:
                assert ctx.bilanco(banka, tarih, kalem, pb) == _loc(ctx, 'bilanco', banka, tarih, kalem, pb)
    # Timestamp ile çağrı da aynı sonucu verir
    assert ctx.bilanco('A Bank', pd.Timestamp('2024-06-30'), 'Mevduat', 'TP') == 51.0


def test_nbsp_kategori_etiketinde_temizlenir_ve_ciftler_toplanir():
    ctx = LookupContext(_df())
    assert ctx.bilanco('A Bank', '2024-03-31', 'Krediler Ve Alacaklar (Toplam)') == 100.0
    # 'Faiz\xa0Gelirleri' ve 'Faiz Gelirleri' aynı kaleme düşer: 3 + 2
    assert ctx.gelir('A Bank', '2024-03-31', 'Faiz Gelirleri') == 5.0
    assert not any('\xa0' in str(x) for x in ctx.df['Kalem Adı'].unique())


def test_onceki_ve_gecen_yil_donemi():
    ctx = LookupContext(_df())
    assert ctx.prev_period('A Bank', '2024-03-31') is None
    assert ctx.prev_period('A Bank', '2024-06-30') == pd.Timestamp('2024-03-31')
    assert ctx.yoy_period('A Bank', '2024-12-31') is None
    assert ctx.yoy_period('A Bank', '2025-03-31') == pd.Timestamp('2024-03-31')
    assert ctx.prev_period('Yok Bank', '2024-06-30') is None
    assert ctx.prev_period('A Bank', '2031-03-31') is None


# --- TP/YP Getirili Aktif – Maliyetli Pasif Spread'i (2026-09-30) ---

def test_tp_yp_getirili_maliyetli_spread_formulu(monkeypatch):
    """Spread = getiri − maliyet (basit fark, yüzde puan)."""
    from pipeline import measures as M
    oran = {('getiri', 'TP'): (30.0, 100.0), ('maliyet', 'TP'): (25.0, 100.0),
            ('getiri', 'YP'): (4.0, 100.0), ('maliyet', 'YP'): (3.5, 100.0)}
    monkeypatch.setattr(M, 'getirili_aktif_getirisi_pb_num_den', lambda c, b, t, pb: oran[('getiri', pb)])
    monkeypatch.setattr(M, 'maliyetli_pasif_maliyeti_pb_num_den', lambda c, b, t, pb: oran[('maliyet', pb)])
    assert abs(M.m_tp_getirili_maliyetli_spread(None, 'X', '2026-06-30') - 5.0) < 1e-9
    assert abs(M.m_yp_getirili_maliyetli_spread(None, 'X', '2026-06-30') - 0.5) < 1e-9
