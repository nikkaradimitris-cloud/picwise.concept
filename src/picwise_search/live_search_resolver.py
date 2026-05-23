from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from picwise_nlu import (
    adapt_local_nlu_intent_for_router,
    build_local_nlu_intent,
    detect_category,
    normalize_greeklish_and_typos,
    normalize_query,
)
from picwise_search_memory.canonical_registry import get_cached_canonical_vocabulary_registry
from picwise_search_memory.broad_query_suggestions import (
    BroadQuerySuggestion,
    build_broad_query_suggestions,
    should_offer_broad_query_suggestions,
)
from picwise_search_memory.index_lookup import lookup_offline_search_index

from .index_resolver_adapter import get_cached_offline_search_index, resolve_query_with_search_index


_CONNECTED_PROVIDER_BY_CATEGORY = {
    "power_banks": "manual_amazon_affiliate",
}

_CONNECTED_STATUSES = {
    "intent_resolved",
    "specific_product_resolved",
    "general_intent_resolved",
}

_INDEX_CATEGORY_OVERRIDE_MIN_CONFIDENCE = 0.84
_INDEX_CATEGORY_OVERRIDE_MIN_SCORE = 0.84


def _vocabulary_registry():
    return get_cached_canonical_vocabulary_registry()


@dataclass(frozen=True)
class LiveSearchResolution:
    raw_query: str
    display_query: str
    normalized_query: str
    canonical_query: str
    canonical_category: str | None
    mega_category_id: str | None
    display_name: str | None
    lower_level_provider_category: str | None
    intent: str
    query_type: str
    confidence: float
    status: str
    needs_review: bool
    provider_key: str
    provider_status: str
    result_allowed: bool
    resolver_state: str
    reason_codes: tuple[str, ...]
    suggestions: tuple[BroadQuerySuggestion, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_query": self.raw_query,
            "display_query": self.display_query,
            "normalized_query": self.normalized_query,
            "canonical_query": self.canonical_query,
            "canonical_category": self.canonical_category,
            "mega_category_id": self.mega_category_id,
            "display_name": self.display_name,
            "lower_level_provider_category": self.lower_level_provider_category,
            "intent": self.intent,
            "query_type": self.query_type,
            "confidence": self.confidence,
            "status": self.status,
            "needs_review": self.needs_review,
            "provider_key": self.provider_key,
            "provider_status": self.provider_status,
            "result_allowed": self.result_allowed,
            "resolver_state": self.resolver_state,
            "reason_codes": list(self.reason_codes),
            "suggestions": [row.to_dict() for row in self.suggestions],
        }


def _normalized_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def is_empty_search_query(query: str) -> bool:
    return not _normalized_text(query)


def empty_landing_search_resolution(query: str = "") -> LiveSearchResolution:
    raw_query = str(query or "")
    return LiveSearchResolution(
        raw_query=raw_query,
        display_query=raw_query,
        normalized_query="",
        canonical_query="",
        canonical_category=None,
        mega_category_id=None,
        display_name=None,
        lower_level_provider_category=None,
        intent="unknown",
        query_type="unknown",
        confidence=0.0,
        status="invalid_intent",
        needs_review=True,
        provider_key="not_connected",
        provider_status="not_connected",
        result_allowed=False,
        resolver_state="blocked_or_unsafe",
        reason_codes=("empty_query",),
    )


