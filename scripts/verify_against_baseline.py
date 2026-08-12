"""
scripts/verify_against_baseline.py
====================================
SALT-OKUMA doğrulama scripti. Hiçbir dosyayı DEĞİŞTİRMEZ.

data/computed.json'daki (pipeline'ın hesapladığı) değerleri, harici bir
referans dosyasıyla (örn. eski v29 PBI export'u — "Kalem" ve "Rasyo"
sheet'leri olan bir xlsx) karşılaştırır, farkları raporlar.

Kullanım:
    python scripts/verify_against_baseline.py datatable_1.xlsx
    python scripts/verify_against_baseline.py datatable_1.xlsx --banka "Kuveyt Türk"
    python scripts/verify_against_baseline.py datatable_1.xlsx --tolerans 0.01 --out rapor.csv

Eşleştirme mantığı:
- catalog.json'daki her measure'ın 'ad' alanı, referans dosyasındaki
  Kalem/Rasyolar isimleriyle (boşluk normalize edilerek) eşleştirilir.
  Örn. "EURO Cinsi Krediler / YP Krediler" (catalog) ==
       "EURO Cinsi Krediler/ YP Krediler" (referans) -> eşleşir.
- Eşleşmeyen measure'lar raporun sonunda "eşleşmedi" listesinde ayrıca
  gösterilir (karşılaştırılmaz, sessizce atlanmaz).
- Büyüklük tipi measure'lar: computed.json TAM TL, referans MİLYON TL
  varsayılır (× 1e6 ile karşılaştırılır).
- Rasyo tipi measure'lar: computed.json YÜZDE (örn. 3.66), referans
  ORAN (örn. 0.0366) varsayılır (× 100 ile karşılaştırılır).

Grup karşılaştırması (opsiyonel, --gruplar ile açılır):
Referans dosyasındaki KAMU/KATILIM/MEVDUAT/RAKİP/SEKTÖR satırları,
catalog.json'daki grup adlarıyla BİREBİR AYNI ŞEY OLDUĞU GARANTİ DEĞİL —
bu yüzden aşağıdaki GROUP_NAME_MAP varsayımsal bir eşleştirmedir, rapor
bunu açıkça belirtir. KAMU ve SEKTÖR için catalog'da karşılık yok, atlanır.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent

# Referans dosyasındaki grup satırı adı -> catalog.json'daki grup adı.
# KAMU ve SEKTÖR için catalog'da karşılık yok (varsayımsal, doğrulanmamış).
GROUP_NAME_MAP = {
    'MEVDUAT': 'Mevduat Bankaları',
    'KATILIM': 'Katılım Bankaları',
    'RAKİP': 'Rakip Bankalar',
}


def norm(s) -> str:
    """Boşluk/slash varyasyonlarını normalize et: 'a / b', 'a/ b' -> 'a/b'."""
    s = str(s).strip()
    s = re.sub(r'\s*/\s*', '/', s)
    s = re.sub(r'\s+', ' ', s)
    return s.lower()


def load_catalog(data_dir: Path) -> dict:
    with open(data_dir / 'catalog.json', encoding='utf-8') as f:
        return json.load(f)


def load_computed(data_dir: Path) -> dict:
    with open(data_dir / 'computed.json', encoding='utf-8') as f:
        return json.load(f)


def load_reference(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    kalem = pd.read_excel(path, sheet_name='Kalem', header=0, engine='openpyxl')
    rasyo = pd.read_excel(path, sheet_name='Rasyo', header=0, engine='openpyxl')
    kalem['Tarih'] = pd.to_datetime(kalem['Tarih']).dt.strftime('%Y-%m-%d')
    rasyo['Tarih'] = pd.to_datetime(rasyo['Tarih']).dt.strftime('%Y-%m-%d')
    return kalem, rasyo


def build_measure_index(measures: list[dict]) -> dict:
    """norm(ad) -> measure dict. Aynı normalize isme sahip iki measure varsa ilkini tutar."""
    idx = {}
    for m in measures:
        key = norm(m['ad'])
        idx.setdefault(key, m)
    return idx


def get_scale(tip: str, birim: str) -> float | None:
    """
    (tip, birim) -> referans değeri pipeline değeriyle aynı ölçeğe getiren çarpan.
    None dönerse: bu birim için ölçek varsayımı GÜVENİLİR DEĞİL, karşılaştırma
    yapılmaz (yanlış OK/FARK üretmektense atlamak tercih edilir).
    """
    if tip == 'buyukluk':
        if birim == 'TL':
            return 1e6      # referans milyon TL varsayılır
        if birim == 'adet':
            return 1.0      # sayım — ölçek yok
        return None
    # tip == 'rasyo'
    if birim == '%':
        return 100.0        # referans oran (0-1) varsayılır
    if birim in ('adet', 'kat'):
        return 1.0
    # 'bin_TL' gibi belirsiz birimler: referansın hangi ölçekte olduğu
    # doğrulanmadı — otomatik karşılaştırma yapma.
    return None


def compare(
    computed: dict,
    catalog: dict,
    kalem_df: pd.DataFrame,
    rasyo_df: pd.DataFrame,
    entity_col_values: set,
    banka_filter: str | None,
    tolerans: float,
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Returns (satirlar, eslesmeyen_measure_listesi, belirsiz_olcek_listesi)
    satirlar: her biri {measure_id, ad, entity, tarih, pipeline_deger,
                        referans_deger, fark_yuzde, durum}
    """
    measures = catalog['measures']
    bank_data = computed.get('bank_data', {})

    # Referans indeksleri: norm(kalem/rasyo adi) -> gercek isim
    kalem_names = {norm(k): k for k in kalem_df['Kalem'].unique()}
    rasyo_names = {norm(r): r for r in rasyo_df['Rasyolar'].unique()}

    # Hızlı lookup için referans DataFrame'lerini indeksle
    kalem_idx = kalem_df.set_index(['BankName', 'Tarih', 'Kalem'])['KalemlerSlicer2']
    rasyo_idx = rasyo_df.set_index(['BankName', 'Tarih', 'Rasyolar'])['RasyolarToplu3']

    satirlar = []
    eslesmeyen = []
    belirsiz = []

    for m in measures:
        mid = m['id']
        ad = m['ad']
        tip = m.get('tip', 'rasyo')
        birim = m.get('birim', '')
        key = norm(ad)

        if tip == 'buyukluk':
            if key not in kalem_names:
                eslesmeyen.append({'id': mid, 'ad': ad, 'tip': tip})
                continue
            ref_sheet_idx = kalem_idx
            ref_col_name = kalem_names[key]
        else:
            if key not in rasyo_names:
                eslesmeyen.append({'id': mid, 'ad': ad, 'tip': tip})
                continue
            ref_sheet_idx = rasyo_idx
            ref_col_name = rasyo_names[key]

        scale = get_scale(tip, birim)
        if scale is None:
            belirsiz.append({'id': mid, 'ad': ad, 'tip': tip, 'birim': birim})
            continue

        mid_data = bank_data.get(mid, {})
        for banka, series in mid_data.items():
            if banka not in entity_col_values:
                continue  # grup/pseudo satırlar burada değil, gerçek bankalar
            if banka_filter and banka != banka_filter:
                continue
            for tarih, pipeline_deger in series.items():
                if pipeline_deger is None:
                    continue
                try:
                    ref_raw = ref_sheet_idx.loc[(banka, tarih, ref_col_name)]
                except KeyError:
                    continue  # referansta bu banka/tarih için veri yok
                if isinstance(ref_raw, pd.Series):
                    ref_raw = ref_raw.iloc[0]
                if pd.isna(ref_raw):
                    continue

                referans_deger = float(ref_raw) * scale
                if referans_deger == 0:
                    fark_yuzde = None
                    durum = 'REFERANS=0'
                else:
                    fark_yuzde = abs(pipeline_deger - referans_deger) / abs(referans_deger)
                    durum = 'OK' if fark_yuzde <= tolerans else 'FARK'

                satirlar.append({
                    'measure_id': mid,
                    'ad': ad,
                    'tip': tip,
                    'entity': banka,
                    'tarih': tarih,
                    'pipeline_deger': pipeline_deger,
                    'referans_deger': referans_deger,
                    'fark_yuzde': fark_yuzde,
                    'durum': durum,
                })

    return satirlar, eslesmeyen, belirsiz


