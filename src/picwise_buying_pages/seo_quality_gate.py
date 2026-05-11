from __future__ import annotations

from dataclasses import dataclass
import re

from picwise_offers import (
    OfferIntakeResult,
    PickWiseRecommendationSet,
    ProductSourceStatus,
    RecommendationStatus,
)

from .seo_contracts import PageQualityStatus, SEOIndexStatus

_ALLOWED_VERTICALS = frozenset(
    {
        "retail_physical_products",
        "software_saas_erp",
        "finance_insurance_business_finance",
    }
)
_BLOCKED_MARKERS = frozenset({"fake", "placeholder", "dummy", "lorem", "ipsum"})
_CANONICAL_PATTERN = re.compile(r"^/best/[a-z0-9]+(?:-[a-z0-9]+)*$")
_MIN_VALID_PRODUCT_COUNT = 4


@dataclass(frozen=True)
class SEOQualityGateInput:
    main_keyword: str
    detected_intent: str
    vertical: str
    source_status: ProductSourceStatus
    recommendation_set: PickWiseRecommendationSet | None
    product_slot_count: int
    valid_product_count: int
    canonical_path: str
    slug_is_valid: bool
    slug_is_unique: bool
    has_content: bool
    finance_insurance_contract_ref: str | None


@dataclass(frozen=True)
class SEOQualityGateResult:
    page_quality_status: PageQualityStatus
    index_status: SEOIndexStatus
    noindex_reason: str | None
    sitemap_eligible: bool
    reasons: tuple[str, ...]


def _contains_fake_commercial_data(recommendation_set: PickWiseRecommendationSet | None) -> bool:
    if recommendation_set is None:
        return False
    for slot in recommendation_set.display_slots:
        title = str(slot.title or "").strip().lower()
        if not title or any(marker in title for marker in _BLOCKED_MARKERS):
            return True
        if slot.price is None or float(slot.price) <= 0:
            return True
        availability = str(slot.availability_status or "").strip().lower()
        if not availability:
            return True
    return False


def _is_specific_intent(detected_intent: str) -> bool:
    return detected_intent in {"specific_product", "general_intent"}


def evaluate_seo_quality_gate(payload: SEOQualityGateInput) -> SEOQualityGateResult:
    reasons: list[str] = []
    if not str(payload.main_keyword).strip():
        reasons.append("invalid_or_empty_keyword")
    if not _is_specific_intent(str(payload.detected_intent)):
        reasons.append("ambiguous_or_unsupported_intent")
    if str(payload.vertical) not in _ALLOWED_VERTICALS:
        reasons.append("unsupported_vertical")
    if payload.finance_insurance_contract_ref or payload.vertical == "finance_insurance_business_finance":
        reasons.append("finance_regulated_manual_review_only")
    if payload.source_status != ProductSourceStatus.CONNECTED:
        reasons.append(f"source_not_connected:{payload.source_status.value}")
    if payload.recommendation_set is None:
        reasons.append("missing_recommendation_set")
    else:
        if payload.recommendation_set.status != RecommendationStatus.READY:
            reasons.append(f"recommendation_set_not_ready:{payload.recommendation_set.status.value}")
    if int(payload.product_slot_count) <= 0:
        reasons.append("empty_product_slots")
    if int(payload.valid_product_count) < _MIN_VALID_PRODUCT_COUNT:
        reasons.append("not_enough_valid_products")
    if _contains_fake_commercial_data(payload.recommendation_set):
        reasons.append("fake_or_placeholder_commercial_data")
    if not payload.slug_is_valid:
        reasons.append("invalid_slug")
    if not payload.slug_is_unique:
        reasons.append("duplicate_slug")
    if not _CANONICAL_PATTERN.match(str(payload.canonical_path)):
        reasons.append("invalid_canonical_path")
    if not payload.has_content:
        reasons.append("thin_or_empty_content")

    if not reasons:
        return SEOQualityGateResult(
            page_quality_status=PageQualityStatus.QUALITY_PASSED,
            index_status=SEOIndexStatus.INDEXABLE,
            noindex_reason=None,
            sitemap_eligible=True,
            reasons=tuple(),
        )

    if any(reason.startswith("invalid_slug") or reason == "invalid_canonical_path" for reason in reasons):
        quality = PageQualityStatus.BLOCKED
        index_status = SEOIndexStatus.BLOCKED
    elif "finance_regulated_manual_review_only" in reasons:
        quality = PageQualityStatus.MANUAL_REVIEW
        index_status = SEOIndexStatus.MANUAL_REVIEW
    elif "source_not_connected:not_connected" in reasons or "not_enough_valid_products" in reasons:
        quality = PageQualityStatus.NEEDS_DATA
        index_status = SEOIndexStatus.NOINDEX
    elif "ambiguous_or_unsupported_intent" in reasons or "recommendation_set_not_ready:not_enough_valid_candidates" in reasons:
        quality = PageQualityStatus.NOT_READY
        index_status = SEOIndexStatus.NOINDEX
    else:
        quality = PageQualityStatus.NOT_READY
        index_status = SEOIndexStatus.NOINDEX

    return SEOQualityGateResult(
        page_quality_status=quality,
        index_status=index_status,
        noindex_reason=reasons[0],
        sitemap_eligible=False,
        reasons=tuple(dict.fromkeys(reasons)),
    )


def has_connected_source(intake_result: OfferIntakeResult) -> bool:
    return intake_result.status == ProductSourceStatus.CONNECTED
