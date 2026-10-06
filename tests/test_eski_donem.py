"""Eski dönem (2013-2018) veri tamamlama testleri (2026-10-03).

BDDK şablonu TFRS 9 (2018-01-01) ile değişti; eski dönem dosyalarında aynı kavramlar farklı kalem
adlarıyla (ve kalem adlarında fazladan / bölünmez boşluklarla) geliyor, bazı 2018 dosyalarında da
geçiş hataları var. pipeline/lookup.py ve pipeline/measures.py bunları eşliyor; testler ham veriyle
(data/veriler.parquet) çalışır, dosya yoksa atlanır.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from pipeline.lookup import LookupContext, kalem_norm, krediler
from pipeline import measures as M

ROOT = Path(__file__).resolve().parent.parent
PARQUET = ROOT / 'data' / 'veriler.parquet'
CATALOG = ROOT / 'data' / 'catalog.json'

pytestmark = pytest.mark.skipif(not (PARQUET.exists() and CATALOG.exists()), reason='ham veri yok')


@pytest.fixture(scope='module')
def ctx():
    cat = json.loads(CATALOG.read_text(encoding='utf-8'))
    return LookupContext.from_parquet(PARQUET, {b['banka_adi']: b['tur'] for b in cat['banks']})


T = pd.Timestamp


def test_kalem_norm_bosluklari_tekler():
    assert kalem_norm('İştirakler (Net)  ') == 'İştirakler (Net)'
    assert kalem_norm('Personel Kredileri - YP, Toplam ') == 'Personel Kredileri - YP, Toplam'
    assert kalem_norm('Tüketici Kredileri,  Standart Nitelikli') == 'Tüketici Kredileri, Standart Nitelikli'


def test_eski_sablon_ortaklik_ve_npl_karsilama(ctx):
    # 2013-2017'de 'Ortaklık Yatırımları' ve 'Beklenen Zarar Karşılıkları' satırları yok
    t = T('2015-06-30')
    assert ctx.bilanco('Akbank', t, 'Ortaklık Yatırımları') > 0
    npl = M.m_npl_karsilama_orani(ctx, 'Akbank', t)
    assert npl is not None and 100 < npl < 250
    assert M.m_donuk_alacaklar_satis_terkin_oncesi(ctx, 'Akbank', t) > 0


def test_eski_sablon_cost_of_risk_ve_maliyet(ctx):
    t = T('2016-12-31')
    cor = M.m_cost_of_risk(ctx, 'Akbank', t)
    assert cor is not None and 0.3 < cor < 4
    # 2018 öncesinde personel 'Diğer Faaliyet Giderleri'nin içinde: iki kez sayılmamalı
    dfg = ctx.gelir('Akbank', t, 'Diğer Faaliyet Giderleri (-)')
    assert M._opex(ctx, 'Akbank', t) == pytest.approx(dfg)
    assert M.m_personel_giderleri(ctx, 'Akbank', t) > 0


def test_2018_12_personel_iki_kat_hatasi(ctx):
    # 2018-12 ham 'Personel Giderleri (-)' satırı 17 bankada dipnotun 2 katı
    t = T('2018-12-31')
    ham = ctx._lookup('gelir', 'Akbank', t, 'Personel Giderleri (-)', 'Toplam')
    dipnot = ctx._lookup('faaliyet_gid_detay', 'Akbank', t, 'Personel Giderleri', 'Toplam')
    assert ham == pytest.approx(2 * dipnot, rel=0.15)
    assert ctx.personel_giderleri('Akbank', t) == pytest.approx(dipnot)


def test_2018_ara_donem_krediler_tam(ctx):
    # 2018-06/09'da '(Toplam)' satırı yalnız canlı kredileri taşıyor (donuk, kiralama, faktoring yok)
    t = T('2018-06-30')
    kva = ctx.bilanco('Akbank', t, 'Krediler Ve Alacaklar')
    donuk = ctx.bilanco('Akbank', t, 'Donuk Alacaklar')
    assert donuk > 0
    assert krediler(ctx, 'Akbank', t) >= kva + donuk


def test_2018_03_beklenen_zarar_asamalardan(ctx):
    assert ctx.bilanco('Akbank', T('2018-03-31'), 'Beklenen Zarar Karşılıkları (-)') != 0


def test_rav_eski_donem_syr_ile_tutarli(ctx):
    # 2014'te RAV satırı boş, 2015'te ağırlıksız risk tutarı: özkaynak / RAV bildirilen SYR'yi vermeli
    for t in ('2014-06-30', '2015-06-30'):
        rav = M.toplam_rav(ctx, 'Akbank', T(t))
        syr = M.m_syr(ctx, 'Akbank', T(t))
        assert M.regulasyon_ozkaynak(ctx, 'Akbank', T(t)) / rav * 100 == pytest.approx(syr, abs=0.15)
    # 2016 sonrası tutarlı ham satır olduğu gibi kalır (BDR sağlaması)
    t = T('2025-12-31')
    assert M.toplam_rav(ctx, 'Kuveyt Türk', t) == ctx.sermaye('Kuveyt Türk', t, 'Kredi Riskine Esas Tutar: Toplam')


def test_syr_ve_ozkaynak_ozet_tablodan(ctx):
    # 2014 katılım bankalarında oran tablosu boş; sermaye yeterliliği özetinden gelir
    t = T('2014-06-30')
    assert M.m_syr(ctx, 'Kuveyt Türk', t) == pytest.approx(15.6, abs=0.01)
    assert M.regulasyon_ozkaynak(ctx, 'Kuveyt Türk', t) > 0


def test_bos_oran_sifir_degil_yok(ctx):
    # Çekirdek sermaye oranı 2014'te bildirilmemiş: 0 yerine "yok"
    assert M.m_cekirdek_syr(ctx, 'Akbank', T('2014-06-30')) is None


def test_tuketici_kredileri_parcalardan(ctx):
    t = T('2014-06-30')
    assert ctx.tk_detay('HSBC', t, 'Krediler ve K. Kartları (Tüketici ve Personel, Toplam)') == 0
    assert M.m_tuketici_kredileri(ctx, 'HSBC', t) > 4e9


# --- Eski dönem NPL doğrulaması (2026-10-03): pano 2018-03 öncesini bu testlere dayanarak gösteriyor ---
_NPL_SINIFLAR = ('Sınırlı', 'Şüpheli', 'Zarar Niteliğinde')


def _bankalar():
    cat = json.loads(CATALOG.read_text(encoding='utf-8'))
    return [b['banka_adi'] for b in cat['banks']]


def test_eski_npl_pay_bagimsiz_tabloyla_ayni(ctx):
    # Bilançodaki 'Takipteki Krediler' = donuk alacak hareket tablosunun dönem sonu bakiyesi (3+4+5. grup)
    from pipeline.lookup import donuk_alacaklar
    n = tutarli = 0
    for t in pd.date_range('2013-12-31', '2017-12-31', freq='QE'):
        for b in _bankalar():
            d = donuk_alacaklar(ctx, b, t)
            akim = sum(ctx.donuk_akim(b, t, f'Donuk Alacaklar ({s}, Dönem Sonu)') for s in _NPL_SINIFLAR)
            if d and akim:
                n += 1
                tutarli += abs(akim - d) <= max(1e3, 0.05 * d)
    assert n > 300 and tutarli / n >= 0.99, (tutarli, n)


def test_eski_npl_payda_brut(ctx):
    # Eski şablonda '(Toplam)' = Krediler + Takipteki − Özel Karşılık (net); payda brüte çevrilmeli
    n = tutarli = 0
    for t in pd.date_range('2013-12-31', '2017-12-31', freq='QE'):
        for b in _bankalar():
            top = ctx.bilanco(b, t, 'Krediler Ve Alacaklar (Toplam)')
            tak = ctx.bilanco(b, t, 'Takipteki Krediler')
            if not (top and tak):
                continue
            n += 1
            net = ctx.bilanco(b, t, 'Krediler Ve Alacaklar') + tak - abs(ctx.bilanco(b, t, 'Özel Karşılıklar (-)'))
            tutarli += abs(top - net) <= max(1e4, 1e-4 * top)
            assert M.npl_payda(ctx, b, t) >= ctx.bilanco(b, t, 'Krediler Ve Alacaklar') + tak - 1
    assert n > 300 and tutarli / n >= 0.98, (tutarli, n)


def test_eski_npl_sektor_seviyesi_ve_sureklilik(ctx):
    # Örneklem toplamı BDDK sektör NPL seyriyle uyumlu (2013-2017 ≈ %2,7-3,4) ve şablon
    # geçişinde (2017-12 → 2018-03) sıçrama yok.
    from pipeline.lookup import donuk_alacaklar

    def toplam(t):
        pay = sum(donuk_alacaklar(ctx, b, T(t)) for b in _bankalar())
        payda = sum(M.npl_payda(ctx, b, T(t)) for b in _bankalar())
        return pay / payda * 100

    for t in ('2013-12-31', '2014-12-31', '2015-12-31', '2016-12-31', '2017-12-31'):
        assert 2.4 <= toplam(t) <= 3.6, (t, toplam(t))
    assert abs(toplam('2018-03-31') - toplam('2017-12-31')) <= 0.3
