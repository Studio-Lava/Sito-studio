"""Compone la copia privata integrale dalle pagine pubblicate e dalla proposta grafica."""
from copy import deepcopy
from pathlib import Path
from shutil import copy2, copytree
from urllib.parse import urlsplit
import json
import re

from lxml import etree, html
from anteprima_news_20261123 import OUT as PREVIEW, SITE
from sincronizza_news_anteprima import read_feed


SOURCE = Path(__file__).resolve().parent / "studio-seo-home-20261119"
DEST = PREVIEW.parent / "Sito_Studio_Lava_revisione_completa"
PAGES = ("index.html", "servizi.html", "elaborazione-paghe-torino.html",
         "costo-del-lavoro.html", "cambiare-consulente-del-lavoro.html", "news.html", "privacy.html")
CONTENTS = {
    "servizi.html": [("aree", "Le aree di consulenza"), ("elaborazione-paghe-torino.html", "Elaborazione paghe"), ("costo-del-lavoro.html", "Costo di un dipendente"), ("cambiare-consulente-del-lavoro.html", "Cambiare consulente")],
    "elaborazione-paghe-torino.html": [("attivita-paghe", "Paghe e adempimenti"), ("primo-incontro", "Il primo confronto"), ("domande", "Domande frequenti")],
    "costo-del-lavoro.html": [("esempio", "Il confronto nel commercio"), ("apprendistato", "Apprendistato"), ("agevolazioni", "Assunzioni agevolate"), ("benefit-welfare", "Benefit e welfare")],
    "cambiare-consulente-del-lavoro.html": [("primo-confronto", "Cosa preparare"), ("journey-title", "Le fasi del passaggio")],
}


def load(path):
    return html.document_fromstring(path.read_text(encoding="utf-8"))


def fragment(s):
    return html.fragment_fromstring(s)


def attach_script(head, name):
    el = etree.SubElement(head, "script", src=name, defer="defer")
    el.text = ""


def interior(doc, name):
    main = doc.xpath("//main")[0]
    main.set("class", "interior " + main.get("class", ""))
    if name == "privacy.html":
        return
    for crumb in main.xpath(".//nav"):
        crumb.drop_tree()
    first = main.find("section")
    title = first.find(".//h1")
    intro = first.find('.//p[@class="page-intro"]')
    actions = first.find('.//div[@class="hero-actions"]')
    if actions is None:
        actions = fragment('<div class="hero-actions"><a class="primary" href="index.html#richiesta">Parliamo del passaggio</a></div>')
    if name == "servizi.html":
        actions = fragment('<div class="hero-actions"><a class="primary" href="#aree">Esplora le attività</a></div>')
        main.find('.//section[@class="section service-details-section"]').set("id","aree")
        topics = main.xpath('.//article[@class="service-detail"]')
        topics[0].find("div").append(fragment('<a class="text-link" href="elaborazione-paghe-torino.html">Elaborazione paghe a Torino</a>'))
        topics[2].find("div").append(fragment('<a class="text-link" href="costo-del-lavoro.html#esempio">Confronta i costi di assunzione</a>'))
    if name == "elaborazione-paghe-torino.html":
        main.find('.//section[@class="section payroll-start"]').set("id","primo-incontro")
        main.find('.//section[@class="section payroll-questions"]').set("id","domande")
    new_hero = fragment('<section class="inner-hero"><div class="wrap inner-hero-grid"><div class="inner-lead"></div><aside class="page-guide" aria-label="Collegamenti utili"><p class="eyebrow">In questa pagina</p><ul></ul></aside></div></section>')
    lead = new_hero.find('.//div[@class="inner-lead"]')
    section_link = '<a href="servizi.html">Servizi</a>' if name != "servizi.html" else "Servizi"
    lead.append(fragment(f'<div class="trail"><a href="index.html">Studio Lava</a><span aria-hidden="true"> / </span>{section_link}</div>'))
    lead.append(title)
    lead.append(intro)
    lead.append(actions)
    if name == "servizi.html":
        new_hero.find('.//p[@class="eyebrow"]').text = "Vai direttamente a"
    for dest, label in CONTENTS[name]:
        href = dest if dest.endswith(".html") else "#" + dest
        li = etree.SubElement(new_hero.find(".//ul"), "li")
        etree.SubElement(li, "a", href=href).text = label
    main.replace(first,new_hero)
    for node in main.xpath('.//*[@data-reveal]'):
        del node.attrib["data-reveal"]


