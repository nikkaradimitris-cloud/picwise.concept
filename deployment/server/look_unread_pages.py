"""A look at why some shops' product pages are not read: what kind of product data each
page carries, never what it says (the checks' rules 4.5 and 5.6.2; owner, 2026-11-22:
a shop that cannot be checked leaves on its day 4, «Σε 3 μέρες»).

    ssh picwise 'sudo systemd-run ... /usr/bin/python3 - [--shop NAME ...]' < deployment/server/look_unread_pages.py

Run once by .github/workflows/server-look-unread.yml, on the server, as the site's user,
with the release in use as its working directory and its code on PYTHONPATH. It changes
nothing. For each shop named, 3 of its products the site shows: its robots.txt first, then
each product's own address (never an Awin link), one request at a time, 3 seconds apart,
under the checks' bot's name; a redirect to another site is not followed.

Printed for each page, as counts and kinds only (the log is public): its answer, its size,
whether it moved, the schema.org types of its JSON-LD, whether it carries microdata, product
tags, a data layer, a framework's state (`__NEXT_DATA__` and the like), the platform it
seems built on, and signs of a challenge or of a page drawn only by script. Never an
address, a product's name or a price.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, os.path.join(os.getcwd(), "deployment", "bot"))

import shop_catalogue_test as look  # noqa: E402  (the release's own: robots.txt, the bot's name)

SHOPS = ("Plusshop UK", "Bazta UK", "Luxe Mattress Affiliation", "Elixir Garden Supplies", "GamingKit",
         "Webbs Motorcycles", "Pro-Camera", "Dean Morris Cards")
PREPARED = "/srv/picwise/shared/prepared/catalogue.json.gz"
PAGES = 3
PAUSE = 3.0
BYTES = 4 * 1024 * 1024

MARKERS = {
    "itemprop": rb"itemprop\s*=",
    "itemtype Product": rb"itemtype\s*=\s*[\"']?https?://schema\.org/Product",
    "itemprop price": rb"itemprop\s*=\s*[\"']?price[\"' >]",
    "meta product:price": rb"(?:property|name)\s*=\s*[\"'](?:product|og):price:amount",
    "meta og:type product": rb"og:type[\"']\s+content\s*=\s*[\"']product",
    "dataLayer": rb"dataLayer",
    "ecommerce": rb"[\"']ecommerce[\"']\s*:",
    "view_item": rb"view_item",
    "__NEXT_DATA__": rb"__NEXT_DATA__",
    "__NUXT__": rb"__NUXT__",
    "__INITIAL_STATE__": rb"__INITIAL_STATE__|__PRELOADED_STATE__|__APOLLO_STATE__",
    "data-price": rb"data-(?:product-)?price",
    "data-product": rb"data-product(?:-id|_id|=)",
    "\"sku\"": rb"[\"']sku[\"']\s*:",
    "\"price\"": rb"[\"']price[\"']\s*:",
    "\"gtin": rb"[\"']gtin(?:8|12|13|14)?[\"']\s*:",
    "\"availability\"": rb"[\"']availability[\"']\s*:",
    "Add to basket/cart": rb"(?i)add\s+to\s+(?:basket|cart|bag)",
}
PLATFORMS = {
    "WooCommerce": rb"(?i)woocommerce",
    "Magento": rb"(?i)mage/|magento",
    "Shopify": rb"(?i)cdn\.shopify\.com|Shopify\.theme",
    "BigCommerce": rb"(?i)bigcommerce",
    "PrestaShop": rb"(?i)prestashop",
    "Shopware": rb"(?i)shopware",
    "Wix": rb"(?i)wixstatic|_wix",
    "Squarespace": rb"(?i)squarespace",
    "nopCommerce": rb"(?i)nopcommerce",
    "EKM": rb"(?i)ekmpowershop|ekm\.net",
    "OpenCart": rb"(?i)route=product/product|opencart",
    "Salesforce": rb"(?i)demandware|salesforce commerce",
    "Next.js": rb"/_next/static",
    "Nuxt": rb"/_nuxt/",
}
CHALLENGE = rb"(?i)cf-chl-|challenge-platform|just a moment\.\.\.|attention required|px-captcha|g-recaptcha|hcaptcha|_incapsula_|perimeterx|datadome"
SCRIPT_ONLY = rb"(?i)enable javascript|javascript is (?:required|disabled)|<div id=[\"'](?:root|app|__next)[\"']>\s*</div>"
JSON_LD = re.compile(rb"<script\b[^>]*application/ld\+json[^>]*>(.*?)</script\s*>", re.I | re.S)


class _Elsewhere(Exception):
    pass


class _SameSite(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        if look._site(urlsplit(newurl).netloc) != look._site(urlsplit(req.full_url).netloc):
            raise _Elsewhere()
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _SameSite())


def fetch(url: str) -> tuple[int, str, bytes, str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": look.USER_AGENT,
                                                   "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
                                                   "Accept-Language": "en-GB,en;q=0.8"})
    try:
        with OPENER.open(request, timeout=20) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read(BYTES), response.geturl(), ""
    except _Elsewhere:
        return 0, "", b"", "", "a redirect to another site"
    except urllib.error.HTTPError as error:
        try:
            body = error.read(256 * 1024)
        except OSError:
            body = b""
        return error.code, (error.headers or {}).get("Content-Type", ""), body, url, ""
    except (urllib.error.URLError, OSError, ValueError) as error:
        return 0, "", b"", "", type(getattr(error, "reason", error)).__name__


def types_of(node, found: set[str]) -> None:
    if isinstance(node, list):
        for item in node:
            types_of(item, found)
    elif isinstance(node, dict):
        kind = node.get("@type")
        for item in (kind if isinstance(kind, list) else [kind]):
            if item:
                found.add(str(item).rsplit("/", 1)[-1])
        for key, value in node.items():
            if key in ("@graph", "mainEntity", "hasVariant", "offers", "itemListElement", "item"):
                types_of(value, found)


def describe(body: bytes) -> list[str]:
    lines = []
    blocks = JSON_LD.findall(body)
    found: set[str] = set()
    broken = 0
    for block in blocks:
        try:
            types_of(json.loads(block.decode("utf-8", "replace"), strict=False), found)
        except ValueError:
            broken += 1
    lines.append(f"JSON-LD blocks {len(blocks)} (not JSON {broken}); types: {', '.join(sorted(found)) or '-'}")
    marks = [f"{name} {len(re.findall(pattern, body))}" for name, pattern in MARKERS.items() if re.search(pattern, body)]
    lines.append("marks: " + (", ".join(marks) or "-"))
    platforms = [name for name, pattern in PLATFORMS.items() if re.search(pattern, body)]
    lines.append("built on: " + (", ".join(platforms) or "-")
                 + ("; A CHALLENGE PAGE" if re.search(CHALLENGE, body) else "")
                 + ("; drawn by script only" if re.search(SCRIPT_ONLY, body) else ""))
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shop", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    from picwise_providers.catalogue_cap import shop_of
    from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure
    from picwise_providers.shop_catalogue import own_address

    wanted = tuple(args.shop) or SHOPS
    prepared = read_prepared_catalogue_to_measure(Path(PREPARED))
    picked: dict[str, list[str]] = {name: [] for name in wanted}
    for product in prepared.products:
        name = shop_of(product)
        if name in picked and len(picked[name]) < PAGES:
            address = own_address(product.product_url, product.raw if isinstance(product.raw, dict) else {})
            if address and "awin" not in urlsplit(address).netloc:
                picked[name].append(address)
    del prepared
    for name in wanted:
        addresses = picked[name]
        print(f"== {name}: {len(addresses)} products picked")
        if not addresses:
            continue
        host = urlsplit(addresses[0])
        status, kind, body, _final, error = fetch(f"{host.scheme}://{host.netloc}/robots.txt")
        rules, delay = look.robots_rules(body.decode("utf-8", "replace")) if status == 200 else ([], None)
        print(f"robots.txt: {status or error}; crawl-delay {delay}; "
              + ", ".join(f"page {n + 1} {'allowed' if look.robots_allows(rules, urlsplit(a).path or '/') else 'DISALLOWED'}"
                          for n, a in enumerate(addresses)))
        for number, address in enumerate(addresses, start=1):
            time.sleep(PAUSE)
            status, kind, body, final, error = fetch(address)
            moved = bool(final) and final.split("#")[0] != address.split("#")[0]
            print(f"page {number}: {status or error}; {kind.split(';')[0] or '-'}; {len(body):,} bytes"
                  + ("; moved within the site" if moved else ""))
            for line in describe(body):
                print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
