# Changelog

Sürüm geçmişi. Her commit'in özetini barındırır.

## Faz 1.5 — 2025-05-02 — Raw'dan Tam Hesaplama Pipeline'ı

**Hedef:** v29'daki tüm 128 measure'ı raw BDDK xlsx'lerinden Python ile yeniden üretmek; yalnızca raw'da olmayan/PBI özel kalemleri baseline'dan kopyalamak. Faz 2 admin upload akışı için zorunlu altyapı.

**Sonuçlar:**
- KT 2025-Q3 için **102/102 raw measure** v29 baseline ile birebir eşleşti (rel < 1e-3).
- 27 banka × 48 çeyrek × 128 measure full pipeline'da **%91.8 exact match** (rel < 0.1%).
- Sapan 8.4% — büyük çoğunluğu IFRS 9 öncesi (≤2017) eski tablo yapısı + grup aggregate'lerin PBI özel ağırlıklı ortalama formülleri.
- Tam pipeline (compute_all + group aggregate) **43.1 saniye** (27 banka × 48 çeyrek × 128 measure).

**Mimari:**
- `MEASURE_FUNCS` (104) — raw verilerden hesaplanan formüller. Pipeline override eder.
- `BASELINE_PASSTHROUGH` (24) — raw'dan tam türetilemeyen kalemler, `base_data`'dan kopyalanır.
- `compute_all(ctx, base_data, catalog, ...)` orkestratörü her iki tarafı birleştirir, ardından `compute_group_aggregates` çağırır.
- 2 placeholder (`tp_spread`, `yp_spread`) — gelecek faza ertelendi.

**Kritik bug fix — NBSP encoding:**
BDDK ham xlsx'lerinde bazı kalem ve tablo adları normal boşluk yerine non-breaking space (\xa0) içeriyor (örn. `İhracat Kredileri,\xa0Standart Nitelikli Krediler, Toplam`). `LookupContext.__init__` artık tüm metin kolonlarında NBSP → normal boşluk normalizasyonu yapıyor. Bu düzeltme öncesi `dis_ticaret_toplam` raw hesabı 0.49% çıkıyordu (gerçek 14.95%); sonrası birebir eşleşiyor.

**Formül keşifleri (KT 2025-Q3 verifikasyonu):**
- `konut_kredileri = 21.490B` = (Tüketici, Personel) × (TP, Dövize Endeksli, YP) "Konut Kredisi" toplamı (Tüketici Kredileri Detay tablosu)
- `bireysel_kredi_kartlari = 31.528B` = (Bireysel KK, Personel KK) × (TP, YP) "Toplam"
- `tuzel_krediler = 528.350B` = krediler − tuketici_kredileri
- `grup_2_krediler = 41.306B` = "Toplam Yakın İzleme" + "Ödeme Planı Uzatılan"
- `donuk_alacaklar_satis_terkin_oncesi = 17.212B` = Donuk + |Aktiften Silinen|
- `npl_rasyosu_satis_terkin_oncesi`: pay = Donuk + |Silinen|, payda = Krediler + |Silinen|
- `dis_ticaret_toplam`: İhracat + İthalat üzerinden (Standart + Yakın İzleme + Ödeme Planı)
- `mali_kesim_toplam`: "Mali Kesime Verilen Krediler,  Standart Nitelikli Krediler, Toplam" — kalem adında çift boşluk var, **NBSP fix sayesinde** çalışıyor
- `menkul_kiymetler_ta`: Devlet + Diğer Menkul + Sermaye + Türev FV + Diğer FV (NOT İtfa Edilmiş)
- `tp_pasifler_oz_haric`: pay = TP Pasifler (özkaynak DAHİL); payda = Toplam Pasifler − Özkaynak
- `ROAA TTM`: TTM(t) = YtD(t) + (FY_prev − YtD(yoy(t))); Avg Balance = (stock(t) + stock(t−4q)) / 2
- Tüm Gelir Tablosu rasyoları (komisyon, faiz_gid_gel, personel_net_kar, reklam_net_kar, net_ucret_op) **TTM/TTM** kullanıyor (YtD değil)
- `konut_tp_pasifler`: payda = TP Pasifler − TP Özkaynak

**BASELINE_PASSTHROUGH gerekçeleri (24 kalem):**
| Kategori | Measure'lar | Sebep |
|----------|-------------|-------|
| Sermaye Yeterliliği | syr, cekirdek_syr | BDDK ana raporlarında yok, ayrı raporlar |
| RWA-bağımlı (5) | rorwa, ort_rav_ort_ozkaynak, net_faiz_ort_rav, grup_2_krediler_cekirdek_sermaye, faiz_getirili_ozkaynak | Risk Ağırlıklı Varlıklar raporlanmıyor |
| YP detay (3) | usd_yp_krediler, euro_yp_krediler, yp_net_pozisyon_ozkaynak | Kur Riski tablosu kompleks, PBI özel formül |
| PBI düzeltmeli (2) | maliyet_gelir_duzeltilmis, nim_duzeltilmis | PBI'nın "düzeltilmiş" tanımı opaque |
| Gayrinakdi (2) | gayrinakdi_krediler, gayrinakdi_komisyon_gayrinakdi | v29 PBI tanımı raw'dan farklı (152.6B vs 52.6B) |
| PBI akım (4) | npl_formasyonu, spread, donuk_intikal/tahsilat | Raw delta ile %5+ sapma |
| IEA tanım (6) | nim, nim_bzk, faiz_getirili_ta/maliyetli/aktif_getirisi, maliyet_gelir | IEA/op gelir tanımı PBI'a özgü, %1-5 sapma |

