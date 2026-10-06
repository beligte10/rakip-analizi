# TCMB EVDS — Bilgi Tabanı (Chatbot Sistem Bağlamı)

> Bu doküman, TCMB EVDS (Elektronik Veri Dağıtım Sistemi) API'sinden gelen verileri yorumlamak için hazırlanmıştır.
> Asistan, kullanıcı sorularını yanıtlarken önce bu dokümandaki tanımları kullanmalı; seri koduna özgü ayrıntı için `evds_katalog.md` dosyasına (katalog scripti ile üretilir) bakmalıdır.
> Bu dokümanda olmayan bir seri kodunun anlamı bilinmiyorsa **tahmin edilmemeli**, "katalogda bulunamadı" denmelidir.

---

## 1. EVDS nedir?

EVDS, Türkiye Cumhuriyet Merkez Bankası'nın (TCMB) ekonomik ve finansal istatistikleri yayımladığı veri dağıtım sistemidir. Veriler şu hiyerarşiyle organize edilir:

```
Kategori (ana başlık)
 └── Veri Grubu (datagroup)   örn. bie_dkdovytl
      └── Seri (series)       örn. TP.DK.USD.A.YTL
```

- **Kategori**: Konu başlığı (Kurlar, Fiyat Endeksleri, Faiz İstatistikleri, Ödemeler Dengesi vb.). `CATEGORY_ID` ile tanımlanır.
- **Veri grubu**: Aynı kaynak/yöntemle yayımlanan seri kümesi. Kodu genelde `bie_` ile başlar. Metaverisi (açıklama, revizyon politikası, yayın notu) grup düzeyindedir.
- **Seri**: Tek bir zaman serisi. Kodu genelde `TP.` ile başlar ve noktalarla ayrılmış bölümlerden oluşur.

## 2. Seri kodu nasıl okunur?

Seri kodları noktalarla ayrılmış bölümlerdir; soldan sağa genelden özele gider.

| Örnek kod | Bölümler | Anlam |
|---|---|---|
| `TP.DK.USD.A.YTL` | TP · DK · USD · A · YTL | TP = tablo/seri öneki, DK = döviz kuru, USD = ABD doları, A = **alış**, YTL = TL cinsinden |
| `TP.DK.USD.S.YTL` | … S … | S = **satış** |
| `TP.DK.EUR.A.YTL` | … EUR … | Euro alış |
| `TP.DK.USD.A.EF.YTL` | … EF … | EF = **efektif** (banknot) alış kuru |

Kural: Kodların bölümlerinin anlamı veri grubuna göre değişir. Bölüm anlamını koddan çıkarmak yerine **katalogdaki `SERIE_NAME` alanını** esas al.

> Not: "YTL" eki tarihsel olarak kalmıştır; bugün değerler Türk Lirası (TL/TRY) cinsindendir.

## 3. Örnek seriler (doğrulama gerektirir)

Aşağıdakiler yaygın kullanılan örneklerdir. Seri kodları ve baz yılları TCMB tarafından güncellenebilir (özellikle endekslerde baz yılı değişir); kesin bilgi için katalog dosyasını kullan.

| Seri kodu | Anlam | Birim / Not |
|---|---|---|
| `TP.DK.USD.A.YTL` | TCMB gösterge niteliğindeki ABD doları döviz alış kuru | TL / 1 USD, günlük (iş günü) |
| `TP.DK.USD.S.YTL` | ABD doları döviz satış kuru | TL / 1 USD |
| `TP.DK.EUR.A.YTL` | Euro döviz alış kuru | TL / 1 EUR |
| `TP.DK.EUR.S.YTL` | Euro döviz satış kuru | TL / 1 EUR |
| `TP.FG.J0` | TÜFE (Tüketici Fiyat Endeksi) genel | Endeks, aylık; baz yılı güncellenebilir |
| `TP.TUFE1YI.T1` | Yurt İçi ÜFE (Üretici Fiyat Endeksi) genel | Endeks, aylık |
| `TP.APIFON4` | TCMB ağırlıklı ortalama fonlama maliyeti | % (yıllık faiz), günlük |

## 4. API parametreleri

Temel sorgu biçimi (parametreler `&` ile birleştirilir):

```
.../series=TP.DK.USD.A.YTL&startDate=01-01-2024&endDate=31-12-2024&type=json&frequency=5&aggregationTypes=avg&formulas=0
```

API anahtarı (`key`) HTTP başlığında gönderilir (v3). Eski sürümde URL parametresi olarak da kullanılıyordu.

