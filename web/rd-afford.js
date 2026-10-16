/* Affordability and equity.

   Both run on core.js. The cash limit uses Core.maxPrice, which walks the duty
   thresholds explicitly rather than trusting a bisection to land the right side
   of a cliff: duty steps at CI$550,000, 650,000 and CI$2,000,000 among others,
   so a plain binary search can report a price that costs thousands more than
   the answer above it. */
(function (w, d) {
  'use strict';

  function el(id) { return d.getElementById(id); }
  // see CMC.readNum: the income and cash boxes are money fields, and reading
  // them with a bare parseFloat is what made this page answer CI$0
  function n(id, fb) { var v = CMC.readNum(id); return v === null ? fb : v; }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* ------------------------------------------------------------ affordability */
  function renderAfford() {
    if (!el('rdAfford') || !w.Core) return;
    var V = CMC.inputs.get();
    var money = function (kyd) { return CMC.money(Math.round(kyd * V.fx), V.symbol); };

    var income = n('aIncome', 0) / V.fx;
    var debts = n('aDebts', 0) / V.fx;
    var ceiling = n('aCeiling', 40);
    var cash = n('aCash', 0) / V.fx;
    var status = el('aStatus').value;

    // 1. what the income will carry
    var room = Math.max(0, income * ceiling / 100 - debts);
    var r = V.rate / 100 / 12, months = Math.max(1, Math.round(V.term * 12));
    var loanFromIncome = r ? room * (1 - Math.pow(1 + r, -months)) / r : room * months;
    var priceFromIncome = V.deposit >= 100 ? 0 : loanFromIncome / (1 - V.deposit / 100);

    // 2. what the cash will cover, duty thresholds and all
    var settings = {
      downPct: V.deposit, rate: V.rate / 100, term: V.term,
      ptype: 'home', status: status, joint: false,
      legalPct: 1, bankPct: 1, valuation: 600, inspection: 0
    };
    var priceFromCash = Core.maxPrice(function (p) { return p.cashToClose <= cash; }, settings);

    var binding = priceFromCash < priceFromIncome ? 'cash' : 'income';
    var answer = Math.min(priceFromIncome, priceFromCash);

    el('aVerdictLabel').textContent = 'The most you can buy';
    el('aMax').textContent = money(answer);
    el('aVerdictNote').textContent = binding === 'cash'
      ? 'Your cash is the binding limit. Your income would carry ' + money(priceFromIncome) +
        ', but the deposit, duty and fees at that price come to more than you have.'
      : 'Your income is the binding limit. Your cash would stretch to ' + money(priceFromCash) +
        ', but the monthly payment at that price is above your ceiling.';

    el('aTable').innerHTML =
      '<thead><tr><th>Limit</th><th>Price</th><th>What sets it</th></tr></thead><tbody>' +
      '<tr><th>Income</th><td class="' + (binding === 'income' ? 'rd-best' : '') + '">' +
        esc(money(priceFromIncome)) + '</td><td>' + ceiling + '% of ' + esc(money(income)) +
        ' a month, less ' + esc(money(debts)) + ' of other debt</td></tr>' +
      '<tr><th>Cash</th><td class="' + (binding === 'cash' ? 'rd-best' : '') + '">' +
        esc(money(priceFromCash)) + '</td><td>' + esc(money(cash)) +
        ' covering the deposit, stamp duty, legal, bank and valuation fees</td></tr>' +
      '</tbody>';

    var run = el('aRun');
    if (run) run.onclick = function () {
      CMC.inputs.set({ price: Math.round(answer) });
      w.location.assign('/calculator/');
    };
  }

  /* ------------------------------------------------------------------ equity */
  function renderEquity() {
    if (!el('rdEquity')) return;
    var V = CMC.inputs.get();
    var money = function (kyd) { return CMC.money(Math.round(kyd * V.fx), V.symbol); };

    var value = n('eValue', 0) / V.fx;
    var balance = n('eBalance', 0) / V.fx;
    var other = n('eOther', 0) / V.fx;
    var ltv = n('eLtv', 80);

    var secured = balance + other;
    var equity = value - secured;
    var ceiling = value * ltv / 100;
    var available = Math.max(0, ceiling - secured);

    el('eLabel').textContent = 'You could release about';
    el('eAvailable').textContent = money(available);
    el('eNote').textContent = available > 0
      ? 'Your equity is ' + money(equity) + '. A lender at ' + ltv +
        '% loan to value would advance up to ' + money(ceiling) + ' in total against the property.'
      : 'At ' + ltv + '% loan to value there is nothing available: what is already secured ' +
        'against the property is at or above the ceiling.';

    el('eTable').innerHTML = '<tbody>' +
      '<tr><th>What it is worth</th><td>' + esc(money(value)) + '</td></tr>' +
      '<tr><th>Mortgage balance</th><td>' + esc(money(-balance)) + '</td></tr>' +
      '<tr><th>Other secured loans</th><td>' + esc(money(-other)) + '</td></tr>' +
      '<tr><th>Your equity</th><td><strong>' + esc(money(equity)) + '</strong></td></tr>' +
      '<tr><th>Lender ceiling at ' + ltv + '%</th><td>' + esc(money(ceiling)) + '</td></tr>' +
      '<tr><th>Available to release</th><td><strong>' + esc(money(available)) +
        '</strong></td></tr></tbody>';

    renderRelease(V, money, { value: value, balance: balance, other: other,
                              secured: secured, available: available, ltv: ltv });
  }

  /* What taking the money actually costs.

     The headroom figure above answers "how much could I", which is where the
     page used to stop. The decision needs three more things: what it costs a
     month, what it costs in total, and the Cayman stamp duty on the larger
     charge, which has a cliff at CI$300,000 that nothing on the page warned
     about. Crossing it lifts the whole sum secured to 1.5% and re-stamps the
     existing charge, so CI$5,000 more borrowed can cost CI$1,575 more in duty. */
  function renderRelease(V, money, q) {
    var wrap = el('eCostWrap');
    if (!wrap || !w.Core) return;

    var release = n('eRelease', 0) / V.fx;
    var rate = n('eRate', 0);
    var years = n('eTerm', 15);

    if (!(release > 0)) {
      wrap.hidden = true;
      return;
    }
    wrap.hidden = false;

    var am = Core.amortise({ loan: release, rate: rate / 100, years: years });
    // duty follows the total secured against the property, not just the new money
    var duty = Core.furtherChargeDuty(q.secured, release);
    var newSecured = q.secured + release;
    var newLtv = q.value > 0 ? newSecured / q.value * 100 : 0;
    var over = release - q.available;

    el('eCostTitle').textContent = 'What releasing ' + money(release) + ' costs';

    // Short labels and one figure per row: the results column is 341px on a
    // desktop two-column layout, and a longer label pushed the amounts, which
    // are the whole point, off the right edge into a scroll.
    rows(el('eCostTable'), '',
      '<tr><th>Monthly payment</th><td><strong>' +
        esc(money(am.pmt)) + '</strong></td></tr>' +
      '<tr><th>Interest over ' + years + ' years</th><td>' +
        esc(money(am.totalInterest)) + '</td></tr>' +
      '<tr><th>Stamp duty on the charge</th><td>' +
        esc(money(duty.amount)) + '</td></tr>' +
      '<tr><th>Total cost</th><td>' +
        esc(money(release + am.totalInterest + duty.amount)) + '</td></tr>' +
      '<tr><th>Secured after</th><td>' + esc(money(newSecured)) + '</td></tr>' +
      '<tr><th>Loan to value after</th><td>' + newLtv.toFixed(0) + '%</td></tr>');

    // the cliff, and the over-ceiling warning, share one line
    var cliff = el('eCliff');
    if (over > 0.5) {
      cliff.hidden = false;
      cliff.textContent = 'This is ' + money(over) + ' more than the ' + q.ltv +
        '% ceiling allows, so a lender would not advance all of it on these figures.';
    } else if (duty.upstamped > 0) {
      cliff.hidden = false;
      cliff.textContent = 'Crossing CI$300,000 of total secured debt puts the whole charge at ' +
        '1.5% rather than 1%, and the existing ' + money(duty.upstamped) +
        // the threshold is inclusive: at exactly CI$300,000 the rate is still 1%
        ' is re-stamped at the higher rate. Releasing ' +
        money(Math.max(0, 300000 - q.secured)) + ' or less would stay at 1%.';
    } else {
      cliff.hidden = true;
    }

    // the 40% guideline, but only when both halves are known
    var pay = n('ePayment', 0) / V.fx, income = n('eIncome', 0) / V.fx;
    var note = el('eAffordNote');
    if (income > 0 && pay > 0) {
      var share = (pay + am.pmt) / income * 100;
      note.hidden = false;
      note.textContent = 'Your payments would come to ' + money(pay + am.pmt) + ' a month, ' +
        share.toFixed(0) + '% of your gross income. ' +
        (share <= 40
          ? 'That sits inside the 40% total debt service guideline most Cayman lenders apply.'
          : 'That is above the 40% total debt service guideline most Cayman lenders apply.');
    } else {
      note.hidden = true;
    }
  }

  function rows(table, head, body) {
    table.innerHTML = (head ? '<thead><tr>' + head + '</tr></thead>' : '') +
      '<tbody>' + body + '</tbody>';
  }

  function start() {
    ['aIncome', 'aDebts', 'aCeiling', 'aCash', 'aStatus'].forEach(function (id) {
      var e = el(id); if (!e) return;
      e.addEventListener('input', renderAfford);
      e.addEventListener('change', renderAfford);
    });
    ['eValue', 'eBalance', 'eOther', 'eLtv', 'eRelease', 'eRate', 'eTerm',
     'ePayment', 'eIncome'].forEach(function (id) {
      var e = el(id); if (!e) return;
      e.addEventListener('input', renderEquity);
      if (e.tagName === 'SELECT') e.addEventListener('change', renderEquity);
    });
    [el('rdAfford'), el('rdEquity')].forEach(function (f) {
      if (f) f.addEventListener('submit', function (ev) { ev.preventDefault(); });
    });
    // carried from the homepage panel
    var q = new URLSearchParams(location.search);

    /* The Refinancing tab lands here, since borrowing against a property is
       what this page works out. Its balance and new rate map onto these
       fields directly; "years left" becomes the term, snapped to an option
       the select actually offers rather than silently ignored. */
    var bal = q.get('bal'), rate = q.get('rate'), years = q.get('years');
    if (bal != null && !isNaN(Number(bal)) && el('eBalance')) {
      el('eBalance').value = Math.round(Number(bal)).toLocaleString('en-US');
    }
    if (rate != null && !isNaN(Number(rate)) && el('eRate')) {
      el('eRate').value = Number(rate);
    }
    if (years != null && !isNaN(Number(years)) && el('eTerm')) {
      var want = Number(years), best = null, gap = Infinity;
      [].slice.call(el('eTerm').options).forEach(function (o) {
        var dgap = Math.abs(Number(o.value) - want);
        if (dgap < gap) { gap = dgap; best = o.value; }
      });
      if (best !== null) el('eTerm').value = best;
    }

    [['income', 'aIncome'], ['debts', 'aDebts']].forEach(function (pair) {
      var v = q.get(pair[0]), e = el(pair[1]);
      if (v == null || v === '' || isNaN(Number(v)) || !e) return;
      e.value = e.hasAttribute('data-cmc-money')
        ? Math.round(Number(v)).toLocaleString('en-US') : v;
    });

    CMC.inputs.subscribe(function () { renderAfford(); renderEquity(); });
    renderAfford(); renderEquity();
  }

  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', start);
  else start();
})(window, document);
