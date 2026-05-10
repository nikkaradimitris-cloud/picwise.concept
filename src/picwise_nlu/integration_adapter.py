from __future__ import annotations

import json
from typing import Any

from .contract import REVIEW_REQUIRED_STATUSES
from .validation import validate_local_nlu_intent

_SAFE_ROUTABLE_QUERY_TYPES = {"specific_product", "general_intent"}
_SAFE_ROUTABLE_STATUSES = {
    "intent_resolved",
    "specific_product_resolved",
    "general_intent_resolved",
}
_BLOCKED_RESULT_KEYS = {
    "products",
    "product",
    "offers",
    "offer",
    "price",
    "prices",
    "affiliate",
    "affiliate_url",
}


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _compact_text(item)
        if text and text not in seen:
            normalized.append(text)
            seen.add(text)
    return normalized


def _as_safe_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    sanitized: dict[str, Any] = {}
    for key, raw in value.items():
        key_text = _compact_text(key)
        if not key_text:
            continue
        key_l = key_text.lower()
        if key_l in _BLOCKED_RESULT_KEYS:
            continue
        if isinstance(raw, (str, int, float, bool)) or raw is None:
            sanitized[key_text] = raw
        elif isinstance(raw, list):
            sanitized[key_text] = _as_str_list(raw)
        elif isinstance(raw, dict):
            sanitized[key_text] = _as_safe_dict(raw)
        else:
            sanitized[key_text] = _compact_text(raw)
    return sanitized


def _safe_confidence(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def _safe_intent(intent: dict) -> dict[str, Any]:
    validated = validate_local_nlu_intent(intent)
    safe_payload = {
        "raw_query": _compact_text(validated.get("raw_query")),
        "normalized_query": _compact_text(validated.get("normalized_query")),
        "query_type": _compact_text(validated.get("query_type")),
        "category": _compact_text(validated.get("category")),
        "brand_candidates": _as_str_list(validated.get("brand_candidates")),
        "model_candidates": _as_str_list(validated.get("model_candidates")),
        "specs": _as_safe_dict(validated.get("specs")),
        "buying_priority": _as_str_list(validated.get("buying_priority")),
        "confidence": _safe_confidence(validated.get("confidence")),
        "needs_review": bool(validated.get("needs_review", True)),
        "status": _compact_text(validated.get("status")),
        "reason_codes": _as_str_list(validated.get("reason_codes")),
        "source": _compact_text(validated.get("source")),
        "schema_version": _compact_text(validated.get("schema_version")),
    }
    return json.loads(json.dumps(safe_payload, ensure_ascii=True, sort_keys=True))


def should_use_local_nlu_intent(intent: dict) -> bool:
    safe_intent = _safe_intent(intent)
    if safe_intent["needs_review"]:
        return False
    if safe_intent["status"] in REVIEW_REQUIRED_STATUSES:
        return False
    if safe_intent["status"] not in _SAFE_ROUTABLE_STATUSES:
        return False
    if safe_intent["query_type"] not in _SAFE_ROUTABLE_QUERY_TYPES:
        return False
    return safe_intent["confidence"] >= 0.35


def build_router_query_from_intent(intent: dict) -> str:
    safe_intent = _safe_intent(intent)
    if not should_use_local_nlu_intent(safe_intent):
        return ""

    normalized_query = _compact_text(safe_intent.get("normalized_query"))
    if normalized_query:
        return normalized_query

    raw_query = _compact_text(safe_intent.get("raw_query"))
    if raw_query:
        return raw_query.lower()

    segments: list[str] = []
    for key in ("category",):
        text = _compact_text(safe_intent.get(key))
        if text:
            segments.append(text.lower())
    segments.extend(item.lower() for item in safe_intent.get("brand_candidates", []))
    segments.extend(item.lower() for item in safe_intent.get("model_candidates", []))
    return _compact_text(" ".join(segments))


def build_safe_router_metadata(intent: dict) -> dict:
    safe_intent = _safe_intent(intent)
    use_intent = should_use_local_nlu_intent(safe_intent)
    enforce_safe_no_result = bool(
        safe_intent.get("needs_review")
        and (
            safe_intent.get("status") in {"ambiguous_needs_review", "no_safe_result", "invalid_intent"}
            or safe_intent.get("query_type") == "ambiguous_query"
        )
    )
    metadata = {
        "source": "local_nlu_adapter",
        "raw_query": safe_intent.get("raw_query", ""),
        "normalized_query": safe_intent.get("normalized_query", ""),
        "query_type": safe_intent.get("query_type", "unknown"),
        "status": safe_intent.get("status", "invalid_intent"),
        "confidence": safe_intent.get("confidence", 0.0),
        "needs_review": bool(safe_intent.get("needs_review", True)),
        "reason_codes": _as_str_list(safe_intent.get("reason_codes")),
        "should_use_local_nlu_intent": use_intent,
        "adapter_decision": "use_local_nlu_intent" if use_intent else "safe_review_only",
        "enforce_safe_no_result": enforce_safe_no_result,
        "router_query": build_router_query_from_intent(safe_intent),
    }
    return json.loads(json.dumps(metadata, ensure_ascii=True, sort_keys=True))


def adapt_local_nlu_intent_for_router(intent: dict) -> dict:
    safe_intent = _safe_intent(intent)
    metadata = build_safe_router_metadata(safe_intent)
    adapted = {
        "source": "local_nlu_adapter",
        "raw_query": safe_intent.get("raw_query", ""),
        "normalized_query": safe_intent.get("normalized_query", ""),
        "router_query": metadata.get("router_query", ""),
        "should_use_local_nlu_intent": bool(metadata.get("should_use_local_nlu_intent", False)),
        "adapter_decision": metadata.get("adapter_decision", "safe_review_only"),
        "router_metadata": metadata,
    }
    return json.loads(json.dumps(adapted, ensure_ascii=True, sort_keys=True))
