"""
assistant.tools
================
Modelin çağırabildiği araçlar (OpenAI "function calling" şeması) ve
yürütücüleri. Hepsi SADECE OKUR; hiçbir araç kayıt yapmaz. Özel ölçü
taslağı (propose_custom_measure) yalnız doğrulanıp önizlenir — kaydetme
kullanıcının arayüzdeki "Kaydet" tıklamasıyla, mevcut /api/my/measures
ucundan olur.

Her yürütücü (model_sonucu, istemci_olayı | None) döner: model_sonucu
modele JSON olarak geri verilir; istemci_olayı (taslak kartı, görünüm açma)
tarayıcıya SSE ile iletilir.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from pipeline import custom_measure_rules as R

from .external import tools as ext
from .knowledge import View, change_info, fold, format_value

MAX_ENTITIES = 12
MAX_DATES = 12
MAX_TOP = 30

_EXPR_DOC = (
    "İfade ağacı. Düğümler: {\"m\": \"<ölçü id>\"} ölçü, {\"k\": sayı} sabit, "
    "{\"op\": \"add|sub|mul|div\", \"l\": düğüm, \"r\": düğüm} işlem; oran (iki ölçü "
    "ifadesinin bölümü) düğümüne isteğe bağlı \"bicim\": \"pct\" (yüzde) | \"kat\" eklenebilir. "
    "Kurallar: toplama/çıkarmada iki taraf aynı birimde olmalı, gelir tablosu (akim) ile "
    "bilanço (stok) tutarı toplanamaz; çarpma yalnız bir sabitle; rasyo ile tutar oranlanamaz. "
    "Akım/stok oranında TTM ve ortalama bakiye otomatik uygulanır. Sadece katalog ölçüleri "
    "(özel ölçüler değil) kullanılabilir; en fazla 10 ölçü."
)

# Analiz paketleri (2026-10-03): analist yanıtı birçok ölçü gerektirir; model her ölçü için ayrı araç
# çağırınca tur sınırı doluyordu. Paket, ilgili ölçüleri tek çağrıda getirir (katalogda olmayan id atlanır).
ANALIZ_PAKETLERI: Dict[str, dict] = {
    'karlilik': {'ad': 'ROAE, ROAA, net kâr, RORWA', 'olculer': ['roae', 'roaa', 'net_donem_kari', 'rorwa']},
    'marj': {'ad': 'NIM, spread, getiri ve maliyet', 'olculer': [
        'nim', 'kredi_mevduat_spread', 'faiz_getirili_aktif_getirisi', 'faiz_maliyetli_pasif_maliyeti']},
    'aktif_kalitesi': {'ad': 'NPL, karşılama, risk maliyeti, 2. grup', 'olculer': [
        'npl_rasyosu', 'npl_karsilama_orani', 'cost_of_risk', 'grup_2_krediler_toplam', 'npl_formasyonu',
        'donuk_tahsilat_intikal', 'npl_3_asama_karsilama']},
    'verimlilik': {'ad': 'Maliyet/gelir, opex, ücret-komisyon', 'olculer': [
        'maliyet_gelir', 'faaliyet_gid_ort_aktif', 'opex_yoy_buyumesi', 'reel_opex_buyumesi', 'net_ucret_komisyonlar']},
    'fonlama': {'ad': 'Kredi/mevduat, vadesiz mevduat, alınan krediler', 'olculer': [
        'krediler_mevduat', 'vadesiz_mevduat_toplam_mevduat', 'alinan_krediler_iemk_toplam_kaynak',
        'tp_krediler_tp_kaynak']},
    'sermaye': {'ad': 'SYR, çekirdek SYR, RAV, RAV yoğunluğu, kaldıraç', 'olculer': [
        'syr', 'cekirdek_syr', 'rav', 'rav_yogunlugu', 'basit_kaldirac', 'basel_kaldirac_orani',
        'yp_net_pozisyon_ozkaynak']},
    'zorunlu_karsilik': {'ad': 'ZK sürüklemesi, TCMB hesabı, getiri ve marj', 'olculer': [
        'zk_surukleme', 'zk_faiz_gelirleri_orani', 'tcmb_hesabi_getirili_aktif', 'ortuk_tcmb_getirisi',
        'faiz_getirili_aktif_getirisi', 'zk_haric_getirili_aktif_getirisi', 'nim_getirili_aktif',
        'nim_swap_duzeltilmis']},
    'buyume': {'ad': 'Aktif, kredi, mevduat tutarları', 'olculer': ['toplam_aktifler', 'krediler', 'mevduat']},
}
MAX_PAKET_OLCU = 8


TOOL_SPECS: List[dict] = [
    {'type': 'function', 'function': {
        'name': 'search_measures',
        'description': 'Katalogdaki ölçüleri (ve kullanıcının özel ölçülerini) doğal dil sorgusuyla arar. '
                       'Bir ölçünün id\'sini bilmiyorsan HER ZAMAN önce bunu çağır.',
        'parameters': {'type': 'object', 'properties': {
            'query': {'type': 'string', 'description': 'Aranan kavram, ör. "takipteki krediler oranı"'},
            'limit': {'type': 'integer', 'description': 'En fazla sonuç (varsayılan 8, üst sınır 15)'},
        }, 'required': ['query']}}},
    {'type': 'function', 'function': {
        'name': 'get_measure_info',
        'description': 'Bir ölçünün tanımı, formülü, dönem yöntemi, kaynağı ve notları.',
        'parameters': {'type': 'object', 'properties': {
            'measure_id': {'type': 'string'},
        }, 'required': ['measure_id']}}},
    {'type': 'function', 'function': {
        'name': 'list_banks_and_groups',
        'description': 'Veri setindeki bankalar (tür, rakip), banka grupları ve üyeleri, mevcut dönemler.',
        'parameters': {'type': 'object', 'properties': {}}}},
    {'type': 'function', 'function': {
        'name': 'get_values',
        'description': 'Seçilen banka/grupların bir ya da BİRDEN ÇOK ölçüdeki değerleri (measure_ids ile tek '
                       'çağrıda en fazla 8 ölçü — analiz sorularında ölçüleri tek tek değil böyle topla). Birden '
                       'fazla dönem verilirse ilk ve son dönem arası değişim de hesaplanır (rasyoda bps, tutarda %).',
        'parameters': {'type': 'object', 'properties': {
            'measure_id': {'type': 'string'},
            'measure_ids': {'type': 'array', 'items': {'type': 'string'},
                            'description': "Birden çok ölçü id'si (measure_id yerine)"},
            'entities': {'type': 'array', 'items': {'type': 'string'},
                         'description': 'Banka ya da grup adları, ör. ["Kuveyt Türk", "Katılım Bankaları"]'},
            'dates': {'type': 'array', 'items': {'type': 'string'},
                      'description': 'YYYY-MM-DD, "2026Q2", "2025" (yıl sonu) ya da "son". Boşsa son dönem.'},
        }, 'required': ['entities']}}},
    {'type': 'function', 'function': {
        'name': 'get_analysis_pack',
        'description': 'Bir analiz başlığının TÜM temel ölçülerini tek çağrıda getirir (banka/grup × dönem). '
                       'Paketler: ' + ', '.join(f'{k} ({v["ad"]})' for k, v in ANALIZ_PAKETLERI.items()) + '. '
                       'Kâr, marj, aktif kalitesi, verimlilik, fonlama, sermaye gibi analiz sorularında ilk iş '
                       'bunu çağır; ölçüleri tek tek aramaktan çok daha hızlıdır. Birden çok paket verilebilir.',
        'parameters': {'type': 'object', 'properties': {
            'packs': {'type': 'array', 'items': {'type': 'string', 'enum': list(ANALIZ_PAKETLERI)}},
            'entities': {'type': 'array', 'items': {'type': 'string'},
                         'description': 'Banka ya da grup adları; boşsa odak banka + Katılım Bankaları + Rakip Bankalar'},
            'dates': {'type': 'array', 'items': {'type': 'string'},
                      'description': 'Boşsa son dönem, bir önceki çeyrek ve geçen yılın aynı dönemi'},
        }, 'required': ['packs']}}},
    {'type': 'function', 'function': {
        'name': 'rank_banks',
        'description': 'Bankaları bir ölçüde bir dönem için sıralar; tutar ölçülerinde evrendeki pay da verilir.',
        'parameters': {'type': 'object', 'properties': {
            'measure_id': {'type': 'string'},
            'date': {'type': 'string', 'description': 'Boşsa son dönem'},
            'universe': {'type': 'string',
                         'description': '"tumu", "katilim", "mevduat" ya da bir grup adı (ör. "Rakip Bankalar")'},
            'order': {'type': 'string', 'enum': ['desc', 'asc'], 'description': 'desc = en yüksek önce'},
            'top_n': {'type': 'integer'},
        }, 'required': ['measure_id']}}},
    {'type': 'function', 'function': {
        'name': 'propose_custom_measure',
        'description': 'Kullanıcının tarif ettiği yeni ölçünün TASLAĞINI doğrular ve önizler. KAYDETMEZ — '
                       'kullanıcı arayüzde çıkan kartta "Kaydet"e basar. ' + _EXPR_DOC,
        'parameters': {'type': 'object', 'properties': {
            'ad': {'type': 'string', 'description': 'Kısa, açıklayıcı ad (en fazla 60 karakter)'},
            'expr': {'type': 'object', 'description': 'İfade ağacı'},
            'sort_direction': {'type': 'string', 'enum': ['desc', 'asc'],
                               'description': 'desc = yüksek değer iyi'},
        }, 'required': ['ad', 'expr']}}},
    {'type': 'function', 'function': {
        'name': 'open_view',
        'description': 'Kullanıcının ekranında bir ölçüyü açar (Anında Görünüm ya da Trend).',
        'parameters': {'type': 'object', 'properties': {
            'measure_id': {'type': 'string'},
            'mode': {'type': 'string', 'enum': ['snapshot', 'trend']},
            'date': {'type': 'string'},
        }, 'required': ['measure_id']}}},
]

TOOL_LABELS = {
    'search_measures': 'Ölçüler aranıyor',
    'get_measure_info': 'Ölçü tanımı okunuyor',
    'list_banks_and_groups': 'Banka ve gruplar listeleniyor',
    'get_values': 'Değerler okunuyor',
    'get_analysis_pack': 'Analiz paketi hazırlanıyor',
    'rank_banks': 'Sıralama hesaplanıyor',
    'propose_custom_measure': 'Ölçü taslağı hazırlanıyor',
    'open_view': 'Görünüm açılıyor',
    **ext.LABELS,
}


_EVREN = {'tumu': 'tüm bankalar', 'katilim': 'katılım bankaları', 'mevduat': 'mevduat bankaları'}


def arac_ozeti(view, name: str, arguments: str) -> str:
    """Araç çağrısının kullanıcıya gösterilecek kısa özeti (2026-10-03): asistan panelinde
    "Hesaplıyorum…" satırına basınca hangi ölçü, banka ve dönemle çalışıldığı görünür.
    Ör. "Toplam Aktifler · Kuveyt Türk, Akbank · 2026-06-30"."""
    try:
        a = json.loads(arguments or '{}')
    except (TypeError, ValueError):
        return ''
    if not isinstance(a, dict):
        return ''
    parca: List[str] = []
    mids = ([a['measure_id']] if a.get('measure_id') else []) + [x for x in (a.get('measure_ids') or []) if isinstance(x, str)]
    adlar = []
    for mid in mids[:3]:
        m = view.meta(mid) if hasattr(view, 'meta') else None
        adlar.append((m or {}).get('ad') or str(mid))
    if adlar:
        parca.append(', '.join(adlar) + (' +%d' % (len(mids) - 3) if len(mids) > 3 else ''))
    if isinstance(a.get('packs'), list) and a['packs']:
        parca.append('paket: ' + ', '.join(map(str, a['packs'][:4])))
    if a.get('query'):
        parca.append('“%s”' % str(a['query'])[:60])
    if a.get('ad'):
        parca.append(str(a['ad'])[:60])
    ents = a.get('entities')
    if isinstance(ents, list) and ents:
        parca.append(', '.join(map(str, ents[:4])) + (' +%d' % (len(ents) - 4) if len(ents) > 4 else ''))
    if a.get('universe'):
        parca.append(_EVREN.get(str(a['universe']), str(a['universe'])))
    if a.get('top_n'):
        parca.append('ilk %s' % a['top_n'])
    tarih = a.get('dates') or a.get('date')
    if isinstance(tarih, list) and tarih:
        parca.append(tarih[0] if len(tarih) == 1 else '%s → %s' % (tarih[0], tarih[-1]))
    elif isinstance(tarih, str) and tarih:
        parca.append(tarih)
    if a.get('mode'):
        parca.append({'snapshot': 'Anında Görünüm', 'trend': 'Trend'}.get(a['mode'], str(a['mode'])))
    if not parca:   # dış kaynak araçları vb.: ilk iki basit değer
        parca = [str(v)[:40] for v in a.values() if isinstance(v, (str, int, float))][:2]
    return ' · '.join(parca)[:180]


def active_specs(dis_veri: bool = True) -> List[dict]:
    """Pano araçları + anahtarı tanımlı dış kaynakların (EVDS, TÜİK) araçları.
    dis_veri=False: kullanıcının rolünde dış veri izni yok (2026-09-30)."""
    return TOOL_SPECS + (ext.active_specs() if dis_veri else [])


def _focus(view) -> str:
    """Panonun odak bankası (admin panelinden seçilir; varsayılan Kuveyt Türk)."""
    return (getattr(view, 'odak', None) or (view.s.computed.get('meta', {}) or {}).get('focus_bank')
            or 'Kuveyt Türk')


def _err(msg: str, **extra) -> Tuple[dict, None]:
    return {'hata': msg, **extra}, None


def _measure(view: View, ref: Any) -> Tuple[Optional[str], Optional[dict]]:
    mid = view.resolve_measure(str(ref or ''))
    if not mid:
        oneriler = [m['id'] for m in view.search(str(ref or ''), 5)]
        return None, {'hata': f"'{ref}' bilinen bir ölçü değil. Önce search_measures ile id bulun.",
                      'benzer_idler': oneriler}
    return mid, None


def _dates(view: View, refs: Any) -> Tuple[List[str], List[str]]:
    refs = refs if isinstance(refs, list) and refs else ['son']
    ok, bad = [], []
    for r in refs[:MAX_DATES]:
        d = view.resolve_date(str(r))
        (ok if d else bad).append(d or str(r))
    return sorted(set(ok)), bad


# ------------------------------------------------------------------
# Yürütücüler
# ------------------------------------------------------------------

def t_search_measures(view: View, a: dict):
    limit = max(1, min(int(a.get('limit') or 8), 15))
    res = view.search(str(a.get('query') or ''), limit)
    return {'sonuclar': res, 'adet': len(res)}, None


def t_get_measure_info(view: View, a: dict):
    mid, e = _measure(view, a.get('measure_id'))
    if e:
        return e, None
    return view.info(mid), None


def t_list_banks_and_groups(view: View, a: dict):
    s = view.s
    rakipler = set(view.group_members.get('Rakip Bankalar') or [])   # güncel grup üyeliği (kişisel katman dahil)
    return {
        'bankalar': [{'ad': b['banka_adi'], 'tur': b.get('tur'), 'rakip': b['banka_adi'] in rakipler}
                     for b in s.banks],
        'gruplar': view.group_members,
        'donemler': {'ilk': s.dates[0] if s.dates else None, 'son': s.default_date,
                     'adet': len(s.dates), 'son_8': s.dates[-8:]},
        'not': 'Veri: BDDK çeyreklik solo finansal tablolar. Grup değerleri üyelerin toplamından '
               '(rasyolarda pay toplamı / payda toplamı) hesaplanır, basit ortalama değildir.',
    }, None


def _deger_blogu(view: View, mid: str, ents: List[str], dates: List[str]):
    meta = view.meta(mid)
    rows, unknown = [], []
    for name in ents[:MAX_ENTITIES]:
        r = view.resolve_entity(str(name))
        if not r:
            unknown.append(name)
            continue
        kind, canon = r
        vals = [{'donem': d, 'deger': (v := view.value(mid, kind, canon, d)),
                 'gosterim': format_value(v, meta)} for d in dates]
        row = {'ad': canon, 'tur': kind, 'degerler': vals}
        if len(dates) > 1:
            row['degisim_ilk_son'] = change_info(vals[0]['deger'], vals[-1]['deger'], meta)
        rows.append(row)
    out = {'olcu': {'id': mid, 'ad': meta['ad'], 'tip': meta.get('tip'), 'birim': meta.get('birim')},
           'sonuclar': rows}
    if unknown:
        out['bilinmeyen_varliklar'] = unknown
    return out


def t_get_values(view: View, a: dict):
    ids = [x for x in (a.get('measure_ids') or []) if isinstance(x, str)][:MAX_PAKET_OLCU]
    if a.get('measure_id'):
        ids.insert(0, a['measure_id'])
    if not ids:
        return _err('measure_id ya da measure_ids gerekli')
    dates, bad_dates = _dates(view, a.get('dates'))
    if not dates:
        return _err('Geçerli dönem yok', gecersiz_donemler=bad_dates, mevcut_son=view.s.default_date)
    ents = [str(x) for x in (a.get('entities') or [])]
    bloklar, hatalar = [], []
    for ref in ids:
        mid, e = _measure(view, ref)
        if e:
            hatalar.append({'olcu': ref, **e})
            continue
        bloklar.append(_deger_blogu(view, mid, ents, dates))
    if len(ids) == 1:   # eski tek ölçü biçimi
        if hatalar:
            return hatalar[0], None
        out = bloklar[0]
    else:
        out = {'olculer': bloklar}
        if hatalar:
            out['hatalar'] = hatalar
    if bad_dates:
        out['gecersiz_donemler'] = bad_dates
    return out, None


def _paket_donemleri(view: View, istenen) -> List[str]:
    if istenen:
        return _dates(view, istenen)[0]
    son = view.resolve_date('son')
    tum = view.s.dates
    if son not in tum:
        return [son] if son else []
    i = tum.index(son)
    secim = [tum[i]]
    if i >= 1:
        secim.insert(0, tum[i - 1])
    yoy = [d for d in tum if d[5:] == son[5:] and int(d[:4]) == int(son[:4]) - 1]
    if yoy and yoy[0] not in secim:
        secim.insert(0, yoy[0])
    return secim


def t_get_analysis_pack(view: View, a: dict):
    paketler = [p for p in (a.get('packs') or []) if p in ANALIZ_PAKETLERI]
    if not paketler:
        return _err('Geçerli paket yok', gecerli=list(ANALIZ_PAKETLERI))
    dates = _paket_donemleri(view, a.get('dates'))
    if not dates:
        return _err('Geçerli dönem yok', mevcut_son=view.s.default_date)
    odak = _focus(view)
    ents = [str(x) for x in (a.get('entities') or [])] or [odak, 'Katılım Bankaları', 'Rakip Bankalar']
    out = {'donemler': dates, 'varliklar': ents[:MAX_ENTITIES], 'paketler': {}}
    for p in paketler:
        bloklar, yok = [], []
        for mid in ANALIZ_PAKETLERI[p]['olculer']:
            if view.meta(mid) is None:
                yok.append(mid)
                continue
            bloklar.append(_deger_blogu(view, mid, ents, dates))
        out['paketler'][p] = {'ad': ANALIZ_PAKETLERI[p]['ad'], 'olculer': bloklar}
        if yok:
            out['paketler'][p]['katalogda_yok'] = yok
    return out, None


def t_rank_banks(view: View, a: dict):
    mid, e = _measure(view, a.get('measure_id'))
    if e:
        return e, None
    meta = view.meta(mid)
    date = view.resolve_date(a.get('date'))
    if not date:
        return _err(f"Geçersiz dönem: {a.get('date')}", mevcut_son=view.s.default_date)
    banks, label = view.bank_filter(a.get('universe'))
    if banks is None:
        return _err(f"Bilinmeyen evren: {a.get('universe')}",
                    gecerli=['tumu', 'katilim', 'mevduat'] + list(view.group_members))
    vals = [(b, view.value(mid, 'banka', b, date)) for b in banks]
    vals = [(b, v) for b, v in vals if v is not None]
    rev = (a.get('order') or 'desc') != 'asc'
    vals.sort(key=lambda x: x[1], reverse=rev)
    top = max(1, min(int(a.get('top_n') or 10), MAX_TOP))
    toplam = sum(v for _, v in vals) if meta.get('tip') == 'buyukluk' and meta.get('birim') == 'TL' else None
    rows = []
    odak = _focus(view)
    for i, (b, v) in enumerate(vals, 1):
        if i > top and b != odak:
            continue
        row = {'sira': i, 'banka': b, 'deger': v, 'gosterim': format_value(v, meta)}
        if toplam:
            row['pay'] = '%' + f'{v / toplam * 100:.2f}'.replace('.', ',')
        rows.append(row)
    return {'olcu': {'id': mid, 'ad': meta['ad'], 'birim': meta.get('birim')}, 'donem': date,
            'evren': label, 'veri_olan_banka': len(vals), 'siralama': rows,
            'not': f'{odak} ilk N dışında kalsa da listeye eklenir.' +
                   (' Pay, evrendeki bankaların toplamına göredir.' if toplam else '')}, None


def t_propose_custom_measure(view: View, a: dict):
    ad = ' '.join(str(a.get('ad') or '').split())
    expr = a.get('expr')
    if isinstance(expr, str):          # bazı modeller nesneyi metin olarak gönderir
        try:
            expr = json.loads(expr)
        except ValueError:
            return _err('expr geçerli bir JSON nesnesi değil')
    sort_direction = a.get('sort_direction') if a.get('sort_direction') in ('asc', 'desc') else 'desc'
    if not ad:
        return _err('Ölçü adı boş olamaz')
    if len(ad) > 60:
        return _err('Ölçü adı en fazla 60 karakter olabilir')
    plan, err = R.analyze(expr, view.cat)
    if err:
        return _err(err, ipucu='Kuralları düzeltip tekrar dene ya da kullanıcıya neden olmadığını açıkla.')
    key = fold(ad)
    if any(fold(m['ad']) == key for m in view.cat.values()):
        return _err('Bu ad hazır bir ölçüde kullanılıyor — o ölçü zaten mevcut olabilir; farklı bir ad seç.')
    if any(fold(c['meta']['ad']) == key for c in view.custom.values()):
        return _err('Kullanıcının bu adla bir özel ölçüsü zaten var; farklı bir ad seç.')
    t = plan['type']
    meta = {'tip': t['tip'], 'birim': t['birim']}
    dates = view.s.dates[-4:]
    odak = _focus(view)
    entities = [odak] + [g for g in view.group_order
                         if g != odak]
    preview = []
    for ent in entities:
        kind = 'banka' if ent == odak else 'grup'
        series = (lambda i, k=kind, n=ent: view._raw_series(i, k, n))
        vals = [R.evaluate(plan, series, d) for d in dates]
        preview.append({'ad': ent, 'degerler': [format_value(v, meta) for v in vals]})
    formul = R.formula_text(plan, view.cat)
    notlar = []
    stack = [plan]
    while stack:
        p = stack.pop()
        if p['kind'] == 'div' and not p.get('scale_only') and p['modes'][0]:
            notlar.append('Gelir tablosu kalemi son 12 aya (TTM), bilanço kalemi 12 aylık ortalamaya çevrildi.')
            break
        if 'l' in p:
            stack += [p['l'], p['r']]
    draft = {'ad': ad, 'expr': expr, 'sort_direction': sort_direction, 'formul': formul,
             'tip': t['tip'], 'birim': t['birim'], 'donemler': dates, 'onizleme': preview,
             'notlar': notlar}
    return {'durum': 'taslak_hazir', 'ad': ad, 'formul': formul, 'birim': t['birim'],
            'onizleme': preview, 'donemler': dates, 'notlar': notlar,
            'not': 'Taslak kullanıcıya kart olarak gösterildi; kaydetmek için kullanıcı "Kaydet"e basmalı. '
                   'Kaydedildiğini SÖYLEME.'}, {'type': 'draft', 'draft': draft}


def t_open_view(view: View, a: dict):
    mid, e = _measure(view, a.get('measure_id'))
    if e:
        return e, None
    mode = a.get('mode') if a.get('mode') in ('snapshot', 'trend') else 'snapshot'
    date = view.resolve_date(a.get('date')) if a.get('date') else None
    return ({'durum': 'acildi', 'olcu': view.meta(mid)['ad'], 'mod': mode, 'donem': date},
            {'type': 'action', 'action': 'open_view', 'measure_id': mid, 'mode': mode, 'date': date})


EXECUTORS = {
    'search_measures': t_search_measures,
    'get_measure_info': t_get_measure_info,
    'list_banks_and_groups': t_list_banks_and_groups,
    'get_values': t_get_values,
    'get_analysis_pack': t_get_analysis_pack,
    'rank_banks': t_rank_banks,
    'propose_custom_measure': t_propose_custom_measure,
    'open_view': t_open_view,
}


def execute(view: View, name: str, raw_args: str, dis_veri: bool = True) -> Tuple[dict, Optional[dict]]:
    fn = EXECUTORS.get(name)
    if fn is None and name in ext.EXECUTORS:
        if not dis_veri:
            return {'hata': 'Dış veri kaynakları bu kullanıcının rolünde kapalı'}, None
        try:
            args = json.loads(raw_args or '{}')
            if not isinstance(args, dict):
                raise ValueError
        except ValueError:
            return {'hata': 'Araç argümanları geçerli JSON değil'}, None
        try:
            return ext.execute(name, args)
        except Exception as e:  # dış servis sohbeti düşürmesin
            return {'hata': f'Araç çalışırken hata: {type(e).__name__}'}, None
    if fn is None:
        return {'hata': f"Bilinmeyen araç: {name}"}, None
    try:
        args = json.loads(raw_args or '{}')
        if not isinstance(args, dict):
            raise ValueError
    except ValueError:
        return {'hata': 'Araç argümanları geçerli JSON değil'}, None
    try:
        return fn(view, args)
    except Exception as e:  # araç hatası sohbeti düşürmesin; model düzeltebilir
        return {'hata': f'Araç çalışırken hata: {type(e).__name__}'}, None
