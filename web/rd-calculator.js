/* The mortgage calculator.

   Every figure comes from core.js, the engine the live site already uses and
   tests. The board shipped its own duty arithmetic, but it has no 10% band at
   CI$2,000,000 and ignores the island it asks about, so it would understate
   duty on the most expensive purchases and misprice every Cayman Brac property.
   See REDESIGN-PLAN.md section 4.1.

   Price, deposit, rate and term are the shared inputs (CMC.inputs); everything
   else is local to this page. */
(function (w, d) {
  'use strict';

  function el(id) { return d.getElementById(id); }
  function numOf(id, fallback) {
    var e = el(id);
    if (!e) return fallback;
    var v = parseFloat(e.value);
    return isNaN(v) ? fallback : v;
  }
  function rawOf(id) {
    var e = el(id);
    if (!e || e.value === '') return null;
    var v = parseFloat(e.value);
    return isNaN(v) ? null : v;
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function trimRate(r) { return String(Math.round(Number(r) * 1000) / 1000); }

  var V;            // the shared inputs, refreshed each render
  function money(kyd) { return CMC.money(Math.round(kyd * V.fx), V.symbol); }

  /* Everything the page needs, in one place, all in CI$. */
  function model() {
    V = CMC.inputs.get();
    var price = V.price;
    var valuation = rawOf('cValuation');
    var island = el('cIsland').value;
    var ptype = el('cPtype').value;
    var status = el('cStatus').value;
    var joint = el('cBuyer').value === 'joint' && status !== 'standard';
    var down = price * V.deposit / 100;
    var loan = Math.max(0, price - down);
    var extra = (rawOf('cExtra') || 0) / V.fx;
    var bldgInStrata = el('cBldgInStrata').checked;

    var am = Core.amortise({ loan: loan, rate: V.rate / 100, years: V.term, extra: extra });
    var insAnnual = bldgInStrata || ptype === 'land' ? 0 : price * numOf('cBldg', 0) / 100;

    var close = Core.closingCosts({
      price: price, loan: loan, ptype: ptype, status: status, joint: joint,
      valuationBasis: valuation != null ? valuation / V.fx : 0,
      location: island,
      legalPct: numOf('cLegal', 1), bankPct: numOf('cBank', 1),
      valuation: numOf('cValFee', 600), inspection: 0
    });

    var strataRaw = rawOf('cStrata');
    var own = Core.monthlyOwnership({
      pmt: am.pmt,
      // unknown is not zero: a strata fee left blank on a condo stays unknown
      strata: strataRaw != null ? strataRaw / V.fx : (ptype === 'land' ? 0 : null),
      insuranceAnnual: insAnnual,
      lifeMonthly: (rawOf('cLife') || 0) / V.fx,
      upkeepAnnual: ptype === 'land' ? 0 : price * numOf('cMaint', 0) / 100,
      strataIncludesInsurance: bldgInStrata
    });

    return {
      price: price, down: down, loan: loan, am: am, close: close, own: own,
      ptype: ptype, status: status, joint: joint, island: island,
      dutiableBasis: close.dutiableBasis,
      cashToClose: down + close.total,
      income: rawOf('cIncome'), cash: rawOf('cCash')
    };
  }

  function rows(table, head, body) {
    table.innerHTML = (head ? '<thead><tr>' + head + '</tr></thead>' : '') +
      '<tbody>' + body + '</tbody>';
  }

  /* ----------------------------------------------------------- the render */
  function render() {
    if (!w.Core || !el('rdCalc')) return;
    var m = model();

    el('rMonthly').textContent = money(m.am.pmt);
    el('rMonthlySub').textContent = 'on a ' + money(m.loan) + ' loan at ' +
      trimRate(V.rate) + '% over ' + V.term + ' years';

    el('rLoan').textContent = money(m.loan);
    el('rDown').textContent = money(m.down);
    el('rDownSub').textContent = V.deposit + '% of the price';
    el('rInterest').textContent = money(m.am.totalInterest);
    el('rInterestSub').textContent = m.am.paidOffEarly
      ? 'Paid off in ' + Math.floor(m.am.months / 12) + ' yrs ' + (m.am.months % 12) +
        ' mo, saving ' + money(m.am.baseInterest - m.am.totalInterest)
      : 'Over the full ' + V.term + ' years';
    el('rCash').textContent = money(m.cashToClose);
    el('rCashSub').textContent = m.cash != null
      ? (m.cashToClose - m.cash / V.fx > 0
          ? 'Short by ' + money(m.cashToClose - m.cash / V.fx)
          : 'Your cash covers it, leaving ' + money(m.cash / V.fx - m.cashToClose))
      : 'Deposit plus duty and fees';

    // the calculator's own link into the listings, per HANDOFF 5.2
    var fit = el('rFitLink');
    if (fit) fit.setAttribute('href', '/listings/?max=' + Math.round(m.price * V.fx) +
      '&monthly=' + Math.round(m.own.total * V.fx));

    // monthly cost of owning
    rows(el('rOwnTable'), '',
      m.own.parts.map(function (p) {
        return '<tr><th>' + esc(p.label) + '</th><td>' +
          (p.amount == null ? '<em>Not entered</em>' : esc(money(p.amount))) + '</td></tr>';
      }).join('') +
      '<tr><th>Total</th><td><strong>' + esc(money(m.own.total)) + '</strong></td></tr>');
    el('rOwnNote').textContent = m.own.complete ? ''
      : 'A blank is treated as unknown, not as nothing, so the total is a floor.';

    // cash at closing
    rows(el('rCashTable'), '',
      '<tr><th>Deposit</th><td>' + esc(money(m.down)) + '</td></tr>' +
      m.close.items.filter(function (i) { return i.amount; }).map(function (i) {
        return '<tr><th>' + esc(i.label) + '</th><td>' + esc(money(i.amount)) + '</td></tr>';
      }).join('') +
      '<tr><th>Total</th><td><strong>' + esc(money(m.cashToClose)) + '</strong></td></tr>');
    el('rCashNote').textContent = 'Legal ' + numOf('cLegal', 1) + '% of the price and bank ' +
      numOf('cBank', 1) + '% of the loan are assumptions you can change above.';

    // stamp duty, with the rule that produced it
    var td = m.close.transferDuty;
    el('rDuty').textContent = money(td.amount);
    el('rDutyWhy').textContent = dutyWhy(td, m);
    el('cMortDuty').value = money(m.close.mortgageDuty.amount);

    // affordability: the 40% total debt service guideline
    var wrap = el('rAffordWrap');
    if (m.income != null && m.income > 0) {
      var incomeKyd = m.income / V.fx;
      var share = m.own.total / incomeKyd * 100;
      wrap.hidden = false;
      el('rAfford').textContent = share <= 40
        ? 'At ' + share.toFixed(0) + '% of your gross monthly income, this sits inside the 40% ' +
          'total debt service guideline most Cayman lenders apply. Other loan payments count ' +
          'towards that 40% as well.'
        : 'At ' + share.toFixed(0) + '% of your gross monthly income, this is above the 40% ' +
          'total debt service guideline most Cayman lenders apply. A larger deposit, a longer ' +
          'term or a lower price would bring it down.';
    } else {
      wrap.hidden = true;
    }

    renderYears(m);
  }

  function dutyWhy(td, m) {
    var basis = money(m.dutiableBasis);
    switch (td.rule) {
      case 'brac-land':
        return 'Nothing to pay under the Cayman Brac concession, if you build within two years.';
      case 'brac-developed':
        return '3% of ' + basis + ' under the Cayman Brac concession.';
      case 'luxury':
        return '10% of ' + basis + ': the rate rises to 10% of the whole value at CI$2,000,000.';
      case 'first-free':
        return 'Nothing to pay: a Caymanian buying a first property, inside the threshold.';
      case 'first-taper':
        // The board's wording. The arithmetic is already right: 3.75% applies to
        // the part above the threshold, not to the whole value.
        return '3.75% above ' + CMC.money(Math.round(td.free * V.fx), V.symbol) + '.';
      case 'second-reduced':
        return '3.75% of ' + basis + ' for a Caymanian second property.';
      case 'first-over': case 'second-over':
        return 'Above the concession limit, so the standard rate applies to the whole value.';
      default:
        return '7.5% of ' + basis + ', the standard rate.';
    }
  }

  function renderYears(m) {
    var table = el('rYears');
    var head = '<th>Year</th><th>Payments</th><th>Interest</th><th>Principal</th><th>Balance</th>';
    var body = '', y, i, payY, intY, prinY, last = null;
    for (y = 1; y <= Math.min(5, Math.ceil(m.am.months / 12)); y++) {
      payY = intY = prinY = 0;
      for (i = (y - 1) * 12; i < y * 12 && i < m.am.rows.length; i++) {
        // core.js uses short keys on its schedule rows: pay, i, p, bal
        payY += m.am.rows[i].pay;
        intY += m.am.rows[i].i;
        prinY += m.am.rows[i].p;
        last = m.am.rows[i].bal;
      }
      body += '<tr><th>' + y + '</th><td>' + esc(money(payY)) + '</td><td>' + esc(money(intY)) +
        '</td><td>' + esc(money(prinY)) + '</td><td>' + esc(money(last || 0)) + '</td></tr>';
    }
    rows(table, head, body);
  }

  function start() {
    if (!el('rdCalc')) return;
    // The old site kept the listings on this page at #listings. Anyone arriving
    // on that link should land where the listings actually are now.
    if (location.hash === '#listings') {
      location.replace('/listings/');
      return;
    }
    ['cValuation', 'cIsland', 'cPtype', 'cStatus', 'cBuyer', 'cExtra', 'cIncome', 'cCash',
     'cStrata', 'cLife', 'cBldg', 'cMaint', 'cLegal', 'cBank', 'cValFee', 'cBldgInStrata']
      .forEach(function (id) {
        var e = el(id);
        if (!e) return;
        e.addEventListener('input', render);
        e.addEventListener('change', render);
      });
    el('rdCalc').addEventListener('submit', function (ev) { ev.preventDefault(); });
    CMC.inputs.subscribe(render);
    render();
  }

  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', start);
  else start();
})(window, document);
