from __future__ import annotations

from .stage31_contracts import ACTIVATION_STATUSES, RISK_LEVELS, STAGE31_ID, Stage31ActivationCandidate


def _require(value: str | None, name: str, errors: list[str]) -> None:
    if not str(value or "").strip():
        errors.append(f"missing:{name}")


def validate_stage31_activation_candidate(candidate: Stage31ActivationCandidate) -> dict[str, object]:
    errors: list[str] = []
    _require(candidate.candidate_id, "candidate_id", errors)
    _require(candidate.runtime_query, "runtime_query", errors)
    _require(candidate.existing_runtime_decision, "existing_runtime_decision", errors)
    _require(candidate.shadow_nlu_target, "shadow_nlu_target", errors)
    _require(candidate.shadow_vertical, "shadow_vertical", errors)
    _require(candidate.comparison_status, "comparison_status", errors)
    _require(candidate.activation_reason, "activation_reason", errors)
    _require(candidate.vertical, "vertical", errors)
    _require(candidate.language, "language", errors)
    if candidate.stage != STAGE31_ID:
        errors.append("stage_must_be_31")
    if candidate.activation_status not in ACTIVATION_STATUSES:
        errors.append("invalid_activation_status")
    if candidate.risk_level not in RISK_LEVELS:
        errors.append("invalid_risk_level")
    if candidate.did_affect_runtime and not candidate.activation_enabled:
        errors.append("runtime_impact_requires_activation_enabled")
    if not candidate.has_rollback_path:
        errors.append("missing_rollback_default_path")
    if candidate.activation_status in {"blocked", "manual_review", "unsupported"} and not candidate.block_reasons:
        errors.append("missing_block_reasons")

    vertical = str(candidate.vertical).lower()
    finance_markers = {"finance_insurance_business_finance", "finance_insurance", "business_finance"}
    if vertical in finance_markers and candidate.activation_status == "activated":
        errors.append("finance_activation_requires_manual_review")

    unsafe_states = {"manual_review", "unsafe_shadow", "unsupported", "ambiguous"}
    comparison = str(candidate.comparison_status).lower()
    metadata_markers = (
        bool(candidate.metadata.get("manual_review")),
        bool(candidate.metadata.get("unsafe_shadow")),
        bool(candidate.metadata.get("unsupported_case")),
        bool(candidate.metadata.get("query_is_ambiguous")),
    )
    if candidate.activation_status == "activated" and (comparison in unsafe_states or any(metadata_markers)):
        errors.append("unsafe_or_ambiguous_case_cannot_activate")
    return {"valid": not errors, "errors": errors}
