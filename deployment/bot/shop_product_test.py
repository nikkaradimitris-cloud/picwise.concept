"""One look at whether a shop the nightly bot never asks answers for its products one at a
time (owner, 2026-11-21, of InStock UK: about 100,000 products, a quarter of the
catalogue, never asked by the bot since 2026-10-26, when its catalogue answered 500; his
plan of that day, a shop that does not accept the bot goes out; asked whether to try a few
first: «Πρώτα δοκιμή σε λίγα»).

    ssh picwise 'sudo systemd-run ... /usr/bin/python3 - --shop "InStock UK"' < deployment/bot/shop_product_test.py

Run once by .github/workflows/server-product-test.yml, on the server, as the site's user,
with the site's code on PYTHONPATH and the release in use as its working directory. It reads
the feed's copies the preparation downloaded (`shop_catalogue_test.feed_copies`, no key
needed) for the shop's rows, takes `SAMPLE` products spread over them, each in stock by the
feed and of its own address, and asks the shop, one request at a time, `PAUSE` seconds apart
or its crawl-delay when longer, only what its robots.txt allows: its robots.txt, the first
page of its Shopify catalogue (`/products.json?limit=1`), and for each product its own page
as Shopify's JSON (`/products/<name>.js`) where its address names one, else, or when that
is no JSON, the page itself, read for a schema.org Product (JSON-LD). Only the shop's own
address, read as text from the feed, is asked: never an Awin link, and a redirect to
another site is not followed (`shop_catalogue_test.fetch`).

For each product it prints what the answer said: its status, whether it is the same
product (the barcode, else the share of the feed title's words in the shop's), and the
stock and the price as the shop says them beside the feed's. Then the counts. Never an
address but the shop's host, never a product's name. Changes nothing.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import quote, urlsplit

sys.path.insert(0, os.path.join(os.getcwd(), "deployment", "bot"))

import shop_catalogue_test as look  # noqa: E402

SHOP = "InStock UK"
SAMPLE = 12
PAUSE = look.PAUSE
# A shop's own title holding this share of the feed title's words is taken for the same product.
SAME_TITLE = 0.6
_WORD = re.compile(r"[a-z0-9]+")
_JSON_LD = re.compile(r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL)
_IN_STOCK = ("instock", "in stock", "in_stock", "limitedavailability", "onlineonly", "presale", "preorder")

Fetch = Callable[[str, int], "look.Answer"]


@dataclass
class Row:
    title: str
    address: str
    price: str
    sale_price: str
    availability: str
    gtin: str


def own_address(product_url: str, raw: Mapping[str, Any]) -> str:
    """The shop's own address of a row: its link's, else its `merchant_deep_link`, as the
    bot reads it (`shop_catalogue.own_address`, written here too, so that this look needs
    no more than the release in use)."""
    from picwise_providers.feed_intake import _shop_address

    address = _shop_address(product_url)
    if address:
        return address
    own = _shop_address(str(raw.get("merchant_deep_link") or ""))
    parts = urlsplit(own)
    return own if parts.scheme.lower() in ("http", "https") and parts.netloc else ""


def _gtin(raw: Mapping[str, Any]) -> str:
    for column in ("gtin", "ean", "product_GTIN", "upc", "isbn"):
        digits = re.sub(r"\D", "", str(raw.get(column) or ""))
        if len(digits) >= 8:
            return digits.lstrip("0")
    return ""


def shop_rows(paths: Iterable[str], shop: str) -> list[Row]:
    """The shop's rows in the feed's copies, in stock by the feed, each of its own address."""
    from picwise_providers.normalization import extract_merchant_name, normalize_feed_row_to_provider_product

    wanted = " ".join(shop.split()).casefold()
    rows: list[Row] = []
    seen: set[str] = set()
    for path in paths:
        for encoding in ("utf-8-sig", "latin-1"):
            found: list[Row] = []
            try:
                for raw in look._rows(path, encoding):
                    if " ".join(str(extract_merchant_name(raw) or "").split()).casefold() != wanted:
                        continue
                    product = normalize_feed_row_to_provider_product(raw, provider_key="awin")
                    if product is None:
                        continue
                    stock = " ".join(str(product.availability_text or "").lower().replace("_", " ").split())
                    if stock not in ("in stock", "1", "yes", "true", "available"):
                        continue
                    address = own_address(product.product_url, raw)
                    if not address:
                        continue
                    found.append(Row(" ".join(str(product.title or "").split()), address, str(product.price_text or ""),
                                     str(raw.get("sale_price") or ""), stock, _gtin(raw)))
            except UnicodeDecodeError:
                continue
            for row in found:
                if row.address not in seen:
                    seen.add(row.address)
                    rows.append(row)
            break
    return rows


def spread(rows: list[Row], count: int) -> list[Row]:
    """`count` rows spread evenly over the shop's rows, the first and the last among them."""
    if len(rows) <= count:
        return list(rows)
    step = (len(rows) - 1) / (count - 1)
    return [rows[round(index * step)] for index in range(count)]


