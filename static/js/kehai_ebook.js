(() => {

  "use strict";


  /* =====================================================
     ELEMENTOS
     ===================================================== */

  const header =
    document.getElementById(
      "kehaiEbookHeader"
    );


  const menuToggle =
    document.getElementById(
      "kehaiEbookMenuToggle"
    );


  const mobileMenu =
    document.getElementById(
      "kehaiEbookMobileMenu"
    );


  const buyButton =
    document.getElementById(
      "kehaiEbookBuyButton"
    );


  /* =====================================================
     HEADER
     ===================================================== */

  function updateHeader() {

    if (!header) {
      return;
    }


    header.classList.toggle(
      "is-scrolled",
      window.scrollY > 10
    );

  }


  updateHeader();


  window.addEventListener(
    "scroll",
    updateHeader,
    {
      passive: true
    }
  );


  /* =====================================================
     MENU MOBILE
     ===================================================== */

  function closeMenu() {

    if (
      !menuToggle
      ||
      !mobileMenu
    ) {
      return;
    }


    menuToggle.setAttribute(
      "aria-expanded",
      "false"
    );


    menuToggle.setAttribute(
      "aria-label",
      "Abrir menu"
    );


    mobileMenu.classList.remove(
      "is-open"
    );


    document.body.classList.remove(
      "kehai-menu-open"
    );

  }


  function openMenu() {

    if (
      !menuToggle
      ||
      !mobileMenu
    ) {
      return;
    }


    menuToggle.setAttribute(
      "aria-expanded",
      "true"
    );


    menuToggle.setAttribute(
      "aria-label",
      "Fechar menu"
    );


    mobileMenu.classList.add(
      "is-open"
    );


    document.body.classList.add(
      "kehai-menu-open"
    );

  }


  menuToggle?.addEventListener(
    "click",
    () => {

      const isOpen =
        menuToggle.getAttribute(
          "aria-expanded"
        ) === "true";


      if (isOpen) {

        closeMenu();

      }

      else {

        openMenu();

      }

    }
  );


  mobileMenu
    ?.querySelectorAll("a")
    .forEach(
      (link) => {

        link.addEventListener(
          "click",
          closeMenu
        );

      }
    );


  document.addEventListener(
    "keydown",
    (event) => {

      if (
        event.key === "Escape"
      ) {

        closeMenu();

      }

    }
  );


  /* =====================================================
     BOTÃO DE COMPRA
     ETAPA 3 CONECTARÁ AO CHECKOUT
     ===================================================== */

  buyButton?.addEventListener(
    "click",
    () => {

      console.info(
        "[KEHAI] Checkout digital será conectado na Etapa 3."
      );

    }
  );


  console.log(
    "[KEHAI] Landing do eBook carregada."
  );

})();
