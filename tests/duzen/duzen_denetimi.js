// Mobil / tablet düzen denetimi (2026-10-03).
// Panoda (index_v30.html) çalışır: görünümleri ve pencereleri sırayla açar, her durumda düzen
// hatalarını toplar. scripts/duzen_denetimi.py bunu başsız Chrome'da farklı ekran boyutlarında
// çalıştırır; tarayıcı konsolundan da kullanılabilir:  await window.__duzenDenetimi()
//
// Hata (test başarısız olur):
//   tasma      — sayfa yatay kayıyor (belge, ekrandan geniş)
//   disari     — görünür bir öğe ekranın dışına taşıyor (kendi kaydırma kabı içinde olanlar hariç)
//   kesik      — metin kutusuna sığmıyor ve üç nokta (…) olmadan kesiliyor
//   yarim      — kart/düğme, kaydırılamayan bir kabın dışına taşıyor (yarım görünür)
//   cakisma    — iki tıklanabilir öğe üst üste biniyor
//   kucuk_hedef— dokunmatik ekranda 28 px'ten küçük tıklanabilir öğe
//   kucuk_yazi — 9 px'ten küçük yazı
(function() {
  var bekle = function(ms) { return new Promise(function(r) { setTimeout(r, ms); }); };

  function yol(el) {
    var p = [];
    for (var n = el; n && n.nodeType === 1 && p.length < 4; n = n.parentElement) {
      var t = n.tagName.toLowerCase();
      if (n.id) { p.unshift(t + '#' + n.id); break; }
      var c = (n.getAttribute('class') || '').trim().split(/\s+/).filter(Boolean).slice(0, 2).join('.');
      p.unshift(t + (c ? '.' + c : ''));
    }
    return p.join(' > ');
  }
  function gorunur(el) {
    var r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    for (var n = el; n && n.nodeType === 1; n = n.parentElement) {
      var cs = getComputedStyle(n);
      if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return false;
    }
    return true;
  }
  // Öğe, yatayda kaydırılan ya da kırpan bir kabın içinde mi? (o zaman taşması kasıtlıdır)
  function kirpilanKapta(el) {
    for (var n = el.parentElement; n && n !== document.body; n = n.parentElement) {
      var ox = getComputedStyle(n).overflowX;
      if (ox === 'auto' || ox === 'scroll' || ox === 'hidden' || ox === 'clip') return true;
    }
    return false;
  }
  // En yakın kırpan ama kaydırılamayan ata (overflow hidden/clip)
  function kirpanKap(el) {
    for (var n = el.parentElement; n && n !== document.body; n = n.parentElement) {
      var ox = getComputedStyle(n).overflowX;
      if (ox === 'auto' || ox === 'scroll') return null;
      if (ox === 'hidden' || ox === 'clip') return n;
    }
    return null;
  }
  // translate="no", grafik içi (svg) ve bilinçli dışarıda tutulan öğeler denetlenmez
  function atla(el) {
    return el.closest('svg, [data-duzen-atla], .no-print[aria-hidden="true"]');
  }
  function ustte(el, r) {
    var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    if (cx < 0 || cy < 0 || cx > window.innerWidth || cy > window.innerHeight) return false;
    var t = document.elementFromPoint(cx, cy);
    return !!t && (t === el || el.contains(t) || t.contains(el));
  }
  // Öğe ya da bir atası sabit konumlu mu (yüzen düğme, sohbet paneli)?
  function sabitMi(el) {
    for (var n = el; n && n.nodeType === 1; n = n.parentElement) if (getComputedStyle(n).position === 'fixed') return true;
    return false;
  }
  var TIKLANABILIR = 'button, a[href], input:not([type=hidden]), select, textarea, [role=button], [role=tab], [role=radio], [role=menuitem]';

  function denetle(durum) {
    var W = window.innerWidth, out = [];
    function ekle(tur, el, bilgi) { out.push({ durum: durum, tur: tur, oge: el ? yol(el) : '', bilgi: bilgi || '' }); }
    var doc = document.documentElement;
    if (doc.scrollWidth > W + 1) ekle('tasma', null, 'belge ' + doc.scrollWidth + ' px, ekran ' + W + ' px');
    // Ana yerleşim kapları yatay kaymamalı (body overflow-x:clip sayfa taşmasını gizler; kap içi kayma da hatadır)
    document.querySelectorAll('.main-panel, .dashboard-grid, .comp-grid, .export-grid, .control-bar, .date-selector-bar, .topbar').forEach(function(k) {
      if (gorunur(k) && k.scrollWidth > k.clientWidth + 1) ekle('tasma', k, k.scrollWidth + ' px içerik, ' + k.clientWidth + ' px kap');
    });

    var tum = document.body.querySelectorAll('*');
    var tiklananlar = [];
    for (var i = 0; i < tum.length; i++) {
      var el = tum[i];
      if (atla(el) || !gorunur(el)) continue;
      var r = el.getBoundingClientRect(), cs = getComputedStyle(el);
      if (cs.position !== 'fixed' && (r.right > W + 1 || r.left < -1) && !kirpilanKapta(el)) {
        ekle('disari', el, Math.round(r.left) + '…' + Math.round(r.right) + ' / ' + W);
      }
      // Kırpan (kaydırılamayan) bir kabın dışına taşan kart/düğme: ekranda yarım görünür
      if (/^(BUTTON|A|SELECT|INPUT)$/.test(el.tagName) || /(^|\s)(group-cell|competitor-card-mini|summary-card|chip)(\s|$)/.test(el.className || '')) {
        var kap = kirpanKap(el);
        if (kap) {
          var kr = kap.getBoundingClientRect();
          if (r.right > kr.right + 2 || r.left < kr.left - 2) ekle('yarim', el, 'kap: ' + yol(kap));
        }
      }
      // kesik metin: kendi metni olan, kırpan ve üç nokta kullanmayan öğe
      var kendiMetni = Array.prototype.some.call(el.childNodes, function(n) { return n.nodeType === 3 && n.nodeValue.trim(); });
      if (kendiMetni && (cs.overflowX === 'hidden' || cs.overflowX === 'clip') && cs.textOverflow !== 'ellipsis'
          && el.scrollWidth > el.clientWidth + 2) {
        ekle('kesik', el, el.textContent.trim().slice(0, 40));
      }
      if (kendiMetni && parseFloat(cs.fontSize) < 9) ekle('kucuk_yazi', el, cs.fontSize + ' "' + el.textContent.trim().slice(0, 30) + '"');
      // Yalnız ekranda görünen ve merkezinde en üstte olan (bir pencerenin altında kalmayan) öğeler
      if (el.matches(TIKLANABILIR) && !el.disabled && ustte(el, r)) {
        // Etiketin içindeki onay kutusu / radyo: dokunma alanı etiketin tamamıdır
        var lab = /^(checkbox|radio)$/.test(el.type) && el.closest('label');
        tiklananlar.push({ el: el, r: lab ? lab.getBoundingClientRect() : r, sabit: sabitMi(el) });
      }
    }
    var dokunmatik = W <= 1024;
    for (var a = 0; a < tiklananlar.length; a++) {
      var A = tiklananlar[a];
      // Paragraf içindeki metin bağlantıları (satır içi) dokunma hedefi kuralından muaftır
      var satirIci = A.el.tagName === 'A' && getComputedStyle(A.el).display === 'inline' && A.el.closest('p, li');
      if (dokunmatik && !satirIci && (A.r.height < 28 || A.r.width < 28)) {
        ekle('kucuk_hedef', A.el, Math.round(A.r.width) + '×' + Math.round(A.r.height) + ' "' + (A.el.textContent || A.el.getAttribute('aria-label') || '').trim().slice(0, 24) + '"');
      }
      for (var b = a + 1; b < tiklananlar.length; b++) {
        var B = tiklananlar[b];
        if (A.el.contains(B.el) || B.el.contains(A.el)) continue;
        if (A.sabit !== B.sabit) continue;   // yüzen düğme (Asistan) kaydırılan içeriğin üstünden geçer: kasıtlı
        var ox = Math.min(A.r.right, B.r.right) - Math.max(A.r.left, B.r.left);
        var oy = Math.min(A.r.bottom, B.r.bottom) - Math.max(A.r.top, B.r.top);
        if (ox > 4 && oy > 4) ekle('cakisma', A.el, '↔ ' + yol(B.el));
      }
    }
    return out;
  }

  function dugme(secici, metin) {
    var l = Array.prototype.slice.call(document.querySelectorAll(secici));
    return metin ? l.find(function(b) { return metin.test(b.textContent); }) : l[0];
  }
  async function tikla(el, ms) { if (el) { el.click(); await bekle(ms || 700); return true; } return false; }
  async function kapat() {
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    var o = document.querySelector('.pw-modal-overlay');
    if (o) o.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    var k = document.querySelector('.pw-modal-close, .wn-modal-close, .pdfm-kapat');
    if (k && document.querySelector('.pw-modal-overlay')) k.click();
    var b = document.querySelector('.topbar-menu-backdrop'); if (b) b.click();
    await bekle(400);
  }
  async function menuden(re) {
    await tikla(document.querySelector('.topbar-menu-btn'), 400);
    var d = dugme('.topbar-toolbar button, .topbar-toolbar a', re);
    if (!d) { await kapat(); return false; }
    await tikla(d, 900);
    return true;
  }

  // Sayfayı ekran ekran kaydırarak denetler (alttaki öğeler de ölçülsün); aynı sorun bir kez yazılır.
  async function sayfaBoyunca(durum) {
    var out = [], gor = {}, H = window.innerHeight;
    var son = Math.min(document.documentElement.scrollHeight, H * 8);
    for (var y = 0; y < son; y += Math.round(H * 0.8)) {
      window.scrollTo(0, y); await bekle(250);
      denetle(durum).forEach(function(x) { var k = x.tur + x.oge + x.bilgi; if (!gor[k]) { gor[k] = 1; out.push(x); } });
    }
    window.scrollTo(0, 0); await bekle(150);
    return out;
  }
  window.__duzenDenetimi = async function() {
    var sonuc = [], gezilen = [];
    var _sb = sayfaBoyunca, _dn = denetle;
    // hangi ekranların gerçekten açılıp denetlendiği raporlanır (sessizce atlanan ekran "0 sorun" sayılmasın)
    sayfaBoyunca = async function(d) { gezilen.push(d); return _sb(d); };
    denetle = function(d) { if (gezilen.indexOf(d) < 0) gezilen.push(d); return _dn(d); };
    var mod = function(i) { return document.querySelectorAll('.date-selector-bar .mode-btn')[i]; };
    window.scrollTo(0, 0);
    await bekle(600);
    sonuc = sonuc.concat(await sayfaBoyunca('anlik'));
    await tikla(document.querySelector('.topbar-menu-btn'), 500);
    sonuc = sonuc.concat(denetle('menu'));
    await kapat();
    await tikla(mod(1), 1500); sonuc = sonuc.concat(await sayfaBoyunca('trend'));
    await tikla(mod(2), 1200); sonuc = sonuc.concat(await sayfaBoyunca('kompozisyon'));
    await tikla(mod(0), 1000);
    if (await menuden(/PDF/)) { sonuc = sonuc.concat(denetle('pdf_penceresi')); await kapat(); }
    if (await menuden(/Ölçü Oluştur|Create Measure/)) { sonuc = sonuc.concat(denetle('olcu_olustur')); await kapat(); }
    if (await menuden(/Odak|Focus/)) { sonuc = sonuc.concat(denetle('odak_penceresi')); await kapat(); }
    if (await menuden(/Yenilikler|What/)) { sonuc = sonuc.concat(denetle('yenilikler')); await kapat(); }
    if (await tikla(document.querySelector('.chat-fab'), 600)) {
      sonuc = sonuc.concat(denetle('asistan'));
      await tikla(dugme('.chat-head button', /✕/), 400);
    }
    if (await menuden(/Excel/)) { sonuc = sonuc.concat(await sayfaBoyunca('disa_aktar')); await tikla(mod(0), 800); }
    sayfaBoyunca = _sb; denetle = _dn;
    return { ekran: window.innerWidth + '×' + window.innerHeight, gezilen: gezilen, sorunlar: sonuc };
  };
  window.__duzenDenetle = denetle;
})();