def _words(text: str) -> set[str]:
    return set(_WORD.findall(html.unescape(text).lower()))


def title_share(feed_title: str, shop_title: str) -> float:
    """The share of the feed title's words the shop's title holds."""
    feed = _words(feed_title)
    return len(feed & _words(shop_title)) / len(feed) if feed else 0.0


def _pounds(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "").split()[0])
    except (ValueError, IndexError):
        return None


def read_shopify(data: Mapping[str, Any]) -> dict[str, Any]:
    """What Shopify's product JSON says: title, whether any variant can be bought, its
    lowest price in pounds (Shopify writes pence), the barcodes."""
    variants = [variant for variant in data.get("variants") or () if isinstance(variant, dict)]
    prices = [variant.get("price") for variant in variants if isinstance(variant.get("price"), (int, float))]
    if not prices and isinstance(data.get("price"), (int, float)):
        prices = [data["price"]]
    return {
        "title": str(data.get("title") or ""),
        "in_stock": bool(data.get("available")) if "available" in data else any(v.get("available") for v in variants),
        "price": min(prices) / 100 if prices else None,
        "gtins": {re.sub(r"\D", "", str(v.get("barcode") or "")).lstrip("0") for v in variants} - {""},
    }


def _products_in(node: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(node, list):
        for item in node:
            yield from _products_in(item)
    elif isinstance(node, dict):
        kind = node.get("@type")
        kinds = kind if isinstance(kind, list) else [kind]
        if "Product" in kinds:
            yield node
        for key in ("@graph", "mainEntity", "itemListElement"):
            if key in node:
                yield from _products_in(node[key])


def read_page(body: str) -> dict[str, Any] | None:
    """What a page's schema.org Product says (JSON-LD), as `read_shopify`, or None."""
    for block in _JSON_LD.findall(body):
        data = None
        # A script's text is read as it stands; a page that escaped it is read unescaped.
        for text in (block.strip(), html.unescape(block.strip())):
            try:
                data = json.loads(text)
                break
            except ValueError:
                continue
        if data is None:
            continue
        for product in _products_in(data):
            offers = product.get("offers")
            offers = offers if isinstance(offers, list) else [offers] if isinstance(offers, dict) else []
            prices = [_pounds(offer.get("price", offer.get("lowPrice"))) for offer in offers if isinstance(offer, dict)]
            stock = [str(offer.get("availability") or "").rsplit("/", 1)[-1].lower() for offer in offers
                     if isinstance(offer, dict) and offer.get("availability")]
            gtins = {re.sub(r"\D", "", str(product.get(key) or "")).lstrip("0")
                     for key in ("gtin", "gtin13", "gtin12", "gtin14", "gtin8")} - {""}
            return {
                "title": str(product.get("name") or ""),
                "in_stock": any(word in _IN_STOCK for word in stock) if stock else None,
                "price": min((price for price in prices if price is not None), default=None),
                "gtins": gtins,
            }
    return None


def _product_path(address: str) -> tuple[str, str]:
    """The page's path with its query, and Shopify's JSON of it where the path names one."""
    parts = urlsplit(address)
    page = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    segments = [segment for segment in parts.path.split("/") if segment]
    for index in range(len(segments) - 2, -1, -1):
        if segments[index].lower() == "products":
            return page, "/products/" + quote(segments[index + 1], safe="") + ".js"
    return page, ""


def judge(row: Row, said: Mapping[str, Any]) -> dict[str, Any]:
    """The same product, the stock and the price, as the shop said them, beside the feed's."""
    share = title_share(row.title, str(said.get("title") or ""))
    by_code = bool(row.gtin and said.get("gtins")) and row.gtin in said["gtins"]
    feed_price = _pounds(row.sale_price) or _pounds(row.price)
    shop_price = said.get("price")
    return {
        "same": by_code or share >= SAME_TITLE,
        "how": "by barcode" if by_code else f"title {share:.0%} alike",
        "in_stock": said.get("in_stock"),
        "feed_price": feed_price,
        "shop_price": shop_price,
        "price_same": None if shop_price is None or feed_price is None else abs(shop_price - feed_price) < 0.01,
    }


def _money(value: float | None) -> str:
    return "not said" if value is None else f"£{value:,.2f}"


def ask_products(rows: list[Row], *, fetch: Fetch, sleep: Callable[[float], None], pause: float = PAUSE) -> dict[str, Any]:
    """Ask the shop for each row's product, as the module says; print each answer."""
    counts = {"asked": len(rows), "answered": 0, "same": 0, "in_stock": 0, "price_same": 0, "requests": 0,
              "refused": 0, "not_found": 0, "no_answer": 0, "unread": 0}
    if not rows:
        print("no row of the shop in stock with an address of its own: nothing asked")
        return counts
    hosts = {urlsplit(row.address).netloc.lower() for row in rows}
    host = max(hosts, key=lambda name: sum(urlsplit(row.address).netloc.lower() == name for row in rows))
    base = f"{urlsplit(rows[0].address).scheme or 'https'}://{host}"
    print(f"host: {host} ({len(hosts)} host{'s' if len(hosts) != 1 else ''} among the products asked)")
    if "awin" in host:
        print("its address is Awin's: nothing asked")
        return counts
    robots = fetch(f"{base}/robots.txt", look.ROBOTS_BYTES)
    counts["requests"] += 1
    if robots.status == 200:
        rules, delay = look.robots_rules(robots.body.decode("utf-8", "replace"))
    elif robots.status in (404, 410):
        rules, delay = [], None
    else:
        print(f"robots.txt: {look._said(robots)}: nothing else asked")
        counts["refused"] = len(rows)
        return counts
    wait = max(pause, delay or 0.0)
    print(f"robots.txt: {'read' if robots.status == 200 else robots.status}; crawl-delay: "
          f"{'none' if delay is None else f'{delay:g} s'}; asked {wait:g} s apart")
    if wait > look.MAX_CRAWL_DELAY:
        print(f"a crawl-delay over {look.MAX_CRAWL_DELAY:g} s: nothing else asked")
        return counts

    def ask(path: str) -> "look.Answer | None":
        if not look.robots_allows(rules, path):
            return None
        sleep(wait)
        counts["requests"] += 1
        return fetch(base + path, look.MAX_BYTES)

    catalogue = ask("/products.json?limit=1")
    print("the catalogue (/products.json): " + ("not asked, robots.txt disallows it" if catalogue is None else
          "answers" if isinstance(look._json(catalogue), dict) else look._said(catalogue)))
    for number, row in enumerate(rows, start=1):
        page, shopify = _product_path(row.address)
        if urlsplit(row.address).netloc.lower() != host:
            print(f"== product {number}: on another host, not asked")
            continue
        said, how, last = None, "", None
        if shopify:
            answer = ask(shopify)
            last = answer
            data = look._json(answer) if answer is not None else None
            if isinstance(data, dict) and ("variants" in data or "title" in data):
                said, how = read_shopify(data), "Shopify JSON"
        if said is None:
            answer = ask(page)
            last = answer if answer is not None else last
            if answer is not None and answer.status == 200 and not answer.error:
                said = read_page(answer.body.decode("utf-8", "replace"))
                how = "its page's JSON-LD" if said is not None else ""
        if said is None:
            if last is None:
                verdict = "not asked, robots.txt disallows it"
                counts["refused"] += 1
            elif last.status in (401, 403, 429, 503):
                verdict = f"refused ({last.status})"
                counts["refused"] += 1
            elif last.status in (404, 410):
                verdict = f"not found ({last.status})"
                counts["not_found"] += 1
            elif last.status == 0:
                verdict = look._said(last)
                counts["no_answer"] += 1
            else:
                verdict = f"{look._said(last)}, no product read on it"
                counts["unread"] += 1
            print(f"== product {number}: {verdict}")
            continue
        counts["answered"] += 1
        found = judge(row, said)
        counts["same"] += found["same"]
        counts["in_stock"] += found["in_stock"] is True
        counts["price_same"] += found["price_same"] is True
        stock = {True: "in stock", False: "sold out", None: "not said"}[found["in_stock"]]
        print(
            f"== product {number}: {how}; the same product: {'yes' if found['same'] else 'no'} ({found['how']}); "
            f"the shop: {stock}, {_money(found['shop_price'])}; the feed: in stock, {_money(found['feed_price'])}"
            + ("" if found["price_same"] is None else "; price " + ("the same" if found["price_same"] else "differs"))
        )
    print(
        f"in all: {counts['asked']} products, {counts['requests']} requests; answered {counts['answered']} "
        f"(the same product {counts['same']}, in stock by the shop {counts['in_stock']}, the feed's price "
        f"{counts['price_same']}); refused {counts['refused']}, not found {counts['not_found']}, "
        f"no answer {counts['no_answer']}, no product read {counts['unread']}"
    )
    return counts


def main(argv: list[str] | None = None, *, fetch: Fetch = look.fetch, sleep: Callable[[float], None] = time.sleep) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--shop", default=SHOP)
    parser.add_argument("--sample", type=int, default=SAMPLE)
    parser.add_argument("--cache-dir", default=look.CACHE_DIR)
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    copies = look.feed_copies(args.cache_dir)
    if not copies:
        print("no copy of the feed in the download cache")
        return 1
    rows = shop_rows(copies, args.shop)
    print(f"{args.shop}: {len(rows):,} products in stock by the feed with an address of their own, in "
          f"{len(copies)} copies of the feed; {min(args.sample, len(rows))} asked, spread over them, as {look.USER_AGENT}")
    ask_products(spread(rows, max(1, args.sample)), fetch=fetch, sleep=sleep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