def _safe_confidence(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return round(score, 2)


def resolve_live_search(query: str) -> LiveSearchResolution:
    raw_query = str(query or "")
    display_query = raw_query
    normalized_query = normalize_query(raw_query)
    canonicalized_query = normalize_greeklish_and_typos(normalized_query)

    intent = build_local_nlu_intent(raw_query)
    adapter = adapt_local_nlu_intent_for_router(intent)
    category_probe = detect_category(canonicalized_query)
    index_result = resolve_query_with_search_index(canonicalized_query)
    raw_index_lookup = lookup_offline_search_index(canonicalized_query, get_cached_offline_search_index())
    broad_suggestions = build_broad_query_suggestions(_vocabulary_registry(), canonicalized_query)
    offer_broad_suggestions = should_offer_broad_query_suggestions(
        normalized_query=canonicalized_query,
        lookup_result=raw_index_lookup,
        suggestions=broad_suggestions,
    )

    canonical_category = intent.get("category") or category_probe.get("category")
    if not canonical_category and index_result.status == "matched" and index_result.canonical_term:
        canonical_category = str(index_result.canonical_term)

    index_high_confidence_category = (
        index_result.status in {"matched", "low_confidence"}
        and bool(index_result.mega_category_id)
        and index_result.confidence >= _INDEX_CATEGORY_OVERRIDE_MIN_CONFIDENCE
        and index_result.score >= _INDEX_CATEGORY_OVERRIDE_MIN_SCORE
    )
    if index_high_confidence_category:
        mega_category_id = index_result.mega_category_id
        if index_result.canonical_term:
            provider_category = category_probe.get("category") or intent.get("category")
            if provider_category in _CONNECTED_PROVIDER_BY_CATEGORY:
                canonical_category = str(provider_category)
            else:
                canonical_category = str(index_result.canonical_term)
    else:
        mega_category_id = (
            intent.get("mega_category_id")
            or category_probe.get("mega_category_id")
            or (index_result.mega_category_id if index_result.status == "matched" else None)
            or (
                canonical_category
                if canonical_category and canonical_category != "power_banks"
                else None
            )
        )
    lower_level_provider_category = category_probe.get("lower_level_provider_category")
    if canonical_category in _CONNECTED_PROVIDER_BY_CATEGORY:
        lower_level_provider_category = canonical_category
    query_type = str(intent.get("query_type") or "unknown")
    confidence = max(
        _safe_confidence(intent.get("confidence")),
        _safe_confidence(category_probe.get("confidence")),
        _safe_confidence(index_result.confidence),
    )
    status = str(intent.get("status") or "manual_review_required")
    needs_review = bool(intent.get("needs_review", True))
    is_ambiguous_or_invalid = status in {"ambiguous_needs_review", "invalid_intent"} or query_type == "ambiguous_query"
    if (
        status not in _CONNECTED_STATUSES
        and index_high_confidence_category
        and canonical_category not in _CONNECTED_PROVIDER_BY_CATEGORY
    ):
        status = "general_intent_resolved"
        needs_review = False

    canonical_query = "power bank" if canonical_category == "power_banks" else (
        (index_result.canonical_term or canonicalized_query or normalized_query or _normalized_text(raw_query).lower())
    )

    provider_lookup_key = str(lower_level_provider_category or canonical_category or "")
    provider_key = _CONNECTED_PROVIDER_BY_CATEGORY.get(provider_lookup_key, "not_connected")
    provider_status = "connected" if provider_lookup_key in _CONNECTED_PROVIDER_BY_CATEGORY else "not_connected"

    connected_category_safe_gate = bool(
        provider_lookup_key in _CONNECTED_PROVIDER_BY_CATEGORY
        and provider_status == "connected"
        and _normalized_text(raw_query)
        and not is_ambiguous_or_invalid
        and confidence >= 0.2
    )
    if connected_category_safe_gate and status not in _CONNECTED_STATUSES:
        status = "general_intent_resolved"
        needs_review = False

    result_allowed = bool(
        provider_lookup_key in _CONNECTED_PROVIDER_BY_CATEGORY
        and provider_status == "connected"
        and status in _CONNECTED_STATUSES
        and confidence >= 0.2
    )

    resolver_state = "not_understood"
    blocked_or_unsafe = status == "invalid_intent" or any(
        marker in str(code).lower()
        for code in intent.get("reason_codes", [])
        for marker in ("unsafe", "blocked")
    )
    if result_allowed:
        resolver_state = "connected_provider_results"
    elif offer_broad_suggestions:
        resolver_state = "broad_query_suggestions"
        mega_category_id = None
        canonical_category = None
        needs_review = False
        status = "general_intent_resolved"
    elif blocked_or_unsafe:
        resolver_state = "blocked_or_unsafe"
    elif mega_category_id and provider_status != "connected":
        resolver_state = "understood_provider_not_connected"
    elif provider_lookup_key in _CONNECTED_PROVIDER_BY_CATEGORY and (needs_review or confidence < 0.2):
        resolver_state = "low_confidence_manual_review"
    elif not mega_category_id and not canonical_category:
        resolver_state = "not_understood"
    else:
        # Unsupported or weakly resolved categories remain safely un-understood.
        resolver_state = "not_understood"

    reason_codes: list[str] = [str(code) for code in intent.get("reason_codes", []) if str(code).strip()]
    reason_codes.extend(f"index_{code}" for code in index_result.reason_codes)
    reason_codes.append(f"index_status_{index_result.status}")
    if not _normalized_text(raw_query):
        reason_codes.append("empty_query")
    if not mega_category_id and not canonical_category:
        reason_codes.append("no_canonical_category")
    if mega_category_id and provider_status != "connected":
        reason_codes.append("provider_not_connected")
    if needs_review:
        reason_codes.append("manual_review_required")
    if provider_status == "connected":
        reason_codes.append("provider_connected")
    if offer_broad_suggestions:
        reason_codes.append("broad_query_suggestions")
    reason_codes.append(f"resolver_state_{resolver_state}")
    reason_codes.append(f"adapter_{adapter.get('adapter_decision', 'safe_review_only')}")

    return LiveSearchResolution(
        raw_query=raw_query,
        display_query=display_query,
        normalized_query=normalized_query,
        canonical_query=canonical_query,
        canonical_category=str(canonical_category) if canonical_category else None,
        mega_category_id=str(mega_category_id) if mega_category_id else None,
        display_name=str(category_probe.get("display_name") or "") or None,
        lower_level_provider_category=str(lower_level_provider_category) if lower_level_provider_category else None,
        intent=str(canonical_category or "unknown"),
        query_type=query_type,
        confidence=confidence,
        status=status,
        needs_review=needs_review,
        provider_key=provider_key,
        provider_status=provider_status,
        result_allowed=result_allowed,
        resolver_state=resolver_state,
        reason_codes=tuple(sorted(set(reason_codes))),
        suggestions=broad_suggestions if offer_broad_suggestions else (),
    )
