"""Each night, before the catalogue is prepared: what the shops whose rows carry no
category say in their own catalogue, each product's type and stock (owner, 2026-10-26:
«Θα κάνεις το 2 και το 3»).

    /usr/bin/python3 deployment/bot/shop_catalogue_bot.py

Run by picwise-shops.service (picwise-shops.timer, 03:40 UTC, before the preparation at
04:17), as the site's user, with the site's code on PYTHONPATH. It reads the public note
(`prepared.json`) for the shops with rows a search could show but for a category, adds
the shops its file already knows, so a shop whose rows it gave a category is asked
again, and reads the feed's newest copy in the download cache (no key needed) for each
shop's address and the product names in its product addresses. Not InStock UK (the
owner, 2026-10-26: it takes part only with the rows it has right; its catalogue answered
500), and not a shop the owner left out (`eligibility.LEFT_OUT_SHOPS`).

Then, a few shops at a time and one request at a time per shop: its robots.txt, and only
what that allows, 3 seconds apart or its crawl-delay when longer: the pages of its
catalogue (`/products.json`, Shopify's, 250 products a page), at most 200 requests a
shop a round; a larger catalogue goes on next round where this one stopped. Only the
shop's own address, read as text from the Awin link's `ued`, is asked: never an Awin
link, and a redirect to another site is not followed (`shop_catalogue_test.fetch`, the
one look of 2026-10-26, whose asking this reuses).

What it saw is kept on the server, in `/srv/picwise/shared/shops/catalogues.json.gz`
(never in Supabase; the format is in `picwise_providers.shop_catalogue`), for the
products of the feed only: each one's type, whether any variant is in stock, the
variants sold out and the day it was seen; a product not seen for `KEEP_DAYS` days is
forgotten. The preparation reads it. Prints counts and shop names, never an address.
Always exits 0: the preparation never waits on a shop.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import quote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

import shop_catalogue_test as look  # noqa: E402

USER_AGENT = look.USER_AGENT
NOTE = look.NOTE
CACHE_DIR = look.CACHE_DIR
CATALOGUES = "/srv/picwise/shared/shops/catalogues.json.gz"
PAUSE = look.PAUSE
MAX_CRAWL_DELAY = look.MAX_CRAWL_DELAY
PAGE = look.PAGE
# The most requests to one shop in one round, its robots.txt included.
MAX_REQUESTS = 200
# Minutes of asking after the feed's copy is read; the preparation follows at 04:17.
BUDGET = 25.0
# Shops asked at the same time; each one still one request at a time.
WORKERS = 4
# A product not seen for this many days is forgotten.
KEEP_DAYS = 30
# Shops never asked (owner, 2026-10-26), as `eligibility.shop_key` reads a name.
LEFT_ALONE = frozenset({"instock uk"})
# A collection said to hold more products than Shopify pages (100 pages of 250) is left
# for the catalogue itself, as is "all", every product's (owner's «Ναι», 26/10: read a
# large catalogue by its collections).
MAX_COLLECTION = 25_000
SKIPPED_COLLECTIONS = frozenset({"all"})
# The most pages of a shop's list of collections asked in a round.
COLLECTION_LIST_PAGES = 10
_TYPE_LENGTH = 120

Fetch = Callable[[str, int], "look.Answer"]


@dataclass
class FeedShop:
    name: str
    rows: int = 0
    hosts: Counter = field(default_factory=Counter)
    # The product names in its product addresses.
    names: set = field(default_factory=set)


def shops_to_ask(note_path: str, known: Mapping[str, Any]) -> list[str]:
    """The shops with rows a search could show but for a category, by the public note,
    and the shops the file already knows; without InStock UK and the left-out shops."""
    from picwise_providers.eligibility import LEFT_OUT_SHOPS

    names = set(known)
    try:
        names.update(look.shops_from_note(note_path))
    except (OSError, ValueError, KeyError):
        pass
    left = LEFT_ALONE | LEFT_OUT_SHOPS
    return sorted(name for name in names if " ".join(name.split()).casefold() not in left)


def read_feed(path: str, wanted: set[str]) -> tuple[dict[str, FeedShop], int]:
    """Each wanted shop's rows, hosts and product names from the feed's copy, read as the
    preparation reads it (UTF-8, else Latin-1); and the rows read."""
    from picwise_providers.feed_intake import _shop_address
    from picwise_providers.normalization import normalize_feed_row_to_provider_product
    from picwise_providers.shop_catalogue import product_address_name, shop_name

    for encoding in ("utf-8-sig", "latin-1"):
        shops: dict[str, FeedShop] = {}
        read = 0
        try:
            for raw in look._rows(path, encoding):
                read += 1
                name = shop_name(raw)
                if name not in wanted:
                    continue
                product = normalize_feed_row_to_provider_product(raw, provider_key="awin")
                if product is None:
                    continue
                shop = shops.setdefault(name, FeedShop(name))
                shop.rows += 1
                host = urlsplit(_shop_address(product.product_url)).netloc.lower()
                if host:
                    shop.hosts[host] += 1
                handle, _variant = product_address_name(product.product_url)
                if handle:
                    shop.names.add(handle)
            return shops, read
        except UnicodeDecodeError:
            continue
    return {}, 0


def _product_entry(product: Mapping[str, Any], today: str) -> list[Any]:
    variants = [variant for variant in product.get("variants") or () if isinstance(variant, dict)]
    said = [variant for variant in variants if "available" in variant]
    in_stock = 1 if not said or any(variant.get("available") for variant in said) else 0
    sold_out = sorted(str(variant.get("id")) for variant in said if variant.get("available") is False and variant.get("id"))
    product_type = " ".join(str(product.get("product_type") or "").split())[:_TYPE_LENGTH]
    return [product_type, in_stock, today, sold_out]


class _Asker:
    """One shop's requests in one round: never past its cap or the round's time, only
    what robots.txt allows, and the pause before each."""

    def __init__(self, base: str, rules: list, wait: float, *, max_requests: int, deadline: float, fetch: Fetch,
                 sleep: Callable[[float], None], clock: Callable[[], float], result: dict[str, Any]) -> None:
        self.base, self.rules, self.wait = base, rules, wait
        self.max_requests, self.deadline = max_requests, deadline
        self.fetch, self.sleep, self.clock, self.result = fetch, sleep, clock, result

    def __call__(self, path: str) -> "look.Answer | str":
        """The shop's answer, or why it was not asked: "cap", "time" or "robots"."""
        if self.result["requests"] >= self.max_requests:
            return "cap"
        if self.clock() >= self.deadline:
            return "time"
        if not look.robots_allows(self.rules, path):
            return "robots"
        self.sleep(self.wait)
        self.result["requests"] += 1
        return self.fetch(self.base + path, look.MAX_BYTES)


