/* =========================================================
   KEHAI — LANDING PAGE DO LIVRO
   Arquivo: static/JS/kehai_livro.js
   ========================================================= */

(() => {

  "use strict";


  /* =========================================================
     1. CONFIGURAÇÕES COMERCIAIS
     ========================================================= */

  const KEHAI_CONFIG = {

    links: {

      physical: "",

      signed: "",

      ebook: "",

      corporate: ""

    },

    prices: {

      physical: "R$ 79,90",

      signed: "R$ 89,90",

      ebook: "R$ 29,90"

    }

  };


  /* =========================================================
     2. HELPERS
     ========================================================= */

  const $ = (
    selector,
    context = document
  ) => context.querySelector(selector);


  const $$ = (
    selector,
    context = document
  ) => Array.from(
    context.querySelectorAll(selector)
  );


  const reducedMotion =
    window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;


  /* =========================================================
     3. ANALYTICS
     ========================================================= */

  function trackEvent(
    eventName,
    data = {}
  ) {

    window.dataLayer =
      window.dataLayer || [];


    window.dataLayer.push({

      event: eventName,

      ...data

    });

  }


  window.kehaiTrack =
    trackEvent;


    /* =========================================================
       4. CONFIGURAÇÃO DOS LINKS DE COMPRA
       ========================================================= */

    const physicalButtons = [

      $("#kehaiBuyPhysical"),

      $("#kehaiBuyFinal")

    ].filter(Boolean);


    const signedButton =
      $("#kehaiBuySigned");


    const ebookButton =
      $("#kehaiBuyEbook");


    const corporateButton =
      $("#kehaiCorporate");


    /*
      Links comerciais que ainda utilizarão
      endereço externo/fixo.
    */
    function configureCommercialLink(
      element,
      url,
      eventName,
      options = {}
    ) {

      if (!element) {
        return;
      }


      if (!url) {

        element.setAttribute(
          "href",
          "#"
        );


        element.dataset.kehaiMissingLink =
          "true";

      }

      else {

        element.setAttribute(
          "href",
          url
        );


        element.dataset.kehaiMissingLink =
          "false";


        if (
          options.newTab === true
        ) {

          element.setAttribute(
            "target",
            "_blank"
          );


          element.setAttribute(
            "rel",
            "noopener noreferrer"
          );

        }

      }


      element.addEventListener(
        "click",
        (event) => {

          trackEvent(
            eventName,
            {
              destination:
                url || "not_configured"
            }
          );


          if (!url) {

            event.preventDefault();

            console.warn(
              `[KEHAI] O link "${eventName}" ainda não foi configurado.`
            );

          }

        }
      );

    }


    /*
      Checkout Mercado Pago
      Livro físico KEHAI
    */
    function configureMercadoPagoCheckout(
      button
    ) {

      if (!button) {
        return;
      }


      button.setAttribute(
        "href",
        "#"
      );


      button.addEventListener(
        "click",
        async (event) => {

          event.preventDefault();


          /*
            Evita dois cliques e,
            consequentemente,
            duas preferências simultâneas.
          */
          if (
            button.dataset.kehaiCheckoutLoading
            ===
            "true"
          ) {
            return;
          }


          trackEvent(
            "click_buy_physical",
            {
              destination:
                "mercado_pago"
            }
          );


          const originalHTML =
            button.innerHTML;


          button.dataset.kehaiCheckoutLoading =
            "true";


          button.setAttribute(
            "aria-busy",
            "true"
          );


          button.innerHTML =
            "Abrindo checkout...";


          try {

            const response =
              await fetch(
                "/api/kehai/checkout",
                {
                  method:
                    "POST",

                  headers: {
                    "Content-Type":
                      "application/json"
                  },

                  body:
                    JSON.stringify({
                      product:
                        "physical"
                    })
                }
              );


            const data =
              await response.json();


            if (
              !response.ok
              ||
              !data.success
            ) {

              throw new Error(
                data.error
                ||
                "Não foi possível criar o checkout."
              );

            }


            if (
              !data.checkout_url
            ) {

              throw new Error(
                "O Mercado Pago não retornou a URL do checkout."
              );

            }


            /*
              Redireciona o comprador
              para o Checkout Pro.
            */
            window.location.assign(
              data.checkout_url
            );

          }

          catch (error) {

            console.error(
              "[KEHAI] Erro ao iniciar Mercado Pago:",
              error
            );


            alert(
              "Não foi possível abrir o pagamento agora. Por favor, tente novamente."
            );


            button.dataset.kehaiCheckoutLoading =
              "false";


            button.removeAttribute(
              "aria-busy"
            );


            button.innerHTML =
              originalHTML;

          }

        }
      );

    }


    /*
      Liga os dois botões de compra
      do livro físico ao Mercado Pago.
    */
    physicalButtons.forEach(
      configureMercadoPagoCheckout
    );


    /*
      Demais modalidades permanecem
      preparadas para configuração posterior.
    */
    configureCommercialLink(
      signedButton,
      KEHAI_CONFIG.links.signed,
      "click_buy_signed"
    );


    configureCommercialLink(
      ebookButton,
      KEHAI_CONFIG.links.ebook,
      "click_buy_ebook",
      {
        newTab: true
      }
    );


    configureCommercialLink(
      corporateButton,
      KEHAI_CONFIG.links.corporate,
      "click_corporate",
      {
        newTab: true
      }
    );

  /* =========================================================
     5. MENU MOBILE
     ========================================================= */

  const menuToggle =
    $("#kehaiBookMenuToggle");


  const mobileMenu =
    $("#kehaiBookMobileMenu");


  function openMobileMenu() {

    if (
      !menuToggle ||
      !mobileMenu
    ) {
      return;
    }


    mobileMenu.classList.add(
      "is-open"
    );


    menuToggle.setAttribute(
      "aria-expanded",
      "true"
    );


    menuToggle.setAttribute(
      "aria-label",
      "Fechar menu"
    );


    document.body.style.overflow =
      "hidden";

  }


  function closeMobileMenu() {

    if (
      !menuToggle ||
      !mobileMenu
    ) {
      return;
    }


    mobileMenu.classList.remove(
      "is-open"
    );


    menuToggle.setAttribute(
      "aria-expanded",
      "false"
    );


    menuToggle.setAttribute(
      "aria-label",
      "Abrir menu"
    );


    document.body.style.overflow =
      "";

  }


  function toggleMobileMenu() {

    const open =
      menuToggle
        ?.getAttribute(
          "aria-expanded"
        ) === "true";


    if (open) {

      closeMobileMenu();

    }

    else {

      openMobileMenu();

    }

  }


  menuToggle?.addEventListener(
    "click",
    toggleMobileMenu
  );


  if (mobileMenu) {

    $$(
      "a",
      mobileMenu
    ).forEach(

      (link) => {

        link.addEventListener(
          "click",
          closeMobileMenu
        );

      }

    );

  }


  document.addEventListener(
    "keydown",
    (event) => {

      if (
        event.key === "Escape"
        &&
        !$("#kehaiBookLightbox")
          ?.classList
          .contains("is-open")
      ) {

        closeMobileMenu();

      }

    }
  );


  window.addEventListener(
    "resize",
    () => {

      if (
        window.innerWidth > 767
      ) {

        closeMobileMenu();

      }

    }
  );


  /* =========================================================
     6. SCROLL SUAVE PARA ÂNCORAS INTERNAS
     ========================================================= */

  $$('a[href^="#"]').forEach(

    (link) => {

      link.addEventListener(

        "click",

        (event) => {

          const href =
            link.getAttribute(
              "href"
            );


          if (
            !href ||
            href === "#"
          ) {
            return;
          }


          const target =
            document.querySelector(
              href
            );


          if (!target) {
            return;
          }


          event.preventDefault();


          const headerHeight =
            $(".kehai-book-header")
              ?.offsetHeight || 0;


          const targetPosition =
            target.getBoundingClientRect().top
            +
            window.scrollY
            -
            headerHeight
            -
            16;


          window.scrollTo({

            top:
              targetPosition,

            behavior:
              reducedMotion
                ? "auto"
                : "smooth"

          });

        }

      );

    }

  );


  /* =========================================================
     7. GALERIA EDITORIAL — LIVRO POR DENTRO
     ========================================================= */

  const galleryMain =
    $("#kehaiBookGalleryMain");


  const galleryMainButton =
    $("#kehaiBookGalleryOpen");


  const galleryThumbs =
    $$(
      ".kehai-book-gallery__thumb"
    );


  const galleryImages =
    galleryThumbs
      .map(
        (button) =>
          button.dataset.image
      )
      .filter(Boolean);


  let currentGalleryIndex =
    0;


  let galleryFadeTimer =
    null;


  /* =========================================================
     8. TROCA A IMAGEM PRINCIPAL
     ========================================================= */

  function setGalleryImage(
    index,
    animate = true
  ) {

    if (
      !galleryMain ||
      !galleryImages.length
    ) {
      return;
    }


    currentGalleryIndex =
      (
        index
        +
        galleryImages.length
      )
      %
      galleryImages.length;


    const nextImage =
      galleryImages[
        currentGalleryIndex
      ];


    galleryThumbs.forEach(
      (
        thumb,
        thumbIndex
      ) => {

        const active =
          thumbIndex ===
          currentGalleryIndex;


        thumb.classList.toggle(
          "active",
          active
        );


        thumb.setAttribute(
          "aria-selected",
          String(active)
        );

      }
    );


    /*
      Evita conflito caso o usuário
      passe rapidamente sobre várias
      miniaturas.
    */

    if (galleryFadeTimer) {

      window.clearTimeout(
        galleryFadeTimer
      );

    }


    if (
      reducedMotion ||
      animate === false
    ) {

      galleryMain.src =
        nextImage;


      galleryMain.style.opacity =
        "1";


      return;

    }


    galleryMain.style.opacity =
      "0";


    galleryFadeTimer =
      window.setTimeout(
        () => {

          galleryMain.src =
            nextImage;


          galleryMain.style.opacity =
            "1";


          galleryFadeTimer =
            null;

        },
        110
      );

  }


  /* =========================================================
     9. EVENTOS DAS MINIATURAS
     ========================================================= */

  galleryThumbs.forEach(
    (
      thumb,
      index
    ) => {


      /*
        DESKTOP:
        apenas passar o mouse já troca
        a imagem principal.
      */

      thumb.addEventListener(
        "mouseenter",
        () => {

          if (
            window.innerWidth > 767
          ) {

            setGalleryImage(
              index
            );

          }

        }
      );


      /*
        DESKTOP E MOBILE:
        clicar/tocar seleciona a página.

        IMPORTANTE:
        NÃO abre o lightbox aqui.
      */

      thumb.addEventListener(
        "click",
        (event) => {

          event.preventDefault();


          setGalleryImage(
            index
          );

        }
      );


      /*
        Acessibilidade por teclado.
      */

      thumb.addEventListener(
        "keydown",
        (event) => {

          if (
            event.key === "Enter"
            ||
            event.key === " "
          ) {

            event.preventDefault();


            setGalleryImage(
              index
            );

          }

        }
      );

    }
  );


  /*
    Inicializa a primeira miniatura
    como ativa.
  */

  if (
    galleryThumbs.length
    &&
    galleryMain
  ) {

    setGalleryImage(
      0,
      false
    );

  }


  /* =========================================================
     10. PRÉ-CARREGAMENTO DAS IMAGENS
     ========================================================= */

  function preloadGalleryImages() {

    galleryImages.forEach(
      (src) => {

        const image =
          new Image();


        image.src =
          src;

      }
    );

  }


  window.addEventListener(
    "load",
    preloadGalleryImages
  );


  /* =========================================================
     11. LIGHTBOX
     ========================================================= */

  const galleryLightbox =
    $("#kehaiBookLightbox");


  const galleryLightboxImage =
    $("#kehaiBookLightboxImage");


  const galleryLightboxCounter =
    $("#kehaiBookLightboxCounter");


  const galleryLightboxClose =
    $("#kehaiBookLightboxClose");


  const galleryLightboxPrev =
    $("#kehaiBookLightboxPrev");


  const galleryLightboxNext =
    $("#kehaiBookLightboxNext");


  function updateGalleryLightbox() {

    if (
      !galleryLightboxImage ||
      !galleryImages.length
    ) {
      return;
    }


    galleryLightboxImage.src =
      galleryImages[
        currentGalleryIndex
      ];


    if (
      galleryLightboxCounter
    ) {

      const current =
        String(
          currentGalleryIndex + 1
        ).padStart(
          2,
          "0"
        );


      const total =
        String(
          galleryImages.length
        ).padStart(
          2,
          "0"
        );


      galleryLightboxCounter.textContent =
        `${current} / ${total}`;

    }

  }


  function openGalleryLightbox() {

    if (
      !galleryLightbox ||
      !galleryImages.length
    ) {
      return;
    }


    updateGalleryLightbox();


    galleryLightbox
      .classList
      .add(
        "is-open"
      );


    galleryLightbox
      .setAttribute(
        "aria-hidden",
        "false"
      );


    document.body.style.overflow =
      "hidden";


    trackEvent(
      "open_book_preview",
      {
        page:
          currentGalleryIndex + 1
      }
    );


    galleryLightboxClose
      ?.focus();

  }


  function closeGalleryLightbox() {

    if (
      !galleryLightbox
    ) {
      return;
    }


    galleryLightbox
      .classList
      .remove(
        "is-open"
      );


    galleryLightbox
      .setAttribute(
        "aria-hidden",
        "true"
      );


    document.body.style.overflow =
      "";


    galleryMainButton
      ?.focus();

  }


  function galleryPrevious() {

    if (
      !galleryImages.length
    ) {
      return;
    }


    const previousIndex =
      (
        currentGalleryIndex
        -
        1
        +
        galleryImages.length
      )
      %
      galleryImages.length;


    setGalleryImage(
      previousIndex,
      false
    );


    updateGalleryLightbox();

  }


  function galleryNext() {

    if (
      !galleryImages.length
    ) {
      return;
    }


    const nextIndex =
      (
        currentGalleryIndex
        +
        1
      )
      %
      galleryImages.length;


    setGalleryImage(
      nextIndex,
      false
    );


    updateGalleryLightbox();

  }


  /* =========================================================
     12. IMAGEM PRINCIPAL ABRE O LIGHTBOX
     ========================================================= */

  galleryMainButton
    ?.addEventListener(
      "click",
      () => {

        openGalleryLightbox();

      }
    );


  /* =========================================================
     13. CONTROLES DO LIGHTBOX
     ========================================================= */

  galleryLightboxClose
    ?.addEventListener(
      "click",
      closeGalleryLightbox
    );


  galleryLightboxPrev
    ?.addEventListener(
      "click",
      galleryPrevious
    );


  galleryLightboxNext
    ?.addEventListener(
      "click",
      galleryNext
    );


  /*
    Clicar fora da imagem fecha.
  */

  galleryLightbox
    ?.addEventListener(
      "click",
      (event) => {

        if (
          event.target ===
          galleryLightbox
        ) {

          closeGalleryLightbox();

        }

      }
    );


  /*
    Teclado.
  */

  document.addEventListener(
    "keydown",
    (event) => {

      const lightboxOpen =
        galleryLightbox
          ?.classList
          .contains(
            "is-open"
          );


      if (!lightboxOpen) {
        return;
      }


      if (
        event.key === "Escape"
      ) {

        closeGalleryLightbox();

      }


      if (
        event.key === "ArrowLeft"
      ) {

        galleryPrevious();

      }


      if (
        event.key === "ArrowRight"
      ) {

        galleryNext();

      }

    }
  );


  /* =========================================================
     14. SWIPE NO LIGHTBOX MOBILE
     ========================================================= */

  let touchStartX =
    0;


  let touchEndX =
    0;


  galleryLightbox
    ?.addEventListener(
      "touchstart",
      (event) => {

        touchStartX =
          event.changedTouches[0]
            ?.screenX || 0;

      },
      {
        passive: true
      }
    );


  galleryLightbox
    ?.addEventListener(
      "touchend",
      (event) => {

        touchEndX =
          event.changedTouches[0]
            ?.screenX || 0;


        const difference =
          touchEndX -
          touchStartX;


        if (
          Math.abs(
            difference
          ) < 45
        ) {

          return;

        }


        if (
          difference > 0
        ) {

          galleryPrevious();

        }

        else {

          galleryNext();

        }

      },
      {
        passive: true
      }
    );


  /* =========================================================
     15. FAQ
     ========================================================= */

  const faqItems =
    $$(
      ".kehai-book-faq__item"
    );


  faqItems.forEach(

    (item) => {

      const button =
        $("button", item);


      const icon =
        $(
          ".kehai-book-faq__icon",
          item
        );


      if (!button) {
        return;
      }


      button.setAttribute(
        "aria-expanded",
        "false"
      );


      button.addEventListener(

        "click",

        () => {

          const isOpen =
            item.classList.contains(
              "is-open"
            );


          faqItems.forEach(

            (otherItem) => {

              if (
                otherItem === item
              ) {
                return;
              }


              otherItem.classList.remove(
                "is-open"
              );


              const otherButton =
                $(
                  "button",
                  otherItem
                );


              const otherIcon =
                $(
                  ".kehai-book-faq__icon",
                  otherItem
                );


              otherButton
                ?.setAttribute(
                  "aria-expanded",
                  "false"
                );


              if (otherIcon) {

                otherIcon.textContent =
                  "+";

              }

            }

          );


          item.classList.toggle(
            "is-open",
            !isOpen
          );


          button.setAttribute(
            "aria-expanded",
            String(!isOpen)
          );


          if (icon) {

            icon.textContent =
              !isOpen
                ? "−"
                : "+";

          }


          if (!isOpen) {

            const question =
              button
                .querySelector("span")
                ?.textContent
                ?.trim() || "";


            trackEvent(

              "faq_open",

              {
                question:
                  question
              }

            );

          }

        }

      );

    }

  );


  /* =========================================================
     16. BARRA DE COMPRA MOBILE
     ========================================================= */

  const hero =
    $(".kehai-book-hero");


  const mobileBuyBar =
    $("#kehaiBookMobileBuy");


  const footer =
    $(".kehai-book-footer");


  let heroVisible =
    true;


  let footerVisible =
    false;


  function updateMobileBuyBar() {

    if (!mobileBuyBar) {
      return;
    }


    const mobile =
      window.innerWidth <= 767;


    const shouldShow =
      mobile
      &&
      !heroVisible
      &&
      !footerVisible;


    mobileBuyBar.classList.toggle(

      "is-visible",

      shouldShow

    );

  }


  if (
    "IntersectionObserver" in window
  ) {


    if (hero) {

      const heroObserver =
        new IntersectionObserver(

          (entries) => {

            const entry =
              entries[0];


            heroVisible =
              entry.isIntersecting;


            updateMobileBuyBar();

          },

          {

            threshold:
              0.08

          }

        );


      heroObserver.observe(
        hero
      );

    }


    if (footer) {

      const footerObserver =
        new IntersectionObserver(

          (entries) => {

            const entry =
              entries[0];


            footerVisible =
              entry.isIntersecting;


            updateMobileBuyBar();

          },

          {

            threshold:
              0.01

          }

        );


      footerObserver.observe(
        footer
      );

    }

  }


  window.addEventListener(

    "resize",

    updateMobileBuyBar

  );


  /* =========================================================
     17. CTA MOBILE
     ========================================================= */

  const mobileBuyButton =
    mobileBuyBar?.querySelector(
      "a"
    );


  mobileBuyButton?.addEventListener(

    "click",

    () => {

      trackEvent(
        "click_mobile_buy_bar"
      );

    }

  );


  /* =========================================================
     18. REVEAL EDITORIAL
     ========================================================= */

  const revealSelectors = [

    ".kehai-book-eyebrow",

    ".kehai-book-section-title",

    ".kehai-book-movement",

    ".kehai-book-provocation__examples",

    ".kehai-book-provocation__closing",

    ".kehai-book-editorial-text",

    ".kehai-book-definition__lead",

    ".kehai-book-definition__text",

    ".kehai-book-audience__roles",

    ".kehai-book-gallery",

    ".kehai-book-author__photo",

    ".kehai-book-author__content",

    ".kehai-book-offer",

    ".kehai-book-corporate__quantities",

    ".kehai-book-manifesto"

  ];


  const revealElements =
    $$(
      revealSelectors.join(",")
    );


  if (!reducedMotion) {

    revealElements.forEach(

      (element) => {

        element.style.opacity =
          "0";


        element.style.transform =
          "translateY(12px)";


        element.style.transition =
          "opacity 620ms cubic-bezier(.22,.61,.36,1), transform 620ms cubic-bezier(.22,.61,.36,1)";

      }

    );


    if (
      "IntersectionObserver" in window
    ) {

      const revealObserver =
        new IntersectionObserver(

          (entries, observer) => {

            entries.forEach(

              (entry) => {

                if (
                  !entry.isIntersecting
                ) {
                  return;
                }


                entry.target.style.opacity =
                  "1";


                entry.target.style.transform =
                  "translateY(0)";


                observer.unobserve(
                  entry.target
                );

              }

            );

          },

          {

            threshold:
              0.08,

            rootMargin:
              "0px 0px -6% 0px"

          }

        );


      revealElements.forEach(

        (element, index) => {

          element.style.transitionDelay =
            `${(index % 4) * 60}ms`;


          revealObserver.observe(
            element
          );

        }

      );

    }

    else {

      revealElements.forEach(

        (element) => {

          element.style.opacity =
            "1";


          element.style.transform =
            "translateY(0)";

        }

      );

    }

  }


  /* =========================================================
     19. PROFUNDIDADE DE SCROLL
     ========================================================= */

  const scrollMilestones =
    new Set();


  function trackScrollDepth() {

    const pageHeight =
      document.documentElement.scrollHeight
      -
      window.innerHeight;


    if (
      pageHeight <= 0
    ) {
      return;
    }


    const percentage =
      Math.round(

        (
          window.scrollY
          /
          pageHeight
        )
        *
        100

      );


    [

      25,

      50,

      75,

      90

    ].forEach(

      (milestone) => {

        if (

          percentage >= milestone

          &&

          !scrollMilestones.has(
            milestone
          )

        ) {

          scrollMilestones.add(
            milestone
          );


          trackEvent(

            "scroll_depth",

            {
              percent:
                milestone
            }

          );

        }

      }

    );

  }


  window.addEventListener(

    "scroll",

    trackScrollDepth,

    {
      passive:
        true
    }

  );


  /* =========================================================
     20. HERO PARALLAX MUITO DISCRETO
     ========================================================= */

  const heroBook =
    $(".kehai-book-hero__image--desktop img");


  function updateHeroBookPosition() {

    if (

      reducedMotion

      ||

      window.innerWidth <= 767

      ||

      !heroBook

    ) {

      return;

    }


    const scroll =
      Math.min(
        window.scrollY,
        500
      );


    const movement =
      scroll * 0.018;


    heroBook.style.transform =
      `rotate(-2deg) translateY(${movement}px)`;

  }


  window.addEventListener(

    "scroll",

    updateHeroBookPosition,

    {
      passive:
        true
    }

  );


  /* =========================================================
     21. VIEW BOOK
     ========================================================= */

  trackEvent(

    "view_book",

    {

      page:
        "/kehai/livro",

      title:
        "KEHAI"

    }

  );


  /* =========================================================
     22. EXPÕE CONFIGURAÇÃO PARA DEBUG
     ========================================================= */

  window.KEHAI_CONFIG =
    KEHAI_CONFIG;


})();
