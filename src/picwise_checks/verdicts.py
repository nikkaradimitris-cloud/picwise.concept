"""What a shop's answer means: the verdicts of the rules' section 5, one function a table.

Every function here is code without a network (rules 14): the bot hands it what the
shop's site answered and the row of the feed it asked for, and it says `passed`,
`failed` with its reason, or `not checked`. Each row of the rules' tables is pinned by a
test named after its section (`tests/test_picwise_checks_verdicts.py`).

Two points the rules leave open are settled here, and recorded in PROGRESS.md (21/11):

- A redirect to another site is not followed (rules 4.1) and is `not checked`; it counts
  with the refusals for whether the shop can be checked (5.6.2).
- An answer the rules' table does not name (a 400, a 405, a redirect with no address) is
  `not checked`: never a cut on an answer nobody looked at. Such a product passes no
  check either, so once its shop's first round is over it is not shown (rules 9.3).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable
from urllib.parse import parse_qs, unquote, urlsplit

from .page_reader import NOTHING, Offer, PageRead, offers_in_pounds, stock_of, title_alike

PASSED = "passed"
FAILED = "failed"
NOT_CHECKED = "not checked"

# The reasons of a failure (the rules' tables).
GONE = "gone"
NO_ANSWER = "no answer"
MOVED = "moved"
NOT_A_PRODUCT_PAGE = "not a product page"
ANOTHER_PRODUCT = "another product"
ID_SHARED = "id shared"
PRICE_FAR_APART = "price far apart"
NOT_AN_IMAGE = "not an image"
EMPTY = "empty"
REFUSED = "refused"
OTHER_ANSWER = "other answer"
NO_CATEGORY = "no category"
SHOP_CANNOT_BE_CHECKED = "shop cannot be checked"

# Why a product was not checked.
ANOTHER_SITE = "another site"
NOT_READ = "no product read"
NOT_UNDERSTOOD = "answer not understood"
OUR_PACE = "our pace"

# How a product's page was known to be its own (rules 5.1, last point).
BY_VARIANT = "by variant id"
BY_CODE = "by code"
BY_ADDRESS = "by address"

# How a price reading is tied to its row (rules 5.3.1).
TIE_VARIANT = "variant id"
TIE_CODE = "code"
TIE_ONE_PRICE = "one price"

REFUSED_STATUSES = frozenset({401, 403, 429})
GONE_STATUSES = frozenset({404, 410})
# "At least 9 in 10" (rules 5.1, 5.4, 5.6.2) and the counts below which no share is read.
MOST = 0.9
PAGES_MIN = 10
PHOTOS_MIN = 20
MAX_CRAWL_DELAY = 60.0
# A tied price under half or over twice the feed's is no price (rules 7.5).
FAR_BELOW = 0.5
FAR_ABOVE = 2.0
# A feed last imported over 7 days ago is old (rules 5.6.4, Proposed).
FEED_OLD_DAYS = 7


@dataclass(frozen=True)
class Row:
    """What the checks know of one row of the feed."""

    key: str
    shop: str
    product_id: str
    address: str
    title: str = ""
    price: float | None = None
    currency: str = ""
    gtin: str = ""
    mpn: str = ""
    skus: frozenset[str] = field(default_factory=frozenset)
    handle: str = ""
    variant: str = ""
    photo: str = ""
    # The feed's own word on stock: "in stock", "sold out" or "" (for the proof of 7.5).
    feed_stock: str = ""


@dataclass(frozen=True)
class PageAnswer:
    """What the shop's site answered at a product's own address (or, in a Shopify shop
    whose catalogue was read whole that night, `in_catalogue` and the product read)."""

    status: int = 0
    error: str = ""
    final_url: str = ""
    redirected: bool = False
    elsewhere: bool = False
    challenge: bool = False
    read: PageRead = NOTHING
    in_catalogue: bool = False


@dataclass(frozen=True)
class Verdict:
    state: str
    reason: str = ""
    by: str = ""

    @property
    def decided(self) -> bool:
        return self.state in (PASSED, FAILED)


def _norm_code(value: str) -> str:
    return re.sub(r"[^0-9A-Z]", "", str(value or "").upper())


def address_parts(url: str) -> tuple[str, str]:
    """A site and a path to compare two addresses of one page by: no scheme, no "www.",
    no trailing slash, no case, the Shopify collection a product page is reached by left
    out ("/collections/x/products/y" is "/products/y")."""
    parts = urlsplit(str(url or "").strip())
    host = parts.netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    path = unquote(parts.path or "/").rstrip("/").lower() or "/"
    path = re.sub(r"^/collections/[^/]+(/products/)", r"\1", path)
    return host, path


def same_page(first: str, second: str) -> bool:
    return address_parts(first) == address_parts(second)


def variant_in(url: str) -> str:
    """The Shopify variant an address names (`?variant=<id>`), or ""."""
    values = parse_qs(urlsplit(str(url or "")).query).get("variant") or [""]
    return values[0].strip()


def codes_agree(row: Row, read: PageRead) -> bool | None:
    """True when a code of the row is on the page; False when the two sides give the
    same kind of code and none agrees (a GTIN, or a part number); None when there is
    nothing to compare. A shop's SKU proves an agreement, never a difference: the feed's
    column may hold another code of the same shop."""
    offers = read.offers
    variants = {offer.variant for offer in offers} - {""}
    if row.variant and row.variant in variants:
        return True
    page_gtins = set(read.gtins) | ({offer.gtin for offer in offers} - {""})
    if row.gtin and row.gtin in page_gtins:
        return True
    page_skus = {_norm_code(sku) for sku in set(read.skus) | {offer.sku for offer in offers}} - {""}
    if page_skus & ({_norm_code(sku) for sku in row.skus} - {""}):
        return True
    page_mpns = {_norm_code(mpn) for mpn in set(read.mpns) | {offer.mpn for offer in offers}} - {""}
    if row.mpn and _norm_code(row.mpn) in page_mpns:
        return True
    if row.gtin and page_gtins:
        return False
    if row.mpn and page_mpns:
        return False
    return None


def another_product(row: Row, read: PageRead) -> bool:
    """Rules 5.1: the page gives a GTIN for every one of its variants and the row's own
    valid GTIN is none of them."""
    if not row.gtin:
        return False
    variant_gtins = [offer.gtin for offer in read.offers] or sorted(read.gtins)
    return bool(variant_gtins) and all(variant_gtins) and row.gtin not in set(variant_gtins)


def _how_agreed(row: Row, read: PageRead) -> str:
    if row.variant and row.variant in {offer.variant for offer in read.offers}:
        return BY_VARIANT
    return BY_CODE if codes_agree(row, read) else BY_ADDRESS


def page_verdict(row: Row, answer: PageAnswer, *, shop_reads_pages: bool, shared_id: bool = False) -> Verdict:
    """The page (the button's far end), rules 5.1. `shop_reads_pages`: the shop's reader
    read a product on at least 9 in 10 of its other pages that answered 200 that night.
    A product with no answer is asked once more at the end of its shop's round by the
    bot; the answer given here is the last."""
    if shared_id:
        return Verdict(FAILED, ID_SHARED)
    read = answer.read or NOTHING
    if answer.in_catalogue:
        return Verdict(PASSED, by=BY_VARIANT if row.variant and _how_agreed(row, read) == BY_VARIANT else BY_ADDRESS)
    if answer.challenge or answer.status in REFUSED_STATUSES:
        return Verdict(NOT_CHECKED, REFUSED)
    if answer.elsewhere:
        return Verdict(NOT_CHECKED, ANOTHER_SITE)
    if answer.status in GONE_STATUSES:
        return Verdict(FAILED, GONE)
    if answer.status == 0 or 500 <= answer.status < 600:
        return Verdict(FAILED, NO_ANSWER)
    if answer.status != 200:
        return Verdict(NOT_CHECKED, NOT_UNDERSTOOD)
    if answer.redirected and answer.final_url and not same_page(row.address, answer.final_url):
        if not read.found:
            return Verdict(FAILED, MOVED)
        agreed = codes_agree(row, read)
        if agreed is True:
            return Verdict(PASSED, by=_how_agreed(row, read))
        if agreed is False or not title_alike(row.title, read.name):
            return Verdict(FAILED, MOVED)
        return Verdict(PASSED, by=BY_ADDRESS)
    if not read.found:
        return Verdict(FAILED, NOT_A_PRODUCT_PAGE) if shop_reads_pages else Verdict(NOT_CHECKED, NOT_READ)
    if another_product(row, read):
        return Verdict(FAILED, ANOTHER_PRODUCT)
    return Verdict(PASSED, by=_how_agreed(row, read))


def _one_price(offers: Iterable[Offer]) -> float | None:
    prices = {offer.price for offer in offers}
    return next(iter(prices)) if len(prices) == 1 and None not in prices else None


def tie(row: Row, read: PageRead, *, feed_rows_one_price: bool) -> tuple[Offer | None, str]:
    """The reading that belongs to the row, rules 5.3.1, and how it is tied; (None, "")
    when none is. `feed_rows_one_price`: the feed has one row for this address, or all
    its rows for it at one price."""
    offers = offers_in_pounds(read.offers)
    if not offers:
        return None, ""
    if row.variant:
        for offer in offers:
            if offer.variant and offer.variant == row.variant:
                return offer, TIE_VARIANT
    row_skus = {_norm_code(sku) for sku in row.skus} - {""}
    for offer in offers:
        if (offer.sku and _norm_code(offer.sku) in row_skus) or (row.gtin and offer.gtin == row.gtin) or (
            read.how != "shopify" and row.mpn and offer.mpn and _norm_code(offer.mpn) == _norm_code(row.mpn)
        ):
            return offer, TIE_CODE
    price = _one_price(offers)
    if price is None:
        return None, ""
    if read.how == "shopify" or feed_rows_one_price:
        stock = {offer.availability for offer in offers}
        availability = next(iter(stock)) if len(stock) == 1 else ""
        return Offer(price=price, currency=offers[0].currency, availability=availability), TIE_ONE_PRICE
    return None, ""


def stock_reading(row: Row, read: PageRead, tied: Offer | None) -> str:
    """"in stock", "sold out" or "" (rules 5.2): the tied offer's word; else, with no
    variant named, sold out only when every offer says so, in stock when one does."""
    if tied is not None and tied.availability:
        return stock_of(tied.availability)
    if row.variant or not read.offers:
        return ""
    states = {stock_of(offer.availability) for offer in read.offers} - {""}
    if "in stock" in states:
        return "in stock"
    return "sold out" if states == {"sold out"} and all(offer.availability for offer in read.offers) else ""


def far_apart(site: float, feed: float) -> bool:
    """Rules 7.5: a tied reading under half of the feed's price or over twice it."""
    return feed > 0 and (site < FAR_BELOW * feed or site > FAR_ABOVE * feed)


def price_verdict(row: Row, tied: Offer | None) -> Verdict | None:
    """Rules 5.3 and 7.5: None when there is no tied price to judge; failed when it is
    far apart; else passed (the same price, or another the card will show once the
    shop's reader is proven)."""
    if tied is None or tied.price is None or row.price is None or row.price <= 0:
        return None
    if far_apart(tied.price, row.price):
        return Verdict(FAILED, PRICE_FAR_APART)
    return Verdict(PASSED)


def same_price(site: float, feed: float) -> bool:
    """To the penny (rules 7.5)."""
    return abs(round(site, 2) - round(feed, 2)) < 0.005


def photo_verdict(status: int, content_type: str = "", length: int | None = None) -> Verdict:
    """The photo, rules 5.4 (owner, 21/11: «Αμέσως, για κάθε λόγο»). A refusal (401,
    403) fails here; a shop whose photo host refuses at least 9 in 10 of 20 photos asked
    that night has them `not checked` instead (`photos_refused`)."""
    if 200 <= status < 300:
        kind = str(content_type or "").split(";")[0].strip().lower()
        if kind and not kind.startswith("image/") and kind != "application/octet-stream":
            return Verdict(FAILED, NOT_AN_IMAGE)
        if length == 0:
            return Verdict(FAILED, EMPTY)
        return Verdict(PASSED)
    if status in GONE_STATUSES:
        return Verdict(FAILED, GONE)
    if status == 429:
        return Verdict(NOT_CHECKED, OUR_PACE)
    if status in (401, 403):
        return Verdict(FAILED, REFUSED)
    if status == 0 or 500 <= status < 600:
        return Verdict(FAILED, NO_ANSWER)
    return Verdict(FAILED, OTHER_ANSWER)


def photos_refused(asked: int, refused: int) -> bool:
    """Rules 5.4: the shop's photo host refuses the checker."""
    return asked >= PHOTOS_MIN and refused >= MOST * asked


@dataclass(frozen=True)
class ShopNight:
    """What one night says of whether a shop can be checked (rules 5.6.2)."""

    own_address: bool = True
    robots: str = "allowed"  # "allowed", "disallowed", "refused" (401, 403)
    crawl_delay: float | None = None
    requests: int = 0
    # The requests that got any answer at all (an HTTP status, a refusal too): 7.1.
    answers: int = 0
    refused: int = 0
    pages_200: int = 0
    pages_read: int = 0
    catalogue_read: bool = False


def shop_checkable(night: ShopNight) -> tuple[bool, str]:
    """Whether the shop could be checked that night, and why not (rules 5.6.2)."""
    if not night.own_address:
        return False, "no address of its own"
    if night.robots == "disallowed":
        return False, "robots.txt disallows its product pages"
    if night.robots == "refused":
        return False, "robots.txt refused"
    if night.crawl_delay is not None and night.crawl_delay > MAX_CRAWL_DELAY:
        return False, "crawl-delay over 60 s"
    if night.catalogue_read:
        return True, ""
    if night.requests and night.refused >= MOST * night.requests:
        return False, "refuses the bot"
    if night.pages_200 >= PAGES_MIN and night.pages_200 - night.pages_read >= MOST * night.pages_200:
        return False, "its pages are not read"
    return True, ""


def shop_reads_pages(pages_200: int, pages_read: int) -> bool:
    """Rules 5.1: the shop's reader reads a product on at least 9 in 10 of its pages
    that answered 200 that night, so a page with none is not a product page."""
    return pages_200 >= PAGES_MIN and pages_read >= MOST * pages_200


# Awin's relationships (rules 5.6.3), as its Publisher API names them.
JOINED = "joined"
PENDING = "pending"
NOT_JOINED = "notjoined"
REJECTED = "rejected"
SUSPENDED = "suspended"


def awin_out(relationship: str | None, link_status: str = "") -> str:
    """Why Awin's reading puts a shop out, or "" when it stays in (rules 5.6.3).
    `relationship` None: the shop is in none of Awin's lists (a programme closed)."""
    if str(link_status or "").strip().lower() == "offline":
        return "Awin: offline"
    if relationship is None:
        return "Awin: in no list"
    relationship = str(relationship).strip().lower()
    if relationship == REJECTED:
        return "Awin: rejected"
    if relationship == SUSPENDED:
        return "Awin: suspended"
    return ""


def feed_is_old(last_import: date | None, today: date) -> bool:
    """Rules 5.6.4 (Proposed): a feed last imported over 7 days ago; a feed whose age is
    not known is not judged by it."""
    return last_import is not None and (today - last_import).days > FEED_OLD_DAYS
