from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from picwise_nlu import normalize_query

from .contracts import OfferHealth, ProviderProduct
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


@dataclass(frozen=True)
class ProviderProductSelectionResult:
    status: str
    matched_count: int = 0
    strong_matched_count: int = 0
    selected_products: tuple[ProviderProduct, ...] = field(default_factory=tuple)
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "matched_count": self.matched_count,
            "strong_matched_count": self.strong_matched_count,
            "selected_count": len(self.selected_products),
            "reason_codes": list(self.reason_codes),
            "selected_products": [
                provider_product_to_backend_dict(product)
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


def _verified_purchasable_from_offer_health(offer_health: OfferHealth) -> bool:
    purch = offer_health.purchasability
    return (
        purch.purchasability_state == "purchasable"
        and purch.verification_confidence in {"high", "strong", "verified"}
    )


def provider_product_to_backend_dict(product: ProviderProduct) -> dict[str, Any]:
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


def _product_type_alignment_adjustment(
    product_type: str,
    *,
    allowed_product_types: tuple[str, ...],
    query_seeks_accessory: bool,
) -> int:
    normalized_type = " ".join(str(product_type or "").split()).strip().lower()
    if _is_weak_product_type(normalized_type):
        return 0
    if not allowed_product_types:
        return 0
    if _product_type_matches_allowed(normalized_type, allowed_product_types):
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

    return {
        "title": str(product.title or "").strip().lower(),
        "product_type": product_type.lower(),
        "category": _build_secondary_category_text(raw, product),
        "brand": str(product.brand or "").strip().lower(),
        "keywords": str(raw.get("keywords") or "").strip().lower(),
        "description": description.lower(),
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


def _query_seeks_accessory(tokens: tuple[str, ...], normalized_query: str) -> bool:
    if any(token in _ACCESSORY_TERMS for token in tokens):
        return True
    normalized = str(normalized_query or "").strip().lower()
    return any(term in normalized for term in _ACCESSORY_TERMS)


def _title_accessory_penalty(
    title: str,
    *,
    normalized_query: str,
    query_seeks_accessory: bool,
) -> int:
    if query_seeks_accessory or not title:
        return 0
    penalty = 0
    for term in _ACCESSORY_TERMS:
        if term in title:
            penalty += _ACCESSORY_PENALTY
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
) -> tuple[int, int, int, str, str] | None:
    fields = _product_search_fields(product)
    allowed_product_types = _resolve_allowed_product_types(normalized_query, tokens)
    matched_tokens = 0
    score = 0
    title_matches = 0
    category_matches = 0

    for token in tokens:
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

    if matched_tokens < len(tokens):
        return None

    normalized = str(normalized_query or "").strip().lower()
    if normalized and normalized in fields["title"]:
        score += _PHRASE_IN_TITLE_BONUS
    if title_matches == len(tokens):
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
    )
    if (
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


def _dedupe_selected_products(
    ranked_products: list[tuple[tuple[int, int, int, str, str], ProviderProduct]],
) -> list[ProviderProduct]:
    seen_ids: set[str] = set()
    seen_titles: set[str] = set()
    selected: list[ProviderProduct] = []

    for _, product in ranked_products:
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
        selected.append(product)

    return selected


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


def select_provider_products_for_query(
    query: str,
    products: tuple[ProviderProduct, ...],
    *,
    max_products: int = 4,
) -> ProviderProductSelectionResult:
    safe_max = max(1, int(max_products))
    normalized_query = normalize_query(str(query or ""))
    tokens = _tokenize_query(query)
    if not tokens:
        return ProviderProductSelectionResult(
            status="no_query_tokens",
            matched_count=0,
            strong_matched_count=0,
            selected_products=tuple(),
            reason_codes=("empty_query",),
        )

    query_seeks_accessory = _query_seeks_accessory(tokens, normalized_query)
    feed_ctx = build_feed_availability_context(products)
    ranked: list[tuple[tuple[int, int, int, str, str], ProviderProduct]] = []
    for product in products:
        card_eligibility = evaluate_product_eligibility(
            product,
            feed_ctx=feed_ctx,
        )
        if not card_eligibility.card_eligible:
            continue
        ranking = _score_product_for_tokens(
            product,
            tokens,
            normalized_query=normalized_query,
            query_seeks_accessory=query_seeks_accessory,
        )
        if ranking is not None:
            ranked.append((ranking, product))

    ranked.sort(key=lambda row: (-row[0][1], -row[0][2], -row[0][0], row[0][3], row[0][4]))
    strong_matched_count = _count_strong_matches(ranked, token_count=len(tokens))
    deduped = _dedupe_selected_products(ranked)
    matched_count = len(deduped)

    if matched_count < safe_max:
        return ProviderProductSelectionResult(
            status="insufficient_relevant_products",
            matched_count=matched_count,
            strong_matched_count=strong_matched_count,
            selected_products=tuple(),
            reason_codes=("insufficient_relevant_products",),
        )

    return ProviderProductSelectionResult(
        status="selected",
        matched_count=matched_count,
        strong_matched_count=strong_matched_count,
        selected_products=tuple(deduped[:safe_max]),
        reason_codes=("provider_feed_products_selected",),
    )


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


def _parse_price_for_tie_breaker(price_text: str) -> float | None:
    cleaned = str(price_text or "").strip().replace(",", "")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


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
) -> ProviderFeedRecommendationDecision:
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
    candidates: list[tuple[tuple[Any, ...], ProviderProduct]] = []

    for product in selected_products:
        ranking = _score_product_for_tokens(
            product,
            tokens,
            normalized_query=normalized_query,
            query_seeks_accessory=query_seeks_accessory,
        )
        if ranking is None:
            continue
        _matched_tokens, score, title_matches, title_key, product_id = ranking
        price_value = _parse_price_for_tie_breaker(product.price_text)
        has_price = 1 if price_value is not None else 0
        sort_key = (
            -score,
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
    winner_score = -winner_key[0]
    winner_title_matches = -winner_key[1]

    top_primary = [
        row
        for row in candidates
        if row[0][0] == winner_key[0] and row[0][1] == winner_key[1]
    ]
    price_used_as_tie_breaker = False
    if len(top_primary) > 1:
        has_price_flags = {row[0][2] for row in top_primary}
        price_values = {row[0][3] for row in top_primary if row[0][2] == 1}
        if len(has_price_flags) > 1 or len(price_values) > 1:
            price_used_as_tie_breaker = True

    reason_codes = _recommendation_reason_codes_for_product(
        winner_product,
        tokens,
        normalized_query=normalized_query,
        query_seeks_accessory=query_seeks_accessory,
        score=winner_score,
        title_matches=winner_title_matches,
        price_used_as_tie_breaker=price_used_as_tie_breaker,
    )
    if not reason_codes:
        reason_codes = ("provider_feed_recommendation_selected",)

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
