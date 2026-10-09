"""
pipeline.rekabet_olculer
=========================
"Kuveyt Türk Rekabet Analizi · 2026 İlk Yarı" çalışmasının (Rekabet Analizi/KT_Rekabet_Analizi_Teknik_Devir.md)
ölçüm sözlüğünden sisteme alınan ölçüler (2026-10-06). Üç parça tek yerde tutulur:

- banka düzeyi formüller (MEASURE_FUNCS'a eklenir),
- grup toplama kuralları (RATIO_NUM_DEN / RATIO_SCALE / GRUP_OZEL / GRUPSUZ; groups.py'ye eklenir),
- katalog kayıtları (KATALOG; catalog.seed.json bu listeden üretilir, bkz. scripts/rekabet_katalog_yaz.py).

Sistemde zaten olan bir ölçünün tanımı DEĞİŞTİRİLMEDİ: dokümandaki tanım farklıysa (ör. NIM'in payda olarak
getirili aktif alması) yeni ölçü ayrı adla eklendi. Birim kuralları sistemle aynı: tutarlar TL, oranlar yüzde
(birim '%'), kişi/şube başına bin TL. Akım ölçülerde (gelir tablosu) oranlar sistemdeki ROAA/NIM gibi TTM,
yıllık büyüme ölçüleri YtD/YtD'dir.

Kaynak kalemleri, dokümandaki KT 30.06.2026 değerleriyle sınanmıştır (tests/test_rekabet_olculer.py).
"""
from __future__ import annotations

from typing import Callable, Dict, Optional, Set, Tuple

from . import manuel_veri
from .lookup import avg_balance, safe_ratio, ttm_flow
from .measures import (
    _NPL_INTIKAL_ITEMS, _NPL_TAHSILAT_ITEMS, _brut_krediler, _faiz_getirili_aktif_detay, _gelir_toplami,
    _opex, _yoy_fark_num_den, m_grup_2_krediler, m_personel_sayisi, m_sube_sayisi, m_toplam_fonlama,
    reel_buyume, toplam_rav,
)

NumDen = Tuple[Optional[float], Optional[float]]
NumDenFn = Callable[..., NumDen]

_SINIFLAR = ('Sınırlı', 'Şüpheli', 'Zarar Niteliğinde')


# ============================================================
# Ortak kalem okuyucular
# ============================================================

def _zk_geliri(ctx, b, t):
    return ctx.gelir(b, t, 'Zorunlu Karşılıklardan Alınan Faizler')


def _tcmb_hesabi(ctx, b, t):
    """TCMB hesabı (TP + YP) — zorunlu karşılık ve serbest hesabı birlikte (dönem sonu stok)."""
    return ctx.tcmb(b, t, 'TCMB Hesabı, (TP)') + ctx.tcmb(b, t, 'TCMB Hesabı, (YP)')


def _faiz_geliri(ctx, b, t):
    return ctx.gelir(b, t, 'Faiz Gelirleri')


def _net_faiz_geliri(ctx, b, t):
    return ctx.gelir(b, t, 'Net Faiz Geliri/Gideri')


def _turev_kz(ctx, b, t):
    return ctx.gelir(b, t, 'Türev Finansal İşlemlerden Kar/Zarar')


def _kambiyo_kz(ctx, b, t):
    return ctx.gelir(b, t, 'Kambiyo İşlemleri Kâr/Zararı')


def _vok(ctx, b, t):
    return ctx.gelir(b, t, 'Sürdürülen Faaliyetler Vergi Öncesi Kar/Zarar')


def _net_kar(ctx, b, t):
    return ctx.gelir(b, t, 'Net Dönem Karı / Zararı')


def _ttm(ctx, b, t, fn):
    return ttm_flow(ctx, b, t, lambda bb, tt: fn(ctx, bb, tt))


def _avg(ctx, b, t, fn):
    return avg_balance(ctx, b, t, lambda bb, tt: fn(ctx, bb, tt))


def _ort_getirili_aktif(ctx, b, t):
    return _avg(ctx, b, t, _faiz_getirili_aktif_detay)


def _ort_tcmb(ctx, b, t):
    return _avg(ctx, b, t, _tcmb_hesabi)


def _nd(num, den) -> NumDen:
    """Payda yoksa/sıfırsa (None, None): grup toplamına hiç girmez."""
    if num is None or not den:
        return None, None
    return num, den


# ============================================================
# 1. Zorunlu karşılık sürüklemesi, TCMB ve marj
# ============================================================

