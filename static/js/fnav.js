(() => {
  const nav = document.getElementById("st-fnav");
  if (!nav) return;

  const triggers = Array.from(nav.querySelectorAll("[data-fnav-trigger]"));
  const panels = Array.from(nav.querySelectorAll("[data-fnav-panel]"));
  const overlay = nav.querySelector("[data-fnav-overlay]");

  const closeAll = () => {
    nav.dataset.open = "0";
    triggers.forEach(t => {
      t.classList.remove("is-active");
      t.setAttribute("aria-expanded", "false");
    });
    panels.forEach(p => p.classList.remove("is-open"));
    nav.querySelector(".fnav-panels")?.setAttribute("aria-hidden", "true");
  };

  const openOne = (key) => {
    nav.dataset.open = "1";
    nav.querySelector(".fnav-panels")?.setAttribute("aria-hidden", "false");

    triggers.forEach(t => {
      const active = t.dataset.fnavTrigger === key;
      t.classList.toggle("is-active", active);
      t.setAttribute("aria-expanded", active ? "true" : "false");
    });

    panels.forEach(p => {
      p.classList.toggle("is-open", p.dataset.fnavPanel === key);
    });
  };

  const isOpenKey = (key) => {
    const p = panels.find(x => x.dataset.fnavPanel === key);
    return !!p && p.classList.contains("is-open");
  };

  // clique nos itens do menu
  triggers.forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const key = btn.dataset.fnavTrigger;
      if (isOpenKey(key)) closeAll();
      else openOne(key);
    });
  });

  // clique fora fecha
  overlay?.addEventListener("click", closeAll);

  // ESC fecha
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAll();
  });

  // se redimensionar, mantém estável
  window.addEventListener("resize", () => {
    // opcional: se quiser sempre fechar ao redimensionar
    // closeAll();
  });

  // começa fechado
  closeAll();
})();
