from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha1
from typing import Any

from picwise_offers import EligibilityGateResult, OfferIntakeResult, PickWiseRecommendationSet
from picwise_search import SearchDecision

from .seo_contracts import PageQualityStatus, SEOBuyingPage
from .seo_quality_gate import SEOQualityGateInput, evaluate_seo_quality_gate
from .seo_slug_builder import build_buying_page_slug


@dataclass(frozen=True)
class SEOPageBuildRequest:
    target_query: str
    query_aliases: tuple[str, ...]
    search_decision: SearchDecision
    intake_result: OfferIntakeResult
    eligibility_result: EligibilityGateResult
    recommendation_set: PickWiseRecommendationSet
    existing_slugs: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None


def _derive_vertical(request: SEOPageBuildRequest) -> str:
    if request.eligibility_result.eligible_candidates:
        value = request.eligibility_result.eligible_candidates[0].vertical
        if value:
            return str(value)
    if request.intake_result.candidates:
        value = request.intake_result.candidates[0].vertical
        if value:
            return str(value)
    return "retail_physical_products"


def _derive_optional_dimensions(request: SEOPageBuildRequest) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    if request.intake_result.candidates:
        candidate = request.intake_result.candidates[0]
        return (
            candidate.engine,
            candidate.category_bucket,
            candidate.google_taxonomy_path,
            candidate.saas_erp_contract_ref,
            candidate.finance_insurance_contract_ref,
        )
    return (None, None, None, None, None)


def _build_metadata(request: SEOPageBuildRequest, canonical_path: str) -> dict[str, Any]:
    base = dict(request.metadata or {})
    query = str(request.target_query).strip()
    base.setdefault("title", f"Best options for {query} | PickWise")
    base.setdefault("description", f"Compare eligible options for {query} using deterministic PickWise recommendation data.")
    base.setdefault("canonical_path", canonical_path)
    base.setdefault("search_route_type", request.search_decision.route_type)
    base.setdefault("source_status", request.intake_result.status.value)
    base.setdefault("guardrails", {"no_fake_data": True, "no_mass_generation": True})
    return base


def _build_page_id(canonical_path: str) -> str:
    digest = sha1(canonical_path.encode("utf-8")).hexdigest()[:12]
    return f"seo-{digest}"


def build_seo_buying_page(request: SEOPageBuildRequest) -> SEOBuyingPage:
    query = str(request.target_query or "").strip()
    slug_result = build_buying_page_slug(query)
    slug = slug_result.slug
    canonical_path = slug_result.canonical_path if slug_result.valid else "/best/invalid"
    vertical = _derive_vertical(request)
    retail_engine, category_bucket, google_taxonomy_path, saas_erp_contract_ref, finance_insurance_contract_ref = (
        _derive_optional_dimensions(request)
    )

    existing_slugs = {str(item).strip() for item in request.existing_slugs if str(item).strip()}
    slug_is_unique = bool(slug and slug not in existing_slugs)
    valid_product_count = len(request.eligibility_result.eligible_candidates)
    product_slot_count = len(request.recommendation_set.display_slots)
    metadata = _build_metadata(request, canonical_path)
    has_content = bool(str(metadata.get("title", "")).strip() and str(metadata.get("description", "")).strip())

    quality_result = evaluate_seo_quality_gate(
        SEOQualityGateInput(
            main_keyword=query,
            detected_intent=request.search_decision.route_type,
            vertical=vertical,
            source_status=request.intake_result.status,
            recommendation_set=request.recommendation_set,
            product_slot_count=product_slot_count,
            valid_product_count=valid_product_count,
            canonical_path=canonical_path,
            slug_is_valid=slug_result.valid,
            slug_is_unique=slug_is_unique,
            has_content=has_content,
            finance_insurance_contract_ref=finance_insurance_contract_ref,
        )
    )

    wise = request.recommendation_set.wise_recommended_product
    if quality_result.page_quality_status != PageQualityStatus.QUALITY_PASSED:
        metadata["recommendation_mode"] = "safe_noindex"
    else:
        metadata["recommendation_mode"] = "public_indexable"

    return SEOBuyingPage(
        page_id=_build_page_id(canonical_path),
        slug=slug if slug_result.valid else "invalid",
        canonical_path=canonical_path,
        main_keyword=query,
        query_aliases=tuple(dict.fromkeys(str(alias).strip() for alias in request.query_aliases if str(alias).strip())),
        detected_intent=request.search_decision.route_type,
        vertical=vertical,
        retail_engine=retail_engine,
        category_bucket=category_bucket,
        google_taxonomy_path=google_taxonomy_path,
        saas_erp_contract_ref=saas_erp_contract_ref,
        finance_insurance_contract_ref=finance_insurance_contract_ref,
        recommendation_set=request.recommendation_set,
        wise_recommended_product=wise,
        product_slot_count=product_slot_count,
        valid_product_count=valid_product_count,
        page_quality_status=quality_result.page_quality_status,
        index_status=quality_result.index_status,
        noindex_reason=quality_result.noindex_reason,
        sitemap_eligible=quality_result.sitemap_eligible,
        last_updated=datetime.now(tz=timezone.utc),
        metadata=metadata,
    )
