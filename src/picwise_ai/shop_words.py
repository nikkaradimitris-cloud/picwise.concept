"""The shops' words for a need, offered as searches only with the catalogue's own counts.

Owner, 2026-11-05: «ΟΤΑΝ ΔΕΝ ΒΡΙΣΚΕΙ ΚΑΤΙ ΝΑ ΜΗΝ ΛΕΕΙ ΔΕΝ ΒΡΕΘΗΚΕ ΣΚΕΨΟΥ ΚΑΤΙ ΠΙΟ ΕΞΥΠΝΟ»,
then «ΣΩΣΤΑ» to this: when no product's title or description says it fits the need, the
page says no sentence; it may offer the words the shops use for that need ("compact" for
"microwave for a small kitchen"), each as a search of its own, "compact microwave". The
AI only proposes the words, from the titles it was given (`checks.shop_words_that_pass`);
each one is kept only when the engine answers its search with products of a kind and
honours every word of it, and the count shown is that answer's, never the AI's: a click
shows exactly those products.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from picwise_ai.complex_search import ComplexSearch

# A button's search is answered as a page's first four are.
_SHOWN = 4
_FOUND_BY_WORDS = "provider_feed_selection_product_named_by_words"


@dataclass(frozen=True)
class ShopWord:
    """A word of the shops for the need: the search a button runs and how many products
    of a kind that search finds."""

    word: str
    search: str
    count: int


def button_search(word: str, complex_search: ComplexSearch) -> str:
    """The search a button runs: the shops' word and the kind the products are."""
    return f"{' '.join(str(word).split())} {complex_search.kind_name}".strip()


def verified_shop_words(
    words: tuple[str, ...], complex_search: ComplexSearch, resolve: Callable[..., Any]
) -> tuple[ShopWord, ...]:
    """The words whose own search the engine answers with products of a kind, matching
    every word of it, with that answer's count; `resolve` is `resolve_live_search`."""
    kept: list[ShopWord] = []
    for word in words:
        search = button_search(word, complex_search)
        try:
            resolution = resolve(search, shown=_SHOWN)
        except Exception:  # a word that cannot be searched is not offered
            continue
        count = int(getattr(resolution, "provider_feed_total_count", 0) or 0)
        if count <= 0 or not str(getattr(resolution, "understood_concept_id", "") or ""):
            continue
        if _FOUND_BY_WORDS in tuple(getattr(resolution, "reason_codes", ()) or ()):
            continue
        if tuple(getattr(resolution, "provider_feed_unmatched_query_terms", ()) or ()):
            continue
        if tuple(getattr(resolution, "provider_feed_partially_matched_terms", ()) or ()):
            continue
        if not tuple(getattr(resolution, "provider_feed_selected_products", ()) or ()):
            continue
        kept.append(ShopWord(word=word, search=search, count=count))
    return tuple(kept)
