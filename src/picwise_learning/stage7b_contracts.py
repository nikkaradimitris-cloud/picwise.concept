from __future__ import annotations

from dataclasses import dataclass, field

SEARCH_LEARNING_APPROVAL_STATUSES: tuple[str, ...] = (
    "pending_human_review",
    "approved",
    "rejected",
)

SEARCH_LEARNING_CLASSIFICATIONS: tuple[str, ...] = (
    "not_understood",
    "low_confidence",
    "ambiguous",
    "wrong_category",
    "provider_not_connected",
    "broad_negative_safe",
    "connected_provider_result",
    "false_positive_risk",
    "no_action_needed",
)


@dataclass(frozen=True)
class SearchLearningCase:
    query: str
    normalized_query: str
    observed_status: str
    expected_behavior: str
    matched_canonical_id: str
    matched_mega_category_id: str
    confidence: float
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    source: str = "offline_learning"
    review_status: str = "pending_human_review"

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "normalized_query": self.normalized_query,
            "observed_status": self.observed_status,
            "expected_behavior": self.expected_behavior,
            "matched_canonical_id": self.matched_canonical_id,
            "matched_mega_category_id": self.matched_mega_category_id,
            "confidence": self.confidence,
            "reason_codes": list(self.reason_codes),
            "source": self.source,
            "review_status": self.review_status,
        }


@dataclass(frozen=True)
class SearchLearningResult:
    case: SearchLearningCase
    classification: str
    requires_review: bool

    def to_dict(self) -> dict:
        return {
            "case": self.case.to_dict(),
            "classification": self.classification,
            "requires_review": self.requires_review,
        }


@dataclass(frozen=True)
class SearchLearningSuggestion:
    suggestion_id: str
    suggestion_type: str
    proposed_action: str
    target_layer: str
    affected_category: str
    evidence: tuple[str, ...] = field(default_factory=tuple)
    risk_level: str = "medium"
    requires_human_approval: bool = True
    can_auto_apply: bool = False

    def __post_init__(self) -> None:
        if not self.requires_human_approval:
            raise ValueError("SearchLearningSuggestion requires human approval")
        if self.can_auto_apply:
            raise ValueError("SearchLearningSuggestion can_auto_apply must always be False")

    def to_dict(self) -> dict:
        return {
            "suggestion_id": self.suggestion_id,
            "suggestion_type": self.suggestion_type,
            "proposed_action": self.proposed_action,
            "target_layer": self.target_layer,
            "affected_category": self.affected_category,
            "evidence": list(self.evidence),
            "risk_level": self.risk_level,
            "requires_human_approval": self.requires_human_approval,
            "can_auto_apply": False,
        }


@dataclass(frozen=True)
class SearchLearningApprovalStatus:
    suggestion_id: str
    status: str
    reviewer: str = ""
    review_notes: str = ""

    def to_dict(self) -> dict:
        return {
            "suggestion_id": self.suggestion_id,
            "status": self.status,
            "reviewer": self.reviewer,
            "review_notes": self.review_notes,
        }


@dataclass(frozen=True)
class SearchLearningReport:
    total_cases: int
    not_understood_count: int
    low_confidence_count: int
    ambiguous_count: int
    wrong_category_count: int
    provider_not_connected_count: int
    broad_negative_safe_count: int
    connected_provider_result_count: int
    false_positive_risk_count: int
    suggestions_by_type: dict[str, int]
    suggestions_requiring_approval: int
    can_auto_apply_anything: bool
    results: tuple[SearchLearningResult, ...] = field(default_factory=tuple)
    suggestions: tuple[SearchLearningSuggestion, ...] = field(default_factory=tuple)
    sources: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "total_cases": self.total_cases,
            "not_understood_count": self.not_understood_count,
            "low_confidence_count": self.low_confidence_count,
            "ambiguous_count": self.ambiguous_count,
            "wrong_category_count": self.wrong_category_count,
            "provider_not_connected_count": self.provider_not_connected_count,
            "broad_negative_safe_count": self.broad_negative_safe_count,
            "connected_provider_result_count": self.connected_provider_result_count,
            "false_positive_risk_count": self.false_positive_risk_count,
            "suggestions_by_type": dict(sorted(self.suggestions_by_type.items())),
            "suggestions_requiring_approval": self.suggestions_requiring_approval,
            "can_auto_apply_anything": False,
            "results": [row.to_dict() for row in self.results],
            "suggestions": [row.to_dict() for row in self.suggestions],
            "sources": list(self.sources),
        }