**Pipeline modülleri:**
- `pipeline/lookup.py` — NBSP normalize, faaliyet_gid_detay tablosu indeksi, katılım helper'ları (vadesiz_mevduat, kiymetli_maden, resmi_kurumlar, tuzel_mevduat), TTM/avg balance helper'ları
- `pipeline/measures.py` — 104 raw fonksiyon + BASELINE_PASSTHROUGH set
- `pipeline/groups.py` — RATIO_NUM_DEN sözlüğü (66 measure pay/payda formülü) + compute_group_aggregates
- `pipeline/compute.py` — compute_all orkestratörü; catalog dict/list ikisini de kabul eder
- `scripts/recompute.py` — yeni compute_all API'sine uyumlu CLI

**Sonraki adım:** Faz 2 — frontend'den embedded JSON'u sökmek, FastAPI app.py + /admin/upload endpoint, repo'yu git'e koymak.

---

## v29 — 2025-05-01 — Yeni 21 Measure Aktivasyonu

**Değişiklik:** Pasifler kategorisindeki 20 + Aktifler'deki 1 measure raw data'dan hesaplanarak aktive edildi. Toplam available measure 105 → 126.

**Yeni measure'lar (21):**
- 4 büyüklük: `vadeli_mevduat`, `toplam_kaynak`, `kiymetli_maden_mevduati`, `resmi_kurumlar_mevduat`
- 17 rasyo: `npl_formasyonu`, `alinan_krediler_iemk_toplam_kaynak`, `tp_alinan_toplam_alinan`, `tuzel_krediler_tuzel_mevduat`, `krediler_altindisi_mevduat`, `krediler_toplam_kaynak`, `tp_krediler_tp_kaynak`, `yp_krediler_yp_altindisi_kaynak`, `vadesiz_mevduat_toplam_kaynak`, `tp_mevduat_altindisi_mevduat`, `tp_kaynak_toplam_kaynak`, `toplam_kaynak_toplam_pasifler`, `tp_pasifler_toplam_pasifler_ozkaynak_haric`, `sermaye_benzeri_pasifler`, `ppborclari_pasifler`, `maliyetli_pasifler_toplam_pasifler`, `serbest_sermaye_ta`

**Hesaplanmamış (2):** `tp_spread`, `yp_spread` — akım rate hesabı, ileride.

**Sanity:** KT 2025-Q3 için tüm değerler PBI ile spot-check edilmiş; "Kuveyt Türk" grubu invariant (bank == group) Δ=0.

**Notlar:**
- `serbest_sermaye_ta` için basitleştirilmiş formül kullanıldı (BDDK resmi tanımı daha geniş; PBI ile uyumsuzluk varsa genişletilecek).
- `npl_formasyonu` mevcut `donuk_intikal_ort_krediler − donuk_tahsilat_ort_krediler` farkından türetildi.

---

## v28 — 2025-05-01 — Pasifler Wrap Bug Fix

**Bug:** ControlBar'da Pasifler alt-kategorisi seçildiğinde measure dropdown alt satıra atlıyordu. Sebep: 65-karakterli `TP Alınan Krediler ve İ.E.M.K / Toplam Alınan Krediler ve İ.E.M.K` measure'ı browser select'in collapsed genişliğini ~600px+ yapıyor, `flex-wrap: wrap` tetikliyordu.

**Fix:** `.control-select.measure`'a `max-width: 360px` + `text-overflow: ellipsis`. Cat/subcat select'lere de max-width. Sadece 89 byte CSS değişikliği.

---

## v27 — 2025-05-01 — Export Modu Eklendi

**Yeni:** 4. mode `Export` — banka/grup multi-select × tarih aralığı × hierarchical measure tree → wide format tablo + Excel/CSV indir.

**Bileşenler:**
- ControlBar'a 4. button
- `ExportView` componenti (~350 satır)
- SheetJS CDN (1.5 MB external) Excel export için
- CSV fallback bağımlılıksız (UTF-8 BOM + `;` ayraç + ondalık virgül; Türkçe Excel uyumlu)

**Tasarım kararları:**
- Bankalar/Gruplar toggle (karışım yok)
- Tarih: başlangıç-bitiş aralık seçimi
- Hierarchical checkbox tree, indeterminate state
- 1000 satır tabloda max, indirmede tüm satırlar

---

## v17 → v26 — Komposizyon ve Trend modları (özet)

v17 baseline'ında Snapshot+Trend vardı. v17→v26 arası 9 iterasyon ile:

- v17: Komposizyon modu eklendi (5 kompozisyon × stack chart, banka/grup × tarih filtreleri, Bileşen/Döviz alt-tab'ları)
- v17 sonrası iterasyonlar: TP/YP refactor → geri alındı (BDDK detayda TP/YP olmayan kalemler nedeniyle); ana kalem üzerinden 2-segmentli döviz dağılımı yaklaşımına geçildi
- Trend modunda görünüm modları: Değer / YtD / YoY / QoQ Büyüme / Pazar Payı
- Snapshot'ta cascading dropdown (Kategori → Alt Kategori → Measure), top-20 sabit set'i, YtD chart yatay liste

Detaylı geçmiş için git log'a bakılır (Faz 1 sonrası repo'da olacak).

---

## Faz 1 — Repo İskeleti (bu commit)

İlk repo tasarımı:
- README, ARCHITECTURE, MEASURES, EXTENDING, DEPLOYMENT dökümantasyonu
- pipeline/ modülleri: lookup, measures, groups, ingest, compute
- scripts/ init_data ve recompute
- data/catalog.json, display_config.json

**Sonraki:** Faz 2 — backend + frontend ayrımı (FastAPI), Faz 3 — Admin UI, Faz 4 — HF Spaces deploy.
