from __future__ import annotations

from typing import Any

_RESOLVED_STATUSES = {
    "intent_resolved",
    "specific_product_resolved",
    "general_intent_resolved",
}

_REVIEW_STATUSES = {
    "ambiguous_needs_review",
    "manual_review_required",
    "insufficient_data",
    "no_safe_result",
    "invalid_intent",
}


def clamp_confidence(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if numeric < 0.0:
        return 0.0
    if numeric > 1.0:
        return 1.0
    return round(numeric, 2)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _has_conflict(analysis: dict[str, Any]) -> bool:
    category = analysis.get("category")
    models = [str(item).lower() for item in _as_list(analysis.get("model_candidates"))]
    specs = _as_dict(analysis.get("specs"))
    priorities = [str(item).lower() for item in _as_list(analysis.get("buying_priority"))]
    reasons = [str(item).lower() for item in _as_list(analysis.get("reason_codes"))]

    has_tyre_size = all(specs.get(key) for key in ("width", "profile", "rim"))
    has_powerbank_spec = bool(specs.get("capacity_mah"))
    has_calc_spec = bool(specs.get("model_code"))
    has_fx_model = any(model.startswith("fx-") for model in models)

    if "ambiguous_category_signals" in reasons:
        return True
    if category == "car_tyres" and (has_powerbank_spec or has_calc_spec or has_fx_model):
        return True
    if category == "calculators" and (has_tyre_size or has_powerbank_spec):
        return True
    if category == "power_banks" and (has_tyre_size or has_calc_spec):
        return True
    if category == "power_banks" and "low_noise" in priorities:
        return True
    if category == "chargers" and has_tyre_size:
        return True
    return False


def _infer_query_type(analysis: dict[str, Any], conflict: bool) -> str:
    category = analysis.get("category")
    brands = _as_list(analysis.get("brand_candidates"))
    models = _as_list(analysis.get("model_candidates"))
    specs = _as_dict(analysis.get("specs"))
    priorities = _as_list(analysis.get("buying_priority"))

    if conflict:
        return "ambiguous_query"

    has_tyre_size = all(specs.get(key) for key in ("width", "profile", "rim"))
    has_specific_specs = has_tyre_size or bool(specs.get("capacity_mah")) or bool(specs.get("model_code"))
    generic_powerbank_models = {"10000mah", "20000mah", "magsafe"}
    only_generic_powerbank_models = bool(
        category == "power_banks"
        and models
        and all(str(model).lower() in generic_powerbank_models for model in models)
    )
    has_specific_signals = bool(
        category
        and models
        and (brands or has_specific_specs)
        and not only_generic_powerbank_models
    )
    if has_specific_signals:
        return "specific_product"

    has_general_signals = bool(category and (brands or priorities or specs or category == "chargers"))
    if has_general_signals:
        return "general_intent"

    if category is None and (brands or models or priorities or specs):
        return "ambiguous_query"
    return "unknown"


def score_detector_analysis(analysis: dict, raw_query: str = "") -> dict:
    payload = dict(analysis or {})
    raw = str(raw_query or "").strip()
    category = payload.get("category")
    brands = _as_list(payload.get("brand_candidates"))
    models = _as_list(payload.get("model_candidates"))
    specs = _as_dict(payload.get("specs"))
    priorities = _as_list(payload.get("buying_priority"))
    base_conf = clamp_confidence(payload.get("confidence", 0.0))
    reason_codes = [str(item).strip() for item in _as_list(payload.get("reason_codes")) if str(item).strip()]

    conflict = _has_conflict(payload)
    query_type = _infer_query_type(payload, conflict)

    score = base_conf * 0.55
    if category:
        score += 0.2
    if brands:
        score += 0.1
    if models:
        score += 0.14
    if priorities:
        score += 0.07
    if specs:
        score += min(0.16, 0.04 * len(specs))
    if query_type == "specific_product":
        score += 0.08
    if query_type == "ambiguous_query":
        score -= 0.22
    if query_type == "unknown":
        score -= 0.28
    if conflict:
        score -= 0.2
        reason_codes.append("conflicting_signals_detected")
    if not raw:
        score = 0.0
        reason_codes.append("empty_raw_query")

    confidence = clamp_confidence(score)
    if query_type in {"unknown", "ambiguous_query"}:
        confidence = clamp_confidence(min(confidence, 0.49))

    reason_codes.append(f"query_type_{query_type}")
    return {
        "category": category,
        "brand_candidates": list(brands),
        "model_candidates": list(models),
        "specs": dict(specs),
        "buying_priority": list(priorities),
        "query_type": query_type,
        "confidence": confidence,
        "has_conflict": conflict,
        "reason_codes": sorted(set(reason_codes)),
    }


def resolve_safe_status(analysis: dict, confidence: float, raw_query: str = "") -> dict:
    payload = dict(analysis or {})
    raw = str(raw_query or "").strip()
    query_type = str(payload.get("query_type") or "unknown")
    category = payload.get("category")
    brands = _as_list(payload.get("brand_candidates"))
    models = _as_list(payload.get("model_candidates"))
    specs = _as_dict(payload.get("specs"))
    priorities = _as_list(payload.get("buying_priority"))
    reasons = [str(item).strip() for item in _as_list(payload.get("reason_codes")) if str(item).strip()]
    bounded_conf = clamp_confidence(confidence)
    conflict = bool(payload.get("has_conflict", False))

    has_meaningful_signals = bool(category or brands or models or specs or priorities)
    has_tyre_size = all(specs.get(key) for key in ("width", "profile", "rim"))
    has_specific_specs = has_tyre_size or bool(specs.get("capacity_mah")) or bool(specs.get("model_code"))
    strong_specific = bool(category and models and (brands or has_specific_specs))
    strong_general = bool(category and (priorities or brands or specs or category == "chargers"))

    status = "manual_review_required"
    if not raw:
        status = "invalid_intent"
        reasons.append("empty_raw_query")
    elif conflict or query_type == "ambiguous_query":
        status = "ambiguous_needs_review"
    elif not has_meaningful_signals:
        status = "insufficient_data"
    elif bounded_conf < 0.4:
        status = "manual_review_required"
        reasons.append("low_confidence_requires_review")
    elif strong_specific and query_type == "specific_product" and bounded_conf >= 0.72:
        status = "specific_product_resolved"
    elif strong_general and query_type in {"general_intent", "specific_product"} and bounded_conf >= 0.52:
        status = "general_intent_resolved"
    elif query_type == "unknown":
        status = "insufficient_data"
    else:
        status = "no_safe_result"

    needs_review = status in _REVIEW_STATUSES
    if status in _RESOLVED_STATUSES and bounded_conf < 0.5:
        status = "manual_review_required"
        needs_review = True
        reasons.append("low_confidence_resolution_blocked")

    return {
        "status": status,
        "needs_review": needs_review,
        "confidence": bounded_conf,
        "reason_codes": sorted(set(reasons)),
    }
