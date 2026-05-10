from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .contract import (
    ALLOWED_QUERY_TYPES,
    ALLOWED_STATUSES,
    LOCAL_NLU_SCHEMA_VERSION,
    LOCAL_NLU_SOURCE,
    REVIEW_REQUIRED_STATUSES,
    LocalNLUIntent,
)


def _as_reason_codes(reason_codes: Any) -> list[str]:
    if not isinstance(reason_codes, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for code in reason_codes:
        text = str(code).strip()
        if text and text not in seen:
            normalized.append(text)
            seen.add(text)
    return normalized


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _normalize_specs(specs: Any) -> dict[str, Any]:
    if not isinstance(specs, Mapping):
        return {}
    normalized: dict[str, Any] = {}
    for key in sorted(specs.keys(), key=lambda raw_key: str(raw_key)):
        normalized[str(key)] = specs[key]
    return normalized


def _compact_spaces(text: str) -> str:
    return " ".join(text.strip().split())


def _json_sanitize(payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return json.loads(json.dumps(payload, sort_keys=True, ensure_ascii=True))
    except (TypeError, ValueError):
        return None


def build_safe_manual_review_intent(
    raw_query: Any, reason_codes: list[str] | None = None
) -> dict[str, Any]:
    raw = str(raw_query or "").strip()
    reason_list = _as_reason_codes(reason_codes)
    if not reason_list:
        reason_list = ["manual_review_required"]
    intent = LocalNLUIntent(
        raw_query=raw,
        normalized_query=_compact_spaces(raw.lower()) if raw else None,
        query_type="ambiguous_query",
        category=None,
        brand_candidates=[],
        model_candidates=[],
        specs={},
        buying_priority=[],
        confidence=0.0,
        needs_review=True,
        status="manual_review_required",
        reason_codes=reason_list,
        source=LOCAL_NLU_SOURCE,
        schema_version=LOCAL_NLU_SCHEMA_VERSION,
    ).to_dict()
    return _json_sanitize(intent) or {
        "raw_query": raw,
        "normalized_query": None,
        "query_type": "ambiguous_query",
        "category": None,
        "brand_candidates": [],
        "model_candidates": [],
        "specs": {},
        "buying_priority": [],
        "confidence": 0.0,
        "needs_review": True,
        "status": "manual_review_required",
        "reason_codes": reason_list,
        "source": LOCAL_NLU_SOURCE,
        "schema_version": LOCAL_NLU_SCHEMA_VERSION,
    }


def build_invalid_intent(raw_query: Any, reason_codes: list[str] | None = None) -> dict[str, Any]:
    raw = str(raw_query or "").strip()
    reason_list = _as_reason_codes(reason_codes)
    if not reason_list:
        reason_list = ["invalid_intent_payload"]
    intent = LocalNLUIntent(
        raw_query=raw,
        normalized_query=_compact_spaces(raw.lower()) if raw else None,
        query_type="unknown",
        category=None,
        brand_candidates=[],
        model_candidates=[],
        specs={},
        buying_priority=[],
        confidence=0.0,
        needs_review=True,
        status="invalid_intent",
        reason_codes=reason_list,
        source=LOCAL_NLU_SOURCE,
        schema_version=LOCAL_NLU_SCHEMA_VERSION,
    ).to_dict()
    return _json_sanitize(intent) or {
        "raw_query": raw,
        "normalized_query": None,
        "query_type": "unknown",
        "category": None,
        "brand_candidates": [],
        "model_candidates": [],
        "specs": {},
        "buying_priority": [],
        "confidence": 0.0,
        "needs_review": True,
        "status": "invalid_intent",
        "reason_codes": reason_list,
        "source": LOCAL_NLU_SOURCE,
        "schema_version": LOCAL_NLU_SCHEMA_VERSION,
    }


def validate_local_nlu_intent(intent: Any) -> dict[str, Any]:
    if isinstance(intent, LocalNLUIntent):
        payload: dict[str, Any] = intent.to_dict()
    elif isinstance(intent, Mapping):
        payload = dict(intent)
    else:
        return build_invalid_intent("", ["intent_not_mapping"])

    raw_query = str(payload.get("raw_query", "")).strip()
    if not raw_query:
        return build_invalid_intent("", ["missing_raw_query"])

    query_type = str(payload.get("query_type", "")).strip()
    if query_type not in ALLOWED_QUERY_TYPES:
        return build_invalid_intent(raw_query, ["invalid_query_type"])

    status = str(payload.get("status", "")).strip()
    if status not in ALLOWED_STATUSES:
        return build_invalid_intent(raw_query, ["invalid_status"])

    brand_value = payload.get("brand_candidates", [])
    if not isinstance(brand_value, list):
        return build_invalid_intent(raw_query, ["brand_candidates_not_list"])

    model_value = payload.get("model_candidates", [])
    if not isinstance(model_value, list):
        return build_invalid_intent(raw_query, ["model_candidates_not_list"])

    buying_priority_value = payload.get("buying_priority", [])
    if not isinstance(buying_priority_value, list):
        return build_invalid_intent(raw_query, ["buying_priority_not_list"])

    reason_codes_value = payload.get("reason_codes", [])
    if not isinstance(reason_codes_value, list):
        return build_invalid_intent(raw_query, ["reason_codes_not_list"])

    confidence_raw = payload.get("confidence", 0.0)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        return build_invalid_intent(raw_query, ["invalid_confidence_type"])
    if confidence < 0.0 or confidence > 1.0:
        return build_invalid_intent(raw_query, ["confidence_out_of_range"])

    needs_review = bool(payload.get("needs_review", False))
    if status in REVIEW_REQUIRED_STATUSES:
        needs_review = True

    specs_value = payload.get("specs", {})
    if not isinstance(specs_value, Mapping):
        return build_invalid_intent(raw_query, ["specs_not_object"])

    category_raw = payload.get("category")
    category = str(category_raw).strip() if category_raw is not None else None
    if category == "":
        category = None

    normalized_query_raw = payload.get("normalized_query")
    if normalized_query_raw is None:
        normalized_query = _compact_spaces(raw_query.lower())
    else:
        normalized_query = _compact_spaces(str(normalized_query_raw)) or None

    validated = LocalNLUIntent(
        raw_query=raw_query,
        normalized_query=normalized_query,
        query_type=query_type,
        category=category,
        brand_candidates=_normalize_string_list(brand_value),
        model_candidates=_normalize_string_list(model_value),
        specs=_normalize_specs(specs_value),
        buying_priority=_normalize_string_list(buying_priority_value),
        confidence=confidence,
        needs_review=needs_review,
        status=status,
        reason_codes=_as_reason_codes(reason_codes_value),
        source=LOCAL_NLU_SOURCE,
        schema_version=LOCAL_NLU_SCHEMA_VERSION,
    ).to_dict()

    safe_payload = _json_sanitize(validated)
    if safe_payload is None:
        return build_invalid_intent(raw_query, ["non_serializable_payload"])
    return safe_payload
