from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any
from picwise_nlu.concept_understanding import ConceptReading

from .awin_adapter import (
    awin_feed_config_from_env,
    feed_file_cache_key,
    load_awin_provider_feed,
)
from .contracts import (
    PROVIDER_FEED_STATUSES,
    FeedAvailabilityContext,
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
from .offer_health import build_feed_availability_context, evaluate_product_eligibility
from .purchasability_cache import enrich_provider_products_with_cache
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
    # Availability context over every row of the feed. Selection, the exported card
    # fields, the recommendation and the outbound redirect all judge availability
    # against this one population, so they cannot disagree about the same offer.
    availability_context: FeedAvailabilityContext | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "feed_status": self.feed_status.to_dict(),
            "parse_result_status": self.parse_result.status if self.parse_result else None,
            "eligibility_count": len(self.eligibility_results),
            "graph_offer_count": len(self.graph_projection.product_offers) if self.graph_projection else 0,
        }
        return payload


def _enrich_provider_eligibility_result(
    product: ProviderProduct,
    *,
    feed_ctx: Any,
) -> ProviderEligibilityResult:
    base = evaluate_provider_product_eligibility(product)
    product_eligibility = evaluate_product_eligibility(product, feed_ctx=feed_ctx)
    return ProviderEligibilityResult(
        product=base.product,
        status=base.status,
        reason_codes=base.reason_codes,
        derived_provider_product_id=base.derived_provider_product_id,
        product_eligibility=product_eligibility,
    )


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


# Resolved-pipeline cache. One search render resolves the pipeline twice (once for
# feed metadata, once to load eligible products) and each pass sweeps every feed row,
# which on a real feed costs seconds against the PROJECT_RULES section 9 render
# budget. The pipeline result is a pure function of feed file content, mega category
# and whether the graph projection was built -- purchasability-cache enrichment is
# applied by callers afterwards, so it is not part of this key and cannot go stale
# here. Keyed on file identity (path, mtime, size); URL-configured feeds are not
# cached.
_PIPELINE_CACHE: dict[tuple[tuple[str, int, int], str, bool], ProviderFeedPipelineResult] = {}
_PIPELINE_CACHE_MAX_ENTRIES = 8


def clear_provider_feed_pipeline_cache() -> None:
    """Drop the resolved-pipeline cache. For tests and for forcing a re-resolve."""
    _PIPELINE_CACHE.clear()


def resolve_provider_feed_pipeline(
    config: ProviderFeedConfig,
    *,
    mega_category_id: str = "",
    include_graph_projection: bool = True,
) -> ProviderFeedPipelineResult:
    """Resolve the provider feed pipeline.

    `include_graph_projection` exists for the request path: nothing in search,
    selection or redirect reads the graph projection, and building it over a real
    feed costs about a second, which the PROJECT_RULES section 9 render budget
    cannot absorb. The default stays True so external callers are unaffected.
    """
    file_key = feed_file_cache_key(config.feed_file)
    cache_key = (
        (file_key, str(mega_category_id or ""), bool(include_graph_projection))
        if file_key is not None
        else None
    )
    if cache_key is not None:
        cached = _PIPELINE_CACHE.get(cache_key)
        if cached is not None:
            return cached
    result = _resolve_provider_feed_pipeline_uncached(
        config,
        mega_category_id=mega_category_id,
        include_graph_projection=include_graph_projection,
    )
    if cache_key is not None and result.feed_status.status == "provider_feed_ready":
        if len(_PIPELINE_CACHE) >= _PIPELINE_CACHE_MAX_ENTRIES:
            _PIPELINE_CACHE.clear()
        _PIPELINE_CACHE[cache_key] = result
    return result


