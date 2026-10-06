"""
assistant.rakip_oneri
=====================
Odak banka için rakip banka önerisi (2026-10-03).

Odak banka değişince "Rakip Bankalar" grubu da o bankaya göre kurulmalı: Kuveyt
Türk'ün rakipleri (büyük özel mevduat bankaları) ile ör. Albaraka'nınkiler
aynı değildir. Öneri iki katmanlı:

1. Benzerlik skoru (deterministik, veriden): son dönemde aktif büyüklüğü
   yakınlığı, aynı segment (katılım / mevduat) ve iş modeli benzerliği (kredi,
   bireysel/tüzel ağırlık, menkul kıymet, vadesiz mevduat payları).
2. Yapay zeka: kıdemli banka stratejisti rolündeki model bu tabloya bakıp
   kıyas setini seçer ve her banka için kısa gerekçe yazar. Model yalnız
   listedeki bankalardan seçebilir; yanıt doğrulanır.

Model yoksa ya da yanıtı geçersizse skorun ilk N bankası, veriden üretilmiş
gerekçeyle önerilir (kaynak: 'benzerlik').
"""
from __future__ import annotations

import json
import math
import re
import threading
from typing import Dict, List, Optional, Tuple

from . import llm

VARSAYILAN_SAYI = 5
EN_AZ, EN_COK = 3, 8

# İş modeli benzerliğinde kullanılan ölçüler (pay/oran, %)
MODEL_OLCULERI = [
    ('krediler_ta', 'Krediler / Aktif'),
    ('tuketici_toplam', 'Tüketici / Krediler'),
    ('tuzel_toplam', 'Tüzel / Krediler'),
    ('menkul_kiymetler_ta', 'Menkul Kıymet / Aktif'),
    ('vadesiz_mevduat_toplam_mevduat', 'Vadesiz / Mevduat'),
]
# Modele bağlam için gösterilen ek göstergeler
EK_OLCULER = [('roae', 'ROAE'), ('nim', 'NIM'), ('npl_rasyosu', 'NPL'), ('sube_sayisi', 'Şube')]

# Kamu sermayeli bankalar. Model sahipliği tahmin etmesin diye tabloya kesin bilgi olarak verilir
# (2026-10-03 denemesinde İş Bankası'nı "kamu bankası" diye yazdı).
KAMU_BANKALARI = frozenset({'Ziraat Bankası', 'Halk Bank', 'Vakıfbank', 'Ziraat Katılım', 'Vakıf Katılım',
                            'Emlak Katılım'})

_onbellek: Dict[tuple, dict] = {}
_kilit = threading.Lock()


def _deger(bank_data: dict, mid: str, banka: str, tarih: str) -> Optional[float]:
    v = ((bank_data.get(mid) or {}).get(banka) or {}).get(tarih)
    return v if isinstance(v, (int, float)) and math.isfinite(v) else None


def _son_tarih(bank_data: dict, banka: str) -> Optional[str]:
    ta = (bank_data.get('toplam_aktifler') or {}).get(banka) or {}
    tarihler = sorted(t for t, v in ta.items() if v)
    return tarihler[-1] if tarihler else None


