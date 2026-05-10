from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable


_SPACE_REGEX = re.compile(r"\s+")
_PUNCT_REGEX = re.compile(r"[^\w/\s]")
_SIZE_REGEX = re.compile(r"\b\d{3}/\d{2}(?:\s*r\d{2}|/\d{2})\b", flags=re.IGNORECASE)
_PRICE_NUMBER_REGEX = re.compile(r"\d+(?:[.,]\d+)?")

_AVAILABILITY_WEIGHTS = {
    "in_stock": 1.0,
    "available": 0.95,
    "limited": 0.7,
    "preorder": 0.55,
    "backorder": 0.45,
    "unknown": 0.4,
    "out_of_stock": 0.0,
}

_SELLER_RELIABILITY_WEIGHTS = {
    "trusted": 1.0,
    "acceptable": 0.8,
    "unknown": 0.4,
    "unreliable": 0.0,
    "blocked": 0.0,
}

_RELIABILITY_REJECTED = {"unreliable", "blocked"}
_RELIABILITY_ALLOWED = {"trusted", "acceptable"}


@dataclass(frozen=True)
class SpecificProductIdentity:
    brand: str
    model: str
    title: str
    size_specs: str
    normalized_key: str


@dataclass
class SpecificProductOffer:
    brand: str
    model: str
    title: str
    size_specs: str
    seller_or_store: str
    price: float
    currency: str
    availability: str
    seller_reliability: str
    store_rating: float
    review_count: int
    delivery_returns_available: bool
    affiliate_url_valid: bool
    data_completeness: float
    normalized_key: str
    ranking_score: float = 0.0


@dataclass(frozen=True)
class SpecificProductOfferSet:
    identity: SpecificProductIdentity | None
    offers: tuple[SpecificProductOffer, ...]
    status: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class OfferRankingResult:
    ranked_offers: tuple[SpecificProductOffer, ...]
    recommended_offer_index: int | None
    status: str
    reason_codes: tuple[str, ...]


def normalize_component(value: str) -> str:
    lowered = str(value or "").strip().lower()
    lowered = _PUNCT_REGEX.sub(" ", lowered)
    lowered = _SPACE_REGEX.sub(" ", lowered).strip()
    return lowered


def normalize_size_specs(value: str) -> str:
    normalized = normalize_component(value)
    normalized = normalized.replace(" / ", "/").replace("/ ", "/").replace(" /", "/")
    normalized = normalized.replace(" r", " r")
    normalized = _SPACE_REGEX.sub(" ", normalized).strip()
    return normalized


def build_normalized_key(brand: str, model: str, size_specs: str) -> str:
    return "|".join(
        (
            normalize_component(brand),
            normalize_component(model),
            normalize_size_specs(size_specs),
        )
    )


def extract_specific_product_identity(query: str) -> SpecificProductIdentity | None:
    normalized_query = normalize_component(query)
    if not normalized_query:
        return None
    size_match = _SIZE_REGEX.search(normalized_query)
    if not size_match:
        return None
    size_specs = normalize_size_specs(size_match.group(0))
    before_size = normalized_query[: size_match.start()].strip()
    if not before_size:
        return None
    parts = before_size.split(" ")
    if len(parts) < 2:
        return None
    brand = parts[0]
    model = " ".join(parts[1:]).strip()
    if not brand or not model or not size_specs:
        return None
    title = f"{brand} {model} {size_specs}".strip()
    return SpecificProductIdentity(
        brand=brand,
        model=model,
        title=title,
        size_specs=size_specs,
        normalized_key=build_normalized_key(brand, model, size_specs),
    )


def _parse_price(value: Any) -> float:
    if isinstance(value, (int, float)):
        return max(float(value), 0.0)
    text = str(value or "")
    match = _PRICE_NUMBER_REGEX.search(text)
    if not match:
        return 0.0
    return max(float(match.group(0).replace(",", ".")), 0.0)


def _parse_currency(value: Any, price_display: str) -> str:
    currency = str(value or "").strip().upper()
    if currency:
        return currency
    display = str(price_display or "").upper()
    if "EUR" in display:
        return "EUR"
    if "USD" in display:
        return "USD"
    return ""


