/* A guided walkthrough of the mortgage calculator.

   Design decisions worth knowing before changing this:

   It never writes to an input. Every step points at something already on the
   page and explains it, so a visitor who is halfway through their own sums can
   open it without losing anything. The one place the reader's answer matters,
   which kind of buyer they are, only chooses which words step 3 uses: it is
   still the visitor who picks the stamp duty status.

   The step card is fixed to the bottom of the viewport rather than floated
   beside whatever it describes. A tooltip that points at an element has to
   solve collisions, flipping and clamping at every width, and gets it wrong on
   a phone. A fixed card never does, the anchor is scrolled into the upper part
   of the screen instead, and the figures stay visible the whole way through,
   which on a calculator is the point.

   There is no dimming backdrop for the same reason: the page stays readable
   and usable while the walkthrough is open. */
(function (w, d) {
  'use strict';

  var SEEN_KEY = 'cmc.walkthrough.seen';
  var GUIDE = '/guides/stamp-duty/';

  /* Each step names a selector already in the page. If a selector ever stops
     matching, that step is skipped rather than the walkthrough breaking. */
  var STEPS = [
    {
      id: 'intro',
      anchor: 'h1',
      title: 'What this page works out',
      body: 'Enter what you want to buy and it shows your monthly payment, the ' +
            'cash you need on the day, and the stamp duty. Every figure is an ' +
            'estimate. First, which describes you?',
      fork: true
    },
    {
      id: 'property',
      anchor: '[aria-label="Property"]',
      title: 'Start with the property',
      body: 'Put in the asking price. The island matters: Cayman Brac has its ' +
            'own stamp duty rates, so choosing it changes what you owe. Raw ' +
            'land is taxed differently from a house or condo.'
    },
    {
      id: 'status',
      anchor: '#cStatus',
      title: 'This is the field to get right',
      body: {
        caymanian: 'Choose "Caymanian, first property". Caymanians buying their ' +
                   'first home pay nothing below a threshold and a reduced rate ' +
                   'above it, which can be tens of thousands less.',
        other: 'Leave this on "Standard rate, 7.5%". The reduced rates are for ' +
               'Caymanians buying a first or second property. Picking one you ' +
               'are not entitled to will understate your costs badly.'
      }
    },
    {
      id: 'mortgage',
      anchor: '[aria-label="Mortgage"]',
      title: 'Your deposit, rate and term',
      body: 'The deposit is a percentage of the price, not an amount. The rate ' +
            'starts at KYD prime plus 0.75%, which is a common Cayman rate, but ' +
            'your bank will quote its own. A longer term lowers the payment and ' +
            'raises the total interest.'
    },
    {
      id: 'payment',
      anchor: '#rMonthly',
      title: 'The first figure: the loan repayment',
      body: 'This is what goes to the bank each month for the mortgage alone. ' +
            'It is not the full cost of living in the place, which is the next ' +
            'figure down.'
    },
    {
      id: 'owning',
      anchor: '[aria-label="Monthly cost of owning"]',
      title: 'The second figure: what it really costs',
      body: 'The repayment plus insurance, upkeep and strata. Where a line says ' +
            '"Not entered" the figure is missing, not zero, so the total is a ' +
            'floor. Enter your strata fee to make it real.'
    },
    {
      id: 'cash',
      anchor: '[aria-label="Cash you need at closing"]',
      title: 'The money you need on the day',
      body: 'A separate lump sum from the monthly payment: your deposit, stamp ' +
            'duty, legal and bank fees. This is the figure that surprises ' +
            'people, so budget for it before you make an offer.'
    },
    {
      id: 'duty',
      anchor: '[aria-label="Stamp duty"]',
      title: 'Stamp duty',
      body: 'A one off government tax on the purchase, due within 45 days of ' +
            'signing. The line underneath says which rule produced your figure. ' +
            'The <a href="' + GUIDE + '">stamp duty guide</a> explains the bands.'
    },
    {
      id: 'next',
      anchor: '[aria-label="Summary"]',
      title: 'Taking it with you',
      body: 'Download the full schedule, save a PDF, or print it for the bank. ' +
            'Your figures follow you to the other calculators on this site, so ' +
            'you only type them once.'
    }
  ];

  var idx = 0, who = 'other', open = false, card, live, prevFocus, steps;

  /* ------------------------------------------------------------- utilities */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function seen() {
    try { return w.localStorage.getItem(SEEN_KEY) === '1'; } catch (e) { return true; }
  }
  function markSeen() {
    try { w.localStorage.setItem(SEEN_KEY, '1'); } catch (e) { /* private mode: no memory, no harm */ }
  }
  function track(name, extra) {
    if (typeof w.gtag !== 'function') return;
    var o = { event_category: 'walkthrough' };
    if (extra) for (var k in extra) if (extra.hasOwnProperty(k)) o[k] = extra[k];
    try { w.gtag('event', name, o); } catch (e) { /* never let analytics break the tour */ }
  }

  // steps whose anchor is actually on the page, resolved once at open
  function usable() {
    return STEPS.filter(function (s) { return d.querySelector(s.anchor); });
  }

  function bodyFor(s) {
    return typeof s.body === 'string' ? s.body : (s.body[who] || s.body.other);
  }

  /* ------------------------------------------------------------ highlights */
  function clearMarks() {
    [].slice.call(d.querySelectorAll('.rd-wt-on')).forEach(function (el) {
      el.classList.remove('rd-wt-on');
    });
  }
  function mark(sel) {
    clearMarks();
    var el = d.querySelector(sel);
    if (!el) return null;
    // a bare field control reads better with its label ringed too
    var target = el.closest ? (el.closest('label.cmc-field') || el) : el;
    target.classList.add('rd-wt-on');
    return target;
  }

  /* --------------------------------------------------------------- the card */
  function build() {
    card = d.createElement('div');
    card.className = 'rd-wt';
    card.setAttribute('role', 'dialog');
    card.setAttribute('aria-label', 'How to use this calculator');
    card.setAttribute('tabindex', '-1');
    card.hidden = true;
    card.innerHTML =
      '<div class="rd-wt__inner">' +
        '<div class="rd-wt__head">' +
          '<span class="rd-wt__count" data-wt-count></span>' +
          '<button type="button" class="rd-wt__x" data-wt-exit ' +
            'aria-label="Close the walkthrough">Close</button>' +
        '</div>' +
        '<div data-wt-live aria-live="polite">' +
          '<h2 class="rd-wt__title" data-wt-title></h2>' +
          '<p class="rd-wt__body" data-wt-body></p>' +
          '<div class="rd-wt__fork" data-wt-fork hidden>' +
            '<button type="button" class="cmc-btn cmc-btn--secondary cmc-btn--sm" ' +
              'data-wt-who="caymanian">A Caymanian buying a first home</button>' +
            '<button type="button" class="cmc-btn cmc-btn--secondary cmc-btn--sm" ' +
              'data-wt-who="other">Everyone else</button>' +
          '</div>' +
        '</div>' +
        '<div class="rd-wt__nav">' +
          '<button type="button" class="cmc-btn cmc-btn--ghost cmc-btn--sm" data-wt-back>Back</button>' +
          '<button type="button" class="cmc-btn cmc-btn--primary cmc-btn--sm" data-wt-next>Next</button>' +
        '</div>' +
      '</div>';
    d.body.appendChild(card);

    card.addEventListener('click', function (ev) {
      var t = ev.target.closest ? ev.target.closest('[data-wt-who],[data-wt-next],[data-wt-back],[data-wt-exit]') : null;
      if (!t) return;
      if (t.hasAttribute('data-wt-who')) {
        who = t.getAttribute('data-wt-who');
        track('walkthrough_audience', { audience: who });
        go(idx + 1);
      } else if (t.hasAttribute('data-wt-next')) {
        if (idx >= steps.length - 1) finish(); else go(idx + 1);
      } else if (t.hasAttribute('data-wt-back')) {
        go(idx - 1);
      } else {
        quit('close');
      }
    });

    d.addEventListener('keydown', function (ev) {
      if (!open) return;
      if (ev.key === 'Escape') { ev.preventDefault(); quit('escape'); }
      else if (ev.key === 'ArrowRight') { ev.preventDefault(); if (idx < steps.length - 1) go(idx + 1); }
      else if (ev.key === 'ArrowLeft') { ev.preventDefault(); go(idx - 1); }
    });
  }

  /* ------------------------------------------------------------- the moves */
  function go(n) {
    if (n < 0) return;
    if (n >= steps.length) return finish();
    idx = n;
    var s = steps[idx];

    card.querySelector('[data-wt-count]').textContent = 'Step ' + (idx + 1) + ' of ' + steps.length;
    card.querySelector('[data-wt-title]').textContent = s.title;
    // only the duty step carries a link, and it is ours, not user input
    card.querySelector('[data-wt-body]').innerHTML = bodyFor(s);

    var fork = card.querySelector('[data-wt-fork]');
    fork.hidden = !s.fork;
    card.querySelector('[data-wt-next]').hidden = !!s.fork;
    card.querySelector('[data-wt-next]').textContent =
      idx === steps.length - 1 ? 'Done' : 'Next';
    card.querySelector('[data-wt-back]').disabled = idx === 0;

    var el = mark(s.anchor);
    if (el) {
      /* Instant, not smooth. Smooth scrolling is silently a no-op in some
         browsers and under reduced-motion settings, and when it does nothing
         the step rings a field that is hundreds of pixels off screen, which is
         worse than no animation. Found by measuring, not by reading. */
      var top = el.getBoundingClientRect().top + w.pageYOffset - Math.round(w.innerHeight * 0.22);
      w.scrollTo(0, Math.max(0, top));
    }
    // focusing must not fight the scroll we just made
    try { card.focus({ preventScroll: true }); } catch (e) { card.focus(); }
    track('walkthrough_step', { step_index: idx + 1, step_id: s.id });
  }

  function start(auto) {
    steps = usable();
    if (!steps.length) return;
    idx = 0; open = true;
    card.hidden = false;
    d.body.classList.add('rd-wt-open');
    prevFocus = d.activeElement;
    markSeen();
    track('walkthrough_start', { trigger: auto ? 'auto' : 'button' });
    go(0);
  }

  function close() {
    open = false;
    card.hidden = true;
    d.body.classList.remove('rd-wt-open');
    clearMarks();
    if (prevFocus && prevFocus.focus) prevFocus.focus();
  }
  function quit(how) {
    track('walkthrough_exit', { step_index: idx + 1, step_id: steps[idx] && steps[idx].id, how: how });
    close();
  }
  function finish() {
    track('walkthrough_finish', { steps: steps.length });
    close();
  }

  /* -------------------------------------------------------------------- go */
  function init() {
    var btn = d.getElementById('rdWalkBtn');
    if (!btn || !d.getElementById('rdCalc')) return;
    build();
    btn.addEventListener('click', function () { start(false); });
    // once, ever, and only when the visitor has not already started typing
    if (!seen()) w.setTimeout(function () { if (!open) start(true); }, 1200);
  }

  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', init);
  else init();
})(window, document);
