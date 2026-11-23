"""Compone le due pagine statiche dell'anteprima locale con i materiali dello Studio."""
import json
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "05_OUTPUT/SEO_STUDIO_LAVA/2026/2026-11/anteprima_sito_news"
SITE = "https://www.studiolava.it/"
PROFILE = "https://www.instagram.com/studio_lava_cdl/"
FEED_NAME = "news-feed.js"
FEED_PREFIX = "globalThis.studioLavaNews = "
SERVICES = [
    ("Elaborazione paghe a Torino", "Dalla prima assunzione alla gestione mensile di cedolini e contributi.", "elaborazione-paghe-torino.html"),
    ("Costo di un dipendente", "Contratti, orari e agevolazioni a confronto, con un esempio nel commercio.", "costo-del-lavoro.html"),
    ("Cambiare consulente del lavoro", "Documenti, prossime scadenze e responsabilità nel passaggio al nuovo Studio.", "cambiare-consulente-del-lavoro.html"),
]

NEWS = [
    dict(key="retribuzioni", cover="retribuzioni.webp", folder="retribuzioni",
         category="Retribuzioni", date="2026-11-17", display="17 novembre 2026",
         title="Stipendio in contanti e diffida amministrativa",
         summary="Il Ministero del Lavoro chiarisce se la diffida si applica al pagamento diretto in contanti. Il carosello spiega anche perché la firma sul cedolino, da sola, non prova il versamento.",
         post="Df1l7LPDa7R", slides=[
             "Stipendio in contanti? La diffida non si applica", "Pagamenti tracciabili dal 2018",
             "La firma sul cedolino non prova il pagamento", "La diffida non sana il contante",
             "Sanzione da 1.000 a 5.000 euro", "Somme fuori busta: il LUL non basta",
             "Prima di pagare, scegli il mezzo"]),
    dict(key="infortuni", cover="infortuni.webp", folder="infortuni", category="Infortuni sul lavoro",
         date="2026-11-10", display="10 novembre 2026",
         title="Infortunio nel tragitto casa-lavoro. Chi avvisa l’INAIL?",
         summary="I dati INAIL sugli infortuni in itinere e le prime comunicazioni che coinvolgono lavoratore e azienda dopo un incidente.",
         post="Dfjtx8njJrU", slides=["Incidente andando al lavoro?", "Quando è «in itinere»",
             "Denunce in aumento del 6,1%", "Il lavoratore avvisa l’azienda",
             "L’azienda comunica a INAIL", "Il riconoscimento spetta a INAIL"]),
    dict(key="formazione", cover="altro.webp", folder="formazione", category="Salute e sicurezza",
         date="2026-11-03", display="3 novembre 2026",
         title="Quando comincia la formazione sulla sicurezza dei neoassunti?",
         summary="Il chiarimento dell’Ispettorato distingue l’avvio della formazione dal termine per completarla e affronta il caso del turismo e dei pubblici esercizi.",
         post="DfRotNmjz-3", slides=["Neoassunti e sicurezza", "I 60 giorni non rinviano l’avvio",
             "La formazione inizia all’assunzione", "Turismo e pubblici esercizi: 30 giorni",
             "Documenta l’avvio del percorso", "Informazione prima dell’impiego"]),
]


def ig_url(item):
    return PROFILE + "p/" + item["post"] + "/"


def initial_feed():
    rows = []
    for item in NEWS:
        row = {k: item[k] for k in ("key", "title", "summary", "category", "date", "display")}
        row.update(post=ig_url(item), slides=reader_slides(item))
        rows.append(row)
    return rows


def feed_text(rows):
    safe = json.dumps(rows, ensure_ascii=False, indent=2).replace("<", r"\u003c")
    return FEED_PREFIX + safe + ";\n"


def reader_slides(item):
    return [{"title": title, "src": "assets/" + (item["cover"] if n == 1 else f'{item["folder"]}/{n:02}.webp')}
            for n, title in enumerate(item["slides"], start=1)]


def brand():
    return ('<a class="brand" href="index.html" aria-label="Studio Lava, homepage">'
            '<img src="assets/logo.svg" alt="" width="62" height="31">'
            '<span><strong>Studio Lava</strong><small>Consulente del Lavoro</small></span></a>')


