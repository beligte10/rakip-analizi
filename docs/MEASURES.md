# Measure Kataloğu

Bu döküman 128 measure'ın tam referansıdır. Pipeline'ın gerçek formüllerinin "ground truth"u `pipeline/measures.py` içindeki Python fonksiyonları + docstring'leridir; bu MD dosya bu kodun insan-okunur özetidir.

**Statü (Faz 1.5):**
- Toplam tanımlı: **128**
- Raw veriden hesaplanabilen: **104** (MEASURE_FUNCS)
- Baseline'dan kopyalanan: **24** (BASELINE_PASSTHROUGH)
- Henüz hesaplanamayan placeholder: **2** (`tp_spread`, `yp_spread` — flow rate hesabı)

**BASELINE_PASSTHROUGH** kategorileri:
- **SYR & Çekirdek SYR** (2): BDDK ana raporlarında yok, ayrı sermaye yeterliliği raporlarından gelir
- **RWA-bağımlı rasyolar** (5): Risk Ağırlıklı Varlık tabanlı rasyolar (rorwa, ort_rav_ort_ozkaynak, net_faiz_ort_rav, grup_2_krediler_cekirdek_sermaye, faiz_getirili_ozkaynak)
- **YP detay** (3): USD/EUR krediler ve YP net pozisyon — Kur Riski tablosu kompleksitesi
- **PBI özel düzeltmeli** (2): maliyet_gelir_duzeltilmis, nim_duzeltilmis
- **Gayrinakdi** (2): gayrinakdi_krediler ve komisyon rasyosu — v29 PBI tanımı raw'dan farklı
- **PBI özel akım** (4): npl_formasyonu, spread, donuk_intikal/tahsilat — raw delta hesabıyla %5+ sapma
- **IEA tanım farkı** (6): nim, nim_bzk, faiz_getirili_ta/maliyetli/aktif_getirisi, maliyet_gelir — IEA/op gelir tanımında %1-5 sapma

KT 2025-Q3 için 102/102 raw measure birebir match (rel < 1e-3); 27 banka × 48 çeyrek için 91.8% exact match.

## İçindekiler

