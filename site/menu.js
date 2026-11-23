const menuButton = document.querySelector('.menu-toggle');
const nav = document.getElementById('nav');
const servicesMenu = nav.querySelector('.nav-services');

function toggleMenu(open) {
  menuButton.setAttribute('aria-expanded', String(open));
  menuButton.textContent = open ? 'Chiudi' : 'Menu';
  nav.classList.toggle('is-open', open);
  if (!open) servicesMenu.open = false;
}

menuButton.addEventListener('click', () => toggleMenu(!nav.classList.contains('is-open')));
nav.addEventListener('click', event => {
  if (event.target.closest('a')) toggleMenu(false);
});
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape') return;
  if (servicesMenu.open) {
    servicesMenu.open = false;
    servicesMenu.querySelector('summary').focus();
  } else if (nav.classList.contains('is-open')) {
    toggleMenu(false);
    menuButton.focus();
  }
});
document.addEventListener('click', event => {
  if (!servicesMenu.contains(event.target)) servicesMenu.open = false;
});
servicesMenu.addEventListener('focusout', event => {
  if (!servicesMenu.contains(event.relatedTarget)) servicesMenu.open = false;
});
matchMedia('(min-width: 591px)').addEventListener('change', () => toggleMenu(false));