def compare_groups(
    computed: dict,
    catalog: dict,
    kalem_df: pd.DataFrame,
    rasyo_df: pd.DataFrame,
    tolerans: float,
) -> list[dict]:
    """Opsiyonel: catalog.json grupları ile referansın KAMU/KATILIM/MEVDUAT/RAKİP/SEKTÖR
    pseudo-satırlarını karşılaştırır. GROUP_NAME_MAP varsayımsaldır — bkz. modül docstring."""
    measures = catalog['measures']
    group_data = computed.get('group_data', {})

    kalem_names = {norm(k): k for k in kalem_df['Kalem'].unique()}
    rasyo_names = {norm(r): r for r in rasyo_df['Rasyolar'].unique()}
    kalem_idx = kalem_df.set_index(['BankName', 'Tarih', 'Kalem'])['KalemlerSlicer2']
    rasyo_idx = rasyo_df.set_index(['BankName', 'Tarih', 'Rasyolar'])['RasyolarToplu3']

    satirlar = []
    for m in measures:
        mid, ad, tip = m['id'], m['ad'], m.get('tip', 'rasyo')
        key = norm(ad)
        if tip == 'buyukluk':
            if key not in kalem_names:
                continue
            ref_idx, ref_col, scale = kalem_idx, kalem_names[key], 1e6
        else:
            if key not in rasyo_names:
                continue
            ref_idx, ref_col, scale = rasyo_idx, rasyo_names[key], 100.0

        mid_groups = group_data.get(mid, {})
        for ref_group_name, catalog_group_name in GROUP_NAME_MAP.items():
            gseries = mid_groups.get(catalog_group_name, {})
            for tarih, vobj in gseries.items():
                pipeline_deger = vobj.get('value') if isinstance(vobj, dict) else vobj
                if pipeline_deger is None:
                    continue
                try:
                    ref_raw = ref_idx.loc[(ref_group_name, tarih, ref_col)]
                except KeyError:
                    continue
                if isinstance(ref_raw, pd.Series):
                    ref_raw = ref_raw.iloc[0]
                if pd.isna(ref_raw):
                    continue
                referans_deger = float(ref_raw) * scale
                if referans_deger == 0:
                    fark_yuzde, durum = None, 'REFERANS=0'
                else:
                    fark_yuzde = abs(pipeline_deger - referans_deger) / abs(referans_deger)
                    durum = 'OK' if fark_yuzde <= tolerans else 'FARK'
                satirlar.append({
                    'measure_id': mid, 'ad': ad, 'tip': tip,
                    'entity': f'{catalog_group_name} (ref:{ref_group_name})',
                    'tarih': tarih,
                    'pipeline_deger': pipeline_deger,
                    'referans_deger': referans_deger,
                    'fark_yuzde': fark_yuzde,
                    'durum': durum,
                })
    return satirlar


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('reference_xlsx', type=Path, help='Referans xlsx (Kalem + Rasyo sheet\'leri olan)')
    ap.add_argument('--data-dir', type=Path, default=REPO_ROOT / 'data')
    ap.add_argument('--banka', help='Sadece tek banka için karşılaştır (örn. "Kuveyt Türk")')
    ap.add_argument('--tolerans', type=float, default=0.01, help='Kabul edilebilir bağıl fark (varsayılan %%1)')
    ap.add_argument('--gruplar', action='store_true', help='Banka grubu karşılaştırmasını da çalıştır (varsayımsal eşleştirme)')
    ap.add_argument('--out', type=Path, help='Detaylı sonucu CSV olarak kaydet')
    args = ap.parse_args()

    if not args.reference_xlsx.exists():
        print(f"❌ {args.reference_xlsx} bulunamadı"); sys.exit(1)

    catalog = load_catalog(args.data_dir)
    computed = load_computed(args.data_dir)
    kalem_df, rasyo_df = load_reference(args.reference_xlsx)

    real_banks = {b['banka_adi'] for b in catalog['banks']}

    satirlar, eslesmeyen, belirsiz = compare(
        computed, catalog, kalem_df, rasyo_df, real_banks, args.banka, args.tolerans,
    )

    if not satirlar:
        print("⚠ Karşılaştırılabilir hiçbir (measure, banka, tarih) hücresi bulunamadı.")
        sys.exit(0)

    df = pd.DataFrame(satirlar)

    print(f"\n{'='*70}\nBANKA BAZLI KARŞILAŞTIRMA — {len(df)} hücre karşılaştırıldı\n{'='*70}")
    print(f"Kullanılan measure sayısı: {df['measure_id'].nunique()} / {len(catalog['measures'])}")
    print(f"Eşleşmeyen (isim bulunamayan) measure sayısı: {len(eslesmeyen)}")
    print(f"Ölçeği belirsiz (karşılaştırılmayan) measure sayısı: {len(belirsiz)}")

    ok = (df['durum'] == 'OK').sum()
    fark = (df['durum'] == 'FARK').sum()
    refsifir = (df['durum'] == 'REFERANS=0').sum()
    print(f"\n  ✓ OK          : {ok}  ({ok/len(df)*100:.1f}%)")
    print(f"  ✗ FARK (>%{args.tolerans*100:.1f}) : {fark}  ({fark/len(df)*100:.1f}%)")
    print(f"  · REFERANS=0  : {refsifir}")

    if fark:
        print(f"\n--- En büyük 15 fark ---")
        worst = df[df['durum'] == 'FARK'].copy()
        worst = worst.sort_values('fark_yuzde', ascending=False).head(15)
        for _, r in worst.iterrows():
            print(f"  {r['measure_id']:<35} {r['entity']:<20} {r['tarih']}  "
                  f"pipeline={r['pipeline_deger']:.4f}  referans={r['referans_deger']:.4f}  "
                  f"fark=%{r['fark_yuzde']*100:.1f}")

    # measure bazında özet: hangi measure'larda kaç FARK var
    print(f"\n--- Measure bazında FARK özeti (en çok farkı olan ilk 15) ---")
    measure_summary = (
        df.groupby(['measure_id', 'ad'])['durum']
        .apply(lambda s: (s == 'FARK').sum())
        .sort_values(ascending=False)
        .head(15)
    )
    for (mid, ad), n_fark in measure_summary.items():
        if n_fark > 0:
            total = len(df[df['measure_id'] == mid])
            print(f"  {mid:<35} {ad:<50} {n_fark}/{total} hücre farklı")

    if eslesmeyen:
        print(f"\n--- Eşleşmeyen measure'lar (referansta isim bulunamadı, karşılaştırılmadı) ---")
        for e in eslesmeyen:
            print(f"  {e['id']:<35} {e['ad']}")

    if belirsiz:
        print(f"\n--- Ölçeği belirsiz measure'lar (birim='bin_TL' vb. — otomatik karşılaştırılmadı, elle kontrol gerekir) ---")
        for e in belirsiz:
            print(f"  {e['id']:<35} {e['ad']:<55} birim={e['birim']}")

    if args.gruplar:
        print(f"\n{'='*70}\nGRUP BAZLI KARŞILAŞTIRMA (varsayımsal eşleştirme — dikkatli okuyun)\n{'='*70}")
        print(f"Eşleştirme: {GROUP_NAME_MAP}")
        print("NOT: Referanstaki KAMU ve SEKTÖR için catalog.json'da karşılık yok, atlandı.\n")
        grup_satirlar = compare_groups(computed, catalog, kalem_df, rasyo_df, args.tolerans)
        if grup_satirlar:
            gdf = pd.DataFrame(grup_satirlar)
            g_ok = (gdf['durum'] == 'OK').sum()
            g_fark = (gdf['durum'] == 'FARK').sum()
            print(f"  {len(gdf)} hücre karşılaştırıldı — ✓ OK: {g_ok}  ✗ FARK: {g_fark}")
            if g_fark:
                print(f"\n  En büyük farklar:")
                gworst = gdf[gdf['durum'] == 'FARK'].sort_values('fark_yuzde', ascending=False).head(10)
                for _, r in gworst.iterrows():
                    print(f"    {r['measure_id']:<35} {r['entity']:<35} {r['tarih']}  "
                          f"pipeline={r['pipeline_deger']:.4f}  referans={r['referans_deger']:.4f}  "
                          f"fark=%{r['fark_yuzde']*100:.1f}")
            df = pd.concat([df, gdf], ignore_index=True)
        else:
            print("  Karşılaştırılabilir grup hücresi bulunamadı.")

    if args.out:
        df.to_csv(args.out, index=False, encoding='utf-8-sig')
        print(f"\n💾 Detaylı rapor kaydedildi: {args.out}")


if __name__ == '__main__':
    main()
