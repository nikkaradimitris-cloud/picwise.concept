"""What the search box suggests as the buyer types (step 4 of the price-first plan).

Owner, 2026-10-16: from the first letter, word suggestions that narrow with each letter
("l" -> laptop, lamp), and the likely word completed in faint letters. In practice, as
recorded in `docs/picwise_price_first_plan_2026-10-15.md` and
`docs/LANDING_PAGE_SPEC.md`:

- the suggestions are PicWise's own vocabulary: the names of the kinds it knows, in
  English and Greek, and a brand with a kind ("samsung smartphone");
- only a search that returns products from the connected shops is offered. A kind
  with no product in the feed is not, and neither is a brand alone, which names no
  product ("samsung" asks which product is meant);
- the larger first, so the first suggestions for "l" are the kinds with the most
  products.

Nothing here is a claim about the products: the list is the words that find them.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Mapping, Sequence

import re

from picwise_nlu.concept_understanding import (
    CATEGORY_FIELD_SEPARATOR,
    read_kind_word,
    understand_product_query,
)
from picwise_nlu.product_concepts import get_product_concepts_by_id

from .contracts import ProviderProduct
from .kind_choices import KindChoice
from .search_selection import (
    _FILTER_FIELDS,
    _KIND_MARKERS,
    _carries,
    _context_allows_member,
    _filter_units,
    _product_concepts,
    _product_search_fields,
    _word_forms,
)

# A brand with a kind is offered when the brand has at least this many products of
# that kind: one product is a shop's stray listing more often than a range.
_MIN_BRAND_KIND_PRODUCTS = 2
# The brand-with-kind suggestions kept, the largest first. The whole list travels to
# the browser once, and the caps keep it near 40 KB (about 12 KB compressed).
_MAX_BRAND_KIND_SUGGESTIONS = 400
# A shop's own name for a kind PicWise does not know -- a product type such as
# "Network Switches", or the last crumb of its category path such as "Rabbit Hutches"
# -- is offered when at least this many products would answer it, and the largest of
# them up to the cap.
_MIN_FEED_PHRASE_PRODUCTS = 3
_MAX_FEED_PHRASE_SUGGESTIONS = 800
_PHRASE_SPLIT_RE = re.compile(r"\s*(?:&|,|/|\band\b)\s*", flags=re.IGNORECASE)
_PHRASE_WORD_RE = re.compile(r"^[^\W\d_]+(?:[ -][^\W\d_]+){1,3}$")


@dataclass(frozen=True)
class SearchSuggestion:
    """One suggestion: the words put in the box, and how many products they find."""

    text: str
    products: int


def suggestion_key(text: str) -> str:
    """The form a suggestion is matched in: no accents, lower case, final sigma as σ.

    The page normalises what the buyer types the same way, so "λαπ" finds "λάπτοπ".
    """
    decomposed = unicodedata.normalize("NFD", str(text or ""))
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(stripped.lower().replace("ς", "σ").split())


def _same_name(left: str, right: str) -> bool:
    """Two names of one kind that differ only in their endings, as a singular and its
    plural do: "laptop" and "laptops", "φορητός υπολογιστής" and "φορητοί υπολογιστές"."""
    left_words, right_words = left.split(), right.split()
    if len(left_words) != len(right_words):
        return False
    for a, b in zip(left_words, right_words):
        common = 0
        for x, y in zip(a, b):
            if x != y:
                break
            common += 1
        if common < min(len(a), len(b)) - 2 or abs(len(a) - len(b)) > 3:
            return False
    return True


def _kind_names(concept_id: str) -> tuple[str, ...]:
    """The names a buyer would type for one kind, each once: no plural of a name kept,
    and no weak name, which is read in a search but is also an ordinary word."""
    concept = get_product_concepts_by_id().get(concept_id)
    if concept is None:
        return tuple()
    weak = set(concept.weak)
    kept: list[str] = []
    for name in concept.english + concept.greek:
        if name in weak or not name.strip():
            continue
        key = suggestion_key(name)
        if any(_same_name(key, suggestion_key(other)) for other in kept):
            continue
        kept.append(name)
    return tuple(kept)


def _reads_as(text: str, concept_id: str) -> bool:
    """Is this text read as that kind? A name the lexicon shares with another kind, or
    one the understanding reads otherwise, is not offered for it."""
    reading = understand_product_query(text)
    return bool(reading.understood) and reading.concept_id == concept_id


def _shop_phrases(product: ProviderProduct, fields: dict[str, str]) -> tuple[str, ...]:
    """The shop's own names for what this product is: the last crumb of its product
    type, else of its first category path, split where it lists two ("Dog Crates &
    Playpens"). Two to four words of letters only, lower case."""
    raw = product.raw if isinstance(product.raw, dict) else {}
    source = str(raw.get("product_type") or "")
    if not source.strip():
        category = fields.get("category", "")
        source = category.split(CATEGORY_FIELD_SEPARATOR)[0] if category else ""
    leaf = source.split(">")[-1]
    phrases = []
    for part in _PHRASE_SPLIT_RE.split(leaf):
        phrase = " ".join(part.lower().split())
        if _PHRASE_WORD_RE.match(phrase):
            phrases.append(phrase)
    return tuple(phrases)


def _answers_phrase(phrase: str, product: ProviderProduct, haystack: dict[tuple[str, ...], str]) -> bool:
    """Would a search for the phrase find this product: every word carried, and the
    phrase's last word what the product is (`read_kind_word`, as the word search reads it)?"""
    words = tuple(phrase.replace("-", " ").split())
    units = _filter_units(words, {})
    if not all(_carries(unit, haystack) for unit in units):
        return False
    raw = product.raw if isinstance(product.raw, dict) else {}
    return read_kind_word(
        str(raw.get("product_type") or ""), str(product.title or ""), _word_forms(words[-1])
    ).names


def build_search_suggestions(
    products: tuple[ProviderProduct, ...],
    *,
    choices: Mapping[str, Sequence[KindChoice]] | None = None,
) -> tuple[SearchSuggestion, ...]:
    """The suggestions for one catalogue: the products a search can show.

    `products` must be what a search reads: the feed's eligible products that are new.
    A kind counts the products a search for it would list, by the same reading
    (`_product_concepts`, `_context_allows_member`), so "bed" is not offered on the
    strength of dog beds alone. `choices` are the general kinds' choices worked out for
    the same products (`kind_choices.build_kind_choices`): each is offered too, so that
    typing "cable" lists "hdmi cable" and "extension cable" after it (owner, 2026-10-28:
    the box completes which cable is meant).
    """
    kind_counts: dict[str, int] = {}
    brand_kind_counts: dict[tuple[str, str], int] = {}
    brand_names: dict[str, str] = {}
    phrase_counts: dict[str, int] = {}
    for product in products:
        fields = _product_search_fields(product)
        haystack = {_FILTER_FIELDS: " ".join(fields[name] for name in _FILTER_FIELDS if fields.get(name))}
        for phrase in _shop_phrases(product, fields):
            if _answers_phrase(phrase, product, haystack):
                phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        kinds = _product_concepts(product, fields)
        brand = " ".join(str(product.brand or "").split())
        for concept_id in kinds - _KIND_MARKERS:
            if not _context_allows_member(kinds, concept_id, tuple(concept_id.split("_"))):
                continue
            kind_counts[concept_id] = kind_counts.get(concept_id, 0) + 1
            if brand:
                key = (brand.lower(), concept_id)
                brand_kind_counts[key] = brand_kind_counts.get(key, 0) + 1
                brand_names.setdefault(brand.lower(), brand)

    suggestions: dict[str, SearchSuggestion] = {}

    def offer(text: str, count: int) -> None:
        key = suggestion_key(text)
        if key and (key not in suggestions or suggestions[key].products < count):
            suggestions[key] = SearchSuggestion(text=text, products=count)

    for concept_id, count in kind_counts.items():
        for name in _kind_names(concept_id):
            if _reads_as(name, concept_id):
                offer(name, count)

    pairs = sorted(
        (
            (count, brand, concept_id)
            for (brand, concept_id), count in brand_kind_counts.items()
            if count >= _MIN_BRAND_KIND_PRODUCTS
        ),
        key=lambda row: (-row[0], row[1], row[2]),
    )
    kept_pairs = 0
    for count, brand, concept_id in pairs:
        if kept_pairs >= _MAX_BRAND_KIND_SUGGESTIONS:
            break
        concept = get_product_concepts_by_id().get(concept_id)
        if concept is None or not concept.primary_english:
            continue
        text = f"{brand_names[brand]} {concept.primary_english}"
        if _reads_as(text, concept_id):
            offer(text, count)
            kept_pairs += 1

    phrases = sorted(
        ((count, phrase) for phrase, count in phrase_counts.items() if count >= _MIN_FEED_PHRASE_PRODUCTS),
        key=lambda row: (-row[0], row[1]),
    )
    # The same name in its singular and plural is offered once ("memory module" and
    # the shop's "memory modules"), grouped by the start of the first word.
    by_start: dict[str, list[str]] = {}
    for key in suggestions:
        by_start.setdefault(key.split()[0][:4], []).append(key)
    for count, phrase in phrases[:_MAX_FEED_PHRASE_SUGGESTIONS]:
        # One read as a kind with no product here would find nothing.
        reading = understand_product_query(phrase)
        if reading.understood and reading.concept_id not in kind_counts:
            continue
        key = suggestion_key(phrase)
        bucket = by_start.setdefault(key.split()[0][:4], [])
        if any(_same_name(key, other) for other in bucket):
            continue
        offer(phrase, count)
        bucket.append(key)
    for kind_choices in (choices or {}).values():
        for choice in kind_choices:
            key = suggestion_key(choice.text)
            bucket = by_start.setdefault(key.split()[0][:4], [])
            if any(_same_name(key, other) for other in bucket if other != key):
                continue
            offer(choice.text, choice.products)
            if key not in bucket:
                bucket.append(key)

    return tuple(
        sorted(suggestions.values(), key=lambda row: (-row.products, suggestion_key(row.text)))
    )
