/* ================= Core maths (no DOM) ================= */
var Core = (function () {
  'use strict';
  var R = {
    std: 0.075, lux: 0.10, luxFrom: 2000000, reduced: 0.0375,
    first: { home: { single: [550000, 650000], joint: [600000, 700000] },
             land: { single: [250000, 350000], joint: [450000, 550000] } },
    second: { home: { single: 600000, joint: 700000 },
              land: { single: 300000, joint: 550000 } },
    mort: { threshold: 300000, low: 0.01, high: 0.015 },
    regTransfer: 50, regCharge: 50
  };

  function standardDuty(v) { return v >= R.luxFrom ? v * R.lux : v * R.std; }

  function transferDuty(v, ptype, status, joint) {
    v = Math.max(0, v);
    var std = standardDuty(v), out = { amount: std, std: std, rule: v >= R.luxFrom ? 'luxury' : 'standard' };
    var who = joint ? 'joint' : 'single';
    if (status === 'first') {
      var t = R.first[ptype][who];
      out.free = t[0]; out.upper = t[1];
      if (v <= t[0]) { out.amount = 0; out.rule = 'first-free'; }
      else if (v <= t[1]) { out.amount = (v - t[0]) * R.reduced; out.rule = 'first-taper'; }
      else { out.rule = 'first-over'; out.atLimit = (t[1] - t[0]) * R.reduced; }
    } else if (status === 'second') {
      var cap = R.second[ptype][who];
      out.cap = cap;
      if (v <= cap) { out.amount = v * R.reduced; out.rule = 'second-reduced'; }
      else { out.rule = 'second-over'; out.atLimit = cap * R.reduced; }
    }
    return out;
  }

  function mortgageDuty(loan) {
    if (loan <= 0) return { amount: 0, rate: 0 };
    var rate = loan <= R.mort.threshold ? R.mort.low : R.mort.high;
    return { amount: loan * rate, rate: rate };
  }

  function payment(L, annual, n) {
    if (L <= 0 || n <= 0) return 0;
    var r = annual / 12;
    return r === 0 ? L / n : L * r / (1 - Math.pow(1 + r, -n));
  }

  function amortise(L, annual, years, extra) {
    var n = Math.max(1, Math.round(years * 12)), r = annual / 12, pmt = payment(L, annual, n);
    var bal = L, cumI = 0, cumP = 0, rows = [], bals = [L], ints = [0], m = 0;
    extra = Math.max(0, extra || 0);
    while (bal > 0.005 && m < n) {
      m++;
      var i = bal * r, p = pmt - i + extra;
      if (p > bal || m === n) p = bal;
      bal -= p; cumI += i; cumP += p;
      rows.push({ m: m, pay: p + i, p: p, i: i, bal: Math.max(0, bal), cumI: cumI, cumP: cumP });
      bals.push(Math.max(0, bal)); ints.push(cumI);
    }
    return { pmt: pmt, n: n, months: m, rows: rows, bals: bals, ints: ints,
             totalInterest: cumI, baseInterest: L > 0 ? pmt * n - L : 0 };
  }

  // The one-off costs of buying, on the calculator's own planning defaults.
  // opts: {ptype, status, joint, legalPct, bankPct, valuation, inspection, insPct}
  function closingCosts(price, loan, opts) {
    opts = opts || {};
    var ptype = opts.ptype || 'home';
    var td = transferDuty(price, ptype, opts.status || 'standard', !!opts.joint);
    var md = mortgageDuty(loan);
    var legal = price * (opts.legalPct == null ? 0.5 : opts.legalPct) / 100;
    var bank = loan * (opts.bankPct == null ? 1 : opts.bankPct) / 100;
    var valuation = loan > 0 ? (opts.valuation == null ? 700 : opts.valuation) : 0;
    var inspection = opts.inspection == null ? 750 : opts.inspection;
    var insurance = ptype === 'home' ? price * (opts.insPct == null ? 1 : opts.insPct) / 100 : 0;
    var registry = R.regTransfer + (loan > 0 ? R.regCharge : 0);
    return {
      transferDuty: td.amount, mortgageDuty: md.amount, registry: registry,
      legal: legal, bank: bank, valuation: valuation, inspection: inspection, insurance: insurance,
      total: td.amount + md.amount + registry + legal + bank + valuation + inspection + insurance
    };
  }

  return { R: R, transferDuty: transferDuty, mortgageDuty: mortgageDuty, payment: payment,
           amortise: amortise, standardDuty: standardDuty, closingCosts: closingCosts };
})();
if (typeof module !== 'undefined') module.exports = Core;
