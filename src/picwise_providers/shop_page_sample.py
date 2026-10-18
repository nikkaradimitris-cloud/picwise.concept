"""Whether the products a feed lists can really be bought: a sample, checked on each
shop's own pages. Measured, not yet a rule.

Owner, 2026-10-18: most products the live site shows are out of stock on the shop's
page ("we show ghosts"), and the feed cannot tell them apart -- no shop sends a listing
date or says "out of stock" (`feed_freshness`). The one place the truth is written is
the shop's product page, so the deployment's build checks a sample there: up to N
products per shop, half its cheapest (price first shows those first) and half drawn at
random, and writes the counts into its public note (`tools/prepare_catalogue.py
--sample-shop-pages N`). The owner's question it answers: is it one shop, or all?

How a page is read, strongest evidence first:

- the page's structured data, which shops write for search engines: schema.org
  `availability` (JSON-LD or microdata) or `product:availability`;
- the HTTP answer: 404 or 410 is a page that is gone, a redirect to a home, category
  or search page is a product that is gone, 403 or 429 or a bot challenge is a page
  that could not be checked;
- with neither, the words on the page (`purchasability_verifier`), reported apart,
  since a related-products strip can say "out of stock" about something else.

Two things it never does. It never opens the Awin link (`aw_deep_link`): that is a
tracked click, and an automated one would be a fake click on the owner's account; it
opens the shop's own link (`merchant_deep_link`) or nothing. And it asks each shop's
`robots.txt` first, opening nothing the shop asks robots not to open.
"""
from __future__ import annotations

import json
import random
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from .contracts import ProviderProduct
from .decision_labels import parse_price_amount
from .normalization import extract_merchant_name, is_valid_http_url
from .purchasability_verifier import (
    DEFAULT_USER_AGENT,
    analyze_product_page_content,
    html_to_visible_text,
    is_redirect_suspect,
)

