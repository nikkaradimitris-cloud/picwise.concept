"""The AI layer on the site: one search that reads the stored answer, or asks for one, and
the small answer the page's script asks for (`docs/PICWISE_AI_LAYER_SPEC.md`, 4.4 and
4.5; the Decision Contract, "The products that fit a complex search first").

The site never calls the API and never waits (the spec, 1.4): for a complex search with
no answer stored it writes a draft to the folder it shares with the service
`picwise-assist` (`picwise_ai.store`) and draws the page as before, with an empty place
its script fills; the draft becomes a job only when that script asks, so a visitor whose
browser runs no script, as most bots, costs nothing. With an answer stored, the search
puts first the products whose own words show they fit (owner, 2026-11-06) and the page
draws them marked, at once. Without the shared folder (`PICWISE_ASSIST_DIR`) nothing here
changes the page.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from types import SimpleNamespace
from typing import Any

from picwise_ai.complex_search import SHOWN_FOR_CANDIDATES, complex_search_of, description_of, why_not_asked
from picwise_ai.shop_words import verified_shop_words
from picwise_ai.store import (
    AssistLookup,
    activate_draft,
    assist_directory,
    draft_waits,
    fitting_words,
    job_pending,
    read_result,
    read_served,
    valid_key,
    write_draft,
    write_served,
)
from picwise_providers.state import resolve_card_eligible_provider_feed_product_by_id
from picwise_search import resolve_live_search
from picwise_surface.assist import AssistView


class _Descriptions:
    """Each product's own description by its id, read only when a job is written."""

    def get(self, product_id: Any, default: str = "") -> str:
        product = resolve_card_eligible_provider_feed_product_by_id(str(product_id or ""))
        return description_of(product) if product is not None else default


def page_resolution(resolution: Any, shown: int) -> Any:
    """The answer as the page holds it: the products "More" has opened, no more. The search
    is run for the 30 products the AI reads; the page shows what it showed before."""
    first = len(tuple(getattr(resolution, "provider_feed_selected_products", ()) or ()))
    more = tuple(getattr(resolution, "provider_feed_more_products", ()) or ())
    if not first or not more:
        return resolution
    holds = max(first, -(-max(int(shown or 0), first) // first) * first)
    return replace(resolution, provider_feed_more_products=more[: max(0, holds - first)])


def resolve_with_assist(
    query: str, *, shown: int = 0, write_jobs: bool = True, now: datetime | None = None
) -> tuple[Any, AssistView | None]:
    """One search and the AI layer's part of its page.

    With an answer stored for the search and its products: the products that fit first,
    with the sentence and their words; or the shops' words, counted once (the place left
    empty until the page's script has them counted). With none: a draft, written once
    (never on a page the script reads again: `write_jobs` False), and the empty place.
    """
    directory = assist_directory()
    if directory is None:
        return resolve_live_search(query, shown=shown), None
    lookup = AssistLookup(directory, query, now=now)
    full = resolve_live_search(query, shown=max(int(shown or 0), SHOWN_FOR_CANDIDATES), fitting_for=lookup)
    page = page_resolution(full, shown)
    if why_not_asked(query, full) or not lookup.key:
        return page, None
    key, result = lookup.key, lookup.result
    if result is not None:
        status = result.get("status")
        if status == "shown" and getattr(full, "provider_feed_fitting_product_ids", ()):
            return page, AssistView(sentence=str(result.get("sentence") or ""), fit_words=fitting_words(result))
        if status == "buttons":
            served = read_served(directory, key)
            if served is None:
                return page, AssistView(pending_key=key)
            buttons = _buttons(served)
            return page, (AssistView(buttons=buttons) if buttons else None)
        return page, None
    if write_jobs and not job_pending(directory, key) and not draft_waits(directory, key):
        complex_search = complex_search_of(query, full, descriptions=_Descriptions())
        if complex_search is None:
            return page, None
        try:
            write_draft(directory, complex_search, full.provider_feed_candidates_signature, now=now)
        except OSError:
            return page, None
    return page, AssistView(pending_key=key)


def _buttons(served: list[dict[str, Any]]) -> tuple[tuple[str, str, int], ...]:
    buttons = []
    for row in served:
        word, search = str(row.get("word") or "").strip(), str(row.get("search") or "").strip()
        try:
            count = int(row.get("count") or 0)
        except (TypeError, ValueError):
            continue
        if word and search and count > 0:
            buttons.append((word, search, count))
    return tuple(buttons)


def count_shop_words(result: dict[str, Any]) -> list[dict[str, Any]]:
    """The shops' words of an answer, each kept only when the catalogue answers its own
    search with products of the kind and every word of it, with that count
    (`shop_words.verified_shop_words`)."""
    words = tuple(str(word) for word in result.get("shop_words") or () if str(word).strip())
    kind = SimpleNamespace(kind_name=str(result.get("kind_name") or ""))
    return [
        {"word": word.word, "search": word.search, "count": word.count}
        for word in verified_shop_words(words, kind, resolve_live_search)
    ]


def assist_status(key: str, *, now: datetime | None = None) -> dict[str, str]:
    """What the page's script is told: "ready" (read the page again), "pending" (ask again
    in a second) or "none" (stop: nothing will change the page). Its first question makes
    the page's draft a job for the service."""
    directory = assist_directory()
    if directory is None or not valid_key(key):
        return {"state": "none"}
    result = read_result(directory, key, now=now)
    if result is None:
        if job_pending(directory, key):
            return {"state": "pending"}
        try:
            activated = activate_draft(directory, key, now=now)
        except OSError:
            activated = False
        return {"state": "pending" if activated else "none"}
    status = result.get("status")
    if status == "shown":
        return {"state": "ready"}
    if status == "buttons":
        served = read_served(directory, key)
        if served is None:
            served = count_shop_words(result)
            try:
                write_served(directory, key, served)
            except OSError:
                pass
        return {"state": "ready" if _buttons(served) else "none"}
    return {"state": "none"}