def header(is_news):
    home = "index.html" if is_news else ""
    active = ' aria-current="page"' if is_news else ""
    service_links = "".join(f'<li><a href="{SITE}{url}">{label}</a></li>' for label, _, url in SERVICES)
    return f'''<a href="#contenuto" class="skip">Vai al contenuto</a>
<header class="mast"><div class="wrap bar">{brand()}
<button class="menu-toggle" aria-expanded="false" aria-controls="nav">Menu</button>
<nav id="nav" aria-label="Navigazione principale">
<a href="{home}#studio">Lo Studio</a><details class="nav-services"><summary>Servizi</summary>
<ul><li><a href="{SITE}servizi.html">Tutti i servizi</a></li>{service_links}</ul></details>
<a href="news.html"{active}>News</a><a class="nav-contact" href="{home}#contatti">Contatti</a></nav></div></header>'''


def footer():
    return f'''<footer><div class="wrap foot">{brand()}<p>Studio Lava di Giovanni Lava<br>
Corso Francia 335, 10142 Torino · P. IVA 11011470017<br>Albo dei Consulenti del Lavoro di Torino n. 1752</p>
<div class="foot-links"><a href="{PROFILE}">Instagram</a><a href="{SITE}privacy.html">Informativa privacy</a></div></div></footer>'''


def html(title, description, content, is_news=False):
    return f'''<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow"><meta name="description" content="{escape(description)}">
<title>{title} | Studio Lava</title><link rel="icon" href="assets/logo.svg"><link rel="stylesheet" href="stile.css">
<script src="{FEED_NAME}" defer></script><script src="interazioni.js" defer></script></head><body>{header(is_news)}
<main id="contenuto">{content}</main>{footer()}{viewer()}</body></html>'''


def meta(item):
    return (f'<div class="meta"><span>{item["category"]}</span>'
            f'<time datetime="{item["date"]}">{item["display"]}</time></div>')


def cover(item, eager=False):
    loading = "eager" if eager else "lazy"
    return f'''<a class="cover-frame" href="{ig_url(item)}" aria-label="Apri su Instagram il carosello {escape(item['slides'][0])}">
<img src="assets/{item['cover']}" width="720" height="900" loading="{loading}" alt="Copertina del carosello «{escape(item['slides'][0])}»"></a>'''


def actions(item):
    return f'''<div class="post-actions"><a class="link-action" href="{ig_url(item)}">Apri su Instagram</a>
<button type="button" class="viewer-launch" data-read="{item['key']}" aria-haspopup="dialog">Sfoglia qui</button></div>'''


def viewer():
    data = {}
    for item in NEWS:
        slides = reader_slides(item)
        data[item["key"]] = {"title": item["title"], "post": ig_url(item), "slides": slides}
    payload = json.dumps(data, ensure_ascii=False).replace("<", r"\u003c")
    return f'''<script type="application/json" id="dati-caroselli">{payload}</script>
<dialog id="lettore" aria-labelledby="lettore-titolo"><div class="dialog-top">
<h2 id="lettore-titolo"></h2><button type="button" class="close" aria-label="Chiudi il carosello" autofocus>Chiudi</button></div>
<div class="slide-stage"><img id="slide-img" alt=""></div>
<div class="slide-controls"><button class="prev" type="button">Precedente</button><span id="slide-status" aria-live="polite"></span><button class="next" type="button">Successiva</button></div>
<a class="reader-ig" href="{PROFILE}">Apri su Instagram</a></dialog>'''


