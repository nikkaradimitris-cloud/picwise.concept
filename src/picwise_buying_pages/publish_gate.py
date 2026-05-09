from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from typing import Mapping

from .google_quality_gate import evaluate_google_quality_gate
from .index_gate import evaluate_index_gate, is_product_slot_publicly_valid
from .models import ApprovalStatus, BuyingPage, IndexStatus
from .repository import BuyingPagesRepository

APPROVAL_DECISION_APPROVED = "approved"
APPROVAL_DECISION_REJECTED = "rejected"
APPROVAL_DECISION_MANUAL_REQUIRED = "manual_required"
APPROVAL_DECISION_REVIEW_REQUIRED = "review_required"
APPROVAL_DECISION_PENDING = "pending"

PUBLISH_OUTCOME_PUBLISHED = "published"
PUBLISH_OUTCOME_BLOCKED = "blocked"
PUBLISH_OUTCOME_NEEDS_REVIEW = "needs_review"

_SELLER_RELIABILITY_REASON_SUFFIXES = frozenset(
    {
        "seller_unreliable_or_blocked",
        "seller_manual_review_required",
        "seller_status_unknown",
    }
)

_PRODUCT_GATE_REASON_SUFFIXES = frozenset(
    {
        "missing_title",
        "missing_or_invalid_availability",
        "availability_not_public_safe",
        "missing_image",
        "missing_or_invalid_price",
        "missing_currency",
        "missing_affiliate_url",
        "missing_short_product_text",
        "missing_useful_specs",
        "missing_short_description",
        "fake_or_suspicious_product_data",
        "price_band_currency_mismatch",
        "missing_seller_identity",
        "missing_return_policy_signal",
        "missing_shipping_info_signal",
    }
)


@dataclass(frozen=True)
class PublishGateResult:
    outcome: str
    page: BuyingPage
    reason_codes: tuple[str, ...]
    approval_decision: str
    candidate_trace: Mapping[str, object] | None = None
    source_metadata: Mapping[str, object] | None = None


def normalize_approval_decision(raw_decision: str) -> str:
    decision = str(raw_decision).strip().lower()
    if decision in {
        APPROVAL_DECISION_APPROVED,
        APPROVAL_DECISION_REJECTED,
        APPROVAL_DECISION_MANUAL_REQUIRED,
        APPROVAL_DECISION_REVIEW_REQUIRED,
        APPROVAL_DECISION_PENDING,
        "approved_candidate",
        "rejected_candidate",
    }:
        if decision == "approved_candidate":
            return APPROVAL_DECISION_APPROVED
        if decision == "rejected_candidate":
            return APPROVAL_DECISION_REJECTED
        return decision
    raise ValueError(f"Unsupported approval decision '{raw_decision}'.")


def _has_alias_conflict(page: BuyingPage, published_repository: BuyingPagesRepository) -> bool:
    terms = (page.main_keyword, *page.keyword_aliases)
    for term in terms:
        existing = published_repository.get_by_keyword(term)
        if existing is not None and existing.slug != page.slug:
            return True
    return False


def _passes_product_gate(page: BuyingPage, *, index_reasons: tuple[str, ...]) -> bool:
    if len(page.products) != 4:
        return False
    if not all(is_product_slot_publicly_valid(page, product) for product in page.products):
        return False
    for reason in index_reasons:
        if ":" not in reason:
            continue
        suffix = reason.split(":", maxsplit=1)[1]
        if suffix in _PRODUCT_GATE_REASON_SUFFIXES:
            return False
    return True


def _passes_seller_reliability_gate(index_reasons: tuple[str, ...]) -> bool:
    for reason in index_reasons:
        suffix = reason.split(":", maxsplit=1)[-1]
        if suffix in _SELLER_RELIABILITY_REASON_SUFFIXES:
            return False
    return True


def _transition_non_public(page: BuyingPage, *, decision: str) -> BuyingPage:
    approval_status = ApprovalStatus.PENDING_REVIEW
    if decision == APPROVAL_DECISION_REJECTED:
        approval_status = ApprovalStatus.REJECTED
    transitioned = copy(page)
    object.__setattr__(transitioned, "approval_status", approval_status)
    object.__setattr__(transitioned, "index_status", IndexStatus.NOINDEX)
    return transitioned