def current_home(doc, public):
    for label in doc.xpath('//div[@class="hero-text"]/p[normalize-space()="Studio di Giovanni Lava"]'):
        label.drop_tree()
    profiles = doc.get_element_by_id("professionisti")
    source_profiles = public.get_element_by_id("professionisti").xpath(".//article")
    if not source_profiles:
        raise ValueError("Nessun profilo trovato nella home originale.")
    cards = []
    for profile in source_profiles:
        card = deepcopy(profile)
        role = card.find('p[@class="role"]')
        role.set("class", "team-role")
        card.find("h3").addnext(role)
        cards.append(card)
    profiles[:] = cards
    section = doc.get_element_by_id("contatti")
    section.find(".//address/a[@class='text-link']").drop_tree()
    section.find(".//address").append(fragment('<a class="text-link" href="#richiesta">Scrivi allo Studio</a>'))
    hero_contact = doc.xpath('//div[@class="hero-actions"]/a[@class="primary"]')[0]
    hero_contact.set("href","#richiesta")
    form_section = fragment('<section id="richiesta" class="enquiry section"><div class="wrap split"><div><p class="eyebrow">Contatti</p><h2>Scrivi allo Studio</h2><p class="enquiry-intro">Descrivici la tua esigenza. Ti ricontatteremo per parlarne.</p></div></div></section>')
    form = deepcopy(public.xpath("//form[@data-contact-form]")[0])
    for field in form.xpath('.//input[@name="access_key"]'):
        field.drop_tree()
    form.attrib.pop("action",None)
    form.attrib.pop("novalidate",None)
    form_section.find("div").append(form)
    section.addnext(form_section)
    doc.xpath('//section[contains(@class,"hero")][1]')[0].set("id","home")


def local_links(doc, name):
    for a in doc.xpath("//a[@href]"):
        u = urlsplit(a.get("href"))
        if u.netloc == "www.studiolava.it":
            href = u.path.strip("/") or "index.html"
            if u.fragment:
                href = ("" if href == name else href) + "#" + u.fragment
            a.set("href",href)
        if a.get("href") == "index.html?contatto=1#contatti":
            a.set("href","index.html#richiesta")


def static_news(doc, archive, feed):
    lead_class, list_class = ("feature", "other-grid") if archive else ("home-lead", "briefs")
    lead = doc.find(f'.//article[@class="{lead_class}"]')
    listing = doc.find(f'.//div[@class="{list_class}"]')
    template = deepcopy(listing[0])
    for el in list(listing):
        listing.remove(el)
    for i, item in enumerate(feed if archive else feed[:3]):
        card = lead if i == 0 else deepcopy(template)
        if i:
            listing.append(card)
        card.find('.//div[@class="meta"]/span').text = item["category"]
        date = card.find(".//time")
        date.text = item["display"]
        date.set("datetime", item["date"])
        heading = card.xpath('.//h2|.//h3')[0]
        if archive:
            card.set("id", item["key"])
            heading.text = item["title"]
        else:
            heading[0].set("href", "news.html#" + item["key"])
            heading[0].text = item["title"]
        cover = card.find('.//a[@class="cover-frame"]')
        if cover is not None:
            slide = item["slides"][0]
            cover.set("href", item["post"])
            cover.set("aria-label", "Apri su Instagram il carosello " + item["title"])
            cover[0].set("src", slide["src"])
            cover[0].set("alt", "Copertina del carosello «" + slide["title"] + "»")
            heading.getnext().text = item["summary"]
            card.find('.//a[@class="link-action"]').set("href", item["post"])
            card.find('.//button[@data-read]').set("data-read", item["key"])
    entries = {item["key"]: item for item in feed}
    doc.get_element_by_id("dati-caroselli").text = json.dumps(entries, ensure_ascii=False).replace("<", r"\u003c")


