from __future__ import annotations

import logging
import os
import tempfile
import threading
from collections.abc import Callable, Iterable, Sequence
from contextlib import contextmanager
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
from .kind_choices import KindChoice, build_kind_choices
from .offer_health import (
    build_feed_availability_context,
    evaluate_product_eligibility,
    offer_validity_reason_codes,
)
from .product_photos import gone_photos, gone_photos_key, photo_is_gone
from .prepared_catalogue import (
    PreparedCatalogue,
    check_prepared_catalogue,
    prepared_catalogue_age_limit,
    prepared_catalogue_path,
)
from .normalization import extract_merchant_name
from .purchasability_cache import enrich_provider_products_with_cache, resolve_purchasability_cache
from .shop_catalogue import apply_shop_catalogues
from .suggestions import SearchSuggestion, build_search_suggestions
from .search_selection import (
    ProviderFeedRecommendationDecision,
    ProviderProductSelectionResult,
    SearchCatalogue,
    _product_concepts,
    _product_search_fields,
    _kind_index,
    _word_lookup,
    build_search_catalogue,
    decide_recommended_provider_product,
    forget_search_indexes,
    is_strong_feed_opportunity_selection,
    product_kind_key,
    product_non_new_condition,
    remember_product_kinds,
    select_provider_products_for_query,
    warm_kind_index,
    warm_word_lookup,
)

logger = logging.getLogger(__name__)


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
    _KEEPER.pop("refused", None)
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

    # What the shops' own catalogues and the rows' barcodes say, before any row is
    # judged (`shop_catalogue.py`, owner, 2026-10-26).
    parse_result = replace(parse_result, products=apply_shop_catalogues(parse_result.products))
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


def _search_catalogue(
    pipeline: ProviderFeedPipelineResult, *, leave_out_gone_photos: bool = True
) -> SearchCatalogue:
    """The products a search reads, judged once per feed load and list of gone photos:
    eligible in the feed, card-eligible, their photo not gone (`product_photos`), and
    which of them are new (`build_search_catalogue`).

    The preparation keeps the products whose photo is gone (`leave_out_gone_photos`
    False): the nightly photo check reads its photos from the prepared file, and asks
    again after a week whether a gone one has come back."""
    photos = gone_photos_key() if leave_out_gone_photos else ("every photo",)
    name = "search_catalogue" if leave_out_gone_photos else "search_catalogue_every_photo"
    cached = _CATALOGUE_CACHE.get(name)
    if cached is not None and cached[0] is pipeline and cached[1][0] == photos:
        return cached[1][1]

    def build(ready: ProviderFeedPipelineResult) -> SearchCatalogue:
        gone = gone_photos() if leave_out_gone_photos else frozenset()
        rows = tuple(
            row
            for row in ready.eligibility_results
            if row.status == "eligible" and not photo_is_gone(row.product, gone)
        )
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

    catalogue = build(pipeline)
    _CATALOGUE_CACHE[name] = (pipeline, (photos, catalogue))
    return catalogue


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
    return len(products), len(_shops_of(products))


def _shops_of(products: Sequence[ProviderProduct]) -> set[str]:
    """The shops the products come from, each named once."""
    return {
        str(extract_merchant_name(product.raw if isinstance(product.raw, dict) else {}) or "").strip().lower()
        for product in products
    } - {""}


# The prepared feed this process read (`prepared_catalogue.py`), with the file identity
# it was read from, and its search catalogue for the day it was built on.
_PREPARED_STATE: dict[str, Any] = {}
# Held while a prepared file is read where a request may be reading it too, so that it
# is read once; never while a search runs.
_PREPARED_LOCK = threading.RLock()
# The keeper of the server's site (`keep_prepared_catalogue_loaded`): its thread, the
# process that started it, and the prepared file it refused last.
_KEEPER: dict[str, Any] = {}


def _keeper_on() -> bool:
    """Is this process's keeper at work? Then a request never loads a new prepared file
    or builds a new day's catalogue itself while it has one to answer from: the keeper
    does, off to the side. Not in a process forked from the one that started it, nor
    once its thread has ended: a request then loads as without a keeper."""
    thread = _KEEPER.get("thread")
    return thread is not None and thread.is_alive() and _KEEPER.get("pid") == os.getpid()


