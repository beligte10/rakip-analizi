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

import pandas as pd
from .lookup import (
    LookupContext, safe_ratio,
    krediler, donuk_alacaklar,
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


_KART_KALEMLERI = (
    'Bireysel Kredi Kartları - TP, Toplam',
    'Bireysel Kredi Kartları - YP, Toplam',
    'Personel Kredi Kartları - TP, Toplam',
    'Personel Kredi Kartları - YP, Toplam',
)


def tuketici_kredileri_kk_haric(ctx, b, t):
    """PBI 'Tüketici Kredileri (KK Hariç)' = [Tüketici Kr. ve Bireysel KK] − [Bireysel KK].

    2026-09-30: tablonun 'Toplam' satırından kartlar düşülür; önceden alt
    kalemler (Tüketici/Personel × TP/DE/YP + KMH TP/YP) toplanıyordu. BDR'lerle
    doğrulandı — Toplam satırı doğru, kalem toplamı hatalı olabiliyor:
    YK 2026-06 ham veride 'KMH - YP' TP'nin kopyası (+149.296 mn), Garanti'de
    BDR'deki 'KMH-TP (Personel)' 190 mn şablonda ayrı kalem değil, TEB'de
    ham Tüketici YP 12 mn (BDR 5)."""
    return m_tuketici_kredileri(ctx, b, t) - sum(ctx.tk_detay(b, t, k) for k in _KART_KALEMLERI)


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
def m_donuk_alacaklar(ctx, b, t): return donuk_alacaklar(ctx, b, t)


def m_konut_kredileri(ctx, b, t):  return _tk_breakdown(ctx, b, t, 'Konut Kredisi')
def m_tasit_kredileri(ctx, b, t):  return _tk_breakdown(ctx, b, t, 'Taşıt Kredisi')
def m_ihtiyac_kredileri(ctx, b, t):
    """İhtiyaç + 'Diğer' tüketici/personel kredileri (2026-09-30): Rakip Analizi
    202606.pdf 'Diğer'i ihtiyaca katıyor — KT Haziran 2026 BDR: 4.124 + 278
    personel + 330 diğer = 4.732 (PDF); 20/20 banka, oran 51/51 tutuyor."""
    return _tk_breakdown(ctx, b, t, 'İhtiyaç Kredisi') + _tk_breakdown(ctx, b, t, 'Diğer')


_TK_PARCA_KALEMLERI = (
    [f'Tüketici Kredileri - {x}, Toplam' for x in ('TP', 'Dövize Endeksli', 'YP')]
    + [f'Bireysel Kredi Kartları - {x}, Toplam' for x in ('TP', 'YP')]
    + [f'Personel Kredileri - {x}, Toplam' for x in ('TP', 'Dövize Endeksli', 'YP')]
    + [f'Personel Kredi Kartları - {x}, Toplam' for x in ('TP', 'YP')])


def m_tuketici_kredileri(ctx, b, t):
    """2026-10-03: toplam satırı 2014-2015'te bazı bankalarda (Burgan, Fibabanka, HSBC, ING,
    Odeabank) boş; aynı tablodaki parçaların (tüketici + bireysel kart + personel kredisi +
    personel kartı) toplamı kullanılır. Toplam satırı faiz/reeskont tahakkukunu da içerdiğinden
    parça toplamı ondan %1-4 düşük kalır (ikisinin de olduğu 1118 noktada ölçüldü)."""
    v = ctx.tk_detay(b, t, 'Krediler ve K. Kartları (Tüketici ve Personel, Toplam)')
    return v or sum(ctx.tk_detay(b, t, k) for k in _TK_PARCA_KALEMLERI)


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
    """1. grup (standart nitelikli) krediler = canlı krediler (Krediler Ve Alacaklar) + faktoring
    + kiralama − 2. grup. TFRS 9 dönemlerinde (Toplam) − Donuk − 2. grup ile aynı sonucu verir
    (2026-10-03: 2018-03 ve 2018-12 sonrası tüm banka-dönemlerde fark yok); 2013-2017'de
    '(Toplam)' satırı özel karşılık düşülmüş NET tutar olduğundan eski formül 1. grubu
    (takipteki − özel karşılık) kadar şişiriyordu. Krediler Ve Alacaklar satırı boşsa (ilk
    dönem dosyaları) eski formül."""
    kva = ctx.bilanco(b, t, 'Krediler Ve Alacaklar')
    if not kva:
        return krediler(ctx, b, t) - donuk_alacaklar(ctx, b, t) - m_grup_2_krediler(ctx, b, t)
    return (kva + ctx.bilanco(b, t, 'Faktoring Alacakları') + ctx.bilanco(b, t, LEASING_KALEM)
            - m_grup_2_krediler(ctx, b, t))


def m_grup_2_krediler_cekirdek_sermaye(ctx, b, t):
    """Grup 2 (Yakın İzlemedeki) Krediler / Çekirdek Sermaye (CET1) (%).
    Pay: m_grup_2_krediler (mevcut). Payda: 'Çekirdek Sermaye Toplamı'
    (ctx.sermaye = sermaye yeterliliği tablosu)."""
    return safe_ratio(m_grup_2_krediler(ctx, b, t), cekirdek_sermaye(ctx, b, t))


def cekirdek_sermaye(ctx, b, t):
    """Çekirdek sermaye (CET1) tutarı. 2015 ve öncesi dosyalarda tutar satırı boş ama oran
    raporlanmış: tutar = Çekirdek Sermaye Yeterliliği Oranı × toplam RAV (2026-10-03)."""
    v = ctx.sermaye(b, t, 'Çekirdek Sermaye Toplamı')
    if v:
        return v
    oran = ctx.sermaye_orani(b, t, 'Çekirdek Sermaye Yeterliliği Oranı (%)')
    rav = toplam_rav(ctx, b, t)
    return oran * rav / 100.0 if oran and rav else v


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
        regulasyon_ozkaynak(ctx, b, t),
    )


def m_donuk_alacaklar_satis_terkin_oncesi(ctx, b, t):
    # donuk_alacaklar(): 2013-2017'de 'Takipteki Krediler' (eskiden bu dönemde 0 − silinen dönüyordu)
    return donuk_alacaklar(ctx, b, t) - _aktiften_silinen(ctx, b, t)


# ============================================================
# BÜYÜKLÜKLER — Bilanço Pasifler & Bilanço Dışı
# ============================================================

def m_mevduat(ctx, b, t):     return ctx.bilanco(b, t, 'Mevduat')
def m_vadesiz_mevduat(ctx, b, t): return ctx.vadesiz_mevduat(b, t)
def m_ozkaynaklar(ctx, b, t): return ctx.bilanco(b, t, 'Özkaynaklar')


# Bilanço Dışı Yükümlülükler tablosundaki 'Garanti Ve Kefaletler, Toplam'ın
# alt kalemleri — Toplam satırı bozuk/tutarsız göründüğünde yedek olarak
# bunların toplamı kullanılır (bkz. m_gayrinakdi_krediler).
_GAYRINAKDI_LEAF_KALEMLER = [
    'Garanti Ve Kefaletler, Teminat Mektupları',
    'Garanti Ve Kefaletler, Banka Kredileri',
    'Garanti Ve Kefaletler, Akreditifler',
    'Garanti Ve Kefaletler, Garanti Verilen Prefinansmanlar',
    'Garanti Ve Kefaletler, Cirolar',
    'Garanti ve Kefaletler, Menkul Kıy. İh. Satın Alma Garantilerimizden',
    'Garanti ve Kefaletler, Faktoring Garantilerimizden',
    'Garanti Ve Kefaletler, Diğer Garantilerimizden',
    'Garanti ve Kefaletler, Diğer Kefaletlerimizden',
]


def m_gayrinakdi_krediler(ctx, b, t):
    """Bilanço dışı 'Garanti Ve Kefaletler, Toplam' kalemi (2026-09-09'da
    raw'a taşındı — önceden BASELINE_PASSTHROUGH'daydı çünkü v29 PBI ile tam
    eşleşip eşleşmediği doğrulanmamıştı). Analiz: 1057 tarihsel (banka,
    tarih) noktasından 1053'ü v29 baseline'la birebir eşleşiyor; kalan 4'ü ya
    ihmal edilebilir küçük bankalarda (~2015-2019, milyon TL seviyesinde)
    ufak yuvarlama farkı ya da KT 2020-06-30'da kaynak veride 'Toplam'
    satırının bizzat bozuk olması (-2.15 trilyon, alt kalemler toplamı ~12.1
    milyar — baseline'la eşleşen değer). O yüzden negatif (fiziksel olarak
    anlamsız) bir Toplam görülürse alt kalemlerin toplamına düşülür."""
    toplam = ctx.bd(b, t, 'Garanti Ve Kefaletler, Toplam')
    if toplam < 0:
        return sum(ctx.bd(b, t, k) for k in _GAYRINAKDI_LEAF_KALEMLER)
    return toplam


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
def m_personel_giderleri(ctx, b, t):       return ctx.personel_giderleri(b, t)


def _opex(ctx, b, t):
    """PBI [Diğer Faaliyet Giderleri (OPEX)] = Personel Giderleri + Diğer
    Faaliyet Giderleri. PBI datatable'ıyla doğrulandı (2026-09-23): KT
    2025-12-31 18.053 + 16.283 = 34.337 mn TL, PBI 34.337. Önceden yalnız
    'Diğer Faaliyet Giderleri (-)' kalemi kullanılıyordu (personel hariç),
    bu da bu ölçüyü ve onu kullanan 2 rasyoyu yaklaşık yarıya düşürüyordu.
    2026-10-03: şablon farkları LookupContext.opex'te (2013-2017'de personel Diğer Faaliyet
    Giderleri'nin içinde; 2018-12'de ham personel satırı 2 kat; 2018'de bazı katılım bankalarında
    personel satırı eksik)."""
    return ctx.opex(b, t)