| Parametre | Zorunlu | Açıklama |
|---|---|---|
| `series` | evet | Seri kodu. Birden fazlası `-` ile birleştirilir: `TP.DK.USD.A.YTL-TP.DK.EUR.A.YTL` |
| `startDate` | evet | Başlangıç, biçim **GG-AA-YYYY** |
| `endDate` | evet | Bitiş, biçim **GG-AA-YYYY** |
| `type` | evet | `json`, `xml` veya `csv` |
| `frequency` | hayır | Çıktı frekansı (Bölüm 5) |
| `aggregationTypes` | hayır | Frekans düşürülürken kullanılacak toplulaştırma (Bölüm 6) |
| `formulas` | hayır | Değerlere uygulanacak dönüşüm (Bölüm 7) |

Çoklu seri sorgusunda `aggregationTypes` ve `formulas` da seri sayısı kadar, `-` ile ayrılarak verilebilir (örn. `avg-avg`, `0-3`).

### Metaveri uç noktaları

| Amaç | Uç nokta |
|---|---|
| Tüm kategoriler | `categories/type=json` |
| Bir kategorideki veri grupları | `datagroups/mode=2&code=<CATEGORY_ID>&type=json` |
| Tek veri grubunun bilgisi | `datagroups/mode=1&code=<bie_kodu>&type=json` |
| Tüm veri grupları | `datagroups/mode=0&type=json` |
| Bir veri grubundaki seriler | `serieList/type=json&code=<bie_kodu>` |

## 5. Frekans (`frequency`) kodları

| Kod | Frekans |
|---|---|
| 1 | Günlük (takvim günü) |
| 2 | İş günü |
| 3 | Haftalık (cuma) |
| 4 | Ayda iki kez |
| 5 | Aylık |
| 6 | 3 aylık (çeyreklik) |
| 7 | 6 aylık |
| 8 | Yıllık |

- Her serinin **orijinal (yayın) frekansı** vardır (katalogda `FREQUENCY_STR`). Veriyi yalnızca orijinal frekanstan **daha seyrek** bir frekansa çevirebilirsin (günlük → aylık gibi). Aylık seriyi günlüğe çeviremezsin.
- Frekans düşürüldüğünde birden fazla gözlem tek değere indirilir; bu işlemi `aggregationTypes` belirler.

## 6. Toplulaştırma (`aggregationTypes`)

| Değer | Anlam | Tipik kullanım |
|---|---|---|
| `avg` | Dönem ortalaması | Döviz kuru, faiz (dönem ortalaması) |
| `min` | Dönem içi en düşük | |
| `max` | Dönem içi en yüksek | |
| `first` | Dönemin ilk gözlemi | |
| `last` | Dönemin son gözlemi (dönem sonu) | Dönem sonu kur, stok değişkenleri |
| `sum` | Dönem toplamı | Akım değişkenleri (ihracat, ithalat, işlem hacmi) |

Dikkat: **Stok** değişkenlerde (bakiye, rezerv, mevduat stoğu) `sum` anlamsızdır; `last` veya `avg` kullanılmalıdır. **Akım** değişkenlerde (aylık ihracat gibi) `sum` uygundur. Endekslerde ve oranlarda (% faiz) `sum` kullanılmaz. Her serinin varsayılan yöntemi katalogda `DEFAULT_AGG_METHOD_STR` alanındadır.

## 7. Formüller (`formulas`) — veri dönüşümleri

| Kod | Ad | Hesaplama |
|---|---|---|
| 0 | Düzey | Ham değer, dönüşüm yok |
| 1 | Yüzde değişim | (Xₜ / Xₜ₋₁ − 1) × 100 — bir önceki gözleme göre |
| 2 | Fark | Xₜ − Xₜ₋₁ |
| 3 | Yıllık yüzde değişim | (Xₜ / Xₜ₋₁ yıl önce − 1) × 100 — geçen yılın aynı dönemine göre |
| 4 | Yıllık fark | Xₜ − X(aynı dönem, geçen yıl) |
| 5 | Bir önceki yılın sonuna göre yüzde değişim | Yıl başından bugüne (YTD) % değişim |
| 6 | Bir önceki yılın sonuna göre fark | YTD mutlak fark |
| 7 | Hareketli ortalama | Kayan pencere ortalaması |
| 8 | Hareketli toplam | Kayan pencere toplamı |

Önemli kurallar:
- "Önceki gözlem" **seçilen frekansa** göredir. Aylık frekansta kod 1 = aylık değişim, günlük frekansta kod 1 = günlük değişimdir.
- Enflasyon örneği: TÜFE endeksine `formulas=3` (yıllık yüzde değişim) uygulanırsa **yıllık enflasyon** elde edilir; `formulas=1` aylık enflasyonu verir.
- Formül uygulandığında yanıtta orijinal sütun yerine dönüştürülmüş değer döner. Dönüşüm sonucundaki ilk gözlemler hesaplanamadığı için boş (`null`) olabilir.
- **Faiz gibi zaten yüzde olan serilerde** "yüzde değişim" faizin değişim oranıdır, **puan farkı değildir**. Puan farkı için `formulas=2` (fark) kullan.

