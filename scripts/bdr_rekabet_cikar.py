#!/usr/bin/env python3
"""BDR arşivinden (solo PDF) Rekabet Analizi'nin elle yüklenen ölçülerini çeyrek çeyrek çıkarır.

    python3 scripts/bdr_rekabet_cikar.py --arsiv ~/Desktop/BDR-Arsiv/raporlar --ceyrek 2026-2C --kontrol   # elle yüklenenle karşılaştır
    python3 scripts/bdr_rekabet_cikar.py --arsiv ... --ceyrek 2025-4C 2026-1C --cikti cikti/rekabet_gecmis.csv

Çıktı: `olcu,tarih,banka,deger` CSV (scripts/manuel_olcu_yukle.py biçimi; oranlar yüzde, tutarlar mn TL).
Ölçüler: basel_kaldirac_orani, lcr, lcr_yp (tablo satırlarından), serbest_karsilik (dipnot cümlelerinden).
Üretim verisine yazmaz.
"""
import argparse
import csv
import hashlib
import re
import subprocess
import sys
import unicodedata
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')
KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from pipeline import pdf_ingest as P  # noqa: E402

CEYREK_TARIH = {'1C': '03-31', '2C': '06-30', '3C': '09-30', '4C': '12-31'}
ONBELLEK = Path('/private/tmp/claude-501/-Users-farukkezer-Desktop-v3-Rakip-Analizi/544c2269-b9f8-4e93-a0c0-fad7401f80ae/scratchpad/rekabet_onbellek')


def tarih_of(ceyrek: str) -> str:
    y, c = ceyrek.split('-')
    return f'{y}-{CEYREK_TARIH[c]}'


def _metin(yol: Path, sayfa_sonu=None) -> str:
    anahtar = hashlib.md5(f'{yol}|{sayfa_sonu}'.encode()).hexdigest()
    ONBELLEK.mkdir(parents=True, exist_ok=True)
    onb = ONBELLEK / f'{anahtar}.txt'
    if onb.exists():
        return onb.read_text(encoding='utf-8')
    kmd = ['pdftotext', '-layout'] + (['-l', str(sayfa_sonu)] if sayfa_sonu else []) + [str(yol), '-']
    try:
        t = unicodedata.normalize('NFC', subprocess.run(kmd, capture_output=True, check=True, timeout=300).stdout.decode('utf-8', 'ignore'))
    except Exception:
        t = ''
    onb.write_text(t, encoding='utf-8')
    return t


def _slug(ad: str) -> str:
    t = ad.lower().replace('ı', 'i').replace('ö', 'o').replace('ü', 'u').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('İ', 'i')
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')


# arşiv dosya adı ipuçları (slug içinde geçen parça → banka)
_AD_IPUCU = {'Garanti Bankası': ('garanti',), 'Halk Bank': ('halkbank', 'halk-bank'), 'İş Bankası': ('is-bankasi', 'isbank', 'isbtr'),
             'Ziraat Bankası': ('ziraat-bankasi',), 'Yapı Kredi': ('yapi-kredi',), 'Kuveyt Türk': ('kuveyt-turk',),
             'Türkiye Finans': ('turkiye-finans',), 'Vakıfbank': ('vakifbank',), 'Vakıf Katılım': ('vakif-katilim',),
             'Ziraat Katılım': ('ziraat-katilim',), 'Emlak Katılım': ('emlak-katilim',), 'Dünya Katılım': ('dunya-katilim',),
             'Şekerbank': ('sekerbank', 'skbnk'), 'TOM Bank': ('tom-bank',), 'ING Bank': ('ing',), 'Alternatif Bank': ('alternatif',),
             'Burgan Bank': ('burgan',), 'Hayat Finans': ('hayat-finans',), 'Odeabank': ('odeabank',), 'Albaraka': ('albaraka',),
             'Akbank': ('akbank',), 'Denizbank': ('denizbank',), 'Enpara': ('enpara',), 'Fibabanka': ('fibabanka',), 'HSBC': ('hsbc',),
             'QNB': ('qnb',), 'TEB': ('teb',)}


