from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
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
from .feed_intake import measure_feed_intake
from .graph_projection import project_provider_products_to_graph
from .offer_health import (
    build_feed_availability_context,
    evaluate_product_eligibility,
    offer_validity_reason_codes,
)
from .prepared_catalogue import (
    PreparedCatalogue,
    check_prepared_catalogue,
    prepared_catalogue_age_limit,
    prepared_catalogue_path,
)
from .normalization import extract_merchant_name
from .purchasability_cache import enrich_provider_products_with_cache, resolve_purchasability_cache
from .suggestions import SearchSuggestion, build_search_suggestions
from .search_selection import (
    ProviderFeedRecommendationDecision,
    ProviderProductSelectionResult,
    SearchCatalogue,
    _product_concepts,
    build_search_catalogue,
    decide_recommended_provider_product,
    is_strong_feed_opportunity_selection,
    product_kind_key,
    product_non_new_condition,
    remember_product_kinds,
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
    _PREPARED_STATE.clear()
    remember_product_kinds({})


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
    # Only the graph projection reads the mega category. Without it every mega category
    # shares one entry: each used to judge the whole feed again, seconds on a real feed.
    cache_mega_category_id = str(mega_category_id or "") if include_graph_projection else ""
    cache_key = (
        (file_key, cache_mega_category_id, bool(include_graph_projection))
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


def _feed_eligible_products(pipeline: ProviderFeedPipelineResult) -> tuple[ProviderProduct, ...]:
    return tuple(row.product for row in pipeline.eligibility_results if row.status == "eligible")


def _search_catalogue(pipeline: ProviderFeedPipelineResult) -> SearchCatalogue:
    """The products a search reads, judged once per feed load: eligible in the feed,
    card-eligible, and which of them are new (`build_search_catalogue`)."""

    def build(ready: ProviderFeedPipelineResult) -> SearchCatalogue:
        rows = tuple(row for row in ready.eligibility_results if row.status == "eligible")
        # The pipeline judged each row against the same availability context as it
        # loaded the feed; that judgement is reused rather than made a second time.
        judged = all(row.product_eligibility is not None for row in rows)
        return build_search_catalogue(
            tuple(row.product for row in rows),
            feed_ctx=ready.availability_context,
            card_eligible=(
                tuple(row.product_eligibility.card_eligible for row in rows) if judged else None
            ),
        )

    return _cached_for(pipeline, "search_catalogue", build)


# The search catalogue, counts and suggestions of the pipeline last read, kept with it
# so they are worked out once per feed load. Keyed by the pipeline object itself.
_CATALOGUE_CACHE: dict[str, tuple[ProviderFeedPipelineResult, Any]] = {}


def _cached_for(pipeline: ProviderFeedPipelineResult, name: str, build):
    cached = _CATALOGUE_CACHE.get(name)
    if cached is not None and cached[0] is pipeline:
        return cached[1]
    value = build(pipeline)
    _CATALOGUE_CACHE[name] = (pipeline, value)
    return value


def _catalogue_counts(pipeline: ProviderFeedPipelineResult) -> tuple[int, int]:
    """The products a search looks through, the feed's eligible ones, and their shops.

    Read from the pipeline as loaded, without judging each product again: this runs
    when a page is drawn, and judging 40,000 products takes seconds.
    """
    products = [row.product for row in pipeline.eligibility_results if row.status == "eligible"]
    shops = {
        str(extract_merchant_name(product.raw if isinstance(product.raw, dict) else {}) or "").strip().lower()
        for product in products
    } - {""}
    return len(products), len(shops)


# The prepared feed this process read (`prepared_catalogue.py`), with the file identity
# it was read from, and its search catalogue for the day it was built on.
_PREPARED_STATE: dict[str, Any] = {}


def prepare_feed_catalogue(
    feed_config: ProviderFeedConfig | None = None,
    *,
    now: datetime | None = None,
) -> PreparedCatalogue | None:
    """The configured feed read and judged as a search reads it, ready to be written
    (`tools/prepare_catalogue.py`), or None when the feed cannot be read."""
    config = feed_config or awin_feed_config_from_env()
    pipeline = resolve_provider_feed_pipeline(config, include_graph_projection=False)
    if pipeline.feed_status.status != "provider_feed_ready" or pipeline.availability_context is None:
        return None
    catalogue = _search_catalogue(pipeline)
    eligible_count, shop_count = _catalogue_counts(pipeline)
    return PreparedCatalogue(
        prepared_at=now or datetime.now(timezone.utc),
        feed_status=pipeline.feed_status,
        availability_context=pipeline.availability_context,
        products=catalogue.products,
        non_new=tuple(product_non_new_condition(product) for product in catalogue.products),
        kinds=tuple(
            _product_concepts(product, fields)
            for product, fields in zip(catalogue.products, catalogue.fields)
        ),
        eligible_count=eligible_count,
        shop_count=shop_count,
        suggestions=build_search_suggestions(catalogue.new_products),
        search_fields=catalogue.fields,
    )


def measure_configured_feed_intake(feed_config: ProviderFeedConfig | None = None) -> dict[str, Any] | None:
    """Per shop, what the configured feed brings in and why the rest is held back
    (`feed_intake`), for the build's public note; None when the feed cannot be read.
    Reads the feed as `prepare_feed_catalogue` did, from the same cache."""
    config = feed_config or awin_feed_config_from_env()
    pipeline = resolve_provider_feed_pipeline(config, include_graph_projection=False)
    if pipeline.feed_status.status != "provider_feed_ready":
        return None
    not_new = {
        id(row.product)
        for row in pipeline.eligibility_results
        if row.status == "eligible"
        and row.product_eligibility is not None
        and row.product_eligibility.card_eligible
        and product_non_new_condition(row.product)
    }
    return measure_feed_intake(pipeline.eligibility_results, not_new_products=not_new)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _active_prepared_catalogue() -> PreparedCatalogue | None:
    """The prepared feed to read instead of the feed itself, when there is a fresh one.

    Not with a purchasability cache configured: a checked shop page can show a product
    the prepared file had no reason to keep, or hide one it kept.
    """
    path = prepared_catalogue_path()
    if path is None or resolve_purchasability_cache() is not None:
        return None
    file_key = feed_file_cache_key(str(path))
    if file_key is None:
        return None
    if _PREPARED_STATE.get("file_key") != file_key:
        check = check_prepared_catalogue(path)
        _PREPARED_STATE.clear()
        _PREPARED_STATE["file_key"] = file_key
        _PREPARED_STATE["prepared"] = check.catalogue
        _PREPARED_STATE["check"] = check
        remember_product_kinds({})
    prepared = _PREPARED_STATE.get("prepared")
    # Older than the limit, the feed itself is read again until a new file comes.
    return prepared if prepared is not None and _is_fresh(prepared) else None


def _is_fresh(prepared: PreparedCatalogue) -> bool:
    return datetime.now(timezone.utc) - prepared.prepared_at <= prepared_catalogue_age_limit()


def prepared_catalogue_status() -> dict[str, Any]:
    """Whether this server answers from a prepared feed, for the readiness page.

    "in_use" with the time it was prepared; else why not: "not_present" (no file in
    this deployment, or none configured), "not_used" (a purchasability cache is
    configured), "too_old", "other_code", "other_format" or "unreadable", and in each of
    those the server reads the feed itself. Loads the file when this process has not.
    """
    path = prepared_catalogue_path()
    if path is None or feed_file_cache_key(str(path)) is None:
        return {"state": "not_present"}
    if resolve_purchasability_cache() is not None:
        return {"state": "not_used", "reason": "purchasability_cache_configured"}
    prepared = _active_prepared_catalogue()
    if prepared is not None:
        return {"state": "in_use", **_prepared_time(prepared.prepared_at)}
    check = _PREPARED_STATE.get("check")
    if check is None:
        return {"state": "not_present"}
    if check.state == "fresh":
        # Read fresh, and older than the limit since.
        return {"state": "too_old", **_prepared_time(check.prepared_at)}
    status: dict[str, Any] = {"state": check.state}
    if check.prepared_at is not None:
        status.update(_prepared_time(check.prepared_at))
    return status


def _prepared_time(prepared_at: datetime) -> dict[str, Any]:
    age = datetime.now(timezone.utc) - prepared_at
    return {
        "prepared_at": prepared_at.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "age_hours": round(age.total_seconds() / 3600, 1),
    }


def _prepared_search_catalogue(prepared: PreparedCatalogue) -> SearchCatalogue:
    """The prepared products a search reads today.

    Everything was judged when the file was written except the one rule that moves with
    the date: an offer whose validity window has closed since then is left out.
    """
    today = _today()
    cached = _PREPARED_STATE.get("catalogue")
    if cached is not None and cached[0] == today:
        return cached[1]
    open_today = tuple(
        not offer_validity_reason_codes(product, today=today) for product in prepared.products
    )
    catalogue = build_search_catalogue(
        prepared.products,
        feed_ctx=prepared.availability_context,
        card_eligible=open_today,
        non_new=prepared.non_new,
        fields=prepared.search_fields or None,
    )
    kinds_of = {id(product): kinds for product, kinds in zip(prepared.products, prepared.kinds)}
    remember_product_kinds(
        {
            product_kind_key(product, fields): kinds_of[id(product)]
            for product, fields in zip(catalogue.products, catalogue.fields)
        }
    )
    _PREPARED_STATE["catalogue"] = (today, catalogue)
    return catalogue


def peek_search_catalogue_counts() -> tuple[int, int] | None:
    """(products, shops) a search reads, when this process has the feed loaded, else None.

    For the scanning screen (step 4): "Searching 39,815 products from 2 shops". It reads
    only the feed this process already holds, the one loaded last: it never loads one,
    and never reads the feed configuration either, which for a feed URL can start a
    download. A page drawn before the first search stays fast and names no number.
    """
    prepared = _PREPARED_STATE.get("prepared")
    if prepared is not None and _is_fresh(prepared):
        return prepared.eligible_count, prepared.shop_count
    try:
        entries = list(_PIPELINE_CACHE.items())
    except RuntimeError:
        # The search warm-up thread added a pipeline while this read: say no number.
        return None
    for (_file_key, mega_category_id, with_graph), pipeline in reversed(entries):
        if not mega_category_id and not with_graph and pipeline.feed_status.status == "provider_feed_ready":
            return _cached_for(pipeline, "counts", _catalogue_counts)
    return None


def search_suggestions(
    feed_config: ProviderFeedConfig | None = None,
) -> tuple[SearchSuggestion, ...]:
    """What the search box suggests for the connected catalogue (`suggestions.py`)."""
    prepared = _active_prepared_catalogue() if feed_config is None else None
    if prepared is not None:
        return prepared.suggestions
    config = feed_config or awin_feed_config_from_env()
    pipeline = resolve_provider_feed_pipeline(config, include_graph_projection=False)
    if pipeline.feed_status.status != "provider_feed_ready":
        return tuple()
    return _cached_for(
        pipeline,
        "suggestions",
        lambda ready: build_search_suggestions(_search_catalogue(ready).new_products),
    )


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
    prepared = _active_prepared_catalogue() if feed_config is None else None
    if prepared is not None:
        index = _PREPARED_STATE.get("by_id")
        if index is None:
            index = {str(product.provider_product_id or "").strip(): product for product in prepared.products}
            _PREPARED_STATE["by_id"] = index
        match = index.get(wanted)
        if match is None or evaluate_provider_product_eligibility(match).status != "eligible":
            return None
        if not evaluate_product_eligibility(match, feed_ctx=prepared.availability_context).card_eligible:
            return None
        return match
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
    shown: int = 0,
) -> ProviderProductSelectionResult:
    prepared = _active_prepared_catalogue() if feed_config is None else None
    if prepared is not None:
        selection = select_provider_products_for_query(
            query,
            prepared.products,
            max_products=max_products,
            reading=reading,
            feed_ctx=prepared.availability_context,
            shown=shown,
            catalogue=_prepared_search_catalogue(prepared),
        )
        return replace(selection, feed_availability_context=prepared.availability_context)
    config = feed_config or awin_feed_config_from_env()
    pipeline = resolve_provider_feed_pipeline(config, include_graph_projection=False)
    catalogue = None
    if pipeline.feed_status.status != "provider_feed_ready":
        products, availability_context = tuple(), None
    else:
        products = _feed_eligible_products(pipeline)
        availability_context = pipeline.availability_context
        purchasability_cache = resolve_purchasability_cache()
        if purchasability_cache is None:
            catalogue = _search_catalogue(pipeline)
        else:
            # A checked shop page can change whether a product may be shown between
            # two searches, so these products are judged on every search.
            products = enrich_provider_products_with_cache(products, purchasability_cache)
    selection = select_provider_products_for_query(
        query,
        products,
        max_products=max_products,
        reading=reading,
        feed_ctx=availability_context,
        shown=shown,
        catalogue=catalogue,
    )
    if availability_context is None:
        return selection
    return replace(selection, feed_availability_context=availability_context)


def resolve_search_provider_feed_recommendation_decision(
    *,
    query: str,
    selection: ProviderProductSelectionResult,
) -> ProviderFeedRecommendationDecision:
    if selection.price_first:
        return _price_first_recommendation_decision(selection)
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
            condition_requested=bool(selection.condition_request),
            feed_ctx=selection.feed_availability_context,
        )
    return decide_recommended_provider_product(
        query,
        selection.selected_products,
        required_tokens=selection.required_query_terms or None,
        condition_requested=bool(selection.condition_request),
        feed_ctx=selection.feed_availability_context,
    )


