# Veri Göçü (Sunucu Değiştirme / Yeni Deploy)

## İki yöntem var — hangisini kullanmalısınız?

| | SSH/terminal erişimin var mı? | Nasıl |
|---|---|---|
| **A. Admin panelden (önerilen)** | Gerekmez | Kaynak sunucunun admin panelinde **🚚 Sunucu Taşıma** bölümünden "Veriyi İndir"e tıkla, indirilen ZIP'i hedef sunucunun admin panelindeki "İçe Aktar"a sürükle. İki tık, tarayıcıdan. |
| **B. Script + SSH** | Gerekir | `scripts/export_data_snapshot.py` ile paket üret, `scp`/rsync ile taşı, Docker volume'a elle aç. Hedefte tam `/admin/rebuild` kapasitesi (ham arşiv dahil) gerekiyorsa ya da otomasyona/CI'a gömülecekse. |

**Çoğu durumda A yeterli ve daha güvenli** — tarayıcıdan iki tıkla olur, dosya yolu/izin hatası riski yok. B'ye sadece SSH erişimin olmadığı ya da ham arşivi de taşımak istediğin durumlarda geç.

---

## Yöntem A — Admin panelden (SSH gerekmez)

1. **Kaynak sunucuda:** `/admin`'e gir → **📤 Veri Yükleme** sekmesi → en altta **🚚 Sunucu Taşıma** bölümü → **⬇️ Veriyi İndir**. Tarayıcı bir ZIP indirir (`kt-rakip-analizi-veri_<tarih>.zip`), içinde `computed.json` + `veriler.parquet` + `upload_history.json` + bir `manifest.json` (kaç ölçü/banka/dönem, hangi tarihe kadar, hangi git commit'ten üretildiği) var.
2. İndirilen ZIP'i (birine ilet, mail/Drive/USB — fark etmez) hedef sunucuya ulaştır.
3. **Hedef sunucuda:** `/admin`'e gir → aynı bölümdeki **⬆️ İçe Aktar** kutusuna ZIP'i sürükle. Mevcut veri otomatik yedeklenir (`data/backups/`), sonra ZIP'in içeriği uygulanır. Sonuç ekranında manifesto özeti (kaynağın hangi tarihe kadar veri içerdiği) gösterilir — indirmeden önce mutlaka bu tarihi beklediğinle karşılaştır.
4. Ana sayfaya dönüp hard refresh (Ctrl+Shift+R) yap, güncel veriyi doğrula.

`users.json` (üye hesapları) varsayılan olarak dahil edilmez — sadece iki taraftaki checkbox'ı işaretlersen taşınır (hedefte zaten gerçek üyeler varsa yanlışlıkla silinmesin diye).

**Not:** `data/raw/` (ham xlsx arşivi) bu yönteme dahil DEĞİL — sadece dashboard'un çalışması için gerekli önceden-hesaplanmış veri taşınır. Hedefte tam `/admin/rebuild` kapasitesi de isteniyorsa Yöntem B'deki `--include-raw` gerekir.

---

## Yöntem B — Script + SSH

SSH erişimin yoksa Yöntem A'yı kullan — bu bölüm sadece dosya sistemine/sunucuya doğrudan erişimin olduğu durumlar için.

**Kural: `data/` klasörünü ASLA elle zip'leyip taşıma** (yani proje klasörünü olduğu gibi ziplemek, `data/`'yı da içine alacak şekilde). Bunun yerine `scripts/export_data_snapshot.py` kullan — her zaman `data/computed.json`'daki GÜNCEL veriden paket üretir ve paketin içine hangi tarihe kadar veri olduğunu açıkça yazan bir `MANIFEST.txt` gömer. `data/` bilinçli olarak git'te değil (git-push-to-deploy kurulumunda sunucudaki `git pull`, tracked bir dosyayı eski git kopyasıyla üzerine yazıp canlı veriyi geri alabilir) — yani kod GitHub'dan güncel gelir ama veri gelmez, bunu elle/doğru taşımak senin sorumluluğunda. 2026-08'de tam bunun kurbanı olundu: proje klasörü olduğu gibi zip'lenip yeni bir sunucuya yüklendi, içindeki `data/` klasörü Eylül 2025'te donmuş eski bir kopyaydı, bunu fark edecek bir mekanizma yoktu.

### Paket üretme (kaynak makinede)

```bash
python scripts/export_data_snapshot.py
```

Bu, proje kökünde `rakip-analizi-data_<son-dönem>_<üretim-zamanı>.zip` üretir (~16-20MB, ~9-10 saniye) ve terminale şu manifestoyu basar:

```
Ölçü sayısı          : 160
Banka sayısı         : 27
Son "dolu" çeyrek    : 2026-06-30  (24/27 banka raporlamış)
```

**Taşımadan önce kontrol et:** bu satırdaki tarih, senin beklediğin son dönemle eşleşiyor mu? Eşleşmiyorsa önce lokal `data/`'yı güncelle (admin panelden upload + rebuild, veya `scripts/recompute.py`), sonra script'i tekrar çalıştır. Eski bir manifesto ile devam etme.

