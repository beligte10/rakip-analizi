# Banka Logoları

Bu klasöre logo dosyalarını koyun, sonra şu komutu çalıştırın:

```bash
python scripts/embed_logos.py --optimize --yaz
```

`--optimize`: 60 KB üstü SVG'ler 64×64 px PNG'ye çevrilerek gömülür
(orijinal dosyalar bu klasörde **korunur**). Logolar arayüzde 18×18 px
rozet olarak gösterildiği için görsel fark olmaz, ama HTML çok küçülür —
ilk denemede 1215 KB → 191 KB. macOS `qlmanage` kullanır; yoksa orijinal
gömülür, hata vermez.

Optimizasyon istemiyorsanız `--optimize` olmadan çalıştırın.

Script logoları base64 data URI olarak `index_v30.html` içine gömer — böylece
HTML tek dosya / offline çalışmaya devam eder (harici istek yok).

## Dosya adlandırma

Dosya adı `data/catalog.json`'daki banka adıyla **birebir aynı** olmalı
(Türkçe karakterler dahil):

```
Kuveyt Türk.svg
QNB Finansbank.png
Denizbank.svg
TEB.png
Vakıf Katılım.svg
Ziraat Katılım.png
```

Adı eşleşmeyen dosyalar atlanır ve script uyarı verir.

## Format

- Desteklenen: `.svg` `.png` `.jpg` `.jpeg` `.webp`
- **SVG tercih edilir** — küçük dosya, her ölçekte net görünür
- PNG kullanıyorsanız şeffaf arka planlı ve ~64×64 px yeterli
- 60 KB üstü dosyalarda script uyarır (HTML boyutunu şişirir)

## Notlar

- Logolar 18×18 px rozet alanında, oranı korunarak (`object-fit: contain`)
  beyaz zemin üzerinde gösterilir.
- Logosu olmayan banka otomatik olarak renkli baş-harf rozetine düşer —
  hata vermez, eksik logo sorun çıkarmaz.
- Logolar ilgili bankaların tescilli markalarıdır; bu dashboard içinde
  yalnızca ilgili kurumu tanımlamak (rekabet analizi) amacıyla kullanılır.