def m_diger_faaliyet_giderleri(ctx, b, t): return _opex(ctx, b, t)
def m_karsilik_giderleri(ctx, b, t):       return ctx.gelir(b, t, 'Kredi Ve Diğer Alacaklar Değer Düşüş Karşılığı (-)')
def m_net_donem_kari(ctx, b, t):           return _net_donem_kari(ctx, b, t)
def m_brut_faaliyet_kari(ctx, b, t):
    # BDDK 'Faaliyet Gelirleri/Giderleri Toplamı' = karşılık ve faaliyet
    # giderlerinden ÖNCEKİ brüt faaliyet kârı. 2026-09-27'ye kadar yanlışlıkla
    # 'Net Faaliyet Karı/Zararı' okunuyordu (PDF ile 20/20 doğrulandı).
    return ctx.gelir(b, t, 'Faaliyet Gelirleri/Giderleri Toplamı')
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


def npl_payda(ctx, b, t):
    """NPL rasyosu paydası. TFRS 9 sonrası bilançoda 'Krediler Ve Alacaklar (Toplam)' brüttür
    (donuk + kiralama dahil). 2013-2017 dosyalarında 'Takipteki Krediler' brüt tutarken o
    toplam NET donuk içerir ve kiralama alacaklarını hariç tutar; bu dönemde brüt payda =
    Krediler Ve Alacaklar + Kiralama + Takipteki (_brut_krediler). Kuveyt Türk 2017-12:
    714,1 / 38.637,4 = %1,85."""
    if ctx.bilanco(b, t, 'Donuk Alacaklar') == 0 and ctx.bilanco(b, t, 'Takipteki Krediler') != 0:
        return _brut_krediler(ctx, b, t)
    return krediler(ctx, b, t)


def m_npl_rasyosu(ctx, b, t):
    return safe_ratio(donuk_alacaklar(ctx, b, t), npl_payda(ctx, b, t))


def m_npl_rasyosu_satis_terkin_oncesi(ctx, b, t):
    silinen_abs = abs(_aktiften_silinen(ctx, b, t))
    pay = donuk_alacaklar(ctx, b, t) + silinen_abs
    payda = npl_payda(ctx, b, t) + silinen_abs
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


def _grup_2_tuzel(ctx, b, t):
    """Grup 2 tüzel = Grup 2 toplam − kredi kartı − tüketici. Mali kesim yakın izlemedekiler
    ÇIKARILMAZ: PBI paydası (Tüzel Krediler, kredi kartı hariç) mali kesimi içerdiği için pay da
    içerir (2026-10-01, ING 2026-03 / QNB / Akbank / Vakıfbank PDF noktalarıyla doğrulandı)."""
    return (m_grup_2_krediler(ctx, b, t)
          - _grup2_kategori(ctx, b, t, 'Kredi Kartları')
          - _grup2_kategori(ctx, b, t, 'Tüketici Kredileri'))


def _tuzel_kredi_kartlari(ctx, b, t):
    """Toplam kredi kartı (Grup 1 + Grup 2) − bireysel kredi kartları.
    PBI [Tüzel Kredi Kartları] ile KT'de birebir (2025-12: 57.231 mn)."""
    toplam_kk = (ctx.grup12(b, t, 'Kredi Kartları,  Standart Nitelikli Krediler, Toplam')
               + _grup2_kategori(ctx, b, t, 'Kredi Kartları'))
    return toplam_kk - m_bireysel_kredi_kartlari(ctx, b, t)


def _tuzel_krediler_kk_haric(ctx, b, t):
    return m_tuzel_krediler(ctx, b, t) - _tuzel_kredi_kartlari(ctx, b, t)


def m_grup_2_tuzel_tuzel(ctx, b, t):
    """2026-09-23: payda PBI'daki gibi Tüzel Krediler (KREDİ KARTI HARİÇ) —
    pay zaten kredi kartlarını dışlıyordu, payda dışlamıyordu. PBI
    datatable'ıyla son 5 çeyrekte 119/130 (önceden 54/132), KT birebir."""
    return safe_ratio(_grup_2_tuzel(ctx, b, t), _tuzel_krediler_kk_haric(ctx, b, t))


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


def kur_ayrimli_krediler(ctx, b, t, pb):
    """TP/YP brüt krediler, YP'yi kur riski tablosundan alarak (2026-09-30).

    BDDK bilançosunda dövize endeksli krediler TP sütununda; 'Ana Ortaklık
    Bankanın Kur Riskine İlişkin Bilgiler' tablosunda ise döviz cinsinde
    (YP) gösteriliyor. PBI YP krediyi bu tablodan alıyor, TP = toplam − YP:
    Rakip Analizi 202606.pdf ile TP Krediler/Toplam, TP Krediler/TP Kaynak ve
    YP Krediler/YP Altındışı Kaynak 52/52 noktada doğrulandı (bilanço
    ayrımıyla 8, 8, 6/52). Tablo yoksa (1.184 banka-dönemden 5'i: Hayat
    Finans, Dünya Katılım 2023-24) bilanço ayrımına düşülür.
    NOT: TP/YP spread'lerin kredi getirisi bilanço ayrımıyla kalır — kur
    riski ayrımı orada PDF'ten daha uzak sonuç verdi."""
    yp = ctx.kur_konsolide(b, t, _KUR_KREDI_TOPLAM)
    if not yp:
        return _brut_krediler(ctx, b, t, pb)
    return yp if pb == 'YP' else _brut_krediler(ctx, b, t) - yp


def m_tp_krediler_toplam(ctx, b, t):
    """TP Brüt Krediler / Toplam Brüt Krediler — TP kur riski ayrımıyla
    (bkz. kur_ayrimli_krediler)."""
    return safe_ratio(kur_ayrimli_krediler(ctx, b, t, 'TP'), _brut_krediler(ctx, b, t))


def m_yp_krediler_toplam(ctx, b, t):
    """PBI [YP Krediler/ Toplam Krediler] = [YP Brüt Krediler]/[Toplam Brüt Krediler].
    2026-09-30: YP kur riski ayrımıyla (TP payıyla toplamı %100 kalsın diye)."""
    return safe_ratio(kur_ayrimli_krediler(ctx, b, t, 'YP'), _brut_krediler(ctx, b, t))


def m_yp_aktifler_toplam_pasifler(ctx, b, t):
    # PBI: YP Aktifler / YP Pasifler (payda PB=YP). Eskiden payda Toplam idi.
    return safe_ratio(ctx.bilanco(b, t, 'Toplam Aktifler', 'YP'),
                      ctx.bilanco(b, t, 'Toplam Pasifler', 'YP'))


def m_diger_aktifler_ta(ctx, b, t):
    # PBI: numerator = çoklu bilanço kalemi toplamı (_diger_aktifler_kompozit), tek satır değil.
    return safe_ratio(_diger_aktifler_kompozit(ctx, b, t), ctx.bilanco(b, t, 'Toplam Aktifler'))


_FINANSAL_VARLIK_BILESENLERI = (
    'Nakit Değerler Ve Merkez Bankası', 'Bankalar', 'Para Piyasalarından Alacaklar',
    'Gerçeğe Uygun D. Farkı K/Z Yan.Fv (Net)',
    'Gerçeğe Uygun Değer Farkı Diğer Kapsamlı Gelire Yansıtılan Finansal Varlıklar',
    'Türev Finansal Varlıklar', 'İtfa Edilmiş Maliyeti ile Ölçülen Finansal Varlıklar',
)


def finansal_varliklar(ctx, b, t):
    """PBI finansal varlıklar: bileşenlerin toplamı, nakit tarafındaki beklenen
    zarar karşılığı DÜŞÜLMEDEN (2026-10-01, Rakip Analizi 202606.pdf 52/52;
    'Finansal Varlıklar (Net)' satırıyla 37/52 — Garanti BDR: nakit + bankalar
    + PP 968.354 = net satır 967.380 + karşılık 974)."""
    return sum(ctx.bilanco(b, t, k) for k in _FINANSAL_VARLIK_BILESENLERI)


def m_finansal_varliklar_net_ta(ctx, b, t):
    return safe_ratio(finansal_varliklar(ctx, b, t), ctx.bilanco(b, t, 'Toplam Aktifler'))


def m_menkul_kiymetler_ta(ctx, b, t):
    return safe_ratio(_menkul_kiymetler(ctx, b, t), ctx.bilanco(b, t, 'Toplam Aktifler'))


def m_ortaklik_yatirimlari_ta(ctx, b, t):
    return safe_ratio(ctx.bilanco(b, t, 'Ortaklık Yatırımları'), ctx.bilanco(b, t, 'Toplam Aktifler'))


def npl_karsiligi(ctx, b, t):
    """NPL karşılama oranının payı: toplam kredi karşılığı. TFRS 9'da 'Beklenen Zarar Karşılıkları'
    (1.+2.+3. aşama). 2013-2017 şablonunda bu satır yok; aynı kapsam = özel karşılıklar (takipteki
    krediler için) + genel karşılıklar (canlı krediler için) (2026-10-03)."""
    if ctx.var('bilanco', b, t, 'Beklenen Zarar Karşılıkları (-)'):
        return abs(ctx.bilanco(b, t, 'Beklenen Zarar Karşılıkları (-)'))
    return abs(ctx.bilanco(b, t, 'Özel Karşılıklar (-)')) + abs(ctx.bilanco(b, t, 'Genel Karşılıklar'))


def m_npl_karsilama_orani(ctx, b, t):
    return safe_ratio(npl_karsiligi(ctx, b, t), donuk_alacaklar(ctx, b, t))


