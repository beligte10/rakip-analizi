"""
pipeline.datatable
===================
`datatable_1.xlsx` (Power BI export) formatını okuyup dashboard payload'ı
(`computed.json`) üretir. BDDK banka-başına xlsx pipeline'ının (ingest.py +
lookup.py + measures.py) yerine geçer.

KAYNAK FORMAT (2 sheet, header 1. satırda):
  Kalem sheet : BankName | Tarih | KalemlerSlicer2 (DEĞER) | Kalem (isim)
                86 kalem, değerler MİLYON TL (adet olanlar hariç)
  Rasyo sheet : BankName | Tarih | RasyolarToplu3 (DEĞER) | Rasyolar (isim)
                141 rasyo, ölçek rasyodan rasyoya DEĞİŞİR (bkz. _scale)

`BankName` içinde 27 gerçek banka + 5 grup satırı (KAMU/KATILIM/MEVDUAT/
RAKİP/SEKTÖR) bulunur. Grup satırları KULLANILMAZ — catalog.json'daki kendi
grup tanımlarımız (5 grup) banka değerlerinden yeniden hesaplanır, çünkü
datatable'ın RAKİP tanımı (3 banka) catalog'unkiyle (5 banka) uyuşmuyor ve
"KT Hariç Katılım Bankaları" datatable'da hiç yok.

ÖLÇEK KURALLARI (catalog.json'daki `birim` alanına göre):
  Kalem  + birim TL      → × 1e6   (milyon TL → TL)
  Kalem  + birim adet    → × 1     (Şube/Personel Sayısı)
  Rasyo  + birim %       → × 100   (oran 0-1 → yüzde)
  Rasyo  + birim % (bps) → ÷ 100   (BPS_RATIOS listesindekiler)
  Rasyo  + birim kat     → × 1
  Rasyo  + birim bin_TL  → × 1     (zaten bin TL)

BİLİNEN KAYNAK VERİ SORUNU: Serinin ilk dönemlerinde (2015) ortalama-bakiye
gerektiren rasyolar (ROAA, ROAE vb.) kaynak dosyada hatalı olabilir — PBI
modeli t-4 çeyrek olmadığı için anlamsız değerler üretmiş (örn. KT ROAA
2015-Q1 = 11.6 ≈ %1160). inf/NaN değerler None'a çevrilir; bu tür aşırı
değerler için `--sanity-max` eşiği kullanılabilir.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ============================================================
# Sabitler
# ============================================================

GROUP_ROWS_IN_SOURCE = {'KAMU', 'KATILIM', 'MEVDUAT', 'RAKİP', 'SEKTÖR'}

# Değeri BPS cinsinden gelen rasyolar (catalog birim='%' ama kaynak bps)
BPS_RATIOS = {
    'Brüt CoR (bps)',
    'Spread (bps)',
    "Kredi Mevduat Spread'i",
    "TP Kredi Mevduat Spread'i",
    "YP Kredi Mevduat Spread'i",
}

# catalog measure id → (sheet, datatable'daki isim)
# Sadece isim normalize edilerek OTOMATİK eşleşmeyenler burada.
MANUAL_MAP: Dict[str, Tuple[str, str]] = {
    # --- Büyüklükler (Kalem sheet) ---
    'krediler':                            ('kalem', 'Toplam Brüt Krediler'),
    'mevduat':                             ('kalem', 'Toplam Mevduat'),
    'tuzel_krediler':                      ('kalem', 'Tüzel Krediler ve Kurumsal Kredi Kartları'),
    'donuk_alacaklar_satis_terkin_oncesi': ('kalem', 'Donuk Alacaklar, Terkin Dahil'),
    'kiymetli_maden_mevduati':             ('kalem', 'KM Mevduatı'),
    'gayrinakdi_krediler':                 ('kalem', 'Gayrinakdi Krediler'),
    'net_donem_kari':                      ('kalem', 'Net Dönem Karı/Zararı'),
    'net_faiz_geliri':                     ('kalem', 'Net Faiz Geliri/Gideri'),
    'net_ucret_komisyonlar':               ('kalem', 'Net Ücret ve Komisyon Gelirleri/Giderleri'),
    'net_ticari_kar':                      ('kalem', 'Net Ticari Kar/Zarar'),
    'diger_faaliyet_giderleri':            ('kalem', 'Diğer Faaliyet Giderleri (OPEX)'),
    'karsilik_giderleri':                  ('kalem', 'Beklenen Zarar Karşılıkları'),
    'gnakdi_alinan_ucret_komisyonlar':     ('kalem', 'Gayrinakdi Kredilerden Alınan Ücret Ve Komisyonlar'),

    # --- Rasyolar (Rasyo sheet) ---
    'krediler_ta':                         ('rasyo', 'Brüt Krediler/ Toplam Aktifler'),
    'grup_1_krediler_toplam':              ('rasyo', 'Grup 1 Krediler Oranı'),
    'npl_rasyosu':                         ('rasyo', 'Takibe Dönüşüm Oranı (NPL Rasyosu)'),
    'npl_rasyosu_satis_terkin_oncesi':     ('rasyo', 'NPL (Terkin Dahil)'),
    'npl_karsilama_orani':                 ('rasyo', 'Toplam NPL Karşılama Oranı'),
    'donuk_tahsilat_ort_krediler':         ('rasyo', 'Donuk Alacaklar, Dönemiçi Tahsilat/ Ortalama Krediler'),
    'donuk_intikal_ort_krediler':          ('rasyo', 'Donuk Alacaklar, Dönemiçi İntikal/ Ortalama Krediler'),
    'grup_2_tuketici_tuketici':            ('rasyo', 'Grup 2 Tüketici/ Tüketici Kredileri'),
    'grup_2_tuzel_tuzel':                  ('rasyo', 'Grup 2 Tüzel/ Tüzel Krediler'),
    'konut_tp_pasifler':                   ('rasyo', 'Konut Kredileri/ TP Pasifler (Özkaynak Hariç)'),
    'faiz_getirili_maliyetli':             ('rasyo', 'Faiz (Kar Payı) Getirili Aktifler/ Faiz (Kar Payı) Maliyetli Pasifler'),
    'faiz_getirili_ozkaynak':              ('rasyo', 'Ortalama Faiz (Kar Payı) Getirili Aktifler/ Ortalama Özkaynaklar'),
    'alinan_krediler_iemk_toplam_kaynak':  ('rasyo', 'Alınan Krediler+İhç Edilen Mk(Net)/Toplam Kaynak'),
    'tp_alinan_toplam_alinan':             ('rasyo', 'TP Alınan Krediler+İhç Edilen Mk(Net)/Toplam AK.+İ.E.MK.'),
    'tp_pasifler_toplam_pasifler_ozkaynak_haric': ('rasyo', 'TP Pasifler/ Toplam Pasifler (Özkaynak Hariç)'),
    'syr':                                 ('rasyo', 'SYR'),
    'roaa':                                ('rasyo', 'ROAA'),
    'roae':                                ('rasyo', 'ROAE'),
    'faiz_gideri_faiz_geliri':             ('rasyo', 'Faiz (Kar Payı) Giderleri/ Faiz (Kar Payı) Gelirleri'),
    'nim':                                 ('rasyo', 'Net Faiz (Kar Payı) Marjı'),
    'nim_duzeltilmis':                     ('rasyo', 'Düzeltilmiş Net Faiz (Kar Payı) Marjı'),
    'nim_bzk_sonrasi':                     ('rasyo', 'BZK Sonrası Düzeltilmiş Net Faiz (Kar Payı) Marjı'),
    'gayrinakdi_komisyon_gayrinakdi':      ('rasyo', 'Gayrinakdi Kredilerden Alınan Faiz (Kar Payı)/ Gayrinakdi Krediler'),
    'net_ucret_operasyonel':               ('rasyo', 'Net Ücret ve Komisyonlar/ Faaliyet Giderleri'),
    'maliyet_gelir':                       ('rasyo', 'Standart Maliyet Gelir Rasyosu'),
    'maliyet_gelir_duzeltilmis':           ('rasyo', 'Düzeltilmiş Maliyet Gelir Rasyosu'),
    'cost_of_risk':                        ('rasyo', 'Brüt CoR (bps)'),
    'spread':                              ('rasyo', 'Spread (bps)'),
    # measures.py'de kaynak_pacal_maliyet == faiz_maliyetli_pasif_maliyeti
    'kaynak_pacal_maliyet':                ('rasyo', 'Faiz (Kar Payı) Maliyetli Pasiflerin Maliyeti'),
    'personel_basina_personel_gideri':     ('rasyo', 'Personel Başına Personel Giderleri'),
}

# Kaynakta güvenilir karşılığı BULUNAMAYAN measure'lar — bilinçli olarak boş
# bırakılır (yanlış eşleştirip sessizce hatalı veri üretmektense).
KNOWN_UNMAPPED = {
    # 'Brüt Faaliyet Karı/Zararı' = BDDK 'Net Faaliyet Karı/Zararı'. Kaynakta
    # 'Faaliyet Gelirleri' ve 'Ana Bankacılık Gelirleri' var ama ikisi de bu
    # tanımın birebir karşılığı değil.
    'brut_faaliyet_kari',
}

# Grup rasyo aggregasyonunda ağırlık (= payda) olarak kullanılacak Kalem adı.
# Matematiksel temel: rasyo_i = pay_i / payda_i olduğundan
#   Σ(rasyo_i × payda_i) / Σ(payda_i) = Σpay_i / Σpayda_i
# yani hazır rasyodan ağırlıklı ortalama TAM olarak yeniden kurulabilir.
DENOM_ALIAS: Dict[str, str] = {
    'toplam aktifler': 'Toplam Aktifler',
    'ortalama aktifler': 'Toplam Aktifler',
    'toplam pasifler': 'Toplam Aktifler',              # bilanço dengesi
    'toplam pasifler (özkaynaklar hariç)': 'Toplam Pasifler (Özkaynak Hariç)',
    'toplam pasifler (özkaynak hariç)': 'Toplam Pasifler (Özkaynak Hariç)',
    'tp pasifler (özkaynak hariç)': 'Toplam Pasifler (Özkaynak Hariç)',
    'toplam krediler': 'Toplam Brüt Krediler',
    'krediler': 'Toplam Brüt Krediler',
    'mevduat': 'Toplam Mevduat',
    'toplam mevduat': 'Toplam Mevduat',
    'altındışı mevduat': 'Toplam Mevduat (KM Hariç)',
    'toplam kaynak': 'Toplam Kaynak',
    'altındışı kaynak': 'Toplam Kaynak',
    'özkaynaklar': 'Özkaynaklar',
    'toplam özkaynaklar': 'Toplam Özkaynaklar',
    'ortalama özkaynaklar': 'Özkaynaklar',
    'yp krediler': 'YP Brüt Krediler',
    'yp pasifler': 'YP Aktifler',
    'yp kaynak': 'YP Kaynak',
    'yp altındışı kaynak': 'YP Kaynak',
    'yp altındışı mevduat': 'YP Mevduat',
    'tp mevduat': 'TP Mevduat',
    'tp kaynak': 'TP Kaynak',
    'tüketici kredileri': 'Tüketici Kredileri (KK Hariç)',
    'tüzel krediler': 'Tüzel Krediler ve Kurumsal Kredi Kartları',
    'tüzel mevduat': 'Tüzel Mevduat',
    'çekirdek sermaye': 'Çekirdek Sermaye (CET 1)',
    'maliyetli pasifler': 'Faiz (Kar Payı) Maliyetli Pasifler',
    'faiz (kar payı) maliyetli pasifler': 'Faiz (Kar Payı) Maliyetli Pasifler',
    'faiz (kar payı) getirili aktifler': 'Faiz (Kar Payı) Getirili Aktifler',
    'faiz (kar payı) gelirleri': 'Faiz (Kar Payı) Gelirleri',
    'faiz (kar payı) geliri': 'Faiz (Kar Payı) Gelirleri',
    'net dönem kar/zararı': 'Net Dönem Karı/Zararı',
    'net dönem karı/zararı': 'Net Dönem Karı/Zararı',
    'gayrinakdi krediler': 'Gayrinakdi Krediler',
    'operasyonel giderler': 'Diğer Faaliyet Giderleri (OPEX)',
    'faaliyet giderleri': 'Diğer Faaliyet Giderleri (OPEX)',
    'toplam vadeli mevduat': 'Vadeli Mevduat',
    'toplam risk tabanı': 'Toplam Aktifler',           # RAV yok — yaklaşık
    'ortalama rav': 'Toplam Aktifler',                 # RAV yok — yaklaşık
}

# Adı "X / Y" kalıbında OLMAYAN (ROAA, SYR, NIM, Spread gibi) rasyolar için
# paydayı elle tanımla. İkinci eleman: ağırlık TAM mı (True) yoksa YAKLAŞIK mı
# (False). Yaklaşık olanlar kaynakta payda kalemi hiç bulunmayan rasyolardır —
# örn. RAV (risk ağırlıklı varlık) datatable'da yok, Toplam Aktifler ile
# ağırlıklandırılır. Rapor bunları ayrıca listeler.
MANUAL_DENOM: Dict[str, Tuple[str, bool]] = {
    'npl_rasyosu_satis_terkin_oncesi': ('Toplam Brüt Krediler', True),
    'npl_formasyonu':                  ('Toplam Brüt Krediler', True),
    'npl_karsilama_orani':             ('Donuk Alacaklar', True),
    'donuk_tahsilat_ort_krediler':     ('Toplam Brüt Krediler', True),
    'donuk_intikal_ort_krediler':      ('Toplam Brüt Krediler', True),
    'konut_tp_pasifler':               ('TP Kaynak', False),
    'tp_alinan_toplam_alinan':         ('Alınan Krediler', True),
    'roaa':                            ('Toplam Aktifler', True),
    'roae':                            ('Özkaynaklar', True),
    'faiz_getirili_aktif_getirisi':    ('Faiz (Kar Payı) Getirili Aktifler', True),
    'faiz_maliyetli_pasif_maliyeti':   ('Faiz (Kar Payı) Maliyetli Pasifler', True),
    'kaynak_pacal_maliyet':            ('Faiz (Kar Payı) Maliyetli Pasifler', True),
    'kredi_pacal_getiri':              ('Toplam Brüt Krediler', True),
    'cost_of_risk':                    ('Toplam Brüt Krediler', True),
    'nim':                             ('Faiz (Kar Payı) Getirili Aktifler', True),
    'nim_duzeltilmis':                 ('Faiz (Kar Payı) Getirili Aktifler', True),
    'nim_bzk_sonrasi':                 ('Faiz (Kar Payı) Getirili Aktifler', True),
    'komisyon_gid_gel':                ('Alınan Ücret Ve Komisyonlar', True),
    'reklam_net_kar':                  ('Net Dönem Karı/Zararı', True),
    'personel_net_kar':                ('Net Dönem Karı/Zararı', True),
    'maliyet_gelir':                   ('Faaliyet Gelirleri', True),
    'maliyet_gelir_duzeltilmis':       ('Faaliyet Gelirleri', True),
    # --- Aşağıdakiler YAKLAŞIK: gerçek payda kaynakta yok ---
    'syr':                             ('Toplam Aktifler', False),   # payda: RAV
    'cekirdek_syr':                    ('Toplam Aktifler', False),   # payda: RAV
    'rorwa':                           ('Toplam Aktifler', False),   # payda: RAV
    'net_faiz_ort_rav':                ('Toplam Aktifler', False),   # payda: RAV
    # Spread'ler oran değil FARK (iki getiri oranının farkı); aktifle ağırlıklandırılır
    'spread':                          ('Toplam Aktifler', False),
    'kredi_mevduat_spread':            ('Toplam Aktifler', False),
    'tp_spread':                       ('TP Kaynak', False),
    'yp_spread':                       ('YP Kaynak', False),
}

# Şube/Personel başına rasyolar: ağırlık = bölen (adet)
PER_UNIT_DENOM: Dict[str, str] = {
    'sube_basina_krediler': 'Şube Sayısı',
    'sube_basina_mevduat': 'Şube Sayısı',
    'sube_basina_net_kar': 'Şube Sayısı',
    'sube_basina_personel': 'Şube Sayısı',
    'personel_basina_krediler': 'Personel Sayısı',
    'personel_basina_mevduat': 'Personel Sayısı',
    'personel_basina_net_kar': 'Personel Sayısı',
    'personel_basina_personel_gideri': 'Personel Sayısı',
}

# Kompozisyon: component id → Kalem adı (veya None = residual)
# 'total' toplamı verir; residual = total − diğer componentler.
COMPOSITION_SPECS: Dict[str, dict] = {
    'aktif': {
        'total': 'Toplam Aktifler',
        'components': [
            ('nakit', 'Nakit ve Nakit Benzerleri'),
            ('menkul', 'Menkul Kıymetler'),
            ('net_kredi', 'Net Krediler'),
            ('diger', None),
        ],
        'currency': ('TP Aktifler', 'YP Aktifler'),
    },
    'pasif': {
        'total': 'Toplam Aktifler',   # Toplam Pasifler = Toplam Aktifler
        'components': [
            ('mevduat', 'Toplam Mevduat'),
            ('mevduat_disi', ['Alınan Krediler', 'İhraç Edilen Menkul Kıymetler']),
            ('sermaye_benzeri', 'Sermaye Benzeri Krediler'),
            ('ozkaynak', 'Özkaynaklar'),
            ('diger', None),
        ],
        'currency': None,
    },
    'kaynak': {
        'total': 'Toplam Kaynak',
        'components': [
            ('mevduat', 'Toplam Mevduat'),
            ('alinan_kredi', 'Alınan Krediler'),
            ('ihrac', 'İhraç Edilen Menkul Kıymetler'),
            ('para_piyasa', None),   # residual
        ],
        'currency': ('TP Kaynak', 'YP Kaynak'),
    },
    'kredi': {
        'total': 'Toplam Brüt Krediler',
        'components': [
            ('tuketici_kart', 'Tüketici Kredileri ve Bireysel Kredi Kartları'),
            ('mali_kesim', 'Mali Kesime Verilen Krediler'),
            ('dis_ticaret', 'Dış Ticaret Kredileri'),
            ('leasing', 'Finansal Kiralama Alacakları'),
            ('tuzel_diger', None),
        ],
        'currency': ('TP Brüt Krediler', 'YP Brüt Krediler'),
    },
    'gelir': {
        'total': None,   # component toplamı
        'components': [
            ('net_faiz', 'Net Faiz Geliri/Gideri'),
            ('net_komisyon', 'Net Ücret ve Komisyon Gelirleri/Giderleri'),
            ('net_ticari', 'Net Ticari Kar/Zarar'),
            ('diger_faaliyet', 'Diğer Faaliyet Gelirleri'),
        ],
        'currency': None,   # gelir tablosunda TP/YP yok
    },
}


def norm(s) -> str:
    """'a / b', 'a/ b', 'a  /b' → 'a/b' (küçük harf)."""
    s = str(s).strip()
    s = re.sub(r'\s*/\s*', '/', s)
    s = re.sub(r'\s+', ' ', s)
    return s.lower()


# ============================================================
# Kaynak okuma
# ============================================================

class DatatableContext:
    """datatable xlsx'ine (entity, tarih, isim) → değer şeklinde erişim."""

    def __init__(self, kalem_df: pd.DataFrame, rasyo_df: pd.DataFrame):
        self.kalem = self._index(kalem_df, 'KalemlerSlicer2', 'Kalem')
        self.rasyo = self._index(rasyo_df, 'RasyolarToplu3', 'Rasyolar')
        self.kalem_names = {norm(n): n for n in kalem_df['Kalem'].unique()}
        self.rasyo_names = {norm(n): n for n in rasyo_df['Rasyolar'].unique()}

        entities = set(kalem_df['BankName'].unique()) | set(rasyo_df['BankName'].unique())
        self.banks = sorted(entities - GROUP_ROWS_IN_SOURCE)
        self.dates = sorted(set(kalem_df['Tarih'].unique()) | set(rasyo_df['Tarih'].unique()))

    @staticmethod
    def _index(df: pd.DataFrame, val_col: str, name_col: str) -> Dict[tuple, float]:
        d = df[[val_col, 'BankName', 'Tarih', name_col]].copy()
        d[val_col] = pd.to_numeric(d[val_col], errors='coerce')
        d = d.replace([np.inf, -np.inf], np.nan).dropna(subset=[val_col])
        return {
            (b, t, n): float(v)
            for v, b, t, n in zip(d[val_col], d['BankName'], d['Tarih'], d[name_col])
        }

    def get_kalem(self, entity: str, tarih: str, name: str) -> Optional[float]:
        return self.kalem.get((entity, tarih, name))

    def get_rasyo(self, entity: str, tarih: str, name: str) -> Optional[float]:
        return self.rasyo.get((entity, tarih, name))

    @classmethod
    def from_xlsx(cls, path: Path | str) -> 'DatatableContext':
        path = Path(path)
        kalem = pd.read_excel(path, sheet_name='Kalem', header=0, engine='openpyxl')
        rasyo = pd.read_excel(path, sheet_name='Rasyo', header=0, engine='openpyxl')
        for df in (kalem, rasyo):
            df['Tarih'] = pd.to_datetime(df['Tarih']).dt.strftime('%Y-%m-%d')
        return cls(kalem, rasyo)


