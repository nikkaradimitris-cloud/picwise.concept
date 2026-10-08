from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from picwise_nlu import normalize_query
from picwise_nlu.concept_understanding import (
    ConceptReading,
    annotate_product_concepts,
    normalize_spec_text,
    strip_accents_if_needed,
    understand_product_query,
)

from .contracts import FeedAvailabilityContext, OfferHealth, ProviderProduct
from .normalization import extract_merchant_name
from .decision_labels import parse_price_amount
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


def _product_text_contains_token(product: ProviderProduct, token: str) -> bool:
    fields = _product_search_fields(product)
    return any(_token_matches_field(token, value) for value in fields.values())


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
    # The feed availability context the selection judged card eligibility against. The
    # exported card fields and the recommendation must read the same one.
    feed_availability_context: FeedAvailabilityContext | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "partially_matched_terms": [list(row) for row in self.partially_matched_terms],
            "understood_concept": self.understood_concept,
            "effective_query": self.effective_query,
            "required_filter_terms": list(self.required_filter_terms),
            "status": self.status,
            "matched_count": self.matched_count,
            "strong_matched_count": self.strong_matched_count,
            "selected_count": len(self.selected_products),
            "reason_codes": list(self.reason_codes),
            "unmatched_query_terms": list(self.unmatched_query_terms),
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


_CONDITION_KEYS = ("condition", "product_condition", "item_condition")


def _feed_condition(raw: dict[str, Any]) -> str:
    """The item condition as the feed row states it ("new", "refurbished"), or ""."""
    for key in _CONDITION_KEYS:
        value = " ".join(str(raw.get(key) or "").split())
        if value:
            return value
    return ""


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

    return " ".join(part.strip().lower() for part in parts if part.strip())


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
) -> int:
    if query_seeks_accessory or not title:
        return 0
    main_product_text = _INCLUDED_ITEMS_RE.split(title, maxsplit=1)[0]
    penalty = _ACCESSORY_PENALTY * _accessory_terms_in(main_product_text)
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
) -> tuple[int, int, int, str, str] | None:
    """Rank one product. `tokens` must all match; `scoring_tokens` only add points.

    The two differ when a query carries words this inventory cannot be filtered by:
    those words no longer exclude a product, but a product that does mention them still
    scores higher, so the closest answer to the buyer's actual phrasing wins.
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
    between. In general the picks are evenly spaced positions of the price-sorted
    group, endpoints included: two slots are the cheapest and the dearest, three add
    the middle one, one slot is the middle one; a position halfway between two
    products rounds up. Returned cheapest first. Prices that cannot be compared
    (missing, or in different currencies) give no range to spread across, so the group
    keeps its rank order.
    """
    if slots <= 0 or not group:
        return []
    prices = [parse_price_amount(product.price_text) for product in group]
    currencies = {str(product.currency or "").strip().upper() for product in group}
    if any(price is None for price in prices) or len(currencies) > 1:
        return group[:slots]
    order = sorted(range(len(group)), key=lambda index: (prices[index], index))
    if len(order) <= slots:
        return [group[index] for index in order]
    last = len(order) - 1
    if slots == 1:
        # The middle position, rounded the same way as every other pick.
        return [group[order[int(last / 2 + 0.5)]]]
    picks = [order[int(step * last / (slots - 1) + 0.5)] for step in range(slots)]
    return [group[index] for index in picks]


