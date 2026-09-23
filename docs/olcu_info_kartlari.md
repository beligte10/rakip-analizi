# Ölçü Bilgi Kartları

<!-- Biçim: her kart "---" satırıyla ayrılır. Kart "## <Ölçü Adı>" ile başlar, hemen altında `id: <ölçü_id>` bulunur; uygulama kartı bu id ile eşleştirir. -->

---

## Toplam Aktifler

`id: toplam_aktifler`

**Tanım:** Bankanın bilançosundaki tüm varlıkların toplamı; ölçek göstergesi.

**Formül:** Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Krediler

`id: krediler`

**Tanım:** Bilançodaki net krediler ve alacaklar.

**Formül:** Bilanço 'Krediler ve Alacaklar (Toplam)'; eski TMS 39 dönemlerinde 'Krediler'. Donuk alacaklar ve karşılıklar netleştirilmiş haliyle.

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

> ℹ️ Faktoring/leasing ve donuk alacaklar dahil değil; brüt tanım için Toplam Brüt Krediler.

---

## Grup 1 Krediler

`id: grup_1_krediler`

**Tanım:** Standart nitelikli (Aşama 1) krediler.

**Formül:** Krediler (net) − Donuk Alacaklar − Grup 2 Krediler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Grup 1-2 Krediler tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

**Terimler:**

- *Krediler (net):* Bilanço 'Krediler ve Alacaklar (Toplam)'; eski TMS 39 dönemlerinde 'Krediler'. Donuk alacaklar ve karşılıklar netleştirilmiş haliyle.
- *Grup 2 Krediler:* Yakın İzlemedeki krediler: 'Krediler ve Diğer Alacaklar' + 'Ödeme Planı Uzatılanlar' + 'Diğer' alt kalemleri.

---

## Donuk Alacaklar

`id: donuk_alacaklar`

**Tanım:** Tahsili gecikmiş / takibe düşmüş (Aşama 3) krediler.

**Formül:** Donuk Alacaklar

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

> ℹ️ Düşük değer daha iyi (sıralama artan).

---

## Donuk Alacaklar (Satış ve Terkin Öncesi)

`id: donuk_alacaklar_satis_terkin_oncesi`

**Tanım:** Dönem içinde satılan veya aktiften silinen tutarlar geri eklenmiş donuk alacaklar.

**Formül:** Donuk Alacaklar + |Aktiften Silinen (Sınırlı + Şüpheli + Zarar Niteliğinde)|

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Donuk Alacak Hareket tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

> ℹ️ Silinen tutarlar YtD hareket tablosundan gelir.

---

## Grup 2 Krediler

`id: grup_2_krediler`

**Tanım:** Yakın izlemedeki (Aşama 2) krediler.

**Formül:** Yakın İzlemedeki krediler: 'Krediler ve Diğer Alacaklar' + 'Ödeme Planı Uzatılanlar' + 'Diğer' alt kalemleri.

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Grup 1-2 Krediler tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Tüketici Kredileri ve Bireysel Kredi Kartları

`id: tuketici_kredileri`

**Tanım:** Bireysel krediler ve bireysel kredi kartları toplamı (personel kredileri dahil).

**Formül:** Tüketici ve Personel Kredileri + Kredi Kartları (Toplam)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Tüketici Kredileri detay tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Bireysel Kredi Kartları

`id: bireysel_kredi_kartlari`

**Tanım:** Bireysel ve personel kredi kartı bakiyeleri.

**Formül:** Bireysel KK (TP+YP) + Personel KK (TP+YP)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Tüketici Kredileri detay tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## İhtiyaç Kredileri

`id: ihtiyac_kredileri`

**Tanım:** Genel ihtiyaç kredileri.

**Formül:** Tüketici + Personel İhtiyaç Kredisi (TP + YP + Dövize Endeksli)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Tüketici Kredileri detay tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Konut Kredileri

`id: konut_kredileri`

**Tanım:** Konut kredileri.

**Formül:** Tüketici + Personel Konut Kredisi (TP + YP + Dövize Endeksli)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Tüketici Kredileri detay tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Taşıt Kredileri

`id: tasit_kredileri`

**Tanım:** Taşıt kredileri.

**Formül:** Tüketici + Personel Taşıt Kredisi (TP + YP + Dövize Endeksli)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Tüketici Kredileri detay tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Tüzel Krediler

`id: tuzel_krediler`

**Tanım:** Bireysel olmayan (kurumsal/ticari/KOBİ) krediler.

**Formül:** Krediler (net) − Tüketici Kredileri ve Bireysel KK

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Tüketici Kredileri detay tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

**Terimler:**

- *Krediler (net):* Bilanço 'Krediler ve Alacaklar (Toplam)'; eski TMS 39 dönemlerinde 'Krediler'. Donuk alacaklar ve karşılıklar netleştirilmiş haliyle.

> ℹ️ Doğrudan raporlanmaz, farktan türetilir.

---

## TP Aktifler / Toplam Aktifler

`id: tp_aktifler_ta`

**Tanım:** Aktiflerin Türk parası kısmının payı.

**Formül:** TP Toplam Aktifler / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Finansal Varlıklar (Net) / Toplam Aktifler

`id: finansal_varliklar_net_ta`

**Tanım:** Finansal varlıkların aktif içindeki payı.

**Formül:** (Finansal Varlıklar (Net) + İtfa Edilmiş Maliyetle Ölçülen FV) / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Menkul Kıymetler / Toplam Aktifler

`id: menkul_kiymetler_ta`

**Tanım:** Menkul kıymet portföyünün aktif içindeki payı.

**Formül:** Menkul Kıymetler / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Menkul Kıymetler:* GUD Farkı K/Z Yansıtılan FV + GUD Farkı DKG Yansıtılan FV + İtfa Edilmiş Maliyetle Ölçülen FV + Türev FV + Satılmaya Hazır FV (eski) + Vadeye Kadar Elde Tutulacak (eski).

---

## Krediler / Toplam Aktifler

`id: krediler_ta`

**Tanım:** Net kredilerin aktif içindeki payı.

**Formül:** Krediler (net) / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Krediler (net):* Bilanço 'Krediler ve Alacaklar (Toplam)'; eski TMS 39 dönemlerinde 'Krediler'. Donuk alacaklar ve karşılıklar netleştirilmiş haliyle.

> ℹ️ Brüt versiyonu: brut_krediler_ta.

---

## Grup 1 Krediler / Toplam Krediler

`id: grup_1_krediler_toplam`

**Tanım:** Standart nitelikli kredilerin toplam krediler içindeki payı.

**Formül:** Grup 1 Krediler / Toplam Brüt Krediler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Grup 1-2 Krediler

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Brüt Krediler:* Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler (NPL dahil). TP/YP kırılımı aynı kalemlerin TP/YP kolonlarıyla.

---

## Donuk Alacaklar / Toplam Krediler (NPL Rasyosu)

`id: npl_rasyosu`

**Tanım:** Takipteki kredi oranı (NPL).

**Formül:** Donuk Alacaklar / Krediler (net)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Krediler (net):* Bilanço 'Krediler ve Alacaklar (Toplam)'; eski TMS 39 dönemlerinde 'Krediler'. Donuk alacaklar ve karşılıklar netleştirilmiş haliyle.

> ℹ️ Payda net krediler; düşük değer daha iyi.

---

## NPL Rasyosu (Satış ve Terkin Öncesi)

`id: npl_rasyosu_satis_terkin_oncesi`

**Tanım:** Satış ve aktiften silme etkisi arındırılmış NPL oranı.

**Formül:** (Donuk Alacaklar + |Aktiften Silinen|) / (Krediler (net) + |Aktiften Silinen|)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Donuk Alacak Hareket tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Krediler (net):* Bilanço 'Krediler ve Alacaklar (Toplam)'; eski TMS 39 dönemlerinde 'Krediler'. Donuk alacaklar ve karşılıklar netleştirilmiş haliyle.

---

## Net NPL Formasyon Rasyosu

`id: npl_formasyonu`

**Tanım:** Dönemde oluşan net yeni NPL'in kredilere oranı.

**Formül:** (Σ Dönem İçi İntikal + Diğer Giriş + Σ Dönem İçi Tahsilat + Diğer Çıkış) × 12 / ay sayısı / Ortalama Toplam Brüt Krediler

**Hesaplama dönemi:** Pay: yılbaşından kümülatif (YtD), yıllıklandırılmış (×12/ay) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Donuk Alacak Hareket tablosu; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Brüt Krediler:* Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler (NPL dahil). TP/YP kırılımı aynı kalemlerin TP/YP kolonlarıyla.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

> ℹ️ Tahsilatlar ham veride negatif. Pay YtD, yıllıklandırılmaz.

---

## Donuk Alacaklar Dönemiçi Tahsilat / Ortalama Krediler

`id: donuk_tahsilat_ort_krediler`

**Tanım:** Dönem içinde donuk alacaklardan yapılan tahsilatın kredilere oranı.

**Formül:** −(Σ Dönem İçi Tahsilat + Diğer Çıkış) / Ortalama Toplam Brüt Krediler

**Hesaplama dönemi:** Pay: yılbaşından kümülatif (YtD) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Donuk Alacak Hareket tablosu; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Brüt Krediler:* Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler (NPL dahil). TP/YP kırılımı aynı kalemlerin TP/YP kolonlarıyla.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

> ℹ️ Pozitif gösterim için işaret çevrilir.

---

## Donuk Alacaklar Dönemiçi İntikal / Ortalama Krediler

`id: donuk_intikal_ort_krediler`

**Tanım:** Dönem içinde donuk alacağa geçen tutarın kredilere oranı.

**Formül:** (Σ Dönem İçi İntikal + Diğer Giriş) / Ortalama Toplam Brüt Krediler

