(() => {
  const btn = document.querySelector("[data-nav-toggle]");
  const panel = document.querySelector("[data-nav-mobile]");
  if (!btn || !panel) return;

  btn.addEventListener("click", () => {
    const isHidden = panel.hasAttribute("hidden");
    if (isHidden) panel.removeAttribute("hidden");
    else panel.setAttribute("hidden", "");
  });
})();
