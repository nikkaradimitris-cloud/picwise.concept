"""An hour's look at the first cards of common searches: where each card's button leads,
whether its price is the shop's, whether its photo loads, and whose fault each failure is:
ours, Awin's or the shop's (owner, 2026-11-21: some buttons do not lead to the shop, some
prices differ from the shop's, some photos never load; task 2 of the work split by model:
«an hour's look, no scan ... the ids two shops share, counted»).

    ssh picwise 'sudo systemd-run ... /usr/bin/python3 - [--search tv ...]' < deployment/server/look_cards.py

Run once by .github/workflows/server-look-cards.yml, on the server, as the site's user, with
the release in use as its working directory and its code on PYTHONPATH. It changes nothing.

- The cards: each search asked of the site on the server itself, as a page is
  (`/search?q=`, no script, so no visitor's search is logged and nothing is sent to the
  AI), its first `CARDS` cards read: title, shop, price, photo, button.
- The button, never pressed: `/out/feed` finds a product by its id alone in an index of the
  prepared catalogue in which, of two products under one id, the last stands
  (`state.resolve_card_eligible_provider_feed_product_by_id`); the same index is built here
  from the same file, and the product it gives is checked as the site checks it at a click.
  Its link is read as text: an Awin link (`cread.php` with the shop's address in it, or
  `pclick.php` with none), never opened, and the shop's own address read from it, else
  from the row's `merchant_deep_link` (`shop_catalogue.own_address`).
- The shop's page: that address, asked once, only as its robots.txt allows, `PAUSE` seconds
  apart on one host: its status, and the product it describes (schema.org Product, else
  Shopify's JSON of it), the same product or not, in stock or not, at what price and in
  what currency, beside the card's. Never an Awin link; a redirect to another site is not
  followed (`shop_catalogue_test.fetch`).
- The photo: asked as a browser on the site's page asks it (with the site's address as
  Referer, the site's own policy), and again without one when that fails, so that a shop
  refusing other sites' pages (403) is told from a photo that is gone (404).
- The ids two shops share: over the whole prepared catalogue, the ids of two products or
  more, the products whose button leads to another product, by shop.

Prints per card a line, then the counts. Never an address but a host, never a link.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import parse_qs, quote, urlsplit

sys.path.insert(0, os.path.join(os.getcwd(), "deployment", "bot"))

import shop_catalogue_test as look  # noqa: E402  (the release's own: robots.txt, asking a shop)

SITE = "http://127.0.0.1:8016"
PREPARED = "/srv/picwise/shared/prepared/catalogue.json.gz"
# The owner's own searches of 20/11, from his phone's history (sent 21/11 15:29 Athens), then
# those of his plan of 21/11 that go wrong and are not among them.
SEARCHES = (
    "uhd monitor", "computer monitor", "workstation", "work pants", "work trousers", "cargo trousers",
    "card readers", "card printer", "car speakers", "car tyres", "Nike shoes", "sofa", "laptop", "perfume",
    "running shoes", "trainers", "dress", "maxi dress", "boots", "air fryer",
    "printer", "tablet", "drill", "mattress",
)
CARDS = 4
PAUSE = look.PAUSE
PHOTO_TIMEOUT = 10
SLOW_PHOTO = 5.0
SAME_TITLE = 0.6
SITE_ADDRESS = "https://picwise.subby.cloud/"
PHOTO_AGENT = "Mozilla/5.0 (compatible; PicWise-PhotoCheck/1.0; +https://picwise.subby.cloud)"
EXAMPLES = 6
_WORD = re.compile(r"[a-z0-9]+")
_ARTICLE = re.compile(r'<article class="pw-card[^"]*" data-choice-id="[^"]*">(.*?)</article>', re.DOTALL)
_JSON_LD = re.compile(r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL)
_IN_STOCK = ("instock", "limitedavailability", "onlineonly", "presale", "preorder", "backorder")


def _text(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def _first(pattern: str, block: str) -> str:
    match = re.search(pattern, block, re.DOTALL)
    return html.unescape(match.group(1)) if match else ""


def read_cards(page: str, limit: int = CARDS) -> list[dict[str, str]]:
    """The first cards of a search's page: title, shop, price, photo and the button's id."""
    cards = []
    for block in _ARTICLE.findall(page)[:limit]:
        href = _first(r'class="pw-card-cta pw-card-cta-link" href="([^"]*)"', block)
        query = parse_qs(urlsplit(href).query)
        cards.append({
            "title": _text(_first(r'<h2 title="([^"]*)" class="pw-card-title"', block)),
            "shop": _text(_first(r'<p class="pw-card-shop">(.*?)</p>', block)),
            "price": _text(_first(r'<p class="pw-price">(.*?)</p>', block)),
            "image": _first(r'<img class="pw-product-image" src="([^"]*)"', block),
            "pid": (query.get("pid") or [""])[0],
            "button": urlsplit(href).path,
        })
    return cards


def _pounds(value: Any) -> float | None:
    match = re.search(r"\d[\d,]*(?:\.\d+)?", str(value or ""))
    return float(match.group(0).replace(",", "")) if match else None


def _words(text: str) -> set[str]:
    return set(_WORD.findall(html.unescape(str(text or "")).lower()))


def title_share(card_title: str, shop_title: str) -> float:
    card = _words(card_title)
    return len(card & _words(shop_title)) / len(card) if card else 0.0


def _products_in(node: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(node, list):
        for item in node:
            yield from _products_in(item)
    elif isinstance(node, dict):
        kind = node.get("@type")
        if "Product" in (kind if isinstance(kind, list) else [kind]):
            yield node
        for key in ("@graph", "mainEntity"):
            if key in node:
                yield from _products_in(node[key])


def read_page(body: str) -> dict[str, Any] | None:
    """What a page's schema.org Product says: its name, price and currency, stock, barcodes."""
    for block in _JSON_LD.findall(body):
        data = None
        for text in (block.strip(), html.unescape(block.strip())):
            try:
                data = json.loads(text)
                break
            except ValueError:
                continue
        for product in _products_in(data):
            offers = product.get("offers")
            offers = offers if isinstance(offers, list) else [offers] if isinstance(offers, dict) else []
            offers = [offer for offer in offers if isinstance(offer, dict)]
            prices = [_pounds(offer.get("price", offer.get("lowPrice"))) for offer in offers]
            stock = [str(offer.get("availability") or "").rsplit("/", 1)[-1].lower() for offer in offers
                     if offer.get("availability")]
            return {
                "title": str(product.get("name") or ""),
                "price": min((price for price in prices if price is not None), default=None),
                "currency": next((str(offer.get("priceCurrency")) for offer in offers if offer.get("priceCurrency")), ""),
                "in_stock": any(word in _IN_STOCK for word in stock) if stock else None,
                "gtins": {re.sub(r"\D", "", str(product.get(key) or "")).lstrip("0")
                          for key in ("gtin", "gtin13", "gtin12", "gtin14", "gtin8")} - {""},
                "how": "schema.org",
            }
    return None


