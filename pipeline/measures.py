"""
pipeline.measures
==================
Tüm measure'ların formülleri burada — banka × tarih × kalem girdisinden tek
sayı (veya None) döndüren küçük fonksiyonlar.

Yapı:
- `MEASURE_FUNCS`: id → fonksiyon. Pipeline buradan iterate eder.
- `BASELINE_PASSTHROUGH`: ham veride bulunmayan / direkt hesaplanmış halde
  gelen kalemler (SYR, Çekirdek SYR, RWA-bağımlı rasyolar). Bunlar
  `compute_all` tarafından `base_data`'dan kopyalanır.

Bir formül None döndürürse pipeline bunu da None olarak yazar (raw'dan
hesaplanamadığını belirtir).
"""
from __future__ import annotations
from typing import Callable, Dict, Set
from .lookup import (
    LookupContext, safe_ratio,
    krediler, faiz_getirili_aktif, maliyetli_pasif,
    ttm_flow, avg_balance,
)


# ============================================================
# YARDIMCI: Yapısal kalem hesapları
# ============================================================

def _tk_breakdown(ctx, b, t, category):
    """Tüketici Kredileri tablosundan kategori bazlı toplam (Tüketici + Personel × TP/YP/DE)."""
    s = 0.0
    for prefix in ['Tüketici Kredileri', 'Personel Kredileri']:
        for ccy in ['TP', 'YP', 'Dövize Endeksli']:
            s += ctx.tk_detay(b, t, f'{prefix} - {ccy}, {category}')
    return s


def _grup2_kategori(ctx, b, t, prefix):
    """Grup 2 (Yakın İzlemedeki) için verilen prefix'in toplamı.
    PBI: A (Krediler ve Diğer Alacaklar) + B (Ödeme Planı Uzatılan) + C (Diğer).
    (Eskiden C='..., Diğer' eksikti — birçok bankada hatalı sonuç veriyordu.)"""
    return (
        ctx.grup12(b, t, f'{prefix}, Yakın İzlemedeki, Krediler ve Diğer Alacaklar')
      + ctx.grup12(b, t, f'{prefix}, Yakın İzlemedeki, Ödeme Planının Uzatılmasına Yönelik Değişiklik Yapılanlar')
      + ctx.grup12(b, t, f'{prefix}, Yakın İzlemedeki, Diğer')
    )


# ---- Faz 5 yardımcıları (PBI uyumu) ----
LEASING_KALEM = 'Kiralama İşlemlerinden Alacaklar'


def leasing(ctx, b, t):
    """PBI [Leasing] = Kiralama İşlemlerinden Alacaklar (Bilanço, Toplam)."""
    return ctx.bilanco(b, t, LEASING_KALEM)


def toplam_krediler_net_leasing(ctx, b, t):
    """PBI 'Toplam Krediler' paydası = Toplam Brüt Krediler − Leasing."""
    return krediler(ctx, b, t) - leasing(ctx, b, t)


def tuketici_kredileri_kk_haric(ctx, b, t):
    """PBI 'Tüketici Kredileri (KK Hariç)' = [Tüketici Kr. ve Bireysel KK] − [Bireysel KK]
    = Tüketici(TP/DE/YP) + Personel(TP/DE/YP) + Kredili Mevduat Hesabı(TP+YP). Kartlar hariç.
    Not: 'Personel Kredileri - YP, Toplam ' kaleminde sonda boşluk var (BDDK ham)."""
    kalemler = [
        'Tüketici Kredileri - TP, Toplam',
        'Tüketici Kredileri - Dövize Endeksli, Toplam',
        'Tüketici Kredileri - YP, Toplam',
        'Personel Kredileri - TP, Toplam',
        'Personel Kredileri - Dövize Endeksli, Toplam',
        'Personel Kredileri - YP, Toplam ',
        'Kredili Mevduat Hesabı - TP',
        'Kredili Mevduat Hesabı - YP',
    ]
    return sum(ctx.tk_detay(b, t, k) for k in kalemler)


def _diger_aktifler_kompozit(ctx, b, t):
    """PBI 'Diğer Aktifler' (nihai, Faz 5 Gün 2) = aşağıdaki 5 Bilanço (Toplam) kalemi.
    Karar: 'Yatırım Amaçlı Gayrimenkuller (Net)' BİR kez sayılır (eski PBI'daki mükerrer iptal).
    'Ortaklık Yatırımları' ve 'Satış Amaç. Elde Tut. Ve Durdu. Faal. İliş. Dv' formülden çıkarıldı."""
    kalemler = [
        'Maddi Duran Varlıklar (Net)',
        'Maddi Olmayan Duran Varlıklar (Net)',
        'Yatırım Amaçlı Gayrimenkuller (Net)',
        'Diğer Aktifler',
        'Vergi Varlığı',
    ]
    return sum(ctx.bilanco(b, t, k) for k in kalemler)


def _aktiften_silinen(ctx, b, t):
    """Donuk akım tablosundan toplam aktiften silinen (negatif gelir)."""
    return sum(
        ctx.donuk_akim(b, t, f'Donuk Alacaklar ({sinif}, Aktiften Silinen)')
        for sinif in ['Sınırlı', 'Şüpheli', 'Zarar Niteliğinde']
    )


def _menkul_kiymetler(ctx, b, t):
    """
    PowerBI referans tanımı (2026-08-12'de kullanıcının paylaştığı DAX
    formülüyle birebir hizalandı — TFRS9 muhasebe sınıflandırması bazlı):
    Gerçeğe Uygun D. Farkı K/Z Yan.FV (Net) + Gerçeğe Uygun Değer Farkı
    Diğer Kapsamlı Gelire Yansıtılan FV + İtfa Edilmiş Maliyetle Ölçülen FV
    + Türev Finansal Varlıklar + Satılmaya Hazır FV (Net, eski/pre-TFRS9
    dönemler için) + Vadeye Kadar Elde Tutulacak Yatırımlar (Net, eski
    dönemler için).

    ÖNCEKİ (v29) tanım "ürün türü" bazlıydı (Devlet Borçlanma Senetleri +
    Diğer Menkul Değerler + Sermayede Payı Temsil Eden MD + Türev FV +
    Diğer FV) — sayısal olarak genelde örtüşüyordu (aynı finansal varlık
    havuzunun farklı kesitler/kırılımlar üzerinden toplamı) ama PowerBI'nin
    kullandığı TFRS9-bazlı kalemler BDDK Ana Tablo'nun birincil satırları
    olduğundan bu tanım tercih edildi.
    """
    return (
        ctx.bilanco(b, t, 'Gerçeğe Uygun D. Farkı K/Z Yan.Fv (Net)')
      + ctx.bilanco(b, t, 'Gerçeğe Uygun Değer Farkı Diğer Kapsamlı Gelire Yansıtılan Finansal Varlıklar')
      + ctx.bilanco(b, t, 'İtfa Edilmiş Maliyeti ile Ölçülen Finansal Varlıklar')
      + ctx.bilanco(b, t, 'Türev Finansal Varlıklar')
      + ctx.bilanco(b, t, 'Satılmaya Hazır Finansal Varlıklar (Net)')
      + ctx.bilanco(b, t, 'Vadeye Kadar Elde Tutulacak Yatırım.(Net)')
    )


def _net_donem_kari(ctx, b, t):
    return ctx.gelir(b, t, 'Net Dönem Karı / Zararı')


def _ttm(ctx, b, t, kalem_fn):
    return ttm_flow(ctx, b, t, kalem_fn)


def _avg(ctx, b, t, stock_fn):
    return avg_balance(ctx, b, t, stock_fn)


# ============================================================
# BÜYÜKLÜKLER — Bilanço Aktifler
# ============================================================

def m_toplam_aktifler(ctx, b, t): return ctx.bilanco(b, t, 'Toplam Aktifler')
def m_krediler(ctx, b, t):        return krediler(ctx, b, t)
def m_donuk_alacaklar(ctx, b, t): return ctx.bilanco(b, t, 'Donuk Alacaklar')


def m_konut_kredileri(ctx, b, t):  return _tk_breakdown(ctx, b, t, 'Konut Kredisi')
def m_tasit_kredileri(ctx, b, t):  return _tk_breakdown(ctx, b, t, 'Taşıt Kredisi')
def m_ihtiyac_kredileri(ctx, b, t): return _tk_breakdown(ctx, b, t, 'İhtiyaç Kredisi')


def m_tuketici_kredileri(ctx, b, t):
    return ctx.tk_detay(b, t, 'Krediler ve K. Kartları (Tüketici ve Personel, Toplam)')


def m_bireysel_kredi_kartlari(ctx, b, t):
    return sum(
        ctx.tk_detay(b, t, k) for k in [
            'Bireysel Kredi Kartları - TP, Toplam',
            'Bireysel Kredi Kartları - YP, Toplam',
            'Personel Kredi Kartları - TP, Toplam',
            'Personel Kredi Kartları - YP, Toplam',
        ]
    )


def m_tuzel_krediler(ctx, b, t):
    return krediler(ctx, b, t) - m_tuketici_kredileri(ctx, b, t)


def m_grup_2_krediler(ctx, b, t):
    return (
        ctx.grup12(b, t, 'Toplam, Yakın İzlemedeki, Krediler ve Diğer Alacaklar')
      + ctx.grup12(b, t, 'Toplam, Yakın İzlemedeki, Ödeme Planının Uzatılmasına Yönelik Değişiklik Yapılanlar')
      + ctx.grup12(b, t, 'Toplam, Yakın İzlemedeki, Diğer')
    )


def m_grup_1_krediler(ctx, b, t):
    return krediler(ctx, b, t) - ctx.bilanco(b, t, 'Donuk Alacaklar') - m_grup_2_krediler(ctx, b, t)


def m_grup_2_krediler_cekirdek_sermaye(ctx, b, t):
    """Grup 2 (Yakın İzlemedeki) Krediler / Çekirdek Sermaye (CET1) (%).
    Pay: m_grup_2_krediler (mevcut). Payda: 'Çekirdek Sermaye Toplamı'
    (ctx.sermaye = sermaye yeterliliği tablosu)."""
    return safe_ratio(
        m_grup_2_krediler(ctx, b, t),
        ctx.sermaye(b, t, 'Çekirdek Sermaye Toplamı'),
    )


