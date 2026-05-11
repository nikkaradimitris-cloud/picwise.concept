from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from picwise_offers import PickWiseRecommendationSet, ProductDisplaySlot, WiseRecommendedProduct


class SEOBuyingPageContractError(ValueError):
    """Raised when Stage 37 SEO buying page data is invalid."""


class PageQualityStatus(str, Enum):
    QUALITY_PASSED = "quality_passed"
    NEEDS_DATA = "needs_data"
    NOT_READY = "not_ready"
    MANUAL_REVIEW = "manual_review"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class SEOIndexStatus(str, Enum):
    INDEXABLE = "indexable"
    NOINDEX = "noindex"
    BLOCKED = "blocked"
    MANUAL_REVIEW = "manual_review"


@dataclass(frozen=True)
class SEOBuyingPage:
    page_id: str
    slug: str
    canonical_path: str
    main_keyword: str
    query_aliases: tuple[str, ...]
    detected_intent: str
    vertical: str
    retail_engine: str | None
    category_bucket: str | None
    google_taxonomy_path: str | None
    saas_erp_contract_ref: str | None
    finance_insurance_contract_ref: str | None
    recommendation_set: PickWiseRecommendationSet | None
    wise_recommended_product: WiseRecommendedProduct | None
    product_slot_count: int
    valid_product_count: int
    page_quality_status: PageQualityStatus
    index_status: SEOIndexStatus
    noindex_reason: str | None
    sitemap_eligible: bool
    last_updated: datetime
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        if not str(self.page_id).strip():
            raise SEOBuyingPageContractError("page_id is required.")
        if not str(self.slug).strip():
            raise SEOBuyingPageContractError("slug is required.")
        if not str(self.main_keyword).strip():
            raise SEOBuyingPageContractError("main_keyword is required.")
        if not str(self.detected_intent).strip():
            raise SEOBuyingPageContractError("detected_intent is required.")
        if not str(self.vertical).strip():
            raise SEOBuyingPageContractError("vertical is required.")
        if not str(self.canonical_path).startswith("/best/"):
            raise SEOBuyingPageContractError("canonical_path must stay under /best/.")
        if self.canonical_path != f"/best/{self.slug}":
            raise SEOBuyingPageContractError("canonical_path must match slug.")
        if int(self.product_slot_count) < 0:
            raise SEOBuyingPageContractError("product_slot_count must be >= 0.")
        if int(self.valid_product_count) < 0:
            raise SEOBuyingPageContractError("valid_product_count must be >= 0.")
        if not isinstance(self.metadata, dict):
            raise SEOBuyingPageContractError("metadata must be a dict.")

        aliases = tuple(str(alias).strip() for alias in self.query_aliases if str(alias).strip())
        object.__setattr__(self, "query_aliases", aliases)

        try:
            quality = (
                self.page_quality_status
                if isinstance(self.page_quality_status, PageQualityStatus)
                else PageQualityStatus(str(self.page_quality_status))
            )
        except ValueError as exc:
            raise SEOBuyingPageContractError("page_quality_status is invalid.") from exc
        object.__setattr__(self, "page_quality_status", quality)

        try:
            index_status = (
                self.index_status
                if isinstance(self.index_status, SEOIndexStatus)
                else SEOIndexStatus(str(self.index_status))
            )
        except ValueError as exc:
            raise SEOBuyingPageContractError("index_status is invalid.") from exc
        object.__setattr__(self, "index_status", index_status)

        if self.index_status == SEOIndexStatus.INDEXABLE:
            if self.page_quality_status != PageQualityStatus.QUALITY_PASSED:
                raise SEOBuyingPageContractError("indexable page must be quality_passed.")
            if not self.sitemap_eligible:
                raise SEOBuyingPageContractError("indexable page must be sitemap_eligible.")
            if self.noindex_reason:
                raise SEOBuyingPageContractError("indexable page cannot carry noindex_reason.")
        elif not str(self.noindex_reason or "").strip():
            raise SEOBuyingPageContractError("non-indexable page must define noindex_reason.")

    @property
    def robots_meta(self) -> str:
        return "index,follow" if self.index_status == SEOIndexStatus.INDEXABLE else "noindex,follow"

    @property
    def display_slots(self) -> tuple[ProductDisplaySlot, ...]:
        if self.recommendation_set is None:
            return tuple()
        return tuple(self.recommendation_set.display_slots)
