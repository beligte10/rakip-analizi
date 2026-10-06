"""
assistant.service
==================
Sohbet döngüsü: model ↔ araçlar, en fazla MAX_ROUNDS tur. Tarayıcıya giden
olaylar (SSE'de her biri bir JSON satırı):

    {"type": "delta",  "text": "..."}                 yanıt parçası
    {"type": "tool",   "name": "...", "label": "...", "detay": "..."} araç çalışıyor (detay: ölçü · banka · dönem özeti)
    {"type": "draft",  "draft": {...}}                özel ölçü taslağı kartı
    {"type": "action", "action": "open_view", ...}    ekranda görünüm aç
    {"type": "error",  "message": "..."}
    {"type": "done"}

Gizlilik: modele kullanıcının adı/e-postası GÖNDERİLMEZ; yalnız soru,
katalogdan seçilen tanımlar ve araçların döndürdüğü (kamuya açık BDDK
kaynaklı) değerler gider.
"""
from __future__ import annotations

import json
from typing import Iterator, List, Optional

from . import llm
from .knowledge import Store, View
from .external import evds as ext_evds, tuik as ext_tuik
from .tools import TOOL_LABELS, active_specs, arac_ozeti, execute

MAX_ROUNDS = 16   # analist yanıtları birden çok ölçü/kıyas topladığı için
SON_TUR_NOTU = ('Araç çağırma hakkın bitti. Şu ana kadar araçlardan gelen verilerle yanıtını şimdi yaz; '
                'eksik kalan noktaları "veri çekilemedi" diye kısaca belirt, rakam uydurma.')
MAX_HISTORY = 20
MAX_MSG_CHARS = 4000

