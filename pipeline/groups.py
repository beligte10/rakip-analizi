"""
pipeline.groups
================
Banka değerlerinden grup değerleri (Kuveyt Türk, Mevduat Bankaları, Rakip
Bankalar, Katılım Bankaları, KT Hariç Katılım Bankaları) hesaplar.

Toplama mantığı measure tipine göre:
- Büyüklük (TL veya adet)  → SUM (üye banka değerlerinin toplamı)
- Stok rasyo                → Ağırlıklı ortalama: Σnumerator / Σdenominator × 100
- Akım/TTM rasyo            → Numerator (TTM toplam) / Denominator (avg balance)
- Spread/farklar            → Basit ortalama
- Şube/Personel başına      → Σtoplam_değer / Σbölücü / scale

Her rasyo measure'ı için pay/payda fonksiyonu `RATIO_NUM_DEN`
sözlüğünde tanımlı. Tek giriş noktası `build_group_data()` — üye
bankaların pay/payda değerlerini toplar, sonra bölme yapar. Bu modülde
grup hesaplamak için tek fonksiyon budur (bkz. `build_group_data`
docstring'i — önceden var olan ikinci, kullanılmayan implementasyon
kaldırıldı).
"""
from __future__ import annotations
from typing import Callable, Dict, List, Optional, Tuple

from .lookup import (
    LookupContext, krediler, faiz_getirili_aktif, maliyetli_pasif,
    ttm_flow, avg_balance,
)
from .measures import (
    m_konut_kredileri, m_tasit_kredileri, m_ihtiyac_kredileri,
    m_bireysel_kredi_kartlari, m_tuketici_kredileri, m_tuzel_krediler,
    m_grup_1_krediler, m_grup_2_krediler, m_toplam_kaynak,
    m_vadeli_mevduat, m_toplam_fonlama,
    _grup2_kategori, _aktiften_silinen, _menkul_kiymetler,
    toplam_krediler_net_leasing, tuketici_kredileri_kk_haric,
    _diger_aktifler_kompozit,
    _brut_krediler, _NPL_INTIKAL_ITEMS, _NPL_TAHSILAT_ITEMS,
    _KUR_KREDI_USD, _KUR_KREDI_EURO, _KUR_KREDI_TOPLAM,
    _faiz_getirili_aktif_detay,
    _faiz_maliyetli_pasif_detay,
    _yp_net_genel_pozisyon,
    _kredi_riski, _piyasa_riski, _operasyonel_risk,
    _LIKIDITE_ACIGI_KALEM, _birikimli_vadeli_mevduat,
)


NumDenFn = Callable[[LookupContext, str, str], Tuple[Optional[float], Optional[float]]]


# ============================================================
# Pay/payda formülleri — her rasyo için (banka bazlı num, den)
# ============================================================

# --- Bilanço basit rasyolar ---
def _nd_npl(ctx, b, t):
    return ctx.bilanco(b, t, 'Donuk Alacaklar'), krediler(ctx, b, t)


def _nd_npl_formasyonu(ctx, b, t):
    """Grup agregasyonu: Σ(net oluşum) / Σ(ort. brüt kredi). measures.m_npl_formasyonu
    ile aynı taban; _agg_ratio paylar/paydaları ayrı toplar."""
    net_olusum = (
        sum(ctx.donuk_akim(b, t, k) for k in _NPL_INTIKAL_ITEMS)
        + sum(ctx.donuk_akim(b, t, k) for k in _NPL_TAHSILAT_ITEMS)
    )
    ort_brut = avg_balance(ctx, b, t, lambda bb, tt: _brut_krediler(ctx, bb, tt))
    return net_olusum, ort_brut


def _nd_npl_satis_terkin(ctx, b, t):
    silinen_abs = abs(_aktiften_silinen(ctx, b, t))
    return (
        ctx.bilanco(b, t, 'Donuk Alacaklar') + silinen_abs,
        krediler(ctx, b, t) + silinen_abs,
    )


def _nd_npl_karsilama(ctx, b, t):
    bzk = abs(ctx.bilanco(b, t, 'Beklenen Zarar Karşılıkları (-)'))
    return bzk, ctx.bilanco(b, t, 'Donuk Alacaklar')


def _nd_krediler_ta(ctx, b, t):
    return krediler(ctx, b, t), ctx.bilanco(b, t, 'Toplam Aktifler')


def _nd_diger_aktifler_ta(ctx, b, t):
    return _diger_aktifler_kompozit(ctx, b, t), ctx.bilanco(b, t, 'Toplam Aktifler')


def _nd_finansal_varliklar(ctx, b, t):
    fv = (ctx.bilanco(b, t, 'Finansal Varlıklar (Net)')
        + ctx.bilanco(b, t, 'İtfa Edilmiş Maliyeti ile Ölçülen Finansal Varlıklar'))
    return fv, ctx.bilanco(b, t, 'Toplam Aktifler')


def _nd_menkul_kiymetler(ctx, b, t):
    return _menkul_kiymetler(ctx, b, t), ctx.bilanco(b, t, 'Toplam Aktifler')


def _nd_ortaklik_yatirimlari(ctx, b, t):
    return ctx.bilanco(b, t, 'Ortaklık Yatırımları'), ctx.bilanco(b, t, 'Toplam Aktifler')


def _nd_faiz_getirili_ta(ctx, b, t):
    return _faiz_getirili_aktif_detay(ctx, b, t), ctx.bilanco(b, t, 'Toplam Aktifler')


def _nd_faiz_getirili_maliyetli(ctx, b, t):
    # DAX birebir: pay 13-bileşen IEA detay, payda 9-bileşen maliyetli pasif detay.
    return _faiz_getirili_aktif_detay(ctx, b, t), _faiz_maliyetli_pasif_detay(ctx, b, t)