def _read_listing(ask: _Asker, path_of: Callable[[int], str], page: int, page_size: int,
                  record: Callable[[list], list[str]], *, last_page: int | None = None) -> tuple[int, str, int]:
    """Read the pages of one listing of products, the catalogue or a collection, from
    `page` on. Returns the page the next round goes on from (1 once it is read), how it
    ended -- "end" (its last page read), "limit" (the shop pages it no further: Shopify
    answers 400 past page 100), "cap", "time", "robots", or "error <what it answered>"
    -- and the last page read."""
    seen: set[str] = set()
    last_read = 0
    while True:
        if last_page is not None and page > last_page:
            return 1, "limit", last_read
        answer = ask(path_of(page))
        if isinstance(answer, str):
            return page, answer, last_read
        data = look._json(answer)
        listed = data.get("products") if isinstance(data, dict) else None
        if not isinstance(listed, list):
            if answer.status == 400 and page > 1:
                return 1, "limit", last_read
            return page, f"error {look._said(answer) if answer.status != 200 or answer.error else 'not JSON'}", last_read
        last_read = page
        handles = record(listed)
        if page > 1 and handles and all(handle in seen for handle in handles):
            # The shop answers every page with the same products: the listing is read.
            return 1, "end", last_read
        seen.update(handles)
        if len(listed) < page_size:
            return 1, "end", last_read
        page += 1


def _read_collections(ask: _Asker, page_size: int) -> list[list[Any]] | str:
    """The shop's collections, as [name, how many products it says each holds or None],
    or why they could not be read."""
    found: list[list[Any]] = []
    for page in range(1, COLLECTION_LIST_PAGES + 1):
        answer = ask(f"/collections.json?limit={page_size}&page={page}")
        if isinstance(answer, str):
            return found or answer
        data = look._json(answer)
        listed = data.get("collections") if isinstance(data, dict) else None
        if not isinstance(listed, list):
            return found or f"error {look._said(answer) if answer.status != 200 or answer.error else 'not JSON'}"
        for collection in listed:
            if isinstance(collection, dict) and str(collection.get("handle") or "").strip():
                count = collection.get("products_count")
                found.append([str(collection["handle"]).strip(), count if isinstance(count, int) else None])
        if len(listed) < page_size:
            break
    return found