def _resolve_size_specs(candidate: dict[str, Any]) -> str:
    direct = candidate.get("size_specs")
    if direct:
        return str(direct)
    specs = candidate.get("specifications")
    if isinstance(specs, (list, tuple)):
        for item in specs:
            item_text = str(item or "")
            if _SIZE_REGEX.search(normalize_component(item_text)):
                return item_text
    title = str(candidate.get("title", ""))
    title_match = _SIZE_REGEX.search(normalize_component(title))
    if title_match:
        return title_match.group(0)
    return ""


def build_offer_from_candidate(candidate: dict[str, Any]) -> SpecificProductOffer | None:
    brand = str(candidate.get("brand", "")).strip()
    model = str(candidate.get("model", "")).strip()
    title = str(candidate.get("title", "")).strip()
    size_specs = _resolve_size_specs(candidate).strip()
    if (not brand or not model or not size_specs) and title:
        identity = extract_specific_product_identity(title)
        if identity is not None:
            brand = brand or identity.brand
            model = model or identity.model
            size_specs = size_specs or identity.size_specs
    if not brand or not model or not size_specs:
        return None
    price_display = str(candidate.get("price_or_cost_display", ""))
    price = _parse_price(candidate.get("price", price_display))
    return SpecificProductOffer(
        brand=brand,
        model=model,
        title=title or f"{brand} {model} {size_specs}",
        size_specs=size_specs,
        seller_or_store=str(
            candidate.get("seller_or_store")
            or candidate.get("seller_name")
            or candidate.get("merchant_or_provider")
            or ""
        ),
        price=price,
        currency=_parse_currency(candidate.get("currency"), price_display),
        availability=str(candidate.get("availability") or "unknown"),
        seller_reliability=str(
            candidate.get("seller_reliability")
            or candidate.get("seller_reliability_status")
            or "unknown"
        ),
        store_rating=float(candidate.get("store_rating") or candidate.get("seller_rating") or 0.0),
        review_count=int(candidate.get("review_count") or candidate.get("seller_reviews_count") or 0),
        delivery_returns_available=bool(
            candidate.get("delivery_returns_available")
            or candidate.get("return_policy_available")
            or candidate.get("shipping_info_available")
        ),
        affiliate_url_valid=bool(str(candidate.get("redirect_target", "")).startswith(("http://", "https://"))),
        data_completeness=float(candidate.get("data_completeness") or 0.0),
        normalized_key=build_normalized_key(brand, model, size_specs),
        ranking_score=0.0,
    )


def _is_identity_confident(identity: SpecificProductIdentity | None) -> bool:
    if identity is None:
        return False
    return bool(
        normalize_component(identity.brand)
        and normalize_component(identity.model)
        and normalize_size_specs(identity.size_specs)
    )


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _availability_score(value: str) -> float:
    key = normalize_component(value).replace(" ", "_")
    return _AVAILABILITY_WEIGHTS.get(key, _AVAILABILITY_WEIGHTS["unknown"])


def _seller_reliability_score(value: str) -> float:
    key = normalize_component(value).replace(" ", "_")
    return _SELLER_RELIABILITY_WEIGHTS.get(key, _SELLER_RELIABILITY_WEIGHTS["unknown"])


def _compute_data_completeness(offer: SpecificProductOffer) -> float:
    if offer.data_completeness > 0:
        return _clamp01(offer.data_completeness)
    checks = [
        bool(normalize_component(offer.brand)),
        bool(normalize_component(offer.model)),
        bool(normalize_size_specs(offer.size_specs)),
        bool(normalize_component(offer.seller_or_store)),
        offer.price > 0,
        bool(normalize_component(offer.currency)),
        bool(normalize_component(offer.availability)),
        offer.store_rating > 0,
        offer.review_count >= 0,
        offer.delivery_returns_available,
        offer.affiliate_url_valid,
    ]
    return sum(1 for flag in checks if flag) / float(len(checks))


