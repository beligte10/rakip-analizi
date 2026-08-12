# Sistemi Genişletme Rehberi

Bu sistem değişmeyi kolaylaştıracak şekilde tasarlandı. Aşağıda her senaryo için adım adım talimatlar var.

## 1. Mevcut Yapı Taşlarından Yeni Rasyo Ekleme

**Örnek:** "Tüketici Kredileri / Mevduat" diye yeni bir measure.

**Adım 1 — `pipeline/measures.py`:** Yeni fonksiyon ekle.

```python
def m_tuketici_mevduat(ctx, b, t, computed=None):
    """
    DAX: M[tuketici_kredileri] / M[mevduat] × 100
    Type: rasyo, %, stok
    """
    if computed is None:
        return None
    tk = computed.get('tuketici_kredileri', {}).get(b, {}).get(t)
    mv = computed.get('mevduat', {}).get(b, {}).get(t)
    return safe_ratio(tk, mv)
```

**Adım 2 — `MEASURE_FUNCS` registry'sine ekle:**

```python
MEASURE_FUNCS = {
    ...,
    'tuketici_mevduat': m_tuketici_mevduat,
}
COMPUTED_DEPENDENT.add('tuketici_mevduat')  # computed alıyor
```

**Adım 3 — `data/catalog.json`:** measures listesine entry ekle.

```json
{
  "id": "tuketici_mevduat",
  "ad": "Tüketici Kredileri / Mevduat",
  "tip": "rasyo",
  "akim_stok": "stok",
  "birim": "%",
  "kategori": "Bilanço",
  "alt_kategori": "Aktifler",
  "pazar_payi": false,
  "sort_direction": "asc"
}
```

**Adım 4 — Grup ağırlıklı ortalama için `pipeline/groups.py`:**

```python
def _numden_tuketici_mevduat(ctx, b, t):
    # Gerçek yapı taşları lazım; computed measure değil raw'dan
    tk = ctx.bilanco(b, t, 'Tüketici Kredileri ve Bireysel Kredi Kartları')
      # NOT: bu kalem `Tüketici Kredileri, Bireysel Kredi Kartları, ...` tablosundan
      # gerçek raw kalem adı bulunmalı; örnek için varsayım
    mv = ctx.bilanco(b, t, 'Mevduat')
    return tk, mv

RATIO_NUM_DEN['tuketici_mevduat'] = _numden_tuketici_mevduat
```

**Adım 5 — Recompute:**

```bash
python scripts/recompute.py
```

**Adım 6 — `docs/MEASURES.md`'yi güncelle** (manuel; otomatik jeneratör Faz 2'de).

**Adım 7 — Commit & push:**

```bash
git add pipeline/measures.py pipeline/groups.py data/catalog.json docs/MEASURES.md
git commit -m "feat(measure): add tuketici_mevduat ratio"
```

Sunucuyu yeniden başlatın (`python app.py`) veya admin panelinden "Yeniden Hesapla" tetikleyerek dashboard'u güncelleyin.

---

## 2. Ham Bilanço Kalemi → Yeni Büyüklük

**Örnek:** "Bağlı Ortaklıklar (Net)" diye yeni bir büyüklük measure.

**Adım 1 — `pipeline/measures.py`:**

```python
def m_bagli_ortakliklar(ctx, b, t):
    """
    DAX: B[Bağlı Ortaklıklar (Net)]
    Type: büyüklük, TL, stok
    """
    return ctx.bilanco(b, t, 'Bağlı Ortaklıklar (Net)')

MEASURE_FUNCS['bagli_ortakliklar'] = m_bagli_ortakliklar
```

**Adım 2 — `catalog.json`'a entry, sonra recompute.**

Ham veri yeniden yüklenmiyor — `data/raw/` zaten dolu, pipeline yeniden çalışınca yeni measure tüm geçmiş için doldurulur (48 dönem × 27 banka).

---

## 3. Tamamen Yeni Bir BDDK Kalemi