def benzerlik_tablosu(computed: dict, catalog: dict, odak: str) -> Tuple[Optional[str], List[dict]]:
    """Odak bankanın son dönemine göre diğer bankaların benzerlik skoru (0-100), yüksekten düşüğe."""
    bd = computed.get('bank_data') or {}
    tarih = _son_tarih(bd, odak)
    if not tarih:
        return None, []
    bankalar = [b for b in catalog.get('banks', []) if b.get('tur') != 'Grup']
    tur = {b['banka_adi']: b.get('tur') for b in bankalar}
    dijital = {b['banka_adi']: bool(b.get('dijital_only')) for b in bankalar}
    profil = {}
    for b in bankalar:
        ad = b['banka_adi']
        ta = _deger(bd, 'toplam_aktifler', ad, tarih)
        if not ta:
            continue
        profil[ad] = {'ta': ta, **{m: _deger(bd, m, ad, tarih) for m, _ in MODEL_OLCULERI + EK_OLCULER}}
    if odak not in profil:
        return tarih, []
    toplam_ta = sum(p['ta'] for p in profil.values())

    # Model ölçülerinde bankalar arası yayılım (standartlaştırma için)
    yayilim = {}
    for m, _ in MODEL_OLCULERI:
        xs = [p[m] for p in profil.values() if p[m] is not None]
        if len(xs) > 2:
            ort = sum(xs) / len(xs)
            yayilim[m] = math.sqrt(sum((x - ort) ** 2 for x in xs) / len(xs)) or 1.0
    f = profil[odak]
    satirlar = []
    for ad, p in profil.items():
        if ad == odak:
            continue
        boyut = math.exp(-abs(math.log(p['ta'] / f['ta'])))
        farklar = [((p[m] - f[m]) / yayilim[m]) ** 2 for m in yayilim if p[m] is not None and f[m] is not None]
        model = math.exp(-math.sqrt(sum(farklar) / len(farklar))) if farklar else 0.5
        ayni_segment = tur.get(ad) == tur.get(odak)
        skor = 100 * (0.45 * boyut + 0.35 * model + 0.20 * (1.0 if ayni_segment else 0.0))
        satirlar.append({
            'banka': ad, 'tur': tur.get(ad), 'dijital': dijital.get(ad, False), 'kamu': ad in KAMU_BANKALARI,
            'skor': round(skor, 1), 'aktif_pay': round(100 * p['ta'] / toplam_ta, 2),
            'buyukluk_orani': round(p['ta'] / f['ta'], 2), 'ayni_segment': ayni_segment,
            'gostergeler': {m: (None if p[m] is None else round(p[m], 2)) for m, _ in MODEL_OLCULERI + EK_OLCULER},
        })
    satirlar.sort(key=lambda r: -r['skor'])
    return tarih, satirlar


def _veri_gerekcesi(r: dict, dil: str = 'tr') -> str:
    oran = r['buyukluk_orani']
    if dil == 'en':
        boyut = ('similar size' if 0.67 <= oran <= 1.5
                 else f'{oran:.1f}x larger' if oran > 1 else f'{100 * oran:.0f}% of the focus bank\'s assets')
        seg = ('same segment' if r['ayni_segment']
               else ('participation bank' if r['tur'] == 'Katılım' else 'deposit bank'))
        return f'{seg}, {boyut} (asset share {r["aktif_pay"]:.1f}%); similarity score {r["skor"]:.0f}'
    boyut = ('benzer büyüklükte' if 0.67 <= oran <= 1.5
             else f'{oran:.1f} kat büyük' if oran > 1 else f'aktifi odak bankanın %{100 * oran:.0f}\'i')
    seg = 'aynı segment' if r['ayni_segment'] else ('katılım bankası' if r['tur'] == 'Katılım' else 'mevduat bankası')
    return f'{seg}, {boyut} (aktif payı %{r["aktif_pay"]:.1f}); benzerlik skoru {r["skor"]:.0f}'


