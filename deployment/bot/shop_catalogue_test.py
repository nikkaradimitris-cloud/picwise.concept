"""One look at the shops whose rows a search could show but for a category: does each
publish its catalogue for machines, and does that catalogue say what each product is?
(owner, 2026-10-26: «ναι, ξεκίνα τη δοκιμή στα 56 καταστήματα»).

    ssh picwise 'sudo systemd-run --quiet --wait --pipe --collect -p User=picwise ... \
        /usr/bin/python3 -' < deployment/bot/shop_catalogue_test.py

Run once by .github/workflows/server-shop-test.yml, on the server, as the site's user,
with the site's code on PYTHONPATH. It reads the public note (`prepared.json`) for the
shops with rows a search could show but for a category, and the feed's copy in the
download cache (no key needed) for each shop's address and the product names in its
product addresses. Then, one shop at a time: its robots.txt, and only what that allows,
3 seconds apart or its crawl-delay when longer: the first page of its catalogue
(`/products.json`, Shopify's, up to 250 products), one of its rows without a category
(`/products/<name>.js`), and, for a shop of more than 5,000 rows, a page past the
5,000th product, else its collections (`/collections.json`). Only the shop's own
address, read as text from the Awin link's `ued`, is asked: never an Awin link, and a
redirect to another site is not followed. Prints counts, shop names, their hosts, the
shops' own types and collection names; never a whole address. Changes nothing.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterator
from urllib.parse import quote, unquote, urlsplit

USER_AGENT = "PicWiseBot/0.1 (+https://picwise.subby.cloud)"
# The name a robots.txt may give this bot its own rules under.
ROBOTS_TOKEN = "picwisebot"
NOTE = "/srv/picwise/shared/public/prepared.json"
CACHE_DIR = "/srv/picwise/shared/cache"
# Seconds between two requests to the same shop, or its crawl-delay when longer.
PAUSE = 3.0
# A crawl-delay longer than this leaves the shop out.
MAX_CRAWL_DELAY = 60.0
TIMEOUT = 20
# Minutes after which no further shop is asked, so the run ends within its job.
BUDGET = 35.0
# The most read of one answer; of a robots.txt, the first 500 KiB, as Google reads it.
MAX_BYTES = 20 * 1024 * 1024
ROBOTS_BYTES = 500 * 1024
PAGE = 250
# A shop of more rows than this is asked for page 21, its products 5,001 to 5,250:
# Shopify's catalogue is said, unconfirmed, to stop at 5,000 products for large shops.
LARGE_SHOP = 5000
PAST_PAGE = 21
# How many of a shop's types and collections are printed, the most frequent first.
LISTED = 8
# How many of a shop's product names without a category are kept to ask one of.
SAMPLE = 5


@dataclass
class Shop:
    name: str
    # Its rows a search could show but for a category, as the note counts them.
    showable: int
    rows: int = 0
    without_category: int = 0
    hosts: Counter = field(default_factory=Counter)
    # The product names in its product addresses ("/products/<name>"), of all its rows
    # and of those without a category.
    names: set = field(default_factory=set)
    names_without: set = field(default_factory=set)
    in_stock_sample: list = field(default_factory=list)
    other_sample: list = field(default_factory=list)


@dataclass
class Answer:
    # 0 when no answer came.
    status: int
    content_type: str = ""
    body: bytes = b""
    # Why no answer came: a timeout, a refused connection, a redirect to another site.
    error: str = ""


Fetch = Callable[[str, int], Answer]


# ---- robots.txt -----------------------------------------------------------------


def robots_rules(text: str, token: str = ROBOTS_TOKEN) -> tuple[list[tuple[bool, str]], float | None]:
    """The Allow and Disallow rules of the groups naming `token`, else of the "*" groups,
    and their crawl-delay (RFC 9309; Crawl-delay is not in it, read as most crawlers do)."""
    groups: list[tuple[list[str], list[tuple[bool, str]], float | None]] = []
    agents: list[str] = []
    rules: list[tuple[bool, str]] = []
    delay: float | None = None
    in_rules = False
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        name, value = (part.strip() for part in line.split(":", 1))
        name = name.lower()
        if name == "user-agent":
            if in_rules:
                groups.append((agents, rules, delay))
                agents, rules, delay, in_rules = [], [], None, False
            agents.append(value.lower())
        elif name in ("allow", "disallow"):
            in_rules = True
            # An empty Disallow allows everything: no rule.
            if value:
                rules.append((name == "allow", value))
        elif name == "crawl-delay":
            in_rules = True
            try:
                delay = float(value)
            except ValueError:
                pass
    if agents:
        groups.append((agents, rules, delay))
    chosen = [group for group in groups if token in group[0]] or [group for group in groups if "*" in group[0]]
    merged = [rule for group in chosen for rule in group[1]]
    delays = [group[2] for group in chosen if group[2] is not None]
    return merged, (max(delays) if delays else None)


def _robots_match(pattern: str, target: str) -> bool:
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    expression = ".*".join(re.escape(part) for part in body.split("*"))
    return re.match(expression + ("$" if anchored else ""), target) is not None


def robots_allows(rules: list[tuple[bool, str]], target: str) -> bool:
    """Whether a path with its query may be asked: the longest matching rule decides,
    Allow when an Allow and a Disallow are as long (RFC 9309)."""
    best: tuple[int, bool] | None = None
    for allow, pattern in rules:
        if _robots_match(pattern, target):
            candidate = (len(pattern), allow)
            if best is None or candidate > best:
                best = candidate
    return True if best is None else best[1]


# ---- asking a shop ----------------------------------------------------------------


def _site(host: str) -> str:
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


class _Elsewhere(Exception):
    pass


class _SameSiteRedirects(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only within the same site (with or without "www.")."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        if _site(urlsplit(newurl).netloc) != _site(urlsplit(req.full_url).netloc):
            raise _Elsewhere(urlsplit(newurl).netloc.lower())
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# Never through a proxy: the server asks the shop itself.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _SameSiteRedirects())


def fetch(url: str, limit: int = MAX_BYTES) -> Answer:
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json, text/plain;q=0.9, */*;q=0.5"}
    )
    try:
        with _OPENER.open(request, timeout=TIMEOUT) as response:
            body = response.read(limit + 1)
            content_type = response.headers.get("Content-Type", "")
            # Too large: its first part only, which a robots.txt is read by.
            if len(body) > limit:
                return Answer(response.status, content_type, body[:limit], "too large")
            return Answer(response.status, content_type, body)
    except _Elsewhere as moved:
        return Answer(0, error=f"redirected to another site ({moved})")
    except urllib.error.HTTPError as error:
        return Answer(error.code, error.headers.get("Content-Type", "") if error.headers else "")
    except (urllib.error.URLError, OSError, ValueError) as error:
        reason = getattr(error, "reason", error)
        return Answer(0, error=reason if isinstance(reason, str) else type(reason).__name__)


def _json(answer: Answer) -> Any:
    """The answer read as JSON, or None when it is not JSON (a page, a password wall)."""
    if answer.status != 200 or answer.error or answer.body.lstrip()[:1] not in (b"{", b"["):
        return None
    try:
        return json.loads(answer.body.decode("utf-8", "replace"))
    except ValueError:
        return None


def _said(answer: Answer) -> str:
    if answer.error:
        return f"no answer ({answer.error})"
    if answer.status == 200:
        kind = answer.content_type.split(";")[0].strip() or "no content type"
        return f"200, not JSON ({kind})"
    return str(answer.status)


# ---- the feed's copy and the note -----------------------------------------------


def shops_from_note(path: str) -> dict[str, Shop]:
    """The shops with rows a search could show but for a category, the most first."""
    with open(path, encoding="utf-8") as handle:
        note = json.load(handle)
    entries = (note.get("intake") or {}).get("shops") or []
    shops = []
    for entry in entries:
        without = entry.get("without_category") or {}
        showable = int(without.get("shown_by_title") or 0) + int(without.get("shown_by_type") or 0)
        if showable:
            shops.append(Shop(entry["shop"], showable))
    shops.sort(key=lambda shop: (-shop.showable, shop.name))
    return {shop.name: shop for shop in shops}


def feed_copy(cache_dir: str) -> str | None:
    """The newest copy of the feed the preparation downloaded (never a partial one)."""
    copies = glob.glob(os.path.join(cache_dir, "picwise_awin_feed_*.bin"))
    return max(copies, key=os.path.getmtime) if copies else None


def product_name(path: str) -> str:
    """The product's name in a Shopify-like address: what follows its last "products"."""
    segments = [unquote(segment) for segment in path.split("/") if segment]
    for index in range(len(segments) - 2, -1, -1):
        if segments[index].lower() == "products":
            return segments[index + 1].strip().lower()
    return ""


