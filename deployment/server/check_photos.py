"""Check every night which products' photos are gone, so that the site leaves them out.

    python3 deployment/server/check_photos.py \
        [--catalogue /srv/picwise/shared/prepared/catalogue.json.gz] \
        [--db /srv/picwise/shared/photos/photos.sqlite3] \
        [--out /srv/picwise/shared/photos/gone.json] [--budget-minutes 60]

The owner, 2026-11-01, of products whose photo did not load on the live site: «Όταν το
προϊόν δεν φέρνει φωτογραφία δεν πρέπει να εμφανίζεται... Στις περισσότερες περιπτώσεις
είναι not found». A read of the live site's photos the same day found 19 of 244 gone (HTTP
404, with or without a Referer: links to nothing, not refused), 18 of them InStock UK's.

Run by picwise-photos.service, every night after the preparation and once by each
deployment (in the background). The photos are those of the prepared catalogue the site
reads. Each address is asked once (HEAD, as a browser's first look; GET of one byte where
HEAD is refused), over kept-open connections, at most `--budget-minutes` a night: never
asked first, then those that could not be read, then gone ones after a week, then the
others after two weeks. Only HTTP 404 and 410 call a photo gone; a photo that could not be
read (no answer, refused, a server error, too many asks) is asked again the next night,
never called gone. What each address answered is kept in a small database.

Written: the addresses of the catalogue's photos that are gone, one JSON file, replaced
whole (`picwise_providers.product_photos` reads it for the site). Printed: counts, and the
shops with the most gone photos; no address. Exits 0, or 1 when the catalogue cannot be
read (the last file kept).
"""
from __future__ import annotations

import argparse
import gc
import http.client
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
import urllib.parse
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

DEFAULT_CATALOGUE = Path("/srv/picwise/shared/prepared/catalogue.json.gz")
DEFAULT_DB = Path("/srv/picwise/shared/photos/photos.sqlite3")
DEFAULT_OUT = Path("/srv/picwise/shared/photos/gone.json")
WORKERS = 16
TIMEOUT_SECONDS = 15
MAX_REDIRECTS = 3
USER_AGENT = "Mozilla/5.0 (compatible; PicWise-PhotoCheck/1.0; +https://picwise.subby.cloud)"
DAY = 86400
# When an address is asked again.
AGAIN_GONE = 7 * DAY
AGAIN_OK = 14 * DAY
AGAIN_UNREAD = DAY // 2
FORGET_AFTER = 30 * DAY
# Answers that say the photo is not there: the link points to nothing.
GONE_STATUSES = frozenset({404, 410})
LISTED_SHOPS = 15

Fetch = Callable[[str], int]


def _connection(cache: dict[tuple[str, str], http.client.HTTPConnection], scheme: str, host: str):
    key = (scheme, host)
    connection = cache.get(key)
    if connection is None:
        factory = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
        connection = factory(host, timeout=TIMEOUT_SECONDS)
        cache[key] = connection
    return connection