def read_shopify(data: Mapping[str, Any]) -> dict[str, Any]:
    """What Shopify's product JSON says (`/products/<name>.js`: prices in pence)."""
    variants = [variant for variant in data.get("variants") or () if isinstance(variant, dict)]
    prices = [variant["price"] for variant in variants if isinstance(variant.get("price"), (int, float))]
    return {
        "title": str(data.get("title") or ""),
        "price": min(prices) / 100 if prices else None,
        "currency": "",
        "in_stock": bool(data.get("available")) if "available" in data else any(v.get("available") for v in variants),
        "gtins": {re.sub(r"\D", "", str(v.get("barcode") or "")).lstrip("0") for v in variants} - {""},
        "how": "Shopify JSON",
    }


def link_kind(url: str) -> str:
    parts = urlsplit(str(url or ""))
    host = parts.netloc.lower()
    if "awin1.com" in host:
        if parts.path.endswith("cread.php"):
            return "Awin cread" if parse_qs(parts.query).get("ued") else "Awin cread, no address"
        return "Awin " + (parts.path.rsplit("/", 1)[-1] or "link")
    if parts.scheme in ("http", "https") and host:
        return "the shop's own link"
    return "not a link"


class Asker:
    """One request at a time per host, `pause` seconds apart; robots.txt for shops' pages."""

    def __init__(self, fetch: Callable[[str, int], Any], sleep: Callable[[float], None], clock: Callable[[], float],
                 pause: float = PAUSE) -> None:
        self.fetch, self.sleep, self.clock, self.pause = fetch, sleep, clock, pause
        self.last: dict[str, float] = {}
        self.robots: dict[str, tuple[list, float] | str] = {}
        self.requests = 0

    def _wait(self, host: str, wait: float) -> None:
        since = self.clock() - self.last.get(host, -1e9)
        if since < wait:
            self.sleep(wait - since)
        self.last[host] = self.clock()

    def page(self, url: str) -> Any:
        """The shop's answer, or a word why it was not asked."""
        parts = urlsplit(url)
        host = parts.netloc.lower()
        base = f"{parts.scheme}://{parts.netloc}"
        rules = self.robots.get(host)
        if rules is None:
            self._wait(host, self.pause)
            self.requests += 1
            answer = self.fetch(f"{base}/robots.txt", look.ROBOTS_BYTES)
            if answer.status == 200:
                found, delay = look.robots_rules(answer.body.decode("utf-8", "replace"))
                rules = (found, max(self.pause, delay or 0.0))
            elif answer.status in (404, 410):
                rules = ([], self.pause)
            else:
                rules = f"its robots.txt {look._said(answer)}"
            self.robots[host] = rules
        if isinstance(rules, str):
            return rules
        found, wait = rules
        path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        if wait > look.MAX_CRAWL_DELAY:
            return "its crawl-delay is too long"
        if not look.robots_allows(found, path):
            return "its robots.txt disallows the page"
        self._wait(host, wait)
        self.requests += 1
        return self.fetch(base + path, look.MAX_BYTES)


