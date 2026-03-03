// Menu mobile
window.toggleMenu = function () {
  const el = document.getElementById('navMobile');
  if (!el) return;
  el.style.display = (el.style.display === 'block') ? 'none' : 'block';
};

// Modal
(function () {
  function setModal(open) {
    const modal = document.getElementById('videoModal');
    if (!modal) return;
    modal.setAttribute('aria-hidden', open ? 'false' : 'true');
  }

  window.openVideoModal = function () { setModal(true); };
  window.closeVideoModal = function () { setModal(false); };

  document.addEventListener('click', (e) => {
    const t = e.target;
    if (t && t.matches && t.matches('[data-open-video]')) setModal(true);
    if (t && t.matches && t.matches('[data-close-modal]')) setModal(false);
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') setModal(false);
  });
})();

// Scroll reveal
(function () {
  const els = Array.from(document.querySelectorAll('[data-reveal]'));
  if (!els.length) return;

  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) entry.target.classList.add('is-visible');
    });
  }, { threshold: 0.12 });

  els.forEach(el => io.observe(el));
})();
