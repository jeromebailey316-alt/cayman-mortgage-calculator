/* =============================================================================
   Core: every figure the site quotes comes from here, so the calculator, the
   equity page and the rent-vs-buy page cannot drift apart.

   Three kinds of number are kept separate on purpose:
     RULES   government rules — rates and thresholds set by law
     LENDER  what banks publish or tell the property press; editable by the user
     PLAN    planning assumptions with no authority at all; editable

   Anything the user has not told us is `null`, never 0. A missing strata fee and
   a strata fee of zero are different facts, and the interface has to say which.
   ============================================================================= */
var Core = (function () {
  'use strict';

  // --- government rules -----------------------------------------------------
  var RULES = {
    verified: '2026-10-01',
    sources: {
      duty: 'https://www.caymanlandinfo.ky/services/valuation/stamp-duty',
      luxury: 'https://gov.ky/w/legislation-passed-to-increase-stamp-duty-on-properties-worth-2m-and-over',
      concession: 'https://www.caymanlandinfo.ky/docs/default-source/laws-and-regulations/stamp-duty/application-concession-form-for-caymanian-property-buyers.pdf',
      registry: 'https://www.caymanlandinfo.ky/services/land-registry/registry-fees'
    },
    std: 0.075,            // transfer duty, standard
    lux: 0.10,             // from 1 January 2026, on the whole value
    luxFrom: 2000000,
    reduced: 0.0375,       // the Caymanian concession rate
    first: {
      home: { single: [550000, 650000], joint: [600000, 700000] },
      land: { single: [250000, 350000], joint: [450000, 550000] }
    },
    second: {
      home: { single: 600000, joint: 700000 },
      land: { single: 300000, joint: 550000 }
    },
    mort: { threshold: 300000, low: 0.01, high: 0.015 },
    regTransfer: 50,
    regCharge: 50,
    dutyDueDays: 45,
    /* Cayman Brac only — Little Cayman is on the standard rates. Open to any buyer,
       not only Caymanians. A Cabinet concession under s.20(6)(a) of the Stamp Duty
       Act rather than a rate in the Regulations, so it is applied for and approved,
       and it expires. Undeveloped land at 0% must be built on within two years or
       the duty is clawed back with a 10% penalty. */
    brac: {
      from: '2026-01-01',
      expires: '2030-12-31',
      cap: 2000000,          // at or above this, the standard 10% applies
      developed: 0.03,
      undeveloped: 0,
      source: 'https://www.caymanlandinfo.ky/docs/default-source/laws-and-regulations/stamp-duty/stamp-duty-rates-cayman-brac-(2025).pdf',
      note: 'Cayman Brac concession, effective 1 January 2026, approved to 31 December 2030. '
          + 'Undeveloped land at 0% must be developed within two years, with a transfer '
          + 'restriction and full duty plus a 10% penalty if it is not.'
    }
  };

  // --- planning assumptions (no authority; the user can change all of them) ---
  var PLAN = {
    legalPct: 0.5,         // % of price
    bankPct: 1,            // % of loan
    valuation: 700,
    inspection: 750,
    insPctHouse: 1,        // % of value a year
    insPctCondo: 0.35,     // strata usually covers the building
    upkeepPctHouse: 1,
    upkeepPctCondo: 0.5,
    sellingCostPct: 6,
    fx: 0.82               // US$1 = CI$0.82
  };

  function isNum(v) { return typeof v === 'number' && isFinite(v); }
  function num(v, fallback) { return isNum(v) ? v : (fallback === undefined ? null : fallback); }
  function pos(v) { return isNum(v) && v > 0 ? v : 0; }

  /* ---------------------------------------------------------------- duty --- */

  function standardDuty(v) { return v >= RULES.luxFrom ? v * RULES.lux : v * RULES.std; }

  /* Duty on a Cayman Brac transfer under the island concession. Returns null where
     it does not apply, so the caller falls back to the ordinary rules. */
  function bracDuty(v, ptype, asOf) {
    var b = RULES.brac;
    var day = asOf || RULES.verified;
    if (day > b.expires) return null;              // concession lapsed
    if (v >= b.cap) return null;                   // CI$2M and over: standard 10%
    var undeveloped = ptype === 'land';
    var rate = undeveloped ? b.undeveloped : b.developed;
    return {
      amount: v * rate, rate: rate, value: v,
      rule: undeveloped ? 'brac-land' : 'brac-developed',
      conditional: undeveloped,                    // the 0% comes with a build condition
      expires: b.expires, note: b.note, source: b.source
    };
  }

  /* status: 'standard' | 'first' | 'second'; ptype: 'home' | 'land'
     location: 'grand' | 'brac' | 'little' — only Cayman Brac has its own rates.
     Where a Brac buyer also qualifies for a Caymanian concession, the cheaper of the
     two applies; they are alternative reliefs, not cumulative. */
  function transferDuty(value, ptype, status, joint, location, asOf) {
    var v = Math.max(0, pos(value));
    var std = standardDuty(v);
    var out = { amount: std, std: std, rate: v >= RULES.luxFrom ? RULES.lux : RULES.std,
                rule: v >= RULES.luxFrom ? 'luxury' : 'standard', value: v };
    var who = joint ? 'joint' : 'single';
    var kind = ptype === 'land' ? 'land' : 'home';
    if (status === 'first') {
      var t = RULES.first[kind][who];
      out.free = t[0]; out.upper = t[1];
      if (v <= t[0]) { out.amount = 0; out.rate = 0; out.rule = 'first-free'; }
      else if (v <= t[1]) { out.amount = (v - t[0]) * RULES.reduced; out.rate = RULES.reduced; out.rule = 'first-taper'; }
      else { out.rule = 'first-over'; out.atLimit = (t[1] - t[0]) * RULES.reduced; }
    } else if (status === 'second') {
      var cap = RULES.second[kind][who];
      out.cap = cap;
      if (v <= cap) { out.amount = v * RULES.reduced; out.rate = RULES.reduced; out.rule = 'second-reduced'; }
      else { out.rule = 'second-over'; out.atLimit = cap * RULES.reduced; }
    }
    if (location === 'brac') {
      var brac = bracDuty(v, ptype, asOf);
      if (brac && brac.amount <= out.amount) {
        brac.std = out.std;
        brac.alternative = out.rule;               // what the ordinary rules would have charged
        brac.alternativeAmount = out.amount;
        return brac;
      }
      if (brac) out.bracWorse = brac.amount;       // the island rate exists but is dearer
    }
    return out;
  }

  /* Duty when borrowing more against a property that already has a charge.
     The rate follows the total sum secured, so crossing CI$300,000 lifts the whole
     amount to 1.5% and the existing charge is upstamped to match. */
  function furtherChargeDuty(existingSecured, additional) {
    var existing = pos(existingSecured), extra = pos(additional);
    if (extra <= 0) return { amount: 0, rate: 0, upstamped: 0 };
    var onTotal = mortgageDuty(existing + extra);
    var alreadyPaid = mortgageDuty(existing).amount;
    var due = Math.max(0, onTotal.amount - alreadyPaid);
    return {
      amount: due, rate: onTotal.rate, total: existing + extra,
      onTotal: onTotal.amount, alreadyPaid: alreadyPaid,
      upstamped: existing > 0 && onTotal.rate > mortgageDuty(existing).rate ? existing : 0
    };
  }

  // Charged on the sum secured by the charge being stamped.
  function mortgageDuty(sumSecured) {
    var s = pos(sumSecured);
    if (s <= 0) return { amount: 0, rate: 0 };
    var rate = s <= RULES.mort.threshold ? RULES.mort.low : RULES.mort.high;
    return { amount: s * rate, rate: rate };
  }

  // Every price at which a cost steps. Used when solving for a maximum price:
  // costs jump at these points, so a smooth search would overshoot.
  function dutyThresholds(ptype, status, joint) {
    var kind = ptype === 'land' ? 'land' : 'home', who = joint ? 'joint' : 'single', out = [RULES.luxFrom];
    if (status === 'first') out = out.concat(RULES.first[kind][who]);
    if (status === 'second') out.push(RULES.second[kind][who]);
    return out.sort(function (a, b) { return a - b; });
  }

  /* ------------------------------------------------------------- payments --- */

  function payment(loan, annualRate, nMonths) {
    var L = pos(loan), n = Math.max(1, Math.round(nMonths || 0));
    if (L <= 0) return 0;
    var r = (annualRate || 0) / 12;
    return r === 0 ? L / n : L * r / (1 - Math.pow(1 + r, -n));
  }

  /* Amortisation with optional extra payments and rate changes.
     o: {loan, rate (annual, as a fraction), years, extra, rateChanges:[{month, rate}]}
     A rate change recalculates the payment from the balance and months remaining
     at that point, which is what a variable-rate lender actually does. */
  function amortise(o) {
    o = o || {};
    var L = pos(o.loan), years = Math.max(1 / 12, o.years || 0), n = Math.max(1, Math.round(years * 12));
    var rate = o.rate || 0, extra = pos(o.extra);
    var changes = (o.rateChanges || []).slice().sort(function (a, b) { return a.month - b.month; });
    var pmt = payment(L, rate, n);
    var bal = L, cumI = 0, rows = [], bals = [L], ints = [0], m = 0, basePmt = pmt;
    var scheduled = pmt;

    while (bal > 0.005 && m < n) {
      m++;
      while (changes.length && changes[0].month === m) {
        rate = changes.shift().rate;
        scheduled = payment(bal, rate, n - m + 1);   // same payoff date, new rate
      }
      var r = rate / 12;
      var interest = bal * r;
      var principal = scheduled - interest + extra;
      if (principal > bal || m === n) principal = bal;
      if (principal < 0) principal = 0;              // negative amortisation guard
      bal -= principal;
      cumI += interest;
      rows.push({ m: m, pay: principal + interest, p: principal, i: interest, bal: Math.max(0, bal), cumI: cumI });
      bals.push(Math.max(0, bal));
      ints.push(cumI);
    }
    return {
      pmt: basePmt, scheduled: scheduled, n: n, months: m, rows: rows, bals: bals, ints: ints,
      totalInterest: cumI,
      baseInterest: L > 0 ? basePmt * n - L : 0,
      paidOffEarly: m < n,
      monthsSaved: Math.max(0, n - m)
    };
  }

  /* -------------------------------------------------------- closing costs --- */

  /* Itemised, with each line marked so the interface can say what is a quote,
     what is an estimate and what is simply unknown.
     o: {price, loan, ptype, status, joint, chattels, valuationBasis,
         legalPct, bankPct, valuation, inspection, insuranceFirstYear, payInsuranceAtClose} */
  function closingCosts(o) {
    o = o || {};
    var price = pos(o.price), loan = pos(o.loan);
    var dutiableBasis = isNum(o.valuationBasis) && o.valuationBasis > 0 ? o.valuationBasis : price;
    var dutiable = Math.max(0, dutiableBasis - pos(o.chattels));
    var td = transferDuty(dutiable, o.ptype, o.status, o.joint, o.location, o.asOf);
    var md = mortgageDuty(loan);
    var items = [
      { key: 'transferDuty', label: 'Stamp duty on the transfer', amount: td.amount, kind: 'rule' },
      { key: 'mortgageDuty', label: 'Stamp duty on the mortgage', amount: md.amount, kind: 'rule' },
      { key: 'registry', label: 'Land Registry fees', kind: 'rule',
        amount: RULES.regTransfer + (loan > 0 ? RULES.regCharge : 0) }
    ];
    function plan(key, label, amount, estimated) {
      items.push({ key: key, label: label, amount: amount == null ? null : amount,
                   kind: amount == null ? 'unknown' : (estimated ? 'estimate' : 'quote') });
    }
    plan('legal', 'Legal fees', price * num(o.legalPct, PLAN.legalPct) / 100, o.legalPct == null);
    plan('bank', 'Bank fee', loan > 0 ? loan * num(o.bankPct, PLAN.bankPct) / 100 : 0, o.bankPct == null);
    plan('valuation', 'Valuation', loan > 0 ? num(o.valuation, PLAN.valuation) : 0, o.valuation == null);
    plan('inspection', 'Inspection or survey', num(o.inspection, PLAN.inspection), o.inspection == null);
    if (o.payInsuranceAtClose) {
      plan('insurance', "First year's insurance", num(o.insuranceFirstYear, null), o.insuranceFirstYear == null);
    }
    var known = items.filter(function (i) { return i.amount != null; });
    var unknown = items.filter(function (i) { return i.amount == null; });
    return {
      items: items,
      transferDuty: td, mortgageDuty: md,
      dutiable: dutiable, dutiableBasis: dutiableBasis,
      total: known.reduce(function (s, i) { return s + i.amount; }, 0),
      complete: unknown.length === 0,
      unknown: unknown.map(function (i) { return i.label; })
    };
  }

  /* ------------------------------------------------------ monthly to own --- */

  /* o: {pmt, strata, insuranceAnnual, lifeMonthly, upkeepAnnual, strataIncludesInsurance}
     Anything null stays null and is listed in `unknown` — it is never added as 0. */
  function monthlyOwnership(o) {
    o = o || {};
    var parts = [
      { key: 'pmt', label: 'Mortgage principal and interest', amount: num(o.pmt, 0) },
      { key: 'strata', label: 'Strata fees', amount: num(o.strata, null) },
      { key: 'insurance', label: 'Building insurance',
        amount: o.strataIncludesInsurance ? 0 : (isNum(o.insuranceAnnual) ? o.insuranceAnnual / 12 : null) },
      { key: 'life', label: 'Life insurance', amount: num(o.lifeMonthly, null) },
      { key: 'upkeep', label: 'Maintenance allowance',
        amount: isNum(o.upkeepAnnual) ? o.upkeepAnnual / 12 : null }
    ];
    var known = parts.filter(function (p) { return p.amount != null; });
    var unknown = parts.filter(function (p) { return p.amount == null; });
    return {
      parts: parts,
      total: known.reduce(function (s, p) { return s + p.amount; }, 0),
      complete: unknown.length === 0,
      unknown: unknown.map(function (p) { return p.label; }),
      strataIncludesInsurance: !!o.strataIncludesInsurance
    };
  }

  /* --------------------------------------------------------- affordability --- */

  /* Everything a purchase at `price` costs, used by both the calculator and the
     affordability solvers so they cannot disagree. */
  function purchase(price, s) {
    s = s || {};
    var p = pos(price);
    var down = s.downIsAmount ? Math.min(p, pos(s.downAmount)) : p * num(s.downPct, 0) / 100;
    var loan = Math.max(0, p - down);
    var insAnnual = isNum(s.insuranceAnnual) ? s.insuranceAnnual
                  : (isNum(s.insPct) ? p * s.insPct / 100 : null);
    var upkeepAnnual = isNum(s.upkeepPct) ? p * s.upkeepPct / 100 : null;
    var close = closingCosts({
      price: p, loan: loan, ptype: s.ptype, status: s.status, joint: s.joint,
      chattels: s.chattels, valuationBasis: s.valuationBasis, location: s.location,
      legalPct: s.legalPct, bankPct: s.bankPct, valuation: s.valuation, inspection: s.inspection,
      insuranceFirstYear: insAnnual, payInsuranceAtClose: s.payInsuranceAtClose
    });
    var months = Math.max(1, Math.round(num(s.term, 25) * 12));
    var pmt = payment(loan, num(s.rate, 0) / 100, months);
    var own = monthlyOwnership({
      pmt: pmt, strata: s.strata, insuranceAnnual: insAnnual, lifeMonthly: s.life,
      upkeepAnnual: upkeepAnnual, strataIncludesInsurance: s.strataIncludesInsurance
    });
    return {
      price: p, down: down, loan: loan, ltv: p > 0 ? loan / p : 0,
      pmt: pmt, closing: close, ownership: own,
      cashToClose: down + close.total,
      cashComplete: close.complete
    };
  }

  /* Highest price where `ok(purchase)` still holds.
     Costs step at duty thresholds, so a plain bisection can land just above a
     cliff: after bisecting we test each threshold boundary explicitly. */
  function maxPrice(ok, s, hiGuess) {
    var hi = hiGuess || 2e7;
    if (!ok(purchase(1000, s))) return 0;
    if (ok(purchase(hi, s))) return hi;
    var lo = 1000;
    for (var i = 0; i < 60 && hi - lo > 100; i++) {
      var mid = (lo + hi) / 2;
      if (ok(purchase(mid, s))) lo = mid; else hi = mid;
    }
    var best = lo;
    dutyThresholds(s.ptype, s.status, s.joint).forEach(function (t) {
      [t - 1, t].forEach(function (candidate) {
        if (candidate > best && ok(purchase(candidate, s))) best = candidate;
      });
    });
    return Math.floor(best / 100) * 100;
  }

  /* The three budgets the brief asks for. Each returns null when the inputs it
     needs are missing — a budget nobody told us about is not a budget of zero.
     h: {grossMonthly, takeHomeMonthly, debtsMonthly, otherCommitments,
         livingCosts, savingsTarget, cashAvailable, cashReserve, dsrPct} */
  function budgets(h, s) {
    h = h || {}; s = s || {};
    var out = { lending: null, comfortable: null, cash: null, limitedBy: null };
    var dsr = num(h.dsrPct, 33) / 100;

    // 1. what a lender might advance, on a debt-service ratio
    if (isNum(h.grossMonthly) && h.grossMonthly > 0) {
      var roomForDebt = h.grossMonthly * dsr - pos(h.debtsMonthly);
      out.lending = roomForDebt <= 0 ? 0 : maxPrice(function (p) { return p.pmt <= roomForDebt; }, s);
      out.lendingRoom = roomForDebt;
    }
    // 2. what the household can carry once everything else is paid
    if (isNum(h.takeHomeMonthly) && h.takeHomeMonthly > 0) {
      var spare = h.takeHomeMonthly - pos(h.livingCosts) - pos(h.debtsMonthly)
                - pos(h.otherCommitments) - pos(h.savingsTarget);
      out.comfortableSpare = spare;
      out.comfortable = spare <= 0 ? 0
        : maxPrice(function (p) { return p.ownership.total <= spare; }, s);
    }
    // 3. what the cash stretches to, after the reserve they want to keep
    if (isNum(h.cashAvailable) && h.cashAvailable > 0) {
      var usable = h.cashAvailable - pos(h.cashReserve);
      out.cashUsable = usable;
      out.cash = usable <= 0 ? 0 : maxPrice(function (p) { return p.cashToClose <= usable; }, s);
    }
    var have = ['lending', 'comfortable', 'cash'].filter(function (k) { return out[k] != null; });
    if (have.length) {
      out.max = Math.min.apply(null, have.map(function (k) { return out[k]; }));
      out.limitedBy = have.filter(function (k) { return out[k] === out.max; })[0];
      out.assessed = have;
    }
    return out;
  }

  /* How a given property sits against whatever the household has told us.
     Never claims more than it knows: each test is reported separately. */
  function fit(price, h, s) {
    h = h || {};
    var p = purchase(price, s);
    var res = { price: p.price, monthly: null, cash: null, cashShortfall: null,
                incomeChecked: false, cashChecked: false, purchase: p };
    var dsr = num(h.dsrPct, 33) / 100;
    if (isNum(h.grossMonthly) && h.grossMonthly > 0) {
      res.incomeChecked = true;
      var room = h.grossMonthly * dsr - pos(h.debtsMonthly);
      res.monthly = p.pmt <= room ? 'within' : (p.pmt <= room * 1.1 ? 'stretch' : 'over');
      res.monthlyRoom = room;
    }
    if (isNum(h.cashAvailable) && h.cashAvailable > 0) {
      res.cashChecked = true;
      var usable = h.cashAvailable - pos(h.cashReserve);
      res.cashShortfall = Math.max(0, p.cashToClose - usable);
      res.cash = res.cashShortfall === 0 ? 'within' : 'short';
    }
    res.complete = p.cashComplete && p.ownership.complete;
    return res;
  }

  /* -------------------------------------------------------------- currency --- */

  function toKyd(v, cur, fx) { return cur === 'USD' ? pos(v) * num(fx, PLAN.fx) : pos(v); }
  function fromKyd(v, cur, fx) { return cur === 'USD' ? v / num(fx, PLAN.fx) : v; }

  var api = {
    RULES: RULES, PLAN: PLAN,
    R: RULES,                                   // older name, still used by page code
    isNum: isNum, num: num,
    standardDuty: standardDuty, transferDuty: transferDuty, mortgageDuty: mortgageDuty,
    bracDuty: bracDuty, furtherChargeDuty: furtherChargeDuty,
    dutyThresholds: dutyThresholds,
    payment: payment, amortise: amortise,
    closingCosts: closingCosts, monthlyOwnership: monthlyOwnership,
    purchase: purchase, maxPrice: maxPrice, budgets: budgets, fit: fit,
    toKyd: toKyd, fromKyd: fromKyd
  };
  return api;
})();
if (typeof module !== 'undefined') module.exports = Core;
