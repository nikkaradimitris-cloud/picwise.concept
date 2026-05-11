from __future__ import annotations

from dataclasses import dataclass

from .stage30_config import Stage30ShadowConfig


@dataclass(frozen=True)
class Stage30ComparisonResult:
    comparison_status: str
    failure_type: str | None
    expected_learning_action: str
    vertical: str
    manual_review: bool


def _is_unknown(value: str | None, *, markers: tuple[str, ...]) -> bool:
    text = str(value or "").strip().lower()
    return text in {marker.lower() for marker in markers}


def compare_runtime_vs_shadow(
    *,
    runtime_target: str | None,
    runtime_vertical: str | None,
    runtime_decision: str,
    shadow_target: str | None,
    shadow_vertical: str | None,
    shadow_status: str,
    shadow_needs_review: bool,
    config: Stage30ShadowConfig,
) -> Stage30ComparisonResult:
    resolved_runtime_vertical = str(runtime_vertical or "").strip() or "unknown"
    resolved_shadow_vertical = str(shadow_vertical or "").strip() or "unknown"
    resolved_vertical = resolved_runtime_vertical if resolved_runtime_vertical != "unknown" else resolved_shadow_vertical

    if resolved_vertical in config.unsupported_verticals:
        return Stage30ComparisonResult(
            comparison_status="unsupported",
            failure_type="unsupported_vertical",
            expected_learning_action="manual_review",
            vertical=resolved_vertical,
            manual_review=True,
        )

    runtime_unknown = _is_unknown(runtime_target, markers=config.unknown_target_markers)
    shadow_unknown = _is_unknown(shadow_target, markers=config.unknown_target_markers)

    if runtime_unknown and shadow_unknown:
        return Stage30ComparisonResult(
            comparison_status="both_unknown",
            failure_type=None,
            expected_learning_action="none",
            vertical=resolved_vertical,
            manual_review=False,
        )
    if runtime_unknown:
        return Stage30ComparisonResult(
            comparison_status="runtime_unknown",
            failure_type="runtime_unknown_target",
            expected_learning_action="collect_failure",
            vertical=resolved_vertical,
            manual_review=False,
        )
    if shadow_unknown:
        return Stage30ComparisonResult(
            comparison_status="shadow_unknown",
            failure_type="shadow_unknown_target",
            expected_learning_action="collect_failure",
            vertical=resolved_vertical,
            manual_review=False,
        )

    if shadow_needs_review or shadow_status in {"ambiguous_needs_review", "manual_review_required"}:
        return Stage30ComparisonResult(
            comparison_status="unsafe_shadow",
            failure_type="shadow_requires_review",
            expected_learning_action="manual_review",
            vertical=resolved_vertical,
            manual_review=True,
        )

    if (
        resolved_runtime_vertical != "unknown"
        and resolved_shadow_vertical != "unknown"
        and resolved_runtime_vertical != resolved_shadow_vertical
    ):
        return Stage30ComparisonResult(
            comparison_status="disagreement",
            failure_type="wrong_vertical",
            expected_learning_action="manual_review",
            vertical=resolved_vertical,
            manual_review=True,
        )

    runtime_target_text = str(runtime_target or "").strip().lower()
    shadow_target_text = str(shadow_target or "").strip().lower()
    if runtime_target_text == shadow_target_text:
        return Stage30ComparisonResult(
            comparison_status="aligned",
            failure_type=None,
            expected_learning_action="none",
            vertical=resolved_vertical,
            manual_review=False,
        )

    regulated = resolved_vertical in config.regulated_verticals
    status = "manual_review" if regulated else "disagreement"
    return Stage30ComparisonResult(
        comparison_status=status,
        failure_type="wrong_category",
        expected_learning_action="manual_review" if regulated else "suggest_learning",
        vertical=resolved_vertical,
        manual_review=regulated or runtime_decision == "manual_review_required",
    )
