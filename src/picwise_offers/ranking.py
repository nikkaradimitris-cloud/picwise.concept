from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re

from .contracts import ExternalOffer, ExternalOfferStatus

_TOKEN_REGEX = re.compile(r"[^\w]+", flags=re.UNICODE)
_UNKNOWN_TEXT_VALUES = {"", "unknown", "n/a", "na", "none"}


class OfferRankingReason(str, Enum):
    STRONG_INTENT_MATCH = "strong_intent_match"
    COMPETITIVE_PRICE = "competitive_price"
    TRUSTED_STORE_SIGNALS = "trusted_store_signals"
    STRONG_RETURNS_POLICY = "strong_returns_policy"
    FAST_DELIVERY_SIGNAL = "fast_delivery_signal"
    COMPLETE_EXTERNAL_DATA = "complete_external_data"
    AFFILIATE_URL_VALID = "affiliate_url_valid"
    LOWER_DATA_COMPLETENESS = "lower_data_completeness"
    LOW_AVAILABILITY_SIGNAL = "low_availability_signal"


class OfferRankingStatus(str, Enum):
    RANKED = "ranked"
    INSUFFICIENT_VALID_OFFERS = "insufficient_valid_offers"
    NO_VALID_EXTERNAL_OFFERS = "no_valid_external_offers"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


@dataclass(frozen=True)
class OfferRankingInput:
    intent_label: str
    offers: tuple[ExternalOffer, ...] = field(default_factory=tuple)
    max_options: int = 4


@dataclass(frozen=True)
class RankedOffer:
    offer: ExternalOffer
    weighted_score: float
    reasons: tuple[OfferRankingReason, ...] = field(default_factory=tuple)
    data_completeness: float = 0.0


@dataclass(frozen=True)
class OfferRankingResult:
    status: OfferRankingStatus
    top_offers: tuple[RankedOffer, ...]
    recommended_offer_id: str | None
    reasons: tuple[str, ...] = field(default_factory=tuple)


def _tokenize(value: str) -> set[str]:
    return {token for token in _TOKEN_REGEX.split((value or "").strip().lower()) if token}


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    lowered = (text or "").strip().lower()
    return any(word in lowered for word in words)


def _availability_score(value: str) -> float:
    lowered = (value or "").strip().lower()
    if lowered in {"in_stock", "available", "ready"}:
        return 1.0
    if lowered in {"limited", "few_left", "low_stock"}:
        return 0.5
    return 0.0


def _text_quality_score(value: str) -> float:
    lowered = (value or "").strip().lower()
    if lowered in _UNKNOWN_TEXT_VALUES:
        return 0.0
    return 1.0


def _affiliate_score(offer: ExternalOffer) -> float:
    return 1.0 if offer.affiliate_url.startswith("http://") or offer.affiliate_url.startswith("https://") else 0.0


def _data_completeness(offer: ExternalOffer) -> float:
    fields = (
        offer.external_product_title,
        offer.external_store,
        offer.external_url,
        offer.delivery,
        offer.returns,
        offer.affiliate_url,
        offer.data_source,
    )
    quality = sum(_text_quality_score(value) for value in fields)
    return round(quality / float(len(fields)), 4)


