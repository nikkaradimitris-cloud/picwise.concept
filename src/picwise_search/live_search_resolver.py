from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from picwise_nlu import (
    adapt_local_nlu_intent_for_router,
    build_local_nlu_intent,
    detect_category,
    normalize_greeklish_and_typos,
    normalize_query,
)


_CONNECTED_PROVIDER_BY_CATEGORY = {
    "power_banks": "manual_amazon_affiliate",
}

_UNDERSTOOD_CATEGORIES = {
    "power_banks",
    "chargers",
    "car_tyres",
    "calculators",
}

_CONNECTED_STATUSES = {
    "intent_resolved",
    "specific_product_resolved",
    "general_intent_resolved",
}

_CANONICAL_QUERY_BY_CATEGORY = {
    "power_banks": "power bank",
    "chargers": "charger",
    "car_tyres": "car tyres",
    "calculators": "calculator",
}


@dataclass(frozen=True)
class LiveSearchResolution:
    raw_query: str
    display_query: str
    normalized_query: str
    canonical_query: str
    canonical_category: str | None
    intent: str
    query_type: str
    confidence: float
    status: str
    needs_review: bool
    provider_key: str
    provider_status: str
    result_allowed: bool
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_query": self.raw_query,
            "display_query": self.display_query,
            "normalized_query": self.normalized_query,
            "canonical_query": self.canonical_query,
            "canonical_category": self.canonical_category,
            "intent": self.intent,
            "query_type": self.query_type,
            "confidence": self.confidence,
            "status": self.status,
            "needs_review": self.needs_review,
            "provider_key": self.provider_key,
            "provider_status": self.provider_status,
            "result_allowed": self.result_allowed,
            "reason_codes": list(self.reason_codes),
        }


def _normalized_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


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

    canonical_category = intent.get("category") or category_probe.get("category")
    query_type = str(intent.get("query_type") or "unknown")
    confidence = max(_safe_confidence(intent.get("confidence")), _safe_confidence(category_probe.get("confidence")))
    status = str(intent.get("status") or "manual_review_required")
    needs_review = bool(intent.get("needs_review", True))
    is_ambiguous_or_invalid = status in {"ambiguous_needs_review", "invalid_intent"} or query_type == "ambiguous_query"

    canonical_query = (
        _CANONICAL_QUERY_BY_CATEGORY.get(str(canonical_category))
        or canonicalized_query
        or normalized_query
        or _normalized_text(raw_query).lower()
    )

    provider_key = _CONNECTED_PROVIDER_BY_CATEGORY.get(str(canonical_category), "not_connected")
    provider_status = "connected" if str(canonical_category) in _CONNECTED_PROVIDER_BY_CATEGORY else "not_connected"

    connected_category_safe_gate = bool(
        canonical_category in _CONNECTED_PROVIDER_BY_CATEGORY
        and provider_status == "connected"
        and _normalized_text(raw_query)
        and not is_ambiguous_or_invalid
        and confidence >= 0.2
    )
    if connected_category_safe_gate and status not in _CONNECTED_STATUSES:
        status = "general_intent_resolved"
        needs_review = False

    result_allowed = bool(
        canonical_category in _CONNECTED_PROVIDER_BY_CATEGORY
        and provider_status == "connected"
        and status in _CONNECTED_STATUSES
        and confidence >= 0.2
    )

    reason_codes: list[str] = [str(code) for code in intent.get("reason_codes", []) if str(code).strip()]
    if not _normalized_text(raw_query):
        reason_codes.append("empty_query")
    if not canonical_category:
        reason_codes.append("no_canonical_category")
    if canonical_category in _UNDERSTOOD_CATEGORIES and provider_status != "connected":
        reason_codes.append("provider_not_connected")
    if needs_review:
        reason_codes.append("manual_review_required")
    if provider_status == "connected":
        reason_codes.append("provider_connected")
    reason_codes.append(f"adapter_{adapter.get('adapter_decision', 'safe_review_only')}")

    return LiveSearchResolution(
        raw_query=raw_query,
        display_query=display_query,
        normalized_query=normalized_query,
        canonical_query=canonical_query,
        canonical_category=str(canonical_category) if canonical_category else None,
        intent=str(canonical_category or "unknown"),
        query_type=query_type,
        confidence=confidence,
        status=status,
        needs_review=needs_review,
        provider_key=provider_key,
        provider_status=provider_status,
        result_allowed=result_allowed,
        reason_codes=tuple(sorted(set(reason_codes))),
    )
