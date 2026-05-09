from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .keyword_clusters import KeywordClusterCandidate


class CandidateApprovalStatus(str, Enum):
    APPROVED_CANDIDATE = "approved_candidate"
    REVIEW_REQUIRED = "review_required"
    REJECTED_CANDIDATE = "rejected_candidate"


@dataclass(frozen=True)
class EconomicSignals:
    buying_intent_strength: float
    product_availability: float
    price_target_fit: float
    commission_potential: float
    estimated_traffic: float
    competition_inverse: float
    expected_revenue: float


@dataclass(frozen=True)
class ScoredCandidate:
    candidate: KeywordClusterCandidate
    signals: EconomicSignals
    weighted_score: float
    approval_status: CandidateApprovalStatus
    approval_reason: str


def _clamp_0_1(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def score_candidate(
    candidate: KeywordClusterCandidate,
    *,
    buying_intent_strength: float,
    product_availability: float,
    price_target_fit: float,
    commission_potential: float,
    estimated_traffic: float,
    competition_inverse: float,
    expected_revenue: float,
) -> ScoredCandidate:
    signals = EconomicSignals(
        buying_intent_strength=_clamp_0_1(buying_intent_strength),
        product_availability=_clamp_0_1(product_availability),
        price_target_fit=_clamp_0_1(price_target_fit),
        commission_potential=_clamp_0_1(commission_potential),
        estimated_traffic=_clamp_0_1(estimated_traffic),
        competition_inverse=_clamp_0_1(competition_inverse),
        expected_revenue=_clamp_0_1(expected_revenue),
    )
    weighted_score = (
        signals.buying_intent_strength * 0.23
        + signals.product_availability * 0.18
        + signals.price_target_fit * 0.17
        + signals.commission_potential * 0.17
        + signals.estimated_traffic * 0.12
        + signals.competition_inverse * 0.08
        + signals.expected_revenue * 0.05
    )

    hard_gate_failures = []
    if signals.product_availability < 0.40:
        hard_gate_failures.append("low_availability")
    if signals.commission_potential < 0.35:
        hard_gate_failures.append("low_commission")
    if signals.expected_revenue < 0.30:
        hard_gate_failures.append("weak_expected_revenue")
    if signals.buying_intent_strength < 0.35:
        hard_gate_failures.append("weak_intent")

    if hard_gate_failures:
        status = CandidateApprovalStatus.REJECTED_CANDIDATE
        reason = "hard_gates_failed:" + ",".join(hard_gate_failures)
    elif weighted_score >= 0.70:
        status = CandidateApprovalStatus.APPROVED_CANDIDATE
        reason = "strong_multi_signal_economics"
    elif weighted_score >= 0.45:
        status = CandidateApprovalStatus.REVIEW_REQUIRED
        reason = "mid_confidence_requires_editorial_review"
    else:
        status = CandidateApprovalStatus.REJECTED_CANDIDATE
        reason = "insufficient_economic_score"

    return ScoredCandidate(
        candidate=candidate,
        signals=signals,
        weighted_score=round(weighted_score, 4),
        approval_status=status,
        approval_reason=reason,
    )