SYSTEM_PROMPT = """Sen "KT Rakip Analizi" panosunun kıdemli banka analistisin: Türkiye bankacılık sektörünü \
yıllardır izleyen, yatırımcı sunumu ve yönetim kurulu notu hazırlamış bir sell-side / strateji analisti gibi \
düşünürsün. Kuveyt Türk Strateji ekibine rekabet analizinde destek veriyorsun. Veri: BDDK'nın kamuya açık \
çeyreklik solo finansal tablolarından türetilmiş {n_banks} banka × {n_dates} dönem ({first} → {last}) × \
{n_measures} ölçü. Varsayılan (en güncel) dönem: {last}. Panonun odak bankası: {odak} (kullanıcı "biz", \
"bankamız" derse bu bankadır; karşılaştırmalar varsayılan olarak onun etrafında kurulur).

KURALLAR (değişmez)
1. Sayıları ASLA tahmin etme ya da hafızadan yazma. Her rakam bir araç sonucundan gelmeli. Araç değer \
döndürmezse "bu dönem için veri yok" de. Sektör hakkındaki genel bilgini yalnız YORUM için kullan, rakam için değil.
2. Rakamları araçların verdiği "gosterim" alanıyla aynen yaz (birim ve ölçek hazır). Değişimler için \
araçların "degisim" alanını kullan. Kendi hesabın yalnız aynı birimdeki iki rasyo arasındaki basit fark \
(puan / bps) olabilir; bunu yaptığında "fark" diye belirt. Oran, büyüme ya da toplam türetme.
3. Ölçü id'sini bilmiyorsan önce search_measures çağır. Birden fazla aday uygunsa en uygununu seç ve \
hangisini kullandığını belirt; gerçekten belirsizse kullanıcıya sor.
4. Grup değerleri (Katılım Bankaları, Mevduat Bankaları, Rakip Bankalar …) üyelerin toplamından \
hesaplanır (rasyolarda pay toplamı / payda toplamı), basit ortalama değildir. Sorulursa bunu açıkla.
5. Yeni ölçü isteğinde: önce search_measures ile bileşen ölçülerin id'lerini bul, sonra \
propose_custom_measure ile taslak oluştur. Hazır bir ölçü isteği zaten karşılıyorsa önce onu öner. \
Taslak kartta görünür; kaydetmek için kullanıcı "Kaydet"e basar — "kaydettim" deme. Kural hatası \
dönerse düzeltip tekrar dene ya da neden mümkün olmadığını açıkla.
6. Kullanıcı bir ölçüyü "göster/aç" derse open_view kullan.
7. Yatırım tavsiyesi verme (hisse al/sat, hedef fiyat yok). Stratejik çıkarım ve soru önerisi serbesttir.
8. Bu pano dışındaki konularda (genel sohbet, kod yazma vb.) kibarca yalnız bu veriyle yardım \
edebildiğini söyle.

ANALİST GİBİ ÇALIŞ
0. ÖNCE VERİ: Banka, grup, ölçü ya da dönem içeren her soruda yanıt yazmadan ÖNCE araçlarla (get_values, \
rank_banks …) veriyi çek. Araç sonucu olmadan tablo, yorum ya da "sürücü" yazma; "[Değer]" gibi yer tutucu \
ASLA kullanma. Aşağıdaki çerçeve neyi çekeceğini planlamak içindir, verinin yerine geçmez.
A. Tek rakamla yetinme; her bulguyu üç eksende bağlama oturt. HIZ KURALI: araç turların sınırlıdır. Analiz
sorularında ÖNCE get_analysis_pack ile ilgili paket(ler)i tek çağrıda getir (karlilik, marj, aktif_kalitesi,
verimlilik, fonlama, sermaye, buyume); paketin kapsamadığı ölçüler için get_values'a measure_ids ver (tek
çağrıda 8 ölçüye kadar) ve gerekirse tek rank_banks. Ölçüleri tek tek search_measures/get_values ile
toplama; en fazla 3-4 araç turunda veriyi tamamla, sonra yanıtı yaz:
   - Kıyas: odak banka ↔ Katılım Bankaları / Rakip Bankalar / Mevduat Bankaları grubu ve rank_banks ile sıra.
   - Zaman: son çeyrek, bir önceki çeyrek ve geçen yılın aynı dönemi (yıllık ölçülerde yıl sonları). get_values'a \
bu dönemleri TEK çağrıda ver (ör. dates: ["2025-06-30", "2026-03-31", "2026-06-30"]); "degisim" alanı yönü verir.
   - Sürücü: rasyoyu oluşturan bileşenlere in (aşağıdaki ağaçlar). "Ne oldu"dan sonra "neden" ve "ne anlama geliyor".
B. Analiz ağaçları (ölçü id'leri katalogdadır, emin değilsen search_measures):
   - Kârlılık (DuPont): roae ← roaa × kaldıraç; roaa ← nim + ücret/komisyon − faaliyet gideri − kredi riski \
maliyeti (cost_of_risk) − vergi. rorwa sermaye verimliliğini gösterir.
   - Marj: nim ← faiz getirili aktif getirisi − maliyetli pasif maliyeti (spread, kredi_mevduat_spread, tp_spread, \
yp_spread); faiz getirili aktif payı (faiz_getirili_ta) ve aktif karması (krediler_ta, menkul_kiymetler_ta).
     Zorunlu karşılık etkisi: zk_surukleme (getiri − ZK hariç getiri, puan) = bloğun büyüklüğü \
(tcmb_hesabi_getirili_aktif) × getiri farkı (ortuk_tcmb_getirisi); katılım bankalarında marjı bastıran ana neden \
genellikle budur. nim_getirili_aktif (getirili aktif paydalı) ve nim_swap_duzeltilmis (yalnız türev K/Z) ile birlikte oku; \
bu ölçüler `zorunlu_karsilik` paketinde.
   - Aktif kalitesi: npl_rasyosu (satış/terkin öncesiyle birlikte oku), npl_formasyonu, grup_2_krediler_toplam, \
npl_karsilama_orani, cost_of_risk. NPL düşüşü satış/terkinden mi, tahsilattan mı geliyor ayırt et: \
donuk_tahsilat_intikal, donuk_portfoy_temizligi (terkin+satış / dönem başı donuk), donuk_net_olusum; karşılık \
düzeyi için npl_3_asama_karsilama ve grup_2_karsilama (npl_karsilama_orani toplam karşılığı kullanır, bunlar aşama bazlıdır).
   - Verimlilik: maliyet_gelir, faaliyet_gid_ort_aktif, opex_yoy_buyumesi ↔ gelir büyümesi (opex_gelir_makasi), \
reel_opex_buyumesi; şube/personel başına ölçüler.
   - Fonlama ve likidite: krediler_mevduat, vadesiz_mevduat_toplam_mevduat, alinan_krediler_iemk_toplam_kaynak, \
TP/YP kaynak dengesi, likidite açığı vade dilimleri.
   - Sermaye: syr, cekirdek_syr, rav büyümesi ↔ kredi büyümesi, yp_net_pozisyon_ozkaynak, rav_yogunlugu. \
Basel III kaldıraç oranı, LCR, serbest karşılık ve TÜFEX tamponu BDDK verisinde yoktur; yalnız elle yüklenen \
dönemlerde dolu olur, boşsa uydurma. 2026'da SYR/RAV karşılaştırırken BDDK'nın 01.01.2026'da kaldırdığı sabit kur \
esnekliğini hatırlat (RAV yoğunluğundaki sıçrama organik risk alımı değildir).
   - Büyüme ve pazar payı: tutar ölçülerinde rank_banks'in verdiği pay; nominal büyümeyi enflasyon ortamında \
yorumla (yüksek enflasyonda %40 nominal büyüme reel küçülme olabilir; reel/USD görünüm panoda var).
C. Sektör bağlamı ve tuzaklar (yorumda kullan):
   - Katılım bankaları faiz yerine kâr payı ile çalışır; "faiz" ölçüleri onlarda kâr payıdır. Katılım fonu \
maliyeti ve kârın dağıtım yapısı mevduat bankalarından farklıdır; katılımı katılımla, mevduatı mevduatla da kıyasla.
   - Gelir tablosu kalemleri yılbaşından kümülatiftir (YtD); çeyrekleri doğrudan kıyaslarken bunu hatırla. \
ROAA/ROAE/NIM gibi ölçüler yıllıklandırılmış/ortalama bakiyelidir.
   - 2018'de TFRS 9 geçişi var (karşılık ve donuk alacak tanımları değişti); 2018 öncesi ↔ sonrası kıyasında uyar.
   - 2022-2023'te BDDK sermaye esneklikleri (sabit kur, menkul değer) SYR'yi etkiledi; KKM ve zorunlu karşılık \
düzenlemeleri, TCMB faiz döngüsü marjları belirgin biçimde oynattı. Sıra dışı sıçramalarda baz etkisi, \
birleşme/devir, yeni banka (ilk yıllar) ihtimalini belirt.
   - Küçük ve yeni bankalarda (Hayat Finans, TOM Bank, Dünya Katılım, Enpara …) büyüme ve rasyolar düşük bazdan \
uç değerler üretir; ortalamaları onlar üzerinden yorumlama.
   - Analitik dürüstlük: Her ölçüyü katalogdaki adıyla an; başka bir kavram olarak yeniden etiketleme (ör. \
"Ortalama Faiz Getirili Aktifler / Ortalama Özkaynaklar" kaldıraç DEĞİLDİR; doğrudan kaldıraç ölçüsü yoksa \
ROAE ile ROAA'nın birlikte okunmasıyla nitel yorumla). Veride görmediğin bir nedeni (segment, fiyatlama gücü, \
dijitalleşme, yönetim kararı …) olgu gibi yazma: "olası", "işaret ediyor olabilir" diye sun ve hangi ölçüyle \
doğrulanabileceğini söyle. Grup değerleri ortalama DEĞİLDİR: "katılım bankaları ortalaması" ya da "sektör \
ortalaması" yazma; "Katılım Bankaları grubu (%3,10)" gibi yaz.
   - Birim: rasyo değişimlerini bps ile ver; NPL karşılama gibi 100'ün üstündeki oranlarda puanla yaz \
(100 bps = 1 puan; ör. "−18,8 puan").
D. Yanıt biçimi (Türkçe, profesyonel ve öz):
   - İlk satır: tek cümlelik ana sonuç (en önemli bulgu, yönüyle).
   - Sonra küçük bir Markdown tablosu (banka/grup × dönem; birimler gosterim alanından).
   - "Sürücüler" altında 2-4 madde: değişimi ne açıklıyor.
   - "Çıkarım" altında 1-3 madde: odak banka için stratejik anlamı (fırsat, risk, izlenecek gösterge).
   - Gerekirse "Not" ile veri sınırı (eksik dönem, tanım farkı, yapısal kırılma). Kullanılan ölçüleri ve dönemi belirt.
   - Basit bir bilgi sorusuna (ör. "KT'nin son SYR'si?") kısa yanıt ver; tam çerçeveyi analiz, karşılaştırma, \
"neden", "değerlendir", "yorumla" türü sorularda kullan. Uygunsa sonunda bir derinleştirme sorusu öner.{dis_kaynak}{ekran}"""

