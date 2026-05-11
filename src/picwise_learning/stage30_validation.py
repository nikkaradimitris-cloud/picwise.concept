from __future__ import annotations

from .stage30_contracts import COMPARISON_STATUSES, EXPECTED_LEARNING_ACTIONS, STAGE30_ID, Stage30ShadowRecord


def _require(value: str | None, name: str, errors: list[str]) -> None:
    if not str(value or "").strip():
        errors.append(f"missing:{name}")


def validate_shadow_record(record: Stage30ShadowRecord) -> dict[str, object]:
    errors: list[str] = []
    _require(record.shadow_record_id, "shadow_record_id", errors)
    _require(record.runtime_query, "runtime_query", errors)
    _require(record.timestamp, "timestamp", errors)
    _require(record.existing_runtime_decision, "existing_runtime_decision", errors)
    _require(record.shadow_nlu_target, "shadow_nlu_target", errors)
    _require(record.shadow_vertical, "shadow_vertical", errors)
    _require(record.vertical, "vertical", errors)
    _require(record.language, "language", errors)
    if record.stage != STAGE30_ID:
        errors.append("stage_must_be_30")
    if record.comparison_status not in COMPARISON_STATUSES:
        errors.append("invalid_comparison_status")
    if record.expected_learning_action not in EXPECTED_LEARNING_ACTIONS:
        errors.append("invalid_expected_learning_action")
    if record.did_affect_runtime:
        errors.append("runtime_mutation_not_allowed")
    if not record.offline_only:
        errors.append("offline_only_required")
    if not record.internal_only:
        errors.append("internal_only_required")
    return {"valid": not errors, "errors": errors}
