/* Shared inputs: price, deposit, rate, term and currency, entered once and used
   everywhere (HANDOFF 5.1).

   A faithful port of CMC.inputs from the reference bundle, minus React: same
   storage key, same defaults, same get/set/subscribe/reset, same cross-tab sync.
   All maths stays in CI$; currency only converts what is displayed and entered,
   at the fixed peg.

   Panels on the page register themselves with CMC.bindPanel, so every control
   bound to the same field stays in step without each page writing its own glue. */
(function (w) {
  'use strict';

  var KEY = 'cmc.inputs';
  // rate: KYD prime 7.00% + 0.75, see the rate hint on the calculator page
  var DEFAULTS = { price: 650000, deposit: 10, rate: 7.75, term: 25, currency: 'KYD' };
  var USD_PER_KYD = 1.20;   // fixed peg: CI$1 = US$1.20

  function norm(k, v) { return k === 'currency' ? (v === 'USD' ? 'USD' : 'KYD') : Number(v); }
  function valid(k, v) {
    return k === 'currency' ? (v === 'USD' || v === 'KYD') : (v != null && v !== '' && !isNaN(Number(v)));
  }
  function read() {
    try { var raw = w.localStorage.getItem(KEY); return raw ? JSON.parse(raw) : {}; }
    catch (e) { return {}; }
  }

  var mem = read();
  var listeners = [];

  var inputs = {
    key: KEY,
    defaults: DEFAULTS,
    usdPerKyd: USD_PER_KYD,
    get: function (fallback) {
      var o = {}, k;
      for (k in DEFAULTS) o[k] = DEFAULTS[k];
      if (fallback) for (k in fallback) if (valid(k, fallback[k])) o[k] = norm(k, fallback[k]);
      for (k in mem) if (valid(k, mem[k])) o[k] = norm(k, mem[k]);
      o.fx = o.currency === 'USD' ? USD_PER_KYD : 1;
      o.symbol = o.currency === 'USD' ? 'US$' : 'CI$';
      return o;
    },
    set: function (partial) {
      var changed = false, k;
      for (k in partial) {
        if (!(k in DEFAULTS) || !valid(k, partial[k])) continue;
        if (mem[k] === norm(k, partial[k])) continue;
        mem[k] = norm(k, partial[k]); changed = true;
      }
      if (!changed) return;
      try { w.localStorage.setItem(KEY, JSON.stringify(mem)); } catch (e) {}
      notify();
    },
    reset: function () {
      mem = {};
      try { w.localStorage.removeItem(KEY); } catch (e) {}
      notify();
    },
    subscribe: function (fn) {
      listeners.push(fn);
      return function () { var i = listeners.indexOf(fn); if (i >= 0) listeners.splice(i, 1); };
    }
  };

  function notify() {
    var v = inputs.get();
    for (var i = 0; i < listeners.length; i++) { try { listeners[i](v); } catch (e) {} }
  }

  try {
    w.addEventListener('storage', function (e) {
      if (e.key !== KEY) return;
      mem = read(); notify();
    });
  } catch (e) {}

  /* ---- money, matching fmtMoney in the bundle ---- */
  function money(n, symbol) {
    var s = symbol || 'CI$';
    var r = Math.round(Number(n) || 0);
    return (r < 0 ? '-' : '') + s + Math.abs(r).toLocaleString('en-US');
  }

  /* ---- the amortising payment, the one formula the whole site uses ---- */
  function payment(principal, annualRate, years) {
    var r = (Number(annualRate) || 0) / 100 / 12;
    var n = Math.max(1, Math.round((Number(years) || 0) * 12));
    if (!r) return principal / n;
    return principal * r / (1 - Math.pow(1 + r, -n));
  }

  /* ---- bind every [data-cmc-bind] control on the page to the shared store ----
     A control's value is in display currency; price converts, the rest do not. */
  function bindAll(root) {
    var els = [].slice.call((root || document).querySelectorAll('[data-cmc-bind]'));
    if (!els.length) return;

    function write(v) {
      els.forEach(function (el) {
        var k = el.getAttribute('data-cmc-bind');
        if (document.activeElement === el) return;   // never fight the person typing
        if (k === 'price') {
          el.value = el.hasAttribute('data-cmc-money')
            ? groupMoney(v.price * v.fx) : Math.round(v.price * v.fx);
        }
        else if (k === 'currency') el.value = v.currency;
        else if (k in v) el.value = v[k];
      });
    }

    els.forEach(function (el) {
      var k = el.getAttribute('data-cmc-bind');
      el.addEventListener('input', function () {
        var v = inputs.get(), o = {};
        if (k === 'currency') { o.currency = el.value; }
        else {
          var n = el.hasAttribute('data-cmc-money') ? parseMoney(el.value) : parseFloat(el.value);
          if (n == null || isNaN(n)) return;
          o[k] = k === 'price' ? n / v.fx : n;
        }
        inputs.set(o);
      });
      if (el.tagName === 'SELECT') el.addEventListener('change', function () { el.dispatchEvent(new Event('input')); });
    });

    inputs.subscribe(write);
    write(inputs.get());
  }

  /* ---- money fields: grouped while reading, plain while typing ---- */
  function parseMoney(v) {
    var n = parseFloat(String(v).replace(/[^0-9.-]/g, ''));
    return isNaN(n) ? null : n;
  }
  /* Read a numeric field, whatever kind it is.

     A money field carries thousands separators once it loses focus, so
     parseFloat alone turns "650,000" into 650. Every caller that remembered to
     strip them was correct and every caller that forgot was silently wrong by a
     factor of a thousand: the affordability page read CI$9,000 a month as CI$9
     and answered CI$0, equity turned CI$240,000 of headroom into CI$240, and
     the listings minimum price quietly reset on the next re-sort.

     So the decision is taken from the element's own attribute rather than from
     the caller's memory of which fields are money. Returns null for empty or
     unparseable, never NaN. */
  function readNum(ref) {
    var el = typeof ref === 'string' ? document.getElementById(ref) : ref;
    if (!el || el.value === '' || el.value == null) return null;
    var n = el.hasAttribute('data-cmc-money') ? parseMoney(el.value) : parseFloat(el.value);
    return (n === null || isNaN(n)) ? null : n;
  }

  function groupMoney(n) {
    return Math.round(n).toLocaleString('en-US');
  }
  function bindMoney(root) {
    [].slice.call((root || document).querySelectorAll('[data-cmc-money]')).forEach(function (el) {
      el.addEventListener('focus', function () {
        var n = parseMoney(el.value);
        if (n != null) el.value = String(Math.round(n));   // plain digits to edit
      });
      el.addEventListener('blur', function () {
        var n = parseMoney(el.value);
        el.value = n == null ? '' : groupMoney(n);
      });
      // format whatever the field was rendered with
      var n = parseMoney(el.value);
      if (n != null) el.value = groupMoney(n);
    });
  }

  /* ---- "Use in calculator" on a listing tile ----
     Sets the shared price and hands the island and property type to the
     calculator in the URL, because duty depends on both: a Cayman Brac lot
     priced as a Grand Cayman house would be wrong by thousands.

     The control sits inside the card's link to the agent's site, as the
     favourite and compare chips already do, so the click must be stopped from
     reaching it. Bound per button rather than delegated: a delegated handler
     that misses once sends the visitor off to the agency instead. */
  function bindUseInCalculator(root) {
    [].slice.call((root || document).querySelectorAll('.rd-use-calc')).forEach(function (b) {
      if (b.dataset.rdBound) return;
      b.dataset.rdBound = '1';
      b.addEventListener('click', function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var price = parseFloat(b.getAttribute('data-use-price'));
        if (!isNaN(price) && price > 0) inputs.set({ price: price });
        var q = [];
        var island = b.getAttribute('data-use-island');
        var ptype = b.getAttribute('data-use-ptype');
        if (island) q.push('island=' + encodeURIComponent(island));
        if (ptype) q.push('ptype=' + encodeURIComponent(ptype));
        w.location.assign('/calculator/' + (q.length ? '?' + q.join('&') : ''));
      });
    });
  }

  /* ---- the CI$ / US$ toggle ---- */
  function bindCurrency(root) {
    var btns = [].slice.call((root || document).querySelectorAll('[data-cmc-currency]'));
    if (!btns.length) return;
    btns.forEach(function (b) {
      b.addEventListener('click', function () {
        inputs.set({ currency: b.getAttribute('data-cmc-currency') });
      });
    });
    function paint(v) {
      btns.forEach(function (b) {
        var on = b.getAttribute('data-cmc-currency') === v.currency;
        b.classList.toggle('cmc-pill--active', on);
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
    }
    inputs.subscribe(paint);
    paint(inputs.get());
  }

  /* ---- the homepage/compact panel: recompute its result from the store ---- */
  function bindPanel(panel) {
    if (!panel) return;
    var out = panel.querySelector('[data-cmc-result]');
    var sub = panel.querySelector('[data-cmc-result-sub]');
    function render(v) {
      var loan = v.price * (1 - v.deposit / 100);
      var m = payment(loan, v.rate, v.term) * v.fx;
      if (out) out.textContent = money(Math.round(m), v.symbol);
      if (sub) sub.textContent = 'on ' + money(Math.round(loan * v.fx), v.symbol) + ' over ' + v.term + ' yrs';
    }
    inputs.subscribe(render);
    render(inputs.get());
  }

  w.CMC = w.CMC || {};
  w.CMC.inputs = inputs;
  w.CMC.money = money;
  w.CMC.payment = payment;
  w.CMC.bindAll = bindAll;
  w.CMC.bindCurrency = bindCurrency;
  w.CMC.parseMoney = parseMoney;
  w.CMC.readNum = readNum;
  w.CMC.bindUseInCalculator = bindUseInCalculator;
  w.CMC.bindPanel = bindPanel;

  function start() {
    bindAll(document);
    bindCurrency(document);
    bindMoney(document);
    bindUseInCalculator(document);
    [].slice.call(document.querySelectorAll('.cmc-calc')).forEach(bindPanel);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})(window);
