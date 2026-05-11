from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import OfferCandidate


class RecommendationStatus(str, Enum):
    READY = "ready"
    NOT_ENOUGH_VALID_CANDIDATES = "not_enough_valid_candidates"
    NO_VALID_CANDIDATES = "no_valid_candidates"
    MANUAL_REVIEW = "manual_review"


class RecommendationReason(str, Enum):
    STRONG_TITLE_MATCH = "strong_title_match"
    AVAILABLE_NOW = "available_now"
    PRICE_PRESENT = "price_present"
    AFFILIATE_LINK_PRESENT = "affiliate_link_present"
    TRUSTED_SELLER = "trusted_seller"
    DATA_COMPLETENESS_HIGH = "data_completeness_high"
    TIGHT_SCORE_MARGIN = "tight_score_margin"
    SAFE_RECOMMENDATION = "safe_recommendation"
    REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True)
class ProductDisplaySlot:
    slot_index: int
    candidate_id: str
    title: str
    seller_name: str | None
    price: float | None
    currency: str | None
    outbound_url: str | None
    affiliate_url: str | None
    availability_status: str | None
    reason_codes: tuple[RecommendationReason, ...]
    score: float


@dataclass(frozen=True)
class WiseRecommendedProduct:
    candidate_id: str
    title: str
    reason: RecommendationReason
    confidence: float
    risk_status: str
    explanation: str


@dataclass(frozen=True)
class PickWiseRecommendationSet:
    status: RecommendationStatus
    display_slots: tuple[ProductDisplaySlot, ...]
    wise_recommended_product: WiseRecommendedProduct | None
    recommendation_explanation: str
    tradeoff_summary: str
    confidence_status: str
    risk_status: str


def _score_candidate(candidate: OfferCandidate, query: str) -> tuple[float, tuple[RecommendationReason, ...]]:
    reasons: list[RecommendationReason] = []
    score = 0.0
    title = (candidate.title or "").lower()
    query_tokens = [token for token in query.lower().split(" ") if token]
    overlap = len([token for token in query_tokens if token in title])
    if overlap >= 2:
        score += 0.35
        reasons.append(RecommendationReason.STRONG_TITLE_MATCH)
    if (candidate.availability_status or "").lower() in {"available", "in_stock", "limited"}:
        score += 0.2
        reasons.append(RecommendationReason.AVAILABLE_NOW)
    if candidate.price is not None and candidate.price > 0:
        score += 0.15
        reasons.append(RecommendationReason.PRICE_PRESENT)
    if candidate.affiliate_url:
        score += 0.1
        reasons.append(RecommendationReason.AFFILIATE_LINK_PRESENT)
    if candidate.seller_name:
        score += 0.1
        reasons.append(RecommendationReason.TRUSTED_SELLER)

    completeness_checks = (
        bool(candidate.title),
        bool(candidate.brand),
        bool(candidate.model),
        bool(candidate.image_url),
        bool(candidate.outbound_url),
        candidate.price is not None,
    )
    completeness = sum(1 for item in completeness_checks if item) / float(len(completeness_checks))
    score += completeness * 0.1
    if completeness >= 0.8:
        reasons.append(RecommendationReason.DATA_COMPLETENESS_HIGH)
    return round(score, 6), tuple(reasons)


def build_pickwise_recommendation_set(
    *,
    query: str,
    eligible_candidates: tuple[OfferCandidate, ...],
) -> PickWiseRecommendationSet:
    if not eligible_candidates:
        return PickWiseRecommendationSet(
            status=RecommendationStatus.NO_VALID_CANDIDATES,
            display_slots=tuple(),
            wise_recommended_product=None,
            recommendation_explanation="No valid eligible candidates are available for this query.",
            tradeoff_summary="No tradeoff comparison is possible until eligible data is available.",
            confidence_status="low_confidence",
            risk_status="needs_data",
        )

    ranked: list[tuple[OfferCandidate, float, tuple[RecommendationReason, ...]]] = []
    seen = set()
    for candidate in eligible_candidates:
        dedupe_key = ((candidate.brand or "").lower(), (candidate.model or "").lower(), (candidate.title or "").lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        score, reasons = _score_candidate(candidate, query)
        ranked.append((candidate, score, reasons))

    ranked_sorted = sorted(ranked, key=lambda item: (-item[1], item[0].candidate_id))
    top = ranked_sorted[:4]
    slots = tuple(
        ProductDisplaySlot(
            slot_index=index + 1,
            candidate_id=candidate.candidate_id,
            title=candidate.title or "Untitled candidate",
            seller_name=candidate.seller_name,
            price=candidate.price,
            currency=candidate.currency,
            outbound_url=candidate.outbound_url,
            affiliate_url=candidate.affiliate_url,
            availability_status=candidate.availability_status,
            reason_codes=reasons,
            score=score,
        )
        for index, (candidate, score, reasons) in enumerate(top)
    )

    status = RecommendationStatus.READY if len(slots) >= 4 else RecommendationStatus.NOT_ENOUGH_VALID_CANDIDATES
    wise: WiseRecommendedProduct | None = None
    confidence_status = "medium_confidence"
    risk_status = "low_risk"
    explanation = "Top candidates are selected by deterministic relevance, availability, and data completeness scores."
    tradeoff = "Lower-priced options can rank below higher-confidence options with stronger availability and data completeness."

    if slots:
        top_slot = slots[0]
        second_score = slots[1].score if len(slots) > 1 else 0.0
        margin = top_slot.score - second_score
        safe_recommendation = top_slot.score >= 0.52 and margin >= 0.015 and top_slot.outbound_url is not None
        if safe_recommendation:
            wise = WiseRecommendedProduct(
                candidate_id=top_slot.candidate_id,
                title=top_slot.title,
                reason=RecommendationReason.SAFE_RECOMMENDATION,
                confidence=min(0.99, round(top_slot.score, 2)),
                risk_status="low_risk",
                explanation=(
                    "Recommended because it has the highest deterministic score with a clear margin "
                    "over alternatives and valid outbound data."
                ),
            )
            confidence_status = "high_confidence"
            risk_status = "low_risk"
        else:
            if margin < 0.03:
                explanation = "Top candidates are close in score, so a single safe recommendation is withheld."
                tradeoff = "Best options are similar; manual preference should drive final choice."
            confidence_status = "review_confidence"
            risk_status = "manual_review"
            if top_slot.reason_codes:
                reason_codes = tuple(top_slot.reason_codes) + (RecommendationReason.REVIEW_REQUIRED,)
            else:
                reason_codes = (RecommendationReason.REVIEW_REQUIRED,)
            slots = tuple(
                ProductDisplaySlot(
                    slot_index=slot.slot_index,
                    candidate_id=slot.candidate_id,
                    title=slot.title,
                    seller_name=slot.seller_name,
                    price=slot.price,
                    currency=slot.currency,
                    outbound_url=slot.outbound_url,
                    affiliate_url=slot.affiliate_url,
                    availability_status=slot.availability_status,
                    reason_codes=reason_codes if slot.slot_index == 1 else slot.reason_codes,
                    score=slot.score,
                )
                for slot in slots
            )
    return PickWiseRecommendationSet(
        status=status,
        display_slots=slots,
        wise_recommended_product=wise,
        recommendation_explanation=explanation,
        tradeoff_summary=tradeoff,
        confidence_status=confidence_status,
        risk_status=risk_status,
    )
