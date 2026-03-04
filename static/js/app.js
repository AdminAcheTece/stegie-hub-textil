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

// ===========================
// TOPBAR: toggle menu mobile
// ===========================
(function () {
  const burger = document.querySelector(".st-burger");
  const menu = document.getElementById("stMobileMenu");
  if (!burger || !menu) return;

  burger.addEventListener("click", () => {
    const isOpen = burger.getAttribute("aria-expanded") === "true";
    burger.setAttribute("aria-expanded", String(!isOpen));
    menu.hidden = isOpen;
  });
})();

// ===========================
// NAVBAR: mobile toggle + fechar dropdown fora/ESC
// ===========================
(function () {
  // mobile menu
  const burger = document.querySelector(".st-fnav__burger");
  const mobileMenu = document.getElementById("stFnavMobile");
  if (burger && mobileMenu) {
    burger.addEventListener("click", () => {
      const isOpen = burger.getAttribute("aria-expanded") === "true";
      burger.setAttribute("aria-expanded", String(!isOpen));
      mobileMenu.hidden = isOpen;
    });
  }

  // dropdown close helpers
  const dropdowns = Array.from(document.querySelectorAll(".st-dd"));

  function closeAll() {
    dropdowns.forEach(d => d.removeAttribute("open"));
  }

  // fecha ao clicar fora
  document.addEventListener("click", (e) => {
    const clickedInside = dropdowns.some(d => d.contains(e.target));
    if (!clickedInside) closeAll();
  });

  // fecha no ESC
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAll();
  });
})();

// ===========================
// NAVBAR: mobile + fechar dropdown fora/ESC + só 1 aberto
// ===========================
(function () {
  const burger = document.querySelector(".st-fnav__burger");
  const mobileMenu = document.getElementById("stFnavMobile");

  if (burger && mobileMenu) {
    burger.addEventListener("click", () => {
      const isOpen = burger.getAttribute("aria-expanded") === "true";
      burger.setAttribute("aria-expanded", String(!isOpen));
      mobileMenu.hidden = isOpen;
    });
  }

  const dropdowns = Array.from(document.querySelectorAll(".st-dd"));

  function closeAll(except = null) {
    dropdowns.forEach(d => {
      if (d !== except) d.removeAttribute("open");
    });
  }

  // só 1 dropdown aberto por vez
  dropdowns.forEach(d => {
    d.addEventListener("toggle", () => {
      if (d.open) closeAll(d);
    });
  });

  // fecha ao clicar fora
  document.addEventListener("click", (e) => {
    const inside = dropdowns.some(d => d.contains(e.target));
    if (!inside) closeAll();
  });

  // fecha no ESC
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAll();
  });
})();
