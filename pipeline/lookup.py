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
import re
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from pathlib import Path


def kalem_norm(kalem: str) -> str:
    """Kalem adı karşılaştırma biçimi: ardışık boşluklar teke iner, baş/son boşluk atılır.
    BDDK şablonunda aynı kalem dönemden döneme farklı boşlukla yazılabiliyor (2013-2017
    dosyalarında 'Bağlı Ortaklıklar (Net) ', 'İştirakler (Net)  ', 'Maddi Duran Varlıklar
    (Net) '; grup kredileri dipnotunda 'İşletme Kredileri, Standart…' / 'Kredi Kartları,
    Standart…' gibi tek/çift boşluk). Birebir aramada bu kalemler 0 dönüyordu (2026-10-03)."""
    return re.sub(r'\s+', ' ', str(kalem)).strip()


def _kategori_normalle(df: pd.DataFrame, col: str, fn) -> None:
    """Kategorik sütunun etiketlerini fn ile dönüştürür; aynı etikete inen kategoriler
    birleşir (kodlar yeniden eşlenir — 2,85 M satırı str'ye çevirmeden)."""
    c = df[col]
    if not isinstance(c.dtype, pd.CategoricalDtype):
        df[col] = c.astype(str).map(fn)
        return
    yeni = [fn(x) for x in c.cat.categories]
    tekil = list(dict.fromkeys(yeni))
    if len(tekil) == len(yeni):
        df[col] = c.cat.rename_categories(yeni)
        return
    konum = {k: i for i, k in enumerate(tekil)}
    eslem = np.array([konum[k] for k in yeni], dtype=np.int64)
    kod = c.cat.codes.to_numpy()
    df[col] = pd.Categorical.from_codes(np.where(kod >= 0, eslem[np.clip(kod, 0, None)], -1), categories=tekil)


# Eski (TFRS 9 öncesi, 2013-12 … 2017-12) BDDK şablonu → yeni şablon karşılıkları
# (2026-10-03). Yeni kalem o banka-dönemde hiç yoksa eski kalemlerden kurulur.
TFRS9_BASLANGIC = pd.Timestamp('2018-01-01')
ESKI_ORTAKLIK_KALEMLERI = ('İştirakler (Net)', 'Bağlı Ortaklıklar (Net)',
                           'Birlikte Kontrol Edi. Ortaklık.(İş Ort.)( Net)')
BZK_ASAMA_KALEMLERI = ('Aylık Beklenen Zarar Karşılığı (Birinci Aşama)',
                       'Kredi Riskinde Önemli Artış (İkinci Aşama)',
                       'Temerrüt (Üçüncü Aşama/Özel Karşılık)')
GRUP1_TOPLAM_EKI = ', Standart Nitelikli Krediler, Toplam'
ESKI_GRUP1_ALT_KALEMLER = ('Krediler ve Diğer Alacaklar',
                           'Ödeme Planının Uzatılmasına Yönelik Değişiklik Yapılanlar', 'Diğer')


def _veri_duzeltmeleri_uygula(df: pd.DataFrame) -> None:
    """pipeline/veri_duzeltmeleri.py kayıtlarını yerinde uygular (yalnız ham değer
    beklenenle uyuşuyorsa)."""
    from .veri_duzeltmeleri import DUZELTMELER
    for d in DUZELTMELER:
        m = ((df['Banka Adı'] == d['banka']) & (df['Tarih'] == pd.Timestamp(d['tarih']))
             & (df['Tablo Adı'] == d['tablo']) & (df['Kalem Adı'] == d['kalem'])
             & (df['Para Birimi'] == d['para_birimi']))
        if int(m.sum()) != 1:
            continue
        i = df.index[m][0]
        if abs(float(df.at[i, 'Tutar']) - d['beklenen']) <= 1e-6 * abs(d['beklenen']):
            df.at[i, 'Tutar'] = d['deger']