def _choose_shown_products(
    ranked: list[tuple[tuple[int, int, int, str, str], ProviderProduct]],
    *,
    safe_max: int,
    fields_by_id: dict[int, dict[str, str]],
    scoring_tokens: tuple[str, ...],
) -> list[ProviderProduct]:
    """The products to show, from candidates that already passed every hard filter.

    Groups of substantially equivalent products are taken in relevance order; a group
    that fits in the free slots is shown whole, and the group that does not is reduced
    by `_spread_across_price`. Nothing here adds a candidate: the alphabetical order of
    titles, which used to decide among equivalents, no longer decides anything.
    """
    rows = []
    for position, (ranking, ranked_product, shown_product) in enumerate(
        _dedupe_ranked_products(ranked)
    ):
        fields = fields_by_id.get(id(ranked_product)) or _product_search_fields(ranked_product)
        rows.append((_substantive_relevance(ranking, fields, scoring_tokens), position, shown_product))
    rows.sort(key=lambda row: (-row[0][0], -row[0][1], -row[0][2], row[1]))

    chosen: list[ProviderProduct] = []
    start = 0
    while start < len(rows) and len(chosen) < safe_max:
        end = start
        while end < len(rows) and rows[end][0] == rows[start][0]:
            end += 1
        group = [product for _relevance, _position, product in rows[start:end]]
        chosen.extend(_spread_across_price(group, safe_max - len(chosen)))
        start = end
    return chosen


def _count_strong_matches(
    ranked_products: list[tuple[tuple[int, int, int, str, str], ProviderProduct]],
    *,
    token_count: int,
) -> int:
    strong_count = 0
    for ranking, _product in ranked_products:
        _matched_tokens, score, title_matches, _title_key, _product_id = ranking
        if score >= _STRONG_MATCH_MIN_SCORE and title_matches >= token_count:
            strong_count += 1
    return strong_count


def is_strong_feed_opportunity_selection(
    selection: ProviderProductSelectionResult,
    *,
    max_products: int = 4,
) -> bool:
    safe_max = max(1, int(max_products))
    if selection.status != "selected":
        return False
    if len(selection.selected_products) < safe_max:
        return False
    return selection.strong_matched_count >= safe_max


def _product_concepts(product: ProviderProduct, fields: dict[str, str]) -> frozenset[str]:
    raw = product.raw if isinstance(product.raw, dict) else {}
    return annotate_product_concepts(
        str(raw.get("product_type") or ""),
        fields["category"],
        str(product.title or ""),
    )


def _unannotated_product_names_concept(fields: dict[str, str], feed_terms: tuple[str, ...]) -> bool:
    # A product whose feed text names no known concept at all can still be the thing
    # asked for; it qualifies only if its own text carries the concept's English name.
    if not feed_terms:
        return False
    text = " ".join((fields["title"], fields["product_type"], fields["category"]))
    return all(term in text for term in feed_terms)


def _distinct_product_count(rows: list[tuple[ProviderProduct, dict[str, str]]]) -> int:
    seen: set[str] = set()
    for product, _fields in rows:
        seen.add(
            _product_identity_key(product)
            or str(product.provider_product_id or "").strip()
            or _normalize_dedupe_title(product.title)
        )
    return len(seen)


