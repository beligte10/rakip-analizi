"""EVDS bilgi tabanı (assistant/external/evds_bilgi_tabani.md) — bölümlere ayrılmış, asistana
`evds_rehber` aracıyla ihtiyaç anında verilir (tüm doküman her soruda isteme taşınmaz).

Bölümler dosyadaki "## N. Başlık" satırlarından okunur; konu anahtarı → bölüm numarası eşlemesi
aşağıdadır. Dosya yoksa araç hata yerine kısa bir uyarı döner.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

DOSYA = Path(__file__).with_name('evds_bilgi_tabani.md')

# konu → (bölüm no, kısa açıklama)
KONULAR: Dict[str, tuple] = {
    'genel': (1, 'EVDS nedir; kategori > veri grubu > seri hiyerarşisi'),
    'seri_kodu': (2, 'Seri kodu nasıl okunur (TP.DK.USD.A.YTL …)'),
    'ornek_seriler': (3, 'Sık kullanılan seriler (kurlar, TÜFE, ÜFE, fonlama maliyeti)'),
    'api': (4, 'API parametreleri ve metaveri uç noktaları'),
    'frekans': (5, 'Frekans kodları; yalnız daha seyrek frekansa çevrilebilir'),
    'toplulastirma': (6, 'avg/min/max/first/last/sum — stok ve akım için doğru seçim'),
    'formul': (7, 'Formüller (yüzde değişim, fark, yıllık değişim, YTD, hareketli ortalama)'),
    'yanit': (8, 'Yanıt yapısı ve veri okuma kuralları (boş değer ≠ 0)'),
    'olcu_turleri': (9, 'Fiyat/endeks/oran/stok/akım türleri ve toplulaştırma'),
    'hatalar': (10, 'Sık hatalar ve çözümleri'),
    'davranis': (11, 'Asistan davranış kuralları'),
}


def _bolumler() -> Dict[int, str]:
    try:
        metin = DOSYA.read_text(encoding='utf-8')
    except OSError:
        return {}
    out: Dict[int, str] = {}
    parcalar = re.split(r'(?m)^## (\d+)\.\s', metin)
    # parcalar: [giriş, no, gövde, no, gövde …]
    for i in range(1, len(parcalar) - 1, 2):
        govde = parcalar[i + 1].split('\n---', 1)[0].strip()
        out[int(parcalar[i])] = '## ' + parcalar[i] + '. ' + govde
    return out


_onbellek: Optional[Dict[int, str]] = None


def bolumler() -> Dict[int, str]:
    global _onbellek
    if _onbellek is None:
        _onbellek = _bolumler()
    return _onbellek


def konu_listesi() -> List[dict]:
    return [{'konu': k, 'aciklama': a} for k, (_, a) in KONULAR.items()]


def getir(konu: str) -> Optional[str]:
    """Konunun bölüm metni; bilinmeyen konu ya da dosya yoksa None."""
    ref = KONULAR.get(str(konu or '').strip().lower())
    if not ref:
        return None
    return bolumler().get(ref[0])


def davranis_kurallari() -> str:
    """Bölüm 11'in kural satırları (sistem istemine gömülür); dosya yoksa boş."""
    b = bolumler().get(11, '')
    kurallar = re.findall(r'(?m)^\d+\.\s+(.*)$', b)
    return '\n'.join(f'- {k}' for k in kurallar)