# --- Kur Riski: YP kredi kompozisyonu (Ana Ortaklık kur riski tablosu) ---
# NOT: kalem adlarında virgülden ÖNCE boşluk var ('Krediler , USD'). Birebir.
# Kalemler yalnız 'Ana Ortaklık Bankanın Kur Riskine İlişkin Bilgiler' tablosunda
# (kur_konsolide). DAX'te Tablo filtresi yok ama çift-sayım olmuyor (Banka'nın
# tablosunda bu kredi kalemleri bulunmuyor). Para Birimi='Toplam'.
_KUR_KREDI_USD = 'Kur Riski, Varlıklar (Krediler , USD)'
_KUR_KREDI_EURO = 'Kur Riski, Varlıklar (Krediler , EURO)'
_KUR_KREDI_TOPLAM = 'Kur Riski, Varlıklar (Krediler , Toplam)'


def m_usd_yp_krediler(ctx, b, t):
    """USD Cinsi Krediler / YP Brüt Krediler (%)."""
    return safe_ratio(
        ctx.kur_konsolide(b, t, _KUR_KREDI_USD),
        ctx.kur_konsolide(b, t, _KUR_KREDI_TOPLAM),
    )


def m_euro_yp_krediler(ctx, b, t):
    """EURO Cinsi Krediler / YP Brüt Krediler (%)."""
    return safe_ratio(
        ctx.kur_konsolide(b, t, _KUR_KREDI_EURO),
        ctx.kur_konsolide(b, t, _KUR_KREDI_TOPLAM),
    )


# --- YP Net Genel Pozisyonu / Regülasyon Özkaynağı (Faz 6+, PBI DAX) ---
# Pay: Net Bilanço Pozisyonu + Net Nazım Hesap Pozisyonu (Ana Ortaklık kur tablosu,
#   kur_konsolide). Pozisyon NEGATİF (kısa) ya da POZİTİF (uzun) olabilir → oran ±.
# Payda: 'Toplam Ozkaynaklar' (regülasyon özk.; ozkaynak_detay tablosu) — bilanço
#   'Özkaynaklar'ı DEĞİL. Kalem adı düz 'O', 'ı'sız ('Ozkaynaklar') — birebir.
_KUR_YP_NET_BILANCO = 'Kur Riski, Yükümlülükler (Net Bilanço Pozisyonu, Toplam)'
_KUR_YP_NET_NAZIM = 'Kur Riski, Yükümlülükler (Net Nazım Hesap Pozisyonu, Toplam)'


def _yp_net_genel_pozisyon(ctx, b, t):
    """YP Net Genel Pozisyonu = Net Bilanço Pozisyonu + Net Nazım Hesap Pozisyonu
    (Ana Ortaklık Bankanın Kur Riskine İlişkin Bilgiler, PB='Toplam')."""
    return (
        ctx.kur_konsolide(b, t, _KUR_YP_NET_BILANCO)
        + ctx.kur_konsolide(b, t, _KUR_YP_NET_NAZIM)
    )


def m_yp_net_pozisyon_ozkaynak(ctx, b, t):
    """Yabancı Para Net Genel Pozisyonu / Toplam Özkaynaklar (Ana+Katkı Sermaye) (%).
    Payda = ctx.ozkaynak_detay('Toplam Ozkaynaklar') (regülasyon özkaynağı)."""
    return safe_ratio(
        _yp_net_genel_pozisyon(ctx, b, t),
        ctx.ozkaynak_detay(b, t, 'Toplam Ozkaynaklar'),
    )


def m_donuk_alacaklar_satis_terkin_oncesi(ctx, b, t):
    return ctx.bilanco(b, t, 'Donuk Alacaklar') - _aktiften_silinen(ctx, b, t)


# ============================================================
# BÜYÜKLÜKLER — Bilanço Pasifler & Bilanço Dışı
# ============================================================

def m_mevduat(ctx, b, t):     return ctx.bilanco(b, t, 'Mevduat')
def m_vadesiz_mevduat(ctx, b, t): return ctx.vadesiz_mevduat(b, t)
def m_ozkaynaklar(ctx, b, t): return ctx.bilanco(b, t, 'Özkaynaklar')


def m_gayrinakdi_krediler(ctx, b, t):
    """v29 PBI tanımı raw 'Garanti Ve Kefaletler, Toplam' ile tam eşleşmiyor —
    bu measure BASELINE_PASSTHROUGH'da. Burada placeholder."""
    return None


# ============================================================
# BÜYÜKLÜKLER — Gelir Tablosu
# ============================================================

def m_faiz_gelirleri(ctx, b, t):           return ctx.gelir(b, t, 'Faiz Gelirleri')
def m_faiz_giderleri(ctx, b, t):           return ctx.gelir(b, t, 'Faiz Giderleri')
def m_net_faiz_geliri(ctx, b, t):          return ctx.gelir(b, t, 'Net Faiz Geliri/Gideri')
def m_alinan_ucret_komisyonlar(ctx, b, t): return ctx.gelir(b, t, 'Alınan Ücret Ve Komisyonlar')
def m_verilen_ucret_komisyonlar(ctx, b, t): return ctx.gelir(b, t, 'Verilen Ücret Ve Komisyonlar')
def m_net_ucret_komisyonlar(ctx, b, t):    return ctx.gelir(b, t, 'Net Ücret Ve Komisyon Gelirleri/Giderleri')
def m_net_ticari_kar(ctx, b, t):           return ctx.gelir(b, t, 'Ticari Kar/Zarar (Net)')
def m_personel_giderleri(ctx, b, t):       return ctx.gelir(b, t, 'Personel Giderleri (-)')
def m_diger_faaliyet_giderleri(ctx, b, t): return ctx.gelir(b, t, 'Diğer Faaliyet Giderleri (-)')
def m_karsilik_giderleri(ctx, b, t):       return ctx.gelir(b, t, 'Kredi Ve Diğer Alacaklar Değer Düşüş Karşılığı (-)')
def m_net_donem_kari(ctx, b, t):           return _net_donem_kari(ctx, b, t)
def m_brut_faaliyet_kari(ctx, b, t):       return ctx.gelir(b, t, 'Net Faaliyet Karı/Zararı')
def m_reklam_giderleri(ctx, b, t):         return ctx.faaliyet_gid_detay(b, t, 'Reklam ve İlan Giderleri')
def m_gnakdi_alinan_ucret_komisyonlar(ctx, b, t): return ctx.gelir(b, t, 'Gayri Nakdi Kredilerden')


# ============================================================
# BÜYÜKLÜKLER — Şube & Personel
# ============================================================

def m_sube_sayisi(ctx, b, t):     return ctx.sube(b, t, 'Şube Sayısı')
def m_personel_sayisi(ctx, b, t): return ctx.sube(b, t, 'Personel Sayısı')


# ============================================================
# RASYOLAR — Bilanço Aktifler
# ============================================================

def m_krediler_ta(ctx, b, t):
    return safe_ratio(krediler(ctx, b, t), ctx.bilanco(b, t, 'Toplam Aktifler'))


def m_krediler_mevduat(ctx, b, t):
    return safe_ratio(krediler(ctx, b, t), ctx.bilanco(b, t, 'Mevduat'))


def m_npl_rasyosu(ctx, b, t):
    return safe_ratio(ctx.bilanco(b, t, 'Donuk Alacaklar'), krediler(ctx, b, t))


def m_npl_rasyosu_satis_terkin_oncesi(ctx, b, t):
    silinen_abs = abs(_aktiften_silinen(ctx, b, t))
    pay = ctx.bilanco(b, t, 'Donuk Alacaklar') + silinen_abs
    payda = krediler(ctx, b, t) + silinen_abs
    return safe_ratio(pay, payda)


def m_grup_1_krediler_toplam(ctx, b, t):
    """2026-08-14: payda measures.docx DAX'ıyla hizalandı — 'Grup 1 Krediler /
    Toplam Brüt Krediler' (önceden 'Krediler Ve Alacaklar (Toplam)' tek satırı
    kullanılıyordu, Faktoring/Kiralama/Donuk/Takipteki hariçti)."""
    return safe_ratio(m_grup_1_krediler(ctx, b, t), _brut_krediler(ctx, b, t))


def m_grup_2_krediler_toplam(ctx, b, t):
    return safe_ratio(m_grup_2_krediler(ctx, b, t), toplam_krediler_net_leasing(ctx, b, t))


def m_grup_2_tuketici_tuketici(ctx, b, t):
    g2_tuk = _grup2_kategori(ctx, b, t, 'Tüketici Kredileri')
    return safe_ratio(g2_tuk, tuketici_kredileri_kk_haric(ctx, b, t))


def m_grup_2_tuzel_tuzel(ctx, b, t):
    g2_total = m_grup_2_krediler(ctx, b, t)
    g2_kart = _grup2_kategori(ctx, b, t, 'Kredi Kartları')
    g2_tuk = _grup2_kategori(ctx, b, t, 'Tüketici Kredileri')
    g2_mali = _grup2_kategori(ctx, b, t, 'Mali Kesime Verilen Krediler')
    return safe_ratio(g2_total - g2_kart - g2_tuk - g2_mali, m_tuzel_krediler(ctx, b, t))


def m_konut_tuketici(ctx, b, t):
    return safe_ratio(m_konut_kredileri(ctx, b, t), m_tuketici_kredileri(ctx, b, t))


def m_tasit_tuketici(ctx, b, t):
    return safe_ratio(m_tasit_kredileri(ctx, b, t), m_tuketici_kredileri(ctx, b, t))


def m_tuketici_toplam(ctx, b, t):
    """2026-08-14: payda DAX'a göre Toplam Brüt Krediler (bkz. m_grup_1_krediler_toplam notu)."""
    return safe_ratio(m_tuketici_kredileri(ctx, b, t), _brut_krediler(ctx, b, t))