def _model_istegi(odak: str, odak_tur: str, tarih: str, satirlar: List[dict], n: int,
                  odak_profil: str = '-', dil: str = 'tr') -> List[dict]:
    basliklar = ['Banka', 'Tür', 'Sahiplik', 'Skor', 'Aktif payı %', 'Büyüklük (odak=1)'] + [ad for _, ad in MODEL_OLCULERI + EK_OLCULER]

    def hucre(v):
        return '-' if v is None else (f'{v:g}' if isinstance(v, (int, float)) else str(v))
    tablo = ['| ' + ' | '.join(basliklar) + ' |', '|' + '---|' * len(basliklar)]
    for r in satirlar:
        tablo.append('| ' + ' | '.join([r['banka'] + (' (dijital)' if r['dijital'] else ''), r['tur'] or '-',
                                        'kamu' if r['kamu'] else 'özel', hucre(r['skor']), hucre(r['aktif_pay']), hucre(r['buyukluk_orani'])]
                                       + [hucre(r['gostergeler'][m]) for m, _ in MODEL_OLCULERI + EK_OLCULER]) + ' |')
    sistem = ('Sen Türkiye bankacılık sektörünü iyi bilen kıdemli bir banka stratejistisin. Görevin, bir bankanın '
              'yönetimine sunulacak rekabet analizinde kullanılacak RAKİP (kıyas) bankalar setini seçmek. '
              'Yalnız verilen tablodaki bankalardan seç; tablo dışı banka adı yazma. Yanıtın YALNIZ geçerli JSON olsun.')
    kullanici = (
        f'Odak banka: {odak} ({odak_tur} bankası, {"kamu" if odak in KAMU_BANKALARI else "özel"} sermayeli). Dönem: {tarih}. Odak bankanın göstergeleri: {odak_profil}.\n'
        'Aday bankalar (skor: veriden benzerlik, 0-100; büyüklük ölçeği, aynı segment ve iş modeli karması):\n'
        + '\n'.join(tablo) + '\n\n'
        f'{n} rakip seç (gerekirse {EN_AZ}-{EN_COK} arası). İlkeler:\n'
        '- Odak bankanın müşteri ve fon için doğrudan rekabet ettiği bankalar: benzer ölçek ve benzer iş modeli.\n'
        '- Katılım bankası odaksa en az 1-2 katılım bankası olsun; ama katılım bankaları küçükse ölçek olarak '
        'kıyaslanan mevduat bankaları da eklenebilir (ör. büyük bir katılım bankası büyük özel bankalarla kıyaslanır).\n'
        '- Kamu bankaları (Sahiplik sütunu "kamu") farklı fonlama ve politika rolüne sahiptir; odak kamu bankası '
        'değilse yalnız gerçekten doğrudan rakipse seç. Sahipliği YALNIZ Sahiplik sütunundan al.\n'
        '- Çok küçük, yeni ya da yalnız dijital bankaları odak banka da öyle değilse seçme.\n'
        '- Skor yol göstericidir, mekanik uygulama; sektör bilgini kullan.\n'
        'Her banka için en fazla 18 kelimelik Türkçe gerekçe yaz: tablodan en az bir sayı ver (ör. büyüklük oranı, '
        'aktif payı ya da bir gösterge) ve tabloda olmayan nitelik (dijital dönüşüm, sermaye kökeni, strateji …) yazma; '
        'sahiplik (kamu/özel) yalnız Sahiplik sütununa göre yazılabilir.\n'
        'Gerekçeler yalnız Türkçe kelimelerle yazılsın (başka dil/alfabe karışmasın).\n'
        'Biçim: {"rakipler": [{"banka": "...", "gerekce": "..."}]}'
        + ('\nGerekçeleri İNGİLİZCE yaz (banka adları tablodaki gibi kalsın).' if dil == 'en' else ''))
    return [{'role': 'system', 'content': sistem}, {'role': 'user', 'content': kullanici}]


def _odak_profili(computed: dict, odak: str, tarih: str) -> str:
    bd = computed.get('bank_data') or {}
    parca = []
    for m, ad in MODEL_OLCULERI + EK_OLCULER:
        v = _deger(bd, m, odak, tarih)
        if v is not None:
            parca.append(f'{ad} {v:.2f}'.rstrip('0').rstrip('.'))
    return ', '.join(parca) or '-'


def _json_ayikla(metin: str) -> Optional[dict]:
    metin = re.sub(r'```(?:json)?', '', metin or '')
    bas, son = metin.find('{'), metin.rfind('}')
    if bas < 0 or son <= bas:
        return None
    try:
        return json.loads(metin[bas:son + 1])
    except ValueError:
        return None


