from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Iterable

from .stage29_contracts import Stage29FailureRecord, Stage29LearningSuggestion


def _risk_for_failure_type(failure_type: str) -> str:
    if failure_type in {"wrong_vertical", "unsafe_pass", "unsupported_interface"}:
        return "high"
    if failure_type in {"wrong_category", "brand_model_spec_failure"}:
        return "medium"
    return "low"


def build_learning_suggestions(
    failures: Iterable[Stage29FailureRecord],
) -> list[Stage29LearningSuggestion]:
    grouped: dict[tuple[str, str, str], list[Stage29FailureRecord]] = defaultdict(list)
    for failure in failures:
        key = (failure.failure_type, failure.vertical, failure.expected_nlu_target)
        grouped[key].append(failure)

    suggestions: list[Stage29LearningSuggestion] = []
    for (failure_type, vertical, target), rows in sorted(grouped.items()):
        failure_ids = tuple(row.failure_id for row in rows)
        languages = tuple(sorted({row.language for row in rows}))
        noise_types = tuple(
            sorted({noise for row in rows for noise in row.applied_noise_types})
        )
        examples = tuple(row.generated_query_record_id for row in rows[:5])
        confidence = round(min(0.95, 0.45 + (0.05 * len(rows))), 2)
        suggestion_id = "s29_sug_" + hashlib.sha1(
            f"{failure_type}|{vertical}|{target}".encode("utf-8")
        ).hexdigest()[:12]
        suggestions.append(
            Stage29LearningSuggestion(
                suggestion_id=suggestion_id,
                source_failure_ids=failure_ids,
                suggested_target=target,
                suggested_rule_or_mapping=f"map_failure:{failure_type}:to:{target}",
                reason=f"Recurring {failure_type} across {len(rows)} offline samples.",
                examples=examples,
                affected_languages=languages,
                affected_noise_types=noise_types,
                vertical=vertical,
                risk_level=_risk_for_failure_type(failure_type),
                confidence=confidence,
                approval_status="pending",
            )
        )
    return suggestions
