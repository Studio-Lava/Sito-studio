const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const header = document.querySelector(".site-header");
const revealItems = document.querySelectorAll("[data-reveal], .person-card, .services-grid li");
const anchorLinks = document.querySelectorAll('a[href^="#"]');

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

window.addEventListener("load", () => {
  if (window.location.hash && document.querySelector(window.location.hash)) {
    window.requestAnimationFrame(() => scrollToSection(window.location.hash, "auto"));
  }
});
