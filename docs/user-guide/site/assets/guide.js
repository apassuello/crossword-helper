// User guide page behaviour: appearance toggle, phone menu, and the "on this page" highlight.
(function () {
  var root = document.documentElement;

  var themeBtn = document.querySelector('.g-theme');
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      var dark = root.dataset.theme
        ? root.dataset.theme === 'dark'
        : window.matchMedia('(prefers-color-scheme: dark)').matches;
      root.dataset.theme = dark ? 'light' : 'dark';
      try { localStorage.setItem('guide-theme', root.dataset.theme); } catch (e) { /* storage blocked: toggle still works */ }
    });
  }

  var menuBtn = document.querySelector('.g-menu');
  if (menuBtn) {
    menuBtn.addEventListener('click', function () {
      var open = document.body.classList.toggle('nav-open');
      menuBtn.setAttribute('aria-expanded', String(open));
    });
  }

  var links = Array.prototype.slice.call(document.querySelectorAll('.g-toc a'));
  if (!links.length || !('IntersectionObserver' in window)) return;
  var byId = {};
  links.forEach(function (a) { byId[decodeURIComponent(a.hash.slice(1))] = a; });
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      links.forEach(function (a) { a.classList.remove('is-current'); });
      var link = byId[entry.target.id];
      if (link) link.classList.add('is-current');
    });
  }, { rootMargin: '-60px 0px -70% 0px' });
  Object.keys(byId).forEach(function (id) {
    var heading = document.getElementById(id);
    if (heading) observer.observe(heading);
  });
})();
