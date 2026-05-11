from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Stage31ActivationConfig:
    activation_enabled: bool = False
    allowed_verticals: tuple[str, ...] = ("retail_physical_products",)
    blocked_verticals: tuple[str, ...] = (
        "finance_insurance_business_finance",
        "finance_insurance",
        "business_finance",
    )
    min_confidence: float = 0.85
    allow_saas_erp: bool = False
    block_ambiguous_queries: bool = True
    block_manual_review: bool = True
    block_unsafe_shadow: bool = True
    require_stage30_alignment_or_safe_disagreement: bool = True
    rollback_on_error: bool = True
    allow_nlu_target_influence: bool = False
    safe_comparison_statuses: tuple[str, ...] = ("aligned", "disagreement")
    unsupported_comparison_statuses: tuple[str, ...] = (
        "unsupported",
        "runtime_unknown",
        "shadow_unknown",
        "both_unknown",
    )
    manual_review_comparison_statuses: tuple[str, ...] = ("manual_review", "unsafe_shadow")
    metadata: dict[str, str] = field(default_factory=dict)


def build_default_stage31_config() -> Stage31ActivationConfig:
    return Stage31ActivationConfig()