def photo(url: str, *, referer: str | None, opener: Callable[..., Any] = urllib.request.urlopen,
          clock: Callable[[], float] = time.monotonic) -> tuple[int, str, int, float]:
    """A photo asked as a browser asks it: status (0 for no answer), its type, its bytes
    (the first 64 KB), the seconds it took; never through a proxy."""
    headers = {"User-Agent": PHOTO_AGENT, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}
    if referer:
        headers["Referer"] = referer
    started = clock()
    try:
        with opener(urllib.request.Request(url, headers=headers), timeout=PHOTO_TIMEOUT) as answer:
            body = answer.read(65536)
            return answer.status, answer.headers.get("Content-Type", ""), len(body), clock() - started
    except urllib.error.HTTPError as error:
        return error.code, "", 0, clock() - started
    except (urllib.error.URLError, OSError, ValueError):
        return 0, "", 0, clock() - started


_PHOTO_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def photo_verdict(url: str, *, ask: Callable[..., tuple[int, str, int, float]]) -> str:
    if not url:
        return "no photo address"
    status, kind, size, seconds = ask(url, referer=SITE_ADDRESS)
    if status == 200 and kind.startswith("image/") and size:
        return f"loads ({kind.split(';')[0]}, {seconds:.1f} s)" + (" SLOW" if seconds > SLOW_PHOTO else "")
    again = ask(url, referer=None)
    alone = "loads without our address as Referer" if again[0] == 200 and again[1].startswith("image/") else ""
    said = (f"no answer in {PHOTO_TIMEOUT} s" if status == 0 else f"{status}"
            + (f", {kind.split(';')[0] or 'no type'}" if status == 200 else ""))
    return f"FAILS ({said})" + (f"; {alone}" if alone else "")


def shared_ids(products: Iterable[Any]) -> dict[str, Any]:
    """The ids two products or more share, as the site's index meets them: of each id the
    last product stands, so the buttons of the others lead to it."""
    from picwise_providers.normalization import extract_merchant_name

    by_id: dict[str, list] = defaultdict(list)
    for product in products:
        raw = product.raw if isinstance(product.raw, Mapping) else {}
        by_id[str(product.provider_product_id or "").strip()].append(
            (" ".join(str(extract_merchant_name(raw) or "").split()), " ".join(str(product.title or "").split())))
    shared = {pid: rows for pid, rows in by_id.items() if len(rows) > 1}
    pairs: Counter = Counter()
    examples = []
    for pid, rows in shared.items():
        winner = rows[-1]
        for shop, title in rows[:-1]:
            pairs[(shop, winner[0])] += 1
            if len(examples) < EXAMPLES and shop != winner[0]:
                examples.append(f"{shop}: {title[:50]} -> {winner[0]}: {winner[1][:50]}")
    return {
        "ids": len(shared),
        "ids_of_two_shops": sum(1 for rows in shared.values() if len({shop for shop, _title in rows}) > 1),
        "products_led_elsewhere": sum(len(rows) - 1 for rows in shared.values()),
        "of_another_shop": sum(1 for rows in shared.values() for shop, _t in rows[:-1] if shop != rows[-1][0]),
        "pairs": pairs.most_common(10),
        "examples": examples,
    }