class LookupContext:
    """Long-format raw veriye indekslenmiş erişim sağlar."""

    def __init__(self, df: pd.DataFrame, bank_turu_map: Dict[str, str] | None = None):
        # NBSP (\xa0) gibi ince karakter farklarını normalize et — BDDK ham verisinde
        # birçok kalem ve tablo adında NBSP bulunur; tek seferde normal boşluğa çeviriyoruz.
        for col in ['Kalem Adı', 'Tablo Adı', 'Tablo Türü', 'Banka Adı', 'Para Birimi']:
            if col not in df.columns:
                continue
            if isinstance(df[col].dtype, pd.CategoricalDtype):
                # Etiket düzeyinde temizle (2026-09-29): 2,85M satırı str'ye çevirmek
                # tabloyu 66 MB'tan 1,56 GB'a şişiriyor, süreç tepesi ~4,7 GB oluyordu.
                c = df[col].astype(pd.CategoricalDtype([str(x) for x in df[col].cat.categories]))
                yeni = [x.replace('\xa0', ' ') for x in c.cat.categories]
                if len(set(yeni)) == len(yeni):
                    df[col] = c.cat.rename_categories(yeni)
                else:
                    df[col] = c.astype(str).str.replace('\xa0', ' ', regex=False).astype('category')
            else:
                df[col] = df[col].astype(str).str.replace('\xa0', ' ', regex=False)

        # Kanonik banka adları (2026-10-02, pipeline/banka_adlari.py): eski parquet'lerde
        # 'QNB Finansbank' gibi eski adlar kalmışsa platform adına çevrilir.
        from .banka_adlari import BANKA_AD_ESLEME
        if 'Banka Adı' in df.columns and BANKA_AD_ESLEME:
            col = df['Banka Adı']
            if isinstance(col.dtype, pd.CategoricalDtype):
                eski = [c for c in col.cat.categories if c in BANKA_AD_ESLEME]
                if eski:
                    if any(BANKA_AD_ESLEME[c] in col.cat.categories for c in eski):
                        df['Banka Adı'] = col.astype(str).replace(BANKA_AD_ESLEME).astype('category')
                    else:
                        df['Banka Adı'] = col.cat.rename_categories(BANKA_AD_ESLEME)
            elif col.isin(list(BANKA_AD_ESLEME)).any():
                df['Banka Adı'] = col.replace(BANKA_AD_ESLEME)

        self.df = df

        if not pd.api.types.is_datetime64_any_dtype(df['Tarih']):
            df['Tarih'] = pd.to_datetime(df['Tarih'])

        _veri_duzeltmeleri_uygula(df)
        if 'Kalem Adı' in df.columns:
            _kategori_normalle(df, 'Kalem Adı', kalem_norm)

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
            ('sermaye_orani', df['Tablo Adı'] == 'Kredilere İlişkin Olarak Ayrılan Özel Karşılıklar'),
            # tp_spread/yp_spread için (2026-09-21, kullanıcının verdiği DAX
            # formülüne göre) — kaynak şablonda başında fazladan bir boşluk
            # var (' Kredilerden...'), bu proje genelinde sık görülen bir
            # BDDK şablon tuhaflığı (bkz. sermaye_orani docstring'i).
            ('kredi_faiz_tpyp', df['Tablo Adı'] == ' Kredilerden Alınan Faiz Gelirlerine İlişkin Bilgiler'),
            ('mevduat_faiz_vade', df['Tablo Adı'] == 'Mevduata Ödenen Faizin Vade Yapısına Göre Gösterimi'),
            ('katilma_kar_payi_vade', df['Tablo Adı'] == 'Katılma Hesaplarına Ödenen Kar Paylarının Vade Yapısına Göre Gösterimi'),
            ('karsilik_gid', df['Tablo Adı'] == 'Bankaların Kredi ve Diğer Alacaklarına İlişkin Karşılık Giderleri'),
            # TP/YP Getirili Aktif – Maliyetli Pasif spread'i için (2026-09-30):
            # faiz gelir/giderlerinin TP/YP kırılımlı dipnot tabloları (kalem
            # adları tablolar arasında çakışmıyor, tek anahtarda toplanıyor).
            ('faiz_tpyp', df['Tablo Adı'].isin([
                ' Menkul Değerlerden Alınan Faizlere İlişkin Bilgiler',
                'Bankalardan Alınan Faiz Gelirlerine İlişkin Bilgiler',
                'Kullanılan Kredilere Verilen Faizlere İlişkin Bilgiler',
                'İhraç Edilen Menkul Kıymetlere Verilen Faizler'])),
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

        # Hızlı erişim (2026-09-29): _lookup her kalem için pandas MultiIndex .loc
        # çağırıyordu — tam hesaplamada ~1,1 milyon çağrı, sürenin neredeyse tamamı
        # (compute_all 15,8 sn → 1,0 sn; build_group_data 19,6 sn → 0,9 sn; çıktı
        # birebir aynı). _idx (Series) korunur: TracingLookupContext onu kullanır.
        self._fast = {}
        for k, s in self._idx.items():
            if len(s) == 0 or s.index.nlevels < 4:
                self._fast[k] = {}
                continue
            # Seviye nesneleri paylaşılır (51 tarih, birkaç bin kalem): satır başına yeni
            # Timestamp/str üretmek 2M girdide ~2 GB tutuyordu.
            mi = s.index
            lv = [list(mi.levels[i]) for i in range(4)]
            keys = zip(*(map(lv[i].__getitem__, mi.codes[i].tolist()) for i in range(4)))
            self._fast[k] = dict(zip(keys, s.to_numpy().tolist()))
        self._ts_cache = {}
        self._knorm: Dict[str, str] = {}
        self._pos = {b: {d: i for i, d in enumerate(ds)} for b, ds in self._dates_by_bank.items()}

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

    def _k(self, kalem) -> str:
        """İstenen kalem adının normal biçimi (önbellekli; bkz. kalem_norm)."""
        k = self._knorm.get(kalem)
        if k is None:
            k = self._knorm[kalem] = kalem_norm(kalem)
        return k

    def _lookup(self, table_key: str, banka, tarih, kalem, pb) -> float:
        d = self._fast.get(table_key)
        if not d:
            return 0.0
        return d.get((banka, self._ts(tarih), self._k(kalem), pb), 0.0)

    def var(self, table_key: str, banka, tarih, kalem, pb='Toplam') -> bool:
        """Kalem o banka-dönemin ham dosyasında satır olarak var mı (değeri 0 olsa da)?
        Eski şablonda hiç bulunmayan kalemi, değeri gerçekten 0 olandan ayırmak için."""
        d = self._fast.get(table_key) or {}
        return (banka, self._ts(tarih), self._k(kalem), pb) in d

    def _ts(self, tarih):
        """_norm_tarih'in önbellekli hâli — aynı 'YYYY-MM-DD' milyonlarca kez gelir."""
        if isinstance(tarih, pd.Timestamp):
            return tarih
        t = self._ts_cache.get(tarih)
        if t is None:
            t = self._ts_cache[tarih] = pd.Timestamp(tarih)
        return t

    # Tablo erişimleri
    def bilanco(self, banka, tarih, kalem, pb='Toplam'):
        k = self._k(kalem)
        if k == 'Ortaklık Yatırımları' and not self.var('bilanco', banka, tarih, k, pb):
            # 2013-2017 şablonunda tek satır yok: iştirakler + bağlı ortaklıklar + birlikte kontrol edilenler
            return sum(self._lookup('bilanco', banka, tarih, x, pb) for x in ESKI_ORTAKLIK_KALEMLERI)
        v = self._lookup('bilanco', banka, tarih, k, pb)
        if v == 0 and k == 'Beklenen Zarar Karşılıkları (-)':
            # 2018-03 dosyalarında toplam satırı boş, aşama satırları (1./2./3. aşama) dolu
            v = sum(self._lookup('bilanco', banka, tarih, x, pb) for x in BZK_ASAMA_KALEMLERI)
        return v

    def gelir(self, banka, tarih, kalem, pb='Toplam'):
        k = self._k(kalem)
        if k == 'Personel Giderleri (-)' and pb == 'Toplam':
            return self.personel_giderleri(banka, tarih)
        return self._lookup('gelir', banka, tarih, k, pb)

    # --- Personel gideri ve OPEX (2026-10-03, ham veri şablon farkları) -------------------
    # • 2013-2017 şablonunda gelir tablosunda personel satırı yok; personel 'Diğer Faaliyet
    #   Giderleri'nin içinde. Personel tutarı 'Diğer Faaliyet Giderlerine İlişkin Bilgiler'
    #   dipnotunda ayrıca var (dipnot toplamı = Diğer Faaliyet Giderleri).
    # • 2018-12 ham verisinde 17 mevduat bankasının gelir tablosu personel satırı dipnotun tam
    #   2 katı (ör. Akbank 9A18 1.567 → 12A18 4.246; dipnot 2.123 ve toplam gider kimliği dipnotu
    #   doğruluyor). Bu durumda dipnot değeri kullanılır.
    # • 2018-06/09 katılım bankalarında gelir tablosu satırı yok ama Diğer Faaliyet Giderleri
    #   personeli içermiyor (Brüt faaliyet kârı − karşılık − DFG − net faaliyet kârı = dipnot
    #   personel); personel dipnottan alınıp OPEX'e eklenir.
    def personel_giderleri(self, banka, tarih):
        g = self._lookup('gelir', banka, tarih, 'Personel Giderleri (-)', 'Toplam')
        d = self._lookup('faaliyet_gid_detay', banka, tarih, 'Personel Giderleri', 'Toplam')
        if g and d and 1.8 <= g / d <= 2.3:
            return d
        return g if g else d

    def _personel_ayri(self, banka, tarih) -> bool:
        """Personel gideri gelir tablosunda 'Diğer Faaliyet Giderleri'nden ayrı mı raporlanmış?"""
        if self._lookup('gelir', banka, tarih, 'Personel Giderleri (-)', 'Toplam'):
            return True
        if self._ts(tarih) < TFRS9_BASLANGIC:
            return False
        d = self._lookup('faaliyet_gid_detay', banka, tarih, 'Personel Giderleri', 'Toplam')
        if not d:
            return False
        g = lambda k: self._lookup('gelir', banka, tarih, k, 'Toplam')
        ima = (g('Faaliyet Gelirleri/Giderleri Toplamı') - g('Kredi Ve Diğer Alacaklar Değer Düşüş Karşılığı (-)')
               - g('Diğer Faaliyet Giderleri (-)') - g('Net Faaliyet Karı/Zararı'))
        return abs(ima - d) <= 0.05 * abs(d)

    def opex(self, banka, tarih):
        """Toplam faaliyet gideri (personel dahil), şablon farklarından bağımsız."""
        dfg = self._lookup('gelir', banka, tarih, 'Diğer Faaliyet Giderleri (-)', 'Toplam')
        return dfg + (self.personel_giderleri(banka, tarih) if self._personel_ayri(banka, tarih) else 0.0)

    def mvy(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('mvy', banka, tarih, kalem, pb)

    def tfv(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('tfv', banka, tarih, kalem, pb)

    def kredi_faiz_tpyp(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('kredi_faiz_tpyp', banka, tarih, kalem, pb)

    def faiz_tpyp(self, banka, tarih, kalem, pb='Toplam'):
        """Menkul değer / bankalar faiz gelirleri ile kullanılan kredi ve ihraç
        edilen MK faiz giderlerinin TP/YP kırılımlı dipnot tabloları."""
        return self._lookup('faiz_tpyp', banka, tarih, kalem, pb)

    def mevduat_faiz_vade(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('mevduat_faiz_vade', banka, tarih, kalem, pb)

    def katilma_kar_payi_vade(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('katilma_kar_payi_vade', banka, tarih, kalem, pb)

    def karsilik_gid(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('karsilik_gid', banka, tarih, kalem, pb)

    def sube(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('sube', banka, tarih, kalem, pb)

    def bd(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('bd', banka, tarih, kalem, pb)

    def tk_detay(self, banka, tarih, kalem, pb='Toplam'):
        return self._lookup('tk_detay', banka, tarih, kalem, pb)

    def grup12(self, banka, tarih, kalem, pb='Toplam'):
        k = self._k(kalem)
        if k.endswith(GRUP1_TOPLAM_EKI) and not self.var('grup12', banka, tarih, k, pb):
            # 2013-2017: standart nitelikli krediler tek 'Toplam' satırı yerine üç alt satırda
            kat = k[:-len(GRUP1_TOPLAM_EKI)]
            return sum(self._lookup('grup12', banka, tarih, f'{kat}, Standart Nitelikli, {x}', pb)
                       for x in ESKI_GRUP1_ALT_KALEMLER)
        return self._lookup('grup12', banka, tarih, k, pb)

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

    def sermaye_orani(self, banka, tarih, kalem, pb='Toplam'):
        """'Kredilere İlişkin Olarak Ayrılan Özel Karşılıklar' tablosu — BDDK
        şablonunda mislabeled/reused bir sayfa adı (bu proje genelinde sıkça
        görülen bir kalıp, bkz. tcmb/sermaye docstring'leri); gerçekte
        Sermaye Yeterliliği Standart Oranına İlişkin Özet Bilgi'yi taşıyor
        ('Sermaye Yeterlilik Rasyosu (%)', 'Çekirdek Sermaye Yeterliliği
        Oranı (%)', 'Ana Sermaye Yeterliliği Oranı (%)'). 2026-09-12'de
        BDR-Kısayol entegrasyonu sırasında keşfedildi — BDDK'nın kendisi bu
        oranları zaten hesaplayıp raporluyor, ayrıca türetmeye gerek yok
        (1055/1055 ve 1054/1054 tarihsel noktada ±0.01pp içinde doğrulandı)."""
        return self._lookup('sermaye_orani', banka, tarih, kalem, pb)

    # tp_spread/yp_spread için (2026-09-21, kullanıcının verdiği PBI DAX
    # formülüne göre): "[TP/YP Vadeli Mevduatın Maliyeti]" ölçüsünün PAYI —
    # gerçek vadeli (vadesiz hariç) TP/YP faiz/kâr payı gideri.
    # - Mevduat bankası: 'Mevduata Ödenen Faizin Vade Yapısına Göre
    #   Gösterimi' tablosunda (TP/YP, Toplam, Toplam) − (TP/YP, Toplam,
    #   Vadesiz) — Toplam maturity kırılımı vadesizi de içeriyor.
    # - Katılım bankası: 'Katılma Hesaplarına Ödenen Kar Paylarının Vade
    #   Yapısına Göre Gösterimi' tablosunda 'Toplam -TP/YP Toplam' zaten
    #   SADECE katılma hesaplarını kapsıyor (vadesiz eşleniği olan Özel Cari
    #   Hesaplar bu tabloda hiç yok — ayrı bir tabloda, kâr payı almaz) —
    #   çıkarma gerekmiyor.
    def vadeli_mevduat_faizi(self, banka, tarih, pb):
        if self.bank_turu.get(banka) == 'Katılım':
            toplam = self.katilma_kar_payi_vade(banka, tarih, 'Toplam -' + pb + ' Toplam')
            if pb == 'YP':   # DAX: C − D (kıymetli maden depo kâr payı hariç)
                toplam -= self.katilma_kar_payi_vade(banka, tarih, 'Kıymetli Maden Depo Hesapları - YP Toplam')
            return toplam
        # 2026-09-30 (Rakip Analizi 202606.pdf'ten geri çözüldü): mevduata ödenen
        # TP/YP faizin tamamı, kıymetli maden faizi hariç (payda da KM'yi dışlar).
        # Vadesiz hesaplara faiz ödenmediğinden 'Toplam − Vadesiz' ile aynı; KM
        # yalnız YP'de var (Akbank 2026-06: YP 3.534 − KM 411).
        toplam = self.mevduat_faiz_vade(banka, tarih, 'Mevduata Ödenen Faiz (' + pb + ', Toplam, Toplam)')
        km = self.mevduat_faiz_vade(banka, tarih, 'Mevduata Ödenen Faiz (' + pb + ', Kıymetli Maden, Toplam)')
        return toplam - km

    # tp_spread/yp_spread PAYDASI (2026-09-21, kullanıcı: gerçek PBI ekran
    # görüntüsüyle karşılaştırınca değerler ~100-250bps yüksek çıkıyordu —
    # kök neden: payda "TOPLAM TP/YP Mevduat" (vadesiz dahil) kullanılıyordu,
    # bu maliyeti olduğundan düşük gösterip spread'i şişiriyordu).
    #
    # Mevduat bankası: 2026-09-30'dan beri DTH / kur riski bankalar mevduatı /
    # vade tablosu vadesizleriyle (bkz. vadeli_mevduat_bakiyesi içindeki not).
    # Önceki yaklaşıklık (bilanço − DTH ve KM vadesizi) PDF'ten TP'de ~7, YP'de
    # ~15 bps sapıyordu.
    #
    # Katılım bankası (2026-09-27): kâr payı alan bakiye = bilançodaki TP/YP
    # Mevduat − kâr payı almayan Özel Cari Hesaplar ('Toplanan Fonların Vade
    # Yapısı' tablosu); YP'de ayrıca Kıymetli Maden DH da düşülür. Önceden
    # toplam bakiye (vadesiz dahil) kullanılıyordu: maliyet düşük, spread
    # yüksek çıkıyordu (KT TP spread +649 bps, PBI −67). Rakip Analizi
    # 202606.pdf ile katılım bankalarında PBI'a bps düzeyinde yaklaşıyor.
    _OZEL_CARI = {
        'TP': ('Özel Cari Hesaplar Gerçek Kişi Ticari Olmayan-TP  Toplam',
               'Özel Cari Hesaplar Diğer-TP  Toplam'),
        'YP': ('Özel Cari Hesaplar Gerçek Kişi Ticari Olmayan- YP  Toplam',
               'Özel Cari Hesaplar Diğer-YP  Toplam'),
    }

    def vadeli_mevduat_bakiyesi(self, banka, tarih, pb):
        toplam_pb = self.bilanco(banka, tarih, 'Mevduat', pb)
        if self.bank_turu.get(banka) == 'Katılım':
            if pb not in self._OZEL_CARI:
                return toplam_pb - self.vadesiz_mevduat(banka, tarih)
            ozel_tp = sum(self.tfv(banka, tarih, k) for k in self._OZEL_CARI['TP'])
            if pb == 'TP':
                return toplam_pb - ozel_tp
            # DAX: [YP Vadeli (KM Hariç)] = [Vadeli] − [TP Vadeli] − [KM Vadeli]
            vadeli = self.bilanco(banka, tarih, 'Mevduat') - self.vadesiz_mevduat(banka, tarih)
            tp_vadeli = self.bilanco(banka, tarih, 'Mevduat', 'TP') - ozel_tp
            km_vadeli = self.kiymetli_maden(banka, tarih) - self.tfv(banka, tarih, 'Kıymetli Maden DH Vadesiz')
            return vadeli - tp_vadeli - km_vadeli
        # Mevduat bankası (2026-10-01, Power BI DAX'ına birebir):
        #   [TP Vadeli Mevduat] = [TP Mevduat] − [TP Vadesiz Mevduat]
        #   [TP Vadesiz Mevduat] = Tasarruf + Resmi + Ticari + Diğer Kurul. vadesiz
        #       + 'Bankalar Mevduatı' (banka vadesizlerinin toplamı) − Yurtdışı Bankalar vadesiz
        #   [YP Vadeli Mevduat (KM Hariç)] = [Vadeli Mevduat] − [TP Vadeli] − [KM Vadeli]
        #       ([Vadeli] = Toplam Mevduat − Vadesiz; [KM Vadeli] = KM − KM Vadesiz)
        # Önceki geri çözüm (banka vadesizlerin tamamı çıkarılıyordu) Halk/Enpara/Ziraat'ta
        # PDF'ten sapıyordu; DAX ile 8/14 mevduat bankası iki spread'de de birebir.
        if pb == 'TP':
            return toplam_pb - self._tp_vadesiz_dax(banka, tarih)
        if pb == 'YP':
            vadeli = self.bilanco(banka, tarih, 'Mevduat') - self.vadesiz_mevduat(banka, tarih)
            tp_vadeli = self.bilanco(banka, tarih, 'Mevduat', 'TP') - self._tp_vadesiz_dax(banka, tarih)
            km_vadeli = self.kiymetli_maden(banka, tarih) - self.mvy(banka, tarih, 'Kıym. Mad. Depo Hesabı, Vadesiz')
            return vadeli - tp_vadeli - km_vadeli
        return toplam_pb - self.vadesiz_mevduat(banka, tarih)

    def _mvy_vadesiz(self, banka, tarih, kalem):
        """Bazı BDDK kalem adları sonda boşlukla gelir ('Tasarruf Mevduatı, Vadesiz ')."""
        return self.mvy(banka, tarih, kalem) or self.mvy(banka, tarih, kalem + ' ')

    def _tp_vadesiz_dax(self, banka, tarih):
        v = self._mvy_vadesiz
        return (v(banka, tarih, 'Tasarruf Mevduatı, Vadesiz')
                + v(banka, tarih, 'Resmi Kurul. Mev., Vadesiz')
                + v(banka, tarih, 'Ticari Kurul. Mevd., Vadesiz')
                + v(banka, tarih, 'Diğer Kurul. Mevd., Vadesiz')
                + v(banka, tarih, 'Bankalar Mevduatı')
                - v(banka, tarih, 'Bank. Mevduat, Yurtdışı Bankalar, Vadesiz'))

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
        """PBI [Tüzel Mevduat] — Resmi Kuruluşlar HARİÇ (2026-09-23, PBI
        datatable'ıyla doğrulandı: Akbank 2025-12 Ticari 529.855 + Diğer
        15.310 = 545.165 mn, PBI 545.165). Katılım'da fon tablosu tüzel
        kişileri birden çok segmentte veriyor: Ticari + Diğer (her segmentte,
        index aynı adlı satırları topluyor) + YP özel cari hesaplardaki
        yurtiçi/yurtdışı yerleşik tüzel kişiler + 'Ticari ve Diğer Kur.'
        (KT 2025-12: 187.316 mn, PBI 187.316). Kalem adlarındaki çift/üçlü
        boşluklar BDDK şablonunda böyle."""
        if self.bank_turu.get(banka) == 'Katılım':
            return (
                self.tfv(banka, tarih, 'Ticari Kuruluşlar  Toplam')
                + self.tfv(banka, tarih, 'Diğer Kuruluşlar  Toplam')
                + self.tfv(banka, tarih, 'Yurtiçinde Yer. Tüz. K   Toplam')
                + self.tfv(banka, tarih, 'Yurtdışında Yer. Tüz. K.  Toplam')
                + self.tfv(banka, tarih, 'Ticari ve Diğer Kur.  Toplam')
            )
        return (
            self.mvy(banka, tarih, 'Tic. Kur. Mevduatı, Toplam')
            + self.mvy(banka, tarih, 'Diğ. Kur. Mevduatı, Toplam')
        )

    # Zaman serisi yardımcıları
    def get_dates(self, banka):
        return self._dates_by_bank.get(banka, [])

    def prev_period(self, banka, tarih):
        i = self._pos.get(banka, {}).get(self._ts(tarih))
        return self._dates_by_bank[banka][i - 1] if i else None

    def yoy_period(self, banka, tarih):
        i = self._pos.get(banka, {}).get(self._ts(tarih))
        return self._dates_by_bank[banka][i - 4] if i is not None and i >= 4 else None

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
    """IFRS9 sonrası 'Krediler Ve Alacaklar (Toplam)', legacy 'Krediler'.

    2018-06 ve 2018-09 ham verisinde '(Toplam)' satırı yalnız canlı kredileri ('Krediler Ve
    Alacaklar' = 1. + 2. grup) taşıyor; diğer tüm TFRS 9 dönemlerinde olduğu gibi donuk,
    kiralama ve faktoring alacakları eklenmemiş (2026-10-03: 823 banka-dönemin 779'unda
    '(Toplam)' = Krediler Ve Alacaklar + Faktoring + Kiralama + Donuk; kalan 44'ün tamamı bu iki
    dönem). Bu durumda toplam bileşenlerden kurulur."""
    v = ctx.bilanco(banka, tarih, 'Krediler Ve Alacaklar (Toplam)', pb)
    if v == 0:
        return ctx.bilanco(banka, tarih, 'Krediler', pb)
    if hasattr(ctx, 'var') and ctx.var('bilanco', banka, tarih, 'Donuk Alacaklar', pb):
        kva = ctx.bilanco(banka, tarih, 'Krediler Ve Alacaklar', pb)
        ek = (ctx.bilanco(banka, tarih, 'Donuk Alacaklar', pb)
              + ctx.bilanco(banka, tarih, 'Kiralama İşlemlerinden Alacaklar', pb)
              + ctx.bilanco(banka, tarih, 'Faktoring Alacakları', pb))
        if ek and abs(v - kva) <= max(1.0, abs(v) * 1e-9):
            return kva + ek
    return v


def donuk_alacaklar(ctx, banka, tarih, pb='Toplam'):
    """Donuk (takipteki) alacaklar. TFRS 9 sonrası bilançoda 'Donuk Alacaklar'; 2013–2017
    dosyalarında aynı kalem 'Takipteki Krediler' adıyla (eski BDDK formatı) bulunur.
    Yeni kalem 0 ise eski kaleme düşülür (krediler() ile aynı mantık)."""
    v = ctx.bilanco(banka, tarih, 'Donuk Alacaklar', pb)
    if v == 0:
        v = ctx.bilanco(banka, tarih, 'Takipteki Krediler', pb)
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