def _resolve_provider_feed_pipeline_uncached(
    config: ProviderFeedConfig,
    *,
    mega_category_id: str = "",
    include_graph_projection: bool = True,
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

    feed_availability_context = build_feed_availability_context(parse_result.products)
    eligibility_results = tuple(
        _enrich_provider_eligibility_result(product, feed_ctx=feed_availability_context)
        for product in parse_result.products
    )
    graph_projection = (
        project_provider_products_to_graph(
            eligibility_results,
            mega_category_id=mega_category_id,
        )
        if include_graph_projection
        else None
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
        availability_context=feed_availability_context,
    )


def is_safe_no_card_feed_status(status: str) -> bool:
    return status in PROVIDER_FEED_STATUSES and status != "provider_feed_ready"


def load_eligible_provider_feed_products(
    feed_config: ProviderFeedConfig | None = None,
) -> tuple[ProviderProduct, ...]:
    products, _availability_context = _load_eligible_products_with_availability_context(
        feed_config
    )
    return products


def _load_eligible_products_with_availability_context(
    feed_config: ProviderFeedConfig | None = None,
) -> tuple[tuple[ProviderProduct, ...], FeedAvailabilityContext | None]:
    config = feed_config or awin_feed_config_from_env()
    pipeline = resolve_provider_feed_pipeline(config, include_graph_projection=False)
    if pipeline.feed_status.status != "provider_feed_ready":
        return tuple(), None
    products = tuple(
        row.product
        for row in pipeline.eligibility_results
        if row.status == "eligible"
    )
    return enrich_provider_products_with_cache(products), pipeline.availability_context


def resolve_card_eligible_provider_feed_product_by_id(
    provider_product_id: str,
    *,
    feed_config: ProviderFeedConfig | None = None,
) -> ProviderProduct | None:
    """Find one card-eligible feed product by id, for outbound redirect resolution.

    Card eligibility is re-checked here rather than trusted from the rendered page:
    a product that became out of stock, discontinued or verified unbuyable since
    render must not be redirected to. Returns None when the id is unknown or the
    product is no longer eligible.
    """
    wanted = str(provider_product_id or "").strip()
    if not wanted:
        return None
    config = feed_config or awin_feed_config_from_env()
    # Resolve straight off the parsed feed rather than the full pipeline: this runs
    # on every outbound click, and the pipeline's per-product eligibility sweep and
    # graph projection would blow the PROJECT_RULES section 9 300ms budget. The
    # availability context is still built over the whole feed, because feed-wide
    # signals decide whether availability counts as weak.
    parse_result = load_awin_provider_feed(config)
    if parse_result.status != "provider_feed_loaded":
        return None
    products = enrich_provider_products_with_cache(parse_result.products)
    if not products:
        return None
    match = None
    for product in products:
        if str(product.provider_product_id or "").strip() == wanted:
            match = product
            break
    if match is None:
        return None
    if evaluate_provider_product_eligibility(match).status != "eligible":
        return None
    feed_ctx = build_feed_availability_context(products)
    if not evaluate_product_eligibility(match, feed_ctx=feed_ctx).card_eligible:
        return None
    return match


def resolve_search_provider_feed_product_selection(
    *,
    query: str,
    feed_config: ProviderFeedConfig | None = None,
    max_products: int = 4,
    reading: ConceptReading | None = None,
) -> ProviderProductSelectionResult:
    products, availability_context = _load_eligible_products_with_availability_context(
        feed_config
    )
    selection = select_provider_products_for_query(
        query,
        products,
        max_products=max_products,
        reading=reading,
        feed_ctx=availability_context,
    )
    if availability_context is None:
        return selection
    return replace(selection, feed_availability_context=availability_context)


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
    if selection.understood_concept:
        return decide_recommended_provider_product(
            selection.effective_query or query,
            selection.selected_products,
            required_tokens=selection.required_filter_terms,
            concept_verified=True,
            concept_id=selection.understood_concept,
            feed_ctx=selection.feed_availability_context,
        )
    return decide_recommended_provider_product(
        query,
        selection.selected_products,
        required_tokens=selection.required_query_terms or None,
        feed_ctx=selection.feed_availability_context,
    )


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

    # Only feed_status is read below, so skip the graph projection.
    pipeline = resolve_provider_feed_pipeline(
        config,
        mega_category_id=str(mega_category_id or ""),
        include_graph_projection=False,
    )
    feed_status = pipeline.feed_status
    return SearchProviderFeedMetadata(
        provider_feed_status=feed_status.status,
        provider_feed_reason_codes=feed_status.reason_codes,
        provider_feed_eligible_count=feed_status.eligible_count,
    )


def _normalized_mega_category_id(value: str | None) -> str:
    return " ".join(str(value or "").split()).strip()
