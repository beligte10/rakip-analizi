"""EVDS seri kataloğu (2026-10-02): kategori → veri grubu → seri.

`evds_katalog_olustur.py`'nin (kök dizin) yaptığı işin uygulama içi, aranabilir hali:
EVDS'den kategorileri, veri gruplarını ve her gruptaki serileri çekip tek bir JSON'a
yazar (data/evds_katalog.json). Asistan bu dosyadan SERİ düzeyinde arar (ad, etiket,
grup, kategori), seri kodunu doğrular, orijinal frekansı ve varsayılan toplulaştırmayı
bilir. Dosya yoksa araçlar eski davranışa (yalnız veri grubu araması, canlı API) düşer.

Güncelleme: `python3 scripts/evds_katalog_guncelle.py` (EVDS_API_KEY gerekir, ~3-5 dk)
ya da admin panelinden. Katalog yenilenince bellekteki kopya `yenile()` ile tazelenir.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import evds

_ROOT = Path(__file__).resolve().parents[2]
KATALOG_YOLU = Path(os.environ.get('EVDS_KATALOG_YOLU', _ROOT / 'data' / 'evds_katalog.json'))
SURUM = 1

# Orijinal frekans (TR) → kod; yalnız daha SEYREK frekansa çevrilebilir (kod büyüdükçe seyrekleşir).
FREKANS_SIRASI = {'GÜNLÜK': 1, 'GUNLUK': 1, 'İŞ GÜNÜ': 2, 'IS GUNU': 2, 'HAFTALIK': 3, 'AYDA 2 KEZ': 4,
                  'AYLIK': 5, 'ÜÇ AYLIK': 6, 'UC AYLIK': 6, '3 AYLIK': 6, 'ÇEYREKLİK': 6, 'ALTI AYLIK': 7, '6 AYLIK': 7,
                  'YILLIK': 8}

# Kullanıcı dili → EVDS adlarında geçen karşılıklar (her terim, eş anlamlılarından biriyle eşleşebilir).
SINONIM = {
    'dolar': ['usd', 'abd'], 'avro': ['eur', 'euro'], 'euro': ['eur'], 'sterlin': ['gbp'], 'frank': ['chf'],
    'enflasyon': ['tufe', 'enflasyon'], 'tufe': ['tüfe', 'tufe'], 'ufe': ['üfe', 'ufe'],
    'altin': ['altın', 'altin'], 'faiz': ['faiz'], 'mevduat': ['mevduat'], 'kredi': ['kredi'],
    'kur': ['kur', 'döviz'], 'doviz': ['döviz', 'doviz'], 'rezerv': ['rezerv'],
}

# Sık sorulan konular için doğrulanmış (katalogda var olan) seri kısayolları: sorguda anahtar terimlerden
# biri geçerse bu seriler sonuç listesinin başına konur. Kodlar katalogdan teyit edilmiştir (2026-10-02);
# TP.FG.J0 gibi "(Arşiv)" seriler yerine güncel baz yılı serisi önerilir. Katalogda olmayan kod sessizce atlanır.
ONERILEN = [
    ({'dolar', 'usd'}, ['TP.DK.USD.A.YTL', 'TP.DK.USD.S.YTL']),
    ({'avro', 'euro', 'eur'}, ['TP.DK.EUR.A.YTL', 'TP.DK.EUR.S.YTL']),
    ({'sterlin', 'gbp'}, ['TP.DK.GBP.A.YTL', 'TP.DK.GBP.S.YTL']),
    ({'tufe', 'enflasyon', 'tuketici fiyat'}, ['TP.TUKFIY2025.GENEL']),
    ({'ufe', 'uretici fiyat'}, ['TP.TUFE1YI.T1']),
    ({'fonlama', 'politika faiz', 'politika faizi'}, ['TP.APIFON4']),
    ({'tlref', 'gecelik'}, ['TP.BISTTLREF.ORAN']),
    ({'bist'}, ['TP.MK.F.BILESIK']),
    ({'rezerv'}, ['TP.AB.N07']),
    ({'cari', 'cari islemler', 'cari denge', 'cari acik'}, ['TP.ODANA6.Q01']),
    ({'ihtiyac'}, ['TP.KBK.TRY.KBTF10', 'TP.KKP.TRY.KTF10']),
    ({'konut'}, ['TP.KBK.TRY.18', 'TP.KKP.TRY.18']),
]

_kilit = threading.Lock()
_onbellek: Dict[str, object] = {'katalog': None, 'mtime': None}


def _norm(s: object) -> str:
    s = unicodedata.normalize('NFKD', str(s or '')).casefold().replace('ı', 'i')
    return ''.join(c for c in s if not unicodedata.combining(c))


def _alternatifler(t: str) -> List[str]:
    """Bir arama teriminin eşleşme alternatifleri: kendisi, hafif ek kırpma (faizi → faiz), eş anlamlılar."""
    alt = [t]
    for kes, taban in ((1, 3), (2, 4), (3, 4)):
        if len(t) - kes >= taban:
            alt.append(t[:-kes])
    alt += [_norm(x) for x in SINONIM.get(t, [])]
    return alt


def _tr_buyuk(s: str) -> str:
    return (s or '').replace('i', 'İ').replace('ı', 'I').upper()


def frekans_kodu(frekans_str: str) -> Optional[int]:
    """Katalogdaki FREQUENCY_STR → frekans kodu (1..8); bilinmiyorsa None."""
    f = _tr_buyuk(str(frekans_str or '').strip())
    return FREKANS_SIRASI.get(f)


# ------------------------------------------------------------------ üretim
def _cat_id(v) -> str:
    try:
        return str(int(float(v)))
    except (TypeError, ValueError):
        return str(v or '')


def olustur(ilerleme: Optional[Callable[[int, int], None]] = None, calisan: int = 4) -> dict:
    """EVDS'den tüm kataloğu çeker (API anahtarı gerekir). ~700 seri listesi isteği; 3-5 dk."""
    if not evds.enabled():
        raise evds.ExternalError('EVDS_API_KEY tanımlı değil')
    kats = evds._get('categories/type=json', timeout=60.0) or []
    gruplar = evds._get('datagroups/mode=0&type=json', timeout=90.0) or []
    kategoriler = {}
    for c in kats:
        cid = _cat_id(c.get('CATEGORY_ID'))
        kategoriler[cid] = {'ad': str(c.get('TOPIC_TITLE_TR') or c.get('TOPIC_TITLE_ENG') or cid).strip(),
                            'ad_en': str(c.get('TOPIC_TITLE_ENG') or '').strip(),
                            'ust': _cat_id(c.get('UST_CATEGORY_ID')) if c.get('UST_CATEGORY_ID') not in (None, -1, -1.0) else ''}
    grup_out = {}
    for g in gruplar:
        kod = g.get('DATAGROUP_CODE')
        if not kod:
            continue
        grup_out[kod] = {
            'ad': str(g.get('DATAGROUP_NAME') or '').strip(), 'ad_en': str(g.get('DATAGROUP_NAME_ENG') or '').strip(),
            'kat': _cat_id(g.get('CATEGORY_ID')), 'frekans': str(g.get('FREQUENCY_STR') or '').strip(),
            'birim': str(g.get('BIRIMI') or '').strip(), 'kurum': str(g.get('DATASOURCE') or '').strip(),
            'baslangic': g.get('START_DATE'), 'bitis': g.get('END_DATE'), 'guncelleme': g.get('LAST_UPDATED'),
            'not': str(g.get('NOTE') or '').replace('\n', ' ').strip()[:400],
            'metaveri': g.get('METADATA_LINK') or '',
        }
    kodlar = list(grup_out)
    sonuc: Dict[str, list] = {}
    sayac = {'i': 0}
    kilit = threading.Lock()

    def getir(kod: str):
        rows = []
        for deneme in range(3):
            try:
                rows = evds._get(f'serieList/type=json&code={kod}', timeout=60.0)
                break
            except evds.ExternalError:
                if deneme == 2:
                    rows = []
        out = []
        for s in rows if isinstance(rows, list) else []:
            out.append([s.get('SERIE_CODE'), str(s.get('SERIE_NAME') or '').strip(), kod,
                        str(s.get('FREQUENCY_STR') or '').strip(), s.get('DEFAULT_AGG_METHOD') or '',
                        s.get('START_DATE'), s.get('END_DATE'),
                        str(s.get('TAG') or '').strip(), str(s.get('SERIE_NAME_ENG') or '').strip(),
                        # izin verilen toplulaştırmalar: a=avg f=first l=last x=max n=min s=sum
                        ''.join(k for k, alan in (('a', 'AVGABLE'), ('f', 'FIRSTABLE'), ('l', 'LASTABLE'),
                                                  ('x', 'MAXABLE'), ('n', 'MINABLE'), ('s', 'SUMABLE')) if s.get(alan))])
        with kilit:
            sonuc[kod] = out
            sayac['i'] += 1
            if ilerleme:
                ilerleme(sayac['i'], len(kodlar))

    with ThreadPoolExecutor(max_workers=calisan) as ex:
        list(ex.map(getir, kodlar))
    seriler = [s for kod in kodlar for s in sonuc.get(kod, []) if s[0]]
    return {'surum': SURUM, 'olusturma': datetime.datetime.now().isoformat(timespec='seconds'),
            'kategoriler': kategoriler, 'gruplar': grup_out, 'seriler': seriler}