def nd_zk_faiz_geliri(ctx, b, t):
    return _nd(_ttm(ctx, b, t, _zk_geliri), _ttm(ctx, b, t, _faiz_geliri))


def nd_tcmb_getirili_aktif(ctx, b, t):
    return _nd(_ort_tcmb(ctx, b, t), _ort_getirili_aktif(ctx, b, t))


def nd_ortuk_tcmb_getirisi(ctx, b, t):
    return _nd(_ttm(ctx, b, t, _zk_geliri), _ort_tcmb(ctx, b, t))


def nd_zk_haric_getiri(ctx, b, t):
    fg, zk = _ttm(ctx, b, t, _faiz_geliri), _ttm(ctx, b, t, _zk_geliri)
    ga, tc = _ort_getirili_aktif(ctx, b, t), _ort_tcmb(ctx, b, t)
    if None in (fg, zk, ga, tc):
        return None, None
    return _nd(fg - zk, ga - tc)


def nd_getiri(ctx, b, t):
    return _nd(_ttm(ctx, b, t, _faiz_geliri), _ort_getirili_aktif(ctx, b, t))


def nd_nim_getirili_aktif(ctx, b, t):
    return _nd(_ttm(ctx, b, t, _net_faiz_geliri), _ort_getirili_aktif(ctx, b, t))


def nd_nim_swap(ctx, b, t):
    """Swap düzeltmesi yalnız TÜREV K/Z'dir (kambiyo ve diğer ticari K/Z dahil değil)."""
    return _nd(_ttm(ctx, b, t, lambda c, bb, tt: _net_faiz_geliri(c, bb, tt) + _turev_kz(c, bb, tt)),
               _ort_getirili_aktif(ctx, b, t))


def _bir(fn):
    """(num, den) → oran (yüzde)."""
    def f(ctx, b, t):
        n, d = fn(ctx, b, t)
        return safe_ratio(n, d)
    return f


def m_zorunlu_karsilik_geliri(ctx, b, t):
    return _zk_geliri(ctx, b, t)


def m_zk_surukleme(ctx, b, t):
    """Sürükleme (puan) = ZK hariç getiri − getiri'nin negatifi ters: getiri − ZK hariç getiri (≤ 0 beklenir).
    Doküman: −(getiri_zk − getiri) × 10.000 bps; burada yüzde puan (−2,46 = −246 bps)."""
    g = _bir(nd_getiri)(ctx, b, t)
    gz = _bir(nd_zk_haric_getiri)(ctx, b, t)
    return None if g is None or gz is None else g - gz


def grup_zk_surukleme(ctx, uyeler, tarih, ilk_tarih, sum_ratio):
    g = sum_ratio(ctx, nd_getiri, uyeler, tarih, ilk_tarih, 100.0)
    gz = sum_ratio(ctx, nd_zk_haric_getiri, uyeler, tarih, ilk_tarih, 100.0)
    return None if g is None or gz is None else g - gz


# ============================================================
# 2. Donuk alacak hareketi ve karşılıklar
# ============================================================

def _donuk_akim_toplam(ctx, b, t, sablon):
    return sum(ctx.donuk_akim(b, t, sablon % s) for s in _SINIFLAR)


def _donuk_onceki_donem(ctx, b, t):
    return _donuk_akim_toplam(ctx, b, t, 'Donuk Alacaklar (%s, Önceki Dönem)')


def _donuk_terkin_satis(ctx, b, t):
    return abs(_donuk_akim_toplam(ctx, b, t, 'Donuk Alacaklar (%s, Aktiften Silinen)')) \
        + abs(_donuk_akim_toplam(ctx, b, t, 'Donuk Alacaklar (%s, Satılan)'))


def _intikal(ctx, b, t):
    return sum(ctx.donuk_akim(b, t, k) for k in _NPL_INTIKAL_ITEMS)


def _tahsilat(ctx, b, t):
    """Ham veride negatif saklanır; pozitif döndürülür."""
    return -sum(ctx.donuk_akim(b, t, k) for k in _NPL_TAHSILAT_ITEMS)


def _intikal_donem_ici(ctx, b, t):
    return _donuk_akim_toplam(ctx, b, t, 'Donuk Alacaklar (%s, Dönem İçi İntikal)')


def _tahsilat_donem_ici(ctx, b, t):
    return -_donuk_akim_toplam(ctx, b, t, 'Donuk Alacaklar (%s, Dönem İçi Tahsilat)')


