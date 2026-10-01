/* Tests for the shared financial engine.   node test/core.test.js
   No dependencies: a wrong number here is worse than a missing framework. */
'use strict';
const Core = require('../web/core.js');

let pass = 0, fail = 0;
const failures = [];

function ok(name, cond, detail) {
  if (cond) { pass++; return; }
  fail++; failures.push(name + (detail ? '  — ' + detail : ''));
}
function near(name, got, want, tol) {
  const t = tol === undefined ? 0.5 : tol;
  ok(name, Math.abs(got - want) <= t, `got ${got}, wanted ${want} (±${t})`);
}
function group(title) { console.log('\n' + title); }

/* ------------------------------------------------------------- payments --- */
group('Payments and amortisation');

near('payment: 720k at 7.25% over 25y', Core.payment(720000, 0.0725, 300), 5203.9, 1);
near('payment: zero interest spreads the loan evenly', Core.payment(240000, 0, 240), 1000, 0.01);
near('payment: no loan, no payment', Core.payment(0, 0.0725, 300), 0, 0);
near('payment: negative loan treated as none', Core.payment(-50000, 0.0725, 300), 0, 0);

const am = Core.amortise({ loan: 500000, rate: 0.07, years: 25 });
near('amortise: months run the full term', am.months, 300, 0);
near('amortise: final balance clears', am.bals[am.bals.length - 1], 0, 0.01);
near('amortise: total interest', am.totalInterest, am.pmt * 300 - 500000, 2);

const amZero = Core.amortise({ loan: 120000, rate: 0, years: 10 });
near('amortise: zero rate charges no interest', amZero.totalInterest, 0, 0.01);
near('amortise: zero rate clears the balance', amZero.bals[amZero.bals.length - 1], 0, 0.01);

const amExtra = Core.amortise({ loan: 500000, rate: 0.07, years: 25, extra: 500 });
ok('amortise: extra payments finish early', amExtra.months < am.months,
   `${amExtra.months} vs ${am.months}`);
ok('amortise: extra payments cost less interest', amExtra.totalInterest < am.totalInterest,
   `${Math.round(amExtra.totalInterest)} vs ${Math.round(am.totalInterest)}`);
near('amortise: extra payments still clear the balance',
     amExtra.bals[amExtra.bals.length - 1], 0, 0.01);

const amNone = Core.amortise({ loan: 0, rate: 0.07, years: 25 });
near('amortise: no borrowing, no interest', amNone.totalInterest, 0, 0);

// a rate rise partway through: payment is recut from the balance and months left
const amRise = Core.amortise({ loan: 500000, rate: 0.07, years: 25, rateChanges: [{ month: 61, rate: 0.09 }] });
ok('amortise: a rate rise costs more interest', amRise.totalInterest > am.totalInterest,
   `${Math.round(amRise.totalInterest)} vs ${Math.round(am.totalInterest)}`);
near('amortise: a rate rise still clears the balance', amRise.bals[amRise.bals.length - 1], 0, 0.01);
const atChange = Core.amortise({ loan: 500000, rate: 0.07, years: 25 }).rows[59].bal;
near('amortise: recut payment matches the balance and term left',
     amRise.rows[60].pay, Core.payment(atChange, 0.09, 240), 2);

/* ----------------------------------------------------------------- duty --- */
group('Stamp duty: thresholds and concessions');

near('standard: 7.5% below the high-value line', Core.transferDuty(1000000, 'home', 'standard', false).amount, 75000);
near('standard: just under CI$2M is still 7.5%', Core.transferDuty(1999999, 'home', 'standard', false).amount, 149999.925, 0.5);
near('standard: at CI$2M it is 10% of the whole value', Core.transferDuty(2000000, 'home', 'standard', false).amount, 200000);
ok('standard: crossing CI$2M costs about CI$50k more',
   Core.transferDuty(2000000, 'home', 'standard', false).amount
   - Core.transferDuty(1999999, 'home', 'standard', false).amount > 50000);

near('first-time: nothing at CI$550,000', Core.transferDuty(550000, 'home', 'first', false).amount, 0);
near('first-time: 3.75% on the slice above CI$550,000',
     Core.transferDuty(600000, 'home', 'first', false).amount, 50000 * 0.0375);
near('first-time: at the CI$650,000 ceiling', Core.transferDuty(650000, 'home', 'first', false).amount, 100000 * 0.0375);
near('first-time: one dollar over the ceiling loses the concession',
     Core.transferDuty(650001, 'home', 'first', false).amount, 650001 * 0.075, 1);
