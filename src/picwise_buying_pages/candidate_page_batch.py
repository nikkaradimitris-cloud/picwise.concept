from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from .seo_slug_builder import build_buying_page_slug


class CandidatePageStatus(str, Enum):
    candidate_ready = "candidate_ready"
    needs_products = "needs_products"
    needs_locale = "needs_locale"
    needs_keywords = "needs_keywords"
    needs_four_products = "needs_four_products"
    duplicate_slug_blocked = "duplicate_slug_blocked"
    blocked = "blocked"


@dataclass(frozen=True)
class CandidatePageBuildInput:
    keyword_clusters: tuple[Mapping[str, Any], ...]
    products: tuple[Mapping[str, Any], ...]
    locale_decisions: tuple[Mapping[str, Any], ...]
    recommendation_mapping: Mapping[str, str]
    max_candidate_pages: int = 3000


@dataclass(frozen=True)
class CandidatePageRecord:
    candidate_page_id: str
    slug: str
    locale: str
    market: str
    target_category: str
    buyer_intent: bool
    main_keyword: str
    support_keywords: tuple[str, ...]
    long_tail_keywords: tuple[str, ...]
    selected_product_ids: tuple[str, ...]
    recommended_product_id: str | None
    product_count: int
    source_cluster_id: str
    source_provider_batch_id: str
    status: CandidatePageStatus
    blocker_reasons: tuple[str, ...]
    review_reasons: tuple[str, ...]
    is_public: bool = False
    is_indexable: bool = False
    sitemap_included: bool = False


@dataclass(frozen=True)
class CandidatePageBatchResult:
    total_requested: int
    total_built: int
    candidate_ready_count: int
    blocked_count: int
    needs_products_count: int
    needs_locale_count: int
    needs_keywords_count: int
    needs_four_products_count: int
    duplicate_slug_count: int
    status_counts: dict[str, int]
    blocker_counts: dict[str, int]
    candidate_pages: tuple[CandidatePageRecord, ...]
    can_move_to_step6: bool


def _norm_text(value: Any) -> str:
    return str(value or "").strip()


def _norm_lower(value: Any) -> str:
    return _norm_text(value).lower()


def _norm_upper(value: Any) -> str:
    return _norm_text(value).upper()


def _coerce_keyword_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        cleaned = [_norm_lower(item) for item in value if _norm_text(item)]
        return tuple(dict.fromkeys(cleaned))
    return tuple()


def _is_provider_ready(product: Mapping[str, Any]) -> bool:
    if isinstance(product.get("provider_ready"), bool):
        return bool(product["provider_ready"])
    status = _norm_lower(product.get("provider_status") or product.get("status"))
    return status in {"provider_ready", "step2_ready", "ready"}


def _build_locale_ready_market_by_product(
    locale_decisions: Iterable[Mapping[str, Any]],
) -> dict[str, str]:
    ready: dict[str, str] = {}
    for item in locale_decisions:
        product_id = _norm_text(item.get("product_id") or item.get("candidate_id"))
        if not product_id:
            continue
        status = _norm_lower(item.get("status"))
        if status not in {"locale_ready", "ready"}:
            continue
        market = _norm_upper(item.get("target_market") or item.get("market"))
        if market:
            ready[product_id] = market
    return ready


def _cluster_is_page_ready(cluster: Mapping[str, Any]) -> bool:
    if bool(cluster.get("is_page_ready")):
        return True
    status = _norm_lower(cluster.get("status") or cluster.get("cluster_status"))
    return status == "page_ready"


def _cluster_scale_slots(cluster: Mapping[str, Any]) -> int:
    raw = cluster.get("deterministic_scale_slots", 1)
    try:
        slots = int(raw)
    except (TypeError, ValueError):
        return 1
    return max(1, slots)


def _category_matches(product: Mapping[str, Any], target_category: str) -> bool:
    if not target_category:
        return True
    product_category = _norm_lower(product.get("target_category") or product.get("category"))
    return product_category == target_category


