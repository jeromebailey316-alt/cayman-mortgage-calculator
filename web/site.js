/* Shared header behaviour: the light/dark button and the sideways nav on a phone.
   Loaded with defer on every page. */
(function () {
  var KEY = 'caymanMortgage.theme';
  var SUN = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.2M12 19.3v2.2M4.3 4.3l1.6 1.6M18.1 18.1l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.3 19.7l1.6-1.6M18.1 5.9l1.6-1.6"/></svg>';
  var MOON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 14.3A8.5 8.5 0 0 1 9.7 3.5a8.5 8.5 0 1 0 10.8 10.8z"/></svg>';
  function saved() { try { var t = localStorage.getItem(KEY); return t === 'dark' || t === 'light' ? t : null; } catch (e) { return null; } }
  function systemDark() { return !!(window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches); }
  // The saved choice was already put on <html> before first paint by the inline
  // snippet in the head (page.THEME_PREPAINT); this file only wires up the button.
  function apply(choice) {
    var root = document.documentElement;
    if (choice) root.setAttribute('data-theme', choice); else root.removeAttribute('data-theme');
    var dark = choice ? choice === 'dark' : systemDark(), btn = document.getElementById('themeBtn');
    if (!btn) return;
    btn.innerHTML = dark ? SUN : MOON;
    var label = dark ? 'Switch to light mode' : 'Switch to dark mode';
    btn.setAttribute('aria-label', label); btn.title = label;
  }
  function start() {
    apply(saved());
    var btn = document.getElementById('themeBtn');
    if (btn) btn.addEventListener('click', function () {
      var next = (saved() ? saved() === 'dark' : systemDark()) ? 'light' : 'dark';
      try { localStorage.setItem(KEY, next); } catch (e) { /* ignore */ }
      apply(next);
    });
    if (window.matchMedia) {
      var mq = matchMedia('(prefers-color-scheme: dark)');
      var onChange = function () { if (!saved()) apply(null); };
      if (mq.addEventListener) mq.addEventListener('change', onChange);
      else if (mq.addListener) mq.addListener(onChange);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();

  // On a phone the nav scrolls sideways: bring the current page's tab into view,
  // and fade the right edge while there is more to see.
  function navScroll() {
    var nav = document.querySelector('.site-nav');
    if (!nav) return;
    var here = nav.querySelector('a[aria-current="page"]');
    // Centre it by setting the nav's own scroll position. scrollIntoView() would also
    // work, but Chrome then starts keyboard Tab from that link, skipping the skip link.
    if (here && nav.scrollWidth > nav.clientWidth) {
      nav.scrollLeft = here.offsetLeft - nav.offsetLeft - (nav.clientWidth - here.offsetWidth) / 2;
    }
    var mark = function () {
      var more = nav.scrollWidth - nav.clientWidth - nav.scrollLeft > 8;
      nav.classList.toggle('more', more);
    };
    // scroll and resize fire many times a frame; measure at most once per frame
    var queued = false;
    var onMove = function () {
      if (queued) return;
      queued = true;
      requestAnimationFrame(function () { queued = false; mark(); });
    };
    mark();
    nav.addEventListener('scroll', onMove, { passive: true });
    window.addEventListener('resize', onMove, { passive: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', navScroll); else navScroll();
})();