**Hesaplama dönemi:** Pay: yılbaşından kümülatif (YtD) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Donuk Alacak Hareket tablosu; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Brüt Krediler:* Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler (NPL dahil). TP/YP kırılımı aynı kalemlerin TP/YP kolonlarıyla.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

---

## Grup 2 Krediler / Toplam Krediler

`id: grup_2_krediler_toplam`

**Tanım:** Yakın izlemedeki kredilerin toplam kredilere oranı.

**Formül:** Grup 2 Krediler / (Krediler (net) − Kiralama İşlemlerinden Alacaklar)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Grup 1-2 Krediler; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Krediler (net):* Bilanço 'Krediler ve Alacaklar (Toplam)'; eski TMS 39 dönemlerinde 'Krediler'. Donuk alacaklar ve karşılıklar netleştirilmiş haliyle.
- *Grup 2 Krediler:* Yakın İzlemedeki krediler: 'Krediler ve Diğer Alacaklar' + 'Ödeme Planı Uzatılanlar' + 'Diğer' alt kalemleri.

> ⚠️ Diğer "…/Toplam Krediler" oranlarından farklı payda (brüt değil).

---

## Grup 2 Krediler / Çekirdek Sermaye

`id: grup_2_krediler_cekirdek_sermaye`

**Tanım:** Aşama 2 kredilerin çekirdek sermayeye oranı; sermaye üzerindeki potansiyel risk baskısı.

**Formül:** Grup 2 Krediler / Çekirdek Sermaye Toplamı

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Grup 1-2 Krediler; Sermaye Yeterliliği tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Grup 2 Krediler:* Yakın İzlemedeki krediler: 'Krediler ve Diğer Alacaklar' + 'Ödeme Planı Uzatılanlar' + 'Diğer' alt kalemleri.

---

## Tüketici Kredileri / Toplam Krediler

`id: tuketici_toplam`

**Tanım:** Bireysel kredilerin toplam kredi içindeki payı.

**Formül:** Tüketici Kredileri ve Bireysel KK / Toplam Brüt Krediler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Tüketici Kredileri detay; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Brüt Krediler:* Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler (NPL dahil). TP/YP kırılımı aynı kalemlerin TP/YP kolonlarıyla.

---

## Grup 2 Tüketici Kredileri / Tüketici Kredileri

`id: grup_2_tuketici_tuketici`

**Tanım:** Bireysel kredilerde Aşama 2 oranı.

**Formül:** Grup 2 Tüketici Kredileri / Tüketici Kredileri (KK hariç)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Grup 1-2 Krediler; Tüketici Kredileri detay

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ℹ️ Payda kredi kartlarını içermez, KMH dahildir.

---

## Bireysel Kredi Kartları / Toplam Krediler

`id: bkk_toplam`

**Tanım:** Bireysel kredi kartlarının toplam kredi içindeki payı.

**Formül:** Bireysel Kredi Kartları / Toplam Brüt Krediler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Tüketici Kredileri detay; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Brüt Krediler:* Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler (NPL dahil). TP/YP kırılımı aynı kalemlerin TP/YP kolonlarıyla.

---

## İhtiyaç Kredileri / Toplam Krediler

`id: ihtiyac_toplam`

**Tanım:** İhtiyaç kredilerinin toplam kredi içindeki payı.

**Formül:** İhtiyaç Kredileri / Toplam Brüt Krediler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Tüketici Kredileri detay; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Brüt Krediler:* Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler (NPL dahil). TP/YP kırılımı aynı kalemlerin TP/YP kolonlarıyla.

---

## Konut Kredileri / Tüketici Kredileri

`id: konut_tuketici`

**Tanım:** Konut kredilerinin bireysel krediler içindeki payı.

**Formül:** Konut Kredileri / Tüketici Kredileri ve Bireysel KK

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Tüketici Kredileri detay

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Konut Kredileri / TP Pasifler

`id: konut_tp_pasifler`

**Tanım:** Konut kredilerinin TP yabancı kaynaklara oranı (vade uyumsuzluğu göstergesi).

**Formül:** Konut Kredileri / (TP Toplam Pasifler − TP Özkaynaklar)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Tüketici Kredileri detay; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Taşıt Kredileri / Tüketici Kredileri

`id: tasit_tuketici`

**Tanım:** Taşıt kredilerinin bireysel krediler içindeki payı.

**Formül:** Taşıt Kredileri / Tüketici Kredileri ve Bireysel KK

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Tüketici Kredileri detay

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Tüzel Krediler / Toplam Krediler

`id: tuzel_toplam`

**Tanım:** Tüzel kredilerin toplam kredi içindeki payı.

**Formül:** Tüzel Krediler / Toplam Brüt Krediler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Tüketici Kredileri detay

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Brüt Krediler:* Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler (NPL dahil). TP/YP kırılımı aynı kalemlerin TP/YP kolonlarıyla.

---

## Grup 2 Tüzel Krediler / Tüzel Krediler

`id: grup_2_tuzel_tuzel`

**Tanım:** Tüzel kredilerde Aşama 2 oranı.

**Formül:** (Grup 2 Toplam − Grup 2 Kredi Kartları − Grup 2 Tüketici − Grup 2 Mali Kesim) / Tüzel Krediler (Kredi Kartları Hariç)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Grup 1-2 Krediler; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Tüzel Krediler (Kredi Kartları Hariç):* Tüzel Krediler − Tüzel Kredi Kartları (toplam kredi kartı − bireysel kredi kartları).

---

## Dış Ticaret Kredileri / Toplam Krediler

`id: dis_ticaret_toplam`

**Tanım:** İhracat ve ithalat kredilerinin toplam kredi içindeki payı.

**Formül:** (İhracat + İthalat Kredileri; Standart + Grup 2) / Toplam Brüt Krediler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Grup 1-2 Krediler; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Brüt Krediler:* Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler (NPL dahil). TP/YP kırılımı aynı kalemlerin TP/YP kolonlarıyla.

---

## Mali Kesime Verilen Krediler / Toplam Krediler

`id: mali_kesim_toplam`

**Tanım:** Finansal kuruluşlara verilen kredilerin payı.

**Formül:** Mali Kesime Verilen Krediler (Standart Nitelikli) / Toplam Brüt Krediler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Grup 1-2 Krediler; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Brüt Krediler:* Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler (NPL dahil). TP/YP kırılımı aynı kalemlerin TP/YP kolonlarıyla.

> ℹ️ Pay yalnız Grup 1 (Standart) kısmı içerir.

---

## TP Krediler / Toplam Krediler

`id: tp_krediler_toplam`

**Tanım:** TL kredilerin toplam kredi içindeki payı.

**Formül:** TP Toplam Brüt Krediler / Toplam Brüt Krediler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Brüt Krediler:* Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler (NPL dahil). TP/YP kırılımı aynı kalemlerin TP/YP kolonlarıyla.

---

## USD Cinsi Krediler / YP Krediler

`id: usd_yp_krediler`

**Tanım:** YP krediler içinde USD cinsinin payı.

**Formül:** USD Cinsi Krediler / YP Krediler Toplamı

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Kur Riski tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## EURO Cinsi Krediler / YP Krediler

`id: euro_yp_krediler`

**Tanım:** YP krediler içinde EUR cinsinin payı.

**Formül:** EUR Cinsi Krediler / YP Krediler Toplamı

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Kur Riski tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Ortaklık Yatırımları / Toplam Aktifler

`id: ortaklik_yatirimlari_ta`

**Tanım:** İştirak/bağlı ortaklık yatırımlarının aktif içindeki payı.

**Formül:** Ortaklık Yatırımları / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Diğer Aktifler / Toplam Aktifler

`id: diger_aktifler_ta`

**Tanım:** Faiz getirmeyen diğer aktiflerin payı.

**Formül:** (Maddi Duran V. + Maddi Olmayan Duran V. + Yatırım Amaçlı Gayrimenkuller + Diğer Aktifler + Vergi Varlığı) / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Faiz (Kar Payı) Getirili Aktifler / Toplam Aktifler

`id: faiz_getirili_ta`

**Tanım:** Faiz/kâr payı getiren aktiflerin toplam aktife oranı.

**Formül:** Faiz Getirili Aktifler (detaylı) / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; TCMB tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Faiz (Kar Payı) Getirili Aktifler (detaylı, 13 bileşen):* TCMB Hesabı (TP+YP) + Bankalar + Para Piyasalarından Alacaklar + GUD K/Z FV + GUD DKG FV + İtfa Edilmiş Maliyet FV + Satılmaya Hazır (eski) + VKET (eski) + Türev FV + Riskten Korunma Türev FV + Toplam Brüt Krediler − |Beklenen Zarar Karşılıkları|.

---

## Faiz (Kar Payı) Getirili Aktifler / Maliyetli Pasifler

`id: faiz_getirili_maliyetli`

**Tanım:** Getirili aktiflerin maliyetli pasifleri kaç kat karşıladığı.

**Formül:** Faiz Getirili Aktifler (detaylı) / Faiz Maliyetli Pasifler (detaylı)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; TCMB tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** Kat

**Terimler:**

- *Faiz (Kar Payı) Getirili Aktifler (detaylı, 13 bileşen):* TCMB Hesabı (TP+YP) + Bankalar + Para Piyasalarından Alacaklar + GUD K/Z FV + GUD DKG FV + İtfa Edilmiş Maliyet FV + Satılmaya Hazır (eski) + VKET (eski) + Türev FV + Riskten Korunma Türev FV + Toplam Brüt Krediler − |Beklenen Zarar Karşılıkları|.
- *Faiz (Kar Payı) Maliyetli Pasifler (detaylı, 9 bileşen):* Vadeli Mevduat + Alınan Krediler + Para Piyasalarına Borçlar + İhraç Edilen MK (Net) + GUD K/Z Finansal Yükümlülükler + Türev Finansal Yükümlülükler + Faktoring Borçları + Kiralama Borçları + Sermaye Benzeri Krediler.

> ℹ️ Birim: kat.