ok('first-time: the cliff is real', Core.transferDuty(650001, 'home', 'first', false).amount
   - Core.transferDuty(650000, 'home', 'first', false).amount > 44000);

near('first-time joint: nothing at CI$600,000', Core.transferDuty(600000, 'home', 'first', true).amount, 0);
near('first-time land: nothing at CI$250,000', Core.transferDuty(250000, 'land', 'first', false).amount, 0);
near('second property: 3.75% of the whole value', Core.transferDuty(600000, 'home', 'second', false).amount, 22500);
near('second property: over the cap reverts to 7.5%',
     Core.transferDuty(600001, 'home', 'second', false).amount, 600001 * 0.075, 1);

near('mortgage duty: 1% at CI$300,000', Core.mortgageDuty(300000).amount, 3000);
near('mortgage duty: 1.5% of the whole sum just above', Core.mortgageDuty(300001).amount, 4500.015, 0.1);
near('mortgage duty: nothing without a loan', Core.mortgageDuty(0).amount, 0);

/* ------------------------------------------------- Cayman Brac concession --- */
group('Cayman Brac (and not Little Cayman)');

near('brac: 3% on a developed property under CI$2M',
     Core.transferDuty(400000, 'home', 'standard', false, 'brac').amount, 12000);
near('brac: nothing on undeveloped land under CI$2M',
     Core.transferDuty(300000, 'land', 'standard', false, 'brac').amount, 0);
ok('brac: the 0% on land carries a build condition',
   Core.transferDuty(300000, 'land', 'standard', false, 'brac').conditional === true);
near('brac: at CI$2M the standard 10% applies',
     Core.transferDuty(2000000, 'home', 'standard', false, 'brac').amount, 200000);
near('brac: just under CI$2M is still 3%',
     Core.transferDuty(1999999, 'home', 'standard', false, 'brac').amount, 59999.97, 0.5);
near('little cayman: no island concession, standard 7.5%',
     Core.transferDuty(400000, 'home', 'standard', false, 'little').amount, 30000);
near('grand cayman: unchanged', Core.transferDuty(400000, 'home', 'standard', false, 'grand').amount, 30000);
ok('brac: a Caymanian first-time buyer keeps the better of the two reliefs',
   Core.transferDuty(400000, 'home', 'first', false, 'brac').amount === 0);
ok('brac: the concession lapses after it expires',
   Core.transferDuty(400000, 'home', 'standard', false, 'brac', '2031-01-01').amount === 30000);
ok('brac: a Brac purchase is cheaper than the same house on Grand Cayman',
   Core.transferDuty(400000, 'home', 'standard', false, 'brac').amount
   < Core.transferDuty(400000, 'home', 'standard', false, 'grand').amount);

group('Borrowing more against an existing charge');

near('further charge: duty follows the total, less what was already paid',
     Core.furtherChargeDuty(250000, 100000).amount, 2750);
ok('further charge: the existing charge is upstamped when the rate rises',
   Core.furtherChargeDuty(250000, 100000).upstamped === 250000);
near('further charge: staying under CI$300,000 is charged at 1%',
     Core.furtherChargeDuty(100000, 50000).amount, 500);
ok('further charge: no upstamping when the rate does not change',
   Core.furtherChargeDuty(100000, 50000).upstamped === 0);
near('further charge: nothing borrowed, nothing due', Core.furtherChargeDuty(250000, 0).amount, 0);
near('further charge: a first charge is simply the ordinary duty',
     Core.furtherChargeDuty(0, 400000).amount, Core.mortgageDuty(400000).amount);

/* -------------------------------------------------------- closing costs --- */
group('Closing costs');

const cc = Core.closingCosts({ price: 900000, loan: 720000, ptype: 'home', status: 'standard' });
near('closing: transfer duty', cc.transferDuty.amount, 67500);
near('closing: mortgage duty', cc.mortgageDuty.amount, 10800);
near('closing: registry is CI$100 with a charge', cc.items.find(i => i.key === 'registry').amount, 100);
ok('closing: defaults are marked as estimates',
   cc.items.filter(i => i.kind === 'estimate').length >= 4);
ok('closing: complete when nothing is unknown', cc.complete === true, JSON.stringify(cc.unknown));