def look_at_card(card: Mapping[str, str], by_id: Mapping[str, list], prepared: Any, asker: Asker,
                 ask_photo: Callable[..., tuple[int, str, int, float]]) -> dict[str, tuple[str, str]]:
    """What a card's button, shop's page, price and photo give: for each, a few words and
    the class they are counted under."""
    from picwise_providers.eligibility import evaluate_provider_product_eligibility
    from picwise_providers.normalization import extract_merchant_name
    from picwise_providers.offer_health import evaluate_product_eligibility
    from picwise_providers.shop_catalogue import own_address

    def shop_of(product: Any) -> str:
        raw = product.raw if isinstance(product.raw, Mapping) else {}
        return " ".join(str(extract_merchant_name(raw) or "").split())

    found: dict[str, tuple[str, str]] = {}
    candidates = by_id.get(card["pid"].strip()) or []
    if not candidates:
        found["button"] = ("FAILS: no product under its id (\"no longer available\")", "no product under its id")
        return found
    # The card's own product: of those under its id, the one its title and shop name.
    own = max(candidates, key=lambda product: (title_share(card["title"], str(product.title or "")),
                                               bool(shop_of(product)) and shop_of(product) in card["shop"]))
    # The site's index keeps the last product of an id (`resolve_card_eligible_...`).
    product = candidates[-1]
    if product is not own:
        found["button"] = (f"FAILS: leads to another product, {shop_of(product)}: "
                           f"{' '.join(str(product.title or '').split())[:60]} (its id shared)", "leads to another product")
    elif evaluate_provider_product_eligibility(product).status != "eligible" or not evaluate_product_eligibility(
            product, feed_ctx=prepared.availability_context).card_eligible:
        found["button"] = ("FAILS: the product no longer passes (\"no longer available\")", "no longer passes")
    else:
        kind = link_kind(product.product_url)
        found["button"] = (f"leads to its product ({kind})", f"leads to its product, {kind}")
    raw = own.raw if isinstance(own.raw, Mapping) else {}
    address = own_address(own.product_url, raw)
    said = None
    if not address:
        found["page"] = ("no address of the shop's own in its link or row", "no address")
    else:
        answer = asker.page(address)
        if isinstance(answer, str):
            found["page"] = (f"not asked: {answer}", "not asked")
        elif answer.status != 200 or answer.error:
            found["page"] = (f"FAILS: {look._said(answer)}", f"FAILS {answer.status or 'no answer'}")
        else:
            said = read_page(answer.body.decode("utf-8", "replace"))
            parts = urlsplit(address)
            name = next((part for part in reversed(parts.path.split("/")) if part), "")
            if said is None and "/products/" in parts.path:
                again = asker.page(f"{parts.scheme}://{parts.netloc}/products/{quote(name, safe='')}.js")
                data = look._json(again) if not isinstance(again, str) else None
                said = read_shopify(data) if isinstance(data, dict) else None
            if said is None:
                found["page"] = ("200, no product read on it", "200, no product read")
    if said is not None:
        share = title_share(card["title"], said["title"])
        same = share >= SAME_TITLE
        stock = {True: "in stock", False: "SOLD OUT", None: "stock not said"}[said["in_stock"]]
        found["page"] = (f"200 ({said['how']}), {'the same product' if same else 'ANOTHER product?'} "
                         f"(title {share:.0%} alike), {stock}",
                         f"200, {'the same product' if same else 'another product?'}, {stock.lower()}")
        shop_price, card_price = said["price"], _pounds(card["price"])
        currency = said["currency"] if said["currency"] and said["currency"] != "GBP" else ""
        if shop_price is None or card_price is None:
            found["price"] = ("not said by the shop", "not said")
        elif abs(shop_price - card_price) < 0.01:
            found["price"] = (f"the same ({card['price']})", "the same")
        else:
            found["price"] = (f"DIFFERS: the card {card['price']}, the shop {shop_price:,.2f}"
                              f"{' ' + currency if currency else ''} ({(shop_price / card_price - 1) * 100:+.0f}%)",
                              "differs" + (f" ({currency})" if currency else ""))
    verdict = photo_verdict(card["image"], ask=ask_photo)
    found["photo"] = (verdict, "loads" + (" slow" if verdict.endswith("SLOW") else "") if verdict.startswith("loads")
                      else verdict.split(";")[0])
    return found