def nd_donuk_tahsilat_intikal(ctx, b, t):
    """Yalnız 'Dönem İçi' intikal ve tahsilat satırları (diğer giriş/çıkış hariç): KT 9.871 / 20.929 = %47,2."""
    return _nd(_tahsilat_donem_ici(ctx, b, t), _intikal_donem_ici(ctx, b, t))


def nd_donuk_portfoy_temizligi(ctx, b, t):
    return _nd(_donuk_terkin_satis(ctx, b, t), _donuk_onceki_donem(ctx, b, t))


def m_donuk_net_olusum(ctx, b, t):
    return _intikal(ctx, b, t) - _tahsilat(ctx, b, t)


_ASAMA_3 = 'Temerrüt (Üçüncü Aşama/Özel Karşılık)'
_ASAMA_2 = 'Kredi Riskinde Önemli Artış (İkinci Aşama)'


def _asama_karsiligi(ctx, b, t, kalem, eski_kalem=None):
    """Aşama karşılığı (pozitif). TFRS 9 aşama satırı boş/sıfırsa (2018-2020 bazı dosyalarda) eski şablondaki
    karşılık satırı; ikisi de yoksa None (sıfır değil: veri yok)."""
    for k in (kalem, eski_kalem):
        if k and ctx.var('bilanco', b, t, k) and ctx.bilanco(b, t, k):
            return abs(ctx.bilanco(b, t, k))
    return None


def _ozel_karsilik_donuk_tablosu(ctx, b, t):
    """Donuk alacak dipnotundaki özel karşılık satırları (III–V. grup toplamı), pozitif; yoksa None."""
    v = sum(abs(ctx.donuk_akim(b, t, 'Donuk Alacaklar (%s, Özel Karşılık)' % s)) for s in _SINIFLAR)
    return v or None


def nd_npl_3_asama_karsilama(ctx, b, t):
    """3. aşama (özel) karşılık / donuk alacak. Sıra: bilanço 3. aşama satırı → donuk dipnotundaki özel karşılık
    (2018-2020'de aşama satırları boş) → eski şablonun özel karşılıkları."""
    from .lookup import donuk_alacaklar
    pay = _asama_karsiligi(ctx, b, t, _ASAMA_3)
    if pay is None:
        pay = _ozel_karsilik_donuk_tablosu(ctx, b, t)
    if pay is None:
        pay = _asama_karsiligi(ctx, b, t, 'Özel Karşılıklar (-)')
    return _nd(pay, donuk_alacaklar(ctx, b, t))


def nd_grup_2_karsilama(ctx, b, t):
    return _nd(_asama_karsiligi(ctx, b, t, _ASAMA_2), m_grup_2_krediler(ctx, b, t))


# ============================================================
# 3. Gider, verimlilik ve gelir yapısı
# ============================================================

def nd_personel_basina_opex(ctx, b, t):
    return _nd(_ttm(ctx, b, t, _opex), m_personel_sayisi(ctx, b, t))


def nd_sube_basina_opex(ctx, b, t):
    return _nd(_ttm(ctx, b, t, _opex), m_sube_sayisi(ctx, b, t))


def _personel_sayisi_deger(ctx, b, t):
    return m_personel_sayisi(ctx, b, t)


def nd_personel_sayisi_yoy(ctx, b, t):
    """Kadro değişimi (YoY): (personel − önceki yıl) / önceki yıl. Pay = fark, payda = baz."""
    return _yoy_fark_num_den(ctx, b, t, _personel_sayisi_deger)


def _kisi_basi(ctx, b, t, gider_fn):
    p = m_personel_sayisi(ctx, b, t)
    g = gider_fn(ctx, b, t)
    return g / p if p and g is not None else None


def _kisi_basi_yoy(ctx, b, t, gider_fn):
    prev = ctx.yoy_period(b, t)
    if prev is None:
        return None
    cur, baz = _kisi_basi(ctx, b, t, gider_fn), _kisi_basi(ctx, b, prev, gider_fn)
    return None if not cur or not baz or baz <= 0 else (cur / baz - 1) * 100.0


def m_personel_basina_personel_gideri_yoy(ctx, b, t):
    return _kisi_basi_yoy(ctx, b, t, lambda c, bb, tt: c.gelir(bb, tt, 'Personel Giderleri (-)'))


def m_personel_basina_opex_yoy(ctx, b, t):
    return _kisi_basi_yoy(ctx, b, t, _opex)