# Price first (owner, 2026-10-15 and 2026-10-16). The selection already chose the
# Recommended over the whole answer, by price; nothing here scores the products again.
# The old step re-read the search's words from each of four cards, found none carrying
# all of them for "3 seater sofa grey", and left a page of four right products empty.
_PRICE_FIRST_NO_RECOMMENDATION = {
    "no_product_code": "no_recommendation_without_product_code",
    "too_few_products": "no_recommendation_too_few_products",
}


def _price_first_recommendation_decision(
    selection: ProviderProductSelectionResult,
) -> ProviderFeedRecommendationDecision:
    if selection.status == "insufficient_relevant_products":
        return ProviderFeedRecommendationDecision(
            decision_status="insufficient_selected_products",
            recommendation_reason_codes=("insufficient_selected_products",),
        )
    if selection.status != "selected" or not selection.selected_products:
        return ProviderFeedRecommendationDecision(
            decision_status="no_selection",
            recommendation_reason_codes=("no_feed_selection",),
        )
    if selection.recommended_product_id:
        return ProviderFeedRecommendationDecision(
            decision_status="recommended",
            recommended_product_id=selection.recommended_product_id,
            recommendation_reason_codes=("price_first_mid_priced",),
            # Not a confidence judgement: the Recommended follows a stated price rule.
            recommendation_confidence="not_applicable",
        )
    status = _PRICE_FIRST_NO_RECOMMENDATION.get(
        selection.recommendation_status, "no_recommendation_too_few_products"
    )
    return ProviderFeedRecommendationDecision(
        decision_status=status,
        recommendation_reason_codes=(status,),
        recommendation_confidence="not_applicable",
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

    if not _normalized_mega_category_id(mega_category_id) and not allow_without_mega_category:
        return None
    feed_status = resolve_provider_feed_status(feed_config)
    return SearchProviderFeedMetadata(
        provider_feed_status=feed_status.status,
        provider_feed_reason_codes=feed_status.reason_codes,
        provider_feed_eligible_count=feed_status.eligible_count,
    )


def _normalized_mega_category_id(value: str | None) -> str:
    return " ".join(str(value or "").split()).strip()


def resolve_provider_feed_status(feed_config: ProviderFeedConfig | None = None) -> ProviderFeedStatus:
    """The status of the feed this server answers from: the prepared feed when there is
    a fresh one, else the configured feed as loaded."""
    prepared = _active_prepared_catalogue() if feed_config is None else None
    if prepared is not None:
        return prepared.feed_status
    config = feed_config or awin_feed_config_from_env()
    # Only feed_status is read, so skip the graph projection.
    return resolve_provider_feed_pipeline(config, include_graph_projection=False).feed_status
