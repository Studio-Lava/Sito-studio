"""Aggiorna solo l'anteprima locale con i caroselli fotografici pubblicati dallo Studio.

Il primo passaggio parte dalla data più antica già presente nell'anteprima.
I passaggi successivi conservano l'archivio e riconoscono i nuovi post da Meta.
Per la lettura reale servono STUDIO_IG_ACCOUNT_ID e STUDIO_IG_TOKEN,
oppure l'inserimento interattivo previsto dal verificatore.
"""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

from PIL import Image, ImageOps

from anteprima_news_20261123 import FEED_NAME, FEED_PREFIX, OUT, feed_text, initial_feed
from verifica_feed_instagram_studio import (
    WORK, ProbeError, account_client, collect, download_image, get_collection,
)


ROME = ZoneInfo("Europe/Rome")
MONTHS = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
          "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre")
POST_LINK = re.compile(r"https://(?:www\.)?instagram\.com/(?:studio_lava_cdl/)?p/([A-Za-z0-9_-]+)/?")
ASSET = re.compile(r"assets/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.(?:webp|png|jpe?g|avif)", re.I)


def shortcode(url):
    match = POST_LINK.fullmatch(url)
    if not match:
        raise ProbeError("Collegamento Instagram inatteso. L’archivio viene conservato.")
    return match[1]


def read_feed(path):
    if not path.exists():
        return initial_feed()
    content = path.read_text(encoding="utf-8").rstrip()
    if not content.startswith(FEED_PREFIX) or not content.endswith(";"):
        raise ProbeError("Il file delle news esistente ha un formato inatteso.")
    rows = json.loads(content[len(FEED_PREFIX):-1])
    if not isinstance(rows, list) or not rows:
        raise ProbeError("Il file delle news è vuoto o illeggibile.")
    return rows


def format_caption(caption, date_label):
    lines = [line.strip() for line in (caption or "").splitlines() if line.strip()]
    lines = [line for line in lines if not line.startswith(("#", "http://", "https://"))]
    if not lines:
        return "Aggiornamento del " + date_label, ""
    first = lines[0]
    if len(first) > 125:
        title = first[:124].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
        paragraphs = lines
    else:
        title, paragraphs = first, lines[1:]
    summary = " ".join(paragraphs)
    if len(summary) > 280:
        summary = summary[:279].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
    return title, summary


def save_image(source, stage):
    with Image.open(source) as image:
        if image.width * image.height > 24_000_000:
            raise ProbeError("Immagine troppo grande per il collaudo.")
        upright = ImageOps.exif_transpose(image).convert("RGB")
        upright.thumbnail((1200, 1500), Image.Resampling.LANCZOS)
        tmp = stage / "conversione.webp"
        upright.save(tmp, "WEBP", quality=87, method=4)
    name = hashlib.sha256(tmp.read_bytes()).hexdigest() + ".webp"
    os.replace(tmp, stage / name)
    return "assets/instagram/" + name


def children_for(query, media_id):
    children = list(get_collection(query, media_id, "children", "id,media_type,media_url"))
    if len(children) < 2 or len({str(row["id"]) for row in children}) != len(children):
        raise ProbeError("Il carosello contiene un elenco di slide incompleto o duplicato.")
    if any(row["media_type"] == "VIDEO" for row in children):
        return []
    if any(row["media_type"] != "IMAGE" or not row.get("media_url") for row in children):
        raise ProbeError("Meta non ha restituito tutte le immagini del carosello.")
    return children


