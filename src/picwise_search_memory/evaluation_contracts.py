from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BlindEvaluationCase:
    case_id: str
    canonical_id: str
    canonical_term: str
    mega_category_id: str
    query: str
    expected_normalized_term: str
    expected_mega_category_id: str
    variant_type: str
    source: str
    should_match: bool

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "canonical_id": self.canonical_id,
            "canonical_term": self.canonical_term,
            "mega_category_id": self.mega_category_id,
            "query": self.query,
            "expected_normalized_term": self.expected_normalized_term,
            "expected_mega_category_id": self.expected_mega_category_id,
            "variant_type": self.variant_type,
            "source": self.source,
            "should_match": self.should_match,
        }


@dataclass(frozen=True)
class BlindEvaluationResult:
    case_id: str
    query: str
    expected_canonical_id: str
    expected_mega_category_id: str
    matched_canonical_id: str
    matched_mega_category_id: str
    status: str
    score: float
    passed: bool
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "query": self.query,
            "expected_canonical_id": self.expected_canonical_id,
            "expected_mega_category_id": self.expected_mega_category_id,
            "matched_canonical_id": self.matched_canonical_id,
            "matched_mega_category_id": self.matched_mega_category_id,
            "status": self.status,
            "score": self.score,
            "passed": self.passed,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class BlindEvaluationThresholds:
    mega_category_accuracy_min: float = 0.90
    canonical_accuracy_min: float = 0.70
    wrong_category_rate_max: float = 0.05
    false_positive_rate_max: float = 0.02
    broad_term_safety_rate_min: float = 0.95

    def to_dict(self) -> dict:
        return {
            "mega_category_accuracy_min": self.mega_category_accuracy_min,
            "canonical_accuracy_min": self.canonical_accuracy_min,
            "wrong_category_rate_max": self.wrong_category_rate_max,
            "false_positive_rate_max": self.false_positive_rate_max,
            "broad_term_safety_rate_min": self.broad_term_safety_rate_min,
        }


@dataclass(frozen=True)
class BlindEvaluationReport:
    total_cases: int
    passed: int
    failed: int
    accuracy: float
    canonical_accuracy: float
    mega_category_accuracy: float
    no_match_rate: float
    wrong_category_rate: float
    false_positive_rate: float
    broad_term_safety_rate: float
    counts_by_mega_category_id: dict[str, int]
    counts_by_variant_type: dict[str, int]
    failed_cases: tuple[BlindEvaluationResult, ...]
    threshold_status: dict[str, bool]
    can_proceed_to_stage5: bool

    def to_dict(self) -> dict:
        return {
            "total_cases": self.total_cases,
            "passed": self.passed,
            "failed": self.failed,
            "accuracy": self.accuracy,
            "canonical_accuracy": self.canonical_accuracy,
            "mega_category_accuracy": self.mega_category_accuracy,
            "no_match_rate": self.no_match_rate,
            "wrong_category_rate": self.wrong_category_rate,
            "false_positive_rate": self.false_positive_rate,
            "broad_term_safety_rate": self.broad_term_safety_rate,
            "counts_by_mega_category_id": dict(sorted(self.counts_by_mega_category_id.items())),
            "counts_by_variant_type": dict(sorted(self.counts_by_variant_type.items())),
            "failed_cases": [row.to_dict() for row in self.failed_cases],
            "threshold_status": dict(sorted(self.threshold_status.items())),
            "can_proceed_to_stage5": self.can_proceed_to_stage5,
        }