- [Yapı Taşları](#yapı-taşları) — formüllerde kullanılan ham BDDK kalemleri
- [Notasyon](#notasyon) — formül gösterim kuralları
- [v29'da Eklenen 21 Measure](#v29da-eklenen-21-measure) — detaylı formüller
- [Mevcut 105 Measure](#mevcut-105-measure) — kategori bazında liste
- [Henüz Hesaplanamayan 2](#henüz-hesaplanamayan-2)
- [Grup Aggregation Kuralları](#grup-aggregation-kuralları)

---

## Yapı Taşları

Tüm formüller bu temel kalemler üzerine kurulur. Bunlar BDDK xlsx'lerindeki orijinal Türkçe kalem adlarıdır.

### Bilanço — Ana Tablo (Para Birimi: Toplam | TP | YP)

**Aktifler tarafı:**
- `Toplam Aktifler`
- `Krediler Ve Alacaklar (Toplam)` — IFRS 9 sonrası ana kredi kalemi (Mevduat bankaları için bazen `Krediler` kullanılır; pipeline ikisini de dener)
- `Donuk Alacaklar`
- `Finansal Varlıklar (Net)`
- `Menkul Kıymetler` ile ilişkili alt kalemler:
  - `Gerçeğe Uygun D. Farkı K/Z Yan.Fv (Net)`
  - `Gerçeğe Uygun Değer Farkı Diğer Kapsamlı Gelire Yansıtılan Finansal Varlıklar`
  - `İtfa Edilmiş Maliyeti ile Ölçülen Finansal Varlıklar`
  - `Türev Finansal Varlıklar`
  - `Satılmaya Hazır Finansal Varlıklar (Net)` (legacy TMS 39)
  - `Vadeye Kadar Elde Tutulacak Yatırım.(Net)` (legacy TMS 39)
- `Maddi Duran Varlıklar (Net)`
- `Maddi Olmayan Duran Varlıklar (Net)`
- `Yatırım Amaçlı Gayrimenkuller (Net)`
- `Ortaklık Yatırımları`

**Pasifler tarafı:**
- `Toplam Pasifler` (= Toplam Aktifler, bilanço dengesi)
- `Mevduat`
- `Alınan Krediler`
- `Para Piyasalarına Borçlar`
- `İhraç Edilen Menkul Kıymetler (Net)`
- `Sermaye Benzeri Krediler`
- `Özkaynaklar`

### Mevduat detay tabloları (banka tipine göre değişir)

**Mevduat Bankaları** → `Mevduatın Vade Yapısına İlişkin Bilgiler`:
- `Toplam, Vadesiz`
- `Toplam Mevduat, Toplam`
- `Resmi Kur. Mevduatı, Toplam`
- `Tic. Kur. Mevduatı, Toplam`
- `Diğ. Kur. Mevduatı, Toplam`
- `Kıymetli Maden DH, Toplam`

**Katılım Bankaları** → `Toplanan Fonların Vade Yapısına İlişkin Bilgiler`:
- `Toplam Vadesiz`
- `Toplanan Fonların Vade Toplamı` (= Mevduat eşdeğeri)
- `Resmi Kuruluşlar \xa0Toplam` (3 alt-satır toplanır: gerçek kişi, ticari, diğer)
- `Ticari Kuruluşlar \xa0Toplam`
- `Diğer Kuruluşlar \xa0Toplam`
- `Kıymetli Maden DH \xa0Toplam`

**NOT — Non-breaking space:** Katılım kalemlerinde `\xa0` (Unicode U+00A0) karakteri var. Pipeline string match'lerinde bu karakter kritik; `Resmi Kuruluşlar Toplam` (regular space) hiçbir satırla eşleşmez.

### Gelir Tablosu

- `Faiz (Kar Payı) Gelirleri` / `Giderleri`
- `Net Faiz (Kar Payı) Geliri (Gideri)`
- `Alınan Ücret ve Komisyonlar` / `Verilen Ücret ve Komisyonlar`
- `Net Ticari Kar (Zarar)`
- `Diğer Faaliyet Giderleri (Operasyonel Giderler)`
- `Personel Giderleri` / `Reklam Giderleri` / `Karşılık Giderleri`
- `Brüt Faaliyet Karı / Zararı`
- `Net Dönem Karı (Zararı)`

### Şube & Personel

- `Şube-Personel` tablosundan `Şube Sayısı`, `Personel Sayısı`

---

## Notasyon

Formüllerde:
- `B[<kalem>]` = Bilanço Ana Tablo'dan o kalemin **Toplam** Para Birimi değeri
- `B[<kalem>; TP]` = aynı kalemin **TP** değeri
- `B[<kalem>; YP]` = aynı kalemin **YP** değeri
- `MVY[<kalem>]` = Mevduatın Vade Yapısı tablosundan (Mevduat bankası)
- `TFV[<kalem>]` = Toplanan Fonların Vade Yapısı (Katılım bankası)
- `M[<id>]` = mevcut başka bir computed measure'ın değeri
- `Σ_grup` = grup üyesi bankaların toplamı

---

## v29'da Eklenen 21 Measure

### Büyüklükler (4)

#### `vadeli_mevduat` — Vadeli Mevduat
```
B[Mevduat] - VadesizMevduat(banka)

VadesizMevduat = if Banka Türü == 'Katılım':
                    TFV[Toplam Vadesiz]
                 else:
                    MVY[Toplam, Vadesiz]
```
**Tip:** büyüklük, TL, stok | **Kategori:** Bilanço/Pasifler

#### `toplam_kaynak` — Toplam Kaynak
```
B[Mevduat] + B[Alınan Krediler]
         + B[Para Piyasalarına Borçlar]
         + B[İhraç Edilen Menkul Kıymetler (Net)]
```
**Tip:** büyüklük, TL, stok | **Kategori:** Bilanço/Pasifler

Para birimi varyantları için aynı formül; pipeline'da `m_toplam_kaynak(b, t, pb='TP'|'YP'|'Toplam')`.

#### `kiymetli_maden_mevduati` — Kıymetli Maden Mevduatı
```
if Katılım: TFV[Kıymetli Maden DH \xa0Toplam]
else:       MVY[Kıymetli Maden DH, Toplam]
```
**Tip:** büyüklük, TL, stok | **Kategori:** Bilanço/Pasifler

#### `resmi_kurumlar_mevduat` — Resmi Kurumlar Mevduatı
```
if Katılım: TFV[Resmi Kuruluşlar \xa0Toplam]   # 3 sub-satırın SUM'u
else:       MVY[Resmi Kur. Mevduatı, Toplam]
```
**Tip:** büyüklük, TL, stok | **Kategori:** Bilanço/Pasifler

### Rasyolar (17)

#### `npl_formasyonu` — NPL Formasyonu
```
M[donuk_intikal_ort_krediler] - M[donuk_tahsilat_ort_krediler]
```
Net new NPL formation rate. Akım rasyo, `\xa0` raw'dan değil, mevcut measure'lardan türetilir.  
**Tip:** rasyo, %, stok-akım karması | **Kategori:** Bilanço/Aktifler

#### `alinan_krediler_iemk_toplam_kaynak`
```
(B[Alınan Krediler] + B[İhraç Edilen Menkul Kıymetler (Net)]) / M[toplam_kaynak] × 100
```

#### `tp_alinan_toplam_alinan` — TP (Alınan + İEMK) / Toplam (Alınan + İEMK)
```
(B[Alınan Krediler; TP] + B[İhraç Edilen Menkul Kıymetler (Net); TP])
  ÷ (B[Alınan Krediler] + B[İhraç Edilen Menkul Kıymetler (Net)])
  × 100
```

#### `tuzel_krediler_tuzel_mevduat` — Tüzel Krediler / Tüzel Mevduat
```
M[tuzel_krediler] / TüzelMevduat × 100

TüzelMevduat = if Katılım:
                  TFV[Ticari Kuruluşlar \xa0Toplam]
                + TFV[Diğer Kuruluşlar \xa0Toplam]
                + TFV[Resmi Kuruluşlar \xa0Toplam]
               else:
                  MVY[Tic. Kur. Mevduatı, Toplam]
                + MVY[Diğ. Kur. Mevduatı, Toplam]
                + MVY[Resmi Kur. Mevduatı, Toplam]
```

#### `krediler_altindisi_mevduat` — Krediler / Altın-dışı Mevduat
```
Krediler / (B[Mevduat] - KıymetliMaden) × 100
```

#### `krediler_toplam_kaynak` — Krediler / Toplam Kaynak
```
Krediler / M[toplam_kaynak] × 100
```

#### `tp_krediler_tp_kaynak`
```
Krediler[TP] / TopplamKaynak[TP] × 100
```

#### `yp_krediler_yp_altindisi_kaynak`
```
Krediler[YP] / (TopplamKaynak[YP] - KıymetliMaden) × 100

NOT: Kıymetli Maden Mevduatı YP cinsinden kabul edilir.
```

#### `vadesiz_mevduat_toplam_kaynak`
```
VadesizMevduat / M[toplam_kaynak] × 100
```

#### `tp_mevduat_altindisi_mevduat`
```
B[Mevduat; TP] / (B[Mevduat] - KıymetliMaden) × 100
```

#### `tp_kaynak_toplam_kaynak`
```
TopplamKaynak[TP] / TopplamKaynak × 100
```

#### `toplam_kaynak_toplam_pasifler`
```
M[toplam_kaynak] / B[Toplam Pasifler] × 100
```

#### `tp_pasifler_toplam_pasifler_ozkaynak_haric`
```
B[Toplam Pasifler; TP] / (B[Toplam Pasifler] - B[Özkaynaklar]) × 100
```

#### `sermaye_benzeri_pasifler` — Sermaye Benzeri Krediler / Toplam Pasifler
```
B[Sermaye Benzeri Krediler] / B[Toplam Pasifler] × 100
```

#### `ppborclari_pasifler` — Para Piyasası Borçları / Toplam Pasifler
```
B[Para Piyasalarına Borçlar] / B[Toplam Pasifler] × 100
```

#### `maliyetli_pasifler_toplam_pasifler` — Maliyetli Pasifler / Toplam Pasifler
```
(M[toplam_kaynak] + B[Sermaye Benzeri Krediler]) / B[Toplam Pasifler] × 100
```

#### `serbest_sermaye_ta` — Serbest Sermaye / Toplam Aktifler ⚠
```
(B[Özkaynaklar] - SabitAktifler) / B[Toplam Aktifler] × 100

SabitAktifler = B[Maddi Duran Varlıklar (Net)]
              + B[Maddi Olmayan Duran Varlıklar (Net)]
              + B[Yatırım Amaçlı Gayrimenkuller (Net)]
              + B[Ortaklık Yatırımları]
```
**⚠ Basitleştirme:** BDDK'nın resmi Serbest Sermaye tanımı daha geniştir (Net Donuk Alacaklar, Cari Vergi Varlığı, Şerefiye düşülür). PBI'daki değerle uyumsuzluk olursa formül genişletilecek.

---

## Mevcut 105 Measure

### Bilanço


#### Bilanço / Aktifler  (46 measure)

| ID | Ad | Tip | Birim |
|---|---|---|---|
| `bireysel_kredi_kartlari` | Bireysel Kredi Kartları | büyüklük | TL |
| `donuk_alacaklar` | Donuk Alacaklar | büyüklük | TL |
| `donuk_alacaklar_satis_terkin_oncesi` | Donuk Alacaklar (Satış ve Terkin Öncesi) | büyüklük | TL |
| `grup_1_krediler` | Grup 1 Krediler | büyüklük | TL |
| `grup_2_krediler` | Grup 2 Krediler | büyüklük | TL |
| `konut_kredileri` | Konut Kredileri | büyüklük | TL |
| `krediler` | Krediler | büyüklük | TL |
| `tasit_kredileri` | Taşıt Kredileri | büyüklük | TL |
| `toplam_aktifler` | Toplam Aktifler | büyüklük | TL |
| `tuketici_kredileri` | Tüketici Kredileri ve Bireysel Kredi Kartları | büyüklük | TL |
| `tuzel_krediler` | Tüzel Krediler | büyüklük | TL |
| `ihtiyac_kredileri` | İhtiyaç Kredileri | büyüklük | TL |
| `bkk_toplam` | Bireysel Kredi Kartları / Toplam Krediler | rasyo | % |
| `diger_aktifler_ta` | Diğer Aktifler / Toplam Aktifler | rasyo | % |
| `npl_rasyosu` | Donuk Alacaklar / Toplam Krediler (NPL Rasyosu) | rasyo | % |
| `donuk_tahsilat_ort_krediler` | Donuk Alacaklar Dönemiçi Tahsilat / Ortalama Krediler | rasyo | % |
| `donuk_intikal_ort_krediler` | Donuk Alacaklar Dönemiçi İntikal / Ortalama Krediler | rasyo | % |
| `dis_ticaret_toplam` | Dış Ticaret Kredileri / Toplam Krediler | rasyo | % |
| `euro_yp_krediler` | EURO Cinsi Krediler / YP Krediler | rasyo | % |
| `faiz_getirili_maliyetli` | Faiz (Kar Payı) Getirili / Maliyetli Pasifler | rasyo | % |
| `faiz_getirili_ta` | Faiz (Kar Payı) Getirili / Toplam Aktifler | rasyo | % |
| `faiz_getirili_ozkaynak` | Faiz (Kar Payı) Getirili / Özkaynaklar | rasyo | % |
| `finansal_varliklar_net_ta` | Finansal Varlıklar (Net) / Toplam Aktifler | rasyo | % |
| `grup_1_krediler_toplam` | Grup 1 Krediler / Toplam Krediler | rasyo | % |
| `grup_2_krediler_toplam` | Grup 2 Krediler / Toplam Krediler | rasyo | % |
| `grup_2_krediler_cekirdek_sermaye` | Grup 2 Krediler / Çekirdek Sermaye | rasyo | % |
| `grup_2_tuketici_tuketici` | Grup 2 Tüketici Kredileri / Tüketici Kredileri | rasyo | % |
| `grup_2_tuzel_tuzel` | Grup 2 Tüzel Krediler / Tüzel Krediler | rasyo | % |
| `konut_tp_pasifler` | Konut Kredileri / TP Pasifler | rasyo | % |
| `konut_tuketici` | Konut Kredileri / Tüketici Kredileri | rasyo | % |
| `krediler_ta` | Krediler / Toplam Aktifler | rasyo | % |
| `mali_kesim_toplam` | Mali Kesime Verilen Krediler / Toplam Krediler | rasyo | % |
| `menkul_kiymetler_ta` | Menkul Kıymetler / Toplam Aktifler | rasyo | % |
| `npl_karsilama_orani` | NPL Karşılama Oranı | rasyo | % |
| `npl_rasyosu_satis_terkin_oncesi` | NPL Rasyosu (Satış ve Terkin Öncesi) | rasyo | % |
| `ortaklik_yatirimlari_ta` | Ortaklık Yatırımları / Toplam Aktifler | rasyo | % |
| `ort_rav_ort_ozkaynak` | Ortalama RAV / Ortalama Özkaynaklar | rasyo | % |
| `tp_aktifler_ta` | TP Aktifler / Toplam Aktifler | rasyo | % |
| `tp_krediler_toplam` | TP Krediler / Toplam Krediler | rasyo | % |
| `tasit_tuketici` | Taşıt Kredileri / Tüketici Kredileri | rasyo | % |
| `tuketici_toplam` | Tüketici Kredileri / Toplam Krediler | rasyo | % |
| `tuzel_toplam` | Tüzel Krediler / Toplam Krediler | rasyo | % |
| `usd_yp_krediler` | USD Cinsi Krediler / YP Krediler | rasyo | % |
| `yp_aktifler_toplam_pasifler` | YP Aktifler / Toplam Pasifler | rasyo | % |
| `yp_net_pozisyon_ozkaynak` | Yabancı Para Net Genel Pozisyonu / Toplam Özkaynaklar | rasyo | % |
| `ihtiyac_toplam` | İhtiyaç Kredileri / Toplam Krediler | rasyo | % |

#### Bilanço / Bilanço Dışı  (1 measure)

| ID | Ad | Tip | Birim |
|---|---|---|---|
| `gayrinakdi_krediler` | Gayrinakdi Krediler (Garanti ve Kefaletler) | büyüklük | TL |

#### Bilanço / Pasifler  (8 measure)

| ID | Ad | Tip | Birim |
|---|---|---|---|
| `mevduat` | Mevduat | büyüklük | TL |
| `vadesiz_mevduat` | Vadesiz Mevduat | büyüklük | TL |
| `ozkaynaklar` | Özkaynaklar | büyüklük | TL |
| `krediler_mevduat` | Krediler / Mevduat | rasyo | % |
| `syr` | Sermaye Yeterlilik Rasyosu (SYR) | rasyo | % |
| `tp_mevduat_toplam_mevduat` | TP Mevduat / Toplam Mevduat | rasyo | % |
| `vadesiz_mevduat_toplam_mevduat` | Vadesiz Mevduat / Toplam Mevduat | rasyo | % |
| `cekirdek_syr` | Çekirdek Sermaye Yeterliliği Oranı | rasyo | % |

### Gelir Tablosu


(40 measure)

| ID | Ad | Tip | Birim |
|---|---|---|---|
| `alinan_ucret_komisyonlar` | Alınan Ücret ve Komisyonlar | büyüklük | TL |
| `brut_faaliyet_kari` | Brüt Faaliyet Karı / Zararı | büyüklük | TL |
| `diger_faaliyet_giderleri` | Diğer Faaliyet Giderleri (Operasyonel Giderler) | büyüklük | TL |
| `faiz_gelirleri` | Faiz (Kar Payı) Gelirleri | büyüklük | TL |
| `faiz_giderleri` | Faiz (Kar Payı) Giderleri | büyüklük | TL |
| `gnakdi_alinan_ucret_komisyonlar` | G.Nakdi Kredilerden Alınan Ücret ve Komisyonlar | büyüklük | TL |
| `karsilik_giderleri` | Karşılık Giderleri | büyüklük | TL |
| `net_donem_kari` | Net Dönem Karı (Zararı) | büyüklük | TL |
| `net_faiz_geliri` | Net Faiz (Kar Payı) Geliri (Gideri) | büyüklük | TL |
| `net_ticari_kar` | Net Ticari Kar (Zarar) | büyüklük | TL |
| `net_ucret_komisyonlar` | Net Ücret ve Komisyonlar | büyüklük | TL |
| `personel_giderleri` | Personel Giderleri | büyüklük | TL |
| `reklam_giderleri` | Reklam Giderleri | büyüklük | TL |
| `verilen_ucret_komisyonlar` | Verilen Ücret ve Komisyonlar | büyüklük | TL |
| `nim_bzk_sonrasi` | BZK Sonrası Düzeltilmiş Net Faiz (Kar Payı) Marjı (NIM) | rasyo | % |
| `maliyet_gelir_duzeltilmis` | Düzeltilmiş Maliyet / Gelir Rasyosu | rasyo | % |
| `nim_duzeltilmis` | Düzeltilmiş Net Faiz (Kar Payı) Marjı (NIM) | rasyo | % |
| `faaliyet_gid_ort_aktif` | Faaliyet Giderleri / Ortalama Aktifler | rasyo | % |
| `faiz_getirili_aktif_getirisi` | Faiz (Kar Payı) Getirili Aktiflerin Getirisi | rasyo | % |
| `faiz_gideri_faiz_geliri` | Faiz (Kar Payı) Gideri / Faiz (Kar Payı) Geliri | rasyo | % |
| `faiz_maliyetli_pasif_maliyeti` | Faiz (Kar Payı) Maliyetli Pasiflerin Maliyeti | rasyo | % |
| `gayrinakdi_komisyon_gayrinakdi` | Gayrinakdi Kredi Komisyonları / Gayrinakdi Krediler | rasyo | % |
| `kaynak_pacal_maliyet` | Kaynağın Paçal Maliyeti | rasyo | % |
| `komisyon_gid_gel` | Komisyon Giderleri / Komisyon Gelirleri | rasyo | % |
| `kredi_mevduat_spread` | Kredi Mevduat Spread'i | rasyo | % |
| `cost_of_risk` | Kredi Riski Maliyeti (Cost of Risk) | rasyo | % |
| `kredi_pacal_getiri` | Kredilerin Paçal Getirisi | rasyo | % |
| `maliyet_gelir` | Maliyet / Gelir Rasyosu | rasyo | % |
| `net_faiz_ort_rav` | Net Faiz (Kar Payı) Geliri / Ortalama RAV | rasyo | % |
| `nim` | Net Faiz (Kar Payı) Marjı (NIM) | rasyo | % |
| `net_ucret_operasyonel` | Net Ücret ve Komisyonlar / Operasyonel Giderler | rasyo | % |
| `net_ucret_ort_aktif` | Net Ücret ve Komisyonlar / Ortalama Aktifler | rasyo | % |
| `roaa` | Ortalama Aktif Karlılığı (ROAA) | rasyo | % |
| `roae` | Ortalama Özkaynak Karlılığı (ROAE) | rasyo | % |
| `personel_net_kar` | Personel Giderleri / Net Dönem Kar/Zararı | rasyo | % |
| `personel_ort_aktif` | Personel Giderleri / Ortalama Aktifler | rasyo | % |
| `rorwa` | RORWA | rasyo | % |
| `reklam_net_kar` | Reklam Giderleri / Net Dönem Kar/Zararı | rasyo | % |
| `reklam_ort_aktif` | Reklam Giderleri / Ortalama Aktifler | rasyo | % |
| `spread` | Spread | rasyo | % |

### Şube & Personel


(10 measure)

| ID | Ad | Tip | Birim |
|---|---|---|---|
| `personel_sayisi` | Personel Sayısı | büyüklük | adet |
| `sube_sayisi` | Şube Sayısı | büyüklük | adet |
| `personel_basina_krediler` | Personel Başına Krediler | rasyo | bin_TL |
| `personel_basina_mevduat` | Personel Başına Mevduat | rasyo | bin_TL |
| `personel_basina_net_kar` | Personel Başına Net Kar | rasyo | bin_TL |
| `personel_basina_personel_gideri` | Personel Başına Personel Gideri | rasyo | bin_TL |
| `sube_basina_krediler` | Şube Başına Krediler | rasyo | bin_TL |
| `sube_basina_mevduat` | Şube Başına Mevduat | rasyo | bin_TL |
| `sube_basina_net_kar` | Şube Başına Net Kar | rasyo | bin_TL |
| `sube_basina_personel` | Şube Başına Personel | rasyo | adet |

---

## Henüz Hesaplanamayan 2

### `tp_spread`, `yp_spread` — TP/YP Kredi Mevduat Spread'i

**Konsept:** Annualized faiz geliri yieldı (TP/YP krediler üzerinden) − annualized faiz gideri maliyeti (TP/YP mevduat üzerinden).

**Neden eksik:** İki ardışık dönem ortalama bakiye + yıllıklandırma + para birimi kırılımı gerektiriyor. Akım kalemler (`Faiz (Kar Payı) Gelirleri`) BDDK'da Para Birimi='Toplam' raporlandığı için TP/YP ayrımı için sub-tablo derinliğine inmek lazım (`Kredilerden Alınan Faiz Gelirlerine İlişkin Bilgiler` tablosu).

**TBD:** PBI'daki orijinal formülü doğruladıktan sonra implementasyon. İleriki bir iterasyonda.

---

## Grup Aggregation Kuralları

`group_data` her measure için 5 grup değeri tutar. Toplama mantığı:

| Measure tipi | Aggregation |
|---|---|
| Büyüklük (TL) | `Σ` (üye bankaların toplamı) |
| Büyüklük (adet — şube/personel) | `Σ` |
| Rasyo (stok) | Ağırlıklı ortalama: `Σnumerator / Σdenominator × 100`. Her rasyo için pay/payda formülü `pipeline/groups.py` içinde tanımlı. |
| Rasyo (akım — npl_formasyonu) | Şu an basit ortalama; ileride weighted'a dönülebilir |

**5 grup:**
1. `Kuveyt Türk` (tek bankalı — KT'nin değerini doğrulamak için)
2. `Mevduat Bankaları`
3. `Rakip Bankalar` (KT'ye en yakın 5 banka — `rakip: true` field'ı catalog'ta)
4. `Katılım Bankaları` (tüm katılım bankaları, KT dahil)
5. `KT Hariç Katılım Bankaları`

Grup üyelikleri `data/catalog.json` → `groups.members` altında.

**Tutarlılık invariantı:** "Kuveyt Türk" grubu tek bankalıdır → her measure için `group_data['<measure>']['Kuveyt Türk']` = `bank_data['<measure>']['Kuveyt Türk']`. v29'da bu invariant tüm 21 yeni measure için Δ=0 olarak doğrulanmıştır.

---

## Doküman Bakımı

Yeni measure eklediğinde bu MD'nin güncellenmesi şart. Otomatik jeneratör (Faz 2): `scripts/generate_measures_doc.py` her measure fonksiyonunun docstring'ini okuyup MD üretir. Şimdilik manuel.