# ============================================================
# Measure eşleştirme & ölçekleme
# ============================================================

def build_measure_map(catalog: dict, ctx: DatatableContext) -> Tuple[Dict[str, Tuple[str, str]], List[dict]]:
    """catalog measure id → (sheet, datatable adı). Dönüş: (map, eşleşmeyenler)."""
    mapping: Dict[str, Tuple[str, str]] = {}
    unmapped: List[dict] = []

    for m in catalog['measures']:
        mid, ad = m['id'], m['ad']
        if mid in KNOWN_UNMAPPED:
            unmapped.append({'id': mid, 'ad': ad, 'sebep': 'kaynakta güvenilir karşılık yok'})
            continue
        if mid in MANUAL_MAP:
            sheet, name = MANUAL_MAP[mid]
            src = ctx.kalem_names if sheet == 'kalem' else ctx.rasyo_names
            if norm(name) in src:
                mapping[mid] = (sheet, name)
            else:
                unmapped.append({'id': mid, 'ad': ad, 'sebep': f'MANUAL_MAP hedefi kaynakta yok: {name}'})
            continue
        key = norm(ad)
        if key in ctx.kalem_names:
            mapping[mid] = ('kalem', ctx.kalem_names[key])
        elif key in ctx.rasyo_names:
            mapping[mid] = ('rasyo', ctx.rasyo_names[key])
        else:
            unmapped.append({'id': mid, 'ad': ad, 'sebep': 'isim eşleşmedi'})

    return mapping, unmapped


