"""Which current shop offer covers a product (owner, 2026-11-01).

The owner's words: «Ανά προϊόν... Όταν ψάχνει ένας πελάτης ένα προϊόν ή μία κατηγορία
υπάρχει προσφορά σε αυτό το προϊόν ... προϊόντα με προσφορές πρώτα», and, asked whether
that changes "cheapest first": «Ένα προϊόν με προσφορά θα μπαίνει πρώτα από το φθηνότερο».

The offers are Awin's, fetched every night by `deployment/server/fetch_offers.py` into a
file the site reads (`PICWISE_OFFERS_FILE`). Awin gives them per shop, not per product,
so an offer is said to cover a product only where its own words leave no doubt, and a
product it may not cover is never said to be on offer:

- the offer states a discount: a percentage, an amount off, "half price", a second one
  free. A free delivery, a new collection, a bundle price or a code alone is not a
  discount on the product;
- it is meant for shoppers: an offer that speaks of commission is the network's to the
  publisher;
- it is live now by its own dates;
- a voucher comes with its code: a voucher is a code typed at the shop's checkout, and
  Awin gives it only for the programmes PicWise is joined to. Without it the shopper
  cannot have the discount, so the voucher covers no product (2026-11-01, after the
  first deployment showed Geepas's code-less "Kettle & Toaster Set 10 OFF" first). A
  promotion needs no code;
- and it covers the product: the whole shop ("sitewide", "everything", "your order",
  "your first order", "new customers", or a discount naming nothing but the shop), or the
  kind it names, every word of which is in the product's title ("10% off mixer grinders"
  covers a "Mixer Grinder 750W"). An offer that says "up to" or "selected" covers no
  product: some of them only, and which ones it does not say.

Without the file, or with no offer for a product's shop, nothing changes: the order is
the price, as before.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

OFFERS_FILE_ENV = "PICWISE_OFFERS_FILE"
# How often the file is looked at again for a newer one, at most.
_RECHECK_SECONDS = 60.0

_DISCOUNT = re.compile(
    r"\d+(?:\.\d+)?\s?%"            # 10%, 23 %
    r"|£\s?\d+(?:\.\d+)?\s?off\b"   # £15 off
    r"|\b\d+\s?off\b"               # 10 OFF
    r"|\bhalf[\s-]price\b"
    r"|\bbogof\b|\bbuy one,? get one\b|\b2 for 1\b|\bsecond (?:one )?free\b",
    re.IGNORECASE,
)
_NOT_FOR_SHOPPERS = re.compile(r"\bcommission\b|\bcpa\b|\baffiliates?\b|\bpublishers?\b", re.IGNORECASE)
_WHOLE_SHOP = re.compile(
    r"\bsite\s?-?wide\b|\bstore\s?-?wide\b|\beverything\b|\ball orders\b|\ball products\b"
    r"|\ball items\b|\ball purchases\b|\bentire (?:site|store|range|order)\b|\bany order\b"
    r"|\byour (?:first |next )?order\b|\bfirst order\b|\bnew customers?\b|\bfull range\b",
    re.IGNORECASE,
)
_SOME_ONLY = re.compile(r"\bup to\b|\bselected\b|\bselect lines\b|\bselected lines\b", re.IGNORECASE)
_DISCOUNT_WORDS = re.compile(
    r"\d+(?:\.\d+)?\s?%|£\s?\d+(?:\.\d+)?|\b\d+\b|\bhalf[\s-]price\b|\bbogof\b|\bbuy one,? get one\b",
    re.IGNORECASE,
)
_WORD = re.compile(r"[a-z0-9]+")
# Words that say how much or when, not what: what is left names what the offer covers.
_FILLER = frozenset(
    """
    a an and or the of on in at to for with from by off save saving savings get got extra
    flat enjoy now today only just all our your you new plus free discount discounts voucher
    vouchers code codes offer offers deal deals sale sales promo promotion promotions price
    prices purchase purchases order orders product products item items range collection
    collections first next welcome back customers customer whole entire any every store
    shop site sitewide storewide wide everything special exclusive limited time when use
    using apply applied applies included including inc incl over above under spend min
    minimum orders up selected select lines its it is are this that these those per pc pcs
    """.split()
)


@dataclass(frozen=True)
class ProductOffer:
    """A current shop offer that covers a product, as the card shows it."""

    shop: str
    joined: bool
    offer_id: str
    kind: str
    title: str
    terms: str
    end: datetime
    code: str
    # "shop" when it covers the whole shop, "kind" when it names the product's kind.
    scope: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "shop": self.shop,
            "joined": self.joined,
            "offer_id": self.offer_id,
            "kind": self.kind,
            "title": self.title,
            "terms": self.terms,
            "end": self.end.isoformat(),
            "code": self.code,
            "scope": self.scope,
        }


@dataclass(frozen=True)
class _Offer:
    offer: ProductOffer
    start: datetime | None
    words: frozenset[str]


# Words whose last "s" is not a plural's.
_NOT_PLURAL = frozenset(
    {"christmas", "lens", "series", "news", "canvas", "atlas", "gas", "bus", "plus", "bonus", "status", "chaos"}
)


def _singular(word: str) -> str:
    if word in _NOT_PLURAL:
        return word
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith(("ches", "shes", "sses", "xes")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _words(text: str) -> list[str]:
    return [_singular(word) for word in _WORD.findall(str(text or "").lower())]


def _date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def offer_scope(title: str, shop_name: str) -> tuple[str, frozenset[str]] | None:
    """("shop", {}) for an offer on the whole shop, ("kind", words) for one on the
    products whose titles carry every one of `words`, or None for one PicWise never
    puts on a product."""
    text = " ".join(str(title or "").split())
    if not text or _NOT_FOR_SHOPPERS.search(text) or not _DISCOUNT.search(text):
        return None
    if _SOME_ONLY.search(text):
        return None
    if _WHOLE_SHOP.search(text):
        return "shop", frozenset()
    shop_words = set(_words(shop_name))
    shop_joined = "".join(_words(shop_name))
    named = [
        word
        for word in _words(_DISCOUNT_WORDS.sub(" ", text))
        if word not in _FILLER and not any(char.isdigit() for char in word) and len(word) > 1
    ]
    subject = [word for word in named if word not in shop_words]
    if not subject or (shop_joined and "".join(named) and "".join(named) in shop_joined):
        # A discount naming nothing but the shop ("Bio Gaia 15% off voucher").
        return "shop", frozenset()
    return "kind", frozenset(subject)


def _covers(words: frozenset[str], title: str) -> bool:
    title_words = set(_words(title))
    joined = "".join(_words(title))
    return all(word in title_words or (len(word) >= 6 and word in joined) for word in words)


class _Offers:
    """The offers file, read once and again when it changes."""

    def __init__(self) -> None:
        self.key: tuple[str, int, int] | None = None
        self.checked = 0.0
        self.by_shop: dict[str, tuple[_Offer, ...]] = {}

    def load(self, document: Mapping[str, Any] | None) -> None:
        by_shop: dict[str, tuple[_Offer, ...]] = {}
        shops = (document or {}).get("shops") if isinstance(document, Mapping) else None
        for ident, shop in (shops or {}).items():
            if not isinstance(shop, Mapping):
                continue
            name = " ".join(str(shop.get("name") or "").split())
            kept: list[_Offer] = []
            for row in shop.get("offers") or ():
                if not isinstance(row, Mapping):
                    continue
                end = _date(row.get("end"))
                scope = offer_scope(str(row.get("title") or ""), name)
                if end is None or scope is None:
                    continue
                code = " ".join(str(row.get("code") or "").split())
                if str(row.get("type") or "").strip().lower() == "voucher" and not code:
                    # A voucher without its code: the shopper cannot have it.
                    continue
                kept.append(_Offer(
                    offer=ProductOffer(
                        shop=name,
                        joined=bool(shop.get("joined")),
                        offer_id=str(row.get("id") or ""),
                        kind=str(row.get("type") or ""),
                        title=" ".join(str(row.get("title") or "").split()),
                        terms=" ".join(str(row.get("terms") or "").split()),
                        end=end,
                        code=code,
                        scope=scope[0],
                    ),
                    start=_date(row.get("start")),
                    words=scope[1],
                ))
            if kept:
                by_shop[str(ident).strip()] = tuple(kept)
        self.by_shop = by_shop

    def refresh(self) -> None:
        path = str(os.environ.get(OFFERS_FILE_ENV) or "").strip()
        now = time.monotonic()
        if self.key is not None and self.key[0] == path and now - self.checked < _RECHECK_SECONDS:
            return
        self.checked = now
        if not path:
            self.key, self.by_shop = None, {}
            return
        try:
            stat = os.stat(path)
        except OSError:
            self.key, self.by_shop = (path, 0, 0), {}
            return
        key = (path, int(stat.st_mtime_ns), int(stat.st_size))
        if key == self.key:
            return
        try:
            with open(path, encoding="utf-8") as handle:
                document = json.load(handle)
        except (OSError, ValueError):
            document = None
        self.load(document)
        self.key = key


_OFFERS = _Offers()
_SET_BY_HAND = False


def set_offers_document(document: Mapping[str, Any] | None) -> None:
    """Use this document instead of the file (tests); None goes back to the file."""
    global _SET_BY_HAND
    if document is None:
        _SET_BY_HAND = False
        _OFFERS.key, _OFFERS.by_shop, _OFFERS.checked = None, {}, 0.0
        return
    _SET_BY_HAND = True
    _OFFERS.load(document)


def _shop_id(raw: Mapping[str, Any]) -> str:
    value = raw.get("merchant_id") or raw.get("advertiser_id") or raw.get("MERCHANT_ID")
    if not value:
        return ""
    return value.strip() if isinstance(value, str) else str(value).strip()


def _covering(offers: tuple[_Offer, ...], product: Any, moment: datetime) -> ProductOffer | None:
    live = [entry for entry in offers if entry.offer.end >= moment and (entry.start is None or entry.start <= moment)]
    if not live:
        return None
    covering = [entry for entry in live if entry.offer.scope == "shop"]
    kinds = [entry for entry in live if entry.offer.scope == "kind"]
    if kinds:
        # The title's words are read once for all the kind offers of its shop.
        words = _words(str(getattr(product, "title", "") or ""))
        title_words, joined = set(words), "".join(words)
        covering += [
            entry
            for entry in kinds
            if all(word in title_words or (len(word) >= 6 and word in joined) for word in entry.words)
        ]
    if not covering:
        return None
    # One naming its kind before one on the whole shop, one with a code before one
    # without, then the one ending first.
    covering.sort(key=lambda entry: (entry.offer.scope != "kind", not entry.offer.code, entry.offer.end))
    return covering[0].offer


def _current() -> dict[str, tuple[_Offer, ...]]:
    if not _SET_BY_HAND:
        _OFFERS.refresh()
    return _OFFERS.by_shop


def offer_for_product(product: Any, *, now: datetime | None = None) -> ProductOffer | None:
    """The current offer that covers this product, or None."""
    by_shop = _current()
    if not by_shop:
        return None
    raw = getattr(product, "raw", None)
    offers = by_shop.get(_shop_id(raw if isinstance(raw, Mapping) else {}))
    return _covering(offers, product, now or datetime.now(timezone.utc)) if offers else None


def offers_covering(products: Any, *, now: datetime | None = None) -> dict[int, ProductOffer]:
    """The current offer covering each of these products that has one, by `id(product)`:
    the file is looked at once, and a product whose shop has no offer costs one lookup."""
    by_shop = _current()
    if not by_shop:
        return {}
    moment = now or datetime.now(timezone.utc)
    found: dict[int, ProductOffer] = {}
    # A shop whose offers all cover the whole shop gives every product the same one:
    # worked out once for the shop, not once for each of its products.
    whole_shop: dict[str, ProductOffer | None] = {}
    for product in products:
        raw = getattr(product, "raw", None)
        shop = _shop_id(raw) if isinstance(raw, Mapping) else ""
        offers = by_shop.get(shop) if shop else None
        if not offers:
            continue
        if shop in whole_shop:
            offer = whole_shop[shop]
        else:
            offer = _covering(offers, product, moment)
            if all(entry.offer.scope == "shop" for entry in offers):
                whole_shop[shop] = offer
        if offer is not None:
            found[id(product)] = offer
    return found
