from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from .stage30_contracts import Stage30ShadowRecord
from .stage31_contracts import STAGE31_ID, Stage31ActivationCandidate


def _detect_language(query: str, fallback: str = "en") -> str:
    text = str(query or "")
    if any("\u0370" <= char <= "\u03ff" for char in text):
        return "el"
    return fallback


def _derive_risk_level(vertical: str, comparison_status: str) -> str:
    blocked_verticals = {"finance_insurance_business_finance", "finance_insurance", "business_finance"}
    if vertical in blocked_verticals:
        return "high"
    if comparison_status in {"manual_review", "unsafe_shadow", "unsupported"}:
        return "high"
    if comparison_status in {"disagreement", "runtime_unknown", "shadow_unknown", "both_unknown"}:
        return "medium"
    return "low"


def build_stage31_activation_candidate(
    *,
    runtime_query: str,
    runtime_decision: dict[str, Any],
    source_shadow_record: Stage30ShadowRecord | None = None,
    activation_enabled: bool,
    metadata: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> Stage31ActivationCandidate:
    query = str(runtime_query or "")
    runtime_decision_text = str(
        runtime_decision.get("existing_runtime_decision")
        or runtime_decision.get("status")
        or "unknown"
    )
    existing_runtime_target = runtime_decision.get("existing_runtime_target")
    shadow_nlu_target = "unknown"
    shadow_vertical = str(runtime_decision.get("vertical") or runtime_decision.get("existing_runtime_vertical") or "unknown")
    comparison_status = str(runtime_decision.get("comparison_status") or "unsupported")
    confidence = float(runtime_decision.get("shadow_confidence", 0.0) or 0.0)
    vertical = str(runtime_decision.get("vertical") or runtime_decision.get("existing_runtime_vertical") or shadow_vertical or "unknown")
    language = _detect_language(query)
    source_shadow_record_id: str | None = None
    offline_or_internal_marker = True
    if source_shadow_record is not None:
        shadow_nlu_target = str(source_shadow_record.shadow_nlu_target or "unknown")
        shadow_vertical = str(source_shadow_record.shadow_vertical or shadow_vertical or "unknown")
        comparison_status = str(source_shadow_record.comparison_status or comparison_status)
        confidence = float(source_shadow_record.shadow_confidence or 0.0)
        vertical = str(source_shadow_record.vertical or vertical or shadow_vertical)
        language = str(source_shadow_record.language or language or "en")
        source_shadow_record_id = source_shadow_record.shadow_record_id
        offline_or_internal_marker = bool(source_shadow_record.offline_only or source_shadow_record.internal_only)
    else:
        shadow_nlu_target = str(runtime_decision.get("shadow_nlu_target") or existing_runtime_target or "unknown")
    resolved_timestamp = timestamp or datetime.now(UTC).isoformat()
    payload = "|".join(
        [
            query.strip().lower(),
            runtime_decision_text.strip().lower(),
            str(shadow_nlu_target).strip().lower(),
            str(resolved_timestamp),
        ]
    )
    candidate_id = "s31_activation_" + hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    resolved_metadata = {
        "runtime_route_type": str(runtime_decision.get("route_type") or ""),
        "manual_review": bool(runtime_decision.get("status") == "manual_review_required"),
        "query_is_ambiguous": bool(runtime_decision.get("route_type") == "ambiguous_query"),
        "unsafe_shadow": comparison_status == "unsafe_shadow",
        "unsupported_case": comparison_status == "unsupported",
        "commercial_execution_implied": False,
        "timestamp": resolved_timestamp,
    }
    if metadata:
        resolved_metadata.update(metadata)
    return Stage31ActivationCandidate(
        candidate_id=candidate_id,
        stage=STAGE31_ID,
        runtime_query=query,
        existing_runtime_decision=runtime_decision_text,
        existing_runtime_target=str(existing_runtime_target) if existing_runtime_target is not None else None,
        shadow_nlu_target=str(shadow_nlu_target or "unknown"),
        shadow_vertical=str(shadow_vertical or "unknown"),
        shadow_confidence=confidence,
        comparison_status=str(comparison_status or "unsupported"),
        activation_status="disabled" if not activation_enabled else "eligible",
        activation_reason="activation_disabled_by_config" if not activation_enabled else "pending_gate_evaluation",
        block_reasons=(),
        risk_level=_derive_risk_level(str(vertical or "unknown"), str(comparison_status or "unsupported")),
        vertical=str(vertical or "unknown"),
        language=str(language or "en"),
        source_shadow_record_id=source_shadow_record_id,
        did_affect_runtime=False,
        activation_enabled=bool(activation_enabled),
        offline_or_internal_marker=offline_or_internal_marker,
        has_rollback_path=True,
        metadata=resolved_metadata,
    )
