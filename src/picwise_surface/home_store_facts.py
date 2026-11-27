"""What the home page as a store knows of its catalogue (`docs/PICWISE_HOME_STORE_SPEC.md`,
5.10): worked out once for each catalogue this process answers from, never while a page
is drawn, and shown only beside the catalogue it was worked out for.

- Each kind of the Recommended band (`data/home_store.json`): its Recommended exactly as
  its search's first card shows it tonight, by the search's own code
  (`resolve_live_search`, then the search page's own cards, `reference._build_price_first_cards`):
  never another rule. A kind with no Recommended tonight has no card.
- Which tiles' searches have products tonight: a tile whose search shows no card is not
  drawn, never a link to an empty answer (the specification, 5.8).
- The shops: how many a search reads, and the eight with the most products a search
  holds, by their names as a buyer knows them (`shop_names`); never by commission.
- The shops' offers that cover products shown tonight (`picwise_providers.product_offers`,
  the same rules as a card's offer): one a shop, the one a card would show first; the
  row ordered by how many products shown tonight each covers, eight at most; never by
  commission, never by whether the account is joined.

The searches are made here as on the site, with no AI layer and nothing written to the
searches' log or counted as a visitor's. On the server a thread of each worker works the
facts out when the switch is on (`keep_home_facts_current`, started by
`deployment/server/wsgi_server.py`): about thirty searches when a worker first answers
from a catalogue and again each night. Where no catalogue is prepared (the Vercel backup)
nothing is known and the page leaves out what needs it.

Kept out of `picwise_providers` and `picwise_nlu`: a change here prepares nothing again.
"""
from __future__ import annotations

import logging
import os
import re
import threading
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Callable, Iterable

from picwise_providers.normalization import extract_merchant_name
from picwise_providers.product_offers import offers_covering
from picwise_providers.state import loaded_prepared_at
from picwise_search import resolve_live_search

from .home_store import (
    MIN_PRODUCTS,
    Departments,
    HomeFacts,
    HomeLists,
    Kind,
    OfferCard,
    Pick,
    home_store_on,
    load_departments,
    load_home_lists,
)
from .reference import _build_price_first_cards, provider_feed_cards_will_render
from .shop_names import shop_display_name

logger = logging.getLogger(__name__)

# The shops named on the page (the specification, 5.9), and the offers in its row (5.5).
TOP_SHOPS = 8
TOP_OFFERS = 8
_STATE: dict[str, Any] = {"facts": None, "kinds": None}
_WORK_LOCK = threading.Lock()
_WATCHER: dict[str, Any] = {}
_UNSET_KINDS: Any = object()


def current_home_facts() -> HomeFacts | None:
    """The facts of the catalogue this process answers from now, or None: facts of
    another catalogue are never shown (a Recommended card must be its search's tonight)."""
    facts = _STATE["facts"]
    if facts is None or facts.prepared_at != loaded_prepared_at():
        return None
    return facts


def set_home_facts_for_tests(facts: HomeFacts | None) -> None:
    _STATE["facts"] = facts


@dataclass(frozen=True)
class KindFacts:
    """A department's kind tonight (the specification, 7.1): how many products its search
    holds, the price of its cheapest card, its Recommended as its search shows it."""

    count: int
    low: str
    pick: Pick | None


@dataclass(frozen=True)
class OfferKind:
    """A kind an offer covers products of tonight: its words, how many, the cheapest's
    price (the offers' pages, the specification 7.2)."""

    query: str
    count: int
    low: str


@dataclass(frozen=True)
class DepartmentsFacts:
    prepared_at: datetime | None
    kinds: dict[str, KindFacts]
    # For each offer, the departments' kinds whose search holds products it covers, the
    # most first.
    offer_kinds: dict[str, tuple[OfferKind, ...]] = field(default_factory=dict)


def current_kind_facts() -> DepartmentsFacts | None:
    """The departments' facts of the catalogue this process answers from now, or None."""
    facts = _STATE["kinds"]
    if facts is None or facts.prepared_at != loaded_prepared_at():
        return None
    return facts


def set_kind_facts_for_tests(facts: DepartmentsFacts | None) -> None:
    _STATE["kinds"] = facts


def _link_words(name: str) -> str:
    """"See kettles", "See TVs": the name's first letter small unless it starts a word in
    capitals."""
    if len(name) > 1 and name[1].isupper():
        return f"See {name}"
    return f"See {name[:1].lower()}{name[1:]}"


def first_page(resolution: Any) -> Any:
    """A search's answer as its first page shows it, whatever "More" opened."""
    if getattr(resolution, "provider_feed_more_products", ()):
        return replace(resolution, provider_feed_more_products=())
    return resolution