def m_mali_kesim_toplam(ctx, b, t):
    """2026-08-14: payda DAX'a göre Toplam Brüt Krediler. 2026-10-01: pay = Standart + Yakın
    İzlemedeki mali kesim kredileri (dış ticaret ölçüsüyle aynı yapı; ING 2026-03 ve QNB/Akbank/
    Vakıfbank 2026-06 PDF noktalarıyla doğrulandı)."""
    mk = (ctx.grup12(b, t, 'Mali Kesime Verilen Krediler,  Standart Nitelikli Krediler, Toplam')
          + _grup2_kategori(ctx, b, t, 'Mali Kesime Verilen Krediler'))
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


def m_kiymetli_maden_toplam_mevduat(ctx, b, t):
    return safe_ratio(ctx.kiymetli_maden(b, t), ctx.bilanco(b, t, 'Mevduat'))


def m_tp_mevduat_toplam_mevduat(ctx, b, t):
    return safe_ratio(ctx.bilanco(b, t, 'Mevduat', 'TP'), ctx.bilanco(b, t, 'Mevduat'))


def m_yp_mevduat_toplam_mevduat(ctx, b, t):
    """YP Mevduat (kıymetli maden dahil) / Toplam Mevduat. 100 − TP payı
    olarak DEĞİL doğrudan hesaplanır: bazı eski dönemlerde ham veride
    TP + YP ≠ Toplam. PBI kalemlerinden (YP Mevduat / Toplam Mevduat)
    hesaplanan oranla 2019+ 641/643 aynı (2026-09-24)."""
    return safe_ratio(ctx.bilanco(b, t, 'Mevduat', 'YP'), ctx.bilanco(b, t, 'Mevduat'))


# ============================================================
# RASYOLAR — Gelir Tablosu (YtD)
# ============================================================

# Aşağıdaki 5 rasyo PBI'da YtD/YtD (iki akım kalemin yılbaşından bugüne
# oranı, yıllıklandırma yok). Önceden TTM/TTM hesaplanıyordu — Aralık'ta
# ikisi aynı sonucu verdiği için fark yalnız Mart/Haziran/Eylül'de görünüyordu.
# PBI datatable'ıyla doğrulandı (2026-09-23, son 5 çeyrek): faiz gid/gel
# 135/135, komisyon 132/135, reklam/net kâr 130/132, personel/net kâr 27/27,
# net ücret/opex 133/135.
def m_komisyon_gid_gel(ctx, b, t):
    return safe_ratio(ctx.gelir(b, t, 'Verilen Ücret Ve Komisyonlar'),
                      ctx.gelir(b, t, 'Alınan Ücret Ve Komisyonlar'))


def m_faiz_gideri_faiz_geliri(ctx, b, t):
    return safe_ratio(ctx.gelir(b, t, 'Faiz Giderleri'), ctx.gelir(b, t, 'Faiz Gelirleri'))


def m_personel_net_kar(ctx, b, t):
    return safe_ratio(ctx.gelir(b, t, 'Personel Giderleri (-)'),
                      ctx.gelir(b, t, 'Net Dönem Karı / Zararı'))


def m_insan_sermayesi_yatirim_getirisi(ctx, b, t):
    """İnsan Sermayesi Yatırım Getirisi = Dönem Net Kârı / Personel Giderleri ('kat').

    1 TL personel giderine karşılık kaç TL net kâr: 1,2 = 1,2 katı. Yüzdeye
    ÇEVRİLMEZ (scale=1). Pay ve payda yılbaşından kümülatif (YtD) — kardeş ölçü
    personel_net_kar'ın (Personel Giderleri / Net Dönem Kârı) tersi; yıllıklandırılmaz."""
    return safe_ratio(ctx.gelir(b, t, 'Net Dönem Karı / Zararı'),
                      ctx.gelir(b, t, 'Personel Giderleri (-)'), scale=1.0)


# --- OPEX / gelir büyümesi ve makas (slayt "Gider performansı", 2026-10-02) -------------
# Hepsi YtD/YtD yıllık büyüme: aynı çeyreğin yılbaşından itibaren kümülatif değeri, bir
# önceki yılın aynı çeyreğiyle kıyaslanır (6A26 / 6A25). Pay = fark, payda = baz dönem —
# gruplar için pay/paydalar toplanıp (groups.py) aynı tanım korunur.
def _yoy_fark_num_den(ctx, b, t, deger_fn):
    prev = ctx.yoy_period(b, t)
    if prev is None:
        return None, None
    cur, baz = deger_fn(ctx, b, t), deger_fn(ctx, b, prev)
    if not cur or not baz or baz < 0:
        return None, None
    return cur - baz, baz


def _gelir_toplami(ctx, b, t):
    return ctx.gelir(b, t, 'Faaliyet Gelirleri/Giderleri Toplamı')


def opex_yoy_num_den(ctx, b, t):
    return _yoy_fark_num_den(ctx, b, t, _opex)


def gelir_yoy_num_den(ctx, b, t):
    return _yoy_fark_num_den(ctx, b, t, _gelir_toplami)


def reel_buyume(nominal_pct, tufe_pct):
    """Fisher: (1 + nominal) / (1 + TÜFE) − 1, yüzde olarak; veri yoksa None."""
    if nominal_pct is None or tufe_pct is None:
        return None
    return ((1 + nominal_pct / 100.0) / (1 + tufe_pct / 100.0) - 1) * 100.0


def m_opex_yoy_buyumesi(ctx, b, t):
    return safe_ratio(*opex_yoy_num_den(ctx, b, t))


def m_gelir_yoy_buyumesi(ctx, b, t):
    return safe_ratio(*gelir_yoy_num_den(ctx, b, t))


def m_reel_opex_buyumesi(ctx, b, t):
    from .makro import tufe_yillik
    return reel_buyume(m_opex_yoy_buyumesi(ctx, b, t), tufe_yillik(t))


def m_opex_gelir_makasi(ctx, b, t):
    """Makas (puan) = Faaliyet gelirleri büyümesi − OPEX büyümesi (YoY, YtD). Pozitif =
    gelir giderden hızlı büyüyor (operasyonel kaldıraç); negatif = gider gelirin önünde."""
    g, o = m_gelir_yoy_buyumesi(ctx, b, t), m_opex_yoy_buyumesi(ctx, b, t)
    return None if g is None or o is None else g - o


def m_reklam_net_kar(ctx, b, t):
    return safe_ratio(ctx.faaliyet_gid_detay(b, t, 'Reklam ve İlan Giderleri'),
                      ctx.gelir(b, t, 'Net Dönem Karı / Zararı'))


def m_net_ucret_operasyonel(ctx, b, t):
    """Payda OPEX (personel dahil, bkz. _opex) — önceden yalnız Diğer
    Faaliyet Giderleri'ydi, oran ~2 kat çıkıyordu."""
    return safe_ratio(ctx.gelir(b, t, 'Net Ücret Ve Komisyon Gelirleri/Giderleri'),
                      _opex(ctx, b, t))


def m_maliyet_gelir(ctx, b, t):
    """Maliyet / Gelir Rasyosu (%) = (Diğer Faaliyet Giderleri + Personel
    Giderleri) / Faaliyet Gelirleri/Giderleri Toplamı — YtD/YtD (TTM DEĞİL).

    2026-09-12'de iki hata birden düzeltildi (BASELINE_PASSTHROUGH'dan
    raw'a taşındı):
    1. Payda eskiden yalnız Net Faiz+Net Ücret+Ticari K/Z topluyordu; ham
       veride 'Faaliyet Gelirleri/Giderleri Toplamı' adlı hazır bir kalem
       var (= Net Faiz Geliri/Gideri + Net Ücret ve Komisyon + Temettü
       Gelirleri + Ticari Kar/Zarar (Net) + Diğer Faaliyet Gelirleri —
       Akbank 2025-12-31'de 209.070.888.000 TL ile birebir doğrulandı) —
       eski payda Temettü ve Diğer Faaliyet Gelirleri'ni atlıyordu.
    2. TTM annualizasyonu YANLIŞ uygulanmıştı — bu rasyo PBI'da YtD/YtD
       (yıl içinde YtD; yıllıklandırılmıyor). Akbank'ta 2025-06-30/09-30/
       12-31 üçü de plain YtD ile prod'la BİREBİR eşleşti, TTM'li versiyon
       ~1-1.5pp sistematik sapma veriyordu.
    Sonuç: 1054 tarihsel noktadan %92.4'ü ±0.5pp içinde (medyan fark 0,
    %88.6'sı ±0.01pp). Kalan sapma bilinen veri-kalitesi istisnalarında
    (TOM Bank, Alternatif Bank, Odeabank — bu proje genelinde başka
    ölçülerde de görülen bankalar) yoğunlaşıyor."""
    maliyet = _opex(ctx, b, t)
    gelir = ctx.gelir(b, t, 'Faaliyet Gelirleri/Giderleri Toplamı')
    return safe_ratio(maliyet, gelir)


def m_maliyet_gelir_duzeltilmis(ctx, b, t):
    """PBI [Düzeltilmiş Maliyet Gelir Rasyosu] = (OPEX + Kredi Değer Düşüş
    Karşılığı) / Faaliyet Gelirleri/Giderleri Toplamı, YtD/YtD.

    Formülü hiç belgelenmemişti, BASELINE_PASSTHROUGH'ta donmuştu (yeni
    çeyrekte hep boş). PBI datatable değerlerinden geri çıkarıldı
    (2026-09-23): KT 2025-12-31 (34.337 + 12.690) / 101.096 = %46,517,
    PBI %46,517; 2026-03-31 %53,855, PBI %53,855."""
    maliyet = _opex(ctx, b, t) + ctx.gelir(b, t, 'Kredi Ve Diğer Alacaklar Değer Düşüş Karşılığı (-)')
    return safe_ratio(maliyet, ctx.gelir(b, t, 'Faaliyet Gelirleri/Giderleri Toplamı'))