def _build_ranked_offer(offer: ExternalOffer, *, intent_label: str, min_price: float, max_price: float) -> RankedOffer:
    intent_tokens = _tokenize(intent_label)
    title_tokens = _tokenize(offer.external_product_title)
    overlap_count = len(intent_tokens & title_tokens)
    intent_score = overlap_count / max(1.0, float(len(intent_tokens) or 1))

    if max_price <= min_price:
        price_score = 1.0
    else:
        price_score = 1.0 - ((offer.price - min_price) / (max_price - min_price))
    price_score = max(0.0, min(1.0, price_score))

    availability_score = _availability_score(offer.availability)
    store_trust_score = max(0.0, min(1.0, offer.review_score / 5.0))
    returns_score = 1.0 if _contains_any(offer.returns, ("free", "easy", "30 day", "30-day")) else 0.4
    delivery_score = 1.0 if _contains_any(offer.delivery, ("same day", "next day", "24h", "1-2 day")) else 0.5
    reviews_score = max(0.0, min(1.0, offer.review_score / 5.0))
    completeness_score = _data_completeness(offer)
    affiliate_validity_score = _affiliate_score(offer)

    weighted_score = (
        intent_score * 0.24
        + price_score * 0.16
        + availability_score * 0.13
        + store_trust_score * 0.11
        + returns_score * 0.10
        + delivery_score * 0.09
        + reviews_score * 0.08
        + completeness_score * 0.05
        + affiliate_validity_score * 0.04
    )
    if completeness_score < 0.85:
        # Incomplete external data is still rankable but must be noticeably de-prioritized.
        weighted_score *= 0.85

    reasons: list[OfferRankingReason] = []
    if intent_score >= 0.5:
        reasons.append(OfferRankingReason.STRONG_INTENT_MATCH)
    if price_score >= 0.75:
        reasons.append(OfferRankingReason.COMPETITIVE_PRICE)
    if store_trust_score >= 0.75:
        reasons.append(OfferRankingReason.TRUSTED_STORE_SIGNALS)
    if returns_score >= 1.0:
        reasons.append(OfferRankingReason.STRONG_RETURNS_POLICY)
    if delivery_score >= 1.0:
        reasons.append(OfferRankingReason.FAST_DELIVERY_SIGNAL)
    if completeness_score >= 0.95:
        reasons.append(OfferRankingReason.COMPLETE_EXTERNAL_DATA)
    else:
        reasons.append(OfferRankingReason.LOWER_DATA_COMPLETENESS)
    if affiliate_validity_score >= 1.0:
        reasons.append(OfferRankingReason.AFFILIATE_URL_VALID)
    if availability_score < 0.5:
        reasons.append(OfferRankingReason.LOW_AVAILABILITY_SIGNAL)

    return RankedOffer(
        offer=offer,
        weighted_score=round(weighted_score, 6),
        reasons=tuple(reasons),
        data_completeness=completeness_score,
    )


def rank_external_offers(ranking_input: OfferRankingInput) -> OfferRankingResult:
    valid_offers = [
        offer
        for offer in ranking_input.offers
        if offer.status == ExternalOfferStatus.VALID_EXTERNAL_OFFER and offer.is_external_temporary_data
    ]
    if not valid_offers:
        return OfferRankingResult(
            status=OfferRankingStatus.NO_VALID_EXTERNAL_OFFERS,
            top_offers=tuple(),
            recommended_offer_id=None,
            reasons=("no_valid_external_offers",),
        )

    sorted_by_price = sorted(valid_offers, key=lambda offer: (offer.price, offer.offer_id))
    min_price = sorted_by_price[0].price
    max_price = sorted_by_price[-1].price

    ranked = [
        _build_ranked_offer(
            offer,
            intent_label=ranking_input.intent_label,
            min_price=min_price,
            max_price=max_price,
        )
        for offer in valid_offers
    ]
    ranked_sorted = sorted(
        ranked,
        key=lambda candidate: (-candidate.weighted_score, -candidate.data_completeness, candidate.offer.offer_id),
    )
    top_offers = tuple(ranked_sorted[: max(1, ranking_input.max_options)])

    if len(top_offers) < 2:
        return OfferRankingResult(
            status=OfferRankingStatus.INSUFFICIENT_VALID_OFFERS,
            top_offers=top_offers,
            recommended_offer_id=top_offers[0].offer.offer_id if top_offers and top_offers[0].weighted_score >= 0.75 else None,
            reasons=("insufficient_valid_offers",),
        )

    top_score = top_offers[0].weighted_score
    second_score = top_offers[1].weighted_score
    if abs(top_score - second_score) <= 0.02:
        return OfferRankingResult(
            status=OfferRankingStatus.MANUAL_REVIEW_REQUIRED,
            top_offers=top_offers,
            recommended_offer_id=None,
            reasons=("ambiguous_top_offer_scores",),
        )

    recommended_offer_id = top_offers[0].offer.offer_id if top_score >= 0.60 and top_offers[0].data_completeness >= 0.85 else None
    status = OfferRankingStatus.RANKED if recommended_offer_id is not None else OfferRankingStatus.MANUAL_REVIEW_REQUIRED
    reasons = ("ranked_with_recommended_offer",) if recommended_offer_id is not None else ("recommended_offer_not_safe",)
    return OfferRankingResult(
        status=status,
        top_offers=top_offers,
        recommended_offer_id=recommended_offer_id,
        reasons=reasons,
    )