def synchronize(query, account, output=OUT, download=download_image, lockfile=None, since=None):
    target = output / FEED_NAME
    lockfile = lockfile or WORK / "sincronizza_news_anteprima.sqlite3"
    with closing(sqlite3.connect(lockfile, timeout=10)) as lock:
        lock.execute("BEGIN IMMEDIATE")
        original = read_feed(target)
        by_code = {shortcode(row["post"]): dict(row) for row in original}
        if len(by_code) != len(original) or len({row["key"] for row in original}) != len(original):
            raise ProbeError("Il file delle news contiene riferimenti duplicati.")
        by_media_id = {}
        for code, row in by_code.items():
            if row.get("media_id"):
                mid = str(row["media_id"])
                if mid in by_media_id:
                    raise ProbeError("Uno stesso carosello compare due volte nel file delle news.")
                by_media_id[mid] = code
        if since is None:
            since = min(row["date"] for row in original)
        remote = collect(query, account, with_caption=True)
        added, skipped_video = 0, 0
        # I temporanei e il manifest sono sullo stesso volume per il cambio atomico.
        with TemporaryDirectory(prefix=".news-", dir=output) as tmp:
            stage = Path(tmp)
            for media_id, item in remote.items():
                published = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
                if published.tzinfo is None:
                    raise ProbeError("La data ricevuta da Meta è priva del fuso orario.")
                local = published.astimezone(ROME)
                date = local.date().isoformat()
                if date < since:
                    continue
                code = shortcode(item["permalink"])
                if str(media_id) in by_media_id and by_media_id[str(media_id)] != code:
                    raise ProbeError("Il collegamento non corrisponde più all’identificativo del carosello.")
                by_media_id[str(media_id)] = code
                current = by_code.get(code)
                if current and str(current.get("media_id", media_id)) != str(media_id):
                    raise ProbeError("Meta associa due identificativi diversi allo stesso post.")
                display = f"{local.day} {MONTHS[local.month - 1]} {local.year}"
                title, summary = format_caption(item.get("caption"), display)
                instant = published.astimezone(timezone.utc).isoformat()
                if current is not None:
                    current.update(media_id=str(media_id), timestamp=instant)
                    if current.get("from_instagram"):
                        current.update(title=title, summary=summary, date=date, display=display)
                    if all(ASSET.fullmatch(slide["src"]) and (output / slide["src"]).is_file()
                           for slide in current["slides"]):
                        continue
                children = children_for(query, media_id)
                if not children:
                    skipped_video += 1
                    continue
                slides = []
                for i, child in enumerate(children, 1):
                    with download(child["media_url"]) as image:
                        src = save_image(image, stage)
                    slides.append({"title": f"{title}, pagina {i}", "src": src})
                if current:
                    current["slides"] = slides
                else:
                    by_code[code] = dict(key="ig-" + str(media_id), post=item["permalink"],
                                         media_id=str(media_id), from_instagram=True, timestamp=instant,
                                         category="News sul lavoro", date=date, display=display,
                                         title=title, summary=summary, slides=slides)
                    added += 1
            rows = sorted(by_code.values(), key=lambda r: (r["date"], r.get("timestamp", ""), r["key"]), reverse=True)
            if len({row["key"] for row in rows}) != len(rows):
                raise ProbeError("La sincronizzazione produrrebbe due news con lo stesso identificativo.")
            content = feed_text(rows)
            changed = not target.exists() or content != target.read_text(encoding="utf-8")
            if changed or any(stage.glob("*.webp")):
                for path in stage.glob("*.webp"):
                    dest = output / "assets" / "instagram" / path.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if not dest.exists():
                        os.replace(path, dest)
                if changed:
                    pending = stage / FEED_NAME
                    pending.write_text(content, encoding="utf-8")
                    os.replace(pending, target)
        return added, skipped_video, changed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", choices=("graph.instagram.com", "graph.facebook.com"), default="graph.instagram.com")
    try:
        account, query = account_client(parser.parse_args().host)
        added, video, changed = synchronize(query, account)
        print(f"Nuovi caroselli fotografici: {added}. Caroselli con video esclusi: {video}.")
        print("Anteprima aggiornata." if changed else "Anteprima già aggiornata.")
    except HTTPError as exc:
        sys.exit(f"Meta ha respinto la richiesta (HTTP {exc.code}).")
    except ProbeError as exc:
        sys.exit(str(exc))
    except (URLError, OSError, KeyError, ValueError, TypeError, Image.DecompressionBombError, sqlite3.Error):
        sys.exit("Lettura o sincronizzazione incompleta. Il feed precedente resta disponibile.")
