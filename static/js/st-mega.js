(function () {
  const triggers = Array.from(document.querySelectorAll("[data-mega-trigger]"));
  const panels = Array.from(document.querySelectorAll(".st-mega"));

  function closeAll() {
    triggers.forEach(btn => {
      btn.classList.remove("is-open");
      btn.setAttribute("aria-expanded", "false");
    });
    panels.forEach(p => p.classList.remove("is-open"));
  }

  function openPanel(key, btn) {
    closeAll();
    const panel = document.getElementById(`mega-${key}`);
    if (!panel) return;

    btn.classList.add("is-open");
    btn.setAttribute("aria-expanded", "true");
    panel.classList.add("is-open");
  }

  triggers.forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const key = btn.getAttribute("data-mega-trigger");
      const panel = document.getElementById(`mega-${key}`);
      const isOpen = panel && panel.classList.contains("is-open");

      if (isOpen) closeAll();
      else openPanel(key, btn);
    });
  });

  // Fecha clicando fora
  document.addEventListener("click", (e) => {
    const insideTop = e.target.closest("#stTopbar");
    const insideMega = e.target.closest(".st-mega");
    if (!insideTop && !insideMega) closeAll();
  });

  // Fecha no ESC
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAll();
  });

  // Se rolar, pode fechar (opcional). Comente se não quiser.
  window.addEventListener("scroll", () => {
    closeAll();
  }, { passive: true });
})();
