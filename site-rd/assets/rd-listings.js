/* The Listings page: filter, sort, page and compare, on the real scraped data.

   Cards are built here rather than server-side because 873 listings is far too
   much markup to ship and every control has to work on the client anyway. The
   markup matches redesign.py's listing_card exactly, so the homepage's static
   cards and these are the same component.

   Stamp duty in the comparison comes from core.js, the engine the live site
   already uses and tests, so the figure here and in the calculator agree. */
(function (w, d) {
  'use strict';

  var CMP_KEY = 'cmc.compare';
  var FAV_KEY = 'cmc.favourites';
  var PAGE = 12;
  var MAX_COMPARE = 4;

  var all = [];
  var view = [];
  var shown = PAGE;
  var compare = [];          // snapshots, so a choice survives paging and reload
  var favourites = {};       // urls the visitor has starred, kept like compare

  var grid, countEl, moreWrap, moreBtn, bar, barCount, panel, table;

  /* ---------------------------------------------------------------- helpers */
  function money(n) {
    var v = CMC.inputs.get();
    return CMC.money(Math.round(n * v.fx), v.symbol);
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  /* Agencies type their titles by hand: pipes become commas, a bracket gets the
     space it is missing, doubled spaces collapse. The wording is left alone. */
  function cleanTitle(t) {
    return String(t || '').trim()
      // en and em dashes are ruled out of rendered text; a plain hyphen matches
      // the " - " most other titles already use
      .replace(/[\u2013\u2014]/g, ' - ')
      .replace(/\|/g, ', ')
      .replace(/\s*\(/g, ' (')
      .replace(/\s{2,}/g, ' ')
      .replace(/\s+,/g, ',')
      .trim();
  }

  function districtOf(area) {
    var a = (area || '').toLowerCase();
    if (a.indexOf('little cayman') >= 0) return 'Little Cayman';
    if (a.indexOf('cayman brac') >= 0 || /\bbrac\b/.test(a)) return 'Cayman Brac';
    if (a.indexOf('seven mile') >= 0 || a.indexOf('w bay bch') >= 0) return 'Seven Mile Beach';
    if (a.indexOf('west bay') >= 0 || a.indexOf('w bay') >= 0) return 'West Bay';
    if (/george town|south sound|prospect|spotts|red bay/.test(a)) return 'George Town';
    if (/bodden town|savannah|lower valley|newlands|breakers|pedro/.test(a)) return 'Bodden Town';
    if (/east end|high rock|colliers/.test(a)) return 'East End';
    if (/north side|rum point|cayman kai|kaibo/.test(a)) return 'North Side';
    return 'Elsewhere';
  }
  function islandOf(area) {
    var dd = districtOf(area);
    return dd === 'Cayman Brac' ? 'brac' : dd === 'Little Cayman' ? 'little' : 'grand';
  }
  function monthlyFor(l) {
    var v = CMC.inputs.get();
    return CMC.payment(l.price_kyd * (1 - v.deposit / 100), v.rate, v.term);
  }
  function dutyFor(l) {
    // The engine the calculator uses, so the two never disagree. Standard rate:
    // the listings page does not know the visitor's concession status.
    if (!w.Core || !Core.transferDuty) return null;
    return Core.transferDuty(l.price_kyd, l.ptype === 'land' ? 'land' : 'home',
                             'standard', false, islandOf(l.location)).amount;
  }
  function icon(name, size) {
    var P = w.RD_ICON_PATHS || {};
    var paths = P[name] || [];
    var out = '';
    for (var i = 0; i < paths.length; i++) out += '<path d="' + paths[i] + '"/>';
    return '<svg class="cmc-icon" width="' + size + '" height="' + size + '" viewBox="0 0 24 24"' +
      ' fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"' +
      ' stroke-linejoin="round" aria-hidden="true">' + out + '</svg>';
  }

  var PLACEHOLDER_ICON = '';   // filled once the icon paths are available

  /* ------------------------------------------------------------------ card */
  function card(l) {
    var id = l.url;
    var comparing = compare.some(function (c) { return c.url === id; });
    var ext = /^https?:\/\//i.test(l.url || '');
    // An agency photo can 404 or be blocked; swap in the placeholder rather
    // than leaving a broken image in the frame.
    var media = l.image
      ? '<img src="' + esc(l.image) + '" alt="" loading="lazy" referrerpolicy="no-referrer"' +
        ' onerror="this.parentNode.insertAdjacentHTML(\'afterbegin\',' +
        ' \'<div class=&quot;cmc-listing__placeholder&quot;>' + PLACEHOLDER_ICON +
        '</div>\'); this.remove();">'
      : '<div class="cmc-listing__placeholder">' + icon('house', 32) + '</div>';
    media += '<span class="cmc-badge cmc-badge--navy cmc-listing__badge">For sale</span>';
    var faved = !!favourites[id];
    media += '<button type="button" class="cmc-listing__fav' +
      (faved ? ' cmc-listing__fav--on' : '') + '" data-fav="' + esc(id) + '"' +
      ' aria-pressed="' + (faved ? 'true' : 'false') + '"' +
      ' aria-label="' + (faved ? 'Remove from saved' : 'Save listing') + '">' +
      icon('heart', 16) + '</button>';
    media += '<button type="button" class="cmc-listing__compare' +
      (comparing ? ' cmc-listing__compare--on' : '') + '" data-cmp="' + esc(id) + '"' +
      ' aria-pressed="' + (comparing ? 'true' : 'false') + '">' +
      '<span class="cmc-listing__compare-box">' + (comparing ? icon('check', 12) : '') + '</span>' +
      (comparing ? 'Comparing' : 'Compare') + '</button>';

    var meta = '';
    if (l.beds != null) meta += '<span>' + icon('bed-double', 14) + l.beds + ' Bed' + (l.beds === 1 ? '' : 's') + '</span>';
    if (l.baths != null) meta += '<span>' + icon('bath', 14) + l.baths + ' Bath' + (l.baths === 1 ? '' : 's') + '</span>';
    if (l.sqft != null) meta += '<span>' + icon('ruler', 14) + Math.round(l.sqft).toLocaleString('en-US') + ' Sq Ft</span>';

    var agency = (l.sources && l.sources[0]) || l.source || '';
    return '<a class="cmc-listing" href="' + esc(l.url) + '"' +
      (ext ? ' target="_blank" rel="noopener"' : '') +
      ' aria-label="' + esc(cleanTitle(l.title)) + ': view on the agent\'s site">' +
      '<div class="cmc-listing__media">' + media + '</div>' +
      '<div class="cmc-listing__body">' +
      '<div class="cmc-listing__price">' + esc(money(l.price_kyd)) + '</div>' +
      '<div class="cmc-listing__address">' + esc(cleanTitle(l.title) || 'Property for sale') + '</div>' +
      (l.location ? '<div class="cmc-listing__locality">' + esc(cleanTitle(l.location)) + '</div>' : '') +
      '<div class="cmc-listing__monthly">' + icon('calculator', 14) + 'From <strong>' +
      esc(money(monthlyFor(l))) + '</strong>/mo</div>' +
      '</div>' +
      (meta ? '<div class="cmc-listing__meta">' + meta + '</div>' : '') +
      '<div class="cmc-listing__agency"><span>Listed by ' + esc(agency) + '</span>' +
      (ext ? '<span class="cmc-listing__ext">View on agent\'s site' + icon('external-link', 12) + '</span>' : '') +
      '</div>' +
      '<div class="rd-listing-actions">' +
        '<button type="button" class="cmc-btn cmc-btn--secondary cmc-btn--sm rd-use-calc"' +
        ' data-use-price="' + Math.round(l.price_kyd) + '"' +
        ' data-use-island="' + islandOf(l.location) + '"' +
        ' data-use-ptype="' + (l.ptype === 'land' ? 'land' : 'home') + '">' +
        icon('calculator', 16) + '<span>Use in calculator</span></button>' +
      '</div></a>';
  }

  /* --------------------------------------------------------------- filters */
  function val(id) { var el = d.getElementById(id); return el ? el.value : ''; }

  /* Acreage, on a stepped scale. Half the listings with a figure are under
     0.4 acres and the largest is 100, so a linear track would put the median
     at 0.4% along it. Index 0 means no minimum; the last index means no
     maximum, so the handful of large parcels stay reachable. */
  var ACRE_STOPS = [0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1, 1.5, 2, 3, 5, 10, 25, 50, null];
  var ACRE_TOP = ACRE_STOPS.length - 1;

  function acreLabel(i) {
    var v = ACRE_STOPS[i];
    return v === null ? 'any' : String(v);
  }

  function acreUnit(v) { return v === 1 ? ' acre' : ' acres'; }

  function acreRange() {
    var lo = d.getElementById('fAcreMin'), hi = d.getElementById('fAcreMax');
    if (!lo || !hi) return null;
    var a = parseInt(lo.value, 10), b = parseInt(hi.value, 10);
    if (a > b) { var t = a; a = b; b = t; }
    return { i: a, j: b, min: ACRE_STOPS[a], max: ACRE_STOPS[b],
             active: a > 0 || b < ACRE_TOP };
  }

  function paintAcres() {
    var r = acreRange();
    if (!r) return;
    var fill = d.getElementById('fAcreFill'), out = d.getElementById('fAcreOut');
    if (fill) {
      fill.style.left = (r.i / ACRE_TOP * 100) + '%';
      fill.style.width = ((r.j - r.i) / ACRE_TOP * 100) + '%';
    }
    if (out) {
      out.textContent = !r.active ? 'Any'
        : r.max === null ? acreLabel(r.i) + '+ acres'
        : r.i === r.j ? acreLabel(r.i) + acreUnit(r.min)
        : acreLabel(r.i) + ' to ' + acreLabel(r.j) + acreUnit(r.max);
    }
  }

  /* Land has no bedroom or bathroom count: 335 of the 336 land listings carry
     neither. Selecting it zeroes both and takes them out of play rather than
     leaving two controls that would filter the whole category away. */
  function syncRooms() {
    var isLand = val('fType') === 'land';
    ['fBeds', 'fBaths'].forEach(function (id) {
      var el = d.getElementById(id);
      if (!el) return;
      if (isLand) {
        if (el.dataset.was === undefined) el.dataset.was = el.value;
        el.value = '0';
        el.disabled = true;
      } else if (el.disabled) {
        el.disabled = false;
        el.value = el.dataset.was || '';
        delete el.dataset.was;
      }
    });
  }

  function apply() {
    var district = val('fDistrict'), type = val('fType');
    // read through CMC.readNum: these are money fields, and once one loses
    // focus "500,000" parses as 500, so the minimum silently vanished on the
    // next re-sort
    var min = CMC.readNum('fMin'), max = CMC.readNum('fMax');
    if (min === null) min = NaN;
    if (max === null) max = NaN;
    var beds = val('fBeds'), baths = val('fBaths');
    var acres = acreRange();
    var v = CMC.inputs.get();
    // the price boxes are in the display currency
    if (!isNaN(min)) min = min / v.fx;
    if (!isNaN(max)) max = max / v.fx;

    view = all.filter(function (l) {
      if (!(l.price_kyd > 0)) return false;
      if (district && districtOf(l.location) !== district) return false;
      if (type && l.ptype !== type) return false;
      if (!isNaN(min) && l.price_kyd < min) return false;
      if (!isNaN(max) && l.price_kyd > max) return false;
      if (!roomsOk(l.beds, beds)) return false;
      if (!roomsOk(l.baths, baths)) return false;
      if (acres && acres.active) {
        // no figure means it cannot be shown to be in range, so it is out; the
        // hint under the slider says this before anyone narrows
        if (!(l.acres > 0)) return false;
        if (acres.min !== null && l.acres < acres.min) return false;
        if (acres.max !== null && l.acres > acres.max) return false;
      }
      return true;
    });

    var sort = val('fSort');
    view.sort(function (a, b) {
      if (sort === 'price-asc') return a.price_kyd - b.price_kyd;
      if (sort === 'price-desc') return b.price_kyd - a.price_kyd;
      if (sort === 'size') return (b.sqft || 0) - (a.sqft || 0);
      return String(b.scraped_at || '').localeCompare(String(a.scraped_at || ''));
    });
    shown = PAGE;
    render();
  }

  /* "0" is an exact match: land carries null, not 0, so both count as none.
     Every other value is a floor. */
  function roomsOk(have, want) {
    if (want === '') return true;
    var n = parseFloat(want);
    if (n === 0) return !(have > 0);
    return have >= n;
  }

  function bindCards() {
    // Bound directly rather than delegated: the compare control sits inside the
    // card's anchor, so if interception ever misses, the visitor is thrown out to
    // the agency's site mid-task. A handler on the button itself cannot miss.
    if (w.CMC && CMC.bindUseInCalculator) CMC.bindUseInCalculator(grid);
    [].slice.call(grid.querySelectorAll('[data-fav]')).forEach(function (b) {
      b.addEventListener('click', function (ev) {
        ev.preventDefault(); ev.stopPropagation();
        toggleFav(b.getAttribute('data-fav'), b);
      });
    });
    [].slice.call(grid.querySelectorAll('[data-cmp]')).forEach(function (b) {
      b.addEventListener('click', function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        toggleCompare(b.getAttribute('data-cmp'), b);
      });
    });
  }

  function render() {
    var slice = view.slice(0, shown);
    grid.innerHTML = slice.map(card).join('');
    bindCards();
    countEl.textContent = view.length
      ? view.length.toLocaleString('en-US') + ' listing' + (view.length === 1 ? '' : 's') +
        ', showing ' + slice.length
      : 'No listings match these filters. Try a wider price range or another district.';
    moreWrap.hidden = slice.length >= view.length;
    renderCompare();
  }

  /* --------------------------------------------------------------- compare */
  function loadFav() {
    try { favourites = JSON.parse(w.localStorage.getItem(FAV_KEY) || '{}') || {}; }
    catch (e) { favourites = {}; }
    if (typeof favourites !== 'object' || !favourites) favourites = {};
  }
  function toggleFav(url, btn) {
    if (favourites[url]) delete favourites[url]; else favourites[url] = 1;
    try { w.localStorage.setItem(FAV_KEY, JSON.stringify(favourites)); } catch (e) {}
    var on = !!favourites[url];
    btn.classList.toggle('cmc-listing__fav--on', on);
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    btn.setAttribute('aria-label', on ? 'Remove from saved' : 'Save listing');
  }

  function loadCompare() {
    try { compare = JSON.parse(w.localStorage.getItem(CMP_KEY) || '[]') || []; }
    catch (e) { compare = []; }
    if (!Array.isArray(compare)) compare = [];
  }
  function saveCompare() {
    try { w.localStorage.setItem(CMP_KEY, JSON.stringify(compare)); } catch (e) {}
  }
  function toggleCompare(url, btn) {
    var i = -1, k;
    for (k = 0; k < compare.length; k++) if (compare[k].url === url) i = k;
    if (i >= 0) compare.splice(i, 1);
    else {
      if (compare.length >= MAX_COMPARE) return;
      var l = null;
      for (k = 0; k < all.length; k++) if (all[k].url === url) l = all[k];
      if (!l) return;
      compare.push(l);            // a snapshot, so paging and filtering cannot lose it
    }
    saveCompare();
    // Update just this button and the comparison, never the whole grid: a full
    // re-render would throw away the focus the visitor is standing on.
    if (btn) paintCompareButton(btn, compare.some(function (c) { return c.url === url; }));
    renderCompare();
  }

  function paintCompareButton(btn, on) {
    btn.classList.toggle('cmc-listing__compare--on', on);
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    btn.innerHTML = '<span class="cmc-listing__compare-box">' + (on ? icon('check', 12) : '') +
      '</span>' + (on ? 'Comparing' : 'Compare');
  }

  var ROWS = [
    ['Price', function (l) { return money(l.price_kyd); }, function (l) { return l.price_kyd; }, 'low'],
    ['Estimated monthly', function (l) { return money(monthlyFor(l)); }, monthlyFor, 'low'],
    ['Down payment', function (l) {
      return money(l.price_kyd * CMC.inputs.get().deposit / 100);
    }, function (l) { return l.price_kyd * CMC.inputs.get().deposit / 100; }, 'low'],
    ['Stamp duty', function (l) { var x = dutyFor(l); return x == null ? 'Not known' : money(x); },
      dutyFor, 'low'],
    ['Beds', function (l) { return l.beds == null ? 'Not listed' : String(l.beds); },
      function (l) { return l.beds; }, 'high'],
    ['Baths', function (l) { return l.baths == null ? 'Not listed' : String(l.baths); },
      function (l) { return l.baths; }, 'high'],
    ['Size', function (l) {
      return l.sqft == null ? 'Not listed' : Math.round(l.sqft).toLocaleString('en-US') + ' sq ft';
    }, function (l) { return l.sqft; }, 'high'],
    ['Price per sq ft', function (l) {
      return l.sqft ? money(l.price_kyd / l.sqft) : 'Not known';
    }, function (l) { return l.sqft ? l.price_kyd / l.sqft : null; }, 'low'],
    ['Status', function (l) { return l.status || 'For sale'; }, null, null],
    ['District', function (l) { return districtOf(l.location); }, null, null]
  ];

  function renderCompare() {
    var n = compare.length;
    bar.hidden = n === 0;
    d.body.classList.toggle('rd-has-compare', n > 0);
    barCount.textContent = n + ' selected' + (n >= MAX_COMPARE ? ' (max)' : '');
    panel.hidden = n < 2;
    if (n < 2) { table.innerHTML = ''; return; }

    var head = '<thead><tr><th></th>' + compare.map(function (l) {
      return '<th>' + esc(l.title || 'Listing') + '<br><span style="font-size:12px;' +
        'line-height:16px;font-weight:500;color:var(--ink-500)">' +
        esc(l.location || '') + ' · listed by ' + esc((l.sources && l.sources[0]) || l.source || '') +
        '</span></th>';
    }).join('') + '</tr></thead>';

    var body = '<tbody>' + ROWS.map(function (r) {
      var label = r[0], text = r[1], num = r[2], best = r[3];
      var bestVal = null;
      if (num && best) {
        compare.forEach(function (l) {
          var x = num(l);
          if (x == null || isNaN(x)) return;
          if (bestVal == null) bestVal = x;
          else bestVal = best === 'low' ? Math.min(bestVal, x) : Math.max(bestVal, x);
        });
      }
      return '<tr><th>' + esc(label) + '</th>' + compare.map(function (l) {
        var x = num ? num(l) : null;
        var isBest = bestVal != null && x != null && !isNaN(x) && x === bestVal && compare.length > 1;
        return '<td class="' + (isBest ? 'rd-best' : '') + '">' + esc(text(l)) + '</td>';
      }).join('') + '</tr>';
    }).join('') + '</tbody>';

    var links = '<tr><th></th>' + compare.map(function (l) {
      return '<td><a class="cmc-btn cmc-btn--secondary cmc-btn--sm" href="' + esc(l.url) +
        '" target="_blank" rel="noopener"><span>View on agent\'s site</span>' +
        icon('external-link', 16) + '</a></td>';
    }).join('') + '</tr>';

    table.innerHTML = head + body + '<tfoot>' + links + '</tfoot>';
  }

  /* ------------------------------------------------------------------ boot */
  function start() {
    grid = d.getElementById('rdGrid');
    if (!grid) return;
    countEl = d.getElementById('rdCount');
    moreWrap = d.getElementById('rdMoreWrap');
    moreBtn = d.getElementById('rdMore');
    bar = d.getElementById('rdCmpBar');
    barCount = d.getElementById('rdCmpCount');
    panel = d.getElementById('compare');
    table = d.getElementById('rdCmpTable');

    PLACEHOLDER_ICON = icon('house', 32).replace(/"/g, '&quot;');

    loadFav();
    loadCompare();

    ['fDistrict', 'fType', 'fMin', 'fMax', 'fBeds', 'fBaths', 'fSort'].forEach(function (id) {
      var el = d.getElementById(id);
      if (el) el.addEventListener('input', apply);
      if (el && el.tagName === 'SELECT') el.addEventListener('change', apply);
    });
    var fType = d.getElementById('fType');
    if (fType) fType.addEventListener('change', function () { syncRooms(); apply(); });
    ['fAcreMin', 'fAcreMax'].forEach(function (id) {
      var el = d.getElementById(id);
      if (!el) return;
      el.addEventListener('input', function () { paintAcres(); apply(); });
    });
    syncRooms();
    paintAcres();
    var form = d.getElementById('rdFilters');
    if (form) form.addEventListener('submit', function (ev) { ev.preventDefault(); apply(); });
    if (moreBtn) moreBtn.addEventListener('click', function () { shown += PAGE; render(); });

    function clear() { compare = []; saveCompare(); render(); }
    var c1 = d.getElementById('rdCmpClear'), c2 = d.getElementById('rdCmpClose');
    if (c1) c1.addEventListener('click', clear);
    if (c2) c2.addEventListener('click', clear);

    // Re-price everything when the shared deposit, rate, term or currency moves.
    CMC.inputs.subscribe(render);

    fetch('/listings.json').then(function (r) { return r.json(); }).then(function (data) {
      all = (data.listings || []).filter(function (l) { return l.price_kyd > 0; });
      // ?max= and monthly= come from the calculator's "see homes that fit" link
      var q = new URLSearchParams(location.search);
      if (q.get('max')) { var m = d.getElementById('fMax'); if (m) m.value = q.get('max'); }
      apply();
    }).catch(function () {
      countEl.textContent = 'The listings could not be loaded. Reload the page to try again.';
      moreWrap.hidden = true;
    });
  }

  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', start);
  else start();
})(window, document);
