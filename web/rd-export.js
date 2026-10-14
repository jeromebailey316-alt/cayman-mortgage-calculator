/* Excel, PDF and Print for the mortgage calculator (HANDOFF 5.2).

   SheetJS and jsPDF are fetched on first use rather than on page load. Together
   they are several hundred kilobytes, which would undo the Lighthouse target in
   section 7 for a feature most visitors never touch. A spinner-free wait is
   fine: the note says what is happening, and a failure falls back to CSV rather
   than leaving the button dead. */
(function (w, d) {
  'use strict';

  var XLSX_SRC = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';
  var JSPDF_SRC = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';

  function el(id) { return d.getElementById(id); }
  function note(msg) { var n = el('rExportNote'); if (n) n.textContent = msg || ''; }

  var loaded = {};
  function load(src) {
    if (loaded[src]) return loaded[src];
    loaded[src] = new Promise(function (resolve, reject) {
      var s = d.createElement('script');
      s.src = src;
      s.onload = resolve;
      s.onerror = function () { loaded[src] = null; reject(new Error('could not load ' + src)); };
      d.head.appendChild(s);
    });
    return loaded[src];
  }

  /* The figures, read back from the page so the file always matches what is
     on screen rather than recomputing and risking a quiet divergence. */
  function snapshot() {
    var v = CMC.inputs.get();
    var price = v.price, down = price * v.deposit / 100;
    var loan = Math.max(0, price - down);
    var extra = parseFloat((el('cExtra') || {}).value) || 0;
    var am = Core.amortise({ loan: loan, rate: v.rate / 100, years: v.term, extra: extra / v.fx });
    var close = Core.closingCosts({
      price: price, loan: loan, ptype: el('cPtype').value,
      status: el('cStatus').value, joint: el('cBuyer').value === 'joint',
      location: el('cIsland').value,
      legalPct: parseFloat(el('cLegal').value) || 0,
      bankPct: parseFloat(el('cBank').value) || 0,
      valuation: parseFloat(el('cValFee').value) || 0, inspection: 0
    });
    return { v: v, price: price, down: down, loan: loan, am: am, close: close,
             monthly: el('rMonthly').textContent, cash: el('rCash').textContent };
  }

  function money(x, s) { return CMC.money(Math.round(x * s.v.fx), s.v.symbol); }

  /* ------------------------------------------------------------------ Excel */
  function rowsForSchedule(s) {
    var out = [['Month', 'Payment', 'Principal', 'Interest', 'Extra', 'Balance']];
    s.am.rows.forEach(function (r) {
      out.push([r.m,
                Math.round(r.pay * s.v.fx), Math.round(r.p * s.v.fx),
                Math.round(r.i * s.v.fx),
                Math.round(Math.max(0, r.pay - s.am.pmt) * s.v.fx),
                Math.round(r.bal * s.v.fx)]);
    });
    return out;
  }
  function rowsForSummary(s) {
    return [
      ['Cayman Mortgage Calculator', ''],
      ['Currency', s.v.currency],
      ['Purchase price', Math.round(s.price * s.v.fx)],
      ['Deposit', Math.round(s.down * s.v.fx)],
      ['Deposit percentage', s.v.deposit],
      ['Loan', Math.round(s.loan * s.v.fx)],
      ['Interest rate', s.v.rate],
      ['Term in years', s.v.term],
      ['Monthly cost of owning', s.monthly],
      ['Stamp duty on the transfer', Math.round(s.close.transferDuty.amount * s.v.fx)],
      ['Stamp duty on the mortgage', Math.round(s.close.mortgageDuty.amount * s.v.fx)],
      ['Cash to close', s.cash],
      ['Total interest over the term', Math.round(s.am.totalInterest * s.v.fx)],
      ['', ''],
      ['Estimates only, not financial or legal advice.', '']
    ];
  }

  function csvFallback(s) {
    var all = rowsForSummary(s).concat([['', '']], rowsForSchedule(s));
    var csv = all.map(function (r) {
      return r.map(function (c) {
        var t = String(c == null ? '' : c);
        return /[",\n]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
      }).join(',');
    }).join('\n');
    download(new Blob([csv], { type: 'text/csv' }),
             'cayman-mortgage-schedule-' + Math.round(s.price) + '-' + s.v.currency + '.csv');
    note('Excel could not be loaded, so the schedule was saved as CSV instead.');
  }

  function download(blob, name) {
    var url = URL.createObjectURL(blob);
    var a = d.createElement('a');
    a.href = url; a.download = name;
    d.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function excel() {
    var s = snapshot();
    note('Building the spreadsheet.');
    load(XLSX_SRC).then(function () {
      var wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(rowsForSummary(s)), 'Summary');
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(rowsForSchedule(s)), 'Schedule');
      XLSX.writeFile(wb, 'cayman-mortgage-schedule-' + Math.round(s.price) + '-' +
                     s.v.currency + '.xlsx');
      note('Saved. ' + s.am.rows.length + ' months of payments, in ' + s.v.currency + '.');
    }).catch(function () { csvFallback(s); });
  }

  /* -------------------------------------------------------------------- PDF */
  function pdf() {
    var s = snapshot();
    note('Building the PDF.');
    load(JSPDF_SRC).then(function () {
      var JsPDF = (w.jspdf && w.jspdf.jsPDF) || w.jsPDF;
      if (!JsPDF) throw new Error('jsPDF did not register');
      var doc = new JsPDF({ unit: 'pt', format: 'a4' });
      var W = doc.internal.pageSize.getWidth();
      var y = 0;

      doc.setFillColor(1, 21, 51); doc.rect(0, 0, W, 86, 'F');
      doc.setTextColor(255); doc.setFont('helvetica', 'bold'); doc.setFontSize(18);
      doc.text('Cayman Mortgage Calculator', 40, 40);
      doc.setFont('helvetica', 'normal'); doc.setFontSize(10);
      doc.text('Estimates only, not financial or legal advice.', 40, 62);
      y = 120;

      function section(title, pairs) {
        doc.setTextColor(1, 21, 51); doc.setFont('helvetica', 'bold'); doc.setFontSize(12);
        doc.text(title, 40, y); y += 18;
        doc.setFont('helvetica', 'normal'); doc.setFontSize(10); doc.setTextColor(60);
        pairs.forEach(function (p) {
          doc.text(String(p[0]), 40, y);
          doc.text(String(p[1]), W - 40, y, { align: 'right' });
          y += 16;
        });
        y += 10;
      }

      section('Property and buyer', [
        ['Purchase price', money(s.price, s)],
        ['Island', el('cIsland').options[el('cIsland').selectedIndex].text],
        ['Property type', el('cPtype').options[el('cPtype').selectedIndex].text],
        ['Stamp duty status', el('cStatus').options[el('cStatus').selectedIndex].text]
      ]);
      section('Mortgage', [
        ['Deposit', money(s.down, s) + ' (' + s.v.deposit + '%)'],
        ['Loan', money(s.loan, s)],
        ['Rate', s.v.rate + '%'],
        ['Term', s.v.term + ' years'],
        ['Monthly cost of owning', s.monthly]
      ]);
      section('Cash and running costs', [
        ['Stamp duty on the transfer', money(s.close.transferDuty.amount, s)],
        ['Stamp duty on the mortgage', money(s.close.mortgageDuty.amount, s)],
        ['Cash to close', s.cash],
        ['Total interest over the term', money(s.am.totalInterest, s)]
      ]);

      var years = [];
      for (var yy = 1; yy <= Math.min(5, Math.ceil(s.am.months / 12)); yy++) {
        var pay = 0, bal = 0;
        for (var i = (yy - 1) * 12; i < yy * 12 && i < s.am.rows.length; i++) {
          pay += s.am.rows[i].pay; bal = s.am.rows[i].bal;
        }
        years.push(['Year ' + yy, money(pay, s) + ' paid, ' + money(bal, s) + ' left']);
      }
      section('The first five years', years);

      doc.setFontSize(8); doc.setTextColor(120);
      doc.text('Rates and fees change. Confirm every figure with your attorney and lender ' +
               'before you commit.', 40, doc.internal.pageSize.getHeight() - 40);

      doc.save('cayman-mortgage-summary-' + Math.round(s.price) + '-' + s.v.currency + '.pdf');
      note('Saved.');
    }).catch(function () {
      note('The PDF could not be built. Use Print instead, and choose Save as PDF.');
    });
  }

  function start() {
    var x = el('rXlsx'), pb = el('rPdf'), pr = el('rPrint');
    if (x) x.addEventListener('click', excel);
    if (pb) pb.addEventListener('click', pdf);
    if (pr) pr.addEventListener('click', function () { w.print(); });
  }
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', start);
  else start();
})(window, document);
