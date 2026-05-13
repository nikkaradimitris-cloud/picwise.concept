from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .feed_dry_run import AffiliateFeedDryRunReport


@dataclass(frozen=True)
class ProviderFeedContract:
    required_core: tuple[str, ...]
    required_for_public_candidate: tuple[str, ...]
    enrichment_allowed_from_trusted_map: tuple[str, ...]
    optional: tuple[str, ...]
    forbidden_to_fabricate: tuple[str, ...]


@dataclass(frozen=True)
class ProviderBatchThresholds:
    max_rejected_rate: float = 0.0
    max_review_required_rate: float = 0.05
    min_seller_trust_coverage: float = 1.0
    min_image_coverage: float = 1.0
    min_price_currency_coverage: float = 1.0
    min_affiliate_url_coverage_when_monetized: float = 1.0
    min_shipping_info_coverage: float = 1.0
    min_return_policy_coverage: float = 1.0
    min_specs_or_description_coverage: float = 1.0
    max_locale_currency_mismatch_rate: float = 0.0
    require_no_fabricated_enrichment: bool = True
    require_no_public_route_or_sitemap_changes: bool = True
    require_no_live_api_scraping_or_credentials: bool = True
    monetization_expected: bool = True


@dataclass(frozen=True)
class ProviderBatchReadinessResult:
    status: str
    passed_thresholds: tuple[str, ...]
    failed_thresholds: tuple[str, ...]
    blockers: tuple[str, ...]
    required_provider_improvements: tuple[str, ...]
    allowed_remediation_inputs: tuple[str, ...]
    can_move_to_step3: bool


PROVIDER_FEED_CONTRACT = ProviderFeedContract(
    required_core=(
        "product_id_or_deterministic_external_id",
        "title",
        "product_url_or_outbound_url",
        "image_url",
        "price",
        "currency",
        "availability",
        "merchant_or_seller",
        "category_or_taxonomy_signal",
        "locale_or_market_signal_when_available",
    ),
    required_for_public_candidate=(
        "affiliate_url_when_monetized",
        "seller_reliability_status_from_trusted_mapping",
        "shipping_information",
        "return_policy_information",
        "specifications_or_useful_description",
        "category_or_taxonomy_linkage",
        "locale_market_currency_consistency",
    ),
    enrichment_allowed_from_trusted_map=(
        "trusted_seller_reliability_by_name",
        "shipping_info_available_by_candidate_id",
        "return_policy_available_by_candidate_id",
        "taxonomy_linkage_by_candidate_id",
        "specs_or_description_by_candidate_id",
        "affiliate_url_by_candidate_id",
        "locale_market_currency_by_candidate_id",
        "expected_currency_by_market",
    ),
    optional=(
        "brand",
        "model",
        "gtin_ean_mpn",
        "rating_reviews_when_provider_supplied",
        "sale_price_when_provider_supplied",
    ),
    forbidden_to_fabricate=(
        "seller_reliability_status",
        "shipping_information",
        "return_policy_information",
        "taxonomy_linkage",
        "specifications_or_description",
        "affiliate_url",
        "title",
        "price",
        "currency",
        "availability",
        "merchant_or_seller",
        "rating_reviews",
        "sale_price",
        "locale_market_currency_consistency",
    ),
)

ALLOWED_REMEDIATION_INPUTS = PROVIDER_FEED_CONTRACT.enrichment_allowed_from_trusted_map

_MISSING_FIELD_THRESHOLD_RULES = {
    "missing_image": ("image_coverage", "improve_image_coverage"),
    "missing_price": ("price_currency_coverage", "improve_price_coverage"),
    "missing_seller_reliability": ("seller_trust_coverage", "provide_trusted_seller_mapping"),
    "missing_shipping_info": ("shipping_info_coverage", "provide_shipping_info"),
    "missing_return_policy": ("return_policy_coverage", "provide_return_policy"),
    "missing_specifications": ("specs_description_coverage", "provide_specs_or_description"),
    "missing_affiliate_url": ("affiliate_url_coverage", "provide_affiliate_urls"),
}


