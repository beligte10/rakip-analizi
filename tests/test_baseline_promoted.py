"""
Ham veriden hesaplanan rasyoların GERÇEK PBI çıktısıyla uyumu (regresyon).

Referans: `data/computed_datatable_kaynakli_yedek.json` — PBI raporunun
kendi datatable export'undan (datatable_1.xlsx) üretilmiş değerler, 2015-03
→ 2026-03. 2026-09-23'e kadar bu test referans olarak canlı
`data/computed.json`'u, yani PIPELINE'IN KENDİ ÇIKTISINI kullanıyordu —
döngüseldi: yanlış bir formül, kendi eski yanlış değerleriyle "uyumlu"
görünüyordu (ör. Maliyetli Pasif Maliyeti KT'de %10,8 hesaplanıyordu, PBI
%19,8). Şimdi bağımsız PBI değerlerine karşı ölçülüyor.

Yalnız 2019 ve sonrası: 2013-2018 arası bazı BDDK şablon kalemleri farklı
adlandırıldığı için eski dönemlerde yapısal sapma var (bkz. docs/
PROJE_EL_KITABI.md Dönem 33). Eşikler 2026-09-23 ölçümünün biraz altında.

Gerçek `data/veriler.parquet` + PBI referans JSON'una bağımlı (bu makineye
özel, .gitignore'da) — yoksa test SESSİZCE ATLANIR.
"""
from pathlib import Path
import json
import statistics

import pytest

from pipeline.lookup import LookupContext
from pipeline import measures as m

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
VERILER_PATH = DATA_DIR / 'veriler.parquet'
PBI_PATH = DATA_DIR / 'computed_datatable_kaynakli_yedek.json'
CATALOG_PATH = DATA_DIR / 'catalog.json'
SINCE = '2019-03-31'

pytestmark = pytest.mark.skipif(
    not VERILER_PATH.exists() or not PBI_PATH.exists(),
    reason='data/veriler.parquet veya PBI referans JSON bu makinede yok',
)


@pytest.fixture(scope='module')
def ctx():
    import pandas as pd
    df = pd.read_parquet(VERILER_PATH)
    catalog = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
    bank_turu_map = {b['banka_adi']: b['tur'] for b in catalog['banks']}
    return LookupContext(df, bank_turu_map)


@pytest.fixture(scope='module')
def pbi():
    # Referans datatable eski banka adlarını taşır ('QNB Finansbank'); platform adına çevrilir.
    from pipeline.banka_adlari import kanonik
    bd = json.loads(PBI_PATH.read_text(encoding='utf-8'))['bank_data']
    return {mid: {kanonik(b): v for b, v in banks.items()} for mid, banks in bd.items()}


def _diffs(ctx, pbi, measure_id, fn):
    diffs = []
    for bank, dates in pbi.get(measure_id, {}).items():
        for date, pbi_v in dates.items():
            if pbi_v is None or date < SINCE:
                continue
            try:
                my_v = fn(ctx, bank, date)
            except Exception:
                my_v = None
            if my_v is None:
                continue
            diffs.append(abs(my_v - pbi_v))
    return diffs


