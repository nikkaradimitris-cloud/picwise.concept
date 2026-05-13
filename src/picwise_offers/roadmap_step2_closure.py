from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from .affiliate_feed_adapter import AffiliateFeedRowResult, AffiliateFeedRowStatus, adapt_affiliate_feed_rows
from .feed_dry_run import run_affiliate_feed_dry_run
from .feed_enrichment import FeedEnrichmentContracts, build_feed_enrichment_remediation_summary
from .provider_contract import (
    ProviderBatchReadinessResult,
    ProviderBatchThresholds,
    evaluate_provider_batch_readiness,
)

_REQUIRED_FIELD_ORDER = (
    "title",
    "image",
    "price",
    "description",
    "specs",
    "availability",
    "merchant_seller",
    "affiliate_link",
    "category_data",
)

_LOCALE_CURRENCY_MISMATCH_CODES = {
    "locale_market_mismatch",
    "market_currency_mismatch",
    "expected_locale_mismatch",
    "expected_market_mismatch",
    "expected_currency_mismatch",
}

_KNOWN_APPLIED_ENRICHMENTS = {
    "affiliate_url_coverage",
    "return_policy_coverage",
    "shipping_info_coverage",
    "specs_description_coverage",
    "taxonomy_linkage_coverage",
    "trusted_seller_reliability_mapping",
}


