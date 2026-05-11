from __future__ import annotations

import hashlib
from collections import Counter

from .stage29_contracts import (
    Stage29EvaluationRecord,
    Stage29GeneratedQueryRecord,
    Stage29LearningSuggestion,
    Stage29RegressionCase,
    Stage29RegressionPack,
)


def _case_id(*parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"s29_reg_{digest}"


def build_regression_pack(
    generated_records: list[Stage29GeneratedQueryRecord],
    evaluations: list[Stage29EvaluationRecord],
    approved_suggestions: list[Stage29LearningSuggestion],
    all_suggestions: list[Stage29LearningSuggestion],
) -> Stage29RegressionPack:
    eval_by_id = {row.generated_query_record_id: row for row in evaluations}
    cases: list[Stage29RegressionCase] = []

    for row in generated_records:
        evaluation = eval_by_id.get(row.record_id)
        failure_type = evaluation.failure_type if evaluation else None
        risk = "medium" if failure_type else "low"
        if failure_type in {"unsafe_pass", "wrong_vertical"}:
            risk = "high"
        cases.append(
            Stage29RegressionCase(
                case_id=_case_id(row.record_id, row.language, row.noise_profile),
                generated_query=row.generated_query,
                expected_nlu_target=row.expected_nlu_target,
                language=row.language,
                noise_profile=row.noise_profile,
                vertical=row.vertical,
                risk_level=risk,
                original_failure_type=failure_type,
            )
        )

    for suggestion in all_suggestions:
        if suggestion.approval_status in {"rejected", "manual_review"} and suggestion.risk_level == "high":
            cases.append(
                Stage29RegressionCase(
                    case_id=_case_id(suggestion.suggestion_id, "high_risk"),
                    generated_query=f"guardrail:{suggestion.suggestion_id}",
                    expected_nlu_target=suggestion.suggested_target,
                    language=suggestion.affected_languages[0] if suggestion.affected_languages else "en",
                    noise_profile="guardrail",
                    vertical=suggestion.vertical,
                    risk_level="high",
                    original_failure_type="manual_review",
                )
            )

    source_counts = Counter(
        "approved_suggestion_case" if case.generated_query.startswith("guardrail:") else "generated_case"
        for case in cases
    )
    source_counts["approved_suggestions"] = len(approved_suggestions)

    return Stage29RegressionPack(
        pack_id=f"s29_regression_pack_{len(cases)}",
        cases=tuple(cases),
        source_counts=dict(source_counts),
    )
