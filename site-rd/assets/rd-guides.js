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
