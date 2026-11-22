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

# The second look (22/11 04:10 Athens): the shops whose pages the checks still do not read,
# once a reCAPTCHA box no longer counted as a challenge.
SHOPS = ("Plusshop UK", "Bazta UK", "Luxe Mattress Affiliation", "Elixir Garden Supplies", "Pro-Camera")
PREPARED = "/srv/picwise/shared/prepared/catalogue.json.gz"
PAGES = 5
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
# A refusal dressed as a page: only what such a page writes (never a reCAPTCHA box or
# Cloudflare's script, which sit on ordinary pages too; those are counted as boxes).
INTERSTITIAL = {
    "Cloudflare challenge": rb"_cf_chl_opt|cf-chl-bypass|<title>Just a moment|Attention Required! \| Cloudflare",
    "PerimeterX block": rb"px-captcha",
    "Incapsula block": rb"Incapsula incident ID|_Incapsula_Resource\?CWUDNSAI",
    "DataDome block": rb"captcha-delivery\.com",
    "SiteGround captcha": rb"sgcaptcha",
    "Imunify360": rb"(?i)imunify360",
    "Sucuri": rb"(?i)sucuri",
    "Wordfence": rb"(?i)wordfence",
    "DDoS-Guard": rb"(?i)ddos-guard",
    "AWS WAF": rb"(?i)awswaf|aws-waf-token",
    "Akamai": rb"bm-verify|_abck",
    "Kasada": rb"KPSDK",
    "F5": rb"TSPD|/TSbd/",
    "BitNinja": rb"(?i)bitninja",
    "Queue-it": rb"(?i)queue-it",
    "Radware": rb"(?i)perfdrive|shieldsquare",
}
BOXES = {"reCAPTCHA box": rb"g-recaptcha|recaptcha/api\.js", "hCaptcha box": rb"hcaptcha",
         "Cloudflare's script": rb"/cdn-cgi/challenge-platform/"}
SCRIPT_ONLY = rb"(?i)enable javascript|javascript is (?:required|disabled)|<div id=[\"'](?:root|app|__next)[\"']>\s*</div>"
SHELLS = {
    "an empty app box": rb"(?i)<div\s+id=[\"']?(?:app|root|__nuxt|__next|main-app)[\"']?[^>]*>\s*</div>",
    "Vue": rb"(?i)data-v-app|__vue|vue(?:\.runtime)?(?:\.min)?\.js|chunk-vendors",
    "React": rb"(?i)data-reactroot|react-dom|__REACT",
    "Angular": rb"(?i)ng-version|ng-app",
    "webpack": rb"(?i)webpackJsonp|__webpack|/static/js/",
    "Vite": rb"(?i)/assets/index-[a-z0-9_-]+\.js|vite",
    "a framework's state": rb"__NEXT_DATA__|__NUXT__|__INITIAL_STATE__|__PRELOADED_STATE__|__APOLLO_STATE__",
}
API_HINTS = {"GraphQL": rb"(?i)graphql", "an /api/ path": rb"[\"'`]/api/", "an API's address": rb"(?i)api_?url|apibase|baseurl|api_host"}
TITLE = re.compile(rb"<title[^>]*>(.*?)</title\s*>", re.I | re.S)
TITLE_KINDS = (("says not found", rb"(?i)\b404\b|not found|no longer|unavailable|does ?n[o']t exist|oops|\berror\b"),
               ("says a check", rb"(?i)just a moment|attention required|checking|verif|access denied|forbidden|blocked|captcha|security|robot"))
PAGE_TYPE = re.compile(rb"[\"'](?:pageType|page_type|pagetype|pageCategory|ecomm_pagetype|template)[\"']\s*:\s*[\"']([A-Za-z0-9_ .-]{1,30})[\"']")
PAGE_TYPES = {"product", "productpage", "product_page", "product-page", "pdp", "item", "product.liquid", "404",
              "error", "notfound", "not_found", "page not found", "category", "collection", "home", "homepage",
              "search", "searchresults", "cart", "other"}