BDDK formatında yeni satır geldi (örn. 2026'da yeni bir hesap kalemi).

**Eski tarihler için** raw veride bu kalem yok → `ctx.bilanco(...)` 0 döner. Pipeline fail-soft, sorun olmaz.

**Yeni tarihler için** raw veride var → measure değer döner.

Coverage paneli (Admin tab) bu durumu gösterecek: "Bu measure 2025-Q4'ten itibaren mevcut".

---

## 4. Yeni Banka Ekleme

**Örnek:** "Yeni Banka A.Ş." adında yeni bir katılım bankası.

**Adım 1 — `data/catalog.json`:** banks dizisine entry ekle.

```json
{
  "banka_adi": "Yeni Banka A.Ş.",
  "tur": "Katılım",
  "rakip": false,
  "dijital_only": false,
  "groups": ["Katılım Bankaları", "KT Hariç Katılım Bankaları"]
}
```

**Adım 2 — `groups.members` altındaki ilgili gruplara banka adını ekle:**

```json
"Katılım Bankaları": [..., "Yeni Banka A.Ş."],
"KT Hariç Katılım Bankaları": [..., "Yeni Banka A.Ş."]
```

**Adım 3 — Admin panelinden xlsx upload.**

Banka için her dönemin xlsx dosyasını yükle (`Yeni Banka A.Ş. - DD.MM.YYYY.xlsx` formatında). Hiç xlsx yoksa banka dropdown'larda görünür ama tüm hücreler boş olur.

**Adım 4 — Recompute.**

Otomatik tetiklenir (her upload sonrası), veya manuel `scripts/recompute.py`.

**Önemli:** Yeni banka grup ortalamalarını değiştirir. Örn. KT Hariç Katılım grubu için ROAA hesabı yeniden ağırlıklı ortalama alınır.

---

## 5. Yeni Grup Ekleme

**Örnek:** "Devlet Bankaları" grubu.

`catalog.json` → `groups` altında:

```json
"order": [..., "Devlet Bankaları"],
"members": {
  ...,
  "Devlet Bankaları": ["Ziraat Bankası", "Halk Bank", "Vakıfbank",
                       "Ziraat Katılım", "Vakıf Katılım", "Emlak Katılım"]
},
"colors": {
  ...,
  "Devlet Bankaları": "#7c3aed"
}
```

Her bankanın `groups` field'ına yeni grubu ekle:

```json
{"banka_adi": "Ziraat Bankası", ..., "groups": [..., "Devlet Bankaları"]}
```

Recompute → yeni grup tüm measure'larda otomatik görünür. Pipeline dinamik (üyeleri okur, agregasyon yapar).

---

## 6. Kategori / Alt-Kategori Değişikliği

Bir measure'ı "Bilanço/Aktifler"den "Bilanço/Pasifler"e taşı:

`catalog.json` → ilgili measure entry'sinde `alt_kategori` field'ını değiştir.

Veri etkilenmez. Frontend dropdown'ında measure başka grupta görünür. Recompute'a bile gerek yok (frontend `/data.json` cache'i bittiğinde yenilenir).

---

## 7. Composition Tanımı Değişikliği

Aktif Kompozisyonu'nda yeni bir component eklemek istiyorsan:

`catalog.json` → `compositions.aktif.components` dizisine yeni entry ekle.

Composition_data hesabı pipeline'da yapılıyor (Faz 2'de tam implementasyon); şimdilik manuel mapping'e bağlı.

---

## Test Süreci

Her değişiklik sonrası:

1. **Sanity check:** Bilinen değer doğru hesaplanıyor mu?
   ```python
   from pipeline.lookup import LookupContext
   from pipeline.measures import compute_measure
   ctx = LookupContext.from_parquet('data/veriler.parquet')
   v = compute_measure('toplam_aktifler', ctx, 'Kuveyt Türk', '2025-09-30')
   assert abs(v - 1_217_286_799_000) < 1
   ```

2. **Coverage:** Yeni measure tüm bankalarda hesaplanmış mı?
   - Admin panelinde "Coverage" gösterimi (Faz 3'te)
   - Veya: `python -c "import json; d=json.load(open('data/computed.json')); print(len(d['bank_data']['<measure_id>']))"`

3. **Grup tutarlılığı:** "Kuveyt Türk" tek-bankalı grubu için bank_data == group_data invariantı bozulmuyor mu?

4. **Frontend:** Dashboard'da measure dropdown'da görünüyor mu, snapshot/trend/export modlarında düzgün render ediliyor mu?

---

## Geri Alma

Her değişiklik git commit. Bug çıkarsa:

```bash
git revert <commit-hash>
```

Sunucuyu yeniden başlatın → eski versiyona dönülür. Yüklü ham veri etkilenmez.