def _grup_kisi_basi_yoy(ctx, uyeler, tarih, ilk_tarih, gider_fn, aktif_uyeler):
    """Grup: (Σ gider / Σ personel) bu yıl ÷ aynı oran geçen yıl − 1 (üye oranlarının ortalaması DEĞİL)."""
    gn = gd = bn = bd = 0.0
    for b in aktif_uyeler(uyeler, tarih, ilk_tarih):
        prev = ctx.yoy_period(b, tarih)
        if prev is None:
            continue
        p1, p0 = m_personel_sayisi(ctx, b, tarih), m_personel_sayisi(ctx, b, prev)
        g1, g0 = gider_fn(ctx, b, tarih), gider_fn(ctx, b, prev)
        if not (p1 and p0) or g1 is None or g0 is None:
            continue
        gn, gd, bn, bd = gn + g1, gd + p1, bn + g0, bd + p0
    if not gd or not bd or not bn:
        return None
    return ((gn / gd) / (bn / bd) - 1) * 100.0


def nd_net_ucret_faaliyet_gelirleri(ctx, b, t):
    return _nd(ctx.gelir(b, t, 'Net Ücret Ve Komisyon Gelirleri/Giderleri'), _gelir_toplami(ctx, b, t))


def m_faaliyet_gelirleri(ctx, b, t):
    return _gelir_toplami(ctx, b, t)


# ============================================================
# 4. Kârlılık bileşimi
# ============================================================

def m_vergi_oncesi_kar(ctx, b, t):
    return _vok(ctx, b, t)


def nd_efektif_vergi(ctx, b, t):
    return _nd(ctx.gelir(b, t, 'Sürdürülen Faaliyetler Vergi Karşılığı (±)'), _vok(ctx, b, t))


def nd_istirak_kari(ctx, b, t):
    return _nd(ctx.gelir(b, t, 'Özkaynak Yöntemi Uygulanan Ortaklıklardan Kar/Zarar'), _vok(ctx, b, t))


def nd_net_kar_yoy(ctx, b, t):
    return _yoy_fark_num_den(ctx, b, t, _net_kar)


def m_net_kar_yoy_buyumesi(ctx, b, t):
    return safe_ratio(*nd_net_kar_yoy(ctx, b, t))


def _reel(nominal, t):
    from .makro import tufe_yillik
    return reel_buyume(nominal, tufe_yillik(t))


def m_reel_net_kar_buyumesi(ctx, b, t):
    return _reel(m_net_kar_yoy_buyumesi(ctx, b, t), t)


def grup_reel_net_kar(ctx, uyeler, tarih, ilk_tarih, sum_ratio):
    return _reel(sum_ratio(ctx, nd_net_kar_yoy, uyeler, tarih, ilk_tarih, 100.0), tarih)


def m_turev_kar_zarar(ctx, b, t):
    return _turev_kz(ctx, b, t)


def m_kambiyo_kar_zarar(ctx, b, t):
    return _kambiyo_kz(ctx, b, t)


# ============================================================
# 5. Döviz, altın, fonlama ve sermaye
# ============================================================

def _yp_fonlama(ctx, b, t):
    return sum(ctx.bilanco(b, t, k, 'YP') for k in
               ('Mevduat', 'Alınan Krediler', 'Para Piyasalarına Borçlar', 'İhraç Edilen Menkul Kıymetler (Net)'))


def nd_yp_toplam_fonlama(ctx, b, t):
    return _nd(_yp_fonlama(ctx, b, t), m_toplam_fonlama(ctx, b, t))


def nd_krediler_toplam_fonlama(ctx, b, t):
    return _nd(_brut_krediler(ctx, b, t), m_toplam_fonlama(ctx, b, t))


def _altin_vadesiz(ctx, b, t):
    """Altın (kıymetli maden) hesaplarının vadesiz kısmı. Katılım bankalarında fon vade tablosundan (Toplanan Fonların Vade Yapısı),
    mevduat bankalarında mevduat vade tablosundan ('Kıym. Mad. Depo Hesabı, Vadesiz') — ikisi de BDDK verisinde bulunur, böylece tüm
    dönemler için hesaplanır. Bulunamazsa elle yüklenen BDR verisi (manuel_olculer.json) yedek olarak kullanılır."""
    if ctx.bank_turu.get(b) == 'Katılım':
        v = ctx.tfv(b, t, 'Kıymetli Maden DH Vadesiz')
    else:
        v = ctx.mvy(b, t, 'Kıym. Mad. Depo Hesabı, Vadesiz')
    if v:
        return v
    return manuel_veri.deger('altin_vadesiz_tutar', b, t)


def nd_altin_vadesiz_payi(ctx, b, t):
    return _nd(_altin_vadesiz(ctx, b, t), ctx.kiymetli_maden(b, t))


