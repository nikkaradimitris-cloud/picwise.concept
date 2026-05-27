from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .awin_adapter import awin_feed_config_from_env, load_awin_provider_feed
from .contracts import (
    PROVIDER_FEED_STATUSES,
    ProviderEligibilityResult,
    ProviderFeedConfig,
    ProviderFeedStatus,
    ProviderGraphProjectionResult,
    ProviderParseResult,
    ProviderProduct,
    SearchProviderFeedMetadata,
)
from .eligibility import evaluate_provider_product_eligibility
from .graph_projection import project_provider_products_to_graph
from .search_selection import (
    ProviderFeedRecommendationDecision,
    ProviderProductSelectionResult,
    decide_recommended_provider_product,
    is_strong_feed_opportunity_selection,
    select_provider_products_for_query,
)


@dataclass(frozen=True)
class ProviderFeedPipelineResult:
    feed_status: ProviderFeedStatus
    parse_result: ProviderParseResult | None = None
    eligibility_results: tuple[ProviderEligibilityResult, ...] = field(default_factory=tuple)
    graph_projection: ProviderGraphProjectionResult | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "feed_status": self.feed_status.to_dict(),
            "parse_result_status": self.parse_result.status if self.parse_result else None,
            "eligibility_count": len(self.eligibility_results),
            "graph_offer_count": len(self.graph_projection.product_offers) if self.graph_projection else 0,
        }
        return payload


def _aggregate_feed_status(
    *,
    provider_key: str,
    parse_result: ProviderParseResult,
    eligibility_results: tuple[ProviderEligibilityResult, ...],
) -> ProviderFeedStatus:
    eligible_count = sum(1 for row in eligibility_results if row.status == "eligible")
    review_count = sum(1 for row in eligibility_results if row.status == "needs_review")
    blocked_count = sum(1 for row in eligibility_results if row.status == "blocked")
    product_count = len(eligibility_results)

    if parse_result.status == "provider_feed_not_configured":
        return ProviderFeedStatus(
            status="provider_feed_not_configured",
            provider_key=provider_key,
            reason_codes=parse_result.reason_codes,
        )
    if parse_result.status == "provider_feed_parse_failed":
        return ProviderFeedStatus(
            status="provider_feed_parse_failed",
            provider_key=provider_key,
            reason_codes=parse_result.reason_codes,
        )
    if parse_result.status == "provider_feed_empty" or product_count == 0:
        return ProviderFeedStatus(
            status="provider_feed_empty",
            provider_key=provider_key,
            reason_codes=parse_result.reason_codes + ("normalized_product_count_zero",),
            product_count=product_count,
        )
    if eligible_count == 0 and review_count == 0:
        return ProviderFeedStatus(
            status="provider_feed_no_eligible_products",
            provider_key=provider_key,
            reason_codes=("all_products_blocked",),
            product_count=product_count,
            blocked_count=blocked_count,
        )
    if eligible_count > 0:
        final_status = "provider_feed_ready"
    else:
        final_status = "provider_feed_loaded"

    reason_codes = tuple(parse_result.reason_codes)
    if review_count:
        reason_codes = reason_codes + ("reviewable_products_present",)
    if blocked_count:
        reason_codes = reason_codes + ("blocked_products_present",)

    return ProviderFeedStatus(
        status=final_status,
        provider_key=provider_key,
        reason_codes=reason_codes,
        product_count=product_count,
        eligible_count=eligible_count,
        review_count=review_count,
        blocked_count=blocked_count,
    )


