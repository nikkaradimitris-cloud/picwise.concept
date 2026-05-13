from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


class PromotionDecisionStatus(str, Enum):
    promoted_to_limited_exposure = "promoted_to_limited_exposure"
    keep_controlled = "keep_controlled"
    hold_manual_review = "hold_manual_review"
    reject_from_promotion = "reject_from_promotion"
    rollback_required = "rollback_required"
    needs_more_observation = "needs_more_observation"


@dataclass(frozen=True)
class PromotionPolicy:
    outbound_error_hold_threshold: int = 0
    outbound_error_rollback_threshold: int = 2
    preview_error_hold_threshold: int = 0
    preview_error_rollback_threshold: int = 2
    require_preview_evidence_for_promotion: bool = True
    require_outbound_evidence_for_promotion: bool = True
    allow_sitemap_candidate_flag: bool = True
    force_keep_controlled: bool = False
    rollback_reason_tokens: tuple[str, ...] = (
        "provider_contract_regression",
        "rollback",
        "runtime_regression",
        "critical",
    )


@dataclass(frozen=True)
class PromotionDecision:
    candidate_page_id: str
    slug: str
    source_observation_status: str
    decision_status: PromotionDecisionStatus
    can_enter_limited_exposure: bool
    can_expand_sitemap_candidate: bool
    requires_manual_review: bool
    requires_rollback: bool
    reasons: tuple[str, ...]
    blocker_reasons: tuple[str, ...]
    review_reasons: tuple[str, ...]
    rollback_reasons: tuple[str, ...]
    evidence_summary: Mapping[str, Any]
    is_public: bool = False
    is_live_sitemap_included: bool = False


@dataclass(frozen=True)
class PromotionPolicyBatchResult:
    total_pages: int
    promoted_to_limited_exposure_count: int
    keep_controlled_count: int
    hold_manual_review_count: int
    reject_from_promotion_count: int
    rollback_required_count: int
    needs_more_observation_count: int
    status_counts: dict[str, int]
    blocker_counts: dict[str, int]
    review_counts: dict[str, int]
    rollback_counts: dict[str, int]
    can_move_to_step10: bool
    decisions: tuple[PromotionDecision, ...]


def _norm_text(value: Any) -> str:
    return str(value or "").strip()


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = _norm_text(value).lower()
    if normalized in {"1", "true", "yes", "y", "ready", "pass", "passed"}:
        return True
    if normalized in {"0", "false", "no", "n", "blocked", "fail", "failed"}:
        return False
    return default


def _as_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_reason_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        cleaned = [_norm_text(item) for item in value if _norm_text(item)]
        return tuple(dict.fromkeys(cleaned))
    single = _norm_text(value)
    return (single,) if single else tuple()


def _policy_from_input(policy: PromotionPolicy | None) -> PromotionPolicy:
    return policy if policy is not None else PromotionPolicy()


def _requires_rollback(
    *,
    summary: Mapping[str, Any],
    policy: PromotionPolicy,
    blocker_reasons: tuple[str, ...],
    source_reasons: tuple[str, ...],
) -> tuple[bool, tuple[str, ...]]:
    rollback_reasons: list[str] = []
    outbound_error_count = _as_int(summary.get("outbound_error_count"))
    preview_error_count = _as_int(summary.get("preview_error_count"))

    if outbound_error_count >= policy.outbound_error_rollback_threshold:
        rollback_reasons.append("outbound_error_trend_requires_rollback")
    if preview_error_count >= policy.preview_error_rollback_threshold:
        rollback_reasons.append("preview_error_trend_requires_rollback")

    searchable_reasons = [reason.lower() for reason in (*blocker_reasons, *source_reasons)]
    for token in policy.rollback_reason_tokens:
        token_norm = token.lower()
        if any(token_norm in reason for reason in searchable_reasons):
            rollback_reasons.append(f"rollback_token_detected:{token_norm}")

    unique = tuple(dict.fromkeys(rollback_reasons))
    return (len(unique) > 0, unique)


def _build_decision_payload(decision: PromotionDecision) -> dict[str, Any]:
    payload = asdict(decision)
    payload["decision_status"] = decision.decision_status.value
    return payload


