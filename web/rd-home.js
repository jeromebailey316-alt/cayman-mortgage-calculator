/* The homepage panel: three modes behind one set of tabs.

   The tabs used to be links, so choosing Refinancing left the page before the
   visitor had entered anything. Each is now a real tab over its own inputs,
   and only "See full breakdown" navigates. What it carries with it depends on
   the mode: Buying already travels in the shared store, the other two append
   their fields to the query string and the target pages read them back.

   Arithmetic runs on core.js, so the figure here cannot disagree with the
   figure on the page the button leads to. */
(function (w, d) {
  'use strict';

  function el(id) { return d.getElementById(id); }
  function num(id, fb) { var v = CMC.readNum(id); return v === null ? fb : v; }

  var panel, tabs, thumb, pills, panes, mode = 'buy';

  /* ------------------------------------------------------------- the capsule */
  function placeThumb(animate) {
    if (!thumb || !tabs) return;
    var on = tabs.querySelector('.cmc-pill--active');
    if (!on) return;
    // getComputedStyle rather than a hardcoded inset: the pills' own padding is
    // a token and may change with the design system.
    var a = on.getBoundingClientRect(), b = tabs.getBoundingClientRect();
    if (!a.width) return;                       // hidden or not laid out yet
    if (!animate) thumb.style.transition = 'none';
    thumb.style.width = a.width + 'px';
    thumb.style.transform = 'translateX(' + (a.left - b.left) + 'px)';
    thumb.setAttribute('data-placed', '');
    if (!animate) {
      // force a reflow so the transition is only suppressed for this placement
      void thumb.offsetWidth;
      thumb.style.transition = '';
    }
  }

  /* ---------------------------------------------------------------- switching */
  function select(next, focus) {
    if (!next || next === mode) return;
    mode = next;
    pills.forEach(function (p) {
      var on = p.getAttribute('data-mode') === mode;
      p.classList.toggle('cmc-pill--active', on);
      p.setAttribute('aria-selected', on ? 'true' : 'false');
      p.setAttribute('tabindex', on ? '0' : '-1');
      if (on && focus) p.focus();
    });
    panes.forEach(function (pane) {
      pane.hidden = pane.getAttribute('data-pane') !== mode;
    });
    placeThumb(true);
    render();
  }

  // Left and right move between tabs, as a tablist is expected to.
  function onKey(ev) {
    var i = pills.indexOf(d.activeElement);
    if (i < 0) return;
    var j = ev.key === 'ArrowRight' ? i + 1
          : ev.key === 'ArrowLeft' ? i - 1
          : ev.key === 'Home' ? 0
          : ev.key === 'End' ? pills.length - 1 : -1;
    if (j < 0 && j !== 0) return;
    ev.preventDefault();
    j = (j + pills.length) % pills.length;
    select(pills[j].getAttribute('data-mode'), true);
  }

  /* ------------------------------------------------------------------ figures */
  function pane(m) { return panel.querySelector('[data-pane="' + m + '"]'); }

  function show(m, label, value, sub, href) {
    var p = pane(m);
    if (!p) return;
    p.querySelector('[data-cmc-result-label]').textContent = label;
    p.querySelector('[data-cmc-result]').textContent = value;
    p.querySelector('[data-cmc-result-sub]').textContent = sub;
    var cta = p.querySelector('.cmc-calc__cta');
    if (cta && href) cta.setAttribute('href', href);
  }

  function render() {
    if (!panel || !w.Core || !w.CMC) return;
    var V = CMC.inputs.get();
    var money = function (kyd) { return CMC.money(Math.round(kyd * V.fx), V.symbol); };

    if (mode === 'buy') {
      var loan = Math.max(0, V.price * (1 - V.deposit / 100));
      show('buy', 'Estimated monthly',
           money(Core.payment(loan, V.rate / 100, V.term * 12)),
           'on ' + money(loan) + ' over ' + V.term + ' yrs',
           '/calculator/');
      return;
    }

    if (mode === 'refi') {
      // display currency in, kyd out: the engine works in one currency only
      var bal = num('hBalance', 0) / V.fx;
      var cur = num('hCurRate', 0), nw = num('hNewRate', 0), yrs = num('hYears', 20);
      var now = Core.payment(bal, cur / 100, yrs * 12);
      var next = Core.payment(bal, nw / 100, yrs * 12);
      var diff = now - next;
      show('refi', 'New monthly payment', money(next),
           // never call a rise a saving
           (diff > 0.5 ? 'down from ' + money(now)
            : diff < -0.5 ? 'up from ' + money(now)
            : 'the same as now') + ', same ' + yrs + ' yrs left',
           // The equity page is the fuller picture of borrowing against a
           // property, so it is where the breakdown lives. Current rate has no
           // field there and is dropped rather than mapped onto something it
           // does not mean.
           '/equity/?bal=' + Math.round(bal) + '&rate=' + nw + '&years=' + yrs);
      return;
    }

    var income = num('hIncome', 0) / V.fx;
    var debts = num('hDebts', 0) / V.fx;
    var room = Math.max(0, income * 0.40 - debts);
    var afLoan = loanFor(room, V.rate / 100, V.term);
    var price = V.deposit >= 100 ? 0 : afLoan / (1 - V.deposit / 100);
    show('afford', 'The most you can buy', money(price),
         room > 0
           ? 'on ' + money(income) + ' a month, ' + V.term + ' yr term'
           : 'your other debts already use the whole 40% guideline',
         '/affordability/?income=' + Math.round(income) + '&debts=' + Math.round(debts));
  }

  // present value of a level payment; core.js has no inverse of payment()
  function loanFor(pmt, rate, years) {
    var r = rate / 12, n = Math.max(1, Math.round(years * 12));
    return r ? pmt * (1 - Math.pow(1 + r, -n)) / r : pmt * n;
  }

  /* -------------------------------------------------------------------- start */
  function start() {
    panel = d.querySelector('[data-cmc-panel]');
    if (!panel) return;
    tabs = panel.querySelector('.cmc-calc__tabs');
    thumb = panel.querySelector('[data-cmc-thumb]');
    pills = [].slice.call(panel.querySelectorAll('.cmc-pill'));
    panes = [].slice.call(panel.querySelectorAll('[data-pane]'));

    pills.forEach(function (p) {
      p.addEventListener('click', function () { select(p.getAttribute('data-mode')); });
    });
    if (tabs) tabs.addEventListener('keydown', onKey);

    ['hBalance', 'hCurRate', 'hNewRate', 'hYears', 'hIncome', 'hDebts'].forEach(function (id) {
      var e = el(id);
      if (!e) return;
      e.addEventListener('input', render);
      e.addEventListener('change', render);
    });

    CMC.inputs.subscribe(render);
    // the fonts settle after first paint and the pills change width with them
    placeThumb(false);
    if (d.fonts && d.fonts.ready) d.fonts.ready.then(function () { placeThumb(false); });
    w.addEventListener('resize', function () { placeThumb(false); });
    render();
  }

  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', start);
  else start();
})(window, document);
