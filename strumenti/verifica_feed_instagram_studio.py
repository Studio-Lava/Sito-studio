"""Collaudo privato. Solo lettura da Meta, nessun aggiornamento del sito.

Usa STUDIO_IG_ACCOUNT_ID e STUDIO_IG_TOKEN. Per Instagram Login imposta
--host graph.instagram.com. Senza --stato non viene scritto alcun file.
Con --stato .codex_work/nome.sqlite3 il primo passaggio fissa il riferimento
e quelli successivi segnalano i caroselli comparsi dopo quella lettura.
"""
import argparse
import getpass
import json
import os
import sqlite3
import sys
from contextlib import closing
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


USERNAME = "studio_lava_cdl"
SAMPLE = "Df1l7LPDa7R"
APP_ID = 0x534C4947
WORK = Path(__file__).resolve().parent
ASSETS = WORK.parent / "05_OUTPUT/SEO_STUDIO_LAVA/2026/2026-11/anteprima_sito_news/assets"


class ProbeError(Exception):
    """Messaggio del collaudo che può essere mostrato senza esporre credenziali."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


opener = build_opener(NoRedirect())


def get_collection(query, obj, edge, fields):
    params = {"fields": fields, "limit": 50}
    seen_cursors = set()
    while True:
        page = query(f"{obj}/{edge}", params)
        if not isinstance(page.get("data"), list):
            raise ProbeError("Meta non ha restituito un elenco leggibile.")
        yield from page["data"]
        paging = page.get("paging", {})
        if not paging.get("next"):
            return
        cursor = paging.get("cursors", {}).get("after")
        if not cursor or cursor in seen_cursors:
            raise ProbeError("Paginazione incompleta. Il riferimento non viene aggiornato.")
        seen_cursors.add(cursor)
        params["after"] = cursor


def collect(query, account, with_caption=False):
    profile = query(account, {"fields": "id,username"})
    if profile.get("username", "").casefold() != USERNAME:
        raise ProbeError("L’account autorizzato non corrisponde al profilo dello Studio.")
    albums = {}
    fields = "id,media_type,permalink,timestamp" + (",caption" if with_caption else "")
    for post in get_collection(query, account, "media", fields):
        if post["media_type"] != "CAROUSEL_ALBUM":
            continue
        url = urlsplit(post["permalink"])
        if url.scheme != "https" or url.hostname not in {"www.instagram.com", "instagram.com"}:
            raise ProbeError("Il collegamento al carosello non è su Instagram.")
        if not str(post["id"]).isdecimal() or not post.get("timestamp"):
            raise ProbeError("Il carosello non ha ID o data leggibili.")
        albums[post["id"]] = post
    return albums


def image_request(url, full=False):
    host = urlsplit(url)
    domains = ("cdninstagram.com", "fbcdn.net", "fbsbx.com", "instagram.com")
    if host.scheme != "https" or not any(host.hostname == d or
            (host.hostname or "").endswith("." + d) for d in domains):
        raise ProbeError("Il file non è servito da un dominio Meta riconosciuto.")
    return Request(url, headers={} if full else {"Range": "bytes=0-63"})


def check_image(url):
    request = image_request(url)
    with opener.open(request, timeout=25) as response:
        if response.headers.get_content_maintype() != "image" or not response.read(64):
            raise ProbeError("Il file immagine del carosello non è leggibile.")


def album_images(query, post):
    images = list(get_collection(query, post["id"], "children", "id,media_type,media_url"))
    if len(images) < 2 or len({p["id"] for p in images}) != len(images):
        raise ProbeError("Elenco delle slide insufficiente o duplicato.")
    for image in images:
        if image["media_type"] != "IMAGE" or not image.get("media_url"):
            raise ProbeError("Il collaudo richiede un carosello con tutte le slide fotografiche.")
    return images


def check_album(query, post, check_asset):
    images = album_images(query, post)
    for image in images:
        check_asset(image["media_url"])
    return len(images)


def download_image(url):
    limit = 16 * 1024 * 1024
    with opener.open(image_request(url, full=True), timeout=25) as response:
        if response.headers.get_content_maintype() != "image":
            raise ProbeError("Confronto da confermare: formato della risposta inatteso.")
        content = response.read(limit + 1)
    if len(content) > limit:
        raise ProbeError("Confronto da confermare: immagine troppo grande per questa prova.")
    return BytesIO(content)


def ordered_visual_comparator():
    try:
        from PIL import Image, ImageChops, ImageOps, ImageStat
    except ImportError:
        raise ProbeError("Per --confronta-slide esegui il verificatore con il Python professionale dello Studio.") from None

    def signature(source):
        try:
            with Image.open(source) as image:
                if image.width * image.height > 24_000_000:
                    raise ProbeError("Confronto da confermare: risoluzione eccessiva per il test.")
                upright = ImageOps.exif_transpose(image)
                if abs(upright.width / upright.height - 0.8) > 0.025:
                    raise ProbeError("Confronto da confermare: le proporzioni differiscono dalle slide originali.")
                return upright.convert("RGB").resize((160, 200), Image.Resampling.LANCZOS)
        except (OSError, ValueError, Image.DecompressionBombError):
            raise ProbeError("Confronto da confermare: immagine illeggibile.") from None

    # I riferimenti in ordine di lettura comprendono la copertina come prima pagina.
    paths = [ASSETS / "retribuzioni.webp"] + sorted((ASSETS / "retribuzioni").glob("[0-9][0-9].webp"))
    if len(paths) != 7 or not all(p.is_file() for p in paths):
        raise ProbeError("Il campione richiede la copertina e le sei slide interne approvate.")
    references = [signature(path) for path in paths]

    def identify(source, expected, label):
        candidate = signature(source)
        scores = sorted((sum(ImageStat.Stat(ImageChops.difference(candidate, ref)).mean) / 3, index)
                        for index, ref in enumerate(references))
        (best, matched), (second, _) = scores[:2]
        # Errore medio assoluto RGB in livelli 0–255. Ricampionamento comune,
        # limite assoluto e margine fra candidate evitano conferme su pagine simili.
        if best > 12 or second - best < 3 or (best > 0 and second < 1.55 * best):
            raise ProbeError(f"{label}: corrispondenza visiva da confermare.")
        if matched != expected:
            raise ProbeError(f"{label}: corrisponde alla pagina {matched + 1} anziché alla pagina {expected + 1}.")

    def compare(sources, cover, load):
        if len(sources) != len(references):
            raise ProbeError("Il numero di slide ricevute differisce dall’originale approvato.")
        for position, source in enumerate(sources):
            with load(source) as child:
                identify(child, position, f"Slide {position + 1}")
        if cover:
            with load(cover) as photo:
                identify(photo, 0, "Copertina del contenitore Instagram")
        return bool(cover)

    return compare


def visual_comparator():
    compare_order = ordered_visual_comparator()

    def compare(query, post, download=download_image):
        images = album_images(query, post)
        cover = query(post["id"], {"fields": "media_url"}).get("media_url")
        return compare_order([image["media_url"] for image in images], cover, download)

    return compare


def verify(query, account, check_asset, db, compare=None):
    albums = collect(query, account)
    db.execute("BEGIN IMMEDIATE")
    db.execute("CREATE TABLE IF NOT EXISTS viste (account TEXT, media TEXT, PRIMARY KEY(account, media))")
    seen = {row[0] for row in db.execute("SELECT media FROM viste WHERE account=?", (account,))}
    if not seen or compare:
        sample = next((post for post in albums.values()
                       if urlsplit(post["permalink"]).path.rstrip("/").endswith("/p/" + SAMPLE)), None)
        if not sample:
            raise ProbeError("Il post di riferimento del 17 novembre non compare nel feed.")
    if compare:
        compared_cover = compare(query, sample)
        print("Campione: prima slide e sequenza completa confrontate con le immagini originali.")
        print("Copertina del contenitore verificata." if compared_cover else
              "Meta non ha restituito la copertina separata del contenitore.")
    if not seen:
        results = [(sample["permalink"], check_album(query, sample, check_asset))]
    else:
        results = [(post["permalink"], check_album(query, post, check_asset))
                   for post in albums.values() if post["id"] not in seen]
    db.executemany("INSERT OR IGNORE INTO viste VALUES (?, ?)", ((account, mid) for mid in albums))
    db.commit()
    return bool(seen), results


def account_client(host):
    if host not in {"graph.facebook.com", "graph.instagram.com"}:
        raise ProbeError("Host Meta non valido.")
    if not sys.stdin.isatty() and not (os.getenv("STUDIO_IG_ACCOUNT_ID") and os.getenv("STUDIO_IG_TOKEN")):
        raise ProbeError("L’esecuzione non interattiva richiede le credenziali nelle variabili di ambiente.")
    account = os.getenv("STUDIO_IG_ACCOUNT_ID") or input("ID account Instagram autorizzato: ").strip()
    if not account.isascii() or not account.isdecimal():
        raise ProbeError("L’ID dell’account deve essere numerico.")
    token = os.getenv("STUDIO_IG_TOKEN") or getpass.getpass("Token di lettura (inserimento nascosto): ")
    if not token or not token.isascii() or any(ord(c) <= 32 or ord(c) >= 127 for c in token):
        raise ProbeError("Token mancante o in formato non valido.")

    def query(path, params):
        request = Request(f"https://{host}/v27.0/{path}?{urlencode(params)}",
                          headers={"Authorization": "Bearer " + token})
        with opener.open(request, timeout=25) as response:
            return json.load(response)

    return account, query


def main():
    cli = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    cli.add_argument("--host", choices=["graph.facebook.com", "graph.instagram.com"], default="graph.facebook.com")
    cli.add_argument("--stato", type=Path, help="Database privato .sqlite3 dentro .codex_work per confrontare più passaggi.")
    cli.add_argument("--confronta-slide", action="store_true",
                     help="Confronta in memoria tutte le immagini del campione, in ordine, con le WebP approvate.")
    options = cli.parse_args()
    compare = visual_comparator() if options.confronta_slide else None
    state = None
    if options.stato:
        state = options.stato.resolve()
        if state.parent != WORK or state.suffix.lower() != ".sqlite3":
            cli.error("Scegli un file .sqlite3 direttamente dentro .codex_work.")
    account, query = account_client(options.host)
    existed = state is not None and state.exists()
    with closing(sqlite3.connect(state or ":memory:")) as db:
        if existed and db.execute("PRAGMA application_id").fetchone()[0] != APP_ID:
            raise ProbeError("Il file esistente non è un database di questo collaudo.")
        if not existed:
            db.execute(f"PRAGMA application_id={APP_ID}")
        repeat, results = verify(query, account, check_image, db, compare)
    print("Nuovi caroselli osservati:" if repeat else "Carosello di riferimento individuato nel feed:")
    for link, slides in results:
        print(f"  {link} — {slides} immagini accessibili")
    if not results:
        print("  Nessun nuovo ID.")


if __name__ == "__main__":
    try:
        main()
    except HTTPError as exc:
        sys.exit(f"Lettura rifiutata dal servizio (HTTP {exc.code}).")
    except (URLError, TimeoutError, OSError):
        sys.exit("Impossibile completare la lettura o aprire il file di stato.")
    except ProbeError as exc:
        sys.exit(str(exc))
    except (ValueError, KeyError, sqlite3.Error):
        sys.exit("Risposta o stato del collaudo non validi.")