@dataclass(frozen=True)
class RoadmapStep2ClosureResult:
    total_rows: int
    field_coverage: dict[str, float]
    rows_missing_each_field: dict[str, tuple[str, ...]]
    adapter_summary: dict[str, Any]
    dry_run_summary: dict[str, Any]
    remediation_summary: dict[str, Any]
    provider_readiness_summary: dict[str, Any]
    step2_closure_status: dict[str, bool]
    can_move_to_step3: bool
    blockers: tuple[str, ...]
    required_provider_fixes: tuple[str, ...]
    evidence_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _to_local_rows_or_raise(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise TypeError("rows must be a local list[dict].")
    materialized: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise TypeError(f"rows[{index}] must be a dict.")
        materialized.append(dict(row))
    return materialized


def _candidate_id_or_row_index(row_result: AffiliateFeedRowResult) -> str:
    if row_result.candidate and row_result.candidate.candidate_id:
        return str(row_result.candidate.candidate_id)
    return f"row_index:{row_result.row_index}"


def _has_non_empty_text(value: Any) -> bool:
    return bool(str(value or "").strip())


def _missing_fields_for_row(row_result: AffiliateFeedRowResult) -> set[str]:
    candidate = row_result.candidate
    if candidate is None:
        return set(_REQUIRED_FIELD_ORDER)

    metadata = candidate.metadata if isinstance(candidate.metadata, dict) else {}
    enrichment = metadata.get("enrichment") if isinstance(metadata.get("enrichment"), dict) else {}

    has_description = _has_non_empty_text(metadata.get("short_description"))
    raw_specs = metadata.get("specifications")
    if isinstance(raw_specs, (list, tuple)):
        has_specs = any(_has_non_empty_text(item) for item in raw_specs)
    else:
        has_specs = _has_non_empty_text(raw_specs)

    has_category_data = any(
        _has_non_empty_text(value)
        for value in (
            candidate.category,
            candidate.category_bucket,
            candidate.google_taxonomy_path,
        )
    ) or bool(enrichment.get("has_taxonomy_linkage"))

    missing: set[str] = set()
    if not _has_non_empty_text(candidate.title):
        missing.add("title")
    if not _has_non_empty_text(candidate.image_url):
        missing.add("image")
    if candidate.price is None or float(candidate.price) <= 0:
        missing.add("price")
    if not has_description:
        missing.add("description")
    if not has_specs:
        missing.add("specs")
    if not _has_non_empty_text(candidate.availability_status):
        missing.add("availability")
    if not _has_non_empty_text(candidate.seller_name):
        missing.add("merchant_seller")
    if not _has_non_empty_text(candidate.affiliate_url):
        missing.add("affiliate_link")
    if not has_category_data:
        missing.add("category_data")
    return missing


def _build_field_proof(
    usable_row_results: tuple[AffiliateFeedRowResult, ...],
) -> tuple[dict[str, float], dict[str, tuple[str, ...]]]:
    total_usable = len(usable_row_results)
    rows_missing_each_field: dict[str, list[str]] = {key: [] for key in _REQUIRED_FIELD_ORDER}
    if total_usable == 0:
        return {key: 0.0 for key in _REQUIRED_FIELD_ORDER}, {key: tuple() for key in _REQUIRED_FIELD_ORDER}

    for row_result in usable_row_results:
        row_identifier = _candidate_id_or_row_index(row_result)
        for missing_field in sorted(_missing_fields_for_row(row_result)):
            rows_missing_each_field[missing_field].append(row_identifier)

    field_coverage: dict[str, float] = {}
    frozen_rows_missing: dict[str, tuple[str, ...]] = {}
    for field_name in _REQUIRED_FIELD_ORDER:
        missing = tuple(sorted(rows_missing_each_field[field_name]))
        frozen_rows_missing[field_name] = missing
        field_coverage[field_name] = (total_usable - len(missing)) / total_usable
    return field_coverage, frozen_rows_missing


def _detect_fabricated_enrichment(remediation_summary: Mapping[str, Any]) -> bool:
    results = remediation_summary.get("results", [])
    if not isinstance(results, list):
        return False
    for result in results:
        if not isinstance(result, Mapping):
            continue
        applied = result.get("applied_enrichments", [])
        if not isinstance(applied, (list, tuple)):
            continue
        for enrichment_name in applied:
            if str(enrichment_name) not in _KNOWN_APPLIED_ENRICHMENTS:
                return True
    return False


def _build_provider_readiness_summary(result: ProviderBatchReadinessResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "passed_thresholds": result.passed_thresholds,
        "failed_thresholds": result.failed_thresholds,
        "blockers": result.blockers,
        "required_provider_improvements": result.required_provider_improvements,
        "allowed_remediation_inputs": result.allowed_remediation_inputs,
        "can_move_to_step3": result.can_move_to_step3,
    }


def _build_dry_run_summary(dry_run_report: Any) -> dict[str, Any]:
    return {
        "total_rows": dry_run_report.total_rows,
        "mapped_count": dry_run_report.mapped_count,
        "review_required_count": dry_run_report.review_required_count,
        "rejected_count": dry_run_report.rejected_count,
        "eligibility_pass_count": dry_run_report.eligibility_pass_count,
        "eligibility_fail_count": dry_run_report.eligibility_fail_count,
        "recommendation_ready_count": dry_run_report.recommendation_ready_count,
        "missing_field_counts": dict(dry_run_report.missing_field_counts),
        "rejection_reason_counts": dict(dry_run_report.rejection_reason_counts),
        "review_reason_counts": dict(dry_run_report.review_reason_counts),
        "readiness_status": dry_run_report.readiness_status,
        "blockers_before_3000_candidate_pages": tuple(dry_run_report.blockers_before_3000_candidate_pages),
    }


def run_roadmap_step2_closure_proof(
    rows: Iterable[Mapping[str, Any]],
    *,
    source_id: str,
    trusted_seller_status_by_name: Mapping[str, str] | None = None,
    enrichment_contracts: FeedEnrichmentContracts | None = None,
    threshold_config: ProviderBatchThresholds | Mapping[str, Any] | None = None,
    strict_field_coverage_threshold: float = 1.0,
    max_review_required_rate: float = 0.0,
) -> RoadmapStep2ClosureResult:
    local_rows = _to_local_rows_or_raise(rows)
    batch = adapt_affiliate_feed_rows(
        local_rows,
        source_id=source_id,
        trusted_seller_status_by_name=trusted_seller_status_by_name,
    )
    usable_row_results = tuple(
        row_result
        for row_result in batch.row_results
        if row_result.status != AffiliateFeedRowStatus.REJECTED and row_result.candidate is not None
    )
    field_coverage, rows_missing_each_field = _build_field_proof(usable_row_results)

    dry_run_report = run_affiliate_feed_dry_run(
        local_rows,
        source_id=source_id,
        trusted_seller_status_by_name=dict(trusted_seller_status_by_name or {}),
        include_enrichment_remediation_summary=True,
        enrichment_contracts=enrichment_contracts,
    )
    remediation_summary = build_feed_enrichment_remediation_summary(
        batch.mapped_candidates,
        contracts=enrichment_contracts,
    )

    fabricated_enrichment_detected = _detect_fabricated_enrichment(remediation_summary)
    locale_currency_mismatch_count = 0
    remediation_results = remediation_summary.get("results", [])
    if isinstance(remediation_results, list):
        for result in remediation_results:
            if not isinstance(result, Mapping):
                continue
            review_reasons = result.get("review_reasons", [])
            if not isinstance(review_reasons, (list, tuple)):
                continue
            locale_currency_mismatch_count += sum(
                1 for review_reason in review_reasons if str(review_reason) in _LOCALE_CURRENCY_MISMATCH_CODES
            )

    total_rows = len(local_rows)
    rejected_count = batch.status_counts.get(AffiliateFeedRowStatus.REJECTED.value, 0)
    review_required_count = batch.status_counts.get(AffiliateFeedRowStatus.REVIEW_REQUIRED.value, 0)
    review_required_rate = (review_required_count / total_rows) if total_rows else 0.0

    provided_thresholds = dict(threshold_config) if isinstance(threshold_config, Mapping) else {}
    readiness_thresholds = ProviderBatchThresholds(
        max_rejected_rate=float(provided_thresholds.get("max_rejected_rate", 0.0)),
        max_review_required_rate=float(provided_thresholds.get("max_review_required_rate", max_review_required_rate)),
        min_seller_trust_coverage=float(provided_thresholds.get("min_seller_trust_coverage", 1.0)),
        min_image_coverage=float(provided_thresholds.get("min_image_coverage", strict_field_coverage_threshold)),
        min_price_currency_coverage=float(
            provided_thresholds.get("min_price_currency_coverage", strict_field_coverage_threshold)
        ),
        min_affiliate_url_coverage_when_monetized=float(
            provided_thresholds.get(
                "min_affiliate_url_coverage_when_monetized",
                strict_field_coverage_threshold,
            )
        ),
        min_shipping_info_coverage=float(provided_thresholds.get("min_shipping_info_coverage", 1.0)),
        min_return_policy_coverage=float(provided_thresholds.get("min_return_policy_coverage", 1.0)),
        min_specs_or_description_coverage=float(provided_thresholds.get("min_specs_or_description_coverage", 1.0)),
        max_locale_currency_mismatch_rate=float(provided_thresholds.get("max_locale_currency_mismatch_rate", 0.0)),
        require_no_fabricated_enrichment=bool(provided_thresholds.get("require_no_fabricated_enrichment", True)),
        require_no_public_route_or_sitemap_changes=bool(
            provided_thresholds.get("require_no_public_route_or_sitemap_changes", True)
        ),
        require_no_live_api_scraping_or_credentials=bool(
            provided_thresholds.get("require_no_live_api_scraping_or_credentials", True)
        ),
        monetization_expected=bool(provided_thresholds.get("monetization_expected", True)),
    )

    provider_payload = {
        "total_rows": dry_run_report.total_rows,
        "mapped_count": dry_run_report.mapped_count,
        "review_required_count": dry_run_report.review_required_count,
        "rejected_count": dry_run_report.rejected_count,
        "missing_field_counts": dict(dry_run_report.missing_field_counts),
        "review_reason_counts": dict(dry_run_report.review_reason_counts),
        "enrichment_remediation_summary": remediation_summary,
        "public_routes_unchanged": True,
        "sitemap_unchanged": True,
        "no_live_api_calls": True,
        "no_scraping": True,
        "no_credentials_added": True,
        "fabricated_enrichment_detected": fabricated_enrichment_detected,
    }
    provider_readiness = evaluate_provider_batch_readiness(
        provider_payload,
        remediation_summary=remediation_summary,
        threshold_config=readiness_thresholds,
    )

    field_blockers = tuple(
        f"{field_name}_coverage_below_threshold"
        for field_name in _REQUIRED_FIELD_ORDER
        if field_coverage.get(field_name, 0.0) < strict_field_coverage_threshold
    )

    blockers: list[str] = list(field_blockers)
    if rejected_count > 0:
        blockers.append("rejected_rows_present")
    if review_required_rate > max_review_required_rate:
        blockers.append("review_required_rate_above_threshold")
    if locale_currency_mismatch_count > 0:
        blockers.append("locale_currency_mismatch_detected")
    if fabricated_enrichment_detected:
        blockers.append("fabricated_enrichment_detected")
    blockers.extend(provider_readiness.blockers)
    unique_blockers = tuple(dict.fromkeys(sorted(blockers)))

    required_provider_fixes: list[str] = []
    for field_name in _REQUIRED_FIELD_ORDER:
        if rows_missing_each_field.get(field_name):
            required_provider_fixes.append(f"provide_missing_{field_name}")
    if rejected_count > 0:
        required_provider_fixes.append("remove_or_fix_rejected_rows")
    if review_required_rate > max_review_required_rate:
        required_provider_fixes.append("reduce_review_required_rows")
    required_provider_fixes.extend(provider_readiness.required_provider_improvements)
    unique_fixes = tuple(dict.fromkeys(sorted(required_provider_fixes)))

    all_fields_pass = all(
        field_coverage.get(field_name, 0.0) >= strict_field_coverage_threshold for field_name in _REQUIRED_FIELD_ORDER
    )
    step2_closed = (
        all_fields_pass
        and rejected_count == 0
        and review_required_rate <= max_review_required_rate
        and provider_readiness.status == "step2_ready"
        and provider_readiness.can_move_to_step3
        and not fabricated_enrichment_detected
        and len(unique_blockers) == 0
    )

    step2_status = {
        "step2_closed": step2_closed,
        "step2_not_ready": not step2_closed,
    }

    adapter_summary = {
        "total_rows": len(batch.row_results),
        "status_counts": dict(sorted(batch.status_counts.items())),
        "mapped_candidate_ids": tuple(
            sorted(candidate.candidate_id for candidate in batch.mapped_candidates if candidate.candidate_id)
        ),
    }
    dry_run_summary = _build_dry_run_summary(dry_run_report)
    provider_readiness_summary = _build_provider_readiness_summary(provider_readiness)
    evidence_summary = {
        "required_field_names": _REQUIRED_FIELD_ORDER,
        "strict_field_coverage_threshold": strict_field_coverage_threshold,
        "review_required_rate": review_required_rate,
        "max_review_required_rate": max_review_required_rate,
        "rejected_count": rejected_count,
        "locale_currency_mismatch_count": locale_currency_mismatch_count,
        "provider_readiness_status": provider_readiness.status,
        "no_public_routes_or_sitemap_changes": True,
        "no_live_api_scraping_credentials": True,
        "no_fabricated_enrichment_detected": not fabricated_enrichment_detected,
    }

    return RoadmapStep2ClosureResult(
        total_rows=total_rows,
        field_coverage=field_coverage,
        rows_missing_each_field=rows_missing_each_field,
        adapter_summary=adapter_summary,
        dry_run_summary=dry_run_summary,
        remediation_summary=remediation_summary,
        provider_readiness_summary=provider_readiness_summary,
        step2_closure_status=step2_status,
        can_move_to_step3=step2_closed and provider_readiness.can_move_to_step3,
        blockers=unique_blockers,
        required_provider_fixes=unique_fixes,
        evidence_summary=evidence_summary,
    )
