"""
pipeline.custom_measure_rules
==============================
"Ölçü Oluştur" (kullanıcı tanımlı özel ölçü) için ANLAM kuralları: hangi
A/B/işlem kombinasyonu geçerli, sonuç hangi birimde çıkar.

Değer hesabı tarayıcıda yapılır (frontend/index_v30.html::customMeasureSpec,
AYNI kuralların JS karşılığı); sunucu burada yalnız tanımın anlamlı olup
olmadığını doğrular ki API'ye doğrudan istek atılarak da saçma bir ölçü
kaydedilemesin. İki taraf değişirse birlikte değişmeli.

Kurallar (2026-09-24):
- A ile B aynı ölçü olamaz.
- Fark/Toplam: aynı birim; tutar ölçülerde akım (gelir tablosu, YtD) ile
  stok (bilanço) karıştırılamaz.
- Oran: rasyo ile tutar oranlanamaz. Tutar/tutar:
    TL/TL     → yüzde (varsayılan) veya kat
    adet/adet → kat (varsayılan) veya yüzde
    TL/adet   → bin TL (birim başına; ör. personel başına kredi)
    adet/TL   → geçersiz
  Rasyo/rasyo → kat (varsayılan) veya yüzde.
- A×Sabit: her ölçüde geçerli.
"""
from __future__ import annotations
from typing import Dict, List, Optional

OPS = ('ratio', 'diff', 'sum', 'scale')
BICIMLER = ('pct', 'kat')


def ratio_formats(ma: dict, mb: dict) -> List[str]:
    """Oran için izin verilen biçimler; ilki varsayılan. Boş liste = geçersiz.
    'bin_TL' sabit biçimdir (seçilemez)."""
    ta, tb = ma.get('tip'), mb.get('tip')
    if ta == 'rasyo' and tb == 'rasyo':
        return ['kat', 'pct']
    if ta != tb:
        return []
    ba, bb = ma.get('birim'), mb.get('birim')
    if ba == 'TL' and bb == 'TL':
        return ['pct', 'kat']
    if ba == 'adet' and bb == 'adet':
        return ['kat', 'pct']
    if ba == 'TL' and bb == 'adet':
        return ['bin_TL']
    return []


def check(op: str, a: str, b: Optional[str], bicim: Optional[str],
          by_id: Dict[str, dict]) -> Optional[str]:
    """Hata mesajı ya da None (geçerli)."""
    if op not in OPS:
        return f"Geçersiz işlem: '{op}'"
    ma = by_id.get(a)
    if ma is None:
        return f"'{a}' geçerli bir ölçü değil"
    if op == 'scale':
        return None
    mb = by_id.get(b) if b else None
    if mb is None:
        return f"'{b}' geçerli bir ölçü değil"
    if a == b:
        return 'A ve B aynı ölçü olamaz'
    if op in ('diff', 'sum'):
        if ma.get('birim') != mb.get('birim'):
            return (f"Birimler uyuşmuyor ({ma.get('birim')} ≠ {mb.get('birim')}) — "
                    f"fark/toplam için aynı birimde iki ölçü seçin")
        if (ma.get('tip') == 'buyukluk' and mb.get('tip') == 'buyukluk'
                and ma.get('akim_stok') != mb.get('akim_stok')):
            return ('Gelir tablosu kalemi (yılbaşından kümülatif) ile bilanço kalemi '
                    '(dönem sonu bakiye) toplanamaz/çıkarılamaz')
        return None
    formats = ratio_formats(ma, mb)
    if not formats:
        return 'Bu iki ölçünün oranı anlamlı değil (rasyo ile tutar ya da adet / TL)'
    if bicim is not None and bicim not in formats:
        return f"Bu oran için geçersiz biçim: '{bicim}'"
    return None