def nd_yp_fonlama_fazlasi_aktif(ctx, b, t):
    """YP fonlama fazlası = max(0, YP toplam fonlama − YP brüt krediler); aktife oranı."""
    fazla = max(0.0, _yp_fonlama(ctx, b, t) - _brut_krediler(ctx, b, t, 'YP'))
    return _nd(fazla, ctx.bilanco(b, t, 'Toplam Aktifler'))


def nd_rav_yogunlugu(ctx, b, t):
    return _nd(toplam_rav(ctx, b, t), ctx.bilanco(b, t, 'Toplam Aktifler'))


def nd_basit_kaldirac(ctx, b, t):
    return _nd(ctx.bilanco(b, t, 'Özkaynaklar'), ctx.bilanco(b, t, 'Toplam Aktifler'))


# ============================================================
# 6. Elle yüklenen (BDR) ölçüler
# ============================================================

def _manuel(mid):
    return lambda ctx, b, t: manuel_veri.deger(mid, b, t)


def nd_kar_tamponu_net_kar(ctx, b, t):
    """(Serbest karşılık bakiyesi + TÜFEX tamponu) / dönem net kârı (YtD). Yalnız İKİ bileşen de bilindiğinde hesaplanır: TÜFEX'i
    bilinmeyen (açıklamayan / tahmini enflasyon kullanıp varsayımı vermeyen) bankada kısmi tampon göstermek tamponu olduğundan düşük
    gösterirdi. Yapısal sıfır (TÜFEX = 0) açıkça 0 olarak yüklüdür."""
    sk, tx = manuel_veri.deger('serbest_karsilik', b, t), manuel_veri.deger('tufex_tamponu', b, t)
    if sk is None or tx is None:
        return None, None
    return _nd(sk + tx, _net_kar(ctx, b, t))


# ============================================================
# Kayıtlar
# ============================================================

# Banka düzeyi: rasyo ölçüler (num, den) → yüzde; ölçek 100 dışındakiler RATIO_SCALE'de.
RATIO_NUM_DEN: Dict[str, NumDenFn] = {
    'zk_faiz_gelirleri_orani': nd_zk_faiz_geliri,
    'tcmb_hesabi_getirili_aktif': nd_tcmb_getirili_aktif,
    'ortuk_tcmb_getirisi': nd_ortuk_tcmb_getirisi,
    'zk_haric_getirili_aktif_getirisi': nd_zk_haric_getiri,
    'nim_getirili_aktif': nd_nim_getirili_aktif,
    'nim_swap_duzeltilmis': nd_nim_swap,
    'donuk_tahsilat_intikal': nd_donuk_tahsilat_intikal,
    'donuk_portfoy_temizligi': nd_donuk_portfoy_temizligi,
    'npl_3_asama_karsilama': nd_npl_3_asama_karsilama,
    'grup_2_karsilama': nd_grup_2_karsilama,
    'personel_basina_opex': nd_personel_basina_opex,
    'sube_basina_opex': nd_sube_basina_opex,
    'personel_sayisi_yoy': nd_personel_sayisi_yoy,
    'net_ucret_faaliyet_gelirleri': nd_net_ucret_faaliyet_gelirleri,
    'efektif_vergi_orani': nd_efektif_vergi,
    'istirak_kari_vergi_oncesi_kar': nd_istirak_kari,
    'net_kar_yoy_buyumesi': nd_net_kar_yoy,
    'yp_toplam_fonlama_payi': nd_yp_toplam_fonlama,
    'krediler_toplam_fonlama': nd_krediler_toplam_fonlama,
    'altin_vadesiz_payi': nd_altin_vadesiz_payi,
    'yp_fonlama_fazlasi_aktif': nd_yp_fonlama_fazlasi_aktif,
    'rav_yogunlugu': nd_rav_yogunlugu,
    'basit_kaldirac': nd_basit_kaldirac,
    'kar_tamponu_net_kar': nd_kar_tamponu_net_kar,
    'personel_basina_opex_yoy': None,        # özel grup kuralı (aşağıda)
    'personel_basina_personel_gideri_yoy': None,
}
RATIO_NUM_DEN = {k: v for k, v in RATIO_NUM_DEN.items() if v is not None}

# Bin TL ölçüler: kalemler TL, gösterim bin TL (num / den / 1000).
RATIO_SCALE: Dict[str, float] = {
    'personel_basina_opex': 0.001,
    'sube_basina_opex': 0.001,
}