def _modelden(cfg: llm.LLMConfig, mesajlar: List[dict], gecerli: set) -> Optional[List[dict]]:
    parcalar = []
    for tur, yuk in llm.stream_chat(cfg, mesajlar, None, temperature=0.1):
        if tur == 'content':
            parcalar.append(yuk)
    js = _json_ayikla(''.join(parcalar))
    liste = (js or {}).get('rakipler') if isinstance(js, dict) else None
    if not isinstance(liste, list):
        return None
    out, gorulen = [], set()
    for x in liste:
        if not isinstance(x, dict):
            continue
        ad = str(x.get('banka') or '').replace(' (dijital)', '').strip()
        if ad in gecerli and ad not in gorulen:
            gorulen.add(ad)
            gerekce = re.sub(r'\s{2,}', ' ', llm.cjk_temizle(str(x.get('gerekce') or ''))).strip()
            out.append({'banka': ad, 'gerekce': gerekce[:160]})
    return out[:EN_COK] if len(out) >= EN_AZ else None


def rakip_oner(computed: dict, catalog: dict, odak: str, cfg: Optional[llm.LLMConfig] = None,
               n: int = VARSAYILAN_SAYI, anahtar: object = None, dil: str = 'tr') -> dict:
    """{'odak', 'tarih', 'kaynak': 'yapay_zeka'|'benzerlik', 'oneriler': [{banka, gerekce, skor}],
    'adaylar': [{banka, skor, tur}]}. `anahtar` (ör. veri sürümü) verilirse sonuç önbelleklenir."""
    n = max(EN_AZ, min(EN_COK, int(n or VARSAYILAN_SAYI)))
    dil = 'en' if dil == 'en' else 'tr'
    ob_anahtar = (odak, n, anahtar, bool(cfg), dil) if anahtar is not None else None
    if ob_anahtar is not None:
        with _kilit:
            if ob_anahtar in _onbellek:
                return _onbellek[ob_anahtar]
    tarih, satirlar = benzerlik_tablosu(computed, catalog, odak)
    skor = {r['banka']: r for r in satirlar}
    odak_tur = next((b.get('tur') for b in catalog.get('banks', []) if b.get('banka_adi') == odak), '') or ''
    oneriler, kaynak, uyari = None, 'benzerlik', None
    if cfg is not None and satirlar:
        try:
            oneriler = _modelden(cfg, _model_istegi(odak, odak_tur, tarih, satirlar, n, _odak_profili(computed, odak, tarih), dil), set(skor))
            if oneriler:
                kaynak = 'yapay_zeka'
            else:
                uyari = 'Yapay zeka geçerli bir liste döndürmedi; veriye dayalı benzerlik önerisi gösteriliyor.'
        except llm.LLMError:
            uyari = 'Yapay zeka servisine ulaşılamadı; veriye dayalı benzerlik önerisi gösteriliyor.'
    if not oneriler:
        # Yalnız dijital bankalar, odak banka da dijital değilse yedek öneriye alınmaz
        odak_dijital = any(b.get('banka_adi') == odak and b.get('dijital_only') for b in catalog.get('banks', []))
        oneriler = [{'banka': r['banka'], 'gerekce': _veri_gerekcesi(r, dil)}
                    for r in satirlar if odak_dijital or not r['dijital']][:n]
    for o in oneriler:
        o['skor'] = skor.get(o['banka'], {}).get('skor')
        if not o.get('gerekce'):
            o['gerekce'] = _veri_gerekcesi(skor[o['banka']], dil)
    sonuc = {'odak': odak, 'tarih': tarih, 'kaynak': kaynak, 'oneriler': oneriler,
             'adaylar': [{'banka': r['banka'], 'skor': r['skor'], 'tur': r['tur']} for r in satirlar]}
    if uyari:
        sonuc['uyari'] = uyari
    # Model hatası geçicidir: yedek öneri yalnız model hiç yapılandırılmamışsa önbelleklenir
    if ob_anahtar is not None and (kaynak == 'yapay_zeka' or cfg is None):
        with _kilit:
            if len(_onbellek) > 64:
                _onbellek.clear()
            _onbellek[ob_anahtar] = sonuc
    return sonuc
