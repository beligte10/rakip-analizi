"""
pipeline.cikti_ingest
======================
BDR-Kısayol'un `<DÖNEM>.json` çıktısını (bkz. VERI-FORMATI.md) Rakip
Analizi'nin mevcut long-format ara formatına (Banka Adı/Tarih/Tablo Türü/
Tablo Adı/Kalem Adı/Para Birimi/Tutar) dönüştürür.

Tasarım kararı: pipeline.lookup.LookupContext ve pipeline.measures hiç
değişmiyor — bu modül sadece ALTERNATİF bir ham-kaynak → ara-format
üreticisi. Faz 1 (destekleyici/test): bu modül hiçbir dosyaya yazmaz, saf
fonksiyonlardan oluşur, HTTP'den habersizdir.

Kapsam (bkz. plan): kayıtlar (Grup 1, tam), dipnot'un doğrulanmış 7 tablosu
(kalan_vade, mvy, tfv, sermaye_ozet, risk_agirlikli, tk_detay, grup12,
faaliyet_gid_detay, donuk_akim) ve olgular (şube/personel). `tfv` bazı
katılım bankalarında eksik gelebilir (kaynağın kendi sınırlaması).
kur_riski_konsolide (ayrı "konsolide" dosyadan gelir) ve ozkaynak_degisim
(kolon anlamı banka bazında değişken, hiçbir measure kullanmıyor) bu turda
KAPSAM DIŞI.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

import pandas as pd

# --- Banka adı eşlemesi (VERI-FORMATI.md §8) --------------------------------

BANK_NAME_MAP: Dict[str, str] = {
    'DenizBank': 'Denizbank',
    'Garanti BBVA': 'Garanti Bankası',
    'Halkbank': 'Halk Bank',
    'ING': 'ING Bank',
    'QNB': 'QNB Finansbank',
    'VakıfBank': 'Vakıfbank',
}


def normalize_bank_name(banka: str) -> str:
    return BANK_NAME_MAP.get(banka, banka)


# --- Birim normalizasyonu (VERI-FORMATI.md §10 — birim dönemden döneme değişir) --

def normalize_birim(deger: Optional[float], birim: str) -> Optional[float]:
    if deger is None:
        return None
    if birim == 'milyon':
        return deger * 1_000_000
    if birim == 'bin':
        return deger * 1_000
    raise ValueError(f"Bilinmeyen birim: {birim!r}")


# --- Dönem <-> tarih --------------------------------------------------------

_CEYREK_AY_GUN = {'1': '03-31', '2': '06-30', '3': '09-30', '4': '12-31'}


def donem_to_tarih(donem: str) -> str:
    """'2026-2C' -> '2026-06-30'."""
    yil, ceyrek = donem.split('-')
    ceyrek = ceyrek.rstrip('Cc')
    return f"{yil}-{_CEYREK_AY_GUN[ceyrek]}"


def fy_onceki_tarih(cari_tarih: str) -> str:
    """Bilanço/stok kalemleri: onceki = önceki YIL SONU (fiscal year-end)."""
    yil = int(cari_tarih[:4])
    return f"{yil - 1}-12-31"


def yoy_tarih(cari_tarih: str) -> str:
    """Akış/YtD kalemleri (gelir tablosu, nakit akış): onceki = YoY aynı çeyrek."""
    yil, ay_gun = cari_tarih.split('-', 1)
    return f"{int(yil) - 1}-{ay_gun}"


_ROMAN_RE = re.compile(r'^[IVXLCDM]+$')


def _is_roman(kod: str) -> bool:
    return bool(_ROMAN_RE.match(kod))


# --- Grup 1 (kayitlar) — tablo -> Tablo Adı ---------------------------------

_STOK_TABLOLAR = {
    'bilanco_varliklar': 'Bilanço',
    'bilanco_yukumlulukler': 'Bilanço',
    'nazim_hesaplar': 'Bilanço Dışı Yükümlülükler',
}
_AKIS_TABLOLAR = {
    'kar_zarar': 'Gelir Tablosu',
    'kar_zarar_kapsamli_gelir': 'Kapsamlı Gelir Tablosu',
    'nakit_akis': 'Nakit Akış Tablosu',
    'kar_dagitim': 'Kâr Dağıtım Tablosu',
}

# Rakip Analizi'nin pipeline/measures.py'de LİTERAL olarak referans ettiği
# üst-düzey (Roma rakamı) satırlar — çıktı'da TÜMÜ BÜYÜK HARF veya BDDK'nın
# güncel şablonundaki farklı kelimeyle geliyor, bu yüzden birebir kopyalanamaz.
# Anahtar: (tablo, kod) -> measures.py'nin beklediği BİREBİR kalem metni.
_ROMAN_OVERRIDES: Dict[tuple, str] = {
    # bilanco_varliklar
    ('bilanco_varliklar', 'I'): 'Finansal Varlıklar (Net)',
    ('bilanco_varliklar', 'IV'): 'Ortaklık Yatırımları',
    ('bilanco_varliklar', 'V'): 'Maddi Duran Varlıklar (Net)',
    ('bilanco_varliklar', 'VI'): 'Maddi Olmayan Duran Varlıklar (Net)',
    # bilanco_yukumlulukler
    ('bilanco_yukumlulukler', 'I'): 'Mevduat',
    ('bilanco_yukumlulukler', 'II'): 'Alınan Krediler',
    ('bilanco_yukumlulukler', 'III'): 'Para Piyasalarına Borçlar',
    ('bilanco_yukumlulukler', 'IV'): 'İhraç Edilen Menkul Kıymetler (Net)',
    ('bilanco_yukumlulukler', 'XIV'): 'Sermaye Benzeri Krediler',
    ('bilanco_yukumlulukler', 'XVI'): 'Özkaynaklar',
    # kar_zarar
    ('kar_zarar', 'I'): 'Faiz Gelirleri',
    ('kar_zarar', 'II'): 'Faiz Giderleri',
    ('kar_zarar', 'III'): 'Net Faiz Geliri/Gideri',
    ('kar_zarar', 'IV'): 'Net Ücret Ve Komisyon Gelirleri/Giderleri',
    ('kar_zarar', 'VI'): 'Ticari Kar/Zarar (Net)',
    ('kar_zarar', 'XI'): 'Personel Giderleri (-)',
    ('kar_zarar', 'XII'): 'Diğer Faaliyet Giderleri (-)',
    ('kar_zarar', 'XIII'): 'Net Faaliyet Karı/Zararı',
    ('kar_zarar', 'XXV'): 'Net Dönem Karı / Zararı',
    # nazim_hesaplar kod I -> Rakip Analizi'nin 'bd' tablosundaki sentetik adı
    ('nazim_hesaplar', 'I'): 'Garanti Ve Kefaletler, Toplam',
}

# Kod eşleşmesi katılım/mevduat şablonuna göre kayabilir (VERI-FORMATI §4.3 —
# ama doküman bunun çıktı tarafında zaten normalize edildiğini söylüyor,
# yani _ROMAN_OVERRIDES tabloda hem mevduat hem katılım bankaları için aynı
# kod->kalem eşlemesi geçerli olmalı).

_SENTETIK_TOPLAM = {
    'bilanco_varliklar': 'Toplam Aktifler',
    'bilanco_yukumlulukler': 'Toplam Pasifler',
}

# Rakip Analizi'nin raw'ında bazı BÜYÜKLÜKLERİN İKİ AYRI kalem adıyla aynı satır
# değeriyle bulunması gerekiyor (pipeline/measures.py'nin _brut_krediler'i
# 'Krediler Ve Alacaklar' (parantezsiz, ham/brüt) kullanırken, krediler()
# helper'ı 'Krediler Ve Alacaklar (Toplam)' arıyor ve bulamazsa legacy
# 'Krediler'e düşüyor — çıktı'daki kod 2.1 zaten 'Krediler' adıyla geldiği
# için krediler() sorunsuz çalışıyor, ama _brut_krediler'in bare adı EK bir
# alias olarak ayrıca yazılmalı).
_EXTRA_ALIASES: Dict[tuple, List[str]] = {
    ('bilanco_varliklar', '2.1'): ['Krediler Ve Alacaklar'],
    # kod II'nin GRAND TOTAL'i değil, alt kalemi 2.4 ('...Diğer Finansal
    # Varlıklar') Rakip'in 'İtfa Edilmiş Maliyeti ile Ölçülen Finansal
    # Varlıklar' kalemine karşılık geliyor (finansal_varliklar_net_ta ile
    # doğrulandı — kod II'nin NET toplamını kullanmak %92 gibi anlamsız
    # yüksek bir oran veriyordu, 2.4 ile %39-40 bandına düşüyor).
    ('bilanco_varliklar', '2.4'): ['İtfa Edilmiş Maliyeti ile Ölçülen Finansal Varlıklar'],
}

# Rakip Analizi'nin ham verisinde 've'/'ile' bağlaçları TUTARSIZ şekilde
# büyük harfle yazılıyor ('Krediler Ve Alacaklar', 'Nakit Değerler Ve Merkez
# Bankası', 'Alınan Ücret Ve Komisyonlar' gibi — hepsi capital 'Ve'), çıktı'nın
# kalem metni ise düzgün Türkçe gramerle küçük harf kullanıyor ('ve'). Her
# kayıt satırı için, farklıysa, bağlaçları büyük harfe çevrilmiş bir alias da
# ayrıca yazılır (iki farklı kalem adı altında aynı değer — LookupContext
# exact-dict-key kullandığı için zararsız).
_CONNECTOR_RE = re.compile(r'\b(ve|ile)\b')
_CONNECTOR_UPPER = {'ve': 'Ve', 'ile': 'İle'}  # Python .capitalize() 'ile'->'Ile' üretir, Türkçe 'İle' değil


def _connector_alias(kalem: str) -> Optional[str]:
    alias = _CONNECTOR_RE.sub(lambda m: _CONNECTOR_UPPER[m.group(1)], kalem)
    return alias if alias != kalem else None


_TRAILING_EKSI_RE = re.compile(r'\s*\(-\)\s*$')


def _kalem_variants(kalem: str) -> List[str]:
    """Bağlaç büyük/küçük harfi ve sondaki '(-)' işareti Rakip Analizi'nin
    ham verisinde tutarsız — dört varyantın hepsi (gerekirse) üretilir."""
    variants = {kalem}
    stripped = _TRAILING_EKSI_RE.sub('', kalem)
    variants.add(stripped)
    for v in list(variants):
        alias = _connector_alias(v)
        if alias:
            variants.add(alias)
    variants.discard(kalem)
    return list(variants)


def _emit(rows: List[dict], banka: str, tarih: str, tablo_turu: str,
          tablo_adi: str, kalem: str, pb: str, tutar: Optional[float]) -> None:
    if tutar is None:
        return
    rows.append({
        'Banka Adı': banka, 'Tarih': tarih, 'Tablo Türü': tablo_turu,
        'Tablo Adı': tablo_adi, 'Kalem Adı': kalem, 'Para Birimi': pb,
        'Tutar': tutar,
    })


def convert_kayitlar(kayitlar: List[dict]) -> List[dict]:
    """Grup 1 (kayitlar) -> long-format satırlar.

    Her kayıt TP/YP/Toplam için ayrı satır, cari VE onceki için ayrı Tarih.
    Stok tablolarında (bilanço/nazım hesaplar) onceki = önceki yıl sonu;
    akış tablolarında (gelir tablosu vb.) onceki = YoY aynı çeyrek — bu,
    pipeline/lookup.py'nin kendi ttm_flow()'unun kullandığı YoY kuralıyla
    tutarlı.
    """
    rows: List[dict] = []
    # Toplam Aktifler/Pasifler sentezi için roman satırları biriktir.
    roman_sums: Dict[tuple, dict] = {}

    for rec in kayitlar:
        banka = normalize_bank_name(rec['banka'])
        tablo = rec['tablo']
        kod = rec['kod']
        birim = rec['birim']
        cari_tarih = donem_to_tarih(rec['donem'])

        if tablo in _STOK_TABLOLAR:
            tablo_adi = _STOK_TABLOLAR[tablo]
            onceki_tarih = fy_onceki_tarih(cari_tarih)
        elif tablo in _AKIS_TABLOLAR:
            tablo_adi = _AKIS_TABLOLAR[tablo]
            onceki_tarih = yoy_tarih(cari_tarih)
        else:
            continue  # bilinmeyen/işlenmeyen tablo tipi

        kalem_ana = _ROMAN_OVERRIDES.get((tablo, kod), rec['kalem'])
        kalemler = [kalem_ana]
        kalemler.extend(_EXTRA_ALIASES.get((tablo, kod), []))
        kalemler.extend(_kalem_variants(kalem_ana))
        # "(-)" ile biten kalemler (Faiz/Personel/Diğer Faaliyet Giderleri,
        # Verilen Ücret ve Komisyonlar vb.) Rakip Analizi'nin ham verisinde
        # HER ZAMAN pozitif büyüklük olarak tutuluyor (doğrulandı: Akbank,
        # Türkiye Finans, ING Bank'ın kendi ham parquet satırları) — BDDK
        # etiketindeki "(-)" yalnız formülde çıkarılacağını belirtiyor,
        # değerin kendisi negatif değil. Ama BDR PDF'lerinin bazılarında
        # (ölçüldü: ING Bank, Türkiye Finans) bu satırlar parantez içinde
        # ("(9.870.896)") yani GERÇEKTEN negatif basılıyor — ayrıştırıcımız
        # bunu doğru okuyor ama Rakip'in her zaman-pozitif konvansiyonuyla
        # çelişiyor. `abs()` diğer 25 bankada no-op, bu 2 bankada düzeltiyor.
        zorla_pozitif = kalem_ana.strip().endswith('(-)')

        for blok, tarih in (('cari', cari_tarih), ('onceki', onceki_tarih)):
            blok_deger = rec.get(blok)
            if not blok_deger:
                continue
            for alan, pb in (('tp', 'TP'), ('yp', 'YP'), ('toplam', 'Toplam')):
                if alan not in blok_deger:
                    continue
                tutar = normalize_birim(blok_deger.get(alan), birim)
                if zorla_pozitif and tutar is not None:
                    tutar = abs(tutar)
                for kalem in kalemler:
                    _emit(rows, banka, tarih, 'Ana Tablo', tablo_adi, kalem, pb, tutar)

        # Toplam Aktifler/Pasifler sentezi: yalnız üst-düzey (roma) satırlar,
        # TP/YP/Toplam'ın hepsi (tp_aktifler_ta gibi ölçüler TP kırılımını
        # istiyor).
        if tablo in _SENTETIK_TOPLAM and _is_roman(kod):
            key = (banka, tablo)
            acc = roman_sums.setdefault(key, {
                'cari': {'tp': 0.0, 'yp': 0.0, 'toplam': 0.0},
                'onceki': {'tp': 0.0, 'yp': 0.0, 'toplam': 0.0},
            })
            for blok in ('cari', 'onceki'):
                blok_deger = rec.get(blok)
                if not blok_deger:
                    continue
                for alan in ('tp', 'yp', 'toplam'):
                    if blok_deger.get(alan) is not None:
                        acc[blok][alan] += normalize_birim(blok_deger[alan], birim)

    # Sentetik Toplam Aktifler/Pasifler satırlarını yaz.
    donem_by_banka_tablo: Dict[tuple, tuple] = {}
    for rec in kayitlar:
        if rec['tablo'] in _SENTETIK_TOPLAM:
            banka = normalize_bank_name(rec['banka'])
            cari_tarih = donem_to_tarih(rec['donem'])
            donem_by_banka_tablo[(banka, rec['tablo'])] = (
                cari_tarih, fy_onceki_tarih(cari_tarih)
            )
    for (banka, tablo), sums in roman_sums.items():
        kalem = _SENTETIK_TOPLAM[tablo]
        cari_tarih, onceki_tarih = donem_by_banka_tablo[(banka, tablo)]
        for blok, tarih in (('cari', cari_tarih), ('onceki', onceki_tarih)):
            for alan, pb in (('tp', 'TP'), ('yp', 'YP'), ('toplam', 'Toplam')):
                _emit(rows, banka, tarih, 'Ana Tablo', 'Bilanço', kalem, pb, sums[blok][alan] or None)

    return rows


# --- Grup 2 (dipnot) --------------------------------------------------------

# pipeline/lookup.py'nin gerçekte beklediği tablo adları (docstring'lerinden
# birebir alınmış — bazıları BDDK şablonunda mislabeled/karışık kullanılıyor,
# bkz. lookup.py'deki notlar).
_TABLO_ADI = {
    'kalan_vade': 'Aktif ve Pasif Kalemlerin Kalan Vadelerine Göre Gösterimi',
    'mvy': 'Mevduatın Vade Yapısına İlişkin Bilgiler',
    'tfv': 'Toplanan Fonların Vade Yapısına İlişkin Bilgiler',
    'sermaye': 'Finansal Varlık ve Borçların Gerçeğe Uygun Değerlerine İlişkin Bilgiler',
    'tcmb': 'Nakit Değerler ve TCMB’ye İlişkin Bilgiler',
    'ozkaynak_detay': 'Özkaynak Kalemlerine İlişkin Bilgiler',
    'tk_detay': 'Tüketici Kredileri, Bireysel Kredi Kartları, Personel Kredileri ve Personel Kredi Kartlarına İlişkin Bilgiler',
    'grup12': 'Birinci ve İkinci Grup Krediler, Diğer Alacaklar ile Sözleşme Koşullarında Değişiklik Yapılan Kredilere İlişkin Bilgiler',
    'faaliyet_gid_detay': 'Diğer Faaliyet Giderlerine İlişkin Bilgiler',
    'donuk_akim': 'Toplam Donuk Alacaklara İlişkin Bilgiler',
    'sermaye_orani': 'Kredilere İlişkin Olarak Ayrılan Özel Karşılıklar',
}

# _LIKIDITE_ACIGI_KALEM (measures.py) ile birebir — ham veride 'Likitide' yazım
# hatası korunuyor, kolon sırası kalan_vade'nin 8 kolonuyla (Vadesiz, 1 Aya
# Kadar, 1-3 Ay, 3-12 Ay, 1-5 Yıl, 5 Yıl ve Üzeri, Dağıtılamayan, Toplam) aynı.
_KALAN_VADE_KOLONLAR = [
    'Vadesiz', '1 Aya Kadar', '1-3 Ay', '3-12 Ay', '1-5 Yıl', '5 Yıl Ve Üzeri', 'Dağıtılamayan',
]


def _convert_kalan_vade(rows_in: List[dict], banka: str, tarih: str, birim: str, out: List[dict]) -> None:
    """kalan_vade: 8 kolon (7 vade dilimi + Toplam). Sadece 'Likidite Fazlası /
    (Açığı)' satırı Rakip Analizi'nde kullanılıyor (7 likidite_acigi_* ölçüsü)."""
    for r in rows_in:
        kalem_ham = r['kalem']
        degerler = r['degerler']
        if not kalem_ham or ('Likidite' not in kalem_ham and 'Likitide' not in kalem_ham):
            continue
        for i, kolon in enumerate(_KALAN_VADE_KOLONLAR):
            if i >= len(degerler) - 1:
                break
            _emit(out, banka, tarih, 'Dipnot', _TABLO_ADI['kalan_vade'],
                  f'Kalan Vadelerine Göre, Likitide Açığı, {kolon}', 'Toplam',
                  normalize_birim(degerler[i], birim))


# mvy/tfv 'Toplam' satırının 8 kolonu (2026-09-13'te bdr-kisayol-main'in
# dipnot.py'si düzeltildi — Vadesiz artık kalem metnine gömülü değil, KENDİ
# kolonu: [Vadesiz, 1 Aya Kadar, 1-3 Ay, 3-6 Ay, 6-12 Ay, 1 Yıl ve Üzeri,
# Birikimli, TOPLAM_MEVDUAT]. Mevduat/katılım şablonuna göre kalem adları
# FARKLI (ctx.vadesiz_mevduat / ctx.mvy / ctx.tfv, pipeline/measures.py'den
# birebir).
_MVY_BUCKET_KALEM = ['Toplam, 1 Aya Kadar', 'Toplam, 1-3 Ay', 'Toplam, 3-6 Ay', 'Toplam, 6 Ay-1 Yıl']
_TFV_BUCKET_KALEM: List[str] = []  # katılım vade dilimleri measures.py'de kullanılmıyor (branching yapılmamış)


# Kategori satırları (Resmi/Ticari/Diğer Kuruluşlar Mevduatı, Kıymetli Maden
# Depo Hesabı) -> ctx.resmi_kurumlar/tuzel_mevduat/kiymetli_maden'in beklediği
# kalemler (pipeline/lookup.py'den birebir). Yalnız satırın SON kolonu
# (Toplam) kullanılır; satır başlığı embedded sayı taşıyor ('Resmi Kuruluşlar
# Mevduatı 23.375' gibi), bu yüzden prefix eşleşmesi kullanılıyor.
_MVY_KATEGORI_PREFIX = {
    'Resmi Kuruluşlar Mevduatı': 'Resmi Kur. Mevduatı, Toplam',
    'Ticari Kuruluşlar Mevduatı': 'Tic. Kur. Mevduatı, Toplam',
    'Diğer Kuruluşlar Mevduatı': 'Diğ. Kur. Mevduatı, Toplam',
    'Kıymetli Maden Depo Hesabı': 'Kıymetli Maden DH, Toplam',
}
_TFV_KATEGORI_PREFIX = {
    'Resmi Kuruluşlar': 'Resmi Kuruluşlar  Toplam',
    'Ticari Kuruluşlar': 'Ticari Kuruluşlar  Toplam',
    'Diğer Kuruluşlar': 'Diğer Kuruluşlar  Toplam',
    'Kıymetli Maden DH': 'Kıymetli Maden DH  Toplam',
}


def _convert_mvy_tfv(rows_in: List[dict], banka: str, tarih: str, birim: str, out: List[dict],
                      tablo: str) -> None:
    """mvy/tfv: 'Toplam' satırı (vade dilimleri + vadesiz mevduat) ve kategori
    satırları (resmi/ticari/diğer kuruluşlar, kıymetli maden) işlenir."""
    tablo_adi = _TABLO_ADI[tablo]
    vadesiz_kalem = 'Toplam, Vadesiz' if tablo == 'mvy' else 'Toplam Vadesiz'
    birikimli_kalem = 'Toplam, Birikimli' if tablo == 'mvy' else 'Toplam  Birikimli Katılma Hesabı'
    bucket_kalem = _MVY_BUCKET_KALEM if tablo == 'mvy' else _TFV_BUCKET_KALEM
    kategori_prefix = _MVY_KATEGORI_PREFIX if tablo == 'mvy' else _TFV_KATEGORI_PREFIX

    for r in rows_in:
        kalem_ham = r['kalem']
        if not kalem_ham:
            continue
        kalem_strip = kalem_ham.strip()
        degerler = r['degerler']

        if kalem_strip == 'Toplam':
            # degerler = [Vadesiz, 1 Ay, 1-3 Ay, 3-6 Ay, 6-12 Ay, 1 Yıl+, Birikimli, TOPLAM]
            if degerler and degerler[0] is not None:
                _emit(out, banka, tarih, 'Dipnot', tablo_adi, vadesiz_kalem, 'Toplam', normalize_birim(degerler[0], birim))
            for i, kalem in enumerate(bucket_kalem):
                idx = i + 1
                if idx >= len(degerler):
                    break
                _emit(out, banka, tarih, 'Dipnot', tablo_adi, kalem, 'Toplam', normalize_birim(degerler[idx], birim))
            if len(degerler) >= 7 and degerler[6] is not None:
                _emit(out, banka, tarih, 'Dipnot', tablo_adi, birikimli_kalem, 'Toplam', normalize_birim(degerler[6], birim))
            continue

        for prefix, kalem in kategori_prefix.items():
            if prefix in kalem_strip and degerler and degerler[-1] is not None:
                _emit(out, banka, tarih, 'Dipnot', tablo_adi, kalem, 'Toplam', normalize_birim(degerler[-1], birim))
                break


def _convert_sermaye_risk(rows_in: List[dict], banka: str, cari_tarih: str,
                           onceki_tarih: str, birim: str, out: List[dict]) -> None:
    """risk_agirlikli'nin toplam RAV satırı -> ctx.sermaye'nin
    'Kredi Riskine Esas Tutar: Toplam' kalemi (PBI [Toplam RAV] DAX'ı SADECE bu
    kalemi okuyor — bkz. pipeline/measures.py m_rav docstring'i — BDDK şablonunda
    yanlış adlandırılmış ama sayısal olarak toplam RAV'a eşit, doğrulandı).
    risk_agirlikli'nin 'Piyasa riski'/'Operasyonel risk' satırları -> ctx.tcmb'nin
    'Sermaye Std. Oranı, ... Riskine Esas Tutar (Pret/Oret)' kalemleri.
    sermaye_ozet'in 'Toplam Özkaynak (...)' satırı -> ctx.ozkaynak_detay'ın
    'Toplam Ozkaynaklar' kalemi (BDDK ham veride 'Ö'süz/'ı'sız yazılı).

    NOT (2026-09-12 düzeltmesi): toplam RAV satırının etiketi BAZI bankalarda
    ("İş Bankası" tipi "sarkan etiket" kontaminasyonu, bkz. VERI-FORMATI.md
    §6.8) formül ekini ("(1+4+7+...)") kaybedip salt "Toplam" olarak geliyor,
    bazılarında (ör. Vakıf Katılım) araya bir sıra numarası karışıp "Toplam 25
    (1+4+...)" oluyor (ölçüldü, ING/TEB/Vakıf Katılım — 2026-2Ç). Eski `kalem_
    ham.startswith('Toplam (')` şartı bu varyantları kaçırıyor, payda (Toplam
    RAV) hiç bulunamıyor, m_toplam_risk_tabani yalnız Piyasa+Operasyonel'e
    düşüyor ve bu iki oranı 8-10x şişiriyor. Artık VERI-FORMATI §6.8'in tavsiye
    ettiği gibi alt dize/başlangıç eşleşmesi kullanılıyor — yalnız 'Toplam
    Özkaynak' ile karışmaması için o özel olarak dışlanıyor. Karşılaştırma
    BÜYÜK/KÜÇÜK HARFTEN bağımsız yapılıyor — Enpara ölçüldü, satırı tümüyle
    büyük harfle "TOPLAM (1+4+...)" basıyor."""
    for r in rows_in:
        kalem_ham = (r['kalem'] or '').strip()
        kalem_upper = kalem_ham.upper()
        degerler = r['degerler']
        # sermaye_ozet'in KENDİ "Toplam Risk Ağırlıklı Tutarlar" satırı (aynı
        # değeri taşıyan ayrı bir kaynak, ölçüldü: Akbank'ta ikisi de eşit)
        # bilerek dışlanıyor — aksi halde iki kaynak da eşleşip AYNI kaleme
        # iki kez yazılıyor ve LookupContext bunları TOPLUYOR (Akbank'ta RAV
        # tam 2 katına çıkıyordu, regresyon testinde yakalandı).
        if (kalem_upper == 'TOPLAM'
                or (kalem_upper.startswith('TOPLAM ')
                    and not kalem_upper.startswith('TOPLAM ÖZKAYNAK')
                    and not kalem_upper.startswith('TOPLAM RISK'))
                ) and len(degerler) >= 2:
            _emit(out, banka, cari_tarih, 'Dipnot', _TABLO_ADI['sermaye'],
                  'Kredi Riskine Esas Tutar: Toplam', 'Toplam', normalize_birim(degerler[0], birim))
            _emit(out, banka, onceki_tarih, 'Dipnot', _TABLO_ADI['sermaye'],
                  'Kredi Riskine Esas Tutar: Toplam', 'Toplam', normalize_birim(degerler[1], birim))
        elif kalem_ham.startswith('Toplam Özkaynak') and len(degerler) >= 2:
            _emit(out, banka, cari_tarih, 'Dipnot', _TABLO_ADI['ozkaynak_detay'],
                  'Toplam Ozkaynaklar', 'Toplam', normalize_birim(degerler[0], birim))
            _emit(out, banka, onceki_tarih, 'Dipnot', _TABLO_ADI['ozkaynak_detay'],
                  'Toplam Ozkaynaklar', 'Toplam', normalize_birim(degerler[1], birim))
        elif kalem_ham == 'Piyasa riski' and degerler:
            _emit(out, banka, cari_tarih, 'Dipnot', _TABLO_ADI['tcmb'],
                  'Sermaye Std. Oranı, Piyasa Riskine Esas Tutar (Pret)', 'Toplam',
                  normalize_birim(degerler[0], birim))
        elif 'Çekirdek Sermaye Yeterliliği Oranı' in kalem_ham and degerler:
            # ORAN (%) — para birimi tutarı DEĞİL, normalize_birim UYGULANMAZ.
            # NOT: 'Çekirdek' kontrolü ÖNCE gelmeli — aksi halde bu satır da
            # aşağıdaki genel 'Sermaye Yeterliliği Oranı' alt-dizesiyle eşleşirdi.
            _emit(out, banka, cari_tarih, 'Dipnot', _TABLO_ADI['sermaye_orani'],
                  'Çekirdek Sermaye Yeterliliği Oranı (%)', 'Toplam', degerler[0])
        elif ('Sermaye Yeterliliği Oranı' in kalem_ham and 'Ana Sermaye' not in kalem_ham
              and degerler):
            _emit(out, banka, cari_tarih, 'Dipnot', _TABLO_ADI['sermaye_orani'],
                  'Sermaye Yeterlilik Rasyosu (%)', 'Toplam', degerler[0])
        elif kalem_ham == 'Operasyonel risk' and degerler:
            _emit(out, banka, cari_tarih, 'Dipnot', _TABLO_ADI['tcmb'],
                  'Sermaye Std. Oranı, Operasyonel Riske Esas Tutar (Oret)', 'Toplam',
                  normalize_birim(degerler[0], birim))


_TK_KALEM_MAP = {
    'Toplam Tüketici Kredileri': 'Krediler ve K. Kartları (Tüketici ve Personel, Toplam)',
    'Bireysel Kredi Kartları-TP': 'Bireysel Kredi Kartları - TP, Toplam',
    'Bireysel Kredi Kartları-YP': 'Bireysel Kredi Kartları - YP, Toplam',
    'Personel Kredi Kartları-TP': 'Personel Kredi Kartları - TP, Toplam',
    'Personel Kredi Kartları-YP': 'Personel Kredi Kartları - YP, Toplam',
}


def _convert_tk_detay(rows_in: List[dict], banka: str, tarih: str, birim: str, out: List[dict]) -> None:
    """tk_detay: 3 kolon (KısaVadeli, OrtaUzunVadeli, Toplam) — yalnız son
    kolon (Toplam) kullanılır."""
    for r in rows_in:
        kalem_ham = (r['kalem'] or '').strip()
        degerler = r['degerler']
        toplam = degerler[-1] if degerler else None
        kalem = _TK_KALEM_MAP.get(kalem_ham)
        if kalem is not None:
            _emit(out, banka, tarih, 'Dipnot', _TABLO_ADI['tk_detay'], kalem, 'Toplam',
                  normalize_birim(toplam, birim))


_GRUP12_KOLONLAR = [
    'Standart Nitelikli Krediler ve Diğer Alacaklar',
    'Toplam, Yakın İzlemedeki, Krediler ve Diğer Alacaklar',
    'Toplam, Yakın İzlemedeki, Ödeme Planının Uzatılmasına Yönelik Değişiklik Yapılanlar',
    'Toplam, Yakın İzlemedeki, Diğer',
]


def _convert_grup12(rows_in: List[dict], banka: str, tarih: str, birim: str, out: List[dict]) -> None:
    """grup12: 'Toplam' satırının 4 kolonu -> Standart/YenidenYapılDışı/
    SözleşmeDeğişikliği/YenidenFinansman."""
    for r in rows_in:
        if (r['kalem'] or '').strip() != 'Toplam':
            continue
        degerler = r['degerler']
        for i, kalem in enumerate(_GRUP12_KOLONLAR):
            if i >= len(degerler):
                break
            _emit(out, banka, tarih, 'Dipnot', _TABLO_ADI['grup12'], kalem, 'Toplam',
                  normalize_birim(degerler[i], birim))


def _convert_faaliyet_gid(rows_in: List[dict], banka: str, cari_tarih: str,
                           onceki_tarih: str, birim: str, out: List[dict]) -> None:
    """faaliyet_gid_detay: 2 kolon (cari, önceki). Kalem metni birebir."""
    for r in rows_in:
        degerler = r['degerler']
        if len(degerler) < 2:
            continue
        kalem = (r['kalem'] or '').strip()
        _emit(out, banka, cari_tarih, 'Dipnot', _TABLO_ADI['faaliyet_gid_detay'], kalem, 'Toplam',
              normalize_birim(degerler[0], birim))
        _emit(out, banka, onceki_tarih, 'Dipnot', _TABLO_ADI['faaliyet_gid_detay'], kalem, 'Toplam',
              normalize_birim(degerler[1], birim))


_DONUK_SINIF = ['Sınırlı', 'Şüpheli', 'Zarar Niteliğinde']
_DONUK_HAREKET_MAP = {
    'Dönem İçinde İntikal': 'Dönem İçi İntikal',
    'Dönem İçinde Tahsilat': 'Dönem İçi Tahsilat',
    'Diğer Donuk Alacak Hesaplarından Giriş': 'Diğer Giriş',
    'Diğer Donuk Alacak Hesaplarına Çıkış': 'Diğer Çıkış',
}
# Rakip Analizi'nin ham verisinde (doğrulandı: Halkbank/Akbank/ING'in kendi
# parquet satırları) "çıkış" yönündeki hareketler (Tahsilat, Çıkış) HER ZAMAN
# negatif, "giriş" yönündekiler (İntikal, Giriş) HER ZAMAN pozitif — bu, BDR
# PDF'inin yazdığı işaretten bağımsız, stok-akış (açılış+giriş-çıkış=kapanış)
# muhasebe kuralı. BDR PDF'lerinin çoğu Tahsilat'ı da pozitif basıyor (yalnız
# "(-)" etiket, değer pozitif — kar_zarar'daki aynı desen) ama bazı bankalar
# (ölçüldü: Hayat Finans) parantezli/negatif basıyor. `-abs()`/`abs()` bu
# farkı elerken doğru işaretli bankaları bozmuyor (idempotent).
_DONUK_CIKIS_HAREKETLERI = {'Dönem İçi Tahsilat', 'Diğer Çıkış'}


def _convert_donuk_akim(rows_in: List[dict], banka: str, tarih: str, birim: str, out: List[dict]) -> None:
    """donuk_akim: 3 kolon (Sınırlı/Şüpheli/Zarar Niteliğinde). Kalem metninden
    hareket tipi ayıklanıp 'Donuk Alacaklar (<sınıf>, <hareket>)' kalıbına
    dönüştürülür — pipeline/measures.py'nin _NPL_INTIKAL_ITEMS/_NPL_TAHSILAT_ITEMS
    ile birebir eşleşecek şekilde.

    NOT: 'Dönem Sonu Bakiyesi' satırını Rakip'in BİLANÇO 'Donuk Alacaklar'
    kalemine sentezlemek DENENDİ (grup_1_krediler'i düzeltiyor gibi
    görünüyordu) ama _brut_krediler'i (brut_krediler_ta, npl_formasyonu vb.
    birçok ölçünün paydası) BOZDUĞU regresyon testinde yakalandı — production'da
    aynı kalem HER İKİ formülde de kullanılıyor ve tek bir sentetik değer
    ikisini birden tutarlı kılamadı. Bu yüzden BİLİNÇLİ OLARAK eklenmedi;
    grup_1_krediler/grup_1_krediler_toplam bu turda kapsam dışı kalıyor
    (bkz. pipeline/cikti_ingest.py modül docstring'i)."""
    for r in rows_in:
        kalem_ham = (r['kalem'] or '').strip()
        hareket = None
        for prefix, canonical in _DONUK_HAREKET_MAP.items():
            if kalem_ham.startswith(prefix):
                hareket = canonical
                break
        if hareket is None:
            continue
        degerler = r['degerler']
        cikis_yonu = hareket in _DONUK_CIKIS_HAREKETLERI
        for i, sinif in enumerate(_DONUK_SINIF):
            if i >= len(degerler):
                break
            kalem = f'Donuk Alacaklar ({sinif}, {hareket})'
            tutar = normalize_birim(degerler[i], birim)
            if tutar is not None:
                tutar = -abs(tutar) if cikis_yonu else abs(tutar)
            _emit(out, banka, tarih, 'Dipnot', _TABLO_ADI['donuk_akim'], kalem, 'Toplam', tutar)


def convert_dipnot(dipnot: List[dict], birim_map: Dict[str, str]) -> List[dict]:
    """Grup 2 (dipnot) -> long-format satırlar. Sadece doğrulanmış 7 tablo
    işlenir (bkz. modül docstring'i). `birim_map`: banka -> 'bin'/'milyon'
    (banka_ozetleri'nden — dipnot kayıtlarının kendi birim alanı yok, VERI-
    FORMATI §10 uyarınca kayitlar'la aynı birimi paylaşıyorlar)."""
    out: List[dict] = []
    by_key: Dict[tuple, List[dict]] = {}
    for r in dipnot:
        banka = normalize_bank_name(r['banka'])
        cari_tarih = donem_to_tarih(r['donem'])
        key = (banka, r['tablo'], r['blok'], cari_tarih)
        by_key.setdefault(key, []).append(r)

    seen_banka_donem = {(normalize_bank_name(r['banka']), donem_to_tarih(r['donem'])) for r in dipnot}

    for banka, cari_tarih in seen_banka_donem:
        onceki_tarih = fy_onceki_tarih(cari_tarih)
        birim = birim_map.get(banka, 'bin')

        cari_rows = by_key.get((banka, 'kalan_vade', 'cari', cari_tarih), [])
        onceki_rows = by_key.get((banka, 'kalan_vade', 'onceki', cari_tarih), [])
        _convert_kalan_vade(cari_rows, banka, cari_tarih, birim, out)
        _convert_kalan_vade(onceki_rows, banka, onceki_tarih, birim, out)

        for tablo in ('mvy', 'tfv'):
            for blok, tarih in (('cari', cari_tarih), ('onceki', onceki_tarih)):
                rows_in = by_key.get((banka, tablo, blok, cari_tarih), [])
                _convert_mvy_tfv(rows_in, banka, tarih, birim, out, tablo)

        sermaye_rows = (by_key.get((banka, 'sermaye_ozet', 'akim', cari_tarih), [])
                        + by_key.get((banka, 'risk_agirlikli', 'akim', cari_tarih), []))
        _convert_sermaye_risk(sermaye_rows, banka, cari_tarih, onceki_tarih, birim, out)

        for blok, tarih in (('cari', cari_tarih), ('onceki', onceki_tarih)):
            _convert_tk_detay(by_key.get((banka, 'tk_detay', blok, cari_tarih), []), banka, tarih, birim, out)

        _convert_grup12(by_key.get((banka, 'grup12', 'cari', cari_tarih), []), banka, cari_tarih, birim, out)

        _convert_faaliyet_gid(by_key.get((banka, 'faaliyet_gid_detay', 'akim', cari_tarih), []),
                               banka, cari_tarih, onceki_tarih, birim, out)

        _convert_donuk_akim(by_key.get((banka, 'donuk_akim', 'akim', cari_tarih), []), banka, cari_tarih, birim, out)

    return out


# --- Grup 3 (olgular) -------------------------------------------------------

def convert_olgular(olgular: List[dict]) -> List[dict]:
    """sube_yurtici(+yurtdisi) veya sube_toplam -> 'Şube Sayısı';
    personel_sayisi -> 'Personel Sayısı' (bkz. pipeline/measures.py
    m_sube_sayisi/m_personel_sayisi — tablo adı 'Şube-Personel')."""
    out: List[dict] = []
    by_banka_donem: Dict[tuple, Dict[str, float]] = {}
    for r in olgular:
        banka = normalize_bank_name(r['banka'])
        key = (banka, r['donem'])
        by_banka_donem.setdefault(key, {})[r['olgu']] = r['deger']

    for (banka, donem), olgu_map in by_banka_donem.items():
        cari_tarih = donem_to_tarih(donem)
        onceki_tarih = fy_onceki_tarih(cari_tarih)

        for tarih, suffix in ((cari_tarih, ''), (onceki_tarih, '_onceki')):
            if f'sube_toplam{suffix}' in olgu_map:
                sube = olgu_map[f'sube_toplam{suffix}']
            elif f'sube_yurtici{suffix}' in olgu_map:
                sube = olgu_map[f'sube_yurtici{suffix}'] + olgu_map.get(f'sube_yurtdisi{suffix}', 0)
            else:
                sube = None
            if sube is not None:
                _emit(out, banka, tarih, 'Dipnot', 'Şube-Personel', 'Şube Sayısı', 'Toplam', sube)
            if f'personel_sayisi{suffix}' in olgu_map:
                _emit(out, banka, tarih, 'Dipnot', 'Şube-Personel', 'Personel Sayısı', 'Toplam',
                      olgu_map[f'personel_sayisi{suffix}'])

    return out


# --- Ana giriş noktası -------------------------------------------------------

def cikti_to_dataframe(data: dict) -> pd.DataFrame:
    """`<DÖNEM>.json` içeriğini pipeline.lookup.LookupContext'in beklediği
    long-format DataFrame'e çevirir. `Banka Türü` kolonu `sablon` alanından
    türetilir (mevduat->Mevduat, katilim->Katılım)."""
    birim_map = {normalize_bank_name(o['banka']): o['birim'] for o in data.get('banka_ozetleri', [])}

    rows: List[dict] = []
    rows.extend(convert_kayitlar(data.get('kayitlar', [])))
    rows.extend(convert_dipnot(data.get('dipnot', []), birim_map))
    rows.extend(convert_olgular(data.get('olgular', [])))

    df = pd.DataFrame(rows, columns=['Banka Adı', 'Tarih', 'Tablo Türü', 'Tablo Adı',
                                      'Kalem Adı', 'Para Birimi', 'Tutar'])
    df['Tarih'] = pd.to_datetime(df['Tarih'])

    sablon_map = {normalize_bank_name(o['banka']): o['sablon'] for o in data.get('banka_ozetleri', [])}
    banka_turu_map = {b: ('Katılım' if s == 'katilim' else 'Mevduat') for b, s in sablon_map.items()}

    df['Banka Türü'] = df['Banka Adı'].map(banka_turu_map)
    return df, banka_turu_map


def bankalar_ve_donemler(data: dict) -> tuple:
    """Bu JSON'un kapsadığı banka listesi ve (cari) dönem tarihi — admin
    endpoint'inin compute_all'a `banks=`/`dates=` olarak geçmesi için."""
    bankalar = sorted({normalize_bank_name(o['banka']) for o in data.get('banka_ozetleri', [])})
    donem = data.get('donem')
    tarihler = [donem_to_tarih(donem)] if donem else []
    return bankalar, tarihler