def _rows(path: str, encoding: str) -> Iterator[dict[str, str]]:
    from picwise_providers.awin_adapter import _is_gzip_file, _open_feed_text

    with _open_feed_text(path, gzipped=_is_gzip_file(path), encoding=encoding) as text:
        reader = csv.reader(text)
        header = next(reader, None) or []
        for row in reader:
            if row:
                yield {key: value for key, value in zip(header, row) if value}


def read_feed(path: str, shops: dict[str, Shop]) -> int:
    """Fill each shop's rows, hosts and product names from the feed's copy, read as the
    preparation reads it (UTF-8, else Latin-1); return the rows read."""
    from picwise_providers.feed_intake import _shop_address
    from picwise_providers.normalization import extract_merchant_name, normalize_feed_row_to_provider_product

    for encoding in ("utf-8-sig", "latin-1"):
        for name, shop in list(shops.items()):
            shops[name] = Shop(shop.name, shop.showable)
        read = 0
        try:
            for raw in _rows(path, encoding):
                read += 1
                shop = shops.get(" ".join(str(extract_merchant_name(raw) or "?").split()))
                if shop is None:
                    continue
                product = normalize_feed_row_to_provider_product(raw, provider_key="awin")
                if product is None:
                    continue
                shop.rows += 1
                address = urlsplit(_shop_address(product.product_url))
                if address.netloc:
                    shop.hosts[address.netloc.lower()] += 1
                name = product_name(address.path)
                if name:
                    shop.names.add(name)
                if " ".join(str(product.category_text or "").split()):
                    continue
                shop.without_category += 1
                if name:
                    shop.names_without.add(name)
                    in_stock = " ".join(str(product.availability_text or "").lower().replace("_", " ").split())
                    sample = shop.in_stock_sample if in_stock == "in stock" else shop.other_sample
                    if len(sample) < SAMPLE:
                        sample.append(name)
            return read
        except UnicodeDecodeError:
            continue
    return 0