def _select_products_for_concept(
    reading: ConceptReading,
    eligible: tuple[ProviderProduct, ...],
    eligible_fields: tuple[dict[str, str], ...],
    *,
    safe_max: int,
) -> ProviderProductSelectionResult:
    """Select four instances of the concept the buyer means, then apply their filters.

    The product name is not a text filter here: every candidate is already an instance
    of the concept, established from its feed type by `annotate_product_concepts`. That
    is what lets "πλυντηριο", "plintirio" and "washing machine" reach the same products,
    and what stops a relaxed filter from ever changing the kind of product answered.
    """

    def members_for(concept_id: str) -> list[tuple[ProviderProduct, dict[str, str]]]:
        rows = []
        for product, fields in zip(eligible, eligible_fields):
            concepts = _product_concepts(product, fields)
            if concept_id in concepts or (
                not concepts and _unannotated_product_names_concept(fields, reading.feed_terms)
            ):
                rows.append((product, fields))
        return rows

    concept_id = str(reading.concept_id)
    unmatched_name_words: tuple[str, ...] = tuple()
    members = members_for(concept_id)
    if _distinct_product_count(members) < safe_max and reading.fallback_concept_id:
        # Too few of the narrower kind ("σκούπα ρομπότ"): answer with the broader kind
        # it belongs to and say which word of the name could not be honoured.
        broader_members = members_for(reading.fallback_concept_id)
        if _distinct_product_count(broader_members) >= safe_max:
            members = broader_members
            concept_id = reading.fallback_concept_id
            unmatched_name_words = reading.fallback_unmatched

    filters = tuple(term for term in reading.filters if term not in _CONNECTIVE_TOKENS)
    feed_terms = tuple(reading.feed_terms)
    scoring_tokens = tuple(dict.fromkeys(feed_terms + filters))
    effective_query = " ".join(scoring_tokens)
    query_seeks_accessory = _query_seeks_accessory(scoring_tokens, effective_query)

    def display(terms: tuple[str, ...]) -> tuple[str, ...]:
        # Quote the buyer's own words, not the feed-language filter they became.
        return tuple(dict.fromkeys(reading.filter_sources.get(term, term) for term in terms))

    def rank_with(required: tuple[str, ...]):
        rows: list[tuple[tuple[int, int, int, str, str], ProviderProduct]] = []
        for product, fields in members:
            ranking = _score_product_for_tokens(
                product,
                required,
                normalized_query=effective_query,
                query_seeks_accessory=query_seeks_accessory,
                scoring_tokens=scoring_tokens,
                fields=fields,
                concept_verified=True,
            )
            if ranking is not None:
                rows.append((ranking, product))
        return rows

    required = filters
    unmatchable: tuple[str, ...] = tuple()
    ranked = rank_with(required)
    # How many products carry the whole request, reported when four cannot be shown.
    strict_count = len(_dedupe_selected_products(ranked))
    if filters and len(_dedupe_selected_products(ranked)) < safe_max:
        plan = resolve_query_token_plan(
            filters,
            tuple(product for product, _ in members),
            max_products=safe_max,
            product_fields=tuple(fields for _, fields in members),
        )
        required, unmatchable = plan.required, plan.unmatchable
        ranked = rank_with(required)
        if len(_dedupe_selected_products(ranked)) < safe_max:
            # No filter can be honoured with a full set; the concept alone still can.
            required, unmatchable = tuple(), filters
            ranked = rank_with(required)

    ranked.sort(key=lambda row: (-row[0][1], -row[0][2], -row[0][0], row[0][3], row[0][4]))
    deduped = _dedupe_selected_products(ranked)

    # A filter that could not hold for all four may still hold for some of them; those
    # rank first. Say how many rather than calling it unmatched.
    fields_by_id = {id(product): fields for product, fields in members}
    shown = _choose_shown_products(
        ranked,
        safe_max=safe_max,
        fields_by_id=fields_by_id,
        scoring_tokens=scoring_tokens,
    )
    fully_unmatched: list[str] = []
    partial: list[tuple[str, int]] = []
    for term in unmatchable:
        carrying = sum(
            1
            for product in shown
            if term in " ".join(value for value in fields_by_id.get(id(product), {}).values() if value)
        )
        if 0 < carrying < len(shown):
            partial.append((reading.filter_sources.get(term, term), carrying))
        else:
            fully_unmatched.append(term)
    unmatched = display(tuple(fully_unmatched)) + tuple(reading.judgements) + unmatched_name_words
    unmatched = tuple(dict.fromkeys(unmatched))
    common = dict(
        understood_concept=concept_id,
        effective_query=effective_query,
        required_filter_terms=required,
        required_query_terms=feed_terms + required,
        unmatched_query_terms=unmatched,
        partially_matched_terms=tuple(partial) if len(deduped) >= safe_max else tuple(),
    )
    if len(deduped) < safe_max:
        return ProviderProductSelectionResult(
            status="insufficient_relevant_products",
            matched_count=strict_count,
            strong_matched_count=strict_count,
            selected_products=tuple(),
            reason_codes=("insufficient_relevant_products", "product_concept_understood"),
            **common,
        )
    return ProviderProductSelectionResult(
        status="selected",
        matched_count=len(deduped),
        # Every one is an instance of the concept and carries every required filter,
        # which is what "strong" means for a token match.
        strong_matched_count=len(deduped),
        selected_products=tuple(shown),
        reason_codes=("provider_feed_products_selected", "product_concept_understood"),
        **common,
    )


