/* Live figures inside the guides.

   The stamp duty guide's quick estimate is bound to the shared price, and its
   rate label is computed rather than fixed: the board hard-coded "7.5%", which
   stops being true at CI$2,000,000 where the rate becomes 10% of the whole
   value. */
(function (w, d) {
  'use strict';

  function start() {
    var out = d.getElementById('gdDuty');
    if (!out || !w.Core) return;
    var label = d.getElementById('gdRateLabel');

    function render() {
      var v = CMC.inputs.get();
      var td = Core.transferDuty(v.price, 'home', 'standard', false, 'grand');
      out.textContent = CMC.money(Math.round(td.amount * v.fx), v.symbol);
      if (label) {
        label.textContent = td.rule === 'luxury'
          ? 'Standard rate at CI$2M and over: 10%'
          : 'Standard rate: 7.5%';
      }
    }
    CMC.inputs.subscribe(render);
    render();
  }

  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', start);
  else start();
})(window, document);

/* ---- Refinancing break-even (HANDOFF 5.5) -------------------------------- */
(function (w, d) {
  'use strict';
  function el(id) { return d.getElementById(id); }
  function n(id, fb) { var e = el(id); if (!e) return fb; var v = parseFloat(e.value); return isNaN(v) ? fb : v; }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function render() {
    if (!el('rdRefi') || !w.Core) return;
    var money = function (x) { return CMC.money(x, 'CI$'); };
    var bal = n('fBal', 0), cur = n('fCur', 0), yrs = Math.max(1, n('fYears', 20));
    var nr = n('fNew', 0), nt = Math.max(1, n('fTerm', yrs));
    var curPay = CMC.payment(bal, cur, yrs);
    var newPay = CMC.payment(bal, nr, nt);
    var saving = curPay - newPay;

    // the engine's rule, rather than a second copy of the 1%/1.5% split
    var mduty = el('fCharge').checked ? Core.mortgageDuty(bal).amount : 0;
    var other = n('fLegal', 0) + n('fVal', 0) + bal * n('fBank', 0) / 100 + n('fErc', 0);
    var total = mduty + other;

    var curInt = curPay * yrs * 12 - bal;
    var newInt = newPay * nt * 12 - bal;
    var net = curInt - newInt - total;

    var label = 'Break-even', verdict, note;
    if (saving > 0) {
      var m = Math.ceil(total / saving);
      verdict = m + ' months';
      note = 'The monthly saving of ' + money(saving) + ' repays ' + money(total) +
        ' of costs in ' + (m < 24 ? m + ' months' : (Math.round(m / 12 * 10) / 10) + ' years') +
        '. Worth it if you will keep the mortgage longer than that.';
      if (net < 0) {
        note += ' Over the whole term, though, the new loan costs ' + money(-net) +
          ' more, usually because the term is longer.';
      }
    } else if (nt > yrs && newInt + total > curInt) {
      label = 'Lower payment, higher cost';
      verdict = 'Not a saving';
      note = 'A longer term lowers the payment but costs more interest overall than you save.';
    } else {
      label = 'No monthly saving';
      verdict = 'Not worth it';
      note = 'The new payment is not lower than the current one at these figures.';
    }

    el('fVerdictLabel').textContent = label;
    el('fVerdict').textContent = verdict;
    el('fNote').textContent = note;

    el('fTable').innerHTML = '<tbody>' +
      '<tr><th>Payment now</th><td>' + esc(money(curPay)) + ' a month</td></tr>' +
      '<tr><th>Payment after</th><td>' + esc(money(newPay)) + ' a month</td></tr>' +
      '<tr><th>Monthly saving</th><td>' + esc(money(saving)) + '</td></tr>' +
      '<tr><th>Stamp duty on the new charge</th><td>' + esc(money(mduty)) + '</td></tr>' +
      '<tr><th>Legal, valuation, bank fee and any early repayment charge</th><td>' +
        esc(money(other)) + '</td></tr>' +
      '<tr><th>Total cost of switching</th><td><strong>' + esc(money(total)) +
        '</strong></td></tr>' +
      '<tr><th>Interest over the term now</th><td>' + esc(money(curInt)) + '</td></tr>' +
      '<tr><th>Interest over the new term, plus costs</th><td>' +
        esc(money(newInt + total)) + '</td></tr>' +
      '<tr><th>Net saving</th><td><strong>' + esc(money(net)) + '</strong></td></tr>' +
      '</tbody>';
  }

  function start() {
    if (!el('rdRefi')) return;
    ['fBal','fCur','fYears','fNew','fTerm','fErc','fLegal','fVal','fBank','fCharge']
      .forEach(function (id) {
        var e = el(id); if (!e) return;
        e.addEventListener('input', render);
        e.addEventListener('change', render);
      });
    el('rdRefi').addEventListener('submit', function (ev) { ev.preventDefault(); });
    render();
  }
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', start);
  else start();
})(window, document);

/* ---- Cash at closing, on the same core.js itemisation as the calculator --- */
(function (w, d) {
  'use strict';
  function el(id) { return d.getElementById(id); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function render() {
    var table = el('ccTable');
    if (!table || !w.Core) return;
    var v = CMC.inputs.get();
    var money = function (kyd) { return CMC.money(Math.round(kyd * v.fx), v.symbol); };
    var status = el('ccStatus').value;
    var price = v.price;
    var down = price * v.deposit / 100;
    var close = Core.closingCosts({
      price: price, loan: Math.max(0, price - down), ptype: 'home',
      status: status, joint: false, location: 'grand',
      legalPct: 1, bankPct: 1, valuation: 600, inspection: 0
    });
    var total = down + close.total;

    table.innerHTML = '<tbody>' +
      '<tr><th>Deposit</th><td>' + esc(money(down)) + '</td></tr>' +
      close.items.filter(function (i) { return i.amount; }).map(function (i) {
        return '<tr><th>' + esc(i.label) + '</th><td>' + esc(money(i.amount)) + '</td></tr>';
      }).join('') +
      '<tr><th>Total on the day</th><td><strong>' + esc(money(total)) +
      '</strong></td></tr></tbody>';

    el('ccNote').textContent = 'That is ' + (total / price * 100).toFixed(1) +
      '% of the purchase price. Legal at 1% and the bank fee at 1% are typical, not quoted: ' +
      'ask for both in writing.';
  }

  function start() {
    if (!el('ccTable')) return;
    var s = el('ccStatus');
    if (s) s.addEventListener('change', render);
    var f = el('rdClosing');
    if (f) f.addEventListener('submit', function (ev) { ev.preventDefault(); });
    CMC.inputs.subscribe(render);
    render();
  }
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', start);
  else start();
})(window, document);