# (measure_id, fonksiyon, min_kabul_orani (<=0.5pp), min_nokta_sayisi)
# Yorumdaki yüzde: 2026-09-23 ölçümü (2019+).
PBI_UYUMLU = [
    ('syr', m.m_syr, 0.95, 500),                                          # 98.3
    ('cekirdek_syr', m.m_cekirdek_syr, 0.95, 500),                        # 99.0
    ('rorwa', m.m_rorwa, 0.93, 500),                                      # 96.0
    ('net_faiz_ort_rav', m.m_net_faiz_ort_rav, 0.90, 500),                # 94.4
    ('faiz_getirili_aktif_getirisi', m.m_faiz_getirili_aktif_getirisi, 0.90, 500),  # 94.2
    ('faiz_getirili_ozkaynak', m.m_faiz_getirili_ozkaynak, 0.95, 500),    # 97.7
    ('gayrinakdi_komisyon_gayrinakdi', m.m_gayrinakdi_komisyon_gayrinakdi, 0.95, 500),  # 99.9
    ('maliyet_gelir', m.m_maliyet_gelir, 0.90, 500),                      # 94.9
    ('maliyet_gelir_duzeltilmis', m.m_maliyet_gelir_duzeltilmis, 0.90, 500),  # 94.2
    ('nim', m.m_nim, 0.93, 500),                                          # 96.2
    ('nim_duzeltilmis', m.m_nim_duzeltilmis, 0.92, 500),                  # 95.3
    ('nim_bzk_sonrasi', m.m_nim_bzk_sonrasi, 0.90, 500),                  # 92.8
    # spread ve faiz_maliyetli_pasif_maliyeti 2026-09-30'da çıkarıldı: datatable eski
    # tanımı (pay = toplam Faiz Giderleri) taşıyor; esas referans Haziran 2026 PDF'i
    # (pay = kaynağa verilen faizler) — bkz. aşağıdaki PDF_202606.
    # kredi_mevduat_spread 2026-09-27'de çıkarıldı: datatable eski tanımı (yalnız mevduat
    # maliyeti) taşıyor; esas referans Haziran 2026 PDF'i — bkz. test_pdf_202606_uyum.
    ('cost_of_risk', m.m_cost_of_risk, 0.93, 500),                        # 97.0
    ('npl_formasyonu', m.m_npl_formasyonu, 0.95, 500),                    # 98.4
    ('grup_2_tuzel_tuzel', m.m_grup_2_tuzel_tuzel, 0.90, 500),            # 94.7
    ('tuzel_krediler_tuzel_mevduat', m.m_tuzel_krediler_tuzel_mevduat, 0.92, 500),  # 95.6
    ('tp_pasifler_toplam_pasifler_ozkaynak_haric', m.m_tp_pasifler_toplam_pasifler_ozkaynak_haric, 0.97, 500),  # 99.7
    ('tp_alinan_toplam_alinan', m.m_tp_alinan_toplam_alinan, 0.97, 500),  # 99.9
    ('faiz_gideri_faiz_geliri', m.m_faiz_gideri_faiz_geliri, 0.93, 500),  # 96.9
    ('komisyon_gid_gel', m.m_komisyon_gid_gel, 0.93, 500),                # 97.7
    ('reklam_net_kar', m.m_reklam_net_kar, 0.93, 500),                    # 97.6
    ('faaliyet_gid_ort_aktif', m.m_faaliyet_gid_ort_aktif, 0.85, 500),    # 89.5
    ('net_ucret_operasyonel', m.m_net_ucret_operasyonel, 0.92, 500),      # 96.3
    # PBI datatable'ında yalnız 2026-03-31 var.
    ('personel_net_kar', m.m_personel_net_kar, 0.95, 20),                 # 100
]


@pytest.mark.parametrize('measure_id,fn,min_oran,min_n', PBI_UYUMLU)
def test_pbi_ile_uyum(ctx, pbi, measure_id, fn, min_oran, min_n):
    diffs = _diffs(ctx, pbi, measure_id, fn)
    assert len(diffs) >= min_n, f'{measure_id}: yeterli karşılaştırma noktası yok ({len(diffs)})'
    oran = sum(1 for d in diffs if d < 0.5) / len(diffs)
    medyan = statistics.median(diffs)
    assert oran >= min_oran, f'{measure_id}: ±0.5pp uyum oranı {oran:.1%} < {min_oran:.0%}'
    assert medyan < 0.5, f'{measure_id}: medyan fark {medyan:.4f} beklenenden büyük'