def home():
    featured, *others = NEWS
    related = "".join(f'''<article class="brief">{meta(item)}<h3><a href="news.html#{item["key"]}">{item["title"]}</a></h3></article>''' for item in others)
    rows = "".join(f'<a class="service" href="{SITE}{url}"><h3>{label}</h3><span>{desc}</span></a>' for label, desc, url in SERVICES)
    return f'''<section class="hero"><div class="wrap hero-grid">
<div class="hero-text"><p class="eyebrow rule">Studio di Giovanni Lava</p><h1>Consulenza del lavoro <em>a Torino.</em></h1>
<p class="intro">Dalla prima assunzione alla gestione delle paghe, affianchiamo la tua azienda nelle scelte che riguardano le persone e il costo del lavoro.</p>
<div class="hero-actions"><a class="primary" href="#contatti">Contatta lo Studio</a><a class="text-link" href="#servizi">Esplora i servizi</a></div></div>
<figure class="portrait"><img src="assets/giovanni.webp" width="842" height="1169" alt="Ritratto di Giovanni Lava" fetchpriority="high">
<figcaption><strong>Giovanni Lava</strong><span>Consulente del Lavoro</span></figcaption></figure></div></section>
<section class="news-home"><div class="wrap"><div class="section-head"><div><p class="eyebrow">Dal nostro Studio</p><h2>News sul lavoro</h2></div>
<a class="text-link" href="news.html">Tutte le news</a></div>
<div class="home-news-grid"><article class="home-lead">{cover(featured)}<div>{meta(featured)}
<h3><a href="news.html#{featured['key']}">{featured['title']}</a></h3><p>{featured['summary']}</p>{actions(featured)}</div></article>
<div class="briefs">{related}</div></div></div></section>
<section id="servizi" class="section services"><div class="wrap split"><div><p class="eyebrow">Servizi per le aziende</p><h2>Quando rivolgersi<br>allo Studio</h2>
<a class="text-link" href="{SITE}servizi.html">Tutti i servizi</a></div><div class="service-list">{rows}</div></div></section>
<section id="studio" class="section studio"><div class="wrap split"><div><p class="eyebrow">Lo Studio</p><h2>Chi segue la tua azienda</h2></div>
<div class="studio-copy"><p>A Torino, Giovanni Lava e i suoi collaboratori seguono le aziende nella gestione delle paghe, negli adempimenti mensili e nelle scelte che riguardano il personale.</p>
<a class="text-link" href="#professionisti">Conosci i professionisti</a></div></div>
<div id="professionisti" class="wrap team-profiles" role="region" aria-label="I professionisti dello Studio" tabindex="-1">
<article><h3>Giovanni Lava</h3><p class="team-role">Titolare dello Studio</p>
<p>Consulente del Lavoro iscritto all’Albo di Torino dal 2013. Si occupa di amministrazione del personale e insegna elaborazione paghe. È stato consigliere dell’Associazione Giovani Consulenti del Lavoro di Torino.</p></article>
<article><h3>Anna Canfora</h3><p class="team-role">Collaboratrice di Studio</p>
<p>Abilitata all’esercizio della professione di Consulente del Lavoro, si occupa di amministrazione del personale e degli adempimenti legati ai rapporti di lavoro.</p></article>
<article><h3>Andrea Sblendorio</h3><p class="team-role">Praticante Consulente del Lavoro</p>
<p>Affianca lo Studio nell’elaborazione dei cedolini, nella gestione delle pratiche e nella consulenza alle aziende clienti.</p></article>
</div></section>
<section id="contatti" class="contact"><div class="wrap split"><div><p class="eyebrow">Contatti</p><h2>Parliamo della<br>tua azienda.</h2><p>Corso Francia 335, Torino</p></div>
<address><a class="phone" href="tel:+390114051299">011 405 1299</a><a class="email" href="mailto:amministrazione@studiolava.it">amministrazione@studiolava.it</a>
<span>Dal lunedì al venerdì<br>9.00–13.00 e 14.00–18.00</span>
<a class="text-link" href="{SITE}#contatti">Contatti sul sito dello Studio</a></address></div></section>'''


def archive():
    featured, *others = NEWS
    return f'''<div class="archive wrap"><header class="archive-head"><p class="eyebrow rule">Studio Lava · Approfondimenti</p>
<h1>News sul <em>lavoro.</em></h1><p class="intro">Paghe, contratti e sicurezza. I chiarimenti dello Studio per chi gestisce il personale, da leggere e sfogliare.</p></header>
<article id="{featured['key']}" class="feature">{cover(featured, True)}<div class="feature-text"><p class="eyebrow feature-label">In evidenza</p>{meta(featured)}
<h2>{featured['title']}</h2><p>{featured['summary']}</p>{actions(featured)}</div></article>
<section class="previous"><h2>Le altre notizie</h2><div class="other-grid">''' + "".join(
        f'''<article id="{item['key']}" class="other">{cover(item)}<div>{meta(item)}<h3>{item['title']}</h3>
<p>{item['summary']}</p>{actions(item)}</div></article>''' for item in others) + '</div></section></div>'


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    if not (OUT / FEED_NAME).exists():
        (OUT / FEED_NAME).write_text(feed_text(initial_feed()), encoding="utf-8")
    (OUT / "index.html").write_text(html("Consulente del Lavoro a Torino per aziende", "Studio Lava affianca le aziende nella gestione del personale.", home()), encoding="utf-8")
    (OUT / "news.html").write_text(html("News sul lavoro", "I caroselli di Studio Lava su paghe, contratti e sicurezza.", archive(), True), encoding="utf-8")