# Banka düzeyinde (num, den) çiftinden hesaplanan rasyolar için tek fonksiyon (sistem MEASURE_FUNCS biçimi).
MEASURE_FUNCS: Dict[str, Callable] = {
    mid: (lambda fn, sc: (lambda ctx, b, t: safe_ratio(*fn(ctx, b, t), scale=sc)))(fn, RATIO_SCALE.get(mid, 100.0))
    for mid, fn in RATIO_NUM_DEN.items()
}
MEASURE_FUNCS.update({
    'zorunlu_karsilik_geliri': m_zorunlu_karsilik_geliri,
    'zk_surukleme': m_zk_surukleme,
    'donuk_net_olusum': m_donuk_net_olusum,
    'faaliyet_gelirleri': m_faaliyet_gelirleri,
    'vergi_oncesi_kar': m_vergi_oncesi_kar,
    'reel_net_kar_buyumesi': m_reel_net_kar_buyumesi,
    'turev_kar_zarar': m_turev_kar_zarar,
    'kambiyo_kar_zarar': m_kambiyo_kar_zarar,
    'personel_basina_opex_yoy': m_personel_basina_opex_yoy,
    'personel_basina_personel_gideri_yoy': m_personel_basina_personel_gideri_yoy,
    **{mid: _manuel(mid) for mid in ('basel_kaldirac_orani', 'lcr', 'lcr_yp', 'serbest_karsilik', 'tufex_tamponu')},
})

# Grup değeri üye oranlarının toplanmasıyla değil, kendi kuralıyla bulunan ölçüler:
# fn(ctx, uyeler, tarih, first_date_map, sum_ratio, aktif_uyeler)
GRUP_OZEL: Dict[str, Callable] = {
    'zk_surukleme': lambda ctx, u, t, f, sr, au: grup_zk_surukleme(ctx, u, t, f, sr),
    'reel_net_kar_buyumesi': lambda ctx, u, t, f, sr, au: grup_reel_net_kar(ctx, u, t, f, sr),
    'personel_basina_opex_yoy':
        lambda ctx, u, t, f, sr, au: _grup_kisi_basi_yoy(ctx, u, t, f, _opex, au),
    'personel_basina_personel_gideri_yoy':
        lambda ctx, u, t, f, sr, au: _grup_kisi_basi_yoy(
            ctx, u, t, f, lambda c, bb, tt: c.gelir(bb, tt, 'Personel Giderleri (-)'), au),
}

# Grup değeri HESAPLANMAYAN ölçüler: paydası açıklanmayan rasyoların paçalı yazılmaz (LCR, kaldıraç).
GRUPSUZ: Set[str] = {'basel_kaldirac_orani', 'lcr', 'lcr_yp'}


# ============================================================
# Katalog kayıtları (catalog.seed.json'a bu sırayla eklenir)
# ============================================================

def _k(mid, ad, tip, akim_stok, birim, kategori, alt, sort, pazar=False):
    return {'id': mid, 'ad': ad, 'tip': tip, 'akim_stok': akim_stok, 'birim': birim, 'kategori': kategori,
            'alt_kategori': alt, 'pazar_payi': pazar, 'sort_direction': sort}


_GT, _BL, _SP = 'Gelir Tablosu', 'Bilanço', 'Şube & Personel'

