"""Prepara il sito pubblicabile in locale senza modificare anteprima o sito online."""
from copy import deepcopy
from pathlib import Path
from shutil import copy2, copytree
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
import argparse
import os
import sqlite3
import sys

from lxml import etree, html
from componi_sito_completo import DEST, SOURCE, PAGES, load, static_news
from sincronizza_news_anteprima import FEED_NAME, read_feed, synchronize
from verifica_feed_instagram_studio import ProbeError, account_client


OUTPUT = Path(__file__).resolve().parent / "rilascio_studiolava" / "site"


def write_page(page, target):
    target.write_text(html.tostring(page, encoding="unicode", doctype="<!doctype html>"), encoding="utf-8")


def refresh_pages(site):
    feed = read_feed(site / FEED_NAME)
    with TemporaryDirectory(prefix=".pagine-news-", dir=site) as temp:
        staging = Path(temp)
        for name in ("index.html", "news.html"):
            doc = load(site / name)
            static_news(doc, name == "news.html", feed)
            write_page(doc, staging / name)
        for name in ("index.html", "news.html"):
            (staging / name).replace(site / name)


def prepare():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    copytree(DEST / "assets", OUTPUT / "assets", dirs_exist_ok=True)
    for name in ("stile.css", "pagine.css", "menu.js", "news-feed.js", "lettore.js", "sitemap.xml"):
        copy2(DEST / name, OUTPUT / name)
    for name in ("CNAME", "robots.txt", "favicon.ico", "favicon-studio-lava.ico"):
        copy2(SOURCE / name, OUTPUT / name)
    original = load(SOURCE / "index.html").xpath("//form[@data-contact-form]")[0]
    endpoint = original.get("action")
    if endpoint != "https://api.web3forms.com/submit":
        raise ValueError("Verificare il recapito del modulo.")
    for name in PAGES:
        page = load(DEST / name)
        for element in page.xpath('//head/meta[@name="robots" or @http-equiv="Content-Security-Policy"]'):
            element.drop_tree()
        policy = "object-src 'none'; base-uri 'none'; form-action 'none'; connect-src 'none'"
        if name == "index.html":
            form = page.xpath("//form[@data-contact-form]")[0]
            form.set("action", endpoint)
            form.set("method", original.get("method"))
            form.insert(0, deepcopy(original.xpath('input[@name="access_key"]')[0]))
            policy = "object-src 'none'; base-uri 'none'; form-action https://api.web3forms.com; connect-src https://api.web3forms.com"
        etree.SubElement(page.find("head"), "meta", attrib={"http-equiv": "Content-Security-Policy", "content": policy})
        write_page(page, OUTPUT / name)
    copy2(Path(__file__).with_name("contatti_rilascio_studiolava.js"), OUTPUT / "contatti.js")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--sincronizza", choices=("graph.facebook.com", "graph.instagram.com"))
    cli.add_argument("--sito", type=Path, default=OUTPUT, help="Cartella del sito da sincronizzare.")
    args = cli.parse_args()
    if args.sincronizza is None:
        if args.sito != OUTPUT:
            cli.error("--sito va usato con --sincronizza.")
        prepare()
    else:
        site = args.sito.resolve()
        if not all((site / name).is_file() for name in ("index.html", "news.html", FEED_NAME)):
            cli.error("La cartella deve contenere la home, l’archivio e il feed dello Studio.")
        if not all(os.environ.get(name) for name in ("STUDIO_IG_ACCOUNT_ID", "STUDIO_IG_TOKEN")):
            cli.error("Configurare l’identificativo Instagram e il token di lettura nelle variabili d’ambiente.")
        try:
            account, query = account_client(args.sincronizza)
            added, skipped, _ = synchronize(query, account, output=site,
                                            lockfile=site.parent / "sincronizzazione.sqlite3")
            refresh_pages(site)
            print(f"Nuovi caroselli: {added}. Caroselli con video esclusi: {skipped}.")
        except HTTPError as exc:
            sys.exit(f"Meta ha respinto la richiesta (HTTP {exc.code}).")
        except ProbeError as exc:
            sys.exit(str(exc))
        except (URLError, OSError, KeyError, ValueError, TypeError, sqlite3.Error):
            sys.exit("Sincronizzazione interrotta. La versione pubblica non è stata modificata.")