# ------------------------------------------------------------------
# Haziran 2026 PDF'i (Rakip Analizi 202606.pdf) — esas referans (kullanıcı
# kararı 2026-09-27). Değerler PDF'ten okundu: ilk 20 listesi ve rakip trendi.
# ------------------------------------------------------------------
T = '2026-06-30'
PDF_202606 = [
    # (ölçü, fonksiyon, banka, tarih, PDF değeri, ölçek, tolerans)
    # İhtiyaç + 'Diğer' tüketici (2026-09-30; KT BDR 4.124 + 278 + 330 = 4.732 mn)
    ('ihtiyac_kredileri', m.m_ihtiyac_kredileri, 'Kuveyt Türk', T, 4732, 1e-6, 1),
    ('ihtiyac_kredileri', m.m_ihtiyac_kredileri, 'TEB', T, 57097, 1e-6, 1),
    ('ihtiyac_kredileri', m.m_ihtiyac_kredileri, 'Kuveyt Türk', '2025-12-31', 3187, 1e-6, 1),
    ('ihtiyac_toplam', m.m_ihtiyac_toplam, 'Kuveyt Türk', '2024-09-30', 0.61, 1, 0.006),
    # Mali kesim = Standart + Yakın İzlemedeki; Grup 2 tüzel payı mali kesimi çıkarmaz (2026-10-01, ING/QNB/Akbank/Vakıfbank)
    ('mali_kesim_toplam', m.m_mali_kesim_toplam, 'QNB', T, 2.66, 1, 0.006),
    ('mali_kesim_toplam', m.m_mali_kesim_toplam, 'QNB', '2026-03-31', 2.61, 1, 0.006),
    ('grup_2_tuzel_tuzel', m.m_grup_2_tuzel_tuzel, 'QNB', T, 6.33, 1, 0.006),
    ('grup_2_tuzel_tuzel', m.m_grup_2_tuzel_tuzel, 'Vakıfbank', T, 8.45, 1, 0.006),
    ('grup_2_tuzel_tuzel', m.m_grup_2_tuzel_tuzel, 'Akbank', T, 4.30, 1, 0.006),
    # TP/YP Kredi Mevduat Spread'i — vadeli mevduat tanımı PDF'ten çözüldü (2026-09-30)
    ('tp_spread', m.m_tp_spread, 'QNB', T, -411, 100, 1),
    ('tp_spread', m.m_tp_spread, 'QNB', '2025-09-30', -519, 100, 1),
    ('tp_spread', m.m_tp_spread, 'TEB', T, 58, 100, 1),
    ('tp_spread', m.m_tp_spread, 'HSBC', T, 864, 100, 1),
    ('yp_spread', m.m_yp_spread, 'Yapı Kredi', T, 576, 100, 1),
    ('yp_spread', m.m_yp_spread, 'Denizbank', '2025-12-31', 438, 100, 1),
    ('yp_spread', m.m_yp_spread, 'QNB', '2025-03-31', 481, 100, 1),
    ('yp_spread', m.m_yp_spread, 'TEB', T, 599, 100, 1),
    # Finansal varlıklar: bileşen toplamı, nakit BZK düşülmeden (2026-10-01)
    ('finansal_varliklar_net_ta', m.m_finansal_varliklar_net_ta, 'Garanti Bankası', T, 33.35, 1, 0.006),
    ('finansal_varliklar_net_ta', m.m_finansal_varliklar_net_ta, 'Albaraka', T, 41.70, 1, 0.006),
    ('finansal_varliklar_net_ta', m.m_finansal_varliklar_net_ta, 'TEB', '2025-03-31', 41.77, 1, 0.006),
    # Serbest sermaye − Yatırım Amaçlı Gayrimenkuller (2026-09-30)
    ('serbest_sermaye_ta', m.m_serbest_sermaye_ta, 'Garanti Bankası', T, 5.95, 1, 0.006),
    ('serbest_sermaye_ta', m.m_serbest_sermaye_ta, 'Vakıfbank', T, 3.82, 1, 0.006),
    ('serbest_sermaye_ta', m.m_serbest_sermaye_ta, 'Halk Bank', T, 0.45, 1, 0.006),
    ('serbest_sermaye_ta', m.m_serbest_sermaye_ta, 'Kuveyt Türk', T, 7.44, 1, 0.006),
    ('kredi_mevduat_spread', m.m_kredi_mevduat_spread, 'Kuveyt Türk', T, 988, 100, 1),
    ('kredi_mevduat_spread', m.m_kredi_mevduat_spread, 'Denizbank', T, 646, 100, 1),
    ('kredi_mevduat_spread', m.m_kredi_mevduat_spread, 'Şekerbank', T, 1331, 100, 1),
    ('kredi_mevduat_spread', m.m_kredi_mevduat_spread, 'Kuveyt Türk', '2024-09-30', 956, 100, 1),
    ('kredi_mevduat_spread', m.m_kredi_mevduat_spread, 'QNB', '2026-03-31', 559, 100, 1),
    ('kaynak_pacal_maliyet', m.m_kaynak_pacal_maliyet, 'Kuveyt Türk', T, 8.41, 1, 0.006),
    ('kaynak_pacal_maliyet', m.m_kaynak_pacal_maliyet, 'Denizbank', T, 18.71, 1, 0.006),
    ('kaynak_pacal_maliyet', m.m_kaynak_pacal_maliyet, 'Yapı Kredi', T, 16.34, 1, 0.006),
    ('brut_faaliyet_kari', m.m_brut_faaliyet_kari, 'Kuveyt Türk', T, 66119, 1e-6, 1),
    ('brut_faaliyet_kari', m.m_brut_faaliyet_kari, 'Ziraat Bankası', T, 274337, 1e-6, 1),
    # 2026-09-30: pay = kaynağa verilen faizler (repo/diğer faiz hariç)
    ('faiz_maliyetli_pasif_maliyeti', m.m_faiz_maliyetli_pasif_maliyeti, 'Kuveyt Türk', T, 14.44, 1, 0.006),
    ('faiz_maliyetli_pasif_maliyeti', m.m_faiz_maliyetli_pasif_maliyeti, 'İş Bankası', T, 23.05, 1, 0.006),
    ('faiz_maliyetli_pasif_maliyeti', m.m_faiz_maliyetli_pasif_maliyeti, 'Denizbank', T, 21.77, 1, 0.006),
    ('spread', m.m_spread, 'Şekerbank', T, 492, 100, 1),
    ('spread', m.m_spread, 'HSBC', T, 438, 100, 1),
    ('spread', m.m_spread, 'QNB', T, 217, 100, 1),
    # 2026-09-30: TP/YP kredi ayrımı kur riski tablosundan (dövize endeksli = YP)
    ('tp_krediler_toplam', m.m_tp_krediler_toplam, 'Şekerbank', T, 71.96, 1, 0.006),
    ('tp_krediler_toplam', m.m_tp_krediler_toplam, 'Yapı Kredi', T, 71.00, 1, 0.006),
    ('tp_krediler_tp_kaynak', m.m_tp_krediler_tp_kaynak, 'QNB', T, 125.63, 1, 0.006),
    ('yp_krediler_yp_altindisi_kaynak', m.m_yp_krediler_yp_altindisi_kaynak, 'Türkiye Finans', T, 108.97, 1, 0.006),
    ('tp_spread', m.m_tp_spread, 'Albaraka', T, 296, 100, 2),
    ('yp_spread', m.m_yp_spread, 'Albaraka', T, 575, 100, 2),
    # 2026-10-01 Power BI DAX'ı birebir (TP vadesiz / YP = Vadeli − TP − KM / brüt kredi ayrımı):
    ('tp_spread', m.m_tp_spread, 'Halk Bank', T, 12, 100, 1),
    ('tp_spread', m.m_tp_spread, 'Vakıfbank', T, -241, 100, 1),
    ('yp_spread', m.m_yp_spread, 'Vakıfbank', T, 507, 100, 1),
    ('tp_spread', m.m_tp_spread, 'Garanti Bankası', T, -129, 100, 1),
    ('tp_spread', m.m_tp_spread, 'İş Bankası', T, -401, 100, 1),
    ('yp_spread', m.m_yp_spread, 'İş Bankası', T, 597, 100, 1),
    ('tp_spread', m.m_tp_spread, 'Şekerbank', T, 979, 100, 1),
    ('yp_spread', m.m_yp_spread, 'Şekerbank', T, 581, 100, 1),
    ('tp_spread', m.m_tp_spread, 'Enpara', T, -428, 100, 1),
    ('yp_spread', m.m_yp_spread, 'Kuveyt Türk', T, 512, 100, 1),
]