class Asker:
    """Asks for photos over connections kept open, one set per thread."""

    def __init__(self) -> None:
        self._local = threading.local()

    def _cache(self) -> dict[tuple[str, str], http.client.HTTPConnection]:
        cache = getattr(self._local, "cache", None)
        if cache is None:
            cache = self._local.cache = {}
        return cache

    def _ask(self, method: str, url: str) -> tuple[int, str]:
        parts = urllib.parse.urlsplit(url)
        scheme = parts.scheme.lower()
        if scheme not in ("http", "https") or not parts.netloc:
            raise ValueError("not a web address")
        target = urllib.parse.urlunsplit(("", "", parts.path or "/", parts.query, ""))
        headers = {"User-Agent": USER_AGENT, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}
        if method == "GET":
            headers["Range"] = "bytes=0-0"
        cache = self._cache()
        for attempt in (1, 2):
            connection = _connection(cache, scheme, parts.netloc)
            try:
                connection.request(method, target, headers=headers)
                response = connection.getresponse()
                response.read()
                location = response.getheader("Location") or ""
                if response.getheader("Connection", "").lower() == "close":
                    connection.close()
                    cache.pop((scheme, parts.netloc), None)
                return response.status, location
            except (http.client.HTTPException, OSError):
                # A kept connection the server has closed since: once more on a new one.
                connection.close()
                cache.pop((scheme, parts.netloc), None)
                if attempt == 2:
                    raise
        raise OSError("not asked")

    def close(self) -> None:
        """Close the connections this thread kept open."""
        cache = self._cache()
        for connection in cache.values():
            connection.close()
        cache.clear()

    def __call__(self, url: str) -> int:
        """The HTTP status the photo's address answers, after its redirects; 0 when none."""
        try:
            for method in ("HEAD", "GET"):
                address = url
                for _hop in range(MAX_REDIRECTS + 1):
                    status, location = self._ask(method, address)
                    if status in (301, 302, 303, 307, 308) and location:
                        address = urllib.parse.urljoin(address, location)
                        continue
                    break
                # A server that refuses HEAD is asked for one byte instead.
                if method == "HEAD" and status in (403, 405, 501):
                    continue
                return status
            return status
        except (ValueError, http.client.HTTPException, OSError):
            return 0


def state_of(status: int) -> str:
    """"ok", "gone", or "unread" for an answer: only a link to nothing is gone."""
    if status in GONE_STATUSES:
        return "gone"
    if 200 <= status < 300:
        return "ok"
    return "unread"


def open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path))
    db.execute(
        "CREATE TABLE IF NOT EXISTS photo ("
        " url TEXT PRIMARY KEY, state TEXT NOT NULL, status INTEGER NOT NULL, asked INTEGER NOT NULL)"
    )
    return db


def known(db: sqlite3.Connection) -> dict[str, tuple[str, int]]:
    return {url: (state, asked) for url, state, asked in db.execute("SELECT url, state, asked FROM photo")}


def due(urls: Iterable[str], seen: dict[str, tuple[str, int]], now: int) -> list[str]:
    """The addresses to ask tonight, in order: never asked, could not be read, gone a
    week ago, read well two weeks ago; the longest unasked first in each."""
    order = []
    for url in urls:
        record = seen.get(url)
        if record is None:
            order.append((0, 0, url))
            continue
        state, asked = record
        if state == "unread" and now - asked >= AGAIN_UNREAD:
            order.append((1, asked, url))
        elif state == "gone" and now - asked >= AGAIN_GONE:
            order.append((2, asked, url))
        elif state == "ok" and now - asked >= AGAIN_OK:
            order.append((3, asked, url))
    order.sort()
    return [url for _rank, _asked, url in order]


def ask_all(urls: list[str], fetch: Fetch, *, workers: int, budget_seconds: float,
            clock: Callable[[], float] = time.monotonic) -> dict[str, int]:
    """Each address's answer, asked `workers` at a time, until the budget is spent."""
    answers: dict[str, int] = {}
    started = clock()
    pending = iter(urls)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        running = {}
        for url in pending:
            running[pool.submit(fetch, url)] = url
            if len(running) >= workers * 4:
                break
        while running:
            done, _ = wait(running, return_when=FIRST_COMPLETED)
            for future in done:
                url = running.pop(future)
                try:
                    answers[url] = future.result()
                except Exception:  # one address's surprise never stops the night's check
                    answers[url] = 0
            if clock() - started < budget_seconds:
                for url in pending:
                    running[pool.submit(fetch, url)] = url
                    if len(running) >= workers * 4:
                        break
    return answers