def _scale(sheet: str, name: str, birim: str) -> float:
    """Kaynak değerini catalog biriminin beklediği ölçeğe çeviren çarpan."""
    if sheet == 'kalem':
        return 1.0 if birim == 'adet' else 1e6      # milyon TL → TL
    if birim == '%':
        return 0.01 if name in BPS_RATIOS else 100.0  # bps → % / oran → %
    return 1.0                                       # kat, bin_TL, adet


# ============================================================
# bank_data
# ============================================================

def build_bank_data(ctx: DatatableContext, catalog: dict,
                    mapping: Dict[str, Tuple[str, str]]) -> Dict[str, dict]:
    """bank_data[measure_id][banka][tarih] = değer (None olabilir)."""
    birim_of = {m['id']: m.get('birim', '') for m in catalog['measures']}
    catalog_banks = [b['banka_adi'] for b in catalog['banks']]
    banks = [b for b in catalog_banks if b in set(ctx.banks)]

    bank_data: Dict[str, dict] = {}
    for mid, (sheet, name) in mapping.items():
        scale = _scale(sheet, name, birim_of.get(mid, ''))
        getter = ctx.get_kalem if sheet == 'kalem' else ctx.get_rasyo
        series: Dict[str, dict] = {}
        for b in banks:
            vals = {}
            for t in ctx.dates:
                raw = getter(b, t, name)
                if raw is not None:
                    vals[t] = raw * scale
            if vals:
                series[b] = vals
        bank_data[mid] = series
    return bank_data


