"""Whether a search is complex enough for the AI layer, and what it is asked about.

The AI layer's spec (`docs/PICWISE_AI_LAYER_SPEC.md`, 4.1): the AI is asked only when a
search for a kind is answered with products and the page says "PicWise could not match":
words of the search no product of the kind carries ("quiet washing machine"), or a
narrower kind with no product that fell back to the broader one ("motorcycle helmet").
These are the engine's own signals; the search's length, or words like "for" and «για»,
decide nothing on their own.

Never asked about: the buyer's judgements ("best", «φθηνό»), which PicWise answers with
its own order and Recommended; a condition ("refurbished"), which has its own rule
(`picwise_providers.product_condition`). Not asked either: a search whose kind was not
understood (no verified products to read), and an answer found by its words (its products
are doubtful, not verified: the decision contract, "The main kind only", point 7).
"""
from __future__ import annotations

import html
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from picwise_nlu.concept_understanding import (
    normalize_understanding_text,
    read_condition_request,
    understand_product_query,
)
from picwise_nlu.product_concepts import get_product_concepts_by_id
from picwise_providers.decision_labels import format_price_display
from picwise_providers.search_selection import AI_CANDIDATES

# At most this many products of the answer are read, in the page's order: the
# Recommended, the products on offer, then the rest, cheapest first. One number with the
# selection's, which keeps the AI's answer under these products' signature.
MAX_CANDIDATES = AI_CANDIDATES
# The page holds products in fours; a search run for the AI asks for this many.
SHOWN_FOR_CANDIDATES = 32
# Of each product's own description, the AI reads this many characters at most (owner,
# 2026-11-05: «ΣΩΣΤΑ», to the AI reading the description too): a need a shop states there
# ("low noise 49 dB", "ages 6-10") is found, which the engine's filters never read
# (`search_selection._FILTER_FIELDS`: title, type and brand).
DESCRIPTION_CHARACTERS = 400
# The feed's columns a description is read from, the first one given.
_DESCRIPTION_COLUMNS = ("description", "product_short_description")
_TAG = re.compile(r"<[^>]+>")

# The buyer's judgements in English. The engine sets apart only the Greek ones
# (`product_concepts._JUDGEMENT_QUALIFIERS`) and reads these as words to match, so a
# search for "best power bank" says "PicWise could not match: best". They are never
# asked about: what is "best" or "good" is not in a title, and PicWise does not judge it.
_ENGLISH_JUDGEMENTS = frozenset(
    """
    best better good great nice top quality premium cheap cheaper cheapest budget
    affordable inexpensive expensive value popular reliable recommended perfect ideal
    excellent amazing decent fine
    """.split()
)
# Reason codes of an answer found by its words, not by a kind.
_FOUND_BY_WORDS = "provider_feed_selection_product_named_by_words"


@dataclass(frozen=True)
class Candidate:
    """One product of the answer as the AI reads it: a short number, never its link."""

    number: int
    product_id: str
    title: str
    brand: str
    price_text: str
    currency: str
    shop: str
    description: str = ""


@dataclass(frozen=True)
class ComplexSearch:
    """A search the AI is asked about: its words the engine could not match, and the
    products of the answer it reads."""

    search: str
    words: tuple[str, ...]
    kind_name: str
    fell_back: bool
    candidates: tuple[Candidate, ...]
    total: int
    kind_id: str = ""


def _key(text: str) -> str:
    return normalize_understanding_text(str(text or "")).strip()


def why_not_asked(search: str, resolution: Any) -> str:
    """Why the AI is not asked about this search ("" when it is): for the measure's
    report and the service's log."""
    if not str(getattr(resolution, "understood_concept_id", "") or ""):
        return "no kind understood"
    if _FOUND_BY_WORDS in tuple(getattr(resolution, "reason_codes", ()) or ()):
        return "answered by its words"
    if not _rows(resolution):
        return "no products"
    if not _unmatched(resolution):
        return "every word matched"
    if not _words(search, resolution):
        return "only judgements or a condition not matched"
    return ""