KATALOG = [
    # 1. Zorunlu karşılık, TCMB ve marj
    _k('zorunlu_karsilik_geliri', 'Zorunlu Karşılıklardan Alınan Faiz (Kar Payı) Gelirleri', 'buyukluk', 'akim', 'TL', _GT, None, 'desc', True),
    _k('zk_faiz_gelirleri_orani', 'Zorunlu Karşılık Gelirleri / Faiz (Kar Payı) Gelirleri', 'rasyo', 'akim', '%', _GT, None, 'asc'),
    _k('tcmb_hesabi_getirili_aktif', 'Ortalama TCMB Hesabı / Ortalama Faiz (Kar Payı) Getirili Aktifler', 'rasyo', 'stok', '%', _BL, 'Aktifler', 'asc'),
    _k('ortuk_tcmb_getirisi', 'Örtük TCMB Getirisi (ZK Geliri / Ortalama TCMB Hesabı)', 'rasyo', 'akim', '%', _GT, None, 'desc'),
    _k('zk_haric_getirili_aktif_getirisi', 'ZK Hariç Faiz (Kar Payı) Getirili Aktif Getirisi', 'rasyo', 'akim', '%', _GT, None, 'desc'),
    _k('zk_surukleme', 'Zorunlu Karşılık Sürüklemesi (puan)', 'rasyo', 'akim', '%', _GT, None, 'desc'),
    _k('nim_getirili_aktif', 'Net Faiz (Kar Payı) Marjı (Getirili Aktif Bazlı)', 'rasyo', 'akim', '%', _GT, None, 'desc'),
    _k('nim_swap_duzeltilmis', 'Swap Düzeltilmiş Net Faiz (Kar Payı) Marjı (Getirili Aktif Bazlı)', 'rasyo', 'akim', '%', _GT, None, 'desc'),
    # 2. Donuk alacak hareketi ve karşılıklar
    _k('donuk_tahsilat_intikal', 'Donuk Alacak Tahsilatı / İntikali', 'rasyo', 'akim', '%', _BL, 'Aktifler', 'desc'),
    _k('donuk_portfoy_temizligi', 'Donuk Alacak Portföy Temizliği ((Terkin + Satış) / Dönem Başı Donuk)', 'rasyo', 'akim', '%', _BL, 'Aktifler', 'desc'),
    _k('donuk_net_olusum', 'Donuk Alacak Net Oluşumu (İntikal − Tahsilat)', 'buyukluk', 'akim', 'TL', _BL, 'Aktifler', 'asc'),
    _k('npl_3_asama_karsilama', 'NPL 3. Aşama Karşılama Oranı', 'rasyo', 'stok', '%', _BL, 'Aktifler', 'desc'),
    _k('grup_2_karsilama', 'Grup 2 Krediler 2. Aşama Karşılama Oranı', 'rasyo', 'stok', '%', _BL, 'Aktifler', 'desc'),
    # 3. Gider, verimlilik ve gelir yapısı
    _k('faaliyet_gelirleri', 'Faaliyet Gelirleri', 'buyukluk', 'akim', 'TL', _GT, None, 'desc', True),
    _k('net_ucret_faaliyet_gelirleri', 'Net Ücret ve Komisyonlar / Faaliyet Gelirleri', 'rasyo', 'akim', '%', _GT, None, 'desc'),
    _k('personel_basina_opex', 'Personel Başına OPEX', 'rasyo', 'akim', 'bin_TL', _SP, None, 'asc'),
    _k('sube_basina_opex', 'Şube Başına OPEX', 'rasyo', 'akim', 'bin_TL', _SP, None, 'asc'),
    _k('personel_sayisi_yoy', 'Personel Sayısı Değişimi (YoY)', 'rasyo', 'stok', '%', _SP, None, 'asc'),
    _k('personel_basina_personel_gideri_yoy', 'Personel Başına Personel Gideri Büyümesi (YoY)', 'rasyo', 'akim', '%', _SP, None, 'asc'),
    _k('personel_basina_opex_yoy', 'Personel Başına OPEX Büyümesi (YoY)', 'rasyo', 'akim', '%', _SP, None, 'asc'),
    # 4. Kârlılık bileşimi
    _k('vergi_oncesi_kar', 'Vergi Öncesi Kar (Sürdürülen Faaliyetler)', 'buyukluk', 'akim', 'TL', _GT, None, 'desc', True),
    _k('efektif_vergi_orani', 'Efektif Vergi Oranı', 'rasyo', 'akim', '%', _GT, None, 'asc'),
    _k('istirak_kari_vergi_oncesi_kar', 'Özkaynak Yöntemi İştirak Kârı / Vergi Öncesi Kar', 'rasyo', 'akim', '%', _GT, None, 'asc'),
    _k('net_kar_yoy_buyumesi', 'Net Dönem Kârı Büyümesi (YoY)', 'rasyo', 'akim', '%', _GT, None, 'desc'),
    _k('reel_net_kar_buyumesi', 'Reel Net Dönem Kârı Büyümesi (TÜFE\'ye Göre)', 'rasyo', 'akim', '%', _GT, None, 'desc'),
    _k('turev_kar_zarar', 'Türev Finansal İşlemlerden Kar/Zarar', 'buyukluk', 'akim', 'TL', _GT, None, 'desc'),
    _k('kambiyo_kar_zarar', 'Kambiyo İşlemleri Kâr/Zararı', 'buyukluk', 'akim', 'TL', _GT, None, 'desc'),
    # 5. Döviz, altın, fonlama ve sermaye
    _k('yp_toplam_fonlama_payi', 'YP Toplam Fonlama / Toplam Fonlama', 'rasyo', 'stok', '%', _BL, 'Pasifler', 'desc'),
    _k('krediler_toplam_fonlama', 'Toplam Brüt Krediler / Toplam Fonlama', 'rasyo', 'stok', '%', _BL, 'Pasifler', 'desc'),
    _k('altin_vadesiz_payi', 'Altın Hesapları Vadesiz Payı (Altın Hesapları İçinde)', 'rasyo', 'stok', '%', _BL, 'Pasifler', 'desc'),
    _k('yp_fonlama_fazlasi_aktif', 'YP Fonlama Fazlası / Toplam Aktifler', 'rasyo', 'stok', '%', _BL, 'Pasifler', 'desc'),
    _k('rav_yogunlugu', 'RAV Yoğunluğu (Toplam RAV / Toplam Aktifler)', 'rasyo', 'stok', '%', _BL, 'Pasifler', 'asc'),
    _k('basit_kaldirac', 'Basit Kaldıraç (Özkaynaklar / Toplam Aktifler)', 'rasyo', 'stok', '%', _BL, 'Pasifler', 'desc'),
    # 6. Elle yüklenen (BDR) ölçüler
    _k('basel_kaldirac_orani', 'Basel III Kaldıraç Oranı', 'rasyo', 'stok', '%', _BL, 'Pasifler', 'desc'),
    _k('lcr', 'Likidite Karşılama Oranı (LCR)', 'rasyo', 'stok', '%', _BL, 'Pasifler', 'desc'),
    _k('lcr_yp', 'Likidite Karşılama Oranı (LCR, YP)', 'rasyo', 'stok', '%', _BL, 'Pasifler', 'desc'),
    _k('serbest_karsilik', 'Serbest Karşılık Bakiyesi', 'buyukluk', 'stok', 'TL', _BL, 'Pasifler', 'desc', True),
    _k('tufex_tamponu', 'TÜFEX Tamponu', 'buyukluk', 'akim', 'TL', _GT, None, 'desc', True),
    _k('kar_tamponu_net_kar', 'Kâr Tamponu (Serbest Karşılık + TÜFEX) / Net Dönem Kârı', 'rasyo', 'akim', '%', _GT, None, 'desc'),
]

