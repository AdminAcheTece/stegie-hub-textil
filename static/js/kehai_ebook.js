(() => {

  "use strict";


  /* =====================================================
     HELPERS
     ===================================================== */

  const $ = (
    selector,
    context = document
  ) =>
    context.querySelector(
      selector
    );


  const $$ = (
    selector,
    context = document
  ) =>
    Array.from(
      context.querySelectorAll(
        selector
      )
    );


  async function fetchJson(
    url,
    options = {}
  ) {

    const response =
      await fetch(
        url,
        options
      );


    let data = {};


    try {

      data =
        await response.json();

    }

    catch {

      data = {};

    }


    if (!response.ok) {

      throw new Error(
        data.error
        ||
        "Não foi possível concluir a operação."
      );

    }


    return data;

  }


  /* =====================================================
     HEADER
     ===================================================== */

  const header =
    $("#kehaiEbookHeader");


  function updateHeader() {

    header
      ?.classList
      .toggle(
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

  const menuToggle =
    $("#kehaiEbookMenuToggle");


  const mobileMenu =
    $("#kehaiEbookMobileMenu");


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


  menuToggle
    ?.addEventListener(
      "click",
      () => {

        const isOpen =
          menuToggle
            .getAttribute(
              "aria-expanded"
            )
          ===
          "true";


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


  /* =====================================================
     CHECKOUT DIGITAL
     ===================================================== */

  const checkout =
    $("#kehaiEbookCheckout");


  const checkoutDialog =
    $("#kehaiEbookCheckoutDialog");


  const checkoutForm =
    $("#kehaiEbookCheckoutForm");


  const checkoutName =
    $("#kehaiEbookCheckoutName");


  const checkoutEmail =
    $("#kehaiEbookCheckoutEmail");


  const checkoutEmailConfirmation =
    $("#kehaiEbookCheckoutEmailConfirmation");


  const checkoutSubmit =
    $("#kehaiEbookCheckoutSubmit");


  const checkoutError =
    $("#kehaiEbookCheckoutError");


  const checkoutCloseButtons =
    $$(
      "[data-kehai-ebook-checkout-close]"
    );


  /*
    Captura automaticamente os
    CTAs existentes da página.

    Portanto não precisamos alterar
    os botões já criados na Etapa 2.
  */
  const buyButtons = [

    ...$$(
      'a[href="#comprar"]'
    ),

    $("#kehaiEbookBuyButton")

  ].filter(Boolean);


  let checkoutSubmitting =
    false;


  let checkoutLastTrigger =
    null;


  function setCheckoutError(
    message = ""
  ) {

    if (!checkoutError) {
      return;
    }


    if (!message) {

      checkoutError.hidden =
        true;

      checkoutError.textContent =
        "";

      return;

    }


    checkoutError.textContent =
      message;


    checkoutError.hidden =
      false;

  }


  function openCheckout(
    trigger = null
  ) {

    if (
      !checkout
      ||
      !checkoutDialog
    ) {
      return;
    }


    checkoutLastTrigger =
      trigger
      ||
      document.activeElement;


    closeMenu();


    checkout.classList.add(
      "is-open"
    );


    checkout.setAttribute(
      "aria-hidden",
      "false"
    );


    document.body.classList.add(
      "kehai-ebook-checkout-open"
    );


    setCheckoutError();


    window.requestAnimationFrame(
      () => {

        (
          checkoutName
          ||
          checkoutDialog
        )
          ?.focus();

      }
    );


    window.dataLayer =
      window.dataLayer || [];


    window.dataLayer.push({
      event:
        "open_checkout_ebook"
    });

  }


  function closeCheckout() {

    if (!checkout) {
      return;
    }


    if (
      checkoutSubmitting
    ) {
      return;
    }


    checkout.classList.remove(
      "is-open"
    );


    checkout.setAttribute(
      "aria-hidden",
      "true"
    );


    document.body.classList.remove(
      "kehai-ebook-checkout-open"
    );


    checkoutLastTrigger
      ?.focus?.();

  }


  function emailIsValid(
    input
  ) {

    return Boolean(
      input
      &&
      input.value.trim()
      &&
      input.checkValidity()
    );

  }


  function checkoutIsReady() {

    const name =
      checkoutName
        ?.value
        ?.trim()
      ||
      "";


    const email =
      checkoutEmail
        ?.value
        ?.trim()
        ?.toLowerCase()
      ||
      "";


    const confirmation =
      checkoutEmailConfirmation
        ?.value
        ?.trim()
        ?.toLowerCase()
      ||
      "";


    return Boolean(

      name.length >= 2

      &&

      emailIsValid(
        checkoutEmail
      )

      &&

      emailIsValid(
        checkoutEmailConfirmation
      )

      &&

      email === confirmation

    );

  }


  function updateCheckoutReadiness() {

    if (!checkoutSubmit) {
      return;
    }


    const ready =
      checkoutIsReady();


    checkoutSubmit.disabled =
      !ready
      ||
      checkoutSubmitting;


    checkoutSubmit.setAttribute(
      "aria-disabled",
      String(
        checkoutSubmit.disabled
      )
    );


    if (
      !checkoutSubmitting
    ) {

      checkoutSubmit.textContent =
        ready
          ?
          "Ir para o pagamento"
          :
          "Complete seus dados";

    }

  }


  function validateCheckout() {

    setCheckoutError();


    const name =
      checkoutName
        ?.value
        ?.trim()
      ||
      "";


    if (
      name.length < 2
    ) {

      checkoutName
        ?.classList
        .add(
          "is-invalid"
        );


      setCheckoutError(
        "Informe seu nome."
      );


      checkoutName
        ?.focus();


      return false;

    }


    if (
      !emailIsValid(
        checkoutEmail
      )
    ) {

      checkoutEmail
        ?.classList
        .add(
          "is-invalid"
        );


      setCheckoutError(
        "Informe um e-mail válido."
      );


      checkoutEmail
        ?.focus();


      return false;

    }


    if (
      !emailIsValid(
        checkoutEmailConfirmation
      )
    ) {

      checkoutEmailConfirmation
        ?.classList
        .add(
          "is-invalid"
        );


      setCheckoutError(
        "Confirme seu e-mail."
      );


      checkoutEmailConfirmation
        ?.focus();


      return false;

    }


    const email =
      checkoutEmail
        .value
        .trim()
        .toLowerCase();


    const confirmation =
      checkoutEmailConfirmation
        .value
        .trim()
        .toLowerCase();


    if (
      email
      !==
      confirmation
    ) {

      checkoutEmailConfirmation
        .classList
        .add(
          "is-invalid"
        );


      setCheckoutError(
        "Os dois e-mails precisam ser iguais."
      );


      checkoutEmailConfirmation
        .focus();


      return false;

    }


    return true;

  }


  function setSubmitting(
    submitting
  ) {

    checkoutSubmitting =
      submitting;


    if (!checkoutSubmit) {
      return;
    }


    checkoutSubmit.disabled =
      submitting;


    checkoutSubmit.setAttribute(
      "aria-busy",
      String(submitting)
    );


    if (submitting) {

      checkoutSubmit.textContent =
        "Preparando pagamento...";

    }

    else {

      updateCheckoutReadiness();

    }

  }


  async function submitCheckout(
    event
  ) {

    event.preventDefault();


    if (
      checkoutSubmitting
    ) {
      return;
    }


    if (
      !validateCheckout()
    ) {
      return;
    }


    setSubmitting(
      true
    );


    try {

      const data =
        await fetchJson(

          "/api/kehai/ebook/checkout",

          {

            method:
              "POST",

            headers: {

              "Content-Type":
                "application/json"

            },

            body:
              JSON.stringify({

                customer: {

                  name:
                    checkoutName
                      .value
                      .trim(),

                  email:
                    checkoutEmail
                      .value
                      .trim(),

                  email_confirmation:
                    checkoutEmailConfirmation
                      .value
                      .trim()

                }

              })

          }

        );


      if (
        !data.success
        ||
        !data.checkout_url
      ) {

        throw new Error(
          data.error
          ||
          "O Mercado Pago não retornou o checkout."
        );

      }


      window.dataLayer =
        window.dataLayer
        ||
        [];


      window.dataLayer.push({

        event:
          "begin_payment_ebook",

        order_number:
          data.order_number,

        value:
          29.90,

        currency:
          "BRL"

      });


      const paymentUrl =
        data.sandbox_checkout_url
        ||
        data.checkout_url;
      
      
      window.location.assign(
        paymentUrl
      );

    }


    catch (error) {

      console.error(
        "[KEHAI EBOOK] Checkout:",
        error
      );


      setCheckoutError(
        error.message
        ||
        "Não foi possível abrir o pagamento agora."
      );


      setSubmitting(
        false
      );

    }

  }


  /* =====================================================
     EVENTOS DOS BOTÕES
     ===================================================== */

  buyButtons.forEach(
    (button) => {

      button.addEventListener(
        "click",
        (event) => {

          event.preventDefault();

          openCheckout(
            button
          );

        }
      );

    }
  );


  checkoutCloseButtons.forEach(
    (button) => {

      button.addEventListener(
        "click",
        closeCheckout
      );

    }
  );


  [
    checkoutName,
    checkoutEmail,
    checkoutEmailConfirmation

  ]
    .filter(Boolean)
    .forEach(
      (input) => {

        input.addEventListener(
          "input",
          () => {

            input.classList.remove(
              "is-invalid"
            );


            setCheckoutError();


            updateCheckoutReadiness();

          }
        );

      }
    );


  checkoutForm
    ?.addEventListener(
      "submit",
      submitCheckout
    );


  /* =====================================================
     TECLA ESC
     ===================================================== */

  document.addEventListener(
    "keydown",
    (event) => {

      if (
        event.key === "Escape"
      ) {

        const checkoutOpen =
          checkout
            ?.classList
            .contains(
              "is-open"
            );


        if (checkoutOpen) {

          event.preventDefault();

          closeCheckout();

        }

        else {

          closeMenu();

        }

      }

    }
  );


  updateCheckoutReadiness();


  console.log(
    "[KEHAI] Landing e checkout do eBook carregados."
  );

})();
