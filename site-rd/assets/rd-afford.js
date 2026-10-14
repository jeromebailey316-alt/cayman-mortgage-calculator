/* Affordability and equity.

   Both run on core.js. The cash limit uses Core.maxPrice, which walks the duty
   thresholds explicitly rather than trusting a bisection to land the right side
   of a cliff: duty steps at CI$550,000, 650,000 and CI$2,000,000 among others,
   so a plain binary search can report a price that costs thousands more than
   the answer above it. */
(function (w, d) {
  'use strict';

  function el(id) { return d.getElementById(id); }
  function n(id, fb) { var e = el(id); if (!e) return fb; var v = parseFloat(e.value); return isNaN(v) ? fb : v; }
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
  }

  function start() {
    ['aIncome', 'aDebts', 'aCeiling', 'aCash', 'aStatus'].forEach(function (id) {
      var e = el(id); if (!e) return;
      e.addEventListener('input', renderAfford);
      e.addEventListener('change', renderAfford);
    });
    ['eValue', 'eBalance', 'eOther', 'eLtv'].forEach(function (id) {
      var e = el(id); if (!e) return;
      e.addEventListener('input', renderEquity);
    });
    [el('rdAfford'), el('rdEquity')].forEach(function (f) {
      if (f) f.addEventListener('submit', function (ev) { ev.preventDefault(); });
    });
    CMC.inputs.subscribe(function () { renderAfford(); renderEquity(); });
    renderAfford(); renderEquity();
  }

  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', start);
  else start();
})(window, document);