# Seçicide "Rekabet Analizi" kategorisi altında gruplanır (2026-10-06): ölçünün asıl yeri (bilanço/gelir tablosu)
# yerine çalışmanın konu başlıkları kullanılır. Gruplar seçicide bu sırayla görünür.
KATEGORI = 'Rekabet Analizi'
ALT_KATEGORILER = {
    'Zorunlu Karşılık ve Marj': ['zorunlu_karsilik_geliri', 'zk_faiz_gelirleri_orani', 'tcmb_hesabi_getirili_aktif',
                                 'ortuk_tcmb_getirisi', 'zk_haric_getirili_aktif_getirisi', 'zk_surukleme',
                                 'nim_getirili_aktif', 'nim_swap_duzeltilmis'],
    'Donuk Alacak ve Karşılıklar': ['donuk_tahsilat_intikal', 'donuk_portfoy_temizligi', 'donuk_net_olusum',
                                    'npl_3_asama_karsilama', 'grup_2_karsilama'],
    'Gider ve Verimlilik': ['faaliyet_gelirleri', 'net_ucret_faaliyet_gelirleri', 'personel_basina_opex',
                            'sube_basina_opex', 'personel_sayisi_yoy', 'personel_basina_personel_gideri_yoy',
                            'personel_basina_opex_yoy'],
    'Kârlılık Bileşimi': ['vergi_oncesi_kar', 'efektif_vergi_orani', 'istirak_kari_vergi_oncesi_kar',
                          'net_kar_yoy_buyumesi', 'reel_net_kar_buyumesi', 'turev_kar_zarar', 'kambiyo_kar_zarar'],
    'Döviz, Altın ve Fonlama': ['yp_toplam_fonlama_payi', 'krediler_toplam_fonlama', 'altin_vadesiz_payi',
                                'yp_fonlama_fazlasi_aktif'],
    'Sermaye ve Likidite': ['rav_yogunlugu', 'basit_kaldirac', 'basel_kaldirac_orani', 'lcr', 'lcr_yp'],
    'Kâr Tamponu': ['serbest_karsilik', 'tufex_tamponu', 'kar_tamponu_net_kar'],
}
_ALT_BY_ID = {mid: alt for alt, ids in ALT_KATEGORILER.items() for mid in ids}
_SIRA = {mid: i for i, mid in enumerate(m for ids in ALT_KATEGORILER.values() for m in ids)}
for _m in KATALOG:
    _m['kategori'] = KATEGORI
    _m['alt_kategori'] = _ALT_BY_ID[_m['id']]
KATALOG.sort(key=lambda m: _SIRA[m['id']])

IDS = [k['id'] for k in KATALOG]