def evaluate_promotion_decision(
    page_observation_summary: Mapping[str, Any],
    policy: PromotionPolicy | None = None,
) -> dict[str, Any]:
    resolved_policy = _policy_from_input(policy)
    summary = dict(page_observation_summary or {})

    candidate_page_id = _norm_text(summary.get("candidate_page_id") or "candidate-page-unknown")
    slug = _norm_text(summary.get("slug"))
    source_status = _norm_text(summary.get("status"))
    source_reasons = _to_reason_tuple(summary.get("reasons"))

    preview_render_count = _as_int(summary.get("preview_render_count"))
    outbound_click_count = _as_int(summary.get("outbound_click_count"))
    preview_error_count = _as_int(summary.get("preview_error_count"))
    outbound_error_count = _as_int(summary.get("outbound_error_count"))
    manual_review_count = _as_int(summary.get("manual_review_count"))
    blocker_event_count = _as_int(summary.get("blocker_event_count"))
    promotion_ready = _as_bool(summary.get("promotion_ready"))
    is_live_mvp_ready = _as_bool(summary.get("is_live_mvp_ready"))
    controlled_and_reversible = _as_bool(summary.get("controlled_and_reversible"), default=True)

    reasons: list[str] = []
    blocker_reasons: list[str] = []
    review_reasons: list[str] = []
    rollback_reasons: list[str] = []

    has_preview_evidence = preview_render_count > 0
    has_outbound_evidence = outbound_click_count > 0

    if source_status == "needs_more_data":
        reasons.append("source_status_needs_more_data")
        decision_status = PromotionDecisionStatus.needs_more_observation
    elif source_status == "hold_manual_review" or manual_review_count > 0:
        review_reasons.append("manual_review_event_present")
        reasons.append("manual_review_required")
        decision_status = PromotionDecisionStatus.hold_manual_review
    elif source_status == "blocked" or blocker_event_count > 0:
        blocker_reasons.append("source_blocked_or_blocker_event_present")
        is_rollback, rollback_codes = _requires_rollback(
            summary=summary,
            policy=resolved_policy,
            blocker_reasons=tuple(blocker_reasons),
            source_reasons=source_reasons,
        )
        rollback_reasons.extend(rollback_codes)
        if is_rollback:
            reasons.append("blocked_evidence_requires_rollback")
            decision_status = PromotionDecisionStatus.rollback_required
        else:
            reasons.append("blocked_evidence_rejects_promotion")
            decision_status = PromotionDecisionStatus.reject_from_promotion
    elif source_status != "observation_ready":
        reasons.append("non_promotable_source_observation_status")
        decision_status = PromotionDecisionStatus.keep_controlled
    elif not promotion_ready:
        reasons.append("source_observation_not_promotion_ready")
        decision_status = PromotionDecisionStatus.keep_controlled
    elif not is_live_mvp_ready or not controlled_and_reversible:
        blocker_reasons.append("must_remain_live_ready_controlled_and_reversible")
        reasons.append("promotion_contract_requires_controlled_live_ready")
        decision_status = PromotionDecisionStatus.reject_from_promotion
    elif (
        resolved_policy.require_preview_evidence_for_promotion
        and not has_preview_evidence
    ) or (
        resolved_policy.require_outbound_evidence_for_promotion
        and not has_outbound_evidence
    ):
        if resolved_policy.require_preview_evidence_for_promotion and not has_preview_evidence:
            reasons.append("preview_evidence_missing")
        if resolved_policy.require_outbound_evidence_for_promotion and not has_outbound_evidence:
            reasons.append("outbound_evidence_missing")
        decision_status = PromotionDecisionStatus.needs_more_observation
    elif (
        outbound_error_count > resolved_policy.outbound_error_hold_threshold
        or preview_error_count > resolved_policy.preview_error_hold_threshold
    ):
        is_rollback, rollback_codes = _requires_rollback(
            summary=summary,
            policy=resolved_policy,
            blocker_reasons=tuple(blocker_reasons),
            source_reasons=source_reasons,
        )
        if is_rollback:
            rollback_reasons.extend(rollback_codes)
            reasons.append("error_threshold_requires_rollback")
            decision_status = PromotionDecisionStatus.rollback_required
        else:
            if outbound_error_count > resolved_policy.outbound_error_hold_threshold:
                review_reasons.append("outbound_error_threshold_exceeded")
            if preview_error_count > resolved_policy.preview_error_hold_threshold:
                review_reasons.append("preview_error_threshold_exceeded")
            reasons.append("error_threshold_requires_manual_review")
            decision_status = PromotionDecisionStatus.hold_manual_review
    elif resolved_policy.force_keep_controlled:
        reasons.append("policy_forces_keep_controlled")
        decision_status = PromotionDecisionStatus.keep_controlled
    else:
        reasons.append("observation_ready_for_limited_exposure")
        decision_status = PromotionDecisionStatus.promoted_to_limited_exposure

    requires_manual_review = decision_status == PromotionDecisionStatus.hold_manual_review
    requires_rollback = decision_status == PromotionDecisionStatus.rollback_required
    can_enter_limited_exposure = decision_status == PromotionDecisionStatus.promoted_to_limited_exposure
    can_expand_sitemap_candidate = bool(
        can_enter_limited_exposure and resolved_policy.allow_sitemap_candidate_flag
    )

    evidence_summary = {
        "promotion_ready": promotion_ready,
        "is_live_mvp_ready": is_live_mvp_ready,
        "controlled_and_reversible": controlled_and_reversible,
        "has_preview_evidence": has_preview_evidence,
        "has_outbound_evidence": has_outbound_evidence,
        "preview_render_count": preview_render_count,
        "outbound_click_count": outbound_click_count,
        "preview_error_count": preview_error_count,
        "outbound_error_count": outbound_error_count,
        "manual_review_count": manual_review_count,
        "blocker_event_count": blocker_event_count,
    }

    decision = PromotionDecision(
        candidate_page_id=candidate_page_id,
        slug=slug,
        source_observation_status=source_status,
        decision_status=decision_status,
        can_enter_limited_exposure=can_enter_limited_exposure,
        can_expand_sitemap_candidate=can_expand_sitemap_candidate,
        requires_manual_review=requires_manual_review,
        requires_rollback=requires_rollback,
        reasons=tuple(dict.fromkeys((*source_reasons, *reasons))),
        blocker_reasons=tuple(dict.fromkeys(blocker_reasons)),
        review_reasons=tuple(dict.fromkeys(review_reasons)),
        rollback_reasons=tuple(dict.fromkeys(rollback_reasons)),
        evidence_summary=evidence_summary,
        is_public=False,
        is_live_sitemap_included=False,
    )
    return _build_decision_payload(decision)


