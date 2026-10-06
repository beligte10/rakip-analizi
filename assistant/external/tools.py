"""EVDS ve TÜİK araçları: şema (OpenAI function calling) + yürütücüler.

Araçlar yalnız ilgili anahtar sunucu ortamında tanımlıysa modele sunulur
(bkz. active_specs). Her sonuç bir "kaynak" alanı taşır — model veriyi
kaynağıyla birlikte göstermeli, pano (BDDK) verisiyle karıştırmamalı.
Satır sınırları istem boyutunu (ve maliyeti) küçük tutar.
"""
from __future__ import annotations

import calendar
import datetime
import re
from typing import Any, List, Optional, Tuple

from . import evds, evds_katalog, evds_rehber, tuik
from .http import ExternalError

EVDS_MAX_ROWS = 120
TUIK_DEFAULT_ROWS = 150
TUIK_MAX_ROWS = 300
MAX_DIM_VALUES = 60

EVDS_KAYNAK = 'TCMB EVDS (evds3.tcmb.gov.tr)'
TUIK_KAYNAK = 'TÜİK Veri Portalı SDMX servisi'

EVDS_SPECS: List[dict] = [
    {'type': 'function', 'function': {
        'name': 'evds_ara',
        'description': 'TCMB EVDS\'de SERİ ve veri grubu arar (faiz oranları, kurlar, kredi/mevduat hacimleri, '
                       'enflasyon, rezervler, ödemeler dengesi …). Türkçe ya da İngilizce kelimeler; hepsi '
                       'geçmeli. Sonuçta seri kodu, ad, frekans, birim, varsayılan toplulaştırma ve veri '
                       'aralığı gelir — evds_veri\'ye doğrudan bu kodları ver.',
        'parameters': {'type': 'object', 'properties': {
            'query': {'type': 'string', 'description': 'ör. "dolar kuru", "mevduat faizi", "tüfe", "TP.FG.J0"'},
        }, 'required': ['query']}}},
    {'type': 'function', 'function': {
        'name': 'evds_seriler',
        'description': 'Bir EVDS veri grubundaki serileri (kod, ad, frekans) listeler.',
        'parameters': {'type': 'object', 'properties': {
            'grup_kodu': {'type': 'string', 'description': 'evds_ara\'dan gelen kod, ör. "bie_kt100h"'},
        }, 'required': ['grup_kodu']}}},
    {'type': 'function', 'function': {
        'name': 'evds_veri',
        'description': 'EVDS serilerinin değerleri (en fazla 5 seri). Uzun aralıkta düşük frekans seç '
                       '(ör. aylik) — en fazla %d satır döner. Seri bilgisi (ad, birim, frekans) ve '
                       'uyarılar sonuçla birlikte gelir.' % EVDS_MAX_ROWS,
        'parameters': {'type': 'object', 'properties': {
            'seriler': {'type': 'array', 'items': {'type': 'string'}, 'description': 'ör. ["TP.DK.USD.A"]'},
            'baslangic': {'type': 'string', 'description': 'YYYY-MM-DD, YYYY-MM ya da YYYY'},
            'bitis': {'type': 'string', 'description': 'YYYY-MM-DD, YYYY-MM ya da YYYY; boşsa bugün'},
            'frekans': {'type': 'string', 'enum': list(evds.FREKANS),
                        'description': 'Yalnız serinin kendi frekansından daha SEYREK bir frekans seçilebilir'},
            'toplulastirma': {'type': 'string', 'enum': list(evds.TOPLULASTIRMA),
                              'description': 'Frekans düşürülürken; boşsa serinin varsayılanı. Stokta last/avg, '
                                             'akımda sum, oran/faizde avg'},
            'formul': {'type': 'string', 'enum': list(evds.FORMUL),
                       'description': 'Dönüşüm; boşsa düzey (ham değer). Yıllık enflasyon = TÜFE + '
                                      'yillik_yuzde_degisim; faizde puan farkı = fark'},
        }, 'required': ['seriler', 'baslangic']}}},
    {'type': 'function', 'function': {
        'name': 'evds_rehber',
        'description': 'EVDS kullanım rehberi (bilgi tabanı): seri kodu okuma, frekans, toplulaştırma, formüller, '
                       'veri türleri, yanıt okuma kuralları, hatalar. Emin olmadığın bir EVDS kavramında (hangi '
                       'toplulaştırma/formül, boş değer, frekans kısıtı) çağır.',
        'parameters': {'type': 'object', 'properties': {
            'konu': {'type': 'string', 'enum': list(evds_rehber.KONULAR),
                     'description': '; '.join(f'{k}: {a}' for k, (_, a) in evds_rehber.KONULAR.items())},
        }, 'required': ['konu']}}},
]