const ccUnknown = Core.closingCosts({ price: 900000, loan: 720000, payInsuranceAtClose: true });
ok('closing: unknown insurance is reported, not counted as zero',
   ccUnknown.complete === false && ccUnknown.unknown.length === 1, JSON.stringify(ccUnknown.unknown));
ok('closing: an unknown line never adds NaN', isFinite(ccUnknown.total), String(ccUnknown.total));

const ccChattels = Core.closingCosts({ price: 900000, loan: 0, chattels: 50000 });
near('closing: chattels come off the dutiable value', ccChattels.dutiable, 850000);
near('closing: registry is CI$50 with no charge',
     ccChattels.items.find(i => i.key === 'registry').amount, 50);

const ccVal = Core.closingCosts({ price: 900000, loan: 0, valuationBasis: 1000000 });
near('closing: duty follows the valuation when it is higher than the price',
     ccVal.transferDuty.amount, 75000);

/* ------------------------------------------------------------ ownership --- */
group('Monthly cost to own');

const ownFull = Core.monthlyOwnership({ pmt: 5204, strata: 550, insuranceAnnual: 3150, lifeMonthly: 60, upkeepAnnual: 4500 });
near('ownership: adds up the known parts', ownFull.total, 5204 + 550 + 3150 / 12 + 60 + 4500 / 12, 0.5);
ok('ownership: complete when everything is known', ownFull.complete === true);

const ownPartial = Core.monthlyOwnership({ pmt: 5204, strata: null, insuranceAnnual: null });
ok('ownership: missing costs are listed, not silently zero',
   ownPartial.complete === false && ownPartial.unknown.length === 4, JSON.stringify(ownPartial.unknown));
near('ownership: the total still excludes the unknowns', ownPartial.total, 5204, 0.01);

const ownZeroStrata = Core.monthlyOwnership({ pmt: 1000, strata: 0, insuranceAnnual: 1200, lifeMonthly: 0, upkeepAnnual: 0 });
ok('ownership: an entered zero is a fact, not a gap', ownZeroStrata.complete === true);

const ownCondo = Core.monthlyOwnership({ pmt: 1000, strata: 500, insuranceAnnual: 2400, lifeMonthly: 0,
                                         upkeepAnnual: 0, strataIncludesInsurance: true });
near('ownership: insurance inside strata is not charged twice', ownCondo.total, 1500, 0.01);

/* ---------------------------------------------------------- affordability --- */
group('Affordability');

const settings = { downPct: 15, rate: 7.25, term: 25, ptype: 'home', status: 'standard',
                   insPct: 1, upkeepPct: 1, strata: 0, life: 0, payInsuranceAtClose: true };

const bNone = Core.budgets({}, settings);
ok('budgets: nothing entered means no budget at all',
   bNone.lending === null && bNone.comfortable === null && bNone.cash === null && bNone.limitedBy === null);

const bIncome = Core.budgets({ grossMonthly: 15000 }, settings);
ok('budgets: income alone gives a lending estimate only',
   bIncome.lending > 0 && bIncome.comfortable === null && bIncome.cash === null);
ok('budgets: the lending estimate respects the debt-service room',
   Core.purchase(bIncome.lending, settings).pmt <= 15000 * 0.33 + 1,
   `pmt ${Core.purchase(bIncome.lending, settings).pmt}`);

const bDebts = Core.budgets({ grossMonthly: 15000, debtsMonthly: 1200 }, settings);
ok('budgets: existing debts reduce the lending estimate', bDebts.lending < bIncome.lending,
   `${bDebts.lending} vs ${bIncome.lending}`);

const bCash = Core.budgets({ cashAvailable: 120000 }, settings);
ok('budgets: cash alone gives a cash budget only',
   bCash.cash > 0 && bCash.lending === null && bCash.comfortable === null);
ok('budgets: cash budget stays inside the cash available',
   Core.purchase(bCash.cash, settings).cashToClose <= 120000 + 1,
   `cash to close ${Core.purchase(bCash.cash, settings).cashToClose}`);

const bReserve = Core.budgets({ cashAvailable: 120000, cashReserve: 20000 }, settings);
ok('budgets: a retained reserve lowers the cash budget', bReserve.cash < bCash.cash,
   `${bReserve.cash} vs ${bCash.cash}`);
ok('budgets: the reserve really is left untouched',
   Core.purchase(bReserve.cash, settings).cashToClose <= 100000 + 1);