# ============================================================
# group_data — catalog'un KENDİ 5 grup tanımıyla
# ============================================================

def _denom_kalem_for(mid: str, ad: str, ctx: DatatableContext) -> Tuple[Optional[str], bool]:
    """
    Rasyonun paydasını temsil eden Kalem adını bul (grup ağırlığı için).
    Dönüş: (kalem_adi | None, tam_mi)  — tam_mi=False ise ağırlık yaklaşıktır.
    """
    if mid in PER_UNIT_DENOM:
        return PER_UNIT_DENOM[mid], True
    if mid in MANUAL_DENOM:
        return MANUAL_DENOM[mid]
    if '/' in ad:
        rhs = norm(ad.split('/')[-1])
        rhs = re.sub(r'\s*\(.*?\)\s*$', '', rhs).strip()   # sondaki parantezi at
        if rhs in DENOM_ALIAS:
            return DENOM_ALIAS[rhs], True
        if rhs in ctx.kalem_names:
            return ctx.kalem_names[rhs], True
    return None, False


def build_group_data(ctx: DatatableContext, catalog: dict,
                     bank_data: Dict[str, dict]) -> Tuple[Dict[str, dict], List[dict]]:
    """
    group_data[measure_id][grup][tarih] = {'value': v}

    - Büyüklük  → Σ üye banka değerleri
    - Rasyo     → Σ(rasyo_i × payda_i) / Σ(payda_i)   (payda = Kalem, TAM ağırlıklı ort.)
    - Paydası bulunamayan rasyo → hesaplanmaz (None), raporda listelenir
    """
    members_map = (catalog.get('groups', {}) or {}).get('members', {}) or {}
    group_data: Dict[str, dict] = {}
    agirliksiz: List[dict] = []
    yaklasik: List[dict] = []

    for m in catalog['measures']:
        mid, ad, tip = m['id'], m['ad'], m.get('tip', 'rasyo')
        series = bank_data.get(mid)
        if not series:
            continue
        group_data.setdefault(mid, {})

        denom_kalem = None
        if tip != 'buyukluk':
            denom_kalem, tam = _denom_kalem_for(mid, ad, ctx)
            if denom_kalem is None:
                agirliksiz.append({'id': mid, 'ad': ad})
                continue
            if not tam:
                yaklasik.append({'id': mid, 'ad': ad, 'agirlik': denom_kalem})

        for gname, members in members_map.items():
            if not members:
                continue
            gd = {}
            for t in ctx.dates:
                if tip == 'buyukluk':
                    vals = [series.get(b, {}).get(t) for b in members]
                    vals = [v for v in vals if v is not None]
                    v = sum(vals) if vals else None
                else:
                    num = den = 0.0
                    any_data = False
                    for b in members:
                        r = series.get(b, {}).get(t)
                        w = ctx.get_kalem(b, t, denom_kalem)
                        if r is None or w is None or w == 0:
                            continue
                        num += r * w
                        den += w
                        any_data = True
                    v = (num / den) if (any_data and den != 0) else None
                if v is not None:
                    gd[t] = {'value': v}
            if gd:
                group_data[mid][gname] = gd

    return group_data, agirliksiz, yaklasik