def _belge_metni(yol: Path, sayfa_sonu=None) -> str:
    """PDF → metin; .docx (bazı çeyreklerde TEB) → macOS textutil ile düz metin."""
    if yol.suffix.lower() == '.docx':
        anahtar = hashlib.md5(f'{yol}|docx'.encode()).hexdigest()
        ONBELLEK.mkdir(parents=True, exist_ok=True)
        onb = ONBELLEK / f'{anahtar}.txt'
        if not onb.exists():
            try:
                t = subprocess.run(['textutil', '-convert', 'txt', '-stdout', str(yol)], capture_output=True, check=True, timeout=300).stdout.decode('utf-8', 'ignore')
            except Exception:
                t = ''
            onb.write_text(unicodedata.normalize('NFC', t), encoding='utf-8')
        return onb.read_text(encoding='utf-8')
    return _metin(yol, sayfa_sonu)


def bankalari_bul(klasor: Path, hedef):
    """Çeyrek klasöründeki solo belgeleri bankaya eşler: {banka: yol}. Konsolide dosyalar atlanır. Önce dosya adı ipucu ('turkiye-finans-solo' → Türkiye
    Finans), olmazsa ilk sayfaların içeriği (banka_ve_donem) kullanılır."""
    adaylar = {}
    for yol in sorted(list(klasor.glob('*.pdf')) + list(klasor.glob('*.docx'))):
        ad = yol.name.lower()
        if 'konsolide' in ad and 'olmayan' not in ad:
            continue
        slug = _slug(ad.rsplit('.', 1)[0])
        ad_banka = next((b for b in hedef for ip in _AD_IPUCU.get(b, ()) if re.search(rf'(^|-){re.escape(ip)}(-|$)', slug)), None)
        if ad_banka is not None:
            adaylar.setdefault(ad_banka, []).append((0, yol))
            continue
        ilk = _belge_metni(yol, 4)
        if not ilk:
            continue
        banka, _t = P.banka_ve_donem(ilk)
        if banka not in hedef:
            continue
        up = P._tr_upper(ilk[:6000])
        if 'KONSOLİDE OLMAYAN' not in up and not ad.endswith('solo.pdf'):
            continue
        adaylar.setdefault(banka, []).append((1, yol))
    # aynı banka için birden çok aday olabilir (ör. yanlış klasöre konmuş başka çeyrek dosyası): önce '-solo' adlıları, sonra kalanlar
    return {b: [y for _o, y in sorted(v, key=lambda x: (x[0], not x[1].stem.lower().endswith('solo'), x[1].name))] for b, v in adaylar.items()}


_SAYI = re.compile(r'\(?-?\d[\d.,]*\)?')


def _say(m):
    return P.sayi(m.group(0))


def oranlar(metin: str):
    """LCR (TP+YP, YP) ve Basel III kaldıraç oranı: cari dönem = ilk eşleşen satır."""
    lcr = lcr_yp = kal = None
    for l in metin.split('\n'):
        if lcr is None:
            mh = re.match(r'^\s*(?:\d+\s+)?Likidite\s+Karşılama\s+Oranı\s*(?:\(%\))?\s*:?\s*%?\s*([\d.,]+)\s+%?\s*([\d.,]+)\s*$', l, re.I)
            if mh:
                a1, a2 = P.sayi(mh.group(1)), P.sayi(mh.group(2))
                if a1 and a2 and 20 <= a1 <= 5000:
                    lcr, lcr_yp = a1, a2
        if lcr is None and re.search(r'L[İI]K[İI](?:D[İI]T|T[İI]D)E\s+KAR[ŞS]\s*ILAMA\s+ORANI\s*\(%\)', P._tr_upper(l)):
            sy = [_say(m) for m in _SAYI.finditer(re.sub(r'^.*?\(%\)', '', l, flags=re.I))]
            sy = [x for x in sy if x is not None]
            if len(sy) >= 2:
                lcr, lcr_yp = sy[0], sy[1]
        if kal is None:
            mm = re.match(r'^\s*(?:\d+\.?\s+)?(?:Geçiş\s+Süreci\s+Uygulanmamış\s+)?(?:Basel\s+III\s+)?Kaldıraç\s+[Oo]ranı\s*(?:\(%\))?\s+(.*)$', l, re.I)
            if mm:
                sy = [_say(m) for m in _SAYI.finditer(mm.group(1))]
                sy = [x for x in sy if x is not None]
                if sy and 0.5 <= sy[0] <= 40:
                    kal = sy[0]
    if lcr is None:      # .docx (hücre başına bir satır): etiketten sonraki ilk iki yüzde değeri = TP+YP, YP
        satir = [x.strip().replace('\xa0', '') for x in metin.split('\n')]
        for i, x in enumerate(satir):
            if re.fullmatch(r'Likidite\s+Karşılama\s+Oranı\s*(?:\(%\))?', x, re.I):
                sy = []
                for y in satir[i + 1:i + 10]:
                    m2 = re.fullmatch(r'%?\s*(\d+(?:[.,]\d+)?)', y)
                    if m2:
                        sy.append(P.sayi(m2.group(1)))
                    elif y and not sy:
                        continue
                    elif y:
                        break
                if len(sy) >= 2 and sy[0] and 20 <= sy[0] <= 5000:
                    lcr, lcr_yp = sy[0], sy[1]
                    break
    if kal is None:      # tabloda satır yoksa düzyazı: "konsolide olmayan kaldıraç oranı 31 Aralık 2025 itibarıyla %12,85"
        sx = re.sub(r'\s+', ' ', metin)
        for m in re.finditer(r'kaldıraç\s+oranı(?!nı)[^%.]{0,90}?%\s?([\d]+[.,]\d+)', sx, re.I):
            if not re.search(r'asgari|en az|alt sınır', sx[max(0, m.start() - 60):m.end()], re.I):
                v = P.sayi(m.group(1))
                if v and 0.5 <= v <= 40:
                    kal = v
                    break
    return lcr, lcr_yp, kal


