"""
pipeline.composition
=====================
Kompozisyon (stacked-bar) ve döviz (TP/YP) dağılımı verisi üreticisi.

Frontend (index_v30.html) iki field okur:

  composition_data[compId][entityType][entity][tarih]
      = [ {id, value, pct}, ... ]            # her component için TL değer + yüzde

  currency_data[compId][entityType][entity][tarih]
      = { tp_value, yp_value, total_value, tp_pct, yp_pct }

  entityType: 'bank' | 'group'
  entity:     banka adı  |  grup adı (catalog.groups.members anahtarları)
  tarih:      'YYYY-MM-DD'

Component TL değerleri, ilgili measure'ları besleyen AYNI helper fonksiyonlarla
(pipeline.measures) ham parquet'ten hesaplanır; böylece segmentler measure'larla
birebir mutabık kalır. Component'ler her zaman 'Toplam' para biriminde toplanır;
TP/YP ayrımı yalnızca currency_data'da, kompozisyonun ana (toplam) kalemi üzerinden
2 segment (TP/YP) olarak verilir. Gelir tablosunda TP/YP raporlanmadığı için
gelir kompozisyonu currency desteklemez.
"""
from __future__ import annotations
from typing import Callable, Dict, List, Optional

from .lookup import LookupContext, krediler
from . import measures as M


# --------------------------------------------------------------------------
# Leasing kalem seçimi (kredi kompozisyonu)
# --------------------------------------------------------------------------
# 'Finansal Kiralama Alacakları'        → KT'de 0 (1 Mayıs modeli; leasing slice'ı boş,
#                                          leasing tutarı Tüzel residual'a yazılır)
# 'Kiralama İşlemlerinden Alacaklar'    → KT'de ~66.9 mlr (bilançodaki gerçek kiralama
#                                          alacakları; katılım bankalarında anlamlı slice)
# Tek satırlık değişiklikle iki tanım arasında geçiş yapılabilir.
LEASING_KALEM = 'Kiralama İşlemlerinden Alacaklar'


# --------------------------------------------------------------------------
# Component value fonksiyonları — hepsi (ctx, banka, tarih) -> float (TL, Toplam)
# --------------------------------------------------------------------------

def _nakit(ctx, b, t):
    v = ctx.bilanco(b, t, 'Nakit Değerler Ve Merkez Bankası (Üst Başlık)')
    if v == 0:
        v = ctx.bilanco(b, t, 'Nakit Değerler Ve Merkez Bankası')
    return v


def _net_kredi(ctx, b, t):
    # BZK zaten negatif depolanmış → toplama ile brütten düşülür
    return krediler(ctx, b, t) + ctx.bilanco(b, t, 'Beklenen Zarar Karşılıkları (-)')


def _alinan_kredi(ctx, b, t):
    return ctx.bilanco(b, t, 'Alınan Krediler')


def _diger_aktifler_pbi(ctx, b, t):
    """
    PowerBI referans tanımı (2026-08-12) — AÇIK kalem toplamı, RESIDUAL
    DEĞİL: Maddi Duran Varlıklar (Net) + Maddi Olmayan Duran Varlıklar
    (Net) + Yatırım Amaçlı Gayrimenkuller (Net) + Diğer Aktifler (bilanço
    kalemi) + Vergi Varlığı.

    ÖNEMLİ MİMARİ NOT: Bu fonksiyon kullanıldığında 'aktif' kompozisyonunun
    4 bileşeni (nakit+menkul+net_kredi+diger) ARTIK Toplam Aktifler'e TAM
    EŞİT OLMAYABİLİR — PowerBI'nin kendisi de böyle davranıyor (örn.
    "Bankalar", "İştirakler/Bağlı Ortaklıklar", "Kiralama İşlemlerinden
    Alacaklar" gibi kalemler ne bu listede ne diğer 3 bileşende yer alıyor,
    dolayısıyla küçük bir açıklanmamış fark kalabilir). Önceki (2026-08-11
    öncesi) implementasyon 'diger'i RESIDUAL (Total - diğer 3) olarak
    hesaplıyordu — bu, 4 bileşenin her zaman %100'e tamamlanmasını
    garantiliyordu ama PowerBI'nin gösterdiği sayılarla ÖRTÜŞMÜYORDU.
    """
    return (
        ctx.bilanco(b, t, 'Maddi Duran Varlıklar (Net)')
      + ctx.bilanco(b, t, 'Maddi Olmayan Duran Varlıklar (Net)')
      + ctx.bilanco(b, t, 'Yatırım Amaçlı Gayrimenkuller (Net)')
      + ctx.bilanco(b, t, 'Diğer Aktifler')
      + ctx.bilanco(b, t, 'Vergi Varlığı')
    )


