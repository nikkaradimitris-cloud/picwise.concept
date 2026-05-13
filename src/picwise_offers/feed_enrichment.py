from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping
import re

from .contracts import OfferCandidate

_HTTP_URL_REGEX = re.compile(r"^https?://[a-z0-9.-]+\.[a-z]{2,}(?:[/?#].*)?$", flags=re.IGNORECASE)
_SELLER_RELIABILITY_ALLOWED = {"trusted", "acceptable", "unknown", "unreliable", "blocked"}


@dataclass(frozen=True)
class FeedEnrichmentContracts:
    trusted_seller_reliability_by_name: Mapping[str, str] | None = None
    shipping_info_available_by_candidate_id: Mapping[str, bool] | None = None
    return_policy_available_by_candidate_id: Mapping[str, bool] | None = None
    taxonomy_linkage_by_candidate_id: Mapping[str, str | bool] | None = None
    specs_or_description_by_candidate_id: Mapping[str, Any] | None = None
    affiliate_url_by_candidate_id: Mapping[str, str] | None = None
    locale_market_currency_by_candidate_id: Mapping[str, Mapping[str, str]] | None = None
    expected_currency_by_market: Mapping[str, str] | None = None


@dataclass(frozen=True)
class FeedEnrichmentRemediationResult:
    candidate_id: str
    status: str
    actions: tuple[str, ...]
    missing_fields: tuple[str, ...]
    applied_enrichments: tuple[str, ...]
    review_reasons: tuple[str, ...]
    blocker_reasons: tuple[str, ...]
    can_continue_to_candidate_page_dry_run: bool


def _normalize_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "yes", "y", "available"}:
        return True
    if lowered in {"0", "false", "no", "n", "none", "not_available"}:
        return False
    return None


def _is_valid_http_url(value: str | None) -> bool:
    if not value:
        return False
    return bool(_HTTP_URL_REGEX.match(value.strip()))


def _canonical_seller_reliability(value: str | None) -> str:
    normalized = str(value or "").strip().lower().replace(" ", "_")
    mapping = {
        "trusted": "trusted",
        "acceptable": "acceptable",
        "partner_verified": "acceptable",
        "unknown": "unknown",
        "unreliable": "unreliable",
        "blocked": "blocked",
    }
    return mapping.get(normalized, "unknown")


def _extract_locale_market(candidate: OfferCandidate) -> tuple[str | None, str | None]:
    metadata = candidate.metadata if isinstance(candidate.metadata, dict) else {}
    locale_market = metadata.get("locale_market") if isinstance(metadata.get("locale_market"), dict) else {}
    locale = str(locale_market.get("locale", "")).strip() or None
    market = str(locale_market.get("market", "")).strip() or None
    return locale, market


def _extract_enrichment(candidate: OfferCandidate) -> dict[str, Any]:
    metadata = candidate.metadata if isinstance(candidate.metadata, dict) else {}
    return metadata.get("enrichment") if isinstance(metadata.get("enrichment"), dict) else {}


def _resolve_seller_trust_from_contracts(candidate: OfferCandidate, contracts: FeedEnrichmentContracts) -> str | None:
    if not contracts.trusted_seller_reliability_by_name:
        return None
    seller_name = str(candidate.seller_name or "").strip()
    if not seller_name:
        return None
    for mapped_name, mapped_status in contracts.trusted_seller_reliability_by_name.items():
        if str(mapped_name).strip().lower() == seller_name.lower():
            canonical = _canonical_seller_reliability(mapped_status)
            return canonical if canonical in _SELLER_RELIABILITY_ALLOWED else "unknown"
    return None


def _resolve_specs_or_description(value: Any) -> tuple[bool, bool]:
    if value is None:
        return False, False
    if isinstance(value, str):
        return bool(value.strip()), False
    if isinstance(value, (list, tuple)):
        has_specs = any(str(item).strip() for item in value)
        return False, has_specs
    if isinstance(value, Mapping):
        description = str(value.get("short_description", "")).strip()
        specs = value.get("specifications")
        if isinstance(specs, (list, tuple)):
            has_specs = any(str(item).strip() for item in specs)
        else:
            has_specs = bool(str(specs or "").strip())
        return bool(description), has_specs
    return False, False