---

## YP Aktifler / YP Pasifler

`id: yp_aktifler_toplam_pasifler`

**Tanım:** YP aktiflerin YP pasifleri karşılama oranı.

**Formül:** YP Toplam Aktifler / YP Toplam Pasifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ℹ️ Ad "YP Pasifler" diyor; id'deki "toplam_pasifler" eski tanımdan kalma.

---

## Ortalama Faiz (Kar Payı) Getirili Aktifler / Ortalama Özkaynaklar

`id: faiz_getirili_ozkaynak`

**Tanım:** Getirili aktiflerin özkaynağa oranı (kaldıraç).

**Formül:** Ort. Faiz Getirili Aktifler (detaylı) / Ort. Özkaynaklar

**Hesaplama dönemi:** Pay ve payda: 12 aylık ortalama bakiye

**Kaynak:** Bilanço; TCMB tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** Kat

**Terimler:**

- *Faiz (Kar Payı) Getirili Aktifler (detaylı, 13 bileşen):* TCMB Hesabı (TP+YP) + Bankalar + Para Piyasalarından Alacaklar + GUD K/Z FV + GUD DKG FV + İtfa Edilmiş Maliyet FV + Satılmaya Hazır (eski) + VKET (eski) + Türev FV + Riskten Korunma Türev FV + Toplam Brüt Krediler − |Beklenen Zarar Karşılıkları|.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

> ℹ️ Birim: kat.

---

## Yabancı Para Net Genel Pozisyonu / Toplam Özkaynaklar

`id: yp_net_pozisyon_ozkaynak`

**Tanım:** Açık/fazla döviz pozisyonunun yasal özkaynağa oranı.

**Formül:** (YP Net Bilanço Pozisyonu + YP Net Nazım Hesap Pozisyonu) / Toplam Özkaynaklar (Ana + Katkı Sermaye)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Kur Riski tablosu; Özkaynak Kalemleri tablosu

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## NPL Karşılama Oranı

`id: npl_karsilama_orani`

**Tanım:** Donuk alacakların ayrılan karşılıkla ne ölçüde karşılandığı.

**Formül:** |Beklenen Zarar Karşılıkları| / Donuk Alacaklar

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ℹ️ Karşılık toplam BZK (Aşama 1-2-3 birlikte) olabilir; teyit edilmeli.

---

## Mevduat

`id: mevduat`

**Tanım:** Toplam mevduat (katılım bankalarında toplanan fonlar).

**Formül:** Mevduat

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Toplam Kaynak

`id: toplam_kaynak`

**Tanım:** Mevduat ve piyasa borçlanmasından oluşan ana fon kaynağı.

**Formül:** Mevduat + Alınan Krediler + İhraç Edilen Menkul Kıymetler (Net). Para piyasalarına borçlar DAHİL DEĞİL.

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

> ℹ️ Para piyasalarına borçlar hariç; dahil tanım: Toplam Fonlama.

---

## Kıymetli Maden Mevduatı

`id: kiymetli_maden_mevduati`

**Tanım:** Altın ve diğer kıymetli maden cinsinden mevduat.

**Formül:** Kıymetli Maden Depo Hesabı

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Mevduat / Katılım Fonu detay tablosu

**Kategori:** Bilanço › Pasifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Vadesiz Mevduat

`id: vadesiz_mevduat`

**Tanım:** Vadesiz (özel cari) mevduat.

**Formül:** Vadesiz Mevduat

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Mevduat / Katılım Fonu detay tablosu

**Kategori:** Bilanço › Pasifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Vadeli Mevduat

`id: vadeli_mevduat`

**Tanım:** Vadeli mevduat / katılma hesapları.

**Formül:** Mevduat − Vadesiz Mevduat

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Mevduat detay

**Kategori:** Bilanço › Pasifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

> ℹ️ Farktan türetilir.

---

## Resmi Kurumlar Mevduatı

`id: resmi_kurumlar_mevduat`

**Tanım:** Resmi kuruluşlardan toplanan mevduat.

**Formül:** Resmi Kuruluşlar Mevduatı

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Mevduat / Katılım Fonu detay tablosu

**Kategori:** Bilanço › Pasifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Özkaynaklar

`id: ozkaynaklar`

**Tanım:** Bilanço özkaynakları.

**Formül:** Özkaynaklar

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

> ℹ️ Yasal özkaynaktan farklı; bkz. toplam_ozkaynaklar_regulasyon.

---

## Alınan Krediler ve İ.E.M.K / Toplam Kaynak

`id: alinan_krediler_iemk_toplam_kaynak`

**Tanım:** Borçlanma ve ihraçların toplam kaynak içindeki payı.

**Formül:** (Alınan Krediler + İhraç Edilen MK) / Toplam Kaynak

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Kaynak:* Mevduat + Alınan Krediler + İhraç Edilen Menkul Kıymetler (Net). Para piyasalarına borçlar DAHİL DEĞİL.

---

## TP Alınan Krediler ve İ.E.M.K / Toplam Alınan Krediler ve İ.E.M.K

`id: tp_alinan_toplam_alinan`

**Tanım:** Borçlanma ve ihraçların TL kısmının payı.

**Formül:** TP (Alınan Krediler + İhraç Edilen MK) / (Alınan Krediler + İhraç Edilen MK)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Krediler / Mevduat

`id: krediler_mevduat`

**Tanım:** Kredi/mevduat oranı (LDR).

**Formül:** Krediler (net) / Mevduat

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Krediler (net):* Bilanço 'Krediler ve Alacaklar (Toplam)'; eski TMS 39 dönemlerinde 'Krediler'. Donuk alacaklar ve karşılıklar netleştirilmiş haliyle.

---

## Tüzel Krediler / Tüzel Mevduat

`id: tuzel_krediler_tuzel_mevduat`

**Tanım:** Tüzel kredilerin tüzel mevduatla fonlanma oranı.

**Formül:** Tüzel Krediler / Tüzel Mevduat

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Mevduat detay

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Tüzel Mevduat:* Ticari Kuruluşlar + Diğer Kuruluşlar mevduatı (Resmi Kuruluşlar hariç). Katılım bankalarında ayrıca özel cari hesaplardaki yurtiçi/yurtdışı yerleşik tüzel kişiler.

---

## Krediler / Altındışı Mevduat

`id: krediler_altindisi_mevduat`

**Tanım:** Altın mevduatı hariç kredi/mevduat oranı.

**Formül:** Krediler (net) / (Mevduat − Kıymetli Maden Mevduatı)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Mevduat detay

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Krediler (net):* Bilanço 'Krediler ve Alacaklar (Toplam)'; eski TMS 39 dönemlerinde 'Krediler'. Donuk alacaklar ve karşılıklar netleştirilmiş haliyle.

---

## Krediler / Toplam Kaynak

`id: krediler_toplam_kaynak`

**Tanım:** Kredilerin toplam kaynakla fonlanma oranı.

**Formül:** Toplam Brüt Krediler / Toplam Kaynak

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Brüt Krediler:* Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler (NPL dahil). TP/YP kırılımı aynı kalemlerin TP/YP kolonlarıyla.
- *Toplam Kaynak:* Mevduat + Alınan Krediler + İhraç Edilen Menkul Kıymetler (Net). Para piyasalarına borçlar DAHİL DEĞİL.

---

## TP Krediler / TP Kaynak

`id: tp_krediler_tp_kaynak`

**Tanım:** TL kredilerin TL kaynaklarla fonlanma oranı.

**Formül:** TP Krediler (net) / TP (Mevduat + Alınan Krediler + İhraç Edilen MK)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Krediler (net):* Bilanço 'Krediler ve Alacaklar (Toplam)'; eski TMS 39 dönemlerinde 'Krediler'. Donuk alacaklar ve karşılıklar netleştirilmiş haliyle.

> ℹ️ Pay net krediler (brüt değil).

---

## YP Krediler / YP Altındışı Kaynak

`id: yp_krediler_yp_altindisi_kaynak`

**Tanım:** YP kredilerin altın hariç YP kaynaklarla fonlanma oranı.

**Formül:** YP Krediler (net) / (YP Kaynak − Kıymetli Maden Mevduatı)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Mevduat detay

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Krediler (net):* Bilanço 'Krediler ve Alacaklar (Toplam)'; eski TMS 39 dönemlerinde 'Krediler'. Donuk alacaklar ve karşılıklar netleştirilmiş haliyle.

---

## Vadesiz Mevduat / Toplam Mevduat

`id: vadesiz_mevduat_toplam_mevduat`

**Tanım:** Vadesiz mevduat payı (düşük maliyetli fon).

**Formül:** Vadesiz Mevduat / Mevduat

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Mevduat detay

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Kıymetli Maden Mevduatı / Toplam Mevduat

`id: kiymetli_maden_toplam_mevduat`

**Tanım:** Altın mevduatının mevduat içindeki payı.

**Formül:** Kıymetli Maden Mevduatı / Mevduat

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Mevduat detay

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Vadesiz Mevduat / Toplam Kaynak

`id: vadesiz_mevduat_toplam_kaynak`

**Tanım:** Vadesiz mevduatın toplam kaynak içindeki payı.

**Formül:** Vadesiz Mevduat / Toplam Kaynak

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Mevduat detay

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Kaynak:* Mevduat + Alınan Krediler + İhraç Edilen Menkul Kıymetler (Net). Para piyasalarına borçlar DAHİL DEĞİL.

---

## TP Mevduat / Toplam Mevduat

`id: tp_mevduat_toplam_mevduat`

**Tanım:** TL mevduatın payı.

**Formül:** TP Mevduat / Mevduat

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## TP Mevduat / Altındışı Mevduat

`id: tp_mevduat_altindisi_mevduat`

**Tanım:** TL mevduatın altın hariç mevduat içindeki payı.

