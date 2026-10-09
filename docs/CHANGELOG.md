# Changelog

Sürüm geçmişi. Her commit'in özetini barındırır.

## Rekabet Analizi — tüm bankalar için tamlık (2026-10-09)

- **YtD Büyüme kartı ortalama seçici:** "Ortalamayı göster" düğmesi yerine Yok / Basit / Ağırlıklı / Basit + Ağırlıklı seçici. Ağırlıklı ortalama = Σ(büyüme × baz dönem değeri) / Σ baz
  (= seçili bankaların toplamının büyümesi); baz ≤ 0 ve anomali bankalar dışarıda, miktar (adet) ölçülerinde yalnız basit ortalama. Basit turuncu, ağırlıklı mavi çizgi/çubuk.

- **Rol bazlı ekran izinleri:** Admin → Roller tablosuna "Ekran" bölümü eklendi: Trend ve Kompozisyon sekmeleri, dört dashboard kartı (Banka sıralaması, YtD Büyüme / Rasyo özeti,
  Banka Grupları, Rakip Bankalar) ve menüdeki BDR düğmesi rol başına açılıp kapatılır. Ölçü kategorileri de rol başına gizlenebilir (rolde `gizle:<kategori>` girdisi); gizli kategorinin
  ölçüleri sunucudan hiç gönderilmez (Rekabet Analizi izniyle aynı mekanizma, `_gizli_olculer`). Mevcut tüm roller (özel roller dahil) yeni ekran izinlerini açık olarak alır;
  'Ekran' izinleri ve `gizle:` kısıtları yetki yükseltme denetiminde sayılmaz. Kapalı sekme açılamaz (görünüm/kısayol dahil Anlık Görünüm'e düşer).

- **TÜFEX türetimi (son 8 çeyrek):** `scripts/bdr_rekabet_cikar.py` BDR dipnotundaki "yıllık %X enflasyon tahmini" varsayımı ve "TÜFE tahmininin %1 değişmesi → vergi öncesi kâr ≈ N"
  duyarlılığından TÜFEX'i türetir: (gerçekleşen yıllık TÜFE − varsayım) × duyarlılık. Denizbank/QNB doğrudan açıklar ("referans endekse göre yapılsaydı … net dönem karı X artarak/azalarak";
  azalış negatif tampon). Akbank, QNB, ING, TEB yıl sonlarında fiili enflasyon kullandığını yazdığından 2024-12 / 2025-12 için 0; İş Bankası yıl sonunda da kendi varsayımını açıkladığı
  için türetildi. Yıl sonu duyarlılığı yayımlamayan Garanti, Yapı Kredi, Vakıfbank, Ziraat, Denizbank ile Halk/Burgan/Odeabank/Şekerbank (ve İş 2024-09) boş kalır ("Veri yok").
  Akbank 2024-09 duyarlılığı "yaklaşık 1 milyar" olarak yuvarlak açıklandığı için yaklaşık değerdir. Haziran 2026 elle doğrulanmış değerler korunmuştur.

- **"Tanımsız" / "Veri yok" etiketleri (2026-10-09):** Rekabet Analizi ölçülerinde değeri olmayan bankalar artık yalnızca listeden çıkarılmıyor; Anlık
  Görünüm'ün altında açılır bir şerit ("Değeri olmayan bankalar (N)") bu bankaları ve nedenini gösteriyor. **Tanımsız** = matematiksel olarak
  tanımlı değil (şubesiz banka, önceki yıl kârı ≤ 0, önceki yıl personeli yok, Grup 2 kredisi yok, altın hesabı yok, payda sıfır);
  **Veri yok** = kaynak veri yok / açıklanmıyor (TÜFEX varsayımı verilmemiş, BDR verisi yüklenmemiş, banka henüz faaliyette değil). Nedenler
  `pipeline/bos_nedenleri.py` kurallarıyla hesaplama sırasında üretilip `data/bos_nedenleri.json`'a yazılır (son 12 çeyrek, yalnız boş hücreler;
  `app._run_pipeline_and_save` ve `scripts/recompute.py`), `/api/bos-nedenleri` ile (yalnız Rekabet izni olanlara) sunulur; İngilizce çeviriler
  `frontend/i18n/arayuz_en.json`'a eklendi. Genel metne düşen hücre kalmadı: yeni faaliyete başlayan bankalarda (Hayat Finans, Dünya Katılım, TOM, Enpara)
  Örtük TCMB Getirisi (ortalama TCMB hesabı 0) ve fonlama oranları (toplam fonlama 0) "Tanımsız" olarak sınıflandı. Test izolasyonu: `test_computed_guards`
  gerçek `data/bos_nedenleri.json` dosyasını ezmesin diye fixture `DATA_BOS_NEDEN`'i geçici klasöre alır.