def ask_shop(shop: FeedShop, entry: Mapping[str, Any], *, scheme: str = "https", pause: float = PAUSE,
             max_requests: int = MAX_REQUESTS, page_size: int = PAGE, deadline: float, fetch: Fetch,
             sleep: Callable[[float], None], clock: Callable[[], float], now: datetime) -> dict[str, Any]:
    """One round of one shop: its robots.txt, then its catalogue's pages from where the
    last round stopped; for a catalogue the shop pages no further than page 100, then its
    collections, one after another, from where the last round stopped. Returns the
    shop's new entry for the file."""
    today = now.date().isoformat()
    products: dict[str, list[Any]] = {
        handle: known for handle, known in (entry.get("products") or {}).items() if handle in shop.names
    }
    result: dict[str, Any] = {
        "status": "", "read_at": now.isoformat(timespec="seconds"), "next_page": int(entry.get("next_page") or 1),
        "complete_at": str(entry.get("complete_at") or ""), "pages": 0, "requests": 0, "seen": 0,
        "products": products,
    }
    for key in ("page_limit", "collections", "collection_cursor", "collections_complete_at"):
        if entry.get(key) is not None:
            result[key] = entry[key]
    if clock() >= deadline:
        result["status"] = "not asked, out of time"
        return result
    if not shop.hosts:
        result["status"] = "no address"
        return result
    host = shop.hosts.most_common(1)[0][0]
    if "awin" in host:
        result["status"] = "awin only"
        return result
    base = f"{scheme}://{host}"
    robots = fetch(f"{base}/robots.txt", look.ROBOTS_BYTES)
    result["requests"] += 1
    if robots.status == 200:
        rules, delay = look.robots_rules(robots.body.decode("utf-8", "replace"))
    elif robots.status in (404, 410):
        rules, delay = [], None
    else:
        result["status"] = f"robots.txt {look._said(robots)}"
        return result
    wait = max(pause, delay or 0.0)
    if wait > MAX_CRAWL_DELAY:
        result["status"] = "crawl-delay too long"
        return result
    ask = _Asker(base, rules, wait, max_requests=max_requests, deadline=deadline, fetch=fetch, sleep=sleep,
                 clock=clock, result=result)
    seen_now: set[str] = set()

    def record(listed: list) -> list[str]:
        result["pages"] += 1
        handles = []
        for product in listed:
            if not isinstance(product, dict):
                continue
            handle = str(product.get("handle") or "").strip().lower()
            if not handle:
                continue
            handles.append(handle)
            seen_now.add(handle)
            if handle in shop.names:
                products[handle] = _product_entry(product, today)
        return handles

    def catalogue_path(page: int) -> str:
        return f"/products.json?limit={page_size}&page={page}"

    page_limit = result.get("page_limit")
    start = max(1, result["next_page"])
    page, ended, last_read = _read_listing(ask, catalogue_path, start, page_size, record, last_page=page_limit)
    if ended == "limit" and start > 1:
        # A round that went on from an earlier one starts again from page 1, once.
        page, ended, last_read = _read_listing(ask, catalogue_path, 1, page_size, record, last_page=page_limit)
    if ended == "limit" and page_limit is None and last_read:
        # Shopify pages a catalogue up to page 100 (25,000 products) and answers 400 past
        # it (Back to the Office, 95,050 products, run 40329354654): page that far again.
        result["page_limit"] = page_limit = last_read
    result["next_page"] = page
    if ended in ("end", "limit"):
        result["complete_at"] = result["read_at"]
    status = {
        "end": "read", "limit": "read to the shop's page limit", "cap": "read, goes on next round",
        "time": "read, out of time", "robots": "robots.txt disallows the catalogue",
    }.get(ended, ended.replace("error", "catalogue", 1))
    if ended == "limit" and page_limit:
        status += "; " + _read_shop_collections(ask, result, page_size, record)
    result["status"] = status
    result["seen"] = len(seen_now & shop.names)
    return result


def _read_shop_collections(ask: _Asker, result: dict[str, Any], page_size: int,
                           record: Callable[[list], list[str]]) -> str:
    """The products of a shop's collections, one after another, from where the last
    round stopped, with what the round has left; the collections are listed again after
    each whole pass. Returns how far it went, for the status."""
    collections = result.get("collections") or []
    index, page = (list(result.get("collection_cursor") or [0, 1]) + [0, 1])[:2]
    if not collections or index >= len(collections):
        listed = _read_collections(ask, page_size)
        if isinstance(listed, str):
            return f"its collections not listed ({listed})"
        collections, index, page = listed, 0, 1
    ended = ""
    while index < len(collections):
        name, count = collections[index]
        if name.lower() in SKIPPED_COLLECTIONS or count == 0 or (count is not None and count > MAX_COLLECTION):
            index, page = index + 1, 1
            continue

        def collection_path(number: int, name: str = name) -> str:
            return f"/collections/{quote(name, safe='')}/products.json?limit={page_size}&page={number}"

        page, ended, _last = _read_listing(ask, collection_path, page, page_size, record)
        if ended in ("cap", "time"):
            break
        index, page = index + 1, 1
    if index >= len(collections):
        # Listed again next round, so a new collection is read too.
        result["collections"] = []
        result["collection_cursor"] = [0, 1]
        result["collections_complete_at"] = result["read_at"]
        return f"its {len(collections)} collections read"
    result["collections"] = collections
    result["collection_cursor"] = [index, page]
    return f"its collections read to {index} of {len(collections)}, " + (
        "goes on next round" if ended == "cap" else "out of time"
    )