def prepare_feed_catalogue(
    feed_config: ProviderFeedConfig | None = None,
    *,
    now: datetime | None = None,
    cap: Callable[
        [tuple[ProviderProduct, ...], tuple[frozenset[str], ...], FeedAvailabilityContext],
        Sequence[bool] | None,
    ]
    | None = None,
) -> PreparedCatalogue | None:
    """The configured feed read and judged as a search reads it, ready to be written
    (`tools/prepare_catalogue.py`), or None when the feed cannot be read.

    `cap`, when given, says which of the products a card can show the search keeps, in
    their order (owner, 2026-11-08: the cap of 15% a category holds for the search too,
    `catalogue_cap`): the prepared catalogue, its suggestions and its choices then hold
    only those. None from it keeps every product."""
    config = feed_config or awin_feed_config_from_env()
    pipeline = resolve_provider_feed_pipeline(config, include_graph_projection=False)
    if pipeline.feed_status.status != "provider_feed_ready" or pipeline.availability_context is None:
        return None
    catalogue = _search_catalogue(pipeline, leave_out_gone_photos=False)
    eligible_count = _catalogue_counts(pipeline)[0]
    kinds = tuple(
        _product_concepts(product, fields) for product, fields in zip(catalogue.products, catalogue.fields)
    )
    if cap is not None:
        keep = cap(catalogue.products, kinds, pipeline.availability_context)
        if keep is not None and not all(keep):
            places = [place for place, kept in enumerate(keep) if kept]
            products = tuple(catalogue.products[place] for place in places)
            kinds = tuple(kinds[place] for place in places)
            catalogue = build_search_catalogue(
                products,
                feed_ctx=pipeline.availability_context,
                card_eligible=tuple(True for _product in products),
                non_new=tuple(product_non_new_condition(product) for product in products),
                fields=tuple(catalogue.fields[place] for place in places),
            )
    choices = _catalogue_kind_choices(catalogue, kinds)
    # The shops of the products the search keeps: a shop the cap left nothing of is not
    # one the search reads (the home page names them, owner, 2026-11-12).
    shop_count = len(_shops_of(catalogue.products))
    return PreparedCatalogue(
        prepared_at=now or datetime.now(timezone.utc),
        feed_status=pipeline.feed_status,
        availability_context=pipeline.availability_context,
        products=catalogue.products,
        non_new=tuple(product_non_new_condition(product) for product in catalogue.products),
        kinds=kinds,
        eligible_count=eligible_count,
        shop_count=shop_count,
        suggestions=build_search_suggestions(catalogue.new_products, choices=choices),
        search_fields=catalogue.fields,
        choices=choices,
    )


