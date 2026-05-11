from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

STAGE29_ID = "29"
STAGE29_OFFLINE_MARKER = True

SUGGESTION_APPROVAL_STATUSES = ("pending", "approved", "rejected", "manual_review")
EVALUATION_STATUSES = ("passed", "failed", "manual_review", "unknown", "unsafe_pass")
RISK_LEVELS = ("low", "medium", "high")


@dataclass(frozen=True)
class Stage29SeedRecord:
    seed_id: str
    vertical: str
    canonical_query: str
    expected_nlu_target: str
    expected_intent: str
    language: str
    retail_engine: str | None = None
    mega_category: str | None = None
    google_taxonomy_path: str | None = None
    saas_erp_contract_ref: str | None = None
    finance_insurance_contract_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    offline_only: bool = STAGE29_OFFLINE_MARKER
    test_mode: bool = True


@dataclass(frozen=True)
class Stage29GeneratedQueryRecord:
    record_id: str
    stage: str
    generated_query: str
    canonical_query: str
    source_seed_id: str
    language: str
    vertical: str
    expected_nlu_target: str
    expected_intent: str
    noise_profile: str
    applied_noise_types: tuple[str, ...]
    intent_phrase_type: str
    deterministic_seed: int
    metadata: dict[str, Any] = field(default_factory=dict)
    retail_engine: str | None = None
    category_bucket: str | None = None
    mega_category: str | None = None
    google_taxonomy_path: str | None = None
    saas_erp_contract_ref: str | None = None
    finance_insurance_contract_ref: str | None = None
    offline_only: bool = STAGE29_OFFLINE_MARKER
    test_mode: bool = True


@dataclass(frozen=True)
class Stage29EvaluationRecord:
    generated_query_record_id: str
    generated_query: str
    expected_nlu_target: str
    actual_nlu_target: str
    expected_vertical: str
    actual_vertical: str
    status: str
    failure_type: str | None
    confidence: float | str
    notes: str
    offline_only: bool = STAGE29_OFFLINE_MARKER


@dataclass(frozen=True)
class Stage29FailureRecord:
    failure_id: str
    generated_query_record_id: str
    failure_type: str
    language: str
    vertical: str
    expected_nlu_target: str
    actual_nlu_target: str
    noise_profile: str
    applied_noise_types: tuple[str, ...]
    intent_phrase_type: str
    notes: str
    offline_only: bool = STAGE29_OFFLINE_MARKER


@dataclass(frozen=True)
class Stage29LearningSuggestion:
    suggestion_id: str
    source_failure_ids: tuple[str, ...]
    suggested_target: str
    suggested_rule_or_mapping: str
    reason: str
    examples: tuple[str, ...]
    affected_languages: tuple[str, ...]
    affected_noise_types: tuple[str, ...]
    vertical: str
    risk_level: str
    confidence: float
    approval_status: str = "pending"
    offline_only: bool = STAGE29_OFFLINE_MARKER


@dataclass(frozen=True)
class Stage29UpdatePack:
    pack_id: str
    approved_suggestion_ids: tuple[str, ...]
    proposed_changes: tuple[str, ...]
    risk_summary: dict[str, int]
    examples: tuple[str, ...]
    rollback_notes: str
    validation_status: str
    offline_only: bool = STAGE29_OFFLINE_MARKER


@dataclass(frozen=True)
class Stage29RegressionCase:
    case_id: str
    generated_query: str
    expected_nlu_target: str
    language: str
    noise_profile: str
    vertical: str
    risk_level: str
    original_failure_type: str | None
    offline_only: bool = STAGE29_OFFLINE_MARKER


@dataclass(frozen=True)
class Stage29RegressionPack:
    pack_id: str
    cases: tuple[Stage29RegressionCase, ...]
    source_counts: dict[str, int]
    offline_only: bool = STAGE29_OFFLINE_MARKER