def catalogue_photos(path: Path) -> dict[str, tuple[str, int]]:
    """Each photo address of the prepared catalogue, with its first product's shop and
    how many products show it. The catalogue is let go before any photo is asked."""
    root = Path(__file__).resolve().parents[2]
    for folder in (root, root / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    from picwise_providers.normalization import extract_merchant_name
    from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure

    prepared = read_prepared_catalogue_to_measure(path)
    if prepared is None:
        raise ValueError("the prepared catalogue cannot be read")
    photos: dict[str, tuple[str, int]] = {}
    for product in prepared.products:
        url = " ".join(str(product.image_url or "").split())
        if not url:
            continue
        shop, count = photos.get(url, ("", 0))
        if not count:
            raw = product.raw if isinstance(product.raw, dict) else {}
            shop = str(extract_merchant_name(raw) or "").strip()
        photos[url] = (shop, count + 1)
    del prepared
    gc.collect()
    return photos


def write(document: dict, out: Path) -> None:
    """Replace the file whole, never half written."""
    out.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=out.parent, prefix=".gone.", delete=False)
    try:
        with handle:
            json.dump(document, handle, ensure_ascii=False)
        os.replace(handle.name, out)
    except BaseException:
        Path(handle.name).unlink(missing_ok=True)
        raise


def run(photos: dict[str, tuple[str, int]], db: sqlite3.Connection, out: Path, fetch: Fetch, *,
        workers: int = WORKERS, budget_seconds: float = 3600.0, now: datetime | None = None) -> list[str]:
    """Ask tonight's addresses, keep their answers, write the gone ones; the lines to print."""
    moment = now or datetime.now(timezone.utc)
    stamp = int(moment.timestamp())
    seen = known(db)
    tonight = due(photos, seen, stamp)
    answers = ask_all(tonight, fetch, workers=workers, budget_seconds=budget_seconds)
    states = Counter()
    rows = []
    for url, status in answers.items():
        state = state_of(status)
        states[state] += 1
        rows.append((url, state, status, stamp))
        seen[url] = (state, stamp)
    with db:
        db.executemany(
            "INSERT INTO photo (url, state, status, asked) VALUES (?, ?, ?, ?)"
            " ON CONFLICT(url) DO UPDATE SET state = excluded.state, status = excluded.status,"
            " asked = excluded.asked",
            rows,
        )
        # Addresses gone from the catalogue for a month are forgotten: the file stays small.
        db.execute("CREATE TEMP TABLE IF NOT EXISTS current (url TEXT PRIMARY KEY)")
        db.execute("DELETE FROM current")
        db.executemany("INSERT OR IGNORE INTO current (url) VALUES (?)", ((url,) for url in photos))
        db.execute(
            "DELETE FROM photo WHERE asked < ? AND url NOT IN (SELECT url FROM current)",
            (stamp - FORGET_AFTER,),
        )
    gone = sorted(url for url in photos if seen.get(url, ("", 0))[0] == "gone")
    never = sum(1 for url in photos if url not in seen)
    write({"checked_at": moment.isoformat(timespec="seconds"), "photos": len(photos), "gone": gone}, out)
    gone_products = sum(photos[url][1] for url in gone)
    products = sum(count for _shop, count in photos.values())
    lines = [
        f"photos: {len(photos):,} in the catalogue, of {products:,} products; asked tonight "
        f"{len(answers):,} of the {len(tonight):,} due (read {states['ok']:,}, gone {states['gone']:,}, "
        f"could not be read {states['unread']:,}); never asked yet {never:,}",
        f"photos gone: {len(gone):,}, of {gone_products:,} products, left out of the site",
    ]
    per_shop: Counter = Counter()
    for url in gone:
        per_shop[photos[url][0] or "-"] += photos[url][1]
    for shop, count in per_shop.most_common(LISTED_SHOPS):
        lines.append(f"  {count:>7,}  {shop[:50]}")
    return lines


def main(argv: list[str] | None = None, *, fetch: Fetch | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--catalogue", type=Path, default=DEFAULT_CATALOGUE)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--budget-minutes", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=WORKERS)
    args = parser.parse_args(argv)
    try:
        photos = catalogue_photos(args.catalogue)
    except (OSError, ValueError) as error:
        print(f"photos: not checked ({error}); the last file kept")
        return 1
    db = open_db(args.db)
    try:
        lines = run(photos, db, args.out, fetch or Asker(), workers=args.workers,
                    budget_seconds=max(0.0, args.budget_minutes) * 60)
    finally:
        db.close()
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
