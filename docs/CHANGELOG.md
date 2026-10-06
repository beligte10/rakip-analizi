# Changelog

Sürüm geçmişi. Her commit'in özetini barındırır.

## Yeni ölçüler — 2026-10-06 — Rekabet Analizi çalışmasından 39 ölçü

**Kaynak:** `Rekabet Analizi/KT_Rekabet_Analizi_Teknik_Devir.md` (KT Rekabet Analizi · 2026 İlk Yarı) ölçüm sözlüğü.
Sistemde olmayan ölçüler `pipeline/rekabet_olculer.py`'de toplandı (formüller, grup toplama kuralları, katalog
kayıtları tek yerde; `catalog.seed.json` `scripts/rekabet_katalog_yaz.py` ile üretilir). Katalog 170 → 209 ölçü.

**Aileler:** zorunlu karşılık / TCMB / marj (ZK sürüklemesi, örtük TCMB getirisi, getirili aktif bazlı ve swap
düzeltilmiş NIM) · donuk alacak hareketi ve aşama karşılıkları · gider-verimlilik (personel/şube başına OPEX,
kadro ve ücret etkisi, ücret/faaliyet geliri) · kârlılık bileşimi (efektif vergi, iştirak payı, net kâr YoY ve reel,
türev ve kambiyo K/Z) · YP/altın/fonlama/sermaye (YP fonlama payı, kredi/toplam fonlama, YP fonlama fazlası, RAV
yoğunluğu, basit kaldıraç).

**Tanım çakışmaları:** sistemde var olan ölçüye dokunulmadı; dokümandaki tanım farklıysa yeni ölçü ayrı adla eklendi
(NIM → `nim_getirili_aktif`; NPL karşılama toplam karşılık, `npl_3_asama_karsilama` yalnız 3. aşama).
Kişi/şube başına ölçüler sistem kuralıyla TTM'dir (dokümandaki 6A değerinden farklı). Doğrulama: KT 30.06.2026 için
doküman çıpalarıyla `tests/test_rekabet_olculer.py`.

**Elle yüklenen veri:** Basel III kaldıraç, LCR (toplam/YP), serbest karşılık, TÜFEX tamponu (+ mevduat bankaları
altın vadesiz tutarı) BDDK verisinde yok; doküman verisinden `pipeline/manuel_olculer.json` (yalnız 30.06.2026, 10
banka) olarak eklendi. Yeni dönem: `scripts/manuel_olcu_yukle.py`; ardından `scripts/recompute.py`. LCR ve
kaldıraç için grup paçalı hesaplanmaz (paydası açıklanmıyor). Denetçi görüşü ve TÜFEX kaynağı gibi metin alanları
`metinler` altında tutulur, ölçü olarak gösterilmez.

**Elle yüklenen veri — 27 banka (2026-10-07):** kalan 17 bankanın 30.06.2026 solo BDR PDF'lerinden (bdr-kisayol
bağlantıları; Fibabanka KAP) kaldıraç, LCR (toplam/YP), serbest karşılık ve TÜFEX okundu. Kaldıraç ve LCR 27
bankada tam; çıpa bankaları (Denizbank, Garanti, İş, Yapı Kredi, TEB) doküman değerleriyle ±0,06 içinde tuttu.
Serbest karşılık: raporda tutar yazan bankalar (Albaraka 1.040, Emlak 13.000, Fibabanka 1.210, Şekerbank 1.000)
okundu; "bulunmamaktadır" diyen ya da hiç anmayan bankalar 0 sayıldı (doküman kuralı); Enpara'nın bakiyesi
raporda yalnız 27.08.2025 devir tarihi için var → boş. TÜFEX: Garanti/TEB formülüyle (gerçekleşen TÜFE %32,11 −
varsayım) × duyarlılık doküman değerlerini yeniden üretti; ING (82), Vakıfbank (5.425), Ziraat Bankası (13.307)
aynı yolla türetildi (büyüklük mertebesi); duyarlılığı raporda bulunmayan bankalar boş.

## Düzeltme — 2026-09-12 (devam) — risk_agirlikli "Toplam" satırı eşleşmesi genişletildi

**Bağlam:** 2026-2C için `cikti_compare.py` tekrar çalıştırıldığında uyum oranı **%51.7**
çıktı (bir önceki düzeltmelerden sonra bile) — `piyasa_riski_toplam_risk`/
`operasyonel_risk_toplam_risk` ING Bank, TEB, Vakıf Katılım, Enpara'da hâlâ 6-10x şişik
çıkıyordu.

