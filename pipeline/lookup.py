"""
pipeline.lookup
================
Raw veriden (long-format `Veriler` tablosundan) okuma yardımcıları.

Tasarım kararı: Tüm okumalar bir `LookupContext` üzerinden gider:
- Pipeline'ı test ederken küçük bir DataFrame ile mocking yapılabilir
- Indeksleme tek seferde, sonra hızlı dict-lookup
- Banka türü cache'i context içinde
- Zaman serisi yardımcıları (avg balance, TTM flow) buradan
"""
from __future__ import annotations
import pandas as pd
from typing import Dict, List, Optional
from pathlib import Path


class LookupContext:
    """Long-format raw veriye indekslenmiş erişim sağlar."""

    def __init__(self, df: pd.DataFrame, bank_turu_map: Dict[str, str] | None = None):
        # NBSP (\xa0) gibi ince karakter farklarını normalize et — BDDK ham verisinde
        # birçok kalem ve tablo adında NBSP bulunur; tek seferde normal boşluğa çeviriyoruz.
        for col in ['Kalem Adı', 'Tablo Adı', 'Tablo Türü', 'Banka Adı', 'Para Birimi']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('\xa0', ' ', regex=False)

        self.df = df

        if not pd.api.types.is_datetime64_any_dtype(df['Tarih']):
            df['Tarih'] = pd.to_datetime(df['Tarih'])

        self._idx = {}
        for table_key, mask in [
            ('bilanco', (df['Tablo Türü'] == 'Ana Tablo') & (df['Tablo Adı'] == 'Bilanço')),
            ('gelir', (df['Tablo Türü'] == 'Ana Tablo') & (df['Tablo Adı'] == 'Gelir Tablosu')),
            ('mvy', df['Tablo Adı'] == 'Mevduatın Vade Yapısına İlişkin Bilgiler'),
            ('tfv', df['Tablo Adı'] == 'Toplanan Fonların Vade Yapısına İlişkin Bilgiler'),
            ('sube', df['Tablo Adı'] == 'Şube-Personel'),
            ('bd', df['Tablo Adı'] == 'Bilanço Dışı Yükümlülükler'),
            ('tk_detay', df['Tablo Adı'] == 'Tüketici Kredileri, Bireysel Kredi Kartları, Personel Kredileri ve Personel Kredi Kartlarına İlişkin Bilgiler'),
            ('grup12', df['Tablo Adı'] == 'Birinci ve İkinci Grup Krediler, Diğer Alacaklar ile Sözleşme Koşullarında Değişiklik Yapılan Kredilere İlişkin Bilgiler'),
            ('donuk_akim', df['Tablo Adı'] == 'Toplam Donuk Alacaklara İlişkin Bilgiler'),
            ('kur_riski', df['Tablo Adı'] == "Banka'nın Kur Riskine İlişkin Bilgiler"),
            ('kur_riski_konsolide', df['Tablo Adı'] == 'Ana Ortaklık Bankanın Kur Riskine İlişkin Bilgiler'),
            ('faaliyet_gid_detay', df['Tablo Adı'] == 'Diğer Faaliyet Giderlerine İlişkin Bilgiler'),
            ('sermaye', df['Tablo Adı'] == 'Finansal Varlık ve Borçların Gerçeğe Uygun Değerlerine İlişkin Bilgiler'),
            ('tcmb', df['Tablo Adı'] == 'Nakit Değerler ve TCMB’ye İlişkin Bilgiler'),
            ('ozkaynak_detay', df['Tablo Adı'] == 'Özkaynak Kalemlerine İlişkin Bilgiler'),
            ('kalan_vade', df['Tablo Adı'] == 'Aktif ve Pasif Kalemlerin Kalan Vadelerine Göre Gösterimi'),
        ]:
            self._idx[table_key] = self._index(df[mask])

        if bank_turu_map is None:
            bank_turu_map = (
                df.groupby('Banka Adı', observed=True)['Banka Türü']
                .agg(lambda s: s.dropna().iloc[0] if len(s.dropna()) else '')
                .to_dict()
            )
        self.bank_turu = bank_turu_map

        self._dates_by_bank: Dict[str, List[pd.Timestamp]] = (
            df.groupby('Banka Adı', observed=True)['Tarih']
            .apply(lambda s: sorted(s.unique()))
            .to_dict()
        )

    @staticmethod
    def _index(df: pd.DataFrame) -> pd.Series:
        if len(df) == 0:
            return pd.Series(dtype='float64')
        return df.groupby(
            ['Banka Adı', 'Tarih', 'Kalem Adı', 'Para Birimi'],
            observed=True
        )['Tutar'].sum()

    @staticmethod
    def _norm_tarih(tarih) -> pd.Timestamp:
        if isinstance(tarih, pd.Timestamp):
            return tarih
        return pd.Timestamp(tarih)

    def _lookup(self, table_key: str, banka, tarih, kalem, pb) -> float:
        idx = self._idx.get(table_key)
        if idx is None or len(idx) == 0:
            return 0.0
        try:
            v = idx.loc[(banka, self._norm_tarih(tarih), kalem, pb)]
            if isinstance(v, pd.Series):
                return float(v.sum())
            return float(v)
        except KeyError:
            return 0.0

    # Tablo erişimleri
    def bilanco(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('bilanco', banka, tarih, kalem, pb)

    def gelir(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('gelir', banka, tarih, kalem, pb)

    def mvy(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('mvy', banka, tarih, kalem, pb)

    def tfv(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('tfv', banka, tarih, kalem, pb)

    def sube(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('sube', banka, tarih, kalem, pb)

    def bd(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('bd', banka, tarih, kalem, pb)

    def tk_detay(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('tk_detay', banka, tarih, kalem, pb)

    def grup12(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('grup12', banka, tarih, kalem, pb)

    def donuk_akim(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('donuk_akim', banka, tarih, kalem, pb)

    def kur(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('kur_riski', banka, tarih, kalem, pb)

    def kur_konsolide(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('kur_riski_konsolide', banka, tarih, kalem, pb)

    def faaliyet_gid_detay(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('faaliyet_gid_detay', banka, tarih, kalem, pb)

    def sermaye(self, banka, tarih, kalem, pb='Toplam'):
        """Sermaye yeterliliği / SYR tablosu: Çekirdek Sermaye Toplamı, Kredi Riskine
        Esas Tutar (RWA), İlave Ana Sermaye, Katkı Sermaye vb. NOT: BDDK ham verisinde
        bu kalemler 'Finansal Varlık ve Borçların Gerçeğe Uygun Değerlerine İlişkin
        Bilgiler' tablosunda (karışık/yanlış adlandırılmış) tutuluyor."""
        return self._lookup('sermaye', banka, tarih, kalem, pb)

    def tcmb(self, banka, tarih, kalem, pb='Toplam'):
        """'Nakit Değerler ve TCMB'ye İlişkin Bilgiler' tablosu (TCMB Hesabı TP/YP vb.).
        NOT: tablo adında curly apostrof (U+2019) var; from_parquet ham veriyle birebir."""
        return self._lookup('tcmb', banka, tarih, kalem, pb)

    def ozkaynak_detay(self, banka, tarih, kalem, pb='Toplam'):
        """'Özkaynak Kalemlerine İlişkin Bilgiler' tablosu — regülasyon özkaynağı
        (Ana Sermaye + Katkı Sermaye). NOT: 'Toplam Ozkaynaklar' kalemi BDDK ham
        veride düz 'O' ve 'ı'sız yazılı ('Özkaynaklar' DEĞİL) — birebir kopyalanmalı.
        Bilanço 'Özkaynaklar' kaleminden FARKLI (regülasyon toplam özkaynağı)."""
        return self._lookup('ozkaynak_detay', banka, tarih, kalem, pb)

    def kalan_vade(self, banka, tarih, kalem, pb='Toplam'):
        """'Aktif ve Pasif Kalemlerin Kalan Vadelerine Göre Gösterimi' tablosu
        (Likidite Açığı, Nakit Değerler vb. vade dilimleri). NOT: ham veride
        'Likidite' 'Likitide' olarak yazılı — kalem adları birebir kopyalanmalı."""
        return self._lookup('kalan_vade', banka, tarih, kalem, pb)

    # Banka tipi farkındalı yardımcılar
    def vadesiz_mevduat(self, banka, tarih):
        if self.bank_turu.get(banka) == 'Katılım':
            return self.tfv(banka, tarih, 'Toplam Vadesiz')
        return self.mvy(banka, tarih, 'Toplam, Vadesiz')

    def kiymetli_maden(self, banka, tarih):
        # NBSP normalize sonrası: tüm boşluklar normal — eski "DH \xa0Toplam" → "DH  Toplam"
        if self.bank_turu.get(banka) == 'Katılım':
            return self.tfv(banka, tarih, 'Kıymetli Maden DH  Toplam')
        return self.mvy(banka, tarih, 'Kıymetli Maden DH, Toplam')

    def resmi_kurumlar(self, banka, tarih):
        if self.bank_turu.get(banka) == 'Katılım':
            return self.tfv(banka, tarih, 'Resmi Kuruluşlar  Toplam')
        return self.mvy(banka, tarih, 'Resmi Kur. Mevduatı, Toplam')

    def tuzel_mevduat(self, banka, tarih):
        if self.bank_turu.get(banka) == 'Katılım':
            return (
                self.tfv(banka, tarih, 'Ticari Kuruluşlar  Toplam')
                + self.tfv(banka, tarih, 'Diğer Kuruluşlar  Toplam')
                + self.tfv(banka, tarih, 'Resmi Kuruluşlar  Toplam')
            )
        return (
            self.mvy(banka, tarih, 'Tic. Kur. Mevduatı, Toplam')
            + self.mvy(banka, tarih, 'Diğ. Kur. Mevduatı, Toplam')
            + self.mvy(banka, tarih, 'Resmi Kur. Mevduatı, Toplam')
        )

    # Zaman serisi yardımcıları
    def get_dates(self, banka):
        return self._dates_by_bank.get(banka, [])

    def prev_period(self, banka, tarih):
        t = self._norm_tarih(tarih)
        dates = self.get_dates(banka)
        for i, d in enumerate(dates):
            if d == t:
                return dates[i - 1] if i > 0 else None
        return None

    def yoy_period(self, banka, tarih):
        t = self._norm_tarih(tarih)
        dates = self.get_dates(banka)
        for i, d in enumerate(dates):
            if d == t:
                return dates[i - 4] if i >= 4 else None
        return None

    def fy_prev(self, banka, tarih):
        """Bir önceki yılın Q4."""
        t = self._norm_tarih(tarih)
        target_year = t.year - 1
        for d in self.get_dates(banka):
            if d.year == target_year and d.month == 12 and d.day == 31:
                return d
        return None

    @staticmethod
    def months_in_period(tarih) -> int:
        return LookupContext._norm_tarih(tarih).month

    @classmethod
    def from_parquet(cls, path, bank_turu_map=None):
        return cls(pd.read_parquet(path), bank_turu_map)


# Helpers ----------------------------------------------------------

def safe_ratio(num, den, scale=100.0):
    if num is None or den is None or den == 0:
        return None
    return (num / den) * scale


def krediler(ctx, banka, tarih, pb='Toplam'):
    """IFRS9 sonrası 'Krediler Ve Alacaklar (Toplam)', legacy 'Krediler'."""
    v = ctx.bilanco(banka, tarih, 'Krediler Ve Alacaklar (Toplam)', pb)
    if v == 0:
        v = ctx.bilanco(banka, tarih, 'Krediler', pb)
    return v


def faiz_getirili_aktif(ctx, banka, tarih, pb='Toplam'):
    """Faiz Getirili Aktif (IEA): Krediler + Finansal Varlıklar (Net) + Bankalar + PP Alacaklar."""
    return (
        krediler(ctx, banka, tarih, pb)
        + ctx.bilanco(banka, tarih, 'Finansal Varlıklar (Net)', pb)
        + ctx.bilanco(banka, tarih, 'Bankalar', pb)
        + ctx.bilanco(banka, tarih, 'Para Piyasalarından Alacaklar', pb)
    )


def maliyetli_pasif(ctx, banka, tarih, pb='Toplam'):
    """Maliyetli Pasif = Toplam Kaynak + Sermaye Benzeri Krediler."""
    return (
        ctx.bilanco(banka, tarih, 'Mevduat', pb)
        + ctx.bilanco(banka, tarih, 'Alınan Krediler', pb)
        + ctx.bilanco(banka, tarih, 'Para Piyasalarına Borçlar', pb)
        + ctx.bilanco(banka, tarih, 'İhraç Edilen Menkul Kıymetler (Net)', pb)
        + ctx.bilanco(banka, tarih, 'Sermaye Benzeri Krediler', pb)
    )


def ttm_flow(ctx, banka, tarih, kalem_fn):
    """
    TTM (Trailing Twelve Months) akım.
    BDDK gelir tablosu YtD'dir.
    TTM(t) = YtD(t) + (FY_prev - YtD(yoy(t)))
    Q4 ise zaten yıllık.
    """
    curr = kalem_fn(banka, tarih)
    if curr is None:
        return None
    months = ctx.months_in_period(tarih)
    if months == 12:
        return curr
    fy_prev_t = ctx.fy_prev(banka, tarih)
    yoy_t = ctx.yoy_period(banka, tarih)
    if fy_prev_t is not None and yoy_t is not None:
        fy_prev_v = kalem_fn(banka, fy_prev_t)
        yoy_v = kalem_fn(banka, yoy_t)
        if fy_prev_v is not None and yoy_v is not None:
            return curr + (fy_prev_v - yoy_v)
    return curr * 12.0 / months  # fallback


def avg_balance(ctx, banka, tarih, stock_fn):
    """YoY 2-dönem ortalama: (stock(t) + stock(yoy(t))) / 2."""
    curr = stock_fn(banka, tarih)
    if curr is None:
        return None
    yoy_t = ctx.yoy_period(banka, tarih)
    if yoy_t is None:
        return curr
    yoy_v = stock_fn(banka, yoy_t)
    if yoy_v is None:
        return curr
    return (curr + yoy_v) / 2