def evaluate_publish_gate(
    page: BuyingPage,
    *,
    approval_decision: str,
    published_repository: BuyingPagesRepository,
    economic_score_passed: bool,
    candidate_trace: Mapping[str, object] | None = None,
    source_metadata: Mapping[str, object] | None = None,
) -> PublishGateResult:
    decision = normalize_approval_decision(approval_decision)

    # Evaluate technical/quality gates on the would-be published representation.
    gate_page = copy(page)
    object.__setattr__(gate_page, "approval_status", ApprovalStatus.APPROVED)
    object.__setattr__(gate_page, "index_status", IndexStatus.INDEXABLE)
    index_result = evaluate_index_gate(gate_page)
    google_result = evaluate_google_quality_gate(
        gate_page,
        existing_pages=published_repository.list_pages(),
        economic_score_passed=economic_score_passed,
    )

    slug_conflict = published_repository.get_by_slug(page.slug) is not None
    alias_conflict = _has_alias_conflict(page, published_repository)
    product_ok_passed = _passes_product_gate(gate_page, index_reasons=index_result.reasons)
    seller_reliability_passed = _passes_seller_reliability_gate(index_result.reasons)
    recommended_product_ok = page.recommended_product_id in {item.product_id for item in gate_page.products}
    exact_product_count_ok = len(gate_page.products) == 4
    valid_product_proposals_ok = exact_product_count_ok and all(
        is_product_slot_publicly_valid(gate_page, product) for product in gate_page.products
    )

    reasons: list[str] = []
    if not economic_score_passed:
        reasons.append("economic_scoring_not_passed")
    if not google_result.quality_passed:
        reasons.append("google_quality_gate_not_passed")
    if not product_ok_passed:
        reasons.append("product_ok_gate_not_passed")
    if not seller_reliability_passed:
        reasons.append("seller_reliability_gate_not_passed")
    if not index_result.indexable:
        reasons.append("index_gate_not_passed")
    if slug_conflict:
        reasons.append("duplicate_slug_conflict")
    if alias_conflict:
        reasons.append("alias_conflict")
    if not recommended_product_ok:
        reasons.append("invalid_recommended_product")
    if not exact_product_count_ok:
        reasons.append("invalid_product_count")
    if not valid_product_proposals_ok:
        reasons.append("invalid_product_proposals")

    if decision in {APPROVAL_DECISION_MANUAL_REQUIRED, APPROVAL_DECISION_REVIEW_REQUIRED, APPROVAL_DECISION_PENDING}:
        transitioned = _transition_non_public(page, decision=decision)
        if decision == APPROVAL_DECISION_PENDING:
            reasons.append("approval_pending")
        else:
            reasons.append("approval_manual_review_required")
        return PublishGateResult(
            outcome=PUBLISH_OUTCOME_NEEDS_REVIEW,
            page=transitioned,
            reason_codes=tuple(dict.fromkeys([*reasons, *(f"google:{reason}" for reason in google_result.reasons)])),
            approval_decision=decision,
            candidate_trace=candidate_trace,
            source_metadata=source_metadata,
        )

    if decision == APPROVAL_DECISION_REJECTED:
        transitioned = _transition_non_public(page, decision=decision)
        reasons.append("approval_rejected")
        return PublishGateResult(
            outcome=PUBLISH_OUTCOME_BLOCKED,
            page=transitioned,
            reason_codes=tuple(
                dict.fromkeys(
                    [
                        *reasons,
                        *(f"google:{reason}" for reason in google_result.reasons),
                    ]
                )
            ),
            approval_decision=decision,
            candidate_trace=candidate_trace,
            source_metadata=source_metadata,
        )

    if reasons:
        transitioned = _transition_non_public(page, decision=APPROVAL_DECISION_PENDING)
        return PublishGateResult(
            outcome=PUBLISH_OUTCOME_BLOCKED,
            page=transitioned,
            reason_codes=tuple(
                dict.fromkeys(
                    [
                        *reasons,
                        *(f"google:{reason}" for reason in google_result.reasons),
                        *(f"index:{reason}" for reason in index_result.reasons),
                    ]
                )
            ),
            approval_decision=decision,
            candidate_trace=candidate_trace,
            source_metadata=source_metadata,
        )

    published_page = copy(page)
    object.__setattr__(published_page, "approval_status", ApprovalStatus.APPROVED)
    object.__setattr__(published_page, "index_status", IndexStatus.INDEXABLE)
    return PublishGateResult(
        outcome=PUBLISH_OUTCOME_PUBLISHED,
        page=published_page,
        reason_codes=tuple(),
        approval_decision=decision,
        candidate_trace=candidate_trace,
        source_metadata=source_metadata,
    )
