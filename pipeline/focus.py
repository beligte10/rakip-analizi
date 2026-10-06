"""
pipeline.focus
==============
Odak banka (2026-10-01): dashboard'un üzerinden okunduğu banka. Varsayılan Kuveyt
Türk; admin panelinden başka bir banka seçilince grup yapısı o bankaya göre
yeniden adlandırılır, arayüz (vurgu rengi, sıra rozeti, hızlı seçimler, asistan)
odak bankayı kullanır.

catalog['groups']['focus'] odak bankanın adını tutar (yoksa Kuveyt Türk). Bu alan
`groups` içinde olduğu için seed senkronunda (app._sync_catalog_from_seed) canlı
katalogdan korunur.

apply_focus_bank katalog üzerinde SAF bir dönüşümdür (dosya/ağ yok); recompute'u
çağıran taraf yapar.
"""
from __future__ import annotations

from typing import Dict, List, Optional

VARSAYILAN_ODAK = 'Kuveyt Türk'
SEGMENTLER = ('Katılım Bankaları', 'Mevduat Bankaları')
RAKIP_GRUBU = 'Rakip Bankalar'
HARIC_AYRAC = ' Hariç '


def focus_of(catalog: Optional[dict]) -> str:
    """Katalogdaki odak banka; yoksa ya da bankalar listesinde değilse Kuveyt Türk."""
    groups = (catalog or {}).get('groups') or {}
    odak = groups.get('focus') or VARSAYILAN_ODAK
    return odak


def kisa_ad(banka: str) -> str:
    """Grup adlarında kullanılan kısa banka adı (Kuveyt Türk → KT)."""
    if banka == VARSAYILAN_ODAK:
        return 'KT'
    for ek in (' Bankası', ' Bank'):
        if banka.endswith(ek) and len(banka) > len(ek):
            return banka[: -len(ek)]
    return banka


def _yeniden_adlandir(groups: dict, eski: str, yeni: str) -> None:
    """order / members / colors içinde grup adını, sırasını koruyarak değiştirir."""
    groups['order'] = [yeni if g == eski else g for g in groups.get('order', [])]
    for alan in ('members', 'colors'):
        d = groups.get(alan) or {}
        if eski in d:
            groups[alan] = {(yeni if k == eski else k): v for k, v in d.items()}


def apply_focus_bank(catalog: dict, yeni: str) -> Dict[str, object]:
    """Odak bankayı değiştirir; değişiklik özetini döndürür.

    1. Odak grubu ('Kuveyt Türk' gibi tek bankalık grup) yeni bankanın adını alır.
    2. '<X> Hariç <Segment>' grubu yeni bankanın segmentine göre kurulur
       (Katılım ise 'Katılım Bankaları', değilse 'Mevduat Bankaları'; üyeler =
       segment − odak banka).
    3. Odak banka 'Rakip Bankalar' grubundan çıkarılır (rakip = odak dışındakiler).
    ValueError: bilinmeyen banka ya da ad çakışması.
    """
    gercek = {b['banka_adi'] for b in catalog.get('banks', []) if b.get('tur') != 'Grup'}
    if yeni not in gercek:
        raise ValueError(f'Bilinmeyen banka: {yeni}')
    groups = catalog.setdefault('groups', {'order': [], 'members': {}, 'colors': {}})
    groups.setdefault('order', [])
    groups.setdefault('members', {})
    groups.setdefault('colors', {})
    eski = focus_of(catalog)
    if yeni == eski:
        return {'degisti': False, 'odak': yeni}
    uyeler = groups['members']
    degisen: List[str] = []

    # 1) odak grubu
    if yeni in uyeler and yeni != eski:
        raise ValueError(f"'{yeni}' adında bir grup zaten var")
    if eski in uyeler:
        _yeniden_adlandir(groups, eski, yeni)
        groups['members'][yeni] = [yeni]
    else:
        groups['order'].insert(0, yeni)
        groups['members'][yeni] = [yeni]
        groups['colors'].setdefault(yeni, '#559D87')
    degisen.append(f'{eski} → {yeni}')
    uyeler = groups['members']   # _yeniden_adlandir sözlüğü yeniden kurar

    # 2) "<X> Hariç <Segment>" grubu
    segment = next((s for s in SEGMENTLER if yeni in (uyeler.get(s) or [])), None)
    haric = next((g for g in groups['order'] if HARIC_AYRAC in g and g != yeni), None)
    if haric and segment:
        yeni_haric = f'{kisa_ad(yeni)}{HARIC_AYRAC}{segment}'
        if yeni_haric != haric and yeni_haric not in uyeler:
            _yeniden_adlandir(groups, haric, yeni_haric)
            haric = yeni_haric
            uyeler = groups['members']
        groups['members'][haric] = [b for b in (uyeler.get(segment) or []) if b != yeni]
        degisen.append(f'{haric} güncellendi')

    # 3) rakip grubu: önceki geçişte çıkarılan banka (varsa) eski yerine geri konur;
    #    yeni odak rakip grubundan çıkarılır (kaydı tutulur, ileride geri alınabilsin).
    rakip = uyeler.get(RAKIP_GRUBU)
    if rakip is not None:
        kayit = groups.pop('rakip_cikarilan', None)
        if kayit and kayit.get('banka') in gercek and kayit['banka'] != yeni and kayit['banka'] not in rakip:
            rakip = list(rakip)
            rakip.insert(min(int(kayit.get('sira', len(rakip))), len(rakip)), kayit['banka'])
            uyeler[RAKIP_GRUBU] = rakip
            degisen.append(f"{kayit['banka']} {RAKIP_GRUBU} grubuna geri eklendi")
        if yeni in rakip and len(rakip) > 1:
            groups['rakip_cikarilan'] = {'banka': yeni, 'sira': rakip.index(yeni)}
            uyeler[RAKIP_GRUBU] = [b for b in rakip if b != yeni]
            degisen.append(f'{yeni} {RAKIP_GRUBU} grubundan çıkarıldı')

    groups['focus'] = yeni
    return {'degisti': True, 'odak': yeni, 'onceki': eski, 'degisiklikler': degisen}