# ============================================================
# composition_data + currency_data
# ============================================================

def _component_values(ctx: DatatableContext, entities: List[str], t: str,
                      spec: dict) -> Optional[List[dict]]:
    """Bir kompozisyonun bileşen değerlerini (entity listesi toplanarak) üretir."""
    def kalem_sum(name) -> Optional[float]:
        names = name if isinstance(name, list) else [name]
        total, seen = 0.0, False
        for e in entities:
            for n in names:
                v = ctx.get_kalem(e, t, n)
                if v is not None:
                    total += v
                    seen = True
        return total if seen else None

    comps = spec['components']
    vals: Dict[str, Optional[float]] = {}
    for cid, src in comps:
        vals[cid] = None if src is None else kalem_sum(src)

    residual_ids = [cid for cid, src in comps if src is None]
    known = [v for cid, v in vals.items() if cid not in residual_ids and v is not None]
    if not known:
        return None

    if spec['total'] is None:
        total = sum(known)
    else:
        total = kalem_sum(spec['total'])
        if total is None:
            return None

    for cid in residual_ids:
        vals[cid] = total - sum(known)

    if not total:
        return None

    out = []
    for cid, _ in comps:
        v = vals[cid]
        if v is None:
            continue
        out.append({'id': cid, 'value': v * 1e6, 'pct': (v / total) * 100.0})
    return out or None


