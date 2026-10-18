from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

from picwise_nlu import normalize_query
from picwise_nlu.concept_understanding import (
    ACCESSORY_MARKER,
    CAMPING_MARKER,
    CATEGORY_FIELD_SEPARATOR,
    PET_MARKER,
    UNCERTAIN_MARKER,
    ConceptReading,
    annotate_product_concepts,
    normalize_spec_text,
    KindWordReading,
    read_kind_word,
    product_text_names_concept,
    query_allows_context,
    read_condition_request,
    strip_accents_if_needed,
    understand_product_query,
    words_after_product_name,
)
from picwise_nlu.product_concepts import broader_concepts, get_product_concepts_by_id, get_qualifiers
from picwise_taxonomy.comparison_rules import comparison_rule

from .contracts import FeedAvailabilityContext, OfferHealth, ProviderProduct
from .normalization import extract_merchant_name
from .decision_labels import parse_price_amount
from .product_description import has_sufficient_description
from .product_specs import read_product_specs
from .product_identity import same_product_key
from .product_condition import (
    non_new_condition,
    product_text_for_condition,
    stated_condition,
)
from .offer_health import (
    build_feed_availability_context,
    evaluate_product_eligibility,
    evaluate_recommendation_confidence,
)

_TITLE_WEIGHT = 100
_PRODUCT_TYPE_WEIGHT = 55
_CATEGORY_WEIGHT = 40
_BRAND_WEIGHT = 35
_KEYWORD_WEIGHT = 20
_DESCRIPTION_WEIGHT = 5
_PHRASE_IN_TITLE_BONUS = 150
_ALL_TOKENS_IN_TITLE_BONUS = 80
_PRODUCT_TYPE_IN_TITLE_BONUS = 60
_COMPLETE_PRODUCT_BONUS = 25
_NOT_ACCESSORY_BONUS = 40
_ACCESSORY_PENALTY = 220
_STRONG_MATCH_MIN_SCORE = 280
_PRODUCT_TYPE_ALIGN_BONUS = 130
_PRODUCT_TYPE_CONFLICT_PENALTY = 320
_DESCRIPTION_MAX_LEN = 500
_MIN_TOKEN_LEN = 2

_ACCESSORY_TERMS = frozenset(
    {
        "accessories",
        "accessory",
        "bag",
        "bags",
        "filter",
        "filters",
        "cloth",
        "mop",
        "replacement",
        "spare",
        "parts",
        "kit",
        "tool kit",
        "nozzle",
        "filament",
        "adapter",
        "docking station",
        "lens",
        "cable",
        "battery",
        "sensor",
        "cover",
        "case",
        "stand",
        "bracket",
        "brush",
        "brushes",
        "mount",
    }
)
_ACCESSORY_FOR_PRODUCT_PENALTY = 260
_ACCESSORY_PACK_PREFIX_RE = re.compile(r"^\d+\s*(?:pcs|pc|pack|pieces?)\b", flags=re.IGNORECASE)

_DEDUPE_PUNCT_RE = re.compile(r"[^\w\s]+", flags=re.UNICODE)

_WEAK_PRODUCT_TYPE_VALUES = frozenset(
    {
        "not categorized",
        "uncategorized",
        "other",
        "general",
        "misc",
        "miscellaneous",
    }
)

_GENERIC_CATEGORY_VALUES = frozenset(
    {
        "computers",
        "computer",
        "electronics",
        "electronic",
        "general",
        "other",
        "misc",
        "miscellaneous",
        "default",
        "uncategorized",
        "not categorized",
    }
)

_QUERY_INTENT_ALLOWED_PRODUCT_TYPES: dict[str, tuple[str, ...]] = {
    "laptop": ("laptops",),
    "mouse": ("mice",),
    "monitor": ("computer monitors",),
    "headphones": ("headphones & headsets",),
    "headset": ("headphones & headsets",),
    "webcam": ("webcams",),
    "webcams": ("webcams",),
    "keyboard": ("keyboards",),
    "keyboards": ("keyboards",),
    "printer": (
        "multifunction printers",
        "laser printers",
        "inkjet printers",
        "label printers",
        "large format printers",
        "photo printers",
        "dot matrix printers",
        "plastic card printers",
        "3d printers",
    ),
    "printers": (
        "multifunction printers",
        "laser printers",
        "inkjet printers",
        "label printers",
        "large format printers",
        "photo printers",
        "dot matrix printers",
        "plastic card printers",
        "3d printers",
    ),
    "toner": ("toner cartridges",),
    "hub": ("hubs", "usb hubs", "docking stations"),
    "docking": ("laptop docks & port replicators",),
}

_QUERY_PHRASE_ALLOWED_PRODUCT_TYPES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("docking station", ("laptop docks & port replicators",)),
    ("ink cartridge", ("ink cartridges",)),
    ("toner cartridge", ("toner cartridges",)),
    ("hp toner", ("toner cartridges",)),
    ("computer monitor", ("computer monitors",)),
    ("wireless keyboard", ("keyboards",)),
    ("27 inch monitor", ("computer monitors",)),
    ("office chair", ("office & computer chairs",)),
)


# Grammatical connectives carry no product signal. They are dropped from the required
# token set so a phrase like "power bank for iphone" is not held to the word "for".
_CONNECTIVE_TOKENS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "for",
        "from",
        "in",
        "into",
        "my",
        "of",
        "on",
        "or",
        "per",
        "the",
        "to",
        "with",
        "without",
        "gia",
        "kai",
        "me",
        "se",
    }
)


_MAX_RELAXABLE_TOKENS = 8


@dataclass(frozen=True)
class QueryTokenPlan:
    """The most specific reading of a query that this inventory can actually answer.

    A buyer's words are not all filters. "power bank for iphone" names a product and a
    need; "comfortable office chair" names a product and a preference. Requiring every
    word returned nothing whenever one of them did not appear in the feed text, so the
    buyer who described their need got less than the one who typed a bare noun. That
    inverts the promise the concept makes.

    Requiring none of them is equally wrong: "power bank" would then be answerable by a
    power drill. So the plan searches for the LARGEST set of the buyer's words that at
    least `max_products` products all satisfy, and reports the rest as words PicWise
    could not act on. The inventory decides which words are filters, not a hand-written
    list of qualifiers.

    Consequences worth knowing:

    - With enough matching stock nothing is dropped: four 20000mAh power banks means
      "20000mah" stays a filter.
    - Where stock cannot satisfy every word, the buyer gets the four closest choices
      plus an explicit note about the part that could not be matched, instead of a blank
      page.
    - `unmatched` is never silently discarded; the surface states it.
    """

    required: tuple[str, ...]
    unmatchable: tuple[str, ...]
    connectives: tuple[str, ...]
    ambiguous_product_families: tuple[str, ...] = field(default_factory=tuple)