_GURULTU = re.compile(r'serbest\s+(?:muhasebeci|hesap|likit|bölge|piyasa|dolaşım|olmayan)|serbestçe|serbestlik|serbest\s+bırak', re.I)
_TL_VAR = re.compile(r'\d\s*(?:[Mm]ilyon\s*)?TL')
_BIRIM = r'(?:([Mm]ilyon|[Bb]in)\s*)?TL'
_NO = r'(\d{1,3}(?:[.,]\d{3})*|\d+)'
# tutar serbest karşılıktan ÖNCE: araya rakam ya da cümle sonu girmeden ("2.100 milyon TL tutarındaki serbest karşılığı")
_ONCE = re.compile(_NO + r'\s*' + _BIRIM + r'(?:[’\']?(?:si|sı))?\s*(?:tutarında|tutarındaki)?[^0-9.]{0,150}?serbest\s+kar[şs]ıl[ıi][kğ]', re.I)
# tutar SONRA: "serbest karşılık tutarı 1,000 Milyon TL" / "serbest karşılık ayrılmamış olsaydı … diğer karşılıklar 1.210 milyon TL"
_SONRA = [re.compile(r'serbest\s+kar[şs]ıl[ıi][kğ]\s+tutarı\s+' + _NO + r'\s*' + _BIRIM, re.I),
          re.compile(r'serbest\s+kar[şs]ıl[ıi][kğ][^.]{0,120}?olsaydı[^.]{0,120}?diğer\s+karşılıklar\s+(?:ve\s+[^.]{0,40}?sırasıyla\s+)?' + _NO + r'\s*' + _BIRIM, re.I)]


def serbest_karsilik(metin: str, banka: str = ''):
    """Muhtemel riskler için ayrılan serbest karşılık bakiyesi (mn TL).
    "N Milyon TL tutarında … serbest karşılık", "serbest karşılık tutarı N Milyon TL" ya da "serbest karşılık ayrılmamış olsaydı … diğer karşılıklar
    N milyon TL daha az" cümlelerinden; 'iptal' bağlamları (geçmiş dönem iptali) sayılmaz. "Bulunmamaktadır" ya da hiç anılmıyorsa 0; anılıp tutarı
    okunamıyorsa None (inceleme gerekir). Enpara: bölünmeyle devralınan bilanço notundaki 2.500 TL belirsiz kabul edildiği için None."""
    if banka == 'Enpara':
        return None
    from collections import Counter
    s = re.sub(r'\s+', ' ', metin)
    s = re.sub(r'TMS\s*\d+', 'TMS', s)
    anilan = False
    yok = False
    for m in re.finditer(r'serbest\s+kar[şs]ıl[ıi][kğ]', s, re.I):
        if _GURULTU.search(s[m.start():m.end() + 12]) or re.search(r'iptal', s[max(0, m.start() - 120):m.end() + 120], re.I):
            continue
        if re.match(r'.{0,90}(?:bulunmamaktadır|yoktur|bulunmamıştır)', s[m.end():m.end() + 100], re.I) \
                and not re.match(r'\s*giderl', s[m.end():m.end() + 12], re.I):
            yok = True               # "… bulunmamaktadır"; tutar bulunursa o önceliklidir ('serbest karşılık giderlerinden bulunmamaktadır' gider cümlesidir)
        if _TL_VAR.search(s[max(0, m.start() - 170):m.end() + 200]):
            anilan = True            # tutar içeren cümle; yalnız politika anlatan cümleler (tutarsız) sayılmaz
    # tutar birimi: açık "milyon TL" → 1, "bin TL" → 1/1000; yalnız "TL" → belgenin ana birimi (başlıkta "Milyon Türk Lirası" ya da "Bin Türk Lirası")
    mn = len(re.findall(r'milyon\s+türk\s+lirası', s[:60000], re.I))
    bn = len(re.findall(r'bin\s+türk\s+lirası', s[:60000], re.I))
    belge = 0.001 if bn > mn else 1.0

    def deger(m):
        v = P.sayi(m.group(1))
        b = (m.group(2) or '').lower()
        return None if v is None else v * (1.0 if b == 'milyon' else 0.001 if b == 'bin' else belge)
    once = [deger(m) for m in _ONCE.finditer(s) if not re.search(r'iptal', m.group(0) + s[m.end():m.end() + 45], re.I)]
    if once:
        return Counter(once).most_common(1)[0][0]
    sonra = [deger(m) for k in _SONRA for m in k.finditer(s)]
    if sonra:
        return Counter(sonra).most_common(1)[0][0]
    if yok or not anilan:
        return 0.0
    return None