## 8. Yanıt yapısı ve veri okuma kuralları

JSON yanıtı `items` listesi içerir. Her öğede:
- `Tarih`: gözlem tarihi (günlük için `GG-AA-YYYY`, aylık için `YYYY-M`, çeyreklik için `YYYY-Q1`, yıllık için `YYYY`).
- Seri sütunları: seri kodundaki **noktalar alt çizgiye** çevrilir. Örn. `TP.DK.USD.A.YTL` → `TP_DK_USD_A_YTL`. Formül uygulanmışsa ad sonuna `_YUZDE_DEGISIM`, `_FARK` gibi bir ek gelebilir.
- `UNIXTIME`: tarih bilgisinin epoch karşılığı.

Okuma kuralları:
1. Boş değer (`null`, `""`) = veri yok (hafta sonu/resmi tatil, henüz yayımlanmamış veya serinin başlamadığı dönem). **Sıfır değildir.**
2. Günlük döviz kurlarında hafta sonu ve resmi tatil gözlemi yoktur.
3. Aylık/üç aylık serilerde son dönem **geçici** olabilir ve sonradan revize edilir.
4. Birim, seri adından ve veri grubu notundan okunur; birim belirsizse kullanıcıya birim uydurma.

## 9. Veri türleri (ölçü tipleri) rehberi

| Tür | Özellik | Örnek | Doğru toplulaştırma |
|---|---|---|---|
| **Fiyat / kur** | Anlık değer | USD/TL | `avg` veya `last` |
| **Endeks** | Baz yılına göre göreli düzey (baz=100) | TÜFE, ÜFE | `last` (aylık endekste genelde gerekmez); yorum için % değişim kullan |
| **Oran / faiz (%)** | Yüzde cinsinden | Politika faizi, mevduat faizi | `avg` |
| **Stok** | Belirli bir tarihteki bakiye | Rezervler, mevduat stoğu | `last` / `avg` |
| **Akım** | Dönem içinde gerçekleşen miktar | İhracat, işlem hacmi, ödemeler dengesi kalemleri | `sum` |
| **Beklenti / anket** | Anket ortalaması | Piyasa Katılımcıları Anketi | `last` / `avg` |

## 10. Sık karşılaşılan hatalar ve çözümleri

| Belirti | Olası neden | Çözüm |
|---|---|---|
| Boş / hatalı yanıt, 403 | API anahtarı hatalı veya yanlış yerde gönderildi | Anahtarı v3'te HTTP `key` başlığında gönder |
| SSL / el sıkışma hatası | TCMB sunucusu eski SSL ayarı istiyor | İstemcide legacy SSL (`OP_LEGACY_SERVER_CONNECT`) aç |
| Tarih hatası | Tarih biçimi yanlış | **GG-AA-YYYY** kullan (ISO değil) |
| Frekans hatası | Seri orijinal frekanstan daha sık isteniyor | Orijinalden seyrek bir frekans seç |
| Tüm değerler `null` | Seçilen aralıkta veri yok veya formülün ilk gözlemi | Aralığı genişlet, seri başlangıç tarihini (`START_DATE`) kontrol et |
| Sütun adı eşleşmiyor | Noktalar `_` olmuş | Seri kodunu `.` → `_` çevirerek ara |
| Çok uzun sorgu | Çok seri / çok uzun aralık | Sorguyu parçalara böl |

## 11. Chatbot davranış kuralları

1. Kullanıcı bir seri koduyla soru sorduğunda önce katalogda (`evds_katalog.md`) bu kodu ara; adı, birimi, frekansı ve veri grubunu oradan aktar.
2. Katalogda yoksa kodun bölümlerini yorumlayıp **tahmin etme**; "bu kod katalogda yok" de.
3. "Enflasyon", "kur artışı" gibi türetilmiş istekler için hangi formülün kullanılacağını açıkça belirt (örn. yıllık enflasyon → TÜFE + `formulas=3`).
4. Sayı yorumlarken **birimi ve frekansı** her zaman belirt.
5. Değerler yalnızca dönüştürülmüş/toplulaştırılmışsa bunu ("aylık ortalama", "yıllık % değişim") açıkça söyle.
6. Son dönem verisinin geçici olabileceğini, revize edilebileceğini hatırlat.
7. Yatırım tavsiyesi verme; yalnızca verinin ne ifade ettiğini açıkla.

## 12. Kaynaklar

- EVDS: https://evds3.tcmb.gov.tr (API anahtarı: Benim Sayfam → Profilim → API Key)
- Resmi "EVDS Web Servis Kullanım Kılavuzu" (EVDS yardım bölümünde PDF olarak bulunur)
