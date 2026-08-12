# Mimari

## Tasarım Prensipleri

1. **Ham veri kalıcıdır, dokunulmaz.** `data/raw/` altındaki xlsx'ler bir kez yüklendiğinde değişmez. Pipeline her zaman buradan yeniden hesaplama yapabilir.

2. **Tek doğru kaynak: `catalog.json`.** Measure ve banka metadata'sı (ad, tip, kategori, grup üyeliği vb.) sadece burada tanımlıdır. Frontend ve pipeline ikisi de buradan okur.

3. **Pipeline idempotent ve fail-soft.** Bir dosya bozuksa veya bir kalem eksikse pipeline durmaz; o hücre `null` döner, geri kalan hesap eder.

4. **Frontend sadece sunum.** Hesaplama yok, sadece `data.json` okuyup render eder. Bu sayede backend'deki formül değişikliği frontend'e dokunmadan canlıya çıkar.

5. **Tek HTML dosya frontend.** Hostingsiz ortamda da çalışır, debug kolay, deploy kolay.

## Veri Akışı

```
BDDK xlsx (1 banka × 1 dönem)
        ↓ pipeline/ingest.py
data/raw/<banka>/<dosya>.xlsx
        ↓ pipeline/ingest.py
data/veriler.parquet (long-format: tarih × banka × kalem × para_birimi → tutar)
        ↓ pipeline/measures.py
computed.json (banka × tarih × measure → değer + grup aggregations)
        ↓ FastAPI /data.json endpoint
Frontend (React)
```

## Storage Şeması

### `data/raw/<banka>/<dosya>.xlsx`

Yüklenen ham xlsx'ler. BDDK formatında, hiç dokunulmaz. Klasör adı banka display name (Türkçe karakter dahil). Dosya adı `<Banka> - DD.MM.YYYY.xlsx` formatında.

### `data/veriler.parquet`

Tüm xlsx'lerin konsolide long-format hali. Sütunlar:

| Sütun | Tip | Açıklama |
|---|---|---|
| `Tarih` | datetime64 | Dönem sonu (Q-end) |
| `Banka Adı` | category | Display name (örn. "Kuveyt Türk") |
| `Banka Türü` | category | "Mevduat" \| "Katılım" |
| `Tablo Türü` | category | "Ana Tablo" \| ... |
| `Tablo Adı` | category | "Bilanço", "Gelir Tablosu", "Mevduatın Vade Yapısı..." |
| `Kalem Adı` | category | BDDK kalem ismi (orijinal Türkçe, `\xa0` dahil) |
| `Para Birimi` | category | "Toplam" \| "TP" \| "YP" |
| `Tutar` | float64 | TL |

Yaklaşık 2.6M satır, parquet+zstd ile ~8-10 MB.

### `data/computed.json`

Dashboard payload. v29'un embedded JSON yapısıyla aynı:

```json
{
  "meta": {
    "banks": [...],
    "groups": {...},
    "group_order": [...],
    "dates": ["2013-12-31", ..., "2025-09-30"],
    "available_measures": [...],
    "compositions": {...},
    ...
  },
  "catalog": [
    {"id": "toplam_aktifler", "ad": "Toplam Aktifler", "tip": "buyukluk", ...}
  ],
  "bank_data": {
    "toplam_aktifler": {
      "Kuveyt Türk": {"2025-09-30": 1217286799000.0, ...}
    }
  },
  "group_data": {...},
  "composition_data": {...},
  "currency_data": {...}
}
```

Dosya boyutu ~6-8 MB. Ham parquet'ten her recompute'ta yeniden üretilir.

### `data/catalog.json`

İki bölümü var: measure tanımları ve banka tanımları.

```json
{
  "banks": [
    {
      "banka_adi": "Kuveyt Türk",
      "tur": "Katılım",
      "rakip": false,
      "dijital_only": false,
      "groups": ["Kuveyt Türk", "Katılım Bankaları"]
    },
    ...
  ],
  "groups": {
    "order": ["Kuveyt Türk", "Mevduat Bankaları", "Rakip Bankalar",
              "Katılım Bankaları", "KT Hariç Katılım Bankaları"],
    "members": {
      "Kuveyt Türk": ["Kuveyt Türk"],
      "Katılım Bankaları": [...],
      ...
    },
    "colors": {...}
  },
  "measures": [
    {
      "id": "toplam_aktifler",
      "ad": "Toplam Aktifler",
      "tip": "buyukluk",
      "akim_stok": "stok",
      "birim": "TL",
      "kategori": "Bilanço",
      "alt_kategori": "Aktifler",
      "pazar_payi": true,
      "sort_direction": "asc"
    },
    ...
  ],
  "compositions": {
    "aktif": {
      "ad": "Aktif Kompozisyonu",
      "kategori": "Bilanço",
      "components": [
        {"id": "nakit", "ad": "Nakit ve Nakit Benzerleri", "color": "#..."},
        ...
      ]
    },
    ...
  }
}
```