def _currency_values(ctx: DatatableContext, entities: List[str], t: str,
                     spec: dict) -> Optional[dict]:
    cur = spec.get('currency')
    if not cur:
        return None
    tp_name, yp_name = cur
    tp = yp = 0.0
    seen = False
    for e in entities:
        a, b = ctx.get_kalem(e, t, tp_name), ctx.get_kalem(e, t, yp_name)
        if a is not None:
            tp += a; seen = True
        if b is not None:
            yp += b; seen = True
    if not seen:
        return None
    total = tp + yp
    if not total:
        return None
    return {
        'tp_value': tp * 1e6, 'yp_value': yp * 1e6, 'total_value': total * 1e6,
        'tp_pct': tp / total * 100.0, 'yp_pct': yp / total * 100.0,
    }


def build_composition_data(ctx: DatatableContext, catalog: dict) -> Tuple[dict, dict]:
    members_map = (catalog.get('groups', {}) or {}).get('members', {}) or {}
    catalog_banks = [b['banka_adi'] for b in catalog['banks'] if b['banka_adi'] in set(ctx.banks)]

    composition_data: Dict[str, dict] = {}
    currency_data: Dict[str, dict] = {}

    for cid, spec in COMPOSITION_SPECS.items():
        comp_out = {'bank': {}, 'group': {}}
        curr_out = {'bank': {}, 'group': {}}
        targets = (
            [('bank', b, [b]) for b in catalog_banks]
            + [('group', g, mem) for g, mem in members_map.items() if mem]
        )
        for etype, ename, entities in targets:
            cseries, useries = {}, {}
            for t in ctx.dates:
                cv = _component_values(ctx, entities, t, spec)
                if cv:
                    cseries[t] = cv
                uv = _currency_values(ctx, entities, t, spec)
                if uv:
                    useries[t] = uv
            if cseries:
                comp_out[etype][ename] = cseries
            if useries:
                curr_out[etype][ename] = useries
        composition_data[cid] = comp_out
        if curr_out['bank'] or curr_out['group']:
            currency_data[cid] = curr_out

    return composition_data, currency_data