TUIK_SPECS: List[dict] = [
    {'type': 'function', 'function': {
        'name': 'tuik_ara',
        'description': 'TÜİK veri setlerini (dataflow) arar: enflasyon/TÜFE, GSYH, işgücü, nüfus, dış ticaret, '
                       'sanayi üretimi, konut … Adlar İngilizce; Türkçe yaygın terimler çevrilir. Tüm terimler '
                       'geçmeli.',
        'parameters': {'type': 'object', 'properties': {
            'query': {'type': 'string', 'description': 'ör. "tüfe", "consumer price", "işsizlik"'},
        }, 'required': ['query']}}},
    {'type': 'function', 'function': {
        'name': 'tuik_meta',
        'description': 'Bir TÜİK veri setinin filtrelenebilir boyutları ve değerleri. tuik_cek\'ten ÖNCE çağır; '
                       'filtreyi buradaki değer adlarıyla kur.',
        'parameters': {'type': 'object', 'properties': {
            'dataflow_id': {'type': 'string', 'description': 'ör. "DF_TUFE_SDMX_TT01"'},
        }, 'required': ['dataflow_id']}}},
    {'type': 'function', 'function': {
        'name': 'tuik_cek',
        'description': 'TÜİK veri setinden filtreli veri çeker. Filtresiz çekme: boyut_filtre ve dönem ver. '
                       'En fazla %d satır döner.' % TUIK_MAX_ROWS,
        'parameters': {'type': 'object', 'properties': {
            'dataflow_id': {'type': 'string'},
            'baslangic': {'type': 'string', 'description': 'ör. "2025-01", "2024-Q1", "2023"'},
            'bitis': {'type': 'string'},
            'boyut_filtre': {'type': 'object', 'description': '{boyut_id: [değer adı ya da kodu, …]}',
                             'additionalProperties': {'type': 'array', 'items': {'type': 'string'}}},
            'son_gozlem': {'type': 'integer', 'description': 'Her seride yalnız son N dönem'},
            'limit': {'type': 'integer', 'description': f'Satır sınırı (varsayılan {TUIK_DEFAULT_ROWS})'},
        }, 'required': ['dataflow_id']}}},
]

LABELS = {
    'evds_ara': 'EVDS\'de aranıyor', 'evds_seriler': 'EVDS serileri listeleniyor',
    'evds_veri': 'EVDS\'den veri alınıyor', 'evds_rehber': 'EVDS rehberi okunuyor', 'tuik_ara': 'TÜİK\'te aranıyor',
    'tuik_meta': 'TÜİK veri yapısı okunuyor', 'tuik_cek': 'TÜİK\'ten veri alınıyor',
}


def active_specs() -> List[dict]:
    return (EVDS_SPECS if evds.enabled() else []) + (TUIK_SPECS if tuik.enabled() else [])


def _err(msg: str, kaynak: str) -> Tuple[dict, None]:
    return {'hata': msg, 'kaynak': kaynak}, None


# --- EVDS ---
def _evds_date(s: Any, end: bool = False) -> Optional[str]:
    """YYYY-MM-DD | YYYY-MM | YYYY → GG-AA-YYYY (bitiş için dönem sonu)."""
    s = str(s or '').strip()
    m = re.fullmatch(r'(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?', s)
    if not m:
        return None
    y, mo, d = int(m.group(1)), m.group(2), m.group(3)
    if d:
        return f'{int(d):02d}-{int(mo):02d}-{y}'
    if mo:
        mo = int(mo)
        if not end:
            return f'01-{mo:02d}-{y}'
        return f'{calendar.monthrange(y, mo)[1]:02d}-{mo:02d}-{y}'
    return f'31-12-{y}' if end else f'01-01-{y}'