def _query_token_candidates(tokens: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(token for token in tokens if token not in _CONNECTIVE_TOKENS)


def resolve_query_token_plan(
    tokens: tuple[str, ...],
    products: tuple[ProviderProduct, ...],
    *,
    max_products: int = 4,
    product_fields: tuple[dict[str, str], ...] | None = None,
) -> QueryTokenPlan:
    """Pick the largest subset of the query's words that `max_products` products satisfy.

    `product_fields` lets the caller hand over field text it has already built. Deriving
    it again here would double the per-query string work over the whole feed, which the
    PROJECT_RULES section 9 render budget cannot absorb on a real feed.
    """
    connectives = tuple(token for token in tokens if token in _CONNECTIVE_TOKENS)
    candidates = _query_token_candidates(tokens)
    if not candidates:
        return QueryTokenPlan(required=tuple(), unmatchable=tuple(), connectives=connectives)

    # Words past the cap stay required: the subset search is exponential in the number
    # of relaxable words, and queries this long are not the case worth relaxing for.
    relaxable = candidates[:_MAX_RELAXABLE_TOKENS]
    always_required = candidates[_MAX_RELAXABLE_TOKENS:]

    # One pass over the inventory: which of the relaxable words does each product match?
    # Support is counted in distinct products, not offers: four merchants selling one
    # phone are one product, and must not let a reading look like it fills four choices.
    support: dict[int, set[str]] = {}
    families: dict[int, set[str]] = {}
    field_rows = product_fields or tuple(
        _product_search_fields(product) for product in products
    )
    support_by_family: dict[tuple[int, str], set[str]] = {}
    for row_index, fields in enumerate(field_rows):
        # One joined text per product: this pass only asks whether a word appears at
        # all, so checking six fields separately multiplies the work over the feed for
        # no extra information.
        haystack = " ".join(value for value in fields.values() if value)
        mask = 0
        for index, token in enumerate(relaxable):
            if token and token in haystack:
                mask |= 1 << index
        if always_required and not all(
            token in haystack for token in always_required
        ):
            continue
        if not mask:
            # A product carrying none of the relaxable words supports no reading; every
            # count below asks about a non-empty subset of them.
            continue
        identity = (
            _product_identity_key(products[row_index]) if row_index < len(products) else ""
        ) or f"row:{row_index}"
        support.setdefault(mask, set()).add(identity)
        family = fields["product_type"] or fields["category"] or ""
        if family:
            families.setdefault(mask, set()).add(family)
        support_by_family.setdefault((mask, family), set()).add(identity)

    safe_max = max(1, int(max_products))

    def _distinct_up_to(groups: list[set[str]], limit: int) -> int:
        # Only thresholds are ever asked ("at least four?", "any?"), so stop counting
        # once the answer is known instead of building the union over a whole feed.
        seen: set[str] = set()
        for group in groups:
            for identity in group:
                seen.add(identity)
                if len(seen) >= limit:
                    return len(seen)
        return len(seen)

    def satisfying(subset_mask: int, limit: int = safe_max) -> int:
        return _distinct_up_to(
            [ids for mask, ids in support.items() if mask & subset_mask == subset_mask],
            limit,
        )

    def families_for(subset_mask: int) -> set[str]:
        return {
            family
            for mask, names in families.items()
            if mask & subset_mask == subset_mask
            for family in names
        }

    def satisfying_within(subset_mask: int, allowed_families: set[str]) -> int:
        return _distinct_up_to(
            [
                ids
                for (mask, family), ids in support_by_family.items()
                if mask & subset_mask == subset_mask and family in allowed_families
            ],
            safe_max,
        )

    full_mask = (1 << len(relaxable)) - 1

    def plan_for(mask: int, *, ambiguous: tuple[str, ...] = tuple()) -> QueryTokenPlan:
        return QueryTokenPlan(
            required=tuple(
                token for index, token in enumerate(relaxable) if mask & (1 << index)
            )
            + always_required,
            unmatchable=tuple(
                token for index, token in enumerate(relaxable) if not mask & (1 << index)
            ),
            connectives=connectives,
            ambiguous_product_families=ambiguous,
        )

    if satisfying(full_mask) >= safe_max:
        return plan_for(full_mask)

    # The fullest reading, even when it matches too few products, names the product
    # family the buyer asked about. "laptop bag" matches one bag: relaxing to "laptop"
    # would answer with laptops, which is not what was asked. So when the full reading
    # matches anything at all, relaxation may only add more of that same family.
    anchor_families = families_for(full_mask) if satisfying(full_mask, 1) > 0 else set()

    def support_for(subset_mask: int) -> int:
        if anchor_families:
            return satisfying_within(subset_mask, anchor_families)
        return satisfying(subset_mask)

    # Relax to the most specific reading the inventory can answer with a full set.
    best_size = 0
    best_masks: list[int] = []
    for subset_mask in range(full_mask, 0, -1):
        if subset_mask & full_mask != subset_mask:
            continue
        if support_for(subset_mask) < safe_max:
            continue
        size = bin(subset_mask).count("1")
        if size > best_size:
            best_size, best_masks = size, [subset_mask]
        elif size == best_size:
            best_masks.append(subset_mask)
    if not best_masks:
        return plan_for(full_mask)

    if len(best_masks) > 1:
        # Equally specific readings. If they point at different product families the
        # query is genuinely ambiguous after relaxation -- answering it would mean
        # guessing which product the buyer meant, and showing car batteries to someone
        # who asked about a smartphone is worse than showing nothing. Report the
        # ambiguity instead of picking one.
        families = [families_for(mask) for mask in best_masks]
        shared = set.intersection(*families) if families else set()
        if not shared:
            ambiguous = tuple(
                sorted({name for family in families for name in family})
            )[:8]
            return plan_for(full_mask, ambiguous=ambiguous)

    best_masks.sort(key=lambda mask: (-support_for(mask), mask))
    return plan_for(best_masks[0])


@dataclass(frozen=True)
class ProviderProductSelectionResult:
    status: str
    matched_count: int = 0
    strong_matched_count: int = 0
    selected_products: tuple[ProviderProduct, ...] = field(default_factory=tuple)
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    unmatched_query_terms: tuple[str, ...] = field(default_factory=tuple)
    ambiguous_product_families: tuple[str, ...] = field(default_factory=tuple)
    required_query_terms: tuple[str, ...] = field(default_factory=tuple)
    # Set when the product the buyer means was understood as a concept. Every selected
    # product is then an instance of that concept, whatever words the feed uses for it.
    understood_concept: str = ""
    # What the buyer asked for, restated in the feed's words: "πλυντηριο 8 κιλα" is
    # "washing machine 8kg". Recommendation scoring reads this, not the raw query.
    effective_query: str = ""
    # The filters (specs, preferences, brands) the selection required every product to
    # carry. Unlike `required_query_terms` it excludes the product name itself, which
    # concept membership already guarantees.
    required_filter_terms: tuple[str, ...] = field(default_factory=tuple)
    # Filters some but not all of the selected products carry, as (buyer's words,
    # how many of the selected carry it). Stated as "2 of 4" rather than "not matched".
    partially_matched_terms: tuple[tuple[str, int], ...] = field(default_factory=tuple)
    # The buyer's own words asking for a non-new item, when they asked. Empty means
    # they did not, and then nothing the feed calls non-new was a candidate at all.
    condition_request: tuple[str, ...] = field(default_factory=tuple)
    # A second four, for the kinds of product where there is no "best" and the buyer
    # is choosing by taste or by fit. Owner instruction (2026-10-12): those get a "see
    # more" button. Empty for every other kind, and empty when the feed has no second
    # four to give -- the button is only offered when there is something behind it.
    more_products: tuple[ProviderProduct, ...] = field(default_factory=tuple)
    # The feed availability context the selection judged card eligibility against. The
    # exported card fields and the recommendation must read the same one.
    feed_availability_context: FeedAvailabilityContext | None = None
    # Price first (owner, 2026-10-15 and 2026-10-16). When set, `selected_products` is
    # the first page (the Recommended, then the cheapest) and `more_products` the
    # products "More" has opened after it, in the order shown; `total_count` is how
    # many products the whole answer holds, for the counter "4 of 45".
    price_first: bool = False
    total_count: int = 0
    # The Recommended, chosen over the whole answer, or "" when there is none.
    recommended_product_id: str = ""
    # Why there is a Recommended or not: "recommended", "no_product_code" (no product
    # of the answer carries an EAN/GTIN) or "too_few_products" (no middle to take).
    recommendation_status: str = ""
    # First-page products that are the cheap end of the answer: priced at or below the
    # Recommended or, when there is none, at or below the middle price.
    cheapest_product_ids: tuple[str, ...] = field(default_factory=tuple)
    # (product id, shops) for shown products sold by more than one shop: the card
    # says "Lowest price of N shops".
    shop_counts: tuple[tuple[str, int], ...] = field(default_factory=tuple)
    # (product id, place in the whole answer by price) for shown products: 1 is the
    # cheapest, and products at one price share a place.
    price_ranks: tuple[tuple[str, int], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "price_first": self.price_first,
            "total_count": self.total_count,
            "recommended_product_id": self.recommended_product_id,
            "recommendation_status": self.recommendation_status,
            "cheapest_product_ids": list(self.cheapest_product_ids),
            "shop_counts": [list(row) for row in self.shop_counts],
            "price_ranks": [list(row) for row in self.price_ranks],
            "partially_matched_terms": [list(row) for row in self.partially_matched_terms],
            "understood_concept": self.understood_concept,
            "effective_query": self.effective_query,
            "required_filter_terms": list(self.required_filter_terms),
            "status": self.status,
            "matched_count": self.matched_count,
            "strong_matched_count": self.strong_matched_count,
            "selected_count": len(self.selected_products),
            "more_count": len(self.more_products),
            "reason_codes": list(self.reason_codes),
            "unmatched_query_terms": list(self.unmatched_query_terms),
            "condition_request": list(self.condition_request),
            "ambiguous_product_families": list(self.ambiguous_product_families),
            "required_query_terms": list(self.required_query_terms),
            "selected_products": [
                provider_product_to_backend_dict(
                    product, feed_ctx=self.feed_availability_context
                )
                for product in self.selected_products
            ],
        }


def mask_provider_product_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return "<invalid-url>"
    path = parsed.path or "/"
    if len(path) > 24:
        path = f"{path[:20]}...{path[-1]}"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _category_evidence_for_product(product: ProviderProduct) -> dict[str, str]:
    raw = product.raw if isinstance(product.raw, dict) else {}
    evidence: dict[str, str] = {}
    for key in (
        "merchant_product_category_path",
        "merchant_category",
        "category_name",
        "merchant_product_second_category",
        "merchant_product_third_category",
    ):
        value = str(raw.get(key) or "").strip()
        if value:
            evidence[key] = value
    category_text = str(product.category_text or "").strip()
    if category_text:
        evidence["category_text"] = category_text
    return evidence


def _feed_condition(raw: dict[str, Any]) -> str:
    """The item condition as the feed row states it ("new", "refurbished"), or ""."""
    return stated_condition(raw)


def product_non_new_condition(product: ProviderProduct) -> str:
    """What the feed said to call this product not new, or "".

    Owner decision (2026-10-10): a refurbished or used product is shown only to a buyer
    who asked for that condition. This is the gate that decision runs through, and the
    cards read the same module, so a hidden product and a disclosed one are judged by
    one rule.
    """
    raw = product.raw if isinstance(product.raw, dict) else {}
    stated = _feed_condition(raw)
    if stated:
        # The column spoke; the product's own text is not read, and not even built:
        # this runs once per product of the feed on every search.
        return non_new_condition(condition=stated)
    return non_new_condition(
        text=product_text_for_condition(
            (product.title, raw.get("product_type"), product.category_text)
        )
    )


def _verified_purchasable_from_offer_health(offer_health: OfferHealth) -> bool:
    purch = offer_health.purchasability
    return (
        purch.purchasability_state == "purchasable"
        and purch.verification_confidence in {"high", "strong", "verified"}
    )


def provider_product_to_backend_dict(
    product: ProviderProduct,
    *,
    feed_ctx: FeedAvailabilityContext | None = None,
) -> dict[str, Any]:
    """Export one product's card fields.

    `feed_ctx` must be the context the selection used. Without it the product is judged
    against itself alone, where no column can vary, so availability reads as `weak` even
    for a feed whose stock column is informative.
    """
    if feed_ctx is None:
        feed_ctx = build_feed_availability_context((product,))
    product_eligibility = evaluate_product_eligibility(product, feed_ctx=feed_ctx)
    offer_health = product_eligibility.offer_health
    raw = product.raw if isinstance(product.raw, dict) else {}
    brand = str(product.brand or "").strip()
    currency = str(product.currency or "").strip()
    product_type = str(raw.get("product_type") or "").strip()
    payload: dict[str, Any] = {
        "provider_key": str(product.provider_key or "").strip(),
        "provider_product_id": str(product.provider_product_id or "").strip(),
        "title": str(product.title or "").strip(),
        "price_text": str(product.price_text or "").strip(),
        "availability_text": str(product.availability_text or "").strip(),
        "image_url": str(product.image_url or "").strip(),
        "product_url": str(product.product_url or "").strip(),
        "product_url_masked": mask_provider_product_url(product.product_url),
        "card_eligible": product_eligibility.card_eligible,
        "card_eligibility_reason_codes": list(product_eligibility.reason_codes),
        "recommendation_confidence_ceiling": product_eligibility.recommendation_confidence_ceiling,
        "recommendation_confidence": product_eligibility.recommendation_confidence_ceiling,
        "brand": brand or None,
        "currency": currency or None,
        "merchant_name": extract_merchant_name(raw) or None,
        "condition": _feed_condition(raw) or None,
        # Whether the shop sent a description; a card without one says so (owner,
        # 2026-10-18), since it is shown all the same.
        "has_description": has_sufficient_description(raw, title=product.title),
        "verified_purchasable": False,
    }
    if product_type:
        payload["product_type"] = product_type
        payload["product_type_evidence"] = product_type
    category_evidence = _category_evidence_for_product(product)
    if category_evidence:
        payload["category_evidence"] = category_evidence
    if offer_health is not None:
        payload.update(offer_health.to_dict())
        payload["verified_purchasable"] = _verified_purchasable_from_offer_health(offer_health)
        if offer_health.purchasability.purchasability_state == "purchasability_unknown":
            payload["verified_purchasable"] = False
    return payload


def _tokenize_query(query: str) -> tuple[str, ...]:
    normalized = normalize_query(str(query or ""))
    if not normalized:
        return tuple()
    return tuple(
        token
        for token in normalized.split()
        if len(token) >= _MIN_TOKEN_LEN
    )


def _is_condition_request_token(token: str, condition_words: set[str]) -> bool:
    """Was this feed-facing token read as (part of) a request for a non-new item?

    The understanding layer splits on hyphens, the feed-facing normalisation keeps
    them, so "pre-owned" arrives as one token for two read words.
    """
    if not condition_words:
        return False
    words = strip_accents_if_needed(token.lower()).replace("-", " ").replace("/", " ").split()
    return bool(words) and all(word in condition_words for word in words)


def _normalize_dedupe_title(title: str) -> str:
    collapsed = " ".join(str(title or "").split()).strip().lower()
    if not collapsed:
        return ""
    return _DEDUPE_PUNCT_RE.sub(" ", collapsed)


def _is_generic_category(value: str) -> bool:
    collapsed = " ".join(str(value or "").split()).strip().lower()
    return collapsed in _GENERIC_CATEGORY_VALUES


def _is_weak_product_type(value: str) -> bool:
    collapsed = " ".join(str(value or "").split()).strip().lower()
    return not collapsed or collapsed in _WEAK_PRODUCT_TYPE_VALUES


def _resolve_allowed_product_types(
    normalized_query: str,
    tokens: tuple[str, ...],
) -> tuple[str, ...]:
    allowed: list[str] = []
    normalized = str(normalized_query or "").strip().lower()
    for phrase, product_types in _QUERY_PHRASE_ALLOWED_PRODUCT_TYPES:
        if phrase in normalized:
            allowed.extend(product_types)
    for token in tokens:
        mapped = _QUERY_INTENT_ALLOWED_PRODUCT_TYPES.get(token)
        if mapped:
            allowed.extend(mapped)
    return tuple(dict.fromkeys(product_type.lower() for product_type in allowed))


def _product_type_matches_allowed(
    normalized_type: str,
    allowed_product_types: tuple[str, ...],
) -> bool:
    if not normalized_type:
        return False
    if normalized_type in allowed_product_types:
        return True
    return any(allowed == normalized_type for allowed in allowed_product_types)


def _product_type_names_the_whole_query(
    normalized_type: str,
    tokens: tuple[str, ...],
) -> bool:
    """True when the feed's own product type contains every query token.

    The intent map keys on single tokens, so a token can be mapped to the wrong
    product type when surrounding words change which product is meant: "monitor"
    maps to computer monitors, which made "blood pressure monitor" and "baby
    monitor" collide with their own correct feed type and take the conflict
    penalty. When the feed's own categorisation already names the whole query, the
    feed is the better authority and the mapped hint must not override it.

    Only multi-token queries qualify. A single token matching a broader type is
    exactly the accessory case the penalty exists for -- "laptop" must not be
    satisfied by "Laptop Cases & Bags" -- so single-token queries are left to the
    existing rules.
    """
    if len(tokens) < 2 or not normalized_type:
        return False
    # Substring, not whole word: feed product types are plural ("Blood Pressure
    # Monitors") while queries are singular ("blood pressure monitor"). Requiring
    # every token keeps this tight enough.
    return all(_token_matches_field(token, normalized_type) for token in tokens)


def _product_type_alignment_adjustment(
    product_type: str,
    *,
    allowed_product_types: tuple[str, ...],
    query_seeks_accessory: bool,
    tokens: tuple[str, ...] = (),
) -> int:
    normalized_type = " ".join(str(product_type or "").split()).strip().lower()
    if _is_weak_product_type(normalized_type):
        return 0
    if not allowed_product_types:
        return 0
    if _product_type_matches_allowed(normalized_type, allowed_product_types):
        return _PRODUCT_TYPE_ALIGN_BONUS
    if _product_type_names_the_whole_query(normalized_type, tokens):
        return _PRODUCT_TYPE_ALIGN_BONUS
    if query_seeks_accessory:
        return 0
    return -_PRODUCT_TYPE_CONFLICT_PENALTY


def _build_secondary_category_text(raw: dict[str, Any], product: ProviderProduct) -> str:
    parts: list[str] = []
    for key in (
        "merchant_product_category_path",
        "merchant_product_second_category",
        "merchant_product_third_category",
    ):
        value = str(raw.get(key) or "").strip()
        if value:
            parts.append(value)

    for key in ("merchant_category", "category_name"):
        value = str(raw.get(key) or "").strip()
        if value and not _is_generic_category(value):
            parts.append(value)

    category_text = str(product.category_text or "").strip()
    if category_text and not _is_generic_category(category_text):
        parts.append(category_text)

    # Each field is its own breadcrumb. Joined with a bare space, the last shelf of one
    # ran into the first of the next ("console tables home & garden") and the kind
    # reader could not read either shelf.
    return CATEGORY_FIELD_SEPARATOR.join(part.strip().lower() for part in parts if part.strip())


def _product_search_fields(product: ProviderProduct) -> dict[str, str]:
    raw = product.raw if isinstance(product.raw, dict) else {}
    product_type = str(raw.get("product_type") or "").strip()
    description = str(raw.get("description") or "").strip()
    if len(description) > _DESCRIPTION_MAX_LEN:
        description = ""

    # Accents are stripped and "<number> <unit>" is fused ("8 kg" -> "8kg") so feed
    # text meets the query in the same form the query normalisation produces.
    return {
        "title": normalize_spec_text(strip_accents_if_needed(str(product.title or "").strip().lower())),
        "product_type": strip_accents_if_needed(product_type.lower()),
        "category": strip_accents_if_needed(_build_secondary_category_text(raw, product)),
        "brand": strip_accents_if_needed(str(product.brand or "").strip().lower()),
        "keywords": normalize_spec_text(strip_accents_if_needed(str(raw.get("keywords") or "").strip().lower())),
        "description": strip_accents_if_needed(description.lower()),
    }


def _token_matches_field(token: str, field_text: str) -> bool:
    if not token or not field_text:
        return False
    return token in field_text


def _word_in_text(word: str, text: str) -> bool:
    if not word or not text:
        return False
    pattern = rf"\b{re.escape(word)}\b"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def _accessory_term_pattern(term: str) -> re.Pattern[str]:
    # Whole words, with the plural: "cable" and "cables", "battery" and "batteries" --
    # but not "stand" inside "standard" or "kit" inside "kitchen", which put a real
    # power bank or stand mixer in the accessory penalty.
    stem = re.escape(term)
    plural = f"{re.escape(term[:-1])}ies|" if term.endswith("y") else ""
    return re.compile(rf"\b(?:{plural}{stem}(?:s|es)?)\b")


_ACCESSORY_TERM_PATTERNS = tuple(
    _accessory_term_pattern(term) for term in sorted(_ACCESSORY_TERMS)
)
# What follows these in a title is what comes in the box: "Power Bank with USB-C Cable"
# is a power bank, not a cable.
_INCLUDED_ITEMS_RE = re.compile(r"\s(?:with|incl\.?|including|plus|\+)\s")


def _accessory_terms_in(text: str) -> int:
    return sum(1 for pattern in _ACCESSORY_TERM_PATTERNS if pattern.search(text))


def _query_seeks_accessory(tokens: tuple[str, ...], normalized_query: str) -> bool:
    if any(token in _ACCESSORY_TERMS for token in tokens):
        return True
    normalized = str(normalized_query or "").strip().lower()
    return _accessory_terms_in(normalized) > 0


def _title_accessory_penalty(
    title: str,
    *,
    normalized_query: str,
    query_seeks_accessory: bool,
    concept_id: str = "",
) -> int:
    """How far a title reads as an accessory rather than the product searched for.

    `concept_id` is the kind of product the candidate is already verified to be. When
    the title names that kind with no accessory or part word after the name, an
    accessory word before the name is its type ("Filter Coffee Machine", "Battery Lawn
    Mower") and is not counted.
    """
    if query_seeks_accessory or not title:
        return 0
    main_product_text = _INCLUDED_ITEMS_RE.split(title, maxsplit=1)[0]
    accessory_terms = _accessory_terms_in(main_product_text)
    if accessory_terms and concept_id:
        after_name = words_after_product_name(main_product_text, concept_id)
        if after_name is not None and not _accessory_terms_in(after_name):
            # Every accessory word stands before the name or inside it: it is the type.
            accessory_terms = 0
    penalty = _ACCESSORY_PENALTY * accessory_terms
    if _ACCESSORY_PACK_PREFIX_RE.search(title):
        penalty += _ACCESSORY_PENALTY
    if normalized_query and normalized_query in title and " for " in title:
        for_index = title.find(" for ")
        phrase_index = title.find(normalized_query)
        if phrase_index > for_index:
            penalty += _ACCESSORY_FOR_PRODUCT_PENALTY
    return penalty


def _product_completeness_bonus(product: ProviderProduct) -> int:
    bonus = 0
    if str(product.image_url or "").strip():
        bonus += 8
    if str(product.product_url or "").strip():
        bonus += 6
    if str(product.price_text or "").strip():
        bonus += 6
    if str(product.availability_text or "").strip():
        bonus += 5
    return bonus if bonus == 25 else 0


def _score_product_for_tokens(
    product: ProviderProduct,
    tokens: tuple[str, ...],
    *,
    normalized_query: str,
    query_seeks_accessory: bool,
    scoring_tokens: tuple[str, ...] | None = None,
    fields: dict[str, str] | None = None,
    concept_verified: bool = False,
    concept_id: str = "",
) -> tuple[int, int, int, str, str] | None:
    """Rank one product. `tokens` must all match; `scoring_tokens` only add points.

    The two differ when a query carries words this inventory cannot be filtered by:
    those words no longer exclude a product, but a product that does mention them still
    scores higher, so the closest answer to the buyer's actual phrasing wins.
    `concept_id` names the kind a concept-verified product was verified as.
    """
    if fields is None:
        fields = _product_search_fields(product)
    score_tokens = scoring_tokens or tokens
    allowed_product_types = _resolve_allowed_product_types(normalized_query, score_tokens)
    matched_tokens = 0
    matched_token_set: set[str] = set()
    score = 0
    title_matches = 0
    category_matches = 0

    for token in score_tokens:
        token_matched = False
        if _token_matches_field(token, fields["title"]):
            score += _TITLE_WEIGHT
            title_matches += 1
            token_matched = True
        if fields["product_type"] and _token_matches_field(token, fields["product_type"]):
            score += _PRODUCT_TYPE_WEIGHT
            category_matches += 1
            token_matched = True
        if _token_matches_field(token, fields["category"]):
            score += _CATEGORY_WEIGHT
            category_matches += 1
            token_matched = True
        if fields["brand"] and _token_matches_field(token, fields["brand"]):
            score += _BRAND_WEIGHT
            token_matched = True
        if _token_matches_field(token, fields["keywords"]):
            score += _KEYWORD_WEIGHT
            token_matched = True
        if fields["description"] and _token_matches_field(token, fields["description"]):
            score += _DESCRIPTION_WEIGHT
            token_matched = True
        if token_matched:
            matched_tokens += 1
            matched_token_set.add(token)

    # Every required word must match. Words this inventory cannot be filtered by are
    # not in `tokens`, so they add points above but never exclude.
    if any(token not in matched_token_set for token in tokens):
        return None

    normalized = str(normalized_query or "").strip().lower()
    if normalized and normalized in fields["title"]:
        score += _PHRASE_IN_TITLE_BONUS
    if tokens and title_matches >= len(tokens):
        score += _ALL_TOKENS_IN_TITLE_BONUS
    if category_matches > 0:
        score += _CATEGORY_WEIGHT // 2
    if tokens and _word_in_text(tokens[-1], fields["title"]):
        score += _PRODUCT_TYPE_IN_TITLE_BONUS

    raw = product.raw if isinstance(product.raw, dict) else {}
    product_type = str(raw.get("product_type") or "").strip()
    type_alignment = _product_type_alignment_adjustment(
        product_type,
        allowed_product_types=allowed_product_types,
        query_seeks_accessory=query_seeks_accessory,
        tokens=tokens,
    )
    if concept_verified:
        # The product is already known to be the kind the buyer asked for. The
        # word-level type hints exist to establish exactly that, and on a feed that
        # names its types in Greek they would reject every correct product.
        type_alignment = max(type_alignment, 0)
    elif (
        allowed_product_types
        and product_type
        and not _is_weak_product_type(product_type)
        and type_alignment < 0
    ):
        return None
    score += type_alignment

    accessory_penalty = _title_accessory_penalty(
        fields["title"],
        normalized_query=normalized,
        query_seeks_accessory=query_seeks_accessory,
        concept_id=concept_id if concept_verified else "",
    )
    score -= accessory_penalty
    if accessory_penalty == 0 and not query_seeks_accessory:
        score += _NOT_ACCESSORY_BONUS
    score += _product_completeness_bonus(product)

    return (
        matched_tokens,
        score,
        title_matches,
        str(product.title or "").strip().lower(),
        str(product.provider_product_id or "").strip(),
    )


_GTIN_KEYS = ("gtin", "product_gtin", "ean", "upc", "isbn", "gtin13", "gtin12", "gtin14", "gtin8")
_MPN_KEYS = ("mpn", "manufacturer_part_number")
_GTIN_LENGTHS = frozenset({8, 12, 13, 14})


def _raw_value_any_case(raw: dict[str, Any], keys: tuple[str, ...]) -> str:
    # Feed headers vary in case ("product_GTIN", "EAN"); try the spellings directly
    # rather than lowering every column of every row on the request path.
    for key in keys:
        for spelling in (key, key.upper(), key.replace("gtin", "GTIN")):
            value = " ".join(str(raw.get(spelling) or "").split())
            if value:
                return value
    return ""


def _product_identity_key(product: ProviderProduct) -> str:
    """Which product this offer is for, independent of the merchant selling it.

    A GTIN (EAN, UPC, ISBN) names one product worldwide; brand plus manufacturer part
    number does when there is no GTIN. Without either the offer has no identity beyond
    its own id, and "" is returned. GTINs are padded to 14 digits, so the UPC-12 and
    EAN-13 forms of one code agree.
    """
    raw = product.raw if isinstance(product.raw, dict) else {}
    gtin = re.sub(r"\D", "", _raw_value_any_case(raw, _GTIN_KEYS))
    if len(gtin) in _GTIN_LENGTHS and gtin.strip("0"):
        return f"gtin:{gtin.zfill(14)}"
    mpn = _raw_value_any_case(raw, _MPN_KEYS).lower()
    brand = " ".join(str(product.brand or "").split()).lower()
    if mpn and brand:
        return f"mpn:{brand}|{mpn}"
    return ""


def _is_cheaper_offer(candidate: ProviderProduct, current: ProviderProduct) -> bool:
    if str(candidate.currency or "").strip().upper() != str(current.currency or "").strip().upper():
        return False
    candidate_price = parse_price_amount(candidate.price_text)
    current_price = parse_price_amount(current.price_text)
    if candidate_price is None or current_price is None:
        return False
    return candidate_price < current_price


def _dedupe_selected_products(
    ranked_products: list[tuple[tuple[int, int, int, str, str], ProviderProduct]],
) -> list[ProviderProduct]:
    """Distinct products in rank order, one offer each (see `_dedupe_ranked_products`)."""
    return [shown for _ranking, _ranked, shown in _dedupe_ranked_products(ranked_products)]


def _dedupe_ranked_products(
    ranked_products: list[tuple[tuple[int, int, int, str, str], ProviderProduct]],
) -> list[tuple[tuple[int, int, int, str, str], ProviderProduct, ProviderProduct]]:
    """Distinct products in rank order, one offer each, as (ranking, ranked offer, shown offer).

    Offers of the same product (same GTIN, or brand and part number) collapse into one
    choice: four merchants selling one phone were shown as four "different" choices,
    ranked lowest to highest price, while different phones were pushed out. The offer
    kept is the lowest price in the same currency, placed where the product first
    ranks; a tie keeps the better-ranked offer. The product keeps the ranking of that
    best-ranked offer.
    """
    identities = {id(product): _product_identity_key(product) for _, product in ranked_products}
    best_offer: dict[str, ProviderProduct] = {}
    for _, product in ranked_products:
        identity = identities[id(product)]
        if not identity:
            continue
        current = best_offer.get(identity)
        if current is None or _is_cheaper_offer(product, current):
            best_offer[identity] = product

    seen_ids: set[str] = set()
    seen_titles: set[str] = set()
    seen_identities: set[str] = set()
    selected: list[tuple[tuple[int, int, int, str, str], ProviderProduct, ProviderProduct]] = []

    for ranking, ranked_product in ranked_products:
        product = ranked_product
        identity = identities[id(ranked_product)]
        if identity:
            if identity in seen_identities:
                continue
            seen_identities.add(identity)
            product = best_offer[identity]
        product_id = str(product.provider_product_id or "").strip()
        dedupe_title = _normalize_dedupe_title(product.title)
        if product_id and product_id in seen_ids:
            continue
        if dedupe_title and dedupe_title in seen_titles:
            continue
        if product_id:
            seen_ids.add(product_id)
        if dedupe_title:
            seen_titles.add(dedupe_title)
        selected.append((ranking, ranked_product, product))

    return selected


def _token_in_substantive_fields(token: str, fields: dict[str, str]) -> bool:
    return bool(
        _token_matches_field(token, fields["title"])
        or (fields["product_type"] and _token_matches_field(token, fields["product_type"]))
        or _token_matches_field(token, fields["category"])
        or (fields["brand"] and _token_matches_field(token, fields["brand"]))
    )


def _merchant_text_evidence(fields: dict[str, str], tokens: tuple[str, ...]) -> tuple[int, int]:
    """Score points, and matched words, that come only from merchant free text.

    The keywords and description fields are marketing text each merchant fills in its
    own way. A word found there makes no difference to what the product is, so two
    products that differ only by it are substantially equivalent. Mirrors the keyword
    and description weights of `_score_product_for_tokens`.
    """
    points = 0
    free_text_only = 0
    for token in tokens:
        in_keywords = _token_matches_field(token, fields["keywords"])
        in_description = bool(fields["description"]) and _token_matches_field(
            token, fields["description"]
        )
        if in_keywords:
            points += _KEYWORD_WEIGHT
        if in_description:
            points += _DESCRIPTION_WEIGHT
        if (in_keywords or in_description) and not _token_in_substantive_fields(token, fields):
            free_text_only += 1
    return points, free_text_only


def _substantive_relevance(
    ranking: tuple[int, int, int, str, str],
    fields: dict[str, str],
    tokens: tuple[str, ...],
) -> tuple[int, int, int]:
    """(score, title matches, matched words) without the merchant free-text evidence."""
    matched_tokens, score, title_matches, _title_key, _product_id = ranking
    points, free_text_only = _merchant_text_evidence(fields, tokens)
    return (score - points, title_matches, matched_tokens - free_text_only)


def _spread_across_price(group: list[ProviderProduct], slots: int) -> list[ProviderProduct]:
    """Pick `slots` products from equivalent ones, spread across their price range.

    Owner decision (2026-10-08): when the ranking leaves more than four substantially
    equivalent products, the four shown are the cheapest, the dearest and two in
    between, so a buyer sees the range rather than four neighbours. Restated by the
    owner on 2026-10-12 as four **different** price zones, cheapest first.

    That restatement is a correction, and it was earned by measurement. Spreading over
    evenly spaced **positions** of the price-sorted group gives four different prices
    only when the prices are themselves spread: on the real feed, "phone case" showed
    27.00, 27.00, 27.00 and 55.00, and "backpack" 34.95, 35.95, 35.95, 35.95. Four
    cards at one price are not a decision. So the spread is taken over the group's
    **distinct prices**: one zone per price, evenly spaced zones, endpoints included,
    and the best-ranked product of each chosen zone represents it.

    Where a group holds fewer distinct prices than there are slots, every zone shows
    and the spare slots go to the next best-ranked products, because the contract owes
    four choices and a zone that does not exist cannot be invented -- the real feed has
    43 backpacks at two prices. Prices that cannot be compared (missing, or in
    different currencies) give no range to spread across, so the group keeps its rank
    order.
    """
    if slots <= 0 or not group:
        return []
    prices = [parse_price_amount(product.price_text) for product in group]
    currencies = {str(product.currency or "").strip().upper() for product in group}
    if any(price is None for price in prices) or len(currencies) > 1:
        return group[:slots]
    # One zone per distinct price, each keeping the group's rank order inside it, so
    # the product representing a zone is the best-matching one at that price.
    zones: dict[float, list[int]] = {}
    for index, price in enumerate(prices):
        zones.setdefault(float(price), []).append(index)
    distinct = sorted(zones)
    if len(distinct) <= slots:
        chosen = [zones[price][0] for price in distinct]
        taken = set(chosen)
        spare = sorted(
            index for price in distinct for index in zones[price] if index not in taken
        )
        chosen.extend(spare[: slots - len(chosen)])
        chosen.sort(key=lambda index: (prices[index], index))
        return [group[index] for index in chosen]
    last = len(distinct) - 1
    if slots == 1:
        # The middle zone, rounded the same way as every other pick.
        return [group[zones[distinct[int(last / 2 + 0.5)]][0]]]
    picked = [distinct[int(step * last / (slots - 1) + 0.5)] for step in range(slots)]
    return [group[zones[price][0]] for price in picked]


def is_strong_feed_opportunity_selection(
    selection: ProviderProductSelectionResult,
    *,
    max_products: int = 4,
) -> bool:
    safe_max = max(1, int(max_products))
    if selection.status != "selected":
        return False
    if selection.price_first:
        # Fewer than four are shown as they are (owner, 2026-10-16). A search PicWise
        # did not understand is strong when the kind test passed and every one of its
        # words is carried: "inc cartridge epson" leaves "inc" out and stays weak.
        return bool(selection.selected_products) and (
            selection.strong_matched_count >= selection.total_count > 0
        )
    if len(selection.selected_products) < safe_max:
        return False
    return selection.strong_matched_count >= safe_max


# Kinds already read by the code that prepared the feed (`prepared_catalogue.py`),
# keyed as `annotate_product_concepts` is: reading 40,000 products takes seconds.
_PREPARED_KINDS: dict[tuple[str, str, str], frozenset[str]] = {}


def remember_product_kinds(kinds: dict[tuple[str, str, str], frozenset[str]]) -> None:
    """Take the kinds a prepared feed was read as, in place of any taken before."""
    _PREPARED_KINDS.clear()
    _PREPARED_KINDS.update(kinds)


def product_kind_key(product: ProviderProduct, fields: dict[str, str]) -> tuple[str, str, str]:
    raw = product.raw if isinstance(product.raw, dict) else {}
    return (str(raw.get("product_type") or ""), fields["category"], str(product.title or ""))


def _product_concepts(product: ProviderProduct, fields: dict[str, str]) -> frozenset[str]:
    key = product_kind_key(product, fields)
    known = _PREPARED_KINDS.get(key)
    return known if known is not None else annotate_product_concepts(*key)


def _unannotated_product_names_concept(
    fields: dict[str, str], feed_terms: tuple[str, ...], concept_id: str
) -> bool:
    """A product whose feed text names no known kind can still be the thing asked for.

    It qualifies only if its own title or product type **names** that kind, read the
    same way the annotation reads a kind: carrying the word somewhere is not enough,
    or a "TV Show Theme Blanket" joins the televisions.
    """
    if not feed_terms:
        return False
    text = " ".join(part for part in (fields["title"], fields["product_type"]) if part)
    if not all(_word_in_text(term, text) for term in feed_terms):
        return False
    return product_text_names_concept(text, concept_id)


_FURNITURE_MEGA_CATEGORY = "furniture_living_storage_smart_home"


def _context_allows_member(
    concepts: frozenset[str], concept_id: str, query_tokens: tuple[str, ...]
) -> bool:
    """May a product of this kind answer this search, given the context it carries?

    A pet product answers a search that names a pet ("dog bed") or a kind that is for
    pets ("cat litter"), never a plain "bed" or "sofa" or "toy". A camping product
    answers furniture searches only when the buyer says camping: "bed" is not answered
    with a camping cot. Owner rule of 2026-10-16: the kind asked for, and only that.
    """
    if PET_MARKER in concepts:
        pet_kind = bool({"pet", "dog", "cat"} & set(concept_id.split("_")))
        if not pet_kind and not query_allows_context(query_tokens, PET_MARKER):
            return False
    if CAMPING_MARKER in concepts:
        concept = get_product_concepts_by_id().get(concept_id)
        if (
            concept is not None
            and concept.mega_category_id == _FURNITURE_MEGA_CATEGORY
            and not query_allows_context(query_tokens, CAMPING_MARKER)
        ):
            return False
    return True


# --------------------------------------------------------------------------------------
# Price first: the owner's plan of 2026-10-15, settled on 2026-10-16
# (docs/picwise_price_first_plan_2026-10-15.md). Built for the searches whose product
# was understood on 2026-10-16, and for the others, answered by their words, on
# 2026-10-17 (part 3b).
# --------------------------------------------------------------------------------------

# The Recommended is the middle product by price. With fewer products there is no
# middle: of two, the "middle" is the cheaper one, and "mid-priced" would be false.
# The owner's own example, £100, £150 and £200, recommends £150.
_RECOMMENDED_MIN_PRODUCTS = 3
# A dearest product costing at least twice the next dearest does not count towards the
# middle, and again for the next one (owner, 2026-10-16). It stays in the list.
_EXTREME_PRICE_FACTOR = 2.0
# The subset search over the buyer's words is exponential in their number.
_MAX_RELAXABLE_FILTERS = 8
_BARE_NUMBER_RE = re.compile(r"^\d+$")
# Short forms a buyer types for the word a feed title writes in full.
_FILTER_WORD_ALIASES = {
    "mic": ("microphone",),
    "mics": ("microphones",),
}
# Where a search's words are looked for: the fields that name this one product. The
# keywords and description are marketing text each merchant writes its own way, and a
# shop's shelf is shared by many products and joins kinds together ("Floor & Table
# Lamps", "Kitchen & Dining", "Garden Furniture Sets"): measured on the third real feed
# (2026-10-16), "floor lamp" listed table lamps from that shelf, "dining table" bar
# tables, and "rattan garden furniture set" single chairs. The kind itself is still
# read from the shelf; only the search's further words are not.
_FILTER_FIELDS = ("title", "product_type", "brand")
# Where the word naming a sub-kind is read with the name it qualifies ("floor lamp").
_KIND_PHRASE_FIELDS = ("title", "product_type")


@dataclass(frozen=True)
class _FilterUnit:
    """One thing a search asks of every product: a word, or a count with its noun."""

    # The buyer's own words, as the page quotes them.
    display: str
    # The feed-language filters it stands for.
    terms: tuple[str, ...]
    pattern: re.Pattern[str]
    # A spec ("1.7l"), a count with its noun ("3 seater") or a preference the lexicon
    # knows ("wireless", "grey", "kids"): something a product either is or is not.
    # Any other word may be the buyer's own phrasing ("pc", "zoom", "home").
    known: bool = False
    # Which text it is read in: the fields that say what a product is, or only its
    # title and type, for a word naming a sub-kind with the kind's name.
    fields: tuple[str, ...] = _FILTER_FIELDS


# Words that say what a product has or is made of, never which kind of it it is: they
# are read anywhere in what identifies the product, not as a sub-kind with the kind's
# name ("bluetooth earbuds" are earbuds that are Bluetooth, wherever the title says so).
# The lexicon's preference words (`get_qualifiers`) are the same in the buyer's Greek.
_PROPERTY_WORDS = frozenset(
    """
    bluetooth usb led solar rechargeable foldable folding adjustable outdoor indoor
    wooden wood glass metal steel stainless velvet fabric rattan wicker plastic bamboo
    oak pine marble wifi hdmi rgb automatic manual mini small tall round square
    """.split()
)


@lru_cache(maxsize=1)
def _qualifier_feed_words() -> frozenset[str]:
    return frozenset(
        word
        for qualifier in get_qualifiers()
        if qualifier.english
        for word in qualifier.english.split()
    ) | _PROPERTY_WORDS


@dataclass(frozen=True)
class _PricedProduct:
    """One product of a price-first answer, at the cheapest offer PicWise has for it."""

    product: ProviderProduct
    price: float
    # `same_product_key`: a GTIN key, a brand and MPN key, or "".
    key: str
    shops: int


def _word_forms(word: str) -> tuple[str, ...]:
    """A filter word with its singular or plural, so "burners" finds "4 Burner Gas BBQ"."""
    if len(word) < 3 or any(char.isdigit() for char in word):
        return (word,)
    forms = {word, *_FILTER_WORD_ALIASES.get(word, ())}
    if word.endswith("ies"):
        forms.add(word[:-3] + "y")
    elif word.endswith("es"):
        forms.update({word[:-2], word[:-1]})
    elif word.endswith("s") and not word.endswith("ss"):
        forms.add(word[:-1])
    elif word.endswith("y"):
        forms.update({word + "s", word[:-1] + "ies"})
    else:
        forms.update({word + "s", word + "es"})
    return tuple(sorted(forms, key=lambda form: (-len(form), form)))


def _kind_name_pattern(concept_id: str) -> str:
    """The names of a kind as one alternation, each with its plural."""
    concept = get_product_concepts_by_id().get(concept_id)
    names = concept.english if concept is not None else ()
    alternatives: set[str] = set()
    for name in names:
        words = name.split()
        if not words:
            continue
        for last in _word_forms(words[-1]):
            alternatives.add(r"[\s-]+".join(re.escape(word) for word in words[:-1] + [last]))
    return "|".join(sorted(alternatives, key=lambda form: (-len(form), form)))


def _kind_modifier(reading: ConceptReading, brand_words: frozenset[str]) -> str:
    """The word naming a sub-kind: typed right before the product's name, and neither
    a brand, a number, a spec nor a preference the lexicon knows ("floor lamp",
    "dining table", "standing desk"), or "" when there is none."""
    tokens = list(reading.tokens)
    head = list(reading.concept_words)
    if not head:
        return ""
    start = next(
        (index for index in range(len(tokens)) if tokens[index : index + len(head)] == head),
        -1,
    )
    if start <= 0:
        return ""
    word = tokens[start - 1]
    if (
        word not in reading.filters
        or reading.filter_sources.get(word, word) != word
        or any(char.isdigit() for char in word)
        or word in brand_words
        or word in _qualifier_feed_words()
        or word in {spec.token for spec in reading.specs}
    ):
        return ""
    if start >= 2 and _BARE_NUMBER_RE.match(tokens[start - 2]):
        # "3 seater sofa": the word is the noun of a count, read with its number.
        return ""
    return word


def _filter_units(
    filters: tuple[str, ...],
    sources: dict[str, str],
    *,
    spec_values: frozenset[str] = frozenset(),
    modifier: str = "",
    kind_names: str = "",
) -> tuple[_FilterUnit, ...]:
    """The search's filters as whole words, each found in a product's text or not.

    Price first lists every product that carries the filters, so a filter decides what
    is in the answer and not only its order, and readings loose enough for a ranking
    are not loose enough for that:
    - a filter is matched as a whole word, with its singular or plural: "set" is not
      found in "settee", nor "light" in "lightweight";
    - a count is read with the noun after it: "3 seater", "4 burners". The "3" alone is
      found in any dimension and narrows nothing. "4+1 Burner" counts as 4 burners;
    - the word naming a sub-kind (`modifier`, from `_kind_modifier`) is read with the
      kind's name after it: "floor lamp" is not a table lamp on a "Floor & Table Lamps"
      shelf, nor "coffee table" a side table in "Coffee Wood Effect";
    - "set" followed by "of" is the size of a pack.
    """
    units: list[_FilterUnit] = []
    index = 0
    while index < len(filters):
        word = filters[index]
        following = filters[index + 1] if index + 1 < len(filters) else ""
        if _BARE_NUMBER_RE.match(word) and following.isalpha():
            noun = "|".join(re.escape(form) for form in _word_forms(following))
            units.append(
                _FilterUnit(
                    display=f"{sources.get(word, word)} {sources.get(following, following)}",
                    terms=(word, following),
                    pattern=re.compile(rf"(?<!\w){word}(?:\s*\+\s*\d+)?[\s-]*(?:{noun})(?!\w)"),
                    known=True,
                )
            )
            index += 2
            continue
        forms = "|".join(re.escape(form) for form in _word_forms(word))
        # "Set of 2" is how many come in the pack, not a set of furniture: "patio set"
        # once answered with a pair of folding chairs.
        not_a_count = r"(?!\s+of\b)" if word in {"set", "sets"} else ""
        if word == modifier and kind_names:
            # "floor lamp": the word with the kind's name after it, one word between
            # at most ("Floor Standing Lamp"), in the product's own title or type.
            units.append(
                _FilterUnit(
                    display=sources.get(word, word),
                    terms=(word,),
                    pattern=re.compile(
                        rf"(?<!\w)(?:{forms})(?:[\s-]+\w+)?[\s-]+(?:{kind_names})(?!\w)"
                    ),
                    fields=_KIND_PHRASE_FIELDS,
                )
            )
            index += 1
            continue
        units.append(
            _FilterUnit(
                display=sources.get(word, word),
                terms=(word,),
                pattern=re.compile(rf"(?<!\w)(?:{forms})(?!\w){not_a_count}", flags=re.IGNORECASE),
                known=word in spec_values or word in _qualifier_feed_words(),
            )
        )
        index += 1
    return tuple(units)


def _carries(unit: _FilterUnit, texts: dict[str, str]) -> bool:
    return bool(unit.pattern.search(texts.get(unit.fields, "")))


def _honoured_filter_units(
    units: tuple[_FilterUnit, ...], haystacks: list[dict[tuple[str, ...], str]], *, page_size: int
) -> tuple[tuple[_FilterUnit, ...], tuple[_FilterUnit, ...]]:
    """Which filters the answer requires, and which it had to drop, as (kept, dropped).

    Every filter is required while at least one product carries them all: fewer and
    right beats more and wrong (owner, 2026-10-16), and "2 of 2" is shown as it is.

    When no product carries them all, the search is partly unanswerable, and the set of
    words kept must still be a reading of it:
    - specs, counts and the preferences the lexicon knows (`_FilterUnit.known`) are
      kept while one product carries them: "power bank 20000mah for iphone" is answered
      with the one 20000mAh power bank, though none says iPhone;
    - any other word is kept only if a full page of products carries it with them (all
      the products, if fewer). One product that happens to carry it is no reading of
      the search: "web cam for zoom calls" once answered with the one webcam whose
      title mentions a digital zoom.
    Of the sets that qualify, the one with the most known filters, then the most
    filters, then the one more products carry, then the one keeping the words typed
    first. The page names every dropped filter.
    """
    relaxable = units[:_MAX_RELAXABLE_FILTERS]
    beyond = units[_MAX_RELAXABLE_FILTERS:]
    if not relaxable:
        return (), beyond
    masks: dict[int, int] = {}
    for haystack in haystacks:
        mask = 0
        for index, unit in enumerate(relaxable):
            if _carries(unit, haystack):
                mask |= 1 << index
        masks[mask] = masks.get(mask, 0) + 1
    full = (1 << len(relaxable)) - 1
    if masks.get(full):
        return relaxable, beyond
    enough = max(1, min(page_size, len(haystacks)))
    known_mask = sum(1 << index for index, unit in enumerate(relaxable) if unit.known)
    best: tuple[tuple[int, int, int, int], int] | None = None
    for subset in range(full, 0, -1):
        support = sum(count for mask, count in masks.items() if mask & subset == subset)
        if support < (1 if subset & ~known_mask == 0 else enough):
            continue
        # Keeping an earlier word ranks higher: bit i of the typed order is worth more
        # the earlier the word was typed.
        typed_first = sum(
            1 << (len(relaxable) - 1 - index)
            for index in range(len(relaxable))
            if subset & (1 << index)
        )
        rank = (bin(subset & known_mask).count("1"), bin(subset).count("1"), support, typed_first)
        if best is None or rank > best[0]:
            best = (rank, subset)
    kept_mask = best[1] if best else 0
    kept = tuple(unit for index, unit in enumerate(relaxable) if kept_mask & (1 << index))
    dropped = tuple(
        unit for index, unit in enumerate(relaxable) if not kept_mask & (1 << index)
    ) + beyond
    return kept, dropped


def _merchant_identity(product: ProviderProduct) -> str:
    """The shop selling this offer, as the feed names it, or "" when it does not say."""
    raw = product.raw if isinstance(product.raw, dict) else {}
    merchant = extract_merchant_name(raw) or str(raw.get("merchant_id") or "").strip()
    return merchant.lower()


def _shop_count(offers: list[ProviderProduct]) -> int:
    """How many shops the feed names for these offers. An unnamed one is not counted as
    another shop: "Lowest price of 2 shops" must not rest on a guess."""
    return max(1, len({_merchant_identity(offer) for offer in offers} - {""}))


def _price_first_products(products: list[ProviderProduct]) -> list[_PricedProduct]:
    """The answer's products, each once at its cheapest offer, cheapest first.

    - Prices in different currencies cannot be sorted against each other (owner,
      2026-10-11), so the answer keeps the currency most of its products are priced in.
    - Offers of one product (`same_product_key`) are joined into one, at the cheapest
      offer, and the number of shops selling it is kept for the card (owner rule 5,
      2026-10-16). Every offer here is listed as in stock: card eligibility has
      already removed the rest, so the cheapest kept is the cheapest in stock.
    - The same shop listing one title at one price twice is one card: nothing on the
      page could tell the two apart. Offers whose shop the feed does not name count as
      one shop here.
    - Equal prices are ordered by title, then id, so the order is the same every time.
    """
    priced: list[tuple[ProviderProduct, float, str]] = []
    for product in products:
        price = parse_price_amount(product.price_text)
        if price is None:
            continue
        priced.append((product, price, str(product.currency or "").strip().upper()))
    if not priced:
        return []
    by_currency: dict[str, int] = {}
    for _product, _price, currency in priced:
        by_currency[currency] = by_currency.get(currency, 0) + 1
    if len(by_currency) > 1:
        # The first currency seen wins a tie, so the choice does not depend on hashing.
        kept_currency = max(by_currency, key=lambda currency: by_currency[currency])
        priced = [row for row in priced if row[2] == kept_currency]

    def order_key(row: tuple[ProviderProduct, float, str]) -> tuple[float, str, str]:
        product, price, _currency = row
        return (price, _normalize_dedupe_title(product.title), str(product.provider_product_id))

    priced.sort(key=order_key)
    groups: dict[str, list[ProviderProduct]] = {}
    group_price: dict[str, float] = {}
    for product, price, _currency in priced:
        raw = product.raw if isinstance(product.raw, dict) else {}
        key = same_product_key(raw, brand=str(product.brand or ""))
        group = key or f"offer:{product.provider_product_id}:{id(product)}"
        if group not in groups:
            groups[group] = []
            group_price[group] = price
        groups[group].append(product)

    ordered: list[_PricedProduct] = []
    seen_cards: set[tuple[str, float, str]] = set()
    seen_ids: set[str] = set()
    # Groups were created in price order, so the first offer of each is its cheapest.
    for group, offers in groups.items():
        cheapest = offers[0]
        product_id = str(cheapest.provider_product_id or "").strip()
        card = (
            _normalize_dedupe_title(cheapest.title),
            group_price[group],
            _merchant_identity(cheapest),
        )
        if card in seen_cards or (product_id and product_id in seen_ids):
            continue
        seen_cards.add(card)
        if product_id:
            seen_ids.add(product_id)
        ordered.append(
            _PricedProduct(
                product=cheapest,
                price=group_price[group],
                key="" if group.startswith("offer:") else group,
                shops=_shop_count(offers),
            )
        )
    return ordered


def _counted_products(ordered: list[_PricedProduct]) -> int:
    """How many products of the answer, cheapest first, count towards its middle price.

    A dearest product costing at least twice the next dearest does not count, and again
    for the next one (owner, 2026-10-16). It stays in the list.
    """
    counted = len(ordered)
    while counted >= 2 and ordered[counted - 1].price >= _EXTREME_PRICE_FACTOR * ordered[counted - 2].price:
        counted -= 1
    return counted


def _middle_price(ordered: list[_PricedProduct]) -> float | None:
    """The middle price of the answer: of 45 products the 23rd's, of an even number the
    cheaper middle one's, extreme top prices left out (`_counted_products`)."""
    counted = _counted_products(ordered)
    return ordered[(counted - 1) // 2].price if counted else None


def _median_recommendation(ordered: list[_PricedProduct]) -> tuple[int | None, str]:
    """Which product of the answer is the Recommended, as (index, status).

    Owner rules of 2026-10-15 and 2026-10-16:
    - the middle product by price over the whole answer: of 45, the 23rd; of an even
      number, the cheaper of the two middle ones;
    - before the middle is found, a dearest product costing at least twice the next
      dearest does not count, and again for the next one. It stays in the list;
    - it must carry an EAN/GTIN, so that "not cheaper elsewhere on PicWise" can be
      known. If the middle product has none, the product nearest to it in price that
      has one; of two equally near, the cheaper;
    - with no product carrying one, there is no Recommended, and the cheapest are shown.

    The card says "Mid-priced for this category", so the nearest product with a code
    must be priced between the cheapest and the dearest that count: on a short list the
    nearest one can be the cheapest, and calling it mid-priced would be false.
    """
    counted = _counted_products(ordered)
    if counted < _RECOMMENDED_MIN_PRODUCTS:
        return None, "too_few_products"
    middle_price = ordered[(counted - 1) // 2].price
    lowest, highest = ordered[0].price, ordered[counted - 1].price
    if not lowest < middle_price < highest:
        # One price for all, or the middle at an end: no product is mid-priced.
        return None, "too_few_products"
    best: tuple[tuple[float, float, int], int] | None = None
    for index in range(counted):
        candidate = ordered[index]
        if not candidate.key.startswith("gtin:"):
            continue
        if not lowest < candidate.price < highest:
            continue
        rank = (abs(candidate.price - middle_price), candidate.price, index)
        if best is None or rank < best[0]:
            best = (rank, index)
    if best is None:
        return None, "no_product_code"
    return best[1], "recommended"


def _select_products_for_concept(
    reading: ConceptReading,
    eligible: tuple[ProviderProduct, ...],
    eligible_fields: tuple[dict[str, str], ...],
    *,
    safe_max: int,
    condition_request: tuple[str, ...] = (),
    shown: int = 0,
) -> ProviderProductSelectionResult:
    """Every instance of the concept the buyer means that carries their filters, cheapest first.

    The product name is not a text filter here: every candidate is already an instance
    of the concept, established from its feed type by `annotate_product_concepts`. That
    is what lets "πλυντηριο", "plintirio" and "washing machine" reach the same products,
    and what stops a relaxed filter from ever changing the kind of product answered.

    The answer is ordered by price (owner, 2026-10-15). The first page holds the
    Recommended (`_median_recommendation`) and then the cheapest; "More" opens the next
    cheapest, four at a time, as often as asked. `shown` is how many products the page
    holds, a multiple of `safe_max`.
    """

    def members_for(concept_id: str) -> list[tuple[ProviderProduct, dict[str, str]]]:
        rows = []
        for product, fields in zip(eligible, eligible_fields):
            concepts = _product_concepts(product, fields)
            if concept_id in concepts:
                if _context_allows_member(concepts, concept_id, reading.tokens):
                    rows.append((product, fields))
            elif not concepts and _unannotated_product_names_concept(
                fields, reading.feed_terms, concept_id
            ):
                rows.append((product, fields))
        return rows

    concept_id = str(reading.concept_id)
    unmatched_name_words: tuple[str, ...] = tuple()
    members = members_for(concept_id)
    if not members and reading.fallback_concept_id:
        # None of the narrower kind ("σκούπα ρομπότ"): answer with the broader kind it
        # belongs to and say which word of the name could not be honoured. One product
        # of the narrower kind is answer enough: fewer and right (owner, 2026-10-16).
        broader_members = members_for(reading.fallback_concept_id)
        if broader_members:
            members = broader_members
            concept_id = reading.fallback_concept_id
            unmatched_name_words = reading.fallback_unmatched

    filters = tuple(term for term in reading.filters if term not in _CONNECTIVE_TOKENS)
    feed_terms = tuple(reading.feed_terms)
    effective_query = " ".join(dict.fromkeys(feed_terms + filters))

    # Owner decision (2026-10-10): products that are not new appear only when asked
    # for. When they are, the answer is the products in that condition; when the feed
    # has none, it is the new ones, and the page says the condition was not matched.
    condition_unmatched: tuple[str, ...] = tuple()
    if condition_request:
        asked_for = [row for row in members if product_non_new_condition(row[0])]
        if asked_for:
            members = asked_for
        else:
            condition_unmatched = (condition_request[0],)

    brand_words = frozenset(
        word for _product, fields in members for word in fields.get("brand", "").split()
    )
    units = _filter_units(
        filters,
        reading.filter_sources,
        spec_values=frozenset(spec.token for spec in reading.specs),
        modifier=_kind_modifier(reading, brand_words),
        kind_names=_kind_name_pattern(concept_id),
    )
    haystacks = [
        {
            scope: " ".join(fields[name] for name in scope if fields.get(name))
            for scope in (_FILTER_FIELDS, _KIND_PHRASE_FIELDS)
        }
        for _product, fields in members
    ]
    kept, dropped, ordered = _price_first_answer(members, haystacks, units, page_size=safe_max)
    return _price_first_result(
        ordered,
        kept,
        dropped,
        members,
        haystacks,
        safe_max=safe_max,
        shown=shown,
        understood_concept=concept_id,
        effective_query=effective_query,
        name_terms=feed_terms,
        condition_request=condition_request,
        also_unmatched=tuple(reading.judgements) + tuple(unmatched_name_words) + condition_unmatched,
        reason_code="product_concept_understood",
    )


def _price_first_answer(
    members: list[tuple[ProviderProduct, dict[str, str]]],
    haystacks: list[dict[tuple[str, ...], str]],
    units: tuple[_FilterUnit, ...],
    *,
    page_size: int,
) -> tuple[tuple[_FilterUnit, ...], tuple[_FilterUnit, ...], list[_PricedProduct]]:
    """The words the answer requires and drops, and its products cheapest first."""
    kept, dropped = _honoured_filter_units(units, haystacks, page_size=page_size)
    carrying = [
        product
        for (product, _fields), haystack in zip(members, haystacks)
        if all(_carries(unit, haystack) for unit in kept)
    ]
    return kept, dropped, _price_first_products(carrying)


def _price_first_result(
    ordered: list[_PricedProduct],
    kept: tuple[_FilterUnit, ...],
    dropped: tuple[_FilterUnit, ...],
    members: list[tuple[ProviderProduct, dict[str, str]]],
    haystacks: list[dict[tuple[str, ...], str]],
    *,
    safe_max: int,
    shown: int,
    understood_concept: str,
    effective_query: str,
    name_terms: tuple[str, ...],
    condition_request: tuple[str, ...],
    also_unmatched: tuple[str, ...],
    reason_code: str,
    strong_only_if_whole: bool = False,
) -> ProviderProductSelectionResult:
    """One price-first answer as the page shows it.

    The first page holds the Recommended (`_median_recommendation`) and then the
    cheapest; "More" opens the next cheapest, four at a time, as often as asked.
    `shown` is how many products the page holds, a multiple of `safe_max`. With
    `strong_only_if_whole`, the answer counts as a strong match only when it carries
    every word of the search: a search PicWise did not understand is shown on its own
    strength (`is_strong_feed_opportunity_selection`), and a dropped word weakens it.
    """
    recommended_index, recommendation_status = _median_recommendation(ordered)
    if recommended_index is None:
        display_order = list(ordered)
    else:
        display_order = (
            [ordered[recommended_index]]
            + ordered[:recommended_index]
            + ordered[recommended_index + 1 :]
        )
    page_size = max(safe_max, -(-max(int(shown or 0), safe_max) // safe_max) * safe_max)
    first_page = display_order[:safe_max]
    opened = display_order[safe_max:page_size]

    recommended = ordered[recommended_index] if recommended_index is not None else None
    # "Lowest price" is for the cheap end of the answer: first-page products priced at
    # or below the Recommended or, with none, at or below the middle price (owner,
    # 2026-10-16 and 2026-10-17). Of three standing desks, the £630.99 one is not the
    # lowest price, though it is on the page.
    lowest_price_ceiling = recommended.price if recommended is not None else _middle_price(ordered)
    cheapest_ids = tuple(
        str(entry.product.provider_product_id or "").strip()
        for entry in first_page
        if entry is not recommended
        and lowest_price_ceiling is not None
        and entry.price <= lowest_price_ceiling
    )
    shop_counts = tuple(
        (str(entry.product.provider_product_id or "").strip(), entry.shops)
        for entry in first_page + opened
        if entry.shops > 1
    )
    first_place: dict[float, int] = {}
    for place, entry in enumerate(ordered, start=1):
        first_place.setdefault(entry.price, place)
    price_ranks = tuple(
        (str(entry.product.provider_product_id or "").strip(), first_place[entry.price])
        for entry in first_page + opened
    )

    # A filter dropped for the whole answer may still be carried by part of it. Say
    # how many rather than calling it unmatched, and nothing when every product of the
    # answer carries it after all: "Only some match: retro (1 of 1)" would be false.
    fully_unmatched: list[str] = []
    partial: list[tuple[str, int]] = []
    texts = {
        id(product): haystack for (product, _fields), haystack in zip(members, haystacks)
    }
    for unit in dropped:
        count = sum(1 for entry in ordered if _carries(unit, texts.get(id(entry.product), {})))
        if ordered and count == len(ordered):
            continue
        if count:
            partial.append((unit.display, count))
        else:
            fully_unmatched.append(unit.display)
    unmatched = tuple(dict.fromkeys(tuple(fully_unmatched) + also_unmatched))
    required = tuple(term for unit in kept for term in unit.terms)
    common = dict(
        understood_concept=understood_concept,
        effective_query=effective_query,
        required_filter_terms=required,
        required_query_terms=name_terms + required,
        unmatched_query_terms=unmatched,
        partially_matched_terms=tuple(partial),
        condition_request=condition_request,
        price_first=True,
        total_count=len(ordered),
    )
    if not ordered:
        return ProviderProductSelectionResult(
            status="insufficient_relevant_products",
            matched_count=0,
            strong_matched_count=0,
            selected_products=tuple(),
            reason_codes=("insufficient_relevant_products", reason_code),
            **common,
        )
    return ProviderProductSelectionResult(
        status="selected",
        # Every one is the kind asked for and carries every required filter, which is
        # what "strong" means for a token match.
        matched_count=len(ordered),
        strong_matched_count=0 if strong_only_if_whole and dropped else len(ordered),
        selected_products=tuple(entry.product for entry in first_page),
        more_products=tuple(entry.product for entry in opened),
        reason_codes=("provider_feed_products_selected", reason_code, "price_first"),
        recommended_product_id=(
            str(recommended.product.provider_product_id or "").strip() if recommended else ""
        ),
        recommendation_status=recommendation_status,
        cheapest_product_ids=cheapest_ids,
        shop_counts=shop_counts,
        price_ranks=price_ranks,
        **common,
    )


# Part 3b (2026-10-17): price first for a search whose product the lexicon does not know.
# The words that end the name of the product a search asks for ("lamp for bedroom").
_PURPOSE_TOKENS = frozenset({"for", "with", "without", "gia", "me", "xoris", "choris"})
# The share of the products carrying every word of such a search that must be of one
# known kind for the search to be answered as that kind: "lenovo thinkpad 16gb ram"
# names no kind PicWise knows, and the 59 products carrying its words are laptops.
_DOMINANT_KIND_SHARE = 2 / 3
_KIND_MARKERS = frozenset({ACCESSORY_MARKER, UNCERTAIN_MARKER, PET_MARKER, CAMPING_MARKER})
# A second kind holding this share of the answer to a one-word search makes it name
# several kinds (`_head_names_several_kinds`).
_AMBIGUOUS_FAMILY_SHARE = 0.1
# How many kinds an ambiguous search names on the page.
_AMBIGUOUS_FAMILIES_SHOWN = 8


def _search_head_word(
    tokens: tuple[str, ...],
    units: tuple[_FilterUnit, ...],
    members: list[tuple[ProviderProduct, dict[str, str]]],
    haystacks: list[dict[tuple[str, ...], str]],
) -> _FilterUnit | None:
    """The word that names the product a search asks for, as the unit that matches it.

    The last word before "for", "with" or "without" that is a word, and not a number, a
    spec, a count's noun ("3 seater"), a preference the lexicon knows or a brand: "dog
    crate", "lamb for bedroom", "inc cartridge epson". A word is read as a brand when
    most of the products carrying it carry it in their brand.
    """
    cut = next((i for i, token in enumerate(tokens) if token in _PURPOSE_TOKENS), len(tokens))
    for index in range(cut - 1, -1, -1):
        word = tokens[index]
        if (
            len(word) < 3
            or not word.isalpha()
            or word in _CONNECTIVE_TOKENS
            or word in _qualifier_feed_words()
            or (index >= 1 and _BARE_NUMBER_RE.match(tokens[index - 1]))
        ):
            continue
        unit = next((unit for unit in units if unit.terms == (word,)), None)
        if unit is None:
            continue
        carriers = [i for i, haystack in enumerate(haystacks) if _carries(unit, haystack)]
        in_brand = sum(1 for i in carriers if word in members[i][1].get("brand", "").split())
        if carriers and in_brand * 2 >= len(carriers):
            continue
        return unit
    return None


def _kind_name(concept_id: str) -> str:
    concept = get_product_concepts_by_id().get(concept_id)
    return concept.english[0] if concept is not None and concept.english else concept_id


def _known_kind_counts(rows: list[tuple[ProviderProduct, dict[str, str]]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for product, fields in rows:
        for concept_id in _product_concepts(product, fields) - _KIND_MARKERS:
            counts[concept_id] = counts.get(concept_id, 0) + 1
    return counts


def _dominant_known_kind(rows: list[tuple[ProviderProduct, dict[str, str]]]) -> str:
    """The one known kind most of these products are, or "" when there is none."""
    counts = _known_kind_counts(rows)
    if not counts:
        return ""
    # A broader kind counts every product of its narrower ones; of equal counts the
    # narrower kind is the reading ("laptop" before "computer").
    best = max(counts, key=lambda concept_id: (counts[concept_id], len(broader_concepts(concept_id)), concept_id))
    return best if counts[best] >= _DOMINANT_KIND_SHARE * len(rows) else ""


def _families_of(rows: list[tuple[ProviderProduct, dict[str, str]]]) -> tuple[str, ...]:
    """The kinds a set of products falls into, largest first, as the page names them:
    the broadest known kind of each, or its product type."""
    counts: dict[str, int] = {}
    for product, fields in rows:
        kinds = _product_concepts(product, fields) - _KIND_MARKERS
        if kinds:
            name = _kind_name(min(broader_concepts(kind)[-1] for kind in kinds))
        else:
            name = _product_family(product).split(">")[-1].strip()
        if name:
            counts[name] = counts.get(name, 0) + 1
    return tuple(sorted(counts, key=lambda name: (-counts[name], name)))[:_AMBIGUOUS_FAMILIES_SHOWN]


def _shelf_family(product: ProviderProduct, fields: dict[str, str]) -> str:
    """Where a product is kept: its product type, else its shop's department (the first
    crumb of its first category path), else ""."""
    raw = product.raw if isinstance(product.raw, dict) else {}
    product_type = " ".join(str(raw.get("product_type") or "").split(">")[-1].lower().split())
    if product_type:
        return f"type:{product_type}"
    category = fields.get("category", "")
    first_path = category.split(CATEGORY_FIELD_SEPARATOR)[0] if category else ""
    department = " ".join(first_path.split(">")[0].split())
    return f"department:{department}" if department else ""


def _head_names_several_kinds(
    head: _FilterUnit,
    kept: tuple[_FilterUnit, ...],
    ordered: list[_PricedProduct],
    readings: dict[int, KindWordReading],
    index_of: dict[int, int],
    members: list[tuple[ProviderProduct, dict[str, str]]],
) -> tuple[str, ...]:
    """The kinds a one-word search names, when it names several, else ().

    Measured on the third real feed (2026-10-17): "switch" is a network switch (416), a
    KVM switch (76) or a video switch (19), and price order opened with a £11.99 HDMI
    switch; "tree" is a Christmas tree, a cat tree or a topiary tree; "machine" a coffee,
    binding or stepper machine. PicWise asks which, rather than list them together.
    Products kept apart -- by their product type, or by the shop department they are
    sold in -- are different kinds, and the search is read as naming several when a
    second one holds a tenth of the answer. "gazebo", "hutch", "hammock" and "crate"
    each sit in one department and are answered. A search that says which ("dog
    crate", "network switch") is not read this way; one whose other word no product
    carries ("cofefe machine") is, because the answer is then the head word's alone.
    """
    if any(unit is not head and not unit.known for unit in kept) or not ordered:
        return tuple()
    families: dict[str, int] = {}
    modifiers: dict[str, int] = {}
    for entry in ordered:
        index = index_of.get(id(entry.product))
        if index is None:
            continue
        product, fields = members[index]
        family = _shelf_family(product, fields)
        if family:
            families[family] = families.get(family, 0) + 1
        modifier = readings[index].modifier
        if (
            modifier
            and modifier.isalpha()
            and modifier not in _CONNECTIVE_TOKENS
            and modifier not in fields.get("brand", "").split()
            and modifier not in _qualifier_feed_words()
        ):
            modifiers[modifier] = modifiers.get(modifier, 0) + 1
    large = [family for family, count in families.items() if count >= _AMBIGUOUS_FAMILY_SHARE * len(ordered)]
    if len(large) < 2:
        return tuple()
    word = head.terms[0]
    named = [f"{modifier} {word}" for modifier in sorted(modifiers, key=lambda m: (-modifiers[m], m))]
    if len(named) < 2:
        named = [family.split(":", 1)[1] for family in sorted(large, key=lambda f: (-families[f], f))]
    return tuple(named[:_AMBIGUOUS_FAMILIES_SHOWN])


def _ambiguous_selection(
    families: tuple[str, ...],
    dropped: tuple[_FilterUnit, ...],
    condition_request: tuple[str, ...],
) -> ProviderProductSelectionResult:
    return ProviderProductSelectionResult(
        status="ambiguous_product_family",
        matched_count=0,
        strong_matched_count=0,
        selected_products=tuple(),
        reason_codes=("ambiguous_product_family",),
        unmatched_query_terms=tuple(unit.display for unit in dropped),
        ambiguous_product_families=families,
        condition_request=condition_request,
    )


def _select_products_by_words(
    reading: ConceptReading,
    tokens: tuple[str, ...],
    eligible: tuple[ProviderProduct, ...],
    eligible_fields: tuple[dict[str, str], ...],
    *,
    safe_max: int,
    condition_request: tuple[str, ...] = (),
    shown: int = 0,
) -> ProviderProductSelectionResult:
    """Price first for a search whose product PicWise did not understand (part 3b).

    The answer is every product carrying the search's words, cheapest first, read as
    an understood search reads its filters (`_filter_units`). The kind is tested as
    strictly, because price order puts look-alikes first:
    - the word naming the product (`_search_head_word`) must be what the product is
      (`read_kind_word`): "rabbit hutch" lists hutches, not the £14.99 hutch cover. A
      word that is no product's own noun in the feed names no product there: "lamb
      for bedroom" lists nothing, rather than a cat tree with "Lamb Fleece";
    - when no product is that, or the search names no product, and most products
      carrying all its words are one known kind, the answer is that kind:
      "lenovo thinkpad 16gb ram" lists the ThinkPads carrying it;
    - a search that names several kinds is not guessed at: "machine" and "samsung"
      ask which product is meant.
    """
    members = list(zip(eligible, eligible_fields))
    condition_unmatched: tuple[str, ...] = tuple()
    if condition_request:
        asked_for = [row for row in members if product_non_new_condition(row[0])]
        if asked_for:
            members = asked_for
        else:
            condition_unmatched = (condition_request[0],)
    filters = tuple(token for token in tokens if token not in _CONNECTIVE_TOKENS)
    spec_values = frozenset(spec.token for spec in reading.specs) | frozenset(
        token for token in filters if any(char.isdigit() for char in token)
    )
    units = _filter_units(filters, {}, spec_values=spec_values)
    haystacks = [
        {
            scope: " ".join(fields[name] for name in scope if fields.get(name))
            for scope in (_FILTER_FIELDS, _KIND_PHRASE_FIELDS)
        }
        for _product, fields in members
    ]
    head = _search_head_word(tokens, units, members, haystacks)
    readings: dict[int, KindWordReading] = {}
    if head is not None:
        forms = _word_forms(head.terms[0])
        for i, ((product, _fields), haystack) in enumerate(zip(members, haystacks)):
            if not _carries(head, haystack):
                continue
            raw = product.raw if isinstance(product.raw, dict) else {}
            kind_reading = read_kind_word(
                str(raw.get("product_type") or ""), str(product.title or ""), forms
            )
            if kind_reading.names:
                readings[i] = kind_reading
        if not any(kind_reading.as_noun for kind_reading in readings.values()):
            readings = {}
    chosen = sorted(readings)
    understood_concept = ""
    if not chosen:
        carrying_all = [
            members[i]
            for i, haystack in enumerate(haystacks)
            if units and all(_carries(unit, haystack) for unit in units)
        ]
        concept_id = _dominant_known_kind(carrying_all)
        if not concept_id:
            families = _families_of(carrying_all)
            if len(families) > 1:
                return _ambiguous_selection(families, tuple(), condition_request)
        else:
            understood_concept = concept_id
            chosen = [
                i
                for i, (product, fields) in enumerate(members)
                if concept_id in (concepts := _product_concepts(product, fields))
                and not concepts & {ACCESSORY_MARKER, UNCERTAIN_MARKER}
                and _context_allows_member(concepts, concept_id, tokens)
            ]
    answer_members = [members[i] for i in chosen]
    answer_haystacks = [haystacks[i] for i in chosen]
    kept, dropped, ordered = _price_first_answer(
        answer_members, answer_haystacks, units, page_size=safe_max
    )
    if head is not None and readings:
        index_of = {id(members[i][0]): i for i in chosen}
        families = _head_names_several_kinds(head, kept, ordered, readings, index_of, members)
        if families:
            return _ambiguous_selection(families, dropped, condition_request)
    return _price_first_result(
        ordered,
        kept,
        dropped,
        answer_members,
        answer_haystacks,
        safe_max=safe_max,
        shown=shown,
        understood_concept=understood_concept,
        effective_query=" ".join(dict.fromkeys(filters)),
        name_terms=tuple(),
        condition_request=condition_request,
        also_unmatched=condition_unmatched,
        reason_code="product_named_by_words",
        strong_only_if_whole=True,
    )


@dataclass(frozen=True)
class SearchCatalogue:
    """The products a search reads, judged once (step 5 of the price-first plan).

    Whether a product can be shown on a card and whether the feed calls it not new do
    not depend on the search, and judging every product again on every search was
    about 4 of the 5 seconds a search took on the third feed. Each product's search
    fields are kept with it, read-only.
    """

    # Card-eligible products, in feed order, new or not: a search that asks for a
    # condition reads these.
    products: tuple[ProviderProduct, ...]
    fields: tuple[dict[str, str], ...]
    # The new ones among them: every other search reads only these.
    new_products: tuple[ProviderProduct, ...]
    new_fields: tuple[dict[str, str], ...]


def build_search_catalogue(
    products: tuple[ProviderProduct, ...],
    *,
    feed_ctx: FeedAvailabilityContext | None = None,
    card_eligible: tuple[bool, ...] | None = None,
    non_new: tuple[str, ...] | None = None,
) -> SearchCatalogue:
    """Judge each product once: can a card show it, and is it new.

    `card_eligible`, when given, is that judgement already made for each product, in
    order, against `feed_ctx`: the feed pipeline makes it as it loads the feed.
    `non_new`, when given, is `product_non_new_condition` of each product, in order: a
    prepared feed carries it.
    """
    if card_eligible is None:
        if feed_ctx is None:
            feed_ctx = build_feed_availability_context(products)
        card_eligible = tuple(
            evaluate_product_eligibility(product, feed_ctx=feed_ctx).card_eligible
            for product in products
        )
    eligible = tuple(product for product, shown in zip(products, card_eligible) if shown)
    if non_new is None:
        conditions = tuple(product_non_new_condition(product) for product in eligible)
    else:
        conditions = tuple(condition for condition, shown in zip(non_new, card_eligible) if shown)
    fields = tuple(_product_search_fields(product) for product in eligible)
    new_rows = tuple(
        (product, product_fields)
        for product, product_fields, condition in zip(eligible, fields, conditions)
        if not condition
    )
    return SearchCatalogue(
        products=eligible,
        fields=fields,
        new_products=tuple(product for product, _fields in new_rows),
        new_fields=tuple(product_fields for _product, product_fields in new_rows),
    )


def select_provider_products_for_query(
    query: str,
    products: tuple[ProviderProduct, ...],
    *,
    max_products: int = 4,
    reading: ConceptReading | None = None,
    feed_ctx: FeedAvailabilityContext | None = None,
    shown: int = 0,
    catalogue: SearchCatalogue | None = None,
) -> ProviderProductSelectionResult:
    """The products to show for one search.

    `shown` is how many products of a price-first answer the page holds: the first
    page, plus every four "More" has opened. 0 means the first page only.
    `catalogue` is `products` already judged (`build_search_catalogue`); without it they
    are judged here.
    """
    safe_max = max(1, int(max_products))
    if reading is None:
        reading = understand_product_query(str(query or ""))
    # Words asking for a non-new item are a condition request, not words to match
    # against feed text: a merchant who sells new goods still writes "new" and "used"
    # in its copy. They are dropped from the words the inventory is filtered by, and
    # the condition itself is read from the feed's own column by `_non_new_condition`.
    # The reading was taken on the raw query and this runs on the canonicalised one,
    # which typo correction may have rewritten, so both are read and the words of
    # either count: a request must never end up as a filter because the two spellings
    # disagree.
    condition_request = tuple(
        dict.fromkeys(
            reading.condition_request + read_condition_request(str(query or "")).words
        )
    )
    condition_words = {word for phrase in condition_request for word in phrase.split()}
    tokens = tuple(
        token
        for token in _tokenize_query(query)
        if not _is_condition_request_token(token, condition_words)
    )
    if not tokens and not reading.understood:
        return ProviderProductSelectionResult(
            status="no_query_tokens",
            matched_count=0,
            strong_matched_count=0,
            selected_products=tuple(),
            reason_codes=("empty_query",),
        )

    if catalogue is None:
        catalogue = build_search_catalogue(products, feed_ctx=feed_ctx)
    # Owner decision (2026-10-10): a product the feed calls refurbished, used or
    # otherwise not new is not a candidate at all unless the buyer asked for that
    # condition. Dropped here, before any ranking, so it cannot be shown, counted,
    # recommended or reported as a match.
    if condition_request:
        eligible, eligible_fields = catalogue.products, catalogue.fields
    else:
        eligible, eligible_fields = catalogue.new_products, catalogue.new_fields

    if reading.understood:
        return _select_products_for_concept(
            reading,
            eligible,
            eligible_fields,
            safe_max=safe_max,
            condition_request=condition_request,
            shown=shown,
        )
    return _select_products_by_words(
        reading,
        tokens,
        eligible,
        eligible_fields,
        safe_max=safe_max,
        condition_request=condition_request,
        shown=shown,
    )


def _product_family(product: ProviderProduct) -> str:
    raw = product.raw if isinstance(product.raw, dict) else {}
    return " ".join(str(raw.get("product_type") or product.category_text or "").lower().split())


@dataclass(frozen=True)
class ProviderFeedRecommendationDecision:
    decision_status: str
    recommended_product_id: str | None = None
    recommendation_reason_codes: tuple[str, ...] = field(default_factory=tuple)
    recommendation_confidence: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_status": self.decision_status,
            "recommended_product_id": self.recommended_product_id,
            "recommendation_reason_codes": list(self.recommendation_reason_codes),
            "recommendation_confidence": self.recommendation_confidence,
        }


def _comparable_tie_break_prices(
    products: tuple[ProviderProduct, ...],
) -> dict[str, float | None]:
    """Prices the tie-break may compare, read exactly as the choice labels read them.

    The tie-break once had its own parser: "1.099,00" became 1.099, so the recommendation
    went to a fridge its own card called "3rd lowest price". It also compared 95 GBP with
    100 EUR while the labels on the same page refused to. Prices in different currencies
    are not comparable, so none are compared.
    """
    amounts = {
        str(product.provider_product_id or ""): parse_price_amount(product.price_text)
        for product in products
    }
    currencies = {
        str(product.currency or "").strip().upper()
        for product in products
        if amounts[str(product.provider_product_id or "")] is not None
    }
    if len(currencies) > 1:
        return {key: None for key in amounts}
    return amounts


def _comparable_ranking_property(
    products: tuple[ProviderProduct, ...],
    concept_id: str,
) -> tuple[str, dict[int, float]]:
    """The one specification these products can be ranked on, and each one's value.

    Owner's rule, from 2026-10-11 onward: the recommendation must not rest on price.
    Where the feed states a specification whose direction no buyer would dispute --
    storage, battery, runtime -- that specification decides instead, and price falls
    back to being the last resort it was always meant to be.

    Three conditions, all of them about not overclaiming:

    - The **kind of product** must have a ranking criterion at all
      (`picwise_taxonomy.comparison_rules`). More watts is not a better amplifier and
      more metres is not a better cable, so those kinds never reach here.
    - **At least two** of the four must state the same property. One product stating
      its battery is not a comparison, it is a fact about one product.
    - Every value is read from what the feed **stated as a property**
      (`picwise_providers.product_specs`), never from a number loose in marketing
      prose.

    Returns ("", {}) when the four cannot be compared this way, which is the normal
    case on a feed without specifications, and then nothing here changes the order.
    """
    criteria = comparison_rule(concept_id).ranking_criteria if concept_id else tuple()
    if not criteria:
        return "", {}
    stated: dict[str, dict[int, float]] = {}
    for product in products:
        raw = product.raw if isinstance(product.raw, dict) else {}
        for spec in read_product_specs(raw, title=product.title):
            if spec.property_id in criteria and spec.ranks:
                stated.setdefault(spec.property_id, {})[id(product)] = spec.value
    # The property the most of them state; ties fall to the order the kind lists its
    # criteria in, so the same property is chosen for every query of that kind.
    best = ""
    for property_id in criteria:
        values = stated.get(property_id) or {}
        if len(values) >= 2 and len(values) > len(stated.get(best) or {}):
            best = property_id
    return (best, stated[best]) if best else ("", {})


def _deciding_reason_code(
    sorted_keys: list[tuple[Any, ...]],
    choice_count: int,
    *,
    ranking_property: str = "",
) -> str:
    """What actually separated the recommended choice from the runner-up.

    Shown first on the recommended card, because it is the answer to "why this one?".
    The other reasons describe the winner but are usually just as true of the rest.
    """
    if len(sorted_keys) == 1 and choice_count > 1:
        # The other choices did not carry every word the recommendation was scored on.
        return "closer_search_match"
    if len(sorted_keys) < 2:
        return ""
    winner, runner_up = sorted_keys[0], sorted_keys[1]
    if winner[:2] != runner_up[:2]:
        return "closer_search_match"
    # The specification comes before the price, which is the whole point of reading it.
    if ranking_property and winner[2] != runner_up[2]:
        return f"better_{ranking_property}"
    if winner[3] == -1 and winner[3:5] < runner_up[3:5]:
        return "price_tie_breaker"
    # Same match, same specification, same or incomparable price: only the title order
    # is left, which is no fact about the products. Say so rather than dress it up.
    return "tie_on_search_match_and_price"


def _recommendation_reason_codes_for_product(
    product: ProviderProduct,
    tokens: tuple[str, ...],
    *,
    normalized_query: str,
    query_seeks_accessory: bool,
    score: int,
    title_matches: int,
    price_used_as_tie_breaker: bool,
    concept_id: str = "",
) -> tuple[str, ...]:
    fields = _product_search_fields(product)
    reasons: list[str] = []

    if score >= _STRONG_MATCH_MIN_SCORE:
        reasons.append("strong_query_title_fit")
    if tokens and title_matches == len(tokens):
        reasons.append("all_query_tokens_in_title")
    normalized = str(normalized_query or "").strip().lower()
    if normalized and normalized in fields["title"]:
        reasons.append("query_phrase_in_title")
    if tokens and _word_in_text(tokens[-1], fields["title"]):
        reasons.append("product_type_phrase_in_title")
    if any(_token_matches_field(token, fields["product_type"]) for token in tokens):
        reasons.append("product_type_alignment")
    elif any(_token_matches_field(token, fields["category"]) for token in tokens):
        reasons.append("category_alignment")
    accessory_penalty = _title_accessory_penalty(
        fields["title"],
        normalized_query=normalized,
        query_seeks_accessory=query_seeks_accessory,
        concept_id=concept_id,
    )
    if accessory_penalty == 0 and not query_seeks_accessory:
        reasons.append("main_product_not_accessory")
    if _product_completeness_bonus(product) == _COMPLETE_PRODUCT_BONUS:
        reasons.append("complete_product_fields")
    if price_used_as_tie_breaker:
        reasons.append("price_tie_breaker")

    return tuple(dict.fromkeys(reasons))


def decide_recommended_provider_product(
    query: str,
    selected_products: tuple[ProviderProduct, ...],
    *,
    required_tokens: tuple[str, ...] | None = None,
    concept_verified: bool = False,
    concept_id: str = "",
    condition_requested: bool = False,
    feed_ctx: FeedAvailabilityContext | None = None,
) -> ProviderFeedRecommendationDecision:
    """Pick the recommended product from the four already selected.

    `required_tokens` is the reading the selection settled on. It must be passed when
    the query was relaxed, otherwise this re-scores against words the selection already
    established the inventory cannot be filtered by, finds nothing, and reports no
    recommendation for four products that are sitting right there. `concept_id` is the
    kind the selection verified the four as, so they are scored as they were chosen.
    `condition_requested` says the buyer asked for a non-new item: where the four are
    mixed because the feed had too few, the recommendation must come from the ones
    that are the condition asked for, or PicWise would answer a question nobody asked.
    """
    if not selected_products:
        return ProviderFeedRecommendationDecision(
            decision_status="no_selection",
            recommendation_reason_codes=("no_feed_selection",),
        )
    if len(selected_products) != 4:
        return ProviderFeedRecommendationDecision(
            decision_status="insufficient_selected_products",
            recommendation_reason_codes=("insufficient_selected_products",),
        )

    normalized_query = normalize_query(str(query or ""))
    tokens = _tokenize_query(query)
    if not tokens:
        return ProviderFeedRecommendationDecision(
            decision_status="no_selection",
            recommendation_reason_codes=("empty_query",),
        )

    query_seeks_accessory = _query_seeks_accessory(tokens, normalized_query)
    if concept_verified:
        # The selection already established the kind of product; only its filters,
        # possibly none, are required here.
        filter_tokens = tuple(required_tokens or ())
    else:
        filter_tokens = tuple(required_tokens) if required_tokens else tokens
    candidates: list[tuple[tuple[Any, ...], ProviderProduct]] = []
    full_scores: dict[int, int] = {}
    tie_break_prices = _comparable_tie_break_prices(selected_products)
    # The specification these four can be ranked on, when the kind has one and at
    # least two of them state it. Empty on a feed without specifications, and then
    # the order below is exactly what it was.
    ranking_property, ranking_values = _comparable_ranking_property(
        selected_products, concept_id if concept_verified else ""
    )

    for product in selected_products:
        ranking = _score_product_for_tokens(
            product,
            filter_tokens,
            normalized_query=normalized_query,
            query_seeks_accessory=query_seeks_accessory,
            scoring_tokens=tokens,
            concept_verified=concept_verified,
            concept_id=concept_id,
        )
        if ranking is None:
            continue
        _matched_tokens, score, title_matches, title_key, product_id = ranking
        full_scores[id(product)] = score
        # The same equivalence the four were chosen by: a word that appears only in
        # merchant free text does not make one choice match the search more closely.
        substantive_score, _titles, _matched = _substantive_relevance(
            ranking, _product_search_fields(product), tokens
        )
        price_value = tie_break_prices.get(str(product.provider_product_id or ""))
        has_price = 1 if price_value is not None else 0
        # A product that does not state the property cannot win on it, and is not
        # penalised by it either: it simply sorts below the ones that did, and the
        # card says how many of the four stated theirs.
        spec_value = ranking_values.get(id(product))
        sort_key = (
            -substantive_score,
            -title_matches,
            -spec_value if spec_value is not None else float("inf"),
            -has_price,
            price_value if price_value is not None else float("inf"),
            title_key,
            product_id,
        )
        candidates.append((sort_key, product))

    if not candidates:
        return ProviderFeedRecommendationDecision(
            decision_status="insufficient_selected_products",
            recommendation_reason_codes=("insufficient_selected_products",),
        )

    narrowed_by_condition = False
    if condition_requested:
        asked_for = [row for row in candidates if product_non_new_condition(row[1])]
        if asked_for and len(asked_for) < len(candidates):
            candidates = asked_for
            narrowed_by_condition = True

    candidates.sort(key=lambda row: row[0])
    winner_key, winner_product = candidates[0]
    winner_id = str(winner_product.provider_product_id or "").strip()
    winner_score = full_scores[id(winner_product)]
    winner_title_matches = -winner_key[1]

    deciding_reason = _deciding_reason_code(
        [row[0] for row in candidates],
        # Among the condition asked for, what separated this one from the others of
        # that condition. The condition itself is stated as its own reason below.
        len(candidates) if narrowed_by_condition else len(selected_products),
        ranking_property=ranking_property,
    )

    reason_codes = _recommendation_reason_codes_for_product(
        winner_product,
        tokens,
        normalized_query=normalized_query,
        query_seeks_accessory=query_seeks_accessory,
        score=winner_score,
        title_matches=winner_title_matches,
        price_used_as_tie_breaker=deciding_reason == "price_tie_breaker",
        concept_id=concept_id if concept_verified else "",
    )
    if concept_verified:
        reason_codes = ("product_concept_match",) + tuple(reason_codes)
    if deciding_reason:
        reason_codes = (deciding_reason,) + tuple(
            code for code in reason_codes if code != deciding_reason
        )
    if narrowed_by_condition:
        # What actually kept the new products out: the condition the buyer asked for.
        reason_codes = ("requested_condition_match",) + tuple(
            code for code in reason_codes if code != "requested_condition_match"
        )
    if not reason_codes:
        reason_codes = ("provider_feed_recommendation_selected",)

    if feed_ctx is None:
        feed_ctx = build_feed_availability_context(selected_products)
    winner_eligibility = evaluate_product_eligibility(
        winner_product,
        feed_ctx=feed_ctx,
    )
    if winner_eligibility.offer_health is None:
        recommendation_confidence = "unknown"
    else:
        recommendation_confidence = evaluate_recommendation_confidence(
            card_eligible=winner_eligibility.card_eligible,
            offer_health=winner_eligibility.offer_health,
            has_strong_feed_evidence=winner_eligibility.recommendation_confidence_ceiling
            in {"strong", "limited"},
        )
        if (
            winner_eligibility.offer_health.purchasability.purchasability_state
            == "purchasability_unknown"
            and recommendation_confidence == "strong"
        ):
            recommendation_confidence = "limited"

    return ProviderFeedRecommendationDecision(
        decision_status="recommended",
        recommended_product_id=winner_id or None,
        recommendation_reason_codes=reason_codes,
        recommendation_confidence=recommendation_confidence,
    )