@pytest.mark.parametrize('measure_id,fn,banka,tarih,pdf_v,olcek,tol', PDF_202606,
                         ids=[f'{x[0]}-{x[2]}-{x[3]}' for x in PDF_202606])
def test_pdf_202606_uyum(ctx, measure_id, fn, banka, tarih, pdf_v, olcek, tol):
    v = fn(ctx, banka, tarih)
    assert v is not None, f'{measure_id} {banka} {tarih}: değer yok'
    assert abs(v * olcek - pdf_v) <= tol, f'{measure_id} {banka} {tarih}: {v * olcek:.2f} ≠ PDF {pdf_v}'


def test_tuketici_kk_haric_bdr_toplami(ctx):
    """2026-09-30: KK hariç tüketici kredisi tablonun 'Toplam' satırından —
    BDR toplamları (mn TL, kartlar dahil): YK 881.201 (ham veride kopya KMH-YP
    satırı var), Garanti 1.124.361, TEB 127.483."""
    kart = lambda b: sum(ctx.tk_detay(b, T, k) for k in m._KART_KALEMLERI)
    for banka, bdr in [('Yapı Kredi', 881201), ('Garanti Bankası', 1124361), ('TEB', 127483)]:
        assert abs((m.tuketici_kredileri_kk_haric(ctx, banka, T) + kart(banka)) / 1e6 - bdr) < 1


