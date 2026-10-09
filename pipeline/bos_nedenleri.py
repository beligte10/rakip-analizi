"""
pipeline.bos_nedenleri
=======================
Rekabet Analizi ölçülerinde değeri OLMAYAN (banka × dönem) hücrelerin nedenini kural tabanlı üretir; arayüz bu hücreleri listeden
sessizce çıkarmak yerine "Tanımsız" / "Veri yok" etiketiyle, nedenini yazarak gösterir.

  tanimsiz : değer matematiksel olarak tanımlı değil (şubesi yok, önceki yıl kârı ≤ 0, payda sıfır ...) — veri eksikliği değildir.
  veri_yok : değer olması gerekirdi ama kaynak veri yok / açıklanmıyor (TÜFEX varsayımı verilmemiş, BDR verisi yüklenmemiş ...).

Çıktı: {ölçü_id: {banka: {tarih: [kod, metin]}}} — yalnız son DONEM_SAYISI çeyrek ve yalnız değeri boş hücreler (data/bos_nedenleri.json).
"""
from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple

from . import manuel_veri
from . import rekabet_olculer as R

TANIMSIZ, VERI_YOK = 'tanimsiz', 'veri_yok'
DONEM_SAYISI = 12

Neden = Tuple[str, str]


def _yuklu_donem(ad: str, t: str) -> bool:
    """Elle/BDR'den yüklenen ölçü için bu tarihte HİÇBİR bankada değer yüklenmemişse dönem hiç yüklenmemiştir."""
    veri = (manuel_veri.yukle()['olculer'].get(ad) or {}).get('veri') or {}
    return bool(veri.get(str(t)[:10]))


def _guv(fn, *a):
    try:
        return fn(*a)
    except Exception:
        return None


def _onceki_yil(ctx, b, t) -> Optional[str]:
    return _guv(ctx.yoy_period, b, t)


def _personel(ctx, b, t):
    return _guv(ctx.sube, b, t, 'Personel Sayısı')


def _sube(ctx, b, t):
    return _guv(ctx.sube, b, t, 'Şube Sayısı')


def _faaliyet_yok(ctx, b, t) -> bool:
    """Bankanın bu dönem için bilançosu hiç yok (henüz faaliyette değil / veri yüklenmemiş)."""
    ta = _guv(ctx.bilanco, b, t, 'Toplam Aktifler')
    return not ta


# ---- ölçü kuralları ----------------------------------------------------------------------------------------------

def _sube_basina(ctx, b, t) -> Optional[Neden]:
    if not _sube(ctx, b, t):
        return TANIMSIZ, 'Şubesi yok (dijital banka) — şube başına oran tanımsız'
    return None


def _personel_yoy(ctx, b, t) -> Optional[Neden]:
    prev = _onceki_yil(ctx, b, t)
    if not _personel(ctx, b, t):
        return VERI_YOK, 'Bu dönem personel sayısı yok'
    if prev is None or not _personel(ctx, b, prev):
        return TANIMSIZ, 'Önceki yıl personel verisi yok (banka o tarihte faaliyette değildi) — yıllık değişim tanımsız'
    return None


def _net_kar_yoy(ctx, b, t) -> Optional[Neden]:
    prev = _onceki_yil(ctx, b, t)
    if prev is None:
        return VERI_YOK, 'Önceki yıl verisi yok'
    onceki = _guv(R._net_kar, ctx, b, prev)
    if onceki is None:
        return VERI_YOK, 'Önceki yıl net kâr verisi yok'
    if onceki <= 0:
        return TANIMSIZ, 'Önceki yıl net kârı sıfır ya da negatif — büyüme oranı tanımsız'
    return None


def _grup2(ctx, b, t) -> Optional[Neden]:
    return TANIMSIZ, 'Grup 2 (yakın izleme) kredisi yok ya da sıfır — karşılama oranı tanımsız'


def _altin(ctx, b, t) -> Optional[Neden]:
    if not _guv(ctx.kiymetli_maden, b, t):
        return TANIMSIZ, 'Altın (kıymetli maden) hesabı yok — pay tanımsız'
    return None


def _tufex(ctx, b, t) -> Optional[Neden]:
    if not _yuklu_donem('tufex_tamponu', t):
        return VERI_YOK, 'Bu dönem için BDR verisi yüklenmedi'
    return VERI_YOK, 'TÜFEX hesaplanamıyor: banka tahmini enflasyonla değerliyor ama varsayımı/duyarlılığı açıklamıyor'