def _count_by_status(decisions: Iterable[PromotionDecision]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        key = decision.decision_status.value
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _count_reasons(decisions: Iterable[PromotionDecision], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        reasons = getattr(decision, attr)
        for reason in reasons:
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def evaluate_promotion_policy_batch(
    page_summaries: Iterable[Mapping[str, Any]],
    policy: PromotionPolicy | None = None,
) -> dict[str, Any]:
    resolved_policy = _policy_from_input(policy)
    summaries = [dict(item) for item in page_summaries]
    ordered_summaries = sorted(
        summaries,
        key=lambda item: (_norm_text(item.get("candidate_page_id")), _norm_text(item.get("slug"))),
    )

    decisions: list[PromotionDecision] = []
    for summary in ordered_summaries:
        payload = evaluate_promotion_decision(summary, policy=resolved_policy)
        decisions.append(
            PromotionDecision(
                candidate_page_id=payload["candidate_page_id"],
                slug=payload["slug"],
                source_observation_status=payload["source_observation_status"],
                decision_status=PromotionDecisionStatus(payload["decision_status"]),
                can_enter_limited_exposure=bool(payload["can_enter_limited_exposure"]),
                can_expand_sitemap_candidate=bool(payload["can_expand_sitemap_candidate"]),
                requires_manual_review=bool(payload["requires_manual_review"]),
                requires_rollback=bool(payload["requires_rollback"]),
                reasons=tuple(payload["reasons"]),
                blocker_reasons=tuple(payload["blocker_reasons"]),
                review_reasons=tuple(payload["review_reasons"]),
                rollback_reasons=tuple(payload["rollback_reasons"]),
                evidence_summary=dict(payload["evidence_summary"]),
                is_public=bool(payload["is_public"]),
                is_live_sitemap_included=bool(payload["is_live_sitemap_included"]),
            )
        )

    status_counts = _count_by_status(decisions)
    blocker_counts = _count_reasons(decisions, "blocker_reasons")
    review_counts = _count_reasons(decisions, "review_reasons")
    rollback_counts = _count_reasons(decisions, "rollback_reasons")

    promoted_count = status_counts.get(PromotionDecisionStatus.promoted_to_limited_exposure.value, 0)
    keep_controlled_count = status_counts.get(PromotionDecisionStatus.keep_controlled.value, 0)
    hold_count = status_counts.get(PromotionDecisionStatus.hold_manual_review.value, 0)
    reject_count = status_counts.get(PromotionDecisionStatus.reject_from_promotion.value, 0)
    rollback_count = status_counts.get(PromotionDecisionStatus.rollback_required.value, 0)
    needs_more_count = status_counts.get(PromotionDecisionStatus.needs_more_observation.value, 0)
    total_pages = len(decisions)

    can_move_to_step10 = bool(
        total_pages > 0
        and promoted_count == total_pages
        and keep_controlled_count == 0
        and hold_count == 0
        and reject_count == 0
        and rollback_count == 0
        and needs_more_count == 0
        and all(not item.is_public for item in decisions)
        and all(not item.is_live_sitemap_included for item in decisions)
    )

    batch_result = PromotionPolicyBatchResult(
        total_pages=total_pages,
        promoted_to_limited_exposure_count=promoted_count,
        keep_controlled_count=keep_controlled_count,
        hold_manual_review_count=hold_count,
        reject_from_promotion_count=reject_count,
        rollback_required_count=rollback_count,
        needs_more_observation_count=needs_more_count,
        status_counts=status_counts,
        blocker_counts=blocker_counts,
        review_counts=review_counts,
        rollback_counts=rollback_counts,
        can_move_to_step10=can_move_to_step10,
        decisions=tuple(decisions),
    )

    payload = asdict(batch_result)
    payload["decisions"] = [_build_decision_payload(item) for item in batch_result.decisions]
    return payload