**Formül:** TP Mevduat / (Mevduat − Kıymetli Maden Mevduatı)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Mevduat detay

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## TP Kaynak / Toplam Kaynak

`id: tp_kaynak_toplam_kaynak`

**Tanım:** TL kaynakların payı.

**Formül:** TP (Mevduat + Alınan Krediler + İhraç Edilen MK) / Toplam Kaynak

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Kaynak:* Mevduat + Alınan Krediler + İhraç Edilen Menkul Kıymetler (Net). Para piyasalarına borçlar DAHİL DEĞİL.

---

## Toplam Kaynak / Toplam Pasifler

`id: toplam_kaynak_toplam_pasifler`

**Tanım:** Toplam kaynağın pasif içindeki payı.

**Formül:** Toplam Kaynak / Toplam Pasifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Kaynak:* Mevduat + Alınan Krediler + İhraç Edilen Menkul Kıymetler (Net). Para piyasalarına borçlar DAHİL DEĞİL.

---

## TP Pasifler / Toplam Pasifler (Özkaynaklar Hariç)

`id: tp_pasifler_toplam_pasifler_ozkaynak_haric`

**Tanım:** TL pasiflerin toplam pasiflere oranı.

**Formül:** TP Toplam Pasifler / Toplam Pasifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ⚠️ Adı "Özkaynaklar Hariç" olsa da PBI DAX'ı paydayı Toplam Pasifler (özkaynak dahil) alıyor; birebir uyuldu.

---

## Sermaye Benzeri Krediler / Toplam Pasifler

`id: sermaye_benzeri_pasifler`

**Tanım:** Sermaye benzeri borçların pasif içindeki payı.

**Formül:** Sermaye Benzeri Krediler / Toplam Pasifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Para Piyasasına Borçlar / Toplam Pasifler

`id: ppborclari_pasifler`

**Tanım:** Para piyasası borçlarının pasif içindeki payı.

**Formül:** Para Piyasalarına Borçlar / Toplam Pasifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Faiz (Kar Payı) Maliyetli Pasifler / Toplam Pasifler

`id: maliyetli_pasifler_toplam_pasifler`

**Tanım:** Faiz/kâr payı maliyeti olan pasiflerin payı.

**Formül:** Faiz Maliyetli Pasifler (detaylı) / Toplam Pasifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Mevduat detay

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Faiz (Kar Payı) Maliyetli Pasifler (detaylı, 9 bileşen):* Vadeli Mevduat + Alınan Krediler + Para Piyasalarına Borçlar + İhraç Edilen MK (Net) + GUD K/Z Finansal Yükümlülükler + Türev Finansal Yükümlülükler + Faktoring Borçları + Kiralama Borçları + Sermaye Benzeri Krediler.

---

## Serbest Sermaye / Toplam Aktifler

`id: serbest_sermaye_ta`

**Tanım:** Duran varlıklara bağlanmamış özkaynağın aktife oranı.

**Formül:** (Özkaynaklar − Ortaklık Yatırımları − Maddi Duran V. − Maddi Olmayan Duran V.) / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Sermaye Yeterlilik Rasyosu (SYR)

`id: syr`

**Tanım:** Sermaye yeterlilik rasyosu.

**Formül:** BDDK raporlanan Sermaye Yeterlilik Rasyosu (%)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Sermaye oranları tablosu

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ℹ️ Hesaplanmaz, raporlanan oran alınır.

---

## Çekirdek Sermaye Yeterliliği Oranı

`id: cekirdek_syr`

**Tanım:** Çekirdek sermaye (CET1) yeterlilik oranı.

**Formül:** BDDK raporlanan Çekirdek Sermaye Yeterliliği Oranı (%)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Sermaye oranları tablosu

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ℹ️ Hesaplanmaz, raporlanan oran alınır.

---

## Gayrinakdi Krediler (Garanti ve Kefaletler)

`id: gayrinakdi_krediler`

**Tanım:** Teminat mektupları, akreditifler vb. garanti ve kefaletler.

**Formül:** Garanti ve Kefaletler, Toplam

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Nazım Hesaplar (Bilanço Dışı)

**Kategori:** Bilanço › Bilanço Dışı · **Tip:** Büyüklük (Stok) · **Birim:** TL

> ℹ️ Toplam satırı negatifse alt kalemlerin toplamı kullanılır.

---

## Net Dönem Karı (Zararı)

`id: net_donem_kari`

**Tanım:** Vergi sonrası net dönem kârı.

**Formül:** Net Dönem Karı / Zararı

**Hesaplama dönemi:** Yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Büyüklük (Akım) · **Birim:** TL

> ℹ️ Ara çeyreklerde yılbaşından kümülatif; çeyrekler arası kıyasta dikkat.

---

## Brüt Faaliyet Karı / Zararı

`id: brut_faaliyet_kari`

**Tanım:** Karşılık ve giderler sonrası faaliyet kârı.

**Formül:** Net Faaliyet Karı / Zararı

**Hesaplama dönemi:** Yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Büyüklük (Akım) · **Birim:** TL

> ℹ️ Ad "brüt" diyor, kaynak kalem "Net Faaliyet Karı".

---

## Faiz (Kar Payı) Gelirleri

`id: faiz_gelirleri`

**Tanım:** Faiz / kâr payı gelirleri.

**Formül:** Faiz Gelirleri

**Hesaplama dönemi:** Yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Büyüklük (Akım) · **Birim:** TL

---

## Faiz (Kar Payı) Giderleri

`id: faiz_giderleri`

**Tanım:** Faiz / kâr payı giderleri.

**Formül:** Faiz Giderleri

**Hesaplama dönemi:** Yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Büyüklük (Akım) · **Birim:** TL

---

## Net Faiz (Kar Payı) Geliri (Gideri)

`id: net_faiz_geliri`

**Tanım:** Net faiz / kâr payı geliri.

**Formül:** Net Faiz Geliri / Gideri

**Hesaplama dönemi:** Yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Büyüklük (Akım) · **Birim:** TL

---

## Alınan Ücret ve Komisyonlar

`id: alinan_ucret_komisyonlar`

**Tanım:** Alınan ücret ve komisyonlar.

**Formül:** Alınan Ücret ve Komisyonlar

**Hesaplama dönemi:** Yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Büyüklük (Akım) · **Birim:** TL

---

## G.Nakdi Kredilerden Alınan Ücret ve Komisyonlar

`id: gnakdi_alinan_ucret_komisyonlar`

**Tanım:** Gayrinakdi kredilerden alınan komisyonlar.

**Formül:** Gayri Nakdi Kredilerden (alınan ücret ve komisyon alt kalemi)

**Hesaplama dönemi:** Yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Büyüklük (Akım) · **Birim:** TL

---

## Verilen Ücret ve Komisyonlar

`id: verilen_ucret_komisyonlar`

**Tanım:** Ödenen ücret ve komisyonlar.

**Formül:** Verilen Ücret ve Komisyonlar

**Hesaplama dönemi:** Yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Büyüklük (Akım) · **Birim:** TL

---

## Net Ücret ve Komisyonlar

`id: net_ucret_komisyonlar`

**Tanım:** Net ücret ve komisyon geliri.

**Formül:** Net Ücret ve Komisyon Gelirleri / Giderleri

**Hesaplama dönemi:** Yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Büyüklük (Akım) · **Birim:** TL

---

## Diğer Faaliyet Giderleri (Operasyonel Giderler)

`id: diger_faaliyet_giderleri`

**Tanım:** Toplam operasyonel giderler (PBI adı: "Diğer Faaliyet Giderleri (OPEX)").

**Formül:** Personel Giderleri + Diğer Faaliyet Giderleri

**Hesaplama dönemi:** Yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Büyüklük (Akım) · **Birim:** TL

---

## Net Ticari Kar (Zarar)

`id: net_ticari_kar`

**Tanım:** Sermaye piyasası, türev ve kambiyo işlemleri net sonucu.

**Formül:** Ticari Kar / Zarar (Net)

**Hesaplama dönemi:** Yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Büyüklük (Akım) · **Birim:** TL

---

## Reklam Giderleri

`id: reklam_giderleri`

**Tanım:** Reklam ve ilan giderleri.

**Formül:** Reklam ve İlan Giderleri

**Hesaplama dönemi:** Yılbaşından kümülatif (YtD)

**Kaynak:** Faaliyet Giderleri detay dipnotu

**Kategori:** Gelir Tablosu · **Tip:** Büyüklük (Akım) · **Birim:** TL

> ℹ️ Sıralama azalan (en çok harcayan üstte).

---

## Personel Giderleri

`id: personel_giderleri`

**Tanım:** Personel giderleri.

**Formül:** Personel Giderleri (−)

**Hesaplama dönemi:** Yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Büyüklük (Akım) · **Birim:** TL

---

## Karşılık Giderleri

`id: karsilik_giderleri`

**Tanım:** Kredi ve diğer alacaklar için ayrılan beklenen zarar karşılığı gideri.

**Formül:** Kredi ve Diğer Alacaklar Değer Düşüş Karşılığı (−)

**Hesaplama dönemi:** Yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Büyüklük (Akım) · **Birim:** TL

---

## Ortalama Aktif Karlılığı (ROAA)

`id: roaa`

**Tanım:** Ortalama aktif kârlılığı.

**Formül:** TTM Net Dönem Karı / Ortalama Toplam Aktifler

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Gelir Tablosu; Bilanço

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

---

## Ortalama Özkaynak Karlılığı (ROAE)

`id: roae`

**Tanım:** Ortalama özkaynak kârlılığı.

**Formül:** TTM Net Dönem Karı / Ortalama Özkaynaklar

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Gelir Tablosu; Bilanço

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

---

## RORWA

`id: rorwa`

**Tanım:** Risk ağırlıklı varlık kârlılığı.

**Formül:** TTM Net Dönem Karı / Ortalama RAV

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Gelir Tablosu; Sermaye Yeterliliği

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

