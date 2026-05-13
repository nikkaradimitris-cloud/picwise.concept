from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .affiliate_feed_adapter import AffiliateFeedRowStatus, adapt_affiliate_feed_rows
from .contracts import SourceTrustLevel
from .eligibility import run_product_eligibility_gate
from .recommendation_engine import build_pickwise_recommendation_set


@dataclass(frozen=True)
class AffiliateFeedDryRunReport:
    total_rows: int
    mapped_count: int
    review_required_count: int
    rejected_count: int
    eligibility_pass_count: int
    eligibility_fail_count: int
    recommendation_ready_count: int
    missing_field_counts: dict[str, int]
    rejection_reason_counts: dict[str, int]
    review_reason_counts: dict[str, int]
    locale_counts: dict[str, int]
    market_counts: dict[str, int]
    currency_counts: dict[str, int]
    seller_reliability_counts: dict[str, int]
    readiness_status: str
    blockers_before_3000_candidate_pages: tuple[str, ...]


def _increment(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def _to_local_rows_or_raise(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise TypeError("rows must be a local list[dict].")
    materialized_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise TypeError(f"rows[{index}] must be a dict.")
        materialized_rows.append(dict(row))
    return materialized_rows


def _safe_for_recommendation(candidate: Any) -> bool:
    metadata = candidate.metadata or {}
    enrichment = metadata.get("enrichment") if isinstance(metadata, dict) else {}
    seller_reliability = str((enrichment or {}).get("seller_reliability_status", "unknown")).strip().lower()
    return (
        bool((candidate.title or "").strip())
        and bool((candidate.image_url or "").strip())
        and bool((candidate.outbound_url or "").strip())
        and candidate.price is not None
        and candidate.price > 0
        and seller_reliability in {"trusted", "acceptable"}
    )


def _derive_readiness_status(
    *,
    eligibility_pass_count: int,
    recommendation_ready_count: int,
    blockers_before_3000_candidate_pages: tuple[str, ...],
) -> str:
    if eligibility_pass_count < 4 or recommendation_ready_count < 4:
        return "blocked"
    if blockers_before_3000_candidate_pages:
        return "needs_enrichment"
    return "ready_for_small_batch"


def run_affiliate_feed_dry_run(
    rows: list[dict[str, Any]],
    *,
    source_id: str,
    trusted_seller_status_by_name: dict[str, str] | None = None,
    expected_vertical: str = "retail_physical_products",
    source_trust_level: SourceTrustLevel = SourceTrustLevel.PARTNER_VERIFIED,
    source_connected: bool = True,
    recommendation_query: str = "affiliate feed dry run",
) -> AffiliateFeedDryRunReport:
    local_rows = _to_local_rows_or_raise(rows)
    batch = adapt_affiliate_feed_rows(
        local_rows,
        source_id=source_id,
        trusted_seller_status_by_name=trusted_seller_status_by_name,
    )
    mapped_candidates = batch.mapped_candidates
    eligibility = run_product_eligibility_gate(
        mapped_candidates,
        expected_vertical=expected_vertical,
        source_trust_level=source_trust_level,
        source_connected=source_connected,
    )
    safe_eligible_candidates = tuple(candidate for candidate in eligibility.eligible_candidates if _safe_for_recommendation(candidate))
    recommendation_ready_count = 0
    if safe_eligible_candidates:
        recommendation = build_pickwise_recommendation_set(
            query=recommendation_query,
            eligible_candidates=safe_eligible_candidates,
        )
        recommendation_ready_count = len(recommendation.display_slots)

    missing_field_counts: dict[str, int] = {
        "missing_image": 0,
        "missing_price": 0,
        "missing_seller_reliability": 0,
        "missing_shipping_info": 0,
        "missing_return_policy": 0,
        "missing_specifications": 0,
        "missing_taxonomy_linkage": 0,
        "missing_affiliate_url": 0,
    }
    locale_counts: dict[str, int] = {}
    market_counts: dict[str, int] = {}
    currency_counts: dict[str, int] = {}
    seller_reliability_counts: dict[str, int] = {}
    for candidate in mapped_candidates:
        metadata = candidate.metadata if isinstance(candidate.metadata, dict) else {}
        enrichment = metadata.get("enrichment") if isinstance(metadata.get("enrichment"), dict) else {}
        locale_market = metadata.get("locale_market") if isinstance(metadata.get("locale_market"), dict) else {}

        seller_reliability = str(enrichment.get("seller_reliability_status", "unknown")).strip().lower() or "unknown"
        locale = str(locale_market.get("locale", "unspecified")).strip() or "unspecified"
        market = str(locale_market.get("market", "unspecified")).strip() or "unspecified"
        currency = str(candidate.currency or "unspecified").strip() or "unspecified"

        _increment(locale_counts, locale)
        _increment(market_counts, market)
        _increment(currency_counts, currency)
        _increment(seller_reliability_counts, seller_reliability)

        if not (candidate.image_url or "").strip():
            _increment(missing_field_counts, "missing_image")
        if candidate.price is None or candidate.price <= 0:
            _increment(missing_field_counts, "missing_price")
        if seller_reliability == "unknown":
            _increment(missing_field_counts, "missing_seller_reliability")
        if enrichment.get("shipping_info_available") is None:
            _increment(missing_field_counts, "missing_shipping_info")
        if enrichment.get("return_policy_available") is None:
            _increment(missing_field_counts, "missing_return_policy")
        if not bool(enrichment.get("has_specifications")):
            _increment(missing_field_counts, "missing_specifications")
        if not bool(enrichment.get("has_taxonomy_linkage")):
            _increment(missing_field_counts, "missing_taxonomy_linkage")
        if not (candidate.affiliate_url or "").strip() and (candidate.outbound_url or "").strip():
            _increment(missing_field_counts, "missing_affiliate_url")

    rejection_reason_counts: dict[str, int] = {}
    review_reason_counts: dict[str, int] = {}
    for row_result in batch.row_results:
        if row_result.status == AffiliateFeedRowStatus.REJECTED:
            for reason in row_result.reason_codes:
                _increment(rejection_reason_counts, reason)
        if row_result.status == AffiliateFeedRowStatus.REVIEW_REQUIRED:
            for reason in row_result.reason_codes:
                _increment(review_reason_counts, reason)

    eligibility_fail_count = len(eligibility.decisions) - len(eligibility.eligible_candidates)
    blockers: list[str] = []
    if batch.status_counts.get(AffiliateFeedRowStatus.REJECTED.value, 0) > 0:
        blockers.append("rejected_rows_present")
    if batch.status_counts.get(AffiliateFeedRowStatus.REVIEW_REQUIRED.value, 0) > 0:
        blockers.append("review_required_rows_present")
    if eligibility_fail_count > 0:
        blockers.append("eligibility_gate_failures_present")
    if recommendation_ready_count < 4:
        blockers.append("insufficient_safe_recommendation_candidates")
    for key in (
        "missing_seller_reliability",
        "missing_shipping_info",
        "missing_return_policy",
        "missing_specifications",
        "missing_taxonomy_linkage",
    ):
        if missing_field_counts.get(key, 0) > 0:
            blockers.append(key)

    blockers_before_3000_candidate_pages = tuple(dict.fromkeys(blockers))
    readiness_status = _derive_readiness_status(
        eligibility_pass_count=len(eligibility.eligible_candidates),
        recommendation_ready_count=recommendation_ready_count,
        blockers_before_3000_candidate_pages=blockers_before_3000_candidate_pages,
    )

    return AffiliateFeedDryRunReport(
        total_rows=len(local_rows),
        mapped_count=batch.status_counts.get(AffiliateFeedRowStatus.MAPPED.value, 0),
        review_required_count=batch.status_counts.get(AffiliateFeedRowStatus.REVIEW_REQUIRED.value, 0),
        rejected_count=batch.status_counts.get(AffiliateFeedRowStatus.REJECTED.value, 0),
        eligibility_pass_count=len(eligibility.eligible_candidates),
        eligibility_fail_count=eligibility_fail_count,
        recommendation_ready_count=recommendation_ready_count,
        missing_field_counts=missing_field_counts,
        rejection_reason_counts=rejection_reason_counts,
        review_reason_counts=review_reason_counts,
        locale_counts=locale_counts,
        market_counts=market_counts,
        currency_counts=currency_counts,
        seller_reliability_counts=seller_reliability_counts,
        readiness_status=readiness_status,
        blockers_before_3000_candidate_pages=blockers_before_3000_candidate_pages,
    )