def m_gayrinakdi_komisyon_gayrinakdi(ctx, b, t):
    """Gayri Nakdi Kredilerden (komisyon geliri, TTM) / Gayrinakdi Krediler
    (dönem SONU bakiyesi — ORTALAMA DEĞİL). 2026-09-12'de raw'a taşındı:
    1022 noktadan %99.8'i v29 baseline'la ±0.5pp içinde (medyan fark 0) —
    ortalama bakiye denendiğinde uyum %99.1'e düşüyordu, PBI'ın burada
    dönem-sonu bakiye kullandığı bu şekilde ortaya çıktı."""
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Gayri Nakdi Kredilerden'))
    return safe_ratio(ttm, m_gayrinakdi_krediler(ctx, b, t))


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


def _duzeltilmis_net_faiz_geliri(ctx, b, t):
    """PBI [Düzeltilmiş Net Faiz (Kar Payı) Geliri] = [Net Faiz Geliri/Gideri]
    + [Net Ticari Kar/Zarar] (bkz. m_net_ticari_kar — 'Ticari Kar/Zarar
    (Net)' ham kalemi). Kullanıcının verdiği orijinal PBI DAX'ından
    (2026-09-18) — önceden bu düzeltme hiç uygulanmıyordu."""
    return (ctx.gelir(b, t, 'Net Faiz Geliri/Gideri')
          + ctx.gelir(b, t, 'Ticari Kar/Zarar (Net)'))


