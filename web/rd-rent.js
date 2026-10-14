/* Rent vs buy: the year buying pulls ahead.

   Both sides are compared on the same question, which is what you are left
   with after N years rather than what you paid. Buying wins when the equity
   released by selling exceeds everything the purchase cost you, against what
   renting cost over the same period. Nothing here assumes the difference is
   invested: that turns the answer into a guess about markets. */
(function (w, d) {
  'use strict';
  function el(id) { return d.getElementById(id); }
  function n(id, fb) { var e = el(id); if (!e) return fb; var v = parseFloat(e.value); return isNaN(v) ? fb : v; }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* What each path leaves you with after `yrs` years, in CI$. */
  function outcome(yrs, v, o) {
    var months = yrs * 12;

    // renting: rent paid, rising each year; the deposit stays in your pocket
    var rentPaid = 0, rent = o.rent;
    for (var y = 0; y < yrs; y++) {
      rentPaid += rent * 12;
      rent *= 1 + o.rentRise / 100;
    }

    // buying: deposit and closing costs on day one, then the payment and the
    // running costs, against the equity you walk away with
    var am = Core.amortise({ loan: o.loan, rate: v.rate / 100, years: v.term });
    var paidMonths = Math.min(months, am.rows.length);
    var mortgagePaid = 0, i;
    // core.js uses short keys on its schedule rows: pay, i, p, bal
    for (i = 0; i < paidMonths; i++) mortgagePaid += am.rows[i].pay;
    var balance = paidMonths ? am.rows[paidMonths - 1].bal : o.loan;

    var running = (o.price * 0.01 + o.price * 0.01) / 12 * months;   // insurance and upkeep
    var value = o.price * Math.pow(1 + o.growth / 100, yrs);
    var equity = value * (1 - o.sellPct / 100) - balance;

    var buyOut = equity - (o.down + o.closing + mortgagePaid + running);
    var rentOut = -rentPaid;      // the deposit is still yours, so it nets out
    return { buy: buyOut, rent: rentOut, rentPaid: rentPaid, equity: equity,
             mortgagePaid: mortgagePaid, running: running, value: value, balance: balance };
  }

  function render() {
    if (!el('rdRent') || !w.Core) return;
    var v = CMC.inputs.get();
    var money = function (kyd) { return CMC.money(Math.round(kyd * v.fx), v.symbol); };

    var price = v.price;
    var down = price * v.deposit / 100;
    var close = Core.closingCosts({
      price: price, loan: Math.max(0, price - down), ptype: 'home',
      status: el('vStatus').value, joint: false, location: 'grand',
      legalPct: 1, bankPct: 1, valuation: 600, inspection: 0
    });
    var o = {
      price: price, down: down, loan: Math.max(0, price - down), closing: close.total,
      rent: n('vRent', 0) / v.fx, rentRise: n('vRentRise', 0),
      growth: n('vGrowth', 0), sellPct: n('vSell', 0)
    };

    // the first year buying comes out ahead, if it ever does within 40
    var crossover = null;
    for (var y = 1; y <= 40; y++) {
      var r = outcome(y, v, o);
      if (r.buy >= r.rent) { crossover = y; break; }
    }

    var horizon = Math.max(1, Math.round(n('vYears', 10)));
    var at = outcome(horizon, v, o);
    var ahead = at.buy - at.rent;

    el('vLabel').textContent = crossover ? 'Buying pulls ahead in' : 'Over forty years';
    el('vVerdict').textContent = crossover
      ? 'Year ' + crossover
      : 'Renting stays ahead';
    el('vNote').textContent = crossover
      ? (horizon >= crossover
          ? 'You plan to stay ' + horizon + ' years, which is past the crossover, so buying '
            + 'leaves you about ' + money(ahead) + ' better off than renting.'
          : 'You plan to stay ' + horizon + ' years, which is short of it, so renting leaves '
            + 'you about ' + money(-ahead) + ' better off at these figures.')
      : 'At this rent, this price and these growth rates, buying does not catch up within '
        + 'forty years. The deposit, duty and fees are the reason.';

    el('vTable').innerHTML = '<tbody>' +
      '<tr><th>Rent paid over ' + horizon + ' years</th><td>' + esc(money(at.rentPaid)) + '</td></tr>' +
      '<tr><th>Deposit and costs on the day</th><td>' + esc(money(o.down + o.closing)) + '</td></tr>' +
      '<tr><th>Mortgage paid over ' + horizon + ' years</th><td>' + esc(money(at.mortgagePaid)) + '</td></tr>' +
      '<tr><th>Insurance and upkeep</th><td>' + esc(money(at.running)) + '</td></tr>' +
      '<tr><th>What the property is worth then</th><td>' + esc(money(at.value)) + '</td></tr>' +
      '<tr><th>Still owed</th><td>' + esc(money(-at.balance)) + '</td></tr>' +
      '<tr><th>Equity after selling costs</th><td>' + esc(money(at.equity)) + '</td></tr>' +
      '<tr><th>Buying leaves you</th><td><strong>' + esc(money(at.buy)) + '</strong></td></tr>' +
      '<tr><th>Renting leaves you</th><td><strong>' + esc(money(at.rent)) + '</strong></td></tr>' +
      '</tbody>';
  }

  function start() {
    if (!el('rdRent')) return;
    ['vRent','vRentRise','vGrowth','vYears','vSell','vStatus'].forEach(function (id) {
      var e = el(id); if (!e) return;
      e.addEventListener('input', render);
      e.addEventListener('change', render);
    });
    el('rdRent').addEventListener('submit', function (ev) { ev.preventDefault(); });
    CMC.inputs.subscribe(render);
    render();
  }
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', start);
  else start();
})(window, document);