const bBoth = Core.budgets({ grossMonthly: 15000, cashAvailable: 120000 }, settings);
ok('budgets: the binding constraint is named', bBoth.limitedBy === 'cash' || bBoth.limitedBy === 'lending');
near('budgets: the maximum is the lower of the two', bBoth.max, Math.min(bBoth.lending, bBoth.cash), 1);

const bSpend = Core.budgets({ takeHomeMonthly: 9000, livingCosts: 3000, savingsTarget: 500 }, settings);
ok('budgets: a comfortable budget comes from take-home spending', bSpend.comfortable > 0);
ok('budgets: comfortable budget keeps ownership inside the spare money',
   Core.purchase(bSpend.comfortable, settings).ownership.total <= 9000 - 3000 - 500 + 1);

const bBroke = Core.budgets({ takeHomeMonthly: 3000, livingCosts: 3200 }, settings);
near('budgets: nothing spare means nothing affordable', bBroke.comfortable, 0, 0);

// the solver must not step over a duty cliff
const bCliff = Core.budgets({ cashAvailable: 130000 }, { ...settings, status: 'first' });
const atCliff = Core.purchase(bCliff.cash, { ...settings, status: 'first' });
ok('budgets: the solver respects the concession cliff', atCliff.cashToClose <= 130000 + 1,
   `price ${bCliff.cash} needs ${Math.round(atCliff.cashToClose)}`);

/* ------------------------------------------------------------------ fit --- */
group('How a property fits');

const fitNothing = Core.fit(700000, {}, settings);
ok('fit: with nothing entered, nothing is claimed',
   fitNothing.incomeChecked === false && fitNothing.cashChecked === false
   && fitNothing.monthly === null && fitNothing.cash === null);

const fitIncomeOnly = Core.fit(500000, { grossMonthly: 15000 }, settings);
ok('fit: income entered checks the monthly side only',
   fitIncomeOnly.incomeChecked === true && fitIncomeOnly.cashChecked === false);

const fitCashOnly = Core.fit(500000, { cashAvailable: 50000 }, settings);
ok('fit: cash entered checks the cash side only',
   fitCashOnly.cashChecked === true && fitCashOnly.incomeChecked === false);
ok('fit: a shortfall is quantified', fitCashOnly.cashShortfall > 0,
   String(fitCashOnly.cashShortfall));

const fitBoth = Core.fit(400000, { grossMonthly: 15000, cashAvailable: 200000 }, settings);
ok('fit: both entered, both checked and both pass',
   fitBoth.monthly === 'within' && fitBoth.cash === 'within');

/* ------------------------------------------------------------- currency --- */
group('Currency');

near('currency: US$ to CI$ at 0.82', Core.toKyd(100000, 'USD', 0.82), 82000);
near('currency: a round trip returns the same amount',
     Core.fromKyd(Core.toKyd(123456, 'USD', 0.82), 'USD', 0.82), 123456, 0.01);
near('currency: CI$ is left alone', Core.toKyd(100000, 'KYD', 0.82), 100000);
const dutyKyd = Core.transferDuty(Core.toKyd(1000000, 'USD', 0.82), 'home', 'standard', false).amount;
near('currency: duty is charged on the CI$ amount', dutyKyd, 820000 * 0.075, 1);

/* ------------------------------------------------------- odd inputs ------- */
group('Blank, negative and out-of-range inputs');

ok('guards: a blank price produces no NaN',
   isFinite(Core.purchase(null, settings).cashToClose));
ok('guards: a negative price is treated as none',
   Core.purchase(-500000, settings).loan === 0);
const depositAll = Core.purchase(500000, { ...settings, downPct: 100 });
ok('guards: a 100% deposit leaves no loan and no mortgage duty',
   depositAll.loan === 0 && depositAll.closing.mortgageDuty.amount === 0);
const depositOver = Core.purchase(500000, { ...settings, downIsAmount: true, downAmount: 800000 });
ok('guards: a deposit larger than the price is capped at the price',
   depositOver.down === 500000 && depositOver.loan === 0);
ok('guards: every purchase figure is finite',
   [Core.purchase(0, settings), Core.purchase(1e9, settings)]
     .every(p => isFinite(p.cashToClose) && isFinite(p.pmt) && isFinite(p.ownership.total)));

/* ---------------------------------------------------------------- report --- */
console.log(`\n${pass} passed, ${fail} failed`);
if (fail) {
  console.log('\nFailures:');
  failures.forEach(f => console.log('  ✗ ' + f));
  process.exit(1);
}