def rank_offers(offers: Iterable[SpecificProductOffer]) -> OfferRankingResult:
    prepared = list(offers)
    if not prepared:
        return OfferRankingResult(
            ranked_offers=(),
            recommended_offer_index=None,
            status="no_valid_offers",
            reason_codes=("no_valid_offers",),
        )
    prices = [offer.price for offer in prepared if offer.price > 0]
    min_price = min(prices) if prices else 0.0
    max_price = max(prices) if prices else 0.0
    priced_span = max_price - min_price

    for offer in prepared:
        if offer.price <= 0 or priced_span == 0:
            price_competitiveness = 0.5
        else:
            price_competitiveness = 1.0 - ((offer.price - min_price) / priced_span)
        score = (
            _availability_score(offer.availability) * 0.22
            + _seller_reliability_score(offer.seller_reliability) * 0.18
            + _clamp01(offer.store_rating / 5.0) * 0.12
            + _clamp01(offer.review_count / 500.0) * 0.08
            + (1.0 if offer.delivery_returns_available else 0.0) * 0.12
            + _compute_data_completeness(offer) * 0.12
            + (1.0 if offer.affiliate_url_valid else 0.0) * 0.10
            + _clamp01(price_competitiveness) * 0.06
        )
        offer.ranking_score = round(score, 6)

    ranked = tuple(
        sorted(
            prepared,
            key=lambda item: (
                -item.ranking_score,
                normalize_component(item.seller_or_store),
                item.price,
                normalize_component(item.title),
            ),
        )
    )
    return OfferRankingResult(
        ranked_offers=ranked,
        recommended_offer_index=0 if ranked else None,
        status="ready" if ranked else "no_valid_offers",
        reason_codes=("ranking_completed",) if ranked else ("no_valid_offers",),
    )


def resolve_specific_product_offer_set(
    identity: SpecificProductIdentity | None,
    offers: Iterable[SpecificProductOffer],
) -> tuple[SpecificProductOfferSet, OfferRankingResult]:
    if not _is_identity_confident(identity):
        offer_set = SpecificProductOfferSet(
            identity=identity,
            offers=(),
            status="manual_review_required",
            reason_codes=("insufficient_identity",),
        )
        return (
            offer_set,
            OfferRankingResult(
                ranked_offers=(),
                recommended_offer_index=None,
                status="manual_review_required",
                reason_codes=("insufficient_identity",),
            ),
        )

    candidates = []
    unknown_same_key = []
    rejected_same_key = []
    for offer in offers:
        offer.normalized_key = build_normalized_key(offer.brand, offer.model, offer.size_specs)
        if offer.normalized_key != identity.normalized_key:
            continue
        reliability = normalize_component(offer.seller_reliability).replace(" ", "_")
        if reliability in _RELIABILITY_REJECTED:
            rejected_same_key.append(offer)
            continue
        if reliability not in _RELIABILITY_ALLOWED:
            unknown_same_key.append(offer)
            continue
        candidates.append(offer)

    if not candidates:
        if unknown_same_key:
            status = "manual_review_required"
            reasons = ("unknown_seller_requires_review",)
        elif rejected_same_key:
            status = "no_valid_offers"
            reasons = ("seller_blocked_or_unreliable",)
        else:
            status = "no_valid_offers"
            reasons = ("no_valid_offers",)
        offer_set = SpecificProductOfferSet(identity=identity, offers=(), status=status, reason_codes=reasons)
        return (
            offer_set,
            OfferRankingResult(
                ranked_offers=(),
                recommended_offer_index=None,
                status=status,
                reason_codes=reasons,
            ),
        )

    ranking = rank_offers(candidates)
    capped = ranking.ranked_offers[:4]
    reasons = list(ranking.reason_codes)
    if len(ranking.ranked_offers) > 4:
        reasons.append("capped_to_4_offers")
    if unknown_same_key:
        reasons.append("unknown_sellers_excluded")
    offer_set = SpecificProductOfferSet(
        identity=identity,
        offers=tuple(capped),
        status="ready",
        reason_codes=tuple(reasons),
    )
    return (
        offer_set,
        OfferRankingResult(
            ranked_offers=tuple(capped),
            recommended_offer_index=0 if capped else None,
            status="ready",
            reason_codes=tuple(reasons),
        ),
    )


def resolve_specific_product_offers_from_candidates(
    query: str,
    candidates: Iterable[dict[str, Any]],
) -> tuple[SpecificProductOfferSet, OfferRankingResult]:
    identity = extract_specific_product_identity(query)
    offers = []
    for candidate in candidates:
        offer = build_offer_from_candidate(candidate)
        if offer is not None:
            offers.append(offer)
    return resolve_specific_product_offer_set(identity, offers)