def _kar_tamponu(ctx, b, t) -> Optional[Neden]:
    if not _yuklu_donem('serbest_karsilik', t):
        return VERI_YOK, 'Bu dönem için BDR verisi yüklenmedi'
    sk, tx = manuel_veri.deger('serbest_karsilik', b, t), manuel_veri.deger('tufex_tamponu', b, t)
    if sk is None and tx is None:
        return VERI_YOK, 'Serbest karşılık ve TÜFEX verisi yok'
    if tx is None:
        return VERI_YOK, 'TÜFEX tamponu bilinmediği için kâr tamponu hesaplanamıyor (kısmi tampon gösterilmez)'
    return VERI_YOK, 'Serbest karşılık bakiyesi belirlenemedi'


def _manuel(ad: str) -> Callable:
    def f(ctx, b, t) -> Optional[Neden]:
        if not _yuklu_donem(ad, t):
            return VERI_YOK, 'Bu dönem için BDR verisi yüklenmedi (yalnız son 8 çeyrek yüklü)'
        if manuel_veri.deger(ad, b, t) is None:
            return VERI_YOK, 'Bu ölçü BDR dipnotundan alınır; bu bankanın bu dönemi için değer okunamadı / yüklenmedi'
        return None
    return f


def _ortuk(ctx, b, t) -> Optional[Neden]:
    if not _guv(R._ort_tcmb, ctx, b, t):
        return TANIMSIZ, 'Ortalama TCMB hesabı sıfır (banka yeni faaliyete başladı; 12 aylık ortalama için TCMB hesabı geçmişi yok) — örtük getiri tanımsız'
    return None


def _fonlama(ctx, b, t) -> Optional[Neden]:
    from .measures import m_toplam_fonlama
    if not _guv(m_toplam_fonlama, ctx, b, t):
        return TANIMSIZ, 'Toplam fonlama sıfır (banka henüz fon toplamıyordu) — oran tanımsız'
    return None


def _donuk(ctx, b, t) -> Optional[Neden]:
    return TANIMSIZ, 'Donuk alacak hareketi ya da payda sıfır — oran tanımsız'


_KURALLAR: Dict[str, Callable] = {
    'sube_basina_opex': _sube_basina,
    'personel_sayisi_yoy': _personel_yoy,
    'personel_basina_personel_gideri_yoy': _personel_yoy,
    'personel_basina_opex_yoy': _personel_yoy,
    'personel_basina_opex': lambda c, b, t: None if _personel(c, b, t) else (VERI_YOK, 'Personel sayısı yok'),
    'net_kar_yoy_buyumesi': _net_kar_yoy,
    'reel_net_kar_buyumesi': _net_kar_yoy,
    'grup_2_karsilama': _grup2,
    'ortuk_tcmb_getirisi': _ortuk,
    'yp_toplam_fonlama_payi': _fonlama,
    'krediler_toplam_fonlama': _fonlama,
    'altin_vadesiz_payi': _altin,
    'tufex_tamponu': _tufex,
    'kar_tamponu_net_kar': _kar_tamponu,
    'serbest_karsilik': _manuel('serbest_karsilik'),
    'lcr': _manuel('lcr'),
    'lcr_yp': _manuel('lcr_yp'),
    'basel_kaldirac_orani': _manuel('basel_kaldirac_orani'),
    'donuk_portfoy_temizligi': _donuk,
    'donuk_tahsilat_intikal': _donuk,
    'npl_3_asama_karsilama': _donuk,
}


def neden(ctx, mid: str, banka: str, tarih: str) -> Neden:
    """Değeri boş bir hücre için (tür, metin). Kural bir neden bulamazsa genel metin."""
    if _faaliyet_yok(ctx, banka, tarih):
        return VERI_YOK, 'Bu dönem için banka verisi yok (banka henüz faaliyette değildi ya da rapor yüklenmedi)'
    kural = _KURALLAR.get(mid)
    sonuc = _guv(kural, ctx, banka, tarih) if kural else None
    return sonuc or (TANIMSIZ, 'Gerekli kalemler bu dönemde yok ya da payda sıfır — oran tanımsız')


def uret(ctx, catalog: dict, bank_data: dict) -> Dict[str, Dict[str, Dict[str, list]]]:
    """Rekabet Analizi ölçüleri için son DONEM_SAYISI çeyrekte değeri boş her hücrenin nedeni."""
    bankalar = [b['banka_adi'] for b in catalog['banks']]
    tarihler = sorted({t for ser in bank_data.get(R.IDS[0], {}).values() for t in ser})[-DONEM_SAYISI:]
    out: Dict[str, Dict[str, Dict[str, list]]] = {}
    for mid in R.IDS:
        ser = bank_data.get(mid, {})
        for b in bankalar:
            for t in tarihler:
                if (ser.get(b) or {}).get(t) is None:
                    kod, metin = neden(ctx, mid, b, t)
                    out.setdefault(mid, {}).setdefault(b, {})[t] = [kod, metin]
    return out