def _kat_grup_satiri(g: dict) -> dict:
    return {'kod': g['kod'], 'ad': g.get('ad'), 'frekans': g.get('frekans'), 'kaynak_kurum': g.get('kurum'),
            'birim': g.get('birim'), 'baslangic': g.get('baslangic'), 'bitis': g.get('bitis'),
            'kategori': g.get('kategori'), 'seri_sayisi': g.get('seri_sayisi')}


def t_evds_ara(view, a: dict):
    q = str(a.get('query') or '').strip()
    kat = evds_katalog.yukle()
    if kat:
        seriler = [kat.seri_bilgi(s) for s in kat.ara(q, 15)]
        gruplar = [_kat_grup_satiri(g) for g in kat.grup_ara(q, 6)]
        return {'kaynak': EVDS_KAYNAK, 'sorgu': q, 'seriler': seriler, 'veri_gruplari': gruplar,
                'not': None if (seriler or gruplar) else
                'Katalogda eşleşme yok; daha genel, tek kelimelik ya da İngilizce terim deneyin. '
                'Bulunamayan bir seri kodunu tahmin etme.'}, None
    rows = evds.search(q)
    return {'kaynak': EVDS_KAYNAK, 'sorgu': q, 'sonuclar': [
        {'kod': g['DATAGROUP_CODE'], 'ad': g.get('DATAGROUP_NAME'), 'frekans': g.get('FREQUENCY_STR'),
         'kaynak_kurum': g.get('DATASOURCE'), 'birim': g.get('BIRIMI'),
         'baslangic': g.get('START_DATE'), 'bitis': g.get('END_DATE')} for g in rows],
        'not': ('Seri kataloğu yüklü değil: yalnız veri grubu aranıyor (seri kodları için evds_seriler).'
                if rows else 'Eşleşme yok; daha genel ya da İngilizce kelime deneyin.')}, None


def t_evds_seriler(view, a: dict):
    code = str(a.get('grup_kodu') or '').strip()
    kat = evds_katalog.yukle()
    if kat and kat.grup_serileri(code):
        rows = kat.grup_serileri(code)
        g = kat.gruplar.get(code, {})
        out = [{'kod': s['kod'], 'ad': s['ad'], 'frekans': s['frekans'], 'varsayilan_toplulastirma': s['agg'],
                'baslangic': s['baslangic'], 'bitis': s['bitis']} for s in rows[:80]]
        return {'kaynak': EVDS_KAYNAK, 'grup': code, 'grup_adi': g.get('ad'), 'birim': g.get('birim') or None,
                'seri_sayisi': len(rows), 'seriler': out, 'kisaltildi': len(rows) > 80}, None
    rows = evds.series_list(code)
    out = [{'kod': s.get('SERIE_CODE'), 'ad': s.get('SERIE_NAME'), 'frekans': s.get('FREQUENCY_STR'),
            'varsayilan_toplulastirma': s.get('DEFAULT_AGG_METHOD'),
            'baslangic': s.get('START_DATE'), 'bitis': s.get('END_DATE')} for s in rows[:80]]
    return {'kaynak': EVDS_KAYNAK, 'grup': code, 'seri_sayisi': len(rows), 'seriler': out,
            'kisaltildi': len(rows) > 80}, None


# toplulaştırma adı → katalogdaki izin harfi (evds_katalog: a f l x n s)
_AGG_HARF = {'avg': 'a', 'first': 'f', 'last': 'l', 'max': 'x', 'min': 'n', 'sum': 's'}
_FORMUL_ACIKLAMA = {
    'duzey': 'düzey (ham değer)', 'yuzde_degisim': 'bir önceki gözleme göre % değişim',
    'fark': 'bir önceki gözleme göre fark', 'yillik_yuzde_degisim': 'geçen yılın aynı dönemine göre % değişim',
    'yillik_fark': 'geçen yılın aynı dönemine göre fark', 'yil_sonuna_gore_yuzde_degisim': 'önceki yıl sonuna göre % değişim (YTD)',
    'yil_sonuna_gore_fark': 'önceki yıl sonuna göre fark (YTD)', 'hareketli_ortalama': 'hareketli ortalama',
    'hareketli_toplam': 'hareketli toplam'}