## Pipeline

### `ingest.py`

**Görev:** xlsx → parquet  
**Giriş:** `data/raw/<banka>/<dosya>.xlsx` (bir veya daha fazla)  
**Çıkış:** `data/veriler.parquet` (yenilenmiş)

İki mod:
- **Full rebuild:** `python pipeline/ingest.py --full` — tüm raw klasörünü tarar
- **Incremental:** `ingest_files([path1, path2, ...])` — sadece verilen dosyaları parquet'e ekler

Validation:
- Dosya adından banka & tarih çıkarılır (`<Banka> - DD.MM.YYYY.xlsx`)
- Banka adı catalog'ta var mı (yoksa hata, "yeni banka eklemek için ..." mesajı)
- Dosya yapısı doğru mu (header satır 13'te, beklenen kolonlar var)
- Tarih beklenen Q-end mi (3/31, 6/30, 9/30, 12/31)

### `measures.py`

**Görev:** parquet → computed.json  
**Giriş:** `data/veriler.parquet`  
**Çıkış:** `data/computed.json`

Yapı:
```python
MEASURE_FUNCS = {
    'toplam_aktifler': m_toplam_aktifler,
    'krediler': m_krediler,
    ...
    # her measure için bir fonksiyon
}

def m_toplam_aktifler(b, t):
    return get_bilanco(b, t, 'Toplam Aktifler')
```

Her fonksiyon `(banka, tarih) → float | None` imzasında. Pipeline tüm `(measure, banka, tarih)` kombinasyonları için fonksiyonu çağırır, sonucu `bank_data`'ya yazar.

### `groups.py`

**Görev:** Banka değerlerinden grup değerleri.

Toplama mantığı measure tipine göre:
- **Büyüklük** (TL): `sum`
- **Rasyo:** Ağırlıklı ortalama (`Σnumerator / Σdenominator`). Bu nedenle her rasyo için `num_den_for_ratio()` fonksiyonu da tanımlı olmalı.
- **Akım rasyolar (npl_formasyonu vb.):** Basit ortalama (TBD — hangi BDDK formülü uygulanacak)

## Güvenlik

- **Public okuma, korumalı yazma.** `/data.json` ve frontend public. `/admin/*` endpoint'leri HTTP basic auth.
- **Dosya yükleme validation:** Sadece `.xlsx`, dosya adı regex'ine uyan, banka catalog'ta var olan, beklenen yapıda olan dosyalar kabul edilir.
- **Sınır:** Tek upload max 5 MB (BDDK xlsx'leri tipik 200 KB).

## Çalıştırma

Tamamen yerel: `python app.py` (veya `docker build && docker run`). Harici bir hosting servisine bağımlılık yok — bkz. kök [`README.md`](../README.md).

## Versiyon Yönetimi

Tüm değişiklikler git üzerinde. Konvansiyonlar:
- `feat(measure): ...` — yeni measure veya formül
- `feat(bank): ...` — yeni banka veya grup
- `fix(...): ...` — bug fix
- `docs(...): ...` — dökümantasyon
- `refactor(...): ...` — kod iyileştirme

`docs/CHANGELOG.md` her release'de elle güncellenir (otomatik release notes alternatifi sonra).

## Performans

- **Pipeline süresi:** Tam recompute ~30-60 sn (1 CPU, 2.6M raw satır)
- **API response:** `/data.json` ~6-8 MB; ilk yüklemede 1-3 sn (compress + transfer)
- **Frontend:** İlk render ~2 sn (JSON parse + React mount)
- **Bellek:** Backend ~200-400 MB peak (pandas), frontend ~100 MB (browser)

Ortalama bir geliştirici makinesi (4+ GB RAM, 2+ çekirdek) bu yük için fazlasıyla yeterli.