def _to_report_payload(report: AffiliateFeedDryRunReport | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(report, AffiliateFeedDryRunReport):
        return {
            "total_rows": report.total_rows,
            "mapped_count": report.mapped_count,
            "review_required_count": report.review_required_count,
            "rejected_count": report.rejected_count,
            "missing_field_counts": dict(report.missing_field_counts),
            "review_reason_counts": dict(report.review_reason_counts),
            "blockers_before_3000_candidate_pages": tuple(report.blockers_before_3000_candidate_pages),
            "enrichment_remediation_summary": report.enrichment_remediation_summary,
        }
    return dict(report)


def _resolve_thresholds(
    threshold_config: ProviderBatchThresholds | Mapping[str, Any] | None,
) -> ProviderBatchThresholds:
    if threshold_config is None:
        return ProviderBatchThresholds()
    if isinstance(threshold_config, ProviderBatchThresholds):
        return threshold_config
    payload = dict(threshold_config)
    return ProviderBatchThresholds(
        max_rejected_rate=float(payload.get("max_rejected_rate", 0.0)),
        max_review_required_rate=float(payload.get("max_review_required_rate", 0.05)),
        min_seller_trust_coverage=float(payload.get("min_seller_trust_coverage", 1.0)),
        min_image_coverage=float(payload.get("min_image_coverage", 1.0)),
        min_price_currency_coverage=float(payload.get("min_price_currency_coverage", 1.0)),
        min_affiliate_url_coverage_when_monetized=float(
            payload.get("min_affiliate_url_coverage_when_monetized", 1.0)
        ),
        min_shipping_info_coverage=float(payload.get("min_shipping_info_coverage", 1.0)),
        min_return_policy_coverage=float(payload.get("min_return_policy_coverage", 1.0)),
        min_specs_or_description_coverage=float(payload.get("min_specs_or_description_coverage", 1.0)),
        max_locale_currency_mismatch_rate=float(payload.get("max_locale_currency_mismatch_rate", 0.0)),
        require_no_fabricated_enrichment=bool(payload.get("require_no_fabricated_enrichment", True)),
        require_no_public_route_or_sitemap_changes=bool(
            payload.get("require_no_public_route_or_sitemap_changes", True)
        ),
        require_no_live_api_scraping_or_credentials=bool(
            payload.get("require_no_live_api_scraping_or_credentials", True)
        ),
        monetization_expected=bool(payload.get("monetization_expected", True)),
    )


def _safe_rate(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _bool_flag(payload: Mapping[str, Any], key: str, default: bool = True) -> bool:
    value = payload.get(key, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _extract_unresolved_missing_from_remediation(summary: Mapping[str, Any]) -> dict[str, int]:
    unresolved = {
        "missing_seller_reliability": 0,
        "missing_shipping_info": 0,
        "missing_return_policy": 0,
        "missing_specifications": 0,
        "missing_affiliate_url": 0,
    }
    results = summary.get("results", [])
    if not isinstance(results, list):
        return unresolved

    missing_field_mapping = {
        "seller_reliability_status": "missing_seller_reliability",
        "shipping_info_available": "missing_shipping_info",
        "return_policy_available": "missing_return_policy",
        "specifications_or_description": "missing_specifications",
        "affiliate_url": "missing_affiliate_url",
    }
    for result in results:
        if not isinstance(result, Mapping):
            continue
        fields = result.get("missing_fields", [])
        if not isinstance(fields, (list, tuple)):
            continue
        for field in fields:
            normalized = missing_field_mapping.get(str(field))
            if normalized:
                unresolved[normalized] += 1
    return unresolved


def evaluate_provider_batch_readiness(
    dry_run_report: AffiliateFeedDryRunReport | Mapping[str, Any],
    remediation_summary: Mapping[str, Any] | None = None,
    threshold_config: ProviderBatchThresholds | Mapping[str, Any] | None = None,
) -> ProviderBatchReadinessResult:
    report = _to_report_payload(dry_run_report)
    thresholds = _resolve_thresholds(threshold_config)

    total_rows = int(report.get("total_rows", 0) or 0)
    mapped_count = int(report.get("mapped_count", 0) or 0)
    review_required_count = int(report.get("review_required_count", 0) or 0)
    rejected_count = int(report.get("rejected_count", 0) or 0)
    missing_field_counts = dict(report.get("missing_field_counts", {}) or {})
    review_reason_counts = dict(report.get("review_reason_counts", {}) or {})
    inherited_remediation_summary = report.get("enrichment_remediation_summary")
    resolved_remediation_summary = remediation_summary or (
        inherited_remediation_summary if isinstance(inherited_remediation_summary, Mapping) else None
    )

    unresolved_by_field = dict(missing_field_counts)
    if isinstance(resolved_remediation_summary, Mapping):
        unresolved_from_remediation = _extract_unresolved_missing_from_remediation(resolved_remediation_summary)
        for key, unresolved_count in unresolved_from_remediation.items():
            unresolved_by_field[key] = unresolved_count

    mapped_denom = mapped_count if mapped_count > 0 else max(total_rows - rejected_count, 1)
    total_denom = max(total_rows, 1)
    rejected_rate = _safe_rate(rejected_count, total_denom)
    review_required_rate = _safe_rate(review_required_count, total_denom)

    seller_trust_coverage = 1.0 - _safe_rate(float(unresolved_by_field.get("missing_seller_reliability", 0)), mapped_denom)
    image_coverage = 1.0 - _safe_rate(float(unresolved_by_field.get("missing_image", 0)), mapped_denom)
    price_currency_coverage = 1.0 - _safe_rate(float(unresolved_by_field.get("missing_price", 0)), mapped_denom)
    affiliate_coverage = 1.0 - _safe_rate(float(unresolved_by_field.get("missing_affiliate_url", 0)), mapped_denom)
    shipping_coverage = 1.0 - _safe_rate(float(unresolved_by_field.get("missing_shipping_info", 0)), mapped_denom)
    return_policy_coverage = 1.0 - _safe_rate(float(unresolved_by_field.get("missing_return_policy", 0)), mapped_denom)
    specs_description_coverage = 1.0 - _safe_rate(float(unresolved_by_field.get("missing_specifications", 0)), mapped_denom)

    mismatch_keys = (
        "locale_market_mismatch",
        "market_currency_mismatch",
        "expected_locale_mismatch",
        "expected_market_mismatch",
        "expected_currency_mismatch",
    )
    mismatch_count = sum(int(review_reason_counts.get(key, 0) or 0) for key in mismatch_keys)
    if isinstance(resolved_remediation_summary, Mapping):
        results = resolved_remediation_summary.get("results", [])
        if isinstance(results, list):
            mismatch_count = 0
            for result in results:
                if not isinstance(result, Mapping):
                    continue
                reasons = result.get("review_reasons", [])
                if not isinstance(reasons, (list, tuple)):
                    continue
                mismatch_count += sum(1 for reason in reasons if str(reason) in mismatch_keys)
    locale_currency_mismatch_rate = _safe_rate(mismatch_count, mapped_denom)

    passed_thresholds: list[str] = []
    failed_thresholds: list[str] = []
    blockers: list[str] = []
    improvements: list[str] = []

    threshold_checks: list[tuple[str, bool, str | None, str | None]] = [
        (
            "rejected_rate",
            rejected_rate <= thresholds.max_rejected_rate,
            "rejected_rows_present" if rejected_rate > thresholds.max_rejected_rate else None,
            "remove_rejected_rows_and_fix_core_contract_violations",
        ),
        (
            "review_required_rate",
            review_required_rate <= thresholds.max_review_required_rate,
            "review_required_rate_above_threshold" if review_required_rate > thresholds.max_review_required_rate else None,
            "reduce_review_required_rows_via_provider_fixes_or_trusted_maps",
        ),
        (
            "seller_trust_coverage",
            seller_trust_coverage >= thresholds.min_seller_trust_coverage,
            "seller_trust_coverage_below_threshold" if seller_trust_coverage < thresholds.min_seller_trust_coverage else None,
            "expand_trusted_seller_mapping_and_provider_trust_metadata",
        ),
        (
            "image_coverage",
            image_coverage >= thresholds.min_image_coverage,
            "image_coverage_below_threshold" if image_coverage < thresholds.min_image_coverage else None,
            "ensure_provider_supplies_image_url_for_all_rows",
        ),
        (
            "price_currency_coverage",
            price_currency_coverage >= thresholds.min_price_currency_coverage,
            "price_currency_coverage_below_threshold"
            if price_currency_coverage < thresholds.min_price_currency_coverage
            else None,
            "ensure_provider_supplies_price_and_currency_for_all_rows",
        ),
        (
            "shipping_info_coverage",
            shipping_coverage >= thresholds.min_shipping_info_coverage,
            "shipping_info_coverage_below_threshold" if shipping_coverage < thresholds.min_shipping_info_coverage else None,
            "provide_shipping_information_for_all_candidate_rows",
        ),
        (
            "return_policy_coverage",
            return_policy_coverage >= thresholds.min_return_policy_coverage,
            "return_policy_coverage_below_threshold"
            if return_policy_coverage < thresholds.min_return_policy_coverage
            else None,
            "provide_return_policy_information_for_all_candidate_rows",
        ),
        (
            "specs_description_coverage",
            specs_description_coverage >= thresholds.min_specs_or_description_coverage,
            "specs_description_coverage_below_threshold"
            if specs_description_coverage < thresholds.min_specs_or_description_coverage
            else None,
            "provide_specifications_or_useful_descriptions_for_all_candidate_rows",
        ),
        (
            "locale_currency_mismatch_rate",
            locale_currency_mismatch_rate <= thresholds.max_locale_currency_mismatch_rate,
            "locale_currency_mismatch_detected"
            if locale_currency_mismatch_rate > thresholds.max_locale_currency_mismatch_rate
            else None,
            "align_locale_market_currency_or_keep_mismatches_blocked",
        ),
    ]

    if thresholds.monetization_expected:
        threshold_checks.append(
            (
                "affiliate_url_coverage",
                affiliate_coverage >= thresholds.min_affiliate_url_coverage_when_monetized,
                "affiliate_url_coverage_below_threshold"
                if affiliate_coverage < thresholds.min_affiliate_url_coverage_when_monetized
                else None,
                "supply_affiliate_url_for_all_monetized_rows",
            )
        )

    for threshold_name, passed, blocker_code, improvement in threshold_checks:
        if passed:
            passed_thresholds.append(threshold_name)
        else:
            failed_thresholds.append(threshold_name)
            if blocker_code:
                blockers.append(blocker_code)
            improvements.append(improvement)

    if thresholds.require_no_fabricated_enrichment:
        fabricated_enrichment_detected = _bool_flag(report, "fabricated_enrichment_detected", default=False)
        if fabricated_enrichment_detected:
            failed_thresholds.append("no_fabricated_enrichment")
            blockers.append("fabricated_enrichment_detected")
            improvements.append("remove_fabricated_enrichment_and_use_trusted_maps_only")
        else:
            passed_thresholds.append("no_fabricated_enrichment")

    if thresholds.require_no_public_route_or_sitemap_changes:
        public_routes_unchanged = _bool_flag(report, "public_routes_unchanged", default=True)
        sitemap_unchanged = _bool_flag(report, "sitemap_unchanged", default=True)
        if public_routes_unchanged and sitemap_unchanged:
            passed_thresholds.append("no_public_route_or_sitemap_changes")
        else:
            failed_thresholds.append("no_public_route_or_sitemap_changes")
            blockers.append("public_route_or_sitemap_changes_detected")
            improvements.append("revert_public_route_or_sitemap_changes")

    if thresholds.require_no_live_api_scraping_or_credentials:
        no_live_api_calls = _bool_flag(report, "no_live_api_calls", default=True)
        no_scraping = _bool_flag(report, "no_scraping", default=True)
        no_credentials_added = _bool_flag(report, "no_credentials_added", default=True)
        if no_live_api_calls and no_scraping and no_credentials_added:
            passed_thresholds.append("no_live_api_scraping_or_credentials")
        else:
            failed_thresholds.append("no_live_api_scraping_or_credentials")
            blockers.append("live_api_scraping_or_credentials_violation")
            improvements.append("remove_live_api_calls_scraping_and_credentials")

    for missing_key, (_, improvement_code) in _MISSING_FIELD_THRESHOLD_RULES.items():
        if int(unresolved_by_field.get(missing_key, 0) or 0) > 0:
            improvements.append(improvement_code)

    status: str
    unique_blockers = tuple(dict.fromkeys(blockers))
    unique_failed = tuple(dict.fromkeys(failed_thresholds))
    unique_passed = tuple(dict.fromkeys(passed_thresholds))
    unique_improvements = tuple(dict.fromkeys(improvements))

    if not unique_failed:
        status = "step2_ready"
    elif "rejected_rate" in unique_failed or "locale_currency_mismatch_rate" in unique_failed:
        status = "step2_not_ready"
    else:
        status = "step2_conditionally_ready"

    return ProviderBatchReadinessResult(
        status=status,
        passed_thresholds=unique_passed,
        failed_thresholds=unique_failed,
        blockers=unique_blockers,
        required_provider_improvements=unique_improvements,
        allowed_remediation_inputs=ALLOWED_REMEDIATION_INPUTS,
        can_move_to_step3=status == "step2_ready",
    )


def describe_provider_contract() -> dict[str, Any]:
    return asdict(PROVIDER_FEED_CONTRACT)