_FREKANS_AD = {v: k for k, v in evds.FREKANS.items()}


def _veri_dogrula(kat, codes: List[str], freq: Optional[int], agg: Optional[str]):
    """Katalog biliniyorsa: (hata_mesajı | None, seri_bilgileri, katalogda_olmayanlar)."""
    bilgi, yok = [], []
    for c in codes:
        s = kat.seri(c)
        if not s:
            yok.append(c)
            continue
        bilgi.append(kat.seri_bilgi(s))
        orijinal = evds_katalog.frekans_kodu(s['frekans'])
        if freq and orijinal and freq < orijinal:
            return (f"{c} serisi '{s['frekans']}' yayımlanır; '{_FREKANS_AD.get(freq, freq)}' gibi daha sık bir "
                    f"frekansa çevrilemez. Serinin kendi frekansını ya da daha seyrek bir frekansı seçin."), bilgi, yok
        if freq and agg and s['izinli_agg'] and _AGG_HARF.get(agg) not in s['izinli_agg']:
            izin = [k for k, h in _AGG_HARF.items() if h in s['izinli_agg']]
            return (f"{c} serisi için '{agg}' toplulaştırması desteklenmiyor (stok/oran serilerinde 'sum' "
                    f"anlamsızdır). Desteklenenler: {', '.join(izin)}; serinin varsayılanı: {s['agg'] or '-'}."), bilgi, yok
    return None, bilgi, yok


def t_evds_veri(view, a: dict):
    seriler = a.get('seriler') or []
    if isinstance(seriler, str):
        seriler = [seriler]
    start = _evds_date(a.get('baslangic'))
    if not start:
        return _err('baslangic YYYY-MM-DD, YYYY-MM ya da YYYY olmalı', EVDS_KAYNAK)
    if a.get('bitis'):
        end = _evds_date(a.get('bitis'), end=True)
        if not end:
            return _err('bitis YYYY-MM-DD, YYYY-MM ya da YYYY olmalı', EVDS_KAYNAK)
    else:
        end = datetime.date.today().strftime('%d-%m-%Y')
    freq = evds.FREKANS.get(a.get('frekans')) if a.get('frekans') else None
    agg = a.get('toplulastirma') if a.get('toplulastirma') in evds.TOPLULASTIRMA else None
    formula = evds.FORMUL.get(a.get('formul')) if a.get('formul') else None
    codes = [str(s).strip().upper() for s in seriler]
    kat = evds_katalog.yukle()
    bilgi, yok = [], []
    if kat:
        hata, bilgi, yok = _veri_dogrula(kat, codes, freq, agg)
        if hata:
            return _err(hata, EVDS_KAYNAK)
    try:
        items = evds.fetch(codes, start, end, freq, agg if freq else None, formula)
    except ExternalError as e:
        if yok and getattr(e, 'status', None) == 400:
            return _err('Geçersiz seri kodu: ' + ', '.join(yok) + ' katalogda yok; evds_ara ile doğru kodu bulun '
                        '(kod tahmin etmeyin).', EVDS_KAYNAK)
        raise
    rows = evds.clean_rows(items, codes)
    truncated = len(rows) > EVDS_MAX_ROWS
    notlar = []
    if truncated:
        notlar.append('Satır sınırı aşıldı: en yeni %d satır gösteriliyor. Daha düşük frekans seçin.' % EVDS_MAX_ROWS)
    if yok:
        notlar.append('Katalogda bulunamayan seri kodu: ' + ', '.join(yok) + ' — adı/birimi doğrulanamadı, tahmin etme.')
    if rows and all(all(v is None for k, v in r.items() if k != 'tarih') for r in rows):
        notlar.append('Tüm değerler boş (null): seçilen aralıkta veri yok ya da formülün ilk gözlemleri; '
                      'aralığı genişletin / serinin başlangıç tarihine bakın. Boş değer sıfır değildir.')
    arsiv = [b['kod'] for b in bilgi if b.get('uyari')]
    if arsiv:
        notlar.append('Arşiv serisi: ' + ', '.join(arsiv) + ' — baz yılı eski olabilir; güncel seriyi evds_ara ile kontrol edin.')
    notlar.append('Son dönem geçici olabilir; TCMB sonradan revize edebilir. Boş (null) değer = veri yok, sıfır değil.')
    return {'kaynak': EVDS_KAYNAK, 'seriler': codes, 'seri_bilgi': bilgi or None, 'donem': [start, end],
            'frekans': a.get('frekans') or 'serinin kendi frekansı', 'toplulastirma': agg if freq else None,
            'formul': a.get('formul') or 'duzey',
            'donusum': _FORMUL_ACIKLAMA.get(a.get('formul') or 'duzey'),
            'satir_sayisi': len(rows), 'kisaltildi': truncated, 'notlar': notlar,
            'satirlar': rows[-EVDS_MAX_ROWS:]}, None