Seçenekler:

| Bayrak | Ne zaman kullanılır |
|---|---|
| `--include-raw` | Hedef sunucuda ileride tam `/admin/rebuild` (data/raw/'dan yeniden hesaplama) yapılabilmesi gerekiyorsa. Paket ~180MB'a çıkar. Normal bir "veriyi taşı" işleminde gerekmez — `computed.json` + `veriler.parquet` zaten çalışan bir sistem için yeterli. |
| `--no-users` | Üye hesaplarını (`users.json`) pakete katma — örn. sadece finansal veriyi tazelemek istiyorsan, üye listesine dokunmadan. |
| `--out <yol>` | Paketi proje kökü dışında bir yere yaz. |

### Hedef sunucuya kurma

1. Zip'i sunucuya taşı (`scp`, ya da Coolify/panelin kendi dosya yükleme yolu).
2. Sunucudaki kalıcı volume'ün gerçek host yolunu bul:
   ```bash
   docker inspect <container_adı> --format '{{ json .Mounts }}'
   ```
   `data/` için mount edilen `Source` yolunu not al (örn. `/var/lib/docker/volumes/<isim>-kt-data/_data`).
3. Zip'i doğrudan o yolun İÇİNE aç (üzerine yazmadan önce, o an sunucuda çalışan bir kurulum varsa mevcut `data/`'yı yedekle — `cp -r`). Zip içeriği zaten `data/` önekisiz paketlenmiştir (`computed.json`, `veriler.parquet`, ... doğrudan kökte), yani sonuç doğrudan `_data/computed.json` olur — container içeride bu yolu `/app/data/computed.json` olarak görür:
   ```bash
   unzip rakip-analizi-data_*.zip -d /var/lib/docker/volumes/<isim>-kt-data/_data/
   ```
4. Dosya sahipliğini container'ın çalıştığı non-root kullanıcıya çevir (bu projede uid `10001`):
   ```bash
   chown -R 10001:10001 /var/lib/docker/volumes/<isim>-kt-data/_data/
   ```
5. Container'ı yeniden başlat (Coolify'da "Restart", veya `docker restart <container_adı>`).
6. Doğrula:
   ```bash
   docker exec <container_adı> python3 -c "import json; d=json.load(open('/app/data/computed.json')); print(len(d['bank_data']), 'ölçü')"
   ```
   ya da doğrudan siteyi açıp dashboard'da son dönemin (örn. 2026-06-30) göründüğünü kontrol et.

---

## Her iki yöntemde de ortak tuzak: Upload ile Rebuild'i karıştırmak

Hem Yöntem A hem B, `data/raw/` (ham xlsx arşivi) hariç sadece önceden-hesaplanmış veriyi taşır. Bu, göçten SONRA sunucuda bir tuzak bırakır:

- **Upload** (`/admin/upload`) sadece o an yüklenen dosyaları işler, mevcut veriye **ekler** (upsert). Güvenli, günlük kullanım için budur.
- **Rebuild** (`/admin/rebuild`) sunucudaki **`data/raw/`'ın tamamını** okuyup her şeyi sıfırdan hesaplar. Göç sonrası sunucuda `data/raw/` eksik olduğundan (ham arşiv taşınmadıysa), Rebuild o eksik veriyle tüm geçmişi ezer.

**Sonuç:** Ham arşivi de taşımadıysan (`--include-raw` kullanmadıysan), göç sonrası o sunucuda **sadece Upload kullan, asla Rebuild'e basma.** Bu proje 2026-08'de tam bunu yaşadı (51 dönemden 1 döneme düşüş).

## Pakete dahil olmayanlar (Yöntem B — Yöntem A da aynı kapsamı taşır)

| Dosya/klasör | Neden hariç |
|---|---|
| `computed_backup_*.json`, `veriler_backup_*.parquet`, `computed_datatable_kaynakli_yedek.json` | Eski yedekler; taşınırsa hangisinin "doğru" olduğu belirsizleşir — bu doküman tam bunu önlemeye çalışıyor. |
| `data/backups/` | `app.py`'nin kendi rebuild-öncesi otomatik yedekleri; kaynak makinenin geçmişine ait, hedefte anlamsız. |
| `data/.session_secret` | Oturum çerezi imzalama anahtarı — her deploy kendi anahtarını üretmeli (bkz. `app.py::_get_or_create_session_secret`), sunucuya özel bir sır, taşınması gereksiz. |
| `data/raw/` | Varsayılan olarak hariç (~180MB) — sadece hedefte tam rebuild kapasitesi isteniyorsa `--include-raw` ile dahil et. |

## Küçük veri düzeltmeleri için

Sadece birkaç bankanın/dönemin verisi mi güncellenecek? O zaman tüm bu süreç gereksiz — canlı sitenin admin panelinden doğrudan **Upload** yap, script'e gerek yok. Bu doküman/script yalnızca **sunucu değişimi, yedekten geri yükleme, ya da "sıfırdan yeni bir ortam kurma"** senaryoları içindir.
