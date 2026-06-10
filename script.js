const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const header = document.querySelector(".site-header");
const revealItems = document.querySelectorAll("[data-reveal], .person-card, .services-grid li");
const anchorLinks = document.querySelectorAll('a[href^="#"]');
const contactModal = document.querySelector("[data-contact-modal]");
const contactDialog = document.querySelector(".contact-modal__dialog");
const contactOpenButtons = document.querySelectorAll("[data-contact-open]");
const contactCloseButtons = document.querySelectorAll("[data-contact-close]");
const contactForm = document.querySelector("[data-contact-form]");
const formStatus = document.querySelector("[data-form-status]");
const focusableSelector = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "textarea:not([disabled])",
  "select:not([disabled])",
  "[tabindex]:not([tabindex='-1'])"
].join(",");
let previousFocus = null;

function updateHeaderState() {
  header?.classList.toggle("is-scrolled", window.scrollY > 12);
}

function scrollToSection(targetId, behavior = "smooth") {
  const target = document.querySelector(targetId);
  if (!target) return;

  const scrollTarget = targetId === "#contatti"
    ? document.querySelector(".final-cta")
    : target.querySelector(".section-heading, .contact-panel") || target;
  const headerHeight = header?.offsetHeight || 0;
  const extraOffset = targetId === "#contatti" ? 18 : 22;
  const top = scrollTarget.getBoundingClientRect().top + window.scrollY - headerHeight - extraOffset;

  window.scrollTo({
    top,
    behavior: reduceMotion ? "auto" : behavior
  });
}

if (!reduceMotion) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.16, rootMargin: "0px 0px -8% 0px" }
  );

  revealItems.forEach((item, index) => {
    item.style.setProperty("--reveal-delay", `${Math.min(index % 8, 7) * 55}ms`);
    observer.observe(item);
  });

  let ticking = false;
  function updateParallax() {
    const progress = Math.min(window.scrollY / 620, 1);
    document.documentElement.style.setProperty("--hero-shift", `${progress * 30}px`);
    ticking = false;
  }

  window.addEventListener("scroll", () => {
    updateHeaderState();
    if (!ticking) {
      window.requestAnimationFrame(updateParallax);
      ticking = true;
    }
  }, { passive: true });
} else {
  revealItems.forEach((item) => item.classList.add("is-visible"));
  window.addEventListener("scroll", updateHeaderState, { passive: true });
}

updateHeaderState();

function getModalFocusableItems() {
  if (!contactModal) return [];
  return Array.from(contactModal.querySelectorAll(focusableSelector))
    .filter((item) => item.offsetParent !== null);
}

function openContactModal() {
  if (!contactModal || !contactDialog) return;

  previousFocus = document.activeElement;
  contactModal.hidden = false;
  document.body.classList.add("modal-open");
  formStatus?.classList.remove("is-error", "is-success");
  if (formStatus) formStatus.textContent = "";

  window.requestAnimationFrame(() => {
    const firstInput = contactModal.querySelector("#contact-name");
    (firstInput || contactDialog).focus();
  });
}

function closeContactModal() {
  if (!contactModal) return;

  contactModal.hidden = true;
  document.body.classList.remove("modal-open");
  if (previousFocus && typeof previousFocus.focus === "function") {
    previousFocus.focus();
  }
}

function trapModalFocus(event) {
  if (!contactModal || contactModal.hidden || event.key !== "Tab") return;

  const focusableItems = getModalFocusableItems();
  if (!focusableItems.length) return;

  const firstItem = focusableItems[0];
  const lastItem = focusableItems[focusableItems.length - 1];

  if (event.shiftKey && document.activeElement === firstItem) {
    event.preventDefault();
    lastItem.focus();
  } else if (!event.shiftKey && document.activeElement === lastItem) {
    event.preventDefault();
    firstItem.focus();
  }
}

contactOpenButtons.forEach((button) => {
  button.addEventListener("click", openContactModal);
});

contactCloseButtons.forEach((button) => {
  button.addEventListener("click", closeContactModal);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && contactModal && !contactModal.hidden) {
    closeContactModal();
    return;
  }

  trapModalFocus(event);
});

anchorLinks.forEach((link) => {
  link.addEventListener("click", (event) => {
    const targetId = link.getAttribute("href");
    if (!targetId || targetId === "#") return;

    if (!document.querySelector(targetId)) return;

    event.preventDefault();
    scrollToSection(targetId);
    window.history.replaceState(null, "", targetId);
  });
});

contactForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!contactForm.checkValidity()) {
    formStatus?.classList.add("is-error");
    formStatus?.classList.remove("is-success");
    if (formStatus) formStatus.textContent = "Compili i campi obbligatori prima dell'invio.";
    contactForm.reportValidity();
    return;
  }

  const endpoint = contactForm.getAttribute("action") || "";
  const submitButton = contactForm.querySelector("button[type='submit']");

  if (!endpoint) {
    formStatus?.classList.add("is-error");
    formStatus?.classList.remove("is-success");
    if (formStatus) formStatus.textContent = "Endpoint del modulo non ancora configurato.";
    return;
  }

  submitButton.disabled = true;
  formStatus?.classList.remove("is-error", "is-success");
  if (formStatus) formStatus.textContent = "Invio in corso...";

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      body: new FormData(contactForm),
      headers: {
        "Accept": "application/json"
      }
    });

    if (!response.ok) {
      throw new Error("Invio non riuscito");
    }

    contactForm.reset();
    formStatus?.classList.add("is-success");
    if (formStatus) {
      formStatus.textContent = "Grazie, la richiesta \u00e8 stata inviata. Lo Studio la ricontatter\u00e0 al pi\u00f9 presto.";
    }
  } catch (error) {
    formStatus?.classList.add("is-error");
    if (formStatus) formStatus.textContent = "Invio non riuscito. Riprovare o contattare lo Studio via email.";
  } finally {
    submitButton.disabled = false;
  }
});

window.addEventListener("load", () => {
  if (window.location.hash && document.querySelector(window.location.hash)) {
    window.requestAnimationFrame(() => scrollToSection(window.location.hash, "auto"));
  }
});