def _resolve_locale_consistency_reasons(
    *,
    candidate: OfferCandidate,
    contracts: FeedEnrichmentContracts,
) -> tuple[str, ...]:
    reasons: list[str] = []
    locale, market = _extract_locale_market(candidate)
    currency = str(candidate.currency or "").strip().upper() or None

    if locale and market:
        locale_upper = locale.upper()
        market_upper = market.upper()
        if "-" in locale_upper and not locale_upper.endswith(f"-{market_upper}"):
            reasons.append("locale_market_mismatch")

    if contracts.expected_currency_by_market and market and currency:
        for mapped_market, mapped_currency in contracts.expected_currency_by_market.items():
            if str(mapped_market).strip().upper() == market.upper():
                expected = str(mapped_currency).strip().upper()
                if expected and currency != expected:
                    reasons.append("market_currency_mismatch")

    if contracts.locale_market_currency_by_candidate_id:
        expected = contracts.locale_market_currency_by_candidate_id.get(candidate.candidate_id)
        if isinstance(expected, Mapping):
            expected_locale = str(expected.get("locale", "")).strip()
            expected_market = str(expected.get("market", "")).strip()
            expected_currency = str(expected.get("currency", "")).strip().upper()
            if expected_locale and locale and expected_locale.lower() != locale.lower():
                reasons.append("expected_locale_mismatch")
            if expected_market and market and expected_market.upper() != market.upper():
                reasons.append("expected_market_mismatch")
            if expected_currency and currency and expected_currency != currency:
                reasons.append("expected_currency_mismatch")

    return tuple(dict.fromkeys(reasons))


def _to_local_candidates_or_raise(candidates: Iterable[OfferCandidate]) -> tuple[OfferCandidate, ...]:
    if isinstance(candidates, tuple):
        materialized = candidates
    elif isinstance(candidates, list):
        materialized = tuple(candidates)
    else:
        raise TypeError("candidates must be a local list[OfferCandidate] or tuple[OfferCandidate, ...].")

    for index, candidate in enumerate(materialized):
        if not isinstance(candidate, OfferCandidate):
            raise TypeError(f"candidates[{index}] must be an OfferCandidate.")
    return materialized


