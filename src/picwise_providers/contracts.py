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
class ProviderParseResult:
    status: str
    products: tuple[ProviderProduct, ...] = field(default_factory=tuple)
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    parse_errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProviderEligibilityResult:
    product: ProviderProduct
    status: str
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    derived_provider_product_id: str = ""


@dataclass(frozen=True)
class ProviderGraphProjectionResult:
    product_offers: tuple[Any, ...] = field(default_factory=tuple)
    brands: tuple[Any, ...] = field(default_factory=tuple)
    product_families: tuple[Any, ...] = field(default_factory=tuple)
    query_aliases: tuple[Any, ...] = field(default_factory=tuple)
    edges: tuple[Any, ...] = field(default_factory=tuple)
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
