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

With the checks' switch on (`data/checks_switch.json`; the checks' rules 5.4, owner,
2026-11-21: «Αμέσως, για κάθε λόγο»), any failure leaves the photo's products out that
night: no answer or a server error (asked once more at the end of the run), an answer
that is no image, an empty one, a refusal; a 429 is our own pace and not a failure, and a
shop whose photo host refuses at least 9 in 10 of 20 photos asked has them not checked.
The brakes of the rules' 7.2 and 7.4 hold, by the same numbers: a shop whose new
failures pass a quarter of its photos decided (at least 20) has them held one night and
asked first (until the owner's word where it has fewer than 20 photos read on record),
and a night whose new failures would leave out over a tenth of the products cuts none.
A failure other than 404 and 410 is asked again the next night.

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


# With the checks' switch on, a 200 that is no image is read as 415 and an empty one as
# 204 (their HTTP meanings), so that the night's answers stay one number each.
NOT_AN_IMAGE = 415
EMPTY = 204
# The checks' rules 5.4 and 7.2 (`picwise_checks.brakes`), for photos.
REFUSED_SHARE = 0.9
REFUSED_MIN = 20
SHOP_MIN_DECIDED = 20
SHOP_NEW_FAILURES_SHARE = 0.25
SHOP_MIN_PASSES = 20
NIGHT_NEW_CUTS_SHARE = 0.10
OWNER_WORDS = Path(__file__).resolve().parents[2] / "data" / "checks_owner_words.json"


def checks_switch_on() -> bool:
    """The checks' switch (`picwise_providers.checks_applied`, the checks' rules 7.7)."""
    root = Path(__file__).resolve().parents[2]
    for folder in (root, root / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    from picwise_providers.checks_applied import checks_switch_on as switch_on

    return switch_on()


class Asker:
    """Asks for photos over connections kept open, one set per thread. `strict` (the
    checks' switch on): a 200 that is no image answers 415, an empty one 204."""

    def __init__(self, *, strict: bool = False) -> None:
        self._local = threading.local()
        self.strict = strict

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
                self._local.kind = (response.getheader("Content-Type") or "").split(";")[0].strip().lower()
                self._local.length = response.getheader("Content-Length")
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
                return self._strictly(status, method)
            return self._strictly(status, "GET")
        except (ValueError, http.client.HTTPException, OSError):
            return 0

    def _strictly(self, status: int, method: str) -> int:
        if not self.strict or status != 200:
            return status
        kind = getattr(self._local, "kind", "")
        if kind and not kind.startswith("image/") and kind != "application/octet-stream":
            return NOT_AN_IMAGE
        if method == "HEAD" and str(getattr(self._local, "length", None) or "").strip() == "0":
            return EMPTY
        return status


def state_of(status: int, *, strict: bool = False) -> str:
    """"ok", "gone", or "unread" for an answer: only a link to nothing is gone. `strict`
    (the checks' switch on, rules 5.4): any other failure is "failed", a refusal
    "refused" (judged with its shop's other photos), a 429 "unread"."""
    if status in GONE_STATUSES:
        return "gone"
    if not strict:
        return "ok" if 200 <= status < 300 else "unread"
    if 200 <= status < 300 and status != EMPTY:
        return "ok"
    if status == 429:
        return "unread"
    if status in (401, 403):
        return "refused"
    return "failed"


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
        if state in ("held", "held for the owner"):
            order.append((0, asked, url))
        elif state in ("unread", "failed") and now - asked >= AGAIN_UNREAD:
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


def owner_cut_shops(path: Path = OWNER_WORDS) -> set[str]:
    """The shops whose held products the owner said to cut («κόψε»; the checks' rules 7.2)."""
    try:
        return {str(name) for name in json.loads(path.read_text(encoding="utf-8")).get("cut_held_shops", [])}
    except (OSError, ValueError, AttributeError):
        return set()


def strict_states(photos: dict[str, tuple[str, int]], answers: dict[str, int], before: dict[str, tuple[str, int]],
                  *, owner_cut: set[str] = frozenset()) -> tuple[dict[str, str], dict[str, object]]:
    """Tonight's states with the checks' switch on (module docstring), and what the brakes did."""
    states = {url: state_of(status, strict=True) for url, status in answers.items()}
    shop_of = {url: photos.get(url, ("", 0))[0] or "-" for url in answers}
    asked: Counter = Counter(shop_of.values())
    refused: Counter = Counter(shop_of[url] for url, state in states.items() if state == "refused")
    hosts_refusing = {shop for shop, count in refused.items()
                      if asked[shop] >= REFUSED_MIN and count >= REFUSED_SHARE * asked[shop]}
    for url, state in states.items():
        if state == "refused":
            states[url] = "unread" if shop_of[url] in hosts_refusing else "failed"
    passes_on_record: Counter = Counter(photos.get(url, ("", 0))[0] or "-" for url, (state, _asked) in before.items()
                                        if state == "ok" and url in photos)
    decided: Counter = Counter()
    new_failures: dict[str, list[str]] = {}
    for url, state in states.items():
        if state in ("ok", "failed", "gone"):
            decided[shop_of[url]] += 1
        was = before.get(url, ("", 0))[0]
        if state in ("failed", "gone") and was not in ("failed", "gone", "held", "held for the owner"):
            new_failures.setdefault(shop_of[url], []).append(url)
        elif state in ("failed", "gone") and was == "held for the owner" and shop_of[url] not in owner_cut:
            states[url] = "held for the owner"
    braked: list[str] = []
    for shop, urls in new_failures.items():
        if decided[shop] >= SHOP_MIN_DECIDED and len(urls) > SHOP_NEW_FAILURES_SHARE * decided[shop]:
            braked.append(shop)
            held = "held" if passes_on_record[shop] >= SHOP_MIN_PASSES else "held for the owner"
            for url in urls:
                states[url] = held
    products = sum(count for _shop, count in photos.values())
    cut_products = sum(photos.get(url, ("", 0))[1] for urls in new_failures.values() for url in urls
                       if states[url] in ("failed", "gone"))
    night_brake = products > 0 and cut_products > NIGHT_NEW_CUTS_SHARE * products
    if night_brake:
        for urls in new_failures.values():
            for url in urls:
                if states[url] in ("failed", "gone"):
                    states[url] = "held"
    return states, {"hosts_refusing": sorted(hosts_refusing), "braked_shops": sorted(braked),
                    "night_brake": night_brake}


def run(photos: dict[str, tuple[str, int]], db: sqlite3.Connection, out: Path, fetch: Fetch, *,
        workers: int = WORKERS, budget_seconds: float = 3600.0, now: datetime | None = None,
        strict: bool = False, clock: Callable[[], float] = time.monotonic) -> list[str]:
    """Ask tonight's addresses, keep their answers, write the gone ones; the lines to print.
    `strict`: the checks' switch is on (module docstring)."""
    moment = now or datetime.now(timezone.utc)
    stamp = int(moment.timestamp())
    seen = known(db)
    before = dict(seen)
    tonight = due(photos, seen, stamp)
    started = clock()
    answers = ask_all(tonight, fetch, workers=workers, budget_seconds=budget_seconds, clock=clock)
    brakes: dict[str, object] = {}
    if strict:
        # No answer or a server error: asked once more at the end of the run (rules 5.4).
        again = [url for url, status in answers.items() if status == 0 or 500 <= status < 600]
        left = budget_seconds - (clock() - started)
        if again and left > 0:
            answers.update(ask_all(again, fetch, workers=workers, budget_seconds=left, clock=clock))
        tonight_states, brakes = strict_states(photos, answers, before, owner_cut=owner_cut_shops())
    else:
        tonight_states = {url: state_of(status) for url, status in answers.items()}
    states = Counter()
    rows = []
    for url, status in answers.items():
        state = tonight_states[url]
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
    leave_out = ("gone", "failed") if strict else ("gone",)
    gone = sorted(url for url in photos if seen.get(url, ("", 0))[0] in leave_out)
    never = sum(1 for url in photos if url not in seen)
    write({"checked_at": moment.isoformat(timespec="seconds"), "photos": len(photos), "gone": gone}, out)
    gone_products = sum(photos[url][1] for url in gone)
    products = sum(count for _shop, count in photos.values())
    lines = [
        f"photos: {len(photos):,} in the catalogue, of {products:,} products; asked tonight "
        f"{len(answers):,} of the {len(tonight):,} due (read {states['ok']:,}, gone {states['gone']:,}, "
        f"could not be read {states['unread']:,}"
        + (f", failed {states['failed']:,}, held {states['held'] + states['held for the owner']:,}" if strict else "")
        + f"); never asked yet {never:,}",
        f"photos gone: {len(gone):,}, of {gone_products:,} products, left out of the site"
        + (" (any failure: the checks' switch is on)" if strict else ""),
    ]
    if brakes.get("night_brake"):
        lines.append("photos: THE NIGHT'S BRAKE: over a tenth of the products would go; no new photo cut tonight")
    if brakes.get("braked_shops"):
        lines.append("photos: shops braked (held one night): " + ", ".join(brakes["braked_shops"]))
    if brakes.get("hosts_refusing"):
        lines.append("photos: shops whose photo host refuses the check (not checked): "
                     + ", ".join(brakes["hosts_refusing"]))
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
    strict = checks_switch_on()
    try:
        lines = run(photos, db, args.out, fetch or Asker(strict=strict), workers=args.workers,
                    budget_seconds=max(0.0, args.budget_minutes) * 60, strict=strict)
    finally:
        db.close()
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