def _nd_faiz_getirili_ozkaynak(ctx, b, t):
    # Ortalama IEA detay / Ortalama Özkaynaklar (kat). avg_balance — PARALLELPERIOD
    # DEĞİL (handover GT#1). Grup: Σ(avg IEA)/Σ(avg Özk) × scale(=1).
    num = avg_balance(ctx, b, t, lambda bb, tt: _faiz_getirili_aktif_detay(ctx, bb, tt))
    den = avg_balance(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Özkaynaklar'))
    return num, den


def _nd_tp_aktifler_ta(ctx, b, t):
    return ctx.bilanco(b, t, 'Toplam Aktifler', 'TP'), ctx.bilanco(b, t, 'Toplam Aktifler')


def _nd_yp_aktifler_pasifler(ctx, b, t):
    return ctx.bilanco(b, t, 'Toplam Aktifler', 'YP'), ctx.bilanco(b, t, 'Toplam Pasifler', 'YP')


def _nd_grup1_toplam(ctx, b, t):
    # 2026-08-14: payda Toplam Brüt Krediler (banka m_grup_1_krediler_toplam ile hizalı)
    return m_grup_1_krediler(ctx, b, t), _brut_krediler(ctx, b, t)


def _nd_grup2_toplam(ctx, b, t):
    return m_grup_2_krediler(ctx, b, t), toplam_krediler_net_leasing(ctx, b, t)


def _nd_grup2_cekirdek(ctx, b, t):
    return m_grup_2_krediler(ctx, b, t), ctx.sermaye(b, t, 'Çekirdek Sermaye Toplamı')


def _nd_usd_yp(ctx, b, t):
    return ctx.kur_konsolide(b, t, _KUR_KREDI_USD), ctx.kur_konsolide(b, t, _KUR_KREDI_TOPLAM)


def _nd_euro_yp(ctx, b, t):
    return ctx.kur_konsolide(b, t, _KUR_KREDI_EURO), ctx.kur_konsolide(b, t, _KUR_KREDI_TOPLAM)


def _nd_yp_net_pozisyon_ozkaynak(ctx, b, t):
    # Net Genel Pozisyon (Bilanço+Nazım, ±) / Toplam Ozkaynaklar (regülasyon özk.).
    return _yp_net_genel_pozisyon(ctx, b, t), ctx.ozkaynak_detay(b, t, 'Toplam Ozkaynaklar')


def _nd_grup2_tuketici(ctx, b, t):
    g2_tuk = _grup2_kategori(ctx, b, t, 'Tüketici Kredileri')
    return g2_tuk, tuketici_kredileri_kk_haric(ctx, b, t)


def _nd_grup2_tuzel(ctx, b, t):
    g2_total = m_grup_2_krediler(ctx, b, t)
    g2_kart = _grup2_kategori(ctx, b, t, 'Kredi Kartları')
    g2_tuk = _grup2_kategori(ctx, b, t, 'Tüketici Kredileri')
    g2_mali = _grup2_kategori(ctx, b, t, 'Mali Kesime Verilen Krediler')
    return g2_total - g2_kart - g2_tuk - g2_mali, m_tuzel_krediler(ctx, b, t)


def _nd_konut_tuketici(ctx, b, t):
    return m_konut_kredileri(ctx, b, t), m_tuketici_kredileri(ctx, b, t)


def _nd_tasit_tuketici(ctx, b, t):
    return m_tasit_kredileri(ctx, b, t), m_tuketici_kredileri(ctx, b, t)


def _nd_ihtiyac_toplam(ctx, b, t):
    return m_ihtiyac_kredileri(ctx, b, t), _brut_krediler(ctx, b, t)


def _nd_konut_tp_pasifler(ctx, b, t):
    den = ctx.bilanco(b, t, 'Toplam Pasifler', 'TP') - ctx.bilanco(b, t, 'Özkaynaklar', 'TP')
    return m_konut_kredileri(ctx, b, t), den


def _nd_bkk_toplam(ctx, b, t):
    return m_bireysel_kredi_kartlari(ctx, b, t), _brut_krediler(ctx, b, t)


def _nd_tuketici_toplam(ctx, b, t):
    return m_tuketici_kredileri(ctx, b, t), _brut_krediler(ctx, b, t)


def _nd_tuzel_toplam(ctx, b, t):
    return m_tuzel_krediler(ctx, b, t), _brut_krediler(ctx, b, t)


def _nd_dis_ticaret(ctx, b, t):
    toplam = 0.0
    for kategori in ['İhracat Kredileri', 'İthalat Kredileri']:
        toplam += ctx.grup12(b, t, f'{kategori},  Standart Nitelikli Krediler, Toplam')
        toplam += _grup2_kategori(ctx, b, t, kategori)
    return toplam, _brut_krediler(ctx, b, t)


def _nd_mali_kesim(ctx, b, t):
    mk = ctx.grup12(b, t, 'Mali Kesime Verilen Krediler,  Standart Nitelikli Krediler, Toplam')
    return mk, _brut_krediler(ctx, b, t)


def _nd_tp_krediler_toplam(ctx, b, t):
    # 2026-08-14: TP Brüt Krediler / Toplam Brüt Krediler (banka ile hizalı)
    return _brut_krediler(ctx, b, t, 'TP'), _brut_krediler(ctx, b, t)


# --- Pasif basit ---
def _nd_krediler_mevduat(ctx, b, t):
    return krediler(ctx, b, t), ctx.bilanco(b, t, 'Mevduat')


def _nd_vadesiz_mevduat_mev(ctx, b, t):
    return ctx.vadesiz_mevduat(b, t), ctx.bilanco(b, t, 'Mevduat')


def _nd_tp_mevduat(ctx, b, t):
    return ctx.bilanco(b, t, 'Mevduat', 'TP'), ctx.bilanco(b, t, 'Mevduat')


# --- Akım/TTM rasyolar ---
def _nd_roaa(ctx, b, t):
    nk = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Dönem Karı / Zararı'))
    avg_ta = avg_balance(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Toplam Aktifler'))
    return nk, avg_ta


def _nd_roae(ctx, b, t):
    nk = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Dönem Karı / Zararı'))
    avg_oz = avg_balance(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Özkaynaklar'))
    return nk, avg_oz


def _nd_nim(ctx, b, t):
    nfg = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Faiz Geliri/Gideri'))
    avg_iea = avg_balance(ctx, b, t, lambda bb, tt: faiz_getirili_aktif(ctx, bb, tt))
    return nfg, avg_iea


def _nd_nim_bzk_sonrasi(ctx, b, t):
    def f(bb, tt):
        return (ctx.gelir(bb, tt, 'Net Faiz Geliri/Gideri')
              - ctx.gelir(bb, tt, 'Kredi Ve Diğer Alacaklar Değer Düşüş Karşılığı (-)'))
    nfg = ttm_flow(ctx, b, t, f)
    avg_iea = avg_balance(ctx, b, t, lambda bb, tt: faiz_getirili_aktif(ctx, bb, tt))
    return nfg, avg_iea


def _nd_iea_getiri(ctx, b, t):
    fg = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Faiz Gelirleri'))
    avg_iea = avg_balance(ctx, b, t, lambda bb, tt: faiz_getirili_aktif(ctx, bb, tt))
    return fg, avg_iea


def _nd_mp_maliyet(ctx, b, t):
    fgd = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Faiz Giderleri'))
    avg_mp = avg_balance(ctx, b, t, lambda bb, tt: maliyetli_pasif(ctx, bb, tt))
    return fgd, avg_mp


def _nd_faiz_gid_gel(ctx, b, t):
    fgd = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Faiz Giderleri'))
    fg = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Faiz Gelirleri'))
    return fgd, fg


def _nd_faaliyet_aktif(ctx, b, t):
    g = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Diğer Faaliyet Giderleri (-)'))
    avg_ta = avg_balance(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Toplam Aktifler'))
    return g, avg_ta


def _nd_personel_aktif(ctx, b, t):
    g = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Personel Giderleri (-)'))
    avg_ta = avg_balance(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Toplam Aktifler'))
    return g, avg_ta


def _nd_reklam_aktif(ctx, b, t):
    g = ttm_flow(ctx, b, t, lambda bb, tt: ctx.faaliyet_gid_detay(bb, tt, 'Reklam ve İlan Giderleri'))
    avg_ta = avg_balance(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Toplam Aktifler'))
    return g, avg_ta


def _nd_personel_kar(ctx, b, t):
    pg = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Personel Giderleri (-)'))
    nk = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Dönem Karı / Zararı'))
    return pg, nk


def _nd_reklam_kar(ctx, b, t):
    rg = ttm_flow(ctx, b, t, lambda bb, tt: ctx.faaliyet_gid_detay(bb, tt, 'Reklam ve İlan Giderleri'))
    nk = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Dönem Karı / Zararı'))
    return rg, nk


def _nd_net_ucret_aktif(ctx, b, t):
    nuk = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Ücret Ve Komisyon Gelirleri/Giderleri'))
    avg_ta = avg_balance(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Toplam Aktifler'))
    return nuk, avg_ta


def _nd_net_ucret_op(ctx, b, t):
    nuk = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Ücret Ve Komisyon Gelirleri/Giderleri'))
    fg = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Diğer Faaliyet Giderleri (-)'))
    return nuk, fg


def _nd_komisyon_gid_gel(ctx, b, t):
    vk = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Verilen Ücret Ve Komisyonlar'))
    ak = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Alınan Ücret Ve Komisyonlar'))
    return vk, ak


def _nd_maliyet_gelir(ctx, b, t):
    def maliyet(bb, tt):
        return (ctx.gelir(bb, tt, 'Diğer Faaliyet Giderleri (-)')
              + ctx.gelir(bb, tt, 'Personel Giderleri (-)'))
    def gelir(bb, tt):
        return (ctx.gelir(bb, tt, 'Net Faiz Geliri/Gideri')
              + ctx.gelir(bb, tt, 'Net Ücret Ve Komisyon Gelirleri/Giderleri')
              + ctx.gelir(bb, tt, 'Ticari Kar/Zarar (Net)'))
    return ttm_flow(ctx, b, t, maliyet), ttm_flow(ctx, b, t, gelir)


def _nd_kredi_pacal(ctx, b, t):
    fg = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Kredilerden Alınan Faizler'))
    avg_kred = avg_balance(ctx, b, t, lambda bb, tt: krediler(ctx, bb, tt))
    return fg, avg_kred


def _nd_cost_of_risk(ctx, b, t):
    cr = ttm_flow(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Kredi Ve Diğer Alacaklar Değer Düşüş Karşılığı (-)'))
    avg_kred = avg_balance(ctx, b, t, lambda bb, tt: krediler(ctx, bb, tt))
    return cr, avg_kred


def _nd_donuk_intikal(ctx, b, t):
    # DAX birebir: Σ İntikal (5 kalem, YtD) / ort. brüt kredi (5 bileşen).
    intikal = sum(ctx.donuk_akim(b, t, k) for k in _NPL_INTIKAL_ITEMS)
    ort_brut = avg_balance(ctx, b, t, lambda bb, tt: _brut_krediler(ctx, bb, tt))
    return intikal, ort_brut


def _nd_donuk_tahsilat(ctx, b, t):
    # DAX birebir: Σ Tahsilat (5 kalem, YtD, ham negatif) / ort. brüt kredi.
    # *-1 konvansiyonu için payı pozitife çeviriyoruz (Σnum/Σden pozitif çıksın).
    tahsilat = sum(ctx.donuk_akim(b, t, k) for k in _NPL_TAHSILAT_ITEMS)
    ort_brut = avg_balance(ctx, b, t, lambda bb, tt: _brut_krediler(ctx, bb, tt))
    return -tahsilat, ort_brut


# --- Pasif yeni 21 measure ---
def _nd_alinan_iemk(ctx, b, t):
    num = (ctx.bilanco(b, t, 'Alınan Krediler')
         + ctx.bilanco(b, t, 'İhraç Edilen Menkul Kıymetler (Net)'))
    return num, m_toplam_kaynak(ctx, b, t)


def _nd_tp_alinan(ctx, b, t):
    return ctx.bilanco(b, t, 'Alınan Krediler', 'TP'), ctx.bilanco(b, t, 'Alınan Krediler')


def _nd_tuzel_kred_mev(ctx, b, t):
    return m_tuzel_krediler(ctx, b, t), ctx.tuzel_mevduat(b, t)


def _nd_kred_altindisi_mev(ctx, b, t):
    den = ctx.bilanco(b, t, 'Mevduat') - ctx.kiymetli_maden(b, t)
    return krediler(ctx, b, t), den


def _nd_kred_kaynak(ctx, b, t):
    # 2026-08-14: pay Toplam Brüt Krediler (banka m_krediler_toplam_kaynak ile hizalı)
    return _brut_krediler(ctx, b, t), m_toplam_kaynak(ctx, b, t)


def _nd_tp_kred_kaynak(ctx, b, t):
    # 2026-08-15: 'Kaynak' tanımı m_toplam_kaynak ile hizalandı (Para Piyasalarına
    # Borçlar çıkarıldı) — banka m_tp_krediler_tp_kaynak ile tutarlı (2026-08-12 fix).
    pay = krediler(ctx, b, t, 'TP')
    den = (ctx.bilanco(b, t, 'Mevduat', 'TP')
         + ctx.bilanco(b, t, 'Alınan Krediler', 'TP')
         + ctx.bilanco(b, t, 'İhraç Edilen Menkul Kıymetler (Net)', 'TP'))
    return pay, den


def _nd_yp_kred_altindisi(ctx, b, t):
    # 2026-08-15: Para Piyasalarına Borçlar çıkarıldı (banka m_yp_krediler_yp_altindisi_kaynak ile hizalı)
    pay = krediler(ctx, b, t, 'YP')
    yp_kaynak = (ctx.bilanco(b, t, 'Mevduat', 'YP')
               + ctx.bilanco(b, t, 'Alınan Krediler', 'YP')
               + ctx.bilanco(b, t, 'İhraç Edilen Menkul Kıymetler (Net)', 'YP'))
    return pay, yp_kaynak - ctx.kiymetli_maden(b, t)


def _nd_vadesiz_kaynak(ctx, b, t):
    return ctx.vadesiz_mevduat(b, t), m_toplam_kaynak(ctx, b, t)


def _nd_tp_mevduat_altindisi(ctx, b, t):
    den = ctx.bilanco(b, t, 'Mevduat') - ctx.kiymetli_maden(b, t)
    return ctx.bilanco(b, t, 'Mevduat', 'TP'), den


def _nd_tp_kaynak(ctx, b, t):
    # 2026-08-15: Para Piyasalarına Borçlar çıkarıldı (banka m_tp_kaynak_toplam_kaynak ile hizalı)
    tp_kaynak = (ctx.bilanco(b, t, 'Mevduat', 'TP')
               + ctx.bilanco(b, t, 'Alınan Krediler', 'TP')
               + ctx.bilanco(b, t, 'İhraç Edilen Menkul Kıymetler (Net)', 'TP'))
    return tp_kaynak, m_toplam_kaynak(ctx, b, t)


def _nd_kaynak_pasifler(ctx, b, t):
    return m_toplam_kaynak(ctx, b, t), ctx.bilanco(b, t, 'Toplam Pasifler')


def _nd_tp_pasifler_oz_haric(ctx, b, t):
    pay = ctx.bilanco(b, t, 'Toplam Pasifler', 'TP')
    den = ctx.bilanco(b, t, 'Toplam Pasifler') - ctx.bilanco(b, t, 'Özkaynaklar')
    return pay, den


def _nd_sermaye_benzeri(ctx, b, t):
    return ctx.bilanco(b, t, 'Sermaye Benzeri Krediler'), ctx.bilanco(b, t, 'Toplam Pasifler')


def _nd_ppb(ctx, b, t):
    return ctx.bilanco(b, t, 'Para Piyasalarına Borçlar'), ctx.bilanco(b, t, 'Toplam Pasifler')


def _nd_maliyetli_pasif(ctx, b, t):
    # DAX birebir: 9 bileşen (vadesiz hariç). measures._faiz_maliyetli_pasif_detay.
    return _faiz_maliyetli_pasif_detay(ctx, b, t), ctx.bilanco(b, t, 'Toplam Pasifler')


def _nd_serbest_sermaye(ctx, b, t):
    serbest = (ctx.bilanco(b, t, 'Özkaynaklar')
             - ctx.bilanco(b, t, 'Ortaklık Yatırımları')
             - ctx.bilanco(b, t, 'Maddi Duran Varlıklar (Net)')
             - ctx.bilanco(b, t, 'Maddi Olmayan Duran Varlıklar (Net)'))
    return serbest, ctx.bilanco(b, t, 'Toplam Aktifler')


# --- 2026-08-14 measures.docx yeni 20 rasyo — grup ağırlıklı agregasyon ---
def _nd_kredi_riski_toplam_risk(ctx, b, t):
    return _kredi_riski(ctx, b, t), _piyasa_riski(ctx, b, t) + _operasyonel_risk(ctx, b, t) + _kredi_riski(ctx, b, t)


def _nd_piyasa_riski_toplam_risk(ctx, b, t):
    return _piyasa_riski(ctx, b, t), _piyasa_riski(ctx, b, t) + _operasyonel_risk(ctx, b, t) + _kredi_riski(ctx, b, t)


def _nd_operasyonel_risk_toplam_risk(ctx, b, t):
    return _operasyonel_risk(ctx, b, t), _piyasa_riski(ctx, b, t) + _operasyonel_risk(ctx, b, t) + _kredi_riski(ctx, b, t)


def _nd_brut_krediler_ta(ctx, b, t):
    return _brut_krediler(ctx, b, t), ctx.bilanco(b, t, 'Toplam Aktifler')


def _nd_bankalar_ta(ctx, b, t):
    return ctx.bilanco(b, t, 'Bankalar'), ctx.bilanco(b, t, 'Toplam Aktifler')


def _nd_nakit_degerler_ta(ctx, b, t):
    return ctx.bilanco(b, t, 'Nakit Değerler Ve Merkez Bankası'), ctx.bilanco(b, t, 'Toplam Aktifler')


def _nd_yp_krediler_toplam(ctx, b, t):
    return _brut_krediler(ctx, b, t, 'YP'), _brut_krediler(ctx, b, t)


def _nd_birikimli_vadeli(ctx, b, t):
    return _birikimli_vadeli_mevduat(ctx, b, t), m_vadeli_mevduat(ctx, b, t)


def _nd_resmi_kurumlar_mev(ctx, b, t):
    return ctx.resmi_kurumlar(b, t), ctx.bilanco(b, t, 'Mevduat')


def _nd_toplam_fonlama_mp(ctx, b, t):
    return m_toplam_fonlama(ctx, b, t), _faiz_maliyetli_pasif_detay(ctx, b, t)


def _nd_tuzel_mevduat_mev(ctx, b, t):
    return ctx.tuzel_mevduat(b, t), ctx.bilanco(b, t, 'Mevduat')


def _nd_alinan_krediler_toplam_pasifler(ctx, b, t):
    return ctx.bilanco(b, t, 'Alınan Krediler'), ctx.bilanco(b, t, 'Toplam Pasifler')


# Likidite Açığı vade dilimleri (7) — num = kalan_vade kalem, den = Toplam Aktifler.
def _make_nd_likidite(kalem):
    def fn(ctx, b, t):
        return ctx.kalan_vade(b, t, kalem), ctx.bilanco(b, t, 'Toplam Aktifler')
    return fn


# Vadeli mevduat vade dilimleri (4) — num = mvy dilim, den = Vadeli Mevduat.
# NOT: mvy tablosu (konvansiyonel) — katılım bankalarında num=0 (banka seviyesiyle
# aynı sınır; _LIKIDITE_ACIGI_KALEM notuna paralel).
_VADELI_DILIM_KALEM = {
    'vadeli_1ay_toplam_vadeli': 'Toplam, 1 Aya Kadar',
    'vadeli_1_3ay_toplam_vadeli': 'Toplam, 1-3 Ay',
    'vadeli_3_6ay_toplam_vadeli': 'Toplam, 3-6 Ay',
    'vadeli_6_12ay_toplam_vadeli': 'Toplam, 6 Ay-1 Yıl',
}


def _make_nd_vadeli(kalem):
    def fn(ctx, b, t):
        return ctx.mvy(b, t, kalem), m_vadeli_mevduat(ctx, b, t)
    return fn


# Map: measure_id → (num, den) fonksiyonu
RATIO_NUM_DEN: Dict[str, NumDenFn] = {
    # Bilanço basit
    'npl_rasyosu': _nd_npl,
    'npl_formasyonu': _nd_npl_formasyonu,
    'npl_rasyosu_satis_terkin_oncesi': _nd_npl_satis_terkin,
    'npl_karsilama_orani': _nd_npl_karsilama,
    'krediler_ta': _nd_krediler_ta,
    'diger_aktifler_ta': _nd_diger_aktifler_ta,
    'finansal_varliklar_net_ta': _nd_finansal_varliklar,
    'menkul_kiymetler_ta': _nd_menkul_kiymetler,
    'ortaklik_yatirimlari_ta': _nd_ortaklik_yatirimlari,
    'faiz_getirili_ta': _nd_faiz_getirili_ta,
    'faiz_getirili_maliyetli': _nd_faiz_getirili_maliyetli,
    'faiz_getirili_ozkaynak': _nd_faiz_getirili_ozkaynak,
    'tp_aktifler_ta': _nd_tp_aktifler_ta,
    'yp_aktifler_toplam_pasifler': _nd_yp_aktifler_pasifler,
    'grup_1_krediler_toplam': _nd_grup1_toplam,
    'grup_2_krediler_toplam': _nd_grup2_toplam,
    'grup_2_krediler_cekirdek_sermaye': _nd_grup2_cekirdek,
    'usd_yp_krediler': _nd_usd_yp,
    'euro_yp_krediler': _nd_euro_yp,
    'yp_net_pozisyon_ozkaynak': _nd_yp_net_pozisyon_ozkaynak,
    'grup_2_tuketici_tuketici': _nd_grup2_tuketici,
    'grup_2_tuzel_tuzel': _nd_grup2_tuzel,
    'konut_tuketici': _nd_konut_tuketici,
    'tasit_tuketici': _nd_tasit_tuketici,
    'ihtiyac_toplam': _nd_ihtiyac_toplam,
    'konut_tp_pasifler': _nd_konut_tp_pasifler,
    'bkk_toplam': _nd_bkk_toplam,
    'tuketici_toplam': _nd_tuketici_toplam,
    'tuzel_toplam': _nd_tuzel_toplam,
    'dis_ticaret_toplam': _nd_dis_ticaret,
    'mali_kesim_toplam': _nd_mali_kesim,
    'tp_krediler_toplam': _nd_tp_krediler_toplam,
    # Pasif basit
    'krediler_mevduat': _nd_krediler_mevduat,
    'vadesiz_mevduat_toplam_mevduat': _nd_vadesiz_mevduat_mev,
    'tp_mevduat_toplam_mevduat': _nd_tp_mevduat,
    # Akım/TTM
    'roaa': _nd_roaa,
    'roae': _nd_roae,
    'nim': _nd_nim,
    'nim_bzk_sonrasi': _nd_nim_bzk_sonrasi,
    'faiz_getirili_aktif_getirisi': _nd_iea_getiri,
    'faiz_maliyetli_pasif_maliyeti': _nd_mp_maliyet,
    'kaynak_pacal_maliyet': _nd_mp_maliyet,
    'faiz_gideri_faiz_geliri': _nd_faiz_gid_gel,
    'faaliyet_gid_ort_aktif': _nd_faaliyet_aktif,
    'personel_ort_aktif': _nd_personel_aktif,
    'reklam_ort_aktif': _nd_reklam_aktif,
    'personel_net_kar': _nd_personel_kar,
    'reklam_net_kar': _nd_reklam_kar,
    'net_ucret_ort_aktif': _nd_net_ucret_aktif,
    'net_ucret_operasyonel': _nd_net_ucret_op,
    'komisyon_gid_gel': _nd_komisyon_gid_gel,
    'maliyet_gelir': _nd_maliyet_gelir,
    'kredi_pacal_getiri': _nd_kredi_pacal,
    'cost_of_risk': _nd_cost_of_risk,
    'donuk_intikal_ort_krediler': _nd_donuk_intikal,
    'donuk_tahsilat_ort_krediler': _nd_donuk_tahsilat,
    # Pasif 21 yeni
    'alinan_krediler_iemk_toplam_kaynak': _nd_alinan_iemk,
    'tp_alinan_toplam_alinan': _nd_tp_alinan,
    'tuzel_krediler_tuzel_mevduat': _nd_tuzel_kred_mev,
    'krediler_altindisi_mevduat': _nd_kred_altindisi_mev,
    'krediler_toplam_kaynak': _nd_kred_kaynak,
    'tp_krediler_tp_kaynak': _nd_tp_kred_kaynak,
    'yp_krediler_yp_altindisi_kaynak': _nd_yp_kred_altindisi,
    'vadesiz_mevduat_toplam_kaynak': _nd_vadesiz_kaynak,
    'tp_mevduat_altindisi_mevduat': _nd_tp_mevduat_altindisi,
    'tp_kaynak_toplam_kaynak': _nd_tp_kaynak,
    'toplam_kaynak_toplam_pasifler': _nd_kaynak_pasifler,
    'tp_pasifler_toplam_pasifler_ozkaynak_haric': _nd_tp_pasifler_oz_haric,
    'sermaye_benzeri_pasifler': _nd_sermaye_benzeri,
    'ppborclari_pasifler': _nd_ppb,
    'maliyetli_pasifler_toplam_pasifler': _nd_maliyetli_pasif,
    'serbest_sermaye_ta': _nd_serbest_sermaye,
    # 2026-08-14 measures.docx yeni 20 rasyo
    'kredi_riski_toplam_risk': _nd_kredi_riski_toplam_risk,
    'piyasa_riski_toplam_risk': _nd_piyasa_riski_toplam_risk,
    'operasyonel_risk_toplam_risk': _nd_operasyonel_risk_toplam_risk,
    'brut_krediler_ta': _nd_brut_krediler_ta,
    'bankalar_toplam_aktifler': _nd_bankalar_ta,
    'nakit_degerler_ta': _nd_nakit_degerler_ta,
    'yp_krediler_toplam_krediler': _nd_yp_krediler_toplam,
    'birikimli_vadeli_mevduat_toplam_vadeli': _nd_birikimli_vadeli,
    'resmi_kurumlar_mevduat_toplam_mevduat': _nd_resmi_kurumlar_mev,
    'toplam_fonlama_faiz_maliyetli_pasif': _nd_toplam_fonlama_mp,
    'tuzel_mevduat_toplam_mevduat': _nd_tuzel_mevduat_mev,
    'alinan_krediler_toplam_pasifler': _nd_alinan_krediler_toplam_pasifler,
    **{mid: _make_nd_likidite(kalem) for mid, kalem in _LIKIDITE_ACIGI_KALEM.items()},
    **{mid: _make_nd_vadeli(kalem) for mid, kalem in _VADELI_DILIM_KALEM.items()},
}


# Rasyo display ölçeği: varsayılan 100 (yüzde). 'kat'/oran olarak gösterilen
# measure'lar için 1.0 — bank seviyesi safe_ratio(scale=1.0) ile tutarlı olmalı.
RATIO_SCALE: Dict[str, float] = {
    'faiz_getirili_maliyetli': 1.0,  # birim='kat' → 2,05 kat
    'faiz_getirili_ozkaynak': 1.0,   # birim='kat' → 10,2 kat
    'toplam_fonlama_faiz_maliyetli_pasif': 1.0,  # birim='kat'
}


# Spread/farklar — basit ortalama ile aggregate
SIMPLE_AVG_RATIOS = {
    'spread',
    'kredi_mevduat_spread',
    'tp_spread',
    'yp_spread',
}

# Şube/personel başına özel handling
PER_BRANCH_RATIOS = {
    'sube_basina_krediler':           ('krediler', 'sube_sayisi', 1000),
    'sube_basina_mevduat':            ('mevduat', 'sube_sayisi', 1000),
    'sube_basina_net_kar':            ('net_donem_kari', 'sube_sayisi', 1000),
    'sube_basina_personel':           ('personel_sayisi', 'sube_sayisi', 1),
    'personel_basina_krediler':       ('krediler', 'personel_sayisi', 1000),
    'personel_basina_mevduat':        ('mevduat', 'personel_sayisi', 1000),
    'personel_basina_net_kar':        ('net_donem_kari', 'personel_sayisi', 1000),
    'personel_basina_personel_gideri': ('personel_giderleri', 'personel_sayisi', 1000),
}


# ============================================================
# Aggregation — value-level
# ============================================================

def _active_members(members, tarih, first_date_map):
    """
    Üyelerden HANGİLERİ bu tarihte piyasada var olması beklenen (kurulmuş)
    bankalar? (first_date_map[b] is None veya first_date_map[b] > tarih olan
    üyeler — yani bu ölçüt için hiç veri geçmişi olmayan/henüz kurulmamış
    bankalar — hariç tutulur.)

    first_date_map=None ise (first-date bilgisi hesaplanamamışsa, ör. eski
    çağrı yolları) TÜM üyeler "aktif" sayılır — eski (2026-08-11 öncesi)
    davranışla geriye dönük uyumlu.
    """
    if first_date_map is None:
        return list(members)
    return [b for b in members
            if first_date_map.get(b) is not None and first_date_map.get(b) <= tarih]


def _agg_size(bank_data, mid, members, tarih, first_date_map=None):
    """Büyüklük: Σ üye değerleri.

    İKİ AYRI "eksik veri" durumu var, birbirine KARIŞTIRILMAMALI:
    1. Banka henüz KURULMAMIŞ (first_date > tarih, ör. Enpara 2024-12-31
       öncesi, Dünya Katılım 2023-12-31 öncesi) — bu üye MEŞRU şekilde
       gruptan hariç tutulur, kalan üyelerin toplamı hesaplanır. Bu olmadan
       "Mevduat Bankaları"/"Katılım Bankaları" gibi çok üyeli gruplar,
       en yeni kurulan üyenin ilk raporlama tarihinden ÖNCEKİ HİÇBİR
       dönemde değer göstermiyordu (bkz. 2026-08-12 kullanıcı raporu).
    2. Banka ZATEN KURULMUŞ ama bu ÖZEL tarihte veri sağlamamış (çeyrek
       admin panelden banka banka yüklenirken henüz sırası gelmemiş) — bu
       GERÇEK bir eksikliktir, grup None döner (aksi halde grup toplamı
       gerçekte olduğundan küçük görünüp YtD/YoY oranlarını yanıltıcı
       çarpıtır, bkz. 2026-08-11 Haziran 2026 kısmi çeyrek olayı).
    """
    series = bank_data.get(mid, {})
    active = _active_members(members, tarih, first_date_map)
    vals = [series.get(b, {}).get(tarih) for b in active]
    if any(v is None for v in vals):
        return None
    return sum(vals) if vals else None


def _agg_ratio(ctx, mid, members, tarih, first_date_map=None):
    """Stok/akım rasyo: Σnum / Σden × 100. Aktif üyeler veri sağlamalı (bkz. _agg_size)."""
    fn = RATIO_NUM_DEN.get(mid)
    if fn is None:
        return None
    active = _active_members(members, tarih, first_date_map)
    num_sum, den_sum = 0.0, 0.0
    for b in active:
        try:
            n, d = fn(ctx, b, tarih)
        except Exception:
            return None
        if n is None or d is None:
            return None
        num_sum += n
        den_sum += d
    if den_sum == 0:
        return None
    return (num_sum / den_sum) * RATIO_SCALE.get(mid, 100.0)


def _agg_simple_avg(bank_data, mid, members, tarih, first_date_map=None):
    """Basit ortalama. Aktif üyeler veri sağlamalı (bkz. _agg_size)."""
    series = bank_data.get(mid, {})
    active = _active_members(members, tarih, first_date_map)
    vals = [series.get(b, {}).get(tarih) for b in active]
    if any(v is None for v in vals):
        return None
    return (sum(vals) / len(vals)) if vals else None


def _agg_per_unit(ctx, mid, members, tarih, first_date_map=None):
    """Şube/Personel başına: Σ(toplam_değer) / Σ(bölücü) / scale.
    Aktif üyeler veri sağlamalı (bkz. _agg_size)."""
    if mid not in PER_BRANCH_RATIOS:
        return None
    value_id, divisor_id, scale_div = PER_BRANCH_RATIOS[mid]
    active = _active_members(members, tarih, first_date_map)
    num_sum, den_sum = 0.0, 0.0
    for b in active:
        # Bölücü önce: 0 şube/personel olan üye (ör. dijital banka — Enpara,
        # TOM Bank, Hayat Finans 0 şube) bu "başına" metriğinden TAMAMEN
        # dışlanır (hem pay hem paydadan düşer). 2026-08-15 fix: eskiden
        # `not d → return None` idi, yani gruba tek bir 0-şubeli üye girdiği
        # anda TÜM grup boş dönüyordu (Katılım Bankaları 2022'den sonra,
        # Mevduat Bankaları kesintili). Şubesiz banka "şube başına" istatistiğe
        # dahil değildir — grubu boşaltmamalı.
        if divisor_id == 'sube_sayisi':
            d = ctx.sube(b, tarih, 'Şube Sayısı')
        else:  # personel_sayisi
            d = ctx.sube(b, tarih, 'Personel Sayısı')
        if not d:
            continue

        if value_id == 'krediler':
            n = krediler(ctx, b, tarih)
        elif value_id == 'mevduat':
            n = ctx.bilanco(b, tarih, 'Mevduat')
        elif value_id == 'net_donem_kari':
            # 2026-08-15: akım → TTM ile yıllıklandır (banka m_*_basina_net_kar ile hizalı,
            # ara çeyreklerde YtD sawtooth'unu önler)
            n = ttm_flow(ctx, b, tarih, lambda bb, tt: ctx.gelir(bb, tt, 'Net Dönem Karı / Zararı'))
        elif value_id == 'personel_sayisi':
            n = ctx.sube(b, tarih, 'Personel Sayısı')
        elif value_id == 'personel_giderleri':
            # 2026-08-15: akım → TTM (banka m_personel_basina_personel_gideri ile hizalı)
            n = ttm_flow(ctx, b, tarih, lambda bb, tt: ctx.gelir(bb, tt, 'Personel Giderleri (-)'))
        else:
            n = None

        if n is None:
            continue  # numerator verisi eksik üye — grubu boşaltmadan atla
        num_sum += n
        den_sum += d
    if den_sum == 0:
        return None
    if scale_div == 1:
        return num_sum / den_sum
    return num_sum / scale_div / den_sum


# ============================================================
# Main entry — build_group_data
# ============================================================
#
# TEK grup-hesaplama motoru. Önceden burada `compute_group_aggregates` adında
# ayrı bir implementasyon vardı (Sektör/Mevduat Sektörü/Katılım — banka
# `tur`üne göre 3 sabit grup, sonuçları bank_data içine sahte "banka" olarak
# gömüyordu). O fonksiyon hem hiçbir yerden okunmuyordu (frontend sadece
# `group_data`'yı okur) hem de bir bug içeriyordu (`tip == 'büyüklük'`
# kontrolü catalog'daki gerçek değer olan `'buyukluk'` ile hiç eşleşmiyordu,
# yani büyüklük tipi measure'lar bile yanlış dala düşüyordu). Kaldırıldı.
#
# Şimdi tek implementasyon bu: catalog.json → groups.members'taki 5 grubu
# (Kuveyt Türk, Mevduat Bankaları, Rakip Bankalar, Katılım Bankaları,
# KT Hariç Katılım Bankaları) hesaplar, `group_data[measure_id][grup][tarih]
# = {'value': v}` şeklinde AYRI bir yapı döner (bank_data'ya karışmaz).
# app.py ve scripts/recompute.py bu TEK fonksiyonu kullanır.

def build_group_data(
    bank_data: Dict[str, Dict[str, Dict[str, Optional[float]]]],
    catalog,
    ctx: LookupContext,
) -> Dict[str, Dict[str, Dict[str, dict]]]:
    """
    `compute_all()`'ın ürettiği banka-level bank_data'dan, catalog.json'daki
    `groups.members` tanımına göre grup aggregate'lerini hesaplar.

    Dönüş: group_data[measure_id][grup_adi][tarih] = {'value': v}
    """
    if isinstance(catalog, list):
        # Sadece measures listesi geldiyse — banks/groups bilgisi yok.
        return {}

    members_map = (catalog.get('groups', {}) or {}).get('members', {}) or {}
    measures_list = catalog.get('measures', [])
    real_banks = set(b['banka_adi'] for b in catalog.get('banks', []))

    # Tarih unionu (gerçek bankalar üzerinden — grup pseudo-kayıtları hariç)
    date_set = set()
    for bydict in bank_data.values():
        for bname, series in bydict.items():
            if bname in real_banks:
                date_set.update(series.keys())
    dates = sorted(date_set)

    # Her bankanın İLK raporlama tarihi — "henüz kurulmamış" (Enpara,
    # Hayat Finans, Dünya Katılım, TOM Bank gibi sonradan kurulan bankalar)
    # ile "kurulmuş ama bu tarihte veri eksik" ayrımı için (bkz. _agg_size
    # docstring'i). toplam_aktifler referans alınır — ölçüt bazında değil,
    # bankanın gerçek varlığına dair sabit bir gerçek olduğundan.
    ta_series = bank_data.get('toplam_aktifler', {})
    first_date_map: Dict[str, Optional[str]] = {}
    for b in real_banks:
        b_dates = [d for d, v in ta_series.get(b, {}).items() if v is not None]
        first_date_map[b] = min(b_dates) if b_dates else None

    group_data: Dict[str, Dict[str, dict]] = {}
    for mid_meta in measures_list:
        mid = mid_meta['id']
        tip = mid_meta.get('tip', 'rasyo')
        group_data.setdefault(mid, {})
        for gname, members in members_map.items():
            if not members:
                continue
            gd = {}
            for tarih in dates:
                if mid in PER_BRANCH_RATIOS:
                    v = _agg_per_unit(ctx, mid, members, tarih, first_date_map)
                elif mid in SIMPLE_AVG_RATIOS:
                    v = (_agg_size(bank_data, mid, members, tarih, first_date_map)
                         if mid == 'npl_formasyonu'
                         else _agg_simple_avg(bank_data, mid, members, tarih, first_date_map))
                elif tip == 'buyukluk':
                    v = _agg_size(bank_data, mid, members, tarih, first_date_map)
                elif mid in RATIO_NUM_DEN:
                    v = _agg_ratio(ctx, mid, members, tarih, first_date_map)
                else:
                    v = _agg_simple_avg(bank_data, mid, members, tarih, first_date_map)
                if v is not None:
                    gd[tarih] = {'value': v}
            if gd:
                group_data[mid][gname] = gd
    return group_data
