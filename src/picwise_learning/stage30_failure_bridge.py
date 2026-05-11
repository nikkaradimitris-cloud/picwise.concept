from __future__ import annotations

import hashlib
from collections.abc import Iterable

from .stage30_contracts import Stage30FailureCandidate, Stage30ShadowRecord


def _risk_level_for(record: Stage30ShadowRecord) -> str:
    if record.vertical == "finance_insurance_business_finance":
        return "high"
    if record.comparison_status in {"manual_review", "unsafe_shadow", "unsupported"}:
        return "high"
    if record.comparison_status in {"disagreement", "runtime_unknown", "shadow_unknown"}:
        return "medium"
    return "low"


def build_failure_candidate(record: Stage30ShadowRecord) -> Stage30FailureCandidate | None:
    if record.expected_learning_action == "none":
        return None
    failure_type = str(record.failure_type or "").strip() or "shadow_disagreement"
    payload = "|".join([record.shadow_record_id, failure_type, record.runtime_query.strip().lower()])
    candidate_id = "s30_fail_" + hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    manual_review = (
        record.expected_learning_action == "manual_review"
        or record.vertical == "finance_insurance_business_finance"
        or record.comparison_status in {"manual_review", "unsafe_shadow", "unsupported"}
    )
    return Stage30FailureCandidate(
        candidate_id=candidate_id,
        source="runtime_shadow",
        runtime_query=record.runtime_query,
        observed_runtime_decision=record.existing_runtime_decision,
        observed_runtime_target=record.existing_runtime_target,
        shadow_decision=record.comparison_status,
        shadow_target=record.shadow_nlu_target,
        failure_type=failure_type,
        language=record.language,
        noise_signals=record.noise_signals,
        vertical=record.vertical,
        risk_level=_risk_level_for(record),
        manual_review=manual_review,
        metadata={
            "shadow_record_id": record.shadow_record_id,
            "expected_learning_action": record.expected_learning_action,
        },
    )


def build_failure_candidates(records: Iterable[Stage30ShadowRecord]) -> list[Stage30FailureCandidate]:
    output: list[Stage30FailureCandidate] = []
    for record in records:
        candidate = build_failure_candidate(record)
        if candidate is not None:
            output.append(candidate)
    return output