def t_evds_rehber(view, a: dict):
    konu = str(a.get('konu') or '').strip().lower()
    metin = evds_rehber.getir(konu)
    if metin is None:
        return {'kaynak': 'EVDS bilgi tabanı', 'hata': 'Bilinmeyen konu', 'konular': evds_rehber.konu_listesi()}, None
    return {'kaynak': 'EVDS bilgi tabanı (TCMB EVDS dokümantasyonundan derlenmiştir)', 'konu': konu,
            'icerik': metin}, None


# --- TÜİK ---
def t_tuik_ara(view, a: dict):
    q = str(a.get('query') or '').strip()
    rows = tuik.search_dataflows(tuik.dataflows(), q)
    return {'kaynak': TUIK_KAYNAK, 'sorgu': q, 'eslesme_sayisi': len(rows), 'sonuclar': [
        {'id': d['id'], 'ad': d.get('name'), 'aciklama': (d.get('description') or '')[:200],
         'surum': d.get('version')} for d in rows[:15]],
        'not': None if rows else 'Eşleşme yok; İngilizce terim deneyin (ör. "consumer price").'}, None


def t_tuik_meta(view, a: dict):
    df_id = str(a.get('dataflow_id') or '').strip()
    version = tuik.resolve_version(tuik.dataflows(), df_id, '')
    dims = tuik.dimensions(df_id, version)
    filtrelenebilir = []
    for d in dims:
        if d['single_value']:
            continue
        vals = d['values']
        filtrelenebilir.append({'id': d['id'], 'ad': d['name'], 'tur': d['type'], 'deger_sayisi': d['value_count'],
                                'degerler': [v['name'] for v in vals[:MAX_DIM_VALUES]],
                                'kisaltildi': len(vals) > MAX_DIM_VALUES})
    sabit = {d['id']: d['values'][0]['name'] for d in dims if d['single_value'] and d['values']}
    return {'kaynak': TUIK_KAYNAK, 'dataflow_id': df_id, 'surum': version,
            'filtrelenebilir_boyutlar': filtrelenebilir, 'sabit_boyutlar': sabit,
            'not': 'Dönem (TIME_PERIOD) boyut_filtre ile değil baslangic/bitis ile süzülür.'}, None