# ============================================================
# meta
# ============================================================

def build_meta(ctx: DatatableContext, catalog: dict, bank_data: dict,
               old_meta: Optional[dict] = None) -> dict:
    """Statik alanları (renkler, ramp'lar) eski meta'dan korur, dinamikleri yeniden üretir."""
    meta = dict(old_meta or {})
    catalog_banks = [b['banka_adi'] for b in catalog['banks']]
    real = [b for b in catalog_banks if b in set(ctx.banks)]

    date_set = set()
    for series in bank_data.values():
        for b, vals in series.items():
            if b in set(real):
                date_set.update(k for k, v in vals.items() if v is not None)
    dates = sorted(date_set)

    meta['banks'] = [
        {k: b[k] for k in ('banka_adi', 'tur', 'rakip', 'dijital_only') if k in b}
        for b in catalog['banks']
    ]
    groups = catalog.get('groups', {}) or {}
    meta['groups'] = groups.get('members', {})
    meta['group_order'] = groups.get('order', list(meta['groups'].keys()))
    if groups.get('colors'):
        meta['group_colors'] = groups['colors']
    meta['dates'] = dates
    meta['total_periods'] = len(dates)

    ta = bank_data.get('toplam_aktifler', {})
    meta['bank_coverage'] = {
        b: sum(1 for v in ta.get(b, {}).values() if v is not None) for b in real
    }
    top20 = {}
    for d in dates:
        rows = [(b, ta.get(b, {}).get(d)) for b in real if ta.get(b, {}).get(d) is not None]
        rows.sort(key=lambda x: x[1], reverse=True)
        top20[d] = [b for b, _ in rows[:20]]
    meta['top20_by_date'] = top20

    meta['available_measures'] = [
        m['id'] for m in catalog['measures']
        if any(v is not None for b in real for v in bank_data.get(m['id'], {}).get(b, {}).values())
    ]
    if catalog.get('compositions'):
        meta['compositions'] = catalog['compositions']
    return meta