def make_page(name, common, feed):
    news_page = name == "news.html"
    preview_page = news_page or name == "index.html"
    public = None if news_page else load(SOURCE/name)
    doc = load(PREVIEW/name) if preview_page else public
    head = doc.find("head")
    if name == "index.html":
        current_home(doc,public)
    if not preview_page:
        doc.find("body").set("class", "inner-page")
        old_main = doc.xpath("//main")[0]
        for child in list(doc.find("body")):
            if child is not old_main:
                child.drop_tree()
        header, skip, footer = (deepcopy(common.xpath(expr)[0]) for expr in ("//header", "//a[@class='skip']", "//footer"))
        old_main.addprevious(skip)
        old_main.addprevious(header)
        old_main.addnext(footer)
        interior(doc,name)
    if name == "index.html":
        doc.replace(head,deepcopy(public.find("head")))
        head = doc.find("head")
    for item in head.xpath('link[@rel="stylesheet" or @rel="icon"]|script[@src]|meta[@name="robots"]'):
        item.drop_tree()
    etree.SubElement(head,"meta",name="robots",content="noindex,nofollow")
    # La copia di revisione non trasmette dati, nemmeno con JavaScript disattivato.
    etree.SubElement(head,"meta",attrib={"http-equiv":"Content-Security-Policy","content":"form-action 'none'; connect-src 'none'; object-src 'none'; base-uri 'none'"})
    if news_page:
        etree.SubElement(head,"link",rel="canonical",href=SITE+name)
    if name == "privacy.html" and not head.xpath('meta[@name="description"]'):
        etree.SubElement(head,"meta",name="description",content="Come Studio Lava tratta i dati inviati tramite il modulo contatti.")
    etree.SubElement(head,"link",rel="icon",href="assets/favicon-studio-lava.svg")
    for sheet in ("stile.css","pagine.css"):
        etree.SubElement(head,"link",rel="stylesheet",href=sheet)
    attach_script(head,"menu.js")
    if preview_page:
        static_news(doc,news_page,feed)
        head.append(fragment('<noscript><style>.viewer-launch{display:none}</style></noscript>'))
        attach_script(head,"news-feed.js")
        attach_script(head,"lettore.js")
    if name == "index.html":
        attach_script(head,"contatti.js")
    local_links(doc,name)
    if name in (*CONTENTS,"privacy.html"):
        for a in doc.xpath('//nav[@id="nav"]//a|//footer//a'):
            a.attrib.pop("aria-current",None)
            if a.get("href") == name:
                a.set("aria-current","page")
    (DEST/name).write_text(html.tostring(doc,encoding="unicode",doctype="<!doctype html>"),encoding="utf-8")


if __name__ == "__main__":
    DEST.mkdir(parents=True,exist_ok=True)
    copytree(PREVIEW/"assets",DEST/"assets",dirs_exist_ok=True)
    copy2(PREVIEW/"news-feed.js",DEST/"news-feed.js")
    for asset in ("favicon-studio-lava.svg","giovanni-lava-professionale.png","logo-definitivo-vettoriale-trasparente.svg"):
        copy2(SOURCE/"assets"/asset,DEST/"assets"/asset)
    css = (PREVIEW/"stile.css").read_text(encoding="utf-8")
    (DEST/"stile.css").write_text(re.sub(r"(?m)^(\s*)nav(?=[. {])",r"\1#nav",css),encoding="utf-8")
    js = (PREVIEW/"interazioni.js").read_text(encoding="utf-8")
    menu, sep, reader = js.partition("function validArticle(")
    if not sep:
        raise ValueError("Codice del lettore non riconosciuto.")
    (DEST/"menu.js").write_text(menu,encoding="utf-8")
    (DEST/"lettore.js").write_text(sep+reader,encoding="utf-8")
    common = load(PREVIEW/"news.html")
    feed = read_feed(PREVIEW/"news-feed.js")
    for page in PAGES:
        make_page(page,common,feed)
    sitemap = etree.parse(str(SOURCE/"sitemap.xml"), etree.XMLParser(remove_blank_text=True))
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    news_url = etree.SubElement(sitemap.getroot(),namespace+"url")
    etree.SubElement(news_url,namespace+"loc").text = SITE+"news.html"
    sitemap.write(str(DEST/"sitemap.xml"),encoding="UTF-8",xml_declaration=True,pretty_print=True)
    (DEST/"robots.txt").write_text("User-agent: *\nDisallow: /\n",encoding="utf-8")
