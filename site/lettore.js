function validArticle(article) {
  const permalink = /^https:\/\/(?:www\.)?instagram\.com\/(?:studio_lava_cdl\/)?p\/[A-Za-z0-9_-]+\/?$/;
  const imagePath = /^assets\/(?:[A-Za-z0-9_-]+\/)*[A-Za-z0-9_-]+\.(?:webp|png|jpe?g|avif)$/i;
  return article && typeof article.key === 'string' && /^[A-Za-z0-9_-]+$/.test(article.key)
    && ['title', 'summary', 'category', 'date', 'display', 'post'].every(field => typeof article[field] === 'string')
    && article.title.trim() && /^\d{4}-\d{2}-\d{2}$/.test(article.date) && permalink.test(article.post)
    && Array.isArray(article.slides) && article.slides.length >= 2
    && article.slides.every(slide => slide && typeof slide.title === 'string'
        && typeof slide.src === 'string' && imagePath.test(slide.src));
}

function fillNewsCard(template, article) {
  const card = template.cloneNode(true);
  card.querySelector('.meta span').textContent = article.category;
  const time = card.querySelector('time');
  time.dateTime = article.date;
  time.textContent = article.display;
  const headingLink = card.querySelector('h3 a');
  if (headingLink) {
    headingLink.href = 'news.html#' + article.key;
    headingLink.textContent = article.title;
  } else {
    card.id = article.key;
    card.querySelector('h2, h3').textContent = article.title;
  }
  const coverLink = card.querySelector('.cover-frame');
  if (coverLink) {
    const cover = article.slides[0];
    coverLink.href = article.post;
    coverLink.setAttribute('aria-label', 'Apri su Instagram il carosello ' + article.title);
    const image = coverLink.querySelector('img');
    image.src = cover.src;
    image.alt = 'Copertina del carosello «' + cover.title + '»';
    const summary = card.querySelector('p:not(.eyebrow)');
    summary.textContent = article.summary;
    summary.hidden = !article.summary;
    card.querySelector('.link-action').href = article.post;
    card.querySelector('[data-read]').dataset.read = article.key;
  }
  return card;
}

function renderNews(articles) {
  const archive = document.querySelector('.archive');
  const lead = document.querySelector(archive ? '.feature' : '.home-lead');
  const list = document.querySelector(archive ? '.other-grid' : '.briefs');
  const others = archive ? articles.slice(1) : articles.slice(1, 3);
  const cards = others.map(article => fillNewsCard(list.firstElementChild, article));
  lead.replaceWith(fillNewsCard(lead, articles[0]));
  list.replaceChildren(...cards);
  (archive ? list.closest('.previous') : list).hidden = !others.length;
}

const feed = globalThis.studioLavaNews;
let posts = new Map(Object.entries(JSON.parse(document.getElementById('dati-caroselli').textContent)));
if (Array.isArray(feed) && feed.length && feed.every(validArticle)) {
  const byKey = new Map(feed.map(article => [article.key, article]));
  if (byKey.size === feed.length) {
    renderNews(feed);
    posts = byKey;
  }
}
const dialog = document.getElementById('lettore');
const heading = dialog.querySelector('h2');
const picture = document.getElementById('slide-img');
const statusText = document.getElementById('slide-status');
const previous = dialog.querySelector('.prev');
const next = dialog.querySelector('.next');
const instagram = dialog.querySelector('.reader-ig');
let post;
let slideIndex = 0;
let trigger;

function showSlide(index) {
  if (index < 0 || index >= post.slides.length) return;
  slideIndex = index;
  const slide = post.slides[index];
  picture.src = slide.src;
  picture.alt = slide.title;
  statusText.textContent = (index + 1) + ' di ' + post.slides.length;
  previous.disabled = index === 0;
  next.disabled = index === post.slides.length - 1;
  if (next.disabled && document.activeElement === next) previous.focus();
  if (previous.disabled && document.activeElement === previous) next.focus();
}

for (const button of document.querySelectorAll('[data-read]')) {
  button.addEventListener('click', () => {
    trigger = button;
    post = posts.get(button.dataset.read);
    heading.textContent = post.title;
    instagram.href = post.post;
    showSlide(0);
    dialog.showModal();
  });
}
previous.addEventListener('click', () => showSlide(slideIndex - 1));
next.addEventListener('click', () => showSlide(slideIndex + 1));
dialog.querySelector('.close').addEventListener('click', () => dialog.close());
dialog.addEventListener('close', () => trigger?.focus());
dialog.addEventListener('keydown', event => {
  if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
    event.preventDefault();
    showSlide(slideIndex + (event.key === 'ArrowLeft' ? -1 : 1));
  }
});
let touchStart;
picture.addEventListener('touchstart', event => {
  if (event.touches.length === 1) touchStart = [event.touches[0].clientX, event.touches[0].clientY];
}, { passive: true });
picture.addEventListener('touchend', event => {
  if (!touchStart) return;
  const dx = event.changedTouches[0].clientX - touchStart[0];
  const dy = event.changedTouches[0].clientY - touchStart[1];
  touchStart = null;
  if (Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy) * 1.5) showSlide(slideIndex + (dx < 0 ? 1 : -1));
}, { passive: true });
picture.addEventListener('touchcancel', () => { touchStart = null; });