> ℹ️ RAV yalnız kredi riski (bkz. rav notu).

---

## Net Faiz (Kar Payı) Geliri / Ortalama RAV

`id: net_faiz_ort_rav`

**Tanım:** Risk ağırlıklı varlık başına net faiz geliri.

**Formül:** TTM Net Faiz Geliri / Ortalama RAV

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Gelir Tablosu; Sermaye Yeterliliği

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

---

## Faiz (Kar Payı) Getirili Aktiflerin Getirisi

`id: faiz_getirili_aktif_getirisi`

**Tanım:** Getirili aktiflerin ortalama getirisi.

**Formül:** TTM Faiz Gelirleri / Ort. Faiz Getirili Aktifler (detaylı)

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Gelir Tablosu; Bilanço; TCMB tablosu

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *Faiz (Kar Payı) Getirili Aktifler (detaylı, 13 bileşen):* TCMB Hesabı (TP+YP) + Bankalar + Para Piyasalarından Alacaklar + GUD K/Z FV + GUD DKG FV + İtfa Edilmiş Maliyet FV + Satılmaya Hazır (eski) + VKET (eski) + Türev FV + Riskten Korunma Türev FV + Toplam Brüt Krediler − |Beklenen Zarar Karşılıkları|.
- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

---

## Faiz (Kar Payı) Gideri / Faiz (Kar Payı) Geliri

`id: faiz_gideri_faiz_geliri`

**Tanım:** Faiz gelirinin ne kadarının faiz giderine gittiği.

**Formül:** Faiz Giderleri / Faiz Gelirleri

**Hesaplama dönemi:** Pay ve payda: yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

> ℹ️ PBI raporundaki gibi yılbaşından bugüne (YtD) oran; yıllıklandırılmaz. Aralık dışındaki çeyreklerde TTM oranından farklıdır.

---

## Faaliyet Giderleri / Ortalama Aktifler

`id: faaliyet_gid_ort_aktif`

**Tanım:** Operasyonel verimlilik: aktif başına faaliyet gideri.

**Formül:** TTM Operasyonel Giderler (OPEX) / Ortalama Toplam Aktifler

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Gelir Tablosu; Bilanço

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.
- *Operasyonel Giderler (OPEX):* Personel Giderleri + Diğer Faaliyet Giderleri.

> ℹ️ Personel giderleri dahil (PBI tanımı).

---

## Faiz (Kar Payı) Maliyetli Pasiflerin Maliyeti

`id: faiz_maliyetli_pasif_maliyeti`

**Tanım:** Maliyetli pasiflerin ortalama maliyeti.

**Formül:** TTM Faiz Giderleri / Ortalama Faiz (Kar Payı) Maliyetli Pasifler (detaylı, 9 bileşen)

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Gelir Tablosu; Bilanço

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *Faiz (Kar Payı) Maliyetli Pasifler (detaylı, 9 bileşen):* Vadeli Mevduat + Alınan Krediler + Para Piyasalarına Borçlar + İhraç Edilen MK (Net) + GUD K/Z Finansal Yükümlülükler + Türev Finansal Yükümlülükler + Faktoring Borçları + Kiralama Borçları + Sermaye Benzeri Krediler.
- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

> ℹ️ Spread hesabındaki payda ile aynı (PBI tanımı).

---

## Net Faiz (Kar Payı) Marjı (NIM)

`id: nim`

**Tanım:** Net faiz marjı.

**Formül:** TTM Net Faiz Geliri / Ortalama Toplam Aktifler

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Gelir Tablosu; Bilanço

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

> ℹ️ Payda toplam aktif (getirili aktif değil).

---

## Düzeltilmiş Net Faiz (Kar Payı) Marjı (NIM)

`id: nim_duzeltilmis`

**Tanım:** Ticari kâr/zarar etkisiyle düzeltilmiş net faiz marjı.

**Formül:** TTM Düzeltilmiş Net Faiz Geliri / Ort. Faiz Getirili Aktifler (detaylı)

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Gelir Tablosu; Bilanço; TCMB tablosu

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *Faiz (Kar Payı) Getirili Aktifler (detaylı, 13 bileşen):* TCMB Hesabı (TP+YP) + Bankalar + Para Piyasalarından Alacaklar + GUD K/Z FV + GUD DKG FV + İtfa Edilmiş Maliyet FV + Satılmaya Hazır (eski) + VKET (eski) + Türev FV + Riskten Korunma Türev FV + Toplam Brüt Krediler − |Beklenen Zarar Karşılıkları|.
- *Düzeltilmiş Net Faiz Geliri:* Net Faiz (Kar Payı) Geliri + Ticari Kar/Zarar (Net).
- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

> ℹ️ Payda NIM'den farklı (getirili aktif).

---

## BZK Sonrası Düzeltilmiş Net Faiz (Kar Payı) Marjı (NIM)

`id: nim_bzk_sonrasi`

**Tanım:** Karşılık giderleri sonrası düzeltilmiş net faiz marjı.

**Formül:** TTM (Düzeltilmiş Net Faiz Geliri − Karşılık Giderleri) / Ort. Faiz Getirili Aktifler (detaylı)

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Gelir Tablosu; Bilanço; TCMB tablosu

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *Faiz (Kar Payı) Getirili Aktifler (detaylı, 13 bileşen):* TCMB Hesabı (TP+YP) + Bankalar + Para Piyasalarından Alacaklar + GUD K/Z FV + GUD DKG FV + İtfa Edilmiş Maliyet FV + Satılmaya Hazır (eski) + VKET (eski) + Türev FV + Riskten Korunma Türev FV + Toplam Brüt Krediler − |Beklenen Zarar Karşılıkları|.
- *Düzeltilmiş Net Faiz Geliri:* Net Faiz (Kar Payı) Geliri + Ticari Kar/Zarar (Net).
- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

---

## Gayrinakdi Kredi Komisyonları / Gayrinakdi Krediler

`id: gayrinakdi_komisyon_gayrinakdi`

**Tanım:** Gayrinakdi kredilerin komisyon getirisi.

**Formül:** TTM G.Nakdi Kredilerden Alınan Komisyon / Gayrinakdi Krediler (dönem sonu)

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: dönem sonu bakiye

**Kaynak:** Gelir Tablosu; Nazım Hesaplar

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.

> ℹ️ Payda ortalama değil, dönem sonu.

---

## Komisyon Giderleri / Komisyon Gelirleri

`id: komisyon_gid_gel`

**Tanım:** Komisyon gelirinin ne kadarının komisyon giderine gittiği.

**Formül:** Verilen Ücret ve Komisyonlar / Alınan Ücret ve Komisyonlar

**Hesaplama dönemi:** Pay ve payda: yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

> ℹ️ PBI raporundaki gibi yılbaşından bugüne (YtD) oran; yıllıklandırılmaz. Aralık dışındaki çeyreklerde TTM oranından farklıdır.

---

## Net Ücret ve Komisyonlar / Ortalama Aktifler

`id: net_ucret_ort_aktif`

**Tanım:** Aktif başına net ücret-komisyon geliri.

**Formül:** TTM Net Ücret ve Komisyonlar / Ortalama Toplam Aktifler

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Gelir Tablosu; Bilanço

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

---

## Net Ücret ve Komisyonlar / Operasyonel Giderler

`id: net_ucret_operasyonel`

**Tanım:** Net komisyon gelirinin faaliyet giderlerini karşılama oranı.

**Formül:** Net Ücret ve Komisyonlar / Operasyonel Giderler (OPEX)

**Hesaplama dönemi:** Pay ve payda: yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *Operasyonel Giderler (OPEX):* Personel Giderleri + Diğer Faaliyet Giderleri.

> ℹ️ PBI raporundaki gibi yılbaşından bugüne (YtD) oran; yıllıklandırılmaz. Aralık dışındaki çeyreklerde TTM oranından farklıdır.

---

## Reklam Giderleri / Ortalama Aktifler

`id: reklam_ort_aktif`

**Tanım:** Aktif başına reklam harcaması.

**Formül:** TTM Reklam Giderleri / Ortalama Toplam Aktifler

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Faaliyet Giderleri dipnotu; Bilanço

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

---

## Reklam Giderleri / Net Dönem Kar/Zararı

`id: reklam_net_kar`

**Tanım:** Reklam giderinin net kâra oranı.

**Formül:** Reklam Giderleri / Net Dönem Karı

**Hesaplama dönemi:** Pay ve payda: yılbaşından kümülatif (YtD)

**Kaynak:** Faaliyet Giderleri dipnotu; Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

> ℹ️ Zarar eden bankada negatif/anlamsız.

> ℹ️ PBI raporundaki gibi yılbaşından bugüne (YtD) oran; yıllıklandırılmaz. Aralık dışındaki çeyreklerde TTM oranından farklıdır.

---

## Personel Giderleri / Ortalama Aktifler

`id: personel_ort_aktif`

**Tanım:** Aktif başına personel gideri.

**Formül:** TTM Personel Giderleri / Ortalama Toplam Aktifler

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Gelir Tablosu; Bilanço

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

---

## Personel Giderleri / Net Dönem Kar/Zararı

`id: personel_net_kar`

**Tanım:** Personel giderinin net kâra oranı.

**Formül:** Personel Giderleri / Net Dönem Karı

**Hesaplama dönemi:** Pay ve payda: yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

> ℹ️ Zarar eden bankada negatif/anlamsız.

> ℹ️ PBI raporundaki gibi yılbaşından bugüne (YtD) oran; yıllıklandırılmaz. Aralık dışındaki çeyreklerde TTM oranından farklıdır.

---

## Maliyet / Gelir Rasyosu

`id: maliyet_gelir`

**Tanım:** Maliyet/gelir (verimlilik) oranı.

**Formül:** (Diğer Faaliyet Giderleri + Personel Giderleri) / Faaliyet Gelirleri-Giderleri Toplamı