def m_tuzel_toplam(ctx, b, t):
    """2026-08-14: payda DAX'a göre Toplam Brüt Krediler."""
    return safe_ratio(m_tuzel_krediler(ctx, b, t), _brut_krediler(ctx, b, t))


def m_ihtiyac_toplam(ctx, b, t):
    """2026-08-14: payda DAX'a göre Toplam Brüt Krediler."""
    return safe_ratio(m_ihtiyac_kredileri(ctx, b, t), _brut_krediler(ctx, b, t))


def m_bkk_toplam(ctx, b, t):
    """2026-08-14: payda DAX'a göre Toplam Brüt Krediler."""
    return safe_ratio(m_bireysel_kredi_kartlari(ctx, b, t), _brut_krediler(ctx, b, t))


def m_konut_tp_pasifler(ctx, b, t):
    tp_pas_oz_haric = ctx.bilanco(b, t, 'Toplam Pasifler', 'TP') - ctx.bilanco(b, t, 'Özkaynaklar', 'TP')
    return safe_ratio(m_konut_kredileri(ctx, b, t), tp_pas_oz_haric)


def m_tp_aktifler_ta(ctx, b, t):
    return safe_ratio(ctx.bilanco(b, t, 'Toplam Aktifler', 'TP'), ctx.bilanco(b, t, 'Toplam Aktifler'))


def m_tp_krediler_toplam(ctx, b, t):
    """2026-08-14: DAX'a göre 'TP Brüt Krediler / Toplam Brüt Krediler'."""
    return safe_ratio(_brut_krediler(ctx, b, t, 'TP'), _brut_krediler(ctx, b, t))


def m_yp_krediler_toplam(ctx, b, t):
    """PBI [YP Krediler/ Toplam Krediler] = [YP Brüt Krediler]/[Toplam Brüt Krediler]."""
    return safe_ratio(_brut_krediler(ctx, b, t, 'YP'), _brut_krediler(ctx, b, t))


def m_yp_aktifler_toplam_pasifler(ctx, b, t):
    # PBI: YP Aktifler / YP Pasifler (payda PB=YP). Eskiden payda Toplam idi.
    return safe_ratio(ctx.bilanco(b, t, 'Toplam Aktifler', 'YP'),
                      ctx.bilanco(b, t, 'Toplam Pasifler', 'YP'))


def m_diger_aktifler_ta(ctx, b, t):
    # PBI: numerator = çoklu bilanço kalemi toplamı (_diger_aktifler_kompozit), tek satır değil.
    return safe_ratio(_diger_aktifler_kompozit(ctx, b, t), ctx.bilanco(b, t, 'Toplam Aktifler'))


def m_finansal_varliklar_net_ta(ctx, b, t):
    fv = (ctx.bilanco(b, t, 'Finansal Varlıklar (Net)')
        + ctx.bilanco(b, t, 'İtfa Edilmiş Maliyeti ile Ölçülen Finansal Varlıklar'))
    return safe_ratio(fv, ctx.bilanco(b, t, 'Toplam Aktifler'))


def m_menkul_kiymetler_ta(ctx, b, t):
    return safe_ratio(_menkul_kiymetler(ctx, b, t), ctx.bilanco(b, t, 'Toplam Aktifler'))


def m_ortaklik_yatirimlari_ta(ctx, b, t):
    return safe_ratio(ctx.bilanco(b, t, 'Ortaklık Yatırımları'), ctx.bilanco(b, t, 'Toplam Aktifler'))


def m_npl_karsilama_orani(ctx, b, t):
    karsilik = abs(ctx.bilanco(b, t, 'Beklenen Zarar Karşılıkları (-)'))
    return safe_ratio(karsilik, ctx.bilanco(b, t, 'Donuk Alacaklar'))


def m_mali_kesim_toplam(ctx, b, t):
    """2026-08-14: payda DAX'a göre Toplam Brüt Krediler."""
    mk = ctx.grup12(b, t, 'Mali Kesime Verilen Krediler,  Standart Nitelikli Krediler, Toplam')
    return safe_ratio(mk, _brut_krediler(ctx, b, t))


def m_dis_ticaret_toplam(ctx, b, t):
    """2026-08-14: payda DAX'a göre Toplam Brüt Krediler."""
    toplam = 0.0
    for kategori in ['İhracat Kredileri', 'İthalat Kredileri']:
        toplam += ctx.grup12(b, t, f'{kategori},  Standart Nitelikli Krediler, Toplam')
        toplam += _grup2_kategori(ctx, b, t, kategori)
    return safe_ratio(toplam, _brut_krediler(ctx, b, t))


# ============================================================
# RASYOLAR — Bilanço Pasifler
# ============================================================

def m_vadesiz_mevduat_toplam_mevduat(ctx, b, t):
    return safe_ratio(ctx.vadesiz_mevduat(b, t), ctx.bilanco(b, t, 'Mevduat'))


def m_tp_mevduat_toplam_mevduat(ctx, b, t):
    return safe_ratio(ctx.bilanco(b, t, 'Mevduat', 'TP'), ctx.bilanco(b, t, 'Mevduat'))


# ============================================================
# RASYOLAR — Gelir Tablosu (YtD)
# ============================================================

def m_komisyon_gid_gel(ctx, b, t):
    vk = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Verilen Ücret Ve Komisyonlar'))
    ak = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Alınan Ücret Ve Komisyonlar'))
    return safe_ratio(vk, ak)


def m_faiz_gideri_faiz_geliri(ctx, b, t):
    fgd = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Faiz Giderleri'))
    fg = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Faiz Gelirleri'))
    return safe_ratio(fgd, fg)


def m_personel_net_kar(ctx, b, t):
    pg = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Personel Giderleri (-)'))
    nk = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Dönem Karı / Zararı'))
    return safe_ratio(pg, nk)


def m_reklam_net_kar(ctx, b, t):
    rg = _ttm(ctx, b, t, lambda bb, tt: ctx.faaliyet_gid_detay(bb, tt, 'Reklam ve İlan Giderleri'))
    nk = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Dönem Karı / Zararı'))
    return safe_ratio(rg, nk)


def m_net_ucret_operasyonel(ctx, b, t):
    nuk = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Ücret Ve Komisyon Gelirleri/Giderleri'))
    dfg = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Diğer Faaliyet Giderleri (-)'))
    return safe_ratio(nuk, dfg)


def m_maliyet_gelir(ctx, b, t):
    """Operasyonel Gider TTM / Operasyonel Gelir TTM × 100."""
    def maliyet(bb, tt):
        return (ctx.gelir(bb, tt, 'Diğer Faaliyet Giderleri (-)')
              + ctx.gelir(bb, tt, 'Personel Giderleri (-)'))
    def gelir(bb, tt):
        return (ctx.gelir(bb, tt, 'Net Faiz Geliri/Gideri')
              + ctx.gelir(bb, tt, 'Net Ücret Ve Komisyon Gelirleri/Giderleri')
              + ctx.gelir(bb, tt, 'Ticari Kar/Zarar (Net)'))
    return safe_ratio(_ttm(ctx, b, t, maliyet), _ttm(ctx, b, t, gelir))


def m_gayrinakdi_komisyon_gayrinakdi(ctx, b, t):
    """Gayri Nakdi Komisyon Geliri / Gayri Nakdi Krediler — gayrinakdi PBI tanımına bağlı."""
    return None  # gayrinakdi_krediler baseline'a düşüyor; bu da baseline'dan


# ============================================================
# RASYOLAR — Annualized (TTM + avg balance)
# ============================================================

