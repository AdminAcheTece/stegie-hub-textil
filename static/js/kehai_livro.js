/* =========================================================
   KEHAI — LANDING PAGE DO LIVRO
   Arquivo: static/JS/kehai_livro.js
   ========================================================= */

(() => {

  "use strict";


  /* =========================================================
     1. CONFIGURAÇÕES COMERCIAIS
     =========================================================

     IMPORTANTE:

     Quando os canais de venda estiverem definidos,
     substitua apenas os links abaixo.

     Não será necessário alterar o restante do JavaScript.
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


  /*
   EXEMPLO FUTURO:

   links: {

     physical:
       "https://checkout.exemplo.com/kehai",

     signed:
       "https://checkout.exemplo.com/kehai-autografado",

     ebook:
       "https://www.amazon.com.br/....",

     corporate:
       "https://wa.me/55XXXXXXXXXXX"

   }

  */


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
     =========================================================

     Estrutura preparada para futura integração com:

     - Google Analytics 4
     - Google Tag Manager
     - Meta Pixel

     Nenhum ID é inventado aqui.
     ========================================================= */

  function trackEvent(
    eventName,
    data = {}
  ) {

    window.dataLayer =
      window.dataLayer || [];


    window.dataLayer.push({

      event:
        eventName,

      ...data

    });


    /*
    Durante desenvolvimento você pode habilitar:

    console.log(
      "[KEHAI Analytics]",
      eventName,
      data
    );
    */

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



  /* =========================================================
     5. FUNÇÃO PARA CONFIGURAR LINKS
     ========================================================= */

  function configureCommercialLink(
    element,
    url,
    eventName,
    options = {}
  ) {

    if (!element) {
      return;
    }


    /*
     Se ainda não existe link configurado,
     evita que o botão envie o visitante para "#".
    */

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


        /*
         Enquanto o checkout não estiver configurado,
         impedimos navegação falsa.
        */

        if (!url) {

          event.preventDefault();


          console.warn(
            `[KEHAI] O link "${eventName}" ainda não foi configurado em KEHAI_CONFIG.links.`
          );

        }

      }
    );

  }



  /* =========================================================
     6. APLICA LINKS
     ========================================================= */

  physicalButtons.forEach(
    (button) => {

      configureCommercialLink(

        button,

        KEHAI_CONFIG.links.physical,

        "click_buy_physical"

      );

    }
  );


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
     7. MENU MOBILE
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


  /*
   Fecha o menu quando o visitante
   seleciona qualquer link.
  */

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



  /* =========================================================
     8. ESC PARA FECHAR MENU
     ========================================================= */

  document.addEventListener(

    "keydown",

    (event) => {

      if (
        event.key === "Escape"
      ) {

        closeMobileMenu();

      }

    }

  );



  /* =========================================================
     9. FECHA MENU AO VOLTAR PARA DESKTOP
     ========================================================= */

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
     10. SCROLL SUAVE PARA ÂNCORAS INTERNAS
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


          /*
           Compensa o header sticky.
          */

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

      });

    }

  );



  /* =========================================================
     GALERIA EDITORIAL — LIVRO POR DENTRO
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
    galleryThumbs.map(
      button =>
        button.dataset.image
    );


  let currentGalleryIndex =
    0;


  /* =========================================================
     TROCA A IMAGEM PRINCIPAL
     ========================================================= */

  function setGalleryImage(
    index
  ) {

    if (
      !galleryImages.length
      ||
      !galleryMain
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


    /*
      pequeno fade
    */

    galleryMain.style.opacity =
      "0";


    window.setTimeout(
      () => {

        galleryMain.src =
          galleryImages[
            currentGalleryIndex
          ];


        galleryMain.style.opacity =
          "1";

      },
      120
    );


    galleryThumbs.forEach(
      (
        thumb,
        index
      ) => {

        thumb.classList.toggle(
          "active",
          index === currentGalleryIndex
        );

      }
    );

  }


  /* =========================================================
     HOVER + CLIQUE NAS MINIATURAS
     ========================================================= */

  galleryThumbs.forEach(
    (
      thumb,
      index
    ) => {


      /*
        DESKTOP:
        passar o mouse já troca
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
        CLIQUE:
        troca a imagem e abre ampliada.
      */

      thumb.addEventListener(
        "click",
        () => {

          setGalleryImage(
            index
          );


          openGalleryLightbox(
            index
          );

        }
      );

    }
  );

  /* =========================================================
     LIGHTBOX
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
      !galleryLightboxImage
      ||
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

      galleryLightboxCounter.textContent =
        `${
          String(
            currentGalleryIndex + 1
          ).padStart(
            2,
            "0"
          )
        } / ${
          String(
            galleryImages.length
          ).padStart(
            2,
            "0"
          )
        }`;

    }

  }



  function openGalleryLightbox(
    index = currentGalleryIndex
  ) {

    if (
      !galleryLightbox
    ) {
      return;
    }


    currentGalleryIndex =
      index;


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

  }



  function galleryPrevious() {

    currentGalleryIndex =
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
      currentGalleryIndex
    );


    updateGalleryLightbox();

  }



  function galleryNext() {

    currentGalleryIndex =
      (
        currentGalleryIndex
        +
        1
      )
      %
      galleryImages.length;


    setGalleryImage(
      currentGalleryIndex
    );


    updateGalleryLightbox();

  }


  /* IMAGEM PRINCIPAL */

  galleryMainButton
    ?.addEventListener(
      "click",
      () => {

        openGalleryLightbox(
          currentGalleryIndex
        );

      }
    );


  /* FECHAR */

  galleryLightboxClose
    ?.addEventListener(
      "click",
      closeGalleryLightbox
    );


  /* SETAS */

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


  /* CLICAR FORA */

  galleryLightbox
    ?.addEventListener(
      "click",
      event => {

        if (
          event.target ===
          galleryLightbox
        ) {

          closeGalleryLightbox();

        }

      }
    );


  /* TECLADO */

  document.addEventListener(
    "keydown",
    event => {

      if (
        !galleryLightbox
          ?.classList
          .contains(
            "is-open"
          )
      ) {
        return;
      }


      if (
        event.key ===
        "Escape"
      ) {

        closeGalleryLightbox();

      }


      if (
        event.key ===
        "ArrowLeft"
      ) {

        galleryPrevious();

      }


      if (
        event.key ===
        "ArrowRight"
      ) {

        galleryNext();

      }

    }
  ); 
   
  /* =========================================================
     13. FAQ
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


      /*
       Complementa acessibilidade,
       mesmo que atributos não tenham
       sido inseridos no HTML original.
      */

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


          /*
           Fecha os outros.
           Assim o FAQ funciona como
           accordion editorial.
          */

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


          /*
           Alterna o atual.
          */

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
     14. BARRA DE COMPRA MOBILE
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


    /* HERO */

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



    /* FOOTER */

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
     15. CTA MOBILE
     ========================================================= */

  const mobileBuyButton =
    mobileBuyBar?.querySelector(
      "a"
    );


  /*
   Na V1 ele leva até a seção comercial.

   Quando o checkout estiver definido,
   podemos decidir se esse botão deve
   comprar diretamente ou continuar
   levando para as opções.
  */

  mobileBuyButton?.addEventListener(

    "click",

    () => {

      trackEvent(

        "click_mobile_buy_bar"

      );

    }

  );



  /* =========================================================
     16. REVEAL EDITORIAL
     =========================================================

     Adicionamos uma animação extremamente
     discreta sem precisar colocar classes
     manualmente em todo o HTML.
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


  /*
   Adiciona estilos mínimos via JS.

   Assim não precisamos alterar o CSS
   já criado apenas para as animações.
  */

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

          /*
           Pequeno stagger.
          */

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
     17. PROFUNDIDADE DE SCROLL
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
     18. HERO PARALLAX MUITO DISCRETO
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


    /*
     Apenas poucos pixels.
     O livro não deve parecer flutuando.
    */

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
     19. VIEW BOOK
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
     20. EXPÕE CONFIGURAÇÃO PARA DEBUG
     =========================================================

     Permite verificar no Console:

     KEHAI_CONFIG

     sem alterar internamente o código.
     ========================================================= */

  window.KEHAI_CONFIG =
    KEHAI_CONFIG;


})();