_TUFEX_VAR = re.compile(r'(?:yıllık\s*%\s*(\d{1,2}(?:[.,]\d+)?)\s*(?:enflasyon|TÜFE)\s*tahmin|'
                        r'tahmini\s+enflasyon\s+oranı\s+yıllık\s+%\s*(\d{1,2}(?:[.,]\d+)?))', re.I)
_TUFEX_ACIK = re.compile(r'referans\s+endeks\w*\s+göre\s+yapılsaydı(?:[^.]|\.(?=\d)){0,300}?net\s+dönem\s+kar\w*\s+([\d.,]+)\s*([Mm]ilyon\s*)?TL\s+(artarak|azalarak)', re.I)
_TUFEX_DUY = re.compile(
    r'(?:TÜFE|enflasyon)\s+tahmin\w*\s+(?:oranının\s+)?(?:%\s*(\d+(?:[.,]\d+)?)|(\d+)\s*baz\s*puan)[^.]{0,260}?'
    r'(?:vergi\s+öncesi|net\s+dönem)[^.]{0,40}?(?:kâr|kar)\w*[^.]{0,30}?(?:yaklaşık\s*)?([\d]{1,3}(?:[.,]\d+)*)\s*(milyar|milyon|Milyon)?', re.I)


def tufex_bilgisi(metin: str):
    """TÜFE'ye endeksli devlet tahvili değerlemesindeki yıllık enflasyon varsayımı (%) ve duyarlılık (1 puanlık değişimin vergi öncesi kâra etkisi, mn TL).
    "değerlemesi yıllık %30 enflasyon tahminine göre yapılmıştır. TÜFE tahmininin %1 artması … vergi öncesi dönem karı yaklaşık 1.136 milyar TL …"
    Cümle yoksa (varsayım, duyarlılık) = (None, None)."""
    s = re.sub(r'(\d{2})\.(\d{2})\.(\d{4})', r'\1/\2/\3', re.sub(r'\s+', ' ', metin))      # tarihlerdeki noktalar cümle sonu sanılmasın
    mv = _TUFEX_VAR.search(s)
    if not mv:
        return None, None
    g = mv.group(1) or mv.group(2)
    varsayim = P.sayi(g.replace(',', '.')) if g else None
    md = _TUFEX_DUY.search(s, mv.start() - 200 if mv.start() > 200 else 0)
    if not md:
        return varsayim, None
    puan = float(md.group(1).replace(',', '.')) if md.group(1) else float(md.group(2)) / 100.0
    ham = md.group(3)
    birim = (md.group(4) or '').lower()
    if birim == 'milyar':                                  # "1.136 milyar TL" → 1.136 × 1000 mn; "1 milyar" → 1000 mn
        tutar = float(ham.replace(',', '.')) * 1000
    elif birim == 'milyon':
        tutar = P.sayi(ham)
    else:                                                  # birimsiz "TL": belgenin ana birimi (Bin Türk Lirası → ÷1000)
        mn = len(re.findall(r'milyon\s+türk\s+lirası', s[:60000], re.I))
        bn = len(re.findall(r'bin\s+türk\s+lirası', s[:60000], re.I))
        tutar = P.sayi(ham)
        tutar = tutar * 0.001 if tutar is not None and bn > mn else tutar
    if not tutar or not puan:
        return varsayim, None
    return varsayim, tutar / puan