def _diger_faaliyet_geliri_pbi(ctx, b, t):
    """PowerBI referans tanımı (2026-08-12): Temettü Gelirleri + Diğer
    Faaliyet Gelirleri (önceki implementasyonda Temettü Gelirleri eksikti)."""
    return (ctx.gelir(b, t, 'Temettü Gelirleri')
            + ctx.gelir(b, t, 'Diğer Faaliyet Gelirleri'))


def _dis_ticaret(ctx, b, t):
    toplam = 0.0
    for kat in ['İhracat Kredileri', 'İthalat Kredileri']:
        toplam += ctx.grup12(b, t, f'{kat},  Standart Nitelikli Krediler, Toplam')
        toplam += M._grup2_kategori(ctx, b, t, kat)
    return toplam


def _mali_kesim(ctx, b, t):
    return ctx.grup12(b, t, 'Mali Kesime Verilen Krediler,  Standart Nitelikli Krediler, Toplam')


def _leasing(ctx, b, t):
    return ctx.bilanco(b, t, LEASING_KALEM)


# --------------------------------------------------------------------------
# Kompozisyon tanımları
#   total_fn:    payda (yüzde için) — toplam kalem değeri
#   currency_kalemler: TP/YP toplamı için ham bilanço kalemleri (None → currency yok)
#                      (bu kalemlerin TP ve YP değerleri toplanır)
#   currency_krediler: True ise TP/YP, lookup.krediler(pb=) ile alınır (kredi komp.)
#   components:  [(component_id, value_fn ya da None=residual)]
#                value_fn None ise residual = total - (diğer componentler)
# --------------------------------------------------------------------------

def _aktif_total(ctx, b, t):
    return ctx.bilanco(b, t, 'Toplam Aktifler')


def _kaynak_total(ctx, b, t):
    return M.m_toplam_kaynak(ctx, b, t)


def _krediler_total(ctx, b, t):
    return krediler(ctx, b, t)


COMPOSITION_SPECS: Dict[str, dict] = {
    'aktif': {
        'total_fn': _aktif_total,
        'currency_kalemler': ['Toplam Aktifler'],
        'components': [
            ('nakit',     _nakit),
            ('menkul',    M._menkul_kiymetler),
            ('net_kredi', _net_kredi),
            # PowerBI referansı (2026-08-12): AÇIK kalem toplamı, residual
            # DEĞİL — bkz. _diger_aktifler_pbi docstring'i. 4 bileşen artık
            # Toplam Aktifler'e tam eşit olmayabilir (PowerBI'de de öyle).
            ('diger',     _diger_aktifler_pbi),
        ],
    },
    'pasif': {
        # PowerBI referansı (2026-08-12): residual'ın BAZI [Toplam Aktifler]
        # — [Toplam Pasifler] DEĞİL (iki kalem bilanço özdeşliği gereği
        # eşit olmalı ama PowerBI formülü açıkça Toplam Aktifler'i temel
        # alıyor, birebir hizalandı).
        'total_fn': _aktif_total,
        'currency_kalemler': ['Toplam Pasifler'],
        'components': [
            ('mevduat',         lambda c, b, t: c.bilanco(b, t, 'Mevduat')),
            # PowerBI referansı: 'Alınan Krediler' TEK BAŞINA ayrı bir
            # bileşen — önceki implementasyon bunu 'Para Piyasalarına
            # Borçlar' + 'İhraç Edilen Menkul Kıymetler (Net)' ile
            # birleştiriyordu ('mevduat_disi'). O iki kalem artık PowerBI
            # gibi residual'a ('diger') düşüyor.
            ('alinan_kredi',    _alinan_kredi),
            ('sermaye_benzeri', lambda c, b, t: c.bilanco(b, t, 'Sermaye Benzeri Krediler')),
            ('ozkaynak',        lambda c, b, t: c.bilanco(b, t, 'Özkaynaklar')),
            ('diger',           None),  # residual — PowerBI'de de residual (Diğer Pasifler formülü)
        ],
    },
    'kaynak': {
        'total_fn': _kaynak_total,
        # Toplam Kaynak tek kalem değil; TP/YP, 4 bileşenin TP/YP toplamıdır
        'currency_kalemler': ['Mevduat', 'Alınan Krediler',
                              'Para Piyasalarına Borçlar', 'İhraç Edilen Menkul Kıymetler (Net)'],
        'components': [
            ('mevduat',     lambda c, b, t: c.bilanco(b, t, 'Mevduat')),
            ('alinan_kredi', lambda c, b, t: c.bilanco(b, t, 'Alınan Krediler')),
            ('para_piyasa', lambda c, b, t: c.bilanco(b, t, 'Para Piyasalarına Borçlar')),
            ('ihrac',       lambda c, b, t: c.bilanco(b, t, 'İhraç Edilen Menkul Kıymetler (Net)')),
        ],
    },
    'kredi': {
        'total_fn': _krediler_total,
        'currency_krediler': True,   # TP/YP = krediler(pb='TP'/'YP')
        'components': [
            ('tuketici_kart', M.m_tuketici_kredileri),
            ('mali_kesim',    _mali_kesim),
            ('dis_ticaret',   _dis_ticaret),
            ('leasing',       _leasing),
            ('tuzel_diger',   None),  # residual
        ],
    },
    'gelir': {
        'total_fn': None,   # total = component toplamı
        'currency_kalemler': None,   # gelir tablosunda TP/YP yok
        'components': [
            ('net_faiz',       lambda c, b, t: c.gelir(b, t, 'Net Faiz Geliri/Gideri')),
            ('net_komisyon',   lambda c, b, t: c.gelir(b, t, 'Net Ücret Ve Komisyon Gelirleri/Giderleri')),
            ('net_ticari',     lambda c, b, t: c.gelir(b, t, 'Ticari Kar/Zarar (Net)')),
            # PowerBI referansı (2026-08-12): Temettü Gelirleri + Diğer
            # Faaliyet Gelirleri — önceki implementasyonda Temettü
            # Gelirleri eksikti.
            ('diger_faaliyet', _diger_faaliyet_geliri_pbi),
        ],
    },
}