def clean_description(text: Any, limit: int = DESCRIPTION_CHARACTERS) -> str:
    """A shop's description as the AI reads it: no markup, one line, cut at a word."""
    plain = " ".join(html.unescape(_TAG.sub(" ", str(text or ""))).split())
    if len(plain) <= limit:
        return plain
    cut = plain[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:-") + " …"


def description_of(product: Any) -> str:
    """A feed product's own description (`ProviderProduct.raw`), cleaned; "" if none."""
    raw = getattr(product, "raw", None) or {}
    for column in _DESCRIPTION_COLUMNS:
        text = clean_description(raw.get(column))
        if text:
            return text
    return ""


def complex_search_of(
    search: str, resolution: Any, *, descriptions: Mapping[str, str] | None = None
) -> ComplexSearch | None:
    """The search as the AI is asked about it, or None when it is not complex.

    `resolution` is the live search resolver's answer (`resolve_live_search`), run with
    `shown=SHOWN_FOR_CANDIDATES` so that it holds the products the AI reads;
    `descriptions` gives each product's description by its id (`description_of`).
    """
    if why_not_asked(search, resolution):
        return None
    concept_id = str(getattr(resolution, "understood_concept_id", "") or "")
    unmatched = _unmatched(resolution)
    reading = understand_product_query(search)
    fallback_words = {_key(word) for word in tuple(reading.fallback_unmatched or ())}
    fell_back = bool(reading.fallback_concept_id) and any(_key(word) in fallback_words for word in unmatched)
    kind_id = str(reading.fallback_concept_id) if fell_back else concept_id
    concept = get_product_concepts_by_id().get(kind_id)
    kind_name = concept.primary_english if concept is not None else kind_id.replace("_", " ")
    candidates = tuple(
        Candidate(
            number=number,
            product_id=str(row.get("provider_product_id") or "").strip(),
            title=" ".join(str(row.get("title") or "").split()),
            brand=" ".join(str(row.get("brand") or "").split()),
            # As every price PicWise shows reads: the feed's price with its currency.
            price_text=format_price_display(row),
            currency=str(row.get("currency") or "").strip(),
            shop=" ".join(str(row.get("merchant_name") or "").split()),
            description=clean_description(
                (descriptions or {}).get(str(row.get("provider_product_id") or "").strip(), "")
            ),
        )
        for number, row in enumerate(_rows(resolution)[:MAX_CANDIDATES], start=1)
    )
    return ComplexSearch(
        search=" ".join(str(search or "").split()),
        words=_words(search, resolution),
        kind_name=kind_name,
        fell_back=fell_back,
        candidates=candidates,
        total=int(getattr(resolution, "provider_feed_total_count", 0) or 0),
        kind_id=kind_id,
    )


def _rows(resolution: Any) -> list[dict[str, Any]]:
    selected = tuple(getattr(resolution, "provider_feed_selected_products", ()) or ())
    more = tuple(getattr(resolution, "provider_feed_more_products", ()) or ())
    return [row for row in selected + more if isinstance(row, dict)]


def _unmatched(resolution: Any) -> tuple[str, ...]:
    terms = tuple(getattr(resolution, "provider_feed_unmatched_query_terms", ()) or ())
    return tuple(dict.fromkeys(str(term).strip() for term in terms if str(term).strip()))


def _words(search: str, resolution: Any) -> tuple[str, ...]:
    reading = understand_product_query(search)
    judgements = {_key(word) for word in tuple(reading.judgements or ())} | _ENGLISH_JUDGEMENTS
    condition = {_key(word) for word in read_condition_request(search).words}
    kept = []
    for term in _unmatched(resolution):
        parts = _key(term).split()
        if not parts or all(part in judgements for part in parts):
            continue
        if _key(term) in condition or all(part in condition for part in parts):
            continue
        kept.append(term)
    return tuple(kept)