def offer_counts(resolution: Any) -> dict[str, tuple[int, str]]:
    """For each offer covering products of a search's whole answer (as far as "More"
    opened it), how many and the cheapest's price, the shop's own."""
    from .reference import _display_price

    offers = dict(getattr(resolution, "provider_feed_offers", ()) or ())
    products = tuple(getattr(resolution, "provider_feed_selected_products", ()) or ()) + tuple(
        getattr(resolution, "provider_feed_more_products", ()) or ()
    )
    found: dict[str, list[Any]] = {}
    for product in products:
        offer = offers.get(str(product.get("provider_product_id") or "").strip())
        offer_id = str((offer or {}).get("offer_id") or "").strip()
        if not offer_id:
            continue
        shown = _display_price(product)
        digits = re.search(r"\d[\d,]*(?:\.\d+)?", shown)
        price = float(digits.group(0).replace(",", "")) if digits else None
        held = found.setdefault(offer_id, [0, None, ""])
        held[0] += 1
        if price is not None and (held[1] is None or price < held[1]):
            held[1], held[2] = price, shown
        elif not held[2]:
            held[2] = shown
    return {offer_id: (count, low) for offer_id, (count, _value, low) in found.items()}


def kind_facts(name: str, query: str, resolution: Any) -> KindFacts | None:
    """A kind's facts by its search's own first page, or None when it shows none."""
    try:
        if resolution is None or not provider_feed_cards_will_render(resolution):
            return None
        resolution = first_page(resolution)
        cards = _build_price_first_cards(resolution=resolution)
    except Exception:
        logger.exception("a department could not read the search %r", query)
        return None
    if not cards:
        return None
    count = int(getattr(resolution, "provider_feed_total_count", 0) or 0) or len(cards)
    cheapest = next((card for card in cards if not card.get("recommended")), cards[0])
    low = str(cheapest.get("price") or "").strip()
    pick = recommended_pick(Kind(query=query, kind=name, link=_link_words(name), drawing=""), resolution)
    return KindFacts(count=count, low=low, pick=pick)


def work_out_kind_facts(
    *,
    departments: Departments | None = None,
    search: Callable[[str], Any] | None = None,
    prepared_at: datetime | None = _UNSET_KINDS,
) -> DepartmentsFacts:
    """Every department's kinds, each by its search (about 210 searches): worked out once
    for each catalogue, never while a page is drawn."""
    departments = departments if departments is not None else load_departments()
    search = search if search is not None else _whole_answer_search
    when = loaded_prepared_at() if prepared_at is _UNSET_KINDS else prepared_at
    kinds: dict[str, KindFacts] = {}
    by_offer: dict[str, list[OfferKind]] = {}
    for items in departments.kinds.values():
        for item in items:
            if item.query in kinds:
                continue
            try:
                resolution = search(item.query)
            except Exception:
                logger.exception("a department's search for %r failed", item.query)
                continue
            fact = kind_facts(item.name, item.query, resolution)
            if fact is None:
                continue
            kinds[item.query] = fact
            try:
                counted = offer_counts(resolution)
            except Exception:
                logger.exception("a department could not count the offers of %r", item.query)
                counted = {}
            for offer_id, (count, low) in counted.items():
                by_offer.setdefault(offer_id, []).append(OfferKind(query=item.query, count=count, low=low))
    offer_kinds = {
        offer_id: tuple(sorted(found, key=lambda kind: (-kind.count, kind.query))) for offer_id, found in by_offer.items()
    }
    return DepartmentsFacts(prepared_at=when, kinds=kinds, offer_kinds=offer_kinds)


def _whole_answer_search(query: str) -> Any:
    """A kind's search as far as "More" can open it, so that an offer's products are
    counted among all of its products the page can show (`MAX_SHOWN_PRODUCTS`)."""
    from picwise_search.live_search_resolver import MAX_SHOWN_PRODUCTS

    return resolve_live_search(query, shown=MAX_SHOWN_PRODUCTS)


def recommended_pick(kind: Kind, resolution: Any) -> Pick | None:
    """The kind's Recommended as its search's first card shows it, or None when the
    search has no Recommended (too few products, no barcode) or shows no card."""
    try:
        cards = _build_price_first_cards(resolution=resolution)
    except Exception:  # a search the page could not draw has no card here either
        logger.exception("the home page could not read the Recommended of %r", kind.query)
        return None
    if not cards or not cards[0].get("recommended"):
        return None
    card = cards[0]
    title, price = str(card.get("name") or "").strip(), str(card.get("price") or "").strip()
    shop, image = str(card.get("shop") or "").strip(), str(card.get("image") or "").strip()
    if not (title and price and shop and image):
        return None
    return Pick(query=kind.query, kind=kind.kind, link=kind.link, title=title, price=price, shop=shop, image=image)


