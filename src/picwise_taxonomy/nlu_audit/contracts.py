from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from picwise_taxonomy.nlu_training import NLUTrainingPackBuildResult


class NLUCoverageStrength(str, Enum):
    STRONG = "strong"
    PARTIAL = "partial"
    THIN = "thin"
    INSUFFICIENT_DATA = "insufficient_data"
    NEEDS_REVIEW = "needs_review"


class NLUSafetyStatus(str, Enum):
    SAFE = "safe"
    REVIEW_REQUIRED = "review_required"
    INVALID_UNSAFE_PASS = "invalid_unsafe_pass"


@dataclass(frozen=True)
class NLUMegaCategoryAuditRow:
    mega_category_id: str
    engine_id: str
    pack_status: str
    coverage_strength: NLUCoverageStrength
    safety_status: NLUSafetyStatus
    total_examples: int
    safe_examples: int
    review_only_examples: int
    disabled_gap_examples: int
    unsafe_passes: int
    examples_by_variant_type: dict[str, int] = field(default_factory=dict)
    examples_by_language_script: dict[str, int] = field(default_factory=dict)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class NLUCoverageAuditInput:
    training_result: NLUTrainingPackBuildResult | None = None
    stage_title: str = "Stage 27C — NLU Coverage / Safety Audit"


@dataclass(frozen=True)
class NLUCoverageAuditResult:
    rows: tuple[NLUMegaCategoryAuditRow, ...]
    total_mega_categories: int
    strong_count: int
    partial_count: int
    thin_count: int
    insufficient_data_count: int
    needs_review_count: int
    total_examples: int
    safe_examples: int
    review_only_examples: int
    disabled_gap_examples: int
    unsafe_passes: int
    examples_by_variant_type: dict[str, int]
    examples_by_language_script: dict[str, int]
    examples_by_engine: dict[str, int]
    examples_by_mega_category: dict[str, int]
    valid: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)
    stage_title: str = "Stage 27C — NLU Coverage / Safety Audit"