def m_nim(ctx, b, t):
    """PBI [Net Faiz (Kar Payı) Marjı] = TTM [Net Faiz Geliri/Gideri] /
    [Ortalama Aktifler] (Ortalama TOPLAM aktif, detaylı faiz getirili aktif
    DEĞİL).

    Kullanıcının verdiği orijinal PBI DAX'ıyla (2026-09-18) düzeltildi —
    önceki formül (2026-09-15, ⚠️ EN İYİ TAHMİN) payda olarak yanlışlıkla
    detaylı (13-bileşenli) Faiz Getirili Aktif kullanıyordu; bu, "Net Faiz
    (Kar Payı) Marjı 2" adlı AYRI bir PBI ölçüsüymüş (katalogda karşılığı
    yok) — 1057 noktalık doğrulamada payımın tutarlı ~%7-8 fazla çıkmasının
    (bkz. eski docstring, docs/PROJE_EL_KITABI.md Dönem 25/26) kök nedeni
    buydu: küçük paydaya (faiz getirili aktif < toplam aktif) bölünce oran
    yapay şekilde şişiyordu."""
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Faiz Geliri/Gideri'))
    avg = _avg(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Toplam Aktifler'))
    return safe_ratio(ttm, avg)


def m_nim_duzeltilmis(ctx, b, t):
    """PBI [Düzeltilmiş Net Faiz (Kar Payı) Marjı] = TTM [Düzeltilmiş Net
    Faiz (Kar Payı) Geliri] / [Ortalama Faiz (Kar Payı) Getirili Aktifler]
    (detaylı 13-bileşenli payda — m_nim'den FARKLI, bkz. orada).

    Kullanıcının verdiği orijinal PBI DAX'ıyla (2026-09-18) ilk kez
    uygulandı — önceden (2026-09-12) hiç formül adayı bulunamadığı için
    BASELINE_PASSTHROUGH'ta donmuş kalıyordu (bkz. docs/PROJE_EL_KITABI.md)."""
    ttm = _ttm(ctx, b, t, lambda bb, tt: _duzeltilmis_net_faiz_geliri(ctx, bb, tt))
    avg = _avg(ctx, b, t, lambda bb, tt: _faiz_getirili_aktif_detay(ctx, bb, tt))
    return safe_ratio(ttm, avg)


def m_nim_bzk_sonrasi(ctx, b, t):
    """PBI [BZK Sonrası Düzeltilmiş Net Faiz (Kar Payı) Marjı] = TTM
    ([Düzeltilmiş Net Faiz (Kar Payı) Geliri] − BZK) / [Ortalama Faiz
    (Kar Payı) Getirili Aktifler]. BZK = 'Kredi Ve Diğer Alacaklar Değer
    Düşüş Karşılığı (-)' ham kalemi (m_cost_of_risk'te de aynı kalem).

    Kullanıcının verdiği orijinal PBI DAX'ıyla (2026-09-18) düzeltildi —
    önceki formül (2026-09-15, ⚠️ EN İYİ TAHMİN, sadece %43 ±0.5pp uyum)
    ölçü ADI "Düzeltilmiş" dese de Net Ticari Kar/Zarar ayarlamasını hiç
    uygulamıyordu; payı sadece ham Net Faiz Geliri − BZK'ydı."""
    def duzeltilmis_minus_bzk(bb, tt):
        return (_duzeltilmis_net_faiz_geliri(ctx, bb, tt)
              - ctx.gelir(bb, tt, 'Kredi Ve Diğer Alacaklar Değer Düşüş Karşılığı (-)'))
    ttm = _ttm(ctx, b, t, duzeltilmis_minus_bzk)
    avg = _avg(ctx, b, t, lambda bb, tt: _faiz_getirili_aktif_detay(ctx, bb, tt))
    return safe_ratio(ttm, avg)


def m_cost_of_risk(ctx, b, t):
    """PBI [Brüt CoR (bps)] = TTM [Beklenen Kredi Zararı Karşılıkları
    (Brüt)] / [Ortalama Brüt Krediler] × 10000. Kullanıcının verdiği
    orijinal PBI DAX'ıyla (2026-09-21) düzeltildi — payda önceden yanlışlıkla
    NET Krediler (krediler()) kullanıyordu, DAX açıkça BRÜT (_brut_krediler)
    istiyor. Pay tarafında ayrı bir "Brüt" ham kalem yok — Gelir Tablosu'nda
    tek karşılık kalemi ('Kredi Ve Diğer Alacaklar Değer Düşüş Karşılığı
    (-)') zaten değişmedi. Birim ×10000 (bps) yerine bu projenin '%'
    biriminde kalması için ×100 (safe_ratio) kullanılıyor.

    Pay 2026-09-23'te düzeltildi: Gelir Tablosu'ndaki 'Kredi Ve Diğer
    Alacaklar Değer Düşüş Karşılığı (-)' DEĞİL, karşılık giderleri
    dipnotundaki Beklenen Kredi Zararı / Özel Karşılık kalemi (bkz.
    _cor_pay). PBI datatable'ıyla son 5 çeyrekte 130/134, KT birebir."""
    ttm = _ttm(ctx, b, t, lambda bb, tt: _cor_pay(ctx, bb, tt))
    avg = _avg(ctx, b, t, lambda bb, tt: _brut_krediler(ctx, bb, tt))
    return safe_ratio(ttm, avg)


_COR_KALEM = 'Karşılık Giderleri (Beklenen Kredi Zararı Karşılıkları / Özel Karşılıklar )'


_COR_ESKI_KALEMLER = ('Karşılık Giderleri (Kredi ve Diğer Alacaklara İlişkin Özel Karşılıklar )',
                      'Karşılık Giderleri (Genel Karşılık Giderleri )')


def _cor_pay(ctx, b, t):
    """PBI [Beklenen Kredi Zararı Karşılıkları (Brüt)] — 'Bankaların Kredi
    ve Diğer Alacaklarına İlişkin Karşılık Giderleri' dipnotu (kalem adının
    sonundaki boşluk BDDK şablonunda var). Gelir Tablosu'ndaki toplam karşılık
    kalemi bunu + diğer karşılıkları içerdiğinden (ör. KT 2025-12: 12.690 vs
    11.372 mn) CoR'u ~%10 şişiriyordu.
    2013-2017 şablonunda 'Beklenen Kredi Zararı' satırı yok; aynı kapsam (canlı + takipteki
    krediler) = özel karşılık giderleri (III-V. grup) + genel karşılık giderleri (2026-10-03)."""
    if ctx.var('karsilik_gid', b, t, _COR_KALEM):
        return ctx.karsilik_gid(b, t, _COR_KALEM)
    return sum(ctx.karsilik_gid(b, t, k) for k in _COR_ESKI_KALEMLER)


def m_faaliyet_gid_ort_aktif(ctx, b, t):
    """TTM OPEX (personel dahil, bkz. _opex) / ortalama aktif. PBI
    datatable'ıyla son 5 çeyrekte 128/135 (önceden 1/135)."""
    ttm = _ttm(ctx, b, t, lambda bb, tt: _opex(ctx, bb, tt))
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
    """PBI [Faiz (Kar Payı) Getirili Aktiflerin Getirisi] = TTM Faiz
    Gelirleri / Ortalama Faiz Getirili Aktif. 2026-09-12'de basit (4
    bileşenli, lookup.faiz_getirili_aktif) paydadan DETAYLI (13 bileşenli,
    _faiz_getirili_aktif_detay — TCMB tablosu dahil) paydaya geçildi: basit
    payda ile 27 banka × tüm dönemlerde medyan fark 0.94pp, %30.3'ü ±0.5pp
    içindeydi; detaylı payda ile medyan fark 0, %92.5'i ±0.5pp içinde —
    kalan sapma küçük/yeni katılım bankalarında (Emlak Katılım, Dünya
    Katılım, Hayat Finans) yoğunlaşıyor. BASELINE_PASSTHROUGH'dan raw'a
    taşındı (bkz. MEASURE_FUNCS)."""
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Faiz Gelirleri'))
    avg = _avg(ctx, b, t, lambda bb, tt: _faiz_getirili_aktif_detay(ctx, bb, tt))
    return safe_ratio(ttm, avg)


def faiz_maliyetli_pasif_num_den(ctx, b, t):
    """(TTM kaynağa verilen faizler, ortalama 9 bileşenli maliyetli pasif) —
    banka ve grup hesabı (groups.RATIO_NUM_DEN / COMPOUND_SPREADS) ortak.

    2026-09-30: pay önceden toplam 'Faiz Giderleri' idi. Rakip Analizi
    202606.pdf ile 52/52 noktada doğrulandı: PBI payda yalnız Mevduata +
    Kullanılan Kredilere + İhraç Edilen MK'lere Verilen Faizler'i
    (_KAYNAK_FAIZ_KALEMLERI) kullanıyor; para piyasası (repo) ve diğer faiz
    giderleri hariç. Payda (9 bileşen) değişmedi. Spread de buna bağlı (52/52)."""
    num = _ttm(ctx, b, t, lambda bb, tt: sum(ctx.gelir(bb, tt, k) for k in _KAYNAK_FAIZ_KALEMLERI))
    den = _avg(ctx, b, t, lambda bb, tt: _faiz_maliyetli_pasif_detay(ctx, bb, tt))
    return num, den


def _faiz_maliyetli_pasif_maliyeti_detay(ctx, b, t):
    """TTM kaynağa verilen faizler / ortalama DETAYLI (9 bileşenli) maliyetli pasif."""
    return safe_ratio(*faiz_maliyetli_pasif_num_den(ctx, b, t))


def m_faiz_maliyetli_pasif_maliyeti(ctx, b, t):
    """2026-09-23: payda basit 'maliyetli_pasif' yerine detaylı 9 bileşenli
    tanım — PBI'ın kendi [Spread (bps)] içinde kullandığı ile aynı. PBI
    datatable'ıyla son 5 çeyrekte 129/135 (önceden 0/135; KT 2025-12 %10,79
    yerine PBI'daki gibi %19,82)."""
    return _faiz_maliyetli_pasif_maliyeti_detay(ctx, b, t)


_KAYNAK_FAIZ_KALEMLERI = ('Mevduata Verilen Faizler', 'Kullanılan Kredilere Verilen Faizler ',
                          'İhraç Edilen Menkul Kıymetlere Verilen Faizler')


def kaynak_pacal_num_den(ctx, b, t):
    """(TTM kaynağa verilen faizler, ortalama Toplam Kaynak) — banka ve grup
    hesabı (groups.RATIO_NUM_DEN / COMPOUND_SPREADS) aynı tanımı kullanır."""
    num = _ttm(ctx, b, t, lambda bb, tt: sum(ctx.gelir(bb, tt, k) for k in _KAYNAK_FAIZ_KALEMLERI))
    den = _avg(ctx, b, t, lambda bb, tt: m_toplam_kaynak(ctx, bb, tt))
    return num, den


def m_kaynak_pacal_maliyet(ctx, b, t):
    """PBI [Kaynağın Paçal Maliyeti]: kaynağa (mevduat + alınan krediler +
    ihraç edilen menkul kıymetler) verilen faiz/kâr payı giderleri / ortalama
    kaynak. 2026-09-27: önceden Faiz Maliyetli Pasiflerin Maliyeti'ne eşitti;
    Rakip Analizi 202606.pdf ile ilk 20 bankada 20/20 doğrulandı."""
    num, den = kaynak_pacal_num_den(ctx, b, t)
    return safe_ratio(num, den)


# PBI'daki ortak "spread" deseni: ((1+getiri)/(1+maliyet)-1)×10000 (bps).
# Kullanıcının verdiği orijinal DAX'larla (2026-09-21) doğrulandı — spread
# ölçüleri ÖNCEDEN hep basit FARK (getiri − maliyet) ile hesaplanıyordu, bu
# ise PBI'ın kullandığı BİLEŞİK (compounding) formülden farklı sonuç verir
# (iki oran da küçükken fark küçük ama TL faiz oranlarının yüksek olduğu
# dönemlerde ikisi arasındaki sapma anlamlı büyüyebilir — kullanıcı "hesap-
# lamalar yanlış geliyor" diye bildirdi). tp_spread/yp_spread (2026-09-21,
# bkz. yukarıda) ile AYNI desen — o ikisi de bu helper'ı kullanacak şekilde
# yeniden yazıldı, tekrar önlemek için.
def _compound_spread_pct(getiri_pct, maliyet_pct):
    """getiri_pct/maliyet_pct YÜZDE olarak verilir (ör. 15.3 = %15,3).
    Sonuç YÜZDE PUANI (DAX'ın ×10000/bps'inin /100'ü) — bu projede rasyo
    ölçüler '%' biriminde olduğu için (catalog'da 'bps' desteklenmiyor)."""
    if getiri_pct is None or maliyet_pct is None:
        return None
    y, c = getiri_pct / 100.0, maliyet_pct / 100.0
    if (1 + c) == 0:
        return None
    return ((1 + y) / (1 + c) - 1) * 100


def m_spread(ctx, b, t):
    """PBI [Spread (bps)] = ((1 + [Faiz (Kar Payı) Getirili Aktiflerin
    Getirisi]) / (1 + [Faiz (Kar Payı) Maliyetli Pasiflerin Maliyeti]) − 1)
    × 10000 (ikisi de detaylı 13/9-bileşenli tanımla).

    Kullanıcının verdiği orijinal PBI DAX'ıyla (2026-09-21) düzeltildi —
    önceki formül (2026-09-15, ⚠️ EN İYİ TAHMİN) basit FARK (a − p)
    kullanıyordu; PBI'ın gerçek formülü bileşik (ratio-of-ratios)."""
    a = m_faiz_getirili_aktif_getirisi(ctx, b, t)
    p = _faiz_maliyetli_pasif_maliyeti_detay(ctx, b, t)
    return _compound_spread_pct(a, p)


def m_kredi_pacal_getiri(ctx, b, t):
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Kredilerden Alınan Faizler'))
    avg = _avg(ctx, b, t, lambda bb, tt: krediler(ctx, bb, tt))
    return safe_ratio(ttm, avg)


def m_kredi_mevduat_spread(ctx, b, t):
    """PBI [Kredi Mevduat Spread'i] = ((1 + [Kredilerin Paçal Getirisi]) /
    (1 + [Mevduatın Paçal Maliyeti]) − 1) × 10000.

    Kullanıcının verdiği orijinal PBI DAX'ıyla (2026-09-21) düzeltildi —
    önceki formül basit FARK (kg − mm) kullanıyordu. 2026-09-27: PBI'daki
    maliyet yalnız mevduat değil Kaynağın Paçal Maliyeti (mevduat + alınan
    krediler + ihraç edilen MK); Rakip Analizi 202606.pdf ile 20/20 banka ve
    rakip trendinde 32/32 doğrulandı."""
    kg = m_kredi_pacal_getiri(ctx, b, t)
    return _compound_spread_pct(kg, m_kaynak_pacal_maliyet(ctx, b, t))


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
    return safe_ratio(_npl_net_olusum_yillik(ctx, b, t),
                      avg_balance(ctx, b, t, lambda bb, tt: _brut_krediler(ctx, bb, tt)))


def _npl_net_olusum_yillik(ctx, b, t):
    """YtD net NPL oluşumu × 12 / ay. PBI oranı yıllıklandırıyor (2026-09-23,
    datatable: Mart'ta bizim değerin tam 4, Haziran'da 2 katı, Aralık'ta aynısı);
    son 5 çeyrekte 130/135 (önceden 33/135)."""
    net_olusum = (
        sum(ctx.donuk_akim(b, t, k) for k in _NPL_INTIKAL_ITEMS)
        + sum(ctx.donuk_akim(b, t, k) for k in _NPL_TAHSILAT_ITEMS)
    )
    return net_olusum * 12 / ctx.months_in_period(t)


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
    aksi halde TP/Toplam oranı tutarsız iki farklı tanımı karşılaştırırdı.
    2026-09-30: pay kur riski ayrımlı TP brüt kredi (bkz. kur_ayrimli_krediler)."""
    pay = kur_ayrimli_krediler(ctx, b, t, 'TP')
    den = (ctx.bilanco(b, t, 'Mevduat', 'TP')
         + ctx.bilanco(b, t, 'Alınan Krediler', 'TP')
         + ctx.bilanco(b, t, 'İhraç Edilen Menkul Kıymetler (Net)', 'TP'))
    return safe_ratio(pay, den)


def m_yp_krediler_yp_altindisi_kaynak(ctx, b, t):
    """2026-08-12: 'Kaynak' tanımı m_toplam_kaynak ile tutarlı hale getirildi
    (Para Piyasalarına Borçlar çıkarıldı) — bkz. m_tp_krediler_tp_kaynak notu.
    2026-09-30: pay kur riski tablosundaki YP kredi (bkz. kur_ayrimli_krediler)."""
    pay = kur_ayrimli_krediler(ctx, b, t, 'YP')
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
    """TP Pasifler / Toplam Pasifler. Ölçünün adı "Özkaynaklar Hariç" dese de
    PBI DAX'ı (measures.docx) paydayı düz [Toplam Pasifler] alıyor; önceki
    kod paydadan özkaynağı düşüyordu. PBI datatable'ıyla son 5 çeyrekte
    135/135 (önceden 0/135)."""
    return safe_ratio(ctx.bilanco(b, t, 'Toplam Pasifler', 'TP'),
                      ctx.bilanco(b, t, 'Toplam Pasifler'))


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


def serbest_sermaye(ctx, b, t):
    """Özkaynak − duran varlıklar. 2026-09-30: Yatırım Amaçlı Gayrimenkuller de
    düşülüyor (Rakip Analizi 202606.pdf 51/51; önceden Garanti, Vakıf, Halk
    farklıydı — yalnız bu bankalarda kalem büyük)."""
    return (ctx.bilanco(b, t, 'Özkaynaklar')
          - ctx.bilanco(b, t, 'Ortaklık Yatırımları')
          - ctx.bilanco(b, t, 'Maddi Duran Varlıklar (Net)')
          - ctx.bilanco(b, t, 'Maddi Olmayan Duran Varlıklar (Net)')
          - ctx.bilanco(b, t, 'Yatırım Amaçlı Gayrimenkuller (Net)'))


def m_serbest_sermaye_ta(ctx, b, t):
    return safe_ratio(serbest_sermaye(ctx, b, t), ctx.bilanco(b, t, 'Toplam Aktifler'))


# ============================================================
# TP/YP Kredi Mevduat Spread'i (2026-09-21, kullanıcının verdiği orijinal
# PBI DAX'ına göre): önceden placeholder'dı (hep None dönüyordu, ham veride
# karşılığı bulunamadığı için).
#
# DAX: [TP/YP Kredi Mevduat Spread'i] =
#   ((1 + [TP/YP Kredilerin Getirisi]) / (1 + [TP/YP Vadeli Mevduatın
#   Maliyeti]) − 1) × 10000  (yani baz puan)
#
# [TP/YP Kredilerin Getirisi]: TTM 'Kredilerden Faizler (Toplam, TP/YP)'
#   (' Kredilerden Alınan Faiz Gelirlerine İlişkin Bilgiler' dipnot
#   tablosu — Gelir Tablosu'nun kendisinde TP/YP kırılımı YOK) / Ortalama
#   Krediler (TP/YP, bilanço zaten kırılımlı) — genel `kredi_pacal_getiri`
#   ölçüsünün TP/YP'ye ayrılmış hali.
#
# [TP/YP Vadeli Mevduatın Maliyeti]: TTM gerçek VADELİ (vadesiz hariç)
#   TP/YP faiz/kâr payı gideri (bkz. ctx.vadeli_mevduat_faizi — mevduat
#   bankasında 'Mevduata Ödenen Faizin Vade Yapısına Göre Gösterimi'
#   dipnotundan Toplam−Vadesiz, Katılım bankasında 'Katılma Hesaplarına
#   Ödenen Kar Paylarının Vade Yapısına Göre Gösterimi' dipnotundan zaten
#   vadesiz içermeyen 'Toplam -TP/YP Toplam') / Ortalama TP/YP Vadeli
#   Mevduat bakiyesi (bkz. ctx.vadeli_mevduat_bakiyesi).
#
#   DÜZELTME (2026-09-21, kullanıcı gerçek PBI ekran görüntüsüyle
#   karşılaştırdı — "veriler hala yanlış"): payda ÖNCEDEN TOPLAM TP/YP
#   Mevduat (vadesiz dahil) kullanıyordu, bu maliyeti olduğundan düşük
#   gösterip spread'i ~100-250bps şişiriyordu. Artık mevduat bankasında
#   ctx.vadeli_mevduat_bakiyesi ile TP/YP'ye özel gerçek vadeli bakiye
#   türetiliyor ('Döviz Tevdiat Hesabı'+'Kıymetli Maden Depo Hesabı'
#   segmentleri YP vadesizin iyi bir yaklaşıklığı — v29 ekran
#   görüntüsüyle ortalama sapma ~36bps'e düştü, önceden 100-250bps'ti).
#   ⚠️ Katılım bankasında (YP katılma hesabı segmentleri dipnotta güvenilir
#   görünmediği için) hâlâ TOPLAM bakiye kullanılıyor — bu alt küme için
#   yaklaşıklık aynen sürüyor.
#
# Birim: DAX ×10000 (baz puan) döndürür; bu projede rasyo ölçüler '%'
# biriminde (safe_ratio gibi ×100), o yüzden burada ×100 kullanılıp
# sonuç YÜZDE PUANI (bps/100) olarak döndürülüyor — kardeş ölçü
# `kredi_mevduat_spread` ile birim tutarlılığı için.
def tp_yp_kredi_getirisi_num_den(ctx, b, t, pb):
    """(TTM TP/YP kredi faizi, ortalama TP/YP krediler) — banka ve grup (groups.COMPOUND_SPREADS)."""
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.kredi_faiz_tpyp(bb, tt, 'Kredilerden Faizler (Toplam, ' + pb + ')'))
    avg = _avg(ctx, b, t, lambda bb, tt: brut_krediler_tpyp(ctx, bb, tt, pb))
    return ttm, avg


def brut_krediler_tpyp(ctx, b, t, pb):
    """PBI [TP/YP Brüt Krediler] (2026-10-01, kullanıcı DAX'ı).
    YP = 'Kur Riski, Varlıklar (Krediler, Toplam)' + YP Beklenen Zarar Karşılıkları
    (kur tablosu karşılık düşülmüş net tutar verir; bilançodaki YP karşılık eklenir).
    TP = bilanço TP brüt krediler − [DEK Krediler]; PBI'da DEK = YP Brüt − bilanço YP
    brüt (dövize endeksli krediler bilançoda TP sütununda, YP'ye aktarılır). Bu yüzden
    TP = Toplam brüt − YP brüt ile aynı sonucu verir (DAX 2026-10-01 ile doğrulandı;
    Vakıfbank, Garanti, İş, Akbank, Şekerbank'ta PDF'in TP→YP kaymasıyla tutuyor).
    Kur tablosu yoksa bilanço ayrımına düşer."""
    yp = ctx.kur_konsolide(b, t, _KUR_KREDI_TOPLAM)
    if not yp:
        return _brut_krediler(ctx, b, t, pb)
    yp += abs(ctx.bilanco(b, t, 'Beklenen Zarar Karşılıkları (-)', 'YP'))
    return yp if pb == 'YP' else _brut_krediler(ctx, b, t) - yp


def tp_yp_mevduat_maliyeti_num_den(ctx, b, t, pb):
    """(TTM TP/YP vadeli mevduat faizi, ortalama TP/YP vadeli mevduat)."""
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.vadeli_mevduat_faizi(bb, tt, pb))
    avg = _avg(ctx, b, t, lambda bb, tt: ctx.vadeli_mevduat_bakiyesi(bb, tt, pb))
    return ttm, avg


def _tp_yp_kredi_getirisi(ctx, b, t, pb):
    return safe_ratio(*tp_yp_kredi_getirisi_num_den(ctx, b, t, pb))


def _tp_yp_mevduat_maliyeti(ctx, b, t, pb):
    return safe_ratio(*tp_yp_mevduat_maliyeti_num_den(ctx, b, t, pb))


def _tp_yp_spread(ctx, b, t, pb):
    y = _tp_yp_kredi_getirisi(ctx, b, t, pb)
    c = _tp_yp_mevduat_maliyeti(ctx, b, t, pb)
    return _compound_spread_pct(y, c)


def m_tp_spread(ctx, b, t): return _tp_yp_spread(ctx, b, t, 'TP')
def m_yp_spread(ctx, b, t): return _tp_yp_spread(ctx, b, t, 'YP')


# --- TP/YP Getirili Aktif – Maliyetli Pasif Spread'i (2026-09-30, kullanıcı
# formülü): Spread = Faiz Gelirleri / Faiz Getirili Aktifler − Faiz Giderleri /
# Faiz Maliyetli Pasifler (basit fark), TP ve YP için ayrı. PDF'teki "TP/YP
# Kredi Mevduat Spread'i" (tp_spread/yp_spread) DEĞİL — o yalnız kredi ile
# vadeli mevduatı karşılaştırır; bu formül o sayfaları vermiyor (0/52).
#
# Faiz gelirleri: kredi, menkul değer ve bankalar faizleri TP/YP dipnot
# tablolarından. Zorunlu karşılık, para piyasası ve diğer faiz gelirlerinin
# TP/YP kırılımı BDDK verisinde yok: TP'ye yazılır (TL zorunlu karşılıklar
# faiz alır, ters repo ağırlıkla TL) — böylece TP + YP = toplam faiz geliri.
# Faiz giderleri: vadeli mevduat + kullanılan krediler + ihraç edilen MK
# faizleri (TP/YP) — Faiz Maliyetli Pasiflerin Maliyeti'nin 30.09 tanımıyla
# aynı kalemler; repo/diğer faiz giderleri hariç.
_GETIRILI_AKTIF_BILANCO = (
    'Bankalar', 'Para Piyasalarından Alacaklar',
    'Gerçeğe Uygun D. Farkı K/Z Yan.Fv (Net)',
    'Gerçeğe Uygun Değer Farkı Diğer Kapsamlı Gelire Yansıtılan Finansal Varlıklar',
    'İtfa Edilmiş Maliyeti ile Ölçülen Finansal Varlıklar',
    'Satılmaya Hazır Finansal Varlıklar (Net)', 'Vadeye Kadar Elde Tutulacak Yatırım.(Net)',
    'Türev Finansal Varlıklar', 'Riskten Korunma Amaçlı Türev Fv',
)
_TP_ATANAN_FAIZ_GELIRLERI = ('Zorunlu Karşılıklardan Alınan Faizler',
                             'Para Piyasası İşlemlerinden Alınan Faizler', 'Diğer Faiz Gelirleri  ')


def _faiz_getirili_aktif_pb(ctx, b, t, pb):
    """_faiz_getirili_aktif_detay'ın TP/YP kırılımı (aynı 13 bileşen)."""
    return (
        ctx.tcmb(b, t, 'TCMB Hesabı, (' + pb + ')')
        + sum(ctx.bilanco(b, t, k, pb) for k in _GETIRILI_AKTIF_BILANCO)
        + _brut_krediler(ctx, b, t, pb)
        - abs(ctx.bilanco(b, t, 'Beklenen Zarar Karşılıkları (-)', pb))
    )


def _faiz_gelirleri_pb(ctx, b, t, pb):
    v = (ctx.kredi_faiz_tpyp(b, t, 'Kredilerden Faizler (Toplam, ' + pb + ')')
         + ctx.faiz_tpyp(b, t, 'Menkul Değerlerden Faizler (Toplam, ' + pb + ')')
         + ctx.faiz_tpyp(b, t, 'Bankalardan Faizler (Toplam, ' + pb + ')'))
    if pb == 'TP':
        v += sum(ctx.gelir(b, t, k) for k in _TP_ATANAN_FAIZ_GELIRLERI)
    return v


def _faiz_giderleri_pb(ctx, b, t, pb):
    return (ctx.vadeli_mevduat_faizi(b, t, pb)
            + ctx.faiz_tpyp(b, t, 'Kredilere Faizler (Toplam, ' + pb + ')')
            + ctx.faiz_tpyp(b, t, 'İhraç Edilen Menkul Kıymetlere Verilen Faizler, ' + pb))


def _faiz_maliyetli_pasif_pb(ctx, b, t, pb):
    return (ctx.vadeli_mevduat_bakiyesi(b, t, pb)
            + sum(ctx.bilanco(b, t, k, pb) for k in _MALIYETLI_PASIF_DETAY_KALEMLER))


def getirili_aktif_getirisi_pb_num_den(ctx, b, t, pb):
    return (_ttm(ctx, b, t, lambda bb, tt: _faiz_gelirleri_pb(ctx, bb, tt, pb)),
            _avg(ctx, b, t, lambda bb, tt: _faiz_getirili_aktif_pb(ctx, bb, tt, pb)))


def maliyetli_pasif_maliyeti_pb_num_den(ctx, b, t, pb):
    return (_ttm(ctx, b, t, lambda bb, tt: _faiz_giderleri_pb(ctx, bb, tt, pb)),
            _avg(ctx, b, t, lambda bb, tt: _faiz_maliyetli_pasif_pb(ctx, bb, tt, pb)))


def _getirili_maliyetli_spread_pb(ctx, b, t, pb):
    y = safe_ratio(*getirili_aktif_getirisi_pb_num_den(ctx, b, t, pb))
    c = safe_ratio(*maliyetli_pasif_maliyeti_pb_num_den(ctx, b, t, pb))
    if y is None or c is None:
        return None
    return y - c


def m_tp_getirili_maliyetli_spread(ctx, b, t): return _getirili_maliyetli_spread_pb(ctx, b, t, 'TP')
def m_yp_getirili_maliyetli_spread(ctx, b, t): return _getirili_maliyetli_spread_pb(ctx, b, t, 'YP')


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
    """Kredi kartı kredileri = Grup 1 (standart) + Grup 2 (yakın izleme: krediler ve
    diğer alacaklar + ödeme planı uzatılan + diğer). 2026-10-01 (kullanıcı kararı,
    BDR sağlaması): PBI DAX'ı 'Bireysel Kredi Kartları - TP'yi iki kez topluyordu
    (YP hiç yoktu) — KT 239.079 / Garanti 1.771.420 / TEB 172.783 çıkıyordu; BDR'ye
    göre 137.461 / 748.887 / 70.795."""
    return (ctx.grup12(b, t, 'Kredi Kartları,  Standart Nitelikli Krediler, Toplam')
            + _grup2_kategori(ctx, b, t, 'Kredi Kartları'))


def m_toplam_mevduat_km_haric(ctx, b, t):
    """PBI [Toplam Mevduat (KM Hariç)] = [Toplam Mevduat] - [KM Mevduatı]."""
    return ctx.bilanco(b, t, 'Mevduat') - ctx.kiymetli_maden(b, t)


def m_toplam_ozkaynaklar_regulasyon(ctx, b, t):
    """PBI [Toplam Özkaynaklar (Ana Sermaye+ Katkı Sermaye)] = regülasyon
    özkaynağı ('Özkaynak Kalemlerine İlişkin Bilgiler' tablosu, 'Toplam
    Ozkaynaklar' kalemi) — Bilanço'daki 'Özkaynaklar'dan FARKLI. Zaten
    m_yp_net_pozisyon_ozkaynak içinde payda olarak kullanılıyordu; burada
    kendi başına büyüklük olarak da açığa çıkarıldı."""
    return regulasyon_ozkaynak(ctx, b, t)


def regulasyon_ozkaynak(ctx, b, t):
    """Regülasyon özkaynağı. 2026-10-03: özkaynak dipnotu boşsa (2014'te çoğu banka) aynı
    dosyadaki sermaye yeterliliği özetinin özkaynak satırı (ikisinin de olduğu 1118 noktanın
    1065'inde ±%0,2 içinde aynı)."""
    return (ctx.ozkaynak_detay(b, t, 'Toplam Ozkaynaklar')
            or ctx.tcmb(b, t, 'Sermaye Std. Oranı, Özkaynak'))


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
    return toplam_rav(ctx, b, t)


def m_ort_rav_ort_ozkaynak(ctx, b, t):
    """PBI [Ortalama RAV / Ortalama Özkaynaklar] (kat) — ortalama RAV
    (m_rav) / ortalama Özkaynaklar. PBI datatable'ıyla son 5 çeyrekte
    130/135, KT birebir (2025-12: 4,99 kat)."""
    return safe_ratio(_avg(ctx, b, t, lambda bb, tt: m_rav(ctx, bb, tt)),
                      _avg(ctx, b, t, lambda bb, tt: ctx.bilanco(bb, tt, 'Özkaynaklar')),
                      scale=1.0)


def _oran_ya_da_yok(v):
    """Oran 0 raporlanmışsa (dönemde bildirilmemiş) değer yok sayılır."""
    return v if v else None


def m_syr(ctx, b, t):
    """Sermaye Yeterlilik Rasyosu (%) — BDDK'nın kendisi bu oranı zaten
    hesaplayıp 'Kredilere İlişkin Olarak Ayrılan Özel Karşılıklar' adlı
    (mislabeled/reused) tabloda 'Sermaye Yeterlilik Rasyosu (%)' kalemi
    olarak raporluyor; RAV/Özkaynak'tan ayrıca türetmeye gerek yok.
    2026-09-12'de BASELINE_PASSTHROUGH'dan raw'a taşındı — 1055 tarihsel
    (banka,tarih) noktasından 1055'i v29 baseline'la ±0.01pp içinde
    eşleşiyor (98.4%'ü tam sıfır fark).
    2026-10-03: oran satırı boşsa (2013-2014 katılım bankaları) aynı dosyadaki sermaye
    yeterliliği özetinin oranı (ikisinin de olduğu 1159 noktanın 1149'unda ±0,02 puan aynı)."""
    return _oran_ya_da_yok(ctx.sermaye_orani(b, t, 'Sermaye Yeterlilik Rasyosu (%)')
                           or ctx.tcmb(b, t, _SYR_TCMB))


def m_cekirdek_syr(ctx, b, t):
    """Çekirdek Sermaye Yeterliliği Oranı (%) — aynı tablo, aynı gerekçe
    (bkz. m_syr). 1054/1054 noktadan 99.3%'ü tam sıfır fark ile eşleşti."""
    return _oran_ya_da_yok(ctx.sermaye_orani(b, t, 'Çekirdek Sermaye Yeterliliği Oranı (%)'))


def m_rorwa(ctx, b, t):
    """RORWA = TTM Net Dönem Karı / Ortalama RAV (%). Standart uluslararası
    banka karlılık rasyosu (Return on Risk-Weighted Assets). 2026-09-12'de
    doğrulandı: 950 noktadan %96.1'i v29 baseline'la ±0.5pp içinde (medyan
    fark 0) — kalan sapma büyük ölçüde küçük/yeni katılım bankalarında."""
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Dönem Karı / Zararı'))
    avg = _avg(ctx, b, t, lambda bb, tt: m_rav(ctx, bb, tt))
    return safe_ratio(ttm, avg)


def m_net_faiz_ort_rav(ctx, b, t):
    """Net Faiz (Kar Payı) Geliri / Ortalama RAV (%). 2026-09-12'de
    doğrulandı: 948 noktadan %95.0'i ±0.5pp içinde (medyan fark 0)."""
    ttm = _ttm(ctx, b, t, lambda bb, tt: ctx.gelir(bb, tt, 'Net Faiz Geliri/Gideri'))
    avg = _avg(ctx, b, t, lambda bb, tt: m_rav(ctx, bb, tt))
    return safe_ratio(ttm, avg)


def _piyasa_riski(ctx, b, t):
    return ctx.tcmb(b, t, 'Sermaye Std. Oranı, Piyasa Riskine Esas Tutar (Pret)')


def _operasyonel_risk(ctx, b, t):
    return ctx.tcmb(b, t, 'Sermaye Std. Oranı, Operasyonel Riske Esas Tutar (Oret)')


_RAV_SATIRI_BASLANGIC = pd.Timestamp('2016-01-01')
_SYR_TCMB = 'Sermaye Yeterliliği, Özkaynaklar / (Kredi + Piyasa + Operasyonel Riske Esas Tutar)'


def toplam_rav(ctx, b, t):
    """Toplam risk ağırlıklı tutar (2026-10-01, BDR sağlaması). Ham 'Kredi Riskine
    Esas Tutar: Toplam' satırı adına rağmen TOPLAM RAV'ı taşıyor (SYR = özkaynak /
    bu satır; 2016'dan beri 985 banka-dönemin 975'inde; KT/Garanti/TEB Haziran 2026
    BDR'leriyle birebir). PBI de bu satırı RAV olarak kullanıyor (PDF'teki RORWA,
    Net Faiz/Ort. RAV, Ort. RAV/Ort. Özkaynak bununla tutuyor).

    2026-10-03: satır 2014'te boş, 2015'te ağırlıklandırılmamış risk tutarlarının toplamı
    (RAV değil; bu yıllarda tolerans ±%10), sonra birkaç dönemde boş ya da 10 kat hatalı. Ham satır SYR ile kaba olarak
    tutarlıysa (özkaynak / RAV, 2016'dan itibaren SYR'nin 0,5-2 katı) olduğu gibi kullanılır: küçük farklar
    gerçek (BDDK'nın 2022-23 sabit kur / menkul değer esnekliklerinde SYR farklı hesaplanıyor).
    Değilse sırasıyla:
    1) aynı dosyadaki sermaye yeterliliği özeti (TCMB tablosu: kredi + piyasa + operasyonel
       riske esas tutar) SYR ile tutarlıysa (±%10) o,
    2) özet ham satırı doğruluyorsa (±%2; hatalı olan özkaynak satırı) ham satır,
    3) RAV = özkaynak / SYR (SYR'nin tanımı) — toplam aktiflerin 0,2-1,6 katı aralığındaysa,
    4) hiçbiri değilse ham satır (eski davranış)."""
    ham = ctx.sermaye(b, t, 'Kredi Riskine Esas Tutar: Toplam')
    syr = ctx.sermaye_orani(b, t, 'Sermaye Yeterlilik Rasyosu (%)') or ctx.tcmb(b, t, _SYR_TCMB)
    ozk = regulasyon_ozkaynak(ctx, b, t)
    if not (syr and ozk and syr > 0 and ozk > 0):
        return ham

    def oran(rav):   # örtük SYR / bildirilen SYR
        return ozk / rav * 100.0 / syr if rav and rav > 0 else 0.0

    # 2015 ve öncesinde satır başka bir kavram (ağırlıksız risk) → sıkı tolerans
    alt, ust = (0.9, 1.1) if pd.Timestamp(t) < _RAV_SATIRI_BASLANGIC else (0.5, 2.0)
    if alt <= oran(ham) <= ust and ham != ozk:
        return ham
    ozet = (ctx.tcmb(b, t, 'Sermaye Std. Oranı, Kredi Riskine Esas Tutar (Kret)')
            + _piyasa_riski(ctx, b, t) + _operasyonel_risk(ctx, b, t))
    if 0.9 <= oran(ozet) <= 1.1:
        return ozet
    if ham and ozet and abs(ozet / ham - 1) <= 0.02:
        return ham
    # SYR ile aynı tablodaki özkaynak önce (özkaynak dipnotu birkaç dönemde farklı kapsamda)
    ta = ctx.bilanco(b, t, 'Toplam Aktifler')
    for o in (ctx.tcmb(b, t, 'Sermaye Std. Oranı, Özkaynak'), ozk):
        tanim = o / syr * 100.0
        if ta and 0.2 <= tanim / ta <= 1.6:
            return tanim
    return ham


def _kredi_riski(ctx, b, t):
    """Kredi riskine esas tutar (karşı taraf kredi riski dahil) = toplam RAV −
    piyasa − operasyonel (KT BDR: 861.892 − 92.638 − 129.913 = 636.607 + 2.734).
    Sonuç ≤ 0 ise (2 eski kayıt: ham veri tutarsız) değer yok."""
    k = toplam_rav(ctx, b, t) - _piyasa_riski(ctx, b, t) - _operasyonel_risk(ctx, b, t)
    return k if k > 0 else None


def m_toplam_risk_tabani(ctx, b, t):
    """PBI [Toplam Risk] = Kredi + Piyasa + Operasyonel risk = toplam RAV.
    2026-10-01: önceden ham satır (zaten toplam) + piyasa + operasyonel
    toplanıyordu — son ikisi iki kez sayılıyordu."""
    return toplam_rav(ctx, b, t)


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


# Vadeli mevduatın vade dilimleri (2026-10-01): mevduat bankasında 'Mevduatın
# Vade Yapısı' Toplam satırı, katılım bankasında 'Katılım Fonunun Vade Yapısı'
# Toplam satırı — katılım tablosunun her sütunu bir dilim (3 aya kadar = 1–3 ay,
# 6 aya kadar = 3–6 ay, 9 aya kadar + 1 yıla kadar = 6–12 ay). Önceden katılım
# bankalarında hep 0 dönüyordu (KT BDR: 170.262 / 161.780 / 13.489 / 34.517).
_VADE_DILIMI = {
    '1ay': (('Toplam, 1 Aya Kadar',), ('Toplam  1 Aya Kadar',)),
    '1_3': (('Toplam, 1-3 Ay',), ('Toplam  3 Aya Kadar',)),
    '3_6': (('Toplam, 3-6 Ay',), ('Toplam  6 Aya Kadar',)),
    '6_12': (('Toplam, 6 Ay-1 Yıl',), ('Toplam  9 Aya Kadar', 'Toplam  1 Yıla Kadar')),
}


def _vade_dilimi(ctx, b, t, dilim):
    mevduat_k, katilim_k = _VADE_DILIMI[dilim]
    if ctx.bank_turu.get(b) == 'Katılım':
        return sum(ctx.tfv(b, t, k) for k in katilim_k)
    return sum(ctx.mvy(b, t, k) for k in mevduat_k)


def m_vadeli_1ay_toplam_vadeli(ctx, b, t):
    """PBI [1 Aya Kadar Vadeli Mevduat/ Toplam Vadeli Mevduat]."""
    return safe_ratio(_vade_dilimi(ctx, b, t, '1ay'), m_vadeli_mevduat(ctx, b, t))


def m_vadeli_1_3ay_toplam_vadeli(ctx, b, t):
    return safe_ratio(_vade_dilimi(ctx, b, t, '1_3'), m_vadeli_mevduat(ctx, b, t))


def m_vadeli_3_6ay_toplam_vadeli(ctx, b, t):
    return safe_ratio(_vade_dilimi(ctx, b, t, '3_6'), m_vadeli_mevduat(ctx, b, t))


def m_vadeli_6_12ay_toplam_vadeli(ctx, b, t):
    return safe_ratio(_vade_dilimi(ctx, b, t, '6_12'), m_vadeli_mevduat(ctx, b, t))


def m_yp_krediler_toplam_krediler(ctx, b, t):
    """PBI [YP Krediler/ Toplam Krediler] = [YP Brüt Krediler]/[Toplam Brüt
    Krediler] — mevcut 'yp_krediler_yp_altindisi_kaynak' ölçüsünden FARKLI
    (o, YP kaynak tabanına göre). 2026-09-30: YP kur riski ayrımıyla."""
    return safe_ratio(kur_ayrimli_krediler(ctx, b, t, 'YP'), _brut_krediler(ctx, b, t))


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
    'gayrinakdi_krediler': m_gayrinakdi_krediler,

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
    'kiymetli_maden_toplam_mevduat': m_kiymetli_maden_toplam_mevduat,
    'tp_mevduat_toplam_mevduat': m_tp_mevduat_toplam_mevduat,
    'yp_mevduat_toplam_mevduat': m_yp_mevduat_toplam_mevduat,

    # Gelir Tablosu rasyolar (YtD)
    'maliyet_gelir': m_maliyet_gelir,
    'maliyet_gelir_duzeltilmis': m_maliyet_gelir_duzeltilmis,
    'komisyon_gid_gel': m_komisyon_gid_gel,
    'faiz_gideri_faiz_geliri': m_faiz_gideri_faiz_geliri,
    'personel_net_kar': m_personel_net_kar,
    'insan_sermayesi_yatirim_getirisi': m_insan_sermayesi_yatirim_getirisi,
    'opex_yoy_buyumesi': m_opex_yoy_buyumesi,
    'gelir_yoy_buyumesi': m_gelir_yoy_buyumesi,
    'reel_opex_buyumesi': m_reel_opex_buyumesi,
    'opex_gelir_makasi': m_opex_gelir_makasi,
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
    'tp_getirili_maliyetli_spread': m_tp_getirili_maliyetli_spread,
    'yp_getirili_maliyetli_spread': m_yp_getirili_maliyetli_spread,
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
    'syr': m_syr,
    'cekirdek_syr': m_cekirdek_syr,
    'rorwa': m_rorwa,
    'ort_rav_ort_ozkaynak': m_ort_rav_ort_ozkaynak,
    'net_faiz_ort_rav': m_net_faiz_ort_rav,
    'faiz_getirili_aktif_getirisi': m_faiz_getirili_aktif_getirisi,
    'gayrinakdi_komisyon_gayrinakdi': m_gayrinakdi_komisyon_gayrinakdi,
    'nim': m_nim,
    'nim_duzeltilmis': m_nim_duzeltilmis,
    'nim_bzk_sonrasi': m_nim_bzk_sonrasi,
    'spread': m_spread,
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
# Şu an boş: son üyesi 'maliyet_gelir_duzeltilmis' 2026-09-23'te PBI
# datatable'ından formülü çıkarılıp raw'a taşındı (bkz.
# m_maliyet_gelir_duzeltilmis). Mekanizma, ileride ham veriden
# hesaplanamayan bir ölçü eklenirse diye korunuyor.
BASELINE_PASSTHROUGH: Set[str] = set()

# 2026-09-15: kullanıcı, birebir doğrulanmamış olsalar bile 'nim',
# 'nim_bzk_sonrasi', 'spread' için elimdeki EN İYİ TAHMİN formülünün
# (BASELINE_PASSTHROUGH'ta donmuş Mart değerini Haziran'a "ileri taşımak"
# yerine) kullanılmasını istedi — bkz. m_nim/m_nim_bzk_sonrasi/m_spread
# docstring'leri için doğruluk oranları (sırasıyla %81.7/%43/%78.3,
# ±0.5pp). MEASURE_FUNCS'a taşındılar; 'maliyet_gelir_duzeltilmis' ve
# 'nim_duzeltilmis' için hiç formül adayı olmadığından pasif kaldı.


# Rekabet Analizi çalışmasından alınan ölçüler (2026-10-06): formüller pipeline/rekabet_olculer.py'de.
# Dosyanın sonunda: o modül bu dosyadaki yardımcıları içe aktarır.
from . import rekabet_olculer as _rekabet  # noqa: E402

MEASURE_FUNCS.update(_rekabet.MEASURE_FUNCS)