**Kök neden:** `_convert_sermaye_risk`'in RAV toplamını (`Kredi Riskine Esas Tutar:
Toplam`) yakalamak için kullandığı `kalem_ham.startswith('Toplam (')` şartı çok katıydı.
`risk_agirlikli`'nin toplam satırının etiketi bankaya göre değişiyor: ING Bank/TEB'de
formül eki kaybolup salt **"Toplam"** kalıyor, Vakıf Katılım'da araya bir sıra numarası
karışıp **"Toplam 25 (1+4+...)"** oluyor, Enpara'da tamamı **BÜYÜK HARFLE "TOPLAM
(1+4+...)"** basılıyor — üçü de eski şartla eşleşmiyordu. Payda (`m_toplam_risk_tabani`)
bu durumda yalnız Piyasa+Operasyonel'e düşüyor (Kredi Riski bileşeni hiç eklenmiyor),
bu da her iki oranı da olması gerekenin 6-10 katına şişiriyordu.

**Düzeltme:** Eşleşme artık büyük/küçük harften bağımsız ve alt dize bazlı (VERI-
FORMATI.md §6.8'in zaten önerdiği yaklaşım) — yalnız sermaye_ozet'in KENDİ "Toplam Risk
Ağırlıklı Tutarlar" satırı (aynı değeri taşıyan ayrı bir kaynak) bilinçli olarak
dışlanıyor; ilk denemede bu dışlama unutulup Akbank'ta RAV'ın tam 2 katına çıktığı
regresyon testinde (`test_akbank_byte_exact`) yakalandı ve düzeltildi.

**Sonuç:** ING Bank/TEB/Vakıf Katılım/Enpara'nın piyasa/operasyonel risk oranları artık
doğru. 2026-2C uyum oranı %51.7 → **%53.1** (mütevazı — mvy/tfv kolon kayması hâlâ en
büyük tek kalem, aşağıya bakınız). 27 test tekrar geçti.

## Düzeltme — 2026-09-12 — cikti_ingest.py: iki sistemik işaret (sign) hatası giderildi, mvy/tfv kolon kayması teşhis edildi

**Bağlam:** 2026-1C için `cikti_compare.py` çalıştırıldığında uyum oranı **%52.7** çıktı
(1961 uyuşan, 1760 farklı, 390 JSON'da yok). En yüksek yüzdeli farkların analizi 3 ayrı
kök nedene işaret etti.

### 1) Kâr/Zarar "(-)" etiketli kalemler — bazı bankalarda işaret ters

`personel_giderleri`, `diger_faaliyet_giderleri`, `faiz_giderleri`,
`verilen_ucret_komisyonlar` gibi ölçüler ING Bank ve Türkiye Finans'ta **tam +200%**
farkla çıkıyordu (`JSON=-X`, `Mevcut=X` — birebir işaret ters çevrilmiş). Kaynak
doğrulaması: `veriler.parquet`'te bu kalemler HER ZAMAN pozitif (Akbank, ING Bank,
Türkiye Finans'ın kendi ham satırları karşılaştırıldı) — BDDK etiketindeki "(-)" yalnız
formülde çıkarılacağını belirtiyor, saklanan değer negatif değil. Ama BDR PDF'lerinin
ING Bank/Türkiye Finans basımı bu satırları **parantez içinde** ("(9.870.896)") yani
gerçekten negatif yazdırıyor — `bdr-kisayol-main`'in ayrıştırıcısı bunu doğru okuyor
(kaynağa sadık), sorun yalnız bizim tarafın "(-)" etiketini her zaman pozitif ham veri
sayması gereken varsayımıyla çelişmesinde.

**Düzeltme:** `convert_kayitlar`'da kalem adı "(-)" ile bitiyorsa `abs()` uygulanıyor
(25/27 bankada no-op, ING/Türkiye Finans'ta düzeltiyor).

### 2) Donuk Alacak Hareketleri — Tahsilat/Çıkış işareti ters

`donuk_tahsilat_ort_krediler`/`npl_formasyonu` birçok bankada (Halkbank, Akbank, Ziraat,
Emlak Katılım, Vakıf Katılım, TOM Bank...) yanlış işaretli çıkıyordu.
`measures.py`'nin kendi docstring'i zaten "ham veride NEGATİF" diyordu (`m_donuk_
tahsilat_ort_krediler`) — doğrulandı: `veriler.parquet`'te "Dönem İçi Tahsilat" HER
ZAMAN negatif (Halkbank: -1.317.834.000, Akbank: -2.177.220.000), bizim JSON'umuz ise
BDR PDF'inin bastığı (genellikle pozitif) işareti koruyor. Hayat Finans'ta ise TAM TERSİ
— hem bizim JSON hem Rakip'in ham verisi negatif (bu bankanın PDF'i de parantezli
basıyor) — yani işaret PDF'e göre değişken, Rakip'in kendi konvansiyonu ise HER ZAMAN
sabit (Tahsilat/Çıkış negatif, İntikal/Giriş pozitif).

**Düzeltme:** `_convert_donuk_akim`'de "çıkış" yönü (Tahsilat, Diğer Çıkış) `-abs()`,
"giriş" yönü (İntikal, Diğer Giriş) `abs()` ile normalize ediliyor — hangi bankanın PDF'i
hangi işareti kullanırsa kullansın sonuç artık Rakip'in sabit konvansiyonuyla eşleşiyor.

Her iki düzeltme de mevcut 27 testin tamamını (`test_cikti_ingest.py`,
`test_baseline_promoted.py`) geçti.

### 3) mvy/tfv vade dilimi kolonları — TEŞHİS EDİLDİ, DÜZELTİLMEDİ (öncelikli açık iş)

`vadeli_3_6ay_toplam_vadeli`/`vadeli_6_12ay_toplam_vadeli`/`birikimli_vadeli_mevduat_
toplam_vadeli` ailesi listenin EN ÜSTÜNDE (bazı satırlar >100.000% fark) — kök neden
`bdr-kisayol-main` tarafında: "Mevduatın Vade Yapısına İlişkin Bilgiler" dipnotu
gerçekte **9 kolonlu** bir matris (Vadesiz / 7 Gün İhbarlı / 1 Aya Kadar / 1-3 Ay / 3-6
Ay / 6 Ay-1 Yıl / 1 Yıl ve Üstü / Birikimli Mevduat / Toplam — doğrulandı, Fibabanka
2026-1C sayfa 65 ham metniyle), ama `bakim/ayiklama/ayristir.py`'nin genel `veri_
kolonlari()` sezgisi (sık kullanılmayan/seyrek dolu kolonları "gürültü" sayıp eleyen
`len(k) >= max(3, enbuyuk*0.5)` eşiği) yalnız **4 kolonu** tespit ediyor — "3-6 Ay",
"6 Ay-1 Yıl", "1 Yıl ve Üstü", "Birikimli" kolonları sessizce düşüyor ve "Toplam"
(genel toplam) sütunu yanlışlıkla "1 Yıl ve Üstü" pozisyonuna kayıyor. Bu, `cikti_
ingest.py`'nin `_MVY_BUCKET_KALEM` indeks varsayımlarıyla (degerler[0]=1 Aya Kadar...
degerler[5]=Birikimli) da uyumsuz — iki tarafın da (ayrıştırıcı + ingest indeksleme)
koordineli düzeltilmesi gerekiyor. Bu turda ELLENMEDİ (kapsamı `bdr-kisayol-main`
tarafında dipnot.py'ye özel, başlık-konum-bazlı bir kolon tespiti eklemeyi gerektiriyor)
— bir sonraki öncelik olarak işaretlendi.

## Bulgu — 2026-09-12 — Kret/Pret/Oret (RAV kırılımı) 3 bankada byte-exact doğrulandı

**Kaynak:** `bdr-kisayol-main` projesinde `dipnot.py`'ye yeni bir Grup 2 tablosu
(`risk_agirlikli`) eklendi — BDR PDF'inin "ii. Risk Ağırlıklı Tutarlara Genel
Bakış" dipnotu (Dördüncü Bölüm, Özkaynak dipnotunun hemen ardından; BDDK'nın
standart Basel Pillar 3 tarzı RAV özet şablonu). Bu, önceden yalnız TOPLAM RAV'ı
taşıyan `sermaye_ozet`'ten farklı olarak Kredi/Karşı Taraf Kredi/Piyasa/
Operasyonel Risk kırılımını satır satır veriyor.

**Doğrulama:** Akbank, Kuveyt Türk ve Alternatif Bank'ta (1 mevduat + 1 katılım
+ 1 mevduat, 2025-4Ç) `measures.py`'deki `_kredi_riski`/`_piyasa_riski`/
`_operasyonel_risk` fonksiyonlarının okuduğu ham değerler
(`Sermaye Std. Oranı, .../(Kret)/(Pret)/(Oret)`, "tcmb" tablo etiketi altında —
bkz. `ctx.tcmb` docstring'i) BDR PDF'inden bağımsız çıkarılan rakamlarla
**üçünde de birebir eşleşti**:

| Banka | Kret (bin TL) | Pret (bin TL) | Oret (bin TL) |
|---|---|---|---|
| Akbank | 1.694.291.120 | 45.632.139 | 227.728.071 |
| Kuveyt Türk | 453.053.554 | 69.351.303 | 88.762.224 |
| Alternatif Bank | 67.869.461 | 3.419.700 | 4.691.612 |

Bu, `m_kredi_riski_toplam_risk`/`m_piyasa_riski_toplam_risk`/
`m_operasyonel_risk_toplam_risk` ve dolayısıyla `m_toplam_risk_tabani`
ölçülerinin ham veride yanıltıcı bir tablo etiketi taşımasına rağmen (kalemler
gerçekte "tcmb" değil Sermaye Yeterliliği dipnotundan geliyor) DEĞER olarak
tamamen doğru hesaplandığını kanıtlıyor. Sermaye/RAV kırılımının kalan
ölçüleri (Kret/Pret/Oret toplam-risk-payı oranları) artık tamamen doğrulanmış
durumda.

## Bulgu — 2026-09-11 — Alternatif Bank 2024-4Ç: raw'daki Ortaklık Yatırımları/Özkaynaklar tutarsızlığı araştırıldı (kaynak farkı, hata değil)

**Kaynak:** `bdr-kisayol-main` projesinin sistematik karşılaştırmasında (484 top-level kalem,
%93.18 birebir eşleşme) tespit edilen tek açıklanamayan fark, ayrı bir turda araştırıldı.

**Gözlem:** `veriler.parquet`'te Alternatif Bank 2024-12-31 (Toplam):
- `Bağlı Ortaklıklar (Net)` / `Ortaklık Yatırımları` = 691.465 bin TL
- `Özkaynaklar` = 7.295.479 bin TL
- `Toplam Aktifler` = `Toplam Pasifler` = 83.325.148 bin TL

BDR PDF'inden (bdr-kisayol-main pipeline'ı, **solo** rapor — kapsam kararı gereği) çıkan
değerler:
- `Ortaklık Yatırımları` = 350.580 bin TL (2024-4Ç PDF'in kendi cari dönem kolonu **ve**
  2025-1Ç PDF'in önceki dönem/karşılaştırma kolonu birbirini doğruluyor — iki bağımsız
  dosya, 3 ay arayla yayınlanmış, aynı rakam)
- `Özkaynaklar` = 6.954.594 bin TL
- `VARLIKLAR TOPLAMI` = 82.984.263 bin TL

Fark her üç kalemde de **tam olarak aynı: 340.885 bin TL** (raw daha yüksek). Bu, tek bir
satırda kopyala-yapıştır/typo hatası değil — bilanço bütünüyle tutarlı, dengeli
(`Toplam Aktifler = Toplam Pasifler`) ama bizim solo BDR PDF'imizden 340.885 bin TL daha
büyük ikinci bir versiyon.

**Elenen ihtimaller:**
- Konsolide (solo değil) rapor karışıklığı değil — Alternatif Bank'ın 2024-4Ç konsolide
  PDF'inde `Ortaklık Yatırımları` = 0 (bağlı ortaklık tam konsolide edildiği için satır
  boşalıyor), raw'daki 691.465 ile örtüşmüyor.
- Dönem/kolon kayması (cari↔önceki karışması) değil — 350.580, hem 2024-4Ç'nin cari
  kolonunda hem 2025-1Ç'nin önceki-dönem kolonunda birebir tekrarlanıyor, iki ayrı PDF
  arasında iç tutarlı.
- BDDK'nın genel Aylık Bülten'i (bddk.org.tr) banka bazlı kırılım sağlamıyor, yalnızca
  sektör/grup toplamı veriyor — bu kaynakla hakemlik yapılamadı (daha önceki turda da aynı
  sonuca varılmıştı).

**Sonuç:** `bdr-kisayol-main` tarafının doğruluğu iki bağımsız BDDK PDF'iyle teyit edildi;
sorun bizim çıkarımımızda değil. Raw'daki xlsx kaynağının (`Metot: AC`, `Şablon:
BNK_DATA_TOTAL` etiketli üçüncü parti veri seti) bu tarihe farklı, ama kendi içinde tutarlı
bir bilanço ataması var — en olası açıklama bir restatement/düzeltme ya da vendor'ın bağlı
ortaklık yatırımını farklı bir yöntemle (örn. özkaynak yöntemine göre yeniden değerleme)
taşıması; her iki tarafta da simetrik +340.885 hareketi ("aktif tarafı + özkaynak tarafı
birlikte artıyor, bilanço dengede kalıyor") bunu destekliyor. Kesin kaynağı doğrulamak için
vendor'a ya da bankanın 2024-4Ç için sonradan yayınlanmış bir düzeltme raporuna bakmak
gerekir — bu depoda elde mevcut veriyle kapatılamıyor. Sistematik karşılaştırmadaki 484
kalemlik örneklemde tek istisna bu olduğundan (%99.8 açıklanabilirlik), kapsam dışı olarak
işaretlendi.

## Bulgu — 2026-09-11 — BASELINE_PASSTHROUGH'un 2 kalemi artık raw'dan hesaplanabilir (RAV artık raporlanıyor)

**Kaynak:** `bdr-kisayol-main` projesinde (PDF tabanlı BDR ayrıştırıcı, bu depodan bağımsız)
"Sermaye Yeterliliği Oranları" özet tablosu (`dipnot.sermaye_ozet_satirlari`) eklendi —
BDR PDF'inin Dördüncü Bölüm I no'lu dipnotunun sonunda, "Toplam Özkaynak (Ana sermaye ve
katkı sermaye toplamı)" satırından "Uygulanacak İndirim Esaslarında..." öncesine kadar
olan bant. Bu tablo **Toplam Risk Ağırlıklı Tutarlar (RAV)**'ı da satır olarak taşıyor —
"RWA-bağımlı" gerekçesiyle BASELINE_PASSTHROUGH'a alınmış kalemler için önceki varsayım
("Risk Ağırlıklı Varlıklar raporlanmıyor") artık geçersiz.

**Doğrulama (Akbank, 2025-06-30, `computed.json`'daki mevcut baseline değerleriyle
birebir karşılaştırıldı):**

| Measure | Formül | Hesaplanan | `computed.json` | Eşleşme |
|---|---|---|---|---|
| `syr` | BDR'de doğrudan satır ("Sermaye Yeterliliği Oranı (%)") | 20.32 | 20.32 | ✅ birebir |
| `cekirdek_syr` | BDR'de doğrudan satır ("Çekirdek Sermaye Yeterliliği Oranı (%)") | 14.93 | 14.93 | ✅ birebir |
| `rorwa` | TTM(Net Dönem Karı) / Avg(RAV, t & t-4q) × 100 | 2.68287 | 2.6829 | ✅ birebir |
| `net_faiz_ort_rav` | TTM(Net Faiz Geliri) / Avg(RAV, t & t-4q) × 100 | 4.08398 | 4.083983 | ✅ birebir |

TTM ve Avg Balance için bu changelog'da zaten belgelenmiş kendi formülünüz kullanıldı
(`TTM(t) = YtD(t) + (FY_prev − YtD(yoy(t)))`, `Avg Balance = (stock(t) + stock(t−4q)) / 2`)
— RORWA ve net_faiz_ort_rav'ın avg RAV'ı `t` ve `t-4q` (yıl önceki aynı çeyrek)
kullanılarak hesaplandı, `t` ve `t-1` (bir önceki yıl sonu) DEĞİL.

**Düzeltme (aynı gün) — `ort_rav_ort_ozkaynak` ve `grup_2_krediler_cekirdek_sermaye`
kontrol edildi, ikisi de yukarıdaki listeye ait değilmiş:**
- `ort_rav_ort_ozkaynak` **catalog.json'da mevcut değil** — bu depoda artık böyle bir
  measure id'si yok (muhtemelen Faz 1.5'ten bu yana yeniden adlandırılmış/kaldırılmış).
  Doğrulanacak bir şey yok.
- `grup_2_krediler_cekirdek_sermaye` **zaten BASELINE_PASSTHROUGH'ta değil** — canlı
  `m_grup_2_krediler_cekirdek_sermaye` fonksiyonu var (measures.py:186) ve
  `computed.json`'da gerçek bir değeri var (Akbank 2025-06-30: 31.9416). Önceki girdideki
  "kısmi kapsandı" notu, bu changelog'un Faz 1.5 girdisindeki **eski (24 kalemli)**
  BASELINE_PASSTHROUGH listesine bakılarak yazılmıştı — güncel kod değil. Özür: yanlış
  alarm.

  Yine de çapraz doğrulama yapıldı, farklı bir değeri var: **PDF tabanlı pipeline'ımız
  aynı sonucu bağımsız olarak üretiyor.** BDR'de "Çekirdek Sermaye Toplamı" satırı
  `sermaye_ozet`'in taradığı bandın hemen öncesinde (Akbank sayfa 30: 260.313.241 bin TL,
  cari) — `grup12`'nin "Toplam" satırındaki Yakın İzlemedeki 3 kolonu (İhtisas Dışı +
  Sözleşme Değişikliği + Yeniden Finansman = 83.148.235) buna bölündüğünde **31.941608**
  çıkıyor — `computed.json`'daki 31.941607995269056 ile ✅ birebir. Bunun pratik anlamı:
  xlsx kaynağı değişmeden bırakılsa bile, ileride PDF pipeline'ı bu measure için de
  çapraz doğrulama/yedek kaynak olarak kullanılabilir (bkz. Grup 2/3 sınırlamaları:
  grup12 şu an yalnız 15/27 bankada ve yalnız Cari Dönem'de — bu doğrulama tek bankada,
  tek dönemde yapıldı, genellemeden önce daha fazla örnek gerekir).
- `faiz_getirili_ozkaynak` — bkz. aşağıdaki **düzeltme**, TCMB Hesabı sanılanın aksine
  BDR'de var.

**DÜZELTME (aynı gün, birkaç saat sonra) — önceki "TCMB/Faiz Maliyetli Pasif kaynağı
bulunamadı, BDDK Aylık Bülten'e bağımlı" tespiti YANLIŞTI, iki ayrı hata içeriyordu:**

1. **`maliyetli_pasifler_toplam_pasifler` ve `toplam_fonlama_faiz_maliyetli_pasif` hiç
   `ctx.tcmb()` kullanmıyor.** `_faiz_maliyetli_pasif_detay` (measures.py:951) ve
   `m_toplam_fonlama` (measures.py:1003) **saf `ctx.bilanco()`** — Vadeli Mevduat, Alınan
   Krediler, Para Piyasalarına Borçlar, İhraç Edilen Menkul Kıymetler vb. Her ikisi de
   zaten `MEASURE_FUNCS`'ta kayıtlı (satır 1325, 1351) — **hiçbir zaman
   BASELINE_PASSTHROUGH'ta değildi, hiç kapalı değilmiş.** İlk mesajımdaki "Faiz
   Maliyetli Pasif Detayı (2): BDDK Aylık Bülten" sınıflandırması, ölçü adındaki
   "Faiz Maliyetli Pasif" ifadesinin TCMB Hesabı'yla aynı grupta olduğu varsayımına
   dayanıyordu — koda hiç bakmadan yapılmış yanlış bir kategorizasyon.

2. **TCMB Hesabı, İnteraktif Aylık Bülten'den DEĞİL, BDR'nin kendisinden geliyor** —
   yalnız beklediğim başlıkla ("Nakit Değerler ve TCMB'ye İlişkin Bilgiler") aramıştım,
   bulamayınca "kaynak yok" sonucuna atladım. Gerçek başlık farklı: **Beşinci Bölüm,
   I. Aktif Kalemlere İlişkin Açıklama ve Dipnotlar, a. "Nakit değerler ve T.C. Merkez
   Bankası Hesabı ile T.C. Merkez Bankası hesabı içeriğine ilişkin bilgiler", 1. "Nakit
   Değerler ve T.C. Merkez Bankası hesabına ilişkin bilgiler"** (Akbank 2025-06-30,
   sayfa 63) — TP/YP kırılımlı, tam olarak `ctx.tcmb(b,t,'TCMB Hesabı, (TP)')` /
   `(YP)`'nin ihtiyacı olan veri: Cari Dönem TCMB satırı TP=203.323.759, YP=199.831.427.

   `_faiz_getirili_aktif_detay`'ın 13 bileşeninden TCMB dışındaki 11'i zaten bilinen
   bilanço kalemleri (Bankalar, Para Piyasalarından Alacaklar, GUD K/Z, GUD DKG, İtfa
   Edilmiş Maliyet, Türev FV, Hedge Türev FV, Brüt Krediler, BZK).

**TAM DOĞRULAMA (aynı gün, üçüncü geçiş) — kalem eşleştirmesi tamamlandı, 3 measure de
birebir eşleşti:**

`data/veriler.parquet`'ten Akbank'ın ham Bilanço/mvy/tcmb kalemleri satır satır çekilip
(2025-06-30 ve avg_balance için 2024-06-30) formül elle yeniden kuruldu:

| Measure | Hesaplanan | `computed.json` | Eşleşme |
|---|---|---|---|
| `faiz_getirili_ta` | 92.36050013622645 | 92.36050013622645 | ✅ birebir (son hane dahil) |
| `faiz_getirili_maliyetli` | 1.3984738048447363 | 1.3984738048447363 | ✅ birebir |
| `faiz_getirili_ozkaynak` | 9.664690915955463 | 9.664690915955463 | ✅ birebir |

**Önceki ~2 puanlık farkın sebebi bulundu:** `_brut_krediler`'i yanlış "gross-up"
ediyordum (Net Krediler'e BZK'yı tekrar ekliyordum). Doğrusu: `Krediler Ve Alacaklar`
+ `Donuk Alacaklar` toplamı zaten BDR'nin bilançodaki tek "Krediler" satırına eşit
(Akbank 2025-06-30: 1.393.529.620 + 52.746.785 = 1.446.276.405 — bizim bilançodaki
"Krediler" (kod 2.1) ile birebir), BZK ayrıca **eklenmeden** olduğu gibi kullanılıp
formülün sonunda tek sefer düşülüyor.

**Kesinleşen kalem eşleştirmesi (BDR PDF → raw kalem adı):**
- `TCMB Hesabı, (TP/YP)` → Beşinci Bölüm I.a.1 "Nakit Değerler ve T.C. Merkez Bankası
  hesabına ilişkin bilgiler" tablosu, "TCMB" satırı, TP/YP kolonları
- `Bankalar`, `Para Piyasalarından Alacaklar`, `Gerçeğe Uygun D. Farkı K/Z Yan.Fv (Net)`,
  `...Diğer Kapsamlı Gelire Yansıtılan FV`, `Türev Finansal Varlıklar` → bilanço
  kodları 1.1.2, 1.1.3, 1.2, 1.3, 1.4 (1.4 = kar/zarar + hedge alt kalemlerinin toplamı,
  "Riskten Korunma Amaçlı Türev Fv" Akbank'ta 0 — 1.4 tek satırda toplu geliyor)
- `İtfa Edilmiş Maliyeti ile Ölçülen Finansal Varlıklar` → bilanço 2.4 ("...ile Ölçülen
  **Diğer** Finansal Varlıklar" — isim farklı ama değer birebir aynı kalem)
- `Krediler Ve Alacaklar` + `Donuk Alacaklar` (ayrı ayrı DEĞİL, toplamları) → bilanço
  2.1 "Krediler" (bizim taksonomimizde tek satır, alt kırılımı yok)
- `Beklenen Zarar Karşılıkları (-)` → bilanço 2.5, mutlak değeri tek sefer düşülüyor
- `Vadeli Mevduat` (= Toplam Mevduat − Vadesiz Mevduat) → bilanço "Mevduat" −
  `mvy`/`tfv` tablosunun "Toplam" satırının Vadesiz kolonu (bugün eklediğimiz `dipnot.py`)
- `Özkaynaklar` (avg_balance, spot DEĞİL) → bilanço özkaynak toplamı, t ve t-4ç
  ortalaması — **`sermaye_ozet`'teki "Toplam Özkaynak (regülasyon)" ile KARIŞTIRILMAMALI**,
  bu düz bilanço Özkaynaklar kalemi

**Güncel durum — hepsi netleşti:**
- `maliyetli_pasifler_toplam_pasifler`, `toplam_fonlama_faiz_maliyetli_pasif`: zaten
  çalışıyor, hiç kapsam dışı değilmiş.
- `faiz_getirili_ta`, `faiz_getirili_maliyetli`, `faiz_getirili_ozkaynak`: **kapsam dışı
  değil, formülü birebir doğrulandı** — BASELINE_PASSTHROUGH'tan çıkarılıp raw'dan
  hesaplanan `MEASURE_FUNCS`'a taşınabilir.
- BDDK İnteraktif Aylık Bülten testi (banka bazlı veri yok) doğru bir bulgu ama bu
  measure ailesiyle **hiç ilgisi yokmuş** — `ctx.tcmb()` adının çağrıştırdığı yanlış bir
  izdi; asıl kaynak BDR'nin kendisi.

**Yan bulgu:** Aynı raw tabloda (`Nakit Değerler ve TCMB'ye İlişkin Bilgiler`) RAV'ın
risk türüne göre kırılımı da var — `Sermaye Std. Oranı, Kredi/Piyasa/Operasyonel Riskine
Esas Tutar (Kret/Pret/Oret)`. Akbank 2024-06-30 (ara dönem!) için de dolu — daha önceki
"RAV kırılımı yalnız yıl sonu raporunda var" tespiti muhtemelen bankaya/döneme özgüydü,
genellenmemeli. Bu 3 ölçü (Sermaye/RAV kategorisinden) ayrı bir doğrulama turu
gerektiriyor.

