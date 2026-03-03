// -----------------------------
// Menu mobile (suporta 2 padrões):
// 1) id="navMobile" (toggle display)
// 2) class=".nav" com botão .nav-toggle (toggle class is-open)
// -----------------------------
window.toggleMenu = function () {
  const byId = document.getElementById('navMobile');
  if (byId) {
    byId.style.display = (byId.style.display === 'block') ? 'none' : 'block';
    return;
  }

  const nav = document.querySelector('.nav');
  if (!nav) return;
  nav.classList.toggle('is-open');
};

// Se existir um botão com class nav-toggle, conecta automaticamente
document.addEventListener('click', (e) => {
  const t = e.target;
  if (!t) return;

  // Clica no botão (ou em algo dentro dele)
  const toggleBtn = t.closest ? t.closest('.nav-toggle') : null;
  if (toggleBtn) window.toggleMenu();
});


// -----------------------------
// Modal
// -----------------------------
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
    if (!t || !t.matches) return;
    if (t.matches('[data-open-video]')) setModal(true);
    if (t.matches('[data-close-modal]')) setModal(false);
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') setModal(false);
  });
})();


// -----------------------------
// Scroll reveal
// -----------------------------
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

console.log("Stegie app.js carregado");