# ============================================================
# Üst seviye
# ============================================================

def build_payload(xlsx_path: Path | str, catalog: dict,
                  old_meta: Optional[dict] = None) -> Tuple[dict, dict]:
    """
    datatable xlsx → (computed.json payload, rapor)

    Rapor: {mapped, unmapped, agirliksiz_rasyolar, banks, dates, ...}
    """
    from datetime import datetime

    ctx = DatatableContext.from_xlsx(xlsx_path)
    mapping, unmapped = build_measure_map(catalog, ctx)
    bank_data = build_bank_data(ctx, catalog, mapping)
    group_data, agirliksiz, yaklasik = build_group_data(ctx, catalog, bank_data)
    composition_data, currency_data = build_composition_data(ctx, catalog)
    meta = build_meta(ctx, catalog, bank_data, old_meta)

    payload = {
        'meta': meta,
        'catalog': catalog['measures'],
        'bank_data': bank_data,
        'group_data': group_data,
        'composition_data': composition_data,
        'currency_data': currency_data,
        'timestamp': datetime.now().isoformat(),
        'source': 'datatable',
    }
    rapor = {
        'mapped': len(mapping),
        'unmapped': unmapped,
        'agirliksiz_rasyolar': agirliksiz,
        'yaklasik_agirlikli_rasyolar': yaklasik,
        'banks': len([b for b in (bb['banka_adi'] for bb in catalog['banks']) if b in set(ctx.banks)]),
        'dates': meta['dates'],
        'compositions': list(composition_data.keys()),
    }
    return payload, rapor