# --------------------------------------------------------------------------
# Çekirdek hesaplama
# --------------------------------------------------------------------------

def _component_values(ctx, banka, tarih, spec) -> Optional[Dict[str, float]]:
    """Bir banka×tarih için tüm componentlerin TL değerini hesaplar.

    Dönüş: {component_id: value} veya None (anlamlı veri yoksa).
    Residual (value_fn=None) total - diğerleri olarak hesaplanır.
    """
    comps = spec['components']

    # Önce non-residual componentler
    vals: Dict[str, float] = {}
    for cid, fn in comps:
        if fn is None:
            continue
        vals[cid] = float(fn(ctx, banka, tarih) or 0.0)

    # Total
    if spec.get('total_fn') is not None:
        total = float(spec['total_fn'](ctx, banka, tarih) or 0.0)
    else:
        total = sum(vals.values())   # gelir: componentlerin toplamı

    # Anlamlı veri yoksa atla
    if total is None or abs(total) < 1.0:
        return None
    if all(abs(v) < 1.0 for v in vals.values()):
        return None

    # Residual component(ler)i
    for cid, fn in comps:
        if fn is None:
            vals[cid] = total - sum(v for k, v in vals.items())

    vals['__total__'] = total
    return vals


def _currency_values(ctx, banka, tarih, spec) -> Optional[Dict[str, float]]:
    """TP/YP toplamı. Dönüş: {tp, yp, total} veya None."""
    if spec.get('currency_krediler'):
        tp = float(krediler(ctx, banka, tarih, 'TP') or 0.0)
        yp = float(krediler(ctx, banka, tarih, 'YP') or 0.0)
    else:
        kalemler = spec.get('currency_kalemler')
        if not kalemler:
            return None
        tp = sum(float(ctx.bilanco(banka, tarih, k, 'TP') or 0.0) for k in kalemler)
        yp = sum(float(ctx.bilanco(banka, tarih, k, 'YP') or 0.0) for k in kalemler)
    total = tp + yp
    if abs(total) < 1.0:
        return None
    return {'tp': tp, 'yp': yp, 'total': total}


def _to_comp_list(vals: Dict[str, float], spec) -> List[dict]:
    """
    {component_id: value} → frontend [{id, value, pct}] (catalog component sırasıyla).

    PowerBI referansı (2026-08-12, kullanıcı doğruladı): yüzdeler MUTLAK
    DEĞERLERE göre hesaplanır — payda = Σ|component_i|, pay = |component_i|
    — böylece bileşenler HER ZAMAN tam %100'e tamamlanır. Bu, hem 'aktif'
    kompozisyonundaki (artık residual olmayan, bkz. _diger_aktifler_pbi)
    açıklanmamış küçük farkı hem de 'gelir' kompozisyonundaki negatif
    kalemleri (ör. zarar eden bir dönemde net_ticari < 0) aynı şekilde ele
    alır: negatif bir kalem kendi BÜYÜKLÜĞÜ kadar bir dilim kaplar (payda
    ve pay ikisi de mutlak değer), 'value' alanı (TL) ise İŞARETLİ kalır —
    frontend negatif olduğunu value'dan anlayıp ayrıca işaretleyebilir.
    Gerçek Toplam Aktifler/Pasifler (`vals['__total__']`) BURADA
    KULLANILMIYOR — sadece component'lerin kendi (mutlak) toplamı esas alınır.
    """
    abs_total = sum(abs(vals.get(cid, 0.0)) for cid, _ in spec['components'])
    out = []
    for cid, _ in spec['components']:
        v = vals.get(cid, 0.0)
        pct = (abs(v) / abs_total * 100.0) if abs_total else 0.0
        out.append({'id': cid, 'value': v, 'pct': pct})
    return out