CANONICAL = re.compile(rb"<link\b[^>]*rel\s*=\s*[\"']?canonical[\"']?[^>]*>", re.I)
HREF = re.compile(rb"href\s*=\s*[\"']([^\"']+)[\"']", re.I)
SCRIPTS = re.compile(rb"<script\b", re.I)
SCRIPT_FILES = re.compile(rb"<script\b[^>]*\bsrc\s*=", re.I)
NOINDEX = re.compile(rb"<meta\b[^>]*name\s*=\s*[\"']?robots[\"']?[^>]*noindex", re.I)
MAGENTO = {"data-price-amount": rb"data-price-amount\s*=", "finalPrice": rb"data-price-type\s*=\s*[\"']finalPrice",
           "a price box": rb"data-price-box\s*=\s*[\"']?product-id-", "priceConfig with prices": rb"\"priceConfig\"[^<]{0,400}\"prices\""}
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


def visible_text(body: bytes) -> int:
    """The size of the words a reader sees without running the page's script."""
    text = re.sub(rb"(?is)<(script|style|noscript|template|svg)\b.*?</\1\s*>", b" ", body)
    text = re.sub(rb"(?s)<!--.*?-->", b" ", text)
    text = re.sub(rb"(?s)<[^>]+>", b" ", text)
    return len(re.sub(rb"\s+", b" ", text).strip())


def title_kind(body: bytes) -> str:
    found = TITLE.search(body)
    if not found:
        return "none"
    words = len(found.group(1).split())
    for kind, pattern in TITLE_KINDS:
        if re.search(pattern, found.group(1)):
            return f"{kind} ({words} words)"
    return f"other ({words} words)"


def where_moved(asked: str, final: str) -> str:
    path = urlsplit(final).path.rstrip("/")
    if not path:
        return "to the home page"
    if re.search(r"(?i)search|catalogsearch|/collections?/|/category|/c/", path):
        return "to a list or a search"
    return "to another page" if path != urlsplit(asked).path.rstrip("/") else "to the same page"


def deeper(body: bytes, asked: str) -> list[str]:
    """The second look's signs: kinds and counts only."""
    lines = []
    walls = [name for name, pattern in INTERSTITIAL.items() if re.search(pattern, body)]
    boxes = [name for name, pattern in BOXES.items() if re.search(pattern, body)]
    lines.append(f"title: {title_kind(body)}; words seen without script {visible_text(body):,}; "
                 f"scripts {len(SCRIPTS.findall(body))} (from files {len(SCRIPT_FILES.findall(body))})"
                 + (f"; noindex" if NOINDEX.search(body) else ""))
    canonical = CANONICAL.search(body)
    if canonical:
        href = HREF.search(canonical.group(0))
        same = bool(href) and urlsplit(href.group(1).decode("utf-8", "replace")).path.rstrip("/") == urlsplit(asked).path.rstrip("/")
        lines.append("canonical: " + ("its own address" if same else "another address"))
    else:
        lines.append("canonical: none")
    kinds = sorted({value.decode("ascii", "replace").strip().lower() for value in PAGE_TYPE.findall(body)})
    if kinds:
        lines.append("page type in its data: " + ", ".join(kind if kind in PAGE_TYPES else "other" for kind in kinds))
    shells = [name for name, pattern in SHELLS.items() if re.search(pattern, body)]
    hints = [name for name, pattern in API_HINTS.items() if re.search(pattern, body)]
    magento = [f"{name} {len(re.findall(pattern, body))}" for name, pattern in MAGENTO.items() if re.search(pattern, body)]
    lines.append("a refusal's signs: " + (", ".join(walls) or "none") + "; boxes: " + (", ".join(boxes) or "none"))
    lines.append("an app drawn by script: " + (", ".join(shells) or "-") + "; it asks: " + (", ".join(hints) or "-"))
    if magento:
        lines.append("Magento's price: " + ", ".join(magento))
    return lines


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
                 + ("; asks for script" if re.search(SCRIPT_ONLY, body) else ""))
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
                  + (f"; moved {where_moved(address, final)}" if moved else ""))
            for line in describe(body) + deeper(body, address):
                print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