# ---- what a shop's catalogue says -------------------------------------------------


def _share(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "-"


def _kinds(read: Callable[[str, str, str], frozenset], product_type: str, title: str) -> set[str]:
    return {kind for kind in read(product_type, "", title) if not kind.startswith("__")}


def catalogue_page(products: list[dict], shop: Shop, read: Callable) -> dict[str, Any]:
    """What one page of a shop's catalogue says: how many products name a type and tags,
    say their stock, are in the feed (and among its rows without a category), and get a
    kind from their type and title, against the title alone."""
    page = {"products": len(products), "type": 0, "tags": 0, "stock_said": 0, "in_stock": 0, "in_feed": 0,
            "in_feed_without": 0, "kind": 0, "title_kind": 0, "type_adds": 0, "differ": 0, "types": Counter()}
    for product in products:
        if not isinstance(product, dict):
            continue
        product_type = " ".join(str(product.get("product_type") or "").split())
        title = " ".join(str(product.get("title") or "").split())
        if product_type:
            page["type"] += 1
            page["types"][product_type] += 1
        if product.get("tags"):
            page["tags"] += 1
        variants = [variant for variant in product.get("variants") or () if isinstance(variant, dict)]
        if any("available" in variant for variant in variants):
            page["stock_said"] += 1
            if any(variant.get("available") for variant in variants):
                page["in_stock"] += 1
        handle = str(product.get("handle") or "").strip().lower()
        if handle in shop.names:
            page["in_feed"] += 1
            if handle in shop.names_without:
                page["in_feed_without"] += 1
        with_type = _kinds(read, product_type, title)
        alone = _kinds(read, "", title)
        page["kind"] += bool(with_type)
        page["title_kind"] += bool(alone)
        page["type_adds"] += bool(with_type and not alone)
        page["differ"] += bool(with_type and alone and not with_type & alone)
    return page


def ask_shop(shop: Shop, *, scheme: str, pause: float, large_shop: int, fetch: Fetch,
             sleep: Callable[[float], None], read: Callable) -> dict[str, Any]:
    """Ask one shop what robots.txt allows; print what it says; return it for the table."""
    result: dict[str, Any] = {"shop": shop.name, "showable": shop.showable, "robots": "-", "catalogue": "-",
                              "type": "-", "kind": "-", "title_kind": "-", "product": "-", "past": "-",
                              "collections": "-", "asked": 0, "open": False, "typed": False}
    print(
        f"== {shop.name}: {shop.showable:,} rows a search could show but for a category "
        f"(in the feed's copy: {shop.rows:,} rows, {shop.without_category:,} without a category)"
    )
    if not shop.hosts:
        print("   no shop address in its rows: nothing asked")
        result["robots"] = "no address"
        return result
    host = shop.hosts.most_common(1)[0][0]
    print(f"   host: {host} ({len(shop.hosts)} host{'s' if len(shop.hosts) != 1 else ''} in its rows)")
    if "awin" in host:
        print("   its address is Awin's: nothing asked")
        result["robots"] = "awin only"
        return result
    base = f"{scheme}://{host}"
    robots = fetch(f"{base}/robots.txt", ROBOTS_BYTES)
    result["asked"] += 1
    if robots.status == 200:
        rules, delay = robots_rules(robots.body.decode("utf-8", "replace"))
        result["robots"] = "read"
    elif robots.status in (404, 410):
        rules, delay = [], None
        result["robots"] = "none"
    else:
        print(f"   robots.txt: {_said(robots)}: nothing else asked")
        result["robots"] = f"{robots.status or 'no answer'}"
        return result
    wait = max(pause, delay or 0.0)
    print(f"   robots.txt: {'read' if robots.status == 200 else robots.status}; crawl-delay: "
          f"{'none' if delay is None else f'{delay:g} s'}")
    if wait > MAX_CRAWL_DELAY:
        print(f"   a crawl-delay over {MAX_CRAWL_DELAY:g} s: nothing else asked")
        result["robots"] = "slow"
        return result

    def ask(path: str, label: str) -> Answer | None:
        if not robots_allows(rules, path):
            print(f"   {label}: not asked, robots.txt disallows it")
            return None
        sleep(wait)
        result["asked"] += 1
        return fetch(base + path, MAX_BYTES)

    # 1. The catalogue's first page.
    answer = ask(f"/products.json?limit={PAGE}", "/products.json")
    data = _json(answer) if answer else None
    products = data.get("products") if isinstance(data, dict) else None
    if isinstance(products, list):
        page = catalogue_page(products, shop, read)
        result.update(catalogue=f"{page['products']}", open=True, type=_share(page["type"], page["products"]),
                      kind=_share(page["kind"], page["products"]),
                      title_kind=_share(page["title_kind"], page["products"]),
                      typed=page["products"] > 0 and page["type"] >= 0.8 * page["products"])
        print(
            f"   /products.json: a catalogue of {page['products']} products; a type {page['type']} "
            f"({_share(page['type'], page['products'])}), tags {page['tags']}; stock said {page['stock_said']}, "
            f"in stock {page['in_stock']}"
        )
        print(
            f"      a kind from type and title {page['kind']} ({_share(page['kind'], page['products'])}), "
            f"the title alone {page['title_kind']} ({_share(page['title_kind'], page['products'])}); "
            f"the type adds {page['type_adds']}, they differ {page['differ']}"
        )
        print(f"      in the feed {page['in_feed']}, of them without a category {page['in_feed_without']}")
        if page["types"]:
            print("      types: " + "; ".join(f"{value} ({count})" for value, count in page["types"].most_common(LISTED)))
    elif answer is not None:
        result["catalogue"] = _said(answer) if answer.status != 200 else "not JSON"
        print(f"   /products.json: {_said(answer)}")
    else:
        result["catalogue"] = "disallowed"

    # 2. One of its rows without a category, by its own address's product name.
    sample = shop.in_stock_sample or shop.other_sample
    if not sample:
        result["product"] = "no name"
        print("   /products/<name>.js: no product name in the addresses of its rows without a category")
    else:
        answer = ask(f"/products/{quote(sample[0])}.js", "/products/<name>.js")
        data = _json(answer) if answer else None
        if isinstance(data, dict) and "title" in data:
            product_type = " ".join(str(data.get("type") or "").split())
            title = " ".join(str(data.get("title") or "").split())
            with_type = sorted(_kinds(read, product_type, title))
            alone = sorted(_kinds(read, "", title))
            result["product"] = "a type" if product_type else "no type"
            print(
                f"   /products/<name>.js (a row without a category): type "
                f"{json.dumps(product_type[:60], ensure_ascii=False)}; a kind: {', '.join(with_type) or 'none'} "
                f"(the title alone: {', '.join(alone) or 'none'}); in stock: "
                f"{'yes' if data.get('available') else 'no' if 'available' in data else 'not said'}"
            )
        elif answer is not None:
            result["product"] = _said(answer) if answer.status != 200 else "not JSON"
            print(f"   /products/<name>.js (a row without a category): {_said(answer)}")
        else:
            result["product"] = "disallowed"

    # 3. Past the 5,000th product for a large shop, else its collections.
    if shop.rows > large_shop:
        answer = ask(f"/products.json?limit={PAGE}&page={PAST_PAGE}", f"/products.json page {PAST_PAGE}")
        data = _json(answer) if answer else None
        products = data.get("products") if isinstance(data, dict) else None
        if isinstance(products, list):
            result["past"] = f"{len(products)}"
            first = PAGE * (PAST_PAGE - 1) + 1
            print(f"   /products.json page {PAST_PAGE} (products {first:,} to {first + PAGE - 1:,}): "
                  f"{len(products)} products")
        elif answer is not None:
            result["past"] = _said(answer) if answer.status != 200 else "not JSON"
            print(f"   /products.json page {PAST_PAGE}: {_said(answer)}")
        else:
            result["past"] = "disallowed"
    else:
        answer = ask(f"/collections.json?limit={PAGE}", "/collections.json")
        data = _json(answer) if answer else None
        collections = data.get("collections") if isinstance(data, dict) else None
        if isinstance(collections, list):
            result["collections"] = f"{len(collections)}"
            names = [" ".join(str(entry.get("title") or "").split()) for entry in collections if isinstance(entry, dict)]
            print(f"   /collections.json: {len(collections)} collections" +
                  (": " + "; ".join(name for name in names[:LISTED] if name) if names else ""))
        elif answer is not None:
            result["collections"] = _said(answer) if answer.status != 200 else "not JSON"
            print(f"   /collections.json: {_said(answer)}")
        else:
            result["collections"] = "disallowed"
    return result


def print_table(results: list[dict[str, Any]]) -> None:
    print()
    print(f"{'rows':>9}  {'robots':<10} {'catalogue':<12} {'a type':>7} {'a kind':>7} {'title':>7}  "
          f"{'one row':<10} {'past 5,000':<10} {'collections':<11}  shop")
    for result in results:
        print(
            f"{result['showable']:>9,}  {result['robots']:<10} {result['catalogue'][:12]:<12} {result['type']:>7} "
            f"{result['kind']:>7} {result['title_kind']:>7}  {result['product'][:10]:<10} {result['past'][:10]:<10} "
            f"{result['collections'][:11]:<11}  {result['shop']}"
        )
    rows = sum(result["showable"] for result in results)
    open_ = [result for result in results if result["open"]]
    typed = [result for result in open_ if result["typed"]]
    print()
    print(
        f"in all: {len(results)} shops, {rows:,} rows a search could show but for a category; "
        f"a catalogue answered for {len(open_)} shops ({sum(r['showable'] for r in open_):,} rows); "
        f"a type on at least 80% of its first page for {len(typed)} shops ({sum(r['showable'] for r in typed):,} rows); "
        f"requests {sum(result['asked'] for result in results)}"
    )


def main(argv: list[str] | None = None, *, fetch: Fetch = fetch, sleep: Callable[[float], None] = time.sleep,
         clock: Callable[[], float] = time.monotonic) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--note", default=NOTE)
    parser.add_argument("--cache-dir", default=CACHE_DIR)
    parser.add_argument("--scheme", default="https")
    parser.add_argument("--pause", type=float, default=PAUSE)
    parser.add_argument("--large-shop", type=int, default=LARGE_SHOP)
    parser.add_argument("--budget", type=float, default=BUDGET, help="minutes")
    args = parser.parse_args(argv)
    started = clock()
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    from picwise_nlu.concept_understanding import annotate_product_concepts

    try:
        shops = shops_from_note(args.note)
    except (OSError, ValueError, KeyError) as error:
        print(f"no note to read the shops from: {type(error).__name__}")
        return 1
    copy = feed_copy(args.cache_dir)
    if copy is None:
        print("no copy of the feed in the download cache")
        return 1
    written = datetime.fromtimestamp(os.path.getmtime(copy), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    read = read_feed(copy, shops)
    print(
        f"the feed's copy of {written}, {os.path.getsize(copy) / 1e6:,.0f} MB: {read:,} rows read; "
        f"{len(shops)} shops with rows a search could show but for a category, "
        f"{sum(shop.showable for shop in shops.values()):,} such rows"
    )
    print(f"asked as {USER_AGENT}, {args.pause:g} s apart or a shop's crawl-delay")
    print()
    results = []
    for shop in shops.values():
        if clock() - started >= args.budget * 60:
            print(f"== {shop.name}: not asked, out of time")
            results.append({"shop": shop.name, "showable": shop.showable, "robots": "no time", "catalogue": "-",
                            "type": "-", "kind": "-", "title_kind": "-", "product": "-", "past": "-",
                            "collections": "-", "asked": 0, "open": False, "typed": False})
            continue
        results.append(ask_shop(shop, scheme=args.scheme, pause=args.pause, large_shop=args.large_shop,
                                fetch=fetch, sleep=sleep, read=annotate_product_concepts))
    print_table(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
