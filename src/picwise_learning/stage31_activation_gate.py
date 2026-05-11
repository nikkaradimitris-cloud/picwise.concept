from __future__ import annotations

from dataclasses import dataclass

from .stage31_config import Stage31ActivationConfig
from .stage31_contracts import Stage31ActivationCandidate


@dataclass(frozen=True)
class Stage31GateResult:
    activation_status: str
    activation_reason: str
    block_reasons: tuple[str, ...]
    risk_level: str


def _is_truthy_marker(candidate: Stage31ActivationCandidate, key: str) -> bool:
    value = candidate.metadata.get(key)
    return bool(value)


def evaluate_stage31_activation_gate(
    candidate: Stage31ActivationCandidate,
    *,
    config: Stage31ActivationConfig,
) -> Stage31GateResult:
    block_reasons: list[str] = []
    query = str(candidate.runtime_query or "").strip()
    vertical = str(candidate.vertical or "").strip()
    comparison_status = str(candidate.comparison_status or "").strip()

    if not candidate.activation_enabled or not config.activation_enabled:
        return Stage31GateResult(
            activation_status="disabled",
            activation_reason="activation_disabled_by_config",
            block_reasons=("activation_disabled",),
            risk_level="low",
        )

    if not query:
        return Stage31GateResult(
            activation_status="unsupported",
            activation_reason="runtime_query_missing",
            block_reasons=("missing_runtime_query",),
            risk_level="high",
        )

    if vertical in config.blocked_verticals:
        return Stage31GateResult(
            activation_status="manual_review",
            activation_reason="blocked_vertical_requires_manual_review",
            block_reasons=("blocked_vertical",),
            risk_level="high",
        )

    if vertical == "software_saas_erp" and not config.allow_saas_erp:
        return Stage31GateResult(
            activation_status="blocked",
            activation_reason="saas_erp_not_enabled",
            block_reasons=("saas_erp_not_enabled",),
            risk_level="medium",
        )

    if vertical and vertical not in config.allowed_verticals and vertical != "software_saas_erp":
        return Stage31GateResult(
            activation_status="unsupported",
            activation_reason="vertical_not_supported",
            block_reasons=("vertical_not_supported",),
            risk_level="high",
        )

    if candidate.shadow_confidence < config.min_confidence:
        block_reasons.append("shadow_confidence_below_threshold")

    if config.require_stage30_alignment_or_safe_disagreement and comparison_status not in config.safe_comparison_statuses:
        block_reasons.append("comparison_status_not_safe")

    if comparison_status in config.unsupported_comparison_statuses:
        return Stage31GateResult(
            activation_status="unsupported",
            activation_reason="comparison_status_unsupported",
            block_reasons=tuple(block_reasons or ["comparison_status_unsupported"]),
            risk_level="high",
        )

    if comparison_status in config.manual_review_comparison_statuses:
        return Stage31GateResult(
            activation_status="manual_review",
            activation_reason="comparison_status_requires_manual_review",
            block_reasons=tuple(block_reasons or ["comparison_status_requires_manual_review"]),
            risk_level="high",
        )

    if config.block_ambiguous_queries and _is_truthy_marker(candidate, "query_is_ambiguous"):
        block_reasons.append("ambiguous_query_blocked")
    if config.block_manual_review and _is_truthy_marker(candidate, "manual_review"):
        block_reasons.append("manual_review_marker_blocked")
    if config.block_unsafe_shadow and _is_truthy_marker(candidate, "unsafe_shadow"):
        block_reasons.append("unsafe_shadow_marker_blocked")
    if _is_truthy_marker(candidate, "unsupported_case"):
        return Stage31GateResult(
            activation_status="unsupported",
            activation_reason="unsupported_case_marker",
            block_reasons=tuple(block_reasons or ["unsupported_case_marker"]),
            risk_level="high",
        )
    if _is_truthy_marker(candidate, "commercial_execution_implied"):
        block_reasons.append("commercial_execution_blocked")

    data_missing = not candidate.shadow_nlu_target or not candidate.existing_runtime_decision
    if data_missing:
        return Stage31GateResult(
            activation_status="unsupported",
            activation_reason="runtime_or_shadow_data_missing",
            block_reasons=tuple(block_reasons or ["runtime_or_shadow_data_missing"]),
            risk_level="high",
        )

    if block_reasons:
        return Stage31GateResult(
            activation_status="blocked",
            activation_reason="activation_blocked_by_guardrails",
            block_reasons=tuple(block_reasons),
            risk_level="medium",
        )

    return Stage31GateResult(
        activation_status="eligible",
        activation_reason="eligible_for_controlled_activation",
        block_reasons=(),
        risk_level="low",
    )
