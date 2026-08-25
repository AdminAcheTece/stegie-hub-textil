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
       4. COMPRA DO LIVRO FÍSICO
       CEP → FRETE → PEDIDO → MERCADO PAGO
       ========================================================= */

    const physicalButtons =
      $$("[data-kehai-checkout-trigger]");


    const signedButton =
      $("#kehaiBuySigned");


    const ebookButton =
      $("#kehaiBuyEbook");


    const corporateButton =
      $("#kehaiCorporate");


    const checkout =
      $("#kehaiCheckout");


    const checkoutDialog =
      $("#kehaiCheckoutDialog");


    const checkoutForm =
      $("#kehaiCheckoutForm");


    const checkoutCloseButtons =
      $$("[data-kehai-checkout-close]");


    const checkoutCep =
      $("#kehaiCheckoutCep");


    const checkoutCalculateShipping =
      $("#kehaiCheckoutCalculateShipping");


    const checkoutShippingStatus =
      $("#kehaiCheckoutShippingStatus");


    const checkoutShippingOptions =
      $("#kehaiCheckoutShippingOptions");


    const checkoutName =
      $("#kehaiCheckoutName");


    const checkoutEmail =
      $("#kehaiCheckoutEmail");


    const checkoutPhone =
      $("#kehaiCheckoutPhone");


    const checkoutDocument =
      $("#kehaiCheckoutDocument");


    const checkoutStreet =
      $("#kehaiCheckoutStreet");


    const checkoutNumber =
      $("#kehaiCheckoutNumber");


    const checkoutComplement =
      $("#kehaiCheckoutComplement");


    const checkoutDistrict =
      $("#kehaiCheckoutDistrict");


    const checkoutCity =
      $("#kehaiCheckoutCity");


    const checkoutState =
      $("#kehaiCheckoutState");


    const checkoutShippingLabel =
      $("#kehaiCheckoutShippingLabel");


    const checkoutShippingPrice =
      $("#kehaiCheckoutShippingPrice");


    const checkoutTotal =
      $("#kehaiCheckoutTotal");


    const checkoutError =
      $("#kehaiCheckoutError");


    const checkoutSubmit =
      $("#kehaiCheckoutSubmit");


    const checkoutProgressShipping =
      $("[data-kehai-progress='shipping']");


    const checkoutProgressData =
      $("[data-kehai-progress='data']");


    const checkoutProgressPayment =
      $("[data-kehai-progress='payment']");


    const KEHAI_PHYSICAL_PRICE_CENTS =
      7990;


    const checkoutStateData = {

      selectedShipping:
        null,

      quotedCep:
        "",

      orderNumber:
        null,

      submitting:
        false,

      lastTrigger:
        null

    };


    const brlFormatter =
      new Intl.NumberFormat(
        "pt-BR",
        {
          style:
            "currency",

          currency:
            "BRL"
        }
      );


    function moneyFromCents(
      cents
    ) {

      return brlFormatter.format(
        Number(cents || 0) / 100
      );

    }


    function normalizeCep(
      value
    ) {

      const digits =
        String(value || "")
          .replace(/\D/g, "")
          .slice(0, 8);


      return digits.length === 8
        ? digits
        : "";

    }


    function formatCep(
      value
    ) {

      const digits =
        String(value || "")
          .replace(/\D/g, "")
          .slice(0, 8);


      if (
        digits.length <= 5
      ) {

        return digits;

      }


      return (
        digits.slice(0, 5)
        +
        "-"
        +
        digits.slice(5)
      );

    }


    function formatPhone(
      value
    ) {

      const digits =
        String(value || "")
          .replace(/\D/g, "")
          .slice(0, 11);


      if (
        digits.length <= 2
      ) {

        return digits;

      }


      if (
        digits.length <= 6
      ) {

        return (
          `(${digits.slice(0, 2)}) `
          +
          digits.slice(2)
        );

      }


      if (
        digits.length <= 10
      ) {

        return (
          `(${digits.slice(0, 2)}) `
          +
          `${digits.slice(2, 6)}-`
          +
          digits.slice(6)
        );

      }


      return (
        `(${digits.slice(0, 2)}) `
        +
        `${digits.slice(2, 7)}-`
        +
        digits.slice(7)
      );

    }


    function formatCpf(
      value
    ) {

      const digits =
        String(value || "")
          .replace(/\D/g, "")
          .slice(0, 11);


      if (digits.length <= 3) {
        return digits;
      }


      if (digits.length <= 6) {
        return `${digits.slice(0, 3)}.${digits.slice(3)}`;
      }


      if (digits.length <= 9) {
        return (
          `${digits.slice(0, 3)}.`
          +
          `${digits.slice(3, 6)}.`
          +
          digits.slice(6)
        );
      }


      return (
        `${digits.slice(0, 3)}.`
        +
        `${digits.slice(3, 6)}.`
        +
        `${digits.slice(6, 9)}-`
        +
        digits.slice(9)
      );

    }


    function setCheckoutError(
      message = ""
    ) {

      if (!checkoutError) {
        return;
      }


      checkoutError.textContent =
        message;


      checkoutError.classList.toggle(
        "is-visible",
        Boolean(message)
      );

    }


    function setShippingStatus(
      message = "",
      type = ""
    ) {

      if (!checkoutShippingStatus) {
        return;
      }


      checkoutShippingStatus.textContent =
        message;


      checkoutShippingStatus.classList.remove(
        "is-loading",
        "is-error",
        "is-success"
      );


      if (type) {

        checkoutShippingStatus
          .classList
          .add(
            `is-${type}`
          );

      }

    }


    function invalidateCreatedOrder() {

      checkoutStateData.orderNumber =
        null;

    }


    function resetShippingSelection(
      options = {}
    ) {

      checkoutStateData.selectedShipping =
        null;


      checkoutStateData.quotedCep =
        "";


      invalidateCreatedOrder();


      if (
        checkoutShippingOptions
        &&
        options.keepOptions !== true
      ) {

        checkoutShippingOptions.innerHTML =
          "";

      }


      if (
        checkoutShippingLabel
      ) {

        checkoutShippingLabel.textContent =
          "Frete";

      }


      if (
        checkoutShippingPrice
      ) {

        checkoutShippingPrice.textContent =
          "A calcular";

      }


      if (
        checkoutTotal
      ) {

        checkoutTotal.textContent =
          moneyFromCents(
            KEHAI_PHYSICAL_PRICE_CENTS
          );

      }


      updateCheckoutReadiness();

    }


    function updateCheckoutSummary() {

      const shipping =
        checkoutStateData.selectedShipping;


      const shippingCents =
        shipping
          ? Number(shipping.preco_cents || 0)
          : 0;


      if (
        checkoutShippingLabel
      ) {

        checkoutShippingLabel.textContent =
          shipping
            ? (
                "Frete — "
                +
                shipping.servico
              )
            : "Frete";

      }


      if (
        checkoutShippingPrice
      ) {

        checkoutShippingPrice.textContent =
          shipping
            ? moneyFromCents(
                shippingCents
              )
            : "A calcular";

      }


      if (
        checkoutTotal
      ) {

        checkoutTotal.textContent =
          moneyFromCents(
            KEHAI_PHYSICAL_PRICE_CENTS
            +
            shippingCents
          );

      }

    }


    function selectShippingOption(
      shippingId
    ) {

      if (
        !checkoutShippingOptions
      ) {
        return;
      }


      const optionElement =
        checkoutShippingOptions
          .querySelector(
            `[data-shipping-id="${CSS.escape(String(shippingId))}"]`
          );


      if (!optionElement) {
        return;
      }


      const raw =
        optionElement
          .dataset
          .shippingData;


      if (!raw) {
        return;
      }


      try {

        checkoutStateData.selectedShipping =
          JSON.parse(raw);

      }

      catch (error) {

        console.error(
          "[KEHAI] Opção de frete inválida:",
          error
        );

        return;

      }


      $$(
        ".kehai-book-checkout__shipping-option",
        checkoutShippingOptions
      ).forEach(
        (element) => {

          const selected =
            element ===
            optionElement;


          element.classList.toggle(
            "is-selected",
            selected
          );


          const radio =
            $("input[type='radio']", element);


          if (radio) {

            radio.checked =
              selected;

          }

        }
      );


      invalidateCreatedOrder();


      updateCheckoutSummary();


      updateCheckoutReadiness();


      trackEvent(
        "select_shipping",
        {
          service:
            checkoutStateData
              .selectedShipping
              ?.servico,

          company:
            checkoutStateData
              .selectedShipping
              ?.transportadora,

          price:
            checkoutStateData
              .selectedShipping
              ?.preco
        }
      );

    }


    function renderShippingOptions(
      options
    ) {

      if (
        !checkoutShippingOptions
      ) {
        return;
      }


      checkoutShippingOptions.innerHTML =
        "";


      const normalized =
        (Array.isArray(options)
          ? options
          : [])
          .map(
            (item) => {

              const priceNumber =
                Number.parseFloat(
                  String(item.preco || "0")
                    .replace(",", ".")
                );


              return {
                ...item,

                preco_cents:
                  Math.round(
                    priceNumber * 100
                  )
              };

            }
          )
          .filter(
            (item) =>
              item.id
              &&
              Number.isFinite(
                item.preco_cents
              )
          )
          .sort(
            (a, b) =>
              a.preco_cents
              -
              b.preco_cents
          );


      if (
        !normalized.length
      ) {

        setShippingStatus(
          "Não encontramos uma opção de entrega para este CEP.",
          "error"
        );


        resetShippingSelection({
          keepOptions:
            true
        });


        return;

      }


      normalized.forEach(
        (item) => {

          const label =
            document.createElement(
              "label"
            );


          label.className =
            "kehai-book-checkout__shipping-option";


          label.dataset.shippingId =
            String(item.id);


          label.dataset.shippingData =
            JSON.stringify(
              item
            );


          const prazo =
            item.prazo_dias
              ? (
                  `${item.prazo_dias} `
                  +
                  (
                    Number(item.prazo_dias) === 1
                      ? "dia útil"
                      : "dias úteis"
                  )
                )
              : "Prazo informado pela transportadora";


          label.innerHTML =
            `
              <input
                type="radio"
                name="kehai_shipping"
                value="${String(item.id)}"
              >

              <span class="kehai-book-checkout__shipping-option-main">

                <strong>
                  ${item.servico || "Entrega"}
                  ·
                  ${item.transportadora || "Transportadora"}
                </strong>

                <span>
                  Prazo estimado: ${prazo}
                </span>

              </span>

              <span class="kehai-book-checkout__shipping-option-price">
                ${moneyFromCents(item.preco_cents)}
              </span>
            `;


          const radio =
            $("input", label);


          radio?.addEventListener(
            "change",
            () => {

              selectShippingOption(
                item.id
              );

            }
          );


          checkoutShippingOptions
            .appendChild(
              label
            );

        }
      );


      selectShippingOption(
        normalized[0].id
      );


      setShippingStatus(
        normalized.length === 1
          ? "Opção de entrega encontrada."
          : `${normalized.length} opções de entrega encontradas.`,
        "success"
      );

    }


    async function fetchJson(
      url,
      options = {}
    ) {

      const response =
        await fetch(
          url,
          options
        );


      let data =
        {};


      try {

        data =
          await response.json();

      }

      catch (error) {

        data =
          {};

      }


      if (!response.ok) {

        throw new Error(
          data.error
          ||
          "Não foi possível concluir a solicitação."
        );

      }


      return data;

    }


    async function autofillAddressByCep(
      cep
    ) {

      if (!cep) {
        return;
      }


      try {

        const response =
          await fetch(
            `https://viacep.com.br/ws/${cep}/json/`,
            {
              headers: {
                "Accept":
                  "application/json"
              }
            }
          );


        if (!response.ok) {
          return;
        }


        const data =
          await response.json();


        if (
          !data
          ||
          data.erro
        ) {
          return;
        }


        if (
          checkoutStreet
          &&
          data.logradouro
        ) {

          checkoutStreet.value =
            data.logradouro;

        }


        if (
          checkoutDistrict
          &&
          data.bairro
        ) {

          checkoutDistrict.value =
            data.bairro;

        }


        if (
          checkoutCity
          &&
          data.localidade
        ) {

          checkoutCity.value =
            data.localidade;

        }


        if (
          checkoutState
          &&
          data.uf
        ) {

          checkoutState.value =
            String(data.uf)
              .toUpperCase();

        }


        invalidateCreatedOrder();

      }

      catch (error) {

        /*
          O preenchimento automático é
          apenas uma conveniência.
          A compra continua funcionando
          caso o serviço externo esteja
          indisponível.
        */

        console.info(
          "[KEHAI] CEP sem preenchimento automático."
        );

      }

    }


    async function calculateShipping() {

      const cep =
        normalizeCep(
          checkoutCep?.value
        );


      setCheckoutError();


      if (!cep) {

        checkoutCep
          ?.classList
          .add(
            "is-invalid"
          );


        setShippingStatus(
          "Digite um CEP válido com 8 números.",
          "error"
        );


        checkoutCep
          ?.focus();


        return;

      }


      checkoutCep
        ?.classList
        .remove(
          "is-invalid"
        );


      resetShippingSelection();


      checkoutStateData.quotedCep =
        cep;


      setShippingStatus(
        "Consultando as opções de entrega...",
        "loading"
      );


      if (
        checkoutCalculateShipping
      ) {

        checkoutCalculateShipping.disabled =
          true;


        checkoutCalculateShipping.textContent =
          "Calculando...";

      }


      try {

        const data =
          await fetchJson(
            "/api/kehai/frete",
            {
              method:
                "POST",

              headers: {
                "Content-Type":
                  "application/json"
              },

              body:
                JSON.stringify({
                  cep:
                    cep
                })
            }
          );


        if (!data.success) {

          throw new Error(
            data.error
            ||
            "Não foi possível calcular o frete."
          );

        }


        checkoutStateData.quotedCep =
          cep;


        renderShippingOptions(
          data.opcoes
        );


        autofillAddressByCep(
          cep
        );


        trackEvent(
          "calculate_shipping",
          {
            cep_prefix:
              cep.slice(0, 5),

            options:
              Array.isArray(data.opcoes)
                ? data.opcoes.length
                : 0
          }
        );

      }

      catch (error) {

        console.error(
          "[KEHAI] Erro ao calcular frete:",
          error
        );


        resetShippingSelection();


        setShippingStatus(
          error.message
          ||
          "Não foi possível calcular o frete agora.",
          "error"
        );

      }

      finally {

        if (
          checkoutCalculateShipping
        ) {

          checkoutCalculateShipping.disabled =
            false;


          checkoutCalculateShipping.textContent =
            "Calcular frete";

        }


        updateCheckoutReadiness();

      }

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


      checkoutStateData.lastTrigger =
        trigger
        ||
        document.activeElement;


      checkout.classList.add(
        "is-open"
      );


      checkout.setAttribute(
        "aria-hidden",
        "false"
      );


      document.body.classList.add(
        "kehai-checkout-open"
      );


      setCheckoutError();


      updateCheckoutReadiness();


      window.requestAnimationFrame(
        () => {

          (
            checkoutCep
            ||
            checkoutDialog
          )
            ?.focus();

        }
      );


      trackEvent(
        "open_checkout_physical"
      );

    }


    function closeCheckout() {

      if (!checkout) {
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
        "kehai-checkout-open"
      );


      checkoutStateData
        .lastTrigger
        ?.focus?.();

    }


    function shippingIsReady() {

      const cep =
        normalizeCep(
          checkoutCep?.value
        );


      return Boolean(
        cep
        &&
        cep === checkoutStateData.quotedCep
        &&
        checkoutStateData.selectedShipping
      );

    }


    function customerDataIsReady() {

      const requiredInputs = [
        checkoutName,
        checkoutEmail,
        checkoutPhone,
        checkoutDocument,
        checkoutStreet,
        checkoutNumber,
        checkoutDistrict,
        checkoutCity,
        checkoutState
      ].filter(Boolean);


      const fieldsValid =
        requiredInputs.every(
          (input) => {

            const value =
              String(input.value || "")
                .trim();


            if (!value) {
              return false;
            }


            if (
              input.type === "email"
              &&
              !input.checkValidity()
            ) {
              return false;
            }


            if (
              input === checkoutState
              &&
              !/^[A-Za-z]{2}$/
                .test(value)
            ) {
              return false;
            }


            return true;

          }
        );


      const phoneDigits =
        String(
          checkoutPhone?.value || ""
        )
          .replace(/\D/g, "");


      const documentDigits =
        String(
          checkoutDocument?.value || ""
        )
          .replace(/\D/g, "");


      return (
        fieldsValid
        &&
        phoneDigits.length >= 10
        &&
        documentDigits.length === 11
      );

    }


    function updateCheckoutProgress() {

      const shippingReady =
        shippingIsReady();


      const dataReady =
        customerDataIsReady();


      const paymentReady =
        shippingReady
        &&
        dataReady;


      [
        checkoutProgressShipping,
        checkoutProgressData,
        checkoutProgressPayment
      ]
        .filter(Boolean)
        .forEach(
          (step) => {
            step.classList.remove(
              "is-active",
              "is-complete"
            );
          }
        );


      if (checkoutProgressShipping) {

        checkoutProgressShipping
          .classList
          .toggle(
            "is-complete",
            shippingReady
          );

        checkoutProgressShipping
          .classList
          .toggle(
            "is-active",
            !shippingReady
          );

      }


      if (checkoutProgressData) {

        checkoutProgressData
          .classList
          .toggle(
            "is-complete",
            paymentReady
          );

        checkoutProgressData
          .classList
          .toggle(
            "is-active",
            shippingReady
            &&
            !dataReady
          );

      }


      if (checkoutProgressPayment) {

        checkoutProgressPayment
          .classList
          .toggle(
            "is-active",
            paymentReady
          );

      }

    }


    function updateCheckoutReadiness() {

      updateCheckoutProgress();


      if (!checkoutSubmit) {
        return;
      }


      const ready =
        shippingIsReady()
        &&
        customerDataIsReady();


      const disabled =
        !ready
        ||
        checkoutStateData.submitting;


      checkoutSubmit.disabled =
        disabled;


      checkoutSubmit.setAttribute(
        "aria-disabled",
        String(disabled)
      );


      if (
        !checkoutStateData.submitting
      ) {

        checkoutSubmit.textContent =
          ready
            ? "Ir para o pagamento"
            : "Complete os dados para continuar";

      }

    }


    function validateCheckoutForm() {

      setCheckoutError();


      const cep =
        normalizeCep(
          checkoutCep?.value
        );


      if (
        !cep
        ||
        cep !==
          checkoutStateData.quotedCep
        ||
        !checkoutStateData.selectedShipping
      ) {

        setCheckoutError(
          "Calcule o frete e confirme uma opção de entrega antes de continuar."
        );


        checkoutCep
          ?.focus();


        return false;

      }


      const requiredInputs = [

        checkoutName,
        checkoutEmail,
        checkoutPhone,
        checkoutDocument,
        checkoutStreet,
        checkoutNumber,
        checkoutDistrict,
        checkoutCity,
        checkoutState

      ].filter(Boolean);


      let firstInvalid =
        null;


      requiredInputs.forEach(
        (input) => {

          const value =
            String(
              input.value || ""
            ).trim();


          let valid =
            Boolean(value);


          if (
            input.type === "email"
          ) {

            valid =
              valid
              &&
              input.checkValidity();

          }


          if (
            input === checkoutState
          ) {

            valid =
              /^[A-Za-z]{2}$/
                .test(value);

          }


          input.classList.toggle(
            "is-invalid",
            !valid
          );


          if (
            !valid
            &&
            !firstInvalid
          ) {

            firstInvalid =
              input;

          }

        }
      );


      if (firstInvalid) {

        setCheckoutError(
          "Revise os campos destacados antes de continuar."
        );


        firstInvalid.focus();


        return false;

      }


      const phoneDigits =
        String(
          checkoutPhone?.value || ""
        )
          .replace(/\D/g, "");


      if (
        phoneDigits.length < 10
      ) {

        checkoutPhone
          ?.classList
          .add(
            "is-invalid"
          );


        setCheckoutError(
          "Informe um telefone válido com DDD."
        );


        checkoutPhone
          ?.focus();


        return false;

      }


      const documentDigits =
        String(
          checkoutDocument?.value || ""
        )
          .replace(/\D/g, "");


      if (
        documentDigits.length !== 11
      ) {

        checkoutDocument
          ?.classList
          .add(
            "is-invalid"
          );


        setCheckoutError(
          "Informe um CPF válido com 11 dígitos."
        );


        checkoutDocument
          ?.focus();


        return false;

      }


      return true;

    }


    function setCheckoutSubmitting(
      submitting
    ) {

      checkoutStateData.submitting =
        submitting;


      if (!checkoutSubmit) {
        return;
      }


      checkoutSubmit.setAttribute(
        "aria-busy",
        String(submitting)
      );


      if (submitting) {

        checkoutSubmit.disabled =
          true;


        checkoutSubmit.setAttribute(
          "aria-disabled",
          "true"
        );


        checkoutSubmit.textContent =
          "Preparando pagamento...";

      }

      else {

        updateCheckoutReadiness();

      }

    }


    async function createOrderIfNeeded() {

      if (
        checkoutStateData.orderNumber
      ) {

        return checkoutStateData.orderNumber;

      }


      const shipping =
        checkoutStateData.selectedShipping;


      const orderData =
        await fetchJson(
          "/api/kehai/pedido",
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
                  "physical",

                shipping_service_id:
                  String(shipping.id),

                customer: {

                  name:
                    checkoutName.value.trim(),

                  email:
                    checkoutEmail.value.trim(),

                  phone:
                    checkoutPhone.value
                      .replace(/\D/g, ""),

                  document:
                    checkoutDocument.value
                      .replace(/\D/g, "")

                },

                address: {

                  postal_code:
                    normalizeCep(
                      checkoutCep.value
                    ),

                  street:
                    checkoutStreet.value.trim(),

                  number:
                    checkoutNumber.value.trim(),

                  complement:
                    checkoutComplement
                      ?.value
                      ?.trim()
                      ||
                      "",

                  district:
                    checkoutDistrict.value.trim(),

                  city:
                    checkoutCity.value.trim(),

                  state:
                    checkoutState.value
                      .trim()
                      .toUpperCase()

                }

              })
          }
        );


      if (
        !orderData.success
        ||
        !orderData.order_number
      ) {

        throw new Error(
          orderData.error
          ||
          "Não foi possível criar o pedido."
        );

      }


      checkoutStateData.orderNumber =
        orderData.order_number;


      trackEvent(
        "create_order",
        {
          order_number:
            orderData.order_number,

          total:
            orderData.total
        }
      );


      return orderData.order_number;

    }


    async function openMercadoPagoForOrder(
      orderNumber
    ) {

      const checkoutData =
        await fetchJson(
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
                order_number:
                  orderNumber
              })
          }
        );


      if (
        !checkoutData.success
        ||
        !checkoutData.checkout_url
      ) {

        throw new Error(
          checkoutData.error
          ||
          "O Mercado Pago não retornou o checkout."
        );

      }


      trackEvent(
        "begin_payment",
        {
          order_number:
            orderNumber,

          destination:
            "mercado_pago"
        }
      );


      window.location.assign(
        checkoutData.checkout_url
      );

    }


    async function submitPhysicalOrder(
      event
    ) {

      event.preventDefault();


      if (
        checkoutStateData.submitting
      ) {
        return;
      }


      if (
        !validateCheckoutForm()
      ) {
        return;
      }


      setCheckoutSubmitting(
        true
      );


      setCheckoutError();


      try {

        const orderNumber =
          await createOrderIfNeeded();


        await openMercadoPagoForOrder(
          orderNumber
        );

      }

      catch (error) {

        console.error(
          "[KEHAI] Erro ao iniciar a compra:",
          error
        );


        setCheckoutError(
          error.message
          ||
          "Não foi possível iniciar o pagamento. Tente novamente."
        );


        setCheckoutSubmitting(
          false
        );

      }

    }


    updateCheckoutReadiness();


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


            alert(
              options.missingMessage
              ||
              "Esta modalidade estará disponível em breve."
            );

          }

        }
      );

    }


    /*
      Abre o checkout interno para
      todos os CTAs do livro físico.
    */
    physicalButtons.forEach(
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


    checkoutCalculateShipping
      ?.addEventListener(
        "click",
        calculateShipping
      );


    checkoutCep
      ?.addEventListener(
        "input",
        () => {

          const previous =
            normalizeCep(
              checkoutCep.value
            );


          checkoutCep.value =
            formatCep(
              checkoutCep.value
            );


          checkoutCep
            .classList
            .remove(
              "is-invalid"
            );


          if (
            checkoutStateData.quotedCep
            &&
            previous !==
              checkoutStateData.quotedCep
          ) {

            resetShippingSelection();


            setShippingStatus(
              "CEP alterado. Calcule o frete novamente."
            );

          }


          invalidateCreatedOrder();

        }
      );


    checkoutCep
      ?.addEventListener(
        "keydown",
        (event) => {

          if (
            event.key === "Enter"
          ) {

            event.preventDefault();


            calculateShipping();

          }

        }
      );


    checkoutPhone
      ?.addEventListener(
        "input",
        () => {

          checkoutPhone.value =
            formatPhone(
              checkoutPhone.value
            );

        }
      );


    checkoutDocument
      ?.addEventListener(
        "input",
        () => {

          checkoutDocument.value =
            formatCpf(
              checkoutDocument.value
            );

        }
      );


    checkoutState
      ?.addEventListener(
        "input",
        () => {

          checkoutState.value =
            checkoutState.value
              .replace(/[^A-Za-z]/g, "")
              .slice(0, 2)
              .toUpperCase();

        }
      );


    checkoutForm
      ?.querySelectorAll(
        "input"
      )
      .forEach(
        (input) => {

          input.addEventListener(
            "input",
            () => {

              input.classList.remove(
                "is-invalid"
              );


              if (
                input !== checkoutCep
              ) {

                invalidateCreatedOrder();

              }


              updateCheckoutReadiness();

            }
          );

        }
      );


    checkoutForm
      ?.addEventListener(
        "submit",
        submitPhysicalOrder
      );


    document.addEventListener(
      "keydown",
      (event) => {

        const checkoutOpen =
          checkout
            ?.classList
            .contains(
              "is-open"
            );


        if (!checkoutOpen) {
          return;
        }


        if (
          event.key === "Escape"
        ) {

          event.preventDefault();


          closeCheckout();


          return;

        }


        if (
          event.key !== "Tab"
          ||
          !checkoutDialog
        ) {
          return;
        }


        const focusable =
          $$(
            'button:not([disabled]), input:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
            checkoutDialog
          )
            .filter(
              (element) =>
                element.offsetParent !== null
            );


        if (!focusable.length) {
          return;
        }


        const first =
          focusable[0];


        const last =
          focusable[
            focusable.length - 1
          ];


        if (
          event.shiftKey
          &&
          document.activeElement === first
        ) {

          event.preventDefault();


          last.focus();

        }

        else if (
          !event.shiftKey
          &&
          document.activeElement === last
        ) {

          event.preventDefault();


          first.focus();

        }

      }
    );


    configureCommercialLink(
      signedButton,
      KEHAI_CONFIG.links.signed,
      "click_buy_signed",
      {
        missingMessage:
          "A edição autografada estará disponível em breve."
      }
    );


    configureCommercialLink(
      ebookButton,
      KEHAI_CONFIG.links.ebook,
      "click_buy_ebook",
      {
        newTab:
          true,

        missingMessage:
          "A versão digital estará disponível em breve."
      }
    );


    configureCommercialLink(
      corporateButton,
      KEHAI_CONFIG.links.corporate,
      "click_corporate",
      {
        newTab:
          true,

        missingMessage:
          "O canal de compras corporativas estará disponível em breve."
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