def _old(day: Any, today: date) -> bool:
    try:
        return (today - date.fromisoformat(str(day))).days > KEEP_DAYS
    except ValueError:
        return True


def load(path: str) -> dict[str, Any]:
    from picwise_providers.shop_catalogue import load_shop_catalogues

    data, _status = load_shop_catalogues(path)
    return data or {"version": 1, "shops": {}}


def write(path: str, data: Mapping[str, Any]) -> None:
    """Write the file whole or not at all."""
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".catalogues-", dir=folder)
    try:
        with os.fdopen(handle, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as packed:
            packed.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        os.chmod(temporary, 0o640)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def run_round(*, note: str, cache_dir: str, catalogues: str, scheme: str = "https", pause: float = PAUSE,
              max_requests: int = MAX_REQUESTS, page_size: int = PAGE, budget_minutes: float = BUDGET,
              workers: int = WORKERS, fetch: Fetch = look.fetch, sleep: Callable[[float], None] = time.sleep,
              clock: Callable[[], float] = time.monotonic, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    data = load(catalogues)
    known: dict[str, Any] = dict(data.get("shops") or {})
    wanted = shops_to_ask(note, known)
    copy = look.feed_copy(cache_dir)
    if copy is None:
        print("no copy of the feed in the download cache: nothing asked")
        return 0
    feed, read = read_feed(copy, set(wanted))
    print(
        f"the feed's copy: {read:,} rows read; {len(wanted)} shops to ask, {len(feed)} of them in it; "
        f"asked as {USER_AGENT}, {pause:g} s apart or a shop's crawl-delay, at most {max_requests} requests a shop"
    )
    # The shops never read first, then those read longest ago.
    order = sorted(feed.values(), key=lambda shop: (str((known.get(shop.name) or {}).get("read_at") or ""), -shop.rows, shop.name))
    deadline = clock() + budget_minutes * 60

    def one(shop: FeedShop) -> tuple[str, dict[str, Any]]:
        return shop.name, ask_shop(shop, known.get(shop.name) or {}, scheme=scheme, pause=pause,
                                   max_requests=max_requests, page_size=page_size, deadline=deadline,
                                   fetch=fetch, sleep=sleep, clock=clock, now=now)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = list(pool.map(one, order))
    for name, entry in results:
        known[name] = entry
        print(
            f"== {name}: {entry['status']}; {entry['requests']} requests, {entry['pages']} pages, "
            f"{entry['seen']:,} of its {len(feed[name].names):,} products seen now, {len(entry['products']):,} known"
            + (f"; next round from page {entry['next_page']}" if entry["next_page"] > 1 else "")
        )
    today = now.date()
    for name in list(known):
        entry = known[name]
        if name not in feed and _old(str(entry.get("read_at") or "")[:10], today):
            del known[name]
            continue
        entry["products"] = {
            handle: value for handle, value in (entry.get("products") or {}).items()
            if isinstance(value, list) and len(value) >= 4 and not _old(value[2], today)
        }
    write(catalogues, {"version": 1, "written_at": now.isoformat(timespec="seconds"), "shops": known})
    products = sum(len(entry.get("products") or {}) for entry in known.values())
    with_type = sum(1 for entry in known.values() for value in (entry.get("products") or {}).values() if value[0])
    sold_out = sum(1 for entry in known.values() for value in (entry.get("products") or {}).values() if not value[1])
    print(
        f"in all: {len(results)} shops asked, {sum(entry['requests'] for _name, entry in results):,} requests; "
        f"the file knows {len(known)} shops, {products:,} products ({with_type:,} with a type, {sold_out:,} sold out)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--note", default=NOTE)
    parser.add_argument("--cache-dir", default=CACHE_DIR)
    parser.add_argument("--catalogues", default=CATALOGUES)
    parser.add_argument("--budget", type=float, default=BUDGET, help="minutes")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    try:
        return run_round(note=args.note, cache_dir=args.cache_dir, catalogues=args.catalogues,
                         budget_minutes=args.budget)
    except Exception as error:  # the preparation never waits on a shop
        print(f"the round failed: {type(error).__name__}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
