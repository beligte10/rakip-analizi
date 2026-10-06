# Kuveyt Türk Rekabet Analizi · 2026 İlk Yarı — Teknik Devir Dokümanı

> **Eşlik ettiği dosya:** `HTML_guncel/Kuveyt Turk Rekabet Analizi.html` (3,96 MB, tek dosya, 43 slayt)
> **Dönem:** 30.06.2026 · **Karşılaştırma bazları:** 31.12.2025 (bilanço YtD) · 30.06.2025 (gelir tablosu YoY, ortalamalar)
> **Baz:** Konsolide olmayan (solo) · **Birim:** milyon TL (aksi yazılmadıkça)
> **Banka seti (ekranda):** Kuveyt Türk · QNB · DenizBank · Akbank · Garanti BBVA · Yapı Kredi
> **Veri modelindeki bankalar:** yukarıdaki altı + İş Bankası · TEB · Vakıf Katılım · Ziraat Katılım (sunumda filtrelenir)
> **Hazırlanma:** Ekim 2026 · Strateji Grup Müdürlüğü

---

**İçindekiler**

| | |
|---|---|
| §0 Amaç ve okuma sırası · §1 Mimari · §2 Kaynaklar · §3 Dönemler · §4 Ortak sözleşmeler | Çerçeve |
| §5 Ölçüm sözlüğü — 5.1 büyüklük · 5.2 pazar payı · 5.3 aktif · 5.4–5.5 kredi · 5.6–5.7 aktif kalitesi · 5.8–5.9 fonlama · 5.10 altın · 5.11–5.12 döviz ve kur · 5.13 likidite · 5.14 sermaye · 5.15–5.16 marj ve ZK · 5.17–5.18 gider · 5.19 verimlilik · 5.20–5.21 kârlılık · 5.22 tampon · 5.23 denetçi görüşü | Hesaplamalar |
| §6 Slayt × ölçüm haritası · §7 Doğrulama · §8 Bilinen sapmalar | Kontrol |
| Ek A Alan sözlüğü (354 alan) · Ek B REV dosyaları · Ek C Paket betiği · Ek D Kaynak dokümanlar | Ekler |

---

## 0 · Bu doküman ne işe yarar

HTML'deki **her rakamın nereden geldiğini ve nasıl hesaplandığını** anlatır. Üç soruyu cevaplar:

1. **Ham veri nereden?** Hangi BDR tablosu/dipnotu, hangi CA_BDDK MCP measure'ı veya ham kalemi.
2. **Nasıl hesaplandı?** Formül, dönem eşlemesi, yıllıklandırma, ortalama, yuvarlama.
3. **Nerede görünüyor?** Hangi slaytta, hangi grafikte, hangi kontrol durumunda.

**Okuma sırası önerisi**

| Amaç | Bölüm |
|---|---|
| HTML'i açmak, veriyi değiştirmek | §1 Mimari · Ek C |
| Bir rakamın kaynağını bulmak | §5 Ölçüm sözlüğü → Ek A alan sözlüğü |
| Bir slaytın arkasındaki ölçümler | §6 Slayt × ölçüm haritası |
| MCP ile kendi hesabınızı karşılaştırırken | §4 Ortak sözleşmeler · §8 Bilinen sapmalar |
| Rakamların iç tutarlılığı | §7 Doğrulama |

> ⚠️ **Tekrar üretilebilirlik notu.** Analiz rakamları Ağustos 2026'da BDR PDF'lerinden ve CA_BDDK MCP'den
> betiklerle (`compute.py`, `mktables.py`, `npl3.py`) üretildi. Bu betikler geçici bir çalışma ortamında
> koştu ve **saklanmadı.** Kalıcı çıktı `KT_veri.js` veri modelidir. Bir rakamı yeniden üretmek için bu
> dokümandaki formül + kaynak kalem adresi yeterlidir; çoğu ölçüm için MCP üzerinden tek çağrıyla
> doğrulama yolu da verilmiştir.

---

## 1 · Mimari — HTML nasıl çalışıyor

### 1.1 · Dosya formatı

HTML, Claude Design tarafından üretilmiş **kendi kendine yeten bir paket** (bundle). Dış bağımlılığı yok;
fontlar, logolar, kütüphaneler ve veri dosyaları içine gömülü.

```
<script type="__bundler/manifest">  ← 32 varlık: { uuid: { mime, compressed, data(base64) } }
<script type="__bundler/template">  ← JSON-string olarak sayfa şablonu (≈551 KB HTML)
```

Yükleyici açılışta manifest'teki her varlığı base64 → (gerekirse gzip açma) → Blob URL'e çevirir ve
şablondaki `uuid` referanslarını bu URL'lerle değiştirir.

| Varlık türü | Adet | İçerik |
|---|---:|---|
| `font/woff2` | 18 | Archivo ve gövde fontu |
| `image/png` | 2 | Arka plan / kapak görselleri |
| JS — çalışma zamanı | 5 | React · ReactDOM · `dc-runtime` · Kuveyt Türk design system paketi · şablon iskeleti |
| **JS — veri** | **7** | **`KT_veri.js`** (64 KB) · `KT_logolar.js` (1,8 MB, base64 logolar) · 5 REV ek veri dosyası |

### 1.2 · Veri dosyaları

| Dosya (paket içi adı) | Global | Ne taşır | §'ta |
|---|---|---|---|
| `uploads/KT_veri.js` | `B`, `NPLX`, `NFRG`, `COMPD`, `COMPS`, `GDRB`, `GDRP`, `TUFE`, `TUFE_YTD`, alan listeleri | **Ana veri modeli** — 10 banka × 354 alan + yardımcı tablolar | §5, Ek A |
| `uploads/KT_logolar.js` | `window.KTLOGOS` | Logo ve amblemler (data-URI) | — |
| `uploads/KT_veri_ek_REV01.js` | `window.KT_KOMP_ARA25` | Aktif kompozisyonu, 31.12.2025 | §5.3 |
| `uploads/KT_veri_ek_REV03.js` | `window.KT_FONLAMA` | Fonlama kompozisyonu, iki dönem, PP dahil | §5.8 |
| `uploads/KT_veri_ek_REV04.js` | `window.KT_VADE` | Vadesiz/vadeli/mevduat dışı + altın kırılımı | §5.8 |
| `uploads/KT_veri_ek_REV05.js` | `window.KT_TLCARI` | TL cari hesap ve toplam TL fonlama, iki dönem | §5.9 |
| `uploads/KT_veri_ek_REV15.js` | `window.KT_GIDER_REV15` | KT pazarlama kaleminin reklam/promosyon/kart ayrışımı | §5.18 |

> REV-02 ek dosyası pakette **yoktur** — REV-03 onun yerine geçer (ikisi de `KT_FONLAMA` tanımlar).

### 1.3 · Çalışma zamanı akışı

Şablondaki tek mantık bileşeni (`class Component extends DCLogic`, ≈177 KB) şöyle çalışır:

```
componentDidMount
  └─ 7 veri betiğini sırayla <script> olarak ekler (blob URL varsa onu, yoksa göreli yolu kullanır)
  └─ 120 ms aralıkla yoklar: B yüklendi mi + 4 REV globali hazır mı (en fazla 40 deneme)
banks()                     ← REV-17 banka seti (§1.4) + set içi pay alanlarını yeniden kurar
renderVals()                ← her render'da TÜM slaytların değerlerini hesaplar
  ├─ REV-04 düzeltmesi      vadesiz_altinsiz alanını KT_VADE'den yeniden kurar (§5.8)
  ├─ REV-16 türetmesi       tf_lvl / tf_ytd (toplam fonlama) alanlarını üretir (§5.1)
  └─ out.s00 … out.s49      her slaytın satırları, raylar, manşetler, dipnotlar
```

**Kontrol durumu** (`state`): `metric` (S04 çipi) · `mode` (nominal/reel) · `v04` (tutar/büyüme) ·
`m06/m07/m08` (pay/tutar) · `v06/v07/v08` (banka/paçal) · `d06/d15` (dönem çipleri) · `v15`, `b18`
vb. Her çip/toggle kombinasyonu aynı `renderVals()` çağrısıyla yeniden hesaplanır — önbellek yok.

**Biçimleme yardımcıları** (§4.9): `pct` · `pctS` (işaretli) · `pctRaw` · `num` (tr-TR binlik ayırıcı) ·
`round` (işaret-simetrik).

### 1.4 · Banka seti ve gruplar — iki katman

Veri modeli on bankayı taşır; **sunum altısını gösterir.** Filtre `banks()` içinde yapılır (REV-17):

```js
const S = B.filter(b => ['isb','zk','vk','teb'].indexOf(b.id) < 0);   // 6 banka
S.forEach(b => { b.tier1 = false; });                                   // Tier-1 anahtarı kaldırıldı
```

| Grup (sunum) | Üyeler | Kod |
|---|---|---|
| Rakip paçalı | QNB · DenizBank | `GROUPS.rakip` |
| Tier-1 paçalı | Akbank · Garanti BBVA · Yapı Kredi | `GROUPS.tier1` |
| Altı banka | KT + yukarıdaki beşi | `GROUPS.alti` |

> ⚠️ **Eski set kalıntıları — kullanılmaz.** `KT_veri.js` analiz dönemindeki grupları da taşır:
> `CGRP` (Rakip = QNB+DZB+TEB · Katılım = VK+ZK · Tier-1 = 4 banka · Altı banka = KT, QNB, DZB, TEB, VK, ZK),
> `NFRG` (bu gruplara göre NFR paçalları) ve REV ek dosyalarındaki `pacal` blokları. **Sunum bunları
> okumaz;** paçalları ve set içi payları her render'da banka bazlı tutarlardan yeniden kurar (§4.7, §4.8).
> Veri modelini başka bir araçta kullanacaksanız bu alanlara güvenmeyin.

### 1.5 · Veri nasıl güncellenir

Paket tek dosya olduğu için iki yol var:

| Yol | Ne zaman | Nasıl |
|---|---|---|
| **A · Claude Design projesinde** | Normal yol | `uploads/` altındaki `KT_veri.js` / REV dosyasını değiştir, yeniden paketle |
| **B · Paketi doğrudan düzenle** | Acil düzeltme | Manifest'te ilgili `uuid`'in `data` alanını yeni dosyanın gzip+base64'ü ile değiştir (Ek C betiği) |

Varlık–dosya eşlemesi (bu sürüm):

| uuid (ilk 8) | Dosya |
|---|---|
| `13bd152c` | `KT_veri.js` |
| `7bd53fe9` | `KT_logolar.js` |
| `4771c5cd` | `KT_veri_ek_REV01.js` |
| `759362a4` | `KT_veri_ek_REV03.js` |
| `fa139862` | `KT_veri_ek_REV04.js` |
| `586f879a` | `KT_veri_ek_REV05.js` |
| `c4cf4973` | `KT_veri_ek_REV15.js` |

> ⚠️ `KT_veri.js` üst seviyede `const` tanımlar; aynı sayfada iki kez yüklenirse hata verir. Bileşen bunu
> `window.__ktLoaded` bayrağıyla engeller — betiği elle `eval` etmeyin.

---

## 2 · Veri kaynakları ve soy ağacı

### 2.1 · Kaynak hiyerarşisi

| # | Kaynak | Kapsam | Bu çalışmadaki rolü |
|---|---|---|---|
| 1 | **BDR PDF (solo)** | Bağımsız denetim / sınırlı denetim raporları — ana tablolar + dipnotlar | **Nihai otorite.** 30.06.2026 verisinin birincil kaynağı |
| 2 | **CA_BDDK MCP** | 27 banka, çeyreklik, 342 measure + 1.885 ham kalem, **yalnız solo** | Çapraz kontrol; 31.12.2025 ve 30.06.2025 tabanlarının çoğu; Tier-1 dörtlüsünün verisi |
| 3 | **KT iç muhasebe kayıtları** | 168 hesap, diğer faaliyet giderleri | Yalnız S42 (KT gider kırılımı) |
| 4 | **Harici** | TÜİK TÜFE · BDR değerleme kurları | Reel dönüşüm ve kur arındırması |

**Çelişki kuralı:** BDR ile MCP farklıysa BDR kazanır; fark sessizce yutulmaz, kayda geçer (§8).

### 2.2 · BDR klasörü ve birim tuzağı

```
01_bdr/
├── Haziran 2026/   solo BDR'ler  →  MİLYON TL
├── Aralık 2025/    solo BDR'ler  →  BİN TL
└── Haziran 2025/   solo BDR'ler  →  BİN TL
```

⚠️ 30.04.2026 tarih ve 33239 sayılı Resmî Gazete değişikliğiyle sunum birimi **bin TL → milyon TL** oldu.
2025 raporlarındaki tutarlar **1.000'e bölünerek** kullanıldı.

⚠️ `Aralık 2025/Denizbank - 31.12.2025 Solo.pdf` **aslında 31.03.2025 raporudur.** DenizBank'ın 2025 tam
yıl gelir tablosu MCP'den alındı; bilanço 31.12.2025 değerleri 30.06.2026 raporunun karşılaştırma
sütunundan okundu.

### 2.3 · CA_BDDK MCP

| Konu | Not |
|---|---|
| Kapsam | Solo · çeyreklik · 2013'ten bu yana · tutarlar **mn TL** döner |
| İki katman | **Measure** (DAX tanımlı, `get_metric`/`compare`) ve **ham kalem** (`get_line_item`, `para` = TP/YP/Toplam) |
| Banka adları | `Garanti Bankası` (**Garanti BBVA değil**) · `Yapı Kredi` · `QNB Finansbank` · `İş Bankası` · `Kuveyt Türk` |
| ⚠️ Yanlış ad | **Hata vermez, sessizce boş/0 döner.** `list_banks` ile ad doğrulanmalı |
| 2026-06-30 yüklemesi | **Kısmi.** SYR tüm bankalarda `null`; KT'nin TCMB hesabının TP bacağı (65.971) eksik; VK'nin zorunlu karşılık ve donuk alacak kayıtları sıfır (§8) |
| `null` ≠ yok | `null` dönen rasyolarda neredeyse her zaman **tek bir bileşen** eksiktir; DAX'i `explain_metric` ile alıp bileşeni BDR'den tamamlamak gerekir |

### 2.4 · Harici seriler

| Seri | Değer | Kaynak | Kullanım |
|---|---:|---|---|
| TÜFE YtD (Ara-25 → Haz-26) | **%17,76** | TÜİK | Bilanço kalemlerinin reel dönüşümü · `TUFE_YTD = 0.1776` |
| TÜFE YoY (Haz-25 → Haz-26) | **%32,11** | TÜİK | Gelir tablosu kalemlerinin reel dönüşümü · `TUFE = 0.3211` |
| USD değerleme kuru | 39,7595 · 42,88188 · **46,61281** | BDR (30.06.2025 · 31.12.2025 · 30.06.2026) | Kur arındırması — YtD **+%8,70** |
| EUR | YtD +%5,53 · YoY +%13,95 | BDR | Yalnız duyarlılık notu |

> ⚠️ Kodda iki farklı USD/TRY YtD değeri geçer: veri modelindeki `*_usd` alanları **%8,70** ile
> hesaplanmıştır (BDR kurları); S22'nin sabit kur kutusunda **%8,73** yazar (alanlardan geri çözülmüş
> değer, yuvarlama gürültüsü). Fark ≤ 0,03 puan, gösterimi etkilemez.

### 2.5 · Hangi rakam hangi kaynaktan — özet