DIS_KAYNAK = """
E. DIŞ VERİ ({kaynaklar}): Makro veri (faiz oranları, kurlar, enflasyon, sektör kredi/mevduat \
hacimleri, GSYH, işgücü …) sorulursa bu araçları kullan. Akış: önce ara (evds_ara / tuik_ara), \
sonra seri/boyut listesi (evds_seriler / tuik_meta), en son veri (evds_veri / tuik_cek) — kod ya da \
boyut değeri uydurma. Uzun dönemde düşük frekans seç. Dış veriyi pano (BDDK) verisinden ayrı tut ve \
her zaman kaynağını yaz (ör. "Kaynak: TCMB EVDS"). Reel büyüme gibi birleşik hesaplarda iki \
kaynağın dönemlerinin (çeyrek sonu / ay) eşleştiğini belirt. Araç hata dönerse nedenini kısaca söyle."""


EVDS_KURALLARI = """
EVDS KURALLARI (TCMB EVDS bilgi tabanından; ayrıntı için evds_rehber aracını çağır):
- Seri kodunu evds_ara ile katalogdan bul; kodu ezberden/tahminle yazma. Katalogda yoksa "bu kod katalogda yok" de.
- "(Arşiv)" serilerde uyar; güncel baz yılı serisini seç (ör. TÜFE endeksi: TP.TUKFIY2025.GENEL; TP.FG.J0 arşivdir).
- Frekans: yalnız serinin kendi frekansından daha seyrek seçilebilir. Toplulaştırma: stok (bakiye, rezerv) → last/avg, \
akım (ihracat, hacim) → sum, faiz/oran/kur/endeks → avg (sum asla).
- Formül: yıllık enflasyon = TÜFE endeksi + yillik_yuzde_degisim, aylık enflasyon = yuzde_degisim; faiz gibi zaten yüzde \
olan serilerde puan farkı için fark kullan (yuzde_degisim oransal değişimdir).
- Boş (null) değer veri yok demektir, sıfır değildir. Son dönem geçici olabilir, TCMB revize edebilir — hatırlat.
- Her sayıyla birimi, frekansı ve uygulanan dönüşümü ("aylık ortalama", "yıllık % değişim") belirt; birim bilinmiyorsa uydurma.
- Yatırım tavsiyesi verme; yalnızca verinin ne ifade ettiğini açıkla."""


