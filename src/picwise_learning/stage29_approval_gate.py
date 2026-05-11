from __future__ import annotations

from .stage29_contracts import SUGGESTION_APPROVAL_STATUSES, Stage29LearningSuggestion


def set_approval_status(
    suggestion: Stage29LearningSuggestion,
    status: str,
) -> Stage29LearningSuggestion:
    normalized = str(status or "").strip().lower()
    if normalized not in SUGGESTION_APPROVAL_STATUSES:
        raise ValueError(f"Unsupported approval status: {status}")
    return Stage29LearningSuggestion(
        suggestion_id=suggestion.suggestion_id,
        source_failure_ids=suggestion.source_failure_ids,
        suggested_target=suggestion.suggested_target,
        suggested_rule_or_mapping=suggestion.suggested_rule_or_mapping,
        reason=suggestion.reason,
        examples=suggestion.examples,
        affected_languages=suggestion.affected_languages,
        affected_noise_types=suggestion.affected_noise_types,
        vertical=suggestion.vertical,
        risk_level=suggestion.risk_level,
        confidence=suggestion.confidence,
        approval_status=normalized,
        offline_only=suggestion.offline_only,
    )


def filter_approved_suggestions(
    suggestions: list[Stage29LearningSuggestion],
) -> list[Stage29LearningSuggestion]:
    return [row for row in suggestions if row.approval_status == "approved"]