**Hesaplama dönemi:** Pay ve payda: yılbaşından kümülatif (YtD), yıllıklandırılmaz

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

---

## Düzeltilmiş Maliyet / Gelir Rasyosu

`id: maliyet_gelir_duzeltilmis`

**Tanım:** Kredi karşılık giderlerini de maliyete katan maliyet/gelir oranı.

**Formül:** (Operasyonel Giderler + Kredi ve Diğer Alacaklar Değer Düşüş Karşılığı) / Faaliyet Gelirleri/Giderleri Toplamı

**Hesaplama dönemi:** Pay ve payda: yılbaşından kümülatif (YtD)

**Kaynak:** Gelir Tablosu

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *Operasyonel Giderler (OPEX):* Personel Giderleri + Diğer Faaliyet Giderleri.

---

## Kredi Riski Maliyeti (Cost of Risk)

`id: cost_of_risk`

**Tanım:** Kredi riski maliyeti (PBI adı: "Brüt CoR").

**Formül:** TTM Beklenen Kredi Zararı / Özel Karşılık Giderleri / Ortalama Brüt Krediler

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Kredi ve Diğer Alacaklara İlişkin Karşılık Giderleri dipnotu; Bilanço

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *Toplam Brüt Krediler:* Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler (NPL dahil). TP/YP kırılımı aynı kalemlerin TP/YP kolonlarıyla.
- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

> ℹ️ Kullanıcının verdiği orijinal PBI DAX'ıyla (2026-09-21) düzeltildi — payda önceden yanlışlıkla NET krediler kullanıyordu (pratikte çoğu bankada sonucu neredeyse değiştirmiyor, ama artık DAX'a birebir sadık: v29 baseline'la %96,7 ±0,5pp uyum, medyan fark 0).

---

## Kredi Mevduat Spread'i

`id: kredi_mevduat_spread`

**Tanım:** Kredi getirisi ile mevduat maliyeti arasındaki bileşik spread'i.

**Formül:** ((1 + Kredilerin Paçal Getirisi) / (1 + Mevduatın Paçal Maliyeti) − 1) × 100

**Hesaplama dönemi:** İki yıllıklandırılmış oranın bileşik farkı (TTM / ortalama bakiye)

**Kaynak:** Gelir Tablosu; Bilanço

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Durum:** Kısmen en iyi tahmin

**Terimler:**

- *Mevduatın Paçal Maliyeti:* TTM Mevduata Verilen Faizler / Ortalama Mevduat.
- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

> ℹ️ Kullanıcının verdiği orijinal PBI DAX'ıyla (2026-09-21) düzeltildi — önceki formül basit FARK (getiri − maliyet) kullanıyordu, PBI'ın gerçek formülü bileşik (ratio-of-ratios). Dış formül artık DAX'a birebir sadık; iç "Mevduatın Paçal Maliyeti" alt-formülü henüz ayrıca doğrulanmadı (v29 baseline'la %79,5 ±0,5pp uyum). DAX orijinali ×10000 (baz puan) döner, kardeş ölçülerle (spread, tp_spread, yp_spread) birim tutarlılığı için ×100 (yüzde puanı) kullanılıyor.

---

## Spread

`id: spread`

**Tanım:** Getirili aktif getirisi ile maliyetli pasif maliyeti arasındaki bileşik spread'i.

**Formül:** ((1 + Faiz Getirili Aktiflerin Getirisi) / (1 + Faiz Maliyetli Pasiflerin Maliyeti) − 1) × 100

**Hesaplama dönemi:** İki yıllıklandırılmış oranın bileşik farkı (TTM / ortalama bakiye)

**Kaynak:** Gelir Tablosu; Bilanço; TCMB tablosu

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *Faiz (Kar Payı) Maliyetli Pasifler (detaylı, 9 bileşen):* Vadeli Mevduat + Alınan Krediler + Para Piyasalarına Borçlar + İhraç Edilen MK (Net) + GUD K/Z Finansal Yükümlülükler + Türev Finansal Yükümlülükler + Faktoring Borçları + Kiralama Borçları + Sermaye Benzeri Krediler.
- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

> ℹ️ Kullanıcının verdiği orijinal PBI DAX'ıyla (2026-09-21) düzeltildi — önceki formül basit FARK kullanıyordu ("en iyi tahmin", %78 uyum); bileşik formülle v29 baseline'la %92,8 ±0,5pp uyum, medyan fark 0.

---

## TP Kredi Mevduat Spread'i

`id: tp_spread`

**Tanım:** TL kredi-mevduat spread'i (kullanıcının verdiği orijinal PBI DAX'ına göre, 2026-09-21'de hesaplanır hale getirildi).

**Formül:** ((1 + TP Kredilerin Getirisi) / (1 + TP Vadeli Mevduatın Maliyeti) − 1) × 100

**Hesaplama dönemi:** Pay ve payda: son 12 ay (TTM) / 12 aylık ortalama bakiye

**Kaynak:** Gelir Tablosu; Bilanço; Kredilerden Alınan Faiz Gelirleri dipnotu; Mevduata Ödenen Faizin Vade Yapısı dipnotu (Katılım bankasında: Katılma Hesaplarına Ödenen Kar Paylarının Vade Yapısı dipnotu)

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *TP Kredilerin Getirisi:* TTM Kredilerden Faizler (Toplam, TP) / Ortalama Krediler (TP).
- *TP Vadeli Mevduatın Maliyeti:* TTM gerçek vadeli (vadesiz hariç) TP faiz/kâr payı gideri / Ortalama TP VADELİ Mevduat bakiyesi (mevduat bankasında `Döviz Tevdiat Hesabı`+`Kıymetli Maden Depo Hesabı` segmentlerinden türetilen YP vadesiz payı çıkarılarak; Katılım bankasında hâlâ TOPLAM bakiye — bkz. not).
- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

> ℹ️ 2026-09-21'de kullanıcı gerçek PBI ekran görüntüsüyle karşılaştırdı — payda TOPLAM TP Mevduat (vadesiz dahil) kullanıldığında değerler ~100-250bps yüksek çıkıyordu. Mevduat bankalarında artık gerçek TP Vadeli bakiye türetiliyor (v29 ekran görüntüsüyle ortalama sapma ~36bps'e düştü). ⚠️ Katılım bankalarında (KT, Albaraka, Türkiye Finans, Ziraat/Vakıf/Emlak Katılım) YP katılma hesabı segmentleri dipnotta güvenilir görünmediği için hâlâ TOPLAM bakiye kullanılıyor — bu alt kümede hâlâ olduğundan yüksek çıkabilir.

---

## YP Kredi Mevduat Spread'i

`id: yp_spread`

**Tanım:** YP kredi-mevduat spread'i (kullanıcının verdiği orijinal PBI DAX'ına göre, 2026-09-21'de hesaplanır hale getirildi).

**Formül:** ((1 + YP Kredilerin Getirisi) / (1 + YP Vadeli Mevduatın Maliyeti) − 1) × 100

**Hesaplama dönemi:** Pay ve payda: son 12 ay (TTM) / 12 aylık ortalama bakiye