def kaydet(katalog: dict, yol: Path = KATALOG_YOLU) -> Path:
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    tmp = yol.with_suffix('.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(katalog, f, ensure_ascii=False, separators=(',', ':'))
    tmp.replace(yol)
    yenile()
    return yol


# ------------------------------------------------------------------ okuma / arama
class Katalog:
    """Bellekte hazır, arama için normalize edilmiş katalog."""

    def __init__(self, ham: dict):
        self.ham = ham
        self.kategoriler = ham.get('kategoriler') or {}
        self.gruplar = ham.get('gruplar') or {}
        self.olusturma = ham.get('olusturma')
        self.seriler: List[dict] = []
        self.kod_index: Dict[str, dict] = {}
        for r in ham.get('seriler') or []:
            s = {'kod': r[0], 'ad': r[1], 'grup': r[2], 'frekans': r[3], 'agg': r[4], 'baslangic': r[5], 'bitis': r[6],
                 'tag': r[7] if len(r) > 7 else '', 'ad_en': r[8] if len(r) > 8 else '',
                 'izinli_agg': r[9] if len(r) > 9 else ''}
            g = self.gruplar.get(s['grup'], {})
            s['_ad_n'] = _norm(s['ad'] + ' ' + s['ad_en'])
            s['_grup_n'] = _norm(g.get('ad', '') + ' ' + g.get('ad_en', ''))
            s['_metin'] = _norm(' '.join([s['ad'], s['ad_en'], s['tag'], g.get('ad', ''), g.get('ad_en', ''),
                                          self.kategori_yolu(g.get('kat')), s['kod']]))
            self.seriler.append(s)
            self.kod_index[str(s['kod']).upper()] = s

    def kategori_yolu(self, cid: Optional[str]) -> str:
        parcalar, n = [], 0
        while cid and cid in self.kategoriler and n < 5:
            parcalar.append(self.kategoriler[cid]['ad'])
            cid = self.kategoriler[cid].get('ust') or ''
            n += 1
        return ' > '.join(reversed(parcalar))

    def grup_serileri(self, grup_kodu: str) -> List[dict]:
        if not hasattr(self, '_grup_index'):
            self._grup_index: Dict[str, List[dict]] = {}
            for s in self.seriler:
                self._grup_index.setdefault(s['grup'], []).append(s)
        return self._grup_index.get(grup_kodu, [])

    def grup_ara(self, sorgu: str, limit: int = 8) -> List[dict]:
        """Veri grubu adı/kurum/kategori/kod metninde terimlerin en az yarısı geçenler (en çok eşleşen önce)."""
        terimler = [t for t in _norm(sorgu).split() if len(t) > 1]
        if not terimler:
            return []
        gruplar = [_alternatifler(t) for t in terimler]
        out = []
        for kod, g in self.gruplar.items():
            m = _norm(' '.join([g.get('ad', ''), g.get('ad_en', ''), g.get('kurum', ''), kod,
                                self.kategori_yolu(g.get('kat'))]))
            eslesen = sum(1 for alt in gruplar if any(a in m for a in alt))
            if eslesen * 2 >= len(gruplar):          # terimlerin en az yarısı (grup adı seriden kısa/genel olur)
                ad_n = _norm(g.get('ad', '') + ' ' + g.get('ad_en', ''))
                ad_eslesen = sum(1 for alt in gruplar if any(a in ad_n for a in alt))
                out.append((eslesen, ad_eslesen, str(g.get('bitis') or '')[-4:], kod, g))
        out.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
        return [dict(g, kod=kod, kategori=self.kategori_yolu(g.get('kat')), seri_sayisi=len(self.grup_serileri(kod)))
                for *_, kod, g in out[:limit]]

    def seri(self, kod: str) -> Optional[dict]:
        return self.kod_index.get(str(kod or '').strip().upper())

    def seri_bilgi(self, s: dict) -> dict:
        g = self.gruplar.get(s['grup'], {})
        out = {'kod': s['kod'], 'ad': s['ad'], 'frekans': s['frekans'], 'birim': g.get('birim') or None,
               'varsayilan_toplulastirma': s['agg'] or None, 'grup_kodu': s['grup'], 'grup_adi': g.get('ad'),
               'baslangic': s['baslangic'], 'bitis': s['bitis']}
        if 'arsiv' in _norm(s['ad']):
            out['uyari'] = 'Arşiv serisi (baz yılı değişmiş olabilir); güncel seri için evds_ara ile yeniden ara.'
        return out

    def ara(self, sorgu: str, limit: int = 15) -> List[dict]:
        """Tüm terimler (eş anlamlılarıyla) seri adı/etiket/grup/kategori metninde geçmeli.
        Sıralama: kod tam eşleşmesi > terimlerin seri adında geçmesi > güncellik."""
        ham_terimler = [t for t in _norm(sorgu).split() if len(t) > 1]
        if not ham_terimler:
            return []
        kod = self.seri(sorgu)
        sonuc = [(10 ** 6, kod)] if kod else []
        sorgu_n = _norm(sorgu)
        sorgu_terim = set(ham_terimler)
        for anahtarlar, kodlar in ONERILEN:
            if any((a in sorgu_terim) or (' ' in a and a in sorgu_n) for a in anahtarlar):
                for i, kd in enumerate(kodlar):
                    sd = self.seri(kd)
                    if sd is not None and sd is not kod and all(sd is not x[1] for x in sonuc):
                        sonuc.append((10 ** 5 - i, sd))
        gruplar = []
        for t in ham_terimler:
            gruplar.append(_alternatifler(t))
        eklenen = {id(x[1]) for x in sonuc}
        doviz_istendi = bool(sorgu_terim & {'dolar', 'usd', 'avro', 'euro', 'eur', 'abd', 'doviz', 'yp', 'sterlin', 'gbp'})
        for s in self.seriler:
            if id(s) in eklenen:
                continue
            m = s['_metin']
            if not all(any(a in m for a in alt) for alt in gruplar):
                continue
            puan = sum(100 for alt in gruplar if any(a in s['_ad_n'] for a in alt))
            puan += sum(60 for alt in gruplar if any(a in s['_grup_n'] for a in alt))   # veri grubu adı da konuyu söyler
            puan += 10 if str(s.get('bitis') or '')[-4:] >= str(datetime.date.today().year - 1) else 0
            # Arşiv seriler ve beklenti anketleri, kullanıcı özellikle istemedikçe geriye düşer.
            if 'arsiv' in s['_ad_n'] and 'arsiv' not in sorgu_terim:
                puan -= 80
            # Sorguda döviz belirtilmemişse TL serileri öne çıkar (Euro/USD cinsi seriler geriye).
            if not doviz_istendi and re.search(r'\b(euro|eur|usd|abd dolar\w*)\b', s['_ad_n']):
                puan -= 50
            if ('beklenti' in s['_ad_n'] or s['kod'].startswith(('TP.BEK.', 'TP.PKAUO.', 'TP.HANEBEK.')))\
                    and not (sorgu_terim & {'beklenti', 'beklentisi', 'anket', 'anketi'}):
                puan -= 60
            sonuc.append((puan, s))
        sonuc.sort(key=lambda x: (-x[0], str(x[1]['kod'])))
        return [s for _, s in sonuc[:limit]]


def yukle() -> Optional[Katalog]:
    """Dosyadan (değiştiyse yeniden) yükler; dosya yoksa/okunamıyorsa None."""
    try:
        mtime = KATALOG_YOLU.stat().st_mtime
    except OSError:
        return None
    with _kilit:
        if _onbellek['katalog'] is not None and _onbellek['mtime'] == mtime:
            return _onbellek['katalog']  # type: ignore[return-value]
        try:
            with open(KATALOG_YOLU, encoding='utf-8') as f:
                kat = Katalog(json.load(f))
        except (OSError, ValueError):
            return None
        _onbellek['katalog'], _onbellek['mtime'] = kat, mtime
        return kat


def yenile() -> None:
    with _kilit:
        _onbellek['katalog'], _onbellek['mtime'] = None, None


def ozet() -> dict:
    k = yukle()
    if not k:
        return {'var': False}
    return {'var': True, 'olusturma': k.olusturma, 'kategori': len(k.kategoriler), 'grup': len(k.gruplar),
            'seri': len(k.seriler)}
