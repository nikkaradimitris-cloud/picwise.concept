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
import threading
from collections import Counter
from datetime import datetime
from typing import Any, Callable, Iterable

from picwise_providers.normalization import extract_merchant_name
from picwise_providers.state import loaded_prepared_at
from picwise_search import resolve_live_search

from .home_store import HomeFacts, HomeLists, Kind, Pick, home_store_on, load_home_lists
from .reference import _build_price_first_cards, provider_feed_cards_will_render
from .shop_names import shop_display_name

logger = logging.getLogger(__name__)

# The shops named on the page (the specification, 5.9).
TOP_SHOPS = 8
_STATE: dict[str, Any] = {"facts": None}
_WORK_LOCK = threading.Lock()
_WATCHER: dict[str, Any] = {}


def current_home_facts() -> HomeFacts | None:
    """The facts of the catalogue this process answers from now, or None: facts of
    another catalogue are never shown (a Recommended card must be its search's tonight)."""
    facts = _STATE["facts"]
    if facts is None or facts.prepared_at != loaded_prepared_at():
        return None
    return facts


def set_home_facts_for_tests(facts: HomeFacts | None) -> None:
    _STATE["facts"] = facts


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


def top_shops(products: Iterable[Any], *, count: int = TOP_SHOPS) -> tuple[tuple[str, ...], int]:
    """The `count` shops with the most of these products, by their names as a buyer
    knows them, the most first, then by name; and how many shops there are."""
    tally: Counter[str] = Counter()
    names: dict[str, Counter[str]] = {}
    for product in products:
        raw = getattr(product, "raw", None)
        name = str(extract_merchant_name(raw if isinstance(raw, dict) else {}) or "").strip()
        if not name:
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


_UNSET: Any = object()


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
    for section in lists.sections:
        for tile in section.tiles:
            resolution = answer(tile.query)
            try:
                shown = resolution is not None and provider_feed_cards_will_render(resolution)
            except Exception:
                shown = False
            if shown:
                with_products.add(tile.query)
    shops, shop_count = top_shops(_catalogue_products() if products is None else products)
    return HomeFacts(
        prepared_at=when,
        picks=tuple(picks),
        tiles_with_products=frozenset(with_products),
        shops=shops,
        shop_count=shop_count,
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
            except Exception:  # the next look tries again; the page leaves out what it needs
                logger.exception("the home page's facts could not be worked out")
            stop.wait(every_seconds)

    thread = threading.Thread(target=look, name="picwise-home-facts", daemon=True)
    _WATCHER.update(thread=thread, pid=os.getpid())
    thread.start()
    return stop
