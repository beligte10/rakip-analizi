// Sayfa çevirisi (2026-10-02): giriş, başvuru ve admin sayfaları için TR/EN.
// scripts/i18n_gom.py bu dosyayı sayfanın <head>'ine, önüne KT_I18N = {sozluk, bankalar} koyarak gömer.
// Pano (index_v30.html) kendi React tabanlı çevirisini kullanır; dil seçimi ortaktır (localStorage 'kt_dil').
//
// İngilizce seçiliyken:
//  - Sayfadaki metin düğümleri ve placeholder/title/alt/aria-label öznitelikleri sözlükle çevrilir
//    (önce boşlukları sadeleştirilmiş tam eşleşme, yoksa ifade düzeyinde; banka adları korunur).
//  - Sonradan eklenen içerik (innerHTML, textContent) MutationObserver ile çevrilir.
//  - alert / confirm / prompt mesajları satır satır çevrilir.
//  - translate="no" işaretli öğelerin içi (kullanıcı içeriği, sürüm notları, el kitabı) dokunulmaz.
//  - İlk çeviri bitene kadar gövde gizli tutulur (Türkçe metin bir an görünmesin).
(function() {
  var DIL = 'tr';
  try { DIL = localStorage.getItem('kt_dil') === 'en' ? 'en' : 'tr'; } catch (e) { /* depolama kapalı */ }
  var EN = DIL === 'en';
  var veri = window.KT_I18N || {};
  var SOZLUK = veri.sozluk || {};
  window.KT_DIL = DIL;
  window.KT_LOCALE = EN ? 'en-US' : 'tr-TR';
  window.ktT = function(tr, en) { return EN ? en : tr; };
  window.ktDilSec = function(d) {
    try { localStorage.setItem('kt_dil', d); } catch (e) { /* depolama kapalı */ }
    window.location.reload();
  };

  // <kt-cevir> (tests/test_i18n.py bu bloğu JS motorunda çalıştırır)
  var _re = null, _korRe = null, _bellek = {}, _sayi = 0;
  function _kacis(t) { return t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
  function _sade(t) { return t.replace(/\s+/g, ' ').trim(); }
  function cevir(s) {
    if (!EN || typeof s !== 'string' || !/[A-Za-zÇĞİÖŞÜçğıöşü]/.test(s)) return s;
    var m = /^(\s*)([\s\S]*?)(\s*)$/.exec(s);
    var on = m[1], oz = _sade(m[2]), son = m[3];
    if (Object.prototype.hasOwnProperty.call(_bellek, oz)) return _birlestir(on, oz, _bellek[oz], son);
    var out = SOZLUK[oz];
    if (out == null) {
      if (!_re) {
        var anahtar = Object.keys(SOZLUK).filter(function(k) { return k.trim(); })
          .sort(function(a, b) { return b.length - a.length; });
        _re = new RegExp(anahtar.map(function(k) {
          return (/^\p{L}/u.test(k) ? '(?<!\\p{L})' : '') + _kacis(k) + (/\p{L}$/u.test(k) ? '(?!\\p{L})' : '');
        }).join('|'), 'gu');
        var bankalar = (veri.bankalar || []).slice().sort(function(a, b) { return b.length - a.length; });
        _korRe = bankalar.length ? new RegExp(bankalar.map(_kacis).join('|'), 'g') : null;
      }
      var korunan = [];
      out = _korRe ? oz.replace(_korRe, function(x) { korunan.push(x); return '\uE000' + (korunan.length - 1) + '\uE001'; }) : oz;
      // "<X> Hariç Katılım Bankaları" → "Participation Banks excl. <X>"
      out = out.replace(/(\S+) Hariç (Katılım|Mevduat)( Bankaları)?/g, function(x, ad, seg, tam) {
        return (seg === 'Katılım' ? 'Participation' : 'Deposit') + (tam ? ' Banks' : '') + ' excl. ' + ad;
      });
      out = out.replace(_re, function(x) { return SOZLUK[x]; });
      out = out.replace(/\uE000(\d+)\uE001/g, function(x, i) { return korunan[+i]; });
      // Türkçede sayıdan sonra isim tekildir ("1 banka"); İngilizcede 1 için çoğul eki düşer.
      out = out.replace(/(^|[^\d.,])1 (bank|period|measure|group|page|row|item|file|user|card|cell|role)s\b/g,
                        function(x, o, ad) { return o + '1 ' + ad; });
      if (window.__ktEksik && /[ÇĞİÖŞÜçğıöşü]/.test(out)) window.__ktEksik[oz] = out;
    }
    if (_sayi < 20000) { _bellek[oz] = out; _sayi++; }
    return _birlestir(on, oz, out, son);
  }
  // Türkçe parça boşlukla başlayıp İngilizcesi noktalamayla başlıyorsa (" üzerinden başvurur." → ". They…")
  // öndeki boşluk atılır: "/signup ." yerine "/signup.".
  function _birlestir(on, oz, out, son) {
    var nokta = /^[.,;:!?)]/;
    return (nokta.test(out) && !nokta.test(oz) ? '' : on) + out + son;
  }
  // </kt-cevir>
  window.ktCevir = cevir;
  if (!EN) return;

  document.documentElement.lang = 'en';
  document.documentElement.classList.add('kt-ceviri');
  var stil = document.createElement('style');
  stil.textContent = 'html.kt-ceviri body { visibility: hidden; }';
  (document.head || document.documentElement).appendChild(stil);

  var OZNITELIK = ['placeholder', 'title', 'alt', 'aria-label'];
  var ATLA = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, NOSCRIPT: 1 };
  function atlanir(el) {
    for (; el && el.nodeType === 1; el = el.parentNode) {
      if (ATLA[el.tagName] || el.getAttribute('translate') === 'no') return true;
    }
    return false;
  }
  function metinCevir(n) {
    var v = n.nodeValue, c = cevir(v);
    if (c !== v) n.nodeValue = c;
  }
  function oznitelikCevir(el, ad) {
    var v = el.getAttribute(ad);
    if (v) { var c = cevir(v); if (c !== v) el.setAttribute(ad, c); }
  }
  function agacCevir(kok) {
    if (!kok) return;
    if (kok.nodeType === 3) { if (!atlanir(kok.parentNode)) metinCevir(kok); return; }
    if (kok.nodeType !== 1 || atlanir(kok)) return;
    var w = document.createTreeWalker(kok, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode: function(n) {
        if (n.nodeType === 1 && (ATLA[n.tagName] || n.getAttribute('translate') === 'no')) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var n = kok;
    do {
      if (n.nodeType === 3) metinCevir(n);
      else {
        for (var i = 0; i < OZNITELIK.length; i++) oznitelikCevir(n, OZNITELIK[i]);
        if (n.tagName === 'INPUT' && /^(button|submit|reset)$/i.test(n.type)) oznitelikCevir(n, 'value');
      }
    } while ((n = w.nextNode()));
  }
  new MutationObserver(function(kayitlar) {
    for (var i = 0; i < kayitlar.length; i++) {
      var k = kayitlar[i];
      if (k.type === 'childList') {
        for (var j = 0; j < k.addedNodes.length; j++) agacCevir(k.addedNodes[j]);
      } else if (k.type === 'characterData') {
        if (!atlanir(k.target.parentNode)) metinCevir(k.target);
      } else if (k.type === 'attributes' && !atlanir(k.target)) {
        oznitelikCevir(k.target, k.attributeName);
      }
    }
  }).observe(document.documentElement, {
    childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: OZNITELIK
  });

  function cokSatir(t) { return typeof t === 'string' ? t.split('\n').map(cevir).join('\n') : t; }
  var _alert = window.alert, _confirm = window.confirm, _prompt = window.prompt;
  window.alert = function(t) { return _alert.call(window, cokSatir(t)); };
  window.confirm = function(t) { return _confirm.call(window, cokSatir(t)); };
  window.prompt = function(t, v) { return _prompt.call(window, cokSatir(t), v); };

  function hazir() {
    document.title = cevir(document.title);
    agacCevir(document.body);
    document.documentElement.classList.remove('kt-ceviri');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', hazir);
  else hazir();
  // Güvenlik: bir hata olsa bile sayfa gizli kalmasın.
  setTimeout(function() { document.documentElement.classList.remove('kt-ceviri'); }, 2000);
})();