def t_tuik_cek(view, a: dict):
    df_id = str(a.get('dataflow_id') or '').strip()
    baslangic, bitis = str(a.get('baslangic') or ''), str(a.get('bitis') or '')
    son_gozlem = int(a.get('son_gozlem') or 0)
    limit = max(1, min(int(a.get('limit') or TUIK_DEFAULT_ROWS), TUIK_MAX_ROWS))
    tuik.validate_fetch_params(son_gozlem, limit, baslangic, bitis)
    version = tuik.resolve_version(tuik.dataflows(), df_id, '')
    filtre = a.get('boyut_filtre') or None
    if filtre is not None:
        if not isinstance(filtre, dict):
            return _err('boyut_filtre {boyut_id: [değerler]} biçiminde olmalı', TUIK_KAYNAK)
        filtre = {str(k): [str(x) for x in (v if isinstance(v, list) else [v])] for k, v in filtre.items()}
    key, client_filtre = '', None
    if filtre:
        dims = tuik.dimensions(df_id, version)
        key = tuik.build_sdmx_key(dims, filtre)
        if len(key) > tuik.MAX_KEY_LEN:
            client_filtre = tuik.filtre_to_names(dims, filtre)
            key = ''
    elif not (baslangic or son_gozlem):
        return _err('Filtresiz çekim çok büyük olabilir: önce tuik_meta ile boyut_filtre kurun ya da '
                    'baslangic/son_gozlem verin.', TUIK_KAYNAK)
    # TÜİK'in lastNObservations parametresi sunucuda takılıyor (2026-09-30'da
    # 150 sn'de yanıt yok; dönem filtresi <1 sn). Son N dönem bizde: yeterince
    # geniş bir başlangıçla çekip her serinin son N gözlemi tutulur.
    if son_gozlem and not baslangic:
        baslangic = str(datetime.date.today().year - min(son_gozlem, 30) - 1)
    raw = tuik.fetch(df_id, version, key, baslangic, bitis)
    if raw is None:
        return {'kaynak': TUIK_KAYNAK, 'dataflow_id': df_id, 'satir_sayisi': 0, 'satirlar': [],
                'not': 'Seçilen filtre/dönem için veri yok; dönemi genişletin ya da filtreyi gevşetin.'}, None
    rows = tuik.parse_sdmx_data(raw, keep_dimensions=set(client_filtre or {}))
    if client_filtre:
        rows = tuik.filter_rows(rows, client_filtre)
    if son_gozlem:
        rows = _son_gozlem(rows, son_gozlem)
    rows, truncated, total = tuik.limit_rows(rows, limit)
    return {'kaynak': TUIK_KAYNAK, 'dataflow_id': df_id, 'surum': version, 'satir_sayisi': len(rows),
            'toplam_satir': total, 'kisaltildi': truncated,
            'not': 'Satır sınırı aşıldı; filtreyi daraltın.' if truncated else None, 'satirlar': rows}, None


def _son_gozlem(rows: List[dict], n: int) -> List[dict]:
    """Her seride (TIME_PERIOD ve DEGER dışındaki boyutların birleşimi) son n dönem."""
    series: dict = {}
    for r in rows:
        k = tuple(sorted((a, str(b)) for a, b in r.items() if a not in ('TIME_PERIOD', 'DEGER')))
        series.setdefault(k, []).append(r)
    out: List[dict] = []
    for lst in series.values():
        out.extend(sorted(lst, key=lambda r: str(r.get('TIME_PERIOD', '')))[-n:])
    return out


EXECUTORS = {
    'evds_ara': t_evds_ara, 'evds_seriler': t_evds_seriler, 'evds_veri': t_evds_veri, 'evds_rehber': t_evds_rehber,
    'tuik_ara': t_tuik_ara, 'tuik_meta': t_tuik_meta, 'tuik_cek': t_tuik_cek,
}
KAYNAK = {k: (EVDS_KAYNAK if k.startswith('evds') else TUIK_KAYNAK) for k in EXECUTORS}


def execute(name: str, args: dict) -> Tuple[dict, None]:
    """Dış araç çağrısı; servis/doğrulama hataları modele açıklanır (anahtar içermez)."""
    enabled = evds.enabled() if name.startswith('evds') else tuik.enabled()
    if not enabled:
        return _err('Bu veri kaynağı sunucuda etkin değil (API anahtarı tanımlı değil).', KAYNAK[name])
    try:
        return EXECUTORS[name](None, args)
    except ExternalError as e:
        return _err(str(e), KAYNAK[name])
    except ValueError as e:     # tuik doğrulama hataları (geçersiz boyut/değer/dönem) açıklayıcı
        return _err(str(e)[:600], KAYNAK[name])