def _catalogue_products() -> tuple[Any, ...]:
    """The products a search reads from the prepared catalogue this process holds, or
    none; read only, never loaded here (as `state.peek_search_catalogue_counts`)."""
    from picwise_providers.state import _PREPARED_STATE, _is_fresh

    prepared = _PREPARED_STATE.get("prepared")
    if prepared is None or not _is_fresh(prepared):
        return ()
    return tuple(prepared.products)


# Names in the feed that name no shop a buyer could visit (owner, 2026-11-24, «Ναι σε
# όλα»: off the list of shops and out of their count).
NOT_A_SHOP = frozenset({"shopping ads: google & bing"})


def is_a_shop(name: str) -> bool:
    return " ".join(str(name or "").split()).casefold() not in NOT_A_SHOP


def all_shop_names(products: Iterable[Any]) -> tuple[str, ...]:
    """Every shop of these products, by its name as a buyer knows it, A to Z."""
    names = set()
    for product in products:
        raw = getattr(product, "raw", None)
        name = str(extract_merchant_name(raw if isinstance(raw, dict) else {}) or "").strip()
        if name and is_a_shop(name):
            display = shop_display_name(name)
            if display and is_a_shop(display):
                names.add(display)
    return tuple(sorted(names, key=lambda name: (name.casefold(), name)))


def top_shops(products: Iterable[Any], *, count: int = TOP_SHOPS) -> tuple[tuple[str, ...], int]:
    """The `count` shops with the most of these products, by their names as a buyer
    knows them, the most first, then by name; and how many shops there are. A name that
    names no shop is in neither (`NOT_A_SHOP`)."""
    tally: Counter[str] = Counter()
    names: dict[str, Counter[str]] = {}
    for product in products:
        raw = getattr(product, "raw", None)
        name = str(extract_merchant_name(raw if isinstance(raw, dict) else {}) or "").strip()
        if not name or not is_a_shop(name):
            continue
        key = name.lower()
        tally[key] += 1
        names.setdefault(key, Counter())[name] += 1
    ranked = sorted(tally.items(), key=lambda item: (-item[1], item[0]))
    shown = []
    for key, _count in ranked:
        display = shop_display_name(names[key].most_common(1)[0][0])
        if display and display not in shown:
            shown.append(display)
        if len(shown) >= count:
            break
    return tuple(shown), len(tally)


def _offer_card(offer: Any, covered: int) -> OfferCard:
    return OfferCard(
        shop=shop_display_name(offer.shop) or offer.shop,
        offer_id=offer.offer_id,
        title=offer.title,
        end=offer.end,
        products=covered,
        code=str(offer.code or ""),
        terms=str(offer.terms or ""),
        scope=str(offer.scope or ""),
    )


def all_shop_offers(products: Iterable[Any], *, now: datetime | None = None) -> tuple[tuple[OfferCard, ...], tuple[OfferCard, ...]]:
    """The shops' offers that cover these products, by the rules of a card's offer: the
    row's (for each shop the one a card would show first: naming a kind before the whole
    shop, with a code before without, ending first; the offers covering the most of these
    products first, then the one ending first, then by shop; `TOP_OFFERS` at most) and
    every one of them (the shops in the same order, a shop's offers by the same rank)."""
    products = tuple(products)
    covering = offers_covering(products, now=now)
    tally: dict[tuple[str, str], list[Any]] = {}
    for product in products:
        offer = covering.get(id(product))
        if offer is None:
            continue
        held = tally.setdefault((offer.shop, offer.offer_id), [offer, 0])
        held[1] += 1
    by_shop: dict[str, list[tuple[tuple[Any, ...], Any, int]]] = {}
    for (shop, _offer_id), (offer, covered) in tally.items():
        if not (offer.offer_id and offer.title):
            continue
        rank = (offer.scope != "kind", not offer.code, offer.end, offer.offer_id)
        by_shop.setdefault(shop, []).append((rank, offer, covered))
    for items in by_shop.values():
        items.sort(key=lambda item: item[0])
    shops = sorted(by_shop, key=lambda shop: (-by_shop[shop][0][2], by_shop[shop][0][1].end, shop))
    row = tuple(_offer_card(by_shop[shop][0][1], by_shop[shop][0][2]) for shop in shops)
    row = tuple(sorted(row, key=lambda card: (-card.products, card.end, card.shop)))[:TOP_OFFERS]
    every = tuple(_offer_card(offer, covered) for shop in shops for _rank, offer, covered in by_shop[shop])
    return row, every


def shop_offers(
    products: Iterable[Any], *, count: int = TOP_OFFERS, now: datetime | None = None
) -> tuple[OfferCard, ...]:
    """The row's offers (`all_shop_offers`), `count` at most."""
    return all_shop_offers(products, now=now)[0][:count]


_UNSET: Any = object()