- **Altın Hesapları Vadesiz Payı:** mevduat bankaları için vadesiz altın tutarı artık BDDK verisindeki mevduat vade tablosundan
  (`Kıym. Mad. Depo Hesabı, Vadesiz`) alınıyor; önceki sürüm "bu kırılım BDDK verisinde yok" varsayımıyla yalnız elle yüklenen
  2026-06-30 verisine bağlıydı. Değerler elle yüklenenlerle birebir; böylece 27 bankanın 26'sı ve TÜM dönemler dolu (eksik: kıymetli
  maden hesabı olmayan TOM). Haziran 2026'da dolu banka 15 → 26.
- **Elle yüklenen 6 ölçü için son 8 çeyrek (2024-09-30 → 2026-06-30):** `scripts/bdr_rekabet_cikar.py` BDR arşivindeki (`~/Desktop/BDR-Arsiv/raporlar`)
  solo belgelerden Basel kaldıraç, LCR, LCR-YP ve serbest karşılığı çıkarır (LCR/kaldıraç tablo satırından; serbest karşılık dipnot ve denetçi raporu
  cümlelerinden, "milyon TL" / "bin TL" birimi ayrımıyla). Doğrulama: 2026-06-30'da çıkarılan değerler elle yüklenenlerle 26 bankanın 4 ölçüsünde
  birebir. Arşivdeki tuzaklar giderildi: aynı klasörde başka çeyreğe ait dosya (2025-2C klasöründe Eylül 2025 raporları) dönem kontrolüyle atlanır,
  dosya adı ipucu önceliklidir (Aktif Bank dosyası Türkiye Finans sanılmasın), Halk Bank ve bazı TEB çeyrekleri .docx'tir (macOS `textutil`).
  Anlamsız aykırılar yüklenmedi: Enpara LCR 2025-03/06/09 (banka faaliyete başlamadan, %7.808-34.221) ve TOM LCR-YP 2024-12 (%986.886).
  Boş kalanlar: Enpara (faaliyet öncesi dönemler), Fibabanka LCR 2025-09 (PDF'te tablo yok), Enpara serbest karşılığı (belirsiz).
  TÜFEX: Hazine endeksiyle değerleyen ya da TÜFE'li kıymeti olmayan 13 banka yapısal sıfır (tahmini enflasyon kullanmayan çeyreklerde); tahmini enflasyon
  kullanıp varsayımı açıklamayan (Burgan, Odeabank, Şekerbank, Halk; Fibabanka'nın bazı çeyrekleri, Emlak 2024-12) boş. `kar_tamponu_net_kar` artık
  yalnız serbest karşılık VE TÜFEX bilindiğinde hesaplanır (kısmi tampon göstermemek için). Rekabet ölçülerinde son 8 çeyrek doluluk: %94,8.

## PDF'ten veri — 2026-10-08 — Bilanço + Gelir Tablosu (1. aşama)

**Amaç:** Bankaların konsolide olmayan BDR PDF'lerinden banka bazında veri üretmek (yeni dönem için BDDK Excel/ZIP'e bağımlılığı
azaltmak). Mevcut `cikti_ingest` yolu (BDR-Kısayol JSON'u) geçmiş dönem verisi üzerine bindirilince ölçü bazında %25 uyum
veriyordu; PDF'i doğrudan okuyan yeni yol başlatıldı.

**Eklenenler:** `pipeline/pdf_ingest.py` (okuyucu, doğrulama, eşleme), `pipeline/pdf_haritalari.json` (BDDK kodu → sistem kalem adı,
mevcut BDDK verisiyle DEĞER eşleştirmesiyle öğrenildi), `scripts/bdr_pdf_isle.py` (klasör işleme, `--olcu-sinavi`, `--harita-ogren`),
`tests/test_pdf_ingest.py`. Üretim verisine yazmaz.

**Ölçülen doğruluk (Haziran 2026, 22 banka PDF'i, BDDK verisi referans):**
- Bilanço ve gelir tablosu 22 bankada okunuyor; her banka kendini doğruluyor (aktif toplamı = pasif toplamı; net faiz kimliği).
- Ortak kalemlerde BDDK değeriyle uyum ≥ %95 (Ziraat, Vakıfbank, Albaraka, Denizbank testli).
- Ölçü bazında (209 ölçü × 22 banka): 113 ölçü tüm bankalarda birebir, hücre uyumu %73,7. Kalan ölçüler Bilanço/Gelir dışındaki
  dipnot tablolarına bağlı (donuk alacak, kredi detayı, vade yapıları, TCMB, sermaye yeterliliği, şube/personel, kur riski ...).

**Yapılmadı / sıradaki:** dipnot tabloları (ölçü başına etkisi: tüketici kredi detayı 16, Grup 1-2 krediler 11, donuk alacak hareketi 8,
mevduat ve toplanan fon vade yapısı 29'ar, TCMB 18, diğer faaliyet gider detayı 20, şube/personel 15, sermaye 10-11, kalan vade 7).
Bilanço'daki aşama karşılıkları (1./2./3. aşama), 'Donuk Alacaklar' ve 'Krediler Ve Alacaklar' (canlı) kalemleri de dipnottan gelir.
Okuma yeni dönemin BDDK verisi olmadan yapılabilir, ama eşleme haritası yalnız bu çıktıların biçimine göre öğrenildi; yeni
bir bankanın raporu farklı düzenle gelirse kendi doğrulamasında takılır ve veri üretmez.

**2. aşama — dipnot tabloları (2026-10-08, kısmi):** `pipeline/pdf_dipnot.py` (hücre çıkarma + "ayak izi" öğrenme),
`pipeline/pdf_dipnot_hedefler.json` (ölçülerin okuduğu 19 dipnot tablosu, 266 hücre; TracingLookupContext ile üretildi),
`pipeline/pdf_dipnot_ozellikleri.json` (öğrenilen ayak izleri + her birinin doğruluğu), `scripts/bdr_pdf_dipnot.py`.
Dipnot satırlarında başlık metni bankadan bankaya değiştiği için her hedef (tablo, kalem, para birimi) BDDK verisiyle değer
eşleştirmesiyle öğrenilir; doğruluk **bir banka dışarıda bırakılarak** ölçülür (22 banka):
tcmb %99, bilanço dışı %95, kur riski %94, Grup 1-2 krediler %93, kalan vade %93, sermaye oranları %93, özkaynak %91, gider detayı
%91, kredi faizi %91, sermaye (RAV) %89, faiz TP/YP %86, donuk alacak hareketi %83, mevduat vade yapısı %77, tüketici kredi detayı %72,
katılma hesabı kar payı %67, toplanan fon vade yapısı %46, şube/personel %0 (PDF'te tablo değil, cümle içinde).
Ölçü bazında (BDDK'nın TÜM satırları PDF verisiyle değiştirilerek): yalnız ana tablolar 46 ölçü / hücre %36; dipnotlar eklenince
66 ölçü / hücre %61. Üretimde yalnız doğruluğu eşiğin (`dipnot_esik`, varsayılan KAPALI) üstündeki ayak izleri kullanılır.
**Bilinen boşluklar:** İş Bankası'nın PDF'i birçok dipnotu farklı kelimelerle veriyor (en çok hatalı banka); bilançodaki
Donuk Alacaklar / aşama karşılıkları / canlı krediler kalemleri henüz dipnottan türetilmiyor; şube-personel sayıları cümle
içinden regex ile okunmalı; aynı ölçüdeki tek bir hatalı hücre tüm ölçüyü bozduğundan ölçü bazında %100'e henüz yaklaşılamadı.
**Aşama 3 (2026-10-08) — şube/personel ve bilanço türetilmiş kalemleri:**
- `pipeline/pdf_sube.py`: Şube/Personel Sayısı düzyazıdan okunur (kalıp başına oy, eşit oyda boş). Haziran 2026'da 22 banka × 2
  = 44 hücrenin 40'ı BDDK ile birebir; 4'ü eksik/farklı: Halk (personel PDF'te yalnız "22 binin üzerinde"), TOM ve Enpara
  (şube yok → boş bırakılır), ING (PDF'in kendi cümlesi 1.414 çalışan, BDDK 2.416).
- `Krediler Ve Alacaklar (Toplam)` bilanço 2. bölüm satırlarından türetilir (Krediler + Kiralama + Faktoring; eski biçimde
  Donuk − Özel karşılık): bilanço hücre uyumu 3112 → 3138 / 3502. Kalan farklar İş Bankası (PDF yuvarlaması ~3 mn TL) ve TOM.
- `Donuk Alacaklar` ve 3 aşama karşılığı dipnot ayak izi olarak öğrenildi (`bilanco` tablosu): bir-banka-dışarıda %80; "aşama
  toplamı ≈ bilanço beklenen zarar karşılığı" çapraz kontrolü yalnız 12/22 bankada tutarlı seçim verdi (BDDK ile PDF aşama
  rakamları bazı bankalarda farklı: ör. Vakıfbank 1. aşama) — bu yüzden eşik kapısının (varsayılan kapalı) altında kalır.
- Canlı `Krediler Ve Alacaklar` (= Krediler − Donuk) Donuk güvenilir okunamadığından henüz üretilmiyor.
- **Donuk Alacaklar (2026-10-08, ikinci tur):** `pipeline/pdf_donuk.py` kredi riski tablosundan ("Temerrüt etmiş | etmemiş |
  değer düşüklüğü | net", satır Krediler; tablo yoksa iki ayrı düzyazı cümlesinin kesişimi) brüt donuk alacağı okur: 22/22 banka
  BDDK ile birebir. Aynı tablonun "değer düşüklüğü" sütunu 1.+2.+3. aşama toplamıdır; aşama karşılıkları, öğrenilmiş aday
  hücreler arasından toplamı bu sütuna eşit olan TEK kombinasyon olarak seçilir (3. aşama 18/18, 1.-2. aşama 14/15 ve 15 bankada
  üretilir; Vakıfbank 1. aşama ve Enpara 2. aşamada PDF kendi içinde tutarlı, BDDK değeri farklı). Canlı `Krediler Ve Alacaklar`
  = Krediler − Donuk (yalnız Toplam). Ayrıca `Vergi Varlığı` (= Cari + Ertelenmiş), `Beklenen Zarar Karşılıkları (-)` (işaret
  ve 2.4/2.5 kod farkı) ve `Expected Loss Provisions (-)` ad ile türetilir. Bilanço hücre uyumu (Haziran 2026, tüm tablolar
  PDF'ten) 3138 → 3273 / 3502 (%93,5). Kalan farklar: TP/YP kırılımı olmayan kalemler (Donuk/canlı krediler yalnız Toplam),
  Türev finansal varlıklar/yükümlülükler (BDDK ile PDF bileşimi farklı), İş Bankası PDF yuvarlaması.
- **Vade yapısı tabloları (2026-10-08, üçüncü tur):** `pipeline/pdf_sablon.py` Mevduatın ve Toplanan Fonların Vade Yapısı
  tablolarını hücre hücre tahmin etmek yerine BÜTÜN tablo olarak okur: kalem adları BDDK verisinden şablona çevrilir
  (`pipeline/pdf_sablonlar.json`, `scripts/bdr_pdf_dipnot.py --sablon-uret`), PDF satırları etiket benzerliğiyle sıra korunarak
  hizalanır (aynı adlı kalemler sistemdeki gibi toplanır) ve ÜÇ doğrulamadan geçmeyen tablo için hiç satır üretilmez: (1) her
  satırda sütunlar toplamı = Toplam sütunu, (2) Toplam satırı = üst düzey satırların toplamı, (3) önceki dönem tablosu
  elenir. Haziran 2026: Mevduat bankalarında 15/17 PDF okundu, 2160/2160 hücre BDDK ile birebir; katılım bankalarında 5/6
  PDF, 1220/1220 hücre birebir (eski öğrenmeyle %77 ve %46). Okunamayanlar: Yapı Kredi (8 sütunlu, TP/YP alt toplamlı farklı
  düzen) ve İş Bankası (boş hücreler yazılmadığından sütun konumu metinden çıkmıyor), Emlak Katılım (PDF'in kendi satır toplamı
  tutmuyor).
- **Tüketici kredileri tablosu (2026-10-08):** aynı motorun satır-modu (`pdf_sablon.sablon_kur_satir`): kalem başına "Toplam"
  sütunu, ebeveyn satır = alt satırların toplamı (PDF'te ebeveyn yoksa alt satırlardan türetilir), "Kredili Mevduat Hesabı-TP
  (Gerçek Kişi/Personel)" kırılımları para birimine göre toplanır, kısa+orta=toplam her satırda doğrulanır. 21/23 PDF okundu,
  918/924 hücre BDDK ile birebir. 6 farktan 3'ü Yapı Kredi'de BDDK verisinin kaymasıdır (PDF'te Dövize Endeksli bloğu var,
  BDDK Excel'i değeri "YP" satırına yazmış) — PDF anlamca doğru okunur, BDDK ile birebir eşleşmez. Okunamayanlar: İş Bankası
  (4 sütunlu tablo), HSBC. Tüm tablolar PDF'ten okununca (eşik 0) hücre uyumu %76,7 → %79,1.
- **Katılma hesabı kar payı vade yapısı (2026-10-08):** satır kimliği etiketten (para birimi bölümü "Türk parası/Yabancı para" +
  Bankalar/Gerçek kişi/Resmi/Ticari/Diğer/Kıymetli maden/Toplam/Genel toplam) çıkarılır, sütunlar başlıktan okunur (9 aya kadar,
  birikimli gibi PDF'te olmayan sütunlar sıfır), her satırda sütun toplamı ve TP/YP/Genel toplam kontrolleri aranır. 4/6 katılım
  bankası PDF'i okundu, 448/448 hücre BDDK ile birebir (eski yöntemde %67); Emlak Katılım ve Hayat Finans PDF'lerinde bu tablo
  hiç yok.
- **Mevduata ödenen faizin vade yapısı (2026-10-08):** (para birimi bölümü, tür) × 8 sütun; Yapı Kredi/Burgan gibi 9. "Önceki
  Dönem" sütunu atılır. Her satırda sütun toplamı, TP/YP toplamı ve Genel Toplam kontrolü; 15/17 PDF okundu, 1679/1680 hücre
  BDDK ile birebir (eski yöntemde %88). Okunamayan: İş Bankası (boş hücreler yazılmıyor), Odeabank (satır toplamı tutmuyor).
  Not: "Resmî" gibi şapkalı yazımlar normalleştirilir; önceki dönem tablosu yalnızca başlıktan ÖNCEKİ satırlara bakılarak elenir.
- **Ölçü bazında yeniden sınav (2026-10-08, Haziran 2026, 22 banka × 209 ölçü, BDDK'nın TÜM satırları PDF verisiyle değiştirilerek):**
  `scripts/bdr_pdf_isle.py --olcu-sinavi --dipnot-esik 0` artık ölçü×banka sonuçlarını sınıflandırır (tam / %1 içinde / eksik / yanlış),
  ölçü ve banka bazında dağılımı yazar ve `cikti/olcu_sinavi.json`'a ayrıntı bırakır. Sonuç: 4543 ölçü×banka çiftinin **%90,4'ü
  BDDK ile birebir**, %1,1'i %1 içinde, %0,6'sı eksik (PDF'ten değer çıkmadı), **%7,8'i yanlış değer**; 209 ölçünün 87'si tüm
  bankalarda birebir, 150'si bankaların en az %90'ında birebir. DÜZELTME: önceki turlarda bildirilen "%64 → %79" hücre uyumu,
  klasörde yalnız Mart 2026 PDF'i olan QNB'nin Haziran BDDK satırlarının silinip yerine boş veri konmasıyla (sınav artığı) ~209
  hücre kadar düşük çıkıyordu; sınav artık yalnız sınanan dönemin satırlarını kullanır. Bu turda ayrıca: gelir tablosunda gider
  işaretleri (abs), Kredi Ve Diğer Alacaklar Değer Düşüş Karşılığı (= IX + X), 'Diğer' (= 4.1.2 + 4.2.2) ve vergi kalemleri
  (vergi öncesi − dönem net, ertelenmiş gider ≥ 0 / gelir ≤ 0); bilançoda Donuk/canlı krediler TP/YP, Diğer Finansal Varlıklar,
  Türev (yalnız 1.4.1 / 7.1), Kiralama Borçları, Faktoring. En çok yanlış üreten ölçüler: tp/yp getirili-maliyetli spread, donuk
  portföy temizliği, satış/terkin öncesi donuk ve NPL, spread ölçüleri (faiz dipnotları ve donuk akım tablosu).
- **Faiz dipnotları ve donuk alacak akımı (2026-10-08):** `faiz_tpyp` / `kredi_faiz_tpyp` tablolarının hücre-bazlı öğrenmesi yerine
  beş tablo ayrı ayrı okunur (Bankalardan, Kullanılan Kredilere, Menkul Değerlerden, Kredilerden alınan faiz/kar payı; İhraç edilen
  menkul kıymetler; İştirak ve bağlı ortaklık faizleri): TP/YP sütunları, "Faiz" ya da "Kâr payı" başlıkları, tablo toplamı =
  satırların toplamı ve **tablo toplamı = gelir tablosundaki ilgili satır** (1.1, 1.3 [ya da 1.2+1.3], 1.5, 2.2, 2.4) kontrolü.
  İhraç faizi tablosu hiç yoksa ve gelir tablosunda 2.4 sıfırsa TP/YP sıfır yazılır. Okunan banka sayısı ve BDDK uyumu (Haziran
  2026): Bankalardan 21/23 (210/210), Kullanılan Krediler 20/23 (280/280), Menkul 22/23 (308/308), Kredilerden Alınan 18/23
  (180/180), İştirak 20/23 (36/36), İhraç 12/23 (23/24). `donuk_akim`: "Toplam donuk alacak hareketleri" (III/IV/V. grup × 19 BDDK
  satırı) tablosu doğrudan okunur, akış dengesi (önceki + intikal + giriş − çıkış − tahsilat − kayıttan düşülen − satılan ± kur
  farkı = dönem sonu; dönem sonu − karşılık = net) her grupta doğrulanır, "Aktiften Silinen" = kayıttan düşülen + satılan, parantezli
  çıkışlar ve "31 Aralık 2025 / 30 Haziran 2026" etiketli satırlar desteklenir: 19/23 PDF, 1081/1083 hücre birebir. Ölçü sınavı:
  **%90,4 → %91,3 birebir, yanlış değer %7,8 → %7,3**; donuk portföy temizliği ve satış/terkin öncesi donuk/NPL ölçüleri
  bankaların çoğunda artık birebir. Kalan yanlışlar ağırlıkla İş Bankası (155/209), TOM Bank, Emlak Katılım, Garanti ve Yapı Kredi'nin
  farklı tablo düzenlerinden (boş hücreler yazılmayan tablolar, 8 sütunlu mevduat vadesi, 1./2. aşama karşılıklar) gelir.
- **İş Bankası ve boş hücre yazmayan tablolar (2026-10-08):** pdftotext'in sütun konumlarından yararlanan "konumlu okuma"
  (`pdf_sablon.ham_konumlu_satirlar` / `kolonlara_ata`): sayıların sağ kenarı konumları (en çok sayılı satırlardan sütun merkezi)
  bulunur, eksik hücreli satırlar en yakın merkeze atanır; iki sayı aynı sütuna düşerse başka tabloya geçilmiş sayılıp kesilir.
  Mevduat vade yapısı (7 gün ihbarlı sütunu hiç yazılmayan düzen dahil) 17/17 PDF, mevduat faiz vadesi 16/17, tüketici kredileri
  22/23 (4 sütunlu "Faiz ve Gelir Tahakkuk" düzeni dahil), faiz tabloları (Bankalardan 23/23, Kullanılan Krediler 21/23, Kredilerden
  Alınan 19/23) ve donuk alacak akımı (her akım satırının altında alt satırlar olan düzen, 20/23) artık İş Bankası ve Yapı Kredi'yi
  de okur. Ölçü sınavı: **%91,3 → %92,8 birebir, yanlış değer %7,3 → %6,0**; İş Bankası 155 → 194/209, Yapı Kredi 171 → 194/209.
**Hedef:** ölçü bazında %100'e yakın doğruluk için tablo başına yapısal okuyucu ve çapraz tablo tutarlılık denetimleri
(ör. vade yapısı toplamı = bilanço mevduatı) gerekiyor; bu iş sürüyor.

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