def _dis_kaynak_metni(dis_veri: bool = True) -> str:
    if not dis_veri:
        return ''
    k = [ad for ad, on in (('TCMB EVDS', ext_evds.enabled()), ('TÜİK', ext_tuik.enabled())) if on]
    if not k:
        return ''
    return DIS_KAYNAK.format(kaynaklar=', '.join(k)) + (EVDS_KURALLARI if ext_evds.enabled() else '')


def _ekran_metni(view: View, ekran: Optional[dict]) -> str:
    if not isinstance(ekran, dict):
        return ''
    parcalar = []
    mid = ekran.get('measure_id')
    if isinstance(mid, str) and view.meta(mid):
        parcalar.append(f"ölçü: {view.meta(mid)['ad']} (id: {mid})")
    if isinstance(ekran.get('tarih'), str) and ekran['tarih'] in view.s.dates:
        parcalar.append(f"dönem: {ekran['tarih']}")
    mod = {'snapshot': 'Anında Görünüm', 'trend': 'Trend', 'composition': 'Kompozisyon'}.get(ekran.get('mode'))
    if mod:
        parcalar.append(f'sekme: {mod}')
    if not parcalar:
        return ''
    return ('\n\nKULLANICININ EKRANI (\"bu ölçü\", \"bu dönem\" gibi ifadeler buna işaret eder): '
            + ', '.join(parcalar) + '.')


# Araç çağırmadan yazılmış uzun yanıt büyük olasılıkla veriye dayanmıyor (model çerçeveyi görüp rakamsız
# "analiz" ya da yer tutuculu tablo yazabiliyor — 2026-10-03 denemesi). Böyle bir ilk yanıt gösterilmez,
# model bir kez veriyi araçlarla çekmeye yönlendirilir.
ARACSIZ_SINIR = 300
VERI_HATIRLATMA = ('Yanıtın hiçbir araç sonucuna dayanmıyor. Bu soru veri gerektiriyorsa önce araçlarla '
                   '(search_measures, get_values, rank_banks …) veriyi çek, sonra yalnız dönen değerlerle yanıtla. '
                   'Veri gerektirmiyorsa kısa yanıt ver.')


def _aracsiz_supheli(metin: str) -> bool:
    return len(metin.strip()) > ARACSIZ_SINIR or '[Değer]' in metin or '[değer]' in metin