def m_roaa(ctx, b, t):
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Dönem Karı / Zararı'))
    avg = _avg(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Toplam Aktifler'))
    return safe_ratio(ttm, avg)


def m_roae(ctx, b, t):
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Dönem Karı / Zararı'))
    avg = _avg(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Özkaynaklar'))
    return safe_ratio(ttm, avg)


def m_nim(ctx, b, t):
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Faiz Geliri/Gideri'))
    avg = _avg(ctx, b, t, lambda bb, tt: faiz_getirili_aktif(ctx, bb, tt))
    return safe_ratio(ttm, avg)


def m_nim_bzk_sonrasi(ctx, b, t):
    def nf_minus_prov(bb, tt):
        return (ctx.gelir(bb, tt, 'Net Faiz Geliri/Gideri')
              - ctx.gelir(bb, tt, 'Kredi Ve Diğer Alacaklar Değer Düşüş Karşılığı (-)'))
    ttm = _ttm(ctx, b, t, nf_minus_prov)
    avg = _avg(ctx, b, t, lambda bb, tt: faiz_getirili_aktif(ctx, bb, tt))
    return safe_ratio(ttm, avg)


def m_cost_of_risk(ctx, b, t):
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Kredi Ve Diğer Alacaklar Değer Düşüş Karşılığı (-)'))
    avg = _avg(ctx, b, t, lambda bb, tt: krediler(ctx, bb, tt))
    return safe_ratio(ttm, avg)


def m_faaliyet_gid_ort_aktif(ctx, b, t):
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Diğer Faaliyet Giderleri (-)'))
    avg = _avg(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Toplam Aktifler'))
    return safe_ratio(ttm, avg)


def m_personel_ort_aktif(ctx, b, t):
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Personel Giderleri (-)'))
    avg = _avg(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Toplam Aktifler'))
    return safe_ratio(ttm, avg)


def m_reklam_ort_aktif(ctx, b, t):
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.faaliyet_gid_detay(bb, tt, 'Reklam ve İlan Giderleri'))
    avg = _avg(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Toplam Aktifler'))
    return safe_ratio(ttm, avg)


def m_net_ucret_ort_aktif(ctx, b, t):
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Ücret Ve Komisyon Gelirleri/Giderleri'))
    avg = _avg(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Toplam Aktifler'))
    return safe_ratio(ttm, avg)


def m_faiz_getirili_aktif_getirisi(ctx, b, t):
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Faiz Gelirleri'))
    avg = _avg(ctx, b, t, lambda bb, tt: faiz_getirili_aktif(ctx, bb, tt))
    return safe_ratio(ttm, avg)


def m_faiz_maliyetli_pasif_maliyeti(ctx, b, t):
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Faiz Giderleri'))
    avg = _avg(ctx, b, t, lambda bb, tt: maliyetli_pasif(ctx, bb, tt))
    return safe_ratio(ttm, avg)


def m_kaynak_pacal_maliyet(ctx, b, t):
    return m_faiz_maliyetli_pasif_maliyeti(ctx, b, t)


def m_spread(ctx, b, t):
    a = m_faiz_getirili_aktif_getirisi(ctx, b, t)
    p = m_faiz_maliyetli_pasif_maliyeti(ctx, b, t)
    if a is None or p is None: return None
    return a - p


def m_kredi_pacal_getiri(ctx, b, t):
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Kredilerden Alınan Faizler'))
    avg = _avg(ctx, b, t, lambda bb, tt: krediler(ctx, bb, tt))
    return safe_ratio(ttm, avg)


def m_kredi_mevduat_spread(ctx, b, t):
    kg = m_kredi_pacal_getiri(ctx, b, t)
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Mevduata Verilen Faizler'))
    avg = _avg(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Mevduat'))
    mm = safe_ratio(ttm, avg)
    if kg is None or mm is None: return None
    return kg - mm


def m_donuk_intikal_ort_krediler(ctx, b, t):
    """Donuk Alacaklar (Dönem İçi İntikal) / Ortalama Brüt Krediler (%).
    Pay: Σ İntikal (3 Dönem İçi İntikal + 2 Diğer Giriş) = _NPL_INTIKAL_ITEMS,
      dönem YtD değeri (TTM DEĞİL — PBI DAX birebir).
    Payda: gerçek 12-ay ort. brüt kredi (avg_balance, _brut_krediler)."""
    intikal = sum(ctx.donuk_akim(b, t, k) for k in _NPL_INTIKAL_ITEMS)
    ort_brut = avg_balance(ctx, b, t, lambda bb, tt: _brut_krediler(ctx, bb, tt))
    return safe_ratio(intikal, ort_brut)


def m_donuk_tahsilat_ort_krediler(ctx, b, t):
    """Donuk Alacaklar (Dönem İçi Tahsilat) / Ortalama Brüt Krediler (%).
    Pay: Σ Tahsilat (3 Dönem İçi Tahsilat + 2 Diğer Çıkış) = _NPL_TAHSILAT_ITEMS,
      dönem YtD; ham veride NEGATİF. DAX sonundaki *-1 ile pozitif gösterilir.
    Payda: gerçek 12-ay ort. brüt kredi (avg_balance, _brut_krediler)."""
    tahsilat = sum(ctx.donuk_akim(b, t, k) for k in _NPL_TAHSILAT_ITEMS)
    ort_brut = avg_balance(ctx, b, t, lambda bb, tt: _brut_krediler(ctx, bb, tt))
    r = safe_ratio(tahsilat, ort_brut)
    return None if r is None else -r


# ============================================================
# RASYOLAR — Faiz Getirili Aktif Yapısı
# ============================================================

def _faiz_getirili_aktif_detay(ctx, b, t):
    """Faiz (Kar Payı) Getirili Aktifler — PBI detaylı tanım (13 bileşen):
    TCMB Hesabı (TP+YP) + Bankalar + Para Piyasalarından Alacaklar
    + FVTPL (K/Z Yan. Net) + FVOCI + İtfa Edilmiş Maliyet + SatHazır(legacy)
    + VKET(legacy) + Türev FV + Hedge Türev FV + Toplam Brüt Krediler
    − |Beklenen Zarar Karşılıkları|.
    NOT: BZK ham veride negatif; PBI [BZK(Bilanço)]*-1 = karşılığı düşmek →
    burada -abs() ile (mevcut _nd_npl_karsilama konvansiyonu)."""
    return (
        ctx.tcmb(b, t, 'TCMB Hesabı, (TP)')
        + ctx.tcmb(b, t, 'TCMB Hesabı, (YP)')
        + ctx.bilanco(b, t, 'Bankalar')
        + ctx.bilanco(b, t, 'Para Piyasalarından Alacaklar')
        + ctx.bilanco(b, t, 'Gerçeğe Uygun D. Farkı K/Z Yan.Fv (Net)')
        + ctx.bilanco(b, t, 'Gerçeğe Uygun Değer Farkı Diğer Kapsamlı Gelire Yansıtılan Finansal Varlıklar')
        + ctx.bilanco(b, t, 'İtfa Edilmiş Maliyeti ile Ölçülen Finansal Varlıklar')
        + ctx.bilanco(b, t, 'Satılmaya Hazır Finansal Varlıklar (Net)')
        + ctx.bilanco(b, t, 'Vadeye Kadar Elde Tutulacak Yatırım.(Net)')
        + ctx.bilanco(b, t, 'Türev Finansal Varlıklar')
        + ctx.bilanco(b, t, 'Riskten Korunma Amaçlı Türev Fv')
        + _brut_krediler(ctx, b, t)
        - abs(ctx.bilanco(b, t, 'Beklenen Zarar Karşılıkları (-)'))
    )


def m_faiz_getirili_ta(ctx, b, t):
    """Faiz (Kar Payı) Getirili Aktifler / Toplam Aktifler (%)."""
    return safe_ratio(_faiz_getirili_aktif_detay(ctx, b, t),
                       ctx.bilanco(b, t, 'Toplam Aktifler'))


def m_faiz_getirili_maliyetli(ctx, b, t):
    """Faiz (Kar Payı) Getirili Aktifler / Faiz (Kar Payı) Maliyetli Pasifler (%).
    PBI DAX birebir: pay = _faiz_getirili_aktif_detay (13 bileşen — faiz_getirili_ta
    ile aynı pay), payda = _faiz_maliyetli_pasif_detay (9 bileşen — maliyetli_pasifler_
    toplam_pasifler ile aynı). NOT: basit faiz_getirili_aktif / maliyetli_pasif
    helper'ları DEĞİL (onlar 4 ve 5 bileşenli, ayrı/paylaşımlı)."""
    return safe_ratio(_faiz_getirili_aktif_detay(ctx, b, t),
                      _faiz_maliyetli_pasif_detay(ctx, b, t),
                      scale=1.0)  # 'kat' gösterimi (×100 yüzde DEĞİL): 2,05 kat


def m_faiz_getirili_ozkaynak(ctx, b, t):
    """Ortalama Faiz (Kar Payı) Getirili Aktifler / Ortalama Özkaynaklar (kat).
    Pay = avg_balance(_faiz_getirili_aktif_detay), Payda = avg_balance(Özkaynaklar).
    NOT (PARALLELPERIOD tuzağı — handover GT#1): PBI DAX (A+PARALLELPERIOD(-12 ay))/2
    kalıbı çeyrek-sonu tarih kolonunda BLANK dönüp /2'ye çökerdi (KT spot 10,54 yanlış).
    Pay ve payda aynı artefakta düşünce /2 sadeleşir → spot oran. Doğrusu gerçek
    12-ay ortalaması (avg_balance) → KT 10,24 → 10,2 kat. scale=1.0 (kat)."""
    pay = avg_balance(ctx, b, t, lambda bb, tt: _faiz_getirili_aktif_detay(ctx, bb, tt))
    payda = avg_balance(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Özkaynaklar'))
    return safe_ratio(pay, payda, scale=1.0)


# ============================================================
# RASYOLAR — Şube/Personel
# ============================================================

def _per_fn(ctx, b, t, num_fn, denom_kalem, annualize=False):
    """Pay büyüklüğü (num_fn) / şube ya da personel sayısı / 1000 (bin TL).
    annualize (2026-08-15): akım (flow) büyüklükleri için TTM ile yıllıklandır.
    BDDK gelir tablosu YtD (yıl başından kümülatif) olduğundan, ara çeyreklerde
    ham değer 3/6/9 aylık kısmi kalır — bu da net kar / personel gideri başına
    ölçülerini yıl sonuna göre yapay küçük gösteriyordu (testere-dişi trend).
    ttm_flow ile son 12 aya çevrilir. Stok büyüklüklerinde (krediler, mevduat)
    anlık değer doğru olduğundan annualize=False (varsayılan)."""
    n = m_personel_sayisi(ctx, b, t) if denom_kalem == 'personel' else m_sube_sayisi(ctx, b, t)
    if not n:
        return None
    if annualize:
        num = ttm_flow(ctx, b, t, lambda bb, tt: num_fn(ctx, bb, tt))
    else:
        num = num_fn(ctx, b, t)
    if num is None:
        return None
    return num / n / 1000


def m_personel_basina_krediler(ctx, b, t):
    return _per_fn(ctx, b, t, lambda c, x, y: krediler(c, x, y), 'personel')


def m_personel_basina_mevduat(ctx, b, t):
    return _per_fn(ctx, b, t, lambda c, x, y: c.bilanco(x, y, 'Mevduat'), 'personel')


def m_personel_basina_net_kar(ctx, b, t):
    """2026-08-15: TTM ile yıllıklandırıldı (akım — bkz. _per_fn notu)."""
    return _per_fn(ctx, b, t, lambda c, x, y: c.gelir(x, y, 'Net Dönem Karı / Zararı'), 'personel', annualize=True)


def m_personel_basina_personel_gideri(ctx, b, t):
    """2026-08-15: TTM ile yıllıklandırıldı (akım — bkz. _per_fn notu)."""
    return _per_fn(ctx, b, t, lambda c, x, y: c.gelir(x, y, 'Personel Giderleri (-)'), 'personel', annualize=True)


def m_sube_basina_krediler(ctx, b, t):
    return _per_fn(ctx, b, t, lambda c, x, y: krediler(c, x, y), 'sube')


def m_sube_basina_mevduat(ctx, b, t):
    return _per_fn(ctx, b, t, lambda c, x, y: c.bilanco(x, y, 'Mevduat'), 'sube')


def m_sube_basina_net_kar(ctx, b, t):
    """2026-08-15: TTM ile yıllıklandırıldı (akım — bkz. _per_fn notu)."""
    return _per_fn(ctx, b, t, lambda c, x, y: c.gelir(x, y, 'Net Dönem Karı / Zararı'), 'sube', annualize=True)


def m_sube_basina_personel(ctx, b, t):
    s = m_sube_sayisi(ctx, b, t); p = m_personel_sayisi(ctx, b, t)
    if not s: return None
    return p / s


# ============================================================
# YENİ MEASURE'LAR (v29 — Phase 1 ile geldi)
# ============================================================

def m_vadeli_mevduat(ctx, b, t):
    return ctx.bilanco(b, t, 'Mevduat') - ctx.vadesiz_mevduat(b, t)


def m_kiymetli_maden_mevduati(ctx, b, t): return ctx.kiymetli_maden(b, t)
def m_resmi_kurumlar_mevduat(ctx, b, t):  return ctx.resmi_kurumlar(b, t)


def m_toplam_kaynak(ctx, b, t):
    """PBI [Toplam Kaynak] = Mevduat + Alınan Krediler + İhraç Edilen Menkul
    Kıymetler (Net) — 2026-08-12 düzeltmesi: 'Para Piyasalarına Borçlar'
    yanlışlıkla eklenmişti (measures.docx DAX'ıyla karşılaştırıldığında
    bulundu; KT'de ~%6,9 fazla gösteriyordu). PBI'de Para Piyasalarına
    Borçlar 'Toplam Fonlama' adlı AYRI bir (bizde implement edilmemiş)
    ölçünün bileşeni — 'Toplam Kaynak'ın değil."""
    return (ctx.bilanco(b, t, 'Mevduat')
          + ctx.bilanco(b, t, 'Alınan Krediler')
          + ctx.bilanco(b, t, 'İhraç Edilen Menkul Kıymetler (Net)'))


# --- Net NPL Formasyon Rasyosu (Faz 6, PBI DAX) ---
# Pay: Net NPL Oluşumu = Σ(Dönem İçi İntikal + Diğer Giriş) + Σ(Dönem İçi Tahsilat + Diğer Çıkış)
#   Tahsilat/Çıkış ham veride NEGATİF → toplama net oluşumu verir (intikal − tahsilat).
_NPL_INTIKAL_ITEMS = [
    'Donuk Alacaklar (Sınırlı, Dönem İçi İntikal)',
    'Donuk Alacaklar (Şüpheli, Dönem İçi İntikal)',
    'Donuk Alacaklar (Zarar Niteliğinde, Dönem İçi İntikal)',
    'Donuk Alacaklar (Şüpheli, Diğer Giriş)',
    'Donuk Alacaklar (Zarar Niteliğinde, Diğer Giriş)',
]
_NPL_TAHSILAT_ITEMS = [
    'Donuk Alacaklar (Sınırlı, Dönem İçi Tahsilat)',
    'Donuk Alacaklar (Şüpheli, Dönem İçi Tahsilat)',
    'Donuk Alacaklar (Zarar Niteliğinde, Dönem İçi Tahsilat)',
    'Donuk Alacaklar (Sınırlı, Diğer Çıkış)',
    'Donuk Alacaklar (Şüpheli, Diğer Çıkış)',
]


def _brut_krediler(ctx, b, t, pb='Toplam'):
    """PBI [Toplam Brüt Krediler] = Krediler Ve Alacaklar + Faktoring Alacakları
    + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler
    (hepsi Bilanço, Para Birimi='Toplam'). NPL dahil = brüt. Not: kalem adı
    'Krediler Ve Alacaklar' (parantezsiz), '(Toplam)' suffix'li olan DEĞİL.
    pb parametresi (2026-08-14): TP/YP Brüt Krediler rasyoları için eklendi —
    PBI DAX 'X Krediler/Toplam Krediler' ailesinde payda hep Toplam Brüt
    Krediler'dir (bkz. m_*_toplam fonksiyonları)."""
    return (
        ctx.bilanco(b, t, 'Krediler Ve Alacaklar', pb)
        + ctx.bilanco(b, t, 'Faktoring Alacakları', pb)
        + ctx.bilanco(b, t, 'Kiralama İşlemlerinden Alacaklar', pb)
        + ctx.bilanco(b, t, 'Donuk Alacaklar', pb)
        + ctx.bilanco(b, t, 'Takipteki Krediler', pb)
    )


def m_npl_formasyonu(ctx, b, t):
    """Net NPL Formasyon Rasyosu (%) = Net NPL Oluşumu / Ortalama Brüt Krediler.
    Ortalama Brüt Krediler = gerçek 12-ay ort. = (brüt(t)+brüt(yoy))/2 (avg_balance).
    NOT (Faz 6 kararı): PBI'da PARALLELPERIOD(-12,MONTH) çeyrek-sonu tarih kolonunda
    blank dönüp paydayı brüt(t)/2'ye düşürüyordu (KT Mart'26 yanlış %1,85). Doğru
    değer gerçek ortalama ile %1,11. Bu measure ailesinde (donuk_intikal/tahsilat_ort)
    her zaman gerçek ortalama kullanılır."""
    net_olusum = (
        sum(ctx.donuk_akim(b, t, k) for k in _NPL_INTIKAL_ITEMS)
        + sum(ctx.donuk_akim(b, t, k) for k in _NPL_TAHSILAT_ITEMS)
    )
    ort_brut = avg_balance(ctx, b, t, lambda bb, tt: _brut_krediler(ctx, bb, tt))
    return safe_ratio(net_olusum, ort_brut)


def m_alinan_krediler_iemk_toplam_kaynak(ctx, b, t):
    pay = (ctx.bilanco(b, t, 'Alınan Krediler')
         + ctx.bilanco(b, t, 'İhraç Edilen Menkul Kıymetler (Net)'))
    return safe_ratio(pay, m_toplam_kaynak(ctx, b, t))


def m_tp_alinan_toplam_alinan(ctx, b, t):
    """TP Alınan Krediler ve İ.E.M.K / Toplam Alınan Krediler ve İ.E.M.K.
    2026-08-12 düzeltmesi: İhraç Edilen Menkul Kıymetler (Net) hem pay hem
    paydada eksikti (ölçünün kendi adı 'İ.E.M.K' dese de kod sadece Alınan
    Krediler'i kullanıyordu) — İhraç Edilen MK'sı olan bankalarda (Akbank,
    İş Bankası vb.) birkaç kat yanlış sonuç veriyordu."""
    pay = (ctx.bilanco(b, t, 'Alınan Krediler', 'TP')
         + ctx.bilanco(b, t, 'İhraç Edilen Menkul Kıymetler (Net)', 'TP'))
    payda = (ctx.bilanco(b, t, 'Alınan Krediler')
           + ctx.bilanco(b, t, 'İhraç Edilen Menkul Kıymetler (Net)'))
    return safe_ratio(pay, payda)


def m_tuzel_krediler_tuzel_mevduat(ctx, b, t):
    return safe_ratio(m_tuzel_krediler(ctx, b, t), ctx.tuzel_mevduat(b, t))


def m_krediler_altindisi_mevduat(ctx, b, t):
    den = ctx.bilanco(b, t, 'Mevduat') - ctx.kiymetli_maden(b, t)
    return safe_ratio(krediler(ctx, b, t), den)


def m_krediler_toplam_kaynak(ctx, b, t):
    """2026-08-14: pay DAX'a göre Toplam Brüt Krediler ('Krediler/Toplam Kaynak
    = [Toplam Brüt Krediler]/[Toplam Kaynak]')."""
    return safe_ratio(_brut_krediler(ctx, b, t), m_toplam_kaynak(ctx, b, t))


def m_tp_krediler_tp_kaynak(ctx, b, t):
    """2026-08-12: 'Kaynak' tanımı m_toplam_kaynak ile tutarlı hale getirildi
    (Para Piyasalarına Borçlar çıkarıldı) — DAX bu TP kırılımını ayrıca
    vermiyor ama 'Toplam Kaynak' ile aynı bileşenleri kullanması beklenir,
    aksi halde TP/Toplam oranı tutarsız iki farklı tanımı karşılaştırırdı."""
    pay = krediler(ctx, b, t, 'TP')
    den = (ctx.bilanco(b, t, 'Mevduat', 'TP')
         + ctx.bilanco(b, t, 'Alınan Krediler', 'TP')
         + ctx.bilanco(b, t, 'İhraç Edilen Menkul Kıymetler (Net)', 'TP'))
    return safe_ratio(pay, den)


def m_yp_krediler_yp_altindisi_kaynak(ctx, b, t):
    """2026-08-12: 'Kaynak' tanımı m_toplam_kaynak ile tutarlı hale getirildi
    (Para Piyasalarına Borçlar çıkarıldı) — bkz. m_tp_krediler_tp_kaynak notu."""
    pay = krediler(ctx, b, t, 'YP')
    yp_kaynak = (ctx.bilanco(b, t, 'Mevduat', 'YP')
               + ctx.bilanco(b, t, 'Alınan Krediler', 'YP')
               + ctx.bilanco(b, t, 'İhraç Edilen Menkul Kıymetler (Net)', 'YP'))
    altindisi = yp_kaynak - ctx.kiymetli_maden(b, t)
    return safe_ratio(pay, altindisi)


def m_vadesiz_mevduat_toplam_kaynak(ctx, b, t):
    return safe_ratio(ctx.vadesiz_mevduat(b, t), m_toplam_kaynak(ctx, b, t))


def m_tp_mevduat_altindisi_mevduat(ctx, b, t):
    den = ctx.bilanco(b, t, 'Mevduat') - ctx.kiymetli_maden(b, t)
    return safe_ratio(ctx.bilanco(b, t, 'Mevduat', 'TP'), den)


def m_tp_kaynak_toplam_kaynak(ctx, b, t):
    """2026-08-12: 'Kaynak' tanımı m_toplam_kaynak ile tutarlı hale getirildi
    (Para Piyasalarına Borçlar çıkarıldı) — bkz. m_tp_krediler_tp_kaynak notu."""
    tp_kaynak = (ctx.bilanco(b, t, 'Mevduat', 'TP')
               + ctx.bilanco(b, t, 'Alınan Krediler', 'TP')
               + ctx.bilanco(b, t, 'İhraç Edilen Menkul Kıymetler (Net)', 'TP'))
    return safe_ratio(tp_kaynak, m_toplam_kaynak(ctx, b, t))


def m_toplam_kaynak_toplam_pasifler(ctx, b, t):
    return safe_ratio(m_toplam_kaynak(ctx, b, t), ctx.bilanco(b, t, 'Toplam Pasifler'))


def m_tp_pasifler_toplam_pasifler_ozkaynak_haric(ctx, b, t):
    """Pay = TP Pasifler (özkaynak dahil); payda = Toplam Pasifler − Özkaynak."""
    pay = ctx.bilanco(b, t, 'Toplam Pasifler', 'TP')
    den = ctx.bilanco(b, t, 'Toplam Pasifler') - ctx.bilanco(b, t, 'Özkaynaklar')
    return safe_ratio(pay, den)


def m_sermaye_benzeri_pasifler(ctx, b, t):
    return safe_ratio(ctx.bilanco(b, t, 'Sermaye Benzeri Krediler'),
                      ctx.bilanco(b, t, 'Toplam Pasifler'))


def m_ppborclari_pasifler(ctx, b, t):
    return safe_ratio(ctx.bilanco(b, t, 'Para Piyasalarına Borçlar'),
                      ctx.bilanco(b, t, 'Toplam Pasifler'))


# --- Faiz (Kar Payı) Maliyetli Pasifler — PBI DAX detaylı (9 bileşen) ---
# DİKKAT: lookup.maliyetli_pasif (5 bileşen, full Mevduat) AYRI/paylaşımlı helper'dır
# (faiz_maliyetli_pasif_maliyeti / kaynak_pacal_maliyet / spread / faiz_getirili_maliyetli
# onu kullanır) → ONA DOKUNMA. Bu measure PBI'a özgü tanım kullanır: vadesizi DIŞLAR
# (Vadeli Mevduat) + 4 ek yükümlülük (FVTPL Yük., Türev Yük., Faktoring B., Kiralama B.).
_MALIYETLI_PASIF_DETAY_KALEMLER = [
    'Alınan Krediler',
    'Para Piyasalarına Borçlar',
    'İhraç Edilen Menkul Kıymetler (Net)',
    'Gerçeğe Uygun Değer Farkı Kar Zarara Yansıtılan Finansal Yükümlülükler',
    'Türev Finansal Yükümlülükler',
    'Faktoring Borçları',
    'Kiralama İşlemlerinden Borçlar',
    'Sermaye Benzeri Krediler',
]


def _faiz_maliyetli_pasif_detay(ctx, b, t):
    """PBI [Faiz (Kar Payı) Maliyetli Pasifler] (9 bileşen):
    Vadeli Mevduat (= Toplam Mevduat − Vadesiz Mevduat) + Alınan Krediler
    + Para Piyasalarına Borçlar + İhraç Edilen Menkul Kıymetler (Net)
    + FVTPL Finansal Yükümlülükler + Türev Finansal Yükümlülükler + Faktoring Borçları
    + Kiralama İşlemlerinden Borçlar + Sermaye Benzeri Krediler. Hepsi Bilanço, PB='Toplam'.
    NOT: vadesiz mevduat (maliyetsiz) dışlanır; lookup.maliyetli_pasif (full Mevduat,
    5 bileşen) ayrı/paylaşımlı tanımdır — bu helper onu DEĞİŞTİRMEZ."""
    return (
        m_vadeli_mevduat(ctx, b, t)
        + sum(ctx.bilanco(b, t, k) for k in _MALIYETLI_PASIF_DETAY_KALEMLER)
    )


def m_maliyetli_pasifler_toplam_pasifler(ctx, b, t):
    """Faiz (Kar Payı) Maliyetli Pasifler / Toplam Pasifler (%). PBI DAX birebir."""
    return safe_ratio(_faiz_maliyetli_pasif_detay(ctx, b, t),
                      ctx.bilanco(b, t, 'Toplam Pasifler'))


def m_serbest_sermaye_ta(ctx, b, t):
    serbest = (ctx.bilanco(b, t, 'Özkaynaklar')
             - ctx.bilanco(b, t, 'Ortaklık Yatırımları')
             - ctx.bilanco(b, t, 'Maddi Duran Varlıklar (Net)')
             - ctx.bilanco(b, t, 'Maddi Olmayan Duran Varlıklar (Net)'))
    return safe_ratio(serbest, ctx.bilanco(b, t, 'Toplam Aktifler'))


# tp_spread / yp_spread placeholder
def m_tp_spread(ctx, b, t): return None
def m_yp_spread(ctx, b, t): return None


# ============================================================
# YENİ MEASURE'LAR (2026-08-14 — measures.docx tam DAX taraması)
# ============================================================

def m_toplam_brut_krediler(ctx, b, t):
    return _brut_krediler(ctx, b, t)


def m_toplam_canli_krediler(ctx, b, t):
    """PBI [Toplam Canlı Krediler] = Krediler Ve Alacaklar + Faktoring
    Alacakları + Kiralama İşlemlerinden Alacaklar (Donuk/Takipteki HARİÇ —
    Toplam Brüt Krediler'den NPL'siz hali)."""
    return (
        ctx.bilanco(b, t, 'Krediler Ve Alacaklar')
        + ctx.bilanco(b, t, 'Faktoring Alacakları')
        + ctx.bilanco(b, t, 'Kiralama İşlemlerinden Alacaklar')
    )


def m_toplam_fonlama(ctx, b, t):
    """PBI [Toplam Fonlama] = Mevduat + Alınan Krediler + Para Piyasalarına
    Borçlar + İhraç Edilen Menkul Kıymetler (Net). NOT: [Toplam Kaynak]'tan
    FARKLI — Toplam Kaynak'ta Para Piyasalarına Borçlar YOK (bkz. m_toplam_kaynak
    notu, 2026-08-12 düzeltmesi); Toplam Fonlama PBI'de ayrı bir ölçü ve
    Para Piyasalarına Borçlar'ı İÇERİR."""
    return (
        ctx.bilanco(b, t, 'Mevduat')
        + ctx.bilanco(b, t, 'Alınan Krediler')
        + ctx.bilanco(b, t, 'Para Piyasalarına Borçlar')
        + ctx.bilanco(b, t, 'İhraç Edilen Menkul Kıymetler (Net)')
    )


def m_toplam_kredi_kartlari(ctx, b, t):
    """PBI [Toplam Kredi Kartları] (measures.docx DAX'ı birebir): 3 terimin
    2.si ve 3.sü AYNI kalemi kullanıyor ('Bireysel Kredi Kartları - TP, Toplam'
    iki kez toplanıyor) — YP bireysel kredi kartları formülde hiç yok. Bu,
    PBI kaynağındaki görünür bir kopyala-yapıştır hatası (muhtemelen 3. terim
    '...- YP, Toplam' olmalıydı) ama kullanıcının verdiği DAX'a birebir
    sadık kalındı. YP'de bireysel kredi kartı bakiyesi olan bankalarda bu
    ölçü onu içermeyecek ve TP'yi 2 kez sayacak şekilde PBI ile aynı davranır."""
    return (
        ctx.grup12(b, t, 'Kredi Kartları,  Standart Nitelikli Krediler, Toplam')
        + ctx.tk_detay(b, t, 'Bireysel Kredi Kartları - TP, Toplam')
        + ctx.tk_detay(b, t, 'Bireysel Kredi Kartları - TP, Toplam')
    )


def m_toplam_mevduat_km_haric(ctx, b, t):
    """PBI [Toplam Mevduat (KM Hariç)] = [Toplam Mevduat] - [KM Mevduatı]."""
    return ctx.bilanco(b, t, 'Mevduat') - ctx.kiymetli_maden(b, t)


def m_toplam_ozkaynaklar_regulasyon(ctx, b, t):
    """PBI [Toplam Özkaynaklar (Ana Sermaye+ Katkı Sermaye)] = regülasyon
    özkaynağı ('Özkaynak Kalemlerine İlişkin Bilgiler' tablosu, 'Toplam
    Ozkaynaklar' kalemi) — Bilanço'daki 'Özkaynaklar'dan FARKLI. Zaten
    m_yp_net_pozisyon_ozkaynak içinde payda olarak kullanılıyordu; burada
    kendi başına büyüklük olarak da açığa çıkarıldı."""
    return ctx.ozkaynak_detay(b, t, 'Toplam Ozkaynaklar')


def m_toplam_pasifler(ctx, b, t):
    return ctx.bilanco(b, t, 'Toplam Pasifler')


def m_toplam_pasifler_ozkaynak_haric(ctx, b, t):
    """PBI [Toplam Pasifler (Özkaynak Hariç)] = Toplam Pasifler - Özkaynaklar."""
    return ctx.bilanco(b, t, 'Toplam Pasifler') - ctx.bilanco(b, t, 'Özkaynaklar')


def m_rav(ctx, b, t):
    """PBI [Toplam Risk Ağırlıklı Varlıklar (RAV)] DAX'ı (measures.docx'te
    2 kez birebir aynı verilmiş) yalnızca 'Kredi Riskine Esas Tutar: Toplam'ı
    kullanıyor — isim 'Toplam RAV' dese de formül sadece kredi riski bileşeni
    (Piyasa/Operasyonel dahil değil). DAX'a birebir sadık kalındı; [Toplam
    Risk] (Kredi+Piyasa+Operasyonel toplamı, m_toplam_risk_tabani) PBI'de
    AYRI ve farklı bir ölçü."""
    return ctx.sermaye(b, t, 'Kredi Riskine Esas Tutar: Toplam')


def _kredi_riski(ctx, b, t):
    return ctx.sermaye(b, t, 'Kredi Riskine Esas Tutar: Toplam')


def _piyasa_riski(ctx, b, t):
    return ctx.tcmb(b, t, 'Sermaye Std. Oranı, Piyasa Riskine Esas Tutar (Pret)')


def _operasyonel_risk(ctx, b, t):
    return ctx.tcmb(b, t, 'Sermaye Std. Oranı, Operasyonel Riske Esas Tutar (Oret)')


def m_toplam_risk_tabani(ctx, b, t):
    """PBI [Toplam Risk] = [Kredi Riski]+[Piyasa Riski]+[Operasyonel Risk].
    Kredi Riski = sermaye tablosu 'Kredi Riskine Esas Tutar: Toplam'; Piyasa/
    Operasyonel Risk = tcmb tablosundaki 'Sermaye Std. Oranı, ... Riskine
    Esas Tutar (Pret/Oret)' kalemleri (SYR'nin paydasıyla aynı kalemler —
    ham veride 'Sermaye Yeterliliği, Özkaynaklar / (Kredi + Piyasa +
    Operasyonel Riske Esas Tutar)' kalemiyle doğrulandı)."""
    return _kredi_riski(ctx, b, t) + _piyasa_riski(ctx, b, t) + _operasyonel_risk(ctx, b, t)


def m_kredi_riski_toplam_risk(ctx, b, t):
    return safe_ratio(_kredi_riski(ctx, b, t), m_toplam_risk_tabani(ctx, b, t))


def m_piyasa_riski_toplam_risk(ctx, b, t):
    return safe_ratio(_piyasa_riski(ctx, b, t), m_toplam_risk_tabani(ctx, b, t))


def m_operasyonel_risk_toplam_risk(ctx, b, t):
    return safe_ratio(_operasyonel_risk(ctx, b, t), m_toplam_risk_tabani(ctx, b, t))


def m_brut_krediler_ta(ctx, b, t):
    """PBI [Brüt Krediler/ Toplam Aktifler] = [Toplam Brüt Krediler]/[Toplam
    Aktifler] — mevcut 'krediler_ta' (net Krediler/TA) ölçüsünden FARKLI,
    PBI'de ayrı bir isimle var."""
    return safe_ratio(_brut_krediler(ctx, b, t), ctx.bilanco(b, t, 'Toplam Aktifler'))


def m_alinan_krediler_toplam_pasifler(ctx, b, t):
    return safe_ratio(ctx.bilanco(b, t, 'Alınan Krediler'), ctx.bilanco(b, t, 'Toplam Pasifler'))


def m_bankalar_toplam_aktifler(ctx, b, t):
    return safe_ratio(ctx.bilanco(b, t, 'Bankalar'), ctx.bilanco(b, t, 'Toplam Aktifler'))


def _birikimli_vadeli_mevduat(ctx, b, t):
    if ctx.bank_turu.get(b) == 'Katılım':
        return ctx.tfv(b, t, 'Toplam  Birikimli Katılma Hesabı')
    return ctx.mvy(b, t, 'Toplam, Birikimli')


def m_birikimli_vadeli_mevduat_toplam_vadeli(ctx, b, t):
    return safe_ratio(_birikimli_vadeli_mevduat(ctx, b, t), m_vadeli_mevduat(ctx, b, t))


def m_resmi_kurumlar_mevduat_toplam_mevduat(ctx, b, t):
    return safe_ratio(ctx.resmi_kurumlar(b, t), ctx.bilanco(b, t, 'Mevduat'))


def m_toplam_fonlama_faiz_maliyetli_pasif(ctx, b, t):
    """PBI [Toplam Fonlama/ Faiz (Kar Payı) Maliyetli Pasifler] — 'kat'
    gösterimi (diğer benzer büyüklük-oranlı ölçüler gibi, örn.
    faiz_getirili_maliyetli), %100'e ölçeklenmiyor."""
    return safe_ratio(m_toplam_fonlama(ctx, b, t), _faiz_maliyetli_pasif_detay(ctx, b, t), scale=1.0)


def m_tuzel_mevduat_toplam_mevduat(ctx, b, t):
    return safe_ratio(ctx.tuzel_mevduat(b, t), ctx.bilanco(b, t, 'Mevduat'))


def m_nakit_degerler_ta(ctx, b, t):
    return safe_ratio(ctx.bilanco(b, t, 'Nakit Değerler Ve Merkez Bankası'),
                      ctx.bilanco(b, t, 'Toplam Aktifler'))


def m_vadeli_1ay_toplam_vadeli(ctx, b, t):
    """PBI [1 Aya Kadar Vadeli Mevduat/ Toplam Vadeli Mevduat]. NOT: Katılım
    bankalarında vade dilim sınırları (1/3/6/9 ay) konvansiyonel bankalarla
    (1/1-3/3-6/6-12 ay) örtüşmüyor — bu 4 ölçü ailesi yalnızca mvy tablosunu
    kullanır, Katılım bankalarında 0 döner (branching yapılmadı)."""
    return safe_ratio(ctx.mvy(b, t, 'Toplam, 1 Aya Kadar'), m_vadeli_mevduat(ctx, b, t))


def m_vadeli_1_3ay_toplam_vadeli(ctx, b, t):
    return safe_ratio(ctx.mvy(b, t, 'Toplam, 1-3 Ay'), m_vadeli_mevduat(ctx, b, t))


def m_vadeli_3_6ay_toplam_vadeli(ctx, b, t):
    return safe_ratio(ctx.mvy(b, t, 'Toplam, 3-6 Ay'), m_vadeli_mevduat(ctx, b, t))


def m_vadeli_6_12ay_toplam_vadeli(ctx, b, t):
    return safe_ratio(ctx.mvy(b, t, 'Toplam, 6 Ay-1 Yıl'), m_vadeli_mevduat(ctx, b, t))


def m_yp_krediler_toplam_krediler(ctx, b, t):
    """PBI [YP Krediler/ Toplam Krediler] = [YP Brüt Krediler]/[Toplam Brüt
    Krediler] — mevcut 'yp_krediler_yp_altindisi_kaynak' ölçüsünden FARKLI
    (o, YP kaynak tabanına göre)."""
    return safe_ratio(_brut_krediler(ctx, b, t, 'YP'), _brut_krediler(ctx, b, t))


# --- Likidite Açığı, kalan vadeye göre / Toplam Aktifler (7 dilim) ---
_LIKIDITE_ACIGI_KALEM = {
    'likidite_acigi_vadesiz_ta': 'Kalan Vadelerine Göre, Likitide Açığı, Vadesiz',
    'likidite_acigi_1ay_ta': 'Kalan Vadelerine Göre, Likitide Açığı, 1 Aya Kadar',
    'likidite_acigi_1_3ay_ta': 'Kalan Vadelerine Göre, Likitide Açığı, 1-3 Ay',
    'likidite_acigi_3_12ay_ta': 'Kalan Vadelerine Göre, Likitide Açığı, 3-12 Ay',
    'likidite_acigi_1_5yil_ta': 'Kalan Vadelerine Göre, Likitide Açığı, 1-5 Yıl',
    'likidite_acigi_5yil_uzeri_ta': 'Kalan Vadelerine Göre, Likitide Açığı, 5 Yıl Ve Üzeri',
    'likidite_acigi_dagitilamayan_ta': 'Kalan Vadelerine Göre, Likitide Açığı, Dağıtılamayan',
}


def _make_likidite_acigi_fn(kalem):
    def fn(ctx, b, t):
        return safe_ratio(ctx.kalan_vade(b, t, kalem), ctx.bilanco(b, t, 'Toplam Aktifler'))
    return fn


# ============================================================
# REGISTRY
# ============================================================

MEASURE_FUNCS: Dict[str, Callable] = {
    # === Mevcut 105 ===
    # Bilanço Aktifler büyüklük
    'toplam_aktifler': m_toplam_aktifler,
    'krediler': m_krediler,
    'donuk_alacaklar': m_donuk_alacaklar,
    'donuk_alacaklar_satis_terkin_oncesi': m_donuk_alacaklar_satis_terkin_oncesi,
    'konut_kredileri': m_konut_kredileri,
    'tasit_kredileri': m_tasit_kredileri,
    'ihtiyac_kredileri': m_ihtiyac_kredileri,
    'tuketici_kredileri': m_tuketici_kredileri,
    'tuzel_krediler': m_tuzel_krediler,
    'bireysel_kredi_kartlari': m_bireysel_kredi_kartlari,
    'grup_1_krediler': m_grup_1_krediler,
    'grup_2_krediler': m_grup_2_krediler,
    'grup_2_krediler_cekirdek_sermaye': m_grup_2_krediler_cekirdek_sermaye,
    'usd_yp_krediler': m_usd_yp_krediler,
    'euro_yp_krediler': m_euro_yp_krediler,
    'yp_net_pozisyon_ozkaynak': m_yp_net_pozisyon_ozkaynak,
    'faiz_getirili_ta': m_faiz_getirili_ta,
    'faiz_getirili_maliyetli': m_faiz_getirili_maliyetli,
    'faiz_getirili_ozkaynak': m_faiz_getirili_ozkaynak,

    # Bilanço Pasifler büyüklük
    'mevduat': m_mevduat,
    'vadesiz_mevduat': m_vadesiz_mevduat,
    'ozkaynaklar': m_ozkaynaklar,

    # Gelir Tablosu büyüklük
    'faiz_gelirleri': m_faiz_gelirleri,
    'faiz_giderleri': m_faiz_giderleri,
    'net_faiz_geliri': m_net_faiz_geliri,
    'alinan_ucret_komisyonlar': m_alinan_ucret_komisyonlar,
    'verilen_ucret_komisyonlar': m_verilen_ucret_komisyonlar,
    'net_ucret_komisyonlar': m_net_ucret_komisyonlar,
    'net_ticari_kar': m_net_ticari_kar,
    'personel_giderleri': m_personel_giderleri,
    'diger_faaliyet_giderleri': m_diger_faaliyet_giderleri,
    'karsilik_giderleri': m_karsilik_giderleri,
    'net_donem_kari': m_net_donem_kari,
    'brut_faaliyet_kari': m_brut_faaliyet_kari,
    'reklam_giderleri': m_reklam_giderleri,
    'gnakdi_alinan_ucret_komisyonlar': m_gnakdi_alinan_ucret_komisyonlar,

    # Şube & Personel büyüklük
    'sube_sayisi': m_sube_sayisi,
    'personel_sayisi': m_personel_sayisi,

    # Bilanço Aktifler rasyolar
    'krediler_ta': m_krediler_ta,
    'krediler_mevduat': m_krediler_mevduat,
    'npl_rasyosu': m_npl_rasyosu,
    'npl_rasyosu_satis_terkin_oncesi': m_npl_rasyosu_satis_terkin_oncesi,
    'npl_formasyonu': m_npl_formasyonu,
    'donuk_intikal_ort_krediler': m_donuk_intikal_ort_krediler,
    'donuk_tahsilat_ort_krediler': m_donuk_tahsilat_ort_krediler,
    'grup_1_krediler_toplam': m_grup_1_krediler_toplam,
    'grup_2_krediler_toplam': m_grup_2_krediler_toplam,
    'grup_2_tuketici_tuketici': m_grup_2_tuketici_tuketici,
    'grup_2_tuzel_tuzel': m_grup_2_tuzel_tuzel,
    'konut_tuketici': m_konut_tuketici,
    'tasit_tuketici': m_tasit_tuketici,
    'tuketici_toplam': m_tuketici_toplam,
    'tuzel_toplam': m_tuzel_toplam,
    'ihtiyac_toplam': m_ihtiyac_toplam,
    'bkk_toplam': m_bkk_toplam,
    'konut_tp_pasifler': m_konut_tp_pasifler,
    'tp_aktifler_ta': m_tp_aktifler_ta,
    'tp_krediler_toplam': m_tp_krediler_toplam,
    'yp_aktifler_toplam_pasifler': m_yp_aktifler_toplam_pasifler,
    'diger_aktifler_ta': m_diger_aktifler_ta,
    'finansal_varliklar_net_ta': m_finansal_varliklar_net_ta,
    'menkul_kiymetler_ta': m_menkul_kiymetler_ta,
    'ortaklik_yatirimlari_ta': m_ortaklik_yatirimlari_ta,
    'npl_karsilama_orani': m_npl_karsilama_orani,
    'mali_kesim_toplam': m_mali_kesim_toplam,
    'dis_ticaret_toplam': m_dis_ticaret_toplam,

    # Bilanço Pasifler rasyolar
    'vadesiz_mevduat_toplam_mevduat': m_vadesiz_mevduat_toplam_mevduat,
    'tp_mevduat_toplam_mevduat': m_tp_mevduat_toplam_mevduat,

    # Gelir Tablosu rasyolar (YtD)
    'komisyon_gid_gel': m_komisyon_gid_gel,
    'faiz_gideri_faiz_geliri': m_faiz_gideri_faiz_geliri,
    'personel_net_kar': m_personel_net_kar,
    'reklam_net_kar': m_reklam_net_kar,
    'net_ucret_operasyonel': m_net_ucret_operasyonel,

    # Annualized rasyolar (TTM + Avg balance)
    'roaa': m_roaa,
    'roae': m_roae,
    'cost_of_risk': m_cost_of_risk,
    'faaliyet_gid_ort_aktif': m_faaliyet_gid_ort_aktif,
    'personel_ort_aktif': m_personel_ort_aktif,
    'reklam_ort_aktif': m_reklam_ort_aktif,
    'net_ucret_ort_aktif': m_net_ucret_ort_aktif,
    'faiz_maliyetli_pasif_maliyeti': m_faiz_maliyetli_pasif_maliyeti,
    'kaynak_pacal_maliyet': m_kaynak_pacal_maliyet,
    'kredi_pacal_getiri': m_kredi_pacal_getiri,
    'kredi_mevduat_spread': m_kredi_mevduat_spread,

    # Şube/Personel rasyolar
    'personel_basina_krediler': m_personel_basina_krediler,
    'personel_basina_mevduat': m_personel_basina_mevduat,
    'personel_basina_net_kar': m_personel_basina_net_kar,
    'personel_basina_personel_gideri': m_personel_basina_personel_gideri,
    'sube_basina_krediler': m_sube_basina_krediler,
    'sube_basina_mevduat': m_sube_basina_mevduat,
    'sube_basina_net_kar': m_sube_basina_net_kar,
    'sube_basina_personel': m_sube_basina_personel,

    # === YENİ 21 (v29 / Phase 1 ile gelen) ===
    'vadeli_mevduat': m_vadeli_mevduat,
    'kiymetli_maden_mevduati': m_kiymetli_maden_mevduati,
    'resmi_kurumlar_mevduat': m_resmi_kurumlar_mevduat,
    'toplam_kaynak': m_toplam_kaynak,
    'alinan_krediler_iemk_toplam_kaynak': m_alinan_krediler_iemk_toplam_kaynak,
    'tp_alinan_toplam_alinan': m_tp_alinan_toplam_alinan,
    'tuzel_krediler_tuzel_mevduat': m_tuzel_krediler_tuzel_mevduat,
    'krediler_altindisi_mevduat': m_krediler_altindisi_mevduat,
    'krediler_toplam_kaynak': m_krediler_toplam_kaynak,
    'tp_krediler_tp_kaynak': m_tp_krediler_tp_kaynak,
    'yp_krediler_yp_altindisi_kaynak': m_yp_krediler_yp_altindisi_kaynak,
    'vadesiz_mevduat_toplam_kaynak': m_vadesiz_mevduat_toplam_kaynak,
    'tp_mevduat_altindisi_mevduat': m_tp_mevduat_altindisi_mevduat,
    'tp_kaynak_toplam_kaynak': m_tp_kaynak_toplam_kaynak,
    'toplam_kaynak_toplam_pasifler': m_toplam_kaynak_toplam_pasifler,
    'tp_pasifler_toplam_pasifler_ozkaynak_haric': m_tp_pasifler_toplam_pasifler_ozkaynak_haric,
    'sermaye_benzeri_pasifler': m_sermaye_benzeri_pasifler,
    'ppborclari_pasifler': m_ppborclari_pasifler,
    'maliyetli_pasifler_toplam_pasifler': m_maliyetli_pasifler_toplam_pasifler,
    'serbest_sermaye_ta': m_serbest_sermaye_ta,

    # Placeholder (her zaman None)
    'tp_spread': m_tp_spread,
    'yp_spread': m_yp_spread,

    # === YENİ 31 (2026-08-14 — measures.docx tam DAX taraması) ===
    'toplam_brut_krediler': m_toplam_brut_krediler,
    'toplam_canli_krediler': m_toplam_canli_krediler,
    'toplam_fonlama': m_toplam_fonlama,
    'toplam_kredi_kartlari': m_toplam_kredi_kartlari,
    'toplam_mevduat_km_haric': m_toplam_mevduat_km_haric,
    'toplam_ozkaynaklar_regulasyon': m_toplam_ozkaynaklar_regulasyon,
    'toplam_pasifler': m_toplam_pasifler,
    'toplam_pasifler_ozkaynak_haric': m_toplam_pasifler_ozkaynak_haric,
    'rav': m_rav,
    'toplam_risk_tabani': m_toplam_risk_tabani,
    'kredi_riski_toplam_risk': m_kredi_riski_toplam_risk,
    'piyasa_riski_toplam_risk': m_piyasa_riski_toplam_risk,
    'operasyonel_risk_toplam_risk': m_operasyonel_risk_toplam_risk,
    'brut_krediler_ta': m_brut_krediler_ta,
    'alinan_krediler_toplam_pasifler': m_alinan_krediler_toplam_pasifler,
    'bankalar_toplam_aktifler': m_bankalar_toplam_aktifler,
    'birikimli_vadeli_mevduat_toplam_vadeli': m_birikimli_vadeli_mevduat_toplam_vadeli,
    'resmi_kurumlar_mevduat_toplam_mevduat': m_resmi_kurumlar_mevduat_toplam_mevduat,
    'toplam_fonlama_faiz_maliyetli_pasif': m_toplam_fonlama_faiz_maliyetli_pasif,
    'tuzel_mevduat_toplam_mevduat': m_tuzel_mevduat_toplam_mevduat,
    'nakit_degerler_ta': m_nakit_degerler_ta,
    'vadeli_1ay_toplam_vadeli': m_vadeli_1ay_toplam_vadeli,
    'vadeli_1_3ay_toplam_vadeli': m_vadeli_1_3ay_toplam_vadeli,
    'vadeli_3_6ay_toplam_vadeli': m_vadeli_3_6ay_toplam_vadeli,
    'vadeli_6_12ay_toplam_vadeli': m_vadeli_6_12ay_toplam_vadeli,
    'yp_krediler_toplam_krediler': m_yp_krediler_toplam_krediler,
    **{mid: _make_likidite_acigi_fn(kalem) for mid, kalem in _LIKIDITE_ACIGI_KALEM.items()},
}


# ============================================================
# BASELINE PASSTHROUGH
# ============================================================
# Ham veride bulunmayan veya v29 PBI hesabıyla raw'dan tam eşleşmeyen
# measure'lar — base_data'dan (v29 baseline) olduğu gibi kopyalanır.
BASELINE_PASSTHROUGH: Set[str] = {
    # Sermaye Yeterliliği — BDDK ana raporlarında yok
    'syr',
    'cekirdek_syr',

    # Risk Ağırlıklı Varlıklar (RWA) bağımlı rasyolar
    'rorwa',
    'net_faiz_ort_rav',

    # PBI özel düzeltmeli formüller
    'maliyet_gelir_duzeltilmis',
    'nim_duzeltilmis',

    # Ham veride v29 ile eşleşmiyor / formül belirsiz
    'gayrinakdi_krediler',
    'gayrinakdi_komisyon_gayrinakdi',

    # PBI özel akım formülleri (raw delta hesabıyla tam tutmuyor)
    'spread',

    # IEA/operasyonel gelir tanımı PBI'a özgü — raw'dan ~%2-5 fark
    'maliyet_gelir',
    'nim',
    'nim_bzk_sonrasi',
    'faiz_getirili_aktif_getirisi',
}