def _catalogue_kind_choices(
    catalogue: SearchCatalogue, kinds: tuple[frozenset[str], ...] | None = None
) -> dict[str, tuple[KindChoice, ...]]:
    """The choices of every general kind, for the new products a search reads
    (`kind_choices.build_kind_choices`). `kinds`, when given, are those of
    `catalogue.products`, in order."""
    if kinds is None:
        new_kinds = [
            _product_concepts(product, fields)
            for product, fields in zip(catalogue.new_products, catalogue.new_fields)
        ]
    else:
        kinds_of = {id(product): product_kinds for product, product_kinds in zip(catalogue.products, kinds)}
        new_kinds = [kinds_of[id(product)] for product in catalogue.new_products]
    return build_kind_choices(catalogue.new_products, new_kinds, catalogue.new_fields)


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
    return measure_feed_intake(
        pipeline.eligibility_results,
        not_new_products=not_new,
        read_kinds=lambda product: _product_concepts(product, _product_search_fields(product)),
    )


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
        kept = _PREPARED_STATE.get("prepared") if _keeper_on() else None
        if kept is None or not _is_fresh(kept):
            with _PREPARED_LOCK:
                # Unless another thread of this process read it while this one waited.
                if _PREPARED_STATE.get("file_key") != file_key:
                    check = check_prepared_catalogue(path)
                    _PREPARED_STATE.clear()
                    _PREPARED_STATE["file_key"] = file_key
                    _PREPARED_STATE["prepared"] = check.catalogue
                    _PREPARED_STATE["check"] = check
                    remember_product_kinds({})
        # Else the keeper is reading the new file: the one loaded answers until then.
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

    Everything was judged when the file was written except what moves after it: an offer
    whose validity window has closed since then is left out, and so is a product whose
    photo the nightly check has found gone since (`product_photos`, owner, 2026-11-01).
    """
    today = _today()
    photos = gone_photos_key()
    cached = _PREPARED_STATE.get("catalogue")
    if cached is not None and (cached[0] == (today, photos) or _keeper_on()):
        # With a keeper, the catalogue of the day before, or of before the night's photo
        # check, answers for the seconds the keeper takes to build the new one.
        return cached[1]
    with _PREPARED_LOCK:
        cached = _PREPARED_STATE.get("catalogue")
        if cached is not None and cached[0] == (today, photos):
            return cached[1]
        catalogue, kinds, new_kinds = _build_prepared_search_catalogue(prepared, today)
        remember_product_kinds(kinds)
        _PREPARED_STATE["catalogue"] = ((today, photos), catalogue)
    # The search's indexes, built in the background: no search waits for them.
    warm_word_lookup(catalogue.new_fields)
    warm_kind_index(catalogue.new_products, catalogue.new_fields, new_kinds)
    return catalogue


def _build_prepared_search_catalogue(
    prepared: PreparedCatalogue, today: date
) -> tuple[SearchCatalogue, dict[tuple[str, str, str], frozenset[str]], tuple[frozenset[str], ...]]:
    """The prepared products a search reads on `today` with the photos gone now; their
    kinds as `remember_product_kinds` takes them; and the kinds of the new ones, in
    order, for their kind index."""
    gone = gone_photos()
    open_today = tuple(
        not offer_validity_reason_codes(product, today=today) and not photo_is_gone(product, gone)
        for product in prepared.products
    )
    catalogue = build_search_catalogue(
        prepared.products,
        feed_ctx=prepared.availability_context,
        card_eligible=open_today,
        non_new=prepared.non_new,
        fields=prepared.search_fields or None,
    )
    kinds_of = {id(product): kinds for product, kinds in zip(prepared.products, prepared.kinds)}
    kinds = {
        product_kind_key(product, fields): kinds_of[id(product)]
        for product, fields in zip(catalogue.products, catalogue.fields)
    }
    new_kinds = tuple(kinds_of[id(product)] for product in catalogue.new_products)
    return catalogue, kinds, new_kinds


@contextmanager
def _one_process_at_a_time():
    """Held by a keeper while it reads a new prepared file: the site's workers each
    keep their own copy, and reading it in all of them at once would hold every old
    copy, every new one and the files' text together. Without `fcntl`, or where the
    lock cannot be made, each reads as it comes."""
    handle = None
    try:
        import fcntl

        handle = open(os.path.join(tempfile.gettempdir(), "picwise-prepared-catalogue.lock"), "a+b")
        fcntl.flock(handle, fcntl.LOCK_EX)
    except (ImportError, OSError):
        if handle is not None:
            handle.close()
            handle = None
    try:
        yield
    finally:
        if handle is not None:
            handle.close()


def refresh_prepared_catalogue() -> str:
    """One look by the keeper: the prepared file and the day's catalogue this process
    answers from, brought up to date off to the side; what was done.

    - "loaded": nothing was loaded yet (a worker just started): the file is read as a
      request reads it, and the day's catalogue and its indexes built, before a visitor
      asks. The audit of 2026-11-10 measured the first request of each worker after the
      night's preparation waiting 5.4 to 5.7 s for the file, and its first search 3 s.
    - "changed": a new prepared file was read, its catalogue and indexes built, and put
      in the place of the one loaded in one step. Requests go on answering from the old
      one until that step.
    - "refused": the new file cannot stand in for the feed (written by other code, as
      during a deployment before this process is restarted; unreadable): the one loaded
      goes on answering while it is fresh, and the file is not read again.
    - "rebuilt": the day changed, or the photos found gone did: the day's catalogue was
      built again and put in place in one step.
    - "current" when there was nothing to do; "not_used" when no prepared file stands
      in for the feed here.
    """
    path = prepared_catalogue_path()
    if path is None or resolve_purchasability_cache() is not None:
        return "not_used"
    file_key = feed_file_cache_key(str(path))
    if file_key is None:
        return "not_used"
    if _PREPARED_STATE.get("file_key") != file_key and _KEEPER.get("refused") != file_key:
        loaded = _PREPARED_STATE.get("prepared")
        if loaded is None or not _is_fresh(loaded):
            # Nothing here answers yet, so there is no old copy to hold beside the new:
            # only the reading of the file is taken in turns.
            with _one_process_at_a_time():
                prepared = _active_prepared_catalogue()
            if prepared is None:
                return "refused"
            catalogue = _prepared_search_catalogue(prepared)
            _word_lookup(catalogue.new_fields)
            _kind_index(catalogue.new_products, catalogue.new_fields)
            return "loaded"
        with _one_process_at_a_time():
            check = check_prepared_catalogue(path)
            if check.catalogue is None:
                _KEEPER["refused"] = file_key
                return "refused"
            _put_in_place(check.catalogue, file_key=file_key, check=check)
        return "changed"
    prepared = _PREPARED_STATE.get("prepared")
    if prepared is None or not _is_fresh(prepared):
        return "current"
    cached = _PREPARED_STATE.get("catalogue")
    if cached is None or cached[0] != (_today(), gone_photos_key()):
        _put_in_place(prepared)
        return "rebuilt"
    return "current"


def _put_in_place(prepared: PreparedCatalogue, *, file_key: Any = None, check: Any = None) -> None:
    """Build `prepared`'s catalogue of today and its indexes off to the side, then put
    them in the place of what this process answers from, in one step. With `file_key`,
    `prepared` is a new file's; without, the one already loaded, for a new day or
    newly gone photos."""
    today, photos = _today(), gone_photos_key()
    catalogue, kinds, new_kinds = _build_prepared_search_catalogue(prepared, today)
    _word_lookup(catalogue.new_fields)
    _kind_index(catalogue.new_products, catalogue.new_fields, new_kinds)
    change: dict[str, Any] = {"catalogue": ((today, photos), catalogue)}
    if file_key is not None:
        change.update(
            file_key=file_key,
            prepared=prepared,
            check=check,
            by_id={str(product.provider_product_id or "").strip(): product for product in prepared.products},
        )
    with _PREPARED_LOCK:
        before = _PREPARED_STATE.get("catalogue")
        # A product's kinds are the same in both catalogues: the same code read them.
        remember_product_kinds(kinds, keep_indexes=True)
        # One step: a request reads all of the old or all of the new.
        _PREPARED_STATE.update(change)
    if before is not None and before[1] is not catalogue:
        forget_search_indexes(before[1].fields, before[1].new_fields)


def keep_prepared_catalogue_loaded(
    *, every_seconds: float = 10.0, once_loaded: Callable[[], object] | None = None
) -> threading.Event | None:
    """Start this process's keeper: a thread that looks every few seconds
    (`refresh_prepared_catalogue`), so that no request loads the prepared file or builds
    a day's catalogue itself. For the server's site, whose workers live for days
    (`deployment/server/wsgi_server.py`); never on a serverless host, whose process is
    frozen between requests. `once_loaded` is called once, by the keeper's thread, when
    this process first has a catalogue to answer from: the site makes its first search
    there, so that no visitor's is. Returns the event that stops it, or None where no
    prepared file is configured or a keeper already runs here."""
    if prepared_catalogue_path() is None or _keeper_on():
        return None
    stop = threading.Event()

    def look() -> None:
        waiting = once_loaded
        while not stop.is_set():
            try:
                refresh_prepared_catalogue()
                if waiting is not None and _PREPARED_STATE.get("catalogue") is not None:
                    waiting, call = None, waiting
                    call()
            except Exception:  # the next look tries again; requests load as without a keeper
                logger.exception("the prepared catalogue's keeper could not refresh it")
            stop.wait(every_seconds)

    thread = threading.Thread(target=look, name="picwise-prepared-keeper", daemon=True)
    _KEEPER.update(thread=thread, pid=os.getpid())
    thread.start()
    return stop


def peek_search_catalogue_counts() -> tuple[int, int] | None:
    """(products, shops) a search reads, when this process has the feed loaded, else None.

    For the home page's first fact, "250,000+ products from 80 UK shops" (owner,
    2026-11-12). From a prepared catalogue, the products the search keeps after the cap
    and their shops, never the feed's products before it (the scanning screen had named
    about 735,000 while the search held about 251,000). It reads only the feed this
    process already holds, the one loaded last: it never loads one, and never reads the
    feed configuration either, which for a feed URL can start a download. A page drawn
    before the first search stays fast and names no number.
    """
    prepared = _PREPARED_STATE.get("prepared")
    if prepared is not None and _is_fresh(prepared):
        return len(prepared.products), prepared.shop_count
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
        lambda ready: build_search_suggestions(
            _search_catalogue(ready).new_products, choices=search_kind_choices(feed_config)
        ),
    )


def search_kind_choices(
    feed_config: ProviderFeedConfig | None = None,
) -> dict[str, tuple[KindChoice, ...]]:
    """Per general kind, the choices a search for it offers (`kind_choices.py`): read
    from the prepared feed, or worked out once per feed load."""
    prepared = _active_prepared_catalogue() if feed_config is None else None
    if prepared is not None:
        return prepared.choices
    config = feed_config or awin_feed_config_from_env()
    pipeline = resolve_provider_feed_pipeline(config, include_graph_projection=False)
    if pipeline.feed_status.status != "provider_feed_ready":
        return {}
    return _cached_for(pipeline, "kind_choices", lambda ready: _catalogue_kind_choices(_search_catalogue(ready)))


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
    min_price: float | None = None,
    fitting_for: Callable[[str], Iterable[str] | None] | None = None,
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
            min_price=min_price,
            catalogue=_prepared_search_catalogue(prepared),
            fitting_for=fitting_for,
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
        min_price=min_price,
        catalogue=catalogue,
        fitting_for=fitting_for,
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
    # A price chosen on the price bar (owner, 2026-11-12).
    "price_chosen": "no_recommendation_price_chosen",
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