def test_risk_kart_vade_bdr(ctx):
    """2026-10-01 BDR sağlaması: Toplam Risk = toplam RAV (KT 861.892, Garanti
    3.409.452, TEB 643.547); kredi kartı = Grup 1 + Grup 2 kart kredileri; katılım
    bankasında vadeli vade dilimleri katılım fonu tablosundan."""
    beklenen = {'Kuveyt Türk': (861_892, 74.18, 137_461), 'Garanti Bankası': (3_409_452, 85.60, 748_887),
                'TEB': (643_547, 83.33, 70_795)}
    for banka, (risk, kredi_pay, kart) in beklenen.items():
        assert abs(m.m_toplam_risk_tabani(ctx, banka, T) / 1e6 - risk) < 1
        assert abs(m.m_kredi_riski_toplam_risk(ctx, banka, T) - kredi_pay) < 0.006
        assert abs(m.m_toplam_kredi_kartlari(ctx, banka, T) / 1e6 - kart) < 1
    vade = [m.m_vadeli_1ay_toplam_vadeli, m.m_vadeli_1_3ay_toplam_vadeli,
            m.m_vadeli_3_6ay_toplam_vadeli, m.m_vadeli_6_12ay_toplam_vadeli]
    assert [round(f(ctx, 'Kuveyt Türk', T), 2) for f in vade] == [44.35, 42.14, 3.51, 8.99]


def test_halk_2025_03_net_kar_raporlanan(ctx):
    """2026-10-01 veri düzeltmesi (pipeline/veri_duzeltmeleri.py): Halk Mart 2025 net kâr
    raporlanan 7.051 mn; ROAE/ROAA/RORWA çeyreklik değişimi PDF ile birebir (90 / 1 / 8 bps)."""
    assert abs(ctx.gelir('Halk Bank', '2025-03-31', 'Net Dönem Karı / Zararı') / 1e6 - 7050.953) < 0.01
    assert abs(ctx.gelir('Halk Bank', '2025-06-30', 'Net Dönem Karı / Zararı') / 1e6 - 12032.19) < 0.01  # dokunulmaz
    for f, pdf in [(m.m_roae, 90), (m.m_roaa, 1), (m.m_rorwa, 8)]:
        d = (f(ctx, 'Halk Bank', '2026-06-30') - f(ctx, 'Halk Bank', '2026-03-31')) * 100
        assert round(d) == pdf


def test_enpara_subesiz_2025_09_duzeltmesi():
    """Enpara şubesiz banka: 2025-09 ham 'Şube Sayısı = 1' düzeltmesi sonrası şube
    başına ölçüler hiçbir dönemde değer üretmez (payda 0)."""
    from pipeline.veri_duzeltmeleri import DUZELTMELER
    d = next(x for x in DUZELTMELER if x['banka'] == 'Enpara')
    assert (d['beklenen'], d['deger']) == (1.0, 0.0)


def test_teb_denizbank_bdr_duzeltmeleri():
    """2026-10-01 BDR doğrulaması (TEB 2024-06/2024-09/2024-12/2025-03, Denizbank 2024-09/12):
    ham gelir tablosu ve V. Grup intikal değerleri BDR'ye çekildi; PDF noktalarıyla tutar."""
    from pipeline.veri_duzeltmeleri import DUZELTMELER
    teb = [d for d in DUZELTMELER if d['banka'] == 'TEB']
    dz = [d for d in DUZELTMELER if d['banka'] == 'Denizbank' and d['tablo'].startswith('Toplam Donuk')]
    assert len(teb) == 11 and len(dz) == 2
    assert all(abs(d['deger'] - d['beklenen']) > 1e6 for d in teb + dz)
    dp = {d['kalem']: d for d in DUZELTMELER if d['banka'] == 'Denizbank' and d['tablo'] == 'Şube-Personel'}
    assert dp['Personel Sayısı']['deger'] == 11972.0 and dp['Şube Sayısı']['deger'] == 576.0