def remediate_feed_enrichment_candidates(
    candidates: Iterable[OfferCandidate],
    *,
    contracts: FeedEnrichmentContracts | None = None,
) -> tuple[FeedEnrichmentRemediationResult, ...]:
    local_candidates = _to_local_candidates_or_raise(candidates)
    resolved_contracts = contracts or FeedEnrichmentContracts()
    results: list[FeedEnrichmentRemediationResult] = []

    for candidate in local_candidates:
        enrichment = _extract_enrichment(candidate)
        missing_fields: list[str] = []
        applied_enrichments: list[str] = []
        review_reasons: list[str] = []
        blocker_reasons: list[str] = []
        actions: list[str] = []

        candidate_id = str(candidate.candidate_id or "").strip()
        title = str(candidate.title or "").strip()
        seller_name = str(candidate.seller_name or "").strip()
        outbound_url = str(candidate.outbound_url or "").strip()

        if not candidate_id:
            missing_fields.append("candidate_id")
        if not title:
            missing_fields.append("title")
        if not seller_name:
            missing_fields.append("seller_name")
        if outbound_url and not _is_valid_http_url(outbound_url):
            blocker_reasons.append("invalid_outbound_url")

        seller_reliability = _canonical_seller_reliability(enrichment.get("seller_reliability_status"))
        mapped_reliability = _resolve_seller_trust_from_contracts(candidate, resolved_contracts)
        if mapped_reliability is not None:
            seller_reliability = mapped_reliability
            applied_enrichments.append("trusted_seller_reliability_mapping")
        if seller_reliability in {"unknown"}:
            actions.append("needs_seller_trust")
            missing_fields.append("seller_reliability_status")
        if seller_reliability in {"blocked", "unreliable"}:
            actions.append("manual_review_required")
            review_reasons.append("seller_reliability_requires_manual_review")

        shipping_available = _normalize_bool(enrichment.get("shipping_info_available"))
        if resolved_contracts.shipping_info_available_by_candidate_id and candidate_id in resolved_contracts.shipping_info_available_by_candidate_id:
            shipping_available = _normalize_bool(resolved_contracts.shipping_info_available_by_candidate_id.get(candidate_id))
            applied_enrichments.append("shipping_info_coverage")
        if shipping_available is not True:
            actions.append("needs_shipping_info")
            missing_fields.append("shipping_info_available")

        return_policy_available = _normalize_bool(enrichment.get("return_policy_available"))
        if resolved_contracts.return_policy_available_by_candidate_id and candidate_id in resolved_contracts.return_policy_available_by_candidate_id:
            return_policy_available = _normalize_bool(resolved_contracts.return_policy_available_by_candidate_id.get(candidate_id))
            applied_enrichments.append("return_policy_coverage")
        if return_policy_available is not True:
            actions.append("needs_return_policy")
            missing_fields.append("return_policy_available")

        has_taxonomy_linkage = bool(enrichment.get("has_taxonomy_linkage") or candidate.category_bucket or candidate.google_taxonomy_path or candidate.category)
        if resolved_contracts.taxonomy_linkage_by_candidate_id and candidate_id in resolved_contracts.taxonomy_linkage_by_candidate_id:
            mapped_taxonomy = resolved_contracts.taxonomy_linkage_by_candidate_id.get(candidate_id)
            has_taxonomy_linkage = bool(str(mapped_taxonomy).strip()) if not isinstance(mapped_taxonomy, bool) else mapped_taxonomy
            applied_enrichments.append("taxonomy_linkage_coverage")
        if not has_taxonomy_linkage:
            actions.append("needs_taxonomy_linkage")
            missing_fields.append("taxonomy_linkage")

        has_description = bool(enrichment.get("has_short_description")) or bool(str((candidate.metadata or {}).get("short_description", "")).strip())
        has_specs = bool(enrichment.get("has_specifications")) or bool((candidate.metadata or {}).get("specifications"))
        if resolved_contracts.specs_or_description_by_candidate_id and candidate_id in resolved_contracts.specs_or_description_by_candidate_id:
            mapped_description, mapped_specs = _resolve_specs_or_description(
                resolved_contracts.specs_or_description_by_candidate_id.get(candidate_id)
            )
            has_description = has_description or mapped_description
            has_specs = has_specs or mapped_specs
            applied_enrichments.append("specs_description_coverage")
        if not (has_description or has_specs):
            actions.append("needs_specs_or_description")
            missing_fields.append("specifications_or_description")

        affiliate_url = str(candidate.affiliate_url or "").strip()
        if not affiliate_url and resolved_contracts.affiliate_url_by_candidate_id and candidate_id in resolved_contracts.affiliate_url_by_candidate_id:
            mapped_affiliate_url = str(resolved_contracts.affiliate_url_by_candidate_id.get(candidate_id) or "").strip()
            if _is_valid_http_url(mapped_affiliate_url):
                affiliate_url = mapped_affiliate_url
                applied_enrichments.append("affiliate_url_coverage")
        if not affiliate_url:
            actions.append("needs_affiliate_url")
            missing_fields.append("affiliate_url")

        locale_reasons = _resolve_locale_consistency_reasons(candidate=candidate, contracts=resolved_contracts)
        if locale_reasons:
            actions.append("needs_locale_review")
            review_reasons.extend(locale_reasons)

        if missing_fields or blocker_reasons:
            actions.append("blocked_invalid_core_fields")
            if missing_fields:
                blocker_reasons.append("missing_core_fields")

        deduped_actions = tuple(sorted(dict.fromkeys(actions)))
        deduped_missing_fields = tuple(sorted(dict.fromkeys(missing_fields)))
        deduped_applied = tuple(sorted(dict.fromkeys(applied_enrichments)))
        deduped_reviews = tuple(sorted(dict.fromkeys(review_reasons)))
        deduped_blockers = tuple(sorted(dict.fromkeys(blocker_reasons)))

        if "blocked_invalid_core_fields" in deduped_actions:
            status = "blocked"
        elif deduped_actions:
            status = "needs_remediation"
        else:
            status = "ready"
            deduped_actions = ("ready",)

        can_continue = status == "ready"
        if can_continue and "ready" not in deduped_actions:
            deduped_actions = tuple(sorted(dict.fromkeys((*deduped_actions, "ready"))))

        results.append(
            FeedEnrichmentRemediationResult(
                candidate_id=candidate_id,
                status=status,
                actions=deduped_actions,
                missing_fields=deduped_missing_fields,
                applied_enrichments=deduped_applied,
                review_reasons=deduped_reviews,
                blocker_reasons=deduped_blockers,
                can_continue_to_candidate_page_dry_run=can_continue,
            )
        )

    return tuple(results)


def build_feed_enrichment_remediation_summary(
    candidates: Iterable[OfferCandidate],
    *,
    contracts: FeedEnrichmentContracts | None = None,
) -> dict[str, Any]:
    results = remediate_feed_enrichment_candidates(candidates, contracts=contracts)
    status_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    for result in results:
        status_counts[result.status] = status_counts.get(result.status, 0) + 1
        for action in result.actions:
            action_counts[action] = action_counts.get(action, 0) + 1

    return {
        "total_candidates": len(results),
        "status_counts": dict(sorted(status_counts.items())),
        "action_counts": dict(sorted(action_counts.items())),
        "can_continue_to_candidate_page_dry_run_count": sum(1 for result in results if result.can_continue_to_candidate_page_dry_run),
        "results": [result.__dict__ for result in results],
    }
