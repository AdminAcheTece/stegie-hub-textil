(function () {
  const root = document.getElementById("stMobileNav");
  const openBtn = document.getElementById("stMnavOpen");
  if (!root || !openBtn) return;

  const closeEls = root.querySelectorAll("[data-mnav-close]");
  const tabs = Array.from(root.querySelectorAll("[data-mnav-tab]"));
  const panes = Array.from(root.querySelectorAll("[data-mnav-pane]"));

  function setTab(key) {
    tabs.forEach(t => {
      const active = t.getAttribute("data-mnav-tab") === key;
      t.classList.toggle("is-active", active);
      t.setAttribute("aria-selected", active ? "true" : "false");
    });
    panes.forEach(p => {
      const active = p.getAttribute("data-mnav-pane") === key;
      p.classList.toggle("is-active", active);
    });
  }

  function openMenu() {
    root.hidden = false;
    requestAnimationFrame(() => root.classList.add("is-open"));
    openBtn.setAttribute("aria-expanded", "true");
    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";
  }

  function closeMenu() {
    root.classList.remove("is-open");
    openBtn.setAttribute("aria-expanded", "false");
    document.documentElement.style.overflow = "";
    document.body.style.overflow = "";
    setTimeout(() => { root.hidden = true; }, 180);
  }

  openBtn.addEventListener("click", (e) => {
    e.preventDefault();
    const expanded = openBtn.getAttribute("aria-expanded") === "true";
    expanded ? closeMenu() : openMenu();
  });

  closeEls.forEach(el => el.addEventListener("click", closeMenu));

  tabs.forEach(btn => {
    btn.addEventListener("click", () => setTab(btn.getAttribute("data-mnav-tab")));
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !root.hidden) closeMenu();
  });

  // padrão: abre em Soluções
  setTab("solucoes");
})();
