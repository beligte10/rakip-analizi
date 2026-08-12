# Bağlam Brief — Claude'a Yeni Chat'te Yüklemek İçin

Bu dosya, yeni bir chat başlattığında Claude'un sıfırdan tüm projeyi anlaması için gerekli minimum bağlamı içerir. **Yeni chat'te ilk mesaj olarak bu repo URL'si + bu dosyanın içeriği yeterli.**

---

## Proje Özeti

**KT Strategic Cockpit** — Türk bankacılık sektörü rakip analiz dashboard'u. BDDK kamuya açık kuartelik raporlardan beslenir. 27 banka × 48 dönem × 126 measure üzerinden Snapshot/Trend/Kompozisyon/Export analizleri yapar.

**Sahibi:** Kuveyt Türk Strateji ekibi  
**Statü:** v29 — yapı tam, canlıya alma süreci başlatılıyor

## Mimari (Bir Bakışta)

```
BDDK xlsx → pipeline/ingest → veriler.parquet → pipeline/compute → computed.json → frontend
```

Tek HTML dosya frontend (React, embedded JSON yerine `fetch('/data.json')`), FastAPI backend, parquet+JSON storage, tamamen yerel çalışır (harici hosting bağımlılığı yok).

Detay: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## Measure Sistemi

128 measure tanımlı, 126'sı raw data'dan hesaplanmış halde. Tek doğru kaynak:
- **Formüller:** `pipeline/measures.py` her fonksiyonun docstring'inde DAX-eşdeğer formül var
- **Metadata:** `data/catalog.json` (id, ad, tip, kategori, vb.)
- **İnsan-okunur özet:** `docs/MEASURES.md`

Yapı taşları (Bilanço'dan okunan kalemler), notasyon ve tüm 126 measure listesi `docs/MEASURES.md`'de.

## Banka & Grup Sistemi

27 banka, 5 grup. Banka tipi (`Mevduat` / `Katılım`) `data/catalog.json`'da. Mevduat detayları için banka tipine göre farklı tablo okunur (`Mevduatın Vade Yapısı` vs `Toplanan Fonların Vade Yapısı`). Bu ayrım `pipeline/lookup.py`'da `LookupContext.vadesiz_mevduat()` gibi metodlarda saklı.

5 grup:
1. `Kuveyt Türk` — tek bankalı (KT verisini doğrulamak için)
2. `Mevduat Bankaları`
3. `Rakip Bankalar` — KT'ye en yakın 5 banka
4. `Katılım Bankaları` — tüm katılım bankaları (KT dahil)
5. `KT Hariç Katılım Bankaları`

Grup üyelikleri: `data/catalog.json` → `groups.members`.

## Kritik Tasarım Kararları

1. **Ham veri kalıcıdır.** `data/raw/` altındaki xlsx'ler bir kez yüklendiğinde değişmez. Pipeline her zaman buradan yeniden hesaplama yapabilir. Yeni measure eklemek raw veriye dokunmaz.

2. **Banka tipine göre dual-table lookup.** Mevduat detayları (vadesiz, kıymetli maden, resmi kurumlar) Mevduat ve Katılım bankalarında farklı tablolarda. Katılım kalemlerinde `\xa0` (non-breaking space) var; string match'lerde kritik.

3. **Krediler measure'ı = `Krediler Ve Alacaklar (Toplam)`** (IFRS 9 sonrası), legacy fallback `Krediler`. Pipeline ikisini de dener.

4. **Grup rasyo aggregation = ağırlıklı ortalama** (`Σnumerator / Σdenominator`). Her rasyo için pay/payda formülü `pipeline/groups.py`'da.

5. **Frontend hesaplama yapmaz.** Sadece `data.json`'u render eder. Yeni measure pipeline tarafında eklenir, frontend'e dokunulmaz.

## Bilinen Limitasyonlar

- `tp_spread`, `yp_spread` placeholder — flow rate hesabı henüz yapılmadı (annualization + ortalama bakiye gerekir; faiz akımları Para Birimi='Toplam' raporlandığı için TP/YP ayrımı için sub-tablo lazım: `Kredilerden Alınan Faiz Gelirlerine İlişkin Bilgiler`)
- `serbest_sermaye_ta` formülü basitleştirilmiş — BDDK resmi tanımı daha geniştir (Net Donuk, Cari Vergi, Şerefiye düşülür); PBI ile uyumsuzluk olursa genişletilmeli

## Sürüm & İterasyon Yöntemi

- v29 = mevcut son sürüm (Faz 1 başlangıç noktası)
- Kod değişikliği → sunucuyu yeniden başlat (`python app.py`)
- Ham veri değişikliği → Admin UI'dan upload → otomatik recompute → dashboard yenilenir
- Bug fix iterasyonları canlı sürümde yapılabilir; kritik değişiklikler için lokal `kt_cockpit_v<N>.html` üretip test edilebilir

## Henüz Yapılacaklar (Faz 2-4)

**Faz 2** (sıradaki): Backend + frontend ayırma — `app.py` (FastAPI), v29 frontend'inden embedded JSON'u sökmek, `/data.json` endpoint, `/admin/upload` endpoint.

**Faz 3**: Admin UI — 5. tab olarak dashboard içinde, basic auth korumalı. Coverage paneli, drag-drop upload, "Yeniden Hesapla" butonu.

**Faz 4**: (tamamlandı) — proje tamamen yerel çalışacak şekilde sadeleştirildi, harici hosting bağımlılığı kaldırıldı.

Bunlardan sonra: kapsamlı test (kullanıcı bu chat'te tarif etti), `tp_spread`/`yp_spread` implementasyonu, formül incelikleri (örn. serbest_sermaye genişletmesi).

## Yeni Chat'te Ne Yapmalı

Yeni chat'in ilk mesajına şunlar girilebilir:

> Bu projeyi sürdürelim. Repo: <github-url>. Brief: <CONTEXT.md içeriği>. Şu an Faz 2'deyiz / şu bug'a düştük / şu measure'ı eklemek istiyorum: ...

Claude (yeni chat'teki) `web_fetch` ile repo'yu okuyabilir veya kullanıcıdan ilgili dosyaları görmek için ister.

## Önemli Spot Değerler (v29 baseline)

Bu değerler kullanıcının tahmini doğruluğu için referans noktalarıdır:

| Banka | Tarih | Measure | Değer |
|---|---|---|---|
| Kuveyt Türk | 2025-09-30 | toplam_aktifler | 1.217.286.799.000 TL |
| Kuveyt Türk | 2025-09-30 | krediler | 588.779.601.000 TL |
| Kuveyt Türk | 2025-09-30 | mevduat | 776.817.980.000 TL |
| Kuveyt Türk | 2025-09-30 | toplam_kaynak | 1.042.963.144.000 TL |
| Kuveyt Türk | 2025-09-30 | vadeli_mevduat | 306.056.565.000 TL |
| Kuveyt Türk | 2025-09-30 | kiymetli_maden_mevduati | 242.562.257.000 TL |
| Kuveyt Türk | 2025-09-30 | npl_rasyosu | %2,267 |
| Kuveyt Türk | 2025-09-30 | maliyetli_pasifler_toplam_pasifler | %86,90 |

Pipeline'a değişiklik yapıldığında bu değerler değişmemeli (regression test).