def resolve_provider_feed_pipeline(
    config: ProviderFeedConfig,
    *,
    mega_category_id: str = "",
) -> ProviderFeedPipelineResult:
    provider_key = str(config.provider_key or "").strip() or "unknown_provider"
    parse_result = load_awin_provider_feed(config)

    if parse_result.status in {
        "provider_feed_not_configured",
        "provider_feed_parse_failed",
        "provider_feed_empty",
    }:
        feed_status = _aggregate_feed_status(
            provider_key=provider_key,
            parse_result=parse_result,
            eligibility_results=tuple(),
        )
        return ProviderFeedPipelineResult(
            feed_status=feed_status,
            parse_result=parse_result,
        )

    eligibility_results = tuple(
        evaluate_provider_product_eligibility(product) for product in parse_result.products
    )
    graph_projection = project_provider_products_to_graph(
        eligibility_results,
        mega_category_id=mega_category_id,
    )
    feed_status = _aggregate_feed_status(
        provider_key=provider_key,
        parse_result=parse_result,
        eligibility_results=eligibility_results,
    )
    return ProviderFeedPipelineResult(
        feed_status=feed_status,
        parse_result=parse_result,
        eligibility_results=eligibility_results,
        graph_projection=graph_projection,
    )


def is_safe_no_card_feed_status(status: str) -> bool:
    return status in PROVIDER_FEED_STATUSES and status != "provider_feed_ready"


def load_eligible_provider_feed_products(
    feed_config: ProviderFeedConfig | None = None,
) -> tuple[ProviderProduct, ...]:
    config = feed_config or awin_feed_config_from_env()
    pipeline = resolve_provider_feed_pipeline(config)
    if pipeline.feed_status.status != "provider_feed_ready":
        return tuple()
    return tuple(
        row.product for row in pipeline.eligibility_results if row.status == "eligible"
    )


def resolve_search_provider_feed_product_selection(
    *,
    query: str,
    feed_config: ProviderFeedConfig | None = None,
    max_products: int = 4,
) -> ProviderProductSelectionResult:
    products = load_eligible_provider_feed_products(feed_config=feed_config)
    return select_provider_products_for_query(
        query,
        products,
        max_products=max_products,
    )


def resolve_search_provider_feed_recommendation_decision(
    *,
    query: str,
    selection: ProviderProductSelectionResult,
) -> ProviderFeedRecommendationDecision:
    if selection.status == "insufficient_relevant_products":
        return ProviderFeedRecommendationDecision(
            decision_status="insufficient_selected_products",
            recommendation_reason_codes=("insufficient_selected_products",),
        )
    if selection.status != "selected" or len(selection.selected_products) != 4:
        return ProviderFeedRecommendationDecision(
            decision_status="no_selection",
            recommendation_reason_codes=("no_feed_selection",),
        )
    return decide_recommended_provider_product(query, selection.selected_products)


def resolve_search_provider_feed_selection_with_recommendation(
    *,
    query: str,
    feed_config: ProviderFeedConfig | None = None,
    max_products: int = 4,
) -> tuple[ProviderProductSelectionResult, ProviderFeedRecommendationDecision]:
    selection = resolve_search_provider_feed_product_selection(
        query=query,
        feed_config=feed_config,
        max_products=max_products,
    )
    decision = resolve_search_provider_feed_recommendation_decision(
        query=query,
        selection=selection,
    )
    return selection, decision


def resolve_search_provider_feed_metadata(
    *,
    mega_category_id: str | None,
    manual_provider_connected: bool,
    feed_config: ProviderFeedConfig | None = None,
    allow_without_mega_category: bool = False,
) -> SearchProviderFeedMetadata | None:
    if manual_provider_connected:
        return None

    config = feed_config or awin_feed_config_from_env()
    if not _normalized_mega_category_id(mega_category_id) and not allow_without_mega_category:
        return None

    pipeline = resolve_provider_feed_pipeline(
        config,
        mega_category_id=str(mega_category_id or ""),
    )
    feed_status = pipeline.feed_status
    return SearchProviderFeedMetadata(
        provider_feed_status=feed_status.status,
        provider_feed_reason_codes=feed_status.reason_codes,
        provider_feed_eligible_count=feed_status.eligible_count,
    )


def _normalized_mega_category_id(value: str | None) -> str:
    return " ".join(str(value or "").split()).strip()