| Blok | 30.06.2026 | 31.12.2025 | 30.06.2025 |
|---|---|---|---|
| Bilanço büyüklükleri (6 çekirdek banka) | BDR | BDR karşılaştırma sütunu | BDR · MCP |
| Bilanço büyüklükleri (Tier-1 dörtlüsü) | MCP + BDR | MCP | MCP |
| Gelir tablosu (6A ve TTM) | BDR | BDR / MCP (FY2025) | BDR / MCP |
| Donuk alacak hareketi | **BDR dipnotu** (MCP'de KT/VK eksik) | — | BDR |
| SYR / CET1 / Basel kaldıraç / LCR | **BDR** (MCP boş) | BDR | — |
| TCMB hesabı TP/YP, zorunlu karşılık geliri | BDR (KT ve VK) · MCP (diğerleri) | MCP | MCP |
| TÜFEX, serbest karşılık, denetçi görüşü | **Yalnız BDR** | BDR | — |
| Şube / personel | BDR · MCP | — | MCP |
| KT diğer faaliyet gideri kırılımı | KT iç veri | — | KT iç veri |

---

## 3 · Dönem kısaltmaları

| Kısaltma | Anlamı |
|---|---|
| **Haz-26** | 30.06.2026 dönem sonu (stok) |
| **Ara-25** | 31.12.2025 dönem sonu (stok) — bilanço YtD bazı |
| **Haz-25** | 30.06.2025 dönem sonu — ortalama bakiyelerin ikinci ucu, bilanço YoY bazı |
| **6A26 / 6A25** | 01.01–30.06 kümülatif akım (gelir tablosu) |
| **FY2025** | 2025 tam yıl kümülatif |
| **TTM** | Son 12 ay: `6A26 + FY2025 − 6A25` |
| **Q1 / Q2** | Çeyrek izole akım: Q2 = 6A − 3A |

---

## 4 · Ortak hesaplama sözleşmeleri

Bu sözleşmeler **tüm** ölçümlerin altında yatar. MCP'nin DAX tanımlarıyla hizalıdır; bilinçli sapmalar
açıkça işaretlenmiştir.

### 4.1 · Yıllıklandırma — TTM, 4× çarpma yok

```
X(TTM) = X(6A26) + X(FY2025) − X(6A25)
```

MCP'deki `(Y)` sonekli her measure bu kuralla kurulur (`Annualized Sum`).

**KT örneği — zorunlu karşılık geliri:** `9.325 + 16.034 − 7.633 = 17.726`

> ⚠️ **İki bilinçli istisna:**
> (1) **Gider büyümesi** ve **aktif kalitesi akımları** yıllıklandırılmaz — 6A26 ile 6A25 doğrudan karşılaştırılır.
> (2) **`cor6`** (yarıyıl risk maliyeti) **6A × 2** ile yıllıklandırılır (§5.6). Raporun geri kalanı TTM'dir.

### 4.2 · Ortalama bakiye — 2 nokta, yıllık uçlar

```
Ortalama X = ( X(Haz-26) + X(Haz-25) ) / 2
```

Çeyreklik 5 nokta **kullanılmaz** (MCP DAX'i budur, korunur).

**KT örneği — ortalama aktif:** `(1.472.314 + 1.047.971) / 2 = 1.260.143` → MCP `Ortalama Aktifler` ile birebir.

⚠️ Yüksek enflasyonda 2 nokta ortalaması dönem içi büyümeyi düşük yansıtır; ROAA/ROAE görece yüksek çıkar.

⚠️ **Tek istisna — kasıtsız:** altı çekirdek bankanın `rorwa` alanında ortalama RAV, Haz-25 yerine **Ara-25** ile
kurulmuştur. Ekranda düzeltilmedi; etkisi ve düzeltilmiş değerler §5.14 ve §8.1'de.

### 4.3 · Büyüme

| Kalem türü | Ölçü | Formül | Baz |
|---|---|---|---|
| Bilanço (stok) | **YtD** | `X(Haz-26) / X(Ara-25) − 1` | Önceki yıl sonu — **istisnasız varsayılan** |
| Gelir tablosu (akım) | **YoY** | `X(6A26) / X(6A25) − 1` | Önceki yılın aynı dönemi |
| Rasyo / pay | **bps** | `(oran_t − oran_baz) × 10.000` | Rasyonun kendi bazı |
| Adet (şube, personel) | adet + YoY | `N(Haz-26) − N(Haz-25)` | Haz-25 |

⛔ Oranlarda **yüzdesel değişim kullanılmaz**, her zaman bps.

### 4.4 · Reel dönüşüm

```
Reel = (1 + nominal) ÷ (1 + aynı dönemin TÜFE değişimi) − 1
```

| Kalem türü | TÜFE | Değer |
|---|---|---:|
| Bilanço YtD | Ara-25 → Haz-26 | **%17,76** |
| Gelir tablosu YoY | Haz-25 → Haz-26 | **%32,11** |

**KT örneği — toplam aktif:**

```
Nominal YtD = 1.472.314 ÷ 1.352.066 − 1 = +%8,89
Reel        = 1,08894 ÷ 1,1776 − 1      = −%7,53
```

Eşdeğer okuma: aktifin enflasyona ayak uydurması için 1.592.193 olması gerekiyordu; 1.472.314 oldu —
eksik 119.879, hedefin %7,53'ü.

⚠️ **Basit çıkarma yanlıştır:** `8,89 − 17,76 = −8,87 puan` kaybı 1,34 puan abartır.
Kimlik: `reel = (nominal − TÜFE) ÷ (1 + TÜFE)`.

⚠️ Türkiye'de bankalar **TMS 29 uygulamıyor**; tüm seriler nominal ve düzeltme öncesidir — reel dönüşüm
çifte düzeltme yaratmaz.

### 4.5 · Dolar bazlı büyüme ve kur arındırması

```
Dolar bazlı büyüme = (1 + TL cinsinden büyüme) ÷ (1 + USD/TRY değişimi) − 1      USD/TRY YtD = %8,70
```

**Kullanım (S22 "kur etkisi arındırıldığında"):** TP bacağı **reel** (`÷ 1,1776`), YP bacağı **dolar bazlı**
(`÷ 1,0870`) gösterilir. İkisi farklı numeraire'dir; toplamları doğrudan karşılaştırılmaz.

⚠️ YP sepetinin dolar/euro/altın kırılımı BDR'de yok; tek referans kur (USD) bir **yaklaşıklıktır**.
Euro ile hesaplansa ~3 puan daha düşük çıkardı. Altın hesapları da bu sepetin içindedir.

### 4.6 · Spread — geometrik

```
Spread (bps) = ( (1 + getiri) ÷ (1 + maliyet) − 1 ) × 10.000
```

Basit çıkarma kullanılmaz. Aynı desen kredi–mevduat makası (`km_spread`) için de geçerlidir.

### 4.7 · Paçal — Σ ÷ Σ, asla rasyo ortalaması

```
Grup paçalı = Σ(pay_i) ÷ Σ(payda_i)
```

Basit rasyo ortalaması **hiçbir yerde** kullanılmaz. Sunumda paçal her render'da yeniden kurulur;
payda alanı veri modelinde yoksa oran alanından **geri türetilir**:

| Ölçüm | Pay | Payda (geri türetme) |
|---|---|---|
| Büyüme paçalı (S04) | `Σ X(Haz-26)` | `Σ X(Haz-26) ÷ (1 + ytd_i)` = Σ X(Ara-25) |
| Maliyet/gelir paçalı | `Σ opex` | `Σ opex_i ÷ mgr_i` = Σ faaliyet geliri |
| OPEX karşılama paçalı | `Σ nuk` | `Σ opex` |
| NFR paçalı (S13) | `Σ npl_netform` | `Σ npl_netform_i ÷ nfr_i` = Σ ortalama brüt kredi |
| RAV yoğunluğu paçalı (S31) | `Σ rwa` | `Σ aktif` |
| Kompozisyon paçalı (S06–S08, S15–S16) | `Σ bileşen` | `Σ toplam` |

**Örnek — altı banka aktif paçalı:**
`Σ aktif(Haz-26) = 17.385.454` · `Σ aktif(Ara-25) = 15.250.928` → **+%14,0** nominal · **−%3,2** reel.
KT'nin −%7,5'i paçalın **4,3 puan** gerisindedir (S04 manşeti).

⚠️ **Seviye paçalı yok** (tutar görünümünde gruplar için toplam veya altı banka ortalaması gösterilir, §5.1).
⚠️ **Paydası açıklanmayan rasyonun paçalı yazılmaz** — LCR, LCR-YP, Basel III kaldıraç oranı.

### 4.8 · Set içi pazar payı

```
pay_X(banka) = X(banka) ÷ Σ X(altı banka)
```

Veri modelindeki `pay`, `pay_aktif`, `pay_kredi`, `pay_mevduat`, `pay_kar`, `pay_altin` alanları **eski altı
banka setine göre** hesaplanmıştı. Sunum bunları `banks()` içinde **yeni sete göre yeniden yazar**:

| Alan | Sunumdaki tanım | KT |
|---|---|---:|
| `pay[1]` / `pay_aktif` | aktif ÷ Σ aktif (Haz-26) | **%8,47** |
| `pay[0]` | aktif(Ara-25) ÷ Σ aktif(Ara-25); Ara-25 = aktif ÷ (1 + aktif_ytd) | %8,87 |
| `pay_kredi` · `pay_mevduat` · `pay_kar` · `pay_altin` | ilgili kalem ÷ set toplamı | %7,55 · %9,18 · %10,97 · %22,65 |

### 4.9 · Yuvarlama ve gösterim

```js
round(v, d) = sign(v) × Math.round(|v| × 10^(d+2)) / 10^d      // yüzde, işaret-simetrik
```

`Math.round` yarımı +∞'a yuvarladığı için −5,25 → −5,2 verirken +5,25 → +5,3 veriyordu; büyüklük üzerinden
yuvarlayıp işaret geri konarak iki yön eşitlendi (REV-06).

| Gösterim | Kural |
|---|---|
| Tutar | `tr-TR` binlik ayırıcı, tam sayı mn TL (`1.472.314`) · grup şeridinde mia TL |
| Yüzde | Çoğunlukla 1 ondalık; NPL, NFR, ROAA, NIM gibi küçük oranlar 2 ondalık |
| İşaret | `+` / `−` (U+2212 eksi işareti) |
| bps | Tam sayı |

⚠️ **Hassas alan önceliği:** `yp_mevduat`/`yp_kredi` beş ondalıklı ve ham orana eşittir;
`mevduat_yppay`/`kredi_yppay` aynı oranın dört ondalığa yuvarlanmış kopyasıdır. İki hücrede 0,1 puan
fark yaratır (DenizBank YP mevduat %34,6 vs %34,7; Garanti %32,7 vs %32,8). Doğrusu ham orandır.

### 4.10 · Brüt / net kredi

```
Toplam Brüt Krediler = Krediler + Finansal kiralama alacakları + Faktoring alacakları   (donuk DAHİL, BZK öncesi)
                     = Bilanço "Krediler Ve Alacaklar (Toplam)"  · standart veri seti excel 471
                     = MCP `Toplam Brüt Krediler`
Net Krediler         = Brüt − Beklenen Zarar Karşılıkları (bilanço)
```

| Kullanım | Büyüklük |
|---|---|
| Tüm rasyolar, büyüme, sıralama, pay | **Brüt** |
| Kompozisyon (payların %100 tutması gereken tablolar) — S06 aktif kompozisyonu | **Net** |
| Getirili aktifler (MCP DAX'i) | **Net** (bilinçli istisna) |

⚠️ `Krediler Ve Alacaklar` (excel 472, dar) **brüt değildir** — katılım bankalarında kiralama ve donuk
alacak kadar eksik çıkar (KT'de 31.12.2025'te 83.683 mn TL, brütün %12,8'i).

### 4.11 · Toplam kaynak ile toplam fonlama — iki ayrı büyüklük

| Ad | Tanım | KT Haz-26 | MCP karşılığı | Nerede |
|---|---|---:|---|---|
| **Toplam kaynak** (dar) | Mevduat + Alınan krediler + İhraç edilen MK (net) | **1.200.198** | `Toplam Kaynak` measure'ı | `kredi_kaynak` (%63,2) · altın hariç kredi/kaynak (%91,2) · S15 ray |
| **Toplam fonlama** (geniş) | Toplam kaynak + **Para piyasalarına borçlar** | **1.245.044** | measure yok: `Toplam Kaynak` + `Para Piyasalarına Borçlar` | S04 çipi · S15 · S16 · S18 · S22 · S25 · S26 · S28 · S33 çipi |

```
KT: 1.200.198 + 44.846 = 1.245.044          ← tk_tp + tk_yp = toplam_kaynak + pp   (10/10 bankada birebir)
```

⚠️ İsimler karıştırılmaz: PP içeren her yerde **"toplam fonlama"**, içermeyen her yerde **"toplam kaynak"**.

### 4.12 · Terminoloji köprüsü

Veri modeli ve MCP konvansiyonel sözlüğe normalize edilmiştir (`Faiz Gelirleri`, `Mevduat`). Ekranda
karma karşılaştırmada **`Faiz (Kâr Payı)`** köprüsü kullanılır; tek başına "faiz" katılım bankası için yazılmaz.

| Konvansiyonel | Katılım |
|---|---|
| Faiz geliri / gideri | Kâr payı geliri / gideri |
| Mevduat · vadesiz · vadeli | Toplanan fon · özel cari hesap · katılma hesabı |
| Kredi | Fon kullandırımı |
| Net faiz marjı | Net kâr payı marjı |
| Menkul kıymet ihracı | Sukuk / kira sertifikası (SPV üzerinden — solo bilançoda **Alınan Krediler** içinde) |


---

## 5 · Ölçüm sözlüğü

Her aile için: **alan adı** (`KT_veri.js` veya sayfa içi) · **tanım ve formül** · **kaynak kalem** · **KT değeri** · **ekrandaki yeri**.
Kaynak sütunundaki kısaltmalar:

| Kısaltma | Anlamı |
|---|---|
| **BDR** | Solo bağımsız denetim / sınırlı denetim raporu — tablo veya dipnot adıyla |
| **MCP·m** | CA_BDDK MCP **measure**'ı (DAX tanımlı) |
| **MCP·k** | CA_BDDK MCP **ham kalemi** (`get_line_item`) |
| **xl NNN** | Standart veri setinin excel satırı (31.12.2025 şablonu, `01a_kalem_indeksi.csv`) — referans adres |
| **türetilmiş** | Bu dokümandaki başka alanlardan formülle |

Değerler KT, 30.06.2026; oranlar % ile, tutarlar mn TL.
Tablolar ekrandaki ölçümlerin **ara girdilerini de** içerir. Bir alanın sayfa kodunca doğrudan okunup okunmadığını ve
hangi slaytta göründüğünü **Ek A'nın "Ekran" sütunu** gösterir; *(ekranda yok)* notu yalnız akla gelebilecek
karışıklıklar için düşülmüştür.

---

### 5.1 · Büyüklükler ve büyüme · *S04*

| Alan | Tanım / formül | Kaynak | KT |
|---|---|---|---:|
| `aktif` | Toplam aktifler | BDR bilanço · MCP·m `Toplam Aktifler` · xl 521 | 1.472.314 |
| `aktif_ytd` | `aktif ÷ aktif(Ara-25) − 1` | Ara-25 = BDR karşılaştırma sütunu / MCP | +%8,89 |
| `aktif_reel` | `(1 + aktif_ytd) ÷ 1,1776 − 1` | türetilmiş | −%7,53 |
| `kredi` | **Toplam brüt krediler** (krediler + kiralama + faktoring, donuk dahil) | BDR bilanço "Krediler ve Alacaklar (Toplam)" · MCP·m `Toplam Brüt Krediler` · xl 471 | 758.027 |
| `kredi_ytd` · `kredi_reel` | YtD / reel | türetilmiş | +%15,85 · −%1,63 |
| `mevduat` | Mevduat / toplanan fonlar (bankalar dahil) | BDR bilanço · MCP·m `Toplam Mevduat` · xl 522 | 983.867 |
| `mevduat_ytd` · `mevduat_reel` | YtD / reel | türetilmiş | +%9,32 · −%7,17 |
| `ozkaynak` · `ozkaynak_ytd` | Özkaynaklar · YtD | BDR bilanço · MCP·m `Özkaynaklar` · xl 570 | 138.732 · +%14,33 |
| `toplam_kaynak` · `tk_ytd` | **Dar tanım:** mevduat + alınan krediler + ihraç edilen MK (net) | MCP·m `Toplam Kaynak` · xl 522+525+530 | 1.200.198 · +%9,55 |
| `toplam_kaynak_ytd_reel` | `(1 + tk_ytd) ÷ 1,1776 − 1` | türetilmiş | −%6,97 |
| `pp` | Para piyasalarına borçlar | BDR bilanço · MCP·k `Para Piyasalarına Borçlar` · xl 526 | 44.846 |
| **`tf_lvl`** *(sayfa içi)* | **Toplam fonlama** = `tk_tp + tk_yp` = toplam kaynak + PP | türetilmiş (REV-16) | **1.245.044** |
| **`tf_ytd`** *(sayfa içi)* | `tf_lvl ÷ [ tk_tp ÷ (1+tk_tp_ytd) + tk_yp ÷ (1+tk_yp_ytd) ] − 1` | türetilmiş (REV-16) | **+%8,97** |
| `gayrinakdi` | Garanti ve kefaletler toplamı | BDR · MCP·m `Gayrinakdi Krediler` · xl 2156 | 221.597 *(ekranda yok)* |

**S04 iki görünüm (REV-16, varsayılan `Tutar`):**

| | `Tutar` | `Büyüme` |
|---|---|---|
| Çubuk | `lvl` alanı (Haz-26 tutarı) | `*_ytd` nominal veya reel |
| İkinci değer / soluk çubuk | YtD (soluk çubuk yok) | diğer ölçüm (nominal ↔ reel) |
| Referans çizgisi | **6 banka aritmetik ortalaması** `Σ lvl ÷ 6` | **6 banka paçalı** `Σ lvl ÷ Σ lvl/(1+ytd) − 1` |
| Grup şeridi | toplamlar, **mia TL** (`round(Σ ÷ 1000)`) | paçallar (Rakip · Tier-1 · 6 banka) |
| Nominal \| Reel | pasif (tutarın reel karşılığı yok) | aktif |

> ⚠️ **`tf_ytd` türetme hassasiyeti.** Sayfa, Ara-25 tabanını yuvarlanmış YtD alanlarından geri kurar
> (KT 1.142.524). MCP'den birebir çekilen taban **1.142.596**'dır (`Toplam Kaynak` 1.095.592 +
> `Para Piyasalarına Borçlar` 47.004) → YtD +%8,966. Gösterilen 1 ondalıkta fark yok; ama on bankanın
> birkaçı yuvarlama sınırına 1–4 bps mesafededir. Kesin değerler gerekiyorsa REV-16 v3 §4.3 tablosu esas.

> ⚠️ **Özkaynak ve toplam fonlama için reel alan yoktur;** sayfa `seriesOf()` içinde `(1+nom)/(1+TÜFE YtD)−1`
> ile anlık hesaplar.

---

### 5.2 · Pazar payı · *S05 · S00 kapak*

| Alan | Tanım | KT |
|---|---|---:|
| `pay` | `[Ara-25 payı, Haz-26 payı]` — aktif, set içi (§4.8) | %8,87 → %8,47 |
| `pay_aktif` · `pay_kredi` · `pay_mevduat` · `pay_kar` · `pay_altin` | Haz-26 set içi pay; `pay_kar` = 6A26 net kâr payı | %8,47 · %7,55 · %9,18 · %10,97 · %22,65 |

S05 bir **slope** grafiğidir: her banka için Ara-25 → Haz-26 aktif payı.
⚠️ Veri modelindeki bu alanlar eski sete göredir (`pay` üç elemanlı: Haz-25 · Ara-25 · Haz-26); sunum yeniden yazar.

---

### 5.3 · Aktif anatomisi · *S06*

Kaynak: `COMPD[banka].a` = 4 bileşen × `[tutar, YtD, reel, pay değişimi bps]` · alan adları `akt_*`.

| Alan | Tanım | Kaynak | KT tutar · pay |
|---|---|---|---:|
| `akt_nakit` | **Nakit değerler ve merkez bankası (üst başlık):** kasa + TCMB + bankalar + para piyasalarından alacaklar | BDR bilanço · MCP·m `Nakit ve Nakit Benzerleri` | 422.646 · %28,7 |
| `akt_menkul` | Altı finansal varlık satırı (GUD-K/Z · GUD-DKG · itfa edilmiş maliyet · türev FV dahil) | MCP·m `Menkul Kıymetler` | 258.891 · %17,6 |
| `akt_netkredi` | **Net** krediler = brüt − beklenen zarar karşılıkları (bilanço) | MCP·m `Net Krediler` · xl 471 − xl 491 | 733.078 · %49,8 |
| `akt_diger` | **Artık kalem:** MDV + MODV + yatırım amaçlı GM + ortaklık yatırımları + vergi varlığı + satış amaçlı DV + diğer | `aktif − diğer üçü` | 57.699 · %3,9 |

```
Kimlik:  akt_nakit + akt_menkul + akt_netkredi + akt_diger = aktif     (10/10 banka, sıfır sapma)
Pay değişimi (bps) = [ X/aktif  −  (X/(1+X_ytd)) / (aktif/(1+aktif_ytd)) ] × 10.000
```

KT: nakit payı **−325 bps**, net kredi payı **+270 bps**.

**REV-01 · Ara-25 dönem çipi** (`KT_KOMP_ARA25`): `Ara-25 tutarı = Haz-26 tutarı ÷ (1 + YtD)`, ardından
bankanın Ara-25 toplam aktifine oturacak şekilde normalize edilir. KT Ara-25: 432.095 · 228.671 · 636.819 · 54.477
(toplam 1.352.062).

⚠️ Kompozisyonda net kredi kullanılır (payların %100 tutması için) — tek istisna; diğer her yerde brüt.
⚠️ Ziraat Katılım'ın `Menkul Kıymetler` measure'ı 2026-06-30'da `null` — bileşenlerinden toplandı (79.526).

---

### 5.4 · Kredi portföyü kompozisyonu · *S07*

Kaynak: `COMPD[banka].k` · alan adları `kp_*` · toplam = `kredi` (brüt).

| Alan | Tanım | Kaynak | KT |
|---|---|---|---:|
| `kp_tuketici` | Tüketici kredileri + bireysel kredi kartları (personel dahil) | BDR dipnot "Tüketici Kredileri, Bireysel KK, Personel…" · MCP·m `Tüketici Kredileri ve Bireysel Kredi Kartları` | 95.338 |
| `kp_mali` | Mali kesime verilen krediler | BDR dipnot "Birinci ve İkinci Grup Krediler…" (Grup 1 + 2) | 12.508 |
| `kp_disticaret` | İhracat + ithalat kredileri | aynı dipnot | 114.680 |
| `kp_leasing` | Finansal kiralama alacakları | BDR bilanço · xl 485 | 76.354 |
| `kp_tuzel` | **Artık kalem:** `kredi − diğer dördü` — tüzel + kurumsal KK + **donuk alacaklar + faktoring** | türetilmiş | 459.147 |
| `kp_tuzel_lh` | **Tüzel (geniş)** = `kp_tuzel + kp_leasing + kp_disticaret` | türetilmiş | 650.181 |

**S07 üç kova kullanır** (`KPLH`): tüketici · tüzel (geniş) · mali kesim. Sebep: leasing ve dış ticaretin
banka tipine göre bilanço içi/dışı ayrışması karşılaştırmayı bozar (aşağıda).

⚠️ **Yapısal sıfır — leasing.** Mevduat bankaları leasingi ayrı iştirak üzerinden yürütür; solo bilançoda
`kp_leasing = 0`. Katılım bankasında bilanço içindedir. "Mevduat bankalarında leasing yok" denmez.
Sıfırlar sıfır uzunlukta çubuk + etiketle çizilir.

⚠️ **MCP tuzağı:** `Tüketici Kredileri ve Bireysel Kredi Kartları` measure'ı **Yapı Kredi'de KMH'yi çift
sayıyor** (1.030.521 vs dipnot 881.201) ve İş Bankası'nda +23.817 fazla. Bu iki bankada BDR dipnotu esas
alındı; tüzel artık kalem yeniden kuruldu. Diğer sekiz bankada measure dipnotla birebir.
⚠️ `Grup 1 Krediler` measure'ı on bankanın hiçbirinde kullanılmaz (brütü tutturmuyor) — §5.6.

---

### 5.5 · Tüketici kredileri · *S08*

Kaynak: `COMPD[banka].t` · alan adları `tuk_*` · toplam = `tuk_toplam` = `kp_tuketici`.

| Alan | Tanım | Kaynak | KT |
|---|---|---|---:|
| `tuk_konut` | Konut (personel konut dahil) | BDR dipnot · xl 1456 (+YP 1466, personel 1477) · MCP·m `Konut Kredileri` | 25.636 |
| `tuk_tasit` | Taşıt (personel dahil) | xl 1457 · 1478 | 6.096 |
| `tuk_ihtiyac` | İhtiyaç + **"Diğer"** satırı (personel dahil) | xl 1458–1459 · 1479 | 4.732 |
| `tuk_bkk` | Bireysel kredi kartları (personel KK dahil) | xl 1473 · 1494 | 58.874 |
| `tuk_kmh` | Kredili mevduat hesabı (TP + YP) | MCP·k `Kredili Mevduat Hesabı - TP/YP` · xl 1498–1499 | **0** |

⚠️ **Yapısal sıfır — KMH.** Faizli açık hesap ürünüdür; katılım bankalarında yoktur (`tuk_kmh_ytd = null`).
KT: tüketici + bireysel KK +%36,7 YtD (reel +%16,1); tutar artışının yaklaşık **%83'ü bireysel kredi kartından** (`COMPD.t`'den türetilmiş).

---

### 5.6 · Aktif kalitesi — stok · *S09 · S10 · S14*

| Alan | Tanım / formül | Kaynak | KT |
|---|---|---|---:|
| `npl` | Donuk alacaklar (brüt, III + IV + V. grup) | BDR bilanço · xl 490 | 22.732 |
| `npl_o` · `npl_ara` | `npl ÷ kredi` · aynı oran Ara-25 | MCP·m `NPL Rasyosu` | %3,00 · %2,00 |
| `npl_d_bps` | `(npl_o − npl_ara) × 10.000` | türetilmiş | +100 |
| `g2` | İkinci grup (yakın izlemedeki) krediler | BDR dipnot "Birinci ve İkinci Grup Krediler…" | 57.564 |
| `g2_o` · `g2_ara` | `g2 ÷ kredi` | türetilmiş | %7,59 · %6,84 |
| `npl_kars` | **3. aşama (özel) karşılık ÷ donuk alacak** | BDR dipnot (beklenen kredi zararı aşama tablosu) | %71,4 |
| `g2_kars` | 2. aşama karşılık ÷ Grup 2 kredileri | BDR dipnot | %10,31 |
| `bzk` · `bzk_yoy` | 6A brüt beklenen kredi zararı karşılık gideri · YoY | BDR gelir tablosu · dipnot "Karşılık Giderleri" | 10.556 · +%76,0 |
| `cor6` | `2 × bzk ÷ [(kredi + kredi(Ara-25)) / 2] × 10.000` — **yarıyıl ×2** | türetilmiş | 299 bps |
| `cor_ttm` | MCP·m `Brüt CoR (bps)` = TTM(BKZK brüt) ÷ ortalama brüt kredi (2 nokta) | MCP (KT için BDR) | 244 bps |

**S14 risk merdiveni:** `Grup 1 = kredi − g2 − npl` (**artık kalem**), Grup 2, donuk — %100 normalize.

⚠️ `npl_kars` **MCP'nin `NPL Karşılama Oranı`'ndan farklıdır** — MCP toplam beklenen zarar karşılığını
(1+2+3. aşama) paya alır (ör. Garanti %95,6), analiz yalnız 3. aşamayı (Garanti %62,9).
⚠️ `cor6` ve `cor_ttm` **farklı tabanlardır**, aynı seride karıştırılmaz. KT'de MCP `Brüt CoR` kullanılamaz
(`Beklenen Kredi Zararı Karşılıkları (Brüt)` KT için 0 döner, measure 82 bps verir).
⚠️ `Beklenen Zarar Karşılıkları` ≠ `Beklenen Kredi Zararı Karşılıkları (Brüt)` — farklı measure'lar.
⚠️ `cor6`, `cor_ttm`, `bzk` bu sürümde ekranda gösterilmiyor.

---

### 5.7 · Aktif kalitesi — akım (donuk alacak hareketi) · *S10 · S11 · S12 · S13*

**Kaynak: BDR dipnotu *"Toplam donuk alacaklara ilişkin bilgiler"* — III + IV + V. grup toplamı.**
Veri modelinde hem `B[i]` içinde hem `NPLX[id]` sözlüğünde.

```
Hareket kimliği:  açılış + intikal − tahsilat − terkin − satış (± diğer) = kapanış
```

| Alan | Tanım | Dipnot satırı (xl, grup başına) | KT |
|---|---|---|---:|
| `npl_acilis` | Önceki dönem sonu (31.12.2025) bakiyesi | "Önceki Dönem" · xl 1654/1673/1692 | 13.095 |
| `npl_intikal` | Dönem içi intikal | "Dönem İçi İntikal" · xl 1655/1674/1693 | 20.929 |
| `npl_tahsilat` | Dönem içi tahsilat | "Dönem İçi Tahsilat" · xl 1658/1677/1696 | 9.871 |
| `npl_terkin` | Aktiften silinen | "Aktiften Silinen" · xl 1662/1681/1700 | 1.421 |
| `npl_satis` | Satılan | "Satılan" · xl 1663/1682/1701 | 0 |
| `npl_kapanis` | Dönem sonu | = `npl` | 22.732 |

| Türetilmiş alan | Formül | KT |
|---|---|---:|
| `npl_netform` | **Net oluşum** = `intikal − tahsilat` (terkin ve satış **girmez**) | 11.058 |
| `npl_stok_degisim` | Stok değişimi = `kapanış − açılış` (terkin + satış dahil) | 11.058 |
| `npl_ort_brut` | Ortalama brüt kredi = `(kredi(Haz-26) + kredi(Haz-25)) / 2` | 652.014 |
| `nfr` | **Net NPL formasyon rasyosu** = `npl_netform ÷ npl_ort_brut` — **yıllıklandırılmamış, 6A** | %1,70 |
| `npl_intikal_r` · `npl_tahsilat_r` | `intikal ÷ npl_ort_brut` · `tahsilat ÷ npl_ort_brut` | %3,21 · %1,51 |
| `npl_tah_int` · `npl_tah_int_25` | Tahsilat ÷ intikal (6A26 · 6A25) — yıllıklandırmadan bağımsız | %47,2 · %42,6 |
| `npl_cikis_pay` · `npl_cikis_pay_25` | **Portföy temizliği** = `(terkin + satış) ÷ dönem başı donuk` | %10,9 · %54,9 |
| `npl_o_terkin` | `(npl + terkin) ÷ (kredi + terkin)` | %3,18 |
| `npl_o_duz` | **Terkin + satış öncesi NPL** = `(npl + terkin + satış) ÷ (kredi + terkin + satış)` | %3,18 |
| `npl_bps_duz` · `npl_bps_terkin` | `(npl_o_duz − npl_o) × 10.000` | +18 |
| `npl_d_bps_duz` | `(npl_o_duz − npl_ara) × 10.000` — düzeltilmiş bozulma | +118 |
| `npl_stok_ytd` | `kapanış ÷ açılış − 1` | +%73,6 |
| `npl_intikal_25` · `npl_tahsilat_25` · `npl_cikis_25` | 6A25 akımları | 12.651 · 5.383 · 3.862 |
| `npl_int_yoy` · `npl_tah_yoy` · `npl_cikis` | İntikal/tahsilat YoY · terkin + satış | *(ekranda yok)* |

**S13 paçalı** sayfa içinde (§4.7): `Σ npl_netform ÷ Σ (npl_netform/nfr)`. Altı banka **%1,54** · Rakip %1,67 · Tier-1 %1,47.
`NFRG` (veri modeli) eski gruplara göredir, **kullanılmaz.**

**MCP ile ilişki**

| MCP measure | İlişki |
|---|---|
| `Net NPL Formasyon Rasyosu` | Payı aynı (`intikal + tahsilat`, tahsilat negatif saklı); **yıllıklandırılmış (×2)** — 2'ye bölünerek karşılaştırılır |
| `NPL (Terkin Dahil)` | `npl_o_duz` ile cebirsel olarak aynı; adına rağmen **satışı da içerir** — 5 bankada birebir |

⚠️ **KT ve Vakıf Katılım'da MCP akımları eksik** (KT Şüpheli grup intikali 6.060 yok; VK tablosu sıfır) →
bu iki bankada **BDR esas.**
⚠️ **MCP yanlış sıfırı:** `Donuk Alacaklar (Şüpheli, Önceki Dönem)` KT 2026-06-30 → **0** (doğrusu 4.545);
açılış toplamı MCP'den 8.550 çıkar, doğrusu 13.095. Hareket tablosu MCP'den okunursa açılış bilanço
stoğuyla (Ara-25 `npl`) çapraz kontrol edilmeli.
⚠️ **Hareket kimliği dört bankada tablo kalemleri nedeniyle tam kapanmaz:** TEB işaretsiz "Diğer" 483 ·
Vakıf Katılım "kayıttan düşülen" 771'in 739'u terkin, 32'si II. gruba aktarım · Garanti +135 · İş +15
(diğer giriş/çıkış satırları). Rasyolarda daima `npl_netform` kullanılır.
⚠️ Yıllıklandırma yok: yalnız aynı uzunluktaki dönemler karşılaştırılabilir.

---

### 5.8 · Fonlama · *S15 · S16*

| Alan | Tanım / formül | Kaynak | KT |
|---|---|---|---:|
| `vadesiz` | Vadesiz mevduat / **özel cari hesaplar** (altın vadesiz dahil) | BDR dipnot "Toplanan Fonların Vade Yapısı" (katılım) / "Mevduatın Vade Yapısı" (mevduat) | 599.982 |
| `vadeli` | Vadeli mevduat / **katılma hesapları** | aynı | 383.885 |
| `vadesiz_pay` · `vadesiz_pay_ara` | `vadesiz ÷ mevduat` | türetilmiş | %61,0 · %61,4 |
| `mdk` | **Mevduat dışı kaynak** = alınan krediler + ihraç edilen MK (net) | MCP·m `Alınan Krediler+İhç Edilen Mk(Net)` · xl 525 + 530 | 216.331 |
| `mdk_pay` | `mdk ÷ toplam_kaynak` | türetilmiş | %18,0 |
| `musteri` | Müşteri mevduatı payı = `1 − bankalararası ÷ toplam mevduat` | BDR vade yapısı dipnotu (katılım xl 2609/2626 ÷ 2645 · mevduat xl 1866 ÷ 1873) | %99,8 *(ekranda yok)* |
| `kredi_mevduat` · `km_ara` | `kredi ÷ mevduat` | MCP·m `Krediler/Mevduat` | %77,0 · %72,7 |
| `kredi_kaynak` · `kk_ara` | `kredi ÷ toplam_kaynak` (dar, PP hariç) | MCP·m `Krediler/Toplam Kaynak` | %63,2 · %59,7 |
| `kredi_mevduat_altin_haric` | `kredi ÷ (mevduat − altin)` | türetilmiş | %123,3 |
| `kredi_toplam_kaynak_altin_haric` | `kredi ÷ (toplam_kaynak − altin)` | türetilmiş | %91,2 |
| `vadesiz_altinsiz` *(sayfa içi düzeltilmiş)* | **Altın hariç cari hesap payı** = `(vadesiz − altın vadesiz) ÷ (mevduat − altın)` | `KT_VADE` (REV-04) | **%45,1** |

> ⚠️ **`vadesiz_altinsiz` veri modelinde hatalıdır — sunum düzeltir.** Altı çekirdek bankada (KT, QNB,
> DZB, TEB, VK, ZK) alan `(vadesiz − altın vadesiz) ÷ mevduat` ile hesaplanmış: altın **yalnız paydan**
> düşülmüş, paydadan düşülmemiş (KT **%28,2**). Tier-1 dörtlüsünde doğru formül kullanılmış. Sunum
> `renderVals()` başında `KT_VADE.banka` dizisinden yeniden kurar:
> ```js
> pay   = vadesiz − altin_vadesiz                         // 599.982 − 322.498 = 277.484
> payda = (vadesiz + vadeli) − (altin_vadesiz + altin_vadeli)   // 983.867 − 369.246 = 614.621
> vadesiz_altinsiz = pay / payda                          // %45,15
> ```
> Veri modelini başka yerde kullanıyorsanız `KT_VADE.vadesiz_altinsiz_duzeltilmis` alanını okuyun.

**S15 · Fonlama kompozisyonu — `KT_FONLAMA` (REV-03)**

```
Toplam fonlama = mevduat + alınan krediler + ihraç edilen MK + para piyasalarına borçlar
sira = [mevduat, alinan_krediler, ihrac_edilen_mk, para_piyasalarina_borclar] × { ara25, haz26 }
KT haz26 = [983.867, 216.331, 0, 44.846]  → 1.245.044
KT ara25 = [900.001, 195.592, 0, 47.004]  → 1.142.597
```

| Görünüm | Segmentler |
|---|---|
| Kalem bazlı (varsayılan) | Mevduat · Alınan krediler · İhraç MK/sukuk · Para piyasaları |
| Mevduat / mevduat dışı | Mevduat · (alınan krediler + ihraç MK + PP) |
| Dönem çipi | Haz-26 / Ara-25 — satır sırası Haz-26 mevduat payına sabit |

Kaynak: Haz-26 mevduat ve PP → `KT_veri.js`; alınan krediler ve ihraç MK → MCP measure; Ara-25'in dördü de MCP.
Kimlik: `mevduat + alınan kredi + ihraç MK = toplam kaynak` — iki dönemde 10/10.

⚠️ **Sukuk / SPV.** Katılım bankaları kendi tüzel kişilikleriyle ihraç yapamaz; SPV ihraçları solo
bilançoda **Alınan Krediler** içindedir. `İhraç edilen MK = 0` "sukuk yok" demek değildir (`spv_notu`).
⚠️ TEB'in Ara-25 ihraç MK = 0 değeri gerçektir (2026'da ihraca başladı: 0 → 15.374).

**S16 · Vade kırılımı — `KT_VADE` (REV-04)**

```
sira = [vadesiz, vadeli, mevduat_disi, altin_vadesiz, altin_vadeli]
KT  = [599.982, 383.885, 261.177, 322.498, 46.748]       mevduat_disi = alınan kredi + ihraç MK + PP
```

| Görünüm | Baz | KT cari payı |
|---|---|---:|
| Mevduat | vadesiz + vadeli | %61,0 |
| Toplam fonlama | + mevduat dışı (PP dahil) | %48,2 |
| Altın hariç | (vadesiz − altın vadesiz) + (vadeli − altın vadeli) + mevduat dışı | %31,7 |

---

### 5.9 · TL cari hesap · *S18*

| Alan | Tanım | Kaynak | KT |
|---|---|---|---:|
| `tp_cari` | TL vadesiz mevduat / TL özel cari hesap | MCP·m `TP Vadesiz Mevduat` (9/10 birebir) | 114.320 |
| `tp_mevduat` | TL mevduat / toplanan fon | BDR bilanço TP sütunu | 407.663 |
| `tp_cari_pay` · `tp_cari_pay_ara25` | `tp_cari ÷ tp_mevduat` | türetilmiş | %28,0 · %29,9 |
| `tp_cari_pay_degisim_bps` | `(tp_cari_pay − ara25) × 10.000` | türetilmiş | −185 |

**İkinci görünüm — `KT_TLCARI` (REV-05):** payda **toplam TL fonlama** = `tk_tp` (TP mevduat + TP alınan
kredi + TP ihraç MK + TP PP).

```
sira = [tl_cari_haz26, tl_fonlama_haz26, tl_cari_ara25, tl_fonlama_ara25]
KT   = [114.320, 467.231, 109.281, 426.144]     →  %24,5 (Haz-26) · %25,6 (Ara-25)
Kimlik: MCP 'TP Kaynak' (PP hariç) + pp_tp = tk_tp  →  423.718 + 43.513 = 467.231   (10/10)
```

⚠️ MCP measure boşluğu: `TP Vadesiz Mevduat` Vakıf Katılım için 2026-06-30'da 0 döner; ham kalem dolu (23.522).
Eksen varsayılan görünüme sabit — çip değişince çubuk yeniden ölçeklenmez, payda genişleyince kısalır.

---

### 5.10 · Altın · *S19 · S05 rayı*

| Alan | Tanım / formül | Kaynak | KT |
|---|---|---|---:|
| `altin` | **Kıymetli maden depo hesapları** (müşteri altın hesapları) — YP mevduat içinde | BDR dipnot "Toplanan Fonların Vade Yapısı" kıymetli maden satırları | 369.246 |
| `altin_ara` · `altin_haz` | Ara-25 · Haz-25 bakiyesi | BDR | 321.900 · 194.085 |
| `altin_ytd` · `altin_yoy` | YtD · YoY | türetilmiş | +%14,7 · +%90,3 |
| `altin_pay_mev` · `altin_pay_ara` · `altin_pay_haz` | `altin ÷ mevduat` (üç dönem) | türetilmiş | %37,5 · %35,8 · %28,2 |
| `altin_vadesiz` | Altın hesaplarının vadesiz kısmı | BDR vade dipnotu | 322.498 |
| `altin_vadesiz_pay` | `altin_vadesiz ÷ altin` | türetilmiş | %87,3 |
| `altin_katki` | `altin_vadesiz ÷ vadesiz` — altının cari hesap içindeki payı | türetilmiş | %53,8 |
| `pay_altin` | Set içi altın payı (§4.8) | sayfa içi | %22,7 |
| `altin_zk_alt` · `altin_zk_ust` | Altına isabet eden zorunlu karşılık tahmini bandı = `altin × %26 · %30` | türetilmiş (tahmin) | 96.004 – 110.774 |
| `altin_aktif` | Aktif tarafındaki kıymetli maden (yalnız katılım bankalarında dolu) | BDR | 29.217 *(ekranda yok)* |

⚠️ BDR'ler altın hesabının yalnız TL karşılığını verir; büyümenin **fiyat / hacim ayrıştırması yapılamaz.**

---

### 5.11 · Döviz (YP) kompozisyonu · *S22 · S24 · S25 · S26 · S28 · S33 · S34*

Para birimi bacakları **BDR bilançosunun TP ve YP sütunlarından** okunur (MCP·k `para` = TP / YP).
Kimlik: `TP + YP = Toplam` her kalemde kontrol edilir.

| Alan | Tanım | KT |
|---|---|---:|
| `kredi_tp` · `kredi_yp` | Brüt kredinin TP / YP bacağı | 445.270 · 312.757 |
| `mevduat_tp` · `mevduat_yp` | Mevduatın TP / YP bacağı (YP **altın dahil**) | 407.662 · 576.205 |
| `tk_tp` · `tk_yp` | **Toplam fonlamanın** TP / YP bacağı (**PP dahil**) | 467.231 · 777.813 |
| `pp_tp` · `pp_yp` | PP borçlarının TP / YP bacağı | 43.513 · 1.333 |
| `tcmb_yp` | TCMB hesabı YP bacağı | 216.961 |

**Paylar ve değişimler**

| Alan | Formül | KT |
|---|---|---:|
| `kredi_yppay` · `_ara25` · `_bps` | `kredi_yp ÷ kredi` · Ara-25 · fark bps | %41,3 · %43,3 · −205 |
| `mevduat_yppay` · `_ara25` · `_bps` | `mevduat_yp ÷ mevduat` | %58,6 · %59,4 · −81 |
| `tk_yppay` · `_ara25` · `_haz25` · `_bps` · `_bps_yoy` | `tk_yp ÷ (tk_tp + tk_yp)` | %62,5 · %62,7 · %61,3 · −23 · +121 |
| `yp_kredi` · `yp_mevduat` | Aynı paylar, **5 ondalık** (ham orana eşit — §4.9) | %41,259 · %58,565 |
| `yp_aktif` | YP aktif ÷ toplam aktif | %51,9 |
| `yp_toplam_kaynak_pay` | `(tk_yp − pp_yp) ÷ toplam_kaynak` — **PP hariç** | %64,7 *(REV-11 ile ekrandan kalktı)* |

**Büyüme — kur arındırılmış (S22 "kur etkisi arındırıldığında")**

| Alan | Formül | KT |
|---|---|---:|
| `*_tp_ytd` · `*_tp_ytd_reel` | TP bacağı YtD · `(1+ytd) ÷ 1,1776 − 1` | kredi +%20,0 / +%1,9 · mevduat +%11,5 / −%5,3 · fonlama +%9,6 / −%6,9 |
| `*_yp_ytd` · `*_yp_ytd_usd` | YP bacağı YtD (TL) · `(1+ytd) ÷ 1,0870 − 1` | kredi +%10,4 / +%1,5 · mevduat +%7,8 / −%0,8 · fonlama +%8,6 / −%0,1 |

**Para birimi bazında kredi / fonlama (S25 · S33 çipi)**

| Alan | Formül | KT |
|---|---|---:|
| `ktk_tp` | `kredi_tp ÷ tk_tp` | %95,3 |
| `ktk_yp` | `kredi_yp ÷ tk_yp` | %40,2 |
| `ktk_top` | `kredi ÷ (tk_tp + tk_yp)` — **toplam fonlama bazı** | %60,9 |
| `ktk_fark_puan` | `(ktk_tp − ktk_yp) × 100` | 55,1 |
| `km_tp` · `km_yp` · `km_fark_puan` | Kredi ÷ mevduat, para birimi bazında | %109,2 · %54,3 · 54,9 *(ekranda yok)* |

> ⚠️ İki "kredi/kaynak" oranı vardır ve ikisi de doğrudur: **%63,2** (toplam kaynak, PP hariç — `kredi_kaynak`)
> ve **%60,9** (toplam fonlama, PP dahil — `ktk_top`). Etiket hangisi olduğunu söylemek zorundadır.

**YP fonlama fazlası (S26) — sayfa içi (REV-08)**

```
YP fazlası        = max(0, tk_yp − kredi_yp)            KT 777.813 − 312.757 = 465.056
Aktife oranı      = YP fazlası ÷ aktif                   KT %31,6
Soluk çubuk       = tcmb_yp  (TCMB YP hesabı — zorunlu karşılığın vekili)   KT 216.961
Altın segmenti    = altin;  altın hariç fazla = YP fazlası − altin   KT 95.810
```

⚠️ Veri modelindeki `yp_fazla` (`mevduat_yp − kredi_yp`, KT 263.448) ve `yp_fazla_aktif` **eski tanımdır**, kullanılmaz.
⚠️ **YP zorunlu karşılık bakiyesi BDR'de ayrı satır değildir.** TCMB YP hesabı vekil olarak kullanılır ve
ekranda "TCMB YP hesabı" diye etiketlenir.

**Altın hariç gerçek döviz mevduatı** *(kodda var; slayt bu sürümde sunumdan çıkarılmış)*

| Alan | Formül | KT |
|---|---|---:|
| `mev_yp_ah` | `mevduat_yp − altin` | 206.959 |
| `mev_yppay_ah` | `mev_yp_ah ÷ mevduat` | %21,0 |
| `mev_yp_ah_ytd` · `_usd` | YtD · dolar bazlı | −%2,6 · −%10,4 |

⚠️ **MCP measure adı tuzağı:** `YP Aktifler/ Toplam Aktifler` measure'ının DAX'i `YP Aktifler ÷ YP Pasifler`'dir
— YP aktif payı **değil**, YP karşılama oranıdır. `yp_aktif` ham kalemlerden hesaplandı.

---

### 5.12 · Kur pozisyonu · *S28*

**Kaynak: BDR dipnotu "Kur riskine ilişkin bilgiler"** (katılım: *Ana Ortaklık Bankanın…* tablosu; toplam satırları).

| Alan | Tanım | Kaynak | KT |
|---|---|---|---:|
| `nbp` | Net bilanço pozisyonu (YP aktif − YP pasif) | xl 1422 | −35.675 |
| `nnp` | Net nazım hesap pozisyonu | xl 1423 | +27.822 |
| `ngp` | **Net genel pozisyon** = `nbp + nnp` | türetilmiş | −7.853 |
| `ngp_ozk` | `ngp ÷ ozkaynak` (yasal limit takibi; MCP·m `Yabancı Para Net Genel Pozisyonu / Toplam Özkaynaklar`) | türetilmiş | −%5,66 |
| `turev` | Türev finansal işlemlerden K/Z, 6A26 | BDR gelir tablosu · xl 48 | −47.846 |
| `kambiyo` | Kambiyo işlemleri K/Z, 6A26 | BDR ticari K/Z dipnotu | +48.690 |

S28 sağ kart (YP ağırlığı): `yp_aktif` · `yp_mevduat` · `yp_kredi` · **`tk_yppay`** (REV-11: PP dahil, etiket "YP toplam fonlama").
⚠️ Türev zararı ile kambiyo kârı birbirini götürür — bir korunma bacağıdır, spekülatif pozisyon değildir.

---

### 5.13 · Likidite · *S30 rayı (R6)*

| Alan | Tanım | Kaynak | KT |
|---|---|---|---:|
| `lcr` · `lcr_yp` | Likidite karşılama oranı (toplam · YP) — bankanın açıkladığı değer | **BDR** (MCP'de yok) | %202,0 · %285,4 |
| `likit` | `(Finansal Varlıklar (Net) − Türev FV) ÷ Toplam Aktifler` | BDR bilanço · xl 430 | %46,2 |
| `l1` · `l13` · `l312` · `l15` · `l5` | Kalan vadeye göre likidite açığı/fazlası: 1 aya kadar · 1–3 ay · 3–12 ay · 1–5 yıl · 5 yıl+ | BDR dipnot "Aktif ve Pasif Kalemlerin Kalan Vadelerine Göre Gösterimi" (xl 2120–2139) | −123.345 · 47.364 · 256.206 · 242.243 · 6.912 |
| `l1_pay` | `l1 ÷ aktif` | türetilmiş | −%8,4 |

⚠️ LCR'nin paydası açıklanmadığı için **paçalı yazılmaz.** Vade merdiveni slaytı (S29) bu sürümde sunumdan
çıkarılmıştır; LCR S30'un rayında durur. Merdivende vadesiz ve dağıtılamayan sütunlar yoktur (beş dilimin
toplamı sıfır değildir).

---

### 5.14 · Sermaye · *S30 · S31 · S46*

| Alan | Tanım / formül | Kaynak | KT |
|---|---|---|---:|
| `syr` · `syr_ara` | Sermaye yeterliliği rasyosu (%) | **BDR** (MCP 2026-06-30'da `null`) | 18,00 · 22,11 |
| `syr_bps` | `(syr − syr_ara) × 100` | türetilmiş | −411 |
| `syr_fazla` | `syr − 12` (yasal asgari %12) | türetilmiş | 6,00 puan |
| `cet1` · `cet1_ara` · `cet1_bps` | Çekirdek sermaye yeterliliği oranı | BDR | 15,40 · 19,11 · −371 |
| `ana` | Ana sermaye yeterliliği oranı | BDR | 15,40 |
| `kaldirac` | **Basel III kaldıraç oranı** (ana sermaye ÷ toplam risk tutarı) | **Yalnız BDR** | %6,29 *(ekranda yok)* |
| `basit` | **Basit kaldıraç** = `ozkaynak ÷ aktif` | türetilmiş | %9,42 |
| `rwa` · `rwa_ytd` | **Toplam** risk ağırlıklı varlıklar (kredi + piyasa + operasyonel risk) | BDR SYR tablosu · MCP·m `Toplam Risk Ağırlıklı Varlıklar (RAV)` (birebir) | 861.892 · +%39,5 |
| `dens` · `dens_ara` · `dens_bps` | **RAV yoğunluğu** = `rwa ÷ aktif` | türetilmiş | %58,5 · %45,7 · +1.283 |
| `rorwa` | `kar_ttm ÷ [(rwa(Haz-26) + rwa(Ara-25)) / 2]` — **⚠️ kuraldan sapar, aşağıya bakın** | türetilmiş | %6,11 |

> ⚠️ **Düzenleyici esneklik kırılması — 2025 ile 2026 SYR karşılaştırılamaz.** BDDK'nın 11286 sayılı
> kararıyla kredi riskine esas tutarda 28.06.2024 sabit kuru kullanma imkânı **01.01.2026'dan itibaren
> kaldırıldı.** Altı bankanın tamamı Ara-25'te imkânı kullandı, Haz-26'da hiçbiri kullanmadı. RAV
> yoğunluğu altısında +906 ile +1.283 bps arası sıçradı. SYR düşüşü **organik risk alımı olarak yorumlanmaz.**

> ⚠️ **`rorwa` paydası iki banka grubunda farklı kurulmuş — bilinen sapma (§8).**
> Altı çekirdek bankada (KT, QNB, DZB, TEB, VK, ZK) ortalama RAV **Haz-26 ile Ara-25'in** ortalamasıdır;
> Tier-1 dörtlüsünde (AKB, GAR, İŞ, YKB) ise §4.2 kuralındaki **Haz-26 ile Haz-25'in** ortalamasıdır
> (MCP `RORWA` DAX'i de budur: `Net Dönem Karı (Y) ÷ Ortalama RAV`, `PARALLELPERIOD −12 ay`).
> Ekrandaki altı bankadan üçü etkilenir:
>
> | Banka | Ekranda | Kurala göre (= MCP) | Fark |
> |---|---:|---:|---:|
> | Kuveyt Türk | %6,11 | **%6,53** | +42 bps |
> | QNB | %3,98 | **%4,04** | +6 bps |
> | Denizbank | %4,32 | **%4,55** | +23 bps |
> | Akbank · Garanti · Yapı Kredi | %3,10 · %4,19 · %2,55 | aynı | 0 |
>
> KT ortalama RAV: ekranda (861.892 + 618.050) / 2 = 739.971 · kurala göre (861.892 + 523.878) / 2 = 692.885.
> **Sıralama değişmez** (KT · DZB · GAR · QNB · AKB · YKB). Düzeltme için `B[i].rorwa` alanının üç bankada
> güncellenmesi yeterlidir; RORWA S31 KPI şeridinde ve S46 çipinde görünür.
>
> ℹ️ MCP measure'ının ham kalem adı `Kredi Riskine Esas Tutar: Toplam` olsa da değeri **toplam RAV**'dır —
> `rwa` ile Haz-26 ve Ara-25'te birebir aynı, `RWA Density` de `dens` ile aynı (%58,54 · %45,71).

S31 rakip paçalı RAV yoğunluğu (sayfa içi): `Σ rwa ÷ Σ aktif` (QNB + DZB) = **%77,1**.

---

### 5.15 · Marj ve fiyatlama · *S33 · S34*

**Payda sözleşmeleri (MCP DAX'inden birebir)**

```
Getirili aktifler  = TCMB hesabı (TP + YP) + Bankalar + Para piyasalarından alacaklar
                     + GUD-K/Z + GUD-DKG + İtfa edilmiş maliyet + Satılmaya hazır + Vadeye kadar
                     + Türev FV + Riskten korunma amaçlı türev FV
                     + Toplam brüt krediler − Beklenen zarar karşılıkları (bilanço)        ← kredi NET
Maliyetli pasifler = VADELİ mevduat + Alınan krediler + PP borçlar + İhraç MK (net)
                     + GUD-K/Z finansal yük. + Türev finansal yük. + Faktoring borçları
                     + Kiralama borçları + Sermaye benzeri krediler                         ← vadesiz YOK
Kaynağa verilen faiz (kâr payı) gideri = Mevduata + Kullanılan kredilere + İhraç MK'ye verilen
                                          (xl 30 + 31 + 33)                                 ← PP faizi YOK
```

| Alan | Tanım / formül | Kaynak | KT |
|---|---|---|---:|
| `nim` | **Net faiz (kâr payı) marjı** = `Net faiz geliri (TTM) ÷ Ort. getirili aktifler` | MCP·m `Net Faiz (Kar Payı) Marjı 2` mantığı · xl 36 | %6,81 |
| `nim_swap` | **Swap düzeltilmiş** = `(Net faiz geliri + Türev K/Z) (TTM) ÷ Ort. getirili aktifler` | xl 36 + xl 48 | %3,77 |
| `nim_duz` | **Düzeltilmiş (tüm ticari K/Z)** = `(Net faiz geliri + Net ticari K/Z) (TTM) ÷ Ort. getirili aktifler` | MCP·m `Düzeltilmiş Net Faiz (Kar Payı) Marjı` · xl 36 + 46 | %8,06 |
| `swap_bps` | `(nim_swap − nim) × 10.000` | türetilmiş | −303 |
| `nfg` · `nfg_yoy` | Net faiz (kâr payı) geliri 6A26 · YoY | MCP·m `Net Faiz Geliri/Gideri` · xl 36 | 45.444 · +%66,4 *(ekranda yok)* |
| `fg_ttm` | Faiz (kâr payı) gelirleri, TTM | xl 15 | 190.726 |
| `ort_ga` | Ortalama getirili aktifler (2 nokta) — **BDR'den kurulu** | türetilmiş | 1.169.842 |
| `getiri` | **Getirili aktif getirisi** = `fg_ttm ÷ ort_ga` | MCP·m `Faiz (Kar Payı) Getirili Aktiflerin Getirisi` mantığı | %16,30 |
| `maliyet` | **Maliyetli pasif maliyeti** = `Kaynağa verilen faiz gideri (TTM) ÷ Ort. maliyetli pasifler` | MCP·m `Faiz (Kar Payı) Maliyetli Pasiflerin Maliyeti` | %14,44 |
| `spread` | `((1 + getiri) ÷ (1 + maliyet) − 1) × 10.000` — geometrik | türetilmiş | +163 |
| `spread_pp` | Aynı, maliyet payına **PP faiz gideri (xl 32) eklenerek** | türetilmiş | −186 *(ekranda yok)* |
| `kredi_getiri` | Kredilerin paçal getirisi = kredilerden alınan faiz (TTM) ÷ ort. kredi | MCP·m `Kredilerin Paçal Getirisi` | %19,11 |
| `mevduat_maliyet` | Mevduatın paçal maliyeti = `Kaynağa verilen faiz gideri (TTM) ÷ Ortalama Kaynak` | MCP·m `Mevduatın Paçal Maliyeti` | %8,81 |
| `vadeli_maliyet` | `(TP + YP(altın hariç) + kıymetli maden vadeli faiz, TTM) ÷ (ort. altındışı vadeli + ort. KM vadeli)` | MCP DAX tarifi | %22,38 *(ekranda yok)* |
| `km_spread` | **Fiyatlama makası** = `((1 + kredi_getiri) ÷ (1 + mevduat_maliyet) − 1) × 10.000` | türetilmiş | +947 |

> ⚠️ **NIM adı tuzağı.** MCP'nin `Net Faiz (Kar Payı) Marjı` measure'ı paydaya **ortalama toplam aktifleri**
> alır; rapordaki NIM **`Marjı 2`**'dir (÷ ortalama getirili aktifler).
> ⚠️ **"Swap düzeltmesi" yalnız türev K/Z'dir** (xl 48). MCP'nin `Düzeltilmiş …` measure'ları tüm ticari
> K/Z'yi (türev + kambiyo + sermaye piyasası, xl 46) ekler — ekranda "düzeltilmiş (tüm ticari K/Z)" diye ayrılır.
> ⚠️ **Negatif/düşük spread üç asimetriyle okunur:** (1) getirili aktif düşük getirili YP zorunlu karşılık
> içerir, (2) maliyetli pasif vadesiz mevduatı içermez, (3) maliyet payı PP faizini içermez ama payda PP
> borcunu içerir.
> ⚠️ **KT'nin getiri/NIM/sürükleme rakamları BDR'den kurulmuştur, MCP'den değil** — §5.16 sonundaki not.
> ⚠️ Yapı Kredi'nin maliyetli pasif maliyeti: pay `Kaynağa Verilen Faiz Gideri (Y)` olmalı (toplam faiz gideri
> değil). Doğrusu %20,62 · spread **+187 bps** (eski −83 bps hatalıydı).

---

### 5.16 · Zorunlu karşılık sürüklemesi · *S35*

**Etiket: türetilmiş, örtük.** Zorunlu karşılıklar **ücretlendirilir** (gelir tablosunda ayrı satır, her iki
banka tipinde dolu); fiilen getirisiz olan **YP bacağıdır.** "Sıfır getirili" ifadesi kullanılmaz.

| Alan | Tanım / formül | Kaynak | KT |
|---|---|---|---:|
| `zk_gelir` | Zorunlu karşılıklardan alınan faiz (kâr payı), **TTM** | BDR gelir tablosu · MCP·k · xl 17 | 17.726 |
| `zk_pay` | `zk_gelir ÷ fg_ttm` | türetilmiş | %9,3 |
| `tcmb` | TCMB hesabı (TP + YP), dönem sonu | BDR dipnot "Nakit Değerler ve TCMB" · xl 1528 (TP 1529 · YP 1530) | 282.932 |
| `tcmb_yp` · `tcmb_tp` | YP tutarı · TP payı = `(tcmb − tcmb_yp) ÷ tcmb` | aynı | 216.961 · %23,3 |
| `ort_tcmb` | `(tcmb(Haz-26) + tcmb(Haz-25)) / 2` | türetilmiş | 247.743 |
| `tcmb_pay` | **`ort_tcmb ÷ ort_ga`** — TCMB'nin **ortalama getirili aktif** içindeki payı | türetilmiş | **%21,2** |
| `tcmb_getiri` | **Örtük TCMB getirisi** = `zk_gelir ÷ ort_tcmb` | türetilmiş | %7,15 |
| `zk_tp_getiri` | Yalnız TP bacağının örtük getirisi | türetilmiş | %29,7 *(ekranda yok)* |
| `getiri_zk` | **ZK hariç getiri** = `(fg_ttm − zk_gelir) ÷ (ort_ga − ort_tcmb)` | türetilmiş | %18,76 |
| `zk_bps` | **Sürükleme** = `−(getiri_zk − getiri) × 10.000` | türetilmiş | **−246** |

**Ayrıştırma kimliği** (10/10 bankada ±1 bps):

```
                 w
Sürükleme = ───────── × ( getiri − tcmb_getiri )          w = tcmb_pay
               1 − w
KT:  (0,212 ÷ 0,788) × (16,30 − 7,15) puan = 246 bps
```

İlk terim **bloğun büyüklüğünü**, ikinci terim **getiri farkını** taşır. S35'teki `TCMB hesabı / getirili
aktif` çipi birinci terimi gösterir (REV-12/13): çubuk = `tcmb_pay`, ikinci değer = `ort_tcmb`.

> ⚠️ `tcmb_pay` **toplam aktif payı değildir.** `tcmb ÷ aktif` = %19,2 (dönem sonu, toplam aktif) ayrı bir
> büyüklüktür ve formülde yeri yoktur.

> ⚠️ **KT'de MCP ile fark — açıklandı.** MCP 2026-06-30 kaydında KT'nin **TCMB hesabı TP bacağı (65.971)
> eksiktir** (`Zorunlu Karşılıklar` measure'ı 216.961 = yalnız YP). Bu yüzden MCP'nin getirili aktifi
> 1.304.487 (aktifin %88,6'sı — yedi çeyrektir %92,5–93,9 bandındaydı) ve getirisi %16,78 çıkar.
> Eksik bacak eklenince: `(1.304.487 + 65.971 + 969.227) / 2 = 1.169.842` = **`ort_ga` birebir.**
> Analizin %16,30 · %6,81 · −246 bps değerleri doğrudur; MCP'den yeniden hesaplanırsa %16,78 · %7,00 · −268 bps
> çıkar ve **yanlıştır.**

⚠️ `TCMB hesabı` zorunlu karşılık ile serbest hesabı **birlikte** taşır; örtük getiri bir **proxy**'dir,
açıklanmış ücretlendirme oranı değildir.

---

### 5.17 · Faaliyet giderleri · *S36 · S37 · S38 · S39 · S40 · S41 · S43*

**Gider büyümesi yıllıklandırılmaz** — 6A26 kümülatif ile 6A25 kümülatif doğrudan karşılaştırılır (§4.1).

| Alan | Tanım / formül | Kaynak | KT |
|---|---|---|---:|
| `pg_6m26` · `pg_6m25` | Personel giderleri, 6A | BDR gelir tablosu · MCP·k `Personel Giderleri (-)` · xl 44 | 12.426 · 8.776 |
| `dg_6m26` · `dg_6m25` | Diğer faaliyet giderleri, 6A | BDR gelir tablosu · MCP·k `Diğer Faaliyet Giderleri (-)` · xl 53 | 11.322 · 7.103 |
| `opex` · `opex_6m25` | **OPEX** = personel + diğer faaliyet giderleri | MCP·m `Diğer Faaliyet Giderleri (OPEX)` (adına rağmen ikisinin toplamı) | 23.748 · 15.879 |
| `opex_yoy` · `pg_yoy` · `dg_yoy` | YoY | türetilmiş | +%49,6 · +%41,6 · +%59,4 |
| `*_yoy_reel` | `(1 + yoy) ÷ 1,3211 − 1` (**TÜFE YoY**) | türetilmiş | +%13,2 · +%7,2 · +%20,7 |
| `pg_pay_opex` | `pg ÷ opex` | türetilmiş | %52,3 |
| `gelir_yoy` | **Faaliyet gelirleri** YoY (aşağıdaki tanım) | türetilmiş | +%40,4 |
| `jaws_puan` | **Makas** = `(gelir_yoy − opex_yoy) × 100` | türetilmiş | −9,1 puan |
| `mgr` · `mgr25` | **Maliyet / gelir** = `opex ÷ faaliyet gelirleri` (6A26 · 6A25) | MCP·m `Standart Maliyet Gelir Rasyosu` | %35,9 · %33,7 |
| `mgr_degisim_bps` | `(mgr − mgr25) × 10.000` | türetilmiş | +219 |
| `opex_ort_aktif` | `2 × opex ÷ ortalama aktif` (yarıyıl ×2) | türetilmiş | %3,77 *(ekranda yok)* |

```
Faaliyet gelirleri (MCP·m `Faaliyet Gelirleri`) =
      Net faiz (kâr payı) geliri      xl 36   45.444
    + Net ücret ve komisyon geliri    xl 37   12.305
    + Ticari K/Z (net)                xl 46    5.295
    + Temettü + diğer faaliyet gel.   xl 45 + xl 50    3.075
    = 66.119   (KT 6A26)          → mgr = 23.748 ÷ 66.119 = %35,92
```

⚠️ Faaliyet gelirleri **karşılık giderleri öncesidir.** `mgr` 6A kümülatiftir; MCP'nin aynı measure'ı 2025-12-31'de 12 aylık
değer verir (KT %33,96) — `mgr25` ise 6A25'tir (%33,73). Karıştırılmaz.
⚠️ Tier-1 paçalı maliyet/gelir (S43 notu) sayfa içinde: `Σ opex ÷ Σ (opex / mgr)` = %53,5 (dört banka; ekranda üç).

**Kadro ve birim gider (S39 · S40 · S41)**

| Alan | Tanım | Kaynak | KT |
|---|---|---|---:|
| `personel` · `personel_haz25` | Personel sayısı (dönem sonu) — **her zaman solo** | BDR "Genel Bilgiler" · MCP·m `Personel Sayısı` · xl 2184 | 6.432 · 6.309 |
| `sube` · `sube_haz25` | Yurt içi şube sayısı | MCP·m `Şube Sayısı` · xl 2183 | 452 · 452 |
| `personel_yoy` · `personel_degisim_adet` · `sube_degisim_adet` | Değişim | türetilmiş | +%1,9 · +123 · 0 |
| `sube_pers` | `personel ÷ sube` | türetilmiş | 14,2 |
| `opp26` · `opp25` | **Personel başına OPEX** = `opex ÷ personel × 1.000` (**bin TL, 6A**) | türetilmiş | 3.692 · 2.517 |
| `opp_yoy` · `opp_reel` | YoY · TÜFE YoY ile reel | türetilmiş | +%46,7 · +%11,0 |
| `pgp26` · `pgp25` | **Personel başına personel gideri** = `pg ÷ personel × 1.000` | türetilmiş | 1.932 · 1.391 |
| `pgp_yoy` · `pgp_reel` | YoY · reel | türetilmiş | +%38,9 · +%5,1 |
| `opex_per_sube` | `opex ÷ sube × 1.000` (bin TL, 6A) | türetilmiş | 52.540 *(ekranda yok)* |

**Personel gideri ayrıştırması (S39) — yalnız personel giderine uygulanır**

```
(1 + pg_yoy) = (1 + kadro değişimi) × (1 + kişi başı personel gideri değişimi)

kadro etkisi  = Δpersonel × pgp25                 = 123 × 1,391    =   171 mn TL → 171 ÷ 8.776 = 1,9 puan
ücret etkisi  = personel_haz25 × Δpgp             = 6.309 × 0,541  = 3.412 mn TL →            38,9 puan
çapraz etki   = Δpersonel × Δpgp                  = 123 × 0,541    =    67 mn TL →             0,8 puan
toplam                                                                   = 3.650 mn TL = pg_yoy  41,6 puan
```

Alanlar: `pg_ayr_kadro_puan` · `pg_ayr_ucret_puan` · `pg_ayr_capraz_puan` · `pg_ayr_*_mn`.
⚠️ `k_kadro` · `k_birim` · `k_capraz` **eski (OPEX bazlı) ayrıştırmadır**; Tier-1 dörtlüsünde iç tutarsız, **kullanılmaz.**

---

### 5.18 · KT gider kırılımı · *S42 — yalnız KT*

**Kaynak: KT iç muhasebe kayıtları (168 hesap)**, 11 kaleme ve dört bloğa gruplanmış — proje dosyası
`claude/10_KT_diger_faaliyet_gideri_kirilimi.md`. **BDR değildir;** rakip bankalar için karşılığı yoktur.

| Yapı | Veri | Açıklama |
|---|---|---|
| `GDRB` | `[blok_id, blok_adı, [[kalem, 6A26, 6A25], …]]` × 4 blok | Büyüme yatırımı · Hacme bağlı (mekanik) · Risk ve tahsilat · **İşletme ve diğer** (veri modelinde eski adı "Enflasyon / takdir"; REV-14 ile ekranda yeniden adlandırıldı) |
| `GDRP` | `[[kalem, 6A26, 6A25], …]` × 7 | Promosyon giderleri (THY Miles&Smiles, emekli maaş, kart, …) |
| `GDRT` | `[11.321,6 · 7.101,8]` | Diğer faaliyet giderleri toplamı (iç kayıt) — BDR xl 53 ile mutabık (11.322 · 7.103) |
| `GDRDELTA` | 4.219,8 | Artış, mn TL |
| `KT_GIDER_REV15` | `ayristirma` · `kartBasim` · `musteriKazanimAraToplam` · `kontrol` | REV-15: "Pazarlama, promosyon ve kart" kalemini **Promosyon ve kart** (1.498,1 · 638,0) + **Reklam ve tanıtım** (430,0 · 285,6) olarak ikiye böler |

```
S42 KPI şeridi:  artış = 11.321,6 − 7.101,8 = +4.219,8 mn TL · YoY = 4.219,8 ÷ 7.101,8 = +%59,4
Kelebek grafik:  sol = tutar (6A26), sağ = YoY %, satırlar tutara göre sıralı (REV-14)
Promosyon kartı: 7 kalem (1.366,7 · 576,3) + "Kart basım ve dağıtım" sabit son satır (131,4 · 61,7) — promosyon değildir
Kimlikler:       1.366,7 + 430,0 + 131,4 = 1.928,1  ·  576,3 + 285,6 + 61,7 = 923,6   (blok ve genel toplam değişmez)
```

---

### 5.19 · Verimlilik ve ücret geliri · *S44 · S45*

| Alan | Tanım / formül | Kaynak | KT |
|---|---|---|---:|
| `sube_kar` | `kar_ttm ÷ sube × 1.000` (bin TL, **TTM**) | türetilmiş | 100.044 |
| `pers_kar` | `kar_ttm ÷ personel × 1.000` (bin TL, TTM) | türetilmiş | 7.030 |
| `sube_kredi` | `kredi ÷ sube × 1.000` (bin TL) | türetilmiş | 1.677.051 *(ekranda yok)* |
| `nuk` · `nuk_yoy` | Net ücret ve komisyon gelirleri, 6A · YoY | BDR gelir tablosu · MCP·m `Net Ücret ve Komisyon Gelirleri/Giderleri` · xl 37 | 12.305 · +%79,3 |
| `nuk_opex` | **OPEX'i karşılama** = `nuk ÷ opex` | MCP·m `Net Ücret ve Komisyonlar/Faaliyet Giderleri` mantığı | %51,8 |
| `ucret_pay` | `nuk ÷ faaliyet gelirleri` | türetilmiş | %18,6 |

S44 bir dağılım grafiğidir: x = `mgr`, y = `pers_kar`. Tier-1 paçalı ücret karşılama: `Σ nuk ÷ Σ opex` = %86,5 (dört banka).
⚠️ Şube ve personel **her zaman solo**; verimlilik rasyolarının paydası konsolide analizde de soloda kalır.

---

### 5.20 · Kârlılık · *S00 · S46 · S48*

| Alan | Tanım / formül | Kaynak | KT |
|---|---|---|---:|
| `kar26` · `kar25` | Net dönem kârı, 6A26 · 6A25 | BDR gelir tablosu · MCP·m `Net Dönem Karı/Zararı` · xl 81 | 23.775 · 18.917 |
| `kar_yoy` · `kar_yoy_reel` | YoY · `(1 + yoy) ÷ 1,3211 − 1` | türetilmiş | +%25,7 · −%4,9 |
| `kar_ttm` | `kar26 + kâr(FY2025) − kar25` | MCP·m `Net Dönem Karı/Zararı (Y)` | 45.220 |
| `q1` · `q2` | **İzole çeyrek:** `q1` = 3A26 kümülatif · `q2` = `kar26 − q1` | 31.03.2026 BDR / MCP 2026-03-31 | 12.135 · 11.640 |
| `roaa` · `roaa25` | `kar_ttm ÷ ortalama aktif` (2 nokta) · aynı rasyo **31.12.2025**'te (FY2025) | MCP·m `ROAA` (altı bankada birebir) | %3,59 · %3,66 |
| `roae` · `roae25` | `kar_ttm ÷ ortalama özkaynak` · FY2025 | MCP·m `ROAE` | %38,32 · %39,65 |
| `rorwa` | §5.14 — **bilinen sapma** | türetilmiş | %6,11 (kurala göre %6,53) |
| `pay_kar` | Set içi kâr payı (§4.8) | sayfa içi | %10,97 |

```
KT ROAA = 45.220 ÷ [(1.472.314 + Haz-25 aktif) / 2] = 45.220 ÷ 1.260.143 = %3,588
```

⚠️ `roaa25` / `roae25` **Haz-25 değil, 31.12.2025 değeridir** (MCP 2025-12-31: %3,66 · %39,65). S46'daki boş nokta
"2025 yıl sonu" olarak okunur. RORWA için 2025 değeri yoktur (`g: null`).

---

### 5.21 · Gelir tablosunun bileşimi · *S47*

| Alan | Tanım / formül | Kaynak | KT |
|---|---|---|---:|
| `vok` | Sürdürülen faaliyetler vergi öncesi kâr, 6A26 | BDR gelir tablosu · xl 58 | 31.338 |
| `vergi` · `vergi25` | **Efektif vergi** = `1 − kar26 ÷ vok` (6A26 · 6A25) | türetilmiş (= xl 59 ÷ xl 58) | %24,1 · %23,7 |
| `istirak` | Özkaynak yöntemi uygulanan ortaklıklardan K/Z | BDR gelir tablosu · MCP·k · xl 56 | 0 |
| `istirak_pay` | `istirak ÷ vok` | türetilmiş | %0 |
| `istirak_yontemi` | İştiraklerin solo muhasebe esası (metin) | BDR muhasebe politikaları | "maliyet değeri" |
| `sk_iptal` · `sk_iptal_pay` | Serbest karşılık **iptali** (gelir) · `sk_iptal ÷ vok` | BDR karşılık / diğer faaliyet geliri dipnotu | 0 · %0 |

S47 çubuğu vergi öncesi kârı %100'e normalize eder: **çekirdek bankacılık** = `1 − istirak_pay − sk_iptal_pay` · iştirak geliri · karşılık iptali.

⚠️ **TMS 27 esas farkı.** Solo raporda iştirakleri **özkaynak yöntemiyle** taşıyan bankalarda (QNB, DZB, AKB, GAR, İŞ, YKB)
iştirak kârı solo kâra girer; **maliyet değeriyle** taşıyanlarda (KT, TEB, VK, ZK) girmez. Bu bir **raporlama esası farkıdır**,
iş modeli farkı değil. ROAE karşılaştırmasında ayrıştırılır; ayrıştırılmış seriye "aynı raporlama esasına getirilmiş"
denir, "düzeltilmiş" denmez. (İş Bankası'nda vergi öncesi kârın %96,2'si iştirak gelirinden, efektif vergi −%4,3.)

---

### 5.22 · Yıl sonu kâr tamponu · *S49*

**Tanım:** gelecek dönem kârına aktarılabilecek muhasebesel yastık.

```
tampon     = sk + tufex
tampon_pay = tampon ÷ kar26
```

| Alan | Tanım | Kaynak | KT |
|---|---|---|---:|
| `sk` · `sk_pay` | **Serbest karşılık bakiyesi** (dönem sonu) · `sk ÷ kar26` | BDR dipnotu *"Muhtemel riskler için ayrılan serbest karşılıklara ilişkin bilgiler"* | 0 · %0 |
| `tufex_var` | Bankanın TÜFE'ye endeksli MK değerlemesinde kullandığı **yıllık TÜFE varsayımı** (%) | BDR muhasebe politikaları / menkul değerler dipnotu | `null` |
| `tufex` · `tufex_pay` | **TÜFEX tamponu** — varsayım ile gerçekleşen TÜFE farkının kâra etkisi · `tufex ÷ kar26` | aşağıdaki iki yoldan biri | 0 |
| `tufex_kaynak` | `'aciklanmis'` · `'turetilmis'` · `null` | — | `null` |

**TÜFEX tamponunun iki kaynağı**

| Yol | Bankalar | Tarif |
|---|---|---|
| **Açıklanmış** | QNB (varsayım %25 → **2.699**) · Denizbank (%29 → **1.514**) | BDR cümlesi birebir: *"…net dönem kârı X TL artarak … olacaktı"* |
| **Türetilmiş** | Akbank (%30 → 2.397) · Garanti (%27 → 2.407) · Yapı Kredi (%30 → 2.203) · İş (%29,94 → 714) · TEB (%27 → 678) | `(%32,11 − varsayım) × (açıklanan duyarlılık ÷ duyarlılık puanı)` — örn. Akbank `(32,11 − 30) × 1.136 = 2.397` |
| **Yapısal sıfır** | KT · Vakıf Katılım · Ziraat Katılım | KT ve VK portföyünde TÜFE'ye endeksli MK yok; ZK'nın TÜFE'ye endeksli kira sertifikaları Hazine'nin açıkladığı endeksle değerlenir → tahmin farkı oluşmaz |

**Serbest karşılık (ekrandaki altı banka):** QNB 3.500 · Denizbank 8.700 · Akbank / Garanti / Yapı Kredi / KT 0.
Ekrandaki tamponlar: Denizbank 10.214 (kârının %29,5'i) · QNB 6.199 (%21,2) · Garanti 2.407 · Akbank 2.397 · Yapı Kredi 2.203 · **KT 0.**

⚠️ **Bilinen taban farkı.** Açıklanmış değerler *"30 Haziran 2026 için geçerli referans endekse"* göre ölçer (Hazine
kılavuzu gereği iki ay önceki TÜFE'ye dayanır); türetilmiş değerler gerçekleşen yıllık TÜFE'yi (%32,11) kullanır.
Türetilmiş rakamlar **büyüklük mertebesi** göstergesidir. `tufex_kaynak` alanı ayrımı taşır; S49'un bu sürümü iki
kaynağı aynı renkte çizer.
⚠️ Serbest karşılık BDDK formatında varsa dipnotta zorunludur; **yokluğu sıfır okunur.** Tier-1'de kanıt gücü farklıdır
(Akbank açık beyan; İş Bankası en zayıf — yalnız politika cümlesi).
⚠️ "Tampon sıfır" KT için olumsuz bir kâr kalitesi bulgusu değildir: raporlanan kâr şartsızdır; dört büyük özel bankada da
serbest karşılık yoktur.

---

### 5.23 · Denetçi görüşü · *ekranda yok*

| Alan | İçerik | KT |
|---|---|---|
| `gorus` · `gorus_ok` | Bağımsız denetçi / sınırlı denetim sonucu (metin) · olumlu mu | "Temiz" · `true` |

Ekrandaki altı bankadan **QNB "sınırlı olumlu (şartlı)"** ve **Denizbank "şartlı sonuç"** — şart konusu serbest karşılıktır.
Kaynak yalnız BDR (sayısal veri değil).

---

## 6 · Slayt × ölçüm haritası

Ekrandaki 43 slayt, gösterim sırasıyla. **Çipler** aynı kartta görünüm değiştiren düğmelerdir. Her veri slaytının
sağında bir KPI rayı vardır (`rail` dizileri, R1–R9).
ℹ️ REV-17'den beri altı banka her slaytta sabittir. Kodda kalan **Tier-1 anahtarları** (`t1On`, `t1Ctl`) filtreyi
değiştirmez, çünkü `banks()` her bankada `tier1 = false` yapar.

| # | Etiket | Başlık | Ana ölçümler (alan) | Çip / kontrol | Ek veri |
|---:|---|---|---|---|---|
| 1 | S00 | Kapak | `kar26` · `kar_yoy` · `roaa` · `roae` · `pay` | — | |
| 2 | S03 | Bölüm I · Bilanço | — | — | |
| 3 | S04 | Altı aylık büyüme | `aktif` · `kredi` · `mevduat` · `tf_lvl` · `ozkaynak` + `_ytd` / reel | **Tutar** \| Büyüme · Nominal \| Reel · metrik çipleri: Aktif · Kredi · Mevduat · Toplam fonlama · Özkaynak | sayfa içi `tf_*` (REV-16) |
| 4 | S05 | Pazar payı | `pay` (Ara-25 → Haz-26, set içi) | — | sayfa içi |
| 5 | S06 | Aktif kompozisyonu | `akt_*` · `akt_*_bps` | Ara-25 \| Haz-26 · Pay \| Tutar · Bankalar \| Paçal | `KT_KOMP_ARA25` (REV-01) |
| 6 | S07 | Kredi portföyü | `kp_tuketici` · `kp_tuzel_lh` · `kp_mali` · `_bps` | Raporlanan \| Genişletilmiş · Pay \| Tutar · Bankalar \| Paçal | `KPLH` |
| 7 | S08 | Tüketici kredileri | `tuk_*` · `kp_tuketici_ytd/_reel` | Pay \| Tutar · Bankalar \| Paçal | `COMPD.t` |
| 8 | S09 | NPL seviye ve yön | `npl_ara` → `npl_o` · `npl_d_bps` | — | |
| 9 | S10 | Düzeltilmiş NPL | `npl_o` · `npl_o_duz` · `npl_bps_duz` · `npl_d_bps_duz` | NPL \| Bozulma | |
| 10 | S11 | Donuk alacak hareketi | `npl_acilis` → `npl_intikal` · `npl_tahsilat` · `npl_terkin` · `npl_satis` → `npl_kapanis` (şelale) | banka seçici | `NPLX` |
| 11 | S13 | Net formasyon | `nfr` · `npl_netform` · `npl_cikis_pay(_25)` | — | paçal sayfa içi |
| 12 | S12 | İntikal ve tahsilat | `npl_intikal_r` · `npl_tahsilat_r` · `npl_tah_int` | — | |
| 13 | S14 | Risk merdiveni | Grup 1 (artık) · `g2` · `npl` · `npl_kars` · `g2_kars` | — | |
| 14 | S15 | Fonlama kompozisyonu | mevduat · alınan kredi · ihraç MK · PP | Kalem \| Mevduat / dışı · Ara-25 \| Haz-26 | `KT_FONLAMA` (REV-03) |
| 15 | S16 | Vade kırılımı | `vadesiz` · `vadeli` · mevduat dışı · altın | Mevduat \| Toplam fonlama \| Altın hariç | `KT_VADE` (REV-04) |
| 16 | S18 | TL cari hesap tabanı | `tp_cari_pay` · `_ara25` · `_degisim_bps` | TL mevduat \| Toplam TL fonlama | `KT_TLCARI` (REV-05) |
| 17 | S19 | Altın büyüklük ve pay | `altin` · `altin_ytd` · `altin_pay_mev` · `altin_pay_ara` | — | |
| 18 | S22 | TP / YP kompozisyonu | `*_tp` · `*_yp` · `*_yppay` · `*_tp_ytd_reel` · `*_yp_ytd_usd` | Kredi · Mevduat · Toplam fonlama | |
| 19 | S24 | Dolarizasyon | `tk_yppay_haz25` → `_ara25` → `tk_yppay` (eğim) | — | |
| 20 | S25 | Kredi / kaynak | `ktk_tp` · `ktk_yp` · `ktk_top` · `kredi_kaynak` | — | |
| 21 | S26 | YP fonlama fazlası | `tk_yp − kredi_yp` · `tcmb_yp` (soluk) · `altin` | — | sayfa içi (REV-08) |
| 22 | S28 | Kur pozisyonu | `nbp` · `nnp` · `ngp` · `ngp_ozk` · `turev` · `kambiyo` · YP ağırlıkları | — | |
| 23 | S30 | SYR köprüsü | `syr_ara` → `syr` · `syr_fazla` · ray: `lcr` · `lcr_yp` | — | |
| 24 | S31 | RAV ve sermaye kalitesi | `dens` · `dens_ara` · `syr` · `ana` · `cet1` · `rorwa` | — | rakip paçalı sayfa içi |
| 25 | S32 | Bölüm II · Gelir tablosu | — | — | |
| 26 | S33 | Üç marj | `nim` · `nim_swap` · `nim_duz` | Marj \| Kredi / toplam fonlama (`ktk_tp` · `ktk_yp`) | |
| 27 | S34 | Fiyatlama makası | `maliyet` → `getiri` · `spread` · `kredi_getiri` · `mevduat_maliyet` · `km_spread` | Fiyatlama makası \| Kredi TP–YP \| Kredi portföyü | |
| 28 | S35 | ZK sürüklemesi | `zk_bps` · `getiri` · `getiri_zk` · `tcmb_getiri` · `tcmb_tp` | bps \| TCMB hesabı / getirili aktif (`tcmb_pay`) | |
| 29 | S36 | Gider ve TÜFE | `opex_yoy` · `pg_yoy` · `dg_yoy` vs TÜFE %32,11 | — | |
| 30 | S38 | Reel gider büyümesi | `*_yoy_reel` | OPEX · Personel · Diğer | |
| 31 | S40 | Personel başına gider | `opp_yoy` · `opp_reel` · `pgp_yoy` · `pgp_reel` | Personel başına OPEX \| personel gideri | |
| 32 | S39 | Kadro mu ücret mi | `pg_ayr_*` | — | |
| 33 | S41 | Kadro ve şube | `personel` · `sube` · `_degisim_adet` · `sube_pers` | — | |
| 34 | S42 | KT gider kırılımı | `GDRB` · `GDRP` · `GDRT` | — | `KT_GIDER_REV15` (REV-14/15) |
| 35 | S37 | Makas | `gelir_yoy` · `opex_yoy` · `jaws_puan` | — | |
| 36 | S43 | Maliyet / gelir | `mgr25` → `mgr` · `mgr_degisim_bps` | — | Tier-1 paçalı sayfa içi |
| 37 | S44 | Verimlilik konumlaması | x `mgr` · y `pers_kar` · `sube_kar` | — | |
| 38 | S45 | Ücret ve komisyon | `nuk_opex` · `ucret_pay` · `nuk_yoy` | — | |
| 39 | S46 | Kârlılık üçlüsü | `roaa` · `roae` · `rorwa` (+ `*25`) | ROAA · ROAE · RORWA | |
| 40 | S47 | Gelir tablosu bileşimi | `istirak_pay` · `sk_iptal_pay` · `vergi` · `vok` | — | |
| 41 | S48 | Çeyreklik dağılım | `q1` · `q2` · `kar_ttm` | — | |
| 42 | S49 | Yıl sonu tamponu | `sk` · `tufex` · `tampon` · `tufex_var` | — | |
| 43 | S50 | Kapanış | — | — | |

**Kodda olup ekranda olmayan bloklar:** S17 (altın düzeltilmiş cari payı halteri), S20 (altın eğimi), S21 (altın cari
katkısı), S23 (kur arındırılmış büyüme), S27 (altın hariç YP mevduat, REV-09/10), S29 (likidite vade merdiveni) ve
`s50`–`s52` (eski özet kutuları). `renderVals()` bunları hesaplamaya devam eder; DOM'da karşılıkları yoktur.

---

## 7 · Doğrulama

Veri modeli (`KT_veri.js`) on banka için **142 kimlik testine** tabi tutuldu (Ekim 2026); 128'i tuttu, tutmayan 14'ün üçü alternatif hipotez testiydi (yanlış formülün elenmesi), kalanı aşağıdadır. Testler alanların birbirinden
türetilebildiğini ve formüllerin bu dokümandakiyle aynı olduğunu sınar; tolerans gösterim hassasiyetidir.

**Tutan kimlikler (seçme)**

| Aile | Kimlik |
|---|---|
| Bilanço | `akt_*` dört bileşen = `aktif` · `kp_*` beş bileşen = `kredi` · `tuk_*` = `kp_tuketici` · `vadesiz + vadeli = mevduat` · `mevduat + mdk = toplam_kaynak` |
| Para birimi | `kredi_tp + kredi_yp = kredi` · `mevduat_tp + mevduat_yp = mevduat` · `pp_tp + pp_yp = pp` · **`tk_tp + tk_yp = toplam_kaynak + pp`** |
| Büyüme | tüm `*_reel` ↔ `*_ytd` / `*_yoy` (TÜFE %17,76 / %32,11) · tüm `*_usd` ↔ `*_ytd` (kur %8,70) |
| Aktif kalitesi | `npl_o = npl ÷ kredi` · `npl_netform = intikal − tahsilat` · `nfr = netform ÷ ort. brüt` · `npl_o_duz` · `npl_cikis_pay` · `cor6` (altı çekirdek bankada sıfır sapma) |
| Gelir tablosu | `opex = pg + dg` · `mgr = opex ÷ faaliyet geliri` · `jaws` · `q1 + q2 = kar26` · `kar_yoy_reel` · personel gideri ayrıştırması `(1+kadro)(1+birim)−1 = pg_yoy` |
| ZK | `getiri = fg_ttm ÷ ort_ga` · `tcmb_pay = ort_tcmb ÷ ort_ga` · `tcmb_getiri = zk_gelir ÷ ort_tcmb` · sürükleme ayrıştırma kimliği (±1 bps) |
| Sermaye | `dens = rwa ÷ aktif` · `syr_fazla = syr − 12` · `basit = ozkaynak ÷ aktif` · `ngp = nbp + nnp` |
| Tampon | `tampon = sk + tufex` · `tampon_pay = tampon ÷ kar26` · `sk_iptal_pay = sk_iptal ÷ vok` |

**MCP mutabakatı.** Bilanço büyüklükleri, net kâr, ROAA, ROAE ve RAV ekrandaki altı bankada MCP 2026-06-30 kaydıyla
birebir. Marj, getiri ve maliyet rasyoları MCP DAX tarifiyle kurulmuştur; KT'de MCP kaydı eksik olduğu için BDR'den
kurulmuştur (§5.16). Ara-25 toplam kaynak ve PP on bankada MCP'den birebir çekildi (REV-16 §4.3).

**Testlerin ve MCP çapraz kontrolünün yakaladığı sapmalar** — hepsi §8'de:

| Test | Sonuç |
|---|---|
| `vadesiz_altinsiz` | Altı çekirdek bankada formül hatası (sunumda düzeltildi) |
| `rorwa` | Altı çekirdek bankada payda tabanı farklı (sunumda **düzeltilmedi**) |
| NPL hareket kimliği | TEB +483 · VK −32 · GAR +135 · İŞ +15 (tablo kalemleri; rasyolar etkilenmez) |
| Yuvarlama | `spread` AKB (17,25 → 17) · `km_spread` ZK · `swap_bps` DZB/TEB · `ktk_fark_puan` ZK · `km_fark_puan` TEB · `tp_cari_pay_degisim_bps` YKB — hepsi ≤1 birim; alanlar ham orandan değil yuvarlanmış ara değerden hesaplanmış |
| `k_*` | Eski OPEX ayrıştırması Tier-1'de iç tutarsız — kullanılmıyor |

---

## 8 · Bilinen sapmalar ve tuzaklar

Teknik ekibin MCP'den kendi hesabını yaptığında karşılaşacağı farklar. **Sunumdaki değer doğrudur** yazan satırlarda
MCP'den yeniden hesaplanan değer kullanılmamalıdır.

### 8.1 · Sunumun kendi sapmaları

| # | Konu | Durum | Etki |
|---:|---|---|---|
| 1 | **`rorwa` payda tabanı** — altı çekirdek bankada ort. RAV = (Haz-26 + Ara-25)/2; kural ve Tier-1'de (Haz-26 + Haz-25)/2 | ⚠️ **Açık** — veri güncellemesi gerekir | KT %6,11 → %6,53 · QNB %3,98 → %4,04 · DZB %4,32 → %4,55; sıralama değişmez (§5.14) |
| 2 | **`vadesiz_altinsiz`** — altı çekirdek bankada altın yalnız paydan düşülmüş | ✅ Sunumda düzeltildi (`KT_VADE`, `renderVals()` başı) | KT %28,2 → %45,1 |
| 3 | **`tf_ytd` türetmesi** — Ara-25 tabanı yuvarlanmış YtD'lerden geri kurulur | ℹ️ Gösterimde fark yok | KT +%8,97 (kesin +%8,966) |
| 4 | **`yp_fazla`** eski tanım (mevduat_yp − kredi_yp) | ✅ Kullanılmıyor; S26 `tk_yp − kredi_yp` | — |
| 5 | **Eski set kalıntıları** — `CGRP`, `NFRG`, REV-01 `pacal_*`, veri modelindeki `pay_*` | ✅ Kullanılmıyor; sayfa yeniden hesaplar | Bkz. §1.4 |
| 6 | **S22 kur oranı** kutuda sabit %8,73 yazar | ℹ️ BDR kurlarıyla %8,70; hesaplar `÷1,087` kullanır | Yalnız etiket |
| 7 | **`k_*`** eski OPEX ayrıştırması | ✅ Kullanılmıyor | — |
| 8 | **S49** açıklanmış ve türetilmiş TÜFEX'i aynı renkte çizer | ℹ️ `tufex_kaynak` alanı hazır | Görsel |

### 8.2 · MCP tuzakları

| # | Tuzak | Doğru davranış |
|---:|---|---|
| 1 | **KT TCMB hesabı TP bacağı (65.971) MCP 2026-06-30'da eksik** → getirili aktif, getiri, NIM, sürükleme yanlış | **Sunum doğru** (%16,30 · %6,81 · −246 bps); MCP %16,78 · %7,00 · −268 bps kullanılmaz (§5.16) |
| 2 | KT donuk alacak hareketi eksik (Şüpheli grup intikali 6.060) ve `Şüpheli, Önceki Dönem` **yanlış sıfır** (doğrusu 4.545) | BDR dipnotu esas; açılışı Ara-25 `npl` ile çapraz kontrol et |
| 3 | Vakıf Katılım zorunlu karşılık ve donuk alacak kayıtları 2026-06-30'da **0** | BDR esas |
| 4 | **SYR / CET1** tüm bankalarda 2026-06-30'da `null` | BDR |
| 5 | Yanlış banka adı **sessizce 0** döner | Doğru adlar: `Kuveyt Türk` · `QNB Finansbank` · `Denizbank` · `Garanti Bankası` · `Yapı Kredi` · `Akbank` |
| 6 | `Net NPL Formasyon Rasyosu` **×2 yıllıklandırılmış** | 2'ye böl; sunum yıllıklandırmaz |
| 7 | `Brüt CoR (bps)` TTM; `cor6` yarıyıl ×2 — iki taban | Aynı seride karıştırma; KT'de MCP measure'ı kullanılamaz |
| 8 | `NPL Karşılama Oranı` toplam karşılık (1+2+3. aşama) | Sunum yalnız 3. aşama (`npl_kars`) |
| 9 | `Grup 1 Krediler` brüt krediyi tutturmuyor | Artık kalem: `kredi − g2 − npl` |
| 10 | `Tüketici Kredileri ve Bireysel Kredi Kartları` YKB'de KMH'yi çift sayar, İŞ'te +23.817 | BDR dipnotu |
| 11 | `YP Aktifler/ Toplam Aktifler` adı yanlış — DAX `YP Aktifler ÷ YP Pasifler` | Ham kalemden `yp_aktif` |
| 12 | `Net Faiz (Kar Payı) Marjı` ÷ ortalama **toplam aktif** | Sunumdaki NIM = `… Marjı 2` (÷ ortalama getirili aktif) |
| 13 | `Düzeltilmiş …` marjlar tüm ticari K/Z'yi ekler | "Swap düzeltilmiş" = yalnız türev (xl 48) |
| 14 | `Standart Maliyet Gelir Rasyosu` 2025-12-31'de 12 aylık | `mgr25` 6A25'tir |
| 15 | `Diğer Faaliyet Giderleri (OPEX)` adına rağmen personel + diğer | `opex` ile aynı |
| 16 | `TP Vadesiz Mevduat` VK için 0 (ham kalem dolu) | Ham kalem |
| 17 | `Toplam Risk Ağırlıklı Varlıklar (RAV)` ham kalem adı `Kredi Riskine Esas Tutar: Toplam` | Değer toplam RAV'dır; `rwa` ile birebir |
| 18 | Ziraat Katılım `Menkul Kıymetler` 2026-06-30'da `null` | Bileşenlerden topla |
| 19 | MCP'nin gömülü `Rakip` grubu TEB yerine Vakıf Katılım içerir | Grup araçlarında `rakip=[…]` parametresi; sunum grupları sayfa içinde kurar |

### 8.3 · Kaynak dosya tuzakları

| Tuzak | Not |
|---|---|
| **Birim** | Haziran 2026 BDR'leri **milyon TL**, 31.12.2025 ve Haziran 2025 BDR'leri **bin TL** |
| **Yanlış etiketli dosya** | `01_bdr` klasöründeki Denizbank "31.12.2025" PDF'i aslında **31.03.2025** raporudur |
| **Sütun sırası** | Ziraat Katılım gelir tablosu `6A26 · 6A25 · Q2-26 · Q2-25` (diğerleri `6A26 · Q2-26 · 6A25 · Q2-25`) |
| **Düzenleyici esneklik** | 2025 ve 2026 SYR / RAV karşılaştırılamaz (BDDK 11286) — §5.14 |

---

## Ek A · Alan sözlüğü — `KT_veri.js`

Veri modelindeki her alan, dosyadaki sırasıyla. **KT** sütunu 30.06.2026 değeridir (oranlar % olarak gösterildi; dosyada 0–1 arası).
**Ekran:** ● ekrandaki bir slaytta kullanılıyor (slayt etiketi) · ○ yalnız kodda / gösterilmeyen blokta · — hiç okunmuyor.

| Alan | Birim | Tanım | KT | Ekran | Bkz. |
|---|---|---|---:|---|---|
| `id` | metin | Banka anahtarı (kt, qnb, dnz, teb, vk, zk, akb, gar, isb, ykb) | "kt" | ○ | §1.4 |
| `ad` | metin | Banka adı · kısa ad | "Kuveyt Türk" | ● tümü |  |
| `kisa` | metin | Banka adı · kısa ad | "Kuveyt Türk" | ● tümü |  |
| `tip` | metin | `katilim` / `mevduat` | "katilim" | ○ | §4.12 |
| `renk` | hex | Seri rengi | "#2A8020" | ● tümü |  |
| `logo` | yol | Logo / amblem dosya yolu (KT_logolar.js anahtarıyla eşlenir) | "assets/banks/Kuveyt_Turk.png" | ● tümü | §1.2 |
| `lh` | px | Logo satır yüksekliği (yerleşim) | "12px" | ○ |  |
| `aktif` | mn TL | Toplam aktifler · xl 521 | 1.472.314 | ● S04 S06 S26 S28 S31 | §5.1 |
| `aktif_ytd` | oran | YtD büyüme (Ara-25 bazlı) | %8,89 | ● S04 | §4.3 |
| `aktif_reel` | oran | Reel YtD = (1+ytd)/1,1776−1 | −%7,53 | ● S04 | §4.4 |
| `kredi` | mn TL | Toplam brüt krediler · xl 471 | 758.027 | ● S04 S07 S08 S14 S15 S22 S25 S34 | §5.1 |
| `kredi_ytd` | oran | YtD büyüme (Ara-25 bazlı) | %15,85 | ● S04 S08 S15 | §4.3 |
| `kredi_reel` | oran | Reel YtD = (1+ytd)/1,1776−1 | −%1,63 | ● S04 | §4.4 |
| `mevduat` | mn TL | Mevduat / toplanan fonlar · xl 522 | 983.867 | ● S04 S15 S16 S18 S22 | §5.1 |
| `mevduat_ytd` | oran | YtD büyüme (Ara-25 bazlı) | %9,32 | ● S04 | §4.3 |
| `mevduat_reel` | oran | Reel YtD = (1+ytd)/1,1776−1 | −%7,17 | ● S04 | §4.4 |
| `ozkaynak` | mn TL | Özkaynaklar · xl 570 | 138.732 | ● S04 | §5.1 |
| `ozkaynak_ytd` | oran | YtD büyüme (Ara-25 bazlı) | %14,33 | ● S04 | §4.3 |
| `pay` | dizi | Aktif payı — veri modelinde eski set ve 3 dönem; sayfa [Ara-25, Haz-26] olarak yeniden yazar | `[0.1638, 0.1867, 0.1769]` | ● S00 S05 S06 S22 S34 | §5.2 |
| `pay_aktif` | oran | Set içi pay — veri modeli eski sete göre; sayfa yeniden hesaplar | %17,70 | ● S05 | §4.8 |
| `pay_kredi` | oran | Set içi pay — veri modeli eski sete göre; sayfa yeniden hesaplar | %15,50 | ● S05 | §4.8 |
| `pay_mevduat` | oran | Set içi pay — veri modeli eski sete göre; sayfa yeniden hesaplar | %19,30 | ○ | §4.8 |
| `pay_kar` | oran | Set içi pay — veri modeli eski sete göre; sayfa yeniden hesaplar | %22,70 | ● S00 S05 | §4.8 |
| `pay_altin` | oran | Set içi pay — veri modeli eski sete göre; sayfa yeniden hesaplar | %41,10 | ○ | §4.8 |
| `toplam_kaynak` | mn TL | Toplam kaynak (dar): mevduat + alınan kredi + ihraç MK | 1.200.198 | ● S15 | §5.1 |
| `tk_ytd` | oran | YtD büyüme (Ara-25 bazlı) | %9,55 | ● S15 | §4.3 |
| `pp` | mn TL | Para piyasalarına borçlar · xl 526 | 44.846 | ● S15 | §5.1 |
| `gayrinakdi` | mn TL | Gayrinakdi krediler · xl 2156 | 221.597 | — | §5.1 |
| `kar26` | mn TL | Net dönem kârı 6A26 · 6A25 · xl 81 | 23.775 | ● S00 S43 S48 | §5.20 |
| `kar25` | mn TL | Net dönem kârı 6A26 · 6A25 · xl 81 | 18.917 | ● S48 | §5.20 |
| `kar_yoy` | oran | kar26/kar25−1 | %25,68 | ● S00 S43 S48 | §5.20 |
| `kar_yoy_reel` | oran | (1+kar_yoy)/1,3211−1 | −%4,87 | ● S43 S48 | §5.20 |
| `q1` | mn TL | İzole çeyrek kârı | 12.135 | ● S48 | §5.20 |
| `q2` | mn TL | İzole çeyrek kârı | 11.640 | ● S48 | §5.20 |
| `kar_ttm` | mn TL | TTM net kâr | 45.220 | ● S48 | §4.1 |
| `roaa` | oran | kar_ttm ÷ ort. aktif / ort. özkaynak (2 nokta) | %3,59 | ● S00 S43 S46 | §5.20 |
| `roaa25` | oran | Aynı rasyo 31.12.2025 (FY2025) | %3,66 | ● S43 S46 | §5.20 |
| `roae` | oran | kar_ttm ÷ ort. aktif / ort. özkaynak (2 nokta) | %38,32 | ● S00 S43 S46 | §5.20 |
| `roae25` | oran | Aynı rasyo 31.12.2025 (FY2025) | %39,65 | ● S43 S46 | §5.20 |
| `rorwa` | oran | kar_ttm ÷ ort. RAV — ⚠️ altı çekirdek bankada Ara-25 tabanlı | %6,11 | ● S31 S46 | §5.14 · §8.1 |
| `vok` | mn TL | Vergi öncesi kâr 6A26 · xl 58 | 31.338 | ● S47 | §5.21 |
| `istirak` | mn TL | Özkaynak yöntemi geliri 6A26 · xl 56 | 0 | ● S47 | §5.21 |
| `istirak_pay` | oran | istirak ÷ vok | %0,00 | ● S47 | §5.21 |
| `sk_iptal` | mn TL | Serbest karşılık iptali (gelir) 6A26 | 0 | — | §5.21 |
| `sk_iptal_pay` | oran | sk_iptal ÷ vok | %0,00 | ● S47 | §5.21 |
| `nfg` | mn TL | Net faiz (kâr payı) geliri 6A26 · xl 36 | 45.444 | — | §5.15 |
| `nfg_yoy` | oran | nfg YoY | %66,36 | — | §5.15 |
| `nim` | oran | Net faiz (kâr payı) marjı — ÷ ort. getirili aktif (Marjı 2) | %6,81 | ● S05 S33 | §5.15 |
| `nim_swap` | oran | Swap düzeltilmiş marj (+ türev K/Z) | %3,77 | ● S05 S33 | §5.15 |
| `nim_duz` | oran | Düzeltilmiş marj (+ tüm ticari K/Z) | %8,06 | ● S33 | §5.15 |
| `swap_bps` | bps | (nim_swap − nim) × 1e4 | −303 | — | §5.15 |
| `turev` | mn TL | Türev finansal işlemler K/Z 6A26 · xl 48 | −47.846 | ● S28 | §5.12 |
| `kambiyo` | mn TL | Kambiyo işlemleri K/Z 6A26 | 48.690 | ● S28 | §5.12 |
| `getiri` | oran | Getirili aktif getirisi = fg_ttm ÷ ort_ga | %16,30 | ● S34 S35 | §5.15 |
| `maliyet` | oran | Maliyetli pasif maliyeti | %14,44 | ● S34 | §5.15 |
| `spread` | bps | Geometrik spread | 163 | ● S05 S34 | §4.6 |
| `spread_pp` | bps | Spread, maliyet payına PP faizi eklenerek | −186 | — | §5.15 |
| `kredi_getiri` | oran | Kredilerin paçal getirisi | %19,11 | ● S34 | §5.15 |
| `mevduat_maliyet` | oran | Mevduatın paçal maliyeti | %8,81 | ● S34 | §5.15 |
| `vadeli_maliyet` | oran | Vadeli mevduat (katılma hesabı) maliyeti | %22,38 | — | §5.15 |
| `km_spread` | bps | Kredi–mevduat fiyatlama makası (geometrik) | 947 | ● S34 | §5.15 |
| `zk_gelir` | mn TL | ZK'dan alınan faiz (kâr payı) TTM · xl 17 | 17.726 | ● S35 | §5.16 |
| `zk_pay` | oran | zk_gelir ÷ fg_ttm | %9,30 | — | §5.16 |
| `tcmb` | mn TL | TCMB hesabı (TP+YP) · xl 1528 | 282.932 | ● S35 | §5.16 |
| `tcmb_pay` | oran | ort_tcmb ÷ ort_ga | %21,20 | ● S35 | §5.16 |
| `tcmb_tp` | oran | TCMB hesabının TP payı | %23,30 | ● S35 | §5.16 |
| `tcmb_getiri` | oran | Örtük TCMB getirisi = zk_gelir ÷ ort_tcmb | %7,15 | ● S35 | §5.16 |
| `getiri_zk` | oran | ZK hariç getiri | %18,76 | ● S35 | §5.16 |
| `zk_bps` | bps | Zorunlu karşılık sürüklemesi | −246 | ● S35 | §5.16 |
| `vadesiz` | mn TL | Vadesiz (özel cari) · vadeli (katılma hesabı) | 599.982 | ● S16 | §5.8 |
| `vadeli` | mn TL | Vadesiz (özel cari) · vadeli (katılma hesabı) | 383.885 | ● S16 | §5.8 |
| `mdk` | mn TL | Mevduat dışı kaynak = alınan kredi + ihraç MK | 216.331 | ● S15 S16 | §5.8 |
| `vadesiz_pay` | oran | vadesiz ÷ mevduat (Haz-26 · Ara-25) | %60,98 | ● S05 S15 | §5.8 |
| `vadesiz_pay_ara` | oran | vadesiz ÷ mevduat (Haz-26 · Ara-25) | %61,44 | — | §5.8 |
| `vadesiz_altinsiz` | oran | Altın hariç cari payı — ⚠️ veri modelinde altı bankada hatalı, sayfa düzeltir | %28,20 | ● S05 S16 | §5.8 · §8.1 |
| `musteri` | oran | Müşteri mevduatı payı | %99,78 | — | §5.8 |
| `mdk_pay` | oran | mdk ÷ toplam_kaynak | %18,03 | — | §5.8 |
| `kredi_mevduat` | oran | kredi ÷ mevduat (Haz-26 · Ara-25) | %77,00 | ● S05 | §5.8 |
| `km_ara` | oran | kredi ÷ mevduat (Haz-26 · Ara-25) | %72,70 | — | §5.8 |
| `kredi_kaynak` | oran | kredi ÷ toplam_kaynak (Haz-26 · Ara-25) | %63,20 | ● S05 S15 S25 S33 | §5.8 |
| `kk_ara` | oran | kredi ÷ toplam_kaynak (Haz-26 · Ara-25) | %59,70 | ● S15 | §5.8 |
| `altin` | mn TL | Kıymetli maden depo hesapları (Haz-26 · Ara-25 · Haz-25) | 369.246 | ● S05 S16 S19 S25 S26 | §5.10 |
| `altin_ara` | mn TL | Kıymetli maden depo hesapları (Haz-26 · Ara-25 · Haz-25) | 321.900 | ● S15 | §5.10 |
| `altin_haz` | mn TL | Kıymetli maden depo hesapları (Haz-26 · Ara-25 · Haz-25) | 194.085 | ○ | §5.10 |
| `altin_ytd` | oran | YtD · YoY | %14,71 | ● S05 S16 S19 | §5.10 |
| `altin_yoy` | oran | YtD · YoY | %90,25 | ○ | §5.10 |
| `altin_pay_mev` | oran | altın ÷ mevduat (üç dönem) | %37,53 | ● S05 S19 | §5.10 |
| `altin_pay_ara` | oran | altın ÷ mevduat (üç dönem) | %35,77 | ● S05 S19 | §5.10 |
| `altin_pay_haz` | oran | altın ÷ mevduat (üç dönem) | %28,20 | ○ | §5.10 |
| `altin_vadesiz` | mn TL | Altın hesaplarının vadesiz kısmı | 322.498 | ○ | §5.10 |
| `altin_vadesiz_pay` | oran | altin_vadesiz ÷ altin | %87,34 | ● S05 | §5.10 |
| `altin_katki` | oran | altin_vadesiz ÷ vadesiz | %53,75 | ○ | §5.10 |
| `altin_aktif` | mn TL | Aktif taraftaki kıymetli maden | 29.217 | — | §5.10 |
| `nuk` | mn TL | Net ücret ve komisyon 6A26 · xl 37 | 12.305 | ● S45 | §5.19 |
| `nuk_yoy` | oran | YoY | %79,32 | ● S45 | §5.19 |
| `opex` | mn TL | Personel + diğer faaliyet gideri 6A26 | 23.748 | ● S05 S38 S40 S43 S45 | §5.17 |
| `opex_yoy` | oran | YoY (yıllıklandırmasız) | %49,56 | ● S05 S36 S37 S38 | §5.17 |
| `mgr` | oran | Maliyet/gelir 6A26 · 6A25 | %35,92 | ● S05 S43 S44 | §5.17 |
| `mgr25` | oran | Maliyet/gelir 6A26 · 6A25 | %33,73 | ● S05 S43 | §5.17 |
| `nuk_opex` | oran | nuk ÷ opex | %51,82 | ● S45 | §5.19 |
| `ucret_pay` | oran | nuk ÷ faaliyet gelirleri | %18,61 | ● S45 | §5.19 |
| `sube` | adet | Şube sayısı · xl 2183 | 452 | ● S41 | §5.17 |
| `personel` | adet | Personel sayısı · xl 2184 | 6.432 | ● S41 | §5.17 |
| `sube_pers` | kişi | personel ÷ şube | 14,2 | ● S41 S44 | §5.17 |
| `sube_kar` | bin TL | kar_ttm ÷ şube / personel × 1000 | 100.044 | ● S44 | §5.19 |
| `pers_kar` | bin TL | kar_ttm ÷ şube / personel × 1000 | 7.030 | ● S44 | §5.19 |
| `sube_kredi` | bin TL | kredi ÷ şube × 1000 | 1.677.051 | — | §5.19 |
| `npl` | mn TL | Donuk alacaklar (brüt) · xl 490 | 22.732 | ● S10 S14 | §5.6 |
| `npl_o` | oran | npl ÷ kredi (Haz-26 · Ara-25) | %3,00 | ● S05 S09 S10 S14 | §5.6 |
| `npl_ara` | oran | npl ÷ kredi (Haz-26 · Ara-25) | %2,00 | ● S05 S09 S10 | §5.6 |
| `npl_kars` | oran | 3. aşama karşılık ÷ donuk | %71,37 | ● S14 | §5.6 |
| `g2` | mn TL | Grup 2 krediler | 57.564 | ● S14 S46 | §5.6 |
| `g2_o` | oran | g2 ÷ kredi | %7,59 | ● S05 S14 | §5.6 |
| `g2_ara` | oran | g2 ÷ kredi | %6,84 | ● S05 | §5.6 |
| `g2_kars` | oran | 2. aşama karşılık ÷ Grup 2 | %10,31 | ● S14 | §5.6 |
| `cor6` | bps | Yarıyıl brüt CoR ×2 | 299 | — | §5.6 |
| `cor_ttm` | bps | TTM brüt CoR (MCP) | 244 | — | §5.6 |
| `bzk` | mn TL | 6A brüt beklenen kredi zararı gideri | 10.556 | — | §5.6 |
| `bzk_yoy` | oran | YoY | %76,02 | — | §5.6 |
| `syr` | % | SYR (Haz-26 · Ara-25) — BDR | 18,00 | ● S05 S30 S31 | §5.14 |
| `syr_ara` | % | SYR (Haz-26 · Ara-25) — BDR | 22,11 | ● S30 | §5.14 |
| `syr_bps` | bps | Değişim | −411 | — | §5.14 |
| `cet1` | % | Çekirdek SYR | 15,40 | ● S05 S31 | §5.14 |
| `cet1_ara` | % | Çekirdek SYR | 19,11 | ● S05 | §5.14 |
| `cet1_bps` | bps | Değişim | −371 | — | §5.14 |
| `ana` | % | Ana sermaye yeterliliği | 15,40 | ● S31 | §5.14 |
| `kaldirac` | % | Basel III kaldıraç — BDR | 6,29 | — | §5.14 |
| `basit` | oran | ozkaynak ÷ aktif | %9,42 | — | §5.14 |
| `rwa` | mn TL | Toplam RAV | 861.892 | ● S31 | §5.14 |
| `rwa_ytd` | oran | YtD | %39,45 | — | §5.14 |
| `dens` | oran | rwa ÷ aktif | %58,54 | ● S31 S46 | §5.14 |
| `dens_ara` | oran | rwa ÷ aktif | %45,71 | ● S31 | §5.14 |
| `dens_bps` | bps | Değişim | 1.283 | ● S31 | §5.14 |
| `syr_fazla` | puan | syr − 12 | 6 | ● S05 S30 | §5.14 |
| `lcr` | % | LCR toplam · YP — BDR | 202,00 | ● S05 | §5.13 |
| `lcr_yp` | % | LCR toplam · YP — BDR | 285,40 | ● S05 | §5.13 |
| `likit` | oran | (Finansal varlıklar − türev FV) ÷ aktif | %46,17 | — | §5.13 |
| `l1` | mn TL | Likidite açığı vade dilimleri | −123.345 | ○ | §5.13 |
| `l1_pay` | oran | l1 ÷ aktif | −%8,38 | ○ | §5.13 |
| `l13` | mn TL | Likidite açığı vade dilimleri | 47.364 | ○ | §5.13 |
| `l312` | mn TL | Likidite açığı vade dilimleri | 256.206 | ○ | §5.13 |
| `l15` | mn TL | Likidite açığı vade dilimleri | 242.243 | ○ | §5.13 |
| `l5` | mn TL | Likidite açığı vade dilimleri | 6.912 | ○ | §5.13 |
| `sk` | mn TL | Serbest karşılık bakiyesi | 0 | ● S49 | §5.22 |
| `sk_pay` | oran | sk ÷ kar26 | %0,00 | — | §5.22 |
| `tufex_var` | % | TÜFEX değerleme varsayımı | `null` | ● S49 | §5.22 |
| `tufex` | mn TL | TÜFEX tamponu | 0 | ● S49 | §5.22 |
| `tufex_pay` | oran | tufex ÷ kar26 | %0,00 | — | §5.22 |
| `tufex_kaynak` | metin | aciklanmis / turetilmis / null | `null` | — | §5.22 |
| `tampon` | mn TL | sk + tufex | 0 | ● S49 | §5.22 |
| `tampon_pay` | oran | tampon ÷ kar26 | %0,00 | ● S49 | §5.22 |
| `vergi` | oran | Efektif vergi = 1 − kâr ÷ vok (6A26 · 6A25) | %24,13 | ● S47 | §5.21 |
| `vergi25` | oran | Efektif vergi = 1 − kâr ÷ vok (6A26 · 6A25) | %23,71 | ● S47 | §5.21 |
| `diger_kars` | mn TL | Diğer karşılıklar bakiyesi (bilanço) — serbest karşılık taraması için bağlam | 3.554 | — | §5.22 |
| `gorus` | metin | Denetçi görüşü · olumlu mu | "Temiz" | — | §5.23 |
| `gorus_ok` | metin | Denetçi görüşü · olumlu mu | `true` | — | §5.23 |
| `dayanak` | metin | Görüşün dayanağı / dikkat çekilen husus | "Şart, istisna veya dikkat çekilen husu…" | — | §5.23 |
| `nbp` | mn TL | Net bilanço · nazım · genel pozisyon | −35.675 | ● S28 | §5.12 |
| `nnp` | mn TL | Net bilanço · nazım · genel pozisyon | 27.822 | ● S28 | §5.12 |
| `ngp` | mn TL | Net bilanço · nazım · genel pozisyon | −7.853 | ● S28 | §5.12 |
| `ngp_ozk` | oran | ngp ÷ ozkaynak | −%5,66 | ● S28 | §5.12 |
| `yp_aktif` | oran | YP aktif ÷ aktif | %51,95 | ● S28 | §5.11 |
| `yp_mevduat` | oran | YP pay (5 ondalık) | %58,57 | ● S28 | §5.11 |
| `yp_kredi` | oran | YP pay (5 ondalık) | %41,26 | ● S28 | §5.11 |
| `tp_cari` | mn TL | TL vadesiz · TL mevduat | 114.320 | ● S18 | §5.9 |
| `tp_mevduat` | mn TL | TL vadesiz · TL mevduat | 407.663 | ● S18 | §5.9 |
| `tp_cari_pay` | oran | tp_cari ÷ tp_mevduat | %28,04 | ● S18 | §5.9 |
| `tp_cari_pay_ara25` | oran | tp_cari ÷ tp_mevduat | %29,89 | ● S18 | §5.9 |
| `tp_cari_pay_degisim_bps` | bps | Değişim | −185 | ● S18 | §5.9 |
| `kredi_mevduat_altin_haric` | oran | kredi ÷ (mevduat − altın) | %123,33 | ● S05 | §5.8 |
| `kredi_toplam_kaynak_altin_haric` | oran | kredi ÷ (toplam_kaynak − altın) | %91,22 | ● S05 S15 S25 | §5.8 |
| `yp_toplam_kaynak_pay` | oran | (tk_yp − pp_yp) ÷ toplam_kaynak — PP hariç, ekrandan kalktı | %64,70 | — | §5.11 |
| `toplam_kaynak_pay_6banka` | oran | Eski altı bankalı set içinde toplam kaynak payı (kullanılmıyor) | %18,34 | — | §8.1 |
| `toplam_kaynak_ytd_reel` | oran | Reel YtD = (1+ytd)/1,1776−1 | −%6,97 | — | §4.4 |
| `ozk_yontemi_ttm` | mn TL | Özkaynak yöntemi geliri, TTM | 0 | — | §5.21 |
| `istirak_yontemi` | metin | Solo iştirak muhasebe esası | "maliyet değeri" | — | §5.21 |
| `altin_zk_alt` | mn TL | Altına isabet eden ZK tahmini (×%26 · ×%30) | 96.004 | — | §5.10 |
| `altin_zk_ust` | mn TL | Altına isabet eden ZK tahmini (×%26 · ×%30) | 110.774 | — | §5.10 |
| `fg_ttm` | mn TL | Faiz (kâr payı) gelirleri TTM · xl 15 | 190.726 | — | §5.16 |
| `ort_ga` | mn TL | Ortalama getirili aktifler (2 nokta) | 1.169.842 | ● S35 | §5.15 |
| `ort_tcmb` | mn TL | Ortalama TCMB hesabı (2 nokta) | 247.743 | ● S35 | §5.16 |
| `zk_tp_getiri` | oran | Yalnız TP bacağının örtük getirisi | %29,70 | — | §5.16 |
| `pg_6m26` | mn TL | Personel giderleri · xl 44 | 12.426 | ● S39 | §5.17 |
| `pg_6m25` | mn TL | Personel giderleri · xl 44 | 8.776 | — | §5.17 |
| `pg_yoy` | oran | YoY (yıllıklandırmasız) | %41,59 | ● S36 S38 S39 | §5.17 |
| `pg_yoy_reel` | oran | (1+yoy)/1,3211−1 | %7,17 | ● S38 | §5.17 |
| `dg_6m26` | mn TL | Diğer faaliyet giderleri · xl 53 | 11.322 | — | §5.17 |
| `dg_6m25` | mn TL | Diğer faaliyet giderleri · xl 53 | 7.103 | — | §5.17 |
| `dg_yoy` | oran | YoY (yıllıklandırmasız) | %59,40 | ● S36 S38 | §5.17 |
| `dg_yoy_reel` | oran | (1+yoy)/1,3211−1 | %20,66 | ● S38 | §5.17 |
| `opex_6m25` | mn TL | Aynı, 6A25 | 15.879 | — | §5.17 |
| `opex_yoy_reel` | oran | (1+yoy)/1,3211−1 | %13,24 | ● S05 S36 S38 | §5.17 |
| `pg_pay_opex` | oran | pg ÷ opex | %52,32 | — | §5.17 |
| `gelir_yoy` | oran | Faaliyet gelirleri YoY | %40,39 | ● S05 S37 | §5.17 |
| `jaws_puan` | puan | gelir_yoy − opex_yoy | −9,1 | ● S05 S37 | §5.17 |
| `mgr_degisim_bps` | bps | Değişim | 219 | ● S05 S43 | §5.17 |
| `k_kadro` | puan | Eski OPEX ayrıştırması — kullanılmıyor | 1,9 | — | §8.1 |
| `k_birim` | puan | Eski OPEX ayrıştırması — kullanılmıyor | 46,7 | — | §8.1 |
| `k_capraz` | puan | Eski OPEX ayrıştırması — kullanılmıyor | 0,9 | — | §8.1 |
| `personel_haz25` | adet | Personel sayısı · xl 2184 | 6.309 | — | §5.17 |
| `personel_yoy` | oran | YoY | %1,94 | ● S41 | §5.17 |
| `sube_haz25` | adet | Şube sayısı · xl 2183 | 452 | — | §5.17 |
| `sube_yoy` | oran | YoY | %0,00 | — | §5.17 |
| `pg_ayr_kadro_puan` | puan | Personel gideri ayrıştırması | 1,9 | ● S39 | §5.17 |
| `pg_ayr_ucret_puan` | puan | Personel gideri ayrıştırması | 38,9 | ● S39 | §5.17 |
| `pg_ayr_capraz_puan` | puan | Personel gideri ayrıştırması | 0,8 | ● S39 | §5.17 |
| `pg_ayr_kadro_mn` | mn TL | Aynı, tutar | 171 | ● S39 | §5.17 |
| `pg_ayr_ucret_mn` | mn TL | Aynı, tutar | 3.412 | ● S39 | §5.17 |
| `pg_ayr_capraz_mn` | mn TL | Aynı, tutar | 67 | — | §5.17 |
| `personel_degisim_adet` | adet | Değişim | 123 | ● S41 | §5.17 |
| `sube_degisim_adet` | adet | Değişim | 0 | ● S41 | §5.17 |
| `opp26` | bin TL | opex ÷ personel × 1000 (6A) | 3.692 | ● S40 | §5.17 |
| `opp25` | bin TL | opex ÷ personel × 1000 (6A) | 2.517 | — | §5.17 |
| `opp_yoy` | oran | YoY · reel | %46,68 | ● S40 | §5.17 |
| `opp_reel` | oran | YoY · reel | %11,04 | ● S40 | §5.17 |
| `pgp26` | bin TL | pg ÷ personel × 1000 (6A) | 1.932 | — | §5.17 |
| `pgp25` | bin TL | pg ÷ personel × 1000 (6A) | 1.391 | — | §5.17 |
| `pgp_yoy` | oran | YoY · reel | %38,85 | ● S40 | §5.17 |
| `pgp_reel` | oran | YoY · reel | %5,10 | ● S40 | §5.17 |
| `opex_per_sube` | bin TL | opex ÷ şube × 1000 (6A) | 52.540 | ● S40 | §5.17 |
| `opex_ort_aktif` | oran | 2 × opex ÷ ort. aktif | %3,77 | — | §5.17 |
| `kredi_tp` | mn TL | TP / YP bacağı (tk = toplam fonlama, PP dahil) | 445.270 | ● S22 S34 | §5.11 |
| `kredi_yp` | mn TL | TP / YP bacağı (tk = toplam fonlama, PP dahil) | 312.757 | ● S22 S26 S34 | §5.11 |
| `kredi_yppay` | oran | YP payı | %41,26 | ● S05 S22 S34 | §5.11 |
| `kredi_yppay_ara25` | oran | YP payı, önceki dönem | %43,31 | ● S05 S34 | §5.11 |
| `kredi_yppay_bps` | bps | YP payı değişimi | −205 | ● S22 S34 | §5.11 |
| `kredi_tp_ytd` | oran | Bacak YtD (TL) | %20,00 | ● S22 | §5.11 |
| `kredi_tp_ytd_reel` | oran | TP bacağı reel | %1,89 | ● S22 | §5.11 |
| `kredi_yp_ytd` | oran | Bacak YtD (TL) | %10,40 | ● S22 | §5.11 |
| `kredi_yp_ytd_usd` | oran | YP bacağı dolar bazlı | %1,54 | ● S22 | §4.5 |
| `mevduat_tp` | mn TL | TP / YP bacağı (tk = toplam fonlama, PP dahil) | 407.662 | ● S22 | §5.11 |
| `mevduat_yp` | mn TL | TP / YP bacağı (tk = toplam fonlama, PP dahil) | 576.205 | ● S22 | §5.11 |
| `mevduat_yppay` | oran | YP payı | %58,57 | ● S05 S22 | §5.11 |
| `mevduat_yppay_ara25` | oran | YP payı, önceki dönem | %59,37 | — | §5.11 |
| `mevduat_yppay_bps` | bps | YP payı değişimi | −81 | ● S22 | §5.11 |
| `mevduat_tp_ytd` | oran | Bacak YtD (TL) | %11,50 | ● S22 | §5.11 |
| `mevduat_tp_ytd_reel` | oran | TP bacağı reel | −%5,25 | ● S22 | §5.11 |
| `mevduat_yp_ytd` | oran | Bacak YtD (TL) | %7,80 | ● S22 | §5.11 |
| `mevduat_yp_ytd_usd` | oran | YP bacağı dolar bazlı | −%0,79 | ● S22 | §4.5 |
| `tk_tp` | mn TL | TP / YP bacağı (tk = toplam fonlama, PP dahil) | 467.231 | ● S22 S33 | §5.11 |
| `tk_yp` | mn TL | TP / YP bacağı (tk = toplam fonlama, PP dahil) | 777.813 | ● S22 S26 S33 | §5.11 |
| `tk_yppay` | oran | YP payı | %62,47 | ● S05 S22 S24 S28 | §5.11 |
| `tk_yppay_ara25` | oran | YP payı, önceki dönem | %62,70 | ● S05 S24 | §5.11 |
| `tk_yppay_haz25` | oran | YP payı, önceki dönem | %61,26 | ● S24 | §5.11 |
| `tk_yppay_bps` | bps | YP payı değişimi | −23 | ● S22 S24 | §5.11 |
| `tk_yppay_bps_yoy` | bps | YP payı değişimi | 121 | — | §5.11 |
| `tk_tp_ytd` | oran | Bacak YtD (TL) | %9,60 | ● S04 S22 | §5.11 |
| `tk_tp_ytd_reel` | oran | TP bacağı reel | −%6,89 | ● S22 | §5.11 |
| `tk_yp_ytd` | oran | Bacak YtD (TL) | %8,60 | ● S04 S22 | §5.11 |
| `tk_yp_ytd_usd` | oran | YP bacağı dolar bazlı | −%0,13 | ● S22 | §4.5 |
| `ktk_tp` | oran | Kredi ÷ toplam fonlama (TP · YP · toplam) | %95,30 | ● S25 S33 | §5.11 |
| `ktk_yp` | oran | Kredi ÷ toplam fonlama (TP · YP · toplam) | %40,21 | ● S25 S33 | §5.11 |
| `ktk_top` | oran | Kredi ÷ toplam fonlama (TP · YP · toplam) | %60,90 | ● S25 S33 | §5.11 |
| `ktk_fark_puan` | puan | TP − YP farkı | 55,1 | ● S25 S33 | §5.11 |
| `pp_tp` | mn TL | TP / YP bacağı (tk = toplam fonlama, PP dahil) | 43.513 | — | §5.11 |
| `pp_yp` | mn TL | TP / YP bacağı (tk = toplam fonlama, PP dahil) | 1.333 | — | §5.11 |
| `km_tp` | oran | Kredi ÷ mevduat, para birimi bazında | %109,23 | — | §5.11 |
| `km_yp` | oran | Kredi ÷ mevduat, para birimi bazında | %54,28 | — | §5.11 |
| `km_fark_puan` | puan | TP − YP farkı | 54,9 | — | §5.11 |
| `yp_fazla` | mn TL / oran | Eski YP fazlası tanımı — kullanılmıyor | 263.448 | — | §5.11 · §8.1 |
| `yp_fazla_aktif` | mn TL / oran | Eski YP fazlası tanımı — kullanılmıyor | 0,2 | — | §5.11 · §8.1 |
| `tcmb_yp` | mn TL | TCMB hesabı YP · xl 1530 | 216.961 | ● S26 | §5.16 |
| `mev_yp_ah` | mn TL | Altın hariç YP mevduat | 206.959 | ○ | §5.11 |
| `mev_yppay_ah` | oran | mev_yp_ah ÷ mevduat | %21,03 | ● S05 S22 | §5.11 |
| `mev_yp_ah_ytd` | oran | YtD · dolar bazlı | −%2,60 | — | §5.11 |
| `mev_yp_ah_ytd_usd` | oran | YtD · dolar bazlı | −%10,39 | ○ | §5.11 |
| `npl_acilis` | mn TL | Donuk alacak hareketi (dipnot) | 13.095 | ● S11 | §5.7 |
| `npl_intikal` | mn TL | Donuk alacak hareketi (dipnot) | 20.929 | ● S11 | §5.7 |
| `npl_tahsilat` | mn TL | Donuk alacak hareketi (dipnot) | 9.871 | ● S11 | §5.7 |
| `npl_terkin` | mn TL | Donuk alacak hareketi (dipnot) | 1.421 | ● S10 S11 | §5.7 |
| `npl_satis` | mn TL | Donuk alacak hareketi (dipnot) | 0 | ● S10 S11 | §5.7 |
| `npl_kapanis` | mn TL | Donuk alacak hareketi (dipnot) | 22.732 | ● S11 | §5.7 |
| `npl_netform` | mn TL | intikal − tahsilat | 11.058 | ● S11 S13 | §5.7 |
| `npl_stok_degisim` | mn TL | kapanış − açılış | 11.058 | — | §5.7 |
| `npl_o_terkin` | oran | (npl + terkin) ÷ (kredi + terkin) | %3,18 | — | §5.7 |
| `npl_o_duz` | oran | (npl + terkin + satış) ÷ (kredi + terkin + satış) | %3,18 | ● S10 | §5.7 |
| `npl_bps_terkin` | bps | Düzeltme etkisi | 18 | — | §5.7 |
| `npl_bps_duz` | bps | Düzeltme etkisi | 18 | ● S10 | §5.7 |
| `npl_d_bps` | bps | NPL oranı değişimi | 100 | ● S09 S10 | §5.6 |
| `npl_d_bps_duz` | bps | Düzeltilmiş bozulma (Ara-25 bazlı) | 118 | ● S10 | §5.7 |
| `nfr` | oran | Net NPL formasyon rasyosu (6A, yıllıklandırmasız) | %1,70 | ● S13 | §5.7 |
| `npl_intikal_r` | oran | ÷ ort. brüt kredi | %3,21 | ● S12 | §5.7 |
| `npl_tahsilat_r` | oran | ÷ ort. brüt kredi | %1,51 | ● S12 | §5.7 |
| `npl_tah_int` | oran | tahsilat ÷ intikal (6A26 · 6A25) | %47,16 | ● S05 S12 | §5.7 |
| `npl_tah_int_25` | oran | tahsilat ÷ intikal (6A26 · 6A25) | %42,55 | ● S05 | §5.7 |
| `npl_cikis_pay` | oran | (terkin + satış) ÷ açılış | %10,85 | ● S13 | §5.7 |
| `npl_cikis_pay_25` | oran | (terkin + satış) ÷ açılış | %54,86 | ● S13 | §5.7 |
| `npl_intikal_25` | mn TL | 6A25 akımları | 12.651 | — | §5.7 |
| `npl_tahsilat_25` | mn TL | 6A25 akımları | 5.383 | — | §5.7 |
| `npl_cikis_25` | mn TL | 6A25 akımları | 3.862 | — | §5.7 |
| `npl_stok_ytd` | oran | kapanış ÷ açılış − 1 | %73,59 | ● S11 | §5.7 |
| `npl_ort_brut` | mn TL | (kredi Haz-26 + kredi Haz-25)/2 | 652.014 | ● S13 | §5.7 |
| `npl_cikis` | mn TL | terkin + satış | 1.421 | — | §5.7 |
| `npl_int_yoy` | oran | İntikal · tahsilat YoY | %65,43 | — | §5.7 |
| `npl_tah_yoy` | oran | İntikal · tahsilat YoY | %83,37 | — | §5.7 |
| `amblem` | yol | Logo / amblem dosya yolu (KT_logolar.js anahtarıyla eşlenir) | "assets/banks/emblems/Kuveyt_Turk.png" | ● S44 | §1.2 |
| `akt_nakit` | mn TL | Nakit değerler ve MB | 422.646 | ● S06 | §5.3 |
| `akt_nakit_ytd` | oran | Nakit değerler ve MB YtD | −%2,20 | — | §5.3 |
| `akt_nakit_reel` | oran | Nakit değerler ve MB reel YtD | −%16,90 | — | §5.3 |
| `akt_nakit_bps` | bps | Nakit değerler ve MB pay değişimi | −325 | ● S06 | §5.3 |
| `akt_menkul` | mn TL | Menkul kıymetler | 258.891 | ● S06 | §5.3 |
| `akt_menkul_ytd` | oran | Menkul kıymetler YtD | %13,20 | — | §5.3 |
| `akt_menkul_reel` | oran | Menkul kıymetler reel YtD | −%3,90 | — | §5.3 |
| `akt_menkul_bps` | bps | Menkul kıymetler pay değişimi | 67 | ● S06 | §5.3 |
| `akt_netkredi` | mn TL | Net krediler | 733.078 | ● S06 | §5.3 |
| `akt_netkredi_ytd` | oran | Net krediler YtD | %15,10 | — | §5.3 |
| `akt_netkredi_reel` | oran | Net krediler reel YtD | −%2,20 | — | §5.3 |
| `akt_netkredi_bps` | bps | Net krediler pay değişimi | 270 | ● S06 | §5.3 |
| `akt_diger` | mn TL | Diğer aktifler (artık) | 57.699 | ● S06 | §5.3 |
| `akt_diger_ytd` | oran | Diğer aktifler (artık) YtD | %5,90 | — | §5.3 |
| `akt_diger_reel` | oran | Diğer aktifler (artık) reel YtD | −%10,10 | — | §5.3 |
| `akt_diger_bps` | bps | Diğer aktifler (artık) pay değişimi | −11 | — | §5.3 |
| `kp_tuketici` | mn TL | Tüketici + bireysel KK | 95.338 | ● S07 S08 S34 | §5.4 |
| `kp_tuketici_ytd` | oran | Tüketici + bireysel KK YtD | %36,70 | ● S08 | §5.4 |
| `kp_tuketici_reel` | oran | Tüketici + bireysel KK reel YtD | %16,10 | ● S08 | §5.4 |
| `kp_tuketici_bps` | bps | Tüketici + bireysel KK pay değişimi | 192 | ● S07 S34 | §5.4 |
| `kp_tuzel` | mn TL | Tüzel (artık) | 459.147 | ● S07 | §5.4 |
| `kp_tuzel_ytd` | oran | Tüzel (artık) YtD | %13,90 | — | §5.4 |
| `kp_tuzel_reel` | oran | Tüzel (artık) reel YtD | −%3,20 | — | §5.4 |
| `kp_tuzel_bps` | bps | Tüzel (artık) pay değişimi | −102 | — | §5.4 |
| `kp_mali` | mn TL | Mali kesim | 12.508 | ● S07 S34 | §5.4 |
| `kp_mali_ytd` | oran | Mali kesim YtD | %36,00 | — | §5.4 |
| `kp_mali_reel` | oran | Mali kesim reel YtD | %15,50 | — | §5.4 |
| `kp_mali_bps` | bps | Mali kesim pay değişimi | 24 | ● S07 S34 | §5.4 |
| `kp_disticaret` | mn TL | Dış ticaret | 114.680 | ● S07 | §5.4 |
| `kp_disticaret_ytd` | oran | Dış ticaret YtD | %12,60 | — | §5.4 |
| `kp_disticaret_reel` | oran | Dış ticaret reel YtD | −%4,40 | — | §5.4 |
| `kp_disticaret_bps` | bps | Dış ticaret pay değişimi | −44 | — | §5.4 |
| `kp_leasing` | mn TL | Leasing | 76.354 | ● S07 | §5.4 |
| `kp_leasing_ytd` | oran | Leasing YtD | %8,20 | — | §5.4 |
| `kp_leasing_reel` | oran | Leasing reel YtD | −%8,10 | — | §5.4 |
| `kp_leasing_bps` | bps | Leasing pay değişimi | −71 | — | §5.4 |
| `tuk_konut` | mn TL | Konut | 25.636 | ● S08 | §5.5 |
| `tuk_konut_ytd` | oran | Konut YtD | %8,60 | ● S08 | §5.5 |
| `tuk_konut_reel` | oran | Konut reel YtD | −%7,80 | ● S08 | §5.5 |
| `tuk_konut_bps` | bps | Konut pay değişimi | −697 | — | §5.5 |
| `tuk_tasit` | mn TL | Taşıt | 6.096 | ● S08 | §5.5 |
| `tuk_tasit_ytd` | oran | Taşıt YtD | %15,50 | — | §5.5 |
| `tuk_tasit_reel` | oran | Taşıt reel YtD | −%1,90 | — | §5.5 |
| `tuk_tasit_bps` | bps | Taşıt pay değişimi | −118 | — | §5.5 |
| `tuk_ihtiyac` | mn TL | İhtiyaç + diğer | 4.732 | ● S08 | §5.5 |
| `tuk_ihtiyac_ytd` | oran | İhtiyaç + diğer YtD | %48,50 | — | §5.5 |
| `tuk_ihtiyac_reel` | oran | İhtiyaç + diğer reel YtD | %26,10 | — | §5.5 |
| `tuk_ihtiyac_bps` | bps | İhtiyaç + diğer pay değişimi | 39 | — | §5.5 |
| `tuk_bkk` | mn TL | Bireysel kredi kartı | 58.874 | ● S08 | §5.5 |
| `tuk_bkk_ytd` | oran | Bireysel kredi kartı YtD | %56,40 | ● S08 | §5.5 |
| `tuk_bkk_reel` | oran | Bireysel kredi kartı reel YtD | %32,80 | — | §5.5 |
| `tuk_bkk_bps` | bps | Bireysel kredi kartı pay değişimi | 775 | — | §5.5 |
| `tuk_kmh` | mn TL | KMH | 0 | ● S08 | §5.5 |
| `tuk_kmh_ytd` | oran | KMH YtD | `null` | — | §5.5 |
| `tuk_kmh_reel` | oran | KMH reel YtD | `null` | — | §5.5 |
| `tuk_kmh_bps` | bps | KMH pay değişimi | 0 | — | §5.5 |
| `tuk_toplam` | mn TL | Tüketici toplamı = kp_tuketici | 95.338 | ● S08 | §5.5 |
| `kp_tuzel_lh` | mn TL | Tüzel (geniş) = tüzel + leasing + dış ticaret | 650.181 | ● S07 S34 | §5.4 |

---

## Ek B · REV ek veri dosyaları — şemalar

Hepsi `window` üzerinde tek bir global tanımlar, `KT_veri.js`'ten **sonra** yüklenir ve **yalnız ekrandaki görünümü
genişletir**; ana veri modelindeki hiçbir alanı ezmez (tek istisna: REV-04'ün `vadesiz_altinsiz` düzeltmesi sayfa içinde
uygulanır). Tutarlar mn TL, solo. Her dosyanın `pacal` bloğu **eski gruplara** göredir ve okunmaz (§1.4).

| Global | Dosya | Şekil | Kaynak | Kimlik |
|---|---|---|---|---|
| `KT_KOMP_ARA25` | REV-01 | `aktif[id] = [nakit, menkul, net_kredi, diger]` · `toplam_aktif[id]` · `donem` | `COMPD[id].a`'dan türetilmiş: `tutar ÷ (1 + YtD)`, Ara-25 aktifine normalize | dört bileşen = `toplam_aktif` |
| `KT_FONLAMA` | REV-03 | `banka.{ara25,haz26}[id] = [mevduat, alinan_krediler, ihrac_edilen_mk, pp]` · `sira` · `donemler` · `varsayilan` | Haz-26: mevduat ve PP `KT_veri.js` · alınan kredi ve ihraç MK MCP · Ara-25: dördü MCP | ilk üçü = `toplam_kaynak` (iki dönem, 10/10) |
| `KT_VADE` | REV-04 | `banka[id] = [vadesiz, vadeli, mevduat_disi, altin_vadesiz, altin_vadeli]` · `vadesiz_altinsiz_duzeltilmis[id]` | BDR vade yapısı dipnotu · mevduat dışı = alınan kredi + ihraç MK + PP | `vadesiz + vadeli = mevduat` |
| `KT_TLCARI` | REV-05 | `banka[id] = [tl_cari_haz26, tl_fonlama_haz26, tl_cari_ara25, tl_fonlama_ara25]` | Haz-26 `KT_veri.js` (`tp_cari`, `tk_tp`) · Ara-25 MCP `TP Vadesiz Mevduat`, `TP Kaynak` + PP (TP) | MCP `TP Kaynak` + `pp_tp` = `tk_tp` (10/10) |
| `KT_GIDER_REV15` | REV-15 | `ayristirma` (2 satır) · `kartBasim` · `musteriKazanimAraToplam` · `kontrol` | KT iç muhasebe (168 hesap) | blok ve genel toplam değişmez (§5.18) |

**Revizyon geçmişi (veri etkisi olanlar)**

| REV | Slayt | Değişiklik | Veri |
|---|---|---|---|
| 01 | S06 | Aktif kompozisyonuna Ara-25 dönem çipi | `KT_KOMP_ARA25` |
| 02 → 03 | S15 | Fonlama kompozisyonu PP dahil, iki dönem | `KT_FONLAMA` (REV-02'nin yerine) |
| 04 | S16 · S17 | Vade kırılımı üç görünüm; `vadesiz_altinsiz` düzeltmesi | `KT_VADE` |
| 05 | S18 | TL cari ÷ toplam TL fonlama görünümü | `KT_TLCARI` |
| 08 | S26 | YP fazlası `tk_yp − kredi_yp`, TCMB YP soluk çubuk | sayfa içi |
| 09 · 10 | S27 | Altın ayrışma dokusu, YP fonlama çipi | sayfa içi (slayt bu sürümde gösterilmiyor) |
| 11 | S28 · S22 | 4. çubuk `tk_yppay` (PP dahil), "YP toplam fonlama" adı | sayfa içi |
| 12 · 13 | S35 | TCMB hesabı / ortalama getirili aktif çipi (`tcmb_pay`, ikinci değer `ort_tcmb`) | sayfa içi |
| 14 · 15 | S42 | KPI şeridi, kelebek grafik, reklam ayrıştırması | `KT_GIDER_REV15` |
| 16 | S04 | Tutar \| Büyüme anahtarı (varsayılan Tutar); toplam kaynak → toplam fonlama (PP dahil) | sayfa içi `tf_lvl`, `tf_ytd` |
| 17 | tümü | Banka seti altıya indirildi; gruplar sayfa içinde yeniden kuruldu | `banks()` |

---

## Ek C · Paketten veri çıkarma ve değiştirme

Aşağıdaki betik (Python 3, standart kütüphane) paketi açmadan veri dosyalarını çıkarır ve birini yenisiyle değiştirir.
Bu sürümde test edildi: `KT_veri.js` çıkarılıp geri yazıldığında içerik birebir korunuyor ve sayfa aynı şekilde açılıyor.

```bash
python3 kt_bundle.py list    "Kuveyt Turk Rekabet Analizi.html"
python3 kt_bundle.py extract "Kuveyt Turk Rekabet Analizi.html" veri/
python3 kt_bundle.py replace "Kuveyt Turk Rekabet Analizi.html" 13bd152c veri/KT_veri.js "yeni.html"
```

```python
#!/usr/bin/env python3
"""KT Rekabet Analizi paketi — veri dosyalarını çıkar / değiştir.

Kullanım
  python3 kt_bundle.py list    "Kuveyt Turk Rekabet Analizi.html"
  python3 kt_bundle.py extract "Kuveyt Turk Rekabet Analizi.html" cikti_klasoru/
  python3 kt_bundle.py replace "Kuveyt Turk Rekabet Analizi.html" 13bd152c yeni_KT_veri.js  yeni.html
"""
import sys, re, json, gzip, base64, pathlib

TAG = '<script type="__bundler/manifest">'
NAMES = {'13bd152c': 'KT_veri.js', '7bd53fe9': 'KT_logolar.js', '4771c5cd': 'KT_veri_ek_REV01.js',
         '759362a4': 'KT_veri_ek_REV03.js', 'fa139862': 'KT_veri_ek_REV04.js',
         '586f879a': 'KT_veri_ek_REV05.js', 'c4cf4973': 'KT_veri_ek_REV15.js'}

def load(path):
    html = pathlib.Path(path).read_text(encoding='utf-8')
    i = html.index(TAG) + len(TAG)
    j = html.index('</script>', i)
    return html, i, j, json.loads(html[i:j])

def decode(a):
    raw = base64.b64decode(a['data'])
    return gzip.decompress(raw) if a.get('compressed') else raw

def find(man, prefix):
    hits = [k for k in man if k.startswith(prefix)]
    if len(hits) != 1:
        sys.exit(f'uuid öneki tek bir varlığa eşleşmedi: {prefix} → {hits}')
    return hits[0]

cmd, src = sys.argv[1], sys.argv[2]
html, i, j, man = load(src)

if cmd == 'list':
    for k, a in man.items():
        print(k[:8], a['mime'].ljust(24), 'gz' if a.get('compressed') else '  ',
              len(a['data']), NAMES.get(k[:8], ''))

elif cmd == 'extract':
    out = pathlib.Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
    for k, a in man.items():
        if k[:8] in NAMES:
            (out / NAMES[k[:8]]).write_bytes(decode(a))
            print('yazıldı:', NAMES[k[:8]])

elif cmd == 'replace':
    key = find(man, sys.argv[3])
    new = pathlib.Path(sys.argv[4]).read_bytes()
    a = man[key]
    payload = gzip.compress(new, mtime=0) if a.get('compressed') else new
    a['data'] = base64.b64encode(payload).decode('ascii')
    body = json.dumps(man, ensure_ascii=False, separators=(',', ':'))
    pathlib.Path(sys.argv[5]).write_text(html[:i] + body + html[j:], encoding='utf-8')
    # doğrulama: yeni dosyayı tekrar aç, içerik birebir mi
    _, _, _, chk = load(sys.argv[5])
    assert decode(chk[key]) == new, 'geri okuma tutmadı'
    print('değiştirildi:', key[:8], NAMES.get(key[:8], ''), len(new), 'bayt →', sys.argv[5])
```

**Bir alanı düzeltme akışı** (örnek: §8.1 #1, RORWA)

1. `extract` ile `KT_veri.js`'i çıkar.
2. `B` dizisinde ilgili bankanın nesnesinde alanı güncelle (`rorwa: 0.06111` → `0.06526`); başka bir şeye dokunma.
3. `node -e "new Function(require('fs').readFileSync('veri/KT_veri.js','utf8')+';return B')()"` ile sözdizimini sına.
4. `replace` ile yeni paketi üret, tarayıcıda S31 ve S46'yı kontrol et.

⚠️ `KT_logolar.js` (1,8 MB) yalnız logo taşır; açmaya gerek yoktur.
⚠️ Claude Design projesi kaynak tutuluyorsa (yol A) düzeltme orada da yapılmalı — yoksa bir sonraki paketleme eski veriyi geri getirir.

---

## Ek D · Kaynak dokümanlar

| Doküman | Yer | İçerik |
|---|---|---|
| `00_DEVIR_NOTU_2026H1.md` (v1.6) | `Yarıyıl analizi/` | Analizin metodolojik sözleşmeleri (§4), çıpalar (§9), kısıtlar (§10) |
| `00_cekirdek.md` · `02_rasyo_sozlugu.md` · `01_kalem_haritasi.md` · `01a_kalem_indeksi.csv` · `03_banka_gruplari.md` | `00_talimat/` · proje | Analist ajanının çekirdek talimatı, rasyo tanımları (MCP DAX), excel satır haritası, banka adları ve grupları |
| `claude/04_duzenleyici_esneklik_ve_vk_cipalari.md` | proje | BDDK 11286 esneklik kaldırması, Vakıf Katılım çıpaları |
| `claude/05_2026H1_alti_banka_cipalari.md` | proje | Altı çekirdek bankanın bilanço, gelir tablosu ve rasyo çıpaları |
| `claude/06_2026H1_donuk_alacak_hareketleri.md` | proje | Donuk alacak hareket dipnotları (III–V. grup) |
| `claude/08_MCP_2026H1_veri_mutabakati.md` | proje | MCP 2026-06-30 yüklemesinin BDR ile mutabakatı, eksik kayıtlar |
| `claude/09_yapisal_sifirlar_ve_kompozisyon_cipalari.md` | proje | Yapısal sıfırlar (leasing, KMH, TÜFEX, sukuk) ve kompozisyon çıpaları |
| `claude/10_KT_diger_faaliyet_gideri_kirilimi.md` | proje | S42 iç muhasebe kırılımı |
| `claude/11_Tier1_cipalari_ve_10_banka_konumlama.md` · `claude/12_Tier1_v16_veri_ve_duzeltmeler.md` | proje | Tier-1 genişlemesi, MCP measure tuzakları, TÜFEX ve serbest karşılık taraması |
| `claude/13_SMT_sunum_tasarim_brief.md` | proje | Slayt bazlı tasarım özeti (manşet, kart, ray, dipnot) |
| `REV-01` … `REV-16` MD dosyaları | `05_outputs/` | Her revizyonun gerekçesi, hesap ispatı ve kod yaması |
| Solo BDR PDF'leri | `01_bdr/` | 30.06.2026 · 31.12.2025 · 30.06.2025 (birim tuzağı §2.2) |
