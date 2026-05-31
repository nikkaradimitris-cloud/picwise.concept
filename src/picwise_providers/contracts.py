from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

PROVIDER_FEED_STATUSES = (
    "provider_feed_not_configured",
    "provider_feed_loaded",
    "provider_feed_parse_failed",
    "provider_feed_empty",
    "provider_feed_no_eligible_products",
    "provider_feed_ready",
)

PROVIDER_ELIGIBILITY_STATUSES = (
    "eligible",
    "needs_review",
    "blocked",
)

AVAILABILITY_STATES = (
    "trusted",
    "weak",
    "unknown",
    "out_of_stock",
    "discontinued",
)

PURCHASABILITY_STATES = (
    "purchasable",
    "purchasability_unknown",
    "missing_buy_button",
    "out_of_stock",
    "discontinued",
)

RECOMMENDATION_CONFIDENCE_LEVELS = (
    "strong",
    "limited",
    "weak",
    "unknown",
)


@dataclass(frozen=True)
class ProviderProduct:
    provider_key: str
    provider_product_id: str
    title: str
    brand: str
    category_text: str
    product_url: str
    image_url: str
    price_text: str
    availability_text: str
    currency: str
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderFeedConfig:
    provider_key: str
    feed_file: str | None = None
    feed_url: str | None = None

    def is_configured(self) -> bool:
        return bool(str(self.feed_file or "").strip() or str(self.feed_url or "").strip())


@dataclass(frozen=True)
class ProviderFeedStatus:
    status: str
    provider_key: str
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    product_count: int = 0
    eligible_count: int = 0
    review_count: int = 0
    blocked_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "provider_key": self.provider_key,
            "reason_codes": list(self.reason_codes),
            "product_count": self.product_count,
            "eligible_count": self.eligible_count,
            "review_count": self.review_count,
            "blocked_count": self.blocked_count,
        }


@dataclass(frozen=True)
class SearchProviderFeedMetadata:
    provider_feed_status: str
    provider_feed_reason_codes: tuple[str, ...] = field(default_factory=tuple)
    provider_feed_eligible_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_feed_status": self.provider_feed_status,
            "provider_feed_reason_codes": list(self.provider_feed_reason_codes),
            "provider_feed_eligible_count": self.provider_feed_eligible_count,
        }


@dataclass(frozen=True)
class ProviderParseResult:
    status: str
    products: tuple[ProviderProduct, ...] = field(default_factory=tuple)
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    parse_errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PurchasabilityVerification:
    purchasability_state: str = "purchasability_unknown"
    buy_button_seen: bool | None = None
    out_of_stock_seen: bool | None = None
    final_url: str = ""
    http_status: int | None = None
    last_checked_at: str = ""
    verification_source: str = ""
    verification_confidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "purchasability_state": self.purchasability_state,
            "buy_button_seen": self.buy_button_seen,
            "out_of_stock_seen": self.out_of_stock_seen,
            "final_url": self.final_url,
            "http_status": self.http_status,
            "last_checked_at": self.last_checked_at,
            "verification_source": self.verification_source,
            "verification_confidence": self.verification_confidence,
        }


@dataclass(frozen=True)
class OfferHealth:
    availability_state: str
    purchasability: PurchasabilityVerification
    availability_source_field: str = ""
    feed_availability_signal: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "availability_state": self.availability_state,
            "purchasability_state": self.purchasability.purchasability_state,
            "buy_button_seen": self.purchasability.buy_button_seen,
            "out_of_stock_seen": self.purchasability.out_of_stock_seen,
            "final_url": self.purchasability.final_url,
            "http_status": self.purchasability.http_status,
            "last_checked_at": self.purchasability.last_checked_at,
            "verification_source": self.purchasability.verification_source,
            "verification_confidence": self.purchasability.verification_confidence,
            "availability_source_field": self.availability_source_field,
            "feed_availability_signal": self.feed_availability_signal,
        }


@dataclass(frozen=True)
class ProductEligibility:
    card_eligible: bool
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    offer_health: OfferHealth | None = None
    recommendation_confidence_ceiling: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "card_eligible": self.card_eligible,
            "reason_codes": list(self.reason_codes),
            "recommendation_confidence_ceiling": self.recommendation_confidence_ceiling,
        }
        if self.offer_health is not None:
            payload["offer_health"] = self.offer_health.to_dict()
        return payload


@dataclass(frozen=True)
class FeedAvailabilityContext:
    has_meaningful_variation: bool
    distinct_normalized_values: tuple[str, ...] = field(default_factory=tuple)
    product_count_with_signal: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_meaningful_variation": self.has_meaningful_variation,
            "distinct_normalized_values": list(self.distinct_normalized_values),
            "product_count_with_signal": self.product_count_with_signal,
        }


@dataclass(frozen=True)
class ProviderEligibilityResult:
    product: ProviderProduct
    status: str
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    derived_provider_product_id: str = ""
    product_eligibility: ProductEligibility | None = None


@dataclass(frozen=True)
class ProviderGraphProjectionResult:
    product_offers: tuple[Any, ...] = field(default_factory=tuple)
    brands: tuple[Any, ...] = field(default_factory=tuple)
    product_families: tuple[Any, ...] = field(default_factory=tuple)
    query_aliases: tuple[Any, ...] = field(default_factory=tuple)
    edges: tuple[Any, ...] = field(default_factory=tuple)
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