def rakipleri_normalle(catalog: dict, odak: str, rakipler) -> Optional[List[str]]:
    """Seçilen rakip listesi: yalnız gerçek bankalar, odak banka hariç, tekrarsız, sırası korunur.
    Boş / geçersiz liste → None."""
    if not rakipler:
        return None
    gercek = {b['banka_adi'] for b in catalog.get('banks', []) if b.get('tur') != 'Grup'}
    out: List[str] = []
    for b in rakipler:
        b = str(b).strip()
        if b in gercek and b != odak and b not in out:
            out.append(b)
    return out or None


def set_rakipler(catalog: dict, rakipler: List[str]) -> List[str]:
    """'Rakip Bankalar' grubunu verilen listeyle kurar (2026-10-03: odak bankaya göre yapay zeka önerisi
    ya da kullanıcı seçimi). Grup yoksa odak grubundan sonra eklenir. Değişiklik özetini döndürür."""
    groups = catalog.setdefault('groups', {'order': [], 'members': {}, 'colors': {}})
    uyeler = groups.setdefault('members', {})
    sira = groups.setdefault('order', [])
    onceki = list(uyeler.get(RAKIP_GRUBU) or [])
    if RAKIP_GRUBU not in uyeler:
        odak = groups.get('focus') or VARSAYILAN_ODAK
        sira.insert(sira.index(odak) + 1 if odak in sira else 0, RAKIP_GRUBU)
        groups.setdefault('colors', {}).setdefault(RAKIP_GRUBU, '#E8A33D')
    uyeler[RAKIP_GRUBU] = list(rakipler)
    groups.pop('rakip_cikarilan', None)   # liste açıkça seçildi; eski geri-ekleme kaydı geçersiz
    if onceki == list(rakipler):
        return []
    return [f'{RAKIP_GRUBU}: {", ".join(rakipler)}']


def focus_overlay(catalog: dict, computed: dict, ctx, banka: str,
                  rakipler: Optional[List[str]] = None) -> Dict[str, object]:
    """Kullanıcı bazlı odak banka katmanı (2026-10-02).

    Genel katalog odağı (admin varsayılanı) yerine `banka` odak alındığında
    DEĞİŞEN grupları (odak grubu, '<X> Hariç <Segment>', 'Rakip Bankalar')
    yeniden hesaplar; `rakipler` verilirse 'Rakip Bankalar' bu listeyle kurulur; diğer her şey ortak computed.json'dan gelir. Dönüş, istemcinin
    computed.json üzerine uyguladığı küçük bir yamadır:
      meta (focus_bank, groups, group_order, group_colors, default_date),
      kaldirilan (artık olmayan grup adları), group_data / composition_group /
      currency_group (yalnız değişen gruplar).
    """
    import copy
    from .groups import build_group_data
    from .composition import build_composition_payload

    varyant = copy.deepcopy(catalog)
    apply_focus_bank(varyant, banka)
    rakipler = rakipleri_normalle(varyant, banka, rakipler)
    if rakipler:
        set_rakipler(varyant, rakipler)
    g0, g1 = catalog.get('groups') or {}, varyant['groups']
    m0, m1 = g0.get('members') or {}, g1['members']
    degisen = [ad for ad in g1['order'] if m1.get(ad) != m0.get(ad)]
    kaldirilan = [ad for ad in (g0.get('order') or []) if ad not in m1]

    alt = copy.deepcopy(varyant)
    alt['groups'] = {'order': degisen, 'members': {ad: m1[ad] for ad in degisen},
                     'colors': {ad: (g1.get('colors') or {}).get(ad) for ad in degisen},
                     'focus': banka}
    # alt kataloğun grup üyelikleri yalnız değişenler; 'Rakip Bankalar + <odak>' hesabı için gerçek rakipler lazım
    alt['groups']['members'].setdefault('Rakip Bankalar', m1.get('Rakip Bankalar', []))
    group_data = build_group_data(computed.get('bank_data', {}), alt, ctx) if degisen else {}

    # Kompozisyon: yalnız değişen grupların üyeleri banka listesine konur (banka kısmı atılır).
    uyeler = sorted({b for ad in degisen for b in m1[ad]})
    alt_komp = dict(alt, banks=[b for b in varyant.get('banks', []) if b.get('banka_adi') in uyeler])
    comp, cur = build_composition_payload(ctx, alt_komp) if degisen else ({}, {})
    comp_g = {cid: v.get('group', {}) for cid, v in comp.items()}
    cur_g = {cid: v.get('group', {}) for cid, v in cur.items()}

    ta = (computed.get('bank_data') or {}).get('toplam_aktifler', {}).get(banka, {})
    tarihler = sorted(t for t, v in ta.items() if v is not None)
    meta = {
        'focus_bank': banka,
        'groups': m1,
        'group_order': g1['order'],
        'group_colors': g1.get('colors') or {},
    }
    from .groups import export_grup_adlari
    meta['export_groups'] = export_grup_adlari(varyant)
    if tarihler:
        meta['default_date'] = tarihler[-1]
    return {'meta': meta, 'kaldirilan': kaldirilan, 'group_data': group_data,
            'composition_group': comp_g, 'currency_group': cur_g}
