from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

from .contracts import OfferCandidate, SourceTrustLevel

_URL_REGEX = re.compile(r"^https?://[a-z0-9.-]+\.[a-z]{2,}(?:[/?#].*)?$", flags=re.IGNORECASE)
_PLACEHOLDER_MARKERS = ("placeholder", "fake", "lorem", "ipsum", "todo")


class EligibilityStatus(str, Enum):
    ELIGIBLE = "eligible"
    REJECTED = "rejected"
    NEEDS_DATA = "needs_data"
    MANUAL_REVIEW = "manual_review"
    NOT_CONNECTED = "not_connected"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class CandidateEligibilityDecision:
    candidate: OfferCandidate
    status: EligibilityStatus
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class EligibilityGateResult:
    decisions: tuple[CandidateEligibilityDecision, ...]
    eligible_candidates: tuple[OfferCandidate, ...]
    status_counts: dict[str, int]


def _is_valid_url(value: str | None) -> bool:
    if not value:
        return False
    return bool(_URL_REGEX.match(value.strip()))


def _contains_placeholder_text(candidate: OfferCandidate) -> bool:
    probe_values = (
        candidate.title or "",
        candidate.brand or "",
        candidate.model or "",
        candidate.seller_name or "",
    )
    lowered = " ".join(probe_values).lower()
    return any(marker in lowered for marker in _PLACEHOLDER_MARKERS)


def run_product_eligibility_gate(
    candidates: tuple[OfferCandidate, ...],
    *,
    expected_vertical: str,
    source_trust_level: SourceTrustLevel,
    source_connected: bool,
    image_required: bool = True,
) -> EligibilityGateResult:
    if not source_connected:
        return EligibilityGateResult(
            decisions=tuple(
                CandidateEligibilityDecision(
                    candidate=candidate,
                    status=EligibilityStatus.NOT_CONNECTED,
                    reason_codes=("source_not_connected",),
                )
                for candidate in candidates
            ),
            eligible_candidates=tuple(),
            status_counts={EligibilityStatus.NOT_CONNECTED.value: len(candidates)},
        )

    seen_identity_keys: set[str] = set()
    decisions: list[CandidateEligibilityDecision] = []
    eligible: list[OfferCandidate] = []

    for candidate in candidates:
        reasons: list[str] = []
        status = EligibilityStatus.ELIGIBLE

        if source_trust_level == SourceTrustLevel.UNSAFE:
            status = EligibilityStatus.REJECTED
            reasons.append("unsafe_source")
        if source_trust_level == SourceTrustLevel.UNKNOWN:
            status = EligibilityStatus.MANUAL_REVIEW
            reasons.append("missing_source_trust")

        if not (candidate.title or "").strip():
            status = EligibilityStatus.NEEDS_DATA
            reasons.append("missing_title")
        if image_required and expected_vertical == "retail_physical_products" and not (candidate.image_url or "").strip():
            status = EligibilityStatus.NEEDS_DATA
            reasons.append("missing_image_required")
        if not (candidate.outbound_url or "").strip():
            status = EligibilityStatus.NEEDS_DATA
            reasons.append("missing_outbound_url")
        elif not _is_valid_url(candidate.outbound_url):
            status = EligibilityStatus.REJECTED
            reasons.append("invalid_outbound_url")

        if candidate.vertical and expected_vertical and candidate.vertical != expected_vertical:
            status = EligibilityStatus.NOT_APPLICABLE
            reasons.append("unrelated_vertical_or_category")
        if expected_vertical == "retail_physical_products" and candidate.vertical in {
            "software_saas_erp",
            "finance_insurance_business_finance",
        }:
            status = EligibilityStatus.NOT_APPLICABLE
            reasons.append("non_retail_vertical_in_retail_flow")

        if expected_vertical == "retail_physical_products":
            has_taxonomy = bool((candidate.google_taxonomy_path or "").strip() or (candidate.category_bucket or "").strip())
            if not has_taxonomy:
                status = EligibilityStatus.NEEDS_DATA
                reasons.append("missing_retail_taxonomy_linkage")

        if not (candidate.seller_name or "").strip():
            status = EligibilityStatus.NEEDS_DATA
            reasons.append("missing_seller")
        if candidate.seller_url and not _is_valid_url(candidate.seller_url):
            status = EligibilityStatus.REJECTED
            reasons.append("invalid_seller_url")

        if _contains_placeholder_text(candidate):
            status = EligibilityStatus.REJECTED
            reasons.append("fake_or_placeholder_commercial_data")

        if candidate.vertical == "finance_insurance_business_finance":
            regulated = bool((candidate.metadata or {}).get("regulated"))
            if regulated:
                status = EligibilityStatus.MANUAL_REVIEW
                reasons.append("finance_regulated_manual_review_only")

        identity_key = "|".join(
            (
                (candidate.brand or "").strip().lower(),
                (candidate.model or "").strip().lower(),
                (candidate.title or "").strip().lower(),
            )
        )
        if identity_key in seen_identity_keys:
            status = EligibilityStatus.REJECTED
            reasons.append("duplicate_product")
        elif identity_key != "||":
            seen_identity_keys.add(identity_key)

        if status == EligibilityStatus.ELIGIBLE:
            reasons.append("eligible_for_display")
            eligible.append(candidate)

        decisions.append(
            CandidateEligibilityDecision(
                candidate=candidate,
                status=status,
                reason_codes=tuple(dict.fromkeys(reasons)),
            )
        )

    counts: dict[str, int] = {}
    for decision in decisions:
        counts[decision.status.value] = counts.get(decision.status.value, 0) + 1
    return EligibilityGateResult(
        decisions=tuple(decisions),
        eligible_candidates=tuple(eligible),
        status_counts=counts,
    )