def select_provider_products_for_query(
    query: str,
    products: tuple[ProviderProduct, ...],
    *,
    max_products: int = 4,
    reading: ConceptReading | None = None,
    feed_ctx: FeedAvailabilityContext | None = None,
) -> ProviderProductSelectionResult:
    safe_max = max(1, int(max_products))
    normalized_query = normalize_query(str(query or ""))
    tokens = _tokenize_query(query)
    if reading is None:
        reading = understand_product_query(str(query or ""))
    if not tokens and not reading.understood:
        return ProviderProductSelectionResult(
            status="no_query_tokens",
            matched_count=0,
            strong_matched_count=0,
            selected_products=tuple(),
            reason_codes=("empty_query",),
        )

    query_seeks_accessory = _query_seeks_accessory(tokens, normalized_query)
    if feed_ctx is None:
        feed_ctx = build_feed_availability_context(products)
    eligible = tuple(
        product
        for product in products
        if evaluate_product_eligibility(product, feed_ctx=feed_ctx).card_eligible
    )
    # Build each product's searchable text once and reuse it for both the reading
    # decision and the scoring below.
    eligible_fields = tuple(_product_search_fields(product) for product in eligible)

    if reading.understood:
        return _select_products_for_concept(
            reading, eligible, eligible_fields, safe_max=safe_max
        )

    def rank_with(required: tuple[str, ...]):
        rows: list[tuple[tuple[int, int, int, str, str], ProviderProduct]] = []
        for product, fields in zip(eligible, eligible_fields):
            ranking = _score_product_for_tokens(
                product,
                required,
                normalized_query=normalized_query,
                query_seeks_accessory=query_seeks_accessory,
                scoring_tokens=tokens,
                fields=fields,
            )
            if ranking is not None:
                rows.append((ranking, product))
        return rows

    # Try the buyer's words as given first. When the inventory answers them there is
    # nothing to relax, and this path costs exactly what it did before relaxation
    # existed -- which matters, because relaxation is a second pass over the feed.
    strict_tokens = tuple(_query_token_candidates(tokens)) or tokens
    ranked = rank_with(strict_tokens)
    required_tokens = strict_tokens
    token_plan = QueryTokenPlan(
        required=strict_tokens,
        unmatchable=tuple(),
        connectives=tuple(token for token in tokens if token in _CONNECTIVE_TOKENS),
    )
    if len(_dedupe_selected_products(ranked)) < safe_max:
        token_plan = resolve_query_token_plan(
            tokens,
            eligible,
            max_products=safe_max,
            product_fields=eligible_fields,
        )
        if token_plan.ambiguous_product_families:
            return ProviderProductSelectionResult(
                status="ambiguous_product_family",
                matched_count=0,
                strong_matched_count=0,
                selected_products=tuple(),
                reason_codes=("ambiguous_product_family",),
                unmatched_query_terms=token_plan.unmatchable,
                ambiguous_product_families=token_plan.ambiguous_product_families,
            )
        relaxed_tokens = token_plan.required or strict_tokens
        if relaxed_tokens != strict_tokens:
            required_tokens = relaxed_tokens
            ranked = rank_with(required_tokens)

    ranked.sort(key=lambda row: (-row[0][1], -row[0][2], -row[0][0], row[0][3], row[0][4]))
    # "Strong" means the product carries the whole reading the selection committed to.
    # Counting against the original words would make every relaxed query weak by
    # definition, which would hide results the selection had already judged good.
    strong_matched_count = _count_strong_matches(
        ranked,
        token_count=len(required_tokens),
    )
    deduped = _dedupe_selected_products(ranked)
    matched_count = len(deduped)

    if matched_count < safe_max:
        return ProviderProductSelectionResult(
            status="insufficient_relevant_products",
            matched_count=matched_count,
            strong_matched_count=strong_matched_count,
            selected_products=tuple(),
            reason_codes=("insufficient_relevant_products",),
            unmatched_query_terms=token_plan.unmatchable,
            required_query_terms=required_tokens,
        )

    chosen = tuple(
        _choose_shown_products(
            ranked,
            safe_max=safe_max,
            fields_by_id={id(product): fields for product, fields in zip(eligible, eligible_fields)},
            scoring_tokens=tokens,
        )
    )
    chosen_families = {_product_family(product) for product in chosen}
    if len(chosen_families) > 1 and "" not in chosen_families:
        # Without an understood product the words matched several kinds of product
        # ("machine": coffee machines and washing machines). Four choices of different
        # kinds are not a decision between alternatives, so ask instead of guessing.
        return ProviderProductSelectionResult(
            status="ambiguous_product_family",
            matched_count=0,
            strong_matched_count=0,
            selected_products=tuple(),
            reason_codes=("ambiguous_product_family",),
            unmatched_query_terms=token_plan.unmatchable,
            ambiguous_product_families=tuple(sorted(chosen_families))[:8],
        )

    return ProviderProductSelectionResult(
        status="selected",
        matched_count=matched_count,
        strong_matched_count=strong_matched_count,
        selected_products=chosen,
        reason_codes=("provider_feed_products_selected",),
        unmatched_query_terms=token_plan.unmatchable,
        required_query_terms=required_tokens,
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


def _deciding_reason_code(sorted_keys: list[tuple[Any, ...]], choice_count: int) -> str:
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
    if winner[2] == -1 and winner[2:4] < runner_up[2:4]:
        return "price_tie_breaker"
    # Same match, same or incomparable price: only the title order is left, which is
    # no fact about the products. Say so rather than dress it up.
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
    feed_ctx: FeedAvailabilityContext | None = None,
) -> ProviderFeedRecommendationDecision:
    """Pick the recommended product from the four already selected.

    `required_tokens` is the reading the selection settled on. It must be passed when
    the query was relaxed, otherwise this re-scores against words the selection already
    established the inventory cannot be filtered by, finds nothing, and reports no
    recommendation for four products that are sitting right there.
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

    for product in selected_products:
        ranking = _score_product_for_tokens(
            product,
            filter_tokens,
            normalized_query=normalized_query,
            query_seeks_accessory=query_seeks_accessory,
            scoring_tokens=tokens,
            concept_verified=concept_verified,
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
        sort_key = (
            -substantive_score,
            -title_matches,
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

    candidates.sort(key=lambda row: row[0])
    winner_key, winner_product = candidates[0]
    winner_id = str(winner_product.provider_product_id or "").strip()
    winner_score = full_scores[id(winner_product)]
    winner_title_matches = -winner_key[1]

    deciding_reason = _deciding_reason_code(
        [row[0] for row in candidates], len(selected_products)
    )

    reason_codes = _recommendation_reason_codes_for_product(
        winner_product,
        tokens,
        normalized_query=normalized_query,
        query_seeks_accessory=query_seeks_accessory,
        score=winner_score,
        title_matches=winner_title_matches,
        price_used_as_tie_breaker=deciding_reason == "price_tie_breaker",
    )
    if concept_verified:
        reason_codes = ("product_concept_match",) + tuple(reason_codes)
    if deciding_reason:
        reason_codes = (deciding_reason,) + tuple(
            code for code in reason_codes if code != deciding_reason
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