def tufex_aciklanmis(metin: str):
    """Banka tamponu doğrudan açıklıyorsa (mn TL): "referans endekse göre yapılsaydı … net dönem karı 1.514 TL artarak …" (Denizbank, QNB)."""
    s = re.sub(r'\s+', ' ', metin)
    m = _TUFEX_ACIK.search(s)
    if not m:
        return None
    v = P.sayi(m.group(1))
    if v is not None and m.group(3).lower() == 'azalarak':
        v = -v                       # referans endeksle değerleme kârı azaltıyorsa tampon negatiftir
    if v is None or m.group(2):
        return v
    mn = len(re.findall(r'milyon\s+türk\s+lirası', s[:60000], re.I))
    bn = len(re.findall(r'bin\s+türk\s+lirası', s[:60000], re.I))
    return v * 0.001 if bn > mn else v


def tufex_tamponu(varsayim, duyarlilik, tarih):
    """Türetilmiş TÜFEX tamponu (mn TL) = (gerçekleşen yıllık TÜFE − varsayım) × 1 puanlık duyarlılık; TÜFE serisi pipeline/makro."""
    from pipeline.makro import tufe_yillik
    gercek = tufe_yillik(tarih)
    if None in (varsayim, duyarlilik, gercek):
        return None
    return (round(gercek, 2) - varsayim) * duyarlilik


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--arsiv', type=Path, default=Path.home() / 'Desktop/BDR-Arsiv/raporlar')
    ap.add_argument('--ceyrek', nargs='+', required=True)
    ap.add_argument('--cikti', type=Path)
    ap.add_argument('--kontrol', action='store_true', help='elle yüklenmiş değerlerle karşılaştır')
    a = ap.parse_args(argv)
    import json
    from pipeline import manuel_veri
    kat = json.loads((KOK / 'catalog.seed.json').read_text(encoding='utf-8'))
    hedef = {b['banka_adi'] for b in kat['banks']}
    satirlar = []
    for cq in a.ceyrek:
        tarih = tarih_of(cq)
        bulunan = bankalari_bul(a.arsiv / cq, hedef)
        print(f'{cq} ({tarih}): {len(bulunan)}/{len(hedef)} banka PDF\'i bulundu; eksik: {sorted(hedef - set(bulunan))}')
        for banka, yollar in sorted(bulunan.items()):
            metin = yol = None
            for aday in yollar:
                t = _belge_metni(aday)
                _b, donem = P.banka_ve_donem(t)
                if donem and donem != tarih:
                    print(f'   ! {banka}: {aday.name} dönemi {donem}, beklenen {tarih} → atlandı')
                    continue
                metin, yol = t, aday
                break
            if metin is None:
                continue
            lcr, lcr_yp, kal = oranlar(metin)
            sk = serbest_karsilik(metin, banka)
            for ad, v in (('lcr', lcr), ('lcr_yp', lcr_yp), ('basel_kaldirac_orani', kal), ('serbest_karsilik', sk)):
                if v is not None:
                    satirlar.append((ad, tarih, banka, v))
            if a.kontrol:
                fark = []
                for ad, v in (('lcr', lcr), ('lcr_yp', lcr_yp), ('basel_kaldirac_orani', kal), ('serbest_karsilik', sk)):
                    m = manuel_veri.deger(ad, banka, tarih)
                    m = None if m is None else (m / 1e6 if ad == 'serbest_karsilik' else m)
                    tol = 0.06 if ad != 'serbest_karsilik' else 0.6
                    if (m is None) != (v is None) or (m is not None and abs(m - v) > tol):
                        fark.append(f'{ad}: PDF {v} ≠ elle {None if m is None else round(m, 2)}')
                print(f'   {banka:16}', 'tamam' if not fark else ' | '.join(fark))
    if a.cikti:
        a.cikti.parent.mkdir(parents=True, exist_ok=True)
        with a.cikti.open('w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['olcu', 'tarih', 'banka', 'deger'])
            w.writerows(satirlar)
        print('yazıldı:', a.cikti, len(satirlar), 'satır')
    return 0


if __name__ == '__main__':
    sys.exit(main())