def products_shown(resolution: Any) -> int:
    """How many products a search's answer holds tonight, as its page counts them; 0 when
    it shows no card. The home page shows a kind from two (`MIN_PRODUCTS`)."""
    try:
        if resolution is None or not provider_feed_cards_will_render(resolution):
            return 0
        shown = len(tuple(resolution.provider_feed_selected_products)) + len(
            tuple(getattr(resolution, "provider_feed_more_products", ()) or ())
        )
        return max(int(getattr(resolution, "provider_feed_total_count", 0) or 0), shown)
    except Exception:
        logger.exception("the home page could not count a search's products")
        return 0


def work_out_home_facts(
    *,
    lists: HomeLists | None = None,
    search: Callable[[str], Any] = resolve_live_search,
    products: Iterable[Any] | None = None,
    prepared_at: datetime | None = _UNSET,
) -> HomeFacts:
    """The facts for the catalogue a search reads now. `search` and `products` are the
    site's own unless a test gives its own."""
    lists = lists if lists is not None else load_home_lists()
    when = loaded_prepared_at() if prepared_at is _UNSET else prepared_at
    answers: dict[str, Any] = {}

    def answer(query: str) -> Any:
        if query not in answers:
            try:
                answers[query] = search(query)
            except Exception:  # one search that fails leaves its card and tile out
                logger.exception("the home page's search for %r failed", query)
                answers[query] = None
        return answers[query]

    picks = []
    for kind in lists.recommended:
        resolution = answer(kind.query)
        pick = recommended_pick(kind, resolution) if resolution is not None else None
        if pick is not None:
            picks.append(pick)
    with_products = set()
    asked = [tile.query for section in lists.sections for tile in section.tiles]
    asked += [kind.query for banner in lists.banners for kind in banner.kinds]
    for query in asked:
        if query in with_products:
            continue
        if products_shown(answer(query)) >= MIN_PRODUCTS:
            with_products.add(query)
    catalogue = _catalogue_products() if products is None else tuple(products)
    shops, shop_count = top_shops(catalogue)
    shop_names = all_shop_names(catalogue)
    # The home page's count is the list's (the specification, 7.3).
    shop_count = len(shop_names) if shop_names else shop_count
    try:
        offers, every_offer = all_shop_offers(catalogue)
    except Exception:  # no offers' row rather than a wrong one
        logger.exception("the home page's offers could not be read")
        offers, every_offer = (), ()
    return HomeFacts(
        prepared_at=when,
        picks=tuple(picks),
        tiles_with_products=frozenset(with_products),
        shops=shops,
        shop_count=shop_count,
        shop_names=shop_names,
        offers=offers,
        all_offers=every_offer,
    )


def refresh_home_facts() -> HomeFacts | None:
    """Work the facts out for the catalogue loaded now, unless they are already; kept
    only if the catalogue did not change meanwhile. None where none is loaded."""
    prepared_at = loaded_prepared_at()
    if prepared_at is None:
        return None
    facts = _STATE["facts"]
    if facts is not None and facts.prepared_at == prepared_at:
        return facts
    with _WORK_LOCK:
        facts = _STATE["facts"]
        if facts is not None and facts.prepared_at == prepared_at:
            return facts
        facts = work_out_home_facts(prepared_at=prepared_at)
        if loaded_prepared_at() == prepared_at:
            _STATE["facts"] = facts
        return facts


def refresh_kind_facts() -> DepartmentsFacts | None:
    """As `refresh_home_facts`, for the departments' kinds; worked out after the home
    page's facts, so that those are never kept waiting for them."""
    prepared_at = loaded_prepared_at()
    if prepared_at is None:
        return None
    facts = _STATE["kinds"]
    if facts is not None and facts.prepared_at == prepared_at:
        return facts
    with _WORK_LOCK:
        facts = _STATE["kinds"]
        if facts is not None and facts.prepared_at == prepared_at:
            return facts
        facts = work_out_kind_facts(prepared_at=prepared_at)
        if loaded_prepared_at() == prepared_at:
            _STATE["kinds"] = facts
        return facts


def keep_home_facts_current(*, every_seconds: float = 20.0) -> threading.Event | None:
    """Start this worker's thread that keeps the facts current: while the switch is on
    (`home_store_on`), it works them out when the worker first answers from a catalogue
    and again when a new one is loaded; while it is off, it does nothing. Returns the
    event that stops it, or None when one already runs in this process."""
    if _WATCHER.get("pid") == os.getpid():
        return None
    stop = threading.Event()

    def look() -> None:
        while not stop.is_set():
            try:
                if home_store_on():
                    refresh_home_facts()
                    refresh_kind_facts()
            except Exception:  # the next look tries again; the page leaves out what it needs
                logger.exception("the home page's facts could not be worked out")
            stop.wait(every_seconds)

    thread = threading.Thread(target=look, name="picwise-home-facts", daemon=True)
    _WATCHER.update(thread=thread, pid=os.getpid())
    thread.start()
    return stop