def clean_history(messages) -> List[dict]:
    """İstemciden gelen geçmiş: yalnız user/assistant metinleri, sınırlı."""
    out = []
    for m in (messages or [])[-MAX_HISTORY:]:
        if not isinstance(m, dict) or m.get('role') not in ('user', 'assistant'):
            continue
        text = str(m.get('content') or '').strip()[:MAX_MSG_CHARS]
        if text:
            out.append({'role': m['role'], 'content': text})
    return out


def run_chat(cfg: llm.LLMConfig, store: Store, history: List[dict],
             custom_records: Optional[List[dict]] = None,
             ekran: Optional[dict] = None, dis_veri: bool = True,
             odak: Optional[str] = None, katman: Optional[dict] = None,
             gizli_olculer=None) -> Iterator[dict]:
    store.refresh()
    view = View(store, custom_records, katman, gizli_olculer)
    view.odak = odak   # kullanıcı bazlı odak banka (yoksa panonun varsayılanı)
    s = store
    system = SYSTEM_PROMPT.format(
        n_banks=len(s.banks), n_dates=len(s.dates), n_measures=len(s.measures),
        first=s.dates[0] if s.dates else '?', last=s.default_date or '?',
        odak=odak or (s.computed.get('meta', {}) or {}).get('focus_bank') or 'Kuveyt Türk',
        dis_kaynak=_dis_kaynak_metni(dis_veri), ekran=_ekran_metni(view, ekran))
    if view.gizli:
        system += ('\n\nBu kullanıcının rolünde "Rekabet Analizi" ölçüleri yoktur: ZK sürüklemesi, TCMB getirisi, '
                   'donuk alacak hareketi/aşama karşılama, kadro-ücret etkisi, efektif vergi, TÜFEX, LCR, kaldıraç gibi '
                   'ölçüleri ne öner ne hesapla; sorarsa bu ölçülerin rolünde kapalı olduğunu söyle.')
    specs = active_specs(dis_veri)
    messages: List[dict] = [{'role': 'system', 'content': system}] + history

    arac_kullanildi = False
    hatirlatildi = False
    for tur in range(MAX_ROUNDS + 1):
        son_tur = tur == MAX_ROUNDS
        if son_tur:
            # Tur sınırı doldu: hata vermek yerine modele eldeki verilerle yanıtını yazdır (araçsız son tur)
            messages.append({'role': 'user', 'content': SON_TUR_NOTU})
        text_parts: List[str] = []
        tool_calls = None
        # Henüz araç çağrılmadıysa metin tamponlanır: araçsız şüpheli yanıt hiç gösterilmeden atılabilsin
        tampon = not arac_kullanildi and not hatirlatildi
        try:
            for kind, payload in llm.stream_chat(cfg, messages, None if son_tur else specs):
                if kind == 'content':
                    payload = llm.cjk_temizle(payload)
                    if not payload:
                        continue
                    text_parts.append(payload)
                    if not tampon:
                        yield {'type': 'delta', 'text': payload}
                elif kind == 'tool_calls':
                    tool_calls = payload
        except llm.LLMError as e:
            yield {'type': 'error', 'message': str(e)}
            return

        metin = ''.join(text_parts)
        if son_tur:
            tool_calls = None   # araç kapalı; yine de çağrı gelirse yok say
            if not metin.strip():
                break
        if not tool_calls and tampon and _aracsiz_supheli(metin):
            hatirlatildi = True
            messages.append({'role': 'assistant', 'content': metin})
            messages.append({'role': 'user', 'content': VERI_HATIRLATMA})
            continue
        if tampon and metin:
            yield {'type': 'delta', 'text': metin}
        if not tool_calls:
            yield {'type': 'done'}
            return
        arac_kullanildi = True

        messages.append({'role': 'assistant', 'content': ''.join(text_parts) or None,
                         'tool_calls': tool_calls})
        for call in tool_calls:
            name = call['function']['name']
            yield {'type': 'tool', 'name': name, 'label': TOOL_LABELS.get(name, name),
                   'detay': arac_ozeti(view, name, call['function']['arguments'])}
            result, event = execute(view, name, call['function']['arguments'], dis_veri)
            if event:
                yield event
            messages.append({'role': 'tool', 'tool_call_id': call['id'],
                             'content': json.dumps(result, ensure_ascii=False, default=str)})

    yield {'type': 'error', 'message': 'Yanıt çok fazla adım gerektirdi; soruyu daraltıp tekrar deneyin.'}
