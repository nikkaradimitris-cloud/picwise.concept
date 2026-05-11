from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

STAGE31_ID = "31"

ACTIVATION_STATUSES = (
    "disabled",
    "eligible",
    "activated",
    "blocked",
    "rollback",
    "manual_review",
    "unsupported",
)

RISK_LEVELS = ("low", "medium", "high")


@dataclass(frozen=True)
class Stage31ActivationCandidate:
    candidate_id: str
    stage: str
    runtime_query: str
    existing_runtime_decision: str
    existing_runtime_target: str | None
    shadow_nlu_target: str
    shadow_vertical: str
    shadow_confidence: float
    comparison_status: str
    activation_status: str
    activation_reason: str
    block_reasons: tuple[str, ...]
    risk_level: str
    vertical: str
    language: str
    source_shadow_record_id: str | None
    did_affect_runtime: bool
    activation_enabled: bool
    offline_or_internal_marker: bool
    has_rollback_path: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Stage31AuditRecord:
    candidate_id: str
    activation_status: str
    activation_reason: str
    vertical: str
    risk_level: str
    block_reasons: tuple[str, ...]
    did_affect_runtime: bool
    source_shadow_record_id: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Stage31ActivationSummary:
    total_candidates: int
    eligible: int
    activated: int
    blocked: int
    manual_review: int
    unsupported: int
    rollback: int
    disabled: int
    by_vertical: dict[str, int]
    by_block_reason: dict[str, int]
    by_risk_level: dict[str, int]