**Kaynak:** Gelir Tablosu; Bilanço; Kredilerden Alınan Faiz Gelirleri dipnotu; Mevduata Ödenen Faizin Vade Yapısı dipnotu (Katılım bankasında: Katılma Hesaplarına Ödenen Kar Paylarının Vade Yapısı dipnotu)

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *YP Kredilerin Getirisi:* TTM Kredilerden Faizler (Toplam, YP) / Ortalama Krediler (YP).
- *YP Vadeli Mevduatın Maliyeti:* TTM gerçek vadeli (vadesiz hariç) YP faiz/kâr payı gideri / Ortalama YP VADELİ Mevduat bakiyesi (mevduat bankasında `Döviz Tevdiat Hesabı`+`Kıymetli Maden Depo Hesabı` segmentlerinin vadesiz kısmı çıkarılarak türetilir — bu iki segmentin toplamı bilançodaki YP Mevduat'a ~%1 içinde yaklaşıyor; Katılım bankasında hâlâ TOPLAM bakiye — bkz. not).
- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

> ℹ️ 2026-09-21'de kullanıcı gerçek PBI ekran görüntüsüyle (Haziran 2026) karşılaştırdı — payda TOPLAM YP Mevduat (vadesiz dahil) kullanıldığında değerler ~100-250bps yüksek çıkıyordu (ör. Kuveyt Türk 640 vs gerçek 512bps). Mevduat bankalarında artık gerçek YP Vadeli bakiye türetiliyor — v29 ekran görüntüsüyle ortalama sapma ~36bps'e düştü (Enpara 1259 vs gerçek 1261, TEB 601 vs 599 gibi neredeyse birebir örnekler dahil; Şekerbank hâlâ ~170bps sapıyor, bilinen veri kalitesi istisnası). ⚠️ Katılım bankalarında (KT, Albaraka, Türkiye Finans, Ziraat/Vakıf/Emlak Katılım) YP katılma hesabı segmentleri dipnotta güvenilir görünmediği için (bilançodaki YP Mevduat'ın küçük bir kesrini kapsıyor) hâlâ TOPLAM bakiye kullanılıyor — bu alt kümede hâlâ olduğundan yüksek çıkıyor.

---

## Kredilerin Paçal Getirisi

`id: kredi_pacal_getiri`

**Tanım:** Kredilerin ortalama getirisi.

**Formül:** TTM Kredilerden Alınan Faizler / Ortalama Krediler (net)

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Gelir Tablosu; Bilanço

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *Krediler (net):* Bilanço 'Krediler ve Alacaklar (Toplam)'; eski TMS 39 dönemlerinde 'Krediler'. Donuk alacaklar ve karşılıklar netleştirilmiş haliyle.
- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

---

## Kaynağın Paçal Maliyeti

`id: kaynak_pacal_maliyet`

**Tanım:** Kaynakların ortalama maliyeti.

**Formül:** = Faiz Maliyetli Pasiflerin Maliyeti

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: 12 aylık ortalama bakiye

**Kaynak:** Gelir Tablosu; Bilanço

**Kategori:** Gelir Tablosu · **Tip:** Rasyo (Akım) · **Birim:** %

**Terimler:**

- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

> ℹ️ faiz_maliyetli_pasif_maliyeti ile birebir aynı değer.

---

## Şube Sayısı

`id: sube_sayisi`

**Tanım:** Yurt içi + yurt dışı şube sayısı.

**Formül:** Şube Sayısı

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Şube & Personel (faaliyet raporu bilgisi)

**Kategori:** Şube & Personel · **Tip:** Büyüklük (Stok) · **Birim:** Adet

---

## Şube Başına Krediler

`id: sube_basina_krediler`

**Tanım:** Şube başına kredi hacmi.

**Formül:** Krediler (net) / Şube Sayısı / 1000

**Hesaplama dönemi:** Dönem sonu bakiye / dönem sonu adet

**Kaynak:** Bilanço; Şube & Personel

**Kategori:** Şube & Personel · **Tip:** Rasyo (Stok) · **Birim:** Bin TL

**Terimler:**

- *Krediler (net):* Bilanço 'Krediler ve Alacaklar (Toplam)'; eski TMS 39 dönemlerinde 'Krediler'. Donuk alacaklar ve karşılıklar netleştirilmiş haliyle.

> ℹ️ Şubesiz bankalar (Enpara, TOM Bank, Hayat Finans) listede gösterilmez.

---

## Şube Başına Mevduat

`id: sube_basina_mevduat`

**Tanım:** Şube başına mevduat hacmi.

**Formül:** Mevduat / Şube Sayısı / 1000

**Hesaplama dönemi:** Dönem sonu bakiye / dönem sonu adet

**Kaynak:** Bilanço; Şube & Personel

**Kategori:** Şube & Personel · **Tip:** Rasyo (Stok) · **Birim:** Bin TL

> ℹ️ Şubesiz bankalar gösterilmez.

---

## Şube Başına Net Kar

`id: sube_basina_net_kar`

**Tanım:** Şube başına yıllık net kâr.

**Formül:** TTM Net Dönem Karı / Şube Sayısı / 1000

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: dönem sonu adet

**Kaynak:** Gelir Tablosu; Şube & Personel

**Kategori:** Şube & Personel · **Tip:** Rasyo (Akım) · **Birim:** Bin TL

**Terimler:**

- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.

> ℹ️ Şubesiz bankalar gösterilmez.

---

## Personel Sayısı

`id: personel_sayisi`

**Tanım:** Toplam personel sayısı.

**Formül:** Personel Sayısı

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Şube & Personel

**Kategori:** Şube & Personel · **Tip:** Büyüklük (Stok) · **Birim:** Adet

---

## Şube Başına Personel

`id: sube_basina_personel`

**Tanım:** Şube başına çalışan.

**Formül:** Personel Sayısı / Şube Sayısı

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Şube & Personel

**Kategori:** Şube & Personel · **Tip:** Rasyo (Stok) · **Birim:** Adet

> ℹ️ Şubesiz bankalar gösterilmez.

---

## Personel Başına Krediler

`id: personel_basina_krediler`

**Tanım:** Çalışan başına kredi hacmi.

**Formül:** Krediler (net) / Personel Sayısı / 1000

**Hesaplama dönemi:** Dönem sonu bakiye / dönem sonu adet

**Kaynak:** Bilanço; Şube & Personel

**Kategori:** Şube & Personel · **Tip:** Rasyo (Stok) · **Birim:** Bin TL

**Terimler:**

- *Krediler (net):* Bilanço 'Krediler ve Alacaklar (Toplam)'; eski TMS 39 dönemlerinde 'Krediler'. Donuk alacaklar ve karşılıklar netleştirilmiş haliyle.

---

## Personel Başına Mevduat

`id: personel_basina_mevduat`

**Tanım:** Çalışan başına mevduat hacmi.

**Formül:** Mevduat / Personel Sayısı / 1000

**Hesaplama dönemi:** Dönem sonu bakiye / dönem sonu adet

**Kaynak:** Bilanço; Şube & Personel

**Kategori:** Şube & Personel · **Tip:** Rasyo (Stok) · **Birim:** Bin TL

---

## Personel Başına Net Kar

`id: personel_basina_net_kar`

**Tanım:** Çalışan başına yıllık net kâr.

**Formül:** TTM Net Dönem Karı / Personel Sayısı / 1000

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: dönem sonu adet

**Kaynak:** Gelir Tablosu; Şube & Personel

**Kategori:** Şube & Personel · **Tip:** Rasyo (Akım) · **Birim:** Bin TL

**Terimler:**

- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.

---

## Personel Başına Personel Gideri

`id: personel_basina_personel_gideri`

**Tanım:** Çalışan başına yıllık personel gideri.

**Formül:** TTM Personel Giderleri / Personel Sayısı / 1000

**Hesaplama dönemi:** Pay: son 12 ay (TTM) · Payda: dönem sonu adet

**Kaynak:** Gelir Tablosu; Şube & Personel

**Kategori:** Şube & Personel · **Tip:** Rasyo (Akım) · **Birim:** Bin TL

**Terimler:**

- *TTM (son 12 ay):* BDDK gelir tablosu YtD olduğundan: TTM(t) = YtD(t) + (Önceki yıl sonu − YtD(t − 12 ay)). 4. çeyrekte doğrudan yıllık tutar. Geçmiş dönem yoksa YtD × 12 / ay sayısı.

---

## Toplam Brüt Krediler

`id: toplam_brut_krediler`

**Tanım:** NPL, faktoring ve leasing dahil brüt kredi stoku.

**Formül:** Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler (NPL dahil). TP/YP kırılımı aynı kalemlerin TP/YP kolonlarıyla.

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Toplam Canlı Krediler

`id: toplam_canli_krediler`

**Tanım:** Donuk ve takipteki alacaklar hariç brüt krediler.

**Formül:** Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar (NPL hariç).

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Toplam Fonlama

`id: toplam_fonlama`

**Tanım:** Para piyasası borçları dahil toplam fonlama.

**Formül:** Mevduat + Alınan Krediler + Para Piyasalarına Borçlar + İhraç Edilen Menkul Kıymetler (Net).

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Toplam Kredi Kartları

`id: toplam_kredi_kartlari`

**Tanım:** Kredi kartı kaynaklı toplam alacak (PBI tanımı).

**Formül:** Kredi Kartları Standart Nitelikli (Toplam) + Bireysel KK TP + Bireysel KK TP

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Grup 1-2 Krediler; Tüketici Kredileri detay

**Kategori:** Bilanço › Aktifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

> ⚠️ PBI DAX'ına birebir sadık: Bireysel KK TP iki kez toplanıyor, YP hiç yok. Kaynak formülde kopyala-yapıştır hatası olabilir; teyit edilmeli.

---

## Toplam Mevduat (KM Hariç)

`id: toplam_mevduat_km_haric`

**Tanım:** Kıymetli maden hariç mevduat.

**Formül:** Mevduat − Kıymetli Maden Mevduatı

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Mevduat detay

**Kategori:** Bilanço › Pasifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Toplam Özkaynaklar (Ana Sermaye+ Katkı Sermaye)

`id: toplam_ozkaynaklar_regulasyon`

**Tanım:** Sermaye yeterliliği hesabındaki yasal özkaynak.

**Formül:** Toplam Özkaynaklar (Ana Sermaye + Katkı Sermaye)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Özkaynak Kalemleri tablosu

**Kategori:** Bilanço › Pasifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Toplam Pasifler

`id: toplam_pasifler`

**Tanım:** Bilanço pasif toplamı (= Toplam Aktifler).

**Formül:** Toplam Pasifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Toplam Pasifler (Özkaynak Hariç)

`id: toplam_pasifler_ozkaynak_haric`

**Tanım:** Yabancı kaynaklar toplamı.

**Formül:** Toplam Pasifler − Özkaynaklar

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Toplam Risk Ağırlıklı Varlıklar (RAV)

`id: rav`

**Tanım:** Kredi riskine esas tutar.

**Formül:** Kredi Riskine Esas Tutar: Toplam

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Sermaye Yeterliliği tablosu

**Kategori:** Bilanço › Pasifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

> ⚠️ Ad "Toplam RAV" olsa da yalnız kredi riskini içerir (PBI DAX'ına sadık). Piyasa + operasyonel dahil tutar: toplam_risk_tabani.

---

## Ortalama RAV / Ortalama Özkaynaklar

`id: ort_rav_ort_ozkaynak`

**Tanım:** Özkaynak başına risk ağırlıklı varlık (risk kaldıracı).

**Formül:** Ortalama RAV / Ortalama Özkaynaklar

**Hesaplama dönemi:** Pay ve payda: 12 aylık ortalama bakiye

**Kaynak:** Sermaye Yeterliliği tablosu; Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** Kat

**Terimler:**

- *RAV:* Kredi Riskine Esas Tutar: Toplam (PBI tanımı; piyasa ve operasyonel risk dahil değil).
- *Ortalama bakiye:* (Bakiye(t) + Bakiye(t − 12 ay)) / 2. Bir yıl önceki dönem yoksa dönem sonu bakiye.

---

## Toplam Risk

`id: toplam_risk_tabani`

**Tanım:** Sermaye yeterliliği paydası olan toplam risk tabanı.

**Formül:** Kredi Riskine Esas Tutar + Piyasa Riskine Esas Tutar + Operasyonel Riske Esas Tutar.

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Sermaye Yeterliliği; TCMB tablosu

**Kategori:** Bilanço › Pasifler · **Tip:** Büyüklük (Stok) · **Birim:** TL

---

## Kredi Riski/ Toplam Risk Tabanı

`id: kredi_riski_toplam_risk`

**Tanım:** Kredi riskinin risk tabanındaki payı.

**Formül:** Kredi Riskine Esas Tutar / Toplam Risk Tabanı

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Sermaye Yeterliliği; TCMB tablosu

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Risk Tabanı:* Kredi Riskine Esas Tutar + Piyasa Riskine Esas Tutar + Operasyonel Riske Esas Tutar.

---

## Piyasa Riski/ Toplam Risk Tabanı

`id: piyasa_riski_toplam_risk`

**Tanım:** Piyasa riskinin risk tabanındaki payı.

**Formül:** Piyasa Riskine Esas Tutar / Toplam Risk Tabanı

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Sermaye Yeterliliği; TCMB tablosu

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Risk Tabanı:* Kredi Riskine Esas Tutar + Piyasa Riskine Esas Tutar + Operasyonel Riske Esas Tutar.

---

## Operasyonel Riski/ Toplam Risk Tabanı

`id: operasyonel_risk_toplam_risk`

**Tanım:** Operasyonel riskin risk tabanındaki payı.

**Formül:** Operasyonel Riske Esas Tutar / Toplam Risk Tabanı

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Sermaye Yeterliliği; TCMB tablosu

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Risk Tabanı:* Kredi Riskine Esas Tutar + Piyasa Riskine Esas Tutar + Operasyonel Riske Esas Tutar.

---

## Brüt Krediler/ Toplam Aktifler

`id: brut_krediler_ta`

**Tanım:** Brüt kredilerin aktif içindeki payı.

**Formül:** Toplam Brüt Krediler / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Brüt Krediler:* Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler (NPL dahil). TP/YP kırılımı aynı kalemlerin TP/YP kolonlarıyla.

---

## Alınan Krediler/ Toplam Pasifler

`id: alinan_krediler_toplam_pasifler`

**Tanım:** Alınan kredilerin pasif içindeki payı.

**Formül:** Alınan Krediler / Toplam Pasifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Bankalar/ Toplam Aktifler

`id: bankalar_toplam_aktifler`

**Tanım:** Bankalardan alacakların aktif içindeki payı.

**Formül:** Bankalar / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Birikimli Vadeli Mevduat/ Toplam Vadeli Mevduat

`id: birikimli_vadeli_mevduat_toplam_vadeli`

**Tanım:** Birikimli vadeli mevduatın vadeli mevduat içindeki payı.

**Formül:** Birikimli Vadeli Mevduat / Vadeli Mevduat

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Mevduat Vade Yapısı (katılımda Katılma Hesapları) tablosu

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ℹ️ Katılım bankalarında "Birikimli Katılma Hesabı" kullanılır.

---

## Resmi Kurumlar Mevduatı/ Toplam Mevduat

`id: resmi_kurumlar_mevduat_toplam_mevduat`

**Tanım:** Resmi kurum mevduatının payı.

**Formül:** Resmi Kuruluşlar Mevduatı / Mevduat

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Mevduat detay

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## Toplam Fonlama/ Faiz (Kar Payı) Maliyetli Pasifler

`id: toplam_fonlama_faiz_maliyetli_pasif`

**Tanım:** Toplam fonlamanın maliyetli pasiflere oranı.

**Formül:** Toplam Fonlama / Faiz Maliyetli Pasifler (detaylı)

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Mevduat detay

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** Kat

**Terimler:**

- *Toplam Fonlama:* Mevduat + Alınan Krediler + Para Piyasalarına Borçlar + İhraç Edilen Menkul Kıymetler (Net).
- *Faiz (Kar Payı) Maliyetli Pasifler (detaylı, 9 bileşen):* Vadeli Mevduat + Alınan Krediler + Para Piyasalarına Borçlar + İhraç Edilen MK (Net) + GUD K/Z Finansal Yükümlülükler + Türev Finansal Yükümlülükler + Faktoring Borçları + Kiralama Borçları + Sermaye Benzeri Krediler.

> ℹ️ Birim: kat.

---

## Tüzel Mevduat / Toplam Mevduat

`id: tuzel_mevduat_toplam_mevduat`

**Tanım:** Tüzel mevduatın payı.

**Formül:** Tüzel Mevduat / Mevduat

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço; Mevduat detay

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Tüzel Mevduat:* Ticari Kuruluşlar + Diğer Kuruluşlar mevduatı (Resmi Kuruluşlar hariç). Katılım bankalarında ayrıca özel cari hesaplardaki yurtiçi/yurtdışı yerleşik tüzel kişiler.

---

## Nakit Değerler / Toplam Aktifler

`id: nakit_degerler_ta`

**Tanım:** Nakit ve merkez bankası bakiyelerinin aktif içindeki payı.

**Formül:** Nakit Değerler ve Merkez Bankası / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

---

## 1 Aya Kadar Vadeli Mevduat/ Toplam Vadeli Mevduat

`id: vadeli_1ay_toplam_vadeli`

**Tanım:** 1 aya kadar vadeli mevduatın payı.

**Formül:** Vadeli Mevduat (1 Aya Kadar) / Vadeli Mevduat

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Mevduat Vade Yapısı tablosu

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ⚠️ Katılım bankalarında vade dilimleri farklı olduğundan 0 döner.

---

## 1-3 Ay Vadeli Mevduat/ Toplam Vadeli Mevduat

`id: vadeli_1_3ay_toplam_vadeli`

**Tanım:** 1-3 ay vadeli mevduatın payı.

**Formül:** Vadeli Mevduat (1-3 Ay) / Vadeli Mevduat

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Mevduat Vade Yapısı tablosu

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ⚠️ Katılım bankalarında 0 döner.

---

## 3-6 Ay Vadeli Mevduat/ Toplam Vadeli Mevduat

`id: vadeli_3_6ay_toplam_vadeli`

**Tanım:** 3-6 ay vadeli mevduatın payı.

**Formül:** Vadeli Mevduat (3-6 Ay) / Vadeli Mevduat

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Mevduat Vade Yapısı tablosu

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ⚠️ Katılım bankalarında 0 döner.

---

## 6-12 Ay Vadeli Mevduat/ Toplam Vadeli Mevduat

`id: vadeli_6_12ay_toplam_vadeli`

**Tanım:** 6-12 ay vadeli mevduatın payı.

**Formül:** Vadeli Mevduat (6 Ay-1 Yıl) / Vadeli Mevduat

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Mevduat Vade Yapısı tablosu

**Kategori:** Bilanço › Pasifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ⚠️ Katılım bankalarında 0 döner.

---

## YP Krediler/ Toplam Krediler

`id: yp_krediler_toplam_krediler`

**Tanım:** Yabancı para kredilerin toplam kredi içindeki payı.

**Formül:** YP Toplam Brüt Krediler / Toplam Brüt Krediler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

**Terimler:**

- *Toplam Brüt Krediler:* Krediler ve Alacaklar + Faktoring Alacakları + Kiralama İşlemlerinden Alacaklar + Donuk Alacaklar + Takipteki Krediler (NPL dahil). TP/YP kırılımı aynı kalemlerin TP/YP kolonlarıyla.

---

## Likidite Açığı, Vadesiz / Toplam Aktifler

`id: likidite_acigi_vadesiz_ta`

**Tanım:** Kalan vadeye göre vadesiz dilimdeki likidite açığının aktife oranı.

**Formül:** Likidite Açığı (Vadesiz) / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Kalan Vade (Likidite) tablosu; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ℹ️ Negatif = açık.

---

## Likidite Açığı, 1 Aya Kadar / Toplam Aktifler

`id: likidite_acigi_1ay_ta`

**Tanım:** 1 aya kadar vade dilimindeki likidite açığının aktife oranı.

**Formül:** Likidite Açığı (1 Aya Kadar) / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Kalan Vade (Likidite) tablosu; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ℹ️ Negatif = açık.

---

## Likidite Açığı, 1-3 Ay / Toplam Aktifler

`id: likidite_acigi_1_3ay_ta`

**Tanım:** 1-3 ay vade dilimindeki likidite açığının aktife oranı.

**Formül:** Likidite Açığı (1-3 Ay) / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Kalan Vade (Likidite) tablosu; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ℹ️ Negatif = açık.

---

## Likidite Açığı, 3-12 Ay / Toplam Aktifler

`id: likidite_acigi_3_12ay_ta`

**Tanım:** 3-12 ay vade dilimindeki likidite açığının aktife oranı.

**Formül:** Likidite Açığı (3-12 Ay) / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Kalan Vade (Likidite) tablosu; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ℹ️ Negatif = açık.

---

## Likidite Açığı, 1-5 Yıl / Toplam Aktifler

`id: likidite_acigi_1_5yil_ta`

**Tanım:** 1-5 yıl vade dilimindeki likidite açığının aktife oranı.

**Formül:** Likidite Açığı (1-5 Yıl) / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Kalan Vade (Likidite) tablosu; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ℹ️ Negatif = açık.

---

## Likidite Açığı, 5 Yıl ve Üzeri / Toplam Aktifler

`id: likidite_acigi_5yil_uzeri_ta`

**Tanım:** 5 yıl üzeri vade dilimindeki likidite fazlası/açığının aktife oranı.

**Formül:** Likidite Açığı (5 Yıl ve Üzeri) / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Kalan Vade (Likidite) tablosu; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %

> ℹ️ Negatif = açık.

---

## Likidite Açığı, Dağıtılamayan / Toplam Aktifler

`id: likidite_acigi_dagitilamayan_ta`

**Tanım:** Vadeye dağıtılamayan kalemlerin net pozisyonunun aktife oranı.

**Formül:** Likidite Açığı (Dağıtılamayan) / Toplam Aktifler

**Hesaplama dönemi:** Dönem sonu bakiye

**Kaynak:** Kalan Vade (Likidite) tablosu; Bilanço

**Kategori:** Bilanço › Aktifler · **Tip:** Rasyo (Stok) · **Birim:** %