def _get(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "PicWise look at its own cards"})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=60) as answer:
        return answer.read().decode("utf-8", "replace")


def main(argv: list[str] | None = None, *, get: Callable[[str], str] = _get, fetch=look.fetch,
         sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic,
         ask_photo: Callable[..., tuple[int, str, int, float]] | None = None, prepared: Any = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--search", action="append", help="a search (again for more); the common ones by default")
    parser.add_argument("--prepared", default=PREPARED)
    parser.add_argument("--site", default=SITE)
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    if prepared is None:
        from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure

        prepared = read_prepared_catalogue_to_measure(Path(args.prepared))
        if prepared is None:
            print("the prepared catalogue could not be read")
            return 1
    # Every product under each id, in the catalogue's order: the site's index keeps the last
    # (`state.resolve_card_eligible_provider_feed_product_by_id`).
    by_id: dict[str, list] = defaultdict(list)
    for product in prepared.products:
        by_id[str(product.provider_product_id or "").strip()].append(product)
    print(f"the prepared catalogue of {prepared.prepared_at:%Y-%m-%d %H:%M} UTC: {len(prepared.products):,} products, "
          f"{len(by_id):,} ids")
    shared = shared_ids(prepared.products)
    print(f"ids two products or more share: {shared['ids']:,} ({shared['ids_of_two_shops']:,} of two shops or more); "
          f"products whose button leads to another product: {shared['products_led_elsewhere']:,} "
          f"({shared['of_another_shop']:,} to another shop's)")
    for (shop, winner), count in shared["pairs"]:
        print(f"   {count:>7,}  {shop} -> {winner}")
    for example in shared["examples"]:
        print(f"   e.g. {example}")
    asker = Asker(fetch, sleep, clock)
    asking = ask_photo or (lambda url, referer: photo(url, referer=referer, opener=_PHOTO_OPENER.open))
    tally: dict[str, Counter] = {"button": Counter(), "page": Counter(), "price": Counter(), "photo": Counter()}
    by_shop: dict[str, Counter] = defaultdict(Counter)
    cards_seen = 0
    for search in args.search or SEARCHES:
        try:
            page = get(f"{args.site}/search?q={quote(search)}")
        except (OSError, ValueError) as error:
            print(f"== {search}: the site did not answer ({type(error).__name__})")
            continue
        cards = read_cards(page)
        print(f"== {search}: {len(cards)} cards")
        for number, card in enumerate(cards, start=1):
            cards_seen += 1
            found = look_at_card(card, by_id, prepared, asker, asking)
            print(f"  {number}. {card['shop'][:40]} | {card['title'][:60]} | {card['price']}")
            for part in ("button", "page", "price", "photo"):
                if part in found:
                    words, kind = found[part]
                    print(f"     {part}: {words}")
                    tally[part][kind] += 1
                    if words.startswith(("FAILS", "DIFFERS")) or "SOLD OUT" in words or "ANOTHER" in words:
                        by_shop[card["shop"]][part] += 1
    print()
    print(f"in all: {cards_seen} cards of {len(args.search or SEARCHES)} searches; {asker.requests} requests to shops")
    for part, counts in tally.items():
        print(f"  {part}: " + "; ".join(f"{word} {count}" for word, count in counts.most_common()))
    if by_shop:
        print("  the shops of the cards with a failure:")
        for shop, counts in sorted(by_shop.items(), key=lambda item: -sum(item[1].values())):
            print(f"    {shop}: " + ", ".join(f"{part} {count}" for part, count in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