**Öneri:** `syr`, `cekirdek_syr`, `rorwa`, `net_faiz_ort_rav`, `faiz_getirili_ta`,
`faiz_getirili_maliyetli`, `faiz_getirili_ozkaynak` — **7 measure** — BASELINE_PASSTHROUGH'tan
çıkarılıp raw'dan hesaplanan `MEASURE_FUNCS`'a taşınabilir; formüllerin hepsi yukarıda
**birebir** doğrulandı (Akbank, 2025-06-30, son ondalık hane dahil eşleşiyor).

## Kalan 7 kalem test edildi (aynı gün, dördüncü geçiş) — hepsi doğrulanan BASELINE_PASSTHROUGH kalıyor

Kodda `m_maliyet_gelir`, `m_nim`, `m_nim_bzk_sonrasi`, `m_spread` fonksiyonları **var**
ama şu an kullanılmıyor (measure passthrough olduğu için `computed.json`'daki değer
`base_data`'dan geliyor, bu fonksiyonların çıktısı değil). Fonksiyonları Akbank
2025-06-30 için elle koşturup `computed.json`'daki (v29 PBI baseline) değerle
karşılaştırdım — basit `faiz_getirili_aktif`/`maliyetli_pasif` helper'larını
(lookup.py:241,251 — 4/5 bileşenli, TCMB'siz) ve TTM/avg_balance'ı doğru uyguladım:

| Measure | Hesaplanan | `computed.json` | Fark | Sonuç |
|---|---|---|---|---|
| `maliyet_gelir` | 58.61% | 54.26% | ~%8 rölatif | ❌ eşleşmiyor |
| `nim` | 2.89% | 2.63% | ~%10 rölatif | ❌ eşleşmiyor |
| `nim_bzk_sonrasi` | 1.42% | 1.63% | ~%13 rölatif | ❌ eşleşmiyor |
| `spread` | +1.25% | **-4.53%** | işaret bile ters | ❌ eşleşmiyor, büyük fark |

**Sonuç: bu 4'ü genuinely PBI'a özgü, raw'dan üretilemiyor** — koddaki "IEA/operasyonel
gelir tanımı PBI'a özgü, ~%1-5 sapma" notu doğrulandı (spread'de sapma çok daha büyük,
muhtemelen PBI'nin spread tanımı burada kullanılan basit faiz getirisi/maliyeti
oranlarından temelden farklı bir şey — belki TCMB'li 13-bileşenli `_faiz_getirili_aktif_detay`
kullanıyor, henüz kontrol edilmedi). TCMB grubundaki gibi "benim hatam" değil, gerçek bir
tanım farkı.

Kalan 3 kalemin kodda hiç fonksiyonu yok, denenecek bir şey de yok:
- `gayrinakdi_komisyon_gayrinakdi` → `m_gayrinakdi_komisyon_gayrinakdi` zaten `return None`
  (kodun kendi yorumu: "formül belirsiz")
- `maliyet_gelir_duzeltilmis`, `nim_duzeltilmis` → hiçbir `m_*` fonksiyonu yok

**Nihai durum — BASELINE_PASSTHROUGH'un 12 kaleminin tamamı test edildi:**
- **9'u** raw'dan birebir hesaplanabiliyor (bu changelog'da yukarıda doğrulandı) →
  `MEASURE_FUNCS`'a taşınmaya hazır.
- **3'ü** kalıcı kapsam dışı, formül bile yok (`gayrinakdi_komisyon_gayrinakdi`,
  `maliyet_gelir_duzeltilmis`, `nim_duzeltilmis`).
- **4'ü** formülü var ama raw'dan üretilen sonuç PBI baseline'ıyla tutmuyor
  (`maliyet_gelir`, `nim`, `nim_bzk_sonrasi`, `spread`) — bunlar da fiilen kapsam dışı,
  yalnız "denenmemiş" değil "denendi, tutmadı" statüsünde.

Toplam: 12 kalemin **9'u çözüldü, 7'si kalıcı kapsam dışı** (3 formülsüz + 4 formülü
tutmayan).

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