# What a check found. Shown to the owner in this order.
OUTCOMES = (
    "in_stock", "out_of_stock", "gone", "redirected", "preorder",
    "text_buyable", "text_out_of_stock", "unclear", "blocked", "unreachable",
    "robots_disallowed", "no_direct_link",
)
_IN_STOCK = {"instock", "limitedavailability", "onlineonly", "instoreonly", "in stock", "available"}
_OUT_OF_STOCK = {"outofstock", "soldout", "discontinued", "out of stock", "sold out", "oos"}
_PREORDER = {"preorder", "presale", "backorder", "pre-order", "available for order"}
_LD_JSON_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.IGNORECASE | re.DOTALL
)
_ITEMPROP_RE = re.compile(
    r'itemprop=["\']availability["\'][^>]*?(?:href|content)=["\']([^"\']+)["\']'
    r'|(?:href|content)=["\']([^"\']+)["\'][^>]*?itemprop=["\']availability["\']',
    re.IGNORECASE,
)
_META_AVAILABILITY_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](?:product|og):availability["\'][^>]*content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_BOT_CHALLENGE = ("just a moment", "attention required", "captcha", "are you a robot", "access denied")
_TRACKING_HOSTS = ("awin1.com", "awin.com", "awclick")

# (body, http status or None, final url) for a url; raises on a network failure.
Fetch = Callable[[str], tuple[str, "int | None", str]]


def direct_shop_url(product: ProviderProduct) -> str:
    """The shop's own link to the product, never the Awin tracked one; "" when none."""
    raw = product.raw if isinstance(product.raw, Mapping) else {}
    for key in ("merchant_deep_link", "merchant_url"):
        url = str(raw.get(key) or "").strip()
        if url and is_valid_http_url(url):
            host = (urlparse(url).netloc or "").lower()
            if not any(tracking in host for tracking in _TRACKING_HOSTS):
                return url
    return ""


def _availability_words(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value.rstrip("/").rsplit("/", 1)[-1].strip().lower()
    elif isinstance(value, list):
        for item in value:
            yield from _availability_words(item)


def _walk_ld(node: Any) -> Iterable[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "availability":
                yield from _availability_words(value)
            else:
                yield from _walk_ld(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_ld(item)


def page_availability(html: str) -> str:
    """What the page's structured data says: "in_stock", "out_of_stock", "preorder" or "".

    A page selling a product in several variants is in stock when any variant is.
    """
    words: list[str] = []
    for block in _LD_JSON_RE.findall(html):
        try:
            words.extend(_walk_ld(json.loads(block.strip())))
        except ValueError:
            continue
    for first, second in _ITEMPROP_RE.findall(html):
        words.extend(_availability_words(first or second))
    for value in _META_AVAILABILITY_RE.findall(html):
        words.append(" ".join(value.lower().split()))
    found = set(words)
    if found & _IN_STOCK:
        return "in_stock"
    if found & _OUT_OF_STOCK:
        return "out_of_stock"
    if found & _PREORDER:
        return "preorder"
    return ""


def classify_page(url: str, body: str, status: int | None, final_url: str) -> str:
    """One of `OUTCOMES` for a fetched page."""
    code = status or 0
    if code in (404, 410):
        return "gone"
    if code in (401, 403, 429) or (code >= 400 and any(word in body.lower() for word in _BOT_CHALLENGE)):
        return "blocked"
    if code < 200 or code >= 400:
        return "unreachable"
    if is_redirect_suspect(original_url=url, final_url=final_url):
        return "redirected"
    structured = page_availability(body)
    if structured:
        return structured
    if any(word in html_to_visible_text(body)[:2000] for word in _BOT_CHALLENGE):
        return "blocked"
    verdict = analyze_product_page_content(url=url, html=body, http_status=code, final_url=final_url)
    state = verdict.purchasability_state
    if state == "purchasable":
        return "text_buyable"
    if state in ("out_of_stock", "discontinued"):
        return "text_out_of_stock"
    return "unclear"


def choose_sample(
    products: Sequence[ProviderProduct], *, per_shop: int, seed: str
) -> dict[str, tuple[list[ProviderProduct], list[ProviderProduct]]]:
    """For each shop, (its cheapest, others drawn at random): `per_shop` in all at most,
    half of them the cheapest.

    The same `seed` (the day) draws the same sample, so two builds of a day agree.
    """
    by_shop: dict[str, list[ProviderProduct]] = {}
    for product in products:
        raw = product.raw if isinstance(product.raw, Mapping) else {}
        shop = " ".join(str(extract_merchant_name(raw) or "?").split())
        by_shop.setdefault(shop, []).append(product)
    chosen: dict[str, tuple[list[ProviderProduct], list[ProviderProduct]]] = {}
    for shop, items in sorted(by_shop.items()):
        order = sorted(
            range(len(items)),
            key=lambda index: (
                parse_price_amount(items[index].price_text) is None,
                parse_price_amount(items[index].price_text) or 0.0,
            ),
        )
        cheapest_at = order[: per_shop // 2]
        taken = set(cheapest_at)
        rest = [index for index in range(len(items)) if index not in taken]
        drawn_at = random.Random(f"{seed}:{shop}").sample(rest, min(len(rest), per_shop - len(cheapest_at)))
        chosen[shop] = ([items[index] for index in cheapest_at], [items[index] for index in drawn_at])
    return chosen


def _fetch_with_urllib(url: str, *, timeout: float = 12.0, max_bytes: int = 768_000) -> tuple[str, int | None, str]:
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen

    request = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "text/html,*/*;q=0.8"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(max_bytes)
            return body.decode("utf-8", errors="replace"), getattr(response, "status", None), response.geturl()
    except HTTPError as error:
        body = error.read(64_000).decode("utf-8", errors="replace") if error.fp else ""
        error.close()
        return body, error.code, url


def _robots_allow(url: str, fetch: Fetch, cache: dict[str, RobotFileParser | None]) -> bool:
    parts = urlparse(url)
    root = f"{parts.scheme}://{parts.netloc}"
    if root not in cache:
        try:
            body, status, _final = fetch(f"{root}/robots.txt")
            parser = RobotFileParser()
            parser.parse(body.splitlines() if status and 200 <= status < 300 else [])
            # As robots.txt is read by convention: a file refused to robots refuses all.
            parser.disallow_all = status in (401, 403)
            cache[root] = parser
        except Exception:
            cache[root] = None  # no robots.txt to read: nothing is asked of us
    parser = cache[root]
    return True if parser is None else parser.can_fetch(DEFAULT_USER_AGENT, url)


def _check_shop(
    sample: tuple[list[ProviderProduct], list[ProviderProduct]],
    *,
    fetch: Fetch,
    delay: float,
    deadline: float,
) -> tuple[Counter, Counter]:
    overall: Counter = Counter()
    cheapest: Counter = Counter()
    robots: dict[str, RobotFileParser | None] = {}
    cheapest_items, drawn_items = sample
    for position, product in enumerate([*cheapest_items, *drawn_items]):
        if time.monotonic() > deadline:
            break
        url = direct_shop_url(product)
        if not url:
            outcome = "no_direct_link"
        elif not _robots_allow(url, fetch, robots):
            outcome = "robots_disallowed"
        else:
            try:
                body, status, final_url = fetch(url)
                outcome = classify_page(url, body, status, final_url)
            except Exception:
                outcome = "unreachable"
            if delay:
                time.sleep(delay)
        overall[outcome] += 1
        if position < len(cheapest_items):
            cheapest[outcome] += 1
    return overall, cheapest


def check_shop_pages(
    products: Sequence[ProviderProduct],
    *,
    per_shop: int,
    seed: str,
    fetch: Fetch | None = None,
    delay: float = 0.3,
    time_budget_seconds: float = 300.0,
    workers: int = 12,
) -> dict[str, Any]:
    """Check a sample of each shop's products on the shop's own pages; counts only."""
    sample = choose_sample(products, per_shop=per_shop, seed=seed)
    fetcher = fetch or _fetch_with_urllib
    deadline = time.monotonic() + time_budget_seconds
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            shop: pool.submit(_check_shop, picked, fetch=fetcher, delay=delay, deadline=deadline)
            for shop, picked in sample.items()
        }
        results = {shop: future.result() for shop, future in futures.items()}
    totals: Counter = Counter()
    shops = []
    for shop, (overall, cheapest) in sorted(results.items(), key=lambda item: -sum(item[1][0].values())):
        totals.update(overall)
        shops.append(
            {
                "shop": shop,
                "checked": sum(overall.values()),
                **{outcome: overall[outcome] for outcome in OUTCOMES if overall[outcome]},
                "of_its_cheapest": {outcome: cheapest[outcome] for outcome in OUTCOMES if cheapest[outcome]},
            }
        )
    return {
        "per_shop": per_shop,
        "checked": sum(totals.values()),
        "totals": {outcome: totals[outcome] for outcome in OUTCOMES if totals[outcome]},
        "shops": shops,
    }
