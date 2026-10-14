/* @ds-bundle: {"format":4,"namespace":"CMC","components":[{"name":"Button"},{"name":"Input"},{"name":"Select"},{"name":"PillTabs"},{"name":"Badge"},{"name":"Icon"},{"name":"ListingCard"},{"name":"CalculatorPanel"},{"name":"Header"},{"name":"Footer"},{"name":"Byline"},{"name":"BackToTop"}]} */
(function () {
  var React = window.React;
  var h = React.createElement;

  function cx() {
    var out = [];
    for (var i = 0; i < arguments.length; i++) if (arguments[i]) out.push(arguments[i]);
    return out.join(' ');
  }

  /* ---------- Shared inputs: price, deposit, rate, term, one value site-wide ---------- */
  var INPUT_KEY = 'cmc.inputs';
  var INPUT_DEFAULTS = { price: 650000, deposit: 10, rate: 7.75, term: 25, currency: 'KYD' }; // rate: KYD prime 7.00% + 0.75 (see Calculator page hint)
  var USD_PER_KYD = 1.20; // fixed peg: CI$1 = US$1.20
  function norm(k, v) { return k === 'currency' ? (v === 'USD' ? 'USD' : 'KYD') : Number(v); }
  function valid(k, v) { return k === 'currency' ? (v === 'USD' || v === 'KYD') : (v != null && !isNaN(v)); }
  var inputListeners = [];
  function readInputs() { try { var raw = window.localStorage.getItem(INPUT_KEY); return raw ? JSON.parse(raw) : {}; } catch (e) { return {}; } }
  var inputMem = readInputs();
  function notifyInputs() { for (var i = 0; i < inputListeners.length; i++) { try { inputListeners[i](inputs.get()); } catch (e) {} } }
  var inputs = {
    key: INPUT_KEY,
    defaults: INPUT_DEFAULTS,
    usdPerKyd: USD_PER_KYD,
    get: function (fallback) {
      var o = {}, k;
      for (k in INPUT_DEFAULTS) o[k] = INPUT_DEFAULTS[k];
      if (fallback) for (k in fallback) if (valid(k, fallback[k])) o[k] = norm(k, fallback[k]);
      for (k in inputMem) if (valid(k, inputMem[k])) o[k] = norm(k, inputMem[k]);
      o.fx = o.currency === 'USD' ? USD_PER_KYD : 1; o.symbol = o.currency === 'USD' ? 'US$' : 'CI$';
      return o;
    },
    set: function (partial) {
      var changed = false, k;
      for (k in partial) if (k in INPUT_DEFAULTS && valid(k, partial[k]) && inputMem[k] !== norm(k, partial[k])) { inputMem[k] = norm(k, partial[k]); changed = true; }
      if (!changed) return;
      try { window.localStorage.setItem(INPUT_KEY, JSON.stringify(inputMem)); } catch (e) {}
      notifyInputs();
    },
    reset: function () { inputMem = {}; try { window.localStorage.removeItem(INPUT_KEY); } catch (e) {} notifyInputs(); },
    subscribe: function (fn) { inputListeners.push(fn); return function () { var i = inputListeners.indexOf(fn); if (i >= 0) inputListeners.splice(i, 1); }; }
  };
  try { window.addEventListener('storage', function (e) { if (e.key === INPUT_KEY) { inputMem = readInputs(); notifyInputs(); } }); } catch (e) {}
  function useInputs(fallback) {
    var st = React.useState(inputs.get(fallback));
    React.useEffect(function () { return inputs.subscribe(function () { st[1](inputs.get(fallback)); }); }, []);
    return [st[0], inputs.set];
  }

  /* ---------- Icon: a small Lucide subset (ISC licence, lucide.dev), 24px grid, 1.5 stroke ---------- */
  var PATHS = {
    'house': ['M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8', 'M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'],
    'calculator': ['M6 2h12a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z', 'M8 6h8', 'M16 14v4', 'M16 10h.01', 'M12 10h.01', 'M8 10h.01', 'M12 14h.01', 'M8 14h.01', 'M12 18h.01', 'M8 18h.01'],
    'percent': ['M19 5 5 19', 'M6.5 9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z', 'M17.5 20a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z'],
    'landmark': ['M3 22h18', 'M6 18v-7', 'M10 18v-7', 'M14 18v-7', 'M18 18v-7', 'M12 2 20 7H4z'],
    'file-text': ['M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z', 'M14 2v4a2 2 0 0 0 2 2h4', 'M10 9H8', 'M16 13H8', 'M16 17H8'],
    'receipt': ['M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1z', 'M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8', 'M12 17.5v-11'],
    'map-pin': ['M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z', 'M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6z'],
    'bed-double': ['M2 20v-8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v8', 'M4 10V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v4', 'M12 4v6', 'M2 18h20'],
    'bath': ['M10 4 8 6', 'M17 19v2', 'M2 12h20', 'M7 19v2', 'M9 5 7.621 3.621A2.121 2.121 0 0 0 4 5v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5'],
    'ruler': ['M21.3 15.3a2.4 2.4 0 0 1 0 3.4l-2.6 2.6a2.4 2.4 0 0 1-3.4 0L2.7 8.7a2.41 2.41 0 0 1 0-3.4l2.6-2.6a2.41 2.41 0 0 1 3.4 0z', 'm14.5 12.5 2-2', 'm11.5 9.5 2-2', 'm8.5 6.5 2-2', 'm17.5 15.5 2-2'],
    'search': ['M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z', 'm21 21-4.3-4.3'],
    'heart': ['M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7z'],
    'arrow-right': ['M5 12h14', 'm12 5 7 7-7 7'],
    'chevron-down': ['m6 9 6 6 6-6'],
    'mail': ['M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z', 'm22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7'],
    'phone': ['M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z'],
    'shield-check': ['M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z', 'm9 12 2 2 4-4'],
    'trending-up': ['M22 7 13.5 15.5 8.5 10.5 2 17', 'M16 7h6v6'],
    'check': ['M20 6 9 17l-5-5'],
    'arrow-up': ['M12 19V5', 'm5 12 7-7 7 7'],
    'x': ['M18 6 6 18', 'm6 6 12 12'],
    'external-link': ['M15 3h6v6', 'M10 14 21 3', 'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6'],
    'menu': ['M4 12h16', 'M4 6h16', 'M4 18h16'],
    'info': ['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z', 'M12 16v-4', 'M12 8h.01']
  };
  function Icon(props) {
    var size = props.size || 24;
    var paths = PATHS[props.name] || [];
    return h('svg', {
      className: cx('cmc-icon', props.className), width: size, height: size, viewBox: '0 0 24 24', fill: 'none',
      stroke: 'currentColor', strokeWidth: props.strokeWidth || 1.5, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': 'true'
    }, paths.map(function (d, i) { return h('path', { key: i, d: d }); }));
  }

  /* ---------- Button ---------- */
  function Button(props) {
    var variant = props.variant || 'primary';
    var size = props.size || 'md';
    var Tag = props.href ? 'a' : 'button';
    var rest = {};
    for (var k in props) if (['variant', 'size', 'iconLeft', 'iconRight', 'children', 'className', 'block'].indexOf(k) < 0) rest[k] = props[k];
    if (!props.href && !rest.type) rest.type = 'button';
    rest.className = cx('cmc-btn', 'cmc-btn--' + variant, 'cmc-btn--' + size, props.block && 'cmc-btn--block', props.className);
    return h(Tag, rest,
      props.iconLeft ? h(Icon, { name: props.iconLeft, size: size === 'sm' ? 16 : 18 }) : null,
      h('span', null, props.children),
      props.iconRight ? h(Icon, { name: props.iconRight, size: size === 'sm' ? 16 : 18 }) : null);
  }

  /* ---------- Input / Select ---------- */
  function Field(props, control) {
    return h('label', { className: cx('cmc-field', props.error && 'cmc-field--error', props.className) },
      props.label ? h('span', { className: 'cmc-field__label' }, props.label) : null,
      h('span', { className: 'cmc-field__control' },
        props.prefix ? h('span', { className: 'cmc-field__affix' }, props.prefix) : null,
        control,
        props.suffix ? h('span', { className: 'cmc-field__affix' }, props.suffix) : null,
        props.chevron ? h(Icon, { name: 'chevron-down', size: 16, className: 'cmc-field__chevron' }) : null),
      props.error ? h('span', { className: 'cmc-field__hint cmc-field__hint--error' }, props.error)
        : props.hint ? h('span', { className: 'cmc-field__hint' }, props.hint) : null);
  }
  function Input(props) {
    var rest = {};
    for (var k in props) if (['label', 'hint', 'error', 'prefix', 'suffix', 'className', 'bind'].indexOf(k) < 0) rest[k] = props[k];
    rest.className = 'cmc-field__input';
    if (!rest.type) rest.type = 'text';
    if (props.bind) {
      var bound = useInputs();
      delete rest.defaultValue;
      rest.value = bound[0][props.bind];
      rest.onChange = function (e) { var n = parseFloat(e.target.value); var o = {}; o[props.bind] = isNaN(n) ? 0 : n; bound[1](o); if (props.onChange) props.onChange(e); };
    }
    return Field(props, h('input', rest));
  }
  function Select(props) {
    var rest = {};
    for (var k in props) if (['label', 'hint', 'error', 'prefix', 'suffix', 'className', 'options'].indexOf(k) < 0) rest[k] = props[k];
    rest.className = 'cmc-field__input cmc-field__input--select';
    var opts = (props.options || []).map(function (o, i) {
      var v = typeof o === 'string' ? o : o.value, l = typeof o === 'string' ? o : o.label;
      return h('option', { key: i, value: v }, l);
    });
    var p = {}; for (var k2 in props) p[k2] = props[k2]; p.chevron = true;
    return Field(p, h('select', rest, opts));
  }

  /* ---------- PillTabs ---------- */
  function PillTabs(props) {
    var items = props.items || [];
    return h('div', { className: cx('cmc-pills', props.className), role: 'tablist' }, items.map(function (it) {
      var v = typeof it === 'string' ? it : it.value, l = typeof it === 'string' ? it : it.label;
      var active = v === props.value;
      return h('button', {
        key: v, type: 'button', role: 'tab', 'aria-selected': active ? 'true' : 'false',
        className: cx('cmc-pill', active && 'cmc-pill--active'),
        onClick: function () { if (props.onChange) props.onChange(v); }
      }, l);
    }));
  }

  /* ---------- Badge ---------- */
  function Badge(props) {
    return h('span', { className: cx('cmc-badge', 'cmc-badge--' + (props.tone || 'navy'), props.className) }, props.children);
  }

  /* ---------- ListingCard ---------- */
  function fmtMoney(n, ccy) {
    if (typeof n !== 'number') return n;
    return (ccy || 'CI$') + n.toLocaleString('en-US', { maximumFractionDigits: 0 });
  }
  function ListingCard(props) {
    var meta = [];
    if (props.beds != null) meta.push({ icon: 'bed-double', text: props.beds + (props.beds === 1 ? ' Bed' : ' Beds') });
    if (props.baths != null) meta.push({ icon: 'bath', text: props.baths + (props.baths === 1 ? ' Bath' : ' Baths') });
    if (props.sqft != null) meta.push({ icon: 'ruler', text: props.sqft.toLocaleString('en-US') + ' Sq Ft' });
    var Tag = props.href ? 'a' : 'article';
    var external = !!props.href && /^https?:\/\//i.test(props.href);
    return h(Tag, { className: cx('cmc-listing', props.className), href: props.href, target: external ? '_blank' : undefined, rel: external ? 'noopener' : undefined,
        'aria-label': external && props.address ? props.address + ' : view on the agent\'s site' : undefined },
      h('div', { className: 'cmc-listing__media' },
        props.image ? h('img', { src: props.image, alt: props.imageAlt || '' })
          : h('div', { className: 'cmc-listing__placeholder' }, h(Icon, { name: 'house', size: 32 })),
        props.badge ? h(Badge, { tone: props.badgeTone || 'navy', className: 'cmc-listing__badge' }, props.badge) : null,
        props.onFavourite ? h('button', {
          type: 'button', className: cx('cmc-listing__fav', props.favourited && 'cmc-listing__fav--on'),
          'aria-label': props.favourited ? 'Remove from saved' : 'Save listing', 'aria-pressed': props.favourited ? 'true' : 'false',
          onClick: function (e) { e.preventDefault(); props.onFavourite(); }
        }, h(Icon, { name: 'heart', size: 16 })) : null,
        props.onCompare ? h('button', {
          type: 'button', className: cx('cmc-listing__compare', props.compared && 'cmc-listing__compare--on'),
          'aria-pressed': props.compared ? 'true' : 'false',
          onClick: function (e) { e.preventDefault(); e.stopPropagation(); props.onCompare(); }
        }, h('span', { className: 'cmc-listing__compare-box' }, props.compared ? h(Icon, { name: 'check', size: 12, strokeWidth: 3 }) : null), props.compared ? 'Comparing' : 'Compare') : null),
      h('div', { className: 'cmc-listing__body' },
        h('div', { className: 'cmc-listing__price' }, fmtMoney(props.price, props.currency),
          props.period ? h('span', { className: 'cmc-listing__period' }, ' /' + props.period) : null),
        h('div', { className: 'cmc-listing__address' }, props.address),
        props.locality ? h('div', { className: 'cmc-listing__locality' }, props.locality) : null,
        props.monthly != null ? h('div', { className: 'cmc-listing__monthly' },
          h(Icon, { name: 'calculator', size: 14 }), 'From ', h('strong', null, fmtMoney(props.monthly, props.currency)), '/mo') : null),
      meta.length ? h('div', { className: 'cmc-listing__meta' }, meta.map(function (m, i) {
        return h('span', { key: i }, h(Icon, { name: m.icon, size: 14 }), m.text);
      })) : null,
      props.agency || external ? h('div', { className: 'cmc-listing__agency' },
        props.agency ? h('span', null, 'Listed by ', props.agency) : null,
        external ? h('span', { className: 'cmc-listing__ext' }, 'View on agent\'s site', h(Icon, { name: 'external-link', size: 12 })) : null) : null);
  }

  /* ---------- CalculatorPanel ---------- */
  function payment(principal, annualRate, years) {
    var r = annualRate / 100 / 12, n = years * 12;
    if (principal <= 0 || n <= 0) return 0;
    if (r === 0) return principal / n;
    return principal * r / (1 - Math.pow(1 + r, -n));
  }
  function CalculatorPanel(props) {
    var st = useInputs(props.defaults);
    var v = st[0], set = st[1];
    var tabState = React.useState(props.tab || 'buy');
    var tab = tabState[0], setTab = tabState[1];
    var fx = v.fx || 1;
    function upd(k) { return function (e) { var n = parseFloat(e.target.value); var o = {}; o[k] = isNaN(n) ? 0 : (k === 'price' ? n / fx : n); set(o); }; }
    var loan = v.price * (1 - v.deposit / 100);
    var m = payment(loan, v.rate, v.term) * fx;
    var ccy = props.currency || v.symbol || 'CI$';
    return h('section', { className: cx('cmc-calc', props.compact && 'cmc-calc--compact', props.className), 'aria-label': 'Mortgage calculator' },
      props.hideTabs ? null : h(PillTabs, { items: [{ value: 'buy', label: 'Buying' }, { value: 'refi', label: 'Refinancing' }, { value: 'afford', label: 'What can I afford?' }], value: tab, className: 'cmc-calc__tabs',
        onChange: function (val) { var links = props.tabLinks || {}; if (links[val]) { try { window.location.assign(links[val]); } catch (e) {} return; } setTab(val); } }),
      h('div', { className: 'cmc-calc__grid' },
        h(Input, { label: 'Purchase price', prefix: ccy, type: 'number', inputMode: 'decimal', min: 0, step: 1000, value: Math.round(v.price * fx), onChange: upd('price') }),
        h(Input, { label: 'Deposit', suffix: '%', type: 'number', inputMode: 'decimal', min: 0, max: 100, step: 0.5, value: v.deposit, onChange: upd('deposit') }),
        h(Input, { label: 'Interest rate', suffix: '%', type: 'number', inputMode: 'decimal', min: 0, step: 0.05, value: v.rate, onChange: upd('rate') }),
        h(Select, { label: 'Term', options: [{ value: 15, label: '15 years' }, { value: 20, label: '20 years' }, { value: 25, label: '25 years' }, { value: 30, label: '30 years' }], value: v.term, onChange: upd('term') }),
        h('div', { className: 'cmc-calc__result' },
          h('span', { className: 'cmc-calc__result-label' }, 'Estimated monthly'),
          h('span', { className: 'cmc-calc__result-value' }, fmtMoney(Math.round(m), ccy)),
          h('span', { className: 'cmc-calc__result-sub' }, 'on ' + fmtMoney(Math.round(loan * fx), ccy) + ' over ' + v.term + ' yrs')),
        h(Button, { variant: 'primary', iconRight: 'arrow-right', className: 'cmc-calc__cta', href: props.href, onClick: props.onSubmit }, props.ctaLabel || 'See full breakdown')),
      props.note ? h('p', { className: 'cmc-calc__note' }, h(Icon, { name: 'info', size: 14 }), props.note) : null);
  }

  /* ---------- Byline: who wrote it, who checked it, when the sources were last checked ---------- */
  function Byline(props) {
    var items = [];
    if (props.author) items.push(['Written by', props.author]);
    if (props.reviewer) items.push(['Reviewed by', props.reviewer]);
    if (props.checked) items.push(['Sources checked', props.checked]);
    if (props.updated) items.push(['Last updated', props.updated]);
    return h('div', { className: cx('cmc-byline', props.className) },
      h(Icon, { name: 'shield-check', size: 16 }),
      items.map(function (it, i) { return h('span', { key: i, className: 'cmc-byline__item' }, h('span', { className: 'cmc-byline__k' }, it[0] + ' '), h('strong', null, it[1])); }),
      props.note ? h('span', { className: 'cmc-byline__note' }, props.note) : null);
  }

  /* ---------- Header ---------- */
  function Header(props) {
    var dark = !!props.dark;
    var logo = dark ? props.logoReversed : props.logo;
    var nav = props.nav || [];
    // Which dropdown the visitor has opened with its arrow (hover still previews; the arrow pins it open)
    var openState = React.useState(function () { var idx = null; nav.forEach(function (it, i) { if (it.menu && it.open) idx = i; }); return idx; });
    var openIdx = openState[0], setOpenIdx = openState[1];
    var mobState = React.useState(false);
    var mobileOpen = mobState[0], setMobileOpen = mobState[1];
    React.useEffect(function () {
      if (!mobileOpen) return;
      function onKey(e) { if (e.key === 'Escape') setMobileOpen(false); }
      document.addEventListener('keydown', onKey); return function () { document.removeEventListener('keydown', onKey); };
    }, [mobileOpen]);
    React.useEffect(function () {
      if (openIdx == null) return;
      function onDoc(e) { if (!e.target.closest || !e.target.closest('.cmc-header__item--menu')) setOpenIdx(null); }
      function onKey(e) { if (e.key === 'Escape') setOpenIdx(null); }
      document.addEventListener('click', onDoc); document.addEventListener('keydown', onKey);
      return function () { document.removeEventListener('click', onDoc); document.removeEventListener('keydown', onKey); };
    }, [openIdx]);
    return h('header', { className: cx('cmc-header', dark && 'cmc-header--dark', props.className) },
      props.utility ? h('div', { className: 'cmc-utility' }, h('div', { className: 'cmc-container cmc-utility__row' },
        h('div', { className: 'cmc-utility__items' }, (props.utility.items || []).map(function (it, i) {
          return h('span', { key: i }, it.icon ? h(Icon, { name: it.icon, size: 14 }) : null, it.text);
        })),
        props.utility.right ? h('span', { className: 'cmc-utility__right' }, props.utility.right) : null)) : null,
      h('div', { className: 'cmc-container cmc-header__row' },
        h('a', { className: 'cmc-header__logo', href: props.homeHref || '/', 'aria-label': 'Cayman Mortgage Calculator: home' },
          logo ? h('img', { src: logo, alt: '', style: { height: (props.logoHeight || 40) + 'px' } }) : h('span', { className: 'cmc-header__fallback' }, 'Cayman Mortgage Calculator')),
        h('nav', { className: 'cmc-header__nav', 'aria-label': 'Main' }, nav.map(function (it, i) {
          var isOpen = !!it.menu && openIdx === i;
          var link = h('a', { href: it.href || '#', className: cx('cmc-header__link', it.active && 'cmc-header__link--active', it.menu && 'cmc-header__link--menu'), 'aria-current': it.active ? 'page' : undefined }, it.label);
          if (!it.menu) return h('div', { key: i, className: 'cmc-header__item' }, link);
          var toggle = h('button', {
            type: 'button', className: cx('cmc-header__toggle', isOpen && 'cmc-header__toggle--open'),
            'aria-label': (isOpen ? 'Hide ' : 'Show ') + it.label + ' menu', 'aria-haspopup': 'true', 'aria-expanded': isOpen ? 'true' : 'false',
            onClick: function (e) { e.preventDefault(); e.stopPropagation(); setOpenIdx(openIdx === i ? null : i); }
          }, h(Icon, { name: 'chevron-down', size: 14 }));
          return h('div', { key: i, className: cx('cmc-header__item', 'cmc-header__item--menu', isOpen && 'cmc-header__item--open') }, h('span', { className: 'cmc-header__link-group' }, link, toggle),
            h('ul', { className: 'cmc-header__dropdown', role: 'menu' }, it.menu.map(function (m, j) {
              return h('li', { key: j, role: 'none' }, h('a', { role: 'menuitem', href: m.href || '#', className: cx('cmc-header__dropdown-link', m.active && 'cmc-header__dropdown-link--active') },
                m.icon ? h(Icon, { name: m.icon, size: 18 }) : null,
                h('span', { className: 'cmc-header__dropdown-text' }, h('span', null, m.label), m.description ? h('span', { className: 'cmc-header__dropdown-desc' }, m.description) : null)));
            })));
        })),
        h('div', { className: 'cmc-header__actions' },
          props.cta ? h(Button, { variant: dark ? 'onDark' : 'primary', size: 'sm', href: props.cta.href, iconRight: props.cta.icon, className: 'cmc-header__cta' }, props.cta.label) : null,
          h('button', { type: 'button', className: cx('cmc-header__menu', mobileOpen && 'cmc-header__menu--open'), 'aria-label': mobileOpen ? 'Close menu' : 'Open menu', 'aria-expanded': mobileOpen ? 'true' : 'false', 'aria-controls': 'cmc-mobile-nav', onClick: function () { setMobileOpen(!mobileOpen); } }, h(Icon, { name: mobileOpen ? 'x' : 'menu', size: 22 })))),
      // Phone and tablet menu: every link, groups expanded, the CTA at the bottom
      mobileOpen ? h('nav', { id: 'cmc-mobile-nav', className: 'cmc-header__drawer', 'aria-label': 'Main' },
        nav.map(function (it, i) {
          return h('div', { key: i, className: 'cmc-header__drawer-group' },
            h('a', { href: it.href || '#', className: cx('cmc-header__drawer-link', it.active && 'cmc-header__drawer-link--active'), 'aria-current': it.active ? 'page' : undefined, onClick: function () { setMobileOpen(false); } }, it.label),
            it.menu ? h('div', { className: 'cmc-header__drawer-sub' }, it.menu.map(function (m, j) {
              return h('a', { key: j, href: m.href || '#', className: cx('cmc-header__drawer-sublink', m.active && 'cmc-header__drawer-sublink--active'), onClick: function () { setMobileOpen(false); } },
                m.icon ? h(Icon, { name: m.icon, size: 18 }) : null, h('span', null, m.label));
            })) : null);
        }),
        props.cta ? h(Button, { variant: 'primary', href: props.cta.href, iconRight: props.cta.icon, block: true, className: 'cmc-header__drawer-cta' }, props.cta.label) : null) : null);
  }

  /* ---------- BackToTop: floating button, appears after a screen of scrolling ---------- */
  function BackToTop(props) {
    var st = React.useState(false); var show = st[0], setShow = st[1];
    React.useEffect(function () {
      function onScroll() { setShow(window.scrollY > (props.after || 400)); }
      onScroll(); window.addEventListener('scroll', onScroll, { passive: true });
      return function () { window.removeEventListener('scroll', onScroll); };
    }, []);
    return h('button', {
      type: 'button', className: cx('cmc-totop', show && 'cmc-totop--show', props.className), 'aria-label': 'Back to top', tabIndex: show ? 0 : -1,
      onClick: function () { try { window.scrollTo({ top: 0, behavior: 'smooth' }); } catch (e) { window.scrollTo(0, 0); } }
    }, h(Icon, { name: 'arrow-up', size: 20, strokeWidth: 2 }));
  }

  /* Every page opens at the top: no restored scroll position on reload or back/forward, unless the URL points at an anchor */
  try {
    if ('scrollRestoration' in window.history) window.history.scrollRestoration = 'manual';
    var toTop = function () { if (!window.location.hash) window.scrollTo(0, 0); };
    toTop(); window.addEventListener('pageshow', toTop);
  } catch (e) {}

  /* ---------- Footer ---------- */
  function Footer(props) {
    var cols = props.columns || [];
    return h('footer', { className: cx('cmc-footer', props.className) },
      h('div', { className: 'cmc-container cmc-footer__grid' },
        h('div', { className: 'cmc-footer__brand' },
          props.logoReversed ? h('img', { src: props.logoReversed, alt: 'Cayman Mortgage Calculator', height: 36 }) : h('span', { className: 'cmc-footer__fallback' }, 'Cayman Mortgage Calculator'),
          props.blurb ? h('p', null, props.blurb) : null),
        cols.map(function (c, i) {
          return h('div', { key: i, className: 'cmc-footer__col' },
            h('h4', null, c.title),
            h('ul', null, (c.links || []).map(function (l, j) { return h('li', { key: j }, h('a', { href: l.href || '#' }, l.label)); })));
        })),
      h('div', { className: 'cmc-container cmc-footer__legal' },
        h('span', null, props.legal || ('© ' + new Date().getFullYear() + ' Cayman Mortgage Calculator. Estimates only; not financial advice.')),
        h('span', { className: 'cmc-footer__legal-links' }, (props.legalLinks || []).map(function (l, i) { return h('a', { key: i, href: l.href || '#' }, l.label); }))));
  }

  var w = window;
  w.CMC = w.CMC || {};
  Object.assign(w.CMC, { Button: Button, Input: Input, Select: Select, PillTabs: PillTabs, Badge: Badge, Icon: Icon, ListingCard: ListingCard, CalculatorPanel: CalculatorPanel, Header: Header, Footer: Footer, Byline: Byline, BackToTop: BackToTop, payment: payment, inputs: inputs, useInputs: useInputs });
})();