def _select_recommended_product_id(
    cluster_id: str,
    selected_product_ids: tuple[str, ...],
    selected_products: tuple[Mapping[str, Any], ...],
    recommendation_mapping: Mapping[str, str],
) -> str | None:
    mapped = _norm_text(recommendation_mapping.get(cluster_id, ""))
    if mapped and mapped in selected_product_ids:
        return mapped

    scored: list[tuple[float, str]] = []
    for product in selected_products:
        product_id = _norm_text(product.get("product_id"))
        if not product_id or product_id not in selected_product_ids:
            continue
        raw_score = product.get("recommendation_score")
        if raw_score is None:
            continue
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            continue
        scored.append((score, product_id))
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], item[1]))
    top_score = scored[0][0]
    top_ids = [product_id for score, product_id in scored if score == top_score]
    if top_score <= 0 or len(top_ids) != 1:
        return None
    return top_ids[0]


def _count_statuses(records: Iterable[CandidatePageRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        key = record.status.value
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _count_blockers(records: Iterable[CandidatePageRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for blocker in record.blocker_reasons:
            counts[blocker] = counts.get(blocker, 0) + 1
    return dict(sorted(counts.items()))


def build_candidate_page_batch(
    keyword_clusters: Iterable[Mapping[str, Any]],
    products: Iterable[Mapping[str, Any]],
    locale_decisions: Iterable[Mapping[str, Any]],
    recommendation_mapping: Mapping[str, str] | None = None,
    max_candidate_pages: int = 3000,
) -> dict[str, Any]:
    if not isinstance(max_candidate_pages, int) or max_candidate_pages <= 0:
        raise ValueError("max_candidate_pages must be a positive integer.")

    clusters_sorted = sorted(
        [dict(cluster) for cluster in keyword_clusters],
        key=lambda item: (_norm_text(item.get("cluster_id")), _norm_text(item.get("main_keyword"))),
    )[:max_candidate_pages]
    all_products = [dict(product) for product in products]
    locale_ready_market_by_product = _build_locale_ready_market_by_product(locale_decisions)
    recommendation_lookup = dict(recommendation_mapping or {})

    records: list[CandidatePageRecord] = []
    seen_slugs: set[str] = set()
    deterministic_slot_capacity = 0

    for cluster in clusters_sorted:
        cluster_id = _norm_text(cluster.get("cluster_id") or "cluster-unknown")
        locale = _norm_text(cluster.get("locale"))
        market = _norm_upper(cluster.get("market"))
        target_category = _norm_lower(cluster.get("target_category"))
        main_keyword = _norm_lower(cluster.get("main_keyword"))
        support_keywords = _coerce_keyword_tuple(cluster.get("support_keywords"))
        long_tail_keywords = _coerce_keyword_tuple(cluster.get("long_tail_keywords"))
        buyer_intent = bool(cluster.get("buyer_intent"))
        source_provider_batch_id = _norm_text(cluster.get("source_provider_batch_id") or "step2-provider-batch-unknown")

        slug_result = build_buying_page_slug(main_keyword or cluster_id)
        slug = slug_result.slug
        blocker_reasons: list[str] = []
        review_reasons: list[str] = []
        status = CandidatePageStatus.candidate_ready

        if not _cluster_is_page_ready(cluster):
            status = CandidatePageStatus.needs_keywords
            blocker_reasons.append("keyword_cluster_not_page_ready")

        if not slug_result.valid:
            status = CandidatePageStatus.blocked
            blocker_reasons.append(f"slug_{slug_result.reason_code}")

        matching_products = [
            product for product in all_products if _category_matches(product, target_category)
        ]
        provider_ready_products = [
            product for product in matching_products if _is_provider_ready(product)
        ]
        if not provider_ready_products and status == CandidatePageStatus.candidate_ready:
            status = CandidatePageStatus.needs_products
            blocker_reasons.append("no_provider_ready_products_for_category")

        locale_ready_products = []
        for product in provider_ready_products:
            product_id = _norm_text(product.get("product_id"))
            if not product_id:
                continue
            ready_market = locale_ready_market_by_product.get(product_id)
            if ready_market == market:
                locale_ready_products.append(product)
        if (
            provider_ready_products
            and not locale_ready_products
            and status == CandidatePageStatus.candidate_ready
        ):
            status = CandidatePageStatus.needs_locale
            blocker_reasons.append("no_locale_ready_products_for_market")

        locale_ready_products_sorted = sorted(
            locale_ready_products,
            key=lambda item: _norm_text(item.get("product_id")),
        )
        selected_products = tuple(locale_ready_products_sorted[:4])
        selected_product_ids = tuple(
            _norm_text(product.get("product_id"))
            for product in selected_products
            if _norm_text(product.get("product_id"))
        )
        if (
            0 < len(selected_product_ids) < 4
            and status == CandidatePageStatus.candidate_ready
        ):
            status = CandidatePageStatus.needs_four_products
            blocker_reasons.append("fewer_than_four_products")

        recommended_product_id = _select_recommended_product_id(
            cluster_id=cluster_id,
            selected_product_ids=selected_product_ids,
            selected_products=selected_products,
            recommendation_mapping=recommendation_lookup,
        )
        if (
            status == CandidatePageStatus.candidate_ready
            and recommended_product_id is None
        ):
            review_reasons.append("recommended_product_evidence_missing")

        if slug in seen_slugs:
            status = CandidatePageStatus.duplicate_slug_blocked
            blocker_reasons.append("duplicate_slug_detected")
        elif slug:
            seen_slugs.add(slug)

        record = CandidatePageRecord(
            candidate_page_id=f"candidate-page-{cluster_id}",
            slug=slug,
            locale=locale,
            market=market,
            target_category=target_category,
            buyer_intent=buyer_intent,
            main_keyword=main_keyword,
            support_keywords=support_keywords,
            long_tail_keywords=long_tail_keywords,
            selected_product_ids=selected_product_ids,
            recommended_product_id=recommended_product_id,
            product_count=len(selected_product_ids),
            source_cluster_id=cluster_id,
            source_provider_batch_id=source_provider_batch_id,
            status=status,
            blocker_reasons=tuple(sorted(dict.fromkeys(blocker_reasons))),
            review_reasons=tuple(sorted(dict.fromkeys(review_reasons))),
            is_public=False,
            is_indexable=False,
            sitemap_included=False,
        )
        records.append(record)
        if status == CandidatePageStatus.candidate_ready:
            deterministic_slot_capacity += _cluster_scale_slots(cluster)

    status_counts = _count_statuses(records)
    blocker_counts = _count_blockers(records)

    total_requested = max_candidate_pages
    total_built = len(records)
    candidate_ready_count = status_counts.get(CandidatePageStatus.candidate_ready.value, 0)
    needs_products_count = status_counts.get(CandidatePageStatus.needs_products.value, 0)
    needs_locale_count = status_counts.get(CandidatePageStatus.needs_locale.value, 0)
    needs_keywords_count = status_counts.get(CandidatePageStatus.needs_keywords.value, 0)
    needs_four_products_count = status_counts.get(CandidatePageStatus.needs_four_products.value, 0)
    duplicate_slug_count = status_counts.get(CandidatePageStatus.duplicate_slug_blocked.value, 0)
    blocked_count = (
        status_counts.get(CandidatePageStatus.blocked.value, 0)
        + duplicate_slug_count
        + needs_products_count
        + needs_locale_count
        + needs_keywords_count
        + needs_four_products_count
    )

    can_move_to_step6 = bool(
        candidate_ready_count > 0
        and needs_products_count == 0
        and needs_locale_count == 0
        and needs_keywords_count == 0
        and needs_four_products_count == 0
        and duplicate_slug_count == 0
        and status_counts.get(CandidatePageStatus.blocked.value, 0) == 0
        and deterministic_slot_capacity >= total_requested
    )

    result = CandidatePageBatchResult(
        total_requested=total_requested,
        total_built=total_built,
        candidate_ready_count=candidate_ready_count,
        blocked_count=blocked_count,
        needs_products_count=needs_products_count,
        needs_locale_count=needs_locale_count,
        needs_keywords_count=needs_keywords_count,
        needs_four_products_count=needs_four_products_count,
        duplicate_slug_count=duplicate_slug_count,
        status_counts=status_counts,
        blocker_counts=blocker_counts,
        candidate_pages=tuple(records),
        can_move_to_step6=can_move_to_step6,
    )
    payload = asdict(result)
    payload["candidate_pages"] = [
        {
            **item,
            "status": item["status"].value,
        }
        for item in payload["candidate_pages"]
    ]
    payload["planning_summary"] = {
        "deterministic_slot_capacity": deterministic_slot_capacity,
        "requested_candidate_slots": total_requested,
        "capacity_satisfies_requested_slots": deterministic_slot_capacity >= total_requested,
    }
    return payload
