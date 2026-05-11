from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

STAGE30_ID = "30"
STAGE30_OFFLINE_ONLY = True
STAGE30_INTERNAL_ONLY = True

COMPARISON_STATUSES = (
    "aligned",
    "disagreement",
    "runtime_unknown",
    "shadow_unknown",
    "both_unknown",
    "manual_review",
    "unsafe_shadow",
    "unsupported",
)

EXPECTED_LEARNING_ACTIONS = (
    "none",
    "collect_failure",
    "suggest_learning",
    "manual_review",
)


@dataclass(frozen=True)
class Stage30ShadowRecord:
    shadow_record_id: str
    stage: str
    runtime_query: str
    normalized_query: str
    timestamp: str
    source_surface: str
    source_route: str
    existing_runtime_decision: str
    existing_runtime_target: str | None
    existing_runtime_vertical: str | None
    shadow_nlu_target: str
    shadow_vertical: str
    shadow_confidence: float | str
    comparison_status: str
    failure_type: str | None
    vertical: str
    language: str
    noise_signals: tuple[str, ...]
    expected_learning_action: str
    offline_only: bool = STAGE30_OFFLINE_ONLY
    internal_only: bool = STAGE30_INTERNAL_ONLY
    did_affect_runtime: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Stage30FailureCandidate:
    candidate_id: str
    source: str
    runtime_query: str
    observed_runtime_decision: str
    observed_runtime_target: str | None
    shadow_decision: str
    shadow_target: str
    failure_type: str
    language: str
    noise_signals: tuple[str, ...]
    vertical: str
    risk_level: str
    manual_review: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Stage30ShadowSummary:
    total_shadow_records: int
    aligned_count: int
    disagreement_count: int
    runtime_unknown_count: int
    shadow_unknown_count: int
    manual_review_count: int
    unsupported_count: int
    by_vertical: dict[str, int]
    by_language: dict[str, int]
    by_noise_signal: dict[str, int]
    top_failure_types: tuple[tuple[str, int], ...]
    offline_only: bool = STAGE30_OFFLINE_ONLY
    internal_only: bool = STAGE30_INTERNAL_ONLY