def _agg_component_values(ctx, members, tarih, spec) -> Optional[Dict[str, float]]:
    """Grup: üye bankaların component değerlerini topla, sonra residual + total."""
    comps = spec['components']
    agg: Dict[str, float] = {}
    total = 0.0
    any_data = False
    for cid, fn in comps:
        if fn is None:
            continue
        s = 0.0
        for b in members:
            s += float(fn(ctx, b, tarih) or 0.0)
        agg[cid] = s

    if spec.get('total_fn') is not None:
        for b in members:
            tv = float(spec['total_fn'](ctx, b, tarih) or 0.0)
            total += tv
            if abs(tv) >= 1.0:
                any_data = True
    else:
        total = sum(agg.values())
        any_data = any(abs(v) >= 1.0 for v in agg.values())

    if not any_data or abs(total) < 1.0:
        return None

    for cid, fn in comps:
        if fn is None:
            agg[cid] = total - sum(v for k, v in agg.items())
    agg['__total__'] = total
    return agg


def _agg_currency_values(ctx, members, tarih, spec) -> Optional[Dict[str, float]]:
    if spec.get('currency_krediler'):
        tp = sum(float(krediler(ctx, b, tarih, 'TP') or 0.0) for b in members)
        yp = sum(float(krediler(ctx, b, tarih, 'YP') or 0.0) for b in members)
    else:
        kalemler = spec.get('currency_kalemler')
        if not kalemler:
            return None
        tp = sum(float(ctx.bilanco(b, tarih, k, 'TP') or 0.0) for b in members for k in kalemler)
        yp = sum(float(ctx.bilanco(b, tarih, k, 'YP') or 0.0) for b in members for k in kalemler)
    total = tp + yp
    if abs(total) < 1.0:
        return None
    return {'tp': tp, 'yp': yp, 'total': total}


def _currency_record(cv: Dict[str, float]) -> dict:
    total = cv['total']
    return {
        'tp_value': cv['tp'], 'yp_value': cv['yp'], 'total_value': total,
        'tp_pct': (cv['tp'] / total * 100.0) if total else 0.0,
        'yp_pct': (cv['yp'] / total * 100.0) if total else 0.0,
    }


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def build_composition_payload(ctx: LookupContext, catalog) -> tuple:
    """composition_data ve currency_data sözlüklerini üretir.

    catalog: {'banks': [...], 'groups': {'members': {...}}, 'compositions': {...}}
    Dönüş: (composition_data, currency_data)
    """
    if isinstance(catalog, dict):
        banks = [b['banka_adi'] for b in catalog.get('banks', [])]
        group_members = (catalog.get('groups', {}) or {}).get('members', {}) or {}
    else:
        banks, group_members = [], {}

    composition_data: Dict[str, dict] = {}
    currency_data: Dict[str, dict] = {}

    # Banka tarihleri
    bank_dates = {b: [str(d.strftime('%Y-%m-%d')) for d in ctx.get_dates(b)] for b in banks}
    import pandas as pd

    for cid, spec in COMPOSITION_SPECS.items():
        composition_data[cid] = {'bank': {}, 'group': {}}
        has_currency = spec.get('currency_krediler') or spec.get('currency_kalemler')
        if has_currency:
            currency_data[cid] = {'bank': {}, 'group': {}}

        # --- Bankalar ---
        for b in banks:
            for ds in bank_dates.get(b, []):
                t = pd.Timestamp(ds)
                cv = _component_values(ctx, b, t, spec)
                if cv is not None:
                    composition_data[cid]['bank'].setdefault(b, {})[ds] = _to_comp_list(cv, spec)
                if has_currency:
                    curv = _currency_values(ctx, b, t, spec)
                    if curv is not None:
                        currency_data[cid]['bank'].setdefault(b, {})[ds] = _currency_record(curv)

        # --- Gruplar ---
        for gname, members in group_members.items():
            if not members:
                continue
            # üye tarihlerinin birleşimi
            all_ds = sorted({ds for m in members for ds in bank_dates.get(m, [])})
            for ds in all_ds:
                t = pd.Timestamp(ds)
                cv = _agg_component_values(ctx, members, t, spec)
                if cv is not None:
                    composition_data[cid]['group'].setdefault(gname, {})[ds] = _to_comp_list(cv, spec)
                if has_currency:
                    curv = _agg_currency_values(ctx, members, t, spec)
                    if curv is not None:
                        currency_data[cid]['group'].setdefault(gname, {})[ds] = _currency_record(curv)

    return composition_data, currency_data
