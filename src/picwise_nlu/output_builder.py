from __future__ import annotations

from typing import Any

from .confidence import resolve_safe_status, score_detector_analysis
from .contract import LOCAL_NLU_SCHEMA_VERSION, LOCAL_NLU_SOURCE, LocalNLUIntent
from .detector_pipeline import analyze_normalized_query
from .normalizer import normalize_query
from .typo_normalizer import normalize_greeklish_and_typos
from .validation import validate_local_nlu_intent


def _merge_reasons(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for code in group:
            text = str(code).strip()
            if text and text not in seen:
                merged.append(text)
                seen.add(text)
    return merged


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def build_local_nlu_intent_from_normalized(raw_query: str, normalized_query: str) -> dict:
    raw = str(raw_query or "").strip()
    normalized_input = str(normalized_query or "").strip()
    if not normalized_input and raw:
        normalized_input = normalize_query(raw)
    normalized = normalize_greeklish_and_typos(normalized_input)

    analysis = analyze_normalized_query(normalized)
    scored = score_detector_analysis(analysis, raw_query=raw)
    safe_status = resolve_safe_status(scored, scored.get("confidence", 0.0), raw_query=raw)

    payload = LocalNLUIntent(
        raw_query=raw,
        normalized_query=normalized or None,
        query_type=str(scored.get("query_type", "unknown")),
        category=scored.get("category"),
        brand_candidates=_as_str_list(scored.get("brand_candidates")),
        model_candidates=_as_str_list(scored.get("model_candidates")),
        specs=dict(scored.get("specs", {})) if isinstance(scored.get("specs"), dict) else {},
        buying_priority=_as_str_list(scored.get("buying_priority")),
        confidence=float(safe_status.get("confidence", 0.0)),
        needs_review=bool(safe_status.get("needs_review", True)),
        status=str(safe_status.get("status", "manual_review_required")),
        reason_codes=_merge_reasons(
            _as_str_list(analysis.get("reason_codes")),
            _as_str_list(scored.get("reason_codes")),
            _as_str_list(safe_status.get("reason_codes")),
        ),
        source=LOCAL_NLU_SOURCE,
        schema_version=LOCAL_NLU_SCHEMA_VERSION,
    ).to_dict()
    return validate_local_nlu_intent(payload)


def build_local_nlu_intent(raw_query: str) -> dict:
    raw = str(raw_query or "")
    normalized = normalize_query(raw)
    return build_local_nlu_intent_from_normalized(raw_query=raw, normalized_query=normalized)
